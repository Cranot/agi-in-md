# Sounio Lang Analysis — Relevance to AGI-in-md / Prism Project

**Date**: Mar 15, 2026
**Source**: https://www.souniolang.org/
**Purpose**: Deep analysis of Sounio programming language for ideas, overlaps, and integration possibilities with the Prism project.

---

## 1. What Is Sounio?

Sounio is a systems programming language for "epistemic computing" — programs that know what they know and what they don't. Created by Demetrios Chiuratto Agourakis, MIT-licensed, currently at v1.0.0-beta.5 (self-hosted native ELF codegen achieved as of Mar 2026).

**Scale**: 660K+ lines of language/runtime code, 168K+ stdlib, 15M ontology entities.

**Core innovation**: Uncertainty, confidence, and provenance are first-class language constructs, not libraries or annotations.

### The Type Hierarchy

| Tier | Type | What It Adds |
|------|------|-------------|
| 1 | `T` | Raw value |
| 2 | `Quantity<T, Unit>` | Dimensional safety |
| 3 | `Knowledge<T>` | Uncertainty (epsilon), confidence, source attribution |
| 4 | `Knowledge<T, Provenance>` | Full traceability chains |

Plus: `Validated<T>` (passed formal threshold), `Intervention<T>` and `Counterfactual<T>` (causal reasoning in the type system).

### Key Features
- **Confidence-gated control flow**: `if measurement.epsilon > 0.95 { approve() } else { remeasure() }` — runtime behavior branches on evidence quality
- **Uncertainty auto-propagation**: GUM-standard propagation through all computations
- **Effect system**: IO, mutation, allocation, GPU, probabilistic effects declared in function signatures
- **Refinement types**: Z3 SMT solver-backed constraint verification
- **Compile-time safety refusal**: Low-confidence prescriptions rejected by the compiler, not at runtime
- **Provenance tracking**: Every value carries its measurement chain

### Scientific Domains
Pharmacometrics, neuroimaging, quantum computing, climate science, genomics, fluid dynamics, causal inference, GPU computing, graphics/rendering.

### Compilation Pipeline
Source+Types -> IR+Effects -> Backend Selection -> Runtime Evidence. Targets: native x86/AArch64, GPU/PTX, WebAssembly.

---

## 2. Deep Parallels with Prism

The alignment between Sounio and Prism is striking — both projects attack the same fundamental problem from opposite ends.

### 2.1 The Shared Problem: Epistemic Honesty

**Sounio's framing**: "Software should express not only what it computes, but what it can justify."
**Prism's framing**: Analysis should reveal not only what it finds, but what it conceals and what it can't know.

Both projects recognize that **the gap between computation and knowledge is the critical unsolved problem.** Sounio attacks it at the language level (types that carry uncertainty). Prism attacks it at the analysis level (prompts that detect concealment and confabulation).

### 2.2 Confidence-Gating = Knowledge Gap Detection

Sounio's `Knowledge<T>` with confidence thresholds is structurally identical to what Prism's knowledge gap detection does:

| Concept | Sounio | Prism (Round 41) |
|---------|--------|-------------------|
| Confidence tracking | `Knowledge<T>` with epsilon | `knowledge_audit.md` confabulation risk scores |
| Threshold gates | `if confidence >= 0.95` | Gap classification: STRUCTURAL vs ASSUMED vs TEMPORAL |
| Refusal on low confidence | Compile-time rejection | "Do NOT trust claims with Specificity > threshold" |
| Provenance | `prov="lab_run_042"` | Fill sources: API_DOCS, CVE_DB, COMMUNITY |
| Propagation | Automatic through computation | `Specificity x Verifiability = Constant` (propagates through analysis) |
| Validated vs raw | `Validated<T>` distinct from `T` | Augmented L12 (verified facts) vs raw L12 (unverified) |

**The conservation law `Specificity x Verifiability = Constant` IS the analytical equivalent of Sounio's uncertainty propagation.** In both systems, precision comes at the cost of verifiability. Sounio makes this explicit in types. Prism makes this explicit in analysis output.

### 2.3 Type Hierarchy = Compression Level Hierarchy

| Sounio Type Tier | Prism Compression Level | What it adds |
|------------------|------------------------|-------------|
| `T` (raw) | L1-4 (basic operations) | Raw analytical operation |
| `Quantity<T, Unit>` (dimensioned) | L5-7 (dialectic, concealment) | Domain-specific framing |
| `Knowledge<T>` (uncertain) | L8-11 (construction, impossibility) | Meta-awareness of limits |
| `Knowledge<T, Provenance>` (traced) | L12-13 (conservation law, reflexive ceiling) | Self-referential fixed point |
| `Validated<T>` | L12-G (gap-aware) | Claims separated from verified facts |

