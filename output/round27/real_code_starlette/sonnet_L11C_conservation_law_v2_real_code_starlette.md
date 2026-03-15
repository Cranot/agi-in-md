# Structural Analysis: Starlette Routing

---

## Initial Claim (Falsifiable)

**The deepest structural problem**: `scope` serves simultaneously as routing input, routing output, and inter-layer communication channel. Its mutation during routing is irreversible and non-transactional with respect to dispatch failure — the "two-phase" appearance of `matches()` → `handle()` is false, because context installation (`scope.update(child_scope)`) fires at match-commit time, not at dispatch time.

Falsifiable prediction: if the claim is wrong, then a handler exception after `scope.update()` should leave scope indistinguishable from pre-match state for the purposes of error handling. It does not.

---

## Three-Expert Dialectic

### Expert 1 (Defender): The claim holds

The mutation-before-dispatch structure is load-bearing in the wrong way:

```python
# Router.app() — mutation and dispatch are not transactional
scope.update(child_scope)          # ← state installed permanently
await route.handle(scope, receive, send)  # ← if this raises...
```

If `handle()` raises `HTTPException`, ASGI exception middleware receives a scope where `scope["endpoint"]` already points to the failed route, `scope["path_params"]` reflects the matched path, and `scope["root_path"]` has been modified by any intervening `Mount`. Error handlers that inspect scope see routing success where dispatch failed. In nested `Mount` composition, inner-router mutations flow into outer-layer exception handlers through the same mutable dict.

### Expert 2 (Attacker): Misidentification — the real problem is a hidden two-layer method negotiation protocol

The mutation timing is intentional ASGI design. The real problem is that `Match.PARTIAL` encodes a method-negotiation protocol that is **split across two methods**:

```python
# Route.matches() — produces PARTIAL when path matches but method doesn't
if self.methods and scope["method"] not in self.methods:
    return Match.PARTIAL, child_scope   # method check #1

# Route.handle() — re-checks method to produce 405
if self.methods and scope["method"] not in self.methods:  # method check #2
    raise HTTPException(status_code=405)
```

`matches()` and `handle()` are coupled by a shared understanding of what PARTIAL means that is invisible at the callsite. Override `handle()` in a subclass without knowing this protocol, and you corrupt the 405-before-404 priority ordering.

### Expert 3 (Prober): What both take for granted

Both experts assume the scope dict is the correct medium for routing context. Neither asks: *why is routing context (path_params, endpoint, root_path) in the same dict as transport context (type, headers, method)?*

The transport layer (ASGI) owns scope as an immutable-per-connection record. The routing layer writes into it because it has **no other mechanism to pass progressive path-stripping state through composable middleware boundaries.** Both claims — mutation timing and PARTIAL coupling — are symptoms of this.

The real concealed problem: the router has no first-class representation of a routing decision. `(Match, child_scope)` is a label plus a naked dict. The `Match` enum gives the appearance of a discriminated union, but `child_scope` carries heterogeneous, unstandardized updates that immediately disappear into scope via `.update()`.

---

## Transformation

**Original claim**: scope is mutated before dispatch; the timing is wrong.

**Transformed claim**: The routing system has no type that represents "a routing decision" as distinct from its side effects. `(Match, child_scope)` looks like a typed result but is two naked dicts with a categorical label. This makes routing decisions impossible to reason about, retry, or compose — they are constructed and then immediately destroyed.

**The gap**: I diagnosed *when* mutation happens. The dialectic reveals the problem is that there is **no clean model of a routing decision at all**. Matching, context-building, and installation are tangled because no type exists to carry a decision from production to consumption.

---

## The Concealment Mechanism

**The `Match` enum creates the appearance of a two-phase protocol that does not exist.**

The enum suggests:
- Phase 1: `route.matches(scope) → (Match, child_scope)` — pure discrimination
- Phase 2: `route.handle(scope, receive, send)` — effectful dispatch

This looks clean. But `child_scope` is untyped, `scope.update()` fires between the phases with no rollback mechanism, and `handle()` re-reads scope state that was written by the "pure" phase. The protocol is not two-phase — it is one phase wearing two hats.

The concealment works because enums signal type discipline. A reader sees `Match.FULL` and infers that the system discriminates cleanly before committing. It does not.

---

## First Improvement: The Routing Decision Object (Passes Code Review, Deepens Concealment)

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

@dataclass
class RouteMatch:
    """
    First-class routing decision. Separates match evaluation from 
    context installation. Call .apply() to commit routing context 
    to scope before dispatch.
    """
    match: Match
    scope_updates: Dict[str, Any] = field(default_factory=dict)
    route: Optional['BaseRoute'] = None

    @property
    def is_full(self) -> bool:
        return self.match == Match.FULL

    @property
    def is_partial(self) -> bool:
        return self.match == Match.PARTIAL

    @property
    def is_none(self) -> bool:
        return self.match == Match.NONE

    def apply(self, scope: dict) -> None:
        """Commit routing context to scope. Call before dispatching."""
        scope.update(self.scope_updates)


