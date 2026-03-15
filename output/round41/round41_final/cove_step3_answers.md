## Verification Answers

**Claim 1:** `Route.matches()` uses `path_params.update(matched_params)` — merges, never replaces
**YES** — In `Route.matches()`:
```python
path_params = dict(scope.get("path_params", {}))
path_params.update(matched_params)
```
No deletion or replacement of keys occurs.

---

**Claim 2:** `Mount.matches()` builds `child_scope` with merged `path_params` from parent
**YES** — In `Mount.matches()`:
```python
path_params = dict(scope.get("path_params", {}))
path_params.update(matched_params)
child_scope = {
    "path_params": path_params,
    ...
}
```

---

**Claim 3:** `Router.app()` uses `scope.update(child_scope)` which mutates the global scope
**YES** — In `Router.app()`:
```python
if match is Match.FULL:
    scope.update(child_scope)
    await route.handle(scope, receive, send)
```
And again for partial matches. `scope` is the parameter passed in from outside.

---

**Claim 4:** PARTIAL match logic captures only the first partial match
**YES** — The code reads:
```python
elif match is Match.PARTIAL and partial is None:
    partial = route
    partial_scope = child_scope
```
The `partial is None` guard means subsequent PARTIAL matches are ignored.

---

**Claim 5:** HTTP routing failure produces a 404 response
**YES** — In `Router.not_found()`:
```python
if "app" in scope:
    raise HTTPException(status_code=404)
else:
    response = PlainTextResponse("Not Found", status_code=404)
```

---

**Claim 6:** WebSocket routing failure produces a silent close with no diagnostic info
**YES** — In `Router.not_found()`:
```python
if scope["type"] == "websocket":
    websocket_close = WebSocketClose()
    await websocket_close(scope, receive, send)
    return
```
No error details are sent.

---

**Claim 7:** `request_response` defines a nested `async def app` that shadows the outer `app`
**YES** — The function contains:
```python
async def app(scope, receive, send):
    request = Request(scope, receive, send)

    async def app(scope, receive, send):
        response = await f(request)
        await response(scope, receive, send)
```

---

**Claim 8:** `replace_params()` mutates `path_params.pop(key)`
**YES** — The function contains:
```python
def replace_params(path, param_convertors, path_params):
    for key, value in list(path_params.items()):
        ...
        path_params.pop(key)
```
This modifies the caller's dictionary.

---

**Claim 9:** The nested inner `app` closes over `request` but the outer `app`'s parameters are unused
**NO** — The outer `app`'s parameters `(scope, receive, send)` ARE used:
1. Passed to `Request(scope, receive, send)` constructor
2. Passed to `wrap_app_handling_exceptions(app, request)(scope, receive, send)`

---

**Claim 10:** `redirect_slashes` creates a shallow scope copy
**YES** — The code uses:
```python
redirect_scope = dict(scope)
```
`dict(scope)` creates a shallow copy, then only `path` is modified.

---

**Claim 11:** Mount compiles `self.path + "/{path:path}"` but stores original `self.path`
**YES** — In `Mount.__init__()`:
```python
self.path = path.rstrip("/")
...
self.path_regex, self.path_format, self.param_convertors = compile_path(self.path + "/{path:path}")
```

---

**Claim 12:** `Mount.routes` property uses `getattr(self._base_app, "routes", [])`
**YES** — The property is:
```python
@property
def routes(self):
    return getattr(self._base_app, "routes", [])
```

---

**Claim 13:** Middleware wrapping uses `reversed(middleware)` and assigns `self.app = cls(self.app, ...)`
**YES** — In both `Route.__init__()` and `Mount.__init__()`:
```python
if middleware is not None:
    for cls, args, kwargs in reversed(middleware):
        self.app = cls(self.app, *args, **kwargs)
```

---

**Claim 14:** `matches()` returns a partial scope that must be merged via `scope.update()`
**YES** — All `matches()` implementations return `(Match.X, child_scope)` where `child_scope` is incomplete (e.g., only contains `endpoint` and `path_params`), requiring merge into full scope.

---

**Claim 15:** Endpoint unwrapping handles `functools.partial` but not class instances with `__call__`, decorator chains, or lambda wrappers
**YES** — The unwrapping logic:
```python
endpoint_handler = endpoint
while isinstance(endpoint_handler, functools.partial):
    endpoint_handler = endpoint_handler.func
if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
    ...
```
Only `functools.partial` is handled in the while loop.

---

**Claim 16:** `matched_params[key] = self.param_convertors[key].convert(value)` assumes key exists
**YES** — The line:
```python
matched_params[key] = self.param_convertors[key].convert(value)
```
Accesses `self.param_convertors[key]` without defensive check (though `compile_path` should ensure consistency).

---

**Claim 17:** A `Match` enum exists with NONE, PARTIAL, and FULL states
**YES** — The enum is defined:
```python
class Match(Enum):
    NONE = 0
    PARTIAL = 1
    FULL = 2
```

---

**Claim 18:** `BaseRoute` subclasses implement `matches()` methods
**YES** — `BaseRoute` defines abstract `matches()`:
```python
class BaseRoute:
    def matches(self, scope):
        raise NotImplementedError()
```
Both `Route` and `Mount` subclass `BaseRoute` and implement `matches()`.
