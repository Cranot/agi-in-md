# U11: Words-Per-Operation Measurement Across All 50 Prisms

**Date:** Mar 17, 2026
**Question:** Is the words-per-operation ratio approximately constant across prisms? (Tests MDL principle — Grünwald 2007)

## Result: MDL PREDICTION SUPPORTED (84%)

42/50 prisms have a words-per-operation ratio within 2x of the median (31.2 w/op).

| Statistic | Value |
|-----------|-------|
| Mean | 37.5 w/op |
| Median | 31.2 w/op |
| StdDev | 24.7 |
| Min | 12.3 (l12_universal — maximally compressed) |
| Max | 128.0 (prereq — mostly prose, not analysis) |
| Range factor | 10.4x |
| Within 2x of median | 42/50 (84%) |

## Full Table

| Prism | Words | Ops | W/Op |
|-------|-------|-----|------|
| api_surface | 158 | 7 | 22.6 |
| api_surface_neutral | 179 | 6 | 29.8 |
| arc_code | 122 | 4 | 30.5 |
| archaeology | 184 | 2 | 92.0 |
| audit_code | 245 | 7 | 35.0 |
| behavioral_synthesis | 179 | 6 | 29.8 |
| claim | 74 | 3 | 24.7 |
| codegen | 165 | 5 | 33.0 |
| contract | 85 | 3 | 28.3 |
| cultivation | 176 | 2 | 88.0 |
| deep_scan | 270 | 8 | 33.8 |
| degradation | 61 | 3 | 20.3 |
| error_resilience | 201 | 5 | 40.2 |
| error_resilience_70w | 85 | 6 | 14.2 |
| error_resilience_compact | 113 | 6 | 18.8 |
| error_resilience_neutral | 202 | 6 | 33.7 |
| evidence_cost | 171 | 6 | 28.5 |
| evolution | 151 | 6 | 25.2 |
| evolution_neutral | 168 | 7 | 24.0 |
| fidelity | 213 | 5 | 42.6 |
| fix_cascade | 192 | 6 | 32.0 |
| identity | 214 | 5 | 42.8 |
| knowledge_audit | 220 | 6 | 36.7 |
| knowledge_boundary | 296 | 7 | 42.3 |
| knowledge_typed | 119 | 5 | 23.8 |
| l12 | 332 | 12 | 27.7 |
| l12_complement_adversarial | 179 | 5 | 35.8 |
| l12_synthesis | 184 | 5 | 36.8 |
| l12_universal | 86 | 7 | 12.3 |
| l12g | 190 | 14 | 13.6 |
| optimize | 151 | 6 | 25.2 |
| oracle | 324 | 15 | 21.6 |
| pedagogy | 76 | 3 | 25.3 |
| prereq | 384 | 3 | 128.0 |
| reachability | 162 | 6 | 27.0 |
| rejected_paths | 65 | 3 | 21.7 |
| scarcity | 65 | 3 | 21.7 |
| sdl_abstraction | 313 | 7 | 44.7 |
| sdl_coupling | 301 | 7 | 43.0 |
| sdl_simulation | 215 | 6 | 35.8 |
| sdl_trust | 270 | 8 | 33.8 |
| security_v1 | 167 | 7 | 23.9 |
| simulation | 189 | 4 | 47.2 |
| state_audit | 206 | 6 | 34.3 |
| strategist | 940 | 8 | 117.5 |
| testability_v1 | 158 | 7 | 22.6 |
| verify_claims | 214 | 9 | 23.8 |
| writer | 498 | 5 | 99.6 |
| writer_critique | 217 | 5 | 43.4 |
| writer_synthesis | 299 | 8 | 37.4 |

## Outliers (>2x or <0.5x median)

**HIGH outliers** (>62.4 w/op):
- `prereq` (128.0) — prose-heavy knowledge gap scanner, not analytical operations
- `strategist` (117.5) — reference documentation listing all modes/prisms, not analytical steps
- `writer` (99.6) — creative writing instructions, different cognitive type
- `archaeology` (92.0) — paragraph-style with 2 heavy steps instead of many light ones
- `cultivation` (88.0) — same paragraph-style pattern

**LOW outliers** (<15.6 w/op):
- `l12_universal` (12.3) — maximally compressed L12, every word carries an operation
- `l12g` (13.6) — 14 ops packed into 190 words, highest operation density
- `error_resilience_70w` (14.2) — intentionally compressed variant

## Interpretation

The core analytical prisms cluster tightly around **25-45 words per operation**. This is consistent with MDL: there is an irreducible encoding cost per cognitive operation (~30 words), and the compression floor (60-70%) reflects approaching this minimum.

**Outlier pattern:** Prisms that deviate are either:
1. Non-analytical (prereq, strategist, writer) — different cognitive type
2. Maximally compressed (l12_universal, l12g) — below the stable floor
3. Paragraph-style (archaeology, cultivation) — fewer but heavier operations

**The ~30 w/op constant** suggests each cognitive operation requires approximately 30 words to encode in a way that reliably activates the model. Below ~15 w/op, prisms become stochastic (confirmed by l12_universal needing Sonnet). Above ~45 w/op, extra words are scaffolding, not operations.

## Connection to MDL (Grünwald 2007)

The Minimum Description Length principle states: the best model is the shortest program that generates the data. Applied here:
- Each prism is a "program" for generating structural analysis
- The ~30 w/op ratio is the MDL of each cognitive operation
- The compression floor = sum of all operations' MDLs
- You cannot compress below this floor without losing operations

This is the first quantitative evidence that the compression floor has a theoretical explanation, not just an empirical one.
