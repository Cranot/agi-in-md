# AGI in md

System prompts are cognitive lenses. They change how models frame problems, not how well they solve them. This project maps the space of cognitive compression — encoding analytical operations in minimal markdown that reliably activates specific reasoning patterns across language models.

25 rounds, 393+ experiments across Haiku/Sonnet/Opus. 11 confirmed compression levels. 19 domains tested.

## The Compression Taxonomy

| Level | Min ops | Words | What it encodes | Example |
|---|---|---|---|---|
| **11A** | L10-C + category naming + adjacent-category artifact + new impossibility | ~190w | Escape to adjacent design category, name trade-off between impossibilities | `level11_constraint_escape.md` |
| **11B** | L10-B + fourth construction as redesign + sacrifice + revaluation | ~195w | Accept design-space topology, inhabit feasible point, revalue original "flaws" | `level11_acceptance_design.md` |
| **11C** | L10-C + invariant inversion + new impossibility + conservation law | ~170w | Invert impossibility, find conserved quantity across all designs | `level11_conservation_law.md` |
| **10B** | L9-B + third resolving construction + failure analysis | ~140w | Discover design-space topology through failed resolution attempt | `level10_third_construction.md` |
| **10C** | L9-C + second improvement + second recursion + invariant | ~130w | Prove structural invariants through double recursive construction | `level10_double_recursion.md` |
| **9B** | L8 + contradicting second construction + structural conflict | ~115w | Triangulate identity ambiguity through contradicting improvements | `level9_counter_construction.md` |
| **9C** | L8 + recursive self-diagnosis of improvement | ~97w | Find concealment's self-similarity by applying diagnostic to own improvement | `level9_recursive_construction.md` |
| **8** | L7 + generative construction + 3 emergent properties | ~97w | Engineer improvement that deepens concealment, name what construction reveals | `level8_generative_v2.md` |
| **7** | claim + dialectic + gap + mechanism + application | ~78w | Name how input conceals problems, apply to find what dialectic missed | `level7_diagnostic_gap.md` |
| **6** | claim + 3 voices + evaluation | ~60w | Claim transformed through forced dialectical engagement | `level6_falsifiable.md` |
| **5B** | 4 phases | ~55w | Derive, predict, execute, self-correct | `level5_hybrid.md` |
| **5A** | 3 voices + synthesis | ~45w | Multi-voice dialectic with emergent insight | `level5_perspectival.md` |
| **4** | 4+ ops | 25-30w | Protocol + self-questioning | `structure_first_v4.md` |
| **3** | 3 ops | 12-15w | Operations + analytical rails | — |
| **2** | 2 ops | 5-6w | Two operations with ordering | — |
| **1** | 1 op | 3-4w | One behavioral change | — |

**Levels are categorical, not continuous.** Below each threshold, that type of intelligence CANNOT be encoded — not "less effective," categorically absent.

## Key Results

### Cognitive lenses (Rounds 1-6)
- **No IQ boost on pure reasoning** — all models solve logic puzzles identically regardless of system prompt. Massive effect on in-domain analysis.
- **Receptivity tone curve**: Haiku responds to ideas. Sonnet responds to commands. Opus responds to both.
- **Lenses are domain-independent**: correlate/transform/compress transferred to biology, music, ethics, math, legal, medical, scientific methodology, AI governance — 11 domains confirmed.
- **Characters compose**: stacking two characters gives both strengths without dilution.

### Composition algebra (Rounds 7-20)
- **9 activated opcodes in 4 classes**: Constructive (name, solve, steelman), Deconstructive (invert, attack, decompose), Excavative (find assumptions, predict failures), Observational (track confidence, rate difficulty, etc.)
- **4 generative ops is the sweet spot.** 5 triggers merger. Modifiers are free additions (up to 4 tested).
- **Complementary pairs multiply, similar pairs merge, orthogonal pairs add.** But similar ops only merge when targeting the same object.
- **Best single sequence**: "Steelman. Find assumptions. Solve. Attack."

