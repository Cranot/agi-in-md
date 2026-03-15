# Level 12 Structural Diagnosis: Circuit Breaker + Retry Mechanism

## The Falsifiable Claim

**The circuit breaker observes service health through the only mechanism that affects service load: by attempting requests. Therefore, the observer constitutes what it observes. You cannot determine whether the service has recovered without attempting to serve it, and the attempt itself is the risk condition you're protecting against.**

More precisely: the state transition that matters (OPEN→HALF_OPEN→CLOSED) is driven by measurement, but measurement IS the intervention.

---

## Three Voices in Disagreement

**Defender (sustains the claim):**
This is exactly right. Look at the code: OPEN→HALF_OPEN happens on time alone (wall-clock). But HALF_OPEN→CLOSED happens only if `_success_count >= _half_open_max`, which requires successful executions. So every state decision depends on an execution that risked the failure condition the state machine exists to prevent. The code doesn't separate "testing if service recovered" from "making a request that might fail." They're identical.

**Attacker (challenges the framing):**
You're describing the circuit breaker as if it's trying to do something impossible. It's not. It's a standard pattern — gradually let traffic through in HALF_OPEN to test recovery. The observer-constitutive property is *the point*, not a hidden flaw. If you don't want to risk requests, use a separate health endpoint, but then you have a different problem (the health endpoint can lie). The code makes an honest trade-off: we learn the service is healthy by trying it.

**Probe (questions what both assume):**
Wait — you both agree the observation requires an attempt. So the question isn't whether it's observer-constitutive, but *whether that's actually what the code is doing*. Let me trace: OPEN→HALF_OPEN uses `time.time() - self._last_failure_time`. That's time-elapsed. It doesn't measure service health at all on entry. HALF_OPEN→CLOSED measures successes. So entry is **not** outcome-based; exit **is**. The state machine has two orthogonal decision criteria: time-based entry, outcome-based exit. This means the code can enter HALF_OPEN without any evidence the service recovered, then only afterward measure whether it actually did. That's a specific kind of observer-constitutivity: *you measure *after* you've already decided to trust.*

---

## Concealment Mechanism: Unobserved Entry Criterion

The code hides what it conceals through **temporal separation of decision from measurement**:

- **Hidden**: When OPEN→HALF_OPEN transition happens, it's based on elapsed time alone, not service state
- **Made to look innocent**: The HALF_OPEN state looks symmetric—it allows requests through, measures successes. Looks like careful gradual recovery.
- **Real structure**: The system enters HALF_OPEN on an assumption (time has passed, service might be back) then validates that assumption through attempted requests. The validation IS the risk.

---

## Apply the Mechanism: Engineer Improvement That Deepens Concealment

**Improvement A: "Intelligent Half-Open with Immediate Qualification"**

```python
def execute(self, fn, *args, **kwargs):
    if self._state == self.OPEN:
        if time.time() - self._last_failure_time > self._reset_timeout:
            # IMPROVEMENT: Transition directly to attempt qualification
            # This makes HALF_OPEN invisible—we skip straight to measuring recovery
            self._state = self.HALF_OPEN
            self._half_open_request_count = 0
            self._half_open_entry_time = time.time()
        else:
            raise Exception("Circuit is open")

    if self._state == self.HALF_OPEN:
        self._half_open_request_count += 1
        if self._half_open_request_count > self._half_open_max:
            # If any request in this batch failed, stay open
            raise Exception("Still failing—cannot close yet")
        
        # Execute immediately, treat outcome as readiness proof
        result = self._retry_with_backoff(fn, *args, **kwargs)
        
        # Only now count it as success
        self._on_success()
        if self._success_count >= self._half_open_max:
            self._state = self.CLOSED
            self._failure_count = 0
        
        return result
```

**Three properties visible because we tried to strengthen it:**

1. **The entry criterion was never a measurement.** By making the code more aggressive (skip HALF_OPEN existence, go straight to measurement), we reveal that the original HALF_OPEN state was doing two jobs: serving as a buffer zone (psychological / rate-limited), AND as a measurement zone. The improvement collapses these into one, exposing that the original's "gentleness" was orthogonal to its measurement function.

2. **The code measures outcome-sequences, not outcomes.** Original: "did this request succeed?" Improvement: "did this batch of requests not exceed threshold?" We now see the original's `_half_open_max` was actually counting consecutive successes—a *history*, not a state. The improvement forces us to explicitly count request volume, revealing that the original conflated "number of chances to fail" with "proof of recovery."

3. **Success is time-conflated.** In the improvement, the transition from "in HALF_OPEN" to "closed" happens immediately on the max-th success. Original had: success → increment → check threshold → transition. The improvement speeds this up and reveals: the original was implicitly assuming that time passing between success-1 and success-N was meaningful (the service was staying up). The improvement's immediate transition shows that assumption was invisible.

---

## Apply Diagnostic Recursively to the Improvement

**What does Improvement A conceal?**

It conceals the same observer-constitutive property it was supposed to fix. By removing the explicit HALF_OPEN buffer, we've only relocated the reflexivity into the request count logic. Now every request in the `_half_open_request_count < _half_open_max` zone IS a test and IS a service attempt, and we measure it through pure outcome.

**What property of the original is visible BECAUSE the improvement recreates the problem?**

