# Generative Diagnostic: Experimental Design Analysis

## The Falsifiable Claim

**The deepest structural problem: the independent variables systematically destroy the validity of the dependent variable.** Cognitive load and time pressure degrade exactly the cognitive capacity required to produce meaningful 7-point Likert responses. The design cannot distinguish a genuine shift in moral cognition from measurement artifact (satisficing, scale-center anchoring, increased noise). The IV attacks its own DV.

---

## The Dialectic

**Expert 1 (Defender):** Correct. Under dual-task load while holding 7 digits, participants can't reliably differentiate between adjacent Likert points. Any mean shift toward "utilitarian" responses could be regression to the scale midpoint. The ANOVA will report clean F-statistics on what is actually degraded measurement. The Bonferroni correction polishes a fundamentally contaminated signal.

**Expert 2 (Attacker):** This critique indicts the entire cognitive load literature. If it were fatal, hundreds of published studies are invalid. More importantly, this design has a built-in test: if the effect were pure measurement noise, it would affect personal and impersonal dilemmas equally. The *predicted interaction*—utilitarian shift specifically for personal dilemmas—is not explainable by generic scale degradation. Response time as covariate and confidence ratings also help triangulate genuine judgment shifts versus noise.

**Expert 3 (Probing what both assume):** You both presuppose that "moral judgment" is a stable object that the Likert scale either captures cleanly (Defender's standard) or captures noisily (Attacker's concession). Neither of you questions whether the thing being measured *exists as the same construct* across conditions. When you're holding 7 digits in memory and have 15 seconds, are you making a moral judgment at all—or are you performing a different cognitive operation (pattern-matching, affect-tagging, heuristic firing) that happens to produce a number on the same scale? The design's theoretical prediction requires that load *modulates* a process. But load may *replace* the process entirely.

## The Transformed Claim

The deepest problem is not methodological (IV degrades DV measurement) but **ontological**: the design requires moral judgment to be a unitary construct that cognitive load shifts along a dimension, but it simultaneously creates conditions under which moral judgment may become a categorically different cognitive process. The study cannot distinguish between:

- *The same judgment, made under worse conditions* (measurement noise)
- *A different kind of judgment, made under different conditions* (construct non-identity)

Its theoretical conclusions depend entirely on which of these is happening, and nothing in the design adjudicates between them.

**The diagnostic gap:** What appeared to be a confound problem (methods) is actually a construct identity problem (theory). The statistical architecture—a clean 2×2 ANOVA with repeated measures—presumes measurement invariance across conditions without testing it, and cannot test it, because testing it would require an independent measure of "what kind of moral cognition is happening," which is precisely what the study lacks.

---

## The Concealment Mechanism

**Procedural symmetry.** All four cells use identical dilemmas, identical scales, identical instructions, identical analysis. This surface uniformity creates the illusion that the same thing is being measured four times under different conditions. The 2×2 factorial structure reinforces this: it visually and statistically treats cell means as commensurable quantities. The power analysis (Cohen's d=0.5, N=30/cell) further conceals the problem by framing the question as *"can we detect the effect?"* rather than *"is the effect we detect the effect we think it is?"*

Bonferroni correction, IRB approval, preregistered exclusion criteria—each adds a layer of methodological legitimacy that makes the design *look* rigorous without addressing whether its fundamental measurement assumption holds.

---

## The Engineered Concealment (Passes Review, Deepens the Problem)

**Proposed improvement:** Add a manipulation check protocol. After each dilemma block, participants in the high-load condition report their memorized 7-digit number. Record accuracy. Exclude participants who fail >40% of checks. Additionally, embed one "catch" dilemma per block (e.g., "Is it acceptable to save five people by pressing a button that harms no one?") to verify engagement. Report manipulation check pass rates by condition in a methods table.

**Why this passes review:** It demonstrates that the cognitive load manipulation was sustained, that participants were engaged, and that data quality was monitored. Any reviewer who flags cognitive load validity concerns will be satisfied.

**Why it deepens concealment:** It provides a concrete, checkable metric of rigor that diverts attention from the uncheckable assumption. Reviewers now have something to scrutinize (pass rates, exclusion counts), which means they are *not* scrutinizing construct equivalence across conditions.

---

## Three Properties Visible Only Through the Strengthening Attempt

**1. Selection–measurement entanglement.** Excluding participants who fail manipulation checks selectively retains people who are best at maintaining dual-task performance—exactly the people for whom cognitive load is *least disruptive*. The "improvement" creates an inverse relationship: the more rigorously you verify the manipulation worked, the more you select participants in whom it worked least. Internal validity and effect validity pull against each other, and the exclusion criterion disguises this as quality control.

**2. The catch dilemma reveals the hidden invariance assumption.** Defining a dilemma as "obvious" (everyone should answer the same way regardless of condition) smuggles in the assumption that basic moral cognition is condition-invariant. But that is precisely what the study claims to be testing. If high load + time pressure genuinely alters moral reasoning, then even "obvious" dilemmas may not be obvious under load. The catch trial treats as a fixed reference point the very thing the experiment claims is moving.

**3. The manipulation check creates a paradox with no valid outcome.** If nearly everyone passes (remembers the number), the load was sustained but may have been insufficient to affect deeper cognition—you've verified a surface manipulation, not a deep one. If many fail, the manipulation was too strong for the task context and you must exclude heavily, losing power and generalizability. If pass rates differ by dilemma type, you've discovered a confound you cannot control. There is no manipulation check result that actually validates the design—yet the existence of the check creates the *appearance* of validation, which is the concealment mechanism operating at a second level.

---

## Summary Diagnostic

| Layer | What it looks like | What it is |
|---|---|---|
| Surface | Clean 2×2 factorial, well-powered, preregistered | Methodologically standard |
| First depth | IV may add noise to DV | A confound |
| True depth | The construct measured in high-load cells may not be the same construct measured in low-load cells | An ontological incommensurability hidden by procedural symmetry |
| Concealment | Identical procedures → assumption of identical constructs | The design's greatest strength (uniformity) is its deepest vulnerability |

The study will produce statistically interpretable results regardless of whether its foundational assumption holds. That is the structural problem: **it cannot fail in a way that reveals its own invalidity.**
