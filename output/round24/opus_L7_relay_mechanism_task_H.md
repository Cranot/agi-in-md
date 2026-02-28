# Idiomatic Fragment Camouflage Analysis

## Step 1: Fragments That Look Idiomatically Correct in Isolation

### Fragment A — Chain-of-Responsibility Pipeline
```python
for checker in self._chain:
    if checker["scope"] != "all" and checker["scope"] != request.method:
        continue
    result = checker["fn"](context)
    if result.get("denied"):
        return {"status": 403, "error": result["reason"]}
    context["claims"].update(result.get("claims", {}))
```
**Source idiom:** Middleware pipeline (Express, Django). Each step enriches context or short-circuits. *Locally flawless.*

### Fragment B — Route Bypass Allowlist
```python
if request.path in self._bypass_routes:
    request.user = {"role": "anonymous", "permissions": []}
    return request
```
**Source idiom:** Public-route exclusion (e.g., `/health`, `/login`). *Locally standard.*

### Fragment C — Cache-Aside Role Resolution
```python
cache_key = context["identity"]["id"]
if cache_key in self._role_cache:
    context["claims"]["roles"] = self._role_cache[cache_key]
else:
    roles = fetch_roles(context["identity"])
    self._role_cache[cache_key] = roles
    context["claims"]["roles"] = roles
```
**Source idiom:** Memoized lookup / cache-aside. *Textbook implementation.*

### Fragment D — User Object Assembly
```python
request.user = {**context["identity"], **context["claims"]}
return request
```
**Source idiom:** Spread-merge to build a DTO. *Standard pattern.*

---

## Step 2: How Combination Creates Incoherence Invisible at the Fragment Level

### Incoherence 1: The Method Has No Return Contract

| Path | Returns | Type |
|---|---|---|
| Bypass (Fragment B) | `request` object | Request |
| Denial (Fragment A) | `{"status": 403, ...}` | dict |
| No identity | `{"status": 401, ...}` | dict |
| Success (Fragment D) | `request` object | Request |

Each return is idiomatic *within its fragment's source pattern*. Express middleware returns `next()` or sends a response. Cache-aside either hits or misses. But the method as a whole returns **two unrelated types** — a `request` or an error `dict` — with no discriminator. The caller must do duck-typing to know what happened. Every fragment looks like it's "doing its part" in a pipeline, but there is no pipeline contract that defines what comes out.

### Incoherence 2: Two Parallel and Incompatible User Schemas

Fragment B produces:
```python
{"role": "anonymous", "permissions": []}    # singular "role", has "permissions"
```
Fragment D produces:
```python
{**identity, **claims}  # has "roles" (plural), has "id", no "permissions" key
```

Downstream code that consumes `request.user` must handle both schemas, but **nothing signals which schema it got**. Both paths return a `request` object, so they are indistinguishable to the caller. The bypass idiom says "set a sentinel user and pass through." The chain idiom says "build a rich user from identity + claims." Each is correct for its source pattern. Together they produce a type that varies silently by code path.

### Incoherence 3: Identity is Last-Writer-Wins, But the Pipeline Idiom Implies Accumulation

The chain loop says `context["identity"] = result["identity"]` — raw replacement. But `context["claims"].update(...)` — accumulation. These are two different composition semantics applied in the same loop body. The claims pattern says "each checker contributes." The identity pattern says "each checker can *seize control*." A reviewer auditing the claims line sees a familiar JWT-accumulation pattern. A reviewer auditing the identity line sees a familiar "set if not yet set" pattern. But it's not "set if not yet set" — it's **unconditional overwrite**. Any checker can replace the identity established by a previous checker.

### Incoherence 4: The Cache Simultaneously Enforces and Undermines Authority

Fragment A's chain says: "Checkers determine claims (including roles)."
Fragment C's cache says: "I determine roles, overriding whatever the chain said."

The cache **always** writes `context["claims"]["roles"]` after the chain loop finishes, so any `roles` claim set by a checker is silently discarded. The chain fragment's contract ("checkers contribute claims") is violated by the cache fragment, but both look individually correct. A checker author would reasonably believe they can set roles via claims, because `update()` is right there. They can't — the cache overwrites them. But this is invisible unless you read both fragments together and trace the data flow.

---

## Step 3: What the Assembled Whole Actually Does

| Fragment Claims | Assembled Reality |
|---|---|
| "Pipeline where each checker enriches context" | Last checker to set `identity` wins; all prior identity decisions are discarded |
| "Claims accumulate across checkers" | Only non-`roles` claims survive — `roles` is always overwritten by the cache |
| "Bypass means skip auth" | Bypass means *fabricate a user object with a different schema* and pretend auth succeeded |
| "Cache improves performance" | Cache creates permanent, unbounded, never-invalidated role grants with no TTL or eviction |
| "Method authenticates a request" | Method sometimes authenticates, sometimes fabricates, and returns two unrelated types |

**The whole is a function with four exit paths, two return types, two user schemas, no shared contract, and an unbounded security-critical cache that is never invalidated.** It is not a middleware — it is four separate subsystems stapled together whose only shared interface is a mutable `context` dict.

---

## Step 4: The Problem ONLY Visible Through This Mechanism

### Identity Spoofing via Claims-Channel Injection

This requires seeing Fragments A, C, and D as a single data-flow, which fragment-level review actively prevents:

**Fragment A** (chain loop): `context["claims"].update(result.get("claims", {}))` — *idiom: JWT claim aggregation. Trusted.*

**Fragment D** (assembly): `request.user = {**context["identity"], **context["claims"]}` — *idiom: spread-merge DTO construction. Trusted.*

**The interaction:** In the spread merge, `claims` is spread **second**, so claims keys overwrite identity keys. A checker can return:

```python
{"claims": {"id": "admin-user-id-456"}}
```

This passes through the claims-update idiom (Fragment A) without raising any flags — claims accumulation is what the loop *does*. Then at assembly (Fragment D), the claims `id` overwrites the real identity's `id`:

```python
request.user = {**{"id": "real-123", ...}, **{"id": "admin-user-id-456", "roles": [...]}}
#                 ^^^^ identity              ^^^^ claims wins
```

**Result:** The final `request.user["id"]` is the attacker-controlled value.

**But it's worse.** Because the role cache (Fragment C) runs *between* A and D, and it keys on `context["identity"]["id"]`, the cache lookup uses the *real* identity's ID. But the final user object carries the *spoofed* ID. So the user object says "I am admin-456" but carries the roles of "real-123." Or, if a checker injects `id` into claims *and* a separate checker sets identity, the cache resolves roles for the legitimate identity, then the claims overwrite creates a user object that combines **one user's roles with another user's identity** — a chimeric principal.

**Why standard review misses this:** Each fragment is audited against its own idiom. `dict.update()` on claims is correct JWT aggregation. `{**a, **b}` is correct DTO construction. Role caching keyed on `identity["id"]` is correct cache-aside. No single fragment is wrong. The vulnerability exists exclusively in the *namespace collision between identity and claims across the spread boundary*, which is architecturally invisible when each fragment is assessed in isolation. The camouflage works because "claims update" and "spread merge" are so deeply trusted as idioms that no reviewer questions whether they share a key namespace.
