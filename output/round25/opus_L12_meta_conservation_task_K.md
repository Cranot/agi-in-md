# Meta-Conservation Analysis of Retry + Circuit Breaker

## The Claim

**The retry loop is embedded inside the circuit breaker's execution path, making the circuit breaker's state machine operate on a fundamentally different abstraction level (retry-batches) than the one it must protect (individual calls). The circuit breaker cannot fulfill its contract.**

Evidence: with `failure_threshold=5` and `max_retries=3`, the system makes up to **15 failing calls** before the circuit opens. In `HALF_OPEN`, a "gentle probe" fires 3 aggressive retries with exponential backoff.

---

## Three Experts Transform the Claim

| Expert | Position |
|---|---|
| **Defender** | Correct. The failure count is a count of retry-exhausted batches, not failures. The abstraction mismatch is real and provable. |
| **Attacker** | Too narrow. This is a *symptom* of an SRP violation. The class owns retry logic it should never contain. Composition failure, not abstraction failure. |
| **Prober** | Both of you missed that the *state machine itself is broken*. `_on_failure()` in `HALF_OPEN` doesn't transition to `OPEN` — it just increments a counter. You're debating composition while the core model is wrong. |

**Transformed claim:** The embedded retry both masks the incomplete state machine (retries absorb failures before they reach broken transitions) and is itself a symptom of having no boundary between protection logic and recovery logic.

**The diagnostic gap:** My original claim was about *composition*. The real problem is that the composition error *actively conceals* a state machine error.

---

## The Concealment Mechanism: "Recovery Shadowing"

The retry loop's recovery attempts shadow the circuit breaker's state transition defects. Because retries absorb failures before the state machine sees them, broken transitions are rarely exercised. **The more aggressive the retry, the more invisible the state machine bugs.**

Here are the bugs being shadowed:

```python
def _on_failure(self):
    self._failure_count += 1                          # Bug 1: No special HALF_OPEN handling
    self._last_failure_time = time.time()              #   A single HALF_OPEN failure should
    if self._failure_count >= self._failure_threshold:  #   immediately re-open the circuit.
        self._state = self.OPEN                        #   Instead it needs 5 more failures.

# Bug 2: When OPEN → HALF_OPEN, _success_count resets but _failure_count doesn't.
# The counter carries ghost state from the previous CLOSED period.

# Bug 3: max_retries/base_delay live in **kwargs — they collide with fn's kwargs.

# Bug 4: No thread safety on any mutable state. Every field is a race condition.
```

---

## Improvement #1: Deepen the Concealment (Would Pass Code Review)

```python
def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
    # "Gentle probe" — reduce retries in HALF_OPEN
    retries = 1 if self._state == self.HALF_OPEN else max_retries
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

This *looks correct*. A reviewer sees "HALF_OPEN handled specially" and assumes correctness. But it **deepens concealment** because:

1. It makes HALF_OPEN *appear* addressed at the retry level
2. Draws attention *away* from `_on_failure()` never handling HALF_OPEN→OPEN
3. Actually makes the bug *more reachable*: with only 1 retry in HALF_OPEN, failures reach `_on_failure` more often — but `_on_failure` still doesn't transition correctly

### Three Properties Visible Only Because We Tried to Strengthen

1. **The state machine has no HALF_OPEN → OPEN transition.** Invisible before; now critical because failures reach it.
2. **Retry count is a shadow state variable** — state-dependent but not modeled in state. We've created a second, informal state machine.
3. **`_failure_count` is never reset on HALF_OPEN entry** — ghost state from CLOSED bleeds into HALF_OPEN's threshold logic.

---

## Improvement #2: Centralize the State Machine

What Improvement #1 recreated: state-dependent behavior scattered across methods. Fix it:

```python
class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    TRANSITIONS = {
        (CLOSED,    'success'): lambda self: self._reset_failures(),
        (CLOSED,    'failure'): lambda self: self._to_open()
                                if self._failure_count >= self._failure_threshold else None,
        (HALF_OPEN, 'success'): lambda self: self._to_closed()
                                if self._success_count >= self._half_open_max else None,
        (HALF_OPEN, 'failure'): lambda self: self._to_open(),  # immediate!
        (OPEN,      'timeout'): lambda self: self._to_half_open(),
    }
