# Generative Diagnostic: Hospital AI Triage System

## The Falsifiable Claim

**The system's deepest structural problem is not its bias, its opacity, or its accuracy gaps. It is that "advisory mode" is an autonomy-extraction mechanism disguised as a decision-support tool — it will progressively replace clinical triage judgment with a confirm/reject audit task, and every metric the hospital uses to evaluate the deployment is structurally incapable of detecting this transformation.**

This is falsifiable: measure whether, after 18 months, nurses' independent triage accuracy *without* the system degrades compared to baseline. If it doesn't, I'm wrong.

---

## Three Experts Stress-Test the Claim

### Expert A (Defends)

The claim holds because the deployment is rigged for dependency:

- The **confidence score** creates an illusion of calibrated uncertainty that invites deference — "92% confident, Level 3" feels like a second opinion from a precise colleague, not a compressed statistical approximation
- The **$2.1M savings from optimized staffing** means *fewer nurses per shift*, which means *more time pressure per decision*, which is the single strongest predictor of automation bias in clinical literature
- The **proprietary algorithm with no feature importance disclosure** means nurses *cannot learn the model's reasoning*, which means they cannot develop calibrated distrust — they can only globally trust or globally reject, and institutional pressure favors trust
- The system trains on **attending physician** scores but advises **nurses**, embedding an implicit authority gradient: the AI carries the compressed authority of 50,000 physician decisions

### Expert B (Attacks)

The claim overstates the risk:

- Emergency nurses are among the most autonomous clinical professionals; they routinely override physician orders when patient presentation warrants it
- "Advisory mode" CDS is standard practice (sepsis alerts, early warning scores) and decades of deployment show nurses maintain independent judgment
- The 87% accuracy may *exceed* inter-rater reliability among human triage nurses (literature shows ~60-80% agreement on ESI levels), so the "degradation" framing assumes a baseline that may not exist
- The claim about epistemic loop assumes model retraining on contaminated data, which isn't specified in the scenario

### Expert C (Probes What Both Take for Granted)

Both experts accept a shared frame that is itself the problem:

> "You're both debating whether nurses will appropriately override the AI — whether the human-in-the-loop will hold. But you've both accepted that triage is a classification task: map inputs to acuity levels 1-5. **Triage is not classification.** It is a temporally dynamic, embodied, relational clinical act. The nurse who watches a patient's gait deteriorate over twelve minutes, who notices the subtle flat affect that doesn't match the chief complaint, who recognizes that an unaccompanied elderly patient minimizing symptoms is a different clinical signal than the same vitals in a 30-year-old — that nurse isn't 'classifying.' She is reasoning through a situation. The moment you frame this as 'AI suggests Level 3, nurse confirms or overrides,' you've already destroyed the structure of the judgment you claim to support."

---

## The Transformed Claim

**The system doesn't risk degrading triage accuracy — it ontologically restructures triage from a situated clinical judgment into a confirmation task, and this restructuring is invisible to every evaluation framework available to the hospital, because those frameworks presuppose the classification ontology that the system imposes.**

### The Diagnostic Gap

My original claim stayed within the system's own frame (accuracy, bias, override rates). Only under adversarial pressure did the deeper problem emerge: **the frame itself is the weapon**. By accepting "accuracy against physician ground truth" as the success criterion, I initially couldn't see that the ground truth labels are themselves products of the relational, embodied reasoning that the system structurally cannot perform — and that the accuracy metric specifically rewards the system for compressing away the clinical richness it cannot represent.

---

## The Concealment Mechanism

**Agency Theater**: the deployment creates conspicuous tokens of human authority — the nurse "sees the suggestion," "makes their own decision," "has final say" — while systematically eroding the conditions under which genuine clinical judgment operates. Specifically:

| Visible Performance of Agency | Structural Erosion of Agency |
|---|---|
| Nurse sees AI suggestion *before* deciding | Anchoring bias makes independent assessment cognitively expensive |
| Confidence score shown for "calibration" | High-confidence wrong answers are the most dangerous *and* the hardest to override |
| "Advisory only" framing | Staffing cuts based on projected savings increase time pressure, increasing deference |
| Hospital retains "clinical decision" authority | Hospital lacks technical access to understand *what* it's being advised by |
| 87% accuracy validates deployment | Accuracy computed against labels from a judgment process the system is replacing |

The concealment is *structural*, not intentional. No single actor is hiding anything. The vendor genuinely believes in the product. The administration genuinely wants better care. The concealment emerges from the *architecture of relationships* between proprietary opacity, liability displacement, financial incentive, and metric selection.

---

## The Engineered Improvement (Passes Review, Deepens Concealment)

### Proposal: "Equity-Aware Override Dashboard with Structured Justification"

**Design:** When a nurse overrides the AI's triage suggestion, the system prompts for a structured justification (dropdown: clinical gestalt, vital sign trajectory, patient communication, family/companion input, other). Monthly reports aggregate override rates by patient demographics, correlate overrides with patient outcomes (admission, ICU transfer, 72-hour return), and flag sub-groups where override rates deviate from baseline.

