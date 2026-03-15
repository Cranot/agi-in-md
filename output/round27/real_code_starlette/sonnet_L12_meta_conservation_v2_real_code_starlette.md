## Structural Diagnosis: Starlette Routing

---

### The Claim

**Falsifiable claim**: The deepest structural problem is *split authority over constraint validation* — the decision whether a request is permitted is distributed across three non-adjacent locations: `Route.matches()` (emits `PARTIAL` as a soft rejection signal), `Router.app()` (interprets `PARTIAL` as a priority-lowered fallback), and `Route.handle()` (independently re-enforces the same constraint and generates the response). Adding any new routing dimension — content negotiation, versioning, tenant isolation — requires modifying all three locations because no single location holds authority.

**Falsification test**: Attempt to add `Accept`-header routing (JSON vs HTML handlers on the same path and method) by touching only one location.

---

### Three-Expert Dialectic

**Expert 1 (Defender):** The split is real and consequential. `matches()`, `Router.app()`, and `handle()` each enforce method constraints under different assumptions. Extending this to Accept-header routing requires touching all three independently, plus any custom `BaseRoute` subclasses.

**Expert 2 (Attacker):** "Split authority" is just a symptom. The real problem is that `Match` is a three-value enum encoding a two-dimensional decision: *(match quality) × (rejection reason)*. `PARTIAL` means "path matched, method didn't" for `Route`, but it's undefined for `Mount` — which never returns `PARTIAL` at all. The claim about split authority is complaining about a consequence of using a 1D enum for a 2×N matrix.

**Expert 3 (Probes what both take for granted):** Both experts assume method checking is the central concern. But they both take for granted that *scope mutation is the right communication channel for routing decisions*. `matches()` builds `child_scope`; `Router.app()` calls `scope.update(child_scope)` before `handle()` is called. There's no return value from ASGI callables — `async def f(scope, receive, send) -> None`. Any decision made in `matches()` must either be re-computed in `handle()` or stored in the mutable scope. The "split authority" exists because the interface provides no other option.

---

### Claim Transformation

Original claim: *method validation authority is split across three locations.*

Transformed claim: **ASGI's void-return callable signature makes routing decisions inseparable from routing execution — any constraint evaluated at match-time must be either re-computed at dispatch-time or stored in the mutable scope, because there is no typed return channel.**

**The gap**: I thought the problem was code organization (where is the check). The gap reveals it's an information architecture problem — `matches()` and `handle()` are structurally required to share state through the only available medium: the mutable scope dict.

---

### The Concealment Mechanism

The `Match` enum **makes an interface limitation look like a design choice**. Three-valued `Match(NONE, PARTIAL, FULL)` creates the appearance of a rich routing taxonomy. It conceals that `PARTIAL` exists not to describe match quality but to solve a specific encoding problem: how do you signal "I matched the path but reject the method" when your only communication channel is a side-effecting write to a shared dict?

The enum makes the void-signature workaround look like intentional API design.

---

### The Improvement That Deepens Concealment

Extract method validation into a shared `MethodConstraint` — DRY, testable, clean:

```python
class MethodConstraint:
    def __init__(self, methods):
        self.allowed = None
        if methods is not None:
            self.allowed = {m.upper() for m in methods}
            if "GET" in self.allowed:
                self.allowed.add("HEAD")

    def permits(self, method: str) -> bool:
        return self.allowed is None or method in self.allowed

    def rejection_headers(self) -> dict:
        return {"Allow": ", ".join(sorted(self.allowed))} if self.allowed else {}


class Route(BaseRoute):
    def __init__(self, path, endpoint, *, methods=None, name=None,
                 include_in_schema=True, middleware=None):
        # ... existing setup ...
        self.method_constraint = MethodConstraint(methods)
        self.path_regex, self.path_format, self.param_convertors = compile_path(path)

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
                if not self.method_constraint.permits(scope["method"]):
                    return Match.PARTIAL, child_scope
                return Match.FULL, child_scope
        return Match.NONE, {}

    async def handle(self, scope, receive, send):
        if not self.method_constraint.permits(scope["method"]):
            headers = self.method_constraint.rejection_headers()
            if "app" in scope:
                raise HTTPException(status_code=405, headers=headers)
            response = PlainTextResponse("Method Not Allowed", status_code=405,
                                        headers=headers)
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)
```

