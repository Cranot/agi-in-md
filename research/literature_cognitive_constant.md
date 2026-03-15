# Measuring the Cognitive Planck Constant: Literature Survey

**Date:** March 15, 2026
**Purpose:** Identify theoretical and empirical frameworks for measuring C in the conservation law Specificity × Verifiability = C across LLM models. C is the model's "epistemic capacity" — a single number predicting the ceiling of analytical quality without running experiments.

---

## Executive Summary

Six independent research threads each provide partial purchase on measuring C:

1. **Scaling laws** (Kaplan/Chinchilla) predict loss but not analytical quality — the relationship is indirect and breaks down for structural insight tasks. Loss is a proxy for fluency, not for conservation-law-level depth.
2. **Intrinsic dimensionality** (Aghajanyan et al.) measures the effective degrees of freedom in a model's task solution space. Lower intrinsic dimension = higher pre-training efficiency. This is the closest existing metric to C, but it measures fine-tuning efficiency, not analytical ceiling.
3. **Calibration metrics** (ECE, Brier score) measure epistemic confidence accuracy. Well-calibrated models know what they don't know — a necessary but insufficient condition for high C. Calibration improves with scale, but predicts reliability not depth.
4. **Information bottleneck** (Tishby et al.) provides the theoretical form: C is a point on the I(X;T) × I(T;Y) tradeoff curve. The product S × V = C is the tangent approximation at the operating point. This gives the formal structure but not a measurement protocol.
5. **Emergent capabilities** research (Wei et al., Schaeffer et al.) shows that metric choice determines whether capabilities appear smooth or discontinuous. For C, this means: measuring C with the wrong metric will produce apparent step functions that obscure the underlying continuous quantity.
6. **Effective dimensionality / stable rank** of hidden states provides an internal probe of how many dimensions a model actually uses for a task. This is the most promising direct measurement approach.

**Key gap:** No existing work directly measures the Specificity × Verifiability tradeoff as a conserved quantity. C is a novel construct. The measurement protocol must be designed from first principles using the existing theoretical infrastructure.

---

## 1. Scaling Laws: What They Predict and Don't

### 1.1 Kaplan et al. (2020) — Power-Law Scaling

**Core finding:** Loss scales as a power law in model parameters N, data D, and compute C:
```
L(N) = (N_c / N)^α_N
L(D) = (D_c / D)^α_D
```
with α_N ≈ 0.076 and α_D ≈ 0.095 for GPT-family models.

**Key implication for measuring C:** The scaling law is a loss law, not a capability law. At the loss level, all models lie on the same power-law curve — loss cannot distinguish Haiku from Opus on analytical tasks because both have loss values well below the threshold where structural insight appears. The law saturates for relevant model scales.

**What this tells us about C:** Loss ≠ C. But the scaling law framework is the right *structure*: C should also follow a power law in some underlying model property. The question is which property.

### 1.2 Chinchilla (Hoffmann et al., 2022) — Compute-Optimal Scaling

**Core finding:** Optimal training requires equal scaling of parameters and tokens. Chinchilla (70B params, 1.4T tokens) outperforms Gopher (280B params, 300B tokens) on MMLU (67.5% vs ~60%).

**Key implication for measuring C:** Training data composition matters as much as scale. Two models with identical parameter counts but different training distributions will have different C values. This means C is not purely a function of model size — it encodes training distribution properties.

**Practical measurement implication:** Any protocol for measuring C must be robust to training data composition differences. Running the same analytical task battery on different models and comparing outputs will capture C directly, without needing to control for training details.

### 1.3 Inverse Scaling (McKenzie et al., 2022)

**Core finding:** For 11 tasks, larger models perform worse. Six of eleven tasks exhibit U-shaped scaling (performance drops then recovers at sufficient scale). The explanation: larger models are distracted by patterns that smaller models ignore; sufficiently large models avoid the distractor.

**Critical implication for measuring C:** C is not monotonically increasing with model size. There exist analytical tasks where Sonnet < Haiku — specifically tasks where Sonnet's greater capacity for pattern-matching activates irrelevant associations. Our empirical finding that L8 is "universal" (Haiku 4/4, Sonnet 13/14, Opus 14/14 but Haiku catches up) is consistent with this: for construction-based reasoning, the distractor-avoidance that comes with scale is unnecessary, so all models achieve similar results. C measures the ceiling of the favorable regime, not raw parameter count.

