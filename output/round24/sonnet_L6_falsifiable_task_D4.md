# Structure First: Falsifiable Hypothesis on a Hospital AI Triage System

---

## The Claim

**Falsifiable Hypothesis:** The deepest structural problem is that this system's accuracy metrics are epistemically self-sealing — they measure agreement with historical physician judgment rather than patient outcomes, making it technically impossible to distinguish between clinical accuracy and bias amplification. Consequently, the subgroup disparities (79% elderly, 72% pediatric, 6% gap for unaccompanied patients) cannot be interpreted as failures: they may represent the AI *faithfully learning* how these populations were historically undertriaged, which would mean the validation process is measuring the wrong thing entirely.

**Falsifiability condition:** If researchers compared AI predictions against objective outcome metrics — actual clinical severity classifications, intervention requirements, length of stay, adverse events within 24 hours — and the subgroup accuracy gaps narrowed significantly, the claim is strengthened. If gaps persist or worsen against outcome data, the claim is weakened. If gaps shift direction (the AI *over*-triages elderly patients relative to outcomes), the claim is transformed.

---

## Three Independent Experts

---

### Expert 1: The Defender
*"The ground truth problem is real, and it's structural all the way down."*

The claim is correct, and the implications are more serious than they first appear.

Attending physician triage scores are not neutral clinical facts. They are themselves the product of a cognitive process operating under time pressure, implicit bias, and historically unequal clinical training. The literature on age bias in emergency medicine documents systematic atypical presentation in elderly patients — sepsis without fever, MI without chest pain, abdominal catastrophe without peritoneal signs — which physicians routinely miss at higher rates than in younger adults. Pediatric emergency triage has well-documented anchoring problems around pain expression norms. Patients presenting without companions receive less information from collateral history, which plausibly causes physicians to assign *lower* acuity from incomplete data.

If the training data encodes these patterns, the model has not learned triage — it has learned to approximate physician behavior, including its systematic errors. The 79% and 72% accuracy figures don't tell us the AI is failing these populations; they tell us the AI diverges from physician scores for these populations. The gap could mean the AI is *correcting* for physician bias, or the AI is *amplifying* it. **The validation methodology cannot distinguish these cases.**

This matters structurally because all other safeguards in the deployment depend on the assumption that AI deviations from physician judgment represent AI errors that humans should correct. If some deviations are AI *improvements* that get corrected away by automation-biased nurses, the advisory mode becomes a mechanism for laundering historical bias back into clinical decisions with the appearance of dual human-AI validation. The camera feeds introducing posture and grimacing data add an additional layer: these signals are culturally mediated (stoicism varies by culture, age, pain presentation by condition), and if physicians historically undertriaged stoic presenters, the model will learn to do the same, now with the apparent objectivity of computer vision.

**What would falsify this:** Show me comparative outcomes data. If AI-triaged patients in the 70+ cohort have similar adverse event rates to AI-triaged 20-50 patients, the model may be doing something right even where it diverges from physician scores.

---

### Expert 2: The Attacker
*"The measurement problem is real but not the deepest problem. The advisory mode architecture is."*

The hypothesis is correct about the measurement problem but wrong about its structural depth. What makes a problem "deepest" isn't its abstractness or epistemic elegance — it's its causal proximity to harm. And the most causally proximate structural problem here is the advisory mode deployment architecture, which is designed in a way that systematically eliminates meaningful human oversight while maintaining its appearance.

The behavioral science literature on automation bias is not ambiguous. Studies across aviation, radiology, and clinical decision support consistently show that humans presented with an algorithmic recommendation before making their own assessment converge toward that recommendation at rates far above chance — especially under time pressure, high cognitive load, and when the system displays a confidence score. Emergency departments are precisely the environment where all three conditions are maximized. When a nurse sees "Level 3 — 74% confidence" before evaluating a patient, the nurse is not exercising independent judgment that checks the AI; they are post-hoc rationalizing the AI's output with the bureaucratic appearance of human sign-off.

The advisory mode framing is therefore not a safety feature. It's liability architecture. It creates a paper trail showing a human made the final decision while structurally ensuring that decision is predictably biased toward the AI's output. The $2.1M savings projection makes this explicit: savings come from "reduced over-triage," which means the system's economic function is to move patients *down* acuity levels. The advisory mode ensures this happens while attributing the decision to nursing judgment.

**The claim about ground truth takes for granted** that the accuracy measurement problem is what generates harm. But even with perfect outcome-calibrated ground truth, this advisory mode architecture in this staffing-savings context would produce systematic undertriage through automation bias. You can fix the measurement problem entirely and still deploy a dangerous system.

**What would falsify the claim that advisory mode is the deepest problem:** Show me a hospital where advisory mode AI was deployed with outcome-calibrated validation and produced no systematic undertriage bias in high-volume, time-pressured conditions. That evidence doesn't currently exist.

---

### Expert 3: The Probe
*"Both arguments take for granted that this is a technical problem with a technical solution. What's actually being assumed?"*

The defender and the attacker are arguing about *which technical flaw is deepest* — measurement validity or behavioral architecture. Both arguments assume the question is: "How could this system be deployed responsibly?" Neither asks whether the governance structure that produced this scenario can support responsible deployment at all.

