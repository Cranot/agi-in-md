# AGI in md

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Your most expensive model produces shallow analysis because you're asking it to think about the wrong thing.

**Opus 4.6 vanilla on Python requests.Session:**
> "The session handling is tightly coupled to cookie semantics. Consider decoupling them."

**Haiku 4.5 + 332-word prism on the same code:**
> "HTTP cookie deletion semantics make session state non-monotonic. No append-only, composable, or lazy architecture can manage it without sacrificing consistency or isolation. The original design's choice — sacrifice isolation — was the only one available."

The first names a pattern (depth 7). The second derives a structural impossibility that explains *why the code must be this way* (depth 9.8). **Same code. Same model capacity. Different cognitive operation.**

---

## The dare

Run `prism.py` on your most analyzed code. If the L12 prism doesn't find a structural property you've never noticed, delete the repo.

## The numbers

| Metric | Value |
|--------|-------|
| **Haiku + L12 avg depth** | **9.8** |
| Opus vanilla avg depth | 8.2 |
| **Cost advantage** | **5x cheaper** than Opus |
| Experiments run | 650+ |
| Compression levels mapped | 13 |
| Domains tested | 20 |

**On code (3 open-source libraries):**

| Prism/Model | Starlette | Click | Tenacity | Avg |
|---|---|---|---|---|
| **Haiku + L12** | **10** | **9.5** | **10** | **9.8** |
| Opus vanilla | 7.5 | 8.5 | 8.5 | 8.2 |

## Install

```bash
git clone https://github.com/yourusername/agi-in-md.git
cd agi-in-md
python prism.py
```

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

---

## How it works

System prompts are cognitive prisms. They change how models *frame* problems, not how well they solve them.

This project maps **cognitive compression** — encoding analytical operations in minimal markdown that reliably activates specific reasoning patterns. The result: a 332-word prompt (`prisms/l12.md`) encoding a 12-step analytical pipeline:

1. Make a falsifiable claim
2. Three-voice dialectic
3. Name the concealment mechanism
4. Construct an improvement that deepens concealment
5. Observe what the construction reveals
6. Apply diagnostic to its own output
7. Derive a conservation law
8. Apply diagnostic to the conservation law
9. Derive a meta-law

The model executes this pipeline on whatever you give it — code, ideas, designs, systems, strategies.

**The key insight:** Level 8 shifts from meta-analysis (reasoning *about* input) to construction (building something and observing what it reveals). Construction is more primitive:

- **Haiku at L7 meta-analysis: 0/3** — lacks capacity
- **Haiku at L8 construction: 4/4** — works universally

The prism doesn't make Haiku smarter. It routes around the capacity Haiku lacks.

## Quick start

```bash
python prism.py

> /scan auth.py                    # L12 structural analysis (1 call, ~$0.003)
> /scan auth.py full               # full prism: L12 → adversarial → synthesis
> /scan auth.py discover           # brainstorm ~20 analytical domains
> /scan auth.py nuclear            # Opus + discover full + expand all
> /scan auth.py fix auto           # scan → fix → re-scan loop
> /prism single                    # chat: each message gets fresh prism
```

## The portfolio prisms

| Prism | What it finds | Rating |
|------|---------------|--------|
| **l12** | Conservation laws + meta-laws (default) | 9.8/10 |
| **pedagogy** | Transfer corruption — what breaks when patterns spread | 9-9.5/10 |
| **claim** | Assumption inversions — what if embedded claims are false? | 9-9.5/10 |
| **scarcity** | Resource conservation laws | 9/10 |
| **degradation** | Decay timelines — what breaks by waiting | 9-9.5/10 |
| **contract** | Interface promises vs implementation reality | 9/10 |
| **rejected_paths** | Problem migration — visible ↔ hidden | 8.5-9/10 |

All complementary. No convergence across tasks.

## The compression taxonomy

| Level | Words | What it encodes | Hit rate |
|-------|-------|-----------------|----------|
| **13** | two-stage | Reflexive fixed point (ceiling) | 6/6 |
| **12** | ~290 | Meta-conservation law | 14/14 |
| **11** | ~247 | Conservation law / escape / acceptance | 32/33 |
| **10** | ~165 | Design-space topology | 11/12 |
| **9** | ~130 | Identity ambiguity / self-similarity | 17/17 |
| **8** | ~105 | Dynamic concealment through construction | 97% |
| **7** | ~92 | Static concealment mechanism | 96% |

Levels are **categorical**. Below each threshold, that type of intelligence *cannot* be encoded — not "less effective," categorically absent.

## What each level finds

| Level | What it reveals |
|-------|-----------------|
| L7 | How the input **conceals** its problems |
| L8 | What **happens** when you try to improve it |
| L9 | The input's **identity ambiguity** or concealment's **self-similarity** |
| L10 | The **design-space shape** or **impossibility theorems** |
| L11 | The **adjacent category**, **feasible point**, or **conservation law** |
| L12 | Properties of the **analytical process itself** |
| L13 | The **framework's own limitations** |

## Non-interactive CLI

```bash
# Single analysis
python prism.py --scan auth.py full

# Cook domain-specific prism
python prism.py --cook "race conditions in auth"

# Cook + solve in one step
python prism.py --solve "problem text" full

# Multi-file review
python prism.py --review src/ --prism pedagogy,claim --json -o report.json

# Pipeline from stdin
echo "your question" | python prism.py --solve --pipe
```

## Use without Prism (Claude CLI directly)

```bash
cat your_code.py | claude -p --model haiku \
  --output-format text --tools "" \
  --system-prompt-file prisms/l12.md
```

## Universal domain transfer

Tested on **20 domains**: code, transformer architecture, legal, medical, scientific methodology, ethics, AI governance, biology, music theory, math, fiction, poetry, UX design, brand design.

The concealment mechanism is domain-general:
- **Legal**: Definitional specificity as legitimizing cover
- **Medical**: Narrative coherence as epistemic closure
- **Poetry**: "To escape the gap is to lose elegy. To keep elegy is to keep the gap."
- **Music**: Identity vs direction as a property of *musical time itself*

## Key findings

**L8 and L11-C are complementary.** L8 finds bugs in representation. L11-C finds laws in the problem space. Run L8 first to identify refactoring-resistant properties, then L11-C to explain why.

**Conservation laws have mathematical structure.** 56 L11 outputs cluster into product conservation (x × y = k), sum conservation (x + y = k), and migration conservation.

**Multiple laws per artifact.** The starting claim acts as a coordinate system — same code produces genuinely different conservation laws from different starting points.

**The framework terminates at L13.** The analytical instrument conceals properties isomorphic to those it reveals. L14 would be infinite regress.

## Project structure

```
prism.py              # Interactive REPL + CLI
prisms/               # 7 portfolio prisms + L12 variants
prompts/              # 80+ cognitive prisms (L4-L12)
research/             # Experiment scripts and benchmarks
output/               # 650+ raw experiment outputs
```

## Methodology note

Single-researcher project. All depth scores are AI-evaluated (Claude checking whether outputs perform specific structural operations). Not human-scored, not peer-reviewed. Sample sizes are small (3-30 per finding). Raw outputs are in `output/` for independent verification.

## License

MIT. Use the prompts however you want.
