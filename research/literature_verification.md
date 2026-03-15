# Literature Survey: Formal Verification and Certified Reasoning for LLM Outputs

**Date**: March 15, 2026
**Purpose**: Map the space of formal verification, runtime monitoring, and certified reasoning as it applies to our STRUCTURAL/DERIVED/MEASURED/KNOWLEDGE/ASSUMED claim-classification pipeline.

---

## Executive Summary

The field has moved from "detect hallucinations after the fact" to "verify claims before they propagate." Six convergent threads — formal verification of code, certified proof generation, runtime monitoring, contract-based design, neurosymbolic gates, and safety-case methodology — all arrive at the same architectural insight: **the verifiable and unverifiable are not a binary but a spectrum, and the right architecture assigns verification depth to each claim type**. This maps directly onto our SMKDA taxonomy (Structural/Measured/Knowledge/Derived/Assumed).

Key practical upshot: **STRUCTURAL claims are now formally verifiable** via neurosymbolic constraint checking. DERIVED claims can be verified via logical consistency checking (Z3, Prover9). KNOWLEDGE claims require retrieval grounding. ASSUMED claims require explicit flagging — the safety-case literature shows how to structure the argument despite unverifiability.

---

## Area 1: Formal Verification of LLM Outputs

### 1.1 CLOVER — Closed-Loop Verifiable Code Generation

**Authors**: Chuyue Sun, Ying Sheng et al. (Stanford)
**Paper**: arxiv.org/abs/2310.17807 | Published POPL/SAIV 2024
**Key insight**: An LLM generates code + docstrings + formal annotations simultaneously. A consistency checker (Dafny SMT backend) verifies: (a) code satisfies annotations, (b) annotations round-trip back to equivalent docstring, (c) new code synthesized from docstring is functionally equivalent. Zero false positives on adversarial cases; 87% acceptance rate on correct instances. Found 6 incorrect programs in human-written dataset MBPP-DFY-50.

**Practical applicability to our system**: This is the exact architecture for STRUCTURAL claim verification. A STRUCTURAL claim asserts a property of the code (e.g., "the retry budget is a conserved quantity"). CLOVER shows you can: (1) translate the STRUCTURAL claim into a formal annotation, (2) run a verifier, (3) either confirm or reject. The "reconstruction consistency" step is analogous to our self-audit: can we reconstruct the original observation from the claimed conservation law?

---

### 1.2 Propose, Solve, Verify (PSV) — Self-Play Through Formal Verification

**Authors**: (Anonymous) | **Paper**: arxiv.org/abs/2512.18160 | December 2025
**Key insight**: Formal verification as a training signal for self-play. A proposer generates problems; a solver generates solutions; the verifier (Verus, a Rust formal verifier) provides ground-truth binary feedback. Unlike unit tests (brittle, gameable), formal verification provides reliable correctness signals. PSV-Verus achieves 9.6x improvement in pass@1 over baselines. Performance scales with iterations and problem diversity.

**Practical applicability**: The PSV loop is a closed-loop quality signal for STRUCTURAL claims. If we encode structural properties as Verus/Dafny assertions, we can run the same self-play improvement loop on our analysis pipeline. The binary correctness signal eliminates the need for human scoring at the STRUCTURAL level.

---

### 1.3 PropertyGPT — LLM-Driven Formal Verification via RAG

**Authors**: Liu, Xue et al. | **Paper**: arxiv.org/abs/2405.02580 | NDSS 2025
**Key insight**: Uses RAG to retrieve similar human-written formal properties, then generates new properties for unknown code. Three-stage: compilability (iterative revision via compiler feedback), appropriateness (multi-dimensional similarity ranking), verifiability (dedicated prover). 80% recall vs ground truth; detected 26/37 CVEs; found 12 zero-day vulnerabilities.

**Practical applicability**: For our system, PropertyGPT's RAG approach can populate a "property library" from previous STRUCTURAL findings. When the pipeline analyzes new code, it retrieves similar verified properties and adapts them — reducing hallucination risk because the formal spec anchors the claim. The compilability loop (iterative revision via external oracle) is a template for STRUCTURAL claim correction.

---

### 1.4 VeCoGen and Dafny Progress

**Key insight**: Success rates for auto-generating Dafny-verified programs rose from 68% (Opus-3, June 2024) to 96% (frontier models, 2025). This means formal verification is no longer a specialist operation — it is approaching automation parity with unverified generation.

