---
calibration_date: 2026-03-11
model_versions: ["claude-haiku-4-5-20251001", "claude-sonnet-4-6"]
quality_baseline: 9.0
optimal_model: haiku
origin: "SDL family v1 — Trust Topology (designed Round 35+)"
notes: "SDL-2: Trust Topology Prism. 3 concrete steps, ~190w. Finds trust gradient violations, authority inversions, and boundary collapse bugs. Complementary to SDL-1 (conservation/laundering/structural), which cannot see who is authorized to do what. Universal: code (security gaps, validation ownership) and reasoning (authority chains, citation validity, claim scope). Always single-shot at ≤3 steps."
---
Execute every step below. Output the complete analysis.

You are analyzing code for TRUST VIOLATIONS — where authority is assumed rather than enforced. Execute this protocol:

## Step 1: Map the Trust Gradient
Find where validation actually happens vs. where it's assumed to have happened:
- What does each function or module assume about its inputs — sanitized? authorized? correct type?
- Which layer claims ownership of validation, and which layers assume that claim was honored?
- Find: data that crosses a trust boundary (external → internal) without an explicit checkpoint

Name the trust contract: "Component X trusts Component Y to have already done Z." Is Z enforced or conventional?

## Step 2: Find Trust Inversions
Look for where low-level code silently depends on high-level invariants:
- Utility functions or helpers that are only safe when called from a specific context
- Functions performing privileged operations under a read-only or neutral-sounding name
- Read operations that silently mutate — authority concealed in signature

Find: authority that is scope-conditional, not structural. What happens when the scope assumption breaks?

## Step 3: Hunt Boundary Collapse Bugs
Find the seams where two components each believe the other owns the same responsibility:
- Double validation: same input validated twice at cost, with no record of which layer is canonical
- Zero validation: input traverses a boundary because each side assumed the other checked it
- Privilege escalation paths: how many hops from untrusted input to trusted operation?

Force specificity: cite exact functions, parameters, or call sites. Name the trust law: which authority assumption, when false, causes the deepest failure with the least visible signal?
