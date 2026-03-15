# Literature Review — Epistemic AI & Uncertainty Systems

**Date**: Mar 15, 2026
**Author**: Research agent (Claude Sonnet 4.6)
**Purpose**: Survey of related work across five domains relevant to the Prism project's knowledge gap detection pipeline and `Specificity × Verifiability = Constant` conservation law.

---

## Overview

The Prism project independently discovered several principles that are actively researched in the academic AI community under different terminology. This review maps the correspondences, identifies the gaps, and notes where the project leads rather than follows.

**Core parallel**: Prism's `Specificity × Verifiability = Constant` (P206, Round 41) is the analytical instantiation of a constraint that appears across five literatures: uncertainty quantification, conformal prediction, knowledge grounding, provenance tracking, and cognitive calibration science. Each field found it from a different angle.

---

## 1. Epistemic AI Frameworks — Uncertainty Quantification

### 1.1 The Two-Tier Uncertainty Distinction

**Source**: Standard UQ literature; synthesized in "Uncertainty Quantification and Confidence Calibration in Large Language Models: A Survey" (arxiv:2503.15850, 2025).

Every serious UQ framework distinguishes:
- **Epistemic uncertainty**: gaps in knowledge, reducible with more data or retrieval. What Prism calls CONTEXTUAL and ASSUMED gaps.
- **Aleatoric uncertainty**: irreducible noise inherent to the domain. What Prism calls structural impossibility (the conservation law itself).

**Relevance**: Prism's gap taxonomy (STRUCTURAL / DERIVED / MEASURED / CONTEXTUAL / ASSUMED) maps cleanly to this distinction. STRUCTURAL and DERIVED claims have low epistemic uncertainty (they derive from source code directly); CONTEXTUAL and ASSUMED claims have high epistemic uncertainty (depend on external facts or psychological models). The 5-tier classification (P213) is independently convergent with academic UQ frameworks.

**Key insight for Prism**: The academic field treats "epistemic uncertainty" as a property of individual claims. Prism found the same thing from the opposite direction: `Specificity × Verifiability = Constant` is the conservation law that explains WHY epistemic uncertainty scales with claim specificity. This is a stronger statement — not just "high specificity = high uncertainty" but "their product is conserved across all analysis."

### 1.2 Self-Verbalized Uncertainty (Prompt-Level)

**Sources**:
- "Revisiting Epistemic Markers in Confidence Estimation" (ACL 2025): studies how LLMs use hedging language ("I think," "I'm not sure") as confidence signals.
- "Mind the Confidence Gap" (arxiv:2502.11028, 2025): overconfidence, calibration, and distractor effects.
- "Extending Epistemic Uncertainty Beyond Parameters Would Assist in Designing Reliable LLMs" (arxiv:2506.07448, 2025): epistemic uncertainty as semantic feature gap in hidden space.

**Key finding**: Self-verbalized confidence is poorly calibrated and prone to overconfidence. Verbal confidence markers ("I'm certain that...") do NOT reliably predict accuracy. Models fail to distinguish between high-confidence correct answers and high-confidence hallucinations.

**Relevance**: This validates Prism's knowledge_audit prism design choice. Rather than asking the model to self-report confidence, the audit prism uses adversarial construction to ATTACK claims — a behaviorally different operation that bypasses the self-report calibration failure. Structural auditing > self-report asking.

**Gap Prism leads on**: No prompt-level framework in the literature performs adversarial construction-based auditing. The field focuses on extracting confidence scores; Prism focuses on stress-testing claims. Different operations.

### 1.3 Epistemic Integrity Architecture (Type-Theoretic)

**Source**: "Beyond Prediction: Structuring Epistemic Integrity in Artificial Reasoning Systems" (arxiv:2506.17331, 2025).

Proposes formal architecture for AI systems with epistemic constraints:
- **Belief Architecture**: persistent (φ, Justification(φ)) pairs — propositions tagged with their derivation chains.
- **Epistemic State Tagging**: marks beliefs as 'derived', 'approximate', or 'operationally justified'.
- **Confidence Stratification**: explicit thresholds (50%, 95%, 99%) mapping probabilistic credence to distinct epistemic categories.
- **Contradiction Resolution Protocols**: AGM (Alchourrón-Gärdenfors-Makinson) belief revision theory.
- **Blockchain-based audit trails**: verifiable, temporally persistent epistemic records.

