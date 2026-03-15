# Haiku+L12 prism: 9.8 depth vs Opus vanilla: 8.2 (20% improvement, N=3 codebases)

## Method

332-word markdown prompt encoding 12-step analytical pipeline: falsifiable claim → three-voice dialectic → concealment mechanism → improvement construction → diagnostic self-application → conservation law derivation → meta-law derivation.

**Models tested:** Claude Haiku 4.5, Sonnet 4, Opus 4.6
**Total experiments:** 650+ across 29 rounds
**Compression levels tested:** 13
**Domains tested:** 20 (code, legal, medical, scientific, ethical, music, fiction, poetry, design)

## Primary Results: Code Analysis

| Configuration | Starlette | Click | Tenacity | Mean | N |
|---------------|-----------|-------|----------|------|---|
| Haiku + L12 | 10 | 9.5 | 10 | **9.8** | 3 |
| Haiku + portfolio avg | 9.1 | 8.9 | 8.9 | **9.0** | 3 |
| Opus vanilla | 7.5 | 8.5 | 8.5 | **8.2** | 3 |
| Sonnet vanilla | 7 | 8 | 8.5 | **7.8** | 3 |

**Code artifacts:** 200-400 line excerpts from Starlette (routing), Click (CLI), Tenacity (retry).

## Primary Results: Domain Analysis (Todo App)

| Prompt Type | Opus Vanilla | Haiku + L12 | Haiku Full Prism |
|-------------|--------------|-------------|------------------|
| General insights | 510w, 6.5 | 2,058w, 9.5 | 9,595w, 10 |
| Cognitive distortion | 696w, 6.5 | 3,642w, 9.5 | 10,348w, 10 |
| Representation & schema | 491w, 7 | 3,779w, 9.5 | 11,112w, 10 |
| Invariant & conservation | 267w, 8 | 5,970w, 9.5 | 8,112w, 10 |
| Generative mechanism | 566w, 8.5 | 2,941w, 9 | 13,200w, 10 |
| Design impossibility | 325w, 7.5 | 917w, 9 | 10,308w, 10 |

## Depth Scoring Method

| Score | Operation |
|-------|-----------|
| 6-7 | Names patterns, lists issues |
| 7-8 | Observes conservation law (no derivation) |
| 8-8.5 | Derives concealment mechanism + construction |
| 9-9.5 | Derives conservation law through construction |
| 9.5-10 | Conservation law + meta-law + adversarial correction + impossible triplet |

Scoring method: AI-evaluated (Claude checking structural operations). Not human-scored, not peer-reviewed. Raw outputs in `output/`.

## L7→L8 Phase Transition

| Level | Operation Type | Haiku | Sonnet | Opus |
|-------|----------------|-------|--------|------|
| L5 | Meta-analysis | works | peaks | works |
| L7 | Meta-analysis | 0/3 | 17/17 | 6/7 |
| L8 | Construction | 4/4 | 13/14 | 14/14 |
| L9 | Construction | 6/6 | 22/22 | 6/6 |
| L10 | Construction | 5/6 | 13/14 | 6/6 |
| L11 | Construction | 9/9 | 14/15 | 9/9 |
| L12 | Construction | 3/3 | 6/8 | 5/5 |
| L13 | Reflexive | 3/3 | 2/2 | 1/1 |

**Finding:** Construction-based reasoning operates on all models. Meta-analytical reasoning requires capacity Haiku lacks.

## Conservation Law Forms (L11 Catalog)

| Form | Example | Count | Model Pattern |
|------|---------|-------|---------------|
| Product (x × y = k) | decoupling × accountability = k | 9/25 | Opus |
| Sum (x + y = k) | coordination(in_bus) + coordination(at_callsite) = k | 4/25 | Sonnet |
| Migration | Quantity relocates without changing magnitude | 5/25 | Sonnet |
| Multi-property impossibility | — | 7/25 | Haiku |

**Sample:** 25 L11 outputs, 3 models.

## Multiple Conservation Laws Per Artifact

