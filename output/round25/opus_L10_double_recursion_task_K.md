# Structural Diagnostic: Double Recursion on a Circuit Breaker with Retry

## Initial Claim (Falsifiable)

**The deepest structural problem: the retry loop is invisible to the circuit breaker's failure accounting.** `_retry_with_backoff` makes up to 3 attempts per call, but `_on_failure` increments `_failure_count` by 1. With `failure_threshold=5`, the breaker requires 5 failed `execute()` calls — meaning **15 actual failed requests** — before tripping. The mechanism designed to protect a failing service amplifies load 3× before ever engaging.

---

## Three-Expert Dialectic

**Defender:** It's worse than stated. In `HALF_OPEN` — meant to be a *cautious probe* — the code retries 3 times. A single probe hammers the recovering service with a burst of attempts. The entire purpose of `HALF_OPEN` is subverted.

**Attacker:** Many real circuit breakers embed retries. The breaker counts *logical operations*, not *physical attempts*. This is a defensible design choice, not a structural flaw. The threshold simply means "5 failed operations."

**Probing the shared assumption:** Both experts assume "failure" has a single meaning. The code never classifies failures. A `ConnectionTimeout` (transient) and an `AuthenticationError` (permanent) are treated identically by *both* the retry loop and the circuit breaker. The retry loop wastes attempts on non-transient errors. The circuit breaker counts transient errors that retries should have absorbed. The absence of a **failure taxonomy** makes the two mechanisms structurally incoherent regardless of composition strategy.

### Transformed Claim

> The deepest structural problem is not policy conflation but **semantic absence**: there is no failure taxonomy enabling the retry mechanism and the circuit breaker to coordinate on which failures are transient (retry-eligible) vs. persistent (breaker-eligible). Without this, both mechanisms degrade each other.

### The Diagnostic Gap

Original claim: **structural composition** (two mechanisms in one path).
Transformed claim: **type-level absence** (no failure vocabulary).
The gap reveals I was analyzing *plumbing* when the problem lives in the *type system*.

---

## The Concealment Mechanism

**Name:** *State-machine completeness illusion.*

The three states (`CLOSED`, `OPEN`, `HALF_OPEN`) and their transitions form a visually complete state machine diagram. This completeness conceals:

1. Failure counts are incoherent (retries invisible to breaker)
2. `HALF_OPEN` probes are aggressive (3 retries, not a gentle test)
3. Zero thread safety despite shared mutable state
4. `max_retries` in `_retry_with_backoff`'s signature is swallowed by `**kwargs`, meaning callers passing `max_retries` to `execute()` silently override the retry count — a latent parameter injection bug

The well-formed skeleton *looks like* a correct state machine, so reviewers audit transitions rather than semantics.

---

## First Improvement (Engineered to Deepen Concealment)

This would pass code review. It adds enums, locks, type hints, reduced HALF_OPEN retries, gradual recovery, a custom exception, and a state property:

```python
import time, random, threading
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitOpenError(Exception):
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3,
                 max_retries=3, base_delay=1):
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._last_failure_time = None
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN and self._last_failure_time:
                if time.time() - self._last_failure_time > self._reset_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
            return self._state

    def execute(self, fn: Callable, *args, **kwargs) -> Any:
        current_state = self.state  # lock acquired and released here
        if current_state == CircuitState.OPEN:
            raise CircuitOpenError(f"Circuit open, retry after {self._reset_timeout}s")

        retries = 1 if current_state == CircuitState.HALF_OPEN else self._max_retries

        try:
            result = self._retry_with_backoff(fn, retries, *args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _retry_with_backoff(self, fn, max_retries, *args, **kwargs):
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception:
                if attempt == max_retries - 1:
                    raise
                delay = self._base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)

    def _on_success(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._half_open_max:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
            else:
                self._failure_count = max(0, self._failure_count - 1)

    def _on_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN
```

### Three Properties Visible Only Because I Strengthened the Concealment

