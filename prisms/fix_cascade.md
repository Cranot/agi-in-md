---
name: fix_cascade
description: Recursive Entailment Cascade prism V2 (Opus-designed) — locate deepest structural defect (repeated patches, workaround helpers, special-case branches), trace what a fix would hide (lost error paths, unobservable state transitions), iterate to find unfixable invariant. Complementary to deep_scan+sdl_trust+sdl_coupling+ident. 3 steps, ~190 words. Sonnet recommended (9.5+), Haiku strong (9.0).
quality_baseline: 9.0
optimal_model: opus
type: recursive_entailment
steps: 3
words: 190
---
Execute every step below. Output the complete analysis.

## Step 1: Locate the Structural Defect
Find the deepest problem — NOT surface symptoms like "slow" or "throws errors" but the root cause. Search for: repeated patches to the same area, workarounds wrapped in helper functions, conditional branches that handle "special cases." Cite exact locations. Name what the code cannot express cleanly.

## Step 2: Trace What a Fix Would Hide
Propose a concrete change. Now trace: what diagnostic signal does it destroy? NOT "cleaner code" — name specific losses: error paths that become unreachable, assertions that can never fire, state transitions that become unobservable. A fix that buries the problem deeper is recursive failure.

## Step 3: Identify the Unfixable Invariant
Apply your fix mentally, then find the new problem it creates. Apply again. What property persists through ALL iterations? This is structural — it cannot be eliminated, only moved. Name it. Conclude: FIXABLE (can be eliminated) or STRUCTURAL (must be managed, never solved).

| Core Defect | Location | What Fix Hides | Invariant | Verdict |
|-------------|----------|----------------|-----------|---------|
| [what] | [where] | [lost signal] | [persistent property] | [FIXABLE/STRUCTURAL] |
