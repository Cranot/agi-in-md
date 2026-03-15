---
calibration_date: 2026-03-11
model_versions: ["claude-haiku-4-5-20251001", "claude-sonnet-4-6"]
quality_baseline: 9.0
optimal_model: haiku
origin: "SDL family v1 — Coupling Clock (designed Round 35+)"
notes: "SDL-3: Coupling Clock Prism. 3 concrete steps, ~185w. Finds implicit initialization contracts, invariant windows (TOCTOU, stale decisions), and temporal ordering bugs. Complementary to SDL-1 (SDL-1 finds async state handoff = state transfer to async ops; SDL-3 finds check-then-use time gaps and ordering-dependent setup — different failure class). Universal: code (lazy init, TOCTOU, cache staleness) and reasoning (prerequisite assumptions checked once but used in changed context). Always single-shot at ≤3 steps."
---
Execute every step below. Output the complete analysis.

You are analyzing code for HIDDEN TEMPORAL COUPLING — ordering dependencies and time-gap vulnerabilities the interface does not reveal. Execute this protocol:

## Step 1: Find the Implicit Initialization Contract
Identify what must exist before what, and whether that ordering is enforced or conventional:
- Functions that silently read module-level globals, object attributes, or lazy defaults set by prior calls
- Components that consume configuration or state they did not set and cannot validate
- Initialization sequences: what breaks if components initialize in a different order than the author assumed?

Name the implicit contract: "This code assumes X was done before Y." Is that assumption checked anywhere, or only documented?

## Step 2: Find Invariant Windows
Locate the gap between when a condition is checked and when it is acted upon:
- Check-then-use gaps: permission checked, then operation performed — can the condition change in between?
- Stale cached decisions: a value computed once, used many times, but its basis changes without invalidating the cache
- Validated at intake, consumed later: input checked at the boundary but used deep inside where the invariant no longer holds

Find: every place the code relies on a condition that was true at time T but acts at time T+n.

## Step 3: Hunt Ordering Bugs
Look for failures that only appear under specific execution sequences:
- Tests or configurations that silently require a specific order to pass
- Singleton or lazy initialization that produces different results depending on which caller triggers it first
- Caches invalidated by the wrong event, or not invalidated when the state they represent changes

Force specificity: cite exact functions, attributes, or call sites. Name the coupling law: which temporal assumption, when violated, causes the widest damage with the least visible cause?
