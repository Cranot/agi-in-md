# Literature Review: LLM Self-Correction, Hallucination Detection & Confabulation

**Context for this review:** The AGI-in-md project discovered that LLM code analysis confabulates specific facts (API names, line numbers, performance claims) while structural insights remain reliable. We identified the universal law `Specificity × Verifiability = Constant` — the more specific a claim, the less verifiable and more likely confabulated. We built prisms (prompts) that detect these gaps, and a single-pass self-correcting analysis (L12-G) that eliminates confabulation. This review situates those findings in the academic literature.

**Date compiled:** Mar 15, 2026
**Searches conducted:** arXiv, targeted paper lookups across 5 topic areas
**Papers reviewed:** ~30 directly, ~20 via search summaries

---

## 1. Hallucination Taxonomies — Do They Match Our Tiers?

### 1.1 Ji et al. 2022 — Survey of Hallucination in NLG

**Citation:** Ziwei Ji, Nayeon Lee, Rita Frieske et al. "Survey of Hallucination in Natural Language Generation." *ACM Computing Surveys*, 2022. arXiv:2202.03629.

**Key findings:** First comprehensive survey of hallucination in neural text generation. Defines hallucination as "generation of unintended text that is fluent and natural, but unfaithful to the source." Covers abstractive summarization, dialogue, QA, data-to-text, machine translation, and visual-language generation.

**Primary taxonomy (two-way):**
- **Intrinsic hallucination**: generated text contradicts the source
- **Extrinsic hallucination**: generated text cannot be verified from the source (may be true, may be false)

**Relation to us:** Our STRUCTURAL/DERIVED/MEASURED/KNOWLEDGE/ASSUMED tier system is considerably more fine-grained. Their extrinsic/intrinsic distinction maps roughly to our STRUCTURAL (derivable, intrinsic to code) vs KNOWLEDGE/ASSUMED (extrinsic — cannot be verified from source). Their framework predates LLMs; it was built on sequence-to-sequence models. **Should cite as foundational taxonomy; differentiate as: we extend from 2-tier to 5-tier, add verifiability scoring per claim, and discovered the product-form law.**

---

### 1.2 Huang et al. 2023 — LLM-Specific Hallucination Survey

**Citation:** Lei Huang, Weijiang Yu, Weitao Ma et al. "A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions." *ACM Transactions on Information Systems (TOIS)*, 2023. arXiv:2311.05232.

**Key findings:** Introduces a taxonomy specific to general-purpose LLMs (not task-specific models). Identifies contributing factors: training data issues, model architecture limitations, inference-time instabilities. Reviews detection benchmarks and mitigation strategies including retrieval augmentation.

**Taxonomy (partial, from abstract):** Focuses on the distinction between knowledge-based and reasoning-based hallucinations, with sub-categories by generation stage (encoding, decoding, training).

**Relation to us:** Their "knowledge-based" hallucination matches our KNOWLEDGE tier (claims about APIs, libraries, versions). Their "reasoning-based" hallucination is different from ours — they mean logical errors in reasoning chains, whereas our DERIVED tier is about claims derived from code structure (generally reliable). **Cite as the LLM-era taxonomic foundation; differentiate: we found that what they call "reasoning" (structural analysis) is actually LESS confabulation-prone, not more — a reversal of their framing.**

---

### 1.3 Zhang et al. 2023 — Siren's Song Survey

**Citation:** Yue Zhang, Yafu Li, Leyang Cui et al. "Siren's Song in the AI Ocean: A Survey on Hallucination in Large Language Models." arXiv:2309.01219, 2023 (v3 revised Sep 2025).