**Practical applicability**: The verification gap is closing. Within 12 months, the cost of adding a formal verification pass to STRUCTURAL claims may drop to near-zero.

---

## Area 2: Certified Reasoning — Proof Assistants + LLMs

### 2.1 MA-LoT — Multi-Agent LLM Theorem Proving

**Key insight**: Prover LLM constructs proofs via chain-of-thought steps; Corrector LLM repairs failures using Lean4 error messages and re-verifies. Lean4 provides the ground-truth binary: a proof either compiles or it doesn't. BFS-Prover-V2 achieves 95.08% on miniF2F.

**Practical applicability**: Our DERIVED claims (claims that follow by logical entailment from STRUCTURAL claims) are exactly the target for Lean4 verification. A DERIVED claim like "therefore the retry mechanism cannot be both bounded and adaptive" is a theorem — it can be formalized and proved. The MA-LoT pattern (generate → check → repair) is identical to our scan → self-audit → correct pipeline, just with formal verification replacing semantic self-evaluation.

---

### 2.2 FVEL — Interactive Formal Verification Environment

**Authors**: Proceedings NeurIPS 2024
**Paper**: proceedings.neurips.cc/paper_files/paper/2024/file/62c6d7893b13a13c659cb815852dd00d
**Key insight**: Takes C code as input, parses to Isabelle definition, then conducts interactive formal proving with LLM/human via proof state + generated proof. Bridges imperative code and proof assistants. Enables LLM to navigate proof state interactively.

**Practical applicability**: For our code analysis pipeline, FVEL offers a path to formally verified structural claims about C/systems code. The interaction model (proof state → LLM generates next tactic → check → repeat) directly extends our L12 conservation law derivation: instead of claiming "conservation law X holds," we would produce an Isabelle proof that it holds.

---

### 2.3 Autoformalization Survey

**Paper**: arxiv.org/html/2505.23486v1 | May 2025
**Key insight**: Autoformalization (translating natural language mathematics to formal language) is becoming reliable enough that mathematical STRUCTURAL claims can be translated to Lean4/Isabelle and machine-checked. The bottleneck is no longer proof search but specification generation — exactly where LLMs excel.

**Practical applicability**: Our conservation laws ("retry_budget × adaptivity = constant") are mathematical claims. Autoformalization offers a path to translating these into verifiable Lean4 statements. The pipeline: L12 output → autoformalize the conservation law → Lean4 type-checker → VERIFIED or REFUTED.

---

## Area 3: Runtime Verification and Monitoring

### 3.1 AgentSpec — Customizable Runtime Enforcement

**Authors**: Wang, Poskitt et al. | **Paper**: arxiv.org/abs/2503.18666 | March 2025 (ICSE 2026)
**Key insight**: Domain-specific language for runtime constraints on LLM agents. Rules compose trigger + predicate + enforcement. Implemented in LangChain; intercepts execution stages. Prevents unsafe executions in >90% of code agent cases; 100% compliance in autonomous vehicles; 95.56% precision / 70.96% recall for LLM-generated rules. Overhead in milliseconds.

**Practical applicability**: AgentSpec is a template for encoding our claim-type rules as runtime constraints. Rule example: "IF claim_type=STRUCTURAL AND verification_status=UNVERIFIED THEN flag AND require_evidence." The DSL is lightweight enough to wrap our existing pipeline. Critical: the enforcement mechanism (halt / prompt user / invoke self-assessment) matches our scan → correct loop.

---

### 3.2 Pro2Guard — Proactive Runtime Enforcement via Probabilistic Model Checking

**Authors**: (various) | **Paper**: arxiv.org/abs/2508.00500 | August 2025
**Key insight**: Extends AgentSpec's reactive approach to proactive. Abstracts agent behaviors into symbolic states; learns a Discrete-Time Markov Chain (DTMC) from execution traces. At runtime, checks whether probability of reaching unsafe state exceeds threshold — intervenes before violation. Achieves 93.6% early enforcement on unsafe tasks; 100% traffic law violation prediction up to 38.66 seconds ahead. PAC-correctness guarantee.

