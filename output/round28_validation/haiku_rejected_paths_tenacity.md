I'll apply the **rejected_paths** lens directly — mapping the fix→new-bug dependency graph across the codebase's core decisions.

---

## **CONCRETE PROBLEM → REJECTED PATHS → INVISIBLE CONSEQUENCES**

### **Problem 1: State Ownership Through Callback Mutations**

**Visible symptom:**
```python
self.statistics["idle_for"] += sleep  # Mutated in _post_stop_check_actions
self.statistics["attempt_number"] += 1  # But also in next_action()
```
Statistics are modified both by the retry loop AND by user callbacks. Which thread owns the data?

**Design chosen: threading.local() + public dict**
- ✓ Thread-safe by isolation
- ✓ Callbacks can read statistics
- ✗ Creates: **Implicit ownership ambiguity** — The state is "mine, but I'm giving callbacks access to it"

**Rejected Path A: Explicit state transactions**
```python
# Inside iter(): snapshot, call callback, merge back
stats_before = self.statistics.copy()
self.after(retry_state)  # callback runs
if self.statistics != stats_before:
    raise RuntimeError("Callback modified statistics!")
```
- Visible problem: Fails hard if callbacks need to modify state
- Invisible problem it would create: Users can't instrument retry behavior without subclassing

**Rejected Path B: Read-only statistics view**
```python
self.statistics = ReadOnlyDict(actual_stats)
```
- Visible problem: Callbacks can't track state they care about
- Invisible problem: Forces separate user-owned instrumentation, code duplication

**THE INVISIBLE PROBLEM CREATED by chosen path:**

When a callback modifies `statistics`, it's not clear:
- Should it mutate before or after the decision point?
- Does `retry_object.statistics` in the callback reflect the real retry state?
- What happens if the callback crashes — were statistics already incremented?

```python
# User writes:
def log_attempt(retry_state):
    stats = retry_state.retry_object.statistics
    stats["custom_failures"] = stats.get("custom_failures", 0) + 1

# This reads "attempt_number" but when?
# Before or after retry_loop incremented it?
```

**When visible under pressure:** 
- Custom metrics code logs attempt #5 three times because it runs in `before`, `after`, and `before_sleep`
- Statistics show idle_time > total_time due to callback overhead
- Concurrent access: one thread's callback reads another thread's copy of old statistics via timing race

---

### **Problem 2: Action Chain Volatility**

**Visible symptom:**
```python
def _begin_iter(self, retry_state):
    self.iter_state.reset()  # Blow away actions
    # Conditionally rebuild based on outcome
    if fut is None:  # First attempt
        if self.before is not None:
            self._add_action_func(self.before)
    else:  # Retry
        self.iter_state.is_explicit_retry = fut.failed and isinstance(...)
        if not self.iter_state.is_explicit_retry:
            self._add_action_func(self._run_retry)
    self._add_action_func(self._post_retry_check_actions)
```

The action chain is rebuilt every iteration. Decision points use flags (`is_explicit_retry`, `retry_run_result`) set in *previous* actions to decide what to add.

