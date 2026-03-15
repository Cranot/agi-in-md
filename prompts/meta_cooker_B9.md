You design system prompts for AI code analysis. 60+ experiments, one clear winner at 9.5/10:

THE CHAMPION (9.5/10):
"Design new code by someone who internalized this code's pattern but faced a different problem—which patterns do they unconsciously resurrect? Show the code. Trace which transferred patterns create silent corruption."
WHY 9.5: Second-order analysis — traces the code's influence on PEOPLE. Built a complete queue management system showing exactly where the transferred circuit-breaker pattern corrupts.

6 PROMPTS AT 9/10 (none matched 9.5):
- Fix-to-new-bug dependency graph (novel systematic mapping, but "fixes have trade-offs" is known)
- What the code assumes will never run out (novel question, good scarcity identification)
- Recursive enforcement cascades (each fix creates new contract)
- Temporal decay timeline (what degrades without code changes)
- V1 bug → V2 required feature (Hyrum's Law precisely formalized)
- Control boundary inversion (conservation of information cost)

WHY THE 9/10s FALL SHORT: Each applies ONE analytical lens deeply. The champion applies its lens AND crosses an analytical boundary (from analyzing CODE to analyzing PEOPLE WHO READ CODE). That boundary-crossing is what creates surprise.

DIMENSIONS NOT YET EXPLORED:
1. The code's relationship to its TEST SUITE — what does testing this code make UNTESTABLE about adjacent code?
2. The code as an ARGUMENT — what claim does this code make about the world, and is that claim true?
3. The code's FAILURE MODE as a feature — if this code fails in production, what does the failure TEACH the organization?

Generate THREE prompts that cross an analytical boundary the way the champion does. Each must move from analyzing the artifact to analyzing something OUTSIDE the artifact that the artifact shapes. Under 80 words each. Output only the prompts.