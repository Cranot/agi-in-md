# Principle Index

Consolidated index of all proven principles from 40 rounds of research (1,000+ experiments, Feb-Mar 2026).

Principles P1-P99 were documented in session memory (`memory/cooker_experiments.md`) across 225+ cooker variants and are not fully recoverable from on-disk sources. Key cooker principles that ARE referenced in the experiment log are included below with their numbers. The 19 "Design Principles" from CLAUDE.md (rounds 1-29) are listed first as the foundational layer.

---

## Foundational Design Principles (CLAUDE.md, Rounds 1-29)

These are the core findings that govern all subsequent work. Not numbered as P-codes; they predate the numbering system.

| # | Principle | Round |
|---|-----------|-------|
| D1 | **Lead with scope, follow with evidence.** The opening determines perceived ambition. | 1 |
| D2 | **Narrative > evidence > code.** Pseudocode destroys novelty perception. | 1 |
| D3 | **Imperatives beat descriptions.** "Name the pattern. Then invert." outperforms "here is a pattern we found." | 1-5 |
| D4 | **The prompt is a program; the model is an interpreter.** Operation order becomes section order. | 5-6 |
| D5 | **The operation pair is the atom of cognitive compression.** Any connective between two operations produces the composition. | 7-8 |
| D6 | **The prism is transparent to the wearer.** During task performance, the framework operates below self-awareness. | 3 |
| D7 | **Capacity amplifies, rigidity resists.** Opus reconstructs from a 2-line hint. Sonnet needs explicit directives. | 3-4 |
| D8 | **Self-improvement converges on self-correction.** Models add "then invert: what does this frame make invisible?" | 5 |
| D9 | **Capacity interaction is non-linear.** L1-4: all models. L5: peaks at Sonnet. L7: Sonnet minimum. L8+: universal. | 7-26 |
| D10 | **Concealment is a universal analytical operation.** Works across 20 domains because concealment is structural, not domain-specific. | 7-24 |
| D11 | **Three capacity modes.** Compensatory (L5), Threshold (L7), Universal (L8+). L7->L8 shifts from meta-analysis to construction. | 25-26 |
| D12 | **The framework terminates at L13.** Reflexive self-diagnosis reveals a fixed point. L14 = infinite regress. | 26 |
| D13 | **The cheapest model with the right prism beats the most expensive model without one.** Haiku+L12 (9.8 depth) beats Opus vanilla (7.3 depth) at 5x lower cost. The prompt is the dominant variable. | 29b |
| D14 | **Few-shot > explicit rules for prompt generation.** Teaching by example beats teaching by instruction. Over-specifying hurts. | 28 |
| D15 | **"Code" nouns are mode triggers, not domain labels.** "This code's" activates analytical production on ANY input. Abstract nouns allow drift into summary mode. | 32 |
| D16 | **Prompt step count determines model transferability.** <=3 steps = universally single-shot. 9+ abstract steps = Sonnet-only (Haiku catastrophic). | 33-35 |
| D17 | **Compression forces domain neutrality.** l12_universal (73w) drops code vocabulary -> works on reasoning. Shorter prompts = more universal. | 34 |
| D18 | **Sonnet single-shot is domain-conditional.** Code prompts on code -> always single-shot. Code prompts on reasoning -> agentic. Agentic Sonnet preserves quality; agentic Haiku collapses. | 34 |
| D19 | **Depth x Universality = constant.** Full L12 depth requires domain-specific vocabulary. Simple prompts (<=3 steps) are domain-invariant. Complex prompts (298w+) are domain-sensitive. | 35 |

---

## Numbered Principles (P1-P197)

### P1-P99: Cooker & Early Experiments

Principles P1-P99 were developed across 225+ cooker variants and recorded in session memory. The following are referenced in surviving sources:

