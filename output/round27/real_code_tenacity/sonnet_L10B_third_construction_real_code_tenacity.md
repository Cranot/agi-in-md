## The Claim

**`IterState`'s lifetime mismatches its purpose, and the mismatch is what drives the action-chain design.**

`IterState` is a temporary accumulator for one `iter()` call, but it lives on `threading.local()` with instance scope. `reset()` compensates by clearing it at the start of each `iter()` invocation. The self-modifying action list — where `_post_retry_check_actions` appends to the same list being iterated in `iter()` — is a direct consequence: actions are methods of `self`, so they reach execution state via `self.iter_state` rather than receiving it as an argument. The thread-local shortcut exists because the data wasn't passed correctly to begin with.

**Falsifiable form**: Replace `self.iter_state` with a local variable inside `iter()` and pass it explicitly where needed. Every documented behavior is preserved. Only undocumented assumptions about reaching execution state through `self` break.

---

## Three Experts

**The Defender agrees**: The red flag is `for action in self.iter_state.actions` iterating a list while `_post_retry_check_actions` and `_post_stop_check_actions` append to it mid-loop. Python's index-based list iteration makes this work, but it's load-bearing fragility — insert instead of append, or switch to a generator, and control flow silently breaks. Any exception mid-chain leaves `iter_state` dirty until the next `reset()`.

**The Attacker redirects**: Wrong target. The self-modifying list is intentional lazy evaluation — deferred branching. The *real* problem is in `wraps()`:

```python
copy = self.copy()
wrapped_f.statistics = copy.statistics   # ← race condition
self._local.statistics = copy.statistics
```

Each call creates its own `copy`, but all writes land on `wrapped_f.statistics` — a shared function attribute. Concurrent calls produce non-deterministic statistics for any observer of `wrapped_f.statistics`. The thread-local protects internal state but exposes statistics through an unsafe shared reference.

**The Probe challenges what both take for granted**: Both experts assume the problem is *in* the iteration implementation. Neither questions why `BaseRetrying` holds per-iteration state at all. A `Retrying` instance simultaneously acts as: (1) a retry *policy* (stop, wait, retry strategies), (2) an *executor* for a specific call, and (3) a *state container* for the current execution. `copy()` partially acknowledges this — it creates a new executor per call — but execution state still lives on the policy object. The thread-local isn't a threading mechanism. It's a design marker: *the object doesn't know what it is.*

---

## Transformed Claim

**Original**: `IterState`'s lifetime mismatches its purpose.

**Transformed**: `BaseRetrying` conflates policy identity with execution state. The lifetime mismatch of `IterState` is a symptom. `copy()` is an incomplete acknowledgment — it creates a new executor per call but doesn't relocate state to where it belongs.

**The diagnostic gap**: The original claim is about one data structure's scope. The transformed claim is about the object's responsibility allocation. Fixing `IterState`'s lifetime doesn't resolve the class's identity crisis — it's still simultaneously policy and executor. The thread-local isn't a technical convenience. It's an architectural marker.

---

## Concealment Mechanism: Compensating Normalization

Each of these signals careful design independently:
- `@dataclasses.dataclass(slots=True)` → "performance-conscious"
- `threading.local()` → "thread-safe"
- `reset()` → "lifecycle-managed"

Together they form a **legitimacy cascade**. A reviewer sees three green flags. None reveal that `IterState` is compensating for a problem that shouldn't exist. The fix is visible; the thing being fixed is not.

---

## Improvement 1: Deepening the Concealment

Add re-entrancy detection and a context manager lifecycle to `IterState`:

```python
@dataclasses.dataclass(slots=True)
class IterState:
    actions: list[Callable] = dataclasses.field(default_factory=list)
    retry_run_result: bool = False
    stop_run_result: bool = False
    is_explicit_retry: bool = False
    _active: bool = dataclasses.field(default=False, repr=False)

    def reset(self) -> None:
        """Prepare for a new iteration cycle."""
        self.actions = []
        self.retry_run_result = False
        self.stop_run_result = False
        self.is_explicit_retry = False
        self._active = False

    @contextlib.contextmanager
    def activate(self):
        """Ensure clean state for one iteration. Not re-entrant."""
        if self._active:
            raise RuntimeError("IterState is not re-entrant within a single thread")
        self.reset()
        self._active = True
        try:
            yield self
        finally:
            self._active = False

def iter(self, retry_state):          # In BaseRetrying
    with self.iter_state.activate():
        self._begin_iter(retry_state)
        result = None
        for action in self.iter_state.actions:
            result = action(retry_state)
    return result
```

