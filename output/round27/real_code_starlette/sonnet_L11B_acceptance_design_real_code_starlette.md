## The Analysis

---

### I. The Claim

**`Match.PARTIAL` is semantically split between two incompatible meanings — "path matched, method didn't" (a rejection signal in `Route`) and "best candidate for fallback dispatch" (a selector signal in `Router`) — and this dual meaning forces `handle()` to re-examine what `matches()` already determined, creating a two-phase protocol whose first phase mutates shared state before the second phase can reject the request.**

Falsifiable. Counter-arguments: PARTIAL is intentional three-state routing; `handle()` is the authoritative enforcement point, not duplication; `matches()` is a pure query. All defensible. Let's run the debate.

---

### II. Three Experts

**The Defender:** The PARTIAL/FULL/NONE trichotomy is the mechanism by which a Router finds the "least wrong answer" across all routes before committing. `matches()` is declarative — it describes what this route *could* handle. `handle()` is imperative — it *does* handle it. The method check appears twice because they serve different purposes: `matches()` is used to rank candidates, `handle()` is used to enforce constraints. The duplicate is intentional separation of concerns.

**The Attacker:** The claim understates the problem. The issue isn't PARTIAL's dual meaning — it's that `scope.update(child_scope)` executes *before* `handle()` is called. So when a PARTIAL match is promoted to dispatch, the scope already carries `endpoint` pointing to a route that will reject the request with a 405. The scope is corrupted from the perspective of any upstream error handler or middleware that reads it after dispatch. The dual-meaning of PARTIAL is just the symptom. The cause is that the protocol commits before it can validate.

**The Prober (examining shared assumptions):** Both of you assume that `matches()` and `handle()` *should* be separate phases. Both assume that scope-as-dict is the right carrier for routing state. Both assume the three-method protocol on `BaseRoute` is the correct decomposition. But look at what `child_scope` actually is: it's the output of a match *and* the input to a handle. It's simultaneously a query result and a configuration. The same dict does both jobs. The enum value (PARTIAL/FULL) is not the real protocol — `child_scope`'s content *is* the protocol, and neither of you questioned it.

**The Transformation:** The claim shifts from "PARTIAL is semantically overloaded" to: *the routing protocol encodes a hidden ordering dependency where `matches()` produces state that `handle()` must consume, and scope mutation is the carrier of this dependency — making the first phase of a two-phase commit invisible at the type level.*

**The gap:** I started with an enum semantics problem. I now have a stateful protocol problem. The enum is a symptom. The concealment mechanism hid the cause.

---

### III. The Concealment Mechanism

**Nominalized mutation.** `scope.update(child_scope)` reads as data enrichment — "adding routing context to the scope" — but it functions as a dispatch commitment. The dict update looks like a read operation producing output; it is actually the first half of a write protocol that cannot be undone. The concealment is that `child_scope` is named as if it's the *result* of matching, when it is actually the *precondition* for handling. Python's dict idiom (`scope.update(...)`) makes a one-way commitment look like bidirectional information flow.

Secondary mechanism: the `Match` enum names obscure what PARTIAL actually tracks. "Partial" implies spatial incompleteness (matched prefix but not full path). But in `Route`, PARTIAL means temporal incompleteness (path decision made, method decision deferred). The name mismatches the semantics.

---

### IV. Improvement 1: Deepen the Concealment (Passes Review)

Introduce a typed `MatchResult` dataclass that makes scope mutation explicit, structured, and *named as safe*:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class MatchResult:
    """Encapsulates the result of a route match operation."""
    match: Match
    endpoint: Any = None
    path_params: dict = field(default_factory=dict)
    root_path: str = ""
    app_root_path: str = ""

    def apply_to_scope(self, scope: dict) -> None:
        """Apply matched routing context to request scope."""
        if self.endpoint is not None:
            scope["endpoint"] = self.endpoint
        existing = dict(scope.get("path_params", {}))
        existing.update(self.path_params)
        scope["path_params"] = existing
        if self.root_path:
            scope["root_path"] = self.root_path
        if self.app_root_path:
            scope["app_root_path"] = self.app_root_path

    @classmethod
    def none(cls) -> "MatchResult":
        return cls(match=Match.NONE)
