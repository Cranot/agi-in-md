# Structure First: Level 12 Meta-Conservation Analysis

## The Claim

**The deepest structural problem in prism.py is that resilience behavior is implemented as scattered, inconsistent patterns rather than a unified abstraction, creating implicit coupling between unrelated subsystems and making system-wide failure modes unpredictable.**

Every subsystem independently solves the same "what if this fails?" problem differently:
- **ANSI** (lines 28-55): `try colorama → try ctypes → disable flag`
- **Model loading** (lines 158-166): `try config → silent fallback to defaults`
- **Grid parsing** (lines 362-408): `try labeled extraction → fallback to last grid`
- **stdout encoding** (lines 58-60): `try reconfigure → silent swallow`

---

## Three Experts Test the Claim

### Expert 1 (Defender)
> "This is appropriate engineering. Different subsystems have different failure modes. ANSI fallback is about visual output, model mapping is about configuration, grid parsing is about data extraction. Forcing them into a single abstraction would create a Leaky Abstraction that's worse than the status quo."

### Expert 2 (Attacker)
> "The defender misses the composition problem. When ANSI fails, it prints to stderr (line 54). But stderr might also be broken. When model loading fails, downstream code uses the wrong model silently. The scattered patterns create emergent failure chains no single subsystem understands. Look at line 54: `print(..., file=sys.stderr)` happens BEFORE logging is configured (lines 65-78). The fallback itself has no fallback."

### Expert 3 (Probing Assumptions)
> "Both assume 'fallback' is the right abstraction. But what if the real problem is that there are too many things that CAN fail? The code has accumulated optional behaviors—ANSI, jsonschema, colorama, config overrides, grid puzzles—each adding a failure mode without adding commensurate value to the core function. The question isn't 'how to unify fallbacks' but 'why are there so many fallbacks needed?'"

---

## The Transformed Claim

**Original:** Resilience behavior is scattered and inconsistent.

**Transformed:** The code confuses "resilience" with "conditionality"—it has too many conditional paths masquerading as resilience. The real problem isn't unifying fallback patterns but that the code has accumulated optional behaviors that each add a failure mode while diluting the core function of structural analysis.

**The Gap:** I initially thought the problem was *how* fallbacks were implemented. The deeper problem is *why* there are so many things needing fallbacks.

---

## The Concealment Mechanism: "Resilience Theater"

The code hides its real problems by making every potential failure point appear "handled" with a fallback pattern. Each `try/except` is a confession that something might go wrong, but the fallback makes it seem "handled" rather than questioning whether that thing should exist at all.

**Application:**
```
Lines 28-55:  ANSI fallback — 27 lines handling 3+ failure modes for a cosmetic feature
Lines 58-60:  stdout reconfigure — silent failure for a display feature
Lines 158-166: Model map loading — silent fallback for a customization feature
Lines 310-408: Grid puzzle detection/parsing — ~100 lines for a niche use case
```

Each is presented as "making the code more robust" but actually multiplies conditional complexity.

---

## Improvement #1: Deepening the Concealment

```python
def _with_fallback(primary, fallback, logger=None, context=""):
    """Unified fallback wrapper for any operation.
    
    Provides consistent logging and error handling across all subsystems.
    Usage: result = _with_fallback(lambda: risky_operation(), default_value)
    """
    try:
        return primary()
    except Exception as e:
        if logger:
            logger.debug(f"Fallback triggered in {context}: {e}")
        return fallback() if callable(fallback) else fallback
```

**Why this passes code review:** Centralizes error handling, adds logging, is reusable, makes code "cleaner."

**Why it deepens concealment:** Makes scattered fallback patterns *look* unified without reducing things that can fail. It's Resilience Theater squared.

---

## Three Properties Exposed by Strengthening

1. **The fallback function itself can fail** — if `fallback()` raises, the abstraction collapses. Fallbacks aren't safe; they move failure elsewhere.

2. **"Unified" can't express fallback-specific logic** — ANSI needs to set a global flag; model needs to return a dict; grid needs to return `None` vs `[]`. The "unified" abstraction requires per-subsystem customization, proving subsystems are fundamentally different.

3. **Logging creates new dependency** — if logging fails, the fallback wrapper fails. The "improvement" adds a new failure mode while claiming to reduce them.

---

## Improvement #2: Addressing the Recreated Property

