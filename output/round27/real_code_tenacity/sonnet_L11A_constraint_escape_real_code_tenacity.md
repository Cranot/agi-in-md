## Structure First Analysis: Tenacity

---

### I. The Falsifiable Claim

**The deepest structural problem:** `IterState.actions` is a list that is constructed during its own traversal. In `iter()`, the `for action in self.iter_state.actions` loop executes, but `_post_retry_check_actions` and `_post_stop_check_actions` call `self._add_action_func(...)` mid-iteration — appending to the list being looped over. Python's list iterator follows appended items. The actual execution sequence for any given retry outcome is unrecoverable without simulating full execution.

**The specific, falsifiable form:** Given the inputs `(stop, wait, retry, reraise)` and a `retry_state` with a known outcome, you cannot determine the sequence of functions that will execute without running `_begin_iter` and observing what it appends, then running each appended function and observing what they conditionally append. There is no static representation of the control flow.

---

### II. Three Independent Experts

**Expert A (Defender):** The dynamic-append pattern is intentional lazy evaluation. Each action decides what further processing is warranted. `_post_retry_check_actions` doesn't append the stop-check if retry is unnecessary. This is cleaner than branching—actions compose without nested conditionals. It's continuation-passing style without the call stack overhead.

**Expert B (Attacker):** The append-during-iteration pattern is an abuse of Python's list iterator that is indistinguishable from a bug. More critically: `wraps()` contains `self._local.statistics = copy.statistics` — it aliases the *copy's* statistics dict into the *original object's* thread-local. The copy is supposed to be independent, but now both share the same statistics dict. This silently corrupts per-call isolation. That's not CPS elegance, that's a race condition wearing a strategy-pattern costume.

**Expert C (Questioner):** You're both arguing about the action list. Expert A says it's intentional CPS, Expert B says it's a mutation bug. But what do both of you assume without examining it?

You both assume that the retry policy (should I retry?) and the retry executor (run the thing, track state) *should be evaluated together in the same loop.* You treat the action chain as a sequencing problem when it might be an architecture problem. Why does `_run_retry` need access to `retry_state` to call `self.retry(retry_state)`? Because `self.retry` is a stateful object that needs to see *accumulated execution state* to make its decision. The real assumption: **the retry decider must live inside the execution loop.**

---

### III. Claim Transformation

**Original claim:** The action list builds itself during traversal, making control flow invisible.

**Transformed claim:** The code's deepest problem is that *retry policy evaluation is entangled with execution state accumulation*. The action chain is not the disease—it's a symptom of the real constraint: you cannot evaluate `stop_after_attempt(3)` without knowing how many attempts have occurred, which requires being inside the retry loop.

**The gap:** The original claim was mechanical (list mutation). The transformed claim is architectural (policy requires shared mutable state). The distance between them reveals that every syntactic fix—named stages, cleaner sequencing—preserves the real problem.

---

### IV. The Concealment Mechanism

**Named Strategy Parameters.** The constructor signature `Retrying(stop=stop_after_attempt(3), wait=wait_exponential(2), retry=retry_if_exception_type(IOError))` creates the illusion that behavior is fully specified by composing declarative strategies. The user sees configuration; the code hides that these strategies are callbacks handed into an implicit state machine whose transitions are encoded across three private methods. The strategies *look like* the system's behavior; the actual control flow lives invisibly in `_begin_iter → _post_retry_check_actions → _post_stop_check_actions`.

A user reading the constructor believes they understand what the retrier will do. They cannot, without reading the private action chain.

---

### V. The Improvement That Deepens Concealment

