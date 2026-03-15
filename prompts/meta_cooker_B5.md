A system prompt scored 9.5/10 on code analysis by finding the "fix-to-new-bug dependency graph" — for each bug, it traced what fix would create what new invisible bug.

But that prompt has three blind spots:
1. It only looks FORWARD (bug → fix → new bug). It never looks BACKWARD (what prior decision made this bug inevitable?)
2. It treats each bug independently. It never asks: do these bugs NEED each other? Would fixing one make another unfixable?
3. It finds what happens when developers ACT. It never finds what happens when developers DON'T act — what the code silently degrades into if nobody touches it for a year.

Design THREE prompts, each targeting one blind spot. Each must:
- Start with "First: identify every concrete bug"
- Include a construction step (build, write, or design something)
- End with a testable prediction
- Be under 80 words

Output only the three prompts, labeled by which blind spot they target.