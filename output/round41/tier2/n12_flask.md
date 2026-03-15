# PHASE 1 — STRUCTURAL ANALYSIS

## Three Properties This Code Simultaneously Claims

1. **Global Proxy Access** — `request`, `session`, `g`, `app_ctx` are globally accessible (lines 31-35 imports) and delegate to the current context via `_cv_app` (line 960), claiming thread-safe request-local state without explicit parameter passing.

2. **Transparent Middleware Composability** — The `wsgi_app` method (lines 1295-1344) and its docstring explicitly promise that middleware can wrap the app without losing reference to the original object: "middleware can be applied without losing a reference to the app object."

3. **Strict Request Isolation** — Each request gets its own `AppContext` (line 1320), pushed/popped in LIFO order with error collection (lines 1320-1344), claiming no state leakage between requests.

## Proof They Cannot Coexist

The contradiction is in `wsgi_app` (lines 1312-1344):

```python
def wsgi_app(self, environ, start_response):
    ctx = self.request_context(environ)  # Line 1320
    error: BaseException | None = None
    try:
        try:
            ctx.push()                     # Line 1324 — context becomes valid HERE
            response = self.full_dispatch_request(ctx)
```

**The fatal sequence:**
1. Middleware wrapping `wsgi_app` receives `environ` and `start_response`
2. Middleware can do work BEFORE calling the wrapped app
3. During that window, `request`, `session`, `g` are **undefined or point to stale context**
4. If middleware needs globals, it must run after `ctx.push()`
5. If middleware runs after `ctx.push()`, it cannot intercept **before** context creation

**The trilemma:**
- If middleware sees valid globals → it cannot short-circuit before expensive context setup
- If middleware can short-circuit → it cannot see valid globals
- If both are true → middleware must be Flask-aware (not WSGI-composable)

## Conservation Law

**Context Visibility × Middleware Interception Depth = Constant**

The deeper middleware intercepts (earlier in the call chain), the less context is available. The more context is available, the less middleware can intercept early.

## Concealment Mechanism

1. **Proxy indirection** (lines 1049-1056): `request`, `session`, `g` added to Jinja globals are proxy objects — the indirection hides *when* they're valid, making invalid access fail at runtime rather than at definition.

2. **Signature-mismatch wrappers** (lines 56-84): `remove_ctx` and `add_ctx` silently adapt between old and new method signatures, hiding that context is threaded through explicitly in some paths and implicitly in others.

3. **Exception-based routing** (lines 432-454): `raise_routing_exception` uses control-flow exceptions, concealing that routing decisions happen during a window when context validity is ambiguous.

4. **Deferred error collection** (lines 1214-1235): `_CollectErrors()` in teardown callbacks accumulates errors silently, deferring their visibility past the context lifetime.

## Improvement That Recreates the Problem Deeper

**Proposed fix:** Pass context explicitly to middleware via environ:

```python
environ['flask.context'] = ctx  # Make context available to middleware
```

**How it recreates the problem:**
1. Now middleware must know to look for `flask.context` — coupled to Flask internals
2. Middleware that doesn't know about this key sees nothing — partial visibility
3. Non-Flask WSGI middleware still sees stale/invalid proxies — the original problem persists for anything not Flask-aware

The fix trades **universal composability** for **Flask-aware composability**, recreating the same exclusion at a deeper layer.

---

# PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | Source/Verification |
|-------|---------------|------------|---------------------|
| Global proxy access via `_cv_app` | SAFE | 1.0 | Lines 31-35, 960, 1013-1015 |
| Middleware composability promised | SAFE | 1.0 | Lines 1295-1310 docstring |
| Request isolation via AppContext | SAFE | 1.0 | Lines 1320-1344, push/pop pattern |
| Middleware sees invalid globals before ctx.push() | SAFE | 1.0 | Lines 1320-1324 sequence |
| Signature wrappers conceal context threading | SAFE | 1.0 | Lines 56-84, 269-304 |
| Proxy indirection hides validity window | SAFE | 1.0 | Lines 1049-1056 |
| Exception-based routing control flow | SAFE | 1.0 | Lines 432-454 |
| `_CollectErrors` defers errors | SAFE | 1.0 | Lines 1214-1235 |
| Conservation law form | SAFE | 1.0 | Logical derivation from code structure |
| Explicit fix recreates problem | SAFE | 0.9 | Structural prediction from WSGI protocol constraints |

**All claims are STRUCTURAL** — derivable from source code alone.

---

# PHASE 3 — SELF-CORRECTION

No claims flagged as CONFABULATED or confidence < 0.5.

One claim at 0.9 confidence ("explicit fix recreates problem") is a structural prediction. Verification: Any mechanism that makes context visible to middleware either (a) couples middleware to Flask internals, breaking WSGI composability, or (b) pushes context earlier, eliminating short-circuit capability. This is derivable from the protocol structure.

---

# FINAL OUTPUT

## Conservation Law

**Context Visibility × Middleware Interception Depth = Constant**

## Corrected Defect Table

| # | Location | Defect | Severity | Type |
|---|----------|--------|----------|------|
| 1 | Lines 1320-1324 | **Context validity gap** — any code between `wsgi_app` entry and `ctx.push()` sees invalid/stale globals. Middleware wrapping `wsgi_app` executes in this gap. | HIGH | Structural |
| 2 | Lines 56-84 | **Silent signature adaptation** — `remove_ctx`/`add_ctx` wrap methods without caller awareness, making context flow invisible in stack traces. | MEDIUM | Structural |
| 3 | Lines 432-454 | **Exception-based routing** — `raise_routing_exception` uses exceptions for control flow during context ambiguity window, complicating error handling. | MEDIUM | Structural |
| 4 | Lines 1049-1056 | **Proxy validity hidden** — `request`, `session`, `g` proxies fail at access time, not at definition, delaying error discovery. | MEDIUM | Structural |
| 5 | Lines 1214-1235 | **Deferred teardown errors** — `_CollectErrors()` silently collects teardown errors, potentially hiding failures until after context is invalid. | LOW | Structural |
| 6 | Lines 269-304 | **Subclass signature trap** — `__init_subclass__` wraps mismatched signatures with deprecation warning, but the wrapper is applied silently at class definition time. | LOW | Structural |
| 7 | Line 1320 | **Context creation before validation** — `request_context(environ)` creates context from unvalidated environ; malicious environ could inject bad state before any check. | MEDIUM | Structural |
| 8 | Lines 460-470 | **Handler lookup during exception** — `_find_error_handler` called during exception handling; if handler lookup itself fails, no fallback exists. | LOW | Structural |