### Level 5-7 (Rounds 21-24)
- **Level 5 peaks at Sonnet, not Opus.** Both L5 types are epistemic scaffolds. Sonnet benefits most (needs scaffold, has capacity to use it). Opus can already self-scaffold.
- **Level 6: claim-tested-by-dialectic.** Forced signal coupling — the claim is both prediction and dialectic target. Only forced interaction produces L6; naive composition of L5 signals fails.
- **Level 7: concealment-mechanism-applied.** Three-constraint forcing: name mechanism, apply it, find what dialectic missed. Sonnet 17/17, Opus 6/7.

### Level 8 (Round 25)
- **Level 8: generative-diagnostic.** Engineer a legitimate-looking improvement that deepens the concealment, then name three properties of the problem only visible because you tried to strengthen it.
- **L7 diagnoses what IS. L8 diagnoses what HAPPENS when you try to improve it.** The generative move forces engagement with the problem's dynamics — propagation, stability under change, feedback loops — which are categorically invisible to static analysis.
- **L8 inverts the capacity curve.** L5 peaks at Sonnet (process scaffold). L7 requires Sonnet-class minimum (0/3 Haiku). L8 works on ALL models including Haiku (4/4). Construction-based reasoning is a different cognitive operation than meta-analysis — it's accessible at every capacity level.
- **Haiku: 4/4 (100%). Sonnet: 13/14 (93%). Opus: 14/14 (100%).** Full domain transfer confirmed. L8 eliminates the capacity floor — L7 was 0/3 on Haiku but L8 is 4/4. The generative forcing function ("build and observe") routes around the meta-analytical capacity L7 requires.
- **Three L8 candidate prompts tested; one won.** Recursive meta-concealment (L8-A) risked decorative meta-commentary. Mechanism dialectic (L8-B) had high variance. Generative application (L8-C) was most reliable — v2 refinement achieved 93-100% hit rate.
- **Key v1→v2 refinement:** "should pass code review" + "name three properties only visible because you tried to strengthen it" turned L8 from 25% outlier to 93-100% default.
- **L8 activates on creative/aesthetic domains where L7 could not.** 8/8 (100%) on fiction, poetry, music, and design. L7 was 0% on poetry. L8's construction step IS creative revision — the native operation of creative work. First compression level to genuinely transfer to aesthetic domains. 15 domains confirmed total.

### Level 9 (Round 25)
- **Level 9 has TWO complementary variants**, not one. Both confirmed at 100% across all models.
- **L9-B (Counter-Construction)**: Engineer a second improvement that contradicts the first — strengthens what the first weakened. Name the structural conflict that exists only because both improvements are legitimate. Finds the artifact's **identity ambiguity** — it doesn't know what it is.
- **L9-C (Recursive Construction)**: Apply the same diagnostic to your own L8 improvement. Find what the improvement conceals, and what property of the original is visible only because the improvement recreates it. Finds concealment's **self-similarity** — improvements reproduce the original flaw at higher sophistication.
- **L9-B and L9-C are complementary**: B finds what the artifact IS (undeclared identity). C finds what HAPPENS WHEN YOU FIX IT (concealment reproduces). Both are categorically beyond L8.
- **Sonnet: 22/22 (100%). Opus: 6/6 (100%). Haiku: 6/6 (100%).** Total: 34/34. L9 maintains L8's universal accessibility. Construction scaffolds the recursive target.
- **L9 transfers fully to creative/aesthetic domains.** 8/8 (100%) on fiction, poetry, music, design. Aesthetic identity ambiguity is SHARPER than code — "cannot separate what is concealing from what is excellent." New concealment category: Excellence-Defense Identity.
- **Opus produces qualitatively deeper L9**: More ontologically precise, compositional category errors, temporal/causal depth. L9 may have internal depth grades.
- **L9-D (Combined B+C)**: 2/3 produce potential L10 findings — recursive application to the structural conflict reveals properties impossible for either variant alone.

