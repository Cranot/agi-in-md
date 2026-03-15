# Knowledge Audit: Level 12 Analysis of prism.py

## Methodology

For each factual assertion in the analysis, I determine:
1. **SAFE** — Verifiable from source code alone (structural observations, line references, code logic)
2. **KNOWLEDGE CLAIM** — Requires external knowledge (APIs, libraries, patterns, specifications, best practices)

---

## SAFE Claims (Skip)

These are verifiable from source and require no external knowledge:
- Line number references (28-55, 158-166, 362-408, etc.)
- Code structure descriptions ("try colorama → try ctypes → disable flag")
- Function existence and signatures
- Variable names and values
- Logic flow descriptions (if X raises, Y happens)
- Bug #1: ANSI fallback skipping ctypes on non-ImportError — directly readable from exception handling logic
- Bug #5: No default for unknown prism names — readable from dict structure
- Bug #14: Empty list return ambiguity — readable from function return

---

## KNOWLEDGE CLAIMS: Attack Construction

### Claim 1: "Leaky Abstraction"

**Exact claim:** "Forcing them into a single abstraction would create a Leaky Abstraction that's worse than the status quo."

**Dependency:** The concept that unified error handling across heterogeneous subsystems produces worse outcomes than specialized handling — a claim about software architecture patterns and their trade-offs.

**Failure mode:** 
- Counter-examples where unified resilience patterns succeed (circuit breakers, retry policies, fallback chains in distributed systems)
- The claim depends on "worse" being measurable — but no metric is provided
- Some abstraction leakiness is tolerable; the claim assumes it's fatal

**Confabulation risk:** **MEDIUM**. "Leaky Abstraction" is a real term (Joel Spolsky, 2002), but applying it to this specific case requires architectural judgment that varies by context.

**If I had access to:** Software architecture literature, case studies of unified vs scattered error handling
**What would change:** The claim might be reframed as "unified abstractions for heterogeneous failure modes require careful design" rather than a binary "would be worse."

---

### Claim 2: "stderr might also be broken"

**Exact claim:** "When ANSI fails, it prints to stderr (line 54). But stderr might also be broken."

**Dependency:** Knowledge about when/how stderr can fail in Python runtime environments.

**Failure mode:**
- stderr is typically the last resort stream — it fails only in extreme cases (closed file descriptor, redirected to full disk)
- The claim treats stderr failure as a realistic concern without probability assessment
- If stderr fails, the entire process is likely in unrecoverable state anyway

**Confabulation risk:** **LOW**. This is technically true but practically marginal.

**If I had access to:** Python runtime documentation, stderr failure modes
**What would change:** Would likely classify this as "theoretically possible but not worth handling" rather than a meaningful critique.

---

### Claim 3: "ARC grids have specific dimensions"