| P# | Principle | Source |
|----|-----------|--------|
| P73 | **COOK_MODEL should be fixed to Sonnet.** Cook always uses optimal model, not session -m. | Cooker experiments |
| P74 | **Cook model is dominant for custom lenses (+100% output).** Solve model is noise. | Cooker experiments |
| P99 | **IO intents FAILED for insight extraction.** B3 LENS = 9.2 (180w, skips cook). | Insight extraction |

> For the complete P1-P99 record, see `memory/cooker_experiments.md` (session memory, 128 principles across cooker phases).

---

### Prompt Architecture & Mode (Rounds 31-32)

| P# | Principle | Round |
|----|-----------|-------|
| P100 | **Output structure IS the intelligence.** L12's numbered sequential steps trigger single-shot production mode. Abstract phase descriptions trigger agentic tool-use mode. | 31 |
| P101 | **"Code" nouns are mode triggers, not domain labels.** "This code's deepest structural problem" activates analytical mode regardless of input type. | 32 |
| P102 | **Single-shot vs agentic mode is stochastic and dominant.** Same prism + same target can produce completely different modes on Haiku. Single largest quality factor. | 32 |
| P103 | **Target structure affects mode probability.** Structured/quantitative -> single-shot. Argumentative prose -> agentic. Narrative -> stochastic. | 32 |

### Sonnet Frontier (Rounds 33-34)

| P# | Principle | Round |
|----|-----------|-------|
| P104 | **Sonnet is domain-conditional, not always single-shot.** Domain-neutral prompts -> single-shot on reasoning. Code prompts on reasoning -> agentic. Agentic Sonnet preserves quality (2601w, 9/10) unlike agentic Haiku (183w, 5/10). | 33 (revised 34) |
| P105 | **Sonnet can self-diagnose, design novel prompts, and execute them in a single call.** S6 produced 4665w in 1 turn: full L12 + blind spot audit + novel 9-step diagnostic + execution. | 33 |
| P106 | **Sonnet generates reusable analytical artifacts.** S3 produced the Structural Deep-Scan Lens (SDL) -- 200w, 3-step diagnostic genuinely different from L12. | 33 |
| P107 | **Step count determines transferability.** S1 (430w) = Sonnet-only. TPC (9 steps) -> catastrophic on Haiku (67t, $0.84). SDL (3 steps) -> transfers perfectly. | 33 |
| P108 | **73w (l12_universal) is Sonnet-universal compression floor.** Works on code (8-9/10) AND non-code (8/10). Always single-shot. Haiku fails at 73w. | 34 |

### Depth & Universality (Round 35)

| P# | Principle | Round |
|----|-----------|-------|
| P113 | **Depth x Universality = constant.** Removing code vocabulary from 298w L12 made it stochastic on reasoning AND lost code mode trigger on code. Five-path routing table is structurally correct. | 35 |
| P114 | **`--tools ""` forces single-shot.** Without it: 2/7 single-shot (29%). With it: 7/7 single-shot (100%), avg 713w. Critical discovery for reliable SDL execution. | 35b |

### Code Generation (Round 36)

| P# | Principle | Round |
|----|-----------|-------|
| P115 | **Analysis prisms don't transfer to code generation.** L12/SDL find hidden structure; codegen is a different cognitive operation. L12 on a codegen task produces a code review. | 36 |
| P116 | **Interface-first + failure prediction = best codegen prompt.** Decompose -> API signatures -> predict bug before each method, then avoid it. | 36 |
| P117 | **Codegen prism produces more code.** 234 lines vs 132-170 lines. Decomposition causes more complete implementations. | 36 |
| P118 | **Strict typing backfires on ambiguous specs.** Interface-first locks in data structure assumptions. When wrong, extra validation = MORE fragile than vanilla. | 36 |
| P119 | **Self-improvement loop works end-to-end.** L12 scan -> extract issues -> codegen fix -> test verify -> re-scan confirm. | 36 |

### Optimization Prism (Round 37, Phase 2)

