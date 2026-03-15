# Structure First Analysis: Starlette Routing

## Initial Claim

**Deepest structural problem**: The scope mutation pattern (`scope.update(child_scope)`) creates implicit state coupling between routing layers that accumulates invisibly. Each mount/route in the nesting chain mutates a shared dictionary, and downstream handlers depend on implicit invariants about what keys exist and their values—yet these invariants are undocumented, untested at boundaries, and can be corrupted by middleware that modifies scope between routing stages.

---

## Three Experts Test the Claim

### Expert A (Defends): "This is real and dangerous"

The claim identifies a genuine architectural weakness. Consider nested mounts:
```python
Mount("/api", routes=[
    Mount("/v1", routes=[
        Route("/users/{id}", handler)
    ])
])
```

Each Mount modifies `root_path`, `app_root_path`, and `path_params`. If middleware at the `/api` level modifies any of these, the inner mount sees corrupted state. The implicit contract—"thou shalt not modify scope keys that routing uses"—is nowhere enforced. A middleware that strips a prefix for URL rewriting would break inner routing silently.

### Expert B (Attacks): "This is how ASGI works"

The claim attacks a non-problem. The scope dictionary IS the ASGI request representation—mutation is the intended pattern. The spec defines scope as mutable state that passes through the ASGI stack. Routes aren't "corrupting" scope; they're progressively enriching it. The "implicit invariants" are actually explicit in the ASGI specification and well-understood by framework authors. This is feature, not bug.

### Expert C (Probes assumptions): "What does both take for granted?"

Both experts assume the scope dictionary is the *only* communication channel between routing layers. But there's a second channel: the Match enum return value. The PARTIAL/FULL distinction creates a parallel decision tree that affects which scope mutations "count." When a route returns `Match.PARTIAL`, the scope is populated but the route isn't executed—yet those scope mutations persist if no FULL match is found later. Expert A's claim about "accumulated state" misses that PARTIAL matches leave "orphan mutations" in scope that handlers never asked for.

---

## Transformed Claim

**The problem is not scope mutation per se, but the non-transactional nature of routing decisions**: scope mutations from PARTIAL matches persist even when those routes aren't selected, creating "phantom state" that can affect error handling and the `default` handler. The scope dictionary becomes a log of attempted matches, not just the successful one.

---

## Concealment Mechanism

**Name**: *Progressive Enrichment Mask*

The code conceals its real problem by presenting scope mutation as "enrichment"—a positive-sounding frame that implies only additive, beneficial changes. The pattern `scope.update(child_scope)` looks like giving more information to downstream code. What it hides: enrichment from *rejected* routes also persists. The Match enum creates a control-flow branch, but scope mutations happen outside that branch's transaction boundary.

---

## Applying the Concealment: A "Legitimate" Improvement

```python
class Router:
    async def app(self, scope, receive, send):
        # ... existing code ...
        
        partial = None
        partial_scope = None  # Track scope separately
        
        for route in self.routes:
            match, child_scope = route.matches(scope)
            if match is Match.FULL:
                # Create a fresh scope copy for FULL matches
                # to prevent pollution from previous PARTIAL matches
                final_scope = dict(scope)
                final_scope.update(child_scope)
                await route.handle(final_scope, receive, send)
                return
            elif match is Match.PARTIAL and partial is None:
                partial = route
                partial_scope = child_scope

        if partial is not None:
            final_scope = dict(scope)
            final_scope.update(partial_scope)
            await partial.handle(final_scope, receive, send)
            return
```

**Code review would pass**: "Prevents scope pollution, cleaner isolation, explicit scope lifecycle."

---

## What the Improvement Conceals

The improvement **deepens concealment** by making scope appear transactional at the Router level, while the real problem lives at the Route level. Each Route's `matches()` method still mutates the scope it receives through `path_params.update()` inside the returned `child_scope`. But now the Router hides this by copying.

**Three properties visible only because I tried to strengthen the concealment:**

