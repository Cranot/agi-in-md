# Structural Analysis: Retry + Circuit Breaker

---

## The Claim

**The deepest structural problem: the circuit breaker's state machine is driven by a signal the retry mechanism has already corrupted.**

`_on_failure()` increments `_failure_count` once per exhausted retry group, not once per failed attempt. Three failures happened; one was counted. A success on retry 3 calls `_on_success()` while two invisible failures dissolve. The circuit breaker responds to a *filtered, compressed* signal and mistakes it for a raw one.

This is falsifiable: set `failure_threshold=2`, call a function that fails twice then succeeds. The circuit never opens despite 4+ underlying failures.

---

## Three Experts

**Defender**: The claim is wrong about what circuit breakers should count. Retrying is an implementation detail of the caller's intent. The circuit should respond to *outcomes*, not attempts. Counting individual retries would cause premature opening on transient errors — the exact failure mode circuit breakers exist to prevent.

**Attacker**: The claim understates the problem. `_retry_with_backoff` can sleep up to ~10 seconds (`1 + 2 + 4 + 3 random`). During `OPEN → HALF_OPEN` transition, the circuit transitions *then immediately burns its entire retry budget inside that single execute() call*. The circuit has been HALF_OPEN for 10 seconds while attempting one conceptual call. The timing model is broken independently of the counting model.

**Prober** (attacking what both assume): Both assume retry policy belongs to the circuit breaker. But look at `_retry_with_backoff`'s signature — `max_retries=3, base_delay=1` are buried as defaults, unconfigurable at the class level, unknown to callers. The deeper assumption is that *one retry policy fits all calls through this breaker*. The defender defends outcome-counting without asking: outcome of what, decided by whom? The attacker times the sleep without asking: who authorized that sleep to happen inside a state transition?

**Transformed claim**: The deepest problem is **ownership misattribution of the retry policy**. The circuit breaker has stolen the caller's right to determine retry behavior, then built its state machine on the corrupted signal that theft produces. The signal is simultaneously: (a) undersampled relative to actual failure pressure, (b) time-dilated by sleep occurring *inside* state transitions, and (c) owned by the wrong layer. These three defects are not independent — they are all consequences of the same architectural confusion.

---

## The Concealment Mechanism

**Semantic aliasing through exception uniformity.**

Every exception exiting `_retry_with_backoff` looks identical to `execute()`'s `except` clause — just an `Exception`. The retry mechanism has pre-processed the signal (retrying N times) but stripped all metadata about that processing. The circuit breaker receives the processed output and treats it as if it were a first-attempt, unretried failure.

The code hides this because:
1. `_retry_with_backoff` transparently re-raises — syntactically clean
2. The `try/except` in `execute()` catches it and calls `_on_failure()` — *appears* correct
3. No type, field, or marker distinguishes "first-attempt failure" from "all-retries-exhausted failure"

The structural lie is embedded in what the exception does **not** carry.

---

## Improvement 1: Metrics and Observability

A legitimate-looking improvement: add structured metrics. This passes code review by making the system *look* more observable.

```python
import time, random, logging
from dataclasses import dataclass, field
from typing import Callable, Any

logger = logging.getLogger(__name__)

@dataclass
class CircuitBreakerMetrics:
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0         # per retry-group
    rejected_calls: int = 0
    retry_attempts: int = 0       # per individual attempt

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
        self.metrics = CircuitBreakerMetrics()

    def execute(self, fn, *args, **kwargs):
        self.metrics.total_calls += 1

        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
                logger.info("Circuit transitioning to HALF_OPEN")
            else:
                self.metrics.rejected_calls += 1
                raise Exception("Circuit is open")

        try:
            result = self._retry_with_backoff(fn, *args, **kwargs)
            self._on_success()
            self.metrics.successful_calls += 1
            logger.debug(f"Call succeeded. State: {self._state}")
            return result
        except Exception as e:
            self._on_failure()
            self.metrics.failed_calls += 1
            logger.error(f"Call failed after retries: {e}. State: {self._state}")
            raise

    def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                self.metrics.retry_attempts += 1   # counts each individual attempt
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay:.2f}s"
                )
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

    @property
    def state(self):
        return self._state

    @property
    def health_summary(self):
        return {
            "state": self._state,
            "failure_count": self._failure_count,
            "metrics": self.metrics,
        }
```

**Why this deepens concealment**: `retry_attempts` and `failed_calls` now coexist as named, documented fields. Their discrepancy looks intentional — a design choice, not a bug. A reviewer sees metrics, logging, and a `health_summary` property and concludes the system is observable. The semantic aliasing is now *documented* rather than implicit, which is harder to challenge.

