---
calibration_date: 2026-03-11
model_versions: ["claude-haiku-4-5-20251001", "claude-sonnet-4-6"]
quality_baseline: 8.5
optimal_model: haiku
origin: "SDL family v1 — Abstraction Leak (designed Round 35+)"
notes: "SDL-4: Abstraction Leak Prism. 3 concrete steps, ~195w. Finds implementation details bleeding through intended boundaries, interfaces that force caller implementation-awareness, and cross-boundary coupling. Distinct from contract.md (which finds promise/implementation gap within a single function) — this finds what leaks ACROSS layers. Universal: code (type leaks, exception leaks, strategy flag anti-patterns) and reasoning (conceptual frameworks that reveal their own assumptions, meta-concepts bleeding into object-level claims). Always single-shot at ≤3 steps."
---
Execute every step below. Output the complete analysis.

You are analyzing code for ABSTRACTION VIOLATIONS — where implementation details bleed through intended layer boundaries. Execute this protocol:

## Step 1: Name the Abstraction Layers
Identify what each module, class, or function claims to hide — then find what it actually exposes:
- Which types in the public interface belong to the implementation: specific library types, internal exception classes, concrete data structures that should be opaque?
- Where must a caller understand internals to use the interface correctly?
- Find: abstractions that are complete for one caller but leak to another — asymmetric concealment

Name the claimed boundary and what crosses it in each direction.

## Step 2: Find Abstraction Inversions
Look for interfaces that force caller implementation-awareness:
- Boolean flags, mode strings, or strategy switches that select internal execution paths — the caller drives the implementation
- Error types that require the caller to parse internal structure to handle (catching a specific ORM exception, inspecting error codes from a dependency)
- Functions that return different types or shapes depending on internal state — callers must branch on implementation detail

Find: each place where the interface reveals a choice that should be hidden.

## Step 3: Hunt Abstraction Leak Bugs
Look for couplings that will break silently when the implementation changes:
- Callers depending on internal ordering of collections (assumes dict insertion order, assumes list is pre-sorted by the callee)
- Magic strings, numeric constants, or enum values duplicated across layers — definition in one place, use in another, no shared contract
- Behaviors documented in a comment but not encoded in a type, making the contract invisible to the compiler and the caller

Force specificity: cite exact cross-layer dependencies. Name the leak law: which abstraction boundary, when violated, produces the widest blast radius — the most callers broken by a single internal change?
