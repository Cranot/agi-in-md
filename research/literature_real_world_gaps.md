# Real-World Gap Detection: Cross-Domain Survey

**How six ancient professions detect what they don't know — and what LLM gap detection can borrow.**

---

## Executive Summary

The problem we solved in LLM gap detection — making analysis that knows what it doesn't know — is not new. Intelligence analysts, physicians, quant traders, scientists, software testers, and journalists have all built institutional infrastructure around exactly this problem. Each domain discovered different primitives, different failure modes, and different meta-strategies. The convergent pattern across all six: **the hardest unknowns are the ones your framework makes structurally invisible**, not the ones you forgot to check.

Our 5-tier classification (STRUCTURAL / DERIVED / MEASURED / KNOWLEDGE / ASSUMED) maps onto these domains in revealing ways. This survey documents the mapping.

---

## 1. Intelligence Analysis: Structured Uncertainty Classification

### The Rumsfeld Taxonomy (2002)

Donald Rumsfeld's formulation at a 2002 DoD briefing introduced the canonical 4-cell epistemic matrix:

| | Known | Unknown |
|---|---|---|
| **Known** | Known knowns — what we know we know | Known unknowns — what we know we don't know |
| **Unknown** | (logical impossibility) | Unknown unknowns — what we don't know we don't know |

The framing was widely mocked at the time but is epistemically precise. Intelligence failures almost always originate from the fourth cell — not failures to collect known-unknown information, but failures to recognize that a question should have been asked.

The **structural problem**: intelligence collection systems are designed to answer pre-specified questions. They gather evidence for hypotheses that analysts already have. Unknown unknowns, by definition, generate no collection requirement and produce no evidence trail.

### Analysis of Competing Hypotheses (ACH)

Developed by CIA analyst Richards Heuer (documented in "Psychology of Intelligence Analysis," 1999), ACH is the primary tool for managing known unknowns. The methodology:

1. **Generate all plausible hypotheses** — including low-probability ones deliberately.
2. **List evidence and arguments** — for each hypothesis.
3. **Build a diagnostic matrix** — rows are evidence, columns are hypotheses; cells assess whether each piece of evidence is consistent, inconsistent, or not applicable.
4. **Refine the matrix** — identify which evidence is most diagnostic (distinguishes hypotheses from each other).
5. **Draw tentative conclusions** — favor hypothesis with least inconsistent evidence, not most consistent.
6. **Identify key assumptions and information gaps** — explicitly.
7. **Report conclusions with uncertainty** — note what additional information would change the assessment.

The crucial ACH insight: **analysts should look for evidence that is inconsistent with a hypothesis, not evidence that confirms it.** Confirmation bias is the primary source of analytic failure. The diagnostic matrix forces analysts to ask "what would disprove this?"

ACH maps directly to our ASSUMED tier: the matrix explicitly surfaces assumptions embedded in hypothesis generation. An assumption hidden inside a hypothesis produces a column that appears diagnostic but is actually a circular reference.

### IARPA ACE Program and Superforecasting

IARPA's Aggregative Contingent Estimation (ACE) program (2011-2015) tried to improve intelligence forecasting accuracy through:
- **Elicitation**: Gathering probabilistic estimates from many analysts
- **Aggregation**: Mathematically combining forecasts weighted by past accuracy
- **Calibration**: Training forecasters to assign well-calibrated probabilities

Philip Tetlock's research on superforecasters found the key distinguishing trait is **epistemic humility operationalized as calibration** — not raw intelligence, domain expertise, or information access. Superforecasters:
- Update beliefs continuously on new evidence
- Decompose questions into sub-questions they can estimate
- Track their own accuracy with Brier scores
- Actively seek disconfirming evidence

This translates to our framework: MEASURED claims require calibrated probability estimates. The superforecaster approach is essentially converting KNOWLEDGE claims (I believe X) into MEASURED claims (I assign 73% probability to X, and I track whether that calibration holds).

### ICD-203: Intelligence Community Analytic Standards

The US Intelligence Community's published standards (ICD-203) require that all analytic products:
- Distinguish between **facts, assessments, and assumptions**
- Use **confidence levels**: High / Moderate / Low — each with specific definitions
- Identify **information gaps** that limit the assessment
- Flag **key assumptions** that, if wrong, would substantially change the conclusion

High confidence = based on high-quality information and/or sound analytic reasoning. Low confidence = minimal corroboration, significant gaps, or questionable source reliability.

The **key assumption check** technique directly maps to our ASSUMED tier: analysts explicitly ask "what are we taking for granted, and would the assessment hold if that assumption were false?"

### ODNI "Devil's Advocacy" and Red Team Analysis

