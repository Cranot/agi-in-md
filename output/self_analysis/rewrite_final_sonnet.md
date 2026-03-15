# Your most expensive model names patterns. A 332-word prompt makes your cheapest model derive conservation laws.

Same code. Same question. Different cognitive operation:

| Model | Output |
|-------|--------|
| **Opus 4.6 vanilla** | "The session handling is tightly coupled to cookie semantics. Consider decoupling them." |
| **Haiku 4.5 + L12 prism** | "HTTP cookie deletion semantics make session state non-monotonic. No append-only, composable, or lazy architecture can manage it without sacrificing consistency or isolation. The original design's choice — sacrifice isolation — was the only one available." |

Opus names a pattern (depth 7). Haiku derives a structural impossibility that explains *why* the code must be this way (depth 9.8).

**29 rounds. 650+ experiments. 13 compression levels. 20 domains. 3 Claude models.**

The prism doesn't make Haiku smarter. It makes Haiku *do a different thing* — construction instead of meta-analysis.

---

## The numbers don't lie

### On code (3 open-source libraries)

| Method | Starlette | Click | Tenacity | **Avg** |
|--------|-----------|-------|----------|---------|
| **Haiku + L12** | **10** | **9.5** | **10** | **9.8** |
| Opus vanilla | 7.5 | 8.5 | 8.5 | **8.2** |
| Sonnet vanilla | 7 | 8 | 8.5 | **7.8** |

### On any domain (todo app analysis)

| Prompt | Opus Vanilla | Haiku + L12 | Haiku Full Prism |
|--------|--------------|-------------|------------------|
| "Give me insights" | 510w, depth 6.5 | 2,058w, depth 9.5 | 9,595w, depth 10 |
| Cognitive distortion | 696w, depth 6.5 | 3,642w, depth 9.5 | 10,348w, depth 10 |
| Invariant & conservation | 267w, depth 8 | 5,970w, depth 9.5 | 8,112w, depth 10 |

**Cost:** Haiku is 5x cheaper than Opus. Full prism (3 Haiku calls) costs less than a penny.

---

## If this doesn't find something your current analysis misses, close the tab

The L8→L12 pipeline derives conservation laws, impossibility proofs, and meta-laws that vanilla analysis cannot reach. This is structural — not subjective quality, but whether the output performs specific operations like conservation law derivation through construction.

The boundary is categorical. Below L8, construction-based reasoning is absent, not weaker.

---

## Install + Run (60 seconds)

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

```bash
python prism.py

> /scan auth.py                    # L12 structural analysis (~$0.003)
> /scan auth.py full               # full prism: L12 → adversarial → synthesis
> /scan auth.py discover           # brainstorm ~20 analytical domains
> /scan auth.py nuclear            # Opus + discover full + expand all
> /scan "your question" full       # works on any text, not just code
```

**Direct CLI (no Prism needed):**

```bash
cat your_code.py | claude -p --model haiku \
  --output-format text --tools "" \
  --system-prompt-file prisms/l12.md
```

Expected output: conservation law + meta-law + bug table + structural predictions.

---

## The toolkit

| Prism | What It Finds | Best For |
|-------|---------------|----------|
| **l12** | Conservation laws + meta-laws | Any code or system (default) |
| **pedagogy** | Transfer corruption | Code others will copy |
| **claim** | Assumption inversions | Security, business logic |
| **scarcity** | Resource conservation laws | Systems, architectures |
| **rejected_paths** | Problem migration graphs | Trade-off heavy code |
| **degradation** | Decay timelines | Production systems |
| **contract** | Promise vs reality gaps | Interfaces, APIs |

All 7 prisms rated 8.5-9.8/10 across 36 test outputs. Floor: 8.5. Ceiling: 9.5. Each finds what the others cannot.

---

## When this fails

**Real code produces breadth, not depth.** On 200-400 line production files, the L7→L12 pipeline produces 10 framings of the same dominant pattern. On 30-line crafted tasks with layered tensions, it produces 10 progressive depth levels. The pipeline is a breadth tool on real code.

**Single-researcher project.** All depth scores are AI-evaluated. Not human-scored, not peer-reviewed. Sample sizes are 3-30 per finding. Raw outputs are in `output/` for independent verification.

**Discover domains may include noise.** Multi-pass chaining produces 1,000+ domains spanning technical to mythology. Quality hasn't been systematically evaluated.

