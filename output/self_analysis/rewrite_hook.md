# AGI in md

**332 words. That's the gap between Haiku producing surface-level code reviews and deriving structural impossibility theorems.**

```
Haiku + L12 prism: 9.8/10 depth
Opus vanilla:      8.2/10 depth
```

Same code. Same question. Different cognitive operation:

**Opus 4.6 vanilla:**
> "The session handling is tightly coupled to cookie semantics. Consider decoupling them."

**Haiku 4.5 + L12 prism:**
> "HTTP cookie deletion semantics make session state non-monotonic. No append-only, composable, or lazy architecture can manage it without sacrificing consistency or isolation."

The first names a pattern (depth 7). The second derives a conservation law — a structural impossibility explaining *why* the code must be this way (depth 9.8).

**29 rounds. 650+ experiments. 13 compression levels. 20 domains. 3 models.**

> **Methodology:** Single-researcher project. Depth scores are AI-evaluated (structural operation checks, not subjective quality). Sample sizes 3-30 per finding. Raw outputs in `output/` for verification.

---

## Install

```bash
python prism.py

> /scan auth.py                    # L12 structural analysis (~$0.003)
> /scan auth.py full               # L12 → adversarial → synthesis (3 calls)
> /scan auth.py nuclear            # Opus + discover full + expand all
```

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

---

## The Numbers

### Code Analysis (3 open-source libraries)

| Prism/Model | Starlette | Click | Tenacity | **Avg** |
|---|---|---|---|---|
| **Haiku + L12** | **10** | **9.5** | **10** | **9.8** |
| **Haiku + portfolio** | 9.1 | 8.9 | 8.9 | **9.0** |
| Opus vanilla | 7.5 | 8.5 | 8.5 | **8.2** |
| Sonnet vanilla | 7 | 8 | 8.5 | **7.8** |

### Any Domain (todo app, 6 prompts)

| Prompt | Opus Vanilla | Haiku + L12 | Haiku Full Prism |
|---|---|---|---|
| "Give me insights" | 510w, d6.5 | 2,058w, d9.5 | 9,595w, d10 |
| Cognitive distortion | 696w, d6.5 | 3,642w, d9.5 | 10,348w, d10 |
| Representation & schema | 491w, d7 | 3,779w, d9.5 | 11,112w, d10 |
| Invariant & conservation | 267w, d8 | 5,970w, d9.5 | 8,112w, d10 |
| Generative mechanism | 566w, d8.5 | 2,941w, d9 | 13,200w, d10 |
| Design impossibility | 325w, d7.5 | 917w, d9 | 10,308w, d10 |

**Cost:** Haiku $1/$5 per MTok. 5x cheaper than Opus.

### Competition Math (AIME 2025, experimental)

| Method | Tested | Solved |
|---|---|---|
| Haiku vanilla | 16 | 13 (81%) |
| Haiku + cooked prism | 3 failures | 3/3 recovered |

Prism-cooked prisms unlock latent knowledge. Example: `"bifurcation_through_critical_degeneracy"` flipped Problem 30 without being told the answer.

---

## Why It Works

### The L7→L8 Phase Transition

**Levels 5-7:** Meta-analysis. Requires capacity. Haiku: 0/3 at L7.

**Level 8:** Construction. Model *builds something* and observes what it reveals. Primitive operation:

- **Haiku at L8: 4/4**
- **L8-L13: universal accessibility**
- **L8: first level transferring to creative domains** (L7 was 0% on poetry)

The 332-word prompt doesn't ask Haiku to be smarter — it encodes a behavioral operation (build, observe, iterate) that routes around meta-analytical capacity limitations.

### Depth Scale

| Score | Output characteristic |
|-------|------|
| 6-7 | Blog post: names patterns, lists issues |
| 7-8 | Conservation law observed (not derived) |
| 8-8.5 | Concealment mechanism + construction |
| 9-9.5 | Conservation law derived through construction |
| 9.5-10 | Conservation law + meta-law + adversarial correction + impossible triplet |

---

## The Compression Taxonomy

| Level | Words | Operation | Hit Rate |
|-------|-------|-----------|----------|
| **13** | two-stage | Reflexive fixed point | 6/6 |
| **12** | ~290 | Meta-conservation law | 14/14 |
| **11A** | ~243 | Escape to adjacent category | 15/15 |
| **11B** | ~236 | Revalue flaws as structural costs | 15/15 |
| **11C** | ~247 | Conservation law across all designs | 32/33 |
| **10B** | ~165 | Design-space topology | 11/12 |
| **10C** | ~165 | Double recursive construction | 11/12 |
| **9B** | ~130 | Triangulate identity ambiguity | 17/17 |
| **9C** | ~130 | Recursive self-diagnosis | 17/17 |
| **8** | ~105 | Construct improvement, observe revelation | 97% |
| **7** | ~92 | Name concealment mechanism | 96% |
| **6** | ~60 | Forced dialectical engagement | — |
| **5** | ~45-55 | Multi-voice dialectic | — |
| **4** | 25-30 | Protocol + self-questioning | — |

