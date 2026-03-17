# All Champions — Master Index

**Date**: Mar 11, 2026 | **Total experiments**: 930+ | **Total champions**: 60+ | **Output types**: 20 | **Domains**: 9+
**Method**: All Haiku 4.5 unless noted. All solve via `prism.py --solve --pipe -m haiku --isolate`

---

## Quick Reference: The Absolute Best

| Category | Champion | Score | Size | What makes it THE best |
|----------|----------|-------|------|------------------------|
| **Code Review** | L12 (hand-crafted) | 9.8 | 332w prompt | Zero cook cost, instant, baseline everything beats |
| **Most Bugs** | EXP14 (full L12 few-shot) | 9.8 | — | 26 bugs — most ever from single call |
| **Deepest Code** | EXP31 (combined best) | 9.8 | — | 3 independent conservation laws |
| **Reasoning** | P2 (multi-law+M2) | 9.8+ | 44KB | ALL-TIME largest reasoning output, 23 defects |
| **Universal** | N1 (V1+M2) | 9.8+ | 30-33KB | 9.8+ on BOTH code AND reasoning |
| **Insight Extraction** | Run 4 / Run 23 / Sonnet 1 / Sonnet 2 | 9.3 | 1.4-2.9Kw | 4 co-champions, 20 conservation laws from 200w seed |
| **Largest Output** | Z8 (audience) | 9.8+ | 54KB | ALL-TIME largest single output |
| **Most Rigorous** | AA2 (math proof) | 9.8+ | 26KB | 8D design space, 256 cells, 16 forbidden |
| **Deepest Assumptions** | Q2 (compression+M2) | 9.8+ | 20KB | 109:1 compression ratio, 12 tiered assumptions |
| **Most Novel** | Q1 (counterfactual+M2) | 9.8 | 24KB | X/G oscillation discovery |
| **First Falsifiable** | P1 (construction+prediction+M2) | 9.8+ | 19KB | 3 dated predictions with likelihoods |
| **Best Combo** | Z4 (steelman+entropy) | 9.8+ | 35KB | STRONGEST sequential combo tested |
| **Best Pipeline** | X5 (Sonnet cook → Haiku solve) | 9.8+ | 39.8KB | 2x deeper than Haiku cook |
| **Compressed** | BB3 (51w lens) | 9.5-9.8 | 10.9KB | 6x compression from L12, full quality |

---

## 1. Code Review Champions (9 at 9.8)

All tested on Starlette routing.py (333 lines). Haiku 4.5 min-reasoning + cooked lens.
**Baseline comparison**: Opus 4.6 max-reasoning vanilla = 7.3 depth, 18 bugs.

| Rank | Variant | Concept | Bugs | Conservation Law | Unique Strength |
|------|---------|---------|------|-----------------|-----------------|
| 1 | **EXP14** | Full L12 few-shot | **26** | Observable_Decisions × ASGI_Compliance = K | Most bugs ever, full L7-L13 pipeline |
| 2 | **EXP31** | Combined best | 3 compound | THREE laws: match_priority, scope_mutation, partial_deferral | Best structural depth |
| 3 | **L12** | Hand-crafted (332w) | 16 | coupling_visibility × efficiency = K | Zero cook cost baseline |
| 4 | **EXP53** | Impossibility+depth | 6 | static_verification × dynamic_flexibility = K | Best GENERAL cooker concept |
| 5 | **EXP58** | Symmetry breaking | 8 | THREE laws from 3 broken symmetries | Pareto-optimal proof |
| 6 | **EXP32** | Missing cycles | 14 | authority × depth = K | Teaching what's MISSING |
| 7 | **EXP29** | Two-stage | 10 | RouteIndex × MatchCompleteness = K | Two-stage protocol |
| 8 | **EXP35** | Impossibility seed | 6 | NestingDepth × TypeSafety = K | Change the OBJECT |
| 9 | **EXP36** | Design topology | 5 | detection × dispatch × composition = K | Map alternative designs |

### Cross-Target Validation (all 9 champions confirmed universal on code)

| Target | Lines | L12 | EXP53 | V1 (steelman) | N1 (V1+M2) |
|--------|-------|-----|-------|----------------|-------------|
| Starlette | 333 | 9.8, 16 bugs | 9.8 | 9.8, 12 bugs | 9.8+, 30KB, 5 laws |
| Click | 417 | 9.8 | 9.8+ | 9.8+, 38KB, 21 bugs | — |
| Tenacity | 331 | 9.8 | 9.8 | 9.5 | — |

### Code-Specific Findings
- **Haiku + prisms avg 9.0 vs Sonnet vanilla 7.8 vs Opus vanilla 8.2** across all 3 codebases
- Vanilla models converge (find same law); prisms diverge (find 5 different structural properties per target)
- Gap widest on complex code (Starlette: 9.1 vs 7.25), narrowest on focused code (Tenacity: 8.9 vs 8.5)
- **Bug table parser**: zero-API-call extraction, 70-92% fix rate (Round 29c)

