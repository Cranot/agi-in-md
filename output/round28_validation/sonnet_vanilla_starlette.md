Here's a thorough analysis of the Starlette routing module:

---

## Structural Patterns

**Compile-once, match-many.** `compile_path` runs at `__init__` time, producing a compiled regex + format string + convertor map. Runtime matching is pure regex. Clean separation.

**Middleware as stack wrapping.** Both `Route`, `Mount`, and `Router` use the same pattern: iterate middleware in reverse, each wrapping the previous callable. `self.app` ends up as the outermost shell, `self._base_app` (or the original endpoint) lives at the core. Consistent across all three classes.

**ASGI scope-as-shared-dict threading.** Routing state is passed by mutating the scope dict (`scope.update(child_scope)`). Child routes communicate with parents and error handlers through keys they inject into scope (`endpoint`, `path_params`, `root_path`, `app_root_path`).

**`"app" in scope` as nesting detector.** When there's a parent Starlette app, `"app"` is in scope and errors should raise `HTTPException` (to bubble up). When the router is outermost, send a plain response directly. Used in two places. Fragile — any middleware that adds `"app"` to scope would accidentally switch behavior.

---

## Problems

### 1. Shadow variable in `request_response`

```python
async def app(scope, receive, send):         # outer app
    request = Request(scope, receive, send)

    async def app(scope, receive, send):     # inner app — shadows outer
        response = await f(request)
        await response(scope, receive, send)

    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
```

The inner `app` silently shadows the outer. The `wrap_app_handling_exceptions` call captures the inner one, which is correct, but a future reader editing this function risks passing the wrong `app`. The inner should be named `_inner` or `_handler`.

---

### 2. `replace_params` mutates the caller's dict

```python
def replace_params(path, param_convertors, path_params):
    for key, value in list(path_params.items()):
        if "{" + key + "}" in path:
            ...
            path_params.pop(key)   # <-- mutates input
    return path, path_params
```

`url_path_for` in `Route` doesn't notice because it doesn't reuse the dict. But `Mount.url_path_for` does this:

```python
path_params["path"] = ""                                          # mutates caller's dict
path_prefix, remaining_params = replace_params(..., path_params)  # pops more keys
if path_kwarg is not None:
    remaining_params["path"] = path_kwarg
```

The caller's `path_params` dict is modified in place. If the caller passes `**kwargs` this is the unwrapped dict, so it's a copy — but it's easy to call `url_path_for` with an explicit dict and get it silently destroyed.

---

### 3. `assert` used for runtime validation

Three locations:

```python
assert path.startswith("/"), "Routed paths must start with '/'"          # Route.__init__
assert convertor_type in CONVERTOR_TYPES, f"Unknown path convertor ..."  # compile_path
assert not remaining_params                                               # Route.url_path_for
```

`assert` statements are eliminated when Python runs with `-O` (optimize flag). The first two are legitimate validation that should raise `ValueError`. The third (`assert not remaining_params`) is a "this can't happen" invariant — but if `replace_params` has a bug, this silently passes in optimized mode instead of raising.

---

### 4. The 405 dance — method checking split across two methods

In `Route`:

```python
def matches(self, scope):
    if match:
        if self.methods and scope["method"] not in self.methods:
            return Match.PARTIAL, child_scope    # path matched, method didn't
        else:
            return Match.FULL, child_scope

async def handle(self, scope, receive, send):
    if self.methods and scope["method"] not in self.methods:  # checked AGAIN
        ...send 405...
    else:
        await self.app(scope, receive, send)
```

`Match.PARTIAL` from `Route` means "path matched but method didn't." `Match.PARTIAL` from `Mount` means "prefix matched." These are semantically different uses of the same enum value — `Mount.matches` always returns `FULL` for any path prefix match. The semantic overloading is not documented and not obvious.

---

### 5. Router only tracks the first partial match

```python
elif match == Match.PARTIAL and partial is None:
    partial = route          # first partial wins, rest ignored
    partial_scope = child_scope
```

If three routes all match the path but none match the method (e.g., GET /users when only POST and PUT exist), only the first route's allowed methods appear in the 405 `Allow` header. A correct 405 response should aggregate methods from all matching routes.

---

### 6. `redirect_slashes` uses a shallow scope copy

```python
redirect_scope = dict(scope)   # shallow copy
if route_path.endswith("/"):
    redirect_scope["path"] = redirect_scope["path"].rstrip("/")
else:
    redirect_scope["path"] = redirect_scope["path"] + "/"
```

`path_params` inside scope is a dict — `redirect_scope["path_params"]` still points to the same object. Any route that mutates `scope["path_params"]` during redirect matching would corrupt the original scope. In practice routes don't mutate during `matches()`, but the pattern is a trap.

Also: path and path_info can both carry the path in some ASGI setups. Only `"path"` is updated here, not `"path_info"` or `"raw_path"`. This is likely fine for Starlette's own servers but fragile under non-standard ASGI middleware.

---

### 7. `"app" in scope` is an implicit convention, not a contract

```python
if "app" in scope:
    raise HTTPException(status_code=404)
else:
    response = PlainTextResponse("Not Found", status_code=404)
```

This convention is invisible to users of the router. A custom middleware that stores something under `"app"` in scope (reasonable — `scope["app"]` is an ASGI idiom) would silently switch the router into "raise exceptions" mode for 404/405. No validation, no documentation, no type annotation signals this expectation.

---

## Summary Table

| Issue | Severity | Location |
|---|---|---|
| Shadow `app` variable | Medium — readability trap | `request_response` |
| Mutating input `path_params` | Medium — caller surprise | `replace_params`, `Mount.url_path_for` |
| `assert` for runtime validation | Medium — fails under `-O` | `compile_path`, `Route.__init__`, `url_path_for` |
| `Match.PARTIAL` overloaded semantics | Low — conceptual debt | `Route.matches` vs `Mount.matches` |
| 405 method check duplicated | Low — fragile split responsibility | `Route.matches` + `Route.handle` |
| First partial match only for 405 | Low — incorrect Allow header | `Router.app` |
| Shallow scope copy in redirect | Low — latent mutation bug | `Router.app` |
| `"app" in scope` implicit convention | Low — invisible contract | `not_found`, `Route.handle` |

The most structurally significant: **scope mutation as the communication mechanism** couples every layer together through a shared mutable dict, making the data flow invisible to static analysis and any individual route's side effects invisible to its neighbors.