**Relevance**: This is the architectural cousin of both Sounio Lang and Prism's knowledge_typed prism. The "epistemic state tagging" ('derived', 'approximate', 'operationally justified') closely parallels Prism's 5-tier classification (STRUCTURAL/DERIVED/MEASURED/CONTEXTUAL/ASSUMED). The "Confidence Stratification" is what Prism's gap_extract_v2 does — assigns numerical confidence to each tier.

**Gap**: This paper operates at the system architecture level (redesigning AI systems from scratch). Prism operates at the prompt level — applying the same epistemic discipline to existing models without architectural changes. Prism's approach is more immediately deployable.

### 1.4 Epistemic Anti-Patterns (Parametric Modeling)

**Source**: "Parametric Modeling of Epistemic Anti-Patterns in Language Models" (research.aiqa.io, 2025).

Defines four failure modes:
1. **Hallucination (H)**: fabricated information
2. **Simulation Drift (D)**: incoherence in long outputs
3. **Override Behavior (O)**: ignoring constraints
4. **Falsehood Confidence (F)**: maintaining incorrect claims with conviction

Proposes a parametric risk equation: `A = α⋅T^γ⋅L^λ⋅E^ϵ⋅(1/P^ρ⋅S^σ⋅R^η⋅C^χ)` where controllable variables include temperature, token length, prompt structure, role clarity, and constraint enforcement.

Introduces the **Epistemic Illusion Index**: measures how fluent-but-false outputs deceive users.

**Relevance**: This formalizes what Prism found empirically in Round 41:
- Prism's BT-4 (confabulation predictor) shows confabulation is predictable from surface features.
- The "Falsehood Confidence" pattern corresponds exactly to Prism's finding that high-specificity claims with high-confidence presentation are the most dangerous — they pass casual review.
- Prism's P211: "Confabulation predictable from surface features: high specificity + not quoted from source = HIGH risk" is the prompt-level instantiation of this formal model.

**Key insight**: Prompt structure (S) and constraint enforcement (C) are the prompt-level variables. This validates Prism's approach: structured prompts (L12-G's three-phase architecture) reduce hallucination not by changing the model but by changing the generation constraint landscape.

---

## 2. Conformal Prediction for LLMs

### 2.1 Core Method

**Sources**:
- "Conformal Prediction for Natural Language Processing: A Survey" (TACL 2024, MIT Press)
- "Token-Entropy Conformal Prediction" — TECP (MDPI Mathematics 2025)
- "Selective Conformal Uncertainty in LLMs" — SConU (ACL 2025)
- "Conformal Language Modeling" (OpenReview/ICLR 2024)

**What it is**: Conformal prediction wraps any model (no retraining required) and produces prediction SETS with statistical coverage guarantees. Instead of a single answer, the model outputs a set of answers guaranteed to contain the correct answer at a specified confidence level (e.g., 90%).

**How it works at inference time**:
1. Calibrate on a validation set: find threshold q such that 90% of calibration examples have the correct answer in the prediction set.
2. At inference: include all candidate answers scoring above q in the prediction set.
3. The size of the prediction set signals uncertainty: large set = uncertain, small set = confident.

**Key mathematical property**: Coverage guarantees hold without any assumptions about the model's internal architecture. The only assumption is exchangeability of calibration and test data.

**Relevance to Prism**: Conformal prediction is the rigorous statistical framework for what Prism does informally with confidence tiers. Where Prism assigns qualitative tiers (STRUCTURAL/DERIVED/MEASURED/CONTEXTUAL/ASSUMED), conformal prediction would assign quantitative coverage sets. The frameworks are complementary:
- Conformal prediction: statistically rigorous, requires calibration data, model-agnostic.
- Prism's gap detection: semantically interpretable, works zero-shot, produces actionable fill strategies.

**Gap Prism leads on**: Conformal prediction produces prediction sets but doesn't tell you WHY a claim is uncertain or HOW to fill the gap. Prism's gap taxonomy does both — it classifies uncertainty by type and maps each type to a fill mechanism (API_DOCS, CVE_DB, COMMUNITY, BENCHMARK, CHANGELOG).