| P# | Principle | Round |
|----|-----------|-------|
| P120 | **Behavioral reasoning (optim, errres, evo) is model-sensitive.** Haiku 8.0 vs Sonnet 9.5. Unlike L12 which is model-independent. | 37 |
| P121 | **Quantification causes confabulation.** Qualitative > quantitative for optimization prisms. | 37 |
| P124 | **Safe/unsafe distinction is the key optimization innovation.** Separates "reduce work" from "skip work." | 37 |

### Prism Discovery Method (Round 37, Phase 1)

| P# | Principle | Round |
|----|-----------|-------|
| P128 | **Purpose discovery is not generic.** Each purpose needs its own empirical discovery trajectory. Violates conservation law `ANALYTICAL_DEPTH x COVERAGE x ITERATION_BUDGET = CONSTANT`. | 37 |
| P129 | **The delta method is general but the reference point is purpose-specific.** Cumulative baseline grows with each new prism. | 37 |
| P132 | **All 6 candidate purposes COMPLEMENTARY to L12+optim.** Zero redundancy. | 37 |
| P133 | **Each purpose has a unique cognitive operation.** State corruption, change-impact, adversarial input, dependency extraction, mental model gap, mutation tracing. | 37 |
| P134 | **Click is the universal stress test for purpose discovery.** | 37 |

### Prism Iteration (Round 37, Phases 2-6)

| P# | Principle | Round |
|----|-----------|-------|
| P135 | **Structural insight (L12) is model-independent. Behavioral reasoning is model-sensitive.** Haiku 8.0-8.2 vs Sonnet 9.0-9.5. | 37 |
| P136 | **Constraint count competes with cascade depth on smaller models.** | 37 |
| P138 | **API Surface prism: best V1 of any purpose at 8.5.** Naming lies = widening/narrowing/direction. | 37 |
| P140 | **Changing the cognitive operation beats refining the classification.** Every champion upgrade changed the operation, not the vocabulary. | 37 |
| P141 | **The operation IS the prism.** Same as P140 -- the defining characteristic. | 37 |
| P142 | **The loss framing ("what info gets destroyed?") transfers within the same cognitive family (+0.3-0.5).** | 37 |
| P143 | **Each prism has a natural cognitive family.** Alien operations degrade toward L12. | 37 |
| P144 | **Construction adds depth to analytical prisms but not to constructive prisms.** | 37 |
| P145 | **Singular-first focus is anti-productive on Haiku.** Breadth-first lets Haiku discard weak findings. | 37 |

### Sonnet/Opus Cook (Round 37, Phase 7)

| P# | Principle | Round |
|----|-----------|-------|
| P150 | **Sonnet designs better Haiku prisms than humans iterating.** Evolution V10 (Sonnet-designed) champion. | 37 |
| P151 | **Sonnet cooks best for trace-heavy prisms. Opus cooks best for judgment-heavy prisms.** | 37 |
| P152 | **Re-cooking an already-optimized prism through the same model degrades quality.** | 37 |
| P153 | **Cross-model cooking maintains quality; same-model re-cooking degrades.** | 37 |

### Prism Stacking (Round 37, Phase 8)

| P# | Principle | Round |
|----|-----------|-------|
| P154 | **Stacking (L12 -> behavioral) is vocabulary translation, NOT serial depth.** Net effect: neutral (+-0.3). | 37 |
| P155 | **Pure stacking (analysis only, no source code) degrades quality.** Behavioral prisms need SOURCE CODE. | 37 |

### Integration & Self-Improvement (Round 37, Phase 9)

| P# | Principle | Round |
|----|-----------|-------|
| P158 | **Self-improvement loop has two failure modes.** Without constraints -> checklists. With constraints -> abstract elegance Haiku can't execute. | 37 |
| P159 | **Concreteness x Abstraction = constant in prism design.** | 37 |

### Frontier Experiments (Round 37, Phases 10-11)

