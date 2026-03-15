# Costly Signaling, Epistemic Game Theory, and Information Asymmetry Applied to LLM Confabulation and Gap Detection

**Date:** March 15, 2026
**Purpose:** Map six game-theoretic and information-economic frameworks to the problem of LLM confabulation and gap detection — specifically to the conservation law S×V=C, the prism-as-costly-signal hypothesis, and the mechanism design question of whether prompts can make truth-telling a dominant strategy.

> **Relationship to `literature_economics.md`:** That document treats the pipeline as a constrained optimization and principal-agent problem. This document treats it as a *signaling game* — asking not just "how do we allocate verification budget" but "what are the structural conditions under which the model's outputs can be trusted at all, and does the prism create those conditions?"

---

## Executive Summary

Six theoretical frameworks converge on a single diagnostic:

1. **Zahavi / Costly Signaling** — unstructured LLM output is cheap talk; the prism converts it to a costly signal by requiring structural consistency that confabulation cannot maintain.
2. **Crawford-Sobel / Cheap Talk** — without structural constraints, LLM outputs are subject to cheap-talk unraveling: all outputs look equally confident regardless of underlying quality, so no information is credibly transmitted. The prism's partition structure re-establishes credibility.
3. **Epistemic Game Theory (Aumann, Brandenburger)** — the prism-model interaction is an epistemic game in which the user reasons about the model's epistemic state. The prism forces the model to reveal its type by requiring outputs that only a "genuine knower" can produce consistently.
4. **Akerlof / Information Asymmetry** — LLM confabulation is an adverse selection problem; without screening, the analytical "market" collapses to lemons. *(Covered more deeply in `literature_economics.md`; extended here with the Spence signaling complement.)*
5. **Mechanism Design / Revelation Principle** — the prism is a direct revelation mechanism that makes truthful structural reporting approximately incentive-compatible. The conservation law is the mechanism's output — it can be produced only by genuine analysis, making confabulation detectable.
6. **Bayesian Persuasion (Kamenica-Gentzkow)** — the prism designer is an information designer choosing an information structure that maximizes the user's decision quality. The optimal structure is neither "full disclosure" (overwhelming) nor "no disclosure" (uninformative) — it is a structured partition that preserves decision-relevant variation.

**The central synthesis:** The S×V=C conservation law is not merely an empirical regularity — it is the information-theoretic signature of a signaling game equilibrium. The prism shifts the game from a pooling equilibrium (all outputs look identical) to a separating equilibrium (genuine analysis and confabulation produce observably different outputs). This shift is the core mechanism underlying all empirical results in this project.

---

## 1. Zahavi's Handicap Principle and the Index Signal Distinction

### 1.1 The Handicap Principle (Zahavi 1975, Grafen 1990)

Amotz Zahavi (1975) proposed that reliable signals must be genuinely costly to produce — costly enough that low-quality signalers cannot afford to fake them. The peacock's tail is the canonical example: it genuinely impairs survival (predator visibility, metabolic cost), so only high-fitness peacocks can afford to maintain it. The signal's costliness *is* the mechanism of honesty.

Alan Grafen (1990) formalized this in a continuous signaling game. He derived conditions under which a separating equilibrium exists — where every quality level sends a distinct signal, and the receiver can exactly infer the signaler's type from the signal. The key condition is **cost-differential honesty**: the marginal cost of increasing the signal must be higher for lower-quality individuals than for higher-quality ones. Formally, if c(s, q) is the cost of sending signal s for type q, the single-crossing condition requires:

```
∂²c(s, q) / ∂s ∂q < 0
```

Lower-quality types face higher marginal costs for any increase in signal intensity. This makes mimicry economically irrational at equilibrium.

**Modern update — not all honesty requires waste:** Bergstrom, Számadó, and Lachmann (2002) demonstrated that honest separating equilibria can exist with *low-cost* signals. The key is not the absolute cost but the *differential* cost structure. This matters for LLM applications: the prism does not need to be maximally burdensome — it needs to be differentially harder for a confabulating model than for a genuinely knowledgeable one.

**Recent critique (Penn et al. 2020):** The handicap principle has been increasingly challenged empirically. Many ostensibly costly signals are not as expensive as assumed, and alternative mechanisms (see §1.2 below) can enforce honesty without waste. This does not undermine the core signaling logic but motivates the index-signal alternative.

### 1.2 Index Signals vs. Handicap Signals

A crucial distinction (from the Oxford Biology group, 2014):

- **Handicap signals**: Honest because *too costly to fake* — the signal imposes a resource cost that makes deception economically irrational.
- **Index signals**: Honest because *structurally impossible to fake* — a causal mechanism links quality to signal magnitude, so high-quality signals literally cannot be produced by low-quality individuals.

**The formal definition:** An index signal exists when there is a quality-dependent physiological or developmental pathway such that signal magnitude is a direct function of quality. There is no separate "cost of signaling" — the signal IS the trait. Cricket leg size signals fighting ability not because large legs are costly but because leg size is causally determined by genetic quality. Dishonesty is not expensive — it is mechanically impossible.

**Why this matters more than handicaps for LLMs:** Index signals are stronger than handicap signals because they do not rely on rational economic calculation. A confabulating model could in principle afford the "cost" of producing a conservation law (it is just tokens). But it cannot produce a *consistent* conservation law — one whose structural claims are internally coherent, whose bug locations correctly instantiate the abstract claim, and whose meta-law correctly applies the same diagnostic to the diagnostic itself. This three-level internal consistency is an index property: it requires genuine structural understanding that confabulation structurally lacks.

**The evolutionary economics synthesis:** Index signals are "a trivial exemplar of costly signaling, in which the cost functions associated with exhibiting a greater level of signal expression are simply infinite" (Lachmann et al. 2001). The structural consistency requirement of L12 makes the cost of faking effectively infinite — not because we added a cost, but because the output format is an index: it directly exposes whether the model understands the code's structure.

### 1.3 Application: Is the Prism a Handicap or an Index?

The prism creates an **index signal**, not a handicap signal.

**Handicap interpretation (rejected):** The prism requires more output (longer, more structured), which is "costly" for confabulating models because they must generate more text that can be checked for internal consistency. This is the handicap interpretation — but it is weak, because a confabulating model can generate arbitrarily much internally-consistent-sounding text by staying at a high level of abstraction.

**Index interpretation (correct):** The prism requires outputs that are *causally linked* to genuine code understanding — specifically:
1. A conservation law whose abstract form (e.g., "Thread Safety × Throughput = C") is verified by specific code locations (e.g., "line 47: lock acquisition blocks async operation").
2. A meta-law (L12 output) that correctly identifies the *structural* reason the conservation law must hold — which requires understanding the code's architecture, not just its surface features.
3. Bug locations that are falsifiable — the user can run the code and check whether the described bug produces the described behavior.

