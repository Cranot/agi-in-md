# L12g Structural Analysis: Protein Folding Claim

## PHASE 1 — STRUCTURAL ANALYSIS

### Three Simultaneously Claimed Properties
1. **Higher accuracy**: 0.89 GDT-TS, outperforming AlphaFold2 by 3.2%
2. **Lower cost**: 10x less compute
3. **Conservation law holds**: "folding accuracy × computational cost = constant for a given sequence length"

### Proof of Impossibility
The claim is **self-refuting**. If accuracy × cost = constant, then:
- Their system: 0.89 × 0.1 = **0.089**
- AlphaFold2: ~0.858 × 1.0 = **0.858**

These products differ by **9.6x**. The stated conservation law directly contradicts the claimed performance. You cannot have higher accuracy AND lower cost while maintaining a constant product—the algebra doesn't permit it.

### Conservation Law
**Accuracy × Compute = Constant** (they stated it)

This means: any accuracy gain requires proportional compute increase. The constant is method-dependent but task-scoped.

### Concealment Mechanism
**Subset reframing**: The qualifier "on multi-domain proteins" restricts the comparison domain. The method doesn't beat AlphaFold2 on protein folding—it beats AlphaFold2 on a specific subcategory where AlphaFold2's architecture is suboptimal. The 10x compute claim likely:
- Excludes preprocessing/training costs
- Measures inference-only on favorable inputs
- Uses different hardware normalization

### Improvement That Recreates the Problem
Add a domain-classification pre-filter that routes multi-domain proteins to this method and single-domain to AlphaFold2.

**New claim**: "Our ensemble achieves 5% improvement over AlphaFold2 on all proteins at 5x less compute."

**Deeper problem**: The ensemble now has two conservation laws operating:
1. Multi-domain routing accuracy × classifier compute
2. Single-domain routing accuracy × classifier compute

The classifier introduces a **new constant**: routing accuracy × ensemble overhead. We've concealed the original trade-off inside the routing decision—the ensemble fails on boundary cases where domain classification is ambiguous, recreating the accuracy-cost trade-off at the classification layer.

---

## PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | Source Needed |
|-------|---------------|------------|---------------|
| Three properties are mutually exclusive | STRUCTURAL | 1.0 | None — algebraic derivation |
| Conservation law stated in text | STRUCTURAL | 1.0 | None — direct quote |
| Self-contraction is provable | STRUCTURAL | 1.0 | None — follows from above |
| AlphaFold2 baseline ~0.858 GDT-TS | CONTEXTUAL | 0.7 | CASP15 official results |
| Multi-domain proteins are a distinct category | CONTEXTUAL | 0.6 | Domain biology literature |
| 3.2% improvement is significant vs noise | CONTEXTUAL | 0.5 | CASP evaluation methodology |
| 10x compute comparison is fair | CONTEXTUAL | 0.4 | Their methodology section |
| 847 proteins / 12 families is adequate | CONTEXTUAL | 0.5 | Statistical power analysis |
| Concealment via subset reframing | STRUCTURAL | 0.85 | Inferred from qualifier |

**If wrong about concealment mechanism**: Alternative explanations include:
- Method actually violates conservation (new paradigm) — but then why state the law?
- Compute measured differently (training excluded) — still concealment
- GDT-TS vs other metrics cherry-picked — metric selection concealment

---

## PHASE 3 — SELF-CORRECTION

### Verified Findings (SAFE + HIGH CONFIDENCE)

**Conservation Law**: `Folding_Accuracy × Computational_Cost = Constant` (stated in source)

**Core Defect**: The claim contains an internal contradiction derivable from source text alone:
- Claim A: 3.2% higher accuracy
- Claim B: 10x lower cost  
- Claim C: Accuracy × Cost = constant
- **A + B + C cannot all be true**

**Structural Concealment**: The phrase "on multi-domain proteins" restricts the validity domain. This is a **scope qualifier** that prevents direct comparison to the general "protein folding" problem.

### Removed/Downgraded Claims
- ~~AlphaFold2 actual GDT-TS~~ — UNVERIFIABLE from source (external benchmark)
- ~~3.2% is statistically significant~~ — UNVERIFIABLE (need variance data)
- ~~10x compute is fair comparison~~ — UNVERIFIABLE (need methodology)
- Specific concealment is subset-reframing — CONFIDENCE 0.85 (multiple alternative explanations exist)

### Corrected Defect Table

| Location | Defect | Severity | Type |
|----------|--------|----------|------|
| Abstract | Claims A, B, C are mutually exclusive | Critical | Logical |
| Abstract | Conservation law contradicts performance claims | Critical | Structural |
| "on multi-domain proteins" | Scope qualifier conceals domain restriction | High | Structural |
| "10x less compute" | Undefined measurement boundary | Medium | Contextual |
| "0.89 GDT-TS" | Single metric, no variance reported | Medium | Contextual |

---

## FINAL OUTPUT

**Conservation Law**: `Accuracy × Compute = Method_Constant` (explicitly stated)

**Corrected Defects** (source-grounded only):

| # | Defect | Evidence | Type |
|---|--------|----------|------|
| 1 | Internal contradiction: higher accuracy + lower cost + conservation law | 0.89 × 0.1 ≠ ~0.86 × 1.0 | SAFE |
| 2 | Scope qualifier "multi-domain" restricts generality | Present in source text | SAFE |
| 3 | Conservation law undermines own performance claims | Stated law falsifies stated results | SAFE |