# Route.matches() now returns RouteMatch
class Route(BaseRoute):
    def matches(self, scope) -> RouteMatch:
        if scope["type"] == "http":
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)
            if match:
                matched_params = {
                    k: self.param_convertors[k].convert(v)
                    for k, v in match.groupdict().items()
                }
                path_params = {**scope.get("path_params", {}), **matched_params}
                scope_updates = {"endpoint": self.endpoint, "path_params": path_params}
                if self.methods and scope["method"] not in self.methods:
                    return RouteMatch(Match.PARTIAL, scope_updates, route=self)
                return RouteMatch(Match.FULL, scope_updates, route=self)
        return RouteMatch(Match.NONE)


# Router.app() with RouteMatch
async def app(self, scope, receive, send):
    partial_match: Optional[RouteMatch] = None

    for route in self.routes:
        route_match = route.matches(scope)
        if route_match.is_full:
            route_match.apply(scope)             # ← named commit point
            await route.handle(scope, receive, send)
            return
        elif route_match.is_partial and partial_match is None:
            partial_match = route_match

    if partial_match is not None:
        partial_match.apply(scope)               # ← named commit point
        await partial_match.route.handle(scope, receive, send)
        return
    # ... redirect_slashes, default
```

**Why this passes code review**: adds type safety, names the commit operation, gives reviewers a `RouteMatch` class to inspect, adds readable boolean properties, and aligns with the "Result object" pattern familiar from other frameworks.

**Why it deepens concealment**:

1. `RouteMatch` *looks like* a routing decision object, but `apply()` still mutates scope non-reversibly at the same moment as before. The commit is named but not transactional.
2. The `route` back-reference field (`route: Optional['BaseRoute']`) looks like hygiene but reveals that you cannot use the match result without the original route — the decision is incomplete without the object that generated it.
3. `scope_updates: Dict[str, Any]` presents heterogeneous scope mutations (path_params vs root_path vs endpoint) as a uniform dict. The difference between Route-style and Mount-style updates, with their different reversibility properties, is now hidden behind a flat interface.

---

## Three Properties Visible Because We Tried to Strengthen It

**1. The apply/commit boundary is cosmetically named but structurally identical to before.**
Naming `scope.update()` as `.apply()` makes the mutation look deliberate and bounded. But it fires at the exact same point in execution. The improvement reveals that the original code's problem is not *unnamed mutation* but *mutation whose semantics cannot be inverted* — and naming it doesn't change that.

**2. The `route` back-reference on RouteMatch exposes that handle() re-queries scope.**
Adding `route=self` to every RouteMatch makes visible that to use a RouteMatch, you need both the match data AND the original route, because `Route.handle()` re-checks `scope["method"]` — information the route already evaluated during `matches()`. `RouteMatch` should carry a complete dispatch instruction but cannot, because `handle()` is a method on the route object that reads scope rather than its arguments.

**3. `scope_updates: Dict[str, Any]` conceals that Mount and Route install categorically different kinds of context.**
`Route.matches()` installs path_params and endpoint. `Mount.matches()` installs path_params, root_path, app_root_path, and endpoint-as-app. These have different semantics: endpoint is a display value; root_path is a URL-construction accumulator. Putting them all in one `Dict[str, Any]` makes the heterogeneity invisible. The improvement exposes this by forcing you to ask what `scope_updates` means — and discovering it means different things for different route types.

---

## Applying the Diagnostic to the Improvement

**What `RouteMatch` conceals**: that scope is still the sole communication channel between routing layers. When a `Mount` dispatches to an inner `Router`, that inner Router also calls `route_match.apply(scope)` on its matched routes. Multiple `.apply()` calls fire on the same dict at different nesting depths with no coordination. The clean `apply()` interface hides that context installation is not hierarchically isolated.

**What property of the original problem is visible only because RouteMatch recreates it**: The `handle()` method still re-checks `scope["method"]` after `apply()` has fired. This means matching and dispatch are not cleanly separated — the route is queried *twice*, once in `matches()` and once in `handle()`, and the `RouteMatch` between them does not carry the dispatch-ready instruction that would avoid the re-check. The object looks complete but isn't. The improvement recreates the original problem at a higher abstraction level: now you have a "routing decision object" that doesn't actually encode the routing decision.

---

## Second Improvement: Pre-resolved Handlers (Addresses Re-query)

```python
@dataclass
class RouteMatch:
    match: Match
    scope_updates: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None   # ← pre-resolved at match time

    def apply(self, scope: dict) -> None:
        scope.update(self.scope_updates)

    async def dispatch(self, scope, receive, send) -> None:
        """Atomically apply context and dispatch. No re-querying."""
        self.apply(scope)
        if self.handler is not None:
            await self.handler(scope, receive, send)