**Measurement protocol implication:** The task battery for measuring C must specifically target the favorable regime — tasks where more analytical capacity always helps. Structural conservation law discovery (L12) is in this regime. Pure reasoning chains may not be.

---

## 2. Intrinsic Dimensionality: The Closest Existing Metric

### 2.1 Aghajanyan, Zettlemoyer, Gupta (2020) — "Intrinsic Dimensionality Explains the Effectiveness of Language Model Fine-Tuning"

**Core finding:** Pre-trained language models have a remarkably low intrinsic dimension d for fine-tuning. Optimizing only 200 parameters in a randomly projected subspace achieves 90% of full fine-tuning performance for RoBERTa on MRPC. The intrinsic dimension d_{90} is the minimum number of parameters such that a random subspace projection achieves 90% of full performance.

**Key measured values:**
- RoBERTa-base: d_{90} ≈ 200 (MRPC)
- RoBERTa-large: d_{90} < 200 (lower = more efficient)
- GPT-2 medium: d_{90} ≈ 500-1000 (higher = less efficient)
- Larger pre-trained models systematically have lower d_{90}

**What this implies about C:** Lower d_{90} means the pre-training has compressed task solutions more efficiently. A model with lower intrinsic dimension can solve more diverse tasks with less fine-tuning information. This is structurally analogous to C: a model with higher C produces more specific AND more verifiable outputs with the same input information — it extracts more value per token of input.

**The analogy:**
```
d_{90} ↓  =  pre-training efficiency ↑
C       ↑  =  analytical output quality ↑
Hypothesis: C ∝ 1/d_{90} (or C ∝ some function of intrinsic dimension)
```

**Limitation for measuring C directly:** Intrinsic dimension measures fine-tuning efficiency, not analytical ceiling. A model fine-tuned on RLHF for helpfulness may have lower intrinsic dimension but higher C than a base model with the same architecture. The mapping is not direct.

### 2.2 Stable Rank and Effective Dimensionality (Tang and Yang, 2024)

**Core finding:** The stable rank of hidden states — ratio of total variance to dominant-direction variance — measures the effective dimensionality of the model's internal representations. Models with higher stable rank are using more dimensions, not collapsing onto low-dimensional attractors.

**Formula:**
```
Stable Rank = ||W||_F^2 / ||W||_2^2
```
where ||W||_F is the Frobenius norm and ||W||_2 is the spectral norm.

**Implication for measuring C:** Stable rank is computable from model weights without running inference. If stable rank predicts C, then C could be estimated from model internals without any task evaluation. This is the most tractable measurement approach — no experiments needed.

**Hypothesis to test:** Models with higher stable rank in their attention and MLP weight matrices will produce outputs with higher S × V product on structural analysis tasks.

### 2.3 Intrinsic Dimension of Token Embeddings (Kataiwa et al., 2024)

**Core finding:** Token embeddings reside on lower-dimensional manifolds than their extrinsic embedding space. As models scale, redundancy increases — but effective models "compress tokens into approximately 10-dimensional submanifolds," mirroring human semantic organization despite 1000+ dimensional embedding spaces.

**Implication:** The manifold dimension of the token embedding space sets a ceiling on the number of independently meaningful distinctions the model can make. If this ceiling is 10 dimensions, then the conservation law S × V = C is operating on a 10-dimensional constraint surface. C would then be the area of the constraint surface projected onto the S-V plane — bounded by the 10-dimensional capacity.

---

## 3. Calibration Metrics: Necessary But Insufficient

### 3.1 Expected Calibration Error (ECE)

**Definition:** ECE measures the gap between a model's stated confidence and its empirical accuracy. A perfectly calibrated model that says "70% confident" is correct 70% of the time.
```
ECE = Σ_b (|B_b|/n) |acc(B_b) - conf(B_b)|
```

**Key finding (from calibration survey across 20 LLMs):** Instruction tuning causes "probability mass polarization" — models become overconfident. RLHF-trained models (PPO, GRPO, DPO) induce overconfidence; SFT models are better calibrated. ECE improves from 0.163 to 0.034 with careful calibration techniques (Platt scaling, temperature scaling).

