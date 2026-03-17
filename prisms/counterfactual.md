---
name: counterfactual
description: Systematic counterfactual exploration — for each architectural decision, construct the alternative universe where the opposite choice was made. Deeper than rejected_paths (which traces migration). This prism constructs and evaluates the full alternative.
quality_baseline: 8.5
optimal_model: sonnet
type: counterfactual
steps: 4
words: 200
origin: "Round 42 — deepens rejected_paths with full alternative construction + evaluation"
---
Execute every step below. Output the complete analysis.

## Step 1: Decision Extraction

Identify the 3 most consequential design decisions in this code. Not small choices — the structural commitments that shaped everything else. For each: state the decision, state the alternative that was NOT chosen, and name what evidence in the code reveals this was a deliberate choice (not accident).

## Step 2: Alternative Construction

For each decision, CONSTRUCT the alternative in detail. What would the code look like if the opposite choice had been made? Be concrete: show the different interfaces, the different data flow, the different error handling. This is not speculation — derive the alternative from the constraints the original decision was responding to.

## Step 3: Comparative Analysis

For each pair (actual vs alternative): what does the alternative GAIN that the actual sacrifices? What does the alternative SACRIFICE that the actual gains? Which bugs in the actual code DISAPPEAR in the alternative? Which NEW bugs does the alternative introduce?

Name the conservation law for each pair: what quantity is conserved regardless of which choice is made?

## Step 4: The Unchosen Path

Across all 3 decisions, is there a SINGLE alternative architecture that takes the opposite of every choice? What does that maximally-different system look like? Is it coherent, or do the opposite choices conflict with each other? If they conflict: which pair of decisions are secretly coupled — changing one FORCES the other?
