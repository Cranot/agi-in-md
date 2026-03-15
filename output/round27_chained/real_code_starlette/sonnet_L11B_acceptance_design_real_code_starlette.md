# Structure First: Level 11 Counter-Construction

---

## THE INITIAL CLAIM

**`url_path_for` and the dispatch loop are structurally decoupled systems using the same first-match-wins heuristic on different keys — dispatch on path regex, URL generation on name string — so there exist valid routing configurations where `url_path_for(name)` returns a URL that dispatches to a handler other than the one registered under `name`. The code provides no mechanism to detect, prevent, or warn about this discrepancy at registration time or link-generation time.**

Falsifiable:

```python
f_real = lambda req: PlainTextResponse("real")
f_shadow = lambda req: PlainTextResponse("shadow")

router = Router([
    Mount("/api", app=Router([Route("/items", f_real, name="items")])),
    Route("/api/items", f_shadow, name="api_items"),
])
```

`router.url_path_for("api_items")` → `"/api/items"` (Route.url_path_for: name `"api_items"` matches `self.name`, no path params, returns URLPath). Dispatching `GET /api/items` → Mount matches first (FULL, regex `^/api/(?P<path>.+)$` matches with path=`"items"`) → inner router → `f_real` runs. Handler `f_shadow` is permanently unreachable. `url_path_for` succeeded — returned a well-formed URL, no exception — for a route no request will ever reach. The failure is deterministic and silent.

This is structurally distinct from L10-B. L10-B: within the dispatch traversal, success-case (run the handler) and failure-case (report 405) need different information. This claim: the dispatch traversal (forward, path-keyed) and the URL generation traversal (reverse, name-keyed) use incompatible priority orderings on the same route list, making their outputs irreconcilable whenever route overlap exists.

L10-B identified `url_path_for` as a "missing index" and stopped there. This analysis investigates why the index is missing and what happens when you try to add it.

---

## THE THREE-EXPERT DIALECTIC

**Expert 1 — Defender:** The discrepancy is real, structural, and consequential. Applications use `url_path_for` to construct links, generate redirects, and write test assertions. If `url_path_for("api_items")` returns `"/api/items"` and `GET /api/items` reaches `f_real` rather than `f_shadow`, every link generated for `"api_items"` points to the wrong handler. Tests that construct requests via `url_path_for` will test `f_real` while believing they're testing `f_shadow`. This is not a marginal edge case — it surfaces naturally during application evolution, when a developer adds a Mount to organize an API without removing individual routes the Mount now shadows. The shadow is invisible: `url_path_for` returns a URL, the URL is valid, the application appears to work. Only `f_shadow` never runs.

**Expert 2 — Attacker:** Route shadowing is user error. Registering `Route("/api/items")` AFTER `Mount("/api")` creates an obviously unreachable route — dispatch is first-match-wins, and the Mount captures all `/api/...` traffic. The routing system is not responsible for the consequences of user mistakes. Furthermore, `url_path_for("api_items")` returns `"/api/items"` — which IS the path for the route registered as `"api_items"`. The function's contract is satisfied: it returns the path that matches the route's pattern. Whether that route is reachable in dispatch is a separate question. Fix the registration API to detect shadows at registration time, not `url_path_for`'s return value.

**Expert 3 — Probing:** You're both assuming there's a ground truth — a "correct" URL for `"api_items"`. But what does "correct" mean in a system where dispatch is order-dependent? If you register `Route("/api/items")` before `Mount("/api")`, the Route wins dispatch. `url_path_for("api_items")` returns `"/api/items"`, `GET /api/items` reaches `f_shadow` — round trip holds. Reorder registration, the Mount wins, the round trip breaks. Same routes, same URL, different handler. The question isn't "does `url_path_for` return the right URL?" — it's "what does 'right' mean when dispatch correctness is itself order-dependent?" The round-trip invariant isn't just unenforced — it's **order-contingent**. Any system that uses first-match-wins for dispatch and first-match-wins for URL generation will satisfy the round-trip invariant when they agree on priority, and violate it when they don't. That agreement is an emergent property of registration order, not an enforced contract.

