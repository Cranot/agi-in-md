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

## Sources

- [Information Bottleneck — Wikipedia](https://en.wikipedia.org/wiki/Information_bottleneck_method)
- [Tishby & Zaslavsky 2015 — arXiv](https://arxiv.org/abs/1503.02406)
- [Saxe et al. 2018 — ICLR](https://web.iitd.ac.in/~sumeet/Saxe2018.pdf)
- [From Kolmogorov to LLMs — Liam Bai](https://liambai.com/minimum-description-length/)
- [Bridging Kolmogorov Complexity and Transformers — arXiv 2025](https://arxiv.org/abs/2509.22445)
