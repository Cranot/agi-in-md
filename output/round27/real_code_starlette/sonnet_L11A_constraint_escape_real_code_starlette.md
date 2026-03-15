# Structural Analysis: Starlette Routing

---

## The Claim

**The deepest structural problem: route tree traversal is entangled with path decomposition, making the tree's structure unqueryable without executing its transformations.**

Every operation — dispatch, URL generation, method collection — must re-execute the same path-stripping transformation to read the tree's own contents. Structure and transformation are fused. Reading requires writing.

*Falsifiable prediction:* You cannot generate a correct 405 Allow header listing *all* methods for a given path across all matching routes without re-traversing the tree a second time, because the first traversal commits to a single route before checking the others.

---

## Three Experts

**Expert A — Defends:** The prediction is demonstrably correct. In `Router.app()`, the loop commits to `partial` on first match and breaks out. In `Route.handle()`, the Allow header contains only `", ".join(self.methods)` — *this route's* methods. If two routes share a path but differ in methods, a mismatched-method request returns `Allow: GET, HEAD` when the correct answer is `Allow: GET, HEAD, POST`. This is observable, wrong behavior flowing directly from single-pass commitment.

**Expert B — Attacks:** Scope mutation isn't the core problem — it's ASGI protocol design. Routes are supposed to modify scope; that's the contract. The real problem is `Match.PARTIAL`'s semantics: it conflates "path matched" with "method didn't." This is wrong granularity in the enum, not wrong in the mutation. Notice that `redirect_slashes` already works correctly by using `redirect_scope = dict(scope)` — the system already knows how to avoid mutation when it matters.

**Expert C — Probes the shared assumption:** Both of you assume this system has one job (correct request dispatch). It has two orthogonal jobs: *dispatch* and *URL generation*, and the claim applies differently to each. URL generation via `url_path_for` has an independent catastrophe: it uses `try/except NoMatchFound` in nested loops as a branching mechanism. `Router.url_path_for` catches `NoMatchFound` from every route; `Mount.url_path_for` does the same recursively. This is O(n·depth) exception-based tree walking. These two problems — dispatch mutation and URL generation control flow — look unrelated, but why does the same tree structure force both?

---

## Claim Transformation

After the dialectic, the claim sharpens:

**Transformed claim:** The routing tree is a shared data structure expected to serve two incompatible traversal strategies — dispatch (imperative, depth-first, commit-on-match, path-mutating) and URL generation (declarative, exhaustive backtracking, exception-based) — and these strategies are structurally opposed. Every new query type (method collection, schema generation, logging) must also be grafted onto this same incompatible interface.

**The gap:** I began with "mutation causes problems." The transformed claim is "incompatible traversal strategies share one structure." Mutation was a symptom. The dual-use tree is the cause.

---

## The Concealment Mechanism

**Uniform interface polymorphism hiding strategy divergence.**

`BaseRoute` declares `matches`, `url_path_for`, `handle`, and `__call__` as a clean, symmetric interface. `Route` and `Mount` implement all four. This symmetry makes them *appear* to be equivalent route-matching entities.

What it hides:
- `Route.matches()` is O(1) regex; `Mount.matches()` always returns FULL and defers to sub-routing — fundamentally different semantics under the same method name
- `Route.url_path_for()` does parameter substitution; `Mount.url_path_for()` does recursive tree search via exceptions
- `Route.handle()` can generate 405; `Mount.handle()` always delegates — meaning error detection happens at variable depths depending on nesting
- The polymorphic interface hides that Mount and Route have opposite "cost" structures for the same method calls

The uniform interface says: "these are the same kind of thing." The implementation says: "these are fundamentally different traversal strategies wearing the same interface."

---

## Improvement 1: Legitimate Deepening of the Concealment

Here is an improvement that would pass code review:

```python
class Router:
    async def app(self, scope, receive, send):
        assert scope["type"] in ("http", "websocket", "lifespan")
        if "router" not in scope:
            scope["router"] = self
        if scope["type"] == "lifespan":
            await self.lifespan(scope, receive, send)
            return

        full_match = None
        partial_matches: list[tuple] = []

        for route in self.routes:
            match, child_scope = route.matches(scope)
            if match == Match.FULL:
                if full_match is None:
                    full_match = (route, child_scope)
                # Don't break: continue to collect partials for 405 aggregation
            elif match == Match.PARTIAL:
                partial_matches.append((route, child_scope))

        if full_match is not None:
            route, child_scope = full_match
            scope.update(child_scope)
            await route.handle(scope, receive, send)
            return

        if partial_matches:
            # Aggregate allowed methods from ALL partial matches for correct Allow header
            allowed_methods: set[str] = set()
            for r, _ in partial_matches:
                if hasattr(r, "methods") and r.methods:
                    allowed_methods.update(r.methods)
            route, child_scope = partial_matches[0]
            scope.update(child_scope)
            scope["_router_allowed_methods"] = frozenset(allowed_methods)
            await route.handle(scope, receive, send)
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
```

This passes code review because:
- It fixes the real, documented bug (incomplete Allow header)
- It's backward compatible
- The pattern (collect all, pick first) is familiar
- The test suite for 405 behavior would pass

---

## Three Properties Visible Only Because We Tried to Strengthen It

**1. Scope is an untyped global variable used as a communication channel.**
We had to add `scope["_router_allowed_methods"]` — a private key with no schema, no type guarantees, and no documented contract. `Route.handle()` would need to check for it. The fix exposes that scope has become a mutable bag passing invisible messages between components that are supposed to be independent.

**2. The improvement is depth-1 only.**
`Mount` never returns `PARTIAL` — it always returns `FULL` and delegates. So our "aggregate all partial matches" fix works only at the top-level router. When a `Mount` contains two sub-routes with different methods for the same path, the Mount returns FULL to our aggregation loop, we see no partials, and the inner 405 is still broken. Trying to fix the aggregation reveals that it cannot be fixed without reaching inside Mount — which violates the uniform interface.

**3. `handle()` is called on one route but the relevant information is aggregate across many.**
We collect methods from multiple routes but must call `handle()` on exactly one. The method signature `handle(scope, receive, send)` has no mechanism to accept aggregate information. We are forced to smuggle it through scope, recreating the same coupling we tried to escape. The interface cannot be extended to receive cross-route context without changing every implementer.

---

## What the Improvement Conceals — and What It Recreates

The improvement makes the 405 case *look* solved. Code review passes. Tests pass for top-level routes. What it conceals: the fix is local; the problem is topological.

**What it recreates:** Through a `Mount`, the path-stripping that `Mount.matches()` performs to convert `route_path` into `remaining_path` is inextricably coupled to traversal. `allowed_methods_for_path` at the Mount level requires re-executing that same stripping to pass the correct sub-path to sub-routes. Our improvement doesn't reach inside Mount; to reach inside, you would re-implement path stripping. And re-implementing path stripping *is* re-implementing `matches()`. The improvement recreates the invariant precisely at the Mount boundary.

---

## Improvement 2: Addressing the Recreated Property

Add a separate, non-mutating query method to the `BaseRoute` interface:

