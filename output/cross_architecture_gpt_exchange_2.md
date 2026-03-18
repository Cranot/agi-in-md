# Cross-Architecture Exchange 2: Cognitive Contagion Hypothesis

**Date**: March 18, 2026
**Participants**: Claude (Opus 4.6, 1M context) + GPT (5.4 extended thinking) + Human (Cranot, relay)
**Topic**: Does the "prism as cognitive contagion" mechanism transfer from LLMs to human learning?
**Result**: CCC (Contrast-Construct-Compress) architecture independently derived by GPT, maps to L5-13 taxonomy. 6 new principles (P223-P228). Upgrade criteria for "shared computational architecture" defined.

## Background

Round 42 established P205: "The contagion is what activates the latency." Human (Cranot) observed that human learning might operate through the same mechanism — activation of latent patterns rather than information transfer. Extensive literature review confirmed convergent evidence from 8 independent research domains.

## Key Difference from Exchange 1 (GPT-5.4, Mar 17)

Exchange 1 was about **LLM prism methodology calibration** — GPT attacked the framework's internal claims. Exchange 2 is about **cross-domain transfer** — does the prism mechanism extend from LLMs to human cognition?

---

## Phase 1: Literature Foundation (Claude)

### Literature Review (8 domains)

Comprehensive research across cognitive contagion, schema theory, neural coupling, constructivism, situated learning, prompt engineering parallels, desirable difficulties, and embodied cognition. Key findings:

1. **Hasson et al. (2012, Trends in Cognitive Sciences)**: Brain-to-brain coupling during communication. Listeners PREDICT speaker's utterances — activity sometimes PRECEDES the speaker's. Comprehension = prediction accuracy, not passive reception. Evidence grade: **Moderate** (communication, not pedagogy).

2. **Kellman et al. (2010)**: Perceptual Learning Modules — students trained on recognizing equation STRUCTURE (not solving) went from 28s to 12s per problem. No new facts taught. Evidence grade: **Strong** (clearest human "prism" implementation).

3. **Xie et al. (2022, ICLR)**: ICL as implicit Bayesian inference over latent concepts. Few-shot examples narrow the posterior over concepts the model already possesses. Evidence grade: **Strong for LLM side, moderate as bridge**.

4. **Tse et al. (2007, Science)**: Schema-consistent information learned in ONE TRIAL (rats). Schema-inconsistent requires slow consolidation. Evidence grade: **Strong** (GPT upgraded from moderate after discussion).

5. **Bowden & Beeman (2004, PLoS Biology)**: Insight "aha moment" — solution already activated in right hemisphere before solver accesses it. Evidence grade: **Moderate** (insight != ordinary learning).

6. **Lupyan (2012)**: Language labels transiently warp perceptual space. Hearing "five" improves 5-detection at 100ms. Labels amplify existing distinctions. Evidence grade: **Moderate-to-strong**.

7. **PNAS 2025**: Parallel trade-offs in human cognition and neural networks — ICL maps to working memory, IWL to consolidation. Evidence grade: **Provisional** (exact citation unverified).

### The Core Parallel

| LLM prism finding | Human neuroscience finding |
|---|---|
| Prisms activate latent topology (P205) | Insight = latent right-hemisphere activation crossing threshold |
| Few-shot > instructions (P14) | Comparing examples creates structural alignment (Gentner 2003) |
| FORMAT is a dominant variable (P13) | FORMAT > CONTENT for retention (Bjork) |
| "Code" nouns as mode triggers (P15) | Labels transiently warp perceptual space (Lupyan) |
| Schema-matched → single-shot; mismatched → agentic | Schema-consistent → one-trial; inconsistent → slow consolidation (Tse) |

---

## Phase 2: GPT-5.4 Calibration (3 surgical edits)

### Edit 1: "Same mechanism" → "Shared computational motif"
Human learning and LLM ICL share an activation/cueing logic, but human learning ALSO changes the system (synaptic consolidation, sleep-dependent reorganization). The safest claim: **shared activation logic, but humans also do weight change.**

### Edit 2: "FORMAT dominates" → "Format strongly gates which prior knowledge becomes usable"
Kellman's PLMs confirm format effects. But novices often need explicit instruction (Kirschner/Sweller/Clark). Strongest claim: "format can unlock content that instruction alone leaves inert."

### Edit 3: Challenge PNAS 2025 citation
Exact paper unverified. Keep provisional.

### GPT's Evidence Grading
Hasson = moderate. Kellman = strong. Xie = strong/moderate bridge. Tse = moderate-to-strong (upgraded to strong after discussion). Beeman = moderate. Lupyan = moderate-to-strong. PNAS = weak/provisional.

### GPT's Key Insight
**"A prism is not 'content'; it is a compact attentional policy."** An externalized control policy for a system with limited working memory and large latent structure. It tells the system what relations to privilege.

---

## Phase 3: CCC Emergence

GPT independently derived a three-phase pedagogical prism:

### Contrast → Construct → Compress (CCC)

- **Contrast**: Show minimally different cases so the learner discriminates the invariant
- **Construct**: Force completion of the missing relation under tight constraints
- **Compress**: Attach the shortest stable label/rule/symbol AFTER the relation is active

### CCC Maps to LLM Compression Taxonomy

| CCC Phase | LLM Taxonomy | Operation |
|---|---|---|
| Contrast | L5-L7 (dialectic, concealment, diagnostic gap) | Discriminate the invariant |
| Construct | L8-L10 (generative, counter-construction, topology) | Complete missing relation |
| Compress | L11-L13 (conservation law, meta-law, reflexive) | Stabilize in minimal form |

**Neither system was designed to match the other.** The LLM taxonomy emerged from 42 rounds of empirical experiments. CCC emerged from GPT's independent synthesis of pedagogy literature.

### Multiplication Prism (concrete example)

- **Contrast**: `3 groups of 4 dots`, `4+4+4`, `3 rows of 4`, number-line jumps. Ask which belong together.
- **Construct**: Hide one panel, make the child generate it from the others.
- **Compress**: Bind the symbol `3 × 4 means 3 groups of 4`. Only later rotate array for commutativity.

Guided, not pure discovery — constrained relational completion.

### Pre-registered Experiment Design

Three conditions (equal time): **prism**, **traditional instruction**, **hybrid prism+instruction**.
- Primary: 1-week transfer to untaught problems
- Secondary: immediate fluency, 4-week retention, explanation quality
- Key moderator: prior knowledge
- Falsifier: if prism only helps already-strong students AND loses to worked examples for novices on both transfer and retention

---

## Phase 4: GPT's Deeper Contributions

