---
name: evolution
description: Evolution prism V10 (Sonnet-designed) — trace invisible handshakes (data flowing between functions without appearing in signatures), propagate minimal poison mutations through contamination paths, map the fragility atlas. Complementary to L12+optim+errres+api_surface. 3 steps, ~130 words. Sonnet recommended (9.5+), Haiku strong (8.5-8.7).
quality_baseline: 9.5
optimal_model: sonnet
type: evolution
steps: 3
words: 130
---

Execute every step below. Output the complete analysis.

## Step 1: Trace Invisible Handshakes
Find data that flows between functions WITHOUT appearing in signatures: mutable shared state, closure captures, implicit ordering requirements, return values that constrain future calls. Trace each from origin through every dependent function. Name the unwritten rule binding them.

## Step 2: Propagate the Poison
For each handshake, trace the SMALLEST mutation that corrupts it without triggering any error. Follow the contamination path: list every function that receives wrong data. For each, state the exact wrong behavior — not "breaks" but "computes X instead of Y" or "sends malformed Z to W."

## Step 3: The Fragility Atlas
Rank by cascade size. Name the architectural decision that created each contract. State the conservation law: what does eliminating implicit coupling cost?

| Hidden Contract | Functions Corrupted | Wrong Behavior Produced | Architectural Cause | Explicitness Cost |
|---|---|---|---|---|
