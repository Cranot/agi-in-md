# L12G Structural Analysis: Starlette routing.py

## PHASE 1 — STRUCTURAL ANALYSIS

### Three Properties This Code Simultaneously Claims

1. **Deterministic first-match routing** — Routes checked in declaration order, first FULL match terminates
2. **Complete partial-match handling** — When no FULL match exists, PARTIAL matches are properly handled
3. **Correct redirect semantics** — `redirect_slashes` finds the right target for path normalization

### Proof They Cannot Coexist

**Contradiction location:** `Router.app()` method (lines ~270-300)

```python
# First loop: FIRST-WINS semantics for partials
partial = None
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match is Match.FULL:
        # ...returns immediately...
    elif match is Match.PARTIAL and partial is None:  # ← FIRST-WINS
        partial = route

# Second loop: ALL-CHECKED semantics for redirects  
for route in self.routes:  # ← iterates ALL routes
    match, child_scope = route.matches(redirect_scope)
    if match is not Match.NONE:
        # ...uses this match...
```

**The incoherence:** Partial matching uses first-wins. Redirect uses all-checked. A route that returns PARTIAL in the first loop might have returned FULL after slash adjustment — but we'll never check it because we already committed to the first partial. Conversely, the redirect loop might find a match that a DIFFERENT partial would have preferred.

The code claims consistent routing semantics but implements two different search strategies in adjacent blocks.

### Conservation Law

```
Match Consistency × Implementation Simplicity = constant
```

- To unify semantics: track all partials → more complex state management
- To keep simplicity: accept inconsistent search strategies → behavioral surprises
- You cannot have both uniform matching logic AND the current linear-scan simplicity

### Concealment Mechanism

**Procedural hiding via variable naming:**

```python
elif match is Match.PARTIAL and partial is None:
    partial = route
    partial_scope = child_scope
```

The variable `partial` (singular) conceals that this is a **first-wins** selection, not a **best-of** selection. A reader sees "handle partial match" and assumes completeness. The `is None` guard is the mechanism — it looks like initialization, but it's actually a selection filter.

**Dual-loop concealment:**

Two separate `for route in self.routes` loops in the same function. Each has different semantics (first-terminate vs all-check). The proximity conceals the inconsistency — readers process them as "the routing part" and "the redirect part" rather than comparing their search strategies.

### Improvement That Recreates the Problem Deeper

**Refactor:** Track all partials, select "best" by specificity:

```python
partials = []
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match is Match.FULL:
        # ...
    elif match is Match.PARTIAL:
        partials.append((route, child_scope))

if partials:
    best_partial = max(partials, key=lambda p: specificity(p[1]))
    # ...
```

**New problem at deeper level:** Now you need a `specificity()` function. Should it prefer longer path matches? More constrained convertors? Earlier declaration order? Any choice creates a new inconsistency with the redirect loop's selection logic. You've moved the problem from "first vs all" to "specificity metric vs redirect's implicit metric."

---

## PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | If Wrong, What Changes |
|-------|---------------|------------|------------------------|
| Routes checked in declaration order | STRUCTURAL | 1.0 | — |
| First FULL match terminates | STRUCTURAL | 1.0 | — |
| `partial is None` implements first-wins | STRUCTURAL | 1.0 | — |
| Redirect loop checks ALL routes | STRUCTURAL | 1.0 | — |
| Two loops have different semantics | STRUCTURAL (derivation) | 1.0 | — |
| A route PARTIAL in first loop could FULL after redirect | CONTEXTUAL | 0.85 | Depends on whether slash-adjusted paths can change PARTIAL→FULL for same route |
| Partial commitment prevents checking alternatives | STRUCTURAL (derivation) | 1.0 | — |
| Conservation law form: Consistency × Simplicity | STRUCTURAL (derivation) | 0.95 | Form might differ, but trade-off exists |
| Variable naming conceals first-wins semantics | STRUCTURAL | 1.0 | — |
| Refactored "best partial" creates new metric problem | STRUCTURAL (derivation) | 1.0 | — |

**Low-confidence item analysis:**

Claim: "A route that returns PARTIAL might have returned FULL after slash adjustment"

Let me verify from source:

```python
# Route.matches() - line ~150
if self.methods and scope["method"] not in self.methods:
    return Match.PARTIAL, child_scope
else:
    return Match.FULL, child_scope
```

PARTIAL is returned when path matches but method doesn't. Redirect changes `path`, not `method`. So this claim is **UNVERIFIABLE** — redirect doesn't affect method-based PARTIALs.

However, a DIFFERENT route might match the redirected path with the correct method. The redirect loop finds this. But we've already committed to the first partial. So the core contradiction (first-wins vs all-checked) remains valid even if my specific mechanism was wrong.

---

## PHASE 3 — SELF-CORRECTION

### Removed/Revised Claims

1. ~~"A route that returns PARTIAL in the first loop might have returned FULL after slash adjustment"~~ — **REMOVED**. Redirect modifies path, not method. PARTIAL from method-mismatch won't become FULL.

2. **Revised:** The inconsistency is between **commitment to first partial** vs **re-searching all routes for redirect**. If route A returns PARTIAL (method mismatch) and route B would return FULL on the redirected path, we use route A (first partial) and never discover route B's redirect match — because we committed to partial BEFORE checking redirects.

### Verified Claims

| Claim | Verification |
|-------|--------------|
| Routes checked in declaration order | [VERIFY: source:line_277] `for route in self.routes:` |
| First FULL match terminates | [VERIFY: source:line_280-282] `if match is Match.FULL: ... return` |
| `partial is None` implements first-wins | [VERIFY: source:line_284] `elif match is Match.PARTIAL and partial is None:` |
| Redirect loop checks ALL routes | [VERIFY: source:line_299] `for route in self.routes:` (no early termination on match check, only on response send) |
| Partial commitment happens before redirect check | [VERIFY: source:line_288-292] partial stored, then redirect loop at line 297 |
| Variable naming (`partial` singular) obscures first-wins | [VERIFY: derivation] Name implies single entity, guard `is None` hides selection semantics |
| Conservation: Match Consistency × Implementation Simplicity = constant | [VERIFY: derivation] Unifying search strategies requires additional state; current simplicity requires accepting inconsistency |

---

## FINAL OUTPUT

### Conservation Law
```
Match Consistency × Implementation Simplicity = constant
```

### Corrected Defect Table

| Defect | Location | Severity | Type | Verification |
|--------|----------|----------|------|--------------|
| Inconsistent search strategy: partial=first-wins, redirect=all-checked | Router.app(), lines 277-311 | MODERATE | Structural | [VERIFY: source:line_284 vs source:line_299] |
| First-wins semantics concealed by variable name | Router.app(), line 284 | LOW | Structural | [VERIFY: source:line_284] `partial is None` guard |
| Partial commitment blocks redirect discovery of better matches | Router.app(), lines 288-310 | MODERATE | Structural | [VERIFY: derivation] Partial stored at line 288-292, redirect at 297-310, no backtracking |
| Two search loops with different termination semantics in same function | Router.app() | LOW | Structural | [VERIFY: source:line_277, source:line_299] |
| Scope mutation is side effect (child_scope merged permanently) | Router.app(), line 281, 293 | LOW | Structural | [VERIFY: source:line_281, source:line_293] `scope.update(child_scope)` |
