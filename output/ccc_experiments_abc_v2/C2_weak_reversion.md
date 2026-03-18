## Three Structural Mechanisms

### 1. Exception-Driven Delegation in URL Generation

`Mount.url_path_for` uses exception catching as control flow for delegation to child routes.

```python
for route in self.routes or []:
    try:
        url = route.url_path_for(remaining_name, **remaining_params)
        return URLPath(path=path_prefix.rstrip("/") + str(url), protocol=url.protocol)
    except NoMatchFound:
        pass
```

- **Input**: Route name with dotted namespace (e.g., `"admin:users:detail"`)
- **Output**: URL path or exception
- **Breaks if removed**: URL generation across mounted apps — each Mount would need explicit knowledge of its children's route names

The concealment: The `NoMatchFound` exception is the delegation protocol. Routes signal "not mine" by throwing, and parents catch to try siblings. This makes stack traces during debugging misleading — exceptions are expected, not exceptional. The name-matching logic (stripping prefix, checking `self.name + ":"`) creates a distributed namespace that has no central registry.

---

### 2. The Three-Phase Dispatch Decision Tree

`Router.app` implements a prioritized fallback chain: FULL match → PARTIAL match → slash redirect → default handler.

```python
# Phase 1: Find FULL match
for route in self.routes:
    if match is Match.FULL:
        return
    elif match is Match.PARTIAL and partial is None:
        partial = route

# Phase 2: Use PARTIAL if no FULL
if partial is not None:
    return

# Phase 3: Try slash redirect
if route_path.endswith("/") or not route_path.endswith("/"):
    # retry all routes with modified path

# Phase 4: Default handler
await self.default(...)
```

- **Input**: Request scope
- **Output**: Handler execution
- **Breaks if removed**: HTTP semantics — clients would get 404 for `/users/` when `/users` exists (or vice versa), and 404 for valid paths with wrong methods

The concealment: Each phase has different success criteria. Phase 1 terminates on first FULL. Phase 2 uses first-captured PARTIAL. Phase 3 re-routes by path mutation. The precedence rules are invisible — removing a route can change which partial is captured, changing error codes from 405 to 404 for unrelated methods.

---

### 3. Scope as Accumulator with Invisible Contracts

Routes and Router both write to `scope` without declaring what they expect to read.

```python
# Router writes:
scope["router"] = self

# Route writes:
child_scope = {"endpoint": self.endpoint, "path_params": path_params}

# Mount writes:
child_scope = {
    "path_params": path_params,
    "app_root_path": scope.get("app_root_path", root_path),
    "root_path": root_path + matched_path,
    "endpoint": self.app,
}
```

- **Input**: Original request scope
- **Output**: Mutated scope with 4+ new keys
- **Breaks if removed**: All downstream handlers — they read `scope["path_params"]` and `scope["endpoint"]` without any type declarations or null checks

The concealment: The contract is purely conventional. A handler that accesses `scope["path_params"]["id"]` works because routing put it there, but there's no declaration of this dependency. The `root_path` / `app_root_path` distinction (added only by Mount) creates a two-tier path context that handlers must know about implicitly.

---

## Conservation Law

**Routing Implicitness × Debuggability = constant**

Every mechanism that makes routing more automatic (partial matching, slash redirects, scope injection, exception-driven delegation) proportionally disperses control flow decisions across multiple locations:

- The PARTIAL match precedence is determined by route registration order, not explicit priority
- The slash redirect retries the entire route list with a modified scope
- The URL generation namespace is distributed across the Mount hierarchy
- The scope contract exists only in handler implementations that read it

This conservation is absolute: making routing "just work" for more cases always means the actual execution path is determined by invisible state and implicit precedence rules. A request that returns 405 vs 404 vs 301 has taken fundamentally different paths through the same code, but the decision points are distributed, not centralized.

The routing system trades explicit dispatch (visible if/else chains) for implicit dispatch (match precedence and scope mutation). You cannot add convenience without removing traceability.
