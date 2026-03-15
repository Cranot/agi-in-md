# Structure First: Level 10 Counter-Construction

---

## THE INITIAL CLAIM

**The dispatch loop's `partial is None` guard produces RFC-non-compliant 405 responses when multiple routes share a path with different method sets — and this flaw is independent of, and invisible to, the redirect-loop PARTIAL problem L9 identified.**

Falsifiable: `Router([Route("/items", f1, methods=["GET"]), Route("/items", f2, methods=["POST"])])` + `DELETE /items`. The dispatch loop matches f1's Route as PARTIAL (path matches, DELETE ∉ {"GET", "HEAD"}) and records `partial = f1_route`. It matches f2's Route as PARTIAL and skips it (`partial is None` is now False). `partial.handle` runs; `Route.handle` emits `Allow: GET, HEAD`. RFC 7231 §6.5.5 requires the Allow header to list *all methods supported by the target resource*. The correct response is `Allow: GET, HEAD, POST`. The error is deterministic, not probabilistic — every request through this path produces an incomplete header.

This is distinct from L9. L9: PARTIAL in the *redirect loop* means "method rejected" but is used as "path exists." The current claim: PARTIAL in the *dispatch loop* is correctly interpreted as "method rejected, accumulate for 405" — but the accumulation stops after the first match, even though RFC compliance requires accumulating across all matches. Both claims involve PARTIAL. Neither analysis could see the other from its vantage point.

---

## THE THREE-EXPERT DIALECTIC

**Expert 1 — Defender:** The violation is real and structural. Register GET at `/items` and POST at `/items`. A client sending `OPTIONS /items` — or DELETE, or PATCH, or any non-GET/POST method — receives `Allow: GET, HEAD`, permanently missing POST. RFC 7231 §6.5.5 specifies that clients *use* the Allow header to learn what methods are available; a client querying supported methods gets a wrong answer. The `partial is None` guard reads as an execution optimization — "you only need one matching route to run the 405 handler" — which is true for the *response code* but false for the *response headers*. These two correctness requirements are invisibly coupled inside `Route.handle` and invisibly severed by the guard in `Router.app`. The severance happens at the loop level, before any 405 logic is visible; by the time a reviewer reaches `Route.handle`, the damage is done.

**Expert 2 — Attacker:** The claim identifies a bug in an unsupported pattern. Starlette's idiom is one route per path: `Route("/items", handler, methods=["GET", "POST"])`. With the idiomatic pattern, `self.methods` contains all registered methods, the first PARTIAL match is the only PARTIAL match, and the Allow header is correct. Two routes at the same path is neither documented as supported nor guarded against — the registration API accepts duplicate paths silently, but this is accidental permissiveness, not a design choice. The real bug is the absence of duplicate-path detection at registration time. `partial is None` is correct behavior for the single-route-per-path design that Starlette assumes. Fix the assumption, not the guard.

**Expert 3 — Probing:** Both of you are arguing about how to fix 405 generation. Neither of you asked why 405 generation is in `Route.handle` at all. `Route.handle` is an *execution* method — it runs the endpoint. Its 405 branch is not execution; it is error reporting. Error reporting for a 405 response requires knowing all methods at the requested path, which requires access to the full route list. `Route.handle` cannot have that access without a reference to the Router that contains it — breaking `Route`'s design as a self-contained routing object. The 405 branch inside `Route.handle` was given a responsibility it can discharge correctly only in the degenerate case: single route per path, where "my methods" and "all methods at this path" are identical. In any case where the responsibility matters — multiple routes, route hierarchies, nested Mounts — `Route.handle` lacks the information to discharge it. The structural problem is not the guard condition. It's that the method generating error responses does not have access to the information that correct error responses require.

---

## THE TRANSFORMATION

