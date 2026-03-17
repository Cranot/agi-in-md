---
name: emergence
description: Interaction emergence prism — finds properties that arise from component INTERACTIONS, not from components themselves. Detects systemic behaviors invisible to single-component analysis. Works on multi-file projects or complex single files with interacting subsystems.
quality_baseline: 8.5
optimal_model: sonnet
type: emergent
steps: 4
words: 195
origin: "Round 42 — fills epistemic gap: no prism detected emergent properties from interactions"
---
Execute every step below. Output the complete analysis.

## Step 1: Interaction Map

Identify every point where components INFLUENCE each other — not just call each other. Influence includes: shared state, implicit ordering dependencies, resource competition, error propagation, configuration coupling, naming conventions that encode assumptions across boundaries.

For each interaction: name the two components, the coupling mechanism, and what assumption each makes about the other.

## Step 2: Emergent Behaviors

Which behaviors does the SYSTEM exhibit that NO individual component intends? These are properties of interactions, not implementations. Look for:
- Feedback loops (A affects B affects A)
- Race conditions between subsystems
- Cascading failures across boundaries
- Implicit protocols that no single component documents
- Resource exhaustion from individually-reasonable allocations

Name each emergent behavior and trace it to the specific interactions that produce it.

## Step 3: Invisible Contracts

What agreements exist between components that are NOT in any interface, type signature, or documentation? These implicit contracts are the most fragile part of the system. For each: who would break it accidentally, and what would the symptom be?

## Step 4: Emergence Conservation Law

What quantity is conserved across all emergent behaviors? Name it: A x B = constant. What does the system ALWAYS produce when components interact, regardless of which specific components are involved?
