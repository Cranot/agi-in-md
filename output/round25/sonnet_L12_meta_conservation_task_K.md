# Structural Diagnosis: Retry + Circuit Breaker

---

## I. The Falsifiable Claim

**Claim**: The circuit breaker's semantic integrity is destroyed by fusing the retry mechanism inside its execution path. `failure_threshold` measures retry-exhausted call aggregates, not individual service failure events. To trip the breaker, the system makes `failure_threshold × max_retries` = 15 actual service calls — not 5. This makes every threshold value impossible to reason about correctly.

*This is falsifiable*: instrument `fn` with a call counter. Tripping the breaker requires 15 calls, not 5.

---

## II. Three Experts Debate

**Defender** sharpens the claim: It's worse than count ambiguity. The exponential backoff means each failing `execute()` call takes up to 7 seconds (1 + 2 + 4 seconds of sleep). Five failed calls consume ~35 seconds — longer than `reset_timeout=30`. The breaker opens directly into an almost-immediate HALF_OPEN transition, defeating its entire purpose as a cooling mechanism. The retry backoff and the reset timeout are in an undocumented race condition.

**Attacker** rejects the framing: Count ambiguity is a configuration problem — set `max_retries=1` and it disappears. The *actual* deep problem is that the breaker uses a cumulative count with no decay. A service that fails 4 times over 3 hours and then recovers completely still sits at `_failure_count=4`. One transient failure trips it permanently. More critically, `_on_success` in CLOSED state resets `_failure_count` to 0 on *any success* — making the threshold mean "failure_threshold consecutive failures after the last success." That's neither a count nor a rate; it's an undocumented third model that no one will configure correctly.

**Prober** challenges what both take for granted: You're both assuming "failure" is a discrete, observable event. Neither of you noticed that `fn()` has no timeout. It can block indefinitely. An infinitely blocking call is registered as neither success nor failure — the circuit breaker simply hangs. Both arguments assume the circuit breaker *receives* a failure signal; this one can receive nothing. The binary success/failure model conceals that the most dangerous failure mode (total unresponsiveness) is invisible to this architecture.

---

## III. The Transformation

**Original claim**: *Retry-inside-breaker creates ambiguous failure counting.*

**Transformed claim**: **The code has no model of time as a continuous dimension. It treats service health as a scalar accumulator when it is fundamentally a rate within a temporal window. The retry fusion, the count decay problem, and the timeout blindness are all symptoms of a single root: the code has no theory of *when* events occurred relative to each other.**

**The gap**: My original claim was about semantic precision. The transformed claim is about temporal modeling. I was looking at the wrong dimension.

---

## IV. The Concealment Mechanism: Parameter Plausibility

The constructor `(failure_threshold=5, reset_timeout=30, half_open_max=3)` creates the illusion of *correctability*. These look like knobs you could tune to get correct behavior. This conceals that **no configuration of these parameters produces correct behavior**, because the underlying model (static accumulator, fused retry/breaker, no temporal decay, no timeout) cannot be made correct regardless of values. The parameters perform the function of hiding a modeling error behind an optimization surface.

---

## V. Improvement I — Deepening the Concealment

This passes code review. It fixes the legitimate complaints (count → rate, uses proper types) while perfectly concealing the structural problems:

