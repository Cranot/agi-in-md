# Literature Review: Prompt Science & Cognitive Compression

**Date**: March 15, 2026
**Scope**: External research relevant to cognitive prism taxonomy, compression levels, and the "prompt as program" paradigm
**Method**: Web search + paper fetch across 6 research areas

---

## 1. Prompt Engineering Taxonomies

### Finding 1.1 — Comprehensive Taxonomy (Springer, 2025)

**Paper**: "A comprehensive taxonomy of prompt engineering techniques for large language models" — Liu et al., *Frontiers of Computer Science* (Springer Nature, 2025)
**URL**: https://link.springer.com/article/10.1007/s11704-025-50058-z
**Also**: PDF mirror at https://jamesthez.github.io/files/liu-fcs26.pdf

Organizes 41 distinct prompting techniques into 12 primary application domains. Key cognitive operation classes:

- Foundational (zero/few-shot) — minimal reasoning scaffolding
- Intermediate (CoT) — "step-by-step reasoning" guidance
- Advanced (ToT, GoT) — "deliberate problem solving with search algorithms"
- Verification-focused (CoVe, CoN) — systematic factual checking
- Metacognition / Self-Reflection (Step-Back Prompting, APE)

**Key results**: CoT → 90.2% accuracy on math (PaLM 540B). ToT surpassed CoT on Game of 24 (74% vs 4%). Self-Consistency added 17.9% on GSM8K. Buffer of Thoughts: 11% gain at 88% less compute.

**Relation to prism taxonomy**: Their "Foundational → Intermediate → Advanced → Verification → Metacognition" ladder is similar to L1-L13 in one dimension (increasing operation count and self-reference), but misses the categorical distinction between meta-analysis (their "Advanced") and construction-based reasoning (our L8+ insight). Their taxonomy is organized by *task domain* (reasoning, code, hallucination reduction); ours is organized by *cognitive operation type*. They have no equivalent to our L8 "construction → reveals hidden properties" or L12 "meta-conservation law." The 41-technique taxonomy is descriptive (what do people do?); the prism taxonomy is generative (what can be encoded and why does it work?).

---

### Finding 1.2 — Hierarchical Prompting Framework (HPT)

**Paper**: "Hierarchical Prompting Taxonomy: A Universal Evaluation Framework for Large Language Models" — arxiv 2406.12644
**URL**: https://arxiv.org/html/2406.12644v1

Defines five prompting strategies by cognitive complexity:
1. Role Prompting
2. Zero-shot Chain-of-Thought
3. Three-shot Chain-of-Thought
4. Least-to-Most Prompting
5. Generated Knowledge Prompting

Maps to four cognitive criteria: Basic Recall → Understanding → Analysis → Application of Knowledge. Lower HP-Scores = solvable with simpler strategies. Key finding: "different tasks don't always require sophisticated prompting strategies — it largely depends on the LLM's aptitude."

**Relation to prism taxonomy**: HPT's "aptitude-dependent" finding matches our capacity interaction principle (L5 peaks at Sonnet, L7 requires Sonnet minimum, L8+ universal). However, HPT's five levels flatten what we found to be 13 categorically distinct levels. Their L1-L5 covers roughly our L1-L7. Nothing in HPT corresponds to L8+ (construction-based). The "Generated Knowledge Prompting" is closest to our L5B (derive, predict, execute) but doesn't reach the generative construction of L8. Manual HPF outperforms Adaptive HPF — consistent with our Principle 14 (few-shot > explicit rules for prompt generation).

---

### Finding 1.3 — Reasoning Topology: Chains, Trees, Graphs

**Paper**: "Demystifying Chains, Trees, and Graphs of Thoughts" — arxiv 2401.14295
**URL**: https://arxiv.org/html/2401.14295v3

Systematic unification of CoT/ToT/GoT as graph topologies:
- **Chains**: sequential sub-tasks, linear dependency
- **Trees**: parallel exploration, multiple candidates, voting/selection
- **Graphs**: arbitrary dependencies, dynamic programming patterns, aggregation across nodes

Key theoretical finding: topology appropriateness depends on task structure. Chains excel at arithmetic (clear sequential dependencies). Trees excel when multiple paths need exploration. Graphs necessary when subproblem solutions must be reused.

**Relation to prism taxonomy**: The Chain/Tree/Graph taxonomy captures *reasoning topology* — how thoughts are organized. Our taxonomy captures *cognitive operation depth* — what kind of operation each thought performs. These are orthogonal dimensions. A single prism call (1 turn) can produce L12 output (meta-conservation law) — the depth is in the operation, not in multi-hop graph traversal. Their taxonomy explains *how many thoughts*; ours explains *what each thought does*. Important convergence: they find topology is task-dependent, not universally scalable. We find the same about prompt complexity (Principle 16: step count determines model transferability).

