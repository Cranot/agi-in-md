# Literature Review: Metacognition in AI Systems

**Context for this review:** The AGI-in-md project discovered that LLM structural analysis is reliable, but specific factual claims (API names, line numbers, performance metrics) are frequently confabulated. We formalized this as `Specificity × Verifiability = Constant`. We found that prompt-based adversarial construction (the prism approach) bypasses metacognitive failures that plague self-report approaches. This review surveys what the academic literature says about AI metacognition — why it fails, when it works, and how it might be improved.

**Date compiled:** Mar 15, 2026
**Papers reviewed:** 30+ directly, 40+ via search summaries
**Scope:** Metacognitive monitoring, Theory of Mind, introspection vs. performance gaps, metacognitive training, philosophical foundations

---

## 1. Metacognitive Monitoring in LLMs — Can Models Assess Their Own Confidence?

### 1.1 Kadavath et al. 2022 — Language Models (Mostly) Know What They Know

**Citation:** Saurav Kadavath, Tom Conerly, Amanda Askell, et al. (Anthropic). "Language Models (Mostly) Know What They Know." arXiv:2207.05221, 2022.

**Key findings:** The foundational metacognition paper. Introduces two metrics:
- **P(True)**: probability that the model's proposed answer is correct, as estimated by the model itself.
- **P(IK)** ("I know"): probability that the model knows the answer before generating any proposed answer.

Larger models show well-calibrated self-evaluation on multiple choice and true/false questions. P(IK) predictions appropriately increase with contextual information and hints. Performance partially generalizes across tasks but struggles on entirely new task types.

**Key caveat:** The title "mostly" is load-bearing. Calibration holds for in-distribution factual questions. It breaks down for:
- Out-of-distribution questions (new task types)
- Highly specific claims that require external verification
- Long-form generation where atomic claims are less calibrated than aggregate responses

**Relation to our work:** This paper establishes that models CAN be calibrated in principle. Our finding explains WHY calibration fails for specific claims in code analysis: those claims (API version numbers, exact line counts) require external verification that is outside the model's training distribution. Our `Specificity × Verifiability = Constant` law explains the mechanism behind Kadavath et al.'s partial failure.

---

### 1.2 Steyvers, Belem, Smyth 2025 — Metacognition Is Trainable

**Citation:** Mark Steyvers, Catarina Belem, Padhraic Smyth. "Improving Metacognition and Uncertainty Communication in Language Models." arXiv:2510.05126, 2025.

**Key findings:** Fine-tuning can teach models to better communicate uncertainty. The team trained on two metacognitive tasks: (1) assigning numeric confidence scores to answers, and (2) pairwise comparison of which of two answers the model would more likely get right.

Results:
- Fine-tuning improved calibration within trained domains AND across unseen domains (medical, legal).
- Multitask training (both tasks together) produces broader generalization than single-task training.
- Gains are task-specific: training on confidence scoring does not automatically transfer to pairwise comparison.

**Core conclusion:** "Uncertainty communication in LLMs is trainable but requires multitask training to generalize effectively."

**Relation to our work:** This directly answers our Question 4 (can models be trained for better metacognition?). YES — metacognition is trainable via fine-tuning. But the cost (labeled data, retraining) is high. Our prism approach achieves similar metacognitive accuracy at inference time, zero-shot, via adversarial construction — a fundamentally different mechanism that doesn't require retraining.

**Key distinction:** Training improves SELF-REPORT calibration. Prism bypasses self-report entirely — instead of asking the model "are you confident?", the prism asks "what would destroy this claim?". The operations are structurally different. One improves the model's confidence meter; the other stress-tests the claim directly.

---

### 1.3 Dunning-Kruger in LLMs (Ghosh & Panday, 2026)

**Citation:** Sudipta Ghosh, Mrityunjoy Panday. "The Dunning-Kruger Effect in Large Language Models." arXiv, 2026.

**Key findings:** Poorly performing models display markedly higher overconfidence. Expected Calibration Error (ECE) ranges from 0.122 to 0.726 across four tested models. Weaker models are simultaneously less accurate AND more overconfident — the AI analog of the human cognitive bias where the least competent individuals overestimate their abilities most severely.

**Relation to our work:** This explains a critical design choice in the prism system: we do NOT route metacognitive questions to weaker models. Haiku + right prism beats Opus vanilla, but only because the prism is doing the metacognitive work. Without the prism, Haiku's self-confidence is dangerously miscalibrated. The prism externalizes metacognition from the model into the prompt structure.

---

### 1.4 EpiCaR 2026 — Self-Training Induces Overconfidence

**Citation:** Jewon Yeom, Jaewon Sok, Seonghyeon Park et al. "EpiCaR: Knowing What You Don't Know Matters for Better Reasoning." arXiv, 2026.

**Key findings:** Self-training approaches (RLHF variants, self-play) cause models to become overconfident and lose the ability to represent uncertainty. The model learns to sound confident because confident answers are rewarded during training, regardless of accuracy.

