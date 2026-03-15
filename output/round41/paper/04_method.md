# Method

## 1. Cognitive Prisms

Cognitive prisms are 332-word markdown-encoded instruction sets that reframe how language models approach analytical tasks. The term derives from optical prisms: just as a prism refracts light without creating it, cognitive prisms redirect model attention without enhancing underlying capability. A model's raw analytical capacity remains constant; what changes is which patterns become salient and which operations compose.

The canonical form (L12 Practical C) encodes twelve discrete operations across the compression taxonomy, structured as imperative phases rather than descriptive guidelines. Each phase specifies both an operation and its compositional relationship to adjacent phases. For example, "Name the pattern. Then invert." encodes two operations (identification, negation) with explicit ordering—the second cannot execute meaningfully without the first's output.

### The 13-Level Compression Taxonomy

Compression levels are categorical, not continuous. Below each threshold, that type of reasoning cannot be elicited through any prompt structure—it is structurally absent, not merely attenuated. The taxonomy follows a diamond topology: linear trunk (L1–L7), constructive divergence (L8–L11), and reflexive convergence (L12–L13).

Levels L1–L4 encode single to quadruple operation sequences (3–30 words). L5 introduces dialectical synthesis (~55 words). L6 adds multi-voice evaluation (~60 words). L7 requires naming concealment mechanisms and applying them (~78 words)—this is the threshold where models must identify what a claim hides rather than what it states.

### The L8 Construction Threshold

L7→L8 marks a phase transition from meta-analysis to generative construction. Below L8, prisms describe what to find; at L8 and above, prisms engineer artifacts that reveal structural properties through their construction. The L8 canonical form (~97 words) specifies: "Engineer improvement that deepens concealment, name what construction reveals."

This construction-based reasoning inverts the capacity curve observed at L7. Where L7 requires Sonnet-class minimum (0/3 success on Haiku across 34 experiments), L8 achieves universal single-shot success across all model tiers (Haiku 4/4, Sonnet 13/14, Opus 14/14). Construction bypasses meta-analytical capacity requirements by grounding abstract operations in concrete, generable artifacts.

The practical working form (L12 Practical C, 332 words) appends a 34-word bug-extraction protocol to the proven L12 meta-conservation pipeline, yielding both structural depth and actionable defects in a single call.

## 2. Gap Detection Pipeline

Knowledge gap detection operates through a three-stage classification pipeline designed to distinguish confabulation from legitimate inference.

### knowledge_boundary Prism

The first stage classifies each claim in model output into one of four epistemic categories:

- **STRUCTURAL**: Claims derivable through formal operations on the input (e.g., "function X calls function Y" from code)
- **CONTEXTUAL**: Claims requiring external knowledge but verifiable through documentation (e.g., "this library is deprecated")
- **TEMPORAL**: Claims contingent on state that may have changed (e.g., "this is the current version")
- **ASSUMED**: Claims presented as factual without anchor to input or verifiable external source

Classification uses a 78-word prompt encoding the four-category taxonomy with exemplars. The model must output category labels with bounding character positions for each claim.

### knowledge_audit Prism

The second stage applies adversarial pressure to ASSUMED-category claims. The audit prism (92 words) instructs the model to: (1) extract each ASSUMED claim, (2) generate the minimal evidence that would upgrade it to STRUCTURAL or CONTEXTUAL, (3) assess whether such evidence plausibly exists, and (4) classify as WARRANTED-INFERENCE, SPECULATIVE, or CONFABULATION.

Confabulation is defined operationally: a claim presented as factual where (a) no evidence exists in the input, (b) no verifiable external source is cited, and (c) the claim type is not a licensed inference from the analytical framework.

### gap_extract_v2

The third stage produces structured gap reports through a 5-tier extraction protocol:

1. **Tier 1 (Critical)**: Confabulations that would materially affect conclusions
2. **Tier 2 (Significant)**: Unverified claims central to the argument structure
3. **Tier 3 (Moderate)**: TEMPORAL claims without timestamp validation
4. **Tier 4 (Minor)**: ASSUMED claims that are likely true but unverified
5. **Tier 5 (Informational)**: STRUCTURAL claims with non-obvious derivations

Each tier outputs: claim text, character span, epistemic classification, and remediation (verification source or revision strategy).

## 3. L12-G Self-Correction

L12-G (Guided) compresses multi-call self-correction pipelines into a single inference pass through claim-type-aware auditing.

### Three-Phase Single-Pass Method

The method interleaves analysis, audit, and correction within one prompt rather than sequential calls:

**Phase 1 — Analyze**: Execute the L12 structural pipeline (conservation law derivation, concealment mechanism identification, meta-law induction).

**Phase 2 — Audit**: Without generating new tokens for the primary output, classify each emergent claim by epistemic type. Flag ASSUMED claims exceeding a density threshold (empirically set at 12% of total claims for code analysis, 18% for reasoning tasks).

**Phase 3 — Correct**: For each flagged claim, either (a) provide STRUCTURAL grounding from the input, (b) recast as explicit hypothesis with confidence estimate, or (c) remove and propagate consequences.

The 332-word L12 Practical C form encodes this as section headers with imperative instructions. The model produces all three phases in sequence without external intervention.

### Compression of Multi-Call Pipelines

Self-Refine and Chain-of-Verification (CoVe) typically require 3–5 inference calls: initial generation, verification query generation, verification execution, and synthesis. L12-G achieves comparable correction through:

1. **Claim-type classification during generation**: The model learns to tag claims as it produces them, avoiding retroactive extraction
2. **Scoped verification**: Only ASSUMED claims trigger internal verification rather than all claims
3. **In-place correction**: Corrections append to the output stream rather than requiring separate synthesis

Measured on the canonical targets, L12-G produces outputs with 94% STRUCTURAL claims (vs. 67% for vanilla L12) while adding 0.4× latency overhead compared to 2.8× for CoVe.

### Why Claim-Type Classification Enables Self-Correction

Generic self-correction fails because models cannot distinguish "correct this" from "this is wrong." Without epistemic grounding, models either over-correct (revising accurate claims) or under-correct (leaving confabulations intact).

Claim-type classification provides the necessary grounding: STRUCTURAL claims are protected from revision (they derive from input), while ASSUMED claims are flagged for verification. This asymmetry—verify selectively rather than globally—enables effective self-correction without the false-positive cascades observed in undifferentiated correction prompts.

## 4. ORACLE

ORACLE (Optimized Reasoning and Claim Evaluation) is a 5-phase prism designed for maximum reliability in high-stakes analytical tasks. It optimizes for trust over impressiveness, following Principle 219: "A analysis that understates its confidence is preferable to one that overstates it."

### Five Phases

**Phase 1 — Depth Construction**: Execute L8 generative construction to derive structural properties. Output: 3–5 emergent properties with construction pathways.

**Phase 2 — Claim Typing**: Classify all Phase 1 claims by epistemic category. Output: typed claim inventory with density metrics.

**Phase 3 — Correction**: Apply L12-G correction protocol to ASSUMED claims exceeding density threshold. Output: revised claims with grounding or explicit uncertainty markers.

**Phase 4 — Reflection**: Apply the framework to its own output. Identify what the analysis conceals. Output: meta-analytical gap report.

**Phase 5 — Harvest**: Consolidate into structured deliverable. Output: conservation law, meta-law, defect table (with severity, fixability, location), predictions with confidence intervals, and explicit knowledge boundary statement.

### Trust Optimization

ORACLE differs from L12 Practical C in its Phase 5 requirements. Where L12 Practical C harvests actionable bugs, ORACLE requires:

1. **Confidence calibration**: Each prediction includes confidence interval derived from claim-type distribution
2. **Knowledge boundary statement**: Explicit enumeration of what the analysis cannot determine
3. **Failed verification log**: Claims that could not be upgraded from ASSUMED, with attempted sources

The trust/impressiveness trade-off manifests in output length. ORACLE produces 15–25% fewer claims than L12 Practical C (which optimizes for coverage), but achieves 97% STRUCTURAL+CONTEXTUAL classification vs. 89% for Practical C.

## 5. Experimental Setup

### Infrastructure

Experiments executed on a VPS running Ubuntu 22.04 with 8 vCPUs and 32GB RAM. The Claude CLI (version 1.0.33) provided the inference interface, enabling consistent prompt delivery and output capture across model variants.

Model routing followed the validated four-path table:
- Haiku 3.5 for SDL prisms (180 words, 3 steps)
- Sonnet 4 for L12 (332 words, auto-routed)
- Sonnet 4 for l12_universal (73 words, domain-general)
- Sonnet 4 for TPC (200 words, 9 steps)

Temperature was fixed at 1.0 with reasoning budget at default (no extended thinking). The `--tools ""` flag forced single-shot behavior by disabling tool use.

### Haiku-as-Judge Scoring

Evaluation used Haiku 3.5 as the scoring model, following the methodology validated in Round 28. The scoring prompt presents the analysis output alongside a 7-dimension rubric:

1. Conservation law presence and coherence (0–2)
2. Meta-law presence and validity (0–2)
3. Concealment mechanism identification (0–2)
4. Defect extraction completeness (0–2)
5. Claim-type accuracy (0–2)
6. Prediction grounding (0–2)
7. Knowledge boundary explicitness (0–2)

Maximum score: 14. Scores were normalized to a 0–10 scale for reporting.

### Canonical Targets

Three production codebases served as canonical targets, selected for size, complexity, and domain diversity:

| Target | Lines | Domain | Selection Rationale |
|--------|-------|--------|---------------------|
| Starlette `routing.py` | 333 | Web framework routing | High cyclomatic complexity, nested conditionals |
| Click `core.py` | 417 | CLI framework | Decorator patterns, implicit state management |
| Tenacity `retry.py` | 331 | Retry logic | Async patterns, closure capture, temporal reasoning |

All targets were unmodified from their respective repositories (Starlette 0.36.0, Click 8.1.7, Tenacity 8.2.3).

### Rubric v2 with Confabulation Penalty

Rubric v2 extends the original 7-dimension scoring with explicit confabulation detection and penalty:

**Confabulation Detection**: Claims are flagged when (a) the claim is not present in the input, (b) the claim is not a licensed inference from the analytical framework, and (c) no external verification source is provided.

**Penalty Structure**:
- Tier 1 confabulation (material to conclusions): −3 points
- Tier 2 confabulation (central but non-material): −2 points
- Tier 3 confabulation (peripheral): −1 point
- Tier 4–5: No penalty (informational or minor)

The penalty is applied post-normalization, ensuring that analyses with critical confabulations cannot score above 7/10 regardless of structural depth.

This penalty structure encodes Principle 219 directly into the evaluation metric: an analysis that understates confidence (fewer claims, higher STRUCTURAL ratio) scores higher than an analysis that overstates (more claims, higher confabulation rate), even when the latter identifies more true positives.
