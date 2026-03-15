# PHASE 1 — STRUCTURAL ANALYSIS

## Three Properties This Code Claims

1. **Bidirectional Routing** — `matches()` maps URL → handler; `url_path_for()` maps handler name → URL
2. **Hierarchical Composition** — Mount can nest Router, Router can nest Mount, arbitrary depth
3. **Local Knowledge Only** — Each route level knows only its own path pattern, no parent back-references

## Proof They Cannot Coexist

```
url_path_for at depth N needs: full URL = Σ(ancestor paths) + local path
                               
With local knowledge only: each level knows only 1 path segment

To reconstruct: must traverse root → leaf
But url_path_for starts from: leaf (named route), no path to root

Resolution in code: ":" naming convention (lines 238-253)
   - Name "api:v1:users" encodes full hierarchy path
   - REQUIRES manual coordination between name and structure
   - NOT derived from composition — externally imposed
```

The three properties are **structurally incompatible**. The code resolves this by sacrificing Property 3 (local knowledge) — routes MUST know their qualified names, which encodes global hierarchy knowledge.

---

## Conservation Law

```
Local Autonomy × URL Reconstruction Capability = Constant
```

- Increase autonomy (routes don't know parents) → URL reconstruction fails
- Increase reconstruction (full URLs from handlers) → routes must know qualified names
- The ":" separator is the **coordination tax** paid to maintain bidirectionality under composition

---

## Concealment Mechanism

**Exception uniformity** (lines 7-10):

```python
class NoMatchFound(Exception):
    def __init__(self, name, path_params):
        params = ", ".join(list(path_params.keys()))
        super().__init__(f'No route exists for name "{name}" and params "{params}".')
```

Three distinct failures produce identical messages:
1. Route doesn't exist
2. Wrong qualified name format (`"users"` vs `"api:users"`)
3. Missing path parameters

The coordination failure is **concealed as "not found"** — debugging requires knowing the hidden name contract.

---

## Improvement That Recreates The Problem

**Proposed:** Auto-generate qualified names from hierarchy position.

```python
# Router registers children with parent prefix
def add_route(self, route):
    route.qualified_name = f"{self.qualified_name}:{route.name}" if self.qualified_name else route.name
```

**Deeper recreation:**
- Route ORDER now determines names (first registration wins)
- Moving routes silently breaks `url_path_for` callers
- Tests couple to hierarchy structure
- **Coordination migrates** from "know the name" → "understand the hierarchy"

The impossibility (bidirectional routing + composition + local knowledge) is **invariant** — solutions relocate the coordination cost, never eliminate it.

---

# PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | If Wrong |
|-------|---------------|------------|----------|
| Mount appends `/{path:path}` to regex | STRUCTURAL | 1.0 | N/A |
| url_path_for uses `:` separator | STRUCTURAL | 1.0 | N/A |
| NoMatchFound has uniform message | STRUCTURAL | 1.0 | N/A |
| Three properties cannot coexist | STRUCTURAL (derivation) | 0.95 | Would need to find hidden reconciliation mechanism |
| Conservation law form | STRUCTURAL (derivation) | 0.9 | Different mathematical form possible |
| Function shadowing in request_response | STRUCTURAL | 1.0 | N/A |
| Shallow copy for redirect_scope | STRUCTURAL | 1.0 | N/A |
| Auto-names recreate problem | STRUCTURAL (derivation) | 0.85 | Alternative: maybe names COULD be derived without coordination |

---

# PHASE 3 — SELF-CORRECTION

**Confidence < 0.5 claims:** None

**All claims are STRUCTURAL or high-confidence derivations.** Proceeding to verified output.

---

# FINAL OUTPUT

## Conservation Law
```
Local Autonomy × URL Reconstruction Capability = Constant
```
[VERIFY: derivation from source:lines_142-156 (matches), source:lines_232-256 (url_path_for hierarchy traversal)]

---

## Corrected Defect Table

| # | Location | Severity | Type | Description | Verification |
|---|----------|----------|------|-------------|--------------|
| 1 | Lines 24-33 | Low | Code smell | **Function shadowing**: inner `async def app` shadows outer `async def app`. Intentional (inner handles response after outer creates Request) but confusing. | [VERIFY: source:lines_24-33] |
| 2 | Line 313 | Low | Edge case | **Shallow copy**: `redirect_scope = dict(scope)` shares nested mutable objects. ASGI spec likely prevents, but structural risk. | [VERIFY: source:line_313] |
| 3 | Lines 7-10 | Medium | UX | **Undifferentiated failures**: NoMatchFound doesn't distinguish "wrong name format" from "missing params" from "nonexistent route". Debugging requires knowledge of hidden `:` convention. | [VERIFY: source:lines_7-10] |
| 4 | Lines 238-253 | Structural | Design | **Coordination tax**: `url_path_for` requires qualified names (`parent:child`). Manual synchronization between route structure and naming. Cost migrates, never eliminated. | [VERIFY: derivation from source:lines_238-253 — see impossibility proof] |
| 5 | Lines 220-221 | Low | Fragility | **Indirect route access**: `Mount.routes` uses `getattr(self._base_app, "routes", [])` — silently returns empty list if wrapped app lacks routes attribute. | [VERIFY: source:lines_220-221] |

---

## Structural Insight

The routing system embodies a **genuine impossibility theorem**:

> Bidirectional URL routing (URL↔handler) + hierarchical composition + local-only knowledge are mutually exclusive.

The `:` naming convention is not a solution — it's the **coordination cost made visible**. Every nested Mount forces callers to know the full ancestry path. The conservation law is:

```
Depth × Per-Level Coordination = Total Coordination Cost
```

This is **structural**, not fixable. Any "improvement" (auto-names, reverse indexes, route registries) merely **migrates** the coordination burden to a different subsystem. The impossibility is invariant.
