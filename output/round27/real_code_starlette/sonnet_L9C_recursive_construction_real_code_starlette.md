## Recursive Construction: Starlette Routing

---

### I. THE CLAIM

**Specific, falsifiable**: `Match.PARTIAL` encodes HTTP method semantics into a generic routing primitive, and `Router.app` discards all partial matches except the first, making 405 responses structurally incorrect. Concretely: given two routes for the same path with different methods, a mismatched request produces an `Allow` header listing only the first route's methods, not their union.

```python
# Demonstrable failure:
routes = [
    Route("/users", get_users, methods=["GET"]),
    Route("/users", create_user, methods=["POST"]),
]
# DELETE /users → 405, Allow: GET, HEAD   ← POST is silently dropped
```

This is falsifiable: trace `Router.app` → `partial = route; partial_scope = child_scope` → `Route.handle` → `{"Allow": ", ".join(self.methods)}`. The second partial match is never stored.

---

### II. THREE EXPERTS CHALLENGE

**Expert A (Defender)**: "This is intentional. Defining the same path with multiple Route objects on the same Router is an antipattern. Starlette's routing philosophy expects a single route per path with internal method dispatch. The docs are clear. The correct fix is the user's problem, not the framework's."

The defender is correct that the pattern is discouraged. But the claim doesn't require the pattern to be common. The code makes an architectural promise via `Match.PARTIAL` that it cannot keep: the enum implies a three-state classification, but only one partial match is ever retained. The promise is false regardless of how often users trigger it.

**Expert B (Attacker)**: "The claim is too narrow. The 405 problem is a symptom. The real failure is that `scope.update(child_scope)` is called *before* `route.handle()` in the partial-match branch — meaning the scope has already been mutated with the first partial match's data. Any middleware downstream operates on a scope that has been committed to the first partial match's `endpoint` and `path_params` before the 405 decision is made. The 405 response is wrong, but the scope corruption is worse."

The attacker forces a scope audit:

```python
# In Router.app:
if partial is not None:
    scope.update(partial_scope)          # ← scope["endpoint"] now points to partial match's handler
    await partial.handle(scope, receive, send)  # ← 405 response, but scope is already poisoned
```

Any exception middleware, tracing middleware, or logging middleware that reads `scope["endpoint"]` after this point receives the wrong endpoint. The 405 isn't just incorrectly formatted — it carries fabricated routing metadata.

**Expert C (Prober)**: "Both of you assume that scope mutation is a Starlette design choice. It isn't — it's an ASGI protocol constraint. The spec defines `scope` as the connection's ambient state dict. Starlette has no way to communicate routing results except by writing to it. What you call 'scope pollution' is ASGI's only transport mechanism for intra-framework state. The `Match` enum and the partial-match problem are downstream effects of the ASGI spec making scope the universal shared mutable state."

The prober is partially right. But this grants too much. ASGI requires scope to carry protocol state (`type`, `headers`, `method`, `path`). It does *not* require routing metadata (`endpoint`, `path_params`, `root_path`, `app_root_path`, `router`) to live in the same dict. Starlette chose to merge these, and that choice is what the concealment mechanism exploits.

---

### III. CLAIM TRANSFORMATION

**Original claim**: `Match.PARTIAL` loses information about allowed methods.

**Transformed claim**: The routing system conflates two ontologically distinct categories — ASGI protocol state (set by the server, connection-scoped, immutable in transit) and routing metadata (set by the router, request-scoped, accumulated during dispatch) — into a single shared mutable dict. This conflation makes routing non-idempotent, prevents rollback, makes scope auditing impossible, and is the structural precondition for every other bug, including the 405 problem.

**The gap**: I started with a specific symptom (wrong Allow header). I ended with a structural diagnosis (scope dual-use). The gap is real: the 405 problem could be fixed in isolation without touching the deeper issue. That would make the deeper issue *harder* to see. This is exactly the concealment structure.

---

### IV. THE CONCEALMENT MECHANISM

**Name**: *Abstraction laundering via incremental legibility.*

Each individual scope mutation looks safe and local:

```python
child_scope = {"endpoint": self.endpoint, "path_params": path_params}  # looks isolated
# ...
scope.update(child_scope)  # looks like a small, controlled merge
```

The `child_scope` intermediate variable creates the visual appearance of a copy or snapshot. It looks like the mutation is bounded. But `child_scope` is never a snapshot — it's a staging area for accumulation. The code produces the *aesthetic* of isolation while performing global state mutation.

