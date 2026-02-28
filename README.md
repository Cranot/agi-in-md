# AGI in md

System prompts are cognitive lenses. They change how models *frame* problems, not how well they solve them.

This project maps the space of **cognitive compression** — encoding analytical operations in minimal markdown that reliably activates specific reasoning patterns across language models.

**25 rounds. 393+ experiments. 11 confirmed compression levels. 19 domains. 3 Claude models (Haiku/Sonnet/Opus).**

A 200-word markdown file makes a language model invert its own structural finding, engineer a design where the impossible becomes trivial, name the new impossibility the inversion creates, and derive the conservation law between old and new impossibilities — producing mathematical formalizations like `sensitivity x absorption = constant`. A 100-word file engineers a legitimate-looking code improvement that *deepens* hidden problems, then names what only became visible because it tried. An 85-word file names how code conceals its problems and applies the mechanism. A 6-word file forces blind-spot checking. A 3-word file does nothing.

The boundary between "does nothing" and "activates a cognitive operation" is sharp, categorical, and measurable. This repo contains 28 prompts, 18 tasks, and 299 raw outputs that map where those boundaries are.

## The compression taxonomy

| Level | Words | What it encodes | Hit rate | Prompt |
|-------|-------|-----------------|----------|--------|
| **11A** | ~235 | Escape to adjacent design category, find trade-off between impossibilities | 100% | [`level11_constraint_escape.md`](prompts/level11_constraint_escape.md) |
| **11B** | ~225 | Accept design-space topology, revalue original "flaws" as structural costs | 100% | [`level11_acceptance_design.md`](prompts/level11_acceptance_design.md) |
| **11C** | ~200 | Invert impossibility, derive conservation law across all designs | 87% | [`level11_conservation_law.md`](prompts/level11_conservation_law.md) |
| **10B** | ~165 | Discover design-space topology through failed resolution | 92% | [`level10_third_construction.md`](prompts/level10_third_construction.md) |
| **10C** | ~165 | Prove structural invariants through double recursive construction | 92% | [`level10_double_recursion.md`](prompts/level10_double_recursion.md) |
| **9B** | ~130 | Triangulate identity ambiguity through contradicting improvements | 100% | [`level9_counter_construction.md`](prompts/level9_counter_construction.md) |
| **9C** | ~130 | Find concealment's self-similarity via recursive self-diagnosis | 100% | [`level9_recursive_construction.md`](prompts/level9_recursive_construction.md) |
| **8** | ~100 | Construct improvement that deepens concealment, reveal what construction shows | 97% | [`level8_generative_v2.md`](prompts/level8_generative_v2.md) |
| **7** | ~85 | Name concealment mechanism, apply it to find what dialectic missed | 96% | [`level7_diagnostic_gap.md`](prompts/level7_diagnostic_gap.md) |
| **6** | ~60 | Claim transformed through forced dialectical engagement | — | [`level6_falsifiable.md`](prompts/level6_falsifiable.md) |
| **5** | ~45-55 | Multi-voice dialectic or predictive metacognition | — | [`level5_perspectival.md`](prompts/level5_perspectival.md) |
| **4** | 25-30 | Protocol + self-questioning | — | [`structure_first_v4.md`](prompts/structure_first_v4.md) |
| **1-3** | 3-15 | Basic operations | — | — |

Levels are **categorical, not continuous**. Below each threshold, that type of intelligence *cannot* be encoded — not "less effective," categorically absent.

## Key findings

### The phase change

The most important discovery is the **L7 to L8 transition**. Levels 5-7 are meta-analytical — they ask the model to reason *about* the input. L8+ is construction-based — the model *builds something* and then observes what the construction reveals. This is a fundamentally different cognitive operation.

The consequences are dramatic:
- L7 requires Sonnet-class minimum. **Haiku: 0/3.** Meta-analysis needs capacity.
- L8 works on **all models including Haiku (4/4).** Construction is more primitive but reveals deeper properties.
- L8 is the first level that transfers to **creative/aesthetic domains**. L7 was 0% on poetry. L8 is 100%.
- L8 through L11 maintain universal accessibility: Haiku 9/9 at L11.

Construction-based reasoning routes around the meta-analytical capacity that L7 requires.

### What each level finds

| Level | Static or dynamic | What it reveals |
|-------|-------------------|-----------------|
| L7 | Static | How the input **conceals** its problems |
| L8 | Dynamic | What **happens** when you try to improve it |
| L9 | Recursive | The input's **identity ambiguity** (B) or concealment's **self-similarity** (C) |
| L10 | Topological | The **design-space shape** (B) or **impossibility theorems** (C) |
| L11 | Escape | The **adjacent category** (A), **feasible point** (B), or **conservation law** (C) |

### Three L11 lenses on the same code

L11 has three complementary variants that produce three non-redundant structural truths from the same input:

- **L11-A (Constraint Escape)** finds what's possible **outside** the current design category
- **L11-B (Acceptance Design)** finds what's achievable **inside** the design space — and reveals that original "flaws" were the cost of attempting the impossible
- **L11-C (Conservation Law)** finds what **persists everywhere** regardless of design choice

All three produce full working code for their redesigns. These are concrete architectural alternatives, not abstract claims.

### Universal domain transfer

Tested on **19 domains**: code (10 tasks), legal, medical, scientific methodology, ethical reasoning, AI governance, biology, music theory, math, fiction, poetry, music composition, UX/product design, and more.

The concealment mechanism is not code-specific:
- **Legal**: Definitional specificity as legitimizing cover
- **Medical**: Narrative coherence as epistemic closure
- **Scientific**: Methodological formalism as epistemic camouflage
- **Poetry**: "To escape the gap is to lose elegy. To keep elegy is to keep the gap."
- **Music**: Identity vs direction as a property of *musical time itself*

