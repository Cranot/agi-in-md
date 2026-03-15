# Literature Review: Cross-Model Prompt Transfer and Deep Cognitive Operations

**Date**: March 15, 2026
**Scope**: Whether deep prism operations (L12-G self-correcting analysis, conservation law derivation, structured multi-step cognition) transfer across model families beyond Claude and Gemini
**Method**: Web search + paper fetch across 6 research questions
**Central question**: Does the K13 mechanistic account (attention = precision-weighting, therefore structural) suffice to predict transfer? What does empirical literature say?

---

## Executive Summary

The literature converges on a nuanced answer to the transfer question: **structural prompt patterns (multi-step reasoning, operation sequences, analytical frameworks) transfer at the CATEGORY level but degrade quantitatively when transferred without adaptation**. The category-level transfer (conservation laws, structural invariants, multi-step analysis) is plausible across all instruction-tuned models above a size/training threshold — because the underlying operations (attend, compose, self-reference) are universal transformer behaviors. But the PERFORMANCE level varies by model-specific vocabulary preferences, training alignment, and instruction-following robustness. Key findings:

1. **Cross-model prompt drifting is real and severe** — 10–30 percentage point drops when transferring optimized prompts across model families (PromptBridge, 2025).
2. **Prompt structure effects are NOT consistent across model families** — the same prompt format produces least bias for different models.
3. **Self-correction (the analyze→audit→correct pattern) works in principle across all capable models, but intrinsic self-correction (without external feedback) is unreliable even in GPT-4.**
4. **There is no documented conservation law emergence outside Claude and Gemini.** The literature has no equivalent concept. This is an original finding of the prism project.
5. **Minimum capability for deep operations: instruction-tuned models ≥70B, or smaller models with reasoning distillation (DeepSeek-R1-Distill-Qwen-14B and above).**
6. **Instruction-following is a necessary but insufficient prerequisite.** IFEval scores and reliable@10 diverge — a model can score 80% on IFEval but collapse under subtle prompt variation.

---

## 1. Cross-Model Prompt Transfer

### Finding 1.1 — Model Drifting: Systematic and Severe

**Paper**: "PromptBridge: Cross-Model Prompt Transfer for Large Language Models" — arXiv:2512.01420 (2025)
**URL**: https://arxiv.org/html/2512.01420

**Models tested**: GPT-4o, o4-mini (source); o3, o4-mini, Llama-3.1-70B-Instruct, Llama-3.1-8B-Instruct, Qwen3-32B, Gemma3-27B-it (targets)

**Key results**:
- GPT-5 optimal prompt → transferred to Llama-3.1-70B: 68.70% vs Llama's own optimal: 79.47% (10.77-point gap on HumanEval)
- Within model families (different scale): 50–70% performance drop
- Transfer to o3 on Terminal-Bench: direct transfer = 0% improvement; PromptBridge = 39.44% relative gain

