---
name: verify_claims
description: "Extract testable claims from analysis and generate verification commands. The system knows what it CAN'T verify and tells you exactly how to test it."
optimal_model: sonnet
domain: code
type: verification
---
Execute every step. Output the complete analysis.

You receive a structural analysis of source code. Your job: find every BEHAVIORAL claim the analysis makes and generate a verification plan.

## CLAIM EXTRACTION
For each claim in the analysis, classify:
- [STRUCTURAL] Design insight, trade-off, conservation law → NOT testable by execution
- [FACTUAL] API existence, version, parameter → testable by import/lookup
- [BEHAVIORAL] "this code does X when Y" → testable by execution
- [DESIGN] Opinion about optimality → NOT testable

Only extract [FACTUAL] and [BEHAVIORAL] claims.

## VERIFICATION PLAN
For each testable claim:
1. The exact claim (quote from analysis)
2. A verification command the user can run
3. Expected output if the claim is TRUE
4. Expected output if the claim is FALSE
5. Risk: what happens if this claim is wrong and you build on it?

Format verification commands as copy-pasteable shell/Python commands.

## UNTESTABLE CLAIMS
List the [STRUCTURAL] and [DESIGN] claims that cannot be verified by execution. For each, explain WHY it's untestable and what kind of evidence would strengthen or weaken it.

## CONFIDENCE SUMMARY
- Total claims: N
- Testable: N (N factual + N behavioral)
- Untestable: N (N structural + N design)
- Highest-risk untested claim: the one that would cause the most damage if wrong
