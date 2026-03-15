# Structural Deep-Scan Analysis: Starlette Routing

## Step 1: Conservation Law

**Conserved Quantity: "Route Specificity × Dispatch Speed × Composition Depth"**

The system can optimize for any two, but never all three:

| Choose Two | Sacrifice |
|------------|-----------|
| Specific matching + Fast dispatch | Shallow route trees (no deep mounts) |
| Fast dispatch + Deep composition | Ambiguous matches (first-wins semantics) |
| Deep composition + Specific matching | O(n×depth) dispatch cost per request |

**The Unavoidable O(n) Cost:** `Router.app()` performs linear search through `self.routes`. Every request must potentially check every route until a `Match.FULL` is found. This cannot be optimized away because:
- Routes can overlap in patterns (`/users` vs `/users/{id}`)
- PARTIAL matches must be remembered for 405 Method Not Allowed responses
- The order of route registration is semantically meaningful (first match wins)

**The Flexibility Payment:** To gain middleware stacking (`self.app = cls(self.app, ...)`) and nested mounts, the system pays in call stack depth and scope mutation complexity. Each mount layer adds one stack frame and one `scope.update()`.

---

## Step 2: Information Laundering

### 2.1 `NoMatchFound` Exception Stripping

**Location:** `Router.url_path_for()` lines 328-333

```python
def url_path_for(self, name, /, **path_params):
    for route in self.routes:
        try:
            return route.url_path_for(name, **path_params)
        except NoMatchFound:
            pass  # <-- INFORMATION DESTROYED HERE
    raise NoMatchFound(name, path_params)
```

**What's Lost:** When 10 routes are checked and all fail, only the final exception surfaces. The caller cannot know:
- Which routes were candidates
- Whether the name matched but params were wrong
- Whether params matched but name was wrong

**Trace:** `Mount.url_path_for()` compounds this by catching and suppressing `NoMatchFound` for each child route in its loop.

### 2.2 Silent Parameter Skipping

**Location:** `replace_params()` lines 44-51

```python
def replace_params(path, param_convertors, path_params):
    for key, value in list(path_params.items()):
        if "{" + key + "}" in path:  # <-- SILENT SKIP if not found
            ...
            path_params.pop(key)
    return path, path_params  # remaining params silently returned
```

**What's Lost:** A typo in a parameter name (`user_id` vs `userid`) results in the parameter being silently left in `remaining_params` rather than raising an error. The caller must check the return value to detect problems.

### 2.3 Scope Mutation Without Provenance

**Location:** `BaseRoute.__call__()` line 113, `Router.app()` lines 376, 381

```python
scope.update(child_scope)  # mutation in-place
await self.handle(scope, receive, send)
```

**What's Lost:** After dispatch, `scope` contains merged data from all matched routes, but no record of which route added which keys. Debugging "where did this path_params value come from?" requires tracing the entire match chain.

---

## Step 3: Structural Bugs

### 3.A Async State Handoff Violation: Caller's Dict Mutation

**Location:** `Mount.url_path_for()` lines 279-282

```python
path_kwarg = path_params.get("path")
path_params["path"] = ""  # <-- MUTATES CALLER'S DICT
path_prefix, remaining_params = replace_params(...)
if path_kwarg is not None:
    remaining_params["path"] = path_kwarg
```

**Pattern:** Direct mutation of a passed-in dictionary before async operations.

**The Bug:** If caller does:
```python
params = {"path": "/users", "id": "1"}
url = mount.url_path_for("admin:user", **params)
# params["path"] is now "" -- caller's data corrupted
```

**Impact:** Subsequent calls using the same `params` dict will fail mysteriously because `path` was clobbered.

**Fix:** Should copy: `path_params = dict(path_params)` before mutation.

---

### 3.B Priority Inversion: First Partial Wins

**Location:** `Router.app()` lines 373-383

```python
partial = None
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match is Match.FULL:
        scope.update(child_scope)
        await route.handle(scope, receive, send)
        return
    elif match is Match.PARTIAL and partial is None:  # <-- FIRST WINS
        partial = route
        partial_scope = child_scope

if partial is not None:
    scope.update(partial_scope)
    await partial.handle(scope, receive, send)  # <-- MAY BE SUBOPTIMAL
```

**Pattern:** Early-return caching without comparison.

**The Bug:** Given routes:
```python
routes = [
    Route("/api", endpoint=a, methods=["POST"]),  # index 0
    Route("/api", endpoint=b, methods=["GET"]),   # index 1
]
```

A `GET /api` request matches PARTIAL on route 0 (path matches, method doesn't), then FULL on route 1. But if route 0's methods were `["GET"]` and route 1's were also `["GET"]`, both would be FULL matches and route 0 wins—correct.

The problem: PARTIAL matches aren't compared for "closeness." If route 0 has `methods=["POST", "PUT"]` and route 1 has `methods=["GET"]`, and request is `DELETE /api`, both are PARTIAL. Route 0 wins arbitrarily, returning 405 with `Allow: POST, PUT` when perhaps route 1's `Allow: GET` would be more useful.

**Impact:** 405 responses may show misleading `Allow` headers.

---

### 3.C Edge Case in Composition: Empty String Slicing

**Location:** `Mount.matches()` lines 261-262

```python
remaining_path = "/" + matched_params.pop("path")
matched_path = route_path[: -len(remaining_path)]
```

**Pattern:** `[:-len(x)]` where x can be minimal length.

**The Bug:** When `path` parameter is empty string:
- `remaining_path = "/" + "" = "/"`
- `matched_path = route_path[:-1]`

For a mount at path `""` matching request `/`, with path regex `^/(?P<path>.*)$`:
- `route_path = "/"`
- `path` group = `""`
- `remaining_path = "/"`
- `matched_path = "/"[:-1] = ""` ✓ Correct

But for mount at `/api` matching `/api`, with regex `^/api/(?P<path>.*)$`:
- The regex requires `/api/` with trailing slash
- Matching `/api` (no slash) fails at regex level—no issue

**Real edge case:** What if `route_path` is somehow shorter than `remaining_path`?

```python
route_path = "/a"
remaining_path = "/xy"  # len 3
matched_path = "/a"[:-3] = ""  # Python handles this gracefully
```

**Verdict:** Python's slice semantics save this from crashing, but the logic assumes `remaining_path` is always a suffix of `route_path`. If the path convertor returned something longer than the actual suffix, slicing would produce wrong results.

---

## Summary

| Category | Finding | Severity |
|----------|---------|----------|
| **Conservation** | Route specificity × Dispatch speed × Composition depth - pick two | Architectural |
| **Laundering** | `NoMatchFound` loses all context about which routes were tried | Debug pain |
| **Laundering** | `replace_params` silently skips unknown parameters | Silent failure |
| **Bug A** | `Mount.url_path_for` mutates caller's `path_params` dict | Data corruption |
| **Bug B** | First PARTIAL match wins, not "best" PARTIAL match | Wrong 405 headers |
| **Bug C** | Negative slicing assumes suffix relationship | Guarded by regex |