```python
import time
import random
import collections
from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum


class CircuitState(Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


@dataclass
class RetryPolicy:
    """Separates retry behavior from circuit logic."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter_factor: float = 1.0
    retryable_exceptions: tuple = (Exception,)

    def compute_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        return delay + random.uniform(0, self.jitter_factor)


@dataclass
class WindowStats:
    """Sliding window for failure rate — prevents stale counts."""
    size: int
    _outcomes: collections.deque = field(init=False)

    def __post_init__(self):
        self._outcomes = collections.deque(maxlen=self.size)

    def record(self, success: bool) -> None:
        self._outcomes.append(success)

    @property
    def failure_rate(self) -> float:
        if not self._outcomes:
            return 0.0
        return 1.0 - (sum(self._outcomes) / len(self._outcomes))

    @property
    def is_saturated(self) -> bool:
        return len(self._outcomes) == self.size


class CircuitBreaker:
    """
    Sliding-window rate-based circuit breaker with configurable retry policy.

    Transitions:
        CLOSED    -> OPEN      when window saturates and failure_rate > threshold
        OPEN      -> HALF_OPEN after reset_timeout has elapsed
        HALF_OPEN -> CLOSED    after half_open_max consecutive probe successes
        HALF_OPEN -> OPEN      on any probe failure
    """

    def __init__(
        self,
        failure_rate_threshold: float = 0.5,
        window_size: int = 10,
        reset_timeout: float = 30.0,
        half_open_max: int = 3,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        self._state = CircuitState.CLOSED
        self._window = WindowStats(size=window_size)
        self._probe_success_count = 0
        self._failure_rate_threshold = failure_rate_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time: Optional[float] = None
        self._retry_policy = retry_policy or RetryPolicy()

    @property
    def state(self) -> CircuitState:
        return self._state

    def execute(self, fn: Callable, *args, **kwargs):
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - (self._last_failure_time or 0)
            if elapsed > self._reset_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
            else:
                raise Exception(
                    f"Circuit open — retry in {self._reset_timeout - elapsed:.1f}s "
                    f"(failure rate: {self._window.failure_rate:.1%})"
                )

        try:
            result = self._execute_with_retry(fn, *args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _execute_with_retry(self, fn: Callable, *args, **kwargs):
        policy = self._retry_policy
        last_exc = None
        for attempt in range(policy.max_retries):
            try:
                return fn(*args, **kwargs)
            except policy.retryable_exceptions as e:
                last_exc = e
                if attempt < policy.max_retries - 1:
                    time.sleep(policy.compute_delay(attempt))
        raise last_exc

    def _on_success(self):
        if self._state == CircuitState.HALF_OPEN:
            self._probe_success_count += 1
            if self._probe_success_count >= self._half_open_max:
                self._transition_to(CircuitState.CLOSED)
        else:
            self._window.record(True)

    def _on_failure(self):
        self._last_failure_time = time.time()
        if self._state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
            return
        self._window.record(False)
        if self._window.is_saturated and \
           self._window.failure_rate > self._failure_rate_threshold:
            self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        self._state = new_state
        if new_state == CircuitState.HALF_OPEN:
            self._probe_success_count = 0
        elif new_state == CircuitState.CLOSED:
            self._window = WindowStats(size=self._window.size)
```

**Why this passes review**: proper enums, dataclasses, type hints, rate-based threshold, explicit state machine transitions, informative error message, separated retry policy. It looks architecturally mature.

**Why it deepens concealment**: the `RetryPolicy` dataclass creates the *appearance* that retry and circuit concerns are separated, while the circuit breaker still owns the execution path — the structural inversion remains invisible.

---

## VI. Three Properties Only Visible From Strengthening

**1. Window fill latency**: `window_size=10` with `max_retries=3` means the breaker needs 10 `execute()` calls to produce meaningful statistics. Each failing call takes up to 7 seconds of backoff. The breaker cannot trip for 70 seconds minimum. `window_size` *looks* like it controls measurement granularity but actually controls **protection latency**. This was invisible in the original — the count-based model could trip after 5 events with no fill requirement.

**2. HALF_OPEN retries the probe**: The clean `RetryPolicy` separation makes this harder to notice, not easier. `_execute_with_retry` is called identically in HALF_OPEN and CLOSED states. The single probe request that should test service recovery silently becomes 3 requests. The sophistication of the retry policy object *deepens* the concealment of this flaw.

**3. Window reset on CLOSED transition creates false confidence**: When HALF_OPEN → CLOSED succeeds, `WindowStats` is replaced with a fresh empty window. Failure rate resets to 0.0%. The evidence that caused the circuit to trip is destroyed. The breaker begins its next CLOSED cycle without memory of the failure pattern that just occurred.

---

## VII. Diagnostic on Improvement I

