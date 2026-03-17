# Emergence Analysis: Tenacity Retry Library

## Step 1: Interaction Map

| # | Component A | Component B | Coupling Mechanism | A assumes about B | B assumes about A |
|---|-------------|-------------|-------------------|-------------------|-------------------|
| 1 | `_iter_state_var` (ContextVar) | `IterState` | Global context variable accessed via property getter | ContextVar is properly isolated per async context | IterState is initialized before any access |
| 2 | `IterState` | `BaseRetrying._local` | Dual state mechanisms (ContextVar + threading.local) | Both provide isolation without interaction | Statistics and iter_state don't need synchronization |
| 3 | `RetryCallState` | `BaseRetrying.statistics` | Mutable dict reference held across copy boundary | Dict structure is stable, keys don't change | Updates are atomic, no race with reads |
| 4 | `AttemptManager` | `RetryCallState` | Manager receives state reference, modifies it in `__exit__` | `__exit__` always called after `__enter__` | Only one of set_result or exception handling happens |
| 5 | `IterState.actions` list | `iter()` method | Self-modifying list: actions append actions during execution | List copy (`list()`) prevents iteration-modification races | Actions don't modify other actions' effects |
| 6 | `DoAttempt`/`DoSleep` sentinels | `__iter__`/`__call__` loops | Type-based control flow dispatch | Only these 3 types are returned from `iter()` | Type check via `isinstance` is sufficient dispatch |
| 7 | `RetrySignal` exception | `is_explicit_retry` flag | Exception type used as control signal, not error | RetrySignal is never accidentally raised by user code | Flag correctly reflects exception state at check time |
| 8 | `copy()` method | `wraps()` decorator | Fresh instance per call, but statistics dict shared | Copy is complete and independent | Statistics reference is intentionally shared |
| 9 | `before`/`after` hooks | `retry`/`stop` decisions | Hooks execute regardless of outcome | Hooks don't throw exceptions | Hooks don't modify retry_state in decision-affecting ways |
| 10 | `statistics` dict | 100-entry limit | Dict cleared when `len() > 100` | Clearing doesn't lose critical data mid-retry | 100 is appropriate threshold for any use case |
| 11 | `sleep` function injection | `wait` strategy calculations | Callable injected, called with calculated value | Sleep behaves like `time.sleep` (blocks, no throw) | `upcoming_sleep` is always a valid float |
| 12 | `Future` (custom subclass) | `concurrent.futures.Future` | Inheritance from stdlib class | Future API is stable across Python versions | `failed` property correctly wraps `exception()` check |
| 13 | `retry_error_callback` | `retry_error_cls` | Callback takes precedence, skips exception construction | Callback handles outcome properly | Only one error handling path executes |
| 14 | `before_sleep` hook | `DoSleep` execution | Hook runs immediately before sleep | Hook doesn't prevent or modify sleep duration | `upcoming_sleep` is finalized before hook runs |
| 15 | `RetryCallState.outcome` | `RetryError(last_attempt)` | Future passed to exception constructor | Outcome is always a Future when accessed | RetryError can extract what it needs from Future |
| 16 | `_first_set` helper | `copy()` arguments | Sentinel `_unset` checked via identity, not truthiness | Callers use `_unset`, never `None` for "not provided" | `None` means "disable this feature", not "not set" |
| 17 | `attempt_number` | `Future` construction | 1-indexed counter passed to Future | Counter starts at 1, increments after each attempt | Future doesn't modify attempt_number |
| 18 | `ContextVar` | `__call__` vs `__iter__` | `__call__` sets ContextVar; `__iter__` relies on property getter | ContextVar is set before any IterState access | Same ContextVar works for sync and async contexts |

---

## Step 2: Emergent Behaviors

### EB1: Dynamic State Machine Construction
**What the system does:** Builds a state machine at runtime by appending actions to a list, where each action can append more actions. No single component knows the full state graph.

**Trace:** `_begin_iter()` → `_add_action_func()` → `_post_retry_check_actions()` → `_post_stop_check_actions()` creates a chain where:
- First call: appends `before` hook → `DoAttempt` sentinel
- After attempt: appends `_run_retry` → `_post_retry_check_actions`
- If retry: appends `after` → `_run_wait` → `_run_stop` → `_post_stop_check_actions`
- If stop: appends either `retry_error_callback` or `exc_check` or `next_action` → `before_sleep` → `DoSleep`

The state machine topology is determined by runtime conditions (exception type, retry decision, stop decision) and is built while being traversed.

### EB2: Implicit Coroutine Protocol via Sentinel Types
**What the system does:** Uses type-checking on return values to implement coroutine-like yield/resume without generators. `DoAttempt` means "yield to user code", `DoSleep` means "yield to time", anything else means "return".

**Trace:** `iter()` returns → `isinstance(do, DoAttempt)` → yield `AttemptManager` OR `isinstance(do, DoSleep)` → call `self.sleep(do)` OR `break`

The protocol is invisible to type checkers. No abstract base class defines it. The three branches are the entire retry lifecycle encoded as types.

