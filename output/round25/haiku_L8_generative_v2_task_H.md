# Structural Diagnostic: Authentication Middleware

## Initial Claim (Falsifiable)

**The deepest structural problem: This middleware assumes authorization (roles) can be factored out as a post-chain step indexed by identity.id alone, hiding the reality that authorization is context-dependent and architecturally privileged. This creates invisibly fragile ordering—any checker that needs roles, or any role decision that depends on request context beyond identity.id, cannot exist. The chain appears comprehensive while the real authorization is done outside it.**

Falsifiable: Try implementing (1) a checker that uses roles within the chain, (2) time-aware role caching, (3) API-version-specific roles, (4) per-permission role freshness. All fail.

---

## Three-Expert Stress Test

**Expert 1 (Defender):**
> "This is actually clean architecture. Authentication and authorization are properly separated. The chain establishes who you are; roles determine what you can do. That's textbook layering."

**Expert 2 (Attacker):**
> "That separation is fake. Roles aren't a separate layer—they're THE authorization. And you can't make authorization decisions without request context. You need roles to influence which identity sources are trusted. The cache key is a lie—identity.id isn't enough."

**Expert 3 (Prober):**
> "What happens when: A checker needs to know which roles a user will have before deciding to establish identity? A checker must reject based on roles? Roles are time-of-day dependent? Different identity sources give different roles? Can the architecture survive *any* of these?"

### The Transformation

- **Original claim:** "Roles are privileged and hidden as post-processing"
- **After defense:** "Maybe not hidden—maybe *intentionally separated*. But that separation assumption is the load-bearing wall."
- **After attack:** "The separation forces a caching strategy that works for none of the real cases."
- **After probing:** "The real problem is deeper: the architecture bakes in a specific policy (roles are identity properties, cache key is ID only, lookup happens once per request) and disguises it as a neutral technical detail."

---

## Concealment Mechanism: Privilege Through Invisibility

The code hides its problems through **two nested concealments**:

1. **Privilege by Position, Not Declaration**
   - Role fetching is outside the chain, giving it special status without acknowledging this as a design choice
   - It's not a checker (which would expose composability questions)
   - It's not in context (which would expose visibility questions)  
   - It just *is*, positioned after everything else—that positioning *is* the policy

2. **Assumed Simplicity Smuggling Policy as Fact**
   - `cache_key = context["identity"]["id"]` appears to be code, but it's actually a policy: "Roles are properties of identity alone, not of request context, time, endpoint, or permission"
   - This policy is invisible because it's embedded, not stated
   - No documentation says "roles cannot be request-context-dependent"—the code just *prevents it*

**Combined effect:** The chain *appears* to be doing the real work while roles *appear* to be a technical detail. Inverted: roles ARE the authorization decision; the chain is subordinate to it.

---

## The Legitimate-Looking Improvement That Deepens Concealment

```python
class AuthMiddleware:
    def __init__(self):
        self._chain = []
        self._bypass_routes = set()
        self._role_cache = {}
        self._cache_ttl = 3600        # NEW: explicit cache TTL ← LOOKS GOOD
        self._cache_timestamps = {}   # NEW: track freshness ← LOOKS GOOD

    def set_cache_ttl(self, ttl):
        """Configure role cache time-to-live"""  # ← PROFESSIONAL TOUCH
        self._cache_ttl = ttl

    def authenticate(self, request):
        # ... chain execution unchanged ...
        
        cache_key = context["identity"]["id"]
        current_time = time.time()
        
        # NEW: Validate cache age before use
        if (cache_key in self._role_cache and 
            current_time - self._cache_timestamps.get(cache_key, 0) < self._cache_ttl):
            context["claims"]["roles"] = self._role_cache[cache_key]
        else:
            roles = fetch_roles(context["identity"])
            self._role_cache[cache_key] = roles
            self._cache_timestamps[cache_key] = current_time
            context["claims"]["roles"] = roles

        request.user = {**context["identity"], **context["claims"]}
        return request
```

**Why This Passes Code Review:**
- ✓ Addresses obvious gap: "cache never expires"
- ✓ Standard pattern: TTL-based invalidation
- ✓ Configurable: allows tuning
- ✓ Professional: timestamps, time.time()
- ✓ Makes problem look *solved*

**Why It Deepens Concealment:**
- Makes caching look *sophisticated* (thus trustworthy) when the strategy is fundamentally wrong
- Reviewers think "good, now cache is properly invalidated" while the real problem remains
- Harder to argue with because it *looks* correct
- Hides that TTL is wrong model; what matters is context, not elapsed time

---

## Three Properties Revealed Only By Trying to Strengthen It

### 1. **TTL Exposes That Time Is the Wrong Invalidation Model**

By making TTL explicit, we've revealed the hidden assumption: "Role freshness is time-based."

But consider reality:
- Admin role granted at 2:05 PM → identity is "Admin" **immediately**
- Admin role revoked at 2:07 PM → identity should be "User" **immediately**
- TTL-based cache gives you stale data at 2:08 PM (if TTL is 5 minutes)

What *actually* matters for role freshness:
- Did an admin privilege change occur? (not: has 3600 seconds elapsed?)
- Is the user in a different organization context? (not: is the timestamp old?)
- Are permissions contextual to this request? (not: based on global time?)

**The visibility:** By trying to fix caching with TTL, we've exposed that the cache key strategy itself (`identity["id"]` alone) is incompatible with proper authorization freshness.

### 2. **The Cache Key Strategy Is Secretly Policy-Loaded, Not Technical**

Adding TTL made us examine: "What exactly are we caching against?"

Answer: `identity["id"]`

But this reveals the hidden policy: "All users with the same ID have the same roles, regardless of request context, time, or session state."

This policy is invisible because it's embedded. But observable: Try to implement:
- Roles that depend on request.headers["api-version"]?
- Roles that depend on which endpoint is being called?
- Roles that depend on whether this is the user's first request or nth request?
- **All impossible** because cache key is just ID

**The visibility:** By trying to add a "freshness" mechanism, we've exposed that the "freshness" problem is really a "cache strategy" problem—and the cache strategy is wrong for the actual use case.

### 3. **One Role Lookup Is Actually a Hidden Architectural Choice, Not a Technical Detail**

The code calls `fetch_roles()` exactly once, at a fixed point, with no alternatives.

This appears to be "how authorization works" but it's actually "one policy choice among many."

Observable policies it's baking in:
- One role source is authoritative (no multi-source resolution)
- Roles are not permission-specific (you fetch "all roles" once, not "roles-for-this-endpoint")
- Roles are not time-dependent (you can't say "during this time window use these roles")
- Roles are not checker-dependent (all checkers see the same roles)
- Role freshness is a request-level concern (not per-endpoint or per-permission)

**The visibility:** By trying to make caching "more sophisticated" with TTL, we've exposed that we're not actually solving the architectural problem—we're just adding knobs to a broken assumption. The real issue becomes visible: the architecture allows for *exactly one* role resolution strategy, globally, for all requests, for all users, based only on identity.id, and we're pretending that's a technical detail rather than a design choice.

---

## The Diagnosis

**What the code is actually hiding:** Not that the cache has no TTL (surface problem—easy to fix). Rather, that the entire authorization model is baked in and invisible—roles as identity properties, lookup as post-processing, caching as global and static. The code makes this look like architecture when it's actually policy.

**What the "improvement" reveals:** By trying to fix caching, we had to concretize what "proper caching" means, which exposed that the caching can never be "proper" because the cache key strategy is wrong for the actual problem domain.
