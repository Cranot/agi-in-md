# Structural Autopsy of a Retry-Circuit Breaker Fusion

## The Claim

**The deepest structural problem: two state machines with incompatible temporal models are fused into a single execution path.** The retry mechanism operates in *attempt-local time* (delays between retries of one call), while the circuit breaker operates in *system-global time* (failure rates across all calls). Their fusion means neither can reason correctly about its own time domain.

---

## Three Experts Stress-Test the Claim

**Defender:** Correct — with `max_retries=3` and `failure_threshold=5`, you need 15 actual downstream failures to trip the circuit. The retry loop *consumes* failures the circuit breaker needs to count. The threshold is a lie.

**Attacker:** That's by design. Retries handle transient failures; the circuit breaker handles persistent ones. Retries *should* absorb noise before signaling the breaker. The real problem is elsewhere.

**Prober:** You're both arguing about *counts*, but you're taking for granted that the problem is quantitative. Look at the *time* interaction: during `time.sleep()` in the retry backoff, other callers in a concurrent system hit this same circuit breaker. `_last_failure_time` gets silently overwritten. The failure count mutates without synchronization. The two time domains don't just interact — they *corrupt* each other.

### Transformed Claim

The deepest problem isn't the count mismatch — it's that **the retry's backoff sleeps distort the circuit breaker's failure-rate signal**, and the **circuit breaker's state transitions can invalidate a retry sequence mid-flight** without the retry knowing. Two clocks, one thread, no coordination.

**The diagnostic gap:** Original claim was *quantitative* (counts are wrong). Transformed claim is *topological* (the state spaces are incommensurable). What appeared as a counting bug is actually an architectural impossibility.

---

## The Concealment Mechanism

**Semantic flattening through sequential composition.**

By burying `_retry_with_backoff` as a private method inside `execute()`, the code presents two co-equal state machines as a parent-and-helper relationship. The `try/except` in `execute` looks like a clean binary gate — success or failure — concealing that `result` might represent *success-after-two-failures* (which the circuit breaker never learns about) and that the raised exception represents *three-failures-compressed-into-one* (which the circuit breaker counts once). The private method prefix `_` further conceals the retry mechanism as an "implementation detail" rather than an independent stateful system.

---

## Improvement 1: Deepen the Concealment

Make the retry loop "aware" of circuit state — *looks* like a fix, actually makes the concealment airtight:

```python
def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            # "Respect" circuit breaker mid-retry
            if self._state == self.OPEN:
                raise
            delay = min(base_delay * (2 ** attempt), 30) + random.uniform(0, 0.5)
            time.sleep(delay)
```

**Why this passes review:** "We should bail out of retries if the circuit opens." Sensible.

**Why this deepens concealment:** In a single-threaded context, `self._state` *cannot* become `OPEN` during the retry loop — nothing calls `_on_failure()` inside the loop. The check is vacuous. In a multi-threaded context, it's a data race (no lock). But now the code *looks* coordinated, inoculating it against the very criticism it deserves.

### Three Properties Visible Only Because of the Strengthening Attempt

1. **No callback channel exists** — there's no way for individual retry failures to reach the circuit breaker without breaking the sequential nesting
2. **The state is not thread-safe** — attempting to read `self._state` from within the retry loop exposes the absence of any synchronization primitive
3. **The retry has no failure taxonomy** — it catches bare `Exception`, so it cannot distinguish retryable transients from failures that should immediately trip the breaker

---

## Improvement 2: Contradicts Improvement 1

Extract the retry mechanism into a fully independent, composable unit with *zero* knowledge of circuit state:

