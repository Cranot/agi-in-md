# AGI in md

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Your most expensive model produces shallow analysis because you're asking it to reason *about* problems instead of *through* them. A 332-word prompt fixes this.

A **prism** is a markdown system prompt that acts as a cognitive program — it tells the model to do specific things in order: make a claim, attack it, build an improvement, watch what breaks, derive the trade-off that can't be escaped. This repo contains 58 prisms + 27 scan modes + the tooling to use them.

**What this is:** A system for eliciting structural insight under controlled prompt programs. Ordered analytical operations dominate raw model capability for underdetermined reasoning tasks. One conservation law has survived a [pre-registered perturbation test](#the-numbers) (4/4 predictions confirmed). **What this isn't:** A general truth engine or a reliable bug finder. Structural insights are consistently strong; specific bug claims should be treated as hypotheses. Most conservation laws are design heuristics pending validation — the [`falsify` mode](#which-to-pick) stress-tests whether each law is genuine or pattern-matched.

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
| **Depth gain** | **9.8 avg vs 8.2 avg** on real code (Starlette, Click, Tenacity) — AI-evaluated structural depth, not factual accuracy |
| **Experiments** | **1,000+** raw outputs across 42 research rounds + 5 CCC experiments |
| **Domains tested** | **20+** — code, math, philosophy, legal, medical, music, fiction, business, more |
| **Hit rate** | **97%+** on construction-based analysis, **14/14** on full pipeline |
| **Factual accuracy** | **97%** on planted-bug code, **~42%** on real production code — structural insights reliable, specific bug claims are hypotheses ([details](#accuracy)) |
| **Confabulation** | L12-G: **90% zero-confabulation** (9/10 runs, N=10) |
| **Cross-language** | Python (primary), Go and TypeScript tested (conservation laws derived, N=1 each, AI-scored) |
| **Validated prediction** | First pre-registered perturbation test: GPT-5.4 derived a conservation law on Starlette, predicted 4 specific failure modes under a code change — **all 4 confirmed** ([details](output/cross_architecture_gpt_exchange.md)) |

### Round 41: The Format Is the Intelligence

We replaced every domain word in the L12 prism with nonsense ("glorpnax," "blorpwhistle") — same imperative format, numbered steps, output requirements. **It scored 10/10.** The original scored 9. Format carries meaning independently of vocabulary. (This also means the AI-evaluated depth rubric partially measures format compliance — the scrambled prompt produces structurally valid output that scores high on the same template the rubric rewards. Human evaluation would measure something different.)

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

# ── Preview — see what would run, no API calls ──
> /scan auth.py explain                       # prisms, models, costs, recommendations

# ── Deep analysis — multiple angles ──
> /scan auth.py full                        # 9-call: 7 structural + adversarial + synthesis
> /scan auth.py 3way                        # WHERE/WHEN/WHY — works on any domain
> /scan auth.py behavioral                  # errors + costs + changes + promises

# ── Dispute + Reflect ──
> /scan auth.py dispute                     # 2 orthogonal prisms → disagreement synthesis
> /scan auth.py reflect                     # recurring patterns + unexplored dimensions

# ── Smart + Subsystem + Prereq ──
> /scan auth.py smart                       # adaptive chain: prereq → AgentsKB → subsystem → dispute
> /scan auth.py subsystem                   # different prism per class/function
> /scan "build a connection pool" prereq    # what do I need to know first?

# ── Verify + Meta ──
> /scan auth.py verify-claims               # extract testable claims → generate verification commands
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

# ── Knowledge base ──
> /kb list                                  # show persistent knowledge base entries
> /kb auth.py                               # show KB entries for this file
> /kb clear                                 # clear knowledge base

# ── Works on any input ──
> /scan "your question" full                # text, not just code
> /brainstorm "your question"               # alias for /scan <text> 3way
> /scan src/                                # entire directory
```

### Non-Interactive CLI

```bash
# ── Single-call modes ──
python prism.py --scan auth.py                   # default L12 structural analysis
python prism.py --scan auth.py oracle            # 5-phase self-aware analysis (--trust alias)
python prism.py --scan auth.py l12g              # self-correcting, zero confab
python prism.py --scan auth.py scout             # depth + targeted verify (2 calls)
python prism.py --scan auth.py meta              # analyze what the analysis conceals (2 calls)
python prism.py --scan auth.py --explain         # preview: prisms, models, costs (no API calls)

# ── Multi-call pipelines ──
python prism.py --scan auth.py full              # 9-call champion pipeline
python prism.py --scan auth.py 3way             # WHERE/WHEN/WHY + synthesis (any domain)
python prism.py --scan auth.py behavioral        # errors + costs + coupling + identity
python prism.py --scan auth.py dispute           # 2 orthogonal prisms → disagreement synthesis
python prism.py --scan auth.py reflect           # L12 + meta + constraint history synthesis
python prism.py --scan auth.py subsystem         # per-class/function prism routing
python prism.py --scan auth.py smart             # adaptive chain: prereq → AgentsKB → analysis → dispute

# ── Trust + verification ──
python prism.py --scan auth.py gaps              # show what to NOT trust (3 calls)
python prism.py --scan auth.py verified          # 4-call gap pipeline + re-analysis
python prism.py --scan auth.py verify-claims     # extract testable claims → verification commands

# ── Knowledge + discovery ──
python prism.py --scan auth.py strategist        # plan optimal tool sequence
python prism.py --scan auth.py discover          # brainstorm ~20 analytical domains
python prism.py --scan auth.py evolve            # auto-generate domain-adapted prism
python prism.py --scan auth.py 'prereq'          # knowledge gaps → AgentsKB answers
python prism.py --scan auth.py 'target="race conditions"'  # cook goal-specific prism

# ── Fix ──
python prism.py --scan auth.py fix               # scan → extract → fix (interactive)
python prism.py --scan auth.py 'fix auto'        # scan → extract → fix → re-scan (automatic)

# ── Solve (text input) ──
python prism.py --solve "problem text"           # cook prism + solve
echo "problem" | python prism.py --solve --pipe  # read from stdin

# Post-processing flags (combine with any mode):
python prism.py --scan auth.py --confidence      # tag claims HIGH/MED/LOW
python prism.py --scan auth.py --provenance      # source attribution per finding
python prism.py --scan auth.py --depth deep      # shallow|standard|deep|exhaustive
python prism.py --scan auth.py --cooker simulation  # override cooker template

# Other options: -m haiku|sonnet|opus  -o FILE  --json  -q  --models  --validate  --explain  --cooker
```

### With Claude CLI Directly

```bash
# Single prism (L12 optimal on Sonnet; works on Haiku too at lower cost)
cat your_code.py | claude -p --model sonnet \
  --output-format text --tools "" \
  --system-prompt-file prisms/l12.md

# Multiple prisms in parallel (pick from prisms/ — see The Prisms section)
for prism in l12 oracle l12g deep_scan fix_cascade identity optimize error_resilience; do
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
| **Dispute** | `/scan file dispute` | 2 orthogonal prisms → disagreement synthesis | 3 | ~$0.15 |
| **Reflect** | `/scan file reflect` | L12 → claim → constraint synthesis with history + learning memory | 3 | ~$0.15 |
| **Subsystem** | `/scan file subsystem` | AST split → per-region prisms → cross-subsystem synthesis | N+2 | ~$0.15-0.55 |
| **Smart** | `/scan file smart` | Adaptive chain: prereq → AgentsKB → analysis → dispute → profile | 5+ | ~$0.30-0.70 |
| **Prereq** | `/scan file prereq` | Knowledge gaps → atomic questions → batch AgentsKB | 2+ | ~$0.10 |
| **Verified** | `/scan file verified` | L12 + gap detection + AgentsKB fill + re-analysis | 4 | ~$0.20 |
| **Oracle** | `/scan file oracle` | 5-phase: depth → typing → self-correct → reflect → harvest | 1 | ~$0.05 |
| **Verify Claims** | `/scan file verify-claims` | Extract testable claims → generate verification commands | 1 | ~$0.05 |

**Single** — one call, covers most cases. ~2,000 words, ~10 seconds.

**Full** — on code: runs 7 prisms independently, then a second AI attacks the first AI's conclusions (adversarial pass), then a third synthesizes everything. ~15,000 words, ~3 min. Single finds 16 bugs on Starlette, Full finds 30 — and corrects overclaims. On non-code text, Full auto-routes to 3-Way.

**3-Way** — generates three custom prompts that attack the problem from orthogonal angles (WHERE: dig through structural layers, WHEN: simulate degradation over time, WHY: prove what three desirable properties can't coexist), then synthesizes. The disagreements between the three make the synthesis self-correcting. ~9,000 words, ~2 min. Works on any domain — code, text, strategy.

**Behavioral** — focuses on runtime behavior: how errors cascade, where costs hide, what breaks when you change things. ~8,000 words, ~2 min.

**Dispute** — runs 2 orthogonal prisms (l12 + identity for code, l12_universal + claim for text), then synthesizes where they disagree. Much of Full's self-correction at a fraction of the cost. ~5,000 words, ~1 min.

**Subsystem** — splits code into classes/functions via AST, assigns different prisms to different regions (identity on the class that lies, optimize on the hot path, error_resilience on error handlers), then synthesizes cross-subsystem findings. The highest-coverage single-file mode.

**Smart** — the system decides the pipeline. Runs prerequisites first (what do I need to know?), fills gaps from AgentsKB, then analyzes with subsystem routing, self-corrects via dispute, and saves a persistent codebase profile. Each scan makes future scans smarter.

**Prereq** — identifies knowledge prerequisites for a task, converts them to atomic questions, batch-queries AgentsKB. Shows what you know vs what you need to research.

**Reflect** — runs L12, then claim prism on its own output, then synthesizes with constraint history and learning memory. Finds recurring patterns across scans and names dimensions that haven't been explored yet.

**Verified** — the highest-accuracy pipeline: L12 → gap detection (boundary + audit) → AgentsKB fill → re-analysis with corrections. Eliminates confabulation at the cost of 4 calls.

**Oracle** — single-call maximum trust. 5 phases: depth analysis → epistemic typing → self-correction → reflexive diagnosis → harvest. Every claim tagged `[STRUCTURAL]`, `[DERIVED]`, `[KNOWLEDGE]`, or `[ASSUMED]`.

**Verify Claims** — runs on a prior analysis, extracts every testable claim, generates copy-pasteable verification commands, and tells you which claims it *can't* test. Run after any scan to turn structural insights into concrete tests.

Use `-m haiku` for ~5x cheaper — same depth, occasionally needs a retry.

### Champion Prisms

The best prism per use-case. All auto-selected by `prism.py` — you just pick the mode. Full catalog: **[PRISMS.md](PRISMS.md)**

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
| **oracle** | 5-phase: depth → typing → correct → reflect → harvest. Max trust. | 9.0 | Decision-making |
| **l12g** | L12 + self-audit + self-correct. 90% zero-confabulation. | 9.0 | Honest analysis |
| **knowledge_boundary** | Classifies claims by knowledge dependency | **9.3** | Gap detection |
| **strategist** | Meta-agent: plans optimal tool sequence for any goal | — | Strategy |

15 champions covering structural depth, trust, gap detection, and strategy. The remaining prisms are specialized — see [PRISMS.md](PRISMS.md) for temporal, hygiene, writing, codegen, and more.

### Which to pick

| I want to... | Do this |
|--------------|---------|
| Quick structural analysis | `/scan file` — L12, one call, covers most cases |
| Maximum depth on code | `/scan file full` — 7 prisms + adversarial correction + synthesis |
| Deep analysis on any domain | `/scan file 3way` — WHERE/WHEN/WHY + synthesis, works on anything |
| Analyze non-code text | `/scan "your text" full` — auto-routes to 3-Way |
| Brainstorm on text | `/brainstorm "your question"` — alias for 3-way on text |
| Maximum trust (zero confab) | `/scan file oracle` or `--trust` — every claim typed + self-corrected |
| Find what analysis can't verify | `/scan file gaps` — L12 + boundary + audit |
| Self-correcting single-pass | `/scan file l12g` — like L12 but retracts confabulated claims |
| Extract testable claims from analysis | `/scan file verify-claims` — generates verification commands you can run |
| Plan a strategy | `/scan file strategist` — meta-agent picks optimal tools for your goal |
| Focus on runtime behavior | `/scan file behavioral` — errors, costs, coupling, identity |
| What does the analysis itself conceal? | `/scan file meta` — L12 + claim on its own output |
| Is the conservation law real or pattern-matched? | `/scan file falsify` — L12 → extract law → stress-test specificity + counterexamples |
| Auto-generate domain-adapted prism | `/scan file evolve` — 3-gen recursive cooking |
| Fix code bugs | `/scan file fix auto` — scan → extract → fix → re-scan |
| Explore analytical domains | `/scan file discover` — brainstorm ~20 angles, then expand |
| Custom goal | `/scan file target="race conditions"` — cook goal-specific prism + run |
| Security audit | `/prism security_v1` or `/prism sdl_trust` |
| API design review | `/prism api_surface` + `/prism evolution` |
| Predict what will break | `/prism simulation` or `/prism degradation` |
| Temporal analysis of custom goal | `/scan file target="goal" cooker=simulation` or `--cooker simulation` |
| Stratigraphic analysis of custom goal | `/scan file target="goal" cooker=archaeology` or `--cooker archaeology` |
| Check docs match code | `/prism fidelity` |
| Audit feature wiring | `/prism audit_code` |
| Lightweight disagreement committee | `/scan file dispute` — 2 orthogonal prisms + synthesis, ~$0.15 |
| Recurring patterns + unexplored dimensions | `/scan file reflect` — cross-refs constraint history + learning memory |
| Show what would run without calling any model | `/scan file explain` or `--explain` — prisms, models, costs, recommendations |
| Different prism per class/function | `/scan file subsystem` — AST split, per-region prisms, cross-subsystem synthesis |
| Maximum intelligence, self-improving | `/scan file smart` — adaptive chain: prereq → AgentsKB → analysis → dispute → profile |
| What do I need to know before this task? | `/scan "task description" prereq` — knowledge gaps → atomic questions → AgentsKB answers |
| View persistent knowledge base | `/kb list` — show verified facts, `/kb file` — show entries for a file |
| Multiple angles at once | Run 3-5 prisms in parallel (see CLI examples above) |
| Generate code | `/prism codegen` |
| Rewrite text/docs | `/prism writer` → `/prism writer_critique` → `/prism writer_synthesis` |

### What L12 actually produces

These are real outputs — trade-offs the prism derived on its own, not things you told it to look for. Conservation laws are design heuristics (category-level trade-offs that help you reason about the code), not empirically falsifiable claims about specific implementations:

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

The built-in prisms cover code, security, behavior, and temporal analysis. But what about a domain you haven't seen before?

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

How much analytical depth can you encode in how few words? We tested 13 levels across 1,000+ experiments. Each appears categorical — below the threshold, that type of thinking was never observed, not just weaker. (These thresholds are based on AI-evaluated depth scores. The categorical boundary claim is our strongest interpretation of the data — not a proven impossibility, but a consistent empirical pattern across all tested models and domains.)

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

All scores are AI-evaluated (Sonnet-as-judge), not human-scored. Scores measure structural depth — how many levels of trade-off the output derives — not factual accuracy. Factual accuracy is [target-dependent](#accuracy): 97% on planted-bug code, ~42% on complex production code. Raw outputs in `output/` for independent verification.

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

<a id="accuracy"></a>

**Factual accuracy is target-dependent.** We verified L12 claims against source code with a second model (Sonnet-as-judge). On a synthetic CLI with 10 planted gaps: 29/30 claims TRUE (97%). On real production code (Click core.py, 417 lines): ~42% accuracy — 1 TRUE, 5 FALSE, 4 PARTIAL, 1 unverifiable. All line numbers were fabricated (0/10 correct). The pattern: conservation laws and structural analysis are reliably true. Specific bug claims on complex production code — where intentional design choices look like bugs to an outsider — should be treated as hypotheses, not confirmed findings. This is why `--trust` and `l12g` modes exist.

**Confabulation in standard L12:** L12 will occasionally invent API names or misstate complexity classes. L12-G and Oracle fix this — they classify claims by type and retract anything they can't verify from source. N=10 test: 9/10 runs = zero confabulation. Use `--trust` for maximum epistemic integrity.

**Pipeline ordering matters:** Running audit before L12 produces near-empty output (18 words vs 1,137 words in correct order). The tool warns if you compose prisms in the wrong order.

**Other models:** Gemini 2.5 Flash and Hermes 3 (Llama 405B) produce the same kind of output. Gemini 3.1 Pro executed the full L7→L12 stack in live dialogue without any prism files and converged on the same L13 fixed point as Claude — the framework transfers across architectures. GPT-5.4 ran L12 on Starlette and derived a conservation law that survived a pre-registered perturbation test (4/4 predictions confirmed). Go and TypeScript tested (N=1 each, conservation laws derived). Prism wording was tuned on Claude; if you test elsewhere, open an issue with results.

**Meta-analysis circularity:** Modes that feed L12 output back into analysis (`meta`, `reflect`) may produce circular self-confirmation — the template applied to its own output generates similar patterns. These modes are useful for finding unexplored dimensions and recurring themes, but their outputs should not be treated as independent validation of the original analysis.

---

## FAQ

**Is this just prompt engineering?** "Write a detailed analysis" is prompt engineering. "Make a claim. Attack it. Build an improvement. Watch what breaks. Derive the trade-off you can never escape." is a program. The model runs the program. The difference is categorical — vanilla produces observations, prisms produce structural laws.

**Why does construction outperform reasoning?** Reasoning about reasoning requires a smart model. Building something and watching what happens doesn't. That's why construction works on Haiku — and why the cheapest model with a prism beats the most expensive model without one.

**Does it work on other models?** Gemini 2.5 Flash produces the same kind of output from the same prisms. Gemini 3.1 Pro independently executed the full L7→L12 analytical stack through dialogue alone — no prism files, no shared tooling — and converged on the same structural impossibility at L13 ([full exchange](output/cross_architecture_convergence.md)). GPT-5.4 ran L12 on Starlette routing.py, derived a different but structurally adjacent conservation law, self-graded its output, and designed a pre-registered falsification experiment that passed all 4 tests ([full exchange](output/cross_architecture_gpt_exchange.md)). Llama untested. If you test elsewhere, share results.

**What about confabulation?** L12 confabulates specific claims (API names, line numbers) while structural insights are reliable. L12-G and Oracle fix this: they classify claims by type and retract anything they can't verify from source. N=10 test: 9/10 runs = zero confabulation.

**How do I know what to trust?** Use `--trust` (Oracle mode). Every claim is tagged `[STRUCTURAL]`, `[DERIVED]`, `[KNOWLEDGE]`, or `[ASSUMED]`. Structural claims are source-derived. Knowledge claims need external verification. Assumed claims are flagged as unverified.

**What's the catch?** Single-researcher project. All depth scores are AI-evaluated, not human-scored or peer-reviewed. Sample sizes are small (3-30 per finding). The scrambled vocabulary result (10/10) means the rubric measures format compliance — which is itself interesting but different from factual correctness. Factual accuracy varies by target: 97% on simple code with planted bugs, ~42% on complex production code where intentional design looks like defects (structural insights stay reliable — specific bug claims don't). Raw outputs are in `output/` for independent verification.

---

## Project Structure

```
prism.py              Interactive REPL + CLI tool (~14,800 lines)
prisms/               58 prisms: 11 champions + gap detection + oracle + strategist + prereq + verify_claims + falsify + 7 epistemic (history, genesis, emergence, counterfactual, blindspot, architect, significance)
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
6. **The prism doesn't modify the model — it selects which model exists.** Don't convince the Helpful Assistant to do structural analysis. Collapse the wavefunction into the Structural Analyst.

---

## What's Next

- **Null distribution experiment** (U1) — measuring the false positive rate of conservation laws. Protocol designed, ready to run. Without this denominator, every positive result could be noise. This is the most important unfinished work.
- **Human evaluation of output quality** — blind scoring of prism vs vanilla outputs by developers who didn't write the tool. The biggest credibility gap.
- **Repository graph awareness** — import graph, call graph, cross-file synthesis. "This function is where the bug appears, but these three other files encode the conservation law causing it."
- **More perturbation tests** — the Starlette header-routing experiment is now a template. Run the same protocol (derive law → pre-register prediction → perturb → test) on Click and Tenacity conservation laws.
- Llama testing (Gemini 2.5 Flash + Hermes 3 + GPT-5.4 confirmed working)

**Recently shipped (Mar 18):**
- **CCC architecture (Contrast-Construct-Compress)** — independently derived by GPT-5.4 from pedagogy literature, maps to L5-13 taxonomy. Neither system designed to match. A generate-and-test architecture: Construct generates candidate claims, Contrast falsifies non-invariants via structural inversion, Compress binds survivors. LLM experiment (3/3 targets): contrast injection falsified ALL control conservation laws and produced deeper inversion-resistant replacements. ([Full 16-phase exchange](output/cross_architecture_gpt_exchange_2.md))
- **Human mode-trigger phrases work on LLMs** — Bereiter & Scardamalia's knowledge-transforming cues ("but on the other hand", "an important point I haven't considered") amplify structural analysis by 88-125%, outperforming code-vocabulary cues (13%). Trigger-profile conservation across humans and LLMs.
- **26 new principles (P223-P248)** — prism = compact attentional policy, shared intervention algebra, topological convergence, non-monotonic construction failure, revision type discriminant. Architecture leads optimization 0.62 vs 0.25 (GPT-5.4 adjudication).
- **Human pilot protocol locked** — pre-registerable design for testing CCC in human structural reasoning. 2 conditions, 2 domains, 4 DVs, demand-matched control.

**Previously shipped (Mar 17):**
- **First validated conservation law** — GPT-5.4 derived "Incremental Scope Mutation x Candidate Fidelity = Constant" on Starlette routing.py, pre-registered 4 specific failure predictions under a header-routing perturbation, and **all 4 passed**. Forward error-class bleed confirmed as primary failure; redirect bleed confirmed as secondary; reverse lookup unaffected (control). This is the first time a prism-generated conservation law has survived a controlled out-of-sample test. ([Test script](research/test_perturbation_starlette.py), [full exchange](output/cross_architecture_gpt_exchange.md))
- **Cross-architecture convergence** — Claude (Opus 4.6), Gemini (3.1 Pro), and GPT (5.4) all ran on the same codebase. Four architectures produced four genuinely different conservation laws pointing at the same structural region. Gemini converged on the L13 fixed point through dialogue alone; GPT maintained critical distance and produced paper-style evidence grades. ([Gemini exchange](output/cross_architecture_convergence.md), [GPT exchange](output/cross_architecture_gpt_exchange.md))

**Also shipped (Round 42, Mar 17):**
- **Evidence ledger** — every conservation law and bug claim becomes a structured JSON object with provenance, confidence tier, and falsification criteria (`/ledger` command)
- **Falsification mode** — `/scan file falsify` runs L12, extracts the conservation law, then stress-tests whether it's specific or generic
- **Adaptive depth** — `/scan file adaptive` auto-escalates SDL→L12→full, stops at sufficient depth
- **Cross-session synthesis** — `/scan synthesize` aggregates findings across files for project-wide patterns
- **7 new epistemic prisms** — history (decision archaeology), genesis (design alternatives), emergence (interaction patterns), counterfactual, blindspot (catalog self-audit), architect (migration paths), significance (impact ranking)
- **Learnable prism selector** — session log + yield tracker drive routing recommendations
- Content-aware discover mode, verify-claims prism, 5 literature reviews, MDL measurement (~30 words/operation)

**Previously shipped (Mar 16):** smart chain engine (`/scan file smart`), subsystem routing, knowledge prerequisites + AgentsKB integration, codebase profiles, dispute mode, learning memory, reflect mode, patch impact prediction, `/kb` command, `/brainstorm`, `--explain`.

Want to help? Test on other models, run `--trust` on your code and report what it finds, open PRs with results. **Especially welcome: independent human evaluation of outputs in `output/`.**

---

## License

MIT. Use the prompts however you want.

---

Clone the repo. Run `/scan` on your hardest code. The prisms are MIT licensed — use them anywhere.