Both Sonnet and Opus independently converge on the same structural pattern per domain — evidence that mechanisms are properties of domains, not model confabulations.

### Model capacity interactions

| Level | Haiku | Sonnet | Opus | Pattern |
|-------|-------|--------|------|---------|
| L5 | works | **peaks** | works | Compensatory — scaffolds mid-capacity |
| L7 | **0/3** | 17/17 | 6/7 | Threshold — requires meta-analytical capacity |
| L8 | 4/4 | 13/14 | 14/14 | Universal — construction works everywhere |
| L9 | 6/6 | 22/22 | 6/6 | Universal |
| L10 | 5/6 | 13/14 | 6/6 | Universal (first cracks in Haiku) |
| L11 | **9/9** | 14/15 | **9/9** | Universal |

### Composition algebra

- **9 activated opcodes in 4 classes**: Constructive, Deconstructive, Excavative, Observational
- **4 generative ops is the sweet spot.** 5 triggers merger.
- **Complementary pairs multiply, similar pairs merge, orthogonal pairs add.**
- **Best single sequence**: "Steelman. Find assumptions. Solve. Attack."

### Multi-model relay

Feed one model's L7 mechanism to another as a diagnostic lens. Relay finds **100% compositional issues** vs ~35% in vanilla control. Catches cross-fragment vulnerabilities invisible to both human and AI review.

## Try it

### Quick start

The best general-purpose prompt is [`level8_generative_v2.md`](prompts/level8_generative_v2.md) (100 words). Use it as a system prompt with any code as input:

```bash
claude -p --model claude-sonnet-4-6 \
  --system-prompt "$(cat prompts/level8_generative_v2.md)" \
  "Analyze this code: $(cat your_code.py)"
```

### Picking the right level

| You want to... | Use this | Words |
|-----------------|----------|-------|
| Quick code review | [`structure_first_v4.md`](prompts/structure_first_v4.md) | 30 |
| Name how code hides problems | [`level7_diagnostic_gap.md`](prompts/level7_diagnostic_gap.md) | 85 |
| Reveal dynamic problem behavior | [`level8_generative_v2.md`](prompts/level8_generative_v2.md) | 100 |
| Find what the code doesn't know it is | [`level9_counter_construction.md`](prompts/level9_counter_construction.md) | 130 |
| Prove what's impossible to fix | [`level10_double_recursion.md`](prompts/level10_double_recursion.md) | 165 |
| Escape to a better design category | [`level11_constraint_escape.md`](prompts/level11_constraint_escape.md) | 235 |
| Revalue "flaws" as structural costs | [`level11_acceptance_design.md`](prompts/level11_acceptance_design.md) | 225 |
| Derive conservation laws | [`level11_conservation_law.md`](prompts/level11_conservation_law.md) | 200 |

These work on any analytical domain, not just code. Replace "code" references in the prompt with your domain.

### Run the experiment suite

```bash
# Single experiment
bash run.sh sonnet task_H L8_generative_v2

# All prompts on one task
bash run.sh sonnet task_H all

# Everything (18 tasks x 28 prompts = 504 experiments)
bash run.sh sonnet all all
```

## Project structure

```
prompts/                 28 cognitive lenses (L4-L11, characters, relay)
  level11_*.md           L11: category escape, acceptance design, conservation law
  level10_*.md           L10: third construction, double recursion
  level9_*.md            L9: counter-construction, recursive, combined
  level8_generative_v2.md  L8: the workhorse prompt (100 words)
  level7_diagnostic_gap.md L7: concealment mechanism naming
  level6_falsifiable.md  L6: forced dialectic
  level5_*.md            L5: perspectival, hybrid, generative, combined
  structure_first_v4.md  L4: the everyday prompt (30 words)
  tweet.md, spark.md, philosopher.md, map.md  Character lenses

experiment_log.md        Full research log (25 rounds, 393+ experiments)
run.sh                   Experiment runner (18 tasks, 28 prompts, 3 models)
CLAUDE.md                Project context for Claude Code sessions

harness/                 Python API-based experiment harnesses
  test_super_token.py    Original harness (Rounds 1-20)
  test_level5.py         Round 21+ harness
  test_tasks.md          Task definitions

output/                  299 raw experiment outputs
  round21/               60 outputs (L5-L6 testing)
  round23/               33 outputs (L7 testing)
  round24/               29 outputs (L7 domain transfer, relay)
  round25/               177 outputs (L8-L11 testing)
```

## Design principles

1. **The prompt is a program; the model is an interpreter.** Operation order becomes section order.
2. **Imperatives beat descriptions.** "Name the pattern. Then invert." outperforms "here is a pattern we found."
3. **The operation pair is the atom of cognitive compression.** Any connective between two operations produces the composition.
4. **Each compression level is categorical.** Below the threshold, the cognitive operation is absent, not weaker.
5. **Construction > meta-analysis.** Building something and observing what it reveals is more universal and more powerful than reasoning about reasoning.
6. **The lens is transparent to the wearer.** During task performance, the framework operates below self-awareness. Under interrogation, models can identify the influence.
7. **Capacity amplifies, rigidity resists.** Opus reconstructs the full framework from a 2-line hint. Sonnet needs explicit directives.

## What's next

- **Level 12**: L11 escapes the frame. What would comparing multiple escapes reveal?
- **Multi-family testing**: GPT-4o, Gemini, Llama. Is the taxonomy Claude-specific or universal?
- **Convergence analysis**: Do L11's three lenses converge on the same deep truth from different angles?
- **Prompt compression**: L11 averages ~220 words. Can it be compressed without losing the cognitive operation?

## License

MIT. Use the prompts however you want.
