# Structure-First Analysis: Circuit Breaker Conservation Law

## Falsifiable Claim (Original)

**The deepest structural problem: Failure is not a unified observable.** The code counts failures in CLOSED state to answer "Is this service worki    -> Done (89s) -> 212 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/haiku_L11_conservation_law_task_K.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
ggers the retry loop (3 internal attempts), but counts as 1 failure to the circuit. If those retries exhaust, `_on_failure()` is called once. However, if the service is flaky but recovering, both CLOSED and HALF_OPEN can see failures, but `_failure_count` never resets in HALF_OPEN. So one failure in HALF_OPEN stays until timeout expires, trapping us."

**Attacker**: "Wait. That's not the deepest problem—that's a bug. The real issue is what the code *takes for granted*: that `_failure_count` and `_success_count` are observing the same underlying reality. But they're not. In CLOSED, you're measuring 'service availability.' In HALF_OPEN, you're measuring 'recovery hypothesis validity.' These are different things. The code looks like it has one state machine, but it's actually hosting two incompatible decision models."

**Prober**: "Both right, but you're both assuming the counters *mean* something. What are you taking for granted about what 'failure' IS? You've defined it by *when it happens*, not by *what it tests*. CLOSED failure means 'this service call didn't work.' HALF_OPEN failure means 'the recovery probe didn't work.' Same word, different observational target. The code never names this shift."

## Concealment Mechanism

**Semantic homogeneity of syntactic operations**: The same code paths (`self._failure_count += 1`) mean fundamentally different things in different contexts. The code *looks* unified because the operations are syntactically identical, but the semantics are fragmented. This is invisible because:
- The state machine structure appears organized
- The code doesn't document what is being counted in each state
- Happy paths work, so the fragmentation never surfaces

---

## Deepening Improvement (Legitimate, Makes Concealment Worse)

```python
def _on_failure(self):
    # NEW: Explicit state-dependent behavior
    if self._state == self.HALF_OPEN:
        self._state = self.OPEN  # Failure in recovery = immediate reopen
        self._last_failure_time = time.time()
    else:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._failure_threshold:
            self._state = self.OPEN
        
# Also reset in transition:
if self._state == self.OPEN:
    if time.time() - self._last_failure_time > self._reset_timeout:
        self._state = self.HALF_OPEN
        self._failure_count = 0  # NEW
        self._success_count = 0
```

**Why this deepens concealment**: By making the state-dependent branching *explicit*, we make the problem appear **solved** while actually **formalizing the semantic split**. The code now announces its fragmentation: "failure means different things here." This makes reviewers think "good, it's handling state-specific logic" when actually it's revealing that the abstraction is broken.

### Three Properties Now Visible

1. **Failure is not an observable fact; it's a state-dependent interpretation.** CLOSED failure → increment counter. HALF_OPEN failure → immediately revert hypothesis. Same event type, incommensurable responses.

2. **The circuit breaker runs two competing hypotheses simultaneously:**
   - CLOSED: "Assume the service works until proven otherwise"
   - HALF_OPEN: "Assume the service now works until proven otherwise"
   
   But they can't both count toward the same threshold—they're testing opposite defaults.

3. **The asymmetry is encoded in the threshold numbers, not the logic:** 5 failures to open, but 3 successes to close. This isn't symmetrical because the prior beliefs aren't symmetrical. The code obscures that these numbers are solving different inference problems.

---

## Second-Order Diagnostic (Applied to Improvement)

**What the improved code conceals**: That the circuit breaker isn't really a single state machine—it's a **switching system between two incompatible decision models**. The code now makes the switch *visible* but hides that the models themselves are misaligned.

**What becomes visible because of the improvement**: The state-specific branching reveals that success/failure recording has **no unified semantics**. It's not measuring "service health"—it's measuring "which hypothesis am I testing?" But that "which hypothesis" is implicit in the state, not explicit in the data.

---

## Second Improvement (Addresses Recreated Property)

```python
class StateSpecificObserver:
    """Extract the semantic drift into separate objects."""
    
    class ClosedStateObserver:
        def __init__(self, threshold):
            self.failure_count = 0
            self.threshold = threshold
        
        def record_success(self): 
            self.failure_count = 0
        
        def record_failure(self) -> bool:
            self.failure_count += 1
            return self.failure_count >= self.threshold

    class HalfOpenStateObserver:
        def __init__(self, recovery_threshold):
            self.success_count = 0
            self.recovery_threshold = recovery_threshold
        
        def record_success(self) -> bool:
            self.success_count += 1
            return self.success_count >= self.recovery_threshold
        
        def record_failure(self):
            # Failure in half-open doesn't accumulate
            return True  # "Revert immediately"

# Usage
self._closed_observer = StateSpecificObserver.ClosedStateObserver(5)
self._half_open_observer = StateSpecificObserver.HalfOpenStateObserver(3)

if self._state == "half_open":
    should_close = self._half_open_observer.record_success()
else:
    should_open = self._closed_observer.record_failure()
```

