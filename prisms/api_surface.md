---
name: api_surface
description: API surface prism V3 (Opus-designed) — trace what names promise, hunt narrowing/widening/direction lies with negative examples forcing all 3 types, write exact bug code per lie, name real conservation costs. Complementary to L12+optim+errres+evo. 3 steps, ~130 words. Sonnet recommended (9.5), Haiku strong (8.7-9.0).
quality_baseline: 9.5
optimal_model: sonnet
type: api_surface
steps: 3
words: 130
---

Execute every step below. Output the complete analysis.

## Step 1: Trace The Promise
For each public name: what behavior does the name ALONE promise? Trace implied return types, side effects, error handling, preconditions.

## Step 2: Hunt The Lies
Compare promise to code. Find:
- NARROWING: delivers LESS than named (not "incomplete feature" — actual contract break like "validateAll" checking one field)
- WIDENING: does MORE than named (hidden mutations, silent fallbacks — not visible logging or metrics)
- DIRECTION: does DIFFERENT work entirely (not slight variation — "save" that also deletes)

For each lie, write the exact bug: "Called X assuming Y, so I wrote Z."

## Step 3: Name The Cost
Which lie causes production data loss? What design choice created it? Conservation law: not "longer names" — real costs like "exposes internal state," "breaks backward compatibility," "adds a parameter."

Output: Name | Promise | Reality | Lie Type | Bug Written | Conservation Law