```

Update `Route.matches()` to return `MatchResult` instead of a tuple. Update `Router.app()` to call `result.apply_to_scope(scope)` before dispatch.

**Why this passes review:** Type safety over opaque dicts. Explicit mutation point. Self-documenting. Named constructor for the no-match case. All senior engineers approve.

**Why this deepens the concealment:**

The three-tuple `(Match, dict)` was at least legible as "here is a verdict and here is some data." The `MatchResult` with `apply_to_scope()` makes the mutation look like a *method responsibility* — the result is in charge of its own application. This hides that `apply_to_scope()` is the first half of a two-phase commit, because a method named `apply_to_scope` sounds like a safe idempotent operation. The commitment is now invisible *behind an API*.

---

### V. Three Properties Only Visible Because We Tried to Strengthen

**1. `child_scope` is a promise, not data.** When we tried to type it as a `MatchResult`, we were forced to decide: should the struct carry the route reference? Should it carry a callable? The discomfort reveals that `child_scope` isn't just state — it's a contract between `matches()` and `handle()`. The `endpoint` key inside it is a commitment that dispatch will occur to that endpoint. Typing it as "data" is a lie.

**2. `path_params` accumulation is additive across nesting levels.** When we wrote `existing.update(self.path_params)`, we realized this isn't a replace — outer params survive inner matches. The MatchResult struct suggests a clean record, but the actual semantic is append-only accumulation across recursive descent. The struct gives false completeness; the real path_params are assembled across multiple `apply_to_scope` calls at different nesting levels.

**3. `apply_to_scope` crosses a layer boundary carrying mutable intent.** The MatchResult is created at Route level but `apply_to_scope` is called at Router level. A struct that carries both data and a method that mutates caller-owned state is coupling Route's internal decisions to Router's dispatch loop — but the coupling is invisible because it's dressed as a method call.

---

### VI. Improvement 2: Contradict Improvement 1 (Also Passes Review)

Eliminate PARTIAL entirely. Separate path topology from method validation. Make `matches()` answer only "does this path belong here?"

```python
class Route(BaseRoute):
    def matches(self, scope):
        """Returns FULL or NONE based on path only. Never PARTIAL."""
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
                return Match.FULL, child_scope
        return Match.NONE, {}

    def method_allowed(self, scope) -> bool:
        """Separate, explicit method validation."""
        return not self.methods or scope["method"] in self.methods
```

Update `Router.app()`:

```python
async def app(self, scope, receive, send):
    path_match = None
    path_scope = None

    for route in self.routes:
        match, child_scope = route.matches(scope)
        if match == Match.FULL:
            if route.method_allowed(scope):
                scope.update(child_scope)
                await route.handle(scope, receive, send)
                return
            elif path_match is None:
                path_match = route
                path_scope = child_scope

    if path_match is not None:
        scope.update(path_scope)
        await path_match.handle(scope, receive, send)
        return

    await self.default(scope, receive, send)
