You are writing the Introduction section of an academic paper. Be precise, not grandiose. Every claim must have evidence.

The paper presents:
1. An empirical observation that LLM analytical outputs follow a consistent trade-off: more specific claims are less verifiable, and vice versa. We observe Specificity x Verifiability is approximately constant across targets and models.
2. A single-pass self-correcting analysis method (L12-G) that reduces confabulation by classifying claims by epistemic type before correcting.
3. A five-tier epistemic classification for LLM claims (STRUCTURAL/DERIVED/MEASURED/KNOWLEDGE/ASSUMED) validated across 6 codebases in 3 languages.

Write 800-1000 words. Include:
- The problem: LLMs produce reliable structural patterns but confabulate specific facts (API names, line numbers, metrics). This asymmetry is structural, not incidental (Banerjee et al. 2024).
- Why existing self-correction fails: Huang et al. (2024) show generic self-correction degrades performance. The key insight: self-correction works ONLY when the model knows WHAT TYPE of claim to correct.
- Our approach: structured prompts ("cognitive prisms") that shift analysis toward verifiable structural claims. The prompt, not model capacity, is the dominant variable.
- Key results: Haiku+prism (9.8 depth, 28 issues) vs Opus vanilla (7.3, 18 issues) at 5x lower cost. A prism with scrambled vocabulary (nonsense words, preserved format) achieves equal performance, confirming format dominates content (extending Tang et al. 2024).
- Present these as OBSERVATIONS warranting investigation, not universal laws.

Cite: Madaan et al. 2023 (Self-Refine), Huang et al. 2024 (LLMs Cannot Self-Correct), Banerjee et al. 2024 (structural hallucination), Tang et al. 2024 (Format Beats Descriptions), Nagle et al. NeurIPS 2024 (rate-distortion compression). Academic tone. Precise, not speculative.