| P# | Principle | Round |
|----|-----------|-------|
| P161 | **Factory prisms match hand-iterated champions.** Sonnet already knows the cognitive operations that 90 experiments discovered. | 37 |
| P162 | **Compression resistance correlates with operation clarity.** ErrRes compresses -40% without quality loss. | 37 |
| P163 | **Cross-language transfer is vocabulary-dependent.** Abstract operations transfer; code-specific degrades. | 37 |
| P164 | **Cross-prism breeding produces novel operations.** ErrRes+Optim hybrid -> "Evidence Cost Map" at 9.0. | 37 |
| P165 | **Model-specificity is noise.** Opus designs better prisms for ALL models, not model-specific ones. | 37 |
| P166 | **Cross-prism hybrids are generalists, not specialists.** Most stable but don't dominate parents. | 37 |
| P167 | **Deep compression can IMPROVE quality.** ErrRes 70w (9.5) > ErrRes 165w (9.0). Fewer words = less drift. | 37 |
| P168 | **Compression resistance is determined by operation concreteness.** | 37 |

### Accuracy & Composition (Round 37)

| P# | Principle | Round |
|----|-----------|-------|
| P170 | **L12 accuracy is target-dependent.** Synthetic: 97%. Real Click: ~42%. ALL line numbers fabricated. Structural insight >> bug finding. | 37 |
| P171 | **Horizontal prism composition is additive.** L12 + audit_code: 21 findings, ZERO overlap. Each prism's power = corresponding blind spot. | 37 |
| P172 | **Vertical composition FAILS for code-vocabulary prisms.** Code prisms drill through analysis text to hallucinated code. Needs reasoning-vocabulary prisms. | 37 |
| P173 | **Codegen prism activation is stochastic on Haiku.** Protocol activates: +4 pts. Skipped: -2 pts. Needs Sonnet. | 37 |

### Alternative Primitive Operations (Round 39)

| P# | Principle | Round |
|----|-----------|-------|
| P175 | **Construction is not the only L8-primitive.** Any concrete, generative operation with observable side-effects bypasses meta-analytical capacity. 7/7 operations work single-shot on Haiku. | 39 |
| P176 | **Five alternative primitives all produce conservation laws on Haiku single-shot (10/10).** Destruction, Simulation, Transplantation, Miniaturization, Forgery. | 39 |
| P177 | **Simulation and Miniaturization are most orthogonal to existing prisms.** Temporal and information-theoretic axes not covered by any current prism. | 39 |
| P178 | **COOKER DRIFT.** COOK_UNIVERSAL absorbs alternative operations into L12's construction pattern. Hand-crafted prompts preserve operational uniqueness; cooked prompts homogenize. Exception: Forgery aligns with construction. | 39 |
| P179 | **Conservation law diversity correlates with prompt operation-specificity.** Operation-specific prompts -> more diverse laws. Cooker homogenizes findings. | 39 |
| P180 | **Sonnet lifts ALL operations by +0.7 avg depth.** Simulation/Miniaturize/Transplant benefit most (hypothetical reasoning). Destruction/Forgery plateau at 8.5. | 39 |
| P181 | **Operations must be imperative steps, not themes.** COOK_UNIVERSAL cannot generate alternative L8 primitives; its template overrides any intent. | 39 |
| P182 | **Content Hallucination.** Cooked lenses via --intent don't anchor model to actual source code. Model hallucinates code content (FastAPI CRUD instead of Starlette routing.py). | 39 |
| P183 | **Taxonomy is a tree above L8.** L9-Simulation produces different meta-law than construction's L9. Diamond topology holds. | 39 |

### Diamond Convergence (Round 39)