This passes code review: it adds explicit lifecycle management, re-entrancy detection, type annotations, and documentation. It looks like a matured implementation.

**Three properties visible only because we tried to strengthen it**:

1. **The re-entrancy check surfaces an undocumented invariant**: Adding `if self._active: raise RuntimeError` immediately raises the question — *can `iter()` be called re-entrantly from the same thread?* With thread-local storage it cannot, but the original code fails silently. The improvement makes the constraint explicit and reveals that recursive retry (a retried function calling itself through the same retrier) has undefined behavior in the original.

2. **The `finally` block without `reset()` reveals the exception path is distinct**: If we only set `_active = False` without resetting, the dirty actions list from a failed iteration persists until the next `activate()`. This surfaces that the *exception path* and *success path* have different state-cleanliness requirements — a distinction the original `reset()` at the top of `_begin_iter` silently erases.

3. **The context manager frame highlights the mutation-during-iteration**: Wrapping `for action in self.iter_state.actions` inside `with self.iter_state.activate()` makes the boundary explicit — and suddenly the fact that those same actions append to `self.iter_state.actions` mid-loop is more visible, not less. The improvement we designed to conceal actually illuminates the problem for any reader who examines the scope of the `with` block.

---

## Improvement 2: The Contradiction

Eliminate thread-local storage for `IterState` entirely by passing it as a local variable:

```python
def iter(self, retry_state):
    iter_state = IterState()          # local, not thread-local
    self._begin_iter(retry_state, iter_state)
    result = None
    for action in iter_state.actions:
        result = action(retry_state)
    return result

def _begin_iter(self, retry_state, iter_state):
    fut = retry_state.outcome
    if fut is None:
        if self.before is not None:
            iter_state.actions.append(self.before)
        iter_state.actions.append(lambda rs: DoAttempt())
        return
    iter_state.is_explicit_retry = fut.failed and isinstance(fut.exception(), TryAgain)
    if not iter_state.is_explicit_retry:
        iter_state.actions.append(
            lambda rs, s=iter_state: self._run_retry_with_state(rs, s)
        )
    iter_state.actions.append(
        lambda rs, s=iter_state: self._post_retry_check_actions(rs, s)
    )

def _post_retry_check_actions(self, retry_state, iter_state):
    if not (iter_state.is_explicit_retry or iter_state.retry_run_result):
        iter_state.actions.append(lambda rs: rs.outcome.result())
        return
    if self.after is not None:
        iter_state.actions.append(self.after)
    iter_state.actions.append(lambda rs, s=iter_state: self._run_wait(rs))
    iter_state.actions.append(lambda rs, s=iter_state: self._run_stop(rs))
    iter_state.actions.append(lambda rs, s=iter_state: self._post_stop_check_actions(rs, s))
```

This passes code review: it eliminates shared mutable state, makes data flow explicit, minimizes state lifetime, and is directly testable in isolation.

**Why it contradicts Improvement 1**: Improvement 1 said "make the shared-state lifecycle explicit with guardrails" — it strengthened the thread-local pattern. Improvement 2 says "eliminate shared state entirely." One optimizes the implicit channel; the other abolishes it. Both pass review because both address real problems in the original.

---

## The Structural Conflict

The conflict is not stylistic. It's architectural:

| | Improvement 1 | Improvement 2 |
|---|---|---|
| `iter_state` location | `self._local` (managed) | local variable in `iter()` |
| How actions reach iteration state | via `self.iter_state` | via closures capturing local var |
| Action signatures | `fn(retry_state)` | `fn(retry_state, iter_state)` or closures |
| What's strengthened | **Encapsulation** — actions don't expose their dependencies | **Transparency** — data flow is traceable |

The conflict exists because the current design has **two communication channels** between `iter()` and the actions it runs:
1. The *explicit argument* — `retry_state`, passed to every action
2. The *implicit shared state* — `iter_state` via `self`