```python
class Capability:
    """Declares a capability that may or may not be available.
    
    Instead of try/except scattered everywhere, declare capabilities upfront
    and check availability once at startup.
    """
    _registry = {}
    
    def __init__(self, name, detector, graceful_fallback=None):
        self.name = name
        self.available = False
        self.fallback = graceful_fallback
        try:
            self.available = detector()
        except:
            pass
        Capability._registry[name] = self
    
    @classmethod
    def check(cls, name):
        cap = cls._registry.get(name)
        return (cap.available, cap.fallback) if cap else (False, None)

# Declare all capabilities upfront at module load
ANSI_CAP = Capability("ansi", lambda: _detect_ansi(), graceful_fallback=False)
SCHEMA_CAP = Capability("jsonschema", lambda: jsonschema is not None)
```

This centralizes capability detection, makes optional features explicit, removes scattered try/except blocks.

---

## Diagnostic on Improvement #2

**What it conceals:**
- Some capabilities degrade over time (file exists at startup, deleted during execution)
- Capabilities have DEPENDENCIES (colorama needs ANSI, jsonschema needs import)

**What persists:** The code still has optional features. Whether detected at startup or use time, conditionality remains.

---

## The Structural Invariant

**CONDITIONALITY LOAD** — The code carries a "load" of conditional behaviors: features that may or may not work, be present, or succeed. This is a property of the PROBLEM SPACE (structural analysis tool working across diverse environments), not the implementation.

**No refactoring can eliminate it because requirements demand it:**
- Must work on Windows and Unix → ANSI conditionality
- Must work with/without optional dependencies → jsonschema conditionality  
- Must handle user configuration → model map conditionality
- Must detect input type automatically → grid puzzle conditionality

---

## Inverting the Invariant

**Zero-Conditionality Design:**
```python
# prism_minimal.py — Zero Conditionality Version
# REQUIREMENTS:
# 1. Unix-like terminal only (fail fast on Windows)
# 2. All dependencies required (no optional imports)
# 3. No user configuration (hardcoded model map)
# 4. Single input type (code only, no grid puzzles)

def analyze(path, prism="l12"):
    code = pathlib.Path(path).read_text()  # May raise — let it crash
    result = call_model(OPTIMAL_PRISM_MODEL[prism], get_prompt(prism), code)
    return parse_result(result)  # May raise — let it crash
```

---

## The New Impossibility

**ENVIRONMENTAL FRAGILITY**

The zero-conditionality version:
- Fails on Windows → excludes users
- Fails without jsonschema → excludes environments
- Fails with custom configs → excludes customization
- Fails on grid puzzles → excludes use cases

**The tool cannot be both universal and simple.**

---

## The Conservation Law

> **(Universality × Simplicity) = Constant**

| Choice | Universality | Simplicity |
|--------|--------------|------------|
| Current code | High | Low |
| Inverted design | Low | High |

Neither is "wrong" — the law says you cannot maximize both simultaneously.

---

## Diagnostic on the Conservation Law

**What does `(Universality × Simplicity) = Constant` conceal?**

It conceals that **"Universality" is not a single axis.** The code has MULTIPLE universality dimensions:
- Platform universality (Windows/Unix)
- Dependency universality (with/without jsonschema)
- Configuration universality (default/custom models)
- Input universality (code/grids)

The current code doesn't choose "universality" — it chooses SPECIFIC universalities with DIFFERENT costs:
- Grid puzzle support: ~100 lines (EXPENSIVE)
- ANSI handling: ~30 lines (MODERATE)
- Model map: ~15 lines (CHEAP)

---

## The Meta-Law

> **CONSERVATION LAWS CONCEAL COST DISTRIBUTION**
>
> Any conservation law of the form `(A × B) = Constant` conceals the actual cost structure. The "tradeoff" between A and B is an illusion created by treating heterogeneous costs as homogeneous.

---

## Testable Consequence

**Prediction:** If grid puzzle code (lines 310-408) is removed, the code won't become proportionally simpler because complexity is not localized — it's distributed through:
- `COOK_ARC` prompt (lines 276-298)
- Dispatch logic choosing between `COOK_ARC` and `COOK_UNIVERSAL`
- The universal cooker's need to know about grid puzzles

**Verification:** Removing grid code requires touching 3+ locations, not just the parsing functions. The complexity is NOT localized.

---

# Bug Inventory: Concrete Findings