### 2.2 KNOWNO — Conformal Prediction for Planning

**Source**: "KNOWNO: Knowing When to Ask in Robotic Planning" (Google DeepMind, NeurIPS 2023). Referenced in 2025 surveys.

Applies conformal prediction to LLM-based robotic planning. The key insight: when the prediction set contains only one plan, the model is confident enough to act. When the set has multiple plans, the robot should ask a human for clarification.

**Relevance**: This is the actionability threshold mechanism. Prism's gap detection pipeline implicitly does the same: when gaps are STRUCTURAL (one clear answer from source code), proceed. When gaps are CONTEXTUAL or ASSUMED (multiple plausible fills), flag for human verification. KNOWNO formalizes the confidence threshold; Prism operationalizes it via claim typing.

### 2.3 Semantic Entropy Probes (Inference-Time)

**Source**: "Semantic Entropy Probes: Robust and Cheap Hallucination Detection in LLMs" (Farquhar et al., Oxford/OATML, ICML 2024).

**Key innovation**: Linear probes trained on LLM hidden states can approximate semantic entropy (a measure of output variability across semantically equivalent paraphrases) from a SINGLE generation — eliminating the need to sample multiple outputs.

**How it works**: The probe reads the model's internal activation states at inference time. High entropy in hidden states predicts hallucination. Works without model retraining, using only a linear classifier on top of frozen model representations.

**Relevance**: This is the cleanest inference-time uncertainty detector — no sampling overhead, works on frozen models. Where this differs from Prism:
- Semantic entropy probes detect THAT a claim is uncertain (binary signal).
- Prism's knowledge_audit classifies WHY (what type of gap) and WHERE to fill it.

Both are complementary. A deployed system could run semantic entropy probes as a cheap pre-filter (is this claim uncertain at all?) and Prism's audit prism for claims that trigger the filter (what kind of uncertainty, and how to resolve it?).

---

## 3. Knowledge Graphs + LLMs — Grounding and Factual Verification

### 3.1 RAG and the Grounding Problem

**Sources**:
- "UltRAG: A universal simple scalable recipe for knowledge graph RAG" (OpenReview 2025)
- "Simple is Effective: The Roles of Graphs and LLMs in Knowledge-Graph-Based RAG" (OpenReview 2025)
- "Mitigating Hallucination in RAG LLMs: A Review" (MDPI Mathematics 2025)

**State of the art**: Retrieval-Augmented Generation (RAG) grounds LLM outputs in external knowledge sources, reducing hallucination rates. Knowledge Graph RAG (KG-RAG) extends this to structured knowledge, enabling multi-hop reasoning.

**Key limitation of RAG**: RAG reduces hallucination on topics covered by the retrieval corpus but does not eliminate it. Models still hallucinate when:
1. The retrieved documents don't contain the answer (out-of-domain query).
2. The model misinterprets or ignores retrieved context.
3. The claim is about a relationship not explicitly stated in any document.

**Relevance to Prism**: RAG addresses Prism's CONTEXTUAL gap type (version-dependent, library-specific claims). When Prism's knowledge_boundary prism flags a claim as CONTEXTUAL with fill_source=API_DOCS, the fill step IS essentially a RAG query against the AgentsKB or web search. Prism's pipeline is RAG applied selectively (only for high-risk claims) rather than universally (for every query).

**Gap Prism leads on**: RAG systems retrieve documents and inject them uniformly. Prism's pipeline first audits WHICH claims need grounding (gap detection), then retrieves only for those claims (targeted fill), then re-runs analysis with corrected facts (augmented re-analysis). This three-stage approach (audit → targeted fill → re-analysis) is not in the RAG literature.

### 3.2 Explicit Knowledge Boundary Modeling (EKBM)

**Source**: "Enhancing LLM Reliability via Explicit Knowledge Boundary Modeling" (arxiv:2503.02233, 2025).

**What it does**: Trains models to classify their own outputs as "Sure" or "Unsure" during generation, using a two-stage fast/slow pipeline. High-confidence outputs proceed immediately; low-confidence outputs undergo multi-step refinement.

**Training method**: SFT + DPO to improve model self-awareness about knowledge limits, without degrading task performance.

