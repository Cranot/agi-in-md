---
name: error_resilience_70w
description: Error resilience prism ULTRA-COMPACT — compressed from V11 (165w to ~70w) scoring 9.5 on Starlette (HIGHER than full version). Sonnet-compressed. The most efficient behavioral prism. Use when extreme word budget matters.
type: error_resilience
steps: 3
words: 70
optimal_model: sonnet
---
Execute every step below. Output the complete analysis.

## Step 1: The Shared State
Name mutable state multiple functions access. For each: writer, reader, unchecked assumption.

## Step 2: The Corruption Cascade
Trace writer fails mid-update through first corrupt reader to propagated writes to exit. Classify: error, silent, deferred. Map all chains.

## Step 3: The Silent Exits
For silent/deferred exits: name catching invariant, blocking contract. State conservation law. Table: Chain | Corruption Entry | Hops | Exit Type | Missing Check | Blocking Contract.
