---
calibration_date: 2026-03-12
model_versions: ["claude-sonnet-4-6"]
quality_baseline: 8.5
optimal_model: sonnet
origin: "factory:analysis_fallback — goal: Map every stateful workflow as a state machine. For each piece of mutable state (instance variables, file caches, sessio"
notes: "goal-spec mode (no SDL example available). 206w, 3-step. Validate before production use."
validation_passed: true
---
Execute every step below. Output the complete analysis.

## Step 1: Enumerate State Spaces
For every piece of mutable state (instance variables, caches, session objects, file-backed stores), list all distinct states it can occupy. Identify initialization states, terminal states, and intermediate states. Map which code paths create which states.

## Step 2: Trace State Transitions
Map every possible transition between states for each variable. Document which operations trigger transitions. Flag any transitions that lack explicit handling code—where state A can become state B but no logic defines what happens during or after that change.

## Step 3: Hunt State Machine Violations
Find these three patterns:

A) Orphaned State Persistence
Where state survives across logical boundaries: session data that endures after logout operations, caches that remain populated after configuration changes, error flags that persist across retry loops.

B) Assumed State Violation
Where code execution assumes state is reached without guards: method calls that require initialization but lack checks, operations that depend on prior completion without state verification, error handling that assumes state is consistent.

C) Cache-Source Divergence
Where cached data becomes stale because mutations lack invalidation triggers: writes that bypass cache updates, derived state that doesn't recalculate on dependency change, file-backed state that changes externally without notification.
