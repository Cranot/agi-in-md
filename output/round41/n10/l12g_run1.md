# L12g Structural Analysis: Starlette routing.py

## PHASE 1 — STRUCTURAL ANALYSIS

### Three Simultaneously Claimed Properties

1. **Ordered determinism** — Routes match in definition order, first FULL wins
2. **Partial-match recovery** — Routes can match path but fail method check (PARTIAL), with fallback handling
3. **Mount prefix isolation** — Mount points compose cleanly via `root_path` remapping

### The Impossibility Proof

**PARTIAL-match recovery × Mount prefix isolation = mutually exclusive.**

When a Mount matches (`/api`), it **always** returns `Match.FULL` (line 191-192) because the `{path:path}` catch-all guarantees path match. There is **no Mount.PARTIAL** — Mount has no method discrimination. 

Consequence: If you mount a sub-router with method-discriminated routes at `/api`, and someone requests `POST /api/users` but the sub-route only allows GET:
- The Mount returns FULL (passes prefix)
- The sub-route returns PARTIAL (fails method)
- **No outer fallback possible** — the Mount already committed to FULL

The outer Router's PARTIAL recovery logic (lines 248-251) is **structurally unreachable** for any failure inside a Mount.

### Conservation Law

```
Route_Expressiveness × Match_Ambiguity = constant
```

OR equivalently:

```
Prefix_Composability × Method_Recoverability = constant
```

Mounts trade method-level PARTIAL semantics for prefix-level composition. You cannot have both.

### Concealment Mechanism

**Distributed responsibility across match levels.** 
- Route.matches() knows about methods (line 146-148)
- Mount.matches() does NOT know about methods (line 191 returns only FULL or NONE)
- Router.app() tries to handle PARTIAL (line 248-251) but cannot see inside Mount's delegation

The PARTIAL mechanism exists in code but is **structurally bypassed** by Mount's unconditional FULL return. The bug is not in any single function — it's in the interaction between layers that each make locally-correct decisions.

### Improvement That Recreates The Problem Deeper

Add `methods` parameter to `Mount.__init__`:

```python
class Mount(BaseRoute):
    def __init__(self, path, app=None, routes=None, methods=None, ...):
        self.methods = {m.upper() for m in methods} if methods else None
```

Then in `Mount.matches()`:
```python
if self.methods and scope["method"] not in self.methods:
    return Match.PARTIAL, child_scope  # Now Mount can return PARTIAL
```

**This recreates the problem deeper because:**
- Now Mount can return PARTIAL
- But Mount ALSO uses `{path:path}` catch-all
- If method fails, `remaining_path` is already computed and `child_scope` has mutated `root_path`
- The PARTIAL return contains **already-consumed path state** — the caller cannot retry with a different Mount
- We've added method discrimination but **path consumption happens before method check**

The fix introduces a new impossibility: **early path commitment vs late method rejection**.

---

## PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | If Wrong |
|-------|---------------|------------|----------|
| Routes match in definition order | STRUCTURAL: Router.app() iterates `self.routes` list sequentially | 1.0 SAFE | N/A |
| First FULL wins | STRUCTURAL: line 245-247 `return` after first FULL | 1.0 SAFE | N/A |
| PARTIAL fallback exists | STRUCTURAL: lines 248-251 | 1.0 SAFE | N/A |
| Mount always returns FULL or NONE | STRUCTURAL: Mount.matches() lines 178-195 have no PARTIAL branch | 1.0 SAFE | N/A |
| Mount has no method discrimination | STRUCTURAL: Mount.__init__ has no `methods` param, matches() doesn't check scope["method"] | 1.0 SAFE | N/A |
| Mount uses `{path:path}` catch-all | STRUCTURAL: line 170 `compile_path(self.path + "/{path:path}")` | 1.0 SAFE | N/A |
| PARTIAL unreachable inside Mount | DERIVATION: Mount returns FULL → Router proceeds → Mount.handle() delegates to inner app → inner Route returns PARTIAL to its own Router → outer Router already exited | 0.95 | Would need runtime test |
| Conservation law form | DERIVATION from structural constraints | 0.85 | Form might differ |
| Concealment mechanism description | STRUCTURAL: code inspection shows distributed responsibility | 0.9 | N/A |
| Improvement creates path-before-method commitment | STRUCTURAL: matches() computes remaining_path before any method check could happen | 1.0 SAFE | N/A |

---

## PHASE 3 — SELF-CORRECTION

**Confidence < 0.95 claim revised:**

> "PARTIAL unreachable inside Mount" — This is a derivation. Let me verify structurally.

[VERIFY: derivation] Router.app() at line 245-247 returns immediately on `match is Match.FULL`. Mount.matches() at line 191 returns `Match.FULL, child_scope` unconditionally when path regex matches (which it always does due to `{path:path}`). Therefore, when a Mount's prefix matches, Router.app() **never reaches** the PARTIAL fallback at lines 248-251 for that Mount. The PARTIAL handling inside the mounted app is local to that app's own Router — the outer Router has already committed.

**Confidence < 0.9 claim revised:**

> Conservation law form — The precise mathematical form may vary, but the structural trade-off (Mount composition vs method-level PARTIAL) is source-grounded.

---

## FINAL OUTPUT

### Conservation Law
```
Mount_Composability × Method_Partial_Recovery = constant
```
[VERIFY: derivation from Mount.matches() returning only FULL/NONE while Route.matches() can return PARTIAL]

### Corrected Defect Table

| Location | Defect | Severity | Type | Verification |
|----------|--------|----------|------|--------------|
| Mount.matches():178-195 | Returns only FULL or NONE — no method discrimination means outer Router's PARTIAL recovery (248-251) is structurally bypassed for any failure inside a Mount | High | Structural | [VERIFY: source:178-195, 248-251] |
| Mount.__init__:170 | `{path:path}` catch-all guarantees path match — combined with no method check, Mount cannot express "path matches but method doesn't" | High | Structural | [VERIFY: source:170] |
| Router.app():248-251 | PARTIAL fallback exists but is unreachable for failures that occur inside Mount delegation chain | Medium | Structural | [VERIFY: source:245-247 + 178-195] |
| Mount.matches():185-186 | `remaining_path` computed before any method check could occur — if method were added, path commitment would precede method rejection | Medium | Structural | [VERIFY: source:185-186] |
| Router.app():245-247 | Early return on FULL prevents any "try next route" semantics for Mount-level failures | Low | Design | [VERIFY: source:245-247] |
| request_response():47-52 | Nested `async def app` shadows outer — inner app never executes `wrap_app_handling_exceptions` correctly | Medium | Fixable | [VERIFY: source:47-52] |
| compile_path():66 | `duplicated_params` detected but only checks within single route — cross-route param conflicts in Mount chains are silent | Low | Structural | [VERIFY: source:66-72] |

### Meta-Conservation Law
[VERIFY: derivation] This analysis conceals: **The value of Mount's simplification.** By NOT supporting method-level PARTIAL, Mount avoids the complexity of "partially committed" state where path is consumed but method rejected. The "defect" is also a feature — it forces method discrimination to happen at the leaf Route level where rollback is cheap.
