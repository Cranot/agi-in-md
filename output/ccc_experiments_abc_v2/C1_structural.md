## Three Structural Mechanisms

### 1. Scope Mutation as Hidden Data Flow

The `matches()` methods don't just return match status — they silently inject data into the request's scope dictionary.

- **Input**: Original scope dict + route match result
- **Output**: Mutated scope containing `path_params`, `endpoint`, `root_path`, `app_root_path`
- **Breaks if removed**: All downstream handlers — they depend on `scope["path_params"]` and `scope["endpoint"]` existing, but the dependency is invisible. You can't trace where these values originate; they materialize during routing.

The concealment: The `scope.update(child_scope)` at lines 97 and 160 makes routing a hidden write operation masquerading as a read operation.

---

### 2. Partial Match as Ambiguity Reservation

`Match.PARTIAL` exists to defer rejection. When a path matches but the HTTP method doesn't, the Router stores this as a fallback (lines 265-268) and only uses it if no FULL match succeeds.

- **Input**: Route that matches path regex but fails method constraint
- **Output**: Deferred handling that produces HTTP 405 (Method Not Allowed) instead of 404
- **Breaks if removed**: HTTP semantics — clients would receive 404 for `/users` with POST when only GET is registered, making the API appear to not exist rather than exist-but-forbid-this-method

The concealment: The Router.app method's `partial` variable is an invisible state accumulator. The first PARTIAL match wins — but this precedence rule is nowhere documented, and later partial matches are silently discarded.

---

### 3. Mount's Synthetic Path Parameter

Every Mount compiles its path as `self.path + "/{path:path}"` (line 144). This synthetic `path` parameter captures the remainder for delegation to sub-apps.

- **Input**: Mount path prefix (e.g., `"/api"`)
- **Output**: Regex that matches `/api/anything` and extracts `anything` as a parameter
- **Breaks if removed**: Recursive routing — sub-apps would receive the full original path with prefix, requiring every sub-app to know its mount point and strip it manually

The concealment: The `path` parameter is injected into scope at line 156 (`remaining_path = "/" + matched_params.pop("path")`), then the mount point is stripped via `root_path` modification (line 160). The sub-app receives a rewritten scope as if it were mounted at root. This creates the illusion of independent apps while binding them to their mount context.

---

## Conservation Law

**Automatic Resolution × Control Flow Visibility = constant**

Every mechanism that resolves requests automatically (partial matching, slash redirects, scope injection) proportionally obscures the actual control flow path:

- Scope mutation makes data dependencies invisible
- Partial match precedence makes handler selection non-deterministic from reading route definitions alone  
- Synthetic parameters hide delegation boundaries

The routing system trades explicit control for implicit convenience at every layer. You cannot increase routing "magic" without decreasing the ability to trace why a request reached a particular handler.

This conservation is absolute: making routing more automatic always makes debugging harder, because the control flow decisions migrate from visible code (explicit if/else) to invisible state (scope mutation and precedence rules).