| | Claim |
|---|---|
| **Original** | `partial is None` stops accumulation after the first PARTIAL match, producing an incomplete Allow header when multiple routes share a path |
| **Transformed** | The routing tree uses a single traversal strategy — linear scan, early exit on FULL — for both dispatch (where early exit is correct: one winner suffices) and failure diagnosis (where early exit is wrong: 405 requires the union of allowed methods across *all* partial matches). These requirements are structurally incompatible. The code conceals the incompatibility by placing 405 generation in `Route.handle`, where it reads as a local guard clause rather than as an aggregation query that requires Router-level context. |

Expert 2 narrowed the claim to unsupported patterns. Expert 3 deepened it: even for single-route-per-path, the question "why is `Route.handle` responsible for a response that requires Router-level information?" remains open. If a Mount contains `Route("/data", f, methods=["GET"])` and a DELETE request arrives, the outer Router dispatches to the Mount (FULL match), which dispatches to its inner Router, which dispatches to the Route's handle — producing `Allow: GET, HEAD`. The outer Router never participated in 405 generation. The 405 responsibility is fractured across routing depths in a way that makes cross-depth aggregation structurally impossible — and this fracture exists even in the idiomatic single-route case.

L9 said "the routing system implements one operation well: given a request, find the right handler." The transformation corrects this: the routing system implements the *success case* of one operation well. The *failure case* of the same operation — method not allowed — has a different information requirement that the shared traversal strategy cannot satisfy.

---

## THE CONCEALMENT MECHANISM: **Execution-first naming fuses dispatch with error reporting, suppressing the aggregation question**

`Route.handle` runs endpoints. Its name, position in the call chain, and interface (`scope, receive, send`) uniformly signal execution. The 405 branch reads as a precondition guard — check first, run second — a pattern so common in ASGI middleware that reviewers process it as boilerplate. The question "does this guard have enough information?" is never asked, because guard clauses check conditions evaluable locally: `if self.methods and scope["method"] not in self.methods`. Both operands are on `self` and `scope`. Nothing signals that `self.methods` is one route's methods rather than all methods at this path.

Three reinforcing layers:

**1. Guard-clause form suppresses the completeness question.** Guards are expected to be local. `self.methods` looks complete because it's available and it compiles. The incompleteness — that `self.methods` is a single route's set, not the union across sibling routes — is invisible without knowing that sibling routes exist and cover the same path. Nothing at the call site signals that external data is missing.

**2. `partial is None` reads as execution-selection logic, not information-elimination logic.** The dispatch loop's purpose is finding the route to execute. "Record the first partial match, run it later" reads as efficient execution selection. A reviewer focused on "which route runs?" accepts `partial is None` as a correct "don't overwrite" guard. The question "which routes contribute to the 405 response?" requires reframing the loop as an aggregation operation — a frame the loop's structure never invites.

**3. Correct behavior in the common case postpones discovery indefinitely.** Single-route-per-path is the Starlette idiom. In this case, the first PARTIAL is the only PARTIAL, `self.methods` contains all methods at the path, and the Allow header is correct. The bug surfaces only when two routes share a path — a pattern that is both permissible and rare. Code correct for 99% of usage conceals itself from routine testing and review; it surfaces only in precisely the scenario that exposes the structural limitation.

---

## THE LEGITIMATE IMPROVEMENT THAT DEEPENS CONCEALMENT

Extract `_find_partial_match`, which canonizes the responsibility assignment as a documented architectural principle:

```python
# Router.app — dispatch loop with extraction:

partial, partial_scope = self._find_partial_match(scope)
if partial is not None:
    scope.update(partial_scope)
    await partial.handle(scope, receive, send)
    return

def _find_partial_match(
    self, scope: Scope
) -> tuple[BaseRoute | None, Scope]:
    """
    Identify the route responsible for generating a 405 response.

    Returns the first route whose path matches the request but whose method
    set does not include the request method. Method-not-allowed responses
    are a per-route concern: each Route owns its allowed methods and generates
    the Allow header from its own method set via handle().

    The standard Starlette convention — one route per path, multiple methods
    listed on a single Route — ensures the first partial match's Allow header
    is complete. This method reflects that architectural assumption: method
    aggregation is co-located with the route that registers those methods.
    Routes that share a path should consolidate their method sets into a single
    Route to preserve this invariant.
    """
    for route in self.routes:
        match, child_scope = route.matches(scope)
        if match == Match.PARTIAL:
            return route, child_scope
    return None, {}
```