Both hierarchies are **categorically stepped** — each tier enables a fundamentally different kind of reasoning that cannot exist at lower tiers.

### 2.4 "Compile to Certainty" = "Converge to Conservation Law"

Sounio: the compiler strips uncertainty from the final binary — what compiles is certain.
Prism: the pipeline converges on conservation laws — the structural invariant that survives all adversarial passes.

Both systems use **progressive elimination of uncertainty** as their core operation.

---

## 3. What Prism Could Learn from Sounio

### 3.1 Typed Confidence on Analysis Claims

**Idea**: Tag every claim in prism output with a confidence tier.

Currently, L12 output mixes structural insights (high confidence, unfalsifiable) with factual claims (low confidence, often confabulated). L12-G starts addressing this, but Sounio's approach is more rigorous: the TYPE SYSTEM prevents mixing validated and unvalidated values.

**Actionable**: Extend the gap extraction prompt (`prompts/gap_extract.md`) to output Sounio-style confidence tiers:
```
STRUCTURAL (self-evident from source): "Router uses trie-based dispatch"
MEASURED (derivable from source): "O(n) path traversal per route"
KNOWLEDGE (requires external data): "asyncio.RWLock exists in stdlib"
ASSUMED (unverifiable from source): "This pattern leads to maintenance debt"
```

This is essentially what `knowledge_boundary.md` already does — but Sounio's formal type hierarchy suggests we should make the tiers EXHAUSTIVE and ORDERED, not just categorical.

### 3.2 Provenance as First-Class Output

**Idea**: Every claim in analysis output should carry its source.

Sounio tracks `prov="lab_run_042"` on every value. Prism's L12-G already does this implicitly (verified facts are injected with sources), but the output doesn't systematically tag which claims come from:
- Source code (line N)
- Structural derivation (from conservation law)
- External knowledge (verified via API docs)
- Model assumption (no source)

**Actionable**: Add a `--provenance` flag to `/scan` that appends source attribution to each finding. This is cheap — just a prompt modification, no pipeline change.

### 3.3 Compile-Time Refusal Pattern

**Idea**: Refuse to output claims below a confidence threshold.

Sounio's vancomycin safety gate rejects low-confidence prescriptions AT COMPILE TIME — not as a warning, as a hard failure. The equivalent for Prism: L12-G should OMIT claims it can't verify rather than flagging them.

**Actionable**: L12-G already does this partially (augmented L12 with verified facts produces 0 confabulated claims). The next step is to make the gap detection pass a GATE: if a claim fails verification, it's removed from output entirely, not just flagged.

### 3.4 Effect System = Analytical Side Effects

**Idea**: Track what operations a prism performs beyond analysis.

Sounio requires functions to declare their effects (IO, mutation, GPU). Prism could similarly track what each prism does beyond finding insights:
- Does it confabulate? (effect: CONFABULATION_RISK)
- Does it require external data? (effect: EXTERNAL_QUERY)
- Does it modify the input's framing? (effect: FRAME_SHIFT)
- Is it adversarial? (effect: DESTRUCTION)

**Actionable**: This is a documentation/metadata improvement. Add an `effects` field to prism YAML frontmatter:
```yaml
optimal_model: sonnet
effects: [STRUCTURAL_ANALYSIS, CONFABULATION_RISK_LOW, FRAME_SHIFT]
```

### 3.5 The Four-Stage Pipeline

Sounio enforces: Measure -> Propagate -> Evaluate -> Act.
This maps directly to Prism's gap detection pipeline:

| Sounio Stage | Prism Pipeline Stage |
|-------------|---------------------|
| Measure | L12 analysis (raw findings) |
| Propagate | knowledge_boundary + knowledge_audit (uncertainty assessment) |
| Evaluate | gap_extract (threshold: which claims pass?) |
| Act | Augmented L12 (act only on verified claims) |

**Actionable**: Frame the `/scan file verified` pipeline explicitly as this four-stage model. The naming makes the epistemic intent clear.

---

## 4. What Sounio Could Learn from Prism

### 4.1 Prism's "Cheapest Model + Right Prompt" Finding

Sounio is building a 660K-line compiler. Prism achieves comparable epistemic rigor with 332-word prompts. The finding that Haiku + L12 beats Opus vanilla is directly relevant: could Sounio's verification be achieved through PROMPTS rather than a custom language?

For simple cases (non-safety-critical), a Prism-style approach to uncertainty tracking (prompt the model to track confidence, not a custom type system) could be 1000x cheaper to deploy.

### 4.2 Conservation Laws as Verification

Sounio uses Z3 SMT solver for constraint verification. Prism discovers conservation laws that serve as convergence signals — structural invariants that survive adversarial passes. These are complementary: Sounio proves MATHEMATICAL invariants, Prism discovers STRUCTURAL invariants.