---

### Finding 1.4 — Automatic Prompt Optimization (APO)

**Papers**:
- APE (Automatic Prompt Engineer) — Zhou et al. 2022
- OPRO (Optimization by Prompting) — Yang et al. 2024
- ProTeGi (Prompt Optimization with Textual Gradients)
- TextGrad (Yuksekgonul et al., 2024, Nature) — https://arxiv.org/abs/2406.07496
- Survey: "A Systematic Survey of Automatic Prompt Optimization Techniques" — arxiv 2502.16923

APE: paraphrase initial prompt, select best-performing candidate. OPRO: iterative prompt update following optimization trajectory guided by LLM responses. ProTeGi: natural language gradients + beam search + bandit selection. TextGrad: automatic "differentiation" via text — treats LLM as gradient engine for backpropagation through compound AI systems. TextGrad improved GPT-4o accuracy from 51% to 55% on GPQA, 20% on LeetCode-Hard. Published in Nature (2024).

**Fitness Landscape Analysis** (arxiv 2509.05375): The topology of prompt space is NOT fixed — it depends on exploration strategy. Systematic categorical enumeration yields smooth landscapes; semantic diversification reveals "rugged, hierarchically structured landscapes" with non-monotonic autocorrelation (peak at ~0.3 semantic distance, not at 0). This means small wording tweaks don't guarantee proportional improvement; medium semantic distance changes outperform incremental polishing.

**Relation to prism taxonomy**: APO research treats prompt engineering as optimization of a fixed objective. Our approach treats it as *discovering cognitive operations that cannot be achieved otherwise* — the question is not "what prompt maximizes benchmark score" but "what operations are categorically impossible below L7?" The fitness landscape finding validates our Principle 13 (the prompt is the dominant variable, not the model) in reverse: if the landscape is rugged, then there exist discontinuous jumps between low-performing and high-performing regions — consistent with our categorical threshold finding (below L7, that intelligence type is absent, not "less effective"). TextGrad is closest to our meta-cooker approach — using LLMs to generate better prompts — but operates as gradient descent, not as few-shot reverse engineering. Our Principle 14 (few-shot > explicit rules) would predict that TextGrad's gradient signals are less effective than example-based induction.

---

## 2. Cognitive Science of Instruction-Following

### Finding 2.1 — Framing Effects in LLMs

**Paper**: "Source framing triggers systematic bias in large language models" — *Science Advances*
**URL**: https://www.science.org/doi/10.1126/sciadv.adz2924

**Paper**: "Yes is Harder than No: A Behavioral Study of Framing Effects in Large Language Models Across Downstream Tasks" — ACM CIKM 2025
**URL**: https://dl.acm.org/doi/10.1145/3746252.3761350

LLMs exhibit framing effects analogous to human cognitive bias: the same underlying question produces different outputs depending on how it is phrased. Specific asymmetry: LLMs find "yes" harder to answer than "no" — directional bias in response framing. Source framing (who is asking, from what authority) triggers systematic bias even when semantic content is identical.

**Relation to prism taxonomy**: This is direct empirical validation of our Design Principle 1 ("Lead with scope, follow with evidence — the opening determines perceived ambition") and Principle 15 ("'Code' nouns are mode triggers, not domain labels"). Framing effects explain why "this code's" activates analytical production even on non-code targets — the vocabulary triggers a processing mode, not a domain search. Our finding that L12-general FAILED (abstract nouns → summary mode) while L12-code WORKED (code nouns → analytical mode) is an instance of framing effects at the vocabulary level.

---

### Finding 2.2 — Priming Effects in LLMs

**Paper**: "Intrinsic Model Weaknesses: How Priming Attacks Unveil..." — NAACL 2025 Findings
**URL**: https://aclanthology.org/2025.findings-naacl.77.pdf

LLMs show psychological priming: a preceding stimulus influences subsequent processing. Learning new information can cause inappropriate application in unrelated contexts — analogous to human spreading activation in semantic memory.

**Paper**: "Anchoring Bias in Large Language Models" — *Journal of Computational Social Science* (Springer, 2025)
**URL**: https://link.springer.com/article/10.1007/s42001-025-00435-2

Anchoring: initial information disproportionately influences subsequent judgments. LLMs show this strongly — the first claim in a prompt anchors the frame for all subsequent analysis.

