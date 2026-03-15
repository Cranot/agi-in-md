# Structural Analysis: Starlette routing.py

## Conservation Laws

### Primary Law: Scope Accumulation
```
Σ(path_params updates) × Routing Depth = Information at Handler
```

Every `scope.update(child_scope)` adds keys monotonically. The handler receives the **sum of all routing decisions**. Information flows one direction: in.

**Evidence:**
- `Route.matches()`: `path_params.update(matched_params)` — merges, never replaces
- `Mount.matches()`: builds `child_scope` with merged `path_params` from parent
- `Router.app()`: `scope.update(child_scope)` — mutates global scope

### Secondary Law: Match Exclusivity
```
FULL matches ≤ 1 (first wins)
PARTIAL captures first only (silent discard of rest)
```

**The code:**
```python
elif match is Match.PARTIAL and partial is None:
    partial = route  # ONLY first captured
```

Multiple PARTIAL matches exist; only one is remembered. Information about alternatives is destroyed.

### Tertiary Law: Error Asymmetry
```
HTTP routing failure → 404 response (visible)
WebSocket routing failure → silent close (invisible)
```

Same root cause (no matching route), different information preserved.

---

## Defects

| Location | Severity | Type | Description |
|----------|----------|------|-------------|
| L52-58 | **Medium** | Shadowing | `request_response` defines nested `async def app` that shadows outer `app`. Works via closure, but outer params unused. |
| L66-71 | **High** | Hidden Mutation | `replace_params()` mutates `path_params.pop(key)` — caller's dictionary modified. Callers depend on this side effect. |
| L180-182 | **Medium** | Logic Gap | `partial` captures only FIRST partial match. Overlapping method-restricted routes silently ignored. |
| L194-206 | **High** | Incomplete Copy | `redirect_slashes` creates shallow scope copy, modifies `path`, but path-derived values (if any) stale. Also: redirects on `not Match.NONE` without verifying FULL match exists. |
| L94-97 | **Low** | Silent Failure | WebSocket close on no match sends no diagnostic info. Routing debugging impossible. |
| L152 | **Medium** | Implicit Invariant | Mount compiles `self.path + "/{path:path}"` but stores original `self.path`. Relationship between them is undocumented convention. |
| L163-165 | **Medium** | Duck-typed Access | `Mount.routes` property uses `getattr(self._base_app, "routes", [])` — silently returns empty if wrapped app has no routes. |

### Critical Bug: The `request_response` Nesting

```python
async def app(scope, receive, send):           # OUTER
    request = Request(scope, receive, send)
    
    async def app(scope, receive, send):       # INNER — SHADOWS
        response = await f(request)            # closes over outer's request
        await response(scope, receive, send)
    
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
```

The outer `app` receives `(scope, receive, send)` but passes them to the INNER `app` via the closure. The outer parameters are unused. This is **correct but structurally confusing** — the same name means two different functions in the same lexical scope.

---

## Concealment Mechanisms

### 1. Middleware Burial
```python
for cls, args, kwargs in reversed(middleware):
    self.app = cls(self.app, *args, **kwargs)
```

After wrapping, `self.app` is N layers deep. Original endpoint is archaeologically buried. Debugging requires manual unwrapping.

### 2. Scope Fragment Merging
```python
match, child_scope = route.matches(scope)
# ... later ...
scope.update(child_scope)
```

`matches()` returns a **partial scope** that MUST be merged. New route types that forget this call silently fail. The contract is implicit.

### 3. Endpoint Unwrapping Incompleteness
```python
while isinstance(endpoint_handler, functools.partial):
    endpoint_handler = endpoint_handler.func
```

Handles `functools.partial` but not:
- Class instances with `__call__`
- Decorator chains
- Lambda wrappers

The "is this a function?" heuristic is partial.

### 4. Mount Routes Property Hides Wrapping
```python
@property
def routes(self):
    return getattr(self._base_app, "routes", [])
```

If Mount wraps a raw ASGI app (not a Router), `routes` returns `[]` — falsy but valid. Callers can't distinguish "no routes" from "wrapped app has no routes attribute".

### 5. Convertor Assumption
```python
matched_params[key] = self.param_convertors[key].convert(value)
```

Assumes `key` exists in `param_convertors`. If regex captures a param not in convertors dict, KeyError. No defensive check.

---

## The Deepest Pattern

**What the code pretends to be:** Simple path matching with handlers.

**What the code actually is:** A recursive descent parser with:
- State machine (NONE → PARTIAL → FULL)
- Middleware composition (decorator pattern)
- Scope accumulation (monotonic growth)
- Implicit contracts between BaseRoute subclasses and Router

**The state machine is never declared — it emerges from:**
1. `Match` enum (states)
2. `matches()` methods (transitions)
3. `Router.app()` dispatch logic (state handler)

This is **correct by convention** but fragile to extension.

---

## Structural vs Fixable Classification

| Defect | Classification | Why |
|-------|----------------|-----|
| Nested `app` shadowing | **Structural** | Requires redesign of `request_response` |
| `replace_params` mutation | **Fixable** | Copy dict at entry |
| PARTIAL first-only | **Fixable** | Collect all PARTIALs, apply priority |
| Redirect scope incomplete | **Fixable** | Re-derive all path-related values |
| WebSocket silent close | **Fixable** | Add close code/reason |
| Middleware burial | **Structural** | Inherent to wrapping pattern |
| Scope fragment contract | **Structural** | Requires explicit interface |

---

## Meta-Observation

This file demonstrates **conservation of complexity**: the apparent simplicity of `Route(path, endpoint)` is achieved by pushing complexity into:
1. Implicit scope mutation
2. Hidden middleware layers  
3. Undeclared state machine
4. Asymmetric error handling

The code is **correct** but the structure **conceals its own operation**. A reader must trace execution to understand what `scope` contains at any point — it's not derivable from local inspection.
