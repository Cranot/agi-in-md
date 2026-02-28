# Structural Analysis: Retry Mechanism with Circuit Breaker

---

## I. The Claim

**Specific, falsifiable claim:** The circuit breaker's deepest structural problem is that retry and circuit breaking are semantically opposed but architecturally coupled — retries assume transient failures worth repeating; circuit breaking assumes persistent failures worth stopping. Nesting retry inside the circuit breaker guarantees the circuit opens *slowest* precisely when it should open *fastest*: during sustained failure, every logical failure costs `base_delay * (2^0 + 2^1 + 2^2) ≈ 7s` before registering. With `failure_threshold=5`, the circuit takes ~35 seconds minimum to open while hammering the downstream system with 15 actual calls.

**Falsifiable by:** Measuring time-to-circuit-open and actual call count under sustained failure, with and without the embedded retry.

---

## II. The Expert Debate

**Expert A — Defends:**
The coupling creates a temporal lie. `reset_timeout=30` appears to be a 30-second parameter, but because each "failure" takes 7+ seconds to register, the circuit's effective open-trigger window is `failure_threshold × retry_duration`, which is never visible in the constructor. The parameters are calibrated to a ghost timeline. The `_half_open_max=3` probe behavior is equally corrupted: each HALF_OPEN probe fires 3 retries, so "3 probes" becomes 9 actual calls — exactly the opposite of half-open's purpose, which is *minimal* load during recovery.

**Expert B — Attacks:**
The claim mislocates the problem. The retry/circuit-breaker semantic tension is well-known and well-solved (retry at the outer layer, circuit-break at the inner layer). *This* code's problem isn't the coupling itself — it's that the coupling is **invisible**. A caller of `circuit_breaker.execute(fn)` has no idea 3 retries will happen. The semantic opposition is the symptom; the hidden contract is the disease.

**Expert C — Probes what both take for granted:**
Both experts assume "failure" is a defined concept. Both treat `Exception` as if it were a coherent type. It isn't. A network timeout, a 429 rate limit, a 500 server error, and a `KeyError` from a malformed response are all `Exception` — they all trigger retry, all count against the circuit, all open it identically. The assumption that "failure deserves retry" and "failure should count toward circuit breaking" is only coherent if failure is *homogeneous*. The real concealment is that **`Exception` as universal failure type makes every downstream design decision appear reasonable while being secretly wrong.**

---

## III. The Gap as Diagnostic

| | |
|---|---|
| **Original claim** | Architectural coupling of semantically opposed mechanisms |
| **Transformed claim** | The coupling is made *possible by* — and serves to *conceal* — the erasure of failure semantics. `Exception` monoculture forces retry and circuit breaking to handle failure identically, making coupling appear natural. The structural problem is the absent failure taxonomy; the coupling is its architectural residue. |
| **The gap reveals** | What looked like an architectural problem is an ontological problem. The code doesn't know what failure *is*, so it cannot design around it. Every architectural complaint is downstream of this. |

---

## IV. The Concealment Mechanism

**Exception monoculture.** By catching bare `Exception` at every layer:

- Retry looks universal and sensible (*all* failures might be transient)
- Circuit breaking looks universal and sensible (*all* failures count)
- The coupling looks natural (of course you retry *and* circuit-break on failure)
- The real problem — that different failures require different handling — is structurally invisible

The code hides its problems by making `Exception` the load-bearing type, collapsing heterogeneous reality into a single symbol, after which all design decisions downstream look coherent.

---

## V. Improvement 1 — Deepens Concealment

Add principled exception classification. This passes review easily: it distinguishes retriable from non-retriable errors, prevents logic errors from tripping the circuit, and looks like exactly the right next step.

