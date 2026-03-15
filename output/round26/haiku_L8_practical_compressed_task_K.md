# Analysis: CircuitBreaker State Pollution

## Every Concrete Bug

**Bug A — HALF_OPEN reuses global failure counter**  
When testing recovery in HALF_OPEN, `_on_failure()` increments `_failure_count` (the global history counter from CLOSED state). If you accumulated 4 failures before opening, then one test failure during HALF_OPEN increments to 5, triggering immediate return to OPEN. You never complete the recovery test. State history poisons state transition logic.

**Bug B — Retry logic delays circuit breaker response**  
`_retry_with_backoff` executes *before* state-machine sees the failure. A single failed call retries 3 times (7 sec backoff) before raising. The circuit breaker accumulates failures only after retries exhaust. Fast-fail mechanism is blocked behind exponential backoff.

**Bug C — HALF_OPEN retry pollution**  
During recovery testing, `_retry_with_backoff` sends 3 test attempts per call. You're supposed to test if service recovered with 1 request, not 3. The success/failure signals are entangled with retry behavior.

**Bug D — `_on_success()` unconditionally resets failure history**  
One success in CLOSED state erases all accumulated failure context. For flaky services (fails intermittently, succeeds sometimes), the circuit never trips—successes keep resetting the counter before threshold is reached.

**Bug E — No independent HALF_OPEN failure tracking**  
HALF_OPEN should track "successes with at most N failures allowed during testing." Instead it reuses the global `_failure_count`. There's no "we've accumulated too many failures during testing, return to OPEN" logic—it's just "if global failure count hits threshold."

---

## Structural Pattern

**State machines conflate concerns through variable reuse.**

The same `_failure_count` variable means different things depending on state:
- CLOSED: "consecutive failures toward trip"  
- HALF_OPEN: "test attempt failures compared to historical threshold"

Initialization logic doesn't account for state transition (resetting `_success_count` but NOT `_failure_count` when entering HALF_OPEN). The state machine has multiple operational modes but shared variable ownership—classic state pollution.

Additional pattern: **Embedded retries couple two independent concerns.** Retries (handle transient errors) and circuit breaking (detect persistent failures) are distinct layers, but `execute()` interleaves them.

---

## Fix (Passes Code Review)

```python
class CircuitBreakerFixed:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30, test_attempts=3):
        self._state = self.CLOSED
        self._failure_count = 0        # CLOSED state only
        self._test_success_count = 0   # HALF_OPEN state only
        self._test_failure_count = 0   # HALF_OPEN state only
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._test_attempts = test_attempts
        self._last_failure_time = None

    def execute(self, fn, *args, **kwargs):
        # State transition
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._test_success_count = 0
                self._test_failure_count = 0
            else:
                raise Exception("Circuit is open")

        # Execute (no retries—caller responsibility)
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        if self._state == self.HALF_OPEN:
            self._test_success_count += 1
            if self._test_success_count >= self._test_attempts:
                self._state = self.CLOSED
                self._failure_count = 0
        elif self._state == self.CLOSED:
            self._failure_count = 0

    def _on_failure(self):
        self._last_failure_time = time.time()
        if self._state == self.HALF_OPEN:
            self._state = self.OPEN  # Strict: any failure returns to OPEN
        elif self._state == self.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self._failure_threshold:
                self._state = self.OPEN
```

Key moves:
1. **Independent counters**: `_test_*` isolated from `_failure_count`  
2. **Removed retries**: Delegates to caller layer  
3. **Explicit state init**: Recovery testing starts with clean counters  
4. **Strict HALF_OPEN**: Any failure = return to OPEN (one strike during recovery test)

---

## What the Fix Conceals

The fix hides **the original's implicit tolerance for flakiness**.

Original code: "Successes reset counter, so occasional failures during otherwise-healthy operation don't trip the breaker. Recovery test can fail a few times before re-opening."

Fixed code: "Recovery test is strict—any failure means try again in 30 seconds. No tolerance for transient errors during testing."

This concealment reveals something powerful: **the original's "bug" (success resets history) was actually a feature**—it implemented a windowed metric. The fix makes that design choice explicit but loses the tolerance.

---

## Three Properties Visible Only Because You Engineered a Stronger Version

**1. State machines need variable independence by state mode**  
Building the fix exposed that reusing a variable across states without explicit initialization per transition is a structural error. Once separated, the code's intent became clear. The original code's bugs were symptoms of shared ownership—you can't tell what `_failure_count` means without checking the state.

**2. The implicit "success resets time window" is doing semantic work**  
Original `_on_success()` erasing `_failure_count` looked like a bug. The fix revealed it was implementing "failures older than the most recent success are forgotten"—a reasonable recovery window for flaky services. The fix trades this implicit window (via success reset) for a strict test sequence, exposing that the design choice was always present, just unnamed.

**3. Retry and circuit-breaking are separate failure detection layers**  
Removing internal retries exposed that the circuit breaker was trying to handle two classes of failure simultaneously. Retries handle *transient* failures (try again, it might work). Circuit breaking handles *persistent* failures (stop trying, let system heal). These need independent signals. Original interleaved them; the fix unmixes them. You see now that the 7-second retry delay was actively *hiding* the fast-fail intent of the circuit breaker.

---

## Conservation Law

**`failure_detection_speed × tolerance_to_transient_errors = constant`**

Or more precisely: **The total cost of recovery testing is invariant—speed and reliability trade off.**

- Original: Slow failure detection (wait through retries), high tolerance for flaky recovery (successes reset counter, allowing multiple failed attempts). Total time to fail-then-recover: high.
- Fixed: Fast failure detection (no retries), low tolerance for flaky recovery (one failure returns to OPEN). Total time to fail-then-recover: also high (more cycles through OPEN→HALF_OPEN→OPEN).

You cannot design a circuit breaker that detects failures instantly AND tolerates transient errors during recovery testing. You can move the tradeoff (strict vs permissive) but the cost persists. The specific manifestation changes, but some form of delay or fragility is conserved.

---

## Prediction: What a Developer Hits in 6 Months

**"Why does our circuit breaker never recover? Services keep bouncing between OPEN and HALF_OPEN."**

In production, the fixed code's strictness creates oscillation:
- Service hiccups (0.5% error rate, recovers fast)
- Hits threshold → OPEN
- Waits 30 seconds → HALF_OPEN
- First test request hits a transient error → immediately OPEN
- Waits 30 seconds → HALF_OPEN
- Repeat

The original code tolerated this (success resets counter), but the fix doesn't. Developer realizes **they need windowed tolerance back**: "Allow 3 successes with at most 1 failure during HALF_OPEN," or "track success ratio, not absolute counts."

This loops back to the original's design—implicit tolerance—but now the developer will implement it *explicitly* with a parameter: `test_success_threshold=3, test_failure_tolerance=1`.

The underlying tension (the conservation law) resurfaces: **that parameter choice now makes visible what was hidden before.**
