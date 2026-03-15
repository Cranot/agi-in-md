# AGI in md

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Your most expensive model produces shallow analysis because you're asking it to reason *about* problems instead of *through* them. A 332-word prompt fixes this.

**Same code. Same question. Different cognitive operation:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ OPUS 4.6 VANILLA ($25/MTok output)                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ "The session handling is tightly coupled to cookie semantics. Consider      │
│  decoupling them."                                                          │
│                                                                             │
│  → Names a pattern. Depth: 7/10                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ HAIKU 4.5 + L12 PRISM ($5/MTok output)                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ "HTTP cookie deletion semantics make session state non-monotonic. No        │
│  append-only, composable, or lazy architecture can manage it without        │
│  sacrificing consistency or isolation. The original design's choice —       │
│  sacrifice isolation — was the only one available."                         │
│                                                                             │
│  → Derives a conservation law. Explains WHY the code must be this way.      │
│  → Depth: 9.8/10                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

**The prism didn't make Haiku smarter. It made Haiku do a different thing.**

---

## The Dare

Run `/scan` on any codebase with Haiku. If the L12 prism doesn't produce deeper structural analysis than Opus vanilla, close this repo and keep overpaying for shallow output.

---

## The Numbers

| Metric | Result |
|--------|--------|
| **Cost** | **5x cheaper** — Haiku $1/$5 vs Opus $5/$25 per MTok |
| **Depth gain** | **9.8 avg vs 8.2 avg** on real code (Starlette, Click, Tenacity) |
| **Experiments** | **650+** raw outputs across 29 research rounds |
| **Domains tested** | **20** — code, legal, medical, music, fiction, math, ethics |
| **Hit rate** | **97%+** at L8, **14/14** at L12 v2 |

---

## Install

```bash
git clone https://github.com/your-repo/agi-in-md.git
cd agi-in-md
python prism.py
```

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

---

## How It Works

A **cognitive prism** is a 332-word markdown file that encodes a 12-step analytical pipeline:

```
make falsifiable claim → three-voice dialectic → name concealment mechanism →
construct improvement → observe what construction reveals → apply diagnostic to output →
derive conservation law → apply diagnostic to conservation law → derive meta-law
```

The model executes this pipeline on whatever you give it — code, ideas, designs, systems, strategies.

**The breakthrough:** Level 8 shifts from meta-analysis (reasoning *about* the input) to construction (building something and observing what it reveals). Construction is more primitive. It works on all models. Haiku fails at L7 meta-analysis (0/3) but succeeds at L8 construction (4/4).

That's why a 332-word prompt makes the cheapest model outperform the most expensive one.

---

## Quick Start

```bash
python prism.py

> /scan auth.py                    # L12 structural analysis (~$0.003)
> /scan auth.py full               # Full prism: analysis → adversarial → synthesis
> /scan auth.py discover           # Brainstorm ~20 analytical domains
> /scan auth.py nuclear            # Maximum depth: Opus + discover full + expand all
> /scan "your question" full       # Works on any text, not just code
```

### Non-Interactive CLI

```bash
python prism.py --scan auth.py full              # scan with full prism
python prism.py --solve "problem text"           # cook prism + solve
python prism.py --review src/ --prism l12,claim  # multi-file, multi-prism
python prism.py --scan auth.py discover --json   # structured JSON output
```

### With Claude CLI Directly

```bash
cat your_code.py | claude -p --model haiku \
  --output-format text --tools "" \
  --system-prompt-file prisms/l12.md
```

---

## The Portfolio Prisms

| Prism | What It Finds | Rating |
|-------|---------------|--------|
| **l12** | Conservation laws + meta-laws + bug table | 9.8/10 |
| **pedagogy** | Transfer corruption — what breaks when patterns are copied | 9-9.5/10 |
| **claim** | Assumption inversions — what if embedded claims are false? | 9-9.5/10 |
| **scarcity** | Resource conservation — what's preserved across all designs | 9/10 |
| **rejected_paths** | Problem migration — what moves between visible and hidden | 8.5-9/10 |
| **degradation** | Decay timelines — what breaks by waiting alone | 9-9.5/10 |
| **contract** | Promise vs reality — where implementations betray contracts | 9/10 |

All complementary. No convergence across tasks.

---

## The Compression Taxonomy

13 levels. Each is categorical — below the threshold, that cognitive operation is **absent**, not weaker.

