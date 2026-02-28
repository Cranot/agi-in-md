# Structure First: Diagnostic Gap Analysis

## The Initial Claim

**The deepest structural problem is corrupted ground truth.**

The system uses historical physician triage scores as its benchmark for "correct" triage. This means it learns — with mathematical precision — to replicate patterns that include whatever racial, age-based, gender-based, and class-based disparities existed in historical ED practice. The 87% accuracy figure doesn't measure whether the AI triages patients correctly. It measures whether the AI reproduces what physicians historically did. These are not the same claim, and treating them as equivalent is falsifiable: if you validate against *outcomes* (deterioration, admission, mortality) rather than historical physician scores, the accuracy picture will look materially different — and the subgroup gaps will likely widen or shift in distribution.

---

## The Three-Expert Dialectic

### Expert 1 (Defender): Ground truth contamination is central and mechanistically specific

The sub-group accuracy gaps are exactly what corrupted ground truth predicts. The system achieves 91% accuracy for 20-50 year-olds because that cohort dominated the training data and historical physician behavior was most standardized for them. It achieves 72% for pediatrics because pediatric presentation is physiologically distinctive *and* historical physician behavior for children was more variable, more contested, and more prone to systematic error. The AI hasn't independently discovered a hard clinical problem — it has faithfully encoded the human inconsistency already present in the data.

The falsifiable prediction: if you pull outcome data for the 13% of cases the AI gets "wrong" for adults 20-50 versus the 28% it gets wrong for pediatric cases, you will find the *types* of errors differ qualitatively, not just quantitatively. Adult errors will cluster around unusual presentations. Pediatric errors will be more systematically distributed — because pediatric physician judgment in the training set was itself less reliable.

### Expert 2 (Attacker): Ground truth contamination is real but not the deepest problem — advisory mode is

The deeper structural failure is the deployment architecture. "Advisory mode with confidence scores" is a known cognitive trap, not a safety buffer. When a system presents a recommendation with a confidence percentage before a clinician makes a judgment, anchoring bias does not politely step aside. The nurse is no longer making an independent triage assessment — they are performing *confirmation or override* of a machine suggestion. These are cognitively distinct operations with very different error profiles.

This matters structurally because the liability clause in the vendor contract makes explicit what advisory mode obscures: the hospital assumes full liability for "clinical decisions" made by nurses who are cognitively anchored to an opaque algorithm they cannot interrogate. Advisory mode creates the legal form of human oversight while systematically undermining its substance. The ground truth contamination critic is looking at the training phase. The real leverage point is the moment a nurse sees that confidence score and what it does to their cognitive process.

### Expert 3 (Probing what both take for granted): Both assume the system is trying to maximize clinical accuracy

Both arguments take for granted that this system's *operational* purpose is triage quality. But the explicit framing from administration is $2.1M in savings from "optimized staffing and reduced over-triage."

This should stop the conversation cold. Over-triage — assigning higher acuity than strictly necessary — is the direction of error that costs money. The system is being evaluated on accuracy, but accuracy is symmetric around an asymmetric objective. If the system's deployment is financially rewarded for under-triage and financially penalized for over-triage, then accuracy metrics tell you almost nothing about the system's operational behavior. What matters is: **in which direction does the system err, at what rate, and for which populations?**

Neither expert asked this. The subgroup accuracy figures (79% for elderly, 72% for pediatric) tell you that the system is less accurate for these groups. They tell you nothing about whether the errors are over-triage or under-triage. In a system under institutional pressure to reduce over-triage, you should expect errors to be directionally biased toward under-triage — and you should expect that bias to be concentrated in exactly the populations where the system is least accurate and where the consequences of under-triage are most severe.

---

## The Transformation and the Gap

**Original claim:** The problem is corrupted ground truth producing inherited bias.

**Transformed claim:** Ground truth corruption + advisory mode cognitive capture + directional error incentives create an institutional architecture that is structurally likely to systematically under-triage the most vulnerable patient populations, while distributing liability downward to nurses and providing institutional cover through the appearance of rigorous validation.

The gap is substantial. The original claim is about *data quality in the training phase*. The transformed claim is about *institutional design that converts predictable bias into financial benefit* while constructing deniability. That is not a refinement — it is a category shift from a technical problem to a governance problem.

---

## The Concealment Mechanism: Quantitative Disclosure as Epistemic Foreclosure

The gap reveals a specific concealment mechanism I'll call **accuracy theater** — the deployment of real, disclosed, technically accurate numbers that structurally prevent the more important questions from being asked.

Here is how it operates:

The subgroup analysis is presented as evidence of rigor and transparency. The hospital can say: "We found disparities, we disclosed them, we are monitoring them." This is true. But the accuracy figures were chosen to answer the question *"how accurate is the system?"* — and by answering that question with numbers, they crowd out the questions that matter:

