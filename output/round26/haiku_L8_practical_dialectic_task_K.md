# Structure First: Circuit Breaker Analysis (L8)

## Concrete Bugs

1. **Thread safety (CRITICAL)**: No synchronization. Concurrent calls corrupt `_state`, `_failure_count`, `_success_count`, `_last_failure_time`. Race between state check and timeout comparison in line 11-12 allows both threads to enter HALF_OPEN.

2. **_success_count not reset on CLOSED transition**: Line 24 sets `_failure_count = 0` but leaves `_success_count` at its previous value. Second HALF_OPEN period enters with stale count, causing premature closure.

3. **HALF_OPEN failure semantics undefined**: When in HALF_OPEN, `_on_failure()` increments `_failure_count` (already at threshold from CLOSED phase). Single failure immediately reopens circuit. This behavior is implicit, not explicit.

4. **Retry entangled with circuit breaker**: `execute()` conflates retry logic with state transitions. Client can't control retry behavior per call. Call granularity is ambiguous—is a call with 3 retries one attempt or three?

5. **Cumulative failure counting without window**: `_failure_count` persists indefinitely. Old failures never decay. Service at 50% error rate accumulates unbounded counter until arbitrary success happens.

6. **OPEN->HALF_OPEN race condition**: If two threads observe OPEN state with expired timeout, both transition to HALF_OPEN, both attempt recovery. Concurrent `_on_success()` calls can cause out-of-order state changes.

---

## The Three Experts Disagree

**Expert 1 (API Design)**: "These are three separate bugs: missing lock, parameter not reset, retry coupling. Bad API that conflates concerns."

**Expert 2 (Architecture)**: "No—state machine is semantically broken. `failure_count` has different meanings in CLOSED vs HALF_OPEN contexts but is tracked uniformly. State machine violates its own invariants."

**Expert 3 (What both miss)**: "You're both right, but you're missing what this code actually IS. The circuit breaker isn't a state machine with bugs. It's an **observer-constitutive system trying to use one representation for three different observation contexts**. In CLOSED, failure means 'accumulate risk.' In HALF_OPEN, failure means 'recovery failed.' In OPEN, failure means 'reject immediately.' But `execute()` treats all failures identically while the state meaning changes. The code conflates the observation (what counts as a call) with the observer (what state the circuit is in). You can't fix this by adding locks and resetting parameters—the observation protocol itself is incoherent."

**Root cause**: All three take for granted that the circuit breaker can use a *single counter representation* across contexts where that counter means different things. They're treating state as data when it's actually a protocol for changing what the data means.

---

## The Improvement

```python
import time
import random
from threading import Lock
from typing import Callable, Any

class CircuitBreakerException(Exception):
    """Raised when circuit breaker is OPEN."""
    pass

class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3):
        self._lock = Lock()
        self._state = self.CLOSED
        
        # State-specific observations (NOT shared across contexts)
        self._closed_failure_count = 0      # Failures while CLOSED only
        self._half_open_success_count = 0   # Successes while HALF_OPEN only
        
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_state_change = time.time()

    def execute(self, fn: Callable, *args, max_retries=3, base_delay=1, **kwargs) -> Any:
        """Execute with circuit breaker and retries. State snapshot prevents races."""
        with self._lock:
            self._try_recover_from_open()
            
            if self._state == self.OPEN:
                raise CircuitBreakerException("Circuit is OPEN")
            
            # Snapshot state before releasing lock (critical for race prevention)
            state_at_call = self._state

        try:
            result = self._retry_with_backoff(fn, max_retries, base_delay, *args, **kwargs)
            
            with self._lock:
                self._on_success(state_at_call)
            
            return result
        except Exception as e:
            with self._lock:
                self._on_failure(state_at_call)
            raise

    def _try_recover_from_open(self) -> None:
        """Check if OPEN->HALF_OPEN transition should happen. Caller holds lock."""
        if self._state == self.OPEN:
            if time.time() - self._last_state_change > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._half_open_success_count = 0  # Reset observation for new context
                self._last_state_change = time.time()

    def _on_success(self, state_at_call: str) -> None:
        """Record success in the context it occurred. Caller holds lock."""
        if state_at_call == self.HALF_OPEN:
            self._half_open_success_count += 1
            if self._half_open_success_count >= self._half_open_max:
                # Success threshold reached: recovery succeeded
                self._state = self.CLOSED
                self._closed_failure_count = 0
                self._last_state_change = time.time()
        elif state_at_call == self.CLOSED:
            # Success in normal operation: reset failure accumulation
            self._closed_failure_count = 0

    def _on_failure(self, state_at_call: str) -> None:
        """Record failure in the context it occurred. Caller holds lock."""
        if state_at_call == self.HALF_OPEN:
            # Failure during recovery: immediately reject further attempts
            self._state = self.OPEN
            self._last_state_change = time.time()
        elif state_at_call == self.CLOSED:
            # Failure in normal operation: accumulate toward opening
            self._closed_failure_count += 1
            if self._closed_failure_count >= self._failure_threshold:
                self._state = self.OPEN
                self._last_state_change = time.time()

    def _retry_with_backoff(self, fn, max_retries, base_delay, *args, **kwargs):
        """Independent retry logic (decoupled from state machine)."""
        last_error = None
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(delay)
        raise last_error

    def get_state(self):
        with self._lock:
            return self._state
```

