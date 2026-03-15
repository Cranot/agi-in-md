# L12g Structural Analysis: Starlette routing.py

## PHASE 1 — STRUCTURAL ANALYSIS

### Three Properties This Code Simultaneously Claims

1. **Hierarchical Composition** — `Mount` nests routers/apps, each with isolated path space
2. **Uniform Matching Semantics** — All routes return `Match` enum (NONE/PARTIAL/FULL)
3. **Transparent URL Reversal** — `url_path_for()` reconstructs URLs across nesting boundaries

### Proof These Cannot Coexist

**The contradiction lives in `Mount.matches()` vs `Route.matches()`:**

```python
# Route.matches (lines 119-131): returns PARTIAL for method mismatch
if self.methods and scope["method"] not in self.methods:
    return Match.PARTIAL, child_scope

# Mount.matches (lines 149-165): NEVER returns PARTIAL
if match:
    # ... builds child_scope ...
    return Match.FULL, child_scope
return Match.NONE, {}
```

Mount's path regex is `self.path + "/{path:path}"` — a catch-all that captures everything after the mount point. Mount cannot know if a child route will partially match (wrong method) because it delegates to `self.app` in `handle()`, not in `matches()`.

**Consequence:** A request to `Mount(path="/api", routes=[Route("/users", methods=["GET"])])` for `POST /api/users`:
- Mount returns `Match.FULL` (path matched)
- Router dispatches to Mount
- Mount's internal Router finds no FULL match
- Falls through to `default` handler → 404

But semantically, this should be **405 Method Not Allowed** (the resource exists, method is wrong). Mount swallowed the PARTIAL signal.

### Conservation Law

**Matching Precision × Composition Depth = Constant**

| Composition Level | Matching Precision | What's Lost |
|-------------------|-------------------|-------------|
| Flat routes | FULL + PARTIAL + NONE | No nesting |
| One Mount deep | FULL + NONE at boundary | PARTIAL swallowed |
| N Mounts deep | FULL + NONE only | All PARTIAL signals lost |

### Concealment Mechanism

**The `Match` enum is a false uniformity.** The code *appears* to use consistent matching semantics across all route types, but:

1. `Route.matches()` uses all three values
2. `Mount.matches()` only uses TWO values
3. The type system (Enum) hides this — all returns are type-compatible

The API contract promises `Match` but the behavioral contract differs by class. This is **syntactic uniformity masking semantic divergence**.

### Improvement That Recreates The Problem Deeper

**Proposed fix:** Mount eagerly evaluates child routes in `matches()`:

```python
def matches(self, scope):
    # ... existing path matching ...
    if match:
        # NEW: Check if any child would PARTIAL match
        child_scope["path"] = remaining_path
        for child_route in self.routes:
            child_match, _ = child_route.matches(child_scope)
            if child_match == Match.PARTIAL:
                return Match.PARTIAL, child_scope  # Propagate!
        return Match.FULL, child_scope
```

**New problem created:** This requires Mount to know about `self.routes`, but Mount can wrap any ASGI app (not just Routers). The fix assumes `_base_app` has `.routes` — breaking the `app=` use case where Mount wraps a foreign application.

**Meta-conservation law:** Propagation Completeness × Encapsulation = Constant

---

## PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | Source/Verification |
|-------|----------------|------------|---------------------|
| Mount.matches never returns PARTIAL | STRUCTURAL | 1.0 | Lines 149-165: exhaustive case analysis shows only FULL/NONE returns |
| Route.matches returns PARTIAL for method mismatch | STRUCTURAL | 1.0 | Lines 128-129: explicit `return Match.PARTIAL, child_scope` |
| Mount path regex is `self.path + "/{path:path}"` | STRUCTURAL | 1.0 | Line 145: `compile_path(self.path + "/{path:path}")` |
| POST to mounted route returns 404 not 405 | CONTEXTUAL | 0.7 | Requires tracing Router.app dispatch logic + HTTP semantics |
| Mount can wrap any ASGI app | STRUCTURAL | 1.0 | Line 137: `self._base_app = app` with no type constraint |
| Improvement would break `app=` case | STRUCTURAL | 0.9 | Line 158: `self.routes` returns empty list for non-Router apps |
| get_route_path behavior in redirect | CONTEXTUAL | 0.3 | Function not defined in provided source |
| request_response inner function shadows outer | STRUCTURAL | 1.0 | Lines 21-29: two `async def app` definitions, inner shadows outer |