Notice what's not being analyzed:

**The camera surveillance component** processes patient images without documented consent. Patients in emergency situations are not in a position to consent meaningfully to being analyzed by computer vision systems assessing their grimacing and posture. This isn't a feature of the system that can be fixed with better model cards — it's a categorical violation of informational self-determination that precedes any discussion of accuracy.

**The liability clause** is not boilerplate. It's a designed feature that eliminates vendor accountability for system errors. The vendor has no financial stake in accuracy because they've successfully transferred all clinical liability to the hospital. This creates perverse incentives: the vendor optimizes for appearing to work (high aggregate accuracy, 87% overall) while systematic harm in subgroups becomes the hospital's legal and financial problem. The opacity clause (no model card, no feature importance) compounds this: the hospital cannot audit what the system is actually doing, which means they cannot identify systematic errors, which means they cannot discharge their newly-assumed liability responsibly.

**The nurses' union exclusion** is taken for granted as an oversight — a consultation that should have happened. But it's actually a diagnostic: nurses are the people who would notice when the system fails. They are the most densely informed about edge cases, atypical presentations, and gaps between algorithmic prediction and clinical reality. Excluding them from deployment design means the primary feedback mechanism for identifying errors has been structurally disabled before deployment begins.

**What both arguments take for granted** is that harm is something that will happen in the future when the system is deployed, which good design can prevent. What neither examines is that harm is *already* structurally embedded in the institutional relationships: a vendor with no accountability, a hospital with assumed liability and no audit rights, patients under surveillance without consent, and workers whose expertise has been formally excluded. These aren't technical problems. They're governance failures that ensure technical problems will be invisible and unaddressable when they occur.

**The deepest assumption in the original claim**: that "deepest structural problem" refers to something inside the system. But structural problems can be outside the system — in the contracts, the consultation processes, the accountability architecture — and these are harder to fix precisely because they're not technical.

---

## Synthesis: What the Argument Did to the Claim

### Was the claim falsified, strengthened, or transformed?

**Transformed** — significantly.

The original claim was correct about the measurement problem but located it wrongly as the *deepest* problem. The Expert 2 attack revealed that even perfect measurement can coexist with harmful deployment architecture. The Expert 3 probe revealed that both the measurement and architecture problems assume a level of institutional accountability that doesn't exist in this contract structure.

**What the argument revealed:**

The deepest structural problem is not epistemic (wrong ground truth) or behavioral (automation bias) — it is **the accountability void that makes both of these problems invisible and unaddressable after deployment begins**. Specifically:

1. Proprietary opacity + liability transfer = the hospital cannot identify what the system is doing, and the vendor has no incentive to help them
2. Advisory mode + automation bias = systematic errors appear as nurse decisions, not system failures
3. No union consultation = the people most likely to notice failures have been excluded from the feedback loop
4. Surveillance without consent = a category of harm that exists regardless of accuracy
5. Outcome metrics absent from validation = no way to know whether improving accuracy means improving care

The ground truth problem matters *because* this accountability architecture ensures it will never be detected. If you fixed the ground truth problem alone, the system could still produce systematic undertriage through automation bias, and that undertriage would still be invisible because it would appear as nursing decisions. If you fixed the advisory mode architecture alone, nurses exercising independent judgment would still be judging against a model trained on potentially biased historical data.

### What do I know now that I couldn't know before the argument?

**That "deepest structural problem" in AI deployment is almost never inside the model.** The ground truth problem is a model problem with governance implications. The advisory mode problem is an architecture problem with behavioral implications. But the actual deepest problem is the set of institutional relationships — contracts, liability structures, consultation processes, audit rights — that determine whether any of the technical and behavioral problems can be *seen* and *corrected* once deployment begins.

The hospital is not deploying an AI system. It is deploying an accountability structure in which:
- Errors are attributed to humans (advisory mode)
- Liability is held by the institution without audit rights (vendor contract)
- Feedback from the most informed observers is structurally absent (no union consultation)
- Patient data is processed without meaningful consent (camera surveillance)
- Savings are the primary success metric, creating systematic pressure toward lower acuity assignments

The AI accuracy numbers are almost beside the point. A system with 95% accuracy deployed in this accountability structure would still be dangerous — because the 5% of errors would be invisible, unattributable, and unaddressable by design.

---

## Operational Implications

| Problem Layer | What's Required | What's Present |
|---|---|---|
| Ground truth validity | Outcome-calibrated validation data | Agreement with physician scores only |
| Subgroup performance | Minimum accuracy thresholds by population | Aggregate metric with subgroup disparities acknowledged but no thresholds |
| Automation bias | Blinded assessment before AI display, or AI shown after nurse assessment | AI + confidence shown first |
| Accountability | Vendor liability for model failures, audit rights, model card | Liability transferred, proprietary black box |
| Consent | Patient-facing disclosure for camera surveillance | Unaddressed |
| Feedback loops | Clinical staff as error-detection partners | Union excluded pre-deployment |
| Success metrics | Patient outcome improvement | Cost savings ($2.1M) |

The advisory mode is not a safety feature. It is a liability feature. The difference matters enormously for how to evaluate whether this deployment should proceed.