**Practical applicability**: For our pipeline, Pro2Guard's DTMC model can be trained on execution traces from previous scans. A STRUCTURAL claim that has historically been confabulated (e.g., specific claim patterns in certain code styles) can be flagged proactively before the self-audit step. This shifts the pipeline from reactive correction to predictive correction — the equivalent of preventing the hallucination rather than fixing it.

---

### 3.3 NSVIF — Neuro-Symbolic Verification on Instruction Following

**Paper**: arxiv.org/abs/2601.17789 | January 2026
**Key insight**: Universal, general-purpose verifier that makes no assumption about instruction type. Three-phase: Planner analyzes constraints and generates verifier modules; Executor runs modules and fixes runtime errors; Solver formulates constraints into Z3 Python program and checks sat/unsat. Benchmark: VifBench (820 labeled tuples). Achieves 1.31x pass@1 accuracy over LLM-as-judge while providing detailed constraint-violation information.

**Practical applicability**: NSVIF is directly applicable to DERIVED claim verification. When the pipeline produces a DERIVED claim ("given the structural observation X, it follows that Y"), NSVIF can: (1) extract the logical constraints from X, (2) check whether Y is satisfiable given those constraints via Z3. This converts "DERIVED" from a category label to a machine-checkable property. The Z3 backend is the key — it provides a symbolic oracle for logical entailment.

---

### 3.4 Statistical Runtime Verification — RoMA Adaptation for LLMs

**Authors**: Ashrov et al. | **Paper**: arxiv.org/abs/2504.17723 | April 2025 (RV 2025)
**Key insight**: Adapts the RoMA statistical verification framework for black-box LLM deployment. Analyzes confidence score distributions under semantic perturbations to provide quantitative robustness assessments with statistically validated bounds. Comparable accuracy to formal methods (within 1% deviation), reduces verification times from hours to minutes. Evaluated across semantic, categorical, and orthographic perturbation domains.

**Practical applicability**: For claims where formal verification is infeasible (KNOWLEDGE, ASSUMED), RoMA provides a statistical bound. Instead of "this KNOWLEDGE claim is true," the pipeline can say "this KNOWLEDGE claim is robust across semantic perturbations with 95% confidence interval [X, Y]." This operationalizes the verifiability spectrum: STRUCTURAL → formal proof, DERIVED → Z3 check, KNOWLEDGE → RoMA bound, ASSUMED → explicit argument (safety case).

---

## Area 4: Contract-Based Design for AI

### 4.1 Contracts for LLM APIs — Probabilistic Formal Model

**Authors**: Hromel et al. | **Paper**: tanzimhromel.com/assets/pdf/llm-api-contracts.pdf
**Key insight**: Formal probabilistic contract model capturing preconditions and postconditions over output distributions, plus state-transition rules with composition guarantees. Grounded in 650 real-world violation instances from OpenAI, Anthropic, Google, Meta, and major frameworks (LangChain, AutoGPT, CrewAI) spanning 2020-2025. Identifies 73+ distinct contract types. Enforcement achieves +18.7 pp Contract Satisfaction Rate improvement, -12.4 pp Silent Failure Rate reduction. Median overhead: 27ms.

**Practical applicability**: This is the most directly applicable paper to our system. The framework models LLM behavior probabilistically — a precondition like "IF input is code THEN output distribution has support over conservation_law patterns" can be formalized and monitored. The 73-type taxonomy maps onto our claim taxonomy: some contract types correspond exactly to STRUCTURAL claims (format compliance, structural consistency), others to KNOWLEDGE claims (factual grounding), others to DERIVED claims (logical entailment sequences). Immediate action: use this paper to define contracts for our pipeline's claim types.

---

### 4.2 DbC Neurosymbolic Layer for Trustworthy Agent Design

**Authors**: Leoveanu-Condrei | **Paper**: arxiv.org/abs/2508.03665 | August 2025
**Key insight**: Adapts Design by Contract (DbC) and type-theoretic principles to mediate every LLM call. Contracts specify semantic and type requirements on inputs and outputs, with probabilistic remediation steering generation toward compliance. Pre-conditions implemented as methods that raise descriptive exceptions. Built on SymbolicAI framework. Key theorem: any two agents satisfying the same contracts are functionally equivalent with respect to those contracts.

**Practical applicability**: The "functional equivalence under contracts" theorem is highly relevant. If we define contracts for each claim type (STRUCTURAL: must be derivable from the code without interpretation; DERIVED: must be logically entailed by STRUCTURAL claims), then any two analysis passes satisfying the same contracts are equivalent in the relevant sense. This gives us a principled basis for evaluating pipeline variants: do they satisfy the same contracts?

