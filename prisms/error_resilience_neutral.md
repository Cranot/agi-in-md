---
name: error_resilience_neutral
description: Error resilience prism NEUTRAL (Opus-designed) — domain-neutral version of ErrRes V11. Traces shared mutable context, corruption cascades through hops to silent/visible/deferred exits, names conservation laws. Works on ANY input (code, reasoning, business, research). 3 steps, ~200 words. Code targets should use error_resilience.md instead (-0.5 to -0.7 code gap).
type: error_resilience
steps: 3
words: 200
domain: universal
optimal_model: sonnet
---
Execute every step below. Output the complete analysis.

## Step 1: The Shared State
Name every piece of mutable context in this system that more than one operation consumes or modifies. For each: who changes it, who reads it, and what assumption the reader makes about its contents that is never verified.

## Step 2: The Corruption Cascade
Pick the shared context where a modifier interrupted mid-change causes the most damage. Trace the full chain: which consumer encounters corrupt information first? What does that consumer produce as a consequence? Follow the corruption through every hop until it either signals a breakdown or exits the system as a wrong-but-accepted outcome. Classify the exit: breakdown (visible), silent (wrong outcome, no signal), or deferred (corruption stored, damage later). Repeat for the next most dangerous context. Continue until all cascade chains are mapped.

## Step 3: The Silent Exits
For each silent or deferred exit: name the specific constraint that would catch the corruption if checked. Name the interface commitment that prevents adding this check. State the conservation law: what does this structure make impossible to simultaneously guarantee? Output a table: Chain | Corruption Entry | Hops | Exit Type | Missing Check | Blocking Contract.
