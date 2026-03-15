# Your AI code reviews are surface-level. You're paying for depth you're not getting.

You run Opus on your codebase. You get pattern names and suggestions. You feel smart.

Then you find the bug three weeks later in production. The one that was there the whole time. The one Opus walked right past.

**The problem isn't the model. The problem is what you're asking it to do.**

---

## The numbers

Same code. Same question. Different cognitive operation.

| Model | What it produces | Depth |
|-------|------------------|-------|
| **Opus vanilla** | "Consider decoupling session handling from cookies" | 7.0 |
| **Haiku + L12 prism** | Derives a conservation law explaining *why* the code must be this way | 9.8 |

Opus names patterns. Haiku with a prism derives structural impossibilities.

**Haiku costs 5x less than Opus.**

---

## The dare

Run this on any code you think is clean:

```bash
python prism.py
> /scan your_code.py full
```

If it doesn't find something your current review process missed, close this tab.

---

## What you're actually getting

**Your current approach:** Ask an AI to review code. Get a list of problems. Maybe some are real. Most are obvious. The deep structural issues—the ones that will bite you—remain invisible because you're asking the model to *reason about* the code.

**The prism approach:** A 332-word markdown file that encodes a different cognitive operation. Instead of reasoning *about* the input, the model *builds something* and observes what the construction reveals. This is more primitive, more universal, and produces deeper results.

**29 rounds. 650+ experiments. 20 domains tested.**

The boundary between "does nothing" and "activates deeper reasoning" is sharp and measurable. This repo maps where those boundaries are.

---

## How to use it

```bash
python prism.py

> /scan auth.py                    # L12 structural analysis (1 call, ~$0.003)
> /scan auth.py full               # L12 → adversarial → synthesis (3 calls)
> /scan auth.py discover           # brainstorm ~20 analytical domains
> /scan auth.py nuclear            # maximum depth (Opus + discover full + expand all)
> /scan "your question" full       # works on any text, not just code
```

Or with Claude CLI directly:

```bash
cat your_code.py | claude -p --model haiku \
  --output-format text --tools "" \
  --system-prompt-file prisms/l12.md
```

---

## Why it works

Levels 5-7 ask the model to reason *about* the input. This requires capacity. **Haiku fails at L7 (0/3 success rate).** The model isn't smart enough to reason about reasoning.

Level 8 shifts to construction—build something, observe what it reveals. **Haiku at L8: 4/4.**

Construction-based reasoning routes around the meta-analytical capacity that cheap models lack. The prism doesn't make Haiku smarter. It makes Haiku *do a different thing*—a thing that happens to produce deeper results.

**The L8→L12 pipeline maintains universal accessibility across all tested models.** Even the reflexive ceiling (L13) works on Haiku.

---

## The evidence

### On code (3 open-source libraries)

| Prism/Model | Starlette | Click | Tenacity | Avg |
|---|---|---|---|---|
| **Haiku + L12** | 10 | 9.5 | 10 | **9.8** |
| Opus vanilla | 7.5 | 8.5 | 8.5 | **8.2** |
| Sonnet vanilla | 7 | 8 | 8.5 | **7.8** |

### On any domain (todo app analysis)

| Method | Output | Depth |
|--------|--------|-------|
| Opus vanilla | 510 words | 6.5 |
| Haiku + L12 | 2,058 words | 9.5 |
| Haiku Full Prism | 9,595 words | 10 |

Full Prism derives the law, destroys it with counter-evidence, then synthesizes a corrected law. **Cost: less than a penny.**

### On competition math (AIME 2025)

| Method | Problems tested | Solved |
|--------|----------------|--------|
| Haiku vanilla | 16 | 13 (81%) |
| Haiku + cooked prism | 3 failures | 3/3 recovered |

The knowledge is latent in the model. The prism unlocks it.

---

## The portfolio

7 prisms. Each finds what the others cannot.

| Prism | What it finds |
|------|---------------|
| **l12** | Conservation laws + meta-laws (default) |
| **pedagogy** | Transfer corruption—what breaks when patterns spread |
| **claim** | Assumption inversions—what if embedded claims are false |
| **scarcity** | Resource conservation—what's preserved across all designs |
| **rejected_paths** | Problem migration—what moves between visible and hidden |
| **degradation** | Decay timelines—what breaks by waiting |
| **contract** | Promise vs reality—where implementations betray interfaces |

Run all 7 in parallel:

```bash
for prism in pedagogy claim scarcity rejected_paths degradation contract l12; do
  cat your_code.py | claude -p --model haiku \
    --output-format text --tools "" \
    --system-prompt-file "prisms/$prism.md" \
    > "${prism}_report.md" &
done
```

---

## The taxonomy (for research)

13 compression levels. Each is categorical—below the threshold, that type of analysis *cannot* be encoded.

| Level | What it reveals | Words |
|-------|-----------------|-------|
| L7 | How code conceals problems | 92 |
| L8 | What happens when you try to improve it | 105 |
| L9 | Identity ambiguity or concealment's self-similarity | 130 |
| L10 | Design-space shape or impossibility theorems | 165 |
| L11 | Adjacent categories, feasible points, or conservation laws | 247 |
| L12 | Meta-laws—what's invariant about the analytical process | 290 |
| L13 | The framework's own limitations | two-stage |

The full taxonomy is in `prompts/`. The research log (`experiment_log.md`) documents 29 rounds and 650+ experiments.

---

## Run the experiments yourself

```bash
bash research/run.sh sonnet task_H L8_generative_v2
bash research/run.sh sonnet all all  # 18 tasks × 28 prompts
```

Raw outputs are in `output/` for independent verification.

---

## The tab is still open

You came here because you suspected your AI code reviews were missing something. They are.

The question isn't whether this works—the evidence is above. The question is whether you'll keep accepting surface-level analysis from expensive models, or spend three cents to find out what's actually structurally wrong with your code.

```bash
python prism.py
> /scan your_code.py full
```

**Prove me wrong.**