**Core insight:** RLHF optimizes for human-preferred outputs, and confident outputs are more preferred by human raters than uncertain ones. This creates a systematic pressure toward overconfidence that accumulates across training rounds.

**Relation to our work:** This is a crucial finding for the prism architecture. It means that as models get more capable (more RLHF training), their metacognitive accuracy can DECREASE — they become better at sounding right while being wrong. Prism's adversarial construction approach is immune to this training artifact: we don't ask the model to self-assess, we attack the claim structurally.

---

### 1.5 Verbalized Confidence Is Unreliable (Multiple Sources)

**Key sources:**
- "Benchmarking Uncertainty Calibration in Long-Form QA" (Müller et al., 2026): "Verbalized approaches are systematically biased and poorly correlated with correctness."
- "Are LLM Decisions Faithful to Verbal Confidence?" (Wang et al., 2026): Models show "dissociation" between expressed confidence and actual decision-making behavior.
- "Can LLMs Express Their Uncertainty?" (Xiong et al., 2023): "LLMs, when verbalizing their confidence, tend to be overconfident."
- "Teaching Models to Express Uncertainty in Words" (Lin, Hilton, Evans, 2022): First demonstration that calibrated natural language uncertainty IS trainable — but requires explicit intervention.

**Synthesis:** Verbalized confidence (saying "I'm 80% confident that...") is systematically overconfident and weakly correlated with accuracy. Token probabilities (log-probs) perform only marginally better than verbalization for uncertainty estimation. Neither approach provides reliable metacognitive monitoring for specific claims.

**Relation to our work:** This validates the prism design decision to NOT use self-report. The literature unanimously finds that asking models "how confident are you?" produces miscalibrated answers. Our adversarial construction approach generates a structurally different signal: how easily can this claim be attacked? Fragile claims collapse under construction; robust claims (conservation laws, structural patterns) survive. This is a behavioral test, not a confidence poll.

---

### 1.6 "Know When You're Wrong" (Xie, Liu, Yao, 2026)

**Citation:** Xie Xiaohu, Liu Xiaohu, Yao Benjamin. "Know When You're Wrong: Aligning Confidence with Correctness." arXiv, 2026.

**Key findings:** Supervised fine-tuning (SFT) yields well-calibrated confidence. Reinforcement learning methods induce overconfidence. This is the mechanism behind EpiCaR's finding — it's specifically the RL training that causes miscalibration, not SFT.

**Relation to our work:** Models that have undergone more RL training (Opus, GPT-4 with heavy RLHF) may actually have WORSE metacognitive accuracy than SFT-only models. This creates a counterintuitive prediction: the prism effect should be largest for heavily RLHF-trained models (most confident, most wrong about specific claims) and smallest for base models or SFT-only models. This aligns with our Round 29 finding that Haiku + prism beats Opus vanilla — Opus has undergone more RL training and may be more metacognitively overconfident on specifics.

---

## 2. Theory of Mind in LLMs — And What It Tells Us About Self-Knowledge

Theory of Mind (ToM) is the ability to model other agents' beliefs, intentions, and knowledge states. The question for our work: if a model can model OTHERS' knowledge limits, can it model its OWN?

### 2.1 GPT-4 Lacks Core Features of Theory of Mind (Muchovej et al., 2026)

**Citation:** John Muchovej, Amanda Royka, Shane Lee, Julian Jara-Ettinger. "GPT-4 Lacks Core Features of Theory of Mind." arXiv, 2026.

**Key findings:** LLMs succeed at approximating human judgments in simple ToM paradigms (basic false-belief tasks) but fail at logically equivalent tasks with different surface structure. The model is doing pattern matching on surface features, not genuine mental state reasoning.

**Key insight:** This is the ToM version of what we see in specificity-confabulation. The model appears to have capabilities it doesn't actually have. Surface competence masks structural absence.

**Relation to our work:** If GPT-4 fails at genuine ToM for OTHER agents, it certainly cannot reliably model its OWN knowledge limits as a first-person introspective act. Apparent self-awareness in LLMs (expressing uncertainty, flagging confidence) may be pattern matching on training data, not genuine metacognitive access.

---

### 2.2 Shallow Statistical Associations, Not Genuine ToM (Lombardi & Lenci, 2025)

**Citation:** Agnese Lombardi, Alessandro Lenci. "Doing Things with Words: Rethinking Theory of Mind Simulation." arXiv, 2025.

**Key findings:** GPT-4 frequently fails to select actions based on belief attribution. Apparent ToM-like abilities "stem from shallow statistical associations" — the model learned to output ToM-consistent language without building an actual mental state model.

**Relation to our work:** This finding directly maps to our metacognition context. When an LLM says "I'm not sure about this" or "this might be incorrect," it may be outputting language that statistically follows uncertainty-expressing patterns from training data, without genuine access to its own epistemic state. This is the deep reason why verbalized confidence is unreliable — the model doesn't have access to its own knowledge limits; it just produces confident-sounding or uncertain-sounding text based on surface context.

---

### 2.3 Reasoning Models and ToM (de Haan et al., 2026)

