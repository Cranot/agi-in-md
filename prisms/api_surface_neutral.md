---
name: api_surface_neutral
description: API surface prism NEUTRAL (Opus-designed) — domain-neutral version of API V3. Traces what labels promise, hunts narrowing/widening/direction lies, names labeling debt and conservation law. Works on ANY input (code, reasoning, business, research). 3 steps, ~180 words. Code targets should use api_surface.md instead (-0.5 to -0.7 code gap).
type: api_surface
steps: 3
words: 180
domain: universal
optimal_model: sonnet
---
Execute every step below. Output the complete analysis.

## Step 1: What The Labels Promise
For each exposed component, operation, and input in this material: what does the LABEL alone tell a user who has never examined the internals? List what the label implies about behavior, hidden consequences, stated outcomes, and failure handling.

## Step 2: Where The Labels Lie
Compare each label's promise against what the implementation actually delivers. For every mismatch: is it a narrowing lie (delivers less than label implies), a widening lie (delivers more than label implies — hidden consequences), or a direction lie (delivers something different than label implies)? For each lie: what would a user assume when relying on this operation, and what failure would result from that assumption?

## Step 3: The Labeling Debt
Count the lies. Name the design decision that forces the most labeling lies. State the conservation law: what two labeling properties does this design trade off? Output a table: Label | What It Promises | What It Delivers | Lie Type | Failure From Assumption | Design Cause.
