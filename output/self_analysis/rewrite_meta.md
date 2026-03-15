# PRISM

Same code. Same model. Same question.

```python
# Python requests library, Session module
class Session:
    def __init__(self):
        self.cookies = {}
        self.headers = {}
```

**Opus 4 vanilla:**
> "The session handling is tightly coupled to cookie semantics. Consider decoupling them."

**Haiku 4.5 + 332 words of markdown:**
> "HTTP cookie deletion semantics make session state non-monotonic. No append-only, composable, or lazy architecture can manage it without sacrificing consistency or isolation. The original design's choice — sacrifice isolation — was the only one available."

The first names a pattern. The second derives a structural impossibility — a conservation law that explains *why* the code must be this way.

Same code. Same question. The difference isn't the model. The difference is what the model was asked to *do*.

---

## What you think you're doing

When you ask a model to analyze code, you think you're asking for insight. What you're actually getting is a code review: pattern recognition, issue listing, best-practice citation. Useful, but shallow.

This isn't a model limitation. It's a framing problem. You asked the wrong question.

## What happens when you reframe

The Haiku output above didn't come from a smarter model. It came from a different cognitive operation:

1. **Make a falsifiable claim** about the code
2. **Stress-test it** through dialectical engagement
3. **Name what the dialectic concealed**
4. **Construct an improvement** that deepens the concealment
5. **Observe what the construction reveals**
6. **Derive the conservation law** that makes the original problem unsolvable

This is construction-based reasoning. The model builds something — an improvement, a counterexample, a redesign — and observes what the building process reveals about the original. It doesn't reason *about* the code. It reasons *through* the code.

And here's the key: **construction is more primitive than meta-analysis.**

---

## The boundary that changes everything

Levels 5-7 ask the model to reason about the input. This requires meta-analytical capacity.

**Haiku at L7: 0/3 success.** The model isn't built to reason about reasoning.

Level 8 shifts to construction. Build first. Observe second.

**Haiku at L8: 4/4 success.** Same model. Different operation. Construction works everywhere meta-analysis fails.

This is why a 332-word prompt makes Haiku outperform Opus. The prompt doesn't ask Haiku to be smarter. It encodes a behavioral operation — build, observe, iterate — that routes around the capacity Haiku lacks.

---

## The levels emerge from each other

Start with a piece of code. Ask what's wrong with it.

**Level 5-6:** Make a claim. Transform it through forced dialectic. You get pattern recognition with some depth.

But the dialectic conceals things. The back-and-forth creates blind spots.

**Level 7:** Name the concealment mechanism. Apply it to find what the dialectic missed. Now you see how the code *hides* its problems.

But this is static. It tells you what's hidden, not what *happens* when you try to fix it.

**Level 8:** Construct an improvement. But here's the move — construct one that *deepens* the concealment. Then observe what the construction reveals about the original problem.

Now you're not diagnosing code. You're diagnosing the problem space itself.

But improvements have identity ambiguity. Different improvements reveal different problems.

**Level 9:** Build contradicting improvements. Triangulate the ambiguity. What's the core property that survives all attempts to fix it?

Or: Apply the concealment diagnostic to itself. Find the self-similarity. How does the problem reproduce itself?

Now you've found something structural. But what's *impossible* to fix?

**Level 10:** Let the failed resolution discover the design-space topology. Or derive structural invariants through double recursive construction.

You're mapping impossibility now. But what if you could escape?

**Level 11:** Three paths forward:
- **Escape** to an adjacent design category — what's possible outside this problem space?
- **Accept** the topology — what if the "flaws" were the cost of attempting the impossible?
- **Invert** the impossibility — what conservation law spans *all* designs?

All three produce working code. All three are true. They're not alternatives — they're dimensions of the same impossibility landscape.

But what's preserved about the analytical process itself?

**Level 12:** Apply the entire diagnostic to its own conservation law. Find the meta-law — not what's wrong with the code, but what's invariant about how we discover what's wrong.