**Why this passes code review:**
- DRY: method logic lives in one place
- Testable in isolation
- Clear naming (`permits`, `rejection_headers`)
- Easy to extend (add a new constraint type later)
- Removes the inline `self.methods` set mutation from `__init__`

**Why this deepens concealment:** It makes the two-location check look organized and intentional. It obscures the reason the check happens twice at all. A reviewer sees clean abstraction; they don't see that `MethodConstraint.permits()` is being called in two structurally different contexts.

---

### Three Properties Visible Only From the Strengthening Attempt

**1. The constraint is evaluated against different scope states.**
`matches()` calls `permits(scope["method"])` against the *pre-update* scope. `handle()` calls it against the *post-update* scope (which now contains `path_params`, `endpoint`, etc. from `child_scope`). For `scope["method"]` this doesn't matter — it's stable. But making `MethodConstraint` explicit reveals that *any* constraint that reads scope-state will see different scope depending on which phase evaluates it. The constraint is context-dependent in a way the inline code never made visible.

**2. `Match.PARTIAL` doesn't mean "partial path match" — it means "soft constraint failure."**
Once you extract `MethodConstraint`, you can see that `PARTIAL` is never about the path at all — it's always about method rejection. `Mount` always returns `FULL` or `NONE`. The name `PARTIAL` is a lie that the inline code obscured but the factored-out constraint makes legible.

**3. `Router.app()`'s iteration loop is the hidden authority.**
With the constraint factored out, it becomes clear that `MethodConstraint` doesn't decide whether PARTIAL means "reject this request" or "try this route last." That decision lives entirely in `Router.app()`'s `partial`/`partial_scope` accumulation. The constraint doesn't know its own power — whether its soft rejection is honored or overridden is invisible to it.

---

### The Improvement Is Now Code — Apply the Diagnostic

**What does `MethodConstraint` conceal?**

It conceals that `permits()` is called twice in structurally different contexts — pre-scope-update and post-scope-update — and that this two-call pattern isn't an accident but a *necessary consequence* of having no typed return channel. `MethodConstraint` makes the duplication look like a cleanup opportunity when it's actually a load-bearing constraint.

**Property of the original problem visible because the improvement recreates it:**

The improvement's clean shared object makes it obvious that **scope at match-time and scope at handle-time are different objects** (handle-time scope contains the child_scope update). The original code's inline `self.methods` checks hide this because `scope["method"]` is stable. But `MethodConstraint` exposes it: any non-trivial constraint — one that reads `scope["path_params"]` or `scope["endpoint"]` — would see different data in `matches()` vs `handle()`. The improvement recreates the two-context evaluation problem in a form that makes it impossible to ignore.

---

### Second Improvement: Address the Two-Context Evaluation

Store the constraint result in scope so it's computed exactly once:

```python
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
            method_permitted = self.method_constraint.permits(scope["method"])
            child_scope = {
                "endpoint": self.endpoint,
                "path_params": path_params,
                "_route_method_permitted": method_permitted,   # computed once
            }
            return Match.FULL if method_permitted else Match.PARTIAL, child_scope
    return Match.NONE, {}

async def handle(self, scope, receive, send):
    if not scope.get("_route_method_permitted", True):   # read stored result
        headers = self.method_constraint.rejection_headers()
        if "app" in scope:
            raise HTTPException(status_code=405, headers=headers)
        response = PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
        await response(scope, receive, send)
    else:
        await self.app(scope, receive, send)
```

**Apply the diagnostic again.**

**What does this conceal?**

