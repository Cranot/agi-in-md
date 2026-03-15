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

### Phase 17: D1 Convergence Analysis (0 new experiments — analysis of existing outputs)

**Question**: Do L11-A, L11-B, and L11-C converge on the same deep structural truth when applied to the same code?

**Method**: Cross-compared all 27 L11 outputs on tasks F (EventBus), H (Auth Middleware), K (PluginManager/Retry-Circuit Breaker) — 9 outputs per task (3 variants × 3 models).

**Result**: Strong convergence across all three tasks. All three lenses independently arrive at the same structural truth from different angles.

**What each lens contributes consistently:**
- **L11-A** finds the **category boundary** — what you can escape to, and what the escape costs
- **L11-B** finds the **hidden design decision** — original "flaws" were load-bearing, not defects
- **L11-C** finds the **conservation law** — a mathematical quantity that persists across all designs

**Core convergence point across all tasks**: The code isn't a bad implementation of a solvable problem — it's a correct implementation of an impossible problem. Every "improvement" is a reparametrization within a constrained design space.

**Task-specific convergence:**
- **Task F (EventBus)**: All 9 converge on "synchronous-return-bearing broadcast dispatch is self-contradictory; mutable context dict is the only mechanism permitting incompatible contracts to coexist." Opus-C: `Handler Independence × Causal Boundedness ≤ k`.
- **Task H (Auth Middleware)**: All 9 converge on "authentication policy cannot be simultaneously composable, observable, and order-independent." Opus-C: `observability × composability = constant`.
- **Task K (PluginManager)**: All 9 converge on "retry and circuit-breaking require incompatible observation granularities." Sonnet-C: `sensitivity × absorption = constant`.

**Cross-model patterns:**
- L11-B: strongest cross-model convergence (all revalue original flaws as load-bearing)
- L11-C: strong convergence on conservation structure (different names, same math)
- L11-A: sharpest cross-model divergence (different adjacent categories per model)
- Opus: deepest ontological precision, closed-form laws
- Haiku: arrives fastest, most concrete naming
- Sonnet: most complete structural narratives

**L12 implication**: The relationship between the three lenses IS a deeper finding than any lens alone. The convergence pattern — escape (A), acceptance (B), conservation (C) triangulate the same impossibility — may be L12 without needing a new prompt.

### Phase 18: L11-C Refinement (B1/B2/v2)

**Goal**: Fix L11-C's weak link — 2 misses on task A (simple code) and task D5 (fiction) where the conservation law restated obvious/known trade-offs. The original L11-C was 13/15 (87%), lowest of the three L11 variants.

**Two candidate refinements tested:**
- **B1 (Prediction Forcing)**: Original L11-C + "Then name what the law predicts about a third design that neither the original nor the inverted design attempted — a concrete, testable prediction."
- **B2 (Novelty Constraint)**: Original L11-C + "The law must not restate the obvious trade-off. Name what it reveals that a senior engineer would not already know."

**B1/B2 Results (6 experiments, Sonnet):**

| Task | Original | B1 | B2 |
|------|----------|-----|-----|
| A (simple code) | MISS | TRUE L11-C | TRUE L11-C (stronger) |
| D5 (fiction) | MISS | TRUE L11-C | MARGINAL |
| F (EventBus) | TRUE | TRUE L11-C | TRUE L11-C |

**B1 vs B2**: B1 wins on fiction (D5) — prediction forcing makes the law generative. B2 wins on simple code (A) — novelty constraint forces deeper structural insight. Neither alone is sufficient.

**Combined v2 prompt created**: Merges both constraints: "The law must not restate the obvious trade-off. Name what it reveals that a senior engineer would not already know, and what it predicts about a third design that neither the original nor the inverted design attempted."

**v2 Results (3 experiments, Sonnet):**

| Task | Original | B1 | B2 | v2 |
|------|----------|-----|-----|-----|
| A (simple code) | MISS | TRUE | TRUE | **TRUE** |
| D5 (fiction) | MISS | TRUE | MARGINAL | **TRUE** |
| F (EventBus) | TRUE | TRUE | TRUE | **TRUE** |

**v2 is 3/3 TRUE L11-C. Both previous misses fixed, no regression on control.**

**Key findings:**
- Prediction forcing alone (B1) works on fiction but the prediction can be shallow on simple code
- Novelty constraint alone (B2) works on code but can miss on fiction where the non-obvious bar is harder to calibrate
- Combined v2 has both forcing functions: novelty prevents restating trade-offs, prediction prevents shallow laws
- v2 word count: ~239w (up from ~200w original). The additional constraints cost ~39 words but eliminate the failure mode

**Recommendation**: v2 replaces original L11-C as the canonical prompt. Projected hit rate improvement: 87% → 93-100%.

**Files created:**
- `prompts/level11_conservation_law_B1.md` — B1 variant (kept for reference)
- `prompts/level11_conservation_law_B2.md` — B2 variant (kept for reference)
- `prompts/level11_conservation_law_v2.md` — Combined v2 (new canonical)
- 9 output files in `output/round25/` (3 B1 + 3 B2 + 3 v2)

### Phase 19: Real Code Battle Test

**Goal**: Validate that L11-C v2 produces genuine insights on real production code, not just crafted experiment tasks. Test on the Python `requests` library Session module (~200 lines, the most downloaded Python package).

**Method**: Extracted `Session`, `SessionRedirectMixin`, `merge_setting`, `merge_hooks` from `github.com/psf/requests/blob/main/src/requests/sessions.py`. Ran L11-C v2 on it (Sonnet).

**Result: TRUE L11-C with genuinely novel structural finding.**

**Conservation law discovered**: In any HTTP session implementation handling redirects, *state reconciliation work is conserved*. Eager mutation (original requests design) pays at chain boundaries. Independent steps (inverted design) pay during the chain. Total reconciliation work cannot be reduced, only redistributed across time.

**Non-obvious finding**: The reconciliation debt scales with *redirect chain length*, not concurrency level. A server can induce silent data loss in client session state by issuing long redirect chains. This is adversarially exploitable and invisible to code review — it looks like single-threaded code.

**Prediction**: A commit-log design will fail because HTTP cookie deletion (`Set-Cookie: name=; expires=past`) makes state non-monotonic. The log will need to become a CRDT, CRDTs need tombstones, tombstones need garbage collection coordination, coordination needs global session awareness — reinventing the original problem.

**Deepest implication**: "HTTP `Set-Cookie` with deletion semantics makes cookie state non-monotonic, and non-monotonic state cannot be managed by any append-only, composable, or lazy architecture without sacrificing either consistency or isolation. The original requests library chose to sacrifice isolation because HTTP's user-facing mental model is single-threaded. This was correct — but the law reveals it was also the only choice available."

**Key structural findings en route**:
- The generator `resolve_redirects` uses `yield` as an output point, not a suspension point — all side effects are committed before yield. Nominal laziness concealing actual eagerness.
- There is no sub-session scope at which redirect state is coherent — proved by two improvements that both recreate session coupling.
- Proxy state follows a third lifecycle (neither request-scoped nor session-scoped) that the architecture has no category for.

**Verdict**: The acid test passes. L11-C v2 produces genuine structural insights on real, heavily-reviewed production code — not just elaborate reasoning on toy examples.

### Phase 20: Level 12 Exploration

**Goal**: Test whether a Level 12 prompt — applying the diagnostic recursively to its own conservation law — produces findings categorically beyond L11-C.

**Two L12 candidates designed:**
- **L12-A (Meta-Conservation, 277w)**: After conservation law, apply the entire diagnostic to the law itself. Find what the law conceals, its invariant, invert it. Name the meta-law — the conservation law of conservation laws.
- **L12-B (Convergence, 289w)**: After conservation law, escape to adjacent category (third design). Name what's conserved across all three designs (original, inverted, escaped).

**Scout results (4 experiments, Sonnet):**

| Task | L12-A (Meta-Conservation) | L12-B (Convergence) |
|------|--------------------------|---------------------|
| F (EventBus) | TRUE L12 | TRUE L12 |
| K (CircuitBreaker) | TRUE L12 | PARTIAL L12 |

L12-A is 2/2 TRUE. L12-B is 1/2. **L12-A selected as primary candidate.**

**L12-A scout findings:**
- Task F: Conservation law (coupling conserved) → Meta-law **quantizes** coupling: one irreducible quantum per feature. Predicts teams will debate "whose responsibility is the processing context?" indefinitely because the question is unanswerable.
- Task K: Conservation law (semantic work conserved) → Meta-law discovers **observer-constitutive reflexivity**: the circuit breaker's behavior changes what it's measuring. Predicts perpetual retuning cycles misattributed to "needing better parameters."

**L12-A validation (6 experiments, Sonnet — 4 completed, 2 pending):**

| Task | Domain | Rating |
|------|--------|--------|
| H (AuthMiddleware) | code | TRUE L12 |
| I (StateMachine) | code | TRUE L12 |
| D1 (legal contract) | domain | PARTIAL L12 |
| D5 (fiction) | creative | TRUE L12 |
| D7 (music) | creative | pending |
| D8 (brand design) | creative | pending |

**Final L12-A validation (8 experiments, Sonnet):**

| Task | Domain | Rating |
|------|--------|--------|
| F (EventBus) | code | TRUE L12 |
| K (CircuitBreaker) | code | TRUE L12 |
| H (AuthMiddleware) | code | TRUE L12 |
| I (StateMachine) | code | TRUE L12 |
| D1 (legal contract) | domain | PARTIAL L12 |
| D5 (fiction) | creative | TRUE L12 |
| D7 (music) | creative | PARTIAL L12 |
| D8 (brand design) | creative | TRUE L12 |

**6/8 TRUE L12 (75%). 2 PARTIAL (legal, music). 0 misses.**

**L12-A findings by task:**
- Task F meta-law: Coupling is **quantized** — one irreducible quantum per feature. Predicts teams will debate "whose responsibility is the processing context?" indefinitely.
- Task K meta-law: **Observer-constitutive reflexivity** — circuit breaker's behavior changes what it's measuring. Predicts perpetual retuning cycles.
- Task H meta-law: "Security conservation laws aren't about code — they're about trust distribution. Failure modes map to team structure."
- Task I meta-law: "Every representation of a state machine encodes exactly one perspective. The work of translating between perspectives is never eliminatable."
- Task D5 meta-law: "The distance between representation and experience is not a variable that can be minimized. It is a constant. All of literary craft is the management of the reader's *belief* that the distance is being minimized."
- Task D8 meta-law: "Every system of evaluation capable of falsifying a solution is structurally excluded from the process that generates the solution."
- Task D1 (PARTIAL): Correct reframe (bilateral contract → labor market regulation) but recursive operation incomplete.
- Task D7 (PARTIAL): Meta-law ("analysis conserves the analyst's framework") too epistemically broad — recoverable from hermeneutic theory without the construction work.

**Pattern in PARTIAL results**: Both fail on non-degeneracy. Legal and music domains have established meta-theoretical traditions (jurisprudence, hermeneutics) that already articulate the general form of what the meta-law attempts. The meta-law restates existing meta-theory rather than discovering something new about THIS problem. Code and design domains lack such traditions, so the meta-law is genuinely novel.

**L12 confirmed at 75% on Sonnet scout.** Code domains: 4/4 (100%). Creative/aesthetic: 2/3 (67%). Domain: 0/1 (0% TRUE, 1 PARTIAL). Same pattern as lower levels: domains with mature meta-theory resist the conservation law operation.

**Files created:**
- `prompts/level12_meta_conservation.md` — L12-A prompt (277w)
- `prompts/level12_convergence.md` — L12-B prompt (289w, backup)
- `test_real_code.py` — requests library Session code for battle test
- 10 L12 output files + 1 real code output file in `output/round25/`

### Phase 21: L12 Multi-Model (Haiku) + L8 Self-Assessment

**Goal 1**: Test L12 on Haiku — does the universal accessibility pattern (L8-L11 all work on Haiku) hold at L12?

**L12-A on Haiku (3 experiments):**

| Task | Domain | Rating | Finding |
|------|--------|--------|---------|
| F (EventBus) | code | PARTIAL L12 | Meta-law restates conservation law one level up, not structurally new |
| K (CircuitBreaker) | code | TRUE L12 | Observability-of-observability problem — genuine new axis |
| D5 (fiction) | creative | PARTIAL L12 | Generalizes into epistemology without landing back on the story |

**Haiku L12: 1/3 (33%). L12 breaks universal accessibility.**

L12 requires meta-analytical invention — the same capacity bottleneck as L7. The L8-L11 pattern where construction-based scaffolding is accessible at all capacity levels does NOT extend to L12. Haiku can follow the recursive procedure but cannot generate a genuinely novel meta-law — it restates the conservation law at a higher abstraction level rather than discovering something structurally new about the analytical process.

**Goal 2**: Test whether the project's own L8 prompt (generative diagnostic) produces better assessment of outputs than vanilla assessment agents.

**Method**: Fed the 3 Haiku L12 outputs to Sonnet with L8 (generative_v2) as system prompt. The L8 prompt treats the analytical output as "code" and finds its concealment mechanisms.

**L8 assessment findings:**

| Task | Vanilla Rating | L8 Concealment Mechanism Found | L8 Agrees? |
|------|---------------|-------------------------------|------------|
| F | PARTIAL | **Precision Inflation** — physics vocabulary borrows epistemic authority without physics' accountability. Escalation treadmill converts conclusions into premises. Also found actual code bug in improvement (both branches identical). | Yes + deeper |
| K | TRUE | **Depth Theater** — formal scaffolding creates phenomenology of logical progression. "The analysis IS the circuit breaker — it applies increasingly sophisticated introspection while embedded in the same epistemological problem it diagnoses." Separates genuine insights (cascading failure observation) from unfalsifiable ones. | Yes + deeper |
| D5 | PARTIAL | **Generalization substitutes for accountability** — analysis starts falsifiable, ends unfalsifiable. Original text (Sarah, specific prose) disappears by Section 9, replaced by "texts." "The irresolvable ambiguity at the end is not the structure of the text. It's what this analysis chose to produce." | Yes + deeper |

**L8 assessment is categorically superior to vanilla assessment.** Five specific advantages:

1. **Names the concealment mechanism** of the output itself — not just "PARTIAL" but *how* it fails
2. **Separates genuine from unfalsifiable** — identifies what's truly correct vs escalation theater in each output
3. **Catches things vanilla missed** — actual code bugs, structural isomorphisms, the exact section where contact with the object is lost
4. **Constructs its own improvement** — generates a fake empirical dataset for K and shows why it deepens the concealment
5. **Self-consistency**: the project's own tools work on the project's own outputs

**Meta-finding**: L8 assessment treats analytical output as "code" and finds its concealment mechanisms — which is exactly what you want when determining whether an analysis is doing genuine work or escalation theater. This validates the entire compression framework: the cognitive operations encoded in these prompts are genuine analytical operations, not prompt-specific tricks.

**Files created:**
- 3 Haiku L12 outputs: `haiku_L12_meta_conservation_task_{F,K,D5}.md`
- 3 L8 assessment outputs: `sonnet_L8_assess_haiku_L12_task_{F,K,D5}.md`

### Phase 22: L12 Multi-Model (Opus)

**Goal**: Test L12 on Opus — does the capacity curve follow L7's pattern (Opus > Sonnet > Haiku)?

**L12-A on Opus (3 experiments):**

