# Starlette Routing Analysis: Future-State Simulation

## Step 1: Five Maintenance Cycles

### Cycle 1: New Requirement Forces Structural Change
**Requirement**: Add WebSocket-specific middleware that needs access to route path parameters during WebSocket upgrade handshake.

**Affected Function**: `Mount.matches()` 
**Failure Mode**: The current `Mount.matches()` method creates a `child_scope` with path parameters but doesn't differentiate between WebSocket and HTTP path parameter handling. When adding WebSocket-specific middleware that needs access to path parameters during the upgrade handshake, the path parameters from `route_path` aren't properly preserved in the WebSocket context.

**Specific Issue**: The `matched_params` are only extracted for HTTP routes, while WebSocket routes at `Mount` level don't get the same parameter extraction, causing WebSocket middleware to fail when trying to access path parameters.

### Cycle 2: Bug Report Reveals Hidden Assumption
**Bug**: URL generation fails when nested Mount routes have optional trailing slashes and the `url_path_for()` method is called with a route name that crosses multiple Mount boundaries.

**Affected Function**: `Mount.url_path_for()`
**Failure Mode**: The `url_path_for()` method assumes that route names are hierarchical (using `:` separator) but doesn't properly handle cases where a nested route might have a different name scheme than expected. When a developer tries to generate a URL for a route nested under multiple Mounts with optional trailing slashes, the method fails to correctly reconstruct the path.

**Specific Issue**: In `Mount.url_path_for()`, the condition `name.startswith(self.name + ":")` assumes hierarchical naming, but when dealing with optional trailing slashes and nested Mounts, this assumption breaks because the actual route name might not follow the expected hierarchy.

### Cycle 3: Performance Optimization Breaks Invariant
**Optimization**: Add route caching to improve performance for frequently accessed routes.

**Affected Function**: `Router.__call__()`
**Failure Mode**: When adding a route caching layer, developers modify the `__call__` method to cache match results. However, this breaks the invariant where route matching must be stateless and respect dynamic changes to routes (like middleware being added/removed at runtime).

**Specific Issue**: The cached route matches don't account for middleware changes or dynamic route modifications. When middleware is added or removed after routes are cached, the cached matches become invalid, leading to incorrect handling of requests.

### Cycle 4: New Team Member Misreads Design Intent
**Misinterpretation**: A new developer assumes the `redirect_slashes` parameter should apply to WebSocket routes as well.

**Affected Function**: `Router.__call__()`
**Failure Mode**: The new developer modifies the redirect logic to also handle WebSocket routes by adding redirect responses for WebSocket requests. This breaks the WebSocket protocol, as WebSocket connections require a specific upgrade handshake and cannot be redirected.

**Specific Issue**: The WebSocket upgrade handshake is stateful and requires specific headers. Adding redirects for WebSocket routes breaks the handshake protocol, causing WebSocket connections to fail with 302 redirects instead of proper WebSocket upgrades.

### Cycle 5: Original Author Leaves - Undocumented Knowledge Lost
**Loss**: Original developer who wrote the complex path parameter conversion logic leaves the project.

**Affected Function**: `compile_path()` and `replace_params()`
**Failure Mode**: The complex regex-based path parameter extraction and conversion logic becomes opaque to new maintainers. When a bug report comes in about parameter conversion failing for edge cases, the new team struggles to understand the nuances of the regex patterns and conversion logic.

**Specific Issue**: The `compile_path()` function uses a complex regex with multiple capture groups and conversion logic that's not well-documented. When developers need to add new parameter types or fix edge cases in path matching, they can't easily understand the existing implementation without deep knowledge of the original author's design decisions.

## Step 2: Map the Calcification

### Most Untouchable Parts:
1. **`compile_path()` function**: This becomes the core "fossil" of the system. Its complex regex logic is critical to route matching but is extremely difficult to modify without breaking existing behavior.
2. **`BaseRoute.__call__()` method**: The central dispatch logic becomes untouchable as it's used by all route types. Any change risks breaking the fundamental request handling flow.
3. **`replace_params()` function**: The parameter replacement logic becomes calcified as it's relied upon by URL generation across the entire codebase.

### Fastest Growing Complexity:
- The `Mount.url_path_for()` method grows the fastest in complexity, accumulating special cases for nested routing, optional parameters, and hierarchical naming.

### Cascade Effect:
The Cycle 2 change (bug fix for nested route URL generation) forces the most changes elsewhere. The `Mount.url_path_for()` method becomes a central point that requires coordination with:
- `Route.url_path_for()` (for consistency)
- `Router.url_path_for()` (for the fallback behavior)
- `replace_params()` (for parameter handling)
- `compile_path()` (for path format expectations)

### Calcification Pattern:
**The "String Format Lock-in" Pattern** - Code that relies on string formatting and regex patterns becomes fossilized because:
1. It has implicit contracts with many other parts of the system
2. Changes require updating multiple related components in lockstep
3. The regex logic becomes impossible to reason about over time
4. String-based APIs create fragile dependencies across modules

## Step 3: Derive the Conservation Law

### Temporal Property Conserved:
**The Route Matching Interface** - Despite all maintenance pressure, the `matches(scope)` method signature and its return value (`Match` enum with child_scope dict) remains unchanged across all cycles.

### Structural Invariant:
**The "Scope-Mounting" Pattern** - The pattern of updating the ASGI scope with child scope information cannot change. This invariant maintains the "thread" of request context through nested route handling.

### X × Y = Constant Law:
**Match Complexity × Route Flexibility = Constant**

Where:
- **Match Complexity**: The computational cost of route matching (regex complexity, parameter extraction)
- **Route Flexibility**: The ability to define routes with complex patterns, parameters, and nesting

This conservation law reveals that the system's apparent architecture (a simple router class) actually implements a complex regex-based pattern matching system. The resistance to change comes from the fundamental tradeoff: to maintain high route flexibility, the match complexity must remain high, making the system resistant to modifications that would break this balance.

The system appears to have a simple public API (Router with routes), but its actual architecture requires maintaining complex string processing and state management logic that cannot be easily altered without compromising its core functionality.
