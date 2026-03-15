## The Falsifiable Claim

**The deepest structural problem is that `iter()` executes a list that grows during its own traversal.** `_post_retry_check_actions` and `_post_stop_check_actions` append to `self.iter_state.actions` while `iter()`'s `for` loop is executing items from that same list. Python's index-based list iteration makes this work, but it means `iter()` is not dispatching a pipeline — it is running a trampoline disguised as a for loop. This is falsifiable: you can replace the list with a tuple snapshot at iteration start and watch the retry logic silently break.

---

## Three Experts Debate

**Expert A (defends):** The action queue isn't a hidden trampoline, it's a deliberate continuation-passing mechanism. The `for action in self.iter_state.actions` loop must see newly appended items because later decisions — whether to raise, sleep, or stop — depend on side effects from earlier actions like `_run_retry`. Without mutation-during-iteration, you'd need a full state machine with named states, which is more complex, not less. The pattern earns its complexity by allowing `__call__` and `__iter__` to share identical decision logic.

**Expert B (attacks):** Sharing logic isn't the win the defender claims. The supposed "shared logic" in `iter()` is ten lines of `for action in self.iter_state.actions`. What's actually shared is a bag of closures appended conditionally in `_begin_iter`, `_post_retry_check_actions`, and `_post_stop_check_actions` — three functions that must be read in sequence to understand what any single iteration does. The `IterState.reset()` at the top of `_begin_iter` is silent garbage collection of closures from the previous iteration. Call this what it is: a stateful scheduler implemented inside a for loop.

**Expert C (probes what both assume):** Both experts take for granted that the action queue is the primary design choice. But look at `wraps()`:

```python
copy = self.copy()
wrapped_f.statistics = copy.statistics
self._local.statistics = copy.statistics  # ← original's thread-local points to copy's dict
return copy(f, *args, **kw)              # ← copy.begin() then clears that dict
```

The original instance's thread-local statistics is deliberately aliased to the copy's statistics dictionary *before* `copy.begin()` clears it. `wrapped_f.statistics`, `self._local.statistics`, and `copy.statistics` all point to the same object, which gets cleared on every call. This is identity-through-aliasing: three references to one dict, mutated in place, with no owner. Both experts are debating the action queue while the statistics reference graph is doing something stranger.

---

## Transformation of the Claim

**Original claim:** The action queue is an illegible dynamic control structure.

**Transformed claim:** The action queue is the implementation cost of a protocol that must serve two incompatible execution models — push (`__call__` owns execution) and pull (`__iter__` yields to the caller). The illegibility is not incidental; it is load-bearing.

**The gap:** I initially diagnosed a readability problem. After expert pressure, I see a design space constraint: the retry logic must produce `DoAttempt` and `DoSleep` signals without knowing whether the caller will execute the attempt or yield to an outer loop. The trampoline is how you write one decision engine for both consumers.

---

## The Concealment Mechanism

**Apparent sequential dispatch conceals live queue growth.**

`iter()` reads as: *execute these pre-determined actions in order*. It behaves as: *execute actions that append further actions, consuming the growing tail as it produces it*. The for loop is the concealment — it looks like a dispatcher, but `_post_retry_check_actions` calls `self._add_action_func(self._post_stop_check_actions)` from inside the loop, inserting what amounts to a function call three frames deep into the same iteration's execution sequence.

The mechanism works because Python's list `for` loop is index-based. Appending to the list from inside the loop body is legal and transparent at runtime. Nothing raises. Nothing warns. The loop terminates when the index exceeds the final length, which happens to be exactly after the last appended decision function runs.

---

## Improvement 1: Type-Annotated Pipeline Snapshot (Deepens Concealment)

```python
from typing import Any

def iter(self, retry_state: RetryCallState) -> Any:
    """Execute the action pipeline for this retry iteration."""
    self._begin_iter(retry_state)
    result: Any = None
    actions: list[Any] = self.iter_state.actions  # extracted for clarity
    for action in actions:
        result = action(retry_state)
    return result
```

