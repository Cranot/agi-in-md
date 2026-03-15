## Structure First: Level 11 Diagnostic

---

### THE INITIAL CLAIM

**`Router.app` contains two complete, co-resident dispatch algorithms that share the route list and the `route.matches()` call but implement different and incompatible theories of route identity. The main dispatch encodes route as `(path_regex × method_set → handler)` — it distinguishes `Match.FULL` (path + method match) from `Match.PARTIAL` (path match, method wrong). The `redirect_slashes` dispatch encodes route as `(path_regex → redirect_target)` — it collapses PARTIAL == FULL, treating "path exists for the wrong method" as equivalent to "path exists for this method." The `Match.PARTIAL` sentinel, which exists specifically to carry method-awareness from the matching phase into the handling phase, is discarded by the redirect dispatch at precisely the point where it is most load-bearing.**

Falsifiable configuration:

```python
r = Router(routes=[
    Route("/data", handler, methods=["GET"], name="data")
], redirect_slashes=True)
```

- `POST /data/` arrives.
- Main dispatch: `Route.matches` checks path regex `^/data$` against `/data/`. No match → `Match.NONE`. No FULL, no PARTIAL found.
- Redirect_slashes: toggles path to `/data`. `Route.matches(redirect_scope)` checks regex against `/data` → matches → method check: `POST` not in `{"GET", "HEAD"}` → returns `Match.PARTIAL`. Check: `match != Match.NONE` → True → redirect fires.
- Client follows redirect: `POST /data` → `Match.PARTIAL` → `partial.handle()` → 405.

Result: `POST /data/` → 301/307 → `POST /data` → 405. One unnecessary round trip. The router knew at redirect time that `Match.PARTIAL` meant "path exists, wrong method" — this information was available in the `Match` value — but the redirect check discarded it by using `!= NONE` instead of `== FULL`.

---

### THE THREE-EXPERT DIALECTIC

**Expert 1 — Defender:** The falsifiable test is exact. `Router.app` lines 1–15 implement the main dispatch (FULL → dispatch, PARTIAL → save, NONE → skip). Lines 16–26 implement the redirect check (NONE → skip, any-other → redirect). These are structurally different: the main dispatch uses all three `Match` values semantically; the redirect check uses them as binary (NONE vs any). `Match.PARTIAL` was introduced precisely to encode "path matched, method wrong" — this is the information that distinguishes "redirect will succeed" from "redirect will hit 405." The redirect check ignores this distinction. The `Match` enum has three values. The redirect check throws one of them away.

**Expert 2 — Attacker:** The round trip is a non-issue for the intended use case. `redirect_slashes=True` is designed for browser clients normalizing trailing-slash URLs — browsers send GET requests, and GET requests to path-matching routes always return `Match.FULL` (never PARTIAL). For browser traffic, PARTIAL never occurs in the redirect check. The claim requires a programmatic client sending a wrong-method request to a slash-mismatched path — this is a pathological combination that `redirect_slashes=False` resolves. The feature is correct for its use case. The "bug" is in the caller's use of the feature outside its intended context.

**Expert 3 — Probing:** Both of you are arguing about whether the wrong behavior matters. Neither of you has examined why the redirect check cannot be method-aware even if we wanted it to be. Consider: to correctly redirect only when the toggled path would succeed, the redirect check would need to answer "is `POST /data` a valid request?" This is equivalent to running the full dispatch algorithm on the toggled path with the original method. But `Router.app` is in the middle of dispatch — it cannot issue a fresh dispatch to itself with a different path without recursing into itself. The redirect check is dispatch-internal. A middleware implementation of redirect_slashes could be method-aware (intercept the 404 response, re-issue the toggled request, redirect or not based on the result) but cannot see the route structure. A dispatch-internal implementation can see the route structure but cannot re-issue a request. Is the real question not "why does the redirect check use `!= NONE`?" but "why is redirect_slashes embedded in dispatch rather than implemented as middleware?"

---

### THE TRANSFORMATION

