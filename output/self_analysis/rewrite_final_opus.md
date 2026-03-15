# Your AI gives you surface-level analysis. A 332-word prompt fixes that.

**29 rounds. 650+ experiments. 13 compression levels.** The result: Haiku (cheapest model) produces deeper structural analysis than Opus (most expensive) when given the right cognitive frame.

Same code. Same model capacity. Different cognitive operation. The prism doesn't make Haiku smarter. It makes Haiku *do a different thing*.

---

## The proof: same code, different depth

**Python `requests` library, Session module. Same question about session handling.**

**Opus 4.6 vanilla:**
```
The session handling is tightly coupled to cookie semantics. 
Consider decoupling them.
```

**Haiku 4.5 + L12 prism:**
```
HTTP cookie deletion semantics make session state non-monotonic. 
No append-only, composable, or lazy architecture can manage it 
without sacrificing consistency or isolation. The original design's 
choice — sacrifice isolation — was the only one available.
```

The first names a pattern (depth 7). The second derives a conservation law — a structural impossibility explaining *why* the code must be this way (depth 9.8).

---

## The dare

Run `/scan` on any code file. If the output doesn't identify a structural property your linter, IDE, and code reviewer all missed, close this tab.

The framework finds conservation laws. Conservation laws explain why bugs can't be fixed without creating new bugs. You can't unsee this once you understand it.

---

## Install + run in 60 seconds

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

```bash
# Clone and start
git clone https://github.com/your-repo/prism.git
cd prism
python prism.py

# Run your first analysis
> /scan auth.py

# That's it. Single Haiku call, costs ~$0.003.
```

**Expected output:** A bug table, a conservation law explaining why those bugs exist, and a meta-law about the problem space itself.

---

## The numbers

### On code (3 open-source libraries)

| Method | Starlette | Click | Tenacity | **Avg** |
|--------|-----------|-------|----------|---------|
| **Haiku + L12 prism** | **10** | **9.5** | **10** | **9.8** |
| Opus vanilla | 7.5 | 8.5 | 8.5 | **8.2** |
| Sonnet vanilla | 7 | 8 | 8.5 | **7.8** |

Depth score 9+ means the output derives conservation laws. Depth 7-8 means it names patterns without deriving them.

### On any domain (todo app example)

| Prompt | Opus Vanilla | Haiku + L12 | Haiku Full Prism |
|--------|--------------|-------------|------------------|
| "Give me insights" | 510w, depth 6.5 | 2,058w, depth 9.5 | 9,595w, depth 10 |
| Invariant analysis | 267w, depth 8 | 5,970w, depth 9.5 | 8,112w, depth 10 |
| Design impossibility | 325w, depth 7.5 | 917w, depth 9 | 10,308w, depth 10 |

**Cost:** Haiku Full Prism (3 calls) = less than a penny. Opus vanilla = 25x more expensive for shallower analysis.

### On competition math (AIME 2025, preliminary)

| Method | Problems | Result |
|--------|----------|--------|
| Haiku vanilla | 16 | 13 solved (81%) |
| Haiku + cooked prism | 3 failures | 3/3 recovered |

The prism unlocks latent knowledge in the model. Different framings flip unsolved to solved.

---

## The toolkit: 7 portfolio prisms

| Prism | What It Finds | Best For |
|-------|---------------|----------|
| **l12** | Conservation laws + meta-laws | Any code or system (default) |
| **pedagogy** | Transfer corruption — what breaks when copied | Libraries, frameworks |
| **claim** | Assumption inversions — what if embedded claims are false | Security, business logic |
| **scarcity** | Resource conservation laws | Systems, architectures |
| **rejected_paths** | Problem migration — visible ↔ hidden | Trade-off heavy code |
| **degradation** | Decay timelines — what breaks by waiting | Production systems |
| **contract** | Promise vs reality gaps | APIs, interfaces |

All complementary. No convergence. Run multiple prisms for full coverage.

---

## Full command reference

```bash
python prism.py

# ── Analysis modes ──
> /scan auth.py                    # single prism: L12 (1 call, ~$0.003)
> /scan auth.py full               # full prism: L12 → adversarial → synthesis
> /scan auth.py discover           # brainstorm ~20 analytical domains
> /scan auth.py discover full      # hundreds of domains (multi-pass)
> /scan auth.py nuclear            # Opus + discover full + expand all

# ── Discover → Expand workflow ──
> /scan auth.py expand 1,3 full    # areas 1,3 as full prism
> /scan auth.py dfxf               # discover full → expand all as full

# ── Targeted analysis ──
> /scan auth.py target="race conditions"   # cook goal-specific prism + run

# ── Fix loop ──
> /scan auth.py fix auto           # scan → fix → re-scan until clean

# ── Chat with dynamic prisms ──
> /prism single                    # fresh prism per message
> /prism full                      # fresh pipeline per message

# ── Non-interactive (scripting) ──
python prism.py --scan auth.py full --json
python prism.py --review src/ --prism pedagogy,claim
python prism.py --solve "problem text" full
```