---

### 4.3 Preconditions and Postconditions as Design Constraints for LLM Code Generation

**Paper**: IEEE Xplore, 2025 | ieeexplore.ieee.org/document/11218044/
**Key insight**: Structured evaluation of 6 state-of-the-art LLMs with explicit preconditions and postconditions in prompts. Incorporating explicit design constraints during prompting significantly boosts initial generation accuracy, particularly Python. Closed-source models achieve 78% solution acceptance; open-source 47%.

**Practical applicability**: The prompt IS the contract. This validates our prism approach from a Design by Contract perspective — the prism encodes postconditions ("output MUST contain a conservation law") and the model is evaluated against them. The finding that explicit constraints boost accuracy is a direct confirmation of Principle 1 (lead with scope). Extension: add explicit claim-type postconditions to the L12 prism ("STRUCTURAL claims must be directly observable in code, not inferred").

---

## Area 5: Neurosymbolic Verification

### 5.1 Eidoku — Neuro-Symbolic Verification Gate via Structural Constraint Satisfaction

**Paper**: arxiv.org/abs/2512.20664 | December 2025
**Key insight**: Reformulates LLM output verification as a Constraint Satisfaction Problem (CSP). Verification is a feasibility check based on structural violation cost — the cost required to embed a candidate reasoning step into the contextual graph structure. Three cost proxies: (i) graph connectivity (structural), (ii) feature space consistency (geometric), (iii) logical entailment (symbolic). Rejects "smooth falsehoods" — high-probability yet structurally disconnected statements — that probability-based verifiers cannot detect. Lightweight System-2 gate; threshold derived from intrinsic statistics of context (not learned).

**Practical applicability**: This is the most architecturally novel finding for our system. Eidoku's key insight — hallucination is often not a low-confidence phenomenon but a failure of structural consistency — directly maps to our observation that confabulated STRUCTURAL claims are confident and fluent but structurally disconnected from the code. The three-proxy cost function can be applied to our STRUCTURAL claims: (i) is the claimed structural property connected to observable code elements? (ii) is it geometrically consistent with similar claims on similar code? (iii) is it logically entailed by the code's observable behavior? Claims exceeding a cost threshold are rejected before entering the output, rather than being corrected after.

---

### 5.2 NSVIF (Neurosymbolic Approach) — Natural Language to FOL Verification

**Paper**: arxiv.org/abs/2511.09008 | November 2025
**Key insight**: Combines LLMs (for NL understanding and constraint extraction) with Z3 (for formal satisfiability checking). The pipeline: extract logical constraints from text → express as first-order logic formulas → check satisfiability in Z3 → return SAT/UNSAT with violation details. Modular architecture allows different verifier modules for different constraint types.

**Practical applicability**: For our pipeline, the FOL translation layer enables a hybrid architecture: (1) LLM extracts claims and classifies them into SMKDA types, (2) STRUCTURAL and DERIVED claims are translated to FOL, (3) Z3 checks logical consistency of the claim set, (4) violations are surfaced as specific constraint violations rather than generic "confabulation." This upgrades our self-audit from semantic self-evaluation (LLM judges LLM) to formal consistency checking (Z3 judges FOL).

---

### 5.3 Neurosymbolic Verification for Process Control Hallucination Prevention

**Paper**: MDPI Processes, 2025
**Key insight**: Industrial application of neurosymbolic verification for process control LLMs. Neural network interprets unstructured inputs; symbolic reasoning engine validates against formal business rules and logical constraints before execution. If neural output contradicts established rules, symbolic layer catches error. Particularly relevant for financial, healthcare, and supply chain applications.

**Practical applicability**: This demonstrates production viability of the neurosymbolic approach for high-stakes analysis pipelines. The "separation of understanding from execution" principle maps to our pipeline: the LLM understands the code and generates claims (neural), then a symbolic layer validates claim consistency against code facts (symbolic). The symbolic layer does not need to understand the code — it only needs to check whether the claims are mutually consistent and consistent with directly observable facts.

---

## Area 6: Safety Cases and Assurance

### 6.1 Constructing Safety Cases for AI Systems

