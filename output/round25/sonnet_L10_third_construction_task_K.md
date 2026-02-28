# Deep Structural Analysis: Retry + Circuit Breaker

---

## The Claim

**The deepest structural problem is a fused theory of failure.**

Retry assumes failures are *transient and individual* — each attempt is a fresh probe of an independent event. Circuit breaking assumes failures are *systemic and accumulated* — each outcome is evidence about a downstream service's health. These two assumptions are mutually exclusive as written: retry resolves failures before the circuit breaker can observe them, and the circuit breaker treats aggregated retry outcomes as atomic events. The code is not a misconfigured circuit breaker. It is two incompatible causal models running in the same loop, neither aware the other exists.

**Falsifiability test:** With `failure_threshold=5` and `max_retries=3`, a service that fails every single call requires 5 `execute()` invocations to open the circuit — but those 5 calls have already sent *15 requests* to the failing service. If the models were compatible, the circuit should open no later than call 2 (6 requests). Any benchmark that measures requests-to-open will refute or confirm this within one test run.

---

## Three Experts

**Expert A (Defender):**
The claim holds operationally. Trace the code path: `execute()` calls `_retry_with_backoff()`, which silently absorbs up to 2 failures per call before raising. `_on_failure()` fires exactly once per `execute()` call — not per attempt. The circuit breaker is blind to the interior of its own retry loop. During a failure cascade, this blindness causes the circuit breaker to open *after* the retry mechanism has already amplified load by a factor of 3.

**Expert B (Attacker):**
The claim is correct but misdirected. The deeper problem is thread safety. There are zero locks. Two threads can simultaneously evaluate `self._state == self.HALF_OPEN`, both pass the gate, and both fire requests at the recovering service. `_success_count` can be double-incremented and overtransition HALF_OPEN → CLOSED prematurely, or both threads can trip `_on_failure()` simultaneously and corrupt the state machine. The retry-inside-CB problem is a design smell you can refactor around; the race conditions are architectural failures that make the state machine's guarantees meaningless in production.

**Expert C (Prober):**
Both of you are arguing about *how the implementation fails* while taking for granted that a circuit breaker *should contain retry logic at all*. The circuit breaker pattern, as defined, is a state machine that observes outcomes and gates requests. Retry is a separate policy for tolerating transient outcomes. The question neither of you is asking: *why does a class named `CircuitBreaker` contain `_retry_with_backoff`?* The class name isn't just a label — it's an epistemic frame. It causes readers (including reviewers, including you two) to pattern-match against a known pattern and stop inspecting. What's actually here is a `RetryingCircuitBreaker`, and that compound pattern has no established semantics. You're defending or attacking the implementation of something the name has prevented you from questioning.

---

## Transformation

**Original claim:** Retries are inside the circuit breaker's observation boundary, causing failure signal distortion.

**Transformed claim:** The class commits a category error by fusing two incompatible causal models of failure under a single authoritative name, and the name actively prevents observers from recognizing the fusion.

**The gap:** I began with a *measurement problem* — the circuit breaker can't see retry attempts. I arrived at an *ontological problem* — the two mechanisms cannot both be correct simultaneously about what "failure" means. The gap matters: fixing the measurement (moving retries outside) does not resolve the conceptual conflict, it only makes it explicit. The original claim implied there was a fixable wiring error. The transformed claim implies there is an unfixable semantic incompatibility that any implementation must choose to resolve, not repair.

---

## The Concealment Mechanism: Naming-as-Architecture

The code hides its real problems through **nomenclature that activates cached pattern recognition.**

`CircuitBreaker` is a well-understood industry pattern with documented semantics, state machine diagrams, and known failure modes. When a reader encounters this name, they load the cached pattern and evaluate the code against that template — *is the state machine correct? are the transitions right?* — rather than asking whether the entity being implemented matches the name. The private method `_retry_with_backoff` is doubly hidden: `private` by convention and `method` by encapsulation, so it doesn't appear in the public API. The coupling — `_retry_with_backoff` called from inside `execute()` — reads as mere delegation (an implementation detail) when it is actually a philosophical fusion.

The mechanism: **name a composite thing after one of its parts. Readers will inspect the named part and not notice the composite.**

---

## Improvement 1: The Legitimate Deepener

Extract retry into an injectable `RetryPolicy`. This passes code review and is genuinely better engineering — and it deepens the concealment.

