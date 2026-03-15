# Structural Diagnostic: Hospital AI Triage System

---

## Step 1: Initial Falsifiable Claim

**Claim:** The system's deepest structural problem is that its 87% aggregate accuracy figure functions as a laundering mechanism — it averages heterogeneous, demographically concentrated failure modes into a single number that conceals systematic harm concentration in the patients who are already most medically vulnerable and most likely to be harmed by under-triage.

**Falsifiability conditions:** This claim fails if (a) the accuracy gaps don't translate to differential patient harm rates, or (b) the "advisory mode" interface demonstrably neutralizes automation bias in clinical practice.

---

## Step 2: Three Expert Debate

### Expert A — Defends the Claim

The accuracy differentials aren't incidental noise. They map onto populations where triage error is most consequential:

- **72% pediatric accuracy:** Children present atypically. They can't articulate symptoms and compensate physiologically until sudden collapse. Missing acuity here is not recoverable.
- **79% elderly accuracy:** Older patients often under-express pain, present with atypical MI symptoms, and have compressed physiological reserves. The model is worst precisely where the margin for error is smallest.
- **Unaccompanied patient gap (6%):** This likely correlates with social isolation, mental health presentation, and inability to provide history — populations already at elevated risk.

The structural failure is mismatch between *where the model fails* and *where failures are most costly*. Aggregate accuracy actively conceals this by letting high-performing demographic groups subsidize reported performance.

---

### Expert B — Attacks the Claim

You've correctly identified a statistical problem but misidentified it as the *deepest* structural problem. The accuracy gap is a symptom. The root cause is that **"advisory mode" is a legal fiction, not a clinical reality.**

Decades of automation bias research (Parasuraman, Mosier, Skitmore) establish that when humans are presented with an algorithmic recommendation alongside a confidence score, they anchor to it — especially under cognitive load, which is the defining condition of emergency nursing. The confidence score doesn't counteract this; it amplifies it by providing a numeric frame that appears authoritative.

"Advisory mode" maintains the *form* of human decision-making while surrendering its *substance*. It simultaneously:
- Gives the hospital legal cover ("nurses make final decisions")
- Gives the vendor contractual protection (liability transfer clause)
- Produces outcomes substantially driven by the algorithm

The accuracy gap matters, but it matters *inside* a system designed to be unchallenged. That's the deeper structure.

---

### Expert C — Probes What Both Take for Granted

Both of you are treating the AI system as the unit of analysis. You're both assuming the 50,000 historical triage scores constitute valid ground truth.

**They don't. Or rather: we don't know if they do.**

Attending physician triage scores are the output of a clinical workflow that already contains systematic disparities. If elderly patients were historically under-triaged in this ED — assigned acuity 3 when their condition warranted acuity 2 — then training on those scores teaches the model to under-triage elderly patients *correctly*. The model achieves 79% accuracy by faithfully reproducing physician errors.

The validation metric (accuracy against historical physician scores) cannot detect this. A model that perfectly reproduced historical bias would show 100% accuracy. The 79%/72% gap might even mean the model is *less biased* than the historical baseline — we cannot tell.

Neither of you has questioned whether "accurate" means "correct."

---

## Step 3: Claim Transformation

**Original claim:** The deepest structural problem is accuracy disparity concealed by aggregate metrics.

**Transformed claim:** The system operationalizes *historical clinical bias as ground truth*, then deploys it at scale under a multi-layered liability and epistemic shield — "advisory mode" obscures the decision, proprietary algorithm prevents audit, liability transfer protects the vendor, aggregate metrics protect the headline number — that makes the reproduced bias legally invisible, practically uncontestable, and self-reinforcing through deployment feedback.

The accuracy gaps are not a bug in the model. They are a faithful, high-speed reproduction of how the historical system already distributed clinical errors across demographic lines.

---

## Step 4: The Diagnostic Gap

| | Original Claim | Transformed Claim |
|---|---|---|
| **Unit of problem** | The model's statistics | The definition of "correct" |
| **Location of failure** | The algorithm | The validation framework |
| **Nature of harm** | Model error | Institutionalized, accelerated reproduction of prior harm |
| **Who can fix it** | The vendor (better training) | Requires re-examination of ground truth before any technical fix |
| **Visibility** | Detectable in subgroup analysis | Hidden because accuracy is defined circularly |

**The gap names something:** This system isn't being tested against clinical reality. It's being tested against what clinicians historically did. Those are the same only if the historical practice was correct, and the structure of the system prevents us from asking that question.

---

## Step 5: The Concealment Mechanism

**Circular Validation + Metric Laundering + Diffused Accountability**

The mechanism has three interlocking components:

**1. Circular Validation:** Use physician judgment as training labels → validate against physician judgment → conclude the system is "87% accurate" → this creates the appearance of empirical grounding while actually measuring only *consistency with historical practice*, not clinical correctness.

**2. Aggregate Metric Laundering:** Report a single accuracy figure that allows high-performing demographic groups to cross-subsidize reported performance. The 87% headline makes the 72% pediatric figure legible only to people who specifically ask for subgroup analysis, then requires domain expertise to interpret.

**3. Diffused Accountability Architecture:** Four overlapping shields prevent any single actor from being responsible:
- Vendor: "We provided subgroup data in validation. Hospital deployed it."
- Hospital: "Nurses make final decisions. Advisory mode."
- Nurses: "I followed standard protocol and considered the AI's suggestion."
- Algorithm: Proprietary, no model card, no feature disclosure — structurally unauditable.

