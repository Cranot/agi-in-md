## Starlette Routing Analysis

### Structural Patterns

**Composite dispatch chain.** `Router` → `Mount` → `Route` forms a tree. Each node matches against the ASGI scope, peels off its prefix, and delegates downward. This is the standard ASGI composition model — clean and well-proven.

**Template method on `BaseRoute`.** `matches()` / `handle()` / `url_path_for()` define the protocol; subclasses implement. `__call__` on `BaseRoute` orchestrates match→handle with a built-in 404/websocket-close fallback.

**Middleware as reversed wrapper chain.** `for cls, args, kwargs in reversed(middleware)` appears in `Route`, `Mount`, and `Router` — three independent places building the same onion. Works correctly but is duplicated logic.

---

### Actual Problems

**1. `request_response` shadows its own name** (line ~23-30)

```python
async def app(scope, receive, send):
    request = Request(scope, receive, send)
    async def app(scope, receive, send):  # shadows outer `app`
        response = await f(request)
        await response(scope, receive, send)
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
```

The inner `app` captures `request` from the outer `app`'s scope, then the outer `app` passes the inner `app` to the exception wrapper. It works because Python closures resolve by name at call time — but any refactoring that moves the inner function risks breaking the closure silently. A rename to `inner` would cost nothing.

**2. `replace_params` silently mutates its input**

```python
def replace_params(path, param_convertors, path_params):
    ...
    path_params.pop(key)
    return path, path_params
```

Returns `path_params` after mutating it in place. Callers like `Mount.url_path_for` rely on the mutation to track "remaining" params, but the API *also* returns the dict, creating ambiguity about whether the return value is a new dict or the same one. It's the same one. Anyone calling this expecting non-destructive behavior gets burned.

**3. `assert` used for runtime validation in `compile_path`**

```python
assert convertor_type in CONVERTOR_TYPES, f"Unknown path convertor '{convertor_type}'"
```

And in `Route.__init__`:
```python
assert path.startswith("/"), "Routed paths must start with '/'"
```

Running Python with `-O` strips these entirely. A malformed path or unknown convertor would silently produce garbage regex instead of failing fast. These should be `ValueError` / `TypeError`.

**4. Implicit method defaulting based on endpoint type** (`Route.__init__`)

```python
if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
    self.app = request_response(endpoint)
    if methods is None:
        methods = ["GET"]
else:
    self.app = endpoint
```

Plain functions default to `GET` only. Class-based endpoints default to `methods=None` (all methods allowed). This is a *silent* behavioral fork based on what you pass in — if you forget `methods=["GET", "POST"]` on a function endpoint, POSTs silently 405. If you forget methods on a class endpoint, everything passes through. The asymmetry is undiscoverable without reading source.

**5. Linear scan × 2 on miss** (`Router.app`)

```python
for route in self.routes:          # first scan
    match, child_scope = route.matches(scope)
    ...

# if no match and redirect_slashes:
for route in self.routes:          # second scan with modified path
    match, child_scope = route.matches(redirect_scope)
```

Every 404 pays the cost of scanning all routes twice. For apps with hundreds of routes, this is measurable. No trie, no hash table, no short-circuit caching.

**6. `"app" in scope` as dispatch heuristic** (`Route.handle`, `Router.not_found`)

```python
if "app" in scope:
    raise HTTPException(status_code=405, headers=headers)
else:
    response = PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
await response(scope, receive, send)
```

The presence of `"app"` in the scope dict determines whether to *raise* or *respond directly*. This is a proxy for "am I mounted inside a larger app?" — but scope is a mutable dict that any middleware can modify. The code has two fundamentally different error-handling paths gated on a convention that isn't enforced anywhere.

**7. `Mount.url_path_for` mutation chain**

```python
path_kwarg = path_params.get("path")
path_params["path"] = ""                    # mutate caller's dict
path_prefix, remaining_params = replace_params(...)  # mutates further
if path_kwarg is not None:
    remaining_params["path"] = path_kwarg   # restore, maybe
```

Save → overwrite → call function that pops keys → conditionally restore. This is a mutation juggling act. If `replace_params` changes behavior or a new convertor is added, the restore logic could silently break. The method is doing too much in-place work on a shared dict.

**8. Scope mutation is non-reversible**

```python
scope.update(child_scope)
await route.handle(scope, receive, send)
```

If `route.handle` raises, the scope has already been mutated with `child_scope`. In ASGI this is per-request so it's not catastrophic, but it means error handlers downstream see a scope that's been partially rewritten by a route that failed. Middleware relying on original scope values (like logging the original path) gets the post-match path instead.

---

### Design Observations (Not Bugs, But Worth Naming)

- **PARTIAL match exists only for method-not-allowed.** The entire `Match.PARTIAL` enum value and the partial-tracking loop in `Router.app` exist solely so that a path match with wrong method returns 405 instead of 404. That's a lot of machinery for one HTTP semantic.

- **`Mount` always compiles a catch-all regex** (`/{path:path}`) even when the mount only has exact routes underneath. Every mount pays for a regex that matches everything after the prefix.

- **Middleware triple** `(cls, args, kwargs)` is passed as a raw tuple everywhere. No validation, no type, no named structure. One wrong tuple shape and you get an opaque unpack error at startup.

- **`HEAD` auto-added with `GET`** is a nice convenience, but it's buried in `Route.__init__` constructor logic — invisible to anyone reading route definitions.