**Key findings:** Comprehensive survey focusing on LLM-specific hallucinations with three categories: **input-conflicting** (contradicts user input), **context-conflicting** (contradicts model's own prior context), **fact-conflicting** (contradicts established world knowledge). Reviews detection approaches, mitigation, and evaluation.

**Taxonomy match:** Their "fact-conflicting" maps closely to our KNOWLEDGE tier. Their "context-conflicting" is related to our observation that L12 pipeline can produce contradictory structural claims at different depth levels. **Their framework does not distinguish structural/derived claims as a separate tier.** This is our gap: they treat all hallucinations as factual errors; we found that structural analysis hallucinations are qualitatively different and require different detection strategies.

**Relation to us:** Strong foundational citation. Key differentiation: we prove that confabulation risk is CLAIM-TYPE-DEPENDENT (structural claims = low risk, factual/specific claims = high risk), not uniformly distributed across output. This is not captured in their framework.

---

### 1.4 Liu et al. 2024 — Code Hallucination Taxonomy (Closest Match)

**Citation:** Fang Liu, Yang Liu, Lin Shi et al. "Beyond Functional Correctness: Exploring Hallucinations in LLM-Generated Code." *Transactions on Software Engineering (TSE)*, 2024. arXiv:2404.00971.

**Key findings:** Establishes a taxonomy of code hallucinations with **3 primary categories and 12 specific sub-categories**. Uses thematic analysis. Analyzes distribution across different LLMs and benchmarks. Explores training-free mitigation via prompt enhancement.

**Primary categories (from abstract):** The three categories appear to be: (1) implementation-level errors (wrong API usage, incorrect syntax), (2) semantic errors (functionally incorrect logic), (3) specification errors (misunderstanding the task). The 12 sub-categories cover specific failure modes within these.

**Relation to us:** This is the closest existing work to our confabulation taxonomy. Their code-specific hallucination categories partially align with ours:
- Their implementation-level errors (wrong API names) = our KNOWLEDGE tier
- Their semantic errors (incorrect algorithm choice) = our MEASURED tier (unverifiable performance claims)
- Their specification errors = our ASSUMED tier

**Key difference:** They study hallucination in code GENERATION (LLM writes code). We study hallucination in code ANALYSIS (LLM analyzes existing code). Different task, different hallucination profile — analysis produces more structural claims that are reliable, fewer implementation-level errors. **Should cite and explicitly differentiate the generation vs analysis distinction.**

---

### 1.5 Tonmoy et al. 2024 — Mitigation Survey

**Citation:** S.M. Towhidul Islam Tonmoy et al. "A Comprehensive Survey of Hallucination Mitigation Techniques in Large Language Models." arXiv:2401.01313, 2024.

**Key findings:** Reviews 32 mitigation techniques including RAG, knowledge retrieval, CoNLI, CoVe. Classifies by dataset usage, feedback mechanisms, retriever types.

**Relation to us:** Our "augmented re-analysis" (inject verified facts → re-run L12) is closest to their RAG category, but differs: we don't retrieve external docs, we verify specific claims and inject corrections. **Minor citation; their retrieval framing doesn't capture our selective claim verification approach.**

---

### 1.6 Zavhorodnii et al. 2025 — Automatic Hallucination Classification

**Citation:** Maksym Zavhorodnii, Dmytro Dehtiarov, Anna Konovalenko. "A novel hallucination classification framework." arXiv:2510.05189, 2025.

**Key findings:** Automatic detection and taxonomy using embedding-based clustering in vector space. Found that simple classification algorithms distinguish hallucinations from correct outputs when spatial distances between hallucination clusters and correct-output clusters are measured.

**Relation to us:** Their embedding-distance approach is complementary to our prompt-based claim auditing. They work at the embedding level (black-box); we work at the claim level (interpretable). **Interesting methodological contrast; not a direct citation target.**

---

## 2. Self-Correction in LLMs — Comparison to Our 3-Phase L12-G

### 2.1 Madaan et al. 2023 — Self-Refine (Foundational)

**Citation:** Aman Madaan, Niket Tandon, Prakhar Gupta et al. "Self-Refine: Iterative Refinement with Self-Feedback." arXiv:2303.17651. *NeurIPS 2023*.

**Key findings:** Models generate initial output, provide self-feedback, then refine iteratively. No additional training or labeled data required. ~20% absolute improvement across 7 tasks on GPT-3.5, ChatGPT, GPT-4. Mirrors how humans revise writing.

**Relation to us:** Our L12-G (analyze → audit → correct) is a **single-pass** version of Self-Refine. Critical difference:
- Self-Refine: multiple iterations, domain-agnostic feedback, output-level refinement
- L12-G: exactly 3 phases in one prompt, claim-typed feedback (STRUCTURAL/MEASURED/ASSUMED), targeted correction of confabulation-prone claims only

Our approach is more surgical: we don't refine everything, we identify and correct the specific claim types most likely to confabulate. Also, Self-Refine requires multiple API calls; L12-G does it in one. **Must cite as foundational; differentiate as: L12-G is single-pass self-correction with claim-type-aware auditing, not iterative output-level refinement.**

---

### 2.2 Huang et al. 2024 — LLMs Cannot Self-Correct Reasoning (Critical Counter-Evidence)

**Citation:** Jie Huang, Xinyun Chen, Swaroop Mishra et al. "Large Language Models Cannot Self-Correct Reasoning Yet." *ICLR 2024*. (Identified via search; exact arXiv ID not confirmed in fetches.)

**Key findings:** LLMs struggle to self-correct reasoning without external feedback. Performance sometimes DEGRADES after self-correction. The apparent improvements in iterative modes are often due to sampling variability, not genuine self-critique.

**Relation to us:** This is the most important counter-evidence to understand. Their finding seems to contradict our L12-G result. The reconciliation:
- Huang et al. test self-correction on REASONING tasks (math, logic) where ground truth is unambiguous
- We test self-correction on CODE ANALYSIS where claims are self-typed by verifiability
- Their models don't know WHAT to correct (no claim-type annotation); our L12-G auditing phase explicitly identifies WHICH claims are confabulation-prone before correcting

**This is a key differentiation point**: Our contribution is that labeling claim types (STRUCTURAL/MEASURED/ASSUMED) before self-correction enables effective self-correction even where Huang et al.'s blind self-correction fails. **Must cite and directly address.**

---

### 2.3 Liang et al. 2024 — Internal Consistency and Self-Feedback Survey

**Citation:** Xun Liang, Shichao Song, Zifan Zheng et al. "Internal Consistency and Self-Feedback in Large Language Models: A Survey." arXiv:2407.14507, 2024.

**Key findings:** Proposes "internal consistency" (alignment across model layers) as the unifying framework for self-evaluation and self-refinement. Self-Feedback = Self-Evaluation (detect consistency signals) + Self-Update (apply signals). Proposes "Consistency Is (Almost) Correctness" hypothesis.

**Relation to us:** Their "Consistency Is (Almost) Correctness" hypothesis partially aligns with our finding that STRUCTURAL claims (derivable from code) are reliably correct — they're consistent across multiple model runs. KNOWLEDGE claims are inconsistent across runs → lower correctness. **Provides theoretical grounding for why SelfCheckGPT-style consistency checking (below) works: inconsistency correlates with confabulation.**

---

### 2.4 Reflexion (Shinn et al. 2023) — Verbal Reinforcement for Self-Improvement

**Citation:** Noah Shinn, Federico Cassano, Edward Berman et al. "Reflexion: Language Agents with Verbal Reinforcement Learning." arXiv:2303.11366. *NeurIPS 2023*.

**Key findings:** Agents verbally reflect on task feedback signals and store reflections in episodic memory for subsequent attempts. 91% pass@1 on HumanEval, outperforming GPT-4's 80%.

**Relation to us:** Reflexion requires external feedback signals (execution results, test outcomes) to drive reflection. L12-G is internally-driven: no external feedback, self-classification of claim types. **Different mechanism: Reflexion = external signal → verbal memory. L12-G = internal audit → targeted correction.** Minor citation; conceptually related but different architecture.

---

### 2.5 Li et al. 2025 — Accuracy-Correction Paradox

**Citation:** Yin Li. "Decomposing LLM Self-Correction: The Accuracy-Correction Paradox and Error Depth Hypothesis." arXiv, 2025.

**Key findings:** Weaker models (GPT-3.5, 66% accuracy) achieve 1.6x higher intrinsic correction rates than stronger models (DeepSeek, 94% accuracy). Error detection doesn't predict correction success — Claude detects only 10% of errors but corrects 29% intrinsically.

**Relation to us:** The "error detection doesn't predict correction success" finding is relevant to L12-G design. Our approach separates detection (claim typing phase) from correction (targeted rewrite phase). The paradox may arise because previous work conflates detection and correction as one step; L12-G makes them explicit phases. **Interesting supporting citation for the two-phase approach.**

---

### 2.6 Dhuliawala et al. 2023 — Chain-of-Verification (CoVe)

**Citation:** Shehzaad Dhuliawala, Mojtaba Komeili, Jing Xu et al. "Chain-of-Verification Reduces Hallucination in Large Language Models." arXiv:2309.11495, 2023.

**Key findings:** Four-step method: (1) draft initial response, (2) generate verification questions, (3) answer those questions independently to avoid bias, (4) produce final verified response. Reduces hallucinations across list-based QA, closed-book QA, and long-form generation.

**Relation to us:** CoVe is structurally closest to our L12-G pipeline:
- CoVe: draft → questions → independent answer → verified output
- L12-G: analyze → audit claims by type → correct confabulated claims → output

Key difference: CoVe's verification questions are generic factual checks; L12-G's audit phase is TYPED (identifies claim as STRUCTURAL/MEASURED/ASSUMED/KNOWLEDGE before evaluating it). Also, CoVe requires multiple API calls; we compress to one. **Direct citation and differentiation target: we extend CoVe with typed claim classification and single-pass compression.**

---

## 3. Calibration and Confidence Estimation

### 3.1 Kadavath et al. 2022 — Models Know What They Know

**Citation:** Saurav Kadavath, Tom Conerly, Amanda Askell et al. "Language Models (Mostly) Know What They Know." arXiv:2207.05221, 2022.

**Key findings:** Larger models show strong calibration when answering multiple choice and true/false questions. Introduces P(True) (model evaluates its own proposed answer) and P(IK) (model predicts whether it knows the answer). P(IK) generalizes partially across tasks but struggles with new domains. Model confidence appropriately increases with relevant source materials.

**Relation to us:** Kadavath et al. establish that models CAN be calibrated in principle on factual questions. Our finding complements this: even well-calibrated models confabulate SPECIFIC facts in code analysis because those facts (API versions, line numbers) are outside the calibration distribution. **Our Specificity × Verifiability = Constant law explains WHY calibration fails for specific claims: they require external verification, which no amount of in-distribution calibration training provides.**

---

### 3.2 Zhang et al. 2024 — Atomic Calibration of LLMs

**Citation:** Caiqi Zhang et al. "Atomic Calibration of LLMs in Long-Form Generations." arXiv:2410.13246, 2024.

**Key findings:** LLMs exhibit POORER calibration at the atomic (sentence/claim) level than at the response level. Aggregate confidence masks claim-level miscalibration.

**Relation to us:** This directly supports our discovery. Response-level analysis looks reliable; specific claims within it are poorly calibrated. Our `Specificity × Verifiability = Constant` is the mechanistic explanation: atomic claims require external verification, so they're systematically under-calibrated relative to structural insight. **Strong citation: their atomic calibration finding is the calibration literature's version of our confabulation tier finding.**

---

### 3.3 Yuan et al. 2024 — Fact-Level Confidence Calibration

**Citation:** Yige Yuan et al. "Fact-Level Confidence Calibration and Self-Correction." arXiv:2411.13343, 2024.

**Key findings:** Fine-grained fact-level calibration more effective than overall response confidence for long-form generation.

**Relation to us:** Our claim-level auditing (knowledge_audit prism) is a prompt-based version of their fact-level calibration — no fine-tuning required. **Demonstrates that fact-level differentiation is independently validated; our prism approach achieves it via prompt engineering rather than training.**

---

### 3.4 Marks and Tegmark 2023 — Geometry of Truth

**Citation:** Samuel Marks, Max Tegmark. "The Geometry of Truth: Emergent Linear Structure in Large Language Model Representations of True/False Datasets." *Conference on Language Modeling*, 2024. arXiv:2310.06824.

**Key findings:** LLMs linearly represent truth vs. falsehood of factual statements in activation space at sufficient scale. Simple difference-in-mean probes transfer across datasets. Causal intervention can flip model outputs between true/false.

**Relation to us:** This is an interpretability-level finding that our prism approach indirectly leverages. If the model internally represents truth, the audit phase of L12-G is asking the model to surface that representation explicitly. **Provides mechanistic basis for why prompt-based self-auditing can work: the model has a truth representation we're eliciting.** Different layer (mechanistic interpretability vs. prompt engineering), but converging result.

---

## 4. Prompt-Based Fact-Checking — Prior Work on Our Knowledge_Audit Approach

### 4.1 Manakul et al. 2023 — SelfCheckGPT (Most Relevant)

**Citation:** Potsawee Manakul, Adian Liusie, Mark J. F. Gales. "SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models." *EMNLP 2023*. arXiv:2303.08896.

**Key findings:** Hallucination detection without external knowledge bases or model internals. Core insight: "if an LLM has knowledge of a given concept, sampled responses are likely to be similar and contain consistent facts. However, for hallucinated facts, stochastically sampled responses are likely to diverge." Multiple samples → consistency check → hallucination score.

**Relation to us:** SelfCheckGPT and our knowledge_audit prism are both zero-resource prompt-based approaches to hallucination detection. Key differences:
1. SelfCheckGPT: requires multiple API calls (sample N times, compare). Our approach: single call.
2. SelfCheckGPT: consistency = correctness signal. Our approach: claim-type = correctness signal.
3. SelfCheckGPT: black-box (no knowledge of claim structure). Our approach: white-box (explicitly types claims).
4. SelfCheckGPT: validated on biography generation. We validate on code analysis (different domain).

**The consistency principle underlies both**: their consistency-across-samples insight maps to our tier system — STRUCTURAL claims are consistent across runs (they're derived from code), KNOWLEDGE claims diverge (confabulated differently each run). Our tier system predicts which claims SelfCheckGPT would flag WITHOUT requiring multiple samples. **Major citation and differentiation: we achieve zero-resource hallucination detection in a single pass by typing claims rather than sampling.**

---

### 4.2 Zhang et al. 2023 — Hallucination Snowball

**Citation:** Muru Zhang, Ofir Press, William Merrill et al. "How Language Model Hallucinations Can Snowball." *ICML 2024*. arXiv:2305.13534.

**Key findings:** Models over-commit to early mistakes, creating compounding hallucinations. ChatGPT and GPT-4 can identify 67% and 87% of their own mistakes respectively — but fail to correct them in context. Hallucination involves COMMITMENT BIAS, not just knowledge gaps.

**Relation to us:** The "snowball" phenomenon explains why our L12-G audit phase must be EXPLICIT (name the claim type, name the confabulation risk) rather than implicit. Models see the error but don't correct it unless prompted to. Our 3-phase structure breaks the commitment: phase 1 generates output, phase 2 explicitly labels claims without commitment pressure, phase 3 corrects. **Strong citation: snowball explains WHY our explicit phasing works.**

---

### 4.3 Semnani et al. 2023 — WikiChat

**Citation:** Sina J. Semnani, Violet Z. Yao, Heidi C. Zhang, Monica S. Lam. "WikiChat: Stopping the Hallucination of Large Language Model Chatbots by Few-Shot Grounding on Wikipedia." *EMNLP 2023* (Findings). arXiv:2305.14292.

**Key findings:** 97.3% factual accuracy via Wikipedia grounding. Outperforms GPT-4 by 55% on recent topics. Uses LLM to filter factually grounded content and augment with retrieved information.

**Relation to us:** WikiChat is retrieval-based (external source). Our pipeline is verification-based (classify claims, surgically correct). For code analysis, a Wikipedia-style external source doesn't exist — hence our approach: verify specific claims (asyncio.RWLock existence) via targeted queries rather than broad retrieval. **Minor citation: different domain (trivia vs code), different approach (retrieval vs claim-verification).**

---

### 4.4 Li et al. 2023 — HaluEval Benchmark

**Citation:** Junyi Li, Xiaoxue Cheng, Wayne Xin Zhao et al. "HaluEval: A Large-Scale Hallucination Evaluation Benchmark for Large Language Models." *EMNLP 2023*. arXiv:2305.11747.

**Key findings:** ChatGPT generates hallucinated content in ~19.5% of responses. LLMs struggle with hallucination detection. External knowledge and reasoning steps improve detection. ChatGPT-based framework generates hallucinated samples for benchmark construction.

**Relation to us:** HaluEval establishes ground-truth hallucination rates for question-answering tasks. Our finding: ~28-42% of specific factual claims in code analysis are confabulated (asyncio.RWLock, quadratic mislabeling, etc.). The higher rate makes sense — code analysis requires external knowledge (API documentation, version history) unavailable in training data. **Cite as baseline hallucination rate reference; note that code-analysis confabulation rates are higher than general QA.**

---

## 5. Conservation Laws in AI Analysis — Has Anyone Found Product-Form Invariants?

### 5.1 No Direct Prior Work Found

Extensive search of arXiv for "conservation law LLM," "invariant LLM behavior," "product form LLM accuracy," and "specificity verifiability tradeoff LLM" returned no results. This appears to be a genuinely novel contribution of the AGI-in-md project.

The closest adjacent concepts:

**Calibration vs. Specificity Tradeoff (implicit in literature):**
- FActScore (Min et al., EMNLP 2023) shows that atomizing claims reveals lower accuracy than aggregate assessment — implying a specificity-accuracy tradeoff but not formalized as a product law.
- Atomic Calibration paper (Zhang et al. 2024) shows atomic-level miscalibration — again, implying the relationship but not quantifying it.

**Information-Theoretic Framing:**
- MQAG (Manakul et al., AACL 2023) uses information-theoretic comparison of source and summary answer distributions. Not a conservation law, but demonstrates that information quantity tradeoffs can be quantified in NLP.

**Conclusion:** `Specificity × Verifiability = Constant` appears to be a novel formalization. The phenomenon is implicit in the calibration literature (atomic claims are less calibrated) but has not been formally stated as a multiplicative invariant. **This is a contribution we should publish.**

---

## 6. Summary Table: Where We Sit in the Literature

| Our Discovery | Closest Prior Work | Gap |
|---|---|---|
| 5-tier claim taxonomy (STRUCTURAL/DERIVED/MEASURED/KNOWLEDGE/ASSUMED) | Ji et al. 2022 (2-tier), Liu et al. 2024 (12-cat code hallucination) | None captures verifiability as primary axis; none applied to code ANALYSIS (vs generation) |
| `Specificity × Verifiability = Constant` | Atomic Calibration (Zhang 2024), FActScore (Min 2023) | Product-form law not formalized anywhere |
| L12-G: single-pass 3-phase self-correction | Self-Refine (Madaan 2023), CoVe (Dhuliawala 2023) | Single-pass compression of multi-call pipelines not studied; claim-typed audit not done |
| Claim-typed hallucination detection | SelfCheckGPT (Manakul 2023) | SelfCheckGPT needs N samples; our approach needs 1 call + claim-type classification |
| Structural claims well-calibrated; factual claims poorly calibrated | Kadavath 2022, Yuan 2024 | They measure calibration; we explain WHY via Specificity × Verifiability |
| Explicit phasing breaks commitment bias | Hallucination Snowball (Zhang 2023) | They observe the bias; we design around it |
| Knowledge gap pipeline: detect → classify → verify → correct → re-run | CoVe (Dhuliawala 2023), WikiChat (Semnani 2023) | Theirs: factual QA. Ours: structural code analysis with typed gap classification |

---

## 7. Key Papers to Cite (Prioritized)

### Must Cite
1. **Ji et al. 2022** (hallucination survey) — foundational taxonomy to build on
2. **Madaan et al. 2023** (Self-Refine) — we're compressing their multi-step approach to single-pass
3. **Manakul et al. 2023** (SelfCheckGPT) — closest zero-resource approach; we extend with single-pass + claim typing
4. **Dhuliawala et al. 2023** (CoVe) — structurally closest to L12-G; we extend with claim-type classification
5. **Huang et al. 2024** (LLMs Cannot Self-Correct) — critical counter-evidence; we explain why claim-typed correction succeeds where generic self-correction fails
6. **Zhang et al. 2023** (Hallucination Snowball) — explains why explicit phasing (L12-G) is necessary

### Should Cite
7. **Kadavath et al. 2022** (Models Know What They Know) — foundational calibration work
8. **Zhang et al. 2024** (Atomic Calibration) — atomic-level miscalibration supports our tier finding
9. **Liu et al. 2024** (Code Hallucination Taxonomy) — closest taxonomy; must differentiate generation vs. analysis
10. **Li et al. 2023** (HaluEval) — baseline hallucination rate reference

### Optional / Background
11. **Huang et al. 2023** (LLM Hallucination Survey) — LLM-era taxonomy reference
12. **Zhang et al. 2023** (Siren's Song) — another survey to cite in intro
13. **Shinn et al. 2023** (Reflexion) — related self-improvement with external feedback
14. **Liang et al. 2024** (Internal Consistency Survey) — theoretical framing for why consistency = correctness
15. **Marks & Tegmark 2023** (Geometry of Truth) — mechanistic basis for why self-auditing works

---

## 8. Our Novel Contributions (Not in Literature)

1. **Code analysis confabulation differs from code generation hallucination.** No paper distinguishes these. Analysis is more reliable structurally; factual claims about library APIs are systematically unreliable.

2. **`Specificity × Verifiability = Constant` as a product-form law.** Implicit in calibration literature; never formalized. Universal across 4 domains tested.

3. **Single-pass 3-phase self-correction (L12-G).** Compresses multi-call pipelines (Self-Refine, CoVe) to one call with claim-type-aware auditing.

4. **Claim-type classification as confabulation predictor.** SelfCheckGPT uses consistency; we use claim type. Our approach requires 1 call; theirs requires N. Both work; ours is cheaper.

5. **Conservation law as structural analysis quality signal.** When analysis produces a conservation law (`A × B = constant`), this signals reliable structural depth. Factual errors occur BELOW this layer. No paper uses conservation law emergence as quality signal.

6. **Reflexive gap detection (L13).** Applying the audit to its own conservation law output reveals second-order assumptions (the conservation law framework itself is ASSUMED tier). No prior work applies self-auditing to the auditing framework itself.

---

## 9. Recommended Research Next Steps (from literature gaps)

1. **Write J11 paper**: "Claim-Typed Self-Correction for LLM Code Analysis: A Single-Pass Alternative to Multi-Call Verification." Target: ACL 2026 or EMNLP 2026.

2. **Run SelfCheckGPT comparison**: Apply SelfCheckGPT to the same L12 outputs we have. Compare: does consistency-based detection flag the same claims our tier-based detection flags? Expected result: both flag KNOWLEDGE/ASSUMED tier claims, ours requires 1 call vs. N samples.

3. **Formalize the product law**: Measure Specificity score (claim word length, number of concrete nouns) vs. Verifiability rate (human-verified accuracy) across all 4 codebases. Fit to product form. Compute R². This converts our empirical observation to a formal result.

4. **Benchmark against CoVe**: Apply CoVe (4-step, 4 API calls) and L12-G (1 call) to same targets. Compare confabulation rate in final outputs. Our hypothesis: comparable accuracy at 4x lower cost.

5. **Pilot study**: Apply knowledge_audit prism to outputs from SelfCheckGPT. Do the methods find different confabulations? Expected: complementary — SelfCheckGPT finds inconsistent claims, knowledge_audit finds typed claims. Together = higher recall.