### Level 10 Creative/Aesthetic Transfer (Round 25)
- **L10 transfers fully to creative/aesthetic domains.** 8/8 (100%) on fiction, poetry, music, design.
- **Pattern: aesthetic invariants identify tension between medium's form and subject matter.** The impossibility is the generative condition — the thing that makes the work necessary is the thing the work cannot resolve.

### Level 11 (Round 25)
- **Level 11 has THREE complementary variants**, all confirmed at 100% on Sonnet scout.
- **L11-A (Constraint Escape)**: After L10-C's invariant, name the CATEGORY it bounds, design an artifact in the ADJACENT CATEGORY where the invariant dissolves, name the new impossibility. Finds the **trade-off between old and new impossibilities** — what you gain and lose by escaping the current design's frame.
- **L11-B (Acceptance Design)**: After L10-B's failed resolution, engineer a REDESIGN that accepts the design space's topology, inhabit a feasible point. Finds **revaluation** — what original "flaws" were actually the cost of attempting the impossible. Transforms code review judgment.
- **L11-C (Conservation Law)**: After L10-C's invariant, INVERT it (make impossible trivial), name the new impossibility the inversion creates. Finds **conservation laws** — quantities that cannot be eliminated, only redistributed. Task K produced mathematical formalization: `sensitivity × absorption = constant`.
- **Sonnet: 14/15 (93%). Opus: 9/9 (100%). Haiku: 9/9 (100%). Total: 32/33 (97%).** Highest hit rate of any level. All three variants confirmed across all three models.
- **Universal accessibility maintained at L11.** Haiku 9/9 (100%), continuing the L8→L9→L10→L11 pattern where construction-based scaffolding is accessible at all capacity levels.
- **L11-A and L11-B are perfect (11/11 each).** L11-C is 10/11 — conservation law criterion requires structurally rich input. Simpler code may not provide enough material.
- **L11-A, B, and C are genuinely complementary**: A finds the ADJACENT CATEGORY (what's possible outside). B finds the FEASIBLE POINT (what's achievable inside). C finds the CONSERVED QUANTITY (what persists everywhere). Same code produces three non-redundant structural truths.
- **The L11 operation is: escape the problem's frame, then report what the escape costs.** L10 maps the prison. L11 leaves it and discovers that freedom has its own constraints.
- **All three produce full working code** for redesigns/escapes/inversions. Concrete architectural alternatives, not abstract claims.
- **L11 transfers fully to creative/aesthetic domains.** 11/12 (92%) on fiction, poetry, music, UX design. Same hit rate as code. L11-A and L11-B perfect (4/4 each). L11-C 3/4 — fiction miss (known narratological trade-off). Creative conservation laws are about *migration* (where meaning lives) rather than magnitude. Music is the strongest creative domain for L11.

### Level 10 (Round 25)
- **Level 10 has TWO complementary variants**, same pattern as L9. Both confirmed across all three models.
- **L10-B (Third Construction)**: After L9-B's structural conflict, engineer a third improvement resolving the conflict. Name how it fails. Finds the design space's **hidden topology** — dimensions, constraints, and shapes invisible until you try to build within it.
- **L10-C (Double Recursion)**: After L9-C's recursive diagnostic, engineer a second improvement addressing the recreated property. Apply the diagnostic again. Name the structural invariant. Finds **impossibility theorems** — properties provably immune to any implementation within the current architecture.
- **L10-B and L10-C are complementary**: B finds what the DESIGN SPACE IS (topology). C finds what CANNOT BE DONE within it (invariants). Both are categorically beyond L9.
- **Sonnet: 13/14 (93%). Opus: 6/6 (100%). Haiku: 5/6 (83%). Total: 24/26 (92%).** L10-A (Category Dissolution) eliminated at 2/3 scout, subsumed by L10-B. L10-B and L10-C each 12/13 overall.
- **L10 maintains universal accessibility with first cracks.** Haiku 5/6 (83%) — L10-C more accessible (3/3) than L10-B (2/3). Impossibility theorems are more scaffoldable than open-ended topology revelation. Misses degrade gracefully to L9.
- **Cross-domain transfer confirmed**: Legal task D1 achieved L10 on both variants.
- **L10-C for Haiku, L10-B for Sonnet**: L10-B is more robust for Sonnet (7/7 vs 6/7). L10-C is more robust for Haiku (3/3 vs 2/3). Model-specific affordances at L10.