**Now the problem is explicit**: Success and failure have different types in different states. The objects have *incompatible APIs*. You can't call the same method with the same semantics.

---

## Third-Order Diagnostic

**What this reveals**: By separating the observers, we expose that **you cannot encode state-switching logic without making the state a first-class variable**. The improvement makes the state itself the control structure—every decision goes through an if/else on `self._state`. 

The code now hides: **That the state machine is just a proxy for a deeper problem—you're trying to make incompatible decisions using the same observation mechanism.**

---

## Structural Invariant (The Deep Pattern)

**INVARIANT: The circuit breaker must answer two questions with asymmetric evidence:**
- **CLOSED**: "Should we stop trying?" (Answer: when failures exceed threshold)
- **HALF_OPEN**: "Can we start trying again?" (Answer: when successes exceed recovery threshold)

These have **different base rates** (you need more proof of recovery than of failure), **different temporal windows** (CLOSED observes over multiple requests; HALF_OPEN has a timeout reset), and **different error costs** (false OPEN is bad; false CLOSE is worse). 

**Yet the code uses the same counting mechanism for both.**

The invariant is: **Total design coupling is conserved. You cannot reduce coupling in one dimension without increasing it in another.**

---

## Inverting the Invariant

What if we made the asymmetry the **primary structure**?

```python
class InvertedCircuitBreaker:
    """
    Inversion: Don't separate CLOSED/HALF_OPEN by state.
    Separate by observation window instead.
    """
    def __init__(self, fail_window=30, recover_window=10):
        self._fail_window = fail_window      # "Service broken if 5 failures in 30s"
        self._recover_window = recover_window # "Service recovered if 3 successes in 10s"
        self._failure_log = []   # (timestamp, event)
        self._success_log = []
        self._is_open = False
    
    def execute(self, fn, *args, **kwargs):
        try:
            result = self._retry_with_backoff(fn, *args, **kwargs)
            self._success_log.append(time.time())
            self._check_recovery()  # Check if recent successes close it
            return result
        except Exception as e:
            self._failure_log.append(time.time())
            self._check_failure()   # Check if recent failures open it
            if self._is_open:
                raise Exception("Circuit open")
            raise
    
    def _check_failure(self):
        now = time.time()
        recent_failures = [t for t in self._failure_log 
                          if now - t < self._fail_window]
        self._is_open = len(recent_failures) >= 5
    
    def _check_recovery(self):
        now = time.time()
        recent_successes = [t for t in self._success_log 
                           if now - t < self._recover_window]
        if self._is_open and len(recent_successes) >= 3:
            self._is_open = False
```

**What changed**: No explicit HALF_OPEN state. Recovery happens implicitly through the success window. Opening happens through the failure window.

**New impossibility created**: **You cannot distinguish between a service that's genuinely recovering vs. a service with sporadic transient successes.** The windows are time-based, not threshold-based. A single success in the recovery window counts toward closure, even if it's a false positive.

In the original design: "CLOSED watches, OPEN refuses, HALF_OPEN probes." You *know* when you're testing recovery.

In the inverted design: "Any success might be recovery." You *don't know* if you're testing or just getting lucky.

---

## Conservation Law

**THE FUNDAMENTAL CONSERVATION LAW:**

> **You cannot simultaneously optimize for (1) explicit refusal of failed requests, (2) unified observation of success/failure events, and (3) automatic recovery detection without hiding the mechanisms somewhere.**

| Approach | Visible | Hidden |
|----------|---------|--------|
| **Original (3-state)** | Explicit refusal (OPEN state), unified success/failure recording | Recovery semantics (what is HALF_OPEN really measuring?) |
| **Inverted (time-windowed)** | Explicit recovery logic (windows), automatic probing | Refusal mechanism (when do we stop trying?), false-positive sensitivity |
| **Extracted classes** | State-specific semantics, domain clarity | State becomes control structure (brittle), observation model fragmentation |

**Why this is conserved**: Because success/failure are not objective properties of events—they're **predictive judgments about which hypothesis is being tested**. An HTTP 500 is "failure" if you're testing "is the service up?" but "evidence of recovery" if you're testing "did our fix work?" The same event means different things in different contexts.

**Any circuit breaker must either:**
- Explicitly name the context (state machine) and hide what each state is really measuring → **Original approach**
- Implicitly define the context through observational windows and hide when the transition happens → **Inverted approach**
- Extract the context into objects and hide that the objects are incomparable → **Extracted classes approach**

**The conservation law**: The difficulty of making one thing explicit is exactly the difficulty you create by hiding it elsewhere. The code cannot escape this because it reflects the problem space's inherent asymmetry: **you must unify observations while keeping semantics distinct, or keep observations separate while unifying semantics. You cannot do both.**