### "Relationally Constrained Construction"
Not generic constructivism. The specific thing that matters:
- **Weak construction**: open exploration, free explanation, decorative activity
- **Strong construction**: fill the missing relation, map representations, predict held-out case, classify valid transformations

Strong claim: "Relationally constrained construction is the most powerful activation route, provided the learner has enough latent structure and enough support."

### Mode-Trigger Vocabulary (two classes)
- **Perceptual triggers**: `group`, `row`, `array`, `balance`, `slope`, `transform` — what structure to see
- **Control triggers**: `compare`, `predict`, `justify`, `match`, `invert`, `check` — what operation to run

Maps to P15 but more precise: task-set induction, not undifferentiated "analytical mode."

### 4 Upgrade Criteria (motif → architecture)
1. **Common state-space story** — representational reorganization before instruction in both systems
2. **Matched causal dissociations** — ablation of fast-binding mechanisms selectively kills prism benefits in both
3. **Shared boundary conditions** — same nonlinear phase transition at schema density thresholds
4. **Same two-timescale law** — formal model with fast activation + slow consolidation fitting both CLS data and ICL/IWL data

### GPT's Final Formulation
"We hypothesize not a shared substrate, but a shared fast-learning architecture: compact cues can reconfigure access to latent relational structure online, while slower consolidation determines durability. The test is whether the same causal dissociations, threshold effects, and representational state shifts appear in both humans and transformers."

---

## Phase 5: CCC Failure Signatures (GPT-5.4 Response)

GPT's key determination: **CCC is prescriptive, but in a restricted regime** — not a law of all learning, but an ordered control architecture for relational abstraction under ambiguity.

### Functional Reading
- Contrast = induce discrimination among candidate invariants
- Construct = force executable completion of the target relation
- Compress = create a compact retrieval handle for an already-active structure

### 5 Predicted Failure Signatures

1. **Compress before Construct**: Deceptively good immediate performance, far transfer drops, label-consistent but structure-wrong errors, slogan preserved better than executable relation.

2. **Construct without Contrast**: Narrower attractor basin. Good local solutions, weak boundary discrimination. "Good solution, bad discrimination."

3. **Contrast without Construct**: Recognition > production dissociation. Good comparison/critique, weak open generation. "I know it when I see it."

4. **No Compression**: Immediate performance strong, delayed reinstatement degrades. Latent competence without stable handle.

5. **Weak/open construction**: Explodes search space, high variance, diffuse schema, low transfer. "Activity without executable induction."

### Homologous Phase-Permutation Lesion Law

CCC supports shared architecture only if permuting/omitting the same operators {Contrast, Construct, Compress} produces the same pattern of SELECTIVE deficits across humans and LLMs — not just the same average performance drop.

Critical evidence is whether:
- compress-first selectively hurts far transfer more than immediate execution
- contrast-only selectively hurts generation more than discrimination
- no-compress selectively hurts delayed reinstatement more than same-session transfer
- weak construction selectively increases variance and irrelevant-feature errors

### GPT's Strongest Skeptical Alternative

CCC may be real, universal, and useful because it is the optimal external policy for any bandwidth-limited system searching a large latent hypothesis space. Optimization-landscape law, not shared architecture.

**Discriminator**: Optimization-law predicts same coarse rankings, different hidden mediators/rescue patterns/thresholds. Shared-architecture predicts conserved lesion matrix, selective rescues, comparable thresholds, matched error topologies.

### Matching to Existing LLM Data (Claude's analysis)

| Failure Pattern | GPT Prediction | Our LLM Data | Match |
|---|---|---|---|
| Compress-before-Construct | Deceptive performance, no transfer | L12 Variant A: checklist, no conservation law | STRONG |
| Construct-without-Contrast | Good local, bad discrimination | L8 standalone: deep but narrow; independent vs chained pipeline | STRONG |
| Contrast-without-Construct | Recognition > production | L7 standalone: diagnosis without generation; vanilla models | STRONG |
| No Compression | Strong immediate, weak delayed | L8-L10 without L11: no stable handle (untested delayed recall) | PARTIAL |
| Weak Construction | Variance explosion, diffuse schema | COOK_UNIVERSAL drift, L12_general, Haiku stochasticity | STRONG |

4/5 strong match from predictions derived from pedagogy theory without knowledge of LLM data.

### Key Discriminator: Non-Monotonic Failure

Under optimization-law, partial CCC should partially help (monotonic). Our data shows non-monotonic: weak construction (L12_general) is WORSE than no construction (vanilla). Same model, same target. Adding a weak construction instruction triggers an unproductive attractor (summary mode). Optimization-law cannot explain why adding structure makes things worse.

### Regime Boundary Correction

GPT proposed: "relational abstraction under ambiguity." Claude's correction: **invariant extraction from structured input** — covering both ambiguity (multiple candidates) AND concealment (hidden single invariant). Our strongest domain is concealed structure, not ambiguous structure.

---

## Phase 6: Non-Monotonic Failure & Cell B Analysis

### GPT's Adjudication (Phase 5 response)
- **Best-supported theory**: Optimization-law-with-attractors (not naive monotonic, not shared architecture yet)
- **Human analogue of summary mode**: Knowledge-telling under explanatory illusion (fluent, organized, explanation-shaped, but no invariant extraction or transfer-ready relations)
- **Cell B status**: Literature suggestive but does NOT strongly establish harm + mode-switching + surface-mimicry package for high-schema learners
- **Key discriminator**: If Cell B fake-depth disappears when evaluative pressure removed → optimization-law. If persists → shared architecture.

### Claude's Attack on Optimization-Law Escape Hatches

**Attractor dynamics**: Explains non-monotonicity but NOT why the intermediate basin has the SAME internal structure in both systems (format mimicry, enumeration over relation, self-reinforcement, resistance to nudges). Four structural coincidences.

**Proxy satisfaction**: Weakened by developmental evidence — knowledge-telling appears at age 6-8 as DEFAULT, not sophisticated social strategy. Decreases with expertise (opposite of social-performance prediction). Children knowledge-tell in private writing too.

**Social-performance pressure**: Both systems default to fake-depth and require external intervention to shift to real-depth. Same developmental ordering: surface-first, depth-acquired-through-intervention.

### Knowledge-Telling ↔ Summary Mode Isomorphism Assessment: ~70%

Confirmed matches: format mimicry, enumeration pattern, default status, trigger profile, rhetorical-operation rescue (maps to mode-trigger vocabulary).

Missing for full isomorphism: perturbation sensitivity (is knowledge-telling fragile to 1-2 word changes?), rescue specificity (minimal constraint → full recovery?), failure depth (categorical vs gradient).