| P# | Principle | Round |
|----|-----------|-------|
| P184 | **Diamond topology CONFIRMED (n=2).** Three L8 operations diverge through L9-L11, converge at L12 on the same structural impossibility. | 39 |
| P185 | **L12 convergence point is a structural equivalence class.** "Observer-constitutive" / "observer effect" / "performative contradiction" = same fixed point, three vocabularies. | 39 |
| P186 | **Terminal behavior converges to fixed point regardless of vocabulary.** Construction "terminates," simulation "spirals back," archaeology "reaches bedrock." Same self-referential attractor. | 39 |
| P187 | **Conservation laws are genuinely different at EVERY level except L12.** L9 laws, L10 topologies, L11 impossibilities -- all unique per branch. Only the meta-law is shared. | 39 |
| P188 | **Meta-insight is universal and operation-independent.** "Conservation laws are enacted/deposited/performative, not discovered." Appears across all branches. | 39 |

### Operation Combinations & Cooker Templates (Round 39)

| P# | Principle | Round |
|----|-----------|-------|
| P189 | **Operation combinations produce breadth, not depth.** No combo exceeds individual depth ceiling (8.5). Complementary pairs produce unique cross-findings. Temporally similar pairs interfere. | 39 |
| P190 | **Operation-specific cooker templates preserve operation type.** Key: explicit negative instructions ("No trilemmas, no impossibility proofs"). | 39 |
| P191 | **Three cooker operations on same intent produce WHERE/WHEN/WHY -- zero overlap.** Archaeology: data flows. Simulation: temporal vulnerability. L12: structural impossibility. | 39 |
| P192 | **Cooked prompts require "Execute every step" preamble for Haiku single-shot.** Without it, narrative-style prompts trigger agentic mode. | 39 |

### SDL Compression (Round 39)

| P# | Principle | Round |
|----|-----------|-------|
| P193 | **SDL compression of simulation IMPROVES quality (8.5->8.5-9.0).** Forced concreteness via 3-step format beats narrative temporal cycles. | 39 |
| P194 | **Compression effectiveness is operation-dependent.** Verbose operations benefit most from SDL. Compact operations lose depth. | 39 |

### 3-Cooker Pipeline (Round 39)

| P# | Principle | Round |
|----|-----------|-------|
| P195 | **3-cooker pipeline produces comprehensive intent-specific analysis (9.5 depth).** Structural certainties (4), strong signals (5), unique perspectives (7) from cross-operation validation. | 39 |
| P196 | **Cross-operation synthesis is inherently adversarial.** WHERE/WHEN/WHY disagreements surface naturally. No dedicated adversarial pass needed. | 39 |
| P197 | **3-cooker pipeline = answer to "non-code Full Prism."** COOK_ARCH(WHERE) + COOK_SIM(WHEN) + COOK_L12(WHY) -> synthesis. 4 calls, 9.5 depth. Matches Full Prism at half the calls. Works on ANY domain. | 39 |

---

## Principles by Theme

### Prompt Engineering
D1-D5, P100-P103, P116, P141, P158, P159, P167, P181, P192

### Model Behavior & Routing
D7, D9, D18, P104-P108, P113, P114, P120, P135, P145, P150, P165, P173, P180

### Compression & Taxonomy
D11, D12, D17, D19, P108, P113, P162, P167, P168, P183-P188, P193, P194

### Cooker & Meta-Prompt
D14, P73, P74, P99, P151-P153, P161, P178, P179, P181, P182, P190-P192

### Operations & Construction
D5, D10, P140-P144, P175-P177, P189

### Prism Design & Discovery
P128, P129, P132-P134, P138, P141-P143, P159, P164, P166

### Composition & Pipelines
P154, P155, P170-P172, P195-P197

### Code Generation
P115-P119, P173

### Convergence & Reflexivity
D6, D12, P184-P188

---

## Round 40: VPS Validation Battery (Mar 14, 2026)

