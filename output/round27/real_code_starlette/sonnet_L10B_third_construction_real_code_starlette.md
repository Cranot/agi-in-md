# Structural Analysis: Starlette Routing

---

## The Claim

**`Match.PARTIAL` is semantically overloaded to mean two structurally different things, and the Router's dispatch loop cannot distinguish them.**

Specifically: `Route.matches()` returns `Match.PARTIAL` to mean *"path matches, method doesn't"*. `Mount.matches()` returns `Match.PARTIAL` to mean *"prefix matches, delegate deeper"*. The Router treats both identically — save the first one, use it as fallback — which makes correct 405 handling with aggregated `Allow` headers architecturally impossible, not merely unimplemented.

This is falsifiable: submit two routes `Route("/x", methods=["GET"])` and `Route("/x", methods=["POST"])`, issue a `DELETE /x`, and observe that the 405 response contains only one route's methods, not both.

---

## Three Experts

**Expert A (defends):** The overloading is intentional and safe. `Match.PARTIAL` for Route is a method-mismatch signal that prevents the Router from falling through to a 404 when a path *did* match. It's not overloaded — it's a uniform "best possible match short of FULL" signal. The dispatch loop saving `partial` and using it as fallback is correct behavior.

**Expert B (attacks):** The claim understates the problem. The real issue isn't the enum — it's that `scope` is a shared mutable dict serving three masters simultaneously: ASGI protocol state (`type`, `method`, `path`), routing accumulation state (`path_params`, `root_path`, `app_root_path`), and application context (`endpoint`, `router`). `Match.PARTIAL` overloading is a symptom. The cause is that routing decisions and their semantic payloads can only be assembled by mutating a shared object, so the enum has to carry freight it shouldn't.

**Expert C (probes what both take for granted):** Both assume there's a single dispatch decision per request. But the Router's loop actually performs two distinct operations: *path resolution* (does this route structurally match the URL?) and *method validation* (is this route semantically appropriate for this request?). Both experts, and the code itself, assume these collapse into a single matching phase. But they have different aggregation semantics: path resolution is first-match-wins, method validation is collect-all-then-respond.

### The Claim Transforms

Original: *`Match.PARTIAL` is overloaded.*

Transformed: **The routing system conflates two phases with incompatible aggregation semantics — path resolution (first-wins) and method validation (collect-all) — into a single `matches()` call, making the collect-all semantics unimplementable without restructuring the entire dispatch loop.**

**The gap diagnostic:** I started focused on an enum, ended at a phase-ordering problem. The enum was a local symptom of a global architectural collapse.

---

## The Concealment Mechanism

**Semantic compression through behavioral uniformity.**

The `matches()` interface on `BaseRoute` is elegant and uniform. Every route returns `(Match, dict)`. The Router's dispatch loop is five lines. This uniformity *looks* like good abstraction but conceals that `Route` and `Mount` are computing fundamentally different things and returning them through the same channel.

The concealment works because:
- The enum value `PARTIAL` reads as a clean routing signal
- The Router loop's `partial is None` guard looks like standard "first match wins" logic
- The 405 response in `Route.handle()` looks like it's in the right place
- No individual line is wrong

The real problem — that method validation requires cross-route aggregation before dispatch — is invisible because the code *does something reasonable* even while being structurally incapable of doing the right thing.

---

## Improvement 1: Accumulate All Partials

This passes review. It looks like a robustness improvement:

```python
# In Router.app — replace single `partial` variable:

partials: list[tuple[BaseRoute, dict]] = []

for route in self.routes:
    match, child_scope = route.matches(scope)
    if match == Match.FULL:
        scope.update(child_scope)
        await route.handle(scope, receive, send)
        return
    elif match == Match.PARTIAL:
        partials.append((route, child_scope))

if partials:
    # Aggregate allowed methods across all partial matches
    allowed = set()
    for route, _ in partials:
        if hasattr(route, 'methods') and route.methods:
            allowed.update(route.methods)
    
    if allowed:
        # All partials are method mismatches — return proper 405
        route, child_scope = partials[0]
        scope.update(child_scope)
        headers = {"Allow": ", ".join(sorted(allowed))}
        if "app" in scope:
            raise HTTPException(status_code=405, headers=headers)
        response = PlainTextResponse("Method Not Allowed", 
                                     status_code=405, headers=headers)
        await response(scope, receive, send)
        return
    else:
        # Partials without methods — original behavior
        route, child_scope = partials[0]
        scope.update(child_scope)
        await route.handle(scope, receive, send)
        return
```

