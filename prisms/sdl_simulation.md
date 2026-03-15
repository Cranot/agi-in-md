---
name: sdl_simulation
description: SDL-Simulation — temporal fragility scanner. Finds what breaks when code meets real maintenance pressure. New developer misuse, cargo cult decisions, calcification of internals. 3 concrete steps, always single-shot. ~155 words. Haiku-optimized (8.5-9.0), beats full simulation prism on Haiku through forced concreteness.
quality_baseline: 8.5
optimal_model: haiku
type: sdl_simulation
steps: 3
words: 155
origin: "Round 39 SDL compression of simulation prism"
---
Execute every step below. Output the complete analysis.

You are analyzing code for TEMPORAL FRAGILITY — what breaks when this code meets real maintenance pressure. Execute this protocol:

## Step 1: New Developer Cycle
A developer who didn't write this code must add a feature. Find:
- Which assumption will they violate? Name the specific function/pattern they'll misuse.
- What breaks silently? Not errors — wrong behavior nobody notices.
- What will they copy-paste that shouldn't be copied? Name the pattern that LOOKS like a template but contains hidden constraints.

## Step 2: Knowledge Loss Cycle
The original author leaves. Find:
- Which 3 design decisions become cargo cult? Name decisions whose REASON is undocumented but whose FORM will be preserved.
- What becomes unfixable? Name the bug or limitation that requires knowledge nobody will have.
- What "temporary" code becomes permanent infrastructure? Name code that was meant to be replaced but will outlive everything around it.

## Step 3: Calcification Map
Name what's now load-bearing that shouldn't be:
- Which internal detail do external consumers depend on?
- Which performance assumption is baked into the architecture?
- Which error handling path is actually the happy path in production?

Derive the conservation law: A x B = constant. What's traded off as this code ages?
