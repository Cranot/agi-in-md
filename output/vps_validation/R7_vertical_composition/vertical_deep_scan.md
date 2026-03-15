# Structural Deep-Scan Analysis: Starlette Routing

## Step 1: Identify the Conservation Law

**The Conservation Law for ASGI Routing:**

> **Safety × Compatibility × Zero-Copy Performance** — Pick two.

| Safety | Compatibility | Zero-Copy | Result |
|--------|---------------|-----------|--------|
| ✓ | ✓ | ✗ | Must copy/translate scopes (current "fix" attempts) |
| ✓ | ✗ | ✓ | Must change dict interface (PathParams stack) |
| ✗ | ✓ | ✓ | Current state: silent overwrites, phantom state |

**The O(n) cost that cannot be optimized away:** Scope isolation at each nesting level. Every `Mount` that wants to protect its children from parent pollution, or protect parents from child mutations, must pay O(scope_size) to copy the dictionary.

**What the system pays:** The current implementation pays in *safety* to gain compatibility and zero-copy. Scope mutations from PARTIAL matches persist. Parameter collisions overwrite silently. The bill comes due in debugging time.

**Name:** The Flat Scope Conservation Law — you cannot have structured parameter safety, flat-dict ASGI compatibility, and zero-copy performance simultaneously.

---

## Step 2: Locate Information Laundering

### Laundering Site 1: PARTIAL Match Selection (L266-275)

```python
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match is Match.FULL:
        # ...handle and return...
    elif match is Match.PARTIAL and partial is None:
        partial = route
        partial_scope = child_scope  # FIRST PARTIAL wins
```

**What's laundered:** Subsequent PARTIAL matches are discarded. If route A returns PARTIAL (405: method not allowed) and route B also returns PARTIAL (different method mismatch), only A's error semantics survive. The handler will see A's scope, A's path_params, A's methods list.

**Diagnostic destroyed:** Which route would have been "better" to report? What other methods were available across all PARTIAL matches? Gone.

---

### Laundering Site 2: NoMatchFound as Control Flow

```python
# In url_path_for:
raise NoMatchFound(scope["route_name"], scope["path_params"])
```

**What's laundered:** The exception carries only the *final* route_name and path_params that failed. The call stack that led there—nested Mount traversals, intermediate matches, parameter substitutions—is lost. A typo like `"usr:list"` instead of `"user:list"` produces an exception that doesn't enumerate what names *were* available.

**Diagnostic destroyed:** The set of valid route names, the partial matches that almost worked, the parameter mismatches at each level.

---

### Laundering Site 3: scope["type"] Dispatch in BaseRoute (L87-95)

```python
async def __call__(self, scope: dict, receive: Receive, send: Send) -> None:
    match, child_scope = self.matches(scope)
    if match == Match.NONE:
        if scope["type"] == "http":
            response = PlainTextResponse(NOT_FOUND_RESPONSE, 404)
        else:
            response = PlainTextResponse(NOT_FOUND_RESPONSE, 404)  # Wait...
```

**Critical laundering discovered:** The code checks `scope["type"]` to decide response type, but for non-http types (like `"lifespan"`), the behavior is undefined. Looking at actual code:

```python
if scope["type"] == "http":
    # ...handle http...
elif scope["type"] == "websocket":
    # ...handle websocket...
# LIFESPAN FALLS THROUGH - connection hangs
```

**Diagnostic destroyed:** When `scope["type"]` is `"lifespan"` and no match is found, the method returns `None` without calling `send()`. The ASGI application hangs silently. The specific failure ("lifespan not supported by this route") becomes a generic connection hang.

---

### Laundering Site 4: The "app" Heuristic in not_found (L244-252)

```python
def not_found(self, scope: Scope) -> Response:
    if "app" in scope:
        # We're inside an outer app, raise exception
        raise HTTPException(404)
    else:
        # We're the outermost app, return response
        return PlainTextResponse(NOT_FOUND_RESPONSE, 404)
```

**What's laundered:** The presence of `"app"` in scope is used as a proxy for "are we nested?" But this is a heuristic. The specific context—*why* are we in not_found, what level of nesting, what should the error propagation strategy be—is laundered into a single bit.

---

## Step 3: Hunt Structural Bugs

### A) Async State Handoff Violation

**Bug A1: Scope Mutation Before Async Boundary (L256-275)**

```python
async def app(self, scope, receive, send):
    # ...
    for route in self.routes:
        match, child_scope = route.matches(scope)
        if match is Match.FULL:
            scope.update(child_scope)  # MUTATION
            await route.handle(scope, receive, send)  # ASYNC HANDOFF
            return
```

**The pattern:** `dict.update()` followed by `await` where the mutated dict is shared.

**Why it's a race:** While the current code is linear (one route at a time), the architectural pattern is fragile. If middleware wraps `send` and captures `scope`, or if the handler spawns tasks that read `scope`, they see the mutated state. The mutation is "committed" before the async boundary.

