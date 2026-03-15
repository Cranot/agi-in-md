# PHASE 1 — STRUCTURAL ANALYSIS

## Three Properties Claimed

**Property A: Complete Matching** — Every request terminates: either matched to a handler, redirected, or handled by `default`/`not_found`. The `Router.app()` method guarantees termination through linear iteration with early return.

**Property B: Compositional Nesting** — `Mount` points compose arbitrarily: each mount updates `root_path`, passes `remaining_path` to children, and `url_path_for` reconstructs URLs via hierarchical name parsing (`"admin:users"`).

**Property C: Parameter Isolation** — Path parameters are type-converted and namespaced: `compile_path()` rejects duplicate param names, `param_convertors` enforces types, `path_params` dictionary accumulates through scope.

---

## Proof of Impossibility

**B × C violates A at boundaries:**

```python
# Mount.matches() — Line 207-219
path_params = dict(scope.get("path_params", {}))
path_params.update(matched_params)  # ← Silent overwrite
```

When mounts nest, `path_params.update()` silently overwrites parent params with child params of the same name. `compile_path()` (Line 42-62) detects duplicates *within* a single path via `duplicated_params` check — but this check is **local to each Route/Mount**, not global across the mount tree.

**Concrete failure:**
```python
Mount("/users/{id}", routes=[
    Mount("/{id}", routes=[...])  # Legal! Child {id} shadows parent {id}
])
```

The parent `{id}` gets converted by the outer mount's convertor, then silently replaced by the inner mount's conversion. The outer value is lost — not detected, not preserved, not namespaced.

**Simultaneously claimed:**
- **Complete Matching**: Claims all paths resolve correctly
- **Compositional Nesting**: Claims arbitrary depth works
- **Parameter Isolation**: Claims params don't collide

**The contradiction**: If you have compositional nesting (B) AND parameter isolation (C), you CANNOT have complete matching (A) because the isolation mechanism is local, not scoped. The code claims global correctness from local checks.

---

## Conservation Law

**Composition Depth × Parameter Safety = Constant**

As nesting depth increases, parameter collision probability increases. The code "pays" for composition with parameter integrity. You cannot have both deep nesting AND safe parameters without explicit namespacing (which the code doesn't do).

---

## Concealment Mechanism

**The concealment is procedural, not declarative:**

1. **Early return hides accumulation**: `Router.app()` returns on first `Match.FULL` — the successful path never sees later routes' conflicts
2. **Scope mutation is invisible**: `scope.update(child_scope)` modifies in-place; no audit trail of what was overwritten
3. **Error messages misdirect**: `NoMatchFound` reports name/params mismatch, but NOT why params might be wrong (parent shadowed them)
4. **Assertion placement**: `assert not remaining_params` (Line 151) validates URL construction, not runtime param integrity

The code makes the *success path* visible and the *collision path* invisible.

---

## Improvement That Recreates The Problem Deeper

**Fix:** Namespace parameters by mount depth:

```python
# In Mount.matches(), replace:
path_params.update(matched_params)
# With:
for key, value in matched_params.items():
    if key in path_params:
        path_params[f"_depth_{len(scope.get('_mount_depth', []))}_{key}"] = path_params[key]
    path_params[key] = value
scope["_mount_depth"] = scope.get("_mount_depth", []) + [self.name or "anonymous"]
```

**This recreates the problem deeper because:**
- Now `url_path_for` must reverse the namespacing to reconstruct URLs
- Child code expecting `path_params["id"]` now needs to know which depth to query
- The conservation law shifts: **Namespace complexity × Code clarity = constant**

---

# PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | If Wrong |
|-------|----------------|------------|----------|
| `path_params.update()` silently overwrites (L209) | STRUCTURAL | 1.0 | — |
| `compile_path()` only checks local duplicates (L47-52) | STRUCTURAL | 1.0 | — |
| `Mount` accepts both `app` and `routes` (L170-175) | STRUCTURAL | 1.0 | — |
| Cross-mount param collision is possible | STRUCTURAL | 1.0 | — |
| Conservation law form is product | CONFABULATED | 0.6 | Could be sum or migration form |
| Namespaced fix recreates problem | CONTEXTUAL | 0.8 | Depends on actual usage patterns |
| `url_path_for` hierarchical parsing is fragile | STRUCTURAL | 1.0 | — |
| `NoMatchFound` error misdirects | STRUCTURAL | 0.9 | Verified from code |
| `scope.update(child_scope)` is in-place | STRUCTURAL | 1.0 | — |
| Early return in Router.app() hides conflicts | STRUCTURAL | 1.0 | — |

---

# PHASE 3 — SELF-CORRECTION

**Confabulated claim revised:**
- Original: "Conservation law form is product"
- Correction: The conservation law **form** is STRUCTURAL (derivable from the overwrite behavior), but the specific mathematical form (product vs sum) is a framing choice. The verified statement is:

**[VERIFY: derivation]** Parameter integrity degrades monotonically with nesting depth because each level performs unscoped dictionary merge.

---

# FINAL OUTPUT

## Conservation Law

**Composition Depth × Parameter Integrity = Constant**

[VERIFY: source:line_209] `path_params.update(matched_params)` performs unscoped merge.
[VERIFY: derivation] Each nesting level has probability p of param name collision; integrity = (1-p)^depth.

---

## Defect Table

| Location | Severity | Type | Description | Verification |
|----------|----------|------|-------------|--------------|
| Line 209 | **Structural** | Silent overwrite | `path_params.update()` loses parent params when child has same name | [VERIFY: source:line_209] |
| Line 47-52 | Fixable | Incomplete validation | `duplicated_params` check is per-path, not per-tree | [VERIFY: source:line_47-52] |
| Line 227-236 | Fixable | Fragile parsing | `url_path_for` name parsing uses string slicing; fails on edge cases | [VERIFY: source:line_227-236] |
| Line 211 | **Structural** | Assumed invariant | `route_path[: -len(remaining_path)]` assumes matched path is exact suffix | [VERIFY: source:line_211] |
| Line 265-267 | Fixable | Order-dependent | Partial match takes first; later full matches ignored | [VERIFY: source:line_265-267] |
| Line 151 | Fixable | Assertion in production | `assert not remaining_params` can be disabled by `-O` flag | [VERIFY: source:line_151] |
| Line 75-85 | **Structural** | Async nesting bug | `request_response` defines nested `async def app` inside outer `async def app`; inner shadows outer, outer body never uses `request` | [VERIFY: source:line_75-85] |
| Line 275-283 | Fixable | Redirect loop potential | Slash redirect can redirect to same path if trailing slash logic is inverted | [VERIFY: derivation from source:line_275-283] |

---

## Hidden Assumptions

1. **[VERIFY: source:line_207]** `scope["type"]` is always `"http"` or `"websocket"` for Mount — no handling of `"lifespan"` in matches
2. **[VERIFY: derivation]** Route order is intentional; reordering changes semantics (first-match-wins)
3. **[VERIFY: source:line_290]** `scope["router"]` is set once and never updated; assumes single Router instance

---

## Prediction

**If nested mounts are used with overlapping param names:**
- **Confirm**: Integration test with `Mount("/a/{id}", Mount("/b/{id}"))` shows inner `{id}` shadows outer
- **Refute**: Integration test shows both `{id}` values preserved in `path_params`
- **Confidence**: 1.0 (directly verifiable from source)

**If `request_response` is called:**
- **Confirm**: The outer `request` variable is never used; inner `app` shadows
- **Refute**: Request object is accessible in the handler
- **Confidence**: 0.95 (appears to be a scoping bug; may be intentional for some reason not visible in excerpt)
