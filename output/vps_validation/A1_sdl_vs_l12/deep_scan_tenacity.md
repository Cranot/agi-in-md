# Structural Deep-Scan Analysis: Tenacity Retry Library

## Step 1: Conservation Law

**Conserved Quantity: "Composable Strategies × State Isolation × Control Flow Visibility"**

The system manages an irreducible tension between three properties that cannot coexist:

1. **Composable retry behaviors** — Stop conditions, wait strategies, and retry predicates that can be freely combined
2. **Per-call state isolation** — Statistics and iteration state that don't leak between concurrent retries
3. **Explicit control flow** — Retry logic that's traceable rather than hidden in framework magic

**The O(n) cost that cannot be optimized away:** Every retry iteration rebuilds the action chain from scratch. Lines 146-177 show `_begin_iter` → `_post_retry_check_actions` → `_post_stop_check_actions` appending 4-7 closures per attempt. This is not cacheable because each closure captures current `retry_state` — the cost is conserved, paid on every loop.

**What the system pays:** It gains composability (strategies are just callables) but pays with:
- Global-ish state via `contextvars` (line 13) and `threading.local` (line 103)
- Action chain reconstruction on every iteration
- Implicit control flow through closure chaining

---

## Step 2: Information Laundering

**Three sites where diagnostic specificity is destroyed:**

### Site A: Statistics Silently Discarded (Lines 112-115)
```python
@property
def statistics(self):
    if not hasattr(self._local, "statistics"):
        self._local.statistics = {}
    if len(self._local.statistics) > 100:
        self._local.statistics.clear()  # ← INFORMATION DESTRUCTION
    return self._local.statistics
```
**What's laundered:** A runaway retry loop (100+ retries) erases ALL diagnostic history. The operator learns "something went wrong" but loses timing data, attempt counts, and idle time that would diagnose *why* it exceeded 100.

### Site B: Exception Chain Truncation (Lines 196-199)
```python
def exc_check(rs):
    fut = rs.outcome
    retry_exc = self.retry_error_cls(fut)
    if self.reraise:
        retry_exc.reraise()
    raise retry_exc from fut.exception()  # ← Only LAST exception preserved
```
**What's laundered:** After 47 retry attempts with different exceptions, only the *final* exception appears in the chain. The 46 prior failure modes are permanently lost — no way to see "first 30 were ConnectionTimeout, last 17 were PermissionDenied."

### Site C: RetrySignal Masquerading (Lines 24-26, 166)
```python
class RetrySignal(Exception):
    """Control signal for explicit retry, not a real exception."""
    pass

# Later:
self.iter_state.is_explicit_retry = fut.failed and isinstance(fut.exception(), RetrySignal)
```
**What's laundered:** `RetrySignal` is an `Exception` subclass used for control flow. If user code accidentally catches `Exception` broadly, they intercept the retry mechanism. The "exception-ness" of this signal launders its true nature as a control flow primitive.

---

## Step 3: Structural Bugs

### A) Async State Handoff Violation: ContextVar Race

**Location:** Lines 13, 117-122, 219

```python
# Global context variable
_iter_state_var = contextvars.ContextVar('iter_state', default=None)

# Property that creates on demand
@property
def iter_state(self):
    state = _iter_state_var.get()
    if state is None:
        state = IterState()
        _iter_state_var.set(state)  # ← CREATES NEW STATE
    return state

# But __call__ also sets unconditionally
def __call__(self, fn, *args, **kwargs):
    _iter_state_var.set(IterState())  # ← OVERWRITES EXISTING
    self.begin()
```

**The bug:** If `iter_state` property is accessed *before* `__call__` sets it (e.g., in a `before` hook during setup), a fresh `IterState` is created. Then `__call__` immediately overwrites it with another fresh instance. The first instance's `actions` list is orphaned.

**Concurrent hazard:** In async code, if one coroutine yields after `_iter_state_var.set()` but before `begin()`, and another retry starts, both share the same ContextVar state. The action lists interleave.

### B) Priority Inversion in Search: Last-Result-Wins

**Location:** Lines 150-155

```python
def iter(self, retry_state):
    self._begin_iter(retry_state)
    result = None
    for action in list(self.iter_state.actions):
        result = action(retry_state)  # ← OVERWRITES PREVIOUS
    return result
```

**The bug:** The loop returns only the *last* action's result. The action chain is:
1. `before` hook → returns something (discarded)
2. `_run_retry` → returns bool (discarded)
3. `_post_retry_check_actions` → returns None (discarded)
4. Final action returns `DoAttempt` or `DoSleep`

If a user-provided `before` hook returns a meaningful value, it's silently lost. The "first match" (DoAttempt from early in chain) should control flow, but "last match" wins by overwriting.

### C) Edge Case in Composition: Zero-Wait Sleep

**Location:** Lines 131-135, 180-181

```python
def _run_wait(self, retry_state):
    if self.wait:
        sleep = self.wait(retry_state)
    else:
        sleep = 0.0
    retry_state.upcoming_sleep = sleep  # ← No validation

# Later consumed:
self._add_action_func(lambda rs: DoSleep(rs.upcoming_sleep))
```

**The bug:** If a custom wait strategy returns a negative number (buggy exponential backoff with overflow, or malformed config), `DoSleep(-1.0)` is created. When passed to `self.sleep(do)` (line 225), this calls `time.sleep(-1.0)` which on some platforms is undefined behavior — may raise, may sleep 0, may sleep indefinitely.

**Also:** `seconds_since_start` returns `None` before first outcome (line 251). Wait strategies using this value without null-checking will crash or produce NaN:

```python
@property
def seconds_since_start(self):
    if self.outcome_timestamp is None:
        return None  # ← First attempt has no outcome yet
    return self.outcome_timestamp - self.start_time
```

A wait strategy like `wait_exponential(multiplier=seconds_since_start)` will fail on attempt 1.

---

## Summary

| Finding | Severity | Impact |
|---------|----------|--------|
| Statistics cleared at 100 entries | Medium | Diagnostic loss in failure scenarios |
| Exception chain truncation | High | Post-mortem debugging impaired |
| ContextVar race condition | High | Subtle state corruption in async/concurrent use |
| Last-result-wins in action loop | Low | User hooks' return values ignored |
| Negative/None sleep values | Medium | Undefined behavior or crashes |
