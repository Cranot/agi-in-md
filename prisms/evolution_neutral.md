---
name: evolution_neutral
description: Evolution prism NEUTRAL (Opus-designed) — domain-neutral version of Evo. Maps shotgun surgery targets, tests if restructures create new coupling, finds irreducible coupling invariant. Works on ANY input (code, reasoning, business, research). 3 steps, ~160 words. Code targets should use evolution.md instead (better specificity). Quality on reasoning ~7/10 (some software-framing leakage).
type: evolution
steps: 3
words: 160
domain: universal
optimal_model: sonnet
---
Execute every step below. Output the complete analysis.

## Step 1: Shotgun Surgery Map
For each behavior this system implements: which components must ALL change together to modify that behavior? A behavior is a "shotgun surgery" target if changing it requires touching 3+ components. List every shotgun surgery target, the components involved, and the shared assumption that binds them.

## Step 2: Why They're Bound
For each shotgun surgery target: is the binding explicit (declared contract, shared schema, formal specification) or implicit (convention, duplicated patterns, undocumented invariant)? For implicit bindings: name the specific assumption. Propose the minimal restructure that makes it explicit. After each restructure, check: does it CREATE new shotgun surgery targets elsewhere?

## Step 3: The Coupling Budget
Name the total coupling budget — the irreducible minimum of cross-component dependencies for this system's functionality. State the conservation law: coupling moves but doesn't disappear. What does reducing coupling HERE cost THERE? Output a table: Behavior | Components Bound | Binding Type | Shared Assumption | Restructure Creates.
