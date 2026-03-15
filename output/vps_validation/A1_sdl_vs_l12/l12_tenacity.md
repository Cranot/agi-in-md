# Structure First: L12 Meta-Conservation Analysis of Tenacity

## The Claim

**Specific, falsifiable claim:** The `iter_state` property accesses a context-scoped singleton (`_iter_state_var`) that creates invisible coupling between retry operations, but the code conceals this by appearing to use fresh state via `reset()` — a method that empties shared state rather than isolating it.

```python
@property
def iter_state(self):
    state = _iter_state_var.get()
    if state is None:
        state = IterState()
        _iter_state_var.set(state)
    return state  # ← Returns SHARED state, not instance state
```

---

## Expert Triangulation

**Expert 1 (Defender):** The context variable *is* the isolation mechanism — Python's `contextvars` creates per-context isolation for asyncio tasks. The `reset()` call at the start of each `iter()` ensures clean state. This is intentional design for async compatibility.

**Expert 2 (Attacker):** The context variable creates *task* isolation, not *retry* isolation. Two sequential retries in the same context share state. More critically, `threading.local` for statistics is NOT async-safe — all coroutines in an event loop share the same thread, hence the same `_local`. The iterator interface (`for attempt in retrying:`) never creates a copy, so concurrent iterators corrupt each other's statistics.

**Expert 3 (Prober):** Both assume state *should* be mutable and accumulated during iteration. What if the problem isn't scoping but the very pattern of building an action list via mutation during iteration? The `_add_action_func` pattern is a continuation-passing style implemented via side effects.

**Transformed Claim:** The fundamental problem is **dual-state dissociation** — `RetryCallState` (per-call, explicit) and `IterState` (per-context, implicit) hold related data in disconnected scopes. The action-accumulation loop reads from one and writes to the other through a property that hides the scope boundary.

---

## Concealment Mechanism

**"Procedural Encapsulation"** — The code conceals state-sharing by:

1. **Property indirection**: `iter_state` looks like instance attribute access but fetches from module-level context
2. **Reset theater**: `reset()` appears to create fresh state but actually empties shared mutable state
3. **Copy illusion**: `wraps()` creates copies for the decorator path, but the iterator path (`__iter__`) has no such protection
4. **Dual state**: Splitting state across two objects makes the coupling harder to see

---

## Engineered Improvement (Deepens Concealment)

```python
@dataclasses.dataclass(slots=True)
class IterState:
    actions: list = dataclasses.field(default_factory=list)
    retry_run_result: bool = False
    stop_run_result: bool = False
    is_explicit_retry: bool = False
    _iteration_id: int = 0  # NEW: "Prevents" state corruption

    def reset(self):
        self._iteration_id += 1  # Bump on each reset
        self.actions = []
        self.retry_run_result = False
        self.stop_run_result = False
        self.is_explicit_retry = False

    def validate_context(self, expected_id):
        """Raise if state was corrupted by nested retry."""
        if self._iteration_id != expected_id:
            raise RuntimeError("Retry state corrupted by nested operation")
```

This passes code review — it "adds protection" against state corruption. But it **deepens the concealment** by:
- Making the singleton pattern appear to be a solved problem
- Adding a "validation" that catches the symptom but not the disease
- Entrenching the shared-state design rather than fixing it

---

## Three Properties Visible Only Through Strengthening

1. **Nested retry detection proves sharing**: The `_iteration_id` check would fire during nested retries, revealing that both retries access the SAME `IterState` object
2. **Context inheritance in asyncio**: Child tasks inherit parent context variables — a spawned task would see parent's `_iteration_id`, causing spurious validation failures
3. **Reset is not reinitialization**: Incrementing `_iteration_id` reveals that `reset()` mutates existing state rather than creating fresh state — the object identity persists

---

## Diagnostic on the Improvement