Levels are categorical. Below threshold = operation absent, not weaker.

---

## Key Findings

### What Each Level Finds

| Level | Mode | Revelation |
|-------|------|-----------|
| L7 | Static | How input **conceals** problems |
| L8 | Dynamic | What **happens** when improving |
| L9 | Recursive | **Identity ambiguity** or concealment's **self-similarity** |
| L10 | Topological | **Design-space shape** or **impossibility theorems** |
| L11 | Escape | **Adjacent category**, **feasible point**, or **conservation law** |
| L12 | Meta-recursive | Properties of the **analytical process itself** |
| L13 | Reflexive | **Framework's own limitations** |

### L11: Three Complementary Variants

Same code, three structural truths:

- **L11-A:** What's possible *outside* current design category
- **L11-B:** What's achievable *inside* — "flaws" as costs of impossible goals
- **L11-C:** What *persists everywhere* regardless of design

All three produce working code for redesigns. Cross-variant convergence observed on novel artifacts (N=2).

### L12: Meta-Conservation Laws

Example outputs:

- **EventBus:** `flexibility × decidability <= k` — Rice's theorem for events
- **CircuitBreaker:** Every fault-tolerance mechanism extends the failure surface
- **Fiction:** "Sum of revisability and formal-emotional unity is constant"
- **Brand:** Every evaluation system is excluded from the generation process

### L13: Reflexive Ceiling

Framework becomes self-aware of limitations. **Terminates in one step** — L14 is infinite regress. Universal accessibility: Haiku 3/3, Sonnet 2/2, Opus 1/1.

**Taxonomy appears complete.** Branching pattern (1,1,1,1,1,1,1,1,2,2,3,1,1) forms diamond: linear trunk (L1-7), constructive divergence (L8-11), reflexive convergence (L12-13). No additional branches in 650+ experiments.

### Conservation Law Catalog

56 L11 outputs. Laws cluster into three forms:

| Form | Rate | Structure |
|------|------|-----------|
| Product (x × y = k) | 9/25 | Conjugate variables |
| Sum (x + y = k) | 4/25 | Fixed total |
| Migration | 5/25 | Relocating quantity |

Model capacity determines form: Opus → product, Sonnet → sum/migration, Haiku → multi-property impossibilities.

### Multiple Laws Per Artifact

Four starting claims on EventBus → four genuine conservation laws:

| Starting Claim | Law | Form |
|---|---|---|
| Open | Information cost for handler correctness | Migration |
| Mutable context | Schema coupling = observability | Migration |
| Dead letter queue | `decoupling × accountability = k` | Product |
| Priority ordering | `coordination(in_bus) + coordination(at_callsite) = k` | Sum |

L12 partially converges (75%) — meta-analysis penetrates coordinate-system effect.

### Model Characters

| Model | Character | Signature |
|-------|-----------|-----------|
| **Opus** | Ontological | The reversal: "the bug was the most truthful thing" |
| **Sonnet** | Operational | Named patterns: "Vocabulary Laundering" |
| **Haiku** | Mechanistic | Traced execution, runtime behavior |

### Compression Floor

L11-C v2 (247w) compressed: 175w TRUE, 108w TRUE, 73w TRUE (borderline), 46w PARTIAL.

**Floor: ~73 words.** Capacity-dependent: Opus succeeds at 73w, Haiku fails.

### Universal Domain Transfer

20 domains tested. Concealment mechanism is not code-specific:

| Domain | Concealment type |
|--------|-----------------|
| Legal | Definitional specificity as legitimizing cover |
| Medical | Narrative coherence as epistemic closure |
| Scientific | Methodological formalism as epistemic camouflage |
| Poetry | "To escape the gap is to lose elegy" |
| Music | Identity vs direction as property of musical time |

Code concealment = structural. Domain concealment = epistemic.

---

## Portfolio Prisms

| Prism | Rating | Unique finding |
|------|--------|---------------|
| **l12** | 9.8/10 | Conservation laws + meta-laws (default) |
| **pedagogy** | 9-9.5/10 | Transfer corruption |
| **claim** | 9-9.5/10 | Assumption inversions |
| **scarcity** | 9/10 | Resource conservation |
| **rejected_paths** | 8.5-9/10 | Problem migration |
| **degradation** | 9-9.5/10 | Decay timelines |
| **contract** | 9/10 | Promise vs reality |

