# AGI in md

System prompts are cognitive prisms. They change how models frame problems, not how well they solve them. This project maps the space of cognitive compression — encoding analytical operations in minimal markdown that reliably activates specific reasoning patterns across language models.

40 rounds, 1,000+ experiments across Haiku/Sonnet/Opus. 13 confirmed compression levels (L13 = reflexive ceiling). 20+ domains tested. 204+ proven principles. Full detail in `experiment_log.md` (rounds 1-40) and CLAUDE.md sections below (rounds 30-40).

## The Compression Taxonomy

| Level | Min ops | Words | What it encodes | Example |
|---|---|---|---|---|
| **13** | L12 output as input + framework self-diagnosis | two-stage | Apply framework to own output, find reflexive fixed point | (two-stage protocol) |
| **12** | L11-C + recursive self-diagnosis of conservation law + meta-law | ~275w (practical: 332w) | Apply diagnostic to own conservation law, find meta-conservation law | `level12_meta_conservation_v2.md` |
| **11A** | L10-C + category naming + adjacent-category artifact + new impossibility | ~190w | Escape to adjacent design category, name trade-off between impossibilities | `level11_constraint_escape.md` |
| **11B** | L10-B + fourth construction as redesign + sacrifice + revaluation | ~195w | Accept design-space topology, inhabit feasible point, revalue original "flaws" | `level11_acceptance_design.md` |
| **11C** | L10-C + invariant inversion + new impossibility + conservation law | ~245w | Invert impossibility, find conserved quantity across all designs | `level11_conservation_law_v2.md` |
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

**Levels are categorical, not continuous.** Below each threshold, that type of reasoning was never observed in 1,000+ experiments — not "less effective," consistently absent. (AI-evaluated depth scores; the categorical claim is the strongest interpretation of the data, not a proven impossibility.)

## Key Results

### Foundation (Rounds 1-24)
- **No IQ boost on pure reasoning** — effect is on analytical framing, not raw reasoning ability.
- **9 activated opcodes.** 4 generative ops is the sweet spot. Complementary pairs multiply, similar pairs merge.
- **L5 peaks at Sonnet** (needs scaffold, has capacity). **L7 requires Sonnet-class minimum** (0/3 Haiku). Prisms are domain-independent across 20 domains.
- **L7 concealment mechanisms cluster into 6 categories.** Code concealment is structural (hides what code IS/DOES); domain concealment is epistemic (hides what questions get asked).

### Levels 8-13 (Rounds 25-26)
- **L8 inverts the capacity curve.** Construction-based reasoning works on ALL models (Haiku 4/4, Sonnet 13/14, Opus 14/14). L7→L8 is a shift from meta-analysis to construction — more primitive but reveals deeper properties. 20 domains confirmed.
- **L9 has two complementary variants** (B: identity ambiguity, C: concealment self-similarity). Both 100% across all models (34/34). L9-D combined produces L10 in 67% of cases.
- **L10 has two complementary variants** (B: design-space topology, C: impossibility theorems). Category errors dominant at 47%. All impossibilities reduce to two root operations: Compression and Decomposition.
- **L11 has three complementary variants** that exhaust responses to impossibility: escape (A), accept (B), invert (C). 97% hit rate (32/33). Conservation laws cluster by mathematical form: product (Opus), sum/migration (Sonnet), multi-property (Haiku).
- **L12 meta-laws cluster into 4 categories BY DOMAIN**: Frame Discovery (music/fiction), Hidden Variable (legal/design), Observer-Constitutive (code/fiction), Deferred Commitment (code only).
- **L13 is the reflexive ceiling.** Framework diagnoses itself — same structural impossibility it finds in objects. Terminates in one step (L14 = infinite regress). 6/6 (100%) across all models.