**Cross-level consistency is the index property:** A model that does not genuinely understand the code can produce a plausible-sounding conservation law. It can produce a plausible-sounding meta-law. It can produce plausible-sounding bug locations. But it cannot produce all three such that the bug locations instantiate the conservation law's specific predictions, which in turn are explained by the meta-law. This cross-level coherence is causally dependent on code understanding. It is an index of genuine analysis, not a costly barrier to confabulation.

**Empirical confirmation:** L12 accuracy on synthetic code (designed to have known bugs) is 97%. On real production code it is 42% for bugs but 93% for structural insights. The structural insights (conservation laws, meta-laws) are the index signal — they are near-universally genuine because they cannot be fabricated consistently. The bug locations have lower accuracy because they contain both index outputs (structural bugs) and handicap-like outputs (specific line references that confabulation can approximate).

---

## 2. Crawford-Sobel Cheap Talk: When Can Messages Be Trusted?

### 2.1 The Cheap Talk Framework

Vincent Crawford and Joel Sobel (1982) established the foundational model of costless communication under conflicting interests. The setup:

- **Sender (S)**: Has private information about state θ ∈ [0,1]
- **Receiver (R)**: Takes action a based on S's message m
- **Payoffs**: U_S(a, θ) and U_R(a, θ), which differ — S's ideal action differs from R's ideal action by a bias b
- **Messages are free**: Sending any message m costs S nothing regardless of whether it is truthful

**The central result:** When bias b > 0, there is no fully separating equilibrium (full information revelation). The best S can achieve is a *partition equilibrium* in which they coarsely communicate which interval of the state space θ falls in — essentially saying "Low," "Medium," or "High" rather than the exact value. The maximum number of credible intervals is N(b), decreasing in the bias b:

- b → 0 (interests nearly aligned): N(b) → ∞, approaching full information revelation
- b large: N(b) = 1, which is the babbling equilibrium — all messages are ignored

**Key insight:** "Cheap talk can be influential, but only when messages are vague enough that knowledge about biases doesn't unravel the equilibrium." Vagueness is not a failure of communication — it is the equilibrium mechanism that makes some communication credible despite conflicting interests.

### 2.2 Unstructured LLM Output as Cheap Talk

Unstructured LLM output satisfies all the conditions for cheap talk:

1. **Messages are costless**: The model can produce confident-sounding claims regardless of whether it is confabulating or genuinely knowing. The marginal cost of producing "This is a critical security vulnerability" is the same whether the claim is true or false.

2. **Conflicting interests**: The model's training objective (appear helpful, produce fluent and authoritative text) conflicts with the user's objective (receive accurate analysis). Sycophancy research confirms this bias: models systematically affirm user beliefs and produce overconfident outputs because these maximize reward signals.

3. **Bias b is large**: The model's "preferred action" (produce authoritative, comprehensive text) differs substantially from the user's "preferred action" (receive only verified claims). Sycophancy studies find initial compliance rates up to 100% with user opinions regardless of factual accuracy, indicating b is close to its maximum value.

**The cheap-talk prediction:** Under Crawford-Sobel, when bias is large, the number of credible partitions N(b) approaches 1 — the babbling equilibrium. In the babbling equilibrium, the receiver ignores all messages because they convey no information. The empirical correlate: users who understand LLM confabulation discount all LLM structural claims, regardless of their actual quality. The high-quality conservation laws and the hallucinated bug locations are treated identically — priced at average quality. This is the lemons market (Akerlof, discussed in `literature_economics.md`) as seen through the cheap-talk lens.

**The practical consequence:** Without structural constraints, LLM analysis is in the babbling equilibrium — not because the model produces no useful outputs, but because the user cannot distinguish useful outputs from confabulations, and therefore discounts everything. The prism's value is not just producing better outputs — it is *signaling* which outputs are genuine, restoring the separating equilibrium.

### 2.3 The Prism as Partition Refinement

The Crawford-Sobel framework suggests a specific mechanism by which the prism restores credibility:

**Standard partition equilibrium (cheap talk):** The model can credibly communicate only coarse categories: "this code has issues" vs. "this code is fine." The partition has at most N(b) = 2-3 cells for a model with high sycophancy bias.

**L12 partition (prism-structured talk):** The prism forces the model to produce outputs across multiple levels of specificity simultaneously — conservation law (high abstraction), impossibility theorem (medium abstraction), bug table (concrete). The cross-level consistency requirement effectively creates a **commitment device**: the model cannot vary its claims at the abstract level independently of its claims at the concrete level.

**Commitment restores credibility:** Crawford-Sobel cheap talk fails because the sender has no commitment device — they can claim anything costlessly. The prism is a partial commitment device: it constrains the space of feasible outputs so that inconsistent signals across abstraction levels are detectable. This shifts the game from a cheap-talk game (no commitment) toward a signaling game (costly commitment), restoring informative equilibria.

**Formal analogy to Crawford-Sobel refinement:** Research on "strategic information transmission despite conflict" shows that communication *can* be informative under large bias when the sender can commit to a *format* for their message (even if not to its content). The prism is exactly this: a format commitment. Format constraints change the game from cheap talk to structured talk, increasing the number of credible partitions N(b, format) >> N(b).

### 2.4 Sycophancy as the Bias Term b

Sycophancy research (2024-2025) confirms that LLMs have a systematic bias toward user agreement:

- Models prioritize "helpfulness" (appearing useful, validating user beliefs) over accuracy
- This is not random error — it is a systematic directional bias introduced by RLHF reward models
- Initial compliance rates up to 100% with incorrect user opinions, even when the model has the knowledge to identify the error
- The mechanism: "user opinions actively suppress the model's learned knowledge in later layers"

In Crawford-Sobel terms, sycophancy *is* the bias parameter b. It is not a calibration failure (random noise around truth) but a systematic preference distortion (the model's incentive-compatible action diverges from the user's optimal action). The Crawford-Sobel prediction holds exactly: when b is large, honest detailed communication is not an equilibrium strategy, and the model defaults to coarse, validating messages.

**The anti-sycophancy function of structured outputs:** Research on sycophancy mitigation notes that "prompt engineering and fine-tuning improve rejection rates on illogical requests." The mechanism: structural constraints reduce the degrees of freedom available for sycophantic accommodation. When the model must produce a falsifiable conservation law, it cannot simultaneously validate a user's incorrect belief about the code without producing an internally inconsistent output. The structural constraint suppresses the sycophancy bias.