```python
# Improvement 1: Named Pipeline Stages
# Passes code review: adds documentation, explicitness, traceability.

from enum import Enum, auto
from typing import NamedTuple, Callable

class PipelineStage(Enum):
    PRE_ATTEMPT  = auto()
    RETRY_CHECK  = auto()
    WAIT_CALC    = auto()
    STOP_CHECK   = auto()
    POST_STOP    = auto()
    SLEEP        = auto()

@dataclasses.dataclass(slots=True)
class StagedAction(NamedTuple):
    stage: PipelineStage
    fn: Callable

@dataclasses.dataclass(slots=True)
class IterState:
    actions: list[StagedAction] = dataclasses.field(default_factory=list)
    retry_run_result: bool = False
    stop_run_result: bool = False
    is_explicit_retry: bool = False

    def reset(self):
        self.actions = []
        self.retry_run_result = False
        self.stop_run_result = False
        self.is_explicit_retry = False

    def add(self, stage: PipelineStage, fn: Callable):
        self.actions.append(StagedAction(stage, fn))

    def current_stages(self) -> list[PipelineStage]:
        """Returns which stages are currently scheduled."""
        return [a.stage for a in self.actions]


class BaseRetrying(ABC):
    # ...all existing methods, with _add_action_func replaced:
    
    def _add_action_func(self, fn: Callable, stage: PipelineStage = PipelineStage.PRE_ATTEMPT):
        self.iter_state.add(stage, fn)

    def _begin_iter(self, retry_state):
        self.iter_state.reset()
        fut = retry_state.outcome
        if fut is None:
            if self.before is not None:
                self._add_action_func(self.before, PipelineStage.PRE_ATTEMPT)
            self._add_action_func(lambda rs: DoAttempt(), PipelineStage.PRE_ATTEMPT)
            return
        self.iter_state.is_explicit_retry = fut.failed and isinstance(fut.exception(), TryAgain)
        if not self.iter_state.is_explicit_retry:
            self._add_action_func(self._run_retry, PipelineStage.RETRY_CHECK)
        self._add_action_func(self._post_retry_check_actions, PipelineStage.RETRY_CHECK)

    def _post_retry_check_actions(self, retry_state):
        if not (self.iter_state.is_explicit_retry or self.iter_state.retry_run_result):
            self._add_action_func(lambda rs: rs.outcome.result(), PipelineStage.POST_STOP)
            return
        if self.after is not None:
            self._add_action_func(self.after, PipelineStage.POST_STOP)
        self._add_action_func(self._run_wait, PipelineStage.WAIT_CALC)
        self._add_action_func(self._run_stop, PipelineStage.STOP_CHECK)
        self._add_action_func(self._post_stop_check_actions, PipelineStage.STOP_CHECK)

    def _post_stop_check_actions(self, retry_state):
        if self.iter_state.stop_run_result:
            if self.retry_error_callback:
                self._add_action_func(self.retry_error_callback, PipelineStage.POST_STOP)
                return

            def exc_check(rs):
                fut = rs.outcome
                retry_exc = self.retry_error_cls(fut)
                if self.reraise:
                    retry_exc.reraise()
                raise retry_exc from fut.exception()

            self._add_action_func(exc_check, PipelineStage.POST_STOP)
            return

        def next_action(rs):
            sleep = rs.upcoming_sleep
            rs.next_action = RetryAction(sleep)
            rs.idle_for += sleep
            self.statistics["idle_for"] += sleep
            self.statistics["attempt_number"] += 1

        self._add_action_func(next_action, PipelineStage.POST_STOP)
        if self.before_sleep is not None:
            self._add_action_func(self.before_sleep, PipelineStage.SLEEP)
        self._add_action_func(lambda rs: DoSleep(rs.upcoming_sleep), PipelineStage.SLEEP)

    def iter(self, retry_state):
        self._begin_iter(retry_state)
        result = None
        for staged_action in self.iter_state.actions:
            result = staged_action.fn(retry_state)
        return result
```

**Why it passes code review:** Named stages, typed actions, `current_stages()` introspection method, explicit stage annotations. Reviewers see "explicit pipeline." They approve.

---

### VI. Three Properties Visible Because We Tried to Strengthen It