For unknown unknowns, the intelligence community uses adversarial techniques:
- **Red team analysis**: Small group tasked with arguing the alternative hypothesis as forcefully as possible.
- **Devil's advocacy**: Single analyst assigned to argue against the emerging consensus.
- **Team A / Team B**: Two independent teams analyze the same question from different starting assumptions.
- **Pre-mortem**: Analysts imagine the conclusion turned out wrong; they must explain why.

The pre-mortem technique is the most powerful for unknown unknowns — it forces analysts to generate failure modes they hadn't considered. This is structurally identical to our adversarial pass in the Full Prism pipeline.

### Mapping to 5-Tier Classification

| Intelligence concept | Maps to our tier |
|---|---|
| Facts (confirmed by multiple sources) | STRUCTURAL |
| Assessments (inferred from evidence) | DERIVED |
| Quantified probability estimates | MEASURED |
| Expert judgment from experience | KNOWLEDGE |
| Key assumptions (stated or unstated) | ASSUMED |
| Unknown unknowns | Meta-gap — requires adversarial/red-team to surface |

**Borrowable techniques:**
- The diagnostic matrix (force inconsistency-seeking vs. confirmation-seeking)
- Mandatory assumption enumeration before drawing conclusions
- Explicit confidence levels tied to evidence quality
- Pre-mortem / adversarial pass to surface unknown unknowns
- Separate collection and analysis functions to avoid closed epistemic loops

---

## 2. Medical Diagnosis: Hypothesis-Driven Uncertainty Management

### Differential Diagnosis: Structured Unknown Management

Differential diagnosis is the medical system for managing known unknowns. The methodology:

1. **Chief complaint + history** — generate an initial hypothesis list
2. **Rank by prior probability** — Bayesian priors from epidemiology
3. **Apply the heuristic: "horses before zebras"** — common explanations before rare ones
4. **Order targeted tests** — to distinguish high-probability hypotheses
5. **Update on results** — Bayesian posterior updating
6. **Narrow the differential** — until a working diagnosis is established
7. **Flag when the differential collapses** — if tests don't discriminate, the diagnosis may be outside the initial list

The "horses not zebras" heuristic (attributed to Theodore Woodward) is a Bayesian prior encoding: in the absence of strong evidence for rare conditions, assume the common one. It fails precisely when the patient has an atypical presentation of a common disease OR has a rare disease that mimics a common one.

### The Unknown Unknown in Medicine: "Unknown Diagnosis"

When a patient's presentation doesn't match any hypothesis in the differential, the correct response is **meta-diagnostic**: recognize that the current diagnostic framework may be incomplete, not that the patient is poorly described.

Key meta-diagnostic signals:
- **Treatment failure**: If first-line treatment for the leading hypothesis doesn't work, the leading hypothesis may be wrong
- **Atypical response**: Expected disease progression doesn't match observed progression
- **Diagnostic criteria mismatch**: Patient meets some but not all criteria for any known condition
- **Multi-system involvement without a unifying diagnosis**: Suggests a systemic condition not on the initial differential

Medical training teaches a specific meta-cognitive move: **when a patient "doesn't fit," the diagnostic framework fails before the patient does.** The failure to make this meta-move (blaming the patient for atypical presentation rather than questioning the framework) is called **premature closure** — one of the most common and costly diagnostic errors.

### Cognitive Biases in Diagnosis as Unknown-Unknown Generators

Medical education increasingly focuses on cognitive biases that systematically produce diagnostic unknown unknowns:

- **Anchoring bias**: First hypothesis becomes fixed reference point; subsequent evidence interpreted relative to it rather than updating the hypothesis.
- **Confirmation bias**: Seeking evidence that supports the leading hypothesis; failing to order tests that would disprove it.
- **Availability bias**: Overweighting diagnoses seen recently; a physician who just treated meningitis sees meningitis everywhere.
- **Premature closure**: Stopping the diagnostic process once a "satisfying" explanation is found, before considering the full differential.
- **Framing effect**: Patient presentation framed by a referring physician shapes the receiving physician's hypothesis generation.

Each of these biases generates structural unknown unknowns — conditions systematically excluded from the differential because the cognitive process never generates the question.

**Metacognitive debiasing strategies** taught in modern medical education:
- **Think aloud**: Verbalize diagnostic reasoning to expose assumptions
- **Forced alternative**: Explicitly generate 3 alternative diagnoses before committing
- **Diagnostic time-out**: Pause and ask "what am I missing?" at key decision points
- **Bayesian reflection**: Ask "if this test came back negative, would I change the diagnosis?"

These are structural analogs to our prism operations — they change how the problem is framed, not just how carefully it is analyzed.

### Bayesian Updating in Practice

Physicians don't calculate Bayes' theorem explicitly, but strong clinical reasoners apply it implicitly:

- **Pre-test probability** = epidemiological prior for this patient's demographic + presentation
- **Test sensitivity/specificity** = evidence quality (analogous to our source quality assessment)
- **Post-test probability** = updated belief

The key clinical mistake is **ignoring pre-test probability**: a test with 95% sensitivity and 95% specificity applied to a condition with 1% prevalence still produces more false positives than true positives. This maps directly to our MEASURED tier — a measured finding is only as useful as the calibration of the measuring instrument.

### Mapping to 5-Tier Classification

| Medical concept | Maps to our tier |
|---|---|
| Confirmed test result | STRUCTURAL |
| Clinical inference from exam findings | DERIVED |
| Sensitivity/specificity-weighted test result | MEASURED |
| Pattern recognition from clinical experience | KNOWLEDGE |
| Diagnostic criteria (assumed complete) | ASSUMED |
| "Unknown diagnosis" — no hypothesis matches | Meta-gap |

**Borrowable techniques:**
- Forced alternative hypothesis generation before commitment
- Treatment response as a diagnostic test (if X were true, Y treatment should work)
- Meta-diagnostic trigger: when framework fails, question the framework not the data
- Explicit tracking of cognitive biases as unknown-unknown generators
- "Diagnostic time-out" — a mandated pause to ask what's being missed

---

## 3. Scientific Peer Review: Claim Verification Under Information Asymmetry

### What Peer Review Actually Detects

Peer review operates under severe information asymmetry. Reviewers can detect:
- **Internal inconsistency**: Claims that contradict other claims in the same paper
- **Methodological implausibility**: Designs that couldn't produce the claimed evidence
- **Statistical errors**: P-values, confidence intervals, sample sizes that don't support the conclusions
- **Literature gaps**: Claims that ignore established contradictory evidence in the reviewer's knowledge domain
- **Implausible effect sizes**: Results outside the range of similar studies

Peer review systematically fails to detect:
- **Confabulated citations**: Reviewers rarely verify that cited papers actually say what authors claim. Studies find citation error rates of 10-40% in published literature, with most passing undetected through peer review.
- **Data fabrication**: Unless raw data is submitted for review (rare), reviewers cannot detect invented data
- **P-hacking and selective reporting**: Multiple analyses run but only significant ones reported
- **Unknown unknowns in the domain**: Conditions or confounds the reviewer doesn't know to look for
- **Expertise mismatches**: A reviewer from an adjacent field cannot assess claims that require specialized knowledge outside their training

The **structural failure** of peer review for unknown unknowns: the system selects reviewers based on domain proximity to the authors. Reviewers know the same things, share the same assumptions, and make the same category of unknown unknowns. Cross-domain review is rare and structurally difficult to organize.

### Citation Verification as a Case Study

Citation checking is the clearest example of an in-principle verifiable claim that peer review systematically fails to verify. Studies show:
- ~25% of citations in clinical medicine papers contain errors (wrong year, wrong author, wrong journal)
- ~10% are "phantom citations" — citing a paper that doesn't exist or that says nothing like what's claimed
- Post-publication automated checking (CrossRef, DOI resolution) has improved detection but doesn't check semantic accuracy (does the cited paper actually support the claim?)

Automated fact-checking systems like **ClaimBuster** (University of Texas at Arlington) classify claims by check-worthiness using machine learning trained on annotated political statements. The key classification:
- **Check-worthy factual claim**: Contains an empirical assertion that could in principle be verified
- **Non-check-worthy**: Opinion, question, prediction, or non-factual assertion

ClaimBuster's taxonomy maps closely to our tier system: it distinguishes claims that could be STRUCTURAL (documented facts), DERIVED (inferences from evidence), or ASSUMED (framed as fact but actually presupposition).

### Replication Crisis as Unknown-Unknown Surfacing

The ongoing replication crisis in psychology and medicine is a large-scale discovery of unknown unknowns:
- Many published findings assumed to be STRUCTURAL (confirmed facts) are actually MEASURED at best, and often ASSUMED (the statistical framework assumed independence, normal distribution, no selective reporting)
- Pre-registration requirements convert unknown p-hacking from unknown-unknown to known-unknown
- Open data requirements convert fabrication from unknown-unknown to detectable error
- Multi-site replication studies convert single-site findings from STRUCTURAL to MEASURED

The replication movement is essentially building infrastructure to systematically downgrade claims from higher-confidence tiers to their actual tier. The initial publication assigned too-high confidence; the replication assigns the correct tier.

### Structured Peer Review Techniques

Best-practice peer review now uses structured checklists:
- **CONSORT** (clinical trials): 25-item checklist ensuring all design and analysis elements are reported
- **PRISMA** (systematic reviews): Ensures all search methodology is documented
- **STROBE** (observational studies): Covers confound identification and adjustment
- **ARRIVE** (animal studies): Documents methodology sufficiently for replication

