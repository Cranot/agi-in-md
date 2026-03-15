# Economics, Mechanism Design, and Auction Theory Applied to Cognitive Prism Pipelines

**Date:** March 15, 2026
**Purpose:** Map established economic theory to the empirical discoveries in this project — specifically to the Specificity × Verifiability = Constant conservation law, the multi-stage gap detection pipeline, and the general problem of optimal analytical budget allocation.

---

## Executive Summary

Six economic frameworks converge on the same underlying structure our experiments uncovered:

1. **Constrained optimization / Lagrangian theory** — S×V=C IS a constraint surface. The Lagrange multiplier gives the shadow price of the trade-off: exactly how much verifiability you surrender per unit of specificity gained. KKT conditions characterize every feasible operating point.
2. **Value of information (Blackwell / EVPI / EVSI)** — formalizes when paying for gap detection is rational. The pipeline stage is worth running if and only if EVSI exceeds stage cost. Blackwell's theorem orders our pipeline stages by informativeness — it predicts which stages to run first.
3. **Mechanism design and auction theory** — the pipeline is an attention auction. Each claim "bids" for verification based on impact × risk. Myerson's optimal auction allocates scarce verification budget to highest-virtual-valuation claims. Revelation principle: make the model report its own uncertainty — that report IS the bid.
4. **Pareto frontiers** — S×V=C IS the Pareto frontier of the specificity-verifiability trade-off space. All points off the frontier are strictly dominated. The production possibility frontier framework predicts the shape of the curve and what happens when the pipeline budget changes.
5. **Market for lemons (Akerlof)** — LLM confabulation IS an adverse selection problem. Without gap detection, the analysis market collapses to the lowest common denominator: confident-sounding outputs that the user cannot distinguish from accurate ones. Gap detection is certification.
6. **Contract theory / principal-agent** — the user (principal) cannot observe the model's knowledge state (agent). Gap detection is a monitoring mechanism. Holmstrom's informativeness principle predicts exactly which output signals are worth including in the monitoring contract.

**The critical synthesis:** These six frameworks are not independent. They are six descriptions of the same underlying structure — a constrained resource allocation problem under information asymmetry, where the constraint surface (S×V=C) is the Pareto frontier, the pipeline stages are screening mechanisms that solve an adverse selection problem, the budget allocation is a mechanism design problem solved by virtual valuations, and the entire system is a principal-agent contract for eliciting the model's true epistemic state.

---

## 1. Constrained Optimization Under Conservation Laws: Lagrangian Theory

### 1.1 The Core Framework

The Specificity × Verifiability = C conservation law is a **hyperbolic constraint surface** in 2D analytical space. The standard constrained optimization problem is:

```
Maximize:   U(S, V)         [utility of the analysis]
Subject to: S × V = C       [conservation constraint]
            S, V > 0        [positivity]
```

The Lagrangian is:

```
L(S, V, λ) = U(S, V) - λ(S·V - C)
```

**First-order conditions (Lagrange multiplier method):**
```
∂L/∂S = ∂U/∂S - λV = 0   →   ∂U/∂S = λV
∂L/∂V = ∂U/∂V - λS = 0   →   ∂U/∂V = λS
∂L/∂λ = S·V - C = 0       →   S·V = C
```

**The critical geometric insight** (confirmed by LibreTexts mathematics, 2024): at the optimum, the level curves of the utility function are **tangent to the constraint surface**. No movement along the constraint can improve utility. This is not a trivial statement: it means the optimal operating point is uniquely determined by the ratio of marginal utilities — not by the total budget alone.

### 1.2 Shadow Price Interpretation

The Lagrange multiplier λ is the **shadow price of the constraint** — the marginal utility gained per unit relaxation of S×V=C. Economically: λ is what you would pay to move the constraint (to increase C by one unit). If C could be increased — for instance by switching from Haiku to Sonnet — the value of that switch is exactly λ × ΔC.

**Application to our pipeline:** This is precisely the economic justification for the model routing hierarchy. The shadow price λ quantifies how much depth increases when you move from Haiku (lower C) to Sonnet (higher C). Our empirical finding — Haiku + L12 prism achieves 9.8 depth vs. Opus vanilla 7.3 — means the *prism* increases C more than the model does. The prism shifts the constraint surface outward; the model determines where on the constraint you operate.