---

## THE TRANSFORMATION

| | Claim |
|---|---|
| **Original** | `url_path_for(name)` returns a URL that may dispatch to a different handler than the one registered under `name`, because route shadowing is undetected |
| **Transformed** | The routing system commits two incompatible traversals to the same data structure and the same strategy (first-match-wins) with different keys (path for dispatch, name for URL generation). The round-trip invariant `dispatch(url_path_for(name)) == handler(name)` holds when and only when the first-match-by-name route and the first-match-by-path route are the same object. This is an *order-contingent coincidence*, not a structural guarantee. No change to traversal strategy, data structure, or registration validation can make it a guarantee while preserving route overlap — which the routing system explicitly supports and which is the basis of Mount-based composition. |

Expert 2 narrowed to user error; Expert 3 revealed that "user error" is undefined in a system without overlap detection. More precisely: Expert 3 showed that the round-trip invariant is not merely unenforced — it is *order-contingent*. The same routing table can satisfy or violate the invariant depending on registration sequence. A system where correctness depends on the ordering of correct-looking operations has no failure mode for "user error" — because the operation (route registration) always succeeds, and the invariant violation appears only at link-generation time or request time, not at construction time.

---

## THE CONCEALMENT MECHANISM: **Functional naming converts a search into a lookup, suppressing the question of which match is correct**

`url_path_for` names a search — iterate routes in registration order, return the first whose name matches — as if it named a function: the path FOR a named route. The word "for" carries mathematical connotation: `f(x)` is THE value at `x`, unique and well-defined. A lookup returns a canonical answer. A search returns a first answer. These are different operations with the same interface.

Three reinforcing layers:

**1. `NoMatchFound` names failure as absence, not ambiguity.** The exception signals that no route has the requested name. By naming failure "not found," it implies that *finding* a route means finding the *correct* route. Users who encounter `NoMatchFound` learn to handle "route doesn't exist." They do not learn to ask "is the route I found the right one?" The exception's name suppresses the second question by making the first question feel complete.

**2. The `**path_params` interface mirrors mathematical function notation.** `url_path_for("item", id=42)` reads as application of a function to arguments — get the URL for item 42. This is how every URL-generation API in every major framework works, and those frameworks (Django's `reverse()`, Rails' `path_helpers`) maintain the round-trip invariant by construction (no route shadowing allowed). Starlette inherits the convention without the construction. A reviewer familiar with other frameworks reads `url_path_for` and inherits its guarantee from an architectural assumption the code doesn't share.

**3. Correct behavior in the non-overlap case postpones discovery.** When every path is handled by exactly one route, first-match-by-name and first-match-by-path always agree — because there's only one match. The round-trip invariant holds. Shadowing only occurs when a Mount captures routes that also exist as flat routes — a pattern that arises during refactoring, not initial development. Code that works correctly until a refactoring makes a route unreachable surfaces its failure at the worst time: after trust is established, when causality is hardest to trace.

---

## THE LEGITIMATE IMPROVEMENT THAT DEEPENS CONCEALMENT

Extract a name registry with uniqueness validation, converting the linear-scan search into a declared-canonical lookup:

```python
class Router:
    def __init__(self, routes=None, redirect_slashes=True, default=None,
                 lifespan=None, *, middleware=None):
        self.routes = [] if routes is None else list(routes)
        self._name_registry: dict[str, BaseRoute] = {}
        self._build_name_registry(self.routes, name_prefix="")
        # ... rest of __init__

    def _build_name_registry(self, routes: list[BaseRoute], name_prefix: str) -> None:
        """
        Build a flat index mapping fully-qualified route names to their route
        objects. Raises ValueError on duplicate names.

        The routing contract for url_path_for(name): there is exactly one
        route whose name matches, and its path pattern instantiation is the
        canonical URL for that named resource. Duplicate names violate this
        contract — two routes competing for the same name means url_path_for
        has no canonical answer. This validation enforces the contract at
        registration time rather than silently returning whichever route
        was registered first.

        Fully-qualified names follow the Mount hierarchy: a Route named
        "items" inside a Mount named "api" is indexed as "api:items".
        Anonymous Mounts (name=None) are transparent to the name hierarchy —
        their children are indexed directly under the current prefix.
        """
        for route in routes:
            full_name = (
                f"{name_prefix}:{route.name}"
                if name_prefix and getattr(route, "name", None)
                else getattr(route, "name", None) or ""
            )
            if full_name:
                if full_name in self._name_registry:
                    raise ValueError(
                        f"Duplicate route name '{full_name}'. "
                        f"url_path_for('{full_name}') requires a unique, canonical "
                        f"target. Rename one route or consolidate them."
                    )
                self._name_registry[full_name] = route
            child_prefix = full_name if full_name else name_prefix
            if hasattr(route, "routes") and route.routes:
                self._build_name_registry(route.routes, child_prefix)

    def url_path_for(self, name: str, /, **path_params) -> URLPath:
        """
        Return the canonical URL for the named route with the given parameters.

        The name registry (built at construction time) guarantees that each
        name maps to exactly one route, making url_path_for a true function:
        deterministic, with a unique, canonical result for each (name, params)
        pair. This eliminates the first-match ambiguity of linear-scan lookup.
        """
        if name in self._name_registry:
            route = self._name_registry[name]
            local_name = name.split(":")[-1]
            return route.url_path_for(local_name, **path_params)
        raise NoMatchFound(name, path_params)
```

This passes code review: duplicate name detection is a clearly correct improvement (duplicate names are an obvious mistake), O(1) lookup replaces O(n) scan, and the docstring documents an architectural principle ("canonical URL for that named resource") that is accurate for the declared use case.

It deepens concealment because:

**"url_path_for is a true function: deterministic, with a unique, canonical result"** — this converts an accidental first-match behavior into a declared canonical lookup. The docstring now explicitly asserts the round-trip invariant as a design principle while implementing only half of it. Name uniqueness is enforced; dispatch reachability is not. A route can have a unique name, pass validation, and still be permanently unreachable because a Mount captures its path first. The docstring calls this a "canonical URL for that named resource" — but canonical in which sense? It is canonical in the URL generation system. It is emphatically not canonical in the dispatch system. The docstring's authority suppresses this distinction.

**`route.url_path_for(local_name, **path_params)` calls the leaf route's method with ALL params** — but the leaf route only knows about its own path parameters. A Route at `/items/{id}` inside a `Mount("/api/{version}")` expects `expected_params = {"id"}`. Calling `route.url_path_for("items", version=1, id=42)` → `seen_params = {"version", "id"}` ≠ `expected_params = {"id"}` → `NoMatchFound`. The registry breaks for any named route inside a parameterized Mount. The improvement that claims to make URL generation "a true function" makes it fail for a substantial class of real routes.

---

## THREE PROPERTIES VISIBLE FROM STRENGTHENING

**1. Name uniqueness and dispatch reachability are orthogonal conditions.**

Writing the docstring required articulating WHY name uniqueness makes `url_path_for` canonical. The argument: one name → one route → one path pattern instantiation. But writing this made visible that uniqueness addresses the naming direction only. A uniquely named route can be shadowed by a Mount. Shadow detection requires dispatch simulation — iterating the route list with a synthetic scope and checking which handler reaches FULL match first. The uniqueness registry has no mechanism to perform this simulation. Writing the docstring forced claiming a guarantee ("canonical URL") that requires dispatch-direction information the registry doesn't have.

**2. The registry must be rebuilt on every dynamic route mutation, but there's no hook.**

Starlette's Router supports `add_route(path, endpoint, ...)` and `include_router(router)` after construction. The registry is built once at `__init__`. After a dynamic addition, the registry is stale: `url_path_for` uses the old index while `app` dispatch uses the updated `self.routes`. Writing the registry made this mutation window visible. The original linear scan (`for route in self.routes`) is automatically consistent with dynamic mutations because it reads `self.routes` at call time. The registry trades dynamic consistency for static performance, creating a correctness window the original code didn't have.