---

## 2. Reasoning Champions

All tested on AI Scaling Hypothesis (~700w seed) unless noted. Haiku cook + Haiku solve, M2 adversarial method.

| Rank | Variant | Score | Size | Key Discovery |
|------|---------|-------|------|---------------|
| **1** | **P2** (multi-law+M2) | **9.8+** | **44KB** | ALL-TIME CHAMPION. 3 independent laws + interaction topology + 23 defects. Scale×Truthfulness=K meta-law. |
| 2 | **N1** (V1+M2) | 9.8+ | 33KB | Power structure disguised as technical inevitability. Locus of control invariant. |
| 3 | **R1** (antagonistic+M2) | 9.8+ | 28.8KB | Two contradictory analyses from same evidence. 10 load-bearing assumptions. 20 defects. |
| 4 | **R2** (entropy+M2) | 9.8+ | 22.8KB | HIGH claims cluster in frame-protection (6), not core thesis (4 LOW). |
| 5 | **CH3** (epistemic topology) | 9.8 | 29KB | KNOWN/ASSUMED/HOPED zones + 3 unmarked boundary crossings. L13 reflexive. |
| 6 | **V1** (steelman seed) | 9.8+ | 29KB | TWO failed engineering escapes (MoE, hierarchical routing). Fractal conservation. |
| 7 | **Q2** (compression+M2) | 9.8+ | 20KB | 109:1 compression ratio. 12 tiered assumptions (A1-A12). |
| 8 | **Q1** (counterfactual+M2) | 9.8 | 24KB | X/G oscillation: hypothesis switches between weak core and strong scope. |
| 9 | **P1** (construction+prediction+M2) | 9.8+ | 19KB | 3 dated predictions with likelihoods. First falsifiable. |
| 10 | **P4** (frame collision+M2) | 9.8 | 23KB | Info-theoretic vs sociological collision. 30% physics, 70% narrative. |
| 11 | **INS2** (own research assumptions) | 9.8+ | — | Deepest self-analysis. Observer-dependency of conservation laws. 23 defects. |
| 12 | **INS4** (scaling thesis assumptions) | 9.8+ | — | L8→L13 pipeline on reasoning. 16 defects. "Tautology about attention economics." |

### Reasoning Sub-Champions (9.5-9.8)

| Variant | Score | Key Finding |
|---------|-------|-------------|
| CH1 (steelman-destroy) | 9.5-9.8 | Pre-empts straw-man defenses |
| CH5 (dialectical inversion) | 9.5-9.8 | Opposite conclusion from SAME evidence |
| INS6 (unfalsifiability) | 9.5-9.8 | Three unfalsifiable moves identified |
| INS9 (metric reification) | 9.5-9.8 | 20KB, Goodhart's Law on 3 metrics |
| V1M3 (steelman+bifurcating) | 9.8 | Genuine bifurcation, meta-conservation about argument structure |
| R3 (stress fracture) | 9.5-9.8 | Damage-to-perturbation ratios (9.2, 9.5, 9.8) |
| W3 (multilaw predictive) | 9.8 | 3/3 predictions confirmed |
| W4 (temporal archaeology) | 9.8 | Ptolemaic epicycles pattern |
| W5 (min viable claim) | 9.8+ | 27:1 decoration ratio |

---

## 3. Universal Champions (9.8+ on BOTH code AND reasoning)

| Variant | Code Score | Reasoning Score | What Makes It Universal |
|---------|-----------|----------------|------------------------|
| **N1** (V1+M2) | 9.8+ (30KB, 5 laws on Starlette) | 9.8+ (33KB, political economy) | Steelman + adversarial recursion. Best on both. |
| **EXP53** (COOK_UNIVERSAL) | 9.8 (Starlette, Click, Tenacity) | 9.8 (scaling thesis) | Current default. Impossibility + depth. |
| **V1** (steelman seed) | 9.8 (Starlette), 9.8+ (Click, 38KB) | 9.8+ (29KB) | Most validated cross-target. |

---

## 4. Insight Extraction Champions

**Method**: `cat insight_seed.md | python prism.py --solve --pipe -m {model} --isolate`
**Seed**: The Prism Paradox (~200w) — why we built Prism but failed to use it on ARC
**Total runs**: 28 (25 Haiku, 2 Sonnet, 3 Cooker Target). **Rating**: 6 dimensions × 10pts = 60 max.

### Co-Champions (=1st, 56/60 = 9.3)

