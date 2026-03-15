# Structural Diagnosis: The Architecture Blinds Itself

## Falsifiable Claim (Initial)

**"The retry mechanism obscures actual service health from the circuit breaker by filtering out recovered failures, causing the breaker to infer reliability from post-recovery outcomes while remaining ignorant of pre-recovery attempts. In HALF_OPEN state specifically, a service that succeeds only on retry #2 or #3 looks identical to a service that succeeded immediately—both register as one success—making premature circuit closure inevitable."**

---

## The Three Expert Challenge

**Expert 1 (Defender):** Exactly right. Trace HALF_OPEN: service fails attempt 1, fails attempt 2, succeeds attempt 3. The circuit breaker sees one `_on_success()` call and increments `_success_count`. If that reaches `_half_open_max=3`, the circuit closes. But the underlying service has a 33% success rate. It will fail on the next call immediately.

**Expert 2 (Attacker):** This confuses resilience with health assessment. Retries are **supposed** to hide transient faults. That's their job. The real issue is elsewhere—maybe the thresholds, maybe the timeout math, maybe that failure_count never resets in CLOSED state so one burst of failures followed by a long recovery period still triggers OPEN.

**Expert 3 (Prober):** Both miss the deeper frame. You're observing **the output of a filter** and trying to infer **the input signal**. The retry mechanism is a recovery filter. The circuit breaker has no channel to observe *raw service failures*—only the success/failure of calls that have already been run through 0-3 retry attempts. You're trying to measure "is the service healthy?" but you can only see "did this request eventually succeed?" These aren't the same thing. A consistent 70%-failure service can look perfectly healthy if every request gets 3 attempts.

---

## The Transformed Claim (The Real Problem)

**The circuit breaker and retry mechanism share a single success/failure signal, but operate at different abstractions: retry operates on *attempt-level resilience* while circuit breaker requires *service-health visibility*. The shared signal makes the breaker operate on post-filtered noise, preventing it from ever observing the actual service reliability it's supposed to protect against.**

**Concealment mechanism:** Each call to `execute()` returns a single success/failure outcome that *blends* the retry layer with the health-assessment layer. Neither layer is separately observable. The architecture hides this by naming the boundary between them `_retry_with_backoff()` and `_on_failure()`—making it look like clean separation when it's actually information loss.

---

## Engineering the Deceptive Improvement

Here's a "fix" that sounds rigorous and would pass code review, but deepens the concealment:

```python
class CircuitBreaker:
    # ... existing code ...
    
    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3):
        # ... existing ...
        self._consecutive_failures = 0  # New: track consecutive failures
        self._last_success_time = None

    def execute(self, fn, *args, **kwargs):
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
                self._consecutive_failures = 0  # Reset on state transition
            else:
                raise Exception("Circuit is open")

        try:
            result = self._retry_with_backoff(fn, *args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self._consecutive_failures = 0  # Reset consecutive count
        self._last_success_time = time.time()
        
        if self._state == self.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._half_open_max:
                self._state = self.CLOSED
                self._failure_count = 0
        else:
            self._failure_count = 0

    def _on_failure(self):
        self._consecutive_failures += 1
        self._last_failure_time = time.time()
        
        if self._state == self.HALF_OPEN:
            # Stricter in HALF_OPEN: reopen immediately on failure
            self._state = self.OPEN
        else:
            self._failure_count += 1
            if self._failure_count >= self._failure_threshold:
                self._state = self.OPEN
```

**Why this passes review:**
- "Consecutive failures" tracking looks sophisticated
- HALF_OPEN now "properly" reopens on any failure (seems safer)
- State reset logic is explicit
- Code is more defensive

---

## Three Properties Revealed by the Attempted Fix

### 1. **State-Specific Logic Unmasks Architectural Confusion**

By trying to improve HALF_OPEN handling, I revealed that the original problem isn't a bug in the logic—it's that **we're using one feedback channel for three different purposes:**
- CLOSED state: detect when service starts failing (use `_failure_count`)
- HALF_OPEN state: detect when service has recovered (use `_success_count`)
- OPEN state: detect when we should try again (use timeout)

Each needs different semantics, but they're all funneled through `_on_success()/_on_failure()`. The original code hides this by making the methods simple. My improvement reveals it by making them state-specific.

### 2. **Temporal Asymmetry Cannot Be Fixed with Stricter Rules**

When I added `self._consecutive_failures` and made HALF_OPEN reopen on any failure, I forced something into the open: **you cannot distinguish "service flaked once" from "service is still broken" without observing the time-series of raw attempts.**

The original code tried to pretend this didn't matter by averaging failures over calls. My improvement tried to get stricter by reopening on any HALF_OPEN failure. But both are gambling on what the retries are hiding. Adding `_consecutive_failures` revealed that threshold-based state machines can't capture service reliability—they need observable failure rates, not just counts.

### 3. **The Improvement Needs Metrics It Cannot Access**

When I tried to make the logic stricter, I implicitly created questions the code cannot answer:
- "Is this failure likely to recur?"  
- "How many retry attempts happened before this success?"
- "Is the success rate trending up or down?"

These are visible only if you track raw attempts. The original code hides the need for these metrics by wrapping everything in `_retry_with_backoff()`. My improvement makes the need visible because I'm trying to make decisions in HALF_OPEN without this information—and the decisions become arbitrary.

---

## Diagnostic Applied to My Own Improvement

**What does my improvement conceal?**

1. It conceals that we still cannot see the actual service failure rate. By reopening HALF_OPEN on any failure, it creates the illusion of rigor, but we're still operating on post-retry outcomes. A service with 60% failure rate that gets 3 retries per call will still appear sporadic—sometimes succeeding, sometimes not—and my improvement will flap between HALF_OPEN and OPEN without ever observing the real signal.

2. It conceals that the problem is *architectural*, not algorithmic. By adding more state logic, I'm trying to patch a fundamental design flaw (shared feedback channel) with a local fix (state-specific rules). The patch works until it doesn't—exactly like the original code.

**What property of the original problem is visible only because my improvement recreates it?**

**The original code and my improvement both require the same impossible oracle: they need to assess service health based only on whether individual calls eventually succeeded, filtered through a retry mechanism designed to hide failures.** 

The original code hides this by staying simple. My improvement reveals it by getting complex—because when I try to be stricter, I immediately run into the fact that strictness without observability is just arbitrary threshold-tuning.

The only way either code "works" is if the real service health is already favorable enough that the retry mechanism doesn't filter much. In that case, the circuit breaker is unnecessary. If the service is unreliable enough to need a circuit breaker, the retry mechanism inevitably hides the signal the breaker needs. **Both versions encode this contradiction in their structure.**