**3. The leaf route's `url_path_for` cannot reconstruct the full path through Mount prefixes.**

Extracting `route.url_path_for(local_name, **path_params)` for registry-stored leaf routes revealed that Mount prefix composition is a traversal property, not a route property. `Mount.url_path_for` achieves full-path generation by composing `path_prefix + child_url` during recursive traversal — each level contributes its local prefix, and the call stack accumulates the full path. When the registry bypasses this traversal and calls the leaf route directly, it gets only the route's local path. The Mount's contribution is lost. Writing the registry made visible that `url_path_for`'s correct output depends on the traversal path taken to reach the route, not on the route object alone — which means no flat index can serve `url_path_for` correctly without replicating the traversal.

---

## THE SECOND IMPROVEMENT (Contradiction)

Improvement 1 formalizes "name uniqueness makes url_path_for canonical." The contradicting improvement validates dispatch reachability at construction time:

```python
import warnings

class RouteConsistencyWarning(UserWarning):
    pass


class Router:
    def __init__(self, routes=None, redirect_slashes=True, default=None,
                 lifespan=None, *, middleware=None):
        self.routes = [] if routes is None else list(routes)
        # ... rest of __init__
        self._validate_url_dispatch_consistency()

    def _validate_url_dispatch_consistency(self) -> None:
        """
        Verify that url_path_for produces URLs that will dispatch to their
        intended handlers. For each named route, generate its path pattern
        and simulate dispatch to confirm no earlier route shadows it.

        This enforces the round-trip invariant: url_path_for(name) returns
        a URL that, when requested, reaches the handler registered under name.
        Without this check, url_path_for may succeed for permanently unreachable
        routes, generating links that silently route to different handlers.
        """
        for route in self.routes:
            name = getattr(route, "name", None)
            if not name:
                continue
            try:
                url = self._url_path_for_single(route, name)
            except (NoMatchFound, Exception):
                continue  # Parameterized routes — skip; params unknown at construction

            # Simulate dispatch with the generated URL
            synthetic_scope: Scope = {
                "type": "http",
                "method": "GET",
                "path": str(url),
                "root_path": "",
                "query_string": b"",
                "headers": [],
                "path_params": {},
            }
            first_full_route = self._find_first_full_match(synthetic_scope)
            if first_full_route is not None and first_full_route is not route:
                warnings.warn(
                    f"Route '{name}' at path '{url}' is shadowed by "
                    f"'{getattr(first_full_route, 'name', repr(first_full_route))}'. "
                    f"url_path_for('{name}') will generate '{url}', "
                    f"but requests to that URL will reach the shadowing route. "
                    f"Reorder route registration or remove the unreachable route.",
                    RouteConsistencyWarning,
                    stacklevel=4,
                )

    def _find_first_full_match(self, scope: Scope) -> BaseRoute | None:
        for route in self.routes:
            match, _ = route.matches(scope)
            if match == Match.FULL:
                return route
        return None
```

This also passes code review. The RFC-like argument ("the round-trip invariant") is precise and correct. The warning (not raise) preserves backward compatibility. The `_find_first_full_match` logic is directly parallel to the dispatch loop's own logic. Both improvements address a real gap in url_path_for's contract and can be reviewed independently.

---

## THE STRUCTURAL CONFLICT

**The conflict that exists only because both improvements are legitimate:**

Improvement 1 makes name uniqueness a construction-time invariant: one name, one route, canonical URL. The docstring calls this "a true function."

Improvement 2 makes dispatch reachability a construction-time invariant: every named route is the first-dispatch-match for its generated URL.

These seem complementary. They conflict at a single structural point: **the definition of "canonical."**

Improvement 1 defines canonical in the naming direction: `url_path_for(name)` has a unique result. This allows a uniquely-named route to be shadowed in dispatch — the name is unique but the generated URL routes to a different handler.