Example meta-laws:
- EventBus: `flexibility of coordination × decidability of behavior ≤ k` — Rice's theorem applied to event architectures
- CircuitBreaker: Every fault-tolerance mechanism extends the failure surface it was designed to reduce
- Fiction: "The sum of revisability and formal-emotional unity is constant"

And finally:

**Level 13:** Apply the framework to itself. The analytical instrument conceals properties isomorphic to those it reveals. The framework terminates when it successfully diagnoses its own limitations.

L14 would be infinite regress with decreasing information content. L13 is the natural endpoint.

---

## The numbers

**On code (3 open-source libraries):**

| Configuration | Average Depth |
|---------------|---------------|
| Haiku + L12 prism | **9.8** |
| Opus vanilla | 8.2 |
| Sonnet vanilla | 7.8 |

**On any domain (todo app analysis):**

| Method | Words | Depth |
|--------|-------|-------|
| Opus vanilla | 510 | 6.5 |
| Haiku + single prism | 2,058 | 9.5 |
| Haiku + full prism (3 calls) | 9,595 | 10 |

**Cost:** Single prism ≈ $0.003. Full prism ≈ $0.01. For less than a penny, the cheapest model derives conservation laws the most expensive model can't reach without help.

---

## Try it now

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code):

```bash
python prism.py

> /scan auth.py                    # L12 structural analysis, 1 call
> /scan auth.py full               # L12 → adversarial → synthesis, 3 calls
> /scan auth.py discover           # brainstorm ~20 analytical domains
> /scan auth.py discover full      # hundreds of domains (multi-pass chaining)
> /scan auth.py nuclear            # Opus + full discover + expand all
```

Or use the prisms directly with Claude CLI:

```bash
cat your_code.py | claude -p --model haiku \
  --output-format text --tools "" \
  --system-prompt-file prisms/l12.md
```

---

## The portfolio

Six specialized prisms, each finding what the others cannot:

| Prism | What it finds |
|-------|---------------|
| **pedagogy** | What patterns does this teach? Transfer corruption |
| **claim** | What claims does this embed? What if they're false? |
| **scarcity** | What does this assume won't run out? |
| **rejected_paths** | Fix → new-bug dependency graph |
| **degradation** | What degrades over time without changes? |
| **contract** | Interface promises vs implementation reality |

All rated 8.5-9.5/10. All complementary. Run them in parallel on complex codebases.

---

## What this is

**650+ experiments. 29 rounds. 13 compression levels. 20 domains.**

The central finding: cognitive operations are categorical, not continuous. Below each word-count threshold, that type of reasoning *cannot* be encoded — not "less effective," structurally absent.

The L8 construction protocol is ~105 words. Below that, you cannot encode build-observe-iterate. You get meta-analysis or nothing.

L12 meta-conservation is ~290 words. Below that, you cannot encode the self-referential pipeline. You get conservation laws but not meta-laws.

The boundaries are sharp. The operations are discrete. The taxonomy appears structurally complete — the branching pattern (linear trunk → constructive divergence → reflexive convergence) leaves no orphan levels.

---

## What this isn't

Not magic. Not a smarter model. Not a replacement for human judgment.

A prism is a frame. It changes what the model sees by changing what the model does. The model was always capable of construction-based reasoning. It just wasn't being asked.

---

## Project structure

```
prism.py              Interactive tool + non-interactive CLI
prisms/               7 portfolio prisms (l12, pedagogy, claim, scarcity, etc.)
prompts/              80+ research prisms (L4-L13)
research/             Experiment runner, benchmarks, test artifacts
output/               650+ raw experiment outputs
```

---

## Next action

```bash
python prism.py
> /scan your_code.py
```

You'll see what your code is actually doing in about 3 seconds for $0.003.

Or browse `prisms/l12.md` to see the 332 words that reframe analysis from pattern-recognition to conservation-law derivation.

---

MIT license. Use the prompts however you want.