These checklists are exactly what our tier classification does — they force authors to distinguish between what they measured, what they inferred, and what they assumed. A CONSORT violation in "random allocation" forces the reviewer to downgrade a STRUCTURAL claim to ASSUMED.

### Mapping to 5-Tier Classification

| Peer review concept | Maps to our tier |
|---|---|
| Directly reported measurement with raw data | STRUCTURAL |
| Statistical inference from measurements | DERIVED |
| Calibrated measurement with reported uncertainty | MEASURED |
| Reviewer's domain expertise assessment | KNOWLEDGE |
| Background assumptions (unexamined) | ASSUMED |
| Claims outside reviewer's knowledge domain | Meta-gap |

**Borrowable techniques:**
- Structured checklists that force tier identification (CONSORT/PRISMA model)
- Automated citation verification (semantic, not just bibliographic)
- Cross-domain review to surface unknown unknowns (reviewers from outside the field)
- Pre-registration as assumption surfacing (forces ASSUMED → KNOWLEDGE conversion before data collection)
- Effect size plausibility checks calibrated against field-specific reference distributions

---

## 4. Financial Risk Management: Model Risk and the Unknown Unknown

### Model Risk: When the Model Doesn't Know What It Doesn't Know

The Federal Reserve's SR 11-7 guidance (2011) defines model risk as "the potential for adverse consequences from decisions based on incorrect or misused model outputs." The guidance identifies two primary sources:
1. **Model error**: The model is a flawed representation of the real system
2. **Model misuse**: A valid model used outside its intended domain or with incorrect inputs

The SR 11-7 framework requires banks to maintain **model risk management programs** that:
- Document all model assumptions explicitly
- Conduct independent validation separate from model development
- Stress test models under scenarios outside historical experience
- Maintain an inventory of known model limitations

This is institutionalized ASSUMED-tier management. Model documentation is required to list what the model assumes, and independent validation is required to test whether those assumptions hold.

### The Black Swan Problem

Nassim Taleb's framework (The Black Swan, 2007; Antifragile, 2012) identifies the deepest form of financial unknown unknown: **the distribution of outcomes has fat tails that the model treats as thin tails.** Standard financial models (VaR, Black-Scholes) assume normally-distributed returns. Real markets have power-law tails — extreme events occur orders of magnitude more frequently than the model predicts.