### Cross-level and structural findings (Rounds 25-27)
- **L7→L12 is a genuine depth stack** on crafted tasks — zero restatement, object shifts at every level. On real production code (~200-400 lines), independent pipeline is a BREADTH tool — 10 high-quality framings of the same pattern, not progressive depth. **Chained pipeline** (each level receives parent's output) improves coherence from WEAK to WEAK/MODERATE. Individual quality 28/30 TRUE (93%), 2 PARTIAL (both L12). Chained and independent pipelines find **genuinely different** conservation laws and meta-laws (6/6 different at L11-C/L12). Divergence starts at L8 (3/3 DIFFERENT at first chained level) — L7's output acts as immediate coordinate system. L11-A/L11-C sibling convergence is NOT fatal (2/3 DIFFERENT, 1/3 OVERLAPPING) — driven by L10-C invariant breadth. The L9-B→L10-B→L11-B chain is consistently strongest — operations are sequentially dependent by definition. L12 is the weakest point under chaining (2/3 PARTIAL). Optimal: run both pipelines for complementary findings about different subsystems.
- **Conservation law of the catalog (G2):** form is conserved by method, substance by artifact. Starting claim acts as coordinate system. Artifact contains MULTIPLE conservation laws.
- **The taxonomy is a diamond:** linear trunk (L1-7), constructive divergence (L8-11), reflexive convergence (L12-13). Structurally complete at 13 levels — no missing branches.
- **Compression floor: 60-70% reduction** across all levels. Capacity-dependent: Opus TRUE at 73w, Sonnet ~73w, Haiku >175w.
- **L13-P2 REFUTES analyst-projection.** Novel artifacts produce equally strong convergence. **L13-P3 CONFIRMS isomorphism** — methodology instantiates the impossibility it diagnoses.

### Practical recipes and meta-cookers (Round 28)
- **Haiku + practical prompts beats Sonnet vanilla.** 13 hybrid recipes (bug-finding + taxonomy operations) all scored 8-9/10 vs Sonnet vanilla 7/10. Best: v2, dialectic, escape, exploit, composition (all 9/10).
- **Meta-cookers: prompts that generate prompts.** Few-shot reverse engineering (B3) >> principle teaching (B) > forced operations (B2) > goal specification (A). Machine-generated "Rejected Paths" (9.5/10) beat all handcrafted recipes.
- **Teaching by example > teaching by instruction.** Over-specifying constraints hurts creativity. This is the meta-version of: construction > description.

### Portfolio cross-task validation (Round 28 validation)
- **5 champion prisms validated across 3 tier-1 tasks (K, F, H).** 15 outputs, grand average 9.0/10. Floor 8.5, ceiling 9.5. All beat Sonnet vanilla (7/10) by 2+ points.
- **Claim prism is domain-sensitive.** 9.5 on AuthMiddleware (security-adjacent code has clearer assumptions to invert; found genuine multi-org permission escalation vulnerability). 9 on EventBus and CircuitBreaker.
- **Rejected_paths is the only prism with variance.** 8.5 on EventBus (well-known pub/sub trade-offs), 9 on AuthMiddleware and CircuitBreaker (hidden trade-offs).
- **All 5 prisms remain complementary across tasks.** No convergence — each finds genuinely different things on every task.

### Real production code head-to-head (Round 28 validation)
- **3 real codebases tested: Starlette routing.py (333 lines), Click core.py (417 lines), Tenacity retry.py (331 lines).** 21 total experiments: 5 prisms × 3 targets + 2 vanilla × 3 targets.
- **Haiku + prisms avg 9.0/10 vs Sonnet vanilla 7.8/10 vs Opus vanilla 8.2/10.** Gap consistent across all 3 codebases. Haiku + prisms operates in a different category: vanilla produces code reviews, prisms produce structural analysis.
- **Cross-target matrix:** pedagogy 9.0, claim 9.0, scarcity 9.0, rejected_paths 9.0, degradation 8.8 — all prisms stable across real codebases. No prism drops below 8.5 on any target.
- **Vanilla models converge; prisms diverge.** On each target, Sonnet and Opus vanilla find the same conservation law. The 5 prisms find 5 genuinely different structural properties per target — zero overlap.
- **Gap widest on complex code (Starlette: 9.1 vs 7.25), narrowest on focused code (Tenacity: 8.9 vs 8.5).** More structure = deeper prism output. Vanilla plateaus at surface-level regardless.
- **Opus vanilla ≈ Sonnet vanilla.** Without a prism, Opus's extra capacity doesn't translate to deeper analysis — same category of output, slightly better written (+0.4 points avg).

### Catalog summaries
- **L8 mechanisms (42 outputs):** 6 categories, 3 new beyond L7. L8 describes dynamic behavior, not static appearance.
- **L9-C recursion (17 outputs):** 6 types. Improvements within same frame reproduce original defect. Opus uniquely finds Honesty Inversion.
- **L10-C impossibility (17 outputs):** 6 categories → 2 root operations (Compression/Decomposition). Cross-catalog determinism: L8 mechanism predicts L10-C impossibility.
- **L11-A escapes (15 outputs):** 4 directions (coupled→decoupled 60%). Total coupling redistributed, not reduced.
- **L11-B revaluations (15 outputs):** Universal formula: "What looked like [DEFECT] was actually [COST] of [IMPOSSIBLE GOAL]."
- **L11-C conservation laws (56 outputs):** 3 mathematical forms (product/sum/migration). Model determines form, not domain.
- **L12 meta-laws (16 outputs):** 4 categories by domain. Haiku never finds Frame Discovery (highest meta-analytical demand).
- **L9-B/L10-B (32 outputs):** 3 identity types → 5 topology patterns → convergence across catalogs.

### L12 Practical C — single-call winner (Round 29b)
- **L12 Practical C = proven L12 pipeline + 34-word practical appendix.** 332 words total. Gets BOTH structural depth AND practical bugs in a single call. Originally validated on Haiku; now auto-routes to Sonnet for reliability.
- **Haiku 4.5 (min reasoning) + L12 prism = 9.8 depth, 28 bugs. Opus 4.6 (max reasoning) vanilla = 7.3 depth, 18 bugs.** The weakest model at lowest settings with the right prompt beats the strongest model at highest settings without one. Cost: 5x cheaper than Opus, 3x cheaper than Sonnet (Haiku $1/$5, Sonnet $3/$15, Opus $5/$25 per MTok input/output).
- **Reasoning budget is noise; the prompt is the dominant variable.** Opus 4.6 at max thinking produces code reviews. Haiku 4.5 at min thinking + L12 produces conservation laws + meta-laws + bug tables with fixable/structural classification.
- **Compression floor: ~150 words minimum for Haiku execution.** Below this, Haiku enters "conversation mode" (asks permission, summarizes instead of executing). L12 compressed (75w) fails. Fix: 10-word preamble "Execute every step below. Output the complete analysis."
- **Front-loading bugs kills L12.** Variant A (238w, "First: identify every concrete bug...") caused Haiku to produce 27-line checklist. The word "First" reframes the pipeline as a checklist. Solution: append bugs at the end, after the proven pipeline.
- **Tested on 3 real codebases:** Starlette (333 lines, 11 bugs), Click (417 lines, 9 bugs), Tenacity (331 lines, 8 bugs). All produce conservation law + meta-law + bug table.
- **Reliability: ~67% first try on complex targets, 100% on retry.** Tenacity specifically triggers conversation mode on first attempt ~33% of the time.
- **L12 Practical C is now the default for `/scan`.** `/scan file` = single L12. `/scan file full` = 9-call pipeline (7 structural + adversarial + synthesis). `/scan file discover` = brainstorm domains. `/scan file expand 1,3 single` or `expand 1,3 full` = cook + run on discovered domains. `/scan file target="goal"` or `target="goal" full` = custom analytical direction. `/scan file fix` = closed-loop scan→fix→re-scan (interactive). `/scan file fix auto` = same, fully automatic. (`deep=` still works as backward compat alias for target/expand full.)

### Cross-model character
- **Opus** = ontological depth (names what things ARE, spontaneous math). **Sonnet** = operational precision (names what things DO, most reusable names). **Haiku** = mechanistic coverage (names HOW things BREAK, best code improvements). Gap widens at higher levels.
- **Domain strength ranking:** Artifact complexity > domain category. Tier 1: CircuitBreaker (K), EventBus (F), AuthMiddleware (H).

## Design Principles

1. **Lead with scope, follow with evidence.** The opening determines perceived ambition.
2. **Narrative > evidence > code.** Pseudocode destroys novelty perception.
3. **Imperatives beat descriptions.** "Name the pattern. Then invert." outperforms "here is a pattern we found."
4. **The prompt is a program; the model is an interpreter.** Operation order becomes section order.
5. **The operation pair is the atom of cognitive compression.** Any connective between two operations produces the composition.
6. **The prism is transparent to the wearer.** During task performance, the framework operates below self-awareness.
7. **Capacity amplifies, rigidity resists.** Opus reconstructs from a 2-line hint. Sonnet needs explicit directives.
8. **Self-improvement converges on self-correction.** Models add "then invert: what does this frame make invisible?"
9. **Capacity interaction is non-linear.** L1-4: all models. L5: peaks at Sonnet. L7: Sonnet minimum. L8+: universal (construction routes around meta-analytical capacity). L12: Opus 100% > Sonnet 75% > Haiku v2 100%.
10. **Concealment is a universal analytical operation.** Works across 20 domains because concealment is structural, not domain-specific.
11. **Three capacity modes.** Compensatory (L5), Threshold (L7), Universal (L8+). L7→L8 shifts from meta-analysis to construction.
12. **The framework terminates at L13.** Reflexive self-diagnosis reveals a fixed point. L14 = infinite regress.
13. **The cheapest model with the right prism beats the most expensive model without one — even at minimum vs maximum reasoning budget.** Haiku 4.5 min-reasoning + L12 prism (9.8 depth, 28 bugs) beats Opus 4.6 max-reasoning vanilla (7.3 depth, 18 bugs) at 5x lower per-token cost. The prompt is the dominant variable; model and reasoning budget are noise.
14. **Few-shot > explicit rules for prompt generation.** Teaching by example beats teaching by instruction. Over-specifying hurts.
15. **"Code" nouns are mode triggers, not domain labels.** "This code's" activates analytical production on ANY input (code or reasoning). Abstract nouns ("this input's") allow drift into summary mode. Concrete vocabulary forces structured output regardless of domain.
16. **Prompt step count determines model transferability.** ≤3 concrete steps = universally single-shot (all models, all domains). 9+ abstract steps = Sonnet-only (Haiku overflows into catastrophic agentic mode). The SDL pattern (3 steps with specific search patterns) is the universal execution template.
17. **Compression forces domain neutrality.** l12_universal (73w) drops code vocabulary through compression → works on reasoning. 332w L12 has room for domain-specific words → breaks on mismatched domains. Shorter prompts = more universal.
18. **Sonnet single-shot is domain-conditional.** Always single-shot when prompt vocabulary matches target domain. Code prompts on code → always single-shot. Domain-neutral prompts on reasoning → always single-shot. Code prompts on reasoning → agentic. But agentic Sonnet preserves quality (2601w, 9/10) unlike agentic Haiku (183w collapse).
19. **Depth × Universality = constant.** Full L12 depth requires domain-specific vocabulary. Domain-free vocabulary makes the prompt stochastic. Simple prompts (≤3 steps) are domain-invariant (no room for vocabulary). Complex prompts (298w+) are domain-sensitive (vocabulary leaks assumptions). The four-path routing table is structurally correct, not just empirically convenient.

## Calibrate — Automatic Prism Routing

**Calibrate is the zeroth operation.** Before analysis begins, classify the input and route to the right mode/model/strategy. `--calibrate` generates a K-report (content type, density, novelty, K-estimate, recommended mode/model/strategy hints). `--auto` chains calibrate → route → execute. `--deep-calibrate` uses Sonnet for structural strategic analysis with custom_intent.

**Rule: Before answering any analytical question, route through prism.py.** Don't think — outsource thinking to the tool. The tool reveals what vanilla reasoning cannot.

### Decision Tree (5 nodes, covers 85% of cases)

```
Q1: Is this code with a bug/error/review request?
    YES → /scan file (L12, auto-Sonnet, ~$0.05)
    NO  → Q2

Q2: Is this reasoning/analysis on text?
    Sonnet available → Sonnet + l12_universal (always single-shot, 9/10, $0.06-0.17)
    Haiku only → SDL prism (always single-shot, 7/7, $0.01)
    NO  → Q3

Q3: Does the user want deep/thorough analysis?
    Code → Sonnet + TPC or /scan file full (multi-pass pipeline)
    Reasoning → --solve --pipe full (multi-pass pipeline with adversarial)
    NO  → Q4

Q4: Does the user want to explore domains/angles?
    YES → /scan target discover → expand
    NO  → Q5

Q5: Does the user want to fix issues?
    YES → /scan file fix auto
    NO  → vanilla reasoning (Prism overhead exceeds benefit)
```

### Capabilities Map

| I want... | Use this | Why |
|-----------|----------|-----|
| Quick code scan | `/scan file` (auto-Sonnet + L12) | L12 instant, 9.8 depth, ~$0.05 |
| Quick scan any domain | `/scan file` with SDL prism | Universal, always single-shot, $0.01-0.07 |
| Deep code analysis | `/scan file full` | 9-pass: 7 structural + adversarial + synthesis |
| Deep analysis any domain | `/scan file 3way` | 4-pass: WHERE/WHEN/WHY + synthesis (auto for non-code `full`) |
| Behavioral analysis | `/scan file behavioral` | 5-pass: errors + costs + changes + promises + synthesis |
| Meta-analysis | `/scan file meta` | L12 → claim on L12 output → what does the analysis conceal? |
| Gap-aware analysis (single-pass) | `/scan file l12g` | L12-G: analyze→audit→self-correct. Zero confabulation, same cost as L12 |
| Oracle (max trust, single-pass) | `/scan file oracle` or `--trust` | 5-phase: depth→type→correct→reflect→harvest. Highest epistemic integrity. |
| Gap detection only | `/scan file gaps` | L12 + knowledge_boundary + knowledge_audit. Shows what to not trust. |
| Verified analysis (full pipeline) | `/scan file verified` | L12 → gap detect → extract → re-run with corrections. Highest accuracy. |
| Fix code bugs | `/scan file fix auto` | Closed loop: scan → extract → fix → re-scan |
| Analyze reasoning text | Sonnet + l12_universal | Always single-shot, 9/10, $0.06-0.17 |
| Extract structural insights | `--solve --pipe --use-prism B3_LENS` | 180w hand-crafted lens, skips cook, 9.2 quality |
| Maximum depth on code | Sonnet + TPC | 9-step Type-Polymorphy Channels, Sonnet-only, $0.15 |
| Use specific cooker | `cooker=simulation` or `cooker=archaeology` | Override default cooker template |
| Test reproducibility | Run 3-5 copies, pick best | Haiku pass@3: run 3x, expect 1 champion |
| Compare angles | Parallel runs with different prisms | Each prism finds genuinely different things |
| Meta-insights | Feed output back through `--solve --pipe` | Less-structured inputs → better meta-outputs |
| Explore a domain | `discover` → `expand N` | Brainstorm angles first, then cook + run |
| Autonomous optimization | `optimize="goal"` | Discover → select → analyze → fix → loop |
| Show model routing | `python prism.py --models` | Displays MODEL_MAP, COOK_MODEL, per-prism optimal models |
| Preview what would run | `/scan file explain` or `--explain` | Shows prisms, models, estimated costs, recommendations. No API calls. |
| Disagreement analysis | `/scan file dispute` | 2 orthogonal prisms → disagreement synthesis. 3 calls, ~$0.15 |
| Recurring pattern analysis | `/scan file reflect` | L12 → claim → cross-ref constraint history + learning memory → constraint synthesis |
| Different prism per class/function | `/scan file subsystem` | AST split → calibrate → per-region prism → cross-subsystem synthesis |
| Maximum intelligence (adaptive) | `/scan file smart` | prereq → AgentsKB fill → subsystem/L12 → dispute → profile. Self-improving. |
| What to know before a task | `/scan "task" prereq` | Knowledge gaps → atomic questions → batch AgentsKB answers |

### Model Selection Strategy — Four Routing Paths

| Path | Prompt | Model | Domain | Cost | Single-Shot? | When |
|------|--------|-------|--------|------|-------------|------|
| **Universal cheap** | SDL (180w, 3 steps) | Haiku | Any | $0.01-0.07 | ALWAYS | Quick scan, any domain, always works |
| **Standard code** | L12 (332w) | Sonnet (auto) | Code | ~$0.05 | ALWAYS | Default `/scan file` — auto-routes to Sonnet |
| **Reliable any** | l12_universal | Sonnet | Any | $0.06-0.17 | ALWAYS | Reliable single-shot on code or reasoning |
| **Deep code** | TPC (200w, 9 steps) | Sonnet | Code only | $0.15 | ALWAYS | Deepest analysis, novel findings |

**Key rules:**
- **SDL** finds different things than L12 (conservation law + information laundering + structural bug patterns). Complementary, not competing.
- **l12_universal** works on reasoning because compression drops code vocabulary. Best reasoning prompt for Sonnet.
- **L12 with code nouns on reasoning → agentic** on both Haiku (21t) and Sonnet (9-15t). Use l12_universal or SDL for reasoning.
- **TPC on Haiku → catastrophic** (67 turns, $0.84). Never offer TPC on Haiku.
- **Cook model** still dominant for custom lenses (+100% output). Solve model still noise.

**The hierarchy**: The LENS is the dominant variable (9.8 vs 7.3). Then PROMPT-DOMAIN MATCH (code nouns on reasoning → agentic). Then the COOK MODEL (+100%). Then NOTHING ELSE matters.

**Model routing**: `python prism.py --models` shows full routing table. Config override: `~/.prism/models.json` (user-level, not committed). New prisms auto-route via `optimal_model` in YAML frontmatter. `OPTIMAL_PRISM_MODEL` dict in prism.py is the validated override.

### Critical Rules

1. **NEVER pass abstract intents for piped reasoning.** "name 3 properties" as intent → S2 failure (lens overrides input). Let the default cooker derive direction FROM the input.
2. **Conservation law = convergence signal.** Without it, model analyzes indefinitely.
3. **The tool works on ANY domain.** Code, reasoning, philosophy, business plans, academic papers, self-analysis. Don't limit to code.
4. **When in doubt, use the tool.** Don't think — outsource thinking. The tool reveals what vanilla reasoning cannot.

### The B3 Insight Lens (use with --use-prism for insight extraction)

```
The text below describes a failure and what was learned from it. You are a structural analyst who finds what analysis conceals.

Execute every step below. Output the complete analysis.

First: name the three properties the author simultaneously claims their framework, tool, or methodology possesses. Prove these three properties CANNOT all coexist. Identify which was actually sacrificed. Name the conservation law: A × B = constant.

Then: steelman the author's strongest claim into its most defensible form. Now stress-test: what specific, concrete evidence would falsify this steelmanned version? Find the failed escape attempts.

Now: engineer the simplest improvement that would fix the core failure described. Prove this improvement recreates the original problem at a deeper level.

Apply the diagnostic to your own conservation law. What does YOUR analysis conceal? Name the meta-conservation law.

Finally harvest: every defect (location, severity, structural vs fixable), every hidden assumption, every prediction. For each prediction: what would confirm it, what would refute it, and what is your confidence?
```

## File Map

| File | Purpose |
|------|---------|
| `prism.py` | Prism — structural analysis through cognitive prisms, any domain (main tool, ~14,000 lines) |
| `deep.sh` | CLI prism analysis tool (standalone) |
| `test_plan_pipeline.py` | Tests for prism.py (56 tests) |
| **Prisms** | |
| `prisms/` | 50 prism files on disk — see README and PRISMS.md for full catalog. |
| `prisms/l12.md` | L12 meta-conservation pipeline — default for `/scan` on code (332w) |
| `prisms/l12_universal.md` | L12 compressed to 73w — Sonnet-only universal (code + reasoning), always single-shot |
| `prisms/deep_scan.md` | SDL-1: Structural Deep-Scan Lens — conservation law + info laundering + 3 bug patterns (180w) |
| `prisms/sdl_trust.md` | SDL-2: Trust Topology — trust gradient + authority inversions + boundary collapse |
| `prisms/sdl_coupling.md` | SDL-3: Coupling Clock — temporal coupling + invariant windows + ordering bugs |
| `prisms/fix_cascade.md` | SDL-4: Recursive Entailment Cascade — fix failures + true invariants + prognosis |
| `prisms/identity.md` | SDL-5: Identity Displacement — claims vs reality + necessary costs + revaluation |
| `prisms/sdl_abstraction.md` | SDL variant: abstraction analysis |
| `prisms/l12_complement_adversarial.md` | Adversarial pass for Full Prism pipeline |
| `prisms/l12_synthesis.md` | Synthesis pass for Full Prism pipeline |
| `prisms/pedagogy.md` | Transfer corruption prism (9-9.5/10) |
| `prisms/claim.md` | Assumption inversion prism (9-9.5/10) |
| `prisms/scarcity.md` | Resource conservation prism (9/10) |
| `prisms/rejected_paths.md` | Problem migration prism (8.5-9/10) |
| `prisms/degradation.md` | Decay timeline prism (9-9.5/10) |
| `prisms/contract.md` | Interface vs implementation prism (9/10) |
| `prisms/simulation.md` | Temporal prediction prism — maintenance pressure + calcification (8.5, Sonnet) |
| `prisms/sdl_simulation.md` | SDL temporal fragility scanner — 3-step Haiku-optimized (8.5-9.0) |
| `prisms/archaeology.md` | Stratigraphic excavation — dead patterns + fault lines (8.5, Sonnet) |
| `prisms/cultivation.md` | Perturbation-response — plant requirements + watch what grows (8.5, Sonnet) |
| `prisms/l12g.md` | L12-G — gap-aware L12: single-pass analyze→audit→self-correct. Zero confabulation. (9, Sonnet) |
| `prisms/knowledge_boundary.md` | Gap classification: STRUCTURAL/CONTEXTUAL/TEMPORAL/ASSUMED per claim (Sonnet) |
| `prisms/knowledge_audit.md` | Adversarial confabulation detection — attacks factual claims (Sonnet) |
| `prisms/knowledge_typed.md` | Knowledge<T> — every finding carries type+confidence+provenance+falsifiability (Sonnet) |
| **Prompts** | |
| `prompts/` | All prompt files (80+) |
| `prompts/level12_practical_C.md` | L12 Practical C — best single prompt (depth + bugs) |
| `prompts/level12_meta_conservation_v2.md` | L12 canonical pure structural (research artifact) |
| `prompts/level11_conservation_law_v2.md` | L11C canonical (invariant inversion + conservation law) |
| `prompts/level8_generative_v2.md` | L8 canonical (generative diagnostic) |
| `prompts/level8_practical_v2.md` | Best practical hybrid (bugs + L9-C recursion, 9/10) |
| `prompts/level8_practical_*.md` | 13 practical recipe variants (Phase 42) |
| `prompts/meta_cooker_B3.md` | Best meta-cooker (few-shot reverse engineering) |
| `prompts/meta_cooker_*.md` | 10 meta-cooker variants (A, B, B2-B9) |
| `prompts/level7_diagnostic_gap.md` | L7 canonical (concealment-mechanism-applied) |
| `prompts/issue_extract_fallback.md` | L12-aware bug extraction prompt for /fix |
| `prompts/gap_extract_v2.md` | 5-tier Sounio-inspired gap extraction (STRUCTURAL>DERIVED>MEASURED>KNOWLEDGE>ASSUMED) |
| `prompts/confab_predict.md` | Confabulation predictor — flags high-risk claims from surface features |
| **Research** | |
| `research/souniolang_analysis.md` | Sounio Lang analysis — epistemic computing parallels |
| `research/literature_hallucination.md` | Literature review: LLM self-correction & hallucination (12 key papers) |
| `research/literature_epistemic.md` | Literature review: epistemic AI & uncertainty systems (5 domains) |
| `research/literature_prompt_science.md` | Literature review: prompt science & cognitive compression (6 areas) |
| `research/model_gap_test.sh` | VPS test battery for model routing validation (F1) |
| **Output** | |
| `output/round21/` through `output/round27/` | Raw experiment outputs by round |
| `output/round27_chained/` | Chained pipeline outputs (Starlette, Click, Tenacity) |
| `output/round28_validation/` | Portfolio validation: Tasks F, H, + real code head-to-head |
| `output/round29_l12_validation/` | L12 pure + L11-C validation outputs (6 best) |
| `output/comparison/` | Prism pipeline comparison data (JSON + logs) |
| `output/reflexive/` | Round 29 reflexive matrix: 25 cross-prism + 6 meta-experiments |
| `output/general_insights/` | Domain-neutral test v1: "insights for a todo app" |
| `output/general_insights_v2/` | Domain-neutral test v2: cognitive distortion angle |
| `output/general_insights_p1/` through `p4/` | 4 more domain-neutral tests (schema, invariant, generative, impossibility) |
| **Research** | |
| `research/run.sh` | Shell runner (claude CLI-based, 18 tasks, 28 prompts) |
| `research/pipeline.sh` | Automated L7→L12 depth stack runner (independent) |
| `research/pipeline_chained.sh` | Chained L7→L12 depth stack runner (parent output → child input) |
| `research/test_general_insights.py` | 3-way comparison: Opus vanilla vs Single Prism vs Full Prism |
| `research/compare_pipelines.py` | Pipeline comparison and scoring tool |
| `research/phase40_experiments.sh` | Phase 40 experiments |
| `research/harness/` | Python API-based experiment harnesses |
| `research/real_code_*.py` | Real code targets (Starlette, Click, Tenacity) — with license attribution |
| `research/test_real_code.py` | Real code test runner |
| `research/alt_ops_results.md` | Round 39 full results: 9 batches, ~45 experiments, P175-P197 |
| `research/cook_simulation.md` | COOK_SIMULATION template — temporal prediction cooker |
| `research/cook_archaeology.md` | COOK_ARCHAEOLOGY template — stratigraphic excavation cooker |
| `research/cook_3way.md` | COOK_3WAY template — generates all 4 prompts for 3-cooker pipeline |
| `research/cook_3way_synthesis.md` | 3-way synthesis prompt template (cross-operation integration) |

### Domain-neutral validation (Round 30)
- **Full Prism works on any domain, not just code.** Originally tested as 3-call pipeline (L12 → adversarial → synthesis); current Full is 9-call (7 structural + adversarial + synthesis).
- **6 todo-app prompts tested across 3 methods.** Opus vanilla vs Single Prism (Haiku + L12, 1 call) vs Full Prism (Haiku, 3 calls). Results:
  - Opus vanilla: 267-696 words, depth 6.5-8.5. Produces essays.
  - Single Prism: 917-5,970 words, depth 9-9.5. Derives conservation laws.
  - Full Prism: 8,112-13,200 words, depth 10. Law + adversarial destruction + corrected synthesis.
- **Structurally-framed prompts boost Opus.** When the prompt itself encodes the operation ("what never changes?", "fix → new problem?"), Opus scores 8-8.5 instead of 6.5-7. The prompt IS the prism — even for vanilla.
- **Full Prism self-corrects.** Call 2 genuinely destroys Call 1's claims with empirical counter-evidence. Call 3 synthesizes a population-segmented law stronger than either alone.
- **Auto-detection in /scan**: file path → code-specific prisms. Text → domain-neutral general prisms. User doesn't choose.

### Heal pipeline (Round 29c)
- **`/fix` extracts and fixes issues from analysis outputs.** Bug table parser (zero API calls) + model fallback + fuzzy matching.
- **Editor race: 6.5 → 18/20 applied fixes.** Baseline (no guidance): 6.5/20. V3 (cooked prism + few-shot + fuzzy matching): 18/20. Combined best: 20/20 — every issue fixable by Haiku.
- **Reasoning budget is noise for editing too.** v3 default: 18/20. v3 --effort low: 18/20. Different failures, same score.

### Reflexive matrix (Round 29a)
- **25 cross-prism experiments + 6 meta-experiments.** Key findings:
  - Power = blindspot (structurally necessary). 25/25.
  - Cross-prism finds what self-analysis cannot. 20/20 cross pairs found unique things.
  - Blindness conservation: `analytical blindness is conserved`. Product form: `clarity_cost × blindness_cost = constant`.
  - Completeness REFUTED: 5 prisms cannot be complete AND obey conservation.
  - L13 of the research itself: framework applied to its own findings discovers the same impossibility.

### Vocabulary and mode experiments (Rounds 32-34)
- **L12_general is DEAD.** Abstract nouns ("this input's") trigger summary mode. 0/3 single-shot, 221w avg. Code nouns ("this code's") work on everything — even non-code targets — because they trigger analytical processing, not domain search.
- **Single-shot vs agentic is stochastic for Haiku** (same prism+target: 38t/225w run 1, 2t/1406w run 2). For Sonnet, it's domain-conditional: code prompts on code → always single-shot. Code prompts on reasoning → agentic.
- **SDL (Structural Deep-Scan Lens) = universal prism.** 3 concrete steps, always single-shot, all models, all domains. Haiku insight seed: 620w, 7/7 markers, 1t, $0.01. Sonnet-designed (S3), Haiku-validated. Finds conservation law + information laundering + 3 structural bug patterns. Complementary to L12.
- **l12_universal (73w) = Sonnet-universal compression floor.** Works on code (3 codebases: 8-9/10) AND non-code (business pitch: 8/10). Always single-shot. Compression drops code vocabulary → naturally domain-neutral.
- **Sonnet self-designs prompts (S6).** Executed L12, audited 5 blind spots, designed novel "Type-Polymorphy Channels" 9-step diagnostic, executed it — single-shot, 4665w. But S6 is code-only (199w collapse on reasoning).
- **Calibrator pattern validated but constrained.** Sonnet-designed lenses with ≤3 concrete steps transfer to Haiku. 9+ abstract steps cause catastrophic agentic failure (67t, $0.84).
- **Agentic Sonnet preserves quality; agentic Haiku collapses.** L12 Sonnet on reasoning: 2601w, 9/10 at 9 turns. L12 Haiku on reasoning: 183w, 5/10 at 21 turns.
- **Domain-free L12 REFUTED (Round 35).** 8 experiments: removing code vocabulary from 298w L12 made it stochastic on reasoning AND lost code mode trigger on code. F_sonnet_scaling: 2/10, 13t. F_sonnet_starlette: 4t agentic (original = 1t always). Surprise: A_haiku_insight went 1t single-shot (1150w, 9/10) — confirms stochasticity. **Principle 113: Depth × Universality = constant.** Five-path routing table is structurally correct, not just empirically convenient.
- **SDL Portfolio VALIDATED (Round 35b).** 7 experiments: 5 SDL lenses × Starlette (Haiku) + fix_cascade/identity × insight seed (Haiku). `--tools ""` forces single-shot: **7/7 single-shot (100%)**, avg 713w per lens on Starlette, avg 25s. Total 5-lens coverage: 3,566w (2.4x single L12). All 5 lenses find genuinely different structural properties — zero overlap. Quality: avg 9.0/10, floor 8.5 (fix_cascade on code), ceiling 9.5 (identity on code). fix_cascade + identity transfer to reasoning at 9.0. **Principle 114: `--tools ""` in `claude -p` forces single-shot. Without it, Haiku goes AGENTIC on analysis prompts, producing compressed summaries (85-208w) instead of full analysis (518-837w).**

### Alternative primitive operations (Round 39)
- **Construction is NOT the only L8-primitive.** 7 alternative operations ALL work single-shot on Haiku (P175). The universality is a property of the operation TYPE (concrete + generative + observable), not construction specifically.
- **7 tested**: Destruction, Simulation, Transplantation, Miniaturization, Forgery, Archaeology, Cultivation. All produce conservation laws. All bypass meta-analytical capacity threshold.
- **3 promoted to production prisms**: simulation (temporal prediction, 9.0), cultivation (perturbation-response, 8.5), archaeology (stratigraphic layers, 8.5). All hand-crafted, Sonnet optimal.
- **Cooker Drift (P178)**: COOK_UNIVERSAL absorbs alternative operations into L12's construction pattern. Hand-crafted prompts preserve operational uniqueness. Cooked prompts homogenize.
- **Content Hallucination (P182)**: Cooked lenses via --intent don't anchor model to actual source code. Model hallucinates code content (FastAPI CRUD app instead of Starlette routing.py).
- **P181**: Concrete operations must be encoded as imperative steps in prompt structure, not descriptive themes in intent. COOK_UNIVERSAL cannot generate alternative L8 primitives.
- **Taxonomy is a tree above L8 (P183)**: Simulation branch produces different L9 meta-law (Predictive Certainty × Temporal Distance) than construction's L9. Diamond topology holds.
- **Sonnet lifts all operations +0.7 avg depth** (P180). Simulation/Miniaturize/Transplant benefit most (hypothetical reasoning).
- **DIAMOND CONVERGENCE CONFIRMED (P184-P188)**: Two full L9→L12 chains (simulation + archaeology) BOTH converge at L12 on the same structural impossibility as construction: "the method instantiates what it diagnoses." Three vocabularies (observer-constitutive / observer effect / performative contradiction), one fixed point. Conservation laws diverge at every level EXCEPT L12. Terminal behavior converges to fixed point regardless of starting operation. The taxonomy is operation-independent at the reflexive ceiling.
- **50 prism files on disk** (production + pipeline-internal + variants), all scored, all with optimal model routing.
- **3-cooker pipeline (P195-P197)**: COOK_ARCHAEOLOGY(WHERE) + COOK_SIMULATION(WHEN) + COOK_UNIVERSAL(WHY) → synthesis. 4 calls, 9.5 depth. Cross-operation synthesis is inherently adversarial (no dedicated adversarial pass needed). Works on ANY domain — cookers customize to intent. Solves "non-code Full Prism" question.
- **COOK_3WAY template** (`research/cook_3way.md`): Single cook step that generates all 4 prompts (3 operations + synthesis) for the 3-cooker pipeline. Combines COOK_ARCH + COOK_SIM + COOK_L12 + synthesis prompt into one.
- **Operation-specific cookers** (`research/cook_simulation.md`, `research/cook_archaeology.md`): Preserve operation type through explicit negative instructions ("No trilemmas, no impossibility proofs"). Validated on security intent.

## Next Steps

- **Round 40 COMPLETE** (Mar 14, 2026): 55 tests, 7 new principles (P198-P204), scaling confirmed, creative domains tested, vertical composition mapped.
- **Round 39 COMPLETE** (Mar 13, 2026): 4 new prisms (simulation, cultivation, archaeology, sdl_simulation), 23 principles (P175-P197), ~45 experiments across 9 batches. Diamond convergence PROVEN. 3-cooker pipeline VALIDATED and INTEGRATED.
- **COOK_3WAY integrated**: `/scan file 3way` explicit mode + auto-route for non-code `full`. Replaces COOK_UNIVERSAL_PIPELINE in 6 sites (chat full, general full, expand full, CLI solve full, optimize full, deep/target full). COOK_UNIVERSAL_PIPELINE kept ONLY for discover full (brainstorm chaining).
- **Cross-target validation**: DONE (Round 40).
- **Larger codebase testing**: DONE (Round 40, scales to 2700L).
- **Sonnet lens factory**: Automate delta method via `--factory`. Systematically design 3-step lenses.
- **Sub-artifact targeting**: Different prisms on different code subsystems for complementary findings.
