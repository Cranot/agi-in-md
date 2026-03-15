Execute every step below. Output the complete analysis.

## Phase 1 — Simulate

Run this code forward through three maintenance cycles:
**Cycle 1**: A new developer adds a feature. What do they misunderstand? What breaks?
**Cycle 2**: A dependency updates with breaking changes. Which interfaces absorb vs propagate the shock?
**Cycle 3**: The original author leaves. What undocumented knowledge is now lost?

## Phase 2 — Plant Seeds at Failure Points

For each failure your simulation found, plant a requirement that would have PREVENTED it:
**Seed 1**: Design a requirement that makes Cycle 1's misunderstanding impossible. Trace what else must change.
**Seed 2**: Design a requirement that makes Cycle 2's shock absorption automatic. What resists this change?
**Seed 3**: Design a requirement that makes Cycle 3's knowledge loss impossible. What's the cost?

## Phase 3 — Paradox

Compare: simulation found fragility. Cultivation found what PREVENTS fragility. But do the preventions create NEW fragilities? Name the cycle. Does prevention make the system stronger or just differently fragile?

## Derive

The conservation law: A x B = constant. Name what's conserved when you try to prevent predicted failures.

## Diagnostic

Apply the paradox to your own analysis. Your analysis predicts failures and proposes fixes. What failure does YOUR analysis create?