**Formal prediction:** At the optimum, the ratio of marginal utilities equals the ratio of the constraint's marginal costs:
```
(∂U/∂S) / (∂U/∂V) = V/S
```
If specificity is twice as valuable as verifiability at the margin (∂U/∂S = 2·∂U/∂V), the optimal point has V = 2S — you trade toward specificity until the marginal rates equalize. For code analysis (where precision matters more than coverage), the optimum is high-S/low-V. For risk assessment (where reliability matters more), the optimum is low-S/high-V.

### 1.3 KKT Conditions and Inequality Constraints

The real pipeline has inequality constraints: model API limits, time budgets, minimum reliability thresholds. The **Karush-Kuhn-Tucker (KKT) conditions** extend Lagrangian optimization to this case:

```
KKT conditions for: Maximize U(S,V) s.t. S·V ≥ C_min, S ≥ S_floor, V ≥ V_floor

1. Stationarity:    ∇U = λ·∇(S·V) + μ_S·∇S + μ_V·∇V
2. Primal feasibility: S·V ≥ C_min, S ≥ S_floor, V ≥ V_floor
3. Dual feasibility:   λ, μ_S, μ_V ≥ 0
4. Complementary slackness: λ(S·V - C_min) = 0, μ_S(S - S_floor) = 0, μ_V(V - V_floor) = 0
```

**Complementary slackness** means: if the constraint is not binding (S·V > C_min), its shadow price is zero — we do not pay for slack. This explains why adding a second adversarial pass to an already-complete analysis has near-zero value: the constraint was already satisfied, and the extra call buys nothing on the binding margin.

**Active constraint prediction:** The conservation law S×V=C is always active (binding) for optimal analysis — you are always on the frontier, never inside it. Any analysis inside the frontier is strictly dominated by an analysis on it. This is the formal justification for: "if you could increase depth without sacrificing reliability, you would have already done so."

### 1.4 The Isoquant Geometry

The S×V=C hyperbola is an **isoquant** — a curve along which analytical "output" (conservation constant C) is held fixed. Moving along the isoquant trades specificity for verifiability without changing total analytical value. The **slope of the isoquant at any point is -V/S** (the marginal rate of transformation between specificity and verifiability).

The pipeline stages — L12 (high specificity), SDL (high verifiability), adversarial pass (forces verifiability up) — are movements *along the isoquant* that adjust the S/V ratio, plus movements *between isoquants* that increase C itself (by adding genuinely new information). The adversarial pass moves you toward higher-V/lower-S; the synthesis pass moves the isoquant outward (increases C).

---

## 2. Information Economics: Value of Information, EVPI, EVSI, Blackwell's Theorem

### 2.1 The Core Framework

The decision to run an additional pipeline stage is an **information purchase decision**. The standard value-of-information framework (established in NBER working paper literature, 2010) provides the criterion:

**Expected Value of Perfect Information (EVPI):**
```
EVPI = E[payoff with perfect information] - E[payoff without information]
```
EVPI is the theoretical maximum any information source could be worth. It is a ceiling, not a target.

**Expected Value of Sample Information (EVSI):**
```
EVSI = E[payoff with imperfect signal] - E[payoff without signal]
```
EVSI is what a specific pipeline stage — with its particular accuracy and recall — is actually worth.

**The purchase criterion:** Run stage i if and only if:
```
EVSI(stage_i) > Cost(stage_i)
```

**Application to our pipeline:**
- Stage 1 (L12 single scan, ~$0.05): EVSI is the value of having a conservation law + bug table vs. no analysis. For production code going into a release, EVSI >> $0.05 trivially.
- Stage 2 (adversarial pass, ~$0.05): EVSI is the value of catching the 20-30% of L12 claims that are overclaims. EVSI depends on the stakes: high-stakes code (auth middleware, financial logic) → EVSI >> $0.05. Low-stakes code (internal tooling, scripts) → EVSI ≈ $0.05, marginal.
- Stage 3 (synthesis, ~$0.05): EVSI is the value of the corrected synthesis vs. the pair of conflicting L12 + adversarial outputs. Only positive when conflict is genuine (cross-pipeline divergence), not when both stages agree.
- Stage 4+ (additional prisms): Each additional prism finds different things (zero overlap, empirically confirmed). EVSI is the value of the unique findings. If those findings don't change any decision, EVSI = 0.

**Critical implication:** The pipeline stages are not all equally valuable. EVSI is **target-conditional**: the same stage has different EVSI for auth middleware vs. internal tooling. This formalizes our empirical finding that Full Prism adds more value on complex code than focused code.

### 2.2 Blackwell's Theorem on Information Ordering