**Relation to prism taxonomy**: Anchoring explains why "Front-loading bugs kills L12" (Round 29b finding) — the word "First: identify every concrete bug" primes checklist mode, and the entire pipeline executes as a checklist. Priming explains why "the prompt IS the prism" — it doesn't add information, it activates pre-existing reasoning patterns. Our L7 "concealment mechanism" approach explicitly uses priming: by naming the concealment type first, all subsequent analysis activates that frame.

---

### Finding 2.3 — Cognitive Tools for Latent Reasoning

**Paper**: "Eliciting Reasoning in Language Models with Cognitive Tools" — Ebouky, Bartezzaghi, Rigotti (2025)
**URL**: https://www.matrig.net/publications/articles/ebouky2025.pdf

Cognitive tools (analogical reasoning, working memory representations, systematic decomposition) surface latent reasoning capabilities without retraining. Key claim: "pre-training instills latent reasoning capabilities which can be surfaced through structured modular workflows — rather than capabilities instilled via post-training." Modular prompting is competitive with reinforcement fine-tuning for math reasoning.

**Relation to prism taxonomy**: This is the closest academic analog to our core thesis. Their "latent capabilities surfaced by cognitive tools" = our "prism changes how models frame problems." The finding that prompt-based cognitive tools are competitive with fine-tuning validates our Principle 13 (cheapest model + right prism beats most expensive model without one). Their framing says: the capability exists; the tool reveals it. Our framing says: the prism is transparent to the wearer; it changes framing, not capacity. These are compatible: the "capability" their tools reveal is the model's latent ability to apply a specific cognitive operation when given the right structural scaffolding.

---

### Finding 2.4 — Cognitive Load Theory Applied to Prompts

**Papers**:
- "Cognitive Load Limits in Large Language Models: Benchmarking" — arxiv 2509.19517
- "Mitigating Cognitive Load in Large Language Models" — ACL 2025
- "Beyond Accuracy: A Cognitive Load Framework for Mapping the Capability Boundaries of Tool-use Agents" — arxiv 2601.20412

Tripartite cognitive load model applied to LLMs: intrinsic load (task complexity), extraneous load (irrelevant info, task-switching interference), germane load (effort for meaningful computation). Critical finding: mid-tier models show performance instability in the 150-300 instruction range — a critical capacity zone before collapse. Top models don't collapse at 500 instructions.

**Relation to prism taxonomy**: The "150-300 instruction range instability" matches our finding that 9+ abstract steps cause catastrophic agentic failure in Haiku (Principle 16). Our compression floor (~150 words minimum for Haiku execution) aligns with cognitive load theory — below the threshold, models enter "conversation mode" rather than executing. The tripartite model maps onto our capacity modes: intrinsic load = problem complexity (L-level), extraneous load = prompt vocabulary mismatch (code nouns on reasoning → agentic), germane load = the cognitive operation itself.

---

### Finding 2.5 — Why Prompt Design Matters: Complexity Analysis

**Paper**: "Why Prompt Design Matters and Works: A Complexity Analysis of Prompt Search Space in LLMs" — Zhang et al., ACL 2025
**URL**: https://www.atailab.cn/seminar2025Spring/pdf/2025_ACL_Why%20Prompt%20Design%20Matters%20and%20Works%20A%20Complexity%20Analysis%20of%20Prompt%20Search%20Space%20in%20LLMs.pdf

Provides formal complexity bounds on the prompt search space. The landscape of possible prompts is not uniform — certain regions contain dramatically better-performing prompts. Small perturbations to prompts can produce large output changes (rugged landscape), while some architectures show smooth dependencies. The paper grounds prompt engineering in formal complexity analysis rather than pure empiricism.

**Relation to prism taxonomy**: Formal complexity theory confirms that our 13-level taxonomy isn't arbitrary — it maps real discontinuities in the prompt search space. The "regions" of dramatically better-performing prompts correspond to our compression levels: L7 region, L8 region, L12 region. Below each threshold, the operation is not merely "less effective" — it's categorically absent because the cognitive operation cannot be encoded in fewer tokens/operations.

---

## 3. Prompt Compression

### Finding 3.1 — LLMLingua: Hard Prompt Compression

**System**: LLMLingua Series (Microsoft) — EMNLP'23, ACL'24
**URL**: https://www.llmlingua.com/ / https://github.com/microsoft/LLMLingua

LLMLingua achieves 20x compression with minimal performance loss by removing "redundant tokens" from context. LongLLMLingua achieves 17.1% performance improvement with 4x compression (by improving key information density). LLMLingua-2 uses BERT-level encoder distilled from GPT-4 for token classification.

