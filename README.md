# AGI in md

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Your most expensive model produces shallow analysis because you're asking it to reason *about* problems instead of *through* them. A 332-word prompt fixes this.

A **prism** is a markdown file used as a system prompt. Instead of asking the model to "analyze deeply," it tells the model to do specific things: make a claim, attack it, build an improvement, watch what breaks, derive what can't change. This repo contains 48 prisms + 12 scan modes + the tooling to use them. The newest prisms detect their own knowledge gaps and self-correct confabulated claims.

**Same code. Same question. Different instructions:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ OPUS 4.6 VANILLA ($25 per million output tokens)                            │
│ Analyzing Python requests library Session module                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ "The session handling is tightly coupled to cookie semantics. Consider      │
│  decoupling them."                                                          │
│                                                                             │
│  → Names a pattern. Depth: 7/10                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ HAIKU 4.5 + L12 PRISM ($5 per million output tokens)                        │
│ Analyzing Python requests library Session module                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ "HTTP cookie deletion semantics make session state non-monotonic. No        │
│  append-only, composable, or lazy architecture can manage it without        │
│  sacrificing consistency or isolation. The original design's choice —       │
│  sacrifice isolation — was the only one available."                         │
│                                                                             │
│  → Derives a trade-off that can't be escaped. Explains WHY the code         │
│    must be this way.                                                        │
│  → Depth: 9.8/10                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

**The prism didn't make Haiku smarter. It made Haiku do a different thing.** Vanilla tells you what to change. The prism tells you why you can't — and what you'd lose if you tried.

---

## Try It

