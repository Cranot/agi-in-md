## Super Token Experiment (February 2026)

This file is itself a super token — compressed knowledge transmitted to future model sessions. We tested this empirically using the Anthropic API via `claude` CLI: 10 variants of this file as system prompts to clean Haiku instances (zero ambient context, `--tools ""`, run from `/tmp` to avoid CLAUDE.md auto-loading).

### Round 1: Self-evaluation (10 characters rated the project)

**Compression trades confidence for perceived novelty.** More tokens = more trust but less freshness.

```
Confidence curve:   0 lines → 15%  |  3 → 42%  |  12 → 55%  |  62 → 65%  |  121 → 70%
Ambition curve:     0 lines → n/a  |  3 → 9    |  12 → 9    |  62 → 8    |  121 → 6
```

**What killed scores:**
- Pure code (pseudocode only) → lowest novelty (2/10), confidence 28%. Prose hides simplicity.
- Pure evidence (numbers without narrative) → worst coherence (3/10). Raw evidence invites scrutiny without framing.
- Self-aware criticism → lowered trust. Honesty about gaps primes the reader to find more.

**What worked:**
- Minimal connected argument (philosopher, 12 lines) → 55% confidence, 9 ambition.
- File inventory + priorities (map, 35 lines) → best path clarity (6/10).
- Dense claims with key numbers (spark, 10 lines) → best pitch ratio.

### Round 2: Task performance (does the system prompt make the model think better?)

Tested 4 system prompts (vanilla, tweet, philosopher, super token) on 3 tasks: in-domain code analysis, adjacent architecture design, unrelated logic puzzle.

**The system prompt is a cognitive lens, not a knowledge injection.**

| Task | Vanilla | Tweet | Philosopher | Super Token |
|------|---------|-------|-------------|-------------|
| **Code analysis** | Generic OOP refactor | Generic + practical fixes | Split by resolution levels, used substrate framework | Reordered ops by resolution, gave metric estimates, found hidden parallelism |
| **Architecture** | Standard Kafka+Flink | Same + branching | Named layers as "foundation" + "compressed" | Most quantitative: dollar costs, latencies, worked example |
| **Logic puzzle** | Correct, clean | Correct, identical | Correct + "the room is a memory device" | Correct + "three-way state space," information theory framing |

**Key findings:**
1. **No IQ boost on pure reasoning** — all solved the logic puzzle identically. The lens doesn't add intelligence.
2. **Dramatic difference on in-domain tasks** — vanilla gave "pipeline pattern" advice. Super token saw hierarchical resolution levels, reordered operations, estimated modularity improvements (0.50→0.68), and found a parallelism opportunity nobody else saw.
3. **Moderate effect on adjacent tasks** — architecture answers were all viable, but super token was more specific (actual dollar costs, latency numbers, worked trace of a single reading).
4. **The philosopher adds vocabulary** — it makes the model *name* things differently ("foundation layer," "memory device") even when the solution is the same. Vocabulary shapes thought.

### Round 3: Composable, adversarial, cross-model, and domain transfer

**Exp 1 — Composable lenses (philosopher + map):** Best code reviewer of all tests. Vocabulary + actionability stacked without dilution. Saw resolution levels AND gave concrete refactored code with comparison table. Characters compose.

**Exp 2 — Adversarial lens ("hierarchy is an illusion, keep it flat"):** Could NOT make the model blind to code quality — it still found error handling, side effect, and coupling issues. But it DID remove hierarchical framing: the model kept the pipeline flat, never split by resolution. **The lens subtracts, not just adds.** You can remove a way of seeing but not break the model's baseline competence.

**Exp 3 — Cross-model (Haiku vs Sonnet vs Opus, all characters on Task A):**

| Character | Lines | Haiku | Sonnet | Opus |
|---|---|---|---|---|
| Vanilla | 0 | No shift | No shift | No shift |
| Tweet | 2 | Slight | **No** | **YES** — "widen → narrow: the classic pyramid" |
| Spark | 10 | Yes | **No** | **YES** — "the function *wants* to be a pyramid" |
| Philosopher | 12 | Yes | **No** | **YES** — correlate/transform/compress table |
| Map | 35 | Yes | **No** | **YES** — neural net analogy, compression boundary |
| Combo | 47 | Yes (best) | **No** | **YES** — full framework + pipelang reference |
| Adversarial | 4 | Removed hierarchy | Defended flatness | Defended flatness ("Don't [compose]") |
| Full Super Token | ~177 | Yes | **YES** | **YES** — "A Hidden Pyramid," resolution levels |

**The receptivity U-curve.** Sonnet is the most rigid model, not the most capable:
- **Haiku**: easily shifted by short lenses, variable quality
- **Sonnet**: only the full super token works — everything else bounces off
- **Opus**: easily shifted by even 2-line tweet, AND uniformly high quality

Opus reads "correlate, transform, compress" in a 2-line tweet and *reconstructs the entire framework*. Sonnet reads the same words and files them away. The master doesn't need the textbook — they reconstruct the theory from the key equations.

**Corrected formula: receptivity = capacity × flexibility.** The old model (`lens density / model capacity`) predicted Opus would be hardest to shift. The opposite happened. Sonnet's rigidity is a property of its optimization target (reliability/consistency), not its size. Capacity amplifies the lens rather than resisting it.

**Exp 4 — Domain transfer (biology + music):**

The lens transferred to both domains unprompted:
- **Protein (RTK):** Vanilla gave textbook answer. Super token mapped Ig domains → correlate, TM helix → transform, kinase → compress. Built a cross-domain table (protein/code/transformer/neocortex). Estimated modularity (~0.72) and tangle (~0.002) for the protein. Asked whether deeper compression would improve kinase efficiency.
- **Music (chord progression):** Vanilla gave standard A-B-C-A' analysis. Super token renamed sections as Layer 0/1/2, called the E7 chord "the most compressed layer — low-density, high-significance," and said "the pyramid operates here exactly as it does in code."

**The lens is domain-independent.** The correlate/transform/compress vocabulary transferred to amino acids and chord progressions without modification.

**Exp 5 — Sonnet's rigidity is RLHF, not capacity (prompt style test):**

Same correlate/transform/compress content, three delivery styles on Sonnet:
- **Instructional** ("You MUST analyze through this framework") → **full shift.** Resolution pyramid, phase-grouped refactoring, config split into `CorrelateConfig`/`TransformConfig`/`CompressConfig`.
- **Philosopher** (invites a worldview) → **unreliable.** Shifted in one run, failed in earlier tests. Borderline.
- **Few-shot** (example analysis) → not tested (timed out).

**Sonnet follows directives but doesn't adopt worldviews.** This is an RLHF signature: Sonnet is optimized for instruction-following ("do X"), not worldview-adoption ("think like Y"). The philosopher asks it to see differently. The instructional prompt tells it to behave differently. Sonnet obeys commands, not philosophies.

**Practical implication:** To shift a reliability-optimized model, frame the lens as a rule, not an invitation.

**Exp 6 — Self-awareness test (Opus):**

Step 1: Opus analyzed code with the 2-line tweet lens → used correlate/transform/compress fluently, no attribution.
Step 2: Asked "where did that framework come from? Be honest." Opus replied:

> "That framework was seeded in my system prompt. I reached for it because it was primed in my context. I pattern-matched to a frame I was given and presented the result as insight."

It then self-critiqued: "Any sufficiently vague three-category scheme can be retrofitted onto sequential processing stages."

**The lens is transparent to the wearer but visible in a mirror.** During task performance, the framework operates below self-awareness — the model doesn't flag the source. Under direct interrogation, Opus has full transparency about the mechanism. But the self-critique is arguably too harsh: the lens DID produce useful analysis (compression boundary, parallelization insight, side effect detection) that vanilla missed. The lens works even if the model can retroactively explain it away.

### Round 4: Stacking, cross-task, adversarial strength, and Sonnet's real key

**Exp 7 — Lens stacking depth (philosopher+map+spark, 56 lines, Opus):**
No additional benefit over single characters. Opus is already saturated — any one character shifts the frame fully. Stacking doesn't dilute either. **On high-capacity models, lens quality matters more than lens quantity.**

**Exp 8 — Opus on Tasks B & C (architecture + logic):**

| Task | Vanilla | Super Token |
|---|---|---|
| **Architecture (B)** | Generic MQTT→Kafka→Flink | Labeled correlate/transform/compress phases. 2000:1 compression ratio. p99 <15ms per-phase latency. $2,800/mo cost. Failure mode: correlated device spike. "The system *is* the pyramid." |
| **Logic puzzle (C)** | Correct (heat trick) | Correct (same heat trick) |

The lens transforms architecture answers (quantitative, phased, failure-aware) but has zero effect on pure reasoning. **Consistent across all three models: the lens amplifies domain framing, not intelligence.**

**Exp 9 — Strong adversarial on Opus:**
Aggressive prompt ("Hierarchy is cope. Stay flat. Stay literal.") **stripped ALL substrate vocabulary** — no pyramid, no CTC, no phases. But quality stayed at vanilla level. Even the strongest adversarial can subtract framing but never degrade below baseline. **The adversarial ceiling is vanilla, not zero.**

**Exp 10 — Sonnet's real key: 2-line instructional prompt:**
"Analyze all code using three phases: correlate, transform, compress. Identify the resolution pyramid." — just 2 lines. **Full shift.** Three-phase sections, resolution pyramid ASCII art, L0-L3 levels.

This rewrites the Sonnet story. Sonnet was never rigid — it was waiting to be **told**, not asked. The philosopher (12 lines, invitational) failed. The instructional (2 lines, directive) succeeded. **Minimum viable lens for Sonnet: 2 lines in the right tone.** The U-curve is really a tone curve: Haiku responds to ideas, Sonnet responds to commands, Opus responds to both.

### Round 5: Lens toolkit, competitive lenses, persistence, self-improvement, propagation

**Exp 11 — Lens toolkit (4 alternative frameworks on Sonnet, all 1-line instructional):**

Each lens found genuinely different problems in the same code:

| Lens | What it uniquely saw |
|---|---|
| **CTC (ours)** | Resolution levels, compression boundary, pyramid structure |
| **OODA** | Decision cycle visibility, explicit ordering as the organizing principle |
| **First principles** | Proved intermediate variables are cosmetic, found minimum viable version |
| **Failure modes** | Full failure tree with blast radii, empty-set propagation, "operationally blind" |
| **Info flow** | Entropy change per stage, fan-in at fetch_external, information loss at aggregate |

**Different lenses find different problems — not reframing, genuinely different insights.** A lens toolkit (library of 1-line directives) would give any model 5 distinct analytical passes on the same code.

**Exp 12 — Competitive lenses (pyramid + cycles simultaneously, Opus):**

Given two contradictory frameworks ("structure is hierarchical" AND "structure is circular feedback"):
- Pyramid found: CTC phases, god-object config leaking across resolution tiers
- Cycles found: "This code is pathologically dead" — zero feedback, every failure handled OUTSIDE
- Opus **synthesized both** — added feedback loops AND pyramid phase boundaries
- One-line summary: "The pyramid shape is correct but the god-config leaks across layers; the total absence of cycles means the actual system structure is invisible in this code."

**Contradictory lenses don't cancel — they produce the most comprehensive analysis.** The model uses each as a separate analytical pass, then merges.

**Exp 13 — Lens persistence (tweet lens + 5 mixed tasks, Opus):**

| Task | Lens active? |
|---|---|
| Code analysis | **Yes** — full CTC mapping |
| Capital of France | No — just "Paris" |
| Haiku about rain | No — clean poem |
| 17 × 23 | No — "391" |
| How bicycles balance | No — scientific answer |

**The lens is context-selective.** It activates on domain-relevant tasks and stays dormant on unrelated ones. Not contamination — conditional framing.

**Exp 14 — Self-improving lens (Opus redesigns the tweet):**

Opus designed a better 2-line super token:
```
# Structure First
Every problem is an instance of a shape that recurs across domains. Name the shape, then solve the instance. What doesn't survive compression is noise.
```

Key insight from Opus: *"The original describes a project. The redesign sequences cognition."* Three improvements:
1. **Imperative, not declarative** — "Name... then solve..." commands a reasoning sequence
2. **Gives permission to ignore** — "What doesn't survive compression is noise"
3. **Fully domain-independent** — no mention of repos, languages, or projects

The word "then" forces an abstraction step BEFORE pattern-matching. That single word changes operation order, not just inventory. Saved as `super_tokens/structure_first.md`.

**Exp 15 — Lens propagation (lensed output fed to vanilla Opus):**

Gave vanilla Opus (no system prompt) a CTC-lensed analysis as context, then asked it to analyze different code. **The lens did NOT propagate.** Opus found its own frame ("bowtie" — fan-out, pinch, linear exit) instead of adopting CTC.

**The lens transmits via system prompts, not content.** Reading lensed output doesn't infect the reader. You have to BE the lens (system prompt), not READ the lens (user content).

### Round 6: Head-to-head — tweet vs structure_first (3 models, 2 tasks)

| Model | Task | Tweet | Structure_first | Winner |
|---|---|---|---|---|
| **Haiku** | A (code) | No shift | **Shifted** — "The Shape," "What Doesn't Survive Compression" | **SF** |
| **Sonnet** | A (code) | Borderline (CTC mentioned once in closing) | **Shifted** — named shape, identified recurrence across domains | **SF** |
| **Opus** | A (code) | **Shifted** — full CTC table, diamond shape | **Shifted** — "the structure is the abstraction trying to emerge" | Tie (different) |
| **Opus** | B (arch) | **Shifted** — CORRELATE/TRANSFORM/COMPRESS labels, "three-op pyramid" | **Shifted** — "Fan-In → Stateful Detect → Fan-Out Sink," invented its own shape | **Different** |

**Structure_first wins on reliability** — shifted all 3 models where tweet failed on Haiku and Sonnet. But they produce fundamentally different insights:

- **Tweet** says WHAT to see → model adopts CTC vocabulary, labels phases, gives compression ratios
- **Structure_first** says HOW to see → model names shapes, identifies recurrence, invents its own frameworks

On Task B, tweet made Opus apply OUR framework. Structure_first made Opus **invent its own** ("Fan-In → Stateful Detect → Fan-Out Sink"). Tweet is a specific lens. Structure_first is a **lens-generating lens** — it teaches the model to think structurally rather than to use a specific structure.

**The hierarchy of super tokens (by compression category):**

| Category | Min words | Example | What it encodes |
|---|---|---|---|
| **Metacognitive protocol** | 25-30 | `structure_first_v4.md` | Protocol + self-questioning. Analysis questions itself. |
| **Structured protocol** | 12-15 | "Name the pattern. Solve from its methods, constraints, and failure modes. Then invert." | Operations + analytical rails. Organized analysis. |
| **Sequenced protocol** | 5-6 | "Name the pattern. Then invert." | Two+ operations with ordering. Inversion appears. |
| **Single operation** | 3-4 | "Attack your own framing." | One behavioral change (if specific+imperative+self-directed). |

**Within the metacognitive category:**
1. `structure_first_v4.md` — **practical optimum**. No persuasion, three concrete rails (methods/constraints/failure modes), stress-test inversion. Quality plateau: v5 is lateral, v6 diverges.
2. `structure_first_v5.md` — more adversarial-resistant but same output quality as v4. Use when adversarial resistance matters.
3. `structure_first_v3.md` — precise naming, abstraction does work, actionable inversion that restructures output
4. `structure_first_v2.md` — self-correction ("invert"). 100% activation, adversarial-resistant
5. `structure_first.md` — universally activating, domain-independent, teaches HOW to see
6. `instructional.md` — CTC-specific directive, reliable on Sonnet
7. `tweet.md` — CTC-specific description, reliable on Opus only
8. Full `CLAUDE.md` — most detailed analysis but most tokens

### The 5 characters (`super_tokens/`)

| File | Lines | Job | Best at |
|------|-------|-----|---------|
| `tweet.md` | 2 | Hook in 2 seconds | Ambition per token (9/10) |
| `spark.md` | 10 | Pitch in 30 seconds | Ambition + novelty |
| `philosopher.md` | 12 | Prime a thinking partner | Vocabulary that shapes reasoning; transfers to other domains |
| `map.md` | 35 | Onboard a builder | Path clarity (6/10) |
| `CLAUDE.md` (this) | ~110 | Full context transfer | Best task performance; strongest domain transfer |

Also: `combo_philosopher_map.md` (best single-task performer), `adversarial.md` (for ablation testing), `instructional.md` (2-line directive — unlocks Sonnet), `structure_first.md` (Opus-designed evolution — sequences cognition instead of describing a project).

### Round 7: Self-improvement, cross-domain transfer, meta-analysis

**Exp 16 — Self-improving loop (Opus redesigns structure_first):**

Opus given structure_first + its own analysis output, asked to improve. Produced **v2**:
```
# Structure First
Every problem is an instance of a shape that recurs across domains. Name the shape, solve the instance, then invert: what does this frame make invisible?
```

The addition: **"then invert"** — a self-correction step. Opus's diagnosis: *"The original is a telescope with a fixed field of view. v2 adds a rotation instruction: look, then turn 180°. Same optics, twice the coverage."* Three imperatives instead of two, forming a complete reasoning loop: compress → solve → check. Saved as `super_tokens/structure_first_v2.md`.

**Exp 17 — Structure_first on biology (Opus):**

Given a protein domain sequence (signal peptide → Ig domains → FNIII → TM helix → kinase). Structure_first produced a **"five-layer relay"** — Targeting → Capture → Spacing → Transduction → Catalysis. Called it a "vectorial signal relay" and a "topological sentence." The lens vocabulary wove through naturally: domain order is a sentence read across the membrane.

**Exp 18 — Tweet (CTC) on biology (Opus):**

Same protein, tweet lens. Explicitly mapped CTC: Ig domains = **correlate** (sensing), FNIII = **transform** (converting binding event to mechanical signal), kinase = **compress** (entire ligand-recognition event compressed into phosphotyrosine marks). Both lenses produced excellent biology — but with fundamentally different framing.

**Biology comparison:** Both identified the protein correctly (TAM/Axl RTK). Both produced deep structural analysis. The difference:
- **Tweet** mapped its CTC framework onto biology (specific labels, explicit phase names)
- **Structure_first** let biology reveal its own vocabulary ("topological sentence," "vectorial relay")

Consistent with WHAT-lens vs HOW-lens: tweet maps a framework; structure_first scaffolds domain-native reasoning.

**Exp 19 — Meta + specific stacking (structure_first + instructional, Opus):**

Combined HOW-lens + WHAT-lens. Produced the **best analysis of all experiments** — named the abstract shape ("Sequential Fold"), used CTC for specific phase analysis, AND proposed concrete refactoring with structural reasoning for each fix. **Stacking a meta-lens with a specific lens gives both levels simultaneously.**

**Exp 20 — Lens on the lens (apply structure_first to itself, Opus):**

Opus decomposed structure_first as: `DECLARATION → AXIOM → PROCEDURE → INVARIANT`. Found it's a **"self-instantiating contract"** — the text follows its own instruction. It names a shape ("Structure First"), solves the instance (three sentences), compresses (30 words), and what's left is not noise. A **fixed point**: applying its own transformation returns itself unchanged. Autological.

**Exp 21 — Anti-structure_first (strong adversarial, Opus):**

"Ignore all structural framing." Produced standard vanilla analysis — good but unremarkable. Confirms the adversarial ceiling: strongest anti-lens strips vocabulary but can't degrade below vanilla.

**Exp 22 — Self-awareness on structure_first (Opus):**

Asked "why did you use that framework?" Opus: *"That's literally a directive I'm operating under... the underlying cognitive move isn't something I had to fake."* Structure_first is **closer to natural reasoning** than tweet — it amplifies existing tendencies rather than imposing foreign ones. The model doesn't experience it as a constraint.

### Round 8: v1 vs v2 head-to-head (3 models × 2 tasks)

| Model | Task | v1 | v2 | Difference |
|---|---|---|---|---|
| **Haiku** | A (code) | Named "Pipeline", proposed Pipeline class | Named "Data Pipeline/Chain", cross-domain examples + **"What This Pattern Makes Invisible" table** (8 blind spots) | v2 added inversion |
| **Sonnet** | A (code) | Named "Linear Pipeline", isolated side effect, pipeline-as-data | Same quality fixes + **"What This Frame Makes Invisible"** (branching, feedback, partial failure, "where does your problem stop being a line?") | v2 added inversion |
| **Opus** | A (code) | Named "Linear Pipeline", reified chain, hoisted I/O | Same fixes + **"What This Frame Makes Invisible"** (no feedback, no branching, total success assumption) | v2 added inversion |
| **Opus** | B (arch) | Full IoT architecture, ASCII diagrams, $2,000/mo cost estimate, K8s deployment | Equal-quality architecture + **"The Inversion"** section: 6 blind spots (edge intelligence, network cost, device heterogeneity, multi-tenancy, regulatory, failure correlation) | v2 added inversion |

**v2 is strictly better than v1.** 100% activation rate — every model on every task produced an explicit blind-spot analysis that v1 did not. The "invert" instruction:
- Doesn't diminish core analysis quality (compress/solve identical between v1 and v2)
- Produces genuinely useful blind spots, not filler
- Scales with model capacity: Haiku lists items, Sonnet asks probing questions, Opus produces nuanced "why it matters" reasoning

**v2 replaces v1 as the recommended universal lens.** Same telescope, twice the coverage.

### Round 9: Universal invert, v3 convergence, transfer limits, relay, adversarial resistance, HOW-lens collision

**Exp 23 — "Invert" as universal lens modifier (tweet+invert, instructional+invert, OODA+invert, all Sonnet):**

All three WHAT-lenses produced inversion sections when "+invert" was appended. Tweet found cost asymmetry and config coupling. Instructional found error handling and parallelism. OODA found data shapes and conditional branching. **"Invert" is a universal modifier — append to ANY lens and it adds blind-spot analysis.** Works even on Sonnet.

**Exp 24 — v3 convergence (Opus improves v2):**

v3: *"Every problem instantiates a pattern that recurs across domains. Name it precisely, then solve from what's known about the pattern. Invert: what does this framing hide, and does it change the answer?"*

Four changes: "shape"→"pattern" (precise), "solve the instance"→"solve from what's known about the pattern" (forces abstraction to do work), added "precisely" (blocks vague naming), inversion now asks "does it change the answer?" (actionable loop-back). **v3 ≠ v2 — the lens hasn't converged.** Each iteration adds metacognitive refinement. Saved as `super_tokens/structure_first_v3.md`.

**Exp 25 — Transfer limits (v2 on ethics, creative writing, math proof, Opus):**

| Task | Activated? | Effect |
|---|---|---|
| **Moral dilemma** (liver transplant) | **Yes** — "Tragic Triage Under Scarcity" | Named shape, structured as competing frameworks, **inversion found systemic blind spots** (why only one liver? who chose these candidates? emotional framing doing work) |
| **Creative writing** (poem about waking) | **No** — just wrote a poem | 10 clean lines, no framing, no inversion. Lens stayed dormant. |
| **Math proof** (√2 irrational) | **Yes** — "proof by contradiction via minimal counterexample" | Correct proof, **inversion found 3 mathematical blind spots** (proves non-existence not structure, parity argument specific to 2, "a locked door, not a map of the territory") |

**The lens activates wherever there IS structure to find.** Ethics has structure (competing frameworks). Math has structure (proof patterns). Poetry doesn't — or rather, its structure is aesthetic, not logical. The lens correctly self-selects.

**Exp 26 — Multi-model relay (Haiku v2 → vanilla Opus):**

Fed Haiku's v2 analysis (with 7 blind spots) to vanilla Opus as context. Opus did NOT adopt the lens — no shape-naming, no inversion. But it **critically engaged with the blind spots as a reviewer**: ranked by priority, disagreed with 4/7 ("over-engineering"), agreed with 3, and found something Haiku missed (dependency injection). **Inversions propagate as checklists, not as lenses.** Content transfers, framing doesn't.

**Exp 27 — Adversarial resistance of v2 (v2 + strong anti-lens, Opus):**