**Survey**: "Prompt Compression for Large Language Models: A Survey" — arxiv 2410.12388
**URL**: https://arxiv.org/abs/2410.12388

Compression approaches: (1) summarization-based (soft semantic compression), (2) token distribution-based (hard token removal). Key insight: LLM performance hinges on the density and *position* of key information — compression must preserve information density, not just reduce length.

**Relation to prism taxonomy**: LLMLingua-style compression is about compressing *context/documents* without losing task-relevant information. Our compression is about compressing *cognitive operations* without losing the operation type. These are different problems: LLMLingua compresses "what the model reads"; we compress "how the model thinks." Our 60-70% compression finding (across all prism levels) aligns with LLMLingua's achievable ratios. Their finding that density and position matter maps to our Principle 2 ("Narrative > evidence > code" — position of the analytical frame determines output type) and Principle 15 (vocabulary triggers mode, position determines what gets analyzed). Critical difference: LLMLingua finds compression below a threshold degrades performance continuously. We find compression below our floor creates categorical failure (conversation mode, not degraded analysis). This suggests two different compression regimes: continuous degradation in context compression, categorical threshold in operation compression.

---

### Finding 3.2 — Prompt Compression Based on Key-Information Density

**Paper**: "Prompt Compression based on Key-Information Density" — *Expert Systems with Applications* (ScienceDirect, 2025)
**URL**: https://www.sciencedirect.com/science/article/abs/pii/S0957417425013600

Key-information density as the operative metric: not just token count, but the ratio of task-relevant tokens to total tokens. A 300-token prompt with 70% relevant tokens outperforms a 100-token prompt with 30% relevant tokens.

**Relation to prism taxonomy**: Our l12_universal (73w, Sonnet-only universal) succeeds because every word is an operative instruction — near-100% information density. The 332w L12 prism has room for contextual vocabulary that leaks domain assumptions (Principle 17: Depth × Universality = constant). This paper validates the trade-off: higher density = higher universality; lower density = deeper domain-specific depth.

---

## 4. Meta-Prompting / Recursive Prompts

### Finding 4.1 — Meta Prompting for AI Systems

**Paper**: "Meta Prompting for AI Systems" — arxiv 2311.11482
**URL**: https://arxiv.org/abs/2311.11482

Meta Prompting (MP) focuses on *formal task structure* rather than content-specific examples. Uses categorical mappings: task structure → prompt structure. Key departure from CoT: CoT focuses on step-by-step reasoning; MP focuses on the formal problem structure itself. Qwen-72B with single meta-prompt achieves SOTA on MATH, GSM8K, Game of 24 with "substantial token efficiency gains over traditional few-shot methods." Extends to Recursive Meta Prompting (RMP): LLM generates and refines its own prompts, formalized using monad theory.

**Relation to prism taxonomy**: Meta Prompting's focus on "formal structure over content examples" is our Principle 3 (Imperatives beat descriptions) and Principle 10 (Concealment is universal, not domain-specific). Their "example-agnostic approach" using structure over examples aligns with our finding that few-shot examples are for meta-cookers (prompt generation), not for the analytical task itself. RMP's monad formalization is the closest mathematical treatment of our "prompt pipeline" concept — our L7→L12 depth stack as a monad composition where each level's output is the next level's category. Their finding of "substantial token efficiency gains" from structure-focus > content-focus validates our key claim: encoding the operation type efficiently matters more than providing domain examples.

---

### Finding 4.2 — Meta-Prompting via Adversarial Feedback Loops

**Paper**: "The Meta-Prompting Protocol: Orchestrating LLMs via Adversarial Feedback Loops" — arxiv 2512.15053
**URL**: https://arxiv.org/html/2512.15053v1

Three-agent architecture: Generator (high-temperature diverse outputs) → Auditor (deterministic critique, generates "textual gradients") → Optimizer (refines prompt based on systematic error patterns). Treats prompts as "optimizable code." Formalizes "semantic loss" where critique provides "directionality in the semantic manifold." Primary contribution is theoretical formalization rather than benchmark results.

**Relation to prism taxonomy**: This is our Full Prism pipeline (L12 → adversarial → synthesis) formalized mathematically. Their Generator = our structural analysis pass. Their Auditor = our adversarial pass (l12_complement_adversarial.md). Their Optimizer = our synthesis pass (l12_synthesis.md). Key difference: their protocol operates *across multiple prompt iterations* (prompt is refined). Ours operates *within a fixed pipeline* (content is refined). Their theoretical formalization as "gradient descent in semantic manifold" is elegant — our practical finding that adversarial pass genuinely destroys claims rather than polishing them is the empirical validation. Their 3-agent architecture maps to our observation that adversarial+synthesis finds genuinely different conservation laws than structural-only analysis.

