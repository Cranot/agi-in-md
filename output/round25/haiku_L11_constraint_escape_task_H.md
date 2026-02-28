# Structural Analysis: Authentication Middleware Chain

## The Core Claim (Falsifiable)

**The deepest structural problem: The code conflates two incompatible notions. It treats identity as something the middleware *establishes* (an output of     -> Done (98s) -> 288 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/haiku_L11_constraint_escape_task_H.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
he identity is revoked before the return statement, the code will set stale roles
- If two checkers both set `context["identity"]`, the cache key might shift, but the code doesn't invalidate the cache
- If `fetch_roles()` is unreachable, the code fails even if roles were cached, showing roles aren't truly optional

---

## How Three Experts Transform This Claim

**Expert 1 (Defender):** "You're right. Look at line 27-30: the cache uses only the identity ID, ignoring which checker produced it. If the identity comes from OAuth one request and LDAP the next, they might use `id="john"` for different people, and the cache would be incoherent."

**Expert 2 (Attacker):** "That's a symptom. The real problem is earlier: `result.get("denied")` — what if a checker returns `{"denied": 0}` or `{"denied": None}`? And why is `denied` a signal while `identity` is state? The code doesn't define what each checker is supposed to produce. The identity-caching issue is just what happens when you have undefined contracts."

**Expert 3 (Prober):** "Both true, but you're both assuming the goal is to *fix* this architecture. What if the goal is to understand what this architecture *is*? You're both describing a system that tries to be both: (1) a validator (the middleware decides if a request is allowed) and (2) an authenticator (the middleware decides what identity a request has). But these are two different problems with different answer formats. The cache breaks because it's optimizing for something the middleware isn't actually responsible for — maintaining role data."

**Transformed Claim:** The code is architecturally incoherent because it mixes validation (a decision) with authentication (a lookup). The cache isn't just stale; it's conceptually orphaned — the code owns neither the identity system nor the roles system, but it's building a local view of both and assuming they stay coherent.

---

## The Concealment Mechanism

The code conceals this via **abstraction inversion**:

```python
context = {"request": request, "identity": None, "claims": {}}
```

This single dict makes it *look* like a normal accumulating state machine ("context enrichment"), but it's actually a **lossy projection**:
- `identity` isn't an identity; it's "whatever the last checker returned that had an `identity` key"
- `claims` isn't a set of verified facts; it's a merge of whatever each checker claimed
- The code can't tell if a checker ran and returned nothing, or didn't run at all

The concealment works by:
1. **Using a dict for things that should have contracts** — any checker can return any keys
2. **Naming the loop variable generically** — `for checker in self._chain` hides that each checker has a different purpose
3. **Making the cache look like an optimization** — `if cache_key in self._role_cache` looks like a normal LRU cache, not like trusting stale data from a system you don't maintain

---

## Deepening the Concealment (Code that passes review)

Here's an improvement that looks correct while hiding the real problem:

```python
class AuthMiddleware:
    def __init__(self):
        self._identity_checkers = []
        self._authorization_checkers = []
        self._bypass_routes = set()
        self._role_cache = TTLCache(maxsize=10000, ttl=300)  # Looks rigorous!

    def add_identity_checker(self, fn, scope="all"):
        self._identity_checkers.append({"fn": fn, "scope": scope})

    def add_authorization_checker(self, fn, scope="all"):
        self._authorization_checkers.append({"fn": fn, "scope": scope})

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return request

        # Phase 1: Identify
        identity = None
        for checker in self._identity_checkers:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            result = checker["fn"]({"request": request, "identity": identity})
            if result.get("denied"):
                return {"status": 403, "error": result["reason"]}
            if result.get("identity"):
                if identity and identity["id"] != result["identity"]["id"]:
                    return {"status": 400, "error": "Conflicting identities"}  # Looks good!
                identity = result["identity"]

        if identity is None:
            return {"status": 401, "error": "No identity"}

        # Phase 2: Authorize
        cache_key = (identity["id"], identity.get("realm", "default"))
        if cache_key not in self._role_cache:
            roles = fetch_roles(identity)
            self._role_cache[cache_key] = roles
        
        roles = self._role_cache[cache_key]

        # Phase 3: Check permissions
        context = {"identity": identity, "roles": roles, "request": request}
        for checker in self._authorization_checkers:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            result = checker["fn"](context)
            if result.get("denied"):
                return {"status": 403, "error": result["reason"]}

        request.user = identity
        return request
```

**Why this passes code review:**
- ✓ Separates identity from authorization (looks architecturally sound)
- ✓ Uses TTLCache with explicit TTL (looks like it solved staleness)
- ✓ Checks for conflicting identities (looks defensive)
- ✓ Uses tuple cache keys with realm (looks more robust)
- ✓ Three clear phases (looks like proper separation of concerns)

**Why it deepens the concealment:**

1. **It looks solved** — TTLCache makes staleness look like a solved problem. But you still have a 5-minute window where roles are stale. You've just moved the problem boundary.

2. **It introduces assumptions it doesn't validate** — The `realm` field is new and unchecked. It looks like you're handling multiple identity sources, but if a checker doesn't set `realm`, it defaults to `"default"`, and you get silent cache collisions.

3. **It makes incoherence look impossible** — By checking for conflicting identities, the code looks more rigorous. But what if two checkers run for the same identity, and the *second one* sees different roles? The code can't detect that.

---

## Three Properties Visible Only Because I Tried to Strengthen It

1. **The phantom time window**: By adding a TTL, I made visible that there's an unbridgeable gap between when `fetch_roles()` returns and when the request handler uses those roles. Even with TTL=1 second, that gap exists. The original code hides it by pretending caching is "just an optimization."

2. **The identity source assumption**: By adding `realm`, I revealed that the code assumes `identity["id"]` is globally unique. But it's not. An `id="alice"` from OAuth is different from `id="alice"` from LDAP. The original code hides this by just using the ID directly, making it look like identity is a simple primitive.

3. **The lost temporal ordering**: By separating phases, I made visible that identity and authorization are determined at *different points in time*, but the code treats them as simultaneous. If phase 2 (fetch roles) runs at T=100ms and phase 3 (check permissions) runs at T=101ms, the permission might have changed. But the code assumes it hasn't. The original code hides this by running everything in a loop where "time" is implicit.

---

## Applying the Diagnostic to the "Improved" Version

**What does the improved version conceal?**

It hides that adding phases doesn't actually separate concerns — it separates *when things happen*, which is different. The code still:
- Owns the identity (via checkers)
- Caches the roles (via cache)
- Makes the authorization decision (via checkers)

You've just added a TTL and a tuple cache key, neither of which solves the fundamental incoherence.

**What property of the original problem is visible because I recreated it?**

By adding the TTL, I made visible that **the code assumes roles are a function of time + identity, but it can only check identity, not time**. In the original code, this assumption is invisible. In the improved code, it's visible as "TTL=300", which admits you don't know if roles are still valid after 300 seconds, but you're betting they are.

---

## Second Improvement (Addressing the Recreated Property)

What if I make the temporal locality explicit by revalidating before the decision?

```python
def authenticate(self, request):
    if request.path in self._bypass_routes:
        request.user = {"role": "anonymous", "permissions": []}
        return request

    identity = self._identify(request)
    if isinstance(identity, dict) and identity.get("status"):
        return identity  # Error

    # Get roles, but don't cache — every request pays the cost
    roles = fetch_roles(identity)

    context = {"identity": identity, "roles": roles, "request": request}
    for checker in self._authorization_checkers:
        result = checker["fn"](context)
        if result.get("denied"):
            return {"status": 403, "error": result["reason"]}

    request.user = identity
    return request
```

**Why this doesn't solve it:** Now every request calls `fetch_roles()`, which means:
- You're incurring the cost of no caching (bad performance)
- But you're still assuming that `fetch_roles(identity)` at T=100ms is valid at T=100.001ms when you return (still bad assumption)
- You've made the problem obvious but you haven't solved it

**But this is useful because:** It makes visible that **the real constraint is not caching vs. no-caching, but the gap between when you validate and when you use the validation**. You can't close that gap by fetching more often; you can only close it by removing the gap, which means validating right at the point of use.

---

## The Structural Invariant

What persists through every improvement attempt?

**Invariant: The middleware must make a yes/no decision (allow/deny) based on state (identity, roles) that is maintained by systems the middleware does not control.**

This invariant implies:
- You validate against remote sources
- You make local decisions based on that validation
- That decision must last long enough to be useful (even 0 seconds is "long enough" in some sense)
- But the remote state can change during that interval

The invariant creates a category of designs: **"Decision-after-Validation with Deferred Authority"**

All designs in this category must answer: "What is the acceptable staleness of the information I'm basing decisions on?" The original code doesn't answer this (it assumes infinite staleness is OK because it's cached). The improved version assumes TTL=300s. The no-cache version assumes TTL=0s (which is false, since there's still network latency).

---

## Design in the Adjacent Category: Where the Invariant Dissolves

Move to: **"Continuous Validation with Embedded Authority"**

In this design, the middleware doesn't make yes/no decisions about identity or roles. Instead, it enriches the request with *current* identity data, and downstream services validate permissions:

```python
class IdentityMiddleware:
    """Not an authorization middleware; an identity lookup middleware."""
    
    def __init__(self, identity_service):
        self.identity_service = identity_service  # Our system, not external

    async def __call__(self, request):
        # Step 1: Extract the identity claim from the request
        # (bearer token, session cookie, etc.)
        token = request.headers.get("Authorization")
        
        if not token:
            request.identity = None
            return request

        # Step 2: Validate the claim is well-formed
        try:
            identity_id = parse_token(token)
        except:
            return {"status": 401, "error": "Invalid token"}

        # Step 3: Look up the *current* identity from our database
        # (no cache, this is our system, we can afford to check)
        identity = await self.identity_service.get_identity(identity_id)
        
        if not identity:
            return {"status": 401, "error": "Unknown identity"}

        request.identity = identity
        return request


# Then, in route handlers:
@app.get("/api/data")
async def get_data(request):
    if not request.identity:
        return {"status": 401}
    
    # Permissions are checked by the handler, not the middleware
    # Handlers can make decisions based on current data
    if "read:data" not in request.identity["permissions"]:
        return {"status": 403}
    
    return {"data": "..."}
```

**How this succeeds where every improvement failed:**

1. **No cache, no staleness** — Identity is looked up once per request from the system we control
2. **No incoherence** — The middleware doesn't cache anything; it just looks up current state
3. **Clear authority** — This middleware is a lookup, not a validator. The actual authorization decision is in the handler.
4. **Composable** — Handlers can make different decisions based on what they need to check
5. **Simple** — No state accumulation, no temporal gaps between validation and use

**The new impossibility:**

In the original category, the middleware could *accumulate* identity across checkers and share it. You could say "this request is user X with permissions Y, Z, W" and then pass that package through the rest of the system.

In the new category, you can't do that. The middleware just looks up identity once and returns it. If you need more information (specific permissions for this handler, roles from a different system), the *handler* has to look it up.

More specifically: **You cannot achieve a centralized authorization policy in this design. Each handler must know how to check permissions. You lose the middleware's ability to be a policy enforcement point.**

---

## The Trade-off: Old vs. New Impossibilities

| Property | Original Category | New Category |
|----------|------------------|--------------|
| **Coherence** | ✗ Cache can be stale | ✓ Always fresh lookup |
| **Complexity** | ✗ State accumulation, phases, caching logic | ✓ Simple lookup |
| **Efficiency** | ✓ Can cache, batch lookups | ✗ Lookup per request |
| **Centralized policy** | ✓ Middleware enforces | ✗ Handlers enforce |
| **Temporal gap** | ✗ Between validation and use | ✓ Validation at use-time |
| **Authority clarity** | ✗ Middleware owns state it doesn't control | ✓ Middleware owns only lookups |

**The deep finding:** The original code fails because it tries to *own* identity while delegating to external systems. The better design is for the middleware to *delegate entirely* to external systems (or to internal systems the middleware controls), and let handlers decide what to do with that information.

The trade-off is: you can't have both centralized authorization policy and coherent state. You must choose which system is the authority (middleware or handler), and accept that the other can't enforce policy.
