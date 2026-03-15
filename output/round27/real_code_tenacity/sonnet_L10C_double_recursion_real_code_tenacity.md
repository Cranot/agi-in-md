# Structural Analysis: Tenacity's Retry Engine

---

## I. The Claim

**Specific, falsifiable claim:** `iter()` iterates over `self.iter_state.actions` using a standard `for` loop, while the actions executing *inside that loop* call `_add_action_func()` to append new items to that same live list. Python's list iterator advances by index, not snapshot, so newly appended items are picked up mid-loop. The code is implementing a continuation-passing trampoline disguised as a data structure iteration.

This is falsifiable: if you freeze the list before iteration (`for action in list(self.iter_state.actions)`), the retry lifecycle breaks completely, because `_post_retry_check_actions` and `_post_stop_check_actions` would append their continuations into a dead copy.

```python
def iter(self, retry_state):
    self._begin_iter(retry_state)  # seeds the list
    result = None
    for action in self.iter_state.actions:   # <── live list
        result = action(retry_state)          # actions append MORE actions here
    return result
```

---

## II. Three Expert Challenge

**Defender:** The pattern is coherent. `IterState` makes the execution state explicit. The actions list is a dynamic execution queue that gives you composable, testable lifecycle steps. Each step can conditionally enqueue further steps, which is just a finite automaton.

**Attacker:** The execution order is determined by which closures append to the list in which order. You cannot read `iter()` and know what runs. The actual control flow lives in `_post_retry_check_actions` and `_post_stop_check_actions`, which are themselves actions — meaning the interpreter is inside the program it's interpreting. This is undebuggable.

**Prober:** You're both arguing about *mechanism*. Neither of you is asking: why does the lifecycle need to be dynamically composed at all? The retry lifecycle always follows one of two fixed paths. What is the *runtime dynamic composition actually buying*?

**The transformation:** After the prober's challenge, the claim shifts. The dynamic queue isn't solving a composability problem — it's solving a **pausability problem**. `DoAttempt` and `DoSleep` are not return values; they are *yield points* for the `__iter__` protocol. The action queue is a manually-implemented coroutine that can pause at exactly two points without Python's `yield`. The dynamic composition is load-bearing, but for a completely different reason than it appears.

---

## III. Gap Analysis → Concealment Mechanism

**Original claim:** mutable list iteration as implicit continuation-passing  
**Transformed claim:** a manually-implemented pausable coroutine, requiring mediation between decisions and execution, hidden behind what looks like a generic action-executor framework

**The gap** is the distance between "bad pattern" and "necessary mechanism."

**The concealment:** The code makes the retry lifecycle look like a *general* action-execution framework (implying it could run *any* sequence of actions) when it is actually a *specific* pausable state machine with exactly two yield points. The generality is theatrical. It hides that the real constraint is the `__iter__` protocol — which requires control to return to the caller between `DoAttempt` and `DoSleep`, something a simple sequential function cannot do.

---

## IV. First Improvement: Deepens the Concealment

Add phase labels and a `PhaseAction` wrapper. This passes code review because it adds observability, structured repr, and appears to introduce explicit lifecycle phases.

```python
@dataclasses.dataclass(slots=True)
class PhaseAction:
    """Action with explicit lifecycle phase label for observability."""
    fn: callable
    phase: str

    def __call__(self, retry_state):
        return self.fn(retry_state)

    def __repr__(self):
        return f"PhaseAction(phase={self.phase!r}, fn={self.fn.__qualname__})"


@dataclasses.dataclass(slots=True)
class IterState:
    actions: list = dataclasses.field(default_factory=list)
    retry_run_result: bool = False
    stop_run_result: bool = False
    is_explicit_retry: bool = False
    current_phase: str = "unstarted"

    def reset(self):
        self.actions = []
        self.retry_run_result = False
        self.stop_run_result = False
        self.is_explicit_retry = False
        self.current_phase = "unstarted"

    def add_phase_action(self, fn: callable, phase: str) -> None:
        """Register fn under the named lifecycle phase."""
        self.actions.append(PhaseAction(fn=fn, phase=phase))
        self.current_phase = phase


class BaseRetrying(ABC):
    # Replace _add_action_func with:
    def _add_action_func(self, fn, phase: str = "unnamed"):
        self.iter_state.add_phase_action(fn, phase)

    def _begin_iter(self, retry_state):
        self.iter_state.reset()
        fut = retry_state.outcome
        if fut is None:
            if self.before is not None:
                self._add_action_func(self.before, phase="before")
            self._add_action_func(lambda rs: DoAttempt(), phase="attempt")
            return
        self.iter_state.is_explicit_retry = (
            fut.failed and isinstance(fut.exception(), TryAgain)
        )
        if not self.iter_state.is_explicit_retry:
            self._add_action_func(self._run_retry, phase="retry_check")
        self._add_action_func(self._post_retry_check_actions, phase="post_retry")

    def _post_retry_check_actions(self, retry_state):
        if not (self.iter_state.is_explicit_retry or self.iter_state.retry_run_result):
            self._add_action_func(lambda rs: rs.outcome.result(), phase="return_result")
            return
        if self.after is not None:
            self._add_action_func(self.after, phase="after")
        self._add_action_func(self._run_wait, phase="wait")
        self._add_action_func(self._run_stop, phase="stop_check")
        self._add_action_func(self._post_stop_check_actions, phase="post_stop")
```

