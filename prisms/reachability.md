---
calibration_date: 2026-03-12
model_versions: ["claude-sonnet-4-6"]
quality_baseline: 7.5
optimal_model: sonnet
origin: "factory:analysis_fallback — goal: Find dead code and unreachable paths. Trace every function definition to its call sites. Find: functions defined but nev"
notes: "goal-spec mode (no SDL example available). 162w, 3-step. Validate before production use."
validation_passed: true
---
Execute every step below. Output the complete analysis.

## Step 1: Map Call Graph and Usage
Trace every function definition to all its call sites to identify reachable code paths. Search for: functions defined but never invoked from any execution path, class methods that override parent signatures but are never called polymorphically, imports referenced only in unreachable branches or dead comments.

## Step 2: Detect Stale and Shadow State
Identify variables and configurations that occupy space but never influence behavior. Search for: variables assigned values that are never read before being overwritten, configuration keys checked by validation logic but never set by any configuration loader, exception handlers catching error types the guarded code cannot produce.

## Step 3: Expose Structural Deadness
Reveal code that exists but cannot execute or participate. Find these named patterns: Zombie Override (methods overriding parents but never invoked through base class), Phantom Configuration (validated against constraints but never populated), Orphaned Handler (catching exceptions the try block cannot raise).