**Non-structural claims requiring revision:**

- **405 vs 404 claim (0.7)**: I inferred the HTTP status code from the dispatch flow, but `not_found` explicitly sets 404. The claim about semantic correctness (should be 405) is contextual — depends on HTTP RFC interpretation.

- **get_route_path (0.3)**: This function is called but not defined in the source. Cannot verify redirect logic correctness without it.

---

## PHASE 3 — SELF-CORRECTION

### Removed/Revised Claims

| Original Claim | Status | Reason |
|----------------|--------|--------|
| POST to mounted route should return 405 | **REVISED TO QUALIFIED** | STRUCTURAL: Router.app falls through to `self.default` (line 259). CONTEXTUAL: Whether this is "wrong" depends on HTTP interpretation. The *behavior* is verifiable; the *correctness* is contextual. |
| Redirect logic correctness | **UNVERIFIABLE** | `get_route_path()` not in source — removed from defect table |

### Corrected Defect Table (SAFE + Verified Only)

| Location | Defect | Severity | Classification |
|----------|--------|----------|----------------|
| Lines 149-165 | `Mount.matches()` never returns `Match.PARTIAL`, losing method-mismatch signals from nested routes | **STRUCTURAL** | MEDIUM — API inconsistency, semantic information loss |
| Lines 21-29 | `request_response()` defines nested `async def app` shadowing outer `async def app` | **STRUCTURAL** | LOW — works by closure semantics but confusing |
| Lines 168-186 | `Mount.url_path_for()` with `name=None` bypasses namespace isolation — passes all requests to children without prefix check | **STRUCTURAL** | MEDIUM — unnamed mounts provide no encapsulation |
| Lines 207 vs 218 | `Router.app()` asserts scope type but `Router.__call__()` passes to middleware without assertion | **STRUCTURAL** | LOW — potential inconsistency if middleware doesn't handle all types |
| Line 145 | Mount's catch-all regex `{path:path}` prevents Mount from doing partial path matching | **STRUCTURAL** | MEDIUM — design limitation, not bug |

---

## FINAL OUTPUT

### Conservation Law
**Matching Precision × Composition Depth = Constant**

Deeper route composition trades away matching granularity. Each `Mount` boundary is a precision loss point where `PARTIAL` signals dissolve into `FULL` (path matched) or `NONE` (no handler found).

### Defect Table (Source-Grounded Only)

| # | Location | Defect | Fixable? |
|---|----------|--------|----------|
| 1 | L149-165 | Mount.matches() swallows PARTIAL signals — mounted routes with method constraints return 404 instead of semantically correct status | **Structural** — requires API redesign |
| 2 | L168-186 | Unnamed Mounts (`name=None`) provide no namespace isolation — all url_path_for requests pass through | **Fixable** — document or enforce name requirement |
| 3 | L21-29 | Shadowed function name `app` in `request_response` | **Fixable** — rename inner function |
| 4 | L145 | Mount catch-all regex prevents partial path matching at mount boundaries | **Structural** — inherent to design |
| 5 | L207/218 | Inconsistent scope type assertion between `app()` and `__call__()` | **Fixable** — add assertion or document difference |

### Hidden Assumptions Exposed

1. **All ASGI apps are not equal** — Mount assumes `_base_app.routes` exists for some operations but accepts any callable
2. **Match enum is advisory** — PARTIAL exists but Mount ignores it; the type system doesn't enforce usage
3. **Names provide isolation** — but only if you use them; `name=None` is a silent escape hatch