This passes code review on three grounds: it adds type annotations, it names the intermediate value, and it adds a docstring. The reviewer sees `actions: list[Any] = self.iter_state.actions` and reads it as a snapshot assignment — "we capture the list, then iterate it." But `actions` is a reference to the same list object. The snapshot impression is an artifact of the assignment syntax. Concealment deepens because the named local variable now *implies* a fixed collection while remaining a live reference to a growing queue. The type annotation `list[Any]` is accurate but misleading: it describes what the object is, not what it does.

---

## Three Properties Visible Only from Strengthening

**1. The aliasing is load-bearing, not incidental.** When I tried to write `actions: tuple[Any, ...] = tuple(self.iter_state.actions)` for a genuine snapshot, I broke the retry logic: `_post_retry_check_actions` appended to the original list, which the tuple no longer referenced. The mutation must happen to the iterated collection. You cannot make this safe without redesigning it.

**2. The loop is a scheduler, not a dispatcher.** When I tried to annotate the return type accurately, I realized intermediate action return values are discarded — only the last return value (`DoAttempt`, `DoSleep`, or a result) matters. The loop runs side effects and queue-appends through every step except the last. Calling it a "pipeline" is wrong: pipelines transform data through stages. This propagates state and makes scheduling decisions.

**3. `reset()` is not initialization — it is scope cleanup.** When I tried to pre-allocate `actions` before `_begin_iter` to reuse the list object, I discovered that `reset()` must clear closures that captured `self` from the previous iteration. Without `reset()`, closures accumulate across iterations and actions from prior retry cycles re-execute. The reset is not resetting to a clean state — it is terminating the previous iteration's execution scope.

---

## Improvement 2: Explicit Generator Chain (Contradicts Improvement 1)

Where Improvement 1 made the dynamic queue look like a static pipeline, Improvement 2 makes the dynamic nature explicit:

```python
def _action_sequence(self, retry_state: RetryCallState):
    """Explicitly yield the action sequence for this iteration."""
    fut = retry_state.outcome
    if fut is None:
        if self.before is not None:
            yield self.before
        yield lambda rs: DoAttempt()
        return

    is_explicit_retry = fut.failed and isinstance(fut.exception(), TryAgain)
    if not is_explicit_retry:
        yield self._run_retry
        # HERE: we must execute _run_retry before knowing what comes next
        # but generators can't do that — they yield, they don't execute-then-decide

def iter(self, retry_state: RetryCallState) -> Any:
    self.iter_state.reset()
    result = None
    for action in self._action_sequence(retry_state):
        result = action(retry_state)
    return result
```

This looks more honest — a generator is explicit about laziness. It passes review as "making the implicit explicit." But it *cannot work*. The generator must yield `_run_retry` before it knows the value of `self.iter_state.retry_run_result`, which is set only when `_run_retry` executes. The generator would need to yield, wait for the caller to execute the action, observe the side effect, and then decide what to yield next — which is exactly what a generator *with send()* does, not a generator used in a for loop.

The improvement is legitimate in intent, broken in execution, and reveals something the original concealment hid.

---

## The Structural Conflict

**Decision-dependent sequencing vs. sequence-independent execution.**

Both improvements are legitimate:
- Improvement 1: Make the fixed sequence legible. (A static pipeline should look static.)
- Improvement 2: Make the dynamic sequence explicit. (A dynamic sequence should look dynamic.)

They contradict because the sequence is neither static nor freely dynamic — it is **decided incrementally by the results of executing its own prior elements.** Each decision node (`_post_retry_check_actions`, `_post_stop_check_actions`) can only determine which action comes next after the previous action has run and mutated `iter_state`.

This conflict exists only because both improvements are legitimate. If the pipeline were truly static, Improvement 1 would work and 2 would be unnecessary. If the sequence were purely dynamic, Improvement 2 would work and 1 would be dishonest. The conflict lives exactly in the gap: a sequence whose shape depends on its own execution.

---

## Improvement 3: Explicit Trampoline (Resolves the Conflict)