**Why it passes review with enthusiasm:**
- Directly addresses the disclosed accuracy disparities across sub-groups
- Creates auditable equity data — responsive to any future regulatory inquiry
- Appears to respect and measure nursing expertise
- Generates exactly the kind of "human-in-the-loop monitoring" that AI ethics frameworks recommend
- Any IRB, patient safety committee, or accreditation body would commend it

**Why it deepens the concealment — structurally:**

1. **It encodes agreement as the default and disagreement as an event requiring justification.** Confirming the AI is frictionless. Overriding requires cognitive labor (selecting justification, knowing it's logged). This asymmetric friction is the most reliable known mechanism for amplifying automation bias. Over time, overrides become *remarkable* rather than *routine*, inverting the epistemic relationship: now the nurse must justify her judgment to the system's record, rather than the system justifying its suggestion to the nurse.

2. **The outcomes correlation will systematically vindicate the AI.** Atypical presentations — the cases most likely to be overridden — also have the most ambiguous "correct" triage levels and the most variable outcomes. Retrospective analysis will frequently show that the AI's original assignment was "defensible," creating a quantified narrative that overrides are noisy and often unnecessary. This narrative will appear in quarterly reports as evidence of AI reliability.

3. **The equity dashboard converts a structural problem into a monitoring problem.** Instead of asking "why does this system perform 15 percentage points worse for elderly patients?", the institution now asks "what are the override rates for elderly patients?" — a question that is answerable, actionable, and *completely misses the point*. The dashboard makes the disparity *legible* as a data management issue rather than a deployment ethics issue.

4. **It generates the exact documentation that insulates the hospital legally** while making it harder, not easier, to argue that the system should not have been deployed. "We monitored, we tracked equity metrics, we logged overrides" becomes the institutional defense.

---

## Three Properties Visible Only Because I Tried to Strengthen the Concealment

**Property 1: The monitoring infrastructure can only see what the AI makes legible.**

By designing the override dashboard, I discovered that every monitoring system built on the confirm/override binary inherits the AI's classification ontology. The dashboard can track *whether* nurses disagree with the AI's level assignment. It *cannot* surface the clinical reasoning that never gets expressed — the nurse who *would have* noticed the subtle neurological deterioration but didn't perform that assessment because the AI already confidently assigned Level 4, the waiting room camera that captured 20 minutes of progressive gait instability but compressed it into a movement feature vector that lacked clinical semantics. **The most dangerous failures are the assessments that never happen because the system's confident output forecloses the clinical question that would have prompted them.** No override logging system can capture the absence of a question that was never asked.

**Property 2: The power asymmetry is encoded in the information architecture, not in any individual decision.**

When I tried to design "better oversight," I found that every design preserved the same asymmetry: the vendor holds the model, the hospital holds the outcomes, the nurses hold the override liability, and the patients hold nothing. The override dashboard would give the hospital *more* data about nurse behavior and *zero* additional data about model behavior. It makes nursing judgment more legible to institutional scrutiny while the algorithm remains opaque. The "improvement" strengthens surveillance of the human while deepening opacity of the machine. This asymmetry is not a bug in the deployment — it is the business model. The proprietary clause and the liability clause are not independent contract terms; they are two halves of a single epistemic architecture that ensures the vendor's product can never be independently shown to have caused harm.

**Property 3: "Reduced over-triage" and "optimized staffing" are euphemisms for rationing whose distributional consequences are hidden by the accuracy metric.**

The $2.1M savings require that some patients who would have been triaged to higher acuity (seen faster, more resources) are now triaged lower. "Reduced over-triage" *means* this. The populations bearing this cost are precisely those with the lowest accuracy: pediatric patients (72%), elderly patients (79%), unaccompanied patients (-6%), non-English speakers (-4%). The intersectional burden — an unaccompanied, elderly, non-English-speaking patient — likely faces accuracy far below any reported sub-group figure. By building the equity dashboard, I saw clearly that the dashboard would report these sub-groups as separate rows in a table, never surfacing the *intersectional* patient who exists at the convergence of all risk factors. **The system saves money by undertriaging the most vulnerable, and the monitoring system I designed would make this rationing appear as equity-conscious quality improvement.**

---

## Summary Diagnostic

The code — using "code" in the architectural sense — hides its real problem behind a three-layer concealment:

- **Layer 1 (visible):** Accuracy disparities across sub-groups → addressable with "more data" and "bias mitigation"
- **Layer 2 (partially visible):** Automation bias and liability displacement → addressable with "better human-in-the-loop design"
- **Layer 3 (structurally concealed):** The deployment ontologically transforms triage from clinical judgment into classification confirmation, and every "improvement" to layers 1 and 2 deepens this transformation by further encoding the classification frame as the only legible description of what triage is

The deepest problem is not a property of the AI system. It is a property of the *gap* between what triage actually is and what the system requires triage to become — and that gap is invisible from inside any framework that accepts the system's own description of what it does.
