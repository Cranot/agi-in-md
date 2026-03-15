# Structure First: Double Recursion Analysis

## The Initial Claim

**Falsifiable claim**: The deepest structural problem is that `_retry_with_backoff` nested inside `CircuitBreaker.execute` creates a failure aggregation collapse — all retry attempts (up to 3 individual service calls) register as exactly one circuit breaker failure event. With `failure_threshold=5`, the circuit won't open until 15 actual service failures occur, but the system *believes* it's measuring 5. The `failure_threshold` parameter is semantically unmeasurable because it counts "exhausted retry sequences," a quantity that is a function of both service failure rate AND retry configuration simultaneously.

**Falsifiable test**: Change `max_retries` from 3 to 1 with identical service failure rates — the circuit opens 3× faster with no change to service behavior. The threshold doesn't measure what it claims to measure.

---

## Three Experts

**Expert 1 (Defending)**: The failure aggregation collapse is real and measurable. When `_retry_with_backoff` raises, `execute` calls `_on_failure()` exactly once. The circuit breaker is blind to the 14 failures that occurred before it trips. This isn't just a counting error — it means the circuit breaker's protection window is systematically late. By the time it opens, the service has already absorbed its maximum retry load multiplied by threshold. The HALF_OPEN state's `_success_count` check then compounds this: 3 successful calls after 15 failures is not a meaningful health signal.

**Expert 2 (Attacking)**: The retry-inside-CB is a known design choice, not the deepest bug. Some systems intentionally want retries transparent to the breaker. The *actual* deepest problem is that `_state`, `_failure_count`, `_success_count`, and `_last_failure_time` are modified without any synchronization. Under concurrent load:

```python
# Thread A and Thread B both evaluate this simultaneously:
if self._state == self.OPEN:
    if time.time() - self._last_failure_time > self._reset_timeout:
        self._state = self.HALF_OPEN  # both threads write this
        self._success_count = 0       # race on reset
```

Two threads can simultaneously transition to HALF_OPEN, both running "probe" calls, both independently deciding to CLOSE the circuit. The failure granularity argument is moot if the state machine is corrupt.

**Expert 3 (Probing assumptions)**: Both experts are taking for granted that the circuit breaker has a coherent *protection target*. Expert 1 assumes it's protecting the caller from cascading failures. Expert 2 assumes it's protecting the system from concurrent overload. But the code conflates two orthogonal concerns: protecting the **calling system** from waiting on a dead service, and protecting the **called service** from overload. The retry mechanism inside the CB actively undermines *both*: it increases load on the failing service during the exact window when the CB should be reducing it, while hiding that load from the CB's counting mechanism. Neither expert questioned whether "protection" has a definition here.

---

## The Claim Transforms

**Original claim**: Retry-inside-CB creates failure granularity mismatch at the threshold.

**Transformed claim**: The system has no coherent definition of what a "failure" means at the service boundary. The retry mechanism and circuit breaker each impose incompatible failure semantics — retry treats failure as "this attempt failed, try again"; circuit-break treats failure as "this service is failing, stop trying." These are observations of the same event that cannot both be true simultaneously. Any implementation must choose which semantics dominate, and that choice is currently made by accident (nesting order) rather than design.

**The gap**: Original focused on *counting* (threshold accuracy). Transformed focuses on *observability* (what each component can see). The counting problem is a symptom; the observability asymmetry is the cause.

---

## The Concealment Mechanism

**Abstraction layering that creates information horizons.**

`_retry_with_backoff` reports only its terminal result to `execute`. All intermediate states — attempt count, per-attempt latency, the failure pattern (immediate vs. timeout) — vanish below the circuit breaker's observation horizon. The CB then conceals its own state transitions from callers, who see only `Exception("Circuit is open")` with no state history. Each abstraction layer looks like clean encapsulation. Each is actually an information black hole.

The mechanism works because private methods look like implementation details. `_retry_with_backoff` *is* an implementation detail — that is exactly why it successfully hides four failure events from the system that needs to count them.

---

## Improvement 1: Extract `RetryPolicy` (Deepens Concealment)

This is the "obvious" refactoring. It passes code review. It makes things worse.

```python
import time, random, threading
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter: bool = True


class RetryPolicy:
    """Configurable retry with exponential backoff and jitter cap."""

    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()

    def execute(self, fn: Callable, *args, **kwargs):
        cfg = self.config
        for attempt in range(cfg.max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception:
                if attempt == cfg.max_retries - 1:
                    raise
                jitter = random.uniform(0, 1) if cfg.jitter else 0
                delay = min(
                    cfg.base_delay * (2 ** attempt) + jitter,
                    cfg.max_delay
                )
                time.sleep(delay)


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 30,
        half_open_max: int = 3,
        retry_config: RetryConfig = None,
    ):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time: Optional[float] = None
        self._retry = RetryPolicy(retry_config)

    def execute(self, fn: Callable, *args, **kwargs):
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
            else:
                raise Exception("Circuit is open")

        try:
            result = self._retry.execute(fn, *args, **kwargs)
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
```

