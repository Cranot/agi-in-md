# Knowledge Boundary Analysis: Prism.py Structural Analysis

## Step 1: Claim Classification

### STRUCTURAL (Derivable from source alone)

| # | Claim | Evidence Location |
|---|-------|-------------------|
| 1 | ANSI uses try colorama → try ctypes → disable flag | Lines 28-55, explicit control flow |
| 2 | Model loading uses silent fallback to defaults | Lines 158-166, exception handling pattern |
| 3 | Grid parsing uses fallback to last grid | Lines 362-408, explicit fallback logic |
| 4 | stdout reconfigure swallows exceptions | Lines 58-60, bare except with pass |
| 5 | stderr print happens before logging configured | Line 54 vs lines 65-78, ordering verifiable |
| 6 | colorama.init() non-ImportError skips ctypes | Lines 28-55, exception type analysis |
| 7 | OPTIMAL_PRISM_MODEL has no default | Lines 170-227, dict definition verifiable |
| 8 | jsonschema = None on import failure | Lines 14-17, explicit pattern |
| 9 | FINDINGS_MAX_AGE_DAYS constant defined | Line 143, visible |
| 10 | signal imported but unused | Line 21, import statement |
| 11 | ANSI_SUPPORTED race condition possible | Lines 27, 51, module-level mutation |
| 12 | PRISM_DIR assumes script location | Line 89, path construction |
| 13 | COOK_MODEL hardcoded | Line 169 vs 170-227, comparison |
| 14 | ~100 lines for grid puzzle code | Lines 310-408, countable |
| 15 | Removing grid code requires 3+ locations | Lines 276-308, 310-408, 398-408 — traceable |

### CONTEXTUAL (Depends on external state/knowledge)

| # | Claim | External Dependency |
|---|-------|---------------------|
| C1 | "Forcing single abstraction creates Leaky Abstraction" | Software engineering design principles |
| C2 | "has_markers + grid_lines >= 6 not specific enough" | Actual input corpus distribution |
| C3 | "ARC grids have specific dimensions" | ARC benchmark specification |
| C4 | "Grid puzzles are puzzle-solving, not structural analysis" | Definition of "structural analysis" |

### TEMPORAL (May have expired since training)

| # | Claim | Time Sensitivity |
|---|-------|------------------|
| T1 | "Model behavior changes → extraction degrades silently" | LLM API stability |
| T2 | "Calibration date: 2026-03-05 with no drift detection" | Model version currency |

### ASSUMED (Untested assumptions stated as fact)

| # | Claim | What's Assumed |
|---|-------|----------------|
| A1 | "stderr might also be broken" | Hypothetical failure mode |
| A2 | "Code discussing grid puzzles conceptually triggers wrong prompt" | Heuristic false positive rate |
| A3 | "(Universality × Simplicity) = Constant" | Conservation law validity |
| A4 | "Conservation laws conceal cost distribution" | Meta-theoretical claim |
| A5 | "If grid puzzle code removed, complexity not proportionally simpler" | Testable prediction (not tested) |
| A6 | "~25% of bugs are structural" | Generalization from single codebase |
| A7 | "15 fixable, 5 structural" in bug count | Classification accuracy |

---

## Step 2: Non-STRUCTURAL Claims — Verification Sources

### CONTEXTUAL Claims

| Claim | Verification Source | Staleness Risk | Confidence |
|-------|---------------------|----------------|------------|
| **C1: Leaky Abstraction** | https://en.wikipedia.org/wiki/Leaky_abstraction, Fowler's blog, software engineering literature | Yearly (principles evolve slowly) | **HIGH** |
| **C2: Heuristic specificity** | Test against corpus of 1000+ code files; ARC validation set | Monthly (new input patterns) | **MEDIUM** |
| **C3: ARC grid dimensions** | https://github.com/fchollet/ARC (official repository), ARC paper | Yearly (benchmark stable) | **HIGH** |
| **C4: Structural analysis definition** | Tool's own docstring line 2; software analysis literature | Yearly | **MEDIUM** |

### TEMPORAL Claims

| Claim | Verification Source | Staleness Risk | Confidence |
|-------|---------------------|----------------|------------|
| **T1: Model behavior changes** | OpenAI/Anthropic API changelogs; LLM stability research papers | **DAILY** (models update frequently) | **HIGH** |
| **T2: Calibration date drift** | Anthropic model versioning docs; API deprecation notices | **DAILY** | **HIGH** |

### ASSUMED Claims