**Exact claim:** "ARC grids have specific dimensions" (Bug #8 context)

**Dependency:** Knowledge of ARC (Abstraction and Reasoning Corpus) grid specifications.

**Failure mode:**
- What ARE the specific dimensions? The analysis doesn't state them.
- If ARC allows variable dimensions, the validation isn't "too permissive"
- The analysis assumes knowledge the reader may not have

**Confabulation risk:** **HIGH**. Specific dimension claims without stating the dimensions.

**If I had access to:** ARC dataset specification, Chollet's ARC paper
**What would change:** Could verify: do ARC grids have fixed dimensions? Range? The claim might be wrong or the validation might be appropriate.

---

### Claim 4: "Race condition" with ANSI_SUPPORTED flag

**Exact claim:** "ANSI_SUPPORTED race condition: Flag set at module level, modified in Windows block. If thread reads during import, sees wrong value."

**Dependency:** Python import semantics, thread safety, module initialization timing.

**Failure mode:**
- Python imports are single-threaded by design (import lock)
- The flag is set during module initialization, before any user code runs
- A thread can only read "during import" if spawned by module-level code — which doesn't happen here
- This is not a race condition in standard Python execution model

**Confabulation risk:** **HIGH**. Thread-safety claims often misunderstand Python's import model.

**If I had access to:** Python import system documentation, GIL behavior
**What would change:** This "bug" would likely be reclassified as "not a bug" — Python's import lock prevents this race.

---

### Claim 5: "SCRIPT_DIR / 'prisms' breaks if installed as package"

**Exact claim:** "PRISM_DIR assumes script location: `SCRIPT_DIR / 'prisms'` breaks if installed as package."

**Dependency:** Python packaging behavior, `__file__` location when installed via pip/wheel.

**Failure mode:**
- The claim is directionally correct but imprecise
- `__file__` behavior varies: editable installs work, wheel installs may not
- "Breaks" is vague — does it raise? Return wrong path? Fail silently?

**Confabulation risk:** **MEDIUM**. Common packaging gotcha, but specifics matter.

**If I had access to:** Python packaging docs, `importlib.resources` specification
**What would change:** Would specify: editable installs work, wheel installs need `importlib.resources.files()`. The fix is known.

---

### Claim 6: "Model behavior changes → extraction degrades silently"

**Exact claim:** "Calibration date: 2026-03-05 with no drift detection. Model behavior changes → extraction degrades silently." (Bug #13)

**Dependency:** Knowledge about LLM API behavior stability over time.

**Failure mode:**
- "Model behavior changes" is vague — which changes? Syntax? Temperature? Rate limits?
- Anthropic models have documented versioning; "drift" is not a documented phenomenon
- The prompt format may be stable even if model internals change

**Confabulation risk:** **MEDIUM-HIGH**. Assumes "drift" is a real problem without evidence.

**If I had access to:** Anthropic API changelog, model versioning documentation
**What would change:** Could verify: does Anthropic document model behavior changes? Is "drift" a real concern or FUD?

---

### Claim 7: "25% of bugs are structural" (Conservation Law Prediction)

**Exact claim:** "The conservation law predicts approximately 25% of bugs are structural — inherent in the requirement for a universal tool."

**Dependency:** The conservation law's predictive validity.

**Failure mode:**
- The "prediction" is post-hoc: bugs were classified AFTER the law was stated
- 5/20 = 25% is the count, not a prediction
- Circular: law derived from observation, then claimed to "predict" the observation

**Confabulation risk:** **LOW** (structural issue, not factual confabulation)

**If I had access to:** Independent bug classification, blind review
**What would change:** The "prediction" framing would be corrected to "classification" — the law describes, doesn't predict.

---

### Claim 8: "jsonschema silently disables features"

**Exact claim:** "jsonschema = None if import fails. Code using it must check; any miss causes AttributeError." (Bug #11)

**Dependency:** How the codebase actually uses jsonschema.

**Failure mode:**
- This is verifiable from source: grep for `jsonschema` usage
- If all usage sites check for None, there's no bug
- The claim assumes usage patterns without verifying them

**Confabulation risk:** **LOW-MEDIUM**. Partially verifiable, partially assumed.

**If I had access to:** Full codebase search for jsonschema references
**What would change:** Could verify: do all call sites check for None? If yes, not a bug. If no, specific locations of AttributeError risk.

---

## Summary: Confabulation Risk by Claim

| Claim | Risk | Primary Issue |
|-------|------|---------------|
| Leaky Abstraction | MEDIUM | Architectural judgment stated as fact |
| stderr broken | LOW | True but marginal |
| ARC grid dimensions | **HIGH** | Specifics not stated, may not exist |
| Race condition | **HIGH** | Misunderstands Python import model |
| Package installation | MEDIUM | Directionally correct, imprecise |
| LLM drift | MEDIUM-HIGH | Assumes undocumented phenomenon |
| 25% structural | LOW | Post-hoc framing as prediction |
| jsonschema usage | LOW-MEDIUM | Verifiable from source |

---

## Conservation Law of This Audit

> **STRUCTURAL CONFIDENCE × EXTERNAL CLAIM BREADTH = Constant**

The analysis has:
- **HIGH confidence** on structural observations (line references, code logic, verifiable bugs)
- **VARIABLE confidence** on external claims (ARC specs, Python semantics, LLM behavior)

The more external claims an analysis makes, the more opportunities for confabulation. The analysis's strongest findings (bugs 1, 5, 14) require NO external knowledge. Its weakest claims (bugs 8, 17, 13) require domain expertise the analysis assumes but doesn't cite.

**The conservation law operating here:**

> **An analysis can be BROAD (many claims) or GROUNDED (all verifiable), but not both.**

This analysis chose breadth — 20 bugs, architectural critique, conservation law, meta-law. The cost is that 4-6 claims have medium-to-high confabulation risk.

---

## What External Resources Would Change

| Resource | Claims Affected | Change |
|----------|-----------------|--------|
| ARC specification | Bug #8 | Verify dimension constraints exist |
| Python import docs | Bug #17 | Likely reclassify as "not a bug" |
| Anthropic API changelog | Bug #13 | Verify drift is/isn't documented |
| `importlib.resources` docs | Bug #18 | Confirm fix approach |
| jsonschema usage grep | Bug #11 | Verify None-check coverage |

---

## Unfalsifiable Claims

Regardless of access to documentation, these claims cannot be definitively confirmed or refuted:

1. **"Leaky Abstraction would be worse"** — Value judgment, context-dependent
2. **"Resilience Theater"** — Framing device, not falsifiable claim
3. **"(Universality × Simplicity) = Constant"** — Analytical construct, not empirical law

These are not bugs in the analysis — they're the necessary vocabulary for structural reasoning. But they should be recognized as analytical frameworks, not factual claims.
