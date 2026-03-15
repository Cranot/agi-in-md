# Structural Diagnosis: The Retry-Circuit Breaker Fusion

---

## I. The Claim

**Falsifiable claim:** The circuit breaker's failure counter measures *retry-exhausted operations*, not *individual call attempts*. With `failure_threshold=5` and `max_retries=3`, the circuit opens after 15 actual failed calls — 3× later than the designer intends — while blocking for up to `(1 + 2 + jitter) × 5 ≈ 15+ seconds` of accumulated sleep before even attempting to protect the downstream service.

This is falsifiable: set `failure_threshold=5, max_retries=3`, make a downstream always-fail service, measure actual failed calls before circuit opens. It will be ~15, not 5.

---

## II. The Tribunal

### Expert A — Defends the claim

The claim is correct and understates the severity. The retry consumes the circuit breaker's protective window. By the time the circuit opens, the caller has already absorbed all the backoff latency *and* subjected the downstream service to 15 hammer blows. The circuit breaker is supposed to reduce load on a degrading service; the embedded retry is increasing it. The two mechanisms are causally opposed: one amplifies call volume under failure, the other suppresses it. Fusing them means the gas pedal is wired to the brake.

### Expert B — Attacks the claim

The "3× later" framing is a calibration complaint, not a structural one. Set `failure_threshold=2` and the circuit opens at the same 5-6 actual failures. The real problem is the **missing state re-check between retry attempts**. During the retry loop, another thread can open the circuit, but the current execution proceeds anyway — violating the circuit breaker's core isolation guarantee. This is not a multiplier problem; it's a race condition. The claim mistakes a tuning issue for an architectural one.

### Expert C — Probes what both take for granted

Both arguments assume the circuit breaker's goal is to *count* failures correctly. But why count? To *detect degradation*. Both of you are taking for granted that **failures are independent events**. If the downstream is failing due to overload, retry attempts are not independent — they *contribute to* the degradation the circuit breaker is trying to detect. The retry isn't just slow to trigger the circuit; it is generating the load that degrades the service further, which generates more failures, which triggers more retries. You're not debating a threshold; you're debating a feedback loop. Neither of you has addressed that.

### The Transformation

My original claim was about **measurement granularity** (circuit breaker sees 3× fewer events). Expert B adds a **concurrency dimension** (state is stale between retries). Expert C reveals the **causal structure**: retry and circuit breaker are not just miscounted — they are causally opposed forces whose combination creates a positive feedback loop during degradation.

**Transformed claim:** *The deepest structural problem is a causal inversion: retry increases load on a failing service, circuit breaker is designed to decrease it; embedding retry inside circuit breaker's `execute` creates a mechanism that actively worsens the degradation it is designed to detect, while simultaneously hiding that worsening from itself.*

---

## III. The Concealment Mechanism

**Correct vocabulary on incorrect semantics.**

The code has all the right words: `CLOSED`, `OPEN`, `HALF_OPEN`, exponential backoff with jitter, proper state transitions, `_on_success`/`_on_failure` — every term is correct. The states are named correctly. The backoff is textbook. This surface correctness makes the code *look like* it is implementing two well-understood patterns.

The mechanism works by making `_retry_with_backoff` a *private method* — syntactically subordinate to the circuit breaker, semantically prior to it. It looks like an implementation detail. The name `execute` implies "do the thing with protection"; internally, "protection" appears to subsume "retry," when actually retry is undermining protection.

Applied: `_on_failure` is called after the retry loop, so it *looks like* correct failure accounting. But it is measuring a different failure than the one `failure_threshold` was designed to detect.

---

## IV. Improvement 1: Legitimate-Looking, Deepens Concealment