**Relevance**: EKBM's "Sure/Unsure" binary is a coarser version of Prism's 5-tier confidence taxonomy. EKBM requires fine-tuning; Prism achieves similar classification through prompt engineering alone (zero-shot). The finding that "smaller models can be more self-aware than larger ones through targeted training" parallels Prism's finding that Haiku + right prism beats Opus vanilla.

### 3.3 Abstention Research

**Source**: "Know Your Limits: A Survey of Abstention in Large Language Models" (TACL 2025, Wen et al.).

**Key finding**: LLMs show significant over-refusal — models are often too conservative, refusing tasks they could handle. The same models are simultaneously overconfident on tasks they cannot handle. These are separate failure modes (over-refusal ≠ under-refusal).

**Relevance**: Prism's knowledge_audit prism is not about abstention — it's about CLASSIFICATION. Rather than having the model refuse uncertain claims, Prism identifies, classifies, and fills them. This is strictly superior to abstention: the system still produces output, but the output is better grounded. The abstention literature addresses the question "should the model answer?"; Prism addresses "if it answers, which parts should you trust?"

---

## 4. Provenance Tracking in AI

### 4.1 Prompt Provenance Model (PPM)

**Source**: "Prompt Provenance: Toward Traceable LLM Interactions" (Procko et al., SSRN 2025).

**What it is**: A W3C PROV-O extension that models prompts, completions, and dialogue histories as first-class provenance entities. Creates formal relationships between: user intent → system messages → retrieved sources → generated artifacts.

**Key constructs**:
- Prompts as entities with lineage.
- Completions as derived entities.
- Sources as influencing agents.
- The chain: User Intent → Prompt → Retrieval → Completion → Artifact.

**Relevance**: This is the formal information-theoretic backing for Prism's K1b item (`--provenance` flag). PPM formalizes exactly what Prism's knowledge_typed prism does informally: every finding should carry (claim, source, derivation_path, confidence). The difference: PPM is a metadata model for logging; Prism's knowledge_typed prism is a live analysis operation that extracts this structure on-the-fly from a single model pass.

### 4.2 PROV-AGENT and Agentic Workflow Provenance

**Source**: "LLM Agents for Interactive Workflow Provenance" (arxiv:2509.13978, 2025).

Extends classical provenance to agentic workflows. Frameworks like Graphectory, PROV-AGENT, and AdProv extend PROV with agent-level and prompt-level metadata for multi-step LLM pipelines.

**Relevance**: Prism's full pipeline (L12 → boundary → audit → extraction → fill → re-analysis) is a multi-step agentic workflow. Each step transforms the artifact and adds epistemic guarantees. PROV-AGENT formalizes the lineage between pipeline steps. This aligns with Prism's J10 vision: `.deep/knowledge/` storing verified facts per file across sessions. The persistent KB is provenance tracking for code analysis.

### 4.3 Data Provenance Initiative

**Source**: "The Data Provenance Initiative" (Carnegie Mellon University, 2023-2025). Ongoing initiative tracking training data lineage for major LLMs.

**Key insight**: "Where does each claim come from?" is unanswerable for LLM outputs without provenance tracking during training. The initiative advocates for training data cards that record source, license, transformation, and intended use for every training document.

**Relevance**: This explains WHY Prism's confabulation problem is structural: models cannot trace claims to training sources because that provenance wasn't tracked during training. Prism's gap detection is a post-hoc provenance recovery mechanism — not perfect, but the best achievable without retraining. The conservation law `Specificity × Verifiability = Constant` is the formal statement of this limitation: high-specificity claims (exact version numbers, API signatures) require specific training data provenance that doesn't exist.

---

## 5. Type Systems for AI Outputs

### 5.1 Sounio Lang — First-Class Uncertainty Types (Independent Discovery)

**Source**: souniolang.org. See `research/souniolang_analysis.md` for full analysis.

**Summary**: Sounio is a systems programming language where `Knowledge<T>` is a first-class type carrying epsilon (uncertainty), confidence, and provenance. GUM-standard uncertainty propagation is automatic. Created by Demetrios Chiuratto Agourakis.

**Isomorphism with Prism**: Sounio's type hierarchy (raw → dimensioned → uncertain → traced → validated) is structurally isomorphic to Prism's compression levels (L1-4 → L5-7 → L8-11 → L12-13 → L12-G). Both are categorically stepped. Both discovered that separating verified from unverified is the critical operation. Neither cited the other.