**1. The lock creates TOCTOU, not safety.** `execute()` calls `self.state` (acquires lock, checks state, mutates it, releases lock), then *proceeds without the lock*. Between the state read and the `fn()` call, another thread can trip the breaker, change state, or reset counts. The lock's presence makes this race condition *invisible to reviewers* — they see `threading.Lock()` and assume safety.

**2. Reducing HALF_OPEN retries to 1 reveals that the retry count was load-bearing for state transition semantics.** In HALF_OPEN: 1 attempt per probe, need 3 successes to close. In CLOSED: 3 retries per call, so failures are 3× harder to produce. The HALF_OPEN→CLOSED transition is a **behavioral cliff**: the instant we close, we become 3× more failure-tolerant. The system will oscillate between states differently depending on retry counts — and this coupling is now *harder* to see because the retry reduction *looks like* a principled fix.

**3. The `state` property performs mutation as a side effect of reading.** Any monitoring, logging, or debugging code that reads `breaker.state` can trigger OPEN→HALF_OPEN transitions. The property syntax conceals that observation changes the observed. This is a Heisenbug factory.

---

## Diagnostic Applied to the Improvement

**What it conceals:** The failure accounting is still incoherent. The Enum creates the illusion of a well-defined state machine. The lock creates the illusion of thread safety. The reduced HALF_OPEN retries create the illusion that retry/breaker interaction was considered. All cosmetic.

**What property of the original problem is recreated:** The improvement recreates the property that **failure counts and retry counts are denominated in different, incommensurable units**. The original was *uniformly* wrong (always 3 retries, always 1 failure increment). The improvement, by varying retry counts per state, makes the incommensurability *visible as asymmetry* — but doesn't resolve it. `failure_threshold=5` still means "5 failed execute() calls," not "5 failed attempts," and the gap between these two meanings now varies by state.

---

## Second Improvement (Addressing the Recreated Property)

This improvement counts each retry attempt as a failure against the breaker, separates probe execution from retried execution, adds a failure taxonomy, and allows the breaker to trip mid-retry:

```python
import time, random, threading
from enum import Enum
from typing import Callable, Any, Optional, Tuple, Type
from dataclasses import dataclass

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitOpenError(Exception):
    pass

@dataclass
class FailureWindow:
    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[float] = None

    def reset(self):
        self.failures = 0
        self.successes = 0
        self.last_failure_time = None

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 30,
        half_open_max: int = 3,
        max_retries: int = 3,
        base_delay: float = 1,
        retryable_exceptions: Tuple[Type[Exception], ...] = (IOError, TimeoutError),
    ):
        self._state = CircuitState.CLOSED
        self._window = FailureWindow()
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._retryable_exceptions = retryable_exceptions
        self._lock = threading.RLock()
        self._probe_semaphore = threading.Semaphore(1)

    def execute(self, fn: Callable, *args, **kwargs) -> Any:
        with self._lock:
            self._try_transition_to_half_open()
            state = self._state
            if state == CircuitState.OPEN:
                raise CircuitOpenError("Circuit is open")

        if state == CircuitState.HALF_OPEN:
            return self._execute_probe(fn, *args, **kwargs)
        return self._execute_with_retries(fn, *args, **kwargs)

    def _execute_probe(self, fn, *args, **kwargs):
        if not self._probe_semaphore.acquire(blocking=False):
            raise CircuitOpenError("Probe already in progress")
        try:
            result = fn(*args, **kwargs)
            with self._lock:
                self._window.successes += 1
                if self._window.successes >= self._half_open_max:
                    self._state = CircuitState.CLOSED
                    self._window.reset()
            return result
        except Exception:
            with self._lock:
                self._record_failure()
            raise
        finally:
            self._probe_semaphore.release()

    def _execute_with_retries(self, fn, *args, **kwargs):
        last_exc = None
        for attempt in range(self._max_retries):
            try:
                result = fn(*args, **kwargs)
                with self._lock:
                    self._window.failures = max(0, self._window.failures - 1)
                return result
            except self._retryable_exceptions as e:
                last_exc = e
                with self._lock:
                    self._record_failure()
                    if self._state == CircuitState.OPEN:
                        raise CircuitOpenError("Tripped during retry") from e
                if attempt < self._max_retries - 1:
                    time.sleep(self._base_delay * (2 ** attempt) + random.uniform(0, 1))
            except Exception:
                with self._lock:
                    self._record_failure()
                raise
        raise last_exc

    def _record_failure(self):
        self._window.failures += 1
        self._window.last_failure_time = time.time()
        if self._window.failures >= self._failure_threshold:
            self._state = CircuitState.OPEN

    def _try_transition_to_half_open(self):
        if self._state == CircuitState.OPEN and self._window.last_failure_time:
            if time.time() - self._window.last_failure_time > self._reset_timeout:
                self._state = CircuitState.HALF_OPEN
                self._window.successes = 0
```

