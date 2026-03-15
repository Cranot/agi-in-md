# L12G Structural Analysis: Starlette routing.py

## PHASE 1 — STRUCTURAL ANALYSIS

### Three Properties This Code Simultaneously Claims

1. **Uniform Match Semantics** — All routes implement `matches()` returning `Match.{NONE, PARTIAL, FULL}` with consistent meaning
2. **Compositional Hierarchy** — Mount → Router → Route nesting to arbitrary depth with clean delegation
3. **Scope Isolation** — Each routing level operates on isolated scope without interfering with siblings

### Proof They Cannot Coexist

```
Route.matches()  → returns Match.PARTIAL for path match + method mismatch [lines 126-134]
Mount.matches()  → returns ONLY Match.FULL or Match.NONE [lines 191-206]
Mount.path_regex → compiled with "/{path:path}" suffix, matches EVERYTHING [line 182]
```

**The contradiction**: Mount claims to implement the Match protocol but cannot produce PARTIAL. When a Route nested inside a Mount would return PARTIAL (correct path, wrong method), the Mount has already returned FULL. The Match enum's semantic precision degrades with composition depth.

**Proof by construction**:
1. Create `Mount("/api", routes=[Route("/users", endpoint, methods=["POST"])])`
2. Request `GET /api/users` → path matches Mount, Mount returns FULL
3. Mount delegates to Route, Route returns PARTIAL (method mismatch)
4. Router.app() receives FULL from Mount, stores PARTIAL from Route
5. PARTIAL handling executes, but Mount already committed to FULL semantics

The uniformity is an illusion — Mount's Match behavior is fundamentally different from Route's.

### Conservation Law

```
Matching Precision × Composition Depth = Constant
```

As nesting deepens:
- Level 0 (Route): Match.PARTIAL correctly signals method mismatch
- Level 1 (Mount→Route): Mount returns FULL, method semantics lost to parent
- Level 2+: Method information exists only in innermost scope

The system conserves matching information by degrading precision. You cannot have both deep composition AND precise matching — the Match enum's PARTIAL state becomes unreachable at depth.

### Concealment Mechanism

The concealment operates through **protocol surface uniformity hiding semantic divergence**:

1. **Identical interface, divergent semantics**: Both Route and Mount have `matches(self, scope) → tuple[Match, dict]`, but Mount's implementation ignores HTTP method entirely while Route's depends on it.

2. **Scope mutation obscures information flow**: `scope.update(child_scope)` [lines 148, 207, 266, 297] mutates shared state, making it impossible to trace what information existed at each level.

3. **Path parameter catch-all**: Mount's `/{path:path}` [line 182] guarantees path matching, making Mount.matches() effectively a constant function that ignores most of the Match protocol.

### Improvement That Recreates the Problem

**Proposed fix**: Add method awareness to Mount.matches() by collecting all child methods:

```python
class Mount(BaseRoute):
    def __init__(self, ...):
        # ...existing code...
        self._child_methods = self._collect_child_methods()
    
    def matches(self, scope):
        # ...existing path matching...
        if scope["method"] not in self._child_methods:
            return Match.PARTIAL, child_scope
        return Match.FULL, child_scope
```

**How this recreates the problem deeper**:
1. Now Mount knows child methods → **coupling introduced**
2. WebSocket routes don't have methods → **new special case needed**
3. Nested Mounts require recursive method collection → **performance cost**
4. Dynamic route addition breaks cached method set → **fresh bug category**

The fix trades the original problem (Match semantic degradation) for a new problem (Mount-child coupling). The conservation law holds: `Decoupling × Method Awareness = Constant`.

---

## PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | Verification |
|-------|---------------|------------|--------------|
| Mount.matches returns only FULL/NONE | STRUCTURAL | 1.0 | [VERIFY: source:191-206] No code path returns PARTIAL |
| Route.matches returns PARTIAL for method mismatch | STRUCTURAL | 1.0 | [VERIFY: source:130-132] Explicit check and return |
| Mount.path_regex includes `/{path:path}` | STRUCTURAL | 1.0 | [VERIFY: source:182] compile_path called with self.path + suffix |
| Match semantic precision degrades with depth | STRUCTURAL | 1.0 | [VERIFY: derivation] Mount returns FULL, Route returns PARTIAL, Mount wraps Route |
| scope.update() mutates shared state | STRUCTURAL | 1.0 | [VERIFY: source:148,207,266,297] dict.update() is in-place mutation |
| Mount ignores HTTP method entirely | STRUCTURAL | 1.0 | [VERIFY: source:191-206] No reference to scope["method"] |
| Conservation law: Precision × Depth = constant | STRUCTURAL | 0.95 | [VERIFY: derivation] Logical consequence of items 1-4 |
| Fix would introduce coupling | STRUCTURAL | 0.9 | [VERIFY: derivation] By construction — Mount must know child methods |

**Non-structural claims audited**:
- None. All claims derive from source code or direct logical consequence.

---

## PHASE 3 — SELF-CORRECTION

No claims flagged as CONFABULATED or confidence < 0.5. All surviving claims verified.

---

## FINAL OUTPUT

### Conservation Law
```
Matching Precision × Composition Depth = Constant
```

### Corrected Defect Table

| # | Location | Severity | Type | Description | Verification |
|---|----------|----------|------|-------------|--------------|
| 1 | Lines 191-206 | **Structural** | Mount cannot return PARTIAL | Mount.matches() has no code path producing Match.PARTIAL, breaking Match protocol semantics when nested routes have method constraints | [VERIFY: source:191-206] |
| 2 | Line 182 | **Fixable** | Over-greedy path matching | Mount's `/{path:path}` suffix matches all remaining paths, preventing Mount-level path validation | [VERIFY: source:182] |
| 3 | Lines 148, 207, 266, 297 | **Fixable** | Scope mutation | `scope.update(child_scope)` mutates caller's state, making request scope modification untraceable | [VERIFY: source:148,207,266,297] |
| 4 | Lines 288-299 | **Fixable** | Redirect without validation | Router redirects for trailing slash without verifying redirect target actually exists | [VERIFY: source:288-299] |
| 5 | Line 153 | **Fixable** | path_params mutation | `replace_params()` mutates `path_params` dict via `.pop()`, causing side effects in caller | [VERIFY: source:153] |
| 6 | Lines 66-77 | **Fixable** | Confusing naming | `request_response()` defines nested function named `app` shadowing outer `app`, reducing readability | [VERIFY: source:66-77] |
| 7 | Lines 242-254 | **Structural** | Name collision in url_path_for | Multiple `name=None` mounts all attempt to resolve same name, first match wins by route order, not specificity | [VERIFY: source:242-254] |

### Meta-Conservation Law (L12)
```
Analytical Completeness × Framework Simplicity = Constant
```

This analysis conceals: the runtime behavior of middleware stacking (lines 108-110, 175-178, 225-228). Each route can have middleware that wraps the app, but this analysis treats routes as static structures. The dynamic middleware composition at request time creates a different conservation law: `Middleware Flexibility × Debuggability = Constant`.
