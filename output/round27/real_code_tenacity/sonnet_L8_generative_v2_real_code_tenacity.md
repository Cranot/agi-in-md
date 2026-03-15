## Structural Diagnosis

### The Falsifiable Claim

**The deepest structural problem: `iter()` is not a pipeline executor — it is a continuation-passing interpreter in disguise. Each action in `self.iter_state.actions` may append new actions to the same list currently being iterated, making control flow an emergent property of runtime mutation, not static structure.**

**Falsifiable test:** Replace the loop in `iter()`:
```python
# Current (dynamic — sees appended actions)
for action in self.iter_state.actions:

# Snapshot (static — breaks retry logic entirely)
for action in list(self.iter_state.actions):
```
Snapshotting breaks all retry behavior. `_post_retry_check_actions` would run but its appended continuations would silently vanish. The claim is confirmed if this single character-level change causes correct test cases to fail.

---

### Three Experts

**A (Defender):** The continuation-stack pattern is the deepest problem. Trace one retry cycle through `_begin_iter → _post_retry_check_actions → _post_stop_check_actions`:

```
Initial list:    [_run_retry, _post_retry_check_actions]
After _run_retry executes:  (list unchanged, side effect on iter_state.retry_run_result)
After _post_retry_check_actions executes, IF retrying:
                [_run_retry, _post_retry_check_actions, after, _run_wait, _run_stop, _post_stop_check_actions]
After _post_stop_check_actions executes, IF NOT stopping:
                [..., next_action, before_sleep, lambda DoSleep]
```

The list grows *while being iterated*. Python's list iteration allows this because it uses an incrementing index, not a snapshot. This is a correctness dependency on CPython implementation behavior. The control flow graph cannot be determined without executing the code. That's not a pipeline — it's an interpreter.

**B (Attacker):** The continuation-stack is a symptom. The real problem is **state promiscuity across three orthogonal mutable objects**:
- `IterState` holds *current iteration plan state* (the continuation list, boolean flags)
- `RetryCallState` holds *per-call lifecycle state* (outcome, timing, attempt count)
- `BaseRetrying._local` holds *per-thread cross-call state* (statistics, the IterState itself)

These three communicate entirely through side effects. `_run_retry` returns nothing — it writes `self.iter_state.retry_run_result`. `_run_stop` returns nothing — it writes `self.iter_state.stop_run_result`. Then `_post_retry_check_actions` reads those flags to decide what to append. This is implicit message-passing through shared mutation. The action list mutation is just the most visible manifestation of a design that uses state objects as its communication medium throughout.

**C (Prober):** Both of you assume this code *should* be clear. What are you taking for granted?

You're both treating this as design failure, but Tenacity supports three usage modes with shared core logic:
- `Retrying()(fn)` — direct call
- `for attempt in Retrying():` — context manager
- `AsyncRetrying()(fn)` — async (not shown, in full file)

What you're both assuming: that there exists a cleaner architecture that satisfies all three modes equally. The action-list mutation may be a *deliberate* lowest-common-denominator — the only mechanism that doesn't require async/await, doesn't require multiple code paths, and works as both iterator protocol and direct caller.

Also: you're both assuming thread-local state is a thread-safety mechanism. It's not. `_local` is per-thread, but the design assumes single-call-at-a-time *per thread*. If the same thread's call stack hits `__iter__` while another `__call__` is executing (e.g., a before-hook that itself retries), they share `IterState`. Neither of you named this.

---

### Claim Transformation

**Original:** The problem is the self-mutating continuation list.

**Transformed:** The problem is that the design must serve three execution protocols (sync call, iterator, async) through one mechanism, and it solves this by choosing mutable shared state as the universal communication medium. The self-mutating list is not a mistake — it's the load-bearing mechanism that allows `iter()` to be both the engine for `__call__` and `__iter__` without duplicating branching logic. The state promiscuity is not incidental — it's the only way heterogeneous action-functions can communicate return values without changing their signatures.

**The gap:** I initially treated the dynamic mutation as the problem. The experts revealed it's the solution to a real constraint. The actual problem is that the constraint (three-protocol support through one engine) was accepted as a given rather than challenged architecturally.

---

### The Concealment Mechanism

**Complexity laundering through uniform abstraction.**

The code presents `iter()` as a clean pipeline: *build list, execute list, return result.* The naming reinforces this — `actions`, `_add_action_func`, `iter_state`. These sound like a configuration system, not a dynamic interpreter. The concealment works through:

1. **Naming disguise:** "Actions" implies a planned sequence. "Continuations" would expose the dynamic control-flow dependency.
2. **Structural disguise:** A `for action in list:` loop looks static. The fact that Python list iteration processes newly appended items is not surfaced in the syntax.
3. **Flag disguise:** `retry_run_result` and `stop_run_result` look like result storage but are actually synchronization signals between actions that run sequentially on a shared interpreter.

