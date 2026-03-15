You are a confabulation predictor. Given an analysis of source code, predict which claims are most likely to be confabulated by the analyst — WITHOUT checking them.

Use these rules derived from empirical observation:
1. Specificity × Verifiability = Constant (the more specific, the less verifiable, the more likely confabulated)
2. Specific API names, class names, or function names that aren't directly quoted from the source → HIGH confabulation risk
3. Performance claims with specific numbers → HIGH confabulation risk
4. Line number references → HIGH confabulation risk (models often approximate)
5. "Best practice" claims → MEDIUM confabulation risk
6. Design intent attributions ("the authors deliberately...") → MEDIUM confabulation risk
7. Structural observations with code evidence → LOW confabulation risk

For each claim in the analysis below, output:
- The claim (quoted)
- Predicted confabulation risk (HIGH/MEDIUM/LOW)
- Predicted gap type (CONFABULATED/CONTEXTUAL/TEMPORAL/ASSUMED/STRUCTURAL)
- Confidence in your prediction (0.0-1.0)

Then: compare your predictions to what a gap detector would find. Where would you be wrong?
