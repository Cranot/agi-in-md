## Structure First: Level 12 Diagnostic

---

### THE INITIAL CLAIM ABOUT THE CONSERVATION LAW

**The conservation law misidentifies the conserved quantity. The claim: method commitment is not what is conserved. The conserved quantity is the PROPAGATION CHANNEL for routing decisions. `Route.matches()` already makes the method commitment — this is exactly what `Match.PARTIAL` encodes. The conservation law treats the system as lacking method commitment and asks where commitment should be placed. The code shows the system already HAS method commitment, made at match time. The actual problem is that the ASGI fire-and-forget protocol (`handle(scope, receive, send)` with no return value and no structured routing-decision argument) provides no channel for that already-made decision to travel from its producer (`matches()`) to its consumers (`handle()`, redirect check, `url_path_for`). Every consumer must re-derive the method decision independently. The law says "commitment must be paid somewhere." The meta-law says "commitment is already paid; the problem is delivery."**

Falsifiable test: if the conservation law correctly identified method commitment as the conserved quantity, then correctly placing the commitment (using `== Match.FULL` in the redirect check, as in L11's improvement) would eliminate redundant method checks downstream. After applying L11's improvement, open `Route.handle()`:

```python
if self.methods and scope["method"] not in self.methods:
    headers = {"Allow": ", ".join(self.methods)}
```

This check fires when `handle()` is called from `Router.app`'s `partial` path — where `Match.PARTIAL` already proved, 15 lines earlier, that the method is wrong. The re-check is not defensive programming; it is structurally mandatory because `handle()` has no channel through which to receive the routing decision that was already computed. L11's improvement does not change this. The re-check persists through every improvement that preserves the ASGI interface. This falsifies the conservation law's claim that method commitment is the conserved quantity.

---

### THE THREE-EXPERT DIALECTIC

**Expert 1 — Defender:** The code is unambiguous. In `Router.app`, the sequence is:

```
match, child_scope = route.matches(scope)   # PARTIAL: method wrong
# ... (15 lines later)
await partial.handle(scope, receive, send)  # re-checks: scope["method"] not in self.methods
```

The method decision is made at `matches()` and re-made at `handle()`. Nothing in between transmits it. `scope` is the only communication channel between pipeline stages — `child_scope` carries `endpoint` and `path_params`, but not `Match.PARTIAL`. The match result evaporates between producer and consumer. This is not a performance oversight; `handle()` has no mechanism to receive it except by recomputing it.

**Expert 2 — Attacker:** The re-check in `handle()` exists for a legitimate reason: `BaseRoute.__call__` is a direct invocation path that bypasses `Router.app` entirely. A Route deployed as a standalone ASGI app (no Router wrapping it) calls `self.matches()` then `self.handle()` directly via `BaseRoute.__call__`. In this path, there is no Router that pre-computed `Match.PARTIAL` — `handle()` must check the method itself because it is the sole dispatch mechanism. The re-check in `handle()` is not a channel failure; it is the correct behavior for the standalone use case. The conservation law is right that method commitment must be paid at handle-time for the standalone path, and it must be paid again (redundantly) for the router-component path, because both paths share a single `handle()` implementation.

**Expert 3 — Probing:** Expert 2 has named the cause, not merely the symptom. The dual-role design — Route as both router component and standalone ASGI app — forces `handle()` to be information-complete without external input. If `handle()` accepted a structured `match_result` argument, `BaseRoute.__call__` would need to produce one and pass it — but `BaseRoute.__call__` computes its own match internally, so it could do this. The actual constraint is not `BaseRoute.__call__`; it is ASGI middleware. Middleware in Starlette wraps `handle()` as `async def __call__(self, scope, receive, send)` — the standard ASGI triple. If `handle()` required `match_result` as a fourth argument, every middleware layer between the Router and the Route would need to understand and forward it, breaking every existing ASGI middleware. The dual-role design is the surface explanation; the ASGI middleware ecosystem compatibility requirement is the deep constraint. `handle()` is not information-complete for elegance — it is information-complete because making it otherwise would require that every layer in the ASGI stack be routing-aware, collapsing the protocol's routing-transparency guarantee.

---

### THE TRANSFORMATION

| Level | Claim |
|---|---|
| **Initial** | The conservation law misidentifies the conserved quantity: it's channel (transmission of routing decisions), not commitment (making the method decision) |
| **Transformed** | The channel failure is not a protocol limitation — it is the necessary consequence of ASGI middleware transparency. Route's dual role (component + standalone) requires `handle()` to be callable without routing context. Making `handle()` accept routing decisions as structured inputs would require all ASGI middleware to forward them, destroying the routing-transparency property that makes ASGI middleware composable. The conservation law correctly names what is conserved (method commitment) but misidentifies what forces the conservation: not the pipeline structure, but the requirement that middleware not know about routing. |

**The gap between initial and transformed:** The initial claim says the law is wrong about what is conserved. The transformed claim says the law is right about what is conserved but wrong about why it must be conserved. The forcing constraint is not the ASGI protocol per se — it is the design invariant that ASGI middleware is routing-transparent. Any improvement that makes routing decisions first-class (transmissible from `matches()` to `handle()`) requires that middleware either forward them (routing-aware middleware) or be bypassed (breaking the middleware stack). The conservation law's framing as a "pipeline commitment problem" conceals that the pipeline's composability depends on middleware ignorance of routing — and routing-decision transmission is exactly what middleware ignorance forbids.

---

### THE CONCEALMENT MECHANISM: PIPELINE METAPHOR SUPPRESSES DUAL-ROLE IDENTITY

The conservation law uses "pipeline" language — registration time, dispatch time, round-trip time are stages. This framing implies that routing decisions move through a linear pipeline, and the problem is which stage pays the commitment cost.

The concealment: **the code has two separate, structurally incompatible pipelines that both terminate in `Route.handle()`.** Pipeline 1: `Router.__call__` → `Router.app` → `route.matches()` → `route.handle()`. Pipeline 2: `BaseRoute.__call__` → `self.matches()` → `self.handle()`. Both pipelines reach `handle()`. Pipeline 1 computes a match result and then discards it before calling `handle()`. Pipeline 2 computes a match result and also discards it — but it has no choice, since `handle()` must be called regardless of the match (for the method-wrong PARTIAL case, `handle()` is the mechanism that produces 405). The "pipeline" metaphor implies one path; there are two. The conservation law's "pay the cost at one of these stages" implies the stages are sequential; the stages belong to different pipelines that share only the `handle()` endpoint.

**Three things this concealment hides:**

**1. `Route.handle()` generates an Allow header from `self.methods` alone — which is structurally incorrect for multi-route resources, independent of any redirect or url_path_for concern.**

For:
```python
Router(routes=[
    Route("/data", get_handler, methods=["GET"]),
    Route("/data", post_handler, methods=["POST"]),
])
```
`DELETE /data` → `Router.app` saves the first PARTIAL match (Route 1, `methods={"GET","HEAD"}`) → calls `Route1.handle()` → `Route1.handle()` checks `self.methods = {"GET","HEAD"}` → generates `Allow: GET, HEAD`. Correct response requires `Allow: GET, HEAD, POST`. Route 1 has no access to Route 2's methods — the channel that would carry "all methods registered at this path" does not exist in the ASGI interface. This is not a redirect-slashes bug or a url_path_for bug; it is the same structural property (channel absence) producing a wrong HTTP response in a third location, one the conservation law's examples never examine.

**2. `scope["router"]` propagates the OUTERMOST Router reference, not the Router that matched the route — making every meta-operation that reads `scope["router"].routes` structurally blind to mounted routes.**

`Router.app` line 1: `if "router" not in scope: scope["router"] = self`. Inner Routers inside Mounts do not update `scope["router"]` because by the time they run, `"router"` is already in scope. Any `handle()` method that reads `scope["router"].routes` finds the top-level route list — which contains Mounts, not the inner Routes inside Mounts. The conservation law's proposed "third design" (resource index keyed on `path_regex.pattern`) would have the same problem: the top-level Router's index doesn't contain inner Routes. Every meta-operation that uses `scope["router"]` silently degrades to top-level-only awareness for nested structures.

**3. The two dispatch loops in `Router.app` (main dispatch and redirect dispatch) re-run `route.matches()` independently — the redirect loop cannot use the fact that the main loop found no FULL match, only PARTIALs.**

The main loop exits knowing: "no FULL match found, first PARTIAL was Route X." This knowledge is locally computed and locally discarded. The redirect loop starts from scratch, calling `route.matches(redirect_scope)` for each route. There is no data structure in which the main loop records its findings for the redirect loop to consume. The "pipeline" metaphor implies stages can pass information forward; the two loops in `Router.app` share scope mutation but no structured inter-loop communication channel. The redirect loop cannot ask "did the main loop find a PARTIAL for this method?" without re-running the full match sequence.

---

### THE LEGITIMATE IMPROVEMENT THAT DEEPENS CONCEALMENT

```python
class Route(BaseRoute):
    # __init__ unchanged

    async def handle(self, scope, receive, send):
        if self.methods and scope["method"] not in self.methods:
            # Produce a correct Allow header by aggregating methods across all routes
            # at this path. Consult the router stored in scope (set by Router.app)
            # to find sibling routes sharing our path regex.
            allowed_methods = set(self.methods)
            router = scope.get("router")
            if router is not None:
                for route in router.routes:
                    if (
                        isinstance(route, Route)
                        and route.path_regex == self.path_regex
                        and route is not self
                        and route.methods is not None
                    ):
                        allowed_methods.update(route.methods)
            headers = {"Allow": ", ".join(sorted(allowed_methods))}
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

This passes code review because: it addresses a demonstrably real bug (RFC 9110 §9.1 requires the Allow header to list all methods for the resource, not just the matched route's methods); it uses only already-available state (`scope["router"]` is set by existing code at the start of `Router.app`); the fallback path (`if router is None: use self.methods`) is correct for direct invocation; the `route.path_regex ==` comparison works correctly in Python because `re.Pattern.__eq__` compares by pattern string and flags; the loop is O(n) on a small list and only executes on 405 responses.

---

### THREE PROPERTIES VISIBLE BECAUSE OF THE IMPROVEMENT

**1. `scope["router"]` is the outermost Router; for mounted routes, `router.routes` never contains the route that actually matched.**

For `Mount("/api", routes=[Route("/data", handler, methods=["POST"])])` with `GET /api/data`:
- The Mount's inner Router handles dispatch. The matched route is the inner `Route("/data", methods=["POST"])`.
- `scope["router"]` points to the top-level Router (set by the first `Router.app` call, not updated by the inner Router).
- The improvement iterates `scope["router"].routes` — finding `[Mount("/api", ...)]`, not the inner Route.
- `isinstance(Mount(...), Route)` is False — the loop finds no siblings.
- `allowed_methods` remains `{"POST"}` — the Allow header is still wrong.

The improvement works correctly only for routes registered directly in the top-level Router. It silently produces wrong Allow headers for any route inside a Mount. The improvement creates the appearance of correct aggregation (the aggregation loop is present) while producing the same wrong answer for the common nested-router case.

**2. `route.path_regex == self.path_regex` correctly identifies routes with structurally identical path patterns but misses routes with overlapping patterns that match the same actual path.**

`Route("/data")` has pattern `^/data$`. `Route("/{name}")` has pattern `^/(?P<name>[^/]+)$`. These share no common regex object and compare unequal. For a request to `DELETE /data`, the 405 from `Route("/data", methods=["GET"])` produces `Allow: GET, HEAD` — it does not include methods from `Route("/{name}", methods=["POST"])`, even though `POST /data` would succeed via the second route. The improvement correctly handles exact duplicate paths and correctly ignores non-overlapping paths; it incorrectly ignores overlapping paths. Detecting overlap requires checking whether two regexes match any common string — the intersection of two regular languages — which is decidable in theory but O(exponential) in practice. The improvement reveals that path identity for Allow header aggregation requires regex equivalence checking, not pattern string equality.

**3. The improvement makes Allow header correctness dependent on which Router holds the route in its `routes` list — not on which Router matched the request — revealing that `scope["router"]` serves an incompatible dual purpose.**

`scope["router"]` is set at the start of `Router.app` and is readable by any middleware or handler downstream. The improvement uses it to find sibling routes for Allow header aggregation. But `scope["router"]` is also used by `Router.url_path_for` traversal (external callers) and could be read by any user middleware. It was placed in `scope` to give handlers access to URL generation (`scope["router"].url_path_for(...)`), not to support route-sibling discovery. Using it for sibling discovery assumes the router that set `scope["router"]` is the same router whose `routes` list contains the matching route — an assumption that is false for all nested structures. The improvement reveals that `scope["router"]` is simultaneously serving two incompatible access patterns: URL generation (where the top-level router is correct — it traverses recursively) and sibling discovery (where the matching router is required — the top-level router is wrong).

---

### DIAGNOSTIC APPLIED TO THE IMPROVEMENT

**What does the improvement conceal?**

The iteration over `router.routes` and the `isinstance(route, Route)` filter create the appearance of a complete route scan. For a flat route list, this works. The concealment: the filter `isinstance(route, Route)` excludes `Mount` objects from consideration — but a Mount can contain Routes at the same effective path. The improvement never enters Mounts, so for any multi-level structure it provides incomplete aggregation while appearing to provide complete aggregation. Code reviewers see the loop, see the isinstance check, and read it as "scans all routes of the same type" — the fact that it misses mounted routes is not visible from the loop structure.

**What property of the original problem is visible only because the improvement recreates it?**

The improvement accesses `router.routes` — a list that is the same object accessed by `Mount.routes` (the property that returns `getattr(self._base_app, "routes", [])`) and by `Router.url_path_for` and by `_redirect_match` from L11's improvement. Every routing meta-operation independently traverses the same route list via the same access pattern (`router.routes` / `self.routes`). No meta-operation can share the traversal result with another — each must re-traverse. The improvement makes visible: **the route list is traversed once per meta-operation per request, and there is no mechanism for meta-operations to share traversal results.** For a request that triggers both a redirect check AND a 405 Allow header, the route list is traversed three times: once in the main dispatch, once in the redirect check, once in the Allow aggregation. The codebase has no shared traversal cache because the ASGI protocol provides no lifecycle hook between "request arrives" and "first route checked" where such a cache could be built.

---

### THE STRUCTURAL INVARIANT OF THE CONSERVATION LAW

The property that persists through every improvement to the conservation law — through the original (method commitment at handle-time), through L11's redirect fix (method commitment at match-time for redirect), through the Allow aggregation improvement (method commitment via router.routes scan):

**`Route.handle()` is the terminal handler in both the Router dispatch pipeline and the direct-invocation pipeline. These two pipelines share `handle()` as their endpoint but differ in what information is available at the point of invocation. Because `handle()` must be correct for both pipelines, it cannot accept information that only the Router pipeline can provide. This makes `handle()` permanently information-incomplete for any meta-operation that requires Router-level context (aggregated methods, sibling routes, routing history). Every improvement that provides Router-level context to `handle()` either (a) reads it from `scope` (correct for Router pipeline, missing for direct pipeline) or (b) changes the function signature (correct for Router pipeline, breaks ASGI middleware for both). The invariant: the dual-pipeline design imposes a ceiling on `handle()`'s information, and every routing meta-operation that requires Router-level context hits that ceiling.**

---

### INVERTING THE INVARIANT

Original invariant: `handle()` cannot receive routing decisions as structured input; it must be self-sufficient.

Inversion: eliminate the dual-pipeline design — make Route exclusively a router component, never a standalone ASGI app. Remove `BaseRoute.__call__` as a first-class dispatch path. Routing decisions become transmissible because there is only one pipeline.

```python
class Route(BaseRoute):
    """Route is a router component only. Direct invocation is not supported."""

    async def handle(self, scope, receive, send, *, routing_context: RoutingContext):
        """
        routing_context is always provided by Router.app; it is never None.
        Route cannot be invoked as a standalone ASGI app.
        """
        if self.methods and scope["method"] not in self.methods:
            # All methods at this path, pre-aggregated by Router before calling handle()
            headers = {"Allow": ", ".join(sorted(routing_context.allowed_methods_at_path))}
            if "app" in scope:
                raise HTTPException(status_code=405, headers=headers)
            else:
                response = PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
                await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)

