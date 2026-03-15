## Structure First Analysis: Retry + Circuit Breaker

---

## Falsifiable Claim: The Deepest Problem

**The retry mechanism and circuit breaker are nested when they must be orthogonal.** This is falsifiable: swap their nesting order and observe categorically different semantics, proving they are independent state machines that the code treats as one.

Specifically: in HALF_OPEN state, the circuit breaker is supposed to fire *one probe request*. Instead, it silently fires three. The probe semantic is destroyed by the nesting, invisibly.

---

## Three Experts Transform It

**Reliability Engineer** sees the failure accounting inversion: retries absorb failures *before* the circuit breaker observes them. The circuit breaker's `failure_threshold=5` actually means "5 logical operations failed after exhausting 3 retries each" — 15 real failures. The threshold is miscalibrated by a factor of `max_retries`.

**Distributed Systems Engineer** sees no mutex around state transitions. Two threads can simultaneously read `_failure_count >= _failure_threshold`, both transition to OPEN, then race on `_success_count` during HALF_OPEN. The state machine is a fiction under concurrency.

**API Designer** sees that `max_retries` and `base_delay` are buried as keyword defaults in `_retry_with_backoff`, invisible at construction time. The retry policy cannot be configured, tested, or replaced without modifying the circuit breaker class.

---

## The Concealment Mechanism

**Nested Encapsulation as Semantic Erasure.**

By placing `_retry_with_backoff` *inside* `execute`, the code makes it appear that retrying is *part of* circuit breaking. The actual structure — two independent state machines with a composition order that changes behavior — becomes invisible. You can read the entire class without realizing you're making a non-obvious architectural choice (retry-inside-CB vs CB-inside-retry) with hard consequences.

---

## First Improvement: Explicit Separation

```python
import time, random, threading
from typing import Callable, Optional, Type

class RetryPolicy:
    def __init__(self, max_retries=3, base_delay=1.0,
                 retryable: Callable[[Exception], bool] = None):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.retryable = retryable or (lambda e: True)

    def execute(self, fn, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if not self.retryable(e) or attempt == self.max_retries - 1:
                    raise
                delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    def execute(self, fn, *args, **kwargs):
        with self._lock:
            self._maybe_transition_to_half_open()
            if self._state == self.OPEN:
                raise CircuitOpenError("Circuit is open")

        try:
            result = fn(*args, **kwargs)
            with self._lock:
                self._on_success()
            return result
        except CircuitOpenError:
            raise
        except Exception:
            with self._lock:
                self._on_failure()
            raise

    def _maybe_transition_to_half_open(self):
        if (self._state == self.OPEN
                and self._last_failure_time
                and time.time() - self._last_failure_time > self._reset_timeout):
            self._state = self.HALF_OPEN
            self._success_count = 0

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

Now composition is *explicit and meaningful*:

```python
cb = CircuitBreaker(failure_threshold=5)
retry = RetryPolicy(
    max_retries=3,
    retryable=lambda e: not isinstance(e, CircuitOpenError)  # never retry open circuit
)

# Strategy A: retry INSIDE circuit breaker
# CB sees 1 logical failure; HALF_OPEN probes correctly fire once
result = cb.execute(lambda: retry.execute(my_fn, arg))

