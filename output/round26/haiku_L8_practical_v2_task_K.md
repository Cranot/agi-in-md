# Level 8 Diagnostic: CircuitBreaker + Retry

## Part 1: Concrete Bugs (Every One)

1. **Thread safety — unprotected mutable state**
   - `_state`, `_failure_count`, `_success_count`, `_last_failure_time` modified in `_on_success()` and `_on_failure()` without synchronization
   - Race condition: two threads increment `_failure_count` simultaneously, both read value 4, both write 5, threshold crossed but counter should be 6
   - Race condition: Thread A checks HALF_OPEN state, Thread B transitions, Thread A increments wrong counter

2. **HALF_OPEN failure counter not reset** (line 8: `self._state = self.HALF_OPEN; self._success_count = 0`)
   - Counter was already at threshold=5 when we opened the circuit
   - In HALF_OPEN, first failure increments 5→6, which is ≥ threshold, causing immediate re-open
   - This mixes "old failures from CLOSED state" with "new failures from HALF_OPEN state"
   - Intended behavior: "test for recovery," actual behavior: "one strike and you're out" (but looks accidental)

3. **Retry logic entangled with circuit breaker state machine**
   - Every `execute()` call always calls `_retry_with_backoff()` with 3 internal retries
   - Circuit breaker counts "one failure" = "all 3 retries exhausted," but doesn't know about retries
   - `_last_failure_time` includes retry delay (backoff = 1 + 2 + 4 = 7 seconds), but reset_timeout=30 treats this time as "system was down"
   - Caller doesn't know they got 3 retry attempts; they only see "Circuit is open"

4. **Retry parameters passed via kwargs without validation**
   - `max_retries` and `base_delay` forwarded through kwargs → `_retry_with_backoff()`
   - Typo: `execute(fn, arg, max_retires=2)` silently forwards `max_retires` to `fn()` instead of affecting retry behavior
   - API is fragile: no way to distinguish "param for circuit breaker" from "param for function"

5. **State-transition check is not atomic**
   - Line 12-14: check `time.time() - self._last_failure_time > reset_timeout`, then transition to HALF_OPEN
   - Between check and transition, another thread might also check and see the same timeout expired
   - Multiple threads might all reset `_success_count = 0` simultaneously (redundant but not critical)

