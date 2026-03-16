# U2: Information Bottleneck Theory — Literature Review

**Date:** Mar 17, 2026
**Question:** Is P19 (`Depth x Universality = constant`) the IB Lagrangian in disguise?

## Core Papers

1. **Tishby, Pereira & Bialek (1999)** — Original IB paper. Introduced the optimization: `min I(X;Z) - β·I(Z;Y)` where X=input, Z=compressed representation, Y=relevant variable, β=tradeoff parameter.

2. **Tishby & Zaslavsky (2015)** — "Deep Learning and the Information Bottleneck Principle" IEEE ITW. Applied IB to DNNs: any DNN can be quantified by mutual information between layers and input/output variables. [arXiv:1503.02406](https://arxiv.org/abs/1503.02406)

3. **Shwartz-Ziv & Tishby (2017)** — Training DNNs shows two phases: (1) fitting (mutual info with input AND output increases) then (2) compression (mutual info with input decreases while output info preserved).

4. **Saxe et al. (2018)** — "On the Information Bottleneck Theory of Deep Learning" ICLR. Challenged: compression phase may depend on activation function (ReLU doesn't show it), not universal. The IB claims don't hold in the general case.

## Mapping to P19

| IB Term | Project Term | Interpretation |
|---------|-------------|----------------|
| I(Z;Y) — mutual info with output | **Depth** | How much structural information the prism output captures |
| I(X;Z) — mutual info with input | **1/Universality** | How much domain-specific info the prompt retains |
| β — Lagrange multiplier | **The constant C** in P19 | Tradeoff parameter |

**The mapping:** A universal prompt (l12_universal, 73w) minimizes I(X;Z) — it drops domain-specific vocabulary, retaining only the analytical operations. This forces lower I(Z;Y) — less depth. A domain-specific prompt (l12, 332w) retains more domain info → higher depth but lower universality.

## Phase Transitions

IB theory predicts **structural phase transitions** at critical values of β where the representation reorganizes. In the project's terms:

- **L12 → l12_universal transition (332w → 73w):** May be a phase transition where domain-specific vocabulary is dropped as a discrete event, not a gradual compression.
- **The 60-70% compression floor:** May correspond to a critical β below which the compressed representation can no longer maintain the analytical operations (mutual info with output drops below the threshold for conservation law generation).

**Testable prediction:** Parameterize prism word count from 73w to 332w in ~30w steps. Plot (depth, universality). If the curve shows discrete jumps (phase transitions) rather than smooth decay, IB is supported. If smooth, the tradeoff is continuous and IB phase transitions don't apply.

## IB Applied to LLMs

- Recent work (2025) connects Kolmogorov complexity to transformer compression, showing asymptotically optimal description length objectives exist for transformers.
- The IB framework has been used to analyze information flow through transformer layers, but NOT applied to system prompts or cognitive compression.
- **This would be novel**: applying IB to prompt design as a compression problem is unexplored territory.

## Limitations

1. **Saxe et al. (2018) challenge**: The compression phase in IB may be activation-function dependent, not universal. Our "compression floor" might be a different phenomenon.
2. **Computability**: Kolmogorov complexity is uncomputable — practical MDL uses approximations. Our word-count measurements are rough proxies.
3. **The β analogy is loose**: In IB, β is a continuous parameter optimized over. In P19, "the constant" is empirically measured, not optimized.
4. **Phase transitions require data**: We need many data points on the compression curve to detect discrete jumps. Currently we have only ~5 data points (l12_universal 73w, SDL 180w, L12 332w, and a few others).

## Verdict

The IB analogy is **promising but unproven**. The mapping is clean on paper (P19 ≈ IB Lagrangian), but the critical test — whether the depth-universality tradeoff shows phase transitions — hasn't been run. The U11 result (MDL supported, ~30 w/op constant) is consistent with IB's prediction that there's an irreducible encoding cost, but doesn't prove the IB mechanism specifically.

**Next step:** Run the parameterized word-count experiment (U2 experiment in ROADMAP). 10 targets × 10 compression levels = 100 runs. ~$5 on Haiku. 1-2 days.

## Additional Papers Found (from agent research)

- **Zaslavsky, Kemp, Regier & Tishby (2018)** — "Efficient Compression in Color Naming and Its Evolution" PNAS. Human color-naming systems achieve near-optimal IB compression. Languages = different positions on beta axis. Color categories evolve through structural phase transitions. **Direct analogue:** different prisms at different word counts = different beta positions. Compression levels = IB phase transitions.
- **Yang et al. (2025)** — "Exploring Information Processing in LLMs: Insights from IB Theory" arXiv:2501.00999. LLMs compress input into task-specific spaces. Introduced IC-ICL (Information Compression-based Context Learning). Validates that prisms act as compression lenses defining the task space.
- **QUITO-X (EMNLP 2025)** — arXiv:2408.10497. Context compression as IB problem. 80M model with IB achieves 25% better compression. Compressed contexts sometimes outperform full contexts — confirms P17 (compression forces domain neutrality).
- **Deletang et al. (ICLR 2024)** — "Language Modeling Is Compression" arXiv:2309.10668. LLMs are general-purpose compressors. Chinchilla 70B beats domain-specific compressors.
- **Futrell & Hahn (Nature Human Behaviour 2025)** — Natural languages minimize predictive information (excess entropy) — direct IB formulation at every linguistic level.

## Key Limitation: P19 Is Multiplicative, IB Is Additive

P19: Depth × Universality = constant (hyperbola). IB Lagrangian: L = I(X;T) - β·I(T;Y) (linear for fixed β). The IB curve is concave, not hyperbolic. However, if Universality is measured as number of working domains (discrete) and Depth as average quality, the product form could be an empirical approximation over a narrow range. Critical test: is the tradeoff steeper at low universality (IB predicts yes) or constant elasticity everywhere (hyperbola)?

## Sources

- [Information Bottleneck — Wikipedia](https://en.wikipedia.org/wiki/Information_bottleneck_method)
- [Tishby & Zaslavsky 2015 — arXiv](https://arxiv.org/abs/1503.02406)
- [Saxe et al. 2018 — ICLR](https://web.iitd.ac.in/~sumeet/Saxe2018.pdf)
- [Zaslavsky et al. 2018 — PNAS](https://www.pnas.org/doi/10.1073/pnas.1800521115)
- [Yang et al. 2025 — arXiv](https://arxiv.org/abs/2501.00999)
- [QUITO-X 2025 — arXiv](https://arxiv.org/abs/2408.10497)
- [Deletang et al. 2024 — arXiv](https://arxiv.org/abs/2309.10668)
- [Futrell & Hahn 2025 — arXiv](https://arxiv.org/abs/2405.12109)
- [From Kolmogorov to LLMs — Liam Bai](https://liambai.com/minimum-description-length/)
- [Bridging Kolmogorov Complexity and Transformers — arXiv 2025](https://arxiv.org/abs/2509.22445)