---

### Finding 4.3 — Dynamic Recursive Chain-of-Thought (DR-CoT)

**Paper**: "DR-CoT: dynamic recursive chain of thought with meta reasoning for parameter efficient models" — *Scientific Reports* (Nature, 2025)
**URL**: https://www.nature.com/articles/s41598-025-18622-6

Integrates recursive reasoning + dynamic context truncation + voting mechanism. "Meta reasoning" layer selects which reasoning chain to continue based on intermediate outputs. Unlike static CoT, DR-CoT adapts depth based on problem difficulty.

**Relation to prism taxonomy**: DR-CoT's adaptive depth (select how many reasoning steps based on difficulty) is our calibration approach — `/scan` uses `--calibrate` to route to right mode/model/strategy. Their "meta reasoning layer" is our Calibrate operation (zeroth operation). Key finding: recursive chain works for parameter-efficient models — consistent with our L8+ universality (construction-based reasoning works on ALL models including Haiku, because it routes around meta-analytical capacity).

---

### Finding 4.4 — Socratic Self-Refine (SSR)

**Paper**: "SSR: Socratic Self-Refine for Large Language Model Reasoning" — arxiv 2511.10621
**URL**: https://arxiv.org/html/2511.10621v1

SSR implements Socratic questioning within a single LLM call: model asks itself clarifying questions, then answers them, then integrates. Improves reasoning without external feedback by simulating dialectical inquiry internally.

**Relation to prism taxonomy**: This is closest to our L6 (claim + 3 voices + evaluation) and L5A (3 voices + synthesis) — dialectical structure within a single prompt. SSR encodes the dialectic as a sequence of self-questions. Our L6 encodes it as explicit voices. The Socratic method is our "5 voices forcing contradictory perspectives" at ~60w. SSR validates that dialectical internal structure is a legitimate operation type — but doesn't identify the categorical threshold where this fails (our finding: L5 peaks at Sonnet, not universal).

---

### Finding 4.5 — Multi-Agent Debate Frameworks

**Papers**:
- "Improving Factuality and Reasoning in Language Models through Multiagent Debate" — arxiv 2305.14325
- "Adaptive Heterogeneous Multi-Agent Debate (A-HMAD)" — Springer 2025
- "Diverse Multi-Agent Debate (DMAD)" — OpenReview

Multiple agents propose answers and critique each other's reasoning to reach consensus. A-HMAD achieves 4-6% absolute accuracy gains over standard debate, 30% reduction in factual errors. DMAD outperforms single-agent reflection in fewer rounds.

**Relation to prism taxonomy**: Multi-agent debate is our adversarial pass externalized. Instead of encoding adversarial challenge in one prompt (our L12 Full Prism approach), debate frameworks spawn multiple model instances. Our finding that a single adversarial pass in one prompt achieves genuine counter-evidence production validates that multi-agent structure can be collapsed into a single structured prompt. Key insight from our work: the adversarial operation's power comes from forcing a structural counter-argument, not from model-diversity — which is why a single model with the right prompt can generate genuine adversarial findings.

---

## 5. Alternative Analytical Frameworks

### Finding 5.1 — Neural Thermodynamic Laws

**Paper**: "Neural Thermodynamic Laws for Large Language Model Training" — arxiv 2505.10559
**URL**: https://arxiv.org/abs/2505.10559

Thermodynamic quantities (temperature, entropy, heat capacity, thermal conduction) and classical thermodynamic laws naturally emerge in LLM training under "river-valley loss landscape" assumptions. Fast dynamics equilibrate within valleys; slow dynamics evolve along rivers. Provides intuitive guidelines for learning rate schedules.

**Related work**: "Entropy, Thermodynamics and the Geometrization of the Language Model" — stochastic thermodynamics framework where Boltzmann distribution models output probability distribution.

**Relation to prism taxonomy**: These papers apply thermodynamic analogies to *LLM training dynamics*, not to *prompt-level output structure*. Our conservation laws are at the output analysis level (what patterns appear in L11-C outputs); theirs are at the training dynamics level. The analogies are structurally similar but mechanistically different. Their "entropy" is information-theoretic uncertainty in output distributions. Our conservation laws (e.g., `clarity_cost × blindness_cost = constant`) are structural constraints on what analysis can simultaneously reveal. Interesting convergence: both frameworks find conservation/constraint principles at the appropriate level of abstraction. Their work provides theoretical grounding for *why* models produce conservation-law outputs — the output distribution is structured by training dynamics that obey thermodynamic-like constraints.