```

**Why this passes review:** Single-responsibility `matches()`. No semantic overloading. Explicit method gate before commit. Cleaner than PARTIAL promotion. Different senior engineers approve.

---

### VII. The Structural Conflict

Apply both improvements simultaneously:
- Improvement 1 says: **MatchResult owns the commit**. `apply_to_scope()` is the MatchResult's responsibility. The Router just calls it.
- Improvement 2 says: **Router owns the commit**. The Router decides whether to commit based on `method_allowed()`. The Router calls `scope.update()` only after validation.

These require contradictory ownership of the dispatch decision:

| Question | Improvement 1 | Improvement 2 |
|----------|---------------|---------------|
| Who decides when to commit? | MatchResult | Router |
| Where is method logic? | In handle() | In method_allowed() on Route |
| What does matches() return? | MatchResult (opaque) | (Match, dict) + separate query |
| Who calls scope.update? | MatchResult.apply_to_scope | Router.app directly |

If you have both: MatchResult has `apply_to_scope()`, but Router must call `route.method_allowed()` *before* calling `result.apply_to_scope()`. Now `apply_to_scope` cannot be called inside `MatchResult.__init__` or eagerly — it must wait. But if Router controls when `apply_to_scope` is called, why does MatchResult have that method? And if MatchResult doesn't call it eagerly, it's not encapsulation — it's a deferred callback dressed as an object.

**The structural conflict:** Encapsulating routing state (Improvement 1) and separating routing concerns (Improvement 2) require contradictory answers to "who owns the dispatch commitment."

---

### VIII. Improvement 3: Resolve the Conflict (Passes Review)

Two-stage commit protocol. MatchResult is a proposal; a separate `Commit` object is created only after validation:

```python
@dataclass
class RouteProposal:
    match: Match
    child_scope: dict
    route: "BaseRoute"

    def is_method_valid(self, scope: dict) -> bool:
        return getattr(self.route, "method_allowed", lambda s: True)(scope)

    def commit(self, scope: dict) -> None:
        scope.update(self.child_scope)


class Route(BaseRoute):
    def propose(self, scope) -> RouteProposal:
        """Returns a proposal without committing anything."""
        ...  # same logic as matches(), returns RouteProposal


class Router:
    async def app(self, scope, receive, send):
        proposals = []
        for route in self.routes:
            proposal = route.propose(scope)
            if proposal.match != Match.NONE:
                proposals.append(proposal)

        for proposal in proposals:
            if proposal.is_method_valid(scope):
                proposal.commit(scope)
                await proposal.route.handle(scope, receive, send)
                return

        if proposals:
            proposals[0].commit(scope)
            await proposals[0].route.handle(scope, receive, send)
            return

        await self.default(scope, receive, send)
```

This satisfies both: the proposal object encapsulates routing state (Improvement 1), and the Router controls when commitment occurs based on a separate validity check (Improvement 2). Both reviewers sign off.

---

### IX. How It Fails

**It fails at nesting depth.** When `Router.app()` dispatches to a `Mount`, `Mount.handle()` calls `self.app(scope, receive, send)`, which calls a *nested Router*'s `app()`, which runs its own `propose()` loop. The `RouteProposal` and two-stage commit at the outer level don't propagate inward. Each nested Router does its own eager `scope.update(child_scope)` internally before returning — the recursive descent is not proposal-based.

Concretely: `Mount.matches()` correctly returns a `RouteProposal` at the outer level. The outer Router commits it and calls `Mount.handle()`. Inside `Mount.handle()`, `self.app(scope, receive, send)` fires the inner Router, which calls the *old* `matches()` (or the *old* `propose()`) on inner routes. The inner routes `scope.update()` without going through the outer two-stage protocol. Method validation at the outer level does nothing for method validation at any inner level.

The "correct" fix would require every nested Router to use the same proposal protocol. But then `Mount`'s `handle()` would need to thread a proposal context downward — and ASGI's calling convention is `(scope, receive, send)`. There's no fourth parameter for a routing context object.

---

### X. What the Failure Reveals

The conflict (Improvement 1 vs. Improvement 2) told us: *ownership of the dispatch commitment is ambiguous*. We thought the problem was about deciding who calls `scope.update`.

The failure of Improvement 3 reveals something the conflict alone could not: **the commit is not a single event — it is a recursive series of events distributed across the call tree, one at each nesting level.** There is no single commit point to make two-phase, because routing is not a single decision; it is a recursive descent where each level makes its own local commitment before delegating to the next.

This reveals the design space's actual topology: any protocol that attempts to defer commitment at level N will succeed at level N and fail at level N+1, because level N+1's scope mutations happen inside level N's dispatch, after level N's protocol has concluded. The design space does not contain a feasible two-phase commit — it contains an unbounded series of one-phase commits, one per nesting level, each invisible to the levels above it.

---

### XI. The Redesign: Accept the Topology

Don't fight the recursive structure. Accept that routing is recursive and scope is the channel. Redesign to make the recursion **explicit and traversable** without trying to defer any commits.

```python
@dataclass(frozen=True)
class RouteMatch:
    route: "BaseRoute"
    path_params: dict
    matched_path: str
    remaining_path: str
    depth: int = 0

