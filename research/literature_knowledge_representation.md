# Literature Review — Knowledge Representation, Ontologies & LLM Knowledge Management

**Date**: Mar 15, 2026
**Author**: Research agent (Claude Sonnet 4.6)
**Purpose**: Survey for a system where LLM analysis detects its own knowledge gaps, classifies them by type (STRUCTURAL/DERIVED/MEASURED/KNOWLEDGE/ASSUMED), and fills them from external sources (AgentsKB, web search, CVE databases).

---

## Overview

Six interconnected bodies of literature are directly relevant to building a principled gap-detection and gap-filling pipeline on top of LLM analysis:

1. Epistemic ontologies — how to formally represent "I know X with confidence Y from source Z"
2. Open-world vs closed-world assumption — how KBs handle incompleteness
3. Knowledge base completion — detecting and filling structural gaps
4. Belief revision (AGM theory) — updating beliefs consistently under contradiction
5. Meta-knowledge standards — confidence, provenance, temporal validity
6. Neuro-symbolic integration — reconciling soft (LLM) and hard (KG) knowledge

The central finding: **each literature converges on the same representation problem** — knowledge is not binary. It exists on a continuum of confidence, provenance, and freshness, and the system that manages it must track all three axes explicitly. The gap-type taxonomy (STRUCTURAL/DERIVED/MEASURED/KNOWLEDGE/ASSUMED) maps cleanly onto existing formalisms, mostly unexploited in LLM systems.

---

## 1. Epistemic Ontologies — Representing "What I Know and How"

### 1.1 The Core Problem

Standard RDF/OWL represents facts as binary assertions: either a triple exists or it does not. Reality requires annotating triples with:
- **Confidence**: probability or fuzzy degree of belief (0.0–1.0)
- **Provenance**: what source generated this, via what process
- **Temporal validity**: when was this true, is it still true
- **Epistemic status**: known / believed / assumed / inferred / measured

OWL2 (SROIQ(D) description logic, W3C 2009) cannot natively represent any of these. This has spawned a family of extensions.

### 1.2 RDF-Star — The Emerging Standard

**Standard**: RDF-star (W3C, now part of RDF 1.2 / SPARQL 1.2)
**What it does**: Allows embedding a triple as the subject or object of another triple.

```
<< :python :hasVulnerability :CVE-2024-1234 >> :confidence 0.92 .
<< :python :hasVulnerability :CVE-2024-1234 >> :source :NVD .
<< :python :hasVulnerability :CVE-2024-1234 >> :detectedAt "2026-03-15" .
```

Before RDF-star, the only options were:
- **Standard reification** (4 extra triples per annotation — expensive)
- **Named graphs** (graph-level, not triple-level granularity)
- **Singleton properties** (hacky: introduces unique predicate per statement)

**Practical applicability**: RDF-star is the right native mechanism for the gap-filling pipeline. Each filled gap becomes an annotated triple with its confidence, source, and timestamp. GraphDB 10+ natively supports RDF-star and SPARQL-star queries over annotations.

### 1.3 Probabilistic OWL Extensions

**PR-OWL 2** (da Costa et al.): Extends OWL with Multi-Entity Bayesian Networks. Allows probabilistic axioms — "this class membership holds with probability P" — with full inference. But inference is expensive, and the probabilistic parts must be separated from deterministic parts.

**Poss-OWL 2**: Possibilistic extension. Uses necessity and possibility degrees instead of probability. Better for modeling expert subjective uncertainty ("I am 80% certain that...").

**Fuzzy OWL 2**: Degrees of truth for class membership. Useful when class boundaries are inherently vague.

**Practical applicability**: For the gap-filling pipeline, full PR-OWL is overkill. The simpler pattern — attach a `:confidence` literal to each filled gap statement via RDF-star — achieves 90% of the benefit at 1% of the complexity.

### 1.4 Epistemic Logic Operators