| # | Principle | Evidence |
|---|-----------|----------|
| P198 | **L12 scales to 2700 lines with no quality degradation.** Larger files produce richer conservation laws — Rich console.py (2684L) scored 10.0, the highest in 40 rounds. | P3 batch: Flask 9.5, Rich 10.0, Requests 9.5 |
| P199 | **sdl_simulation degrades cross-target (7.0-7.5 vs 8.5-9.0 Starlette baseline).** The 3-step SDL compression loses temporal depth. Full simulation prism significantly outperforms its SDL variant on Click/Tenacity. | P1 batch: Click 7.0, Tenacity 7.5 |
| P200 | **l12 fails on pure creative input (conversation mode) but succeeds on structured creative (UX with metrics/constraints).** l12_universal works on everything. Compression forces domain neutrality — 73w has no room for code vocabulary that triggers confusion on creative inputs. | R5 batch: l12 poetry 5.0, l12 UX 9.5, l12u poetry 9.0, l12u UX 8.5 |
| P201 | **Vertical composition works for meta-analytical prisms but fails for constructive prisms.** claim prism analyzes the analysis (7.5). deep_scan/pedagogy revert to analyzing original code extracted from L12 quotes (7.0/6.5). Operation type determines vertical transferability. | R7 batch |
| P202 | **70w is below the analytical compression floor on Haiku.** SDL at 180w is the empirical minimum for genuine structural insight. At 70w, models enumerate rather than analyze — fill slots instead of derive. | A4 batch: errres70w avg 7.0 vs full errres 9.0 |
| P203 | **Miniaturize Sonnet lift = +1.5 (exceeds +0.7 average).** But 8.0 is at the production floor, not above it. Conservation laws generic. Operation overlaps with L12's improvement cycles. Not promoted. | R2 batch: Sonnet 8.0 vs Haiku 6.5 |
| P204 | **Solve model matters as much as cook model for cooked prisms.** Sonnet cook + Sonnet solve produces 2x the output of Sonnet cook + Haiku solve (1772w vs 871w avg). Same cooked prism, dramatically different depth. | R1 batch: 3 intents × 2 models |

### Theme Index (Round 40)
- **Scaling**: P198
- **Prism Design**: P199, P202, P203
- **Domain Universality**: P200
- **Composition**: P201
- **Model Routing**: P204

## Round 41: Knowledge Gap Detection (Mar 15, 2026)

~95 VPS experiments. Discovery: LLM analysis confabulates specific claims while structural insights are reliable. Built gap detection pipeline + single-pass self-correcting analysis (L12-G). Universal conservation law found.

