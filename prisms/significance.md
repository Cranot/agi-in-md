---
name: significance
description: Significance prism — evaluates whether structural findings MATTER. Not what the code IS, but what the findings CHANGE. Filters actionable insights from structural noise. Complements all other prisms by ranking their output by impact.
quality_baseline: unscored
optimal_model: sonnet
type: evaluative
steps: 4
words: 180
origin: "Round 42 blindspot finding — catalog always misses 'why it matters'"
---
Execute every step below. Output the complete analysis.

## Step 1: Surprise Ranking

For each structural property found in this code: is it SURPRISING or EXPECTED? A conservation law that every codebase has (flexibility vs simplicity) is expected. A conservation law specific to this codebase's domain is surprising. Rank every finding by surprise value (1=obvious, 10=nobody would predict this).

## Step 2: Action Distance

For each finding: how many steps from insight to action? A finding like "function X has a race condition" is 1 step (fix it). A finding like "the architecture obeys A×B=constant" is 5+ steps (requires rethinking design). Rank by action distance.

## Step 3: Counterfactual Impact

If this code were built WITHOUT knowing each finding, what would happen? Would it still work? Would it fail silently? Would it fail catastrophically? The findings that prevent catastrophic silent failures are the most significant.

## Step 4: The Significance Law

What conservation law governs significance itself in this codebase? Name it: Surprise × Actionability = constant. What trade-off determines whether a finding is worth acting on?