### EB3: Exception-as-Signaling Side Channel
**What the system does:** Uses `RetrySignal` exception to communicate "retry now" without going through normal retry decision logic. Creates a control path invisible to `retry` strategy.

**Trace:** User code raises `RetrySignal` → caught by `AttemptManager.__exit__` → stored in `outcome` → `_begin_iter()` checks `isinstance(fut.exception(), RetrySignal)` → sets `is_explicit_retry = True` → skips `_run_retry` → goes directly to wait/stop logic

This bypasses the `retry` strategy entirely. The user can force retry regardless of retry predicate.

### EB4: Dual Isolation Mechanisms Without Coordination
**What the system does:** Uses both `threading.local` (for statistics) and `ContextVar` (for iter_state) to isolate state. In async contexts, ContextVar provides coroutine isolation, but threading.local provides thread isolation. The two can diverge.

**Trace:** `statistics` property accesses `self._local` → `iter_state` property accesses `_iter_state_var.get()` → both are "isolated" but by different mechanisms

If a retry spans thread boundaries (e.g., thread pool executor), statistics and iter_state could desynchronize. Neither mechanism knows about the other.

### EB5: Statistics as Shared Mutable State Across Copy Boundary
**What the system does:** Each `copy()` creates a new `BaseRetrying` instance, but all copies share the same `statistics` dict via the same `_local` reference (within a thread).

**Trace:** `wraps()` creates `copy = self.copy()` → `wrapped_f.statistics = copy.statistics` → `statistics` property returns `self._local.statistics` (same dict for all copies in same thread)

Multiple concurrent retries in the same thread (if possible) would race on statistics. The "copy" is not a full isolation.

### EB6: Self-Healing Memory Limit via Clear-on-Overflow
**What the system does:** Statistics dict auto-clears when it exceeds 100 keys. This is a memory guard, but also loses history.

**Trace:** `statistics` property checks `if len(self._local.statistics) > 100: self._local.statistics.clear()`

Any code reading statistics after clear sees empty dict. The 100 threshold is arbitrary and undocumented.

### EB7: Timestamp Coupling via Dual Assignment
**What the system does:** `outcome` and `outcome_timestamp` must be set together. If one is set without the other, `seconds_since_start` returns wrong value.

**Trace:** `set_result()` and `set_exception()` both do `self.outcome, self.outcome_timestamp = fut, ts` as tuple assignment → `seconds_since_start` property computes `outcome_timestamp - start_time`

If a future subclass overrode setting behavior, or if `prepare_for_next_attempt()` cleared one but not the other, calculations would break.

### EB8: Copy-on-Read Race Window
**What the system does:** `for action in list(self.iter_state.actions)` copies the list before iteration, but actions can append during iteration. New actions execute in same loop iteration.

**Trace:** `iter()` copies list → iterates → action function calls `_add_action_func()` → appended action executes in same `for` loop (because `list()` was only of original list)

This is intentional (allows dynamic state machine building) but creates a window where the list being executed diverges from the list as it conceptually "should be".

### EB9: Exception Chain Integrity Dependency
**What the system does:** `raise retry_exc from fut.exception()` creates exception chain. If `fut.exception()` is `None` (no exception), the `from` clause gets `None`, creating unusual chain.

**Trace:** `_post_stop_check_actions` inner `exc_check` function → `raise retry_exc from fut.exception()` → if `fut.failed` is False but we reached this path, `fut.exception()` is None

The path to `exc_check` requires `stop_run_result = True`, which should only happen after a failed attempt, but the exception chain construction doesn't verify.

### EB10: Hook Execution Order Dependency on Outcome
**What the system does:** `before` hook runs before first attempt. `after` hook only runs if retry will happen. `before_sleep` only runs if sleep will happen. The hook execution order depends on runtime outcomes.

**Trace:** 
- First attempt: `before` → attempt → (no `after` because not retrying yet, just checking)
- Actually: `before` → attempt → if retry needed: `after` → wait → stop check → if continuing: `before_sleep` → sleep

The `after` hook runs AFTER retry decision, not after attempt. It means "after failed attempt that will be retried", not "after every attempt".

---

## Step 3: Invisible Contracts

