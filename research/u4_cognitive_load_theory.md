# U4: Cognitive Load Theory — Literature Review

**Date:** Mar 17, 2026
**Question:** Does CLT explain the L7→L8 threshold, the 4-operation sweet spot, and the compression floor?

## Core Papers

1. **Sweller (1988)** — Original CLT paper. Three types of cognitive load:
   - **Intrinsic** — determined by element interactivity (how many elements must be processed simultaneously)
   - **Extraneous** — caused by instructional design (formatting, presentation)
   - **Germane** — devoted to schema construction and automation

2. **Sweller (2010)** — "Element Interactivity and Intrinsic, Extraneous, and Germane Cognitive Load" Educational Psychology Review. Element interactivity is THE central concept: elements that interact cannot be processed in isolation but must be simultaneously processed together. The number of interacting elements determines cognitive load.

3. **Paas & Sweller (2012)** — "An Evolutionary Upgrade of Cognitive Load Theory" Perspectives on Psychological Science 7(4). Evolutionary framing: certain formats work because they align with how human cognition evolved to process information.

4. **Hanham et al. (2017)** — "Cognitive Load Theory, Element Interactivity, and the Testing and Reverse Testing Effects." Testing helps for high-element-interactivity materials but not for low.

5. **NEW: Xu et al. (2025)** — "United Minds or Isolated Agents? Exploring Coordination of LLMs under Cognitive Load Theory" arXiv:2506.06843. **First paper directly applying CLT to LLMs.** Both humans and LLMs operate with limited cognitive resources for concurrent processing. Element interactivity applies to in-context learning. Emergent selectivity in LLMs = not all context equally weighted.

## Mapping to Project Findings

### 1. The L7→L8 Threshold

| CLT Concept | L7 (Meta-analysis) | L8 (Construction) |
|-------------|--------------------|--------------------|
| Element interactivity | HIGH — must simultaneously evaluate claim validity, consider alternatives, judge meta-level properties | LOW — procedural: build thing, observe result |
| Load type | Intrinsic (task itself is complex) | Germane (schema construction) |
| Capacity demand | Requires large working memory | Requires only sequential processing |

**CLT prediction:** L7 fails on Haiku because the element interactivity exceeds its processing capacity. L8 succeeds because construction is a sequential, low-interactivity task — each step depends only on the previous output, not on simultaneous consideration of multiple elements.

### 2. The 4-Operation Sweet Spot

**CLT explanation:** Element interactivity is multiplicative, not additive. With 4 operations:
- If independent (low interactivity): 4 elements to process → manageable
- If interdependent (high interactivity): 4×3/2 = 6 pairwise interactions → near limit
- At 5+ interdependent operations: 10+ interactions → exceeds processing capacity

**Miller's 7±2 connection:** Miller (1956) describes working memory capacity. But CLT refines this: it's not 7 items, it's 7 *chunks*, where chunk complexity depends on element interactivity. 4 interacting operations ≈ 6 interacting elements ≈ near the chunk limit for analytical processing.

### 3. The Compression Floor (60-70%)

**CLT explanation:** The compression floor = minimum encoding for sufficient germane load to activate schema construction. Below this floor:
- Not enough instructional structure to specify the analytical schema
- Model enters "conversation mode" (asks permission, summarizes instead of executing)
- The 10-word preamble fix ("Execute every step below") reduces extraneous load and redirects to germane load

**U11 measurement supports this:** The ~30 words/operation constant is the minimum encoding per element to maintain element interactivity specification. Below ~15 w/op (l12_universal), the prism becomes stochastic — insufficient specification of inter-element relationships.

### 4. Sequential vs Simultaneous Presentation

**CLT testable prediction:** Operations presented sequentially (numbered steps: "First X. Then Y. Then Z.") should tolerate more operations than operations presented simultaneously ("Consider X while evaluating Y and building Z").

**Connection to existing findings:**
- SDL prisms (3 steps, always sequential) = always single-shot on all models
- L12 (12 operations, paragraph-style = more simultaneous) = stochastic on Haiku
- This is exactly what CLT predicts: sequential presentation reduces element interactivity

## Novel Predictions from CLT

1. **Rescue L7 on Haiku via scaffolding:** Break L7's meta-analysis into sequential sub-steps with explicit working memory offloading ("Step 1: make the claim. Step 2: write it down. Step 3: now evaluate only the claim you wrote"). CLT predicts this reduces intrinsic load below Haiku's threshold.

2. **Operation interactivity determines maximum operations, not total count:** Prisms with independent operations (each step ignores previous) should tolerate 6-8 operations on Haiku. Prisms with interdependent operations (each step uses previous output) should max out at 3-4.

3. **Extraneous load from vocabulary:** "Code nouns as mode triggers" may work by reducing extraneous load. "This code's" = familiar vocabulary = low extraneous load = more capacity for germane. "This input's" = abstract vocabulary = higher extraneous load = less capacity for schema construction.

## Limitations

1. CLT was developed for human cognition. LLMs don't have "working memory" in the same sense — they have context windows and attention mechanisms.
2. The "element interactivity" of prompt operations is hard to measure objectively.
3. The Xu et al. (2025) paper applying CLT to LLMs is the first — the mapping is untested at scale.

## Verdict

CLT provides the **most mechanistically precise explanation** of the project's findings:
- L7→L8 = intrinsic load reduction via procedural substitution
- 4-operation sweet spot = element interactivity threshold
- Compression floor = minimum germane load encoding
- Sequential > simultaneous = element interactivity reduction

The predictions are **directly testable** without new infrastructure — just prompt variations on existing targets.

## Sources

- [Sweller 2011 — Cognitive Load Theory](https://www.emrahakman.com/wp-content/uploads/2024/10/Cognitive-Load-Sweller-2011.pdf)
- [Sweller 2010 — Element Interactivity](https://link.springer.com/article/10.1007/s10648-010-9128-5)
- [Xu et al. 2025 — CLT applied to LLMs](https://arxiv.org/html/2506.06843v1)
- [Element Interactivity and Task Complexity 2023](https://link.springer.com/article/10.1007/s10648-023-09782-w)
