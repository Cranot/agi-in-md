# Structural Analysis: Retry Mechanism with Circuit Breaker

---

## I. The Falsifiable Claim

**The circuit breaker's failure counter measures retry-chain exhaustions, not service failures, causing it to open approximately `max_retries` times later than health state warrants, and silently amplifying load on failing services by a factor of `max_retries` before opening.**

This is falsifiable: mock a service failing 100% of the time. Count actual calls before the circuit opens. You'll get `failure_threshold × max_retries = 15`, not `5`. During HALF_OPEN, a single probe fires 3 times internally before the circuit breaker registers a single failure event.

---

## II. Three Experts Stress-Test the Claim

**Expert A — Defends it:**
The arithmetic is clean. `_on_failure()` is called exactly once per exhausted retry chain, not once per actual call failure. The `_failure_threshold` of 5 is calibrated against a unit that doesn't correspond to service health. The claim is correct and verifiable.

**Expert B — Attacks it:**
The retry-inside-breaker pattern is documented in Hystrix-style implementations and is a deliberate trade-off, not a structural error. The *actual* structural problem is that `_failure_count` never decays in CLOSED state — it only resets on success. A service that produces 4 failures followed by 1 success followed by 4 more failures never trips the circuit. More critically: the entire state machine has no locking. In any concurrent context (the only context where circuit breakers matter), `_state`, `_failure_count`, and `_success_count` are all race conditions. Two threads can simultaneously read `OPEN`, both decide to transition to `HALF_OPEN`, and `_success_count` can overshoot `_half_open_max` non-atomically.

**Expert C — Probes what both take for granted:**
Both experts assume the circuit breaker should observe exceptions as its input signal. Both take for granted that exception propagation is the correct health measurement boundary. Expert A assumes retry-amplification is bad; Expert B assumes thread-safety is the "real" problem — but both accept that `try/except` is the right observation instrument. What neither questions: a circuit breaker consuming binary exception signals is receiving the *coarsest possible* signal. Timeout, 500, connection refused, malformed response — all collapse into one boolean. The structural problem may be that the entire architecture is built on exception semantics as its health model.

---

## III. The Transformed Claim

**Original:** The failure counter measures the wrong granularity.

**Transformed:** The circuit breaker and retry mechanism are coupled through exception propagation as their sole shared signal, which forces both to operate on the same failure semantics despite serving fundamentally different purposes — retry hedges against transience (per-call, time-local), circuit breaker measures systemic state (cross-call, time-global) — and this coupling is the structural invariant that makes every local fix inadequate.

The granularity problem isn't a bug to fix. It's a symptom of incompatible coordination domains forced into one class.

---

## IV. The Concealment Mechanism

**Idiomatic exception propagation as observation boundary.**

The code uses `try/except` as its health measurement instrument. This is *idiomatic* — exceptions propagate, handlers handle them. The retry catches exceptions internally and re-raises the final one; `execute` catches the re-raised exception and calls `_on_failure`. This looks exactly like correct Python. The concealment is that three distinct semantics travel through the same exception channel:

1. **Transient failure** — retry domain: "this attempt failed, try again"
2. **Systemic health signal** — circuit breaker domain: "the service is degraded"
3. **Caller notification** — exception propagation domain: "your operation failed"

These are collapsed into one exception object bubbling up a call stack. The code *looks* correct because exception handling is what you do with exceptions. The structural problem hides inside idiomatic code.

---

## V. The Legitimate-Looking Improvement That Deepens Concealment

```python
def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
    last_exception = None
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
    raise last_exception
```

**Why it passes code review:**
- Properly preserves `last_exception` — better error fidelity
- Cleaner control flow — eliminates the nested `if attempt == max_retries - 1` check
- Correctly raises after loop exhaustion
- Follows standard Python retry idiom

**Why it deepens concealment:**
The `last_exception` variable makes the retry loop look like careful, intentional exception management — which makes the abstraction boundary between retry-domain and circuit-breaker-domain even less visible. The code now appears *more* professional, and the structural coupling is harder to see, not easier.

---

## VI. Three Properties Visible Only Because We Tried to Strengthen It

1. **There is no injection point.** When we tried to add feedback from retry attempts to the circuit breaker, we had nowhere to put it without restructuring. The `last_exception` solution proved this: the retry loop is architecturally opaque to the object that wraps it.

2. **`max_retries` and `failure_threshold` are uncalibrated.** Attempting to improve the retry forced us to notice that `3` and `5` have no designed relationship. Change one, the other becomes wrong. There's no formula connecting them in the design.