Epistemic logic uses modal operators: K(agent, φ) = "agent knows φ". Dynamic Epistemic Logic (DEL) models how knowledge changes across events (learning new facts, observing actions).

**Practical relevance**: The gap type taxonomy maps onto epistemic logic operators:
- KNOWLEDGE gaps → ¬K(LLM, φ) — the LLM doesn't know φ (not in training data)
- ASSUMED gaps → B(LLM, φ) — the LLM believes φ but without verified evidence
- MEASURED gaps → ∃source: K(source, φ) ∧ ¬access(LLM, source)
- STRUCTURAL gaps → ¬expressible(φ, current_schema)
- DERIVED gaps → φ derivable from known facts but not yet derived

This decomposition is not novel — it matches standard epistemic logic distinction between knowledge (justified true belief) and assumption (belief without justification).

### 1.5 Key Source

**Survey**: "Uncertainty Management in the Construction of Knowledge Graphs" (2024) — comprehensive treatment of how to represent uncertainty at the triple, graph, and inference level. Distinguishes epistemic uncertainty (incomplete knowledge) from ontic uncertainty (inherent in the world). The former is addressable by gap-filling; the latter is not.

---

## 2. Open-World vs Closed-World Assumption

### 2.1 The Fundamental Distinction

**Closed-World Assumption (CWA)**: If a fact is not in the KB, it is false. Standard in relational databases, Datalog, SPARQL by default.

**Open-World Assumption (OWA)**: If a fact is not in the KB, its truth is unknown. Standard in OWL/RDF. The KB is incomplete by definition.

### 2.2 Why This Matters for LLMs

LLMs operate under a de facto open world. The model was trained on a subset of knowledge, so the absence of a fact in the model's outputs does not mean the fact is false — it may simply be unlearned or stale.

However, **gap detection requires a partial CWA**: we need to know what the model *should* know in order to classify what it *doesn't* know. Without some notion of expected coverage, all gaps are indistinguishable from "normal" incompleteness.

The practical resolution used in knowledge graph research:
- Apply CWA within a **bounded scope** (e.g., "all CVEs from 2020–2024 for Python packages")
- Apply OWA everywhere else
- The bounded scope defines the "expected coverage" against which gaps are measured

### 2.3 InferWiki Dataset and OWA Evaluation

Recent work (InferWiki, 2024) annotated KG test triples with whether they can be verified via inference patterns within the KG (closed-world) or require external sources (open-world). This dual annotation is exactly the architecture needed for gap classification:
- Gap solvable by internal reasoning → DERIVED type
- Gap requiring external lookup → KNOWLEDGE or MEASURED type

### 2.4 LLM-Specific Gap Literature

"Towards Detecting Prompt Knowledge Gaps for Improved LLM-guided Issue Resolution" (arXiv:2501.11709, 2025): Identifies four gap categories in developer prompts: Missing Context, Missing Specifications, Multiple Context, Unclear Instructions. These are surface-level gaps (prompt engineering), not epistemic gaps in the model's world model.

"Bridging Knowledge Gaps in LLMs via Function Calls" (ACM CIKM 2024): Proposes routing to external APIs/functions when confidence falls below threshold. Architecture: detect low confidence → classify gap type → select retrieval function → fill gap → re-analyze. This is the closest existing implementation to the target system.

### 2.5 Practical Implication

The gap-filling pipeline should operate under **local CWA**: define a scope (the artifact being analyzed + its known dependency surface), assert CWA within that scope, and treat any assertion outside the scope as OWA. Gaps that fall within the CWA scope are actionable (fetch CVE data, check API surface, verify version constraints). Gaps outside scope are acknowledged but not pursued.

---

## 3. Knowledge Base Completion — Detecting and Filling Structural Gaps

### 3.1 The KGC Task

