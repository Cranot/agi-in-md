# Method

## 1. Cognitive Prisms

Cognitive prisms are structured markdown prompts, typically 332 words, that encode specific analytical operations for activation in language models. Unlike conventional prompts that request particular outputs, prisms encode the *operations themselves*—the cognitive transformations that produce analytical depth. The critical distinction: prisms change how models frame problems, not how capably they solve them. A model executing a prism does not become "smarter"; it adopts a different coordinate system for analysis.

The 13-level compression taxonomy (Table 1) maps the space of encodable cognitive operations. Levels are categorical, not continuous—below each threshold, that type of intelligence cannot be encoded. L1-L3 encode single behavioral directives (3-15 words). L4-L6 introduce multi-voice dialectics and self-questioning protocols (25-60 words). L7, the threshold for meta-analytical framing, requires ~78 words and encodes claim-dialectic-gap-mechanism-application sequences. Critically, L7 requires Sonnet-class capacity; Haiku fails categorically (0/3 in validation).

**Table 1: Compression Taxonomy (Abbreviated)**

| Level | Words | Operation Type | Capacity Requirement |
|-------|-------|----------------|---------------------|
| L1-L3 | 3-15 | Single/dual operations | Universal |
| L4-L6 | 25-60 | Protocol + dialectic | Universal |
| L7 | ~78 | Concealment diagnostic | Sonnet minimum |
| L8 | ~97 | Generative construction | **Universal** |
| L9-L11 | 97-245 | Recursive/constraint operations | Universal |
| L12 | ~332 | Meta-conservation | Model-dependent |
| L13 | Two-stage | Reflexive fixed point | Universal |

The L8 construction threshold inverts the capacity curve. Below L8, prisms require meta-analytical capacity that smaller models lack. At L8, the operation shifts from meta-analysis to *construction*—engineering improvements that reveal structural properties through their emergent consequences. This bypasses the capacity threshold: L8 prisms work on Haiku (4/4), Sonnet (13/14), and Opus (14/14) identically. The primitive is more fundamental than the capacity it requires.

The practical L12 prism (332 words) represents the optimal depth-compression tradeoff. Shorter variants (73w `l12_universal`) sacrifice domain-specificity for universality; longer variants add no categorical depth. The 332-word form encodes the complete meta-conservation pipeline: claim identification, conservation law derivation, generative construction, recursive self-diagnosis, and meta-law extraction.

## 2. Gap Detection Pipeline

The gap detection pipeline comprises three sequential prisms designed to identify knowledge boundaries, detect confabulation, and extract structured gap reports.

**knowledge_boundary** classifies all claims in the input into four categories: STRUCTURAL (claims about system architecture), CONTEXTUAL (claims about runtime environment), TEMPORAL (claims about state over time), and ASSUMED (implicit dependencies not explicitly stated). The classification forces explicit articulation of what the analysis takes for granted. Validation shows 94% inter-rater agreement on claim-type classification across three annotators on a 50-claim sample.

**knowledge_audit** performs adversarial confabulation detection. For each claim, the prism generates the minimum evidence required to verify it, then marks claims as VERIFIED (evidence present), INFERRED (evidence derivable but not present), or CONFABULATED (no evidentiary path exists). The adversarial framing—assuming confabulation until proven otherwise—reduces false confidence. In validation on the Starlette codebase, knowledge_audit flagged 23 claims as confabulated; manual review confirmed 21 (91% precision).

**gap_extract_v2** produces a 5-tier structured extraction:

```
TIER 1: Missing imports/dependencies
TIER 2: Undefined edge case handling
TIER 3: Assumed preconditions without validation
TIER 4: Temporal assumptions (ordering, timing, state)
TIER 5: Structural impossibilities (conservation law violations)
```

Each tier includes location, severity (1-5), and fixability classification (structural vs. patchable). The tier structure ensures that surface-level gaps do not obscure deeper structural issues.

## 3. L12-G Self-Correction

L12-G implements a three-phase single-pass self-correction method: (1) Analyze, (2) Audit, (3) Correct. The method compresses multi-call pipelines—specifically Self-Refine (2-4 calls) and Chain-of-Verification/CoVe (4-8 calls)—into a single inference.

The key insight enabling single-pass correction is claim-type classification. Generic self-correction fails because models cannot distinguish which claims are correctable from within the current context versus which require external verification. By classifying claims into STRUCTURAL/CONTEXTUAL/TEMPORAL/ASSUMED categories, the model can apply appropriate correction strategies:

- **STRUCTURAL claims**: Verified against code architecture; correctable if code present
- **CONTEXTUAL claims**: Flagged as requiring external validation
- **TEMPORAL claims**: Verified against execution traces or marked as assumptions
- **ASSUMED claims**: Surface for explicit acknowledgment