**Paper**: arxiv.org/abs/2601.22773 | January 2026
**Key insight**: Systematic structured-argument methodology for AI safety assurance. A safety case has four components: objectives (must be met for safety), arguments (that objectives are met), evidence (that arguments are true), scope (in which the case holds). Adapts traditional aviation/nuclear safety case methodology (GSN — Goal Structuring Notation) to AI systems. Safety cases are already mandated in aviation (EASA NPA 2025-07, EU AI Act compliance).

**Practical applicability**: Our verified analysis pipeline produces claims. A safety case for our pipeline would look like: Objective: "analysis output contains no false STRUCTURAL claims." Argument: "STRUCTURAL claims are verified against observable code properties." Evidence: "verification logs from CLOVER/NSVIF." Scope: "code inputs ≤ N lines, Python/TypeScript." This framing makes the pipeline's quality claims auditable — a property that matters if the pipeline is used in safety-critical contexts.

---

### 6.2 Safety Cases for Frontier AI

**Paper**: arxiv.org/html/2410.21572v1 | October 2024
**Key insight**: Systematic methodology for frontier AI safety cases. Key challenge: AI systems' capabilities emerge unpredictably, behaviors vary with prompts, and risk profiles shift through fine-tuning and deployment context — exactly opposite to traditional safety case assumptions of stable architecture and known failure modes.

**Practical applicability**: The "inability argument" pattern from frontier AI safety cases maps to our pipeline. An inability argument says "the system CANNOT make false STRUCTURAL claims because the claims are constrained to be directly observable in code." This is stronger than "the system is unlikely to make false claims." Our claim taxonomy enables this shift: by defining STRUCTURAL claims as "directly derivable from observable code properties," we create a formal inability argument for that claim type.

---

### 6.3 Assessing Confidence in Frontier AI Safety Cases

**Paper**: arxiv.org/abs/2502.05791 | February 2025
**Key insight**: Applies Assurance 2.0 methodology to AI safety cases. Introduces Delphi method for reproducible, transparent probabilistic assessment. The core contribution: a structured method for assigning confidence levels to safety arguments where formal proof is impossible.

**Practical applicability**: For our ASSUMED and KNOWLEDGE claims — where formal verification is impossible — this framework provides a structured alternative. Instead of "this claim is unverifiable," the pipeline can produce "this claim is ASSUMED with confidence level X based on [evidence]." The Delphi method for aggregating multiple assessments maps to our multi-pass pipeline: run the claim through 3 passes, aggregate, assign confidence with bounds.

---

### 6.4 BIG Argument Framework for AI Safety Cases

**Paper**: arxiv.org/html/2503.11705v3 | March 2025
**Key insight**: Synthesizes 60 years of safety case methodology into a Bayesian framework for AI. Safety cases are structured arguments supported by evidence — not proof, but traceable argumentation. The BIG argument framework distinguishes claim strength (how well-supported is the claim?) from claim scope (in what contexts does it hold?).

**Practical applicability**: Directly applicable to our claim confidence scoring. Our STRUCTURAL claims can be annotated with Bayesian confidence derived from: (1) formal verification status (verified → high), (2) cross-validation across multiple analysis passes (consistent → higher), (3) scope annotation (applies to this pattern in this language → narrow but confident vs. applies universally → broad but uncertain). The BIG framework gives this a principled mathematical foundation.

---

## Synthesis: Application to Our STRUCTURAL/DERIVED/MEASURED/KNOWLEDGE/ASSUMED Pipeline

### The Verification Spectrum

| Claim Type | Verification Method | Tool | Confidence Form |
|---|---|---|---|
| STRUCTURAL | Formal verification (SMT/Dafny/Lean4) | CLOVER, NSVIF Z3 layer | VERIFIED / REFUTED (binary) |
| DERIVED | Logical satisfiability (Z3 FOL) | NSVIF, LINC | SAT / UNSAT with violation detail |
| MEASURED | Statistical grounding (RoMA bounds) | RoMA adaptation | Confidence interval [X, Y] |
| KNOWLEDGE | Retrieval grounding (RAG) | PropertyGPT pattern | Grounded / Ungrounded + source |
| ASSUMED | Safety case argument | BIG framework, Assurance 2.0 | Structured argument + scope |

### Immediate Integration Opportunities