### 4.3 The Reflexive Ceiling (L13)

Prism's L13 finding — that any framework applied to itself discovers the same impossibility it diagnoses — is directly relevant to Sounio. The question for Sounio: can its type system represent the uncertainty of its own uncertainty propagation? Prism says this terminates in one step (fixed point). Sounio's type hierarchy doesn't yet address self-referential uncertainty.

---

## 5. Competitive Analysis

### 5.1 Where They Overlap

Both projects:
- Make epistemic properties explicit rather than implicit
- Separate verified from unverified claims
- Track provenance
- Use progressive refinement toward certainty
- Target high-consequence domains

### 5.2 Where They Diverge

| Dimension | Sounio | Prism |
|-----------|--------|-------|
| Level | Language (compiler) | Prompt (cognitive compression) |
| Cost | 660K lines, years of development | 332 words, 40 rounds |
| Domain | Scientific computing | Any domain (code, reasoning, text) |
| Users | Scientists writing code | Anyone analyzing anything |
| Verification | Formal (Z3 SMT) | Empirical (conservation law convergence) |
| Deployment | Install compiler, rewrite code | One prompt, any model |
| Uncertainty model | Continuous (epsilon values) | Categorical (STRUCTURAL/ASSUMED/TEMPORAL) |

### 5.3 Competitive Threat Assessment