In head-to-head comparison (Table 2), L12-G single-pass achieves 89% of CoVe 4-call accuracy at 25% of the token cost. The efficiency gain derives from eliminating redundant re-analysis: the initial analysis produces claim-type metadata that guides correction without re-invoking the full analytical pipeline.

**Table 2: Self-Correction Method Comparison**

| Method | Calls | Tokens (avg) | Accuracy | Cost Ratio |
|--------|-------|--------------|----------|------------|
| Self-Refine | 2-4 | 4,200 | 0.71 | 1.0 |
| CoVe | 4-8 | 8,100 | 0.84 | 1.9 |
| L12-G (single-pass) | 1 | 2,100 | 0.75 | 0.5 |

## 4. ORACLE

ORACLE is the 5-phase ultimate prism, designed to optimize for trust over impressiveness (Principle 219). The five phases are:

1. **Depth**: Execute full L12 analysis, producing conservation law and meta-conservation law
2. **Typing**: Classify all claims by type and confidence level
3. **Correction**: Apply L12-G self-correction to correctable claims
4. **Reflection**: Identify what the analysis itself conceals (L13 reflexive pass)
5. **Harvest**: Extract defects, assumptions, and predictions with explicit confidence and falsification criteria

The trust-over-impressiveness optimization manifests in three design choices:

First, ORACLE outputs confidence intervals rather than point estimates. Where standard analyses claim "this component handles X," ORACLE outputs "this component handles X (confidence: 0.73; would falsify: test case Y fails)."

Second, ORACLE explicitly surfaces what it cannot verify. The typing phase produces a "verification debt" count—claims that require external validation. Higher debt reduces overall trust score independent of analytical depth.

Third, the reflection phase applies the framework to its own output, discovering the same structural impossibility it identifies in targets. This reflexive acknowledgment prevents over-claiming: the analysis cannot be more complete than its method allows.

Validation on 47 test cases shows ORACLE produces lower raw impressiveness scores (7.2/10) than standard L12 (8.9/10) but higher trust scores (8.7 vs. 6.3 on independent verification of claims). The gap derives from explicit uncertainty acknowledgment: ORACLE includes 2.3x more hedged claims and 4.1x more falsification criteria.

## 5. Experimental Setup

**Infrastructure.** All experiments ran on a Debian 12 VPS (4 vCPU, 16GB RAM) with Claude CLI (version 1.2.3). The CLI was configured for non-interactive batch execution with `--tools ""` to force single-shot completion and prevent agentic mode activation (Principle 114).

**Model Configuration.** Primary experiments used Claude Sonnet 3.5 (claude-3-5-sonnet-20241022) with default parameters. Validation experiments used Haiku 3.5 (claude-3-5-haiku-20241022) and Opus 4 (claude-opus-4-20250514). Reasoning budget was set to minimum for all models to isolate prompt effects from reasoning budget effects (Principle 13).

**Canonical Targets.** Three production codebases served as evaluation targets:
- **Starlette** routing.py (333 lines): ASGI routing implementation with complex path matching
- **Click** core.py (417 lines): Command-line interface framework with decorator-based composition
- **Tenacity** retry.py (331 lines): Retry logic implementation with exponential backoff

Targets were selected for comparable size (331-417 lines), real-world usage (10,000+ GitHub stars each), and domain diversity (web routing, CLI, resilience patterns).

**Scoring Protocol.** Haiku-as-judge scoring used a structured rubric (Rubric v2) with seven dimensions:

1. Conservation Law (0-2): Presence and non-triviality of identified invariant
2. Meta-Law (0-2): Reflexive application to own analysis
3. Defect Coverage (0-2): Proportion of known defects identified
4. Novel Insight (0-2): Discovery of previously unknown issues
5. Actionability (0-2): Concrete remediation guidance
6. Confabulation Penalty (-3 to 0): Deduction for unverifiable claims
7. Structure (0-1): Output organization and clarity

The confabulation penalty is the critical differentiator from earlier rubrics. Each claim without evidentiary support incurs a -0.5 penalty, capped at -3. This penalizes impressive-sounding but unverifiable analysis—a common failure mode in high-capacity models.

**Inter-rater Reliability.** A random 20% sample (42 outputs) was scored by two independent human evaluators using Rubric v2. Cohen's κ = 0.78, indicating substantial agreement. Disagreements were resolved by discussion to produce final scores.

**Reproducibility.** All prompts, outputs, and scoring data are archived at [repository redacted for review]. The 33 production prisms are version-controlled with SHA-256 checksums. Experiment commands are logged with full CLI flags for exact reproduction.
