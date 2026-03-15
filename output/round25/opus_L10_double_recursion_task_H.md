# Structural Diagnosis: Double Recursion

## The Claim (Specific, Falsifiable)

> **The deepest structural problem is not the chain, the cache, or any single bug — it is that `authenticate` encodes three semantically distinct outcomes (authenticated, bypassed-anonymous, denied) into an ambiguous return type, and every internal mechanism (bypass set, chain, role cache) exists to compensate for the absence of an explicit outcome distinction.**

Falsifiable: if you can show that the caller can structurally distinguish all three outcomes without inspecting return value internals, the claim is wrong.

---

## Three Experts Stress-Test the Claim

**Defender:** The claim holds. On success, you get a `request` object. On bypass, you get a `request` object. On denial, you get a `dict`. The caller must do `isinstance` or key-checking to distinguish success from failure, and *cannot distinguish* success from bypass at all. This is a security-relevant ambiguity — downstream code treats an anonymous-bypass user identically to a fully-authenticated user.

**Attacker:** The real problem is more mundane. The `_role_cache` is an unbounded dict with no TTL — revoked roles persist forever. The `claims.update()` allows later checkers to silently overwrite earlier claims, including security-critical ones like `roles`. The return type is sloppy, but it's not the *deepest* problem; it's the cache-as-implicit-authorization-state that's dangerous.

**Probing what both assume:** Both experts assume the `authenticate` method is the correct unit of analysis. But the function does four things: routing bypass, identity establishment, claim accumulation, and role fetching with caching. The return type ambiguity is a *symptom* of the fact that this function has no single responsibility. The attacker's cache concern and the defender's return type concern are both consequences of a function that doesn't know what it is.

### Transformed Claim

> **The function's incoherent return type is a projection of its incoherent responsibility boundary. The four concerns (bypass, identity, claims, role-caching) are entangled in shared mutable state (`context` dict), and the return type ambiguity is what makes this entanglement invisible to callers.**

The gap between original and transformed claim: I initially located the problem at the *interface*. The transformation reveals it's at the *responsibility boundary*, with the interface merely being the surface where the entanglement becomes visible.

---

## The Concealment Mechanism

**Name: Type Pun as Implicit Success**

By returning the `request` object for both "authenticated" and "bypassed," the code *puns* two semantically different types into one runtime type. The caller reads "I got a request back" as "proceed normally." This hides:
1. That bypass users were never validated
2. That the `request.user` dict has different shapes depending on path taken
3. That an anonymous bypass user gets `permissions: []` but no `roles` key, while an authenticated user gets `roles` but no `permissions` key

---

## Improvement #1: Legitimate-Looking, Concealment-Deepening

This would pass code review. It "fixes" the return type:

```python
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class AuthResult:
    authenticated: bool
    user: Dict
    denied: bool = False
    error: Optional[str] = None
    status_code: int = 200

class AuthMiddleware:
    def __init__(self):
        self._chain = []
        self._bypass_routes = set()
        self._role_cache = {}

    def add(self, checker_fn, scope="all"):
        self._chain.append({"fn": checker_fn, "scope": scope})

    def bypass(self, route):
        self._bypass_routes.add(route)

    def authenticate(self, request) -> AuthResult:
        if request.path in self._bypass_routes:
            return AuthResult(
                authenticated=True,  # <-- THE DEEPENED CONCEALMENT
                user={"role": "anonymous", "permissions": []},
            )

        context = {"request": request, "identity": None, "claims": {}}

        for checker in self._chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            result = checker["fn"](context)
            if result.get("denied"):
                return AuthResult(
                    authenticated=False, denied=True,
                    error=result["reason"], status_code=403
                )
            context["claims"].update(result.get("claims", {}))
            if result.get("identity"):
                context["identity"] = result["identity"]

        if context["identity"] is None:
            return AuthResult(
                authenticated=False, error="No identity established",
                status_code=401
            )

        cache_key = context["identity"]["id"]
        if cache_key in self._role_cache:
            context["claims"]["roles"] = self._role_cache[cache_key]
        else:
            roles = fetch_roles(context["identity"])
            self._role_cache[cache_key] = roles
            context["claims"]["roles"] = roles

        return AuthResult(
            authenticated=True,
            user={**context["identity"], **context["claims"]},
        )
```

**Why it passes review:** It introduces a proper result type, eliminates the polymorphic return, adds type hints. It looks like a clear improvement.

**Why it deepens concealment:** The bypass path now returns `authenticated=True`. The type pun is *formalized*. Before, a careful reader might notice the return type inconsistency and ask "wait, is bypass really the same as authentication?" Now, the `AuthResult` dataclass *asserts* that they are the same. The ambiguity is no longer accidental — it's encoded in the schema.

### Three Properties Visible Only Because We Tried to Strengthen

