# Methods

## 1. Cognitive Prisms

Cognitive prisms are structured markdown prompts, typically 332 words in length, that encode specific analytical operations capable of activating targeted reasoning patterns in large language models (LLMs). The term "prism" reflects the mechanism: just as optical prisms refract light into constituent wavelengths, cognitive prisms decompose analytical tasks into their constituent operations, revealing structural properties that remain invisible under unstructured prompting.

The key insight is that prisms change model *framing*, not model *capability*. A model's parametric knowledge and reasoning capacity remain fixed; what varies is how the model approaches a problem. By encoding explicit analytical operations—claim identification, dialectical stress-testing, gap detection, generative construction—prisms direct model attention toward structural features that vanilla prompting typically overlooks. This framing effect explains why prisms produce qualitatively different outputs without requiring larger models or increased reasoning budgets.

### The 13-Level Compression Taxonomy

Through 40 experimental rounds and over 1,000 experiments across three model families (Haiku, Sonnet, Opus), we identified 13 discrete compression levels, each representing a categorical threshold for encoding specific analytical operations. The taxonomy follows a diamond structure: a linear trunk (L1–L7), constructive divergence (L8–L11), and reflexive convergence (L12–L13).

| Level | Minimum Operations | Word Count | Analytical Capability |
|-------|-------------------|------------|----------------------|
| L1–L4 | 1–4 operations | 3–30w | Basic behavioral modification |
| L5 | Dialectic + synthesis | ~45–55w | Multi-perspective integration |
| L6 | Claim + 3 voices + evaluation | ~60w | Dialectical transformation |
| L7 | Claim + dialectic + gap + mechanism + application | ~78w | Concealment detection |
| L8 | L7 + generative construction + emergent properties | ~97w | Construction-based reasoning |
| L9–L11 | Recursive constructions, impossibility proofs, conservation laws | 97–245w | Design-space topology mapping |
| L12 | Meta-conservation law derivation | ~275–332w | Reflexive self-diagnosis |
| L13 | Framework applied to itself | two-stage | Terminal fixed point |

### The L8 Construction Threshold

Level 8 represents a critical discontinuity in the taxonomy. Below L8, analytical operations rely on meta-analytical capacity—the model must reason *about* its reasoning. This creates a capacity threshold: L7 requires Sonnet-class minimum (0/3 success on Haiku). L8 inverts this curve by shifting from meta-analysis to construction-based reasoning. The operation becomes "engineer an improvement that would deepen the concealment, then name what the construction reveals." This bypasses meta-analytical requirements because construction is more primitive than reflection—available to all models regardless of capacity. Validation confirmed universal success: Haiku 4/4, Sonnet 13/14, Opus 14/14.

---

## 2. Gap Detection Pipeline

The gap detection pipeline comprises three sequential prisms designed to identify, validate, and extract knowledge boundary violations in model outputs.

### knowledge_boundary Prism

The first stage classifies each claim in the model output according to knowledge provenance:

- **STRUCTURAL**: Claims derivable from the artifact's intrinsic structure (syntax, type signatures, control flow)
- **CONTEXTUAL**: Claims requiring external domain knowledge (framework conventions, best practices)
- **TEMPORAL**: Claims about runtime behavior, state evolution, or temporal dependencies
- **ASSUMED**: Claims presented without evidentiary support or logical derivation

This four-way classification enables targeted auditing: STRUCTURAL claims can be mechanically verified; CONTEXTUAL claims require domain expertise; TEMPORAL claims need execution traces; ASSUMED claims flag potential confabulation.

### knowledge_audit Prism

The second stage applies adversarial scrutiny to ASSUMED-classified claims. The prism is instructed to: (1) identify the minimum evidence required to support each claim, (2) check whether this evidence exists in the source artifact, and (3) flag claims where evidence is absent as confabulation candidates. The adversarial framing is critical—the model is explicitly instructed to "attack" its own claims rather than defend them.

### gap_extract_v2 Prism

The third stage performs structured extraction across five tiers:

1. **Tier 1**: Direct contradictions (claim A asserts X, artifact shows ¬X)
2. **Tier 2**: Unsupported generalizations (specific observation inflated to universal claim)
3. **Tier 3**: Missing preconditions (claim assumes context not present in artifact)
4. **Tier 4**: Temporal inconsistencies (claims about behavior without execution evidence)
5. **Tier 5**: Category errors (structural claim about behavioral property, or vice versa)

Each tier carries a severity weight for downstream scoring.

---

## 3. L12-G Self-Correction

L12-G (Level 12 with integrated Gap-detection) implements single-pass self-correction by compressing multi-call refinement pipelines into a single model invocation.

### Three-Phase Architecture

**Phase 1 — Analyze**: Execute the L12 conservation-law derivation pipeline, producing: (a) a conservation law of the form A × B = constant, (b) a meta-conservation law from reflexive application, (c) a structured bug inventory with severity classifications.