**1. Eidoku gate on STRUCTURAL claims (highest priority)**
Before any STRUCTURAL claim enters the output, run the three-proxy cost check: graph connectivity (is it connected to code elements?), geometric consistency (is it similar to verified structural claims?), logical entailment (is it derivable?). Claims exceeding the cost threshold are reclassified as ASSUMED. This requires no LLM — it is a lightweight symbolic pass that runs after the analysis.

**2. Z3 consistency check on DERIVED claims**
NSVIF's three-phase architecture (Planner → Executor → Z3 Solver) can be applied to our DERIVED claims. The Planner extracts the logical form of the STRUCTURAL claims the DERIVED claim depends on. The Z3 Solver checks whether the DERIVED claim is satisfiable given those dependencies. If UNSAT, the DERIVED claim is confabulated and is reclassified.

**3. AgentSpec rules for the pipeline**
Encode the claim-type rules as AgentSpec specifications: "IF claim_type=STRUCTURAL THEN evidence must include code_location." "IF claim_type=KNOWLEDGE THEN external_source must be cited." "IF verification_status=UNVERIFIED AND claim_strength=HIGH THEN require_second_pass." The DSL overhead is milliseconds; this adds formal enforceability to what are currently semantic guidelines.

**4. Contract layer (DbC-inspired)**
Apply Leoveanu-Condrei's SymbolicAI contract layer to our pipeline: preconditions on what inputs are valid for each prism, postconditions on what claim types are permissible given the input domain. The "functional equivalence under contracts" theorem then enables us to compare prism variants formally: two prisms that satisfy the same contracts are equivalent with respect to those contracts.

**5. Safety case for the pipeline itself**
Use the BIG framework to construct a safety case for our verified analysis pipeline. Objective: "no false STRUCTURAL claims enter output." Argument: "STRUCTURAL claims pass Eidoku gate AND Z3 consistency check." Evidence: "gate rejection rates across 1000+ experiments." Scope: "code inputs, Python/TypeScript, ≤3000 lines." This turns our experimental results into a structured assurance argument.

### The Deep Architectural Insight

All six areas converge on one pattern: **the verifiable subset of claims can be handled symbolically with binary guarantees; the unverifiable subset requires structured argumentation with explicit confidence bounds**. Our SMKDA taxonomy naturally partitions claims along this dimension:

- STRUCTURAL + DERIVED = symbolic verification territory (binary, fast, cheap)
- MEASURED = statistical verification territory (probabilistic bounds, medium cost)
- KNOWLEDGE + ASSUMED = structured argumentation territory (traceable, auditable)

The current pipeline treats all five types with the same self-audit mechanism (LLM judges LLM). The literature shows this is unnecessary for STRUCTURAL/DERIVED (use formal tools — faster, cheaper, binary) and insufficient for KNOWLEDGE/ASSUMED (use structured argumentation — not just "is it true?" but "what is the scope and confidence?").

The verifiable analysis pipeline of 2026 is: **prism generates claims → Eidoku gate filters STRUCTURAL → Z3 validates DERIVED → RoMA bounds MEASURED → RAG grounds KNOWLEDGE → BIG framework structures ASSUMED → output is a typed, evidence-annotated claim set with formal guarantees where possible and explicit uncertainty where not.**

---

## Key Papers for Immediate Follow-Up

1. **Eidoku** (arxiv.org/abs/2512.20664) — implement the three-proxy cost function as a post-processing gate
2. **NSVIF** (arxiv.org/abs/2601.17789) — adapt the Z3 constraint-satisfaction layer for DERIVED claims
3. **AgentSpec** (arxiv.org/abs/2503.18666) — encode claim-type rules as runtime enforcement DSL
4. **Contracts for LLM APIs** (tanzimhromel.com/assets/pdf/llm-api-contracts.pdf) — use the 73-type taxonomy and formal probabilistic model as specification foundation
5. **CLOVER** (arxiv.org/abs/2310.17807) — adapt the reconstruction consistency check for structural claim verification
6. **DbC Neurosymbolic Layer** (arxiv.org/abs/2508.03665) — implement the contract precondition/postcondition pattern on claim types
7. **BIG Argument Framework** (arxiv.org/html/2503.11705v3) — structure the pipeline's own quality assurance as a safety case

---

## Sources