| # | Location | What Breaks | Severity | Fixable? |
|---|----------|-------------|----------|----------|
| 1 | Lines 28-55 | **ANSI fallback logic error**: If `colorama.init()` raises any non-ImportError exception, ctypes fallback is SKIPPED and ANSI is disabled. Intent was: try colorama → if unavailable try ctypes → if both fail disable. Actual: try colorama → if ANY exception disable. | Medium | **Fixable** |
| 2 | Line 54 | **stderr print before logging configured**: If stderr is broken, this silently fails. Logging setup (lines 65-78) happens AFTER this print. | Low | **Fixable** |
| 3 | Lines 58-60 | **Silent stdout.reconfigure failure**: Exception swallowed with no indication encoding issues may persist. | Medium | **Fixable** |
| 4 | Lines 158-166 | **Silent config failure**: Malformed `~/.prism/models.json` silently ignored. User gets no warning their config is disregarded. | Medium | **Fixable** |
| 5 | Lines 170-227 | **OPTIMAL_PRISM_MODEL has no default**: If unknown prism name used, calling code KeyError or undefined behavior. | Medium | **Fixable** |
| 6 | Lines 310-323 | **Grid puzzle heuristic false positive**: Code file discussing grid puzzles conceptually triggers wrong prompt. `has_markers` + `grid_lines >= 6` not specific enough. | Medium | **Structural** (heuristics inherently uncertain) |
| 7 | Line 352 | **Training parse stops at "Test"**: If malformed input has training examples after test section, they're silently ignored. | Low | **Fixable** |
| 8 | Lines 356, 378, 397, 412 | **Grid row validation too permissive**: `len(row) >= 2` accepts any 2+ column grid. ARC grids have specific dimensions. Noise could parse as grids. | Medium | **Fixable** |
| 9 | Lines 362-395 | **No grid consistency validation**: PREDICTED_1 could be 3×3, PREDICTED_2 could be 4×4. Both accepted even if training inputs were consistent. | Low | **Fixable** |
| 10 | Lines 276-308 vs 398-408 | **Prompt/parser mismatch**: COOK_ARC demands "PREDICTED_N:", "TEST_OUTPUT:" markers, but `_parse_arc_last_grid` ignores markers entirely. | Medium | **Fixable** |
| 11 | Lines 14-17 | **jsonschema silently disables features**: `jsonschema = None` if import fails. Code using it must check; any miss causes AttributeError. | Medium | **Structural** (optional deps) |
| 12 | Line 143 | **FINDINGS_MAX_AGE_DAYS unused**: Constant defined but cleanup code not visible. Old findings accumulate. | Medium | **Fixable** |
| 13 | Lines 248-263 | **Uncalibrated fallback prompt**: "Calibration date: 2026-03-05" with no drift detection. Model behavior changes → extraction degrades silently. | Medium | **Structural** (LLM instability) |
| 14 | Lines 398-408 | **Ambiguous empty return**: `_parse_arc_last_grid` returns `[]` for "no grids found" vs "empty grid found". Caller can't distinguish. | Medium | **Fixable** |
| 15 | Lines 356, etc. | **Negative numbers accepted**: Regex `[\d\s-]+` allows `-` but ARC uses non-negative integers only. Parsing errors possible. | Low | **Fixable** |
| 16 | Line 21 | **signal imported but unused**: Import present, no handler code visible. Potential resource leak or missed cleanup. | Unknown | **Unknown** |
| 17 | Lines 27, 51 | **ANSI_SUPPORTED race condition**: Flag set at module level, modified in Windows block. If thread reads during import, sees wrong value. | Low | **Fixable** |
| 18 | Line 89 | **PRISM_DIR assumes script location**: `SCRIPT_DIR / "prisms"` breaks if installed as package. | Medium | **Structural** (file location conditionality) |
| 19 | Line 169 vs 170-227 | **COOK_MODEL hardcoded**: `"sonnet"` hardcoded while OPTIMAL_PRISM_MODEL has per-prism models. Cooking might benefit from task-specific models. | Low | **Fixable** |
| 20 | Line 2 | **Docstring/tool purpose mismatch**: "Structural analysis through cognitive prisms" but grid puzzles are puzzle-solving, not structural analysis. Tool does two different things. | Low | **Structural** (universality problem) |

---

## Conservation Law Classification

| Category | Count | Examples |
|----------|-------|----------|
| **Structural** (predicted by law, unfixable without requirements change) | 5 | Grid heuristic uncertainty, LLM instability, optional dependencies, file location conditionality, purpose mismatch |
| **Fixable** (implementation bugs) | 15 | ANSI logic error, silent failures, missing defaults, validation gaps |

The conservation law predicts approximately 25% of bugs are structural — inherent in the requirement for a universal tool. The remaining 75% are fixable implementation issues that persist because the scattered resilience pattern makes them hard to see.