**Deeper parallel**: Sounio's GUM uncertainty propagation (the product of uncertainties through a computation chain) IS the formal version of `Specificity × Verifiability = Constant`. GUM says: when you multiply quantities with uncertainties ε₁ and ε₂, the result has uncertainty that propagates as a product form. Prism says: specificity × verifiability is constant across all claims. Both express the same conservation principle, one for computational measurements, one for language model outputs.

### 5.2 Epistemic Integrity Architecture (Structured Outputs)

**Source**: arxiv:2506.17331 (see Section 1.3 above).

The "Confidence Stratification" (50%/95%/99% thresholds mapped to epistemic categories) is a type system in the loose sense: it assigns each claim a type based on evidential certainty. This is the academic version of Prism's 5-tier taxonomy (STRUCTURAL=0.9+, DERIVED=0.6-0.9, MEASURED=0.3-0.6, CONTEXTUAL=0.1-0.3, ASSUMED=<0.1).

### 5.3 Structured Output Reliability (STED + Consistency Scoring)

**Source**: "STED and Consistency Scoring: A Framework for Evaluating LLM Structured Output Reliability" (arxiv:2512.23712, 2025).

Proposes metrics for evaluating the reliability of LLM structured outputs (JSON, YAML, etc.):
- Syntax Score: is the JSON valid?
- Type Score: do field types match the schema?
- Consistency Score: does the same query produce the same output across runs?

**Relevance**: Prism's gap_extract.md produces structured JSON output (claim, type, fill_source, query, risk, impact, confidence). STED's consistency scoring applies directly: running gap_extract multiple times on the same target should produce consistent gap classifications. This is a validation methodology for Prism's extraction step.

### 5.4 OpenAI Structured Output Confidence Gap

**Source**: OpenAI Developer Community, "Structured Output Confidence Score" (2025 discussion).

**Key gap**: OpenAI's structured outputs enforce schema compliance (JSON fields, types) but do NOT provide per-field confidence scores. Log probabilities exist at the token level but are not surfaced per structured field.

**Relevance**: This is the exact gap that Prism's knowledge_typed prism fills. Where OpenAI's structured outputs give you (field: value), Prism's knowledge_typed gives you (field: value, confidence: 0.7, source: "line 42", falsifiable_by: "api_docs"). Prism is doing in a prompt what structured output APIs haven't built yet.

---

## 6. Cognitive Science of Expertise — Abstract vs. Concrete Calibration

### 6.1 The Overconfidence Literature

**Sources**:
- "The Dunning-Kruger Effect and Its Discontents" (BPS, 2021)
- "Overconfidence in Probability and Frequency Judgments: A Critical Examination" (ResearchGate)
- Moore & Healy (2008): Three types of overconfidence — overestimation, overplacement, overprecision.

**Key finding**: Human overconfidence is domain- and granularity-dependent:
- **Overestimation**: believing your performance is better than it is. Worse for harder tasks.
- **Overprecision**: expressing unwarranted certainty in specific values. Worse for specific numerical claims than general directional claims.
- **Expert calibration**: Experts are better calibrated than novices within their domain, but may be WORSE calibrated when making specific claims outside their domain's data.

**Relevance**: This is the human psychology analog of Prism's P206. The conservation law `Specificity × Verifiability = Constant` maps to the "overprecision" form of overconfidence: the more specific the claim (narrow confidence interval), the more likely it's wrong. Human experts exhibit the same pattern as LLMs — better at abstract pattern recognition, worse at specific fact recall.

### 6.2 Abstract vs. Concrete Framing Effects

**Source**: "The Effect of Abstract versus Concrete Framing on Judgments" (PMC:5357666, 2017).

**Key finding**: Identical behaviors described abstractly vs. concretely elicit different attributional patterns. Abstract framing → biological/universal explanations (general claims). Concrete framing → psychological/situational explanations (specific claims). The framing changes WHICH explanatory framework people invoke, not just HOW confident they are.