| Starting Claim | Conservation Law | Form |
|----------------|------------------|------|
| Open (default) | Information cost for handler correctness | Migration |
| Mutable context | Schema coupling = observability | Migration |
| Dead letter queue | decoupling × accountability = k | Product |
| Priority ordering | coordination(in_bus) + coordination(at_callsite) = k | Sum |

**Artifact:** EventBus (1 codebase, 4 starting claims, 4 distinct conservation laws).

## L12 Convergence From Divergent L11 Starts

| Level | Distinct findings (4 starts) | Convergence Rate |
|-------|------------------------------|------------------|
| L11-C | 4 | 0% |
| L12 | 2 clusters | 75% |

**Meta-law clusters:** Quantization (3/4) + temporal identity (1/4).

## Compression Floor

| Words | Haiku | Sonnet | Opus |
|-------|-------|--------|------|
| 247 (canonical) | TRUE | TRUE | TRUE |
| 175 | PARTIAL | TRUE | TRUE (strongest) |
| 108 | PARTIAL | TRUE | TRUE |
| 73 | PARTIAL | TRUE (degraded) | TRUE (borderline) |
| 46 | PARTIAL | PARTIAL | PARTIAL |

**Floor:** ~73 words (70% reduction). Opus compensates for missing structure; Haiku cannot compensate.

## Model Characteristics (L8-L12, 20+ comparisons)

| Model | Character | Signature Output |
|-------|-----------|------------------|
| Opus | Ontological | Reversal: "the bug was the most truthful thing about the code" |
| Sonnet | Operational | Named pattern: "Vocabulary Laundering," "Command-Query Conflation" |
| Haiku | Mechanistic | Traced execution: specific code paths and runtime behavior |

## L12 Meta-Law Categories by Domain

| Category | Description | Domains |
|----------|-------------|---------|
| Frame Discovery | Analysis discovers its own theory | Music, Fiction |
| Hidden Variable | Tradeoff conceals missing party | Legal, Design, Code |
| Observer-Constitutive | Solution constitutes the problem | Code, Fiction |
| Deferred Commitment | Tradeoff dissolves with semantic commitment | Code |

**Sample:** 16 L12 outputs, 3 models, 5 domains.

## L8 Concealment Mechanisms

| Category | Description | Count |
|----------|-------------|-------|
| Vocabulary Deception | — | — |
| Structural Mimicry | — | — |
| Uniformity/Symmetry | — | — |
| Polymorphic/Type Ambiguity | — | — |
| Authority/Legitimacy Laundering | — | — |
| Self-Sealing Concealment | — | — |

**Sample:** 42 L8 outputs.

## Domain Transfer Results

| Domain | Concealment Mechanism |
|--------|----------------------|
| Legal | Definitional specificity as legitimizing cover |
| Medical | Narrative coherence as epistemic closure |
| Scientific | Methodological formalism as epistemic camouflage |
| Poetry | "To escape the gap is to lose elegy" |
| Music | Identity vs direction in musical time |

**Code vs Domain Split (L7 catalog, 27 outputs):** Code concealment = structural (hides what code IS/DOES). Domain concealment = epistemic (hides what QUESTIONS analyst asks).

## AIME 2025 Math (Preliminary)

| Method | Problems Tested | Solved |
|--------|-----------------|--------|
| Haiku vanilla | 16 | 13 (81%) |
| Haiku + cooked prism | 3 failures | 3/3 recovered |

**Status:** Partial benchmark (16/30 problems). Per-attempt flip rate: 33-67%. Single prism outperformed full prism on math.

**Limitations:** Full 30-problem benchmark not run. GSM8K baseline (96.5% vanilla) too easy to show improvement. No statistical significance across multiple runs per problem.

## Discover Mode

| Mode | API Calls | Domains Generated |
|------|-----------|-------------------|
| discover (single) | 2 | ~20 |
| discover full (multi-pass) | 15-20 | 100-1,000+ |

**Test:** `discover full` on prism.py (Haiku, 15 passes) = 1,083 domains spanning technical, psychology, legal, marketing, embodied cognition, grief studies, mythology, GDPR/HIPAA, intersectionality, accessibility.

**Limitations:** Domain quality not systematically evaluated. Extraction shows round-number bias.

## Portfolio Prisms