**What it conceals:** The fact that `IterState` is fundamentally shared across all retry operations in a context, by adding a counter that makes it *appear* lifecycle-managed.

**Recreated property visible only because of the improvement:** The `_iteration_id` creates a new invariant — "iteration ID must match expected" — which fails in legitimate nested retry scenarios, proving the scoping model is wrong.

---

## Second Improvement (Addresses Recreated Property)

```python
class BaseRetrying(ABC):
    @property  
    def iter_state(self):
        state = _iter_state_var.get()
        # Create fresh state per call, not per context
        if state is None or state._iteration_id > 0:
            state = IterState()
            _iter_state_var.set(state)
        return state
```

This "fixes" the nested retry issue by creating fresh state when any retry has run before.

---

## Diagnostic on Second Improvement

**What persists:** The context variable is still shared. Creating "fresh" state in a shared context is still wrong for:
- Concurrent asyncio tasks (they share context)
- Thread inheritance (new threads inherit context)
- The `statistics` property still uses `threading.local`, which is broken for asyncio

**Structural invariant discovered:** **Context-scoped state cannot provide call-scoped isolation.** The improvement moves the problem but doesn't solve it.

---

## Structural Invariant

**The Invariant: Mutable Accumulation State Must Be Scoped to the Iteration, Not the Context**

This persists because:
1. The action list (`actions`) is built by appending during iteration
2. The result flags (`retry_run_result`, `stop_run_result`) are set during iteration  
3. These must be fresh per-iteration, but the context variable provides per-context sharing

The problem space itself — "accumulate actions during a control flow iteration" — requires iteration-scoped state, but the implementation uses context-scoped state.

---

## Inversion: Make State Per-Call

```python
class RetryCallState:
    def __init__(self, retry_object, fn, args, kwargs):
        # ... existing fields ...
        self.iter_state = IterState()  # ← Per-call, not per-context
        
class BaseRetrying:
    # Remove iter_state property entirely
    # All code passes retry_state.iter_state explicitly
```

**New impossibility created:** Callbacks that expect implicit context access (e.g., logging correlation IDs set by `before` callback and read by application code) would break — the state is no longer accessible outside the explicit `retry_state` parameter.

---

## Conservation Law

**The sum of implicit-context bugs and explicit-threading bugs is constant.**

- **Implicit context** (current design): Bugs with nested/concurrent retries sharing state
- **Explicit threading** (inverted design): Bugs with callbacks unable to access state implicitly

You cannot eliminate both simultaneously because retry operations span multiple call frames but need to share control flow state.

---

## Meta-Conservation Law

**The conservation law conceals that the split between `IterState` and `RetryCallState` is itself the root problem.**

Why do two state objects exist?
- `RetryCallState`: Data (fn, args, outcome, timestamps)
- `IterState`: Control flow (actions list, result flags)

They're split because control flow state needs to be **reset each iteration** while data state needs to **persist across iterations**. But this split creates the scoping problem — which scope for which state?

**The meta-law:** Any retry implementation that separates "call data state" from "iteration control state" will have bugs at the boundary where control flow decisions need to read call data, because the two states live in different scopes.

**Concrete, testable prediction:** Any code that:
1. Sets state in phase 1 (detect failure)
2. Reads state in phase 2 (compute delay)
3. Applies effect in phase 3 (sleep)

Will have bugs where state from phase 1 is stale or corrupt in phase 2/3 when retries nest or concurrency occurs.

---

## Complete Bug Manifest

