# L12 Structural Analysis: Starlette routing.py

## PHASE 1 — STRUCTURAL ANALYSIS

### Three Properties This Code Simultaneously Claims

1. **Isolated Route Matching** — Each route independently evaluates `matches(scope)` and returns a discrete Match state (NONE/PARTIAL/FULL) without side effects
2. **Compositional Scope Accumulation** — Child scopes merge into parent via `scope.update(child_scope)`, enabling nested routing with propagated context
3. **Deterministic Dispatch Priority** — First FULL match wins; if none, first PARTIAL wins; else default handler

### Proof They Cannot Coexist

**The contradiction:** Scope accumulation (Property 2) violates isolation (Property 1).

Examine `Router.app()` lines 285-299:
```python
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match is Match.FULL:
        scope.update(child_scope)  # MUTATION
        await route.handle(scope, receive, send)
        return
```

Now examine nested routing via `Mount.matches()` lines 204-220:
```python
child_scope = {
    "path_params": path_params,
    "root_path": root_path + matched_path,  # ACCUMULATES
    "endpoint": self.app,
}
```

**The impossibility:** A nested Router's route matching depends on `scope["path_params"]` (line 173: `path_params = dict(scope.get("path_params", {}))`). But `path_params` was mutated by the parent Mount. Therefore:

- Route A at `/api/users/{id}` mounted at `/api` sees `path_params = {"id": "123"}` 
- The SAME Route A class instantiated directly at `/users/{id}` sees `path_params = {"id": "123"}`

But the `root_path` differs (`/api` vs `""`), affecting `url_path_for` reconstruction (line 234 uses `app_root_path`). The route's match decision is **not isolated** — it depends on invisible ancestor state.

### Conservation Law

**Composition Depth × Debugging Predictability = Constant**

| Depth | Predictability | Evidence |
|-------|---------------|----------|
| 1 (flat Router) | High | Single loop, visible scope |
| 2 (Router→Mount→Router) | Medium | Scope accumulates across 2 boundaries |
| 3+ | Low | `root_path` + `path_params` + `app_root_path` chain invisibly |

### Concealment Mechanism

**In-place scope mutation disguises state flow.**

Lines 177, 219, 290 all use `scope.update(child_scope)` — a **destructive merge** that overwrites parent state. The original scope is unrecoverable. This conceals:
- Which layer added which path_params
- Whether `endpoint` was set by current route or inherited
- The difference between "no match" and "match with empty params"

### Improvement That Recreates The Problem Deeper

**Proposed fix:** Immutable scope threading with explicit accumulation:

```python
# Instead of scope.update(child_scope)
merged_scope = {**scope, **child_scope}  # Non-destructive
await route.handle(merged_scope, receive, send)
```

**Why this recreates the problem:** Now each layer has perfect visibility into its inputs. But:
- Memory grows O(depth) per request
- Debuggers must trace the full chain
- The **question** "what changed at this layer?" is answered, but **new question** emerges: "which layer's change caused this bug?"

The conservation law manifests differently: **Visibility × Traceability = Constant**

---

## PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | If Wrong, What Changes |
|-------|---------------|------------|------------------------|
| Routes evaluate `matches(scope)` independently | **STRUCTURAL** [VERIFY: source:173-180] | 1.0 | N/A |
| `scope.update(child_scope)` mutates in-place | **STRUCTURAL** [VERIFY: source:177, 219, 290] | 1.0 | N/A |
| Nested routing depends on accumulated path_params | **STRUCTURAL** [VERIFY: source:173 `scope.get("path_params", {})`] | 1.0 | N/A |
| First FULL match wins | **STRUCTURAL** [VERIFY: source:290-293] | 1.0 | N/A |
| PARTIAL used for method mismatch | **STRUCTURAL** [VERIFY: source:178 returns PARTIAL when method not in self.methods] | 1.0 | N/A |
| Mount adds `root_path` accumulation | **STRUCTURAL** [VERIFY: source:215 `root_path + matched_path`] | 1.0 | N/A |
| Conservation law form (Depth × Predictability) | **DERIVATION** [VERIFY: logical inference from mutation chain] | 0.85 | Might be different variable pair |
| `url_path_for` affected by root_path | **STRUCTURAL** [VERIFY: source:234 uses `app_root_path`] | 1.0 | N/A |
| Immutable scope would increase memory O(depth) | **CONTEXTUAL** [depends on Python dict copy behavior] | 0.9 | If dict sharing optimized, cost is O(1) |
| "Isolation" is the claimed property | **STRUCTURAL** [VERIFY: source:285-299 loop design shows intent] | 0.8 | Alternate framing: "modularity" |
| Improvement recreates problem at deeper level | **DERIVATION** [VERIFY: conservation law transfer principle] | 0.75 | Might not transfer; could be different defect class |

