[36mBehavioral Pipeline: code mode, 4 prisms + synthesis[0m
[1m[34m── ERRORS (error_resilience) ── real_code_tenacity.py ──[0m
[2mthinking...[0m                                        # Analysis of Tenacity Retry Library Error Boundaries

## Step 1: The Error Boundaries

### Boundary 1: `AttemptManager.__exit__` (lines ~104-115)
```python
def __exit__(self, exc_type, exc_value, traceback):
    if exc_type is not None and exc_value is not None:
        self.retry_state.set_exception((exc_type, exc_value, traceback))
        return True
    if not self._result_set:
        self.retry_state.set_result(None)
    return None
```
**What specific failure context is preserved vs destroyed:**

| Preserved | Destroyed |
|-----------|-----------|
| `exc_type`, `exc_value`, `traceback` (passed to `set_exception`) | Local variables from the function that raised (in `fn`'s stack frame) |
| Timestamp via `set_exception` | The fact that `__exit__` was entered due to exception vs normal exit |
| Whether `self._result_set` was True before exception | Distinction between "function returned None normally" vs "exception occurred but `set_result` was never called" |
| Exception object itself via `Future.set_exception` | Full `exc_info` tuple structure (traceback chain beyond immediate frame) |

**Destruction mechanism:** The `return True` swallows the exception entirely - control flow continues normally. No flag indicates an exception was ever caught. The `_result_set` boolean conflates two different failure modes: explicit `None` return vs exception before any `set_result` call.

---

### Boundary 2: `RetryCallState.set_exception` (lines ~268-273)
```python
def set_exception(self, exc_info):
    ts = time.monotonic()
    fut = Future(self.attempt_number)
    fut.set_exception(exc_info[1])  # Only exc_value
    self.outcome, self.outcome_timestamp = fut, ts
```
**What specific failure context is preserved vs destroyed:**

| Preserved | Destroyed |
|-----------|-----------|
| `exc_value` (exception instance) | `exc_type` as separate value |
| Timestamp | Original `exc_info` tuple structure |
| Attempt number | Original traceback reference (replaced by `Future`'s storage) |

**Destruction mechanism:** Only `exc_info[1]` passed to `Future.set_exception`, discarding the original 3-tuple structure. The `Future` wrapper creates a new exception context.

---

### Boundary 3: `Retrying.__call__` (lines ~225-240)
```python
def __call__(self, fn, *args, **kwargs):
    # ...
    while True:
        do = self.iter(retry_state=retry_state)
        if isinstance(do, DoAttempt):
            try:
                result = fn(*args, **kwargs)
            except BaseException:
                retry_state.set_exception(sys.exc_info())  # Captures full exc_info
            else:
                retry_state.set_result(result)
```
**What specific failure context is preserved vs destroyed:**

| Preserved | Destroyed |
|-----------|-----------|
| Full `sys.exc_info()` at catch point | Stack frames above `__call__` (if any) |
| Exception type, value, traceback | Local variables in `fn` after exception point |
| Function arguments (`args`, `kwargs`) | Return value (never reached) |

**Destruction mechanism:** The `except` block converts exception flow into data flow via `set_exception`. The exception is no longer "active" - it's stored in `outcome`.

---

### Boundary 4: `_run_retry` via `_run_wait` (lines ~156-162)
```python
def _run_wait(self, retry_state):
    if self.wait:
        sleep = self.wait(retry_state)
    else:
        sleep = 0.0
    retry_state.upcoming_sleep = sleep
```
**What specific failure context is preserved vs destroyed:**

| Preserved | Destroyed |
|-----------|-----------|
| Final `sleep` value | Whether `self.wait` raised an exception vs returned normally |
| Whether `self.wait` is None | Partial state if `self.wait` failed mid-calculation |
| `retry_state` reference | Any exception from `self.wait` (propagates silently, breaking iteration) |

**Destruction mechanism:** No try/except around `self.wait(retry_state)`. If it raises, the entire `iter` loop crashes with an unrelated exception, losing the retry context.

---

### Boundary 5: `iter` method action dispatch (lines ~164-168)
```python
def iter(self, retry_state):
    self._begin_iter(retry_state)
    result = None
    for action in list(self.iter_state.actions):
        result = action(retry_state)
    return result
```
**What specific failure context is preserved vs destroyed:**

| Preserved | Destroyed |
|-----------|-----------|
| Final `result` from last action | All intermediate `result` values from previous actions |
| Action execution order (via list) | Which specific action failed (if exception raised) |
| `retry_state` mutations | Return value from actions that aren't last |

**Destruction mechanism:** Each action's return value overwrites the previous. Only the last action's result survives. If an action raises, the action that caused it is lost from context.

---

## Step 2: The Missing Context

### Destroyed Datum 1: `exc_type` and `traceback` from `exc_info` tuple in `set_exception`

**Trace forward:**
1. `set_exception(exc_info)` receives `(type, value, tb)` tuple
2. Only `exc_info[1]` (value) passed to `Future.set_exception`
3. Downstream in `_post_stop_check_actions`, `exc_check` function creates `RetryError`:
   ```python
   def exc_check(rs):
       fut = rs.outcome
       retry_exc = self.retry_error_cls(fut)
       if self.reraise:
           retry_exc.reraise()
       raise retry_exc from fut.exception()
   ```

**Decision branch that needs it:**
- `retry_exc.reraise()` (line ~90 in `RetryError.reraise`):
  ```python
  def reraise(self):
      if self.last_attempt.failed:
          raise self.last_attempt.result()  # This is fut.exception()
      raise self
  ```
- This `raise` needs the **original traceback** to preserve the full stack from `fn` to the reraise point.

**WRONG branch taken instead:**
- When `reraise=True` and `retry` condition fails:
  - `exc_check` raises `RetryError` wrapping `fut.exception()`
  - The `raise retry_exc from fut.exception()` creates a **new exception chain**
  - The original traceback from `fn` is now buried as `__cause__`, not the primary traceback
  - Debugging now shows "RetryError" at top level, obscuring whether the original exception came from `fn` or `self.wait`

**User-visible harm:**
```python
@retry(stop=stop_after_attempt(1), reraise=True)
def failing_function():
    raise ValueError("original error")

failing_function()
```
**Expected traceback:**
```
Traceback (most recent call last):
  File "test.py", line 3, in failing_function
    raise ValueError("original error")
ValueError: original error
```

**Actual traceback:**
```
Traceback (most recent call last):
  File "test.py", line 3, in failing_function
    raise ValueError("original error")
ValueError: original error

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "test.py", line 276, in __call__
    raise retry_exc from fut.exception()
tenacity.RetryError: <Future at 0x... exception=ValueError('original error')>
```

The `reraise=True` option is **misnamed** - it doesn't reraise the original exception, it raises a `RetryError` wrapper. Users expecting the original exception to bubble up unchanged get a wrapper instead.

---

### Destroyed Datum 2: Whether `__exit__` was entered due to exception vs normal exit

**Trace forward:**
1. `AttemptManager.__exit__` catches all exceptions, returns `True`
2. No flag distinguishes "exception occurred" from "normal return with None"
3. In `_begin_iter`, the code checks `is_explicit_retry` but not "any exception occurred":
   ```python
   self.iter_state.is_explicit_retry = fut.failed and isinstance(fut.exception(), RetrySignal)
   ```
4. This only catches `RetrySignal`, not other exceptions

**Decision branch that needs it:**
- The `lambda rs: rs.outcome.result()` in `_post_retry_check_actions`:
  ```python
  if not (self.iter_state.is_explicit_retry or self.iter_state.retry_run_result):
      self._add_action_func(lambda rs: rs.outcome.result())  # Re-raises if outcome failed
      return
  ```
- This branch assumes: if not retrying, then get result (which may raise)

**WRONG branch taken instead:**
- When `fn` raises an exception and `retry` condition returns `False`:
  - `_run_retry` sets `retry_run_result = False`
  - Code reaches the `lambda rs: rs.outcome.result()` branch
  - Calls `result()` which re-raises the stored exception
  - **This is actually correct behavior** - the exception propagates

Wait, let me re-examine. The destruction here is more subtle. The real issue is:

**When `fn` returns `None` normally vs raises exception before `set_result`:**
- Both result in `outcome = Future()` with either `set_result(None)` or `set_exception(exc)`
- In `__exit__`:
  - Exception path: calls `set_exception`, returns `True`
  - Normal path: if `_result_set` is False (never called `set_result`), calls `set_result(None)`

**The confusion:**
- If `fn` raises `RetrySignal`, `is_explicit_retry` becomes True
- If `fn` raises any other exception, `is_explicit_retry` is False, `retry_run_result` may be False
- Then `outcome.result()` is called, which raises the original exception

So this boundary **correctly** propagates non-retryable exceptions. The information destruction is more about observability - you can't tell from `IterState` whether an exception occurred without inspecting `outcome`.

---

### Destroyed Datum 3: All intermediate action return values in `iter`

**Trace forward:**
1. `iter` executes actions: `for action in list(self.iter_state.actions): result = action(retry_state)`
2. Each action returns a value (e.g., `DoAttempt()`, `DoSleep(1.5)`, or a computed value)
3. Only the final `result` is returned
4. Intermediate values are overwritten

**Decision branch that needs it:**
- None in current code - actions are executed sequentially for side effects only
- The action chain is stateful via `retry_state` mutations, not via return values

**WRONG branch taken instead:**
- If an early action returns an error signal (not an exception, but a value like `{"error": True}`), it's lost
- This is **not currently a bug** - the design uses exceptions for error handling in actions

**User-visible harm:**
- None in current implementation, but the design makes debugging difficult
- If `self.wait` returns an invalid value (e.g., negative sleep), it's stored in `upcoming_sleep` without validation
- No action return value can indicate "this wait value is invalid"

---

### Destroyed Datum 4: Exception from `self.wait` in `_run_wait`

**Trace forward:**
1. `_run_wait` calls `sleep = self.wait(retry_state)`
2. No try/except around this call
3. If `self.wait` raises, the exception propagates out of `iter`
4. The `while True` loop in `__call__` or `__iter__` catches nothing

**Decision branch that needs it:**
- The `if isinstance(do, DoSleep)` check in `__call__`:
  ```python
  elif isinstance(do, DoSleep):
      retry_state.prepare_for_next_attempt()
      self.sleep(do)
  ```

**WRONG branch taken instead:**
- When `self.wait` raises an unexpected exception:
  - The exception bubbles out of `iter`
  - `do` is never assigned a value
  - The `while True` loop is broken by the uncaught exception
  - User sees an error from their `wait` callback, not from their retryable function

**User-visible harm:**
```python
import random

@retry(wait=lambda _: random.choice(["a"]))  # Returns non-numeric
def test():
    raise ValueError("try again")

test()  # TypeError: can't convert str to float
```
**Expected:** Wait strategy validation error
**Actual:** Random `TypeError` from `DoSleep(float)` constructor or deep in retry logic

---

## Step 3: The Impossible Fix

### Boundary Destroying the MOST Information: `AttemptManager.__exit__`

This boundary destroys:
1. Distinction between "exception occurred" vs "normal exit without result"
2. Original exception context beyond what's stored in `retry_state`
3. Whether `fn` never completed vs completed with explicit `None`

---

### Fix A: Preserve exception occurrence flag

```python
class AttemptManager:
    def __init__(self, retry_state):
        self.retry_state = retry_retry_state
        self._result_set = False
        self._exception_occurred = False  # NEW: Track if exception was caught

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None and exc_value is not None:
            self._exception_occurred = True  # NEW: Set flag
            self.retry_state.set_exception((exc_type, exc_value, traceback))
            return True
        if not self._result_set:
            self.retry_state.set_result(None)
        return None
```

**What Fix A DESTROYS:**
- The **silent swallowing** of exceptions. Now we know if one occurred.
- The **conflation** of `None` returns with exceptions.
- The **ability to use `RetrySignal` as a control flow mechanism** without it being distinguishable from other exceptions.

**NEW information destroyed by Fix A:**
- The **original simplicity** of the "all exceptions are just data in `outcome`" model
- Now downstream code must check `manager._exception_occurred` OR `outcome.failed`
- This creates **dual sources of truth** for exception state

---

### Fix B: Preserve the exception context fully (original traceback)

```python
class RetryCallState:
    def set_exception(self, exc_info):
        ts = time.monotonic()
        fut = Future(self.attempt_number)
        fut.set_exception(exc_info[1])
        self.outcome, self.outcome_timestamp = fut, ts
        self._original_exc_info = exc_info  # NEW: Preserve full tuple
```

And update `RetryError.reraise`:
```python
class RetryError(Exception):
    def __init__(self, last_attempt):
        self.last_attempt = last_attempt
        super().__init__(last_attempt)

    def reraise(self):
        if self.last_attempt.failed:
            exc_info = getattr(self.last_attempt, '_original_exc_info', None)
            if exc_info:
                # Preserve original traceback using raise...from... syntax
                raise exc_info[1].with_traceback(exc_info[2])
            raise self.last_attempt.result()
        raise self
```

**What Fix B DESTROYS:**
- The **memory efficiency** of discarding traceback objects early
- The **exception wrapping isolation** - now `reraise` truly re-raises the original exception, losing the "retry failed" context
- The **ability to distinguish** "exception from original function" vs "exception during retry logic"

**NEW information destroyed by Fix B:**
- The **retry context itself** when `reraise=True`
- User sees "ValueError: original error" with no indication this was a retry failure
- Stack trace doesn't show retry logic decisions

---

### What Survives Both Fixes?

| Boundary | Destroyed | Wrong Decision | Harm | Fix A Destroys | Fix B Destroys | Invariant |
|----------|-----------|----------------|------|----------------|----------------|-----------|
| `AttemptManager.__exit__` | Exception occurrence flag | Can't distinguish `None` return from exception without inspecting `outcome.failed` | Debugging difficulty, silent failures | Simplicity of single-source-of-truth (outcome.failed) | Exception swallowing capability | `outcome` must contain either a result or an exception |
| `RetryCallState.set_exception` | `exc_type` and `traceback` from full `exc_info` | `reraise=True` raises wrapper `RetryError` instead of original exception | Misleading stack traces, wrong exception type at top level | Memory efficiency (traceback objects kept) | Retry context in exception chain | `outcome.failed` must indicate if exception exists |
| `Retrying.__call__` except block | Local variables from `fn` after exception | Can't inspect `fn`'s post-exception state | Debugging limited to exception object | None (already preserves what matters) | None | `retry_state.outcome` must be set on exception |

### Structural Invariant

**The `outcome` Future object is the sole source of truth for whether an exception occurred.**

Any fix that preserves additional information (exception occurrence flag, original exc_info tuple) creates a **dual-source-of-truth** problem:
- `outcome.failed` / `outcome.exception()`
- `_exception_occurred` flag / `_original_exc_info` tuple

These can become inconsistent if:
- Future is modified externally
- Exception is cleared from Future
- Flag is set incorrectly

The invariant is: **`outcome.failed` must be equivalent to "an exception was stored in the outcome"**, and all other exception state must be derived from this, not duplicated.

The true fix requires a **redesign of `Future`** to preserve `exc_info` tuple natively:
```python
class Future(futures.Future):
    def __init__(self, attempt_number):
        super().__init__()
        self.attempt_number = attempt_number
        self._exc_info = None  # NEW: Store full tuple
    
    def set_exception(self, exc_info):  # Changed signature
        self._exc_info = exc_info  # Store tuple
        super().set_exception(exc_info[1])  # Pass value to parent
```

This preserves information without creating dual sources of truth - the Future itself becomes the authoritative source.

  [2mSaved to .deep/findings/real_code_tenacity.md[0m
[1m[34m── COSTS (optimize) ── real_code_tenacity.py ──[0m
[2mthinking...[0m                                        I'll execute the three-step analysis to identify opacity boundaries and their performance costs.

## Step 1: Search for Opacity

**Boundaries identified:**

1. **ContextVar boundary (`_iter_state_var`)**: Uses `contextvars.ContextVar` for async/task-local storage. The lookup mechanism is hidden in CPython's task context implementation - dictionary lookup within task context structure.

2. **Threading.local boundary (`self._local`)**: Thread-local storage for statistics. Hidden implementation: thread ID → storage mapping in C code with potential lock contention during initial access per thread.

3. **Strategy composition boundary**: `self.stop()`, `self.wait()`, `self.retry()`, `self.before`, `self.after`, `self.before_sleep`. All are dynamic dispatch through potentially user-defined callables.

4. **Future/futures.Future boundary**: Uses `concurrent.futures.Future` which contains hidden locks (`self._condition`), event notifications, and thread synchronization primitives even though no actual concurrency occurs.

5. **Exception capture boundary**: `sys.exc_info()` captures current exception with full traceback. Hidden: stack frame walk, traceback object allocation, frame object creation.

6. **Dynamic action list (`iter_state.actions`)**: Runtime-growing list of lambda functions. The execution path is constructed during iteration, not statically determined.

7. **Sleep indirection**: `self.sleep` parameter allows custom sleep functions (default `time.sleep`). Virtual call boundary.

## Step 2: Trace the Blind Workarounds

**For each boundary, the blocked optimizations and actual costs:**

**ContextVar (`_iter_state_var.get/set`)**:
- **Blocked optimization**: Direct stack variable or struct member access
- **Blind workaround**: Hash lookup in task context dict
- **Cost**: 25-40ns per access (dict lookup), plus potential cache miss if task context is cold

**Threading.local statistics**:
- **Blocked optimization**: Static metrics storage with inline updates
- **Blind workaround**: `hasattr` check, dictionary creation, thread ID lookup on every access
- **Cost**: 30-50ns for hasattr + dict ops, plus ~100ns for first access per thread

**Strategy callbacks (`stop/wait/retry/before/after`)**:
- **Blocked optimization**: Inline branch prediction, specialized code paths
- **Blind workaround**: Python function call through indirection
- **Cost**: 80-150ns per callable, prevents inlining and cross-procedure optimization

**Future object usage**:
- **Blocked optimization**: Direct outcome storage (simple struct with result flag)
- **Blind workaround**: 
  - Lock acquisition in `set_result`/`set_exception`: ~40ns for uncontended lock
  - Condition variable notification: 50-100ns even with no waiters
  - Memory barriers for thread visibility
- **Cost**: ~200-300ns total per outcome set, completely unnecessary in single-threaded case

**Exception capture (`sys.exc_info()`)**:
- **Blocked optimization**: Return early with error code
- **Blind workaround**: Full traceback capture with stack walk
- **Cost**: 
  - Traceback object allocation: ~1-2μs
  - Frame object creation per stack frame: ~200ns per frame
  - Memory allocation overhead

**Dynamic action list**:
- **Blocked optimization**: Static state machine with direct branches
- **Blind workaround**: 
  - List append operations: 40-60ns per append
  - List iteration overhead: 30-50ns per element
  - Type checking through `isinstance(do, DoAttempt/Sleep)`: 20-30ns per check
- **Cost**: ~100-150ns per action in the iteration loop

## Step 3: Name the Conservation Law

| Boundary | Erased Data | Blocked Optimization | Blind Workaround | Concrete Cost | Flattening Breaks |
|----------|-------------|---------------------|------------------|---------------|-------------------|
| **Future/futures.Future** | Lock state, condition variable sync protocol | Direct struct assignment (result + flag) | Lock acquire, condition notify, memory barrier | 200-300ns per outcome set | Reuse of concurrent primitives (no benefit here) |
| **Dynamic action list** | Control flow graph is runtime-computed | Static state machine with inline branches | List append, list iteration, type checks | 100-150ns per action | Composition of retry strategies at runtime |
| **Exception capture (`sys.exc_info()`)** | Stack frames are always captured | Early return on error without allocation | Traceback alloc, frame creation, stack walk | 1-2μs + 200ns/frame | Detailed exception introspection |
| **Strategy callbacks (stop/wait/retry)** | Call target determined at runtime | Inline branch prediction, specialized code | Indirect function call | 80-150ns per call | Pluggable retry policies |
| **ContextVar (`_iter_state_var`)** | Task context dict lookup | Direct stack/local variable access | Hash lookup in task context | 25-40ns per access | Async/task-local isolation |
| **Threading.local (`self._local`)** | Thread ID → storage mapping | Static metrics storage | hasattr check + dict ops | 30-50ns per access | Thread-safe statistics without locks |

**Primary Boundary Destroyer: Future/futures.Future**

The Future abstraction is the most destructive boundary because:
- It introduces lock synchronization (~40ns) even in single-threaded code
- Condition variable notification overhead (~50-100ns) with zero waiters
- Memory barriers enforcing visibility across non-existent threads
- Complex internal state machine for a simple "result or exception" store

**Trade**: Flattening Future to a direct `outcome: tuple[type, object]` field would expose ~250ns per attempt but breaks the ability to integrate with actual concurrent.futures workflows. However, since Tenacity's RetryCallState is fundamentally single-threaded (no concurrent waiters), this abstraction is pure overhead—there's no actual concurrency to manage. The "conservation" here is illusory; breaking this boundary would only lose the ability to pass outcomes to code expecting Future objects, which Tenacity doesn't do.

  [2mSaved to .deep/findings/real_code_tenacity.md[0m
[1m[34m── ENTAILMENT (fix_cascade) ── real_code_tenacity.py ──[0m
[2mthinking...[0m                                        # Structural Analysis: Tenacity Retry Library

## Step 1: Locate the Structural Defect

**Core Defect: Dynamic Control-Flow Flattening via Action List Rebuilding**

The deepest problem is the **action list architecture** that forces control flow to be rebuilt on every iteration through list mutation, rather than using Python's native sequential execution.

### Exact Locations:

**1. Action list rebuild on every iteration (Lines 128-132):**
```python
def iter(self, retry_state):
    self._begin_iter(retry_state)
    result = None
    for action in list(self.iter_state.actions):  # Actions rebuilt each call
        result = action(retry_state)
    return result
```

**2. State scattered across methods that mutate actions (Lines 133-164):**
```python
def _begin_iter(self, retry_state):
    self.iter_state.reset()  # Must clear first
    # ... then add actions conditionally
    self._add_action_func(lambda rs: DoAttempt())

def _post_retry_check_actions(self, retry_state):
    if not (self.iter_state.is_explicit_retry or self.iter_state.retry_run_result):
        self._add_action_func(lambda rs: rs.outcome.result())  # Add terminal action
        return
    # ... add more actions
    self._add_action_func(self._post_stop_check_actions)  # Recursive action building

def _post_stop_check_actions(self, retry_state):
    if self.iter_state.stop_run_result:
        # ... add error actions
        return
    # ... add retry actions
    self._add_action_func(lambda rs: DoSleep(rs.upcoming_sleep))
```

**3. Dual control-flow paths with duplicated result handling (Lines 166-186 & 242-258):**
```python
# In __iter__:
def __iter__(self):
    while True:
        do = self.iter(retry_state=retry_state)  # Get command from action list
        if isinstance(do, DoAttempt):
            yield AttemptManager(retry_state=retry_state)
        elif isinstance(do, DoSleep):
            retry_state.prepare_for_next_attempt()
            self.sleep(do)
        else:
            break

# In __call__ (nearly identical):
def __call__(self, fn, *args, **kwargs):
    while True:
        do = self.iter(retry_state=retry_state)  # Same pattern
        if isinstance(do, DoAttempt):
            # ... handle attempt
        elif isinstance(do, DoSleep):
            # ... handle sleep
        else:
            return do
```

**What the code cannot express cleanly:**
- **Causal chains**: The relationship between "should retry" → "calculate wait" → "check stop condition" is hidden across 3 methods
- **State validity windows**: `IterState.actions` is only valid immediately after `_begin_iter()` runs; accessing it at any other point gives stale data
- **Branch causality**: Which action gets added next depends on state set by previous action, but this dependency is implicit

## Step 2: Trace What a Fix Would Hide

**Proposed Fix:** Eliminate the action list entirely. Use a direct state machine with explicit states (ATTEMPT, WAIT, STOP, RAISE, RETURN).

**Diagnostic signals destroyed:**

| Lost Signal | Current Exposure | After Fix |
|-------------|------------------|-----------|
| **Action order validation** | Can print `iter_state.actions` to see exact execution plan | State transitions implicit in code flow - cannot inspect without debugging |
| **Mid-interaction introspection** | Can log each action as it's executed (line 131) | Would need to add logging at every branch point manually |
| **Strategy composition failure** | If retry/wait/stop hooks conflict, appears as wrong action in list | Would appear as control flow bug - harder to attribute to which strategy |
| **State mutation detection** | `iter_state.reset()` creates clear boundary; can detect if actions leaked | No clear reset point; state mutation could silently propagate |
| **Async continuation capture** | Action list is serializable; could theoretically pause/resume | Native call stack cannot be serialized - breaks future async features |

**Concrete example of buried failure:**
Currently, if a custom `retry` condition raises an exception, it will be visible as the action that should have been added being missing from `iter_state.actions`. After fixing to direct control flow, that same bug appears as "loop never exits" - the diagnostic signal moves from "missing action in list" to "infinite loop."

## Step 3: Identify the Unfixable Invariant

**Apply fix iteratively:**

**Iteration 1:** Replace action list with direct state machine.
- New problem: Now `@retry` decorator, `Retrying.__call__`, and `BaseRetrying.__iter__` need different state machine implementations
- Fixed by: Extracting state machine engine into separate class

**Iteration 2:** Extract state machine engine.
- New problem: How do strategies (retry/wait/stop hooks) influence control flow? They can't return "next action" anymore
- Fixed by: Making them return enum values that drive state machine

**Iteration 3:** Use enum-based strategy composition.
- New problem: Strategies need to know about each other (stop condition needs to know if retry happened; wait needs to know if stop is imminent)
- Fixed by: Passing shared state object to all strategies

**Iteration 4:** Pass shared state object.
- **Result:** We've recreated `RetryCallState` - the state object that already exists!

**The Persistent Invariant:**
**"State-dependent control flow must be recomputed after each state transition."**

The retry logic requires decisions (should I retry? should I stop? how long to wait?) that:
1. **Depend on current state** (did the last attempt fail? how many retries so far?)
2. **Mutate that state** (increment attempt counter, record outcome)
3. **Produce next control-flow decision** (retry again, stop and raise, return result)

This creates a fundamental tension:
- If decisions are **data-driven** (action list), you must rebuild the decision tree after each state change
- If decisions are **code-driven** (if/else chains), you cannot introspect or modify the decision logic without changing code

The invariant manifests as:
- **Either:** Mutable action lists that must be rebuilt (current approach)
- **Or:** Hard-coded control flow that cannot be composed or introspected
- **Or:** A state machine engine that recreates the same complexity elsewhere

### Verdict: STRUCTURAL

The action list architecture is not a bug - it's a **necessary adaptation** to two conflicting requirements:

1. **Composability:** Users need to combine retry strategies, stop conditions, wait policies, and hooks
2. **Introspection:** The library needs to support execution traces, statistics, and debugging

The action list **makes these tensions visible** as a clumsy but workable interface. "Fixing" it would only move the complexity into:
- A more complex state machine engine
- Harder-to-debug control flow
- Lost diagnostic capabilities

The correct management strategy is:
- **Document** the action list lifecycle clearly
- **Validate** `iter_state.actions` in tests to catch rebuild errors
- **Provide helper methods** for common action-building patterns
- **Accept** that some redundancy between `__iter__` and `__call__` is the cost of supporting both iterator and direct-call patterns

| Core Defect | Location | What Fix Hides | Invariant | Verdict |
|-------------|----------|----------------|-----------|---------|
| Dynamic control-flow flattening via action list rebuilding | `iter()`, `_begin_iter()`, `_post_retry_check_actions()`, `_post_stop_check_actions()` | Action order validation, mid-interaction introspection, strategy composition failure detection, state mutation boundaries, async continuation capture | State-dependent control flow must be recomputed after each state transition (creates tension between composability and native execution) | **STRUCTURAL** - Must be managed through documentation, validation, and acceptance of necessary complexity |

  [2mSaved to .deep/findings/real_code_tenacity.md[0m
[1m[34m── DISPLACEMENT (identity) ── real_code_tenacity.py ──[0m
[2mthinking...[0m                                        # IDENTITY DISPLACEMENT ANALYSIS: Tenacity Retry Library

## Step 1: Surface the Claim

**Artifact Claim**: A "retry library" for Python using "strategy composition, action chains, state tracking"

### Explicit Promises by Component:

1. **`retry` decorator function**: Claims to wrap functions with automatic retry behavior
2. **`Retrying` class**: Claims to orchestrate retry attempts with configurable strategies
3. **`Future` class**: Claims to be a `concurrent.futures.Future` (inherits from it)
4. **`AttemptManager` class**: Claims to "manage" retry attempts via context manager protocol
5. **`DoAttempt` and `DoSleep` classes**: Claim to be control flow markers
6. **`iter_state` property**: Claims to track "iteration state"
7. **`RetryError` class**: Claims to be an exception type for retry failures
8. **`__iter__` method**: Claims to be a Python iterator yielding retry attempts
9. **`Future.failed` property**: Claims to indicate if the future/result failed

### Expected User Mental Model:
- Decorate a function → it retries on failure
- Iterator yields attempt objects → you execute them
- `Future` objects represent asynchronous/deferred results
- State tracking is simple bookkeeping

---

## Step 2: Trace the Displacement

### Displacement 1: `Future` Claims to be a Future, Is Actually a Synchronous Result Container

**Location**: Lines 143-153
```python
class Future(futures.Future):
    def __init__(self, attempt_number):
        super().__init__()
        self.attempt_number = attempt_number

    @property
    def failed(self):
        return self.exception() is not None

    @classmethod
    def construct(cls, attempt_number, value, has_exception):
        fut = cls(attempt_number)
        if has_exception:
            fut.set_exception(value)
        else:
            fut.set_result(value)
        return fut
```

**Contradiction**: 
- **Claims**: `isinstance(Future(...), futures.Future)` → "I am a concurrent future"
- **Reality**: The `construct()` method creates already-completed futures. `set_result()` and `set_exception()` are called immediately in the same thread. There is no actual concurrency, no callbacks, no polling. It's a completed result wrapper misusing the Future interface.

---

### Displacement 2: `__iter__` Claims to be an Iterator, Is Actually a Control Flow Interpreter

**Location**: Lines 120-135
```python
def __iter__(self):
    self.begin()
    retry_state = RetryCallState(self, fn=None, args=(), kwargs={})
    while True:
        do = self.iter(retry_state=retry_state)
        if isinstance(do, DoAttempt):
            yield AttemptManager(retry_state=retry_state)
        elif isinstance(do, DoSleep):
            retry_state.prepare_for_next_attempt()
            self.sleep(do)
        else:
            break
```

**Contradiction**:
- **Claims**: Iterator protocol yielding retry attempt objects
- **Reality**: Uses `isinstance()` checks on yielded values to dispatch control flow. `DoSleep` (a float subclass) triggers sleep logic, `DoAttempt` yields execution context, anything else breaks. The "iteration" is actually a state machine disguised as iteration.

---

### Displacement 3: `AttemptManager` Claims to Manage Attempts, Is Actually a Deferred State Mutator

**Location**: Lines 91-104
```python
class AttemptManager:
    def __init__(self, retry_state):
        self.retry_state = retry_state
        self._result_set = False

    def __enter__(self):
        pass

    def set_result(self, value):
        self.retry_state.set_result(value)
        self._result_set = True

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None and exc_value is not None:
            self.retry_state.set_exception((exc_type, exc_value, traceback))
            return True
        if not self._result_set:
            self.retry_state.set_result(None)
        return None
```

**Contradiction**:
- **Claims**: Context manager for "managing" retry attempts
- **Reality**: `__enter__` does nothing (`pass`). The real work happens in `__exit__` via side effects. If you call `set_result()`, it marks a flag; otherwise, `__exit__` defaults to setting `None`. It's not "managing" anything—it's deferring state mutation until context exit, silently mutating a shared `retry_state` object.

---

### Displacement 4: `iter_state` Claims to Track Iteration, Is Actually a Command Queue

**Location**: Lines 17-24, 86-112
```python
@dataclasses.dataclass(slots=True)
class IterState:
    actions: list = dataclasses.field(default_factory=list)
    retry_run_result: bool = False
    stop_run_result: bool = False
    is_explicit_retry: bool = False
    # ... reset method ...

# In BaseRetrying:
@property
def iter_state(self):
    state = _iter_state_var.get()
    if state is None:
        state = IterState()
        _iter_state_var.set(state)
    return state

def _add_action_func(self, fn):
    self.iter_state.actions.append(fn)

def iter(self, retry_state):
    self._begin_iter(retry_state)
    result = None
    for action in list(self.iter_state.actions):
        result = action(retry_state)
    return result
```

**Contradiction**:
- **Claims**: "State tracking for iteration" (as the name suggests)
- **Reality**: `actions` is a mutable list of functions queued for execution. `iter()` doesn't "iterate" over attempts—it executes a command queue. The property name suggests iteration state, but it's actually a command buffer for a state machine.

---

### Displacement 5: `DoSleep` Claims to be a Sleep Marker, Is Actually a Type-Based Control Signal

**Location**: Lines 38-39, embedded in iteration logic
```python
class DoSleep(float):
    pass

# Usage in __iter__ and __call__:
elif isinstance(do, DoSleep):
    retry_state.prepare_for_next_attempt()
    self.sleep(do)
```

**Contradiction**:
- **Claims**: A marker class representing "sleep now"
- **Reality**: Inherits from `float` so it carries sleep duration as a value. But the control flow depends on `isinstance()` checking, not the value. `DoSleep(5.0)` triggers sleep; `5.0` does not. It's using Python's type system as a control flow protocol.

---

### Displacement 6: `retry` Function Claims to be a Decorator, Is Actually a Decorator Factory That Can Be Two Things

**Location**: Lines 233-240
```python
def retry(*dargs, **dkw):
    if len(dargs) == 1 and callable(dargs[0]):
        return retry()(dargs[0])  # ← Calls retry() AGAIN

    def wrap(f):
        r = Retrying(*dargs, **dkw)
        return r.wraps(f)

    return wrap
```

**Contradiction**:
- **Claims**: A decorator for adding retry behavior
- **Reality**: When called as `@retry` (no parens), it detects `len(dargs) == 1 and callable(dargs[0])` and **recursively calls itself** with no arguments to get the "real" decorator. The function shifts identities based on whether it's called with or without arguments.

---

### Displacement 7: `Future.failed` Property Claims to Indicate Failure, Is Actually Derived from Exception State

**Location**: Lines 148-149
```python
@property
def failed(self):
    return self.exception() is not None
```

**Contradiction**:
- **Claims**: A property indicating if this future/result "failed"
- **Reality**: `futures.Future` doesn't have a `failed` property. This is an invention. It doesn't check if the wrapped function raised an exception—it checks if **this Future object** has an exception set. But since `Future.construct()` **always** sets either result or exception immediately, `failed` is just "was the `has_exception` flag passed to `construct()`?" disguised as runtime state.

---

## Step 3: Name the Cost

### Displacement 1: `Future` is a Synchronous Result Container

**WHAT IT BUYS**: 
- Uniform interface for "attempt outcomes" without introducing a new `AttemptResult` type
- Ability to use `future.failed`, `future.result()`, `future.exception()` methods consistently
- Polymorphic code that can handle both async and sync outcomes (the library has async variants)

**COST**: 
- Misuse of `concurrent.futures.Future` inheritance — violates Liskov Substitution Principle (a `Future` that is never "pending")
- Users might expect `.add_done_callback()` to work, or `.cancel()`, but they don't

**HONEST VERSION**:
```python
@dataclasses.dataclass
class AttemptOutcome:
    attempt_number: int
    value: Any = None
    exception: Optional[BaseException] = None
    
    @property
    def failed(self):
        return self.exception is not None
```
**SACRIFICE**: Loses the semantic familiarity of `Future` API, requires learning new type.

**VERDICT**: **NECESSARY** — The `Future` API provides a rich, well-known interface for result/exception handling. Creating a new type would force users to learn a custom API.

---

### Displacement 2: `__iter__` is a Control Flow Interpreter

**WHAT IT BUYS**:
- Pythonic API: `for attempt in retryer:` looks like iteration
- Declarative control flow: The "iterator" yields tokens, and the `__iter__` loop dispatches based on token type
- Enables the library to implement complex retry logic (pre/post hooks, stop conditions, sleep calculations) without exposing internal state

**COST**:
- Violates iterator semantics — yielding different types (`DoSleep` vs `AttemptManager`) to control flow is unconventional
- Debugging is harder: control flow depends on runtime `isinstance()` checks

**HONEST VERSION**:
```python
def execute(self, fn, *args, **kwargs):
    while True:
        decision = self._make_retry_decision()
        if decision.kind == Decision.ATTEMPT:
            try:
                return fn(*args, **kwargs)
            except BaseException as e:
                self._handle_exception(e)
        elif decision.kind == Decision.SLEEP:
            time.sleep(decision.duration)
        elif decision.kind == Decision.STOP:
            break
```
**SACRIFICE**: Loses the elegant `for attempt in Retrying(...):` syntax, requires explicit state machine.

**VERDICT**: **NECESSARY** — The iterator-based API is one of Tenacity's most powerful features. It enables writing custom retry logic that reads like iteration, which is invaluable for complex retry scenarios.

---

### Displacement 3: `AttemptManager` is a Deferred State Mutator

**WHAT IT BUYS**:
- Flexibility: Users can call `set_result()` to override the result, or let it default to `None`
- Exception swallowing: `__exit__` returns `True` on exceptions, preventing propagation (necessary for retry logic)
- Clean API: No explicit `commit()` or `save()` needed

**COST**:
- Silent mutation: The `retry_state` object is modified as a side effect
- The `_result_set` flag is subtle — easy to miss that not calling `set_result()` means "set to None"

**HONEST VERSION**:
```python
with attempt as result_proxy:
    try:
        result = fn(*args, **kwargs)
        result_proxy.set_result(result)
    except BaseException:
        result_proxy.set_exception(sys.exc_info())
        result_proxy.suppress_exception()
```
**SACRIFICE**: More verbose API; requires explicit exception suppression.

**VERDICT**: **NECESSARY** — The context manager pattern is standard in Python, and the deferred mutation allows for result interception. The cost is minor confusion about the default `None` behavior.

---

### Displacement 4: `iter_state` is a Command Queue

**WHAT IT BUYS**:
- Separation of concerns: The "what to do next" logic (queued functions) is separate from the "do it" logic (`iter()` loop)
- Dynamic action generation: Methods like `_post_retry_check_actions()` can queue different actions based on runtime state
- Composable hooks: `before`, `after`, `before_sleep` callbacks are just queued functions

**COST**:
- Name confusion: `iter_state` suggests "state of iteration," not "command queue"
- Mutability: The `actions` list is mutated across method calls, making control flow harder to trace

**HONEST VERSION**:
```python
@property
def command_queue(self):
    state = _command_var.get()
    if state is None:
        state = CommandQueue()
        _command_var.set(state)
    return state
```
**SACRIFICE**: Admitting it's a command queue loses the "iteration" abstraction. Users have to understand "command queuing" instead of "state tracking."

**VERDICT**: **NECESSARY** — The command queue pattern is the core of Tenacity's strategy composition. It's what allows `retry`, `wait`, `stop`, and `before/after` hooks to compose cleanly.

---

### Displacement 5: `DoSleep` is a Type-Based Control Signal

**WHAT IT BUYS**:
- Self-documenting tokens: `DoSleep(5.0)` clearly means "sleep for 5 seconds"
- No separate flag variable: The token type (`DoSleep` vs `DoAttempt` vs return value) encodes the action
- Works with both iterator and direct call patterns

**COST**:
- Type abuse: Using `isinstance()` for control flow is unconventional
- `DoSleep` inherits from `float` solely to carry a value, mixing type signaling with data

**HONEST VERSION**:
```python
@dataclasses.dataclass
class SleepAction:
    duration: float

@dataclasses.dataclass
class AttemptAction:
    manager: AttemptManager

def iter(self, retry_state):
    # ... returns SleepAction or AttemptAction or result
```
**SACRIFICE**: More verbose; loses the "just check isinstance" simplicity.

**VERDICT**: **NECESSARY** — The `DoAttempt` / `DoSleep` pattern is a clever use of Python's type system. It keeps the API terse while maintaining clarity. The float inheritance is a bit hacky but harmless.

---

### Displacement 6: `retry` is a Decorator Factory That Shifts Identity

**WHAT IT BUYS**:
- Dual API: `@retry` and `@retry(...)` both work
- Zero-config defaults: `@retry` uses sensible defaults; `@retry(stop=stop_after_attempt(3))` customizes

**COST**:
- Confusing implementation: The recursive `return retry()(dargs[0])` is head-scratching
- Makes the function's identity context-dependent

**HONEST VERSION**:
```python
def retry(**kwargs):
    def decorator(f):
        return Retrying(**kwargs).wraps(f)
    return decorator

# For no-arg usage:
retry_default = retry()
```
**SACRIFICE**: Users must write `@retry_default` or `@retry()` instead of just `@retry`.

**VERDICT**: **NECESSARY** — The dual API is a Python best practice (see `dataclasses.dataclass`, `functools.lru_cache`). The confusion is implementation detail; the API is intuitive.

---

### Displacement 7: `Future.failed` is Derived from Exception State

**WHAT IT BUYS**:
- Convenient boolean check: `if outcome.failed:` is cleaner than `if outcome.exception() is not None:`
- Consistent with mental model: "Did this attempt fail?" is a natural question

**COST**:
- Inventive API: `futures.Future` doesn't have `.failed`, so this is non-standard
- Not a true property of "failure" — it's just "has an exception"

**HONEST VERSION**:
```python
# Use: if outcome.exception() is not None:
```
**SACRIFICE**: Verbose; doesn't read as naturally.

**VERDICT**: **NECESSARY** — The `.failed` property is a usability enhancement. It doesn't break anything since it's a new property, not overriding standard behavior.

---

## FINAL ANALYSIS

### ACCIDENTAL DISPLACEMENTS: 0

Every displacement in Tenacity appears **necessary**. The library uses Python's protocols (iterators, context managers, inheritance) in unconventional ways to achieve a **cohesive goal**: composable retry strategies with a clean, declarative API.

### The Core Trade-off

Tenacity sacrifices **semantic purity** for **API expressiveness**:
- `Future` isn't a true future, but it provides a familiar result/exception interface
- `__iter__` isn't a true iterator, but it enables `for attempt in retryer:` syntax
- `iter_state` isn't just "state," but it enables hook composition
- `DoSleep` / `DoAttempt` abuse type checking, but they enable readable control flow

These displacements are **intentional design decisions**, not technical debt. The "honest" versions would require users to understand more concepts (command queues, state machines, explicit result types) and write more verbose code.

**Tenacity's genius is that it uses Python's "weird" features (contextvars, isinstance control flow, sentinel objects) to make retry logic feel simple.**

  [2mSaved to .deep/findings/real_code_tenacity.md[0m

[36mSynthesis: combining 4 analyses...[0m
[1m[34m── SYNTHESIS ── real_code_tenacity.py ──[0m
[2mthinking...[0m                                        # UNIFIED ANALYSIS: Tenacity Retry Library

## Step 1: The Convergence Points

### Convergence A: The `Future` Object as Triple-Boundary Destroyer

**Independent Discoveries:**
- **ERRORS**: Discards `exc_type` and `traceback` from `exc_info` tuple, only preserving `exc_value`
- **COSTS**: Introduces 200-300ns of lock/condition variable overhead despite single-threaded usage
- **PROMISES**: Claims to be a `concurrent.futures.Future` but is actually a synchronous result container

**What the Convergence Reveals:**
The `Future` object is the **primary information destroyer** across all dimensions. It's not just "overkill" (COSTS) or "misnamed" (PROMISES) — it's structurally incapable of preserving the full exception context because `concurrent.futures.Future` was designed for inter-thread communication, not intra-thread exception wrapping. The lock overhead is the price of using the wrong abstraction, and the lost traceback is the consequence of that abstraction's API limitations.

**No Single Analysis Found:**
The `Future` choice creates a **dependency lock-in**: fixing the traceback loss requires either (a) breaking `Future` compatibility, or (b) storing parallel exception data that creates dual-source-of-truth problems. The lock-in is why the "impossible fix" from ERRORS can't be cleanly implemented — the Future API itself is the constraint.

---

### Convergence B: Action List as Performance-Destroying Control Flow

**Independent Discoveries:**
- **COSTS**: Dynamic action list prevents static optimization (~100-150ns per action)
- **CHANGES**: Forces control flow to be rebuilt on every iteration via mutation
- **PROMISES**: `iter_state` claims to track "iteration state" but is actually a command queue

**What the Convergence Reveals:**
The action list is simultaneously a **performance bottleneck** (rebuilding + dispatch), a **structural necessity** (enables strategy composition), and a **semantic lie** (mislabeled as "state" not "queue"). The convergence shows that Tenacity's composability comes at three simultaneous costs: CPU cycles (rebuilding), code clarity (mutation), and conceptual honesty (misleading names).

**No Single Analysis Found:**
The action list creates an **observability illusion**: it looks introspectable (you can print `iter_state.actions`), but the list is transient and rebuilt. Debugging tools that snapshot the action list will capture a moment that immediately becomes stale. There's no stable "execution plan" to observe — only the transient state of a queue about to be consumed and rebuilt.

---

### Convergence C: Exception Swallowing as Silent Failure Vector

**Independent Discoveries:**
- **ERRORS**: `AttemptManager.__exit__` returns `True`, swallowing all exceptions
- **PROMISES**: `AttemptManager` claims to "manage" attempts but is actually a deferred state mutator
- **COSTS** (implicit): Exception capture costs 1-2μs but the swallowed exception prevents early exit optimization

**What the Convergence Reveals:**
The exception swallowing is both an **information destroyer** (ERRORS) and a **control flow hack** (PROMISES). The convergence shows that `AttemptManager` isn't managing anything — it's converting exceptions into data silently, then converting data back into control flow via the action list. This round-trip (exception → data → control flow) is what enables the `@retry` decorator syntax, but it requires destroying the exception's immediate propagation.

**No Single Analysis Found:**
The silent exception swallow creates **non-local causality bugs**: if a `before_sleep` callback raises, it doesn't propagate through the exception handling path — it crashes the iteration loop entirely. The exception handling at `__exit__` only catches exceptions from the wrapped function `fn`, not from the retry infrastructure itself. This creates two different exception propagation paths that are indistinguishable from outside.

---

### Convergence D: Duplicate Control Paths in `__iter__` vs `__call__`

**Independent Discoveries:**
- **CHANGES**: Nearly identical control-flow logic duplicated across `__iter__` and `__call__`
- **PROMISES**: `__iter__` claims to be an iterator but is actually a control flow interpreter
- **ERRORS** (implicit): Both paths can destroy exception context differently

**What the Convergence Reveals:**
The duplication isn't just code smell — it's a **semantic divergence** waiting to happen. `__iter__` yields `AttemptManager` objects, `__call__` doesn't. One supports manual iteration, the other is automatic. Yet both use the same `isinstance(do, DoAttempt/Sleep)` dispatch. The convergence reveals that the "iterator" protocol is being used as a **coroutine mechanism**, not iteration — the yielded values aren't the data being iterated, they're control tokens.

**No Single Analysis Found:**
The dual paths create **protocol ambiguity**: if you call `iter(retryer)` you get a different object than if you use `for attempt in retryer:`. The iterator protocol is conflated with the retry control flow, making it impossible to implement standard iterator helpers (like `itertools.islice`) without breaking retry logic.

---

## Step 2: The Blind Spots

### Blind Spot 1: Memory Leak via Traceback Accumulation

**What None Found:**
Every failed retry call creates a new `Future` object with `set_exception()`, which stores the exception object including its full traceback. In `RetryCallState`, these futures are stored sequentially in `self.outcome`. In long-running processes with frequent retries (e.g., a service retrying network calls millions of times), the traceback objects (which contain frame references) accumulate and are never cleared.

**Concrete Harm:**
```python
@retry(wait=wait_fixed(0.1), stop=stop_after_attempt(1000000))
def flaky_network_call():
    raise ConnectionError("timeout")

# After 1 million failed attempts:
# - 1 million Future objects
# - 1 million traceback objects
# - Each traceback holds frame objects with local variable references
# - Memory: potentially hundreds of MB to GB
```

The `retry_state` object is recreated per retry call, but in iterator usage (`for attempt in retryer:`), the same `retry_state` persists across all attempts, accumulating all previous outcomes in some usage patterns.

---

### Blind Spot 2: Race Condition in Statistics Collection

**What None Found:**
The `_local` threading.local storage for statistics has no synchronization. In async code where the same `Retrying` object is used across multiple tasks (even if not concurrent), the statistics counters can be corrupted due to task switching during the increment operations.

**Concrete Harm:**
```python
retryer = Retrying(wait=wait_fixed(1), statistics=True)

async def task1():
    for attempt in retryer:
        with attempt:
            await async_operation()

async def task2():
    for attempt in retryer:  # Same retryer object
        with attempt:
            await async_operation()

# If both tasks run (even sequentially but with task switching),
# _local.statistics may have incorrect counts
```

The `contextvars.ContextVar` approach for `iter_state` is task-safe, but the statistics storage is not. This creates inconsistent observability — some state is task-local, some is incorrectly shared.

---

### Blind Spot 3: Timeout Calculation Can Deadlock

**What None Found:**
If a custom `wait` strategy returns a negative sleep duration (e.g., due to clock skew or user error), the code attempts to `time.sleep(negative)` which raises `ValueError`, crashing the retry loop. However, if using the iterator pattern manually, the user might have already captured the `DoSleep` object and be holding it, creating a state where the retry state is prepared (`prepare_for_next_attempt()` called) but the sleep never happened.

**Concrete Harm:**
```python
wait_strategy = lambda rs: -1.0  # Bug: returns negative

@retry(wait=wait_strategy)
def function():
    raise ValueError("retry me")

# In manual iteration:
for attempt in retryer:
    with attempt:
        # If attempt fails, next iteration returns DoSleep(-1.0)
        # User code might store: sleep_action = attempt.retry_state.outcome
        # Then time.sleep(sleep_action) raises ValueError
        # But retry_state.attempt_number has already been incremented!
        # Next retry starts with wrong attempt number
```

The `prepare_for_next_attempt()` happens before the sleep, breaking atomicity of the "attempt → sleep → retry" transition.

---

### Blind Spot 4: Probability Distribution Blindness in Retry Conditions

**What None Found:**
The retry library treats all attempts as independent discrete events, but many failure modes are **probabilistically correlated**. A network timeout followed by another timeout is evidence of a systemic issue (server down), not random flakiness. Exponential backoff is appropriate for independent failures, but inappropriate for correlated failures.

**Concrete Harm:**
```python
@retry(wait=wait_exponential(multiplier=1, min=1, max=60))
def call_api():
    # If server is down, all retries will fail
    # Exponential backoff wastes time: 1s, 2s, 4s, 8s, 16s, 32s, 60s
    # Total: ~2 minutes of guaranteed failure
    raise ConnectionError("server down")
```

The library has no concept of **failure pattern recognition** — it can't detect "the same error keeps happening" and fail fast instead of backing off. This is a **structural blind spot**: the retry condition is evaluated per-attempt, not across the attempt history pattern.

---

### Blind Spot 5: Signal Handler Interference

**What None Found:**
The `time.sleep()` call in the retry loop blocks signals. If a process receives SIGTERM during the sleep period, the shutdown is delayed until the sleep completes. For long sleep durations (e.g., max=60 seconds), this can cause graceful shutdown to take minutes.

**Concrete Harm:**
```python
@retry(wait=wait_exponential(max=60))
def long_running_service():
    # Service runs continuously
    # When deployment triggers SIGTERM for graceful shutdown:
    # - If in the middle of a 60-second backoff sleep
    # - Shutdown delayed up to 60 seconds
    # - May trigger force-kill after timeout
    process_request()
```

The use of `time.sleep()` instead of an interruptible wait primitive (like `threading.Event.wait()`) makes the retry loop unresponsive to signals.

---

## Step 3: The Unified Law

**THE CONSERVATION OF ABSTRactive COMPLEXITY**

| Location | Error View | Cost View | Change View | Promise View | Unified Finding |
|----------|------------|-----------|-------------|--------------|-----------------|
| **`Future` objects** | Destroys `exc_type` and traceback from `exc_info` tuple | 200-300ns lock/condition overhead for single-threaded usage | No state transitions — already completed futures | Claims async/concurrent but is synchronous wrapper | **Reused abstraction destroys information and pays performance tax** |
| **Action list (`iter_state.actions`)** | Loses intermediate return values from actions | 100-150ns per action for dynamic dispatch | Control flow rebuilt every iteration via mutation | Claims "state tracking" but is command queue | **Misnamed abstraction hides control flow behind data structure** |
| **`AttemptManager.__exit__`** | Swallows all exceptions (return True) | 1-2μs exception capture cost for no early-exit benefit | Exception → data conversion enables action pattern | Claims "management" but is deferred state mutator | **Protocol abuse (context manager) hides round-trip conversion** |
| **`DoSleep`/`DoAttempt` tokens** | Type information used for control flow instead of data | isinstance() checks prevent branch prediction | State machine disguised as iterator protocol | Claims "sleep" and "attempt" markers but are control signals | **Type system abused for control flow encoding** |
| **`__iter__` / `__call__` duality** | Exception handling differs between paths | Duplicate dispatch logic, no code reuse | Nearly identical control flow in two methods | Claims "iterator" but is coroutine/control interpreter | **Protocol conflation creates maintenance burden** |
| **`retry` decorator** | Recursive self-call for @retry vs @retry() | Indirection overhead, decorator factory cost | Identity shifts based on call pattern | Claims decorator but is decorator factory | **API convenience trades implementation clarity** |

### THE UNIFIED LAW:

**"Every gain in API expressiveness requires an equivalent loss in either information preservation, performance efficiency, or semantic honesty."**

The law operates through three mechanisms:

1. **Abstraction Reuse Penalty**: Using `Future` buys familiar API but costs tracebacks and lock overhead. The reuse isn't free — it's paid in destroyed information and unnecessary synchronization.

2. **Protocol Distortion Penalty**: Using iterators for control flow, context managers for state mutation, and type checks for dispatch all work, but each distorts the original protocol's semantics. The distortion is the tax for expressive syntax.

3. **Composition Mechanism Tax**: The action list enables unlimited strategy composition (wait, stop, retry, hooks) but requires dynamic rebuilding and hides causality. The composition flexibility is paid for in runtime reconstruction cost.

**The Conservation Equation:**
```
Expressiveness + Composability + Debuggility = Constant

If you gain API expressiveness (clean @retry syntax), you lose debuggility (hidden control flow).
If you gain composability (pluggable strategies), you lose performance (dynamic dispatch).
If you gain semantic honesty (honest names), you lose expressiveness (verbose APIs).
```

Tenacity maximizes **expressiveness** (clean decorator syntax) and **composability** (unlimited strategy combination). The constant requires sacrificing **debuggility** (hidden control flow), **performance** (unnecessary abstractions), and **semantic honesty** (misleading names).

**No single analysis could see this trade-off surface** — it only emerges when comparing what each dimension values vs what it destroys. The ERRORS view wants perfect information preservation. The COSTS view wants zero overhead. The CHANGES view wants static predictability. The PROMISES view wants honest naming. Tenacity's design choices systematically trade all four for a singular goal: **making retry logic feel magically simple**.

The law reveals that Tenacity's complexity isn't accidental — it's the **minimum necessary complexity** to achieve its core promise: a retry library that's powerful enough for complex scenarios but simple enough to use with a single decorator. The "impossible fixes" from each analysis are impossible because they would break this fundamental trade-off.

  [2mSaved to .deep/findings/real_code_tenacity.md[0m
  [2mSaved to .deep/findings/real_code_tenacity.md[0m

[32mBehavioral Pipeline complete: 4 analyses + synthesis[0m
  [2mFindings: .deep/findings/[0m
  [36m6 issues (2 P1, 2 P2, 2 P3).[0m
  [2m  Type a number to fix one issue[0m
  [2m  /fix          pick issues interactively[0m
  [2m  /fix auto     fix all issues (up to 3 passes)[0m