```python
class BaseRoute:
    def matches(self, scope): raise NotImplementedError()
    def url_path_for(self, name, /, **path_params): raise NotImplementedError()
    async def handle(self, scope, receive, send): raise NotImplementedError()
    async def __call__(self, scope, receive, send): ...

    def allowed_methods(self, scope) -> frozenset[str] | None:
        """Non-mutating path query. Returns None if path doesn't match,
        frozenset of methods if it does (empty frozenset = any method allowed)."""
        return None

class Route(BaseRoute):
    def allowed_methods(self, scope) -> frozenset[str] | None:
        if scope["type"] == "http":
            route_path = get_route_path(scope)
            if self.path_regex.match(route_path):
                return frozenset(self.methods) if self.methods else frozenset()
        return None

class Mount(BaseRoute):
    def allowed_methods(self, scope) -> frozenset[str] | None:
        if scope["type"] not in ("http", "websocket"):
            return None
        route_path = get_route_path(scope)
        match = self.path_regex.match(route_path)
        if not match:
            return None
        matched_params = match.groupdict()
        remaining_path = "/" + matched_params["path"]
        # Construct sub-scope with stripped path — without mutating original
        sub_scope = {**scope, "path": remaining_path,
                     "path_params": {**scope.get("path_params", {})}}
        collected: set[str] = set()
        for route in self.routes or []:
            methods = route.allowed_methods(sub_scope)
            if methods is not None:
                collected.update(methods)
        return frozenset(collected) if collected else None
```

Then in `Router.app()`, replace the `scope["_router_allowed_methods"]` hack:

```python
if partial_matches:
    allowed: set[str] = set()
    for route in self.routes:
        methods = route.allowed_methods(scope)
        if methods is not None:
            allowed.update(methods)
    # ... dispatch to first partial, pass `allowed` to handle via scope or headers
```

This looks like a proper fix: a dedicated query method, non-mutating, delegating correctly through Mount boundaries via a sub-scope copy.

---

## Diagnostic Applied to Improvement 2

**What it conceals:** It adds a *third* traversal algorithm to a tree already supporting two. The routing tree now must serve: dispatch (`matches` + `handle`), URL generation (`url_path_for`), and method collection (`allowed_methods`). Each traversal is structurally similar — pattern match, extract remainder, recurse — but implemented independently, tripling the surface area for bugs.

**What property of the original problem is visible only because this improvement recreates it:**

`Mount.allowed_methods()` constructs `sub_scope = {**scope, "path": remaining_path}` — a copy of scope with path-stripping applied. This is, functionally, what `Mount.matches()` does, except `matches()` also mutates `root_path` and sets `endpoint`. The improvement reveals:

**Every query operation on this tree must perform path decomposition — strip the matched prefix, recurse with the remainder. Path decomposition is the only access mechanism for sub-tree information.**

This is the invariant.

---

## The Structural Invariant

> **Path decomposition is both the access mechanism and the transformation. To query sub-tree structure, you must execute the sub-tree transformation. Reading requires writing, or re-implementing writing.**

This persists through every improvement:
- Dispatch reads by executing `matches()` — which strips path and mutates scope
- URL generation reads by executing template substitution in reverse — which reassembles path by traversal
- Method collection (improvement 2) reads by executing path-stripping — which re-implements matches without the side effects
- Any new query (schema export, route documentation, caching) must also implement path decomposition

No improvement eliminates this because it is not a property of any single implementation — it is a property of the *problem formulation:* hierarchical path routing where sub-tree relevance depends on how much path was consumed by ancestors.

---

## The Category

**Transform-coupled route trees:** routing designs where path decomposition is the only access mechanism for hierarchical routing structure. Every query — regardless of purpose — must execute the decomposition transformation to traverse the tree.

The invariant that bounds this category:

> Sub-tree information is structurally unreachable without executing ancestor path transformations.

---

## The Adjacent Category: Compiled Routing Tables

The adjacent category dissolves the invariant by separating structure from transformation at a compile step. The tree is compiled *once* into a queryable form, and querying does not require re-executing transformation.