# Strategy B: retry OUTSIDE circuit breaker
# Each attempt is a CB event; effective threshold = 5/3 ≈ 1.6 real failures
result = retry.execute(lambda: cb.execute(my_fn, arg))
```

---

## Three Properties Only Visible Through Construction

**1. The Probe Corruption Property.**
Only when you try to configure HALF_OPEN separately from retry do you discover that retry-inside destroys the probe semantic. You cannot see this in the original code because the two concepts share no interface — the problem has no surface.

**2. The Threshold Dilution Ratio.**
The relationship `effective_threshold = failure_threshold / max_retries` only becomes explicit when you must choose a composition order. Strategy A and Strategy B have thresholds that differ by a factor of 3, using the same numbers. This ratio is invisible until you hold the policies as separate objects.

**3. The `retryable` Predicate Dependency.**
Building `RetryPolicy` forces you to answer: "should we retry a `CircuitOpenError`?" The answer (no) reveals a *semantic dependency* from retry policy to circuit breaker exceptions that was completely hidden in the original nesting. The dependency existed — it was just invisible.

---

## Diagnostic Applied to the Improvement

The improvement separates concerns correctly but introduces **Composition Ambiguity**: Strategy A and Strategy B are syntactically identical in weight — one lambda wrapping another — but semantically opposite in failure semantics. Nothing in the API guides you to the right choice. The concealment mechanism has shifted from *nested encapsulation* to **symmetric composition hiding asymmetric consequence**.

The new deepest problem: the composition order should be determined by a policy about *what counts as a failure for the circuit breaker's purposes*, but that policy has no representation in the system.

---

## Second Improvement: Named Composition Strategies

```python
from dataclasses import dataclass

@dataclass
class ResilienceConfig:
    failure_threshold: int = 5
    reset_timeout: int = 30
    half_open_max: int = 3
    max_retries: int = 3
    base_delay: float = 1.0
    retryable: Callable[[Exception], bool] = None


class ResiliencePolicy:
    """
    Makes the composition order an explicit, named decision.
    """

    @classmethod
    def logical_failures(cls, config: ResilienceConfig) -> "ResiliencePolicy":
        """
        Circuit breaker counts logical operation failures.
        Retries are transparent to the circuit breaker.
        HALF_OPEN sends exactly one logical probe.
        Use when: transient errors should not count against the threshold.
        """
        cb = CircuitBreaker(config.failure_threshold,
                            config.reset_timeout, config.half_open_max)
        retry = RetryPolicy(
            config.max_retries, config.base_delay,
            retryable=lambda e: not isinstance(e, CircuitOpenError)
        )
        return cls(lambda fn, *a, **kw: cb.execute(
            lambda: retry.execute(fn, *a, **kw)
        ))

    @classmethod
    def attempt_failures(cls, config: ResilienceConfig) -> "ResiliencePolicy":
        """
        Circuit breaker counts every individual attempt.
        Retries multiply pressure on the circuit breaker.
        HALF_OPEN probe retries if that probe attempt fails.
        Use when: you want fast circuit opening under sustained load.
        """
        cb = CircuitBreaker(config.failure_threshold,
                            config.reset_timeout, config.half_open_max)
        retry = RetryPolicy(
            config.max_retries, config.base_delay,
            retryable=lambda e: not isinstance(e, CircuitOpenError)
        )
        return cls(lambda fn, *a, **kw: retry.execute(
            lambda: cb.execute(fn, *a, **kw)
        ))

    def __init__(self, strategy: Callable):
        self._strategy = strategy

    def execute(self, fn, *args, **kwargs):
        return self._strategy(fn, *args, **kwargs)
```

---

## The Structural Invariant

**Observation boundaries must match the semantic granularity of the state machine they govern.**

A circuit breaker's state (CLOSED/OPEN/HALF_OPEN) is defined over *logical operations*. Its observation boundary must be the logical operation boundary. A retry policy's decisions are defined over *individual attempts*. Its observation boundary must be the attempt boundary. When these boundaries coincide (original code) or are chosen without guidance (first improvement), the invariant is violated — one policy observes events at the wrong granularity.

---

## Inversion: Where the Impossible Becomes Trivial

**Event-Sourced Resilience — each policy subscribes to the event stream at its own granularity:**

```python
from dataclasses import dataclass, field
from uuid import UUID, uuid4

@dataclass
class ResilienceEvent:
    attempt_id: UUID
    operation_id: UUID           # groups attempts belonging to one logical call
    granularity: str             # "attempt" | "operation"
    outcome: str                 # "success" | "failure"
    exception: Optional[Exception]
    timestamp: float = field(default_factory=time.time)