1. **The `authenticated` boolean is underdetermined.** Bypass users are not "authenticated" — they're "exempted." The improvement forces a binary where three states exist, revealing the boolean was always the wrong abstraction.

2. **The `user` dict remains structurally inconsistent.** Bypass: `{"role": ..., "permissions": [...]}`. Authenticated: `{"id": ..., "roles": [...], ...}`. The `AuthResult` wrapper makes this *harder* to see because `user: Dict` conceals the schema divergence.

3. **The cache is now further from its invalidation surface.** By cleaning up the return path, we've made the function *look* more correct, which reduces the probability that a reviewer scrutinizes the `_role_cache` — which still has no TTL, no size bound, and no invalidation mechanism.

---

## Diagnose the Improvement: What Does It Conceal?

Improvement #1 conceals that **`authenticated=True` is being used to encode two unrelated states** (identity-verified and route-exempted). The property of the original problem that the improvement *recreates* is:

> **A single field is doing double duty as both an identity assertion and a routing decision.**

In the original, the `request` object was the overloaded carrier. Now `authenticated: bool` is. The structural shape is identical — the name changed, the problem didn't.

---

## Improvement #2: Address the Recreated Property

```python
from dataclasses import dataclass
from typing import Optional, Dict
from enum import Enum

class AuthOutcome(Enum):
    AUTHENTICATED = "authenticated"
    BYPASSED = "bypassed"
    DENIED = "denied"
    NO_IDENTITY = "no_identity"

@dataclass(frozen=True)
class AuthResult:
    outcome: AuthOutcome
    user: Optional[Dict] = None
    error: Optional[str] = None
    status_code: int = 200

class AuthMiddleware:
    def __init__(self, role_provider, cache_ttl=300):
        self._chain = []
        self._bypass_routes = set()
        self._role_provider = role_provider
        self._role_cache = TTLCache(ttl=cache_ttl)

    def add(self, checker_fn, scope="all"):
        self._chain.append({"fn": checker_fn, "scope": scope})

    def bypass(self, route):
        self._bypass_routes.add(route)

    def authenticate(self, request) -> AuthResult:
        # Phase 1: Bypass (explicit, distinct outcome)
        if request.path in self._bypass_routes:
            return AuthResult(
                outcome=AuthOutcome.BYPASSED,
                user={"role": "anonymous", "permissions": []},
            )

        # Phase 2: Identity establishment
        context = {"request": request, "identity": None, "claims": {}}
        for checker in self._chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            result = checker["fn"](context)
            if result.get("denied"):
                return AuthResult(
                    outcome=AuthOutcome.DENIED,
                    error=result["reason"], status_code=403,
                )
            context["claims"].update(result.get("claims", {}))
            if result.get("identity"):
                context["identity"] = result["identity"]

        if context["identity"] is None:
            return AuthResult(
                outcome=AuthOutcome.NO_IDENTITY,
                error="No identity established", status_code=401,
            )

        # Phase 3: Role enrichment (separated concern)
        roles = self._role_cache.get_or_set(
            context["identity"]["id"],
            lambda: self._role_provider(context["identity"]),
        )
        context["claims"]["roles"] = roles

        return AuthResult(
            outcome=AuthOutcome.AUTHENTICATED,
            user={**context["identity"], **context["claims"]},
        )
```

### Diagnose Improvement #2

**What does this still conceal?** The `claims.update()` call remains. Checkers in the chain can still silently overwrite each other's claims, including `roles`. The `context` dict is still shared mutable state threaded through the chain. Phase 2 *looks* like a clean pipeline but is actually an order-dependent mutation sequence where any checker can sabotage any other.

**The recreated property:** The chain itself is a concealment mechanism. Each checker appears independent (it's "just a function in a list") but is actually coupled to every other checker through shared mutable context. The enum fixed the *output* ambiguity. The *internal* ambiguity — that the chain conflates identity establishment and authorization checking and claim accumulation into a single untyped loop — persists.

---

## The Structural Invariant

> **Every improvement relocates the ambiguity between "who is this entity" (identity), "what may this entity do" (authorization), and "should we even check" (routing) — but cannot eliminate it, because the code's responsibility boundary encompasses all three, and they are fundamentally distinct temporal phases being compressed into a single synchronous call.**

This is a property of the **problem space**, not the implementation:
- Identity is established *once* (at authentication time)
- Authorization is checked *per-resource* (at access time)  
- Bypass is decided *before either* (at routing time)

No single `authenticate()` method can correctly unify these three because they occur at different points in a request's lifecycle. Every refactoring of this function will rediscover this invariant — the three concerns will couple through whatever shared state the refactoring introduces, because the function's signature promises to resolve all three simultaneously.

The structural invariant is: **temporal phase compression is preserved through every improvement because the method boundary itself encodes it.**
