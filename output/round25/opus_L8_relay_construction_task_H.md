# Structure First Analysis: Auth Middleware Chain

## 1. The Vocabulary That Terminates Inspection

The code borrows from three well-established lexicons simultaneously, and each one shuts down a different line of questioning:

| Term | Borrowed From | What It Suppresses |
|---|---|---|
| **"chain"** | Middleware frameworks (Express, Django) | The assumption of composable, independent handlers prevents you from asking whether checkers are actually independent |
| **"claims"** | JWT / OAuth 2.0 | The formality of the word makes `dict.update()` look like standard claims-merging, preventing you from asking about overwrite semantics |
| **"scope"** | OAuth 2.0 scopes | Actually means HTTP method filtering — but the word "scope" makes this seem like a rich authorization concept |
| **"context"** | Request-context patterns | Suggests structured, controlled data flow — hides that it's a shared mutable dict every checker can read and corrupt |
| **"bypass"** | Security exemption patterns | Suggests "skip authentication" — hides that it actually *injects a synthetic identity* |

The compound effect: anyone reading this recognizes "auth middleware chain with claims and scopes," nods, and stops inspecting. **Recognition terminates analysis.**

---

## 2. The Engineered Improvement

A "reasonable" strengthening — priority-ordered chain execution, wildcard bypass patterns, claim schema validation, and context snapshots for debugging:

```python
class AuthMiddleware:
    def __init__(self, claim_schema=None):
        self._chain = []
        self._bypass_patterns = []
        self._role_cache = {}
        self._claim_schema = claim_schema or {}

    def add(self, checker_fn, scope="all", priority=0):
        self._chain.append({"fn": checker_fn, "scope": scope, "priority": priority})
        self._chain.sort(key=lambda c: c["priority"], reverse=True)

    def bypass(self, pattern):
        self._bypass_patterns.append(re.compile(pattern))

    def authenticate(self, request):
        if any(p.match(request.path) for p in self._bypass_patterns):
            request.user = {"role": "anonymous", "permissions": [], "_bypassed": True}
            return request

        context = {"request": request, "identity": None, "claims": {}}

        for checker in self._chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            snapshot = dict(context["claims"])          # freeze pre-checker state
            result = checker["fn"](context)
            if result.get("denied"):
                return {"status": 403, "error": result["reason"],
                        "_pre_denial_claims": snapshot}
            for key, val in result.get("claims", {}).items():
                if key in self._claim_schema:           # validate against schema
                    if not self._claim_schema[key](val):
                        continue                        # silently skip bad claims
                context["claims"][key] = val
            if result.get("identity"):
                context["identity"] = result["identity"]

        if context["identity"] is None:
            return {"status": 401, "error": "No identity established"}

        cache_key = context["identity"]["id"]
        if cache_key in self._role_cache:
            context["claims"]["roles"] = self._role_cache[cache_key]
        else:
            roles = fetch_roles(context["identity"])
            self._role_cache[cache_key] = roles
            context["claims"]["roles"] = roles

        request.user = {**context["identity"], **context["claims"]}
        return request
```

Every change is individually defensible. Together, they deepen every structural problem.

---

## 3. Three Properties Exposed By the Improvement

### Property 1: Priority ordering promotes hidden inter-checker coupling to an intentional feature

In the original code, checkers execute in insertion order. Each checker receives accumulated `context` — meaning checker #3 might silently depend on claims set by checker #1. This dependency is invisible because insertion order feels natural ("of course they run in order").

**Adding priority ordering** makes execution order explicit and decoupled from registration order. But now: if a high-priority identity-checker runs before a lower-priority token-validator that was *registered* first, the accumulated `context` changes shape depending on priority values. The snapshot "improvement" tries to capture this, which **promotes the hidden coupling into a documented, supported feature**. The system now *officially* tracks how context evolves through the chain, making the mutation dependency look designed rather than accidental.

> What was always true: the "chain" has never been a chain. It's a pipeline of co-routines sharing mutable state, where each checker is an implicit consumer of its predecessors' side effects.

### Property 2: The return value develops two irreconcilable object shapes, exposing caller-internal coupling

`authenticate()` returns either:
- **Success/bypass**: the mutated `request` object (has `.path`, `.method`, `.user`)
- **Denial/failure**: a plain dict `{"status": 403, "error": "..."}` (has string keys)