This passes review: it's additive, preserves existing behavior for the common case, improves 405 headers for multi-method routes, no breaking changes.

### Three Properties Now Visible

**1. The `Route`/`Mount` distinction is invisible at the call site.** When you build `partials: list[tuple[BaseRoute, dict]]`, you immediately need to ask `hasattr(route, 'methods')` — a duck-typed check on a concrete subclass attribute — because `BaseRoute` has no `methods` protocol. The base class pretends the distinction doesn't exist, and you can only handle it by reaching past the interface.

**2. `Match.PARTIAL` carries no information about *why* it matched partially.** To distinguish "prefix match" from "method mismatch," you have to inspect the route object after getting its match result. The match result itself is opaque. The enum value that looks like a routing signal is actually just a boolean "not FULL, not NONE" with all semantics deferred to out-of-band inspection.

**3. The `allowed` aggregation logic now exists in two places.** It's in `Route.handle()` (using `self.methods`) and now in `Router.app` (using `route.methods` via hasattr). You've duplicated the logic but in different contexts, with different scoping. Any change to method handling must now be made in two places that don't reference each other.

---

## Improvement 2: Eliminate Method Mismatch from `Match`

This also passes review. It treats method mismatch as request data, not routing signal:

```python
class Route(BaseRoute):
    def matches(self, scope):
        if scope["type"] == "http":
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                path_params = dict(scope.get("path_params", {}))
                path_params.update(matched_params)
                child_scope = {
                    "endpoint": self.endpoint,
                    "path_params": path_params,
                }
                if self.methods and scope["method"] not in self.methods:
                    # Path matched. Method didn't. Signal it as data, not routing.
                    child_scope["_allowed_methods"] = frozenset(self.methods)
                    return Match.FULL, child_scope  # ← FULL, not PARTIAL
                return Match.FULL, child_scope
        return Match.NONE, {}
```

The Router loop then reads `child_scope.get("_allowed_methods")` on FULL matches to distinguish "routable FULL" from "method-refused FULL." This passes review: it moves the semantics of method refusal into the payload where it can be aggregated, removes the `Match.PARTIAL` overloading for this case, and the behavior is identical for correct requests.

**These two improvements directly contradict each other.**

Improvement 1 embraces `Match.PARTIAL` as a meaningful signal and builds infrastructure (a list, aggregation logic) around it.

Improvement 2 eliminates `Match.PARTIAL` from `Route` entirely, returning `Match.FULL` with metadata instead.

---

## The Structural Conflict

Both improvements are legitimate responses to the same real problem. Their conflict is not technical — it's architectural:

**Is method refusal a routing disposition or a request property?**

- **If routing disposition** (Improvement 1): `matches()` returns PARTIAL, the Router loop aggregates partials, the routing *decision* is "I almost matched." The contract is: `Match` is the authoritative signal.
- **If request property** (Improvement 2): `matches()` returns FULL with metadata, the Router reads the metadata, method refusal is data carried alongside a successful path match. The contract is: `Match` signals path resolution only.

The conflict exists *because both are legitimate* — method refusal is simultaneously a routing-level decision (should the router continue trying other routes?) and a response-level fact (which methods are actually allowed?). Neither improvement is wrong. They resolve different halves of the same incoherence.

---

## Improvement 3: `MatchResult` — Resolves the Conflict

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class MatchResult:
    match: Match
    child_scope: dict = field(default_factory=dict, compare=False)
    allowed_methods: Optional[frozenset[str]] = None

    @property
    def method_not_allowed(self) -> bool:
        return self.allowed_methods is not None
    
    @property  
    def path_matched(self) -> bool:
        return self.match != Match.NONE