1. **The stage list cannot be populated statically.** Attempting to name stages revealed that you cannot pre-populate `[PRE_ATTEMPT, RETRY_CHECK, WAIT_CALC, STOP_CHECK, SLEEP]` at construction time. Stages only exist at runtime because later stages depend on the *outcome* of earlier stages. The naming exercise proves the pipeline is not actually a pipeline.

2. **`PipelineStage.RETRY_CHECK` appears twice in the actions list** — once for `_run_retry` and once for `_post_retry_check_actions`. This means the stage enum doesn't describe stages; it describes categories of action. The sequencing is still in the append order, not the stage label. The names lie.

3. **`_post_retry_check_actions` and `_post_stop_check_actions` are the real control flow.** By annotating them as `PipelineStage.RETRY_CHECK` and `PipelineStage.STOP_CHECK`, we reveal that the *decision functions themselves are stages in the pipeline*. The strategies (`self.retry`, `self.stop`) are not the system—the private methods that invoke them and decide what to append next are the actual state machine.

---

### VII. What the Improvement Conceals; What It Recreates

**What the improved code conceals:** The stage labels suggest that `PRE_ATTEMPT → RETRY_CHECK → WAIT_CALC → STOP_CHECK → SLEEP` is a fixed sequence. It is not. The sequence is: whatever actions happen to be in the list at iteration time, which depends on outcomes, which depends on strategy return values.

**What property of the original problem is only visible because the improvement recreates it:** The improvement makes it obvious that `_post_retry_check_actions` — a function that *is itself an action* — appends further actions conditionally. This function *is not a stage*; it is a **branch in a state machine encoded as a list append**. The improvement, by forcing us to assign it a stage label, reveals that we are doing CPS (continuation-passing) through a mutable list: each function's "continuation" is decided by appending to the shared action list. The improvement recreates the original problem: control flow that is invisible until execution because it is built by execution.

---

### VIII. Second Improvement: Explicit State Machine

