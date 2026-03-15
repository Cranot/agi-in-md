## The Falsifiable Claim

**`Match.PARTIAL` is an undocumented inter-object protocol masquerading as a data type.** It encodes a behavioral contract between `Route` and `Router` — specifically that PARTIAL means "path matched, method didn't" — that Route emits and Router interprets, but this contract appears nowhere in the type system, docstrings, or class boundaries.

This is falsifiable: if PARTIAL had consistent semantics across all `BaseRoute` subclasses, or if the Router-Route coupling were explicit, the claim collapses.

---

## The Three Experts

**Defender**: The PARTIAL mechanism is precisely correct. Without it, a router can't distinguish 404 (no path match) from 405 (path match, wrong method). The full scan-before-commit behavior is necessary to honor RFC 9110 §15.5.6. The duplication of the method check in both `matches()` and `handle()` is deliberate — `handle()` is the authoritative enforcement point; `matches()` is purely advisory. Calling this a "coupling" misidentifies an intentional two-phase protocol as accidental coupling.

**Attacker**: The claim is too narrow. PARTIAL is just a symptom of a worse problem: **the system cannot backtrack after mutating scope**. Look at the Router's dispatch loop — it saves `partial_scope` and then calls `scope.update(partial_scope)` before `partial.handle()`. Scope is mutated optimistically. The PARTIAL mechanism exists because linear scan with eager mutation has no rollback. The enum is a workaround for the real disease, which is that matching and committing are structurally inseparable.

**Prober**: Both of you accept that the `matches()`/`handle()` split is the natural architecture. But examine `BaseRoute.__call__`:

```python
async def __call__(self, scope, receive, send):
    match, child_scope = self.matches(scope)
    if match == Match.NONE:
        # respond 404/close websocket
        return
    scope.update(child_scope)
    await self.handle(scope, receive, send)
```

When a `Route` runs *standalone* (not inside a Router), it calls `matches()` → `handle()` directly, handles 405 correctly, and PARTIAL is never observed by anything. When a `Route` runs *inside a Router*, PARTIAL is meaningful. The claim and the attack both miss that **Route and Router are actually two execution models for the same object**, and the enum only makes sense in the coordinated model. The Route implicitly knows it will be orchestrated.

---

## The Transformation

**Original claim**: PARTIAL conflates routing negotiation with dispatch priority.

**Transformed claim**: `Route` has two execution models — standalone (via `BaseRoute.__call__`) and coordinated (via `Router.app`) — with no explicit interface separating them. The Match enum is an invisible protocol that only activates in the coordinated model. `Route` silently assumes an orchestrator that understands PARTIAL semantics. The structural separation (distinct classes, clean hierarchy) conceals a tight behavioral coupling.

---

## The Gap As Diagnostic

The original claim looked at what the enum *means*. The transformed claim reveals *who is responsible for knowing what it means*. The gap between them is this:

> The code presents clean class hierarchies as proof of clean separation, but the behavioral contracts that make those hierarchies work are unwritten and untyped.

**Concealment mechanism: structural separation as camouflage for behavioral coupling.** Class boundaries, inheritance, and clean method signatures create the visual impression of modularity. The actual runtime dependencies — the implicit contracts, the shared assumptions about scope state, the orchestration expectations — live between the classes, invisible.

---

## What the Entire Dialectic Failed to Surface

Applying the concealment mechanism more broadly, here are the couplings still hiding behind structural cleanliness:

**1. The `scope["app"]` sentinel is an undocumented execution context detector.**

Both `Router.not_found` and `Route.handle()` check `if "app" in scope` to decide whether to raise `HTTPException` or return a `PlainTextResponse` directly. This is a runtime flag that signals "I am embedded inside a larger Starlette application." There is no documented contract for when this key is set, who sets it, or what it means. Any code that inherits from `BaseRoute` or calls `Router.not_found` must implicitly know this convention or silently produce wrong behavior.

**2. `path_params` accumulation has no namespace isolation.**

When routes are nested — Mount inside Router, Router inside Mount — each level does:

```python
path_params = dict(scope.get("path_params", {}))
path_params.update(matched_params)
```

If a parent Mount and a child Route both define `{id}`, the child silently overwrites the parent's value with no warning. The hierarchical class structure implies namespace separation that does not exist in the runtime data.

**3. `Mount._base_app` and `Mount.app` are silently different objects used for different purposes.**

`self.app` is the middleware-wrapped app used for request handling. `self._base_app` is the unwrapped app used by the `routes` property for URL generation introspection. This means middleware added to a Mount is transparent for URL path generation but opaque for request handling. URL generation and request handling operate on structurally different object graphs with no documentation that this divergence is intentional.

**4. `Router.routes` is mutable at runtime but `middleware_stack` is not.**

`middleware_stack` is built once at construction by wrapping `self.app`:

```python
self.middleware_stack = self.app
if middleware:
    for cls, args, kwargs in reversed(middleware):
        self.middleware_stack = cls(self.middleware_stack, *args, **kwargs)
```

`self.routes` is a public list. If you `router.routes.append(new_route)` at runtime, the new route becomes visible to the redirect-slash logic (which re-scans `self.routes` per request) but the middleware stack is stale. A route appended after construction receives middleware treatment different from one present at construction — invisibly, with no error. The clean separation of `routes` and `middleware_stack` as independent attributes hides that they must be constructed in sync.

**5. `request_response` contains intentional name shadowing that destroys auditability.**

```python
def request_response(func):
    f = ...
    async def app(scope, receive, send):          # returned to caller
        request = Request(scope, receive, send)
        async def app(scope, receive, send):      # shadows outer `app`
            response = await f(request)
            await response(scope, receive, send)
        await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    return app
```

The inner `app` deliberately shadows the outer `app` so that `wrap_app_handling_exceptions` receives the inner closure — the one that actually calls the handler. This is the correct behavior, but the mechanism is a namespace collision that requires knowing that Python's closure resolution will pick the inner definition. Any modification to this function that introduces another reference to `app` before the shadow point will silently pass the wrong callable to `wrap_app_handling_exceptions`. The "clean" functional style conceals this fragility entirely.

---

## Summary

The concealment mechanism is the same at every level: structural cleanliness (separate classes, explicit hierarchies, pure functions) is used, consciously or not, to make implicit contracts invisible. The code looks modular. It is not. The real architecture lives in the whitespace between the class definitions — in undocumented scope keys, accumulation semantics, construction-time assumptions, and name shadowing — exactly where no static analysis tool, type checker, or code reviewer will look first.
