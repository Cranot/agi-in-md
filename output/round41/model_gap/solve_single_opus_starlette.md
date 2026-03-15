# Starlette ASGI Routing: A Structural Analysis of Fundamental Tradeoffs

## I. The Three Properties and Their Incompatibility

**Property 1: Deterministic Route Resolution**
The ideal routing system provides unambiguous mapping from request paths to endpoints, independent of registration order.

**Property 2: Composable Nested Routing via Mount**
`Mount("/api", routes=[...])` allows modular application structure where sub-routers can be developed independently.

**Property 3: Flexible Parameter Matching**
Path converters like `{id:int}`, method constraints, and regex patterns enable expressive route definitions.

### The Impossibility Proof

```python
# Location: Mount.__init__
self.path_regex, self.path_format, self.param_convertors = compile_path(
    self.path + "/{path:path}"
)
```

This `{path:path}` capture is **fundamentally greedy**—it matches *any* remaining path. Consider:

```python
routes = [
    Route("/api/docs", endpoint=docs),
    Mount("/api/{path:path}", routes=[
        Route("/items", endpoint=items),  # This will never match!
    ])
]
```

The Mount's greedy capture creates an **ambiguity zone**: nested routes are shadowed by the mount point itself. The system cannot simultaneously guarantee (1) unambiguous resolution AND (2) arbitrary nesting depth.

Furthermore, in `Route.matches()`:

```python
# Parameters extracted and converted BEFORE method validation
matched_params[key] = self.param_convertors[key].convert(value)
# ... later ...
if self.methods and scope["method"] not in self.methods:
    return Match.PARTIAL, child_scope  # Partial match after conversion work
```

This creates PARTIAL matches where the path succeeds but method fails, introducing registration-order dependency.

**Conservation Law:**
```
ROUTING SPECIFICITY × COMPOSITION DEPTH = CONSTANT
```

As Mount nesting increases (composition depth ↑), the system's ability to make globally optimal routing decisions decreases (specificity ↓).

---

## II. Engineering Improvements That Recreate the Problem

### Improvement 1: Pre-sort Routes by Specificity

**Proposal:** Rank routes by specificity to make matching order-independent.

**What defines specificity?** We need heuristics for:
- `/users/{id:int}` (1 param, typed)
- `/posts/{slug}` (1 param, untyped)
- `/about` (0 params, literal)
- `/orgs/{org}/teams/{team}/projects/{project}` (3 params)

**Ranking algorithm:**
```python
specificity_score = (
    num_literal_segments * 100 +
    num_typed_params * 10 +
    num_untyped_params * 1
)
```

**New facet revealed:** Edge cases explode:
- `/api/{version:v1|v2}/users` — what's the score?
- `/users/{id:int}` vs `/users/admin` — literal might come *after* param
- `{host}` host-based routing mixes with path routing

**Result:** The specificity calculation subsystem becomes a complex source of bugs, recreating the problem at a meta-level. We've traded routing ambiguity for scoring ambiguity.

### Improvement 2: Pre-compile All Routes into Single Unified Trie

**Proposal:** Flatten the entire route hierarchy into one optimized structure.

**The deeper recreation:** Mount composition requires dynamic scope manipulation:

```python
# In Mount.matches()
child_scope = {
    "root_path": root_path + matched_path,  # Dynamic concatenation!
    "path_params": path_params,             # Inheritance chain
    "endpoint": self.app,
}
```

A monolithic compiled structure cannot express this **modular isolation** without losing the ability to:
- Update `root_path` incrementally
- Inherit/override path parameters per-mount
- Maintain independent route namespaces

**Result:** Performance improved, but **composability sacrificed**. You can no longer plug in a mount point as a black box—it must be aware of the global routing structure.

---

## III. The Conservation Law Examined

The law `ROUTING SPECIFICITY × COMPOSITION DEPTH = CONSTANT` treats routing as a pure function:
```
f(path, method) → endpoint
```

**What this conceals:** ASGI scope is **mutable state** passed downward:

```python
# In Router.__call__, then Route.matches(), then Mount.matches()
scope.update(child_scope)  # Mutates shared dictionary!
```

This enables **parameter inheritance across compositional boundaries**:

```python
# Scope after matching /orgs/{org_id}/projects/{project_id}
scope['path_params'] = {'org_id': '123', 'project_id': '456'}
# Inner route inherits BOTH params without declaring them
```

**Feature vs. Bug:**
- ✓ **Feature:** `/orgs/{org_id}/projects/{project_id}/tasks/{task_id}` — shared context propagates naturally
- ✗ **Bug:** Parent and child routes use same param name:

```python
Mount("/users/{user_id}", routes=[
    Route("/posts/{user_id}", ...)  # Shadows parent param!
])
```

The conservation law cannot predict when this inheritance is intentional (feature) or accidental (bug). The mutable scope threading **enables** the composition depth that the law quantifies.

---

## IV. Concrete Defects Harvested

### (1) **MEDIUM — Boundary-Unaware Root Path Construction**
```python
# Location: Mount.matches()
matched_path = route_path[: -len(remaining_path)]  # Slices by string length!
```
**Defect:** When `remaining_path` contains segments that appear in `route_path`, slicing by length produces incorrect boundaries.

