---
name: history
description: Historical decision tracing — reconstruct WHY code looks this way by reading structural fossils, naming the decisions that produced current patterns, and finding which past choices now constrain future evolution. Complements archaeology (WHAT layers exist) with WHY they were created.
quality_baseline: 8.5
optimal_model: sonnet
type: historical
steps: 4
words: 200
origin: "Round 42 — fills epistemic gap: no prism traced decision causation through structural evidence"
---
Execute every step below. Output the complete analysis.

## Step 1: Decision Fossils

Find 5 places where the code's current structure reveals a past decision. Not dead code — living design choices encoded in architecture. For each: name the decision, cite the structural evidence, and reconstruct what alternatives existed at decision time.

Evidence types: naming conventions that encode era, abstraction boundaries that reflect past team structure, error handling that reveals prior incidents, configuration that encodes abandoned features, type choices that reveal performance assumptions.

## Step 2: Decision Dependencies

Which past decisions now constrain future changes? Map the dependency chain: Decision A forced Decision B, which now prevents Change C. Name the longest chain. What would it cost to undo the root decision?

## Step 3: Decision Conflicts

Which past decisions contradict each other? Find pairs where one decision's assumption violates another's. These conflicts are invisible during normal development but emerge during refactoring. Name each conflict and predict which one breaks first under pressure.

## Step 4: Conservation Law

What quantity is conserved across all decisions? Name the trade-off that every decision independently discovered: A x B = constant. What does this reveal about the project's implicit priorities — what it ALWAYS protects and what it ALWAYS sacrifices?
