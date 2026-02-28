# Structural Diagnosis: Retry × Circuit Breaker Failure Semantics

## The Claim (Specific, Falsifiable)

> **The deepest structural problem is that the retry loop is fused inside the circuit breaker's execution path, making the circuit br    -> Done (133s) -> 205 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/opus_L11_conservation_law_task_K.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
send one request, see if the service recovered. But this code fires up to 3 retries with exponential backoff *even in HALF_OPEN*. That's not probing, that's hammering a recovering service. The entire state machine's contract is violated by the embedded retry.

**Attacker:** Overstated. Many production circuit breakers embed retries. The *real* critical flaw is simpler: there's no thread safety. Two goroutines could both see `HALF_OPEN`, both retry, both call `_on_success`, and both believe they transitioned the state. The semantic issue is a design choice; the race condition is a bug.

**Prober (questioning both):** You both assume the problem is in the *mechanism*. But look: there's no logging, no metrics, no callbacks—no observation protocol at all. The fusion of retry and circuit-breaking wouldn't be dangerous if operators could *see* the compound behavior. The unobservability is what lets every other problem persist undetected.

### Transformed Claim

> The deepest structural problem is **unobservable failure compounding**: the retry mechanism silently multiplies both failure count and latency, while the circuit breaker treats each compound sequence as a single atomic event. The absence of any observation surface makes the system's actual failure behavior *unknowable* from its configuration alone.

### The Diagnostic Gap

| Original Claim | Transformed Claim |
|---|---|
| "Fused retry/CB have irreconcilable semantics" | "The compounding is invisible because observation is absent" |

The gap reveals: the semantic conflict isn't inherently irreconcilable—it's **unmanageable because it's unobservable**.

---

## The Concealment Mechanism

**Name: *Abstraction Collapse as Information Destruction***

`execute()` collapses a complex event sequence (up to 3 attempts, variable delays, partial successes) into a single boolean outcome. This abstraction boundary *destroys* the information the circuit breaker would need to make correct state decisions. The code *looks* clean precisely because the complexity is consumed inside `_retry_with_backoff` and never surfaces.

Concretely:

```
Reality:     attempt₁=FAIL → sleep → attempt₂=FAIL → sleep → attempt₃=FAIL
CB sees:     one failure
CB misses:   2 additional failures, ~7 seconds of backoff latency
```

---

## Improvement #1: Legitimate-Looking, Deepens Concealment

This would pass code review. It "fixes" the HALF_OPEN retry problem:

```python
def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
    max_retries = self._adjust_retries_for_state(max_retries)
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)

def _adjust_retries_for_state(self, max_retries):
    if self._state == self.HALF_OPEN:
        return 1  # Single attempt when probing
    return max_retries
```

### Why This Deepens Concealment

It creates the *appearance* of state-awareness while making the system harder to reason about. A reviewer thinks: "Great, HALF_OPEN is now gentle." But:

### Three Properties Visible Only Because We Tried to Strengthen

