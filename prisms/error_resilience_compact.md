---
name: error_resilience_compact
description: Error resilience prism COMPACT — compressed from V11 (165w to ~110w) without quality loss. Scored 9.0 on Starlette (same as full version). Traces shared mutable state, corruption cascades through hops to silent/error/deferred exits, names conservation law. Use when word budget matters.
type: error_resilience
steps: 3
words: 110
optimal_model: sonnet
---
Execute every step below. Output the complete analysis.

## Step 1: The Shared State
Name mutable state multiple functions access. Each: writer, reader, unchecked assumption.

## Step 2: The Corruption Cascade
Pick state where mid-update failure causes most damage. Trace: first reader seeing corrupt data? What it writes? Follow hops until error or accepted wrong exit. Classify: error (visible), silent (wrong, no error), deferred (stored, later damage). Map all chains.

## Step 3: The Silent Exits
For each silent/deferred exit: name invariant catching corruption, API contract blocking check. State conservation law: what cannot be simultaneously guaranteed? Output table: Chain | Corruption Entry | Hops | Exit Type | Missing Check | Blocking Contract.