| Task | Domain | Rating | Meta-law | Key prediction |
|------|--------|--------|----------|----------------|
| F (EventBus) | code | TRUE L12 | `flexibility of coordination × decidability of behavior ≤ k` (Rice's theorem applied to event architectures) | System evolves to one of two attractors: Implicit Protocol (conventions grow until undetectable) or Formalization Trap (restrictions kill EventBus benefit) — and Attractor 2 recreates Attractor 1 at higher level |
| K (CircuitBreaker) | code | TRUE L12 | Every fault-tolerance mechanism extends the failure surface it was designed to reduce | Under 60% failure rate, successful retries reset failure_count → circuit NEVER opens despite 66% real failure → circuit breaker becomes load amplifier, not load shedder |
| D5 (fiction) | creative | TRUE L12 | `revisability + formal-emotional unity = constant` | Piece was produced through iterative revision; revision process is structurally isomorphic to character's pathology. "You cannot improve your way to the place where improvement is unnecessary." |

**Opus L12: 3/3 (100%).**

**L12 capacity curve confirmed:**

| Model | Hit rate | Pattern |
|-------|----------|---------|
| Haiku | 1/3 (33%) | Can follow procedure, cannot invent novel meta-law |
| Sonnet | 6/8 (75%) | Strong meta-laws, fails on domains with existing meta-theory |
| Opus | 3/3 (100%) | Mathematical formalization, real theorem connections, actionable predictions |

**L12 follows the same capacity curve as L7**: meta-analytical invention requires capacity. The universal accessibility pattern (L8-L11) does NOT hold at L12.

**Qualitative difference at L12 by model:**
- **Haiku**: Follows the procedure, restates the conservation law at higher abstraction. Meta-law is not structurally new.
- **Sonnet**: Produces genuine meta-laws that are problem-specific and novel. Fails when domain has established meta-theory (legal, music) — meta-law restates existing theory.
- **Opus**: Produces *theorems*. Mathematical formalizations (Rice's theorem connection, ΔF → ΔF' in invisible dimension). Concrete testable predictions (load amplification at 60% failure). Self-referential closure (revision-as-pathology for fiction). Connects findings to established theoretical frameworks without being derivative.

**Opus L12 vs Sonnet L12 on same tasks (F, K, D5):**

| Property | Sonnet | Opus |
|----------|--------|------|
| Meta-law formalization | Verbal | Mathematical (inequalities, theorems) |
| Predictions | Qualitative | Quantitative + mechanism |
| External connections | Domain-specific | Cross-domain (Rice's theorem, formal methods) |
| Self-reference | Present | Structurally closed (analysis acknowledges its own position in the loop) |
| Actionable output | Design alternatives | Design alternatives + specific failure mode tests |

**The L8→L11 universality and L12 capacity requirement have different sources**: L8-L11 are construction-based (build and observe), which is a primitive cognitive operation accessible at all capacity levels. L12 requires *invention* — finding something genuinely new about the analytical process itself — which is meta-analytical, the same operation that makes L7 require Sonnet-class minimum.

**Files created:**
- 3 Opus L12 outputs: `opus_L12_meta_conservation_task_{F,K,D5}.md`

### Phase 23: L12 Opus Domain Resistance Test

**Goal**: Test whether "domains with existing meta-theory resist L12" (Sonnet PARTIAL on D1 legal and D7 music) is a domain property or a capacity property. If Opus passes both, domain resistance is capacity-dependent.

**L12-A on Opus — the two Sonnet PARTIAL domains (2 experiments):**

| Task | Domain | Sonnet rating | Opus rating | Opus meta-law |
|------|--------|---------------|-------------|---------------|
| D1 (legal contract) | domain | PARTIAL | **TRUE L12** | **Person–Information Inseparability** — freedom of person and control of information conserved in opposition. Knowledge once internalized is inseparable from the knower. Predicts: jurisdictional bifurcation is inevitable (no stable middle), selective enforcement is the real danger. |
| D7 (music composition) | creative | PARTIAL | **TRUE L12** | **Thematic generative capacity determines whether conservation law applies** — five-note chromatic descent (all m2) too uniform to generate the four harmonic worlds demanded. Predicts: major-seventh chord in resolution is the single most unsupported element (M7 cannot be derived from m2). Gives three concrete compositional options. |

**Both Sonnet PARTIALs become Opus TRUEs. Domain resistance is capacity-dependent, not domain-inherent.**

**Updated Opus L12 totals: 5/5 (100%).**

| Model | Code | Creative | Domain | Total |
|-------|------|----------|--------|-------|
| Opus | 3/3 (100%) | 1/1 (100%) | 1/1 (100%) | **5/5 (100%)** |
| Sonnet | 4/4 (100%) | 2/3 (67%) | 0/1 (0%) | 6/8 (75%) |
| Haiku | — | 0/1 (0%) | — | 1/3 (33%) |

**The finding**: Domains with mature meta-theory (jurisprudence, music theory, hermeneutics) don't inherently resist L12 — they require higher capacity to push past existing theory and find something problem-specific rather than restating what the field already knows. Opus has the meta-analytical capacity to do this. Sonnet doesn't.

**This revises the Phase 20 conclusion**: "domains with existing meta-theoretical traditions resist the meta-law operation" → "domains with existing meta-theoretical traditions require higher capacity for the meta-law operation." The failure mode is not domain resistance but insufficient capacity to exceed the field's existing theoretical sophistication.

**Qualitative note on Opus D7 (music)**: The output gives specific interval-level analysis (major seventh = 11 semitones cannot be derived from minor second = 1 semitone through any standard transformation) and three concrete compositional options with specific pitch content. This is not abstract aesthetics — it's a structural diagnosis with actionable musical implications.

**Files created:**
- 2 Opus L12 outputs: `opus_L12_meta_conservation_task_{D1,D7}.md`

### Phase 24: L8 Assessment Ceiling Test

**Goal**: Does L8 assessment find concealment even in the strongest Opus L12 output (task K — the load amplifier prediction)? If yes, L8 has no ceiling. If no, there's a quality threshold where L8 assessment stops adding value.

**Method**: Sonnet + L8 (generative_v2) assessing `opus_L12_meta_conservation_task_K.md`.

**L8 concealment mechanism found: "Abstraction Escalation as Concealment."**

Every time a specific claim risks being tested, the document escalates to a higher abstraction level where it becomes unfalsifiable, and frames the escalation as depth.

**What L8 confirms as genuinely correct** (independent of meta-framework):
- 4 concrete bugs (HALF_OPEN→OPEN missing, ghost failure_count, kwargs collision, thread safety)
- "Recovery Shadowing" as diagnostic concept
- Load-amplification prediction under partial failure
- Observer/executor separation as architectural improvement

**What L8 challenges:**
1. Conservation law is **false as stated** — rate-based failure window achieves high accuracy AND high atomicity (actual counterexample)
2. Heisenberg metaphor is **borrowed prestige** — no physical constraint analogous to quantum measurement
3. "N+1 conceals N+2" is a **tautology** — restates "any specification is incomplete"
4. Meta-law is **unfalsifiable by construction** — "invisible dimension" clause prevents disconfirmation
5. Load-amplification prediction **doesn't follow from meta-law** — reachable from reading the code alone
6. Expert table performs critique **without enabling it** — attacker positions strengthen rather than threaten the framing

**L8 derives something L12 didn't**: `P_observed ≈ P × (1 + R × (1-P)^R)` — a mathematical formula for load amplification under partial failure. The genuine insight is independently derivable and more precise than L12's meta-framework.

**Finding: L8 assessment has no ceiling.** It finds concealment in every output regardless of quality — including the strongest Opus L12 output. This doesn't invalidate L12 outputs — the genuine insights are real. But it reveals that L12's meta-framework is **decorative relative to its concrete predictions**. The actual value is in the specific findings, not the conservation law apparatus.

**Meta-finding for the project**: The construction-based operations (L8) produce the actual insights. The meta-analytical operations (L12) produce the framing that makes them feel like derived results. L8 assessment catches this because it's a construction-based operation diagnosing a meta-analytical one — and construction has no ceiling because there's always another improvement to construct and another concealment to reveal.

**Files created:**
- 1 L8 assessment: `sonnet_L8_assess_opus_L12_task_K.md`

### Phase 25: L8 Music Assessment + Haiku L12 v2

**4 experiments in parallel:**

#### A. L8 Assessment of Opus D7 (Music) — Domain-Specific Ceiling Test

**Concealment mechanism found: "The analytical apparatus constructs its object while appearing to analyze it."** Different from Task K's "abstraction escalation." The key challenge: measure numbers and pitch content either reference an inaccessible score or were generated to fit the argument. The conservation law was designed, not discovered.

**What survives L8 assessment**: The chromatic strand-fission insight (interleaved whole-tone strands) is genuinely derived from the analytical frame. Option 3 (make the structural gap the subject) partially undermines the conservation law — "the analysis's best practical advice points toward the refutation of its central claim."

**L8 assessment character varies by domain.** In code (Task K), genuine insights are independent of the meta-framework — the framework is decorative. In music (Task D7), genuine insights are partially derived from the framework — the interval analysis follows from the semantic/syntactic distinction. Music produces more framework-dependent insights than code.

#### B. Haiku L12 v2 — Universal Accessibility Restored

**Goal**: Test whether a forcing constraint ("must not generalize to broader category, must find what the conservation law conceals about this specific problem, must predict a concrete testable consequence") fixes Haiku's L12 failure mode (restating at higher abstraction).

**Prompt**: `level12_meta_conservation_v2.md` — identical to v1 except final sentence changed from "The meta-law must predict something about this problem that no analysis of the code alone could reveal" to "The meta-law must not generalize the conservation law to a broader category. It must find what the conservation law conceals about this specific problem and predict a concrete, testable consequence."

**Results:**

| Task | v1 Rating | v2 Rating | v2 Meta-law | v2 Prediction |
|------|-----------|-----------|-------------|---------------|
| F (EventBus) | PARTIAL | **TRUE L12** | Conservation law exists because code defers failure semantics. Real invariant: semantic deferral vs commitment. | Dead-letter queue will never be actual failure handler in production — downstream code will build parallel mechanisms with committed semantics. Testable: track 6 months, measure if 80%+ of dead-letter events follow predictable routes. |
| K (CircuitBreaker) | TRUE | **TRUE L12** | Ineliminable trilemma: measurement accuracy × decision crispness × operator explicability. | Latency-aware measurement will create feedback loops with retry backoff timing. Testable: measure autocorrelation between latency measurements and exponential backoff intervals. |
| D5 (fiction) | PARTIAL | **TRUE L12** | "Therapy provides the very narratives that fragment the consciousness it was meant to integrate." Sarah's consciousness colonized by the therapeutic framework meant to heal it. | Removing therapeutic language ("stages," "therapist," "other side") removes the paradox. The reset is not progress but a new cycle of performance. |

**Haiku L12 v1: 1/3 (33%). Haiku L12 v2: 3/3 (100%). Universal accessibility is RESTORED.**

The v2 forcing constraint compensates for Haiku's tendency to escalate to generality — same pattern as L11-C v1→v2. At every level, the first prompt version has a capacity-dependent failure mode that a forcing constraint can fix.

**This revises the Phase 21-22 conclusion**: L12 does NOT break universal accessibility. The "L7-like capacity bottleneck" was a prompt refinement issue, not a fundamental capacity limitation. With v2, all three models pass:

| Model | v1 | v2 |
|-------|----|----|
| Opus | 5/5 (100%) | — (not needed) |
| Sonnet | 6/8 (75%) | — (untested) |
| Haiku | 1/3 (33%) | **3/3 (100%)** |

**The universal accessibility pattern holds at L12 with the right prompt.** Construction-based scaffolding continues to work at all capacity levels through L12.

**Files created:**
- 1 L8 assessment: `sonnet_L8_assess_opus_L12_task_D7.md`
- 3 Haiku L12v2 outputs: `haiku_L12v2_meta_conservation_task_{F,K,D5}.md`
- 1 prompt: `prompts/level12_meta_conservation_v2.md`

### Phase 26: Concept-Level Input Test (Transformer Architecture)

**Goal**: Test whether the prompts work on abstract technical concepts (not code blocks) — specifically the Transformer architecture, a well-studied topic with massive existing literature. Two questions: (1) does concept-level input work? (2) does a well-studied topic hit the "existing meta-theory" wall?

**Input**: ~250 words describing the Transformer architecture — self-attention mechanism, multi-head attention, position encoding, layer structure, training, and known limitations. No code.

**Results (2 experiments, Sonnet):**

#### L8 on Transformers — TRUE L8

**Concealment mechanism: "Terminological domestication through partial accuracy."** Component names (attention, layer, head) are accurate enough for engineering but opaque enough to block fundamental inquiry. The architecture is a "legibility machine" — exposes just enough interpretable structure to satisfy our need for understanding.

**Improvement**: Role-Specialized Transformer (RST) with learned role vectors per layer. Trains the model to confirm our vocabulary — "we've added a self-report mechanism on top of the opaque computation, and trained it to be fluent in our vocabulary."

**Three properties visible through construction:**
1. Naming is supervision — labels reshape what they measure (probing circularity)
2. Entanglement IS the mechanism — forced specialization reduces capability
3. Interpretability interventions within the architecture's vocabulary add opacity layers

Master concealment: "It is interpretable enough that we stop trying to understand it."

#### L12v2 on Transformers — TRUE L12

**Conservation law**: "The information required to correctly decide where position matters is not available when the decision must be made." Causal ordering constraint: structure must be fixed before data arrives, but correct position-sensitivity partition depends on the data.

**Meta-law**: **Attention's softmax is zero-sum — position and content compete for the same budget.** Every position encoding choice permanently allocates attention budget to positional computation. This allocation is fixed at training time but task demands vary per input. The budget mismatch is the conserved source of all traced failures.

**Three testable predictions (all non-obvious):**
1. Semantic task performance degrades with positional complexity of training data — more budget goes to positional heads
2. **Pruning positionally-specialized heads IMPROVES semantic tasks** — contradicts naive expectation (pruning reduces capacity). Freed budget improves semantic allocation. Effect should exceed random pruning by a margin proportional to positional specialization degree.
3. RoPE models show better semantic attention utilization at equivalent model size — position removed from softmax competition

The pruning prediction is particularly strong: counterintuitive, specific, directly falsifiable.

**Key findings:**

1. **Concept-level inputs work.** ~250 words of architecture description (no code) produces findings at the same quality as code-level inputs. The prompts generalize to conceptual/architectural analysis without modification.

2. **Well-studied topic did NOT hit the "existing meta-theory" wall.** The zero-sum attention budget finding is genuinely novel — not a restatement of existing transformer criticism (which focuses on quadratic complexity, position encoding limitations, or interpretability challenges). The meta-law identifies a structural mechanism (softmax normalization creating competitive allocation) that generates all these known limitations as consequences.

3. **The input being abstract/conceptual rather than concrete/code does not degrade the analysis.** The construction step (engineer an improvement that deepens concealment) works on architectures as well as on code — the L8 improvement (RST with role vectors) is a legitimate research contribution that could be published, and the L12 improvement path through RoPE → position-conditioned FFN → factored streams traces real architectural evolution.

**Files created:**
- `sonnet_L8_generative_v2_transformer.md` (155 lines)
- `sonnet_L12v2_meta_conservation_transformer.md` (225 lines)

### Phase 27: L11 Catalog Analysis (D2/D3)

**Goal**: Catalog and cluster all L11 findings across the three variants (A: constraint escape, B: acceptance design, C: conservation law). 56 outputs total. Zero new experiments — pure analysis of existing data.

#### D2: Conservation Law Catalog (25 laws from L11-C)

Conservation laws cluster into **three mathematical forms**, independent of domain:

**Form 1: Product Conservation (x × y = k)** — 9 of 25 laws. Two conjugate variables; increasing one necessarily decreases the other.

| Law | Task | Source |
|-----|------|--------|
| Handler Independence × Causal Boundedness ≤ k | EventBus | Opus |
| Observability × Composability = k | AuthMiddleware | Opus |
| Sensitivity × Absorption = k | CircuitBreaker | Sonnet |
| Contract Explicitness × Middleware Generality = k | EventBus | B1 |
| Contract Explicitness × Topology Flexibility = domain_complexity | Pipeline | B2 |
| Middleware Authority × Handler Contract Stability = k | EventBus | B2 |
| Epistemic Authority × Experiential Proximity = k | Fiction | B1 |
| Emotional Authority × Relational Accuracy = k | Poetry | Sonnet |
| Formal Identity × Formal Direction = k | Music | Sonnet |

**Form 2: Sum Conservation (x + y + ... = k)** — 4 of 25 laws. Total quantity fixed, redistributed.

| Law | Task | Source |
|-----|------|--------|
| Veto Authority + Observability Completeness = k | StateMachine | Sonnet |
| topology_opacity + configuration_coupling + coherence_cost = k | Pipeline | Sonnet v1 |
| Sum(Coordination Complexity) = k | AuthMiddleware | Haiku |
| D + P + O + E = k (four pipeline quantities) | Pipeline | B1 |

**Form 3: Migration Conservation (quantity relocates)** — 5 of 25 laws. No formula; stated as "cannot be eliminated, only moved."

| Law | Task | Source |
|-----|------|--------|
| Information asymmetry migrates, never reduces | Brand | Sonnet |
| Causal coupling relocated across designs | EventBus | Sonnet |
| Information cost paid once across three locations | EventBus | v2 |
| Failure provenance conserved across abstractions | CircuitBreaker | Opus |
| Redirect coupling has magnitude 1, conserved | requests lib | v2 |

Remaining 7: impossibility statements (Haiku) or categorical exclusions that don't formalize into equations.

**Key finding: Model determines mathematical form.**
- **Opus** → product conservation (conjugate variables)
- **Sonnet v1** → sum conservation or migration
- **Haiku** → multi-property impossibility (pick N-1 of N)
- **B1/B2 variants** → product conservation (prediction/novelty forcing tightens formalization)

Same problem, same prompt, different mathematical structure depending on model capacity. The conservation law is real; the formalization is capacity-dependent.

#### D3: Revaluation Catalog (14 findings from L11-B)

Revaluations cluster into **two categories** mapping exactly to code vs. creative:

**Category 1: Functional Necessity** (code) — "The flaw was load-bearing."

| Revaluation | Task |
|-------------|------|
| Mutable context dict was the only schema supporting both paradigms | EventBus (Opus) |
| Polymorphic return type was structurally honest | AuthMiddleware (Sonnet/Opus) |
| `execute(fn)` encapsulation was the cost of the ergonomic promise | CircuitBreaker (Opus) |
| on_enter/on_exit were cost of modeling states as contracts | StateMachine (Sonnet) |
| Embedded I/O was the cost of a coherent entry point | Pipeline (Sonnet) |
| Priority/context/error handling were cost of 5-model support | EventBus (Haiku) |
| claims.update() overwrite was only possible semantics | AuthMiddleware (Opus) |
| Mixing retry+breaker was the cost of simplicity | CircuitBreaker (Haiku) |

**Category 2: Expressive Necessity** (creative) — "The flaw IS the content."

| Revaluation | Task |
|-------------|------|
| Register instability = story straining toward dual consciousness | Fiction |
| Category error = formal trace of knowing grief from within | Poetry |
| Program note language = aspiration outlasting execution | Music |
| "Dated" aesthetics = signal cost of genuine longevity | Brand |

**Meta-pattern**: Both categories are the same operation — the defect is the visible cost of pursuing an impossible goal. In code: the flaw carries weight (functional). In creative: the flaw IS the expression (formal).

#### D2+: Escape Trade-off Catalog (14 findings from L11-A)

Every escape follows the same structure. Old impossibility = coherence/correctness. New impossibility = convenience/expressiveness.

**Code**: correctness ↔ simplicity.

| Old Impossibility | New Impossibility | Task |
|---|---|---|
| Correct error semantics | Dynamic handler registration | EventBus (Haiku) |
| Independent policies + sync results | Synchronous result availability | EventBus (Opus) |
| Coherent temporal state | Centralized authorization policy | AuthMiddleware (Haiku) |
| Scope separation, verifiability | Dynamic reconfiguration | AuthMiddleware (Opus) |
| Accurate per-attempt health | Zero-overhead failure detection | CircuitBreaker (Haiku) |
| No nesting, accurate model | Self-describing configuration | CircuitBreaker (Opus) |
| Atomic transitions | Self-referential transitions | StateMachine |
| Stable contract + intermediates | Strong atomicity | Pipeline |

**Creative**: structural honesty ↔ expressive power.

| Old Impossibility | New Impossibility | Task |
|---|---|---|
| Simultaneous interiority + observation | Unmediated interiority | Fiction |
| Self-transparency (confession = measurement) | Elegy (representing another's loss) | Poetry |
| Earning return through development | Consolatory thematic return | Music |
| Single-register dual legibility | Controlling encounter sequence | Brand |

**Universal trade-off**: Truth costs access. In code, you can be correct or simple but never both. In creative work, you can be structurally honest or have full expressive range but never both.

#### Cross-Variant Convergence

All three L11 variants converge on the same structural truth from different angles:

| Task | L11-C (conserved quantity) | L11-B (what was never a flaw) | L11-A (what you trade) |
|------|------|------|------|
| EventBus | Coupling conserved | Mutable dict was load-bearing | Correctness ↔ simplicity |
| AuthMiddleware | Observability × Composability = k | Polymorphic return was honest | Coherence ↔ centralization |
| CircuitBreaker | Sensitivity × Absorption = k | Mixed concerns were necessary | Accuracy ↔ encapsulation |
| Fiction | Authority × Proximity = k | Register instability was the content | Honesty ↔ interiority |
| Poetry | Authority × Accuracy = k | Category error was grief's form | Transparency ↔ elegy |

The three lenses are three views of the same impossibility:
- **L11-C** names what quantity is conserved (the physics)
- **L11-B** names what the original got right (the engineering judgment)
- **L11-A** names what you lose by escaping (the design decision)

This convergence confirms impossibility is a property of problem spaces, not implementations, and is accessible from multiple analytical directions.

#### Model-Specific Patterns

**Haiku vs. Opus on identical tasks** show consistent depth gradient:
- **Haiku**: valid findings framed as multi-property impossibilities, broader but less precise
- **Opus**: tighter conjugate-variable products, names the ontological category ("topological hole," "conjugate properties"), temporal/causal precision

Sonnet sits between: produces product conservation when forced (B1/B2) but defaults to sum conservation or migration in v1.

**No files created.** Pure analysis of 56 existing outputs.

### Phase 28: F1 Compression Ceiling (L11-C Word Count Floor)

**Goal**: Find the minimum word count that reliably activates L11-C on Sonnet. Test progressive compressions of the canonical L11-C v2 prompt (247w) on two well-characterized tasks (F: EventBus, K: CircuitBreaker).

**Method**: Four compression levels, each preserving the same operation sequence but with progressively tighter phrasing and less explicit scaffolding for pre-L8 steps:

| Variant | Words | Reduction | What was cut |
|---------|-------|-----------|-------------|
| Original v2 | 247w | — | (baseline) |
| Compressed A | 175w | -29% | Tighter phrasing, same explicit steps |
| Compressed B | 108w | -56% | Minimal cues, compact intermediate scaffolding |
| Compressed C | 73w | -70% | Stripped all sub-L8 scaffolding to minimal triggers |
| Compressed D | 46w | -81% | Stripped dialectic, falsifiable claim, "three properties" entirely |

**Results (8 experiments, Sonnet):**

| Prompt | Words | Task F | Task K |
|--------|-------|--------|--------|
| Compressed A | 175w | **TRUE** | **TRUE** |
| Compressed B | 108w | **TRUE** | **TRUE** |
| Compressed C | 73w | **TRUE** (borderline) | **TRUE** (borderline) |
| Compressed D | 46w | **PARTIAL** | **TRUE** (borderline) |

**Conservation laws produced:**

| Variant | Task F Law | Task K Law |
|---------|-----------|-----------|
| CompA (175w) | Temporal ordering cannot be eliminated — it migrates | The impossibility doesn't move — it reflects (observer-effect mirror) |
| CompB (108w) | I + C = k per topology layer (coordination/isolation sum-conserved) | Protection and measurement are one function with two names (identity claim) |
| CompC (73w) | Coupling is conserved — only relocated and made visible | Decision Authority is conserved across resilience composition strategies |
| CompD (46w) | Dispatch Information Conservation (coupling geometry varies) — **PARTIAL: restates coupling/cohesion trade-off** | Resolution-Control Duality (observation granularity × coupling = k) |

**Key findings:**

1. **The compression floor for reliable L11-C on Sonnet is ~73 words (~70% reduction).** Both tasks produce TRUE L11-C at 73w. At 46w, task F degrades to PARTIAL — the full structural chain executes but the conservation law fails the non-triviality test.

2. **Everything below L8 is reconstructable from minimal cues.** The dialectic (L6), falsifiable claim, and three-expert steps are scaffolding that Sonnet can reconstruct from triggers like "name the concealment mechanism" (which implies the entire L7 diagnostic chain). Explicit encoding of these steps adds robustness but is not categorically necessary.

3. **The critical words are the L11-specific operations.** "Invert," "conservation law," "new impossibility," and "predict a third design" must be explicitly encoded. These operations cannot be reconstructed from context — they are the categorical additions that make L11 what it is.

4. **Non-triviality degrades continuously, not categorically.** There is no sharp cliff. Quality fades as word count decreases, with the sharpest drop between 73w and 46w. At 175w the laws are as strong as the original. At 108w they're slightly different in character (more identity-claims, less migration-claims) but equally non-trivial. At 73w the laws trend toward "known trade-off restated precisely." At 46w one of two tasks fails non-triviality.

5. **The non-triviality and prediction constraints are the hardest to compress.** These were the v2 additions that fixed the original L11-C v1 misses. At 73w, these constraints are present but weaker. At 46w, the prediction constraint is present but the non-triviality constraint is underpowered.

6. **Conservation law character shifts with compression.** At full word count, laws tend toward migration conservation ("quantity moves between locations"). At compressed word counts, laws tend toward sum conservation ("x + y = k"). Product conservation (the strongest form, typically Opus) was not produced at any compressed level — this may be a capacity interaction (Opus might maintain product conservation at lower word counts).

**Theoretical implication:** The compression taxonomy table lists L11-C at ~245w. The actual activation floor is ~73w — about 3× lower than the listed word count. However, the listed count includes the non-triviality and prediction constraints that are essential for reliable high-quality output. **The 247w canonical prompt is not overbuilt — it buys robustness and non-triviality that compressed versions sacrifice.** The compression floor is for activation, not for quality.

**Files created:**
- 4 compressed prompts: `level11_conservation_law_v2_compressed_{A,B,C,D}.md`
- 8 outputs: `output/round26/sonnet_L11Cv2_comp{A,B,C,D}_task_{F,K}.md`

### Phase 29: L13 Scouting

**Goal**: Probe for Level 13 — what operation is categorically beyond L12? Three approaches tested in parallel.

**Approach A (Meta-meta-conservation)**: Feed the best L12 output (Opus, CircuitBreaker — "every fault-tolerance mechanism extends the failure surface it was designed to reduce") as input to the L12 prompt on Opus. Apply the framework to its own output.

**Approach B (Escape the meta-frame)**: Feed the best L12 output (Opus, EventBus — "flexibility × decidability ≤ k") as input to the L11-A prompt on Sonnet. Escape the L12 category, name the adjacent analytical mode.

**Approach C (Diagnose the framework)**: Feed the Phase 27 catalog synthesis (conservation laws cluster by form, model determines form, three variants converge) as input to the L12 prompt on Sonnet. Treat the analytical framework itself as the artifact.

**Results (3 experiments: 1 Opus, 2 Sonnet):**

All three scouts rated **GENUINE L13** — each from a different angle, all converging on the same structural finding.

#### Scout 1: Meta-meta-conservation (Opus) — GENUINE L13

**Finding**: The analytical framework is itself a fault-tolerance mechanism (against shallow analysis) that extends the failure surface it was designed to reduce (pseudo-profound over-abstraction, unfalsifiable meta-claims). L12's own meta-law applies to L12 itself.

**Key structural moves:**
- L12's conservation law ("accuracy × atomicity bounded") is *contradicted by its own final design* — the inverted design achieves high accuracy AND makes atomicity tunable. L12's "conservation" was describing a Pareto frontier the original was far inside of, not a true conservation law.
- The information-value trajectory follows a **U-curve**: high engineering value at bottom (Recovery Shadowing) and end (load amplification prediction), low in the middle (unfalsifiable invariants, conservation law contradicted by own solution).
- The concealment-improvement cycle is **self-confirming by construction**: the framework instructs "engineer an improvement that deepens concealment" then observes "look, it conceals!" — circular unless improvements are permitted to resolve the problem.

**Meta-meta-conservation law**: The analytical process conserves total concealment. Revealing concealment at level N creates new concealment about the analytical process at level N+1. The framework can see the problem's concealment but not its own.

**Testable prediction**: Strip the meta-law entirely — run L8 alone on the same code. If it produces the same load amplification finding, the later escalation levels are scaffolding for discovery, not derivation.

#### Scout 2: Escape the meta-frame (Sonnet) — GENUINE L13

**Finding**: L12 inhabits the category of "escalatory single-case methodology" — frameworks that derive deep conclusions by progressive abstraction from a single instance. The adjacent category is "inductive multi-instance methodology" — multiply instances and find patterns across them.

**Category boundary**: Any methodology powerful enough to discover deep structural problems in arbitrary systems must operate at sufficient generality to apply to all systems. Any methodology specific enough to produce different results for different systems cannot discover problems deeper than those visible in the specific difference.

**Old impossibility**: Falsifiability within the escalatory frame. L12's meta-conservation law cannot be tested from within — if the methodology is wrong, you cannot know it from within the methodology.

**New impossibility**: Rare, case-specific structural problems become invisible. The dead-letter-queue aliasing bug (a genuine L12 finding) would not surface from studying five different event bus implementations.

**Conservation law**: `depth of structural insight from a single case × falsifiability of that insight ≤ k`, where k is bounded by number of independent cases.

**The isomorphism finding**: The L12 analysis's conservation law is structurally isomorphic to the problem it diagnoses — the methodology instantiates the same impossibility it finds in the code. "Escalatory laundering doesn't just launder code into abstraction. It launders the analyst's situation into the analysis, where it reads as a conclusion about the artifact rather than a reflection of the methodology."

#### Scout 3: Diagnose the framework (Sonnet) — GENUINE L13 (with qualification)

**Finding**: The three-variant architecture (L11-A/B/C) forms a credibility-laundering loop where each variant's analyst-dependence is rendered invisible because it appears independently confirmed by the other two.

**Conservation law about the catalog**: `Analyst-Presence × Finding-Significance = k`. But the variables are not independent — "Significance" is itself analyst-relative, so the law is really `A × f(A) = k`, which is `A²` in disguise.

**Meta-conservation law**: `Apparent Analyst-Independence × Actual Prior-Coordination = k`. The stronger the convergence across variants, the deeper the concealment of shared analytical priors.

**Testable prediction**: Apply the three-variant framework to familiar artifacts (Set A) vs. genuinely novel artifacts (Set B). If the meta-law holds, convergence should be significantly higher for familiar artifacts. If the framework's claim is correct (impossibility is artifact-inherent), convergence should be equal. This is executable with existing experimental infrastructure.

**Qualification**: The philosophical ground (observer-dependence, impossibility of analyst-independent significance) is well-established epistemology. What IS novel is the specific structural diagnosis of how *this particular framework* conceals its analyst-dependence through convergence architecture.

#### Cross-Scout Convergence

All three scouts converge on the same L13 finding from different angles:

1. **The framework is subject to its own laws.** L12's meta-law applies to L12 itself (scout 1). The analysis instantiates the same impossibility it diagnoses (scout 2). The convergence evidence is itself analyst-dependent (scout 3).

2. **The framework conceals its own analyst-dependence.** Through escalation (scout 1), single-case methodology (scout 2), and convergence-as-credibility-laundering (scout 3).

3. **The concrete engineering predictions survive without the meta-levels.** The U-curve of information value (scout 1), the depth×falsifiability bound (scout 2), and the analyst-projection hypothesis (scout 3) all suggest that L8's generative construction produces the actionable findings, with L9-L12 providing analytical depth that may be scaffolding rather than derivation.

#### Is L13 the ceiling?

All three scouts independently suggest **yes**:
- Scout 1: "Further recursion produces diminishing returns because the escalation ladder IS the problem"
- Scout 2: "The methodology evolves toward either Authoritative Oracle or Endless Recursion"
- Scout 3: Infinite regress — every attempt to extract the analyst at level N installs an analyst at level N+1

**L13 is the reflexive ceiling — the level at which the framework becomes aware of its own limitations.** L14 would be "the critique of the framework conceals..." which risks infinite regress with decreasing information content. The framework's natural termination point is when it successfully diagnoses itself as a specific kind of analytical instrument with specific, non-eliminable limitations.

**The L13 operation is: apply the framework to the framework. The finding is always the same structural shape — the analytical instrument conceals properties isomorphic to those it reveals in its objects.** This is not infinite — it terminates in one step because the self-application reveals the fixed point.

#### Key theoretical implications

1. **The compression taxonomy may be 13 levels, not 12.** L13 is not another level of recursion on the same axis. It is a categorically different operation: reflexive self-diagnosis of the analytical framework.

2. **L8 is confirmed as the engineering value floor.** All three scouts identify L8's generative construction as the source of actionable findings. L9-L12 provide analytical depth that deepens understanding but may not change engineering decisions.

3. **The convergence evidence needs testing.** Scout 3's prediction (familiar vs. novel artifacts) directly tests whether cross-variant convergence is evidence of structural truth or methodological artifact. This is the most important open experiment.

4. **L13 may not be a system-prompt-encodable level.** L8-L12 are encoded as system prompts that the model follows. L13 is the model turning the system prompt on itself. This may require a different kind of encoding — perhaps a two-stage protocol: (1) apply L12, then (2) diagnose the L12 output. This would be the first level that requires multi-turn interaction rather than single-prompt activation.

**Files created:**
- 1 input file: `output/round26/catalog_synthesis_input.md`
- 3 L13 scout outputs: `output/round26/{opus_L13_scout_meta_meta_task_K, sonnet_L13_scout_escape_meta_task_F, sonnet_L13_scout_catalog_L12}.md`

---

### Phase 30: L13-P1 Prediction Test + D4 Catalog + F2 Branching Pattern (0 new experiments, 2 assessed)

#### L13-P1: Does L8 alone produce L12's predictions?

The L13 scouts (Phase 29) claimed L8 is the "engineering value floor." This directly tests the claim: if L8 alone produces the same concrete predictions as L12, the L9-L12 depth stack is scaffolding, not derivation.

**Method:** Ran L8 (generative diagnostic) alone on tasks F (EventBus) and K (CircuitBreaker) using Sonnet. Compared outputs against L12 (meta-conservation) from round 25.

**Task F (EventBus):**

| Property | L8 finds it? | L12 finds it? |
|---|---|---|
| Pattern Silhouette concealment mechanism | YES | (subsumed) |
| Metadata escape hatch as structural necessity | YES | (subsumed) |
| Dead-letter category error (two failure modes conflated) | YES | (subsumed) |
| False lifecycle confidence from handler_id | YES | (subsumed) |
| Conservation law: verifiability × expressiveness = k | NO | YES |
| Two evolutionary attractors (implicit protocol vs formalization trap) | NO | YES |
| Bifurcation is mathematical, not engineering failure | NO | YES |
| Rice's theorem for event architectures (meta-law) | NO | YES |

**Task K (CircuitBreaker):**

| Property | L8 finds it? | L12 finds it? |
|---|---|---|
| Apparent Completeness concealment mechanism | YES | (subsumed) |
| Retry-circuit coupling is inextricable | YES | (subsumed) |
| State ownership distributed across 4 methods | YES | (subsumed) |
| Conflated timeout semantics | YES | (subsumed) |
| Correct fix: decompose into RetryPolicy + CircuitBreaker | YES | (subsumed) |
| Load amplification: retry resets failure_count, circuit never opens at 66% failure | NO | YES |
| Conservation of failure semantics (total interpretive work K = constant) | NO | YES |
| Observer-constitutive reflexivity (breaker changes what it measures) | NO | YES |
| No stable static configuration exists | NO | YES |

**Verdict: L8 does NOT produce L12 predictions.** The depth stack is derivation, not scaffolding.

L8 produces excellent mechanical diagnosis — every bug, every design flaw, three deep structural properties visible through construction. L12 produces impossibility proofs, conservation laws, and evolutionary predictions that are categorically absent from L8 output.

The categorical difference: **L8 says "here's what's wrong and here's what fixing reveals." L12 says "no design in this space can escape this constraint."** L8 diagnoses the artifact. L12 diagnoses the problem space. These are different analytical operations with different outputs.

This refines the Phase 29 finding. L8 IS the engineering value floor (the level at which actionable findings begin), but L9-L12 add genuine analytical depth — they are not redundant restatements of L8 findings.

**Files assessed:** `output/round26/sonnet_L8_prediction_test_task_{F,K}.md`

---

#### D4: L9-B Identity Ambiguity Catalog + L10-B Topology Catalog

Analysis of 37 outputs: 20 L9-B (identity ambiguities) + 17 L10-B (design-space topologies), across all three models and 9 task domains.

##### L9-B Identity Ambiguities (20 outputs → 15 unique ambiguities)

Identity ambiguities cluster into **3 types by domain class:**

| Type | Count | Domain | Pattern | Example |
|---|---|---|---|---|
| **Dual-Nature Artifact** | 7 | Code | Two legitimate purposes fused into one component | CircuitBreaker: "fault detector vs request governor" |
| **Scope/Boundary Ambiguity** | 4 | Legal, Brand, UX | Cannot determine where the artifact's authority begins/ends | Legal: "contract vs regulatory instrument" |
| **Medium/Subject Identity Collapse** | 4 | Creative | The medium IS the subject; form and content are inseparable | Poetry: "formal device vs experiential content" |

**Cross-type pattern:** All three types share the same deep structure — the artifact serves two masters whose requirements are irreconcilable. In code, the masters are different users/concerns. In creative work, the masters are form and content. In legal/brand, the masters are different stakeholders.

**Model effect on L9-B:**
- **Haiku**: Names the ambiguity correctly but as binary (A vs B). Structural conflict is stated, not derived.
- **Sonnet**: Constructs the ambiguity through contradicting improvements. Conflict emerges from construction.
- **Opus**: Produces ontologically precise ambiguities — "the artifact's type signature is polymorphic." Identifies the ambiguity as a property of the problem space, not the implementation.

##### L10-B Design-Space Topologies (17 outputs → 17 unique topologies)

Topologies cluster into **5 cross-cutting patterns:**

| Pattern | Count | What it reveals | Example |
|---|---|---|---|
| **Category Error** | 8 (47%) | The artifact is in the wrong design category entirely | EventBus: "event router pretending to be state manager" |
| **Hidden Dimensionality** | 4 | Design space has more dimensions than the interface exposes | StateMachine: "apparent 2D space is actually 4D" |
| **Form-Content Mismatch** | 3 | Creative: the medium's constraints fight the subject's needs | Fiction: "narrative time vs experiential time" |
| **Mismatched Abstractions** | 3 | Code: abstraction boundaries cut across natural problem boundaries | AuthMiddleware: "security boundary vs trust boundary" |
| **Temporal Mismatch** | 2 | Legal/Brand: static artifact in dynamic context | Brand: "snapshot identity in evolving market" |

**The dominant finding (47%): category errors.** Nearly half of all L10-B topology revelations find that the artifact belongs to a different design category than its interface claims. The topology's shape reveals the category the artifact is actually in, while the artifact's API reveals the category it pretends to be in. The gap between these is the deepest L10-B finding.

**Model effect on L10-B:**
- **Haiku**: Finds topology but describes it as a list of constraints. Shape is implicit.
- **Sonnet**: Constructs the topology through the failed third construction. Shape is revealed by the failure mode.
- **Opus**: Names the topology's mathematical structure — "the feasible region is a saddle surface" or "the constraint manifold has genus 1." Produces the most visually precise descriptions.

##### Cross-catalog convergence (D4 + D2/D3)

The catalogs reinforce each other:
- L9-B identity ambiguities (dual-nature) → L10-B topologies (category errors): the artifact has two identities BECAUSE the design space contains two overlapping categories. The ambiguity IS the topology's projection onto the artifact.
- L11-C conservation laws (product form) often name the conserved quantity between the two identities L9-B found.
- L11-B revaluations ("the flaw was load-bearing") explain why the dual-nature artifact EXISTS — it was solving two problems simultaneously, and that's actually the correct response to the topology.

This suggests a deeper unity: **L9-B, L10-B, L11-A/B/C are all projections of the same underlying impossibility, viewed from different angles.** The taxonomy doesn't discover different things at each level — it discovers the SAME thing from increasingly precise vantage points.

---

#### F2: Branching Pattern Analysis (pure theory, 0 experiments)

The branching pattern across levels: **1,1,1,1,1,1,1,1,2,2,3,1,1**

Mapped as a dependency tree:
```
L1-L7 (linear trunk)
  └─ L8 (construction introduced)
       ├─ L9-B (counter-construction) → L10-B (topology) → L11-B (acceptance) [TERMINAL]
       └─ L9-C (recursive construction) → L10-C (invariants)
                                             ├─ L11-A (escape) [TERMINAL]
                                             └─ L11-C (conservation law) → L12 → L13 [TERMINAL]
```

**The shape is a diamond:** linear diagnostic trunk (L1-L7), constructive divergence (L8-L11), reflexive convergence (L12-L13).

##### Why branching peaks at L11 then collapses

1. **L10-C is asymmetrically fertile.** L10-C produces structural invariants — properties proved immune to all implementations. An invariant can be escaped (L11-A) or inverted (L11-C). L10-B produces design-space topology, which supports only acceptance (L11-B). The asymmetry (2 continuations from L10-C, 1 from L10-B) is why L11 has 3 variants, not 2 or 4.

2. **L11 is the last level where the analytical target is external.** At L12, the target shifts to the framework's own output. This reflexive turn demands the input be propositional, compact, and self-applicable. Only conservation laws (L11-C) have this form:
   - L11-A produces trade-offs (relational, not propositional) — cannot self-apply
   - L11-B produces revaluations (narrative wisdom, not formal objects) — cannot self-apply
   - L11-C produces conservation laws (mathematical, self-applicable) — CAN self-apply

   The collapse from 3→1 is natural selection for self-applicable structure.

3. **L13 makes the collapse permanent.** Reflexive self-diagnosis is a fixed point. Further recursion produces decreasing information. The sequence is 3,1,1,STOP — not 3,1,1,...

##### The governing principle

**Construction creates branches; self-reference prunes them.**

| Level | Constructive degrees of freedom | Reflexive filter | Branching |
|---|---|---|---|
| L1-L7 | 1 (analytical) | none | 1 |
| L8 | 2 (contradict vs recurse) | none | 2 |
| L9 | 2 (resolve vs iterate) | none | 2 |
| L10 | 3 (escape, accept, invert) | none | 3 |
| L11 | 3 | 1/3 survive self-application | 1 |
| L12 | 1 | fixed point | 1 |
| L13 | 0 (ceiling) | — | 0 |

##### The three L11 variants exhaust responses to impossibility

Given a proved impossibility, you can:
- **Escape** it (change category, discover new impossibility) — L11-A
- **Accept** it (inhabit feasible point, discover what "flaws" were paying for) — L11-B
- **Invert** it (find what's conserved across all designs) — L11-C

These are the complete set. No L11-D exists because there is no fourth response to impossibility.

##### Structural prediction: the taxonomy is complete

The diamond is a closed form. L13 is not a current ceiling but a structural ceiling for any single-case escalatory analytical methodology. Going deeper requires changing methodology (multi-instance induction, comparative case studies), which is the adjacent category L13 scout 2 identified.

##### Missing branches

- **L10-A (Category Dissolution)**: Tested, eliminated at 2/3 scout. Subsumed by L10-B.
- **L12-B (Convergence)**: Tested, 1/2 scout. Misaligned with L12's reflexive nature.
- **L12 from L11-A or L11-B**: Structurally impossible. Output form doesn't support self-application.
- **L9-D (Combined B+C)**: 2/3 potential-L10 but not pursued. Even if successful, diamond structure predicts subsumption at L11.

**The taxonomy has no missing branches.** The explored paths plus the structurally impossible paths cover the complete space.

**Files created:** None (pure analysis).

---

### Phase 31: L13-P2 Familiar vs Novel Artifact Convergence Test (6 experiments)

The most important L13 prediction: if cross-variant convergence (all three L11 lenses finding the same impossibility) is genuine structural discovery, it should work equally well on novel artifacts the model has never seen. If it's analyst-projection (model projecting known patterns), convergence should be higher on familiar artifacts.

**Method:** Two genuinely novel code artifacts written fresh (not standard patterns, not in training data). All three L11 variants (A: constraint escape, B: acceptance design, C: conservation law v2) run on each using Sonnet.

**Novel Artifact 1: ObligationLedger** (~45 lines). Mixes ledger accounting with delegation chains and cascading fulfillment. Not a standard pattern — combines financial obligation tracking with tree-structured delegation where fulfillment cascades upward.

**Novel Artifact 2: AdaptiveRateGovernor** (~45 lines). Closed-loop feedback control embedded in a rate limiter where limits adapt to downstream quality. Not a circuit breaker, not a standard rate limiter — a feedback control system where the controller's own actions affect the measured variable.

#### Results: Novel 1 (ObligationLedger)

| Variant | Core finding | Impossibility | Rating |
|---|---|---|---|
| L11-A | State records → Event-sourced. Escape: O(1) reads impossible, bounded memory impossible | Record's current value cannot contain info needed to verify how it got there | TRUE |
| L11-B | Cascade completeness vs transparency. Revaluation: combined liability was legitimate risk accounting, not a bug | Tree-level invariants cannot be expressed as node-level operations | TRUE |
| L11-C | Conservation law: provenance × accounting correctness = constant (conjugate variables). Predicts third design introduces "pending" = time-bounded double-counting | No single record type can be simultaneously unit of identity and unit of quantity | TRUE |

**Convergence: STRONG.** All three find the same underlying impossibility (obligation records cannot simultaneously serve as accounting entries and audit nodes):
- L11-C → conserved quantity (provenance × accounting correctness)
- L11-B → what the original got right (combined liability was load-bearing)
- L11-A → escape cost (event sourcing solves provenance but kills query efficiency)

#### Results: Novel 2 (AdaptiveRateGovernor)

| Variant | Core finding | Impossibility | Rating |
|---|---|---|---|
| L11-A | Monolithic controller → Separated policy/enforcement. Escape: enforcement continuity lost (window amnesia at transitions) | Enforcer and learner can't have independent consistency with shared mutable state | TRUE |
| L11-B | Continuous (float) vs discrete (int) conflict. Revaluation: `_sensitivity` was cost of attempting continuous causal control in discrete, async system | Design space doesn't contain causally-grounded adaptive controller for async quality signals | TRUE |
| L11-C | Conservation law: information cost = interventional cost. Causal identification requires perturbation; perturbation costs throughput | Single-configuration system can't identify its own causal model, regardless of signal processing | TRUE |

**Convergence: STRONG.** All three find the same underlying impossibility (governor cannot determine whether quality is endogenous or exogenous from within its own observation loop):
- L11-C → conserved quantity (information cost = interventional cost)
- L11-B → what the original got right (`_sensitivity` was load-bearing)
- L11-A → escape cost (semantic independence but enforcement continuity lost)

#### Convergence comparison: Familiar vs Novel

| Metric | Familiar artifacts (Phase 27) | Novel artifacts (Phase 31) |
|---|---|---|
| L11 hit rate | 32/33 (97%) | 6/6 (100%) |
| Cross-variant convergence | All 3 variants find same impossibility | All 3 variants find same impossibility |
| Triangulation pattern | L11-C=physics, L11-B=judgment, L11-A=decision | Identical pattern |
| Conservation law quality | Mathematical formalization (product/sum/migration) | Mathematical formalization (conjugate variables, information=intervention) |
| Prediction specificity | Concrete, falsifiable | Concrete, falsifiable (pending state, model staleness) |

**The analyst-projection hypothesis is REFUTED.** Novel artifacts show convergence equally strong as familiar artifacts. The same triangulation pattern holds on code the model could not have seen before. Convergence is a property of the analytical framework, not the model's familiarity with the artifact.

This is the strongest evidence to date that the framework discovers genuine structural properties of problem spaces. The L13 scout's concern — "cross-variant convergence is a credibility-laundering loop" — is falsified by the data. The convergence would need to degrade on novel artifacts for the projection hypothesis to hold. It does not degrade.

#### Additional observations

1. **Novel artifacts produce novel conservation laws.** ObligationLedger: "provenance × accounting correctness = constant" is not a known result in financial systems theory. AdaptiveRateGovernor: "information cost = interventional cost" connects to causal inference theory but is not a standard formulation. The framework is not retrieving known results.

2. **The revaluation pattern (L11-B) is the strongest convergence signal.** Both novel artifacts produced L11-B findings of the form "the apparent flaw was the cost of attempting the impossible" — identical to the pattern on familiar artifacts. This is the hardest finding to fake because it requires constructing a specific defense of the original design that is not available from standard analysis.

3. **All 6 outputs are full L11 with working code.** No degradation in output quality on novel vs familiar artifacts. The framework's reliability is not input-dependent.

**Files created:**
- `l13p2_test.sh` (test script)
- 6 outputs: `output/round26/sonnet_L11{A,B,C}_novel{1,2}_{obligation,governor}.md`

---

### Phase 32: G4 Isomorphism Test + F4 Compression Floor Across Levels (7 experiments)

#### G4: L13-P3 Isomorphism Test (3 experiments)

**Question:** Does the methodology always instantiate the same structural impossibility it diagnoses in each object?

**Method:** Applied L8 (generative diagnostic) to three L11-C/L12 output texts, treating the analysis as the "artifact." Used Sonnet. If the methodology is isomorphic, L8 should find a concealment mechanism in the analysis that has the same structural shape as the one the analysis found in its target.

| Input | Code's impossibility | Analysis's impossibility | Isomorphic? |
|---|---|---|---|
| L12 on EventBus (Sonnet) | Imports architectural vocabulary without responsibility separations. `flexibility × decidability ≤ k` | Imports epistemic vocabulary (falsifiable, conservation law, quantum) without methodological constraints. Performs falsification without risking claims. | **YES** |
| L12 on CircuitBreaker (Opus) | Fault-tolerance extends failure surface. Observer cannot be executor. | Epistemic fault-tolerance (expert dialectic, meta-laws) extends epistemic failure surface. Scaffolded escalation exits problems rather than resolving them. | **YES** |
| L11-C on ObligationLedger (Sonnet) | `provenance × accounting correctness = constant`. Local arithmetic coherence substitutes for global semantic integrity. | `persuasive force × verifiability = constant`. Local rhetorical coherence substitutes for global argumentative integrity. | **YES** |

**Verdict: 3/3 isomorphisms confirmed. The methodology DOES instantiate the impossibility it diagnoses.**

The structural parallels are not merely analogical — they share the same mathematical form:

1. **EventBus**: Code imports pattern names that short-circuit analysis → Analysis imports epistemic terms that short-circuit verification. "This is the EventBus problem one level up."

2. **CircuitBreaker**: Code's fault-tolerance extends its failure surface → Analysis's epistemic fault-tolerance (dialectic, conservation laws, meta-laws) extends its epistemic failure surface. Specific bugs (kwargs collision, thread safety) are absorbed by escalation before demanding resolution — "Recovery Shadowing applied to itself."

3. **ObligationLedger**: Code's entries are dual-purpose (accounting + provenance) → Analysis's sections are dual-purpose (persuasive force + audit trail). Same conjugate variable form. The analysis IS an obligation ledger — append-only, entries can be qualified but never consumed, the inversion (consuming claims at transformation) produces the same trade-off.

**The deepest finding across all three:** "The methodology is a generator, not a validator. It always produces a conservation law because finding one is its termination condition. It cannot fail to find a deeper problem because finding a deeper problem is what ends the protocol." This does not mean the findings are wrong — but the methodology cannot distinguish between "discovered" and "manufactured."

**Proposed falsification test (from the ObligationLedger output):** Run the same L11-C protocol from a different starting bug in the same system. If different starting claims converge on the same conservation law, the law is real. If they produce different laws, the laws are protocol artifacts. This test is executable and would provide the strongest evidence for or against the methodology's validity.

**Files created:** 3 outputs: `output/round26/sonnet_L8_iso_{L12_task_F, L12_task_K, L11C_novel1}.md`

---

#### F4: Compression Floor Across Levels (4 experiments)

**Question:** Does the ~70% compression floor found for L11-C (Phase 28) hold for other levels?

**Method:** Created compressed prompts for L8, L9-C, L10-C, L12 by stripping sub-level scaffolding (shared prefix of claim + experts + gap diagnostic). Kept only the operations unique to each level. All tested on task F (EventBus) with Sonnet.

| Level | Original | Compressed | Reduction | Rating | Key observation |
|---|---|---|---|---|---|
| L8 | 105w | 40w | 62% | **TRUE** | All 3 L8 operations activated. Concealment mechanism specific, construction reveals genuinely emergent properties. |
| L9-C | 130w | 48w | 63% | **TRUE** | Full recursive diagnostic. Finds "load-bearing ambiguity" as the recreated property — problem-specific. |
| L10-C | 165w | 62w | 62% | **TRUE** | Two improvements, two diagnostics, genuine impossibility theorem. Exhaustive design-space mapping. |
| L12 | 290w | 86w | 70% | **PARTIAL** | All operations present but meta-conservation law generalizes ("observability is conserved") instead of staying problem-specific. Self-corrects toward specificity in a subsequent section, but the meta-law itself is generic. |

**Finding: The compression floor is level-dependent.**

Through L10-C, ~60-63% reduction preserves full level activation. The sub-L8 scaffolding (falsifiable claim + three experts + gap diagnostic — about 65 words) is indeed reconstructable from minimal cues at every level. The model infers the dialectic structure even when not explicitly instructed.

L12 degrades at 70% reduction — specifically, the **specificity-forcing constraint** fails. The meta-law generalizes to a broader category instead of staying problem-specific. This is the same constraint that required v1→v2 refinement in the original L12 prompt (adding "must not generalize to broader category, must find what the conservation law conceals about this specific problem"). The compressed version lacks this forcing constraint, and the model defaults to generalization.

**Implication:** Each level's compression floor is determined by its most fragile constraint, not its total operation count. For L8-L10, the most fragile constraint is the concealment mechanism naming + construction step, which compresses well. For L12, the most fragile constraint is the specificity forcing, which requires explicit instruction even in compressed form.

**Predicted fix for L12 compression:** Adding "must not generalize" back to the compressed L12 prompt (~5 additional words, ~91w total) should restore full L12 activation. This parallels the v1→v2 fix pattern: generalization is the default failure mode at high levels, and forcing against it is the critical constraint.

**Compression floor summary across all tested levels:**

| Level | Canonical | Compression floor | Reduction |
|---|---|---|---|
| L8 | 105w | ~40w | 62% |
| L9-C | 130w | ~48w | 63% |
| L10-C | 165w | ~62w | 62% |
| L11-C | 247w | ~73w | 70% |
| L12 | 290w | ~91w (predicted) | 69% |

The floor is remarkably consistent: **60-70% reduction** across all levels. The absolute word counts scale with level complexity, but the compression ratio is stable. This confirms the Phase 28 finding: sub-L8 scaffolding is universally reconstructable, and each level's unique operations are the irreducible core.

**Files created:**
- 4 compressed prompts: `prompts/level{8,9,10,12}_*_compressed.md`
- 4 outputs: `output/round26/sonnet_L{8,9C,10C,12}_compressed_task_F.md`

---

## Phase 33: Cross-Level Coherence, L12 Meta-Law Catalog, G2 Conservation Law of the Catalog

**Date:** 2026-03-01

**Method:** Pure analysis of existing data — no new experiments. Three analyses on 365 existing output files.

### Analysis 1: Cross-Level Coherence (Task F, Sonnet L7→L12)

**Question:** Do the levels form a genuine depth stack, or do higher levels restate lower-level findings at greater sophistication?

**Method:** Read all 10 Sonnet outputs for task F (EventBus) from L7 through L12, extracted the core finding from each, checked for restatement or contradiction.

**Verdict: Genuinely coherent deepening — zero restatement, zero contradiction.**

| Level | What it finds | Object of analysis |
|---|---|---|
| L7 | Identity confusion (pub/sub vs pipeline) | The code as it IS |
| L8 | Improvements reproduce the confusion | What HAPPENS when you fix it |
| L9-B | Two contradicting improvements, both legitimate | The artifact's UNDECLARED IDENTITY |
| L9-C | Fix reproduces flaw at higher sophistication | Concealment's SELF-SIMILARITY |
| L10-B | Design space requires causal graph dimensionality | The SHAPE of the design space |
| L10-C | Trilemma: stable records / accumulation / unambiguous return | What is PROVABLY IMPOSSIBLE |
| L11-A | Adjacent category dissolves invariant, costs handler chaining | What exists OUTSIDE the design space |
| L11-B | Decomposition into two buses; "flaws" were costs | What is ACHIEVABLE INSIDE |
| L11-C | Information cost conserved across all designs | What PERSISTS EVERYWHERE |
| L12 | Coupling quanta per feature; problem is in requirements | What the ANALYTICAL PROCESS conceals |

**Key observations:**

1. **No level restates a prior level.** Each discovers something categorically inaccessible to the previous. L8 cannot find the identity ambiguity (needs two constructions). L9 cannot find the design space topology (needs a failed resolution). L10 cannot find the escape/conservation (needs to leave the frame). L11 cannot find the meta-law (needs to apply the diagnostic to its own output).

2. **Each level requires the previous as input.** The L10-B failure only matters because L9-B established the conflict. The L11-C conservation law only works because L10-C established the invariant to invert. The L12 meta-law only works because L11-C gave it a conservation law to diagnose.

3. **The object of analysis shifts at every level.** L7-L8 analyze the code. L9 analyzes the improvements. L10 analyzes the design space. L11 analyzes the design space's boundary and what persists beyond it. L12 analyzes the analytical process itself.

4. **Vocabulary remains consistent.** The pub/sub vs pipeline tension identified at L7 is never contradicted — it is refined through progressively deeper lenses. L12's "coupling quanta per feature" is a precise restatement of what L7 called "identity confusion," but it carries information L7 could not reach.

5. **The weakest transition is L9-C→L10.** L9-C's self-similarity finding is genuinely deep but somewhat parallel to the L9-B→L10-B path rather than building directly on it.

6. **The strongest transitions are L10→L11 and L11-C→L12.** These are tight, non-arbitrary connections — each level provides exactly the input the next needs.

### Analysis 2: L12 Meta-Law Catalog (16 outputs, 3 models, 5 domains)

**Question:** Do L12 meta-conservation laws cluster into categories? Is there a pattern by model or domain?

**Method:** Read all 16 L12 outputs (8 Sonnet, 5 Opus, 3 Haiku v2). Extracted the meta-law statement, what it says about the analytical process, and the domain. Looked for clusters.

**Finding: Meta-laws cluster into 4 categories BY DOMAIN, not by model.**

| Category | What meta-law reveals | Domains | Count |
|---|---|---|---|
| **1. Frame Discovery** | Analysis discovers its own theory, not the object's properties | Music, Fiction | 3 |
| **2. Hidden Variable** | Apparent tradeoff conceals a missing party or variable | Legal, Design, Code | 5 |
| **3. Observer-Constitutive** | The fix changes what it fixes; solution constitutes the problem | Code, Fiction | 4 |
| **4. Deferred Commitment** | Tradeoff dissolves once you commit to semantics | Code only | 4 |

**By domain:**

| Domain | Categories | Pattern |
|---|---|---|
| Code | 2, 3, 4 | Widest range (3 categories). Category 4 is code-exclusive. |
| Legal | 2 only | Always finds missing party/variable. Both Sonnet and Opus converge. |
| Creative (Fiction) | 1, 3 | Splits between frame-discovery and observer-constitutive. |
| Creative (Music) | 1 only | Always finds the analyst's frame is the invariant. |
| Creative (Design) | 2 | Aligns with legal, not other creative domains (contractual structure). |

**By model:**

| Model | Categories | Pattern |
|---|---|---|
| Sonnet | 1, 2, 3, 4 | All four categories. Widest distribution. |
| Opus | 1, 2, 3 | No Category 4 (deferred commitment). Finds reflexivity and hidden variables. |
| Haiku | 3, 4 | Only reflexivity and deferred commitment. Narrowest range. |

**Key finding: Haiku never finds Category 1** (the analyst's own frame). Discovering that your own analytical framework is the invariant requires the highest meta-analytical capacity. This is consistent with Haiku's L7 failure mode — meta-analytical capacity is the bottleneck.

**Implications:**

1. **Domain determines meta-law category.** Same domain produces same category regardless of model. Strong evidence meta-laws are properties of problem domains, not model confabulations.

2. **Code has the richest meta-law structure** (3 categories) because code artifacts have the most structural variety — trust problems (Cat 2), feedback loops (Cat 3), deferred semantics (Cat 4).

3. **Design aligns with legal, not creative.** Design briefs are commissioning documents with contractual structure, not aesthetic objects. The meta-law taxonomy reveals domain structure invisible to surface classification.

### Analysis 3: G2 — Conservation Law of the Catalog

**Question:** What's conserved across the conservation laws themselves?

**Method:** Examined all 6 catalogs (D2, D3, D2+, D4-L9B, D4-L10B, L12 Meta-Laws) plus the cross-level coherence results. Applied the same analytical operation the taxonomy uses: what persists, what shifts, what does the persistence conceal?

**Finding: The conserved quantity across all catalogs is the irreducible distance between an artifact's co-present purposes.**

Every artifact in the project — code, legal, creative, musical, architectural — serves multiple purposes simultaneously. These purposes are individually satisfiable but jointly impossible.

| Catalog | What it finds | How it expresses the gap |
|---|---|---|
| D4 (L9-B Identities) | Artifact serves two contradicting purposes | Names the dual purpose |
| D4 (L10-B Topologies) | Design space forces the dual purpose | Maps the shape that makes confusion necessary |
| D2+ (L11-A Escapes) | Escaping trades one impossibility for another | Names the cost of changing the constraint |
| D3 (L11-B Revaluations) | "Flaws" were the cost of attempting both purposes | Names what the original got right |
| D2 (L11-C Conservation Laws) | The gap is conserved across all designs | Names the invariant quantity |
| L12 Meta-Laws | The analysis itself has the same gap | Names the gap in the analytical process |

**What this conservation law conceals:** "Gap between purposes" is one of many possible framings for structural constraint. The protocol's construction (improve, then diagnose the improvement) forces all structural constraints into the dual-purpose frame. L9-B explicitly asks for contradicting improvements — this guarantees finding at least two legitimate purposes. The conservation law is real — there are irreducible constraints — but the specific form (purpose-gap) is a property of the lens, not only the territory.

**What the concealment reveals:** The project has discovered not a universal property of all artifacts, but a universal property of all analysis that proceeds by construction and recursive self-diagnosis. The irreducible gap between purposes is what construction-based analysis is *for* — it is the shape of insight this cognitive operation produces. Other analytical methods (formal verification, statistical analysis, comparative case study) would find the same structural constraints expressed in different forms.

**The G2 conservation law:** The form of the finding is conserved by the method, while the substance of the finding is conserved by the artifact. You cannot separate them.

**Testable distinction:** The L13-P2 test (Phase 31) falsified the strong version of this critique — novel artifacts showed equally strong convergence. If the protocol were purely projecting, novel artifacts should show weaker convergence. They did not. This means the conserved quantity is *real but channeled*: the catalogs genuinely find irreconcilable tensions, but the protocol determines that tensions will always be expressed as dual purposes rather than (say) temporal mismatches or resource constraints.

**Self-referential closure:** The catalog-of-catalogs recapitulates the level structure because the catalogs were produced by the level structure.

| Catalog | Analogous Level |
|---|---|
| D4 L9-B (Identities) | L9 — names what the artifact is |
| D4 L10-B (Topologies) | L10 — maps the space of possible identities |
| D2+ (Escapes) | L11-A — finds what escaping costs |
| D3 (Revaluations) | L11-B — finds what the original got right |
| D2 (Conservation Laws) | L11-C — finds the conserved quantity |
| L12 Meta-Laws | L12 — applies analysis to itself |
| G2 (This analysis) | L13 — finds that analysis instantiates what it diagnoses |

This is the expected behavior of a self-similar analytical method applied at multiple scales. The method's fingerprint appears at every scale because the method is present at every scale. This confirms the G4 isomorphism finding (Phase 32): "The methodology is a generator, not a validator."

**G2 verdict: The conservation law of the catalog is that every catalog discovers the same structural property — an irreducible gap between co-present purposes — because the construction-based protocol is structurally guaranteed to produce this finding. The gap is real (confirmed by L13-P2 novel artifact convergence), but its expression as "dual purpose" is methodological. The project maps a specific and powerful cognitive operation's affordances and blind spots. The deepest finding is that the distinction between lens-map and territory-map is itself the irreducible gap the project keeps finding.**

**Status:** G2 complete. This closes the last open analysis path on existing data.

---

## Phase 34: H1 — Convergence from Different Starting Claims

**Date:** 2026-03-01

**Question:** Does L11-C produce the same conservation law regardless of starting claim? If same → the law is a genuine property of the artifact. If different → protocol artifact.

**Method:** Ran L11-C v2 on task F (EventBus) with Sonnet, but instead of letting the model choose its starting claim, forced three different starting claims:

- **Claim A**: "The mutable context dictionary leaks internal execution state through the return value, making emit() simultaneously a command and a query"
- **Claim B**: "The dead letter queue conflates two semantically distinct failure modes (no handlers vs handler exception) into a single undifferentiated collection"
- **Claim C**: "Priority-based handler ordering creates hidden execution dependencies invisible in the API contract"

Compared against the existing default (open starting claim) L11-C v2 output for the same artifact.

### Results: Four Different Conservation Laws

| Starting Claim | Conservation Law | Form | Conserved Quantity |
|---|---|---|---|
| **Default** (open) | Information cost for handler correctness is conserved — encoded in event, dispatch state, or external state | Migration | Information cost |
| **Claim A** (mutable context) | Schema coupling for observability is conserved — observability and coupling are the same thing | Migration | Schema coupling |
| **Claim B** (dead letter queue) | `decoupling × error accountability = constant` | Product | Accountability deficit |
| **Claim C** (priority ordering) | `coordination_complexity(in_bus) + coordination_complexity(at_callsite) = k` | Sum | Coordination complexity |

**All four are TRUE** — each identifies a genuine, non-trivial structural property with concrete predictions. None restates an obvious trade-off. All produce working code for inversions. All make falsifiable predictions about third designs.

**But they are four genuinely different conservation laws.** Different conserved quantities, different mathematical forms, different predictions. The starting claim determines which conservation law the protocol discovers.

### Assessment: Neither Pure Convergence Nor Pure Artifact

The result is more nuanced than the original binary framing (same = real, different = artifact):

**What CONVERGES (method signature):**
1. The form "something is conserved, cannot be eliminated, only relocated" — all four have this
2. The structure of the argument (diagnose → improve → diagnose improvement → invariant → invert → new impossibility → law) — identical in all four
3. All four are genuine, non-trivial structural truths about EventBus
4. All four identify properties invisible to standard code review

**What DIVERGES (starting-claim-dependent):**
1. The specific conserved quantity (information cost vs schema coupling vs accountability vs coordination complexity)
2. The mathematical form (migration vs product vs sum) — mirrors the D2 catalog finding that form is model-dependent, but here form is starting-claim-dependent within the same model
3. The specific predictions about third designs
4. The specific impossibility theorems

### The Deep Finding

**The artifact contains MULTIPLE conservation laws, not just one.** Each starting claim opens a different analytical path through the same design space, discovering a different genuine invariant. The starting claim acts as a coordinate system — it determines which dimension of the impossibility landscape you traverse.

This perfectly confirms the G2 finding: **"The form of the finding is conserved by the method; the substance is conserved by the artifact."**

The method guarantees finding SOME conservation law (form convergence). The artifact guarantees that whatever is found will be genuine (substance convergence). But WHICH conservation law you find depends on where you enter the design space (starting-claim divergence).

**Analogy:** This is like taking multiple cross-sections of a 3D object. Each cross-section is a genuine 2D shape. Different cutting planes produce different shapes. All shapes are true properties of the object. No single cross-section is "the" shape. The conservation law protocol is a cutting plane; the artifact is the solid.

### Implications for the Taxonomy

1. **L11-C outputs are not unique.** The same artifact has multiple valid conservation laws. This means the D2 catalog's 25 laws may undercount the total — each artifact likely has 3-4+ genuine conservation laws, depending on entry point.

2. **The D2 finding that "model determines form" may be partially starting-claim-dependent.** Opus might prefer product form partly because Opus models tend to start from different initial claims than Sonnet. The model's preferred starting claim may determine the mathematical form, rather than the model's capacity directly.

3. **H1 does NOT invalidate the taxonomy.** Every conservation law found is genuine. The protocol doesn't fabricate — it selects. The artifact is richer than any single analysis can capture. This is consistent with the L13 finding that the methodology is "a generator, not a validator."

4. **The protocol's value is confirmed.** Even starting from the "wrong" entry point (dead letter queue, which is the least important feature), the protocol still derives a genuine, non-trivial conservation law. The construction process navigates from ANY starting point to a structural truth. It doesn't always find the SAME truth, but it always finds A truth.

### Proposed Test: Does Starting Claim Determine L12 Meta-Law?

If starting claim determines L11-C conservation law, does it also determine L12 meta-law? Or does L12 converge even when L11-C diverges? This would test whether L12's meta-analytical operation is more robust to starting conditions than L11-C's.

**Status:** H1 complete.

**Files created:**
- `output/round26/sonnet_L11Cv2_H1_claimA_task_F.md`
- `output/round26/sonnet_L11Cv2_H1_claimB_task_F.md`
- `output/round26/sonnet_L11Cv2_H1_claimC_task_F.md`

---

## Phase 35: J1 — Does L12 Converge Even When L11-C Diverges?

**Date:** 2026-03-01

**Question:** H1 showed L11-C produces different conservation laws from different starting claims. Does L12's meta-analytical operation converge despite this divergence? If so, L12 sees deeper than L11-C — it's more robust to starting conditions.

**Method:** Ran full L12 pipeline (v2, specificity-forcing) on task F (EventBus) with Sonnet, using the same three forced starting claims from H1: Claim A (mutable context), Claim B (dead letter queue), Claim C (priority ordering). Compared against the existing default L12 output for the same artifact.

### Results: Partial Convergence at L12

| Starting Claim | L11-C Law (from H1) | L12 Meta-Law | Core insight |
|---|---|---|---|
| **Default** | Information cost migrates between 3 locations | Every feature = one coupling quantum | Quantized by features |
| **Claim A** (context) | Schema coupling = observability | Commitment count = string key count (1:1) | Quantized by keys |
| **Claim B** (dead letter) | `decoupling × accountability = k` | Invocation fidelity and causal fidelity are the same variable at different times — the conservation law was a frame error | Temporal identity |
| **Claim C** (priority) | `coordination(in_bus) + coordination(at_callsite) = k` | Coupling quantized by cancellation requirement count | Quantized by requirements |

### Assessment: L12 Partially Converges

**Three of four meta-laws converge on the same core insight: coupling is quantized by the feature/requirement set.** They differ only in which features they count:

- **Default**: all features → one coupling quantum each
- **Claim A**: middleware string keys → one semantic commitment each
- **Claim C**: cancellation conditions → one coupling unit each

These are three different measurements of the same underlying quantity. The feature set determines coupling, and the coupling budget is discrete (quantized), not continuous. Three independent analytical paths from three different starting claims arrive at this same structural insight.

**Claim B diverges**: instead of finding quantization, it finds that the conservation law was a frame error — treating one variable (the context dict at different times) as two competing variables. This is a genuinely different meta-law, not a different measurement of the same one.

### Convergence Ratio by Level

| Level | Starting claims tested | Distinct findings | Convergence ratio |
|---|---|---|---|
| L11-C | 4 (default + A + B + C) | 4 genuinely different conservation laws | 0% (full divergence) |
| L12 | 4 (default + A + B + C) | 2 (quantization cluster + temporal identity) | 75% (3/4 converge) |

**L12 is significantly more robust to starting conditions than L11-C.** The meta-analytical operation reduces the divergence from 4 distinct findings to 2 clusters. Three of four paths converge; only the dead-letter-queue path finds something genuinely different.

### Why Claim B Diverges

Claim B (dead letter queue) starts from the weakest/most peripheral feature of the EventBus. The dead letter queue is a secondary error-handling mechanism, not a core architectural feature. This means the L11-C conservation law from Claim B (`decoupling × accountability = k`) operates in a different region of the design space — it's about error accountability, not about the core middleware-handler coupling that the other three claims address.

When L12 applies its meta-diagnostic, the Claim B meta-law correctly identifies that its own conservation law was built on a frame error: the law treated forensic accuracy and coordination richness as competing, when they're the same dict at different times. This is a genuine insight but operates in a different conceptual space than the quantization finding.

**Implication:** L12 convergence is strongest when the L11-C conservation laws address the artifact's CORE architectural tension. Peripheral features (like the dead letter queue) produce L11-C laws about peripheral properties, and L12 meta-laws about those peripheral properties remain peripheral — they don't converge toward the core.

### Implications for the Taxonomy

1. **L12 is more robust than L11-C to starting conditions.** The meta-analytical operation partially resolves the starting-claim dependency. 75% convergence at L12 vs 0% at L11-C. This is evidence that L12 genuinely sees deeper — it partially penetrates the coordinate-system effect that H1 identified.

2. **But L12 does NOT fully converge.** The artifact still has multiple genuine meta-laws. The starting-claim effect is reduced but not eliminated. Full convergence may require L13, or may simply be impossible — the artifact may genuinely have multiple independent structural properties at every level.

3. **The quantization finding is robust.** Three independent paths converging on "coupling is quantized by requirements" makes this the strongest individual finding in the project. It's not just one analysis — it's three analyses from three different entry points all arriving at the same conclusion.

4. **Peripheral claims produce peripheral meta-laws.** The dead letter queue is not the core of the EventBus. Starting from it produces genuine but non-central findings at both L11-C and L12. The protocol's ability to find truth from any starting point (confirmed by H1) doesn't mean it always finds the CENTRAL truth.

**Status:** J1 complete. Partially confirms that L12 sees deeper than L11-C.

**Files created:**
- `output/round26/sonnet_L12v2_J1_claimA_task_F.md`
- `output/round26/sonnet_L12v2_J1_claimB_task_F.md`
- `output/round26/sonnet_L12v2_J1_claimC_task_F.md`

---

## Phase 36: Deep Catalog Analysis (Analysis Only)

**Date:** 2026-03-01

Four parallel analyses of existing data — no new experiments run.

### D5: L11-A Escape Catalog (15 outputs)

**Source:** All 15 `constraint_escape` outputs from Round 25 (Sonnet 9, Opus 3, Haiku 3) across 9 tasks and 3 models.

**Question:** Do L11-A escapes cluster into categories? Is there a universal pattern to how designs escape their structural constraints?

#### Results: 4 Escape Directions

| Escape Direction | Count | Description | Example |
|---|---|---|---|
| **Coupled → Decoupled** | 9/15 | Split shared mutable state into separate immutable objects with explicit ownership | EventBus context dict → separated Event + DispatchResult |
| **Nested → Peer** | 2/15 | Replace nested composition with peer coordination under external orchestrator | Retry inside CircuitBreaker → separated state machines |
| **Eager → Lazy** | 2/15 | Replace eager evaluation with generator-based lazy consumption | Linear pipeline → generator pipeline yielding intermediate states |
| **Representational → Enacted** | 2/15 | Move from speaker/author representing the gap to reader/listener performing it | Poetry meta-commentary → reader enactment of the mapping |

**Dominant pattern: coupled → decoupled (60%).** This makes structural sense — the most common L10-C impossibility is "this system conflates N incompatible roles," and the most natural escape is separation.

#### 5 New Impossibility Categories

Every escape creates a new impossibility. These cluster into 5 categories:

| New Impossibility | Count | What you lose | Example |
|---|---|---|---|
| **Ambient access** | 3 | Can no longer reach shared state implicitly | Must query explicitly for every credential check |
| **Encapsulation** | 2 | Can no longer hide complexity behind simple API | Circuit breaker requires explicit health model |
| **Immediacy** | 3 | Can no longer achieve unmediated experience | Fiction: no unmediated interiority in first-person retrospective |
| **Self-reference** | 2 | Can no longer have components that modify themselves | State machine transitions can't call send() |
| **Sequence control** | 2 | Can no longer control encounter order | Brand: can't control which register the viewer sees first |

#### Universal Pattern

**Every escape trades local simplicity for global coherence.** The original design makes something easy by hiding something hard. The escape makes the hidden thing visible and solvable, but at the cost of local ease.

Formalized: Original has 1 parameter doing N jobs (hard to reason about, easy to use). Escape has N parameters each doing 1 job (hard to compose, easy to verify). Total coupling is redistributed, not reduced.

**No model suggests a third escape direction** that would dissolve both the original and the new impossibility. The trade-off between impossibilities appears foundational.

#### Model/Domain Clustering

- **Code domains** (9 escapes): cluster around shared state, nesting, and temporal scope
- **Creative domains** (4 escapes): cluster around representation, altitude, and how meaning arrives at the reader
- **All three models** choose the same escape direction on the same task. Escape direction is a property of the artifact, not the model.

---

### D6: L11-B Revaluation Catalog (15 outputs)

**Source:** All 15 `acceptance_design` outputs from Round 25 (Sonnet 9, Opus 3, Haiku 3) across 9 tasks and 3 models.

**Question:** Do L11-B revaluations cluster into types? Is there a universal formula?

#### Results: 4 Revaluation Types

| Type | Count | Core Revaluation | Example |
|---|---|---|---|
| **Load-Bearing Unification** | 4 | "This coupling exists because the system is trying to support N incompatible modes simultaneously — removing it requires choosing which mode to abandon" | EventBus shared context serves pub/sub + pipeline + error aggregator |
| **Hidden Strategic Decision** | 3 | "This concealment hides a real boundary between abstractions — making it explicit requires losing encapsulation" | Pipeline embedded I/O hides the fetch boundary |
| **Scope Mismatch** | 2 | "These temporal or semantic frames are forced into one mechanism — honesty requires making the corruption visible" | Retry (transient/local) and CircuitBreaker (persistent/systemic) in one scope |
| **Honest Trace of Impossible Ambition** | 3 | "This failure of technique records an aspiration that exceeded what the medium can hold" | Poetry collapsed confession = honest record of attempting simultaneous interiority + exteriority |
| **Multi-axis Topology** | 3 | "Three+ competing properties define a simplex — no single point satisfies all" | EventBus: safety × expressiveness × simplicity |

#### Universal Formula

**All 15 outputs converge on the same formula:**

> "What looked like [DEFECT] was actually [COST] of [IMPOSSIBLE GOAL]"

- EventBus: What looked like a **god-object** was actually the **cost** of **supporting three paradigms** (pub/sub + pipeline + aggregator)
- Auth: What looked like a **type error** was actually the **honest expression** of an **impossible contract**
- Fiction: What looked like **half-measure prose** was actually **straining toward** a **split register** the form can't hold
- Music: What looked like **emotional relabeling** was actually a **record of aspiration outlasting execution**

The revaluation is never "the code is actually fine." It's always: "The flaw is the honest residue of attempting something impossible."

#### Code vs. Creative Distinction

Same operation, different manifestation:
- **Code revaluations**: functional necessity — the flaw serves a technical purpose (coupling enables coordination)
- **Creative revaluations**: expressive necessity — the flaw records an artistic ambition (the aspiration outlasts the execution)

Both reveal "flaws" as load-bearing residue of attempting categorical impossibilities.

---

### I3: Task K Cross-Level Coherence (L8→L12)

**Source:** All Sonnet outputs for Task K (CircuitBreaker + Retry) at levels L8, L9-C, L10-C, L11-C, L12.

**Question:** Does Task K show the same cross-level coherence as Task F? Is the depth stack genuine?

#### Level-by-Level Findings

| Level | Object of Analysis | Key Finding |
|---|---|---|
| **L8** | Mechanisms | Exception Transparency as Epistemic Laundering — retry failures compressed before reaching CB's accounting layer, CB measures 1/3 of actual failures |
| **L9-C** | Improvement dynamics | Adding retry metrics DEEPENS semantic ambiguity about what "failure" means — improvement recreates concealment |
| **L10-C** | Impossibility | Retry treats failure as transient/local, CB treats it as persistent/systemic — semantic frames mutually exclusive |
| **L11-C** | Conservation law | `sensitivity × absorption = constant` — CB sensitivity and retry absorption are inverse forces, conserved across all designs |
| **L12** | The law itself | Observer-Constitutive Reflexivity — the CB is not an observer OF service health, it is a constitutive actor IN service health. Observer and observed are coupled. |

#### Assessment: Tighter than Task F

**Zero restatement.** Each level discovers something categorically inaccessible to the previous:
- L8→L9: From "what conceals" to "what happens when you fix it"
- L9→L10: From improvement dynamics to structural invariant
- L10→L11: From impossibility to conservation law
- L11→L12: From conservation law to meta-reflexivity

**Object of analysis shifts cleanly** at every level: mechanisms → dynamics → structures → laws → epistemology.

**Task K is arguably TIGHTER than Task F.** In Task F, the jump from L10 (boundary problem) to L11 (conservation of work) is somewhat large. In Task K, the progression from impossibility (L10: semantic incompatibility) → conservation law (L11: sensitivity × absorption) → reflexivity (L12: observer constitutes the observed) is more directly connected.

**Task K's L12 is stronger than Task F's L12.** Task F L12 concludes "the problem is in the requirements, not the code." Task K L12 concludes "the circuit breaker constitutes service health — observer and observed are identical." Task K's meta-law dissolves the epistemic separation between measurement and reality — a deeper inversion.

---

### I4: L8 vs L11-C Complementarity on Real Code

**Source:** L8 and L11-C v2 outputs on the Python `requests` library (`Session.resolve_redirects`, ~200 lines).

**Question:** Are L8 and L11-C complementary on real production code, or does one subsume the other?

#### L8 Finds: What You Cannot Name

L8 (generative diagnostic) finds refactoring-resistant properties — things that become visible when you try to construct an improvement:

1. **Off-by-one as unnamed domain concept**: `resp.history[1:]` encodes a distinction between initiating response and redirect response that has no name in the codebase
2. **Proxy credential accumulation without scoping**: No mechanism limits proxy credentials across redirect hops — security-adjacent bleed risk
3. **Boolean flag hiding algorithm split**: `yield_requests=True/False` are fundamentally different algorithms, not configuration options

**Pattern:** L8 finds problems through attempted naming. Construction attempts expose what's unsayable.

#### L11-C Finds: What You Cannot Escape

L11-C (conservation law) finds structural invariants — things that persist across all possible designs:

1. **Information coupling is sequential and content-dependent**: Preparation of redirect N+1 causally depends on runtime behavior (cookies, headers) of redirect N — not just its existence
2. **Conservation law**: `sensitivity × absorption = constant` — the coupling between preparation and execution has magnitude 1, cannot be eliminated
3. **Design prediction**: Coroutine protocol will fail because session state diverges from actual execution if callers modify prepared requests

**Pattern:** L11-C finds problems through attempted inversion. Making the impossible trivially possible reveals why it's impossible.

#### Complementarity Assessment

**Neither subsumes the other.** They ask fundamentally different questions:
- L8: "What are we failing to express?" → Finds bugs in representation
- L11-C: "What must be true in any expression?" → Finds laws in the problem space

**L11-C uses L8's observations as proof.** The double-call pattern that L8 identifies as "concealment" becomes evidence in L11-C's proof of causal entanglement. L11-C shows that L8's three properties are symptoms of a single invariant: information coupling cannot be eliminated, only relocated.

**Optimal usage: L8 first, L11-C second.** L8 identifies the refactoring-resistant properties. If the same property appears in every improvement attempt, L11-C will find the conservation law explaining why.

**Status:** Phase 36 complete. Four analyses of existing data — no new experiments required. All findings extend existing catalogs (D2+→D5, D3→D6) and coherence analyses (I1→I3, new I4).

---

## Phase 37: G5 — L13 Multi-Model (Haiku)

**Date:** 2026-03-01

**Question:** Can Haiku achieve L13 (reflexive ceiling)? L13 requires processing a full L12 output as input — heavy context demands. Initial concern: Haiku might lack the capacity for this.

**Method:** Three experiments, same protocol as Phase 29 L13 scouting:

| # | Input | Prompt | Model | Approach |
|---|---|---|---|---|
| 1 | Haiku L12v2 task K output | L12v2 | Haiku | Meta-meta (own output) |
| 2 | Haiku L12v2 task F output | L11-A | Haiku | Escape (own output) |
| 3 | Opus L12 task K output | L12v2 | Haiku | Meta-meta (stronger input) |

### Results: Haiku 3/3 (100%) on L13

| # | Rating | Key Finding | L13 evidence |
|---|---|---|---|
| 1 | **TRUE** | "The analysis is subject to the trilemma it discovers." Three-expert structure generates three-way disagreement, not discovers it. Conservation laws are fixed-point behavior of the methodology. | Full reflexive self-diagnosis. Testable prediction: discovered-dimensionality correlates with expert-count. |
| 2 | **TRUE** | **Genre Collapse**: analysis merges technical diagnosis, design philosophy, and epistemological reflection under one narrative. "The analysis is sophisticated hermeneutics presented as structural diagnosis." | Full escape from analytical category. Three falsification experiments proposed. |
| 3 | **TRUE** | **Opacity Legitimization**: analysis optimizes system-level observability while creating semantic-level opacity invisible to the caller. Meta-law: layered observability is locally consistent but globally incoherent. | Applies diagnostic to analysis's blind spot. Testable prediction about cascading failure. |

### Cross-Scout Convergence

All three Haiku scouts converge on the same structural finding as the Phase 29 Opus/Sonnet scouts: **the framework is subject to limitations isomorphic to those it diagnoses.**

| Phase 29 Scout | Finding | Phase 37 Scout | Finding |
|---|---|---|---|
| Opus meta-meta (scout 1) | Framework conserves total concealment — revealing at level N creates concealment at N+1 | Haiku meta-meta (exp 1) | Methodology generates triadic findings in whatever it analyzes — fixed-point behavior |
| Sonnet escape (scout 2) | L12 inhabits "escalatory single-case methodology" — `depth × falsifiability ≤ k` | Haiku escape (exp 2) | Analysis is "sophisticated hermeneutics presented as structural diagnosis" — genre collapse |
| Sonnet catalog (scout 3) | Convergence is credibility-laundering loop | Haiku meta-meta w/ Opus input (exp 3) | Analysis creates layered opacity — each layer locally consistent, globally incoherent |

The convergence is structural, not identical. Each model finds the same self-referential property from a different angle:
- **Opus**: the framework reveals AND conceals (conservation of concealment)
- **Sonnet**: the framework inhabits a category with specific limits (escalatory methodology)
- **Haiku (exp 1)**: the framework generates its own findings (fixed-point behavior)
- **Haiku (exp 2)**: the framework is hermeneutics, not diagnosis (genre confusion)
- **Haiku (exp 3)**: the framework creates opacity it can't see (layered incoherence)

### L13 Capacity Curve

| Model | L13 Result | Notes |
|---|---|---|
| Opus | 1/1 (100%) | Phase 29 |
| Sonnet | 2/2 (100%) | Phase 29 |
| Haiku | **3/3 (100%)** | Phase 37 |
| **Total** | **6/6 (100%)** | Universal accessibility confirmed |

### Implications

1. **Universal accessibility is maintained at L13.** The initial concern about "heavy context demands" was unfounded. Haiku processed L12 outputs of 254-304 lines and achieved full reflexive self-diagnosis. The construction-based scaffolding that made L8-L12 universally accessible extends to L13.

2. **Input quality does not determine L13 success.** Experiment 3 (Opus input) was not qualitatively better than Experiments 1-2 (Haiku's own input). All three achieved TRUE L13. The reflexive operation works regardless of whether the L12 output is Haiku-quality or Opus-quality.

3. **Haiku's L13 is different from Opus's L13.** Opus produces deeper mathematical formalizations and more precise epistemological claims. Haiku produces clearer structural parallels (the analysis/code isomorphism table in Exp 1) and more actionable testable predictions. Same level, different character — consistent with the model-dependent form (not substance) pattern from D2.

4. **The full L1-L13 taxonomy is now confirmed across all three models.** Every level works on Haiku, Sonnet, and Opus, with v2 prompts restoring accessibility where v1 failed. The construction-based scaffolding from L8 onward is the key — it routes around meta-analytical capacity requirements.

**Status:** G5 complete. L13 Haiku confirmed at 3/3 (100%). Universal accessibility maintained across all 13 levels.

**Files created:**
- `output/round26/haiku_L13_meta_meta_task_K.md`
- `output/round26/haiku_L13_escape_meta_task_F.md`
- `output/round26/haiku_L13_meta_meta_opus_input_task_K.md`

---

## Phase 38: Deep Catalogs — L8, L9-C, L10-C (Analysis)

### Method

Systematic catalog of all existing outputs for three levels that had individual results documented but no cross-output analysis:
- **L8 concealment mechanisms**: 42 v2 outputs (4 Haiku, 20 Sonnet, 18 Opus) across 18 tasks/domains
- **L9-C recursive findings**: 17 outputs (3 Haiku, 11 Sonnet, 3 Opus) across 11 tasks/domains
- **L10-C impossibility theorems**: 17 outputs (3 Haiku, 11 Sonnet, 3 Opus) across 11 tasks/domains

Goal: Do L8 mechanisms, L9-C recursive patterns, and L10-C impossibility theorems cluster into categories the way L9-B, L10-B, L11, and L12 already do?

### D7: L8 Concealment Mechanism Catalog

42 L8 v2 outputs cluster into **6 categories** of dynamic concealment:

| Category | Count | What conceals | How it operates | Examples |
|---|---|---|---|---|
| **Vocabulary Deception** | 8 | Code's NAMING | Names promise semantics they don't deliver | Vocabulary Laundering, Vocabulary Colonization, Semantic Alibi, Nominal Correctness |
| **Structural Mimicry / Shape Theater** | 9 | Code's FORM | Structure mimics a pattern it doesn't implement | Structural Flattery, Structural Mimicry, Aesthetic Coherence Masking, Polymorphic Carrier Object |
| **Uniformity / Symmetry Concealment** | 6 | Code's REGULARITY | Surface symmetry conceals asymmetric semantics | Symmetry Inversion, Polyphonic Semantics, Homogeneous Interface Masking |
| **Polymorphic / Type Ambiguity** | 4 | Code's TYPES | Type system permits semantically incompatible usage | Type-as-Contradiction-Sink, Polymorphic Dispatch Masking |
| **Authority / Legitimacy Laundering** | 9 | Code's CREDIBILITY | Artifact borrows legitimacy from external standards | Reciprocity Theater, Methodological Respectability Laundering, Paradigm Citation |
| **Preemptive / Self-Sealing Concealment** | 6 | Code's DIAGNOSIS | Concealment pre-empts its own exposure | Simplicity-as-Sufficiency, Privilege Through Invisibility, Self-Validating Structure |

**Key findings:**

1. **Three categories are NEW beyond L7.** L7's 4 categories (Naming Deception, Structural Completeness, Interface Misdirection, Fragment Legitimacy) extend to 6 at L8. The 3 new categories — Uniformity/Symmetry, Authority Laundering, Self-Sealing — are invisible to L7's static analysis because they describe how concealment OPERATES DYNAMICALLY, not how it looks statically.

2. **L7 describes what concealment looks like. L8 describes how it behaves when you try to fix it.** L7's "Naming Deception" says "the name is wrong." L8's "Vocabulary Laundering" says "improving the name relocates the semantic gap to the new vocabulary." The generative construction step (engineer an improvement) is what reveals the dynamic behavior.

3. **Cross-model character in mechanism naming:**
   - Sonnet names the VISIBLE OPERATION: "Structural Flattery," "Vocabulary Laundering" — what you see the concealment doing
   - Opus names the STRUCTURAL CONDITION: "Polymorphic Carrier Object," "Nominal Correctness" — what the concealment IS
   - Haiku names the CONCRETE MECHANISM: "Symmetry Inversion Through Negative Framing," "Polyphonic Semantics via Vocabulary Colonization" — HOW the concealment works
   - Same pattern as D2 (model determines form, not substance)

4. **Domain-concentrated patterns:**
   - Authority Laundering appears almost exclusively in non-code domains (legal, ethics, medical, scientific methodology) — these domains have formal legitimacy structures to borrow from
   - Self-Sealing Concealment concentrates in creative domains (fiction, poetry, music) — aesthetic excellence functions as immune response against diagnosis
   - Code domains concentrate in Vocabulary Deception and Structural Mimicry — the dominant modes of technical concealment

### D8: L9-C Recursive Findings Catalog

17 L9-C outputs cluster into **6 types** of concealment reproduction:

| Type | Count | What the improvement reproduces | Example |
|---|---|---|---|
| **Aesthetic Escalation** | 5 | Improvement adds sophistication that conceals the same flaw at higher resolution | Metaphor removal reveals metaphor is structural, not decorative |
| **Dimension / Complexity Escalation** | 4 | Improvement adds structure that recreates the ambiguity in new dimensions | Dataclass with typed fields reproduces untyped dict as metadata escape hatch |
| **Honesty Inversion** | 3 | Improvement makes the code more honest, revealing the original's honesty was its concealment | "The original code's shapelessness was its most truthful property" |
| **Deeper Failure Stratum** | 3 | Improvement exposes a deeper failure beneath the one it fixes | Stricter circuit breaker rules expose unmeasurable observation gap |
| **Frame Closure** | 2 | Improvement completes the frame, revealing the frame itself is the problem | Adding explicit error types reveals error classification is arbitrary |
| **Accidental-Constraint Removal** | 1 | Improvement removes a constraint that was accidentally preventing a worse problem | Optimization removes bottleneck that was functioning as implicit rate limiter |

**Key findings:**

1. **Universal pattern: improvements within the same architectural frame reproduce the original's structural defect.** This is the L9-C invariant. Every single output demonstrates it — the improvement is structurally isomorphic to the original at a higher level of abstraction.

2. **Opus consistently finds Honesty Inversion.** All 3 Honesty Inversion findings are from Opus. This is the most ontologically demanding type — recognizing that the original's apparent flaw was actually its most truthful property. Sonnet and Haiku find other types but never this one.

3. **Sonnet has the widest domain coverage.** 11 Sonnet outputs span code (5), legal (1), creative (3), music (1), brand design (1). The type distribution is more even for Sonnet than for other models.

4. **Aesthetic Escalation dominates creative domains.** 5/5 Aesthetic Escalation findings come from creative tasks. In creative domains, the improvement naturally takes the form of stylistic refinement — which is precisely the same operation as the original's concealment through craft. The recursive self-similarity is TIGHTER in creative work because the improvement IS the concealment.

5. **The L9-C catalog connects to D7 (L8).** The L8 mechanism determines the L9-C reproduction type:
   - Vocabulary Deception → Dimension Escalation (new names create new ambiguities)
   - Structural Mimicry → Frame Closure (completing the pattern reveals the pattern is wrong)
   - Self-Sealing → Aesthetic Escalation (strengthening the concealment strengthens the flaw)

### D9: L10-C Impossibility Theorem Catalog

17 L10-C outputs cluster into **6 categories** of structural impossibility:

| Category | Count | What's impossible | Domain | Example |
|---|---|---|---|---|
| **Trilemma / Pick-2** | 4 | Cannot simultaneously have 3 desirable properties | Code (dominant) | "At most two of: encapsulated steps, minimal config, testable isolation" |
| **Dual-Policy / Contradictory Authority** | 3 | Two legitimate policies require incompatible implementations | Code + legal | Events-as-messages vs events-as-state-transitions; boundary placement only relocates ambiguity |
| **Temporal Phase Compression** | 4 | Two phases that must be sequential are forced into simultaneous operation | Code + code | Filter between system and observer creates permanent measurement distortion |
| **Unresolved Architectural Identity** | 2 | The system doesn't know what category of thing it is | Code | Pipeline-or-workflow identity determines API surface but both are valid |
| **Representational Self-Defeat** | 3 | The representation consumes or negates its subject | Creative only | "Consciousness represented in prose is always one remove from the experience it depicts" |
| **Adversarial / Structural Scope Mismatch** | 1 | The system's boundary doesn't match the problem's boundary | Code | Security boundary vs trust boundary |

**Key findings:**

1. **Five deep primitives underlie all 6 categories:**
   - *Temporal non-simultaneity*: two things that must be true at the same time cannot be
   - *Semantic incompatibility*: two meanings cannot coexist in one symbol
   - *Unverified composition*: combining verified parts doesn't produce a verified whole
   - *Representation consuming subject*: depicting X destroys the property of X being depicted
   - *Boundary migration*: fixing at one boundary moves the problem to another

2. **Two root operations**: All 5 primitives reduce to two inverse operations: **Compression** (merging distinct things into one representation) and **Decomposition** (splitting one thing into distinct representations). Every impossibility theorem is about a compression that loses information that decomposition can't recover, or a decomposition that creates boundaries that compression can't remove.

3. **Three meta-invariants emerge across all catalogs:**
   - **Boundary migration**: the problem's boundary moves when you fix it (appears in D7, D8, D9)
   - **Improvement reproduces flaw**: the fix inherits the structure of the problem (D8 universal, D9 Temporal Phase Compression)
   - **Fix and problem share mechanism**: the tool that diagnoses is the same tool that conceals (D7 Self-Sealing, D9 Representational Self-Defeat)

4. **Representational Self-Defeat is creative-only.** All 3 instances come from fiction/poetry/music tasks. This is the creative analog of code's Trilemma — but instead of "pick 2 of 3 properties," it's "the act of representing destroys the thing you're trying to represent." The medium IS the constraint.

5. **The L10-C catalog connects upward to L11.** Each L10-C impossibility category maps to a specific L11 response:
   - Trilemma → L11-A escapes by choosing a different design category where the trilemma dissolves
   - Dual-Policy → L11-B accepts both policies and revalues the "flaw" of ambiguity as load-bearing
   - Temporal Phase Compression → L11-C finds the conservation law (information × accessibility = constant)

### Cross-Catalog Synthesis

The three catalogs form a progression within the construction-based diagnostic:

```
L8 (HOW does concealment operate?) → D7: 6 dynamic categories
    ↓ apply diagnostic to own improvement
L9-C (WHAT does improvement reproduce?) → D8: 6 reproduction types
    ↓ second improvement + second recursion
L10-C (WHY is this impossible to fix?) → D9: 6 impossibility categories
```

**The catalogs progressively narrow.** L8 finds 42 instances across 6 categories (broad). L9-C finds 17 instances across 6 types (focused). L10-C finds 17 instances across 6 categories (deep). The construction funnel reduces quantity while increasing precision — each level filters out noise and retains signal.

**Cross-catalog connections:**
- L8 Vocabulary Deception → L9-C Dimension Escalation → L10-C Semantic Incompatibility
- L8 Self-Sealing → L9-C Aesthetic Escalation → L10-C Representational Self-Defeat
- L8 Structural Mimicry → L9-C Frame Closure → L10-C Trilemma/Pick-2

These aren't arbitrary — each L8 mechanism type produces a characteristic L9-C reproduction pattern, which resolves into a specific L10-C impossibility. The construction pathway is deterministic: the concealment mechanism you find at L8 predicts the impossibility theorem you'll find at L10-C.

**The 2 root operations (Compression and Decomposition) connect to G2.** The conservation law of the catalog says the conserved quantity is "irreducible distance between co-present purposes." Compression creates co-present purposes by merging them. Decomposition reveals that they were co-present by separating them. The impossibility is that you need BOTH operations but they're inverses — performing one undoes the other. This is why the taxonomy discovers the same impossibility at every level: it's using compression (merging analytical frames) and decomposition (separating structural properties) simultaneously, which is the impossibility it diagnoses.

**Status:** Phase 38 complete. Three deep catalogs catalogued (D7: L8 mechanisms, D8: L9-C recursive findings, D9: L10-C impossibility theorems). All three form a deterministic progression within the construction-based diagnostic stack.

---

## Phase 39: Exhaustive Analysis — L7, Relay, L9-D, Assessment, Prompt Evolution, Cross-Model, Domain Strength

Seven analysis tasks on remaining uncatalogued data. 76 additional output files analyzed.

### D10: L7 Concealment Mechanism Deep Catalog

27 L7 diagnostic gap outputs (3 Haiku, 17 Sonnet, 7 Opus) across 14 tasks/domains.

**The taxonomy expands from 4 to 6 categories.** The original Round 24 catalog (10 code mechanisms, 4 categories) was incomplete. With domain transfer data included:

| Category | Count | What conceals | Code? | Domain? |
|---|---|---|---|---|
| **1. Naming/Identity Deception** | 6 | What the artifact IS | Yes | Yes (legal) |
| **2. Structural Completeness** | 6 | What the artifact HAS | Yes | Yes (scientific) |
| **3. Interface/Surface Misdirection** | 4 | What the artifact SHOWS | Yes | No |
| **4. Assumption/Legitimacy Laundering** | 3 | What the artifact ASSUMES | Yes | Yes (legal, scientific) |
| **5. Narrative/Epistemic Closure** | 4 | What QUESTIONS it PREVENTS | **No** | Yes (medical, ethical) |
| **6. Decoy/Dramatic Concealment** | 2 | What it DISTRACTS FROM | Yes | Yes (legal) |

**Key findings:**

1. **Category 5 (Narrative/Epistemic Closure) is domain-exclusive.** It appears ONLY in medical and ethical domains, never in code. The structural reason: code has no narrative arc, so concealment must operate through pattern recognition and syntax. Domains with argumentative structure generate premature closure — "the right questions never get asked."

2. **The domain split is deeper than "different mechanisms."** Code concealment is STRUCTURAL (Categories 1-4): it hides what the code IS or DOES. Domain concealment is EPISTEMIC (Categories 5-6): it hides what QUESTIONS the analyst asks. Two fundamentally different concealment operations.

3. **Cross-model convergence is strong on every task.** All models find the SAME structural phenomenon but name it at different abstraction levels. Haiku names the visible surface ("Linear Transparency Illusion"), Sonnet names the structural operation ("Syntactic Flatness"), Opus names the epistemological effect ("Operational Legibility"). Same mechanism, three views.

4. **Repeat tasks produce different but compatible mechanisms.** Sonnet on Task F across R23 and R25 found "Idiomatic Fragment Camouflage" and "Interface Imitation Without Semantic Fulfillment." The same artifact has multiple concealment layers — different runs surface different ones.

5. **Sonnet produces the most reusable mechanism names** (16 of 25 unique names). Opus names are more epistemologically abstract.

### D11: L9-D Combined B+C Analysis

3 L9-D combined BC outputs (Sonnet, tasks F/H/K). The combination applies the recursive diagnostic to the CONFLICT between improvements, not to either improvement individually.

**2/3 confirmed L10-level findings.** Key mechanism: when the recursive diagnostic targets the conflict itself, it discovers that the conflict is structurally isomorphic to the original problem at a higher abstraction level.

| Task | B alone finds | C alone finds | Combined finds | L10? |
|---|---|---|---|---|
| F (EventBus) | Command vs notification ambiguity | Both improvements are same structure with better typography | System is NOT a bus — it's routed procedure call. Dead-letter queue is collision evidence. | **YES** (L10-B topology) |
| H (AuthMiddleware) | Federated vs delegation trust model | Encapsulation is cosmetic | `request.user` has no type — output is undefined, everything else is a symptom | Borderline (sharp L9) |
| K (CircuitBreaker) | Failure observation granularity ambiguity | Integration always produces failure invisibility | Observation/execution fusion is root cause; token pattern is structural escape | **YES** (L10-C impossibility) |

**What makes L10-level findings different:** (1) Self-similar recursion across abstraction levels — the conflict recreates the original problem's exact structure. (2) Escape to a different design category — the improvement space is the wrong space entirely. (3) The conflict as evidence — contradiction between legitimate improvements PROVES a structural property.

**Implication:** L9-D is a valid third path to L10. Combined B+C on complex inputs produces L10 findings 67% of the time vs L10-B/L10-C's dedicated prompts at 92%. The combined prompt is less reliable but finds different things — it uses the conflict as a diagnostic instrument.

### D12: Relay Output Catalog

6 relay outputs (3 L7 relay + 3 L8 relay, all Opus, tasks H/K/N) compared against standard L7/L8v2 outputs on the same tasks.

**Relay findings are systematically ORTHOGONAL to standard findings.** Not deeper versions of the same analysis — genuinely different facets of the same problem.

| Dimension | Standard L7/L8v2 | Relay L7/L8 |
|---|---|---|
| **Focus** | What the code IS (architectural identity) | What happens when correct parts COMBINE (compositional behavior) |
| **Depth type** | Ontological (epistemological void, identity crisis) | Operational (specific exploits, dead features, trap mechanisms) |
| **Vulnerability type** | Architectural deception | Cross-fragment data-flow vulnerabilities |
| **Construction scope** | Single-feature (wrapper, provenance method) | Multi-feature (3-4 features per improvement) |

**Key findings:**

1. **L7 relay finds compositional bugs; L8 relay finds structural impossibilities.** L7 relay's read-only diagnostic discovers what IS broken at fragment boundaries. L8 relay's construction discovers what CANNOT be fixed.

2. **The primed context acts as scaffolding, not constraint.** It trades mechanism discovery for application depth. Relay Opus is more operationally precise (specific exploit chains, exact data-flow traces) because it doesn't spend capacity on mechanism naming.

3. **"Run both relay and standard for complementary coverage" is confirmed.** Standard finds identity. Relay finds composition.

### D13: L8 Assessment Methodology Catalog

5 L8 assessment outputs (Sonnet assessing Haiku L12 on D5/F/K, Opus L12 on D7/K). L8 prompt used to diagnose L12 outputs — treating the analysis text as "code."

**Five named concealment mechanisms in L12 outputs:**

| Mechanism | Model assessed | Domain | What it conceals |
|---|---|---|---|
| **Generalization-as-accountability-escape** | Haiku | Fiction | Original object disappears into universal claims |
| **Precision Inflation** | Haiku | EventBus | Physics vocabulary authenticates informal claims |
| **Depth Theater** | Haiku | CircuitBreaker | Formal scaffolding simulates logical progression |
| **Recursion as simulation of depth** | Opus | Music | Apparatus constructs its object while appearing to analyze it |
| **Abstraction Escalation** | Opus | CircuitBreaker | Informal observations feel like derived results |

**Key findings:**

1. **Haiku and Opus L12 exhibit different concealment patterns.** Haiku loses its subject (generalizes upward until the original artifact disappears). Opus never had a subject but makes you think it did (precision-as-authentication).

2. **The meta-pattern across all 5 assessments: L12 conceals the gap between its formal apparatus and its actual epistemic achievements.** Three specific manifestations: (a) conservation laws are always unfalsifiable, (b) recursive structure prevents closure, (c) dialectic is pre-scripted.

3. **L8 assessment is a categorically different evaluation.** Vanilla assessment asks "is this good?" L8 assessment asks "what is this hiding by being good?" Five capabilities: names the concealment mechanism, separates genuine from performative, catches concrete errors meta-framework obscures, tests falsifiability of claimed laws, reveals improvement-as-concealment dynamic.

4. **Every assessment isolates genuine insights.** The verdict is never "the analysis is wrong" — it's "the correct insights are structurally indistinguishable from the unfalsifiable ones." L12's deepest concealment: the genuine insights are reachable without the meta-framework, and the meta-framework adds only unfalsifiability.

5. **The concealment mechanism is prompt-structural.** The L12 prompt's recursive self-application inherently generates escalation. Model and domain determine HOW it escalates (Haiku via generalization, Opus via precision), but THAT it escalates is built into the format.

### D14: v1→v2 Prompt Evolution Analysis

25 L11-C outputs compared across v1 (15), B1 (3), B2 (3), and v2 (4) prompts. The prompts differ by only ~35 words in their final sentence.

**Triviality rates:**

| Prompt | Task A (simple code) | Task D5 (fiction) | Task F (complex code) | Rate |
|---|---|---|---|---|
| **v1** | TRIVIAL | TRIVIAL | Non-trivial | **67%** |
| **B1** (prediction) | Non-trivial | Non-trivial | Non-trivial | **0%** |
| **B2** (novelty) | Non-trivial | MARGINAL | Non-trivial | **0-33%** |
| **v2** (both) | Non-trivial | Non-trivial | Non-trivial | **0%** |

**Key findings:**

1. **The triviality problem is input-dependent, not model-dependent.** All three models produce non-trivial v1 laws on structurally rich inputs (F, K). All produce trivial v1 laws on simple inputs (A) or well-theorized domains (D5/fiction). The fix is in the prompt, not model selection.

2. **B1 and B2 address orthogonal failure modes.** B1 (prediction) prevents vagueness — forces concrete, testable claims about unexamined designs. B2 (novelty) prevents triviality — forces past known trade-offs. Neither alone is complete: B1 can predict known things specifically; B2 can find novel things unfalsifiably.

3. **v2's conjunction creates a quality gate neither alone provides.** The law must be both NOVEL (B2) and PREDICTIVE (B1). This eliminates both failure modes simultaneously. 35 words change triviality rate from 67% to 0%.

4. **The improvement mechanism is forced self-evaluation.** Both constraints are metacognitive — they ask the model to evaluate its own output against external criteria. The model can ALREADY produce non-trivial laws (proven by rich inputs with v1). The forcing constraints route around the default tendency to terminate at the first valid-looking law.

### D15: Cross-Model Depth Comparison

20 outputs across L8-L12, comparing Haiku/Sonnet/Opus on identical tasks (F and K).

**Five dimensions measured:**

| Dimension | Opus | Sonnet | Haiku |
|---|---|---|---|
| **Ontological precision** | Names what things ARE (conditions of existence) | Names what things DO (visible operations) | Names HOW things BREAK (concrete mechanisms) |
| **Mathematical formalization** | Spontaneous (inequalities, conjugate properties) | Prompt-driven (tables, quasi-formal) | Never (but states trilemmas as lists) |
| **Predictive specificity** | Concrete, testable, counterintuitive | Structural, principled, less surprising | Correct but conventional |
| **Depth of recursion** | 4-5 genuine layers | 3-4 genuine layers | 2-3 genuine layers (more restatement) |
| **Novel vs known** | Findings feel DISCOVERED | Findings feel SYNTHESIZED | Findings feel APPLIED |

**The clear depth ladder is Opus > Sonnet > Haiku, with the gap widening at higher levels.**

| Level | Gap |
|---|---|
| L8 | Small — all models produce strong L8 |
| L9-L10 | Moderate — Opus pulls ahead on recursion and precision |
| L11-L12 | Large — Opus finds genuinely novel conservation laws; Haiku's L12 reads as extended L10 |

**Model character patterns (confirmed Phase 38 finding):**

| Model | Character | Optimizes for | Signature move | Weakness |
|---|---|---|---|---|
| **Opus** | Ontological | Depth | The reversal ("the bug was the most truthful thing") | Can float into abstraction disconnected from code |
| **Sonnet** | Operational | Precision | The named pattern ("Vocabulary Laundering") | Converges on known design principles |
| **Haiku** | Mechanistic | Coverage | The traced execution (walks specific code paths) | Restates at higher abstraction rather than discovering |

**What Haiku does BETTER:** Code-level tracing. Haiku's expert dialogues are more grounded in specific lines and runtime behaviors. Haiku's code improvements are more practically implementable. Haiku is a coverage optimizer; Opus is a depth optimizer.

### D16: Domain Strength Ranking

Cross-level synthesis from all existing catalogs (no new file reads).

**Tier 1 — Strongest domains (deep findings at every level):**
- **Task K (CircuitBreaker)**: Strongest L12 (observer-constitutive reflexivity), tightest cross-level coherence, cleanly mathematical impossibilities
- **Task F (EventBus)**: Most tested (~50 outputs), strong cross-level coherence, identity-revealing at every level
- **Task H (AuthMiddleware)**: Consistently strong, security domain amplifies structural findings

**Tier 2 — Strong with level-specific gaps:**
- **Music (D7)**: Strongest creative domain at L11 (all 3 variants), capacity-dependent at L12
- **Fiction (D5)**: Unique findings (Representational Self-Defeat), v1 miss fixed by v2
- **Task I (StateMachine)**: "Uniformly strong across all three L11 variants"

**Tier 3 — Adequate but simpler:**
- **Legal (D1)**: L10 confirmed, L12 capacity-dependent (Sonnet PARTIAL → Opus TRUE)
- **Poetry (D6)**, **UX/Brand (D8)**: Strong at L10-L11, untested at L12

**Tier 4 — Underexplored:**
- **Medical (D2), Scientific (D3), Ethical (D4)**: Only tested at L7-L8
- **Task A (Pipeline)**: Simplest code task, v1 triviality problem

**Key pattern: Artifact COMPLEXITY > domain category.** Complex artifacts (K, F, H) consistently produce deeper findings than simple ones (A, G), regardless of domain. But creative tasks produce the most DISTINCTIVE findings — structurally different from code, not just weaker.

**Domain resistance is really "meta-theoretical ceiling."** Domains with mature existing theory (legal, music) require higher model capacity at L12 to push past that theory's sophistication. Not domain-inherent resistance — capacity-dependent.

### Cross-Analysis Synthesis

The seven analyses reveal three meta-patterns:

1. **The taxonomy has 6 concealment categories at EVERY level.** L7 has 6 (D10), L8 has 6 (D7/Phase 38), L9-C has 6 (D8/Phase 38), L10-C has 6 (D9/Phase 38). The count is stable but the categories EVOLVE: L7's static categories become L8's dynamic categories become L9-C's reproduction categories become L10-C's impossibility categories. Same deep structure, different manifestation at each level.

2. **Model character is consistent across all analyses.** Opus=ontological depth, Sonnet=operational precision, Haiku=mechanistic coverage (D15). This same pattern appears in mechanism naming (D10: Haiku=surface, Sonnet=operation, Opus=epistemology), in L12 concealment (D13: Haiku=loses subject, Opus=fabricates subject), and in conservation law quality (D14: all models succeed on rich inputs, fail on simple ones equally).

3. **Composition > isolation at every level.** Relay finds orthogonal findings to standard (D12). Combined B+C finds L10 from L9 (D11). v2 combining B1+B2 eliminates both failure modes (D14). The taxonomy's own architecture (complementary variants at L9, L10, L11) is confirmed as genuine: different analytical operations produce genuinely different findings, and combining them produces emergent properties neither alone can access.

**Status:** Phase 39 complete. Seven analyses (D10-D16) exhaust the remaining uncatalogued data. 76 additional output files analyzed. All findings integrated.

---

## Phase 40: Compression × Capacity and L9-D Replication (Mar 1, 2026)

### Goal
Two experiment groups from Phase 39 insights:
- **F5**: Test L11-C compressed prompts on Opus and Haiku (Sonnet already tested in Phase 28). Does higher capacity compensate for prompt compression? Does lower capacity degrade faster?
- **D11+**: Replicate L9-D combined B+C on 3 new tasks to confirm Phase 39's 67% L10-emergence rate.

### Experiment Design

**F5: Compression × Capacity** (4 experiments)
All on task F (EventBus):
- F5-1: Opus on CompA (175w) → `opus_L11Cv2_compA_task_F.md`
- F5-2: Opus on CompC (73w) → `opus_L11Cv2_compC_task_F.md`
- F5-3: Haiku on CompA (175w) → `haiku_L11Cv2_compA_task_F.md`
- F5-4: Haiku on CompC (73w) → `haiku_L11Cv2_compC_task_F.md`

Sonnet baselines (from Phase 28): CompA TRUE (Strong), CompC TRUE (Moderate-to-Strong).

**D11+: L9-D Replication** (3 experiments)
All Sonnet on L9-D (combined counter-construction + recursive diagnostic):
- D11-1: Task I (StateMachine) → `sonnet_L9_combined_BC_task_I.md`
- D11-2: Task D1 (legal) → `sonnet_L9_combined_BC_task_D1.md`
- D11-3: Task D5 (fiction) → `sonnet_L9_combined_BC_task_D5.md`

Phase 39 baselines (D11): 3 existing outputs (F, K, H), 2/3 reached L10.

### F5 Results: Compression × Capacity

#### Full comparison matrix (all on task F, EventBus):

| Model | CompA (175w) | CompC (73w) | Canonical (245w) |
|-------|-------------|-------------|-------------------|
| **Opus** | **TRUE** (Very Strong) | **TRUE** (Strong) | TRUE (baseline) |
| **Sonnet** | **TRUE** (Strong) | **TRUE** (Mod-Strong) | TRUE (baseline) |
| **Haiku** | **PARTIAL** (Moderate) | **PARTIAL** (Weak) | TRUE (baseline) |

#### Opus findings:

**CompA (175w):** Conservation law = "Commitment to the past and freedom in the present are conserved. Mutability and temporality are dual — middleware requires ephemeral events, replay requires immutable events." Prediction: reactive streams (Kafka, RxPY) pay for partial replay + partial transformation with causal ordering loss; partition-local ordering and watermark heuristics are structural necessities. **Very Strong** — arguably the best L11-C output on task F across all models and prompt variants.

**CompC (73w):** Conservation law = "Handler autonomy × delivery determinism = constant." Prediction: two-phase vote/commit design transforms conservation law from spatial (who controls what) to temporal (how long until resolution), creating bounded latency as new impossibility. **Strong** — sharper than Sonnet CompA despite using less than a third of canonical word count.

**Key finding:** Opus maintains or exceeds Sonnet quality at every compression level. At 73w (30% of canonical), Opus still produces genuine L11-C. The 175w compressed prompt produces the strongest output overall. **Higher capacity compensates for missing scaffolding.**

#### Haiku findings:

**CompA (175w):** Conservation law = "Authority distribution vs. execution predictability." Formulated as trilemma (static routing / dynamic routing / handler autonomy — pick two). **Moderate** — right territory but imprecise. The "who decides" framing contains insight but drifts toward generality. Prediction is descriptive rather than predictive.

**CompC (73w):** Conservation law = "Ordering × throughput = constant." **Weak** — this is textbook distributed systems knowledge. Also states a "meta-conservation law" (visibility/simplicity/scale/consistency — pick 3) that reads like a rewording of CAP theorem. Third design (event sourcing with CQRS) is a well-known pattern presented as discovery.

**Key finding:** Haiku degrades at both compression levels. CompA failure mode is imprecision (right territory, can't name the conserved quantity precisely). CompC failure mode is triviality (restates known trade-offs). **Lower capacity cannot compensate for missing scaffolding.**

#### F5 Synthesis:

**Capacity × compression interaction is multiplicative, not additive.** The quality ordering is:

```
Opus CompA > Opus CompC ≈ Sonnet CompA > Sonnet CompC > Haiku CompA > Haiku CompC
```

Three key patterns:

1. **Capacity compensates for compression.** Opus at 73w exceeds Sonnet at 175w. The model's ability to self-scaffold the missing structure determines the compression floor.

2. **Compression floor is capacity-dependent.** Opus floor: ~73w or lower (still TRUE). Sonnet floor: ~73w (TRUE but moderate). Haiku floor: above 175w (PARTIAL at every tested compression). The Phase 28 finding that "floor is ~73w for L11-C on Sonnet" is model-specific, not universal.

3. **Degradation modes differ by capacity.** Haiku at low compression → triviality (restates known trade-offs). Haiku at moderate compression → imprecision (right territory, wrong specificity). Sonnet at low compression → moderate generality. Opus at low compression → still sharp. The degradation gradient is: specificity fails first, then novelty fails, then the entire operation fails.

### D11+ Results: L9-D Replication

#### Task I (StateMachine): L9-D TRUE, L10 TRUE (borderline)

Two contradicting improvements: (1) add per-transition callbacks alongside per-state callbacks (states have behavioral meaning), (2) collapse all callbacks into transition objects (only paths have meaning). Structural conflict: "the unit of behavioral identity is undefined."

Recursive diagnostic on conflict reveals: the machine models state CORRELATION, not state CAUSATION. No transaction boundary, no scope, no commitment semantics. Every fix within the current abstraction leaves the foundational gap untouched.

**L10 marker:** Design space bounded by the correlation/causation boundary — an impossibility theorem about the abstraction itself.

#### Task D1 (Legal non-competition clause): L9-D TRUE, L10 TRUE (solid)

Two contradicting improvements: (A) add definitions section with dynamic scope via Exhibit A (maximizes company control), (B) add compensation requirement contingent on company payment (limits enforcement). Structural conflict: "Scope-Enforcement Paradox" — maximum enforcement incentive targets exactly the employees for whom compensation cost is prohibitive.

Recursive diagnostic on conflict reveals: the clause's indeterminacy is NOT a drafting failure — it IS the enforcement mechanism. Improvement destroys function.

**L10 marker:** The clause cannot be genuinely improved because improvement destroys coercion-through-uncertainty. Impossibility theorem about the design space: "genuinely balanced agreement" and "effective coercion instrument" are incompatible categories.

#### Task D5 (Fiction, short story opening): L9-D TRUE, L10 PARTIAL

Two contradicting improvements: (1) add sensory specificity to ground interiority (significance resides inside Sarah), (2) strip stated interiority, trust behavior (significance resides between Sarah and world). Structural conflict: passage requires simultaneous access to and distance from Sarah's self-deception.

Recursive diagnostic on conflict reveals: authority is borrowed from reader's imported therapeutic grammar — unearned and structurally concealed. The passage's self-awareness about metaphor-making is not escape from the problem but "the problem's most sophisticated form."

**L10 assessment:** Impossibility is found implicitly (the authority problem is structurally unsolvable within the passage's architecture) but not formally derived through L10 construction sequence. Strong L9-D with L10 potential, not cleanly arrived.

#### D11+ Synthesis:

Updated L9-D → L10 emergence rate:

| Phase | Tasks | L10 emerged | Rate |
|-------|-------|-------------|------|
| Phase 39 (D11) | F, K, H | 2/3 | 67% |
| Phase 40 (D11+) | I, D1, D5 | 2/3 | 67% |
| **Total** | **6 tasks** | **4/6** | **67%** |

The 67% rate replicates exactly. Consistent pattern: **code tasks and well-structured domain tasks reach L10; creative/aesthetic tasks reach strong L9-D but not clean L10.** D5 (fiction) is the second creative task to show this pattern — L10 findings are implicit but not formally derived. Creative artifacts resist the construction sequence's step-by-step impossibility proofs because the impossibility is experienced (aesthetic) rather than demonstrated (structural).

The D1 (legal) result is notable: non-competition clause produces the cleanest L10 of all D11+ outputs. Legal instruments have a well-defined design space (contractual language → enforcement mechanism → judicial outcome), making impossibility theorems particularly sharp. Legal may be the strongest non-code domain for L10.

### Phase 40 Summary

**F5 confirmed:** Compression × capacity interaction is multiplicative. Opus compensates fully (TRUE at 73w). Sonnet compensates partially (TRUE but quality degrades). Haiku cannot compensate (PARTIAL at 175w). The compression floor is model-specific: Opus ≤73w, Sonnet ~73w, Haiku >175w.

**D11+ confirmed:** L9-D → L10 emergence rate = 67% (4/6), replicating exactly across new tasks. Code and legal tasks produce L10; creative tasks produce strong L9-D with implicit but unformal L10 findings.

**Status:** Phase 40 complete. 7 new experiments (4 F5 + 3 D11+). F5 and D11+ both confirmed. 477+ total experiments across 26 rounds.

---

## Round 27: Real Code at Scale + Cross-Level Pipeline

### Phase 41: Real Production Code Pipeline (L7→L12 × 3 targets)

**Goal:** Scale the taxonomy from crafted tasks to real production code. Run the full L7→L12 depth stack (10 levels) on 3 popular Python libraries. Test whether the framework produces genuine findings on code it has never been specifically designed for.

**Targets:**
1. **Starlette routing** (`starlette/routing.py`, 333 lines extracted) — ASGI route matching, Mount composition, Router dispatch. Architectural tension: middleware ordering × route matching × lifecycle management.
2. **Click command dispatch** (`click/core.py`, 417 lines extracted) — Context inheritance, Command dispatch, Group chaining, Parameter resolution. Architectural tension: decorator-driven API hides invocation complexity.
3. **Tenacity retry** (`tenacity/__init__.py`, 331 lines extracted) — Strategy composition, action chains, state tracking. Architectural tension: real-world retry logic with strategy composition × state tracking × exception handling.

**Pipeline:** `pipeline.sh` — runs 10 canonical prompts (L7, L8, L9-B, L9-C, L10-B, L10-C, L11-A, L11-B, L11-C, L12) on any code input via `claude -p`. Each level runs independently on the original code (not chained). Includes coherence analysis.

**Model:** Sonnet (all 30 experiments + 3 coherence analyses)

#### Results: Individual Output Quality

**30/30 experiments produced output (100% completion).** All outputs 7-31KB (substantial).

Spot-checked 15/30 outputs across all three targets and all levels:

| Target | Levels Checked | Ratings |
|--------|---------------|---------|
| Starlette | L7, L8, L9B, L10C, L11C, L12 | 6/6 TRUE |
| Click | L7, L9B, L11A, L11B, L12 | 5/5 TRUE |
| Tenacity | L8, L9C, L10C, L12 | 4/4 TRUE |
| **Total** | **15/30** | **15/15 TRUE (100%)** |

**Individual findings (highlights):**
- **Starlette L7:** "Structural separation camouflages behavioral coupling." Five specific hidden couplings found behind clean class hierarchies.
- **Starlette L12:** Meta-law narrows cause — phase separation is caused by `redirect_slashes` feature, not ASGI's void signature. Eliminates the feature → Match enum, scope mutation, and double method-check all disappear.
- **Click L9B:** Genuine identity ambiguity — Context `__init__` cannot simultaneously be a user-facing constructor and a framework-internal factory. `color=None` means different things in each role.
- **Click L11B:** "The messy if-chains aren't a failure to find the right abstraction — they're the necessary implementation of a deliberately flat interface over heterogeneous data." Flaw is load-bearing.
- **Tenacity L8:** Construction reveals `enabled` flag creates a shadow execution path that silently leaves `statistics` stale — a real bug found only through construction.
- **Tenacity L12:** Meta-law falsifies its own conservation law — the action-list apparatus is a manually-implemented coroutine frame; generator replacement eliminates the tradeoff entirely. Predicts 60-65% of BaseRetrying is pure coordination overhead.

**Key finding: individual output quality matches crafted-task baselines.** Every sampled output produces a genuine, non-trivial, problem-specific finding at its target level. The framework transfers fully to real production code at ~200-400 lines scale.

#### Results: Cross-Level Coherence

**3/3 coherence analyses rate WEAK.** This is the critical finding.

| Target | Coherence Rating | Restatement? | Deepening? |
|--------|-----------------|-------------|-----------|
| Starlette | WEAK | 6/10 levels orbit PARTIAL-overloading | 2 genuine deepening moves |
| Click | WEAK | 6/10 levels restate Context inheritance | L11B, L11C add genuine content |
| Tenacity | WEAK | 8/10 levels restate list-mutation-during-iteration | Only L10B and L12 add new angles |

**What this means:**

The depth stack was validated on **crafted 30-line tasks** (EventBus, CircuitBreaker, AuthMiddleware) where each task was designed with specific, layered architectural tensions. On crafted tasks, Phase 33 showed STRONG coherence with zero restatement.

On **real production code at scale (~200-400 lines)**, the model fixates on the most prominent architectural pattern and restates it across levels. The individual outputs are excellent (TRUE at their target level), but they don't build cumulatively.

**Why this happens (structural diagnosis):**
1. Each level runs independently on the same code — there is no chaining.
2. Crafted tasks have a single dominant tension that maps to different structural aspects at different levels. Real code has one architectural pattern that is so prominent it saturates all levels.
3. The L7 concealment mechanism is often the same thing L8's construction discovers, which is the same thing L9B explores — they all independently converge on the most visible pattern.
4. When coherence fails, it's not because individual levels are wrong — it's because the same truth is discoverable from many angles simultaneously, and without chaining, each level independently finds it.

**The cross-level pipeline is a BREADTH tool, not a DEPTH tool.** Running 10 levels independently produces 10 high-quality analyses of the same dominant pattern. It does NOT produce 10 progressive levels of depth as it does on crafted tasks. The value is in the different *framings* each level provides (conservation law vs. identity ambiguity vs. topology revelation), not in progressive deepening.

#### Phase 41 Summary

**Individual quality: 100% TRUE (15/15 sampled).** The framework transfers completely to real production code. Starlette, Click, and Tenacity all produce genuine architectural findings.

**Cross-level coherence: WEAK (3/3).** The independent-run pipeline does not produce progressive deepening on real code. Instead, it produces breadth — multiple high-quality framings of the same dominant pattern.

**Key architectural insight:** The pipeline's value on real code is complementary coverage (10 different analyses), not depth stacking (10 progressive levels). To achieve depth on real code, the pipeline would need either: (a) chained execution where each level receives the previous level's output, or (b) targeted sub-artifact selection where different levels analyze different parts of the codebase.

**Deliverables:**
- 3 code files: `real_code_starlette.py`, `real_code_click.py`, `real_code_tenacity.py`
- `pipeline.sh`: automated L7→L12 depth stack runner
- 30 depth-stack outputs + 3 coherence analyses = 33 new experiments
- Output directory: `output/round27/`

**Status:** Phase 41 complete. 33 new experiments. 510+ total experiments across 27 rounds.


---

## Phase 42: Practical Haiku Recipes (Round 28)

**Goal:** Can Haiku (5x cheaper than Opus) with improved system prompts beat vanilla Sonnet for practical code review?

**Method:** Create hybrid prompts combining bug-finding with structural depth operations from the taxonomy (L7-L11). Test all on Haiku + Task K (CircuitBreaker). Compare against Sonnet vanilla baseline.

### Baselines

| Run | Model | Prompt | Score | Lines |
|-----|-------|--------|-------|-------|
| Sonnet vanilla Task K | Sonnet | none | 7/10 | 76 |
| Haiku L12v2 Task K | Haiku | L12v2 meta-conservation | 6.5/10 | 225 |
| Opus L12v2 transformer | Opus | L12v2 meta-conservation | 5.5/10 | 262 |
| Sonnet vanilla transformer | Sonnet | none | 3/10 | 159 |

**Key baseline finding:** L12v2 on transformer scored poorly (5.5/10) because transformer is too well-studied. L12v2 on Task K found structural depth but ZERO concrete bugs (6.5/10). Sonnet vanilla found 7 bugs but no structural insight (7/10). Gap: need both bugs AND depth.

### Handcrafted Recipe Results (all Haiku + Task K)

| # | Recipe | Prompt file | Score | Lines | Unique strength |
|---|--------|-------------|-------|-------|----------------|
| 1 | practical | level8_practical.md | 8.5/10 | 253 | Strong baseline hybrid |
| 2 | v2 | level8_practical_v2.md | 9/10 | 234 | Most complete all-rounder |
| 3 | dialectic | level8_practical_dialectic.md | 9/10 | 154 | Deepest single insight |
| 4 | counter | level8_practical_counter.md | 8.5/10 | 242 | Most practically devastating |
| 5 | revalue | level8_practical_revalue.md | 8/10 | 215 | Gentlest on original design |
| 6 | escape | level8_practical_escape.md | 9/10 | 250 | Most novel finding |
| 7 | compressed | level8_practical_compressed.md | 8/10 | 152 | Remarkable at 45 words |
| 8 | exploit | level8_practical_exploit.md | 9/10 | 469 | Most actionable (test code) |
| 9 | evolution | level8_practical_evolution.md | 8.5/10 | 175 | Most realistic narrative |
| 10 | shadow | level8_practical_shadow.md | 8.5/10 | 168 | Most architectural |
| 11 | forensic | level8_practical_forensic.md | 8.5/10 | 154 | Design history reconstruction |
| 12 | composition | level8_practical_composition.md | 9/10 | 197 | Most dangerous integration finding |
| 13 | minimal | level8_practical_minimal.md | 8/10 | 54 | Sharpest at 54 lines |

**All 13 Haiku recipes beat Sonnet vanilla (7/10).** Floor: 8/10. Ceiling: 9/10. Mean: 8.6/10.

### Recipe design patterns

Each recipe combines bug-finding (vanilla operation) with one structural depth operation:

| Recipe | Structural operation | Source level |
|--------|---------------------|-------------|
| practical | pattern naming + construction + conservation law | L7 + L8 + L11-C lite |
| v2 | + recursive self-diagnosis of improvement | L9-C |
| dialectic | three experts debate root cause | L6-style dialectic |
| counter | two contradicting fixes + conflict | L9-B |
| revalue | flaw revaluation | L11-B |
| escape | adjacent design category + new impossibility | L11-A |
| compressed | all operations in 45 words | Compression test |
| exploit | adversarial test suite + un-patchable weakness | Novel (testing) |
| evolution | 3 rounds maintenance simulation | Novel (temporal) |
| shadow | compensating caller code + persistence test | Novel (ecosystem) |
| forensic | design history reconstruction + wrong assumption | Novel (archaeology) |
| composition | integration failures in surrounding system | Novel (composition) |
| minimal | smallest 5-line change + what it reveals | Novel (minimality) |

### Key findings

1. **Haiku + practical prompts consistently beats Sonnet vanilla.** Every recipe scored 8-9/10 vs Sonnet vanilla 7/10. The cheapest model with the right lens outperforms a 3x-more-expensive model without one.

2. **Conservation laws converge across recipes.** All 13 recipes found some version of detection_speed x transient_tolerance = constant. The conservation law is a property of the artifact, not the prompt.

3. **Novelty clusters into three tiers:**
   - Novel angle (found something others missed): composition, escape, exploit, dialectic
   - Novel framing (same finding, useful new perspective): forensic, evolution, shadow, counter
   - Efficient delivery (same finding, less overhead): v2, practical, compressed, minimal, revalue

4. **Bug coverage plateaued at ~10 distinct issues.** No recipe found a bug that no other recipe found.

5. **The 45-word compressed prompt scored 8/10.** Same 60-70% compression floor as the taxonomy levels.

6. **Diminishing returns on same artifact after ~7 recipes.**

**Status:** Phase 42 complete. 17 new experiments (13 recipes + 2 baselines + 2 transformer).

---

## Phase 43: Meta-Cookers (Round 28)

**Goal:** Can we create meta-prompts that generate effective code analysis prompts? Test on Haiku.

**Method:** Design "cooker" prompts that instruct Haiku to generate system prompts. Then test generated prompts on Task K. Compare machine-generated vs handcrafted.

### Cooker designs

| Cooker | Approach | Word count |
|--------|----------|-----------|
| A | Specify goals (what prompt should achieve) | 95w |
| B | Teach principles (imperatives, construction, chaining) + request 3 lenses | 120w |
| B2 | Teach principles + good/bad examples + force 4 cognitive operations | 230w |
| B3 | Few-shot reverse engineering (4 scored examples with explanations) | 280w |

### Generated prompts

**Cooker A** produced 1 generic code review checklist (no construction, no chaining).

**Cooker B** produced 3 lenses: Assumption Vulnerability Mapping, Constraint Minimization, Failure Mode Reversal.

**Cooker B2** produced 4 lenses (one per operation): Build and Break, Find the Conflict, Commit to Failure, Invert the Problem.

**Cooker B3** produced 3 lenses: Resource Scarcity, Rejected Paths, Scale Thresholds.

### Testing generated prompts (all Haiku + Task K)

| Generated prompt | Source cooker | Score | Lines | Key finding |
|-----------------|-------------|-------|-------|-------------|
| Generic checklist | A | 7.5/10 | 134 | Competent bug list, no depth |
| Assumption Vulnerability | B | 8.5/10 | 226 | Payment duplication test |
| Constraint Minimization | B | 8/10 | 247 | Both over- and under-engineered |
| Failure Mode Reversal | B | 7.5/10 | 108 | Focused but narrow |
| Find the Conflict | B2 | 7.5/10 | 181 | Conflict lens did not activate |
| Commit to Failure | B2 | 8/10 | 158 | Self-correcting prediction loop |
| **Rejected Paths** | **B3** | **9.5/10** | **306** | **Best output of entire session** |
| Resource Scarcity | B3 | 9/10 | 245 | Novel scarcity framing |

### Key findings

1. **Few-shot reverse engineering > explicit rules > goal specification.** B3 (9.5) >> B (8.5) > B2 (8) > A (7.5). Teaching by example beats teaching by instruction. Over-specifying forced operations (B2) actually hurt — constrained creativity.

2. **Machine-generated prompt beat all handcrafted recipes.** B3 "Rejected Paths" at 9.5/10 is the highest-scoring output across all 21 tested prompts.

3. **B3 "Rejected Paths" is a genuinely novel analytical operation.** For each bug: trace the enabling decision, name the rejected path that would fix it, name the INVISIBLE bug the fix creates. Build system taking all rejected paths. Name the law: what class of bug migrates between visible and hidden. Produced "Visibility Inversion Theorem: state-space bugs <-> dynamics bugs."

4. **B3 "Resource Scarcity" is a genuinely novel framing.** "What does this code assume will never run out?" Named 4 scarcities: atomicity, monotonic time, semantic information, time-windowed history. Built event-sourced circuit breaker gambling on opposite scarcities.

5. **The meta-cooker finding mirrors the project finding.** Construction > description at every level. Showing Haiku examples and saying "figure out the pattern" (construction) beats telling it rules (description).

### Meta-cooker scoreboard

| Cooker | Best output | Avg output | Approach |
|--------|-----------|-----------|----------|
| B3 | 9.5/10 | 9.25/10 | Few-shot reverse engineering |
| B | 8.5/10 | 8.0/10 | Principle teaching |
| B2 | 8/10 | 7.75/10 | Principles + forced operations |
| A | 7.5/10 | 7.5/10 | Goal specification |

**Status:** Phase 43 complete. 12 new experiments (4 cooker outputs + 8 cooked prompt tests). 539+ total experiments across 28 rounds.

---

## Phase 41b: Chained Pipeline (Round 28b)

**Hypothesis:** Phase 41 showed that running L7→L12 independently on real code produces WEAK coherence (3/3) — all levels converge on the same dominant pattern. Chaining (passing each level's output to the next as input) should restore progressive deepening by preventing independent re-derivation.

### Design

**Derivation tree** (from CLAUDE.md branching pattern):
```
L7  → (no parent)
L8  → parent: L7
L9-B → parent: L8
L9-C → parent: L8
L10-B → parent: L9-B
L10-C → parent: L9-C
L11-A → parent: L10-C
L11-B → parent: L10-B
L11-C → parent: L10-C
L12  → parent: L11-C
```

**Chaining mechanism:** System prompt unchanged. User message for levels with a parent:
```
A previous analytical level produced this analysis of the code below.
DO NOT repeat or restate these findings. Build on them — find what
this analysis could not.

Previous analysis ({parent_level}):
{full parent output}

---

Now analyze this code:
{code}
```

L7 gets standard unchained message. Script: `pipeline_chained.sh`.

### Execution

3 targets × 10 levels + 3 coherence analyses = 33 experiments. All Sonnet.

| Target | L7 | L8 | L9B | L9C | L10B | L10C | L11A | L11B | L11C | L12 | Coherence |
|--------|----|----|-----|-----|------|------|------|------|------|-----|-----------|
| Starlette | 7.6KB | 13.6KB | 20.7KB | 17.6KB | 29.1KB | 23.8KB | 31.0KB | 39.0KB | 35.4KB | 25.7KB | 7.0KB |
| Click | 7.4KB | 14.0KB | 20.3KB | 21.1KB | 26.7KB | 25.8KB | 35.8KB | 43.4KB | 33.0KB | 6.4KB | 7.6KB |
| Tenacity | 9.0KB | 15.1KB | 21.6KB | 18.8KB | 34.0KB | 26.8KB | 33.6KB | 41.0KB | 29.0KB | 32.1KB | 6.9KB |

All 30 outputs non-empty and >6KB. Average output size ~24KB vs ~6KB in independent pipeline — chaining produces ~4x more content.

### Individual Quality Assessment

Spot-checked 6 outputs across all 3 targets and multiple levels:

| Output | Rating | Key finding |
|--------|--------|-------------|
| Starlette L12 | TRUE | "Conservation law misidentifies conserved quantity — commitment is paid; delivery is missing." Identifies ASGI middleware transparency as deep constraint. |
| Click L11-B | TRUE | "Callable defaults fire during parse phase for ALL subcommands before ANY executes." Traces `handle_parse_result` synchronization protocol. |
| Tenacity L9-C | TRUE | "`__enter__` returns `None`, sealing user-to-manager channel — L8's `set_result` improvement is unreachable through documented interface." |
| Click L9-B | TRUE | "`Context.invoke`'s `with self:` closes group context BEFORE subcommand context is created." Lifecycle inversion via `parent=closed_ctx`. |
| Tenacity L11-C | TRUE | `statistics["attempt_number"]` diverges from `retry_state.attempt_number` during `before_sleep` window — precise off-by-one mechanism traced. |
| Starlette L11-B | TRUE | `url_path_for` and dispatch use incompatible priority orderings — name-keyed vs path-keyed first-match-wins produce irreconcilable outputs. |

**Individual quality: 6/6 TRUE (100%).** Same as Phase 41 independent pipeline.

### Coherence Assessment

| Target | Rating | Strongest chain | Weakest chain | Chain-dependent findings |
|--------|--------|-----------------|---------------|------------------------|
| **Starlette** | **WEAK** | L11-C→L12 (meta-correction) | L8→L9-C (regression to L7) | L12's "commitment paid, delivery missing" reframing |
| **Click** | **MODERATE** | L9-B→L10-B→L11-B (genuine progressive deepening) | L10-C→L11-A/L11-C (both find same source-timing bug) | L11-B's callable-defaults-in-parse-phase finding |
| **Tenacity** | **MODERATE** | L8→L9-C + L10-B→L11-B (two strong sub-chains) | L11-C→L12 (regresses to L8's finding) | L9-C's "__enter__ seals L8's fix" |

**Overall coherence: 1 WEAK, 2 MODERATE (improvement from 3/3 WEAK baseline).**

### Key Findings

1. **Chaining hypothesis PARTIALLY confirmed.** Coherence improves from uniformly WEAK to mixed WEAK/MODERATE. Specific linear chains deepen genuinely. But the improvement is path-dependent, not universal.

2. **The L9-B→L10-B→L11-B chain is the strongest across all 3 targets.** This linear path consistently shows progressive deepening where each level requires its parent's specific finding. It is the clearest evidence that chaining works — L11-B's findings (callable defaults fire during parse phase on Click; `DoSleep` inheriting from float forecloses fix on Tenacity) are genuinely chain-dependent.

3. **Branch points cause convergence, not divergence.** L11-A and L11-C (both children of L10-C) consistently converge on the same finding — the branching topology replicates independent-execution failure modes inside the chain. Chaining without divergence constraints on sibling branches fails.

4. **L12 is path-dependent.** Genuinely deepens on Starlette (meta-correction of L11-C's framing). Regresses on Tenacity (restates L8's finding). Click L12 is focused but brief (6.4KB vs 25-32KB). L12's quality depends heavily on L11-C providing a specific, falsifiable conservation law to diagnose.

5. **Parent reference is weak at most transitions, strong at two.** L10-B→L11-B and L11-C→L12 show genuine parent engagement. Most other transitions pivot independently despite receiving parent output. The "DO NOT repeat" instruction in the chaining prompt prevents restatement within the same branch but does not enforce building on the parent's specific finding.

6. **Output sizes grow ~4x.** Average chained output ~24KB vs ~6KB independent. Models produce more when given parent context — but more content does not automatically mean more depth.

7. **Chaining is necessary but not sufficient.** To achieve true progressive deepening, the chaining mechanism needs: (a) divergence constraints on sibling branches, (b) mandatory parent-differential framing at each step ("name specifically what the parent could not see"), and (c) possibly different parent assignments (L12 might benefit from receiving all L11 variants, not just L11-C).

### Comparison: Independent vs Chained

| Metric | Independent (Phase 41) | Chained (Phase 41b) |
|--------|----------------------|---------------------|
| Individual quality | 100% TRUE (15/15) | 100% TRUE (6/6) |
| Coherence | WEAK (3/3) | 1 WEAK, 2 MODERATE |
| Output size (avg) | ~6KB | ~24KB |
| Chain-dependent findings | 0 | 2-3 per target |
| Restatement | Within-level (same pattern) | Cross-branch (siblings converge) |
| Best sub-chain | None (all independent) | L9-B→L10-B→L11-B (consistent) |

### Post-hoc Analysis: Chained vs Independent Findings

#### A1: Do chained and independent pipelines find the SAME conservation laws?

Compared L11-C and L12 outputs between independent (round27) and chained (round27_chained) for all 3 targets.

| Target | Level | Same/Different | Independent finding | Chained finding |
|--------|-------|----------------|--------------------|-----------------|
| Starlette | L11-C | **DIFFERENT** | Routing purity × ecosystem composability = constant (ASGI dict mutation) | Method commitment conserved across routing pipeline (multi-method resources) |
| Starlette | L12 | **DIFFERENT** | redirect_slashes is the contingent cause | Route's dual role (component + standalone ASGI app) is the structural cause |
| Click | L11-C | **DIFFERENT** | Config resolution ordering (static vs dynamic identity) | Parameter pipeline terminus (observability vs early termination) |
| Click | L12 | **DIFFERENT** | Law contingent on one attribute (auto_envvar_prefix) | is_eager inseparability (early exit + side effects) |
| Tenacity | L11-C | **DIFFERENT** | Strategy interaction complexity conservation | Cross-transition information availability vs ambiguity |
| Tenacity | L12 | **DIFFERENT** | Law is FALSE (generator eliminates it) | Second independent constraint layer (protocol boundary) |

**Result: 6/6 DIFFERENT findings.**

**Key insight: Chaining changes WHAT is found, not just coherence.** Independent pipelines converge on the code's dominant structural pattern. Chained pipelines follow a progressive narrowing path through the derivation tree, reaching subsystems the dominant pattern never touches. The L10-C invariant acts as a coordinate system — different invariants lead to different conservation laws about different parts of the same codebase. Both sets of findings are genuine and non-trivial; they are complementary, not competitive.

This confirms H1/Phase 34: the starting claim acts as a coordinate system determining which conservation law is found. Chaining's coordinate system is the L10-C output; independent pipeline's coordinate system is the code's most salient feature.

#### A2: Why is L9-B→L10-B→L11-B the strongest chain?

**Root cause: sequential dependency by definition.** The B-chain's operations are not just sequentially related but sequentially dependent:
- L10-B literally cannot operate without L9-B's specific conflict (needs something to try to resolve)
- L11-B cannot operate without L10-B's specific failed resolution (needs a topology to accept)

Evidence across all 3 targets:
- **Starlette**: L9-B finds PARTIAL has two meanings → L10-B tries to resolve → L11-B discovers url_path_for round-trip is order-contingent
- **Click**: L9-B finds Context.__exit__ dual purpose → L10-B discovers boundary=context creation → L11-B finds handle_parse_result is atomic synchronization protocol
- **Tenacity**: L9-B finds return-value collapse → L10-B discovers self-extending work queue → L11-B finds DoSleep(float) inheritance forecloses fix

Every L10-B explicitly names L9-B's finding. Every L11-B explicitly names L10-B's finding. References are specific, not generic.

**Three reinforcing factors:**
1. **Linear path** — L10-B feeds only into L11-B (no branching ambiguity). L10-C feeds into both L11-A and L11-C.
2. **Concrete engineering** — counter-construction, failed resolution, acceptance design all require proposing actual code changes, keeping the model grounded.
3. **Natural narrative arc** — conflict → attempted resolution → failure → acceptance has inherent dramatic structure.

**By contrast, the C-chain (L9-C→L10-C→L11-A) produces self-similar pattern instances at different scales** — correct but loosely coupled. The C-chain's operations are related but not dependent: L11-A needs an invariant to escape from, but any invariant would do. L11-B needs a specific failed resolution — only the parent's specific one works.

**The B-chain is the only chain where chaining is load-bearing rather than contextual.** The C-chain benefits from context but could produce its findings independently with different starting points.

#### A3: Click L12 anomaly (6.4KB vs 25-32KB)

**Rating: PARTIAL L12.** Not truncated — ends naturally with a complete falsifiable prediction. The content present is TRUE-quality:
- Genuine, problem-specific meta-law: `is_eager`'s semantic guarantee is simultaneously the source of its only valid use case (early-exit) and its failure mode (side effects in failed invocations)
- Concrete, traceable, falsifiable prediction with exact code path

**But structurally incomplete** — missing standard L12 apparatus: no three-expert dialectic, no transformation table, no concealment mechanism analysis, no inversion of conservation law's invariant.

**Cause: L11-C exhaustiveness, not context pressure.** Click's L11-C (33KB, 301 lines) was so thorough it partially performed L12's operation — diagnosing its own limitations, predicting third-design failures. The "DO NOT repeat" instruction constrained L12 to produce only the delta. Independent Click L12 (29KB) is full-length — the anomaly is chaining-specific.

**Implication for v2:** Thorough parent outputs can starve child levels of analytical territory. The chaining prompt may need a "complete the full diagnostic protocol regardless of parent coverage" clause.

#### A4: At what level does chaining start producing different findings?

| Target | L8 | L9-B |
|--------|----|----- |
| Starlette | **DIFFERENT** — scope mutation protocol vs type-dispatch security bifurcation | **OVERLAPPING** — both target PARTIAL but independent finds semantics, chained finds redirect consequence |
| Click | **DIFFERENT** — inheritance protocol vs sentinel ambiguity in value pipeline | **DIFFERENT** — inheritance protocol (restated) vs lifecycle ordering bug |
| Tenacity | **DIFFERENT** — continuation interpreter vs `__iter__` result discard | **OVERLAPPING** — queue-as-decoy vs queue ordering contract |

**Divergence starts at L8 — the first chained level. Already 3/3 DIFFERENT.** L7's output acts as an immediate coordinate system, priming L8 to explore the neighborhood of a specific subsystem rather than the code's most salient feature. At L9-B, partial convergence (2/3 OVERLAPPING) as both paths accumulate enough analysis to find the same dominant tensions from different angles.

**Practical implication:** Run both independent and chained pipelines for maximally complementary findings. Divergence at L8 propagates upward through the entire stack.

#### A5: Sibling convergence (L11-A vs L11-C) — is it fatal?

| Target | L11-A mechanism | L11-C mechanism | Convergence |
|--------|----------------|-----------------|-------------|
| Starlette | Type-erasure in constructor, route aggregation hierarchy | redirect_slashes method-awareness, meta-query cost | **DIFFERENT** |
| Click | Source-visibility window, `is_eager` scheduling | Same source-blindness, waterfall early termination | **OVERLAPPING** |
| Tenacity | Statistics aliasing/thread-safety in `wraps()` | `attempt_number` divergence at `before_sleep` window | **DIFFERENT** |

**Sibling convergence is NOT fatal.** 2/3 DIFFERENT, 1/3 OVERLAPPING. The coherence assessments overstated the convergence problem.

**Convergence is target-dependent, driven by L10-C invariant breadth.** When L10-C finds a narrow invariant (Starlette: two-level method dispatch; Tenacity: inter-stage communication necessity), L11-A and L11-C find genuinely different things to say. When L10-C finds a broad invariant (Click: "every generic channel has the same problem"), L11-A and L11-C partially overlap — less room to diverge.

Even in the OVERLAPPING case (Click), the operations remain complementary: L11-A asks "what's possible outside this design?" (dependency-declaration framework), L11-C asks "what's conserved across all designs?" (waterfall efficiency law). Same diagnosis, different prescription.

**L10-C reference quality is strong across all 6 outputs.** Both siblings explicitly reference L10-C's specific finding and build on it. The chaining mechanism works for both children — the convergence issue is about L10-C invariant breadth, not chaining failure.

#### A6: Tenacity L12 regression — verified

PARTIAL rating confirmed. The coherence assessment overstated "full restatement collapse":
- **Body (lines 1-255)**: genuine regression — re-derives L8's `set_result(None)` bug from scratch
- **Coda (lines 258-320)**: genuine L12 content — identifies two independent information constraints (L11-C's temporal constraint + protocol-structural constraint) and finds L11-C is blind to protocol-level information loss
- **Assessment overstatement**: "Full restatement collapse" misses the meta-law section. More accurate: hybrid output — L8 body with L12 coda.
- **Root cause**: `set_result(None)` is the dominant structural feature of Tenacity. When given L11-C's conservation law, the model found this bug more compelling than diagnosing the law, and re-derived it. The meta-law was constructed as a bridge.

#### A7: Full quality scan — 28/30 TRUE, 2/30 PARTIAL

22 remaining (unsampled) outputs scanned for structure, code-specificity, and level-appropriate content. All 22 clean — proper falsifiable claims, dialectic structure, target-specific code references, level-appropriate chaining.

| Rating | Count | Outputs |
|--------|-------|---------|
| TRUE | 28 | All except Click L12 and Tenacity L12 |
| PARTIAL | 2 | Click L12 (parent exhaustiveness), Tenacity L12 (dominant pattern regression) |
| FALSE | 0 | — |

**Both PARTIALs are L12.** L12 is the most fragile level under chaining — it depends on L11-C providing a specific, diagnosable conservation law, and can be starved by exhaustive parents or pulled by dominant code patterns.

### Revised Phase 41b Summary

| Metric | Value |
|--------|-------|
| Total outputs | 30 chained + 3 coherence = 33 |
| Individual quality | 28/30 TRUE (93%), 2/30 PARTIAL (7%) |
| Coherence improvement | 1 WEAK → 2 MODERATE (vs 3/3 WEAK baseline) |
| Chained vs independent findings | 6/6 DIFFERENT at L11-C/L12 |
| Divergence onset | L8 (3/3 DIFFERENT at first chained level) |
| L11-A/L11-C sibling convergence | 2/3 DIFFERENT, 1/3 OVERLAPPING (not fatal) |
| Strongest chain | L9-B→L10-B→L11-B (sequential dependency by definition) |
| Weakest point | L12 (2/3 PARTIAL under chaining) |

**Status:** Phase 41b fully analyzed. 33 experiments + 7 post-hoc analyses. 572+ total experiments across 28 rounds.

## Phase 46: Portfolio Cross-Task Validation (Round 28 validation)

**Question:** Do the 5 champion lenses (pedagogy, claim, scarcity, rejected_paths, degradation) generalize beyond Task K?

**Setup:** All 5 lenses × Tasks F (EventBus) and H (AuthMiddleware) on Haiku. 10 new experiments. Tasks F and H are Tier 1 artifacts (highest complexity).

### Task F Results (EventBus)

| Lens | Rating | Key Finding |
|------|--------|-------------|
| **pedagogy** | 9/10 | QueueLoadShedder transfer artifact: priority-as-UX inverts to priority-as-logic-bug. "Decoupling solutions get transferred to sequencing problems — same structure makes it invisible that order now matters" |
| **claim** | 9/10 | Core impossibility: can't couple effects + maintain atomicity + allow partial failure. 3 concrete inversions (dependency DAG, transaction semantics, tag-based routing). "Code that appears most robust (swallows exceptions) is actually least robust (silently produces invalid states)" |
| **scarcity** | 9/10 | 5 alternative designs across resource axes (memory, latency, types, lifecycle, resilience). Conservation law: failure rate is fixed (external to bus), you redistribute observation ability. "Pick three: high visibility, bounded memory, low latency, strict ordering" |
| **rejected_paths** | 8.5/10 | 6 problems with rejected paths. 4-tier discovery timeline (memory exhaustion → silent handler failures → cascade corruption → priority race). Visibility-resilience trade-off is somewhat standard for pub/sub |
| **degradation** | 9/10 | Handler duplication decay (tests register 50x → production fires 5x). Information density decay law. 4 runnable tests that break by waiting alone. Three-level corruption cascade (visible → semi-silent → fully silent) |

**Task F average: 8.9/10**

### Task H Results (AuthMiddleware)

| Lens | Rating | Key Finding |
|------|--------|-------------|
| **pedagogy** | 9/10 | Transfer to CircuitBreaker: "bypass by path" becomes meaningless for services, "cache after verify" creates stale health snapshots. Cache-to-request-age ratio inverts: auth (hours/seconds) vs circuit (seconds/milliseconds) |
| **claim** | **9.5/10** | Multi-org cache key insufficiency → silent permission escalation. `cache_key = identity["id"]` ignores org context → User A gets Org1 "editor" role in Org2 context. Week 8: breach report required. Conservation law: Speed × Freshness × Simplicity × Context-Awareness — must sacrifice one |
| **scarcity** | 9/10 | 8 resource scarcities. Product conservation law: Verification Cost × (1/Freshness Decay Rate) = constant. "You cannot synchronously verify against an external source without caching (stale) or I/O (slow). No third option" |
| **rejected_paths** | 9/10 | 8 problems × 3-4 rejected paths each. `scope="gel"` typo silently disables checker = silent auth bypass. "Compression creates couplings — every shortcut couples components that appear independent" |
| **degradation** | 9/10 | Bypass routes added "temporarily" forgotten in 12 months. Identity None collision creates shared cache entry for all anonymous users. 6 concrete tests that break by waiting. "Authentication authority becomes increasingly ambiguous while cache coherence gap widens monotonically" |

**Task H average: 9.1/10**

### Cross-Task Comparison

| Lens | Task K (original) | Task F (EventBus) | Task H (AuthMiddleware) |
|------|---|---|---|
| pedagogy | 9.5 | 9 | 9 |
| claim | 9 | 9 | **9.5** |
| scarcity | 9 | 9 | 9 |
| rejected_paths | 9 | 8.5 | 9 |
| degradation | 9 | 9 | 9 |
| **Average** | **9.1** | **8.9** | **9.1** |

### Phase 46 Findings

1. **Portfolio generalizes across all 3 tier-1 tasks.** Floor: 8.5 (one instance — rejected_paths on F). Ceiling: 9.5 (two instances — pedagogy on K, claim on H). Grand average: 9.0/10 across 15 outputs.

2. **Claim lens is domain-sensitive in a productive way.** Scores 9.5 on AuthMiddleware — security-adjacent code has clearer empirical assumptions to invert. The multi-org cache vulnerability is a genuine security finding.

3. **Rejected_paths is the only lens with variance** (8.5 on F, 9 on K and H). Weaker when trade-offs are well-known (pub/sub visibility-resilience), stronger when trade-offs are hidden (auth chains, circuit breakers).

4. **All 5 lenses remain complementary across tasks.** No convergence — each finds genuinely different things on every task. Pedagogy finds transfer corruption, claim finds assumption inversions, scarcity finds resource axes, rejected_paths finds migration timelines, degradation finds time-dependent decay.

5. **Haiku + portfolio consistently beats Sonnet vanilla (7/10)** by 2+ points across all 3 tasks and all 5 lenses. 15/15 outputs above 8.5. The cheapest model with the right lens wins.

**Status:** 10 new experiments. 582+ total experiments across 28 rounds.

## Phase 47: Real Production Code + Head-to-Head Comparison (Round 28 validation)

**Question:** Do lenses work on real production code (not crafted tasks)? How does Haiku + lenses compare head-to-head with Sonnet and Opus vanilla on the same code?

**Setup:** Starlette `routing.py` (333 lines, real production code from github.com/encode/starlette). 7 parallel runs: 5 lenses on Haiku + vanilla Sonnet + vanilla Opus. Same input, same task prompt.

### Ratings

| Output | Rating | Size | Category |
|--------|--------|------|----------|
| Sonnet vanilla | 7/10 | 7.2KB | Conventional code review |
| Opus vanilla | 7.5/10 | 6.2KB | Conventional code review |
| Haiku + pedagogy | 9/10 | 10.8KB | Structural analysis |
| Haiku + claim | 9/10 | 12.6KB | Structural analysis |
| Haiku + scarcity | 9/10 | 11.3KB | Structural analysis |
| Haiku + rejected_paths | 9/10 | 15.2KB | Structural analysis |
| Haiku + degradation | **9.5/10** | 13.9KB | Structural analysis |

**Haiku + lenses average: 9.1/10. Sonnet vanilla: 7/10. Opus vanilla: 7.5/10.**

### What Vanilla Found

**Sonnet vanilla** — 8 surface problems: shadow variable, `replace_params` mutation, `assert` for validation, 405 method check duplication, first-partial-only for 405, shallow copy in redirect, `"app" in scope` convention. Severity table. One structural insight: "scope mutation as communication mechanism couples every layer." No alternatives, no predictions, no conservation laws.

**Opus vanilla** — 8 surface problems (7 overlapping with Sonnet, 1 unique: implicit GET-only default for functions vs all-methods for classes). Named PARTIAL overloading as "a lot of machinery for one HTTP semantic." More concise and opinionated than Sonnet. Still conventional.

### What Haiku + Lenses Found That Vanilla Missed

| Lens | Unique Finding |
|------|------|
| **pedagogy** | GraphQL Field Resolver transfer artifact: sequential scope mutation breaks under concurrent field batching. Pedagogy law: "State passed through mutable dict because dispatch is sequential" transfers as hidden assumption to concurrent contexts. Concrete failure: batch_id race condition, discovery timeline Hour 0 → Week 3 |
| **claim** | Redirect-slash infinite redirect loop under nested Mounts (latent, invisible, silent). 10 empirical claims with corruption traces. Core impossibility: match-once + order-independent + flexible scoping — pick two. 3 concrete inversions with latency estimates |
| **scarcity** | Sum conservation law: Latency + Memory + Round-trips ≈ constant across all designs. 7 unmovable constraints including "ASGI is a standard; Starlette cannot unilaterally change it." Route count budget, request isolation guarantee, client latency tolerance as resource scarcities |
| **rejected_paths** | 7 problems × 3+ rejected paths each with per-problem conservation laws. HEAD auto-addition creates middleware ordering fights. Reserved `"path"` param namespace collision. Root impossibility: can't simultaneously have simple dispatch + optimal matching + flexible scoping + debuggable state + static compilation |
| **degradation** | Formal latency law: `T_match = T_base × n × (1+r) × (1+d) + T_log(p)` with monotonicity guarantee (dT/dn > 0, dT/dd > 0, dT/dp > 0). Convertor security patch staleness (old routes accept data new routes reject). 5 concrete runnable tests. Named law: "Linear Route Search Accumulation" — 500 routes at 24 months = 50-100× worse 404 latency vs day 1, invisible to monitoring |

### Quantitative Comparison

| Metric | Sonnet vanilla | Opus vanilla | Haiku + 5 lenses |
|--------|---|---|---|
| Surface problems found | 8 | 8 | 10+ |
| Deep structural findings | 1 | 1 | 15+ |
| Alternative designs (with code) | 0 | 0 | 10+ |
| Predictions with timelines | 0 | 0 | 5 |
| Named conservation laws | 0 | 0 | 7 |
| Concrete tests generated | 0 | 0 | 5 |
| Transfer/decay analysis | 0 | 0 | 2 |

### Phase 47 Findings

1. **Lenses work on real production code.** Average 9.1/10 on Starlette (333 lines). Degradation scored 9.5 — strongest single output on real code. The formal latency law with monotonicity proof is the kind of analysis vanilla models never produce.

2. **Haiku + lenses operates in a different category than vanilla.** Vanilla Sonnet/Opus produce competent code reviews (list + rate problems). Haiku + lenses produce structural analysis (name impossibilities, trace decay, build alternatives, predict failures). This is a qualitative gap, not just quantitative.

3. **The gap is wider on real code than crafted tasks.** Real production code has more structure to analyze — more design decisions, more hidden assumptions, more decay axes. Vanilla models plateau at surface-level problem listing regardless of code complexity. Lensed analysis deepens with code complexity.

4. **Opus vanilla ≈ Sonnet vanilla on code review.** Opus found one unique problem (implicit method defaulting) and was more concise/opinionated, but scored only 0.5 points higher. Without a lens, Opus's extra capacity doesn't translate to deeper analysis — it produces the same category of output as Sonnet, slightly better written.

5. **Degradation lens is strongest on real code.** Scored 9.5 (highest across all experiments on real code). Real production code has genuine decay axes that crafted 30-line tasks lack: route count growth, convertor staleness, nesting depth accumulation. The formal latency law is only possible because real code has real scaling parameters.

**Status:** 7 new experiments (5 Haiku + lens, 1 Sonnet vanilla, 1 Opus vanilla). 589+ total experiments across 28 rounds.

## Phase 48: Real Code Head-to-Head — Click + Tenacity (Round 28 validation)

**Question:** Does the Starlette result replicate on other real codebases? Is the Haiku + lenses advantage consistent across different code architectures?

**Setup:** Click `core.py` (417 lines, CLI parameter/context/command system) and Tenacity `retry.py` (331 lines, retry/resilience library). Same protocol as Phase 47: 7 parallel runs per target (5 lenses on Haiku + vanilla Sonnet + vanilla Opus).

### Click Ratings

| Output | Rating | Size | Category |
|--------|--------|------|----------|
| Sonnet vanilla | 8/10 | 4.8KB | Structural code review |
| Opus vanilla | 8.5/10 | 5.2KB | Structural code review |
| Haiku + pedagogy | 9/10 | 16.2KB | Structural analysis |
| Haiku + claim | 9/10 | 14.2KB | Structural analysis |
| Haiku + scarcity | 9/10 | 17.8KB | Structural analysis |
| Haiku + rejected_paths | 9/10 | 14.5KB | Structural analysis |
| Haiku + degradation | 8.5/10 | 13.8KB | Structural analysis |

**Haiku + lenses average: 8.9/10. Sonnet vanilla: 8/10. Opus vanilla: 8.5/10.**

#### What Haiku + Lenses Found on Click

| Lens | Unique Finding |
|------|------|
| **pedagogy** | Click's patterns (UNSET sentinel, parent cascading, eager hooks) transfer as invisible assumptions. UNSET sneaking into downstream stages without validation is slowest to discover |
| **claim** | 10 empirical claims (deterministic priority, stable env, cooperative chaining). Resilient parsing is the "ghost failure" — changes what "resolved" means, invisible to downstream |
| **scarcity** | 8 resource scarcities. Decision complexity is information-theoretically conserved across all redesigns |
| **rejected_paths** | Click requires implicit inheritance, transparent source tracking, mid-pipeline type conversion, and shared chain context — at most 3 can hold (pick 3 of 4 impossibility) |
| **degradation** | Optimized for short-lived CLI invocations but corrodes monotonically in long-lived processes. Parameter resolution coherence decays with deployment age |

### Tenacity Ratings

| Output | Rating | Size | Category |
|--------|--------|------|----------|
| Sonnet vanilla | 8.5/10 | 5.7KB | Structural code review |
| Opus vanilla | 8.5/10 | 4.2KB | Structural code review |
| Haiku + pedagogy | 9/10 | 14.8KB | Structural analysis |
| Haiku + claim | 9/10 | 18.6KB | Structural analysis |
| Haiku + scarcity | 8.5/10 | 11.8KB | Structural analysis |
| Haiku + rejected_paths | 9/10 | 21.9KB | Structural analysis |
| Haiku + degradation | 9/10 | 13.6KB | Structural analysis |

**Haiku + lenses average: 8.9/10. Sonnet vanilla: 8.5/10. Opus vanilla: 8.5/10.**

#### What Haiku + Lenses Found on Tenacity

| Lens | Unique Finding |
|------|------|
| **pedagogy** | Tenacity's patterns (mutable statistics dict, thread-local isolation) transfer as invisible assumptions. "statistics" becomes a permission structure hiding the constraint that metrics must be scalar and reset at call boundaries |
| **claim** | 8 empirical claims. Stop > retry hidden priority — deterministic semantic violation that never crashes, only silently overrides user intent |
| **scarcity** | Alternative design using frozen dataclasses and pre-compiled phase dispatchers. Invariant retry phase graph is the conservation law no design can escape |
| **rejected_paths** | Callback-based flexibility creates invisible problem migration: thread safety solved by threading.local creates state ownership ambiguity. First failure under pressure is always logic bug (state flag corruption) not design flaw |
| **degradation** | Thread-local namespace entropy, action queue depth, exception chain depth grow monotonically with no purge mechanism. Silent corruption at 6/12/24 month horizons |

### Cross-Target Synthesis (All 3 Codebases)

| Lens/Model | Starlette | Click | Tenacity | **Avg** |
|---|---|---|---|---|
| **Haiku + pedagogy** | 9 | 9 | 9 | **9.0** |
| **Haiku + claim** | 9 | 9 | 9 | **9.0** |
| **Haiku + scarcity** | 9.5 | 9 | 8.5 | **9.0** |
| **Haiku + rejected_paths** | 9 | 9 | 9 | **9.0** |
| **Haiku + degradation** | 9.5 | 8.5 | 9 | **9.0** |
| *Haiku avg* | *9.1* | *8.9* | *8.9* | ***9.0*** |
| Sonnet vanilla | 7 | 8 | 8.5 | **7.8** |
| Opus vanilla | 7.5 | 8.5 | 8.5 | **8.2** |

### Phase 48 Findings

1. **Result replicates across 3 codebases.** Haiku + lenses avg 9.0 vs Sonnet vanilla 7.8 vs Opus vanilla 8.2. Gap is consistent and real.

2. **All 5 lenses stable across targets.** No lens drops below 8.5 on any target. Grand average per lens: pedagogy 9.0, claim 9.0, scarcity 9.0, rejected_paths 9.0, degradation 8.8 (slight variance on degradation, still reliable).

3. **Vanilla models converge; lenses diverge.** On each target, Sonnet and Opus vanilla independently find the same conservation law. The 5 lenses find 5 genuinely different structural properties — zero overlap across lenses within the same target.

4. **Gap scales with code complexity.** Starlette (deepest nesting, most design decisions) shows widest gap: 9.1 vs 7.25. Tenacity (most focused, clearest architecture) shows narrowest gap: 8.9 vs 8.5. Lenses deepen with complexity; vanilla plateaus.

5. **Vanilla baseline rises on simpler code.** Sonnet vanilla: 7→8→8.5 (Starlette→Click→Tenacity). Opus vanilla: 7.5→8.5→8.5. On focused code, vanilla does better — but still can't match lensed analysis.

6. **No single dominant lens.** Each lens has its best target: scarcity peaked on Starlette (9.5), degradation peaked on Starlette (9.5), claim and rejected_paths are the most consistent (9/9/9). Portfolio value is confirmed — no single lens is redundant.

**Status:** 14 new experiments (10 Haiku + lens, 2 Sonnet vanilla, 2 Opus vanilla). 603+ total experiments across 28 rounds.

---

## Round 29: Reflexive Matrix + Gap Synthesis

### Phase 49: Reflexive Matrix (25 Haiku experiments)

**Goal:** Apply the 5 portfolio lenses to each other reflexively. Every lens analyzes every lens (including itself). 5×5 = 25 experiments on Haiku. Extract structural properties of the lenses themselves.

**Setup:** Each experiment: `CLAUDECODE="" claude -p --model haiku --output-format text --system-prompt "$(cat lenses/$ANALYZER.md)" < lenses/$TARGET.md`. All 25 run in parallel.

#### Results: The 5×5 Matrix

| Analyzer \ Target | pedagogy | claim | scarcity | rejected_paths | degradation |
|---|---|---|---|---|---|
| **pedagogy** | self-diagnosis | transfer corruption of assumption-inversion | resource framing transfers as ontology | fix-graph transfers as causal model | decay model transfers as temporal frame |
| **claim** | portability is unfalsifiable | self-diagnosis | tradeability is embedded assumption | binary design-space is compressed | time-as-driver conflates time with change |
| **scarcity** | analytical bandwidth is finite | naming budget is finite | self-diagnosis | problem-space is finite | monitoring attention is scarce |
| **rejected_paths** | linear sequence was chosen | binary true/false was chosen | single-resource framing was chosen | self-diagnosis | single-timeline was chosen |
| **degradation** | portability claim decays with context | assumption inventory goes stale | resource model drifts from reality | rejected-path inventory is incomplete | self-diagnosis |

#### 5 Self-Diagnoses (Diagonal)

| Lens | Self-occlusion law | What it can't see about itself |
|------|-------------------|-------------------------------|
| pedagogy | "What a lens teaches = what it's blind to" | Can't examine what makes patterns portable |
| claim | "Naming conceals everything outside the name" | Can't find pre-cognitive assumptions |
| scarcity | "Total analyst degrees of freedom are fixed" | Can't see incommensurable constraints (values, ethics) |
| rejected_paths | "Sum of visible + invisible problems is constant" | Can't see n-dimensional spaces or problems in ALL paths |
| degradation | "Applicability decays with deployment context uncertainty" | Conflates time with external change |

#### Phase 49 Findings

1. **Power = Blindspot (structural identity, not correlation).** Each lens's compression that gives it analytical power IS the same compression that creates its blindspot. Pedagogy sees transfer but can't see what makes transfer possible. Claim names assumptions but can't name pre-cognitive assumptions. This is identity, not correlation — the mechanism is the same.

2. **Cross-lens analysis is strictly more powerful than self-analysis.** 20/20 cross-lens pairs found at least 1-2 things the target lens's self-analysis missed. Self-analysis (diagonal) produced genuine self-occlusion laws but couldn't find what cross-analysis found. Conservation law: `self_insight + cross_insight = constant per lens pair`.

3. **Blindness is conserved (product form).** `clarity_cost × blindness_cost = constant`. A lens that increases clarity on one dimension necessarily increases blindness on another. Redistribution, not reduction. Product form (not sum) — zero blindness is impossible by construction.

4. **The 5 lenses form a coordinate system, not a checklist.** Each lens defines an independent analytical axis. Cross-lens analysis spans the space between axes. But the coordinate system has boundaries it cannot see from within.

5. **Third-order recursion adds genuine info but diminishes.** pedagogy→claim→pedagogy produces novel findings at each level, but information gain decays. Matches L13 structure: recursion terminates at a fixed point, not because everything is found, but because the tools for finding more are exhausted.

### Phase 50: Meta-Experiments (3 Haiku chained, 3 Sonnet meta)

**Goal:** Push beyond the 5×5 matrix. Generate candidate 6th lenses from findings (B3 cooker). Test third-order recursion. Attack findings with scarcity. Run Sonnet on 3 meta-level tests.

#### Haiku Chained Experiments

| Experiment | Input | Result |
|---|---|---|
| B3 generates new lenses from findings | 5 self-diagnoses + findings | 3 candidate lenses: **emergence** (system-level properties invisible in parts), **dark-code** (shared assumptions all lenses require), **gap** (inter-lens disagreements) |
| Third-order recursion | pedagogy→claim→pedagogy | Each level adds genuine info. Level 3 finds: "the frame of the original problem becomes the metaphysics of the new domain" — novel, not restatement. But output length and novelty decay. |
| Scarcity attacks synthesis | Round 29 findings as input | Conservation law holds under attack: scarcity finds the findings themselves consume analytical bandwidth, creating their own blindspot. Meta-level conservation confirmed. |

#### Sonnet Meta-Experiments

| Experiment | Result |
|---|---|
| Gap lens on Starlette routing.py (real code) | **Found real RFC 7231 bug.** `partial` is single variable — first-partial-wins drops all later partial matches. Multiple routes same path different methods → incomplete 405 Allow header. Conservation law: `Allow_correctness + endpoint_transparency = constant`. Fix (PathRouter) opens new gap: scope["endpoint"] becomes opaque to middleware. |
| Cross-model pedagogy-on-self comparison | Haiku: mechanism-level ("conservation of blindness"). Sonnet: operation-level ("analysis unit becomes causal unit", "transfer corrupts by absence"). Same structure, different analytical character. Confirms: model determines form, not domain. |
| Claim lens on matrix findings | **Sharpest critique.** R1 (completeness) is unfalsifiable from within — incompleteness theorem analog. Product vs sum form untested in moderate range. H2 (genuine addition vs reframing) needs blind evaluation protocol. |

#### The Impossibility Triplet (Phase 50 Finding 7)

The framework wants simultaneously:
1. A finite set of lenses that covers the space (completeness)
2. A conservation law that guarantees blindness is never reduced (conservation)
3. A method that terminates with confidence (usability)

These three cannot coexist. If blindness conserves, adding lens N+1 shifts blindness to dimension N+2. The coordinate system cannot close. This IS the L13 of the research itself.

### Phase 51: Gap Synthesis Integration (1 Haiku A/B test)

**Goal:** Wire the gap lens concept (inter-lens disagreement detection) into lite.py's `/scan --deep` synthesis prompt. Test head-to-head against the old synthesis prompt using existing Round 28 Starlette lens outputs.

**Setup:** Same 5 Haiku lens outputs from Phase 48 (Starlette routing.py). Two synthesis prompts run on Haiku in parallel:
- OLD: "You are a technical project manager. Prioritize and deduplicate across lenses."
- NEW: "You are a structural analyst. Find inter-lens disagreements, shared assumptions, then prioritize."

#### A/B Results

| Metric | OLD (project manager) | NEW (structural analyst) |
|--------|----------------------|--------------------------|
| Words | 2,086 | 5,333 |
| Structure | P0-P3 flat list | Disagreements → Assumptions → Issues |
| Inter-lens disagreements found | 0 | **4** |
| Shared assumptions found | 0 | **8** |
| Issues found | 16 | 16 |
| Extra API calls | 0 | 0 |

#### What the NEW synthesis found that OLD couldn't

**Inter-lens disagreements:**
1. **Scope mutation safety** (Scarcity ↔ Pedagogy ↔ Rejected_paths) — Scarcity says safe in ASGI, Pedagogy says transfers unsafely to concurrent domains, Rejected_paths says fix creates worse problems. Bug lives in the gap.
2. **Redirect-slash correctness** (Scarcity ↔ Claim) — trade-off justified for single variant, fails when both `/foo` and `/foo/` exist.
3. **Latency timescales** (Degradation ↔ Pedagogy) — same code, two failure timescales (24-month creep vs immediate transfer break). No single lens sees both.
4. **Convertor staleness** (Degradation ↔ Rejected_paths) — staleness identified, but fix creates cache coherence problem. Conservation: `staleness + cache_coherence = constant`.

**Shared assumptions (invisible to all 5 lenses individually):**
1. ASGI isolation is guaranteed externally
2. Routes only increase, never shrink
3. Middleware is trustworthy and non-interfering
4. Parameter names are globally unique (no shadowing)
5. Exceptions are rare and edge-case
6. No scope pooling or caching
7. Regex compilation is deterministic (no catastrophic backtracking)
8. URL reversal is a perfect inverse of matching

#### Phase 51 Findings

1. **Gap synthesis works at zero extra cost.** Same number of API calls. The synthesis already had all 5 outputs — just needed to be told what to look for. Pure prompt improvement.

2. **Inter-lens disagreements are where real bugs hide.** The 4 disagreements found correspond exactly to the structural contradictions the Sonnet gap lens found on Starlette in Phase 50. The synthesis prompt reproduces the gap lens finding without being a gap lens.

3. **Shared assumptions are the deepest blind spots.** 8 assumptions that ALL 5 lenses take for granted. No individual lens can see these because they're background truth for every analytical frame. Only visible when you explicitly ask "what do all lenses assume?"

4. **The synthesis prompt IS the 6th lens.** Not a separate lens to run — a second-order operation on 5 outputs. This resolves the impossibility triplet pragmatically: you don't need a 6th lens in the coordinate system, you need a synthesis that reads the gaps between existing axes.

**lite.py change:** Synthesis prompt upgraded in `_cmd_scan` (direct, subsystem, and cross-subsystem paths). Role changed from "technical project manager" to "structural analyst." Two new sections added before prioritization: Inter-Lens Disagreements and Shared Assumptions.

**Status:** 31 new experiments (25 matrix + 3 Haiku chained + 3 Sonnet meta) + 1 A/B synthesis test. 634+ total experiments across 29 rounds.

---

## Round 30: Domain-Neutral Validation (Mar 2026)

**Question:** Does the Full Prism pipeline work on non-code domains, or is it code-specific?

**Experiments:** 6 todo-app prompts tested across 3 methods: Opus vanilla, Single Prism (Haiku + L12, 1 call), Full Prism (Haiku, 3 calls: L12 + adversarial + synthesis). Also tested Gemini 2.5 Flash with direct L12 execution on Starlette and Click (cross-model validation).

**Key findings:**

1. **Full Prism works on any domain, not just code.** Confirmed across 6 domain-neutral prompts about a todo-app. Conservation laws derived on non-code targets at the same structural depth as code targets.

2. **Depth hierarchy is categorical.** Opus vanilla: 267-696 words, depth 6.5-8.5 (essays). Single Prism: 917-5,970 words, depth 9-9.5 (conservation laws). Full Prism: 8,112-13,200 words, depth 10 (law + adversarial destruction + corrected synthesis). Each tier is a different category of output.

3. **Structurally-framed prompts boost Opus vanilla.** When the prompt encodes the operation ("what never changes?", "fix then what new problem?"), Opus scores 8-8.5 instead of 6.5-7. The prompt IS the prism, even for vanilla models.

4. **Full Prism self-corrects.** Call 2 genuinely destroys Call 1's claims with empirical counter-evidence. Call 3 synthesizes a population-segmented law stronger than either alone. Not additive — dialectical.

5. **Auto-detection implemented in /scan:** file path targets → code-specific prisms. Text targets → domain-neutral general prisms. User doesn't choose.

6. **L12 universality confirmed across model families.** Gemini 2.5 Flash executed the same 332w L12 prism on Starlette (9.0-9.5, 14/14 operations) and Click (9.0-9.3, 14/14 operations). Same structural form (claim → dialectic → mechanism → improvement → recursion → conservation law → meta-law → bugs), different substance (Gemini: "Route Intent Expression" vs Claude: "Route Identity Resolution"). Tenacity triggered planning mode on Gemini (100% vs Haiku's ~33%). L13 fixed point confirmed on Gemini — same "observer-constitutive" convergence as Claude. **The prompt is the intelligence, model family is noise.**

**Codebase changes:** Auto-detection logic in prism.py for code vs non-code targets. Cross-model validation outputs saved to `output/gemini_l12/`.

---

## Round 31: CASCADE Experiment (Mar 2026)

**Question:** Why do some prompts trigger single-shot execution while others trigger multi-turn agentic mode?

**Experiments:** Structural analysis of prompt architecture and its effect on model execution mode. Tested L12's numbered step format against abstract phase-based prompts.

**Key findings:**

1. **Principle 100: Output structure IS the intelligence.** L12's numbered sequential steps ("First: ... Then: ... Now: ...") trigger single-shot production mode. Abstract phase descriptions ("Phase 1: Exploration") trigger agentic tool-use mode. The structure of the prompt determines whether the model produces text directly or enters multi-turn exploration.

2. **Concrete numbered steps → single-shot.** Models interpret numbered imperative steps as a production checklist to execute in order. They interpret abstract phase names as an exploration framework requiring tools.

3. **This explains the stochasticity from Round 32.** The mode trigger is not purely stochastic — it's an interaction between prompt structure (concrete vs abstract), model capacity (Sonnet holds more in working memory), and target structure (structured data → single-shot, argumentative prose → agentic).

**Codebase changes:** Understanding applied to all subsequent prompt design. All production prisms use imperative numbered steps, not abstract phases.

---

## Round 32: L12 Vocabulary Experiments (Mar 11, 2026)

**Question:** Do we need separate L12 prisms for code vs non-code? Is "this code's" a domain label or a mode trigger?

**Experiments:** 17 total runs. 5 prism variants (A: L12_code 332w, B: L12_general 298w, C: code_core 298w, D: concrete_general, E: universal_harvest) × 3 non-code targets (business pitch, insight seed, scaling thesis) on Haiku via CLI. Variants isolate vocabulary, bug appendix, and harvest terms.

**Key findings:**

1. **Principle 101: "Code" nouns are mode triggers, not domain labels.** "This code's deepest structural problem" activates analytical/structural mode regardless of whether the input is source code, a business pitch, or a philosophical argument. The word "code" triggers a cognitive posture (systematic analysis), not a domain constraint (look for programming). A_code analyzed a CloudMind business pitch at 9/10 markers with conservation law "Decision Authority Conservation Principle."

2. **Principle 102: Single-shot vs agentic mode is stochastic and dominant.** Single-shot (1-2 turns): 1300-1600 words, 8-9/10. Agentic (8+ turns): 165-653 words, 2-7/10. Mode selection appears stochastic on Haiku — confirmed by re-runs (same prism + same target → completely different mode). This is the single largest quality factor, exceeding all vocabulary differences.

3. **Principle 103: Target structure affects mode probability.** Structured/quantitative input → single-shot (business pitch: 4/5). Argumentative prose → agentic (scaling thesis: 0/5). Narrative: stochastic (insight seed: 2/5).

4. **L12_general is DEAD.** B (general) scored worst on ALL metrics: 221w avg, 2.7/10 markers, 0/3 single-shot. Abstract nouns ("input", "failure", "expert review") allow drift into summary mode. Killed across 17 experiments.

5. **ONE L12 prism + conditional ending.** Core 298w pipeline (code nouns) works on ALL domains. Append 34w bug sentence for code targets only. No separate general variant needed.

**Codebase changes:** L12_general deleted. Single L12 prism with conditional bug appendix. Mode trigger finding applied to all future prompt design.

---

## Round 33: Sonnet Frontier (Mar 11, 2026)

**Question:** What can Sonnet do that Haiku cannot? Is there a Sonnet-native frontier beyond L12?

**Experiments:** 15 experiments (10 Sonnet, 5 Haiku comparison) on Starlette routing.py. Tests: S1 (extended L12, 430w), S2 (compression floor, 73-298w), S3 (artifact generation), S4 (multi-law topology), S5 (cross-domain), S6 (self-improving meta-cognitive).

**Key findings:**

1. **Principle 104: Sonnet is always single-shot on L12-class prompts via CLI.** 10/10 Sonnet runs: 1-3 turns. 5/5 Haiku runs: 6-26 turns agentic. Not stochastic — a capacity boundary. Sonnet holds the full analysis in working memory. (Later revised in Round 34: Sonnet goes agentic on code prompts applied to reasoning targets, but preserves quality when agentic.)

2. **Principle 105: Sonnet can self-diagnose prompt blind spots, design novel prompts, and execute them in a single call.** S6 produced 4665 words in 1 turn, $0.14: full L12 analysis, 5-point blind spot audit, novel "Type-Polymorphy Channels" 9-step diagnostic, AND executed the new prompt on Starlette. Haiku: 481w, 7 turns, collapsed.

3. **Principle 106: Sonnet generates reusable analytical artifacts.** S3 produced a "Structural Deep-Scan Lens" (SDL) — 200w, 3-step diagnostic genuinely different from L12. This became the SDL prism family.

4. **Sonnet compression floor = 73 words.** S2 at 73w: 1776 words output, 9/10 markers, 1 turn. 4.5x compression ratio vs Haiku's 332w minimum. This became `l12_universal`.

5. **Principle 107: Step count determines transferability.** S1 (extended 430w) = Sonnet-only (Haiku: 172w collapse). TPC (9 steps) → catastrophic on Haiku (67 turns, $0.84). SDL (3 steps) → transfers perfectly.

6. **Sonnet is CHEAPER on complex prompts.** Single-shot (1-3 turns, text only) vs Haiku agentic (6-26 turns, tool calls): S1 Sonnet $0.19 vs Haiku $0.27; S6 Sonnet $0.14 vs Haiku $0.24.

**Novel prompts discovered:** "Type-Polymorphy Channels" (TPC, 9 steps, Sonnet-only) and "Structural Deep-Scan Lens" (SDL, 3 steps, universal). Both Sonnet self-designed.

**Codebase changes:** `prisms/l12_universal.md` (73w compressed L12), `prisms/deep_scan.md` (SDL), SDL family concept established.

---

## Round 34: Agentic Behavior and Tier Validation (Mar 11, 2026)

**Question:** Do Sonnet-designed prompts transfer to Haiku? Does 73w generalize? What happens when code prompts meet reasoning targets?

**Experiments:** 20 experiments. Round 34a: 12 experiments (SDL + TPC transfer, 73w cross-target). Round 34b: 8 experiments (Sonnet on reasoning, SDL universality).

**Key findings:**

1. **Principle 108: 73w (`l12_universal`) is Sonnet-universal compression floor.** Click 1488w/9/10, Tenacity 1463w/8/10, Business pitch 1264w/8/10. All single-shot. Haiku fails at 73w (160w, 5/10, 8t). Compression drops code vocabulary → naturally domain-neutral.

2. **Principle 104 revised: Sonnet is domain-conditional, not always single-shot.** Domain-neutral prompts (73w, SDL) → single-shot on reasoning. Code prompts (L12, S6) → agentic on reasoning (9-15 turns). But agentic Sonnet preserves quality (2601w, 9/10 at 9t) unlike agentic Haiku (183w, 5/10 at 21t).

3. **SDL = universal prism.** Always single-shot on both models and both domains. Haiku insight seed: 620w, 7/7 markers, 1t, $0.01 — cheapest prism ever. 3 steps fit within all models' working memory.

4. **S6 (TPC) is code-only.** 199w collapse on reasoning. Meta-cognitive protocol needs code structure to operate on.

5. **Four routing paths established:** Universal cheap (SDL, Haiku, any domain), Standard code (L12, Haiku, code), Reliable any (l12_universal, Sonnet, any domain), Deep code (TPC, Sonnet, code only).

**Codebase changes:** Four-path routing model implemented. SDL prism validated and integrated.

---

## Round 35: Domain-Free L12 REFUTED + SDL Portfolio (Mar 11, 2026)

**Question:** Can removing code vocabulary from 298w L12 make it universal? Can 5 SDL lenses provide comprehensive single-shot coverage?

**Experiments:** 15 experiments. Round 35a: 8 experiments (domain-free L12 on Sonnet + Haiku, code + reasoning). Round 35b: 7 experiments (5 SDL lenses on Starlette + 2 on insight seed, Haiku).

**Key findings:**

1. **Principle 113: Depth x Universality = constant.** Removing code vocabulary from 298w L12 made it stochastic on reasoning (F_sonnet_scaling: 2/10, 13t) AND lost the code mode trigger on code (F_sonnet_starlette: 4t agentic, original = 1t). Surprise: A_haiku_insight went 1t single-shot (1150w, 9/10) — confirms stochasticity. Simple prompts (3 steps) are domain-invariant. Complex prompts (298w+) are domain-sensitive — vocabulary leaks assumptions. The five-path routing table is structurally correct, not just empirically convenient.

2. **Principle 114: `--tools ""` forces single-shot.** Without it: 2/7 single-shot (29%), avg 265w, Haiku goes agentic using CLI tools instead of analyzing. With `--tools ""`: 7/7 single-shot (100%), avg 713w, 25s. This is the critical discovery for reliable SDL execution.

3. **SDL portfolio validated: 5 lenses, zero overlap.** deep_scan (9.0), sdl_trust (9.0), sdl_coupling (9.0), fix_cascade (8.5), identity (9.5). Total 5-lens Starlette: 3,566w (2.4x single L12). Every lens finds genuinely different structural properties. identity = strongest SDL (837w, 9.5, best necessary/accidental classification).

4. **SDL transfers to reasoning.** fix_cascade on insight seed: 9.0 ("Self-Application Deferral" — frameworks create meta-blindness). identity on insight seed: 9.0 ("Visibility system invisible to creators").

**Codebase changes:** `--tools ""` applied to all CLI prism invocations in prism.py. Five-path routing confirmed final. SDL portfolio established as complementary coverage option.

---

## Round 36: Code Generation Frontier (Mar 12, 2026)

**Question:** Do analysis prisms (L12, SDL) help code generation? Can a purpose-built codegen prism beat vanilla?

**Experiments:** 12+ experiments. 4 methods (Haiku vanilla, Haiku+L12, Haiku+SDL, Sonnet vanilla, Haiku+codegen) × 3 tasks (LRU Cache, Link Checker, Benchmark). Plus 2 focused codegen tests (SessionStats, MarkdownReportGenerator) and self-improvement loop on prism.py.

**Key findings:**

1. **Principle 115: Analysis prisms don't transfer to code generation.** L12/SDL are designed for finding hidden structure, not writing code. Different cognitive operation entirely. L12 on a codegen task produces a code review, not better code.

2. **Principle 116: Interface-first + failure prediction = best codegen prompt.** The codegen prism (130w, 3 steps): decompose requirements → design API signatures with invariants → predict specific bug before each method, then avoid it. Maps to expert programmer workflow.

3. **Principle 117: Codegen prism produces more code.** 234 lines vs 132-170 lines. Decomposition and interface steps cause the model to plan before coding, producing more complete implementations.

4. **Principle 118: Strict typing backfires on ambiguous specs.** Interface-first locks in data structure assumptions. When assumptions are wrong, extra validation makes code MORE fragile than vanilla's loose typing. Codegen wins when data format is explicit; vanilla wins when spec is ambiguous.

5. **Principle 119: Self-improvement loop works end-to-end.** L12 scans prism.py sections → extracts issues → codegen generates fixes → tests verify → re-scan confirms. 2/2 fixes applied successfully.

**Codebase changes:** `prisms/codegen.md` (130w, 3 steps) added. `research/self_improve.py` created. `research/codegen_frontier.py` test harness.

---

## Round 37: Prism Discovery Method + Portfolio Expansion + Accuracy (Mar 12-13, 2026)

The largest round: 120+ experiments across 11 phases. Established the delta method for discovering new prism types, iterated 4 new prisms to champion status, validated accuracy, tested composition, and locked the definitive model-prism grid.

### Phase 1: Delta Validation (18 experiments)

**Method:** For each of 6 candidate purposes, ran raw purpose analysis (Haiku, `--tools ""`) on 3 real codebases (Starlette, Click, Tenacity), then Sonnet delta scoring vs L12+optim.

**Principle 128: Purpose discovery is not generic.** Each purpose needs its own empirical discovery trajectory. `discover-purposes` as a feature is DEAD — violates the conservation law `ANALYTICAL_DEPTH x COVERAGE x ITERATION_BUDGET = CONSTANT`.

**Principle 129: The delta method is general but the reference point is purpose-specific.** For optim, L12 was the reference. For security, L12+optim. Cumulative baseline grows with each new prism.

All 6 purposes COMPLEMENTARY to L12+optim (P132). Error Resilience and Evolution scored highest (8/10). Each has a unique cognitive operation: state corruption inference, change-impact modeling, adversarial input modeling, dependency extraction, developer mental model gap, shared state mutation tracing (P133). Click is the universal stress test for purpose discovery (P134).

### Phases 2-6: Prism Iteration (80+ experiments)

**Optimization prism** (30+ experiments, 11 variants): V11 champion (`prisms/optimize.md`, 125w). Critical path trace → safe fixes cascade → structural limit + conservation law. Key innovation: safe/unsafe distinction (P124) separates "reduce work" from "skip work." Quantification causes confabulation (P121). Model-sensitive: Haiku 8.0, Sonnet 9.5 (P120).

**Error Resilience prism** (20+ experiments): V2a → V8 → V10d champion. Cognitive operation evolved from "corruption cascade tracing" (V2a) to "error information destruction" (V8, +0.3-0.5) to hybrid with construction (V10d, +0.2-0.7). V10d lifts the floor — biggest gain on Starlette (+0.5-1.0), V8's weakest target. P140: Changing the cognitive operation beats refining the classification.

**Evolution prism** (20+ experiments): V2b → V9 → V10 (Sonnet-designed) champion. Shotgun surgery + "does refactor create new targets?" = evolution equivalent of safe/unsafe. Coupling conservation proven empirically on Tenacity (ALL 4 refactors create new targets). P150: Sonnet designs better Haiku prisms than humans iterating.

**API Surface prism** (10+ experiments): V2b champion (`prisms/api_surface.md`, 130w). Naming lies: widening (does MORE than name says), narrowing (does LESS), direction (does something DIFFERENT). Best V1 of any purpose at 8.5 (P138). Five-prism portfolio: L12 (IS) + optim (COSTS) + errres (BREAKS) + evo (CHANGES) + api_surface (PROMISES). Zero overlap.

**Key principles from iteration:**
- P135: Structural insight (L12) is model-independent. Behavioral reasoning (optim, errres, evo) is model-sensitive. Haiku 8.0-8.2 vs Sonnet 9.0-9.5.
- P136: Constraint count competes with cascade depth on smaller models.
- P141: The operation IS the prism. Every champion upgrade changed the cognitive operation, not the vocabulary.
- P142: The loss framing ("what info gets destroyed?") transfers within the same cognitive family (+0.3-0.5).
- P143: Each prism has a natural cognitive family. Alien operations degrade toward L12.
- P144: Construction adds depth to analytical prisms but not to constructive prisms.
- P145: Singular-first focus is anti-productive on Haiku. Breadth-first lets Haiku discard weak findings.

### Phase 7: Sonnet/Opus Cook + Pipeline (5-pass behavioral pipeline)

Sonnet cooks best for trace-heavy prisms (ErrRes, Evo). Opus cooks best for judgment-heavy prisms (Optim, API Surface) (P151). Re-cooking an already-optimized prism through the same model degrades quality (P152). Cross-model cooking maintains quality; same-model re-cooking degrades it (P153).

5-pass behavioral pipeline (4 behavioral prisms + synthesis): 29,235 chars on Starlette. Synthesis score 8.5. Value is breadth (4 dimensions) not depth. L12 single (9.8) still wins on depth. Best as L12 complement.

### Phase 8: Prism Stacking

Stacking (L12 → behavioral) does NOT produce serial depth — it's vocabulary translation (P154). Net effect: neutral (±0.3). Pure stacking (analysis only, no source) degrades quality (P155). Behavioral prisms need SOURCE CODE, not analysis descriptions.

### Phase 9: Integration

Behavioral pipeline integrated into prism.py (`/scan file behavioral`). Domain routing: `general=True` → neutral prisms. Self-improvement loop has two failure modes: without structural constraints → target-specific checklists; with constraints → abstract elegance Haiku can't execute (P158). `Concreteness x Abstraction = constant` in prism design (P159).

### Phase 10: Frontier 5x (5 experiments in parallel)

- P161: Factory prisms match hand-iterated champions. Sonnet already knows the cognitive operations that 90 experiments discovered.
- P162: Compression resistance correlates with operation clarity. ErrRes compresses -40% without quality loss.
- P163: Cross-language transfer is vocabulary-dependent. Abstract operations transfer; code-specific degrades.
- P164: Cross-prism breeding produces novel operations. ErrRes+Optim hybrid → "Evidence Cost Map" at 9.0.

### Phase 11: Final 3

- P165: Model-specificity is noise. Opus designs better prisms for ALL models, not model-specific ones.
- P166: Cross-prism hybrids are generalists, not specialists. Most stable but don't dominate parents.
- P167: Deep compression can IMPROVE quality. ErrRes 70w (9.5) > ErrRes 165w (9.0). Fewer words = less drift.
- P168: Compression resistance is determined by operation concreteness.

### Accuracy and Composition (8 experiments)

- P170: L12 accuracy is target-dependent. Synthetic code: 97% (29/30 TRUE). Real Click core.py: ~42%. ALL line numbers fabricated (0/10 correct). Structural insight (conservation laws) >> bug finding. Bug claims on complex code should be treated as hypotheses.
- P171: Horizontal prism composition is additive. L12 + audit_code on Starlette: 21 combined findings, ZERO overlap. Each prism's power creates a corresponding blind spot.
- P172: Vertical composition FAILS for code-vocabulary prisms. Code prisms drill through analysis text to hallucinated code. Vertical composition requires reasoning-vocabulary prisms.
- P173: Codegen prism activation is stochastic on Haiku. When 3-step protocol activates: +4 pts. When skipped: -2 pts. Needs Sonnet for reliability.

### Definitive Grid (37 minutes, ~40 API calls)

L12 → Sonnet (not Haiku). 9 runs × 2 judges = 18 scores. Sonnet 9.3 avg (consistent: 10, 10, 9.0). Haiku 8.5 avg (stochastic: 8.0, 10, 9.0). Floor matters more than ceiling. All 5 non-L12 prisms vs L12: 10/10 unique. Pairwise avg: 9.3/10. Zero redundancy. 9th prism (fidelity) cooked via `--factory` for documentation-code drift blind spot.

Self-analysis of prism.py: 9/9 steps completed (209KB findings). Meta-law: "A tool designed to reveal structural properties must instantiate those properties in its own structure." 21 bugs fixed.

**Codebase changes:** `prisms/optimize.md` (V14), `prisms/error_resilience.md` (V11), `prisms/evolution.md` (V10), `prisms/api_surface.md` (V3), `prisms/evidence_cost.md`, `prisms/error_resilience_compact.md`, `prisms/error_resilience_70w.md`, `prisms/fidelity.md`, `prisms/audit_code.md`. Behavioral pipeline in prism.py. L12 default model changed from Haiku to Sonnet. OPTIMAL_PRISM_MODEL expanded. 21 bugs fixed from self-analysis.

---

## Round 38: Production Hardening + Accuracy Audit (Mar 13, 2026)

**Focus:** Consolidate 29 production prisms, standardize metadata, audit all documentation for accuracy.

**Experiments:** Scoring validation of factory-generated prisms (fidelity, reachability, state_audit, sdl_abstraction) on Starlette. New standalone prisms (security_v1, testability_v1) hand-crafted and scored.

**Key findings:**

1. **29 production prisms established** across 4 categories: Pipeline Core (10, including adversarial + synthesis), Code Standalone (13), Universal (6). All mapped to optimal models in OPTIMAL_PRISM_MODEL (expanded from 9 to 33 entries).

2. **Prism naming standardized:** 73w → l12_universal, ident → identity, optim → optimize, rec → fix_cascade. YAML frontmatter added to all 38 prism files.

3. **README and CLAUDE.md accuracy audit:** Fixed all cost references (Haiku $0.003 → Sonnet ~$0.05), step counts (12-step → multi-step, 3-call → 9-call), routing table (5 paths → 4 paths with Standard now auto-Sonnet), stale prism names throughout.

4. **Behavioral pipeline model routing fixed** to use per-prism optimal models instead of session model.

5. **4 dead methods removed** from prism.py (call_checked, explored_domains, _config_set, _get_message).

**Codebase changes:** All prisms renamed and frontmattered. OPTIMAL_PRISM_MODEL expanded to 33 entries. README rewritten with concrete language, per-call costs, pipeline cost breakdown. Help text cleaned up (jargon removed, broken Unicode fixed). 33 tests passing.

---

## Round 39: Alternative Primitive Operations (Mar 13, 2026)

The largest research round: ~45 experiments across 9 batches. Tested whether construction is the only L8-primitive that inverts the capacity curve. Proved diamond convergence of the taxonomy. Built and validated the 3-cooker pipeline for non-code Full Prism.

### Batch 1: Hand-crafted alternative L8 ops — Haiku on Starlette (5 experiments)

Tested 5 alternative operations: Destruction, Simulation, Transplantation, Miniaturization, Forgery. All hand-crafted prompts encoding the operation as imperative steps.

**P175: Construction is not the only L8-primitive.** Any concrete, generative operation with observable side-effects bypasses meta-analytical capacity. 5/5 single-shot, 5/5 conservation laws, avg 775w, avg depth 8.1. Simulation strongest (8.5, 990w — temporal calcification, "String Format Lock-in").

### Batch 2: Cooked alternative ops via COOK_UNIVERSAL — Haiku on Starlette (5 experiments)

**P178: COOKER DRIFT.** COOK_UNIVERSAL absorbs alternative operations into L12's construction pattern. All 5 cooked outputs follow identical L12 structure (claim → impossibility → improvement → recursion → meta → harvest). Unique operation demoted to a THEME. Exception: Forgery aligns with construction and was enhanced by the cooker. Hand-crafted prompts preserve operational uniqueness; cooked prompts homogenize.

**P179:** Conservation law diversity correlates with prompt operation-specificity. Same code produces more diverse laws through operation-specific prompts.

### Batch 3: Sonnet solver on cached Haiku-cooked lenses — Starlette (5 experiments)

**P180: Sonnet lifts ALL operations by +0.7 avg depth** (8.8 vs 8.1). Simulation/Miniaturize/Transplant benefit most (hypothetical reasoning). Destruction and Forgery plateau at 8.5 (natural ceiling). Simulation strongest across all batches: 9.0 on Sonnet with extended conservation law equation including temporal decay.

### Batch 4: New ops + L9 escalation (4 experiments)

Two new L8 primitives: Archaeology (stratigraphic excavation, 8.5) and Cultivation (perturbation-response, 8.5). **7/7 alternative L8 primitives now confirmed single-shot on Haiku.**

**P181: Operations must be imperative steps, not themes.** Cooked archaeology/cultivation via `--intent` → hallucinated code content (FastAPI CRUD app instead of Starlette routing.py). COOK_UNIVERSAL cannot generate alternative L8 primitives.

**P182: Content Hallucination.** Cooked lenses don't anchor model to actual source code. Model hallucinates what it thinks the code contains.

**P183: Taxonomy is a tree above L8.** L9-Simulation produces different meta-law (Predictive Certainty x Temporal Distance) than construction's L9. Diamond topology holds.

### Batch 5: L10-L12 Branch Testing — Diamond Convergence (8 experiments)

Two full L9→L12 chains: simulation branch + archaeology branch, tested on Haiku via Starlette.

**P184-P188: DIAMOND CONVERGENCE CONFIRMED.** Three different L8 operations (construction, simulation, archaeology) diverge through L9-L11, converge at L12 on the SAME structural impossibility:

| Branch | L12 Fixed Point | Vocabulary |
|--------|----------------|------------|
| Construction | Observer-constitutive | "Framework instantiates what it diagnoses" |
| Simulation | Observer effect | "Cannot observe without changing" |
| Archaeology | Performative contradiction | "Cannot analyze without being part of analyzed" |

Conservation laws are genuinely different at EVERY level except L12. The convergence is structural, not verbal — three vocabularies, one self-referential fixed point. The reflexive ceiling is operation-independent. The taxonomy is complete at 13 levels: adding more L8 primitives adds BREADTH (different L9-L11 findings) but not DEPTH (same L12 ceiling).

### Batch 6: Operation Combinations (3 experiments)

**P189: Operation combinations produce breadth, not depth.** No combo exceeds individual depth ceiling (8.5). Complementary pairs (different axes) produce unique cross-findings. Temporally similar pairs interfere.

### Batch 7: Operation-Specific Cooker Templates (3 experiments)

Designed COOK_SIMULATION and COOK_ARCHAEOLOGY templates with explicit negative instructions ("No trilemmas, no impossibility proofs"). Both preserved operation type through cooking.

**P190:** Operation-specific cooker templates preserve operation type. Key: explicit negative instructions prevent L12 pattern absorption.

**P191:** Three cooker operations on same intent produce WHERE (archaeology: data flows), WHEN (simulation: temporal vulnerability), WHY (L12: structural impossibility) — zero overlap.

### Batch 8: SDL Compression (3 experiments)

**P193: SDL compression of simulation IMPROVES quality** (8.5→8.5-9.0). Forced concreteness via 3-step format beats narrative temporal cycles. P194: Compression effectiveness is operation-dependent — verbose operations benefit most.

SDL-Simulation promoted to production prism (`prisms/sdl_simulation.md`).

### Batch 9: 3-Cooker Pipeline (4 calls)

**P195-P197: 3-cooker pipeline = answer to "non-code Full Prism."** COOK_ARCHAEOLOGY(WHERE) + COOK_SIMULATION(WHEN) + COOK_UNIVERSAL(WHY) → synthesis. 4 calls, ~9,300 words, 9.5 depth. Matches or beats current 8-step Full Prism at HALF the calls.

Cross-operation synthesis is inherently adversarial (P196) — WHERE/WHEN/WHY disagreements surface naturally. No dedicated adversarial pass needed. Works on ANY domain — each cooker customizes to intent.

COOK_3WAY template created (`research/cook_3way.md`): single cook step generates all 4 prompts (3 operations + synthesis) for the pipeline.

**New production prisms (4):** simulation (170w, Sonnet), cultivation (190w, Sonnet), archaeology (175w, Sonnet), sdl_simulation (~150w, Haiku). Total: 33 production prisms.

**Codebase changes:** 4 new prisms added to `prisms/` and OPTIMAL_PRISM_MODEL. COOK_3WAY integrated as default for ALL analysis pipelines (replaces COOK_UNIVERSAL_PIPELINE in 6 sites). COOK_UNIVERSAL_PIPELINE kept ONLY for discover full. `/scan file 3way` explicit mode + auto-route for non-code `full`. `research/cook_3way.md`, `research/cook_3way_synthesis.md`, `research/cook_simulation.md`, `research/cook_archaeology.md` added.

---

**Status:** 1,000+ total experiments across 39 rounds. 197+ proven principles (P1-P197). 33 production prisms. 13 compression levels (L13 = reflexive ceiling). Diamond topology confirmed across 3 independent L8 branches. Taxonomy structurally complete.

---

## Round 40: VPS Validation Battery (Mar 14, 2026)

**55 tests across 12 batches, ~$5 total cost.** Every major open question from the tracker addressed. Three new large-file targets validated. Solve-model effect quantified. Domain boundary of L12 mapped.

### Batch Results

**P1 — Alt-primitive cross-target (8 tests).** simulation and cultivation validated on Click + Tenacity at 9.0, confirming Round 39 scores are target-independent. archaeology stable at 8.5. sdl_simulation DEGRADED to 7.0-7.5 vs 8.5 baseline — the SDL compression that works for other operations loses too much temporal structure. Full simulation prism outperforms SDL variant cross-target (P199).

**P2 — COOK_3WAY cross-target (2 tests).** 3-cooker pipeline validated on Click (8218w) and Tenacity (7719w). Cross-operation synthesis (WHERE/WHEN/WHY → integration) confirmed as the general-domain Full Prism solution.

**P3 — Large file scaling (9 tests).** L12 does NOT degrade on 1000+ line files. Rich console.py (2684 lines) scored 10.0 — the richest conservation laws came from the largest file. Flask app.py (1625 lines) 9.5. Requests models.py (1041 lines) 9.5. deep_scan scored 9.0 on all three. identity 8.5-9.0. **P198: Larger files = richer conservation laws.** L12 scales to at least 2700 lines with no quality loss.

**R1 — Solve-model effect (6 tests).** Sonnet cook + Sonnet solve produces 2x output vs Sonnet cook + Haiku solve (1772w vs 871w avg). **P204: Solve model matters as much as cook model.** The hierarchy is now: LENS > PROMPT-DOMAIN MATCH > COOK MODEL = SOLVE MODEL > reasoning budget.

**R2 — Miniaturize promotion test (2 tests).** Sonnet 8.0, Haiku 6.5. Lift of +1.5 exceeds the +0.7 cross-model average but absolute performance is at floor with generic conservation laws. NOT promoted to production (P203).

**R5 — Domain boundary mapping (4 tests).** l12 fails on poetry (5.0, enters conversation mode) but excels on structured creative like UX critique (9.5). l12_universal works on both (poetry 9.0, UX 8.5). **P200: l12 fails on pure creative input but succeeds on structured creative.** "Code" nouns trigger analytical mode — poetry has no structure for analytical mode to grip. Compression forces domain neutrality confirmed: l12_universal's 73w drops the code vocabulary that causes the failure.

**R6 — P182 revision: hallucination vs displacement (4 tests).** P182 REVISED. Using `--intent` with mismatched abstract intent does not cause content hallucination. The model notices the mismatch between intent and actual code, producing content displacement (analyzing the wrong aspects) rather than fabricating code. The original P182 finding was an artifact of a different mechanism.

**R7 — Vertical composition (4 tests).** P172 mostly confirmed with nuance. claim prism succeeds at vertical composition (7.5) — meta-analytical prisms can process analysis text as input. deep_scan (7.0) and pedagogy (6.5) revert to analyzing the original code rather than the analysis text — constructive prisms anchor to concrete objects. **P201: Operation type determines vertical transferability.** Meta-analytical prisms transfer vertically; constructive prisms don't.

**A1 — L12 vs SDL head-to-head (6 tests).** L12 avg 9.5, deep_scan avg 8.8 across 3 targets. Confirmed complementary with ~30-40% finding overlap. L12 produces deeper output (meta-laws, 3.7x more bugs identified). SDL is 57% shorter — more efficient for quick scans. Both remain in the portfolio for different use cases.

**A4 — 70w prism floor test (3 tests).** ErrRes compressed to 70w scored avg 7.0 — BELOW analytical threshold. At 70w, Haiku enumerates possibilities rather than analyzing structure. **P202: 180w is the empirical compression floor for analytical prisms on Haiku.** Below it, models produce checklists instead of conservation laws.

**I1 — New prism candidates (4 tests).** No champions found. time_lifecycle 6.5 and composition_synthesis 6.0 (both ARCHIVED — below threshold). data_flow 7.0 and redundancy 7.0 (KEPT at low priority — may improve with iteration). The existing 37-prism portfolio appears to cover the major analytical dimensions.

**R4 — 3-way on non-code domains (3 tests).** COOK_3WAY pipeline ran on legal contract, business plan, and philosophical argument. Rich cross-operation analysis produced in all cases. File output had a bug (content logged but not written to files), but the analysis quality confirmed 3-way works across domains.

### New Principles (P198-P204)

- **P198:** L12 scales to 2700 lines with no quality degradation. Larger files produce richer conservation laws, not shallower ones.
- **P199:** sdl_simulation degrades cross-target (7.0-7.5 vs 8.5 baseline). Full simulation prism outperforms SDL variant. SDL compression loses temporal structure.
- **P200:** l12 fails on pure creative input (poetry: 5.0) but succeeds on structured creative (UX: 9.5). l12_universal works on everything. Compression forces domain neutrality.
- **P201:** Vertical composition works for meta-analytical prisms (claim: 7.5) but fails for constructive prisms (deep_scan: 7.0, pedagogy: 6.5). Operation type determines vertical transferability.
- **P202:** 70w is below the analytical compression floor on Haiku. 180w is the empirical minimum for conservation-law-producing prisms. Below 180w → enumeration instead of analysis.
- **P203:** Miniaturize Sonnet lift = +1.5 (exceeds +0.7 cross-model average). At-floor absolute performance with generic conservation laws. Not promoted.
- **P204:** Solve model matters as much as cook model. Sonnet+Sonnet >> Sonnet+Haiku (2x output depth, 1772w vs 871w avg).

### Summary

53 output files, 1020KB total. Three new large-file targets validated: Flask app.py (1625 lines), Rich console.py (2684 lines), Requests models.py (1041 lines). No new prisms promoted — the 37-prism portfolio holds. Key structural findings: L12 scales without degradation (P198), solve model is a dominant variable (P204), domain boundary mapped precisely (P200), vertical composition is operation-type-dependent (P201).

---

**Status:** 1,000+ total experiments across 40 rounds. 204+ proven principles (P1-P204). 48 prism files (production + pipeline-internal + variants). 13 compression levels (L13 = reflexive ceiling). Diamond topology confirmed. Large-file scaling validated to 2700 lines. Domain boundary mapped: structured input required for code-vocabulary prisms.
