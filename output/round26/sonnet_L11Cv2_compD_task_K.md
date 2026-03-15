## Analysis: Retry-Wrapped Circuit Breaker

---

## Step 1 — Name the Concealment Mechanism

**"Nested State Laundering"**

The retry loop is *interior* to the circuit breaker's single observation point. The circuit breaker's state machine receives one laundered event per `execute()` call — but that event conceals up to 3 attempts, up to ~3–4 seconds of backoff delay, and an unknown number of intermediate exceptions. Two independent state machines (retry's attempt counter, circuit breaker's failure counter) share no visibility into each other's state.

This creates three compounding distortions:

| Distortion | Mechanism | Effect |
|---|---|---|
| **Failure undercount** | `_failure_count` increments once per exhausted retry burst, not per attempt | Circuit opens 3× slower than intended under sustained load |
| **Temporal erosion** | Backoff delays (1s + 2s + jitter) are consumed *before* `_last_failure_time` can reset the window | A 30s timeout window is effectively 26–27s |
| **HALF_OPEN amplification** | A "probe" in HALF_OPEN fires 3 retries with backoff — far more load than a single test | Damages the recovering service instead of probing it |

---

## Structural Problems (Full Inventory)

```python
# BUG 1: HALF_OPEN failure doesn't immediately re-open
def _on_failure(self):
    self._failure_count += 1          # ← doesn't check _state == HALF_OPEN
    self._last_failure_time = time.time()
    if self._failure_count >= self._failure_threshold:
        self._state = self.OPEN
    # Any failure in HALF_OPEN should instantly → OPEN
    # Instead: relies on accumulated _failure_count from previous OPEN episode

# BUG 2: _failure_count not reset on OPEN → HALF_OPEN transition
if time.time() - self._last_failure_time > self._reset_timeout:
    self._state = self.HALF_OPEN
    self._success_count = 0           # ← resets success
    # ← MISSING: self._failure_count = 0

# BUG 3: kwargs namespace collision
def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
    return fn(*args, **kwargs)
    # If caller's fn legitimately needs a kwarg named 'max_retries',
    # it gets silently intercepted here

# BUG 4: One success in CLOSED wipes all near-failures
def _on_success(self):
    else:
        self._failure_count = 0       # ← 4 failures + 1 success = clean slate
    # Threshold of 5 is meaningless under alternating success/failure

# BUG 5: No thread safety — state transitions are not atomic
# BUG 6: All exceptions are equivalent — timeout ≠ auth failure ≠ serialization error
```

---

## Step 2 — Improvement: Surface the Hidden Layer (Deepened)

Make the concealment *principled* by giving the circuit breaker a probe hook into each retry attempt, without merging the two state machines:

```python
import time, random, threading
from enum import Enum
from typing import Callable, Optional, Type

class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class RetryPolicy:
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0,
                 retryable: tuple[Type[Exception], ...] = (Exception,)):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.retryable = retryable

    def execute(self, fn: Callable, *args,
                attempt_hook: Optional[Callable[[int, Exception | None], None]] = None,
                **kwargs):
        last_exc = None
        for attempt in range(self.max_attempts):
            try:
                result = fn(*args, **kwargs)
                if attempt_hook:
                    attempt_hook(attempt, None)   # ← success probe
                return result
            except self.retryable as e:
                last_exc = e
                if attempt_hook:
                    attempt_hook(attempt, e)      # ← failure probe: CB sees raw attempt
                if attempt < self.max_attempts - 1:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    time.sleep(delay)
        raise last_exc

class CircuitBreaker:
    def __init__(self,
                 failure_threshold: int = 5,
                 reset_timeout: float = 30.0,
                 half_open_max_successes: int = 3,
                 retry_policy: Optional[RetryPolicy] = None):
        self._state = State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max_successes
        self._last_failure_time: Optional[float] = None
        self._lock = threading.RLock()
        # Inject retry policy — default is single-attempt in HALF_OPEN
        self._retry_policy = retry_policy or RetryPolicy(max_attempts=3)
        self._half_open_retry = RetryPolicy(max_attempts=1)  # ← conservative probe

    def _current_retry_policy(self) -> RetryPolicy:
        """State-aware retry selection — the key structural insight."""
        return self._half_open_retry if self._state == State.HALF_OPEN \
               else self._retry_policy

    def execute(self, fn: Callable, *args, **kwargs):
        with self._lock:
            if self._state == State.OPEN:
                elapsed = time.time() - self._last_failure_time
                if elapsed > self._reset_timeout:
                    self._transition_to(State.HALF_OPEN)
                else:
                    raise CircuitOpenError(
                        f"Circuit open. Retry in {self._reset_timeout - elapsed:.1f}s"
                    )
            policy = self._current_retry_policy()

        # Execute outside lock — don't hold lock during IO
        def attempt_hook(attempt: int, exc: Exception | None):
            with self._lock:
                if exc is not None:
                    self._record_attempt_failure()
                # successes recorded at top level only (avoid double-counting)

        try:
            result = policy.execute(fn, *args, attempt_hook=attempt_hook, **kwargs)
            with self._lock:
                self._on_execute_success()
            return result
        except Exception as e:
            # _on_failure already called per-attempt via hook; only transition here
            raise

    def _record_attempt_failure(self):
        """Called per retry attempt — the visibility the original lacked."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._state == State.HALF_OPEN:
            self._transition_to(State.OPEN)          # ← immediate on any HALF_OPEN failure
        elif self._failure_count >= self._failure_threshold:
            self._transition_to(State.OPEN)

    def _on_execute_success(self):
        if self._state == State.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._half_open_max:
                self._transition_to(State.CLOSED)
        elif self._state == State.CLOSED:
            # Decay rather than zero-reset: preserve failure memory
            self._failure_count = max(0, self._failure_count - 1)

    def _transition_to(self, new_state: State):
        self._state = new_state
        if new_state == State.HALF_OPEN:
            self._failure_count = 0       # ← fixed: reset on HALF_OPEN entry
            self._success_count = 0
        elif new_state == State.CLOSED:
            self._failure_count = 0
            self._success_count = 0

class CircuitOpenError(Exception):
    pass
```

