## Structural Analysis: Tenacity Retry Module

### Architecture Pattern: Dynamic Command Queue

The core design is a **self-modifying action chain**. `_begin_iter()` seeds an action list, then actions executed during `iter()` append MORE actions to that same list mid-iteration:

```
iter() loops over actions[]
  → _run_retry appends _post_retry_check_actions
    → which appends _run_wait, _run_stop, _post_stop_check_actions
      → which appends exc_check OR next_action + DoSleep
```

This is the defining structural decision. Everything else follows from it.

### What This Pattern Conceals

**1. Mutation during iteration is the load-bearing trick.**
`for action in self.iter_state.actions` works because CPython's list iterator sees appended items. The entire retry loop — decide, wait, stop-check, sleep — executes as ONE call to `iter()`, not as separate steps. Anyone reading `iter()` sees a simple 3-line loop; the actual control flow is 6-8 deep.

**2. Thread-local state creates invisible coupling.**
`iter_state` and `statistics` live on `threading.local()`, shared implicitly across `iter()` → `_begin_iter()` → `_post_retry_check_actions()` → `_post_stop_check_actions()`. No function signature reveals this dependency. The state is the hidden bus that connects the action chain.

**3. `wraps()` creates a split identity.**
Every invocation runs on a `copy()`, but `wrapped_f.retry` points to the original `self`. The line `self._local.statistics = copy.statistics` bridges them, but now statistics has two sources of truth. The original's thread-local and the copy's thread-local share the same dict object — until someone calls `wraps()` again.

**4. Dual bookkeeping for attempt tracking.**
`attempt_number` and `idle_for` exist in both `RetryCallState` and `self.statistics`, incremented in different places (`prepare_for_next_attempt` vs `next_action` closure in `_post_stop_check_actions`). They must stay synchronized, but nothing enforces this — it's a manual invariant.

### Concrete Problems

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **List mutation during iteration** — action chain depends on CPython list-append-during-for behavior. PyPy, Cython, or a future refactor to tuple could silently break | `iter()` + all `_add_action_func` callers | High (latent) |
| 2 | **Exception swallowing in AttemptManager** — `__exit__` returns `True` for ALL exceptions, storing them for later. BaseException subclasses (KeyboardInterrupt, SystemExit) get captured and retried | `AttemptManager.__exit__` | Medium |
| 3 | **`retry_error_callback` silently wins over `reraise`** — if both are set, callback is checked first in `_post_stop_check_actions`. No warning, no documentation of priority | `_post_stop_check_actions` | Low |
| 4 | **`DoSleep` inherits from `float`** — a type-check sentinel that's also a numeric value. `isinstance(do, DoSleep)` and `self.sleep(do)` use different properties of the same object. Passing `DoSleep(0)` is falsy | `DoSleep` + `__call__`/`__iter__` | Low |
| 5 | **`seconds_since_start` returns `None` before first outcome** — callers (like `_run_stop`) must handle this, but stop strategies may not expect `None` | `RetryCallState.seconds_since_start` | Medium |

### The Conservation Law

**Composition flexibility is conserved by state complexity.** Every pluggable strategy (`stop`, `wait`, `retry`, `before`, `after`, `before_sleep`) adds a slot the user can compose freely — but each slot requires thread-local state coordination, dual bookkeeping, and position-dependent action insertion. You cannot add a new hook point without threading it through the action chain, the iter_state, and both statistics stores.

The library's power (arbitrary strategy composition) and its fragility (implicit state coupling) are the same thing measured in different units.

### Prediction

The most likely future bug: someone adds a new action-chain step that assumes `iter_state.actions` has a fixed length at some point, not realizing earlier actions can append arbitrarily. The dynamic command queue pattern makes the action list's length a runtime property that no static analysis can predict.
