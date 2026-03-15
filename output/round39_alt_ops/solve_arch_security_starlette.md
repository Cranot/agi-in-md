# Stratigraphic Security Excavation of Starlette's ASGI Routing System

## Surface Layer: ASGI Entry Points

The surface consists of two primary entry points where untrusted input first touches the routing system:

1. **Primary ASGI entry point**: `Router.__call__(scope, receive, send)`
   - Accepts `scope` dictionary containing untrusted request data
   - Immediately delegates to middleware stack via `self.middleware_stack(scope, receive, send)`
   - No input validation at surface level

2. **Route entry point**: `BaseRoute.__call__(scope, receive, send)`
   - Receives mutated scope from Router's routing iteration
   - Dispatches based on `scope["type"]` field switching
   - Types: "http", "websocket", "lifespan"
   - Type switching occurs with no sanitization of the type field

3. **Method dispatch in Route.matches()**
   - Checks `scope["method"]` against `self.methods` set
   - No validation of method string format
   - Method comparison is case-sensitive after uppercasing user input

## Path Template Compilation Stratum

Beneath the surface lies the path matching layer where raw path templates become executable regex patterns:

1. **compile_path() transformation**:
   ```python
   PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")
   ```
   - Extracts parameter names and convertor types from `{param:str}` templates
   - Each parameter becomes a named capture group: `(?P<param_name>convertor_regex)`
   - Path segments are regex-escaped before insertion

2. **Parameter extraction flow**:
   ```
   scope["path"] → get_route_path() → path_regex.match() → match.groupdict() 
   → param_convertors[key].convert() → scope["path_params"]
   ```

3. **Validation points**:
   - Parameter name validation: `assert convertor_type in CONVERTOR_TYPES`
   - Duplicate parameter detection: raises ValueError for repeated param names
   - **Critical assumption**: Parameter names in templates are trusted (compile-time only)

4. **What passes unguarded**:
   - Path template syntax itself is never validated at runtime
   - Malformed templates (unclosed braces, invalid regex) would cause compilation failures
   - Convertor regex patterns are trusted implicitly

## Scope Mutation Stratum

The routing system mutates the ASGI scope dictionary at multiple layers:

1. **BaseRoute.__call__ scope mutation**:
   ```python
   scope.update(child_scope)
   ```
   - Overwrites arbitrary scope fields with child route data
   - No protection against key collisions

2. **Route.matches() additions**:
   - `{"endpoint": self.endpoint, "path_params": path_params}`
   - path_params combines existing scope["path_params"] with new matched parameters

3. **Mount.matches() additions**:
   ```python
   {
       "path_params": path_params,
       "app_root_path": scope.get("app_root_path", root_path),
       "root_path": root_path + matched_path,
       "endpoint": self.app,
   }
   ```
   - Critical: Builds new root_path by concatenation
   - **Hidden dependency**: root_path manipulation affects URL generation

4. **Router.app() additions**:
   - `{"router": self}`
   - Router reference added to scope without checking for existing key

5. **Mutable state sharing**:
   - Security-sensitive fields ("user", "auth", "headers") coexist with routing data
   - Child routes can silently overwrite parent scope fields
   - No namespace separation between routing and application state

## Bedrock: Assertion Layer

Critical security assumptions rest on Python's assert mechanism:

1. **compile_path assertions**:
   - `assert convertor_type in CONVERTOR_TYPES` - Guards against unknown convertors
   - When stripped with `python -O`, unknown convertors pass through silently
   - Result: Path matching behavior becomes undefined

2. **Route.__init__ assertions**:
   - `assert path.startswith("/")` - Enforces absolute path requirement
   - Stripped with `-O`, relative paths would be accepted, creating routing conflicts

3. **Mount.__init__ assertions**:
   - `assert path == "" or path.startswith("/")` - Mount path validation
   - `assert app is not None or routes is not None` - Existence requirement
   - Without asserts: empty mounts could be created, leading to routing anomalies

## Fossil Record: Deprecated Patterns

1. **Deprecated async generator lifespans**:
   ```python
   if inspect.isasyncgenfunction(lifespan):
       warnings.warn("async generator function lifespans are deprecated...")
       self.lifespan_context = asynccontextmanager(lifespan)
   ```
   - **Security guarantee**: Generator-based lifespans had clear exception boundaries
   - **Replacement**: Direct async context managers
   - **Lost assumption**: Exception handling behavior changed between approaches
   - Impact: Error propagation patterns shifted subtly

