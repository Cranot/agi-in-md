# Structural Analysis: Starlette Routing

---

## The Claim

**`Match.PARTIAL` encodes method-mismatch inside a value whose semantic is path-match quality, coupling HTTP method validation into the routing protocol. This forces the routing engine to be simultaneously a path resolver and a method validator, while the actual method enforcement is independently re-implemented in `handle()`.**

Falsifiable test: if `PARTIAL` is genuinely a routing concept, removing the method check from `matches()` should break the protocol. If it isn't, `Router.app`'s partial-fallback logic should be unreachable for any well-formed route tree. *Both are partly true simultaneously.*

---

## Three Experts

**Defender** — The `PARTIAL` mechanism is precisely correct. Without it, method-mismatch falls through to `not_found()` and returns 404, which violates HTTP semantics. The `Match` enum lets `Router.app` distinguish "no matching path" from "matching path, wrong method," enabling the correct 405 with `Allow` headers. The design is elegant: the router collects partial matches, picks the best one, and lets `handle()` communicate the failure to the client.

**Attacker** — `PARTIAL` only has consumers at exactly one level of the hierarchy. `BaseRoute.__call__` treats `PARTIAL` identically to `NONE` — both terminate the route — so when routes are invoked directly, the signal is discarded. `Mount.matches()` *never* produces `PARTIAL`; it always returns `FULL` for any prefix match. So the entire signaling mechanism only works within a flat `Router.app` iteration. The moment you compose with `Mount`, the signal is swallowed and the inner `Router` independently reinvents the same check. `PARTIAL` looks compositional but is structurally flat.

**Prober** — Both of you assume method validation *belongs in routing*. What do you both take for granted? That `matches()` should know about HTTP methods at all. But path routing answers "which handler?" while method routing answers "which operation?" These are orthogonal. A path is universal across protocols; `scope["method"]` is HTTP-specific. The `Match` enum mixes a structural concept (route quality) with a protocol concept (HTTP method). The real question isn't whether `PARTIAL` is elegant or broken — it's whether routing should produce it at all.

---

## The Transformation

**Original claim**: `PARTIAL` couples method validation into path routing.

**Transformed claim**: The system encodes HTTP method logic at three independent sites — `matches()` (produces `PARTIAL`), `Router.app` (consumes `PARTIAL`), `handle()` (re-checks and enforces) — with no shared mechanism connecting them, so they can drift. The `Match` enum presents an abstract routing concept while secretly encoding HTTP protocol semantics, making drift invisible until the three sites disagree.

**The gap**: I started with *coupling* and ended with *triplicate enforcement with hidden drift risk*. The transformation reveals that `PARTIAL` isn't just wrong in principle — it creates a concrete maintenance hazard that the clean enum syntax conceals.

---

## Concealment Mechanism

**Abstraction symmetry**: `Route`, `Mount`, and `Router` all implement the same interface (`matches` / `handle` / `url_path_for` / `__call__`). This symmetry implies they're equivalent peers with consistent behavior. The symmetry hides that:

- Only `Route` generates `PARTIAL`
- Only `Router.app` consumes it with special logic
- `Mount` silently drops it (returns `FULL`)
- `BaseRoute.__call__` ignores it entirely

The interface makes all three look like the same kind of thing. They aren't. The abstraction boundary that should reveal structural differences is instead used to paper over them.

---

## Improvement One: `MethodPolicy` Abstraction

This would pass code review. It appears to fix the duplication, adds a clear abstraction, and makes the method logic testable in isolation.