```

**Apply the diagnostic again:** This conceals that the *events* themselves are the wrong granularity. A `'failure'` event from a retried execution that internally failed 3 times is not the same as a `'failure'` from a single call. The table is formally correct but **semantically incoherent** — its inputs don't correspond to reality.

---

## The Structural Invariant

> **The observer (circuit breaker) cannot simultaneously be the executor (retry coordinator) and maintain accurate observations, because execution modifies the thing being observed.**

This is a *Heisenberg problem in reliability engineering.* It persists through every improvement because it's a property of the problem space, not the implementation.

---

## Invert the Invariant: Separate Observer from Executor

```python
class CircuitBreakerGuard:
    """Pure observer. Never executes. Never retries."""
    def check(self):       ...  # raises CircuitOpenError if OPEN
    def record_success(self): ...
    def record_failure(self):  ...  # each REAL failure seen

def retry_with_circuit_breaker(fn, guard, max_retries=3):
    guard.check()
    for attempt in range(max_retries):
        try:
            result = fn()
            guard.record_success()
            return result
        except Exception:
            guard.record_failure()        # every individual failure observed
            if guard.is_open:             # circuit can open MID-RETRY
                raise CircuitOpenError()
            if attempt == max_retries - 1:
                raise
            time.sleep(backoff(attempt))
```

The observer/executor separation is now trivial. **But a new impossibility appears:** The circuit can open *mid-retry-sequence*. A single logical operation becomes non-atomic — some retries execute, then the circuit kills the rest. The caller expects `retry_with_circuit_breaker` to succeed-or-fail as a unit, but the circuit breaker can interrupt it.

---

## The Conservation Law

| | Original Design | Inverted Design |
|---|---|---|
| **Accuracy** | ❌ Sees 1 failure per 3 real failures | ✅ Sees every real failure |
| **Atomicity** | ✅ Retry sequence completes as a unit | ❌ Circuit can interrupt mid-retry |

> **Conservation Law: In a retry-with-circuit-breaker system, you cannot simultaneously have accurate failure observation AND atomic retry sequences. The product of observational accuracy × operational atomicity is bounded.**

---

## Apply the Full Diagnostic to the Conservation Law

**What does the law conceal?** A third property: **timeliness of protection.** The original delays protection (retries absorb failures, circuit opens late). The inverted design provides immediate protection (opens mid-retry). The real trade space is three-dimensional.

**Invariant of the law:** Any conservation law over N fault-tolerance properties conceals at least one additional property it implicitly fixes. Accounting for N+1 properties reveals N+2.

**Invert that invariant:** Try to write a specification that accounts for all properties. You can't — each new property makes the spec itself part of the failure surface.

---

## The Meta-Conservation Law

> **Every fault-tolerance mechanism extends the failure surface it was designed to reduce.** Reducing controlled failures by ΔF produces emergent failures ΔF' in a dimension invisible from the design that produced ΔF.

---

## The Prediction (What No Code Analysis Alone Reveals)

The meta-law predicts a specific production failure mode that exists in **no individual component** but only in their composition:

**Under sustained partial failure (e.g., 60% of calls failing), the retry mechanism will hold the circuit breaker in `CLOSED` state far longer than intended.** Here's why:

```
Call 1: fail, fail, succeed (retry saves it) → _on_success() → _failure_count = 0  ← RESET!
Call 2: fail, fail, succeed (retry saves it) → _on_success() → _failure_count = 0  ← RESET!
Call 3: fail, fail, succeed ...
... this continues indefinitely ...
```

Each successful retry **resets the failure counter to zero**, so the circuit *never opens* despite 66% of actual calls failing. The system maintains **maximum load** on the degraded service — 3× the intended call volume due to retries — precisely when it should be backing off.

**The circuit breaker becomes a load amplifier, not a load shedder.** This is the meta-law's prediction made concrete: the retry mechanism (fault tolerance) creates sustained overload (new failure surface) in a dimension (aggregate downstream load under partial failure) invisible from either component's logic alone.

### What to Actually Build

```python
# Separate the concerns. Let the circuit breaker observe real calls.
guard = CircuitBreakerGuard(failure_rate_threshold=0.5, window_size=100)  # rate-based!
retry = RetryPolicy(max_retries=3, backoff=exponential(base=1))

# Compose from outside — never embed one inside the other.
result = retry.execute(lambda: guard.protect(downstream_call))
#                       ↑ retry owns the loop
#                              ↑ guard sees every real call
```

Rate-based failure tracking (not counter-reset-on-success) eliminates the load amplification. Exterior composition eliminates Recovery Shadowing. The state machine becomes auditable because it operates on real events. The accuracy-atomicity tradeoff remains — it always will — but now it's *visible and tunable* rather than concealed.