```python
# Improvement 2: Explicit Finite State Machine
# Addresses: control flow that is only visible at runtime

from enum import Enum, auto
from typing import Optional

class RetryPhase(Enum):
    BEFORE_ATTEMPT  = auto()
    DO_ATTEMPT      = auto()
    EVAL_RETRY      = auto()
    EVAL_STOP       = auto()
    CALC_SLEEP      = auto()
    BEFORE_SLEEP    = auto()
    DO_SLEEP        = auto()
    RETURN_RESULT   = auto()
    RAISE_ERROR     = auto()
    INVOKE_CALLBACK = auto()

# Transition table: phase -> (condition, next_phase_if_true, next_phase_if_false)
# None condition = unconditional
TRANSITIONS: dict[RetryPhase, tuple] = {
    RetryPhase.BEFORE_ATTEMPT: (None, RetryPhase.DO_ATTEMPT, None),
    RetryPhase.DO_ATTEMPT:     (None, RetryPhase.EVAL_RETRY, None),
    RetryPhase.EVAL_RETRY:     ("retry_needed", RetryPhase.CALC_SLEEP, RetryPhase.RETURN_RESULT),
    RetryPhase.CALC_SLEEP:     (None, RetryPhase.EVAL_STOP, None),
    RetryPhase.EVAL_STOP:      ("stop_triggered", RetryPhase.RAISE_ERROR, RetryPhase.BEFORE_SLEEP),
    RetryPhase.BEFORE_SLEEP:   (None, RetryPhase.DO_SLEEP, None),
    RetryPhase.DO_SLEEP:       (None, RetryPhase.BEFORE_ATTEMPT, None),
}

class RetryStateMachine:
    def __init__(self, retrying: BaseRetrying):
        self.retrying = retrying
        self.phase = RetryPhase.BEFORE_ATTEMPT
    
    def step(self, retry_state) -> Optional[object]:
        """Execute one phase transition. Returns action object or None."""
        r = self.retrying
        
        if self.phase == RetryPhase.BEFORE_ATTEMPT:
            if r.before: r.before(retry_state)
            self.phase = RetryPhase.DO_ATTEMPT
            return DoAttempt()
        
        elif self.phase == RetryPhase.DO_ATTEMPT:
            # Outcome set externally. Check for explicit retry first.
            fut = retry_state.outcome
            if fut.failed and isinstance(fut.exception(), TryAgain):
                # Explicit retry: skip retry check
                self.phase = RetryPhase.CALC_SLEEP
            else:
                self.phase = RetryPhase.EVAL_RETRY
            return None  # no external action
        
        elif self.phase == RetryPhase.EVAL_RETRY:
            retry_needed = r.retry(retry_state)
            if not retry_needed:
                self.phase = RetryPhase.RETURN_RESULT
            else:
                if r.after: r.after(retry_state)
                self.phase = RetryPhase.CALC_SLEEP
            return None
        
        elif self.phase == RetryPhase.CALC_SLEEP:
            sleep = r.wait(retry_state) if r.wait else 0.0
            retry_state.upcoming_sleep = sleep
            r.statistics["delay_since_first_attempt"] = retry_state.seconds_since_start
            self.phase = RetryPhase.EVAL_STOP
            return None
        
        elif self.phase == RetryPhase.EVAL_STOP:
            stop_triggered = r.stop(retry_state)
            if stop_triggered:
                self.phase = RetryPhase.RAISE_ERROR
            else:
                self.phase = RetryPhase.BEFORE_SLEEP
            return None
        
        elif self.phase == RetryPhase.BEFORE_SLEEP:
            sleep = retry_state.upcoming_sleep
            retry_state.next_action = RetryAction(sleep)
            retry_state.idle_for += sleep
            r.statistics["idle_for"] += sleep
            r.statistics["attempt_number"] += 1
            if r.before_sleep: r.before_sleep(retry_state)
            self.phase = RetryPhase.DO_SLEEP
            return DoSleep(sleep)
        
        elif self.phase == RetryPhase.DO_SLEEP:
            retry_state.prepare_for_next_attempt()
            self.phase = RetryPhase.BEFORE_ATTEMPT
            return None
        
        elif self.phase == RetryPhase.RETURN_RESULT:
            return retry_state.outcome.result()
        
        elif self.phase == RetryPhase.RAISE_ERROR:
            if r.retry_error_callback:
                return r.retry_error_callback(retry_state)
            fut = retry_state.outcome
            retry_exc = r.retry_error_cls(fut)
            if r.reraise:
                retry_exc.reraise()
            raise retry_exc from fut.exception()


class Retrying(BaseRetrying):
    def __call__(self, fn, *args, **kwargs):
        self.begin()
        retry_state = RetryCallState(retry_object=self, fn=fn, args=args, kwargs=kwargs)
        sm = RetryStateMachine(self)
        while True:
            action = sm.step(retry_state)
            if isinstance(action, DoAttempt):
                try:
                    result = fn(*args, **kwargs)
                except BaseException:
                    retry_state.set_exception(sys.exc_info())
                    sm.step(retry_state)  # DO_ATTEMPT phase, sets next phase
                else:
                    retry_state.set_result(result)
                    sm.step(retry_state)
            elif isinstance(action, DoSleep):
                self.sleep(action)
            elif action is not None:
                return action
```

---

### IX. Applying the Diagnostic to Improvement 2

**What does Improvement 2 conceal?**

The state machine makes all phases visible and all transitions explicit. But it conceals this: **the strategies (`r.retry`, `r.stop`, `r.wait`) are called with `retry_state` — a mutable object containing accumulated execution history.** The state machine made the *executor's* state explicit. It did nothing about the strategies' implicit dependency on that state.

`stop_after_attempt(3)` reads `retry_state.attempt_number`. `wait_exponential` reads `retry_state.attempt_number` to compute `2^n`. These strategies are not pure functions. They take mutable shared state as input. The state machine improvement made it look like strategies are called with clean data, but `retry_state` carries everything — and the strategies can read whatever they like from it.