```python
from dataclasses import dataclass
from typing import Optional, FrozenSet

@dataclass(frozen=True)
class MethodPolicy:
    """Encapsulates HTTP method validation for a route."""
    allowed: Optional[FrozenSet[str]]  # None = allow all

    @classmethod
    def from_methods(cls, methods: Optional[list]) -> "MethodPolicy":
        if methods is None:
            return cls(allowed=None)
        expanded = {m.upper() for m in methods}
        if "GET" in expanded:
            expanded.add("HEAD")
        return cls(allowed=frozenset(expanded))

    def check(self, method: str) -> Match:
        if self.allowed is None:
            return Match.FULL
        return Match.FULL if method in self.allowed else Match.PARTIAL

    def allow_header(self) -> dict:
        if self.allowed is None:
            return {}
        return {"Allow": ", ".join(sorted(self.allowed))}


class Route(BaseRoute):
    def __init__(self, path, endpoint, *, methods=None, name=None,
                 include_in_schema=True, middleware=None):
        assert path.startswith("/"), "Routed paths must start with '/'"
        self.path = path
        self.endpoint = endpoint
        self.name = get_name(endpoint) if name is None else name
        self.include_in_schema = include_in_schema
        self.method_policy = MethodPolicy.from_methods(methods)

        endpoint_handler = endpoint
        while isinstance(endpoint_handler, functools.partial):
            endpoint_handler = endpoint_handler.func
        if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
            self.app = request_response(endpoint)
            if methods is None:
                self.method_policy = MethodPolicy.from_methods(["GET"])
        else:
            self.app = endpoint

        if middleware is not None:
            for cls, args, kwargs in reversed(middleware):
                self.app = cls(self.app, *args, **kwargs)

        self.path_regex, self.path_format, self.param_convertors = compile_path(path)

    # Expose .methods for backward compatibility
    @property
    def methods(self):
        return self.method_policy.allowed

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
                child_scope = {"endpoint": self.endpoint, "path_params": path_params}
                # Delegate method check to policy — single authority
                return self.method_policy.check(scope["method"]), child_scope
        return Match.NONE, {}

    async def handle(self, scope, receive, send):
        method_match = self.method_policy.check(scope["method"])
        if method_match != Match.FULL:
            headers = self.method_policy.allow_header()
            if "app" in scope:
                raise HTTPException(status_code=405, headers=headers)
            else:
                response = PlainTextResponse("Method Not Allowed",
                                             status_code=405, headers=headers)
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)
```

This passes code review because:
- `MethodPolicy` is a real abstraction with a clear responsibility
- The `check()` method is the single place where method logic lives
- `handle()` now calls `self.method_policy.check()` instead of duplicating the set-membership test
- Backward compatibility is preserved via the `methods` property
- It's unit-testable in isolation

---

## Three Properties Visible Only Because I Tried to Strengthen the Problem

**1. Mount's structural incompatibility**: Making method logic principled in `Route` via `MethodPolicy` makes `Mount`'s complete absence of method logic jarring. But adding `MethodPolicy` to `Mount` would be wrong — Mounts don't own method logic, they delegate it. The improvement reveals that `Mount` isn't "missing" something; it's a different *kind* of thing than `Route`, but the shared interface hides this.

**2. The orphaned consumer**: When I made `MethodPolicy.check()` the single authority in `Route`, I immediately saw that `Router.app`'s `PARTIAL` consumption is three structural layers away from the producer. `Route` produces it; `Router.app` consumes it via a loop that `Route` knows nothing about. The `MethodPolicy` improvement makes the coupling explicit: there are now *two* callers of `MethodPolicy.check()` — `matches()` and `handle()` — for the same router, coordinated by nothing but implicit convention.

**3. The handle/matches duality**: Extracting `MethodPolicy` reveals that `matches()` and `handle()` serve different masters: `matches()` informs `Router.app` (infrastructure), while `handle()` informs the HTTP client (protocol). They share `self.method_policy` but there's no guarantee they remain consistent. The improvement makes it look like they share a single policy object, but they actually perform independent checks on that policy with no coordination.

---

## Diagnostic on Improvement One

**What does `MethodPolicy` conceal?**

It conceals that the true structural problem is not *code duplication* but *architectural placement*. The mixin makes the wrong thing look right — method validation at the routing layer is problematic regardless of how cleanly it is implemented. `MethodPolicy` makes a coherent object out of an incoherent responsibility.