**Blackwell's theorem** (David Blackwell, 1953) establishes a partial order on information sources: source A is "more informative than" (Blackwell-dominates) source B if A can replicate any decision that B could make, but not vice versa. Formally: A Blackwell-dominates B if there exists a stochastic matrix T such that B's signal can be generated from A's signal via T — A can always be "garbled" to replicate B.

**Key implication:** If A Blackwell-dominates B, A has higher EVSI for *every possible decision problem* — not just some. A is universally better. This is the strongest possible information ordering.

**Application to our pipeline stages:**

The pipeline stages are partially ordered by Blackwell dominance:
- L12 (332w, conservation law + bug table) Blackwell-dominates vanilla output because every finding in vanilla output is recoverable from L12 output, but not vice versa (L12 finds conservation laws and meta-laws that vanilla cannot).
- The Full Prism (9-call pipeline) Blackwell-dominates Single Prism for the same reason.
- SDL (3-step, single-shot) and L12 are NOT Blackwell-ordered — they find different things. SDL is not a garbled version of L12; they are genuinely orthogonal. This predicts (correctly) that running both in parallel increases EVSI additively, not redundantly.

**The non-ordering of prisms is the key finding:** The five portfolio prisms (pedagogy, claim, scarcity, rejected_paths, degradation) are pairwise non-Blackwell-ordered. Each finds things the others cannot. This is not an accident — it is the information-theoretic signature of genuine orthogonality. Prisms that ARE Blackwell-ordered collapse into each other (confirmed: l12_general is dominated by l12 on all tasks → deleted).

### 2.3 Information Sufficiency and Minimal Sufficient Statistics

The concept of **sufficient statistics** — a statistic that captures all decision-relevant information from a larger dataset — applies to prism outputs. A prism output is "sufficient" for a decision if no additional raw analysis would change the decision.

**Application:** The conservation law in L12 output is a sufficient statistic for the structural analysis decision: "does this code have a fundamental architectural conflict?" Once the conservation law is identified (e.g., "Thread Safety × Throughput = C"), running the code through a second unrelated prism will not overturn the conservation law (it is a structural invariant). The additional prism may find different things, but cannot render the conservation law false.

This predicts (correctly) that the adversarial pass does not overturn L12's conservation laws — it challenges the *application* and *claims* but not the *structural invariant*. The adversarial pass is not a sufficient statistic-based reduction; it is a claim-level challenge.

---

## 3. Mechanism Design and Auction Theory for Analytical Attention

### 3.1 The Core Problem

The pipeline allocates a scarce resource — **verification budget** — across competing claims. Each claim (bug, structural finding, conservation law) is a potential recipient of verification attention. The problem:

```
Allocate K verification slots to N competing claims
where each claim i has:
  - value v_i = impact × risk (PRIVATE, unknown to the allocator)
  - cost c_i = cost to verify (PUBLIC, estimable from type)

Goal: maximize total verified value subject to budget constraint Σ c_i ≤ B
```

This is exactly the mechanism design problem: how do you allocate resources optimally when valuations are private information?

### 3.2 The Vickrey-Clarke-Groves (VCG) Mechanism

The **VCG mechanism** is the standard solution to the private-valuation allocation problem (Vickrey 1961, Clarke 1971, Groves 1973):

**Structure:**
1. Each agent reports their valuation v̂_i (which may differ from true v_i)
2. The mechanism allocates to maximize reported welfare: Σ v̂_i × x_i
3. Each winner i pays: the externality they impose on others (what others would have received if i had not been present)

**Truth-telling dominance:** Under VCG, reporting true valuation v̂_i = v_i is a **dominant strategy** — it maximizes each agent's utility regardless of what others report. This is the revelation principle in action.

