# Generative Diagnostic: Circuit Breaker with Embedded Retry

## The Falsifiable Claim

**The circuit breaker operates on a systematically falsified model of downstream health: by embedding retries inside its failure-accounting boundary, it absorbs up to `failure_threshold × max_retries` (15) real failing calls while believing only `failure_threshold` (5) have failed, making its protection guarantee quantitatively wrong by a constant factor.**

---

## The Three-Expert Dialectic

### Expert 1 (Defender)
> Correct. The contract of a circuit breaker is: "after N failures, stop sending traffic." But each call to `_on_failure` represents 3 actual failed HTTP calls (or whatever `fn` does). A downstream service experiencing brownout gets 15 failing requests instead of 5 before relief arrives. In HALF_OPEN — supposedly a *careful probe* — every single "probe" actually hammers the recovering service with up to 3 rapid attempts with backoff. The protection ratio is silently wrong.

### Expert 2 (Attacker)
> This is a parameter tuning issue, not a structural one. The *real* structural flaw is invisible: `_retry_with_backoff` captures `max_retries` and `base_delay` from `**kwargs`, meaning they're **silently intercepted from arguments intended for the wrapped function**. If `fn` accepts a parameter called `max_retries`, this code swallows it without error. That's not a tuning problem — it's a **silent correctness violation** with no possible test failure to signal it. Also: every piece of mutable state (`_state`, `_failure_count`, `_success_count`, `_last_failure_time`) is accessed without synchronization. This is unusable in any concurrent context, which is the *only* context circuit breakers exist for.

### Expert 3 (Prober — questioning both)
> You're both describing symptoms. Defender sees wrong counting. Attacker sees namespace collision and thread-unsafety. Neither asks: *why do all three of these exist simultaneously?* Because this code has **no concept of a boundary** at any level:
> - **Policy boundary**: Retry logic and circuit-breaking logic are fused into one control flow
> - **API boundary**: Retry configuration and function arguments share one `**kwargs` dict
> - **Concurrency boundary**: State transitions and state reads have no synchronization surface
>
> These aren't three bugs. They're one architectural absence manifested three ways.

## Transformed Claim

**The deepest structural problem is the systematic absence of boundaries — between retry policy and circuit-breaker policy, between infrastructure arguments and function arguments, and between concurrent state access points. The failure-counting inaccuracy, the `**kwargs` collision, and the thread-unsafety are all consequences of a single missing concept: separation.**

### The Diagnostic Gap

My original claim (wrong counting) targeted the most *visible* symptom. The transformed claim (no boundaries) names the *generative structure*. The gap reveals that **I was drawn to the quantitative error because it's falsifiable and dramatic**, while the real problem is qualitative and architectural — harder to test, harder to name, but responsible for *all* the symptoms simultaneously.

---

## The Concealment Mechanism: **Nominal Correctness**

This code uses every right word — `CLOSED`, `OPEN`, `HALF_OPEN`, exponential backoff, jitter, threshold, timeout — and follows the correct *shape* of the pattern. It would:
- Pass any single-threaded test
- Pass any test where `fn` doesn't use parameters named `max_retries` or `base_delay`  
- Look correct in any code review checking "is this a valid circuit breaker state machine?"

**The vocabulary and structure satisfy pattern-recognition review**, causing reviewers to verify implementation fidelity rather than questioning whether internal architectural boundaries exist.

---

## The Engineered Concealment: A "Fix" That Deepens the Problem

This would pass code review as a clear improvement:

```python
import time, random, threading, logging

logger = logging.getLogger(__name__)


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30,
                 half_open_max=3, max_retries=3, base_delay=1):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._max_retries = max_retries          # <-- "fixed" kwargs collision
        self._base_delay = base_delay
        self._last_failure_time = None
        self._lock = threading.Lock()             # <-- "fixed" thread safety

    def execute(self, fn, *args, **kwargs):
        with self._lock:
            if self._state == self.OPEN:
                if time.time() - self._last_failure_time > self._reset_timeout:
                    self._state = self.HALF_OPEN
                    self._success_count = 0
                    logger.info("Circuit %s -> HALF_OPEN", id(self))
                else:
                    raise CircuitOpenError(self._reset_timeout)
            current_state = self._state           # <-- snapshot for "safe" use

        # Lock released: retries execute outside critical section
        try:
            result = self._retry_with_backoff(fn, *args, **kwargs)
            with self._lock:
                self._on_success()
            return result
        except Exception:
            with self._lock:
                self._on_failure()
            raise

    def _retry_with_backoff(self, fn, *args, **kwargs):
        for attempt in range(self._max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception:
                if attempt == self._max_retries - 1:
                    raise
                delay = min(self._base_delay * (2 ** attempt), 60)
                delay += random.uniform(0, 1)
                logger.debug("Retry %d/%d after %.1fs",       # <-- "observability"
                             attempt + 1, self._max_retries, delay)
                time.sleep(delay)

    def _on_success(self):
        if self._state == self.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._half_open_max:
                self._state = self.CLOSED
                self._failure_count = 0
                logger.info("Circuit %s -> CLOSED", id(self))
        else:
            self._failure_count = max(0, self._failure_count - 1)  # <-- "gradual recovery"

    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._failure_threshold:
            self._state = self.OPEN
            logger.warning("Circuit %s -> OPEN after %d failures",
                           id(self), self._failure_count)


class CircuitOpenError(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after
        super().__init__(f"Circuit open. Retry after {retry_after}s")
```

### Why this passes review and deepens concealment

| Visible "fix" | What it actually conceals |
|---|---|
| `threading.Lock()` added | Lock is *released before the retry loop*. In HALF_OPEN, 20 threads all pass the state check, then all simultaneously execute 3-retry bursts against the recovering service. The "probe" is now a **stampede**. |
| `max_retries` moved to `__init__` | Retry policy is now fused to the circuit breaker's *identity*. You can't retry idempotent GETs 5× and non-idempotent POSTs 0× through the same breaker. The boundary absence is now *permanent API*. |
| `logger.info` on state transitions | Logs show clean state transitions. Individual retry failures go to `DEBUG` (usually off). **The real failure rate is architecturally invisible** in production logging config. |
| `failure_count - 1` gradual recovery | Appears sophisticated. Actually creates a new bug: in CLOSED state after a burst of 4 failures (just under threshold), a single success reduces count to 3. This makes the threshold *non-deterministic* — it depends on interleaving of successes and failures, which is harder to reason about and impossible to test exhaustively. |
| `CircuitOpenError` with `retry_after` | Looks like good API design. But `retry_after` is the *configured* timeout, not the *remaining* time. Callers who respect it will always wait too long. |

---

## Three Properties Visible Only Through Attempted Strengthening

**1. The lock reveals an impossible atomicity requirement.**
When I added the lock, I was *forced* to release it before the retry loop (holding it would serialize all calls, defeating the circuit breaker's purpose). This proves that the state check ("should I allow this call?") and the retry execution ("make the call N times") **require fundamentally different concurrency models**: the state machine needs mutual exclusion; the retry loop needs *admission control* (e.g., a semaphore limiting HALF_OPEN probes to 1). These cannot coexist in one `execute()` method with one lock — the architecture needs two separate components.

**2. Moving retry config to `__init__` reveals a lifecycle mismatch.**
Retry policy should vary *per call* (idempotent vs. non-idempotent, latency-sensitive vs. batch, read vs. write). Circuit breaker policy should vary *per dependency* (database vs. cache vs. third-party API). Fusing them into one constructor makes it impossible to express: "Use this circuit breaker for the payments service, but retry GETs 3× and POSTs 0×." The config binding point reveals that these are **separate concerns with different lifecycles** that were never meant to share an object.

**3. The logging gap reveals a structural observability impossibility.**
When I added logging for state transitions at INFO and retries at DEBUG, it became clear: **the method boundary between `execute` and `_retry_with_backoff` is drawn to hide the most operationally critical information** (actual failure rate per unit time). To observe real downstream health, you'd need to emit metrics *from inside the retry loop* and correlate them with circuit state — but the retry loop has no reference to circuit state (it doesn't know it's inside a circuit breaker). The architecture makes the most important signal *structurally inaccessible* without breaking encapsulation.

---

## Summary Diagnosis

```
Root cause:     Absent boundaries (one architectural deficiency)
Manifestations: 3 (failure accounting, kwargs collision, thread-unsafety)  
Concealment:    Nominal correctness (right vocabulary, right shape, wrong structure)
Correct fix:    Decompose into separate RetryPolicy and CircuitBreaker with
                composition (breaker.execute(retry(fn))) not inheritance/embedding
```

The code doesn't have a bug. It has a missing architectural concept — **separation** — and every observable problem, including ones the "improved" version introduces, traces back to that single absence.