More specifically: `MethodPolicy` looks like a proper abstraction, but it creates a new question: who is `MethodPolicy`'s real owner? It lives on `Route` but is consulted by both `matches()` (for `Router.app`'s benefit) and `handle()` (for the client's benefit). These are different concerns with different scopes. The abstraction papers over the split rather than resolving it.

**What property is visible because the improvement recreates it?**

The improvement recreates and clarifies the `matches()`/`handle()` duality. When `MethodPolicy` is the shared object between both methods, it becomes obvious that `matches()` is producing information for the *router's* decision loop while `handle()` is producing information for the *HTTP response*. These are communications at different layers of the stack. The original code kept them separate (duplicated), which was messy but honest. `MethodPolicy` unifies them into one object while their consumers remain different layers — recreating the fundamental mismatch at a higher level of abstraction.

**The recreated property**: `matches()` and `handle()` communicate with different consumers (routing infrastructure vs. HTTP client) but are forced to share the same mechanism. Any improvement that unifies their logic recreates this split.

---

## Improvement Two: Separate Path Match from Method Match

Address the `matches()`/`handle()` duality directly by removing method logic from `matches()` entirely:

```python
class Route(BaseRoute):
    def matches(self, scope):
        """Pure path matching. No method checking — that is dispatch, not routing."""
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
                    # Communicate allowed methods via scope for dispatch layer
                    "route_allowed_methods": self.methods,
                }
                return Match.FULL, child_scope
        return Match.NONE, {}

    async def handle(self, scope, receive, send):
        allowed = scope.get("route_allowed_methods")
        if allowed and scope["method"] not in allowed:
            headers = {"Allow": ", ".join(sorted(allowed))}
            if "app" in scope:
                raise HTTPException(status_code=405, headers=headers)
            else:
                response = PlainTextResponse("Method Not Allowed",
                                             status_code=405, headers=headers)
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)


# Router.app: drop PARTIAL handling, add post-match method validation
async def app(self, scope, receive, send):
    assert scope["type"] in ("http", "websocket", "lifespan")
    if "router" not in scope:
        scope["router"] = self

    if scope["type"] == "lifespan":
        await self.lifespan(scope, receive, send)
        return

    matched_route = None
    for route in self.routes:
        match, child_scope = route.matches(scope)
        if match == Match.FULL:  # now only FULL or NONE — no PARTIAL
            matched_route = route
            matched_scope = child_scope
            break  # first full match wins; method is checked in handle()

    if matched_route is not None:
        scope.update(matched_scope)
        await matched_route.handle(scope, receive, send)
        return

    route_path = get_route_path(scope)
    if scope["type"] == "http" and self.redirect_slashes and route_path != "/":
        redirect_scope = dict(scope)
        redirect_scope["path"] = (
            redirect_scope["path"].rstrip("/")
            if route_path.endswith("/")
            else redirect_scope["path"] + "/"
        )
        for route in self.routes:
            match, child_scope = route.matches(redirect_scope)
            if match != Match.NONE:
                redirect_url = URL(scope=redirect_scope)
                response = RedirectResponse(url=str(redirect_url))
                await response(scope, receive, send)
                return

    await self.default(scope, receive, send)
```

---

## Diagnostic on Improvement Two

**What does this conceal?**

The method validation moved from `matches()` into scope as `route_allowed_methods`. This looks like decoupling, but scope is now a message-passing channel between routing and dispatch. The scope mutation problem — which runs through the entire original design — is worsened: scope now carries routing *artifacts* (which route matched, what methods it allows) alongside request *context* (path params, root path). The improvement moves the coupling into the data structure it was already coupling through.

More concretely: `scope["route_allowed_methods"]` is set by `Route.matches()` inside `child_scope`, then consumed by `Route.handle()` — but it passes through `scope.update(matched_scope)` in `Router.app`. So `Router.app` now silently forwards routing metadata by mutating a shared dict, and `handle()` reads it back. This is an implicit, untyped protocol baked into a mutable dict.

**What property is visible because this improvement recreates it?**

The improvement makes the scope mutation problem impossible to ignore. In the original code, `scope.update(child_scope)` mutated `path_params` and `endpoint` — clearly request context. In Improvement Two, scope also carries `route_allowed_methods` — a routing implementation detail. The improvement draws a sharp line that was previously blurred: *some things in scope describe the request, and some things describe the routing decision.* The original code put them in the same dict. The improvement recreates this exactly, now with an explicit example of a routing-decision key polluting request scope.

---

## The Structural Invariant

**The routing tree must simultaneously serve as four incompatible data structures:**

1. **Path index** — match an incoming path string against patterns, returning the first winner (wants early termination, regex or trie)
2. **Method validator** — after path match, check HTTP method and collect 405 candidates across all path matches (wants to see *all* matches before rejecting any)
3. **Scope builder** — accumulate request context as traversal descends the tree (wants to write state as it goes down)
4. **URL generator** — given a name and params, reverse the tree to produce a URL (wants to ascend the same structure the path index descends)

These four operations have incompatible structural requirements:

- Path matching wants first-match and early termination; method validation wants all-matches and late selection
- Scope building writes state forward (parent → child); URL generation reads structure backward (child → parent via `NoMatchFound`)  
- `url_path_for` raises exceptions to control flow across recursive traversal; `matches()` returns values

Every improvement tried here moved the tension around without eliminating it:
- `MethodPolicy` unified path and method logic in one object but couldn't resolve their different consumers
- Separating `matches()` from method checking moved method logic into scope, making the scope-as-communication-channel problem explicit
- Any future improvement that cleans up scope will recreate the path/method tension

**This invariant persists because it is a property of the problem, not the implementation.** HTTP routing requires all four operations. A single tree traversal cannot satisfy all four without at minimum one of the following: duplicate traversal, shared mutable state, exception-based control flow for non-error conditions, or asymmetric behavior between structurally equivalent nodes. The original Starlette code uses all four. Each "improvement" trades one for another. The invariant names the irreducible cost of routing as a unified abstraction.