class Route(BaseRoute):
    async def _send_405(self, scope, receive, send):
        headers = {"Allow": ", ".join(self.methods)}
        if "app" in scope:
            raise HTTPException(status_code=405, headers=headers)
        response = PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
        await response(scope, receive, send)

    def matches(self, scope) -> RouteMatch:
        if scope["type"] == "http":
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)
            if match:
                matched_params = {
                    k: self.param_convertors[k].convert(v)
                    for k, v in match.groupdict().items()
                }
                path_params = {**scope.get("path_params", {}), **matched_params}
                scope_updates = {"endpoint": self.endpoint, "path_params": path_params}
                if self.methods and scope["method"] not in self.methods:
                    return RouteMatch(Match.PARTIAL, scope_updates,
                                      handler=self._send_405)         # ← pre-resolved
                return RouteMatch(Match.FULL, scope_updates,
                                  handler=self.app)                   # ← pre-resolved
        return RouteMatch(Match.NONE)

    async def handle(self, scope, receive, send):
        # handle() no longer re-checks methods — handler is pre-resolved
        if self.methods and scope["method"] not in self.methods:
            await self._send_405(scope, receive, send)
        else:
            await self.app(scope, receive, send)
```

**Applying the diagnostic to the second improvement**:

`handler=self._send_405` pre-resolves response logic at match time. This eliminates the re-query of `scope["method"]` in `handle()`. But it reveals something new: **response generation logic (`_send_405`) is now leaking into the matching phase.** `matches()` was supposed to be a pure discrimination function. It now needs to know what to *send* over the network — it constructs a callable that has HTTP-layer semantics. The routing layer and the response layer are now coupled at the point of discrimination.

For `Mount`, pre-resolving `handler=self.app` only captures a reference to the same mutable `Router` object. Routing decisions made at match time capture no snapshot of routing state — they just hold a pointer. If routes are added or removed between match and dispatch (admittedly rare, but possible in test contexts), the pre-resolved handler is stale. The "complete routing decision" is still incomplete.

**The recreated property**: Capturing `self.app` as the handler for a Match.FULL RouteMatch captures the *current* app reference, which for a Mount is a Router with a mutable `routes` list. The handler carries the illusion of a complete dispatch plan, but because the Router it points to is mutable, the plan is not a snapshot — it's a pointer into a live system. The RouteMatch's dispatch plan is only as stable as the object graph it references.

---

## The Structural Invariant

Through every improvement, the following property persists:

> **In a hierarchically composed routing system where each layer strips path prefix and passes enriched context to children, some layer must accumulate and install progressive path-parsing state before delegating. Since ASGI's calling convention `(scope, receive, send)` provides no parameter other than scope for inter-layer communication, scope mutation during routing is not a bug to be fixed — it is a consequence of the protocol.**

The invariant is not "mutation happens" but: **progressive context enrichment in a composable hierarchy with a fixed calling convention must mutate shared state. The complexity of this enrichment cannot be eliminated, only relocated.**

---

## Inverting the Invariant

**The impossible property**: scope context is installed before dispatch.
**Inverted design**: scope context is installed lazily, on-demand, during dispatch.

```python
@dataclass(frozen=True)
class ResolvedRoute:
    """Immutable routing decision. Contains everything needed for dispatch."""
    path_params: Dict[str, Any]
    root_path: str
    endpoint: Any
    handler: Callable
    matched_path: str

class RoutingContext:
    """
    Wraps the immutable base scope with resolved routing context.
    Presented as a dict-like to downstream handlers.
    Base scope is never mutated.
    """
    def __init__(self, base_scope: dict, resolved: ResolvedRoute):
        self._base = base_scope
        self._resolved = resolved
        self._overlay = {
            "path_params": resolved.path_params,
            "root_path": resolved.root_path,
            "endpoint": resolved.endpoint,
        }

    def __getitem__(self, key):
        return self._overlay.get(key, self._base[key])

    def get(self, key, default=None):
        return self._overlay.get(key, self._base.get(key, default))

    def __contains__(self, key):
        return key in self._overlay or key in self._base

    def __setitem__(self, key, value):
        # Inner layers may write — isolated to this context
        self._overlay[key] = value

    def copy(self) -> dict:
        return {**self._base, **self._overlay}

# Pure routing function — no scope mutation
def resolve(routes, scope: dict) -> Optional[ResolvedRoute]:
    for route in routes:
        result = route.try_resolve(scope)
        if result is not None:
            return result
    return None