**None.** They operate at entirely different layers. Sounio is a programming language. Prism is a prompt engineering system. They could coexist perfectly — in fact, running Prism analysis ON Sounio code would be valuable (L12 could find concealment patterns in Sounio's own compiler).

---

## 6. Integration Possibilities

### 6.1 Prism as Sounio's Analysis Layer

Run L12 + gap detection on Sounio's 660K-line codebase. The compiler itself is "high-consequence software" — exactly the domain where Prism excels. This would:
- Validate Prism on a large, novel codebase (scaling test beyond 2700L)
- Give Sounio structural analysis they likely haven't done
- Demonstrate both tools working together

### 6.2 Sounio-Inspired Confidence Types in Prism Output

Adapt Sounio's `Knowledge<T>` concept for Prism's JSON output format:
```json
{
  "finding": "Router uses trie-based dispatch",
  "confidence": 0.95,
  "tier": "STRUCTURAL",
  "provenance": "source:routing.py:L42-L67",
  "verifiable": true
}
```

This is essentially what gap_extract already produces — but formalizing it with Sounio's vocabulary makes the epistemic commitment explicit.

### 6.3 Sounio as Prism's Formal Backend

For safety-critical applications, Prism could output its conservation laws in Sounio-verifiable format:
```
let law: Knowledge<ConservationLaw> = Knowledge(
  "Specificity x Verifiability = Constant",
  epsilon = 0.15,  // 4/4 targets confirmed
  prov = "round_41_j1_j4"
)
```

This is speculative and far-future, but the type system alignment makes it theoretically possible.

### 6.4 Cross-Pollination of Vocabulary

Both projects use similar concepts with different names:

| Concept | Sounio Term | Prism Term | Better Term? |
|---------|------------|-----------|-------------|
| Tracking what you don't know | Uncertainty propagation | Knowledge gap detection | Both are good |
| Separating verified from unverified | `Validated<T>` vs `T` | Augmented vs raw L12 | "Validated analysis" (from Sounio) |
| Self-referential limits | (not addressed) | L13 reflexive ceiling | Prism's is deeper |
| Making hidden things visible | "shows its work" | "cognitive prism" | Both are good |
| Evidence alongside code | Effect system | Provenance tracking | "Evidence-aware" (from Sounio) |

---

## 7. Philosophical Alignment

### Strong Alignment
- Both reject the assumption that computation = knowledge
- Both believe epistemic properties should be EXPLICIT, not implicit
- Both use progressive refinement toward certainty
- Both target high-consequence decisions
- Both are MIT-licensed, open-source, solo/small-team projects

### Key Divergence
- **Sounio believes you need a new language** to make epistemic properties explicit. The language IS the solution.
- **Prism believes you need the right prompt.** The prompt changes how existing models reason. No new language needed.

This is the fundamental philosophical split: **infrastructure vs. amplification.** Sounio builds new infrastructure (compiler, type system, runtime). Prism amplifies existing infrastructure (LLMs + prompts). Both are valid; they solve different scales of the problem.

Prism's approach is cheaper and faster to deploy. Sounio's approach is more rigorous and formally verifiable. For safety-critical scientific computing, Sounio wins. For general analysis and code review, Prism wins overwhelmingly.

---

## 8. Technical Ideas Worth Investigating

### 8.1 Confidence Propagation Rules (HIGH priority)

Sounio uses GUM-standard uncertainty propagation. Prism should formalize how confidence propagates through its pipeline:
- L12 raw output: confidence = BASE (model-dependent)
- After knowledge_boundary: confidence = BASE * CLASSIFICATION_ACCURACY
- After knowledge_audit: confidence = BASE * CLASSIFICATION_ACCURACY * VERIFICATION_COVERAGE
- After augmented re-analysis: confidence = HIGH (verified facts anchor output)

This gives each pipeline stage a formal confidence multiplier.

### 8.2 Dimensional Analysis for Prisms (MEDIUM priority)

Sounio prevents unit mismatches at compile time. Prism could prevent "prism mismatches" — running a code prism on reasoning text, or a reasoning prism on code. Currently this is handled by vocabulary triggers ("this code's" activates code mode). Could be formalized as prism dimensions:
- Domain dimension: CODE | TEXT | REASONING
- Operation dimension: STRUCTURAL | ADVERSARIAL | CONSTRUCTIVE
- Depth dimension: L1-L13

A "dimensionally invalid" prism application (e.g., TPC on Haiku) would be caught before execution.

### 8.3 Typed Refusal for Prism (HIGH priority)

Implement Sounio's compile-time refusal pattern: if the prism detects it cannot produce reliable output (wrong model, wrong domain, insufficient context), REFUSE rather than produce low-confidence output.

Current behavior: Haiku + L12 on reasoning sometimes enters "conversation mode" (asks permission, summarizes). This is a SOFT failure. Sounio would make it a HARD failure: "Cannot execute L12 on reasoning target with Haiku. Use l12_universal or SDL."

**Actionable**: Add pre-flight checks to prism.py that refuse known-bad combinations rather than attempting them.

### 8.4 The "Knowledge<T>" Prompt Pattern (HIGH priority)

Create a new prism that wraps every claim in Knowledge-style metadata:
```
For each finding, output:
- CLAIM: the finding
- CONFIDENCE: 0.0-1.0 based on source evidence
- PROVENANCE: where this comes from (source line, derivation, assumption)
- VERIFIABLE: can this be checked without the model? (yes/no)
- PROPAGATION: if this is wrong, what else breaks?
```

This is L12-G + Sounio vocabulary. Test whether the formal structure improves output quality.

---

## 9. Summary of Actionable Items

| # | Item | Priority | Effort | Source Concept |
|---|------|----------|--------|---------------|
| K1 | Formalize confidence tiers in gap_extract output (STRUCTURAL > MEASURED > KNOWLEDGE > ASSUMED) | HIGH | 1h | Sounio type hierarchy |
| K2 | Add `--provenance` flag for source attribution on findings | HIGH | 2h | Sounio provenance tracking |
| K3 | Pre-flight refusal for known-bad prism/model/domain combos | HIGH | 2h | Sounio compile-time refusal |
| K4 | "Knowledge<T>" prism pattern — confidence+provenance per claim | HIGH | 1h | Sounio Knowledge<T> type |
| K5 | Formalize confidence propagation through pipeline stages | MEDIUM | 2h | Sounio GUM propagation |
| K6 | Prism dimension typing (domain/operation/depth) | MEDIUM | 3h | Sounio dimensional analysis |
| K7 | Test L12 on Sounio's own codebase (scaling test) | LOW | 1h ($0.50) | Integration opportunity |
| K8 | Frame `/scan file verified` as Measure->Propagate->Evaluate->Act | LOW | 30m | Sounio four-stage pipeline |
| K9 | Add `effects` field to prism YAML frontmatter | LOW | 1h | Sounio effect system |

---

## 10. Conclusion

Sounio and Prism are deeply aligned philosophically but operate at entirely different layers of the stack. Sounio is building epistemic infrastructure FROM SCRATCH (a new language). Prism is achieving epistemic amplification ON TOP OF existing infrastructure (prompts on LLMs).

The most valuable takeaway is Sounio's formal vocabulary and type hierarchy for uncertainty. Prism already does most of what Sounio does epistemically — but without the formal language. Adopting Sounio's vocabulary (Knowledge<T>, Validated<T>, confidence tiers, provenance chains, compile-time refusal) would make Prism's gap detection pipeline more rigorous without changing its architecture.

The conservation law `Specificity x Verifiability = Constant` is Prism's version of Sounio's uncertainty propagation — both express the fundamental tension between precision and reliability. Neither project has cited the other, but they discovered the same structural truth independently.

**Bottom line**: No competitive threat. Strong philosophical alignment. Several high-value ideas to adopt (confidence tiers, provenance, typed refusal). Integration possible but not urgent. Monitor Sounio's progress — if they achieve formal verification of scientific software, Prism's gap detection pipeline could feed into their type system.
