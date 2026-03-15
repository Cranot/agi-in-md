---
name: evidence_cost
description: Evidence Cost prism (Opus-bred hybrid of ErrRes + Optim) — maps unchecked shared state with validation cost ranking, traces how skipped validation causes BOTH errors AND wasted computation, names the diagnostic conservation law (observability budget). 3 steps, ~160 words. Scored 9.0 on Starlette. Novel cross-dimensional insight neither parent finds alone.
quality_baseline: 9.0
optimal_model: sonnet
type: hybrid
parents: [error_resilience, optim]
steps: 3
words: 160
---
Execute every step below. Output the complete analysis.

## Step 1: The Evidence Cost Map
Name every shared state whose invariants go unchecked. For each: what diagnostic information would detect corruption early? What's the allocation cost to preserve it—O(1) checksum, O(n) snapshot, O(n²) operation log? What does the fast path discard? Rank by: validation_cost × mutation_frequency.

## Step 2: The Silent Waste Cascade
For each unchecked state, trace corruption forward. At each hop measure: CPU wasted on corrupt data, memory wasted on defensive copies made because validation was too expensive, I/O wasted on retries that cannot diagnose root cause. The key insight: the same skipped validation causes both errors AND performance waste. Map: Unchecked Write → Wasted Computation → Silent Exit.

## Step 3: The Diagnostic Conservation Law
Conservation law: Bytes used for error evidence cannot simultaneously hold payload data. Every system allocates its observability budget somewhere—you cannot have fast path, full safety, and debuggability. Table: State | Evidence Discarded | Waste From Blindness | Validation Cost | Impossible Trio Choice.