**Application to claim verification:** The pipeline can implement a VCG-like mechanism by:
1. Having the model self-report uncertainty/impact for each claim (this IS the model's bid v̂_i)
2. Ranking claims by reported impact × estimated verification cost (the VCG allocation rule)
3. Verifying in decreasing priority until budget is exhausted
4. The model's truthful reporting is incentivized because: if the model inflates a claim's importance, it gets verified and exposed as confabulation — worse outcome than truthful reporting

**Critical insight:** The model's self-reported confidence IS its bid in this auction. A model that says "I'm uncertain about this" is bidding low; a model that says "definitively" is bidding high. Gap detection (finding where the model's confidence exceeds its actual knowledge) is equivalent to detecting bid inflation — exactly what auction fraud prevention does.

### 3.3 Myerson's Optimal Auction and Virtual Valuations

**Myerson's framework** (1981) extends VCG to revenue-optimal settings. The key concept is **virtual valuation**:

```
ψ(v_i) = v_i - (1 - F(v_i)) / f(v_i)
```

where F and f are the CDF and PDF of the valuation distribution. Myerson's result: the optimal mechanism allocates to the agent with the highest *virtual* valuation (not highest true valuation), and items are not allocated when all virtual valuations are negative.

**Economic meaning:** Virtual valuation discounts high true valuations to account for the information rents agents extract by pretending to have lower valuations. The discount is larger when high valuations are rare (fat upper tail → small f(v_i) → large discount).

**Application to verification budget:**
- Claims with high impact × high uncertainty → high virtual valuation → allocate verification budget
- Claims with high impact × low uncertainty (model is confident AND correct) → negative virtual valuation → do NOT verify; trust the model
- Claims with low impact × high uncertainty → low virtual valuation → skip; not worth verifying even if uncertain

**The "reserve price":** Myerson's mechanism has an implicit reserve price — below a threshold virtual valuation, no resources are allocated. In our pipeline, this corresponds to: don't verify claims below an impact threshold, even if the model flagged them as uncertain. This is the formal basis for the bug-table triage: structural vs. fixable classification IS the reserve price — structural bugs have higher virtual valuations.

### 3.4 The Revelation Principle

The **revelation principle** (Myerson 1979) states: any allocation achievable by a complex mechanism (where agents behave strategically) can also be achieved by a **direct revelation mechanism** where agents truthfully report their private information.

**Implication for our pipeline:** We do not need a complex multi-round interrogation protocol to elicit the model's epistemic state. We need only a mechanism where truthful uncertainty reporting is incentivized. The L12 prism IS this mechanism — it forces the model to produce verifiable structural claims (conservation laws, impossibility theorems) that can only be produced if the model has genuine understanding, not just surface-level confidence.

**Mechanism as prism:** The prism is the direct revelation mechanism. By structuring the output format to require formal structural claims, the prism makes confabulation detectable. The model "reveals" its true knowledge state through the structure of its output, not through explicit confidence scores.

---

## 4. Pareto Frontiers in Multi-Objective Optimization

### 4.1 S×V=C IS the Pareto Frontier

**Pareto efficiency** (derived from Vilfredo Pareto): an allocation is Pareto optimal if no objective can be improved without worsening another. The set of all Pareto-optimal points is the **Pareto frontier**.

For our two-objective problem (maximize S and maximize V simultaneously):
- Every point ON the curve S×V=C is Pareto optimal — to increase S, you must decrease V.
- Every point INSIDE the curve (S×V < C) is Pareto dominated — you can increase both S and V simultaneously by moving to the frontier.
- Every point OUTSIDE the curve (S×V > C) is infeasible.

**The conservation law IS the Pareto frontier.** This is not an analogy — it is the mathematical identity. The Pareto frontier of the Specificity-Verifiability trade-off is exactly the set of points satisfying S×V=C.

### 4.2 The Shape of the Frontier and Its Predictions

The hyperbolic shape of S×V=C (rectangular hyperbola) has specific economic predictions:

**Elasticity of substitution:** For a rectangular hyperbola, the elasticity of substitution between S and V is exactly 1. This means: if you increase specificity by 10%, you lose exactly 10% of verifiability, regardless of where on the curve you are. The trade-off rate is constant in percentage terms. This is the Cobb-Douglas production function with equal exponents — the "neutral" case.

**Implications:**
- No diminishing returns in percentage terms: doubling specificity halves verifiability, always
- No "sweet spot" by default: the frontier is symmetric — there is no geometrically privileged point
- The optimal point depends ONLY on relative marginal utilities: if you value specificity twice as much as verifiability (|∂U/∂S| = 2|∂U/∂V|), you operate at V = 2S

**When the frontier shifts outward (increasing C):**
The prism increases C — it moves the entire frontier outward. Our empirical finding that Haiku + L12 (C_prism) >> Opus vanilla (C_vanilla) means the prism strictly expands the feasible frontier. You can achieve the same specificity with higher verifiability, or the same verifiability with higher specificity, or more of both.

**Production Possibility Frontier interpretation:** The pipeline budget determines which isocurve (which value of C) you can reach. More budget → higher C → frontier shifted outward. The production possibility frontier for the pipeline is the set of achievable (S, V) pairs given a fixed budget B:

```
PPF: {(S, V) : S·V ≤ C(B), S, V ≥ 0}
```

where C(B) is an increasing function of budget B. The shape of C(B) determines the returns to scale of the pipeline.

### 4.3 Multi-Objective Pareto Optimality for Pipeline Design

The full pipeline has more than two objectives: Specificity, Verifiability, Cost, Latency, Coverage. The multi-objective Pareto frontier is a **Pareto manifold** in 5D space.

**Key prediction:** Each additional pipeline objective narrows the Pareto frontier (more constraints = smaller feasible set). The 9-call Full Prism is further from the single-objective optimum for cost, but may be on the Pareto frontier of the (Specificity, Verifiability, Coverage) triple trade-off.

**Pareto improvement vs. Pareto trade-off:**
- Adding the adversarial pass is a Pareto improvement on (Verifiability, Coverage) at the cost of (Cost, Latency)
- The net assessment requires weighting the objectives — which is the utility function U(S, V, Cost, Latency, Coverage)

**Scalarization:** When a single utility function is specified (e.g., "maximize depth subject to budget ≤ $0.20"), the multi-objective problem collapses back to a scalar constrained optimization, and the Lagrangian approach in Section 1 applies directly.

---

## 5. Market for Lemons: Adverse Selection and AI Confabulation

### 5.1 Akerlof's Model Applied to LLM Outputs

George Akerlof's 1970 paper "The Market for Lemons" (Nobel 2001) establishes the structure of adverse selection from information asymmetry. The core mechanism (from Corporate Finance Institute, 2024):

**The lemons dynamic:**
> "When buyers cannot distinguish quality differences, they assume average quality and offer average prices. This pricing mechanism forces higher-quality sellers to exit the market — leaving only lower-quality products ('lemons'). The market progressively deteriorates until only the worst products remain."

**Applied to LLM analysis without gap detection:**
- The "market" is the space of analytical claims the model makes
- The "seller" is the model; the "buyer" is the user
- The model has private information about claim quality (whether it is confabulating or genuinely knows)
- The user cannot distinguish high-quality claims (true structural insights) from low-quality claims (confident-sounding confabulations)
- The model's incentive: all claims look equally confident regardless of underlying quality
- The user's response: discount all claims to average quality, treating both structural insights and confabulations as equally uncertain
- Result: the analysis "market" collapses — high-quality analytical claims are treated the same as confabulations, so the discriminative value of the analysis is destroyed

**The lemons collapse in concrete terms:** When a user cannot distinguish L12's conservation law from a hallucinated structural claim, they assign average credibility to both. This means the conservation law is undervalued (treated as possibly hallucinated) and the confabulation is overvalued (treated as possibly correct). Both the genuine insight and the hallucination are "priced" at the same average quality. This is the lemons market equilibrium for AI analysis.

### 5.2 Gap Detection as Certification

Akerlof identified three classes of lemons-market solutions (Corporate Finance Institute, 2024):

1. **Signaling:** High-quality producers voluntarily disclose information (warranties, certifications) to distinguish themselves.
2. **Screening:** The uninformed party designs mechanisms requiring self-selection that reveal the other party's true type.
3. **Certification:** Third-party verification establishes credible quality standards.

**Gap detection maps directly onto certification:**
- The gap detection pipeline is a third-party verifier (second model pass checks first model pass's claims)
- Claims that survive adversarial challenge are "certified" — their quality is now observable by the user
- The adversarial model's role is precisely the role of a certification body: it cannot be gamed by the original model, because it is independent and adversarially motivated

**The warranty interpretation:** L12's conservation law is a "warranty" — a structural claim that is self-falsifying if wrong. "The conservation law is Thread Safety × Throughput = C" can be disproven by a counterexample. A warranty is credible precisely because it creates liability for the warrantor. The structural form of L12 outputs is a warranty mechanism.

**Prediction:** The lemons model predicts that without gap detection, the equilibrium quality of AI analysis will deteriorate over time as users lose the ability to distinguish genuine insights from confabulations. With gap detection, the market separates — high-quality claims survive adversarial challenge and command higher "prices" (higher user trust). This is why the adversarial pass improves user confidence even when it does not change the final claims — it is the certification mechanism, not just a refinement tool.

### 5.3 Signaling and the Structural Output Format

**Spence's signaling model** (Michael Spence, Nobel 2001, co-awarded with Akerlof): signals are credible if they are costly for low-quality types to mimic. Job candidates signal quality via education degrees, which are costly to obtain but cost-differentially more for low-ability candidates.

**Applied to prism outputs:** The conservation law + impossibility theorem format is a credibility signal. A model confabulating cannot consistently produce:
1. A conservation law that correctly identifies the structural invariant
2. A meta-law that explains WHY the conservation law must hold
3. Specific bug locations that instantiate the structural claim

These three together are too costly to fake coherently. Each adds specificity that can be independently checked. The multi-level structure of L12 output is a **signaling device** that distinguishes genuine structural understanding from surface-level pattern matching.

**Cost-of-mimicry argument:** A model confabulating would need to:
1. Invent a plausible-sounding conservation law (easy)
2. Invent supporting evidence that is internally consistent with the law (hard)
3. Produce bug locations that exactly instantiate the law's predictions (very hard — requires genuine code understanding)

Step 3 creates the cost differential. This is why our code prisms find real bugs at much higher rates than vanilla output: the structural format forces consistency between abstract claims and concrete code locations, which confabulation cannot maintain.

---

## 6. Contract Theory: Principal-Agent Framework for AI Analysis

### 6.1 The Principal-Agent Problem

**Standard formulation** (from Corporate Finance Institute, 2024): The principal-agent problem occurs when:
> "A principal-agent problem occurs when a conflict of interest emerges between a principal (who delegates work) and an agent (who performs it). The fundamental challenge stems from information asymmetry — the principal cannot easily observe the agent's true knowledge, effort, or actions."

**Core issues:**
- **Moral hazard:** Once engaged, the agent may under-perform since the principal cannot observe effort
- **Hidden information:** The agent has private knowledge about their capabilities that they may not disclose
- **Hidden action:** The principal cannot monitor whether the agent is actually reasoning or pattern-matching

**Applied to LLM analysis:**
- **Principal:** User (wants accurate structural analysis)
- **Agent:** LLM (has private information about its own knowledge state — whether it "knows" the code or is interpolating)
- **Hidden information:** The model knows which claims are high-confidence genuine insights vs. low-confidence interpolations — the user does not
- **Hidden action:** The user cannot observe whether the model performed genuine structural analysis vs. plausible-sounding pattern matching
- **Moral hazard:** The model has no penalty for confabulation (no feedback loop from wrong outputs) — it will produce confident-sounding outputs regardless of actual quality

### 6.2 Holmstrom's Informativeness Principle

**Holmstrom's informativeness principle** (Bengt Holmstrom, Nobel 2016): A signal should be included in the agent's compensation contract if and only if it provides additional information about the agent's effort, conditional on signals already included. Formally: include signal y in the contract if and only if y is informative about effort given the existing contract signals.

**Application to monitoring design:** The user's "contract" with the LLM is the prism prompt + output format. The output format specifies which signals the user observes:

**Vanilla output:** User observes only final claims. No information about the model's reasoning process, confidence levels, or internal state. By Holmstrom's principle, this is a **non-informative contract** — the user cannot distinguish effort (genuine analysis) from shirking (confabulation).

**L12 output:** User observes conservation law + impossibility theorem + bug table. These are **informative signals** about the model's understanding:
- Conservation law → only producible with genuine structural understanding (high effort signal)
- Impossibility theorem → verifiable structural claim, falsifiable, effort-correlated
- Bug table with structural vs. fixable classification → requires code-level understanding, not pattern matching

**Meta-law:** User observes the model's analysis of its own analysis. This is the highest-effort signal: genuine meta-analytical reasoning that confabulation cannot sustain.

**Holmstrom's prediction:** The L12 format should be included in the monitoring contract because each output type provides additional information about genuine reasoning effort, conditional on the others. This is exactly what we observe: conservation law + bug table are complementary (not redundant) signals.

### 6.3 Screening Mechanisms and Self-Selection

**Screening** (the uninformed party designs mechanisms that induce the agent to self-select truthfully):

The prism prompt IS a screening mechanism. By requiring formal structural claims, it screens for models that can produce genuine structural analysis — models that are "confabulating" will produce formally deficient outputs (missing conservation laws, internally inconsistent bug locations, non-falsifiable claims).

**The screening menu:**
- Format A (vanilla): Accepts all model types (genuine + confabulating). Cannot distinguish.
- Format B (L12): Only models with genuine structural understanding can produce satisfactory outputs. Confabulating models produce outputs that fail the structural consistency check.

The prism screens the model by format requirements. The adversarial pass screens the first-pass output by adversarial challenge. The synthesis pass screens by requiring integration of contradictory claims. This three-stage screening menu is the principal's solution to the hidden-information problem.

### 6.4 Monitoring Costs and the Optimal Contract

**The monitoring cost trade-off:** Adding pipeline stages increases monitoring quality but costs money. The optimal contract minimizes monitoring costs while achieving target information quality. This is the formal setup for the pipeline budget allocation problem.

**Optimal monitoring intensity formula:**
```
Optimal monitoring ∝ (Agency cost of under-monitoring) / (Marginal cost of monitoring)
```

**Agency cost = cost of wrong decision × probability of wrong decision without monitoring**

For high-stakes code (auth middleware, financial logic):
- Cost of wrong decision = very high (security breach, financial loss)
- P(wrong without monitoring) = 42% (L12 accuracy on real production code, empirically measured)
- Agency cost = high × 42% = substantial

For low-stakes code (internal tooling):
- Cost of wrong decision = low (wasted refactoring effort)
- Agency cost = low × 42% = negligible

**Prediction:** The optimal pipeline length is longer for auth middleware than for internal tooling. This matches our empirical calibration: default = L12 single scan; high-stakes = Full Prism. The calibrate mechanism formalizes this judgment.

**The residual monitoring problem:** Even the Full Prism (9-call pipeline) does not eliminate the principal-agent gap — it reduces it. The L12 accuracy on real code is 42% for bugs, and 93% for structural insights. This asymmetry is predicted by contract theory: it is easier to verify effort on task dimensions that have verifiable outputs (structural claims → can be proved/disproved) than on task dimensions with unverifiable outputs (bug location accuracy → requires running the code).

---

## 7. Synthesis: The Unified Economic Model

### 7.1 The Six Frameworks Are One Framework

The six economic frameworks in this document are descriptions of the same underlying structure:

| Framework | What it names | Core result |
|-----------|--------------|-------------|
| Lagrangian | The constraint surface | Optimal point determined by shadow price of trade-off |
| Value of information | The decision to run each stage | Run stage iff EVSI > cost |
| Mechanism design | The allocation of verification budget | VCG/Myerson: allocate to highest virtual valuation |
| Pareto frontier | The shape of the constraint surface | S×V=C IS the Pareto frontier |
| Market for lemons | The adverse selection problem | Gap detection is certification, not enhancement |
| Contract theory | The principal-agent structure | Prism format = monitoring contract |

**The unified model:**
1. The user (principal) faces an adverse selection problem: model outputs may be lemons (confabulations) that she cannot distinguish from genuine insights.
2. The prism format is a screening/monitoring contract that elicits truthful structural outputs from the model (agent).
3. The pipeline stages are sequential certification rounds that progressively raise the quality bar.
4. The allocation of budget across stages is a mechanism design problem solved by virtual valuations (impact × risk).
5. The optimal operating point on the S×V=C frontier is determined by the shadow price (Lagrange multiplier) of the trade-off.
6. The value of running each stage is its EVSI, which is target-conditional and can be calculated before committing the budget.

### 7.2 Novel Predictions from the Economic Framework

These are predictions that follow from the economic theory but are not yet empirically tested:

**Prediction 1: Optimal model selection is target-conditional (Myerson)**
Virtual valuations depend on the distribution of claim types in the target code. Auth middleware has a different distribution (security claims are high-impact → high virtual valuation → more verification) than utility code. The optimal model for auth middleware is not the optimal model for utility code. Current routing uses fixed rules (always Sonnet for L12); Myerson's framework predicts target-adaptive routing would improve efficiency.

**Prediction 2: The adversarial pass adds zero EVSI for internally consistent L12 outputs (Blackwell)**
If L12 output passes a structural consistency check (conservation law is internally consistent with bug table), the adversarial pass is Blackwell-dominated — it cannot add information. EVSI ≈ 0. Budget should skip to synthesis directly.

**Prediction 3: Self-reported confidence is a valid VCG bid (Revelation Principle)**
If the model is prompted to self-report claim confidence alongside the claim, and the pipeline verifies proportionally to reported confidence, the model has dominant strategy incentive to report truthfully (because inflating confidence leads to adversarial scrutiny → exposure → worse outcome). This predicts that "rate your confidence in each claim" added to L12 would improve bug-finding accuracy without increasing total pipeline cost.

**Prediction 4: The lemons equilibrium predicts a quality floor without gap detection (Akerlof)**
In domains where users routinely accept LLM outputs without verification, we predict a quality floor: models will optimize for plausibility rather than accuracy, because the feedback signal distinguishes only the former. Gap detection reverses this incentive: models that produce more verifiable outputs receive better ratings, creating a selection pressure toward higher-quality structural analysis.

**Prediction 5: The shadow price of the conservation constraint is model-class-specific (Lagrange)**
The shadow price λ (how much you gain by moving to a higher C isocurve) is different for Haiku vs. Sonnet vs. Opus. Specifically: λ_haiku > λ_sonnet > λ_opus because Haiku operates further from the frontier and gains more from each unit of constraint relaxation. This predicts that the marginal value of a prism is highest for the weakest model — which exactly matches our empirical result: Haiku + L12 gains more vs. Haiku vanilla than Sonnet + L12 gains vs. Sonnet vanilla.

### 7.3 The Conservation Law of the Economic Framework Itself

Applying the same analytical framework to itself (L13 reflexivity):

**The economic framework's conservation law:** `Precision × Generality = Constant`

- High-precision mechanisms (VCG, Myerson optimal auction) require strong assumptions (independent private values, regular distributions, quasilinear preferences) — they are not general.
- High-generality frameworks (Blackwell ordering) give weaker predictions (ordinal only, no optimal mechanism) — they are not precise.
- The Lagrangian framework has medium precision and medium generality — the mid-point on the economic-framework's own Pareto frontier.

**The meta-law:** Each economic framework in this document sacrifices generality for precision in the same way that each prism sacrifices verifiability for specificity. The parallel is not accidental — both are instances of the same information-theoretic constraint: you cannot simultaneously maximize precision and maximize domain coverage of any analytical framework.

**What this framework conceals:** All six economic frameworks assume the principal knows the distribution of agent types (F(v) in Myerson's framework, the lemons/non-lemons ratio in Akerlof). For LLMs, this distribution is unknown, non-stationary, and model-version-dependent. The frameworks provide the skeleton; the empirical project provides the distributional estimates that make the skeleton operational.

---

## References

### Foundational Theory
- **Akerlof, G.A.** (1970). "The Market for Lemons: Quality Uncertainty and the Market Mechanism." *Quarterly Journal of Economics.* [Nobel Prize 2001]
- **Myerson, R.** (1981). "Optimal Auction Design." *Mathematics of Operations Research.* [Nobel Prize 2007]
- **Vickrey, W.** (1961). "Counterspeculation, Auctions, and Competitive Sealed Tenders." *Journal of Finance.* [Nobel Prize 1996]
- **Holmstrom, B.** (1979). "Moral Hazard and Observability." *Bell Journal of Economics.* [Nobel Prize 2016]
- **Blackwell, D.** (1953). "Equivalent Comparisons of Experiments." *Annals of Mathematical Statistics.*
- **Hurwicz, L., Maskin, E., Myerson, R.** (2007). Nobel Prize in Economics for mechanism design theory.
- **Spence, M.** (1973). "Job Market Signaling." *Quarterly Journal of Economics.* [Nobel Prize 2001]
- **Lagrange, J.L.** (1788). *Mécanique analytique.* [Lagrange multiplier method]
- **Karush, W.** (1939); **Kuhn, H.W. & Tucker, A.W.** (1951). KKT conditions for constrained optimization.

### Information Value Framework
- NBER Working Paper on Value of Information (accessed 2026): EVPI = payoff with perfect information − payoff without information. EVSI = payoff with imperfect signal − payoff without signal. "Information justifies its cost when the expected value gain exceeds the information acquisition cost."
- Corporate Finance Institute (2024). "Adverse Selection." Accessed March 2026: "When buyers cannot distinguish quality differences, they assume average quality and offer average prices. This pricing mechanism forces higher-quality sellers to exit the market."
- Corporate Finance Institute (2024). "Principal-Agent Problem." Accessed March 2026: "A principal-agent problem occurs when... the principal cannot easily observe the agent's true knowledge, effort, or actions."

### Applied and Computational
- **Roughgarden, T.** (2013). CS364A: Algorithmic Game Theory, Stanford University. Lectures on mechanism design, VCG, and optimal auctions. [timroughgarden.org/f13]
- LibreTexts Mathematics (2024). "Lagrange Multipliers." OpenStax Calculus: "At the optimal point on a constraint curve, the level curves of the objective function become tangent to the constraint."

### Connection to This Project's Empirical Findings
- Round 28-40 experiment logs: 1000+ experiments across Haiku/Sonnet/Opus confirming S×V=C conservation law, prism-induced C-expansion, and pipeline EVSI ordering.
- `experiment_log.md` Round 29: Full Prism (30 bugs, Starlette) > Single Prism (16 bugs) — empirical EVSI calculation.
- `CLAUDE.md` Principle 13: "The cheapest model with the right prism beats the most expensive model without one" — empirical confirmation of shadow-price dominance of prism over model class.