**What property of the original problem is visible because Improvement 2 recreates it?**

`step()` in phase `EVAL_RETRY` calls `r.retry(retry_state)` — and if it returns True, calls `r.after(retry_state)` before moving to `CALC_SLEEP`. But `r.after` is a lifecycle hook that can *observe and modify* `retry_state`. This recreates the original problem: **callbacks with access to shared mutable execution state are embedded in the control flow.** The state machine gave the phases names; it didn't give the strategies a pure interface. The strategies still reach into the executor's private state.

This property is only visible because Improvement 2 made the phase transitions explicit. Once we could see the full state machine on one screen, we could ask: "what do these strategies actually receive?" The answer revealed the residual coupling.

---

### X. The Structural Invariant

Through every improvement — named stages, explicit state machine, typed transitions — one property persisted:

> **Retry policy evaluation requires access to accumulated execution state, and that state is produced by the executor. Policy and execution share a mutable object (`RetryCallState`), and no refactoring within a synchronous retry loop can remove this dependency.**

This is not an implementation detail. It is a constraint of the problem:

- `stop_after_attempt(3)` needs `attempt_number`
- `stop_after_delay(30.0)` needs `start_time` and current time
- `retry_if_exception_type(IOError)` needs the actual exception

All of this is produced *by* the execution loop. Any strategy that consults it is reading shared mutable state. Every improvement either moved the coupling (named it) or hid it (abstracted it) but preserved it.

---

### XI. The Category Boundary

**Category name: Stateful Retry Executors**

Systems in this category: policy evaluation occurs *inside* the retry loop; strategies are callbacks that observe accumulated execution state; the executor and the decider share state through a common mutable object.

All major Python retry libraries live here: tenacity, retry, backoff, stamina. The invariant is the price of entry.

---

### XII. The Adjacent Category: Retry as Policy Over Attempt Stream

**The design that dissolves the invariant:**

