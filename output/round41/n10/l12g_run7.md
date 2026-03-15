# PHASE 1 — STRUCTURAL ANALYSIS

## Three Properties This Code Claims

1. **Hierarchical Composition** — Mount objects nest arbitrarily, each adding path prefix and parameters
2. **Uniform ASGI Interface** — Every route/mount/router is callable `(scope, receive, send)`
3. **Independent Level Semantics** — Each route level can be understood and named in isolation

## The Impossibility

Properties 1 + 2 **contradict** Property 3.

Evidence: `scope["path_params"]` is a **flat dict**. Each level calls `path_params.update(matched_params)` (lines 165, 217). By Python dict semantics, inner parameters **silently overwrite** outer parameters with the same name.

If outer Mount defines `{id}` and inner Route also defines `{id}`, the inner wins. Level independence is violated — inner levels must know outer levels' parameter names to avoid collisions.

## Conservation Law

```
Composition_Depth × Parameter_Isolation = constant
```

More nesting = more collision opportunities = less isolation.

## Concealment Mechanism

The `.update()` pattern **appears** to "enrich scope" but actually "potentially overwrite". The hierarchical class structure (Route, Mount, Router) suggests isolation, but runtime state (`scope["path_params"]`) is flat and shared.

## Improvement That Recreates The Problem

Add namespaced parameters: `scope["path_params"][f"L{n}.{key}"]`.

This prevents collisions but breaks `Mount.url_path_for` (lines 229-246), which iterates children with `**remaining_params`. Namespacing requires level-aware parameter transformation — coupling URL generation to tree position, recreating the coupling at a different abstraction layer.

---

# PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | If Wrong |
|-------|---------------|------------|----------|
| Hierarchical Composition exists | STRUCTURAL | 1.0 | N/A |
| Uniform ASGI interface | STRUCTURAL | 1.0 | N/A |
| Independent level semantics | CONTEXTUAL | 0.7 | Conservation law holds but "impossibility" framing weakens |
| `path_params.update()` overwrites | STRUCTURAL | 1.0 | N/A |
| Conservation law form | DERIVATION | 0.85 | Different framing possible |
| `.update()` conceals overwrite | STRUCTURAL | 1.0 | N/A |
| Namespacing fix breaks url_path_for | DERIVATION | 0.75 | Alternative fixes might exist |
| `request_response` nested function anomaly | STRUCTURAL | 1.0 | N/A |
| PARTIAL match discards information | STRUCTURAL | 1.0 | N/A |

---

# PHASE 3 — SELF-CORRECTION

**UNVERIFIABLE (removed):** None — all claims >= 0.75 confidence or reclassified as derivations.

**Revised conservation law confidence:** 0.85 → grounded in structural code patterns, not just theory.

---

# FINAL OUTPUT

## Conservation Law
```
Composition_Depth × Parameter_Isolation = constant
```
[VERIFY: derivation from scope.update() semantics at lines 106, 165, 217, 322]

## Corrected Defect Table

| # | Location | Defect | Severity | Type | Verification |
|---|----------|--------|----------|------|--------------|
| 1 | Lines 165, 217 | **Parameter collision via silent overwrite** — `path_params.update(matched_params)` destroys same-named parameters from outer Mount levels | Medium | Structural | [VERIFY: source:line_165, source:line_217] |
| 2 | Lines 22-28 | **Dead parameter anomaly** — `request_response` defines nested `async def app` that shadows outer; inner function's `(scope, receive, send)` parameters are never used (closure uses outer scope's `request`) | Low | Structural | [VERIFY: source:line_22-28] |
| 3 | Lines 326-328 | **First-PARTIAL-wins discards method information** — `partial is None` check keeps only first partial match; routes with disjoint method sets on same path cannot aggregate allowed methods for correct 405 | Medium | Structural | [VERIFY: source:line_326-328] |
| 4 | Lines 237-244 | **Naming-hierarchy coupling** — `Mount.url_path_for` requires `name.startswith(self.name + ":")` convention; route names encode tree position, breaking portability | Medium | Structural | [VERIFY: source:line_237-244] |
| 5 | Lines 92-99 | **Local-only duplicate validation** — `compile_path` raises on duplicate params within single path but provides no protection across nested Mount boundaries | Low | Structural | [VERIFY: source:line_92-99] |
| 6 | Line 106 | **Scope mutation without copy** — `scope.update(child_scope)` mutates shared scope object; partial matches leave side effects that could affect fallback handling | Low | Structural | [VERIFY: source:line_106] |