```python
from typing import Optional, Callable, Any

class RetryStep:
    """A single step that returns a result and the next step to execute."""
    def __init__(self, fn: Callable, next_step: Optional['RetryStep'] = None):
        self.fn = fn
        self.next_step = next_step

    def execute(self, retry_state: RetryCallState) -> tuple[Any, Optional['RetryStep']]:
        result = self.fn(retry_state)
        return result, self.next_step

class DynamicStep:
    """A step that computes its successor after executing."""
    def __init__(self, fn: Callable[..., Optional['DynamicStep']]):
        self.fn = fn

    def execute(self, retry_state: RetryCallState) -> tuple[Any, Optional['DynamicStep']]:
        next_step = self.fn(retry_state)
        return None, next_step

def iter(self, retry_state: RetryCallState) -> Any:
    step: Any = self._build_initial_step(retry_state)
    result = None
    while step is not None:
        result, step = step.execute(retry_state)
    return result
```

This resolves both concerns: the dynamic nature is explicit (each step declares its successor), and the sequence is legible (follow the `next_step` chain). It passes review as "converting the implicit trampoline to an explicit one" — a recognized refactoring pattern.

---

## How It Fails

The trampoline forces every intermediate step to return `(result, next_step)`. But intermediate results are not used — only the terminal result matters. The trampoline protocol adds wrapping and unwrapping overhead at every step for values that are immediately discarded.

More critically: `DynamicStep` must compute its successor by calling a function that reads `self.iter_state.retry_run_result` — which was set as a side effect of the previous step. The trampoline has not eliminated the shared mutable state; it has moved the mutation from "append to list" to "write to iter_state," then read it from the next step's closure. The successor is still determined by a side effect. The explicit step chain is honest about sequencing but conceals that each step's identity depends on state the previous step left in a shared object.

The trampoline fails because it makes the *chain* explicit while leaving the *state transitions* implicit in `iter_state`. It solves the readability of sequencing while preserving the opacity of state management.

---

## What the Failure Reveals About the Design Space

The conflict between Improvement 1 and 2 suggested: "we can't decide if the sequence is static or dynamic." The failed trampoline reveals something more specific: **this is not a state machine over discrete states — it is a coroutine over observable results.**

A state machine has named, stable states (`RETRYING`, `STOPPED`, `SLEEPING`). This has no such states. It has *observations*: did the last attempt fail? does the retry condition hold? does the stop condition hold? Each observation is the return value of executing a strategy object with the current retry state. The observations are not known until the attempt runs. The attempt is not run by the retry engine — it is run by the caller.

The design space's real constraint: **the retry engine cannot own execution of the attempt, cannot observe the outcome passively, and cannot pre-declare the decision sequence.** Any implementation must either duplicate logic across the sync and iterator protocols, or implement a mechanism that yields control to the caller and resumes with the outcome — a coroutine.

The growing-list trampoline is a coroutine protocol implemented without `yield` or `async/await`. The trampoline refactoring failed because it tried to make the coroutine explicit while keeping the execution model synchronous. These are incompatible.

---

## The Redesign: Accept the Topology

Accept that this is a coroutine-based protocol. Implement it as one:

```python
from typing import Generator, Any

class RetryProtocol:
    """
    Inhabits the feasible point: an explicit coroutine driver.
    Call drive() to get a generator. Send outcomes to it. Receive signals from it.
    """
    def __init__(self, stop, wait, retry, after=None, before=None, before_sleep=None,
                 reraise=False, retry_error_cls=RetryError):
        self.stop = stop
        self.wait = wait
        self.retry = retry
        self.after = after
        self.before = before
        self.before_sleep = before_sleep
        self.reraise = reraise
        self.retry_error_cls = retry_error_cls

    def drive(self) -> Generator[DoAttempt | DoSleep, futures.Future | None, Any]:
        """
        Coroutine driver. Yields DoAttempt or DoSleep.
        After DoAttempt: send a completed Future (success or exception).
        After DoSleep: send None.
        Returns the final result or raises.
        """
        state = RetryCallState(retry_object=self, fn=None, args=(), kwargs={})

        while True:
            if self.before is not None:
                self.before(state)

            outcome: futures.Future = yield DoAttempt()   # caller executes attempt, sends outcome
            state.outcome = outcome
            state.outcome_timestamp = time.monotonic()

            if isinstance(outcome.exception(), TryAgain) or self.retry(state):
                if self.after is not None:
                    self.after(state)

                sleep = self.wait(state)
                state.upcoming_sleep = sleep

                if self.stop(state):
                    retry_exc = self.retry_error_cls(outcome)
                    if self.reraise:
                        retry_exc.reraise()
                    raise retry_exc from outcome.exception()

                state.idle_for += sleep
                if self.before_sleep is not None:
                    self.before_sleep(state)

                yield DoSleep(sleep)                        # caller sleeps, sends None
                state.prepare_for_next_attempt()
            else:
                return outcome.result()                     # success: return or reraise


    # Adapters that consume the coroutine protocol
    def __call__(self, fn, *args, **kwargs):
        """Sync adapter: owns execution."""
        driver = self.drive()
        signal = next(driver)
        while True:
            if isinstance(signal, DoAttempt):
                fut = Future(1)
                try:
                    fut.set_result(fn(*args, **kwargs))
                except BaseException as e:
                    fut.set_exception(e)
                try:
                    signal = driver.send(fut)
                except StopIteration as e:
                    return e.value

            elif isinstance(signal, DoSleep):
                time.sleep(float(signal))
                try:
                    signal = driver.send(None)
                except StopIteration as e:
                    return e.value

    def __iter__(self):
        """Iterator adapter: yields control for manual attempt execution."""
        driver = self.drive()
        signal = next(driver)
        while True:
            if isinstance(signal, DoAttempt):
                manager = AttemptManager.__new__(AttemptManager)
                manager._driver = driver
                yield manager
                signal = manager._next_signal
            elif isinstance(signal, DoSleep):
                time.sleep(float(signal))
                try:
                    signal = driver.send(None)
                except StopIteration:
                    return
```

The coroutine protocol is now the single source of truth. `__call__` and `__iter__` are adapters over it. The decision logic lives once, in `drive()`, as readable sequential code. The `for`/`while` loop does not grow during execution. There is no `IterState`. There is no growing action list.

---

## What the Redesign Sacrifices

**The `wraps()` / decorator integration.** The original `BaseRetrying` is a self-contained callable that can be applied as `@retry` with zero configuration friction. The coroutine protocol requires the caller to know about `drive()`, `send()`, and `StopIteration`. The adapter methods partially hide this, but they cannot be shared via `functools.wraps` with the same transparency — the original `wrapped_f.retry`, `wrapped_f.retry_with`, and `wrapped_f.statistics` integration becomes awkward when the driver is a generator that must be instantiated per-call.

More specifically: the original design allows `r = Retrying(...)` to be called directly as `r(fn, *args, **kwargs)` *and* iterated as `for attempt in r: ...` *and* decorated as `@r` — all from one instance, with shared statistics. The redesign requires separate adapter instances or explicit protocol negotiation.

---

## What Was Never a Flaw

The growing-list trampoline in `iter()` was never a flaw. It was the **exact cost of the correct answer to an impossible question: how do you write retry logic once for two incompatible execution models?**

`__call__` must own execution. It calls `fn`, catches exceptions, and processes results. It cannot yield.

`__iter__` must not own execution. It yields `AttemptManager` to the caller, who runs the attempt in a `with` block. It cannot call `fn`.

These models are not different implementations of the same abstraction — they are categorically different execution protocols. A state machine over named states can't bridge them because the "states" depend on unexecuted outcomes. A generator protocol bridges them structurally but requires the caller to use `send()`, which breaks decorator transparency.

The original design found a third option: encode the decision sequence as an append-to-list side effect inside a for loop that iterates the list it's appending to. Both `__call__` and `__iter__` call `self.iter()` and receive `DoAttempt` or `DoSleep` as return values — indifferent to who executes the attempt or how.

What looked like a concealed trampoline was actually the minimum overhead required to make two incompatible execution protocols share one decision engine without duplication and without requiring the caller to implement a coroutine protocol. The "flaw" was the cost of attempting the impossible: one control structure that both pushes and pulls.
