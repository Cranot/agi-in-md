# Historical Decision Tracing: Tenacity Retry Library

## Step 1: Decision Fossils

### Fossil 1: ContextVars for Iteration State
**Decision:** Use `contextvars.ContextVar` for cross-call state sharing
**Evidence:** `_iter_state_var = contextvars.ContextVar('iter_state', default=None)` + `iter_state` property that lazily initializes
**Alternatives at decision time:** Thread-local storage (wouldn't work with async), explicit parameter threading (verbose), class instance state (breaks reentrancy)
**Reconstruction:** This was added when async/await support became necessary. The library needed state that flows through call stacks without explicit passing, working across both sync and async contexts.

### Fossil 2: Dynamic Action Queue Pattern
**Decision:** Build control flow by appending function objects to a list, then executing sequentially
**Evidence:** `IterState.actions: list`, `_add_action_func()`, `for action in list(self.iter_state.actions): result = action(retry_state)`
**Alternatives at decision time:** State machine with explicit transition table, recursive method calls, hardcoded if/else chain
**Reconstruction:** The action queue allows users to inject callbacks (before, after, before_sleep) at arbitrary points without modifying core logic. This was a composability decision.

### Fossil 3: Type-Based Control Flow Sentinels
**Decision:** Use distinct types (`DoAttempt`, `DoSleep`) as control flow markers returned from iteration
**Evidence:** `class DoAttempt: pass`, `class DoSleep(float): pass`, `isinstance(do, DoAttempt)` / `isinstance(do, DoSleep)` checks
**Alternatives at decision time:** Enum return values, tuple returns `(action_type, value)`, exception-based control flow
**Reconstruction:** Type-based dispatch allows `DoSleep` to also carry the sleep value (via `float` inheritance) while keeping the control flow readable. The naming "Do" prefix suggests an imperative intention.

### Fossil 4: Copy-on-Write Instance Isolation
**Decision:** Each wrapped call gets its own `copy()` of the retry object
**Evidence:** `copy = self.copy()` in `wrapped_f`, extensive `copy()` method with `_unset` sentinel pattern
**Alternatives at decision time:** Shared mutable state with locking, state reset between calls, immutable configuration
**Reconstruction:** This allows concurrent retries with different parameters (via `retry_with()`) while sharing configuration. The `_unset` sentinel pattern enables partial overrides without None ambiguity.

### Fossil 5: Dual Exception Hierarchy
**Decision:** `RetrySignal` for explicit retry control, `RetryError` for final failure reporting
**Evidence:** `class RetrySignal(Exception)` with doc "Control signal for explicit retry, not a real exception", `class RetryError(Exception)` with `reraise()` method
**Alternatives at decision time:** Single exception type with mode flag, return value signaling, callback-based control
**Reconstruction:** `RetrySignal` needed to be an exception to propagate through user code stacks, but semantically it's control flow. `RetryError` wraps the final failure for caller handling. This dualism emerged from the constraint that Python can't intercept `return` but can intercept `raise`.

---

## Step 2: Decision Dependencies

### Dependency Chain 1: Context Isolation
```
ContextVars decision → IterState as context-local → Cannot inspect state from outside retry loop → Debugging requires context awareness
```
**Cost to undo:** Medium-high. Would require threading `iter_state` through 8+ method signatures.

### Dependency Chain 2: Action Queue Architecture
```
Action queue decision → _begin_iter appends conditionally → _post_retry_check_actions appends conditionally → _post_stop_check_actions appends conditionally → Execution order becomes implicit
```
**Longest chain:** Action queue → sequential action types → DoSleep must come after wait calculation → before_sleep must come after RetryAction creation → Cannot reorder without breaking temporal invariants

**Cost to undo root:** High. The entire retry flow is built on action queuing. Would require rewriting `iter()` as a state machine with 6+ explicit states.

### Dependency Chain 3: Copy-on-Write Per-Call Isolation
```
Copy-on-write decision → wraps() creates copy → copy() preserves all callbacks → Callbacks cannot be modified mid-retry → Hot-patching impossible
```
**Cost to undo:** Medium. Could use mutable shared config with copy-on-read, but breaks `retry_with()` pattern.

---

## Step 3: Decision Conflicts

### Conflict 1: Dual Isolation Mechanisms
**Decisions:** `threading.local()` for `statistics` vs `contextvars.ContextVar` for `iter_state`
**Contradiction:** Statistics are thread-local (won't isolate in async contexts), iter_state is context-var (isolates in async). A retry that spans thread handoffs (e.g., thread pool executor) will have statistics attribution problems.
**Breaks first:** `statistics` under async load. Already visible in the `> 100` clear threshold — a defensive hack acknowledging unbounded growth in certain scenarios.

### Conflict 2: Dynamic Actions vs Fixed Sentinels
**Decisions:** Action queue is infinitely extensible vs `DoAttempt`/`DoSleep` are hardcoded types
**Contradiction:** Users can add arbitrary actions via callbacks, but the `__iter__` loop only knows how to handle two sentinel types. Any action that doesn't eventually produce DoAttempt/DoSleep breaks the loop (returns `None` → `break`).
**Breaks first:** The sentinel types. A callback that returns a value accidentally will cause silent loop termination.

### Conflict 3: Exception as Control Flow vs Exception as Error
**Decisions:** `RetrySignal` uses exception mechanism for control vs `RetryError` uses exception mechanism for error reporting
**Contradiction:** Both are exceptions, but semantically opposite. A bare `except Exception:` in user code will catch `RetrySignal` and break explicit retry. The `isinstance(fut.exception(), RetrySignal)` check is the patch.
**Breaks first:** User code with broad exception handlers. The `is_explicit_retry` flag is already the workaround.

---

## Step 4: Conservation Law

### The Conserved Quantity

**Explicitness × Flexibility = Constant**

Every decision trades one for the other:

| Decision | Explicitness Lost | Flexibility Gained |
|----------|-------------------|-------------------|
| ContextVars | State flow is invisible | Async/sync unified |
| Action queue | Control flow is implicit | Callbacks at any point |
| Type sentinels | New control types need code changes | Readable dispatch |
| Copy-on-write | Cannot hot-modify config | Concurrent safe retries |
| Dual exceptions | Must know which exception type | Control flow via raise |

### What the Project ALWAYS Protects

**Composability through indirection.** The library sacrifices:
- **Debugging speed** (action queue is hard to trace)
- **Static analysis** (type-based control flow defeats type checkers)
- **Performance** (copy on every call, action list rebuild each iteration)
- **Cognitive simplicity** (five layers of callback injection)

To protect:
- **User code remains untouched** (decorators, callbacks, no inheritance required)
- **Cross-context compatibility** (sync, async, threaded all work)
- **Retroactive modification** (`retry_with()` changes behavior post-decoration)

### What the Project ALWAYS Sacrifices

**Directness.** There is no "happy path" through this code — even the simplest retry goes through: copy → begin → iter → _begin_iter → action queue build → action queue execute → sentinel dispatch → back to iter → sleep or yield. Every operation is mediated through at least two indirection layers.

### The Implicit Priority

This library prioritizes **library authors over library users** in one dimension (complexity is hidden behind simple decorators) but **users over authors** in another (users can override anything via callbacks). The conservation law reveals: the library bends over backward to never break user code, accepting internal complexity as the cost.
