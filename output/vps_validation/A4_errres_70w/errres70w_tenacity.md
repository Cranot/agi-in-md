# Step 1: The Shared State

1. `_iter_state_var` (ContextVar):
   - Writer: `_begin_iter()`, `_post_retry_check_actions()`, `_post_stop_check_actions()`
   - Reader: `iter_state` property
   - Unchecked assumption: Variable exists in current context

2. `self._local.statistics` (thread-local dict):
   - Writer: `statistics` property, `begin()`, `_post_stop_check_actions()`
   - Reader: `statistics` property
   - Unchecked assumption: Thread-local storage is properly initialized

3. `retry_state` (RetryCallState instance):
   - Writer: `Retrying.__call__()`, `iter()`, `_begin_iter()`, `_post_retry_check_actions()`, `_post_stop_check_actions()`, `prepare_for_next_attempt()`
   - Reader: All methods in `BaseRetrying`
   - Unchecked assumption: Object exists and is properly initialized

# Step 2: The Corruption Cascade

```
Writer: Retrying.__call__() mid-update
  ├─ Creates retry_state but doesn't fully initialize
  ├─ Calls self.iter(retry_state=retry_state)
  │   └─ Calls _begin_iter(retry_state)
  │       └─ Accesses _iter_state_var.get() - ERROR: uninitialized context
  └─ Retry_state may have incomplete state if exception occurs
```

```
Writer: _begin_iter() mid-update
  ├─ Calls self.iter_state.reset() - works on partially initialized state
  ├─ Accesses retry_state.outcome - ERROR: may be None
  └─ Sets iter_state.is_explicit_retry based on faulty outcome check
```

```
Writer: _post_stop_check_actions() mid-update
  ├─ Accesses self.iter_state.stop_run_result - may be uninitialized
  ├─ Modifies self.statistics - may be corrupted
  └─ Creates actions that read from corrupted state
```

Classification: All are ERROR - no silent failures in this cascade, all will raise exceptions when accessing uninitialized state.

# Step 3: The Silent Exits

| Chain | Corruption Entry | Hops | Exit Type | Missing Check | Blocking Contract |
|-------|------------------|------|-----------|---------------|-------------------|
| None detected | - | - | - | - | - |

No silent exits detected in this codebase. All potential failures are explicit errors that will raise exceptions:

1. Accessing uninitialized `_iter_state_var` raises LookupError
2. Accessing `retry_state.outcome` when None is handled by design
3. All state modifications have proper initialization paths

The code follows a strict action pattern where all necessary state is initialized before use, with proper exception handling for the retry mechanism.
