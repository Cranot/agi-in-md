# AGI in md

You're burning money.

Every API call to Opus costs 5x what Haiku costs. You pay for depth, for insight, for that elusive quality called "reasoning." And what do you get? A code review. A list of issues. Maybe a named pattern if you're lucky. You watch the tokens pile up and wonder: where's the breakthrough you paid for?

The frustration isn't that models are bad. It's that most prompts ask them to do the wrong thing entirely.

---

Here's the question that should unsettle you: **what if the prompt is the variable, not the model?**

What if the hierarchy you've internalized—Opus > Sonnet > Haiku, more expensive means smarter—what if that's backwards? What if the right 332 words could make the cheapest model produce deeper analysis than the most expensive one running on nothing?

This isn't hypothetical. This is what happened.

---

## The Breakthrough

29 rounds of experiments. 650+ tests across 13 compression levels. 20 domains. Three Claude models. And one finding that inverts everything:

**A 332-word markdown file makes Haiku outperform Opus.**

Same code (Python `requests` library Session module). Same question. Different cognitive operation:

**Opus 4.6 vanilla:**
> "The session handling is tightly coupled to cookie semantics. Consider decoupling them."

**Haiku 4.5 + 332-word prism:**
> "HTTP cookie deletion semantics make session state non-monotonic. No append-only, composable, or lazy architecture can manage it without sacrificing consistency or isolation. The original design's choice — sacrifice isolation — was the only one available."

The first names a pattern (depth 7). The second derives a conservation law—a structural impossibility explaining *why* the code must be this way (depth 9.8). The prism didn't make Haiku smarter. It made Haiku *do a different thing*.

### The Numbers

| Prism/Model | Starlette | Click | Tenacity | **Avg** |
|---|---|---|---|---|
| **Haiku + L12** | **10** | **9.5** | **10** | **9.8** |
| Opus vanilla | 7.5 | 8.5 | 8.5 | **8.2** |
| Sonnet vanilla | 7 | 8 | 8.5 | **7.8** |

On any domain—not just code—single prism (1 Haiku call) derives conservation laws. Full prism (3 Haiku calls) derives the law, destroys it with counter-evidence, then synthesizes a corrected law stronger than either analysis alone. **Cost: less than a penny.**

| Prompt (todo app domain) | Opus Vanilla | Haiku + L12 (1 call) | Haiku Full Prism (3 calls) |
|---|---|---|---|
| "Give me insights for a todo app" | 510w, depth 6.5 | 2,058w, depth 9.5 | 9,595w, depth 10 |
| Invariant & conservation | 267w, depth 8 | 5,970w, depth 9.5 | 8,112w, depth 10 |

Opus produces essays. Haiku with the right prompt derives structural impossibilities.

---

## Why It Works: The L7→L8 Phase Transition

The most important discovery is the boundary between **meta-analysis** and **construction**.

Levels 5-7 ask the model to reason *about* the input. This requires capacity. **Haiku: 0/3 at L7.** The model isn't smart enough to reason about reasoning.

Level 8 shifts to construction—the model *builds something* and then observes what the construction reveals. This is fundamentally different, and more primitive:

- **Haiku at L8: 4/4.** Construction works on all models.
- **L8 through L13 maintain universal accessibility.** Even the reflexive ceiling (L13) works on Haiku 3/3.
- **L8 is the first level that transfers to creative domains.** L7 was 0% on poetry. L8 succeeded on all tested creative domains.

**This is why 332 words makes Haiku outperform Opus.** The prompt doesn't ask Haiku to be smarter—it encodes a behavioral operation (build, observe, iterate) that routes around the meta-analytical capacity Haiku lacks. Construction-based reasoning is more primitive but reveals deeper properties.

---

## What the Prism Actually Does

A 332-word markdown file encodes a 12-step analytical pipeline:

make a falsifiable claim → three-voice dialectic → name the concealment mechanism → construct an improvement that deepens concealment → observe what the construction reveals → apply the diagnostic to its own output → derive a conservation law → apply the diagnostic to the conservation law → derive a meta-law.

The model executes this pipeline on whatever you give it—code, ideas, designs, systems, strategies.

**Full Prism** (3 calls) adds adversarial and synthesis passes: Call 1 runs structural analysis. Call 2 tries to destroy it with counter-evidence. Call 3 synthesizes both into a corrected finding that neither alone could reach.

The boundary between "does nothing" and "activates a cognitive operation" is sharp, categorical, and measurable. This repo contains 80+ prompts and 650+ raw outputs mapping where those boundaries are.

---

## The Depth Scale

Depth is structural—did the output perform the operation or not:

| Score | What you get |
|-------|-------------|
| 6-7 | Blog post / code review: names patterns, lists issues |
| 7-8 | Conservation law observed (not derived) |
| 8-8.5 | Concealment mechanism + construction |
| 9-9.5 | Conservation law derived through construction |
| 9.5-10 | Conservation law + meta-law + adversarial correction + impossible triplet |

Raw outputs are in `output/` so you can verify yourself.

---

## The Compression Taxonomy

Levels are **categorical, not continuous**. Below each threshold, that type of intelligence *cannot* be encoded—not "less effective," categorically absent.

