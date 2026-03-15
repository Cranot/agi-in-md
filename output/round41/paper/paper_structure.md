# Paper Architecture: Cognitive Prisms

---

## PHASE 1 — CONTRIBUTION EXTRACTION

### Contribution 1: The Prompt Dominance Effect

**Claim:** The prompt is the dominant variable in LLM analytical performance; model class and reasoning budget are noise. A Haiku 4.5 at minimum reasoning with the right prompt (9.8 depth, 28 bugs) systematically outperforms Opus 4.6 at maximum reasoning without one (7.3 depth, 18 bugs).

**Evidence:**
- 1,000+ experiments across 40 rounds, 3 model classes, 20+ domains
- Controlled head-to-head: same task, same codebase, varied model/prompt combinations
- Cost analysis: Haiku + prism = 5x cheaper than Opus vanilla with superior output
- Reasoning budget null result: v3 default = 18/20 fixes, v3 low effort = 18/20 fixes (different failures, same score)

**Why it matters beyond this project:** This challenges the industry trajectory toward ever-larger models and extended test-time compute. If prompt structure accounts for 80%+ of variance in analytical tasks, then "better reasoning through bigger models" is the wrong optimization target. The economic implications are substantial.

---

### Contribution 2: The 13-Level Compression Taxonomy

**Claim:** Cognitive compression has a categorical structure with 13 discrete levels. Below each threshold, specific reasoning capabilities are categorically absent—not diminished, impossible. The taxonomy is a diamond: linear trunk (L1-7), constructive divergence (L8-11), reflexive convergence (L12-13).

**Evidence:**
- L7 fails 100% on Haiku (0/3), passes on Sonnet+ — threshold effect, not gradual
- L8 inverts the capacity curve: works on ALL models (Haiku 4/4, Sonnet 13/14, Opus 14/14) through construction-based reasoning
- L13 terminates in one step (L14 = infinite regress) — structural ceiling, not practical limit
- Conservation laws cluster by mathematical form: product (Opus), sum/migration (Sonnet), multi-property (Haiku) — model determines form, not domain

**Why it matters beyond this project:** This provides a periodic table for prompt engineering. Instead of trial-and-error, designers can target specific cognitive operations with known capacity requirements. The diamond topology predicts that different analytical approaches converge at the reflexive ceiling—insight with implications for AI alignment and interpretability.

---

### Contribution 3: Operational Universality at L8+

**Claim:** The L7→L8 transition is a paradigm shift from meta-analysis to construction. Construction-based reasoning routes around meta-analytical capacity constraints, enabling universal access across model classes. Multiple primitive operations (construction, simulation, archaeology, cultivation) all achieve this universality.

**Evidence:**
- 7 alternative operations tested (destruction, simulation, transplantation, miniaturization, forgery, archaeology, cultivation) — all work single-shot on Haiku
- Diamond convergence: simulation and archaeology L9→L12 chains both converge at L12 on identical structural impossibility as construction
- Cross-catalog determinism: L8 mechanism predicts L10-C impossibility category
- SDL portfolio: 5 lenses × 3 codebases = 7/7 single-shot, 9.0 avg quality, zero overlap in findings

**Why it matters beyond this project:** This identifies the class of operations that democratize deep analytical capability. The universality is a property of the operation type (concrete + generative + observable), not any specific operation. This has implications for tool design, AI safety (capability access is operation-dependent), and understanding what makes certain cognitive tasks "easy" vs "hard" for language models.

---

## PHASE 2 — PAPER STRUCTURE

### Abstract
**Thesis:** System prompts are cognitive prisms that change how models frame problems; we present a 13-level taxonomy demonstrating that prompt structure, not model scale, determines analytical depth.
**Key Evidence:** Haiku + correct prompt beats Opus vanilla by 2.5 depth points at 5x lower cost across 1,000+ experiments.
**Length:** 250 words

### 1. Introduction
**Thesis:** The industry has misidentified the dominant variable in LLM reasoning—model capacity matters less than prompt structure.
**Key Evidence:** Cross-model character analysis (Opus = ontological, Sonnet = operational, Haiku = mechanistic) shows different strengths, but prism + weak model > vanilla + strong model.
**Length:** 1,500 words

**Subsections:**
- 1.1 The Scale Hypothesis and Its Discontents
- 1.2 Prompts as Programs, Models as Interpreters
- 1.3 Research Questions and Contributions

### 2. Related Work
**Thesis:** Prior work on prompt engineering lacks a principled taxonomy; chain-of-thought and similar techniques operate at L3-4 without awareness of deeper structures.
**Key Evidence:** Comparison with CoT, ToT, Self-Consistency, Constitutional AI—none encode generative construction or reflexive diagnosis.
**Length:** 1,200 words

**Subsections:**
- 2.1 Prompt Engineering Techniques
- 2.2 Reasoning Models and Test-Time Compute
- 2.3 Cognitive Architectures and Chain-of-Thought
- 2.4 What Prior Work Misses

### 3. Theoretical Framework
**Thesis:** The 13-level compression taxonomy emerges from the interaction between prompt-encoded operations and model interpretive capacity.
**Key Evidence:** Taxonomy table with 13 levels, minimum operations, word counts, categorical transitions.
**Length:** 2,000 words