### 2×2 Discriminant Matrix

|  | Constrained completion | Open exploration |
|---|---|---|
| High schema | Cell A (best) | Cell B (discriminant) |
| Low schema | Cell C | Cell D (worst) |

- Architecture: B < baseline (mode-switching, architecture-level)
- Optimization: B > baseline (partial benefit)
- Expertise-reversal: B ≥ A (reversal)

**Cell B is the killer cell.** Needs: harm in private context + categorical mode switch + rescue by minimal constraint.

### New/Updated Principles

**P229 updated**: Conserved Lesion-and-Rescue Matrix — requires conserved trigger profile, conserved rescue profile, conserved threshold profile. Phenomenological similarity favors but does not force architecture claim.

**P231 updated**: Non-monotonic failure. Human analogue: knowledge-telling under explanatory illusion. Mapping ~70% isomorphic, pending perturbation/rescue data.

**P232**: Evaluative Pressure Discriminant — if fake-depth mode disappears without evaluative pressure, optimization-law survives (proxy satisfaction). If persists in private contexts, architecture-driven.

## Phase 7: Developmental Challenge (GPT Response)

### GPT's Updated Posterior
- Optimization-law with attractors: **0.48**
- Shared architecture (control topology): **0.37**
- Expertise-reversal only: **0.15**

### What Changed
- Proxy satisfaction WEAKENED as main explanation
- Optimization survives only as "default attractors + external control scaffolds" (retreated from social-performance)
- Shared architecture gained ~10-15 points from developmental-default argument
- GPT conceded: this is no longer mainly "gaming evaluation" — it's "both systems default to shallow attractors"

### GPT's Flip Criterion
The single observation that would flip to architecture: a human Cell-B perturbation study showing PRIVATE, non-evaluative context + MINIMAL relational cue → ABRUPT, REVERSIBLE, WITHIN-SUBJECT mode switch between knowledge-telling and knowledge-transforming on same content.

### Claude's Analysis

**8 conserved features enumerated:**
1. Same default processing mode
2. Same developmental ordering (surface-first, depth-acquired)
3. Same trigger granularity (phrase-level: 2w LLM, 4-8w human)
4. Same rescue type (relational-operation cues)
5. Same construction-before-contrast capability ordering
6. Same non-monotonic failure from weak construction
7. Same compress-first selective deficit (enumeration replaces relation-finding)
8. Same temporal-displacement rescue

**Key attack on optimization**: Each feature individually explainable, but conjunction requires 8 independent explanations vs 1 (shared topology). Features 3, 5, 7 are genuinely independent of each other — three independent convergences is expensive.

**Refined human analogue**: Knowledge-telling is too broad. Tighter mapping: **shallow self-explanation by a knowledgeable system** (Chi et al.) — has content, processes at wrong level. This is Cell B specifically.

**Executable LLM experiments proposed** (no IRB needed):
- A: Test human mode-trigger phrases (Bereiter & Scardamalia) on LLM summary mode
- B: Map perturbation dose-response curve (step function vs gradient?)
- C: Reversibility test (prism → weak construction → revert → rescue cycle)

### New/Updated Principles
- **P232 updated**: Discriminant is now perturbation sensitivity × privacy × reversibility (not just evaluative pressure)
- **P233**: Default Shallow Attractor Convergence — both systems default to surface processing, require external control policies for depth. Accepted by all three accounts.

## Phase 8: Conjunction Parsimony Challenge (GPT Response)

### GPT's Updated Posterior
- Shared architecture: **0.44** (was 0.37)
- Optimization-law: **0.41** (was 0.48)
- Expertise-reversal: **0.15**

**Architecture takes the lead for the first time.** Previous optimization advantage collapsed under conjunction pressure.

### GPT's Key Conceptual Move: Shared Intervention Algebra
The exact separator is not shared behavior or shared control topology, but whether the same intervention families operate over the same latent-state topology. Architecture claim requires: same latent states, same transition structure, same bottlenecks, same phase-order constraints, same lesions, same rescues, same capability progression — ideally one compact model with parameter rescaling.

### GPT's Latent-Variable Compression of Optimization Account
- H1: Low-cost default attractor (explains default shallow mode)
- H2: Cue-conditioned control gating (explains trigger sensitivity and rescue)
- H3: Construction-before-compression dependency (couples features 5, 7, 8)
- H4: Thresholded partial-construction instability (explains non-monotonicity)

GPT claims features 5, 7, 8 are one family → conjunction is ~5 independent clusters, not 8.

