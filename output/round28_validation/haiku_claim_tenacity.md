Perfect. I'll apply the **claim lens** framework to Tenacity. Let me extract empirical claims, invert them, and trace corruption.

---

## EXTRACTED EMPIRICAL CLAIMS

### **Claim 1: Sleep Duration Equals Actual Delay**
**Embedded in:** `self.sleep(do)` + `idle_for` tracking + decision rules that use `delay_since_first_attempt`

**Assumption:** When you sleep(10ms), you wait 10ms. Retry timing is wall-clock observable.

**If false:**
- GC pause during sleep: you ask for 10ms, get 100ms
- `idle_for` says 10ms, reality is 100ms
- Decision rule: "stop if total_time > 500ms" fires at wrong attempt count
- Under high load: all sleeps compress by 10x, retry storms form unexpectedly

**Concrete corruption:** Rate limiter designed for "1s backoff between retries" gets preempted. Backoff becomes 50ms effective. Client hammers recovering database with 20x expected load.

---

### **Claim 2: State Transitions Are Instantaneous (Atomic)**
**Embedded in:** `retry_state.outcome = None → Future` (observable boundary)

**Assumption:** Between clearing outcome and setting it, no observer reads a half-done state.

**If false (under async/threading):**
- Thread A: `outcome = None` (clear for next attempt)
- [preemption]
- Thread B: `if outcome is None: do_next_action()` ← fires early
- Thread A: `outcome = Future(...)` ← too late, B already acted

**Concrete corruption:** Race between "prepare for next attempt" and "decide what to do." Observer thread reads None, thinks attempt hasn't started, schedules another attempt, original thread finally records the outcome. Result: double-attempts on same error.

---

### **Claim 3: Decisions Compose Linearly (retry ⊥ stop)**
**Embedded in:** `_run_retry()` called, then `_run_stop()` called separately

**Assumption:** "Should retry?" and "Should stop?" are independent. Evaluate both, combine results.

**If false:**
- `retry(TimeoutError)` = True (timeout occurred, want retry)
- `stop(after_attempt=3)` = True (3 attempts reached)
- **Implicit resolution: stop wins** (code checks stop second)
- User expected: "retry up to 3 times" (retry has priority)

**Concrete corruption:** On attempt 3, timeout occurs. Code:
```python
# _run_retry: True (timeout, want retry)
# _run_stop: True (attempt limit, want stop)
# Result: raises RetryError on attempt 3
# But user logic expected attempt 3 to succeed with one final retry
```

Decision composition has hidden priority order (`stop > retry`) not visible in user code. Silent semantic violation of retry specification.

---

### **Claim 4: Exceptions Contain Full Error State**
**Embedded in:** `set_exception(exc_info[1])` — only uses exception, discards traceback

**Assumption:** Exception object is self-contained. Traceback is redundant for reraise.

**If false:**
```python
# Original failure at line 42 (SQL error)
# After reraise through RetryError:
raise self.last_attempt.result()
# Traceback now points to reraise() call, not line 42
```

**Concrete corruption:** Debug stack trace loses original failure site. SQL error on line 42 shows as "error in tenacity.py line 88." Developer spends hours debugging wrong line of code.

---

### **Claim 5: Thread-Local Storage Solves Concurrency**
**Embedded in:** `self._local = threading.local()` for statistics + iter_state

**Assumption:** Each thread gets isolated dict. Shared Retrying instance safe across threads.

**If false:**
```python
# Single Retrying instance shared:
r = Retrying(stop=stop_after_attempt(3))

# Thread A:
copy = r.copy()  # A gets local statistics
wrapped_f.statistics = copy.statistics

# Thread B:
copy = r.copy()  # B gets local statistics  
wrapped_f.statistics = copy.statistics  # Overwrites A's reference!

# Thread A reads wrapped_f.statistics: sees B's data
```