Improvement 2 defines canonical in the dispatch direction: `url_path_for(name)` produces a URL that dispatches to the named handler. This allows duplicate names — two routes at the same path with different methods are both reachable (via method dispatch), but naming uniqueness would prohibit registering both under different names.

Applying both: every named route must be both uniquely named AND the first-dispatch-match for its path. This prohibits any configuration where a named route is shadowed. Shadowing occurs when a Mount covers a path that a flat route also covers — exactly the pattern that enables Mount-based composition.

Mount-based composition is Starlette's primary architectural feature: `include_router` works by creating Mounts. A large application that includes sub-routers creates Mounts that cover path prefixes. If those prefixes overlap with flat routes (from any earlier registration), both improvements together would either raise at construction time (Improvement 1: duplicate name) or warn loudly (Improvement 2: shadowed route). The developer who composes two independently-correct routers produces a router that fails both invariants — not because either router is wrong, but because composition creates overlap.

The conflict exists because both improvements are correct for single-router, single-level routing tables, and both become incorrect for composed routing tables. The improvements cannot coexist in a system designed for composition.

---

## THE THIRD IMPROVEMENT (Resolution)

Resolve the conflict by making canonicity context-dependent: a route is canonical within its own scope (Mount-level), and reachability warnings fire only when a route is shadowed by a route at the SAME level — not across Mount boundaries:

```python
class Router:
    def __init__(self, routes=None, ...):
        self.routes = [] if routes is None else list(routes)
        self._canonical_paths: dict[str, str] = {}  # name → full path
        self._build_route_graph(self.routes, path_prefix="", name_prefix="")
        # ...

    def _build_route_graph(
        self,
        routes: list[BaseRoute],
        path_prefix: str,
        name_prefix: str,
    ) -> None:
        """
        Build a bidirectional routing graph that tracks both:
        (a) name → canonical path (for url_path_for consistency), and
        (b) path → dispatch priority (for reachability validation).

        A route is canonical at its level if no earlier route at the same
        routing level claims its path. Cross-level shadowing (a Mount at
        an outer level shadowing a flat route) is structural — accepted as
        a consequence of composition — and not warned about here.
        """
        seen_paths_at_level: dict[str, str] = {}  # path_pattern → first route name
        for i, route in enumerate(routes):
            route_name = getattr(route, "name", None)
            full_name = (
                f"{name_prefix}:{route_name}"
                if name_prefix and route_name
                else route_name or ""
            )
            route_path = path_prefix + getattr(route, "path", "")

            # Check same-level path shadowing
            path_pattern = getattr(route, "path_format", None)
            if path_pattern is not None:
                full_pattern = path_prefix + path_pattern
                if full_pattern in seen_paths_at_level:
                    shadower_name = seen_paths_at_level[full_pattern]
                    if full_name:
                        warnings.warn(
                            f"Route '{full_name}' at '{full_pattern}' is shadowed "
                            f"at the same routing level by '{shadower_name}'.",
                            RouteConsistencyWarning,
                        )
                else:
                    seen_paths_at_level[full_pattern] = full_name or repr(route)

            if full_name:
                if full_name in self._canonical_paths:
                    raise ValueError(f"Duplicate route name '{full_name}'.")
                self._canonical_paths[full_name] = route_path

            # Recurse into Mount children
            child_prefix = full_name if full_name else name_prefix
            child_path = (path_prefix + route.path) if hasattr(route, "path") else path_prefix
            if hasattr(route, "routes") and route.routes:
                self._build_route_graph(route.routes, child_path, child_prefix)
```

This resolves the conflict: it enforces name uniqueness (satisfying Improvement 1), detects same-level shadowing (satisfying Improvement 2 for the case where shadowing is most obvious), and accepts cross-level shadowing as structural rather than erroneous (preserving composability).

---

## HOW IT FAILS

**1. `path_prefix + route.path` does not compute dispatch paths.**