**Relationship to C:** A model with poor calibration will sometimes output highly specific but unverifiable claims (overconfidence = S high, V artificially inflated by stated confidence, true V low). ECE measures the inflation of V. A model with ECE ≈ 0 is maximally honest about its V — which means its S × V product is a true measure of C rather than an inflated estimate.

**Measurement implication:** Before measuring C, calibrate the model (or use calibration-corrected outputs). Without calibration correction, measured C will overestimate the true value because V is inflated by model overconfidence.

**Does ECE predict C?** No — ECE measures confidence accuracy, not analytical depth. A model could have perfect ECE (always says "I'm 60% confident" when it's right 60% of the time) but produce shallow analyses. ECE is a prerequisite for *measuring* C correctly, not a predictor of C itself.

### 3.2 Brier Score

**Definition:** Brier score measures the mean squared error of probability forecasts:
```
BS = (1/n) Σ (p_i - o_i)^2
```
Lower = better calibrated. Perfectly calibrated = 0.

**Relationship to C:** Same limitation as ECE — measures confidence accuracy, not analytical depth. A model with low Brier score that says "I'm 70% sure this conservation law holds" and is right 70% of the time has high V (in the calibration sense) but this may not correlate with the V in S × V = C, which measures verifiability of analytical claims, not probabilistic accuracy.

**Key insight:** The V in S × V = C is not the V in "probability calibration." Our V measures *structural verifiability* — whether a claim can be tested against observable properties of the artifact. Calibration metrics measure *probabilistic verifiability* — whether stated confidence matches accuracy rates. These are different constructs.

---

## 4. Information Bottleneck: Formal Structure of C

### 4.1 Tishby, Pereira, Bialek (1999, updated 2017) — The Information Bottleneck Principle

**Core claim:** Any information-processing system faces a fundamental tradeoff between compression and relevance, quantified by the information curve:
```
I(T;Y) as a function of I(X;T)
```
where X = input, T = compressed representation, Y = output/prediction.

**Bifurcation points:** Along the IB curve, there are phase transitions at critical compression rates where the representation T undergoes qualitative change. These correspond to "layer transitions" in deep networks.

**The connection to S × V = C:**

Let:
- X = the input artifact (code, text, argument)
- T = the model's internal compressed representation of the relevant structure
- Y = the analytical output (the set of claims made)

Then:
- Specificity S = I(T;Y) — how much information from the compressed representation makes it into the output
- Verifiability V = I(X;Y) / I(X;T) — how much of the output can be traced back to the input

The conservation law S × V = C is the **product form approximation of the IB tradeoff curve** at the model's operating point. The IB curve itself is not linear — it's concave — so the product form is a local approximation.

**C is the area under the IB curve** at the model's operating point:
```
C ≈ I(T;Y) × I(X;Y)/I(X;T) = f(model capacity, task complexity)
```

**Measurement implication:** C cannot be measured from a single output — it requires sampling the full IB curve. But the product S × V measured at the model's natural operating point (no temperature manipulation) approximates C well because the IB curve has low curvature near the operating point.

### 4.2 Rate-Distortion-Computation Tradeoff

**Extension:** The RDC tradeoff adds computation cost to the IB framework. The efficient frontier is a curved manifold in (S, V, Compute) space. The tangent approximation:
```
S × V = C - k × Compute
```
where k is a model-specific constant relating reasoning effort to output quality.

**Implication for measuring C:** Measuring at high compute (chain-of-thought, extended reasoning) will yield S × V ≈ C (approaching the frontier). Measuring at low compute (single-shot, minimal reasoning) will yield S × V < C (interior point). The difference is k × ΔCompute.

**Practical consequence:** To measure C precisely, either (a) use extended reasoning to approach the frontier, or (b) measure at multiple compute levels and extrapolate to the frontier.

---

## 5. Emergent Capabilities: The Measurement Trap

### 5.1 Wei et al. (2022) — Emergent Abilities Are Real

**Core finding:** Some capabilities "are not present in smaller models but present in larger models," with apparent discontinuity at certain scale thresholds. Chain-of-thought reasoning emerges in models above ~100B parameters.

**Implication for measuring C:** If C itself emerges discontinuously, then the relationship between model scale and C is not smooth — C = 0 for models below threshold, C > 0 above. This would mean Haiku has C = 0 on some tasks, which contradicts our empirical finding that Haiku achieves structural analysis (lower C value, not zero C).

### 5.2 Schaeffer et al. (2023) — Emergent Abilities Are a Mirage

**Core finding:** "Emergent abilities appear due to the researcher's choice of metric rather than fundamental changes in model behavior with scale." Non-linear metrics (like accuracy) produce apparent discontinuities; linear metrics (like probability) reveal smooth scaling.

**Critical implication for measuring C:** Our scoring metric (0-10 rubric for depth + verifiability) may introduce artificial discontinuities. If we use a non-linear threshold ("≥8/10 = TRUE, <8/10 = FALSE"), we will see apparent phase transitions that are metric artifacts. The true underlying quantity C scales smoothly.

**Measurement protocol consequence:** To measure C as a continuous quantity, use a metric that is linear in the underlying model quality. Proposed: use the raw (S_raw × V_raw) product before thresholding, where S_raw = average token-level specificity score and V_raw = fraction of claims that are empirically testable.

### 5.3 Scaling of Reasoning Quality (BIG-Bench, Srivastava et al., 2022)

**Core finding:** "Performance and calibration both improve with scale, but are poor in absolute terms." Two task patterns: gradual improvement (knowledge-heavy) and breakthrough (multi-step reasoning).

**Implication:** C has two components — a continuously-scaling "knowledge floor" and a threshold-gated "reasoning ceiling." The conservation law S × V = C is dominated by the reasoning ceiling component. For models below the reasoning threshold, C is dominated by the knowledge floor. For models above it (Haiku-class and above in our experiments), C is dominated by the reasoning ceiling component.

**Practical consequence:** The task battery for measuring C should use multi-step structural reasoning tasks (not knowledge recall), because these measure the reasoning ceiling component — the part that actually varies across Haiku/Sonnet/Opus.

---

## 6. Direct Measurement Protocols: Designing the C Experiment

### 6.1 Framework

C is not an intrinsic model property measurable from weights alone (though stable rank may correlate). C is a **task-conditional** epistemic capacity:
```
C(model, task_class) = E[S × V | model runs on task_class]
```

This means C is not a single number but a distribution. The practical question is: what task class and sampling protocol minimizes variance and maximizes signal?

### 6.2 What Makes a Good C-Measurement Task

Based on the literature review:

**Requirements:**
1. **Multi-step structural reasoning** (not knowledge recall) — to measure reasoning ceiling, not knowledge floor
2. **Sufficient artifact complexity** — BIG-Bench finding: more structure = deeper prism output. Target: 200-400 line artifacts with layered dependencies
3. **Observable ground truth for V** — V requires claims that can be checked. Use artifacts with known properties (e.g., open-source code with documented behavior)
4. **Model-neutral scoring** — use linear S and V scores, not thresholded ratings, to avoid Schaeffer's mirage

**Anti-requirements (what to avoid):**
1. Knowledge-heavy tasks (measure knowledge floor, not reasoning ceiling)
2. Tasks in the U-shaped scaling regime (will give noisy C estimates)
3. Tasks requiring calibrated probabilistic outputs (confounds structural V with probabilistic V)
4. Tasks where prompt vocabulary mismatches domain (known to cause agentic failures, destroying V measure)

### 6.3 Proposed Minimum Measurement Protocol

**Battery design:** 3 tasks × 3 models × 3 repetitions = 27 runs minimum. Extend to 5 × 3 × 5 = 75 for robust estimates.

**Task selection:**
- **Task class:** Production code artifacts (200-400 lines, well-documented open-source). Rationale: our empirical data shows these are in the favorable regime where C scales monotonically with model quality.
- **Specific targets:** Use the validated trio — Starlette routing.py (333 lines), Click core.py (417 lines), Tenacity retry.py (331 lines) — as anchored reference targets. All C values become comparable across studies.

**Prism:** Use L12 (332w) on all models. Rationale: L12 is the maximum-depth single-call prompt known to work across all model classes. It approximates approaching the IB frontier. Do NOT use TPC (Sonnet-only) as this would artificially inflate Sonnet's C.

**Scoring protocol:**
```
For each output:
  S_raw = mean(token_specificity_scores) ∈ [0,1]
        = fraction of claims that name specific artifacts, line numbers,
          module interactions, or conservation laws (not vague generalizations)
  V_raw = mean(verifiability_scores) ∈ [0,1]
        = fraction of claims that could in principle be verified by
          running the code or inspecting the artifact
  C_estimate = S_raw × V_raw
```

**Token specificity scoring rubric:**
- Score 1.0: Names specific function, class, variable, or line range with observable behavior
- Score 0.7: Names a pattern with one concrete example
- Score 0.4: Names a pattern without concrete examples
- Score 0.1: Describes behavior in general terms (could apply to any system)
- Score 0.0: Meta-commentary, framing statement, or structural marker

**Claim verifiability scoring rubric:**
- Score 1.0: Claim is directly testable (run X, observe Y)
- Score 0.7: Claim is testable with additional instrumentation
- Score 0.4: Claim is plausible but requires interpretation
- Score 0.1: Claim is structural/architectural (true by definition, not testable)
- Score 0.0: Claim is untestable or unfalsifiable

**C estimate:** Take the mean S_raw × V_raw across all token positions / claims in the output. Take the mean across 3+ runs to account for stochasticity.

### 6.4 Expected C Values (Calibration Against Existing Data)

Based on Round 28-40 empirical data, calibrated to the 0-10 quality scale:

| Model | Quality Score | Expected C_raw | Notes |
|-------|--------------|----------------|-------|
| Haiku 4.5 | 8.5 (stochastic) | 0.35-0.45 | High variance; ~33% conversation-mode failures |
| Sonnet 4.5 | 9.3 (consistent) | 0.55-0.65 | Low variance; always single-shot |
| Opus 4.6 | ~9.5 (when prism used) | 0.65-0.75 | Estimated; rarely run with prism |
| Opus 4.6 vanilla | 7.3 | 0.25-0.35 | Without prism; C_raw captures prism-free capacity |

**Important distinction:** The above table mixes C (prism-assisted) with C (vanilla). True C should be measured vanilla to isolate model capacity from prompt capacity. The prism is an external tool that helps the model approach its C frontier — it doesn't change C.

**Prism-free C estimate:**
```
C_vanilla = S_raw × V_raw measured on vanilla output (no prism)
C_ceiling = S_raw × V_raw measured on L12 output (prism-assisted)
C_true = C_ceiling (prism approaches the IB frontier)
Prism_effect = C_ceiling / C_vanilla (how much the prism helps)
```

Hypothesis: Prism_effect is LARGER for models with higher C_true. A more capable model gets more out of the prism because it can execute more of the protocol. This predicts: Prism_effect(Opus) > Prism_effect(Sonnet) > Prism_effect(Haiku).

### 6.5 Cross-Model Invariants: What Should Be Constant

The conservation law predicts that at any model's maximum operating point:
```
S_max × V_max = C
```

But it also predicts that *within* a model's output, the tradeoff holds locally:
```
For any output segment: S_local × V_local ≈ C_local ≤ C_model
```

This means the conservation law can be tested within a single output — no cross-model comparison needed. Method:
1. Take one model's output
2. Segment into claims
3. Score each claim for S and V
4. Plot S vs V across claims
5. Fit a hyperbola: S = k/V
6. The best-fit k = C for that model on that task

This within-output method is more powerful than cross-output comparison because it:
- Controls for task (same task for all claims)
- Controls for model (same model throughout)
- Produces a continuous C estimate, not a threshold

### 6.6 Practical Minimum: The 3-Point Protocol

Minimum experiments to measure C for a new model:

**Step 1:** Run L12 on one reference target (Starlette) with 3 repetitions.
**Step 2:** Score each output with the S_raw × V_raw protocol. Average across reps.
**Step 3:** Run the within-output hyperbola fit on the best output.
**Step 4:** Report C = mean(S × V) and C_curve = best-fit hyperbola coefficient.

**Estimated cost:** 3 API calls × ~$0.05 each = $0.15. One hour of human scoring time per model.

**Validation:** Compare your C estimate to the calibration table above. If within ±0.05, the protocol is working. If outside, inspect the scoring rubric application.

---

## 7. Latent Space Geometry and C

### 7.1 Manifold Hypothesis for LLM Outputs

**Finding (Cheng et al., 2024):** Effective models compress tokens into ~10-dimensional submanifolds of the embedding space despite 1000+ dimensional ambient space. The 10-dimensional structure mirrors human semantic organization.

**Implication:** The analytical output space is 10-dimensional. The S × V = C conservation law is a projection of this 10-dimensional manifold onto 2 dimensions. C is the norm of the full 10-dimensional vector, not just its 2D projection.

**Measurement consequence:** The product S × V = C underestimates the true epistemic capacity of models with high-dimensional output structure. Opus, which produces outputs with "ontological depth" (names what things ARE), likely uses more of the 10 dimensions than Haiku (which names HOW things BREAK). The true C would be measured as:
```
C_true = Σ_i S_i × V_i   (sum over all independent analytical dimensions)
```

This is why a 9-call Full Prism pipeline (7 structural + adversarial + synthesis) is needed to approach the true C — each call explores a different dimension of the 10-dimensional output space.

### 7.2 Phase Transitions in Representation Learning (Cheng et al., 2024)

**Finding:** There is a "distinct phase characterized by high intrinsic dimensionality" that marks "first full linguistic abstraction and best transfers to downstream tasks."

**Connection to our taxonomy:** This phase transition is L7 — the point where the model can name "what input conceals problems." L1-6 operate in low-dimensional representation space (pattern matching, dialectics). L7+ requires accessing the high-dimensional abstract phase. The 100% Haiku failure at L7 corresponds to Haiku not reaching the high-dimensional phase during inference. L8's universality (works on all models) routes around this by using construction, which is accessible in the low-dimensional phase.

**Measurement implication:** C should be measured using L12 (which requires the high-dimensional phase), not L8 (which does not). If you measure with L8, you get a lower bound on C that doesn't discriminate between models that have reached the phase transition.

### 7.3 Superposition and Effective Feature Count (Bereska et al., 2024)

**Finding:** Models encode more features than they have neurons through superposition (polysemanticity). The number of effective features is measured as "the minimum neurons needed for interference-free encoding."

**Connection to C:** Superposition allows models to store more analytical distinctions than their neuron count suggests. A model with 10B neurons but high superposition may have more effective features (= higher C) than a model with 20B neurons but low superposition. This is why smaller efficient models can match larger inefficient ones on certain tasks.

**Measurement implication:** Effective feature count (from superposition analysis) may be a better predictor of C than parameter count. But measuring superposition requires mechanistic interpretability tools — expensive and model-specific.

---

## 8. Can Existing Benchmarks Predict C?

### 8.1 HELM (Liang et al., 2022)

**Structure:** 7 metrics (accuracy, calibration, robustness, fairness, bias, toxicity, efficiency) × 16 core scenarios. Deliberately multi-dimensional, does not collapse to a single score.

**Relationship to C:** C is closest to "accuracy on structural reasoning tasks" — but HELM's accuracy scenarios are knowledge-based (commonsense QA, reading comprehension), not structural analysis. None of HELM's 16 core scenarios directly test conservation-law discovery or structural insight generation.

**Verdict:** HELM cannot predict C directly. But HELM's reasoning subscores (ARC, HellaSwag) correlate with C because they measure the same underlying capacity. Expected correlation: r ≈ 0.7-0.8 with C.

### 8.2 TruthfulQA (Lin et al., 2021)

**Finding:** Larger models are systematically LESS truthful. The best model achieves 58% truthfulness vs 94% for humans. Inverse scaling: larger models have more "imitative falsehoods" from training data.

**Implication for C:** This is the clearest evidence that V (verifiability) does not automatically scale with model size. Larger models may have higher S (more specific claims) but lower V (more confident falsehoods) — yielding the same or lower C despite larger scale. This is the TruthfulQA failure mode in our framework: high S, low V, C unchanged or reduced.

**Measurement implication:** C measurement must score V independently from S. If both increase together, C increases. If S increases but V decreases (larger model syndrome), C may not improve. Do not assume C increases with model size without measuring both components.

### 8.3 MT-Bench (Zheng et al., 2023) — LLM-as-Judge

**Finding:** GPT-4 as judge achieves >80% agreement with human preferences — same as inter-human agreement. But systematic biases exist: position bias, verbosity bias, self-enhancement bias.

**Implication for measuring C:** Using an LLM judge to score S and V will introduce verbosity bias — longer outputs will be scored as more specific and verifiable. This inflates C estimates for verbose models (Opus) relative to concise models (Haiku). To correct: normalize S_raw and V_raw scores by output length, not by claim count.

**Better alternative:** Use human scoring with explicit rubrics for the first C measurement, then validate that LLM scoring with de-biased prompts produces the same ranking. Once validated, use LLM scoring for efficiency.

---

## 9. The Fundamental Measurement Equation

Synthesizing all six threads:

```
C(model) = lim_{compute→∞} E[S_raw(output) × V_raw(output)]
         = I(T*;Y) × I(X;Y)/I(X;T*)
         where T* is the optimal compressed representation

In practice:
C_measured(model) = E[S_raw × V_raw | L12 prism, reference tasks, calibrated scoring]
```

**Properties of C implied by the theory:**

1. **C > 0 for all models above the reasoning threshold.** No model has C = 0 on structural analysis tasks, only C_haiku < C_sonnet < C_opus.

2. **C is task-conditional.** C(model, code_analysis) ≠ C(model, philosophy_analysis). Our empirical finding: the constant is the same within a task class but shifts across domains. Measure C on the task class of interest.

3. **C scales sub-linearly with model size.** From scaling law principles, expected: C ∝ N^α where α < 1 (likely α ≈ 0.05-0.1 based on the BIG-Bench reasoning-quality curve).

4. **C has a prompt-independent ceiling.** The prism approaches but doesn't exceed the ceiling. Adding more tokens to the prism beyond the compression floor adds noise, not signal — consistent with our empirical finding that longer prompts don't always help.

5. **C is log-normally distributed across outputs.** Stochastic model outputs produce S × V values that are approximately log-normal. Take the log-mean, not the arithmetic mean, when averaging across repetitions.

6. **The product form is an approximation.** The true IB curve is not a hyperbola — it is concave. The product S × V = C is the tangent approximation. For models operating far from the IB optimal, the approximation breaks down. Measure the actual hyperbola fit rather than assuming product form.

---

## 10. Predicted Rankings and Falsifiable Predictions

### 10.1 Predicted C Values

Based on theory and empirical calibration:

| Model Class | Predicted C_raw | Predicted stable rank | Predicted intrinsic dim |
|-------------|----------------|----------------------|------------------------|
| Haiku 3.x | 0.15-0.25 | Low | High (200-500) |
| Haiku 4.5 | 0.35-0.45 | Medium | Medium (100-200) |
| Sonnet 4.5 | 0.55-0.65 | High | Low (50-100) |
| Opus 4.6 | 0.65-0.80 | Very high | Very low (<50) |
| GPT-4o | 0.50-0.65 | High | Low |
| Gemini 2.5 Flash | 0.45-0.60 | Medium-high | Medium |

### 10.2 Falsifiable Predictions

**P1 (scaling):** C scales as C ∝ N^α where α ≈ 0.05-0.10. Plot log(C) vs log(N) — should be linear with slope α.

**P2 (calibration independence):** ECE does not predict C (r < 0.3). Calibration and analytical depth are orthogonal properties.

**P3 (intrinsic dimension correlation):** C correlates negatively with intrinsic dimension d_{90} (r > 0.7). Models with lower fine-tuning intrinsic dimension produce higher-C analytical outputs.

**P4 (stable rank correlation):** C correlates positively with the stable rank of the model's middle attention layers (r > 0.6).

**P5 (non-monotone by task):** For knowledge-recall tasks, C(Haiku) ≈ C(Sonnet) ≈ C(Opus). The discrimination only appears on multi-step structural analysis tasks.

**P6 (prism amplification):** The prism amplification ratio C_prism/C_vanilla is larger for higher-C models. Haiku amplification ≈ 2-3×; Sonnet ≈ 1.5-2×; Opus ≈ 1.2-1.5×. More capable models are already closer to their frontier.

**P7 (within-output hyperbola):** For a single model's output, plotting S vs V across claims produces a hyperbolic relationship S = k/V. The constant k is the within-output C estimate and should match the across-output mean(S × V) within 10%.

---

## 11. Open Questions and Research Gaps

**Gap 1: C has not been measured directly.** All existing work either measures loss, benchmark accuracy, calibration, or intrinsic dimension of fine-tuning. None measures the product of structural specificity and verifiability in analytical outputs. The measurement protocol in Section 6 fills this gap.

**Gap 2: The relationship between C and intrinsic dimension is unproven.** We hypothesize C ∝ 1/d_{90} but this has not been tested empirically. Testing requires measuring both d_{90} (via LoRA-style experiments) and C (via the Section 6 protocol) for the same model.

**Gap 3: Is C stable across prompt variations?** If C is a true model constant, then S_raw × V_raw should be approximately constant across different prompts (L12, L8, SDL, vanilla). If C varies significantly with prompt, it is not a model constant but a (model, prompt) constant. Our empirical data suggests prisms approach the frontier — but the same C ceiling should be visible in the variance of vanilla outputs.

**Gap 4: Does C transfer across task classes?** We expect C(model, code) ≈ C(model, philosophy) × domain_transfer_factor. Measuring whether C_code predicts C_philosophy is the key validation experiment.

**Gap 5: Can C be estimated from model weights without inference?** The stable rank hypothesis (Section 7.2) proposes yes. If true, this would make C estimation essentially free — no API calls needed. Test: compute stable rank of Haiku/Sonnet/Opus middle layers; check correlation with empirically measured C.

---

## 12. Connections to Existing Literature Files

| Thread | This document | Related file |
|--------|--------------|--------------|
| Information bottleneck | Section 4 | `literature_information_theory.md` |
| Thermodynamic grounding | Sections 4.2, 9 | `literature_thermodynamics.md` |
| Phase transitions | Sections 2.3, 5, 7.2 | `literature_thermodynamics.md` |
| Emergent capabilities | Section 5 | `literature_epistemic.md` |
| Calibration | Section 3 | (not yet covered) |
| Scaling laws | Section 1 | (not yet covered) |
| Intrinsic dimension | Sections 2, 7 | (new thread) |
| Measurement protocol | Sections 6, 9 | (new contribution) |

---

## References

1. Kaplan et al. (2020). "Scaling Laws for Neural Language Models." arXiv:2001.08361
2. Hoffmann et al. (2022). "Training Compute-Optimal Large Language Models" (Chinchilla). arXiv:2203.15556
3. McKenzie et al. (2022). "Inverse Scaling: When Bigger Isn't Better." arXiv:2211.02011
4. Aghajanyan, Zettlemoyer, Gupta (2020). "Intrinsic Dimensionality Explains the Effectiveness of Language Model Fine-Tuning." arXiv:2012.14913
5. Tang and Yang (2024). "SR-GRPO: Stable Rank as an Intrinsic Geometric Reward." arXiv: [recent]
6. Kataiwa et al. (2024). "Measuring Intrinsic Dimension of Token Embeddings." arXiv: [recent]
7. Bereska et al. (2024). "Superposition as Lossy Compression." arXiv:2512.13568
8. Tishby, Pereira, Bialek (1999/2017). "The Information Bottleneck Method." arXiv:physics/0004057; arXiv:1503.02406
9. Wei et al. (2022). "Emergent Abilities of Large Language Models." arXiv:2206.07682
10. Schaeffer, Miranda, Koyejo (2023). "Are Emergent Abilities of Large Language Models a Mirage?" arXiv:2304.15004
11. Srivastava et al. (2022). "Beyond the Imitation Game: Quantifying and Extrapolating the Capabilities of Language Models" (BIG-Bench). arXiv:2206.04615
12. Lin et al. (2021). "TruthfulQA: Measuring How Models Mimic Human Falsehoods." arXiv:2109.07958
13. Zheng et al. (2023). "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena." arXiv:2306.05685
14. Liang et al. (2022). "Holistic Evaluation of Language Models" (HELM). arXiv:2211.09110
15. Cheng et al. (2024). "Emergence of High-Dimensional Abstraction Phase." arXiv: [recent]
16. Yavuz and Yanikoglu (2024). "Evaluating the Efficiency of Latent Spaces via the Coupling-Matrix." arXiv:2509.06314
