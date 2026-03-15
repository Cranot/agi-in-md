Here's a structural analysis of the Tenacity retry module, organized by what each pattern hides or assumes:

---

## Patterns

**Dynamic action queue (the core mechanism)**

`_begin_iter` → `_post_retry_check_actions` → `_post_stop_check_actions` each append to `iter_state.actions` *while `iter()` is iterating it*. Python list `for` loops visit newly appended items, so this is effectively a self-building work queue. The loop terminates when nothing more is appended.

This is an unusual pattern. It's not a recursive call chain (no stack depth) and not a fixed state machine (transitions aren't hardcoded). It reads as a linear list but executes as a trampoline. The asymmetry in `_begin_iter` (adds `before` only when `fut is None`) is how "first attempt" vs "retry" is distinguished — by whether the action list was built in the first branch or the second.

**Copy-on-call isolation**

`wraps()` calls `self.copy()` before each invocation so each call gets a fresh statistics dict and `IterState`. The intent: concurrent calls don't share state.

**Thread-local double storage**

`statistics` and `iter_state` live on `self._local` (a `threading.local`), so concurrent threads each get their own instance.

---

## Problems

### 1. Statistics alias breaks thread isolation (real bug)

In `wraps()`:
```python
copy = self.copy()
wrapped_f.statistics = copy.statistics      # points wrapped_f.statistics at copy's dict
self._local.statistics = copy.statistics    # overwrites original's thread-local to same dict
```

`copy.statistics` accesses `copy._local.statistics` — a different `threading.local` from `self._local`. The line `self._local.statistics = copy.statistics` stores the copy's dict as a plain object reference on `self`'s thread-local. But `wrapped_f.statistics` is a plain attribute on the function object, not thread-local. Under concurrent calls:

- Thread A: creates `copy_A`, sets `wrapped_f.statistics = copy_A.statistics`
- Thread B: creates `copy_B`, sets `wrapped_f.statistics = copy_B.statistics` (overwrites A's reference)
- Thread A reads `wrapped_f.statistics` → gets B's stats

The thread-local machinery protects the *copy* during execution, but `wrapped_f.statistics` leaks the last writer's data to any reader. The initial `wrapped_f.statistics = {}` at decoration time is overwritten on every call.

### 2. `TryAgain` bypasses all retry predicates

In `_begin_iter`:
```python
self.iter_state.is_explicit_retry = fut.failed and isinstance(fut.exception(), TryAgain)
if not self.iter_state.is_explicit_retry:
    self._add_action_func(self._run_retry)
```

When `TryAgain` is raised, `_run_retry` is *skipped entirely* — the user's custom `retry=` predicate never runs. `TryAgain` forces a retry unconditionally, overriding `retry=retry_if_exception_type(SomeError)` or any custom predicate. There's no path to "raise TryAgain but still check the retry condition." Users who use `TryAgain` inside a function with a stop condition may be surprised it ignores their retry filter.

### 3. Traceback dropped in `set_exception`

```python
def set_exception(self, exc_info):
    fut.set_exception(exc_info[1])   # exc_info[2] = traceback, discarded
```

`exc_info` is `(type, value, traceback)`. Only the exception value is stored. `futures.Future.set_exception` doesn't accept a traceback. When `RetryError.reraise()` re-raises the last attempt's exception, the original call-site traceback is gone — you get the re-raise point instead.

### 4. `Future` inherits heavyweight machinery it doesn't need

`Future` extends `concurrent.futures.Future`, which wraps every operation in a `threading.Condition` lock. This is a value-holder used in a single-threaded retry loop — it never needs cancellation, callbacks, or multi-waiter notification. The inheritance exists to get `.result()` / `.exception()` semantics, but the lock overhead is paid on every `set_result` / `set_exception` call.

### 5. `AttemptManager` always sets result to `None`

```python
def __exit__(self, exc_type, exc_value, traceback):
    if exc_type is not None:
        self.retry_state.set_exception(...)
        return True
    self.retry_state.set_result(None)   # always None
```

The iterator API (`for attempt in Retrying(): with attempt: ...`) has no way to capture a return value. The result you care about must be assigned outside the block and read after the loop. This is an inherent limitation of Python context managers — you can't yield a value from `__exit__` — but it means users who want to do `result = attempt.call(fn)` must use the functional API instead.

### 6. `before` fires only once; `after` fires per-retry — asymmetry is structural

`before` is added to the action list only when `fut is None` (first iteration). `after` is added in `_post_retry_check_actions` which runs on every subsequent iter call. The names imply symmetry (`before attempt` / `after attempt`) but the semantics are `before first attempt` / `after each retry`. This is documented but the implementation makes the asymmetry invisible — you have to trace through `_begin_iter`'s branch conditions to see it.

---

## Conservation law

The copy-on-call pattern conserves per-call isolation — but only inside the execution path. Every mechanism that tries to expose state externally (e.g., `wrapped_f.statistics`) breaks the isolation invariant, because function attributes are shared across all threads. The library conserves isolation *internally* at the cost of *observability* externally. You can have thread-safe retrying, or you can have readable statistics from outside the call, but the current design can't fully deliver both simultaneously.