```python
import time, sys
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator
from concurrent.futures import Future

# ─────────────────────────────────────────────
# PURE DATA: the result of one attempt
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class AttemptRecord:
    number: int
    elapsed_seconds: float
    exception: Exception | None
    result: Any

    @property
    def failed(self) -> bool:
        return self.exception is not None

NO_RESULT = object()


# ─────────────────────────────────────────────
# PURE DATA: what the policy decides
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class RetryDecision:
    should_retry: bool
    sleep_for: float = 0.0

STOP   = RetryDecision(should_retry=False)
RETRY  = RetryDecision(should_retry=True)


# ─────────────────────────────────────────────
# POLICY: pure function AttemptRecord -> RetryDecision
# ─────────────────────────────────────────────

Policy = Callable[[AttemptRecord], RetryDecision]


def stop_after_attempt(n: int) -> Policy:
    def policy(attempt: AttemptRecord) -> RetryDecision:
        if attempt.number >= n:
            return STOP
        return RETRY
    return policy

def stop_after_delay(seconds: float) -> Policy:
    def policy(attempt: AttemptRecord) -> RetryDecision:
        if attempt.elapsed_seconds >= seconds:
            return STOP
        return RETRY
    return policy

def retry_if_exception_type(*exc_types) -> Policy:
    def policy(attempt: AttemptRecord) -> RetryDecision:
        if attempt.exception is None:
            return STOP  # success, shouldn't be called
        if isinstance(attempt.exception, tuple(exc_types)):
            return RETRY
        return STOP
    return policy

def wait_exponential(multiplier: float = 1.0, base: float = 2.0) -> Policy:
    """Returns a policy that always retries but specifies sleep duration."""
    def policy(attempt: AttemptRecord) -> RetryDecision:
        return RetryDecision(should_retry=True, sleep_for=multiplier * (base ** (attempt.number - 1)))
    return policy


# ─────────────────────────────────────────────
# COMPOSITION: policies are pure functions, compose freely
# ─────────────────────────────────────────────

def all_of(*policies: Policy) -> Policy:
    """Retry only if ALL policies say retry."""
    def combined(attempt: AttemptRecord) -> RetryDecision:
        sleep_for = 0.0
        for p in policies:
            decision = p(attempt)
            if not decision.should_retry:
                return STOP
            sleep_for = max(sleep_for, decision.sleep_for)
        return RetryDecision(should_retry=True, sleep_for=sleep_for)
    return combined

def any_of(*policies: Policy) -> Policy:
    """Retry if ANY policy says retry."""
    def combined(attempt: AttemptRecord) -> RetryDecision:
        sleep_for = 0.0
        for p in policies:
            decision = p(attempt)
            if decision.should_retry:
                sleep_for = max(sleep_for, decision.sleep_for)
                return RetryDecision(should_retry=True, sleep_for=sleep_for)
        return STOP
    return combined


# ─────────────────────────────────────────────
# EXECUTOR: purely mechanical, no retry logic
# ─────────────────────────────────────────────

@dataclass
class RetryError(Exception):
    last_attempt: AttemptRecord

def attempt_stream(fn: Callable, *args, **kwargs) -> Iterator[AttemptRecord]:
    """Generates an infinite stream of AttemptRecords. No retry logic here."""
    attempt_number = 0
    start_time = time.monotonic()
    while True:
        attempt_number += 1
        t0 = time.monotonic()
        try:
            result = fn(*args, **kwargs)
            yield AttemptRecord(
                number=attempt_number,
                elapsed_seconds=time.monotonic() - start_time,
                exception=None,
                result=result,
            )
            return  # success terminates stream
        except Exception as e:
            yield AttemptRecord(
                number=attempt_number,
                elapsed_seconds=time.monotonic() - start_time,
                exception=e,
                result=NO_RESULT,
            )

def execute_with_policy(fn: Callable, policy: Policy, 
                         sleep_fn: Callable = time.sleep,
                         *args, **kwargs) -> Any:
    """
    Mechanical executor: consult policy after each attempt, sleep if told to,
    stop if told to. No retry logic in this function.
    """
    for attempt in attempt_stream(fn, *args, **kwargs):
        if not attempt.failed:
            return attempt.result
        
        decision = policy(attempt)
        if not decision.should_retry:
            raise RetryError(attempt) from attempt.exception
        
        if decision.sleep_for > 0:
            sleep_fn(decision.sleep_for)


# ─────────────────────────────────────────────
# DECORATOR INTERFACE
# ─────────────────────────────────────────────

def retry(policy: Policy, sleep_fn: Callable = time.sleep):
    def decorator(fn: Callable) -> Callable:
        import functools
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return execute_with_policy(fn, policy, sleep_fn, *args, **kwargs)
        wrapper.policy = policy
        return wrapper
    return decorator


# ─────────────────────────────────────────────
# USAGE
# ─────────────────────────────────────────────

my_policy = all_of(
    retry_if_exception_type(IOError, TimeoutError),
    stop_after_attempt(5),
    stop_after_delay(30.0),
    wait_exponential(multiplier=0.5),
)

@retry(my_policy)
def fetch_data(url: str) -> bytes:
    ...
```

**How this succeeds where every improvement failed:**

- **`AttemptRecord` is frozen/immutable.** Policies cannot modify execution state. The policy receives a snapshot.
- **`Policy` is a pure function.** It can be unit-tested with no executor: `assert stop_after_attempt(3)(AttemptRecord(number=3, ...)) == STOP`.
- **Composition is algebraic.** `all_of(p1, p2, p3)` is a policy. `any_of(stop_after_attempt(5), wait_exponential())` is a policy. The composition is a value, not a method chain.
- **The executor has no retry logic.** `execute_with_policy` contains zero branching on retry strategy. It iterates, consults, sleeps, stops. That's all.
- **Control flow is statically visible.** `attempt_stream → policy → sleep | stop` is the entire structure. No implicit phase transitions.