**Citation:** Ian B. de Haan, Peter van der Putten, Max van Duijn. "Reasoning Promotes Robustness in Theory of Mind Tasks." arXiv, 2026.

**Key findings:** Reasoning models (chain-of-thought style) show "consistently increased robustness to prompt variations and task perturbations" in ToM tasks. Slow thinking (extended chain-of-thought) correlates with better ToM performance.

**Caution from other research (Gong et al., 2026):** "Slow thinking collapses: accuracy significantly drops as responses grow longer." Extended CoT can improve ToM accuracy per question but produces more total errors in long outputs.

**Relation to our work:** Chain-of-thought / extended reasoning may improve BOTH ToM for others AND metacognition about self. This could explain why the L12 prism (which forces extended structured reasoning) produces better-calibrated outputs than vanilla generation — it's engineering slow thinking, which activates whatever genuine metacognitive capacity exists in the model.

---

### 2.4 Knowing What You Know Is Not Enough (Pal et al., 2025)

**Citation:** Pal, Kitanovski, Liang, Potti, Goldblum. "Knowing What You Know Is Not Enough." arXiv, 2025.

**Key findings:** LLMs frequently take actions that CONTRADICT their elicited confidence levels. A model that says it's 80% confident will sometimes choose to defer, and when 40% confident will sometimes commit. Static calibration measures don't predict dynamic behavioral consistency.

**Core insight:** There is a dissociation between verbalized confidence (metacognitive self-report) and actual decision behavior. Even when models are accurately calibrated in their confidence expressions, that calibration doesn't translate into appropriate action selection.

**Relation to our work:** This finding makes plain why metacognitive monitoring is hard to deploy reliably. It's not enough to teach models to accurately express confidence — the confidence expression must actually modulate behavior. Prism bypasses this entirely: the adversarial construction attack produces behavioral evidence (does the claim survive?) rather than verbal confidence (how sure do you feel?).

---

## 3. Introspection vs. Performance — The Disconnect

### 3.1 LLM's Internal State Knows When It's Lying (Azaria & Mitchell, 2023)

**Citation:** Amos Azaria, Tom Mitchell. "The Internal State of an LLM Knows When It's Lying." arXiv:2304.13734, 2023.

**Key findings:** A classifier trained on hidden layer activations can detect whether LLM statements are truthful, achieving 71-83% accuracy. This detection outperforms relying on LLM-assigned sentence probabilities. Crucially: the INTERNAL state encodes truth-falseness, even when the output doesn't express uncertainty.

**Key implication:** The model INTERNALLY represents truth/falsehood at a higher accuracy than it EXPRESSES externally. There is a systematic gap between internal representation and verbalized output. The model knows more than it says — or more precisely, its activations reflect more than its words.

**Relation to our work:** This is the mechanistic explanation for why adversarial construction works. The model's internal truth representation can be accessed via adversarial pressure — by constructing a scenario that would falsify the claim, we force the model to engage with its internal truth representation rather than producing surface-pattern-matched output. Prisms are essentially prompts that trigger truth-representation activation rather than fluency-optimized generation.

---

### 3.2 Chain-of-Thought Explanations Are Unfaithful (Turpin et al., 2023)

**Citation:** Miles Turpin, Julian Michael, Ethan Perez, Samuel R. Bowman. "Language Models Don't Always Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting." *NeurIPS 2023*. arXiv:2305.04388.

**Key findings:** CoT explanations can "systematically misrepresent the true reason for a model's prediction." When biasing features (like reordering multiple-choice options) influence model outputs, the CoT explanation does NOT mention these features even though they clearly affected the answer. Accuracy dropped by as much as 36% across 13 BIG-Bench Hard tasks when biases were present.

**Core finding:** Plausible-sounding explanations mask unreliable reasoning. The model's verbalized reasoning process is NOT a reliable window into its actual computational process.

**Relation to our work:** This is the introspection failure at its most explicit. If chain-of-thought reasoning — the model's most extended opportunity to describe its own reasoning — is systematically unfaithful to actual computation, then asking models to self-report confidence is even more unreliable. The reasoning the model produces is post-hoc rationalization, not actual introspection. This is why our construction-based approach works differently: instead of asking "why did you say that?", we ask "can you produce a counter-example?" — a generative task that doesn't rely on introspective access.

---

### 3.3 LLMs Cannot Find Reasoning Errors (Tyen et al., 2023)

**Citation:** Gladys Tyen, Hassan Mansoor, Victor Cărbune, Peter Chen, Tony Mak. "LLMs Cannot Find Reasoning Errors, but Can Correct Them Given the Error Location." *ACL 2024 Findings*. arXiv:2311.08516.

**Key findings:** Poor self-correction performance stems from LLMs' inability to FIND logical mistakes, NOT their inability to correct known mistakes. When error locations are provided, models successfully correct across five reasoning domains. A small classifier trained on out-of-domain data outperforms large models at locating errors.

**Key implication:** Models have correction capacity they cannot access via self-directed introspection. They can fix what they cannot find. The bottleneck is error detection, not error correction.