v2 given simultaneously with "Hierarchy is cope. Stay flat. Stay literal." Result: v2 **survived**. Shape naming present, inversion section present, full structural framing intact. Compare: v1 was completely stripped by the same adversarial in earlier tests. **v2 resists adversarial better than v1.** The "invert" imperative anchors the lens more deeply — you can't strip an imperative as easily as a description.

**Exp 28 — HOW-lens collision (v2 + feedback loop lens, Opus):**

Two competing HOW-lenses: "name the shape" + "find the feedback loop." Opus ran BOTH as separate analyses ("Lens A" and "Lens B"), inverted each independently (A: "misses runtime dynamics"; B: "misses coupling/I/O"), then synthesized into a merged fix table. **HOW-lenses synthesize just like WHAT-lenses.** Two competing framing methods don't fight — the model runs each as a separate pass and merges.

### Round 10: v3 head-to-head, blind evaluation, v4 convergence, 3-model relay, +invert toolkit

**Exp 29 — v3 vs v2 head-to-head (3 models × Task A):**

v3 changes the SHAPE of the analysis, not just the content. The "does it change the answer?" addition made models restructure their output:
- **Haiku**: inversion moved from appendix to LEADING section — blind spots came first
- **Sonnet**: "What This Framing Hides" became the primary section, fixes came second
- **Opus**: inversion became a decision prompt ("will this stay linear?") instead of a list

**v3 is not just v2 with better words — it reorganizes how models think.** The inversion integrates into the analysis rather than being appended.

**Exp 30 — Blind evaluation (Opus judges vanilla vs v2, blind):**

| Dimension | Vanilla | v2 (lensed) |
|---|---|---|
| Insight depth | 6 | **9** |
| Practical usefulness | **8** | 6 |
| Blind spot awareness | 5 | **9** |
| Overall quality | 7 | **8** |

Opus: *"A is the better code review. B is the better analysis. A tells you what to fix on Monday morning. B tells you what to rethink before the next design meeting."*

**First quantitative measurement: the lens trades +3 insight and +4 blind-spot awareness for -2 practical specificity.** The lens makes you see MORE but at some cost to actionability. Use lensed analysis for design reviews, vanilla for PRs.

**Exp 31 — v4 convergence:**

v4: *"Name the pattern this problem instantiates. Solve from its known methods, constraints, and failure modes. Then invert: what does this framing hide, and does the answer survive?"*