Mount's dispatch path is not `parent_path + mount.path` — it's the result of the regex match. `Mount.path = "/api"` (after `rstrip("/")`), but the Mount's regex is compiled as `compile_path("/api/{path:path}")`, which matches `/api/anything` and sets `remaining_path = "/anything"`. The dispatch path through the Mount includes neither the trailing slash logic nor the `root_path` adjustments that `Mount.matches` performs. `route_path = path_prefix + route.path` produces `/api` (for a top-level Mount at `/api`), but the actual path used in dispatch child scopes is computed dynamically from `matched_path = route_path[: -len(remaining_path)]`. String concatenation produces a static approximation of a dynamic computation.

**2. `path_format` is the dispatch attribute; `url_path_for` uses it for construction, not matching.**

`seen_paths_at_level[full_pattern]` uses `path_format` (e.g., `/items/{id}`) as the key. Two routes with the same path format are at the same "path" in the naming system, but the dispatch regex might distinguish them — `{id:int}` and `{id}` produce different regexes that match different values. Conversely, two routes at `/items/{user_id}` and `/items/{item_id}` have different formats but the same structure and will conflict in dispatch. The format string is a construction artifact; using it as a dispatch identity key produces a different partition than the dispatch system uses.

**3. Same-level shadowing detection misses the common case.**

The `seen_paths_at_level` check catches only two routes at identical path formats in the same routes list. The most common shadowing in real applications occurs across levels: a Mount at `/api` captures requests to `/api/items`, shadowing a Route at `/api/items` in the outer router. This is cross-level shadowing. The `_build_route_graph` recursion processes the outer router's routes at one call frame and the Mount's child routes at a deeper call frame — `seen_paths_at_level` is a local variable, distinct per recursion level. Cross-level shadows are never compared. The warning fires for the case that barely occurs (two flat routes at the same path) and misses the case that actually occurs (Mount prefix overlapping individual routes).

**4. WebSocket routes are invisible to the consistency check.**

`Route.matches` returns `Match.NONE` for WebSocket routes when `scope["type"] == "http"`. `_find_first_full_match` uses a synthetic HTTP scope (`"type": "http"`). A route registered as `WebSocketRoute("/ws", handler, name="ws")` would never produce a FULL match in the synthetic scope. The consistency check silently passes for all WebSocket routes — not because they're consistent, but because the simulation uses the wrong scope type. Shadow detection produces false negatives for every WebSocket route.

---

## WHAT THE FAILURE REVEALS ABOUT THE DESIGN SPACE

The conflict (Improvement 1 vs. 2) revealed: `url_path_for` has two incompatible success criteria — name uniqueness and dispatch reachability. The conflict said: *we need to choose which guarantee the system makes.*

Improvement 3's failure reveals *why choosing is impossible*: **the path from a route name to its canonical URL and the path from a URL to its dispatched handler use irreconcilably different data representations.**

**URL generation requires global path context, assembled bottom-up.**

`Mount.url_path_for` achieves correct path generation by accumulating prefix strings during recursive descent: each level contributes `path_prefix.rstrip("/") + child_url`. The full path is assembled from root to leaf through the call stack. The accumulation is the mechanism — it's not an optimization or a convenience. Flattening this into a static structure (the graph) loses the accumulation, because the accumulated value depends on the traversal path taken, not on any property of the individual route.

**Dispatch requires local priority decisions, applied top-down.**

Each router level makes a local decision: does this route return FULL, PARTIAL, or NONE? The first FULL match wins. Priority is local — Route A at position 0 beats Route B at position 1, within the same routes list. But a Mount at position 0 captures ALL matching paths before the inner routes are consulted — so "position within the routes list" and "dispatch priority for a specific path" are not the same concept. A route inside a Mount has local priority 0 within the Mount's inner router, but global dispatch priority is determined by whether the Mount's prefix matches before any outer-level route.

**The failure modes correspond to this directional incompatibility:**