Across layers:
- `Route.matches` stages: `endpoint`, `path_params`
- `Mount.matches` stages: `path_params`, `root_path`, `app_root_path`, `endpoint`
- `Router.app` stages: `router`
- `Router.app` (redirect branch): creates `redirect_scope = dict(scope)` — the only actual copy, but only for the redirect check, not for routing state

The mechanism works because each addition passes local inspection. No single `scope.update()` call is obviously wrong. The wrongness only appears when you map all additions across the full routing stack, which nobody does during code review of a single file.

---

### V. THE IMPROVEMENT

A `MatchCollector` that aggregates partial matches and injects aggregated `allowed_methods` into scope. This looks like it fixes the 405 problem, passes code review on structural grounds, and deepens the concealment by formalizing the wrong model.

```python
# routing.py — targeted improvement to Router.app and supporting infrastructure

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class MatchResult:
    """
    Encapsulates the result of a single route match operation,
    keeping scope updates immutable until the router commits them.
    """
    level: Match
    scope_updates: dict = field(default_factory=dict)
    route: BaseRoute | None = None

    @classmethod
    def none(cls) -> MatchResult:
        return cls(level=Match.NONE)

    @classmethod
    def partial(cls, route: BaseRoute, scope_updates: dict) -> MatchResult:
        return cls(level=Match.PARTIAL, scope_updates=scope_updates, route=route)

    @classmethod
    def full(cls, route: BaseRoute, scope_updates: dict) -> MatchResult:
        return cls(level=Match.FULL, scope_updates=scope_updates, route=route)


class PartialMatchAggregator:
    """
    Collects all partial (path-matched, method-mismatched) results during
    route scanning. Enables correct RFC 7231-compliant Allow headers by
    aggregating methods across all routes that matched the path.
    """

    def __init__(self) -> None:
        self._results: list[MatchResult] = []

    def record(self, result: MatchResult) -> None:
        self._results.append(result)

    @property
    def has_match(self) -> bool:
        return bool(self._results)

    @property
    def best(self) -> MatchResult | None:
        # First partial match retains priority for scope application
        return self._results[0] if self._results else None

    @property
    def allowed_methods(self) -> set[str]:
        """
        Union of all methods from all path-matching routes.
        Produces a correct Allow header even when multiple routes
        share a path with different method sets.
        """
        methods: set[str] = set()
        for result in self._results:
            route = result.route
            if isinstance(route, Route) and route.methods:
                methods |= route.methods
        return methods


class Router:
    # __init__ unchanged

    async def app(self, scope, receive, send):
        assert scope["type"] in ("http", "websocket", "lifespan")
        if "router" not in scope:
            scope["router"] = self
        if scope["type"] == "lifespan":
            await self.lifespan(scope, receive, send)
            return

        aggregator = PartialMatchAggregator()

        for route in self.routes:
            match, child_scope = route.matches(scope)
            if match == Match.FULL:
                scope.update(child_scope)
                await route.handle(scope, receive, send)
                return
            elif match == Match.PARTIAL:
                aggregator.record(MatchResult.partial(route, child_scope))

        if aggregator.has_match:
            best = aggregator.best
            scope.update(best.scope_updates)
            # Inject aggregated allowed methods so handle() can build a correct Allow header
            scope["_allowed_methods"] = aggregator.allowed_methods
            await best.route.handle(scope, receive, send)
            return

        route_path = get_route_path(scope)
        if scope["type"] == "http" and self.redirect_slashes and route_path != "/":
            redirect_scope = dict(scope)
            if route_path.endswith("/"):
                redirect_scope["path"] = redirect_scope["path"].rstrip("/")
            else:
                redirect_scope["path"] = redirect_scope["path"] + "/"
            for route in self.routes:
                match, child_scope = route.matches(redirect_scope)
                if match != Match.NONE:
                    redirect_url = URL(scope=redirect_scope)
                    response = RedirectResponse(url=str(redirect_url))
                    await response(scope, receive, send)
                    return

        await self.default(scope, receive, send)


class Route(BaseRoute):
    # matches() unchanged

    async def handle(self, scope, receive, send):
        if self.methods and scope["method"] not in self.methods:
            # Use aggregated allowed methods from router if available,
            # falling back to this route's own methods for standalone use.
            allowed = scope.get("_allowed_methods", self.methods)
            headers = {"Allow": ", ".join(sorted(allowed))}
            if "app" in scope:
                raise HTTPException(status_code=405, headers=headers)
            else:
                response = PlainTextResponse(
                    "Method Not Allowed", status_code=405, headers=headers
                )
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)
```