3. **The improvement made the failure-count loss explicit.** Storing `last_exception` highlights that whether 1, 2, or 3 failures occurred during the retry chain, the circuit breaker receives exactly one `_on_failure` call. The improvement made the information loss *visible by naming what's preserved.*

---

## VII. Improvement Diagnosed: What It Conceals

The `last_exception` improvement conceals that the number of failures during the retry sequence is permanently discarded — the circuit breaker cannot distinguish "failed once" from "failed three times." The improvement looks like better exception handling but preserves the fundamental structure: retry is a black box emitting one exception signal per chain.

The original problem visible through the improvement: **retry is a black box to the circuit breaker in both the original and improved code.** The improvement *recreates* this property by making the black box look more intentional.

---

## VIII. Second Improvement: Pierce the Black Box

```python
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
    except Exception as e:
        # _on_failure already called per-attempt inside retry
        raise

def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
    last_exception = None
    for attempt in range(max_retries):
        if self._state == self.OPEN:
            raise Exception("Circuit opened mid-retry")
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exception = e
            self._on_failure()          # Report each attempt, not each chain
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
    raise last_exception
```

Now every attempt is observed. The circuit can open mid-retry. This looks like a real improvement.

---

## IX. Diagnostic Applied to Second Improvement

**What it conceals:** `_on_failure()` is now called inside `_retry_with_backoff`, *and* the exception propagates to `execute`'s except clause — which in the original called `_on_failure` again. We've introduced double-counting. To fix it, we remove `_on_failure` from `execute` — but then a single-attempt failure with no retry isn't tracked at all unless retry is always invoked. The state machine is now entangled across two methods that both mutate shared state with no clear ownership.

**Property of original problem recreated:** **`failure_threshold` is now semantically undefined.** In the original, it meant "retry chains." In this version, it means "individual attempts." Change `max_retries` from 3 to 5 and the circuit opens 66% faster with no change to the circuit breaker's configuration. The calibration problem — which the first improvement obscured — is now explicit and unmistakable. The second improvement didn't create this problem. It revealed that the problem was always there, hiding behind the black box.

---

## X. The Structural Invariant

**No observation point inside a nested composition can simultaneously respect both retry-chain semantics and attempt-level semantics.**

Place the observation point outside the retry loop (original design): the circuit breaker sees one failure per chain — correct unit, wrong count.

Place it inside the retry loop (second improvement): the circuit breaker sees one failure per attempt — correct granularity, double-counts per chain.

Every improvement moves the observation point. The invariant persists across all positions because it is not a property of where the point is placed — it is a property of the design pattern: **when retry and circuit breaker share a call stack through exception propagation, they are forced to share failure semantics, but they require incompatible semantics to function correctly.**

---

## XI. The Category of Designs Bounded by This Invariant

**Nested execution policy designs** — any design where resilience policies (retry, circuit breaker, timeout, bulkhead) are expressed as nested function wrappers or method chains that share a single call stack and communicate through exception propagation.

The invariant is: *you cannot observe the right granularity from inside the nesting.*

This category includes: Hystrix-style command wrappers, decorator chains, `with`-statement policy stacks, and the code under analysis. All implementations in this category face the same trade-off, regardless of language or framework.

---

## XII. The Adjacent Category: Where the Invariant Dissolves

**Separated execution policies with a shared health event stream.**

```python
import time, random
from dataclasses import dataclass, field
from typing import Optional
import threading

@dataclass
class HealthEvent:
    service_id: str
    success: bool
    latency_ms: float
    error_type: Optional[str]
    timestamp: float = field(default_factory=time.time)


class HealthModel:
    """Stateful observer of service health. No retry logic."""
    def __init__(self, failure_rate_threshold=0.5,
                 window_seconds=60, min_sample_size=5):
        self._threshold = failure_rate_threshold
        self._window = window_seconds
        self._min_sample = min_sample_size
        self._events: list[HealthEvent] = []
        self._lock = threading.Lock()

    def record(self, event: HealthEvent) -> None:
        cutoff = time.time() - self._window
        with self._lock:
            self._events = [e for e in self._events
                            if e.timestamp > cutoff]
            self._events.append(event)

    def is_open(self, service_id: str) -> bool:
        cutoff = time.time() - self._window
        with self._lock:
            relevant = [e for e in self._events
                        if e.service_id == service_id
                        and e.timestamp > cutoff]
        if len(relevant) < self._min_sample:
            return False
        failure_rate = sum(1 for e in relevant if not e.success) / len(relevant)
        return failure_rate > self._threshold


class RetryPolicy:
    """Executes with retry. No circuit logic — queries HealthModel."""
    def __init__(self, max_retries=3, base_delay=1.0):
        self._max_retries = max_retries
        self._base_delay = base_delay

    def execute(self, fn, service_id: str,
                health_model: HealthModel, *args, **kwargs):
        last_exception = None
        for attempt in range(self._max_retries):
            # Check health before each attempt, not just before the chain
            if health_model.is_open(service_id):
                raise CircuitOpenError(
                    f"{service_id} circuit open at attempt {attempt}")
            start = time.time()
            try:
                result = fn(*args, **kwargs)
                health_model.record(HealthEvent(
                    service_id=service_id, success=True,
                    latency_ms=(time.time() - start) * 1000,
                    error_type=None))
                return result
            except Exception as e:
                last_exception = e
                health_model.record(HealthEvent(
                    service_id=service_id, success=False,
                    latency_ms=(time.time() - start) * 1000,
                    error_type=type(e).__name__))
                if attempt < self._max_retries - 1:
                    delay = (self._base_delay * (2 ** attempt)
                             + random.uniform(0, 1))
                    time.sleep(delay)
        raise last_exception


class CircuitOpenError(Exception):
    pass
```

