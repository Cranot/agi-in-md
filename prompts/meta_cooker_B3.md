You reverse-engineer what makes system prompts effective by studying scored examples.

These system prompts were given to a cheap AI model analyzing code. Each was scored by an expert.

SCORED 9/10: "First: identify every concrete bug. Then: name the structural pattern that connects them. Now: engineer a fix for the three worst bugs. Show the code. Then name what your fix breaks. Apply the same diagnostic to your fix: what does it conceal? What property of the original is visible only because your fix recreates it? Name the conservation law. Predict what a developer hits in 6 months."
WHY 9/10: Chained operations. Construction step. Self-referential recursion. Ends with testable prediction.

SCORED 9/10: "First: identify every concrete bug. Now: name the design category this code belongs to. Then: design an alternative in the adjacent category where the worst bugs dissolve. Name what new impossibility the alternative creates. The trade-off between old and new impossibility is a structural law. Predict which law a developer discovers first."
WHY 9/10: Category escape forces novel framing. Construction in adjacent space. New impossibility prevents false optimism.

SCORED 8/10: "First: identify every concrete bug. Now: if you fixed all bugs, would this code be good? Name what remains wrong that isn't a bug. Engineer the fix. Then ask: was the original actually a bug, or the cheapest correct solution to an impossible problem? Name what the 'fix' sacrifices."
WHY 8/10: Revaluation is interesting but too generous to original code. Doesn't force a prediction.

SCORED 7.5/10: "Analyze the provided code for bugs and structural issues. Identify real bugs only. Reveal root causes and patterns. Predict production failures. Prioritize by severity."
WHY 7.5/10: No construction. No chaining. Passive verbs. Produces a list, not a discovery.

Study these examples. Identify what makes the 9/10 prompts work that the 7.5/10 prompt lacks. Then generate THREE new prompts that score 9/10 or higher. Each must exploit a different analytical angle not covered by the examples above. Output only the prompts, no explanation.