This is legitimate-looking for specific, verifiable reasons: `RetryConfig` is a proper value object, `max_delay` prevents exponential runaway, the jitter flag is a real operational concern, type hints improve readability, the dataclass is testable in isolation. A code review approves this unanimously.

---

## Three Properties Visible Only Because You Tried to Strengthen It

**1. The interface boundary formalizes the information loss.**
By giving `RetryPolicy` a clean `execute(fn) -> result | raise` signature, we've created a formal API contract that has *no channel for intermediate state*. The missing return type is now visible as a design choice, not an oversight. `RetryPolicy.execute` could return `(result, List[AttemptRecord])` — it doesn't. The extraction makes the omission legible.

**2. The composition order is load-bearing but invisible.**
Extracting `RetryPolicy` immediately raises the question: who wraps whom? `CB.execute → RetryPolicy.execute → fn` (current) vs. `RetryPolicy.execute → CB.execute → fn` (alternative) are completely different systems with different failure semantics. The original code hid this by not having a composition boundary. Making it explicit reveals that the nesting order is a major semantic decision presented as a trivial implementation detail.

**3. The retry mechanism is stateless; the circuit breaker is stateful. Extraction makes this asymmetry visible.**
`RetryPolicy` has no instance state that persists between calls. `CircuitBreaker` has four mutable state variables. The original code hid this by colocating them. Separation reveals that they have fundamentally different temporal characters: retry is call-scoped, circuit-break is service-scoped. You cannot compose two things with different temporal scopes without an explicit reconciliation.

---

## Diagnostic on Improvement 1

**What Improvement 1 conceals**: The composition order problem. `CircuitBreaker` owns `RetryPolicy` as a dependency, which looks like clean inversion of control. But this ownership locks in `CB → Retry → fn` order and makes it impossible to change without modifying `CircuitBreaker`. The "clean" API boundary between them masks that they are semantically coupled: `RetryPolicy` must behave differently depending on CB state (e.g., no retries when HALF_OPEN), but it cannot observe that state.

**Property of original problem visible because Improvement 1 recreates it**: The information asymmetry is now a formal API violation. For `RetryPolicy` to be circuit-breaker-aware, it would need to accept CB state as input. For `CircuitBreaker` to be retry-aware, it needs to count attempt-level failures. Neither can get what it needs through the other's public interface. The original problem (retry hides failures from CB) is now recreated as: *the composition boundary prevents the information exchange that would solve the original problem*.

---

## Improvement 2: Shared Failure Observer (Addresses Recreated Property)

The composition boundary hides failures. The fix: create an explicit channel that crosses the boundary.

```python
import time, random, threading
from dataclasses import dataclass, field
from typing import Callable, Optional, List


@dataclass
class AttemptEvent:
    attempt_number: int
    exception: Exception
    timestamp: float
    duration_ms: float


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter: bool = True


class RetryPolicy:
    """
    Retry with exponential backoff. Emits AttemptEvents through an
    optional observer so that callers (e.g., CircuitBreaker) can react
    to individual attempt failures without the retry mechanism needing
    to know about the caller's semantics.
    """

    def __init__(
        self,
        config: RetryConfig = None,
        on_attempt_failure: Optional[Callable[[AttemptEvent], None]] = None,
    ):
        self.config = config or RetryConfig()
        self._on_attempt_failure = on_attempt_failure

    def execute(self, fn: Callable, *args, **kwargs):
        cfg = self.config
        for attempt in range(cfg.max_retries):
            start = time.time()
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                duration_ms = (time.time() - start) * 1000
                if self._on_attempt_failure:
                    self._on_attempt_failure(AttemptEvent(
                        attempt_number=attempt,
                        exception=exc,
                        timestamp=time.time(),
                        duration_ms=duration_ms,
                    ))
                if attempt == cfg.max_retries - 1:
                    raise
                jitter = random.uniform(0, 1) if cfg.jitter else 0
                delay = min(
                    cfg.base_delay * (2 ** attempt) + jitter,
                    cfg.max_delay
                )
                time.sleep(delay)


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 30,
        half_open_max: int = 3,
        retry_config: RetryConfig = None,
    ):
        self._lock = threading.RLock()
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time: Optional[float] = None
        self._attempt_failure_log: List[AttemptEvent] = []

        self._retry = RetryPolicy(
            config=retry_config,
            on_attempt_failure=self._record_attempt_failure,
        )

    def _record_attempt_failure(self, event: AttemptEvent) -> None:
        """
        Observe individual retry attempt failures.
        Updates the last_failure_time on every attempt so the circuit
        breaker's reset window reflects actual last contact, not just
        last sequence failure.
        """
        with self._lock:
            self._last_failure_time = event.timestamp
            self._attempt_failure_log.append(event)

    def execute(self, fn: Callable, *args, **kwargs):
        with self._lock:
            if self._state == self.OPEN:
                if (self._last_failure_time is not None and
                        time.time() - self._last_failure_time > self._reset_timeout):
                    self._state = self.HALF_OPEN
                    self._success_count = 0
                else:
                    raise Exception("Circuit is open")

        try:
            result = self._retry.execute(fn, *args, **kwargs)
            with self._lock:
                self._on_success()
            return result
        except Exception:
            with self._lock:
                self._on_failure()
            raise

    def _on_success(self):
        if self._state == self.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._half_open_max:
                self._state = self.CLOSED
                self._failure_count = 0
                self._attempt_failure_log.clear()
        else:
            self._failure_count = 0

    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._failure_threshold:
            self._state = self.OPEN

    @property
    def attempt_failure_log(self) -> List[AttemptEvent]:
        with self._lock:
            return list(self._attempt_failure_log)
```

