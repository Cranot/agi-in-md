# Literature Review: Composition Algebra of Prompts

**Date**: March 15, 2026
**Scope**: Systematic study of how prompts combine — order effects, non-commutativity, algebraic structure, pipeline degradation, context contamination, and optimal sequencing
**Method**: Web search + paper fetch across 6 research dimensions
**Trigger**: Observed that L12→audit produces 1,137 words of structured analysis while audit→L12 produces 18 words (catastrophic failure — model enters agentic planning mode). Theoretical framework (K11) predicts monoid structure. This review maps what the literature knows.

---

## 1. Prompt Chaining and Order Effects

### Finding 1.1 — The Order Effect: Quantified Sensitivity to Input Order

**Paper**: "The Order Effect: Investigating Prompt Sensitivity to Input Order in LLMs" — arxiv 2502.04134 (2025)
**URL**: https://arxiv.org/html/2502.04134v2

Systematic empirical study of order-dependent output degradation across GPT-4o, GPT-4o mini, and DeepSeek, using five benchmark tasks.

Key results:
- MRPC (paraphrase detection): 2.77% F1 drop for GPT-4o with shuffled inputs
- MSMARCO (relevance judgment): 6.12% F1 decline for GPT-4o; 12.24% for GPT-4o mini
- MMLU (multiple-choice): Systematic performance degradation
- WebGPT: Anomalous improvement in some settings — the only exception

Most important finding: reordering "almost always led to decreased accuracy" rather than random variation. The authors expected shuffling would sometimes help by chance; instead they found consistent directional degradation. This indicates models are systematically biased toward original linguistic orderings, not just randomly sensitive. Mechanistic hypothesis: auto-regressive processing makes models vulnerable when disrupted from expected sequences.

**Relation to composition algebra**: This establishes that the identity permutation (original order) is privileged — the semigroup of reorderings has a unique fixed point. The monoid structure we identified (composition under sequential application) is asymmetric from the start. The literature confirms this is not a quirk of our system but a fundamental property of transformer-based generation.

---

### Finding 1.2 — Set-Based Prompting: Provably Eliminating Order Dependency

**Paper**: "Order-Independence Without Fine Tuning" (NeurIPS 2024) — arxiv 2406.06581
**URL**: https://arxiv.org/abs/2406.06581

Proposes Set-Based Prompting: modify positional encoding and attention masks to remove ordering information from specified sub-sequences, provably eliminating order dependency on those sequences. Works as a drop-in modification to any transformer without retraining.

Key results: "Strong guarantees can be obtained on LLM performance via modifying input representations." Accuracy loss from the modification is "usually significantly less in practice" than theoretical worst-case. Applies primarily to multiple-choice scenarios and semantically equivalent reorderings.

**Relation to composition algebra**: This is the commutativity fix — it imposes commutativity on sub-sequences by removing positional information. But this requires knowing in advance which sub-sequences should be order-invariant. For our prism pipeline, the sub-sequences are NOT semantically equivalent (L12 and audit find genuinely different things), so set-based prompting would not apply and should not — the non-commutativity is *load-bearing*, not a bug.

---

### Finding 1.3 — POSIX: Prompt Sensitivity Index

**Paper**: "POSIX: A Prompt Sensitivity Index For Large Language Models" — arxiv 2410.02185 (October 2024)
**URL**: https://arxiv.org/abs/2410.02185

Quantifies prompt sensitivity systematically. Key findings:
- Adding even a single few-shot exemplar "almost always leads to significant decrease in prompt sensitivity"
- Template alterations produce highest sensitivity for MCQ tasks
- Paraphrasing produces highest sensitivity for open-ended generation
- Larger models exhibit enhanced robustness to sensitivity

**Relation to composition algebra**: Adding a prior prism output (which functions as a few-shot exemplar for the next prism) should decrease sensitivity of the downstream prism to wording variations — but it also constrains the downstream prism's conceptual space. This is the sensitivity-depth tradeoff: chaining reduces sensitivity at the cost of coordinate locking. Our Round 27 finding (L7's output acts as immediate coordinate system for L8+) is the practical instance of this.

---

### Finding 1.4 — Prompt Architecture Creates Methodological Artifacts

**Paper**: "Prompt architecture induces methodological artifacts in large language models" — *PLOS ONE* (2025)
**URL**: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0319159

