# Structural Autopsy of a Circuit Breaker

## The Falsifiable Claim

> **The circuit breaker and retry mechanism have irreconcilably fused failure semantics: the circuit breaker cannot observe, distinguish, or respond to retry-level failures, making its state machine a systematic liar about downstream health.**

---

## Three Experts Test the Claim

**Defender:** Correct. With defaults, the circuit opens after 5 × 3 = **15 actual downstream failures**, not 5. In HALF_OPEN (designed for *gentle probing*), each "probe" fires up to 3 retries — hammering the recovering service. The `failure_threshold` parameter is a lie.

**Attacker:** This is a design choice. The operation *is* "attempt with retries." The circuit counts *operation* failures, which is a valid abstraction. The real structural flaw is **thread-unsafety** — `_state`, `_failure_count`, and `_last_failure_time` are mutated without synchronization, and in production this class is always shared.

**Prober:** Both of you assume the two mechanisms *should* have a unified failure model. The deeper issue is they **can't** — retry handles transient blips (milliseconds), circuit breaker handles systemic outage (minutes). The problem isn't miscounting. It's that **they're fused into one class with no seam**, making it impossible to reason about either independently.

## Claim Transformation

| Original | Transformed |
|---|---|
| "Failure counting is multiplicatively wrong" | "The retry and circuit breaker are structurally fused in a way that makes their individual failure semantics **unobservable** and their interaction **uncontrollable**" |

**The diagnostic gap:** The original claim is fixable with arithmetic. The transformed claim requires architectural decomposition. The original was a *symptom*.

---

## The Concealment Mechanism

**Name: Abstraction-Level Aliasing**

The word "failure" means two different things at two different levels:
- **Retry failure:** one HTTP call returned an error (transient)
- **Circuit failure:** an entire operation is hopeless (systemic)

The methods `_on_success()` and `_on_failure()` conceal this by presenting a single coherent narrative. The vocabulary's apparent simplicity hides the dual semantics. You read the code and think *"failure handling looks clean"* — precisely because the aliasing makes the two levels invisible.

---

## Improvement #1: Deepen the Concealment (Passes Review)

Add "observability" — per-attempt tracking inside retries:

```python
def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3):
    # ... existing init ...
    self._total_attempt_count = 0
    self._retry_exhaustion_count = 0

def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
    for attempt in range(max_retries):
        try:
            self._total_attempt_count += 1
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                self._retry_exhaustion_count += 1
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

**Why it passes review:** "We need metrics. Now we can alert on retry exhaustion rates."

**Why it deepens concealment:** It creates the *illusion* that retries are being observed while the circuit breaker **still doesn't use this data**. The counters exist but don't flow into the state machine. A reviewer sees monitoring and thinks the gap is covered. The structural disconnect becomes *harder* to notice.

### Three Properties Visible Only Because I Tried to Strengthen It

1. **The state machine has no input channel for partial failure.** There's no pathway from retry-level information into `_on_success()`/`_on_failure()`. The API is binary: succeed or fail. There's no signal for *"succeeded, but barely"* — which should keep the circuit warmer.

2. **Success after retries is indistinguishable from instant success.** A function that succeeded on its 3rd retry resets `_failure_count` to 0 identically to one that succeeded instantly. The circuit breaker is being **systematically told the system is healthier than it is**.

3. **`_last_failure_time` records the wrong moment.** It fires *after* all retries are exhausted (potentially 1 + 2 + jitter ≈ 4+ seconds of backoff later), so `reset_timeout` starts late relative to the first actual failure. The open window is shorter than configured.

---

## Improvement #2: Contradicts #1 (Also Passes Review)

Separate concerns — make retry injectable, and disable it during HALF_OPEN:

```python
def execute(self, fn, *args, retry_strategy=None, **kwargs):
    if self._state == self.OPEN:
        if time.time() - self._last_failure_time > self._reset_timeout:
            self._state = self.HALF_OPEN
            self._success_count = 0
        else:
            raise CircuitOpenError("Circuit is open")

    # HALF_OPEN: single probe, no retries — this is the whole point
    use_retry = retry_strategy if self._state == self.CLOSED else None

    try:
        if use_retry:
            result = use_retry.execute(fn, *args, **kwargs)
        else:
            result = fn(*args, **kwargs)
        self._on_success()
        return result
    except Exception as e:
        self._on_failure()
        raise
```

**Why it passes review:** Clean SRP. HALF_OPEN correctly probes with single attempts. Retry logic is injectable and testable.

---

## The Structural Conflict

Both improvements are independently correct and **cannot coexist**:

| | Improvement #1 | Improvement #2 |
|---|---|---|
| **Architecture** | Commits to fusion, adds internal metrics | Separates concerns into distinct objects |
| **Observability** | Retry data visible *inside* the class | Retry data trapped in a separate strategy |
| **Strengthens** | Monitoring of retry-circuit interaction | Independence of retry and circuit logic |
| **Weakens** | Separation of concerns | Ability to observe retry-circuit interaction |

**The conflict that exists only because both are legitimate:**

> The information that matters most — *how retry behavior should influence circuit state* — is **only observable from inside the fused architecture** but **only meaningful from outside it**.

Fusion (#1) lets you see the data but not interpret it structurally. Separation (#2) gives you clean semantics but makes the data inaccessible. The original code resolves this tension by **pretending it doesn't exist** — which is itself the concealment mechanism operating at the architectural level.