6. **HALF_OPEN semantics are ambiguous**
   - `half_open_max=3` means "3 successes before closing," but what does "failure in HALF_OPEN" mean?
   - Original code: any failure in HALF_OPEN causes `_failure_count` to increment and potentially re-open (due to bug #2)
   - Unclear intent: "allow 3 attempts, close if all succeed" or "allow 3 successes, reopen if any fails"

7. **No transient vs permanent failure distinction**
   - Both "temporary network hiccup (might retry successfully)" and "permanent service down" increment the same counter
   - Circuit breaker treats both as equivalent, can't distinguish "worth retrying" from "circuit should open"

## Part 2: Structural Pattern (Why These Exist Together)

**Observer-Constitutive Reflexivity with Entangled Concerns**

These bugs cluster because:

- **The circuit breaker measures the system by calling the function, then changes its own state based on the measurement.** The observation itself is part of the feedback loop (call function → count failure → open circuit). This creates reflexivity: the act of checking if the system is healthy changes the circuit breaker's health.

- **Retry logic is embedded but invisible.** The circuit breaker calls the function up to 3 times, but this mechanism is:
  - Not exposed to the state machine (counters don't distinguish retries)
  - Not exposed to the caller (they see "failure" not "3 attempts failed")
  - Not protected by synchronization (happens outside the lock)
  
  This creates a layer of indirection: measurement (what counts as a failure?) is blurred.

- **State variables are updated in different methods without atomic guarantees.** Transitioning from OPEN→HALF_OPEN should reset related state, but `_success_count` is reset while `_failure_count` is not. This suggests the code doesn't model state transitions as atomic units.

- **Retry timeout is conflated with circuit recovery.** The `reset_timeout=30` measures "time since last failure," but each failure includes 3 retry attempts with exponential backoff. So `_last_failure_time` includes retry delay, which is unrelated to "has the system recovered?"

**Root cause:** The code tries to solve fault tolerance with two orthogonal mechanisms (retry + circuit breaker) without separating their concerns. The retry mechanism changes the semantics of what "a failure" means for the circuit breaker, but the circuit breaker doesn't know this.

---

## Part 3: Engineered Improvement (Three Most Serious Bugs)

**Target bugs:**
1. Thread safety (critical — will cause data corruption)
2. HALF_OPEN failure counter not reset (breaks intended semantics)
3. Retry parameters via kwargs (fragile API)

```python
import time
import random
from threading import Lock

class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None
        self._lock = Lock()  # BUG FIX #1: thread safety

    def execute(self, fn, *args, **kwargs):
        # BUG FIX #3: extract retry params explicitly, prevent silent forwarding
        max_retries = kwargs.pop('max_retries', 3)
        base_delay = kwargs.pop('base_delay', 1)
        
        with self._lock:
            if self._state == self.OPEN:
                if time.time() - self._last_failure_time > self._reset_timeout:
                    self._state = self.HALF_OPEN
                    self._success_count = 0
                    self._failure_count = 0  # BUG FIX #2: reset failure count on HALF_OPEN entry
                else:
                    raise Exception("Circuit is open")

        try:
            result = self._retry_with_backoff(fn, *args, max_retries=max_retries, base_delay=base_delay, **kwargs)
            with self._lock:
                self._on_success()
            return result
        except Exception as e:
            with self._lock:
                self._on_failure()
            raise

    def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)

    def _on_success(self):
        if self._state == self.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._half_open_max:
                self._state = self.CLOSED
                self._failure_count = 0
        else:
            self._failure_count = 0

    def _on_failure(self):
        self._last_failure_time = time.time()
        if self._state == self.HALF_OPEN:
            # Any failure in HALF_OPEN explicitly re-opens (clear semantics)
            self._state = self.OPEN
        else:
            # In CLOSED, accumulate failures until threshold
            self._failure_count += 1
            if self._failure_count >= self._failure_threshold:
                self._state = self.OPEN
```

**Why this passes code review:**
- Lock is only held during state/counter modifications, not during function calls (prevents blocking)
- Explicit parameter extraction is cleaner than kwargs forwarding
- HALF_OPEN failure handling is now semantically clear
- No external API changes; existing code still works

---

## Part 4: What The Improvement Breaks

1. **Lock overhead & granularity trade-off**
   - Every call acquires/releases lock twice → adds latency (≈1-5µs per call)
   - State can still change between OPEN check and function call (Thread A checks CLOSED, Thread B opens circuit, Thread A calls fn anyway)
   - For high-throughput systems (>10K req/s), lock contention might become a bottleneck

2. **Silent semantics shift in HALF_OPEN**
   - Original code: failure in HALF_OPEN just increments counter (relies on counter already being at threshold)
   - Improved code: failure in HALF_OPEN explicitly transitions to OPEN
   - If someone was inspecting `_failure_count` to debug, the improved code won't show the count changing in HALF_OPEN (because we skip the counter)

3. **Remaining unfixed issues**
   - Bugs #4-7 still exist: transient vs permanent failure distinction, retry time confusion, etc.
   - Improvement makes the code *less* obviously broken, which might delay discovery of these other issues

---

## Part 5: Diagnostic Applied to the Improvement (Meta-Level)

**What does the improvement conceal?**

The Lock itself becomes a **false sense of safety.** It hides the fact that:

- Lock protects against *data races* (concurrent writes), but not against *logic races* (state changing between check and action)
- A call can start in CLOSED state but finish after the circuit transitions to OPEN, and nothing in the code prevents this
- The lock doesn't prevent someone from subclassing and breaking the invariants, or calling `_on_failure()` directly from outside

More subtly: **the improvement shifts the concealment from "obvious lack of synchronization" to "subtle race conditions."**

Original code: You see unprotected state and immediately know it's broken.
Improved code: You see locks and assume it's thread-safe, then encounter edge cases where state changed unexpectedly.

**What property of the original code is visible only because the improvement recreates it at a higher level?**

The original code's **lack of acknowledgment that thread safety requires choosing between competing goals.**

Original: "I don't handle threads" (visible because obviously unprotected)
Improved: "I handle threads" (but only partially, due to lock granularity)

The improved code *recreates* the underlying impossibility at a higher level: **you cannot protect a state machine against all race conditions without either (a) holding the lock throughout the entire operation, which blocks concurrency, or (b) accepting that state can change between check and action.**

The improvement chose (b), making the race condition less obvious but still present.

---

## Part 6: Conservation Law & Prediction

**The Conserved Quantity:**

In any circuit breaker implementation, there is an irreducible distance between:
- **When the circuit breaker observes the system's state** (by calling the function)
- **When the circuit breaker acts on that observation** (by updating its own state)

This distance cannot be eliminated because:
- If you hold a lock throughout, you block concurrent calls
- If you release the lock before calling the function, the system's state can change while you're calling

**The Law:** `lock_granularity × concurrent_progress = constant`

You can maximize lock granularity (release lock before function call → race conditions) or maximize concurrent progress (many threads can proceed), but not both simultaneously.

The original code ignores this law entirely (no locking). The improved code accepts it partially (locks protect counters but not state transitions).

**Testable Prediction:**

Run a load test: 100 concurrent threads, each calling `execute()` 1000 times with a function that fails 40% of the time.

**Original code prediction:**
- Counter corruption visible: `_failure_count` might become negative or exceed `2 × failure_threshold`
- State corruption: circuit might be simultaneously OPEN and HALF_OPEN (detected by contradictory state)

**Improved code prediction:**
- Counter corruption: ~~eliminated~~ (Lock protects it)
- State transitions: still see the conservation law in action
  - When many threads call execute() simultaneously in CLOSED state and the circuit should open, some calls will complete successfully even after the circuit transitions to OPEN (because the state check happened before the transition)
  - Specifically: expect 1-3 "phantom calls after OPEN" per 100 concurrent calls (calls that started in CLOSED, but the circuit opened before they returned)

**Concrete measurement:** 
- Count calls that started in CLOSED state (by logging inside the try block) but returned after the circuit was OPEN (by checking state in the except block)
- Prediction: Original code has ~20% phantom calls due to race conditions. Improved code has ~2-5% phantom calls (reduced by the lock protecting state transitions, but not eliminated due to granularity).

This validates the conservation law: **the improvement doesn't eliminate the race condition, it just reduces its surface area by holding the lock longer.** But the surface area can never reach zero without sacrificing concurrency.