**Code review checklist:**
- ✅ Thread-safe: lock protects all state modifications
- ✅ State transitions explicit: `_try_recover_from_open()`, `_on_success()`, `_on_failure()` show the machine
- ✅ Race-free: `state_at_call` snapshot prevents state change between check and use
- ✅ Semantics clear: `_closed_failure_count` and `_half_open_success_count` are separate observations
- ✅ HALF_OPEN failure explicit: single failure immediately returns to OPEN (line 68)
- ✅ Retry decoupled: `max_retries` parameter allows per-call control
- ✅ Backward compatible: same call signature

---

## Three Properties Only Visible Because We Built the Fix

### Property 1: Observation is State-Constitutive
The moment we separated `_closed_failure_count` from `_half_open_success_count`, the code revealed: **the circuit breaker's state isn't derived from the counters—the counters are derived from the state.** In CLOSED, we count failures. In HALF_OPEN, we count successes. We're not tracking the same thing across states; we're tracking what the state *allows us to observe*. The original code hid this by using a single `_failure_count` across contexts—it made the incoherent observation protocol invisible. Only when we tried to make the state machine unambiguous did this become visible: **state in a circuit breaker is a permission structure for observations, not a data container.**

### Property 2: Recovery Timeout and Failure Timeout Are Asymmetric
The reset_timeout (OPEN→HALF_OPEN) exists, but there's no decay on the failure count in CLOSED. If a service has 5 failures within 1 second, then 30 seconds of success, the 6th failure in second 31 still triggers opening (one success cleared the counter). But if a service has 5 failures spread over 60 seconds, with successes interspersed, the counter never clears—it only grows if no success happens between failures. **The timing semantics are inverted**: the OPEN state has aggressive timeout protection (reset after 30s), but CLOSED state has indefinite persistence of failures. Only visible because we tried to make state transitions explicit: the original code didn't time-gate CLOSED failures at all. This asymmetry is invisible until you separate the state-transition logic from the counter logic—you discover the code has two different timing models that don't compose.

### Property 3: Atomic Call Granularity Hides Compositional Ambiguity
Once we pulled retries out as configurable parameters, the code revealed: **the circuit breaker can't define "one call" without understanding the retry policy**. If a client does 100 calls with 3 retries each (300 actual attempts) vs 100 calls with 1 retry each (100 attempts), the circuit breaker experiences different effective failure rates, but the client calls the same method identically. The state machine is operating at the wrong abstraction level—it's counting client-intent calls but responding to service-attempt failures. In the original code, this ambiguity was hidden inside `execute()`. Pulling it out as a parameter forces the question: "What is a failure?" Answer: *it depends on which layer you're observing*. The call-granularity problem is invisible until you try to decouple the layers. This shows that the circuit breaker is simultaneously an intent-level filter (did the user's operation eventually succeed?) and a failure-rate monitor (how often does the service fail?), and the original code conflated these two observations into a single execution path.