The original code's honesty about the asymmetry. Original: time-based entry (hope the service recovered), outcome-based exit (prove it did). The hope is explicit—HALF_OPEN is a hope state. The improvement tries to remove the hope by being aggressive, but this reveals that the hope was actually doing work: it gave the service a recovery window before proving recovery. Without the hope-window, every single request in the qualification zone risks cascading failures if the service is still degraded.

---

## Engineer Second Improvement: Restore Decoupling

**Improvement B: "Decoupled Observation"**

```python
class CircuitBreakerWithDecoupledObservation:
    def __init__(self, failure_threshold=5, reset_timeout=30, 
                 half_open_max=3, health_check_fn=None):
        # ... standard init ...
        self._health_check_fn = health_check_fn  # Separate from execution
        
    def execute(self, fn, *args, **kwargs):
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                # Don't enter HALF_OPEN—check health independently first
                if self._health_check_fn and self._health_check_fn():
                    self._state = self.CLOSED
                    self._failure_count = 0
                else:
                    # Service not healthy—don't try yet
                    raise Exception("Circuit is open - health check failed")
            else:
                raise Exception("Circuit is open")
        
        # Normal execution with retry
        try:
            result = self._retry_with_backoff(fn, *args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _health_check_fn(self):
        """Example: separate lightweight endpoint"""
        try:
            requests.get("http://service/health", timeout=0.1)
            return True
        except:
            return False
```

---

## Apply Diagnostic to Second Improvement: Name the Invariant

**L10-C Structural Invariant:**

The design space has two orthogonal dimensions:

1. **Entry criterion**: Time-based vs. Outcome-based
2. **Exit criterion**: Time-based vs. Outcome-based (rarely used)

All four combinations are attempted across our three improvements:

| Entry | Exit | Problem |
|-------|------|---------|
| Time (Original) | Outcome | Observer-constitutive on exit: prove recovery by attempting |
| Outcome (Impr. A) | Outcome | Observer-constitutive on entry: must attempt to qualify |
| Outcome (Impr. B) | N/A | Observer-constitutive at metadata: health check IS an attempt |
| Time (Impr. B) | N/A | Observation independent of actual service |

**The invariant:** You cannot separate entry-observation from exit-observation without introducing a new observation point. Every attempt to decouple creates a new place where observer and observed must meet.

---

## Invert the Invariant: Name the New Impossibility

**Impossible property:** "Measure service recovery without risking that measurement."

**Invert it to trivial:** Use an observer external to the system being observed.

But this creates a new impossibility: **"Guarantee the external observer is measuring the same service the caller is attempting to reach."**

If your health check endpoint is on a different server, different load balancer, different datacenter, it might show the service is healthy while the caller's requests go to a degraded region.

---

## Conservation Law (L11-C)

**What persists across every design?**

$$\text{observational\_cost} \times \text{measurement\_independence} = k$$

Where:
- **observational_cost** = overhead of determining readiness (0 = passive timeout, 1 = single health request, 2 = multiple probes, 3 = separate health system)
- **measurement_independence** = probability that measurement predicts actual service health (1 = actual request, 0.5 = health endpoint, 0.3 = separate health system)

As you reduce observational cost by decoupling observer from observed, measurement independence drops because observer and observed can diverge.

---

## Apply Diagnostic to the Conservation Law Itself: What Does It Conceal?

**The law conceals that it's measuring TWO different quantities:**

1. The reliability of the observation *method* (health endpoint vs. actual request)
2. The reliability of the observation *timing* (does the observer see the same moment the observer will encounter?)

When observer and observed are identical (original design), these are the same. When they're separate (health endpoint), they can diverge: the health endpoint was correct at time T, but the main service degraded by time T+ε, and the caller's request happens at T+2ε.

**What's actually conserved:** The degree of coupling between observer's decision and observed's actual state.

- Original: highly coupled (request success = service is working)
- Health endpoint: decoupled (endpoint success ≠ main service success)

The law conceals this coupling-decoupling as a single variable "measurement reliability," when actually it's reflecting whether the observer participates in the system it observes.

---

## The Meta-Law (L12): The Conservation Law's Own Concealment

**What the conservation law conceals about THIS circuit breaker problem specifically:**

The law assumes the observer is independent of the risk. But in the circuit breaker, **the observer IS the risk mechanism**. Every HALF_OPEN request is simultaneously:
- A measurement of service health
- A request to the service
- A potential trigger for cascading failure

The conservation law treats these as independent, but they're not.

**The meta-law:** In any system where the observer and the intervention are the same mechanism, the conservation law `observational_cost × measurement_reliability = k` conceals a second, deeper conservation law:

$$\text{observer\_visibility} \times \text{intervention\_safety} = \text{constant}$$

Where:
- **observer_visibility** = how clearly you see why the observer made its decision
- **intervention_safety** = how guaranteed the intervention is to fail safely

**The testable consequence specific to this circuit breaker:**

If you instrument the circuit breaker to make decisions visible (add detailed logging: "Transitioning to HALF_OPEN due to timeout," "Closing circuit due to 3 successes"), you will notice that the success measurements in HALF_OPEN do not predict the request pattern that actually hits the service after the circuit closes. 

The requests that succeeded in HALF_OPEN (low volume, limited concurrency due to circuit filtering) are not representative of what happens when the circuit closes and traffic floods in. The more transparent your decision-making, the more visible this non-representativeness becomes.

**In other words: transparent circuit breaker logic reveals that HALF_OPEN measurements don't validate recovery under the actual load conditions the circuit is protecting against.**