1. **Mutation happens during matching, not handling** — The `matches()` method is named as a query (it should be pure), but it constructs state that affects downstream behavior. The improvement treats the symptom (Router level) while the disease (matches is not pure) persists.

2. **PARTIAL matches are stored but their semantics are undefined** — What does it mean to store a PARTIAL match's scope? The code does it, but there's no documentation of what invariants that scope satisfies. Is it valid to use for error responses?

3. **The Match enum creates a three-way decision tree but only two branches are handled** — What about the interaction between PARTIAL matches at different nesting levels? A Mount can return PARTIAL (method mismatch on the mount's own methods?) but this interacts confusingly with child route PARTIALs.

---

## Second Improvement: Address Recreated Property

The first improvement concealed that `matches()` should be pure but isn't. Let me address that:

```python
class BaseRoute:
    def matches(self, scope) -> tuple[Match, dict]:
        """
        Returns a tuple of (match_type, child_scope_additions).
        
        IMPORTANT: This method MUST NOT modify the input scope.
        The returned dict contains only NEW keys to add.
        Callers are responsible for merging.
        """
        raise NotImplementedError()

class Route(BaseRoute):
    def matches(self, scope):
        if scope["type"] == "http":
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)
            if match:
                # Build child_scope from scratch, never mutate input
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                # NOTE: We CREATE a new dict, we don't UPDATE scope's path_params
                child_scope = {
                    "endpoint": self.endpoint, 
                    "path_params": {**scope.get("path_params", {}), **matched_params}
                }
                if self.methods and scope["method"] not in self.methods:
                    return Match.PARTIAL, child_scope
                else:
                    return Match.FULL, child_scope
        return Match.NONE, {}
```

---

## Apply Diagnostic to Second Improvement

**What does this improvement conceal?**

It makes `matches()` appear pure, but conceals that the `path_params` merging logic still has undefined semantics for nested mounts. When a parent mount adds `path_params` and a child route adds more, the merge order `{**scope.get("path_params", {}), **matched_params}` means child wins on conflict. Is this correct? Undocumented.

**What property of the original problem is visible only because this improvement recreates it?**

The **merge order semantics** for nested path parameters. The original code hid this inside `scope.update()`. By making the merge explicit, I've made visible that there's a policy decision (child wins over parent on key conflict) that was always there but invisible.

---

## Structural Invariant

**The property that persists through every improvement:**

> *Path parameter namespace collisions between nested routing levels are resolved by "last writer wins" with no warning, validation, or documentation.*

This is a property of the **problem space** (nested routing with path parameters), not the implementation. Whether you mutate scope, copy scope, or return deltas—when `/api/{id}` mounts a route `/users/{id}`, the `id` collision has to be resolved somehow. The invariant is: *something gets overwritten silently*.

---

## Invert the Invariant

What if the impossible property (safe handling of nested parameter collisions) became trivially satisfiable?

```python
class PathParams:
    """
    Path parameters as a stack of namespaces, not a flat dict.
    Each nesting level has its own namespace.
    """
    def __init__(self):
        self._stack: list[dict[str, Any]] = [{}]
    
    def push(self, params: dict):
        self._stack.append({**self._stack[-1], **params})
    
    def pop(self):
        self._stack.pop()
    
    def __getitem__(self, key):
        return self._stack[-1][key]
    
    def get(self, key, default=None):
        return self._stack[-1].get(key, default)
    
    def collisions(self) -> set[str]:
        """Returns keys that were overwritten at some level."""
        seen = set()
        collisions = set()
        for level in self._stack:
            collisions.update(seen & level.keys())
            seen.update(level.keys())
        return collisions
    
    def flatten(self) -> dict:
        """Legacy compatibility: returns flattened view with collision warning."""
        result = {}
        for level in self._stack:
            for k, v in level.items():
                if k in result:
                    warnings.warn(f"Path param '{k}' shadowed at nesting boundary")
                result[k] = v
        return result
```

---

## New Impossibility Created by Inversion

The inversion makes parameter collisions visible and safe, but creates a **new impossibility**:

> *Handlers that receive `scope["path_params"]` as a `PathParams` object break compatibility with any middleware or library that expects a plain dict.*

The conservation law: **you cannot add safety without breaking the implicit interface contract.** The `scope` dictionary is a lingua franca—changing its types breaks the ASGI ecosystem compatibility.

---

## Conservation Law

> **The Flat Scope Conservation Law**: In an ASGI routing system, any attempt to add structure to path parameter handling (namespacing, collision detection, type safety) must either (a) break the flat-dict interface that the ecosystem expects, or (b) internally maintain a flat dict for compatibility while the structured representation becomes a lie—a cached view that can be desynchronized from the source of truth.

The problem space (nested routing with path parameters in a dict-based scope) makes it **structurally impossible** to have both safe parameter handling and ecosystem compatibility.

---

## Meta-Analysis: What Does the Conservation Law Conceal?

**What does the law conceal about the problem?**

The law frames the problem as "structure vs. compatibility"—implying these are the only two axes. It conceals a third axis: **the scope dictionary is both data and metadata**. Path params are data (what the user provided), but their presence/nesting is metadata (what the routing tree looks like). The flat dict conflates these.

**What structural invariant of the law persists when I try to improve it?**

If I try to "fix" the law by proposing a hybrid approach (structured internally, flat for external consumers), the invariant that persists is: *there must be a serialization boundary*. Something must translate between the internal structured representation and the external flat representation. That boundary is where bugs live.

**Invert that invariant:**

What if there were no serialization boundary? What if the "flat dict" were a view computed on demand from structured data, with no separate storage?

```python
# Hypothetical: scope returns computed views, not stored dicts
@property
def path_params(self):
    return self._compute_flattened_params()  # Always fresh, never cached
```

---

## Meta-Law (Conservation Law of the Conservation Law)

> **The Serialization Boundary Conservation Law**: Any conservation law that identifies a trade-off between structure and compatibility conceals that the real invariant is the *existence of a translation boundary*. The boundary itself—not the choice of which side to favor—is what creates the impossibility. Translation boundaries are where:
> 1. Information is lost (structured → flat)
> 2. Ambiguity is introduced (flat → structured requires heuristics)
> 3. Bugs accumulate (each direction has edge cases)
> 
> **Testable prediction for this codebase**: Bugs involving path parameters will cluster around translation boundaries—specifically, in `url_path_for()` (which translates flat params back to a structured path) and in nested Mount scenarios (where params must be "un-translated" for child routing). The conservation law predicts these are the highest-bug-density zones.

---

## Concrete Bugs, Edge Cases, and Silent Failures

| # | Location | What Breaks | Severity | Fixable or Structural |
|---|----------|-------------|----------|----------------------|
| 1 | `request_response()` L30-38 | Nested `async def app` shadows outer `async def app`. The outer app's `scope, receive, send` are captured by closure, but if someone inspects the function signature of the returned app, it's misleading (seems like a normal ASGI app but internally depends on closure state). | Medium | **Fixable** — rename inner function |
| 2 | `Route.matches()` L126-139 | `path_params.update(matched_params)` overwrites parent mount's params with same-name child params silently. If `/api/{id}` mounts `/users/{id}`, the first `id` is lost. | High | **Structural** (per conservation law) |
| 3 | `Mount.__init__()` L166 | `self.path_regex, self.path_format, self.param_convertors = compile_path(self.path + "/{path:path}")` — always adds `{path:path}` even if mount has no children, creating a regex that matches more than intended. | Medium | **Fixable** — conditional compilation |
| 4 | `Mount.matches()` L179 | `remaining_path = "/" + matched_params.pop("path")` — if `path` param is somehow missing from regex match (corrupted regex, edge case in path), this raises KeyError, not a clean Match.NONE. | Low | **Fixable** — defensive get |
| 5 | `Mount.url_path_for()` L200-216 | If `self.name is None` and `name` contains `:` (e.g., `"foo:bar:baz"`), the split logic `name[len(self.name) + 1:]` becomes `name[1:]` which incorrectly strips the first character. Wait—no, if `self.name is None`, it uses the full `name`. But if `self.name = "foo"` and `name = "foo:bar:baz"`, it extracts `"bar:baz"` which is correct for one level but ambiguous for deeper nesting. | Medium | **Fixable** — clearer nesting delimiter protocol |
| 6 | `Router.__init__()` L224 | `self.routes = [] if routes is None else list(routes)` — copies the list but not the routes themselves. If route objects are mutated after Router creation, behavior is undefined. | Low | **Fixable** — document or deep copy |
| 7 | `Router.app()` L256-275 | `partial` and `partial_scope` are set on first PARTIAL match, but subsequent PARTIAL matches are ignored. If route A returns PARTIAL (method mismatch) and route B also returns PARTIAL, only A's scope is used. This may not be the desired behavior for error messages (A's 405 vs B's 405). | Medium | **Fixable** — track all PARTIALs |
| 8 | `Router.app()` L277-286 | Redirect logic re-matches all routes with modified scope. If original request matched PARTIAL and redirect scope also matches PARTIAL, infinite redirect loop potential (though unlikely with `/` handling). | Medium | **Fixable** — track attempted redirects |
| 9 | `replace_params()` L45-51 | Modifies `path_params` dict in place (`path_params.pop(key)`) while iterating over `list(path_params.items())`. Safe because of `list()` copy, but confusing and error-prone pattern. | Low | **Fixable** — return new dict |
| 10 | `compile_path()` L59 | `is_host = not path.startswith("/")` — a host route (`@app.route("{subdomain}.example.com")`) is distinguished only by not starting with `/`. But what if someone passes an empty string? `is_host = True` for empty path. | Low | **Fixable** — explicit parameter or assertion |
| 11 | `BaseRoute.__call__()` L87-95 | After `Match.NONE`, the method checks `scope["type"]` to decide between 404 and WebSocket close. But if `scope["type"]` is neither `http` nor `websocket` (e.g., `lifespan`), the method returns without sending anything—the connection hangs. | High | **Fixable** — add else clause or assertion |
| 12 | `Router.not_found()` L244-252 | Checks `"app" in scope` to decide between raising HTTPException and returning PlainTextResponse. This is a heuristic for "are we inside an outer app?" but is undocumented magic. | Medium | **Structural** (ASGI composition ambiguity) |
| 13 | `url_path_for()` generally | The `NoMatchFound` exception is used for control flow (try/except in Mount and Router). This is a performance concern and makes debugging harder—legitimate `NoMatchFound` from a typo look the same as expected misses. | Medium | **Fixable** — use sentinel return value |
| 14 | `Route.__init__()` L109-111 | `if methods is None: methods = ["GET"]` only applies when endpoint is a function. Class-based endpoints don't get default GET, which may surprise users. | Medium | **Fixable** — document or unify behavior |
| 15 | `Router.lifespan` handling | `lifespan_context` is set to `_DefaultLifespan` if None, but `_DefaultLifespan` is not defined in this file. If it's a class that does nothing, lifespan events may be silently ignored. | Unknown | **Unknown** — need to see `_DefaultLifespan` |
| 16 | **Predicted by meta-law**: `url_path_for()` with nested Mounts and parameter collisions | When a nested Mount's child route has a param that collides with the Mount's param, `url_path_for()` will generate incorrect URLs because `replace_params()` consumes params from a flat dict without knowing which level they belong to. | High | **Structural** (per conservation law) |

---

## Summary

The deepest finding is the **Flat Scope Conservation Law**: nested routing with flat dictionaries makes parameter namespace safety structurally impossible without breaking ASGI compatibility. The meta-law reveals that any "fix" creates a translation boundary, and bugs cluster at those boundaries—specifically in `url_path_for()` and nested Mount scenarios.

The 16 concrete issues range from trivial (naming shadowing) to structural (parameter collision semantics). The analysis predicts that `url_path_for()` with nested mounts is the highest-risk area—a falsifiable claim that can be tested by auditing issue trackers or running property-based tests.