---

## Step 3 — Diagnostic on Improvement

```
┌─────────────────────────────────────────────────────┐
│ DIAGNOSTIC: Improvement v1                          │
├──────────────────┬──────────────────────────────────┤
│ FIXED            │ HALF_OPEN immediately → OPEN      │
│                  │ _failure_count reset on HALF_OPEN │
│                  │ CB sees per-attempt failures      │
│                  │ Thread-safe state transitions     │
│                  │ Conservative HALF_OPEN probing    │
│                  │ Failure memory decays (not zeros) │
├──────────────────┼──────────────────────────────────┤
│ NEW PROBLEM A    │ Lock released between state-check │
│                  │ and policy.execute() — TOCTOU gap │
│                  │ State can change between reading  │
│                  │ policy and executing              │
├──────────────────┼──────────────────────────────────┤
│ NEW PROBLEM B    │ attempt_hook closure captures     │
│                  │ self but lock is re-acquired per  │
│                  │ attempt — fine for RLock but      │
│                  │ failure count now increments per  │
│                  │ attempt, so threshold=5 trips on  │
│                  │ first execute() with 5 retries    │
│                  │ — semantics changed               │
├──────────────────┼──────────────────────────────────┤
│ NEW PROBLEM C    │ Decay (-1 per success) means      │
│                  │ failure_count tracks "net" not    │
│                  │ "recent" failures. Under bursty   │
│                  │ traffic, old failures persist     │
│                  │ → circuit never opens             │
├──────────────────┼──────────────────────────────────┤
│ UNRESOLVED       │ Exception type discrimination     │
│                  │ No metrics/observability          │
└──────────────────┴──────────────────────────────────┘
```

**Root cause of Problem B**: changing from per-`execute()` to per-attempt counting changes the unit of `_failure_threshold`. The threshold value now means "attempts" not "calls." Callers can't reason about the threshold without knowing the retry policy — the two are now *semantically coupled* even though they appear structurally decoupled.

---

## Step 4 — Second Improvement: Separate Failure Budgets

The insight from Problem B: the circuit breaker's threshold and the retry policy's attempt count measure different things. Give each its own budget, measured independently:

```python
from dataclasses import dataclass, field
from collections import deque

@dataclass
class WindowedFailureCounter:
    """Sliding window failure rate — fixes both the zero-reset and decay problems."""
    window_seconds: float = 60.0
    failure_threshold_rate: float = 0.5   # open if >50% of calls fail
    min_calls: int = 5                    # don't open on first call
    _events: deque = field(default_factory=deque, init=False)

    def record(self, success: bool):
        now = time.time()
        self._events.append((now, success))
        self._prune(now)

    def _prune(self, now: float):
        cutoff = now - self.window_seconds
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    @property
    def should_open(self) -> bool:
        if len(self._events) < self.min_calls:
            return False
        failures = sum(1 for _, ok in self._events if not ok)
        return (failures / len(self._events)) >= self.failure_threshold_rate

    @property
    def failure_rate(self) -> float:
        if not self._events:
            return 0.0
        return sum(1 for _, ok in self._events if not ok) / len(self._events)


class CircuitBreaker2:
    """
    Two separate budgets:
      - retry policy owns: attempt count, backoff timing
      - circuit breaker owns: call-level success/failure rate over a window
    The attempt_hook bridges them without coupling their semantics.
    """
    def __init__(self,
                 counter: WindowedFailureCounter = None,
                 reset_timeout: float = 30.0,
                 half_open_probe_successes: int = 3,
                 retry_policy: RetryPolicy = None):
        self._counter = counter or WindowedFailureCounter()
        self._reset_timeout = reset_timeout
        self._half_open_probe_successes = half_open_probe_successes
        self._state = State.CLOSED
        self._half_open_successes = 0
        self._opened_at: Optional[float] = None
        self._lock = threading.RLock()
        self._retry_policy = retry_policy or RetryPolicy(max_attempts=3)

    def execute(self, fn: Callable, *args, **kwargs):
        self._check_state()

        policy = RetryPolicy(max_attempts=1) \
                 if self._state == State.HALF_OPEN \
                 else self._retry_policy

        try:
            result = policy.execute(fn, *args, **kwargs)
            self._on_call_success()
            return result
        except Exception:
            self._on_call_failure()
            raise

    def _check_state(self):
        with self._lock:
            if self._state == State.OPEN:
                if time.time() - self._opened_at > self._reset_timeout:
                    self._state = State.HALF_OPEN
                    self._half_open_successes = 0
                else:
                    raise CircuitOpenError()

    def _on_call_success(self):
        with self._lock:
            self._counter.record(True)
            if self._state == State.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self._half_open_probe_successes:
                    self._state = State.CLOSED

    def _on_call_failure(self):
        with self._lock:
            self._counter.record(False)
            if self._state == State.HALF_OPEN:
                self._state = State.OPEN          # immediate
                self._opened_at = time.time()
            elif self._counter.should_open:
                self._state = State.OPEN
                self._opened_at = time.time()
```