```python
import time
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, List

class CircuitState(Enum):
    CLOSED   = "closed"
    OPEN     = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreakerConfig:
    """Unified configuration for circuit breaker and retry behaviour."""
    failure_threshold: int   = 5
    reset_timeout:     float = 30.0
    half_open_max:     int   = 3
    # Retry parameters — part of the circuit breaker's execution policy
    max_retries:  int   = 3
    base_delay:   float = 1.0
    max_delay:    float = 30.0

@dataclass
class ExecutionMetrics:
    total_calls:    int = 0
    total_failures: int = 0   # retry-exhausted failures (circuit breaker events)
    total_retries:  int = 0   # individual retry attempts
    circuit_opens:  int = 0

class CircuitOpenError(Exception):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Circuit open; retry after {retry_after:.1f}s")

class CircuitBreaker:
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self._config  = config or CircuitBreakerConfig()
        self._state   = CircuitState.CLOSED
        self._failure_count  = 0
        self._success_count  = 0
        self._last_failure_time: Optional[float] = None
        self._metrics = ExecutionMetrics()

    # ── Public interface ─────────────────────────────────────────────────────

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def metrics(self) -> ExecutionMetrics:
        return self._metrics

    def execute(self, fn: Callable, *args, **kwargs):
        self._metrics.total_calls += 1
        self._maybe_transition_to_half_open()

        if self._state == CircuitState.OPEN:
            raise CircuitOpenError(self._seconds_until_reset())

        try:
            result = self._execute_with_retry(fn, *args, **kwargs)
            self._on_success()
            return result
        except CircuitOpenError:
            raise
        except Exception:
            self._on_failure()
            raise

    # ── Internal state machine ───────────────────────────────────────────────

    def _maybe_transition_to_half_open(self) -> None:
        if (self._state == CircuitState.OPEN
                and self._last_failure_time is not None
                and time.time() - self._last_failure_time > self._config.reset_timeout):
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0

    def _execute_with_retry(self, fn: Callable, *args, **kwargs):
        last_exc: Optional[Exception] = None
        for attempt in range(self._config.max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_exc = e
                if attempt < self._config.max_retries - 1:
                    self._metrics.total_retries += 1
                    delay = min(
                        self._config.base_delay * (2 ** attempt) + random.uniform(0, 1),
                        self._config.max_delay,
                    )
                    time.sleep(delay)
        raise last_exc  # type: ignore[misc]

    def _on_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.half_open_max:
                self._state   = CircuitState.CLOSED
                self._failure_count = 0
        else:
            self._failure_count = 0

    def _on_failure(self) -> None:
        self._failure_count    += 1
        self._last_failure_time = time.time()
        self._metrics.total_failures += 1
        if self._failure_count >= self._config.failure_threshold:
            self._state = CircuitState.OPEN
            self._metrics.circuit_opens += 1

    def _seconds_until_reset(self) -> float:
        if self._last_failure_time is None:
            return 0.0
        return max(0.0, self._config.reset_timeout
                        - (time.time() - self._last_failure_time))
```

**Why this passes code review:** Enum states, typed config dataclass, proper custom exception, observability metrics, extracted `_maybe_transition_to_half_open`, `max_delay` cap, `CircuitOpenError` not swallowed by the broad `except Exception`. Every individual change is an improvement.

**Why it deepens concealment:**

1. **`CircuitBreakerConfig` legitimises the coupling as API.** `max_retries` now lives beside `failure_threshold` in the same config class. What was a suspicious parameter buried in a private method is now a first-class circuit breaker design parameter. Separating them is now a breaking API change.

2. **`total_retries` in `ExecutionMetrics` looks like observability.** It creates the false impression that individual retry attempts are visible to the circuit breaker. They are counted — but not acted upon. The metric exists without influence.

3. **`CircuitOpenError` re-raises cleanly** from within the retry loop — which hides the fact that circuit state is never checked *between* retry attempts. The error handling looks correct because it is correct for the wrong architecture.

---

## V. Three Properties Visible Only from Strengthening

**Property 1 — The metrics expose the two-denominator problem.**
`total_failures` and `total_retries` have different denominators (operations vs. attempts). The ratio `total_retries / total_failures` ≈ `max_retries - 1`, a constant determined by config — not a runtime health signal. The metrics look diagnostic but measure a tautology. This was invisible before because there were no metrics.

**Property 2 — The config namespace shows the conceptual containment.**
In a correct design, `RetryConfig` and `CircuitBreakerConfig` are separate types. Their merger into one class makes the containment relationship legible *as design*: retry is *inside* the circuit breaker's conceptual boundary. Before, this was an accident of method placement; now it is a stated architectural position.

**Property 3 — Type hints reveal the wrong abstraction boundary.**
`_execute_with_retry(self, fn: Callable, *args, **kwargs)` accepts a `Callable` and returns the result directly. A proper retry abstraction transforms a `Callable` *into* a `Callable` — it is a decorator, not a caller. The type signature `(Callable) -> result` makes visible that retry is being *invoked* rather than *composed*, forcing the circuit breaker to be the composition point.

---

## VI. Improvement 2: Addressing the Recreated Property

The recreated property: **retry and circuit breaker must be composed in a specific order, but nothing enforces it.**