**Why this deepens concealment:** The `phase` labels make the code look like it models explicit lifecycle states. A reviewer sees `phase="retry_check"` and thinks: *this is a proper state machine with named phases.* But the phases are annotations on continuations, not state machine transitions. The sequence is still determined by dynamic append-during-iteration. The labels create the appearance of structure while the mechanism remains an implicit continuation queue. `current_phase` tracks what was most recently enqueued, not what is currently executing — so it lies under concurrent use.

---

## V. Three Properties Visible Only From Strengthening

**1. Phase labels cannot be pre-conditions.** Adding `phase` names reveals there is nowhere to enforce that `"retry_check"` must precede `"stop_check"`. The queue does not validate transition order. The phases are descriptive of what was appended, not prescriptive of what is allowed — the lifecycle ordering lives only in the imperative logic of `_post_retry_check_actions`.

**2. `current_phase` is a lie under the iterator.** `current_phase` is set when an action is *enqueued*, not when it *executes*. By the time `_post_retry_check_actions` runs, `current_phase` is already `"post_retry"` — set during the append, not during execution. The label tracks registration time, not execution time. This exposes that there is no separation between registration and execution in this model.

**3. The two yield points are invisible to the phase system.** `DoAttempt` is labeled `phase="attempt"` and `DoSleep` is labeled `phase="sleep"`, but the phase system cannot express what makes these different from all other actions: they are the points where `iter()` returns control to the caller. The phase labels have no category for "yield point," revealing that the model does not represent its own most important structural feature.

---

## VI. Diagnostic Applied to the First Improvement

**What the improvement conceals:** `PhaseAction` makes actions look like discrete, well-labeled data objects. But every action still closes over `self` (the `BaseRetrying` instance) and reads/writes `self.iter_state`. The actions are not independent units — they are tightly coupled closures that happen to carry a name tag. The wrapper creates the *appearance* of encapsulation without the *property*.

**Property of the original problem recreated:** The coupling between the iteration mechanism and the state it mutates is still present — now it's hidden one layer deeper, inside `PhaseAction.__call__`. Worse: because actions look like data objects with metadata, future maintainers will attempt to serialize them, move them, or test them in isolation — and discover they are not portable at all.

---

## VII. Second Improvement: Addresses the Recreated Property

Break the closure coupling. Evaluate the lifecycle as a pure function that returns an explicit decision. The action queue becomes unnecessary for the callable case.