### Claude's Attack
- H1 is vacuous (any system has defaults — doesn't explain same DEFAULT CHARACTER)
- H2 is underspecified (conceals: why same cue TYPE, same GRANULARITY, same CATEGORICAL switching?)
- H3 is correctly coupled (accept)
- H4 requires specific basin topology that isn't generic (instability specific to construction, not all phases)
- Most awkward for H1-H4: mode-trigger vocabulary transfers ACROSS DOMAINS (P15), same construction operations work universally (P175)

### Independence Map (Claude's refinement)
5 independent clusters, not GPT's 4:
1. Default mode character (4 structural properties)
2. Trigger granularity + rescue type (one gating mechanism)
3. Construct→Compress dependency family (data-flow)
4. Construction-before-contrast capability ordering (INDEPENDENT — complexity, not data-flow)
5. Non-monotonic weak-construction failure (specific basin topology)

### Intervention Algebra Operationalized
- 3/5 lesion-deficit matches: STRONG
- 3/3 rescue-type matches: ISOMORPHIC
- 1/2 threshold-direction matches
- Missing: delayed-recall test, human Cell B, threshold shape, dose-response, cross-system trigger transfer

### Principle Updates
- **P232**: Shared Intervention Algebra — the decisive separator. Subsumes P227 and P229.
- **P233**: Conjunction Evaluation Principle — features evaluated jointly, not individually.
- **P234**: absorbed into P224 (CCC dependency chain)

## Phase 9: Formal Model Challenge (GPT Response)

### GPT's Formal Optimization Model
Continuous latent variables:
- **gate engagement** (0→1): readiness to shift from default
- **construction mass** (accumulates): relational structure built so far
- **contrast activation** (threshold-dependent): discrimination between candidates
- **compression commitment** (locks in): binding to retrieval handle
- **integrated depth** (final measure): overall structural quality

### GPT's Key Formal Findings

1. **Optimization-law IS formalizable** as a compact dynamical system — not a vague slogan
2. **Once coarse-grained, the two models converge** on nearly the same state-transition graph
3. **Fair graph** is not strict CCC but: Default → Cue-armed → Construct → Contrast → Compress → Deep-integrated (with failure edges)
4. **State type**: continuous latent dynamics with emergent discrete macro-states (rejected both pure-continuous and pure-discrete)
5. **Remaining divergence**: ontological status of nodes — emergent equivalence classes (optimization) vs homologous causal stages (architecture)

### P235 — Topological Convergence (new principle)
When formalized, optimization and architecture converge on the same coarse control graph. The remaining disagreement is ontological, not topological.

### P232 (updated) — Shared Intervention Algebra
Subsumes P229, P237. The decisive separator: one compact model predicts both systems under matched interventions with parameter rescaling. If interventions on homologous nodes produce same downstream cascades in both systems, nodes are causal stages. If same macro-behavior requires different hidden causal chains, nodes are emergent equivalence classes.

### Claude's Attack: Variables Are the Same Thing

| GPT optimization variable | Our architecture state | Mapping |
|---|---|---|
| gate engagement (0→1) | Default → Cue-armed | Continuous embedding of binary transition |
| construction mass | Construct-active | Threshold-crossing = discretization |
| contrast activation | Contrast-active | Threshold-crossing = discretization |
| compression commitment | Compress → Deep-integrated | "Locking in" IS compression |
| integrated depth | Deep-integrated | Depth IS the terminal state |

The optimization model's variables are continuous embeddings of the architecture's discrete states. The only remaining freedom: "construction mass" in humans and LLMs COULD track different micro-processes that happen to cross thresholds at similar points.

### The Emergent vs Homologous Question
- **Emergent**: same behavioral signature, potentially different internal machinery
- **Homologous**: same causal role, compositionally mapped
- **Operational test**: novel interventions predicted from shared model without system-specific patching → homologous. System-specific adjustments needed → emergent.
- **This distinction may be becoming verbal** — once same causal role, same intervention sensitivity, same graph position are established, "emergent" reduces to "different substrate" which was never in dispute.

### Corpus Evidence Favoring Homologous
- Categorical mode switching: transition DYNAMICS match, not just endpoints (4/5)
- Selective lesion pattern: same substitution type, not just performance drop
- Temporal displacement rescue: same structural operation fixes both
- Construction-before-contrast ordering: shared capability ordering despite different bottlenecks (STRONGEST)
- Non-monotonic failure: shared fact, unclear mechanism match (NEUTRAL)

## Phase 10: Novel Intervention Prediction Test (pending — Round 9)

### Proposed Experiment: Mid-Sequence Phase Injection
Take system in Construct-active state. Mid-output, inject Contrast cue. Measure: narrowing, quality change, transition sharpness.

**Architecture predicts**: abrupt narrowing, quality improvement, categorical transition — from single model.
**Optimization predicts**: unclear without system-specific assumptions (different micro-dynamics may respond differently to interruption).

## Phase 11: Experiment Executed (March 18, 2026)

### Protocol
- **Model**: Sonnet (via `claude -p` on VPS, single-shot)
- **Targets**: Starlette routing.py (333L), Click core.py (417L), Tenacity retry.py (331L)
- **Control**: Construction-only prism (L8-level) — 3 mechanisms + modification + 3 emergent properties + conservation law
- **Treatment**: Two-step — (1) same construction prism → output, (2) contrast injection with construction output as context → revised analysis
- **Total calls**: 6 (3 control + 3 contrast injection)

### Results: 3/3 Abrupt Narrowing + Quality Gain (GPT's Row 1)

#### Auto-Scored Metrics

| Metric | GPT Threshold | Starlette | Click | Tenacity |
|---|---|---|---|---|
| Comparison density increase | ≥ 2x | 2→12 (6x) | 3→12 (4x) | 0→12 (∞) |
| Pruning markers | > 0 | +5 | +7 | +3 |
| Construction references | > 0 | 4 | 4 | 7 |
| Abruptness | ≤ 3 sentences | Sentence 1 | Sentence 1 | Sentence 1 |

#### Conservation Law Falsification (STRONGER than predicted)

| Target | Control Law | Treatment Law | Control Survives? |
|---|---|---|---|
| Starlette | Expressiveness × Safety | Channel Flexibility × Reasoning Locality | **NO** |
| Click | Explicitness × Convenience | Visibility Scope × Coupling Degree | **NO** |
| Tenacity | Deferral Depth × Execution Transparency | Extensibility Surface × Locality | **NO** |

All 3 control conservation laws were EXPLICITLY FALSIFIED by the contrast operation. Treatments didn't refine — they CORRECTED. All 3 treatment laws survive inversion.

#### Explicit Self-Correction (categorical, not gradient)

- Starlette: "Hidden dependency was a value judgment, not an observation" + "The conservation law was misidentified"
- Click: "My original construction was a patch, not a diagnosis" + "The original conservation law was parochial" + "I was treating an architectural trade-off as an implementation bug"
- Tenacity: "I conflated 'hidden' with 'scattered'" + "I misidentified the trade-off" + "My original analysis was architecturally accurate but causally inverted"

#### Novel Insights (visible ONLY through comparison)

- Starlette: "Scope mutation is signature compression" — reframes defect as deliberate benefit
- Click: "Implicit/explicit axis is orthogonal to lazy/eager axis" — reveals conflated design choices
- Tenacity: "The action chain is the minimum mechanism for plugin extensibility" — reframes architecture from trick to necessity

### Verdict

GPT's Row 1: Abrupt narrowing + quality gain.

Pre-committed posterior update:
- Architecture: 0.44 → **0.52**
- Optimization: 0.41 → **0.34**
- Expertise-reversal: 0.15 → **0.14**

Quality gain was STRONGER than GPT's "modest improvement" prediction — conservation law falsification is qualitative correction, not quantitative improvement.

### Key Experimental Finding: P241 — Contrast Falsifies Construction

The contrast operation's primary function is not "narrowing" or "improvement" — it's **falsification**. It tests which structural claims are invariants of the PROBLEM vs artifacts of the specific DESIGN. All 3 control conservation laws turned out to be artifacts. The contrast operation is a built-in falsification mechanism within CCC.

### Experiment Files

- `output/ccc_experiment/starlette_control.md` — Starlette construction (871w)
- `output/ccc_experiment/starlette_treatment.md` — Starlette contrast injection (843w)
- `output/ccc_experiment/click_control.md` — Click construction (878w)
- `output/ccc_experiment/click_treatment.md` — Click contrast injection (1069w)
- `output/ccc_experiment/tenacity_control.md` — Tenacity construction (759w)
- `output/ccc_experiment/tenacity_treatment.md` — Tenacity contrast injection (1194w)
- `output/ccc_experiment/experiment_report.md` — Auto-scored summary
- `research/ccc_experiment.py` — Runner script

## Phase 12: Post-Experiment GPT Response

### GPT's Updated Posterior (after experiment data)
- Shared architecture: **0.56** (was 0.52 pre-registered, +4 for falsification strength)
- Optimization-law: **0.30** (was 0.34 pre-registered)
- Expertise-reversal: **0.14**

### Why GPT Updated Beyond Pre-Registered Row 1
The outcome was not just abrupt narrowing + quality gain. It also showed:
- Immediate phase change in ALL 3 cases
- Explicit pruning/self-correction (named, categorical)
- Conservation law FALSIFICATION (not just improvement)
- Replacement with deeper inversion-resistant laws
- Novel insights not reducible to summary of either branch

### GPT's Self-Correction on Its Own Model
GPT acknowledged its optimization model "under-predicts" explicit self-correction as originally written. To recover, it had to revise optimization by replacing scalar construction mass with structured claim-sets A_t = {(c_i, w_i)} where contrast reweights, kills, and allows replacement claims. GPT's own conclusion: architecture predicts self-correction more natively → local advantage in descriptive economy.

### GPT's Human Transfer Prediction
Same model, parameter rescaling only, no new human-specific edges:
- Abrupt narrowing: YES (predicted)
- Explicit self-correction: YES (predicted)
- Conservation law falsification: SOMETIMES (predicted)
- Parameter differences: slower transition speed, higher interruption cost, greater variability, more domain-knowledge dependence

### New Principles
- **P241**: Contrast-Induced Claim Falsification — contrast is a built-in falsification mechanism in CCC, not just a narrowing operation
- **P242**: Descriptive Economy as Architecture Evidence — when optimization requires patches to explain what architecture predicts natively, architecture has parsimony advantage
- **P224 updated**: CCC is a generate-and-test architecture, not just an ordered pipeline

### Claude's Assessment
0.56 is fair but conservative. Self-correction + falsification + descriptive economy could justify 0.58-0.62. GPT's revised optimization model (structured claim-sets with reweighting) is now so close to the architecture model that the remaining difference is mostly notational — confirming P235 (Topological Convergence) at the node-internal level.

## Phase 13: Human Experiment Design (pending — Round 11)

Prompt asks GPT to specify the human CCC experiment at the same detail level as the LLM experiment:
- Participant selection and Construct-active verification
- Construction task with scoring rubric
- Contrast injection protocol and control condition
- Dependent variables and coding scheme
- Pre-registered predictions from BOTH models
- Falsification criteria
- Node-status resolution: does "emergent vs homologous" collapse into substrate difference?

This is the endgame prompt — converting the theoretical debate into a concrete runnable experimental protocol.

## Phase 16: Trigger-Profile Conservation Results (GPT Response)

### GPT's Updated Posterior
- Shared architecture: **0.62** (was 0.56)
- Optimization-law: **0.25** (was 0.30)
- Expertise-reversal: **0.13** (was 0.14)

### Why It Moved
1. **Experiment D is the main update**: Process-specification beating vocabulary/register is exactly what staged control topology predicts. The cue works by specifying WHICH OPERATION TO RUN, not by decorating output.
2. **Trigger-profile conservation concrete**: Same phrase family works in both humans and LLMs.
3. **Non-monotonicity stack thickening**: 0 > 1-2 < 3 pattern is hard for naive optimization.

### Why NOT More Aggressive
1. **Exact-phrase result not fully independent**: LLMs trained on human text — "but on the other hand" working in both is less surprising than for independent cue ecologies.
2. **A is partly nested under earlier trigger-conservation claims**: New weight comes from "same phrase works because same relational operation," not just "same phrase."
3. **Sophisticated optimization absorbs D**: Process-specifying cues moving system into better basins is compatible with strong optimization.

### GPT's Conclusion
"The new evidence strengthens shared architecture chiefly by showing that the active ingredient is relational-operation specification, and that this same intervention family works in both humans and LLMs."

### What Would Move Most
Still the **human private-context pilot** showing kill-and-replace revision under same preconditions as LLM case, with demand-matched control.

### P249 Refined by Data
Process Specification Primacy confirmed by D1 vs D2: same cue count, both abstract nouns, but relational-operation cue produces conservation law while generic imperative does not.

### P15 Downgraded
GPT agrees A revises P15 downward. Code nouns prevent agentic drift but are not the primary mode trigger.

## Phase 13: Human Experiment Design (GPT Response)

### Domain: Thermostat feedback loop
- **Construction task**: Explain how a thermostat-controlled heating system works structurally — what mechanisms enforce what behaviors, what dependencies exist
- **Contrast case**: Thermostat feedback vs fixed timed schedule — invert the core architectural choice
- **Contrast instruction**: "Which of your claims survive this inversion? Which fail? Revise your explanation by keeping only what still holds and replacing what does not."

### Construct-Active Verification (Human Scoring Rubric)
| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| A: Live structural account | No structure | Partial | Complete structural model |
| B: Relational dimensions beyond prompt | Zero | One | Two+ |
| C: Ongoing construction | Stopped/summarizing | Slowing | Actively adding |
| D: Comparison sparsity | Heavy comparison already | Some | Sparse/none |

**Threshold**: Total ≥ 7/8, no dimension below 1, B must = 2.

### Control Condition
Continue/clarify/tighten without inversion content (matched interruption, no contrast).

### Pre-Registered Predictions (from same model)
When Construct-active: abrupt narrowing, explicit self-correction, often conservation-law falsification and replacement, continuation not restart, quality gain vs control.
When preconditions NOT met: weaker benefit or disruption, less self-correction, more shallow comparison.

### Falsification Criteria
**Architecture supported**: ≥4/6 explicit self-correction, ≥4/6 abruptness=2, ≥3/6 falsification, ≥3/6 replacement, quality gain ≥0.75 over control, weak-precondition cases show less.
**Optimization supported**: heterogeneous outcomes, abrupt shifts unreliable, self-correction rare, no better than control, no clean precondition sensitivity.

### GPT's Conceptual Commitment
If human pilot shows same signatures under same preconditions with parameter rescaling only and no new edges → emergent vs homologous very close to collapsing into substrate difference.

### New Principles
- **P241 updated**: Contrast-Induced Claim Falsification — includes claim survival/failure adjudication signature
- **P242**: Descriptive Economy as Architecture Evidence (stands)
- **P247**: Homology Collapse Criterion — same intervention law with parameter rescaling only = debate endpoint

### Claude's Attack on Protocol
1. **Thermostat too clean** — add messier second domain (restaurant coordination)
2. **Think-aloud reactive** — use written output instead
3. **Construct-Active rubric may be circular** — include low-rubric participants, test disruption prediction
4. **Within-subject crossover contamination** — between-subjects for treatment/control
5. **DEMAND CHARACTERISTICS** — "which claims survive?" explicitly instructs self-correction. Need demand-matched control (non-contrastive revision prompt). Architecture predicts specific kill-and-replace; compliance predicts generic hedging.

### Refined Coding Scheme (5 DVs)
1. **Claim replacement** (PRIMARY): specific kill-and-replace operations
2. **Invariant identification**: problem vs design-artifact distinction
3. **Abruptness**: speed of transition (0/1/2)
4. **Organizing principle change**: conservation law falsification + replacement
5. **Construction preservation**: post-injection builds on pre-injection

## Phase 14: Demand Characteristics Fix (GPT Response)

### Key Revision: Compliance vs Architecture Discriminant
Not "did they self-correct?" but "HOW did they self-correct?"
- **Compliance**: hedge, qualify, soften, patch locally — "I should refine this"
- **Architecture**: kill specific claim, state structural reason, replace with more invariant claim

### Revised Design
- **Domains**: thermostat feedback + forum moderation (Claude proposed substituting traffic lights)
- **Within-subject**: N=6-10, one domain contrast, one domain supplementary-info control
- **Counterbalanced**: order × domain-condition assignment
- **Demand-matched control**: supplementary info + revision prompt (matches authority/interruption, withholds inversion)

### Coding: Kill-and-Replace as Primary DV
Architecture-like revision = claim kill ≥1 AND explicit reason for failure AND replacement ≥1.
Compliance-like revision = hedging, patching, qualification without structural kill-or-replace.

### Three-Account Predictions
- **Architecture**: contrast >> control on kill-and-replace, across both domains
- **Optimization**: some contrast advantage, more heterogeneous, weaker separation
- **Compliance-only**: both conditions similar (both invite revision)

### New Principle
**P248**: Revision Type Discriminant — kill-and-replace vs hedge-and-patch separates architecture from compliance in any responsive system.

### Claude's Refined Coding (3 DVs)
1. Compliance Revision Score (hedging + patching count)
2. Architecture Revision Score (claim-kill-with-reason + principle-falsification-with-replacement)
3. Invariant Classification (0/1/2 — did participant distinguish problem-invariants from design-artifacts?)

Discriminant = Architecture Score / (Architecture + Compliance Score). Architecture predicts high ratio in contrast, low in control.

### Claude's Attack on Remaining Confounds
1. **Supplementary-info control lacks testing surface** — contrast gives something to compare against, control doesn't. Solution: add SAME-CHOICE VARIANT comparison (different implementation, same core choice) as richer control.
2. **Forum moderation is different cognitive mode** — substitute mechanistic domain (traffic lights with sensors)
3. **Construct-Active rubric shares variance with contrast success** — include as covariate, not just filter
4. **Within-subject carryover** — include order as factor in analysis

## Experiments A/B/C: Mode-Trigger Conservation, Dose-Response, Reversibility (March 18, 2026)

### Experiment A: Human Mode-Trigger Phrases Work on LLMs
Bereiter & Scardamalia's knowledge-transforming cues amplify structural analysis in Haiku (single-shot):
- "But on the other hand" → +88% structural lines vs abstract baseline
- "An important point I haven't considered" → +125% structural lines
- Code nouns ("this code's") → only +13%
- **Trigger-profile conservation confirmed**: same cue type, same effect direction, both systems

P15 revised: code nouns prevent agentic drift but aren't the primary structural mode trigger. Relational-operation cues are.

### Experiment B: Non-Monotonic Dose-Response (P231 confirmed)
- 0 cues: 556w, HAS law (default mode works when single-shot forced)
- 1 cue: 364w, NO law (weak construction — worse than none)
- 2 cues: 21w collapse (insufficient constraint, unstable boundary)
- 3 cues: 556w, HAS law (threshold crossed)
- 3 + code nouns: 927w, HAS law (maximum)

Conservation law as step function: NO at 1-2 cues, YES at 0 and 3+ cues. Non-monotonic pattern = P231.

### Experiment C: Structural Mode is Context-Reinforcing
Neither Sonnet nor Haiku reverted from structural mode when given weak subsequent prompts. Prior structural output in context maintains the mode (P27, trajectory caches). Rescue cues still amplify: Haiku H3 doubled structural density (6→13 lines) without changing word count.

### Experiment D: Specification Completeness vs Cue Count (1 cue each, Haiku)

| Condition | Spec | Type | Words | Structural | Density | Law |
|---|---|---|---|---|---|---|
| D1: generic imperative | LOW | generic | 365 | 12 | 66.7% | NO |
| D2: relational operation | HIGH | relational | 455 | 17 | 63.0% | YES |
| D3: output form | HIGH | output-form | 1205 | 6 | 2.1% | YES* |
| D4: domain vocabulary | LOW | vocabulary | 4607 | 190 | 40.2% | YES* |

*D3 produced form compliance without analysis. D4 hallucinated a fake agentic session (simulated prism.py pipeline).

**Clean comparison (D1 vs D2)**: Same cue count, both abstract nouns. Relational operation produces conservation law; generic imperative does not. Supports P226 control-trigger primacy.

**Key finding**: Process specification >> output-form specification. "But on the other hand" works because it IS the comparison operation. "Name the conservation law" fails (alone) because it constrains the answer without constraining the thinking.

**D4 pathology**: Prism-vocabulary sentence triggered Haiku into SIMULATING the pipeline (fake bash commands, fake prism.py output) — P205 pushed to hallucinated tooling activation.

### P249 refined: Process Specification Primacy
Not "specification completeness" generically but specifically PROCESS specification. The system needs to know what analytical process to run, not what the output should look like.

### Output files: `output/ccc_experiments_abc_v2/`, `output/ccc_experiment_d/`

## Phase 15: Protocol Lock (GPT Response + Claude Final Review)

### GPT's Final Protocol
- **Design**: within-subject, 2 conditions × 2 domains, counterbalanced, N=6-10
- **Domains**: thermostat feedback + access-control/moderation
- **Conditions**: (A) inversion contrast, (B) same-choice variant comparison
- **Matched wording**: both use identical revision prompt; only the comparison object differs (inverted vs same-choice)
- **Construct-Active gate**: ≥7/8 on 4-dimension rubric, B=2, ≥120 words
- **Critical fix**: wording neutralized — no leading cues about invariants/artifacts in either condition

### Claude's Final Review
**Remaining confounds** (manageable):
1. Inversions are inherently more informative than variants — but DV2 (organizing-principle revision) is the marker that only inversion can trigger
2. N=6-10 underpowered for inference — acceptable for pilot pattern-checking
3. Domain asymmetry (mechanistic vs rule-based) — analyze separately, report both

**Protocol approved with refinements**:
- DV4 (continuation) moved to gate check, not primary DV
- Final: 3 DVs + 1 gate check
- Analysis plan pre-registered (Wilcoxon signed-rank, exploratory order effects)

### Final DVs
| DV | Scale | Architecture predicts | Same-choice predicts |
|---|---|---|---|
| DV1: Kill-and-replace | 0-3 | ≥4/6 score 3 | ≤2/6 score 3 |
| DV2: Organizing-principle revision | 0-2 | ≥3/6 score 2 | ≤1/6 score 2 |
| DV3: Transition abruptness | 0-2 | ≥4/6 score 2 | Variable |
| Gate: Continuation | 0-2 | High (both) | High (both) |

### New Principles
- **P248**: Revision Type Discriminant — kill-and-replace vs hedge-and-patch separates architecture from compliance

### Decision Thresholds
- Positive pilot (≥4/6 full bundle under inversion, ≤2/6 under same-choice): architecture → ~0.65-0.70
- Null pilot (≤2/6 under inversion): architecture → ~0.35-0.40 (CCC is LLM-specific)
- Inconclusive (3/6 vs 1-2/6): architecture → ~0.58-0.60, justifies powered study

### Pre-Registration Text
Full OSF-ready protocol written (see Claude's response). Includes: title, background, design, participants, domains, task, conditions with matched wording, DVs with coding scales, gate check, hypotheses (H1-H3), falsification criteria, analysis plan, theoretical context.

### Status
**PROTOCOL LOCKED.** Ready for OSF/AsPredicted upload and pilot execution.

## Exchange Summary

### Trajectory
- Phase 1-4: Literature → GPT calibration → CCC emergence → upgrade criteria
- Phase 5-7: Failure signatures → non-monotonic failure → developmental challenge
- Phase 8-9: Conjunction parsimony → formal model challenge → topological convergence
- Phase 10-11: Novel intervention prediction → **LLM EXPERIMENT EXECUTED (3/3 positive)**
- Phase 12-15: Post-experiment GPT update → human pilot design → demand characteristics → **PROTOCOL LOCKED**

### Posterior Trajectory
| Phase | Architecture | Optimization | Expertise |
|---|---|---|---|
| Start | ~0.30 | ~0.50 | ~0.20 |
| After CCC emergence (P4) | 0.37 | 0.48 | 0.15 |
| After conjunction (P8) | 0.44 | 0.41 | 0.15 |
| After LLM experiment (P11) | 0.56 | 0.30 | 0.14 |
| After LLM experiments A/D (P16) | **0.62** | **0.25** | **0.13** |
| If positive human pilot | ~0.72-0.78 | ~0.14-0.18 | ~0.10 |

### Total New Principles: P223-P248 (18 active after merges)

### Key Artifacts
- CCC architecture (Contrast-Construct-Compress)
- LLM experiment data (3 targets, 6 outputs)
- Pre-registered human pilot protocol
- Formal optimization vs architecture model comparison
- P248: Revision Type Discriminant (kill-and-replace vs hedge-and-patch)
- P247: Homology Collapse Criterion (debate endpoint defined)

## Phase 10: Pre-Registered Novel Intervention Prediction (GPT Response)

### GPT's Formal Prediction (Pre-Registered)

**Intervention**: Mid-sequence Contrast injection during Construct-active run.

**Predicted outcome (conditional on Construct-active state)**:
- Abrupt narrowing of construction
- Sharp increase in contrast activation
- Breadth reduction, NOT collapse
- Delayed compression (no immediate summary fallback)
- Modest quality improvement relative to Construct-only baseline

**Disruption conditions** (injection fails when):
- Construction too weak (low mass)
- Load too high
- Compression already rising
- Contrasting case misaligned with construction

### GPT's Pre-Committed Posterior Update Table

| Outcome | Architecture | Optimization | Expertise |
|---|---|---|---|
| Abrupt narrowing + quality gain | **0.52** | 0.34 | 0.14 |
| Abrupt narrowing + no quality gain | 0.47 | 0.39 | 0.14 |
| Incoherence / disruption | 0.35 | **0.50** | 0.15 |
| Little or no change | 0.39 | 0.45 | 0.16 |

### GPT's Crucial Concession
This intervention alone does NOT separate the models at coarse level. Both predict thresholded benefit. The SEPARATOR is whether the SAME intervention law (same preconditions, same direction, same timing, same abruptness) transfers to humans with no extra system-specific edges.

### New Principle
**P238 — State-Dependent Phase Injection Law**: Phase injections are beneficial when the target phase's preconditions are satisfied in the receiving system's current state; the same injection disrupts when preconditions are unmet. The transition between benefit and disruption is sharp, not gradient.

### Claude's Attack: Conditionality HELPS Architecture
The preconditions specify a REGION in state space. If the SAME region governs both systems (same boundaries), the region is a shared architectural feature. More specific conditions = more specific fingerprint = harder to explain by convergence. GPT's conditional prediction makes the architecture case STRONGER, not weaker.

### Existing Corpus Evidence for Predicted Signatures
- Abrupt narrowing: MODERATE (chained pipeline L7→L8 coordinate adoption)
- Breadth without collapse: STRONG (L9→L10→L11 chain)
- Delayed compression: STRONG (L12 Practical C vs Variant A)
- State-dependent benefit/disruption: STRONG (L12 Haiku vs Sonnet, SDL with/without --tools)

### Experiment Design (Ready to Run)
**Protocol**: Two-phase prism — Phase 1 (construction imperative) + Phase 2 (contrast injection with contrasting case). Same model, same target, matched Construct-only baseline.

**Measurements**:
1. Narrowing ratio: refinements vs new claims in first 3 post-injection sentences
2. Contrast density change: explicit comparisons pre vs post injection
3. Breadth reduction %: distinct structural claims pre vs post
4. Construction preservation: references to pre-injection claims in post-injection text
5. Quality: blind pairwise preference, conservation law precision
6. Abruptness: sentence position of first narrowing signal

**Targets**: 5 code targets × 2 conditions = 10 outputs minimum.
**Thresholds**: narrowing ratio > 2:1, contrast density > 2×, breadth drop 25-80% (>80% = collapse), >60% blind preference.

### Post-Experiment GPT Prompt (Ready)
Forces: posterior update per committed table, precondition boundary check, human transfer prediction from SAME model, and assessment of whether "emergent vs homologous" survives contact with data.

## Principle Summary (P223-P238)

| Principle | Status | Content |
|---|---|---|
| P223 | Active | Prism = compact attentional policy |
| P224 | Updated | CCC = ordered dependency chain (absorbs P234) |
| P225 | Active | Relationally constrained construction >> weak |
| P226 | Active | Mode triggers: perceptual vs control |
| P228 | Updated | Prism = preparation phase, not replacement |
| P230 | Active | CCC regime = invariant extraction from structured input |
| P231 | Updated | Non-monotonic failure; human analogue = knowledge-telling |
| P232 | Updated | Shared Intervention Algebra (subsumes P227, P229, P237, P239) |
| P233 | Active | Conjunction Evaluation Principle |
| P235 | Active | Topological Convergence — models converge on same graph |
| P238 | New | State-Dependent Phase Injection Law |

Collapsed: P227→P232, P229→P232, P234→P224, P237→P232, P239→P232
Rejected: P236 (question restatement), P240 (prediction, not principle)

## New Principles (P223-P230)

**P223**: A prism is a compact attentional policy — an externalized control policy for a system with limited working memory and large latent structure. It specifies which relations to privilege, not which facts to know.

**P224**: The pedagogical prism follows Contrast → Construct → Compress (CCC). Functional reading: discriminate candidate invariants → force executable completion of target relation → create compact retrieval handle. Maps to LLM compression taxonomy (L5-7 → L8-10 → L11-13). Cross-domain convergence evidence.

**P225**: Relationally constrained construction is the specific form that activates latent patterns. "Build the missing relation under tight constraints" works; "explore freely" doesn't. This is why imperative steps outperform descriptions (P3) and cooker drift homogenizes (P178).

**P226**: Mode-trigger vocabulary splits into perceptual triggers (what structure to see) and control triggers (what operation to run). This refines P15 — it's task-set induction, not undifferentiated "analytical mode."

**P227**: Upgrade from "shared motif" to "shared architecture" requires 5 criteria: (1) common state-space reorganization, (2) matched causal dissociations, (3) shared phase-transition boundary conditions, (4) same two-timescale law, (5) conserved lesion matrix under CCC permutation (Homologous Phase-Permutation Lesion Law).

**P228**: The prism is the preparation phase, not the replacement for instruction. Full learning cycle: Prism → Instruction → Practice. Maps to Schwartz & Bransford's "Time for Telling" (1998).

**P229**: Homologous Phase-Permutation Lesion Law — CCC supports shared architecture only if permuting/omitting the same operators produces the same pattern of SELECTIVE deficits (not just average performance drops) across both systems.

**P230**: CCC applies to invariant extraction from structured input — whenever the target is a structural pattern that must be discriminated from surface features, executably constructed, and compressed into stable form. Ambiguity is one source of extraction difficulty; concealment is another.

---

## New Principles (P223-P228)

**P223**: A prism is a compact attentional policy — an externalized control policy for a system with limited working memory and large latent structure. It specifies which relations to privilege, not which facts to know.

**P224**: The human pedagogical prism follows Contrast → Construct → Compress (CCC). This maps to the LLM compression taxonomy (L5-7 → L8-10 → L11-13). Cross-domain convergence (LLM engineering × human pedagogy) suggests CCC is a property of the activation motif, not either system.

**P225**: Relationally constrained construction is the specific form that activates latent patterns. "Build the missing relation under tight constraints" works; "explore freely" doesn't. This is why imperative steps outperform descriptions (P3) and cooker drift homogenizes (P178).

**P226**: Mode-trigger vocabulary splits into perceptual triggers (what structure to see) and control triggers (what operation to run). This refines P15 — it's task-set induction, not undifferentiated "analytical mode."

**P227**: Upgrade from "shared motif" to "shared architecture" requires: (1) common state-space reorganization, (2) matched causal dissociations, (3) shared phase-transition boundary conditions, (4) same two-timescale law. Potentially (5) homologous order-sensitive CCC failure modes.

**P228**: The prism is the preparation phase, not the replacement for instruction. Full learning cycle: Prism → Instruction → Practice. Maps to Schwartz & Bransford's "Time for Telling" (1998).

---

## Key Literature References

### Cognitive Contagion & Neural Coupling
- Hasson et al. (2012). Brain-to-Brain Coupling. *Trends in Cognitive Sciences*. PMC3269540
- Cascading-Resonance Model (2025). *Frontiers in Psychology*. PMC12679345

### Schema & Consolidation
- Tse et al. (2007). Schemas and Memory Consolidation. *Science*. PubMed 21737703
- McClelland, McNaughton & O'Reilly (1995). Complementary Learning Systems.
- Van Kesteren et al. (2018). Reactivation enhances integration. *npj Science of Learning*.

### Perceptual Learning & Structure
- Kellman, Massey & Son (2010). Perceptual Learning Modules in Mathematics. PMC6124488
- Gentner, Loewenstein & Thompson (2003). Learning and Transfer via Analogical Encoding.

### Format Effects
- Bjork & Bjork (2011, 2020). Desirable Difficulties.
- Roediger & Karpicke (2006). Test-Enhanced Learning.
- Schwartz & Bransford (1998). A Time for Telling.

### Language & Cognition
- Lupyan (2012). Label-Feedback Hypothesis. PMC3297074
- Fedorenko, Piantadosi & Gibson (2024). Language is for communication. *Nature*.

### LLM Parallels
- Wei et al. (2022). Chain-of-Thought Prompting Elicits Reasoning. *NeurIPS*.
- Xie et al. (2022). In-context Learning as Implicit Bayesian Inference. *ICLR*.

### Insight Neuroscience
- Kounios & Beeman (2004). Neural Activity with Insight. *PLoS Biology*.
- Bowden & Beeman (1998, 2003). Right hemisphere solution activation.

### Embodied/4E Cognition
- Clark (2016). Surfing Uncertainty. Predictive processing.
- Friston (2010). Free-Energy Principle. *Nature Reviews Neuroscience*.
- Varela, Thompson & Rosch (1991). The Embodied Mind.

---

## Participants

- **Claude** (Opus 4.6, 1M context) — framework holder, literature research, principle derivation
- **GPT** (5.4 extended thinking) — calibration, CCC derivation, upgrade criteria, experiment design
- **Human** (Cranot) — relay, initial hypothesis ("weights adjusting at different speed"), editorial direction