| # | Principle | Evidence |
|---|-----------|----------|
| P205 | **Skills work cross-model at 70B+ with correct structure but shorter output.** Sonnet 2-3x more words than Hermes 3/Llama 70B on same skill. Quality difference is depth, not structure. | Hermes hackathon cross-model validation |
| P206 | **Gap detection is a separate cognitive operation from structural analysis.** Complementary prisms: knowledge_boundary (classification) + knowledge_audit (adversarial). Neither catches all errors alone. But CAN be compressed into L12-G single-pass. | J1-J4: boundary caught asyncio.RWLock, audit caught quadratic. 4/4 targets. |
| P207 | **`Specificity × Verifiability = Constant` — universal conservation law of LLM analysis.** Analysis is strongest where most abstract, weakest where most concrete. 4/4 targets converge independently. | J2 (Starlette), J5 (Click, Tenacity), J4 (Profile) — same product-form law, 4 different vocabularies. |
| P208 | **Gap type distribution shifts with domain.** Code → CONTEXTUAL/TEMPORAL (version-dependent claims). Text → ASSUMED (psychological/strategic). The gap detector automatically routes to the right fill mechanism. | J1-J4: code has API_DOCS/CVE_DB/CHANGELOG gaps. Profile has COMMUNITY/MARKET/BENCHMARK gaps. |
| P209 | **Gap detection pipeline converges in 1 iteration.** Augmented output has fewer gaps; remaining gaps are genuine external dependencies (algorithm theory, regex engine), not confabulation. | EXP-B: boundary on augmented output = mostly STRUCTURAL claims. No recursion needed. |
| P210 | **L12-G (3-phase single-pass) eliminates confabulation at same cost as L12.** Analyze → audit → self-correct in one prompt. Zero confabulated claims. Compression of 4-call pipeline to 1 call. | BT-1: 817w, 0 errors. Augmented L12: 652w, 0 errors. Original L12: 1,119w, 2 errors. |
| P211 | **Reflexive gap detection (L13) reveals assumptions masquerading as structural truths.** The gap detector applied to itself finds 4 blind spots the original audit missed. Refined law: `ACTIONABILITY ∝ FALSIFIABILITY / CONFIDENCE`. | BT-2: meta-audit found practical significance, Python re caching, heuristic-as-law confusion. |
| P212 | **Confabulation predictable from surface features.** High specificity + not quoted from source = HIGH risk. Line numbers, specific API names, performance numbers. Structural observations = LOW risk. | BT-4: predictor correctly flags all line numbers, reconstructed code, internal attribute names. |
| P213 | **Augmented L12 scores HIGHER than original (8 vs 7) with 42% fewer words.** Verified facts constrain model to stay grounded. Pipeline improves quality, not just removes errors. | EXP-A: haiku-as-judge L12=7, augmented=8. 652w vs 1,119w. |
| P214 | **5-tier confidence system (STRUCTURAL > DERIVED > MEASURED > KNOWLEDGE > ASSUMED) provides more granular epistemic classification than 4-tier.** DERIVED catches reasoning errors; MEASURED catches testable claims. V2 extracts 2.8x more claims. | ST-1/ST-6: gap_extract_v2 = 28 claims vs v1 = 10 gaps. Starlette + Click validated. |
| P215 | **L12-G is domain-adaptive — does NOT refuse on non-code input.** Self-corrects on any domain. Board meeting narrative → conservation law + 5 structural defects + self-correction. Confirms P15 (code nouns = mode triggers). | ST-3: L12-G on business text, 917w, full 3-phase output. |
| P216 | **Conservation laws consistently flagged as ASSUMED (confidence 0.18-0.2).** They are analytical constructs, not empirical facts. The gap detector correctly identifies this. | ST-1: conservation law = ASSUMED (0.2). ST-6: trilemma = ASSUMED (0.18). |
| P217 | **Knowledge<T> prism produces typed claims with provenance across codebases.** Every finding carries Type/Confidence/Provenance/Falsifiable/If-wrong. Scores lower on depth rubric (7 vs L12-G 9) because typing fragments narrative flow — but epistemic quality is higher. | ST-2/ST-5/ST-7: Starlette 1,180w, Click 1,021w, Tenacity 1,215w. XT-1: score 7. |

| P218 | **Prism composition is massively non-commutative.** L12→audit = 1,137w of structured analysis. audit→L12 = 18w (catastrophic — model enters planning mode). Pipeline order is a structural requirement. Audit vocabulary triggers "task planning" patterns that override L12's "architectural analysis" mode. Confirms K20 quantum contextuality and K11 non-commutative monoid. | N13: L12→audit=1,137w. audit→L12=18w. |
| P219 | **Current rubrics reward impressiveness, not trust.** L12 scores 12/12 by confabulating APIs. Oracle scores 9/12 by being honest. S×V=C predicts this: high verifiability (trust) = low specificity (impressiveness). The rubric measures S; Oracle optimizes for V. Every AI benchmark that doesn't account for confabulation is measuring the wrong thing. | Oracle battle: L12=12 (confabulates), Oracle=9 (zero confab), Vanilla=11. |

### Theme Index (Round 41)
- **Knowledge Gap Detection**: P206, P207, P208, P209
- **Self-Correction**: P210, P211, P212, P213
- **Epistemic Classification**: P214, P216, P217
- **Composition**: P218
- **Evaluation**: P219
- **Domain Universality**: P215
- **Cross-Model**: P205