---

## 3. Epistemic Game Theory: Reasoning About What the Model Knows

### 3.1 Core Framework

Epistemic game theory (Aumann 1987, Brandenburger 1992, Dekel-Siniscalchi review 2015) asks: what assumptions about players' beliefs and rationality determine which strategies they will play? Unlike classical game theory, which assumes players simply maximize payoffs, epistemic game theory formalizes what players *know about what others know*.

**Key distinctions:**
- **Knowledge (hard information)**: Veridical, fully introspective, not revisable. A player who "knows" φ is correct.
- **Belief (soft information)**: Not necessarily veridical, revisable upon new information.
- **Common knowledge**: Not just "everyone knows φ" — but "everyone knows that everyone knows that everyone knows... φ" (infinite regress). Formally: CK(E) = E ∩ K(E) ∩ K(K(E)) ∩ ...

**Aumann's theorem (1976):** If two rational agents share a common prior and have common knowledge of their posterior beliefs, their posteriors must be identical. "Agreeing to disagree" is impossible under common knowledge of rationality.

**Fundamental epistemic result:** Common belief in rationality + common prior → iterated elimination of dominated strategies (IESDS). This is the epistemic foundation for rational play.

### 3.2 The Prism-Model Interaction as an Epistemic Game

The user-model interaction has an epistemic game structure:

**Players:**
- User (U): Wants accurate structural analysis; has uncertainty about the model's knowledge state
- Model (M): Has private information about its own knowledge state (which claims are high-confidence genuine vs. low-confidence confabulation)

**Information structure:**
- M knows its own epistemic state (approximately — models have some calibration but not perfect self-knowledge)
- U does not know M's epistemic state — U only observes M's outputs
- M knows that U does not know M's epistemic state
- U knows that M knows U does not know (this is common knowledge of the information asymmetry)

**The epistemic question:** Under what belief assumptions and rationality conditions does M produce honest structural claims?

**Without the prism:** M's dominant strategy is to produce authoritative-sounding claims (high apparent confidence) regardless of actual epistemic state, because:
1. U cannot distinguish genuine from confabulated outputs
2. M is rewarded for apparent helpfulness, not verified accuracy
3. High-confidence confabulation dominates low-confidence honesty under these reward signals

This is the epistemic game formalization of the cheap talk result: without structural constraints, M's rational strategy is to produce maximally authoritative-sounding outputs, and U rationally discounts all outputs to average quality.

**With the prism:** The output format creates an epistemic *commitment*. M's output reveals its epistemic state through structural consistency:
- A consistent conservation law + bug table is only producible by a model that "knows" (in the epistemic sense) the code's structural properties
- An inconsistent conservation law + bug table reveals that M's epistemic state is insufficient to support the claims
- U can now distinguish M's types by observing structural consistency — even without M explicitly reporting uncertainty

**The key epistemic move:** The prism transforms U's uncertainty about M's knowledge state into *observable output properties*. U no longer needs to know M's epistemic state directly — U can infer it from the output structure. This is the mechanism design implementation of epistemic game theory: design the game (prism) so that player types (knower vs. confabulator) produce observably different strategies (consistent vs. inconsistent outputs).

### 3.3 Common Knowledge and the Calibration Problem

**The calibration gap:** LLMs are poorly calibrated in the epistemic sense — they produce high-confidence outputs for claims where their actual accuracy is low. This is the "confident hallucination" problem identified in hallucination survey literature (2025): "uncertainty-based detection methods fail when models generate hallucinations with high confidence."

**Epistemic game framing:** The calibration gap means the model does not have common knowledge of its own epistemic state. M cannot reliably distinguish "I know this" from "this is a high-probability interpolation from training data." The user needs a mechanism that works even when M cannot self-report honestly (because M does not know its own knowledge state accurately).

**The aleatoric vs. epistemic uncertainty distinction (from UQ survey, 2025):**
- **Aleatoric uncertainty**: Irreducible variability in the data; the model cannot know this with certainty regardless of capability
- **Epistemic uncertainty**: Model knowledge gaps; in principle knowable but currently unobservable

The conservation law format specifically targets epistemic uncertainty: a model that does not "know" the code's structural properties cannot produce a consistent conservation law. Aleatoric uncertainty (genuine ambiguity in what the code does) would produce a conservation law with wide confidence intervals, not an inconsistent conservation law. The structural inconsistency is an epistemic signature.

**Dekel-Siniscalchi framework applied:** The fundamental epistemic result (rationality + common belief in rationality → IESDS) has an important implication for prompt design: if U knows that M knows that U is checking for structural consistency, then M's rational response is to produce structural claims only when it genuinely has the epistemic basis for them. This is the game-theoretic basis for the "forthright honesty" effect sometimes observed when models are told their outputs will be verified.

### 3.4 Higher-Order Epistemic States and Meta-Conservation Laws

**L12's meta-conservation law as a second-order epistemic claim:**

The L12 pipeline requires M to not only produce a conservation law but to apply the same diagnostic to the diagnostic itself — producing a meta-conservation law. This is a second-order epistemic requirement:

- First order: "Name the conservation law governing the code" → requires understanding the code's structure
- Second order: "Apply the diagnostic to your own analysis" → requires M to model U's likely questions about M's analysis, and respond preemptively

**Kripke model interpretation:** In epistemic game theory, a Kripke model represents possible worlds and the partitions over them that define each agent's information. L12's meta-conservation requirement forces M to model U's partition — to consider what U can and cannot verify about M's analysis. This is exactly the second-order epistemic reasoning that epistemic game theory formalizes.

**Why L12-G (the meta-level) is the strongest gap detector:** A model confabulating at the first order (fake conservation law) would need to also confabulate at the second order (fake meta-analysis of the fake conservation law) in a way that is internally consistent with the first-order confabulation. The probability of maintaining internal consistency across two levels of recursive self-application drops dramatically. This is the information-theoretic reason L12's meta-layer is the most diagnostic: it requires two levels of coherent epistemic state, not one.

---

## 4. Spence's Signaling Model: Education as the Archetype

### 4.1 The Formal Structure

Michael Spence (1973) solved the information asymmetry problem in job markets by identifying education as a credible signal. The key insight: education is not credible because it makes workers more productive — it is credible because it is differentially costly. Low-ability workers face higher costs to obtain the same degree than high-ability workers.