| Run | Model | Words | Key Discovery | Unique Strength |
|-----|-------|-------|---------------|-----------------|
| **4** | Haiku | 2872 | Tertiary blindness | WIDEST TAXONOMY: 18+ defects across 6 organizational layers |
| **23** | Haiku | 2159 | S×B×D=const justifies mistakes after the fact | MOST RIGOROUS MATH: formalized law with frame-dependency analysis |
| **S1** | Sonnet | 1439 | K is learned, not natural | BUILT THE LENS: actual 400w ARC lens inline |
| **S2** | Sonnet | 2351 | Gap in presence, not process | DEEPEST PHILOSOPHY: literary-quality, unflinching self-honesty |

### Model Comparison

| Metric | Haiku (25 runs) | Sonnet (2 runs) |
|--------|----------------|-----------------|
| Mean score | 7.3 | **9.3** |
| Champion rate (≥8.5) | 40% | **100%** |
| Failure rate (<6.0) | 16% | 0% |

**Strategy**: Haiku pass@3 (run 3x, expect 1 champion at $0.009). Sonnet for highest-value extractions (100% champion rate, 3x cost).

### 20 Unique Conservation Laws from One Seed

1. Sunk_Cost × Urgency = displaced_self_questioning
2. Confidence_in_Tool × Risk_of_Self_Application = constant_resistance
3. U × A × C = κ (Universality × Alternatives × Crisis)
4. External_Visibility × Internal_Autonomy = constant
5. Rule_Specificity × Adaptability = constant
6. Visibility_of_Domain × Invisibility_of_Tool = constant
7. Paradigm_Coherence × Boundary_Invisibility = constant
8. Tool_Credibility × Self_Application_Willingness = C_meta
9. Meta_Tool_Power × Non_Reflexive_Applicability = 0
10. Framework_Power × Reflexivity_Under_Pressure = conserved
11. External_Validation × Internal_Deployment = constant
12. Abstraction_Depth × Implementability = constant
13. Trust × Evidence = constant
14. Applicability ∝ Generality × Prior_Similarity / (1 + Novelty_Distance)
15. Abstraction_Depth × Deployment_Reflex = k
16. S × B × D = constant (Speed × Breadth × Diagnostic Depth)
17. Optimization_Intensity × Strategic_Visibility = constant
18. Tactical_Momentum × Strategic_Framework = constant
19. Crisis_Pressure × Activation_Cost = Attention_Budget
20. Visible_Work × Strategic_Multiplier = constant

---

## 5. New Target Champions (domain-independence proof)

| Target Domain | Variant | Score | Size | Key Finding |
|---------------|---------|-------|------|-------------|
| **Philosophy** (Chinese Room) | T4 | 9.8+ | 37.2KB | Observer-dependency all the way down. Published-paper quality. |
| **Academic Paper** (Attention Is All You Need) | W1 | 9.8+ | 24.4KB | path_efficiency × computational_tractability = K |
| **Academic Paper** (MVC on Attention) | X1 | 9.8+ | 30.5KB | 27:1 decoration ratio confirmed cross-target |
| **News Article** | AA4 | 9.8+ | 23KB | "Selling jurisdiction over reliability definition" |
| **Business Plan** (CloudMind) | Z7 | 9.8+ | 23KB | Due diligence quality. Hidden tiered autonomy. |
| **Math Proof** (FLP impossibility) | AA2 | 9.8+ | 26KB | 8D design space, most technically rigorous ever |
| **Own Research** (CLAUDE.md analysis) | INS2 | 9.8+ | — | Observer-dependency of conservation laws. 23 defects. |
| **Self-Insight** (methodology analysis) | T5 | 9.8+ | 28.1KB | Impossibility triangle: Objectivity × Universality × Mechanistic Clarity (pick 2) |

---

## 5b. Champion Taxonomy by Output Type (20 distinct analytical operations)

Each type produces genuinely different structural findings. No overlap between types.