**Relevance**: This is the cognitive science basis for Design Principle 15 in CLAUDE.md: "Code nouns are mode triggers, not domain labels." When Prism prompts use concrete vocabulary ("this code's"), they activate specific analytical frameworks. Abstract vocabulary ("this input's") allows drift. The abstract/concrete distinction is not just about confidence — it changes the TYPE of reasoning engaged.

### 6.3 LLM Overconfidence at Different Abstraction Levels

**Source**: "Mind the Confidence Gap: Overconfidence, Calibration, and Distractor Effects in Large Language Models" (arxiv:2502.11028, 2025).

**Key finding**: LLMs are better calibrated on abstract pattern questions than on specific factual questions — the same asymmetry as human experts. The model's ECE (Expected Calibration Error) is lower on conceptual questions than on specific recall questions.

**Relevance**: This is the direct LLM analog of `Specificity × Verifiability = Constant`. The academic literature measured it via calibration error; Prism discovered it via conservation law induction (running J1-J5 and observing the pattern). Both reach the same conclusion: LLM analysis is most reliable at the most abstract level, least reliable at the most specific.

**Key novelty of Prism's finding**: The academic result is descriptive (LLMs are less accurate on specific claims). Prism's P206 is predictive (the product of specificity × verifiability is CONSTANT, meaning you can trade one for the other but cannot increase both). This is a stronger claim — it's a conservation law, not just a correlation.

### 6.4 Metacognition in LLMs

**Source**: "Metacognition in LLMs and its Relation to Safety" (AGI Safety journal, 2025).

Studies whether LLMs can accurately assess the quality of their own outputs. Key finding: LLMs have some metacognitive ability (their self-assessments correlate with accuracy) but are systematically overconfident on confident-but-wrong outputs. The failure mode: high-confidence wrong answers and high-confidence correct answers are indistinguishable to the model's self-assessment.

**Relevance**: This validates why Prism's audit approach uses construction (adversarial attack on claims) rather than self-report (asking the model to rate its own confidence). Construction bypasses the metacognitive failure: by engineering a stress test, we force the model into a different operation that reveals uncertainty through structural fragility rather than self-rating.

---

## 7. Synthesis — Where Prism Leads, Where It Follows

### 7.1 What the Literature Has That Prism Lacks

| Academic Concept | Status in Prism | Gap |
|-----------------|-----------------|-----|
| Statistical coverage guarantees (conformal prediction) | Not implemented | Prism tiers are qualitative, not statistically calibrated |
| Calibration metrics (ECE, Brier score) | Not measured | No quantitative measurement of Prism's tier accuracy |
| Formal belief revision (AGM theory) | Not implemented | Prism re-runs rather than formally revising beliefs |
| Training-based self-awareness (EKBM) | Not applicable | Prism is prompt-only, cannot retrain |
| PROV-O formal provenance model | Partial (K1b planned) | `--provenance` flag not yet implemented |

### 7.2 What Prism Has That the Literature Lacks

| Prism Innovation | Academic Status | Why It Matters |
|-----------------|-----------------|----------------|
| Conservation law `Specificity × Verifiability = C` | Not found in any paper | Predictive, not merely descriptive. Implies trading rules. |
| Gap taxonomy with typed fill mechanisms | No equivalent | Not just "uncertain" — but WHERE to look for the answer |
| Adversarial construction audit | Not found | Bypasses metacognitive failure; different from sampling-based UQ |
| L12-G single-pass gap elimination | Not found | 0 confabulated claims at 1-call cost via three-phase prompt |
| Tier distribution as pipeline diagnostic | Not found | "Fewer ASSUMED claims in output = pipeline converged" |
| Domain-adaptive gap detection (P214) | Not found | Same prism works on code AND text, adapts gap types automatically |

### 7.3 Closest Academic Neighbors

| Prism Concept | Closest Academic Work | Distance |
|--------------|----------------------|----------|
| knowledge_boundary prism | EKBM (arxiv:2503.02233) | Moderate — different method (prompt vs fine-tuning), similar goal |
| knowledge_audit prism | Epistemic Anti-Patterns (AIQA 2025) | Close — both classify failure types, Prism uses adversarial construction |
| 5-tier confidence taxonomy | Epistemic Integrity Architecture (arxiv:2506.17331) | Close — parallel tier systems, different instantiation |
| knowledge_typed prism | Sounio `Knowledge<T>` type | Very close — same concept, Prism is prompt-level, Sounio is compiler-level |
| `Specificity × Verifiability = C` | GUM uncertainty propagation + overconfidence literature | Structurally equivalent, Prism formulation is stronger (conservation law) |
| Gap fill pipeline | RAG + KNOWNO | Complementary — RAG is the fill step, KNOWNO is the confidence threshold |
| Persistent KB (.deep/knowledge/) | Data Provenance Initiative | Different layer — Prism is runtime recovery, Initiative is training-time tracking |