class Route(BaseRoute):
    def matches(self, scope) -> MatchResult:
        if scope["type"] == "http":
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                path_params = dict(scope.get("path_params", {}))
                path_params.update(matched_params)
                child_scope = {"endpoint": self.endpoint, "path_params": path_params}
                if self.methods and scope["method"] not in self.methods:
                    return MatchResult(Match.FULL, child_scope, 
                                       allowed_methods=frozenset(self.methods))
                return MatchResult(Match.FULL, child_scope)
        return MatchResult(Match.NONE)


# Router.app aggregation:
async def app(self, scope, receive, send):
    assert scope["type"] in ("http", "websocket", "lifespan")
    if "router" not in scope:
        scope["router"] = self
    if scope["type"] == "lifespan":
        await self.lifespan(scope, receive, send)
        return

    partial: Optional[BaseRoute] = None
    partial_scope: dict = {}
    allowed_methods: set[str] = set()

    for route in self.routes:
        result = route.matches(scope)
        if result.path_matched and not result.method_not_allowed:
            if result.match == Match.FULL:
                scope.update(result.child_scope)
                await route.handle(scope, receive, send)
                return
            elif partial is None:
                partial = route
                partial_scope = result.child_scope
        elif result.method_not_allowed:
            allowed_methods.update(result.allowed_methods)

    if allowed_methods:
        headers = {"Allow": ", ".join(sorted(allowed_methods))}
        if "app" in scope:
            raise HTTPException(status_code=405, headers=headers)
        response = PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
        await response(scope, receive, send)
        return

    if partial is not None:
        scope.update(partial_scope)
        await partial.handle(scope, receive, send)
        return

    # ... redirect_slashes, default ...
```

This satisfies both contradicting requirements: `Match` is now unambiguous (path resolution only), and method refusal is explicit data that supports aggregation.

### How It Fails

Remove `Route.handle()`'s method check? Then `BaseRoute.__call__()` — which calls `matches()` then `handle()` directly — silently stops enforcing methods when a `Route` is used as a standalone ASGI app.

Keep `Route.handle()`'s method check? Now method validation runs in two places: once in `matches()` (as `MatchResult.allowed_methods`) and once in `handle()` (as a 405 response). They must stay synchronized. Any change to method handling — adding OPTIONS support, changing HEAD behavior — must be made twice in places that don't reference each other.

You cannot remove one without breaking standalone usage. You cannot keep both without duplicating logic. The improvement collapses back to the original problem under a different name.

---

## What the Failure Reveals About the Design Space

The conflict revealed a tension between two valid architectural choices for `Match` semantics. The failure of the resolution reveals something deeper and unreachable from the conflict alone:

**The ASGI composability requirement and the routing aggregation requirement are mutually exclusive at this level of abstraction, and no mechanism internal to the current architecture can satisfy both.**

The ASGI composability requirement: every route must be a valid standalone ASGI app, callable with `(scope, receive, send)`. This forces `handle()` to be self-contained — it must enforce methods, because there's no guarantee `matches()` was called before it.

The routing aggregation requirement: a Router needs to examine *all* routes that could respond to a request before emitting *any* response — to aggregate `Allow` headers, to detect 405 vs 404, to apply redirect_slashes correctly.

These requirements occupy different positions in the design space. Composability is a *closed-world* requirement: each component knows everything it needs to answer a request. Aggregation is an *open-world* requirement: a coordinator collects information across components before deciding. A system cannot simultaneously be both closed-world (each component is self-sufficient) and open-world (components expose pre-response information to coordinators).

The current architecture resolves this by hiding it: `Match.PARTIAL` leaks pre-response information upward (satisfying aggregation partially) while `handle()` retains full self-sufficiency (satisfying composability). The leak is informal, untyped, and semantically overloaded — which is exactly why it's a concealment mechanism rather than a solution.

What the design space actually requires — and what the failure makes legible — is a **two-phase protocol**: a *planning phase* where routes expose their full decision data without side effects, and a *dispatch phase* where the chosen route acts. HTTP frameworks like Django REST Framework implement this as separate `get_handler()` and `dispatch()`. ASGI's three-argument callable interface provides no hook for a planning phase, so Starlette must retrofit one inside a single `__call__`, which is why the collision between composability and aggregation is structurally unavoidable in this codebase.

The concealment mechanism isn't a bug that can be fixed — it's load-bearing.