```python
class RetryPolicy:
    def __init__(self, max_retries=3, base_delay=1, max_delay=30):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def execute(self, fn, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                delay += random.uniform(0, 0.5)
                time.sleep(delay)

class CircuitBreaker:
    # ... same fields ...
    def __init__(self, ..., retry_policy=None):
        # ...
        self._retry_policy = retry_policy or RetryPolicy()

    def execute(self, fn, *args, **kwargs):
        # ... open/half-open gate check ...
        try:
            result = self._retry_policy.execute(fn, *args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

**Why this passes review:** Clean separation of concerns. Testable independently. Composable. Textbook.

**The contradiction:**
| | Improvement 1 | Improvement 2 |
|---|---|---|
| **Principle** | Retry must check circuit state mid-execution | Retry must have zero knowledge of circuit |
| **Strengthens** | System responsiveness under failure | Composability and testability |
| **Weakens** | Retry independence | Mid-retry circuit awareness |

### The Structural Conflict

**The retry mechanism must be simultaneously coupled to and decoupled from the circuit breaker.** Coupled because mid-retry state changes must be respected (don't waste 30 seconds retrying a dead service). Decoupled because clean composition demands independent reasoning. This is a *coupling paradox*: the system needs tight feedback for safety and clean separation for sanity. Both requirements are legitimate, and they are mutually exclusive within the current design vocabulary.

---

## Improvement 3: Resolve the Conflict

Use a callback protocol — the retry mechanism stays independent but accepts injected signals:

```python
class RetryPolicy:
    def __init__(self, max_retries=3, base_delay=1, max_delay=30):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def execute(self, fn, *args, should_abort=None,
                on_attempt_failure=None, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if on_attempt_failure:
                    on_attempt_failure(e, attempt)
                if attempt == self.max_retries - 1:
                    raise
                if should_abort and should_abort():
                    raise
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                time.sleep(delay + random.uniform(0, 0.5))

class CircuitBreaker:
    # ...
    def execute(self, fn, *args, **kwargs):
        self._check_open_state()
        try:
            result = self._retry_policy.execute(
                fn, *args,
                should_abort=lambda: self._state == self.OPEN,
                on_attempt_failure=lambda e, a: self._on_failure(),
                **kwargs
            )
            self._on_success()
            return result
        except Exception:
            raise  # _on_failure already called per-attempt
```

### How It Fails

This creates a **dual-accounting crisis** — four specific failure modes:

1. **Success-after-failure contradiction:** A call that fails twice then succeeds reports 2 failures *and* 1 success. `_on_success()` resets `_failure_count = 0`, immediately erasing the per-attempt failures. The callbacks were pointless.

2. **Self-tripping abort:** `on_attempt_failure` calls `_on_failure()`, which can set `self._state = OPEN`. On the next iteration, `should_abort()` returns `True` — **the retry loop aborts itself** via its own callback. The retry and circuit breaker form an unintended feedback cycle.

3. **HALF_OPEN state corruption:** In HALF_OPEN, `on_attempt_failure` increments `_failure_count` *and* the eventual success increments `_success_count`. A single call can simultaneously push the circuit breaker toward OPEN and toward CLOSED.

4. **Ontological contradiction exposed:** For the retry mechanism, a failure-then-success is *not a failure* — the sequence succeeded. For the circuit breaker, every failure is a *health signal* — it must be counted regardless of what follows. The callback approach forces both observations to occur on the same event. This is not a bug — it's a proof that no consistent observation point exists.

### What the Failure Reveals

The conflict alone told us: *couple or decouple?* A design-taste question.

The failure of the resolution reveals something the conflict could not: **the retry mechanism and the circuit breaker have incompatible ontologies of failure.**

| | Retry Ontology | Circuit Breaker Ontology |
|---|---|---|
| A failed attempt | A provisional event | A definitive health signal |
| A failed attempt followed by success | Not a failure | A failure *and* a success |
| When failure "counts" | Only at sequence end | At the moment it occurs |

No composition of these two patterns can produce a coherent failure semantics because they disagree on what failure *is*. The design space has a hole at its center: you need a **third concept** — something like "provisional failure" or "weighted health signal" — that neither pattern currently models. A concept where a failed attempt degrades confidence (fractionally incrementing a health score) without committing to a binary failure count. Something like:

```python
self._health = max(0, self._health - 0.3)  # per-attempt degradation
# vs
self._health = min(1, self._health + 0.5)  # per-success recovery
```

The code doesn't need refactoring. It needs a *concept that doesn't exist in its vocabulary yet.* The vocabulary itself — binary success/failure, integer counts, threshold comparisons — is the structural constraint that makes all three improvements simultaneously necessary and mutually destructive.