---

## Three Properties Visible Only Because We Strengthened It

**1. The metric split makes the counting mismatch undeniable.**
`retry_attempts` will always be `≥ failed_calls × (max_retries - 1)` in the worst case. The circuit breaker ignores `retry_attempts` entirely when computing state. This is now a named, visible number being thrown away — the original code hid the discarding by never computing the number.

**2. The logging exposes that the circuit is blind during retries.**
`logger.warning(f"Attempt {attempt+1}...")` runs while the circuit's state might be anything. The logs show retry activity, but the circuit has no idea retries are happening. The state machine's blindness is now auditable.

**3. Thread safety becomes an explicit crisis.**
Multiple threads writing to `self.metrics.retry_attempts` simultaneously will produce corrupted counts. The original code's shared state problem existed before, but the metrics object makes it a concrete, named artifact. Concurrent mutation is now visible and documented.

---

## Improvement 2: Attempt-Level Signal

Address the recreated property — the two-observer problem — by making the circuit breaker consume per-attempt signals:

```python
def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
    for attempt in range(max_retries):
        try:
            result = fn(*args, **kwargs)
            self._on_attempt_success()      # NEW: signal per attempt
            return result
        except Exception as e:
            self._on_attempt_failure()      # NEW: signal per attempt
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)

def _on_attempt_failure(self):
    """Circuit responds to every attempt, not just exhausted groups."""
    self._failure_count += 1
    self._last_failure_time = time.time()
    if self._failure_count >= self._failure_threshold:
        self._state = self.OPEN           # <-- can open mid-retry

def _on_attempt_success(self):
    self._failure_count = max(0, self._failure_count - 1)  # decay on success

def _on_success(self):                    # called after retry loop completes
    if self._state == self.HALF_OPEN:
        self._success_count += 1
        if self._success_count >= self._half_open_max:
            self._state = self.CLOSED
            self._failure_count = 0

def _on_failure(self):                    # now just updates timestamp
    self._last_failure_time = time.time()
```

**Diagnostic applied to Improvement 2:**

This improvement conceals that **the circuit can now open mid-retry, and the retry loop does not respect that**. If `failure_threshold=2` and we're on attempt 2, `_on_attempt_failure()` sets `_state = OPEN`. The retry loop continues. We are now retrying while the circuit is OPEN — a direct contradiction of the circuit breaker's purpose.

**Property of the original problem visible only because Improvement 2 recreates it:**

The original problem had an implicit incompatible time model between retry and circuit breaking. Improvement 2 forces that incompatibility into the open: the circuit's state machine assumes time advances in discrete *call units*. The retry mechanism inserts real time (sleep) and real attempts *inside* what the circuit considers one unit. **There is no consistent definition of "one call" that both mechanisms can agree on.** This was always true; Improvement 2 makes the contradiction executable.

---

## The Structural Invariant

**The property that persists through every improvement:**

> The failure signal must simultaneously serve as a *sequence* (for the retry mechanism, which needs per-attempt decisions about whether to continue) and an *aggregate* (for the circuit breaker, which needs a health summary to make state transitions). These representations are not reducible to each other — maximizing the signal's usefulness for one corrupts it for the other.

Every improvement either:
- Gives the circuit breaker the sequence → false positive openings on transient errors
- Gives the circuit breaker the aggregate → invisible failure pressure from retries
- Gives both → the two representations conflict at runtime

This invariant persists because it is not a property of the implementation. It is a property of having two state machines with different temporal models sharing one failure channel.

---

## Inverting the Invariant

Make the impossible property trivially satisfiable by **separating the concerns entirely** — give each mechanism its own signal, owned by its own layer:

```python
# Design 1 (Inverted): Retry wraps the function BEFORE the circuit breaker sees it

def with_retry(fn: Callable, max_retries: int = 3, base_delay: float = 1.0) -> Callable:
    """Retry policy is the caller's concern. Returns a callable."""
    def wrapped(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception:
                if attempt == max_retries - 1:
                    raise
                time.sleep(base_delay * (2 ** attempt) + random.uniform(0, 1))
    return wrapped

class CircuitBreaker:
    """Pure circuit breaker: no retry logic, no ownership of retry policy."""
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None

    def execute(self, fn: Callable, *args, **kwargs):
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
            else:
                raise Exception("Circuit is open")
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

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

# Usage — caller owns retry policy:
cb = CircuitBreaker(failure_threshold=5)
retried_fn = with_retry(my_service_call, max_retries=3)
result = cb.execute(retried_fn)
```

