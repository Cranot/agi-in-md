I'll execute the excavation protocol layer by layer to analyze the Starlette routing code.

## Layer 1 — Surface: What's visible at first glance

The public API consists of:
- **Route class**: Maps HTTP paths to endpoints with methods and middleware
- **Mount class**: Routes under a path prefix to a sub-application/router
- **Router class**: Central dispatcher that manages a collection of routes
- **NoMatchFound exception**: Raised when URL generation fails
- **Match enum**: Indicates route match quality (NONE/PARTIAL/FULL)
- **compile_path function**: Compiles path patterns to regex converters
- **replace_params function**: Builds URL paths from parameters

Key features:
- ASGI compliance with `async def __call__` methods
- Middleware support through composition
- URL path generation with parameter conversion
- Automatic HTTP method handling (HEAD added with GET)
- WebSocket support
- Redirect slash handling

## Layer 2 — Foundation: What was built FIRST

The oldest structural decisions:

1. **BaseRoute abstract class** - The fundamental abstraction that all routing inherits from. Its `__call__`, `matches`, `url_path_for`, and `handle` methods establish the core contract that everything else depends on.

2. **Route matching via regex compilation** - The `compile_path` function and its use of `PARAM_REGEX` establish how path parameters work. This regex-based approach is the bedrock of how Starlette understands URLs.

3. **Scope-based routing** - The entire system operates on ASGI scopes, with `get_route_path(scope)` and path parameter extraction being the foundation of how routes match requests.

4. **Exception handling in BaseRoute.__call__** - The pattern of returning 404s for HTTP and WebSocket close frames for WS was implemented first and forms the basic error handling strategy.

## Layer 3 — Sediment: What accumulated between foundation and surface

Stratum 1: **WebSocket support** (early addition)
- Added `websocket_close` handling in BaseRoute.__call__
- Mount expanded to support websocket scope type
- Router.not_found added websocket-specific handling

Stratum 2: **Middleware composition** (growth phase)
- Both Route and Mount acquired middleware chains
- Router built a middleware_stack property
- Middleware was applied in reverse order (outermost first)

Stratum 3: **URL generation system** (feature expansion)
- `url_path_for` methods added to all route types
- `replace_params` function created for parameter replacement
- URLPath class introduced (implied by returns)
- `NoMatchFound` exception formalized

Stratum 4: **Lifespan context management** (ASGI 2.0 compliance)
- Router lifespan property with _DefaultLifespan
- Multiple lifespan format support (async generator, generator, direct function)
- Deprecation warnings for generator-based lifespans

Stratum 5: **Redirect slash handling** (UX improvement)
- Added to Router with redirect_slashes parameter
- Automatic redirect behavior for trailing/missing slashes
- Built into the core routing flow in Router.app

Stratum 6: **Parameter conversion system** (refinement)
- Convertor types system (`CONVERTOR_TYPES`)
- Param convertors stored in compiled path data
- Type validation and conversion in Route.matches
- Duplicated parameter detection

## Layer 4 — Fossils: Dead code and vestigial patterns

1. **Deprecated lifespan patterns**:
   - `asynccontextmanager` function usage warnings
   - Generator function lifespan wrappers
   - These replaced with direct async context managers

2. **Vestigial endpoint detection**:
   - The complex endpoint handler inspection (`while isinstance(endpoint_handler, functools.partial):`)
   - Suggests early attempts at wrapping/partial functions that are now less common

3. **Historical route matching patterns**:
   - The Match.PARTIAL handling in Router suggests early attempts at priority-based routing that was simplified

4. **Default Route behavior**:
   - Route.__init__ hardcodes ["GET"] as default methods when None
   - This pattern might be vestigial from an era when GET was more dominant

## Layer 5 — Fault Lines: Where layers meet badly

1. **Mount/Router tension**: Mount creates a Router internally when routes= is provided, but this creates an abstraction layer that can confuse the route hierarchy.

2. **Parameter conversion conflicts**: The convertor system in compile_path vs. the simple string replacement in replace_params - these operate on different data structures (convertors vs string formats).

3. **Middleware composition inconsistencies**: Route and Mount apply middleware in their __init__, while Router applies it in a separate middleware_stack property - different approaches to the same problem.

4. **Scope namespace pollution**: Both Route and Mount add similar but different keys to child_scope (endpoint vs app, path_params handling differences).

5. **Redirect slash complexity**: The redirect logic in Router.app is complex and intertwined with the core routing flow, making it hard to modify or bypass.

## DERIVE: What's the conservation law?

The conservation law is: **Type Safety × Developer Experience = constant**

This codebase consistently preserves this product:
- Type safety through strict parameter validation, convertor systems, and explicit method handling
- Developer experience through automatic behaviors (HEAD with GET, redirect slashes, middleware composition)

When one is sacrificed, the other is increased to maintain the product:
- Adding strict parameter checking (type safety) reduces developer burden (no manual validation needed)
- Automatic behaviors (developer experience) require complex internal type checking

## DIAGNOSTIC: What does YOUR excavation conceal?

My analysis assumes linear development from foundation to surface, but actual development likely involved:
1. Multiple refactors where newer layers completely replaced older ones rather than accumulating
2. Features that were added, then removed, then re-implemented differently
3. The "foundation" I identified may actually be a middle layer built on even older ASGI conventions
4. My sediment analysis assumes chronological addition, but features may have been added out of order based on dependencies
5. The "fault lines" may actually represent intentional design compromises rather than poor layering

The code's actual history likely involves more circular development than my linear excavation suggests, with newer features being built on top of, then below, then around older features as requirements evolved.
