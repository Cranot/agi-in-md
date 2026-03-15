# L12G Structural Analysis: Starlette routing.py

## PHASE 1 — STRUCTURAL ANALYSIS

### Three Properties This Code Claims

1. **Uniform match semantics** — `Match` enum (NONE/PARTIAL/FULL) applies consistently; PARTIAL means "path matched, method didn't"
2. **Method-safe dispatch** — Routes declare methods; handlers only receive matching requests
3. **Route order independence** — Loop tries all routes; first FULL wins; partials collected fairly

### Proof They Cannot Coexist

```python
# Router.app, lines 453-462
partial = None
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match is Match.FULL:
        scope.update(child_scope)
        await route.handle(scope, receive, send)
        return
    elif match is Match.PARTIAL and partial is None:  # ← ONLY FIRST
        partial = route
        partial_scope = child_scope
```

**The conflict:**
- Route A: `/users` methods=[GET, POST]  
- Route B: `/users` methods=[DELETE, PUT]
- Request: `PATCH /users`

What happens:
1. Route A matches PARTIAL (path ✓, method ✗) → stored as `partial`
2. Route B matches PARTIAL → **ignored** (`partial is not None`)
3. Route A's handler called with PATCH request
4. Route A's handler never declared PATCH → undefined behavior

**Route order determines which wrong handler runs.** Method checking is decorative — the first partial's handler executes regardless.

### Conservation Law

```
Dispatch Simplicity × Method Correctness = constant
```

First-wins is O(n) and simple, but violates HTTP semantics. Collecting all partials to build correct 405 with Allow header is O(n) but semantically correct. You cannot have both minimal dispatch logic AND correct method handling.

### Concealment Mechanism

`Match.PARTIAL` sounds like "partial success, needs graceful handling" but actually means **"total failure, but we'll call a handler anyway."** The enum creates an illusion of semantic precision while the dispatch logic ignores it.

### Improvement That Recreates The Problem

```python
# "Fix" — return 405 for partial matches
if partial is not None:
    if scope["method"] not in partial.methods:
        allowed = ", ".join(sorted(partial.methods))
        response = PlainTextResponse("Method Not Allowed", 405)
        response.headers["Allow"] = allowed  # ← INCOMPLETE!
        await response(scope, receive, send)
        return
```

This "fixes" method dispatch but **recreates the problem deeper:** the Allow header only lists the first partial route's methods. Client sees `Allow: GET, POST` when `DELETE, PUT` are also valid. First-wins semantics now corrupts HTTP compliance.

---

## PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | If Wrong |
|-------|---------------|------------|----------|
| Only first PARTIAL stored | STRUCTURAL (line 458: `partial is None`) | 1.0 | — |
| Partial handler called unconditionally | STRUCTURAL (line 463: `partial.handle()`) | 1.0 | — |
| Route.handle has no method awareness | STRUCTURAL (lines 347-348) | 1.0 | — |
| First-wins violates HTTP 405 semantics | CONTEXTUAL (RFC 7231) | 0.95 | Would still be a design flaw |
| Mount reserves "path" param name | STRUCTURAL (line 375: `{path:path}`) | 1.0 | — |
| Shallow copy in redirect_scope | STRUCTURAL (line 468: `dict(scope)`) | 1.0 | — |
| Shallow copy causes current bugs | UNVERIFIABLE | — | Removing |

---

## PHASE 3 — SELF-CORRECTION

**Removed:** "Shallow copy causes bugs" — no mutation path exists in current code. Fragile but not currently broken.

**Verified:** All remaining claims trace to specific lines. The impossibility proof is structurally complete: first-wins dispatch + method-specific routes + HTTP compliance = pick two.

---

## FINAL OUTPUT

### Conservation Law
```
Dispatch Simplicity × Method Correctness = constant
```

### Defect Table (SAFE + Verified Only)

| # | Location | Defect | Severity | Class |
|---|----------|--------|----------|-------|
| 1 | Router.app:458 | First PARTIAL wins; subsequent partials ignored. Multiple routes for same path with different methods → wrong handler for undeclared methods. | **High** | Structural |
| 2 | Router.app:463 | Partial handler called without method validation. Endpoint receives requests for methods it never declared. | **High** | Structural |
| 3 | Route.handle:347-348 | No method awareness. Forwards all requests to `self.app` regardless of match type. | Medium | Structural |
| 4 | Mount.__init__:375 | Forces `{path:path}` parameter. User routes with `{path}` param name collide with internal capture. "path" is effectively reserved. | Medium | Structural |
| 5 | Mount.url_path_for:398-399 | Asymmetric path handling: `lstrip("/")` on reversal vs `"/" + pop()` on match. Works for common cases but assumption-laden. | Low | Structural |
| 6 | compile_path:50-52 | `duplicated_params` check catches same-name params in ONE route, but cannot catch cross-mount collisions (Mount's forced `path` + user's `path`). | Low | Structural |