`_route_method_permitted` is stored in scope — the same scope dict that flows through the entire ASGI chain. There is no enforcement preventing application code from reading or writing `_route_method_permitted`. More critically: if a `Mount` wraps this `Route`, the key persists across routing levels. A Route nested inside two Mounts will carry `_route_method_permitted` set by the innermost `Route.matches()`, but any middleware sitting between the Router and the Route will see it in scope with no context about which routing level set it.

**Property of the original problem visible because the improvement recreates it:**

The stored key exposes that **scope is shared, mutable, untyped global state** — not a typed communication channel. The improvement trades "check twice" for "contaminate scope." It recreates the same core problem in a form that bleeds beyond the routing layer: routing metadata is now visible to application handlers and middleware. The original inline double-check was contained within the routing system. This improvement breaks containment.

---

### The Structural Invariant

Through every improvement — inline duplication → shared constraint object → stored constraint result — one property persists:

> **In ASGI routing, any decision made during `matches()` must be either re-computed in `handle()` or stored in the mutable scope dict, because ASGI provides no typed return channel for routing metadata between the match phase and the dispatch phase.**

This is not an implementation choice. It is forced by `async def callable(scope, receive, send) -> None`. The total routing decision information cannot be eliminated — it can only migrate between storage locations: double-computation, scope pollution, or instance state (which fails because Route instances are shared across concurrent requests).

---

### Invert the Invariant

Make it trivially satisfiable: **give `handle()` a typed input from `matches()`**:

```python
@dataclass
class MatchResult:
    path_params: dict
    method_permitted: bool
    allowed_methods: set[str] | None


class Route(BaseRoute):
    def matches(self, scope) -> tuple[Match, MatchResult | None]:
        if scope["type"] == "http":
            route_path = get_route_path(scope)
            m = self.path_regex.match(route_path)
            if m:
                matched_params = {k: self.param_convertors[k].convert(v)
                                  for k, v in m.groupdict().items()}
                path_params = {**scope.get("path_params", {}), **matched_params}
                permitted = self.method_constraint.permits(scope["method"])
                result = MatchResult(path_params, permitted, self.method_constraint.allowed)
                return (Match.FULL if permitted else Match.PARTIAL), result
        return Match.NONE, None

    async def handle(self, scope, receive, send, *, match_result: MatchResult) -> None:
        # No re-computation, no scope contamination
        if not match_result.method_permitted:
            headers = {"Allow": ", ".join(sorted(match_result.allowed_methods))}
            if "app" in scope:
                raise HTTPException(status_code=405, headers=headers)
            response = PlainTextResponse("Method Not Allowed", status_code=405,
                                        headers=headers)
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)
```

**The new impossibility:**

`Mount.handle()` delegates to `self.app(scope, receive, send)` — an arbitrary ASGI application. The typed `match_result` parameter cannot be passed to a third-party ASGI app without breaking the ASGI interface contract. Any ASGI middleware, sub-application, or framework that wraps a Router will not accept `match_result`. Typed routing metadata cannot propagate past the routing layer's boundary with arbitrary ASGI applications.

---

### The Conservation Law

**Routing decision information is conserved across all representations:**

> Reducing the ambiguity of routing decision storage within the routing layer (from "checked twice" → "shared object" → "stored result" → "typed parameter") creates an equivalent increase in coupling ambiguity at the boundary with the application layer (from "contained" → "slightly exposed" → "scope-contaminating" → "ASGI-contract-violating").

The total "routing decision debt" cannot be eliminated. Every architectural improvement moves it — from double-computation cost to scope pollution to interface violation — but the debt is conserved. You are always trading one form of it for another.

---

### Apply the Diagnostic to the Conservation Law Itself

**What does the conservation law conceal?**

The conservation law frames the problem as information-theoretic — routing decision information must go somewhere. This framing conceals a specific architectural question: *why does routing need to make decisions that persist past the matching phase at all?* The law treats phase separation (match, then select, then handle) as a given. It doesn't ask why the phases are separate.