---

## PHASE 3 — SELF-CORRECTION

**Revision of low-confidence claims:**

1. **"Isolation" framing** (0.8 → **STRUCTURAL**): The loop design at lines 285-299 shows each route receives the same `scope` input before mutation. The *intent* is isolation. The *reality* is isolation-violated-by-mutation. [VERIFY: source:285-299]

2. **Conservation law form** (0.85 → **STRUCTURAL DERIVATION**): The relationship is derivable: more composition layers = more scope fields = more state to track = less predictability. Form is `Depth × Predictability = k`. [VERIFY: derivation from scope accumulation pattern]

3. **Immutable scope memory cost** (0.9 → **CONTEXTUAL, DOWNGRADED**): Python dict merging with `{**scope, **child_scope}` creates new dict. Cost is O(keys) not O(depth) per se. But if scopes grow with depth (they do — `root_path`, `path_params` accumulate), then cost IS O(depth × avg_keys). [VERIFY: derivation + Python semantics]

4. **Improvement recreates problem** (0.75 → **REVISED**): The improvement changes the **concealment mechanism** from "invisible mutation" to "invisible history." The defect migrates from "can't see what changed" to "can't find where it changed." [VERIFY: derivation from conservation law]

---

## FINAL OUTPUT

### Conservation Law
**Composition Depth × Debugging Predictability = Constant**

### Corrected Defect Table

| # | Defect | Location | Severity | Class | Verification |
|---|--------|----------|----------|-------|--------------|
| 1 | **Destructive scope merge** — `scope.update(child_scope)` loses parent state | Lines 177, 219, 290 | High | Structural | [VERIFY: source:177, source:219, source:290] |
| 2 | **Path parameter provenance lost** — Cannot determine which layer added a param | Line 173 `path_params.update(matched_params)` | Medium | Structural | [VERIFY: source:173] |
| 3 | **Partial match scope capture** — PARTIAL match scope saved but not validated for consistency | Lines 296-299 | Medium | Structural | [VERIFY: source:296-299] |
| 4 | **Root path vs app_root_path confusion** — Two similar fields, different semantics, easy to misuse | Lines 214-215 | Low | Structural | [VERIFY: source:214-215] |
| 5 | **Mount path regex appends `{path:path}` unconditionally** — Creates capture even for static mounts | Line 197 | Low | Structural | [VERIFY: source:197] |
| 6 | **URL generation reversibility assumption** — `url_path_for` assumes unique naming across mount hierarchy | Lines 224-240 | Medium | Structural | [VERIFY: source:224-240] |
| 7 | **Middleware reversal creates hidden ordering** — `reversed(middleware)` means declaration order ≠ execution order | Lines 160-161, 187-188 | Medium | Structural | [VERIFY: source:160-161] |
| 8 | **Lifespan deprecation path uses asynccontextmanager without import** — Relies on caller having imported | Lines 261-263 | Low | Contextual | [VERIFY: source:261-263, requires import verification] |

### Meta-Conservation Law (from applying diagnostic to own output)
**Analysis Visibility × Analyst Blindness = Constant**

This analysis conceals: runtime performance characteristics, thread-safety of scope mutation under concurrent requests, and the legitimate design rationale for mutation (avoiding copy overhead on hot path).