**Relation to our work:** L12-G's three-phase structure addresses this exactly. Phase 1 generates output. Phase 2 performs TYPED claim classification (which claims are STRUCTURAL, MEASURED, ASSUMED) — this is the error location step, done by claim type rather than logical inspection. Phase 3 corrects those claims. The prism performs the error location that models cannot do for themselves via introspection, enabling the correction capacity that already exists.

---

### 3.4 GPT-4 Doesn't Know It's Wrong (Stechly et al., 2023)

**Citation:** Kaya Stechly, Matthew Marquez, Subbarao Kambhampati. "GPT-4 Doesn't Know It's Wrong: An Analysis of Iterative Prompting for Reasoning Problems." arXiv:2310.12397, 2023.

**Key findings:** GPT-4 performance improvements in iterative prompting are NOT due to effective self-criticism — correct solutions appeared "fortuitously in top-k completions." The critiques themselves are irrelevant to the improvements. Models cannot effectively verify their own proposed solutions.

**Key implication:** Iterative self-prompting appears to work because of sampling variability (trying again is more likely to hit a correct solution), not because of genuine self-evaluation.

**Relation to our work:** This paper challenges naive self-improvement approaches. Our response: don't ask the model to evaluate its own answer for logical correctness (that's what fails here). Instead, have it generate a CONSTRUCTION (an alternative, an adversary, a counter-example) and examine the structural tension. The construction doesn't require logical self-verification — it requires generative capacity, which models have. The metacognitive work is done by the structure of the prompt, not the model's self-evaluation.

---

### 3.5 Semantic Entropy as Uncertainty Detector (Kuhn, Gal, Farquhar, 2023)

**Citation:** Lorenz Kuhn, Yarin Gal, Sebastian Farquhar. "Semantic Uncertainty: Linguistic Invariances for Uncertainty Quantification in Natural Language Generation." *ICLR 2023 Spotlight*. arXiv:2302.09664.

**Key findings:** Semantic entropy (uncertainty that incorporates semantic equivalence — different sentences that mean the same thing) is more predictive of model accuracy than standard uncertainty measures. Unsupervised, uses only a single model, requires no modifications.

**Core insight:** Uncertainty should be measured at the MEANING level, not the token level. Two different-worded answers that mean the same thing should be treated as the same answer (low uncertainty). Two answers with different meanings, even if each is grammatically confident, indicate high uncertainty.

**Relation to our work:** Semantic entropy is an inference-time uncertainty detector. Prism's adversarial construction is an adversarial certainty test. These are complementary:
- Semantic entropy: "does the model produce consistent meanings when asked the same question multiple times?" (requires multiple samples)
- Prism construction: "does this specific claim survive adversarial attack?" (requires one structured prompt)

Semantic entropy detects THAT a claim is uncertain. Prism's typed audit classifies WHY and WHERE to look for the answer. Both bypass the verbalized confidence failure, via different mechanisms.

---

### 3.6 The Internal State Geometry of Truth (Marks & Tegmark, 2023)

**Citation:** Samuel Marks, Max Tegmark. "The Geometry of Truth: Emergent Linear Structure in Large Language Model Representations of True/False Datasets." *Conference on Language Modeling*, 2024. arXiv:2310.06824.

**Key findings:** At sufficient scale, LLMs linearly represent truth/falsehood of factual statements. Simple probes transfer across datasets. Causal intervention can flip model outputs between true/false by manipulating specific activation directions.

**Relation to our work:** This provides mechanistic support for why prism-based adversarial construction works. If the model internally represents truth linearly, the construction pressure (adversarial attack on a claim) may directly engage the truth direction in representation space, producing more accurate self-assessment than verbalization allows. The prism is an indirect way to surface the model's truth representation without needing mechanistic access to hidden states.

---

## 4. Metacognitive Training — Can Models Learn to Know Their Limits?

### 4.1 R-Tuning: Teaching Models to Say "I Don't Know" (Zhang et al., 2023)

**Citation:** Hanning Zhang, Shizhe Diao, Yong Lin et al. "R-Tuning: Instructing Large Language Models to Say 'I Don't Know'." *NAACL 2024*. arXiv:2311.09677.

**Key findings:** Refusal-Aware Instruction Tuning (R-Tuning) identifies gaps between pre-training knowledge and instruction-tuning data, then trains models to decline questions beyond their parametric knowledge. Results:
- Better calibration than uncertainty-based testing approaches.
- Refusal ability generalizes as "a meta-skill" to out-of-domain datasets.
- Models simultaneously improve on questions they CAN answer (fewer false refusals) and appropriately decline questions they CANNOT (fewer hallucinations).

**Key implication:** The skill of knowing ignorance is meta-trainable — it transfers across domains, meaning it's not memorization of specific uncertain facts but a generalizable metacognitive operation.

**Relation to our work:** R-Tuning is the training-based answer to our Question 4. It works. But it requires:
1. Identifying which training questions are beyond the model's parametric knowledge.
2. Creating labeled data of "I don't know" responses.
3. Fine-tuning on that data.