**Structural invariant of the law:**

Every improvement, and the law itself, treats matching and handling as necessarily distinct phases. This phase separation is itself the invariant the law never questions.

**Invert that invariant:**

Make matching and handling a single atomic operation:

```python
class Route(BaseRoute):
    async def try_handle(self, scope, receive, send) -> bool | PartialMatch:
        """Returns True if handled, PartialMatch if path matched but rejected, False if unmatched."""
        if scope["type"] != "http":
            return False
        route_path = get_route_path(scope)
        m = self.path_regex.match(route_path)
        if not m:
            return False
        matched_params = {k: self.param_convertors[k].convert(v) for k, v in m.groupdict().items()}
        local_scope = {**scope, "path_params": {**scope.get("path_params", {}), **matched_params},
                       "endpoint": self.endpoint}
        if not self.method_constraint.permits(scope["method"]):
            return PartialMatch(allowed_methods=self.method_constraint.allowed)
        await self.app(local_scope, receive, send)
        return True
```

No scope mutation. No Match enum. No two-location checking. Constraint evaluated once, in the only context that exists.

**The new impossibility:**

```python
# Router.app() — redirect_slashes requires this:
for route in self.routes:
    match, child_scope = route.matches(scope)           # FIRST PASS: current path
    ...
# No FULL match found — try modified path:
redirect_scope = dict(scope)
redirect_scope["path"] = redirect_scope["path"] + "/"
for route in self.routes:
    match, child_scope = route.matches(redirect_scope)  # SECOND PASS: modified path
    if match != Match.NONE:
        # redirect
```

If `try_handle` is atomic — it either handles the request or returns — you cannot do a "dry run" against a modified path. You cannot inspect whether a route *would* match `/items/` before committing to redirect from `/items`. The `redirect_slashes` feature requires two complete passes over the route list with two different path variants, inspecting without dispatching. Atomic match-handle makes this structurally impossible.

**The new impossibility**: *A routing system cannot simultaneously support atomic match-execute operations and multi-route pre-dispatch inspection.*

---

### The Conservation Law of the Conservation Law — The Meta-Law

The conservation law said: *routing decision information is conserved; reducing it in one place increases coupling elsewhere.*

The inversion of the law's invariant reveals: the law describes the symptoms of phase separation but conceals its **specific cause**.

The meta-law:

> **The structural phase separation between `matches()` and `handle()` in this routing system is not caused by ASGI's void callable signature — it is caused specifically by the `redirect_slashes` feature, which requires two-pass route inspection against different path variants before dispatching any request. ASGI's void signature determines *where* the decision must be stored; `redirect_slashes` determines *that* phases must be separate at all.**

The conservation law treated phase separation as fundamental. The meta-law identifies it as contingent — contingent on one specific feature.

---

### Concrete, Testable Consequence

Remove `redirect_slashes` from `Router`, and the following becomes architecturally achievable without any form of scope mutation, double-checking, or ASGI contract violation:

- Replace `Match` enum with `try_handle() -> bool | PartialMatch`
- Eliminate `scope.update(child_scope)` entirely
- Evaluate method constraints exactly once, in one location, against stable scope
- Store no routing metadata in scope
- Thread no typed parameters outside the routing layer

Re-add `redirect_slashes`, and you are structurally forced to reintroduce either:
1. Phase separation (match without dispatch, then decide), requiring scope mutation or result storage, or
2. A speculative dispatch mechanism (try the redirect path, capture whether it would match, abandon it), requiring some form of the typed-result interface that violates the ASGI contract for third-party apps

**The testable prediction**: Fork Starlette, delete `redirect_slashes`, implement `try_handle()`-style atomic routing. The Match enum, `scope.update(child_scope)`, and the two-location method check all disappear naturally. Re-add `redirect_slashes`: they all return, in some form, by structural necessity.

The conservation law isn't about information theory. It's about a specific feature's demand for pre-dispatch multi-path inspection, which forces every other structural complexity into existence.