**Why this passes code review:**
- `MatchResult` and `PartialMatchAggregator` are properly typed and documented
- `allowed_methods` aggregation logic is correct and readable
- The loop structure is cleaner — no bare `partial = route; partial_scope = child_scope`
- `_allowed_methods` in scope is documented with a fallback, which looks defensive
- The 405 Allow header now reflects all matching routes' methods

---

### VI. THREE PROPERTIES VISIBLE ONLY FROM STRENGTHENING

**Property 1: The fix is incomplete at the boundary between router and route handler.**

`PartialMatchAggregator` correctly aggregates allowed methods in `Router.app`. But `Route.handle()` only reads `scope.get("_allowed_methods", self.methods)`. This means the fix works only when called through `Router`. When `Route` is used standalone (as a direct ASGI app via `BaseRoute.__call__`), it falls back to `self.methods`. The boundary is invisible until you try to make it correct — at which point you discover that `Route` and `Router` are not actually composable units. They're coupled through implicit scope conventions that have no contract.

**Property 2: `_allowed_methods` in scope is routing metadata contaminating protocol state.**

Adding `scope["_allowed_methods"]` reveals that we're using scope as an inter-component message bus. The improvement adds one more key to the accumulation. Now scope contains: `router`, `endpoint`, `path_params`, `root_path`, `app_root_path`, and `_allowed_methods`. Each key was added to solve a specific problem. Mapping them out reveals that scope is carrying a full routing session state — except with no schema, no ownership, no lifecycle, and no cleanup. The improvement makes the pattern visible precisely because it does it again.

**Property 3: The `Match` enum needs to be a sum type, not an ordinal.**

When writing `PartialMatchAggregator.allowed_methods`, I needed to know *why* the match was partial — was it method mismatch, or something else? The current `Match.PARTIAL` is opaque. If a `Mount` returned `PARTIAL` (it doesn't, but could in a subclass), the aggregator would incorrectly try to read `route.methods`. To make the aggregation correct in the general case, `Match.PARTIAL` needs to carry a payload: `MatchResult.PARTIAL_METHOD_MISMATCH(methods: set[str])`. The enum's ordinal design (0, 1, 2) implies a linear scale but the semantics require a discriminated union. The improvement failed to fix this, which is visible because the aggregator has to do an `isinstance(route, Route)` check — a sign that the type system is wrong at the level of `Match`, not at the level of the aggregator.

---

### VII. RECURSIVE DIAGNOSTIC: WHAT THE IMPROVEMENT CONCEALS

**What the improvement hides:**

The improvement converts a visible hack (`partial = route; partial_scope = child_scope`) into a structured pattern (`PartialMatchAggregator`). This makes the scope mutation look *designed* and *controlled*. But the fundamental operation — `scope.update(best.scope_updates)` — is identical to the original. The structure hides that we didn't change the mechanism; we documented it.

The `_allowed_methods` key deepens the original problem: scope now carries more routing metadata. The improvement adds a new undocumented scope key that every downstream middleware must either handle or ignore. The `_` prefix is supposed to signal "private," but ASGI scopes have no private namespace. Any middleware can read or overwrite `scope["_allowed_methods"]`.

**What property of the original problem is visible only because the improvement recreates it:**

The improvement reveals that the original problem is structural, not incidental. `Route.handle()` and `Router.app` are coordinated through scope because they have no other communication channel — they don't call each other, they don't share a return value, they don't use a passed context object. They are connected only through the ambient mutable dict. The improvement makes this visible because the "fix" to `Router.app` is incomplete without a corresponding "fix" to `Route.handle()`, and the only way to connect those two fixes is... `scope["_allowed_methods"]`. We needed another scope key to fix a problem caused by scope key accumulation.

The original problem generates its own solution space: every fix that stays within the ASGI model must use scope as its channel, which reproduces the conflation the fix was meant to address. The recursion is structural, not accidental.

---

### Summary Diagnosis

| Layer | Surface | Hidden |
|---|---|---|
| `Match` enum | Clean three-state classification | Ordinal encoding HTTP semantics, needs sum type |
| `child_scope` | Appears isolated, bounded | Staging area for global accumulation |
| `scope.update()` | Looks like a small, local merge | Irrevocable global state mutation |
| `PartialMatchAggregator` | Appears to fix 405 problem | Adds another scope key; fix incomplete at Route boundary |
| `scope["_allowed_methods"]` | Appears to connect router to handler | Reveals scope is an unschematized inter-component bus |

The code's concealment mechanism is self-reinforcing: every fix that stays within its architectural model reproduces the problem at one level of abstraction higher. The diagnostic is stable across recursion.