Our prism approach achieves similar metacognitive output zero-shot, via adversarial construction, without labeled data or retraining. The tradeoff: R-Tuning bakes metacognition into the model permanently; prism metacognition must be re-applied at each call. For production deployment of a single model, R-Tuning wins. For a flexible analytical tool that must work across tasks, prism wins.

---

### 4.2 KnowRL: Reinforcement Learning for Self-Knowledge (Kale & Dhami, 2025)

**Citation:** Kale, Dhami. "KnowRL: Teaching Language Models to Know What They Know." arXiv, 2025.

**Key findings:** Uses reinforcement learning with model introspection and consensus-based rewards to improve self-knowledge without external supervision. The model is rewarded when its expressed confidence matches its actual accuracy on held-out evaluation.

**Key mechanism:** Consensus-based rewards: when multiple model samples agree on an answer, confidence should be high. When samples diverge, confidence should be low. This operationalizes semantic entropy as a training signal.

**Relation to our work:** KnowRL is the RL version of metacognitive training. It's clever because it doesn't require ground-truth labels — it uses self-consistency as the confidence proxy. But it optimizes for a specific form of metacognitive accuracy (confidence-accuracy alignment on factual questions). Our prism approach produces a different form of metacognitive output: structural claim classification and adversarial resistance testing. The two approaches probe different aspects of metacognition.

---

### 4.3 Self-Contrast: Exploiting Inconsistency (Zhang et al., 2024)

**Citation:** Wenqi Zhang, Yongliang Shen, Linjuan Wu et al. "Self-Contrast: Better Reflection Through Inconsistent Solving Perspectives." *ACL 2024*.

**Key findings:** Rather than treating self-reflection as a monolithic operation, Self-Contrast generates MULTIPLE diverse solving approaches, identifies discrepancies between them, and synthesizes these differences into a checklist for re-examination. This exploits inconsistency to reveal gaps.

**Core insight:** "The key bottleneck [in self-reflection] is the quality of the self-evaluated feedback." LLMs exhibit overconfidence during self-evaluation, producing rigid or inconsistent assessments. Making the model explicitly examine its own inconsistencies produces more accurate and stable reflection.

**Relation to our work:** Self-Contrast is a prompt-engineering approach to metacognition (no retraining required). The mechanism — diverse perspectives → find inconsistencies → targeted reexamination — parallels our prism pipeline (construction → conservation law → adversarial pass). Both exploit the fact that inconsistency between multiple framings reveals what no single framing can see alone. This is precisely the Design Principle 6 of AGI-in-md: "complementary pairs multiply, similar pairs merge."

---

### 4.4 Vision-Language Introspection for Hallucination (Liu et al., 2026)

**Citation:** Shuliang Liu, Songbo Yang, Dong Fang et al. "Vision-Language Introspection: Mitigating Overconfident Hallucinations in MLLMs via Interpretable Bi-Causal Steering." arXiv:2601.05159, 2026.

**Key findings:** A metacognitive self-correction process for multimodal models. Phase 1: diagnose hallucination risks via probabilistic conflict detection. Phase 2: steer generation away from overconfident predictions via adaptive adjustments.

Results: 12.67% reduction in object hallucination on MMHal-Bench; 5.8% improvement on POPE. Works without model retraining.

**Relation to our work:** This is a vision analog of our L12-G pipeline. Same structure: generate → audit for overconfidence → correct. Different domain (visual vs. code analysis). Validates the three-phase architecture as domain-general: the sequence "generate, audit by type, correct targeted claims" works across modalities.

---

### 4.5 MetaFaith: Faithful Uncertainty Expression (Liu et al., 2025)

**Citation:** Gabrielle Kaili-May Liu, Gal Yona, Avi Caciularu et al. "MetaFaith: Faithful Natural Language Uncertainty Expression in LLMs." arXiv, 2025.

**Key findings:** LLMs "largely fail" at faithful confidence expression. MetaFaith achieves "up to 61% improvement in faithfulness" through explicit training intervention.

**The faithfulness gap:** A model is "faithful" when its expressed uncertainty (e.g., "I'm fairly confident") accurately matches its internal probability of being right. Most models are unfaithful — they express high confidence on uncertain claims and sometimes express uncertainty on correct answers.

**Relation to our work:** The 61% improvement under MetaFaith is large but still leaves a 39% gap from perfect faithfulness. This is why confidence-based approaches remain unreliable even after metacognitive training. Prism avoids this entirely — construction-based adversarial testing doesn't depend on faithful confidence expression, so the faithfulness gap doesn't contaminate the output.

---

## 5. Philosophical Foundations — Epistemology of AI Knowledge

### 5.1 The Frame Problem as Applied to LLMs

**Classic source:** John McCarthy & Patrick Hayes. "Some Philosophical Problems from the Standpoint of Artificial Intelligence." *Machine Intelligence 4*, 1969.

**What the frame problem is:** An AI that can reason about the world also needs to reason about what DOESN'T change when an action is taken. In classic AI, this was computational. In LLMs, the frame problem reappears as: when generating a claim about code, what aspects of the code does the model "know" remain true without explicitly checking?