---

## 8. Key Papers for Citation (if writing up J11)

1. **Farquhar et al. (2024)**: "Semantic Entropy Probes: Robust and Cheap Hallucination Detection in LLMs." ICML 2024. — Closest inference-time uncertainty method to Prism's approach.

2. **Wen et al. (2025)**: "Know Your Limits: A Survey of Abstention in Large Language Models." TACL 2025. — Comprehensive survey of what LLMs do when uncertain.

3. **"Uncertainty Quantification and Confidence Calibration in LLMs: A Survey"** (arxiv:2503.15850, 2025). — Most comprehensive UQ survey; frames the four sources of uncertainty.

4. **"Beyond Prediction: Structuring Epistemic Integrity in AI Reasoning Systems"** (arxiv:2506.17331, 2025). — Closest architectural parallel to Prism's epistemic tier system.

5. **"Parametric Modeling of Epistemic Anti-Patterns"** (AIQA 2025). — Formalizes what Prism found empirically about structured prompts reducing hallucination.

6. **"Enhancing LLM Reliability via Explicit Knowledge Boundary Modeling"** (arxiv:2503.02233, 2025). — Closest to Prism's "Sure/Unsure" classification, via fine-tuning vs. prompting.

7. **"Conformal Prediction for Natural Language Processing: A Survey"** (TACL 2024). — Coverage guarantees: what Prism's qualitative tiers lack but could be augmented with.

8. **"Prompt Provenance: Toward Traceable LLM Interactions"** (SSRN 2025). — Formal model for K1b (`--provenance` flag implementation).

9. **Moore & Healy (2008)**: Three forms of overconfidence. — Human calibration baseline for `Specificity × Verifiability = Constant`.

10. **Sounio Lang** (souniolang.org, v1.0.0-beta.5). — Independent discovery of same principle from compiler design angle.

---

## 9. Recommended Next Steps Based on Literature Gap

### 9.1 Quantitative Calibration of Tier Accuracy (High Priority)
The gap: Prism's 5-tier taxonomy is validated qualitatively (correct API calls, wrong statistics). The literature measures this quantitatively via ECE. **Recommendation**: Run 50 tier classifications against ground-truth verification (check each claim manually or via API). Measure tier accuracy per category. This becomes the empirical validation for J11.

### 9.2 Conformal Prediction Integration (Medium Priority)
Conformal prediction produces statistically guaranteed coverage sets. **Recommendation**: After Prism assigns a confidence score to each claim, use a calibrated conformal prediction wrapper to convert qualitative tiers to formal coverage intervals. This would let Prism say "90% confidence that this STRUCTURAL claim is correct" rather than just "STRUCTURAL (high confidence)." Implementation: requires a calibration set of 100-200 verified claim/tier pairs.

### 9.3 Semantic Entropy Pre-Filter (Low Priority, High Elegance)
Semantic entropy probes (Farquhar et al.) detect uncertain claims at inference time from hidden states, at near-zero cost. **Recommendation**: In a production pipeline, run SEP as a pre-filter before knowledge_boundary + knowledge_audit. Claims with low SE (high internal agreement) can be classified as STRUCTURAL without a full audit. Only high-SE claims route through the full audit pipeline. Cost reduction: potentially 50-70% fewer audit calls.

### 9.4 PPM-Compliant `--provenance` Flag (Planned in K1b)
The Prompt Provenance Model (SSRN 2025) defines exactly the provenance metadata Prism should track. **Recommendation**: Implement K1b with PPM-compliant output: for each claim, record (entity, derivedFrom, influencedBy, generatedAt, confidence). This makes Prism outputs formally compatible with the W3C PROV-O standard, enabling integration with enterprise provenance tracking systems.

---

*Sources: see individual section citations. All searches conducted March 15, 2026.*