- *Path construction fails across Mounts* — because construction requires bottom-up accumulation and the graph is a flat, top-down structure
- *Same-level shadow detection misses cross-level shadows* — because dispatch priority is hierarchical (cross-level) and the detection is flat (same-level)
- *WebSocket routes are invisible* — because the dispatch simulation is typed (HTTP scope) and URL generation is type-independent (names don't carry scope type)
- *`path_format` keys conflate construction format with dispatch identity* — because the two operations use the same string for different semantics

**The conflict alone could not reveal this: it said we need a better algorithm.** It was possible to read the conflict as: "we need a smarter traversal — one that checks name uniqueness AND dispatch priority." Improvement 3's failure shows this is wrong. No traversal of the current data structure simultaneously satisfies both requirements, because the requirements mandate opposite directions of information flow:

- URL generation: leaf → root (accumulate prefix from root to leaf, return to caller)
- Dispatch validation: root → leaf (process each level locally, stop at first FULL)

A single traversal cannot simultaneously flow in both directions. The RoutingGraph tries to pre-compute both at construction time, producing a static structure that is wrong for the direction it approximates and useless for the direction it ignores.

**What the failure reveals about the design space:**

The dispatch system and the URL generation system are not inverses of each other. They cannot be made into inverses without a fundamental change to the data model. Dispatch is a FUNCTION of (request, route_list): it produces one handler by applying priority ordering to a set of matches. Its inverse would be a function of (handler, route_list): find the canonical URL for that handler. But dispatch is non-injective — multiple paths can reach the same handler (through different routes), and multiple routes can map to the same path (through priority ordering where all but the first are shadowed). A non-injective function has no inverse.

Making dispatch injective — ensuring every path reaches exactly one handler AND every handler is reachable via exactly one canonical path — requires eliminating route overlap entirely. Route overlap elimination requires that the route list be a partition of the path space. Starlette's routing explicitly supports non-partition configurations: Mounts can overlap with flat routes, and this overlap is the mechanism by which large applications are composed from smaller routers.

The design space has a topological constraint: **flexible composition requires non-partition routing; consistent round-trip routing requires partition routing.** These are mutually exclusive. Every algorithm, data structure, or validation layer that tries to provide both is operating in an infeasible region of the design space.

---

## THE REDESIGN: EXPLICIT DECOUPLING OF PATH CONSTRUCTION AND DISPATCH REACHABILITY

Accept the design space's topology. The routing system supports non-partition route tables. Therefore it cannot guarantee round-trip consistency. Do not pretend otherwise — but also do not leave users without any mechanism to reason about consistency.

Provide two clearly-separated operations:

```python
class Router:
    def url_path_for(self, name: str, /, **path_params) -> URLPath:
        """
        Construct the URL satisfying the named route's path pattern for
        the given parameters.

        Contract: The returned URL satisfies the route's path constraints
        for the given parameters.

        Not a contract: The returned URL will dispatch to the named route.
        In routing tables with path overlap (e.g., a Mount prefix overlapping
        individual flat routes), url_path_for may succeed for routes that are
        permanently unreachable in dispatch. Use assert_reachable() to verify
        dispatch consistency when constructing routing tables.
        """
        for route in self.routes:
            try:
                return route.url_path_for(name, **path_params)
            except NoMatchFound:
                pass
        raise NoMatchFound(name, path_params)

    def assert_reachable(
        self,
        name: str,
        method: str = "GET",
        /,
        **path_params,
    ) -> URLPath:
        """
        Assert that url_path_for(name, **path_params) produces a URL that
        dispatches to the handler registered under name for the given method.

        Raises RoutingConsistencyError if the route is shadowed.
        Returns the URL on success.

        This is a validation tool for test suites and development environments.
        It performs a dispatch simulation: generates the URL, runs it through
        the route-matching logic, and verifies the first FULL match is the
        named route.

        Because it performs a full dispatch simulation, it correctly detects
        cross-level shadowing (a Mount prefix shadowing a flat route) that
        construction-time validation cannot detect.
        """
        url = self.url_path_for(name, **path_params)
        synthetic_scope: Scope = {
            "type": "http",
            "method": method.upper(),
            "path": str(url),
            "root_path": "",
            "query_string": b"",
            "headers": [],
            "path_params": {},
        }
        first_match = self._find_first_full_match(synthetic_scope)
        expected_route = self._find_route_by_name(name)
        if first_match is not expected_route:
            shadower = getattr(first_match, "name", repr(first_match))
            raise RoutingConsistencyError(
                f"Route '{name}' is shadowed. url_path_for('{name}') → '{url}', "
                f"but {method} {url} dispatches to '{shadower}', not '{name}'. "
                f"The route '{name}' is unreachable."
            )
        return url
```

Application code uses `url_path_for` — fast, always available, correct for non-overlapping tables.
Test suites and startup validation use `assert_reachable` — slow, explicit, detects the gap.

The two methods coexist without conflict: `url_path_for` makes no reachability claim; `assert_reachable` makes the reachability claim explicitly and detects violations.

---

## WHAT IT SACRIFICES

**The single-operation link-generation interface.** Every framework with URL generation provides one call: `reverse("name", **params)`. Users expect one call to produce a correct, routable URL. The redesign requires two calls for safety — `url_path_for` for the path, `assert_reachable` for the guarantee. Applications that want safety must adopt a discipline: call `assert_reachable` at startup or in test suites for every named route. This is not a runtime cost, but it is an architectural discipline that the framework cannot enforce — it can only provide the tool.

**Silent success for unreachable routes.** The original `url_path_for` succeeds silently for shadowed routes. The redesign preserves this behavior (still silently succeeds). Users who don't know to call `assert_reachable` get no protection. The redesign protects users who know to ask for protection; it does nothing for users who don't know the question.

---

## WHAT THE REDESIGN REVEALS WAS NEVER A FLAW

The original `url_path_for`'s silence about dispatch reachability — the absence of any warning, check, or error when a route is shadowed — was not an oversight. It was the honest acknowledgment of what `url_path_for` actually computes.

`url_path_for` computes **path pattern instantiation**: given a route's path format and a set of parameter values, produce the URL that satisfies the route's own constraints. This is a legitimate, correct operation. `Route("/api/{version}/items", f)` with `version="v1"` genuinely produces `/api/v1/items` — the route's pattern is satisfied. Whether `/api/v1/items` dispatches to `f` is a different question, about the routing table's partition structure, not about the route's path pattern.

The "flaw" — that `url_path_for` doesn't guarantee dispatch reachability — was not a design mistake. It was the cost of building a routing system that supports composition through route overlap. The round-trip invariant (`dispatch(url_path_for(name)) == handler(name)`) holds if and only if the routing table is a partition — no path is claimed by more than one route. Starlette's routing deliberately supports non-partition tables: Mounts overlap with flat routes (this is how `include_router` composes sub-applications), and this overlap is the mechanism of composability.

The impossible goal was making one operation — `url_path_for` — simultaneously guarantee both path construction (which it can always compute locally) and dispatch reachability (which requires a global partition property the routing table may not have). Every attempt to retrofit the reachability guarantee onto `url_path_for` fights the non-partition architecture. Improvement 1 (name uniqueness) enforces partitioning in the naming direction without addressing dispatch partitioning. Improvement 2 (reachability validation) detects non-partitioning in dispatch but prohibits composition. Improvement 3 (bidirectional graph) tries to represent both simultaneously and fails because the two directions require incompatible representations.

The redesign accepts that path construction and reachability are different operations with different preconditions. `url_path_for` computes path construction, always and correctly. `assert_reachable` computes reachability, when asked, in applications that have non-overlapping routing tables.

L10-B concluded: "the routing system indexes by route, not by resource — and no traversal strategy, condition logic, or scope injection can bridge that gap, because it is a data model gap." The redesign reveals the same gap from the reverse direction: `url_path_for` indexes by name, dispatch indexes by path, and no validation layer can make these indexes consistent in a routing system that supports overlap. The gap is the cost of the flexibility. The silence was its honest acknowledgment.