Run `/scan` on any file over 100 lines. ([Setup takes 30 seconds.](#install)) The L12 prism will derive a conservation law specific to your code's structure — a trade-off your design encodes that you may not have noticed.

---

## The Numbers

Depth = how deep the analysis goes, scored 1-10. Naming a pattern is ~7. Deriving a structural trade-off the code can never escape is ~9.5. Finding a law about those trade-offs themselves is 10. AI-evaluated, not human-scored. Raw outputs in `output/`.

| Metric | Result |
|--------|--------|
| **Cost** | Single scan ~$0.05 (Sonnet), ~$0.01 with Haiku |
| **Depth gain** | **9.8 avg vs 8.2 avg** on real code (Starlette, Click, Tenacity) |
| **Experiments** | **1,000+** raw outputs across 41 research rounds |
| **Domains tested** | **20+** — code, math, philosophy, legal, medical, music, fiction, business, more |
| **Hit rate** | **97%+** on construction-based analysis, **14/14** on full pipeline |
| **Confabulation** | L12-G: **90% zero-confabulation** (9/10 runs, N=10) |
| **Cross-language** | Python, Go, TypeScript validated |

### Round 41: The Format Is the Intelligence

We replaced every domain word in the L12 prism with nonsense ("glorpnax," "blorpwhistle") — same imperative format, numbered steps, output requirements. **It scored 10/10.** The original scored 9. Format carries meaning independently of vocabulary.

This led to gap detection: prisms that identify what the analysis **can't verify**. Two complementary prisms — `knowledge_boundary` (classifies claims) and `knowledge_audit` (attacks confabulation) — catch errors that L12 misses:

- `asyncio.RWLock` doesn't exist in Python stdlib → L12 proposed it as an improvement → boundary caught it
- O(n)+O(n) labeled "quadratic" → mathematical error → audit caught it
- Neither prism caught both. They're complementary.

**L12-G** compresses this into a single pass: analyze → audit → self-correct. Zero confabulation in 90% of runs. Same cost as L12.

**Oracle** goes further: 5 phases (depth → epistemic typing → self-correction → reflexive diagnosis → harvest). Every claim tagged `[STRUCTURAL]`, `[DERIVED]`, `[KNOWLEDGE]`, or `[ASSUMED]` so you know what to trust.

```bash
python prism.py --scan auth.py oracle     # maximum trust, 5-phase
python prism.py --scan auth.py --trust    # same thing
python prism.py --scan auth.py l12g       # self-correcting, zero confab
python prism.py --scan auth.py verified   # 4-call gap pipeline
python prism.py --scan auth.py gaps       # show what to NOT trust
```

---

## Install

**Requirements:**
- Python 3.9+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — `npm install -g @anthropic-ai/claude-code`, then run `claude` to authenticate

```bash
git clone https://github.com/Cranot/agi-in-md.git
cd agi-in-md
pip install -r requirements.txt   # jsonschema (only dependency)
python prism.py                   # Starts interactive REPL
```

No API key needed — `prism.py` wraps the Claude Code CLI, which uses your Claude subscription. Use `python3` instead of `python` on Linux/Mac if needed.

---

## How It Works

The default prism ([`prisms/l12.md`](prisms/l12.md)) is a 332-word markdown file. It tells the model to:

```
make a falsifiable claim → have three voices attack it → name what the input hides →
build an improvement → watch what the improvement breaks → find the trade-off you can't escape
(conservation law) → find the law about that law (meta-law)
```

A **conservation law** is a trade-off that holds no matter what you do — like "flexibility x security = constant" in a routing system. Change one, the other moves. A **meta-law** is a pattern across those trade-offs themselves — what stays true about the analysis, not just the code.

The model executes this pipeline on whatever you give it — code, ideas, designs, systems, strategies.

**The breakthrough:** Ask a model to *reason about* code and it needs to be smart. Ask it to *build something and watch what happens* — any model can do that. Haiku fails at abstract reasoning (0/3). Haiku succeeds at construction (4/4). That's the whole trick.

Construction isn't the only operation that works. Seven alternatives — simulation (run forward in time), archaeology (dig through layers), cultivation (plant requirements and watch), destruction, transplantation, miniaturization, forgery — all work on Haiku single-shot (100%). Different operations find different things, but they all converge at the deepest level on the same structural impossibility.

---

## Quick Start

```bash
python prism.py

# ── Quick scan — 1 call, ~$0.05 ──
> /scan auth.py                             # L12 structural analysis (default)

# ── Trust modes — zero confabulation ──
> /scan auth.py oracle                      # 5-phase: depth + typing + correct + reflect
> /scan auth.py l12g                        # self-correcting (analyze → audit → correct)
> /scan auth.py --trust                     # alias for oracle

# ── Gap detection — what to NOT trust ──
> /scan auth.py gaps                        # L12 + boundary + audit (3 calls)
> /scan auth.py verified                    # full pipeline + re-analysis (4 calls)
> /scan auth.py scout                       # depth + targeted verify (2 calls)

# ── Deep analysis — multiple angles ──
> /scan auth.py full                        # 9-call: 7 structural + adversarial + synthesis
> /scan auth.py 3way                        # WHERE/WHEN/WHY — works on any domain
> /scan auth.py behavioral                  # errors + costs + changes + promises

# ── Meta ──
> /scan auth.py meta                        # analyze what the analysis conceals
> /scan auth.py strategist                  # plan optimal tool sequence for a goal
> /scan auth.py evolve                      # auto-generate domain-adapted prism

# ── Fix + Discover ──
> /scan auth.py fix auto                    # scan → extract → fix → re-scan
> /scan auth.py discover                    # brainstorm ~20 analytical domains
> /scan auth.py target="race conditions"    # cook goal-specific prism + run

# ── Post-processing ──
> /scan auth.py --confidence                # tag claims HIGH/MED/LOW/UNVERIFIED
> /scan auth.py --provenance                # source attribution per finding
> /scan auth.py --depth deep                # shallow|standard|deep|exhaustive

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
# Single prism (L12 optimal on Sonnet; works on Haiku too at lower cost)
cat your_code.py | claude -p --model sonnet \
  --output-format text --tools "" \
  --system-prompt-file prisms/l12.md

# Multiple prisms in parallel (pick from prisms/ — see The Prisms section)
for prism in l12 deep_scan fix_cascade identity optimize error_resilience fidelity; do
  cat your_code.py | claude -p --model sonnet \
    --output-format text --tools "" \
    --system-prompt-file "prisms/$prism.md" \
    > "${prism}_report.md" &
done
wait
```

---

## The Prisms

Each prism is a standalone `.md` file — use with `prism.py`, the Claude CLI (`claude -p --system-prompt-file`), the Anthropic API, or any tool that accepts system prompts.

**Score** = AI-evaluated depth on real production code (Starlette, Click, Tenacity). **Model** = empirically best, auto-selected by `prism.py`. Per-call cost on a ~300 line file: Haiku ~$0.01, Sonnet ~$0.05, Opus ~$0.07.

### Pipelines

`prism.py` selects the right prisms and models automatically — you just pick the mode.

| Mode | Command | What It Does | Calls | Cost |
|------|---------|-------------|-------|------|
| **Single** | `/scan file` | L12 structural analysis — conservation laws, meta-laws, bugs | 1 | ~$0.05 |
| **Full** | `/scan file full` | 7 structural prisms → adversarial attack → synthesis | 9 | ~$0.50 |
| **3-Way** | `/scan file 3way` | WHERE/WHEN/WHY — 3 auto-generated operations → cross-operation synthesis | 4 | ~$0.25 |
| **Behavioral** | `/scan file behavioral` | Error cascades + costs + coupling + identity → synthesis | 5 | ~$0.20 |

**Single** — one call, covers most cases. ~2,000 words, ~10 seconds.

**Full** — on code: runs 7 prisms independently, then a second AI attacks the first AI's conclusions (adversarial pass), then a third synthesizes everything. ~15,000 words, ~3 min. Single finds 16 bugs on Starlette, Full finds 30 — and corrects overclaims. On non-code text, Full auto-routes to 3-Way.

**3-Way** — generates three custom prompts that attack the problem from orthogonal angles (WHERE: dig through structural layers, WHEN: simulate degradation over time, WHY: prove what three desirable properties can't coexist), then synthesizes. The disagreements between the three make the synthesis self-correcting. ~9,000 words, ~2 min. Works on any domain — code, text, strategy.

**Behavioral** — focuses on runtime behavior: how errors cascade, where costs hide, what breaks when you change things. ~8,000 words, ~2 min.

Use `-m haiku` for ~5x cheaper — same depth, occasionally needs a retry.

### Champion Prisms

The best prism per use-case. All auto-selected by `prism.py` — you just pick the mode. Full catalog of all 33 production prisms: **[PRISMS.md](PRISMS.md)**

| Prism | What It Finds | Score | Best For |
|-------|--------------|-------|----------|
| **l12** | Conservation laws + meta-laws + bug table | **9.8** | Default — `/scan file` |
| **identity** | What code claims to be vs what it does | **9.5** | Structural truth |
| **optimize** | Critical path → safe vs unsafe fixes → cost conservation law | **9.5** | Performance |
| **api_surface** | Naming lies: widening, narrowing, misdirecting callers | **9.5** | API design |
| **evolution** | Implicit data contracts that corrupt on schema change | **9.5** | Change impact |
| **deep_scan** | Information destruction, laundering, silent transformation | 9.0 | Boundary analysis |
| **error_resilience** | Corruption cascades: silent exits, deferred failures | 9.0 | Failure tracing |
| **sdl_trust** | Trust topology: assumed authority, escalation paths | 9.0 | Security audit |
| **pedagogy** | Transfer corruption — what breaks when patterns are copied | 9.0 | Any domain |
| **claim** | Assumption inversion — what if accepted truths are false? | 9.0 | Any domain |
| **l12_universal** | L12 at 73 words — always single-shot on any input | 9.0 | Reasoning/text |

11 champions covering code, performance, API, security, and domain-universal analysis. The remaining 22 production prisms are specialized — see [PRISMS.md](PRISMS.md) for temporal, hygiene, writing, codegen, and more.

### Which to pick

| I want to... | Do this |
|--------------|---------|
| Quick structural analysis | `/scan file` — L12, one call, covers most cases |
| Maximum depth on code | `/scan file full` — 7 prisms + adversarial correction + synthesis |
| Deep analysis on any domain | `/scan file 3way` — WHERE/WHEN/WHY + synthesis, works on anything |
| Analyze non-code text | `/scan "your text" full` — auto-routes to 3-Way |
| Focus on runtime behavior | `/scan file behavioral` — errors, costs, coupling, identity |
| Security audit | `/prism security_v1` or `/prism sdl_trust` |
| API design review | `/prism api_surface` + `/prism evolution` |
| Predict what will break | `/prism simulation` or `/prism degradation` |
| Temporal analysis of custom goal | `/scan file target="goal" cooker=simulation` |
| Stratigraphic analysis of custom goal | `/scan file target="goal" cooker=archaeology` |
| Check docs match code | `/prism fidelity` |
| Audit feature wiring | `/prism audit_code` |
| Multiple angles at once | Run 3-5 prisms in parallel (see CLI examples above) |
| Generate code | `/prism codegen` |
| Rewrite text/docs | `/prism writer` → `/prism writer_critique` → `/prism writer_synthesis` |

### What L12 actually produces

These are real outputs — trade-offs the prism discovered on its own, not things you told it to look for:

- **EventBus** (Opus): "The more flexible your event coordination, the less you can predict what the system will do." Predicts: successful retries reset failure counters, the circuit breaker becomes a load amplifier.
- **CircuitBreaker** (Opus): "Every fault-tolerance mechanism extends the failure surface it was designed to reduce." The fix IS the problem.
- **Fiction** (Opus): "The more you can revise a story, the less emotionally unified it becomes." The revision process mirrors the character's own pathology.
- **Brand design** (Sonnet): "Any evaluation system capable of proving a design wrong is structurally excluded from the process that creates the design."

### Works on any domain

The prism doesn't look for code bugs — it looks for structural trade-offs the input can't escape. That works on anything. Tested on 20+ domains:

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

Both Sonnet and Opus independently find the same structural pattern per domain. The models aren't making this up — the patterns were already there.

### The Cookers — prompts that write prompts

The 33 built-in prisms cover code, security, behavior, and temporal analysis. But what about a domain you haven't seen before?

Cookers are meta-prompts that generate new prisms on the fly. You give a goal ("security analysis of routing code"), the cooker writes a custom prism tailored to that goal, then the prism runs on your input. The user never sees the intermediate step — `prism.py` handles it automatically.

| Cooker | What It Generates | Used By |
|--------|-------------------|---------|
| **COOK_UNIVERSAL** | 1 custom prism from any goal | `target=`, `expand single`, `/prism single` |
| **COOK_3WAY** | 4 prompts: WHERE/WHEN/WHY + synthesis | `full` (on text), `3way`, `expand full`, `optimize full`, `target= full` |
| **COOK_UNIVERSAL_PIPELINE** | N chained brainstorm passes | `discover full` only |
| **COOK_SDL_FACTORY** | New permanent prism from analysis output | `--factory` (sees what existing prisms miss) |
| **COOK_SDL_FACTORY_GOAL** | New permanent prism from goal only | `--factory` (no prior analysis needed) |
| **COOK_LENS_DISCOVER** | Reusable analytical pattern from output | `--lens-discover` |

**COOK_UNIVERSAL** (the single-prism cooker, 280+ variants tested) tells the AI: find three desirable properties that can't coexist, build an improvement, watch it recreate the problem deeper, derive the inescapable trade-off. One call, one prism, any domain.

**COOK_3WAY** (the multi-pass cooker) generates three operations that attack the problem from orthogonal angles — WHERE it's vulnerable (dig through structural layers), WHEN it breaks (simulate degradation over time), WHY it must be this way (prove what can't coexist). Each operation has explicit "MUST NOT" constraints preventing it from drifting into the others' territory. A fourth synthesis prompt cross-references all three. This is the default for all multi-pass analysis.

The **factory cookers** create new permanent prisms: run existing prisms on a target, find what they all miss, then reverse-engineer a new prism that sees the gap.

Every cooker runs on Sonnet regardless of your `-m` flag — the cooker's model is the second most important variable after the prism itself.

---

## The Compression Taxonomy

How much analytical depth can you encode in how few words? We tested 13 levels. Each is categorical — below the threshold, that type of thinking is **absent**, not just weaker.

| Level | Prompt Size | What the Model Does | Hit Rate |
|-------|-------------|--------------------| ---------|
| **12-13** | ~332 words | Derives trade-offs, then finds the law about those trade-offs, then diagnoses its own framework | 14/14 |
| **10-11** | ~165-247 words | Maps the design space: what's impossible, what's conserved, what can't coexist | 97% |
| **8-9** | ~105-130 words | Builds improvements, watches them break, finds what construction reveals | 97% |
| **7** | ~92 words | Names how the input hides its real problems | 96% |
| **5-6** | 45-92 words | Multiple voices argue about the input | — |
| **1-4** | 3-30 words | Basic single operations | — |

**The key insight:** Levels 7 and below require a smart model (Haiku fails 0/3). Level 8 and above require the model to *build something and observe what happens* — any model can do that (Haiku succeeds 4/4). Construction bypasses the intelligence gate.

The production prisms in this repo operate at Level 8-12. The default L12 prism is the full stack: claim → attack → construct → observe → derive trade-off → derive the law about that trade-off.

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

**Cost:** Single prism (~$0.05). Full prism (9 calls, ~$0.50). Under a dollar total. Add `-m haiku` for ~5x cheaper.

### On Competition Math (AIME 2025, Experimental)

| Method | Problems | Solved |
|--------|----------|--------|
| Haiku vanilla | 16 | 13 (81%) |
| Haiku + cooked prism | 3 failures | 3/3 recovered |

The cooker generates a custom prism for the problem type. Haiku already knows the math — it just needs the right question.

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

**Code generation:** Prisms find hidden structure in existing code — they don't help write new code. A separate codegen prism exists (`prisms/codegen.md`: decompose → design API → predict bugs → implement), but analysis and generation are fundamentally different tasks. Don't expect `/scan` to make your model write better functions.

**Large real-world codebases:** Tested on files up to 2,684 lines (Rich console.py scored 10.0 — highest in any test). L12 actually benefits from more code — richer conservation laws, more bugs found (28 on Rich vs 15 on 300-line files). The Full pipeline's 7 prisms may converge on the same dominant pattern on simpler files. For distinct findings on any size, run specific standalone prisms (security, temporal, API) instead.

**Math problems:** Full prism (multi-step pipeline) did NOT help on AIME — single prism worked better. Too many pipeline steps dilute focus on competition problems.

**Other models:** Gemini 2.5 Flash produces the same kind of structural analysis from the same prisms — the technique transfers across model families. GPT/Llama untested. Prism wording was tuned on Claude; if you test elsewhere, open an issue with results.

---

## FAQ

**Is this just prompt engineering?** "Write a detailed analysis" is prompt engineering. "Make a claim. Attack it. Build an improvement. Watch what breaks. Derive the trade-off you can never escape." is a program. The model runs the program. The difference is categorical — vanilla produces observations, prisms produce structural laws.

**Why does construction outperform reasoning?** Reasoning about reasoning requires a smart model. Building something and watching what happens doesn't. That's why construction works on Haiku — and why the cheapest model with a prism beats the most expensive model without one.

**Does it work on other models?** Gemini 2.5 Flash produces the same kind of output from the same prisms. GPT/Llama untested. If you test elsewhere, share results.

**What's the catch?** Single-researcher project. All depth scores are AI-evaluated, not human-scored or peer-reviewed. Sample sizes are small (3-30 per finding). Raw outputs are in `output/` for independent verification.

---

## Project Structure

```
prism.py              Interactive REPL + CLI tool (~11,200 lines)
prisms/               48 prisms: 11 champions + gap detection + oracle + strategist + variants
prompts/              80+ research prisms (L4-L13) + paper prompts + gap extraction
research/             Experiment scripts, benchmarks, 30 literature reviews
output/               1,000+ raw experiment outputs
experiment_log.md     Research log (Rounds 1-41)
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

- Human evaluation of output quality (currently AI-evaluated only)
- Formal derivation of the specificity-verifiability trade-off
- AgentsKB integration for automatic gap filling
- GPT-4o, Llama testing (Gemini 2.5 Flash + Hermes 3 confirmed working)

Want to help? Test on other models, run `--trust` on your code and report what it finds, open PRs with results.

---

## License

MIT. Use the prompts however you want.

---

Clone the repo. Run `/scan` on your hardest code. The prisms are MIT licensed — use them anywhere.