- *In which direction* are errors distributed, and for which populations?
- What does accuracy mean when the benchmark is itself corrupt?
- What accuracy would we find against outcome data rather than historical physician scores?
- What does a 6% accuracy gap for unaccompanied patients mean for a patient who arrives alone, elderly, and non-English-speaking simultaneously (compounding gaps)?

The subgroup breakdown creates the appearance of thorough interrogation while selecting exactly the variables that are already documented in the literature (age, language) and omitting the variables that would reveal institutional incentive alignment (error direction × financial pressure × population vulnerability).

The mechanism is not deception in the naive sense. The numbers are real. The disclosure is genuine. The concealment operates by *answering a question thoroughly enough to make further questions seem unnecessary.*

---

## What the Entire Dialectic Failed to Surface

Every argument above — including the synthesis — operates within a shared assumption: that this system is attempting to extract a coherent medical signal called "acuity level," imperfectly, with quantifiable error rates.

**This assumption is wrong, and the camera feeds are what reveal it.**

The system uses "waiting room camera feeds (posture, movement patterns, facial grimacing)" as input. This is not a supplementary data source. It is a fundamentally different epistemic operation than measuring vitals or parsing a chief complaint — and that difference has been invisible throughout the entire dialectic.

Here is the structural problem the cameras introduce:

**The system doesn't model medical acuity. It models social performance of distress, then labels that performance as acuity.**

Waiting room behavior is not a proxy for acuity. It is a proxy for *how a patient expresses distress in a public institutional space while waiting, given their cultural background, social context, pain tolerance norms, whether they are accompanied, whether they are fearful of medical settings, whether they are cognitively impaired, and dozens of other factors orthogonal to their actual physiological state.*

This matters structurally in ways the dialectic completely missed:

**1. The 6% accuracy gap for unaccompanied patients is now legible as something different.** Unaccompanied patients display distress differently in public spaces. They have no one coaching them on how to signal need. They may be more or less expressive depending on cultural norms about public vulnerability. The camera doesn't see this as noise — it reads it as signal about acuity. Unaccompanied patients aren't harder to triage medically. They are harder to triage for a system that reads social presentation as clinical data.

**2. The camera input makes the system permanently unauditable.** A nurse can interrogate a chief complaint. A nurse can check vitals against clinical intuition. A nurse cannot know what the camera saw and how it weighted what it saw — especially given the proprietary algorithm clause. Advisory mode anchoring doesn't just affect the nurse's judgment; it anchors the nurse to a recommendation that is partly derived from an unexaminable visual interpretation of how the patient sat in a waiting room. This is not a quantifiable confidence score problem. It is a fundamental illegibility problem.

**3. The training data problem is worse than the ground truth contamination argument suggests.** The 50,000 historical visits used as ground truth did not include camera data. The camera inputs are being mapped onto historical acuity labels from a world where no one was watching how patients sat. The system is learning correlations between waiting room behavior and acuity labels that were generated *without observing* that behavior. This is not ground truth contamination — this is a feature-label mismatch at the architectural level.

**4. The population harmed is invisible in the subgroup analysis.** The groups identified — elderly, pediatric, unaccompanied, non-English — are identifiable because they appear in structured metadata. But the population most systematically harmed by camera-based inference is patients whose legitimate medical distress is expressed through behavioral patterns underrepresented in the training distribution — stoic patients, patients with high pain tolerance, patients from cultures where public display of suffering violates norms, patients who are dissociating, patients who are frightened into stillness. These patients don't appear as a subgroup in the accuracy report because you cannot identify them without knowing what the camera captured, which is proprietary.

---

## Final Structural Diagnosis

The system's deepest problem is not bias, or advisory mode anchoring, or corrupted ground truth, or financial misalignment with clinical purpose — though all of these are real and serious.

The deepest problem is that the system treats **social legibility of distress** as a valid proxy for **medical acuity**, without acknowledging that it has done so, without subjecting that assumption to scrutiny, and without disclosing it to the nurses whose clinical judgment it is now shaping.

The concealment mechanism — quantitative disclosure as epistemic foreclosure — functions precisely to prevent this recognition. The accuracy numbers give you something real to argue about. The subgroup analysis gives you a framework for concern that stays within acceptable parameters. The advisory mode framing gives you a theory of human oversight that feels coherent.

All of it prevents the question: *what, exactly, is this system measuring?*

And the answer to that question — it is measuring how much patients look like they should be sick, in a waiting room, to a camera, in a health system under financial pressure to reduce over-triage — is the thing the entire architecture is designed not to say out loud.
