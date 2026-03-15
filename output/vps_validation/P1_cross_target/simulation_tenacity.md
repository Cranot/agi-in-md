# Temporal Simulation: Tenacity Retry Library

## Cycle 1: New Developer Joins

**Misunderstandings**: The action-chain architecture (`_add_action_func` building a list of lambdas executed sequentially) is deeply non-obvious. A new developer will treat `iter()` as a simple loop, not realizing it's a state machine that *builds then executes* behavior dynamically.

**Violated Assumption**: The `DoAttempt`/`DoSleep` return-type pattern. Developer adds logging that swallows these return values, or returns `None` instead, breaking the `isinstance` dispatch. The sentinel `NO_RESULT = object()` pattern gets copied incorrectly.

**What Breaks**: The `_iter_state_var` contextvar—developer assumes state is passed explicitly, creates functions that cross thread boundaries incorrectly. The `IterState.reset()` gets called at wrong times, losing `is_explicit_retry` flag mid-chain.

---

## Cycle 2: Dependency Update

**Shock Absorbers**: The `Future` wrapper class insulates from `concurrent.futures` changes. The `@dataclasses.dataclass(slots=True)` on `IterState` may break if dataclass internals shift—the `slots=True` parameter was added in Python 3.10.

**Shock Propagators**: `contextvars.ContextVar` behavior under asyncio is load-bearing. The `threading.local()` for statistics assumes specific memory model semantics.

**Calcified Patches**: Workaround for `functools.WRAPPER_ASSIGNMENTS` not including `__defaults__` and `__kwdefaults__`—becomes permanent compatibility shim. The `_first_set` helper pattern gets copy-pasted into three other files.

---

## Cycle 3: Original Author Leaves

**Lost Knowledge**:
- Why `RetrySignal` is an `Exception` subclass (control flow, not error)—now treated as real exception by error handlers
- The distinction between `IterState` (per-context, action chain) vs `RetryCallState` (per-call, outcome tracking)—both seem redundant
- Why `statistics` clears at 100 entries (memory guard? performance? arbitrary?)
- The `retry_run_result` vs `stop_run_result` precedence order

**Cargo Cult**: The entire `_post_retry_check_actions` → `_post_stop_check_actions` chain is copied without understanding. The `outcome_timestamp` field is populated but never read.

**Unfixable**: The dual-state architecture. Removing `IterState` would require threading state through ~15 call sites. Removing `RetryCallState` would break the `Future` abstraction. Both must coexist forever.

---

## Cycle 4: 10x Usage Growth

**Failed Performance Assumptions**:
- Action list rebuilt on *every iteration*—O(retry_count) allocations become measurable
- `RetryCallState` instantiated fresh each call—GC pressure
- `time.monotonic()` called 4+ times per attempt—syscall overhead
- `statistics` dict under thread-local with unbounded growth before the 100-clear

**Permanent Infrastructure**: The `copy()` pattern for isolation—creating full object copies per-retry becomes load-bearing for concurrent usage. The `wraps()` decorator's `statistics = {}` mutation becomes API that users depend on for monitoring.

---

## Cycle 5: Security Audit

**Hidden Trust Assumptions**:
- `set_exception((exc_type, exc_value, traceback))` stores raw traceback—could leak sensitive locals
- `fn(*args, **kwargs)` executes arbitrary callables with no validation
- `RetrySignal` can be raised by user code to force infinite retry (DoS vector)
- The global `_iter_state_var` name is fixed—collision risk in shared environments

**Non-Boundaries**:
- `threading.local()` for statistics is *not* process-safe (multiprocessing shares nothing)
- `contextvars` isolation is per-asyncio-task, but `Retrying.__call__` is synchronous—mixed usage leaks state
- The `retry_error_callback` receives full `RetryCallState` including `args`/`kwargs`—data exfiltration path

---

## Derive: Conservation Law

**Calcification Pattern**: The action-chain indirection that enables flexibility becomes the primary source of incomprehensibility. Each cycle adds patches that *use* the action chain rather than simplifying it.

**Conservation Law**: 
```
Architectural Flexibility × Code Comprehensibility = Constant
```

As flexibility is *exercised* (hooks added, callbacks inserted), comprehensibility decreases proportionally. The library sacrificed **obviousness** for **extensibility**—every hook point is a place where mental model must track "what could happen here."

**What Was Sacrificed**: The ability to read `iter()` and understand what it does in one pass. The action chain is a *meta-program*—code that writes code—and humans struggle to simulate meta-programs.

---

## Diagnostic

**My Simulation's Temporal Assumption**: I assumed *continuous active maintenance*—that each cycle brings change. But tenacity-like libraries often reach stability and see *minimal* modification for years.

**What Cycle 6 Would Reveal**: If the library enters maintenance stasis, the calcification *reverses*. Documentation accumulates. StackOverflow answers crystallize patterns. The "unfixable" dual-state architecture becomes *normalized*—nobody questions it because nobody changes it. The conservation law shifts: **Obscurity × Maintenance Frequency = Constant**. Unused code doesn't rot; *changed* code rots.

My analysis also assumed the action-chain pattern is a *design flaw*. Cycle 6 might show it's actually a *successful abstraction*—the hooks that seemed confusing are exactly what power tenacity's plugin ecosystem (custom wait strategies, retry conditions, observability). What I called "cargo cult" might be "stable API."
