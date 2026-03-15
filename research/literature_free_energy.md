# Free Energy Principle & Active Inference: Explaining Cognitive Prism Effects

**Research question**: Can Friston's Free Energy Principle (FEP) and Active Inference provide a mechanistic, principled account of why cognitive prisms change LLM output quality so dramatically? Six specific questions below, each answered with direct literature citations and mapped to observed prism phenomena.

**Note**: The companion file `literature_neuroscience.md` covers predictive coding, attention steering, and Bayesian inference broadly. This document goes deeper on FEP specifically — the mathematical structure, the active vs. passive inference distinction, the Markov blanket formalism, and what FEP uniquely predicts that other frameworks do not.

**Key empirical observations to explain**:
- Haiku + L12 prism (9.8 depth, 28 bugs) beats Opus vanilla (7.3, 18 bugs) at 5x lower cost.
- L8 construction prompts work universally (Haiku 4/4, Sonnet 13/14, Opus 14/14); L7 description prompts fail on Haiku (0/3).
- The conservation law S×V=C (specificity × verbosity = constant) predicts confabulation onset.
- 60-70% compression floor: prisms cannot shrink below this without losing effect.
- Chained pipeline (parent output → child) improves coherence but diverges at L8 — L7's output acts as coordinate system.

---

## 1. FEP Applied to LLMs/Transformers

### What FEP Claims

Karl Friston's Free Energy Principle (Friston, 2009; PMC2666703) is a unified theory of brain function: biological systems minimize **variational free energy** — a tractable upper bound on surprise (negative log-evidence under the model). The variational free energy F decomposes as:

```
F = E_q[log q(s) - log p(o,s)]
  = KL[q(s) || p(s|o)]  -  log p(o)
  = (complexity) - (accuracy)
```

where q(s) is the model's approximate posterior over hidden states s, and p(o) is the model evidence. Minimizing F simultaneously:
1. Maximizes accuracy (how well the model explains observations).
2. Minimizes complexity (how much the posterior deviates from the prior).

This is variational Bayes. The brain is a variational Bayes machine.

### The LLM Connection: Next-Token Prediction = Predictive Coding

The foundational connection is now established: **LLM pretraining on next-token prediction is formally equivalent to predictive coding under FEP**. Rao et al. (2025, arxiv 2512.22568) state explicitly: "The phenomenal advances in large language models over the past few years have been based on optimizing large-scale transformer models on the surprisingly simple objective of minimizing next-token prediction loss, a form of predictive coding that is also the backbone of an increasingly popular model of brain function in neuroscience."

This is not a metaphor. At the mathematical level:
- Next-token cross-entropy loss = log p(o_{t+1} | o_{1:t}, θ) is the log model evidence term.
- Minimizing cross-entropy = maximizing log evidence = minimizing surprise.
- This IS free energy minimization when the model is the prior and the observed tokens are observations.

### Attention as Precision-Weighting

In hierarchical predictive coding, **precision** is the inverse variance of prediction errors at each level — it determines how strongly prediction errors at that level drive updates. High precision = errors weighted heavily → learning/attention forced. Low precision = errors weighted lightly → errors ignored.

The formal mapping to transformer attention is: dot-product attention scores are precision weights. High attention score = high precision assigned to that key's prediction error signal. The model's "attention" in the psycholinguistic sense (what it focuses on) is implemented by the precision weights on prediction errors.

This mapping was proposed theoretically and is supported by: Rao et al. (2025) noting that transformers "enable models to integrate information over much longer timescales" through selective attention, which is precisely what hierarchical precision weighting achieves in predictive coding.