- [Towards Formal Verification of LLM-Generated Code from Natural Language Prompts](https://arxiv.org/abs/2507.13290)
- [Propose, Solve, Verify: Self-Play Through Formal Verification](https://arxiv.org/abs/2512.18160)
- [Clover: Closed-Loop Verifiable Code Generation](https://arxiv.org/abs/2310.17807)
- [CLOVER at Stanford SAIL Blog](http://ai.stanford.edu/blog/clover/)
- [Can Large Language Models Verify System Software?](https://users.cs.duke.edu/~mlentz/papers/llmverif_hotos2025.pdf)
- [Evaluating LLM-Generated ACSL Annotations for Formal Verification](https://arxiv.org/html/2602.13851v1)
- [LLM-Based Theorem Provers — Emergent Mind](https://www.emergentmind.com/topics/llm-based-theorem-provers)
- [FVEL: Interactive Formal Verification Environment (NeurIPS 2024)](https://proceedings.neurips.cc/paper_files/paper/2024/file/62c6d7893b13a13c659cb815852dd00d-Paper-Datasets_and_Benchmarks_Track.pdf)
- [Autoformalization in the Era of Large Language Models: A Survey](https://arxiv.org/html/2505.23486v1)
- [REINFORCED LARGE LANGUAGE MODEL IS A FORMAL THEOREM PROVER](https://www.arxiv.org/pdf/2502.08908)
- [DeepTheorem: Advancing LLM Reasoning for Theorem Proving](https://arxiv.org/pdf/2505.23754)
- [AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents](https://arxiv.org/abs/2503.18666)
- [AgentSpec PDF](https://cposkitt.github.io/files/publications/agentspec_llm_enforcement_icse26.pdf)
- [Pro2Guard: Proactive Runtime Enforcement of LLM Agent Safety via Probabilistic Model Checking](https://arxiv.org/abs/2508.00500)
- [Statistical Runtime Verification for LLMs via Robustness Estimation](https://arxiv.org/abs/2504.17723)
- [Runtime Verification Meets Large Language Models](https://arxiv.org/pdf/2511.14435)
- [Neuro-Symbolic Verification on Instruction Following of LLMs](https://arxiv.org/abs/2601.17789)
- [A Neurosymbolic Approach to Natural Language Formalization and Verification](https://arxiv.org/abs/2511.09008)
- [Eidoku: A Neuro-Symbolic Verification Gate for LLM Reasoning](https://arxiv.org/abs/2512.20664)
- [Neuro-Symbolic Verification for Preventing LLM Hallucinations in Process Control](https://www.mdpi.com/2227-9717/14/2/322)
- [Preconditions and Postconditions as Design Constraints for LLM Code Generation](https://ieeexplore.ieee.org/document/11218044/)
- [Contracts for Large Language Model APIs](https://tanzimhromel.com/assets/pdf/llm-api-contracts.pdf)
- [A DbC Inspired Neurosymbolic Layer for Trustworthy Agent Design](https://arxiv.org/abs/2508.03665)
- [Beyond Postconditions: Can Large Language Models infer Formal Contracts](https://arxiv.org/pdf/2510.12702)
- [PropertyGPT: LLM-driven Formal Verification of Smart Contracts](https://arxiv.org/abs/2405.02580)
- [A Structured Approach to Safety Case Construction for AI Systems](https://arxiv.org/abs/2601.22773)
- [Safety Cases for Frontier AI](https://arxiv.org/html/2410.21572v1)
- [Assessing Confidence in Frontier AI Safety Cases](https://arxiv.org/abs/2502.05791)
- [The BIG Argument for AI Safety Cases](https://arxiv.org/html/2503.11705v3)
- [Safety Case Template for Frontier AI](https://www.governance.ai/research-paper/safety-case-template-for-frontier-ai-a-cyber-inability-argument)
- [EASA AI Trustworthiness Regulatory Proposal](https://www.easa.europa.eu/en/newsroom-and-events/news/easas-first-regulatory-proposal-artificial-intelligence-aviation-now-open)
- [Hallucination Detection and Mitigation in Large Language Models](https://arxiv.org/pdf/2601.09929)
- [From Illusion to Insight: Taxonomic Survey of Hallucination Mitigation](https://www.mdpi.com/2673-2688/6/10/260)
- [Martin Kleppmann: AI will make formal verification go mainstream](https://martin.kleppmann.com/2025/12/08/ai-formal-verification.html)