```python
import time, random

class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    # Principled failure taxonomy (looks legitimate, is arbitrary)
    CIRCUIT_BREAKING_EXCEPTIONS = (ConnectionError, TimeoutError, OSError)
    RETRIABLE_EXCEPTIONS        = (ConnectionError, TimeoutError)
    NON_RETRIABLE_EXCEPTIONS    = (ValueError, TypeError, KeyError)

    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None

    def execute(self, fn, *args, **kwargs):
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
            else:
                raise Exception("Circuit is open")
        try:
            result = self._retry_with_backoff(fn, *args, **kwargs)
            self._on_success()
            return result
        except self.CIRCUIT_BREAKING_EXCEPTIONS:
            self._on_failure()
            raise
        except Exception:
            raise  # Logic errors don't count against circuit

    def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except self.NON_RETRIABLE_EXCEPTIONS:
                raise  # Fast-fail on logic errors
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
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
```

**Why it passes review:** Adds exception classification, prevents logic errors from tripping the circuit, looks principled.

**Why it deepens concealment:** The classification *looks* like it solved the Exception monoculture problem. It hasn't — it replaced one arbitrary treatment with three arbitrary categories. The retry/circuit-break coupling is now *hardened* with a type system that makes it look intentional. The fundamental problem is buried under apparent sophistication.

---

## VI. Three Properties Visible Only From Strengthening

**1. The exception hierarchy is political, not semantic.**
The moment you try to classify exceptions, you discover there's no principled basis. Why does `ConnectionError` break circuits but not `httpx.ReadTimeout`? The classification is arbitrary, but it now *looks* principled, making the arbitrariness harder to challenge.

**2. Two orthogonal taxonomies now run in parallel.**
`RETRIABLE_EXCEPTIONS` and `CIRCUIT_BREAKING_EXCEPTIONS` are distinct sets that will drift independently. New exception types default to non-circuit-breaking and non-retriable — silently incorrect behavior. The code now has two classification systems that will diverge over time with no enforcement mechanism.

**3. Retry and circuit-breaking exception handling are now *inconsistently principled by design*.**
A non-retriable exception *can* break the circuit (if in `CIRCUIT_BREAKING_EXCEPTIONS`). A retriable exception *might not* break the circuit (if not in `CIRCUIT_BREAKING_EXCEPTIONS`). This inconsistency was always present, hidden by uniform treatment. Improvement 1 made it explicit — and then obscured it under the appearance of a solution.

---

## VII. Improvement 2 — Contradicts Improvement 1

Extract retry into an injectable policy. This passes review: it uses dependency injection, separates concerns, makes retry pluggable, and is textbook clean architecture.

```python
import time, random

class RetryPolicy:
    def __init__(self, max_retries=3, base_delay=1):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def execute(self, fn, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.base_delay * (2 ** attempt) + random.uniform(0, 1))


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3,
                 retry_policy=None):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None
        self._retry_policy = retry_policy or RetryPolicy()

    def execute(self, fn, *args, **kwargs):
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

**The contradiction:** Improvement 1 unified exception classification between retry and circuit breaking (they should *know about each other* to be principled). Improvement 2 separates retry from circuit breaking structurally (they should *not know about each other* to be decoupled). Both are legitimate software engineering principles. They cannot both be right.

---

## VIII. The Structural Conflict

The conflict is not just between two improvements — it is a circular dependency in the *problem domain itself*:

```
Whether retry should be circuit-breaker-aware
    determines
whether the two should be coupled.

But what counts as a "circuit-level failure"
    depends on
what retry strategy is in use.
```

Improvement 1 says: "couple them so classification is principled."  
Improvement 2 says: "decouple them so concerns are separated."  
Both are legitimate *because the design space contains no point where both are true simultaneously.*

---

## IX. Improvement 3 — Resolves the Conflict

Make retry observable. The circuit breaker becomes an observer of retry events, gaining visibility without structural coupling. Both previous improvements' requirements are satisfied independently.

```python
import time, random
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class RetryEvent:
    attempt: int
    exception: Exception
    will_retry: bool