---

## Step 5 — Name the Structural Invariant

**"Observation granularity equals execution granularity."**

Every design in this progression assumes the circuit breaker observes at the same level it controls: one `execute()` call = one observable outcome. The retry layer is always subordinate and invisible. This invariant is *load-bearing* — all state machine logic depends on it — yet it is *never stated*.

---

## Step 6 — Invert the Invariant

**Inverted: observation is finer than execution.**

The circuit breaker observes at *sub-call* granularity — individual bytes, partial responses, connection events — while control happens at the call level. Think: streaming responses, health of a connection pool, or TCP-level keepalives. The circuit breaker opens not because a call failed, but because 50ms response latency spiked *within* a call that ultimately succeeded.

```
Original:    [call] → [observe outcome]        (1 call = 1 observation)
Inverted:    [call] → [observe stream of signals] → [decide mid-call]
```

Alternatively, the orthogonal inversion:

**Inverted: execution is finer than observation.**

The circuit breaker makes one binary decision that governs a *batch* of calls — a traffic routing decision, a bulkhead allocation, a deployment gate. One observation (canary health score) controls thousands of executions.

---

## Step 7 — Conservation Law Between Original and Inverted Impossibilities

**"The Resolution–Control Duality"**

> *You cannot simultaneously maximize the temporal resolution of failure observation and minimize the coupling between the observation mechanism and the execution unit. Any gain in observation granularity costs proportional coupling into the execution path; any gain in decoupling costs proportional coarsening of observation.*

| Design | Observation Resolution | Coupling |
|---|---|---|
| Original (nested retry) | Low — per-exhausted-burst | Low — retry is opaque |
| Improvement v1 | Medium — per-attempt | Medium — hook required |
| Improvement v2 | Low — per-call (windowed rate) | Low — fully decoupled |
| Inverted (sub-call) | High — per-signal | High — CB must instrument execution |
| Inverted (batch control) | Low — per-cohort | Low — CB is external |

The conservation law: **information about failure is neither created nor destroyed — only redistributed between the retry layer and the circuit breaker layer.** When you compress failures into a single event (original), the circuit breaker is simple but blind. When you expand visibility (inverted), the circuit breaker is precise but entangled.

The original code's bug is not that it made the wrong choice — it is that it made a choice *without knowing it was choosing.*

---

## Step 8 — Predict a Third Design

**"Event-Sourced Circuit State"**

Following the conservation law: eliminate the layer boundary entirely. Instead of retry-inside-CB or CB-outside-retry, both become *subscribers to a shared failure event log*. Neither calls the other.

```
┌──────────────────────────────────────────────────────┐
│                  Execution Bus                       │
│                                                      │
│  fn() attempt ──→ AttemptEvent{latency, exc, meta}   │
│                         │                            │
│            ┌────────────┼────────────┐               │
│            ▼            ▼            ▼               │
│       RetryPolicy   CircuitBreaker  Metrics          │
│       (subscriber)  (subscriber)   (subscriber)      │
│            │            │                            │
│            └──────→ Gate ←──────────┘               │
│                      │                              │
│              allow / reject / delay                  │
└──────────────────────────────────────────────────────┘
```

Properties of this design:
- **No nesting**: retry and circuit breaker are peers, not parent/child
- **Shared raw data**: circuit breaker sees every attempt, not laundered calls
- **Composable policies**: swap retry strategy without touching circuit breaker
- **Conservation law resolved explicitly**: both subscribers operate on the same event stream, so resolution is equal for both — the duality collapses into a shared information model
- **The threshold semantics are unambiguous**: `failure_threshold` counts raw attempt events, same unit as retry's `max_attempts`

The cost: the event bus is a new coupling surface — both components must agree on the schema of `AttemptEvent`. You've traded an *implicit* coupling (nested call stack) for an *explicit* one (shared schema). The structural invariant is now a *protocol contract* rather than a hidden architectural assumption.