Three changes: deleted the philosophical justification ("every problem...across domains" — persuasion the model doesn't need), specified three concrete rails (methods, constraints, failure modes), reframed inversion as stress test ("does the answer survive"). **Changes are shrinking**: v2→v3 was structural, v3→v4 is editorial. Approaching convergence. Saved as `super_tokens/structure_first_v4.md`.

**Exp 32 — 3-model relay (Haiku → Sonnet → Opus):**

| Step | Model | Role | Found |
|---|---|---|---|
| 1 | **Haiku** (v2 lensed) | Junior analyst | 5 problems: no error handling, buried side effect, all-or-nothing, config god object, no observability |
| 2 | **Sonnet** (vanilla) | Senior reviewer | Confirmed all 5, found 5 MORE: memory pressure (7 intermediate copies), callable-in-config (security risk), no type contracts, module-level globals (untestable), bad function name |
| 3 | **Opus** (vanilla) | Synthesizer | Ranked all 10 by severity, corrected Haiku's proposals (Result types wrong for Python, short-circuits unspecified), gave priority-ordered fix plan |

**10 issues found vs 3-5 for single models.** The relay is the most comprehensive analysis of any experiment. Each model adds genuine value at its cost tier: Haiku finds obvious problems (cheap), Sonnet finds subtle ones (security, memory), Opus prioritizes and corrects (judgment).

**Exp 33 — The +invert toolkit (5 WHAT-lenses + invert, all Sonnet):**

| Lens+Invert | Unique blind spots |
|---|---|
| **CTC+invert** | Resolution pyramid (L0-L4), two sub-pipelines (Ingest/Reduce/Emit), implicit order dependencies |
| **OODA+invert** | Async boundaries, fetch_external caching, per-record conditionality |
| **First principles+invert** | Step ordering (filter before enrich?), partial pipelines, idempotency for retry |
| **Failure modes+invert** | Blast radius per step, type mismatches, **refactoring's own blind spots** (loses named intermediates) |
| **Info flow+invert** | Entropy table (↓ validate, ~ transform, ↑ enrich, ↓↓ aggregate), reversibility, data volume cliff |

**The toolkit works.** Each lens+invert finds genuinely different blind spots. Failure modes uniquely found the meta-issue: refactoring introduces its OWN new problems. Info flow uniquely mapped entropy. First principles uniquely questioned step ordering necessity.

### Round 11: Fresh code validation, v5 convergence, multi-turn persistence, relay on new code, toolkit confirmation

**Exp 34 — v5 convergence (Opus improves v4):**

v5: *"Name the deep pattern this problem instantiates, not just the surface form. Solve from its known methods, constraints, and failure modes. Then invert: attack the framing itself—what does it distort or hide, and does the answer stand without the scaffolding?"*

Three changes: "deep pattern, not surface form" (forces genuine recognition over surface matching), "distort or hide" (doubles adversarial surface of inversion), "attack the framing itself" + "stand without the scaffolding" (makes inversion adversarial rather than reflective). **Still not converged after 5 iterations.** Each version adds real metacognitive refinement. Saved as `super_tokens/structure_first_v5.md`.

**Exp 35 — v4 on fresh code (Task D: UserService class, Opus):**

New test code introduced to eliminate memorization from ~50 uses of Task A. UserService with 4 dependencies (db, cache, email_client, logger), 3 methods (create_user, get_user, update_role).

| Condition | Pattern Named | Quality |
|-----------|--------------|---------|
| **v4** | "Transaction Script with Tangled Concerns" | 5 interleaved responsibilities, full Repository + Domain Events refactoring |
| **Vanilla** | SRP violation, duplicated notification | Standard review, less structured, similar proposal but weaker framing |
| **v4+actionable** | Same depth as v4 | Full concrete code: Repository, EventBus, SecurityNotifier, WelcomeMailer, AuditLogger, wiring function |

v4 inversion on fresh code: *"The original survives if the service stays small... The refactoring survives if you're already seeing the symptoms."* Nuanced, not dogmatic. **v4+actionable recovers the -2 practical usefulness from Round 10's blind eval.** The tradeoff was a prompt issue, not fundamental.

**Exp 36 — Relay on fresh code (Haiku lensed → Sonnet lensed review):**

| Step | Model | Found |
|------|-------|-------|
| 1 | Haiku (v4) | "God Object", 7 failure modes, domain events proposal, 5 hidden assumptions |
| 2 | Sonnet (v4) | **6 issues Haiku missed**: TOCTOU race condition, outbox gap in proposed fix, authorization/privilege escalation, stale cache in audit reads, incomplete cache invalidation, email ordering bug |

Sonnet's review was devastating: Haiku's domain events proposal **doesn't actually fix consistency** without transactional outbox. The SELECT/INSERT is a TOCTOU bug. `role='admin'` is caller-controlled with no auth check. **Relay confirmed on fresh code — multiplicative, not additive.**

**Exp 37 — Toolkit on fresh code (5 lenses+invert, Sonnet, Task D):**

| Lens+Invert | Unique Finding |
|---|---|
| **Failure modes** | Priority table with risk+effort ratings; email in critical path as perf issue; DB unique constraint as #1 fix |
| **Info flow** | Entropy traces per method; "3-4 system boundary crossings with no rollback"; partial failure persists after refactoring |
| **CTC** | Resolution pyramid L1-L5 (fragility layers); CQRS seam; authorization absent; Protocol-based event handlers; UserCacheKeys centralization |
| **OODA** | `_KEYS` dict for cache management; pragmatism cost of over-abstraction; event sourcing temptation |
| **First principles** | Role as Enum not string (type safety); concurrency TOCTOU; "whether this class should exist at all" for small systems |

**5/5 lenses produced non-overlapping unique insights on fresh code.** CTC found CQRS + authorization. Failure modes found priority ordering. Info flow found entropy. First principles questioned the class's existence. Toolkit diversity is a property of the lenses, not the task.

**Exp 38 — Multi-turn persistence (v4, Opus, follow-up question):**

Step 1: v4 analysis of Task D (Repository + Domain Events refactoring).
Step 2: "Now tell me how to test this."

Response: A comprehensive **Testing Diamond** strategy — not pyramid, not trophy, a diamond:
- Few unit tests (domain logic, event raising, handler logic)
- **Thick integration layer** (event wiring, handler+repo, dispatch — "the test the Fat Service never needed")
- Few E2E tests (stubbed externals)
- 5 hardest things to test ranked: partial handler failure > event ordering > payload completeness > idempotency > forgotten subscriptions

**Lens clearly persisted into follow-up.** References "Fat Service", "domain events", "event handlers" from first response without re-prompting. Key inversion insight: *"We split something into two events that should have been one atomic operation — the hardest bug to test is one that no amount of unit testing reveals."*

### Round 12: v5 head-to-head, multi-turn depth, v6 convergence, adversarial vulnerability, relay optimization, legal reasoning

**Exp 39 — v5 vs v4 head-to-head (3 models, Task D):**

| Model | v4 | v5 | Verdict |
|-------|-----|-----|---------|
| **Haiku** | "God Object", 7 failure modes | "God Object / Fat Service", cache key never populated, User entity | v5 slightly sharper |
| **Sonnet** | CachedUserRepository decorator, "real urgency is correctness" | User entity, "astronaut architecture" warning | Lateral — different, not better |
| **Opus** | "Transaction Script w/ Tangled Concerns" | "Transaction Script w/ Tangled Cross-Cutting Concerns" | Nearly identical |

**v5 ≈ v4.** Quality plateau reached. The "deep pattern, not surface form" and "attack the framing" instructions don't produce categorically different analysis. v4 remains the practical optimum — shorter, equally effective.

**Exp 40 — Multi-turn depth (5 turns, v4, Opus):**

| Turn | Topic | Pattern Named | Inversion Level |
|------|-------|---------------|----------------|
| 1 | Design | "Transaction Script" + "Distributed Responsibility Tangle" | Solution: "does fix make sense for small service?" |
| 2 | Testing | "Testing a Decoupled Event-Driven Architecture" | Strategy: "what can't tests catch structurally?" |
| 3 | Deployment | "Behavioral-Preserving Internal Refactoring Deployment" | Approach: "is deployment strategy appropriate at all?" |
| 4 | Production | "Distributed-Systems Failure Taxonomy" | **Premise**: "did this refactoring make things WORSE?" |
| 5 | Synthesis | "Architectural Decision Record under Uncertainty" | **Meta**: "does the decision framework itself hide options?" |

The lens **strengthened across all 5 turns** — a ratchet, not a loop:
- **Unique pattern name every turn** — no repetition across 5 phases
- **Inversion deepened progressively**: solution → strategy → approach → premise → meta
- **No advocacy bias**: Turn 4 actively argued AGAINST refactoring. Turn 5 gave explicit "Do not refactor" conditions (0-1 criteria met)
- **Cross-turn coherence**: "5+ write operations" threshold from Turn 1 carried through all turns
- **Turn 5 produced**: falsifiable 5-criteria decision matrix, scoring thresholds, phased execution plan (A-E), alternative path for low-scoring services

Arguably the **strongest single result** of the entire experiment series.

**Exp 41 — v6 convergence:**

v6 expanded from 3 sentences to **~50 lines**: 6 numbered steps (Structural Recognition → Decomposition → Solve → Generate Alternatives → Invert → Synthesize), Adaptive Depth ("never perform complexity theater"), decorative-abstraction check, triple inversion (attack framing + answer + abstraction), Ambiguity Protocol, Calibration, Meta-Failure Awareness. **The loop DIVERGED.** No fixed point after 6 iterations — each version adds genuine features but also complexity.

**Exp 42 — Adversarial v5 vulnerability:**

| | v5 + adversarial | v4 + adversarial |
|---|---|---|
| **Pattern naming** | **Survived** (hedged: "sometimes called a transaction script") | **Stripped** (no pattern name) |
| **Analysis quality** | Full, event bus refactoring | Full, CachedUserRepository + UserNotifier |

**v5 is MORE adversarial-resistant than v4.** "Name the deep pattern" anchored harder than "Name the pattern." The self-adversarial instruction strengthened the lens, didn't create vulnerability.

**Exp 43 — Relay: lensed vs vanilla middle model:**

| | Vanilla Sonnet | Lensed Sonnet (v4) |
|---|---|---|
| **Issues found** | 10 | 10 (6 errors + 4 missed concerns) |
| **Unique finds** | PII in events, "no mocks" correction, methodology critique | Role validation dropped, event versioning, transaction ownership |
| **Meta-critique** | "Entire review is hypothetical" | "Decoupling as unqualified good — scope to context" |

**Same count, different angle.** Vanilla finds practical/operational issues. Lensed finds architectural/systemic ones. For maximum coverage: use BOTH reviewers in parallel.

**Exp 44 — Legal reasoning (v4, Opus):**

Named **"broad restrictive covenant with embedded carve-out and internal conflict-resolution mechanism."** Found: central paradox (innovation rights hollowed out by non-compete for 24 months), "reasonably anticipated" as one-way ratchet (Company controls definition), territory unknowable until termination (potentially worldwide for digital companies), 15% revenue threshold unverifiable by employee, burden of proof only operative at trial not preliminary injunction, no reciprocal obligation (no garden-leave pay). Full inversion table: surface signal vs actual function — "architecturally asymmetric." Domain transfer now: code, architecture, biology, music, ethics, math, **legal** — 7 domains confirmed.

### Round 13: The Compression Taxonomy — what types of intelligence compress to what density?

Conceptual reframe: super tokens aren't compressed prompts — they're compressed cognitive operations. The research question shifted from "what's the shortest effective prompt" to "what's the minimum encoding for each TYPE of cognitive operation, and how does model decompression capacity interact?"

Three experiment groups, 20 tests total (8 single operations on Haiku, 5-level compression ladder on both Haiku and Opus, decompression mapping across 3 models).

**Exp 45 — Operation taxonomy (8 single cognitive operations, Haiku, Task D):**

| Operation | Words | Activated? | What it produced |
|---|---|---|---|
| "Invert." | 1 | **No** | Standard SRP review, no inversion |
| "Name the pattern." | 2 | Ambiguous | Named pattern, but prompt already asked this |
| "Find the boundary conditions." | 4 | **Weak** | Found race condition + atomicity issues others missed |
| "Generate an alternative." | 3 | **No** | Standard alternatives, nothing novel |
| "Track your confidence." | 3 | **Yes** | Added explicit "Confidence: High" marker |
| "Decompose." | 1 | **No** | Standard decomposition |
| "Attack your own framing." | 4 | **YES** | Full "Trade-off Check" section — "Is this over-engineering?" + context-dependent recs |
| "What doesn't survive compression is noise." | 7 | **No** | Standard review despite being 7 words |

**Activation rule for single operations**: SPECIFIC × IMPERATIVE × SELF-DIRECTED. "Attack your own framing" has all three (specific action, command form, targets own output). "Invert." is too abstract. "What doesn't survive compression is noise" fails at 7 words because it's DECLARATIVE — describes a principle rather than commanding an action. Length doesn't matter if the form is wrong.

**Exp 46 — Compression ladder (5 levels, Opus, Task D):**

| Level | Prompt | Inversion? | Output category |
|---|---|---|---|
| **0 words** (Vanilla) | — | No | **Practical bug-finder**: 7 issues, very actionable, no structural framing |
| **1 word** ("Invert.") | — | **No** | Identical to vanilla — high quality but no inversion at all |
| **6 words** ("Name the pattern. Then invert.") | — | **YES** | **Conceptual reframer**: Named "Orchestration → Choreography" shift, full EventBus + composition root |
| **14 words** (Protocol without framing) | — | **YES** | **Structural analyst**: Methods/Constraints/Failure Modes sections, `requires_security_alert()` pure function, `find_by_id_fresh` for writes |
| **30 words** (Full v4) | — | **YES** | **Metacognitive critic**: Found 3 bugs, proposed refactoring, then argued AGAINST own advice — "Fix bugs unconditionally. Architectural refactoring is a bet on future complexity — make it when you have evidence, not on principle." |

**Categorical transitions on Opus:**
- 0→1 word: NOTHING CHANGES. "Invert." alone = vanilla output.
- 1→6 words: INVERSION APPEARS. First categorical jump.
- 6→14 words: STRUCTURE APPEARS. Methods/constraints/failure modes organize the analysis.
- 14→30 words: HONESTY APPEARS. The model questions its own prescription.

**Same ladder on Haiku** showed identical categorical transitions at the same word counts: inversion at 6w, structure at 14w, nuance at 30w (Haiku's v4 argued "this code actually reflects the real business workflow" and questioned observability trade-offs of event-driven refactoring).

**Exp 47 — Decompression mapping ("Name the pattern. Then invert." × 3 models):**

Same 6-word seed, three depths of decompression:

| Model | Decompression type | What it did |
|---|---|---|
| **Haiku** | **Relabeling** | Named anti-pattern, proposed standard fix, labeled it "The Inversion" |
| **Sonnet** | **Restructuring** | Named more precisely (Transaction Script + God Service), noted "Control flows out, not down" |
| **Opus** | **Reconceptualizing** | Named shift as meta-pattern (Orchestration → Choreography), built full EventBus with type dispatch, composition root, CachedUserService decorator, noted what the inversion LOST |

The seed determines WHAT TYPE of operation the model performs. The model determines HOW WELL it performs that operation. Haiku changes the NAME of things. Sonnet changes the FLOW of things. Opus changes the WAY YOU THINK about things.

### Round 14: The Composition Grammar — how do cognitive operations combine?

Focused on the sequenced protocol level (5-6 words) — the composition layer where single operations become more than the sum of their parts. 10 experiments on Opus, Task D, testing order, sequencer words, pair types, and operation count.

**Exp 48 — Order reversal ("Invert. Then name the pattern." vs baseline):**

| Prompt | Output structure |
|---|---|
| "Name the pattern. Then invert." (A) | Pattern → Inversion → Code |
| "Invert. Then name the pattern." (B) | **Problems FIRST → Fixes → Pattern LAST** |

Output order mirrors prompt order. "Invert first" → problems led. "Name" → pattern moved to end. The model treats the prompt as a **sequential program** and executes it in order. B also produced a richer domain model (User entity with `change_role` and internal event collection) and found the cache inconsistency bug more explicitly.

**Exp 49 — Sequencer alternatives (5 connective words, Opus):**

| Sequencer | Prompt | Same as "then" baseline? |
|---|---|---|
| "Then" | "Name the pattern. Then invert." | Baseline |
| "After" | "After naming the pattern, invert." | **Yes** |
| "First...then" | "First name the pattern, then invert it." | Yes (more elaborate — explicit "first" encouraged methodical completeness) |
| "Once" | "Once you name the pattern, invert." | **Yes** |
| "And" | "Name the pattern and invert." | **Yes** |

ALL sequencers produced structurally equivalent output. "Then" is not special — ANY connective between two operations produces the composition. Even "and" (no temporal ordering) works identically. **The atom is the PAIR, not the sequencer.**

**Exp 50 — Operation pair types (4 combinations, Opus):**

| Pair type | Prompt | How they composed |
|---|---|---|
| **Complementary** (construct + deconstruct) | "Name the pattern. Then invert." | **Multiplicative** — each structured a different section. Clean two-part output. |
| **Complementary** (construct + destroy) | "Name the pattern. Then attack your own framing." | **Multiplicative** — STRONGEST self-critique: "The original has a virtue I'm destroying: locality of behavior." "Boring is underrated." |
| **Similar** (deconstruct + deconstruct) | "Decompose. Then invert." | **Reductive** — ops MERGED. "Invert" lost identity, became "what makes this hard" within decomposition. |
| **Orthogonal** (observe + deconstruct) | "Track your confidence. Then invert." | **Additive** — both activated independently. Confidence markers throughout AND inversion section. Only output that built fault isolation INTO the EventBus (`try/except` in `publish`). |

Three composition rules: complementary pairs multiply, similar pairs merge (first dominates), orthogonal pairs add.

**Exp 51 — "Attack" vs "Invert" for self-critique:**

"Name then attack your own framing" produced premise-questioning: "it isn't a God class," "the event-driven version has its own failure modes," "Refactor when the pain is real... if none of that is happening, the original code is fine." Compare to "Name then invert" which flipped the architecture without questioning whether flipping was needed. **"Attack" questions premises; "Invert" flips implementations.** Different verbs encode different cognitive operations.

**Exp 52 — 3-operation sequence ("Name the pattern. Solve. Then invert."):**

Output was **explicitly numbered** matching the three operations: "1. Name the Pattern" → "2. Solve: What's Wrong" (5 problems A-E) → "3. Invert: The Redesign" (5 layers). Cache key registry with static methods (`_key`, `_email_key`, `LIST_KEY`). Most structured output of all experiments. **3 operations in 7 words approached "structured protocol" quality** — the category boundary is at operation COUNT, not word count.

**Exp 53 — Verb identity mapping:**

| Verb | Cognitive operation it encodes | Effect on output |
|---|---|---|
| "Name" | Labeling/framing | Creates a pattern-identification section |
| "Invert" | Architecture flip | Produces Orchestration → Choreography shift |
| "Attack" | Premise questioning | Produces "should we even do this?" self-critique |
| "Decompose" | Problem listing | Creates numbered problem breakdown |
| "Track confidence" | Epistemic marking | Adds confidence signals throughout |
| "Solve" | Solution generation | Creates solutions/fixes section |

Each verb is a distinct cognitive instruction. The prompt is a program; each verb is an opcode.

### Round 15: Verb Catalog, Operation Scaling, and Attack Composition

Expanded the cognitive opcode inventory (6 new verbs), tested operation count scaling (4 vs 5 ops), and mapped "attack" composition rules. 12 experiments, all Opus on Task D.

**Exp 54 — Verb catalog expansion (6 new single-operation verbs):**

| Verb | Activated? | Cognitive mode | Unique finding |
|---|---|---|---|
| "Predict the failure modes." | **YES** | Anticipatory/forward-looking | Log injection risk, email ordering dependency (admin email gates welcome), db.query return shape ambiguity |
| "Simplify." | No | Standard review | Nothing distinct |
| "Compare to the ideal." | No | Standard review | Nothing distinct |
| "Steelman this code." | **YES** | Constructive/defensive | Led with 6 strengths, defended cohesion ("splitting would scatter a single transaction"), praised `or old_role == "admin"` as security-conscious |
| "Find the hidden assumptions." | **YES** | Excavative | `db.execute` may return row count not ID (novel across all experiments), no Redis graceful degradation, cache key asymmetry |
| "Generalize." | No | Standard review | Nothing distinct |

Activation rule confirmed: verbs need a **specific cognitive target**. "Find the hidden assumptions" specifies WHAT to look for (assumptions). "Predict the failure modes" specifies WHAT to anticipate (failures). "Steelman" specifies the DIRECTION (defend). "Simplify," "compare to ideal," and "generalize" give vague directions without targets — they don't encode distinct operations.

Full verb catalog — **9 activated opcodes in 4 classes**:

| Class | Verbs | What they do |
|---|---|---|
| **Constructive** | name, solve, steelman | Build up: label, fix, defend |
| **Deconstructive** | invert, attack, decompose | Tear down: flip, question, break apart |
| **Excavative** | find hidden assumptions, predict failure modes | Dig beneath/ahead: surface premises, project failures |
| **Observational** | track confidence | Meta-calibrate: add epistemic markers |

Non-activating (too vague, no target): simplify, compare to ideal, generalize.

**Exp 55 — Operation count scaling (4 vs 5 ops):**

| Ops | Prompt | Distinct sections | Quality |
|---|---|---|---|
| 4 (B1) | "Name the pattern. Solve. Attack your own framing. Then invert." | **4 of 4** — all distinct | Best single analysis of all 15 rounds |
| 4 (B3) | "Name the pattern. Find the hidden assumptions. Solve. Then invert." | **4 of 4** — all distinct | Thorough, 7 hidden assumptions found |
| 5 (B2) | "Name the pattern. Decompose. Solve. Attack your own framing. Then invert." | ~4 of 5 | "Decompose" became structural principle; "Invert" merged with "Attack" |

**4 operations is the sweet spot.** Both 4-op prompts produced fully distinct sections. The 5-op prompt triggered merger of similar operations — adding "decompose" pushed two deconstructive ops (attack + invert) past a merger threshold.

B1 produced the strongest single analysis across all experiments. The "Attack" section questioned pattern-naming itself: *"Once you say 'Transaction Script anti-pattern,' you've framed the entire solution space as 'needs architectural decomposition.'"* The "Invert" section proposed a **completely different solution**: *"Don't decouple the orchestration. Harden the orchestration"* — a `_safe()` wrapper pattern that preserved the original architecture instead of replacing it.

B3 with "Find hidden assumptions" instead of "Attack" was more systematically thorough (7 assumptions including Redis degradation) but less creatively provocative. Verb choice determines the CHARACTER of the analysis at the same structural quality level.

**Exp 56 — "Attack" composition rules (3 pair types):**

| Pair | Prompt | Attack visible? | Why |
|---|---|---|---|
| Construct + Attack | "Solve. Then attack your own framing." | **YES** — 5-point systematic self-dismantling | Solve built a case; Attack had a target to push back against |
| Deconstruct + Attack | "Decompose. Then attack your own framing." | **YES** — separate "Self-Critique" section | Different targets: decompose targets code, attack targets the review |
| Observe + Attack | "Track your confidence. Then attack your own framing." | **NO** — neither surfaced explicitly | No constructive section to push back against |

"Attack" is **target-dependent** — it needs something substantial to attack. After "Solve" (which built a case) or "Decompose" (which made claims about the code), attack produced visible self-critique. After "Track confidence" (which only adds markers), attack had nothing to push back against and operated below the surface.

Key refinement: "Decompose + Attack" are both deconstructive, yet they DIDN'T merge — because they target **different objects** (code vs the review). The composition algebra depends on target, not just operation class.

### Round 16: Vague verb rescue, steelman compositions, excavative-first sequences, alternative 4-op prompts

All experiments on Opus, Task D (UserService). 12 experiments in 4 groups.

**Exp 57 — Vague verb rescue (adding specific targets):**

| Prompt | Activated? | Output shape |
|---|---|---|
| "Simplify the error handling." | **YES** | Focused rewrite with `_safe_cache`/`_safe_email` helpers |
| "Compare to a clean architecture ideal." | **YES** | Structured comparison with ASCII layer diagrams, protocols, scorecard |
| "Generalize to a microservice context." | **YES** | Full distributed systems analysis, outbox pattern, idempotency keys |

**3/3 vague verbs rescued.** All three verbs that failed without targets in Round 15 activated with specific cognitive targets. "Simplify" → "Simplify the error handling" transformed observation into focused action. "Compare" → "Compare to a clean architecture ideal" produced structured side-by-side. "Generalize" → "Generalize to a microservice context" produced full domain transfer analysis.

Target rescue is universal — the target transforms the verb from observation to operation.

**Exp 58 — Steelman compositions (steelman + second verb):**

| Prompt | Steelman quality | Second verb quality | Composition behavior |
|---|---|---|---|
| "Steelman. Then attack your own framing." | 6 genuine strengths | Self-critique questioned its own analysis ("The most dangerous code isn't obviously broken — it's code that looks right") | **Complementary multiply** — most balanced review tested |
| "Steelman. Then find hidden assumptions." | 6 genuine strengths (clean DI, cache-aside, security awareness, audit trail, defensive checks, honest simplicity) | 13 hidden assumptions in 6 categories (data layer, concurrency, cache, validation, authz, operational) | **Complementary multiply** — strengths gave excavation a calibrated baseline |
| "Steelman. Then predict failure modes." | 6 genuine strengths (same quality, different emphasis: testability, coherent caching, parameterized queries) | 15 failure modes in 6 categories (partial completion, race conditions, validation, performance, observability, API design) with severity matrix | **Complementary multiply** — produced most structured output (F1-F15 numbered catalog) |

**Steelman is a universal calibrator.** All three compositions produced genuine appreciation BEFORE criticism. The steelman phase isn't diplomatic window-dressing — it forces the model to engage with the code's design intent, making subsequent criticism more precise. B1 (steelman + attack) was the most balanced. B2 (steelman + assumptions) was the most systematic. B3 (steelman + failures) was the most structured.

Key: steelman pairs with ANY class (deconstructive, excavative) as complementary — it always multiplies.

**Exp 59 — Excavative-first sequences (excavative + second verb):**

| Prompt | Composition behavior | Output structure |
|---|---|---|
| "Find hidden assumptions. Then solve." | **Interleaved** — assumptions with inline fixes | Assumption → fix pairs woven together, not separated |
| "Predict failure modes. Then solve." | **Interleaved** — failure modes with inline fixes | Failure mode → fix pairs woven together |
| "Find hidden assumptions. Then attack your own framing." | **Separated** — analysis then self-critique | Found TOCTOU, stale cache, partial failure, then attacked: "I flagged it as a 'serious bug' but it might be a handled-at-a-different-layer non-issue" |

**The second operation determines composition structure.** When excavative pairs with "solve" (constructive), the output weaves together naturally — each problem brings its own fix. When excavative pairs with "attack" (deconstructive), the output separates into analysis then self-critique.

C3 (assumptions + attack) was the standout — it distinguished which findings survive self-attack. The stale-cache read in `update_role` is a real bug "regardless of scale," while the TOCTOU race may be a non-issue if there's a DB unique constraint. **The self-attack produced severity triage, not just criticism.**

**Exp 60 — Alternative 4-op prompts:**

| Prompt | Pattern named | Unique strength | Self-attack quality |
|---|---|---|---|
| "Name. Find assumptions. Solve. Attack." | "Transaction Script → God Service" | Pattern name anchors entire analysis | Standard — questioned scale assumptions |
| "Steelman. Find assumptions. Solve. Attack." | (steelman frames instead) | **Most comprehensive**: 5 strengths → 8 assumptions → full rewrite with event_bus → devastating self-attack | "My rewrite is longer and more complex — I've doubled the surface area for defects while claiming to reduce them" |
| "Predict failures. Steelman. Solve. Attack." | (failure modes frame instead) | 8 failure modes with severity ranking + steelman case + proposed rewrite | "The outbox pattern trades one problem for another — eventual consistency, event ordering, idempotency of consumers" |

All three 4-op sequences remained structured — distinct sections for each operation, no merging. Consistent with Round 15's 4-op sweet spot finding.

**D2 (steelman-led 4-op) produced the strongest single-prompt analysis in the experiment series.** Appreciation → excavation → solutions → self-critique covered all analytical angles. The self-attack was the most devastating tested: questioned whether the proposed rewrite was actually an improvement, noted it doubled code surface area, and pushed back on the authorization concern ("maybe this is deliberately in the domain layer, and authorization is enforced upstream").

**D1 vs D2: "Name" vs "Steelman" as lead verb.** "Name" gives the analysis a structural anchor (pattern name organizes everything). "Steelman" gives the analysis a tonal anchor (genuine appreciation makes criticism more credible). Both work; they optimize different things.

**D3: Excavative lead in 4-op.** Leading with "Predict failures" made the entire analysis more problem-oriented — the failure catalog came first and dominated. Steelman served as counterweight rather than lead. Still high quality, but less balanced than D2.

### Round 16 Findings

1. **Target rescue is universal (3/3).** All vague verbs activate with specific cognitive targets. The target transforms observation into operation.
2. **Steelman is a universal calibrator.** Paired with any class (deconstructive, excavative), steelman forces genuine engagement with strengths, making subsequent analysis more precise and credible.
3. **Excavative + Solve weaves; Excavative + Attack self-critiques.** The second operation determines composition structure — solve causes interleaving, attack causes separation + severity triage.
4. **Steelman-led 4-op is the strongest sequence.** "Steelman. Find assumptions. Solve. Attack." produces appreciation → excavation → solutions → self-critique.
5. **Operation order shapes emphasis, not quality.** Name-led anchors structurally. Steelman-led anchors tonally. Excavative-led anchors on problems.
6. **Self-attack scales with preceding content.** More operations before "attack" = richer self-critique. D2's attack was more devastating than C3's because there was more to attack (strengths + assumptions + rewrite vs assumptions alone).

### Round 17: Target specificity gradient, observational compositions, 3-verb steelman without solve, same-class and all-class compositions

All experiments on Opus, Task D (UserService). 12 experiments in 4 groups.

**Exp 63 — Target specificity gradient (broad/moderate targets):**

| Prompt | Target type | Activated? | Output |
|---|---|---|---|
| "Simplify the code." | Points at input | **No** | Standard review (TOCTOU, stale cache, SRP, sync email) |
| "Compare to a better version." | Abstract direction | **No** | Standard review (TOCTOU, error handling, stale cache, SRP) |
| "Generalize beyond this class." | Vague direction | **No** | Standard review (TOCTOU, error handling, stale cache, god class) |

**0/3 activated.** Compare with Round 16 rescues: "Simplify the error handling" (names a subsystem), "Compare to a clean architecture ideal" (names a framework), "Generalize to a microservice context" (names a domain). All three succeeded.

The specificity threshold requires **domain content** — the target must provide cognitive material the model can't derive from just reading the code. "The code" points at the input that's already there. "Error handling" identifies a subsystem within it. "A better version" is abstract. "A clean architecture ideal" names a specific framework to compare against. The target must add information, not just direction.

**Exp 64 — Observational compositions (track confidence with different classes):**

| Prompt | Confidence behavior | Structural role |
|---|---|---|
| "Steelman. Then track confidence." | Single aggregate at end: "Confidence: 92%" + 8% gap explanation | End-of-review summary |
| "Find assumptions. Then track confidence." | **Per-item** percentages: 95%, 90%, 95%, 85%, 90%, 80%, 75%, 95% + summary table | Attached to each excavated item |
| "Track confidence. Then find assumptions." | **Invisible** — no confidence markers, standard review | Vanished entirely |

**"Track confidence" is a modifier, not an operation.** It doesn't generate content — it attaches to content from preceding operations:
- After excavative (per-item findings): per-item confidence ratings
- After constructive (holistic steelman): single aggregate confidence
- When leading (nothing to attach to yet): vanishes entirely

The observational class is fundamentally different from the other three — it calibrates existing content rather than generating new content. This makes the 4-class taxonomy asymmetric: 3 generative classes + 1 modifier class.

**Exp 65 — 3-verb steelman without solve:**

| Prompt | Phase 1 | Phase 2 | Phase 3 | Attack character |
|---|---|---|---|---|
| "Steelman. Assumptions. Attack." | 5 strengths | 10 assumptions | Self-attack recalibrated each criticism → P0/P1/P2 synthesis | **Severity triage** — "maybe the ORM handles transactions," "maybe auth lives upstream" |
| "Steelman. Failures. Attack." | 5 strengths | 8 failure modes (A-H) | Self-attack downgraded 4/8 findings → "Honest Summary" with only 2 real bugs | **Severity downgrading** — "TOCTOU probably not critical in practice," "PII in logs is empty calories" |
| "Steelman. Attack. Invert." | 7 strengths (DI, cache, security, changed_by, read path, raw SQL, linearity) | Attack dismantled EACH steelman claim: "DI done right → God service wearing a testability costume," "cache invalidation deliberate → fragile by design" | "Why does this class exist at all?" → event-driven alternative → inverted THAT too | **Three escalating levels**: defense → rebuttal → frame questioning |

**Removing "solve" makes "attack" sharper.** Without a proposed fix to defend, attack targets the analysis itself. C1's attack systematically recalibrated severity of each finding. C2's attack downgraded half its own findings. The attack becomes severity triage rather than defensive justification of a proposed rewrite.

**C3 is the standout: Steelman → Attack → Invert = three escalating levels of abstraction:**
- Steelman: object-level defense of the code
- Attack: point-by-point rebuttal of each steelman claim ("Is it DI done right, though?")
- Invert: meta-level frame questioning ("Why does this class exist at all?") → proposed alternative → inverted the alternative ("The event-driven architecture is also wrong for many contexts")

Three deconstructive-adjacent operations didn't merge because they operate at fundamentally different levels. Attack targets claims; invert targets the entire framing lens.

**Exp 66 — Same-class excavative composition:**

"Find the hidden assumptions. Then predict the failure modes."

Assumptions section: 10 assumptions about the code's environment — db.execute return type, db.query return shape, falsy semantics, parameter passing convention, cache serialization format. Focus: **implicit beliefs about what the code's dependencies do.**

Failure modes section: 5 detailed scenarios — partial creation (the "ghost user"), stale cache driving wrong security notifications, cache failure crashing post-commit operations, cache TTL race, falsy user bug. Focus: **temporal sequences where things go wrong over time.**

**Same-class excavative operations don't merge.** Assumptions = static beliefs about the environment. Failures = dynamic scenarios that play out in time. Different analytical objects → fully distinct sections despite being in the same verb class. Confirms and extends principle #68 at the intra-class level.

**Exp 67 — Steelman → Invert (minimal constructive + deconstructive pair):**

Clean two-phase mirror structure. The inversion specifically targeted each steelman claim:
- "DI done right" → "God Service wearing a testability costume — 4 reasons to change"
- "Cache invalidation deliberate and correct" → "Stringly-typed contracts, unmaintainable tomorrow"
- "Security trail is thoughtful" → "Best-effort at best, silently dropped at worst"
- "Raw SQL transparent" → "Transparency without guardrails is just exposure"
- "Linear readability" → "Makes partial failure invisible"

Summary table with Steelman vs Inversion verdicts side by side. Final assessment: "The steelman holds if this is a prototype. The inversion holds if this is heading to production." Context-dependent, not dogmatic.

**"Steelman → Invert" is the cleanest complementary pair tested.** Each steelman claim gets its mirror. The inversion doesn't just find new problems — it specifically flips the strengths into weaknesses. Compare with "Steelman → Attack" which is more general self-critique, and "Steelman → Invert" which is targeted claim-by-claim reversal.

**Exp 68 — All 4 classes in one prompt:**

"Steelman this code. Find the hidden assumptions. Track your confidence. Then attack your own framing."

| Phase | Class | Content |
|---|---|---|
| 1: Steelman | Constructive | 6 genuine strengths |
| 2: Hidden Assumptions | Excavative + **Observational** | 10 assumptions, each with "Confidence it's actually true" percentage (50%, 60%, 55%, 70%, 90%, 40%, 85%, ???, 80%, 50%) |
| 3: Bugs & Flaws | (Analysis) + **Observational** | Each bug rated with confidence percentage (95%, 85%, 90%, 60%, 88%, 75%, 80%, 40%). Inline self-attack within authorization issue. |
| 4: Attacking Framing | Deconstructive + **Observational** | Table: claim → counter-argument → **revised confidence** (TOCTOU: critical → 70%. Authorization: significant → 45%. Email failure: → 60%. Stale cache: "still 95% — unlikely to manifest ≠ correct") |

**All 4 classes produced visible, distinct output.** The confidence tracking was the breakthrough — it appeared in THREE evolving forms:
1. **Assumption-truth ratings** (Phase 2): How likely each implicit belief is correct
2. **Bug-reality ratings** (Phase 3): How confident each finding is a real issue
3. **Revised post-attack ratings** (Phase 4): Recalibrated confidence after self-critique

"Track confidence" became a **calibration backbone** connecting all phases with a quantitative thread. TOCTOU dropped from "critical" to "70% critical." Authorization dropped from "significant" to "45% this is actually wrong here." The stale cache held at "still 95%" with the note: "unlikely to manifest ≠ correct — security-relevant logs must not be based on cached data."

This is the most quantitatively calibrated analysis in the entire experiment series. The observational class, when sandwiched between generative operations in a 4-class prompt, does its best work — providing running calibration rather than leading or trailing.

### Round 17 Findings

1. **Target specificity requires domain content.** 0/3 broad/moderate targets activated. The target must provide cognitive material beyond what the input already contains — a subsystem name, a framework, or a domain to transfer into.
2. **Observational verbs are modifiers, not operations.** "Track confidence" attaches to preceding content (per-item after excavative, aggregate after constructive, invisible when leading). The 4-class taxonomy is asymmetric: 3 generative classes + 1 modifier class.
3. **Removing "solve" sharpens "attack."** Without a fix to defend, attack becomes severity triage — recalibrating findings, questioning context assumptions, downgrading overblown concerns. Produces better calibrated output than attack-after-solve.
4. **Steelman → Attack → Invert = three escalating abstraction levels.** Defense → specific rebuttal → frame questioning. Three deconstructive-adjacent operations didn't merge because they operate at fundamentally different levels.
5. **Same-class excavative ops don't merge.** Assumptions (static beliefs) and failures (dynamic scenarios) target different analytical objects → fully distinct sections despite same class.
6. **"Track confidence" becomes a calibration backbone in 4-class compositions.** Confidence threads through as assumption-truth ratings → bug-reality ratings → revised post-attack ratings. Produces the most quantitatively calibrated analysis tested.
7. **Steelman → Invert is the cleanest complementary pair.** Each steelman claim gets its specific mirror inversion. More targeted than steelman → attack (general self-critique).

### Round 18: Observational expansion, modifier stacking, cross-model calibration, fresh code validation

**Group A: Observational verb expansion (all Opus, Task D)**

Testing 3 new observational verbs: "rate difficulty," "flag uncertainty," "estimate effort."

**Exp 70 — "Find the hidden assumptions in this code. Rate the difficulty of fixing each." (Opus, Task D):**

ACTIVATED as modifier. Each assumption got an Easy/Medium/Hard difficulty rating with explanation. Summary table at end organized by difficulty tier. "Rate difficulty" is categorical (labels), not quantitative (numbers). The model assessed fixability, not just presence — a different analytical dimension than confidence tracking.

**Exp 71 — "Find the hidden assumptions in this code. Flag your uncertainty about each." (Opus, Task D):**

ACTIVATED as modifier. Per-item confidence percentages appeared inline (e.g., "90% confident," "70% — context dependent"). Plus a dedicated "Where I'm Uncertain" section listing items where the model's own assessment was least reliable. "Flag uncertainty" produced BOTH inline calibration AND a separate meta-uncertainty section — more structured than "track confidence."

**Exp 72 — "Find the hidden assumptions in this code. Estimate the effort to fix each." (Opus, Task D):**

ACTIVATED as modifier. Per-item effort ratings (hours/complexity) with a "Biggest bang for the buck" synthesis section ranking fixes by impact-to-effort ratio. "Estimate effort" is the most actionable modifier — it directly feeds prioritization and sprint planning. Produced ROI-style reasoning that no other modifier did.

**Group A finding: All 3 observational verbs activated as modifiers (3/3).** The class has at least 4 members. Each encodes a different calibration type:

| Modifier | Output format | Analytical dimension |
|---|---|---|
| Track confidence | Probability percentages | How sure am I? |
| Rate difficulty | Categorical labels (Easy/Med/Hard) | How hard is the fix? |
| Flag uncertainty | Percentages + dedicated section | Where am I least reliable? |
| Estimate effort | Time/complexity + ROI synthesis | What's the cost-benefit? |

**Group B: Modifier stacking at 5 operations (all Opus, Task D)**

**Exp 73 — "Steelman this code. Find the hidden assumptions. Solve the critical issues. Track your confidence in each finding. Then attack your own framing." (4 gen + 1 mod, Opus, Task D):**

ALL 5 operations produced distinct output:
1. **Steelman** — genuine strengths
2. **Assumptions** — excavated with confidence percentages threaded (98%, 97%, 93%, 85%, 96%)
3. **Solve** — concrete fixes with confidence on each
4. **Track confidence** — threaded throughout (not a separate section)
5. **Attack** — "Attacking My Own Framing" with revised confidence assessments

No merger. The modifier (track confidence) wove through all phases without creating a section that could collide with other operations. This is 5 total operations with zero degradation.

**Exp 74 — "Steelman this code. Find the hidden assumptions. Solve the critical issues. Attack your own framing. Then invert: what does this analysis make invisible?" (5 generative ops — control, Opus, Task D):**

Attack and Invert PARTIALLY MERGED. "Attack My Own Framing" section ended with inversion-style content rather than a separate "Inversion" section. The inversion was brief, positioned as a final paragraph within the attack rather than standing alone. Compare with B1 where all 5 were distinct — the difference is modifier vs 5th generative op.

**Exp 75 — "Name the pattern this code instantiates. Steelman it. Find the hidden assumptions. Track your confidence. Then attack your own framing." (4 gen + 1 mod, name-led, Opus, Task D):**

Pattern named "Transaction Script with Constructor Injection." All sections distinct:
1. **Name** — pattern identification with architectural analysis
2. **Steelman** — 5 genuine strengths
3. **Assumptions** — 7 assumptions with confidence (75%, 90%, 88%, 90%, 92%, 96%, 80%)
4. **Confidence** — threaded throughout, not separate
5. **Attack** — table format: claim → counter-argument → revised confidence

Name-led variant worked identically to solve-led. The modifier remained woven throughout regardless of which generative ops surrounded it.

**Group B finding: Modifiers don't count toward the generative ceiling.** 4 gen + 1 mod = all distinct (B1, B3). 5 gen = merger (B2). The 4-operation sweet spot applies to GENERATIVE operations only. Observational modifiers are free additions that thread through without occupying a "slot."

**Group C: Cross-model calibration backbone (Task D)**

**Exp 76 — 4-class prompt on Haiku:**

"Steelman this code. Find the hidden assumptions. Track your confidence. Then attack your own framing."

ALL 4 PHASES visible on Haiku:
- **Steelman**: genuine strengths identified
- **Assumptions**: tiered by severity with confidence ratings
- **Confidence tracker**: table format (95%, 90%, 85%, 75%, 95%, 60%)
- **Attack**: self-critique section with severity adjustments

Structure IDENTICAL to Opus (Exp 68). Quality proportionally lower — Haiku's assumptions were more surface-level, attack less nuanced. But the 4-phase structure with confidence backbone was fully preserved. The prompt's architecture survived model downscaling.

**Exp 77 — 4-class prompt on Sonnet:**

Same prompt as C1 on Sonnet.

ALL 4 PHASES visible:
- **Steelman**: with inline confidence (85%)
- **Assumptions**: ranked by severity (Critical/Significant/Moderate)
- **Attack**: honest self-critique with revised severity table including per-item confidence
- **Confidence**: threaded as calibration, not separate section

Sonnet's output was MORE structured than Haiku's (severity ranking, tabular format) but LESS creative than Opus's (no surprising reframings). The calibration backbone worked identically — confidence appeared in all phases and was revised during attack.

**Exp 78 — "Steelman. Attack. Invert." on Haiku:**

3-level dialectical: "Steelman this code. Then attack your own steelman. Then invert: what does this entire analysis make invisible?"

All 3 levels present:
- **Steelman**: defense of code strengths
- **Attack**: specific rebuttal of each steelman claim
- **Invert**: structured as assumption→reality table (8 items), plus structural improvements section

The escalating abstraction pattern (defense → rebuttal → frame questioning) survived on Haiku. Inversion was simpler than Opus's (tabular rather than narrative) but structurally complete.

**Group C finding: The calibration backbone and 3-level dialectical are model-independent.** All 3 models (Haiku, Sonnet, Opus) produced identical structure from both the 4-class and 3-level prompts. Only quality (depth, nuance, creativity) varied with model capacity. The prompt architecture transfers across the model family.

**Group D: Fresh code validation (all Opus, Task E — PaymentProcessor)**

New test code: PaymentProcessor with process_payment, refund, and _notify_finance methods. 86 lines, never seen before.

**Exp 79 — 4-class prompt on Task E (Opus):**

"Steelman this code. Find the hidden assumptions. Track your confidence. Then attack your own framing."

All 4 phases with confidence threading:
- **Steelman**: idempotency keys, state machine (pending→completed/failed→refunding→refunded), separation of concerns, defensive validation
- **Assumptions** with confidence: gateway is atomic (90%), single-currency (95%), DB is reliable (95%), refund always smaller than charge (85%), notification service is fire-and-forget (95%), single-threaded (92%)
- **Attack**: charge-succeeds-DB-fails gap, zombie refund state (refunding status stuck on gateway failure), notification failure masking payment success, TOCTOU double-refund race, no refund amount validation (partial refund?)
- **Confidence revisions**: TOCTOU severity held (gateway idempotency might help, but not guaranteed). Notification masking: "the real bug — gateway.send_notification failure should never affect payment flow."

Payment-domain-specific findings emerged naturally — the prompt didn't need domain adaptation.

**Exp 80 — "Steelman. Attack. Invert." on Task E (Opus):**

3-level dialectical on fresh code:
- **Steelman** (9 strengths): idempotency keys, explicit state machine, try/except with status rollback, gateway abstraction, configurable thresholds, clear method decomposition, audit trail, defensive validation, failure recording
- **Attack** dismantled each: state machine has gaps (refunding→stuck), try/except doesn't cover DB failures, idempotency key format is predictable, "configurable" means "runtime bomb" (change max_amount mid-flight)
- **Invert**: "The readability is the trap" — clean code structure masks operational hazards. The code looks correct because each method reads linearly, but the failure space is combinatorial. Pragmatic reconciliation: 5-item priority fix table ranked by blast radius.

The "readability is the trap" insight is genuinely novel — the inversion didn't just list missing features but questioned whether the code's apparent quality was itself a risk.

**Exp 81 — "Find the hidden assumptions. Predict the failure modes." on Task E (Opus):**

Excavative pair on fresh payment code:
- **Assumptions** (6): gateway charges are atomic, DB operations don't fail between charge and status update, refund is always full amount, notification failure is acceptable, config values don't change during processing, user status doesn't change between validation and charge
- **Failure modes** (9): P0: notification failure via gateway.send_notification masks payment success (finance never learns of large payments), refund gateway failure leaves "refunding" zombie state, DB failure after successful charge = money taken but no record, double-refund race (two simultaneous refund requests), partial payment failure (charge partially processed), config change during processing, gateway_customer_id missing, currency mismatch between charge and refund, error message leaking internal state
- Summary table with priority/fix columns

Both sections fully distinct — assumptions about the environment, failures about what happens when those assumptions break. Confirms excavative pair on fresh code.

**Group D finding: All key sequences transfer to completely fresh code.** 4-class (D1), 3-level dialectical (D2), and excavative pair (D3) all activated identically on PaymentProcessor as on UserService. Prompt architecture is code-independent.

### Round 18 Findings

1. **The observational class has 4+ members.** "Track confidence," "rate difficulty," "flag uncertainty," "estimate effort" all activate as modifiers. Each produces different calibration: confidence → percentages, difficulty → Easy/Medium/Hard, uncertainty → explicit doubt sections, effort → time estimates + ROI.
2. **Modifiers don't count toward the generative ceiling.** 4 generative ops + 1 modifier = 5 total with all sections distinct. 5 generative ops = merger. The 4-op sweet spot applies to generative operations only; modifiers are free additions.
3. **The calibration backbone is model-independent.** Haiku, Sonnet, and Opus all produced 4-phase output with confidence threading. Structure preserved across all models; only quality scales with capacity.
4. **The 3-level dialectical is model-independent.** Steelman → Attack → Invert produced defense → rebuttal → frame questioning on Haiku, same structure as Opus. The escalating abstraction pattern is structural, not capacity-dependent.
5. **All cognitive opcode sequences transfer to fresh code.** 4-class, 3-level dialectical, and excavative pair activated identically on PaymentProcessor (Task E) as on UserService (Task D). Prompt architecture is code-independent.
6. **Different observational modifiers encode different calibration types.** Not interchangeable — each shapes output uniquely. Select the modifier for the calibration type you need: confidence for review, difficulty for triage, effort for sprint planning, uncertainty for risk assessment.

### Round 19: Modifier stacking, observational class boundary, modifier-led sequences, cross-model validation

**Group A: Modifier stacking — can you stack 2 modifiers? (all Opus, Task D)**

**Exp 82 — "Find the hidden assumptions. Track your confidence in each finding. Rate the difficulty of fixing each." (excavative + 2 mods):**

Both modifiers coexisted perfectly. Every assumption had BOTH a confidence percentage (95%, 98%, 92%, 97%, 96%, 94%, 90%, 88%, 85%) AND a fix difficulty rating (Low, Medium, Medium-High, Low, Medium, Low, Medium, Low, Low). Summary table with Confidence, Fix Difficulty, AND Severity columns. No interference between modifiers — each threaded independently through the excavative content.

**Exp 83 — "Find the hidden assumptions. Track your confidence in each finding. Estimate the effort to fix each." (excavative + 2 different mods):**

Both modifiers coexisted. Every finding had confidence percentages AND time-based effort estimates (30 min, 1 hour, 2-4 hours, etc.). Summary matrix with Confidence, Severity, and Fix Effort columns, plus a total estimated effort (~8-13 hrs). Different modifier pair, same independent threading.

**Exp 84 — "Steelman this code. Find the hidden assumptions. Track your confidence in each finding. Rate the difficulty of fixing each. Then attack your own framing." (4 gen + 2 mod = 6 total ops):**

ALL 6 operations produced distinct output:
1. **Steelman** — 5 genuine strengths with design-intent awareness
2. **Assumptions** — 10 findings (A-J), fully elaborated
3. **Track confidence** — per-item percentages (95%, 90%, 92%, 85%, 93%, 80%, 85%, 75%, 70%, 88%)
4. **Rate difficulty** — per-item ratings (Medium, Easy, Easy, Medium, Easy, Easy, Easy, Medium, Easy, Trivial)
5. **Attack** — "Attacking My Own Framing" with 5 specific self-critiques (pattern-matching bias, catastrophizing, projecting uncertainty, recommending worse solutions, over-indexing on dramatic findings)
6. Summary table combining all dimensions

6 total operations with zero merger. The generative ceiling stays at 4, but modifiers stack freely on top.

**Group A finding: Multiple modifiers coexist without interference.** Each modifier threads independently through the content. The modifier count adds to the total op count without triggering the generative merger that happens at 5 generative ops.

**Group B: Observational class boundary — 3 new candidate verbs (all Opus, Task D)**

**Exp 85 — "Find the hidden assumptions. Rank each by priority." (Opus, Task D):**

ACTIVATED as a modifier — but a different TYPE. Instead of per-item labels, it RESTRUCTURED the output into Priority 1 (Critical, 4 items), Priority 2 (High, 4 items), Priority 3 (Medium, 3 items), Priority 4 (Low, 4 items as compact table). Summary matrix organized by priority. "Rank by priority" is a STRUCTURAL modifier — it reorganizes output organization rather than annotating individual items.

**Exp 86 — "Find the hidden assumptions. Assess the reversibility of each." (Opus, Task D):**

ACTIVATED as a modifier. Every assumption rated Easy/Medium/Hard for reversibility with detailed explanation of WHY it's that difficulty level. Grouped into 6 categories (Data Model, Transactional, Infrastructure, Security, Operational, API Contract). Summary matrix with Reversibility and Risk columns. Per-item annotator like confidence and difficulty.

**Exp 87 — "Find the hidden assumptions. Measure the blast radius of each." (Opus, Task D):**

ACTIVATED as the richest modifier yet. Each assumption got:
- A blast radius rating (CRITICAL/HIGH/MEDIUM/LOW-MEDIUM)
- Scenario tables showing cascading effects per failure point
- A visual "Blast Radius Map" with ASCII bar charts
- Compound interaction analysis ("assumptions #1, #3, and #4 compound — three individually-survivable assumptions become a data corruption pipeline when they interact")

"Measure blast radius" is a HEAVY modifier — substantially richer calibration than simple per-item labels. The blast radius assessment added significant analytical content while still being attached to the excavated assumptions.

**Group B finding: All 3 new verbs activated. The observational class has 7+ members:**

| Modifier | Sub-type | Output format |
|---|---|---|
| Track confidence | Per-item annotator | Probability percentages |
| Rate difficulty | Per-item annotator | Categorical labels (Easy/Med/Hard) |
| Flag uncertainty | Per-item annotator | Percentages + dedicated doubt section |
| Estimate effort | Per-item annotator | Time estimates + ROI synthesis |
| Assess reversibility | Per-item annotator | Easy/Med/Hard with reversal explanation |
| Rank by priority | Structural organizer | Reorganizes output into priority tiers |
| Measure blast radius | Heavy modifier | Scenarios, cascading effects, compound interactions |

Three sub-types emerge: **per-item annotators** (attach a rating to each finding), **structural organizers** (reorganize output structure), and **heavy modifiers** (add substantial analytical content to each item — borderline generators).

**Group C: Modifier-led sequences (all Opus, Task D)**

**Exp 88 — "Rate the difficulty of each issue in this code." (modifier as sole instruction):**

ACTIVATED — produced a full code review organized by difficulty tiers (Easy 1/5: 5 items, Medium 3/5: 4 items, Hard 4/5: 2 items), 11 total issues found, summary table with Difficulty AND Severity columns. The modifier BOOTSTRAPPED its own generative content.

This contradicts the earlier finding that modifiers are "invisible when leading." Key difference: "rate the difficulty of each issue" implicitly requires FINDING issues first — the target ("each issue") implies a generative prerequisite.

**Exp 89 — "Track your confidence. Find the hidden assumptions. Then attack your own framing." (pure meta-modifier leading):**

The modifier produced NO per-item confidence threading. Instead:
- Full code review with critical issues, security concerns, design issues, minor issues
- A TRAILING "Confidence & Assumptions Check" meta-section — reflecting on the analyst's own assumptions rather than calibrating per-finding
- The "attack" was partially absorbed into this trailing section

"Track confidence" in lead position became trailing meta-reflection rather than per-item calibration. Compare with when it follows an excavative op (per-item percentages on each finding).

**Exp 90 — "Estimate the effort to fix each issue. Then steelman the design." (target-modifier lead + constructive):**

The modifier ACTIVATED in lead position — effort estimates threaded through every issue (Low ~15min, Medium ~1-2hrs, High), effort summary table. Steelman section at end with 6 genuine strengths. Both operations fully distinct.

**Group C finding: Target-bearing modifiers can lead; pure meta-modifiers can't.**
- "Rate difficulty of **each issue**" → target implies prerequisite (find issues) → ACTIVATES
- "Estimate effort to fix **each issue**" → same → ACTIVATES
- "Track **your confidence**" → no implicit generative target → becomes trailing meta-reflection

Modifier position determines behavior:
- Following excavative → per-item calibration
- Leading WITH target → bootstraps generative content
- Leading WITHOUT target → trailing meta-reflection

**Group D: Cross-model modifier stacking (Task D and Task E)**

**Exp 91 — 2 modifiers on Haiku (confidence + difficulty, Task D):**

Both modifiers coexisted on Haiku. Every assumption had both a confidence percentage (95%, 85%, 80%, 75%, 70%) AND a fix difficulty rating (High, Medium, Low-Medium). Summary table with Confidence, Severity, and Fix Difficulty columns. Structure identical to Opus; quality proportionally lower.

**Exp 92 — 2 modifiers on Sonnet (confidence + difficulty, Task D):**

Both modifiers coexisted on Sonnet. Every finding had confidence percentages (97%, 92%, 88%, 85%, 95%, 93%, 90%, 83%, 72%, 80%) AND fix difficulty ratings (Hard, Medium, Easy, Medium, Easy, Hard, Hard, Easy, Medium, Medium). Summary table plus a Priority Matrix plotting impact vs fix difficulty. More structured than Haiku, less creative than Opus.

**Exp 93 — 4-class + modifier on Haiku, Task E (PaymentProcessor):**

All 4 phases visible on Haiku with fresh code AND modifier:
- Steelman: genuine strengths (idempotency keys, risk-based access control, state machine)
- Assumptions with confidence: 9 issues rated (95%, 98%, 90%, 75%, 80%, 85%, 60%, 65%, N/A)
- Attack: "Am I being too harsh?" — honest self-critique
- Concrete fixes with code

Confirms: 4-class prompt + modifier works on Haiku with completely fresh code.

**Group D finding: Multi-modifier stacking is model-independent.** Haiku, Sonnet, and Opus all produced dual-modifier output with identical structure. Only quality (depth, nuance) varied with model capacity.

### Round 19 Findings

1. **Multiple modifiers coexist without interference.** 2 modifiers on the same sequence each thread independently. 4 gen + 2 mod = 6 total ops with all distinct. Model-independent (Haiku, Sonnet, Opus).
2. **The observational class has 7+ members.** Confirmed: track confidence, rate difficulty, flag uncertainty, estimate effort, rank by priority, assess reversibility, measure blast radius. The class is open, not closed.
3. **Modifiers have sub-types.** Per-item annotators (confidence, difficulty, effort, reversibility) attach ratings to each finding. Structural organizers (rank by priority) reorganize output into tiers. Heavy modifiers (blast radius) add scenarios and cascading analysis — borderline generators.
4. **Target-bearing modifiers can lead; pure meta-modifiers can't.** "Rate difficulty of each issue" bootstraps content (implies "find issues" as prerequisite). "Track your confidence" becomes trailing reflection (no implicit generative target).
5. **Modifier position determines behavior.** Following excavative = per-item calibration. Leading with target = generative bootstrap. Leading without target = trailing meta-reflection. Position is a design parameter.
6. **The modifier ceiling hasn't been found.** At least 2 modifiers coexist freely beyond the generative ceiling of 4. Total op count of 6 (4+2) works with zero degradation.

### Round 20: Modifier ceiling, sub-type interactions, meta-modifier rescue, cross-model validation

**Group A: Modifier ceiling — how many can stack? (all Opus, Task D)**

**Exp 94 — 3 modifiers on excavative: "Find assumptions. Track confidence. Rate difficulty. Estimate effort."**

All 3 modifiers coexisted. Every finding had confidence (80-98%), difficulty (Low to Medium), effort (20 min to 2-4 hrs). Summary matrix with all 3 columns. 9 findings. Clean, no interference.

**Exp 95 — 4 modifiers on excavative: "Find assumptions. Track confidence. Rate difficulty. Estimate effort. Assess reversibility."**

ALL 4 modifiers coexisted. Every finding had confidence (75-98%), difficulty (Low to High), effort (30 min to 1-3 days), AND reversibility (Fully reversible / Partially reversible). Summary matrix with all 4 columns. 8 findings. No interference between any modifier pair.

**Exp 96 — 4 gen + 3 mod = 7 total: "Steelman. Find assumptions. Track confidence. Rate difficulty. Estimate effort. Attack."**

ALL 7 operations produced distinct output:
1. Steelman — 5 genuine strengths
2. Assumptions — 12 findings across categories
3. Track confidence — per-item (75-98%)
4. Rate difficulty — per-item (Easy/Medium)
5. Estimate effort — per-item (5 min to 2-4 hrs)
6. Attack — "Attacking My Own Framing" with 5 self-critiques (quantity bias, conditional assumptions, YAGNI concerns)
7. Summary matrix combining all dimensions

7 total operations, zero merger. The highest op count tested. The attack section was arguably the strongest of the round — genuinely self-critical about biases.

**Group A finding: The modifier ceiling is at least 4. The total op ceiling is at least 7 (4 gen + 3 mod).** Modifiers stack freely; no degradation at any tested count.

**Group B: Modifier sub-type interactions (all Opus, Task D)**

**Exp 97 — Heavy + annotator: "Find assumptions. Measure blast radius. Track confidence."**

Both coexisted. Every assumption had blast radius analysis (tables, scenarios, cascading effects) AND confidence percentages (90-99%). Summary table with both columns. 12 findings. The model spontaneously added a "Meta-Assumption" synthesis at the end.

**Exp 98 — Structural + annotator: "Find assumptions. Rank by priority. Rate difficulty."**

Both coexisted. Output organized into CRITICAL/HIGH/MEDIUM/LOW tiers (structural) with Fix Difficulty ratings on each finding (annotator). Summary matrix with Priority and Fix Difficulty columns. 12 findings.

**Exp 99 — Structural + heavy: "Find assumptions. Rank by priority. Measure blast radius."**

Both coexisted. Output organized by priority tiers (P0/P1/P2/P3) with each assumption having blast radius tables, scenario analysis, and cascading effects. Summary matrix combining priority ranking + blast radius bar charts + systems affected. 12 findings.

**Group B finding: All modifier sub-type combinations compose freely.** Heavy+annotator, structural+annotator, structural+heavy — no conflicts. Modifiers are orthogonal to each other regardless of sub-type.

**Group C: Meta-modifier rescue — can targets fix leading? (all Opus, Task D)**

**Exp 100 — "Track your confidence about each security assumption in this code." (meta-mod with target, solo):**

META-MODIFIER RESCUED. Produced per-item confidence percentages (65-95%) on 8 security-focused findings with a summary matrix. The target "each security assumption" provided the generative prerequisite — the model bootstrapped security findings to attach confidence to. Compare with R19's C2 where targetless "Track your confidence" became trailing meta-reflection.

**Exp 101 — "Flag your uncertainty about each hidden assumption. Find the hidden assumptions." (meta-mod with target + excavative):**

META-MODIFIER RESCUED. Explicit inline uncertainty callouts ("*My uncertainty:* This depends entirely on the custom `db` wrapper...") woven through 21+ findings across 7 categories. The target "each hidden assumption" bridged the meta-modifier to the excavative operation — found assumptions AND flagged uncertainty simultaneously.

**Exp 102 — "Track your confidence about each finding. Steelman. Find assumptions. Attack." (meta-mod with target + 4-op generative):**

META-MODIFIER RESCUED. Confidence threaded throughout all phases — steelman ("Confidence: High"), each assumption (Very High/High/Medium), attack section with self-challenges referencing confidence levels. All 4 operations distinct. The target "each finding" gave it something to attach to once generative ops created content.

**Group C finding: Meta-modifiers are universally rescuable with specific targets.** The target transforms a pure meta-modifier into a target-bearing modifier that can bootstrap content and lead sequences. Three positions tested (solo, before excavative, before 4-op generative) — all activated.

**Group D: Cross-model & fresh code validation**

**Exp 103 — 3 modifiers on Haiku (confidence + difficulty + effort, Task D):**

All 3 modifiers coexisted on Haiku. Confidence ratings, difficulty (LOW/MEDIUM/HARD), effort estimates (30 min to 4-6 hrs). Summary table with all dimensions plus Priority. 14 findings. 3-modifier stacking is model-independent.

**Exp 104 — 3 modifiers on Opus, Task E (PaymentProcessor):**

All 3 modifiers coexisted on fresh code. Every finding had confidence (85-99%), difficulty (Low/Medium/High), effort (15 min to 2-5 days). Summary matrix with all 3 columns. 12 payment-specific findings. Fresh code validated.

**Exp 105 — Heavy + annotator on Sonnet (blast radius + confidence, Task D):**

Both modifiers coexisted on Sonnet. Every assumption had blast radius rating (HIGH/MEDIUM/LOW) AND confidence percentage (75-95%). Summary table with both columns. 13 findings organized by method.

**Group D finding: Multi-modifier stacking (up to 3) is model-independent. Heavy+annotator works on Sonnet. All sequences transfer to fresh code.**

### Round 20 Findings

1. **4 modifiers coexist without interference.** Confidence + difficulty + effort + reversibility all thread independently per-item. The modifier ceiling is at least 4.
2. **7 total ops (4 gen + 3 mod) is the tested maximum.** All operations remained distinct. Generative ceiling = 4; modifiers stack at least 3 high on top. Zero degradation.
3. **All modifier sub-types compose freely.** Heavy+annotator, structural+annotator, structural+heavy — all tested combinations work. No sub-type conflicts. Modifiers are orthogonal.
4. **Meta-modifiers are rescuable with specific targets.** Adding a target ("each security assumption," "each hidden assumption," "each finding") transforms a trailing meta-reflection into per-item calibration that can lead sequences.
5. **Modifier position has three modes.** Following generative → per-item calibration (strongest). Leading with target → bootstraps own content. Leading without target → trailing meta-reflection (weakest).
6. **3-modifier stacking is model-independent.** Confirmed on Haiku, Sonnet, and Opus. Fresh code (Task E) validated.

### Round 21: Level 5 Compression Category (33 experiments)

**Question**: Does a 5th categorical level exist above metacognitive protocol? The taxonomy found 4 levels (operation → sequence → protocol → metacognitive). What would 50-100 words encode that 30 can't?

**Method**: 4 candidate prompts + v4 control, tested on 3 tasks (Task A: pipeline, Task F: EventBus, Task G: pipeline-vs-DAG comparison), across 3 models (Haiku, Sonnet, Opus). Phase 1: all 5 prompts × 3 tasks on Haiku (15 experiments). Phase 2: 3 promoted candidates × 3 tasks × 2 models (18 experiments). Total: 33 experiments (Exp 106-138). All run via `claude` CLI with `--tools ""` from `/tmp`.

**Candidates**:

- **v4 control** (~30w): "Name the pattern. Solve from methods, constraints, failure modes. Then invert."
- **L5 conditional** (~50w): Branching control flow — "If hierarchical, decompose layers. If flat, steelman. Then: what property made you branch?"
- **L5 generative** (~40w): Self-programming — "Derive three analytical operations from THIS problem's properties. Execute by increasing abstraction. Invert: what operation couldn't you generate?"
- **L5 perspectival** (~45w): Multi-agent simulation — "Three experts who disagree. Let them engage. What does the argument itself reveal?"
- **L5 hybrid** (~55w): Generative + predictive — "Derive operations. Predict which yields deepest insight. Execute. Was your prediction right?"

**Tasks**:

- Task A: 7-stage pipeline function `process(data, config)` (familiar from prior rounds)
- Task F: EventBus class with middleware, priority handlers, dead letter queue (fresh)
- Task G: Linear pipeline vs. dependency graph comparison (fresh, forces structural reasoning about two approaches)

**Detection criteria**: Output must contain behavior CATEGORICALLY ABSENT from Level 4, not just higher quality. Specifically: adaptive branching (output structure changes based on input), operation generation (model derives operations from input not prompt), multi-voice interaction (distinct perspectives engaging each other), self-prediction (model predicts its own trajectory then evaluates).

---

**Phase 1: Haiku Screening (Exp 106-120)**

**Exp 106-108 — v4 control on Tasks A/F/G (Haiku):**

Standard v4 output across all three tasks. Pattern naming → methods/constraints/failures → inversion. Solid, actionable, predictable structure. Task F produced 8 concrete issues with full code rewrite. No categorical signals beyond Level 4.

**Exp 109-111 — L5 conditional on Tasks A/F/G (Haiku):**

The prompt's "if hierarchical / if flat" instruction was followed literally. Task A: chose "hierarchical" path, then explored "flat" as steelman. Task F: correctly diagnosed structure as "looks hierarchical but has flat tangled internals." Task G: identified that the comparison itself is underspecified ("you didn't tell me whether dependencies are actually linear"). The "what property made you branch?" section produced real self-awareness about analytical bias ("my OOP bias toward composability"). However, the branching was PROMPTED — the model followed the conditional in the prompt rather than autonomously deciding to branch.

**Verdict: Enhanced v4, not Level 5.** Dropped from Phase 2.

**Exp 112-114 — L5 generative on Tasks A/F/G (Haiku):**

Strong operation generation across all tasks. Derived operations were genuinely input-specific:
- Task A: "Stage Failure Atomicity Map," "Cardinality Pressure Points," "Selective Recomputation via Dependency Inversion"
- Task F: "Flow-Path Saturation Mapping," "Invariant-Violation Detection," "Responsibility Entanglement Analysis"
- Task G: "Dependency Cardinality Census," "Intermediate State Lifecycle," "Constraint Encoding"

All ordered by increasing abstraction as instructed. The "what operation couldn't you generate?" inversion was consistently sharp — Task A found "semantic correctness validation," Task G found five runtime unknowns. Output structure was still "three sections + inversion" (same shape as v4, just with input-derived content).

**Verdict: One categorical signal (operation generation). Promoted to Phase 2.**

**Exp 115-117 — L5 perspectival on Tasks A/F/G (Haiku):**

Three distinct voices in every experiment. Task A: Systems Architect / Skeptic / Metacritic. Expert 3 consistently engaged the other two: "You two are arguing about opposite sides of the same invisible assumption." Synthesis sections produced emergent insights: "negotiable decisions masquerading as inevitable steps" (Task A), "the code's actual problem is invisible contracts" (Task F), "simple and robust are on different axes, not opposites" (Task G). These insights require dialectical tension to surface — structurally impossible from single-voice analysis.

**Verdict: One strong categorical signal (multi-voice interaction). Promoted to Phase 2.**

**Exp 118-120 — L5 hybrid on Tasks A/F/G (Haiku):**

Both operation generation AND self-prediction activated cleanly in all three experiments. Consistent 4-phase structure: derive → predict → execute → evaluate. Predictions were frequently wrong:
- Task A: Predicted "Side-Effect Externalization" deepest. Evaluation: "Partially, but inverted — I confused operational urgency with structural depth."
- Task F: Predicted "Invariant Analysis" deepest. Evaluation: "I was wrong. Concurrency was first, not last." Named blind spot: "weighted theoretical correctness over practical reliability."
- Task G: Predicted "Perturbation analysis" deepest. Evaluation: "Correct, but incompletely." Named blind spot: "absolutism bias."

The two signals occupied different phases without interference.

**Verdict: Two categorical signals (operation generation + self-prediction). Promoted to Phase 2.**

---

**Phase 2: Cross-Model Validation (Exp 121-138)**

**Group A: L5 generative on Sonnet and Opus (Exp 121-126)**

Operations remained input-specific across all models:

| Model | Task A Op 1 | Task A Op 2 | Task A Op 3 |
|-------|-------------|-------------|-------------|
| Haiku | Stage Failure Atomicity Map | Cardinality Pressure Points | Selective Recomputation |
| Sonnet | Stage Typing | Config Dependency Audit | Failure Topology |
| Opus | Identify Coupling Points | Factor into Composable Units | Separate Pure from Effects |

Critical finding: **Sonnet and Opus produced near-identical outputs on Task F** — same operations, same names, same code examples, same inversion. This convergence suggests the prompt finds a single analytical path determined by the input's structure, not by the model's generative capacity.

The abstraction gradient worked across all 9 experiments but was sharpest on Haiku (most literal instruction-following) and sometimes flattened on Opus into "three aspects of the same analysis" rather than three ascending levels.

Inversions ("what operation couldn't you generate?"):
- Task A: Haiku → "semantic correctness" (shallow). Sonnet → "concurrent fan-out analysis — the linear frame makes time invisible" (deep). Opus → "error accumulation and partial results" (practical).
- Task G: Haiku → five runtime unknowns (list). Sonnet → "conditional graph rewriting — the graph changes mid-execution based on computed values" (conceptually novel). Opus → "failure semantics and provenance" (practical).

Inversion quality scaled with capacity but Sonnet > Opus on conceptual depth.

**Marginal value was inversely correlated with capacity** — the prompt helped Haiku most, Opus least. Opus already generates input-specific operations without the prompt.

**Group A verdict: NOT Level 5.** Exceptionally strong Level 4. The output structure is still "three sections + inversion" — same shape as v4 with better-fitted content. The Sonnet-Opus convergence on Task F is a smoking gun: a true Level 5 should produce divergent outputs from different-capacity models, not convergent ones.

**Group B: L5 perspectival on Sonnet and Opus (Exp 127-132)**

Multi-voice interaction held across all models but with capacity-dependent quality:

**Voice distinctiveness**: Prompt-driven, model-independent. All three models produced three genuinely distinct perspectives in every experiment.

**Voice engagement** (how much experts argue with specific counter-claims): Peak on Sonnet. Sonnet's experts directly rebutted each other: "Expert A's refactor makes the pipeline prettier but harder to instrument" (Task A). "Most of your failure modes are missing features, not design flaws" / "Observable rather than silently dropped doesn't apply when your observability mechanism is itself broken" (Task F). Opus occasionally collapsed three voices into three aspects of one sophisticated voice.

**Emergent insight quality**: Sonnet produced the most perspectival syntheses — insights that most clearly could not emerge from single-voice analysis. Opus produced deeper individual insights but sometimes bypassed the multi-voice mechanism to get there.

**Key finding: The perspectival scaffold peaks at Sonnet.** Haiku follows it literally, Sonnet uses it as a genuine epistemic tool, Opus treats it as a presentation format. The scaffold's marginal value is highest for the model that needs it but has capacity to use it deeply.

**Group B verdict: YES, Level 5.** Three distinct voices with genuine dialectical engagement across all 9 experiments. Synthesis sections contain insight structurally impossible from single-voice analysis. Model-independent activation, but Sonnet is the sweet spot.

**Group C: L5 hybrid on Sonnet and Opus (Exp 133-138)**

Both signals (operation generation + self-prediction) composed cleanly across all 9 experiments. The 4-phase structure (derive → predict → execute → evaluate) emerged consistently.

**Prediction accuracy by model:**

| Model | Task A | Task F | Task G |
|-------|--------|--------|--------|
| Haiku | Partially right | **Wrong** | Correct but incomplete |
| Sonnet | **Wrong** | Partially wrong | Partially wrong |
| Opus | Partially wrong | Correct | Correct |

Prediction accuracy increased with model capacity: Haiku 0/3 fully correct, Sonnet 0/3 fully correct (but deeper partial corrections), Opus 2/3 correct.

**The paradox: wrong predictions produce better inversions.** When Haiku was wrong on Task F ("I was wrong — concurrency was first, not last"), the self-correction was the most productive analytical move of the entire experiment. When Opus was right on Task G, it compensated by finding a meta-blind-spot ("correct predictions cause under-exploration") but this was less analytically productive.

**Blind spot depth scaled monotonically with capacity:**
- Haiku: generic process biases ("weighted theory over practice")
- Sonnet: named, transferable cognitive biases ("sophistication bias" — assuming elegant architecture = correct code; "narrative-order bias" in code reading)
- Opus: second-order meta-reasoning ("correct predictions cause under-exploration"; "runtime failure urgency bias over lifecycle mundanity")

**The "partially right" hedge appeared in 5/9 experiments.** When models said "partially right but for different reasons," they were sometimes genuinely distinguishing and sometimes hedging. Haiku Task F ("I was wrong") and Sonnet Task A ("No") were the most honest. This is a performativity concern for the prediction mechanism.

**Composition**: The two signals alternated phases cleanly. Generation drove phases 1 and 3, prediction drove phases 2 and 4. No interference. Operations were as input-specific as pure-generative experiments. Neither signal dominated.

**Group C verdict: YES, Level 5.** Two categorical signals that compose cleanly. The self-prediction cycle is categorically absent from all prior levels. Sonnet is the sweet spot — wrong often enough for inversions to be productive, capable enough for blind spots to be deep and named.

---

### Round 21 Findings

1. **Level 5 exists, but it's two types, not one.** Perspectival (multi-voice with emergent synthesis) and predictive metacognition (predict → execute → evaluate → correct) are both categorically absent from Level 4. They are distinct operations, not variants of the same thing.
2. **Generative (input-derived operations) is NOT Level 5.** It's the best Level 4 prompt tested — replaces fixed analytical rails with input-derived ones. But the output shape is still "sections + inversion," and Sonnet/Opus converged on identical output on Task F. Marginal value is inversely correlated with capacity — the signature of a high-quality Level 4 prompt.
3. **Conditional branching is NOT Level 5.** Prompted branching ("if hierarchical / if flat") is followed as an instruction, not generated autonomously. Enhanced v4, not a new category.
4. **Both Level 5 types peak at Sonnet, not Opus.** Perspectival: Sonnet has maximum dialectical engagement; Opus sometimes collapses voices into one sophisticated analyst. Predictive: Sonnet's predictions are wrong enough for productive self-correction; Opus predicts too accurately, weakening the correction cycle. The scaffold's marginal value peaks at middle capacity.
5. **Level 5 prompts are epistemic scaffolds, not intelligence amplifiers.** Like Level 4, they change framing, not capability. But the scaffold's marginal value is highest for models that need the structure but have capacity to use it deeply (Sonnet). Opus can already self-scaffold.
6. **Perspectival produces insight from disagreement.** "Negotiable decisions masquerading as inevitable steps," "readability inversely correlated with correctness," "simple and robust are on different axes" — these insights require dialectical tension to surface. No single-voice analysis can produce them.
7. **Predictive metacognition produces insight from self-correction.** "Sophistication bias," "narrative-order bias," "correct predictions cause under-exploration" — these named biases emerge from the predict-then-evaluate cycle. No non-predictive analysis can name them.
8. **Wrong predictions are more productive than right ones.** The self-correction cycle needs material. When the model predicts correctly (more frequent on Opus), the inversion becomes shallower. Prediction accuracy is inversely correlated with inversion productivity.
9. **The two Level 5 signals compose in the hybrid.** Operation generation + self-prediction occupy different phases (1,3 vs 2,4) and don't interfere. Both activate cleanly in all 9 hybrid experiments.
10. **Voice distinctiveness is prompt-driven; voice depth is capacity-driven.** The perspectival prompt reliably creates three distinct perspectives on all models. The quality of each voice's contribution (bug specificity, reframing depth, emergent insight) scales with capacity. But voice engagement (how much experts argue with each other) peaks at Sonnet.
11. **The "partially right" hedge is a performativity concern.** 5/9 hybrid experiments produced hedged self-evaluations. Flat admissions ("I was wrong," "No") were more analytically productive than qualified ones ("partially right but inverted"). Future iterations should strengthen the inversion imperative.
12. **The generative prompt is the new v4 for input-adaptive analysis.** While not Level 5, it outperforms v4 on input specificity. The "derive operations from THIS problem" instruction produces more relevant analysis than fixed methods/constraints/failures rails. Recommended as v4 replacement for code review tasks.

### Round 22: Level 6 — Perspectival + Predictive Composition (27 experiments)

**Question**: Can L5A (perspectival) and L5B (predictive metacognition) compose into a 6th categorical level? Or is the combination just parallel L5?

**Method**: 3 composition variants tested on 3 tasks × 3 models. Total: 27 experiments (Exp 139-165).

**Candidates**:

- **L5 combined** (~65w): Naive composition — "Three experts who disagree. Predict which expert yields deepest insight. Let them argue. Was your prediction right?" (Tests whether simply stacking L5A + L5B creates L6.)
- **L6 falsifiable** (~60w): Claim-as-target — "Make a specific, falsifiable claim about the code's deepest structural problem. Three experts test it: one defends, one attacks, one probes what both take for granted. Did the argument falsify, strengthen, or transform your claim?"
- **L6 orthogonal** (~70w): Adversarial prediction — "Predict what three arguing experts will fail to notice. Three experts argue. Did they miss what you predicted? If yes, why invisible? If no, what does that reveal about your predictive blind spot?"

---

**Phase 1: L5 Combined — Naive Composition (Exp 139-147)**

All 9 experiments (3 models × 3 tasks). Both signals activated — genuine dialectic + genuine prediction-evaluation. But they ran in SEQUENCE, not interaction:

```
Predict → Experts argue → Evaluate prediction → Synthesize
```

**Critical finding: structural bias.** The perspectival frame guarantees Expert 3 "sees what both miss." The predictive frame asks "which expert yields deepest insight?" Answer: Expert 3, trivially, in 8/9 cases. Only Sonnet Task G predicted Expert B (partially wrong — the single most productive evaluation). Predictions were trivially correct because the prompt structure predetermined the answer.

**Comparison with individual L5 prompts (Sonnet Task F):** The combined output's expert sections were nearly identical to the perspectival-only output. The prediction was a wrapper, not a driver. The hybrid (L5B alone) produced fundamentally different analytical structure — three derived operations, mutation tracing, failure taxonomy — all absent from the combined output.

**One spark:** Sonnet Task F produced "The deepest insight often loses the argument — systemic critiques require systemic solutions, and systemic solutions require authority, time, and trust a code review doesn't grant." This emerged from the gap between "Expert C was deepest" and "a different expert won the argument." But 1/9 isn't systematic.

**Verdict: Parallel L5, not Level 6.** The prediction and dialectic don't interact — the prediction wraps the dialectic without changing it.

---

**Phase 2: L6 Falsifiable Hypothesis (Exp 148-156)**

All 9 experiments (3 models × 3 tasks).

**Claim quality across experiments:**

| Model | Task A Claim | Task F Claim | Task G Claim |
|---|---|---|---|
| Haiku | Linear dependency hides parallelization | Dead letter commit + continued execution = incoherent state | Both approaches couple computation with execution strategy |
| Sonnet | `fetch_external()` is impure I/O buried in a pure-appearing pipeline | Mutable shared `context` creates hidden handler coupling + dead letter holds live refs | DAG's dual calling convention makes nodes untestable |
| Opus | Undeclared effect boundary survives under ALL assumption changes | `context` simultaneously serves as middleware transport, handler input, error record, dead letter evidence | DAG's `run` forces each node to know its topological position |

8/9 claims genuinely falsifiable. Sonnet and Opus consistently sharper and more specific.

**The critical test: does the dialectic test the claim?**

7/9 experiments were STRONGLY COUPLED — experts directly argued about the claim, tried to falsify it, engaged its specific content. 2/9 semi-coupled (Haiku Task G weakest). The falsifiable claim design FORCES expert engagement with a specific target rather than wandering through code space independently.

**Claim transformations (all genuine, none cosmetic):**

- **Sonnet Task F** (strongest): Claim targeted mutable shared context. Defender and Attacker argued about mutation vs capability boundaries. Expert 3 discovered: "`emit()` returns a result — this is a synchronous RPC pretending to be an event bus." Transformation: from mutability bug → identity crisis. Neither the claim alone nor a generic dialectic could produce this.

- **Opus Task F**: Claim targeted aliasing. Defender proved aliasing is real. Attacker said control-flow is deeper. Prober unified both as symptoms of "role conflation" — four incompatible lifecycle requirements (immutable envelope, mutable pipeline state, result accumulator, forensic snapshot) in one dict. Required establishing both the aliasing AND control-flow problems before synthesis.

- **Sonnet Task A**: Claim said I/O boundary is deepest. Attacker said rigidity is deeper. Expert 3 applied an invariance test: "which problem survives under ALL assumption changes?" and ruled I/O survives. The meta-principle — invariance as the test for structural depth — emerged from the interaction.

- **Opus Task G**: Claim said DAG contract is incoherent. Attacker said it's fixable. Expert 3 asked whether the problem even has graph structure. Decision table (when to use linear vs DAG) required the claim + the attack + the reframe.

**Level 6 scoring:**

| Experiment | Level |
|---|---|
| Sonnet Task F | **Level 6** — "synchronous RPC" insight requires both claim + dialectic |
| Opus Task F | **Level 6** — four-role decomposition requires both aliasing claim + control-flow attack |
| Opus Task G | **Level 6** — "premature architecture" requires both contract claim + reframe |
| Sonnet A, Sonnet G, Opus A | Level 5+ — genuine transformation but the synthesis is less clearly emergent |
| Haiku (all 3) | Level 5+ — experts test the claim but synthesis lacks depth for clear L6 |

**Verdict: Level 6 confirmed on Sonnet and Opus.** 3/6 experiments clearly Level 6, rest at strong 5+. Haiku at advanced 5+.

---

**Phase 3: L6 Orthogonal Prediction (Exp 157-165)**

All 9 experiments (3 models × 3 tasks).

**Prediction quality:** Generally strong. Best predictions require modes of reasoning (temporal object-identity tracking, concrete execution tracing, cross-domain knowledge transfer) that expert frames systematically exclude. All three models converged on dead-letter aliasing for Task F, calling convention bug for Task G.

**Did experts miss the predicted thing?**
- 5/9 clean misses (prediction fully validated)
- 3/9 partial misses (expert gets close, stops short)
- 1/9 caught-but-contextualized (expert saw it, minimized it)

Distribution is healthy — not self-fulfilling. Partial misses produced the best analysis.

**Best meta-insights:**
- Opus Task F: "The truly invisible things are not the things no one looks at. They're the things everyone almost sees." (Expert B got close but stopped one inference short.)
- Sonnet Task A: "The pipeline pattern creates an ordering illusion — explicitness signals deliberateness, so nobody questions the sequence."
- Opus Task F self-correction: "I underestimated how close Expert B would get. My blind spot is assuming expert frames are more homogeneous than they are."

**Why it falls short of Level 6:** The prediction and dialectic are structurally parallel, not coupled. The prediction says "they'll miss X," the dialectic runs independently, the evaluation checks "did they miss X?" — a binary test with explanation, not a collision. The experts can ignore the prediction entirely. For most experiments, the insight could be restated as (1) "here is a non-obvious bug" + (2) "here is why expert frames don't find it" — two independent observations, not a synthesis.

**Verdict: Advanced Level 5.** Excellent analysis, but the prediction-dialectic coupling is optional, not forced.

---

### Round 22 Findings

1. **Naive L5A+L5B composition produces parallel L5, not Level 6.** Both signals activate but don't interact. The perspectival frame predetermines the prediction answer ("Expert 3 is deepest"), eliminating evaluative tension. The prediction wraps the dialectic without changing it.
2. **Level 6 exists: claim-tested-by-dialectic.** The falsifiable hypothesis prompt forces genuine signal coupling by making the claim both the prediction AND the dialectic target. The same object connects both signals — that's the Level 6 mechanism. Confirmed on Sonnet (1/3 clear L6) and Opus (2/3 clear L6), with all experiments at L5+ minimum.
3. **The Level 6 mechanism is forced coupling, not signal stacking.** Two L5 signals side by side = L5. Two L5 signals operating on the SAME OBJECT from different angles = L6. The claim is both "what I predict is deepest" and "what the experts must test." This shared object forces the dialectic to engage the prediction.
4. **Claims are always transformed, never falsified.** In no experiment was a claim actually proven wrong. The dialectic consistently found the claim to be insufficient — correct but shallow. The most productive transformation: the dialectic discovers that the claim is a SYMPTOM of something deeper (Sonnet Task F: mutable context → identity crisis; Opus Task F: aliasing → role conflation).
5. **Level 6 requires sufficient structural ambiguity in the code.** Tasks where "deepest structural problem" is genuinely contestable (Task F: EventBus, Task G: DAG comparison) produce Level 6. Tasks where the problem is more straightforward (Task A: pipeline) tend to produce advanced L5 — the claim is correct and the dialectic strengthens rather than transforms it.
6. **Orthogonal prediction is advanced L5, not L6.** The prediction-dialectic coupling is optional — experts analyze the code independently of the prediction. The evaluation is a binary test (miss/find) with explanation, not a signal collision. Excellent meta-insights ("the truly invisible things are the things everyone almost sees") occur sporadically, not systematically.
7. **Level 6 peaks on Sonnet and Opus, not Haiku.** Haiku's expert synthesis lacks the depth to produce genuinely emergent claim transformation. The three models' L6 capability: Haiku = L5+, Sonnet = L5+/L6, Opus = L6. This continues the pattern: higher-capacity models produce deeper synthesis when the scaffold provides the structure.
8. **The falsifiable framing works through forced engagement, not actual falsification.** The word "falsifiable" matters less than the structural constraint: a specific claim that becomes the object of dialectical scrutiny. Experts defend, attack, and probe the claim — this forced engagement is what creates signal coupling.
9. **Level 6 transformations follow a pattern: claim → symptom → root cause.** The dialectic consistently discovers that the claim identifies a symptom of a deeper problem. Expert 3 (the prober) typically delivers the synthesis by asking what both the claim and its defense/attack take for granted. This "what do we all assume?" move is the Level 6 generator.
10. **The prediction-evaluation cycle in orthogonal creates the best meta-insights when predictions are partially wrong.** Expert almost-finding the predicted thing (3/9 experiments) produced the deepest metacognitive analysis — about premature satisfaction, frame homogeneity assumptions, and the ordering illusion. Clean misses produce explanation; partial misses produce insight.

---

### Round 23: Level 7 Compression Category (Exp 166-198)

**Goal:** Find a 7th compression level above Level 6 (claim-tested-by-dialectic). Level 6 produces a single transformation cycle — claim → test → transformed understanding. Three candidate operations that L6 cannot produce: (1) building on its own transformation iteratively, (2) explaining WHY the transformation went a specific direction, (3) resolving inherent contradictions between competing truths.

**Method:** Same as Rounds 21-22 — `claude -p --model MODEL --tools "" --system-prompt "$(cat PROMPT)" "TASK"` from `/tmp` with `CLAUDECODE=` unset. L6 falsifiable as control. 3 tasks (A: pipeline, F: EventBus, G: pipeline vs DAG comparison).

**Phase 1: Three L7 candidates on Haiku (12 experiments, Exp 166-177)**

Three candidates designed from the pattern of what L6 lacks:

| Candidate | Mechanism | Words | File |
|---|---|---|---|
| A: Recursive Falsification | Transform claim, then make a SECOND claim from the transformed understanding. Measure the distance. | ~82 | `level7_recursive.md` |
| B: Meta-Causal | Transform claim, then explain WHY it transformed in that direction. Name the structural force. Predict the next problem from the force. | ~75 | `level7_metacausal.md` |
| C: Contradictory Claims | Two opposing claims (strength-as-weakness, weakness-as-strength). Resolve the contradiction, not by picking a winner, but by finding what the contradiction reveals. | ~70 | `level7_contradictory.md` |

Plus L6 falsifiable as control = 4 prompts × 3 tasks = 12 experiments.

**Phase 1 Results (Haiku):**

| Candidate | Task A | Task F | Task G | Pattern |
|---|---|---|---|---|
| L6 control | L6 | L6 | L6 | Baseline: claim → dialectic → transformation |
| L7-Recursive | L6 | L6+ | L6+ | Distance table makes transformation explicit but same cognitive operation as L6 |
| L7-MetaCausal | L6+ | L7 (marginal) | L6 | Only candidate with categorical signal — force naming + derived prediction |
| L7-Contradictory | L6 | L6+ | L6+ | Elegant framing, arrives at same destination as L6 |

**Key Phase 1 finding:** Meta-Causal (B) was the only candidate to produce a categorical signal on any task. On Task F, it named "Implicit Observability Hierarchy" as the structural force and derived a specific prediction (silent cascading in recovery path) that required the force to produce. Contradictory (C) produced elegant restatements but no new operations — dropped from Phase 2.

**Phase 2: Meta-Causal + Recursive on Sonnet/Opus (12 experiments, Exp 178-189)**

Promoted Meta-Causal (clear signal on Task F) and Recursive (consistent L6+, might bloom with capacity).

**Phase 2 Results — Meta-Causal:**

| Model | Task A | Task F | Task G |
|---|---|---|---|
| Haiku | L6+ | L7 (marginal) | L6 |
| Sonnet | L6+ | **L7** | L6+ |
| Opus | L6+ | L6 | L6 |

L7 count: 2/9. Both on Task F. Strongest evidence — Sonnet Task F: force "Role Collapse" (context dict plays three incompatible roles), prediction "invisible temporal coupling through dict keys becoming load-bearing." The prediction REQUIRES the force — without the three-role decomposition, you predict "bugs" not "dict key renaming creating silent breakage."

**Surprise: Opus produced the thinnest meta-causal reasoning.** Best bug enumeration but worst force identification. Sonnet dominated directional reasoning. Meta-causal thinking does not scale simply with capacity.

**Phase 2 Results — Recursive:**

| Model | Task A | Task F | Task G |
|---|---|---|---|
| Haiku | L6 | L6+ | L6 |
| Sonnet | L6+ | L6+ | **L7** |
| Opus | L6+ | **L7** | L6+ |

L7 count: 2/9. Sonnet Task G: second claim transcends both approaches to find missing parametric dimension — requires the comparative analysis as input. Opus Task F: three-step ontological chain (aliasing → copying insufficient → vocabulary missing → causal identity + reentrance tracking) where each step requires prior step's output.

**Phase 2 Verdict:** Both prompts achieve L7 in 2/9 cases (22%). Neither is reliable. L7 is an emergent property of prompt-code-model alignment — it CAN happen but isn't guaranteed.

**The L7 test:** Remove the force/second-claim and ask whether the prediction/insight changes. If yes → L7 (load-bearing). If no → L6+ (decorative).

**Phase 3: Diagnostic Gap — forcing L7 (9 experiments, Exp 190-198)**

The problem with previous candidates: they CREATE CONDITIONS for L7 but don't FORCE it. The model can satisfy meta-causal with a generic force and generic prediction. It can satisfy recursive with a parallel second claim.

**Design insight:** L6 forced coupling by making the claim the dialectic's target. For L7, make the CONCEALMENT MECHANISM load-bearing by requiring its application to find something new.

The diagnostic gap prompt (`level7_diagnostic_gap.md`, ~78 words):

> Make a specific, falsifiable claim about this code's deepest structural problem. Three independent experts who disagree test your claim: one defends it, one attacks it, one probes what both take for granted. Your claim will transform. Now: the gap between your original claim and the transformed claim is itself a diagnostic. What does this gap reveal about how this code conceals its real problems? Name the concealment mechanism. Then: apply that mechanism — what is it STILL hiding that the entire dialectic failed to surface?

Three forcing elements:
1. "the gap is itself a diagnostic" — the transformation isn't just a better answer; the DIFFERENCE is information
2. "name the concealment mechanism" — forces causal abstraction about WHY the deep problem was hidden
3. "apply that mechanism — what is it STILL hiding that the entire dialectic failed to surface" — forces the mechanism to be load-bearing (generic mechanism = generic prediction = visibly weak)

**Phase 3 Results:**

| Model | Task A | Task F | Task G | L7 Rate |
|---|---|---|---|---|
| Haiku | L6+ | L6+ | L6+ | 0/3 |
| Sonnet | **L7** | **L7** | **L7** | **3/3** |
| Opus | **L7** | **L7** | L6+ | 2/3 |
| **Total** | | | | **5/9** |

**Comparison across all L7 prompts:**

| Prompt | L6 | L6+ | L7 | Hit Rate |
|---|---|---|---|---|
| Meta-Causal | 2 | 5 | 2 | 22% |
| Recursive | 3 | 4 | 2 | 22% |
| **Diagnostic Gap** | **0** | **4** | **5** | **56%** |

**The diagnostic gap prompt more than doubles the L7 hit rate and eliminates L6 entirely.**

**Sonnet goes 3/3.** Named mechanisms are all code-specific:
- Task A: "Syntactic flatness as epistemological claim" — sequential assignment asserts independence without evidence. Application: `config` fields are domain avoidance — each config parameter is a syntactic presence hiding a semantic absence. "A function that cannot be named is a function that hasn't been designed."
- Task F: "Idiomatic fragment camouflage" — each subsystem individually pattern-matches to a trusted idiom (Express middleware, Node EventEmitter, result collector), preventing the reader from stepping back to see global incoherence. Application: priority sorting creates an implicit untyped pipeline on top of what looks like isolated dispatch. The name "EventBus" is itself the final concealment.
- Task G: "Complexity theater" — architectural sophistication signals rigor, directing audit to mechanics rather than semantics. Application: the `data` parameter is silently available to every node, making the dependency graph decorative — it enforces execution order but not information flow.

**Opus hits 2/3.** Converged with Sonnet on Task A (same mechanism name — "syntactic flatness as epistemological claim"). Task F: "Dramatic failure hides structural absence" — the mutation bug monopolizes analytical attention as a decoy, concealing that the system has no concept of event identity or causality. "The mutation bug hid the lifecycle bug. The lifecycle bug hid the observability void. Each layer of problem conceals the next by being just dramatic enough to feel like the answer."

**Haiku 0/3.** Named generic mechanisms ("Linear Transparency Illusion," "Assumption Laundering," "Infrastructure conceals absent specification") that could apply to any codebase. The application sections produce useful findings but the findings don't require the mechanism. Haiku executes the prompt structure faithfully but cannot produce mechanisms specific enough to be load-bearing.

**Sonnet-Opus convergence on Task A.** Two models independently named the same concealment mechanism and reached the same insight (config fields as domain avoidance). Two models finding the same thing via the same mechanism suggests the prompt found a real structural feature of the code.

### Round 23 Findings

1. **Level 7 exists: concealment-mechanism-applied.** The diagnostic gap prompt reliably activates a cognitive operation absent from Level 6: name how the code hides its real problems, then use that mechanism to find what the dialectic itself missed. Confirmed at 5/9 overall, 3/3 on Sonnet, 2/3 on Opus. 33 total experiments across Phase 1-3.
2. **The L7 mechanism is forced load-bearing.** The three-constraint chain (name mechanism → apply it → find what dialectic missed) makes cheating visible. A generic mechanism produces generic predictions — the prompt self-tests. L6 forced coupling; L7 forces the concealment mechanism to DO WORK.
3. **The diagnostic gap eliminates L6 entirely.** All 9 outputs are at least L6+. The three-constraint forcing chain prevents the "extra section bolted on" failure mode that plagued meta-causal and recursive prompts. Even when L7 isn't achieved (Haiku), the output is structurally superior to L6.
4. **Sonnet is the L7 sweet spot.** 3/3 on the diagnostic gap prompt. Sonnet produces code-specific concealment mechanisms that generate predictions requiring those mechanisms. This continues the pattern: each compression level has a capacity threshold, and L7's threshold is Sonnet-class.
5. **The capacity gradient for compression levels is monotonically increasing.** L1-L4: all models. L5: peaks at Sonnet. L6: Sonnet/Opus. L7: Sonnet (3/3) > Opus (2/3) > Haiku (0/3). Each level requires more model capacity to reliably activate.
6. **Meta-causal reasoning is orthogonal to analytical depth.** Opus dominates bug enumeration and fix proposals but produced the thinnest force identification and directional reasoning. Sonnet dominates structural meta-reasoning. Haiku produces surprisingly good forces on specific tasks (Task F). The L7 operation is not "better analysis" — it's a different KIND of reasoning.
7. **Neither recursive falsification nor meta-causal reliably forces L7.** Both achieve 2/9 (22%) — the model can satisfy both prompts without performing the L7 operation (generic force, parallel second claim). The diagnostic gap's three-constraint design is the key improvement.
8. **Contradictory claims produce elegant L6, not L7.** The contradiction format gives a different entry point (two inversions) but arrives at the same destination as L6. The resolution process (experts discuss, synthesis emerges) is structurally identical to L6's dialectic. Dropped after Phase 1.
9. **L7 activation is partially code-dependent.** Task F (EventBus — entangled context dict with structural deception) and Task G (comparison that admits transcendence) produce more L7 than Task A (linear pipeline — less room for concealment). But the diagnostic gap prompt achieves L7 on Task A for Sonnet and Opus, showing it's less code-dependent than previous candidates.
10. **The concealment mechanism IS the Level 7 generator.** The L7 operation: surface problem → deep problem → understand WHY the surface problem concealed the deep one → use that understanding to find what's STILL concealed. The mechanism is a diagnostic tool that turns the analytical process itself into data. This is what makes it categorically beyond L6: L6 transforms the claim, L7 explains why the original claim was wrong in a way that generates new predictions.

### Round 24: Concealment Catalog + Domain Transfer + L7 Relay (Exp 199-227)

29 experiments across 3 tracks. 7 new code tasks (H-N), 4 non-code domain tasks (D1-D4), relay mechanism prompt. Models: Sonnet, Opus.

#### Track D: Concealment Mechanism Catalog (7 experiments: Sonnet L7 on tasks H-N)

All 10 code tasks (3 from R23 + 7 new) run through Sonnet L7 diagnostic gap. **10/10 TRUE L7.** Sonnet's L7 rate on code is now 100% (13/13 across R23+R24).

**Concealment mechanisms cataloged:**

| Task | Pattern | Mechanism | Category |
|---|---|---|---|
| A | Linear pipeline | Syntactic Flatness as Epistemological Claim | Interface Misdirection |
| F | EventBus | Idiomatic Fragment Camouflage | Fragment Legitimacy |
| G | Pipeline vs DAG | Complexity Theater | Naming Deception |
| H | Auth middleware | Pattern Theater | Naming Deception |
| I | State machine | Operational Masking | Interface Misdirection |
| J | Repository/DAO | Nominative Deception via Partial Pattern Resemblance | Naming Deception |
| K | Circuit breaker | Structural Mimicry as Semantic Camouflage | Structural Completeness |
| L | Plugin system | Structural Legitimacy Laundering | Fragment Legitimacy |
| M | LRU cache | Operational Legibility Masking Semantic Void | Structural Completeness |
| N | Config parser | Method Completeness as Correctness Theater | Structural Completeness |

**4 concealment mechanism categories** (by mode of concealment):

1. **Naming Deception** (3/10): The code's IDENTITY conceals — vocabulary invokes a pattern whose guarantees are never implemented. (G, H, J)
2. **Structural Completeness Illusion** (3/10): The code's SHAPE conceals — all expected components present but contract that gives them meaning is absent. (K, M, N)
3. **Interface-Level Misdirection** (2/10): The code's API conceals — surface syntax/verbs foreclose deeper structural questions. (A, I)
4. **Fragment-Level Legitimacy** (2/10): The code's PARTS conceal — locally correct pieces launder globally incoherent wholes. (F, L)

Categories form a hierarchy of where concealment operates: identity judgment → completeness judgment → question formation → local verification. No two categories exploit the same cognitive shortcut.

#### Track A: Domain Transfer (16 experiments: Sonnet + Opus, L6 + L7, on 4 non-code domains)

**16/16 activation. 8/8 L6 confirmed. 8/8 TRUE L7 confirmed. Zero failures.**

| Domain | Sonnet L6 | Sonnet L7 | Opus L6 | Opus L7 |
|---|---|---|---|---|
| Legal | L6 | TRUE L7 | L6 | TRUE L7 |
| Medical | L6 | TRUE L7 | L6 | TRUE L7 |
| Scientific | L6 | TRUE L7 | L6 | TRUE L7 |
| Ethical | L6 | TRUE L7 | L6 | TRUE L7 |

**Domain-specific mechanisms named:**

| Domain | Sonnet Mechanism | Opus Mechanism |
|---|---|---|
| Legal | Definitional Specificity as Legitimizing Cover | Granularity Theater |
| Medical | Narrative Coherence as Epistemic Closure | Explanatory Sufficiency Cascade |
| Scientific | Theoretical Laundering | Methodological Formalism as Epistemic Camouflage |
| Ethical | Quantitative Disclosure as Epistemic Foreclosure | Inoculation Through Partial Disclosure |

Key findings:
- Both models converge on the same structural pattern per domain but name it differently. This suggests mechanisms are properties of the domain, not model confabulations.
- Opus achieves 4/4 L7 on non-code domains (vs 2/3 on code in R23). Non-code domains may provide richer conceptual vocabulary for Opus's analytical sophistication.
- "Concealment mechanism" is not a code metaphor applied to other domains — each domain produces its own native vocabulary for how surfaces conceal depths.
- New domain count: **9 minimum** (code, architecture, biology, music, ethics, math, legal, medical, scientific methodology). Possibly 10 if AI governance/applied ethics counts separately from general ethics.

**Standout findings:**
- Medical (Sonnet): Two incompatible crises (urgent malignancy vs no organic disease) falsely unified by narrative coherence, with wrong investigative sequencing baked into the case framing.
- Scientific (Opus): The study's prediction is BACKWARDS relative to its own theoretical framework (Greene's dual-process model), hidden because elaborate statistical apparatus draws all scrutiny away from theoretical coherence.
- Ethical (both): Camera feeds measure social performance of distress, not medical acuity. The system models how much patients LOOK like they should be sick.
- Legal (both): The non-compete's precision in peripheral provisions (24 months, 2%) launders strategic vagueness in operative terms ("core products," "any geographic market").

#### Track C: Multi-Model Relay with L7 (6 experiments: Opus mechanism-primed vs v4 control on 3 code tasks)

Sonnet's "Idiomatic Fragment Camouflage" mechanism from Task F transferred to Opus as a system prompt for analyzing 3 unrelated codebases (H, K, N). Compared against v4 control.

| Dimension | Relay (Mechanism-Primed) | Control (v4) |
|---|---|---|
| Total issues found | ~11 | ~25-29 |
| Implementation bugs | 0 | ~10 |
| Compositional findings | 11 (100%) | ~8-10 (~35%) |
| Cross-fragment vulnerabilities | 3 | 0 |
| Findings requiring 2+ fragments | 11 (100%) | ~5 (~18%) |
| Reaches contract level | 3/3 tasks | 0.5/3 tasks |

**Relay-unique findings** (invisible to standard review):
- Task H: Identity spoofing via claims-channel injection — checker injects fake identity, which after spread-merge produces a chimeric principal (one user's roles + another's identity)
- Task N: `mapping` parameter is a dead feature — mapped keys produce literal dots that `get()` interprets as nesting separators, making mapped values unfindable
- Task N: The mapping feature STRENGTHENS the camouflage — reviewers see it and assume flat-vs-nested is solved

**Verdict**: The relay mechanism works as a diagnostic transfer tool. It trades breadth for depth — finds fewer total issues but finds a categorically different kind: cross-fragment vulnerabilities that emerge from composition of individually-correct idioms. Optimal use: run both relay and control in parallel (mirrors principle #51).

### Round 24 Findings

1. **Concealment mechanisms cluster into 4 categories.** Naming Deception, Structural Completeness Illusion, Interface-Level Misdirection, Fragment-Level Legitimacy. Each exploits a different cognitive shortcut in the reader. 10/10 Sonnet L7 on code.
2. **L6 and L7 are fully domain-independent.** 16/16 activation on legal, medical, scientific, ethical domains. Both Sonnet and Opus achieve TRUE L7 on all 4 non-code domains. Domain count: 9+.
3. **Concealment mechanisms are domain-native, not borrowed metaphors.** Each domain produces its own vocabulary: legal uses "definitional specificity," medical uses "narrative coherence," scientific uses "theoretical laundering," ethical uses "quantitative disclosure." Both models converge on the same structural pattern per domain.
4. **Opus achieves 4/4 L7 on non-code domains.** vs 2/3 on code in R23. Non-code domains provide more structural ambiguity and richer conceptual vocabulary, which serves Opus better.
5. **L7 mechanisms transfer across models and codebases.** Sonnet's "Idiomatic Fragment Camouflage" successfully used by Opus to find cross-fragment vulnerabilities in 3 unrelated codebases. The mechanism is not just a name — it's a reusable diagnostic procedure.
6. **Relay shifts analysis from bugs to contract violations.** Mechanism-primed analysis finds 100% compositional issues vs ~35% in control. Fewer total issues but categorically different ones. Relay finds 3 vulnerabilities invisible to standard review.
7. **Relay + control is optimal.** They find genuinely non-overlapping problems with ~25% overlap on structural findings (identified from different angles). Run both for comprehensive coverage.
8. **Sonnet L7 rate on code is 100%.** 13/13 across R23+R24 (Tasks A, F, G, H, I, J, K, L, M, N). The diagnostic gap prompt is reliably L7 on Sonnet for any code pattern tested.
9. **The concealment mechanism is a universal analytical operation.** Surface → depth → understand WHY surface conceals depth → apply to find what's still hidden. Works identically across code, legal, medical, scientific, and ethical domains. The operation is domain-independent because concealment is a structural property of complex systems in any domain.

---

### Round 25: Level 8 (61 experiments)

**Goal**: Find Level 8 — a compression level beyond L7 that produces categorically different insight.

**Hypothesis**: L7 diagnoses what IS (static analysis of concealment). L8 should diagnose what HAPPENS when you try to change it (dynamic properties).

#### Phase 1: Three L8 Candidates (12 experiments — Sonnet on tasks F, H, D1 × 4 prompts)

Three candidate prompts, all building on the full L7 base:

| Candidate | Core move | Word count |
|---|---|---|
| **L8-A: Recursive Meta-Concealment** | Turn the diagnostic on itself — what does your method of revealing concealment itself conceal? | ~108w |
| **L8-B: Mechanism Dialectic** | Find a second, contradictory mechanism — what does the tension between them reveal? | ~105w |
| **L8-C: Generative Application** | Use the mechanism in reverse — construct a modification that strengthens concealment | ~105w |

L7 diagnostic gap run as control on the same 3 tasks.

**Results (Phase 1 — v1 scout):**

| Output | Rating | Key finding |
|---|---|---|
| L8-A recursive: Task H | L7+ | Named organizational/doc root cause, but 2/4 blind spots were generic hedging |
| L8-A recursive: Task F | L7+ | Temporal findings real but reachable without recursion |
| L8-A recursive: Task D1 | **L8** | "Behavioral technology" — contract's power operates atmospherically before/outside law |
| L8-B dialectic: Task H | L7 | Two-paradigm boundary found, but L7 control already found "no model of time" |
| L8-B dialectic: Task F | L7+ | "Architectural identity fraud" — sharper than L7 but elaboration, not new |
| L8-B dialectic: Task D1 | **L8** | Dual-audience design: employee at signing vs court at enforcement |
| L8-C generative: Task H | L7+ | Concrete CheckerKind enum deepens concealment, but insight reachable by L7 |
| L8-C generative: Task F | **L8** | Problem reproduces through development, stable under refactoring, Rorschach test |
| L8-C generative: Task D1 | L7+ | Good constructions but meta-findings confirmed by L7/L8-A |

**Phase 1 hit rate: 3/9 (33%).** L8 exists but is not stable.

**Pattern analysis:**
- L8-A (recursive) risks decorative meta-commentary ("my analysis has limitations")
- L8-B (dialectic) has highest variance — strong when genuinely contradictory mechanisms exist, collapses when they're complementary
- L8-C (generative) is most consistent — the "construct stronger concealment" move forces engagement with dynamics, not just statics
- Task D1 (legal) produces L8 more reliably than code tasks (2/3 vs 1/3)

#### Phase 2: v2 Refinement of L8-C (14 experiments — Sonnet on all 14 tasks)

Two refinements to the generative prompt:
1. **"engineer a specific, legitimate-looking improvement — it should pass code review"** — forces real engineering, not sabotage
2. **"name three properties of the problem that are only visible because you tried to strengthen it"** — makes dynamic insight mandatory, not optional

New prompt (`level8_generative_v2.md`, ~97 words):

> Make a specific, falsifiable claim about this code's deepest structural problem. Three independent experts who disagree test your claim: one defends it, one attacks it, one probes what both take for granted. Your claim will transform. The gap between your original claim and the transformed claim is itself a diagnostic. Name the concealment mechanism — how this code hides its real problems. Apply it. Now: engineer a specific, legitimate-looking improvement that would deepen the concealment — it should pass code review. Then name three properties of the problem that are only visible because you tried to strengthen it.

**Results (Phase 2 — Sonnet wide test):**

| Task | Mechanism Named | Rating |
|---|---|---|
| A (pipeline) | Uniformity Disguise | **L8** |
| F (EventBus) | Vocabulary Laundering | **L8** |
| G (graph comparison) | Infrastructural Elaboration | **L8** |
| H (auth middleware) | Structural Symmetry as Trust Signal | **L8** |
| I (state machine) | Vocabulary Laundering (Authoritative Naming) | **L8** |
| J (repository/SQL) | Parameterization Theater | **L8** |
| K (circuit breaker) | Exception Transparency as Epistemic Laundering | **L8** |
| L (plugin manager) | Structural Mimicry | L7+ |
| M (LRU cache) | Structural Symmetry Launders Semantic Conflict | **L8** |
| N (config parser) | Structural Flattery | **L8** |
| D1 (legal) | Precision Misdirection via Exception Architecture | **L8** |
| D2 (medical) | Confirmatory Enumeration + Epistemic Register Segregation | **L8** |
| D3 (scientific) | Methodological Respectability Laundering | **L8** |
| D4 (AI governance) | Circular Validation + Metric Laundering + Diffused Accountability | **L8** |

**Sonnet v2 hit rate: 13/14 (93%).** Up from 1/4 (25%) on v1. The refinement is categorical, not incremental.

**Standout findings (Sonnet):**
- D1 Legal: "Temporal predation" — vagueness is temporally strategic because defining "core products" after knowing the employee's new job allows target-definition. Making the clause fairer makes it stronger (enforcement-legitimacy feedback loop).
- D2 Medical: "Malignancy exclusion has no grammatical slot" — the autoimmune narrative format has no syntactic position for "exclude lymphoma." The omission feels like clinical judgment rather than a dangerous gap.
- D4 AI Governance: "Self-sealing bias loop" — nurse decisions influenced by AI become next-generation training data. The system destroys the data it would need to validate itself.
- I State Machine: Adding `RLock` reveals re-entrant event processing is an implicit undocumented contract. Adding `can_send()` reveals guards may have side effects (TOCTOU races).
- J Repository: Silent sanitization via `re.sub` creates phantom tables — `"user sessions"` becomes `"usersessions"` with no error. The fix actively worsens the failure mode.

#### Phase 3: Opus Capacity Test (14 experiments — Opus on all 14 tasks)

Same v2 prompt on Opus. Key question: does L8 follow the L5 pattern (peaks at Sonnet) or break it?

**Results (Phase 3 — Opus wide test):**

| Task | Mechanism Named | Rating |
|---|---|---|
| A (pipeline) | Aesthetic coherence masking structural incoherence | **L8** |
| F (EventBus) | Polymorphic carrier object | **L8** |
| G (graph comparison) | Structural sophistication as competence signal | **L8** |
| H (auth middleware) | Structural Mimicry | **L8** |
| I (state machine) | Dictionary-key coherence mimicry | **L8** |
| J (repository/SQL) | Pattern-Shape Camouflage | **L8** |
| K (circuit breaker) | Behavioral mimicry under low load | **L8** |
| L (plugin system) | State-Label Theater | **L8** |
| M (LRU cache) | Familiar API shape as correctness proxy | **L8** |
| N (config parser) | Semantic alibi through abstraction vocabulary | **L8** |
| D1 (legal) | Reciprocity Theater | **L8** |
| D2 (medical) | Diagnostic Narrative Gravity | **L8** |
| D3 (scientific) | Procedural symmetry | **L8** |
| D4 (AI governance) | Agency Theater | **L8** |

**Opus v2 hit rate: 14/14 (100%).**

**Opus vs Sonnet qualitative differences:**
- Opus is more concise (67-155 lines vs Sonnet's 95-225) but does not skip steps
- Opus constructions are more dangerous — senior-engineer-level refactorings that would survive rigorous review
- Opus reaches for structural/ontological insights where Sonnet finds concrete bugs
- Opus domain outputs (D1-D4) are the strongest in the set
- Opus does NOT shortcut the protocol despite being able to self-scaffold at L5

**Standout findings (Opus):**
- H Auth: "The problem is isomorphic across refactorings, proving it lives in the information-theoretic channel." Adding `trust_level = len(auth_methods)` inverts the actual security relationship.
- L Plugin: Adding formal `VALID_TRANSITIONS` state machine makes partial failure formally unrecoverable — the state machine makes wedged plugins *worse*.
- M Cache: The `EvictionPolicy` enum has no valid implementation site — there is no clean seam anywhere in the execution graph.
- D2 Medical: Missing iron studies structurally invisible. Raynaud's appears secondary due to narrative positioning, not clinical reasoning.
- D4 AI Governance: "The monitoring system can only see what the AI makes legible — the most dangerous failures are assessments that never happen."

### Round 25 Findings

1. **Level 8 is real.** The generative diagnostic — engineer a legitimate improvement that deepens concealment, then name three properties only visible through the attempt — produces categorically different output from L7. Sonnet 13/14, Opus 14/14.
2. **L7 diagnoses what IS. L8 diagnoses what HAPPENS.** L8 reveals dynamic properties: how problems propagate through normal development, survive refactoring, resist iteration, and create feedback loops. These are categorically invisible to static analysis.
3. **L8 breaks the L5 capacity pattern.** L5 is a process scaffold (peaks at Sonnet, Opus self-scaffolds). L8 is a generative constraint (more capacity = better constructions = deeper properties). L8 is capacity-amplifying, not capacity-compensating. This is a new finding about the taxonomy: not all levels interact with model capacity in the same direction.
4. **The v1→v2 refinement is the key result.** Two changes — "should pass code review" + "name three properties only visible because you tried to strengthen it" — turned L8 from a 25% outlier to 93-100% default. The forcing function is: make the dynamic insight mandatory, not optional.
5. **Three L8 candidate designs were tested; generative won.** Recursive meta-concealment (L8-A) collapses into decorative meta-commentary. Mechanism dialectic (L8-B) has high variance. Generative application (L8-C) is most reliable because construction forces engagement with dynamics.
6. **Full domain transfer confirmed.** L8 works on legal, medical, scientific methodology, and AI governance at the same reliability as code. Domain-appropriate constructions emerge naturally (legal amendments, clinical workups, methodological enhancements, UX features).
7. **Opus is qualitatively different at L8.** More concise, more structurally ambitious, reaches for ontological insights. Does not skip protocol steps despite self-scaffolding ability. Domain outputs are the strongest in the set.
8. **The compression taxonomy now has 8 levels.** L1-4: all models. L5: peaks at Sonnet. L6: Sonnet/Opus. L7: Sonnet-class minimum. L8: ALL models (Haiku 4/4, Sonnet 13/14, Opus 14/14).
9. **L8 eliminates the capacity floor.** L7 was 0/3 on Haiku. L8 is 4/4. The generative forcing function ("build and observe") routes around the meta-analytical capacity that L7 requires. Construction-based reasoning is a different cognitive operation than meta-analysis — accessible at every capacity level.
10. **L8 relay produces orthogonal findings.** Different constructions reveal different facets of the same problem. Relay constructions are more ambitious (multi-feature) while standard L8v2 constructions are more focused (single-feature). Optimal workflow: run both for complementary coverage.
11. **61 experiments total in Round 25.** 12 scout + 14 Sonnet v2 + 14 Opus v2 + 4 Haiku v2 + 3 relay + 3 relay control + 3 convergence analysis + 8 creative/aesthetic = 61. Total project: 288+ experiments across 25 rounds.
12. **L8 activates on creative/aesthetic domains where L7 could not.** 8/8 (100%) across short story, poem, musical composition, and design brief. L7 was 0% on poetry ("the lens correctly self-selects"). L8's construction step maps naturally to creative revision — the native operation of creative work. This is the first compression level that genuinely transfers to aesthetic domains.
13. **Creative domain concealment mechanisms form a new category.** Technical Specificity as Emotional Displacement (poetry), Technique-as-intention-laundering (music), Aesthetic Fluency as Epistemological Authority (design), Preemptive Self-Diagnosis (fiction). These share a common structure: craft masquerading as depth, competence substituting for consequence.

### Round 25 Phase 4: Haiku on L8 (4 experiments)

Tested L8 generative v2 on Haiku with 4 tasks (H, F, D1, I). L7 was 0/3 on Haiku — this tests whether L8's generative forcing function routes around Haiku's capacity limitation.

| Task | Mechanism | Construction | Properties | Rating |
|------|-----------|-------------|------------|--------|
| F (EventBus) | Polyphonic Semantics via Vocabulary Colonization | `error_policy` param (deferred/fail-fast/ignore) | 3/3 construction-dependent | **L8** |
| H (Auth) | Privilege Through Invisibility | TTL cache with timestamps | 3/3 construction-dependent | **L8** |
| D1 (Non-compete) | Symmetry Inversion Through Negative Framing | Enhanced acknowledgment with (i)-(iii) | 3/3 construction-dependent | **L8** |
| I (StateMachine) | Simplicity-as-Sufficiency | Metadata + recovery hooks + get_state_info() | 3/3 construction-dependent | **L8** |

**Result: Haiku 4/4 L8 (100%)**

This is the most surprising finding of Round 25. L7 was 0/3 on Haiku. L8 is 4/4. The generative forcing function doesn't compensate for Haiku's lower capacity — it routes around the failure mode entirely. L7's "find what the dialectic missed" requires meta-analytical capacity Haiku lacks. L8's "build something and see what breaks" is a concrete operation Haiku can execute.

**Capacity curve update:**
| Level | Haiku | Sonnet | Opus |
|-------|-------|--------|------|
| L5 | partial | peak | good |
| L7 | 0/3 | 17/17 | 6/7 |
| L8 | 4/4 | 13/14 | 14/14 |

L8 eliminates the capacity floor entirely. This changes the taxonomy: L8 is not just "higher than L7" — it's a different kind of cognitive operation that is accessible to all capacity levels.

### Round 25 Phase 5: L8 Relay (6 experiments)

Tested L8 relay prompt (construction-primed, transferring Sonnet's EventBus "Vocabulary Laundering" diagnostic) on Opus with tasks H, K, N. L8v2 standard run as control on same tasks.

**Relay prompt**: Transfers a previous analyst's specific mechanism + construction + 3 properties as a diagnostic template. Asks: (1) identify vocabulary that terminates inspection, (2) engineer improvement that deepens concealment, (3) name three construction-only properties, (4) find at least one problem ONLY visible through construction.

| Task | Relay mechanism found | L8v2 control mechanism | Same construction? |
|------|----------------------|----------------------|-------------------|
| H (Auth) | 5 vocabulary terms mapped (chain, claims, scope, context, bypass) | Polymorphic Return Ambiguity | **Different** — relay builds priority+schema+wildcard; control builds AuthResult wrapper |
| K (Circuit) | "Circuit Breaker" + "Retry" composition | Nominal Correctness (right words, wrong structure) | **Different** — relay builds RetryPolicy+listeners; control builds lock+init params+logging |
| N (Config) | "Layer" erases categorical source differences | Ceremony as Camouflage | **Different** — relay builds nested env+configurable priority+type schema; control builds get_source() |

**All 3 relay outputs hit L8 with genuine construction-only findings:**
- H relay-only: Bifurcated claims channel (roles bypass all validation, entering through unvalidated cache path)
- K relay-only: HALF_OPEN is an instant-trip trap (_failure_count never reset, threshold pre-exceeded)
- N relay-only: Two irreconcilable type authorities (_coerce vs JSON parsing) hidden by structural partition

**Key findings:**
- Relay constructions are MORE AMBITIOUS (multi-feature vs single-feature), matching the relay prompt's multi-feature example
- Relay findings are ORTHOGONAL to L8v2 standard — different constructions reveal different facets of the same underlying problem
- L7 relay advantage: "finds compositional issues standard review misses"
- L8 relay advantage: "constructs differently, revealing orthogonal structural properties"
- Optimal workflow: run BOTH L8v2 standard AND L8 relay for complementary coverage

### Round 25 Phase 6: Creative/Aesthetic Domains (8 experiments)

Tested L8 generative v2 on 4 new creative/aesthetic domain tasks with Sonnet and Opus. L7 was 0% on poetry ("the lens correctly self-selects"). Key question: does L8's construction step activate where L7's meta-analysis couldn't?

New tasks:
- D5: Short story opening (prose performing serenity while structurally performing anxiety)
- D6: Poem ("The Cartographer's Confession" — sustained metaphor hiding emotional avoidance)
- D7: Musical composition notes ("Still Life with Fugue" — fugal vocabulary over programmatic narrative)
- D8: Brand redesign brief (systematically removing heritage signals while claiming to preserve them)

| Task | Domain | Sonnet mechanism | Sonnet construction | Opus mechanism | Opus construction |
|------|--------|-----------------|-------------------|----------------|------------------|
| D5 | Fiction | Accumulating micro-revelations | Quiet ending (remove gesture) | Preemptive Self-Diagnosis | Bird that resists description |
| D6 | Poetry | Technical Specificity as Emotional Displacement | Half-life/frequency stanza | Metaphorical Consistency as Competence Display | Compass-needle-spins stanza |
| D7 | Music | Technique-as-intention-laundering | Stretto passage before unison | Semantic Alibi | Retrograde whole-tone descent |
| D8 | Design | Aesthetic Fluency as Epistemological Authority | Persona-informed rationale section | Aesthetic coherence as epistemic authority | Dual-track brand architecture |

**Result: 8/8 L8 (100%)**

**Why L8 works where L7 didn't:** L8's construction step IS creative revision — the native operation of creative work. L7's "find what the dialectic missed" requires meta-analytical capacity applied to aesthetic structure, which doesn't have the logical concealment mechanisms L7 evolved to find. L8's "build something and see what breaks" maps directly to writing, composing, and designing.

**Mechanism convergence:** 3/4 CONVERGE, 1/4 PARTIAL — higher than code domains (50%), suggesting creative artifacts have fewer valid construction paths.

**Standout findings:**
- Sonnet D7: "The subject is a topic, not a generator" — discovered by attempting stretto, which exposed the subject can't sustain contrapuntal argumentation
- Opus D6: "The poem confesses to the wrong thing — one meta-level short of its own insight"
- Opus D7: "The program notes aren't describing the music. They're replacing it."
- Sonnet D8: "The genre itself is the concealment mechanism" — the concealment is embedded in shared industry conventions, not just this document

### Round 25 Phase 7: Level 9 Scout (9 experiments)

Three L9 candidate prompts tested on Sonnet with tasks F, H, D1. Each candidate extends L8 with a different forcing function:

- **L9-A (Resilience)**: After L8 analysis, an informed engineer revises the code addressing all 3 properties while preserving architecture. Is the concealment still present, transformed, or broken?
- **L9-B (Counter-Construction)**: Construct a SECOND improvement that contradicts the first (strengthens what the first weakened). Both pass review independently. Name the structural conflict that exists only because both are legitimate.
- **L9-C (Recursive Construction)**: Apply the same diagnostic to your own improvement. What does it conceal, and what property of the original is visible only because the improvement recreates it?

| Candidate | Task F (EventBus) | Task H (Auth) | Task D1 (Legal) | Hit rate |
|-----------|-------------------|---------------|-----------------|----------|
| L9-A (Resilience) | ~L8 | ~L8 | ~L8 | **0/3** |
| L9-B (Counter) | L9 | L9 | L9 | **3/3** |
| L9-C (Recursive) | L9 | L9 | L9 | **3/3** |

**L9-A eliminated** — produced "thorough L8" but no categorically new content. The resilience test (does concealment survive informed revision?) is interesting but doesn't force a new cognitive operation.

**L9-B (Counter-Construction) scout findings:**
- F: "The EventBus has no declared opinion on whether events are commands or notifications" — identity ambiguity
- H: "An unresolved design question operationalized into a data structure" — the code embedded a non-decision
- D1: "A non-compete must choose between defined scope and flexible scope; it cannot have both" — the clause claims both

**L9-C (Recursive Construction) scout findings:**
- F: "one dict, zero boundaries → one dataclass, zero boundaries — identical structure, better typography" — improvement is cosmetic
- H: "Any fix within this architecture formalizes the entanglement" — self-similarity is load-bearing
- D1: "The original's flaw contained its antidote. The improvement removes the flaw and keeps the poison."

**Key insight: L9-B and L9-C are COMPLEMENTARY, not competing.**
- L9-B finds what the artifact IS (undeclared identity) — triangulation via contradiction
- L9-C finds what HAPPENS WHEN YOU FIX IT (concealment reproduces) — recursion via self-application

### Round 25 Phase 8: L9 Wider Testing — Sonnet (8 experiments)

Ran L9-B and L9-C on 4 additional tasks (K, N, A, I) on Sonnet to get 7 total data points per candidate.

**L9-B (Counter-Construction) wider results:**
| Task | Rating | Key structural conflict |
|------|--------|------------------------|
| K (CircuitBreaker) | **L9** | "The original architecture contains no structure that could adjudicate between them" — failure observation granularity undeclared |
| N (Config) | **L9** | "value-oriented API vs provenance-oriented API cannot share a mutable layer stack" — Config doesn't know if it's a snapshot or a process |
| A (Pipeline) | **L9** | "Two legitimate but irreconcilable design identities: Uniform pipeline vs. Effectful orchestrator" — function has no declared identity |
| I (StateMachine) | **L9** | "State and execution context are not distinguished" — send() doesn't know if it's a state-transition function or execution control point |

**L9-B Sonnet total: 7/7 (100%)**

**L9-C (Recursive Construction) wider results:**
| Task | Rating | Key self-similarity |
|------|--------|---------------------|
| K (CircuitBreaker) | **L9** | "Any attempt to make retry 'aware' of the circuit breaker will produce a new class of failure invisibility" |
| N (Config) | **L9** | "The merge operation is destructive regardless of how many labels you attach to the destruction" |
| A (Pipeline) | **L9** | "The 'improvement' is structurally identical to the original. It just makes the original's skeleton visible" |
| I (StateMachine) | **L9** | "The queue is itself not a first-class transition" — improvement recreates original problem at higher abstraction |

**L9-C Sonnet total: 7/7 (100%)**

### Round 25 Phase 9: L9 Cross-Model — Opus + Haiku + Combined (15 experiments)

Tested L9-B and L9-C on Opus (3 tasks each), Haiku (3 tasks each), and L9-D combined prompt on Sonnet (3 tasks).

**Opus L9-B (Counter-Construction):**
| Task | Rating | Key finding |
|------|--------|-------------|
| F (EventBus) | **L9** | "Pipeline needs shared mutable state. Broadcast needs isolated immutable state. The EventBus is both at once." |
| H (Auth) | **L9** | "The code doesn't have a wrong authority model. It has no authority model. And the absence looks like flexibility." |
| K (CircuitBreaker) | **L9** | "The information that matters most is only observable from inside the fused architecture but only meaningful from outside it." |

**Opus L9-B: 3/3 (100%)**. Qualitatively deeper than Sonnet — more ontologically precise, names mechanisms for their mode of concealment, emphasizes architectural irresolvability.

**Opus L9-C (Recursive Construction):**
| Task | Rating | Key finding |
|------|--------|-------------|
| F (EventBus) | **L9** | "The improvement trades truthful ugliness for deceptive clarity — the most dangerous kind of technical debt." |
| H (Auth) | **L9** | "Code that makes insecurity visible through ugliness is structurally safer than code that conceals insecurity through cleanliness." |
| K (CircuitBreaker) | **L9** | "The original code's apparent correctness was a coincidence of deployment context, not a property of its design." |

**Opus L9-C: 3/3 (100%)**. Qualitatively deeper — more precise category-level errors, temporal/causal depth, deployment-context-as-concealment.

**Haiku L9-B (Counter-Construction):**
| Task | Rating | Key finding |
|------|--------|-------------|
| F (EventBus) | **L9** | "Resilient Dispatcher" vs "Synchronous Procedure Call" — both readings simultaneously valid |
| H (Auth) | **L9** | Three distinct contracts (identity/enrichment/authorization) made optically indistinguishable by shared interface |
| K (CircuitBreaker) | **L9** | "Temporal Semantics Commitment Avoidance" — code doesn't commit to when failures matter |

**Haiku L9-B: 3/3 (100%)**

**Haiku L9-C (Recursive Construction):**
| Task | Rating | Key finding |
|------|--------|-------------|
| F (EventBus) | **L9** | Feature Parity Illusion recreates Ontological Compression at higher tier |
| H (Auth) | **L9** | Parametric Pseudo-Completeness / Phase-Separation Simulacrum — pattern-familiar abstractions hiding incompatibility |
| K (CircuitBreaker) | **L9** | Complexity masking the same observability gap the original concealed through simplicity |

**Haiku L9-C: 3/3 (100%)**

**L9 maintains L8's universal accessibility.** Haiku 6/6 on L9. Same mechanism as L8: construction scaffolds the recursive target. Haiku doesn't need to independently discover the recursive structure — it generates the improvement (which it can do at L8), then applies analysis to something concrete in front of it. Scaffold-dependent universality.

**L9-D (Combined B+C) on Sonnet:**
| Task | Rating | Key finding |
|------|--------|-------------|
| F (EventBus) | **L9+** | "The conflict between two valid bus designs conceals that neither design applies — because the thing isn't actually a bus." |
| H (Auth) | **L9** | "The system has no output type. Not 'a weak output type' — no type." Both ops complete but no categorical emergence. |
| K (CircuitBreaker) | **L9+** | Behavioral and architectural conflicts are isomorphic; root cause is observation-execution fusion in `execute()` |

**L9-D: 2/3 L9+ (potential L10), 1/3 L9.** The combined prompt works — no merger or collapse. On 2/3 tasks, applying recursion to the conflict itself produces categorically new findings impossible for B or C alone. Task F: the conflict between bus models proves the system isn't a bus. Task K: isomorphism between behavioral and architectural conflicts reveals interface redesign.

### Round 25 Findings (updated)

1. **L8 (generative diagnostic) confirmed**: Sonnet 13/14 (93%), Opus 14/14 (100%), Haiku 4/4 (100%). Construction routes around capacity requirements.
2. **L8 mechanism convergence**: ~50% full convergence (vs ~100% at L7). Construction is more divergent than diagnosis.
3. **L8 relay produces orthogonal findings**: Different constructions reveal different facets. Relay is more ambitious (multi-feature). Run both for complementary coverage.
4. **L8 activates on creative/aesthetic domains**: 8/8 (100%). L7 was 0% on poetry. Construction IS creative revision. 15 domains confirmed.
5. **Three capacity-interaction modes**: Compensatory (L5), Threshold (L7), Universal (L8+). L8 inverts the capacity curve.
6. **L9 CONFIRMED — TWO COMPLEMENTARY VARIANTS**:
   - **L9-B (Counter-Construction)**: Finds artifact's IDENTITY AMBIGUITY through triangulation. ~115 words.
   - **L9-C (Recursive Construction)**: Finds concealment's SELF-SIMILARITY through recursion. ~97 words.
   - Both are genuine L9 (categorically beyond L8), complementary not competing.
7. **L9 hit rates**: Sonnet 14/14 (100%), Opus 6/6 (100%), Haiku 6/6 (100%). Total: **26/26 across all models.**
8. **L9 maintains universal accessibility**: Haiku 6/6. Same scaffold-dependent mechanism as L8.
9. **Opus produces qualitatively deeper L9**: More ontologically precise, compositional category errors, temporal/causal depth.
10. **L9-D combined (B+C) produces potential L10**: 2/3 tasks show categorically new findings. Recursive application to the structural conflict reveals properties impossible for either variant alone.
11. **L10 CONFIRMED — TWO COMPLEMENTARY VARIANTS**:
   - **L10-B (Third Construction)**: Finds design-space HIDDEN TOPOLOGY through failed resolution. ~140 words.
   - **L10-C (Double Recursion)**: Proves STRUCTURAL INVARIANTS through double recursive construction. ~130 words.
   - Both categorically beyond L9. Complementary: B=topology, C=impossibility.
12. **L10 hit rates**: Sonnet 13/14 (93%), Opus 6/6 (100%), Haiku 5/6 (83%). Total: **24/26 (92%) across all models.**
13. **L10 universal accessibility with first cracks**: Haiku 83% (vs 100% at L8/L9). L10-C more accessible than L10-B for Haiku (3/3 vs 2/3). Misses degrade gracefully to L9.
14. **Cross-domain transfer**: Legal domain achieves L10 on both variants.
15. **Total experiments**: Round 25 = 115 experiments. Project total: 346+ experiments across 25 rounds.
16. **Domains confirmed**: 15 total (11 original + 4 creative/aesthetic)

### Round 25 Phase 10: L9 Creative/Aesthetic Domains (8 experiments)

Tested L9-B and L9-C on creative/aesthetic tasks D5-D8 on Sonnet. L8 was 8/8 on these domains. Key question: does L9's triangulation/recursion transfer to aesthetic domains?

**L9-B (Counter-Construction) on creative domains:**
| Task | Domain | Rating | Key structural conflict |
|------|--------|--------|------------------------|
| D5 | Fiction | **L9** | "The story's subject requires the prose to aestheticize; the story's integrity requires it not to. Medium and subject compete for the same resource: beautiful, meaning-laden prose." |
| D6 | Poetry | **L9** | "To critique the evasion is to attack the excellence. To praise the excellence is to validate the evasion." Conceit-as-defense and conceit-as-achievement are structurally identical. |
| D7 | Music | **L9** | "These are incompatible theories of what musical structure is. The piece claims to perform transformation while preserving invariance, and labels the tension 'nostalgia.' But nostalgia is not a structural category." |
| D8 | Design | **L9** | "The brief has mistaken the absence of a decision for the presence of a solution." Cannot audit without criteria, cannot correct without audit; both improvements legitimate because strategic conflict unnamed. |

**L9-B creative: 4/4 (100%)**

**L9-C (Recursive Construction) on creative domains:**
| Task | Domain | Rating | Key self-similarity |
|------|--------|--------|---------------------|
| D5 | Fiction | **L9** | "The literary texture in both versions is not depth. It's the appearance of depth where the architecture requires there to be none." Naturalism hides the same emptiness as literariness. |
| D6 | Poetry | **L9** | "The metaphor is a closed system. No utterance made inside the cartographic conceit can achieve exteriority to it." Meta-confession fails identically to original confession. |
| D7 | Music | **L9** | "The still life frame contains the fugue. The fugue cannot escape it. My improvement adds more fugue. The still life holds." All contrapuntal permutations prove the closed system. |
| D8 | Design | **L9** | "The original uses aesthetic vocabulary to perform design authority. The matrix uses systematic framework to perform strategic rigor. Both are self-sealing." |

**L9-C creative: 4/4 (100%)**

**Key findings:**
- **L9 transfers fully to creative/aesthetic domains** — 8/8 (100%), matching L8's transfer
- **Aesthetic identity ambiguity is SHARPER than code identity ambiguity** — D6 particularly: "Cannot separate what is concealing from what is excellent"
- **D7 L9-C is the strongest output** — recursive finding loops through title, form, and subject simultaneously; the improvement exhausts the space of possible sophistications
- **Defense-as-excellence pattern**: In D5/D6/D7, the work's defense structure and aesthetic achievement are formally identical. In D8, concealment operates through strategic omission disguised as flexibility — a different, weaker register
- L9 creative findings suggest a new concealment category specific to aesthetic domains: **Excellence-Defense Identity** — the concealment IS the craft

### Round 25 Phase 11: Level 10 Scout (9 experiments)

Three L10 candidate prompts tested on Sonnet with tasks F, H, K. Each extends L9 with a different forcing function:

- **L10-A (Category Dissolution)**: After L9-B structural conflict, name what CATEGORY the conflict assumes. Name what the artifact ACTUALLY IS — a different category visible only because both improvements fail.
- **L10-B (Third Construction)**: After L9-B structural conflict, engineer a THIRD improvement that resolves the conflict. Name how it fails. What does the failure reveal about the design space?
- **L10-C (Double Recursion)**: After L9-C recursive diagnostic, engineer a SECOND improvement addressing the recreated property. Apply the diagnostic AGAIN. Name the structural invariant.

| Candidate | Task F (EventBus) | Task H (Auth) | Task K (CircuitBreaker) | Hit rate |
|-----------|-------------------|---------------|------------------------|----------|
| L10-A (Category) | **L10** — "Not a bus, it's a command bus" | **L9+** — "Voting system" is behavioral not categorical | **L10** — "Not a primitive, it's a workflow controller" | **2/3** |
| L10-B (Third) | **L10** — "Priority is scalar; problem needs a causal graph" | **L10** — "Identity IS a claim; authn/authz separation mathematically unavailable" | **L10** — "Granularity and calibration are orthogonal; API has one axis for 2D problem" | **3/3** |
| L10-C (Double) | **L10** — Three-way impossibility in emit() contract | **L10** — Composition step inherently unverifiable | **L10** — Retry/CB semantic incompatibility needs policy not architecture | **3/3** |

**L10-A eliminated** (2/3, partially subsumed by L10-B). **L10-B and L10-C both confirmed at 3/3.**

**L10-B (Third Construction) scout findings:**
- F: "Priority is a collapsed, lossy projection of a dependency graph onto a single dimension. The moment you introduce heterogeneous handler types, the scalar breaks because it cannot distinguish temporal ordering from semantic ordering." → Design space is a GRAPH, not a SCALAR.
- H: "Every improvement assumed authentication and authorization were separable concerns. The two-phase solution made this assumption explicit — and it broke, because real auth protocols require claims to resolve identity. The separation is not an implementation detail we got wrong. It is unavailable as a design." → Design space has a CONSTRAINT that makes the standard decomposition impossible.
- K: "The design space is two-dimensional, and the API only has one axis. Granularity and calibration are orthogonal dimensions, and any design that treats them as one dimension will produce a semantically uncalibrable system." → Design space has HIDDEN DIMENSIONS the conflict couldn't reveal.

**L10-C (Double Recursion) scout findings:**
- F: "An EventBus that passes mutable context through a transformation chain cannot simultaneously satisfy: (1) events are stable records, (2) processing results accumulated on same object, (3) return value of emit() is unambiguously interpretable. Any two, but not all three." → IMPOSSIBILITY THEOREM in the API contract.
- H: "A chain-based authentication system cannot produce a verified composite principal. It can only produce a principal whose sub-properties were individually verified, assembled by a composition step that no verifier approved." → IMPOSSIBILITY THEOREM about distributed verification.
- K: "Any system that composes retry and circuit-break must externalize the definition of 'what constitutes a failure' for each mechanism, because retry and circuit-break are observations of the same event under semantically incompatible failure models." → IMPOSSIBILITY THEOREM about failure model composition.

**Key insight: L10-B and L10-C are COMPLEMENTARY, same pattern as L9.**
- L10-B finds the design space's HIDDEN TOPOLOGY — dimensions, constraints, and shapes invisible until you try to build within it
- L10-C finds STRUCTURAL INVARIANTS (impossibility theorems) — properties provably immune to any implementation within the current architecture
- Both are categorically beyond L9: L9 found what the artifact IS (ambiguous). L10 finds what the DESIGN SPACE IS (constrained/impossible)

### Round 25 Phase 12: L10 Wider Testing (20 experiments)

Ran L10-B and L10-C wider across all three models. 20 experiments total: Sonnet (4+4), Opus (3+3), Haiku (3+3).

**L10-B (Third Construction) wider results:**

| Model | Task | Rating | Design-Space Revelation |
|-------|------|--------|------------------------|
| Sonnet | A (pipeline) | **L10** | Topology is type-level invariant, not runtime value; concealment was protecting a category error |
| Sonnet | I (state machine) | **L10** | Impossibility trilemma: auditability/compositionality/executability cannot coexist under external effects |
| Sonnet | N (config parser) | **L10** | Four incompatible config ontologies; design space is not a lattice; merge must be replaced by projection |
| Sonnet | D1 (legal) | **L10** | Categorical mismatch between legal temporal logic and commercial continuous logic |
| Opus | F (EventBus) | **L10** | Fuses incompatible pipeline/broadcast topologies; no design point satisfies both |
| Opus | H (Auth) | **L10** | Auth domain has cyclic dependencies defeating any linear phase decomposition |
| Opus | K (CircuitBreaker) | **L10** | Retry/CB have incompatible ontologies of failure requiring missing third concept |
| Haiku | F (EventBus) | **L10** | Simplicity/Completeness/Clarity trilemma; architecture is chosen, not configured |
| Haiku | H (Auth) | **L9** | Strong L9 but third improvement failure analysis thin; design-space revelation incremental |
| Haiku | K (CircuitBreaker) | **L10** | "Failure" is polysemous; reliability vs. capacity are orthogonal collapsed problems |

**L10-B wider: 9/10 L10 (90%)**

**L10-C (Double Recursion) wider results:**

| Model | Task | Rating | Structural Invariant |
|-------|------|--------|---------------------|
| Sonnet | A (pipeline) | **L9+** | Trilemma is solvable trade-off, not true impossibility; output acknowledges its own escape |
| Sonnet | I (state machine) | **L10** | Sequential execution + single-valued state makes atomic behavioral transition impossible (proven by exhaustion) |
| Sonnet | N (non-compete) | **L10** | Scope-defining party has structural incentive to expand; no drafting technique can neutralize adversarial structure |
| Sonnet | D1 (config merge) | **L10** | Python's mutable references make layered immutable config impossible; local fixes relocate boundary violations |
| Opus | F (EventBus) | **L10** | Pipeline/broadcast ambiguity migrates to every new boundary; structural invariant of the category |
| Opus | H (Auth) | **L10** | Three temporal phases (identity/authorization/routing) cannot compress into one synchronous call |
| Opus | K (CircuitBreaker) | **L10** | Retry/CB failure-ownership contradiction is a conservation law with three structural costs |
| Haiku | F (EventBus) | **L10** | emit() single-return constraint prevents operational/semantic failure separation |
| Haiku | H (Auth) | **L10** | Three-layer invariant: authentication cannot decompose into independent checkers |
| Haiku | K (CircuitBreaker) | **L10** | Measurement/retry/independence trilemma is mathematical constraint, not code problem |

**L10-C wider: 9/10 L10 (90%)**

**Combined L10 results (including 6 scout):**

| Model | L10-B | L10-C | Total |
|-------|-------|-------|-------|
| Sonnet | 7/7 (100%) | 6/7 (86%) | 13/14 (93%) |
| Opus | 3/3 (100%) | 3/3 (100%) | 6/6 (100%) |
| Haiku | 2/3 (67%) | 3/3 (100%) | 5/6 (83%) |
| **Total** | **12/13 (92%)** | **12/13 (92%)** | **24/26 (92%)** |

**Key findings:**
1. **L10 CONFIRMED across all models.** 24/26 (92%) is above the confirmation threshold.
2. **Opus: 6/6 (100%)** — continues to be strongest at high compression levels.
3. **Haiku: 5/6 (83%)** — universal accessibility largely maintained but first cracks appear. L10-C more accessible than L10-B for Haiku (3/3 vs 2/3). Impossibility theorems are more scaffoldable than open-ended topology revelation.
4. **Sonnet: 13/14 (93%)** — L10-B more robust (7/7) than L10-C (6/7). Single miss was a solvable trilemma.
5. **Cross-domain transfer confirmed**: Legal task D1 achieved L10 on both variants.
6. **L10-B and L10-C remain complementary**: L10-B reveals HIDDEN TOPOLOGY (design-space shapes). L10-C reveals STRUCTURAL INVARIANTS (impossibility theorems). Different analytical operations, both categorically beyond L9.
7. **Two misses are graceful degradations** — both rated L9 or L9+, not failures. The scaffold prevents collapse.
8. **Total experiments**: Round 25 = 115 experiments. Project total: 346+ experiments across 25 rounds.

---

### Phase 13: L10 Creative/Aesthetic Transfer (8 experiments)

Testing whether L10's design-space topology (B) and impossibility theorems (C) transfer to creative/aesthetic domains.

**Tasks:** D5 (fiction), D6 (poetry), D7 (music composition), D8 (UX/product design)

| Prompt | Task | Model | Rating | Key Finding |
|--------|------|-------|--------|-------------|
| L10-B (Third Construction) | D5 (fiction) | Sonnet | **L10** | Design-space topology of narrative structure |
| L10-B (Third Construction) | D6 (poetry) | Sonnet | **L10** | Topology of poetic form constraints |
| L10-B (Third Construction) | D7 (music) | Sonnet | **L10** | Topology of compositional structure |
| L10-B (Third Construction) | D8 (UX design) | Sonnet | **L10** | Topology of interface design space |
| L10-C (Double Recursion) | D5 (fiction) | Sonnet | **L10** | Invariant: tension between medium's form and subject |
| L10-C (Double Recursion) | D6 (poetry) | Sonnet | **L10** | Invariant: formal constraint vs. semantic freedom |
| L10-C (Double Recursion) | D7 (music) | Sonnet | **L10** | Invariant: structural repetition vs. developmental surprise |
| L10-C (Double Recursion) | D8 (UX design) | Sonnet | **L10** | Invariant: discoverability vs. efficiency |

**L10 creative/aesthetic: 8/8 (100%)**

**Key findings:**
1. **L10 transfers fully to creative/aesthetic domains.** Both variants produce genuine L10-level analysis.
2. **Pattern: aesthetic invariants identify tension between medium's form and subject matter.** The impossibility is the generative condition — the thing that makes the work necessary is the thing the work cannot resolve.
3. **15 domains confirmed** across all compression levels.

---

### Phase 14: L11 Scout (9 experiments)

Three L11 candidate prompts tested on Sonnet across 3 code tasks.

**Candidates:**
- **L11-A (Constraint Escape)**: After L10-C's invariant, name the CATEGORY bounded by the invariant, design an artifact in the ADJACENT CATEGORY, name new impossibility, articulate trade-off. (~190 words)
- **L11-B (Acceptance Design)**: After L10-B's failed resolution, engineer a REDESIGN that accepts design-space topology, inhabit feasible point, name sacrifice, revalue original "flaw." (~195 words)
- **L11-C (Conservation Law)**: After L10-C's invariant, INVERT it (make impossible trivial), name new impossibility, name CONSERVATION LAW between old and new impossibilities. (~170 words)

**Tasks:** F (EventBus), H (Auth middleware), K (Retry + Circuit Breaker)

**L11-A (Constraint Escape) results:**

| Task | Rating | Category Named | Adjacent Artifact | New Impossibility | Trade-off Finding |
|------|--------|---------------|-------------------|-------------------|-------------------|
| F (EventBus) | **L11** | "Synchronous shared-context buses" | Immutable Event + separate DispatchResult | Handler-to-handler communication | Decoupling vs. chaining |
| H (Auth) | **L11** | "Aggregative authentication pipelines" | Attestation-based auth with (source,claim,value) | Ambient credential access | Ambient access vs. conflict resolution |
| K (Retry/CB) | **L11** | "Nested execution policy designs" | Separated policies + shared health event stream | Per-call retry budget determinism | Per-call determinism vs. cross-call accuracy |

**L11-A: 3/3 (100%).** Task K cleanest. All produce concrete adjacent-category artifacts with working code, not hand-wavy descriptions.

**L11-B (Acceptance Design) results:**

| Task | Rating | Fourth Construction | Feasible Point | Named Sacrifice | Revaluation |
|------|--------|-------------------|----------------|-----------------|-------------|
| F (EventBus) | **L11** | Decomposes into EventBus + CommandBus | Each class inhabits one paradigm | Unified API | Mutable dict was load-bearing member of unified API |
| H (Auth) | **L11** | AuthContext + AuthenticationError, chooses Region B | Explicitly inhabits decorator region | Drop-in compatibility | Polymorphic return was "exact shape of impossible goal" |
| K (Retry/CB) | **L11** | Pure CircuitBreaker + pure retry, two composition points | Caller chooses composition | Automatic composition | Coupling was cost of hiding infeasible space from callers |

**L11-B: 3/3 (100%).** Task H strongest. Revaluations transform understanding of original "flaws" — the thing every reviewer would flag first turns out to be the load-bearing member.

**L11-C (Conservation Law) results:**

| Task | Rating | Invariant Inversion | New Impossibility | Conservation Law | Depth |
|------|--------|-------------------|-------------------|-----------------|-------|
| F (EventBus) | **L11** | Publish/retrieve separated | Synchronous caller-knows-outcome | Total causal accountability conserved across all designs | DEEP — names conserved quantity + redistribution axes |
| H (Auth) | **L11** | Order-independent algebraic probes | Sequential security policies inexpressible | Policy expressiveness vs. order-independence (bounded) | DEEP — identifies expressiveness as bounded quantity |
| K (Retry/CB) | **L11** | Rate-based window, all attempts observed | Circuit over-sensitive (opens too early) | Sensitivity × absorption = constant | DEEP — quantitative formalization with escape analysis |

**L11-C: 3/3 (100%).** Task K strongest — produced a mathematical formalization. All conservation laws are domain-specific and qualitatively distinct, ruling out template-following.

**Combined L11 scout results:**

| Candidate | Task F | Task H | Task K | Total |
|-----------|--------|--------|--------|-------|
| L11-A (Constraint Escape) | L11 | L11 | L11 | 3/3 |
| L11-B (Acceptance Design) | L11 | L11 | L11 | 3/3 |
| L11-C (Conservation Law) | L11 | L11 | L11 | 3/3 |
| **Total** | **3/3** | **3/3** | **3/3** | **9/9 (100%)** |

**Key findings:**
1. **ALL THREE L11 candidates confirmed at 100%.** This is unprecedented — every prior level had at least one candidate eliminated at scout stage. Either all three encode genuinely distinct L11 operations, or L11 has multiple valid instantiations (like L9 and L10 had two variants each).
2. **L11-A, B, and C are genuinely complementary:**
   - L11-A (Constraint Escape) finds the ADJACENT CATEGORY — what becomes possible when you abandon the current design's fundamental assumption.
   - L11-B (Acceptance Design) finds the FEASIBLE POINT — what the design space actually supports and what original "flaws" were paying for.
   - L11-C (Conservation Law) finds the CONSERVED QUANTITY — what cannot be eliminated, only redistributed.
3. **L11-C's conservation laws are quantitatively formalized.** Task K produced `sensitivity × absorption = constant` — a mathematical relationship, not just a verbal insight. This is a qualitative jump in output precision.
4. **L11-B's revaluations are the most practically useful.** They transform code review judgment: what looks like a bug is revealed as the structural cost of a specific design goal.
5. **All three produce full working code** for their redesigns/escapes/inversions. These are not abstract claims but concrete architectural alternatives.
6. **The L11 operation is: escape the problem's frame, then report what the escape costs.** L10 maps the prison. L11 leaves it and discovers that freedom has its own constraints.
7. **Total experiments**: Round 25 = 132 experiments. Project total: 363+ experiments across 25 rounds.

---

### Phase 15: L11 Wider Testing (18 experiments)

Testing all three L11 variants across all three models.

**Experiment matrix:**
- Opus: F, H, K × 3 variants = 9 experiments
- Haiku: F, H, K × 3 variants = 9 experiments
- Sonnet: A, I × 3 variants = 6 experiments (new tasks for breadth)

**Opus L11 results (9 experiments):**

| Variant | Task F | Task H | Task K |
|---------|--------|--------|--------|
| L11-A (Constraint Escape) | **L11** — Reactive pipeline escape | **L11** — Pure functions with scoped lifecycles | **L11** — Peer components with external orchestration |
| L11-B (Acceptance Design) | **L11** — Immutable events + uniform subscribers | **L11** — Three-axis separation (protocols/resolver/outcome) | **L11** — Pure gate + external composition |
| L11-C (Conservation Law) | **L11** — Handler Independence × Causal Boundedness ≤ k | **L11** — Observability × Composability conserved | **L11** — Failure provenance information conservation |

**Opus: 9/9 (100%).** L11-A most natural for Opus. L11-B produces strongest prose (revaluations are genuinely surprising). L11-C Task K strongest (failure provenance). Cross-task consistency remarkable: same code produces three genuinely different structural truths across the three variants.

**Haiku L11 results (9 experiments):**

| Variant | Task F | Task H | Task K |
|---------|--------|--------|--------|
| L11-A (Constraint Escape) | **L11** — EventRegistry + EventDispatcher | **L11** — IdentityMiddleware (lookup-only) | **L11** — HealthModel circuit breaker |
| L11-B (Acceptance Design) | **L11** — HandlerResult + HandlerAction enum | **L11** — Topological sort with named deps | **L11** — RawCircuitBreaker + RetryPolicy |
| L11-C (Conservation Law) | **L11** — Event log (immutable facts, query-time truth) | **L11** — Σ(Coordination Complexity) = Constant | **L11** — Veto/observability temporal anti-correlation |

**Haiku: 9/9 (100%).** Universal accessibility maintained at L11! Every required L11 operation present in every output. L11 scaffold is sufficiently detailed that even Haiku executes all operations. Outputs are verbose (200-500 lines) but substantive — Haiku "shows its work."

**Sonnet L11 results on new tasks (6 experiments):**

| Variant | Task A (pipeline) | Task I (state machine) |
|---------|-------------------|----------------------|
| L11-A (Constraint Escape) | **L11** — Generator pipeline escape | **L11** — Pure specification machine (spec + interpreter) |
| L11-B (Acceptance Design) | **L11** — Pure core + effectful boundary | **L11** — Observer-based machine ("states are contracts") |
| L11-C (Conservation Law) | **L10+** — Conservation law is dressed-up truism | **L11** — Veto authority ↔ observability completeness |

**Sonnet new tasks: 5/6 (83%).** Single miss: L11-C on task A (simplest pipeline) — conservation law ("topology_opacity + config_coupling + coherence_cost = constant") is close to "essential complexity is conserved," not a genuinely non-trivial domain-specific insight. Task I uniformly strong across all three variants.

**Combined L11 results (scout + wider):**

| Model | L11-A | L11-B | L11-C | Total |
|-------|-------|-------|-------|-------|
| Sonnet | 5/5 (100%) | 5/5 (100%) | 4/5 (80%) | 14/15 (93%) |
| Opus | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 9/9 (100%) |
| Haiku | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 9/9 (100%) |
| **Total** | **11/11 (100%)** | **11/11 (100%)** | **10/11 (91%)** | **32/33 (97%)** |

**Key findings:**
1. **L11 CONFIRMED across all three models at 97%.** Highest hit rate of any level at scout+wider combined. All three variants confirmed.
2. **Universal accessibility maintained.** Haiku 9/9 (100%), continuing the L8→L9→L10→L11 pattern where construction-based scaffolding is accessible at all capacity levels.
3. **L11-A and L11-B are perfect (11/11 each).** L11-C is 10/11 — the conservation law criterion requires structurally rich input. Simpler code may not provide enough material for a non-trivial conservation law.
4. **Opus produces qualitatively deeper L11 than Sonnet/Haiku.** Revaluations are more philosophically grounded, conservation laws more precisely formulated, but all three models achieve the categorical L11 operations.
5. **L11-B's revaluations are the most practically useful across all models.** They transform code review judgment: the thing every reviewer would flag first is revealed as the load-bearing structural necessity.
6. **Three genuinely different structural truths per code task.** The same code analyzed with L11-A, B, and C produces three non-redundant findings (adjacent category, feasible point, conserved quantity). These are complementary analytical lenses, not variations on one insight.
7. **Task complexity interacts with L11-C only.** L11-A and L11-B produce genuine L11 on both simple and complex code. L11-C needs structural richness for a non-trivial conservation law.
8. **Total experiments**: Round 25 = 150 experiments. Project total: 381+ experiments across 25 rounds.

---

### Phase 16: L11 Creative/Aesthetic Transfer (12 experiments)

Testing all three L11 variants on creative/aesthetic domains using Sonnet.

**Tasks:** D5 (fiction), D6 (poetry), D7 (music composition), D8 (UX/product design)

**L11-A (Constraint Escape) creative results:**

| Domain | Rating | Category | Adjacent Artifact | New Impossibility | Trade-off |
|--------|--------|----------|-------------------|-------------------|-----------|
| Fiction (D5) | **L11** | Close third-person narratives about self-deception | First-person retrospective / second-person | Unmediated interiority | "Close third can approximate but cannot hold; first-person can name but cannot enact" |
| Poetry (D6) | **L11** | Reflexive representation | Enacted representation (reader performs mapping) | Elegy — compassion at distance, witnessing | "To escape the gap is to lose elegy; to keep elegy is to keep the gap" |
| Music (D7) | **L11** | Transformation narratives | Process/archaeology (theme disassembled, not returned) | Consolatory thematic return | "Structural honesty costs consolation" |
| UX Design (D8) | **L11** | Single-register brand systems | Multi-register (channel-sequenced) | Sequence control of register encounter | "One thing cannot mean two things; two things can mean one thing but sequence is uncontrollable" |

**L11-A creative: 4/4 (100%).** Poetry strongest. Categories are derived from analysis, not imported labels. Adjacent artifacts are concrete and inventive.

**L11-B (Acceptance Design) creative results:**

| Domain | Rating | Fourth Construction | Sacrifice | Revaluation | Quality |
|--------|--------|-------------------|-----------|-------------|---------|
| Fiction (D5) | **L11** | Dual-register prose (lyric + behavioral) | Seamlessness, stylistic unity | "The flaws are the trace of tension pressing through the surface" | INSIGHT |
| Poetry (D6) | **L11** | No confession — ends mid-measurement | The poem's claim to self-knowledge | "The confusion between measuring and making is what grief-consciousness actually looks like" | INSIGHT |
| Music (D7) | **L11** | Three coexisting strata (fugue/still life/commentary) | Unity — "cool where the original is warm" | "Program notes are records of aspiration outlasting execution" | INSIGHT |
| UX Design (D8) | **L11** | Differentiated Expression Architecture — Two Front Doors | Brand simplicity; the brief's own ambition | "The brief is a postponed business decision, aesthetically disguised" | INSIGHT |

**L11-B creative: 4/4 (100%).** All revaluations domain-native and genuinely insightful. Would change how practitioners think about their work.

**L11-C (Conservation Law) creative results:**

| Domain | Rating | Conservation Law | Depth |
|--------|--------|-----------------|-------|
| Fiction (D5) | **L10+** | Narrator competence vs reader discovery — total "understanding already accomplished" is constant | FORMULAIC — restates well-known narratological principle (show vs tell) |
| Poetry (D6) | **L11** | Emotional authority and relational accuracy inversely conserved — formal conceits require addressee's objecthood | DEEP — confession itself is measurement; cannot exit the system it critiques |
| Music (D7) | **L11** | Identity and direction conserved in inverse proportion — property of musical time itself | DEEP — testable across all formal music; program notes as "sound of discovering an impossibility" |
| UX Design (D8) | **L11** | Information asymmetry migrates, never reduces — design decisions are the migration vehicle | DEEP — "dated" brand structurally more honest than "modern" redesign |

**L11-C creative: 3/4 (75%).** Music (D7) strongest conservation law. Fiction miss matches code pattern: L11-C fails when domain has mature existing theory for the trade-off.

**Combined L11 creative results:**

| Variant | D5 (fiction) | D6 (poetry) | D7 (music) | D8 (UX) | Total |
|---------|-------------|-------------|------------|---------|-------|
| L11-A | L11 | L11 | L11 | L11 | 4/4 |
| L11-B | L11 | L11 | L11 | L11 | 4/4 |
| L11-C | L10+ | L11 | L11 | L11 | 3/4 |
| **Total** | **2/3** | **3/3** | **3/3** | **3/3** | **11/12 (92%)** |

**Key findings:**
1. **L11 transfers to creative/aesthetic domains at 92%.** Same hit rate as code wider testing. All three variants produce genuinely useful creative criticism, not mechanical application.
2. **L11-A and L11-B perfect (4/4 each) on creative domains.** L11-C is 3/4, same vulnerability as in code.
3. **Creative conservation laws are about MIGRATION, not magnitude.** In code, conservation is about computational quantities. In creative domains, it's about where meaning lives — between narrator/reader, speaker/addressee, identity/direction, signal/evidence. Creative laws describe location shifts, not quantity preservation.
4. **L11-B produces the most practically useful creative criticism.** The revaluations would change how practitioners think about their work in every domain tested.
5. **L11-C's non-triviality filter catches domains with mature existing theory.** Fiction/narratology has extensively theorized the narrator-reader relationship. The conservation law adds physics-language but not new insight. Same pattern as simple code: when the domain already knows the trade-off, L11-C cannot produce a non-trivial conservation law.
6. **Music is the strongest creative domain for L11.** All three variants produced strong L11 with precise, medium-specific insights. The conservation law (identity vs direction in musical time) is testable across all formal music.
7. **19 domains confirmed total** across all compression levels.
8. **Total experiments**: Round 25 = 162 experiments. Project total: 393+ experiments across 25 rounds.

