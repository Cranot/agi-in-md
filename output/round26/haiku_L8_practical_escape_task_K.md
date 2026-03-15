# Level 8: Structure First — Circuit Breaker + Retry

## Concrete Bugs

1. **Thread Safety Violations** (multiple)
   - `_state` checked, then modified without atomicity — another thread changes state between check and use
   - `_failure_count` and `_success_count` non-atomic increments during concurrent calls
   - `_last_failure_time` can be None when accessed from different thread
   - No locks protecting the execute path

2. **State Inconsistency: HALF_OPEN Failure**
   - Transition OPEN→HALF_OPEN resets `_success_count` but NOT `_failure_count`
   - If failure in HALF_OPEN: `_failure_count` increments from old CLOSED-state value
   - Re-opens only if accumulated failures ≥ threshold
   - A single HALF_OPEN failure doesn't re-open if threshold was 5 and we've only accumulated 1 failure since entering HALF_OPEN
   - State is neither HALF_OPEN-semantics (fail fast) nor CLOSED-semantics (accumulate)

3. **Retry-Circuit Level Conflation**
   - Each `execute()` call can invoke retry_with_backoff (up to 3 attempts = 3 service calls)
   - Circuit counts "function invocations," not "service failures"
   - Failure threshold of 5 means 5 failed *execute()* calls, but each could be 3 retried service calls
   - Circuit thinks service is failing at 1/15 rate; it's actually failing at 5/5 rate
   - Decouples observation (what failed?) from recovery (should we open?)

4. **Thundering Herd on Reset**
   - Multiple threads waiting on OPEN circuit
   - When `time.time() - _last_failure_time > reset_timeout` becomes true, ALL threads see it simultaneously
   - ALL transition to HALF_OPEN in the same millisecond
   - ALL execute retry_with_backoff simultaneously → synchronized load spike on recovering service
   - No jitter, no staggering

5. **Hardcoded Retry Parameters**
   - `max_retries=3, base_delay=1` fixed in method signature
   - But `failure_threshold, reset_timeout, half_open_max` are constructor parameters
   - Inconsistent API — if retries matter to circuit behavior, they should be configurable
   - Can't adjust retry aggressiveness without modifying source code

6. **Success Semantics Ambiguous**
   - "Success" = function returned without exception
   - But `fn()` might be `make_api_call()` that internally catches exceptions and returns error status
   - Circuit thinks service recovered when it only means the wrapper function executed
   - Can't distinguish "service is healthy" from "wrapper is callable"

7. **Race Condition: OPEN→HALF_OPEN Window**
   - Thread 1 checks if timeout expired → YES
   - Thread 1 changes state to HALF_OPEN
   - Thread 2 still in execute() sees OPEN state
   - Thread 2 raises "Circuit is open" exception
   - Yet circuit is actually transitioning to recovery
   - Brief window where circuit rejects calls even though it's testing recovery

8. **No Manual Reset**
   - Stuck state requires code change to recover
   - No `reset()` method for emergency recovery

---

## Design Category

This code inhabits: **Temporal Threshold State Machine with Embedded Recovery Retries**

The concealment: **The circuit does not know if it's observing service health or call resilience.** By embedding retries inside the circuit, observation (counting failures) and recovery (retrying) are fused. The circuit measures failures at the *call* level, not the *service* level. This ambiguity allows it to work despite the bugs — the loose state semantics and race conditions actually dampen cascade effects.

---