### Diagnostic Applied to the Second Improvement

**What it conceals:** The `_lock` pattern is *still* TOCTOU. The lock is held during state check, released, then `fn()` is called unprotected. The `_probe_semaphore` partially fixes HALF_OPEN races but introduces a liveness hazard: if the probing thread is killed between `acquire` and `release` (e.g., via `signal`, `thread.interrupt()`, OOM), the semaphore is permanently held and the circuit *never* leaves OPEN.

More subtly: `failure_threshold=5` with `max_retries=3` now means the breaker can trip after **just 2 calls** to `execute()` (2 × 3 = 6 > 5). The threshold's meaning has silently shifted from "operations" to "attempts." A user migrating from the original code with the same configuration gets radically different behavior. **The configuration's semantics changed but its name didn't.**

**What property is recreated:** The second improvement still recreates the core tension — the `retryable_exceptions` tuple is a *static* classification. But failure transience is often *contextual*: a `TimeoutError` after 2 retries with exponential backoff is very different from a `TimeoutError` on first attempt. A `ConnectionError` during a deployment is transient; during a DNS failure it's persistent. The static tuple creates the illusion of a failure taxonomy while remaining fundamentally unable to distinguish transient-in-context from persistent-in-context.

---

## The Structural Invariant

The property that persists through every improvement, because it belongs to the problem space:

> **Retry and circuit-breaking are dual policies that require contradictory ownership of the failure-decision boundary.**

- A **retry policy** must own the failure interpretation: *"this failure is transient; I'll absorb it and try again."*
- A **circuit breaker** must own the failure interpretation: *"this failure counts toward my threshold; I may need to stop all calls."*

Both mechanisms claim authority over the same event (a failed call), but at **different granularities** — attempt vs. operation — and with **different intents** — absorption vs. accumulation.

| Version | Who is subordinated? | Result |
|---|---|---|
| Original | Circuit breaker (can't see retries) | Breaker is blind; 3× load amplification |
| Improvement 1 | Retry (reduced to 1 in HALF_OPEN) | Behavioral cliff at state transition |
| Improvement 2 | Neither (both count failures) | Configuration semantics become incoherent |

**This is not a bug to be fixed. It is a conservation law.** Any system combining retry and circuit-breaking within a single execution path must choose one of three structural costs:

1. **Hide failures from the breaker** (breaker is degraded)
2. **Hide state from the retrier** (retrier is degraded)
3. **Couple their configurations** (neither can be reasoned about independently)

The only escape from this invariant is to **extract the coupling into an explicit protocol** — a shared failure-classification function `(exception, context) → {retry, break, propagate}` that both mechanisms consume as input rather than either producing as side effect. But this doesn't eliminate the invariant; it relocates it to the classification function, which must now embody the contradiction: deciding, for each failure, whether it is "the kind of failure retries absorb" or "the kind of failure breakers count" — a decision that depends on the very retry/breaker state it's being used to determine.
