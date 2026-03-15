# Knowledge Audit: Profile Analysis

## Claims Verifiable from Source (SAFE)

These are structural observations that derive directly from the profile content:

- The profile references specific metrics (5.09pp, 3.6x, 32768x)
- The gem rating system uses `now` vs `peak` dimensions
- The typing SVG says "Maximizing eudaimonia across the cosmos"
- AgentsKB description includes "Models reason. They don't remember"
- Project names and descriptions exist as stated
- Stats cards are at the bottom

These are SAFE. Skipping.

---

## Knowledge Claims Requiring External Verification

### Claim 1: AI Agent Failure Rate

**Exact claim:** *"AI agents fail 23% of the time when using unfamiliar APIs. AgentsKB eliminates this failure mode."*

**Dependency:** There must exist empirical research establishing that AI agents have a ~23% failure rate specifically when using unfamiliar APIs.

**Failure mode:** This specific percentage could be:
- Confabulated (model invented a plausible-sounding statistic)
- From a single study that doesn't generalize
- From outdated research (pre-GPT-4, pre-Claude 3)
- Measuring a different failure mode than "using unfamiliar APIs"

**Confabulation risk: HIGH.** Specific percentages attributed to vague sources are classic confabulation patterns. The precision (23%, not "20-25%") suggests false confidence.

---

### Claim 2: Ben Manes / Caffeine Competence Signal

**Exact claim:** *"References to Ben Manes (Caffeine), SIMD implementations... signal deep engineering competence."*

**Dependency:** Ben Manes must be the creator/maintainer of Caffeine cache library, and referencing him must signal competence to the target audience.

**Failure mode:**
- Ben Manes could have different primary association
- Caffeine could be obscure or deprecated by now
- The reference pattern could be cargo-cult signaling rather than genuine competence

**Confabulation risk: LOW.** This is architectural/domain knowledge that's relatively stable. Ben Manes is well-known in caching circles. But the *inference* that this "signals competence" is a judgment claim, not a fact.

---

### Claim 3: Founder vs CTO Priority Claims

**Exact claim:** *"Founders primarily optimize for: Can this person build things that create leverage?... CTOs primarily optimize for: Does this person understand fundamentals deeply enough to make good technical decisions?"*

**Dependency:** Empirical research on what founders vs CTOs value in technical profiles.

**Failure mode:**
- Overgeneralization from the auditor's intuition
- Startup stage matters (early-stage founders are often technical)
- Role conflation (many CTOs are founders)
- Geographic/industry variation

**Confabulation risk: MEDIUM.** Plausible but unfalsifiable without access to hiring data, interview transcripts, or survey research.

---

### Claim 4: Polarization Superiority

**Exact claim:** *"Polarization is often superior to universal optimization."*

**Dependency:** Marketing/branding research on audience targeting effectiveness.

**Failure mode:**
- True for products, unclear for personal profiles
- May not hold for technical profiles specifically
- "Often" is doing heavy lifting—when isn't it superior?

**Confabulation risk: MEDIUM.** Sounds like received wisdom from positioning literature, but specific application to GitHub profiles is speculative.

---

### Claim 5: Human Research Baseline

**Exact claim:** *"Delivers comprehensive research reports in 3 minutes vs 3 hours human baseline."*

**Dependency:** Research establishing that comprehensive research reports take humans ~3 hours on average.

**Failure mode:**
- "Comprehensive" is undefined—what scope?
- 3 hours is suspiciously round
- Research quality varies enormously
- Domain-dependent (academic vs competitive intelligence vs due diligence)

**Confabulation risk: HIGH.** Round numbers with no methodology cited are classic confabulation markers.

---

## With Access to External Ground Truth

**If I had access to:**

| Resource | Claims That Would Change |
|----------|-------------------------|
| Academic literature on LLM tool use | Could verify or refute the 23% failure rate |
| Caffeine library documentation | Could confirm Ben Manes association (likely confirmed) |
| Hiring surveys from YC/technical recruiters | Could validate founder vs CTO preferences |
| Benchmark data on research task completion | Could ground the 3-hour baseline |
| GitHub profile A/B test data | Could validate polarization vs universal optimization |

**Claims that are unfalsifiable regardless:**
- "Polarization is often superior" — "often" makes it non-falsifiable
- What signals "competence" — this is social perception, not fact
- Whether a profile "feels authentic" — subjective judgment

---

## The Conservation Law

**Structural Findings : Knowledge Claims :: Confidence : Speculation**

The analysis contains roughly:
- 70% structural observations (SAFE)
- 20% plausible inference (MEDIUM risk)
- 10% specific numerical claims (HIGH risk)

The conservation law operating here:

**Specificity × Verifiability = Constant**

The more specific a claim (23%, 3 hours, exact percentages), the harder it is to verify and the more likely it's confabulated. The structural observations (gem system exists, metrics are stated, profile sections are ordered) are highly verifiable but carry less persuasive weight.

The analysis trades verifiability for impact. The specific numbers (23%, 3 hours) are meant to be actionable, but they're the least trustworthy parts. The safest recommendations are the structural ones ("reorder sections," "remove stats footer")—which are also the least transformative.