| # | Invisible Contract | Who Would Break It | Symptom |
|---|-------------------|-------------------|---------|
| 1 | **IterState is reset before each iteration** | Code that modifies `iter_state` outside of `reset()`, or calls `iter()` without fresh ContextVar | Stale `actions` list, wrong `retry_run_result`, `is_explicit_retry` leakage between retries |
| 2 | **Statistics dict keys are exactly: start_time, attempt_number, idle_for, delay_since_first_attempt** | Code that reads/writes other keys, or code that renames these | `KeyError` or silent wrong values; `delay_since_first_attempt` calculation fails |
| 3 | **`outcome` is always a `Future` when passed to `RetryError`** | Code that sets `outcome` to non-Future (hard in current design, but possible via subclass) | `AttributeError: 'NoneType' object has no attribute 'failed'` in `RetryError.reraise()` |
| 4 | **Only `DoAttempt`, `DoSleep`, or result value are returned from `iter()`** | Action function that returns unexpected type | Infinite loop (neither branch matches) or premature return |
| 5 | **`RetrySignal` is only raised intentionally by retry-aware code** | User library code that happens to raise `RetrySignal` | Unexpected retry bypassing normal retry predicates |
| 6 | **`sleep` function never throws and blocks for exactly the given duration** | Custom `sleep` that throws or returns early | Retry loop breaks without cleanup; `idle_for` tracking wrong |
| 7 | **`before`/`after` hooks don't modify `retry_state` in decision-affecting ways** | Hook that sets `retry_state.outcome = some_future` | Retry decisions based on fabricated state |
| 8 | **`Future.failed` correctly reflects exception state** | Future that is cancelled (`.cancel()` returns True) | `exception()` returns None for cancelled Future, but `failed` returns True → wrong branch |
| 9 | **`copy()` arguments use `_unset` sentinel, not `None`** | Caller passing `None` to mean "use default" | `None` treated as "explicitly set to None", not "not provided" — disables feature instead of using default |
| 10 | **`attempt_number` is 1-indexed** | Code that expects 0-indexed attempts | Off-by-one errors in logging/display; first attempt is "attempt 1", not "attempt 0" |
| 11 | **ContextVar is set before `__call__` but `__iter__` relies on lazy init** | Using `__iter__` directly without ContextVar setup | State leakage if ContextVar already has value from previous retry in same context |
| 12 | **`enabled=False` skips ALL retry logic including statistics** | Code expecting statistics to be populated even when disabled | Empty `statistics` dict; `start_time` not set |
| 13 | **`retry_error_callback` return value becomes final result** | Callback that returns None or raises | Unexpected None result or unhandled exception |
| 14 | **`_first_set` checks identity, not truthiness** | Code passing empty string, 0, or False as intentional value | These values treated as "not set" and replaced with default |
| 15 | **`seconds_since_start` returns None if called before outcome** | Code expecting float | `None - start_time` would fail; caller must handle None |
| 16 | **`prepare_for_next_attempt()` clears outcome but not `idle_for`** | Code expecting clean slate after prepare | `idle_for` accumulates across attempts (intentional but surprising) |

---

## Step 4: Emergence Conservation Law

### **Strategy Composability × Execution Path Transparency = constant**

**Definition:**
- **Strategy Composability** = number of orthogonal strategy dimensions users can independently configure
- **Execution Path Transparency** = ability to trace through a single execution path by reading code linearly

**Evidence from Tenacity:**

| Strategy Dimension | Composability Contribution | Execution Opacity Contribution |
|-------------------|---------------------------|-------------------------------|
| `stop` (when to give up) | Can compose `stop_after_attempt`, `stop_after_delay`, custom predicates | Requires tracing through `_run_stop` → `stop_run_result` → `_post_stop_check_actions` branch |
| `wait` (how long between retries) | Can compose `wait_fixed`, `wait_random`, `wait_exponential`, `wait_combine` | Wait value flows through `_run_wait` → `upcoming_sleep` → `RetryAction` → `DoSleep` |
| `retry` (which errors trigger retry) | Can compose `retry_if_exception_type`, `retry_if_result`, custom predicates | Decision in `_run_retry` → `retry_run_result` → affects whether `after` hook runs |
| `before`/`after`/`before_sleep` hooks | Three independent injection points | Hooks execute at different points in action list; order depends on runtime decisions |
| `retry_error_cls`/`retry_error_callback` | Two ways to handle terminal failure | Callback bypasses exception construction entirely; invisible branch |
| `sleep` function injection | Can use `time.sleep`, `asyncio.sleep`, mock, etc. | Sleep call is in main loop, but sleep function is arbitrary |
| `reraise` flag | Changes exception presentation | Affects `exc_check` inner function; whether `reraise()` or `raise retry_exc` |

**The Conservation:**

```
7+ strategy dimensions × Low transparency = constant

If you want more composability, you MUST accept:
- Action list built at runtime
- Type-based dispatch
- Exception-based signaling
- Multiple state objects with different lifetimes
- Conditional hook execution

If you want more transparency, you MUST accept:
- Fewer strategy dimensions
- Harder to extend
- More code duplication for variations
```

**What the system ALWAYS produces when components interact:**

Regardless of which specific strategies are composed, the interaction ALWAYS produces:

1. **A hidden state machine** — The action list IS the state machine, but it's built dynamically. Every composition creates a different state machine topology, but all share the same construction mechanism.

2. **Deferred decision points** — Every strategy (`stop`, `wait`, `retry`) is a decision deferred to runtime. The composition surface is the set of decision points, and their interaction produces the execution path.

3. **Coupling between outcome and control flow** — The `Future.outcome` determines which branch of the state machine executes. Every composition has this coupling; it's the invariant.

**Meta-observation:** This conservation law applies to ALL strategy-pattern libraries. The more composable the strategies, the harder it is to predict execution by reading code. Tenacity is not unique; it's an instance of a universal trade-off.

**The Conservation Law in One Line:**

> **Every strategy you add requires another layer of indirection in the execution path.**
