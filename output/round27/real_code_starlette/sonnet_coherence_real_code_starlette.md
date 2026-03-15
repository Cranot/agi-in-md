## Coherence Assessment

### 1. RESTATEMENT

**Yes — substantial restatement failure.**

The core PARTIAL-overloading claim appears in L7, L9B, L9C, L10B, L10C, and L11B. Six of ten levels orbit the same finding with cosmetic reframing ("undocumented protocol," "semantic incoherence," "HTTP concern in routing vocabulary," "dual meaning"). The identical falsifiable example — two routes on the same path with different methods producing a wrong `Allow` header — appears nearly verbatim in both L9C and L10B.

L8 and L11C independently claim `scope` mutation is "the real protocol" and "the deepest structural problem," making them restatements of each other rather than progression.

### 2. CONTRADICTION

**Yes — including a direct factual conflict.**

- L9B states: *"Mount never returns PARTIAL — only Route does."*
- L10B states: *"Mount.matches() returns PARTIAL to mean 'prefix matches, delegate deeper.'"*

These are contradictory claims about observable codebase behavior, not different interpretations. One is wrong.

Additionally, L8, L9B, L11A, L11C, and L12 each assert they have identified "the deepest structural problem" with different answers (scope mutation / PARTIAL semantics / tree-transformation fusion / split authority). They cannot all be the deepest.

### 3. PROGRESSIVE DEEPENING

**Partial and non-monotonic.**

| Transition | Assessment |
|---|---|
| L7 → L8 | Genuine: moves from "hidden contract" to "scope mutation is the real protocol" |
| L8 → L9B/C | Regression: returns to L7's PARTIAL framing |
| L9–L10 band | Plateau: four levels rephrase the same finding |
| L10 → L11A | Genuine: elevates to tree/transformation fusion — structure unqueryable without re-executing it |
| L11A → L11B | Regression: back to PARTIAL two-phase protocol |
| L11B → L11C | Revisits L8's scope-mutation terrain with different vocabulary |
| L11C → L12 | Partial advance: extensibility test ("touch one location") is a new probe, but the finding is a restatement of L10C |

Two genuine deepening moves (L7→L8, L10→L11A) are not enough to constitute a coherent progression.

### 4. OBJECT OF ANALYSIS SHIFT

**Incomplete and inconsistent.**

Expected arc: code → improvements → design space → constraints → analytical process

- **L7–L11B**: All analyze the artifact (PARTIAL semantics, scope mutation). No shift.
- **L11A**: Begins to analyze structural constraints ("reading requires writing"), but stays code-bound.
- **L12**: Attempts design-space analysis via extensibility test ("add Accept-header routing by touching one location"). This is the only level that partially crosses into the design-space register.
- No level reaches meta-analysis of the analytical process itself.

The object of analysis does not shift — it wobbles around the artifact.

### 5. Rating: **WEAK**

The levels fail the defining test: each should find what all previous levels could not. Instead, a cluster of six levels (L7, L9B, L9C, L10B, L10C, L11B) are largely interchangeable. The two genuine moves — scope mutation (L8) and tree/transformation fusion (L11A) — are real findings, but they are surrounded by regression and contradiction rather than integrated into a building argument. The factual contradiction between L9B and L10B about Mount's behavior is a structural defect independent of the coherence question.
