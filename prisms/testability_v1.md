---
calibration_date: 2026-03-13
model_versions: ["claude-haiku-4-5-20251001"]
quality_baseline: 8.0
optimal_model: haiku
origin: "VPS Mar 13 sweep, scored R38"
notes: "Testability prism. ~130w, 3-step SDL. Dependency Map → Isolation Cost → Testability Boundary. Code-specific."
---
Execute every step below. Output the complete analysis.

## Step 1: The Dependency Map
For each function in this code: what external state, services, or side effects does it depend on that cannot be replaced in a unit test? List every untestable dependency — globals, singletons, file I/O, network calls, system time, or hidden state shared with other functions.

## Step 2: The Isolation Cost
For each untestable dependency: what is the minimal change to make this function testable in isolation? Classify: injectable (add parameter), abstractable (extract interface), or structural (requires redesign). After each fix, check: does making this function testable break the testability of functions that depend on it?

## Step 3: The Testability Boundary
Name the design decision that creates the deepest untestable dependency chain. State the conservation law: what two properties does making this code testable trade off? Output a table: Function | Untestable Dependency | Fix Type | Fix Breaks Others? | Structural Cause.