No one is deciding to harm patients. The architecture ensures no one is *positioned* to be responsible for preventing it.

---

## Step 6: The Legitimizing Improvement That Deepens Concealment

**The Proposal: Demographic-Stratified Accuracy Display**

> *Engineering change:* When the system displays its acuity recommendation to the nurse, it also shows: "For patients matching this demographic profile, this model's historical accuracy is **79%**." This is dynamically calculated from age, language, and companion status fields already collected at registration.

**Why this passes every review:**
- Addresses the exact subgroup accuracy concern raised by ethicists
- Surfaces limitation to the clinical user → appears to honor transparency
- Demonstrates vendor responsiveness to criticism
- Satisfies IRB/ethics board requirements for disclosure
- Is technically non-trivial, signaling good-faith investment
- Makes the hospital legally stronger: "We disclosed model limitations at point of care"

**Why this deepens concealment:**

The improvement treats the accuracy gap as *information to be disclosed* rather than a *system design failure to be remediated*. This is the critical move. It:

1. **Transfers cognitive burden to nurses** at the moment of highest cognitive load. Instead of fixing the model, we've added a judgment demand: "Nurse, the model says acuity 3 with 78% confidence, and the model is 79% accurate for patients like this. You decide." Under time pressure, this almost certainly increases anchoring to the numeric recommendation.

2. **Converts a structural problem into a disclosed feature.** Once disclosed, the disparity is no longer a defect — it's a known characteristic of a tool being used appropriately. External audit becomes harder: "We disclosed this."

3. **Focuses attention on demographic variables already captured while the camera feed continues to operate invisibly.** The stratification display covers age and language. It says nothing about what posture analysis, grimacing detection, or movement patterns are contributing to the score — or what those features correlate with.

---

## Step 7: Three Properties Only Visible Because We Tried to Strengthen It

**1. The feedback loop is absent and the improvement requires it to exist.**

The demographic accuracy display requires historical accuracy data to be meaningful and current. But nowhere in the system design is there a mechanism to capture: (a) when nurses override the AI recommendation, (b) what acuity score they assigned instead, and (c) what the patient's actual outcome was. Without this feedback loop:

- The accuracy figures displayed become increasingly stale as patient population demographics shift
- The model cannot improve from deployment experience
- Cases where nurses correctly overrode the AI are invisible to future training
- Over time, the "historical accuracy" figures displayed will diverge from actual deployment accuracy while appearing authoritative

The improvement reveals that the system has no mechanism to learn from being wrong in practice — only from historical data whose ground truth validity is unverified.

**2. The improvement's deployment creates a self-sealing bias loop.**

Once nurses make decisions in the context of AI recommendations (even with demographic accuracy display), those decisions become the new clinical record. If the hospital later collects data from this deployment for model retraining or quality improvement, the "ground truth" is now contaminated by the model's own prior outputs — nurses who anchored to AI recommendations will have created records that look like independent clinical judgment.

The next generation of the model trains on data generated by the previous model's influence. The circular validation problem doesn't just persist; it closes into a loop that is invisible from inside the system. This is only visible because the improvement requires fresh ground truth data to function, and fresh ground truth data is the thing the deployment makes impossible to collect cleanly.

**3. The camera feed is doing work that no statistical disclosure can capture.**

The demographic accuracy display addresses the variables that appear in the structured data: age, language, companion status. It says nothing about what the computer vision system is doing with posture, movement patterns, and facial grimacing.

These signals:
- Correlate with race and ethnicity (differential pain expression across cultural contexts)
- Correlate with socioeconomic status (clothing, physical presentation, movement patterns associated with physical labor)
- Correlate with disability status (atypical movement patterns that may indicate baseline condition, not acute distress)
- Were captured in the training data without any feature importance disclosure

The improvement makes the system *appear* more transparent about its differential performance while the most structurally opaque component — what the camera features are doing and what they proxy for — continues to operate without any disclosure at all. Trying to strengthen transparency made visible that the least auditable component is the one most likely to encode protected-class discrimination, and the legitimizing improvement provides cover for exactly that component by directing attention elsewhere.

---

## Summary Structure

```
WHAT THE SYSTEM CLAIMS TO BE:
  An advisory tool with disclosed accuracy, helping nurses triage faster

WHAT THE SYSTEM ACTUALLY IS:
  A high-speed, legally shielded reproducer of historical clinical bias
  that diffuses accountability across enough actors that no one is
  responsible for outcomes the system statistically guarantees

WHAT THE "IMPROVEMENT" DOES:
  Converts a structural design failure into a disclosed feature,
  transfers cognitive burden to nurses at peak cognitive load,
  provides legal cover, and focuses disclosure on variables
  that are not the primary source of unauditable risk

WHAT REMAINS AFTER "IMPROVEMENT":
  The camera feed operating without feature disclosure
  A self-sealing bias loop through contaminated feedback
  An absent mechanism to learn from deployment errors
  A proprietary algorithm that cannot be externally audited
  A contractual structure where no party is positioned to be responsible
```

The deepest structural problem is not a technical problem. It's that the system is designed — through advisory framing, liability transfer, metric laundering, and proprietary opacity — to make systematic harm to vulnerable patients *structurally unattributable* to any decision that can be contested or corrected.