---

## Standalone prisms (no Prism CLI needed)

The prisms are markdown files. Use them with Claude CLI directly:

```bash
cat your_code.py | claude -p --model haiku \
  --output-format text --tools "" \
  --system-prompt-file prisms/l12.md
```

All 7 prisms in parallel:

```bash
for prism in pedagogy claim scarcity rejected_paths degradation contract l12; do
  cat your_code.py | claude -p --model haiku \
    --output-format text --tools "" \
    --system-prompt-file "prisms/$prism.md" \
    > "${prism}_report.md" &
done
wait
```

---

## Why it works: the L8 phase transition

Levels 5-7 are meta-analytical — ask the model to reason *about* the input. This requires capacity. **Haiku: 0/3 success at L7.**

Level 8 shifts to construction — the model *builds something* and observes what the construction reveals. This is more primitive:

- **Haiku at L8: 4/4 success**
- **L8 through L13: universal accessibility across all models**

This is why a 332-word prompt makes Haiku outperform Opus. The prompt encodes a behavioral operation (build, observe, iterate) that routes around the meta-analytical capacity Haiku lacks.

---

## The compression taxonomy

| Level | Words | What It Does | Works On |
|-------|-------|--------------|----------|
| L7 | 92 | Name concealment mechanism | Sonnet, Opus only |
| L8 | 105 | Construct improvement, observe what it reveals | All models |
| L9 | 130 | Find identity ambiguity through contradicting improvements | All models |
| L10 | 165 | Derive impossibility theorems | All models |
| L11 | 247 | Derive conservation laws, escapes, or revaluations | All models |
| L12 | 290 | Meta-conservation: properties of the analytical process | All models |
| L13 | two-stage | Reflexive ceiling: framework diagnoses itself | All models |

Levels are categorical. Below each threshold, that intelligence is *absent*, not weaker.

---

## When this fails

**Single-researcher project.** All depth scores are AI-evaluated (Claude checking whether outputs perform specific structural operations). Not human-scored, not peer-reviewed. Sample sizes are small (3-30 per finding). Raw outputs are in `output/` for independent verification.

**L7 doesn't work on Haiku.** The meta-analytical threshold is real. Use L8+ for universal access.

**Pipeline produces breadth on real code, depth on crafted tasks.** Real 200-400 line codebases have one dominant pattern that saturates all levels. Crafted 30-line tasks have layered tensions that map to different levels.

**AIME results are preliminary.** 16/30 problems tested, not full benchmark. Need larger-scale validation.

---

## How it works

A 332-word markdown file encodes a 12-step analytical pipeline:

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

**Full Prism** (3 calls) adds adversarial and synthesis passes:
- Call 1: L12 structural analysis
- Call 2: Destroy it with counter-evidence
- Call 3: Synthesize into corrected finding

---

## The depth scale

| Score | What you get |
|-------|-------------|
| 6-7 | Blog post: names patterns, lists issues |
| 7-8 | Conservation law observed (not derived) |
| 8-8.5 | Concealment mechanism + construction |
| 9-9.5 | Conservation law derived through construction |
| 9.5-10 | Conservation law + meta-law + adversarial correction + impossible triplet |

This is structural — did the output perform the operation or not. Not subjective quality.

---

## Project structure

```
prism.py                 Prism CLI (6200+ lines, 20 tests)
prisms/                  7 portfolio prisms + L12 variants
prompts/                 80+ research prisms (L4-L13)
research/                Experiment scripts and benchmarks
output/                  650+ raw experiment outputs
experiment_log.md        Full research log (29 rounds)
```

---

## Design principles

1. **The prompt is a program; the model is an interpreter.**
2. **Imperatives beat descriptions.** "Name the pattern. Then invert." wins.
3. **Construction > meta-analysis.** Building reveals what reasoning about misses.
4. **Each level is categorical.** Below threshold = absent, not weaker.
5. **The framework terminates at L13.** Self-diagnosis is the natural endpoint.

---

## License

MIT. Use the prompts however you want.