The improvement makes this worse. The denial path now includes `_pre_denial_claims` (diagnostic snapshot data bolted onto an error dict), while the bypass path now includes `_bypassed: True` bolted onto `request.user`. The caller must:

```python
result = auth.authenticate(request)
if isinstance(result, dict):       # error path — but request is also dict-like?
    return result
# else it's the mutated request... which you already had a reference to
```

**The construction reveals**: the caller must already understand the internal branching structure of `authenticate()` to handle the return. There is no return type — there are three incompatible return *situations* smuggled through one signature. This was always true, but the improvement exposes it by making each branch accrue different diagnostic metadata.

### Property 3: Bypass injects a synthetic identity, creating two irreconcilable "user" shapes

The bypass path manufactures `{"role": "anonymous", "permissions": []}`. The auth-success path produces `{**identity, **claims}` — which has entirely different keys (`id`, `roles`, domain-specific claims). Every downstream consumer of `request.user` must handle both shapes, but nothing enforces this.

**Adding wildcard bypass patterns** makes this worse: `bypass(r"/api/public/.*")` means a regex error could silently grant anonymous access to protected routes. But the deeper exposure is structural. The `_bypassed: True` flag I had to add reveals that **bypass was never "skip auth" — it was "hardcode an alternative auth result."** Every consumer of `request.user` was already required to dual-path, but the vocabulary "bypass" prevented anyone from seeing the obligation.

---

## 4. The Construction-Only Problem: The Bifurcated Claims Channel

This problem is **invisible** in the original code and **only appears** when you attempt the schema validation improvement.

Here is the key passage, post-improvement:

```python
# IN THE CHAIN: claims are validated against schema
for key, val in result.get("claims", {}).items():
    if key in self._claim_schema:
        if not self._claim_schema[key](val):
            continue  # skip invalid claims
    context["claims"][key] = val

# ... later, AFTER the chain ...

# OUTSIDE THE CHAIN: roles bypass validation entirely
context["claims"]["roles"] = self._role_cache[cache_key]
```

There are now **two independent channels** through which claims enter the system:

| Channel | Source | Validated? | Overwrite behavior |
|---|---|---|---|
| Chain path | checker return values | Yes (schema) | Accumulative with silent skip |
| Cache path | `fetch_roles()` / `_role_cache` | **Never** | **Silently overwrites** any chain-set `roles` |

This means:

1. **A checker in the chain could set `claims["roles"]`** — and the post-chain cache injection silently destroys it. The schema validation creates false assurance that validated claims survive.

2. **The role cache has no invalidation, no TTL, no validation.** The first request for a given `identity["id"]` permanently determines the roles for all future requests. A privilege escalation in the backing store is invisible.

3. **`identity["id"]` as cache key depends on which checker last set `identity`** — with priority ordering, this could be non-obvious. A reordering of priorities silently changes which identity's roles get cached.

4. **The `{**context["identity"], **context["claims"]}` merge at the end** means if `identity` has a key named `roles`, it gets overwritten by `claims["roles"]`. If `identity` has a key named anything in `claims`, one silently wins. The improvement cannot add schema validation to this merge because the merge is *after* all validation.

**Why this is construction-only**: In the original code, the role-cache block looks like a straightforward performance optimization — completely normal, utterly unremarkable. Only when you try to add claim validation do you discover that the most security-critical claim in the entire system (*roles*) enters through a path that *cannot be validated*, that *silently overwrites validated claims*, and that *caches permanently based on a mutable identity reference*. The vocabulary "cache" made this look like an optimization. Construction reveals it's an unvalidated, ungoverned backdoor into the claims object.

---

## Summary

The diagnostic pattern works because **strengthening a system forces you to specify what the system actually promises**. This code could never specify:
- What type `authenticate()` returns (because it's three incompatible types)
- What "claims" means (because there are two unrelated injection channels)
- What "chain" guarantees (because checkers are coupled through shared mutable state)
- What "bypass" preserves (because it manufactures a structurally incompatible user)

These aren't bugs. They're **structural incoherences** that the vocabulary ("middleware," "chain," "claims," "cache," "bypass") was precisely sufficient to conceal — until you tried to make them stronger.