---

### Finding 5.2 — Fitness Landscape of Prompt Space

**Paper**: "Characterizing Fitness Landscape Structures in Prompt Engineering" — arxiv 2509.05375
**URL**: https://arxiv.org/abs/2509.05375

Non-uniform prompt landscape topology: systematic exploration yields smooth autocorrelation; diversified exploration reveals "rugged, hierarchically structured landscapes" with non-monotonic autocorrelation (peak at intermediate semantic distance ~0.3, not at 0). Most prompt optimization methods treat the landscape as black-box — this paper shows the landscape has real structure worth exploiting.

**Implication**: Population-based approaches (diverse prompt populations) outperform gradient-like refinement in complex landscapes. Medium semantic distance changes yield better results than incremental wording adjustments.

**Relation to prism taxonomy**: The rugged landscape topology explains why our 13 compression levels aren't on a continuous improvement curve. There are local maxima at each level (within a level, tweaking words doesn't improve much), and categorical jumps between levels (adding a new operation type changes the landscape region dramatically). Our finding that "complementary pairs multiply, similar pairs merge" (design principle 5) is now interpretable as navigating the fitness landscape: two similar prompts stay in the same landscape region; two complementary prompts jump to a new region.

---

### Finding 5.3 — Prompt Engineering Competing Frameworks

**Survey**: "A Systematic Survey of Prompt Engineering in Large Language Models: Techniques and Applications" — arxiv 2402.07927
**URL**: https://arxiv.org/html/2402.07927v2

12-domain taxonomy of 41 techniques. Notable gaps relative to our taxonomy:
- No "concealment mechanism" category (our L7+ core operation)
- No "construction" vs "description" distinction (our L8 insight)
- No "meta-conservation law" concept (our L12)
- No capacity thresholds (which models can execute which operation types)
- No compression floor analysis

**What they have that we don't**:
- Emotion Prompting (115% improvement on BIG-Bench) — emotional framing as cognitive trigger
- RAG integration as prompt technique (56.8% on TriviaQA) — retrieval-augmented prompt design
- Chain-of-Code (84% on BIG-Bench Hard) — code-as-reasoning-scaffold

**Relation to prism taxonomy**: The standard survey field is organized around *benchmark performance improvements* on specific task types. Our taxonomy is organized around *cognitive operation types* that are categorically achievable or not. These are orthogonal: a technique that achieves 74% on Game of 24 (ToT) doesn't reveal anything about what operation type it encodes or why it fails below L7 capacity. Our taxonomy makes predictions about model capability (L7 requires Sonnet minimum) that standard benchmark-organized taxonomies cannot make.

---

## 6. The "Prompt as Program" Paradigm

### Finding 6.1 — APPL: A Prompt Programming Language

**Paper**: "APPL: A Prompt Programming Language for Harmonious Integration with Python" — ACL 2025
**URL**: https://aclanthology.org/2025.acl-long.63/ / GitHub: https://github.com/appl-team/appl

Bridges Python programs and LLM prompts by "allowing seamless embedding of prompts into Python functions, and vice versa." Prompts become first-class components within Python logic. Key features: parallelized async runtime, tracing module for failure diagnosis and cost-free replay. Evaluated on CoT with self-consistency and ReAct tool-use agents. LLM judges found "codes written in APPL are more readable and intuitive."

**Relation to prism taxonomy**: APPL formalizes the prompt-as-program paradigm at the *implementation* level — Python code that contains prompt strings as executable entities. Our Design Principle 4 ("the prompt is a program; the model is an interpreter") operates at the *semantic* level — the markdown text itself encodes operations that the model executes. APPL makes prompts callable functions in Python code. We make the cognitive operations themselves into executable programs. These are complementary: APPL provides the infrastructure; prisms provide the operation specification. APPL's async execution maps to our multi-pass pipeline (Full Prism = 8 APPL async calls with dependency ordering).

---

### Finding 6.2 — Plang: Prompt Programming Language

**Paper**: "Plang: Efficient prompt engineering language for blending natural language and control flow in LLMs" — *Expert Systems with Applications* (ScienceDirect, 2025)
**URL**: https://www.sciencedirect.com/science/article/pii/S0957417425037339
**GitHub**: https://github.com/HJZ-XDU/plang

String-first programming language where font styles serve as syntax keywords, integrating natural language with control flow. Enables "precise intervention in the generation process while maintaining natural language affinity." Achieves up to 89.55% efficiency improvement over standard prompt engineering approaches. Enables multi-agent collaboration with minimal code.