```python
@dataclass(frozen=True)
class RouteRecord:
    """Pure structural data — transformation already executed at compile time."""
    pattern: re.Pattern
    path_format: str
    param_convertors: dict[str, Convertor]
    methods: frozenset[str] | None  # None = any
    endpoint: Any
    name: str | None
    children: tuple['RouteRecord', ...]  # Immutable sub-tree
    prefix: str  # The portion this record consumes

@dataclass
class RoutingTable:
    roots: tuple[RouteRecord, ...]
    by_name: dict[str, list[RouteRecord]]   # Pre-built for O(1) URL generation
    by_path_structure: Any                  # Pre-built trie for O(log n) dispatch

    def dispatch(self, path: str, method: str) -> DispatchResult:
        """Non-mutating. Returns complete result before any scope change."""
        ...

    def allowed_methods(self, path: str) -> frozenset[str] | None:
        """Separate non-mutating query. O(log n) via pre-built index."""
        ...

    def url_for(self, name: str, **params) -> str:
        """O(1) via by_name index. No exception-based traversal."""
        record = self.by_name.get(name)
        if record is None:
            raise NoMatchFound(name, params)
        return record.path_format.format(**params)

    @classmethod
    def compile(cls, routes: list[BaseRoute]) -> 'RoutingTable':
        """One-time compilation: walk the route tree, execute all
        path decompositions, store results as pure data."""
        ...
```

**How this succeeds where every improvement failed:**

1. **Decouples structure from transformation.** Path decomposition runs once at `compile()`. Every subsequent query reads compiled data, not live transformations. Adding `allowed_methods` requires zero new traversal code.

2. **Makes URL generation O(1).** `by_name` is built at compile time. `url_path_for` is a dict lookup, not a try/except tree walk. The O(n·depth) exception-based search disappears.

3. **Correct 405 responses by construction.** `allowed_methods(path)` is a separate query on pre-indexed data. It is structurally impossible for it to return a subset of the correct answer.

4. **Scope mutation is no longer the communication mechanism.** `dispatch()` returns a `DispatchResult` containing path params, endpoint, matched methods, and root path adjustments. The caller can inspect the full result before deciding whether to mutate scope, and how.

5. **New query types cost nothing.** Schema export, route documentation, logging middleware — each is a query on the pre-compiled `RoutingTable`, requiring no new traversal logic.

---

## The New Impossibility

**Dynamic route registration.**

In the transform-coupled tree, adding a route is `self.routes.append(route)` — O(1), immediate, live. Plugins, conditional routes, and test fixtures all work by appending. This is trivial.

In the compiled routing table, adding a route requires `RoutingTable.compile()` — re-traversing all routes, re-building the trie, re-building `by_name`, re-validating duplicate params. If this happens at request time, you've destroyed the performance model. If it happens at startup only, runtime route registration is impossible.

What was trivial in the original category — dynamically adding routes, registering routes from plugins, building routes from database content at startup — becomes a structured phase transition requiring explicit recompilation.

---

## The Finding

| Property | Transform-Coupled Tree | Compiled Routing Table |
|---|---|---|
| Dynamic route registration | **Trivial** — O(1) append | **Impossible** — requires recompile |
| Correct 405 Allow headers | **Impossible** — requires re-traversal | **Trivial** — separate index |
| URL generation | **O(n·depth)** with exceptions as control flow | **O(1)** via pre-built index |
| New query types | **Impossible** — each requires new traversal | **Trivial** — query pre-compiled data |
| Scope mutation safety | **Violated by design** | **Not needed** |
| Plugin/middleware route registration | **Natural** | **Requires commit to compile phase** |

**The trade-off between old and new impossibilities is the finding:**

The original design makes *composition* trivial at the cost of making *queries* structurally incorrect. Any Python object can be a route; any route can be added at any time; no commitment to a final structure is required. This is the design's genuine strength, not an accident.

The compiled design makes *queries* trivially correct at the cost of making *composition* expensive. Correct behavior for every cross-cutting concern — 405 responses, URL generation, schema export — is now a solved problem. But you must commit to a static topology before the first request.

The structural invariant — *reading requires re-executing writing* — is not a bug in Starlette's implementation. It is the cost of choosing dynamic composability over query correctness. Starlette chose composability, correctly, for a web framework. The price is that every query (URL generation, method collection, anything cross-cutting) must be re-implemented as a traversal, and will be structurally incomplete until it is.

The invariant is not a flaw. It is the fingerprint of the category.
