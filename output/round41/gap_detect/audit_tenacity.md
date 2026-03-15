# Knowledge Audit: Tenacity Architectural Critique

## Attack Construction

### KNOWLEDGE CLAIM 1: ContextVar Inheritance in Async

**Exact claim:**
> "In async/await, child tasks inherit parent ContextVar state. `IterState` from one retry operation can leak into nested async calls, causing `actions` from one retry to execute in another's context."

**Dependency:** Python's `contextvars` module semantics, specifically how `ContextVar` behaves with `asyncio.create_task()` and task spawning.

**Failure mode:** 
- Python 3.7+ ContextVars are **task-local**, not inherited by child tasks by default
- `asyncio.create_task()` copies the current context at task creation time—changes in parent don't propagate to already-created children
- The claim implies runtime leakage *during* execution, but ContextVars snapshot at task boundaries

**Confabulation risk:** **MEDIUM-HIGH**. The specific mechanics of ContextVar inheritance are nuanced. Models often conflate "context inheritance at task creation" with "runtime state leakage across tasks."

---

### KNOWLEDGE CLAIM 2: Exception Suppression Scope

**Exact claim:**
> "Exceptions that should escape (like `KeyboardInterrupt`, `SystemExit`) are captured and converted to retry attempts. User cannot interrupt execution during retry loop."

**Dependency:** Python exception hierarchy—specifically that `KeyboardInterrupt` and `SystemExit` inherit from `BaseException` and would be caught by `except BaseException` or context manager `__exit__` returning True.

**Failure mode:**
- `__exit__` receives the exception—it doesn't *catch* it. The `return True` suppresses *re-raising*, but the exception was already raised normally.
- `KeyboardInterrupt` and `SystemExit` are indeed `BaseException` subclasses, so they would reach `__exit__`
- **However**: Tenacity's `retry_if_exception_type` defaults to `Exception`, not `BaseException`—so retry logic may not *trigger* on these

**Confabulation risk:** **MEDIUM**. The exception hierarchy is well-documented, but the interaction between context manager suppression and Tenacity's retry predicates requires tracing actual code paths.

---

### KNOWLEDGE CLAIM 3: Line Number References

**Exact claims:**
> "Layer 1: Outer while loop (line 298, 354)"
> "Layer 2: Action list iteration (line 195)"
> "BaseRetrying.__iter__ (line 298)"
> "Retrying.__call__ (line 354)"

**Dependency:** Specific version of Tenacity source code.

**Failure mode:** Any version change. Line numbers are extremely fragile.

**Confabulation risk:** **HIGH**. Models frequently hallucinate specific line numbers. Without access to the actual source at a specific commit, these are unreliable.

---

### KNOWLEDGE CLAIM 4: Statistics Threshold Behavior

**Exact claim:**
> "Silent clearing at 100 entries can lose critical diagnostic data."

**Dependency:** The actual implementation of statistics storage and the threshold value.

**Failure mode:**
- The threshold might not be 100 in all versions
- The clearing behavior might have been documented or changed
- There might be a configuration option to control this

**Confabulation risk:** **MEDIUM-HIGH**. Specific numeric thresholds are commonly confabulated.

---

### KNOWLEDGE CLAIM 5: Copy Protocol Defect Count

**Exact claim:**
> "**Copy protocol** (`self.copy()`) → 8 concrete defects"

**Dependency:** The causal attribution that copy protocol causes the defects.

**Failure mode:** The 8 defects may not be causally related to `self.copy()`. Looking at the listed defects, only some relate to state management that copy would affect.

**Confabulation risk:** **LOW**. This is internal logical consistency, not external knowledge.

---

## Structural vs. Knowledge Classification

| Claim Type | Verifiable From Analysis | External Knowledge Required |
|------------|-------------------------|----------------------------|
| Action list mutates during iteration | ✅ SAFE | — |
| ContextVar threading obscures state origin | ✅ SAFE | — |
| Two execution paths exist (`__iter__` vs `__call__`) | ✅ SAFE | — |
| `__exit__` returns True | ✅ SAFE | — |
| ContextVar causes async leakage | ❌ KNOWLEDGE | Python async semantics |
| `KeyboardInterrupt` suppressed | ❌ KNOWLEDGE | Python exception hierarchy + Tenacity predicates |
| Line numbers 298, 354, 195 | ❌ KNOWLEDGE | Specific source version |
| Threshold is exactly 100 | ❌ KNOWLEDGE | Current implementation |

---

## Improvement Construction

**With access to official documentation:**
- ContextVar behavior in async contexts would be **confirmed**—Python docs clearly state context is copied at task creation
- The "leakage" claim would be **refined**: it's not runtime leakage but *context snapshot* behavior that could cause issues

**With access to CVE database:**
- No security vulnerabilities would likely be found—these are design issues, not security flaws
- Exception suppression could be a **denial-of-service vector** if retry loops can't be interrupted

**With access to current GitHub issues:**
- Would find if users have reported async state confusion
- Would find if `KeyboardInterrupt` suppression is a known pain point
- Would verify if the 100-entry threshold is documented or configurable

**With access to benchmark data:**
- The "three layers of iteration overhead" claim is **unfalsifiable without measurement**
- Performance impact of action list pattern vs. alternative designs would need empirical data

---

## The Conservation Law for This Audit

**Structural Findings × Knowledge Confidence = Analytical Reliability**

The analysis contains:
- **~15 structural observations** (action list pattern, dual paths, mutable state) — **HIGH confidence**, source-derived
- **~7 knowledge claims** (async semantics, exception behavior, line numbers) — **VARIABLE confidence**, external-dependent

The **analytical reliability** is constrained by the weakest knowledge claim. A single high-confabulation claim (line numbers, exact threshold values) can undermine credibility of the entire critique, even when structural observations are sound.

**The conservation law reveals:**

> The analysis trades **precision** (specific line numbers, exact thresholds) for **credibility risk**. Each specific claim that cannot be verified from source is a potential point of failure. The structural insights (conservation law framework, action list pattern critique) require no external validation and remain robust regardless of implementation details.