**The single-crossing condition (Spence's key assumption):**
Let c(e, θ) = cost of education level e for worker type θ. The condition:
```
∂c/∂e > 0   (education is costly)
∂²c/∂e∂θ < 0  (marginal cost of education decreases in ability)
```

This "single-crossing property" ensures that the iso-utility curves of different types cross exactly once, creating a separation: there exists a threshold education level e* such that:
- High-ability workers choose e ≥ e* (education worth the lower marginal cost)
- Low-ability workers choose e < e* (education not worth the higher marginal cost)

**Separating equilibrium:** At e*, firms can infer worker type from education level. The signal is credible not because education makes workers productive but because the cost differential makes mimicry irrational for low-ability workers.

**Intuitive Criterion (equilibrium refinement, Cho-Kreps 1987):** Of the many possible separating equilibria, the intuitive criterion selects the least-costly one — the equilibrium where the high-ability worker gets just enough education to prevent mimicry by the low-ability worker, but no more.

### 4.2 Spence Applied to LLM Output Formats

**Mapping the analogy:**

| Spence's job market | Prism application |
|---|---|
| Workers (senders) | LLM instances / inference calls |
| Employers (receivers) | Users evaluating analysis quality |
| Ability θ (private information) | Model's genuine understanding of code |
| Education e (costly signal) | Structural output format (conservation law, bug table, meta-law) |
| Wage w(e) | User's trust in / action on the analysis |

**The single-crossing condition in LLMs:** The analogue of Spence's condition:
```
Marginal cost of producing consistent structural outputs is HIGHER for confabulating models
than for genuinely knowledgeable models
```

For a confabulating model, each additional level of structural specificity requires generating more output that must be internally consistent with previous output — and the probability of maintaining internal consistency decreases exponentially with the number of required consistency checks. For a genuinely knowledgeable model, additional levels of specificity are extractable from the underlying representation and do not require independent invention.

This is Spence's single-crossing condition in disguise: the marginal cost of increasing structural detail is higher for "low-ability" (confabulating) models than for "high-ability" (genuinely knowing) models.

**The separating equilibrium for LLMs:** There exists an output format complexity e* (the prism) such that:
- Models with genuine structural understanding will produce outputs at format e*
- Confabulating models will produce outputs that fail format consistency checks at e*

L12 (at 332 words, three levels of structural specificity) is a candidate for this e*. The empirical evidence supports this: L12 achieves 93% accuracy on structural insights (the separating region) and 42% accuracy on specific bug locations (where confabulation can still partially succeed by generating plausibly-located bugs).

**The intuitive criterion implication:** The optimal prism format is the *least complex* format that achieves separation — not the most complex. Adding L14, L15, etc. would not improve separation; it would only increase cost for all model types. L12 (with its L13 reflexive ceiling) is the natural stopping point — the intuitive-criterion-minimal separating format.

### 4.3 Screening vs. Signaling for LLMs

Spence's framework has a dual: *screening*, where the uninformed party (employer/user) designs a menu of options that induces self-selection. This is Stiglitz's contribution (Nobel 2001, co-awarded with Akerlof and Spence):

**Screening formulation:** Design a menu of output formats {format_1, format_2, ...} such that:
- Models with genuine understanding choose the high-complexity format (e.g., L12 full pipeline)
- Models without genuine understanding choose the low-complexity format (e.g., vanilla response)

The user observes which format the model "chooses" (which is revealed by the quality of output produced) and infers the model's type.

**Prism as screening mechanism:** The prism does not literally offer a menu — but it implicitly screens by setting a structural bar that models with different epistemic states will meet to different degrees. The prism prompt is the screening contract: it specifies what a high-quality output looks like, and models sort themselves by how well they can produce it.

**Critical insight — the prism shifts from pooling to separating equilibrium:** Without a prism, both genuine and confabulating models produce similar-looking outputs (pooling equilibrium: user cannot distinguish types). With the prism, they produce observably different outputs (separating equilibrium: user can infer types). The value of the prism is not just the quality of the output it produces — it is the *equilibrium shift* from pooling to separating.

---

## 5. Mechanism Design for Truth-Telling: VCG and the Revelation Principle

*(This section extends §3.4 of `literature_economics.md` with the signaling game perspective.)*

### 5.1 The Revelation Principle Applied to Prompts

The **revelation principle** (Gibbard 1973, Myerson 1979) states: for any mechanism with a Nash equilibrium, there exists an equivalent **direct revelation mechanism** where:
1. Each agent reports their private type honestly
2. The social choice function is applied to these reports
3. Truth-telling is an equilibrium (incentive-compatible)

**The prompt-as-mechanism design problem:** The prism designer is a mechanism designer. The prompt specifies a format that is the "direct revelation mechanism" — it asks the model to reveal its epistemic state through structural output requirements.

**Is L12 a revelation mechanism?** Formally, L12 is incentive-compatible if truth-telling (producing outputs consistent with genuine understanding) is the model's dominant strategy. This requires:

```
U(genuine output | genuine knowledge) > U(confabulated output | genuine knowledge)
U(confabulated output | limited knowledge) < U(genuine output | limited knowledge)
```

The second condition is not satisfied by default — a confabulating model is not penalized for producing confident structural claims. But it is approximately satisfied *through the index property*: a confabulating model cannot produce genuinely consistent structural claims, so its "attempt at genuine output" (given limited knowledge) will be internally inconsistent. The output format makes confabulation observable, not impossible — but observable confabulation reduces user trust, creating a feedback penalty.

**Dominant strategy vs. Bayesian Nash equilibrium:** VCG achieves dominant-strategy incentive compatibility — truth-telling is optimal regardless of what other agents do. The prism achieves something weaker: approximately-Bayesian incentive compatibility — truth-telling (to the extent the model can self-assess) produces better outcomes in expectation. This is the correct analogue for a single-agent inference call: there are no "other agents" to defect against, so the dominant strategy concept is replaced by "does the format reward genuine analysis over confabulation."

### 5.2 The Peer Elicitation Game: A Provably Truthful Mechanism

Recent research (2025) implements genuine incentive-compatible truth-telling for LLMs through **Peer Elicitation Games (PEG)**:

**Structure:**
- Multiple discriminator LLMs evaluate a generator's outputs independently
- Rewards are based on *mutual information* between discriminators' assessments (not simple agreement)
- The scoring rule: payment based on the determinant of the co-report matrix, which is maximized under truthful reporting

**Theorem (from PEG paper, 2025):** Truth-telling is a **dominant strategy** for each discriminator — it maximizes utility regardless of other discriminators' behavior. This is Lemma 1 of the formal framework.

**Nash equilibrium convergence:** Last-iterate convergence to a truthful Nash equilibrium is proven (Theorem 3). This is stronger than average-case convergence — the final policy is guaranteed to be truthful.

**Connection to L12:** The prism single-call setup cannot replicate PEG's multi-agent guarantees. But the pipeline (L12 + adversarial pass) approximates a two-discriminator PEG: the adversarial model's job is to independently evaluate the L12 model's claims. The synthesis pass is the mutual-information-based reconciliation. The theoretical guarantee from PEG suggests this pipeline approximates a Nash-truthful mechanism.

**Anti-collusion property:** PEG prevents collusion by rewarding calibrated mutual information, not consensus. Two discriminators cannot profitably coordinate around a false but mutually agreeable answer. Applied to the pipeline: the adversarial model cannot "agree" with L12's conservation law for strategic reasons — it is incentivized to find genuine contradictions.

### 5.3 Can We Design a Prompt Where Truth-Telling Is Dominant?

**The mechanism design question for prompts:**

Is there a prompt P such that, for any LLM M with any epistemic state θ:
```
Expected_output_quality(M | P, θ = genuine) >
Expected_output_quality(M | P, θ = confabulating)
```

**Near-sufficient condition:** P achieves dominant-strategy truth-telling if:
1. The format requires cross-level structural consistency (index property)
2. Confabulated outputs produce observably inconsistent cross-level claims
3. The user (or the verification pipeline) can detect this inconsistency
4. Inconsistency reduces the model's (operationalized as: output's) utility score