This passes code review: `Router.app` is shorter, the first-wins behavior is explicitly addressed, and the recommendation ("consolidate method sets into a single Route") is actionable and correct for the idiom.

It deepens concealment because:

**"Method-not-allowed responses are a per-route concern"** — this converts an ownership accident into an ownership principle. Nothing in the original design declared that Routes own their 405 responses; `Route.handle` simply happened to contain the 405 branch. The docstring elevates this placement into an architectural decision with named ownership. Future challenges must now defeat an explicit principle, not an undocumented behavior.

**"The first partial match's Allow header is complete"** — this is conditionally true (only under the single-route-per-path convention) stated without the condition. A reviewer who encounters an incomplete Allow header will read this docstring, find a statement of completeness, and conclude that the convention was violated — making the bug the caller's fault rather than the code's structural limitation.

**"Routes that share a path should consolidate their method sets"** — this recommendation is correct as guidance but functions as liability transfer. It tells users how to work around the limitation without naming the limitation. A user who follows the recommendation achieves correct behavior. A user who violates it gets wrong behavior and finds a docstring that told them not to do this. The structural inability to correctly aggregate across multiple routes is now documented as a usage constraint rather than an architectural gap.

---

## THREE PROPERTIES VISIBLE FROM STRENGTHENING

**1. The docstring was forced to invent a completeness argument that the function falsifies.**

Writing "the first partial match's Allow header is complete" required articulating *why* first-wins produces a correct Allow header. The argument: per-route ownership plus the single-route-per-path convention. But writing this made visible that the function produces an *incomplete* Allow header for multi-route configurations — a case the function cannot detect, prevent, or warn about. The condition for correctness ("single-route-per-path") is not enforced anywhere in the registration path, not checked in this function, and not observable at the call site. The docstring claims correctness under a condition the function never verifies. Writing the docstring forced articulating an assumption the code never checks.

**2. The return type forced a binary API for a three-valued situation.**

The signature `tuple[BaseRoute | None, Scope]` collapses three distinct cases: (a) no partial matches — 404 downstream; (b) exactly one partial match — 405 with RFC-correct Allow; (c) multiple partial matches — 405 with RFC-incomplete Allow. Writing the return type made this collapse explicit for the first time. There is no way for the return type to distinguish case (b) from case (c). The API has no channel to signal its own incompleteness to callers. The original inlined code had the same collapse, but it was invisible because no return type forced counting the cases.

**3. The function wanted to be a query on a different data structure.**

When designing `_find_partial_match`, the natural primitive would be "find all routes whose path covers this path regardless of method." But the function calls `route.matches(redirect_scope)` (which performs both path matching and method comparison) and then discards the FULL/PARTIAL distinction in the same operation. This is exactly the pattern L9 identified for the redirect loop: using a request-dispatch API to answer a structural-registration question. Writing the extraction made visible that this function also needs `path_covers(path)` — path matching without method comparison — as a primitive. The original code had the same missing primitive, but the inline form hid it behind `!= Match.NONE`. The extraction forced the question: what operation is this actually performing?

---

## THE SECOND IMPROVEMENT (Contradiction)

Improvement 1 formalizes "Route generates 405 from its own methods, first PARTIAL wins." The contradicting improvement aggregates all partial matches at the Router level and generates the RFC-compliant 405 there:

```python
async def app(self, scope, receive, send):
    assert scope["type"] in ("http", "websocket", "lifespan")
    if "router" not in scope:
        scope["router"] = self
    if scope["type"] == "lifespan":
        await self.lifespan(scope, receive, send)
        return

    partial_matches: list[tuple[BaseRoute, Scope]] = []
    for route in self.routes:
        match, child_scope = route.matches(scope)
        if match == Match.FULL:
            scope.update(child_scope)
            await route.handle(scope, receive, send)
            return
        elif match == Match.PARTIAL:
            partial_matches.append((route, child_scope))

    if partial_matches:
        # RFC 7231 §6.5.5: 405 response MUST include Allow header
        # listing all methods supported by the target resource.
        # Aggregate across all routes that match this path.
        first_route, first_scope = partial_matches[0]
        allowed: set[str] = set()
        for route, _ in partial_matches:
            if hasattr(route, "methods") and route.methods:
                allowed.update(route.methods)
        scope.update(first_scope)
        headers = {"Allow": ", ".join(sorted(allowed))}
        if "app" in scope:
            raise HTTPException(status_code=405, headers=headers)
        response = PlainTextResponse(
            "Method Not Allowed", status_code=405, headers=headers
        )
        await response(scope, receive, send)
        return

    # redirect_slashes and default handling unchanged
    route_path = get_route_path(scope)
    ...
```

This also passes code review. The RFC citation is precise and accurate. The change from "first partial" to "all partials" is self-evidently correct for the stated purpose. The `hasattr` guard handles `BaseRoute` subclasses lacking `methods`. Both improvements live in the same function, affect the same code region, and can be reviewed independently without either failing.

---

## THE STRUCTURAL CONFLICT

**The conflict that exists only because both improvements are legitimate:**

Improvement 1 locates 405 generation in `Route.handle`. This is necessary for the *standalone Route* lifecycle: when a `Route` is used directly as an ASGI app via `BaseRoute.__call__`, there is no Router to aggregate methods. The Route must generate the 405 itself. Improvement 1 formalizes this as "per-route ownership" — a legitimate architectural principle for standalone use.

Improvement 2 locates 405 generation in `Router.app`. This is necessary for RFC compliance when multiple routes share a path. But it creates dead code: `Route.handle`'s 405 branch is now unreachable from `Router.app` (Router generates the response before calling any route's `handle`). `Route.handle`'s 405 branch survives only for `BaseRoute.__call__` (standalone use).

The conflict: `Route.handle` must simultaneously be:

- **Complete for standalone usage** — generates 405 from `self.methods`, no Router available
- **Bypassed for Router usage** — Router generates 405 from aggregated methods before calling `handle`

`Route.handle` has no way to distinguish these contexts. It can check `"app" in scope` (which it already does, to choose between HTTPException and PlainTextResponse), but `"app"` signals application nesting, not "a Router has already generated the correct Allow header and you should not generate another." There is no scope key that means "your 405 branch is pre-empted."

If Improvement 2 is applied without modifying `Route.handle`, standalone Route usage retains the incomplete Allow header. If `Route.handle`'s 405 branch is removed to force all 405 generation through the Router, standalone Route usage breaks entirely. The improvements cannot coexist without bifurcating `Route.handle` on a context it cannot observe — replicating the construction-time split that L8 identified (function endpoint vs class endpoint) now at the error-response level.

The conflict exists because both improvements are correct for distinct and legitimate Route lifecycles. The routing system has no concept of a Route's current lifecycle context, so any single 405 generation strategy is wrong for one of the two lifecycles.

---

## THE THIRD IMPROVEMENT (Resolution)

Resolve the conflict by injecting aggregated methods into scope, allowing `Route.handle` to use them when present and fall back to `self.methods` when absent:

```python
# In Router.app — after aggregation:
if partial_matches:
    first_route, first_scope = partial_matches[0]
    allowed: set[str] = set()
    for route, _ in partial_matches:
        if hasattr(route, "methods") and route.methods:
            allowed.update(route.methods)
    first_scope["allowed_methods"] = allowed  # ← Router injects aggregated set
    scope.update(first_scope)
    await first_route.handle(scope, receive, send)  # ← Route.handle reads it
    return

# In Route.handle:
async def handle(self, scope, receive, send):
    if self.methods and scope["method"] not in self.methods:
        # Use Router-aggregated methods when available;
        # fall back to self.methods for standalone Route usage.
        methods = scope.get("allowed_methods", self.methods)
        headers = {"Allow": ", ".join(sorted(methods))}
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

This satisfies both conflicting requirements: Router-dispatched Routes use the aggregated `allowed_methods`; standalone Routes use `self.methods`. The `BaseRoute` interface is unchanged. No new method signatures. Both lifecycles handled by one code path with a single fallback.

---

## HOW IT FAILS

**1. Scope is a request-carrying channel; routing configuration injected into it becomes an implicit contract with no spec.**

The ASGI spec defines scope as "information about the incoming connection" — `method`, `path`, `headers`, `query_string`, protocol-specific fields. `allowed_methods` is not connection information; it is routing table state for a given path. Injecting it into scope creates a key whose provenance, semantics, and lifecycle are undefined by any spec. Logging middleware, authentication middleware, rate-limiting middleware, and test clients that inspect scope will encounter `allowed_methods`. Some will ignore it. Some will forward it. Some will misinterpret it. None were written to handle it. The ASGI scope is now carrying routing configuration alongside request data with no mechanism to distinguish them.

**2. `hasattr(route, "methods")` silently collapses the `BaseRoute` abstraction.**

`BaseRoute` exists so that `Route` and `Mount` are interchangeable from the Router's perspective — the Router can hold either in `self.routes` and call `.matches()` and `.handle()` on both uniformly. Writing `hasattr(route, "methods")` breaks this: Mount instances lack `methods` and are silently excluded from aggregation. If a Mount wraps Routes with methods=["GET"] and a DELETE request arrives, the outer Router's aggregation sees nothing from the Mount — the Mount's FULL return swallows its contents' method information entirely. The `hasattr` check doesn't fail visibly; it silently produces an empty `allowed` set for Mount-contributed paths, with no log, no exception, no indicator that aggregation was incomplete. The BaseRoute abstraction promised that route types are interchangeable. Improvement 3 reveals that they are interchangeable for dispatch but not for aggregation.

**3. The aggregation does not propagate through Mount hierarchies.**

`Mount("/api", routes=[Route("/items", f1, methods=["GET"]), Route("/items", f2, methods=["POST"])])` + `DELETE /api/items`:

- Outer Router: Mount.matches returns FULL for the `/api` prefix match. No PARTIAL matches in the outer route list. The aggregation code in `Router.app` never fires.
- Outer Router dispatches to the Mount, which dispatches to its inner Router.
- Inner Router: both Routes return PARTIAL. The inner Router's aggregation (if Improvement 3 is also applied to the inner Router) collects both routes and injects `allowed_methods = {"GET", "HEAD", "POST"}`. Correct for the inner Router.

But this only works because the inner Router has both routes. Now consider: `Mount("/v1", routes=[Mount("/api", routes=[Route("/items", f1, methods=["GET"])]), Route("/api/items", f2, methods=["POST"])])`. Here f1 is nested two Mounts deep; f2 is one Mount deep. The outer Router sees only the outer Mounts as FULL. Aggregation across f1 and f2 is impossible — they live in different subtrees, and Mount.matches returns FULL before the outer Router can see their method constraints. The RFC requirement "all methods supported by the target resource" cannot be satisfied across Mount boundaries, because Mount.matches returns FULL for the path prefix regardless of what methods the contained routes support.

**4. The `allowed_methods` key has no defined scope lifetime and no cleanup.**

After `Route.handle` generates the 405 response, `allowed_methods` remains in `scope`. ASGI scopes are connection-scoped, not request-scoped — for HTTP/1.1 keep-alive connections, the scope persists across requests. Test clients frequently reuse scope dicts across requests. Middleware that retries dispatch (e.g., after authentication failures) will encounter stale `allowed_methods` from a previous dispatch attempt. The injected key has no defined lifetime, no cleanup hook, and no documentation that downstream consumers must not rely on it for subsequent requests. An ephemeral routing artifact now persists indefinitely in the connection context.

---

## WHAT THE FAILURE REVEALS ABOUT THE DESIGN SPACE THAT THE CONFLICT ALONE COULD NOT

The conflict (Improvement 1 vs. 2) revealed that 405 generation and route execution have different information requirements: execution needs one route, 405 reporting needs all routes. The conflict said: *we need more information at the point of 405 generation.*

Improvement 3's failure reveals *what kind of information* is missing and *why* the current architecture cannot supply it.

**The routing tree's information flow is structurally unidirectional — downward only.**

Successful dispatch enriches scope as it descends: Router adds `endpoint`, Mounts add `root_path` and `app_root_path`, Routes add `path_params`. Each level provides richer context to the level below. This downward flow is appropriate for the success case: one winner receives enriched context and executes.

For 405 error reporting, the required information flows in the opposite direction: "which methods are registered at this path?" is a question about the routing table's state, not about the request. The answer requires upward aggregation from leaves (individual Routes) through intermediate levels (nested Mounts) to the responder (the first Router that can see all contributing routes). The routing tree has no upward channel. Scope injection simulates upward flow by pre-computing at the top what leaves would need — but this only works when the top can see all leaves directly, which Mount boundaries prevent.

**The failure modes each correspond to a missing dimension of the resource concept.**

Four failures, four dimensions:

- *Scope pollution* — no resource-scoped context, distinct from request-scoped context
- *`hasattr` abstraction collapse* — no typed resource representation that Route and Mount both implement
- *Mount boundary opacity* — no resource identity that spans routing levels
- *Scope key lifetime ambiguity* — no resource lifecycle independent of connection lifecycle

L9 identified the missing resource primitive in the context of redirect canonicalization: the routing system cannot determine whether `/data` and `/data/` refer to the same resource because "resource" doesn't exist in the model. Improvement 3's failure reveals the same missing primitive from the 405 direction: "all methods supported by the target resource" (RFC 7231 §6.5.5) requires a concept of resource that the routing system cannot express.

**What the conflict alone could not reveal:**

The conflict showed that aggregation is required. It was possible to read the conflict and conclude: "we need a better aggregation mechanism — collect all partial matches, aggregate their methods, and inject the result." This reading suggests an algorithmic fix.

Improvement 3's failure shows that aggregation has a *type* requirement that the current system cannot satisfy. You cannot aggregate "all methods at this path" without a data structure that groups routes by resource (path). The routing system's data structure is a flat list of routes ordered by registration. A flat list supports linear-scan aggregation within one router level but not across Mount boundaries, because Mount.matches returns FULL before the outer Router can inspect the Mount's contained routes' method constraints.

A routing system that could correctly generate RFC-compliant 405 responses across arbitrary nesting would need a separate index: a map from normalized path patterns to the union of allowed methods across all routes and all Mount levels that cover that path. This index would have to be built at registration time (when the routing tree is constructed) and maintained across dynamic route additions. It is a fundamentally different data structure from the flat route list — not an improvement to traversal, but a parallel data structure for a parallel query type.

The routing tree was built for one query: given a request, find the handler. The failure of Improvement 3 reveals that this is not the only query the system is responsible for — and that the missing queries (allowed methods at a path, canonical URI for a path, URL for a named route) each require a different index over the routing table. The routing system has one data structure (list of routes) and one traversal (linear scan). It uses this single mechanism for all queries. The four failure modes of Improvement 3 are four different ways the single mechanism fails to approximate the four missing indexes.

The conflict revealed: 405 generation requires aggregation. The failure revealed: aggregation requires an index, and indexes require a data model that identifies what is being indexed. For routing, the indexing unit is the resource — the entity that has a canonical URI, supports a set of methods, and exists at a point in the URI hierarchy. The routing system indexes by route, not by resource. Routes are an implementation artifact; resources are the semantic unit that HTTP addresses. The gap between correct 405 responses and the current architecture is the gap between those two indexing units — and no traversal strategy, condition logic, or scope injection can bridge it, because it is a data model gap, not an algorithm gap.