| # | Bug | Location | What Breaks | Severity | Fixable |
|---|-----|----------|-------------|----------|---------|
| 1 | **Nested iterator state corruption** | `iter_state` property, `__iter__` | Nested `for attempt in retrying:` loops share `IterState`, corrupting outer loop's actions | **HIGH** | Yes — set fresh `IterState` in `__iter__` |
| 2 | **Statistics not async-safe** | `statistics` property | Uses `threading.local` which is shared across all coroutines in same event loop. `asyncio.gather(retry_a(), retry_b())` corrupts statistics | **HIGH** | Yes — use `contextvars` or per-call storage |
| 3 | **Iterator interface has no copy isolation** | `__iter__` vs `wraps` | Decorator path creates `copy()` per call; iterator path shares instance state | **MEDIUM** | Yes — create copy in `__iter__` |
| 4 | **Statistics auto-clear loses data** | `statistics` property | `if len() > 100: clear()` can trigger mid-retry, losing `start_time`, `attempt_number` | **MEDIUM** | Yes — remove auto-clear or use max-size dict |
| 5 | **RetryError.reraise() loses traceback** | `RetryError.reraise` | Calls `raise self.last_attempt.result()` which creates new traceback, losing original | **MEDIUM** | Yes — store and re-raise with original traceback |
| 6 | **Future.exception() null risk** | `exc_check` in `_post_stop_check_actions` | `raise retry_exc from fut.exception()` — if future somehow not done, `from None` causes confusing error | **MEDIUM** | Yes — add null check |
| 7 | **seconds_since_start returns None** | `RetryCallState.seconds_since_start` | Returns `None` before first attempt outcome; `_run_stop` stores this in statistics | **LOW** | Yes — return 0.0 or raise |
| 8 | **DoSleep(0) is falsy** | `DoSleep` class | `DoSleep(0)` equals `0.0`; in boolean context is `False`. Could cause subtle bugs in conditional logic | **LOW** | No — by design, unlikely to manifest |
| 9 | **Unbounded action list if iter interrupted** | `iter`, `_begin_iter` | If exception occurs during action execution before reset, actions persist (though reset happens next iter) | **LOW** | Yes — try/finally around action execution |
| 10 | **RetrySignal subclassing breaks detection** | `_begin_iter` | `isinstance(fut.exception(), RetrySignal)` — subclasses work, but if exception is wrapped/re-raised, detection fails | **LOW** | Partial — document limitation |
| 11 | **Copy shares sleep function reference** | `copy` method | If `sleep` is stateful mock, original and copy affect each other | **VERY LOW** | No — intentional, documented |
| 12 | **NO_RESULT sentinel identity loss** | Module level | If retry state pickled/unpickled, sentinel comparison fails | **VERY LOW** | Yes — use `enum.Enum` |
| 13 | **_first_set can't override to None** | `_first_set` function | Can't explicitly set parameter to `None` to override inherited default | **VERY LOW** | No — intentional API design |
| 14 | **before_sleep can't modify sleep time** | `_post_stop_check_actions` | `before_sleep` called after `next_action` set with sleep value | **VERY LOW** | No — by design |
| 15 | **AttemptManager silently sets None result** | `AttemptManager.__exit__` | If `set_result` never called and no exception, sets `None` — masks user forgetfulness | **VERY LOW** | Partial — could warn |

---

## Conservation Law Prediction: Fixability Classification

| Fixable | Structural (Conservation Law Predicts Unfixable Without Redesign) |
|---------|-------------------------------------------------------------------|
| 1, 2, 3, 4, 5, 6, 7, 9, 10, 12 | 8, 11, 13, 14, 15 |

The structural ones require accepting the trade-off or redesigning the entire state management approach. Bug #2 (async safety) is the most severe and reveals the core design flaw: `threading.local` and `contextvars` serve different concurrency models, and this library tries to serve both with a single state architecture.

---

## Final Finding

**The meta-conservation law for this codebase:**

> *Retry state that spans multiple Python call frames but must be isolated per retry operation will always have bugs at the boundary where "spanning" meets "isolating" — the only question is which side of the boundary the bugs manifest on.*

The current design puts bugs on the "isolation" side (shared state). The inverted design would put bugs on the "spanning" side (callbacks can't access implicit context). The conservation law between these impossibilities is the deep structure of the retry problem itself.
