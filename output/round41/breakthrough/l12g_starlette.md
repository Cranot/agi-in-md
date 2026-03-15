# PHASE 1 — STRUCTURAL ANALYSIS

## Three Properties Claimed (That Cannot Coexist)

**Property A: Request-Scope Unity**
The `Request` object and the `scope` passed downstream represent the same request state.

**Property B: Wrapper Transparency**  
`wrap_app_handling_exceptions` can intercept and potentially modify ASGI parameters before they reach the handler.

**Property C: Closure-Parameter Consistency**
The inner handler's closure-captured `request` and its received `scope/receive/send` parameters are interchangeable.

---

## Proof of Non-Coexistence

```python
def request_response(func):
    f = func if is_async_callable(func) else functools.partial(run_in_threadpool, func)

    async def app(scope, receive, send):           # OUTER: receives (A)
        request = Request(scope, receive, send)    # Request wraps (A)

        async def app(scope, receive, send):       # INNER: receives (B) — SHADOWS OUTER
            response = await f(request)            # Uses Request(A)
            await response(scope, receive, send)   # Passes (B) to response

        await wrap_app_handling_exceptions(app, request)(scope, receive, send)

    return app
```

**Contradiction chain:**
1. Request is constructed from **scope_A** (outer function parameters)
2. Inner function is defined, capturing `request` in its closure
3. `wrap_app_handling_exceptions` is called and may invoke inner function with **scope_B**
4. Handler `f` receives `request` (built from scope_A)
5. Response receives `scope` (which is scope_B)
6. **If scope_A ≠ scope_B → Request.state ≠ scope["state"], Request.path ≠ scope["path"], etc.**

Properties A and B cannot coexist if C is implemented as shown.

---

## Conservation Law

```
request_creation_point × scope_modification_depth = constant
```

**Meaning:** The earlier Request is instantiated (higher ×), the fewer scope modifications can safely occur (lower depth) without creating divergence. This code instantiates Request at depth=0, permitting ZERO downstream modifications.

---

## Concealment Mechanism

1. **Variable shadowing**: Inner `async def app` shadows outer `async def app`, obscuring the boundary
2. **Closure invisibility**: The captured `request` appears to be "the" request, masking that it's bound to stale scope
3. **Latent failure mode**: If `wrap_app_handling_exceptions` passes unmodified parameters, the bug is dormant

---

## Engineered "Improvement" That Recreates The Problem Deeper

```python
# "Fix" that makes it worse:
async def app(scope, receive, send):
    request = Request(scope, receive, send)
    request._scope_snapshot = dict(scope)  # "Cache" for "performance"
    
    async def handler(s, r, t):  # Renamed for "clarity"
        # Now response uses BOTH snapshot AND incoming scope
        merged_scope = {**request._scope_snapshot, **s}
        response = await f(request)  # Still uses original request
        await response(merged_scope, r, t)  # Mutated scope passed down
```

This "improvement" creates a third scope variant (merged), making the inconsistency harder to debug but still present.

---

# PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | Verification Path |
|-------|---------------|------------|-------------------|
| Variable `app` shadows outer `app` | **STRUCTURAL** | 1.0 | Lines 28-35: two `async def app` definitions, one nested |
| Request created from outer scope params | **STRUCTURAL** | 1.0 | Line 29: `Request(scope, receive, send)` uses outer function params |
| Inner function receives potentially different params | **STRUCTURAL** | 1.0 | Line 35: `wrap_app_handling_exceptions(app, request)(scope, receive, send)` |
| `wrap_app_handling_exceptions` may modify scope | **CONTEXTUAL** | 0.3 | Function not defined in provided source |
| Request-scope divergence causes bugs | **CONFABULATED** | 0.4 | Depends on whether wrapper actually modifies scope |
| Mount appends `/{path:path}` synthetically | **STRUCTURAL** | 1.0 | Line 152: `compile_path(self.path + "/{path:path}")` |
| `path_params` mutation in `url_path_for` | **STRUCTURAL** | 1.0 | Line 186: `path_params["path"] = ""` |

---

# PHASE 3 — SELF-CORRECTION

## Claims Removed (UNVERIFIABLE)

1. **"`wrap_app_handling_exceptions` may modify scope"** → UNVERIFIABLE (function not in source)
2. **"This causes runtime bugs"** → UNVERIFIABLE (depends on external behavior)

## Revised Claim: Scope Divergence *Potential*

The code creates the **structural preconditions** for scope divergence:
- Request bound to outer scope
- Inner handler receives potentially different scope  
- Whether divergence manifests depends on external code

---

# FINAL OUTPUT

## Conservation Law

```
request_instantiation_depth × permissible_scope_mutations = 0
```

Request is instantiated at the outermost layer; any downstream mutation creates latent inconsistency.

---

## Corrected Defect Table

| Defect | Location | Evidence | Severity |
|--------|----------|----------|----------|
| **Variable shadowing** | Lines 28-35 | Inner `async def app` shadows outer `async def app` | Medium (readability hazard) |
| **Scope binding mismatch** | Lines 29-33 | Request bound to outer scope; inner function receives different scope parameters | Low (dormant unless wrapper mutates) |
| **Parameter ignored in closure** | Line 32 | `f(request)` uses closure variable, not parameters | Low (ASGI typically passes same values) |
| **Synthetic path parameter** | Line 152 | Mount injects `{path:path}` into param_convertors without user specification | Informational (by design) |
| **Input mutation** | Line 186 | `path_params["path"] = ""` mutates caller's dict | Low (restored before return) |

---

## Source-Grounded Findings Only

1. **Variable shadowing exists** — two functions named `app` at different scopes (lines 28, 31)
2. **Request is bound to outer parameters** — created before wrapper is invoked (line 29)
3. **Mount synthesizes path parameter** — `{path:path}` appended to all mount paths (line 152)
4. **Path params dict is mutated** — temporary overwrite of `path` key (line 186)
