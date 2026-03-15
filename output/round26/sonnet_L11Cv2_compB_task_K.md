# Structural Analysis: Retry + Circuit Breaker

## Falsifiable Claim: The Deepest Problem

**The circuit breaker's failure threshold does not bound service load — it bounds `execute()` call outcomes.** Each `execute()` makes up to `max_retries=3` actual service attempts before reporting one outcome. With `failure_threshold=5`, the service absorbs up to **15 real calls** before the circuit opens. Falsifiable: instrument `fn` with a call counter; observe 15 invocations before state becomes OPEN, not 5. In HALF_OPEN, this is worse — probing for health multiplies load exactly when load-shedding matters most.

---

## Three Experts Transform It

**Defender:** The design is correct at the right abstraction level. The circuit breaker tracks *logical operation* outcomes, not raw attempts. Retrying transparently is a feature. This is standard resilience composition.

**Attacker:** The defender is naming a design choice as if it were a deliberate virtue. HALF_OPEN exists *specifically* to probe with reduced load. Embedded retries mean HALF_OPEN probes still hit the service three times per call. Worse: `_failure_count` is never reset when entering HALF_OPEN — only `_success_count` is — so one failure in HALF_OPEN immediately re-opens because the count is already at threshold. The state machine has a phantom counter it forgot to manage.

```python
def execute(self, fn, *args, **kwargs):
    if self._state == self.OPEN:
        ...
        self._state = self.HALF_OPEN
        self._success_count = 0          # ← resets success counter
        # _failure_count is NOT reset    # ← phantom counter, already ≥ threshold
```

**Prober — Exposed Assumptions:**
- `fn` is idempotent (safe to retry three times unconditionally)
- The caller always wants retries — there is no bypass path
- A failure worth retrying is *also* a failure worth counting against circuit health
- The circuit breaker is single-threaded (no lock anywhere)
- `_last_failure_time` in OPEN state correctly represents "when the circuit should reset" — but it updates on *every* failure, so a sustained failure stream continuously defers reset

---

## Concealment Mechanism: State Aliasing

The circuit breaker's state machine (CLOSED/OPEN/HALF_OPEN) aliases away a concrete execution dimension: **attempt count, cumulative delay, and actual service pressure**. The abstraction is *lossy in exactly the dimension that matters* for the circuit breaker's core function — load shedding.

The circuit breaker appears to count "failures" but actually counts a filtered, retry-smoothed derived signal. The threshold appears to be a load-control knob but controls something averaged and delayed. This is state aliasing: abstract state claims to represent what concrete state actually contains.

---

## Improvement: Deepen the Concealment

Separate retry from circuit breaker. Make them communicate through typed outcomes rather than raw exceptions:

```python
class RetriableError(Exception):
    """Transient — safe to retry, does not indicate system health degradation."""

class SystemError(Exception):
    """Structural — do not retry, circuit breaker should count this."""

class RetryPolicy:
    def __init__(self, max_retries=3, base_delay=1):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def execute(self, fn, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return fn(*args, **kwargs)
            except RetriableError as e:
                if attempt == self.max_retries - 1:
                    raise
                delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
            except SystemError:
                raise  # Never retry; let circuit breaker see it immediately

class CircuitBreaker:
    # ... same state machine, but execute() no longer calls _retry_with_backoff
    def execute(self, fn, *args, **kwargs):
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
                self._failure_count = 0   # ← fix phantom counter
            else:
                raise CircuitOpenError("Circuit is open")
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

The classes are now cleaner individually. But the concealment deepened: **who composes them, and in which direction, is now entirely the caller's responsibility** and is invisible in the class definitions. The coupling moved from *within* the class to *between* the call sites.

---

## Three Properties Visible Only Because We Tried to Strengthen It

**1. Exception taxonomy gap was always load-bearing.**
Separating `RetriableError` from `SystemError` reveals the original code assumed all exceptions are both retryable *and* circuit-health-relevant. These are orthogonal properties. The original code silently collapsed them; the improvement forces the gap into the open.

**2. Composition direction is genuinely ambiguous, not accidentally missing.**
Should retry wrap the circuit breaker (each retry checks circuit state independently) or should the circuit breaker wrap retry (circuit sees one outcome per logical call)? Both are valid. The improvement reveals that neither composition is obviously correct — they have different failure semantics — and the original code baked in one answer without acknowledging the choice existed.

**3. The circuit breaker has no natural unit of measurement.**
When retry is external, the circuit breaker must decide what constitutes "one failure." It was borrowing `execute()` calls as an implicit unit. The improvement reveals this unit was never defined — it was inherited from the call structure, not chosen.

---

## Same Diagnostic Applied to the Improvement

The improvement introduces **Composition Indirection**: by separating concerns, it hides the composition strategy in the caller. A caller can wrap retry inside the circuit breaker, wrap the circuit breaker inside retry, or apply neither — with no guidance from the API on which is correct. 

The concealment mechanism is identical: **state aliasing**, but now the aliased state is the *composition topology itself*. The improvement reduced coupling within classes at the cost of making the structural relationship between classes opaque. The problem didn't go away; it moved one layer outward.

---

## Second Improvement: Make Composition Strategy Explicit

Address the composition direction ambiguity by making it a first-class, typed choice:

```python
class ResiliencePolicy:
    """
    Explicit composition of retry + circuit breaker.
    
    retry_scope='per_execute': CB sees one outcome. Retry is invisible to CB.
                               Use when failures are expensive to report.
    retry_scope='per_attempt': Each retry checks CB state independently.
                               Use when partial recovery is detectable mid-retry.
    """
    def __init__(self, circuit_breaker, retry_policy, retry_scope='per_execute'):
        self._cb = circuit_breaker
        self._retry = retry_policy
        self._retry_scope = retry_scope

    def execute(self, fn, *args, **kwargs):
        if self._retry_scope == 'per_execute':
            # CB wraps retry: one outcome per logical call
            return self._cb.execute(
                lambda: self._retry.execute(fn, *args, **kwargs)
            )
        elif self._retry_scope == 'per_attempt':
            # Retry wraps CB: each attempt is a circuit-checked call
            for attempt in range(self._retry.max_retries):
                try:
                    return self._cb.execute(fn, *args, **kwargs)
                except CircuitOpenError:
                    raise  # Never retry into an open circuit
                except RetriableError:
                    if attempt == self._retry.max_retries - 1:
                        raise
                    time.sleep(self._retry.base_delay * (2 ** attempt)
                               + random.uniform(0, 1))
