# AGI in md

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Your most expensive model produces shallow analysis because you're asking it to reason *about* problems instead of *through* them. A 332-word prompt fixes this.

A **cognitive prism** is a markdown file used as a system prompt. It routes models through a 12-step analytical pipeline — make claim, dialectic, construction, observation, derive law — rather than asking them to "analyze deeply." This repo contains 21 production prisms + the tooling to use them.

**Same code. Same question. Different cognitive operation:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ OPUS 4.6 VANILLA ($25 per million output tokens)                             │
│ Analyzing Python requests library Session module                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ "The session handling is tightly coupled to cookie semantics. Consider      │
│  decoupling them."                                                          │
│                                                                             │
│  → Names a pattern. Depth: 7/10                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ HAIKU 4.5 + L12 PRISM ($5 per million output tokens)                         │
│ Analyzing Python requests library Session module                            │
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

**The prism didn't make Haiku smarter. It made Haiku do a different thing.** Vanilla produces code reviews — lists patterns, rates severity. Prisms produce structural analysis — derives impossibilities, traces decay, predicts failures.

---

## The Dare

Run `/scan` on any file over 100 lines. If the L12 prism doesn't teach you something new about your own code, close this repo and keep overpaying for shallow output.

---

## The Numbers

Depth scored by checking which structural operations the output performs: naming patterns (6-7), observing conservation laws (7-8), deriving them through construction (9-9.5), or deriving meta-laws with adversarial correction (9.5-10). AI-evaluated by Claude, not human-scored. Raw outputs in `output/` for verification.

| Metric | Result |
|--------|--------|
| **Cost** | **5x cheaper** — Haiku $1/$5 vs Opus $5/$25 per million tokens |
| **Depth gain** | **9.8 avg vs 8.2 avg** on real code (Starlette, Click, Tenacity) |
| **Experiments** | **1,000+** raw outputs across 37 research rounds |
| **Domains tested** | **20+** — code, math, philosophy, legal, medical, music, fiction, business, more |
| **Hit rate** | **97%+** at Level 8 (construction), **14/14** at Level 12 (meta-law) |

---

## Install

**Requirements:**
- Python 3.9+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — `npm install -g @anthropic-ai/claude-code`, then run `claude` to authenticate

```bash
git clone https://github.com/Cranot/agi-in-md.git
cd agi-in-md
python prism.py        # Starts interactive REPL
```

No API key needed — `prism.py` wraps the Claude Code CLI, which uses your Claude subscription.

---

## How It Works

The default prism ([`prisms/l12.md`](prisms/l12.md)) is a 332-word markdown file that encodes a 12-step analytical pipeline:

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

# ── Single Prism — 1 call, ~$0.003 ──
> /scan auth.py                             # L12 structural analysis

# ── Full Prism — 9 calls: 7 structural + adversarial + synthesis ──
> /scan auth.py full                        # deeper, multi-pass

# ── Scan + Fix — find issues, then auto-apply fixes ──
> /scan auth.py fix auto                    # scan → extract → fix → re-scan

# ── Discover → Expand — explore, then go deep ──
> /scan auth.py discover                    # brainstorm ~20 analytical domains
> /expand 1,3 full                          # expand specific areas as full prism

# ── One-shot aliases ──
> /scan auth.py dxs                         # discover → expand all as single
> /scan auth.py nuclear                     # Opus + discover full + expand all

# ── Target specific concerns ──
> /scan auth.py target="race conditions"    # cook goal-specific prism + run

# ── Chat with dynamic prisms ──
> /prism single                             # fresh prism per message
> /prism pedagogy                           # static prism for all messages

# ── Works on any input ──
> /scan "your question" full                # text, not just code
> /scan src/                                # entire directory
```

### Non-Interactive CLI

```bash
python prism.py --scan auth.py full              # full prism scan
python prism.py --solve "problem text"           # cook prism + solve
python prism.py --solve "problem text" full      # cook pipeline + chain
python prism.py --vanilla "problem text"         # baseline (no prism)
python prism.py --review src/ --prism l12,claim  # multi-file, multi-prism
python prism.py --scan auth.py discover --json   # structured JSON output
echo "problem" | python prism.py --solve --pipe  # read from stdin

# Options: -m haiku|sonnet|opus  -o FILE  --json  -q (quiet)
```

### With Claude CLI Directly

```bash
# Single prism
cat your_code.py | claude -p --model haiku \
  --output-format text --tools "" \
  --system-prompt-file prisms/l12.md

# All 7 prisms in parallel
for prism in pedagogy claim scarcity rejected_paths degradation contract l12; do
  cat your_code.py | claude -p --model haiku \
    --output-format text --tools "" \
    --system-prompt-file "prisms/$prism.md" \
    > "${prism}_report.md" &
done
wait
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

All complementary. No convergence across tasks. Tested head-to-head: avg 9.0/10 across 36 outputs (3 crafted tasks + 3 open-source codebases). Floor 8.5, ceiling 9.5.

### What L12 actually produces

Real meta-laws from L12 outputs — these are what the prism derives, not what you tell it to find:

- **EventBus** (Opus): `flexibility of coordination × decidability of behavior ≤ k` — Rice's theorem applied to event architectures. Predicts: successful retries reset failure counters, the circuit breaker becomes a load amplifier.
- **CircuitBreaker** (Opus): Every fault-tolerance mechanism extends the failure surface it was designed to reduce.
- **Fiction** (Opus): "The sum of revisability and formal-emotional unity is constant." The revision process is structurally isomorphic to the character's pathology.
- **Brand design** (Sonnet): "Every system of evaluation capable of falsifying a solution is structurally excluded from the process that generates the solution."

