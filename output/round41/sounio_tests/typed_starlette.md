## Finding 1
**Claim**: The `Match` enum defines a three-state matching system (NONE, PARTIAL, FULL) that enables method-mismatch detection without losing path-match information.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:line_16-20
**Falsifiable**: yes — count enum members, verify three distinct states
**If wrong**: The entire partial matching analysis collapses; routing becomes binary.

## Finding 2
**Claim**: `request_response` decorator creates an ASGI application that wraps both async and sync endpoint functions into a uniform async interface.
**Type**: DERIVED
**Confidence**: 0.95
**Provenance**: derivation:from_Finding_1 + source:line_23-35
**Falsifiable**: yes — trace execution path for sync vs async function through `functools.partial(run_in_threadpool, func)`
**If wrong**: The sync/async handling model changes; thread pool behavior becomes unpredictable.

## Finding 3
**Claim**: `request_response` contains a nested function definition `async def app(scope, receive, send)` at line 28 that shadows the outer `app` function at line 26, making the outer function unreachable after the inner definition.
**Type**: MEASURED
**Confidence**: 1.0
**Provenance**: source:line_26-31
**Falsifiable**: yes — static analysis shows inner `app` definition at line 28 overwrites the closure variable before it's called
**If wrong**: No behavior change — the outer `app` is never invoked; inner handles all calls.

## Finding 4
**Claim**: `compile_path` uses regex `PARAM_REGEX` to extract path parameters with optional type converters, enforcing the constraint that all converters must exist in `CONVERTOR_TYPES` at compile time via assertion.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:line_44-72
**Falsifiable**: yes — pass a path with unknown converter like `{id:uuid}` and observe assertion failure
**If wrong**: Path parameter type system changes from closed to open.

## Finding 5
**Claim**: Duplicate path parameter names within a single route raise `ValueError` at route definition time, not at request time.
**Type**: MEASURED
**Confidence**: 1.0
**Provenance**: source:line_62-66
**Falsifiable**: yes — define route with `"/{id}/items/{id}"` and observe immediate `ValueError`
**If wrong**: Error handling shifts from fail-fast to runtime.

## Finding 6
**Claim**: `BaseRoute.__call__` handles `Match.NONE` by sending protocol-specific error responses (404 for HTTP, WebSocket close for WebSocket) without raising exceptions.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:line_87-95
**Falsifiable**: yes — trace the `Match.NONE` branch execution
**If wrong**: Error handling model changes from response-based to exception-based.

## Finding 7
**Claim**: `Route.matches` returns `Match.PARTIAL` when the path matches but the HTTP method doesn't, enabling the Router to potentially redirect or return 405.
**Type**: DERIVED
**Confidence**: 0.95
**Provenance**: derivation:from_Finding_1 + source:line_118-120
**Falsifiable**: yes — send POST to GET-only route and verify `Match.PARTIAL` returned
**If wrong**: Method-based routing disambiguation fails.

## Finding 8
**Claim**: The Router never generates HTTP 405 Method Not Allowed responses — partial matches are handled identically to full matches by calling `route.handle()`.
**Type**: MEASURED
**Confidence**: 0.95
**Provenance**: source:line_233-236
**Falsifiable**: yes — trace `match is Match.PARTIAL` branch at lines 232-236; no 405 generation
**If wrong**: This is a spec violation for HTTP semantic correctness.

## Finding 9
**Claim**: `Mount` compiles its path with an implicit `/{path:path}` suffix, meaning all mounts are prefix matches that capture the remainder into a `path` parameter.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:line_155
**Falsifiable**: yes — inspect `Mount.path_regex` after instantiation
**If wrong**: Mount matching model changes from prefix-capture to exact-match.

## Finding 10
**Claim**: `Mount.matches` constructs `child_scope` with `root_path` accumulation (`root_path + matched_path`), enabling nested mount path reconstruction.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:line_169-175
**Falsifiable**: yes — trace scope mutation through nested mounts
**If wrong**: Nested routing loses path context for URL generation.

## Finding 11
**Claim**: `Mount.url_path_for` handles three distinct cases: exact name match with path param, name prefix delegation (`name:subname`), and anonymous mount delegation.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:line_179-198
**Falsifiable**: yes — test each branch with appropriate name patterns
**If wrong**: Reverse URL generation for mounted apps fails.