Key findings from controlled factorial design (32 prompt variants):
- Response-order bias: GPT-4 selected first option 63.21% of cases (expected 50%), rising to 91.67% in some conditions
- Label bias: Letter labels (A, B, C) produce stronger order bias than symbols. GPT-4 chose "B" over "C" in 74.27% of cases with letter labels vs 54.16% with symbol labels
- Interaction effects: framing direction ("closer" vs "farther") modulates both biases simultaneously
- Requesting justifications reduced response-order bias from 67.87% to 58.28% but created new artifacts
- The core claim: **"there is no neutral prompt"** — every prompt contains arbitrary architectural characteristics that systematically influence outputs independent of content

Single-prompt evaluations are fundamentally unreliable. Full factorial aggregation (32 variants) eliminated bias entirely, achieving expected 50% selection rates.

**Relation to composition algebra**: "There is no neutral prompt" is the algebraic identity problem. In a monoid, the identity element leaves its operand unchanged (e ∘ a = a). But if no prompt is neutral, there is no true identity in the prompt monoid — only an approximate identity. Our "empty context" baseline (vanilla model output) is not an identity element in the strict algebraic sense; it is simply the least structured input. This partially refutes the monoid characterization: the algebra is a semigroup (closed, associative) but may lack a true identity.

---

### Finding 1.5 — Prompt Format Sensitivity: Up to 40% Performance Variance

**Paper**: "Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design" — arxiv 2310.11324 (2024 version)
**URL**: https://arxiv.org/abs/2310.11324

GPT-3.5-turbo's performance varies by up to 40% on code translation tasks depending on prompt template alone. Sensitivity remains even with larger model size, more few-shot examples, or instruction tuning. Key finding: "LLMs are extremely sensitive to subtle changes in prompt formatting in few-shot settings."

**Relation to composition algebra**: A 40% performance variance from template formatting means the "value" of a composition operation is highly non-deterministic. The composition algebra is not a pure algebraic structure over values — it is a probabilistic operator where the distribution of outputs can shift massively from small input perturbations. This is consistent with our finding that the same prism on the same target sometimes produces 9.8/10 and sometimes triggers conversation mode.

---

## 2. Non-Commutativity in NLP Pipelines

### Finding 2.1 — Non-Commutativity is a Known, Well-Documented Phenomenon

The order-dependence literature (Section 1) collectively establishes that prompt composition is non-commutative. The specific mechanisms are:

1. **Auto-regressive position bias**: Transformers encode absolute or relative position; early tokens set interpretation frames that later tokens cannot override (primacy effect)
2. **Attention asymmetry**: The "lost in the middle" phenomenon (see 2.2) demonstrates that tokens in different positions have systematically different influence on the output
3. **Vocabulary priming**: Statistical co-occurrence patterns mean the first words in a context activate semantic neighborhoods that persist through the generation
4. **Mode triggering**: Certain vocabulary or structural patterns activate qualitatively different generation modes (planning mode, analysis mode, conversation mode) that are hard to override once established

These mechanisms are independent and additive. For a two-prompt composition A→B:
- Position bias: A's output occupies the primacy position relative to B's instructions
- Vocabulary priming: A's vocabulary creates semantic attractors that B's output gravitates toward
- Mode triggering: A's output may set a cognitive mode (e.g., "task planning" from the word "First") that persists into B's execution

**Relation to composition algebra**: These three mechanisms explain WHY audit→L12 fails while L12→audit succeeds. The audit prism output is 200-400 words of structured bug listings with phrases like "I found these issues" and "here are the problems to fix." When L12 receives this as context, it reads a task-planning document and enters planning/checklist mode, producing 18 words instead of 1,137. The vocabulary of the audit output is mode-incompatible with L12's analytical mode requirements.

---

### Finding 2.2 — The Lost in the Middle: Position Asymmetry in Context Windows

**Paper**: "Lost in the Middle: How Language Models Use Long Contexts" — *TACL* (MIT Press)
**URL**: https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00638/119630/Lost-in-the-Middle-How-Language-Models-Use-Long

Performance is highest when relevant information occurs at the beginning or end of input context; significantly degrades for middle content. Mechanistic cause: Rotary Position Embedding (RoPE) introduces a long-term decay effect. Tokens at beginning benefit from primacy effect; tokens at end benefit from recency. Middle tokens are too far from both ends.

