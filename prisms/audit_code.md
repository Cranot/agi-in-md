---
name: audit_code
description: Self-Consistency Audit prism — finds feature registration gaps across declaration surfaces (CLI args, dispatch tables, help text, parsers, pipelines). 3 steps, ~200w. Detects wired-but-undocumented, declared-but-unwired, and silently-ignored features. Works on any multi-surface system (CLI tools, web routers, plugin architectures). Conservation law encoded: DETECTION_BREADTH x CONTEXT_DEPTH = CONSTANT — forces exhaustive per-surface enumeration to avoid surface conflation (treating layered registrations as flat).
quality_baseline: 9.0
optimal_model: haiku
type: self_consistency_audit
steps: 3
words: 200
origin: "Research Round 36 — 6 experiments on prism.py self-analysis accuracy. Optimal pipeline: 5-surface decomposition (97%) + adversarial filter (99%). Root cause of false positives: surface conflation."
---
Execute every step below. Output the complete analysis.

You are auditing this code for REGISTRATION GAPS — features that exist on one surface but are missing from another. Execute this protocol:

## Step 1: Enumerate Every Surface

List every place where features are declared, dispatched, or documented. Treat each as independent — NEVER merge related surfaces. Common surfaces: argument parsers, command dispatch tables, help/usage text (each layer separately: auto-generated vs hardcoded), input parsers (regex, keyword extraction), pipeline/workflow definitions, configuration schemas.

For each surface: list every feature it registers. Cite exact locations (function, line, string).

## Step 2: Cross-Reference Matrix

For every feature found on ANY surface, check its presence on ALL other surfaces. Build the matrix:

| Feature | Surface A | Surface B | Surface C | ... |
|---------|-----------|-----------|-----------|-----|
| feature_x | line 42 | MISSING | line 891 | ... |

A gap = present on one surface, absent on another. List every gap.

## Step 3: Classify Each Gap

For each gap, determine:
- **TRUE GAP**: Feature is declared but never wired to dispatch — calling it does nothing or errors silently
- **VISIBILITY GAP**: Feature works but is not discoverable (missing from help, docs, or completions)
- **BY-DESIGN**: Surfaces intentionally differ (internal-only features, deprecated paths, composed-not-declared features)
- **FALSE POSITIVE**: Feature IS present but under a different name, alias, or abstraction layer

For TRUE GAPs and VISIBILITY GAPs: name the exact wire that is missing. What code would connect them?