# Dispatch uses RoutingContext, never touches original scope
async def dispatch(resolved: ResolvedRoute, base_scope: dict, receive, send):
    ctx = RoutingContext(base_scope, resolved)
    await resolved.handler(ctx, receive, send)
```

---

## The New Impossibility

**The inverted design creates**: When `Mount` dispatches to an inner ASGI app (a `Router`, or any third-party ASGI middleware), that app receives a `RoutingContext` — a proxy object — instead of a plain dict. **All existing ASGI middleware in the ecosystem expects a plain dict.** Every `Mount` that wraps a non-Router ASGI app must unwrap `RoutingContext` back into a plain dict via `.copy()`, and at that moment, the mutation-before-dispatch problem returns — the copy is the new scope, and it is mutated by whatever inner middleware runs.

The clean routing design creates an **incompatibility boundary**: you either speak plain-scope ASGI (composable with the ecosystem, routing-impure) or RoutingContext-ASGI (routing-pure, incompatible with the ecosystem). The adapter at every Mount-to-plain-ASGI boundary re-creates the original problem, now hidden inside the adapter.

Additionally: `RoutingContext.__setitem__` allows inner layers to write to the overlay. But if two sibling Mounts need to write to the same key (e.g., both contribute to `path_params`), who owns the overlay? The mutable-overlay problem is the scope-mutation problem, reborn inside the proxy.

---

## The Conservation Law

**Original impossibility**: You cannot separate routing decisions from scope mutation while preserving ASGI's plain-dict calling convention.

**Inverted impossibility**: If you separate routing decisions from scope mutation (via lazy RoutingContext), you cannot maintain ASGI middleware composability without creating an adapter layer that re-introduces scope mutation at the ecosystem boundary.

**The law**: *In any hierarchically composed request-processing system where layers communicate through a fixed protocol, the total complexity of "progressive context enrichment" is conserved. Routing purity and ecosystem composability are not independently achievable — complexity eliminated from one is recovered exactly in the other. The system can choose where this complexity lives, not whether it exists.*

---

## What This Reveals That a Senior Engineer Would Not Already Know

A senior engineer knows there is a purity/composability trade-off in routers. They do not know this:

**The `Match` enum is the mechanism by which the system disguises a conservation problem as a design choice.** By presenting routing as a two-phase protocol (`matches()` → `handle()`), Starlette creates the impression that the coupling between context installation and dispatch is a stylistic decision that could be differently organized. It is not. It is a consequence of ASGI's calling convention, and no reorganization within that convention eliminates it. The enum doesn't separate phases — it labels a single inseparable phase with two names.

More precisely: the double method-check (in `matches()` returning PARTIAL and `handle()` re-checking method) is not a redundancy bug. It is the signature of the conservation law in practice — the routing decision *cannot* be fully encoded in the match result without violating the calling convention, so it must be partially deferred to `handle()`, which re-reads scope. Every "improvement" that tries to pre-resolve the handler encodes response-layer logic into the routing layer, trading one coupling for another.

---

## Prediction About a Third Design

The conservation law predicts:

**A design that achieves routing purity AND composability without creating an adapter burden must change the ASGI calling convention** — specifically, adding a fourth parameter that carries mutable routing state separately from immutable transport state:

```python
async def app(scope, routing_ctx, receive, send): ...
```

Where `scope` is frozen-at-connection-time transport context and `routing_ctx` is a per-request mutable context for path-stripping state.

This design achieves routing purity (scope is never mutated), ecosystem composability within the framework (all layers speak the same four-argument protocol), and no adapter burden between Mounts and inner Routers.

**The new impossibility the law predicts**: this design interoperates with zero existing ASGI middleware. Every Starlette extension, every third-party middleware, every ASGI framework that the ecosystem has built over the last decade speaks `(scope, receive, send)`. The adapter that bridges three-argument ASGI to four-argument ASGI must manage the separation of transport state from routing state on behalf of middleware that cannot. At the ecosystem boundary, it must decide what to put in `scope` vs `routing_ctx` for middleware that doesn't know the distinction exists — and it must make this decision by mutating scope in the way the second design does.

**The law's prediction, precisely**: context enrichment complexity cannot be eliminated by changing the intra-framework protocol. It can only be relocated to the inter-framework protocol boundary, where it becomes invisible to the framework's own code and maximally painful for the ecosystem. A framework that has "solved" routing purity internally has exported the enrichment problem to its users.

The Starlette code's apparent design flaw — scope mutation during routing — is therefore not a mistake. It is the most honest encoding of a conservation law: put the complexity where it is visible and contained, rather than making it the ecosystem's problem. The `Match` enum's false promise of two phases is the only real mistake, because it misleads readers into thinking the problem is architectural when it is contractual.