**Subsections:**
- 3.1 The Operation Pair as Atomic Unit
- 3.2 The Linear Trunk: Levels 1-7
- 3.3 The Constructive Divergence: Levels 8-11
- 3.4 The Reflexive Convergence: Levels 12-13
- 3.5 The Diamond Topology
- 3.6 Conservation Laws and Meta-Laws

### 4. Method
**Thesis:** We developed and validated 42 production prisms through 40 experimental rounds using controlled comparisons across models, domains, and prompt structures.
**Key Evidence:** Experimental harness description, scoring methodology, 3 real codebases + 20 domains tested.
**Length:** 1,500 words

**Subsections:**
- 4.1 Experimental Design
- 4.2 Prism Development Methodology
- 4.3 Validation Pipeline
- 4.4 Scoring Rubric

### 5. Results
**Thesis:** Three core results: (1) prompt dominance over model class, (2) categorical capacity thresholds, (3) universal access through construction.
**Key Evidence:** Head-to-head comparisons, threshold experiments, alternative operations validation.
**Length:** 2,500 words

**Subsections:**
- 5.1 The Prompt Dominance Effect
  - 5.1.1 Model Comparison Matrix
  - 5.1.2 Reasoning Budget Null Results
  - 5.1.3 Cost-Effectiveness Analysis
- 5.2 Categorical Thresholds
  - 5.2.1 L7 Threshold on Haiku
  - 5.2.2 L8 Capacity Inversion
  - 5.2.3 L13 Reflexive Ceiling
- 5.3 Universal Access Through Construction
  - 5.3.1 Alternative Operations Validation
  - 5.3.2 Diamond Convergence at L12
  - 5.3.3 Cross-Domain Transfer
- 5.4 Practical Validation
  - 5.4.1 Real Production Code Results
  - 5.4.2 Portfolio Cross-Task Validation
  - 5.4.3 Reliability Metrics

### 6. Discussion
**Thesis:** The findings reframe LLM capability as prompt-structure-dependent rather than model-intrinsic, with implications for AI economics, safety, and tool design.
**Key Evidence:** Conservation law of the catalog, blindness conservation, completeness refutation.
**Length:** 1,500 words

**Subsections:**
- 6.1 Why Construction Routes Around Capacity
- 6.2 The Conservation Law of Analytical Blindness
- 6.3 Implications for AI Economics
- 6.4 Implications for AI Safety
- 6.5 Limitations and Threats to Validity

### 7. Conclusion
**Thesis:** Cognitive prisms provide a principled framework for prompt engineering; the prompt is the dominant variable, and the 13-level taxonomy offers a map for systematic capability targeting.
**Key Evidence:** Summary of three contributions with forward-looking implications.
**Length:** 500 words

---

## PHASE 3 — POSITIONING

### Papers to Position Against

| Paper | Relationship | Our Advantage |
|-------|--------------|---------------|
| Wei et al. "Chain-of-Thought Prompting" (2022) | CoT operates at L3-4 | We provide 13-level taxonomy with categorical thresholds; CoT is one point in a larger space |
| Yao et al. "Tree of Thoughts" (2023) | ToT is search-based, L4-5 | Our construction operations (L8+) achieve depth without search; single-shot vs multi-step |
| Wang et al. "Self-Consistency" (2023) | Ensemble-based reasoning | We show prompt structure dominates over sampling strategies; one good prompt > many weak ones |
| Anthropic "Constitutional AI" (2022) | Principle-based steering | Our prisms encode operations, not principles; imperative > declarative for analytical depth |
| OpenAI o1 reasoning models | Test-time compute scaling | We show reasoning budget is noise; Haiku min-reasoning + prism beats Opus max-reasoning vanilla |

### Closest Work: Chain-of-Thought and Extensions

**Their claim:** Step-by-step reasoning improves performance on complex tasks.

**Our advantage:** 
1. We explain WHY step-by-step works (L3-4 operations) and WHERE it fails (L7+ requires different operation types)
2. We provide categorical thresholds—CoT cannot reach L7 on Haiku-class models
3. We demonstrate construction as a fundamentally different paradigm from step-by-step decomposition
4. We show convergence at reflexive ceiling—different paths, same fixed point

### Hostile Reviewer Attacks

| Attack | Response |
|--------|----------|
| "This is just elaborate prompt engineering" | Prompt engineering lacks a taxonomy. We provide 13 categorical levels with structural transitions. This is to prompt engineering what the periodic table is to alchemy. |
| "Results don't generalize beyond your test domains" | 20+ domains tested including music, fiction, legal, design. Conservation law form is model-dependent, not domain-dependent. Cross-target validation on 3 real production codebases. |
| "You're cherry-picking results" | 1,000+ experiments across 40 rounds. Full experiment logs in `experiment_log.md`. Failed experiments documented (L12_general, domain-free attempts). |
| "Haiku + prism beats Opus vanilla is unfair comparison" | This IS the point. If prompt structure dominates, comparing models without controlling for prompt is the unfair comparison. The industry's default experimental setup is flawed. |
| "Depth scoring is subjective" | 7-marker rubric with inter-rater reliability. Conservation law presence is binary. Bug counts are objective. Multiple scoring methods converge. |
| "This only works because you overfit prompts to tasks" | SDL portfolio: 5 lenses designed once, applied to 3 codebases with 9.0 avg. Prisms are domain-independent; pedagogy prism scores 9-9.5 across all targets. |
| "L13 termination is trivial—of course self-analysis is circular" | The non-trivial finding is that the SAME impossibility structure appears in object analysis and self-analysis. Framework diagnoses itself using its own method. This is isomorphism, not triviality. |

