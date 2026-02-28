# Structural Autopsy of an Auth Middleware

## The Claim (Specific, Falsifiable)

**The deepest structural problem is that the authentication pipeline conflates identity establishment, claim accumulation, and authorization decision into a si    -> Done (161s) -> 375 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/opus_L11_acceptance_design_task_H.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
tly overwrite earlier ones. A denier doesn't know if identity was established.

**Attacker:** This is a standard middleware pattern — the flexibility *is the point*. The real problem isn't conflation; it's the **inconsistent return types**: `request` object on success, `dict` on failure. That polymorphism is what actually breaks callers.

**Prober (challenges what both assume):** Both assume the *chain* is the unit of analysis. But the real issue may be that the *boundary between the middleware and its environment* is undefined. The code mutates `request.user` as a side effect, returns heterogeneous types, depends on a bare `fetch_roles` global, and maintains instance-level cache state with no eviction. The chain's internal design is a second-order problem; the first-order problem is that the middleware has no coherent contract with anything outside itself.

### The Claim Transforms

> The deepest structural problem is that **the middleware has no coherent boundary contract** — it communicates results through an unstable mix of return values (polymorphic), side effects (`request.user` mutation), and hidden state (role cache), meaning no caller or checker can establish pre- or post-conditions.

### The Diagnostic Gap

I initially looked *inside* the pipeline. The transformation pushed the problem *outward* to the boundary. This reveals that the internal complexity is a **symptom** of undefined external contracts — the pipeline became a bag of concerns because there was never a specification of what it should produce.

---

## The Concealment Mechanism

**Apparent composability.** The `add()` method and chain loop *look like* a well-designed plugin architecture. The `scope` parameter suggests thoughtful filtering. The `context` dict looks like a reasonable threading mechanism. This surface composability conceals:

- Chain order is semantically load-bearing but syntactically arbitrary
- `claims.update()` silently overwrites without conflict detection
- Return type bifurcation makes callers guess their way through results
- The role cache lives at the wrong abstraction level (instance state, no TTL, no eviction)
- Bypass routes create a completely separate code path with different invariants

---

## Improvement #1: Deepen the Concealment (Passes Review)

Add lifecycle hooks and a `phase` parameter — looks like separation of concerns:

```python
class AuthMiddleware:
    def __init__(self):
        self._chain = []
        self._bypass_routes = set()
        self._role_cache = {}
        self._hooks = {"pre_auth": [], "post_auth": [], "on_deny": []}

    def add(self, checker_fn, scope="all", phase="auth"):
        self._chain.append({"fn": checker_fn, "scope": scope, "phase": phase})

    def on(self, event, handler):
        self._hooks[event].append(handler)

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return request

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
                return {"status": 403, "error": result["reason"]}
            context["claims"].update(result.get("claims", {}))
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

        for hook in self._hooks["post_auth"]:
            hook(context)

        request.user = {**context["identity"], **context["claims"]}
        return request
```

A reviewer sees: *"Good — hooks for observability, phases for organization."* But `phase` is **decorative metadata never used in the loop**. The hooks add more mutation points to the shared context with less traceability.

### Three Properties Visible Only Because I Tried to Strengthen Concealment

1. **The phase parameter exposes that the chain has no phase semantics.** Adding it revealed there's no mechanism to enforce ordering or grouping. The loop ignores `phase` entirely.

2. **The hooks reveal that `context` is a de facto mutable global.** Adding pre/post hooks that also mutate `context` shows that *anyone* can write *anything* at *any time*. The hooks just add more uncoordinated writers.

3. **The `on_deny` hook reveals the error path is structurally different from the success path.** Denial returns immediately — `post_auth` never fires. The two paths have fundamentally different observability. The system cannot uniformly audit outcomes.

---

## Improvement #2: Contradicts #1 (Also Passes Review)

Instead of adding extension points, *tighten* the contract with immutability and types:

```python
from dataclasses import dataclass, field
from typing import Optional, Dict

@dataclass(frozen=True)
class AuthIdentity:
    id: str
    provider: str

@dataclass(frozen=True)
class AuthResult:
    identity: Optional[AuthIdentity] = None
    claims: Dict = field(default_factory=dict)
    denied: bool = False
    reason: str = ""

class AuthMiddleware:
    def __init__(self, checkers, bypass_routes=frozenset()):
        self._chain = tuple(checkers)       # immutable
        self._bypass_routes = bypass_routes  # immutable
        self._role_cache = {}

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return request

        identity = None
        claims = {}

        for scope, checker_fn in self._chain:
            if scope != "all" and scope != request.method:
                continue
            result: AuthResult = checker_fn(request)  # no shared context
            if result.denied:
                return {"status": 403, "error": result.reason}
            claims.update(result.claims)
            if result.identity:
                identity = result.identity

        if identity is None:
            return {"status": 401, "error": "No identity established"}

        cache_key = identity.id
        if cache_key in self._role_cache:
            claims["roles"] = self._role_cache[cache_key]
        else:
            roles = fetch_roles(identity)
            self._role_cache[cache_key] = roles
            claims["roles"] = roles

        request.user = {"id": identity.id, "provider": identity.provider, **claims}
        return request
```

This **strengthens what #1 weakened**: removes shared mutable context, types the results, makes the chain immutable. But it **weakens what #1 strengthened**: no extensibility, no lifecycle hooks, no runtime observability.

### The Structural Conflict

**Observability requires shared mutable state; safety requires its absence.**

Both improvements are legitimate because auth middleware genuinely needs both: you need to audit/intercept/extend the pipeline (hooks), AND you need to guarantee checkers can't corrupt each other's state (immutability). The conflict exists *only because both are legitimate*.

---

## Improvement #3: Resolve the Conflict via Event Sourcing

Checkers emit immutable events; the pipeline reduces them; observers watch without mutating:

```python
@dataclass(frozen=True)
class AuthEvent:
    kind: str          # "identity", "claim", "deny"
    payload: dict

@dataclass(frozen=True)
class AuthState:
    identity: Optional[dict] = None
    claims: dict = field(default_factory=dict)
    denied: bool = False
    deny_reason: str = ""
    events: tuple = ()

    def apply(self, event: AuthEvent) -> 'AuthState':
        new_events = self.events + (event,)
        if event.kind == "deny":
            return AuthState(self.identity, self.claims,
                             True, event.payload.get("reason", ""), new_events)
        if event.kind == "identity":
            return AuthState(event.payload, self.claims,
                             False, "", new_events)
        if event.kind == "claim":
            return AuthState(self.identity, {**self.claims, **event.payload},
                             False, "", new_events)
        return AuthState(self.identity, self.claims,
                         self.denied, self.deny_reason, new_events)

class AuthMiddleware:
    def __init__(self, checkers, bypass_routes=frozenset(), observers=()):
        self._chain = checkers
        self._bypass_routes = bypass_routes
        self._observers = observers
        self._role_cache = {}

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            return AuthSuccess({"role": "anonymous", "permissions": []})

        state = AuthState()
        for scope, checker_fn in self._chain:
            if scope != "all" and scope != request.method:
                continue
            for event in checker_fn(request, state):
                state = state.apply(event)
                for obs in self._observers:
                    obs(event, state)  # read-only observation
            if state.denied:
                return {"status": 403, "error": state.deny_reason}

        if state.identity is None:
            return {"status": 401, "error": "No identity established"}

        # role resolution still here...
        cache_key = state.identity["id"]
        roles = self._role_cache.get(cache_key) or self._fetch_and_cache(state.identity)
        state = state.apply(AuthEvent("claim", {"roles": roles}))

        request.user = {**state.identity, **state.claims}
        return request
```

### How It Fails

**Four independent failures:**

1. **Checkers receive `state` and can read it**, reintroducing implicit coupling. Immutability is real at the data level but illusory at the *semantic* level — checkers still branch on what predecessors did.

2. **The role cache still lives on the instance.** Event sourcing handles within-request state beautifully but cannot absorb cross-request caching. The cache is a different *temporal concern* and no single-request event model captures it.

3. **The return type is still polymorphic** — `request` vs `dict`. Event sourcing fixes the *internal* pipeline but cannot resolve the *boundary* contract because that problem lives in the relationship between this component and its caller.

4. **The cost is disproportionate.** This is now significantly more complex for a middleware most teams call with 2–3 checkers.

### What the Failure Reveals

The conflict suggested the problem was a **two-dimensional tension**: mutability vs. observability. The failure reveals the real topology: **three independent axes** — intra-request pipeline safety, cross-request state management, and boundary contract coherence — **that cannot be unified under a single abstraction**. Event sourcing perfectly serves axis 1, is irrelevant to axis 2, and cannot address axis 3. The feasible region contains no point that simultaneously optimizes all three.

---

## The Fourth Construction: Acceptance Design

Stop fighting. Accept that three concerns need three components. The middleware becomes a thin coordinator, not an engine:

```python
from dataclasses import dataclass
from typing import Protocol, Optional

# ── Axis 3: Boundary contract (defined first — it's the real API) ──

@dataclass(frozen=True)
class AuthSuccess:
    user: dict

@dataclass(frozen=True)
class AuthFailure:
    status: int
    error: str

AuthOutcome = AuthSuccess | AuthFailure  # callers MUST handle both


# ── Axis 1: Pipeline phases (protocols, not a chain) ──

class Authenticator(Protocol):
    def identify(self, request) -> Optional[dict]: ...

class ClaimSource(Protocol):
    def claims_for(self, identity: dict, request) -> dict: ...

class AccessPolicy(Protocol):
    def check(self, identity: dict, claims: dict, request) -> Optional[str]: ...


# ── Axis 2: Cross-request state (isolated, explicit lifetime) ──

class RoleResolver:
    def __init__(self, fetch_fn, cache_ttl=300):
        self._fetch = fetch_fn
        self._cache = {}
        self._timestamps = {}
        self._ttl = cache_ttl

    def roles_for(self, identity: dict) -> list[str]:
        key = identity["id"]
        now = _now()
        if key in self._cache and (now - self._timestamps[key]) < self._ttl:
            return self._cache[key]
        roles = self._fetch(identity)
        self._cache[key] = roles
        self._timestamps[key] = now
        return roles


# ── The coordinator ──

class AuthMiddleware:
    def __init__(
        self,
        authenticators: tuple[Authenticator, ...],
        claim_sources: tuple[ClaimSource, ...],
        policies: tuple[AccessPolicy, ...],
        role_resolver: RoleResolver,
        bypass_routes: frozenset[str] = frozenset(),
    ):
        self._authenticators = authenticators
        self._claim_sources = claim_sources
        self._policies = policies
        self._role_resolver = role_resolver
        self._bypass_routes = bypass_routes

    def authenticate(self, request) -> AuthOutcome:
        if request.path in self._bypass_routes:
            return AuthSuccess(user={"role": "anonymous", "permissions": []})

        # Phase 1: Identity (first match wins)
        identity = None
        for authn in self._authenticators:
            identity = authn.identify(request)
            if identity is not None:
                break

        if identity is None:
            return AuthFailure(401, "No identity established")

        # Phase 2: Claims (all contribute)
        claims = {}
        for source in self._claim_sources:
            claims.update(source.claims_for(identity, request))
        claims["roles"] = self._role_resolver.roles_for(identity)

        # Phase 3: Policy (first denial wins)
        for policy in self._policies:
            reason = policy.check(identity, claims, request)
            if reason is not None:
                return AuthFailure(403, reason)

        return AuthSuccess(user={**identity, **claims})
```

### What It Sacrifices

1. **Single-checker flexibility.** You can no longer write one function that authenticates, adds claims, and authorizes. If a concern spans phases, you split it across protocols.
2. **Dynamic pipeline modification.** No `add()`. The pipeline is fixed at construction.
3. **The context-passing pattern.** Authenticators can't see claims. Policies can't add identity. Information flows strictly downhill through the phases.
4. **Mid-pipeline denial before identity.** In the original, a checker could deny before identity was established. Here, denial only happens in the policy phase after identity and claims are resolved.

### What Was Never a Flaw

**The original's `claims.update()` overwrite behavior** — where later checkers silently overwrote earlier claims — looked like a bug. The redesign reveals it was **the cost of allowing a single undifferentiated pipeline to serve three roles simultaneously.** In a system where one function can be authenticator, claim source, and policy enforcer at once, overwriting is how later stages *refine* earlier stages' incomplete work. It's not accidental corruption; it's the only possible semantics for a pipeline that doesn't distinguish "tentatively establishing facts" from "authoritatively correcting facts." Once you separate the phases, the overwrite disappears — not because you fixed it, but because the concept it expressed *no longer exists*.

**The polymorphic return type** — returning either a request object or an error dict — looked like a type error. But it was the honest expression of a system that couldn't commit to an outcome until it was finished. When authentication, claims, and policy are unified, the system genuinely doesn't know whether it's producing a result or an error at any intermediate point. The mixed return type was *structurally honest*. The redesign eliminates it with `AuthOutcome` — but only because separated phases make the error points structurally predictable.

**The original's surface defects were load-bearing.** They were the honest costs of a design that attempted to unify three orthogonal concerns into one. Removing them required accepting that the concerns *are* separate — which is not a fix, but a different set of trade-offs.