class Route(BaseRoute):
    def resolve(self, path: str, method: str) -> RouteMatch | None:
        """Pure function: no scope, no side effects. Returns match or None."""
        match = self.path_regex.match(path)
        if not match:
            return None
        params = {k: self.param_convertors[k].convert(v)
                  for k, v in match.groupdict().items()}
        return RouteMatch(route=self, path_params=params,
                          matched_path=path, remaining_path="", depth=0)

    def allows_method(self, method: str) -> bool:
        return not self.methods or method in self.methods

class Router:
    def resolve(self, path: str, method: str) -> list[RouteMatch]:
        """Collect ALL matches at all depths. Pure traversal."""
        results = []
        for route in self.routes:
            match = route.resolve(path, method)
            if match:
                results.append(match)
        return results

    async def app(self, scope, receive, send):
        path = get_route_path(scope)
        method = scope.get("method", "")
        
        matches = self.resolve(path, method)
        valid = [m for m in matches if m.route.allows_method(method)]
        
        if valid:
            m = valid[0]
            scope["endpoint"] = m.route.endpoint
            scope["path_params"] = {**scope.get("path_params", {}), **m.path_params}
            await m.route.handle(scope, receive, send)
            return
        
        if matches:
            m = matches[0]
            scope["endpoint"] = m.route.endpoint
            scope["path_params"] = {**scope.get("path_params", {}), **m.path_params}
            await m.route.handle(scope, receive, send)
            return
        
        await self.default(scope, receive, send)
```

**What it sacrifices:**

1. **ASGI middleware compatibility.** Any middleware that wraps the app and reads `scope["endpoint"]` or `scope["path_params"]` after the fact relied on scope being mutated during dispatch. Pure `resolve()` doesn't mutate scope until the very end — middleware that reads scope mid-chain breaks.
2. **Incremental Mount nesting.** `Mount` currently works by stripping a path prefix and delegating to an inner app that knows nothing about the outer match. The `resolve()` approach requires the Router to traverse into Mounts' inner routers, which means Router must know about Mount's internal structure — layering violation.
3. **Third-party route compatibility.** Every `BaseRoute` subclass in the ecosystem must implement `resolve()`. The existing `matches()` API is the public contract.
4. **Lifespan and WebSocket dispatch.** The redesign only handles HTTP cleanly. WebSocket routing has different semantics that `resolve()` doesn't capture.

**What the redesign reveals was never a flaw:**

The scope mutation — `scope.update(child_scope)` — was never a design error. It was the **cost of attempting three things simultaneously**:

1. **ASGI compliance:** ASGI mandates that routing state lives in scope. There is no other channel.
2. **Recursive composability:** Mount can nest arbitrarily deep. Each level needs to pass routing state to the next without knowing what the next is.
3. **Handler transparency:** Any handler receives a fully-populated scope with `path_params`, `endpoint`, and `root_path` already resolved — no handler needs to know it was nested.

These three requirements together have only one solution given ASGI's protocol: mutate scope in-place at each recursion level, committing incrementally as you descend. The "flaw" — that scope is mutated before handle() can reject — is not a mistake. It is the exact price of working inside ASGI's single-dict topology while maintaining composability across arbitrary nesting depth.

The original design isn't hiding a problem. It is truthfully representing a constrained design space where scope mutation is not a code smell but a **structural necessity** — one that any redesign that stays inside ASGI will rediscover, and any redesign that escapes it will sacrifice ASGI compatibility in exchange.

The real concealment was never in the code. It was in the assumption that the scope mutation was a local implementation choice that could be refactored away. It cannot. It is load-bearing.
