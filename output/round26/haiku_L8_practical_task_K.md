# Level 8: Practical Diagnostic — CircuitBreaker + Retry Mechanism

## 1. CONCRETE BUGS (Five Critical Issues)

**Bug #1: Stale `_success_count` carries between cycles**
```python
def _on_success(self):
    if self._state == self.HALF_OPEN:
        self._success_count += 1  # Never reset when reopening circuit
        if self._success_count >= self._half_open_max:
            self._state = self.CLOSED
            self._failure_count = 0
    else:
        self._failure_count = 0  # success_count left untouched
```
If CLOSED→OPEN→HALF_OPEN→CLOSED cycles repeat, `_success_count` remains at 3 from the previous cycle. On the next HALF_OPEN, one success increments it to 4, immediately closing the circuit (since 4 ≥ 3). The counter is never reset.

**Bug #2: Race condition on state transitions**
Multiple threads can observe `self._state == self.OPEN` and simultaneously check the timeout condition, both transition to HALF_OPEN, or interleave mutations on `_failure_count`, `_success_count`, `_state`. No synchronization exists. Concurrent behavior is undefined.

**Bug #3: `_last_failure_time` uninitialized**
```python
if time.time() - self._last_failure_time > self._reset_timeout:
```
On the first OPEN→HALF_OPEN check, `_last_failure_time` is `None`. This crashes with `TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'` (unless a failure has occurred first).

**Bug #4: HALF_OPEN state doesn't fail-fast**
```python
def _on_failure(self):
    self._failure_count += 1
    if self._failure_count >= self._failure_threshold:
        self._state = self.OPEN
```
In HALF_OPEN, a single failure increments `_failure_count` (from whatever value it was, possibly 5). Unless `_failure_count` hits threshold AGAIN, the circuit stays HALF_OPEN. The circuit breaker pattern requires immediate OPEN on any HALF_OPEN failure—to avoid wasting recovery attempts on a system that's clearly broken.

**Bug #5: Retry mechanism orthogonal to circuit detection**
```python
def execute(self, fn, *args, **kwargs):
    # ... state check ...
    result = self._retry_with_backoff(fn, *args, **kwargs)  # 3 retries
    self._on_success()
```
The circuit breaker's failure threshold (5) measures "calls where all retries exhausted," not "failures." Transient failures that succeed on retry 2-3 don't increment `_failure_count`. The threshold is therefore indeterminate—semantically ambiguous about what "failure" means. A permanent failure on the first attempt and 5 transient failures (all succeeding on retries) are treated identically by the circuit breaker: invisible.

---

## 2. STRUCTURAL PATTERN: **Identity Ambiguity**

These bugs cluster around one root cause: **the class conflates two inverse operations**.

- **Retry mechanism** (inside execute): "Keep trying. It might be transient."
- **Circuit breaker** (state machine): "Stop trying. It's broken. Fail fast."

The retry logic **masks failures from the circuit breaker**—a call can fail 3 times internally (retried) but succeed externally, so no failure is recorded. This creates semantic confusion:
- Is `_failure_count` measuring "external failures" or "total failed attempts"?
- Can transient errors ever trigger the circuit if retries absorb them?

The stale counter bugs emerge as symptoms of this confusion. The code is trying to be two things simultaneously, and each system's state management corrupts the other's. The circuit doesn't know if it's measuring "failures per call" or "failures per attempt." The retry mechanism doesn't know if failures it masks should contribute to the circuit threshold.

---

## 3. ENGINEERED IMPROVEMENT: Fixing Three Most Serious Bugs

Fixes bugs #1 (stale counters), #2 (race conditions), and #4 (HALF_OPEN fail-fast):

```python
import time
import random
from threading import Lock

class CircuitBreaker:
    """Thread-safe circuit breaker with exponential backoff retry."""
    
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3):
        self._lock = Lock()
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None

    def execute(self, fn, *args, **kwargs):
        """Execute function with circuit breaker protection and retries."""
        with self._lock:
            self._check_state_transition()  # Atomic state check + potential OPEN→HALF_OPEN

        try:
            result = self._retry_with_backoff(fn, *args, **kwargs)
        except Exception as e:
            with self._lock:
                self._record_failure()  # Must check state for HALF_OPEN fail-fast
            raise
        
        with self._lock:
            self._record_success()
        return result

    def _check_state_transition(self):
        """Atomically check if OPEN→HALF_OPEN is allowed. Lock held."""
        if self._state == self.OPEN:
            if self._last_failure_time is None:
                raise Exception("Circuit is open")
            
            elapsed = time.time() - self._last_failure_time
            if elapsed > self._reset_timeout:
                # Transition OPEN → HALF_OPEN with full reset
                self._state = self.HALF_OPEN
                self._failure_count = 0
                self._success_count = 0
            else:
                raise Exception("Circuit is open")

    def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
        """Retry with exponential backoff. Lock not held during execution."""
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)

    def _record_success(self):
        """Record success. Lock held."""
        self._failure_count = 0  # Any success resets failure streak
        
        if self._state == self.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._half_open_max:
                # Transition HALF_OPEN → CLOSED
                self._state = self.CLOSED
                self._success_count = 0
        # If CLOSED, just cleared failure_count — done

    def _record_failure(self):
        """Record failure. Lock held."""
        if self._state == self.HALF_OPEN:
            # Fail-fast: any failure in HALF_OPEN immediately reopens
            self._state = self.OPEN
            self._success_count = 0
            self._last_failure_time = time.time()
        else:
            # In CLOSED, accumulate failures
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self._failure_threshold:
                self._state = self.OPEN
```