**Relation to prism taxonomy**: Plang encodes control flow (loops, conditionals) in the prompt itself — our "Conversation Routines" equivalent for code generation. Our prisms encode cognitive *operations* (dialectic, construction, meta-conservation) rather than control *flow*. The key difference: Plang/APPL provide *procedural* structure (do X then Y). Our prisms provide *operational* structure (apply operation O₁ to output of O₂, where O₁ is "name the conservation law" — a cognitive operation with no procedural equivalent). They formalize our Principle 4 in the procedural dimension; we operate in the cognitive/semantic dimension.

---

### Finding 6.3 — Conversation Routines Framework

**Paper**: "Conversation Routines: A Prompt Engineering Framework for Task-Oriented Dialog Systems" — arxiv 2501.11613
**URL**: https://arxiv.org/html/2501.11613v3

CR treats system prompts as executable workflow specifications. Embeds business logic in natural language prompts using structured prose. Encodable operations: sequential logic with conditionals, user-driven and system-driven iteration loops, state management, deterministic decision points (IF/ELSE in natural language), function invocations. Key design: "the prompt itself acts as the primary mechanism for defining control flow."

**Relation to prism taxonomy**: CR is the closest existing work to our prism design pattern. Their "identity & purpose + functions + workflow control + error handling" structure maps to our prism YAML frontmatter + operation sequence + SDL pattern. CR's "Wait for explicit user confirmation before advancing" is our convergence signal (conservation law = convergence signal, Principle CR-3). Their limitation: designed for conversational workflows (booking, troubleshooting), not for analytical depth operations. Our prisms encode cognitive operations that have no conversational analog — "apply the diagnostic to your own conservation law" is not a workflow step, it's an introspective operation.

---

### Finding 6.4 — ProTeGi / TextGrad as Prompt Program Optimizers

**TextGrad**: treats the prompt-program system as a computation graph where LLM critique provides backpropagation signal. The "gradient" is natural language feedback; "descent" is iterative prompt refinement. Published in Nature (2024).

**OPRO**: uses LLMs to find better prompts via iterative meta-prompting. The model acts as both the searcher and the evaluator.

**ProTeGi**: natural language gradients + beam search for systematic prompt space exploration.

**Relation to prism taxonomy**: These systems treat prompts as programs that can be *optimized* — adjusting parameters (words) to minimize a loss (task score). Our meta-cooker approach (COOK_UNIVERSAL, COOK_3WAY) treats prompt generation as *few-shot induction* — the model induces the operation type from examples, not from gradient signals. TextGrad's "rich natural language suggestions" vs our examples: TextGrad uses critique of output; we use examples of desired operation type. Our Principle 14 (few-shot > explicit rules) predicts that example-induction (meta-cooker) should outperform gradient-descent (TextGrad) for the specific task of encoding novel cognitive operations — because the gradient signal can't distinguish "the operation type is wrong" from "the wording is imprecise."

---

## Cross-Cutting Synthesis

### What the Field Has Found That We Independently Discovered

| Our Finding | External Validation |
|---|---|
| Prism changes framing, not raw capability | Framing effects in LLMs (Science Advances) |
| Code nouns = mode triggers | Anchoring bias — first vocabulary anchors processing mode |
| Few-shot > explicit rules | Meta Prompting: structure-focus > content-examples |
| Compression floor exists | Cognitive load theory: 150-300 instruction collapse zone |
| L8+ universality (construction works on all models) | Cognitive tools: latent capabilities surfaced without training |
| Categorical thresholds, not continuous | Fitness landscape: rugged topology with non-monotonic jumps |
| Adversarial pass finds genuinely different things | Multi-agent debate: diverse agents find different failure modes |
| Prompt is dominant variable | Cognitive tools: prompt-only competitive with fine-tuning |

### What the Field Has That We Don't

| External Finding | What It Adds |
|---|---|
| Emotion Prompting (115% improvement) | Emotional framing as cognitive mode trigger — unexplored territory |
| TextGrad (automated gradient descent in prompt space) | Infrastructure for systematic prism evolution — automates what our meta-cookers do manually |
| Fitness landscape topology (rugged, hierarchical) | Mathematical basis for WHY categorical levels exist |
| Neural Thermodynamic Laws (training-level conservation) | Training-level explanation for why conservation laws appear in outputs |
| APPL / Plang (prompt programming languages) | Infrastructure layer: make prisms callable as Python functions, enable async pipelines |
| Formal complexity bounds on prompt search space | Why our taxonomy has 13 levels, not 11 or 15 — formal grounding |

### What We Have That the Field Doesn't