```

---

## Structural Invariant

**Property of the problem space, not implementation:**

> Any system that measures service health through outcome sampling, while also mitigating failures on the same execution path, observes a distribution that is a function of its own mitigation policy — not the underlying service's true failure rate.

The circuit breaker cannot observe "raw" service health. It can only observe post-retry, post-mitigation health. These are different distributions. The more protection the system provides, the more distorted the health signal becomes. This is not a design flaw — it is a structural property of the problem. You cannot measure the thing you are simultaneously shielding.

---

## Inversion: Where the Impossible Becomes Trivial

The invariant says: raw health measurement is impossible on the production path because mitigation contaminate the signal.

**Invert:** Separate the probe path from the production path entirely.

```
Production request → [No retry] → Circuit Gate → Service
                                        ↑
                    Async health prober (synthetic probes, separate endpoint)
                    drives state machine independently
```

The circuit breaker's state is driven by synthetic probes on a dedicated health path — not by production request outcomes. Production calls don't retry; they either succeed or fail instantly. The circuit opens based on probe health, not production failures.

The "impossible" (uncontaminated measurement) becomes trivial: the probe sees raw service behavior because it is not contaminated by retry mitigation on the production path.

---

## New Impossibility

In the inverted design: **The health probe cannot observe which production requests are failing.**

The probe measures isolated, synthetic signals. Real production failures caused by specific payloads, edge cases, or user-pattern interactions are invisible to it. The circuit can be CLOSED (healthy by probe) while genuine production requests fail. The system gains measurement purity and loses measurement representativeness. The impossibility moved — it didn't disappear.

---

## The Conservation Law

> **Signal fidelity and protection depth are inversely coupled across any resilience system: as the system's protection of the service increases, its ability to measure the service's true health decreases proportionally.**

This is not "measurement affects the measured thing." That's obvious.

This is: **protection and measurement are the same mechanism operating in opposite directions on the same signal.** Retry *is* the distortion of the health signal; it cannot be removed from the measurement without also removing the protection. They are not separable features — they are one function with two names.

**What this predicts about a third design — latency-based circuit breaking (not attempted):**

A circuit breaker triggered by p99 latency rather than failure count will appear to solve the fidelity problem: latency spikes before failures increase, so the circuit detects degradation earlier. The conservation law predicts this apparent gain is paid for by *specificity loss under load*. Latency naturally increases under high request volume independent of service health. The circuit will open on load spikes that are not system failures. 

The design will require a latency *baseline* that tracks under normal load and a threshold *relative* to that baseline — which reintroduces a measurement of "normal," which is itself contaminated by the retry and circuit behavior during measurement. The conservation law predicts that any latency-based design will face the same tradeoff in a new dimension: sensitivity vs. specificity, with their product conserved. Tune for early detection and you get false positives under load. Tune against false positives and you get late detection. The product does not improve; it only redistributes.