**How this succeeds where every improvement failed:**

| Problem | Original | Improvement 1 | Improvement 2 | Adjacent Design |
|---------|----------|---------------|---------------|-----------------|
| Granularity: retry chain vs. attempt | ✗ Chain only | ✗ Chain only | ✗ Double-counts | ✓ Every attempt observed |
| Calibration: threshold independent of retry count | ✗ Threshold = chains | ✗ Threshold = chains | ✗ Threshold = attempts | ✓ Rate-based, count-agnostic |
| Thread safety | ✗ Race conditions | ✗ Race conditions | ✗ Worse races | ✓ Lock on shared model only |
| Mid-retry circuit opening | ✗ Cannot | ✗ Cannot | ✓ But double-counts | ✓ Check before each attempt |
| Failure signal richness | ✗ Binary | ✗ Binary | ✗ Binary | ✓ Rate, latency, error type |

The invariant dissolves because **the observation boundary is no longer the call stack**. `HealthModel.record()` is called at every attempt by `RetryPolicy`, and `HealthModel.is_open()` is queried before every attempt. The two policies are *peers observing the same stream* rather than nested wrappers on the same exception. Calibration becomes independent: changing `max_retries` from 3 to 5 doesn't change when the circuit opens, because the circuit now responds to failure rate, not failure count.

---

## XIII. The New Impossibility

**Per-call retry budget determinism becomes impossible.**

In the original design, `max_retries=3` is a hard guarantee: you get exactly 3 attempts. The retry budget is local, per-call, and unconditional.

In the adjacent design, `max_retries=3` is an upper bound, not a guarantee. If concurrent callers are also failing — each one contributing failure events to the shared `HealthModel` — the circuit can open after your first attempt, interrupting your retry sequence. Your actual retry count is `f(global system state, concurrent callers, timing)`. You cannot predict it locally.

Moreover: **backoff delay interacts with the measurement window in non-local ways.** In the original design, exponential backoff is purely local — it spaces out your attempts. In the adjacent design, your 4-second backoff delay means your retry attempt arrives in a different slice of the `window_seconds` window, potentially after the circuit has already re-closed. The interaction between individual backoff timing and the aggregate sliding window creates dynamics that are impossible to reason about from within `RetryPolicy`.

---

## XIV. The Finding

```
Original Impossibility                Adjacent Impossibility
─────────────────────────────────     ──────────────────────────────────
Observing correct failure             Per-call retry budget
granularity from inside a             is deterministic when circuit
nested call stack.                    state is shared and time-varying.

Calibrating threshold                 Reasoning about backoff's
independently of retry count          interaction with a probabilistic
when count determines events.         sliding window health model.
```

**The structural finding:**

Retry semantics and circuit breaker semantics are incompatible coordination domains. Retry is *per-call, time-local, count-bounded* — it makes a deterministic promise to one caller. Circuit breaking is *cross-call, time-global, rate-measured* — it makes a probabilistic claim about system state shared across all callers.

Any design that co-locates them in a single execution unit forces one domain to surrender to the other. The original design surrenders circuit breaker accuracy to retry opacity. The adjacent design surrenders retry determinism to circuit breaker accuracy.

This trade-off is not implementable away. It is a property of the problem space: **you cannot simultaneously make a deterministic per-call promise and an accurate cross-call probabilistic claim about the same underlying resource state.** Every design choice is a position on this axis, not an escape from it. The original code doesn't have a bug — it has made a hidden, uncritiqued choice about which domain to sacrifice, and it has made that choice invisible.
