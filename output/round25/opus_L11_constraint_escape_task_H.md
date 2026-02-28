# Structural Diagnostic: Auth Middleware Chain

## The Claim

**The deepest structural problem: authentication (identity) and authorization (permissions) are fused into a single sequential chain sharing a mutable context dict, making it impo    -> Done (157s) -> 350 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/opus_L11_constraint_escape_task_H.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
is accidental — order-dependent, not semantically guaranteed.

**Attacker:** Overstated. The code already has implicit phasing: chain runs first, then identity is checked, then roles are fetched. The *actual* deepest problem is the **polymorphic return type** — `authenticate` returns either a `request` object or a `dict` with `status`/`error`. This makes the middleware uncomposable. Every downstream caller must type-check the return. The authn/authz conflation is a smell; the return type is what actually breaks composition.

**Prober (questioning both):** Both assume the chain is the unit of analysis. But step back: `_chain`, `_bypass_routes`, and `_role_cache` are all mutable instance state. This object conflates **configuration** (what checkers exist, what's bypassed), **application-lifetime state** (the role cache), and **per-request computation** (the `authenticate` call). Three temporal scopes collapsed into one `self`. The return type problem and the authn/authz problem are both symptoms of this temporal collapse.

## Transformed Claim

> The deepest structural problem is the collapse of three temporal scopes — **configuration-time** (chain composition, bypass routes), **application-lifetime** (role cache), and **request-lifetime** (context/identity resolution) — into a single mutable object, making every apparent sub-problem structurally irresolvable because fixes to one scope necessarily entangle the others.

**Diagnostic gap:** I initially analyzed *what the code means* (authn vs authz). The real problem is *when each part of the code is supposed to be valid*. Semantic analysis missed temporal analysis.

---

## The Concealment Mechanism

**Name: Sequential Plausibility.**

The code reads top-to-bottom as a compelling narrative: *check bypass → run checkers → verify identity → fetch roles → compose user*. This conceals the temporal collapse because the reader experiences a single clean timeline when the code actually interleaves three distinct lifecycles. The `for` loop especially conceals — it looks like iteration but is actually **accretion of untyped mutable state across an implicit protocol**.

---

## Improvement 1: Strengthen the Concealment

*This passes code review. It adds "lifecycle hooks," a "phase" concept, and cleaner return tuples:*

```python
class AuthMiddleware:
    def __init__(self):
        self._chain = []
        self._bypass_routes = set()
        self._role_cache = {}
        self._hooks = {"pre_auth": [], "post_auth": [], "on_deny": []}

    def add(self, checker_fn, scope="all", phase="auth"):
        self._chain.append({"fn": checker_fn, "scope": scope, "phase": phase})

    def bypass(self, route):
        self._bypass_routes.add(route)

    def on(self, hook_name, fn):
        self._hooks[hook_name].append(fn)

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return True, request

        context = {"request": request, "identity": None, "claims": {}}

        for hook in self._hooks["pre_auth"]:
            hook(context)

        for checker in self._chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            result = checker["fn"](context)
            if result.get("denied"):
                for hook in self._hooks["on_deny"]:
                    hook(context, result)
                return False, {"status": 403, "error": result["reason"]}
            context["claims"].update(result.get("claims", {}))
            if result.get("identity"):
                context["identity"] = result["identity"]

        if context["identity"] is None:
            return False, {"status": 401, "error": "No identity established"}

        cache_key = context["identity"]["id"]
        if cache_key in self._role_cache:
            context["claims"]["roles"] = self._role_cache[cache_key]
        else:
            roles = fetch_roles(context["identity"])
            self._role_cache[cache_key] = roles
            context["claims"]["roles"] = roles

        for hook in self._hooks["post_auth"]:
            hook(context)

        request.user = {**context["identity"], **context["claims"]}
        return True, request
```

**Why this deepens concealment:** The hooks create the *appearance* of lifecycle separation while adding *more mutation points* to the same collapsed object. The `phase` parameter on `add()` is never used in `authenticate` — it's dead metadata that signals phased execution without implementing it. Reviewers see "extensibility" and "separation of concerns."

### Three Properties Visible Only Because I Tried to Strengthen

1. **`context` is the coupling bottleneck.** Every hook and checker needs it. It's request-scoped data accessed via a configuration-scoped method. Hooks can't compose independently because they all share this mutable bag.

2. **The cache is unscopeable.** Adding `post_auth` hooks reveals `_role_cache` can never be correctly invalidated — it lives at application-lifetime but is populated by request-lifetime data. No hook bridges that gap.

3. **The return type bifurcation is load-bearing.** Even the tuple return has two fundamentally different shapes. This reflects the middleware not knowing whether it's a *filter* (pass/reject) or a *transformer* (enrich request). Hooks can't resolve this because hooks can't change what the method *is*.

---

## Recursive Diagnostic on Improvement 1

**What it conceals:** That `context` is an untyped, unscoped protocol. Hooks make it look like there are phases, but `context` flows through all of them identically.

**What property of the original it recreates:** The identity-before-authorization ordering problem. Hooks can now *also* mutate identity during `pre_auth`, making it worse. The structural dependency (authorization depends on identity) remains an implicit convention, not an enforced invariant.

## Improvement 2: Address the Ordering Problem

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List

@dataclass(frozen=True)
class Identity:
    id: str
    provider: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class AuthResult:
    identity: Optional[Identity] = None
    claims: Dict[str, Any] = field(default_factory=dict)
    denied: bool = False
    reason: str = ""

class AuthMiddleware:
    def __init__(self):
        self._authenticators: List[dict] = []   # establish identity
        self._authorizers: List[dict] = []       # check permissions
        self._bypass_routes: set = set()
        self._role_cache: Dict[str, list] = {}

    def add_authenticator(self, fn, scope="all"):
        self._authenticators.append({"fn": fn, "scope": scope})

    def add_authorizer(self, fn, scope="all"):
        self._authorizers.append({"fn": fn, "scope": scope})

    def bypass(self, route):
        self._bypass_routes.add(route)

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return True, request

        # Phase 1: Identity — only authenticators run
        identity = None
        for authn in self._authenticators:
            if authn["scope"] != "all" and authn["scope"] != request.method:
                continue
            result = authn["fn"](request)
            if result.identity:
                identity = result.identity
                break

        if identity is None:
            return False, {"status": 401, "error": "No identity established"}

        # Phase 2: Enrichment — role cache
        cache_key = identity.id
        if cache_key in self._role_cache:
            claims = {"roles": self._role_cache[cache_key]}
        else:
            roles = fetch_roles(identity)
            self._role_cache[cache_key] = roles
            claims = {"roles": roles}

        # Phase 3: Authorization — identity guaranteed to exist
        for authz in self._authorizers:
            if authz["scope"] != "all" and authz["scope"] != request.method:
                continue
            result = authz["fn"](identity, claims, request)
            if result.denied:
                return False, {"status": 403, "error": result.reason}

        request.user = {**identity.__dict__, **claims}
        return True, request
```

This explicitly separates authenticators from authorizers, uses frozen dataclasses, enforces that identity exists before authorization runs, and gives each phase only the data it needs.

## Recursive Diagnostic on Improvement 2

**What it conceals:** The role cache is still application-lifetime state on a configuration-time object. `_role_cache` grows unboundedly, has no TTL, no invalidation, is not thread-safe. The explicit phases make this *harder* to see because the code now *looks* well-structured — Sequential Plausibility is **stronger** than in the original.

**What persists:** The middleware still combines configuration mutation (`add_authenticator`, `bypass`) with request processing (`authenticate`) and lifetime state (`_role_cache`) on a single `self`. The three temporal scopes still share a mutation boundary.

---

## The Structural Invariant

> **A single object holds configuration, runtime cache, and request processing logic, forcing all three temporal scopes to share a mutation boundary.**

This persists through every improvement because it is a property of the *problem framing* — "middleware as object" — not any implementation. As long as the design unit is "an object you configure and then call," `self` collapses deploy-time and request-time, and any cache necessarily lives at the wrong scope.

## The Category Boundary

**Category: Stateful Middleware Objects** — designs where a single configured entity processes requests and manages its own state.

---

## The Adjacent Category: Composed Functions with Injected Scopes

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, Tuple, FrozenSet
import time

# === Configuration-time (frozen at deploy, immutable) ===

@dataclass(frozen=True)
class AuthConfig:
    bypass_routes: FrozenSet[str]
    authenticators: Tuple[Callable, ...]   # Request -> Optional[Identity]
    authorizers: Tuple[Callable, ...]      # (Identity, Claims, Request) -> Optional[Denial]

# === Request-scoped types (created and destroyed per-request) ===

@dataclass(frozen=True)
class Identity:
    id: str
    provider: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Denial:
    status: int
    reason: str

@dataclass(frozen=True)
class AuthenticatedRequest:
    original_request: Any
    identity: Identity
    claims: Dict[str, Any]

# === Application-lifetime (injected, independently lifecycled) ===

class RoleResolver:
    """Owns its own cache, TTL, invalidation, thread-safety."""
    def __init__(self, fetcher, ttl_seconds=300):
        self._fetcher = fetcher
        self._cache: Dict[str, Tuple[list, float]] = {}
        self._ttl = ttl_seconds

    def resolve(self, identity: Identity) -> list:
        now = time.time()
        if identity.id in self._cache:
            roles, ts = self._cache[identity.id]
            if now - ts < self._ttl:
                return roles
        roles = self._fetcher(identity)
        self._cache[identity.id] = (roles, now)
        return roles

    def invalidate(self, identity_id: str):
        self._cache.pop(identity_id, None)

# === The function: no self, no state ===

def authenticate(
    config: AuthConfig,
    role_resolver: RoleResolver,
    request: Any,
) -> AuthenticatedRequest | Denial:

    if request.path in config.bypass_routes:
        return AuthenticatedRequest(
            original_request=request,
            identity=Identity(id="anonymous", provider="bypass"),
            claims={"roles": [], "permissions": []},
        )

    # Phase 1: Identify
    identity = None
    for authn in config.authenticators:
        identity = authn(request)
        if identity is not None:
            break

    if identity is None:
        return Denial(status=401, reason="No identity established")

    # Phase 2: Enrich (via injected, independently-lifecycled resolver)
    roles = role_resolver.resolve(identity)
    claims = {"roles": roles}

    # Phase 3: Authorize (identity guaranteed to exist)
    for authz in config.authorizers:
        denial = authz(identity, claims, request)
        if denial is not None:
            return denial

    return AuthenticatedRequest(
        original_request=request,
        identity=identity,
        claims=claims,
    )
```

### How This Succeeds Where Every Improvement Failed

The invariant **dissolves** — no single object owns configuration, cache, and request processing:

| Temporal Scope | Original | Escaped Design |
|---|---|---|
| **Configuration-time** | Mutable `self._chain`, `self._bypass_routes` | `AuthConfig` — frozen, immutable |
| **Application-lifetime** | `self._role_cache` — unbounded, no TTL | `RoleResolver` — independent object, owns its TTL/invalidation |
| **Request-lifetime** | `context` dict mutated in-place | `AuthenticatedRequest \| Denial` — frozen return values |

The scopes cannot contaminate each other because **they are different types with different mutation boundaries**. You cannot accidentally add a checker at request-time because `AuthConfig` is frozen. You cannot accidentally share cache state because `RoleResolver` is injected, not owned. The return type `AuthenticatedRequest | Denial` is a proper discriminated union — no polymorphic dict-or-request ambiguity.

---

### The New Impossibility

**What was trivial in the original category but impossible in the escape:**

**Dynamic reconfiguration.** In the original `AuthMiddleware`, you could call `add()` or `bypass()` at any time — even mid-flight. A new checker could be hot-added. A route could be bypassed in response to a runtime signal. This was trivial because configuration and execution shared `self`.

In the escaped design, `AuthConfig` is frozen. Adding an authenticator requires constructing an entirely new config and propagating it through an explicit versioning mechanism (e.g., `AtomicReference[AuthConfig]`). The flexibility the original got "for free" now requires deliberate infrastructure.

---

## The Finding

```
┌─────────────────────────┬──────────────────────────┬─────────────────────────────────┐
│                         │ Stateful Middleware Object│ Composed Fns + Injected Scopes  │
├─────────────────────────┼──────────────────────────┼─────────────────────────────────┤
│ TRIVIAL                 │ Dynamic reconfiguration  │ Scope separation, cache          │
│                         │                          │ lifecycle, type safety,          │
│                         │                          │ composability, testability       │
├─────────────────────────┼──────────────────────────┼─────────────────────────────────┤
│ IMPOSSIBLE              │ Correct cache lifecycle, │ Dynamic reconfiguration          │
│                         │ scope separation,        │ without explicit versioning      │
│                         │ compositional reasoning  │ infrastructure                   │
└─────────────────────────┴──────────────────────────┴─────────────────────────────────┘
```

**The trade-off is not about better engineering. It is a category-level invariant:**

Designs where any component can reach any temporal scope through a shared reference are *inherently dynamically reconfigurable* and *inherently unverifiable*. Designs that separate temporal scopes into distinct types are *inherently verifiable* and *inherently rigid*.

The original middleware sits in the first category and conceals this through Sequential Plausibility — the code *reads* like a clean pipeline while *being* a shared mutable state bomb. Every improvement that stays in that category (hooks, phases, typed results) **strengthens the concealment without dissolving the invariant**. The escape dissolves the invariant by making temporal scopes into type boundaries — at the cost of making the once-trivial act of "just add a checker" into a coordination problem.
