

# Falsifiable Hypothesis

## My Claim

**The deepest structural problem in this deployment is not any single bias or accuracy gap, but a fundamental epistemic closure: the system is structurally designed to be unimprovable because the combination of proprietary opacity, ground-truth circularity, and advisory-mode anchoring creates a feedback loop where the system's errors become invisible to the very processes that would need to detect them.**

This is falsifiable: if you can identify a concrete mechanism within this deployment's actual structure through which systematic errors in the most vulnerable subgroups (pediatric, elderly, unaccompanied) would be reliably detected, escalated, and corrected, my claim is wrong.

---

## The Adversarial Argument

### Expert 1 (Defending the claim): The Feedback Trap

The circularity is real and multi-layered:

**Layer 1 — Ground truth is contaminated.** The training labels are attending physician scores, which already contain the biases being replicated (under-triaging atypical presentations in elderly patients, under-weighting nonverbal pain cues in children). The system doesn't learn triage; it learns *physician pattern-matching, including its systematic failures*.

**Layer 2 — Advisory mode creates anchoring, not oversight.** Decades of cognitive science literature on automation bias shows that when a decision-maker sees a machine suggestion *before* forming their own judgment, the suggestion functions as an anchor. The nurse doesn't independently verify — they adjust from the AI's number. This means the AI's errors propagate into the new ground truth (nurse decisions), which will likely become the next round of training data or the metric against which the system is evaluated. *Agreement between nurse and AI will be mistaken for accuracy.*

**Layer 3 — Opacity prevents root-cause analysis.** Without feature importance disclosure or a model card, when a failure occurs (a pediatric patient under-triaged, an elderly patient whose atypical MI presentation was scored acuity 4), no one can determine *why*. Was the camera feed misinterpreting a child's stillness as calm? Was the translation layer stripping urgency markers from a non-English complaint? The proprietary black box means failure modes are individually legible (bad outcome) but structurally opaque (no pathway to fix the cause).

**The closure:** Errors are hardest to detect in exactly the populations where accuracy is lowest. Unaccompanied patients — who already lack an advocate — are 6% more likely to be mis-triaged, and there is no mechanism for anyone to notice this *as a pattern* rather than as isolated incidents.

---

### Expert 2 (Attacking the claim): Advisory Mode Is Real Oversight

This overstates the feedback trap. Several structural features push against epistemic closure:

**Counter 1 — Nurses are not naive automata.** ED nurses are among the most clinically experienced practitioners in medicine. Advisory mode means the AI doesn't *act* — a human does. Experienced nurses regularly override clinical decision support tools. Anchoring bias is real but not deterministic, especially in high-stakes environments where professionals are trained to exercise independent judgment.

**Counter 2 — Clinical outcomes provide external ground truth.** Triage isn't a subjective label that disappears after assignment. If a patient triaged as acuity 4 decompensates in the waiting room, that's a detectable sentinel event. Hospitals have morbidity and mortality review processes, incident reporting systems, and quality metrics (like left-without-being-seen rates, time-to-treatment for STEMI/stroke) that exist independently of the AI system. These are error-detection mechanisms that break the supposed feedback loop.

**Counter 3 — The accuracy numbers, while imperfect, are disclosed.** The hospital *already knows* about the subgroup disparities. The 72% pediatric and 79% elderly numbers exist because someone did the sub-group analysis. This is evidence of monitoring capability, not epistemic closure. The question is whether they act on it — a governance problem, not a structural impossibility.

**Counter 4 — The $2.1M savings create institutional incentive for monitoring.** If the system produces bad outcomes that lead to malpractice suits (the hospital assumes liability, remember), the financial case collapses. Self-interest creates a feedback signal.

---

### Expert 3 (Probing assumptions): What Both Sides Take for Granted

Both arguments share unexamined assumptions that may be more important than the disagreement:

**Assumption 1: That "accuracy" as measured is the right frame.** Both sides treat the 87%/79%/72% numbers as meaningful. But accuracy against *what*? Against attending physician labels that are themselves noisy, biased, and context-dependent. A system that is 87% accurate against a flawed gold standard may be systematically wrong in ways the accuracy metric cannot surface. The real question is: *accurate at predicting what the doctor would have said, or accurate at predicting who is actually sickest?* These are different things, and no one in this scenario is measuring the second one.

**Assumption 2: That the camera feed is a feature, not a liability.** The posture/movement/grimacing analysis introduces an entire modality that is deeply confounded by age, disability, cultural expression of pain, mobility aids, and medication effects. The sub-group accuracy gaps likely trace significantly to this modality, but without feature importance data, no one can test this. Both sides argue about whether the system is fixable without asking whether an entire input channel should exist.

**Assumption 3: That "advisory mode" is a stable equilibrium.** The $2.1M savings projection assumes staffing optimization — meaning fewer nurses, faster throughput, or both. Over time, institutional pressure will push advisory mode toward greater automation. The structural trajectory is toward *more* reliance on the system, not less. Today's "advisory" is tomorrow's "why are you overriding the system and slowing down throughput?" This isn't a slippery slope fallacy — it's a predictable institutional dynamic when cost savings are the deployment rationale.

**Assumption 4: That the nurses' union exclusion is a process failure rather than a structural tell.** The people with the most granular, embodied knowledge of triage failure modes — the nurses — were deliberately excluded from deployment design. This isn't an oversight. It's a structural choice that optimizes for administrative and vendor interests over clinical safety. Both sides argue about whether errors are detectable without noting that the people best positioned to detect them have been structurally silenced.

---

## What the Argument Revealed

My original claim is **partially strengthened but importantly transformed**.

**Strengthened:** Expert 2's strongest counter — that clinical outcomes provide external ground truth — is weaker than it appears. Sentinel events catch *catastrophic* failures (the acuity-4 patient who codes in the waiting room). They do not catch *systematic moderate under-triage* — the elderly patient assigned acuity 3 who should have been acuity 2, who waits 90 minutes longer, whose outcomes are slightly worse in aggregate but whose individual case never triggers a review. The feedback loop isn't about missing disasters; it's about normalizing suboptimal care in ways that remain below the threshold of individual detection.

**Transformed:** Expert 3 fundamentally reframed my claim. The deepest problem isn't epistemic closure *per se* — it's that **the deployment's structure conflates operational optimization with clinical judgment while systematically excluding the actors and information channels that would make the conflation visible.** The opacity isn't just the algorithm; it's the institutional design. Proprietary code, excluded nurses, liability transfer to the hospital, cost-savings framing — these aren't independent problems. They're a coherent structure that insulates the vendor from accountability and the administration from clinical reality.

**What I know now that I couldn't know before the argument:**

The most dangerous feature of this system is not that it will produce spectacular failures that get caught. It's that it will produce a *slight, persistent, statistically invisible degradation of care* for exactly the populations least equipped to advocate for themselves — elderly patients, children, unaccompanied individuals, non-English speakers — and that the deployment is structured so that this degradation registers as *success* (cost savings achieved, overall accuracy acceptable, no sentinel events). The system doesn't need to fail catastrophically to cause serious harm. It needs only to be *slightly, consistently wrong about the most vulnerable people,* in a structure where no one has both the information and the authority to see the pattern.