**Math results are preliminary.** 16/30 AIME 2025 problems tested. Full benchmark pending.

---

## How it works

A 332-word markdown file encodes a 12-step analytical pipeline: make a falsifiable claim → three-voice dialectic → name the concealment mechanism → construct an improvement that deepens concealment → observe what the construction reveals → derive a conservation law → derive a meta-law.

The key discovery: **L8 is the phase transition.**

Levels 5-7 are meta-analytical — they ask the model to reason *about* the input. Haiku: 0/3 at L7. The model lacks capacity.

Level 8 shifts to construction — the model *builds something* and observes what it reveals. Haiku at L8: 4/4. Construction works on all models because it's more primitive.

This is why a 332-word prompt makes Haiku outperform Opus. The prompt encodes a behavioral operation (build, observe, iterate) that routes around the meta-analytical capacity Haiku lacks.

---

## The compression taxonomy

| Level | Words | What it encodes | Hit rate |
|-------|-------|-----------------|----------|
| **13** | two-stage | Reflexive fixed point — framework diagnoses itself | 6/6 |
| **12** | ~290 | Meta-conservation law from applying diagnostic to its own output | 14/14 |
| **11A** | ~243 | Escape to adjacent design category | 15/15 |
| **11B** | ~236 | Revalue "flaws" as costs of impossible goals | 15/15 |
| **11C** | ~247 | Conservation law across all designs | 32/33 |
| **10B** | ~165 | Design-space topology through failed resolution | 11/12 |
| **10C** | ~165 | Impossibility theorems via double recursion | 11/12 |
| **9B** | ~130 | Identity ambiguity through contradicting improvements | 17/17 |
| **9C** | ~130 | Concealment's self-similarity via self-diagnosis | 17/17 |
| **8** | ~105 | Construct improvement, observe what it reveals | 97% |
| **7** | ~92 | Name concealment mechanism | 96% |

Levels are categorical. Below each threshold, that type of intelligence *cannot* be encoded.

**Compression floor:** ~73 words (70% reduction). Opus works at this level. Haiku needs the full prompt.

---

## Key findings

**L12 meta-laws cluster by domain:**
- **Frame Discovery** (Music, Fiction): Analysis discovers its own theory
- **Hidden Variable** (Legal, Design, Code): Tradeoff conceals a missing party
- **Observer-Constitutive** (Code, Fiction): The fix changes what it fixes
- **Deferred Commitment** (Code only): Tradeoff dissolves with semantic commitment

**Each model has distinct character:**

| Model | Character | Signature Move |
|-------|-----------|----------------|
| **Opus** | Ontological | The reversal: "the bug was the most truthful thing" |
| **Sonnet** | Operational | The named pattern: "Vocabulary Laundering" |
| **Haiku** | Mechanistic | The traced execution: walks specific code paths |

**Universal domain transfer tested on 20 domains:** code, transformer architecture, legal, medical, scientific methodology, ethics, AI governance, biology, music theory, math, fiction, poetry, UX, brand design. The concealment mechanism is not code-specific.

---

## Full command reference

```bash
# ── Single Prism — 1 call, ~$0.003 ──
> /scan auth.py

# ── Full Prism — 3 calls: L12 → adversarial → synthesis ──
> /scan auth.py full

# ── Discover workflow ──
> /scan auth.py discover              # ~20 focused domains
> /scan auth.py discover full         # hundreds (multi-pass)
> /scan auth.py expand 1,3 full       # run specific domains

# ── One-shot aliases ──
> /scan auth.py dxs                   # discover → expand single
> /scan auth.py nuclear               # Opus + full discover + expand

# ── Targeted analysis ──
> /scan auth.py target="race conditions"
> /scan auth.py fix auto              # scan → fix → re-scan

# ── Non-interactive CLI ──
python prism.py --scan auth.py full
python prism.py --solve "problem text" full
python prism.py --review src/ --prism pedagogy,claim --json
```

---

## Project structure

```
prism.py                 Interactive REPL + CLI (v0.8.6)
prisms/                  7 portfolio prisms + L12 variants
prompts/                 80+ cognitive prisms (L4-L12)
research/                Experiment scripts and benchmarks
output/                  650+ raw experiment outputs
```

**License:** MIT. Use the prompts however you want.