| Claim | Verification Source | Staleness Risk | Confidence |
|-------|---------------------|----------------|------------|
| **A1: stderr broken** | Test with closed stderr fd; POSIX documentation | Never (edge case) | **UNKNOWN** |
| **A2: Grid heuristic FP** | Test against codebase corpus; measure false positive rate | Monthly | **MEDIUM** |
| **A3: Conservation law** | Formal proof; empirical validation across 10+ codebases | Never (theoretical) | **MEDIUM** |
| **A4: Meta-law** | Validate conservation law classifications across domains | Never (theoretical) | **MEDIUM** |
| **A5: Complexity non-local** | Actually perform the refactoring; measure | Never (testable) | **MEDIUM** |
| **A6: 25% structural** | Classify bugs in 10+ diverse codebases | Yearly | **LOW** |

---

## Step 3: Gap Map — Grouped by Fill Mechanism

### API_DOCS

| Gap | Source | What It Would Verify |
|-----|--------|---------------------|
| ARC grid dimension constraints | https://github.com/fchollet/ARC, ARC paper | Bug #8 severity (grid row validation) |
| LLM model versioning | Anthropic API docs, OpenAI API docs | Bug #13 severity (calibration drift) |

### COMMUNITY

| Gap | Source | What It Would Verify |
|-----|--------|---------------------|
| Leaky Abstraction pattern | Software engineering literature, Martin Fowler's blog | Defender's argument validity |
| LLM extraction stability | arXiv papers on LLM reliability, LangChain docs | Whether drift detection is needed |

### BENCHMARK

| Gap | Source | What It Would Verify |
|-----|--------|---------------------|
| Grid heuristic specificity | Test against 1000+ code files | Bug #6 is real or false positive |
| Conservation law validity | Validate across 10+ codebases | (Universality × Simplicity) holds |

### CHANGELOG

| Gap | Source | What It Would Verify |
|-----|--------|---------------------|
| Model behavior drift | provider-name API changelog (monthly) | Extraction degradation claim |

---

## Step 4: Priority Ranking — Impact if Wrong

### TIER 1: Would invalidate core conclusions

| Rank | Gap | If Wrong, Then... | Fill Mechanism |
|------|-----|-------------------|----------------|
| **1** | **Conservation law validity (A3)** | Entire theoretical framework collapses; "25% structural" becomes arbitrary; meta-law meaningless | BENCHMARK (validate across codebases) |
| **2** | **Model drift severity (T1, T2)** | Bug #13 is overstated; calibration infrastructure may be unnecessary | CHANGELOG + API_DOCS |
| **3** | **Grid heuristic FP rate (A2, C2)** | Bug #6 is false positive; ~100 lines of grid code is actually fit-for-purpose | BENCHMARK (test corpus) |

### TIER 2: Would change severity assessment

| Rank | Gap | If Wrong, Then... | Fill Mechanism |
|------|-----|-------------------|----------------|
| **4** | **ARC grid dimensions (C3)** | Bug #8 (row validation) is more/less severe | API_DOCS (ARC spec) |
| **5** | **Leaky Abstraction (C1)** | Defender is wrong; centralization IS viable | COMMUNITY (SE literature) |
| **6** | **Complexity localization (A5)** | Removing grid code IS proportionally beneficial; refactoring advice changes | BENCHMARK (actual refactor) |

### TIER 3: Would refine but not reverse

| Rank | Gap | If Wrong, Then... | Fill Mechanism |
|------|-----|-------------------|----------------|
| **7** | **25% structural (A6)** | Bug classification shifts; fixable/structural ratio changes | BENCHMARK (10+ codebases) |
| **8** | **Structural analysis definition (C4)** | Bug #20 (purpose mismatch) reclassified | COMMUNITY (domain definitions) |
| **9** | **stderr failure (A1)** | Bug #2 severity assessment | BENCHMARK (edge case testing) |

---

## Summary Statistics

| Category | Count | Percentage |
|----------|-------|------------|
| **STRUCTURAL** | 15 | 45% |
| **CONTEXTUAL** | 4 | 12% |
| **TEMPORAL** | 2 | 6% |
| **ASSUMED** | 7 | 21% |
| *(Derived from structural)* | 6 | 18% |

**Non-structural claims requiring external verification: 13/33 (39%)**

**Highest-risk gaps:**
1. **Conservation law (A3)** — theoretical foundation, untested
2. **Model drift (T1/T2)** — time-sensitive, changes daily
3. **Heuristic specificity (A2/C2)** — empirical claim, untested

---

## Critical Finding

The analysis's **deepest theoretical claims** (conservation law, meta-law, 25% structural ratio) are **ASSUMED** rather than verified. If the conservation law fails validation:

- The "structural vs fixable" classification becomes arbitrary
- The meta-law ("conservation laws conceal cost distribution") is meaningless
- The entire analytical framework needs reconstruction

**The analysis is strongest where it stays closest to code (15 STRUCTURAL claims) and weakest where it builds theory (7 ASSUMED claims).**