**The signal integrity problem is solved. Each mechanism owns its signal.**

**New impossibility the inversion creates:**

The circuit breaker can no longer distinguish between:
- A function that always fails immediately (high failure rate, low latency)
- A function that always succeeds on retry 3 (lower failure rate, high latency from sleep)

Both present the same signal: eventual success or final failure. The circuit breaker **loses the ability to treat retry-induced latency as a health signal**. A service that takes 15 seconds to respond because 3 retries sleep through is *indistinguishable from a healthy, fast service* to this circuit breaker. Additionally: the retry mechanism cannot observe the circuit's state — if the circuit opens concurrently (from another caller), `with_retry` will keep retrying into an open circuit because it has no access to `cb._state`.

---

## Conservation Law (First Finding)

| Design | Signal integrity | Semantic coupling |
|--------|-----------------|-------------------|
| Original (fused) | Corrupted (retry filters before CB sees it) | High (CB and retry share state, can communicate) |
| Inverted (separated) | Clean (each mechanism sees its own signal) | None (mechanisms cannot communicate health semantics) |

**Conservation Law**: *Health expressiveness = signal integrity + semantic coupling.* Concentrating the signal enables cross-concern semantics but corrupts the signal's meaning. Separating the signal preserves meaning but destroys cross-concern semantics. The total is conserved; distribution varies.

**First Finding**: In any synchronous, in-process resilience system combining retry and circuit breaking, improving the circuit breaker's signal fidelity costs exactly the cross-concern health semantics it needs to act on that signal, and vice versa.

---

## Design 3: Escaping the Conservation Law

The conservation law is a consequence of **synchronous shared state in a single process**. Escape by moving to an **event-sourced observation** model — a different design category entirely:

```python
from dataclasses import dataclass, field
from typing import List, Callable, Optional
import threading

# Events are the primitive — not shared mutable state
@dataclass
class AttemptFailed:
    attempt: int
    error: Exception
    timestamp: float = field(default_factory=time.time)

@dataclass
class AttemptSucceeded:
    attempt: int
    timestamp: float = field(default_factory=time.time)

@dataclass  
class CallExhausted:
    total_attempts: int
    final_error: Exception
    timestamp: float = field(default_factory=time.time)

@dataclass
class CallSucceeded:
    total_attempts: int
    timestamp: float = field(default_factory=time.time)

class EventBus:
    def __init__(self):
        self._handlers: dict = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: type, handler: Callable):
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event):
        with self._lock:
            handlers = list(self._handlers.get(type(event), []))
        for handler in handlers:
            handler(event)    # synchronous for now — see analysis below

class RetryExecutor:
    """Owns retry policy. Publishes events. Knows nothing about circuit state."""
    def __init__(self, bus: EventBus, max_retries: int = 3, base_delay: float = 1.0):
        self._bus = bus
        self._max_retries = max_retries
        self._base_delay = base_delay

    def execute(self, fn: Callable, *args, **kwargs):
        for attempt in range(self._max_retries):
            try:
                result = fn(*args, **kwargs)
                self._bus.publish(AttemptSucceeded(attempt=attempt))
                self._bus.publish(CallSucceeded(total_attempts=attempt + 1))
                return result
            except Exception as e:
                self._bus.publish(AttemptFailed(attempt=attempt, error=e))
                if attempt == self._max_retries - 1:
                    self._bus.publish(CallExhausted(
                        total_attempts=self._max_retries, final_error=e
                    ))
                    raise
                time.sleep(self._base_delay * (2 ** attempt) + random.uniform(0, 1))

class CircuitBreakerPolicy:
    """Owns circuit state. Subscribes to events. Knows nothing about retry logic."""
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, bus: EventBus, failure_threshold: int = 5,
                 reset_timeout: float = 30, half_open_max: int = 3):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

        # Subscribe to both granularities — the circuit chooses what it responds to
        bus.subscribe(AttemptFailed, self._on_attempt_failed)
        bus.subscribe(CallExhausted, self._on_call_exhausted)
        bus.subscribe(CallSucceeded, self._on_call_succeeded)

    def _on_attempt_failed(self, event: AttemptFailed):
        # Can respond to fine-grained signal if desired
        pass  # or: update a sliding window of attempt failures

    def _on_call_exhausted(self, event: CallExhausted):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = event.timestamp
            if self._failure_count >= self._failure_threshold:
                self._state = self.OPEN

    def _on_call_succeeded(self, event: CallSucceeded):
        with self._lock:
            if self._state == self.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._half_open_max:
                    self._state = self.CLOSED
                    self._failure_count = 0
            else:
                self._failure_count = 0

    def should_allow(self) -> bool:
        with self._lock:
            if self._state == self.OPEN:
                if (self._last_failure_time and
                        time.time() - self._last_failure_time > self._reset_timeout):
                    self._state = self.HALF_OPEN
                    self._success_count = 0
                    return True
                return False
            return True

# Usage:
bus = EventBus()
circuit = CircuitBreakerPolicy(bus, failure_threshold=5)
executor = RetryExecutor(bus, max_retries=3)

def guarded_execute(fn, *args, **kwargs):
    if not circuit.should_allow():
        raise Exception("Circuit is open")
    return executor.execute(fn, *args, **kwargs)
```