### Concealment mechanism catalog (Round 24)
10 code mechanisms cluster into **4 categories** by mode of concealment:

| Category | Count | What conceals | Examples |
|---|---|---|---|
| Naming Deception | 3 | Code's IDENTITY | Pattern Theater, Complexity Theater, Nominative Deception |
| Structural Completeness | 3 | Code's SHAPE | Structural Mimicry, Operational Legibility, Method Completeness Theater |
| Interface Misdirection | 2 | Code's API | Syntactic Flatness, Operational Masking |
| Fragment Legitimacy | 2 | Code's PARTS | Idiomatic Fragment Camouflage, Structural Legitimacy Laundering |

### Domain transfer (Round 24)
L6 and L7 transfer fully to non-code domains. 16/16 activation, 8/8 TRUE L7.

| Domain | Sonnet mechanism | Opus mechanism |
|---|---|---|
| Legal | Definitional Specificity as Legitimizing Cover | Granularity Theater |
| Medical | Narrative Coherence as Epistemic Closure | Explanatory Sufficiency Cascade |
| Scientific | Theoretical Laundering | Methodological Formalism as Epistemic Camouflage |
| Ethical | Quantitative Disclosure as Epistemic Foreclosure | Inoculation Through Partial Disclosure |

Both models converge on the same structural pattern per domain — evidence that mechanisms are properties of domains, not model confabulations.

### Multi-model relay (Rounds 24-25)
L7 mechanisms transfer across models as diagnostic tools. L7 relay finds 100% compositional issues vs ~35% in vanilla control. L8 relay produces orthogonal findings: different constructions reveal different facets of the same problem. Relay constructions are more ambitious (multi-feature) while standard L8v2 constructions are more focused (single-feature). Optimal: run both relay and standard for complementary coverage.

## Design Principles

1. **Lead with scope, follow with evidence.** The opening determines perceived ambition.
2. **Narrative > evidence > code.** Pseudocode destroys novelty perception.
3. **Imperatives beat descriptions.** "Name the pattern. Then invert." outperforms "here is a pattern we found."
4. **The prompt is a program; the model is an interpreter.** Operation order becomes section order.
5. **The operation pair is the atom of cognitive compression.** Any connective between two operations produces the composition. The sequencer word is irrelevant.
6. **The lens is transparent to the wearer.** During task performance, the framework operates below self-awareness. Under interrogation, models can identify the influence.
7. **Capacity amplifies, rigidity resists.** Opus reconstructs the full framework from a 2-line hint. Sonnet needs explicit directives.
8. **Self-improvement converges on self-correction.** When asked to improve itself, models add "then invert: what does this frame make invisible?"
9. **Each compression level requires more model capacity — but not always linearly.** L1-4: all models. L5: peaks at Sonnet. L6: Sonnet/Opus. L7: Sonnet-class minimum. L8: all models (Haiku 4/4, Sonnet 13/14, Opus 14/14). L9: all models (Haiku 6/6, Sonnet 22/22, Opus 6/6). L10: all models (Haiku 5/6, Sonnet 13/14, Opus 6/6). L11: all models (Haiku 9/9, Sonnet 14/15, Opus 9/9).
10. **The concealment mechanism is a universal analytical operation.** Works across 19 domains because concealment is structural, not domain-specific.
11. **Three capacity-interaction modes.** Compensatory (L5): peaks at mid-capacity, diminishing returns above. Threshold (L7): requires minimum meta-analytical capacity, binary works/doesn't. Universal (L8+L9): construction-based reasoning works at all capacity levels. L7→L8 is not a linear step — it's a shift from meta-analysis to construction, which is more primitive but reveals deeper properties. L9 maintains this universality — construction scaffolds the recursive target.