**Concrete corruption:** Metrics are crossed. Thread A thinks it retried 5 times, but the counter shows 2 (Thread B's count). SLA validation wrong, alerts fire incorrectly.

---

### **Claim 6: Actions Execute in Deterministic Order**
**Embedded in:** `for action in self.iter_state.actions: result = action(retry_state)`

**Assumption:** Build action list → execute serially → all actions complete.

**If false:**
```python
# If action throws mid-list:
self._add_action_func(self.retry_error_callback)  # throws!
self._add_action_func(exc_check)  # never runs!
# Result: exception suppressed, execution continues
# Silent failure — no exception raised at all
```

**Concrete corruption:** Callback throws an error indicating a critical condition (e.g., quota exceeded), but the exception never propagates. Code silently continues, violates SLA, loses money.

---

### **Claim 7: Copy Reproduces Semantics**
**Embedded in:** `self.copy(sleep=_unset, ...)`

**Assumption:** Creating new Retrying with same parameters = same behavior.

**If false (strategies with closures):**
```python
attempt_counter = 0
def my_retry(rs):
    global attempt_counter
    attempt_counter += 1
    return attempt_counter < 5

r = Retrying(retry=my_retry)
r1 = r.copy()  # B strategy still references same global
r2 = r.copy()  # Both share attempt_counter!

# Call r1: counter goes 1,2,3,4
# Call r2: counter goes 5,6,7 (starts at 4!)
```

**Concrete corruption:** When you copy a Retrying config to reuse it, shared mutable state leaks. First invocation uses all attempts, second invocation fails immediately.

---

### **Claim 8: Statistics Are Write-Once Read-After-Write Consistent**
**Embedded in:** `statistics["attempt_number"] += 1`

**Assumption:** Counter increments are atomic. Aggregate counts are monotonic and accurate.

**If false (races under contention):**
```
Thread A: read attempt_number (3)
Thread B: read attempt_number (3)
Thread A: increment to 4, write
Thread B: increment to 4, write
Actual increment: only +1, not +2
```

**Concrete corruption:** Retry count off by 50% under concurrency. Audit logs show 5 retries but actually 10 happened. Compliance violations.

---

## THREE ALTERNATIVE DESIGNS (Inverting Key Claims)

---

### **ALTERNATIVE A: Inverted Claim 1 — Actual Delay ≠ Sleep Duration**

**Design:** Measure actual elapsed time between attempts, not requested sleep time.

```python
class Retrying_MeasuredTime(BaseRetrying):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actual_delays = {}  # attempt_number -> measured_delay
    
    def __call__(self, fn, *args, **kwargs):
        self.begin()
        retry_state = RetryCallState(retry_object=self, fn=fn, args=args, kwargs=kwargs)
        
        while True:
            pre_iter = time.perf_counter()
            do = self.iter(retry_state=retry_state)
            iter_elapsed = time.perf_counter() - pre_iter
            
            if isinstance(do, DoAttempt):
                pre_attempt = time.perf_counter()
                try:
                    result = fn(*args, **kwargs)
                except BaseException:
                    retry_state.set_exception(sys.exc_info())
                else:
                    retry_state.set_result(result)
                attempt_elapsed = time.perf_counter() - pre_attempt
                # Record actual attempt time, not just call time
                self.statistics[f"attempt_{retry_state.attempt_number}_duration"] = attempt_elapsed
                
            elif isinstance(do, DoSleep):
                pre_sleep = time.perf_counter()
                self.sleep(do)
                actual_sleep = time.perf_counter() - pre_sleep
                # Record actual sleep vs requested sleep
                self.actual_delays[retry_state.attempt_number] = {
                    "requested": float(do),
                    "actual": actual_sleep,
                    "drift": actual_sleep - float(do)
                }
                # Adjust upcoming timeouts based on actual drift
                if actual_sleep > float(do) * 1.5:  # 50% drift detected
                    retry_state.upcoming_sleep *= 0.9  # Reduce next sleep
                
                retry_state.prepare_for_next_attempt()
            else:
                return do
```

**Concrete result:** Under GC pauses, system detects "actual sleep was 100ms, requested 10ms" and automatically compensates. Next retry backs off less because system knows scheduling is unpredictable. Retry storms prevented.

**What this reveals:** **The original assumes OS is honest about timing.** Tenacity delegates timing to `time.sleep()` with no visibility into actual delays. Real systems experience dramatic timing variance. The original's `idle_for` is a fiction when GC/scheduling interferes.

---

### **ALTERNATIVE B: Inverted Claim 3 — Decisions Do NOT Compose Linearly**

**Design:** Explicit conflict resolution. If retry and stop both true, consult a priority rule.

```python
class Retrying_ExplicitComposition(BaseRetrying):
    def __init__(self, *args, conflict_resolution="stop", **kwargs):
        # conflict_resolution: "stop", "retry", "explicit_callback"
        super().__init__(*args, **kwargs)
        self.conflict_resolution = conflict_resolution
        self.on_conflict = None  # User-provided arbiter
    
    def _post_stop_check_actions(self, retry_state):
        """Modified to detect and resolve retry/stop conflicts."""
        retry_result = self.iter_state.retry_run_result
        stop_result = self.iter_state.stop_run_result
        
        # Detect conflict
        if retry_result and stop_result:
            # Both true: conflict!
            if self.conflict_resolution == "explicit_callback":
                # Let user decide
                self._add_action_func(self.on_conflict)  # user callback decides
                return
            elif self.conflict_resolution == "retry":
                # Ignore stop, force retry
                def force_retry(rs):
                    rs.next_action = RetryAction(rs.upcoming_sleep)
                    self.statistics["conflicts_resolved_as_retry"] += 1
                self._add_action_func(force_retry)
                return
            elif self.conflict_resolution == "stop":
                # Original behavior: stop wins
                pass  # Continue to original code
        
        # Original behavior if no conflict
        if stop_result:
            if self.retry_error_callback:
                self._add_action_func(self.retry_error_callback)
                return
            def exc_check(rs):
                fut = rs.outcome
                retry_exc = self.retry_error_cls(fut)
                if self.reraise:
                    retry_exc.reraise()
                raise retry_exc from fut.exception()
            self._add_action_func(exc_check)
            return
        
        # Original: next attempt
        def next_action(rs):
            sleep = rs.upcoming_sleep
            rs.next_action = RetryAction(sleep)
            rs.idle_for += sleep
            self.statistics["idle_for"] += sleep
            self.statistics["attempt_number"] += 1
        
        self._add_action_func(next_action)
        if self.before_sleep is not None:
            self._add_action_func(self.before_sleep)
        self._add_action_func(lambda rs: DoSleep(rs.upcoming_sleep))
```

**Concrete result:**
```python
# User specifies priority:
r = Retrying_ExplicitComposition(
    retry=retry_if_exception_type(TimeoutError),
    stop=stop_after_attempt(3),
    conflict_resolution="retry"  # If both true, retry wins
)
```

On attempt 3 with timeout: both retry and stop are true. Instead of raising RetryError, it retries anyway. User's intent is honored.

**What this reveals:** **The original hides composition strategy.** Retry and stop are evaluated independently but combined with implicit priority (stop > retry). Users don't control this. The original buries the precedence rule inside `_post_stop_check_actions`, making it invisible to callers who read only the public API.

---

### **ALTERNATIVE C: Inverted Claim 2 — State Transitions Are NOT Atomic**

**Design:** Explicit state machine with observable intermediate states.

```python
from enum import Enum

class AttemptState(Enum):
    PENDING = "pending"        # No attempt yet
    IN_FLIGHT = "in_flight"    # Currently executing
    COMPLETED = "completed"    # Attempt finished
    RECORDED = "recorded"      # Outcome recorded
    
class RetryCallState_Explicit(RetryCallState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attempt_state = AttemptState.PENDING
    
    def set_result(self, val):
        # Explicit state transitions
        if self._attempt_state != AttemptState.IN_FLIGHT:
            raise RuntimeError(f"Cannot record result in state {self._attempt_state}")
        
        ts = time.monotonic()
        fut = Future(self.attempt_number)
        fut.set_result(val)
        
        self._attempt_state = AttemptState.COMPLETED  # transition
        self.outcome = fut
        self.outcome_timestamp = ts
        self._attempt_state = AttemptState.RECORDED  # final state
    
    def set_exception(self, exc_info):
        if self._attempt_state != AttemptState.IN_FLIGHT:
            raise RuntimeError(f"Cannot record exception in state {self._attempt_state}")
        
        ts = time.monotonic()
        fut = Future(self.attempt_number)
        fut.set_exception(exc_info[1])
        
        self._attempt_state = AttemptState.COMPLETED
        self.outcome = fut
        self.outcome_timestamp = ts
        self._attempt_state = AttemptState.RECORDED
    
    def prepare_for_next_attempt(self):
        if self._attempt_state != AttemptState.RECORDED:
            raise RuntimeError(f"Cannot prepare next attempt in state {self._attempt_state}")
        
        self.outcome = None
        self.outcome_timestamp = None
        self.attempt_number += 1
        self.next_action = None
        self._attempt_state = AttemptState.PENDING

class Retrying_ExplicitStates(BaseRetrying):
    def __call__(self, fn, *args, **kwargs):
        self.begin()
        retry_state = RetryCallState_Explicit(retry_object=self, fn=fn, args=args, kwargs=kwargs)
        
        while True:
            retry_state._attempt_state = AttemptState.IN_FLIGHT  # Mark as in-flight
            
            do = self.iter(retry_state=retry_state)
            if isinstance(do, DoAttempt):
                try:
                    result = fn(*args, **kwargs)
                except BaseException:
                    retry_state.set_exception(sys.exc_info())
                else:
                    retry_state.set_result(result)
            elif isinstance(do, DoSleep):
                retry_state.prepare_for_next_attempt()
                self.sleep(do)
            else:
                return do
```

**Concrete result:** Any thread trying to read `outcome` while state is `IN_FLIGHT` gets an error or can check state explicitly:
```python
if retry_state._attempt_state == AttemptState.IN_FLIGHT:
    # Wait for attempt to complete
    while retry_state._attempt_state != AttemptState.RECORDED:
        time.sleep(0.001)
result = retry_state.outcome
```

This prevents the race where Thread B reads outcome during Thread A's `set_exception()`.

**What this reveals:** **The original conflates "outcome is None" with "no attempt yet."** That works in single-threaded code but breaks under async. The original assumes state is observable only at stable points, but doesn't enforce that. Intermediate states exist (during `set_exception` assignment) but are invisible. Moving to explicit state machine makes atomicity constraints visible and checkable.

---

## CORE IMPOSSIBILITY

Tenacity tries to optimize:

**"Compose retry strategies without losing observability, thread-safety, or user control"**

But this is impossible under:
- **Timing variance** (OS doesn't honor sleep durations)
- **Concurrency** (observers can't see atomic state boundaries)
- **Conflicting constraints** (retry vs stop can both be true)

The artifact chooses to solve this by:
1. **Delegating timing to OS** (assumes honesty; fails on GC)
2. **Using thread-local storage** (hides coordination; fails on shared instances)
3. **Implicit decision precedence** (stop > retry; not visible to users)

Each choice optimizes for simplicity at the cost of hidden failure modes.

---

## SLOWEST, MOST INVISIBLE FAILURE

**Claim 3: Decisions Compose Linearly (stop ⊥ retry)**

This is the slowest, most invisible failure because:

1. **It only manifests under specific conditions:** Timeout + attempt limit both true simultaneously. Not every retry path hits this.

2. **The silent semantic violation:** Code runs successfully, no exception, user code gets RetryError when it expected success. The decision happened invisibly.

3. **Detection is impossible:** Metrics show "retry logic fired" and "stop logic fired" but don't show that one was silently overridden. `statistics` dict doesn't record conflicts.

4. **It doesn't crash or warn.** The code returns RetryError with proper traceback — everything looks correct. But semantically, it violated the retry specification.

5. **Production impact is delayed:** The bug might take weeks to surface. Only when timeout + limit coincide at user's threshold does it appear, under load, at 3am.

**Concrete slowness:** Under normal conditions (timeouts before limit), code works. Add load (timeouts take longer), now timeouts and limit both trigger. Silent semantic flip. Debugging requires reconstructing the race condition, which is non-deterministic.

---

## SUMMARY TABLE

| Claim | If False | Corruption | Invisible? |
|-------|----------|-----------|-----------|
| Sleep = Delay | GC pause compresses timing | Retry storms form unexpectedly | Medium (affects metrics) |
| States atomic | Thread reads mid-transition | Double-attempts or missed attempts | **HIGH** (rare race) |
| Decisions linear | Both retry + stop true | Stop silently wins, user expects retry | **HIGHEST** (deterministic but hidden) |
| Exceptions complete | Traceback lost | Stack traces point to wrong line | Medium (frustrating, not invisible) |
| Thread-local safe | Shared reference | Metrics crossed between threads | Medium (shows in dashboards) |
| Copy semantic | Closures share state | Second copy reuses attempts | High (deterministic) |

**The original architecture optimizes for simplicity (implicit behavior) at the cost of hidden semantics (retry/stop composition, timing assumptions, atomicity boundaries). None of these failures cause crashes — they cause silent specification violations.**