| Level | Claim |
|---|---|
| **L11 initial** | Redirect_slashes check uses `match != Match.NONE`, discarding `Match.PARTIAL`, causing unnecessary round trips for wrong-method slash-mismatched requests |
| **L11 transformed** | The redirect_slashes dispatch is embedded in `Router.app` rather than implemented as middleware because transparent path toggling requires access to the route matching API (visible at dispatch level, not at response level). Being dispatch-internal, the redirect check cannot re-run the full dispatch algorithm on the toggled path — it can only inspect `route.matches()` results. The method-unaware semantics (`!= NONE`) are not a mistake in the check; they are the maximum information available to a dispatch-internal redirect decision. The round trip is not a performance bug — it is the deferred cost of a dispatch computation that the embedded redirect cannot perform in-process. |

**The gap between initial and transformed:** The initial claim locates the fault in the choice of comparison (`!= NONE` vs `== FULL`). The transformed claim locates it in the architectural position of `redirect_slashes` — embedded in dispatch where re-issuing a request is impossible. The method-unaware check is the best available answer at that position. The actual problem is that the decision "should I redirect?" requires the same computation as the dispatch itself, and dispatch-internal code cannot pay that cost without recursing.

---

### THE CONCEALMENT MECHANISM: ORACLE SYMMETRY

The main dispatch and the redirect dispatch both call `route.matches(scope)` — the same method, the same calling convention, returning the same `(Match, child_scope)` tuple. This creates the appearance of a unified routing oracle: both passes consult the same authority, both receive the same structured response.

The concealment: **the two passes read different subsets of the oracle's answer.** The main dispatch reads all three values (NONE/PARTIAL/FULL) and uses their semantic distinction — PARTIAL carries the information "path valid, method wrong." The redirect dispatch reads only two values (NONE vs any) and explicitly erases the semantic distinction — PARTIAL is treated as FULL. `Match.PARTIAL` exists to prevent exactly this erasure, but the redirect dispatch performs it anyway. The shared `route.matches()` call makes the two algorithms look like they consult the same evidence, while concealing that they draw different conclusions from it.

**Three things this concealment hides:**

**1. The redirect_slashes dispatch is the only place in the codebase where `Match.PARTIAL`'s method-awareness is structurally discarded rather than propagated.** Everywhere else that calls `route.matches()`: `Router.app` main loop saves PARTIAL for handle(); `BaseRoute.__call__` passes any non-NONE match to handle() (where method is re-checked); inner Routers inside Mounts repeat the same main-loop logic. `Match.PARTIAL` always reaches `route.handle()`, where it produces 405. The redirect check is the one exception — it terminates the PARTIAL result with a redirect instead of propagating it to handle(). The concealment makes this unique behavior look like routine routing.

**2. `Match.FULL` has different semantics for `Route` and `Mount`.** For `Route.matches`, `Match.FULL` means "path regex matched AND method is in self.methods" — a complete, method-aware match. For `Mount.matches`, `Match.FULL` means "path prefix matched" — there is no method check. `Mount` has no `methods` attribute and never returns `Match.PARTIAL`. When the redirect check reads `match != Match.NONE`, it treats Mount's FULL (prefix match, method unknown) identically to Route's FULL (complete match, method verified). The shared `route.matches()` interface makes this semantic difference invisible — both return the same enum value for structurally different reasons.

**3. The redirect check terminates on the first matching route regardless of whether a better match exists later.** The main dispatch loop continues past PARTIAL matches, looking for a FULL match further in the route list. The redirect check's `if match != Match.NONE: redirect_url = ...; return` terminates immediately on any match — it does not check whether a FULL match (redirect will succeed) appears after a PARTIAL match (redirect will fail). For a route list `[Route("/data", methods=["POST"]), Route("/data", methods=["GET"])]`, a GET request to `/data/` would hit the POST route first (PARTIAL), redirect, then fail at the GET route check... wait, there's no slash difference here. But for `[Mount("/data", ...), Route("/data/item", handler, methods=["GET"])]`, a POST to `/data/item/` might hit the Mount first (FULL prefix match, immediate redirect), when the Route later in the list would have produced PARTIAL (no redirect). The redirect check's early-exit logic differs from the main dispatch's early-exit logic, creating divergent behavior.

---

### THE LEGITIMATE IMPROVEMENT