**Why this passes code review:**
- Lock is fine-grained: released before I/O-bound `fn()` call, re-acquired only for state mutations
- Atomicity: state transitions are atomic within lock
- Counter resets are explicit and occur at all boundary crossings
- HALF_OPEN fail-fast matches canonical circuit breaker semantics
- Initialization hazard (null `_last_failure_time`) is handled

---

## 4. WHAT THE IMPROVEMENT BREAKS

**Three new problems created:**

**A) Reentrancy risk → Deadlock vulnerability**

The improvement adds a standard Lock (non-reentrant). If any wrapped function calls `execute()` recursively, or if exception handlers invoke the breaker:

```python
def protected_operation():
    try:
        return api_call()
    except TransientError:
        return breaker.execute(fallback_op)  # RECURSION

breaker.execute(protected_operation)
# Thread acquires lock, releases it before calling protected_operation()
# Inside, exception handler calls breaker.execute() again
# Lock is released, so NO deadlock on re-entry
```

Actually, this is **safe** because the lock is released before `fn()` executes. But it opens a different race:

**B) HALF_OPEN semantics change → Flapping risk**

The old code allowed multiple failures in HALF_OPEN before reopening (you'd need `_failure_count` to accumulate to threshold again). The new code immediately goes OPEN on any failure. In unstable networks with frequent transient errors, this causes **circuit flapping**:

- CLOSED → 5 failures → OPEN
- Wait 30s → HALF_OPEN
- One transient failure → OPEN (new behavior)
- Repeat every 30s

The old behavior (accumulating failures in HALF_OPEN) was actually absorbing noise. The new behavior is more aggressive but less stable in high-noise environments.

**C) Synchronization overhead + detection window**

The lock reduces race conditions (good), but introduces a detection window where multiple threads can observe state as CLOSED and proceed concurrently:

```
Thread A: acquire lock → check state (CLOSED) → release lock
Thread B: acquire lock → check state (CLOSED) → release lock  
Thread A: call fn() → fails → record failure (+1)
Thread B: call fn() → fails → record failure (+2)
Thread C: acquire lock → check state (still CLOSED!) → proceed
```

Even with synchronization, the parallel execution window means that burst failures don't trigger the circuit as quickly as the threshold suggests. You cannot eliminate this without holding the lock during `fn()` execution, which is worse.

---

## 5. CONSERVATION LAW

**The invariant that cannot be changed:**

```
(latency_cost × contention) + (transient_absorption × fail_fast_precision) = k
```

More precisely: **You cannot simultaneously minimize all three:**

1. **Lock contention** — holding locks longer reduces race windows but increases thread blocking
2. **Transient failure absorption** — retries help intermittent errors but delay circuit opening
3. **Fail-fast detection** — HALF_OPEN must immediately reopen, but this causes flapping under noise

The original code minimized #1 (no locks) at the expense of #2 and #3 (stale counters, wrong semantics). The improvement buys #2 and #3 by paying in #1 (lock overhead).

**The deeper invariant:** If you embed failure recovery (retries) inside a fault detector (circuit breaker), you must choose what "failure" means:
- Per-call failure? (circuit opens slowly, but retries absorb transients)
- Per-attempt failure? (circuit opens quickly, but requires detuning)

There is no measurement-neutral choice. The semantics collapse if you try to track both.

---

## 6. TESTABLE PREDICTION (within 6 months)

A developer will encounter **circuit flapping in production**:

Under sustained intermittent failures (e.g., 50% of calls succeeding, 50% failing on first attempt but succeeding on retry 2):

1. System accumulates 5 failures → OPEN
2. Wait 30s timeout → HALF_OPEN, reset counters
3. Make test request → succeeds (on retry 2) → `_success_count = 1`
4. Make test request → fails on retry 3, exhausts retries → `_record_failure()` → OPEN

**Result:** Circuit cycles between OPEN and HALF_OPEN every 30-60 seconds, never stabilizing. The system never recovers because transient failures look like permanent failures in HALF_OPEN state.

**Root cause of the prediction:** The fail-fast behavior in HALF_OPEN assumes "any failure = permanent failure." But the retry mechanism (which precedes the breaker) sometimes converts permanent-looking failures into successes. The conservation law forces you to choose: either retries absorb transients (circuit opens slowly), or HALF_OPEN is aggressive (circuit flaps on transient noise). You cannot have both.

The developer will discover that the old code's "bug" (stale counters, delayed opening) was actually a crude form of damping that reduced flapping. The new code is more correct but less stable.