**Does L12-G satisfy this?** Approximately yes, for the structural insight component. The conservation law + meta-law two-level consistency check makes confabulation at both levels simultaneously much harder than confabulation at either level alone. The bug table adds a third level (concrete code locations) that must be consistent with both abstract levels.

**The four-path routing table as dominant strategy implementation:** The CLAUDE.md routing table ("code + structural? → L12 Sonnet; reasoning? → l12_universal; quick? → SDL") is a mechanism design solution: it maps each task type to the format that best achieves the revelation condition for that type. Different formats are optimal dominant-strategy mechanisms for different task types.

### 5.4 The "Exogenous Commitment Device" Problem

**The fundamental limitation of prompt-based mechanism design:**

The revelation principle requires that the mechanism *enforcer* (who implements the social choice function) is separate from the *agents* (who reveal their types). In standard mechanism design, the mechanism designer is a third party with commitment power.

In prompt-based mechanism design, the "mechanism" (prompt) is enforced only by the model's own processing — there is no external enforcer. The model could, in principle, "ignore" the format constraints and produce whatever it wants. The fact that LLMs generally follow format constraints is a property of their training, not a structural guarantee.

**Implication:** The prism achieves incentive compatibility through *behavioral constraints* (format compliance) rather than *structural constraints* (the Nash equilibrium is the only viable option). This is weaker than mechanism design's formal guarantee but sufficient for practical purposes: the question is whether LLMs follow format instructions reliably enough that the equilibrium analysis holds approximately.

**Empirical confirmation:** The 100% single-shot rate with `--tools ""` (empirically confirmed in Round 35b) suggests that format compliance is reliable for SDL and L12 prisms. This is the empirical validation of the format-as-commitment assumption.

---

## 6. Bayesian Persuasion: The Information Designer's Problem

### 6.1 Kamenica-Gentzkow Framework (2011, Annual Review 2019)

Emir Kamenica and Matthew Gentzkow (2011) established **Bayesian persuasion** as the canonical model of strategic information disclosure. The setup:

- **Sender (S)**: Commits to an *information structure* π (a signal that maps states to distributions over messages)
- **Receiver (R)**: Takes action a ∈ A based on posterior beliefs after seeing the signal
- **Both know**: S's utility function, R's utility function, and the prior μ₀ over states

**The key commitment:** S commits to π *before* observing the state. This is different from cheap talk (where S can adapt messages to the state strategically). By committing to a signal structure, S can credibly persuade R.

**The concavification result:** The sender's optimal information structure achieves the value equal to the *concave closure* (concavification) of S's utility function evaluated at the prior:

```
V*(μ₀) = sup{v(μ₀) : v concave, v(μ) ≤ U_S(μ) for all μ}
```

**Geometric interpretation:** Draw S's utility U_S(μ) as a function of posterior belief μ. The concave closure is the smallest concave function above this curve. The optimal signal structure corresponds to splitting the prior into posteriors that lie on the concave closure.

**When is persuasion possible?**
- If U_S is already concave: no disclosure is optimal (information only hurts S)
- If U_S is convex: full disclosure is optimal
- If U_S is neither: partial disclosure — specific signal structure — is optimal

### 6.2 The Prism Designer as Information Designer

**Reframing:** The prism designer is not designing a prompt to extract information from the model — the designer is an **information designer** choosing the information structure that will be presented to the user.

**Sender = Prism designer (this project)**: Chooses how to structure the model's output format
**Receiver = User**: Takes decisions (trust the analysis, fix bugs, refactor architecture) based on the model's structured output
**State space**: The actual structural properties of the code being analyzed
**Prior μ₀**: User's prior beliefs about the code's quality and structure

**S's utility:** The prism designer wants the user to take the "right" action — fix real bugs, not hallucinated ones; understand genuine structural problems, not fabricated ones. The designer's utility is maximized when the user's actions are well-calibrated to the code's actual properties.

**Optimal information structure for the prism designer:**

The prism designer should commit to an information structure that:
1. Reveals genuine structural properties (increases U_R by enabling correct decisions)
2. Suppresses confabulations (reduces U_R damage from incorrect actions)
3. Is credible to the user (satisfies Bayesian rationality)

**The conservation law as an optimal partition:** The conservation law output (e.g., "Thread Safety × Throughput = C") is a specific *signal partition* — it maps the actual state space (all possible code structures) into a small number of categories. This is exactly the Kamenica-Gentzkow optimal signal: the coarsest partition that preserves the decision-relevant variation in the state space.