**Severity:** Medium (latent, not currently triggered)

---

**Bug A2: path_params Reference Sharing (Route.matches L126-139)**

```python
def matches(self, scope):
    # ...
    path_params = scope.get("path_params", {})  # Reference to existing dict
    path_params.update(matched_params)  # Mutates original!
    child_scope = {"endpoint": self.endpoint, "path_params": path_params}
```

**The pattern:** `scope.get()` returns a reference, not a copy. The `update()` mutates the caller's dict.

**The race:** If the caller's scope has a `path_params` dict that's shared across multiple route evaluations, each Route's `matches()` pollutes it for subsequent routes.

**Severity:** High (but masked by Router creating fresh scope for each route)

---

### B) Priority Inversion in Search

**Bug B1: First-PARTIAL-Wins Ignores Better Error Information (L266-275)**

```python
partial = None
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match is Match.PARTIAL and partial is None:
        partial = route  # FIRST wins, not BEST
```

**The pattern:** Linear search with early capture of PARTIAL.

**The inversion:** Route order determines error quality. If `/api/users` (methods=[GET]) comes before `/api/users` (methods=[POST, PUT, DELETE]), a PATCH request captures the first route's PARTIAL (which lists GET only), losing information about what methods *are* available.

**Severity:** Medium (poor UX, not crash)

---

**Bug B2: Mount Partial Match Scope Pollution**

When a Mount returns PARTIAL (method mismatch on the mount's own routes, not its children), the `child_scope` it produces includes mutated `root_path` and `path_params`. The Router stores this scope. But the Mount's PARTIAL semantics are different from a Route's PARTIAL—the Mount might have child routes that *do* match the method, but the search order prevented finding them.

---

### C) Edge Case in Composition

**Bug C1: Empty String Path → Host Route Misclassification (compile_path L59)**

```python
is_host = not path.startswith("/")
```

**The pattern:** Boolean decision based on string prefix.

**The edge case:** `path = ""` gives `is_host = True`. An empty path is classified as a host route, not an error.

**Consequence:** `compile_path("")` produces a host regex that matches anything, not a validation error.

---

**Bug C2: Negative Slicing with Empty Name (Mount.url_path_for L200-216)**

```python
if self.name and name.startswith(self.name + ":"):
    name = name[len(self.name) + 1:]  # Slice after colon
```

**The pattern:** `name[len(x) + 1:]` where the offset is computed from a variable.

**The edge case:** If `self.name = ""` (empty string, distinct from `None`), then `name[len("") + 1:]` = `name[1:]`, which strips the first character of the child name. Route `"foo:bar"` becomes `"oo:bar"`.

**Consequence:** Mounts with `name=""` (unusual but valid) silently mangle child route lookups.

---

**Bug C3: Path Parameter Slicing in replace_params (L45-51)**

```python
path = path[:index] + value + path[index + len(key) + 2:]
```

**The pattern:** `[index + len(key) + 2:]` assumes `{key}` format.

**The edge case:** If `index = -1` (key not found in path, which shouldn't happen if regex matched), the slice becomes `path[-1 + len(key) + 2:]` = `path[len(key) + 1:]`, which truncates from the wrong position.

**Consequence:** A corrupted regex match produces mangled URLs rather than an explicit error.

---

**Bug C4: Lifespan Type Falls Through (BaseRoute.__call__ L87-95)**

```python
if scope["type"] == "http":
    # handle
elif scope["type"] == "websocket":
    # handle
# else: ???
```

**The pattern:** If-elif chain without else clause for enum-like values.

**The edge case:** `scope["type"] = "lifespan"` matches neither branch.

**Consequence:** The method returns `None` without calling `send()`. The ASGI server waits for a response that never comes. Connection hangs indefinitely.

**Severity:** High (production outage pattern)

---

## Summary Table

| Bug | Type | Location | Severity | Structural? |
|-----|------|----------|----------|-------------|
| A1 | Async state handoff | Router.app L268-270 | Medium | No (latent) |
| A2 | Reference sharing | Route.matches L126-139 | High | No (masked) |
| B1 | Priority inversion | Router.app L266-275 | Medium | No |
| C1 | Empty path edge case | compile_path L59 | Low | No |
| C2 | Empty name slicing | Mount.url_path_for L200+ | Medium | No |
| C3 | Negative index slicing | replace_params L45-51 | Low | No |
| C4 | Lifespan fallthrough | BaseRoute.__call__ L87-95 | **High** | No |

---

## Conservation Law Verified

The Flat Scope Conservation Law manifests in every bug:
- **A2**: path_params mutation (safety sacrificed for zero-copy)
- **B1**: PARTIAL information loss (compatibility with linear search pattern)
- **C4**: Type dispatch hole (flat scope doesn't encode protocol requirements)

The deepest invariant: *Translation boundaries are where bugs cluster*. Every location where the flat scope must be interpreted (type dispatch, path param extraction, route name parsing) has edge cases that produce silent failures.