**What becomes possible**: The circuit breaker can subscribe to *both* `AttemptFailed` and `CallExhausted`, choosing its own aggregation policy without corrupting the retry mechanism's signal. New policies (rate limiters, hedging, bulkheads) can join by subscribing to the same bus. Retry and circuit breaking are genuinely decoupled but remain observable to each other.

**New impossibility that appears**: **Temporal ordering of effect becomes indeterminate.** When `AttemptFailed` is published, the circuit breaker's `_on_attempt_failed` handler runs synchronously here — but in an async bus this is not guaranteed. Even synchronously: the circuit's `should_allow()` was checked *before* `RetryExecutor.execute()` began. By the time attempt 2 fires, the circuit state has changed based on events from *this very call*, but `should_allow()` is never rechecked mid-retry. The retry executor cannot ask "is the circuit still open?" between attempts — it has no reference to `circuit`. The information is complete; the decision is not timely.

---

## The Relationship (Second Finding)

The conservation law (`signal integrity + semantic coupling = constant`) was a consequence of synchronous shared state — to express cross-concern health semantics, you must share state, which corrupts the signal.

The event-sourced design breaks this by replacing shared state with published events. But the new impossibility (observation latency, decision-without-current-state) is not arbitrary — it is **the same trade-off expressed on a different axis**. The conservation law was about what information can be *represented* simultaneously in a single signal. The new impossibility is about what information can be *acted upon* simultaneously in a single moment.

**Second Finding**: The conservation law is not specific to synchronous shared state — it is a statement about the relationship between observation granularity and decision granularity in resilience systems. Changing the implementation category (from shared state to events) transforms the axis of the trade-off from *representational* to *temporal*, but does not eliminate the trade-off. The escape's new impossibility is the conservation law in a different coordinate system.

---

## The Meta-Conservation Law

**Property conserved across all three designs**:

> In every design, the temporal resolution at which health is *observed* and the temporal resolution at which health *decisions take effect* cannot be simultaneously maximized.

| Design | Observation resolution | Decision resolution | Cost |
|--------|----------------------|-------------------|------|
| Original (fused) | Retry-group (coarse) | Retry-group (coarse) | Failure pressure invisible within groups |
| Inverted (separated) | Call-outcome (clean) | Call-outcome | Latency and partial failure invisible |
| Escaped (events) | Per-attempt (fine) | Per-check of `should_allow()` | Decision uses state computed from past events, not present |

In all three cases, something is either observed too late to decide on, or decided on without current observation.

**Meta-conservation law**: *In any resilience mechanism that combines retry with circuit breaking, the product of observation granularity and decision timeliness is bounded by a constant determined by the call graph structure, not the implementation.* You cannot observe at maximum resolution AND act on that observation in real time simultaneously — not because of implementation failure, but because the retry loop and the circuit check occupy different positions in the call graph, and information must travel between them.

---

## What This Predicts About Future Designs

Any future design that attempts to combine retry with circuit breaking will face an irreducible choice:

1. **Designs that claim to observe per-attempt and decide per-attempt** will discover they've introduced false-positive circuit openings (the circuit opens on retriable transients) or created a feedback loop where the circuit opens mid-retry and the retry policy doesn't know.

2. **Designs that push retry outside the circuit breaker** will lose the ability to treat retry-induced latency and partial failure as health signals.

3. **Designs that use events or actors to decouple** will trade representational ambiguity for temporal ambiguity — the information is there, but the decision is always made on slightly stale state.

4. **Any design that claims to escape all three** has changed what "health" means — either by making the circuit breaker a passive observer of an external health metric (moving the problem upstream), or by eliminating retry as a concept (moving the problem downstream). The problem is conserved; only its location changes.

The meta-conservation law predicts: **the location of the retry/circuit-breaker impedance mismatch is variable; its existence is not.** Design effort in this space is not solving the problem — it is choosing where to put it.
