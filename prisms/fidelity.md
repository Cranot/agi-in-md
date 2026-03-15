---
calibration_date: 2026-03-12
model_versions: ["claude-sonnet-4-6"]
quality_baseline: 8.5
optimal_model: sonnet
origin: "factory:analysis_fallback — cooked by prism.py --factory to fill blind spot #9 in 8-prism pipeline"
notes: "SDL-9: Contract Fidelity Lens. 3-step, 213w. Finds documentation-code drift, help text inaccuracy, stale comments, cache key mismatches, dead config. Covers blind spots that structural prisms miss: promises to external observers (users, integrations, self). Always single-shot at ≤3 steps."
validation_passed: true
---
Execute every step below. Output the complete analysis.

## Step 1: Map Explicit Promises to Implementation
Locate behavioral claims against actual execution paths. Search for: docstrings or help text describing parameter behavior versus actual validation logic; error message templates referencing function names versus the actual raising function; type annotations or comments specifying return values versus what's actually returned; configuration variable descriptions claiming they control behavior versus code paths that read them.

## Step 2: Detect Stale Descriptive State
Find where self-description diverged from current behavior through evolutionary drift. Search for: banner text or status messages containing hardcoded version numbers or module names; cache key generation logic in save paths versus different logic in load/retrieval paths; deprecation warnings that reference old function names or migration paths; comments explaining "why" for logic that has since been refactored away; argument names in command-line parsers versus their internal variable references.

## Step 3: Identify Asymmetric Documentation Contracts
Reveal where public-facing documentation makes guarantees the private implementation cannot uphold. Look for: Orphaned Documentation Claims where README or API docs describe features with no implementation trace; Dead Configuration Paths where commented config options reference removed subsystems; Migration Message Decay where upgrade instructions reference non-existent intermediate states; Semantic Type Violations where documented return types don't match runtime unions or optionals.