```python
from dataclasses import dataclass, field
from typing import Callable, Type
import time, random

@dataclass
class RetryPolicy:
    """
    Configurable exponential backoff with jitter.
    Retries on any exception type in `retryable_exceptions`.
    """
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    retryable_exceptions: tuple = field(default_factory=lambda: (Exception,))

    def execute(self, fn: Callable, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return fn(*args, **kwargs)
            except self.retryable_exceptions as e:
                if attempt == self.max_retries - 1:
                    raise
                delay = min(
                    self.base_delay * (2 ** attempt) + random.uniform(0, 1),
                    self.max_delay
                )
                time.sleep(delay)


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 30.0,
        half_open_max: int = 3,
        retry_policy: RetryPolicy = None,
    ):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None
        self._retry_policy = retry_policy or RetryPolicy()  # injectable

    def execute(self, fn: Callable, *args, **kwargs):
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
            else:
                raise Exception("Circuit is open")
        try:
            result = self._retry_policy.execute(fn, *args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise
```

**Why this passes review:** Dependency injection. `RetryPolicy` is a clean, testable abstraction. The circuit breaker is now configurable with custom retry behavior. `RetryPolicy.execute` mirrors the CB's own `execute` signature — reviewers will praise symmetry.

**Why it deepens the concealment:**

The coupling is now an *injected dependency*, which looks like a feature (configurability) rather than a flaw (fusion). The incompatibility of the two failure models is now distributed across two well-documented classes, each with its own tests and clean interface. Reviewers will evaluate `RetryPolicy` against retry semantics and `CircuitBreaker` against circuit breaker semantics — and both will pass — without a reviewer ever evaluating the *composition*.

---

### Three Properties Visible Only From Trying to Strengthen

**1. The coupling point is the interface, not the implementation.**
By making retry injectable, we revealed that *any* retry policy passed in will create the same observation blindness. We didn't fix the coupling; we made it configurable. The problem isn't how retry is implemented — it's that the CB's `execute()` wraps *any* retry. Strengthening the implementation revealed that the interface is where the problem lives.

**2. `RetryPolicy.execute` and `CircuitBreaker.execute` have identical signatures — and competing semantics.**
Both take `(fn, *args, **kwargs)`. Both claim to "execute" a function reliably. The naming collision is not incidental: they're solving the same problem — reliable function invocation — with irreconcilable assumptions. Making `RetryPolicy` a first-class object forced this into view.

**3. There is no composition protocol.**
`RetryPolicy` has no way to signal "this is attempt 2 of 3" to the circuit breaker. The circuit breaker has no way to tell the retry policy "stop, circuit just opened mid-loop." They are epistemically isolated even when injected together. Injection that provides zero shared state between the composites is not composition — it's sequential delegation that looks like composition.

---

## Improvement 2: The Legitimate Contraditor

Eliminate execution ownership from the circuit breaker entirely. Make it a pure state machine with an observation API. Let retry live outside the circuit breaker boundary, calling the CB after each individual attempt.

```python
import threading, time, random

class CircuitBreaker:
    """
    Pure state machine. Does not execute or retry anything.
    Callers must call should_allow_request() before each attempt
    and record_success()/record_failure() after each outcome.
    """
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30.0, half_open_max=3):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None

    def should_allow_request(self) -> bool:
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
                return True
            return False
        return True

    def record_success(self):
        self._on_success()

    def record_failure(self):
        self._on_failure()

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


def execute_with_retry(fn, circuit_breaker, max_retries=3, base_delay=1.0):
    """
    Retry loop that reports every individual attempt to the circuit breaker.
    The CB can open during a retry sequence, halting further attempts immediately.
    """
    for attempt in range(max_retries):
        if not circuit_breaker.should_allow_request():
            raise Exception("Circuit opened during retry sequence")
        try:
            result = fn()
            circuit_breaker.record_success()
            return result
        except Exception:
            circuit_breaker.record_failure()
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

**Why this passes review:** Clean separation of concerns. The circuit breaker is a textbook state machine. The retry loop is a standalone function. The CB is independently testable against the state machine spec. Each individual retry attempt is visible to the CB — the original flaw is corrected. The CB can interrupt retries the moment it opens.

**This contradicts Improvement 1** by inverting the ownership of execution: Improvement 1 says the CB *wraps* retry (keeps ownership, makes retry injectable). Improvement 2 says retry *calls* the CB (CB has no execution ownership at all). Improvement 1 strengthens encapsulation; Improvement 2 destroys it. Both are correct.

---

### The Structural Conflict That Exists Only Because Both Are Legitimate

The conflict is: **who is the unit of failure?**

- Improvement 1 answers: the unit is an `execute()` call (one signal per client request). The CB observes aggregated outcomes and respects what the caller considers one logical operation.
- Improvement 2 answers: the unit is an individual attempt (one signal per network call). The CB observes physical reality and can respond to the actual failure rate.

Both answers produce valid code. The conflict is not a code bug — it's a disagreement about *what the circuit breaker is modeling*. Is it modeling the health of a service (physical attempts) or the experience of a caller (logical operations)? These are genuinely different things with different correct behaviors. And neither implementation can be correct for both simultaneously.

The conflict exists *only because both pass code review.* If one were obviously wrong, there would be no conflict — just a mistake. The fact that both are defensible means the problem is not in the code at all; it's in the **unspecified requirement for what a "failure" is.**

---

## Improvement 3: The Conflict Resolver

Merge retry into the circuit breaker with per-attempt CB observation **and** state-gated early termination. The circuit breaker watches every attempt and can halt mid-sequence if it opens.

```python
class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30.0, half_open_max=3):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None

    def execute(self, fn, *args, max_retries=3, base_delay=1.0, **kwargs):
        if not self._check_and_maybe_transition():
            raise Exception("Circuit is open")

        for attempt in range(max_retries):
            try:
                result = fn(*args, **kwargs)
                self._on_success()
                return result
            except Exception:
                self._on_failure()              # CB sees every attempt
                if self._state == self.OPEN:
                    raise                       # halt: circuit just opened
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)

    def _check_and_maybe_transition(self) -> bool:
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
                return True
            return False
        return True

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

