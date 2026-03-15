## Verification Questions for Factual Claims

### Conservation Laws Section

**Claim 1:** `Route.matches()` uses `path_params.update(matched_params)` — merges, never replaces
- **Verification:** Does the `matches()` method in the `Route` class contain `path_params.update(matched_params)`? Does it ever delete or replace existing keys?

**Claim 2:** `Mount.matches()` builds `child_scope` with merged `path_params` from parent
- **Verification:** Does `Mount.matches()` construct a `child_scope` dictionary? Does it include `path_params` that incorporates parent routing state?

**Claim 3:** `Router.app()` uses `scope.update(child_scope)` which mutates the global scope
- **Verification:** Does `Router.app()` call `scope.update(child_scope)`? Is `scope` the parameter passed in from outside (making it "global" from the method's perspective)?

**Claim 4:** PARTIAL match logic captures only the first partial match
- **Verification:** Is there code at approximately lines 180-182 that reads `elif match is Match.PARTIAL and partial is None: partial = route`? Does this mean subsequent PARTIAL matches are ignored?

**Claim 5:** HTTP routing failure produces a 404 response
- **Verification:** When no route matches in HTTP handling, does the code return a 404 status code response?

**Claim 6:** WebSocket routing failure produces a silent close with no diagnostic info
- **Verification:** When no route matches in WebSocket handling, does the code close the connection without sending error details?

---

### Defects Section

**Claim 7:** `request_response` at lines 52-58 defines a nested `async def app` that shadows the outer `app`
- **Verification:** Is there a function called `request_response`? Does it contain an outer `async def app` and a nested inner `async def app` with the same name?

**Claim 8:** `replace_params()` at lines 66-71 mutates `path_params.pop(key)`
- **Verification:** Does the `replace_params` function call `path_params.pop(key)`? Does this modify the caller's dictionary?

**Claim 9:** The nested inner `app` in `request_response` closes over the outer `request` but the outer `app`'s parameters are unused
- **Verification:** In the nested structure, does the inner `app` reference `request` from the outer scope? Are the `(scope, receive, send)` parameters of the outer `app` directly used in its body?

**Claim 10:** `redirect_slashes` at lines 194-206 creates a shallow scope copy
- **Verification:** Does the redirect logic create a copy of scope using shallow copy (e.g., `scope.copy()` or `dict(scope)`)? Does it modify only the `path` key?

**Claim 11:** Mount at line 152 compiles `self.path + "/{path:path}"` but stores original `self.path`
- **Verification:** Does the `Mount` class compile a path pattern that includes `/{path:path}`? Does it store the original `self.path` separately?

**Claim 12:** `Mount.routes` property at lines 163-165 uses `getattr(self._base_app, "routes", [])`
- **Verification:** Does the `routes` property of `Mount` use `getattr` with those exact arguments?

---

### Concealment Mechanisms Section

**Claim 13:** Middleware wrapping uses `reversed(middleware)` and assigns `self.app = cls(self.app, ...)`
- **Verification:** Is there middleware wrapping code that iterates in reverse and reassigns `self.app`?

**Claim 14:** `matches()` returns a partial scope that must be merged via `scope.update()`
- **Verification:** Do all `matches()` implementations return a `child_scope` dict? Is this scope incomplete without merging?

**Claim 15:** Endpoint unwrapping handles `functools.partial` but not class instances with `__call__`, decorator chains, or lambda wrappers
- **Verification:** Is there a while loop that unwraps `functools.partial`? Does it check for other wrapper types?

**Claim 16:** `matched_params[key] = self.param_convertors[key].convert(value)` assumes key exists
- **Verification:** Does this line exist? Is there a defensive check before accessing `self.param_convertors[key]`?

---

### The Deepest Pattern Section

**Claim 17:** A `Match` enum exists with NONE, PARTIAL, and FULL states
- **Verification:** Is there a `Match` enum class? Does it have `NONE`, `PARTIAL`, and `FULL` values?

**Claim 18:** `BaseRoute` subclasses implement `matches()` methods
- **Verification:** Is there a `BaseRoute` class? Do `Route`, `Mount`, and potentially other subclasses implement `matches()`?

---

### Summary of Verification Questions

| # | Claim | Verification Method |
|---|-------|---------------------|
| 1 | Route.matches() merges via update | Grep for `path_params.update` in Route class |
| 2 | Mount.matches() builds child_scope with merged params | Inspect Mount.matches() implementation |
| 3 | Router.app() mutates scope | Grep for `scope.update(child_scope)` in Router |
| 4 | PARTIAL captures first only | Find `partial is None` conditional |
| 5 | HTTP failure → 404 | Trace HTTP no-match path |
| 6 | WebSocket failure → silent close | Trace WebSocket no-match path |
| 7 | Nested app shadowing | Read `request_response` function |
| 8 | replace_params mutation | Read `replace_params` function |
| 9 | Outer params unused | Trace parameter usage in nested structure |
| 10 | Shallow scope copy in redirect | Read redirect_slashes implementation |
| 11 | Mount path compilation | Read Mount.__init__ |
| 12 | Mount.routes getattr | Read Mount.routes property |
| 13 | Middleware wrapping pattern | Grep for middleware iteration |
| 14 | matches() returns partial scope | Inspect return type of matches() |
| 15 | Partial unwrapping only | Read endpoint unwrapping logic |
| 16 | No convertor key check | Find param_convertors access |
| 17 | Match enum exists | Grep for `class Match` |
| 18 | BaseRoute with matches() | Find BaseRoute and subclasses |
