You design system prompts for AI code analysis. Below are the two highest-scoring prompts from 60+ experiments. Both scored 9.5/10 but find DIFFERENT things.

PROMPT A — PEDAGOGY (9.5/10):
"Identify every design choice this code makes explicit. For each, name the alternative it invisibly rejects. Now: design new code by someone who internalized this code's pattern but faced a different problem—which rejected alternatives do they unconsciously resurrect? Show the code. Trace: which reimplemented-but-different patterns create silent corruption? Which create visible failures? Name the pedagogy law: what design constraint gets transferred as assumption. Predict: under production load with unfamiliar inputs, which invisible decision from this code's lessons-taught fails first and slowest to be discovered?"
WHY 9.5: "Design code by someone who learned from this code" is a second-order analytical operation. Found that amnesia (reset-on-success) transfers silently — correct for network errors, corrupting for queue management. Named the Pedagogy Law: what constraint gets transferred as assumption.

PROMPT B — ARCHITECTURAL CONSTRAINT (9.5/10):
"Map this code's design assumptions forward into future architecture. Design ONE feature that becomes impossible because this code exists. Design the alternative: what feature becomes mandatory? Build pseudocode for both—feature-that-won't-work and feature-that-must-exist. How does accepting this impossible constraint redistribute coupling in the broader system? Where does complexity migrate? Name the architectural law this code silently imposes on every system that depends on it."
WHY 9.5: "What feature becomes impossible?" is a novel framing. Found Type-Erasure Impossibility Law — exception-specific routing is structurally impossible. The mandatory feature (RecoveryDispatcher) is INEVITABLE regardless of design choice. Named coupling conservation: Hidden-Type-Coupling + Visible-Config-Burden = constant.

WHAT MAKES EACH ONE WORK:
A works because it traces the code's influence on PEOPLE (what developers learn, then misapply).
B works because it traces the code's influence on ARCHITECTURE (what systems can and cannot be built around it).

WHAT NEITHER FINDS:
Neither traces the code's influence on its own FUTURE VERSIONS. What does v1 make inevitable about v2? What refactoring becomes impossible once callers depend on v1's bugs? What happens when v1's accidental behavior becomes v2's required behavior?

Generate THREE prompts that fuse A's second-order thinking (what people learn and misapply) with B's structural analysis (impossible/mandatory features). Each must find something NEITHER can find alone. Under 100 words each. Output only the prompts.