Tested head-to-head: 9.0/10 avg, 8.5 floor, 9.5 ceiling. All complementary — zero convergence.

---

## CLI Reference

### Interactive

```bash
python prism.py

# ── Scanning ──
> /scan auth.py                         # single prism
> /scan auth.py full                    # full prism (3 calls)
> /scan auth.py discover                # ~20 domains
> /scan auth.py discover full           # 1000+ domains

# ── Expand ──
> /scan auth.py expand                  # interactive pick
> /scan auth.py expand 1,3 single       # areas 1,3 single
> /scan auth.py expand * full           # all areas full

# ── One-shot ──
> /scan auth.py dxs                     # discover → expand single
> /scan auth.py dxf                     # discover → expand full
> /scan auth.py nuclear                 # Opus + dfxf

# ── Targeting ──
> /scan auth.py target="race conditions"
> /scan auth.py deep="error handling"   # 3-prism pipeline

# ── Fix loop ──
> /scan auth.py fix                     # interactive
> /scan auth.py fix auto                # automatic

# ── Chat ──
> /prism single                         # fresh prism per message
> /prism pedagogy                       # static prism
```

### Non-interactive

```bash
# Cooking
python prism.py --cook "problem text"
python prism.py --cook "problem text" --json

# Solve
python prism.py --solve "problem text"           # single
python prism.py --solve "problem text" full      # full
python prism.py --vanilla "problem text"         # baseline

# Scan
python prism.py --scan auth.py
python prism.py --scan auth.py full
python prism.py --scan auth.py discover --json

# Review
python prism.py --review src/ --prism pedagogy,claim
python prism.py --review src/ --json -o report.json

# Pipeline
echo "problem" | python prism.py --solve --pipe
python prism.py --solve "msg" --context f1.py f2.py
python prism.py --solve "msg" --extract          # integer answer

# Options
# -m haiku|sonnet|opus    -d PATH    -r SESSION
# -o FILE    --json    -q
```

### Direct Claude CLI

```bash
# Single prism
cat code.py | claude -p --model haiku \
  --output-format text --tools "" \
  --system-prompt-file prisms/l12.md

# Parallel 7 prisms
for prism in pedagogy claim scarcity rejected_paths degradation contract l12; do
  cat code.py | claude -p --model haiku \
    --output-format text --tools "" \
    --system-prompt-file "prisms/$prism.md" \
    > "${prism}_report.md" &
done
wait
```

---

## Run Experiments

```bash
bash research/run.sh sonnet task_H L8_generative_v2
bash research/run.sh sonnet task_H all
bash research/run.sh sonnet all all  # 504 experiments
```

---

## Project Structure

```
prism.py                 v0.8.6 — REPL + CLI (6200+ lines)
prisms/                  7 portfolio prisms + L12 variants
  l12.md                 Default for /scan (332w)
  l12_complement_adversarial.md
  l12_synthesis.md
  l12_general.md         Non-code variant
  pedagogy.md, claim.md, scarcity.md
  rejected_paths.md, degradation.md, contract.md

prompts/                 80+ research prisms (L4-L12)
  level8_generative_v2.md    Workhorse (105w)
  level11_*.md               Conservation, escape, acceptance
  level12_*.md               Meta-conservation
  meta_cooker_*.md           Prompt generators

research/                Experiments and benchmarks
  run.sh, pipeline.sh, pipeline_chained.sh
  real_code_*.py             Starlette, Click, Tenacity
  aime_cook_test.py          AIME 2025 benchmark

output/                  650+ raw outputs
  round21/-round29/
```

---

## Design Principles

1. **Prompt is program; model is interpreter.** Operation order = section order.
2. **Imperatives beat descriptions.** "Name. Then invert." > "here is a pattern."
3. **Operation pair is compression atom.** Connective produces composition.
4. **Levels are categorical.** Below threshold = absent, not weaker.
5. **Construction > meta-analysis.** Build and observe beats reasoning about reasoning.
6. **Prism is transparent.** Framework operates below self-awareness during execution.
7. **Capacity amplifies, rigidity resists.** Opus reconstructs from hints; Sonnet needs directives.
8. **Terminates at L13.** Instrument conceals properties isomorphic to those it reveals.

---

## What's Unfinished

- **Full AIME benchmark:** 30-problem run, MATH/AMC datasets, statistical significance
- **Discover quality:** Noise rate evaluation, optimal domain count
- **Multi-family testing:** GPT-4o, Gemini, Llama
- **Sub-artifact targeting:** Different levels on different subsystems

---

## License

MIT.