class RetryPolicy:
    def __init__(self, max_retries=3, base_delay=1):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._observers: List = []

    def add_observer(self, observer):
        self._observers.append(observer)

    def _notify(self, event: RetryEvent):
        for obs in self._observers:
            obs.on_retry_event(event)

    def execute(self, fn, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                will_retry = attempt < self.max_retries - 1
                self._notify(RetryEvent(attempt, e, will_retry))
                if not will_retry:
                    raise
                time.sleep(self.base_delay * (2 ** attempt) + random.uniform(0, 1))


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

    def on_retry_event(self, event: RetryEvent):
        if not event.will_retry:   # Final failure after all retries
            self._on_failure()

    def execute(self, fn, *args, retry_policy: Optional[RetryPolicy] = None, **kwargs):
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
            else:
                raise Exception("Circuit is open")

        policy = retry_policy or RetryPolicy()
        policy.add_observer(self)           # Circuit breaker observes retry events

        try:
            result = policy.execute(fn, *args, **kwargs)
            self._on_success()
            return result
        except Exception:
            raise   # _on_failure already called via observer

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

---

## X. How Improvement 3 Fails

**Failure 1 — Double-counting risk:** `on_retry_event` calls `_on_failure()` when `will_retry=False`. The `except Exception` block in `execute` does *not* call `_on_failure()` again — but this is now dependent on a coordination assumption between two paths. Future maintainers will "fix" the seemingly-missing `_on_failure()` call in `execute`, introducing a double-count.

**Failure 2 — Observer accumulates across calls:** `policy.add_observer(self)` is called inside `execute`. If the caller passes a shared `RetryPolicy` instance across multiple calls, the circuit breaker registers as an observer *N* times. The Nth call produces N failure notifications from one actual failure.

**Failure 3 — The event model creates an implicit interface contract:** `CircuitBreaker` now depends on `RetryPolicy` emitting `RetryEvent` with a correct `will_retry` field. Swap in any retry policy that doesn't emit events — say, a simple `time.sleep` wrapper — and the circuit breaker silently stops counting failures. The coupling is now *invisible* and *runtime-detectable only*, which is strictly worse than the original explicit coupling.

**Failure 4 — The observer gains no new information:** `RetryEvent` carries `attempt`, `exception`, and `will_retry`. The observer only uses `will_retry`. The richer event model was built to enable the principled classification of Improvement 1 — but `on_retry_event` still doesn't classify by exception type. The complexity was added to solve a problem the architecture cannot actually solve.

---

## XI. What the Failure Reveals About the Design Space

The observer pattern's failure reveals an **impossible triangle** in the design space:

```
        [Principled failure semantics]
               /\
              /  \
             /    \
            /  ✗   \
           /________\
[Full decoupling]    [Circuit visibility into retries]
```

Any two corners are achievable. All three are not:

- **Principled semantics + full decoupling:** impossible — to classify failures you must see them, which requires coupling
- **Full decoupling + circuit visibility:** achievable (Improvement 2) but semantics are lost — `Exception` monoculture returns
- **Circuit visibility + principled semantics:** achievable (Improvement 1) but requires tight coupling

**The conflict alone** (Improvements 1 vs 2) showed us two corners couldn't coexist. **The failed resolution** shows us the triangle *as a whole* is infeasible: the observer pattern appeared to satisfy all three corners simultaneously, but its failures are precisely the three corners reasserting themselves. The design space's topology is triangular, not linear. There is no path to the center.

---

## XII. The Redesign — Accepting the Topology

Accept that automatic composition is impossible and sacrifice it. The redesign inhabits two *feasible points* rather than fighting toward the infeasible center, and exposes the composition seam explicitly.

```python
import time, random
from typing import Tuple, Type


class CircuitOpenError(Exception):
    """Distinct from generic Exception so callers can identify circuit state."""
    pass


class CircuitBreaker:
    """
    Pure circuit breaker. No retry logic.
    Counts every call to execute() that raises as one logical failure.
    The caller decides what constitutes a 'logical failure'
    by choosing what they wrap in execute().
    """
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None

    @property
    def state(self):
        return self._state

    def execute(self, fn, *args, **kwargs):
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
            else:
                raise CircuitOpenError(
                    f"Circuit open. Resets in "
                    f"{self._reset_timeout - (time.time() - self._last_failure_time):.1f}s"
                )
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except CircuitOpenError:
            raise  # Don't count circuit-open as a new failure
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


def retry_with_backoff(
    fn,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    retriable_on: Tuple[Type[Exception], ...] = (Exception,),
    not_retriable_on: Tuple[Type[Exception], ...] = (),
    **kwargs,
):
    """
    Pure retry logic. No circuit-breaking knowledge.
    Caller explicitly specifies failure taxonomy at the call site.
    """
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except not_retriable_on:
            raise
        except retriable_on as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)


# ── Composition Point A ──────────────────────────────────────────────────────
# Circuit breaker counts LOGICAL failures (post-retry exhaustion).
# Semantics: "This service has failed 5 times after all retries."
# Cost: Circuit opens slowly. Good for flaky but recoverable services.

cb_logical = CircuitBreaker(failure_threshold=5, reset_timeout=30)

def call_service_logical(payload):
    def retried():
        return retry_with_backoff(
            _upstream_call,
            payload,
            max_retries=3,
            retriable_on=(ConnectionError, TimeoutError),
            not_retriable_on=(ValueError,),
        )
    return cb_logical.execute(retried)


# ── Composition Point B ──────────────────────────────────────────────────────
# Circuit breaker counts INDIVIDUAL attempts.
# Retry only proceeds if circuit is still closed.
# Semantics: "This service has failed 5 individual calls."
# Cost: Circuit opens aggressively. Good for cascading failure protection.

cb_aggressive = CircuitBreaker(failure_threshold=5, reset_timeout=30)

def call_service_aggressive(payload):
    return retry_with_backoff(
        cb_aggressive.execute,
        _upstream_call,
        payload,
        max_retries=3,
        retriable_on=(Exception,),
        not_retriable_on=(CircuitOpenError,),  # Stop retrying if circuit opens
    )


def _upstream_call(payload):
    # Simulated upstream
    if random.random() < 0.7:
        raise ConnectionError("upstream unavailable")
    return {"ok": True, "payload": payload}
```

---

## XIII. What the Redesign Sacrifices

**Automatic composition.** The original code offered a single `execute(fn)` entry point that handled all resilience concerns invisibly. The redesign requires callers to:

1. Choose composition order explicitly (retry-then-circuit vs. circuit-then-retry)
2. Specify exception taxonomy at each call site
3. Understand the behavioral difference between the two compositions
4. Pass the composed call site, not the raw function

This is more boilerplate, more caller responsibility, and less "batteries included." The original code's ergonomic appeal — one call, all resilience handled — is entirely gone.

---

## XIV. What the Original Design Reveals Was Never a Flaw

The original code's coupling of retry and circuit breaking — diagnosed as its deepest structural problem — **was never a flaw**.

It was the **structural cost of providing a single coherent interface over an inherently incoherent problem space.**

The impossible triangle means: to give callers one method that handles all resilience concerns, you *must* couple retry and circuit breaking. You *must* collapse the failure taxonomy. You *must* make the composition order invisible. These are not ignorant choices — they are the price of usability. The "flaw" was the admission price to a design that works without requiring callers to understand the triangle.

The original code's actual failure was not the coupling itself. It was the **silence** around the coupling:

```python
# What the original code should have said:
class CircuitBreaker:
    """
    NOTE: This circuit breaker embeds retry logic.
    failure_threshold counts logical failures (post-retry), not individual attempts.
    With default max_retries=3, each logical failure represents 3 actual calls.
    Circuit opens after failure_threshold * max_retries actual calls.
    reset_timeout is measured from the last logical failure's FINAL retry, not its first.
    HALF_OPEN probes are also retried, so half_open_max=3 means up to 9 actual probe calls.
    """
```

The architecture was defensible. The missing documentation was not. The code was not hiding a bad design — it was hiding a trade-off it had made silently, preventing callers from calibrating their parameters against the actual behavior they were getting.

**The original design reveals:** the coupling was not a mistake. It was the cost of attempting something genuinely useful — hiding an infeasible design space from callers who don't need to know it exists. The only real flaw was refusing to name what it had done.