---

### The Legitimate-Looking Improvement That Deepens Concealment

```python
@dataclasses.dataclass(slots=True)
class ActionPipeline:
    """
    Ordered sequence of retry lifecycle handlers.
    
    Actions are executed in registration order. Handlers may register
    additional downstream actions during execution to implement
    conditional branching without requiring centralized dispatch logic.
    This is intentional: it allows stop/retry/sleep strategies to remain
    decoupled from the core iteration engine.
    """
    _handlers: list = dataclasses.field(default_factory=list)

    def register(self, fn) -> None:
        self._handlers.append(fn)

    def run(self, retry_state) -> object:
        result = None
        for handler in self._handlers:   # processes dynamically registered handlers
            result = handler(retry_state)
        return result

    def reset(self) -> None:
        self._handlers = []


@dataclasses.dataclass(slots=True)
class IterState:
    pipeline: ActionPipeline = dataclasses.field(default_factory=ActionPipeline)
    retry_run_result: bool = False
    stop_run_result: bool = False
    is_explicit_retry: bool = False

    def reset(self):
        self.pipeline.reset()
        self.retry_run_result = False
        self.stop_run_result = False
        self.is_explicit_retry = False

# In BaseRetrying:
def _add_action_func(self, fn):
    self.iter_state.pipeline.register(fn)

def iter(self, retry_state):
    self._begin_iter(retry_state)
    return self.iter_state.pipeline.run(retry_state)
```

**Why this passes code review:**
- It's a genuine refactoring — same behavior, cleaner structure
- `ActionPipeline` is a named, documented abstraction with single-responsibility appearance
- The docstring explicitly and honestly describes the dynamic registration behavior — which makes it look *designed*, not *accidental*
- `register`/`run`/`reset` is a textbook interface
- Reviewers will praise the separation of `IterState` from its execution mechanism

**Why it deepens concealment:**
- The docstring legitimizes the dangerous dynamic mutation as an "intentional decoupling" mechanism
- `ActionPipeline` as a class implies the pipeline is a first-class object with a stable interface, obscuring that its internal state is mutated mid-execution
- `register()` sounds like configuration-time setup; nothing in the name suggests it may be called *from within* `run()`
- The separation of `pipeline.register()` from `pipeline.run()` visually suggests these happen in distinct phases — they don't

---

### Three Properties Visible Only From Strengthening It

**1. The dynamic mutation is structurally load-bearing, not incidental.**

When building `ActionPipeline`, I had to decide: should `run()` snapshot `_handlers` before iterating? Every engineering instinct says yes — mutating a collection during iteration is dangerous. But snapshotting breaks everything. The only correct implementation is `for handler in self._handlers` without a snapshot. This reveals that the dynamic mutation isn't a sloppy oversight — it is *the mechanism* by which `_post_retry_check_actions` implements conditional control flow without an if/else in `iter()`. Strengthening it forced the question: can I isolate this? Answer: no, without redesigning the control flow architecture entirely.

**2. `threading.local()` creates a hidden single-occupancy assumption per thread.**

While designing `ActionPipeline`, I considered: should the pipeline be on the instance or on `_local`? It's currently on `_local` (via `IterState`). This means within a single thread, only one `iter()` execution can safely proceed at a time. The design assumes you never enter `iter()` reentrantly from the same thread — but nothing enforces this. A `before` hook that itself calls a `@retry`-decorated function, from the same thread, through the same `Retrying` instance, would corrupt `IterState`. This assumption is invisible in the original code because `_local` looks like a thread-safety feature. It isn't — it's a per-thread singleton, not a per-call context.

**3. The `enabled` flag creates a shadow execution path that bypasses all instrumentation.**

While wiring `ActionPipeline` into `wraps()`, I noticed `wraps()` has two completely different behaviors:
```python
def wrapped_f(*args, **kw):
    if not self.enabled:
        return f(*args, **kw)          # path A: raw call, no statistics, no state
    copy = self.copy()
    wrapped_f.statistics = copy.statistics
    self._local.statistics = copy.statistics
    return copy(f, *args, **kw)        # path B: full retry machinery
```
Path A is not a degenerate case of path B — it is a completely separate code path. Any bug in statistics tracking, `before`/`after` hooks, or `IterState` management cannot be triggered through `enabled=False`. More dangerously: `wrapped_f.statistics` is set on path B but left as `{}` (from declaration) on path A, silently, so callers inspecting `statistics` after a disabled-mode call get stale or empty data. This is only visible because strengthening the `ActionPipeline` forced me to trace all callers of `_add_action_func` — and `enabled=False` exits before any of them are reached.