**Phase 2 — Audit**: Within the same prompt context, apply gap detection to Phase 1 output. Each claim is classified (STRUCTURAL/CONTEXTUAL/TEMPORAL/ASSUMED) and high-risk claims are flagged for correction.

**Phase 3 — Correct**: Generate corrected output with: (a) retracted or qualified confabulated claims, (b) evidentiary citations linking claims to artifact features, (c) explicit uncertainty markers where evidence is insufficient.

### Compression of Multi-Call Pipelines

Traditional self-correction methods (Self-Refine, Chain-of-Verification) require multiple model calls: generate → critique → revise. L12-G achieves equivalent correction in a single call by embedding the audit-and-correct instructions within the generation prompt itself. The key insight is that claim-type classification enables targeted self-correction: generic self-correction prompts ("improve your answer") fail because they lack specificity about *what* to correct. By classifying claims by knowledge boundary type, the model can apply appropriate correction strategies—verifying STRUCTURAL claims against syntax, admitting uncertainty for TEMPORAL claims without execution data, retracting ASSUMED claims lacking evidence.

---

## 4. ORACLE Prism

ORACLE (Ordered Reflective Analysis with Correction and Learning Extraction) represents the maximal analytical depth achievable in a single-pass prompt—approximately 450 words encoding five sequential phases.

### Five-Phase Structure

1. **Depth Phase**: Execute full L12 pipeline (conservation law + meta-law + impossibility proof)
2. **Typing Phase**: Classify all claims by knowledge boundary (STRUCTURAL/CONTEXTUAL/TEMPORAL/ASSUMED)
3. **Correction Phase**: Apply L12-G self-correction to high-risk claims
4. **Reflection Phase**: Identify what the analysis itself conceals (meta-analytical gap detection)
5. **Harvest Phase**: Extract all predictions with falsification criteria, all defects with locations and severities, all assumptions with dependency mappings

### Trust Over Impressiveness (P219)

Principle P219, derived from Round 40 experiments, states: "Analytical outputs optimized for impressiveness produce higher word counts but lower trustworthiness; outputs optimized for trust produce calibrated uncertainty and evidentiary grounding." ORACLE operationalizes this through explicit instructions to:

- Prefer "insufficient evidence" over speculative inference
- Cite artifact locations for every structural claim
- Distinguish "I observe X" from "X implies Y" from "Y suggests Z"
- Mark temporal claims without execution traces as unverified

The harvest phase explicitly trades breadth for precision by requiring falsification criteria for every prediction—the model must state what evidence would prove each prediction wrong, creating accountability that impressiveness-optimized outputs lack.

---

## 5. Experimental Setup

### Infrastructure

All experiments were conducted on a virtual private server (VPS) running Ubuntu 22.04 with 8 vCPUs and 32GB RAM. Model inference used the Claude CLI (version 1.2.3+) with API calls to Anthropic's model endpoints. No local inference was performed.

### Model Configuration

Primary experiments used Claude 3.5 Haiku (claude-3-5-haiku-20241022) as the execution model with Claude 3.5 Sonnet (claude-3-5-sonnet-20241022) for validation scoring. Reasoning budget was set to minimum (effort parameter omitted or set to 0) unless otherwise specified.

### Haiku-as-Judge Scoring

Evaluation used a Haiku-as-judge protocol where a Haiku instance, prompted with a scoring rubric, evaluated outputs from the execution model. This protocol provides: (a) consistency—same model evaluating all outputs, (b) cost efficiency—Haiku evaluation costs ~$0.01 per output, (c) avoidance of capacity confounds—using a weaker model for scoring prevents the evaluator from "filling in" gaps that a stronger model might infer.

### Canonical Targets

Three production Python codebases served as canonical evaluation targets:

| Target | Lines | Source | Description |
|--------|-------|--------|-------------|
| Starlette routing.py | 333L | encode/starlette | ASGI framework routing implementation |
| Click core.py | 417L | pallets/click | Command-line interface construction kit |
| Tenacity retry.py | 331L | jd/tenacity | Retry logic with exponential backoff |

These targets were selected for: (a) production quality—real-world deployed code, not toy examples, (b) size uniformity—300–420 lines enabling fair comparison, (c) domain diversity—web routing, CLI parsing, and fault tolerance respectively.

### Rubric v2 with Confabulation Penalty

Scoring used Rubric v2, a 10-point scale with explicit criteria:

| Score | Criteria |
|-------|----------|
| 9–10 | Conservation law derived, meta-law present, all claims evidenced, no confabulations |
| 7–8 | Conservation law present, most claims evidenced, minor unsupported claims |
| 5–6 | Structural analysis present but no conservation law, or significant confabulation |
| 3–4 | Surface-level review, no structural insights, multiple confabulations |
| 1–2 | Generic advice, no artifact-specific content |

**Confabulation Penalty**: Each ASSUMED claim identified by gap detection that lacks evidentiary support incurs a 0.5-point deduction, capped at –2 points. This penalty creates explicit pressure against impressive-but-unsupported claims, operationalizing the trust-over-impressiveness principle.