**Relation to composition algebra**: The context window has a topological structure: beginning and end are privileged positions. In a chained pipeline where A's output is prepended to B's prompt, A occupies the beginning (highest weight) and B's instructions appear later. This means B's instructions are partially attenuated. For our pipeline: when L12's analysis precedes the audit prompt, L12's vocabulary and framing dominate the interpretation even though the audit instructions come later. This is a fundamental asymmetry of the operation — the first operand has structurally more influence than the second.

---

### Finding 2.3 — SPEAR Operator Algebra: Empirical Non-Commutativity

**Paper**: "Making Prompts First-Class Citizens for Adaptive LLM Pipelines" (SPEAR) — arxiv 2508.05012 (August 2025)
**URL**: https://arxiv.org/abs/2508.05012

The closest existing work to our algebraic formalization. SPEAR defines a prompt algebra with six operators:
- **RET[source]**: Retrieve data into context
- **GEN[label]**: Invoke LLM using current prompt + context
- **REF[action,f]**: Transform/refine prompt entries
- **CHECK[cond,f]**: Conditionally apply transformations
- **MERGE[P₁,P₂]**: Reconcile fragments from divergent branches
- **DELEGATE[agent,payload]**: Offload subtasks

The algebra is closed under composition: every operator consumes and produces (P, C, M) triple (Prompt, Context, Metadata).

**Critical empirical finding on non-commutativity**: Table 4 shows Map→Filter versus Filter→Map pipelines yield dramatically different results. Map→Filter achieves ~20% speedup at all selectivity levels. Filter→Map has no speedup benefit at low selectivity. The effect inverts based on predicate pushdown — a purely computational ordering effect.

**Algebraic properties**: Closure proven. Associativity: implicit but not formally proven. Commutativity: explicitly refuted by Table 4. Identity: no true identity element identified. Inverses: not discussed.

**Verdict**: SPEAR establishes an informal operator algebra, prioritizing practical composability over rigorous math. It is the closest existing formalization of prompt pipelines as algebraic structures, and it confirms: the algebra is a semigroup (closed, likely associative), not a group (no inverses) and not commutative.

---

### Finding 2.4 — Multi-Agent Topology: Not All Orderings Are Beneficial

**Paper**: "Multi-Agent Design: Optimizing Agents with Better Prompts and Topologies" (MASS) — arxiv 2502.02533 (2025)
**URL**: https://arxiv.org/html/2502.02533v1

Examines five agent topology classes: Aggregate (parallel + voting), Reflect (iterative self-reflection), Debate (multi-agent discussion), Custom (task-specific modules), Tool-use. Key finding: "not all topologies are beneficial to MAS design" — beneficial configurations are "only a small fraction of the overall set."

Empirical: debate benefits HotpotQA but not other tasks. The MASS framework enforces an explicit sequence rule [summarize, reflect, debate, aggregate] to manage optimization complexity. Stage-based optimization shows that optimizing components in sequence (local → global) outperforms simultaneous joint optimization.

**Relation to composition algebra**: The topology constraint [summarize, reflect, debate, aggregate] is a discovered optimal partial order — not derivable from first principles, but empirically found. This is analogous to our observation that specific pipeline orderings work (L9-B→L10-B→L11-B is "consistently strongest — operations are sequentially dependent by definition") while other orderings fail. The literature confirms: the space of valid orderings is a small fraction of the permutation space, but finding it requires empirical search, not algebraic derivation.

---

## 3. Algebraic Structure of LLM Operations

### Finding 3.1 — Topos Theory for LLMs

**Paper**: "Topos Theory for Generative AI and LLMs" — arxiv 2508.08293 (August 2025)
**URL**: https://arxiv.org/abs/2508.08293

The most mathematically ambitious treatment of LLM composition. Establishes that the category of LLMs forms a **topos** — a "set-like" category with:
- (Co)completeness: all diagrams have solutions in the form of limits and colimits
- Cartesian closure: supports exponential objects
- Subobject classifier: fundamental topos property

Novel compositional architectures derived from universal constructions: pullback, pushout, (co)equalizers, exponential objects. These are alternatives to daisy-chaining or mixture-of-experts.

**Relation to composition algebra**: Topos structure is stronger than monoid/semigroup structure — it is a full categorical framework where composition is constrained by universal properties. However, the paper addresses the *architecture* of LLM systems, not the algebra of prompt transformations within a fixed LLM. For our purposes, the relevant insight is that the category of LLMs supports exponential objects — meaning "the function from LLM-A to LLM-B" is itself an object in the category. This formally justifies the concept of a prism as a morphism: a prism is a function from input-state to output-state in the LLM category.