This looks excellent in review: it adds thread safety via `RLock`, uses the Observer pattern correctly, exposes individual attempt failures without coupling `RetryPolicy` to `CircuitBreaker`, adds duration tracking for latency-based decisions, and the log enables debugging. All legitimate improvements.

---

## Diagnostic on Improvement 2

**What Improvement 2 conceals**:

The callback `_record_attempt_failure` updates `_last_failure_time` but **not** `_failure_count`. Meanwhile `_on_failure` increments `_failure_count`. These are now two competing failure-accounting paths with different variables, triggered in different orders, under the same lock. A complete retry sequence produces: `_record_attempt_failure` called 3× (updating `_last_failure_time` three times) then `_on_failure` called once (incrementing `_failure_count`). The circuit breaker now has split-brain failure accounting: its "how many sequences failed" counter (`_failure_count`) and its "when did something last fail" timestamp (`_last_failure_time`) are updated by different mechanisms on different schedules.

More critically: Improvement 2 conceals that **the callback is invoked while holding retry logic's implicit call stack, but acquiring `self._lock` which is also acquired in `execute`**. If `execute` holds the lock and the retry is called synchronously, the callback reenters the lock — which works with `RLock` but only by accident of implementation. The real locking semantics are undefined.

**Property of the original problem visible because Improvement 2 recreates it**:

The original problem was that retry and circuit-break had incompatible failure semantics applied to the same event. Improvement 2 recreates this exactly: the attempt callback says "this moment in time is a failure event"; `_on_failure` says "this sequence completion is a failure event." The circuit breaker now simultaneously holds both semantic models. The improvement didn't resolve the semantic incompatibility — it internalized it.

The original problem is visible because Improvement 2 reproduces it inside a single method: `_record_attempt_failure` and `_on_failure` are both called during a failed `execute`, they update different state, and there is no reconciliation between them.

---

## The Structural Invariant

> **Any system that composes retry and circuit-break must externalize the definition of "what constitutes a failure" for each mechanism, because retry and circuit-break are observations of the same event under semantically incompatible failure models — and this incompatibility cannot be resolved by any implementation.**

Every improvement recreated the same structure:

| Improvement | Form the invariant took |
|---|---|
| Original | Retry hidden inside CB; CB counts retry-sequences as failures |
| Improvement 1 | Clean API boundary that has no channel for per-attempt events |
| Improvement 2 | Two failure-accounting paths (`_record_attempt_failure` and `_on_failure`) with incompatible semantics coexisting in one object |

The invariant persists because it is not a property of the implementation. It is a property of the **problem domain**: retry says *keep trying this specific call*; circuit-break says *stop trying this service*. These directives are not merely different — they are actively opposed. Any code that executes both must choose, at every failure event, which directive applies. That choice is a domain policy decision. Code that does not make the choice explicitly will make it implicitly, through nesting order, callback timing, or counter selection — and the choice will be wrong in ways that are invisible until production.

**The correct resolution is not an implementation pattern. It is an explicit policy interface**:

```python
class FailurePolicy(Protocol):
    def should_retry(self, attempt: int, exception: Exception) -> bool: ...
    def should_open_circuit(self, failure_count: int, window: List[AttemptEvent]) -> bool: ...
    def should_close_circuit(self, success_count: int) -> bool: ...
```

The policy separates the decision from the mechanism. Retry and circuit-break become pure state machines that execute policy decisions. The incompatibility becomes a named interface whose implementations are testable, auditable, and domain-specific. What was a concealed coupling becomes an explicit contract.