2. **Nested async def in request_response**:
   ```python
   async def app(scope, receive, send):
       request = Request(scope, receive, send)
       
       async def app(scope, receive, send):  # Shadows outer function
           response = await f(request)
           await response(scope, receive, send)
   ```
   - **Vestigial structure**: Inner function shadows outer scope parameters
   - **Hidden obscuring**: Exception boundaries between layers are unclear
   - Impact: Error handling context may be misinterpreted

## replace_params Function Analysis

```python
def replace_params(path, param_convertors, path_params):
    for key, value in list(path_params.items()):
        if "{" + key + "}" in path:
            convertor = param_convertors[key]
            value = convertor.to_string(value)
            path = path.replace("{" + key + "}", value)
            path_params.pop(key)
    return path, path_params
```

**Injection vectors identified**:
1. **Path separator injection**: Convertors must prevent `/` in parameters
2. **Traversal sequences**: `../` mitigation depends on convertor implementation
3. **Control characters**: Encoding/decoding safety not guaranteed at this layer
4. **Parameter substitution**: String replacement occurs without context awareness

**What prevents injection**:
- Individual convertor implementations' `to_string()` methods
- No centralized validation of substituted values
- Path reconstruction assumes convertors are security-aware

## Conservation Law: Path Expressiveness × Attack Surface

The routing system follows a security conservation law:

```
Path expressiveness × Attack surface = constant
```

**Tradeoffs documented**:
1. **Each path parameter**: New injection vector via `convertor.to_string()`
2. **Each mount nesting**: New scope mutation opportunity
   - Mounts create new "root_path" segments
   - Child scopes can overwrite parent fields
3. **Each middleware wrapper**: New exception-handling boundary
   - Exception context may be lost across layers
   - Error propagation paths become complex

**Attack surface expansion points**:
- Parameter convertor complexity → More complex regex → More edge cases
- Mount depth → More scope mutations → More potential for field collisions
- Route count → More match attempts → More regex evaluations

## Fault Lines: Layer Interactions

**Critical fault lines where layers meet**:

1. **Path extraction boundary**:
   ```
   scope["path"] (untrusted) → get_route_path() → regex.match() 
   → groupdict() → convertor.convert() → scope["path_params"] (trusted)
   ```
   - **Trust transition**: Raw path string becomes extracted parameters
   - **What is trusted that should not be**: Parameter names are assumed safe after extraction

2. **Redirect slashes fault line**:
   ```python
   redirect_scope["path"] = redirect_scope["path"].rstrip("/")  # or adds "/"
   redirect_url = URL(scope=redirect_scope)  # Uses manipulated path
   response = RedirectResponse(url=str(redirect_url))
   ```
   - **Open redirect vector**: Path manipulation affects final redirect URL
   - **Attack scenario**: Trailing slash manipulation could bypass domain validation
   - **Missing guard**: No URL validation after path manipulation

3. **Scope mutation fault lines**:
   - **Reading for security**: scope["method"], scope["path"], scope["type"]
   - **Writing with user data**: scope["path_params"], scope["endpoint"]
   - **Shared mutable state**: No clear contract between routing and security layers

## Hidden Dependencies: Mutable State Sharing

**Critical shared mutable state without explicit contracts**:

1. **scope["path_params"] dictionary**:
   - Read by route handlers for parameter access
   - Written by routing layer at multiple mutation points
   - No protection against handler modification affecting routing

2. **scope["root_path"] string**:
   - Read by Mount.matches() for path resolution
   - Written by Mount layer via concatenation
   - **Critical vulnerability**: Path traversal could be introduced if root_path is manipulated

3. **scope["endpoint"] reference**:
   - Written by routing layer
   - Read by ASGI server for dispatch
   - No validation of endpoint callable safety

4. **scope["type"] field**:
   - Used for routing decisions
   - Set by ASGI server, but could be manipulated by middleware
   - No sanitization before type-based dispatch

The routing system assumes clean separation of concerns but shares mutable state across security boundaries without explicit contracts or validation.