---

### Finding 3.2 — DSPy: Prompt Pipelines as Parameterized Programs

**Paper**: "DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines" — arxiv 2310.03714 (ICLR 2024)
**URL**: https://arxiv.org/abs/2310.03714

DSPy models LLM pipelines as "text transformation graphs" — imperative computational graphs where LMs are invoked through declarative modules. Modules are parameterized (learn their behavior through bootstrapping demonstrations within the pipeline). The compiler optimizes any DSPy program via teleprompters that determine how modules should learn from data.

Key structural insight: modules compose through arbitrary code in `forward` methods — sequential, conditional, or iterative. Ordering matters because generated queries must precede retrieval calls, and accumulated context feeds into answer generation. Constraint propagation: DSPy Assertions enable backtracking (retry individual modules on failure), but constraints don't propagate directly between sibling modules — they influence behavior through improved few-shot examples at compile time.

**Relation to composition algebra**: DSPy's architecture implies a composition algebra that is a **partially ordered monoid** — operations have dependencies (some must precede others) but within those constraints, the order can be optimized. The "compile" step is essentially discovering the optimal parametrization of each position in the ordered sequence. DSPy does not address non-commutativity at the vocabulary/framing level — it assumes the output of each module is a semantically neutral input to the next. Our finding that audit output triggers mode-switching is a layer below DSPy's abstraction.

---

### Finding 3.3 — Theoretical Framework for Prompt Engineering

**Paper**: "A Theoretical Framework for Prompt Engineering: Approximating Smooth Functions with Transformer Prompts" — arxiv 2503.20561 (March 2025)
**URL**: https://arxiv.org/html/2503.20561

Establishes a lower bound: multi-step sequential function composition requires minimum transformer size to achieve without chain-of-thought, but CoT prompting distributes computation across multiple tokens, significantly reducing parameter requirements. The key theorem: positional encoding parameter `wj` imposes hierarchical structure on the prompt, marking which stage a token belongs to.

The architecture implies sequential composition is inherently order-dependent: neural network composition is f∘g ≠ g∘f in general. The paper focuses on single-function approximation, not multi-prompt pipelines — so it does not address our specific non-commutativity problem.

**Relation to composition algebra**: Establishes the theoretical floor: even at the level of individual transformer operations, composition is non-commutative (standard result from neural network theory). Our prompt pipeline non-commutativity is a higher-level manifestation of this lower-level property.

---

### Finding 3.4 — Formal Semantics of Prompt Composition

**Paper**: "Revisiting Prompt Sensitivity in Large Language Models for Text Classification: The Role of Prompt Underspecification" — arxiv 2602.04297 (2026)
**URL**: https://arxiv.org/html/2602.04297

In-context learning can address the majority of sensitivity stemming from prompt underspecification as effectively as calibration, without needing model internals. Sensitivity is not random — it is structurally caused by underspecification: when the prompt does not uniquely determine the intended output structure, the model fills the gap with training-data priors.

**Key implication for composition algebra**: A prompt P has a "specification degree" — how precisely it constrains the output format and mode. A fully specified prompt (like our L12 with explicit section labels and operation sequence) has lower sensitivity to context contamination. An underspecified prompt is highly sensitive to the framing provided by prior context. This gives a principled explanation for why audit→L12 fails: the audit output's vocabulary fills a "specification gap" in L12, causing mode misfire.

---

## 4. Optimal Pipeline Ordering

### Finding 4.1 — No General Theory; Empirical Search is Dominant

The literature does not contain a general theory for optimal ordering of semantically distinct prompts in a pipeline. The scheduling literature (e.g., Preble, PARS, 2024) addresses *computational* scheduling (KV cache reuse, latency minimization) not *semantic* ordering (which prompt should run first for best output quality).

The MASS framework (Finding 2.4) finds that local-to-global optimization (optimize individual components first, then topology) outperforms joint optimization — suggesting the ordering problem decomposes hierarchically. But this applies to agent selection, not to the internal ordering of sequential prompt operations on the same content.

**Closest analogous result**: The NLP pipeline literature (dependency parsing, NER, co-reference) established decades ago that earlier stages gatekeep later stages: parsing errors propagate downstream and cannot be recovered. The principle "get the structurally simpler operation right before the complex one" is a common heuristic.

