You design system prompts for AI code analysis. Here are results from previous prompts, scored by an expert.

SCORED 9.5/10 — BEST SO FAR:
"First: identify every concrete bug. For each, trace the decision that enabled it. What rejected path would have prevented this bug but created another invisible one? Design the system taking all rejected paths. Show the code. Which visible bugs vanish? Which invisible dangers emerge? Name the law: what class of bug migrates between visible and hidden. Predict which migration a developer discovers first under load."
WHY 9.5: Forces the model to map the FIX-TO-NEW-BUG dependency graph. Found "Visibility Inversion Theorem" — fixing race conditions creates invisible performance degradation. Novel analytical operation no human designed.

SCORED 9/10:
"First: identify every concrete bug. For each, name the resource scarcity it exposes—what this code assumes will never run out. Then: design a system that gambles on opposite scarcities. Show the code and name the new trade-offs. Name the conservation law. Predict what remains unmovable in 6 months."
WHY 9/10: "What does this code assume will never run out?" is a genuinely novel question. Named 4 scarcities. Built an alternative architecture.

SCORED 7.5/10:
"Find what the code requires from inputs. Find what it promises for outputs. Name where those collide. Engineer the input that triggers both failures."
WHY 7.5: Too abstract. Model couldn't follow the specific analytical angle — collapsed into a generic bug list.

The 9.5 prompt found something NO other prompt found: the invisible bugs that fixes create. The gap: no prompt has yet found the invisible REQUIREMENTS that the code silently imposes on its callers, or the invisible ASSUMPTIONS callers make about the code that the code never promised.

Generate THREE prompts that each find something the 9.5 prompt cannot find. Each must use a different blind spot of the 9.5 prompt. Under 100 words each. Output only the prompts.