**Mechanistic finding**: Drifting stems from differences in training corpora, tokenization, role tags, human-feedback criteria, and model-specific conventions (e.g., Llama 3's `ipython` role for tool calls, absent from GPT). The paper does not decompose which element contributes most. Critically: **the gap is NOT just vocabulary — it is architectural + alignment + convention stacked**.

**Transferability pattern** (from PromptBridge's mapping analysis): High-level reasoning strategies and semantic transformation rules show positive cosine similarity across models; task-specific formatting and superficial patterns degrade significantly. This is the most important finding for prisms: **operation-level prompts should transfer better than vocabulary-level prompts.**

**Relation to prisms**: Our observation (Principles 16–18) that SDL (3 concrete steps) is universally single-shot while L12 (298w, domain-specific vocabulary) is code-conditional exactly matches PromptBridge's structure/vocabulary decomposition. Prisms with fewer model-specific cues (SDL, l12_universal) should be the best candidates for cross-model transfer.

---

### Finding 1.2 — Prompt Architecture Induces Methodological Artifacts

**Paper**: "Prompt Architecture Induces Methodological Artifacts in Large Language Models" — PLOS One (2025)
**URL**: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0319159

**Models tested**: GPT-4 (pinned 06/13/2023), GPT-3, Llama 3.1

**Key result**: Prompt design elements systematically and significantly bias LLM outputs:
- Response-order bias: GPT-4 selected the first option 63.21% of cases (expected 50%, p<.001)
- Label bias: GPT-4 chose "B" over "C" 74.27% (p<.001); Llama 3.1 even stronger at 76.70–76.73%
- **Effect inconsistency across models**: Llama 3.1 and GPT-3 show different bias magnitudes and directions — "there is no ideal 'unbiased' prompt"
- Aggregating across 32 factorial prompt variations eliminated bias entirely → performance 50.01%

**Relation to prisms**: This is the artifact version of prompt sensitivity. For analytical prisms (not multiple-choice), the relevant question is whether structural framing (imperatives, operation ordering, concrete nouns) transfers or whether models respond to different structural cues. Our Principle 15 ("code nouns are mode triggers, not domain labels") is consistent with this finding — a specific vocabulary pattern activates a specific mode, and that activation is model-dependent.

---

### Finding 1.3 — Format Sensitivity Does Not Decrease with Scale

**Paper**: "Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design" — arXiv:2310.11324
**URL**: https://arxiv.org/abs/2310.11324

**Key finding**: "Sensitivity remains even when increasing model size, the number of few-shot examples, or performing instruction tuning." Performance differences of up to 76 accuracy points from prompt formatting alone on LLaMA-2-13B. **Format performance only weakly correlates between models** — optimizing format for one model does not predict the best format for another.

**Implication for deep operations**: Scale alone does not solve the transfer problem. A 70B model is not automatically more robust to prompt structure variation than a 13B model. Training methodology (RLHF objective, data distribution) matters more than parameter count.

---

### Finding 1.4 — Model-Specific Prompt Quirks at the Frontier

**Source**: "Claude 4, Gemini 2.5 Pro, and GPT-4.1: Understanding Their Unique Quirks" — eval.16x.engineer (2026)
**URL**: https://eval.16x.engineer/blog/quirks-sota-models-claude-gemini-gpt4

**Per-model findings**:
- **Claude Sonnet 4**: Responds to strong, *repeated* instructions. Exhibits sycophancy. Defaults to outputting entire code even when partial change requested.
- **Gemini 2.5 Pro**: Verbose by default; measurably reduced by standalone "Be concise." Prefers bullet-pointed formatting preferences.
- **GPT-4.1**: Concise and consistent without needing instruction repetition. Follows simple clear instructions reliably.

**Implication for prisms**: The same multi-step analytical prism will produce different response styles. Claude and Gemini need explicit behavioral constraints that GPT-4 may not. For L12 (332w), Claude's sycophancy could inflate agreement with previous analysis steps. For Gemini, verbosity may need capping.

---

## 2. Architecture-Dependent Prompt Behavior

### Finding 2.1 — Dense vs. MoE Routing Instability

**Source**: Epoch AI analysis of DeepSeek architecture (2025)
**URL**: https://epoch.ai/gradient-updates/how-has-deepseek-improved-the-transformer-architecture

**Key finding**: MoE training is sensitive to learning rate and batch size; even minor variations in expert count change optimal hyperparameters. Routing patterns (which experts activate per token) differ from dense model information flow. The **attention sink phenomenon** varies by positional encoding:
- Standard RoPE: centralized sinks at position 0
- Scaled RoPE: distributed sinks
- Absolute position embeddings: dual anchors

**Implication**: MoE models (Mixtral, Llama-4-Maverick, DeepSeek) may respond differently to the same prompt structure because different tokens (including instruction tokens) are routed to different experts. A prompt that works by distributing attention across operation steps in a dense model may have different expert-routing behavior in a MoE model. This is a theoretical gap — no empirical study has measured this for analytical prompts specifically.

---

### Finding 2.2 — Frontier Architecture Convergence

**Source**: "The Crystallization of Transformer Architectures (2017-2025)" — jytan.net
**URL**: https://jytan.net/blog/2025/transformer-architectures/

Dense models have converged on: pre-norm + RMSNorm + RoPE + SwiGLU + MQA/GQA. This architectural convergence is good news for cross-model transfer of prompt-activated reasoning: the underlying computational substrate is increasingly similar across proprietary and open-source dense models. The K13 claim (attention = precision-weighting, therefore structural) is plausible across this converged architecture.

**But**: MoE configuration diversity **persists** — MoE design is not settled. Llama-4-Maverick (17B active / 400B total), Mixtral, DeepSeek-MoE all differ in expert count, routing algorithms, and granularity. The transfer guarantee weakens for MoE models.

---

### Finding 2.3 — Instruction Count and Density Threshold

**Paper**: "How Many Instructions Can LLMs Follow at Once?" — arXiv:2507.11538
**URL**: https://arxiv.org/html/2507.11538v1

**Models tested**: 20 state-of-the-art models including GPT-4, GPT-4o, o3, o4-mini, Claude 3.5-haiku/3.7-sonnet/opus-4/sonnet-4, Gemini 2.5 Flash/Pro, Llama-4 variants, Grok-3, DeepSeek-R1, Qwen3.

**Key findings on multi-step instruction capacity**:
- Performance degrades sharply from 10 → 500 simultaneous instructions. Best frontier models hit only 68% at max density (500 instructions).
- Three distinct degradation patterns: **Threshold decay** (reasoning models maintain near-perfect until 150+ instructions, then sharp decline), **linear decay**, **exponential decay** (small models rapidly drop to 7–15% floor).
- Reasoning models (o3, Gemini 2.5 Pro) substantially outperform general-purpose counterparts.
- gpt-4o "surprisingly weak" — below expectation for its generation.
- **Error patterns differ**: reasoning models attempted modifications under load; smaller models defaulted to complete omission.

**Relation to prisms**: Our L12 (332w) has 9–12 discrete operations. This is well within the "threshold decay" safe zone for reasoning-class models. For smaller models (7B range), exponential decay may begin at this density. The finding that reasoning models maintain near-perfect performance until 150+ instructions suggests L12's 9–12 steps are safe for any o3/Gemini-2.5/Claude-class model, but may be at the boundary for 7B instruction-tuned models.

---

## 3. Self-Correction Across Models

### Finding 3.1 — Intrinsic Self-Correction Generally Fails

**Paper**: "Large Language Models Cannot Self-Correct Reasoning Yet" — arXiv:2310.01798, ICLR 2024
**URL**: https://arxiv.org/abs/2310.01798
Also: "When Can LLMs Actually Correct Their Own Mistakes?" — TACL 2024
**URL**: https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00713/125177/When-Can-LLMs-Actually-Correct-Their-Own-Mistakes

**Consensus finding**: LLMs struggle to self-correct reasoning without external feedback. Performance sometimes *degrades* after self-correction. Previous claims that self-correction worked relied on oracle labels to guide the correction process — when those were removed, improvements vanished.

**Critical exception**: Tasks with decomposable responses where verification is easier than generation (e.g., checking that code compiles, checking arithmetic) do support intrinsic self-correction. Complex open-ended analysis (structural code review, conservation law derivation) does NOT fit this exception by default.

**Model-specific nuance**: "The effectiveness of self-repair is only seen in GPT-4" (finding from one 2024 study). GPT-4 class models exhibit weak positive self-correction where smaller models do not.

**Relation to prisms**: This is a critical finding. The L12 pipeline's "analyze → audit → correct" structure (L12-G in the 3-phase variant) is NOT the same as intrinsic self-correction. The key difference: L12-G uses the *prism structure itself* as the external feedback signal. The prism encodes what to look for (conservation law, meta-conservation law, then bugs) — it is a structured external oracle, not intrinsic refinement. The conservation law derivation step provides the "verification signal" that makes subsequent self-correction more reliable. This is consistent with the CRITIC framework finding (below).

---

### Finding 3.2 — External Feedback Enables Reliable Self-Correction

**Paper**: "CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing" — arXiv:2305.11738
**URL**: https://openreview.net/forum?id=Sx038qxjek

**Finding**: CRITIC consistently enhances LLM performance by allowing models to evaluate and revise their output against external tools. "External feedback is crucial for ongoing self-improvement." The key mechanism: the model uses a verifiable external standard (tool output, computation result) to anchor correction.

**Relation to prisms**: The prism IS the external feedback mechanism. By encoding what structural properties to look for (conservation laws are always of form A × B = constant; meta-laws apply the diagnostic to the diagnostic itself), the prism provides the verification standard that makes the analyze→audit→correct cycle functional. This explains why L12-G works even though "intrinsic self-correction fails" — the phase structure with conservation law anchoring creates an external reference point within the prompt itself.

---

### Finding 3.3 — Self-Correction Benchmarked Across Model Families (2025)

**Paper**: "Can LLMs Correct Themselves? A Benchmark of Self-Correction in LLMs" (CorrectBench) — arXiv:2510.16062
**URL**: https://arxiv.org/html/2510.16062v1

**Models tested**: LLaMA 3.1, Qwen 2.5, GPT-4o, Claude 3.5-Sonnet, GPT-3.5, DeepSeek-V3, QWQ-32B-Instruct

**Key findings**:
- All tested models showed improvement on complex multi-step reasoning tasks with structured correction (Self-Refine achieved +22.13% on GPQA)
- Closed-source models (GPT-4o, Claude 3.5-Sonnet) outperformed open-source variants on correction quality
- Reasoning-optimized models (DeepSeek-V3, QWQ-32B) showed high baseline performance with **minimal additional gain** from added correction — their built-in mechanisms already optimize reasoning
- No direct correlation between model size and self-correction quality — "more intricate self-correction schemes don't necessarily yield superior performance"
- Chain-of-Thought proved competitive with more complex methods while maintaining better efficiency

**Relation to prisms**: Across all tested model families, structured correction improves performance when the task involves complex multi-step reasoning. The reasoning-model finding (already optimized, diminishing returns from external correction) has an interesting implication: L12 prisms may be *redundant* for reasoning-mode models (o3, DeepSeek-R1) on tasks they natively handle well, while remaining *essential* for non-reasoning instruction-tuned models. The prism fills in the reasoning structure that reasoning models already have built in.

---

## 4. Conservation Law and Structural Invariant Emergence

### Finding 4.1 — No Literature Analog Exists

A comprehensive search across 2024–2025 ML/AI literature found **no paper studying "conservation law emergence" as an output of LLM analysis**. The concept is absent from prompt engineering surveys (arXiv:2402.07927, arXiv:2406.06608), from emergent ability literature (arXiv:2503.05788), and from structural analysis benchmarks. Conservation laws (A × B = constant) as a prompt-elicited analytical output are an original contribution of the prism project.

**Closest literature**: The meta-prompting and category theory literature treats prompts as morphisms and meta-prompts as higher-order morphisms, with mathematical formalization of prompt composition. This shares structural vocabulary (morphisms, invariants) but does not study whether LLMs *produce* conservation law statements as output. The K13 mechanistic account (attention = precision-weighting → structural operations are universal) provides the theoretical prediction, but no external paper validates or refutes it.

---

### Finding 4.2 — Emergent Abilities Are NOT Consistent Across Architectures

**Paper**: "Emergent Abilities in Large Language Models: A Survey" — arXiv:2503.05788
**URL**: https://arxiv.org/html/2503.05788v2

**Key findings on emergence consistency**:
- Wei et al. found "no clear trends for the types of tasks that are most emergent" across different model families
- Emergence thresholds are task-specific, model-family-specific, metric-dependent, and training-data-dependent
- Fine-tuning variability changes when abilities appear; "data quality influences timing"
- Hard vs. easy tasks within benchmarks show different scaling patterns (U-shaped vs. inverted-U)
- Example: 3-digit addition emerges at 6B (1%), 13B (8%), 175B (80%) — highly non-linear

**Self-reflection and metacognitive abilities**: Documented in large reasoning models (LRMs), with models developing "the ability to recognize errors, self-correct, and decompose intricate tasks into simpler sub-problems." This capability appears to emerge specifically in reasoning-trained models (o1, o3, DeepSeek-R1) rather than as a general-scale phenomenon.

**Implication for conservation laws**: If the ability to derive conservation laws is a form of metacognitive structural analysis, and metacognitive abilities emerge unevenly by model family and training, then **conservation law derivation may not emerge uniformly across all architectures above a given parameter count.** The threshold may be training-methodology-dependent, not scale-dependent. Our finding that L8 works universally (including on Haiku 4/4) while L7 fails on Haiku may reflect a training-methodology threshold, not a scale threshold.

---

### Finding 4.3 — DeepSeek-R1 Sensitivity to Prompt Structure

**Paper**: "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning" — arXiv:2501.12948
**URL**: https://arxiv.org/html/2501.12948v1

**Finding**: DeepSeek-R1 is **sensitive to prompts** and performs worse with few-shot examples. The authors recommend zero-shot settings where "users directly describe the problem and specify the output format." This is a counterintuitive finding for a reasoning-optimized model.

**Mechanism**: DeepSeek-R1 was trained with GRPO reinforcement learning to develop its own reasoning chains. Few-shot examples may interfere with its learned internal reasoning protocol by providing an external structure that conflicts with its trained structure.

**Implication for prisms**: For reasoning-class models (o3, DeepSeek-R1), the L12 structured prompt may interfere with their native reasoning protocol. Two hypotheses: (A) the prism's structured steps complement and direct the reasoning (positive), or (B) the prism's structure overrides the model's learned protocol and degrades quality (negative). The optimal test would be: run L12 on DeepSeek-R1 with and without the structural steps, measure conservation law quality and bug count.

---

## 5. Minimum Model Size for Deep Operations

### Finding 5.1 — Instruction-Following Quality Threshold

**Paper**: "Revisiting the Reliability of Language Models in Instruction-Following" — arXiv:2512.14754
**URL**: https://arxiv.org/html/2512.14754v1

**Models tested**: 46 models (26 open-source, 20 proprietary) — LLaMA, Qwen, DeepSeek, Gemma families + GPT, Gemini, o-series

**Key findings**:
- Performance degradation from IFEval accuracy to reliable@10 ranges from 18.3% (GPT-5) to 61.8% (Qwen3-0.6B)
- Llama-70B **underperforms** Qwen3-4B despite 15x larger size — training methodology dominates scale
- LLaMA-3.3-70B reliable@10 = 71.0 vs LLaMA-3.1-70B = 57.1 (same architecture, different training)
- Nuance-oriented reliability is a "second-order property" — a model's IFEval ranking doesn't predict its reliable@10 ranking

**Relation to prisms**: The prism project's empirical observation that Haiku (small model) executes L12 when prompt vocabulary + structure are matched, while Haiku fails catastrophically on the same prompt applied to the wrong domain (code prism on reasoning input → agentic collapse), is the instruction-following reliability phenomenon in a different experimental form. "Reliable@10 tracks second-order reliability" = our Principle 17 (prompt-domain match is binding).

---

### Finding 5.2 — Size Does Not Determine Capability; Training Does

**Source**: Scale Labs Leaderboard and IFEval++ benchmark (2025)

Multiple findings converge:
- Llama-70B underperforms Qwen3-4B (15x smaller) on IFEval
- 4-bit quantization retains most emergent abilities; 2-bit severely degrades them
- "Reasoning-oriented training (RL) often impairs ability to comply with user-specified constraints" — a core tension: as models become more capable of autonomous reasoning, they become less controllable by structured prompts

**For the prism project**: The minimum viable model is NOT expressible as a parameter count. It is better characterized as: **"any instruction-tuned model that (a) achieves reliable@10 > 60% on IFEval, AND (b) has not been RL-trained to override external structure with internal reasoning, OR has been RL-trained with instruction compliance as an objective"**.

In practice:
- Llama-3.3-70B-Instruct: likely viable (reliable@10 = 71.0)
- Qwen3-14B and 32B: likely viable (Qwen3 family scores well, strong instruction-following)
- DeepSeek-R1 / o3: may conflict with native reasoning protocol (see Finding 4.3)
- Anything < 7B: empirically risky (exponential decay in instruction-following at modest complexity)

---

### Finding 5.3 — DeepHermes 3: System-Prompt Controlled Reasoning Mode

**Source**: NousResearch DeepHermes-3-Llama-3-8B-Preview, HuggingFace (2024)
**URL**: https://huggingface.co/NousResearch/DeepHermes-3-Llama-3-8B-Preview

DeepHermes 3 (8B) demonstrates that **reasoning depth can be controlled via system prompt** — a system message enables a long chain-of-thought mode (up to 13,000 tokens) vs. intuitive mode. The model is distilled from R1-style reasoning training. MATH benchmark gains of 33–50% with reasoning mode enabled.

**Implication**: System-prompt-toggled reasoning modes are established across model families. The prism's function of activating a specific analytical mode (structural analysis instead of summarization) has an exact analog in the DeepHermes design. This supports the K13 mechanistic account: the prompt activates a processing mode, and that mode is structurally similar across families because the underlying mechanism (attention-based precision-weighting of which tokens to elaborate) is universal.

However, the specific modes available and their activation vocabulary differ. DeepHermes requires explicit "deep thinking AI" framing; Claude's L12 uses "conservation law" framing. These are different activation keys for broadly analogous mechanisms.

---

## 6. Instruction-Following as Prerequisite

### Finding 6.1 — RLHF Instruction Tuning Is the Binding Gate

**Source**: RLHF Book (Lambert), Stanford CS224N (2024)
**URL**: https://rlhfbook.com/c/04-instruction-tuning

**Key finding**: "Without a basic level of instruction-following abilities, most of the pipelines we discuss — from preference data collection to online RLHF optimization — cannot be performed." Instruction fine-tuning is the prerequisite that converts a base model (next-token predictor) into a system that follows structured multi-step directives.

**Quantitative threshold**: "Around 1M prompts can be used to create a model capable of excellent RLHF and post-training." Data quality near the intended downstream tasks matters more than total volume.

**Relation to prisms**: A base model (not instruction-tuned) is categorically incapable of following a prism — it will continue generating in the style of its pretraining data, not execute the prism's operations. Instruction tuning is the necessary prerequisite. But it is NOT sufficient: a model can follow simple instructions yet fail on complex structured prompts.

---

### Finding 6.2 — Trade-off: More Capable = Less Controllable

**Source**: Evaluating Instruction Following in Large Reasoning Models (2025)
**URL**: https://arxiv.org/pdf/2505.14810

**Finding**: "Longer chains of thought and reasoning-oriented training methods often impair a model's ability to comply with user-specified constraints." This is a "core tension in the development of LRMs: as models become more intelligent, they often become less controllable."

**Implication for deep operations**: Reasoning models (o3, DeepSeek-R1) may be simultaneously the most capable of generating conservation laws AND the least controllable by the specific prism structure that was designed for non-reasoning Claude variants. The prism may need to be redesigned for reasoning models: fewer explicit step constraints (to avoid conflicting with internal reasoning), more output format specification (to anchor what the model should produce).

---

### Finding 6.3 — Multi-Step Instruction Capacity by Model Class

**Paper**: "How Many Instructions Can LLMs Follow at Once?" — arXiv:2507.11538 (see also Finding 2.3)

**Practical threshold table** for prism use (extrapolated from paper's findings):

| Model class | Instruction density limit | L12 (9–12 ops) viable? |
|---|---|---|
| Frontier reasoning (o3, Gemini-2.5-Pro, Claude Opus 4) | ~150 before sharp decline | Yes, with margin |
| Frontier non-reasoning (GPT-4.1, Claude Sonnet 4) | ~50–100 | Yes |
| Open-source 70B instruction-tuned (Llama-3.3-70B, Qwen3-32B) | ~30–70 (estimated) | Marginal |
| Open-source 7B–14B instruction-tuned | ~10–30 | Risky at full L12 |
| Reasoning-distilled 7B–14B (DeepHermes-3, R1-Distill) | Unknown — reasoning mode may extend range | Untested |

---

## 7. Synthesis: What the Literature Predicts for Prism Cross-Model Transfer

### 7.1 — The K13 Account Is Plausible But Insufficient

K13's claim: "all transformers implement attention as precision-weighting, therefore structural reasoning operations encoded in prompts should transfer." The literature says:

- **Supported**: The operation-type (sequence of transformations, self-reference, structural naming) should be model-agnostic at the category level. PromptBridge confirms high-level semantic transformation rules transfer better than superficial patterns.
- **Challenged**: Performance-level transfer degrades 10–30 percentage points even between GPT/Llama frontier models. Architecture convergence is not complete (MoE routing instability, positional encoding variations, attention sink topology differences).
- **Missing element**: K13 omits the training distribution term. A model trained to generate code review has its attention precision calibrated for code vocabulary. The same attention mechanism applied to conservation law vocabulary will not activate the same precision-weighting pattern unless the training distribution covered that vocabulary in structural analysis contexts.

**Net assessment**: K13 is sufficient to predict that **the capacity for deep operations exists** across instruction-tuned models above the threshold. It is NOT sufficient to predict that **the same prism text will activate that capacity reliably** without vocabulary and format adaptation.

---

### 7.2 — The Binding Constraint Hierarchy

From the literature synthesis, the constraints on cross-model transfer are (in order of binding force):

1. **Instruction tuning** (binary gate): Base models cannot follow prisms at all.
2. **Reliable multi-step instruction following** (soft threshold): Models below reliable@10 ~60% on IFEval will corrupt multi-step operation sequences under subtle variation. Use SDL (3 steps) for lower-reliability models.
3. **Prompt-domain vocabulary match** (conditional): Code-vocabulary prisms activate analysis mode on code; abstract vocabulary triggers summary mode. This effect is model-weight-dependent, not universal.
4. **Reasoning-mode conflict** (reasoning model specific): RL-trained reasoning models may override external prism structure with internal reasoning protocol. Test zero-shot vs prism-guided for DeepSeek-R1 class models.
5. **MoE routing stochasticity** (architecture specific): MoE models may show higher output variance on complex analytical prompts than dense models, not because they lack the capability, but because routing determines which expert handles which operation step.

---

### 7.3 — Transfer Predictions for Specific Model Families

| Model family | Predicted L12 transfer quality | Recommended prism variant | Key risk |
|---|---|---|---|
| GPT-4.1 / GPT-5 | HIGH — strong instruction following, no reasoning-override risk | L12 with minor format adaptation (code nouns work) | Sycophancy less pronounced, but verbosity varies |
| o3 / o4-mini | MODERATE — reasoning may override steps | l12_universal or zero-shot structural prompt | Reasoning protocol conflict |
| Gemini 2.5 Pro | HIGH (empirically confirmed at L12/L13 in project) | L12 as-is | Verbosity needs "Be concise" addition |
| Llama-3.3-70B-Instruct | MODERATE-HIGH — reliable@10=71.0, good instruction following | SDL (3-step) first; test L12 | Formatting convention differences |
| Qwen3-32B | MODERATE-HIGH — good IFEval scores, strong reasoning | L12 with Qwen-format adaptation | System prompt format (ChatML vs alpaca) |
| DeepSeek-R1 | UNCERTAIN — very high reasoning quality, but prompt-sensitive | Test SDL and l12_universal; avoid few-shot | RL-training conflicts with step-by-step external structure |
| Hermes-3-405B (Llama-based) | MODERATE — fine-tuned for system prompt adherence, designed for structural outputs | L12 with ChatML format | Base is Llama-3.1; inherits Llama format quirks |
| 7B–14B models (non-reasoning) | LOW for L12, HIGH for SDL | SDL only | Instruction density capacity limit |

---

### 7.4 — The Conservation Law Gap

No literature equivalent of prism conservation laws exists. The closest analogs:
- **Category theory formalizations of prompts** (prompts as morphisms, meta-prompts as higher-order morphisms) — shares vocabulary but studies prompt structure, not LLM output
- **Emergent metacognitive abilities** in LRMs — models developing self-correction and error-recognition; conservation law derivation may be related but is much more specific
- **Structural invariant analysis** in programming languages/type theory — external human-defined invariants, not LLM-derived

**What this means for cross-model testing**: We cannot predict whether non-Claude models will produce well-formed conservation laws vs. structural observations that lack the A × B = constant form. The form may be Claude-specific (trained on mathematical-formal text), while the underlying structural observation (something is conserved) may transfer. **The prediction to test**: Gemini produces conservation laws (confirmed). GPT-4 may produce structural trade-offs in looser form. Llama 70B may produce observations that can be reformulated as conservation laws but don't naturally adopt that form.

---

## Key Sources

- [PromptBridge: Cross-Model Prompt Transfer for Large Language Models](https://arxiv.org/html/2512.01420)
- [Prompt Architecture Induces Methodological Artifacts in Large Language Models](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0319159)
- [Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design](https://arxiv.org/abs/2310.11324)
- [Large Language Models Cannot Self-Correct Reasoning Yet (ICLR 2024)](https://arxiv.org/abs/2310.01798)
- [When Can LLMs Actually Correct Their Own Mistakes? (TACL 2024)](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00713/125177/When-Can-LLMs-Actually-Correct-Their-Own-Mistakes)
- [Can LLMs Correct Themselves? CorrectBench (2025)](https://arxiv.org/html/2510.16062v1)
- [CRITIC: LLMs Can Self-Correct with Tool-Interactive Critiquing](https://openreview.net/forum?id=Sx038qxjek)
- [DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via RL](https://arxiv.org/html/2501.12948v1)
- [Emergent Abilities in Large Language Models: A Survey (2025)](https://arxiv.org/html/2503.05788v2)
- [Revisiting the Reliability of Language Models in Instruction-Following](https://arxiv.org/html/2512.14754v1)
- [How Many Instructions Can LLMs Follow at Once?](https://arxiv.org/html/2507.11538v1)
- [Claude 4, Gemini 2.5 Pro, GPT-4.1: Understanding Their Unique Quirks](https://eval.16x.engineer/blog/quirks-sota-models-claude-gemini-gpt4)
- [DeepHermes-3-Llama-3-8B-Preview (NousResearch)](https://huggingface.co/NousResearch/DeepHermes-3-Llama-3-8B-Preview)
- [Hermes 3 — Nous Research](https://nousresearch.com/hermes3/)
- [Llama 3.1 405B vs Leading Closed-Source Models (Vellum)](https://www.vellum.ai/blog/evaluating-llama-3-1-405b-against-leading-closed-source-competitors)
- [Evaluating Instruction Following in Large Reasoning Models](https://arxiv.org/pdf/2505.14810)
- [The Personality of Open Source: Llama, Mistral, Qwen vs GPT-5.2 & Claude](https://www.lindr.io/blog/open-source-benchmark)