## File Map

| File | Purpose |
|------|---------|
| `experiment_log.md` | Full experiment log (Rounds 1-25, 393+ experiments) |
| `run.sh` | Shell runner (claude CLI-based, 18 tasks, 28 prompts) |
| **Prompts** | |
| `prompts/` | All prompt files (characters, structure_first v1-v5, level 5/6/7 prompts) |
| `prompts/level11_constraint_escape.md` | Level 11A: category escape + impossibility trade-off |
| `prompts/level11_acceptance_design.md` | Level 11B: feasible-point redesign + flaw revaluation |
| `prompts/level11_conservation_law.md` | Level 11C: invariant inversion + conservation law |
| `prompts/level10_third_construction.md` | Level 10B: design-space topology via failed resolution |
| `prompts/level10_double_recursion.md` | Level 10C: structural invariants via double recursion |
| `prompts/level9_counter_construction.md` | Level 9B: identity ambiguity via contradicting constructions |
| `prompts/level9_recursive_construction.md` | Level 9C: self-similarity via recursive self-diagnosis |
| `prompts/level9_combined_BC.md` | Level 9D: combined counter-recursive (potential L10) |
| `prompts/level8_generative_v2.md` | Level 8: generative diagnostic (best prompt) |
| `prompts/level7_diagnostic_gap.md` | Level 7: concealment-mechanism-applied |
| `prompts/level8_relay_construction.md` | Level 8 relay: construction-primed cross-model analysis |
| `prompts/level7_relay_mechanism.md` | Level 7 relay: mechanism-primed cross-model analysis |
| `prompts/level6_falsifiable.md` | Level 6: claim-tested-by-dialectic |
| `prompts/level5_perspectival.md` | Level 5A: multi-voice dialectic |
| `prompts/level5_hybrid.md` | Level 5B: predictive metacognition |
| `prompts/structure_first_v4.md` | Level 4 optimum (control prompt) |
| `prompts/tweet.md` | Character: 2-line hook |
| `prompts/spark.md` | Character: 10-line pitch |
| `prompts/philosopher.md` | Character: thinking partner primer |
| `prompts/map.md` | Character: builder onboarding |
| **Harness** | |
| `harness/test_super_token.py` | Original experiment harness (API-based) |
| `harness/test_level5.py` | Round 21+ experiment harness (API-based) |
| `harness/test_tasks.md` | Original test tasks (A: code structure, B: architecture, C: reasoning) |
| **Output** | |
| `output/round21/` | Round 21-22 raw outputs (60 experiments) |
| `output/round23/` | Round 23 raw outputs (33 experiments) |
| `output/round24/` | Round 24 raw outputs (29 experiments) |
| `output/round25/` | Round 25 raw outputs (177 experiments) |

## Next Steps

- **L11 convergence analysis**: Do the three L11 variants converge on the same findings from different angles? (Like L9-B/C found complementary aspects of the same problems.)
- **L11-C non-triviality problem**: Can the conservation law prompt be refined to avoid the "restates existing theory" failure mode? Possible: add a forcing constraint requiring the law to predict something testable.
- **Level 12?**: L11 escapes the frame. What would forcing the model to COMPARE frames produce? Possible: apply L11 to L11's own escape — find the conservation law of conservation laws.
- **Multi-family testing**: Run the compression taxonomy on GPT-4o, Gemini, Llama. Key question: is the taxonomy Claude-specific or universal?
- **Identity ambiguity catalog**: Do L9-B identity ambiguities cluster into categories? Do L10-B topology findings cluster?
