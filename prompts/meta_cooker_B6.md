You design system prompts for AI code analysis. Below are the four highest-scoring prompts from 50+ experiments, with what makes each work.

SCORED 9.5/10 — CHAMPION:
"First: identify every concrete bug. For each, trace the decision that enabled it. What rejected path would have prevented this bug but created another invisible one? Design the system taking all rejected paths. Show the code. Which visible bugs vanish? Which invisible dangers emerge? Name the law: what class of bug migrates between visible and hidden. Predict which migration a developer discovers first under load."
WHY 9.5: Maps the FIX-TO-NEW-BUG DEPENDENCY GRAPH. Found "Visibility Inversion Theorem." Novel operation: rejected paths create invisible bugs.

SCORED 9/10 — SCARCITY LENS:
"First: identify every concrete bug. For each, name the resource scarcity it exposes—what this code assumes will never run out. Then: design a system that gambles on opposite scarcities. Show the code and name the new trade-offs. Name the conservation law. Predict what remains unmovable in 6 months."
WHY 9/10: "What does this code assume will never run out?" is a genuinely novel question. Named 4 scarcities. Built alternative architecture.

SCORED 9/10 — IMPLICIT CONTRACTS:
"Identify implicit contracts: preconditions callers must satisfy, postconditions code guarantees—neither documented. Design a caller that violates each contract invisibly. Show which violations corrupt state silently, which fail visibly. Engineer enforcement: add validation. Show code. Which violations become detectable? Which impossible? Each enforcement creates a new implicit contract. Name it."
WHY 9/10: Found 9 implicit contracts. Recursive: each enforcement creates new contract. Mapped detection vs impossibility.

SCORED 9/10 — TEMPORAL DECAY:
"First: identify every concrete bug. Design a decay timeline: if no one touches this code for 6/12/24 months, which bugs metastasize? Which error paths silently corrupt data instead of failing? Build a degradation model: brittleness increases where? Test: predictably break the system by only waiting—no new bugs needed."
WHY 9/10: Temporal lens is novel. "Break it by only waiting" produced 4 runnable tests. Decay timeline from latent to liability.

ANALYTICAL OPERATIONS FOUND IN THESE PROMPTS:
- Dependency graph (fix → new bug)
- Construction (build alternative, show code)
- Inversion (take rejected paths / opposite scarcities)
- Recursion (enforcement creates new contract)
- Temporal projection (what happens in 6/12/24 months)
- Classification (visible vs hidden, detectable vs impossible)
- Named law/theorem (forces crystallization)

WHAT NO PROMPT HAS FOUND:
None asks what the code TEACHES its future maintainers — what mental model it installs, what questions it makes unaskable, what design alternatives it makes invisible by existing. None asks what happens when this code INTERACTS with code written by someone who read this code — the second-order effects of the code's implicit pedagogy.

Generate THREE prompts that score 10/10. Each must use at least one analytical operation from the list above PLUS find something none of these four prompts can find. Under 100 words each. Output only the prompts.