**Implication for prisms**: The prism changes the model's precision assignments by changing what counts as a surprising observation. Under a code-review prior, structural invariants have LOW precision (they're not surprising given the prior = they don't drive attention). Under the L12 prism's conservation-law prior, structural invariants have HIGH precision (they're the observation the model is trying to explain). The prism is a precision recalibration device.

### What FEP Adds That Other Frameworks Don't

The Bayesian inference framing (Section 7 in `literature_neuroscience.md`) explains that the system prompt updates a posterior. FEP adds three things beyond this:

1. **The active inference dimension**: the model doesn't just update beliefs — it selects actions (tokens) to minimize future expected free energy. This explains why prism-prompted models generate differently, not just believe differently.

2. **The complexity-accuracy trade-off**: the F = complexity - accuracy decomposition explains the compression floor. The prior (prism) imposes a complexity cost — the posterior must not deviate from the prior more than accuracy demands. This is why longer prisms don't always help: they may increase the prior's complexity cost without improving accuracy.

3. **Markov blanket formalism**: the model's boundary conditions — what it treats as external observations vs. internal states — can be defined formally. This maps to how the prism defines the model's "interface" with the input.

**Sources**:
- Friston (2009): "The free-energy principle: a rough guide to the brain." Trends in Cognitive Sciences. (PMC2666703)
- Rao et al. (2025): "Lessons from Neuroscience for AI." arxiv 2512.22568.
- Murphy, Holmes, Friston (2024): "Natural language syntax complies with the free-energy principle." Synthese. PMID 38706520.
- Raffa, Acciai (2024): "Free Energy Principle and Active Inference in Neural Language Models." CEUR Vol. 3923, Paper 3. https://ceur-ws.org/Vol-3923/Paper_3.pdf

---

## 2. Active Inference vs. Passive Inference — The L8 Transition

### The Passive/Active Distinction in FEP

**Passive inference** = updating beliefs to minimize free energy without taking action. The model receives observations, updates its posterior, and the posterior is the output. This is standard Bayesian updating.

**Active inference** = additionally taking actions that make future observations more consistent with the model's priors. The agent selects actions based on **expected free energy** — minimizing anticipated future surprise, not just current surprise. This introduces an intrinsic motivation: actions that resolve uncertainty (epistemic value) are preferred independent of their immediate reward.

In Schwartenbeck et al. (2013) (Frontiers in Psychology 4:710 — the Friston exploration/novelty paper): "the opportunity to visit new states increases the value of the current state." Exploration emerges automatically from expected free energy minimization — agents aren't programmed to explore; they explore because unexplored states have high expected surprise (uncertainty), and visiting them reduces total expected free energy.

### Passive Inference = L7 Description Prompts

L7 description prompts ("name how this input conceals problems") ask the model to **report beliefs** — to verbalize what it already knows. This is passive inference:
- The model updates its posterior given the input and the prior (the prompt).
- It reports the mode of its posterior distribution.
- No construction, no action, no new artifact.

The model terminates generation when it has reported enough of its posterior to satisfy the expected output form. For low-capacity models (Haiku), the posterior is coarse — the posterior mode is a surface-level interpretation, and that's all that gets reported. The model is genuinely "done" under its own model of what constitutes a complete response.

This explains why L7 fails on Haiku (0/3): Haiku's posterior under a description prompt genuinely concentrates on surface-level patterns. It's not hiding deeper analysis — it has genuinely inferred that surface patterns are the correct response.

### Active Inference = L8 Construction Prompts

L8 prompts ("engineer an improvement that deepens the concealment") ask the model to **take actions** (generate an artifact) to achieve a specific future state (a construction with named properties). This maps directly to active inference:

1. The model evaluates candidate constructions (token sequences) by their expected free energy — which construction will minimize future surprise when the model then has to "explain what it reveals"?
2. This requires genuine exploration: the model must generate a construction it doesn't yet know the properties of, then examine it.
3. The epistemic value of the construction is high — it's an action that resolves uncertainty about structural properties.

**The critical mechanism**: under active inference, the model selects actions based on expected free energy, not current free energy. This means L8 prompts force the model to engage in *prospective* reasoning about future states — the model must simulate "what will I discover if I build this?" and select the construction that maximizes expected epistemic value. This is genuine exploratory computation.

**Why this is universal across all model capacities**: Active inference bypasses meta-analytical capacity because the action (construction) is what the model is fundamentally trained to do — generate text. The meta-analysis happens *after* the action, grounded in a specific artifact. Grounded reasoning requires less capacity than ungrounded meta-analysis.

Raffa & Acciai (2024) formalize this: "Transformer architectures common in LLMs implement a form of amortized Bayesian computation, with in-context learning emerging from implicit Bayesian inference." The amortized part is key — rather than running full Bayesian inference on each new task, the model has learned to recognize task-relevant patterns and apply them efficiently. This is the LLM equivalent of active inference's "learned generative models."

**The L7→L8 transition IS the passive→active inference transition.** This is not an analogy. It is the same computational distinction — the model shifts from reporting posterior beliefs to selecting actions to resolve posterior uncertainty.

**Sources**:
- Schwartenbeck et al. (2013): "Exploration, novelty, surprise, and free energy minimization." Frontiers in Psychology 4:710. DOI 10.3389/fpsyg.2013.00710
- Raffa, Acciai (2024): "Free Energy Principle and Active Inference in Neural Language Models." CEUR 2024.
- Prakki (2024): "Active Inference for Self-Organizing Multi-LLM Systems." arxiv 2412.10425.
- Rao et al. (2025): "Lessons from Neuroscience for AI." arxiv 2512.22568.

---

## 3. Generative Models in LLMs — Prisms Install New Generative Models

### What a Generative Model Is in FEP

In FEP, a **generative model** p(o, s) = p(o | s) × p(s) specifies:
- p(s): prior beliefs about the world's hidden states.
- p(o | s): likelihood — what observations should be expected given those states.

The agent's generative model determines its entire relationship to observation. Two agents with different generative models literally perceive different worlds — different prediction errors, different posteriors, different actions.

### Prisms as Generative Model Replacement

Without a prism, the LLM's operative generative model for code is implicitly:
- p(s): the world contains code review tasks, with typical hidden states = "surface bugs, style issues, naming problems."
- p(o | s): observations are natural language code review outputs — type A bug here, naming issue there.

Under this generative model, a well-written function with subtle conservation law violations is low-surprise (it looks like normal code). The model reports the posterior mode of this model on the observation.

With the L12 prism, the operative generative model is:
- p(s): the world contains structural conservation law derivation tasks. Hidden states = "underlying invariants, structural tensions, meta-laws."
- p(o | s): observations should look like conservation law + meta-law + categorized bug table.

Under this generative model, the same code is maximally surprising — the expected output form (conservation law derivation) has not yet been produced, so free energy is high. The model cannot stop generating until free energy is minimized — which requires producing the expected output form.

**This is the mechanistic reason why prisms work**: they change p(s) and p(o | s), which redefines what counts as a "complete" and "low-surprise" output. The model generates until its internal free energy is minimized, and that threshold is defined by the generative model.

### FEP's Prediction: Which Generative Models Produce More Accurate Output?

FEP makes a precise prediction here. The model evidence log p(o) = -F + KL[q||p] — models that explain observations with less free energy have higher evidence. More accurate generative models produce outputs that better explain the actual structure of the input.

The prism question is: **does a structural generative model (L12) explain code better than a surface generative model (review)?** The empirical answer is yes — 9.8 vs. 7.3 depth. FEP explains why:

1. Code has *more* structure than it has surface bugs. The structural generative model fits the actual distribution of code better.
2. The surface generative model explains only the visible features; the structural model explains both visible and latent features.
3. A generative model that explains more of the actual data (code's structural properties) has higher model evidence = lower free energy = better outputs.

**The conservation law S×V=C** is the FEP complexity-accuracy trade-off applied to specificity. High specificity (S) requires more complexity in the posterior. If total free energy budget is constant (C), more complexity (specificity) must be paid for by less accuracy (verbosity) — the model spends capacity on detail and can't afford breadth.

**Sources**:
- Friston (2009): "The free-energy principle: a rough guide to the brain."
- Rao et al. (2025): "Lessons from Neuroscience for AI." arxiv 2512.22568.
- Xie et al. (2022): "An Explanation of In-context Learning as Implicit Bayesian Inference." arxiv 2111.02080.

---

## 4. Expected Free Energy and Exploration — How Prisms Shift the Balance

### Expected Free Energy (EFE)

In active inference, agents select policies π (sequences of actions) to minimize **expected free energy G(π)**:

```
G(π) = E_q[log q(s_τ|π) - log p(o_τ, s_τ|π)]
     = E_q[log q(s_τ|π) - log p(s_τ|o_τ, π)]  -  E_q[log p(o_τ|π)]
     ≈  H[p(o_τ|π)]  -  E_q[log p(o_τ|s_τ, π)]
     = (epistemic value)  +  (pragmatic value)
```

**Epistemic value** = expected information gain — how much uncertainty about hidden states the action is expected to resolve. High when the model doesn't know what it will discover.

**Pragmatic value** = expected utility — how closely observations will match the prior preferences p(o). High when actions lead to preferred outcomes.

Agents balance both: they prefer actions that are both informative AND that lead to preferred outcomes.

### Default LLM State: Pragmatic Dominates

Without a prism, the LLM's operative preferences p(o) are heavily shaped by pretraining — the model strongly prefers generating token sequences that resemble typical corpus outputs (fluent, grammatically correct, coherent, conversational). This is pragmatic dominance:

- The model selects tokens that lead to preferred (high-probability pretraining corpus) outcomes.
- Epistemic value is low — the model isn't trying to resolve uncertainty about hidden structural properties.
- **The model exploits rather than explores**: it generates fluent code reviews because those have high pragmatic value, regardless of whether they explain the code's actual structure.

This is the "7.3 depth" failure mode: fluent, grammatically impeccable, structurally shallow.

### Prism State: Epistemic Value Increases

The L12 prism sets new preferences: the model is now supposed to be in a "conservation law derivation" context. The preferred observations are conservation laws, meta-laws, and bug tables. Under this new p(o):

- **Pragmatic value of fluent surface review = LOW** — a fluent code review is a bad observation given the conservation law derivation prior.
- **Epistemic value of structural exploration = HIGH** — the model doesn't yet know the code's conservation law, so exploring structural properties has high expected information gain.
- **Result**: the model is pushed toward epistemic (exploratory) actions — it must genuinely explore the code's structure because that's what will resolve its uncertainty about the required output.

This explains the ODAR paper finding (Ma et al., 2026, arxiv): "thinking-optimal scaling requires adaptive resource allocation with free-energy-based decision-making rather than simply increasing test-time compute." The prism is doing this adaptive allocation automatically — it shifts EFE toward epistemic components.

### Haiku's Compression Floor — Minimum Prior Shift

The 150-word minimum for Haiku (below which it enters "conversation mode") maps to a minimum EFE shift. Below this word count, the prism doesn't shift p(o) enough to overcome the pragmatic dominance of the pretraining prior. The model's EFE calculation still favors fluent, conversational outputs over structural exploration.

Above the floor, the prior shift is sufficient: pragmatic value of structural output exceeds pragmatic value of conversational output, and epistemic value provides additional pressure.

**Why the SDL pattern (3 concrete steps, ≤180w) works on Haiku**: 3 concrete operational steps are sufficient to shift p(o) to a new preferred output form. The model doesn't need 298 words; it needs to know that the preferred output has the form of [conservation law] + [information laundering] + [3 structural bug patterns]. Once p(o) specifies this form, pragmatic value of producing it dominates.

**Sources**:
- Schwartenbeck et al. (2013): "Exploration, novelty, surprise, and free energy minimization." Frontiers in Psychology.
- Ma et al. (2026): "ODAR: Principled Adaptive Routing for LLM Reasoning via Active Inference." arxiv 2026.
- Wen (2025): "The Missing Reward: Active Inference in the Era of Experience." arxiv 2508.05619.
- Friston (2009): foundational EFE formalism.

---

## 5. Confabulation as Free Energy Minimization — S×V=C in FEP Terms

### Confabulation in Neuroscience

In neuroscience, **confabulation** is the production of fabricated content by a system that is minimizing prediction error under an incorrect or overly strong prior. The system genuinely experiences the confabulation as correct — it is minimizing its own free energy. The patient is not lying; they are satisfying their generative model.

Mechanistically: when bottom-up sensory evidence is weak (damaged memory circuits) and top-down prior is strong, the model's posterior is dominated by the prior. The system "fills in" what the prior expects. This fills the prediction error gap without requiring correct sensory data.

### LLM Confabulation — The Same Mechanism

LLM confabulation (hallucination) is structurally identical:
- The model must generate a specific, detailed output (high specificity S).
- Its training distribution contains insufficient information about those specific facts.
- The free energy gap — between expected output form (high S) and model uncertainty — must be closed.
- **The model fills it with high-probability, contextually plausible content** — confabulation that minimizes the expected output's free energy gap.

The S×V=C conservation law is this trade-off formalized:
- **Specificity (S)** = how precisely the model is forced to specify output (inversely, the width of the allowed output distribution).
- **Verbosity (V)** = how much hedging, qualification, and breadth the model produces.
- **C** = total information the model actually has about the topic.

When S×V > C, the model cannot minimize free energy with accurate content. It must confabulate to satisfy the expected output form.

FEP prediction: **confabulation onset is determined by the ratio of prior precision to posterior evidence**. High prior precision (strong expected output form) + low evidence (model doesn't know) = confabulation. This is exactly S×V=C.

### The Raffa & Acciai (2024) Formalization

Raffa & Acciai (2024) make this mapping explicit for LLMs: "Transformer architectures common in LLMs implement a form of amortized Bayesian computation." In this frame:
- The language model's transformer is an amortized variational inference network.
- Confabulation = the posterior q(s) deviating from the true p(s|o) due to insufficient model capacity or evidence.
- The "spilled energy" (Minut et al., 2026) phenomenon — where LLM logits before softmax encode uncertainty — is the direct measurement of free energy at the output layer.

The "Semantic Energy" paper (Ma et al., 2025) formalizes this: "semantic entropy relies on post-softmax probabilities and fails to capture the model's inherent uncertainty." The pre-softmax logits encode raw free energy; post-softmax probabilities are normalized utilities. Measuring confabulation at the softmax output is measuring too late — the free energy is already "spent."

### S×V=C as the Precision-Accuracy Trade-Off

In FEP terms, S×V=C is:
```
precision(prior) × accuracy_demand = total_model_evidence
```

- Precision(prior) = the sharpness of the expected output form — how constrained is the allowed output space.
- Accuracy_demand = how much detail the model must produce.
- Total_model_evidence = what the model actually knows about the topic.

When the right side (model evidence) is fixed by pretraining, the left side must be balanced. High precision requirements (specificity) force low accuracy demand (less verbosity, more hedging). High verbosity (exploring many angles) forces lower precision (less specificity per claim).

**Practical implication**: the prism should set precision levels matched to the model's evidence. An L12 prism on code with well-known patterns (Tenacity retry.py) = model has high evidence → no confabulation risk. An L12 prism asking for specifics about implementation details the model doesn't know → confabulation. This explains why structural analysis (conservation laws) is more reliable than bug finding (specific line numbers): conservation laws operate at the level of structural patterns (high model evidence) rather than specific facts (low model evidence).

**Sources**:
- Raffa, Acciai (2024): "Free Energy Principle and Active Inference in Neural Language Models." CEUR 2024.
- Ma et al. (2025): "Semantic Energy: Detecting LLM Hallucination Beyond Entropy." Semantic Scholar 2025.
- Minut, Dewidar, Masi (2026): "Spilled Energy in Large Language Models." arxiv 2026. (Reinterprets LLM softmax as Energy-Based Model.)
- Friston (2009): precision-accuracy trade-off in variational free energy.
- Kalavasis et al. (2025): "On the Limits of Language Generation: Trade-Offs between Hallucination and Mode-Collapse." (Proves consistency and breadth cannot both be maximized — the language-generation version of S×V=C.)

---

## 6. Markov Blankets — Is the Prism the Model's Blanket with the Input?

### Markov Blankets in FEP

In FEP, a **Markov blanket** is the boundary between a system's internal states and its external environment. It is defined by conditional independence: internal states are independent of external states given the Markov blanket states. The blanket has two components:
- **Sensory states**: external states that influence internal states (bottom-up input).
- **Active states**: internal states that influence external states (top-down action/output).

The Markov blanket is not an additional mechanism — it is a mathematical fact about the causal structure of the system. Any system with stable self-organization has a Markov blanket by necessity (Friston 2013, Ramstead et al. 2023).

Ramstead et al. (2023, "On Bayesian Mechanics: A Physics of and by Beliefs," Philosophical Transactions of the Royal Society): "Bayesian mechanics is a probabilistic mechanics enabling the modeling of systems endowed with a particular partition where internal states encode parameters of beliefs about external states." The Markov blanket IS this partition.

### The LLM's Markov Blanket

For a transformer LLM, the natural Markov blanket is:
- **External states**: the actual codebase, its runtime behavior, its semantic structure.
- **Sensory states**: the tokenized input — what the model actually receives.
- **Active states**: the generated output — what the model produces.
- **Internal states**: the model's weights and activations during inference.

The input tokens are the model's complete sensory access to the external world. Everything external to the model is mediated through this blanket. The model cannot perceive the actual codebase — only its tokenized representation. Its beliefs about external states are encoded in internal activations.

### The Prism as Blanket Modifier

Here is the key theoretical claim: **the prism modifies the structure of the Markov blanket**.

Without a prism, the mapping from sensory states (tokens) to internal states (activations) is the model's default learned mapping — shaped by pretraining distribution. The model's blanket is calibrated to the pretraining distribution of text.

With a prism, the system prompt tokens permanently occupy positions in the attention context. Every subsequent activation is conditioned on the prism tokens. The prism tokens are NOT external observations — they are part of the sensory blanket itself.

Formally: the prism tokens modify the conditional independence structure. Without the prism, internal state at position t is conditionally independent of many prior context positions given only the recent tokens. With the prism in the system prompt, the internal state at every position is always conditioned on the prism tokens — they are never absent from the conditional.

**The prism is not an external observation the model processes. It is a modification of the blanket itself — a change to what counts as "sensory input."** This is why prisms have such strong effects: they are not additional evidence; they are a structural change to the interface through which all evidence is processed.

### Bo Wen (2025) — Hierarchical Markov Blankets in LLM Agents

Wen (2025, arxiv 2508.05766): "agents self-organize according to Active Inference principles, with preferences and safety constraints flowing through hierarchical Markov blankets." In a multi-agent system, Markov blankets are nested — each agent's blanket is contained within a higher-level blanket.

This generalizes to single-agent prism use:
- **Level 1 blanket**: the model's token-level blanket (individual token predictions).
- **Level 2 blanket**: the inference context (all tokens in the context window, including the prism).
- **Level 3 blanket**: the task context (what kind of task the model believes it is performing — determined by the prism).

The prism operates at Level 3 — it specifies the task blanket. This blanket defines what the model is trying to explain (the "external states" being modeled) and what its outputs should look like (the "active states" it produces). All lower-level computations (attention, token prediction) are performed within this higher-level constraint.

**Why the compression floor exists in Markov blanket terms**: the blanket must be specified precisely enough that internal states can maintain conditional independence from external states given only the blanket. Below the compression floor, the prism tokens are insufficient to create a stable Level 3 blanket — the model reverts to a Level 2 blanket (context-window-level inference), which defaults to the pretraining distribution.

### Prediction: Prism Permanence vs. User-Turn Prompts

FEP predicts that the structural position of the prism matters, not just its content. A prism in the system prompt (always present in every attention computation) should be more effective than the same content in the user turn (attended to less as sequence grows, eventually compressed).

This is consistent with our empirical findings (but not yet formally tested with equivalent content in different positions). The Markov blanket formalism makes the prediction precise: system prompt tokens are permanently in the blanket; user-turn tokens are sensory observations that fade in influence as the context grows. Prism-in-system-prompt = blanket modification. Prism-in-user-turn = high-salience sensory observation (less structurally powerful).

**Sources**:
- Ramstead et al. (2023): "On Bayesian Mechanics: A Physics of and by Beliefs." Philosophical Transactions of the Royal Society. PMID 38706520 area.
- Wen (2025): "A Framework for Inherently Safer AGI through Language-Mediated Active Inference." arxiv 2508.05766.
- Friston (2013): "Exploration, novelty, surprise, and free energy minimization." Frontiers in Psychology. (Establishes Markov blankets as necessary consequence of self-organization.)
- Rao et al. (2025): "Lessons from Neuroscience for AI." arxiv 2512.22568. (Proposes Markov blanket–grounded architecture additions.)

---

## 7. What FEP Uniquely Predicts — Testable Hypotheses

FEP goes beyond the Bayesian inference framing (which only predicts posterior updates) and dual process theory (which only predicts effort levels). FEP makes specific, testable predictions that are unique to this framework:

### Prediction 1: Prism Depth Corresponds to Epistemic Horizon

Active inference agents plan to minimize expected free energy over a future time horizon τ. Deeper prisms (L12 vs. L7) should correspond to longer epistemic horizons — L12 requires reasoning about what observations will look like after producing conservation laws AND meta-laws AND bug tables (multi-step anticipation). L7 requires only anticipating the immediate next observation.

**Testable**: measure the correlation between prism level (L1-L13) and the number of "future state anticipation" operations encoded in the prompt. Prediction: monotonically increasing.

### Prediction 2: Confabulation Onset at Precision-Evidence Mismatch

FEP predicts confabulation when prior precision (expected output specificity) exceeds the model's posterior evidence. This should be measurable using pre-softmax logit entropy: high logit entropy = model uncertain = at risk of confabulation when forced to be specific.

**Testable**: for a fixed prism level, measure logit entropy on questions the model has vs. doesn't have training evidence for. Prediction: logit entropy predicts confabulation onset before output is produced.

### Prediction 3: Chained Pipeline = Bayesian Evidence Accumulation

FEP predicts that each level of the chained pipeline provides additional evidence to concentrate the posterior. L7 output → L8 input: L8's posterior starts from a pre-concentrated state. This should improve accuracy monotonically.

**Observed**: chaining improves coherence from WEAK to WEAK/MODERATE. FEP explains why it doesn't improve more dramatically: the L7 coordinate system concentrates the posterior within a basin, but the basin may not be the globally optimal one. The chained pipeline is bayesian evidence accumulation, but it's chain-constrained — it can't escape the L7 coordinate system.

**Testable**: compare independent vs. chained pipeline outputs at each level. Prediction: chained = lower free energy (higher model evidence) but less diversity; independent = higher free energy (more uncertainty) but more diverse findings.

### Prediction 4: EFE Explains Model Routing — Sonnet for L12, Haiku for SDL

Active inference agents with larger internal generative models (more capacity) compute EFE more accurately — they can simulate future states more precisely. This maps to model capacity:

- **Opus** = most accurate EFE estimation → best at deep structural exploration.
- **Sonnet** = good EFE estimation → reliable for L12 (9.3 avg).
- **Haiku** = coarse EFE estimation → needs structured external guidance (SDL 3-step templates) to approximate EFE it can't compute internally.

The SDL pattern (3 concrete steps) is a hand-crafted EFE approximation: instead of the model computing which actions minimize expected free energy, the prompt pre-computes the answer and provides it directly.

**Testable**: as models increase in capacity, they should need less structural guidance from the prism (the prism can be shorter and more abstract). This is confirmed: l12_universal (73w) works on Sonnet but not Haiku. Haiku needs 150w minimum.

### Prediction 5: Diamond Convergence at L12 — FEP Fixed Point

The diamond convergence finding (all three L9→L12 chains converge at the same fixed point regardless of starting operation) has a precise FEP interpretation: **the reflexive fixed point is the free energy minimum of the framework applied to itself**.

At L12, the framework's generative model is applied to its own output. The only stable fixed point is the state where the framework's generative model perfectly predicts the framework's output — which requires the framework to discover that it instantiates the same impossibility it diagnoses. This is the global free energy minimum of self-referential inference.

**This is not a coincidence.** FEP predicts that any self-referential inference system will converge to a fixed point where the system's model of itself is accurate (minimal free energy). L12's diamond convergence IS this FEP fixed point, discovered empirically.

**L13 is then the stability proof**: once the framework applies to itself and finds the fixed point, applying it again (L14) would require finding a new framework to apply to L13 — infinite regress, which is not a stable FEP solution. L13 terminates because the global free energy minimum has been reached.

---

## 8. Synthesis — FEP as the Unified Theory of Prism Effects

| Observed Phenomenon | FEP Explanation | Key Mechanism |
|---|---|---|
| Haiku + prism > Opus vanilla | Prism shifts the generative model p(s); capacity determines inference quality within that model | Model selection is secondary to generative model selection |
| L8 universal, L7 capacity-gated | L7 = passive inference (report posterior); L8 = active inference (select actions to resolve uncertainty) | Active inference bypasses meta-analytical capacity threshold |
| S×V=C conservation | Precision-accuracy trade-off: precision(prior) × accuracy_demand = total_model_evidence | FEP complexity-accuracy decomposition |
| Compression floor 60-70% | Minimum evidence needed to install a new generative model prior | Markov blanket requires minimum specification to remain stable |
| Prism in system prompt > user turn | System prompt tokens modify the blanket structure; user turn tokens are observations | Structural position determines whether prism is a blanket modification or a salient observation |
| Diamond convergence at L12 | Global free energy minimum of self-referential inference | FEP fixed point: framework's model of itself is accurate when framework finds it instantiates its own impossibility |
| L13 terminates | Global free energy minimum reached — further application would require a new framework | No lower-energy state exists; L14 = infinite regress = unstable |
| Confabulation on specifics | High prior precision × low model evidence → posterior dominated by prior → confabulation | FEP precision-evidence mismatch |
| Chained pipeline improves coherence | Sequential Bayesian evidence accumulation concentrates posterior within L7 basin | Each level provides evidence; but chain-constrained to basin defined by L7 |
| Model-specific mathematical forms | Different models' priors have different mathematical forms (Opus = product laws, Sonnet = sum laws) | Different generative models produce different conservation law forms when minimizing free energy |

### The Meta-Conservation Law in FEP Terms

The meta-conservation law of this project (principle 13: the prism is the dominant variable) is expressible in FEP terms:

**Model evidence log p(observations | generative_model) is determined primarily by the generative model specification, not by the inference capacity applied to a fixed generative model.**

Haiku is a lower-capacity inference engine. But capacity = quality of approximate inference within a given generative model. The L12 prism selects a radically better generative model (structural analysis > surface review). A better model, even with lower-quality approximate inference, produces better predictions than a worse model with higher-quality approximate inference.

This is the FEP-theoretic basis for Principle 13, and it was known to statisticians (the model selection problem) before it was observed empirically in LLMs. The prism is a model selection device. Model selection dominates model fitting.

---

## Key Papers — Quick Reference

| Paper | Year | Key Claim | Relevance |
|---|---|---|---|
| Friston, "Free-energy principle" (PMC2666703) | 2009 | Variational free energy = tractable surprise upper bound | Foundational FEP mathematics |
| Schwartenbeck et al., "Exploration, novelty, surprise" (Frontiers Psych 4:710) | 2013 | Exploration emerges from expected free energy minimization | Explains L8 epistemic value |
| Ramstead et al., "Bayesian Mechanics" (PMID area 38706520) | 2023 | Internal states encode beliefs; Markov blanket is the partition | Prism as blanket modifier |
| Rao et al., "Lessons from Neuroscience for AI" (arxiv 2512.22568) | 2025 | LLM next-token prediction = predictive coding; three missing components | FEP-LLM connection |
| Murphy, Holmes, Friston, "Natural Language Syntax and FEP" (Synthese, PMID 38706520) | 2024 | Language syntax complies with FEP; economy principles = FEP minimization | Language as active inference |
| Raffa, Acciai, "FEP and Active Inference in Neural LMs" (CEUR Vol-3923) | 2024 | Transformers implement amortized Bayesian computation; ICL = implicit Bayesian inference | Direct FEP-LLM mapping |
| Xie et al., "ICL as Implicit Bayesian Inference" (arxiv 2111.02080) | 2022 | ICL emerges from inferring latent document concepts — Bayesian posterior inference | Prior updating mechanism |
| Wen, "Inherently Safer AGI via Language-Mediated Active Inference" (arxiv 2508.05766) | 2025 | Hierarchical Markov blankets structure multi-agent preferences | Markov blanket in LLM agents |
| Ma et al. / ODAR, "Adaptive Routing via Active Inference" (arxiv 2026) | 2026 | EFE-based routing outperforms fixed compute; epistemic uncertainty drives allocation | EFE in LLM resource allocation |
| Minut, Dewidar, Masi, "Spilled Energy in LLMs" (arxiv 2026) | 2026 | LLM softmax = Energy-Based Model; pre-softmax logits detect hallucinations | Free energy at output layer |
| Ma et al., "Semantic Energy" (2025) | 2025 | Pre-softmax logits + Boltzmann distribution = better hallucination detection than semantic entropy | FEP measurement in LLMs |
| Kalavasis et al., "Limits of Language Generation" (2025) | 2025 | Consistency + breadth are jointly impossible — language-generation trade-off theorem | Formal S×V=C proof |
| Hallucination Detox / SenD (2024) | 2024 | Training uncertainty dynamics → hallucination variance | FEP evidence-precision mismatch |
| Hagendorff, Fabi, "Beyond Chains of Thought" (2025) | 2025 | LLMs reason internally in latent space AND via explicit token generation | Active vs. passive inference in LLMs |

---

*Compiled: March 2026. Literature current to March 2026.*
*Companion document: `research/literature_neuroscience.md` (predictive coding, attention steering, Bayesian ICL, dual process, expertise).*