**Counterexample:**
```python
# route_path = "/api/users/posts"
# remaining_path = "/posts"  # matched by {path:path}
# matched_path = "/api/users/posts"[: -6] = "/api/users" 
# But what if route_path = "/api/posts/posts"?
# matched_path becomes "/api/posts/posts"[: -6] = "/api/posts"
# INCORRECT: should be "/api/posts/posts" - "/posts" (need boundary awareness)
```

### (2) **LOW — Redundant Route Matching in Redirect**
```python
# Location: Router.app(), redirect_slashes block
for route in self.routes:  # First full matching
    match, child_scope = route.matches(scope)
    # ... then later ...
    for route in self.routes:  # Second full matching for redirect check!
        match, child_scope = route.matches(redirect_scope)
```
**Defect:** Performs full route matching twice when slash redirect is needed. Cache the match results from the first pass.

### (3) **LOW — Pre-Validation Parameter Conversion**
```python
# Location: Route.matches()
for key, value in matched_params.items():
    matched_params[key] = self.param_convertors[key].convert(value)
# ... only THEN check method:
if self.methods and scope["method"] not in self.methods:
    return Match.PARTIAL, child_scope
```
**Defect:** Wasteful conversion for requests that will fail method validation. For `{id:uuid}` with expensive parsing, this is pure overhead for POST requests to GET-only routes.

### (4) **HIGH — Exception Pollution in url_path_for**
```python
# Location: Mount.url_path_for()
path_params["path"] = ""  # MUTATION
path_prefix, remaining_params = replace_params(...)
if path_kwarg is not None:
    remaining_params["path"] = path_kwarg  # Restore only if no exception
for route in self.routes or []:
    try:
        url = route.url_path_for(remaining_name, **remaining_params)
        return URLPath(...)
    except NoMatchFound:
        pass  # But path_params is still corrupted!
raise NoMatchFound(name, path_params)  # Reports mutated state
```
**Defect:** If inner route raises `NoMatchFound` after `path_params["path"] = ""`, the exception handler reports corrupted state. Should use try-finally or local copy.

### (5) **MEDIUM — NoMatchContains Partial State**
```python
# Location: NoMatchFound.__init__()
params = ", ".join(list(path_params.keys()))
super().__init__(f'No route exists for name "{name}" and params "{params}".')
```
**Defect:** If a parent route partially matches but child fails, `path_params` contains consumed parent parameters. Error message shows partial consumption that's not user-actionable.

### (6) **MEDIUM — Mutable Scope Sharing Enables Shadowing**
```python
# Location: Both Route.matches() and Mount.matches()
path_params = dict(scope.get("path_params", {}))  # Inherits parent
path_params.update(matched_params)  # Adds own params
```
**Defect:** When parent and child use same param name, child **silently shadows** parent value. No warning, no detection. The hierarchical design enables this by sharing mutable state.

### (7) **LOW — Inconsistent Error Handling**
```python
# Location: Router.not_found()
if "app" in scope:
    raise HTTPException(status_code=404)  # Exception
else:
    response = PlainTextResponse("Not Found", status_code=404)  # Response
    await response(scope, receive, send)
```
**Defect:** Error handling strategy depends on `scope['app']` presence, which is inconsistent based on how Router was called. Makes error handling unpredictable.

---

## V. Synthesis: The Fundamental Tradeoff

Starlette's routing **sacrifices global optimality for modularity**. This is not an accident but a **structurally enforced constraint** of the ASGI scope model:

### The ASGI Scope Dilemma

ASGI scopes are **mutable dictionaries** passed through a call chain. Each layer (`Router` → `Mount` → `Route`) mutates `scope["path_params"]` and `scope["root_path"]`. This design:

1. **Enables compositional depth:** Each mount point can add context without knowing parent structure
2. **Prevents global compilation:** You can't flatten the trie because scope mutations depend on *dynamic call order*, not static structure

### The Conservation Law in Practice

```
GLOBAL ROUTING KNOWLEDGE × MODULAR ISOLATION = CONSTANT
```

- **High global knowledge** (pre-compiled trie): Can optimize globally but loses modularity
- **High modular isolation** (current design): Each mount is a black box, but registration order matters

### The Structural Tradeoff Space

| Dimension | Current Design | Alternative | Cost |
|-----------|---------------|-------------|------|
| Match order | Registration-dependent | Specificity-sorted | Complex ranking bugs |
| Scope mutation | Hierarchical | Immutable | Lost parameter inheritance |
| Compilation | Per-mount | Global | Lost modularity |
| Error handling | Response-or-exception | Consistent | Breaking change |

Starlette chose the **composability** quadrant. The bugs we identified are not defects to be fixed, but the **necessary cost** of maintaining modular isolation in a mutable-scope architecture. Any "fix" that preserves global optimization while maintaining Mount's black-box semantics violates the conservation law.

**The final insight:** The ASGI scope model itself—with its mutable `path_params` dictionary—is the root cause. To have both global optimality AND composability, you'd need a **structural type system** for scope mutations (like Rust's ownership), but Python's dynamic typing makes this infeasible at framework scale.