| Level | Words | What it encodes | Hit rate |
|-------|-------|-----------------|----------|
| **13** | two-stage | Reflexive fixed point (ceiling) | 6/6 |
| **12** | ~290 | Meta-conservation law | 14/14 |
| **11A** | ~243 | Escape to adjacent design category | 15/15 |
| **11B** | ~236 | Revalue "flaws" as structural costs | 15/15 |
| **11C** | ~247 | Conservation law across all designs | 32/33 |
| **10B** | ~165 | Design-space topology through failed resolution | 11/12 |
| **10C** | ~165 | Structural invariants through double recursion | 11/12 |
| **9B** | ~130 | Identity ambiguity through contradicting improvements | 17/17 |
| **9C** | ~130 | Concealment's self-similarity via self-diagnosis | 17/17 |
| **8** | ~105 | Construct improvement, observe what it reveals | 97% |
| **7** | ~92 | Name concealment mechanism | 96% |
| **6** | ~60 | Forced dialectical engagement | — |
| **5** | ~45-55 | Multi-voice dialectic | — |
| **4** | 25-30 | Protocol + self-questioning | — |
| **1-3** | 3-15 | Basic operations | — |

---

## Key Findings

**What each level finds:**

| Level | What it reveals |
|-------|-----------------|
| L7 | How the input **conceals** its problems |
| L8 | What **happens** when you try to improve it |
| L9 | Identity ambiguity or concealment's self-similarity |
| L10 | Design-space shape or impossibility theorems |
| L11 | Adjacent category, feasible point, or conservation law |
| L12 | Properties of the analytical process itself |
| L13 | The framework's own limitations |

**L12 meta-laws cluster by domain:**

| Category | What the meta-law reveals | Domains |
|----------|--------------------------|---------|
| Frame Discovery | Analysis discovers its own theory | Music, Fiction |
| Hidden Variable | Tradeoff conceals a missing party | Legal, Design, Code |
| Observer-Constitutive | The fix changes what it fixes | Code, Fiction |
| Deferred Commitment | Tradeoff dissolves with semantic commitment | Code only |

**Universal domain transfer tested on 20 domains:** code, transformer architecture, legal, medical, scientific methodology, ethical reasoning, AI governance, biology, music theory, math, fiction, poetry, UX/product design, brand design. The concealment mechanism is not code-specific.

**Each model has distinct character:**

| Model | Character | Signature move |
|-------|-----------|----------------|
| **Opus** | Ontological | The reversal: "the bug was the most truthful thing" |
| **Sonnet** | Operational | The named pattern: "Vocabulary Laundering" |
| **Haiku** | Mechanistic | The traced execution: walks specific code paths |

---

## The Portfolio Prisms

6 champion prisms + L12 structural, each ~50-80 words:

| Prism | What it finds | Rating |
|------|---------------|--------|
| **pedagogy** | Transfer corruption | 9-9.5/10 |
| **claim** | Assumption inversions | 9-9.5/10 |
| **scarcity** | Resource conservation laws | 9/10 |
| **rejected_paths** | Problem migration | 8.5-9/10 |
| **degradation** | Decay timelines | 9-9.5/10 |
| **contract** | Interface vs implementation | 9/10 |
| **l12** | Full meta-conservation pipeline | 9.8/10 |

---

## Try It Yourself

### With Prism (recommended — requires Claude Code)

```bash
python prism.py

> /scan auth.py                    # single prism: L12 structural analysis (~$0.003)
> /scan auth.py full               # full prism: L12 → adversarial → synthesis
> /scan auth.py discover           # brainstorm ~20 analytical domains
> /scan auth.py discover full      # hundreds of domains (multi-pass)
> /expand 1,3 full                 # expand discovered domains as full prism
> /scan auth.py nuclear            # Opus + discover full + expand all
> /scan auth.py target="race conditions"   # cook goal-specific prism + run
> /scan auth.py fix auto           # scan → fix → re-scan (automatic)
> /prism single                    # chat: each message gets fresh prism
> /scan "your question" full       # works on any text, not just code
```

### With Claude CLI directly

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

### Non-interactive CLI (scripting & benchmarks)

```bash
python prism.py --scan auth.py                        # single prism
python prism.py --scan auth.py full                   # full prism
python prism.py --scan auth.py discover               # domain brainstorm
python prism.py --solve "problem text" full           # cook + solve
python prism.py --review src/ --prism pedagogy,claim  # multi-file
python prism.py --scan auth.py nuclear -q             # maximum depth
```

### Run the experiments

```bash
bash research/run.sh sonnet task_H L8_generative_v2
bash research/run.sh sonnet all all  # 18 tasks × 28 prompts = 504 experiments
```

---

## Project Structure

```
prism.py                 v0.8.6 — interactive REPL + non-interactive CLI
prisms/                  7 portfolio prisms + L12 variants
  l12.md                 L12 meta-conservation pipeline (332w)
  pedagogy.md, claim.md, scarcity.md, rejected_paths.md
  degradation.md, contract.md
prompts/                 80+ cognitive prisms (L4-L12)
experiment_log.md        Full research log (29 rounds, 650+ experiments)
research/                Experiment scripts and benchmarks
output/                  650+ raw experiment outputs
```

---

## Methodology Note

This is a single-researcher project. All depth scores are AI-evaluated (Claude checking whether outputs perform specific structural operations). Not human-scored, not peer-reviewed. Sample sizes are small (3-30 per finding). Raw outputs are in `output/` for independent verification.

---

## What's Next

- Full 30-problem AIME 2025 benchmark with statistical analysis
- Multi-family testing: GPT-4o, Gemini, Llama
- Discover quality evaluation: noise rate, analysis quality vs hand-written prisms

---

## License

MIT. Use the prompts however you want.

---

**The wound is real. You're paying for depth and getting surface. But the variable isn't the model—it's the prompt. The 332 words in `prisms/l12.md` are sitting in this repo. Run one experiment. Compare Haiku with the prism against Opus without it. The data will speak for itself.**