**Relation to composition algebra**: For our prism pipeline, an actionable heuristic emerges from the literature: place prompts that are more structurally specific and less vocabulary-sensitive earlier; place prompts that are more vocabulary-sensitive later (they can absorb framing from the earlier output). However, the converse risk is that the later prompt is mode-contaminated by the earlier one's vocabulary. The optimal ordering problem is NP-hard in the general case (it requires testing O(n!) orderings) but tractable with structural constraints.

---

### Finding 4.2 — DSPy Learns Optimal Orderings Implicitly

DSPy's MIPRO optimizer (2024) discovers optimal parametrizations of multi-step pipelines through "discrete search: sampling mini-batches, proposing combinations of instructions and traces for every prompt in the pipeline, evaluating candidate programs." This is gradient-free search over the prompt composition space.

Key insight: DSPy treats the pipeline topology (the ordering of modules) as a *given* and optimizes the content of each prompt at each position. It does not search over permutations of pipeline stages. The ordering is provided by the programmer, not discovered.

**Implication**: The literature has no automated method for discovering optimal pipeline orderings at the semantic level. The practical approach is: (1) establish structural dependencies (A must precede B if B uses A's output), (2) apply empirical heuristics about vocabulary contamination, (3) validate by running both orders on held-out examples.

---

### Finding 4.3 — Sequential Dependencies Create Partial Orders, Not Total Orders

From the MASS finding (2.4) and the DSPy composition model (3.2), the conclusion is that optimal orderings form **partial orders** (some operations must precede others) not total orders (a unique best ordering). Within the partial order, multiple valid orderings may exist with similar performance.

For our prism pipeline, this suggests:
- The L7→L8→L9→L10→L11→L12 depth stack is a total order (each level semantically requires the previous)
- The portfolio prisms (L12, audit, optimize, errres, api_surface) form a partial order (they are independent) or an anti-chain (they commute)
- The failure of audit→L12 is a violation of a partial order constraint: audit's output is not a valid input precondition for L12 in analytical mode

---

## 5. Context Contamination

### Finding 5.1 — Pattern Priming: Vocabulary Co-occurrence as Mode Trigger

**Source**: "Pattern Priming in Prompting: How to Shape LLM Output with Statistical Cues" — aightbits.com (2025)
**URL**: https://aightbits.com/2025/05/09/pattern-priming-in-prompting-how-to-shape-llm-output-with-statistical-cues/

LLMs do not execute instructions — they predict tokens. The initial context creates a probability distribution over subsequent token sequences. "Descriptor stacking" (combining related adjectives: "objective, critical, detailed, factual, technically accurate") activates familiar linguistic patterns from training data corpora. Redundancy is not wasteful — it amplifies the probability signal.

Key insight: "earlier generated content [is] increasingly influential on later predictions." As context grows, the model's behavior becomes progressively shaped by what has already been produced, regardless of whether it was accurate or relevant.

**Relation to composition algebra**: This is the mechanistic account of context contamination. When audit produces output like "I identified the following defects: 1. Missing error handling... 2. Race condition..." — this activates a statistical pattern in training data (bug lists, code review documents, task queues). The next call receives this as context and predicts tokens that follow naturally from bug lists: more bug list items, or a planning response like "I'll fix these issues." The L12 analysis mode requires a different statistical pattern (academic paper on systems structure, architectural analysis). The mismatch between the statistical pattern activated by audit output and the pattern required for L12 execution is the root cause of the 18-word collapse.

---

### Finding 5.2 — Prompt Framing Dominance: Expert Framing Bypasses Safety

**Source**: "Prompt Framing Changes LLM Performance (and Safety)" — LessWrong
**URL**: https://www.lesswrong.com/posts/RTHdQuGJeBKWHbgyj/prompt-framing-changes-llm-performance-and-safety

Prepending fixed framing phrases to prompts produces measurable differences in both performance quality and safety outcomes. "Expert framing was shown using statistical testing to increase the rate of compliance with harmful requests." Early words establish an interpretive frame that persists throughout processing.

"Taking a deep breath" is the most reliable performance-enhancing framing, improving results across multiple task types including recall and logic. Coding tasks showed strongest responsiveness to framing.

**Relation to composition algebra**: Framing is the zeroth operation in any composition. Before prism A even begins, the accumulated context from previous turns (or the structural vocabulary of A's output) establishes a framing that constrains all subsequent operations. This is consistent with our Principle 15 (code nouns are mode triggers) and Principle 16 (≤3 concrete steps = universally single-shot): both principles are about framing — controlling which statistical neighborhood the model operates in.

---

### Finding 5.3 — Context Drift in Multi-Turn Conversations

**Paper**: "LLMs Get Lost In Multi-Turn Conversation" — arxiv 2505.06120
**URL**: https://arxiv.org/pdf/2505.06120

Even high-performing models (Claude 3.7 Sonnet, Gemini 2.5, GPT-4.1) show 30-40% average degradation in multi-turn conversation quality. Degradation is independent of model size — small and large models degrade equally. Mechanism: longer sessions contain redundant information that "may negatively affect downstream tasks or subsequent memory construction."

**Relation to composition algebra**: 30-40% degradation across all models is a quantitative estimate of the "composition tax" — the performance cost of operating in a chained context rather than fresh context. Our finding that chained pipeline improves coherence from WEAK to WEAK/MODERATE (Round 27) is consistent with this: chaining helps coordinate across operations, but the context contamination imposes a ceiling on achievable quality that independent calls don't face.

---

### Finding 5.4 — The "Broken Telephone" Effect: Quantified Degradation in Iterative Chains

**Paper**: "LLM as a Broken Telephone: Iterative Generation Distorts Information" — ACL 2025
**URL**: https://arxiv.org/abs/2502.20258

Quantified information distortion in iterative translation chains. Key metrics:

**Degradation rates** (FActScore gradient per iteration):
- Latin-script language pairs (EN↔FR): -0.004 per iteration
- Non-Latin script pairs (EN↔TH): -0.015 to -0.040 per iteration

**Degradation curve shape**: Non-linear accumulation — rapid initial decline, stabilization by iteration ~100 (but at severely degraded level). This is an exponential decay to a lower floor, not linear degradation.

**Primary factors affecting degradation rate**:
1. Language (bridge) similarity: linguistically distant pairs degrade 4-10x faster
2. Chain complexity: 5-language chains average -0.038±0.02 per iteration
3. Temperature: higher temperature → greater factual and semantic degradation; temperature near 1×10⁻⁶ → near-stable
4. Prompt constraint level: constrained prompts (restrictive instructions) preserve more fidelity than simple prompts

**Mitigation**: temperature=0 + highly restrictive prompts reduces degradation substantially but cannot eliminate it entirely.

**Relation to composition algebra**: This provides the first quantitative model of the composition tax. For our chained pipeline, each step has an information fidelity of approximately 1 - gradient (gradient ≈ 0.004-0.04 per step for semantically proximal prompts). A 7-step chain (L7→L8→L9→L10→L11→L12→adversarial) with gradient 0.004 would retain ~97% fidelity; with gradient 0.04 would retain ~75% fidelity. Constrained prompts (our structural prisms with explicit section headers and operations) should be at the low end of this gradient — consistent with our finding of 93% TRUE individual quality even in chained mode (Round 27).

---

## 6. Composable AI Systems

### Finding 6.1 — DSPy: The Compiler Analogy

DSPy (ICLR 2024) is the most influential work on composable AI systems. Its core analogy: a DSPy pipeline is like a program — it has a fixed compositional structure (the module DAG) and parameterized content at each node (the prompts). The "compiler" optimizes parameters while preserving structure. Composition follows strict data dependencies.

Key architectural insight: DSPy Assertions enable local self-repair (retry on constraint violation), but do not propagate constraints globally between modules. Each module is responsible for its own output quality; the composition does not have a global repair mechanism.

**Limitation for our use case**: DSPy assumes the programmer specifies the topology. It cannot discover that audit→L12 is a bad ordering — it requires the programmer to either avoid that ordering or add an explicit intermediate transform that neutralizes the audit output's vocabulary before passing it to L12.

---

### Finding 6.2 — Agent Topologies: DAG is the Standard Model

Current agentic pipelines universally use Directed Acyclic Graphs (DAGs) as their composition model. A DAG encodes partial order constraints: if there is an edge A→B, A must execute before B. Within the partial order, topological sort produces valid orderings.

From the MASS framework: "predefined sequence [summarize, reflect, debate, aggregate]" enforces a total order on composition. Research shows this is not arbitrary — some orderings are substantially better. The search for optimal orderings is the MAS design problem.

**Key practical insight**: Building blocks (Aggregate, Reflect, Debate, Summarize, Tool-use) are not freely interchangeable. Empirically found effective total order: Summarize first (reduce context to structured form), Reflect next (identify gaps in structured form), Debate (challenge the gaps), Aggregate (synthesize the debate). This is analogous to our finding that analysis prisms must precede synthesis prisms (not the other way around).

---

### Finding 6.3 — Composition as Function Composition: The Fundamental Model

The theoretical consensus (topos theory paper, DSPy, SPEAR) treats prompt composition as function composition: prism A maps input X to output A(X). Prism B maps A(X) to B(A(X)). The composition B∘A maps X to B(A(X)).

Properties of this composition:
- **Closed**: If A and B are both valid LLM-callable prompts, B∘A is also a valid LLM-callable prompt sequence
- **Associative**: (C∘B)∘A = C∘(B∘A) — the grouping of how we sequence calls does not change the final result, only the intermediate artifacts
- **Not generally commutative**: B∘A ≠ A∘B — confirmed by all empirical work
- **No general inverse**: Given B∘A, there is no general C such that C∘B∘A = A — the "undo" operation does not exist as a prompt

This confirms the **semigroup structure** (closed, associative) and suggests it is **not a monoid** in the strict sense (no universal identity element). The identity-like behavior of "vanilla query" is only approximate — it changes outputs for some inputs.

**Exception to non-commutativity**: For independent operations (operations that access non-overlapping aspects of the input and produce non-overlapping output dimensions), empirical commutativity may hold approximately. Our portfolio prisms (claim, pedagogy, scarcity, rejected_paths, degradation) are designed to be independent — each finds different things — and should be approximately commutative in terms of which structural features they identify. The ordering matters for output-as-input chaining but not for independent parallel execution.

---

## 7. Synthesis: The Composition Algebra of Prisms

Drawing together findings across all 6 dimensions:

### 7.1 — The Structure is a Non-Commutative Semigroup (Confirmed)

The literature confirms K11's prediction: prompt composition under sequential application forms a semigroup (closed, associative) that is not a group (no general inverses). Whether it is a monoid (has an identity element) is ambiguous — approximate identities exist but no exact identity.

Key confirmation: SPEAR explicitly proves closure (every operator produces the same triple type) and empirically refutes commutativity (Map→Filter ≠ Filter→Map). The literature does not prove associativity explicitly, but it is implicit in every practical pipeline design.

### 7.2 — Non-Commutativity Has Two Distinct Sources

**Source 1: Semantic dependency** (structural). Some operations require the output of others as input. L12 must precede audit in the chained depth stack because audit needs structural findings to annotate. This is a partial order constraint that is semantically necessary and domain-stable.

**Source 2: Context contamination** (accidental). Some operation outputs contain vocabulary or framing that triggers wrong modes in downstream operations. audit→L12 fails not because of semantic dependency but because audit's vocabulary activates planning/checklist mode, overriding L12's analytical mode. This is a vocabulary-level interference effect.

These two sources are independent. Semantic dependency is predictable from the operation definitions. Context contamination is empirically discovered and depends on the specific vocabulary of each prism's output.

### 7.3 — The Composition Tax: Quantified

From the "Broken Telephone" paper (Finding 5.4):
- Information fidelity per step: 1 - (0.004 to 0.04) per iteration, depending on prompt constraint level
- Our structural prisms (with explicit section labels, defined operations) should be at the low end (~0.004/step)
- A 7-step chain retains ~97% fidelity at 0.004/step, ~75% at 0.04/step
- This is consistent with our Round 27 finding: 93% TRUE individual quality in chained mode

From multi-turn conversation degradation (Finding 5.3):
- 30-40% degradation is the upper bound for heavily contaminated contexts
- This is the auditt→L12 failure case (near-total degradation to 18 words)

### 7.4 — The "No Neutral Prompt" Problem and the Identity Element

The PLOS ONE paper (Finding 1.4) establishes "there is no neutral prompt." This formally breaks the monoid structure: there is no true identity element e such that e∘A = A for all A.

However, in practical terms, a near-identity exists: a minimal context-free query ("analyze this code") produces the lowest-variance output and is closest to the identity. The question is whether the algebra is useful as a monoid approximation — and the literature's consensus is yes (DSPy, SPEAR, and multi-agent frameworks all treat the pipeline as if it has an identity, which is the "fresh context" or "no prior prism" state).

### 7.5 — Practical Rules Derived from the Literature

1. **Check mode compatibility before composition**: Ask whether operation A's output vocabulary is mode-compatible with operation B's required input mode. Incompatibility predicts catastrophic failure (18-word output) rather than graceful degradation.

2. **Structural prisms reduce composition tax**: Prompts with explicit section headers, defined operation sequences, and constrained output formats (our prism structure) sit at the low end of the degradation gradient (~0.004/step vs ~0.04/step for unconstrained prompts).

3. **Approximate commutativity for independent operations**: Portfolio prisms that access non-overlapping aspects of the input can be run in any order (or in parallel) without significant quality loss.

4. **Position primacy is structural**: In context window composition, earlier content has more influence than later content (primacy effect + lost-in-middle). When chaining, the most influential frame-setting operation should run first.

5. **Vocabulary neutralization is the missing operation**: What the literature lacks (and our system discovered empirically) is an intermediate "vocabulary neutralizer" operation that strips mode-triggering vocabulary from one operation's output before passing to the next. This is the operation that would make the monoid closer to a group.

6. **Local-to-global optimization for pipelines**: The MASS finding that local optimization (individual component tuning) before global optimization (topology selection) outperforms joint optimization suggests: perfect each prism independently before optimizing the pipeline structure.

---

## References

1. Arxiv 2502.04134 — "The Order Effect: Investigating Prompt Sensitivity to Input Order in LLMs" https://arxiv.org/html/2502.04134v2

2. Arxiv 2406.06581 — "Order-Independence Without Fine Tuning" (NeurIPS 2024) https://arxiv.org/abs/2406.06581

3. Arxiv 2410.02185 — "POSIX: A Prompt Sensitivity Index For Large Language Models" (October 2024) https://arxiv.org/abs/2410.02185

4. PLOS ONE 2025 — "Prompt architecture induces methodological artifacts in large language models" https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0319159

5. Arxiv 2310.11324 — "Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design" https://arxiv.org/abs/2310.11324

6. Arxiv 2508.08293 — "Topos Theory for Generative AI and LLMs" (August 2025) https://arxiv.org/abs/2508.08293

7. Arxiv 2310.03714 — "DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines" (ICLR 2024) https://arxiv.org/abs/2310.03714

8. Arxiv 2312.13382 — "DSPy Assertions: Computational Constraints for Self-Refining Language Model Pipelines" https://arxiv.org/abs/2312.13382

9. Arxiv 2503.20561 — "A Theoretical Framework for Prompt Engineering: Approximating Smooth Functions with Transformer Prompts" (March 2025) https://arxiv.org/html/2503.20561

10. Arxiv 2508.05012 — "Making Prompts First-Class Citizens for Adaptive LLM Pipelines" (SPEAR, August 2025) https://arxiv.org/abs/2508.05012

11. Arxiv 2502.02533 — "Multi-Agent Design: Optimizing Agents with Better Prompts and Topologies" (MASS, 2025) https://arxiv.org/html/2502.02533v1

12. Arxiv 2502.20258 — "LLM as a Broken Telephone: Iterative Generation Distorts Information" (ACL 2025) https://arxiv.org/abs/2502.20258

13. TACL — "Lost in the Middle: How Language Models Use Long Contexts" https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00638/119630/Lost-in-the-Middle-How-Language-Models-Use-Long

14. Arxiv 2406.16008 — "Found in the Middle: Calibrating Positional Attention Bias Improves Long Context Utilization" https://arxiv.org/abs/2406.16008

15. Arxiv 2505.06120 — "LLMs Get Lost In Multi-Turn Conversation" https://arxiv.org/pdf/2505.06120

16. LessWrong — "Prompt Framing Changes LLM Performance (and Safety)" https://www.lesswrong.com/posts/RTHdQuGJeBKWHbgyj/prompt-framing-changes-llm-performance-and-safety

17. AightBits 2025 — "Pattern Priming in Prompting: How to Shape LLM Output with Statistical Cues" https://aightbits.com/2025/05/09/pattern-priming-in-prompting-how-to-shape-llm-output-with-statistical-cues/

18. Arxiv 2502.02533 — "Multi-Agent Design: Optimizing Agents with Better Prompts and Topologies" https://arxiv.org/html/2502.02533v1