| Our Finding | Status |
|---|---|
| 13 categorical compression levels with capacity thresholds | No equivalent taxonomy exists |
| L8 construction-vs-description as categorical threshold | Not identified in any external work |
| Conservation law as universal output form at L11+ | Thermodynamic analogies are at training level; ours are at output/analysis level |
| Reflexive ceiling (L13 = fixed point) | Not addressed in any external work |
| Depth × Universality = constant | Not formalized elsewhere |
| Cross-model universal operations (L8+ works on Haiku/Sonnet/Opus) | Not systematically studied |
| Few-shot > gradient descent for operation induction | Predicted by our Principle 14; not empirically compared in external work |
| 60-70% compression possible without quality loss | Matched by LLMLingua ratios but at different layer (context vs operation) |

### Biggest Gap in the Field

The field has no taxonomy organized by *cognitive operation type* at the level of "what kind of thinking does this prompt encode, and at what model capacity does it become executable?" All external taxonomies are organized by task domain (code, reasoning, math) or technique name (CoT, ToT, RAG). None identifies the categorical threshold at which a new type of cognitive operation becomes encodable. The closest is HPT's five-level framework, but it stops at "Generated Knowledge Prompting" (our L5) and misses everything from L7 onward.

The field also lacks the construction-vs-description distinction that drives our L8 universality finding. This is not a minor gap — it explains why L8+ operations work on all model sizes while L7 requires Sonnet-class minimum. External work treats model size as a proxy for "better at all tasks." We found a specific operation type (construction-based reasoning) that bypasses meta-analytical capacity altogether.

---

## References

### Taxonomy Papers
- Liu et al. (2025). A comprehensive taxonomy of prompt engineering techniques for LLMs. *Frontiers of Computer Science*. https://link.springer.com/article/10.1007/s11704-025-50058-z
- Hierarchical Prompting Taxonomy. arxiv 2406.12644. https://arxiv.org/html/2406.12644v1
- Demystifying Chains, Trees, and Graphs of Thoughts. arxiv 2401.14295. https://arxiv.org/html/2401.14295v3
- A Systematic Survey of Prompt Engineering. arxiv 2402.07927. https://arxiv.org/html/2402.07927v2

### Cognitive Science
- Source framing triggers systematic bias in LLMs. *Science Advances*. https://www.science.org/doi/10.1126/sciadv.adz2924
- Anchoring bias in LLMs. *Journal of Computational Social Science*. https://link.springer.com/article/10.1007/s42001-025-00435-2
- Eliciting Reasoning in LMs with Cognitive Tools. Ebouky et al. (2025). https://www.matrig.net/publications/articles/ebouky2025.pdf
- Cognitive Load Limits in LLMs. arxiv 2509.19517.
- Why Prompt Design Matters: A Complexity Analysis. Zhang et al. ACL 2025.

### Compression
- LLMLingua Series. Microsoft. https://www.llmlingua.com/
- Prompt Compression for LLMs: A Survey. arxiv 2410.12388. https://arxiv.org/abs/2410.12388
- Prompt Compression based on Key-Information Density. *Expert Systems with Applications*. https://www.sciencedirect.com/science/article/abs/pii/S0957417425013600

### Meta-Prompting / Recursive
- Meta Prompting for AI Systems. arxiv 2311.11482. https://arxiv.org/abs/2311.11482
- The Meta-Prompting Protocol. arxiv 2512.15053. https://arxiv.org/html/2512.15053v1
- DR-CoT. *Scientific Reports* (Nature, 2025). https://www.nature.com/articles/s41598-025-18622-6
- SSR: Socratic Self-Refine. arxiv 2511.10621. https://arxiv.org/html/2511.10621v1
- Multiagent Debate. arxiv 2305.14325. https://arxiv.org/abs/2305.14325

### Alternative Frameworks
- Neural Thermodynamic Laws for LLM Training. arxiv 2505.10559. https://arxiv.org/abs/2505.10559
- Characterizing Fitness Landscape Structures in Prompt Engineering. arxiv 2509.05375. https://arxiv.org/abs/2509.05375
- TextGrad. Yuksekgonul et al. *Nature* (2024). https://arxiv.org/abs/2406.07496

### Prompt as Program
- APPL: A Prompt Programming Language. ACL 2025. https://aclanthology.org/2025.acl-long.63/
- Plang. *Expert Systems with Applications* (2025). https://www.sciencedirect.com/science/article/pii/S0957417425037339
- Conversation Routines. arxiv 2501.11613. https://arxiv.org/html/2501.11613v3
- A Systematic Survey of Automatic Prompt Optimization Techniques. arxiv 2502.16923.