class EventBus:
    def __init__(self):
        self._subscribers: list[Callable] = []

    def subscribe(self, fn: Callable): self._subscribers.append(fn)
    def publish(self, event: ResilienceEvent):
        for sub in self._subscribers: sub(event)


class ObservingRetryPolicy:
    def __init__(self, bus: EventBus, max_retries=3, base_delay=1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.bus = bus

    def execute(self, fn, operation_id: UUID, *args, **kwargs):
        for attempt in range(self.max_retries):
            attempt_id = uuid4()
            try:
                result = fn(*args, **kwargs)
                self.bus.publish(ResilienceEvent(
                    attempt_id, operation_id, "attempt", "success", None))
                return result
            except Exception as e:
                self.bus.publish(ResilienceEvent(
                    attempt_id, operation_id, "attempt", "failure", e))
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.base_delay * (2 ** attempt) + random.uniform(0, 1))


class ObservingCircuitBreaker:
    """Subscribes to operation-level events only — granularity is explicit."""
    def __init__(self, bus: EventBus, failure_threshold=5):
        self._threshold = failure_threshold
        self._failures = 0
        bus.subscribe(self._on_event)

    def _on_event(self, event: ResilienceEvent):
        if event.granularity != "operation":   # <-- granularity filter is explicit
            return
        if event.outcome == "failure":
            self._failures += 1
```

**What was previously impossible — now trivial:**
Adding a rate limiter, bulkhead, or timeout observer requires zero modification to existing policies. Each subscribes independently to the events it cares about, at the granularity it understands.

---

## The New Impossibility and the Conservation Law

**New impossibility:** Synchronous, deterministic retry timing. In the event-sourced design, retry scheduling becomes reactive — a subscriber decides whether to retry, but execution sequencing now depends on subscriber order and bus implementation. You cannot guarantee sub-millisecond retry determinism without re-introducing explicit imperative ordering, which collapses back to the composed design.

**Conservation Law: Decision Authority is conserved.**

Every resilience system must assign decision authority — *who decides when to retry, when to open the circuit* — to exactly one locus of control per decision type. You cannot eliminate this authority; you can only relocate it:

| Design | Authority Location |
|---|---|
| Original | Implicit in call stack depth |
| Composed | Explicit in lambda nesting order |
| Event-sourced | Distributed across subscriber registrations |
| (Hypothetical) Type-state | Encoded in the type system itself |

The total decision authority is conserved. Moving it from implicit to explicit, or from central to distributed, does not reduce it — it changes *where you must reason about it*. Each move trades one kind of reasoning cost for another.

---

## Prediction: What a Third Design Reveals

A **type-state design** — where `CircuitBreaker<Closed>`, `CircuitBreaker<Open>`, `CircuitBreaker<HalfOpen>` are distinct types, and state transitions return new types at compile time — would force explicit enumeration of every composite state.

It would reveal: **the composite state space has always been a product.**

```
retry_attempt ∈ {0, 1, 2, exhausted}  ×  cb_state ∈ {CLOSED, OPEN, HALF_OPEN}
= 12 composite states
```

The original code handles most of these implicitly or incorrectly (e.g., retry attempt 0 in HALF_OPEN state vs. retry attempt 2 in HALF_OPEN state are treated identically). The type-state design makes all 12 states *impossible to ignore* — you must write a handler for each transition.

**The deeper revelation:** the type-state design would show that `CircuitOpenError` thrown from inside `RetryPolicy` is not actually an exception — it is a *state transition signal* masquerading as an error. The `retryable` predicate that filters it out is a workaround for the fact that exceptions conflate two distinct concepts: *errors* (something went wrong with the operation) and *signals* (the policy machinery is communicating a state change). All three designs live downstream of this conflation. The third design makes it structurally impossible to confuse them.