Improvement 1 hardens channel 2. Improvement 2 collapses channel 2 into channel 1. Any improvement that preserves one channel strengthens it at the expense of the other, because neither channel alone is sufficient — actions need both the call outcome (`retry_state`) and the iteration's control state (`iter_state.retry_run_result` etc.).

---

## Improvement 3: Resolving the Conflict

Merge both channels into one unified context object, local to `iter()`:

```python
@dataclasses.dataclass
class IterContext:
    """The complete context for one iter() invocation. Not shared."""
    retry_state: RetryCallState
    actions: list = dataclasses.field(default_factory=list)
    retry_run_result: bool = False
    stop_run_result: bool = False
    is_explicit_retry: bool = False

    def add(self, fn: Callable[['IterContext'], Any]) -> None:
        self.actions.append(fn)

# In BaseRetrying:
def iter(self, retry_state: RetryCallState):
    ctx = IterContext(retry_state=retry_state)   # local, self holds nothing
    self._begin_iter(ctx)
    result = None
    for action in ctx.actions:
        result = action(ctx)                     # actions receive ctx, not retry_state
    return result

def _run_retry(self, ctx: IterContext) -> None:
    ctx.retry_run_result = self.retry(ctx.retry_state)

def _run_stop(self, ctx: IterContext) -> None:
    self.statistics["delay_since_first_attempt"] = ctx.retry_state.seconds_since_start
    ctx.stop_run_result = self.stop(ctx.retry_state)

def _post_retry_check_actions(self, ctx: IterContext) -> None:
    if not (ctx.is_explicit_retry or ctx.retry_run_result):
        ctx.add(lambda c: c.retry_state.outcome.result())
        return
    if self.after is not None:
        ctx.add(lambda c: self.after(c.retry_state))   # ← adapter
    ctx.add(self._run_wait)
    ctx.add(self._run_stop)
    ctx.add(self._post_stop_check_actions)
```

This satisfies both: actions don't need to reach `self` for iteration state (satisfying Improvement 2), and the context is self-contained without shared mutable state on `self` (satisfying Improvement 1 more thoroughly than Improvement 1 itself did).

**How it fails**:

The internal action signature is now `fn(ctx: IterContext)`, but every user-supplied hook — `before`, `after`, `before_sleep`, `retry_error_callback` — was designed to receive `retry_state: RetryCallState`. The public API contract is `callable(retry_state)`. The internal contract is now `callable(ctx)`. These are different types.

Every invocation of a user callback now requires an adapter:
```python
ctx.add(lambda c: self.after(c.retry_state))
ctx.add(lambda c: self.before_sleep(c.retry_state))
ctx.add(lambda c: self.before(c.retry_state))
```

These adapters scatter through `_begin_iter`, `_post_retry_check_actions`, and `_post_stop_check_actions`. Worse, they're invisible to the type checker unless explicit overloads are defined. And any user who subclassed `BaseRetrying` and overrode `_run_retry`, `_post_retry_check_actions`, etc. with the old signature breaks silently.

---

## What the Failure Reveals

The conflict revealed that the action protocol has two communication channels. The failure reveals something the conflict alone could not:

**The library's internal execution protocol and its user-facing extension API are the same interface.**

`before`, `after`, `before_sleep`, `retry_error_callback` — these are external hooks. `_run_retry`, `_run_wait`, `_run_stop`, `_post_retry_check_actions` — these are internal plumbing. Both live in `iter_state.actions`. Both use `callable(retry_state)`. There is no boundary.

This means the design space is constrained in a way that no single refactor can resolve:

- Make the internal protocol richer (add `IterContext`) → must either break external hooks or wrap every external hook in an adapter
- Leave external hooks alone → internal state management remains impoverished
- Add a distinct internal action type → now there are two action registries with different dispatch logic

The thread-local storage, the mutable action list, and the lifetime mismatch are all load-bearing. They exist because the library needs an implicit channel between the orchestrator and internal actions that does *not* affect the external hook API. Thread-local on `self` is the only channel that internal methods can access through `self` without appearing in the hook protocol.

**The real design failure is not any of the three improvements' targets. It is the collapsed interface between internal execution infrastructure and external extensibility.** Every improvement that addresses execution state internally propagates to the public API boundary, because there is no boundary. The library cannot evolve its execution model without negotiating every change with its extension points — a constraint that the thread-local kludge currently enforces, invisibly, by keeping internal state off the action protocol entirely.
