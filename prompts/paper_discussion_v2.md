You are writing the Discussion, Limitations, and Conclusion sections.

DISCUSSION (600-800 words):
1. THEORETICAL FRAMING through Information Theory only. The specificity-verifiability trade-off is consistent with rate-distortion theory (Nagle et al. NeurIPS 2024): query-aware compression achieves lower distortion than query-agnostic. Our prisms are query-aware compressors — they direct the model toward structural claims (low distortion on patterns) at the cost of specific claims (high distortion on facts). The trade-off may reflect a fundamental information-theoretic constraint, but we present it as an empirical observation pending formal derivation. Connections to other frameworks (thermodynamics, category theory, cognitive science) are noted as potential directions, not claimed derivations.

2. WHY SELF-CORRECTION WORKS with claim typing. Huang et al. (2024) show generic self-correction fails. Our method works because claim-TYPE classification tells the model WHAT to correct — specific factual claims (KNOWLEDGE/ASSUMED) — while preserving structural claims (STRUCTURAL/DERIVED) that are reliable. This is consistent with the finding that LLMs have internal truth representations that verbalization reports unfaithfully (Azaria & Mitchell 2023).

3. THE EVALUATION PROBLEM. Our rubric rewards depth and conservation laws, which means L12 (which confabulates) scores higher than Oracle (which is honest). This illustrates a broader problem: evaluation metrics that reward fluency over accuracy may systematically prefer confabulating systems. We call for trust-aware evaluation metrics.

LIMITATIONS (400-500 words — be HONEST):
1. Small sample sizes (N=1-5 per condition for most experiments)
2. Haiku-as-judge evaluation (same model family, potential circular bias)
3. No human evaluation of output quality
4. Only tested on Claude and Gemini (cross-model transfer unknown for deep operations)
5. Python-dominant validation (Go and TypeScript are single-run preliminary)
6. The "conservation law" is an empirical observation on limited data, not a proven theorem
7. Autopoietic convergence tested only on one generation chain
8. Scrambled vocabulary result is N=1, needs replication
9. No downstream task validation (were identified bugs real? did fixes help?)

CONCLUSION (300 words):
Present modestly. The core contribution is practical: structured prompts that systematically classify claims by epistemic type enable self-correction that generic methods cannot achieve. The observation that specificity trades against verifiability across targets and models suggests a fundamental constraint worth investigating. The tool and all prompts are released for reproduction.

Academic tone. Honest about limitations. No overclaiming.