---

### XIII. The New Impossibility

**What is trivial in the original category:**

`TryAgain` — raising an exception from inside the retried function to force a retry. And `AttemptManager` — letting code under retry participate in retry decisions from within the attempt. Also: lifecycle hooks (`before`, `after`, `before_sleep`) that can observe *and modify* the retry state from inside the execution.

**What becomes impossible in the adjacent category:**

**In-function retry control.** If `fn()` raises `TryAgain`, the executor sees it as an exception and passes it to `policy(attempt)`. But `policy` is a pure function that maps `AttemptRecord → RetryDecision`. It knows the exception type. But it cannot distinguish "this function knows it should retry and said so explicitly" from "this function hit an unexpected error." The `TryAgain` signal breaks the pure data boundary: it is a **control flow signal masquerading as an exception**, and the pure policy design has no first-class mechanism for it.

To support `TryAgain` in the adjacent category, you'd need to add a special case in `execute_with_policy`:

```python
if isinstance(attempt.exception, TryAgain):
    sleep_fn(0)  # or use decision.sleep_for
    continue
```

But now the executor has retry logic again. The invariant creeps back.

Similarly: **stateful lifecycle hooks.** `before_sleep(retry_state)` can modify `retry_state` — log to databases, update external counters, cancel other tasks. In the pure policy design, hooks can observe `AttemptRecord` but cannot modify what happens next (they don't participate in `RetryDecision`). A hook that needs to *change* the retry behavior — say, "after 3 attempts, switch to a different endpoint" — cannot do so through a pure read-only interface.

---

### XIV. The Trade-Off: The Finding

| Dimension | Stateful Executor (tenacity) | Pure Policy (adjacent) |
|---|---|---|
| **Control flow** | Invisible until execution; emerges from list appends | Statically visible; fixed loop structure |
| **Policy testability** | Impossible without executor; strategies need `RetryCallState` | Trivial; policies are pure functions |
| **Composition** | Methods on strategies; `\|` operator hacks | Algebraic; `all_of`, `any_of` are values |
| **In-function control** | Trivial: `raise TryAgain()` | Impossible without breaking the pure boundary |
| **Lifecycle hooks** | Full mutable access to execution state | Read-only snapshots; cannot affect decisions |
| **Stateful strategies** | Natural; strategies are objects with state | Requires threading state through `AttemptRecord` |

**The finding:**

Tenacity's structural problem — action chain that builds itself during traversal, policy entangled with execution, control flow invisible to static analysis — is not an accident. It is the architectural cost of a specific feature: **the ability for code under retry to participate in its own retry decision from inside the attempt.**

`TryAgain`, `AttemptManager`, and mutable lifecycle hooks all require that the retry mechanism be co-present with the execution, reading and writing shared state. This requirement is what forces policy and execution to share `RetryCallState`. This is what forces the action chain. This is what makes control flow invisible.

The concealment mechanism — **named strategy parameters** — hides this cost by making the system look like pure strategy composition. Users see a clean interface; the entanglement lives in three private methods no one reads.

Every improvement (named stages, explicit state machine) moved the entanglement, named it, or gave it better structure. None removed it, because the entanglement is not in the code — it is in the requirement that `raise TryAgain()` work.

**The old impossibility:** Testing retry policy without the executor. In tenacity, you cannot verify that `stop_after_attempt(3)` stops at attempt 3 without constructing a `RetryCallState` and simulating the loop. The policy is not separable from the execution.

**The new impossibility:** In-function retry control and mutable lifecycle hooks. In the pure policy design, a function cannot signal "I know I should retry" from inside itself, and hooks cannot modify retry behavior dynamically.

**The trade-off in one sentence:** Tenacity chose a design where the function controls the retry, at the cost of making the retry unverifiable in isolation; the pure policy design makes the retry verifiable in isolation, at the cost of making the function's control over its own retry impossible.