```python
import time
import random
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, TypeVar, Iterator
from contextlib import contextmanager

T = TypeVar("T")

# ── Retry as a first-class transformer ──────────────────────────────────────

@dataclass
class RetryConfig:
    max_retries: int   = 3
    base_delay:  float = 1.0
    max_delay:   float = 30.0

class RetryPolicy:
    def __init__(self, config: Optional[RetryConfig] = None):
        self._config = config or RetryConfig()

    def execute(self, fn: Callable[[], T]) -> T:
        """
        Wrap a zero-argument callable, retrying on failure.
        Caller composes the callable; RetryPolicy does not know
        what is being called.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self._config.max_retries):
            try:
                return fn()
            except Exception as e:
                last_exc = e
                if attempt < self._config.max_retries - 1:
                    delay = min(
                        self._config.base_delay * (2 ** attempt) + random.uniform(0, 1),
                        self._config.max_delay,
                    )
                    time.sleep(delay)
        raise last_exc  # type: ignore[misc]

# ── Circuit breaker as a pure guard ─────────────────────────────────────────

class CircuitState(Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int   = 5
    reset_timeout:     float = 30.0
    half_open_max:     int   = 3

class CircuitOpenError(Exception):
    pass

class CircuitBreaker:
    """
    Pure circuit breaker: no retry logic.
    Each call to execute() represents one attempt — never more.
    """
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self._config        = config or CircuitBreakerConfig()
        self._state         = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        return self._state

    def execute(self, fn: Callable[[], T]) -> T:
        self._maybe_transition_to_half_open()

        if self._state == CircuitState.OPEN:
            raise CircuitOpenError("Circuit is open")

        try:
            result = fn()
            self._on_success()
            return result
        except CircuitOpenError:
            raise
        except Exception:
            self._on_failure()
            raise

    def _maybe_transition_to_half_open(self) -> None:
        if (self._state == CircuitState.OPEN
                and self._last_failure_time is not None
                and time.time() - self._last_failure_time > self._config.reset_timeout):
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0

    def _on_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.half_open_max:
                self._state         = CircuitState.CLOSED
                self._failure_count = 0
        else:
            self._failure_count = 0

    def _on_failure(self) -> None:
        self._failure_count    += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._config.failure_threshold:
            self._state = CircuitState.OPEN

# ── Composition — order is now visible and enforced ──────────────────────────

def protected_call(
    fn: Callable,
    *args,
    circuit_breaker: CircuitBreaker,
    retry_policy: RetryPolicy,
    **kwargs,
) -> object:
    """
    Correct composition order:
        retry (outer) → circuit_breaker (inner) → fn

    Each retry attempt goes through the circuit breaker check independently.
    The circuit breaker sees every attempt; it will open mid-retry if warranted.
    """
    return retry_policy.execute(
        lambda: circuit_breaker.execute(
            lambda: fn(*args, **kwargs)
        )
    )
```

**What this addresses:** Retry now wraps circuit breaker, not the reverse. Each retry attempt independently checks circuit state. If the circuit opens on attempt 2, attempt 3 raises `CircuitOpenError` immediately — and `RetryPolicy` propagates it (it only retries generic `Exception`; we can make `CircuitOpenError` not a subclass of the retried exceptions).

---

## VII. Diagnostic Applied to Improvement 2: What Does It Conceal?

**What Improvement 2 conceals:**

`protected_call` enforces the correct composition order — but it reveals a new problem: if `CircuitOpenError` inherits from `Exception`, `RetryPolicy` will *retry on circuit open*, which is precisely the pathological behavior we are trying to eliminate. The fix is to make `CircuitOpenError` not caught by `RetryPolicy`'s broad `except Exception`. This requires `RetryPolicy` to either:

- Know about `CircuitOpenError` (re-introducing coupling), or
- Accept a predicate `should_retry: Callable[[Exception], bool]` (which is the right answer, but reveals the coupling is now in the predicate, not the class hierarchy)

**What property of the original problem is visible only because the improvement recreates it:**

In the original, the retry loop is inside `execute` — it can't accidentally retry a circuit-open event because the circuit check is *before* the retry loop. Improvement 2 exposes the retry to circuit-open errors for the first time, forcing the question: *which exceptions should trigger retry?* This question was invisible in the original precisely because the coupling prevented it from being asked.

The original problem — retry and circuit breaker share failure semantics — is recreated in Improvement 2 as: *they must share exception type knowledge to compose correctly.*

---

## VIII. The Structural Invariant

**The invariant that persists through every improvement:**

> *The system must maintain a correspondence between the failure events the circuit breaker observes and the failure events that actually indicate downstream degradation. Any layer that transforms failures (absorbing them via retry, filtering them via exception type, or amplifying them by exposing individual attempts) changes what the circuit breaker measures without changing what it is calibrated to detect.*

This invariant is not an implementation detail. It is a property of **the problem space**: circuit breakers are calibrated to failure rates of a specific granularity. Retry mechanisms change failure granularity. Their combination always requires *choosing* a granularity — and that choice cannot be hidden, only moved.