## Engineering an "Improvement" That Deepens Concealment

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3, 
                 max_retries=3, base_delay=1):  # Make retries configurable
        # ... existing code ...
        self._lock = threading.RLock()  # Add thread safety
        self._max_retries = max_retries
        self._base_delay = base_delay

    def execute(self, fn, *args, **kwargs):
        with self._lock:  # Atomicity fix
            if self._state == self.OPEN:
                if time.time() - self._last_failure_time > self._reset_timeout:
                    self._state = self.HALF_OPEN
                    self._success_count = 0
                    self._failure_count = 0  # Fix: reset failure count too
                else:
                    raise Exception("Circuit is open")

        try:
            result = self._retry_with_backoff(fn, *args, self._max_retries, self._base_delay, **kwargs)
            with self._lock:
                self._on_success()
            return result
        except Exception as e:
            with self._lock:
                self._on_failure()
            raise

    def _retry_with_backoff(self, fn, *args, max_retries=None, base_delay=None, **kwargs):
        max_retries = max_retries or self._max_retries
        base_delay = base_delay or self._base_delay
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
```

This looks like legitimate improvement:
- ✓ Thread-safe atomicity
- ✓ Configurable retry parameters
- ✓ Fixed state inconsistency (reset `_failure_count` in HALF_OPEN)

---

## Three Properties Visible *Only* Because We Tried to Strengthen It

**1. Observation/Execution Fusion Is Load-Dampening**

The original race conditions were dampening cascade failures. When state checks aren't atomic, they introduce brief delays. Multiple threads checking `_state == OPEN` at different nanoseconds prevents them all from re-executing simultaneously. Making state transitions atomic with locks *accelerates* failure propagation — all waiting threads now synchronize on the lock, see HALF_OPEN at the same moment, and hammer the recovering service in unison. The race conditions were accidentally doing load-shedding. The "fix" creates the thundering herd problem the original looseness was preventing.

**2. State Accumulation Prevents Oscillation**

The "bug" of not resetting `_failure_count` on HALF_OPEN actually prevented state cycling. If you're in HALF_OPEN and get failures, the accumulated old failures from CLOSED prevent oscillation back to CLOSED on a lucky success. The original hysteresis (remembering failures across state transitions) is what made the state machine stable. Fixing it to "proper" semantics (reset counts on transition) creates CLOSED→OPEN→HALF_OPEN→CLOSED oscillation under flaky service. The "correct" code is less resilient.

**3. Retry Level and Circuit Level Are Inseparable Observations**

By making retries configurable (tunable improvement), we reveal they cannot be separated from circuit behavior. The failure_threshold measures "resilient calls" (attempts that survived internal retries), not "service failures." A service failing 10/10 times but with retries surviving 5/10 opens the circuit differently than the same service failing 5/10 times without retries. You can't tune circuit opening without knowing retry policy. You can't tune retry aggressiveness without understanding it changes when circuit opens. They're not independent parameters — they're aspects of one coupled observation model.

---

## Adjacent Design Category: Separated Concerns

Escape to a design where circuit and retry are **decoupled**:

```python
class HealthMonitor:
    """Pure health observation, no recovery logic"""
    HEALTHY, DEGRADED, FAILING = "healthy", "degraded", "failing"
    
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self._state = self.HEALTHY
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._last_failure_time = None
        self._lock = threading.RLock()
    
    def record_success(self):
        with self._lock:
            if self._state != self.HEALTHY:
                self._failure_count = 0
                self._success_count += 1
                if self._success_count >= 3:
                    self._state = self.HEALTHY
                    self._success_count = 0
            else:
                self._failure_count = 0
    
    def record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._success_count = 0
            self._last_failure_time = time.time()
            if self._failure_count >= self._failure_threshold:
                self._state = self.FAILING
            elif self._failure_count >= self._failure_threshold // 2:
                self._state = self.DEGRADED
    
    def can_attempt(self):
        """Is it worth trying right now?"""
        with self._lock:
            if self._state == self.FAILING:
                if time.time() - self._last_failure_time > self._recovery_timeout:
                    self._state = self.DEGRADED
                    self._failure_count = 0
                    return True  # Try ONE recovery attempt
                else:
                    return False
            return True  # HEALTHY or DEGRADED: try

class Resilient:
    def __init__(self, monitor, max_retries=3, base_delay=1):
        self.monitor = monitor
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def call(self, fn, *args, **kwargs):
        if not self.monitor.can_attempt():
            raise Exception(f"Service {self.monitor._state}")
        
        try:
            for attempt in range(self.max_retries):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        self.monitor.record_failure()
                        raise
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(delay)
        except Exception:
            raise
        finally:
            if 'attempt' in locals() and attempt < self.max_retries:
                self.monitor.record_success()
```

---

## What the Escape Loses

1. **Implicit Load Dampening**: Original race conditions accidentally prevented synchronized failure propagation. New design's explicit locks make timing deterministic — and deterministic synchronization can be worse than jittered chaos.

2. **Direct Observation Feedback**: Original code told you circuit state immediately from `execute()` result. New design requires separate `monitor.health` query — observation and action are decoupled in time and space.

3. **Tuned Failure Tolerance**: Original embedded retries into circuit behavior, so failure threshold was in terms of "survived call attempts," not raw service calls. New design counts actual service calls, requiring you to lower failure_threshold to compensate for retries.

---

## New Impossibility the Escape Creates

**`information_cost × separation_of_concerns = constant`**

Original design:
- Observing `_state` is "free" (just read the field)
- But observation is coupled to execution (you learn state only by calling)
- Fused = always synchronized

Escaped design:
- Observing `monitor.health` is pure (independent of execution)
- But now there are **two views of state**: the monitor's model and the actual service behavior
- During network partition or flaky service, they diverge
- You either:
  - Pay cost: call service to sync the monitor (extra traffic)
  - Or accept cost: run on stale information (decisions based on wrong state)

You cannot eliminate this tradeoff. Separation requires a model. Models require synchronization cost or staleness cost.

---

## Testable Predictions

1. **Thundering Herd Prediction**: Add thread-safe locks to the original code. Run 100 concurrent calls during OPEN state. Measure milliseconds between first HALF_OPEN transition and peak request load. Original (loose semantics) will show spread of 50-200ms. Locked version will show synchronized spike within 5ms. The "bugs" were load-shedding.

2. **State Oscillation Prediction**: Fix the HALF_OPEN state consistency. Simulate a service that fails 60% of the time. Measure state transitions over 10 minutes. Buggy original (doesn't reset `_failure_count`) will stabilize OPEN→HALF_OPEN→CLOSED→OPEN. Fixed version will oscillate rapidly: CLOSED→OPEN→HALF_OPEN→CLOSED→OPEN within milliseconds, never stabilizing.

3. **Information Cost Prediction**: Implement the separated design. Run both versions against a degraded service (70% success rate). Original tracks failure rate as "5 calls failed." Separated design tracks it as "5 calls failed, but 15 service attempts total." To get same opening behavior, separated design needs `failure_threshold = 1` (any failure opens it) instead of `threshold = 5`. This cascades — lower threshold means higher false-positive circuit openings on transient errors.