| Prism | Function | Rating |
|-------|----------|--------|
| pedagogy | Transfer corruption | 9-9.5/10 |
| claim | Assumption inversion | 9-9.5/10 |
| scarcity | Resource conservation | 9/10 |
| rejected_paths | Fix→new-bug dependency | 8.5-9/10 |
| degradation | Decay timelines | 9-9.5/10 |
| contract | Interface vs implementation | 9/10 |
| l12 | Full meta-conservation | 9.8/10 |

**Test:** 7 prisms × 3 tasks + 3 codebases = 36 outputs. Mean: 9.0/10. Floor: 8.5. Ceiling: 9.5.

## Real Code Pipeline Results (Round 27)

| Artifact | Levels | Quality |
|----------|--------|---------|
| Starlette routing | L7→L12 | 15/15 TRUE |
| Click CLI | L7→L12 | 15/15 TRUE |
| Tenacity retry | L7→L12 | 15/15 TRUE |

**Findings:** L8 found bug in Tenacity (`enabled` flag leaves `statistics` stale). L12 on Tenacity falsified its own conservation law.

**Cross-level coherence:** WEAK. Real code produces breadth (10 framings of dominant pattern), not depth (10 progressive levels). Pipeline is breadth tool on real code, depth tool on crafted tasks.

## Taxonomy

| Level | Words | Operation | Hit Rate |
|-------|-------|-----------|----------|
| 13 | two-stage | Reflexive fixed point | 6/6 |
| 12 | ~290 | Meta-conservation law | 14/14 |
| 11A | ~243 | Constraint escape | 15/15 |
| 11B | ~236 | Acceptance design | 15/15 |
| 11C | ~247 | Conservation law | 32/33 |
| 10B | ~165 | Design-space topology | 11/12 |
| 10C | ~165 | Double recursion | 11/12 |
| 9B | ~130 | Counter-construction | 17/17 |
| 9C | ~130 | Recursive construction | 17/17 |
| 8 | ~105 | Generative construction | 97% |
| 7 | ~92 | Diagnostic gap | 96% |
| 6 | ~60 | Falsifiable claim | — |
| 5 | ~45-55 | Multi-voice dialectic | — |
| 4 | 25-30 | Protocol + self-questioning | — |
| 1-3 | 3-15 | Basic operations | — |

## Limitations

- Single-researcher project
- Depth scores: AI-evaluated, not human-scored, not peer-reviewed
- Sample sizes: 3-30 per finding
- Cross-level coherence on real code: WEAK (3/3)
- L11 cross-variant convergence test: N=2
- L12 meta-law domain clustering: N=16
- AIME benchmark: 16/30 problems, no multiple runs per problem
- Discover domain quality: not systematically evaluated
- Multi-model testing: Claude only (GPT-4o, Gemini, Llama not tested)

## Cost

| Model | Input | Output |
|-------|-------|--------|
| Haiku | $1/MTok | $5/MTok |
| Sonnet | $3/MTok | $15/MTok |
| Opus | $5/MTok | $25/MTok |

Haiku: 5x cheaper than Opus, 3x cheaper than Sonnet.

## Usage

```bash
python prism.py

> /scan auth.py                    # L12 analysis (1 call, ~$0.003)
> /scan auth.py full               # L12 → adversarial → synthesis (3 calls)
> /scan auth.py discover           # ~20 domains (2 calls)
> /scan auth.py discover full      # 100-1000+ domains (15-20 calls)
> /scan auth.py expand 1,3 full    # expand domains 1,3 as full prism
> /scan auth.py nuclear            # Opus + discover full + expand all
> /scan auth.py target="race conditions"  # goal-specific prism
> /scan auth.py fix auto           # scan → fix → re-scan
> /prism single                    # chat: fresh prism per message
```

## File Structure

```
prism.py                 v0.8.6 (6200+ lines, 20 tests)
prisms/                  7 portfolio prisms + L12 variants
prompts/                 80+ cognitive prisms (L4-L12)
research/                Experiment scripts, benchmarks
output/                  650+ raw experiment outputs
experiment_log.md        Full research log (29 rounds)
```
