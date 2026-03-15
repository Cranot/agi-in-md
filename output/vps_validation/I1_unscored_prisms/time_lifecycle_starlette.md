# Time/Lifecycle Prism Analysis

## Step 1: Find the Ordering Assumptions

1. **Route initialization before use** (Route.__init__):
   - Assumption: Route objects are fully initialized before being matched or called
   - Would fail if `matches()` or `handle()` were called before initialization
   - Location: All BaseRoute subclasses expect initialization first

2. **Router routes initialization before routing** (Router.__init__):
   - Assumption: Router has its routes list populated before route matching
   - Would fail if routes are accessed or matched before initialization
   - Location: Router.app() accesses self.routes

3. **Middleware stack initialization before use** (Router.__init__):
   - Assumption: Middleware stack is built before the router is called
   - Would fail if middleware isn't applied properly during initialization
   - Location: Router.__init__ builds middleware_stack

4. **Path compilation before route matching** (compile_path):
   - Assumption: Path regex is compiled before matching against request
   - Would fail if regex matching attempted before compilation
   - Location: Route and Mount compile paths during initialization

5. **Route matching before handling** (BaseRoute.__call__):
   - Assumption: Match is determined before handling the request
   - Would fail if handling attempted before proper matching
   - Location: BaseRoute.__call__ calls matches() then handle()

6. **Scope existence before router processing** (Router.app):
   - Assumption: ASGI scope exists when router processes requests
   - Would fail if router called without proper scope
   - Location: Router.app accesses scope["type"]

7. **Lifespan context initialization before use** (Router.__init__):
   - Assumption: Lifespan context is set before router handles lifespan events
   - Would fail if lifespan events processed without proper context
   - Location: Router.__init__ sets lifespan_context

## Step 2: Find the Ordering Violations

1. **Violation of Route initialization before use**:
   ```python
   route = Route.__new__(Route)  # Bypass __init__
   await route.handle(scope, receive, send)  # Crashes - undefined attributes
   ```
   - Failure mode: AttributeError when accessing undefined attributes like path_regex, app, etc.
   - Behavior: Crashes with AttributeError on first attribute access

2. **Violation of Router routes initialization before routing**:
   ```python
   router = Router()
   router.routes.append(None)  # Add invalid route after initialization
   await router.app(scope, receive, send)  # Crashes when processing None route
   ```
   - Failure mode: AttributeError when accessing None route's methods
   - Behavior: Crashes with "NoneType has no attribute 'matches'"

3. **Violation of Middleware stack initialization before use**:
   ```python
   router = Router(middleware=None)
   router.middleware_stack = None  # Break middleware stack after init
   await router.__call__(scope, receive, send)  # Crashes
   ```
   - Failure mode: AttributeError when calling None as a coroutine
   - Behavior: Crashes with "'NoneType' object is not callable"

4. **Violation of Path compilation before route matching**:
   ```python
   route = Route("/test", endpoint)
   route.path_regex = None  # Remove compiled regex after init
   match, child_scope = route.matches(scope)  # Crashes
   ```
   - Failure mode: AttributeError when accessing None path_regex
   - Behavior: Crashes with "'NoneType' object has no attribute 'match'"

5. **Violation of Route matching before handling**:
   ```python
   route = Route("/test", endpoint)
   route.path_regex.match = lambda x: None  # Force always no match
   await route.handle(scope, receive, send)  # Called without proper matching
   ```
   - Failure mode: Inconsistent state, potential security issues
   - Behavior: Handles requests that shouldn't match this route

6. **Violation of Scope existence before router processing**:
   ```python
   scope = {}  # Empty scope without required keys
   await router.app(scope, receive, send)  # Crashes on scope access
   ```
   - Failure mode: KeyError when accessing missing scope keys
   - Behavior: Crashes with "'type' not in dict"

7. **Violation of Lifespan context initialization before use**:
   ```python
   router = Router(lifespan=None)
   await router.app({"type": "lifespan", "asgi": {"version": "3.0"}, "event": "startup"}, receive, send)
   # Crashes if lifespan_context is None
   ```
   - Failure mode: AttributeError if lifespan_context is None
   - Behavior: Crashes with "'NoneType' object is not callable"

## Step 3: The Ordering Law

| Assumption | Required Before | Violation Sequence | Failure Mode | Damage | Explicitness Cost |
|------------|-----------------|-------------------|--------------|--------|-------------------|
| Route initialization before use | `matches()`, `handle()` | Create route without `__init__` | AttributeError | High (security risk) | Low (natural in OOP) |
| Router routes initialization before routing | Route matching in `app()` | Create router without routes | AttributeError | High (500 errors) | Medium (list init) |
| Middleware stack initialization before use | ASGI call in `__call__()` | Break middleware after init | AttributeError | Medium (broken functionality) | Low (natural in OOP) |
| Path compilation before route matching | Regex matching in `matches()` | Remove compiled regex after init | AttributeError | Medium (routing errors) | Low (done in init) |
| Route matching before handling | Request handling in `__call__()` | Force bypass of matching | Logic error | High (security risk) | Medium (state tracking) |
| Scope existence before router processing | Router processing | Call with empty scope | KeyError | Medium (500 errors) | High (schema validation) |
| Lifespan context initialization before use | Lifespan event handling | Call with invalid lifespan | AttributeError | Low (only affects startup/shutdown) | Medium (context setup) |

The most damaging ordering violation is **Route initialization before use**. 

**Conservation Law**: Explicit ordering enforcement costs minimal developer effort but prevents critical security vulnerabilities. The cost of making ordering explicit (proper initialization and validation) is low compared to the potential damage of uninitialized routes being called. The explicitness cost is primarily in defensive programming and validation checks, which are small investments that prevent large-scale failures or security breaches.