1. **Threshold semantics are now state-dependent**: `failure_threshold=5` means 15 real failures in CLOSED but 1 real failure in HALF_OPEN (since `_failure_count` is already at threshold—it's never reset on OPEN→HALF_OPEN transition). This asymmetry was *always present* but invisible.

2. **`max_retries` was always implicit circuit breaker state**: By making it depend on `self._state`, we revealed that it was *always* part of the state machine—just hidden.

3. **Time semantics are bifurcated**: In CLOSED, 5 "failures" span ~45 seconds of backoff. In HALF_OPEN post-fix, 1 failure is instantaneous. The `reset_timeout` is calibrated for neither timescale.

---

## Apply Diagnostic to Improvement #1

**What does it conceal?** That the circuit breaker should track *failure rate* (failures/time), not *failure count*. Reducing retries in HALF_OPEN made count-based thresholds even less meaningful as health proxies.

**What original property does it recreate?** The *invisible multiplication problem*—but at a higher level. Before: retries multiplied failures invisibly. Now: state-dependent retry counts multiply the *meaning of `failure_threshold`* invisibly.

---

## Improvement #2: Rate-Based Failure Tracking

```python
def __init__(self, failure_rate_threshold=0.5, observation_window=60,
             min_observations=10, reset_timeout=30, half_open_max=3):
    self._state = self.CLOSED
    self._observations = []          # [(timestamp, success: bool)]
    self._failure_rate_threshold = failure_rate_threshold
    self._observation_window = observation_window
    self._min_observations = min_observations
    # ... rest unchanged

def _record_and_evaluate(self, success):
    now = time.time()
    self._observations.append((now, success))
    cutoff = now - self._observation_window
    self._observations = [(t, s) for t, s in self._observations if t > cutoff]

    if len(self._observations) >= self._min_observations:
        rate = sum(1 for _, s in self._observations if not s) / len(self._observations)
        if rate >= self._failure_rate_threshold:
            self._state = self.OPEN
            self._last_failure_time = now
```

### Apply Diagnostic Again

**What does this conceal?** Each "observation" is *still* a compound retry-sequence. A failure rate of 50% could mean "half the 3-retry sequences fail" (= many real failures) or "half the single-attempt probes fail" (in HALF_OPEN). The rate-based approach *looks* sophisticated but still collapses the retry dimension.

---

## The Structural Invariant

> **The observation boundary and the retry boundary cannot coincide without information loss.**

The circuit breaker wants to observe *individual request outcomes* to assess health. The retry mechanism wants to aggregate *multiple attempts into one logical operation*. Through every improvement—count-based, state-adjusted, rate-based—this mismatch persists. It is a property of the *problem space*, not any implementation.

---

## Invert the Invariant

Make the observation boundary and retry boundary *trivially* coincide by having the circuit breaker observe every individual attempt:

```python
class CircuitBreaker:
    # ... state management ...

    def record_attempt(self, success):
        """Observe every individual attempt, not just operations."""
        self._record_and_evaluate(success)

    def should_allow(self):
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                return True
            return False
        return True


class RetryWithCircuitBreaker:
    def __init__(self, circuit_breaker):
        self.cb = circuit_breaker

    def execute(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
        for attempt in range(max_retries):
            if not self.cb.should_allow():
                raise CircuitOpenError("Circuit open, aborting retry sequence")
            try:
                result = fn(*args, **kwargs)
                self.cb.record_attempt(success=True)   # every attempt observed
                return result
            except Exception as e:
                self.cb.record_attempt(success=False)   # every attempt observed
                if attempt == max_retries - 1:
                    raise
                time.sleep(base_delay * (2 ** attempt) + random.uniform(0, 1))
```

The circuit breaker now sees *every attempt*. The impossible property (coincident boundaries) is trivially satisfied.

### The New Impossibility

The circuit breaker **can no longer distinguish between "one operation that failed 3 times" and "three operations that each failed once."** It has *too much* granularity—it's lost *operation-level context*.

Worse: the circuit can open **mid-retry-sequence**. Caller A's second retry attempt is denied because Caller B's failures (observed between A's attempts) pushed the failure rate over threshold. The circuit breaker's state becomes path-dependent on the *interleaving* of concurrent callers' retry sequences—a property that is essentially non-deterministic.

---

## The Conservation Law

| | Original Design | Inverted Design |
|---|---|---|
| **What's visible** | Operation-level outcomes | Individual attempt outcomes |
| **What's destroyed** | Per-attempt failure detail | Per-operation failure context |
| **Impossibility** | CB cannot see true failure rate | CB cannot see operation boundaries |

### The Finding

> **In any system coupling retry and circuit-breaking, information about failure provenance is conserved across abstraction boundaries: it can be moved but not created.**

You can observe at the *attempt* level (losing which attempts belong to which operation) or at the *operation* level (losing how many attempts each operation consumed). To serve both, you must introduce a third component that maintains the attempt↔operation mapping—which itself becomes a new abstraction boundary subject to the same law.

This is because retry and circuit-breaking are **dual failure strategies**—retry says *"try again"*, circuit-breaking says *"stop trying."* Their duality means any observation point that fully serves one strategy's information needs necessarily starves the other's. The total information deficit is conserved; only its location changes.

**Prescription:** Don't fuse them. Compose them as separate, observable layers with an explicit event protocol between them—accepting that two observation points (one per boundary) are the minimum viable architecture:

```python
# The minimum viable architecture
cb = CircuitBreaker()              # observes operations
retry = RetryPolicy(on_attempt=cb.record_probe)  # emits attempt-level events
pipeline = cb.wrap(retry.wrap(service.call))      # layered, not fused
```

Two boundaries. Two observation points. The conservation law satisfied, not fought.