```python
async def app(self, scope, receive, send):
    assert scope["type"] in ("http", "websocket", "lifespan")
    if "router" not in scope:
        scope["router"] = self
    if scope["type"] == "lifespan":
        await self.lifespan(scope, receive, send)
        return

    partial = None
    for route in self.routes:
        match, child_scope = route.matches(scope)
        if match == Match.FULL:
            scope.update(child_scope)
            await route.handle(scope, receive, send)
            return
        elif match == Match.PARTIAL and partial is None:
            partial = route
            partial_scope = child_scope

    if partial is not None:
        scope.update(partial_scope)
        await partial.handle(scope, receive, send)
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
            # Only redirect when the toggled path produces a complete match.
            # Match.PARTIAL means: path exists, but method is wrong.
            # Redirecting on PARTIAL sends the client to a URL that will 405 —
            # an unnecessary round trip. Match.FULL means the redirect will succeed.
            if match == Match.FULL:
                redirect_url = URL(scope=redirect_scope)
                response = RedirectResponse(url=str(redirect_url))
                await response(scope, receive, send)
                return

    await self.default(scope, receive, send)
```

This passes code review because: the change is one line (`!= Match.NONE` → `== Match.FULL`); the added comment correctly explains the three-way `Match` semantics and why PARTIAL should not trigger redirect; the change is semantically in the direction of "more correct" (redirect only when the redirect will succeed); it eliminates the documented round-trip waste without adding complexity.

---

### THREE PROPERTIES VISIBLE BECAUSE OF THE IMPROVEMENT

**1. For wrong-method slash-mismatched requests, the improvement produces 404 instead of 405 — revealing that the correct response requires method-aware routing of the toggled path, not just path-aware matching.**

After the improvement: `POST /data/` → redirect check finds PARTIAL on `/data` → `!= FULL` → no redirect → `self.default` → 404. But the correct response is 405: the path `/data/` has a slash-mismatched form of a valid resource `/data`, and the method is wrong. The improvement correctly eliminates the unnecessary redirect but produces the wrong terminal response. The correct terminal response (405) requires knowing BOTH that the toggled path is a valid resource AND that the method is wrong for it — which requires running the full method-aware dispatch on the toggled path. The improvement surfaces that there is no correct behavior achievable from a dispatch-internal redirect check without re-running dispatch.

**2. `Mount.matches` always returns `Match.FULL` for prefix-matching paths, regardless of method — after the improvement, Mount redirects fire even when the inner routing will fail.**

For `Mount("/api", routes=[Route("/data", handler, methods=["GET"])])` with `POST /api/data/`:
- Main dispatch: Mount matches `/api/data/`? Mount regex `^/api/(?P<path>.*)$` matches `/api/data/` with path=`data/`. `Match.FULL` → immediate dispatch to inner Router. The redirect check never runs in this case because the Mount greedily consumes the request.

For `POST /api/` when Mount expects inner path `/data`:
- Main dispatch: Mount matches `/api/`? regex matches with path="". FULL → dispatch to inner Router → inner Router finds no match → inner Router redirect_slashes fires (if enabled) — this is a separate, independent redirect mechanism inside the Mount's inner Router.

The improvement makes `Match.FULL` semantics load-bearing: when `== Match.FULL` is required, Mount's FULL (method-blind prefix match) and Route's FULL (method-verified complete match) produce identical behavior in the redirect check, but with different reliability guarantees. A Mount FULL in the redirect check means "redirect to a path under this Mount" — whether the inner routing succeeds is unknown and unknowable without entering the Mount.

**3. Full correctness of the redirect decision requires running the entire dispatch algorithm recursively — which is isomorphic to dispatching the request and reading the response code.**

The improvement prevents redirecting on PARTIAL (correct for Routes). But for Mounts, FULL doesn't guarantee the redirect will succeed. To know whether the redirect will succeed for a mounted path, the check must enter the Mount's inner Router and run its dispatch — which is itself a routing algorithm. Full correctness requires a `_would_redirect_succeed(redirect_scope)` function that recursively runs dispatch on the toggled path without actually sending a response. This function IS the dispatch algorithm, renamed. The improvement reveals: the only correct redirect decision algorithm has the same complexity as the dispatch algorithm itself.

---

### DIAGNOSTIC APPLIED TO THE IMPROVEMENT

**What does the improvement conceal?**

