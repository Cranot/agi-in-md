# Structure First: Circuit Breaker / Retry Diagnostic

## The Claim

**Falsifiable claim:** The deepest structural problem is that the retry mechanism and circuit breaker are architecturally entangled such that each one systematically undermines the other's contract — the circuit breaker's state machine reasons about compressed, fictitious "call outcomes" while real backend failures go unobserved. The circuit breaker is not broken-open; it is running on hallucinated data.

---

## Three Expert Interrogation

```
┌──────────────────────────────────────────────────────────────────┐
│  EXPERT A: DEFENDER                                              │
│                                                                  │
│  "The claim stands. The retry loop is a lie detector             │
│  buried inside the truth-teller. _on_failure() fires once       │
│  per execute() call regardless of how many backend              │
│  invocations occurred inside _retry_with_backoff. With          │
│  max_retries=3 and failure_threshold=5, you need 15             │
│  real backend failures to open the circuit. The threshold       │
│  you configured is not the threshold you got."                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  EXPERT B: ATTACKER                                              │
│                                                                  │
│  "Too narrow. The entanglement is a symptom. The actual          │
│  production failure mode is race conditions. _state,            │
│  _failure_count, _success_count, _last_failure_time — all       │
│  mutated without locks. Under concurrency, two threads          │
│  can both pass the OPEN check, both decrement, both             │
│  transition. The circuit breaker doesn't exist under            │
│  load. You're analyzing a single-threaded fiction."             │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  EXPERT C: PROBER                                                │
│                                                                  │
│  "Both of you accept an assumption: that 'failure' means        │
│  the same thing to both mechanisms. It doesn't. A retry         │
│  failure is: transient, retriable, expected. A circuit          │
│  breaker failure is: persistent, service-down, systemic.        │
│  These are not the same event wearing the same name.            │
│  The code shares an exception path between semantically         │
│  incompatible failure ontologies. Before you argue about        │
│  counts or locks, ask: what IS a failure here?"                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## The Transformation

| | Original Claim | Transformed Claim |
|---|---|---|
| **Focus** | Structural entanglement | Semantic ambiguity |
| **Level** | Architectural | Ontological |
| **Diagnosis** | Wrong arrangement | Undefined meaning |
| **Fix would require** | Moving retry outside CB | Defining failure taxonomy first |

**The Gap:** The original claim was about *where* things live. The transformed claim is that things cannot be properly placed because it has never been decided *what they are*. Arrangement problems are downstream of identity problems.

---

## The Concealment Mechanism

**Name: Exception Transparency as Epistemic Laundering**

Python's exception propagation looks honest. The exception that reaches `_on_failure()` is real. The re-raise in `execute` is genuine. Code review sees correct error handling at every line. What's invisible is that by the time a legitimate exception surfaces to the circuit breaker, it has already been laundered through 1–3 retry attempts — real backend failures that the circuit breaker will never see.

The mechanism conceals by making the **path** look correct while the **count** is wrong. Every individual line passes inspection. The lie lives in the composition.

```
Backend reality:         F  F  F | F  F  F | F  F  F | F  F  F | F  F  F
                         ↑retry1↑   ↑retry2↑   ↑retry3↑   ↑retry4↑   ↑retry5↑

Circuit breaker sees:      ✗          ✗          ✗          ✗          ✗
                                                                        ↑ opens HERE

Actual failures at open:  15 backend failures observed as 5
Configured threshold:      5
Effective threshold:       15
```

---

## The Trojan Improvement

This passes code review. It looks like it adds observability and properly separates retry-level failures from circuit-breaker-level failures.

```python
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
        # NEW: separate granular retry telemetry from circuit-level outcomes
        self._transient_failure_count = 0
        self._exhausted_failure_count = 0

    def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
        last_exc = None
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_exc = e
                # NEW: track each individual backend failure for observability
                self._transient_failure_count += 1
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(delay)
        # NEW: only count as circuit-level failure when retries exhausted
        self._exhausted_failure_count += 1
        raise last_exc

    def get_stats(self):
        """Expose telemetry for monitoring dashboards."""
        return {
            "state": self._state,
            "circuit_failures": self._failure_count,
            "transient_failures": self._transient_failure_count,
            "exhausted_failures": self._exhausted_failure_count,
            "retry_amplification": (
                self._transient_failure_count / self._exhausted_failure_count
                if self._exhausted_failure_count else 0
            )
        }
```

**Why this passes review:**
- Names distinguish "transient" from "exhausted" — looks like proper taxonomy
- `last_exc` preserves original exception type — looks like better error handling
- `get_stats()` exposes a dashboard metric — looks like engineering maturity
- `retry_amplification` ratio sounds sophisticated and diagnostic

**Why this deepens the concealment:**

The `retry_amplification` metric makes reviewers feel the problem is *monitored*, which suppresses the intuition that it might be *structural*. Naming a problem and measuring it creates the cognitive illusion that it is being managed. The ratio is real data about a real problem — and it will never trigger any automated action because it feeds nothing.

---

## Three Properties Only Visible Because I Tried to Strengthen It

### 1. The ratio is load-geometry-dependent, not health-dependent

When I added `retry_amplification`, I had to think about what it measures. It measures the *retry configuration*, not service health. A service that fails on attempt 1 consistently gives amplification=3. A service that fails on attempt 3 consistently gives amplification=1. Same service reliability. Different circuit breaker behavior. The metric appears diagnostic but is actually a function of `max_retries`, not the thing you're trying to observe.

### 2. The fix requires structural surgery, not addition

Adding counters revealed that you cannot fix the semantic conflation by adding more counters *inside* the class. Every fix I tried to apply from within `_retry_with_backoff` deepened the problem. Proper separation requires moving retry outside the circuit breaker entirely — making them composable layers rather than nested internals. The improvement made the impossibility of internal repair visible: **the problem cannot be patched; it can only be dissolved**.

### 3. HALF_OPEN is accidentally correct and structurally broken simultaneously

When engineering the Trojan fix, I traced the HALF_OPEN path with separate counters and noticed: HALF_OPEN re-opens on failure because `_failure_count` was never reset when entering HALF_OPEN — only `_success_count` was reset. It works *by accident*. The code relies on `_failure_count` already being >= threshold, so adding 1 more trips it back. But if `failure_threshold` were ever lowered in production (a common tuning operation), the HALF_OPEN → OPEN transition could silently stop working. The "correct" behavior is load-bearing technical debt invisible until you trace the counter lifecycle to add new instrumentation.

---

## The Actual Repair Surface

```
┌─────────────────────────────────────────────────────┐
│  LAYER         CONCERN           MUST BE SEPARATE   │
├─────────────────────────────────────────────────────┤
│  Retry         Transient faults  classify exception │
│                                  types explicitly   │
├─────────────────────────────────────────────────────┤
│  Circuit       Persistent faults count real backend │
│  Breaker                         invocations, not   │
│                                  execute() calls    │
├─────────────────────────────────────────────────────┤
│  Threading     Shared state      threading.Lock()   │
│                mutation          or atomic ops      │
├─────────────────────────────────────────────────────┤
│  HALF_OPEN     State entry       explicit reset of  │
│  transition    invariants        _failure_count=0   │
└─────────────────────────────────────────────────────┘
```

The diagnostic: this code is a retry mechanism that learned to impersonate a circuit breaker. It dresses in the right vocabulary and state names, but its internal clock ticks on a unit of measurement that doesn't correspond to any phenomenon in the external system. That's the concealment — it looks like a circuit breaker because it has the right words. It isn't one because it counts the wrong things.
