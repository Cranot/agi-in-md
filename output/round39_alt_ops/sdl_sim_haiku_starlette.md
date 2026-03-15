I'll execute this temporal fragility analysis on the Starlette routing code. Let me work through each step systematically.

## Step 1: New Developer Cycle

**Assumption they'll violate:**
The `compile_path` function contains strict parameter validation that developers will likely misuse. New devs will assume they can create routes with parameter names like `user-id` or `api-key`, but the PARAM_REGEX only allows `[a-zA-Z_][a-zA-Z0-9_]*` patterns. They'll violate the naming convention assumption and either get cryptic regex errors or have parameters silently ignored.

**What breaks silently:**
In the `Mount` class's `matches` method, the path extraction logic silently consumes the entire matched path when `/{path:path}` is used. A dev might create nested mounts expecting some path segments to remain for inner routers, but the regex `self.path_regex.match(route_path)` in Mount always consumes the full remaining path in the `path` parameter. This means nested routing configurations will appear to work but silently drop routing decisions from inner routers.

**Copy-paste trap:**
The `replace_params` function looks like a simple template replacement utility that devs might copy for other URL-building purposes. However, it contains critical hidden constraints: it only replaces parameters that exist in the original path template, it requires exact parameter name matching including braces, and it modifies the input path_params dictionary in place. Devs will copy this expecting a generic URL parameter replacement but get unexpected behavior when parameters don't match exactly or when they try to reuse the path_params dict afterward.

## Step 2: Knowledge Loss Cycle

**Cargo cult decisions:**
1. The `Match.NONE/PARTIAL/FULL` enum system - developers will preserve the three-tier matching approach without understanding that `PARTIAL` matching is actually a performance optimization that allows fallback to 404 handlers when method doesn't match. They'll add new match types or modify the enum thinking it's just state tracking.

2. The double-scope pattern in `__call__` methods - every route implements the same pattern of calling `matches()`, updating scope, then calling `handle()`. Without the original docs explaining this is for ASGI protocol compliance and middleware chaining, devs will try to optimize it or change the order.

3. The `redirect_slashes` parameter in Router - they'll preserve this boolean flag without understanding it's a legacy holdover from early web standards where trailing slashes mattered for resource discovery. They'll add complex logic around it when it's just a historical artifact.

**Unfixable problems:**
The `compile_path` function contains hardcoded assumptions about URL parameter conversion types in `CONVERTOR_TYPES` (referenced but not shown). When new conversion types are needed, the regex compilation logic will break because the original team understood the intimate relationship between convertor regex patterns and their conversion methods. New devs won't be able to add new convertor types without deep knowledge of how regex patterns and URL parameter conversion interact.

**Temporary code that becomes permanent:**
The deprecated lifespan handling in Router with its conditional branching between async generators, generators, and modern async context managers. The deprecation warnings suggest this was meant to be temporary, but the complexity means it will likely outlive the actual deprecation as teams continuously add new lifespan scenarios without touching the deprecated paths.

## Step 3: Calcification Map

**Internal detail external consumers depend on:**
The `param_convertors` dictionary in compiled paths is internal implementation detail that became external API. The `url_path_for` methods rely on exact parameter name matching against this dict, and external teams have likely started constructing URL paths by manually manipulating these dictionaries. The internal representation has escaped and become part of the public API.

**Performance assumption baked in:**
The regex-based path matching in `compile_path` assumes all path compilation happens at startup, not at request time. The architecture is built around expensive regex compilation at Router initialization with fast matching at runtime. This makes it impossible to add dynamic route patterns without breaking the performance contract.

**Error handling path that's actually the happy path:**
In `BaseRoute.__call__`, the `Match.NONE` path returns a 404 response immediately, which seems like error handling. But in production, this is actually the happy path for middleware and static file handlers that should process requests even when no route matches. The error handling logic became the primary execution path for legitimate non-routing traffic.

**Conservation Law: A x B = constant**

The routing system conserves **Predictability × Flexibility** = constant. Initially, the system maximizes flexibility with parameterized routes and mounting, but this introduces complexity in parameter validation and scope management. As the code ages, teams add more validation and constraints to maintain predictability, which gradually reduces the flexibility that was originally designed in. The trade-off appears as either:
- More rigid route definitions (less flexibility) for easier debugging (more predictability)
- Or more complex dynamic routing (more flexibility) with harder-to-diagnose routing bugs (less predictability)

---

## Summary of Temporal Fragility

The Starlette routing system shows fragility in three key dimensions:

1. **Parameter handling rigidity** - The strict parameter naming and validation will create friction as teams try to use more complex URL patterns
2. **Scope management complexity** - The double-scope pattern and path parameter accumulation becomes harder to maintain as the routing depth increases
3. **Performance vs. flexibility tension** - The regex-based optimization creates architectural constraints that make dynamic routing additions increasingly expensive

The most dangerous fragility point is the internal `param_convertors` dictionary escaping into public API - this creates a dependency on implementation details that will make future refactoring extremely difficult without breaking changes.