**What it conceals**: The improvement hides that the circuit breaker is an **executor** rather than an **observer**. The state machine (`_transition_to`, `WindowStats`) is now clean enough that its *inputs* look wrong. The improvement makes the state machine so legible that it reveals: the thing generating its inputs (the retry executor) and the thing consuming those inputs (the health model) should not share a call stack.

**Property of original problem visible because improvement recreates it**: The original code's fused `_retry_with_backoff` looked like an implementation detail. The improvement's clean `_execute_with_retry` makes it visible as an **architectural claim** — the claim that the circuit breaker *owns* execution. That claim is wrong, and the improvement makes it impossible to ignore.

---

## VIII. Improvement II — Address the Recreated Property

Separate the circuit breaker from execution entirely. Make failure a structured observation, not an event:

```python
@dataclass
class CallOutcome:
    """Failure carries context — the circuit breaker decides how to interpret it."""
    success: bool
    attempt_number: int       # 0-indexed; which retry within the call
    total_attempts: int       # how many retries were made total
    latency_ms: float
    error_type: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class CircuitBreakerPolicy:
    """
    Pure observer and state machine. Does not execute anything.
    'count_each_attempt' makes the semantic boundary an explicit parameter.
    """

    def __init__(
        self,
        failure_rate_threshold: float = 0.5,
        window_size: int = 10,
        reset_timeout: float = 30.0,
        half_open_max: int = 3,
        count_each_attempt: bool = False,
    ):
        self._state = CircuitState.CLOSED
        self._window: collections.deque = collections.deque(maxlen=window_size)
        self._probe_successes = 0
        self._last_failure_time: Optional[float] = None
        self._failure_rate_threshold = failure_rate_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._count_each_attempt = count_each_attempt

    def observe(self, outcome: CallOutcome) -> None:
        """Record outcome. Policy decides what granularity to count."""
        is_final = outcome.attempt_number == outcome.total_attempts - 1
        if self._count_each_attempt or is_final:
            self._record(outcome.success, outcome.timestamp)

    def should_allow(self) -> bool:
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - (self._last_failure_time or 0)
            if elapsed > self._reset_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
            else:
                return False
        return True

    def _record(self, success: bool, timestamp: float) -> None:
        if not success:
            self._last_failure_time = timestamp

        if self._state == CircuitState.HALF_OPEN:
            if success:
                self._probe_successes += 1
                if self._probe_successes >= self._half_open_max:
                    self._transition_to(CircuitState.CLOSED)
            else:
                self._transition_to(CircuitState.OPEN)
            return

        self._window.append(success)
        if len(self._window) == self._window.maxlen:
            rate = 1 - sum(self._window) / len(self._window)
            if rate > self._failure_rate_threshold:
                self._transition_to(CircuitState.OPEN)

    def _transition_to(self, state: CircuitState) -> None:
        self._state = state
        if state == CircuitState.HALF_OPEN:
            self._probe_successes = 0


class RetryExecutor:
    """Pure executor. Knows nothing about circuit state."""

    def execute(
        self,
        fn: Callable,
        policy: RetryPolicy,
        observer: Callable[[CallOutcome], None],
        *args,
        **kwargs,
    ):
        last_exc = None
        for attempt in range(policy.max_retries):
            t0 = time.time()
            try:
                result = fn(*args, **kwargs)
                observer(CallOutcome(
                    success=True,
                    attempt_number=attempt,
                    total_attempts=attempt + 1,
                    latency_ms=(time.time() - t0) * 1000,
                ))
                return result
            except policy.retryable_exceptions as e:
                last_exc = e
                observer(CallOutcome(
                    success=False,
                    attempt_number=attempt,
                    total_attempts=policy.max_retries,
                    latency_ms=(time.time() - t0) * 1000,
                    error_type=type(e).__name__,
                ))
                if attempt < policy.max_retries - 1:
                    time.sleep(policy.compute_delay(attempt))
        raise last_exc


class ProtectedCaller:
    """Explicit composition point. The retry/circuit interaction is now visible."""

    def __init__(self, breaker: CircuitBreakerPolicy, retry_policy: RetryPolicy):
        self._breaker = breaker
        self._executor = RetryExecutor()
        self._retry_policy = retry_policy

    def call(self, fn: Callable, *args, **kwargs):
        if not self._breaker.should_allow():
            raise Exception("Circuit is open")
        return self._executor.execute(
            fn, self._retry_policy, self._breaker.observe, *args, **kwargs
        )
```