**Design chosen: Dynamic action chain built from state flags**
- ✓ Allows conditional flows (don't call retry() if TryAgain)
- ✓ Allows callbacks to influence retry logic indirectly
- ✗ Creates: **State dependency across action boundaries** — later actions depend on flags set by earlier actions

**Rejected Path A: Recursive decision tree**
```python
def iter(retry_state):
    if outcome is None:
        before()
        return DoAttempt()
    elif should_retry(outcome):
        after()
        sleep_duration = wait(outcome)
        if stop(outcome):
            raise RetryError()
        return DoSleep(sleep_duration)
    else:
        return outcome.result()
```
- Visible problem: Less flexible, harder to interpose
- Invisible problem: Deeply nested conditionals, callback order hardcoded, no way to customize without editing code

**Rejected Path B: Persistent action DAG**
```python
# Define once, execute many times
actions = [before, DoAttempt, retry_check, after_if_retry, wait, stop_check, ...]
```
- Visible problem: Can't conditionally skip actions based on outcome
- Invisible problem: Explosion of action states for all combinations (exponential branching)

**THE INVISIBLE PROBLEM CREATED by chosen path:**

The flags that control action flow (`iter_state.retry_run_result`, `iter_state.is_explicit_retry`) are:
1. Set by action methods (`_run_retry` sets `retry_run_result`)
2. Read by other action methods (`_post_retry_check_actions` reads it)
3. Reset before the next cycle

But the action methods also receive `retry_state` as parameter. If a callback modifies `retry_state.outcome`, the next cycle's decision logic changes, but the flag inversion might not track it:

```python
# Callback does:
def custom_after(retry_state):
    if some_condition:
        retry_state.outcome = None  # Reset to force retry
        
# Next iter(), fut = retry_state.outcome is None
# So we skip _run_retry() and go straight to first-attempt path
# But iter_state flags still think we're in retry mode
```

**When visible under pressure:**
- A monitoring callback clears the outcome to force re-evaluation
- The retry loop's decision logic doesn't re-run because it's flag-driven
- The callback works once, fails the second time (flag-state mismatch)
- Debug logs show contradictory state: "is_explicit_retry=True but outcome is None"

---

### **Problem 3: Exception Semantics Collapse**

**Visible symptom:**
```python
class AttemptManager:
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None and exc_value is not None:
            self.retry_state.set_exception((exc_type, exc_value, traceback))
            return True  # ← Suppress exception!
        self.retry_state.set_result(None)
        return None  # ← Don't suppress
```

When an exception occurs, it's captured and suppressed. When no exception, the result is captured. Both are correct. But the return values (True/False) have opposite meanings:
- `return True` = suppress, exception is swallowed
- `return None` (≈False) = don't suppress, execution continues

**Design chosen: Exception swallowing in __exit__, exception available later in retry_state**
- ✓ Enables retry loop to control the exception
- ✓ No try/except nesting needed
- ✗ Creates: **Exception visibility inversion** — exception exists but isn't visible until retry logic inspects it

**Rejected Path A: Re-raise immediately**
```python
def __exit__(self, ...):
    if exc_type is not None:
        self.retry_state.set_exception((exc_type, exc_value, traceback))
        raise  # Re-raise, don't suppress
```
- Visible problem: Exception propagates, code doesn't continue to retry decision
- Invisible problem: No retry happens, which defeats the purpose

**Rejected Path B: Let exception propagate, catch at top level**
```python
def __call__(self, fn, *args, **kwargs):
    while True:
        try:
            result = fn(*args, **kwargs)
        except Exception as e:
            if should_retry(e):
                continue
            raise
```
- Visible problem: Exception is visible immediately, but user code might catch it before retry logic
- Invisible problem: Multiple exception handling layers, cleanup logic needs to be in finally blocks

**THE INVISIBLE PROBLEM CREATED by chosen path:**

Exception visibility is now **bound to retry state**. An exception exists somewhere (in `retry_state.outcome`), but:
- It's not on the call stack
- It's not in `sys.exc_info()`
- It won't trigger `finally` blocks until retry logic retrieves it
- Cleanup code that depends on exception propagation breaks

```python
# User code does:
with contextmanager_that_cleans_up():
    with AttemptManager(retry_state):
        raise SomeError()  # Suppressed!

# cleanup_up() never runs because no exception propagated
# But retry_state.outcome has the exception, and retry logic will re-raise it
# 3 iterations later, when the exception is actually handled
```

**When visible under pressure:**
- Cleanup code assumes "if exception in this block, cleanup now"
- But exception is invisible, so cleanup doesn't run
- 3 retries later, the exception is raised and cleanup happens late
- Resource leaks: file handles, locks, temporary files created before the exception remain open during retries
- The exception traceback points to the 3rd retry, not the original failure

---

### **Problem 4: Timing Attribution Breaks**

**Visible symptom:**
```python
def set_result(self, val):
    ts = time.monotonic()  # ← Timestamp at outcome
    fut = Future(self.attempt_number)
    fut.set_result(val)
    self.outcome, self.outcome_timestamp = fut, ts

@property
def seconds_since_start(self):
    if self.outcome_timestamp is None:
        return None
    return self.outcome_timestamp - self.start_time  # ← Wall time
```

Timing is captured at `set_result` (when the attempt ends), and wall-clock time includes everything: function runtime + exception handling + callback overhead.

**Design chosen: Single timestamp at outcome, separate `idle_for` for sleep durations**
- ✓ Simple, no overhead
- ✓ Sleep time is explicitly tracked
- ✗ Creates: **Unaccounted time ghost** — Total time - Sleep time ≠ Actual work

**Rejected Path A: Dual timestamps (start + end of attempt)**
```python
def set_result(self, val):
    self.outcome_timestamp_end = time.monotonic()
    # But when is outcome_timestamp_start?
    # Before fn()? After exception handling?
```
- Visible problem: Where does "attempt start" occur? Multiple choices, no clear answer
- Invisible problem: Still doesn't account for callback overhead

**Rejected Path B: Hierarchical timers**
```python
# Track separately:
- attempt_duration
- callback_duration  
- sleep_duration
- framework_overhead
```
- Visible problem: More state, more timestamp calls, cache-line contention
- Invisible problem: Makes simple "how long did this retry take?" harder to answer

**THE INVISIBLE PROBLEM CREATED by chosen path:**

The statistics claim to track timing, but they only track:
- `delay_since_first_attempt` = wall time from start to now
- `idle_for` = total sleep time

This implies: `work_time = delay_since_first_attempt - idle_for`

But the actual breakdown is:
- Actual function runtime
- Exception raising + capturing
- `before()` callback overhead
- `after()` callback overhead
- `wait()` calculation
- `stop()` calculation  
- `before_sleep()` callback overhead
- Framework bookkeeping

Only the actual function runtime is "work". Everything else is overhead. But it's lumped into "work_time".

```python
# User checks:
stats = retry_object.statistics
print(f"Work: {stats['delay_since_first_attempt'] - stats['idle_for']}")

# Output: 0.5 seconds
# But the actual function ran for 0.1 seconds
# 0.4 seconds was callback overhead and exception handling
# The user thinks their function is 5x slower than it is
```

**When visible under pressure:**
- A callback is suspected of being slow, but the statistics show overhead as part of "work time"
- Profiling shows the callback takes 5ms, but statistics attribute 50ms to it
- User removes the callback expecting speedup, sees none, doesn't realize the overhead was in exception handling
- They add another callback, now two callbacks in the blame zone
- SLA metrics fail not because of function runtime, but because of framework overhead, invisible in statistics

---

### **Problem 5: Callback Semantics Drift**

**Visible symptom:**
```python
def _begin_iter(self, retry_state):
    fut = retry_state.outcome
    if fut is None:  # ← First attempt
        if self.before is not None:
            self._add_action_func(self.before)
    # ...
    
def _post_retry_check_actions(self, retry_state):
    if not (self.iter_state.is_explicit_retry or self.iter_state.retry_run_result):
        # ← No retry needed, return result immediately
        self._add_action_func(lambda rs: rs.outcome.result())
        return
    # ← Only execute if we're retrying:
    if self.after is not None:
        self._add_action_func(self.after)
```

The `before` callback fires on the first attempt. The `after` callback fires only if we're retrying. But their names don't distinguish between "after attempt" vs "after failed attempt".

**Design chosen: Implicit callback firing rules**
- ✓ Simple API, few parameters
- ✓ Makes sense for common case (retry logic)
- ✗ Creates: **Callback semantics ambiguity** — when do callbacks fire?

**Rejected Path A: Explicit callback phases**
```python
class RetryPhase(Enum):
    BEFORE_FIRST = 1
    BEFORE_RETRY = 2
    AFTER_ATTEMPT = 3
    AFTER_RETRY = 4
    ON_GIVE_UP = 5

# User specifies:
retry(
    callbacks=[
        (RetryPhase.BEFORE_FIRST, my_before),
        (RetryPhase.AFTER_RETRY, my_after),
    ]
)
```
- Visible problem: API is more verbose, users have to understand phases
- Invisible problem: Phase confusion (which phase does my callback belong in?)

**Rejected Path B: Callback receives phase indicator**
```python
def my_callback(retry_state, phase):
    if phase == "after_attempt":
        ...
    elif phase == "after_retry":
        ...

retry(after=my_callback)  # Callback decides what to do
```
- Visible problem: User has to check phase in every callback
- Invisible problem: Callbacks are no longer simple functions, they're state machines

**THE INVISIBLE PROBLEM CREATED by chosen path:**

The callback names don't match their actual firing rules:

| Callback | Name suggests | Actually fires when | User expects |
|----------|---|---|---|
| `before` | Before attempt? | Before **first** attempt only | Before **each** attempt |
| `after` | After attempt? | After **failed** attempt (if retrying) | After **any** attempt, success or fail |
| `before_sleep` | Before sleep? | Immediately before `DoSleep` action | Before actual `sleep()` call (yes, same, but...) |

```python
# User writes:
@retry(before=lambda rs: print(f"Starting attempt {rs.attempt_number}"))
def my_func():
    if random() > 0.5:
        raise ValueError()
    return "success"

# Attempt 1 succeeds: prints "Starting attempt 1"
# Attempt 2 (after some timeout) succeeds: NO PRINT
# User expected: consistent pre-attempt logging
# Reality: logging only on first attempt
```

The user's callback "before_attempt" fires once and never again for retries, even though the retry loop is working correctly. The callback name is misleading.

**When visible under pressure:**
- Metrics callback assumes "after" fires after each attempt, so it counts the number of "after" calls as "total attempts"
- It misses the last attempt (the successful retry)
- Metrics show 2 attempts but 1 success, appearing as a 50% failure rate
- Real failure rate was 0%, but the callback didn't account for the final successful retry

---

## **THE CONSERVATION LAW: Problem Migration Pattern**

### **What problem migrates between visible and hidden?**

**Visible Problems (solved):**
1. ✓ Thread safety (threading.local solves it)
2. ✓ Retry logic flexibility (callbacks solve it)
3. ✓ Exception handling (AttemptManager suppression solves it)
4. ✓ Retry loop reusability (decorator pattern solves it)

**Hidden Problems (created):**
1. ✗ State ownership clarity → **Callback mutation ambiguity**
2. ✗ Action flow visibility → **Flag-state mismatch under dynamic conditions**
3. ✗ Exception lifecycle → **Cleanup-timing divergence**
4. ✗ Timing attribution → **Overhead misattribution**
5. ✗ Callback contract → **Semantic drift in callback firing rules**

### **The Law:**

> **Callback Opacity Corollary**: Every callback-based system trades explicit control flow visibility for implicit flexibility. The problems don't disappear; they migrate from "visible in code" to "hidden in callback interactions." When the system is under pressure (many callbacks, concurrent access, performance debugging), these hidden problems become visible *through unexpected behavior*, not through the code.

The specific migration:
- **Linear visibility** (retry loop is a sequence of statements) → **Conditional visibility** (which statements execute depends on hidden state flags)
- **Tight coupling** (clear cause-effect) → **Loose coupling via callbacks** (callbacks can side-effect state they're supposed to just observe)
- **Explicit timing** (sequential actions) → **Implicit timing** (overhead distributed across framework, callbacks, exception handling)

### **Which migration a practitioner discovers first under pressure?**

**#1: State flag corruption (Problem 2 → 4)**

This is discovered first because:
- It appears as a **logic bug**, not a performance issue
- It happens with 3+ retries (retry count high enough to trigger edge case)
- A custom callback is often involved (user is adding monitoring/instrumentation)
- The stack trace points to retry loop internals, not the callback
- User reaction: "How did the retry loop call my callback twice?"

**Real scenario:**
```python
@retry(after=lambda rs: print(f"Retry {rs.attempt_number}"))
def flaky_api():
    return api.get()  # Fails on first 2 attempts

# Expected output:
# Retry 2
# Retry 3
# (success on 3rd)

# Actual output:
# Retry 2
# Retry 2  # ← Printed twice!
```

This happens because:
1. Attempt 1 fails, iter_state.retry_run_result = True
2. _post_retry_check_actions adds `self.after` to actions
3. Action executes, prints "Retry 2"
4. Next iteration calls `_begin_iter` which resets iter_state
5. But if `prepare_for_next_attempt` wasn't called correctly, iter_state still references the old action
6. The action runs again with stale state

**Why discovered first?**
- Visible symptom: function called, side effect visible (print)
- Clear reproduction: specific callback, specific retry count
- Pressure triggers it: production traffic with variable latency exposes race conditions

---

## **CONCRETE ARTIFACT: Redesigned with All Rejected Paths**

The code should document its invariants explicitly:

```python
class BaseRetrying(ABC):
    """
    Retry state machine with callback phases.
    
    INVARIANTS (must not be violated by callbacks):
    1. iter_state flags are ephemeral (reset each iteration)
    2. statistics is owned by retry loop, callbacks may READ but must not WRITE
    3. Before callbacks can modify retry_state, after callbacks are read-only
    4. Exceptions are invisible to outer scopes until retry logic re-raises
    5. Callback timing is NOT tracked separately; all overhead is lumped as "work"
    
    CALLBACK FIRING RULES (explicit):
    - before(retry_state):      On FIRST attempt only (attempt_number==1, outcome==None)
    - after(retry_state):       After FAILED attempt when retrying (outcome.failed==True)
    - before_sleep(retry_state): After sleep decision, before sleep duration
    - retry_error_callback():    After final failure, before RetryError raised
    """
    
    def iter_state(self):
        """Action chain state. RESET each iteration. Flags ephemeral."""
        if not hasattr(self._local, "iter_state"):
            self._local.iter_state = IterState()
        return self._local.iter_state
    
    def statistics(self):
        """Retry loop metrics. READ by callbacks, modified ONLY by retry loop.
        
        WARNING: overhead is NOT tracked separately:
        - delay_since_first_attempt = wall time (includes callback + exception handling)
        - idle_for = sleep duration
        - Implied "work" = delay - idle, but this is NOT actual function runtime
        """
        if not hasattr(self._local, "statistics"):
            self._local.statistics = {
                "overhead_untracked": 0,  # ← New: explicit poison pill
            }
        return self._local.statistics
```

**What this fixes:**

✓ **Problem 1** (ownership): Explicit "don't write" contract + `overhead_untracked` flag as a canary
✓ **Problem 2** (action chain): Explicit comment that flags are ephemeral, can't be relied on across iterations
✓ **Problem 3** (exception semantics): Document that exceptions are "invisible to outer scopes"
✓ **Problem 4** (timing): Explicit warning that overhead is untracked
✓ **Problem 5** (callback semantics): Explicit firing rules table

**Invisible dangers that emerge:**

✗ More verbose code (longer docstrings)
✗ False sense of security (documentation doesn't prevent callback bugs at runtime)
✗ Pressure test: developer reads the docstring, ignores it, modifies statistics anyway ("it's just metrics")

---

## **CONCLUSION: Which problem surfaces first?**

Under production pressure (high retry volume, custom callbacks, performance debugging):

**#1: State flag corruption** (Problem 2)
- Symptom: "Callback fired twice / wrong number of times"
- Root cause: iter_state flags are ephemeral, but callback expects them to persist
- Impact: High (logic bugs are worse than performance issues)
- Time to discover: When retry count > 2 and callback side-effects are stateful

**#2: Overhead misattribution** (Problem 4)
- Symptom: "Callback blamed for slowness, but profiling shows function is fast"
- Root cause: Statistics lump callback overhead with function runtime
- Impact: Medium (misleads optimization efforts)
- Time to discover: When SLA breaches during high-retry scenarios

**#3: Exception cleanup divergence** (Problem 3)
- Symptom: "Resource leaks during retries"
- Root cause: Exception invisible, cleanup doesn't run until retry logic re-raises
- Impact: High (silent leaks worse than crashes)
- Time to discover: Under memory/connection pressure, days or weeks later

The **law**: Callback-based systems move problems from "visible in control flow" to "invisible in state machine semantics." The first problem discovered is always a **logic bug** (state flags), not a design flaw, because logic bugs have immediate, repeatable symptoms.