Tracing the invariant:
- **Original code:** Retry absorbs failures → circuit sees 1/3 of actual failures → opens 3× late
- **Improvement 1:** Adds metrics counting both granularities → invariant visible as two-denominator problem
- **Improvement 2:** Separates classes → invariant visible as exception type coupling, composition order constraint

---

## IX. The Inversion

**Making the impossible trivially satisfiable:**

Instead of making the circuit breaker count discrete failure events (which requires choosing a granularity), make it measure **failure rate** over a sliding window of individual attempts — and have every retry attempt report to it directly:

```python
from collections import deque

class RateCircuitBreaker:
    """
    Circuit breaker based on failure rate over a sliding window of attempts.
    Every attempt — including each retry — is an independent observation.
    Granularity problem dissolves: there is no 'correct' event boundary.
    """
    def __init__(self, failure_rate_threshold=0.5, window_size=20, reset_timeout=30.0):
        self._window:    deque[bool] = deque(maxlen=window_size)
        self._threshold  = failure_rate_threshold
        self._window_size = window_size
        self._reset_timeout = reset_timeout
        self._opened_at: Optional[float] = None

    def record_attempt(self, success: bool) -> None:
        """Called by retry loop for every individual attempt."""
        self._window.append(success)

    @property
    def is_open(self) -> bool:
        if self._opened_at is not None:
            if time.time() - self._opened_at > self._reset_timeout:
                self._opened_at = None
                self._window.clear()
            else:
                return True
        if len(self._window) < self._window_size:
            return False
        failure_rate = self._window.count(False) / len(self._window)
        if failure_rate > self._threshold:
            self._opened_at = time.time()
            return True
        return False

    def guard(self) -> None:
        if self.is_open:
            raise CircuitOpenError("Circuit open (rate threshold exceeded)")
```

Now retry calls `record_attempt(False)` on each failed attempt and `guard()` before each attempt. The circuit breaker observes every attempt. The granularity problem is solved.

**The new impossibility:**

With retry count = N per operation and M concurrent callers, the window fills with `N × M` attempt-level observations per operation-level "event." The circuit breaker is now **amplified** by the retry count. One genuinely failing operation with `max_retries=3` contributes 3 failures to the window — *tripling* the circuit's sensitivity. Under concurrent load (e.g., 10 threads each retrying 3× on a briefly-slow service), the window shows 30 failures instead of 10, and the circuit opens on *transient degradation* that a per-operation counter would correctly absorb.

Original impossibility: **Circuit opens too late** (retry absorbs failures, circuit under-sensitive)
Inverted impossibility: **Circuit opens too early** (retry amplifies failures, circuit over-sensitive)

---

## X. The Conservation Law

**Name it:**

> **The Conservation of Failure Observability**
>
> *In any system combining retry and circuit breaker, there is a fixed total "weight" assigned to each failed call. If retry absorbs that weight before the circuit breaker observes it, the circuit is under-sensitive: it opens N× too late, where N = max_retries. If retry exposes that weight to the circuit breaker at attempt granularity, the circuit is over-sensitive: it opens N× too early. The product (circuit sensitivity) × (retry absorption) is constant. You cannot increase one without decreasing the other.*

Formally: let `S` = number of actual failed calls to trigger circuit opening. In the original: `S = failure_threshold × max_retries`. After inversion: `S = failure_threshold / max_retries` (approximately). The designer intends `S = failure_threshold`. No implementation satisfies this without coupling the two mechanisms.

**The escape condition — and why it fails:**

The only escape is to use **two separate failure signals**: one for attempt-level (retries) and one for operation-level (circuit breaker), with independent calibration. This requires the retry policy to distinguish *transient* failures (retry-eligible) from *sustained* failures (circuit-eligible) — which requires the retry to have a model of downstream health, which is the circuit breaker's job. The coupling has not been eliminated; it has been internalized into the failure classification predicate.

**The finding:**

The retry mechanism and circuit breaker impose incompatible granularity requirements on failure events. Retry needs fine-grained failures (per attempt) to decide whether to continue. Circuit breaker needs coarse-grained failures (per operation) to detect systemic degradation without false positives. These two granularities cannot coexist without a failure taxonomy that distinguishes transient from sustained failures — which requires the exact domain knowledge the circuit breaker is supposed to *derive* from observed failure rates. The coupling is not an implementation defect. It is a logical dependency: you cannot compose retry and circuit breaker without deciding which one's failure model takes precedence, and that decision encodes domain knowledge the code currently hides in the integer constants `max_retries=3` and `failure_threshold=5`.