---

## IX. Diagnostic on Improvement II

**What it conceals**: The `count_each_attempt: bool` parameter exposes the problem with perfect clarity — *and then hides that it is unanswerable*. 

- `count_each_attempt=False`: a service that always fails on attempt 1 and succeeds on attempt 2 appears perfectly healthy.
- `count_each_attempt=True`: a service that reliably recovers on the first retry shows a 67% failure rate.

Neither is correct in general. The parameter makes the choice visible but not answerable. It performs the function of making an unanswerable question look like a configuration decision.

**Property of original problem visible because improvement recreates it**: The rich `CallOutcome` struct — carrying `attempt_number`, `total_attempts`, `latency_ms`, `error_type` — reveals what was always true: **the circuit breaker needs a theory of failure, not just observations of it**. The original code had no theory; it counted blindly. The improvement, by providing everything a theory would need, makes the theory's absence structural and undeniable.

---

## X. The Structural Invariant

In any retry + circuit breaker composition, **a boundary must be placed somewhere between "a single service call attempt" and "a complete request."** The circuit breaker's health model is defined relative to this boundary. Every structural improvement — separating classes, adding parameters, enriching observation types — moves the boundary but cannot eliminate it. The boundary's location determines what "failure" means; no code structure makes the location correct by construction.

*This is not fixable by refactoring. It is a property of the problem space.*

The invariant persists because it is the consequence of two incompatible requirements:
- Retries require granular knowledge (individual attempts fail)
- Circuit breakers require aggregate knowledge (overall service health is degraded)

These are incommensurable without a theory that maps one to the other. Every implementation embeds such a theory — either explicitly (via `count_each_attempt`) or implicitly (by fusing retry inside the breaker). The theory cannot be made correct by code structure because correctness is determined by service failure characteristics that are external to the code.

---

## XI. Inverting the Invariant

**The inversion**: Instead of the boundary being a structural decision, make "failure" a first-class value that carries its own semantic weight. The caller — who understands the service domain — declares how each failure should be counted:

```python
@dataclass
class FailureSignal:
    """Caller annotates failure with its circuit-breaking significance."""
    circuit_weight: float   # 0.0 = informational, 1.0 = full circuit-breaking event
    retry_eligible: bool
    failure_class: str      # "transient" | "overload" | "timeout" | "permanent"

# The boundary is now placed by the caller, not the infrastructure:
def call_payment_service(amount):
    try:
        return payment_api.charge(amount)
    except TimeoutError:
        raise WeightedFailure(FailureSignal(
            circuit_weight=0.3,    # timeouts are soft signals
            retry_eligible=True,
            failure_class="timeout"
        ))
    except ServiceOverloadError:
        raise WeightedFailure(FailureSignal(
            circuit_weight=0.8,    # overload strongly predicts continued failure
            retry_eligible=False,  # retrying under overload makes it worse
            failure_class="overload"
        ))
```

The impossible property (correct boundary placement) is now trivially satisfiable: **the caller places it**, and the circuit breaker accumulates weighted signals rather than counting binary events.

**The new impossibility**: Correct `circuit_weight` values can only be derived from production traffic analysis — data that doesn't exist when writing the code. More critically: the caller must model the circuit breaker's internal dynamics to assign correct weights, but the purpose of the circuit breaker is to abstract those dynamics from the caller. **The inversion requires the caller to have a model of the circuit breaker's behavior in order to configure the circuit breaker's behavior.** The system becomes self-referential: correct configuration requires knowing the effect of the configuration.

---

## XII. The Conservation Law

**Failure Semantics are Conserved.**

In any retry + circuit breaker system, the semantic work required to correctly interpret "what counts as a circuit-breaking failure" is constant. Structural improvements redistribute this work between:

| Improvement | Where semantic work lives |
|-------------|--------------------------|
| Original code | Implicit in `failure_threshold` value chosen by operator |
| Improvement I | `failure_rate_threshold` + `window_size` configuration |
| Improvement II | `count_each_attempt` parameter |
| Inverted design | `circuit_weight` values at every call site |

Formally: `W(implementation) + W(configuration) + W(call_site) + W(documentation) = K`

Where K is the irreducible complexity of the target service's failure domain. Making the code more architecturally sophisticated moves semantic work to the call site. Making it simpler moves it to parameter tuning. The total semantic work is conserved; it cannot be eliminated by code structure.

---

## XIII. Applying the Diagnostic to the Conservation Law

**What the law conceals**: The law frames K as a fixed quantity to be correctly allocated. This conceals that **K is not known in advance and changes continuously** — with traffic patterns, upstream dependencies, deployment changes, and time of day. The conservation law assumes a stable failure domain. In reality, the failure domain is dynamic. The law conceals that the problem is not "how to correctly interpret failures" but "how to act under irreducible, non-stationary uncertainty about what failure means."

**The structural invariant of the conservation law**: Every formulation of the law — every refinement of "semantic work," every improvement in boundary placement — presupposes that a "true service health state" exists and the circuit breaker is an imperfect observer of it. This is the invariant: **the observer/observed dualism**. The law always casts this as "circuit breaker observing a service that has a real health state." This framing is not wrong; it is *incomplete in a specific way*.

**Inverting the invariant of the conservation law**: Don't treat the circuit breaker as an observer of service health. Recognize that **the circuit breaker is a constitutive actor in service health**:
- When the breaker opens and stops sending load, the service may genuinely recover — because the breaker's action changed the service's state
- When HALF_OPEN probe traffic arrives, the service sees a sudden load change that may itself cause failure
- Retry traffic during degradation may amplify the degradation the breaker is trying to detect

The breaker doesn't observe service health. The breaker's behavior *is part of* what determines service health. Observer and observed are coupled.

---

## XIV. The Meta-Law

**The Observer-Constitutive Reflexivity Principle**:

Every fault-tolerance mechanism is simultaneously an observer of service health and a constitutive actor in service health. The semantic work of interpreting failures cannot be correctly allocated anywhere in the system because the system's own behavior is part of what determines what counts as a failure. A circuit breaker that retries aggressively creates different service failure patterns than one that fails fast. A breaker with a short `reset_timeout` creates different recovery dynamics than one with a long timeout. **The thing doing the measuring changes the thing being measured.**

This makes static code configuration *structurally insufficient* — not because the configuration is difficult to get right, but because "right" is not a static property. The correct configuration at low traffic is wrong at high traffic. The correct configuration for transient failures is wrong for cascade failures. The configuration space has no stable optimum; it has attractors that shift as the system's own behavior shifts the failure domain.

---

## XV. What the Meta-Law Predicts That No Code Analysis Could Reveal

The meta-law predicts a characteristic operational pathology that is invisible in code review and testing: **configuration brittleness at phase boundaries**.

The system will work acceptably across a wide range of configurations — `failure_threshold` of 3 or 7, `reset_timeout` of 20 or 60. Teams will tune these values and find configurations that seem stable. Then, when service load or failure rate crosses certain thresholds (phase boundaries in the dynamical system sense), the retry backoff timing and circuit-breaking behavior will enter positive feedback with the service's actual failure pattern. Small configuration changes will produce wildly different outcomes. The system will oscillate: the breaker opens, load drops, service recovers, breaker closes, load resumes, service degrades, breaker opens.

**The meta-law predicts this oscillation is not a tuning problem.** It is the structural consequence of placing a statically configured system at the boundary of two coupled dynamical processes (retry amplification and service overload recovery). Teams running this code in production will cycle through configurations indefinitely, each of which works until traffic patterns shift, and will attribute the instability to "needing better parameters" — never recognizing that the need for perpetual retuning *is itself the invariant symptom*. The circuit breaker is not failing to converge on a correct configuration. There is no correct static configuration. The gap between what the code's parameters promise (stable protection thresholds) and what the meta-law reveals (an irreducibly adaptive control problem) is the deepest thing this code hides.