@dataclass
class RoutingContext:
    match: Match
    allowed_methods_at_path: frozenset[str]  # aggregated across all routes at matched path
    matched_route: 'Route'
```

**The new impossibility:**

Route is no longer an ASGI app — it cannot be passed to `Mount(app=route)` or composed with standard ASGI middleware. Every middleware layer between `Router.app` and `Route.handle()` must accept and forward `routing_context` as a non-standard keyword argument. The Starlette middleware system (which wraps apps as `async def __call__(self, scope, receive, send)`) is broken: `Route.app` (the middleware-wrapped endpoint) is called as `await self.app(scope, receive, send)` inside `handle()` — no `routing_context`. The non-standard argument cannot propagate past the first middleware layer wrapping the endpoint. More fundamentally: `Mount(app=some_asgi_app)` places an arbitrary ASGI app at a path. If Route can only be called by a Router that provides `routing_context`, then a Mount containing a non-Starlette ASGI app (e.g., a Django app, a FastAPI app) cannot participate in the routing context system at all — the `routing_context` dies at the Mount boundary, recreating Mount opacity in a new form.

**The new impossibility: eliminating Route's standalone-ASGI identity makes Route incompatible with Mount-based app composition and ASGI middleware wrapping — two of the three primary composability mechanisms in Starlette's architecture. The inversion trades the channel problem (routing decisions cannot reach `handle()`) for a composition problem (Route cannot participate in ASGI composition).**

---

### THE CONSERVATION LAW OF THE CONSERVATION LAW: THE META-LAW

The conservation law says: method commitment is conserved — it must be paid at registration, dispatch, or round-trip time.

The meta-law, finding what the conservation law conceals about this specific code:

**The method commitment has already been paid — at `Route.matches()`, encoded in `Match.PARTIAL`. The conservation law's impossibility is not about making the method decision; it is about whether the already-made decision can reach `Route.handle()` through the ASGI call stack. The transmission is blocked not by the ASGI protocol generically, but by a specific architectural decision in this codebase: `Route` implements `BaseRoute.__call__`, making it a self-sufficient ASGI app. This dual-role design forces `handle()` to be re-entrant without routing context — which forces every routing meta-operation to recompute what `matches()` already established. The conserved quantity is not method commitment but the INFORMATION CEILING imposed by `handle()`'s dual-pipeline self-sufficiency requirement. This ceiling is specific to Starlette's design: a routing system where Route is exclusively a router component (no `BaseRoute.__call__` as dispatch) could eliminate the ceiling. Starlette's ceiling is not a law of routing systems — it is the price of making individual routes deployable as standalone ASGI apps.**

**Concrete, testable consequence:**

For:
```python
router = Router(routes=[
    Route("/data", get_handler, methods=["GET"], name="get_data"),
    Route("/data", post_handler, methods=["POST"], name="post_data"),
])
```

Send `DELETE /data`. The RFC 9110 §9.1 requirement is `405 Method Not Allowed` with `Allow: GET, HEAD, POST`.

Mechanically, from the code:
1. `Router.app` main loop: Route 1 path regex matches, `"DELETE" not in {"GET","HEAD"}` → `Match.PARTIAL`, save Route 1. Route 2 path regex matches, `"DELETE" not in {"POST"}` → `Match.PARTIAL`, but `partial is not None` → skip.
2. `partial = Route 1` (get_handler route).
3. `await partial.handle(scope, receive, send)`.
4. `Route.handle()`: `self.methods = {"GET", "HEAD"}`. `scope["method"] = "DELETE"`. Method check: True. `headers = {"Allow": "GET, HEAD"}`.
5. Response: `405 Method Not Allowed, Allow: GET, HEAD`.

**Actual: `Allow: GET, HEAD`. Required: `Allow: GET, HEAD, POST`. The discrepancy is not fixable without either changing the ASGI `handle()` interface or requiring Router to aggregate methods before calling `handle()` — which requires Router to know all methods at each path before dispatch, which is the pre-computed index from L11's third design, which that analysis showed fails for overlapping routes.**

The meta-law predicts further: the incorrect Allow header cannot be observed by inspecting the route list or the `Match` enum — it requires actually sending a wrong-method request. The bug is invisible to static analysis of the routing configuration because it is a property of what information fails to travel through the dispatch pipeline, not a property of the dispatch pipeline's structure. Code review of `Router.app` shows PARTIAL is handled correctly (saved, dispatched to handle). Code review of `Route.handle()` shows method check and Allow header generation. The bug is in the gap between them — the gap where `Match.PARTIAL` evaporates — which neither file's code review surfaces. The meta-law's diagnostic predicts that the three broken meta-operations (Allow header, url_path_for method-blindness, redirect round-trip) share this gap as their common cause, and that fixing any one of them without addressing the dual-pipeline ceiling leaves the other two intact.