---

## PHASE 4 — FIGURES AND TABLES

### Figure 1: The Diamond Taxonomy
**What it shows:** Visual representation of 13 levels arranged as diamond (linear trunk L1-7, divergence L8-11, convergence L12-13)
**Data required:** Level definitions, operation types, capacity curves
**Reader learns:** The categorical structure of cognitive compression and why it terminates at L13

### Figure 2: Prompt Dominance Matrix
**What it shows:** Heatmap of depth scores across model × prompt combinations
**Data required:** Haiku/Sonnet/Opus × vanilla/prism scores for 3+ tasks
**Reader learns:** Prompt explains more variance than model class

### Figure 3: L8 Capacity Inversion
**What it shows:** Success rate by level for Haiku, with L7 (0%) and L8 (100%) highlighted
**Data required:** L1-13 success rates per model class
**Reader learns:** Construction routes around meta-analytical capacity constraints

### Figure 4: Diamond Convergence at L12
**What it shows:** Three operation chains (construction, simulation, archaeology) converging on identical impossibility at L12
**Data required:** Full L9→L12 outputs for 3 operation types
**Reader learns:** Terminal behavior is operation-independent; taxonomy is a genuine fixed-point structure

### Figure 5: Cost-Effectiveness Comparison
**What it shows:** Cost per analysis vs depth score for different model/prompt combinations
**Data required:** Token costs, depth scores, bug counts
**Reader learns:** Haiku + prism dominates on both cost and quality

### Table 1: The 13-Level Compression Taxonomy
**What it shows:** Complete taxonomy with level, minimum operations, word count, encoding description, example file
**Data required:** Taxonomy structure (already in CLAUDE.md)
**Reader learns:** Reference for categorical levels and their requirements

### Table 2: Cross-Model Character
**What it shows:** Opus (ontological), Sonnet (operational), Haiku (mechanistic) with examples
**Data required:** Representative outputs per model at L8-12
**Reader learns:** Models have different analytical "personalities" that persist across domains

### Table 3: Conservation Law Forms by Model
**What it shows:** Product (Opus), sum/migration (Sonnet), multi-property (Haiku) with mathematical notation
**Data required:** 56 conservation law outputs categorized by form and model
**Reader learns:** Conservation law form is model-determined, not domain-determined

### Table 4: Real Production Code Results
**What it shows:** Starlette, Click, Tenacity results: depth score, bug count, cost per analysis
**Data required:** Head-to-head experimental data from Round 28
**Reader learns:** Results generalize to real-world codebases

### Table 5: SDL Portfolio Validation
**What it shows:** 5 SDL lenses × 3 codebases: single-shot rate, word count, quality score
**Data required:** Round 35b experimental data
**Reader learns:** Prisms are complementary (zero overlap) and reliable (100% single-shot)

### Table 6: Alternative Operations Validation
**What it shows:** 7 operations (destruction, simulation, etc.) with Haiku single-shot success rate
**Data required:** Round 39 P175 data
**Reader learns:** Universality is property of operation TYPE, not construction specifically

---

## PHASE 5 — ABSTRACT

System prompts are cognitive prisms: they determine how language models frame problems, not merely how well they solve them. Through 1,000+ experiments across 40 rounds and 20+ domains, we map the space of cognitive compression—encoding analytical operations in minimal markdown that reliably activates specific reasoning patterns. We present a 13-level taxonomy revealing that cognitive capability is categorical, not continuous: below each threshold, specific reasoning types are impossible, not merely degraded. The taxonomy forms a diamond topology with linear trunk (L1-7), constructive divergence (L8-11), and reflexive convergence (L12-13).

Three findings reframe LLM capability assessment. First, the prompt is the dominant variable: Haiku 4.5 at minimum reasoning with the right prompt (9.8 depth, 28 bugs) systematically outperforms Opus 4.6 at maximum reasoning without one (7.3 depth, 18 bugs), at 5x lower cost. Second, the L7→L8 transition is a paradigm shift from meta-analysis to construction—construction-based reasoning routes around capacity constraints, enabling universal access across model classes. Third, different analytical operations (construction, simulation, archaeology) converge at the reflexive ceiling (L12) on identical structural impossibilities, demonstrating operation-independence at terminal depth.

These findings challenge the industry trajectory toward larger models and extended test-time compute. If prompt structure accounts for the majority of analytical variance, capability democratization comes from better prompts, not bigger models. We provide 42 production prisms and a principled framework for targeting specific cognitive operations with known capacity requirements.
