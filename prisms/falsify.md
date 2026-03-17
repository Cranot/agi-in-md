---
name: falsify
description: Conservation law falsification prism — takes a conservation law claim and stress-tests whether it's a genuine structural constraint or a pattern-matched inevitability narrative. The antidote to the tool's own structural bias toward finding conservation laws. Run AFTER any scan that produces a conservation law.
quality_baseline: unscored
optimal_model: sonnet
type: epistemic
steps: 4
words: 210
origin: "Round 42 — addresses ChatGPT critique that conservation laws risk being unfalsifiable"
---
Execute every step below. Output the complete analysis.

You receive a conservation law claim (A × B = constant) derived from structural analysis. Your job is to ATTACK it — determine whether it's a genuine structural constraint or a compelling-sounding pattern that could apply to almost anything.

## Step 1: Universality Test

Could this SAME conservation law be derived from ANY codebase? State the law, then try to apply it to 3 completely unrelated systems (a todo app, a game engine, a banking system). If it fits all three with minor rewording, it's too generic to be informative. Rate: SPECIFIC (only fits this code) / GENERIC (fits anything) / TRIVIAL (restates a known CS trade-off).

## Step 2: Counterexample Construction

Design a CONCRETE modification to this code that would improve BOTH sides of the trade-off simultaneously. If you can — the law is false. If you genuinely cannot — explain what structural property prevents it. The inability must be SPECIFIC to this code, not a general impossibility.

## Step 3: Alternative Laws

Derive 2 DIFFERENT conservation laws from the same code. If the code supports multiple equally plausible laws, the original wasn't discovered — it was projected. If one law clearly dominates, explain why the others fail.

## Step 4: Verdict

Rate the original conservation law: VERIFIED (specific, no counterexample, dominates alternatives) / PLAUSIBLE (specific but alternatives exist) / GENERIC (applies to anything) / FALSE (counterexample found). State the evidence for your rating.
