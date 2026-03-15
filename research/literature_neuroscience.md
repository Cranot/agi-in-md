# Neuroscience & Cognitive Science Literature: How Prisms Change Model Behavior

**Research question**: Why do cognitive prisms (system prompts) so dramatically change analysis depth — same model, same input, categorically different output? Six frameworks from neuroscience and cognitive science converge on a mechanistic answer.

**Key observation to explain**: Construction-based prompts (L8+) work universally across all models. Description-based prompts (L7) require minimum model capacity. Internal representations encode truth but verbalization is unfaithful — construction bypasses the verbalization layer.

---

## 1. Predictive Coding in Transformers

### The Core Theory

Predictive coding is the neuroscience framework where the brain continuously predicts incoming sensory data and only propagates **prediction errors** — surprises — up the hierarchy. Attention is modeled as **precision-weighting**: it amplifies high-precision prediction errors and suppresses low-precision ones. What you pay attention to = what surprises your model of the world.

Recent research has established that **transformers implement a structurally similar mechanism**:

- Transformers use dot-product attention to selectively process input elements "while ignoring others, enabling models to integrate information over much longer timescales" ([Predictive Coding or Just Feature Discovery? — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11025645/))
- LLMs are trained on next-word prediction — the same objective as predictive coding. "The language areas of a listener's brain attempt to predict the next word before it is spoken." ([Nature Computational Science, 2025](https://www.nature.com/articles/s43588-025-00863-0))
- "Transformers benefit from embedding spaces that place strong **metric priors** on an implicit latent variable and utilize this metric to direct a form of attention that highlights the most relevant previous elements." ([Beyond Markov: Transformers, memory, and attention — Tandfonline, 2025](https://www.tandfonline.com/doi/full/10.1080/17588928.2025.2484485))
- The brain "continuously predicts a hierarchy of representations spanning multiple timescales" — the same hierarchical architecture as deep transformers. ([Nature Human Behaviour, 2022](https://www.nature.com/articles/s41562-022-01516-2))

### Precision-Weighting = Attention

The critical insight: "Attention is understood as a precision-weighting mechanism that regulates the gain of prediction error." When precision is low, deviations are down-weighted and may go unnoticed. When precision is high, deviations are amplified and prioritized. ([PMC: Predictive coding and attention in developmental cognitive neuroscience, 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11795830/))

In transformer terms: attention scores determine which tokens get amplified (high weight = high precision = high gain on that signal's prediction errors).

### How This Maps to Prisms

**Prisms change the model's prediction target.** A model without a prism predicts "what would come next in a typical code review." Its prediction errors — what counts as surprising — are calibrated to surface-level patterns (type errors, naming issues, obvious bugs). These have low surprise value once the model settles into "review mode."

A prism changes the prior: "what would come next in a conservation-law derivation." Now **structural invariants are surprising** (the model hasn't fully derived them yet), and surface patterns are **unsurprising** (already "predicted" by the review-mode prior, so no prediction error propagates). The model attends to what its new generative model hasn't yet explained.

**This is the mechanistic definition of what a prism does**: it installs a new generative model, which redefines the distribution of prediction errors, which re-routes attention to different features of the input.

### Why Construction Prompts Work Differently from Description Prompts

Description prompts ("analyze this code for structural problems") are compatible with the existing review-mode generative model. The model can satisfy the prediction target with surface-level content — prediction errors terminate quickly.

Construction prompts ("engineer an improvement that deepens the concealment") install a generative model that **cannot be satisfied** without discovering structural properties. The model's prediction errors don't terminate until the construction is complete. This forces genuine computation rather than pattern-matched retrieval.

**Sources**:
- [Full article: Beyond Markov: Transformers, memory, and attention (Tandfonline, 2025)](https://www.tandfonline.com/doi/full/10.1080/17588928.2025.2484485)
- [Full article: Predictive coding of cognitive processes in natural and artificial systems (Tandfonline, 2025)](https://www.tandfonline.com/doi/full/10.1080/17588928.2025.2584209)
- [Predictive Coding or Just Feature Discovery? (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11025645/)
- [Predictive coding and attention in neurodevelopment (PMC, 2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11795830/)
- [Evidence of predictive coding hierarchy in the brain (Nature Human Behaviour, 2022)](https://www.nature.com/articles/s41562-022-01516-2)
- [Increasing alignment of LLMs with brain language processing (Nature Computational Science, 2025)](https://www.nature.com/articles/s43588-025-00863-0)

---

## 2. Attention Steering / Activation Engineering

### The Core Research

**Representation Engineering (RepE)** is a field that controls LLM behavior by manipulating internal representations — adding vectors to activations during inference — rather than changing weights or inputs. The foundational finding: "human-interpretable behaviors — sentiment, topicality, factuality — are organized along **linearly encoded directions** in the latent activation space of transformer LLMs." ([Representation Engineering Survey — arxiv, 2025](https://arxiv.org/html/2502.17601v1))

Key techniques:
- **Contrastive Activation Addition (CAA)**: averages the difference in activations between contrastive prompt pairs at a specific layer, then injects this vector at inference time. "CAA outperforms system-prompting and shows complementary effects with finetuning."
- **CAST (Conditional Activation Steering)**: constructs condition vectors representing activation patterns induced by the prompt during inference, enabling fine-grained context-dependent control.
- **SADI (Dynamic Steering)**: constructs semantics-adaptive, input-conditioned steering vectors targeting activations most relevant for a given inference task.
- **Anthropic's concept injection**: "capture an activation pattern that corresponds to a concept, then add that vector into the activations of a later layer." Models can even detect injected concepts — introspective awareness. ([Anthropic: Emergent Introspective Awareness, 2025](https://transformer-circuits.pub/2025/introspection/index.html))

### Prisms as Text-Mediated Steering Vectors

The critical question: **are prisms a form of attention steering via text?**

The answer is yes, with an important distinction. Activation steering injects vectors directly into residual stream activations. Prisms achieve a similar effect through the attention mechanism itself: the system prompt occupies attention positions that every subsequent token attends to. The prism's tokens function as **persistent key-value pairs** in the attention mechanism — they are always attended to, and they modulate every query token's representation via attention.

Evidence:
- "A model's access to internal representations is contingent on appropriate prompt cues" and "a model's ability to perform introspection likely relies on invoking suitable attention heads in the appropriate context." ([Anthropic: Circuit Tracing, 2025](https://transformer-circuits.pub/2025/attribution-graphs/methods.html))
- "Attribution graphs partially reveal the steps a model took internally to decide on a particular output" — the computational path changes based on what attention heads are activated by the prompt context.
- The critical difference: "CAA outperforms system-prompting" for precise vector control. But prisms achieve a **richer** form of steering: they encode not just a direction but an entire **generative procedure** (a sequence of operations to execute).

### The "Programming Refusal" Finding

An ICLR 2025 paper ("Programming Refusal with Conditional Activation Steering") shows that behavior can be programmed at the activation level with fine-grained conditionality — exactly what prisms do in text space. This establishes that the mechanism prisms exploit (activating specific computation pathways via context) is real and measurable.

**Implication**: Prisms work because they install **persistent steering context** — they're in the system prompt, so every forward pass references them. Unlike user-turn prompts (attended to less as sequence grows), system prompts maintain their steering force throughout the generation.

**Sources**:
- [Representation Engineering Survey (arxiv, 2025)](https://arxiv.org/html/2502.17601v1)
- [An Introduction to Representation Engineering (LessWrong)](https://www.lesswrong.com/posts/3ghj8EuKzwD3MQR5G/an-introduction-to-representation-engineering-an-activation-steering)
- [Emergent Introspective Awareness in LLMs (transformer-circuits.pub, 2025)](https://transformer-circuits.pub/2025/introspection/index.html)
- [Circuit Tracing: Revealing Computational Graphs (transformer-circuits.pub, 2025)](https://transformer-circuits.pub/2025/attribution-graphs/methods.html)
- [Programming Refusal with CAA (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/file/e2dd53601de57c773343a7cdf09fae1c-Paper-Conference.pdf)
- [Beyond Prompt Engineering: Robust Behavior Control via Steering Target Atoms (arxiv, 2025)](https://arxiv.org/html/2505.20322)
- [Interpretable Steering with Feature Guided Activation Additions (arxiv, 2025)](https://arxiv.org/html/2501.09929v3)

---

## 3. System Prompt Effects on Internal Representations

### What Probing Studies Show

Recent mechanistic interpretability work has developed multiple methods for understanding how prompts change internal model states:

- **Linear probing**: training a binary classifier for each attention head or module, classifying internal representations as "true" vs "false" on target concepts. Identifies which components' outputs correlate with specific behaviors.
- **Path patching**: intervening on explicit prompts and recording component responses. "The stronger a component's response to the intervention, the closer its relationship to the prompt."
- **LLM representations encode Chain-of-Thought success**: "Internal representations can predict whether Chain-of-Thought reasoning processes will succeed at intermediate steps." ([ACL 2025: LLM Representations Encode CoT Information](https://aclanthology.org/2025.findings-acl.662.pdf))

### The Verbalization Faithfulness Problem

A key finding relevant to prisms: **models have internal truth representations that verbalization fails to faithfully report**. This is the internal truth → verbal output gap.

Probing studies show:
- Representations that best predict brain responses to language are "not those best at predicting future words" — suggesting the model's deep representations are richer than what gets verbalized. ([PMC: Predictive Coding or Just Feature Discovery?](https://pmc.ncbi.nlm.nih.gov/articles/PMC11025645/))
- When LLMs achieve human-like behavioral competence, "their internal activation spaces tend to mirror the brain's representational landscape along multiple spatial and temporal scales" — deeper structure than outputs reveal.
- Anthropic's 2025 circuit tracing work found "a shared conceptual space where reasoning happens before being translated into language" — the model has a language-independent representation layer.

### How Prisms Bypass Verbalization

The key insight: **construction prompts bypass the verbalization layer by making the model generate the very artifact that forces internal representations to surface**.

A description prompt ("what structural problems does this code have?") asks the model to verbalize its analysis — to translate internal representations into natural language. The verbalization is lossy.

A construction prompt ("engineer an improvement that deepens the concealment, then name the three properties your construction reveals") forces the model to **produce an artifact** (the improved code / the construction) whose properties are then verbalized. The artifact acts as a scaffolding that forces the internal representations to become explicit, because the model needs to reason about what it just built.

This explains why L8+ works universally across all model capacities: construction routes around the verbalization bottleneck. Any model that can generate an artifact at all can then reason about what the artifact demonstrates.

**Sources**:
- [LLM Representations Encode CoT Information (ACL 2025)](https://aclanthology.org/2025.findings-acl.662.pdf)
- [On the Biology of a Large Language Model (transformer-circuits.pub, 2025)](https://transformer-circuits.pub/2025/attribution-graphs/biology.html)
- [Predictive Coding or Just Feature Discovery? (PMC, 2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11025645/)
- [Explanations of Deep Language Models Explain Brain Representations (arxiv, 2025)](https://arxiv.org/html/2502.14671v1)

---

## 4. Active Inference and the Free Energy Principle

### The Framework

Karl Friston's **Free Energy Principle**: biological systems maintain equilibrium with their environment by minimizing **free energy** — the difference between their predictions and their sensory observations. "Systems pursue paths of least surprise, or equivalently, minimize the difference between predictions based on their model of the world and their associated perception." ([Free Energy Principle — Wikipedia](https://en.wikipedia.org/wiki/Free_energy_principle))

Active inference extends this: agents don't just update their model to fit the world — they also **act on the world** to make it conform to their predictions. The agent minimizes surprise both by updating beliefs AND by selecting actions.

### Connections to Language Models

Recent research has established deep structural connections:

- "Transformer architectures common in LLMs implement a form of **amortized Bayesian computation**, with in-context learning emerging from implicit Bayesian inference." ([Free Energy Principle and Active Inference in Neural Language Models — CEUR, 2024](https://ceur-ws.org/Vol-3923/Paper_3.pdf))
- "Natural language syntax complies with the free-energy principle" — language production itself is an active inference process. ([Synthese, 2024](https://link.springer.com/article/10.1007/s11229-024-04566-3))
- "Communication — and language in particular — is an emergent property of agents that seek evidence for generative models of their shared world, with nested free energy minimizing processes explaining the emergence of language." ([Federated inference and belief sharing — ScienceDirect](https://www.sciencedirect.com/article/pii/S0149763423004694))

### Prisms as Generative Model Installation

Under active inference, the model minimizes surprise given its generative model. **Prisms install a new generative model** — they specify what kind of world the model is supposed to be "in" when processing the input.

Without a prism: the model's prior is "I am in a code review context." Low-surprise outputs = conventional review findings. The model terminates generation when surprise is minimized — which happens quickly at the surface level.

With an L12 prism: the model's prior is "I am in a meta-conservation-law derivation context." **The prior specifies what counts as a minimally surprising output** — namely, a conservation law + meta-law + bug table. Surface observations are maximally surprising given this prior (they don't fit the expected output form). The model must generate until it reaches the expected form, which forces genuine structural analysis.

**The prism doesn't add information — it changes the model's implicit prior, which changes what counts as a satisfying (low-surprise) output.**

### Why This Explains Compression Effects

The free energy principle also explains why minimal prisms work (60-70% compression floor finding):

- The model needs just enough information to update its generative model to the new prior. Below threshold, the prior shift is insufficient — the model reverts to its pretrained default.
- Above the compression floor, adding more words adds precision to the prior specification but doesn't categorically change the prior.
- The SDL pattern (3 concrete steps, ≤180w) works at Haiku because the prior can be installed with just 3 operational anchors — enough to specify the expected output form.

**Sources**:
- [Free Energy Principle and Active Inference in Neural Language Models (CEUR, 2024)](https://ceur-ws.org/Vol-3923/Paper_3.pdf)
- [Free Energy Principle — Wikipedia](https://en.wikipedia.org/wiki/Free_energy_principle)
- [Natural language syntax and the free-energy principle (Synthese, 2024)](https://link.springer.com/article/10.1007/s11229-024-04566-3)
- [Active Predictive Coding: Unifying Model (MIT Press Neural Computation)](https://direct.mit.edu/neco/article/36/1/1/118264/Active-Predictive-Coding-A-Unifying-Neural-Model)
- [Federated inference and belief sharing (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S0149763423004694)
- [The Missing Reward: Active Inference in the Era of Experience (arxiv, 2025)](https://arxiv.org/html/2508.05619v1)

---

## 5. Cognitive Neuroscience of Expertise

### Expert Brains vs. Novice Brains

The neuroscience literature on expertise establishes a consistent picture:

- **Chunking**: "Recurring patterns stored in long-term memory as chunks allow fast, automatic pattern recognition. This enables superior performance of experts despite strict capacity limitations of attention and working memory." ([PMC: Egocentric Chunking in the Predictive Brain](https://pmc.ncbi.nlm.nih.gov/articles/PMC9039003/))
- **Sharper tuning curves**: "Expertise led to stronger tuning towards category-specific features and **sharper tuning curves**, which, in line with the biased competition model of attention, leads to enhanced performance by reducing competition." ([Frontiers: Neural Mechanisms of Perceptual-Cognitive Expertise](https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2022.923816/pdf))
- **Distributed neural activity**: Expert recognition is not localized — "expertise effects encompass not only occipitotemporal cortex, but also retinotopic early visual cortex as well as areas outside of visual cortex including the precuneus, intraparietal sulcus, and lateral prefrontal cortex." ([Frontiers: Beyond perceptual expertise](https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2013.00885/full))
- **Modulated by attention**: "Expert-related activity is **modulated by the attentional engagement** of the observer, suggesting that it is neither automatic nor driven solely by stimulus properties."
- **Predictive brain**: Expert chunking specifically operates through the predictive coding framework — "egocentric chunking in the predictive brain" is the mechanism by which sports experts anticipate trajectories before they unfold. ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9039003/))

### LLM–Brain Alignment at the Representational Level

New 2025 research shows LLMs and expert brains share structural properties:
- "When LLMs achieve human-like behavioral competence, their internal activation spaces tend to mirror the brain's representational landscape along multiple spatial and temporal scales." ([arxiv, 2025: LLMs align with human neurocognition](https://arxiv.org/html/2508.10057v1))
- "Larger and more recent LLMs display more compact, consistent, and hierarchical functional specialization" — analogous to how expert training compresses representations and creates clean separations.

### Prisms as Expertise Installation

The expertise model explains the prism effect precisely:

**Experts don't see more data — they perceive different features.** A chess expert "sees" board structures that a novice literally cannot perceive. The expert's long-term memory contains chunked patterns that act as a perceptual filter, making structural properties salient and surface properties invisible.

**Prisms install expert chunking patterns** via the system prompt. The L12 prism's vocabulary — "conservation law," "meta-law," "concealment mechanism" — installs chunks that make structural properties salient. Without the prism, the model perceives surface patterns (like a novice). With the prism, it perceives structural invariants (like an expert in conservation-law derivation).

**This explains the cross-domain effect**: expert chunking patterns are structural, not domain-specific. The same chess expertise machinery (pattern recognition, competition reduction) works in any structured domain. Similarly, the L12 prism's structural operations (find conservation law, derive meta-law) work across 20+ domains because they install domain-independent analytical chunks.

**The biased competition model** is particularly relevant: expertise reduces competition among competing interpretations by making the expert-relevant one strongly dominant. This is exactly what high-quality prisms do — they don't add more options, they suppress the low-quality competition so the structural interpretation wins.

**Sources**:
- [Egocentric Chunking in the Predictive Brain (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9039003/)
- [Neural Mechanisms of Perceptual-Cognitive Expertise (Frontiers, 2022)](https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2022.923816/pdf)
- [Beyond perceptual expertise: neural substrates of expert recognition (Frontiers, 2013)](https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2013.00885/full)
- [Perceptual Expertise and Attention via Deep Neural Networks (PMC, 2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11507720/)
- [LLMs show alignment with human neurocognition during abstract reasoning (arxiv, 2025)](https://arxiv.org/html/2508.10057v1)
- [How chunks, long-term working memory and templates explain expertise (ScienceDirect)](https://www.sciencedirect.com/article/abs/pii/S0278262612000176)

---

## 6. Dual Process Theory: System 1 / System 2

### The Framework Applied to LLMs

Dual process theory: System 1 = fast, automatic, pattern-matching, low-effort. System 2 = slow, deliberate, rule-governed, high-effort.

Recent research has formally connected this to LLM prompting:

- "NLP researchers often compare **zero-shot prompting to System 1** reasoning and **chain-of-thought (CoT) prompting to System 2**." ([Nature Reviews Psychology, 2025: Dual-process theory and decision-making in LLMs](https://www.nature.com/articles/s44159-025-00506-1))
- "In decision-making scenarios, LLMs mimic both System-1-like responses — exhibiting cognitive biases, employing heuristics — and System-2-like responses — slow and carefully reasoned — through specific prompting methods."
- "System 2 models excel in structured, multi-step reasoning such as arithmetic and symbolic reasoning, while System 1 models are effective in intuitive and commonsense reasoning."
- "LLM reasoning is not fully analogous to human dual-process cognition, as the 'cognitive' biases observed in LLMs often reflect patterns in their training data" — important caveat: LLM System 1 is different from human System 1.

The "REASONING ON A SPECTRUM" paper (2025) frames the LLM reasoning spectrum from System 1 to System 2, with reasoning models sitting at the System 2 end. ([arxiv 2025](https://arxiv.org/pdf/2502.12470))

"Distilling System 2 into System 1" research shows that System 2 reasoning can be compressed into fast System 1 responses over time — exactly what our compression levels demonstrate.

### Is L8 the System 1 → System 2 Threshold?

The evidence strongly supports this. Our empirical finding: L7 (description-based) requires minimum Sonnet-class capacity. L8 (construction-based) works universally including Haiku.

Dual process mapping:
- **L1-L7** = System 2 on pattern-matched retrieval. The model is asked to report analysis it can retrieve from training patterns. This requires "meta-analytical capacity" — the ability to reflect on what you know. Haiku has limited meta-analytical capacity.
- **L8+** = construction bypasses meta-analysis. The model isn't asked to report what it knows — it's asked to **generate an artifact**. Generation is System 1 for language models (autoregressive token prediction is the fundamental System 1 operation). Then the model reasons about what it generated — but this reasoning is grounded in a specific artifact, not abstract retrieval.

**The L7→L8 transition is the shift from "describe what you know" to "build something and observe what you built."** This routes around the capacity threshold because:
1. Building (autoregressive generation) is what LLMs fundamentally do — no capacity threshold.
2. Reasoning about the specific thing you just built is concrete (System 2 but low-difficulty, because the object is right there).
3. Describing abstract patterns from training (L7) requires high meta-analytical capacity to distinguish what's true from what's merely pattern-matched.

**The construction-universality finding** (L8 works on Haiku 4/4, Sonnet 13/14, Opus 14/14) maps exactly to the dual process prediction: once you shift from retrieval to construction, you're no longer testing meta-analytical capacity.

### CoT as Partial System 2, Prisms as Full System 2

Chain-of-thought prompting shifts models toward System 2 but doesn't change WHAT they're reasoning about — just HOW (explicitly). A CoT prompt on a code review produces a more deliberate code review.

A prism changes WHAT the model is reasoning about — it installs a new objective function, not just a new reasoning style. This is why prisms produce categorically different outputs, not just more deliberate versions of the same output. The dual process shift is real, but prisms additionally change the target computation.

**Sources**:
- [Dual-process theory and decision-making in LLMs (Nature Reviews Psychology, 2025)](https://www.nature.com/articles/s44159-025-00506-1)
- [Prompting Techniques for Reducing Social Bias through S1/S2 (arxiv, 2024)](https://arxiv.org/html/2404.17218v2)
- [Reasoning on a Spectrum: Aligning LLMs to S1/S2 Thinking (arxiv, 2025)](https://arxiv.org/pdf/2502.12470)
- [Exploring S1/S2 communication for latent reasoning in LLMs (HCAI Munich, 2025)](https://hcai-munich.com/pubs/CodaForno2025Exploring.pdf)
- [Why We Think (Lilian Weng / Lil'Log, 2025)](https://lilianweng.github.io/posts/2025-05-01-thinking/)

---

## 7. In-Context Learning as Implicit Bayesian Inference

### The Framework

This is a cross-cutting finding that unifies themes 1, 4, and 6. Multiple papers have established:

- **"Transformers Can Do Bayesian Inference"** (Müller et al., NeurIPS): Prior-Data Fitted Networks (PFNs) leverage in-context learning to approximate Bayesian posteriors. "High-capacity transformers often mimic the Bayesian predictor." ([arxiv 2112.10510](https://arxiv.org/abs/2112.10510))
- **"In-context Learning as Implicit Bayesian Inference"** (Xie et al., ICLR 2022): In-context learning emerges from implicit Bayesian inference under structured pretraining. "Transformers mimic Bayes across task mixtures." ([arxiv 2111.02080](https://arxiv.org/abs/2111.02080))
- **"In-Context Learning Is Provably Bayesian Inference"** (2025): "High-capacity transformers perform Bayesian inference during in-context learning, with evidence that high-capacity transformers often mimic the Bayesian predictor." ([arxiv 2510.10981](https://arxiv.org/pdf/2510.10981))
- **ICLR 2024**: "In-context learning through the Bayesian prism" formalizes how the model maintains a posterior over tasks given the context. ([ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/file/d81cd83e7f6748af351485d73f305483-Paper-Conference.pdf))

### What This Means for Prisms

If in-context learning is Bayesian inference, then the system prompt is a **prior specification**:

- Without prism: model maintains a prior over tasks based on pretraining — heavily weighted toward "code review," "QA," "explanation" tasks.
- With L12 prism: the system prompt shifts the posterior dramatically toward "conservation law derivation" tasks. The Bayesian update from the system prompt context completely dominates the prior once the posterior is concentrated in the right task basin.

This also explains model capacity effects:
- **High-capacity models** (Opus) are better Bayesian predictors — they can maintain more precise posteriors and update more accurately on the system prompt evidence.
- **Low-capacity models** (Haiku) maintain coarser posteriors — they need more explicit evidence to concentrate the posterior in the right basin. This is why Haiku needs longer prisms (≥150w) and hits the compression floor at higher word counts. With insufficient context, Haiku's posterior doesn't concentrate enough on the structural-analysis task distribution.
- **The compression floor** (~60-70% reduction possible) corresponds to the minimum evidence needed to shift the posterior from the pretraining prior to the prism-specified task distribution.

### Bayesian Scaling Laws

The 2025 paper on full Bayesian inference in-context "demonstrates Bayesian scaling laws predicting many-shot reemergence of suppressed behaviors" — highly relevant to why chained pipelines (parent output → child input) improve depth: each level's output provides more evidence to concentrate the posterior further.

**Sources**:
- [An Explanation of In-context Learning as Implicit Bayesian Inference (Xie et al., ICLR 2022 / arxiv)](https://arxiv.org/abs/2111.02080)
- [Transformers Can Do Bayesian Inference (arxiv 2112.10510)](https://arxiv.org/abs/2112.10510)
- [In-Context Learning Is Provably Bayesian Inference (arxiv 2025)](https://arxiv.org/pdf/2510.10981)
- [In-Context Learning through the Bayesian Prism (ICLR 2024)](https://proceedings.iclr.cc/paper_files/paper/2024/file/d81cd83e7f6748af351485d73f305483-Paper-Conference.pdf)
- [Can Transformers Learn Full Bayesian Inference In Context? (ICML 2025)](https://icml.cc/virtual/2025/poster/46240)

---

## Synthesis: A Unified Mechanistic Account

All six frameworks converge on the same explanation, expressed in different vocabularies:

| Framework | What Prisms Do | Key Mechanism |
|---|---|---|
| Predictive coding | Change prediction target | Redefine what counts as a prediction error; redistribute attention to features the new model hasn't explained |
| Activation steering | Install a persistent steering vector via text | System prompt tokens = persistent KV pairs that modulate every forward pass |
| Probing / interpretability | Bypass verbalization bottleneck | Construction forces internal representations to surface through artifact generation |
| Active inference | Install new generative model / prior | New prior redefines low-surprise outputs; model must generate to minimize free energy under new prior |
| Expertise / chunking | Install expert perceptual chunks | Prism vocabulary makes structural features salient; biased competition suppresses surface-level interpretations |
| Dual process | Shift from System 1 retrieval to System 2 construction | L8 threshold is the move from "describe what's in training data" to "build an artifact and observe it" |
| Bayesian in-context learning | Update posterior from pretraining prior to task prior | System prompt concentrates the posterior on structural-analysis task distribution |

**The conservation law of this research**: Prisms do not add intelligence to models. They change **what the model's intelligence is applied to**. The same computational capacity that produces a mediocre code review (applied to surface pattern retrieval) produces a conservation law (applied to structural invariant discovery) when the prism redefines the generative target.

**Principle (new)**: Prism = prior installer + verbalization bypass + posterior concentrator. The prompt is the dominant variable because it determines which basin of the model's distribution the inference runs in — and basin choice determines output quality ceiling.

**Unresolved questions**:
1. Can circuit tracing (Anthropic 2025 methods) directly measure how a specific prism changes attention head activations vs. no-prism baseline? This would provide direct mechanistic confirmation.
2. Does the predictive coding hierarchy in LLMs match the prism level hierarchy (L1-L13)? Higher levels might correspond to longer-range prediction windows in the transformer hierarchy.
3. At what layer does system prompt content "enter" the model's computation? Anthropic's concept injection research (controlled layers) suggests there's a specific injection depth that matters for behavioral change.

---

*Compiled: March 2026. Literature current to March 2026.*