**Why this passes review:** Every attempt updates CB state (correct). The CB can open mid-retry and halt the sequence (correct). Clean encapsulation is preserved (correct). Both prior requirements — granular observation and encapsulated execution — appear to be satisfied.

---

### How It Fails

With `failure_threshold=5` and `max_retries=3`:

A single call to `execute()` where the downstream fails three times increments `_failure_count` by **3**, not 1. Two `execute()` calls that each exhaust retries open the circuit — `failure_count` reaches 6. The threshold of 5 is now calibrated against *attempts*, but the operator configured it thinking it measured *logical calls*.

In HALF_OPEN, a single probe fires 3 attempts, triggering 3 `_on_failure()` calls. `_failure_count` was already at 5 (from before OPEN). Now it's 8. The circuit re-opens on the first attempt of the first probe, before the retry sequence even has a chance to test recovery. HALF_OPEN becomes unreachable in the steady-state — it exists in the code but not in the runtime behavior.

**The failure mode is not a bug. It is a unit mismatch that the API cannot express.**

`failure_threshold=5` has an invisible type: `5 [calls]` or `5 [attempts]`. Improvement 3 silently changes the unit from calls to attempts without changing the parameter name, default value, or documentation. Every existing deployment that configured `failure_threshold` by tuning against "how many failed requests before opening" is now mis-calibrated by a factor of `max_retries`. And there is no way to write the correct value — the parameter cannot specify its own unit.

---

## What the Failure Reveals About the Design Space

The conflict between Improvements 1 and 2 revealed that **observation granularity** is the central tension. Improvement 3 appeared to resolve it by choosing fine granularity (per-attempt). But the failure of Improvement 3 reveals something the conflict alone could not:

**The design space is two-dimensional, and the API only has one axis.**

```
                        Threshold Unit
                    "per call"   "per attempt"
                   ┌───────────┬─────────────┐
Observation    per │ Impr. 1   │ Impr. 3     │
Granularity   call │ (hides    │ (threshold  │
                   │  reality) │  wrong)     │
                   ├───────────┼─────────────┤
              per  │ impossible│ Impr. 2     │
             attem.│ (incoher.)│ (external   │
                   │           │  API only)  │
                   └───────────┴─────────────┘
```

- Improvement 1 occupies the top-left: it observes per-call and the threshold unit is implicitly per-call. Coherent but blind.
- Improvement 2 occupies the bottom-right: it observes per-attempt and the caller configures the threshold with full knowledge. Coherent but externalizes the composition problem.
- Improvement 3 occupies the top-right: it observes per-attempt but the threshold unit is still implicitly per-call. This is the incoherent cell — the design space's broken quadrant. It looks like a resolution because it satisfies both surface requirements, but it lands in the only configuration that is *internally inconsistent.*

The bottom-left is impossible: you cannot observe at call granularity while calibrating a threshold in attempt units, because you don't have attempt information.

**The conflict alone (Improvements 1 vs. 2) suggested the problem was choosing the right granularity.** The failure of Improvement 3 reveals that granularity and calibration are *orthogonal dimensions*, and any design that treats them as one dimension — as this class does with its single `failure_threshold` parameter — will produce a semantically uncalibrable system in at least one of the four cells.

The real design problem is not in any method. It is in the fact that `failure_threshold` has no way to declare what it counts. The parameter is typed as `int`. It needs to be typed as `int [per what unit]`. No amount of refactoring the execution logic resolves this — the problem is in the configuration schema, and it is only visible because we tried every execution strategy and found the schema breaks them all in different ways.
