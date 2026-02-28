# Recursive Structural Diagnostic of the Circuit Breaker

## The Claim (Specific, Falsifiable)

**The retry loop and circuit breaker have incompatible ontologies of "attempt" and "failure," and their nesting creates a state-accounting inversion: the circuit breaker's model of downstream health is *systematically wrong* by a factor of `max_retries`.**

Each `execute()` call generates up to 3 downstream failures, but `_on_failure()` is called at most once. A `failure_threshold` of 5 actually permits **15** downstream failures. In `HALF_OPEN`, the circuit intends to *carefully probe* with limited attempts, but the retry loop fires 3 attempts per probe — blasting a recovering service with the very load the circuit breaker exists to prevent.

---

## Three Experts Disagree

**Expert A (Defender):** Correct. Trace it: HALF_OPEN allows `half_open_max=3` successes to close the circuit. But each of those 3 "probes" internally retries 3 times. You could hit a recovering service with 9 requests during what the circuit breaker models as "3 careful probes." The invariant of HALF_OPEN — limited exposure — is violated by the mechanism that implements it.

**Expert B (Attacker):** This is *intentional abstraction*. The circuit breaker counts *logical operation* failures, not transport-level retries. You want retry to handle transient blips (packet loss, momentary timeouts) while the circuit breaker handles sustained outages. Counting each retry as a circuit failure would make the breaker hypersensitive.

**Expert C (Probes assumptions):** You're both assuming the two mechanisms *can* have independent failure semantics when they share a call stack. But look at `_on_failure()`: it sets `_last_failure_time = time.time()`. When does that fire? *After* the retry loop has already spent `1 + ~3 + ~7 = ~11 seconds` in backoff delays. The circuit breaker records the failure timestamp as 11 seconds after the problem started. The `reset_timeout` clock is wrong from birth. These aren't independent mechanisms with a tuning disagreement — they're **mutually corrupting each other's temporal model**.

---

## Transformed Claim

**Original:** "Failure counting is wrong by a factor of 3."
**Transformed:** "The retry mechanism and circuit breaker corrupt each other's core invariants — failure counts, temporal windows, and probe semantics — because they each assume they are the sole failure-handling layer, but neither is."

**The diagnostic gap:** What looked like a counting bug is actually a **compositional category error** — two patterns that each require *outermost* authority over failure, nested where neither can have it.

---

## The Concealment Mechanism

**Pattern-name authority.** The class is named `CircuitBreaker`. The method is named `_retry_with_backoff`. A reviewer sees these names, mentally substitutes the well-known pattern semantics from the literature, and *never verifies that the composition preserves each pattern's invariants*. Each piece looks correct in isolation. The names make the broken seam invisible.

---

## The Engineered Concealment: A "Thread-Safety" Improvement

This improvement is legitimate, would pass review, and deepens the concealment:

```python
import time, random, threading

class CircuitOpenError(Exception):
    pass

class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3):
        self._lock = threading.RLock()
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None

    @property
    def state(self):
        with self._lock:
            return self._state

    def execute(self, fn, *args, **kwargs):
        with self._lock:
            if self._state == self.OPEN:
                if time.time() - self._last_failure_time > self._reset_timeout:
                    self._state = self.HALF_OPEN
                    self._success_count = 0
                else:
                    raise CircuitOpenError(
                        f"Circuit open for {self._reset_timeout 
                         - (time.time() - self._last_failure_time):.1f}s more"
                    )

        # Lock released during I/O — correct, unavoidable
        try:
            result = self._retry_with_backoff(fn, *args, **kwargs)
            with self._lock:
                self._on_success()
            return result
        except Exception as e:
            with self._lock:
                self._on_failure()
            raise

    def _retry_with_backoff(self, fn, *args, max_retries=3,
                            base_delay=1, **kwargs):
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
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._failure_threshold:
            self._state = self.OPEN
```

**Why this passes review:** Thread safety is a genuine, obvious gap. The lock placement is textbook-correct (hold during state transitions, release during I/O). The `CircuitOpenError` is a real improvement over bare `Exception`. The `state` property is clean encapsulation. Three real problems fixed.

**Why this deepens the concealment:** The locks make the broken composition *look carefully reasoned*. A reviewer sees synchronized state management and concludes the interaction effects have been analyzed. The improvement converts *accidental neglect* into *apparent intentional design*.

---

## Three Properties Visible Only Because I Tried to Strengthen the Concealment

**1. The retry loop is the real concurrency hazard, not the state machine.**
Adding locks forced me to release them during `_retry_with_backoff` (you can't hold a lock during network I/O). This reveals: in HALF_OPEN, 10 threads can simultaneously pass the state check, each fire 3 retries, and blast the recovering service with **30 concurrent requests** — while the circuit breaker believes it authorized 3 careful probes. The lock *precisely frames* the gap it cannot close.

**2. `_last_failure_time` is a hidden reset-timer that retries make wrong.**
The lock made me trace the timestamp lifecycle. Every `_on_failure()` call resets the timeout window. But the timestamp is set *after* the retry loop spent ~11 seconds in backoff. The circuit breaker records "the failure happened now" when the failure actually started 11 seconds ago. The `reset_timeout` window is systematically extended by retry backoff time. With locks, multiple threads' timestamps now *race* to corrupt this value.

**3. The state machine has no transition guards.**
Thread A reads HALF_OPEN, releases the lock, enters the retry loop. Thread B fails, acquires the lock, transitions to OPEN. Thread A's retries complete successfully, it acquires the lock, calls `_on_success()` — which checks `self._state == self.HALF_OPEN`, finds OPEN instead, falls to `else`, and *resets `_failure_count` to 0*. A success during an open circuit **resets the failure counter**. The original code hid this because single-threading made the invalid transition impossible.

---

## Recursive Application: What Does the Improvement Conceal?

The improvement conceals the same thing the original conceals — **the absence of a compositional contract between retry and circuit-breaking** — but through a different mechanism:

| Layer | Concealment Mechanism |
|---|---|
| Original code | **Pattern-name authority**: "it's a circuit breaker with retry" |
| Improved code | **Correctness theater**: locks imply analyzed interactions |

The improvement *recreates* the original problem in a new form: the original code *accidentally* worked in single-threaded contexts because only one probe could execute at a time, making the broken HALF_OPEN semantics survivable. The improvement *removes that accidental constraint* (it's now thread-safe enough to use concurrently) while *preserving the broken composition*, unleashing the HALF_OPEN stampede that single-threading accidentally prevented.

**The property of the original problem visible only through its recreation:** The original code was not "correct but single-threaded." It was **broken in a way that single-threaded deployment happened to mask.** The improvement proves this by providing the concurrency correctness that makes the compositional incorrectness *finally matter*. The original code's apparent correctness was a coincidence of deployment context, not a property of its design.

---

## What Would Actually Fix This

The mechanisms need a **shared failure protocol**, not nesting:

```python
# The retry loop must be circuit-aware:
def _retry_with_backoff(self, fn, *args, max_retries=3, **kwargs):
    with self._lock:
        if self._state == self.HALF_OPEN:
            max_retries = 1  # Circuit says: one shot only
    # ...each individual failure feeds _on_failure()...
```

Or better: **separate the mechanisms entirely** and compose them through an explicit contract where the circuit breaker *wraps* the retry, deciding whether retry is even permitted, rather than the retry being an invisible implementation detail inside the circuit breaker's execute path. The retry should be the outer policy; the circuit breaker should gate each individual attempt.