Knowledge Graph Completion (KGC) predicts missing triples in a KG. Three subtasks:
1. **Link prediction**: Given (head, relation, ?), predict tail entity
2. **Relation prediction**: Given (head, ?, tail), predict relation type
3. **Entity prediction**: Given (?, relation, tail), predict head entity

### 3.2 Current Methods (2024–2025)

**Embedding-based methods** (TransE, RotatE, ComplEx): Map entities and relations to vector space; predict missing links by proximity. Fast, scalable, but require a static snapshot — don't handle temporal change well.

**Hybrid learning** (RL + supervised, 2024 trend): Use reinforcement learning to explore multi-hop reasoning paths for link prediction. More robust than single-step embeddings.

**LLM-based KGC**: Use LLMs to predict missing relations as text generation. "Relations Prediction for Knowledge Graph Completion using Large Language Models" (ACL 2024): LLMs achieve competitive performance on standard KGC benchmarks by framing relation prediction as prompted text generation. But: LLMs hallucinate relations that don't exist in the schema.

**Post-prediction validation** (2024): Recent work adds a validation layer after LLM prediction. LLM generates candidate triple → symbolic reasoner checks consistency with existing KG → inconsistent candidates are rejected. This is the neuro-symbolic pattern in Section 6.

### 3.3 Completeness Dimensions

From KG quality research, completeness has four orthogonal dimensions:
- **Schema completeness**: Does the schema define all relevant relation types?
- **Property completeness**: For entities that have a property, is the value filled?
- **Population completeness**: Are all entities in the domain present?
- **Linkability completeness**: Can entities be linked to external sources (Wikidata, NVD, etc.)?