Taleb's taxonomy maps to our tier system:
- **White swans**: Events within the model's predictive range — MEASURED or DERIVED
- **Grey swans**: Extreme events the model assigns very low probability — KNOWLEDGE (the model knows they're possible, just underestimates frequency)
- **Black swans**: Events the model's distributional assumptions make structurally impossible to predict — the pure unknown unknown, structurally invisible to the framework

The model risk framework essentially says: all model outputs are DERIVED from ASSUMED distributional properties. When the ASSUMED tier fails (tail behavior departs from the assumed distribution), DERIVED claims collapse regardless of how correctly the model executed.

### Stress Testing: Converting Unknown Unknowns to Known Stress Scenarios

Financial regulators now require **stress testing** under scenarios that are deliberately outside historical data:
- **Historical stress scenarios**: 2008 crisis, 1987 crash, 1929 depression — use known extreme events
- **Hypothetical stress scenarios**: "What if interest rates rise 400bp in 3 months?" — deliberately outside model training distribution
- **Reverse stress testing**: "What scenario would make our firm insolvent?" — model-agnostic backward reasoning

Reverse stress testing is the most powerful for unknown unknowns: it asks not "what does the model predict under stress?" but "what would have to be true for the firm to fail?" This forces analysts to generate scenarios outside the model's assumed universe.

This is structurally identical to the pre-mortem technique in intelligence analysis and the adversarial pass in our pipeline. The operation is the same: **assume the model is wrong, then explain why.**

### Model Validation: Independent Uncertainty Quantification

SR 11-7 requires that model validation includes:
- **Conceptual soundness**: Are the model's theoretical foundations appropriate?
- **Ongoing monitoring**: Does the model's performance degrade over time?
- **Outcome analysis**: Does the model's predictions match realized outcomes?
- **Sensitivity analysis**: How much do outputs change when inputs change slightly?

The sensitivity analysis requirement is directly analogous to our DERIVED tier: derived claims should be labeled with their sensitivity to input uncertainty. A conclusion that changes sign when one input changes by 10% is not a STRUCTURAL finding — it's at best a MEASURED one with wide uncertainty bounds.

### Knightian Uncertainty: The Third Type

Economist Frank Knight (1921) distinguished:
- **Risk**: Outcomes with known probability distributions — can be quantified and hedged
- **Uncertainty**: Outcomes with unknown probability distributions — cannot be assigned probabilities
- **Radical uncertainty**: Outcomes that haven't been imagined yet — the pure unknown unknown

This maps more precisely to our tier system than the 2x2 Rumsfeld matrix:
- Risk → MEASURED (probability known)
- Uncertainty → KNOWLEDGE (possible but not quantified)
- Radical uncertainty → ASSUMED (framework does not even generate the question)

The key financial insight: **hedging works for risk, diversification for uncertainty, and only redundancy and robustness for radical uncertainty.** The analogous insight for our gap detection: MEASURED gaps can be quantified, KNOWLEDGE gaps can be flagged, but ASSUMED gaps require a different kind of analysis — one that interrogates the framing rather than the content.

### Mapping to 5-Tier Classification

| Finance concept | Maps to our tier |
|---|---|
| Market price (observed, liquid) | STRUCTURAL |
| Model output (derived from inputs) | DERIVED |
| VaR (estimated with confidence interval) | MEASURED |
| Expert judgment on stress scenarios | KNOWLEDGE |
| Distributional assumptions (normality etc.) | ASSUMED |
| Black swans (structurally invisible) | Meta-gap |

**Borrowable techniques:**
- Mandatory assumption documentation for every model claim
- Reverse stress testing (assume failure, derive conditions)
- Independent validation separate from model development
- Sensitivity analysis tagging: how much does this conclusion depend on each assumption?
- Model inventory with known limitations explicitly catalogued
- Model monitoring over time: does the model's uncertainty grow as conditions change?

---

## 5. Software Testing: Engineering the Discovery of Unknown Unknowns

### Mutation Testing: Testing the Tests

Standard code coverage measures what percentage of code is executed by tests. This answers "what did we test?" not "what would we catch?" Mutation testing answers the second question.

**Methodology:**
1. Take a program and systematically introduce small changes (**mutants**) — flip a `>` to `>=`, change an integer constant, negate a boolean
2. Run the full test suite against each mutant
3. A mutant is **killed** if any test fails; it **survives** if all tests pass
4. The **mutation score** = killed / total mutants

A surviving mutant reveals a behavioral difference in the code that the test suite doesn't detect — a gap in what the tests know to check. A test suite with 100% line coverage can have a mutation score of 40%, revealing that 60% of code mutations go undetected.

**The unknown unknown structure**: The developer wrote tests for behaviors they thought were important. Mutation testing generates perturbations the developer didn't think to test — the mutants are precisely the things the developer didn't know they needed to test for. Each surviving mutant is a known unknown (now known, after mutation testing) that was an unknown unknown before.

This maps to our STRUCTURAL tier: if a claim is STRUCTURAL, any mutation of the underlying evidence should cause the claim to fail. If a structural claim survives mutation of its evidence (the claim is made regardless of what the evidence says), it's misclassified — it's actually ASSUMED.

### Property-Based Testing: Specifying What Should Always Be True

As the Hypothesis library documentation explains: "Property-based testing is the construction of tests such that, when these tests are fuzzed, failures in the test reveal problems with the system under test."

Rather than testing specific input/output pairs, property-based testing specifies **invariants**: conditions that should hold for all inputs. The framework then generates thousands of random inputs attempting to violate the invariant.

**Key insight**: Developers specify properties they believe are universal. When the framework finds a violation, it reveals an assumption the developer made (this property holds for all inputs) that was actually false (it fails for input X). The failing input is an unknown unknown converted to a known counterexample.

Property-based testing maps to our ASSUMED tier: it systematically challenges claims that developers took as axiomatic. The framework assumes nothing — it generates inputs the developer never considered.

### Fuzzing: Black-Box Unknown Unknown Detection

Fuzzing sends malformed, unexpected, or random data to a system and watches for crashes, assertion failures, or undefined behavior. Two variants:

1. **Blackbox fuzzing**: Purely random inputs — discovers unknown unknowns in the execution space developers never tested
2. **Coverage-guided fuzzing** (AFL, libFuzzer): Instruments code to detect which inputs reach new code paths; steers input generation toward unexplored territory

Coverage-guided fuzzing is epistemically sophisticated: it treats unexplored code paths as unknown unknowns and systematically navigates toward them. It doesn't know what it will find — it only knows it hasn't been there yet.

OWASP documents a key example: Microsoft's JPEG parser (MS04-028) was discovered by fuzzing — a zero-sized comment field that crashed the parser. No developer had tested this input because no developer imagined a user would send it. The bug existed in production for years as an unknown unknown.

**The systematic principle**: A fuzzer treats all unexercised program states as potential unknown unknowns and probes them. Coverage-guided fuzzing makes the unknown-unknown discovery systematic rather than random.

### Chaos Engineering: Unknown Unknowns in Distributed Systems

As the Chaos Engineering principles (principlesofchaos.org) state: "Chaos Engineering is the discipline of experimenting on a system in order to build confidence in the system's capability to withstand turbulent conditions in production."

The methodology:
1. **Define steady state**: Normal system metrics (request throughput, latency, error rate)
2. **Form a hypothesis**: System will maintain steady state under perturbation X
3. **Introduce perturbation**: Terminate random instances (Chaos Monkey), inject network latency, kill a dependency
4. **Observe deviation**: Compare perturbed to control group

The crucial chaos engineering insight: "Even when all of the individual services in a distributed system are functioning properly, the interactions between those services can cause unpredictable outcomes."

Individual components are tested in isolation; their interactions generate unknown unknowns. The interaction space between N services is N! in the worst case — no developer can enumerate it. Chaos engineering probes the interaction space systematically, discovering failure modes that emerge from combinations no one tested.

This maps exactly to our DERIVED tier: a derived claim follows from component claims. But if the derivation logic has unknown failure modes (components interact in unexpected ways), the derived claim fails even when all component claims are correct.

**The Netflix Simian Army** extended chaos engineering across multiple failure dimensions:
- **Chaos Monkey**: Kills random instances
- **Chaos Gorilla**: Kills entire availability zones
- **Latency Monkey**: Injects artificial latency
- **Doctor Monkey**: Checks instance health
- **Janitor Monkey**: Cleans unused resources
- **Security Monkey**: Detects security vulnerabilities

Each monkey probes a different class of unknown unknowns in production.

### The Unified Software Testing Principle

Across mutation testing, property-based testing, fuzzing, and chaos engineering, the same operation appears: **generate inputs/states/perturbations that the developer didn't think to specify, then observe whether the system handles them correctly.** The differences are in where the perturbations are applied (code logic, input space, execution state, system architecture) and how they're generated (systematic, random, coverage-guided, random).

The operation is: **assume the developer's knowledge is incomplete, then probe the gaps.**

### Mapping to 5-Tier Classification

| Testing concept | Maps to our tier |
|---|---|
| Confirmed test case (input/expected output) | STRUCTURAL |
| Derived behavior from composition of tested units | DERIVED |
| Mutation score (% of code changes detected) | MEASURED |
| Developer's intended behavior specification | KNOWLEDGE |
| Assumptions in test design (what inputs matter) | ASSUMED |
| Untested interaction effects | Meta-gap → use chaos engineering |

**Borrowable techniques:**
- Mutation testing applied to analysis claims: would this conclusion survive if one evidence item flipped?
- Property-based testing: specify invariants the analysis should maintain; test whether they hold across inputs
- Coverage-driven probing: track which knowledge domains have been "exercised" in the analysis
- Adversarial input generation: systematically generate inputs that challenge the analysis framework
- Perturbation-response testing: what happens to the derived claim if the structural evidence shifts slightly?

---

## 6. Journalism Fact-Checking: Claim Classification and Verifiability Assessment

### The PolitiFact Methodology: Tiered Verifiability

PolitiFact uses a 6-level Truth-O-Meter:
- **TRUE**: Accurate with nothing significant omitted
- **MOSTLY TRUE**: Accurate but needs clarification
- **HALF TRUE**: Partially accurate, omits important context
- **MOSTLY FALSE**: Contains truth but ignores critical facts
- **FALSE**: Inaccurate
- **PANTS ON FIRE**: Inaccurate and a ridiculous claim

The key selection criterion: fact-checkers only rate claims "rooted in a fact that is verifiable." Pure opinions, questions, and predictions are excluded. The fact-checker must first classify: is this a claim that can in principle be verified?

This **verifiability pre-classification** is the key operation. Before assessing accuracy, the methodology forces a meta-question: what type of claim is this? This is exactly our tier classification operating before accuracy assessment.

PolitiFact's "for claims they cannot independently verify, they note limitations in reporting rather than assigning ratings" — this is a documented gap surfacing. They distinguish between "we checked and it's false" and "we could not check this" — two different types of uncertainty.

### ClaimBuster: Automated Check-Worthiness Detection

ClaimBuster (University of Texas at Arlington) uses machine learning to classify political statements into:
- **Check-worthy factual claim (CFS)**: Empirical assertion that could in principle be verified
- **Unimportant factual sentence (UFS)**: Factual but not check-worthy (trivial, already documented)
- **Non-factual sentence (NFS)**: Opinion, question, prediction

Training data: annotated debate transcripts where human fact-checkers marked what they chose to check. The system learns what makes a claim worth checking — which is essentially what makes a claim falsifiable.

The NLP features that predict check-worthiness include:
- Presence of named entities, numbers, and specific events (more concrete = more checkable)
- Grammatical mood (declarative vs. conditional — conditional claims are harder to verify)
- Temporal markers (past events more verifiable than future predictions)
- Comparative claims (require a baseline that may be unknown)

This mapping is precise: check-worthy claims correspond roughly to STRUCTURAL and DERIVED tiers. Non-check-worthy claims (conditional, future, comparative) correspond to KNOWLEDGE and ASSUMED tiers.

### Full Fact's Automated Fact-Checking

UK fact-checker Full Fact (fullfact.org) has developed automated tools for:
- **Claim monitoring**: Detecting when politicians repeat the same claim (allowing pre-verification)
- **Claim matching**: Comparing new claims against a database of previously verified claims
- **Live fact-checking**: Real-time classification of parliamentary debate claims

Their methodology distinguishes three types of factual errors:
1. **Errors of commission**: False statement
2. **Errors of omission**: True but misleading through selective presentation
3. **Errors of framing**: True facts, but context makes them mean something different

Errors of framing are the fact-checker's unknown unknown: the claim is technically accurate, but the framing activates false background assumptions in the reader. This maps precisely to our ASSUMED tier — the claim is true, but its truth depends on assumptions the audience doesn't share.

### International Fact-Checking Network (IFCN) Code of Principles

IFCN accredits fact-checking organizations worldwide based on five commitments:
1. **Nonpartisanship**: Applies same standards to all sides
2. **Transparency of sources**: All sources identified
3. **Transparency of funding**: Revenue sources disclosed
4. **Transparency of methodology**: How claims are selected and checked
5. **Open corrections policy**: Errors corrected publicly and promptly

The methodology transparency requirement is directly analogous to our gap detection output: the fact-checker must document not only what they found but **how they checked and what they couldn't check.** An IFCN-compliant fact-check explicitly distinguishes between "we verified this is false" and "we could not verify this claim."

### The Epistemics of Fact-Checking Limits

Fact-checkers face systematic limits that create structural unknown unknowns:
- **Source opacity**: Claims sourced from classified information, private documents, or off-record conversations cannot be verified externally
- **Methodological disputes**: Where experts disagree, fact-checkers cannot adjudicate (this is not a factual question, it's a KNOWLEDGE-tier dispute)
- **Future predictions**: Claims about future events cannot be verified at the time of publication
- **Counterfactuals**: "The policy prevented X deaths" requires a counterfactual world that doesn't exist

These limits define the upper boundary of the STRUCTURAL tier in journalism: verified published records, confirmed public statements, documented government data. Below that: DERIVED (inferences from verified facts), MEASURED (statistical estimates with stated methodology), KNOWLEDGE (expert consensus), ASSUMED (background assumptions in claim framing).

### Mapping to 5-Tier Classification

| Journalism concept | Maps to our tier |
|---|---|
| Government statistic (official, documented) | STRUCTURAL |
| Journalist's inference from documents | DERIVED |
| Statistical analysis of verified data | MEASURED |
| Expert consensus cited by fact-checker | KNOWLEDGE |
| Framing assumptions enabling the claim | ASSUMED |
| Counterfactual and classified claims | Meta-gap |

**Borrowable techniques:**
- Verifiability pre-classification before accuracy assessment
- "Could not verify" as a distinct output from "false" — gap acknowledgment is a fact-check result
- Framing error detection: when the claim is technically true but context makes it misleading
- Claim matching against prior verified claims (avoid redundant analysis)
- Automated check-worthiness detection to triage claims by verifiability tier

---

## Cross-Domain Synthesis

### The Universal Gap Detection Pattern

Across all six domains, the same structure appears:

**1. Framework-relative blindness.** Every domain's primary failure mode is not oversight but structural blindness — the framework makes certain questions unaskable. Intelligence collection systems collect evidence for pre-specified hypotheses. Differential diagnosis generates hypotheses from pattern recognition of known diseases. Financial models encode distributional assumptions. Test suites encode developer assumptions about what matters. Peer reviewers are selected from within the same epistemic community. Fact-checkers cannot verify what their methodological tools don't address.

**The universal structural principle: an analytical framework that is good at finding X makes it hard to notice things that aren't X.**

**2. The same three operations** convert unknown unknowns to known unknowns across all domains:
- **Adversarial inversion** (intelligence pre-mortem, medical forced alternative, financial reverse stress test, software chaos engineering, peer review red team, journalism counter-claim): assume you're wrong, derive conditions
- **Framework interrogation** (ACH key assumptions check, medical diagnostic time-out, model risk documentation, property-based test invariant specification, CONSORT checklist, fact-checker methodology disclosure): explicitly audit what the framework assumes
- **Independent validation** (red team analysis, second opinion, independent model validation, mutation testing, cross-domain peer review, multi-outlet fact-checking): someone who didn't build the framework checks it

**3. Tier classification is universal.** Every domain independently derived a version of our 5-tier classification:

| Our tier | Intelligence | Medicine | Finance | Software | Peer review | Journalism |
|---|---|---|---|---|---|---|
| STRUCTURAL | Confirmed facts | Confirmed test | Observed market data | Passing test | Replicated finding | Verified document |
| DERIVED | Assessment | Clinical inference | Model output | Derived behavior | Statistical inference | Journalist inference |
| MEASURED | Probabilistic estimate | Calibrated diagnosis | VaR estimate | Mutation score | Effect size + CI | Statistical analysis |
| KNOWLEDGE | Expert judgment | Pattern recognition | Expert stress scenario | Developer intent | Reviewer expertise | Expert consensus |
| ASSUMED | Key assumptions | Diagnostic criteria | Model distributional assumptions | Test design assumptions | Background research paradigm | Framing presuppositions |
| Meta-gap | Unknown unknowns | Unknown diagnosis | Black swans | Untested interactions | Outside reviewer knowledge | Unverifiable claims |

### Key Borrowed Insights for Our Gap Detection

**From intelligence analysis:**
- Pre-mortem as standard pipeline step (already in our adversarial pass — this validates the design)
- Diagnostic matrix: list what evidence would be inconsistent with each claim tier
- Calibrated probability language: distinguish "high confidence" from "assessed" from "assumed"

**From medical diagnosis:**
- Forced alternative generation: before finalizing gap classification, generate 3 alternative interpretations
- Treatment-as-test: derive what additional information would confirm/disconfirm a DERIVED claim
- Meta-diagnostic trigger: when the analysis doesn't converge, question the framework, not the data

**From peer review:**
- Structured checklists that force tier identification (CONSORT model)
- "Could not verify" as an explicit output alongside "false" — gap acknowledgment is informative
- Cross-domain validation: the best unknown-unknown detection uses reviewers from outside the primary domain

**From finance:**
- Sensitivity tagging: every DERIVED claim should carry its sensitivity to each ASSUMED input
- Reverse stress test: assume the claim is wrong; what combination of gap types would explain it?
- Model inventory: catalogue known limitations with each claim, not just confidence levels

**From software testing:**
- Mutation test the analysis: would the conclusion change if one evidence piece flipped?
- Coverage tracking: which knowledge domains have been exercised? Which are unexplored?
- Systematic perturbation: test claims across a range of slight variations, not just the nominal case

**From journalism:**
- Verifiability pre-classification as the first step (before accuracy assessment)
- Explicit "cannot verify" output: surfacing the meta-gap is itself an analytic result
- Framing error detection: technically true but contextually misleading = ASSUMED-tier failure

### The Conservation Law

Across all six domains, one trade-off is conserved:

**COVERAGE × DEPTH × DOMAIN SPECIFICITY = CONSTANT**

A framework that covers all possible gaps (fuzzing, random testing) loses depth and domain specificity. A framework that goes deep into one gap type (ACH hypothesis matrix) misses gaps outside its hypotheses. A framework that is maximally domain-specific (CONSORT checklist for clinical trials) doesn't transfer.

Our 5-tier classification solves this by being a **structural decomposition** rather than a domain-specific checklist. It doesn't enumerate what to look for — it classifies how what you find was derived. This is domain-invariant because the epistemological categories (structural/derived/measured/knowledge/assumed) apply to any claim in any domain.

The remaining unknown unknown in our system: **what the 5-tier classification itself makes structurally invisible.** Based on the cross-domain survey, the strongest candidate is interaction effects — claims that are correctly classified individually but whose interaction produces a new gap category. The chaos engineering lesson: components can be verified individually, but their interactions generate unknown unknowns that no component-level analysis detects.

---

## Appendix: Source Quality Notes

This survey draws on:
- IARPA ACE program documentation (iarpa.gov)
- PolitiFact methodology documentation (politifact.com)
- Chaos Engineering principles (principlesofchaos.org)
- Property-based testing methodology (hypothesis.works)
- OWASP Fuzzing documentation (owasp.org)
- Diagnostic screening research (PMC medical literature)
- SR 11-7 model risk management framework (Federal Reserve, 2011)
- Rumsfeld DoD briefing (February 12, 2002)
- Heuer, R.J. (1999) "Psychology of Intelligence Analysis" — CIA/CSI
- Tetlock, P. & Gardner, D. (2015) "Superforecasting" — ACE program research
- Taleb, N.N. (2007) "The Black Swan" — financial unknown unknowns
- Knight, F.H. (1921) "Risk, Uncertainty and Profit" — Knightian uncertainty taxonomy
- IFCN Code of Principles (poynter.org/ifcn)

Web access was limited for many primary sources (403/404 from Wikipedia, academic publishers, government archives). Key methodology documentation was retrieved from IARPA, principlesofchaos.org, hypothesis.works, owasp.org, politifact.com, and medical PMC archives.