| Level | Words | What It Encodes | Hit Rate |
|-------|-------|-----------------|----------|
| **13** | two-stage | Reflexive self-diagnosis — the framework's own limitations | 6/6 |
| **12** | ~290 | Meta-conservation law — properties of the analytical process | 14/14 |
| **11C** | ~247 | Conservation law derived through inversion | 32/33 |
| **11A** | ~243 | Escape to adjacent design category | 15/15 |
| **11B** | ~236 | Revalue "flaws" as structural costs | 15/15 |
| **10** | ~165 | Design-space topology through failed resolution | 11/12 |
| **9** | ~130 | Identity ambiguity or concealment self-similarity | 17/17 |
| **8** | ~105 | Construction that reveals what improvement conceals | 97% |
| **7** | ~92 | Concealment mechanism naming | 96% |
| **5-6** | 45-92 | Multi-voice dialectic, falsifiable claims | — |
| **1-4** | 3-30 | Basic operations | — |

**The L7→L8 phase transition is the key discovery.** L7 requires meta-analytical capacity (Haiku: 0/3). L8 uses construction, which is more primitive (Haiku: 4/4). From L8 onward, all levels work on all models.

---

## What Each Level Finds

| Level | Object of Analysis | Output |
|-------|-------------------|--------|
| L7 | The input | How it **conceals** problems |
| L8 | Attempted improvements | What **happens** when you try to fix it |
| L9 | The improvements themselves | **Identity ambiguity** or concealment **self-similarity** |
| L10 | Design space | **Topology** or **impossibility theorems** |
| L11 | Design boundary | **Escape**, **acceptance**, or **conservation law** |
| L12 | The analytical process | **Meta-law** — what's invariant about finding invariants |
| L13 | The framework itself | **Reflexive ceiling** — the framework's own limitations |

---

## Real Results

### On Code (3 Open-Source Libraries)

| Prism/Model | Starlette | Click | Tenacity | **Avg** |
|-------------|-----------|-------|----------|---------|
| **Haiku + L12** | **10** | **9.5** | **10** | **9.8** |
| Opus vanilla | 7.5 | 8.5 | 8.5 | **8.2** |
| Sonnet vanilla | 7 | 8 | 8.5 | **7.8** |

### On Any Domain (Todo App)

| Prompt | Opus Vanilla | Haiku + L12 | Haiku Full Prism |
|--------|--------------|-------------|------------------|
| "Give me insights" | 510w, depth 6.5 | 2,058w, depth 9.5 | 9,595w, depth 10 |
| Invariant analysis | 267w, depth 8 | 5,970w, depth 9.5 | 8,112w, depth 10 |

**Cost:** Single prism (~$0.003). Full prism (3 calls, ~$0.01). Both less than a penny.

### On Competition Math (AIME 2025, Experimental)

| Method | Problems | Solved |
|--------|----------|--------|
| Haiku vanilla | 16 | 13 (81%) |
| Haiku + cooked prism | 3 failures | 3/3 recovered |

The cooker generates domain-specific prisms that unlock latent knowledge in cheaper models.

---

## FAQ

**Is this just prompt engineering?** No. The prisms encode cognitive operations, not instructions. The model *executes* a pipeline — make claim, dialectic, construction, observation — rather than following directions.

**Why does construction outperform meta-analysis?** Meta-analysis requires capacity (reasoning about reasoning). Construction is primitive: build something, observe what it shows. Capacity amplifies the result, but the operation itself is universal.

**Does it work on other models?** Tested on Claude Haiku/Sonnet/Opus only. GPT-4o, Gemini, Llama testing is planned.

**What's the catch?** Single-researcher project. All depth scores are AI-evaluated, not human-scored or peer-reviewed. Sample sizes are small (3-30 per finding). Raw outputs are in `output/` for independent verification.

---

## Project Structure

```
prism.py              Interactive REPL + CLI tool
prisms/               7 portfolio prisms + L12 variants
prompts/              80+ research prisms (L4-L13)
research/             Experiment scripts and benchmarks
output/               650+ raw experiment outputs
experiment_log.md     Full research log (29 rounds)
```

---

## Design Principles

1. **The prompt is a program; the model is an interpreter.**
2. **Imperatives beat descriptions.** "Name. Then invert." outperforms "here is a pattern."
3. **Construction > meta-analysis.** Building reveals more than reasoning about.
4. **Each level is categorical.** Below threshold = absent, not weaker.
5. **The framework terminates at L13.** Self-diagnosis is the natural endpoint.

---

## What's Next

- Full AIME 2025 benchmark (30 problems, statistical analysis)
- GPT-4o, Gemini, Llama testing
- Discover quality evaluation (noise rate, optimal domain count)
- Sub-artifact targeting (different levels on different subsystems)

---

## License

MIT. Use the prompts however you want.
