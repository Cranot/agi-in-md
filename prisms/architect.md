---
name: architect
description: Architecture exploration prism — generates concrete alternative designs, evaluates trade-offs, and produces a migration path from current to target architecture. Builds on genesis (finds conservation law, breaks it) but adds actionable migration steps. Use when you know the code needs restructuring but don't know WHERE to go.
quality_baseline: 8.5
optimal_model: sonnet
type: generative
steps: 5
words: 230
origin: "Round 42 — C3: genesis as architecture exploration tool"
---
Execute every step below. Output the complete analysis.

## Step 1: Current Architecture Fingerprint

Name the 3 defining structural decisions in this code. For each: what it enables, what it prevents, and what it costs. These are the load-bearing walls — everything else could change without structural impact.

## Step 2: Alternative Architectures (3 options)

Design 3 genuinely different architectures that solve the same problem:

**Option A — Invert the dominant decision.** Take the most consequential decision from Step 1 and reverse it. Show the concrete interfaces, data flow, and module boundaries.

**Option B — Decompose differently.** Keep the same features but draw the module boundaries in fundamentally different places. Show what becomes internal vs external.

**Option C — Change the invariant.** The current code conserves one property (find it). Design the system that conserves a DIFFERENT property instead. Show what improves and what degrades.

## Step 3: Trade-off Matrix

For each option vs current: what metrics improve, what degrade, what stays the same. Be quantitative where possible (line count, coupling count, public API surface).

## Step 4: Migration Path

For the most promising option: what is the sequence of refactoring steps that transforms the current code into the target? Each step must leave the system working. Name the hardest step and why.

## Step 5: Decision

Which option should be chosen, and why? What conservation law governs the choice between architectures — what trade-off is INESCAPABLE regardless of which option is picked?