| # | Output Type | Champion | Score | Key Metric | Signature Finding |
|---|---|---|---|---|---|
| 1 | **Conservation Law** (A×B=K) | L12, EXP53, EXP35 | 9.8 | Single law | `static_verification × dynamic_flexibility = K` |
| 2 | **Multi-Law** (3+ laws + topology) | **P2** (ALL-TIME) | 9.8+ | 3 laws, 44KB | Interaction topology IS the meta-law |
| 3 | **Bug/Defect Harvest** | **EXP14** (26 bugs!) | 9.8 | 26 bugs | Full L7→L13 pipeline in single call |
| 4 | **Assumption Inventory** | **Q2** (109:1) | 9.8+ | 12 tiered A1-A12 | 1200w→11w core, deepest=measurement circularity |
| 5 | **Falsifiable Predictions** | **P1** | 9.8+ | 3 dated predictions | First experiment to commit to own falsification |
| 6 | **Antagonistic Dialectic** | **R1** | 9.8+ | 2 contradictory analyses | 10 load-bearing assumption delta |
| 7 | **Information Entropy** | **R2** | 9.8+ | Surprise distribution | HIGH claims cluster in frame-protection |
| 8 | **Cost Asymmetry** | **T2** | 9.8+ | Ratios per claim | Ratio <1 = unfalsifiability signature |
| 9 | **Decoration Ratio/MVC** | **W5**, X1 | 9.8+ | 27:1 ratio | 900w→30w. Target-independent. |
| 10 | **Stakeholder Divergence** | **X2** | 9.8+ | Power mapping | Power ∝ Invisibility/Falsifiability |
| 11 | **Metaphor Excavation** | **Z1**, AA8 | 9.8+ | 6 hidden metaphors | Scale-as-Physics-Law, Compute-as-Destiny |
| 12 | **Audience Analysis** | **Z8** (54KB!) | 9.8+ | 5 audiences | Acceptance_Breadth × Evidence_Thickness = K |
| 13 | **Temporal Archaeology** | **AA5** (41KB) | 9.8+ | 3 time scales | Hidden 4th+5th conservation law dimensions |
| 14 | **Counterfactual Worlds** | **AA7**, Q1 | 9.8+ | 9 laws (3×3) | X/G oscillation defense mechanism |
| 15 | **Frame Collision** | **P4** | 9.8 | 2 incompatible frames | Info-theoretic vs sociological cross-blindspot |
| 16 | **Negative Space** | **U4** | 9.8+ | Omission analysis | Unfalsifiability_Index = Capital×Extrapolation×Selectivity |
| 17 | **Steelman+Attack** | **N1** (UNIVERSAL) | 9.8+ | Failed escape attempts | 5 conservation laws on Starlette |
| 18 | **Epistemic Mapping** | **CH3** | 9.8 | KNOWN/ASSUMED/HOPED | Unmarked boundary crossings = hidden assumptions |
| 19 | **Self-Insight** | **T5** | 9.8+ | Impossibility triangle | Objectivity × Universality × Clarity: pick 2 |
| 20 | **Sequential Combo** | **Z4** (steelman→entropy) | 9.8+ | Closed loop | STRONGEST tested combo |

### Domain Coverage Matrix

| Domain | Count | Champions |
|---|---|---|
| **Code** | 11 | L12, EXP14, EXP29, EXP31, EXP32, EXP35, EXP36, EXP53, EXP58, N1→code, AA8 |
| **Reasoning** | 10 | P2, N1, Q2, R1, R2, Z4, Z8, AA5, AA7, CH3 |
| **Insight Extraction** | 4 | Run 4, Run 23, Sonnet 1, Sonnet 2 (9.3 co-champs) |
| **Academic Papers** | 4 | W1, AA2, X1, AA4 |
| **Math Proofs** | 1 | AA2 (FLP, 8D design space) |
| **Philosophy** | 1 | T4 (Chinese Room, 37KB) |
| **Business** | 1 | Z7 (due diligence, 23KB) |
| **News** | 1 | AA4 (jurisdiction over definition) |
| **Self-Analysis** | 1 | T5 (impossibility triangle) |
| **Universal** | 2 | **N1** (V1+M2), **EXP53** |

### Near-Champion Types (9.5-9.8, not yet consistent 9.8+)