These map directly to the gap-type taxonomy:
- Schema completeness deficits → STRUCTURAL gaps
- Property completeness deficits → MEASURED gaps (value should exist, hasn't been captured)
- Population completeness deficits → KNOWLEDGE gaps (entity exists in the world, not in the KB)
- Linkability completeness deficits → sourcing gaps (can't verify against authoritative sources)

### 3.4 UOKGE — Uncertainty-Aware KG Embeddings

UOKGE (Uncertain Ontology-aware Knowledge Graph Embeddings, 2024): Encodes entities as points in vector space and classes as *spheres* with radius proportional to uncertainty. A class with narrow radius = high-confidence, tight boundary (e.g., confirmed CVE severity). A class with wide radius = high uncertainty (e.g., inferred vulnerability from static analysis).

**Practical applicability**: The sphere encoding provides a natural representation for gap confidence: a gap with confidence 0.3 has a wide sphere; a gap with confidence 0.9 (confirmed from NVD) has a narrow sphere.

### 3.5 Gap Visualization — "The Missing Path"

"The Missing Path: Analysing Incompleteness in Knowledge Graphs" (2021, but still reference implementation): Groups entities by their incomplete profile in a visualization tool. Identifies coherent subsets of entities that can be repaired together. The key insight: **gaps cluster by type** — if one entity of a class is missing a property, most others are too. This means gap detection on one example generalizes to the whole class.

For the gap-filling pipeline: if analysis detects a MEASURED gap for one library version, it likely applies to all versions in that dependency tree. Fill once, propagate to similar entities.

---

## 4. Belief Revision — Updating Knowledge Under Contradiction

### 4.1 AGM Theory

The Alchourrón-Gärdenfors-Makinson (AGM) postulates (1985) define three rational operations on a belief set K:
- **Expansion** (K + φ): Add φ without consistency check. K grows.
- **Revision** (K * φ): Add φ while maintaining consistency. If φ contradicts K, some beliefs in K must go.
- **Contraction** (K - φ): Remove φ from K. Minimal change.

The postulates require: revision must be consistent, minimal (change as little as possible), and non-circular (you can't revise away a tautology).

### 4.2 AGM Applied to LLMs — The 2024 Critique

"Fundamental Problems With Model Editing: How Should Rational Belief Revision Work in LLMs?" (arXiv:2406.19354, 2024):

Key findings:
1. LLM knowledge editing methods (ROME, MEMIT, etc.) achieve precise updates but fail to propagate changes coherently to related facts.
2. RippleEdits benchmark: editing "X was born in city Y" should update all downstream facts (Y's country, Y's population, etc.). Current methods update the direct fact but achieve only ~20% accuracy on related fact propagation.
3. **The core problem**: LLMs don't have an explicit belief graph. Revising one "fact" modifies weights that encode many overlapping associations. There is no principled boundary between what should and shouldn't change.
4. Rational belief revision requires knowing the agent's *priors*. For LLMs, priors are implicit in weights and unknown.

### 4.3 ChainEdit — Logical Rule-Guided Belief Propagation

ChainEdit (arXiv:2507.08427, 2025): Addresses the ripple effect by constructing logical dependency chains before editing. Edit + chain = consistent propagation. Uses rules like:
- If (A birthplace B) is edited, then (A nationality B.country) must also update
- If (A CEO B) is edited, then (B foundedBy ≠ A) must be checked

**Practical applicability for gap-filling**: When a gap is filled (new fact F added to analysis), the gap-filler should:
1. Identify all claims in the existing analysis that depend on the old belief
2. Flag them for revision
3. Re-run the downstream reasoning steps with the new fact

This is not free — it requires a dependency graph of the analysis conclusions. But without it, gap-filling produces locally correct but globally inconsistent analysis (the filled gap contradicts claims made elsewhere in the output).

### 4.4 The Revision vs Expansion Distinction

For the gap-filling pipeline, gap type determines which AGM operation applies:
- KNOWLEDGE gap (absent fact, no existing claim) → **Expansion** (K + φ): add new fact, no conflict
- ASSUMED gap (believed fact proven wrong) → **Revision** (K * φ): replace belief, propagate
- MEASURED gap (approximate value corrected to precise value) → **Revision** with small K-change
- STRUCTURAL gap (schema extension) → **Expansion** (new schema element added, no existing belief conflicts)
- DERIVED gap (conclusion reachable but not yet derived) → **Expansion** after derivation

Only ASSUMED gaps require full AGM revision with propagation. The others are safer expansions.

### 4.5 Iterated Belief Revision

Standard AGM handles single-step revision. Iterated revision (Darwiche-Pearl postulates, 1997) handles sequential updates. For a gap-filling pipeline that makes multiple passes, iterated revision rules apply:
- If two pieces of new information contradict each other, priority ordering must exist
- Higher-confidence sources (CVE NVD = authoritative) override lower-confidence sources (LLM inference)
- Most recent measurement overrides older measurement

This translates to: the gap-filling pipeline needs an **explicit priority ordering** across its sources (NVD > vendor advisory > LLM inference > assumed default).

---

## 5. Meta-Knowledge — Representing Knowledge About Knowledge

### 5.1 PROV-O — The W3C Provenance Standard

**Standard**: PROV-O (W3C Recommendation, 2013). Encodes the PROV Data Model in OWL2.

Three core concepts:
- **Entity**: A thing (a piece of data, a document, a fact)
- **Activity**: A process that used/generated entities
- **Agent**: A person, software, or organization responsible for the activity

Core properties:
```turtle
:CVE_analysis prov:wasGeneratedBy :scan_activity .
:scan_activity prov:used :python_package_v3_12 .
:scan_activity prov:wasAssociatedWith :prism_tool .
:CVE_analysis prov:wasDerivedFrom :NVD_database .
:CVE_analysis prov:generatedAtTime "2026-03-15T10:00:00Z" .
```

**Qualified annotations** provide finer granularity:
```turtle
:CVE_analysis prov:qualifiedGeneration [
    a prov:Generation ;
    prov:activity :scan_activity ;
    prov:atTime "2026-03-15T10:00:00Z" ;
    :confidence 0.92 ;
    :gap_type "MEASURED" ;
] .
```

### 5.2 PROV-STAR — RDF-star Extension of PROV-O

PROV-STAR (2024, FOIS conference): Extends PROV-O with RDF-star to attach provenance at the triple level (not just entity level). Enables:
```turtle
<< :pkg :hasVuln :CVE-2024-5678 >> prov:wasDerivedFrom :NVD ;
                                    :confidence 0.97 ;
                                    prov:generatedAtTime "2026-03-15" .
```

This is exactly the representation needed for gap-filled facts: every fact added to the analysis carries its own lineage, confidence, and timestamp.

### 5.3 ISO/IEC 21838-2 — Basic Formal Ontology (BFO)

**Standard**: ISO/IEC 21838-2:2021 (published by ISO/IEC JTC 1)

BFO is a top-level ontology for structuring all other ontologies. Key distinction for meta-knowledge:
- **Continuants**: things that persist through time (entities, substances)
- **Occurrents**: processes, events, intervals (analyses, scans, activities)
- **Specifically Dependent Continuants**: qualities that depend on their bearer (confidence is a quality of a knowledge claim, not a free-floating object)

**Practical relevance**: Confidence and provenance are BFO specifically-dependent continuants. They don't exist independently — they always depend on the claim they qualify. This means confidence cannot be stored separately from the claim; the representation must co-locate them. RDF-star (Section 1.2) achieves this.

### 5.4 PROV-O Mapping to BFO

"A Semantic Approach to Mapping the Provenance Ontology to Basic Formal Ontology" (Nature Scientific Data, 2025): Provides an alignment between PROV-O and BFO, enabling integration of provenance records into formal ontology frameworks. Key mapping:
- prov:Entity → BFO:GenericallyDependentContinuant (data objects)
- prov:Activity → BFO:Process
- prov:Agent → BFO:IndependentContinuant

**Practical relevance**: If the gap-filling pipeline is expected to interoperate with external knowledge systems (MITRE ATT&CK, NVD, ontology-based AgentsKBs), BFO alignment ensures that provenance records are interpretable across systems.

### 5.5 Temporal Validity — The Missing Dimension

Most provenance systems capture *when* a fact was recorded but not *until when* it is valid. For security knowledge (CVEs, dependency versions, API surfaces), temporal validity is critical:
- A CVE severity score may be revised upward (initial: MEDIUM, corrected: CRITICAL)
- A library version may be deprecated
- A vulnerability may be patched

Hybrid Approaches for Temporal Validation (2025 thesis, HAL): Addresses exactly this problem — combining temporal logic with knowledge graph techniques to invalidate stale facts. The architecture:
1. Each fact carries a `validFrom` / `validUntil` interval
2. A background process monitors authoritative sources for updates
3. Facts whose `validUntil` has passed are flagged as STALE and trigger MEASURED gap re-detection

**Practical applicability**: For the gap-filling pipeline, temporal gap type is a subtype of MEASURED: the value was correct but is no longer current. The system should timestamp filled gaps and set a TTL (time-to-live) based on source type:
- CVE scores: TTL 30 days (NVD updates regularly)
- Library version: TTL 7 days (package registries update frequently)
- API surface: TTL = next release
- Structural analysis: TTL = no automatic expiry (structural facts are stable)

---

## 6. Neuro-Symbolic Integration — Reconciling LLM and KG Knowledge

### 6.1 The Fundamental Tension

LLMs:
- Soft, probabilistic associations
- High coverage, low precision
- No explicit provenance
- Vulnerable to hallucination
- Cannot be locally updated without full retraining

Knowledge Graphs:
- Hard, deterministic edges
- Low coverage, high precision
- Explicit provenance
- Verifiable
- Can be locally updated (add/remove triple)

Neither alone is sufficient. The gap-filling pipeline is inherently neuro-symbolic: LLM produces candidate gap claims → KG provides verification and enrichment → LLM synthesizes the augmented analysis.

### 6.2 Integration Architectures (2024–2025 Survey)

"A Review on Synergizing Knowledge Graphs and Large Language Models" (Springer Computing, 2025) identifies three integration modes:

**Mode 1: KG enhances LLM** (KG→LLM)
- LLM is prompted with relevant KG facts at inference time
- Pattern: Graph RAG, KG-augmented prompts
- Use: Fill KNOWLEDGE gaps with verified KG facts before LLM analysis
- Limitation: KG coverage determines ceiling; LLM still hallucinate about KG gaps

**Mode 2: LLM enhances KG** (LLM→KG)
- LLM fills KG gaps by generating candidate triples; KG validates consistency
- Pattern: KGC with LLM + symbolic validator
- Use: Detect STRUCTURAL gaps (missing schema) and propose completions
- Limitation: LLM hallucination in triple generation requires human or automated validation

**Mode 3: Mutual enhancement** (LLM↔KG)
- Iterative: LLM generates → KG validates → LLM revises → repeat
- Pattern: RAG with consistency checking
- Use: Fill ASSUMED gaps where prior belief needs correction
- Best fit for the target gap-filling pipeline

### 6.3 OWL-Based Symbolic Deduction Engines

"On the Potential of Logic and Reasoning in Neurosymbolic Systems Using OWL-Based Knowledge Graphs" (SAGE Journals, 2025):

OWL reasoners (HermiT, Pellet, ELK) can check consistency, classify new facts, and detect contradictions. AlphaGeometry's architecture (LLM + symbolic deduction engine) shows this works at state-of-the-art:
1. LLM generates candidate proof steps
2. Symbolic engine verifies each step
3. If invalid, LLM is asked to generate alternatives

For gap-filling: the symbolic engine is the gap validator. A gap-fill that contradicts an OWL axiom (e.g., claims a version is both vulnerable and patched) is rejected and the LLM is asked to reconsider.

### 6.4 AllegroGraph v8 — Production Neuro-Symbolic Platform

AllegroGraph 8.0 (2024): First commercial KG platform with native LLM integration. Features:
- RAG pipeline with KG retrieval
- Dynamic fact-checking: LLM outputs verified against KG before returning to user
- Native SPARQL + LLM hybrid queries

This is the closest existing production system to the target architecture. The gap-filling pipeline could be implemented as an AllegroGraph workflow: Prism output → LLM gap detection → SPARQL gap query → NVD/CVE fill → RDF-star annotation → re-analysis.

### 6.5 CyKG-RAG — Security-Specific KG-RAG

CyKG-RAG (2024): RAG system combining symbolic KG (CVE, CWE, CAPEC, MITRE ATT&CK) with semantic search. Architecture:
1. Convert security query to SPARQL → retrieve exact matches from CVE/CWE graph
2. Embed query → retrieve semantically similar context
3. Combine both retrievals as LLM context
4. LLM synthesizes answer grounded in both exact facts and fuzzy context

This directly addresses the CVE gap-filling use case. The gap type MEASURED maps cleanly to exact SPARQL retrieval (get the precise CVE score). The gap type KNOWLEDGE maps to semantic search (find related vulnerabilities not directly cited).

### 6.6 Hallucination as Gap Misclassification

"Uncertainty Quantification for Hallucination Detection in LLMs" (arXiv:2510.12040, 2025):

Hallucination = LLM generates a false fact with high confidence. This is equivalent to a KNOWLEDGE gap that the model doesn't know it has — an "unknown unknown."

The paper distinguishes:
- **Calibrated confidence**: model is uncertain and says so → detectable as explicit gap
- **Overconfident hallucination**: model is uncertain but says it's certain → invisible gap

The invisible gap problem is the hardest. The paper's finding: **consistency testing** (ask the same question multiple times with paraphrased prompts) surfaces overconfident hallucinations. If the model gives contradictory high-confidence answers, the underlying claim is uncertain.

**Practical applicability**: The gap detection module should include a consistency-testing pass for ASSUMED gap type: if the LLM states the same assumption differently in different parts of the analysis, it is flagged as ASSUMED rather than KNOWN.

---

## 7. Synthesis — Practical Architecture for the Gap-Filling Pipeline

### 7.1 Knowledge Types and Their Representations

| Gap Type | Epistemic Status | CWA/OWA | AGM Operation | Fill Source | Representation |
|---|---|---|---|---|---|
| STRUCTURAL | expressibility failure | N/A | Schema expansion | Human/LLM schema design | New OWL class/property |
| DERIVED | logically derivable, not derived | CWA (within scope) | Expansion | Internal reasoning | Inferred triple + prov:wasDerivedFrom :reasoning |
| MEASURED | fact exists in world, not in analysis | CWA (within scope) | Expansion | CVE/NVD/registry | Triple + RDF-star confidence + timestamp |
| KNOWLEDGE | fact unknown to LLM | OWA | Expansion | Web search / AgentsKB | Triple + prov:wasDerivedFrom :external_source |
| ASSUMED | belief held without justification | OWA | Revision (if wrong) | Verification against KG | AGM revision + ripple-effect propagation |

### 7.2 Representation Schema

Each filled gap should be stored as an annotated triple:

```turtle
# Minimal gap annotation (RDF-star)
<< :target :hasGap :gap_id >>
    :gapType "MEASURED" ;
    :confidence 0.95 ;
    :filledFrom :NVD_database ;
    :filledAt "2026-03-15T10:30:00Z" ;
    :validUntil "2026-04-15T00:00:00Z" ;
    prov:wasGeneratedBy :gap_fill_activity .

# The filled fact itself
:target :hasVulnerability :CVE-2024-5678 .
<< :target :hasVulnerability :CVE-2024-5678 >>
    :cvssScore 9.1 ;
    :severity "CRITICAL" ;
    :confidence 0.97 ;
    prov:wasDerivedFrom :NVD .
```

### 7.3 Gap Detection Logic (CWA + Consistency)

1. Run LLM analysis → extract all claims
2. For each claim, classify epistemic status:
   - Claim supported by specific cited evidence → MEASURED or DERIVED
   - Claim stated as general knowledge without citation → KNOWLEDGE or ASSUMED
   - Claim contradicted elsewhere in analysis → ASSUMED (overconfident hallucination)
3. Define scope (the artifact + its known dependency surface)
4. Apply local CWA within scope: any property expected but absent = gap
5. Classify gap type by what kind of source could fill it

### 7.4 Belief Revision on Gap Fill

When filling an ASSUMED gap (existing belief corrected):
1. Identify all analysis claims that depended on the old belief (dependency traversal)
2. Flag them as PROVISIONAL
3. Re-run the relevant analysis sections with the corrected fact
4. Apply Darwiche-Pearl iterated revision: source priority = NVD > vendor > LLM inference > default assumption

When filling a KNOWLEDGE gap (new fact added with no prior belief):
1. Expansion only (no existing belief to revise)
2. Check OWL consistency: does new fact contradict any schema axiom?
3. If inconsistent → flag as STRUCTURAL gap (schema needs updating)
4. If consistent → add with annotation

### 7.5 Source Priority Ordering

Implementing iterated revision requires an explicit priority ordering:

```
Level 1 (authoritative): CVE/NVD, NIST, official vendor advisories
Level 2 (trusted): Package registry metadata, official documentation
Level 3 (derived): LLM inference from documented facts
Level 4 (assumed): LLM default assumptions without citation
Level 5 (stale): Facts past their TTL (require re-verification)
```

A gap filled from Level 1 overrides any existing Level 3–4 claim. A Level 3 inference does not override a Level 1 fact.

---

## 8. Key Papers and Standards Reference

| Reference | Type | Relevance |
|---|---|---|
| PROV-O (W3C, 2013) | Standard | Provenance representation: wasGeneratedBy, wasDerivedFrom, qualified annotations |
| RDF-star / RDF 1.2 (W3C, ongoing) | Standard | Triple-level annotation of confidence + provenance |
| ISO/IEC 21838-2:2021 (BFO) | Standard | Top-level ontology; confidence as specifically-dependent continuant |
| OWL2 / SROIQ(D) (W3C, 2009) | Standard | Description logic foundation; base for formal reasoning |
| AGM postulates (Alchourrón et al., 1985) | Theory | Rational belief revision; expansion vs revision vs contraction |
| Darwiche-Pearl postulates (1997) | Theory | Iterated belief revision; priority ordering for sequential updates |
| "Uncertainty Management in KG Construction" (TGDK, 2024) | Survey | Comprehensive: epistemic vs ontic uncertainty, UOKGE embeddings |
| "Fundamental Problems With Model Editing" (arXiv:2406.19354, 2024) | Paper | AGM applied to LLMs; ripple effects; 20% propagation accuracy |
| ChainEdit (arXiv:2507.08427, 2025) | Paper | Logical rule-guided ripple propagation for LLM belief revision |
| "Bridging Knowledge Gaps in LLMs via Function Calls" (ACM CIKM, 2024) | Paper | Closest existing implementation: detect confidence → classify → call function |
| InferWiki (2024) | Dataset | CWA vs OWA annotation for KG test triples |
| "A Review on Synergizing KGs and LLMs" (Springer, 2025) | Survey | Three integration modes; KAG framework |
| CyKG-RAG (CEUR-WS, 2024) | Paper | CVE/CWE/ATT&CK graph-RAG for security QA |
| "On the Potential of Logic in NeSy Using OWL KGs" (SAGE, 2025) | Paper | OWL reasoners as symbolic validators in neuro-symbolic systems |
| PR-OWL 2 (2015, CEUR-WS) | Paper | Probabilistic OWL; Bayesian extensions for ontology uncertainty |
| "UQ for Hallucination Detection in LLMs" (arXiv:2510.12040, 2025) | Survey | Calibrated vs overconfident uncertainty; consistency testing for ASSUMED gaps |
| PROV-STAR (FOIS, 2024) | Paper | RDF-star extension of PROV-O for triple-level provenance |
| "Semantic Mapping PROV-O to BFO" (Nature Sci Data, 2025) | Paper | Interoperability between provenance and formal ontology standards |
| Hybrid Temporal Validation (HAL thesis, 2025) | Thesis | Temporal validity of KG facts; validFrom/validUntil + TTL architecture |

---

## 9. What This Literature Doesn't Cover — Novel Territory

The existing literature does not address:

1. **Gap type as analysis metadata** — no existing system classifies gaps as STRUCTURAL/DERIVED/MEASURED/KNOWLEDGE/ASSUMED within the analysis output itself (as opposed to in a separate KB). The Prism pipeline's novelty is that the analysis *self-annotates* its own epistemic status.

2. **Prism-guided gap detection** — the idea that a cognitive prism (structured analytical frame) forces the model to expose specific gap types that vanilla analysis would not surface. No existing neuro-symbolic system uses analysis structure to guide gap exposure.

3. **Gap-filling as belief revision on analysis text** — existing belief revision work operates on KG triples. Applying AGM revision to a natural language analysis output (where "beliefs" are embedded in prose) requires a mapping from analysis claims to formal propositions that doesn't exist in current tooling.

4. **Conservation laws under gap filling** — the Prism project's finding that analysis properties are conserved (Specificity × Verifiability = Constant, see P206) implies that filling gaps may improve specificity at the cost of verifiability or vice versa. No existing KB completion or belief revision framework tracks conservation laws across the analysis as a whole.

These gaps define the novel contribution of the target system relative to the existing literature.

---

*Sources cited in text; see Section 8 for full reference list.*