## Finding 12
**Claim**: `Router.__init__` wraps itself in middleware by setting `self.middleware_stack = self.app` then applying middleware in reverse order, meaning the outermost middleware wraps the routing logic.
**Type**: DERIVED
**Confidence**: 0.95
**Provenance**: source:line_213-217 + derivation:middleware_pattern
**Falsifiable**: yes — add logging middleware and verify it wraps the Router.app method
**If wrong**: Middleware execution order inverts.

## Finding 13
**Claim**: `Router.not_found` has divergent behavior based on presence of `"app"` key in scope: raises `HTTPException(404)` if present, sends `PlainTextResponse` otherwise.
**Type**: MEASURED
**Confidence**: 1.0
**Provenance**: source:line_219-227
**Falsifiable**: yes — test with and without `"app"` in scope
**If wrong**: Error propagation model changes between mounted and unmounted routers.

## Finding 14
**Claim**: The redirect-slash logic at lines 238-250 performs a second full route traversal with modified path, incurring O(n) cost where n = number of routes.
**Type**: MEASURED
**Confidence**: 1.0
**Provenance**: source:line_238-250
**Falsifiable**: yes — count route iterations in redirect scenario
**If wrong**: Performance model for trailing-slash redirects changes.

## Finding 15
**Claim**: The `GET` method implicitly adds `HEAD` to the allowed methods set (line 133-134), but this addition happens only when `methods` is explicitly provided and contains `GET`.
**Type**: MEASURED
**Confidence**: 1.0
**Provenance**: source:line_131-134
**Falsifiable**: yes — inspect `route.methods` after creating route with `methods=["GET"]`
**If wrong**: HTTP HEAD compliance changes.

## Finding 16
**Claim**: `Route.__init__` unwraps `functools.partial` wrappers to find the underlying function for introspection (lines 111-113), enabling correct naming and method detection for wrapped endpoints.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:line_111-113
**Falsifiable**: yes — pass a `functools.partial` wrapped function as endpoint
**If wrong**: Wrapped endpoints lose correct naming/handler detection.

## Finding 17
**Claim**: `replace_params` mutates the input `path_params` dictionary by popping matched keys, creating a destructive API that loses information about which params were used.
**Type**: MEASURED
**Confidence**: 1.0
**Provenance**: source:line_39
**Falsifiable**: yes — call `replace_params` and observe input dict mutation
**If wrong**: URL generation for nested routes loses parameter tracking.

## Finding 18
**Claim**: `Router.app` method asserts `scope["type"]` is one of three values at line 221, but the type system doesn't enforce this constraint at the ASGI boundary.
**Type**: DERIVED
**Confidence**: 0.9
**Provenance**: source:line_221 + derivation:ASGI_spec_knowledge
**Falsifiable**: yes — pass scope with type="unknown" and observe assertion failure
**If wrong**: Protocol compliance enforcement changes.

## Finding 19
**Claim**: Lifespan handling accepts three different function types (async gen, sync gen, context manager) with deprecation warnings for the generator variants, indicating a migration path in progress.
**Type**: MEASURED
**Confidence**: 1.0
**Provenance**: source:line_203-212
**Falsifiable**: yes — pass each type and observe behavior/warnings
**If wrong**: Backwards compatibility model changes.

## Finding 20
**Claim**: The `Router.routes` list is mutable after construction (line 200 creates a copy but stores a mutable list), enabling dynamic route registration but risking thread-safety issues.
**Type**: DERIVED
**Confidence**: 0.85
**Provenance**: source:line_200 + derivation:concurrency_knowledge
**Falsifiable**: yes — modify `router.routes` post-construction and verify routing changes
**If wrong**: Dynamic routing capability assessment changes.

---

## Conservation Law

**Law**: Match precision × Error specificity = constant
**Type**: DERIVED
**Confidence**: 0.85
**Provenance**: derivation:from_Findings_1,7,8,13

The three-state Match enum (Finding 1) enables partial matching (Finding 7), but the Router discards this information by treating PARTIAL identically to FULL (Finding 8). The system gains match precision at the Route level but loses error specificity at the Router level — no 405 responses despite knowing the method mismatch. Similarly, `not_found` has conditional behavior based on scope contents (Finding 13). Precision gained at one layer is lost at the next.

---

## Count per Type
- 9 STRUCTURAL
- 6 MEASURED
- 5 DERIVED
- 0 KNOWLEDGE
- 0 ASSUMED

## Epistemic Quality Score
69% STRUCTURAL+MEASURED (14/20 grounded in direct code observation)