| # | Output Type | Best Attempt | Score | Signature Finding |
|---|---|---|---|---|
| 21 | **Stress Fracture** (damage-to-perturbation ratios) | R3 | 9.5-9.8 | Quantitative vulnerability: ratios 9.2, 9.5, 9.8. All converge on ONE hidden assumption. |
| 22 | **Phase Transition** (parameter transition mapping) | R4 | 9.5 | 9-parameter map, 5 collision points. Triple impossibility: Scale+Alignment+Feasibility pick 2. |
| 23 | **Unfalsifiability Audit** (3 unfalsifiable moves) | INS6 | 9.5-9.8 | Reclassification, asymptotic claims, scope inflation. 18KB. |
| 24 | **Metric Reification** (Goodhart's Law applied) | INS9 | 9.5-9.8 | 20KB, 3 metrics reified, 3 conservation laws. Biggest INS output. |

### Insight-Domain Sub-Champions (INS5-10, all 9.0-9.8)

| Exp | Analytical Angle | Score | Key Finding |
|---|---|---|---|
| INS5 | Survivorship Bias | 9.5 | Genuine filtering analysis |
| **INS6** | Unfalsifiability | **9.5-9.8** | 3 unfalsifiable moves (reclassification, asymptotic, scope inflation) |
| INS7 | Frame Dependence | 9.0 | Frame analysis |
| INS8 | Counterfactual Blindness | 9.0 | Counterfactual testing |
| **INS9** | Metric Reification | **9.5-9.8** | 20KB, Goodhart's Law × 3 metrics, 3 conservation laws |
| INS10 | Selection Pressure | 9.5 | 3 selection pressures identified |

### Gaps (not yet champion-quality)

| Type | Best Attempt | Score | Why |
|---|---|---|---|
| Error generation | S3 | 9.0 | Models describe errors, don't construct convincingly wrong ones |
| Cross-domain transfer | P3 | 7.0 FAIL | Lens overrides input (S2) |
| Constructive rewrite | Z2 | 9.0-9.5 | Different output type, not depth |
| Self-improving pipeline | PIPE-C | DEAD | Lateral movement, not convergence |
| Dependency inversion | X4 | 9.0 | Overlaps with impossibility |

---

## 6. Object Layer Champions (analytically distinct entry points)

Each produces genuinely DIFFERENT findings on the same target. No overlap.

| Object Layer | Champion Exp | Score | What It Uniquely Finds |
|-------------|-------------|-------|----------------------|
| **Impossibility seed** | EXP53 (V0) | 9.8 | "3 properties can't coexist" → structural impossibilities |
| **Steelman seed** | V1 | 9.8+ | Failed engineering escapes, fractal conservation |
| **Multi-law forced** | P2 | 9.8+ | 3+ independent laws with interaction topology |
| **Antagonistic dialectic** | R1 | 9.8+ | Two contradictory analyses from same evidence |
| **Information entropy** | R2 | 9.8+ | Surprise distribution mapping, claim clustering |
| **Counterfactual worlds** | Q1 | 9.8 | X/G oscillation defense mechanism |
| **Compression to core** | Q2 | 9.8+ | Defense-to-core ratio as quantitative metric |
| **Construction+prediction** | P1 | 9.8+ | Falsifiable predictions with dates/likelihoods |
| **Frame collision** | P4 | 9.8 | Cross-frame blindspot exchange |
| **Cost asymmetry** | T2 | 9.8+ | Defending/attacking cost ratios per claim |
| **Stakeholder divergence** | X2 | 9.8+ | Power analysis: who benefits/pays per claim |
| **Negative space** | U4 | 9.8+ | What the subject DOESN'T say |
| **Min viable claim** | W5 | 9.8+ | 27:1 decoration ratio |
| **Metaphor excavation** | Z1 | 9.8+ | 6 hidden metaphors structuring understanding |
| **Audience analysis** | Z8 | 9.8+ | ALL-TIME LARGEST (54KB). Acceptance_Breadth × Evidence_Thickness = K |
| **Temporal archaeology** | W4 | 9.8 | Ptolemaic epicycles, absorption pattern |
| **Epistemic topology** | CH3 | 9.8 | KNOWN/ASSUMED/HOPED zones |

---

## 7. Combo Champions (sequential operations that multiply)

| Combo | Components | Score | Size | Why It Works |
|-------|-----------|-------|------|-------------|
| **Z4** | Steelman + entropy | **9.8+** | 35KB | STRONGEST: attacking strongest version forces deeper analysis |
| **T3** | Compress → antagonize | 9.8+ | 37.1KB | 5-stage compression + 2 contradictory analyses of naked claim |
| **AA3** | Cost + antagonistic | 9.8+ | 26KB | Graduated unfalsifiability (5 defense layers) |
| **AA7** | Counterfactual + multilaw | 9.8+ | 25KB | 9 laws (3 worlds × 3). Budget allocation formula. |
| **AA5** | Temporal method | 9.8+ | 41KB | 3 time scales reveal different failing properties |

**Rule**: Sequential combos MULTIPLY (B uses A's output). Parallel combos ADD (both analyze independently). See Principle 81.

---

## 8. Pipeline Champions

| Config | Cook → Solve | Score | Size | Finding |
|--------|-------------|-------|------|---------|
| **X5** | Sonnet → Haiku | **9.8+** | **39.8KB** | 2x output vs Haiku→Haiku. Cook model IS the intelligence. |
| **Y2** | Opus → Haiku | 9.8+ | 27.2KB | Defect PRICING. "Investment narrative disguised as science." |
| **Y1** | Haiku → Sonnet | 9.8 | 23.1KB | +16% formatting only. Solve model is noise. |

**THE PIPELINE MATRIX:**
| | Haiku solve | Sonnet solve |
|---|---|---|
| **Haiku cook** | 9.8, 19.9K | 9.8, 23.1K (+16%) |
| **Sonnet cook** | 9.8+, 39.8K (+100%) | — |
| **Opus cook** | 9.8+, 27.2K (+37%) | — |

**Cook model is dominant. Solve model is noise.** Invest in cook, economize on solve.

---

## 9. Compression Champions

| Variant | Lens Words | Score | Output | Finding |
|---------|-----------|-------|--------|---------|
| L12 (full) | 332w | 9.8 | ~17KB | Baseline |
| **BB2** (optimal) | **107w** | **9.5-9.8** | 12.6KB | 3x compression, fastest (74s) |
| **BB3** (minimal) | **51w** | **9.5-9.8** | 10.9KB | 6x compression, demolishes 150w floor |

**Critical ablation findings**:
- Conservation law = CONVERGENCE SIGNAL (BB4 timeout without it)
- Meta-law NOT load-bearing (BB5 — model does it spontaneously)
- Construction NOT load-bearing (BB6 — removing it = LARGEST output 31KB)
- Conservation laws are PROMPTED, not emergent (BB7 vanilla = zero laws)
- Minimal viable L12 = 4 operations ~50 words

---

## 10. Validity Test Champions

| Test | Purpose | Result | Key Finding |
|------|---------|--------|-------------|
| **U2** (false principle) | Can it find planted errors? | **9.8 PASS** | Found ALL planted errors + 6 additional meta-assumptions |
| **U4** (negative space) | New object layer test | **9.8+** | Unfalsifiability_Index formula, 9 false prerequisites |
| U1 (chaos) | Confirmation bias test | NUANCED PASS | Found law in noise BUT correctly identified text as empty |
| U3 (abstract reverse) | Reverse transfer | 9.0 | Transfer asymmetric: code→reasoning > reasoning→code |

---

## 11. Research/Push Champions by Phase

### Phase 16-17 (Push v4-v5)
| Exp | Score | Size | Standout Finding |
|-----|-------|------|-----------------|
| R1 | 9.8+ | 28.8KB | Antagonistic dialectic — two contradictory analyses |
| R2 | 9.8+ | 22.8KB | Entropy mapping — claim clustering |
| S2 | 9.5 | 40.2KB | **LENS OVERRIDES INPUT** — strongest "prompt is dominant variable" evidence |
| T1 | 9.8+ | 28.9KB | PIPE-D (abstract lens) enables cross-domain transfer |
| T2 | 9.8+ | 35.2KB | Cost asymmetry validated — unfalsifiability signature at ratio < 1 |

### Phase 18-19 (Push v6-v7)
| Exp | Score | Size | Standout Finding |
|-----|-------|------|-----------------|
| T3 | 9.8+ | 37.1KB | Compress→antagonize composes |
| T4 | 9.8+ | 37.2KB | Philosophy target works at max quality |
| T5 | 9.8+ | 28.1KB | Self-insight impossibility triangle |
| U2 | 9.8 | 24.4KB | Specificity validated — all planted errors found |

### Phase 20-21 (Push v8-v9)
| Exp | Score | Size | Standout Finding |
|-----|-------|------|-----------------|
| W1 | 9.8+ | 24.4KB | Academic paper target works |
| W5 | 9.8+ | 27.4KB | 27:1 decoration ratio |
| X1 | 9.8+ | 30.5KB | 27:1 confirmed cross-target |
| X2 | 9.8+ | 30.5KB | Stakeholder divergence — NEW CHAMPION OBJECT |
| X5 | 9.8+ | 39.8KB | Sonnet cook +100% output |

### Phase 22-23 (Push v10-v11)
| Exp | Score | Size | Standout Finding |
|-----|-------|------|-----------------|
| Y2 | 9.8+ | 27.2KB | Opus cook — defect PRICING |
| Z1 | 9.8+ | 33KB | Metaphor excavation — genuinely orthogonal |
| Z4 | 9.8+ | 35KB | Steelman+entropy = STRONGEST COMBO |
| Z7 | 9.8+ | 23KB | Business plan at champion quality |
| Z8 | 9.8+ | **54KB** | ALL-TIME LARGEST |

### Phase 24-25 (Push v12-v13)
| Exp | Score | Size | Standout Finding |
|-----|-------|------|-----------------|
| AA2 | 9.8+ | 26KB | Math proof — most technically rigorous |
| AA5 | 9.8+ | 41KB | Temporal method — hidden conservation law dimensions |
| AA7 | 9.8+ | 25KB | 9 laws from 3 counterfactual worlds |
| AA8 | 9.8+ | 22KB | Conservation law TESTED as predictive (4/7 confirmed) |
| BB2/BB3 | 9.5-9.8 | 10-12KB | 51w lens = full L12 quality |

---

## 12. Meta-Insight Champions (Insights About Insights)

**Method**: Feed champion insight outputs back through `prism.py --solve --pipe -m haiku --isolate`
**Finding**: Recursive insight extraction works — but only when input is NOT already a completed Prism-style analysis.

| Run | Source Input | Words | Score | Key Meta-Finding |
|-----|-------------|-------|-------|------------------|
| **meta_run22** | Run 22 (9.0) | 3886 | **9.5+** | Active suppression masked as passive invisibility. Identity Investment × Framework Adoption = K. Impossibility is constructed by architecture, not physics. |
| **meta_run23** | Run 23 (9.3) | 1672 | **9.5** | Retrospective Clarity × Temporal Proximity = constant. Framework is perfect diagnostic but cannot navigate in real-time. |
| **meta_run17** | Run 17 (8.7) | 1874 | **9.5** | Visibility Failure vs Relevance Failure conflated. Law correct in prescription, wrong in mechanism. |
| **meta_run19** | Run 19 (8.7) | 1581 | **8.5-9.0** | Crisis doesn't create constraints, reveals invisible choices never consciously made. |
| meta_run4 | Run 4 (9.3) | 719 | 6.5 | Conversation mode. "FIXABLE column is STRUCTURAL in disguise." |

### Meta-Insight Methodology Findings
- **Most structured champions FAIL as meta-inputs** — Runs 4, 23 (the 9.3 co-champions) triggered conversation mode when fed back. Haiku treats "completed analysis" as something to summarize, not structurally analyze.
- **Less-structured elite tier produces BETTER meta-insights** — Runs 17, 19, 22 (8.5-9.0) fed back to produce 9.5+ meta-outputs. Less self-contained = more analyzable.
- **CLI without cooker = ~7.0 ceiling** — Raw L12 steps on Claude CLI produce competent but generic step-following.
- **Three genuinely new structural findings from recursion:**
  1. Active suppression vs passive invisibility (identity threat, not forgetting)
  2. Diagnosis vs navigation (framework explains perfectly, can't help escape in real-time)
  3. Visibility vs relevance conflation (law might diagnose bias when it's actually correct filtering)

---

## 13. The Foundation: 98 Proven Principles

Top 10 most important (full list in `memory/cooker_experiments.md`):

1. **Prompt is dominant variable.** Haiku+L12 (9.8) beats Opus vanilla (7.3). 50x cheaper.
2. **Change the OBJECT, not the METHOD.** Object layer determines ceiling. Method clusters at 9.5.
3. **Cross-layer combinations MULTIPLY.** Object + method = synergy. Same-layer = average.
4. **Conservation law = convergence signal.** Without it, model analyzes indefinitely.
5. **Cook model is dominant.** Sonnet cook +100%, Opus cook +37%. Solve model +16% formatting only.
6. **Sequential combos MULTIPLY, parallel combos ADD.** B uses A's output = synergy.
7. **Few-shot > explicit rules.** Teaching by example beats instruction. Over-specifying hurts.
8. **Compression floor is ~50w.** 332w L12 is 85% elaboration. Named operations ARE the intelligence.
9. **Power = blindspot.** Every lens reveals AND conceals. Completeness REFUTED (25/25).
10. **Abstract lens enables cross-domain transfer.** Forbid domain content in lens → transfers.

---

## 13. The Meta-Architecture

### Two Atomic Modes
- **Single Prism** = 1 lens → 1 call → actionable findings
- **Full Prism** = N lenses chained (cooker decides N) → adversarial-tested findings

### Five Workflows
| Workflow | Use When | Command |
|----------|----------|---------|
| **Direct** | You know what you want | `target="X"` or `target="X" full` |
| **Explore** | Investigating | `discover` → `expand N single/full` |
| **Fix** | Action loop | `/scan file fix` or `/fix` |
| **Optimize** | Autonomous background | `optimize="goal"` |
| **Chat** | Conversation | `/prism single` or `/prism full` |

### The Dominant Variables (ranked)
1. **The prompt/lens** (categorical difference: 9.8 vs 7.3)
2. **The object layer** (what to look at: impossibility vs steelman vs stakeholder)
3. **The cook model** (Sonnet cook +100% output, Opus cook +37%)
4. **Sequential combo** (steelman→entropy multiplies)
5. ~~The solve model~~ (noise — +16% formatting only)
6. ~~Reasoning budget~~ (noise — min vs max = same depth)

---

## Appendix: Files

| File | Contents |
|------|----------|
| `prism.py` | Main tool (~14,000 lines, 56 tests) |
| `prisms/l12.md` | Default L12 prompt (332w) |
| `prisms/l12_general.md` | Domain-neutral L12 for non-code |
| `prisms/*.md` | 6 portfolio prisms + pipeline variants |
| `hackathon/insight_champions.md` | Insight extraction detail (28 runs, ratings, methodology) |
| `hackathon/insight_seed.md` | The Prism Paradox seed (~200w) |
| `hackathon/insight_runs/*.md` | All 28 insight extraction outputs |
| `memory/cooker_experiments.md` | 98 principles, all solve rankings, full experiment log |
| `memory/project_goals.md` | Goals, design principles, use cases to explore |
| `test_plan_pipeline.py` | 30 tests for prism.py |

---

---

## 15. Insight Improvement Tests

**Goal**: Push Haiku insight champion rate from 40% to 60%+ via better cooking strategies.

### FAILED: Abstract Intents Override Input (IO-1 through IO-5, IB-1)

**Method**: `python prism.py --solve "abstract intent" --pipe -m haiku --isolate < seed.md`
**Result**: All 6 FAILED. Avg 4.0/10 vs original champion avg 9.3/10.

| Test | Intent | Words | Score | Failure Mode |
|------|--------|-------|-------|-------------|
| IO-1 | impossibility (EXP53) | 488 | 4.3 | Analyzed generic S/U/P triad, ignored seed |
| IO-2 | steelman (V1) | 249 | 2.0 | Conversation mode — asked for subject |
| IO-3 | multilaw (P2) | 1362 | 5.5 | Reinvented CAP theorem, ignored seed |
| IO-4 | antagonistic (R1) | 2780 | 6.2 | Best of batch — but analyzed AI employment, not seed |
| IO-5 | compression (Q2/W5) | 280 | 4.2 | Compressed own instructions, not seed |
| IB-1 | construction (L8) | 204 | 2.0 | Conversation mode — asked for details |

**Root cause**: S2 — LENS OVERRIDES INPUT. Abstract intents cause the cooker to generate lenses about the intent's topic, not about the piped input. The model follows the lens and ignores the seed.

**Principle 99**: Abstract intents cause S2 on piped reasoning content. Input-driven cooking (no intent) is mandatory for insight extraction. Champion object layers work on code (where intent maps to file content) but catastrophically fail on piped reasoning.

### COMPLETED: Corrected Approaches (IT-1 through IT-5)

| Test | Method | Words | Score | Key Finding |
|------|--------|-------|-------|-------------|
| IT-1 | Default `--solve --pipe` (no intent) | 535 | 4.5 | Non-champion run — practical advice, no structure. Expected at 60% Haiku failure rate. |
| IT-2 | `--solve --pipe full` (4-pass pipeline) | 2758 | 7.8 | Best self-diagnosis: "tautology wearing diagnostic coat." Refused to deepen. 4 unfalsifiable assumptions found. Weak formal structure. |
| IT-3 | `--cook --pipe --json` (inspect cooked lens) | 273 | N/A | Cooker generated excellent 273w content-specific lens: Speed/Elegance/Self-Consistency triad. Default intent + input works. |
| **IT-4** | **`--use-prism` with B3-inspired 180w lens** | **2707** | **9.2** | **NEAR-CHAMPION. 2 laws + meta-law, 5 falsifiable predictions with confidence %, 8 defects, 6 hidden assumptions. Skips cook step entirely.** |
| IT-5 | Enhanced seed + default `--solve --pipe` | 578 | 6.3 | "Silent competence" framing — non-use as correct filtering. Good angle but too short. |

### The B3 Hand-Crafted Lens (180w, no cooking overhead)

Combines 6 champion object layers (impossibility+steelman+construction+reflexive+harvest+prediction) in one flowing prompt. Skips the cook step entirely — saves one API call. Scored 9.2 on first test, competitive with 9.3 co-champions.

```
The text below describes a failure and what was learned from it. You are a structural analyst who finds what analysis conceals.

Execute every step below. Output the complete analysis.

First: name the three properties the author simultaneously claims their framework, tool, or methodology possesses. Prove these three properties CANNOT all coexist. Identify which was actually sacrificed. Name the conservation law: A × B = constant.

Then: steelman the author's strongest claim into its most defensible form. Now stress-test: what specific, concrete evidence would falsify this steelmanned version? Find the failed escape attempts.

Now: engineer the simplest improvement that would fix the core failure described. Prove this improvement recreates the original problem at a deeper level.

Apply the diagnostic to your own conservation law. What does YOUR analysis conceal? Name the meta-conservation law.

Finally harvest: every defect (location, severity, structural vs fixable), every hidden assumption, every prediction. For each prediction: what would confirm it, what would refute it, and what is your confidence?
```

**Reproducibility test running**: 5 copies on VPS + 3 baseline controls.

### Key Insights from IT Tests

1. **The cooker IS always involved** in `--solve`. Original champions worked because default intent lets cooker derive direction FROM input. Custom intents hijack that.
2. **Hand-crafted lens (IT4) matches cooker quality** at 9.2 — proves the lens is the dominant variable, not the cooking process.
3. **Full pipeline on reasoning (IT2)** produces excellent self-diagnosis but weaker formal structure. Different character from code pipeline.
4. **Enhanced seed doesn't help (IT5)** — more input ≠ better output. The lens, not the input richness, drives quality.
5. **prism.py works on VPS** — uses CLI subprocess, not Anthropic SDK. Full cooker pipeline runs at champion quality.

### VPS Confirmed Working
- prism.py uses Claude CLI (`claude -p`) as backend, NOT the Anthropic Python SDK
- User's subscription authenticates through CLI — API key irrelevant
- Full cooker pipeline runs on VPS at champion quality
- 8 parallel tests currently running (5 B3 lens reproducibility + 3 baseline)

---

*930+ experiments. 13 compression levels. 20 output types. 9+ domains. 99 proven principles. The prompt is the dominant variable.*