`if match == Match.FULL: redirect` reads as "redirect only when the match is complete." For Route objects, this is correct: FULL means method-verified. For Mount objects, this is wrong: Mount's FULL means "prefix matched," with no method verification. The improvement creates the appearance of a method-aware redirect decision while concealing that Mount's FULL carries no method information. Code reviewers reading `match == Match.FULL` will assume the redirect is method-safe — it is not for any request that the redirect sends into a Mount.

**What property of the original problem is visible only because the improvement recreates it?**

The original used `match != Match.NONE` — this erases the PARTIAL/FULL distinction for all route types. The improvement uses `match == Match.FULL` — this enforces the distinction for Route but fails to enforce it for Mount (where the distinction doesn't exist). This recreates, in the redirect decision, the same property that L10 identified in url_path_for method annotation: **the routing layer has complete method information for function-endpoint Routes (`self.methods` is non-None, Match.PARTIAL is used) and no method information for Mounts (no `self.methods`, Match.FULL is always returned for prefix matches).** The improvement makes this asymmetry load-bearing in the redirect check, where L10 made it load-bearing in `RouteURL.methods`. The gap is the same structural property, appearing in a third location.

---

### THE SECOND IMPROVEMENT

Addresses the Mount-opacity problem by probing the inner routing recursively:

```python
def _redirect_match(self, redirect_scope: dict) -> Match:
    """
    Determine the strongest match for redirect_scope through the full
    route tree, including inside Mounts.

    Returns:
      Match.FULL    — the redirect will succeed (complete path+method match)
      Match.PARTIAL — the redirect path exists but method is wrong
      Match.NONE    — the redirect path does not exist
    
    This is a pure read operation (no response sent, no scope mutation).
    """
    best = Match.NONE
    for route in self.routes:
        match, child_scope = route.matches(redirect_scope)
        if match == Match.FULL:
            if isinstance(route, Mount):
                # Mount FULL means prefix matched. Probe inside the Mount's
                # inner Router with the prefix-adjusted scope.
                inner_scope = dict(redirect_scope)
                inner_scope.update(child_scope)
                inner_app = getattr(route, '_base_app', None)
                if isinstance(inner_app, Router):
                    inner_match = inner_app._redirect_match(inner_scope)
                    if inner_match == Match.FULL:
                        return Match.FULL
                    elif inner_match == Match.PARTIAL:
                        best = Match.PARTIAL
                    # Match.NONE: this Mount path is a dead end, continue scanning
                else:
                    # Opaque inner app: cannot probe, conservatively treat as FULL
                    return Match.FULL
            else:
                # Route.FULL: complete match (path + method verified)
                return Match.FULL
        elif match == Match.PARTIAL and best == Match.NONE:
            best = Match.PARTIAL
    return best

# In Router.app, redirect_slashes section:
for route in self.routes:
    match, child_scope = route.matches(redirect_scope)
    if match != Match.NONE:
        # Probe the full route tree to determine redirect validity.
        redirect_match = self._redirect_match(redirect_scope)
        if redirect_match == Match.FULL:
            redirect_url = URL(scope=redirect_scope)
            response = RedirectResponse(url=str(redirect_url))
            await response(scope, receive, send)
            return
        elif redirect_match == Match.PARTIAL:
            # Toggled path exists but method is wrong — 405, no redirect needed.
            # Fall through to self.default (which will 404; correct 405 requires
            # per-resource Allow header, not available here).
            break
        # Match.NONE: this route was a false positive, continue.
```

---

### DIAGNOSTIC APPLIED TO THE SECOND IMPROVEMENT

**What does the improvement conceal?**

`_redirect_match` returns `Match.FULL` for opaque inner apps (non-Router ASGI apps mounted without an inner Router). The comment says "conservatively treat as FULL" — but this is optimistic, not conservative: it assumes the opaque app will succeed, generating a redirect that may 404 or 405 inside the opaque app. The concealment: "conservatively" in the comment means "don't fail to redirect" (conservative about not blocking redirects), which is actually the liberal interpretation. A genuinely conservative choice would be "don't redirect for opaque apps" — returning NONE and letting the client get a 404 directly instead of a redirect to a potentially-failing URL.

More deeply: `_redirect_match` accesses `route._base_app` — a private attribute of Mount — to bypass Mount middleware and probe the inner Router directly. This is the same bypass that `Mount.routes` uses (`getattr(self._base_app, "routes", [])`) for `url_path_for` traversal. The second improvement recreates the Mount-middleware bypass pattern in a third context: url_path_for uses it for URL generation, L10's method aggregation probe used it for method collection, and now `_redirect_match` uses it for redirect validity checking.

**What property of the original problem is visible only because the improvement recreates it?**

`_redirect_match` must access `route._base_app` to enter Mounts for probing. This attribute accesses the pre-middleware inner app, not `route.app` (the middleware-wrapped version). Any middleware wrapping the Mount's inner app is bypassed by the probe. This means: if Mount middleware modifies routing behavior (e.g., path rewriting, auth-based routing), `_redirect_match` sees a different routing structure than forward dispatch does. The improvement makes visible that **Mount middleware is transparent to all routing meta-operations** — url_path_for, Allow header aggregation, and redirect probing all bypass it by accessing `_base_app` directly. Forward dispatch is the only operation that goes through Mount middleware. The structural invariant from L8–L10 (method dispatch at two levels) is accompanied by a parallel invariant: **Mount middleware is opaque to requests but transparent to routing introspection.** Every meta-operation recreates the `_base_app` bypass.

---

### THE STRUCTURAL INVARIANT

The property that persists through every improvement — from L8's sentinel, through L9's closed boundary, through L10's method aggregation, through L11's redirect dispatch:

**Correctly answering any routing meta-query (Is this method allowed at this URL? What URL delivers to this handler? Will redirecting to this URL succeed?) requires the same computation as the dispatch itself. No data structure or algorithm can answer these queries at lower cost than running the full dispatch algorithm, because the dispatch algorithm IS the canonical answer. Routing meta-operations that try to answer these queries at lower cost — consulting `self.methods` instead of running dispatch, using `match != Match.NONE` instead of probing through Mounts, using `RouteURL.methods` instead of per-resource aggregation — are correct only for a restricted input class (function-endpoint routes, GET-only traffic, single-route resources) and incorrect for the complement. The restriction is never stated in the interface. Every improvement that makes a routing meta-operation more correct either (a) re-runs the full dispatch algorithm under a different name (`_redirect_match`), (b) accepts wrong answers for class endpoints and opaque Mounts, or (c) defers to handle() and pays in round trips. The invariant is not in the code; it is in the problem: a routing query is a function of the complete route table evaluated in priority order, and any summary of that function loses information.**

---

### INVERTING THE INVARIANT

The invariant: routing meta-queries require full dispatch computation; summaries lose information.

The inversion: design a system where routing meta-queries are answered in O(1) without full dispatch, by making the summary lossless.

**The inverted design:**

Route identity becomes `(path_regex, method)` — a pair, not a triple with a loose method field. Method is part of route registration:

```python
class MethodRoute:
    """A route keyed by (path, method) — not (path, method_set, handler)."""
    def __init__(self, path: str, method: str, endpoint, name: str | None = None):
        self.path = path
        self.method = method.upper()
        self.endpoint = endpoint
        self.name = name
        self.path_regex, self.path_format, self.param_convertors = compile_path(path)

    def matches(self, scope) -> tuple[Match, dict]:
        """Returns FULL or NONE — Match.PARTIAL is eliminated."""
        if scope["type"] == "http":
            if scope["method"] != self.method:
                return Match.NONE, {}
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)
            if match:
                matched_params = {k: self.param_convertors[k].convert(v)
                                  for k, v in match.groupdict().items()}
                path_params = {**scope.get("path_params", {}), **matched_params}
                return Match.FULL, {"endpoint": self.endpoint, "path_params": path_params}
        return Match.NONE, {}


class MethodRouter:
    def __init__(self, routes=None):
        self.routes = list(routes or [])
        # Pre-computed resource index: path_regex → frozenset(methods)
        self._method_index: dict[str, frozenset[str]] = self._build_index()

    def _build_index(self) -> dict[str, frozenset[str]]:
        index: dict[str, set[str]] = {}
        for route in self.routes:
            key = route.path_regex.pattern
            index.setdefault(key, set()).add(route.method)
        return {k: frozenset(v) for k, v in index.items()}

    def allowed_methods(self, path: str) -> frozenset[str]:
        """O(routes) path scan → O(1) lookup via index."""
        for route in self.routes:
            if route.path_regex.match(path):
                return self._method_index[route.path_regex.pattern]
        return frozenset()

    def url_path_for(self, name: str, method: str, /, **path_params) -> URLPath:
        """Method is a required parameter — the dropped dimension is restored."""
        method = method.upper()
        for route in self.routes:
            if route.name == name and route.method == method:
                seen = set(path_params)
                expected = set(route.param_convertors)
                if seen == expected:
                    path, remaining = replace_params(route.path_format, route.param_convertors, dict(path_params))
                    assert not remaining
                    return URLPath(path=path, protocol="http")
        raise NoMatchFound(name, path_params)
```

In this design:
- `Match.PARTIAL` is eliminated — method is part of route identity, so every path match is also a method match or not a match at all
- `url_path_for` takes `method` as a required parameter — the missing dimension is restored
- Allow header generation is O(1): `self._method_index[route.path_regex.pattern]`
- Redirect_slashes check is trivially correct: `match == Match.FULL` means path and method both verified
- The impossible property (co-evaluating method and path at matching time) becomes trivially satisfiable

**The new impossibility:**

`url_path_for("data", method="POST")` returns `/data`. `url_path_for("data", method="GET")` raises `NoMatchFound` — there's no GET handler named "data." The name "data" is ambiguous: it refers to the POST handler. The URL `/data` is not a property of a named resource — it is a property of a named `(resource, method)` pair. Two handlers at the same URL with different methods must have different names, or share a name but be disambiguated by method in every call.

More fundamentally: `url_path_for` now requires method as input. Template engines, HTML `href` attributes, OpenAPI spec generators, and any code that generates links without knowing the intended method in advance cannot call `url_path_for` correctly. HTML links are method-free by default (they produce GET requests). A method-required `url_path_for` cannot generate the href for an anchor tag that the developer intends to be clicked.

The new impossibility: **co-evaluating method and path in route identity makes it impossible to generate a URL without knowing the intended method. Since URLs in HTML, emails, and external systems are method-free (they represent resources, not operations), any client of the router that needs to produce method-free URLs faces an impossible input requirement. The resource abstraction — "here is the URL for the data endpoint" — cannot be expressed without specifying which method you intend.**

---

### THE CONSERVATION LAW

**Original impossibility (L8–L11):** In the architecture where route identity is `(path, method_set, handler)` — with method_set evaluated at handle-time and exposed only through `Match.PARTIAL` — routing meta-operations (Allow header, url_path_for, redirect validity) cannot be answered correctly at match time without re-running the full dispatch algorithm. Every shortcut (consulting `self.methods`, checking `match != Match.NONE`, reading `Match.PARTIAL`) produces wrong answers for some input class.

**Inverted impossibility:** In the architecture where route identity is `(path, method, handler)` — with method co-evaluated at match time — routing meta-operations that produce method-free URLs (href generation, resource linking, external URL publishing) cannot be answered without knowing the caller's intended method. Method-free URL generation is impossible because the URL's canonical form depends on which method the caller intends.

**The conservation law:** In a routing system that supports multi-method resources, the information needed to correctly generate or validate a URL cannot be localized without the system's clients committing to a method. Specifically:

- If the routing system commits to method at registration (inverted design): URL generation requires method as input. Callers that don't know the method cannot generate correct URLs.
- If the routing system defers method to handle-time (original design): URL validation requires the full dispatch algorithm. Callers that don't run dispatch cannot validate generated URLs.

**The information that is conserved:** the method decision cannot be eliminated from the routing pipeline. It can be pushed to registration time (making callers commit early), to dispatch time (making validation expensive), or to round-trip time (making validation deferred). No design eliminates the commitment; it only moves where and when it is paid.

---

**What a senior engineer would not already know:**

The senior engineer knows the trade-off between resource-oriented and method-oriented routing. What they likely do not know: **`Match.PARTIAL` is the unique mechanism in the codebase that could make routing meta-operations method-aware at match time — and it is discarded by the redirect dispatch at the one location where method-awareness would eliminate a network round trip.** The existence of `Match.PARTIAL` creates a false sense that method information is available everywhere in the routing layer. It is not: `Match.PARTIAL` is available to `Router.app`'s main dispatch loop (which reads all three values), invisible to `BaseRoute.__call__` (which collapses PARTIAL == FULL), and discarded by the redirect check (which uses `!= NONE`). The three sites that call `route.matches()` use the result differently — same oracle, different queries. The redirect check's discarding of PARTIAL is not a mistake: it is the maximum information that a dispatch-internal redirect can use without re-running dispatch. What the senior engineer misses is that the round trip in `redirect_slashes` is not a performance oversight but the AGGREGATION COST of the routing decision, deferred to the network. The routing system cannot determine whether `POST /data/` should redirect to `POST /data` without running dispatch on `POST /data` — and it defers that cost to the client's second request.

**What the law predicts about a third design:**

A third design maintains a pre-computed `{path_regex_pattern → frozenset(methods)}` index at `Router` construction time. This design answers routing meta-queries in O(1) without re-running dispatch, and makes `redirect_slashes` fully method-aware:

```python
# At Router.__init__: build the resource index
self._resource_index = {}
for route in self.routes:
    if hasattr(route, 'path_regex') and hasattr(route, 'methods'):
        key = route.path_regex.pattern
        self._resource_index.setdefault(key, set())
        if route.methods is not None:
            self._resource_index[key].update(route.methods)

# In redirect check:
for route in self.routes:
    match, child_scope = route.matches(redirect_scope)
    if match != Match.NONE:
        methods_at_path = self._resource_index.get(route.path_regex.pattern, None)
        if methods_at_path and scope["method"] in methods_at_path:
            # Method is valid at the toggled path — redirect will succeed
            redirect_url = URL(scope=redirect_scope)
            response = RedirectResponse(url=str(redirect_url))
            await response(scope, receive, send)
            return
        elif methods_at_path and scope["method"] not in methods_at_path:
            # Toggled path exists but method is wrong — 405 directly, no redirect
            # Allow header from index: correct for function endpoints
            headers = {"Allow": ", ".join(sorted(methods_at_path))}
            response = PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
            await response(scope, receive, send)
            return
        # methods_at_path is None: class endpoint, method unknown → redirect optimistically
```

The conservation law predicts this third design succeeds for Starlette's specific path convertor system but fails in the general case. The index keys routes by `path_regex.pattern`. Two routes with the same pattern (e.g., `Route("/data", get_handler, methods=["GET"])` and `Route("/data", post_handler, methods=["POST"])`) share a key — their methods aggregate correctly. But two routes with different patterns that match overlapping paths (e.g., `Route("/data")` and `Route("/{name}")`) have different keys — the index treats them as different resources even though they overlap. The redirect check for `GET /data/` toggled to `GET /data` would consult the `Route("/data")` key — correct. But for `GET /other/` toggled to `GET /other`, the redirect check consults the `Route("/{name}")` key — which reports whatever methods are registered for `/{name}`. If there are none (class endpoint), the index has `None` → redirect optimistically → L10's class endpoint opacity problem reappears in the index.

The law predicts further: the index cannot distinguish which routes shadow which. For `[Route("/data", handler_a, methods=["GET"]), Route("/{name}", handler_b, methods=["POST"])]`, the index reports `GET` for `/data` and `POST` for `/{name}`. But `GET /data` dispatches to `handler_a` (first route, literal match), while `GET /{name}` (with name="data") also dispatches to `handler_a` (because it's first in registration order). The index's answer for `/{name}` is wrong for the specific case where name="data" — the correct answer includes GET (because `/data` shadows `/{name}` for GET). The index cannot capture priority ordering without solving the regex specificity problem — and regex specificity for arbitrary patterns is undecidable. The conservation law's prediction: the third design works for non-overlapping route tables (Starlette's common case) and produces wrong Allow headers and redirect decisions for overlapping route tables (the same shadowing configuration that L10 identified as causing round-trip invariant failures in `url_path_for`). The third design does not solve the problem; it makes the same class of errors as `url_path_for` — wrong answers when routes overlap — but now in the redirect path and Allow header generation instead of in URL generation.