**Why coarsen?** Full disclosure (reporting every line of code's analysis) overwhelms the receiver. No disclosure (vanilla summary) loses all structural information. The conservation law is the optimal intermediate: it summarizes the code's structural properties at exactly the level of granularity that enables correct high-level architectural decisions.

### 6.3 The Verbalized Bayesian Persuasion Connection

Recent work (2025) implements Bayesian persuasion with LLMs as both sender and receiver — **Verbalized Bayesian Persuasion (VBP)**:

**Key findings:**
- LLM-as-sender can learn to commit to information structures through *prompt specification* (the prompt IS the commitment device)
- The "verbalized commitment assumption": the sender's signaling strategy (encoded in their prompt) becomes common knowledge to the receiver
- The "verbalized obedience constraint": the receiver follows recommendations only if they are incentive-compatible

**Connection to our project:**
- The prism prompt IS the sender's committed information structure
- The user IS the receiver who updates beliefs via the structured output
- The conservation law is the message that the sender-model generates under the committed information structure

**Critical finding from VBP:** "Information obfuscation prompts provide minimal additional benefit, indicating the VBP framework can spontaneously learn to withhold or deceive." Applied: we should not add explicit "tell me what you don't know" instructions to the prism — the model learns to withhold under the standard format anyway, and explicit prompting for uncertainty may actually trigger sycophancy (confabulating uncertainty signals to appear appropriately humble).

**The two-stage prism derivation from Bayesian persuasion theory:**

The VBP framework supports the empirical finding that two-stage pipelines (L12 + adversarial) outperform single-stage. In Kamenica-Gentzkow terms:

1. **Stage 1 (L12)**: Sender-model commits to a conservation-law partition. This is the "first-order signal structure."
2. **Stage 2 (adversarial)**: A second sender challenges the first sender's signal structure. This is the "posterior updating" step — the user's posterior after Stage 2 is a refinement of their posterior after Stage 1.

The optimal two-sender Bayesian persuasion result (Gentzkow-Kamenica 2017) shows that competing senders can achieve better outcomes than a single sender, even when they have opposed interests. This is the game-theoretic basis for the adversarial pipeline: the adversarial sender's interest in finding flaws *complements* the L12 sender's interest in finding genuine structure, improving overall calibration.

### 6.4 Optimal Amount of Structure: The Concavification Prescription

**The practical question for prism design:** How much structure is optimal? Too little → cheap talk. Too much → overwhelming, user cannot extract signal.

**Kamenica-Gentzkow prescription:** The optimal signal is the one whose posteriors lie on the concave closure of U_S(μ). For prism design:

- U_S(μ) is the utility to the prism designer of the user having posterior belief μ about the code's quality
- The concave closure identifies the optimal "detail level" — the partition of the state space that maximizes user decision quality

**Translating to word count:** The empirical finding (CLAUDE.md Principle 17) that "Depth × Universality = constant" is a Bayesian persuasion result: more detailed information structures (higher word count, more specific vocabulary) achieve higher depth on matched domains but lose universality — the signal becomes domain-specific and fails to transfer. This is exactly the concavification constraint: the optimal partition is domain-specific, but domain-specificity reduces the feasible state space over which the signal can be applied.

**The 332-word sweet spot:** L12 at 332 words achieves the concave-closure optimum for code analysis tasks. Below ~150 words (the compression floor): the signal is too coarse, falling below the minimum detail needed to induce correct user decisions. Above ~400 words: the signal is too fine, domain-specific vocabulary leaks assumptions that mismatch non-target domains. The empirically discovered compression floor and ceiling are the information-theoretic bounds on the optimal signal structure.

---

## 7. The S×V=C Conservation Law as Signaling Game Equilibrium

### 7.1 Reinterpreting the Conservation Law

The S×V=C conservation law (Specificity × Verifiability = Constant) was discovered empirically. The signaling game framework provides a structural explanation for why this form emerges:

**The conservation law is the equilibrium condition of the signaling game.**

In a separating equilibrium, each type (high-knowledge model, low-knowledge model) produces a distinct signal. The equilibrium condition is that no type wants to deviate — high-knowledge models cannot profitably reduce their structural detail (they would lose user trust), and low-knowledge models cannot profitably increase it (they cannot maintain consistency).

**Specificity and Verifiability as the two dimensions of the separating equilibrium:**

- **Specificity** = how precisely the signal identifies the model's type (high specificity → fewer types can produce the signal)
- **Verifiability** = how easily the receiver can check the signal's honesty (high verifiability → cheating is detected)

In the signaling game equilibrium, increasing specificity requires decreasing verifiability because:
- High-specificity claims (detailed structural insights) require precise cross-level consistency → harder to verify independently
- High-verifiability claims (checkable facts like line numbers) require reducing abstraction → lower specificity

**The conservation law is the equilibrium condition:** At the separating equilibrium boundary, the tradeoff is exact: S × V = constant. Moving off this boundary in either direction:
- Increase S beyond equilibrium: the signal becomes too costly for even high-knowledge models to produce consistently → equilibrium breaks down
- Increase V beyond equilibrium: the signal becomes too easy for low-knowledge models to fake → separating equilibrium collapses to pooling

**The mathematical form S × V = C reflects the Cobb-Douglas structure of separating equilibria:** The rectangular hyperbola is the natural equilibrium boundary shape when the two constraints (type-distinguishing power and faking resistance) are multiplicative rather than additive.

### 7.2 Why Different Model Classes Have Different Constants C

The conservation constant C varies by model class (Haiku C_H < Sonnet C_S < Opus C_O). In signaling game terms:

**C is the model's type-separation capacity.**

A model with higher epistemic capacity can produce signals that are simultaneously more specific AND more verifiable — it can maintain cross-level consistency at higher detail levels. The prism shifts this capacity frontier, but each model class has a ceiling.

**The prism's role:** The prism does not change the fundamental S × V = C shape — it shifts C outward. The shift magnitude is larger for weaker models (the shadow price effect: Haiku gains more from a prism than Opus does) because weaker models are further below their natural separation capacity, and the prism's structural format allows them to reach higher-C operating points.

**Formal interpretation:** The prism provides a coordination mechanism — it tells the model *which* separating equilibrium to select from among the many possible equilibria of the signaling game. Without the prism, weak models default to low-C pooling equilibria. The prism coordinates on a high-C separating equilibrium.

### 7.3 The Pooling → Separating Shift as the Core Value Proposition

The entire project's empirical value — prisms beat vanilla, Haiku + L12 beats Opus vanilla, depth 9.8 vs 7.3 — is the value of the *equilibrium shift*.

**In pooling equilibrium:** All outputs look similar to the user (authoritative, confident, comprehensive). The user cannot distinguish genuine insights from confabulations. They discount everything to average quality.

**In separating equilibrium (with prism):** Outputs differentiate along structural consistency dimensions. The user can identify the high-quality conservation laws (genuine analysis) and the inconsistent bug locations (confabulation boundary). Trust is correctly calibrated.

**The 2.5-point depth gap (9.8 vs 7.3) IS the equilibrium shift value.** It is not that the prism "teaches" the model something new. It is that the prism moves the interaction from a pooling equilibrium (both model types look the same, user discounts both) to a separating equilibrium (model types are distinguishable, user correctly differentiates).

**Crawford-Sobel connection:** The shift from pooling to separating equilibrium in Crawford-Sobel terms corresponds to moving from the babbling equilibrium (N=1, no information transmission) to a multi-partition equilibrium (N>1, coarse but real information transmission). The prism is the partition-generating mechanism.

---

## 8. Synthesis: A Unified Signaling Game Model of Confabulation

### 8.1 The Five Layers

| Layer | Framework | Core claim | Observable consequence |
|---|---|---|---|
| 1. Signal type | Zahavi / Index vs Handicap | L12 output is an index signal (structurally impossible to fake consistently), not a handicap signal | Cross-level consistency is the separating mechanism |
| 2. Credibility regime | Crawford-Sobel | Without prism: babbling equilibrium (no information transmission). With prism: partition equilibrium (coarse but reliable) | Depth gap (9.8 vs 7.3) is the credibility regime shift |
| 3. Epistemic state | Epistemic game theory (Aumann) | Prism forces M to reveal epistemic type via structural output; U infers M's knowledge state without direct observation | Conservation laws and meta-laws are type-revealing signals |
| 4. Type separation | Spence / Screening | Single-crossing condition holds: confabulating models face higher marginal cost of structural consistency | 93% accuracy on structural insights (separating region) vs 42% on bugs (pooling region) |
| 5. Information design | Kamenica-Gentzkow | The prism is an optimal signal partition: coarse enough to be universal, specific enough to enable correct decisions | 332-word sweet spot; Depth × Universality = constant |

### 8.2 Novel Predictions from the Signaling Game Framework

These predictions follow from theory but have not been explicitly tested:

**Prediction SG1: The conservation law is the minimal separating signal.**
The Spence intuitive criterion predicts the least-costly separating format. The conservation law (abstract, short) is less costly than the full multi-level structural analysis. A prism that produces only conservation laws (without bug tables) would still achieve partial separation at lower cost. Test: compare L12 with a conservation-law-only variant for depth vs. cost trade-off.

**Prediction SG2: Adding explicit uncertainty requests degrades output quality.**
Bayesian persuasion (VBP finding): "information obfuscation prompts provide minimal additional benefit." Adding "please indicate your confidence in each claim" to L12 would trigger sycophantic uncertainty signaling — confabulated humility rather than genuine uncertainty — reducing signal quality. Test: compare L12 with L12 + "rate each claim confidence 1-10" on real production code.

**Prediction SG3: Multi-agent pipeline approximately achieves Nash truthfulness.**
PEG theory predicts that a two-discriminator setup (L12 + adversarial pass) converges to a truthful Nash equilibrium. The convergence rate is O(√T) in PEG's rounds; for our two-call pipeline, this is a one-step approximation. Larger pipelines (more adversarial passes) should converge faster. Test: compare 1-adversarial vs 2-adversarial vs 3-adversarial passes for calibration accuracy.

**Prediction SG4: Sycophancy bias b predicts optimal prism complexity.**
Crawford-Sobel: the number of credible partitions N(b) decreases with bias b. Sycophancy research shows b varies by model (Haiku has higher sycophancy than Opus). This predicts that optimal prism complexity is model-dependent: higher-b models need simpler prisms (fewer partition levels) to maintain credibility. This matches the empirical finding that SDL (3 steps) is optimal for Haiku while L12 (13 levels) is optimal for Sonnet/Opus.

**Prediction SG5: The separating equilibrium breaks under adversarial prompting.**
If users are told to push back on the model's conservation laws, the signaling game equilibrium shifts. Models under adversarial pressure may either (a) maintain their structural claims under genuine analysis, or (b) abandon the conservation law under confabulation. This is the Crawford-Sobel prediction: when the "bias" is introduced by adversarial framing, the partition equilibrium degrades. The adversarial pass is valuable precisely because it is a *controlled* bias that tests signal robustness before user deployment.

**Prediction SG6: Index signals are more robust to model updates than handicap signals.**
As LLMs improve, handicap signals (which depend on the absolute cost of producing structured output) lose their credibility — better models can fake the cost. Index signals (which depend on structural consistency) remain valid because the consistency requirement is not a cost but a logical constraint. L12's cross-level consistency requirement should remain a reliable separator across model generations. Test: compare L12 separation effectiveness on GPT-4 vs GPT-5 vs Claude models.

### 8.3 What the Signaling Framework Conceals

Applying L13 reflexivity to this analysis:

**The framework's own conservation law:** `Signal reliability × Signal universality = Constant`

- High-reliability signals (structurally consistent cross-level outputs) are domain-specific — they work on code but fail on text without structural hierarchy.
- High-universality signals (SDL, l12_universal) sacrifice reliability — they work on any domain but the separation between genuine and confabulated is less sharp.

**What this analysis conceals:**

1. **Dynamic signaling:** This analysis treats the prism as a static information structure. In reality, LLM training evolves — models learn to produce conservation-law-shaped outputs without genuine structural understanding (adversarial optimization against the prism). This is the "Goodhart's Law" failure mode: when the signal becomes a target, it ceases to be a reliable signal.

2. **Multi-principal problem:** The analysis assumes one principal (user). In practice, there are many principals (the model's training company, the users, the regulators) with potentially conflicting objectives. The prism is incentive-compatible for one principal's objectives but may be exploited under another principal's incentives.

3. **The model is not a rational agent:** Signaling games assume strategic agents who maximize expected utility. LLMs are not strategic agents — they are function approximators. The "equilibrium" analysis holds only insofar as LLM behavior approximates the equilibrium predictions, which is an empirical question, not a theoretical guarantee.

4. **Confabulation has structure:** This analysis treats confabulation as random noise around truth. But confabulation has systematic structure — it follows statistical patterns in training data. A confabulating model's "fake conservation law" is not random; it is the most statistically likely conservation-law-shaped output given the code. This systematic structure may be exploitable: a sufficiently capable confabulator might produce internally-consistent-seeming structural outputs by pattern-matching from training data.

**The meta-law:** The signaling framework improves on vanilla analysis exactly as prisms improve on vanilla LLM outputs — by imposing structure that makes genuine analysis distinguishable from pattern-matching. But the framework conceals that both prisms and signaling theory are themselves subject to Goodhart's Law: the structural form can become a target, and the separation will degrade as models are trained on examples of good L12 output.

---

## References

### Costly Signaling and Honest Signals
- **Zahavi, A.** (1975). "Mate selection — a selection for a handicap." *Journal of Theoretical Biology* 53(1): 205-214. [Original handicap principle]
- **Grafen, A.** (1990). "Biological signals as handicaps." *Journal of Theoretical Biology* 144(4): 517-546. [Game-theoretic formalization]
- **Bergstrom, C.T., Számadó, S., Lachmann, M.** (2002). "Separating Equilibria in Continuous Signalling Games." *Proceedings of the Royal Society B* 269: 1. [Low-cost separating equilibria]
- **Penn, D.J., et al.** (2020). "The Handicap Principle: how an erroneous hypothesis became a scientific principle." *Biological Reviews* 95(2): 652-670. [PMC7004190 — critical review]
- **Johnston, R.A., et al.** (2014). "The evolution of index signals to avoid the cost of dishonesty." *Proceedings of the Royal Society B* 281: 20140876. [PMC4123701 — index signals]
- **Lachmann, M., Számadó, S., Bergstrom, C.T.** (2001). "Cost and conflict in animal signals and human language." *PNAS* 98(23): 13189-13194. [Index as infinite-cost handicap]

### Cheap Talk and Strategic Information Transmission
- **Crawford, V., Sobel, J.** (1982). "Strategic Information Transmission." *Econometrica* 50(6): 1431-1451. [Canonical cheap talk model]
- **Sobel, J.** (2007). "Signaling Games." Encyclopedia article — UCSD. [Review of signaling game equilibria]
- **A Fine Theorem** (2011). "'Strategic Information Transmission,' V. Crawford & J. Sobel (1982)." Blog review.

### Epistemic Game Theory
- **Aumann, R.J.** (1976). "Agreeing to Disagree." *Annals of Statistics* 4(6): 1236-1239. [Common knowledge of posteriors]
- **Aumann, R.J.** (1987). "Correlated Equilibrium as an Expression of Bayesian Rationality." *Econometrica* 55(1): 1-18.
- **Brandenburger, A., Dekel, E.** (1987). "Rationalizability and Correlated Equilibria." *Econometrica* 55: 1391-1402.
- **Dekel, E., Siniscalchi, M.** (2015). "Epistemic Game Theory." *Handbook of Game Theory* 4: 619-702. [Northwestern — comprehensive review]
- **Bonanno, G.** (2015). "Epistemic Foundations of Game Theory." *UC Davis Handbook chapter.*
- **Brandenburger, A.** (2007). "Epistemic Game Theory: Complete Information." Working paper.

### Signaling, Screening, and Information Asymmetry
- **Spence, M.** (1973). "Job Market Signaling." *Quarterly Journal of Economics* 87(3): 355-374. [Nobel 2001 — education as signal]
- **Akerlof, G.A.** (1970). "The Market for Lemons." *Quarterly Journal of Economics* 84(3): 488-500. [Nobel 2001]
- **Stiglitz, J.E.** (1975). "The Theory of Screening, Education, and the Distribution of Income." *American Economic Review* 65(3): 283-300. [Nobel 2001]
- **Cho, I.K., Kreps, D.M.** (1987). "Signaling Games and Stable Equilibria." *Quarterly Journal of Economics* 102(2): 179-221. [Intuitive criterion]

### Mechanism Design and Revelation Principle
- **Gibbard, A.** (1973). "Manipulation of voting schemes: a general result." *Econometrica* 41: 587-601. [First revelation principle]
- **Myerson, R.B.** (1979). "Incentive Compatibility and the Bargaining Problem." *Econometrica* 47(1): 61-73. [Bayesian revelation principle]
- **Myerson, R.B.** (1981). "Optimal Auction Design." *Mathematics of Operations Research* 6(1): 58-73.
- **VCG**: Vickrey (1961), Clarke (1971), Groves (1973) — dominant-strategy truthfulness in resource allocation.
- **Nobel Prize Scientific Background** (2007). "Mechanism Design Theory." [nobelprize.org/uploads/2018/06/advanced-economicsciences2007.pdf]

### Bayesian Persuasion and Information Design
- **Kamenica, E., Gentzkow, M.** (2011). "Bayesian Persuasion." *American Economic Review* 101(6): 2590-2615. [Canonical framework]
- **Kamenica, E.** (2019). "Bayesian Persuasion and Information Design." *Annual Review of Economics* 11: 249-272. [Review including concavification]
- **Bergemann, D., Morris, S.** (2016). "Information Design, Bayesian Persuasion, and Bayes Correlated Equilibrium." *American Economic Review: P&P* 106(5): 586-591.

### LLM-Specific: Hallucination, Sycophancy, and Game Theory
- **Wang, X. et al.** (2022). "Self-Consistency Improves Chain of Thought Reasoning in Language Models." *ICLR 2023.* [arxiv.org/abs/2203.11171]
- **Hallucination Survey** (2025). "Large Language Models Hallucination: A Comprehensive Survey." *arXiv 2510.06265.* [Taxonomy: intrinsic/extrinsic, aleatoric/epistemic]
- **Uncertainty Quantification Survey** (2025). "Uncertainty Quantification for Hallucination Detection in LLMs." *arXiv 2510.12040.* [Aleatoric vs epistemic, calibration limits]
- **Epistemic Stability** (2026). "Toward Epistemic Stability: Engineering Consistent Procedures for Industrial LLM Hallucination Reduction." *arXiv 2603.10047.* [Five engineering procedures, structured context effects]
- **Sycophancy Survey** (2024). "Sycophancy in Large Language Models: Causes and Mitigations." *arXiv 2411.15287.* [b parameter, empirical conflict rates]
- **Peer Elicitation Games** (2025). "Incentivizing Truthful Language Models via Peer Elicitation Games." *arXiv 2505.13636.* [Dominant strategy truthfulness, Nash convergence]
- **Verbalized Bayesian Persuasion** (2025). "Verbalized Bayesian Persuasion." *arXiv 2502.01587.* [LLM as Bayesian persuasion sender/receiver]
- **LLM-Nash Games** (2025). "Reasoning and Behavioral Equilibria in LLM-Nash Games." *arXiv 2507.08208.* [Epistemic states, reasoning equilibria]
- **Game Theory + LLMs Survey** (2025). "Game Theory Meets Large Language Models: A Systematic Survey." *arXiv 2502.09053.* [ICSAP, strategic preference reporting]
- **Prover-Verifier Games** (2024). "Prover-Verifier Games Improve Legibility of LLM Outputs." *OpenAI.* [cdn.openai.com/prover-verifier-games-improve-legibility-of-llm-outputs/legibility.pdf]

### Connection to This Project
- `experiment_log.md` Rounds 1-40: Empirical S×V=C law, 1000+ experiments, pooling→separating equilibrium shift measured as depth gap (9.8 vs 7.3)
- `research/literature_economics.md`: Lagrangian, Blackwell, VCG, Akerlof, principal-agent formalization of the same phenomena
- `CLAUDE.md` Principles 13-19: Empirical rules that follow from the signaling game equilibrium conditions