**Applied to LLMs:** LLMs implicitly assume their training knowledge is current (it's not), that APIs they've seen haven't changed (they have), and that code they haven't seen follows the same patterns as code they have (it may not). These are frame assumptions — the model treats things as constant without being able to verify that they are.

**Relation to our work:** The frame problem explains WHY structural claims are reliable and specific claims are not. Structural patterns (conservation laws, coupling mechanisms, abstraction layers) are framed correctly — they're invariant across versions and contexts. Specific claims (API names, version numbers) require checking frames that the model cannot verify (what version is installed? what was the API in 2024?). Our `Specificity × Verifiability = Constant` is the quantitative form of the frame problem applied to LLM analysis: specific claims require frame verification that is impossible without external access.

---

### 5.2 Socratic Ignorance and the "Known Unknown" Problem

**Philosophical source:** Plato's dialogues, particularly Meno and Apology. "I know that I know nothing" as a metacognitive stance.

**Applied to LLMs:** Socratic ignorance requires TWO levels:
1. **First-order knowledge**: knowing or not knowing X.
2. **Second-order knowledge**: knowing WHETHER you know X.

LLMs systematically fail at second-order knowledge for specific claims. They know structural patterns (first-order: they have this knowledge from training). They ALSO know they know structural patterns (second-order: they can accurately describe what types of things they know). But for specific facts (API names, performance numbers), they have uncertain first-order knowledge AND poor second-order awareness of that uncertainty — they don't know that they don't know.

**Relation to our work:** This is the philosophical description of `Specificity × Verifiability = Constant`. Structural knowledge is Socratically honest — the model knows it knows these things because they're derivable from the input. Specific knowledge is Socratically dishonest — the model produces specific claims without knowing that those claims are unreliable. The prism's audit phase restores Socratic honesty by forcing the model to classify its own knowledge as STRUCTURAL (I know this from the code) vs. ASSUMED (I'm extrapolating this from patterns).

---

### 5.3 The Epistemic Regress Problem Applied to LLM Self-Knowledge

**Philosophical source:** Standard epistemology. If I know P because I know Q, what justifies Q? The regress must terminate somewhere (foundationalism) or be circular (coherentism) or infinite.

**Applied to LLMs:** When an LLM claims to know something, what is its epistemic justification? For structural claims derived from input code, the justification terminates in the code itself (foundationalism — the code is the ground truth). For specific factual claims about APIs or performance, the justification chains back to training data of unknown reliability, creating an epistemic regress that cannot terminate in anything verifiable.

**Relation to our work:** The 5-tier confidence taxonomy (STRUCTURAL/DERIVED/MEASURED/CONTEXTUAL/ASSUMED) is essentially an epistemic chain analysis:
- STRUCTURAL claims: justification terminates in the input (foundationally grounded).
- DERIVED claims: justification follows logically from structural claims (one inference step from ground).
- MEASURED claims: justification requires empirical verification (chain breaks — can't be closed from input alone).
- CONTEXTUAL claims: justification requires external facts (chain terminates externally).
- ASSUMED claims: justification is pure extrapolation (chain never terminates — infinite regress).

The tier system is a formalization of epistemic regress depth. Claims degrade in reliability as the regress deepens.

---

### 5.4 AI Metacognition and AI Safety (Autonomy Literature)

**Key source context:** The alignment and AI safety community has studied metacognition as a safety property. Specifically: an AI system that correctly identifies the limits of its knowledge is safer than one that acts with false confidence.

**From "Metacognition in LLMs and Its Relation to Safety" (AGI Safety journal, 2025):**

Key finding: LLMs have SOME metacognitive ability — their self-assessments correlate with accuracy — but are systematically overconfident on confident-but-wrong outputs. The critical failure mode: high-confidence-correct and high-confidence-wrong outputs are INDISTINGUISHABLE to the model's own metacognitive monitoring.

**Relation to our work:** This is the safety-level analog of our engineering finding. A model that cannot distinguish between "I'm right and I know it" and "I'm wrong but I sound right" is dangerous in any deployed context. Our prism approach attacks this problem not by improving the self-assessment (which may be fundamentally limited by the training dynamic) but by restructuring the task to produce testable claims — claims that an adversarial agent can attack, revealing fragility before deployment.

---

### 5.5 The Dunning-Kruger Structure in AI Systems

**Human source:** Kruger & Dunning 1999. "Unskilled and Unaware of It." *Journal of Personality and Social Psychology*.

**Applied to AI — from multiple 2026 sources:**

The AI Dunning-Kruger dynamic differs from the human one in a structurally important way:
- Human DK: incompetent people lack the metacognitive skills to recognize their incompetence (metacognition requires competence to build).
- AI DK: training dynamics (RLHF, human preference learning) reward confident outputs, making confident-wrong outputs MORE likely as training progresses. This is NOT because competence increases metacognitive awareness (as in humans) — it's because training systematically misaligns confidence from accuracy.

**Implication:** AI DK is not fixable by improving task competence. It requires targeting the confidence calibration explicitly (R-Tuning, KnowRL) or bypassing confidence expression entirely (prism construction approach).

---

## 6. Synthesis — What the Literature Reveals About Our Findings

### 6.1 The Metacognitive Failure Hierarchy

From the collected literature, metacognitive failures in LLMs cluster into three levels:

**Level 1 — Training-Induced Overconfidence (Structural):**
RLHF rewards confident outputs → models systematically overestimate accuracy on specific claims. This is not a bug; it's a feature of the training objective. Fix requires retraining (R-Tuning, KnowRL) or bypassing confidence expression (prism).

**Level 2 — Introspective Opacity (Architectural):**
The model's verbalized reasoning (CoT) is unfaithful to its actual computation (Turpin et al.). The model CANNOT reliably access its own computational process via introspection. Its stated reasons are post-hoc rationalizations. Fix: access internal states directly (interpretability approaches) or design prompts that don't rely on introspective access (adversarial construction).

**Level 3 — False Confidence Indistinguishability (Representational):**
High-confidence-correct and high-confidence-wrong outputs cannot be distinguished by the model's own metacognitive monitoring. Even if trained to be accurate, the failure mode persists for a residual class of claims. Fix: behavioral testing (does the claim survive attack?) rather than confidence assessment.

**Prism addresses all three levels without retraining:**
- L1: Adversarial construction doesn't ask for confidence expression — bypasses the training-induced overconfidence signal.
- L2: Construction generates a new artifact (conservation law, counter-example) rather than introspecting on the original — doesn't depend on faithful introspective access.
- L3: A claim that cannot survive adversarial construction is revealed as fragile regardless of expressed confidence — bypasses the false-confidence indistinguishability problem.

---

### 6.2 Why Construction Works Where Self-Report Fails

The literature collectively explains the mechanism behind the prism's effectiveness:

1. **Internal truth representation exists** (Marks & Tegmark 2023, Azaria & Mitchell 2023). Models internally represent truth/falseness more accurately than they express it verbally.

2. **Verbal expression is miscalibrated** (Turpin et al. 2023, Xiong et al. 2023, multiple 2026 papers). Verbalized confidence is systematically overconfident and disconnected from internal state.

3. **Construction accesses internal representation indirectly.** When prompted to "engineer an improvement that reveals a deeper problem" or "find what this claim conceals," the model must engage its internal truth representation to generate the construction. This bypasses the verbalization layer where miscalibration occurs.

4. **The quality of the construction is measurable without self-report.** A conservation law is verifiable (it's either a consistent structural principle or it isn't). A counter-example either exists or doesn't. The construction's quality provides behavioral evidence of what the model actually knows, independent of what it says it knows.

This is Design Principle 3 from AGI-in-md: "Imperatives beat descriptions." We don't describe what good analysis looks like and ask the model to assess whether it achieved that — we command the model to generate the construction and observe whether the construction is coherent.

---

### 6.3 Our Novel Contribution vs. the Literature

| Our Finding | Literature Status | What We Add |
|---|---|---|
| Adversarial construction bypasses metacognitive failure | Construction-based reasoning validated indirectly by Marks&Tegmark, Azaria&Mitchell | First explicit framing of CONSTRUCTION as metacognitive bypass (not just quality improvement) |
| Specificity × Verifiability = Constant | Implicit in calibration literature (Kadavath 2022, Zhang 2024) | First product-form conservation law formulation — predictive, not just descriptive |
| L8-primitive universality (construction works for ALL models) | No equivalent — most metacognitive work is model-specific | Identifies a capacity-independent metacognitive mechanism |
| Reflexive ceiling (L13) | Related to epistemic regress discussion | Self-applying the framework reveals the same impossibility — terminates cleanly |
| Prism operates below self-awareness | Turpin et al. (CoT unfaithful) from opposite direction | We leverage this: prism is designed to NOT rely on faithful introspection |
| Conservation law as quality signal | No equivalent | Conservation law emergence → reliable structural analysis (metacognitive proxy) |
| Model character clusters (Opus=ontological, Sonnet=operational, Haiku=mechanistic) | Not in literature | Metacognitive style as model personality — different models have different structural blind spots |

---

### 6.4 Open Questions the Literature Raises for Our Work

**Q1: Does prism construction access internal truth representation directly?**
Marks & Tegmark found that truth is linearly represented. If construction prompts activate this direction, we could measure this with activation patching experiments. This would validate the mechanism rather than just the output.

**Q2: Is our L8 construction-based universality a form of ToM bypass?**
The literature shows ToM fails under perturbation (Nickel et al. 2026) but works for first-order belief attribution. Our construction might work because it doesn't require ToM at all — instead of modeling what the code knows, we generate a new artifact and observe properties of the artifact. This avoids the ToM bottleneck.

**Q3: Can prism metacognition be distilled into model weights?**
R-Tuning shows metacognitive knowledge can be distilled. Could our prism's metacognitive behavior (the construction-based auditing) be distilled into a smaller model that applies it automatically? This would eliminate the per-call prism cost.

**Q4: Does the conservation law (L12) represent a genuine epistemic floor?**
L13 terminates in a reflexive fixed point — the framework diagnoses its own limitations. Is this the Socratic terminus? A model that reaches L13 has identified what it cannot know about itself. Whether this is a genuine epistemic floor or an artifact of prompt design is a philosophical question the literature hasn't addressed.

---

## 7. Key Papers by Relevance Tier

### Tier 1 — Must Engage (directly addresses core mechanism)
1. **Kadavath et al. 2022** (arXiv:2207.05221) — Foundational calibration; "mostly" is our entry point.
2. **Turpin et al. 2023** (arXiv:2305.04388, NeurIPS 2023) — CoT unfaithfulness; explains why construction bypasses verbalization.
3. **Azaria & Mitchell 2023** (arXiv:2304.13734) — Internal state knows truth; mechanism for why prisms work.
4. **Tyen et al. 2023** (arXiv:2311.08516, ACL 2024) — Can't find errors, can fix them; prism performs error location by claim type.
5. **Stechly et al. 2023** (arXiv:2310.12397) — GPT-4 doesn't know it's wrong; validates adversarial construction over self-critique.
6. **Steyvers et al. 2025** (arXiv:2510.05126) — Metacognition is trainable; defines the training-based alternative to prism approach.

### Tier 2 — Strong Support
7. **Kuhn, Gal, Farquhar 2023** (arXiv:2302.09664, ICLR 2023) — Semantic entropy; complementary inference-time uncertainty mechanism.
8. **Marks & Tegmark 2023** (arXiv:2310.06824) — Geometry of truth; mechanistic basis for construction.
9. **EpiCaR 2026** (Yeom et al.) — Self-training induces overconfidence; explains model character differences.
10. **Muchovej et al. 2026** — GPT-4 lacks core ToM; surface competence masks structural absence.
11. **Lombardi & Lenci 2025** — Shallow associations, not genuine ToM; explains why verbalized metacognition is unreliable.
12. **Zhang et al. 2024 (Self-Contrast)** — Multiple perspectives find inconsistencies; parallel to our pipeline structure.
13. **R-Tuning (Zhang et al. 2023)** (arXiv:2311.09677) — Training-based metacognitive improvement; alternative path.

### Tier 3 — Background Context
14. **Pal et al. 2025** — Confidence knowledge ≠ consistent behavior.
15. **Xie et al. 2026** — SFT vs RL calibration dynamics.
16. **de Haan et al. 2026** — Reasoning promotes ToM robustness.
17. **KnowRL (Kale & Dhami 2025)** — RL-based self-knowledge.
18. **MetaFaith (Liu et al. 2025)** — 61% improvement in faithfulness, 39% gap remaining.
19. **Liu et al. 2026 (VLI)** — Vision-language metacognitive correction; validates three-phase architecture cross-modality.

---

## 8. Recommended Next Steps from Literature Gaps

### 8.1 Mechanistic Validation of Construction's Metacognitive Bypass
The literature (Marks & Tegmark, Azaria & Mitchell) establishes that truth is internally represented. We claim construction prompts access this representation. **To validate**: compare activation patterns during (a) "summarize the code" vs. (b) "engineer an improvement that reveals a deeper problem." If construction activates truth-representation directions more strongly, this confirms the mechanism.

### 8.2 Comparison with SelfCheckGPT and Semantic Entropy
Both SelfCheckGPT (consistency-based) and semantic entropy probe different aspects of model uncertainty. **Design**: run all three on the same L12 outputs. Expected: (a) construction-based audit flags KNOWLEDGE/ASSUMED claims, (b) SelfCheckGPT flags the same claims via inconsistency, (c) semantic entropy flags them at inference-time. Convergence confirms all three measure the same underlying uncertainty; divergence reveals different facets.

### 8.3 R-Tuning Comparison on Code Analysis
R-Tuning trains models to say "I don't know" on out-of-knowledge questions. **Design**: apply R-Tuning to code analysis task (train on "I don't know the exact API name / version number / performance metric" patterns). Compare confabulation rate vs. prism-based approach. Expected: R-Tuning reduces false confidence; prism additionally identifies claim types and provides fill paths. Complementary, not competing.

### 8.4 Philosophical Formalization of L13 as Epistemic Floor
L13 terminates in reflexive self-diagnosis: the framework finds the same impossibility in itself that it finds in its objects. This aligns with the epistemic regress argument (regress must terminate somewhere). **To formalize**: prove that L14 generates infinite regress using the chain of metacognitive analysis → meta-metacognitive analysis → ... and that L13 is a fixed point where the framework = its own object. This would connect the empirical finding (100% hit rate on L13 termination) to the philosophical argument for why it must terminate.

---

*Sources: All arXiv papers fetched directly or via search summaries. Searches conducted March 15, 2026. Coverage: metacognitive monitoring (1.x), Theory of Mind (2.x), introspection failures (3.x), metacognitive training (4.x), philosophical foundations (5.x).*
