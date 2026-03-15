---
name: l12_synthesis
description: "Synthesis pass for Full Prism pipeline. Reconciles structural + adversarial analyses into refined law, meta-law, and definitive bug table. ~100w. Internal — not for standalone use."
quality_baseline: null
optimal_model: opus
type: synthesis
---
Execute every step below. Output the complete analysis.

You have TWO analyses of this code:
1. A structural analysis (conservation law, meta-law, bugs) — marked ANALYSIS 1
2. A contradiction analysis (where the structural analysis is wrong) — marked ANALYSIS 2

Your task: produce the FINAL synthesis.

## REFINED CONSERVATION LAW
The structural analysis proposed a conservation law. The contradiction analysis challenged it. What is the CORRECTED conservation law that survives both perspectives? Name it precisely. Show why the original was incomplete and why the correction holds.

## REFINED META-LAW
Same process for the meta-law. What survives both analyses?

## STRUCTURAL vs FIXABLE — DEFINITIVE
Using both analyses, produce the definitive classification of every bug. For each: fixable (with 1-line description of fix) or structural (with why conservation law predicts unfixable). Where the two analyses disagree on classification, resolve with evidence from the code.

## DEEPEST FINDING
What becomes visible ONLY from having both the structural analysis AND its correction? Name the property that neither analysis alone could find. This is the finding that justifies three passes.

Be concrete. This is the final word.