### Works on any domain

The concealment mechanism is not code-specific. L12 tested on 20+ domains:

**Code & Engineering:** Python web frameworks (Starlette), CLI libraries (Click), retry logic (Tenacity), transformer architecture ("Attention Is All You Need")

**Reasoning & Strategy:** AI scaling hypothesis (44 experiments, 20 unique conservation laws from one seed), business strategy, audience analysis, todo app architecture

**Academic & Professional:** Mathematics (FLP impossibility theorem, AIME 2025), philosophy (Chinese Room — 37KB published-paper-quality output), news/journalism, legal analysis, medical reasoning, scientific methodology

**Creative & Humanistic:** Fiction, poetry, music theory, music composition, brand/UX design, ethical reasoning, AI governance

Real findings from non-code domains:

- **Legal**: Definitional specificity as legitimizing cover
- **Medical**: Narrative coherence as epistemic closure
- **Philosophy**: Observer-dependency analysis — isomorphism between the model and the framework
- **Poetry**: "To escape the gap is to lose elegy. To keep elegy is to keep the gap."
- **Music**: Identity vs direction as a property of *musical time itself*
- **Brand design**: "Every system of evaluation capable of falsifying a solution is structurally excluded from the process that generates the solution."

Both Sonnet and Opus independently converge on the same structural pattern per domain — consistent with mechanisms being properties of domains, not model confabulations.

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
| **Haiku + portfolio avg** | 9.1 | 8.9 | 8.9 | **9.0** |
| Opus vanilla | 7.5 | 8.5 | 8.5 | **8.2** |
| Sonnet vanilla | 7 | 8 | 8.5 | **7.8** |

### On Any Domain (Todo App)

| Prompt | Opus Vanilla | Haiku + L12 | Haiku Full Prism |
|--------|--------------|-------------|------------------|
| "Give me insights" | 510w, depth 6.5 | 2,058w, depth 9.5 | 9,595w, depth 10 |
| Invariant analysis | 267w, depth 8 | 5,970w, depth 9.5 | 8,112w, depth 10 |

**Cost:** Single prism (~$0.003). Full prism (9 calls, ~$0.03). Both under a nickel.

### On Competition Math (AIME 2025, Experimental)

| Method | Problems | Solved |
|--------|----------|--------|
| Haiku vanilla | 16 | 13 (81%) |
| Haiku + cooked prism | 3 failures | 3/3 recovered |

*"Cooked" = auto-generated for the specific domain. The cooker analyzes the problem type and generates a prism tailored to it.*

The cooker generates domain-specific prisms that unlock latent knowledge in cheaper models.

### Model Characters

Each model produces categorically different analysis with the same prism:

| Model | Character | Signature move |
|-------|-----------|----------------|
| **Opus** | Ontological depth | The reversal: "the bug was the most truthful thing about the code" |
| **Sonnet** | Operational precision | Named patterns: "Vocabulary Laundering," "Command-Query Conflation" |
| **Haiku** | Mechanistic coverage | Traced execution: walks specific code paths and runtime behavior |

Without a prism, Opus ≈ Sonnet (+0.4 avg). The prism is the multiplier; the model is the base.

---

## When This Fails

**Code generation:** Prisms are analytical, not generative. They find hidden structure in existing code — they don't help write new code. A separate codegen prism exists (`prisms/codegen.md`, 130 words, 3 steps: decompose → design API → predict bugs → implement), but it's a different cognitive operation entirely. Don't expect `/scan` to make your model write better functions.

**Large real-world codebases:** The multi-level pipeline produces breadth (10 framings of the same dominant pattern), not depth. Real 200-400 line production code has one dominant pattern that saturates all levels. For real code, use single prism mode — it's more focused.

**Math problems:** Full prism (multi-step pipeline) did NOT help on AIME — single prism worked better. Too many pipeline steps dilute focus on competition problems.

**Other models:** Gemini 2.5 Flash produces conservation laws from the same L12 prism — the construction operation transfers across model families. GPT/Llama untested. Prism wording was tuned on Claude; if you test elsewhere, open an issue with results.

---

## FAQ

**Is this just prompt engineering?** No. The prisms encode cognitive operations, not instructions. The model *executes* a pipeline — make claim, dialectic, construction, observation — rather than following directions.

**Why does construction outperform meta-analysis?** Meta-analysis requires capacity (reasoning about reasoning). Construction is primitive: build something, observe what it shows. Capacity amplifies the result, but the operation itself is universal.

**Does it work on other models?** Gemini 2.5 Flash produces conservation laws from the same L12 prism — confirmed cross-family. GPT and Llama untested. The construction operation is model-agnostic in theory; the specific wording was optimized on Claude. If you test elsewhere, share results.

**What's the catch?** Single-researcher project. All depth scores are AI-evaluated, not human-scored or peer-reviewed. Sample sizes are small (3-30 per finding). Raw outputs are in `output/` for independent verification.

---

## Project Structure

```
prism.py              Interactive REPL + CLI tool (~9,800 lines)
prisms/               21 production prisms (9-step pipeline + 6 portfolio + SDL + tools)
prompts/              80+ research prisms (L4-L13)
research/             Experiment scripts and benchmarks
output/               992+ raw experiment outputs
experiment_log.md     Full research log (35 rounds)
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

Want to help? Test on other models, run benchmarks, open PRs with results.

---

## License

MIT. Use the prompts however you want.

---

**Stop paying for depth. Start prompting for it.**

Clone the repo. Run `/scan` on your hardest code. If L12 doesn't surprise you, delete it and keep your workflow. But if it does — the prisms are MIT licensed. Use them anywhere.