```python
import enum

class LifecycleOutcome(enum.Enum):
    DO_ATTEMPT = "do_attempt"
    DO_SLEEP   = "do_sleep"
    RETURN     = "return"
    RAISE      = "raise"


@dataclasses.dataclass
class LifecycleDecision:
    outcome: LifecycleOutcome
    return_value: object = None
    sleep_duration: float = 0.0
    exc: BaseException = None

    @classmethod
    def attempt(cls):
        return cls(outcome=LifecycleOutcome.DO_ATTEMPT)

    @classmethod
    def sleep(cls, duration: float):
        return cls(outcome=LifecycleOutcome.DO_SLEEP, sleep_duration=duration)

    @classmethod
    def returning(cls, value):
        return cls(outcome=LifecycleOutcome.RETURN, return_value=value)

    @classmethod
    def raising(cls, exc: BaseException):
        return cls(outcome=LifecycleOutcome.RAISE, exc=exc)


def evaluate_lifecycle(
    retry_object: "BaseRetrying",
    retry_state: "RetryCallState",
) -> LifecycleDecision:
    """
    Pure function: given current retry state, return what to do next.
    No side effects. No mutation of shared data structures.
    """
    fut = retry_state.outcome

    # ── First call: no outcome yet ──────────────────────────────────────────
    if fut is None:
        return LifecycleDecision.attempt()

    # ── Subsequent calls: evaluate outcome ──────────────────────────────────
    is_explicit_retry = fut.failed and isinstance(fut.exception(), TryAgain)
    should_retry = is_explicit_retry or retry_object.retry(retry_state)

    if not should_retry:
        # Success path: return or re-raise the result
        try:
            return LifecycleDecision.returning(fut.result())
        except BaseException as e:
            return LifecycleDecision.raising(e)

    # ── Must retry: compute wait and check stop ─────────────────────────────
    sleep_duration = retry_object.wait(retry_state) if retry_object.wait else 0.0

    # Update statistics as a side-effect boundary (acknowledged)
    elapsed = retry_state.outcome_timestamp - retry_state.start_time
    retry_object.statistics["delay_since_first_attempt"] = elapsed

    # We need upcoming_sleep set before stop check (stop may inspect it)
    retry_state.upcoming_sleep = sleep_duration
    should_stop = retry_object.stop(retry_state)

    if should_stop:
        if retry_object.retry_error_callback:
            return LifecycleDecision.returning(
                retry_object.retry_error_callback(retry_state)
            )
        retry_exc = retry_object.retry_error_cls(fut)
        if retry_object.reraise and fut.failed:
            return LifecycleDecision.raising(fut.exception())
        return LifecycleDecision.raising(retry_exc)

    return LifecycleDecision.sleep(sleep_duration)


class Retrying(BaseRetrying):
    def __call__(self, fn, *args, **kwargs):
        self.begin()
        retry_state = RetryCallState(
            retry_object=self, fn=fn, args=args, kwargs=kwargs
        )

        while True:
            # Run lifecycle hooks (side effects, acknowledged separately)
            if retry_state.outcome is None and self.before is not None:
                self.before(retry_state)
            elif retry_state.outcome is not None and self.after is not None:
                self.after(retry_state)

            decision = evaluate_lifecycle(self, retry_state)

            if decision.outcome is LifecycleOutcome.DO_ATTEMPT:
                try:
                    result = fn(*args, **kwargs)
                except BaseException:
                    retry_state.set_exception(sys.exc_info())
                else:
                    retry_state.set_result(result)

            elif decision.outcome is LifecycleOutcome.DO_SLEEP:
                if self.before_sleep is not None:
                    self.before_sleep(retry_state)
                self.statistics["idle_for"] += decision.sleep_duration
                self.statistics["attempt_number"] += 1
                retry_state.idle_for += decision.sleep_duration
                retry_state.next_action = RetryAction(decision.sleep_duration)
                self.sleep(decision.sleep_duration)
                retry_state.prepare_for_next_attempt()

            elif decision.outcome is LifecycleOutcome.RETURN:
                return decision.return_value

            elif decision.outcome is LifecycleOutcome.RAISE:
                raise decision.exc
```

---

## VIII. Diagnostic Applied to the Second Improvement

**What this improvement conceals:** `evaluate_lifecycle` looks pure, but it has an acknowledged side-effect boundary: it writes to `retry_state.upcoming_sleep` and `retry_object.statistics`. These writes are necessary because `stop` strategies can read `upcoming_sleep`, and statistics must be updated before `stop` is evaluated. The function is not actually pure — it has a dependency on mutation order that cannot be expressed in its type signature.

**What property of the original problem is now visible:** The second improvement recreates, in miniature, the *same ordering problem* the original code had, but now it's inside a single function rather than distributed across an action queue. `retry_state.upcoming_sleep = sleep_duration` must precede `stop(retry_state)` because stop predicates can inspect it. This is an **implicit temporal dependency** between lifecycle steps — and it exists in every implementation because it is a property of the problem, not the code.

---

## IX. The Structural Invariant

**The invariant that persists through every improvement:**

> **The retry lifecycle contains implicit temporal dependencies between its steps that cannot be eliminated by any refactoring, because they are requirements of the problem domain, not accidents of implementation.**

Specifically:
- `wait` must run before `stop`, because stop predicates can inspect upcoming sleep duration
- `stop` must run before sleep, because it determines *whether* sleep occurs
- The outcome must exist before any of these run, because they all condition on it
- Control must be returnable to the caller between *attempt* and *outcome*, because the caller executes the function

Every implementation attempt — the original action queue, the phase-labeled queue, the pure function — must encode these four ordering constraints. The original code encodes them via append-order inside closures. The improvement encodes them via sequential statements inside `evaluate_lifecycle`. The constraints are preserved because they are **the problem**, not an implementation choice.

The code's deepest structural feature is not a flaw: it is a manually implemented coroutine with exactly two yield points, required by the `__iter__` protocol. The action queue is what makes `iter()` usable both as `for attempt in Retrying()` and as `copy(fn, *args, **kwargs)` — the same decision logic serves both because it returns `DoAttempt` and `DoSleep` as values rather than calling `yield`. Every "improvement" that removes the queue must either drop `__iter__` support or reintroduce mediation through some equivalent mechanism (generators, callbacks, explicit state machines). The queue is not hiding a simpler design; it is the minimal-complexity encoding of a genuinely complex constraint: **pausable lifecycle evaluation without language-level coroutine support applied to both iterator and callable interfaces simultaneously.**
