# Structural Analysis: Experimental Design

## Falsifiable Claim

**The deepest structural problem in this design is that the hypothesis, the statistical test, and the power analysis are each aimed at three different inferential targets.** The hypothesis predicts a *three-way interaction* (load × pressure × dilemma type), the analysis plan describes a *2×2 ANOVA with a repeated measure* (which could test this but isn't stated as doing so), and the power analysis is calibrated for what appears to be a *simple pairwise between-group difference* at d=0.5. This misalignment means the study is likely underpowered for its own central claim by a factor of roughly 4×, and the researchers may not have clearly conceptualized what statistical test actually corresponds to their theory.

---

## The Argument: Three Expert Tests

### Expert 1 (Defends the Claim) — Methodologist

The claim is correct and arguably understated. Let's trace the logic carefully.

The prediction is: *"high load + time pressure increases utilitarian responses to personal dilemmas."* Parse this. It says the combination of load AND pressure (not either alone) shifts judgment, and it does so specifically for personal dilemmas (not impersonal ones). That is definitionally a three-way interaction: the two-way interaction between load and pressure is *moderated* by dilemma type.

Now consider the power analysis. Cohen's d=0.5 with n=30 per cell yields roughly 80% power for a *two-sample t-test*. But detecting interaction effects in factorial designs requires approximately **four times** the sample size needed for the corresponding main effect of the same magnitude. For a three-way interaction, the multiplier is worse still because:

- The effect is estimated from a contrast among *all eight* sub-conditions (4 between-subjects cells × 2 dilemma types).
- Error variance in the three-way term absorbs residual variance from all lower-order interactions.
- The within-subject factor (dilemma type) helps, but only if the correlation between personal and impersonal responses is high, which is an untested assumption.

A realistic estimate: to detect a three-way interaction of the equivalent magnitude at 80% power, you'd need roughly **n=80–120 per cell**, not 30. This study with N=120 total is powered for a world in which its own hypothesis is irrelevant.

### Expert 2 (Attacks the Claim) — Experimental Psychologist

This overstates the problem by assuming the researchers *must* test a three-way interaction. There's a defensible alternative reading of both the hypothesis and the analysis plan.

**The hypothesis could be tested as a planned contrast.** "High load + time pressure increases utilitarian responses to personal dilemmas" can be operationalized as: within the personal-dilemma data only, compare condition 4 (high load + time pressure) against the other three conditions (or against condition 1 as the control). This is a focused, single-degree-of-freedom contrast, which is **far more powerful** than an omnibus three-way interaction test. Researchers in moral psychology (following Greene et al.) routinely analyze personal and impersonal dilemmas in separate models precisely to avoid the three-way interaction problem.

Furthermore, d=0.5 with 30 per cell is not unreasonable for such a contrast if you model it as a targeted comparison. The 2×2 ANOVA "with dilemma type as repeated measure" may simply be the omnibus framing for a paper, while the real inferential work is done in planned contrasts. Many analysis plans describe the ANOVA as a structural scaffold and then focus on specific comparisons.

So: the power analysis might be appropriate for the test the researchers actually intend to run, even if the write-up is vague. The problem might be **communication**, not **design**.

### Expert 3 (Probes Assumptions) — Philosopher of Science

Both arguments take for granted a more fundamental assumption: **that the study's inferential logic is coherent enough for the power question to be the deepest problem.** I want to probe what's beneath the disagreement.

**What both sides assume:**
1. That "cognitive load" as operationalized (memorize a 7-digit number) and "cognitive load" as theorized (depleting deliberative resources during moral evaluation) are the same thing. But there's no manipulation check reported. If participants simply abandon the digit string when confronted with an emotionally engaging moral dilemma, the load manipulation is void and no amount of power fixes a null treatment.

2. That the Likert scale linearly maps onto "utilitarian vs. deontological" responding. But a 7-point acceptability rating conflates moral judgment with confidence, emotional reactivity, and demand characteristics. The theoretical construct is categorical (utilitarian vs. deontological reasoning), but the measurement is continuous and possibly non-linear.

3. That 12 dilemmas (6 per type) per person generate stable within-person estimates. But the variance between dilemmas within a type (some personal dilemmas are far more emotionally engaging than others) may swamp the between-condition variance. This is a **stimulus sampling problem**: the design treats dilemmas as fixed effects, but the hypothesis generalizes over the population of dilemmas.

That said, I think the power-hypothesis misalignment IS genuinely deep because it reveals a **conceptual confusion**: the researchers haven't clearly decided whether their claim is about a specific cell, an interaction, or a three-way interaction. That confusion propagates everywhere — into the analysis plan, into the power calculation, and into what would count as confirmatory versus exploratory evidence. The power problem is a *symptom* of this conceptual unclarity, which is the actual structural defect.

---

## Verdict: Transformed

The argument **transforms** my original claim rather than simply falsifying or confirming it.

### What I claimed:
The power analysis is misaligned with the hypothesis by a factor of ~4×.

### What I know now that I couldn't know before the argument:

**The power misalignment is real but is a downstream symptom, not the root cause.** The deepest structural problem is a **cascade of ambiguity between theoretical prediction, operational hypothesis, and statistical test:**

| Layer | What's Stated | What's Actually Needed | Gap |
|---|---|---|---|
| **Theory** | Dual-process: load disrupts deliberation → utilitarian shift for personal dilemmas | Clear causal model specifying which comparison tests the theory | No specification of whether the prediction is about the *combination* being special (interaction) or load and pressure having *additive* effects |
| **Hypothesis** | "High load + time pressure increases utilitarian responses to personal dilemmas" | Disambiguation: is this a simple cell contrast, a two-way interaction within personal dilemmas, or a three-way interaction? | Ambiguous between all three |
| **Analysis** | 2×2 ANOVA with repeated measure | Pre-registered planned contrasts specifying the exact test | Omnibus test that doesn't map to the specific prediction |
| **Power** | d=0.5, n=30/cell | Power for whichever test actually adjudicates the hypothesis | Calculated for a test that may not be the one run |
| **Measurement** | 7-point Likert scale | Manipulation check for load; validated mapping from scale to utilitarian/deontological construct | No manipulation check; construct validity assumed |

The most actionable structural fixes, in order of priority:

1. **Specify the exact contrast** that would confirm versus disconfirm the hypothesis *before* data collection.
2. **Add a manipulation check** for cognitive load (e.g., digit recall accuracy after each dilemma).
3. **Re-run the power analysis** for that specific contrast, likely requiring N=240–480 total.
4. **Treat dilemmas as random effects** (mixed-effects model) rather than fixed repeated measures to address the stimulus sampling problem.
5. **Pre-register** the analysis plan with sufficient specificity to distinguish confirmatory from exploratory findings.

The design is not unsalvageable — but as currently specified, it contains enough structural ambiguity that both a positive and a null result would be uninterpretable.
