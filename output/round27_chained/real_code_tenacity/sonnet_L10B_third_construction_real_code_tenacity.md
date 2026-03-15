## Structure First: Level 10 Diagnostic

---

### The Falsifiable Claim

> **`_post_retry_check_actions` and `_post_stop_check_actions` are not pipeline stages — they are routing nodes that enqueue their own continuations into the work queue during execution. The `for action in self.iter_state.actions` loop traverses an implicit decision tree by materializing one level of edges at a time: after `_begin_iter` returns with `retry_state.outcome` set, `iter_state.actions` contains exactly two items. The remaining 1–5 actions are added by routing nodes mid-iteration. The complete execution plan does not exist at any point before execution ends.**

Falsifiable: after `_begin_iter(retry_state)` with a failing, retriable outcome, `len(iter_state.actions) == 2`. After the loop completes on the "retry needed, stop=False, before_sleep set" path, `len(iter_state.actions) == 7`. The difference of 5 actions was added by running the first 2. There is no architectural moment when the plan exists whole. Any introspection tool that reads `iter_state.actions` after setup sees an incomplete plan that will be assembled by executing the plan.

Python's `for item in list` processes items appended during iteration because the loop uses an index counter against a live list reference. `_post_retry_check_actions` and `_post_stop_check_actions` exploit this: they are not consumers of the work queue, they are producers of the work queue's continuation. The for loop is simultaneously the queue processor and the mechanism by which the queue grows.

---

### The Dialectic

**Expert 1 — Defender**

The self-extending work queue is consequential because it makes structural testing impossible at the plan level. A developer who wants to verify "the correct action sequence for a stop condition" cannot inspect `iter_state.actions` before iteration — it's incomplete. To verify the sequence, they must execute the loop and observe side effects. This means: test coverage of the action chain requires running the full execution, including strategy evaluation; any assertion about "what actions will run" is actually an assertion about "what actions ran"; and the topology of the decision tree — how many branches exist, what triggers each — cannot be determined by static analysis. The plan is knowable only in retrospect.

The concealment deepens through extension. Suppose a developer adds a new routing node to support `retry_if_result`. They call `_add_action_func(self._run_result_check)` then `_add_action_func(self._post_result_check_actions)`. The new node `_post_result_check_actions` must add `after`, `_run_wait`, `_run_stop`, `_post_stop_check_actions` — or not, depending on its decision. Nothing in the existing architecture signals this requirement. The developer doesn't know their new node must add continuation actions, not just compute a result. The work queue's contract ("routing nodes must materialize their outgoing edges or the loop terminates prematurely") is invisible.

**Expert 2 — Attacker**

The self-extending list is Python-idiomatic and deliberate. The pattern makes each routing node independently testable: call `_post_retry_check_actions(retry_state)` directly and inspect what it adds to `iter_state.actions` — this verifies the node's branching behavior without triggering downstream execution. The claim "the plan cannot be known before execution" is vacuously true of any program with conditional logic. You cannot know which branch of `if should_retry:` will be taken before evaluating `should_retry`. The work queue makes branching-by-execution explicit rather than hiding it inside `if/else` blocks.

Furthermore: this is private API. The work queue structure is not visible to callers. Users provide `retry`, `stop`, `wait`, `before`, `after`, `before_sleep` — none of these interact with `iter_state.actions`. The routing node pattern is an encapsulation choice with no external contract violations.

**Expert 3 — Prober**

Both experts argue about whether the work queue is acceptable. Neither asks: **why can't `_begin_iter` simply evaluate all strategies and pre-build the complete action list?**

Examine `_post_retry_check_actions`:

```python
def _post_retry_check_actions(self, retry_state):
    if not (self.iter_state.is_explicit_retry or self.iter_state.retry_run_result):
        self._add_action_func(lambda rs: rs.outcome.result())
        return
    if self.after is not None:
        self._add_action_func(self.after)      # ← added BEFORE wait/stop evaluation
    self._add_action_func(self._run_wait)
    self._add_action_func(self._run_stop)
    self._add_action_func(self._post_stop_check_actions)
```

If we pre-evaluated: `_begin_iter` would call `self.retry(retry_state)`, determine `should_retry`, and if True, immediately call `self.wait(retry_state)` and `self.stop(retry_state)` to build the complete action list. But `after` is registered before `_run_wait` and `_run_stop`. Its position in the plan encodes a timing requirement: `after` fires after retry evaluation but before wait and stop evaluation.

Under pre-evaluation, `self.wait` and `self.stop` run during plan construction — before `after` executes. By the time `after` fires (during the execution loop), `retry_state.upcoming_sleep` has already been set. `after` now observes a different `retry_state` than it currently observes.

The prober's real question: **is the callback timing window — `after` fires between `_run_retry` and `_run_wait`/`_run_stop` — a semantic contract or an accidental artifact of the work queue's structure?** If it's a contract, the work queue is not an implementation choice; it is the only architecture that preserves callback windows defined relative to other evaluation events. If it's accidental, pre-evaluation would be equivalent and cleaner.

The code documents neither position. The window exists; its contractual status is unknown.

---

### The Transformation

| | |
|---|---|
| **Original claim** | Routing nodes self-extend the work queue mid-iteration, making the execution plan unknowable before it starts |
| **Transformed claim** | The work queue's dynamic assembly is mandated by the requirement that callbacks fire in windows defined relative to strategy evaluations. `after` fires after `retry` decides but before `stop` evaluates; `before_sleep` fires after `stop` evaluates but before `DoSleep`. These windows cannot be preserved under pre-evaluation, because pre-evaluation changes what `retry_state` contains when each callback fires. The decision tree structure is invisible not because nobody drew it, but because it is the consequence of encoding evaluation windows as execution order within a sequentially-processed work queue. |

The gap: the original is a structural observation ("the plan assembles itself"). The transformed is a causal claim ("the plan must assemble itself because any static alternative changes the temporal relationship between callbacks and the state mutations they observe"). The original identifies what the code does. The transformed identifies why no simpler architecture can do it the same way.

The gap was forced by the prober's question: *why can't `_begin_iter` pre-build the plan?* Answering that question requires identifying what changes under pre-evaluation — specifically, the state of `retry_state` when `after` fires. That answer reveals the observation window, which reveals that the work queue encodes timing constraints that have no other representation.

---

### The Concealment Mechanism: Observation Window Erasure

The callback interface is `(retry_state) -> None`. Every callback receives `retry_state` and observes it at execution time. Each callback has an implicit observation window: a set of strategy evaluations that have or have not yet run when the callback fires. These windows determine what the callback can validly read from `retry_state`.

**Observation Window Erasure**: the observation windows for callbacks are encoded as execution order within the work queue, with no specification, annotation, or documentation of which `retry_state` fields are set or unset when each callback fires. The windows exist — they are architecturally enforced — but they are invisible. Readers who want to know "when does `after` fire relative to stop evaluation?" must trace `_add_action_func` call sequences across two routing nodes. No API contract, no docstring, no type annotation captures this.

This differs from L9's Pipeline Simulacrum. L9's mechanism conceals that data flows through `IterState` rather than return values — a mismatch between the visual idiom (pipeline) and the actual data model. Observation Window Erasure conceals the timing relationships between strategy evaluations and callback executions — the constraints are invisible rather than misattributed. A reader who correctly understands that IterState carries inter-stage data still cannot determine from the code when `after` fires relative to `upcoming_sleep` being set.

**Applying it — the actual observation windows:**

| Callback | Fires when | `upcoming_sleep` state | `outcome` state | Stop evaluated? |
|---|---|---|---|---|
| `before` | Before first attempt | previous (0.0) | None | No |
| `after` | After retry decided, before wait/stop | previous attempt's value | set | **No** |
| `before_sleep` | After stop decided (False), before `DoSleep` | set to current sleep | set | Yes (False) |
| `retry_error_callback` | After stop decided (True) | set to current sleep | set | Yes (True) |

An `after` callback that reads `retry_state.upcoming_sleep` to report "sleeping for X seconds after this failure" will report the **previous** attempt's sleep value — or 0.0 on the first retry — because `_run_wait` has not yet executed when `after` fires. This is a silent semantic trap. The Observation Window Erasure mechanism makes it invisible: the constraint is encoded only as the registration order of `after` before `_run_wait` in `_post_retry_check_actions`.

---

### Engineering the Concealment-Deepening Improvement

Introduce `ExecutionPhase` annotations that make the action plan appear structurally organized into well-ordered phases:

```python
from enum import Enum, auto

class ExecutionPhase(Enum):
    SETUP = auto()        # before callbacks, DoAttempt
    EVALUATION = auto()   # strategy evaluation: _run_retry, _run_wait, _run_stop
    NOTIFICATION = auto() # observability callbacks: after, before_sleep
    DECISION = auto()     # routing nodes: _post_retry_check_actions, _post_stop_check_actions
    TERMINAL = auto()     # DoSleep, result return, exception raise

@dataclasses.dataclass
class PhasedAction:
    """An action annotated with its execution phase.

    Phase annotations make the execution plan's structure observable
    for tracing and debugging. Actions within a phase run in registration
    order. Use phase_hook() to inject middleware at phase boundaries.
    
    Example:
        @retrying.phase_hook(ExecutionPhase.NOTIFICATION)
        def trace(retry_state):
            log(f"outcome={retry_state.outcome}")
    """
    action: callable
    phase: ExecutionPhase
    description: str = ""

    def __call__(self, retry_state):
        return self.action(retry_state)
```

Update registration and all action sites:

```python
def _add_action_func(self, fn, phase=ExecutionPhase.SETUP, description=""):
    self.iter_state.actions.append(
        PhasedAction(fn, phase, description or getattr(fn, '__name__', repr(fn)))
    )

def _begin_iter(self, retry_state):
    ...
    self._add_action_func(self._run_retry, ExecutionPhase.EVALUATION, "evaluate_retry")
    self._add_action_func(self._post_retry_check_actions, ExecutionPhase.DECISION, "retry_branch")

def _post_retry_check_actions(self, retry_state):
    if not (...):
        self._add_action_func(lambda rs: rs.outcome.result(), ExecutionPhase.TERMINAL, "return_result")
        return
    if self.after is not None:
        self._add_action_func(self.after, ExecutionPhase.NOTIFICATION, "after")
    self._add_action_func(self._run_wait, ExecutionPhase.EVALUATION, "evaluate_wait")
    self._add_action_func(self._run_stop, ExecutionPhase.EVALUATION, "evaluate_stop")
    self._add_action_func(self._post_stop_check_actions, ExecutionPhase.DECISION, "stop_branch")
```

This passes code review: phases are self-documenting; `PhasedAction.description` makes each step traceable; the `phase_hook` extension point enables monitoring middleware; the implementation is backward compatible; `IterState.actions` can now be printed as a structured plan.

**It deepens concealment**: the `ExecutionPhase` vocabulary implies that phases are contiguous ordered blocks — SETUP, then EVALUATION, then NOTIFICATION, then TERMINAL. The actual execution sequence for the "retry, no stop, before_sleep set" path is:

`EVALUATION → DECISION → NOTIFICATION → EVALUATION → EVALUATION → DECISION → NOTIFICATION → TERMINAL`

`NOTIFICATION(after)` fires between the first and second `EVALUATION` blocks. A developer reading the phase annotations and inferring "all EVALUATION completes before NOTIFICATION fires" will write an `after` callback that reads `retry_state.upcoming_sleep` expecting EVALUATION to have set it — and will silently observe the previous attempt's value. The `PhasedAction` improvement adds a vocabulary that actively suggests correct temporal ordering while the actual ordering violates it. The semantic trap is now hidden under an additional layer of apparent structure.

---

### Three Properties Visible Only Because We Tried to Strengthen It

**1. The `EVALUATION` phase is non-contiguous: it spans two separate runs separated by `NOTIFICATION`.**

Assigning phases to the full execution sequence reveals:
```
[EVALUATION(retry), DECISION(branch), NOTIFICATION(after), EVALUATION(wait), EVALUATION(stop), DECISION(branch), NOTIFICATION(before_sleep), TERMINAL(DoSleep)]
```

`EVALUATION` appears in positions 0, 3, and 4 — spanning a `NOTIFICATION` in between. A phase that appears in multiple non-contiguous positions is not a phase; it is a concern that is interleaved with other concerns. This is not a labeling problem — it reveals that the decision to fire `after` between `retry` and `wait`/`stop` evaluations is a semantic requirement encoded as execution position. The non-contiguity of `EVALUATION` is the structural signature of Observation Window Erasure: the window boundaries are gaps in what would otherwise be a contiguous evaluation block.

Any phase-based middleware that injects at "end of EVALUATION" would trigger after `evaluate_retry` — before `evaluate_wait` and `evaluate_stop`. The phases cannot be used to reason about when "all evaluation is complete." The `PhasedAction` improvement makes this architectural split visible for the first time by forcing a labeling decision that reveals the sequencing.

**2. `DECISION` actions carry an implicit liveness postcondition that has no architectural support.**

When assigning `ExecutionPhase.DECISION` to `_post_retry_check_actions` and `_post_stop_check_actions`, the labeling reveals a structural requirement that the code never enforces: routing nodes must enqueue at least one `TERMINAL` action before the loop ends, or `iter()` returns `None`. The callers — `__iter__` and `__call__` — check `isinstance(do, DoAttempt)` and `isinstance(do, DoSleep)` and fall through to `else: break` or `return do` when neither matches. If a routing node adds zero actions, the loop terminates, returning `None` from `iter()`. `__call__` returns `None` from the decorated function. No exception. No warning.

This postcondition — "routing nodes must eventually enqueue a terminal" — is the liveness property of the work queue. It exists only in the programmer's knowledge of which actions are last, which is exactly the ordering-constraint problem L9 identified. The `PhasedAction` improvement makes this visible by introducing a `DECISION` label and a `TERMINAL` label with no structural relationship between them. Any enforcement of "DECISION must eventually enqueue TERMINAL" would require a mechanism the architecture doesn't have.

**3. The action abstraction conflates two structurally different operation kinds with no architectural distinction.**

When wrapping all `_add_action_func` targets in `PhasedAction`, the wrapper treats `_post_retry_check_actions` and `lambda rs: DoSleep(rs.upcoming_sleep)` identically: both are `PhasedAction(action: callable, phase: ..., description: ...)`. But they are structurally different kinds of operations:

- **Object-level actions** (`_run_retry`, `_run_wait`, `after`, `DoSleep` lambda): operate on `retry_state` and/or produce a return value for the caller. Their primary effect is on the per-attempt record.  
- **Meta-level actions** (`_post_retry_check_actions`, `_post_stop_check_actions`): operate on `iter_state.actions` — the execution plan itself. Their primary effect is on the work queue, not on `retry_state`. Their return value is always `None`; their "output" is the set of actions they enqueue.

The `PhasedAction` wrapper has no field for "modifies execution plan vs. modifies retry state." Both kinds carry the same signature, same wrapper, same interface. This conflation means: you cannot determine from an action's type whether it will mutate the work queue mid-iteration. You must read its body. The architecture's action abstraction is reused for operations at two different semantic levels — object level and meta level — with no structural mechanism to distinguish them. The `PhasedAction` improvement makes this conflation more visible by wrapping both kinds in the same typed container, revealing that the container cannot represent the distinction.

---

### The Contradicting Second Improvement

Replace the self-extending work queue with pre-built plan construction: separate "deciding what to do" from "doing it."

```python
class BaseRetrying:
    def iter(self, retry_state):
        """Execute one iteration with a pre-built, immutable execution plan.

        _construct_plan evaluates all branching conditions before any action
        runs. iter_state.actions is fully populated before the execution loop
        begins — no action can modify iter_state.actions during iteration.
        """
        self._construct_plan(retry_state)
        result = None
        for action in self.iter_state.actions:  # immutable during execution
            result = action(retry_state)
        return result

    def _construct_plan(self, retry_state):
        """Build the complete execution plan for this iteration.

        All branching logic is explicit here as if/else. Callers can inspect
        iter_state.actions after this returns to see the complete execution
        sequence before any action fires.
        """
        self.iter_state.reset()
        fut = retry_state.outcome

        if fut is None:
            if self.before is not None:
                self._add_action_func(self.before)
            self._add_action_func(lambda rs: DoAttempt())
            return

        is_explicit_retry = fut.failed and isinstance(fut.exception(), TryAgain)
        self.iter_state.is_explicit_retry = is_explicit_retry

        should_retry = is_explicit_retry or bool(self.retry(retry_state))
        self.iter_state.retry_run_result = should_retry

        if not should_retry:
            self._add_action_func(lambda rs: rs.outcome.result())
            return

        if self.after is not None:
            self._add_action_func(self.after)

        sleep = self.wait(retry_state) if self.wait else 0.0
        retry_state.upcoming_sleep = sleep
        self.statistics["delay_since_first_attempt"] = retry_state.seconds_since_start
        should_stop = bool(self.stop(retry_state))
        self.iter_state.stop_run_result = should_stop

        if should_stop:
            if self.retry_error_callback:
                self._add_action_func(self.retry_error_callback)
                return
            def exc_check(rs):
                retry_exc = self.retry_error_cls(rs.outcome)
                if self.reraise:
                    retry_exc.reraise()
                raise retry_exc from rs.outcome.exception()
            self._add_action_func(exc_check)
            return

        def next_action(rs):
            rs.next_action = RetryAction(rs.upcoming_sleep)
            rs.idle_for += rs.upcoming_sleep
            self.statistics["idle_for"] += rs.upcoming_sleep
            self.statistics["attempt_number"] += 1

        self._add_action_func(next_action)
        if self.before_sleep is not None:
            self._add_action_func(self.before_sleep)
        self._add_action_func(lambda rs: DoSleep(rs.upcoming_sleep))
```

This passes code review independently: all branching logic is explicit `if/else`; `iter_state.actions` is fully populated before execution; `_construct_plan` can be called without executing to inspect the plan; `_post_retry_check_actions` and `_post_stop_check_actions` are eliminated; the routing-node complexity vanishes; the code is significantly easier to read and test.

**How it contradicts Improvement 1:**

Improvement 1 (PhasedAction) preserves the work-queue dynamics and annotates each incrementally-added action with phase metadata. Improvement 2 eliminates work-queue dynamics entirely — `_add_action_func` is only called during `_construct_plan`, never during iteration. These are structurally incompatible: Improvement 1's value proposition ("annotate each step as it is added") requires the incremental addition pattern that Improvement 2 destroys.

More fundamentally: Improvement 1 preserves the current callback timing (`after` fires before `stop` is evaluated). Improvement 2 changes it: `self.stop(retry_state)` runs during `_construct_plan`, before `after` executes. In Improvement 2's execution sequence, `after` fires after `retry_state.upcoming_sleep` has already been set. A monitoring callback reading `upcoming_sleep` inside `after` now observes the **current** attempt's sleep — not the previous attempt's value. This is a behavioral change from the original. Improvement 1 keeps the original behavior (at the cost of accepting the dynamic assembly). Improvement 2 gets the cleaner structure (at the cost of changing the observation window). They cannot both be applied: one accepts the timing; the other changes it.

---

### The Structural Conflict

Both improvements are legitimate because both address real problems:

- Improvement 1 (PhasedAction): targets invisible observation windows. Annotating what each callback can observe makes the timing constraints legible without changing behavior.
- Improvement 2 (pre-built plan): targets plan unknowability. Pre-evaluating strategies makes the execution topology inspectable before iteration begins.

**The structural conflict that exists only because both are legitimate:**

Callback observation windows are defined by the position of callbacks relative to strategy evaluations in the execution sequence. Making the execution sequence pre-inspectable (Improvement 2) requires evaluating strategies before callbacks run, which changes the `retry_state` contents that callbacks observe. Annotating the observation windows (Improvement 1) requires preserving the execution sequence — including the dynamic work-queue assembly that makes the windows invisible.

These are jointly unsatisfiable under the current callback interface: a plan that is (a) pre-inspectable AND (b) preserves current callback observation windows does not exist. To be pre-inspectable, strategies must evaluate during plan construction. To preserve callback windows, strategies must evaluate interleaved with callback execution. These requirements have opposite demands on when `self.retry`, `self.wait`, and `self.stop` are called relative to when `after` and `before_sleep` fire.

This conflict would not be visible from either improvement alone: Improvement 1 accepts dynamic assembly and therefore doesn't encounter the tension between inspectability and timing. Improvement 2 accepts the timing change and therefore doesn't encounter the tension between inspectability and preserving windows. Only by recognizing that both improvements are addressing real, independent problems does the conflict emerge: the two real problems cannot both be solved simultaneously.

---

### The Third Improvement That Resolves the Conflict

Introduce `StrategyEvaluation` as an immutable record of strategy results, stored in `retry_state` where it is observable by all callbacks through the existing interface:

```python
@dataclasses.dataclass(frozen=True)
class StrategyEvaluation:
    """Immutable record of strategy evaluations for one retry iteration.

    Stored as retry_state.last_evaluation before any callbacks fire.
    Callbacks can read evaluation results without the results needing to
    be encoded in retry_state's primary fields.

    Attributes:
        should_retry: whether retry strategy decided to retry
        should_stop: whether stop strategy decided to stop (None if unevaluated)
        planned_sleep: wait strategy result in seconds (None if unevaluated)
        is_explicit_retry: whether TryAgain was raised directly
    """
    should_retry: bool
    should_stop: bool | None
    planned_sleep: float | None
    is_explicit_retry: bool


# In RetryCallState.__init__:
self.last_evaluation: StrategyEvaluation | None = None

# In RetryCallState.prepare_for_next_attempt:
self.last_evaluation = None  # reset with per-attempt state


class BaseRetrying:
    def iter(self, retry_state):
        self.iter_state.reset()
        fut = retry_state.outcome

        if fut is None:
            if self.before is not None:
                self.before(retry_state)
            return DoAttempt()

        is_explicit_retry = fut.failed and isinstance(fut.exception(), TryAgain)

        # Phase 1: evaluate all strategies, produce immutable record
        should_retry = is_explicit_retry or bool(self.retry(retry_state))

        if not should_retry:
            retry_state.last_evaluation = StrategyEvaluation(
                should_retry=False, should_stop=None,
                planned_sleep=None, is_explicit_retry=is_explicit_retry
            )
            return retry_state.outcome.result()

        sleep = self.wait(retry_state) if self.wait else 0.0
        self.statistics["delay_since_first_attempt"] = retry_state.seconds_since_start
        should_stop = bool(self.stop(retry_state))

        retry_state.last_evaluation = StrategyEvaluation(
            should_retry=True, should_stop=should_stop,
            planned_sleep=sleep, is_explicit_retry=is_explicit_retry
        )

        # Phase 2: observability callbacks with full evaluation context available
        if self.after is not None:
            self.after(retry_state)  # retry_state.last_evaluation.should_stop now accessible

        if should_stop:
            if self.retry_error_callback:
                return self.retry_error_callback(retry_state)
            retry_exc = self.retry_error_cls(fut)
            if self.reraise:
                retry_exc.reraise()
            raise retry_exc from fut.exception()

        retry_state.upcoming_sleep = sleep
        retry_state.next_action = RetryAction(sleep)
        retry_state.idle_for += sleep
        self.statistics["idle_for"] += sleep
        self.statistics["attempt_number"] += 1

        if self.before_sleep is not None:
            self.before_sleep(retry_state)

        return DoSleep(sleep)
```

This satisfies both conflicting requirements: strategies are evaluated before callbacks fire (Improvement 2's goal — the plan is determined before `after` runs); evaluation results are observable to all callbacks via `retry_state.last_evaluation` through the existing `retry_state` interface (Improvement 1's goal — observation windows have explicit content). `IterState` is reduced to a reset flag and `is_explicit_retry`. The routing nodes, the work queue, and the for loop over `iter_state.actions` are eliminated. The execution is explicit, sequential, and readable.

---

### How the Third Improvement Fails

`after` now fires after `should_stop` is evaluated. In the original, `after` fires before `stop` is evaluated. This is a deliberate behavioral change — `after` can now read `retry_state.last_evaluation.should_stop`. But it silently breaks callbacks that were designed to **influence** stop decisions by mutating `retry_state` before `stop` evaluates.

Concretely: a callback `after=my_circuit_breaker` that writes to `retry_state.retry_object`'s internal state — expecting a custom `stop` strategy to read that state when it evaluates — will stop having any effect. `stop` has already been called. The mutation arrives after the decision has been made. No error is raised. The retry behavior changes without any diagnostic signal.

This is not a theoretical failure. The `after` callback receives a mutable `retry_state`. Custom stop strategies receive the same mutable `retry_state`. In the original architecture, `after` runs before `stop` evaluates — any mutation `after` makes to `retry_state` or to objects reachable through it affects the stop evaluation. The third improvement terminates this influence pathway. The improvement is externally indistinguishable from the original until a callback that was using this pathway stops working.

---

### What the Failure Reveals About the Design Space

The structural conflict appeared to be about temporal ordering: when do callbacks fire relative to strategy evaluations? The third improvement's failure reveals that this framing is incomplete.

The real question is not when callbacks fire — it is **whether callbacks can influence strategy outcomes by mutating `retry_state`**. The callback interface is `(retry_state) -> None`, where `retry_state` is mutable and is also passed to strategy callables. This makes callbacks and strategies co-tenants of the same mutable object. Any callback that fires before a strategy can influence that strategy's outcome. Any callback that fires after a strategy cannot. The "observation window" is simultaneously an "influence window."

The design space is two-dimensional:
- **Axis 1**: when do callbacks fire relative to strategy evaluations? (the dimension L9's conflict and both improvements optimize along)
- **Axis 2**: can callbacks mutate `retry_state` in ways that affect subsequent strategy evaluations? (the dimension the third improvement's failure reveals)

The conflict between Improvements 1 and 2 is on Axis 1 alone: Improvement 1 preserves current timing; Improvement 2 changes it. The conflict looked resolvable within Axis 1 by finding a timing that satisfies both requirements.

The third improvement's failure reveals that Axis 1 and Axis 2 are coupled through the mutable `retry_state` reference. Moving callbacks after all strategy evaluations (the resolution) removes influence capability from callbacks entirely. Keeping callbacks interleaved with evaluations (the original) preserves influence capability but makes the timing windows invisible and the influence pathways undocumented. There is no position on Axis 1 that gives inspectable timing AND preserves influence — because preserving influence requires that callbacks fire before some strategy evaluates, which requires the timing to be interleaved, which requires the work queue, which is what makes the timing invisible.

**The conflict between ephemeral evaluation and observable state (L9's finding) was a conflict about storage models for decision results**. The failure of the third improvement reveals a deeper and irresolvable conflict: the `(retry_state) -> None` interface for callbacks is the same mutable-object interface used to pass state to strategy callables. Observation and influence share one channel, with no architectural distinction between a callback that reads and one that writes to affect a subsequent strategy. The design space does not contain a solution that simultaneously makes observation windows explicit AND allows callbacks to influence strategies through `retry_state` — because those two requirements demand incompatible positions on Axis 2 with respect to the same mutable object.

L9 found that the callback interface cannot receive evaluation results. The third improvement reveals why: any solution that adds evaluation results to `retry_state` — the only channel available to callbacks — also makes those results mutable by the callbacks. And making evaluation results mutable by callbacks means callbacks can retroactively affect decisions that have already been made, or that the immutability of `StrategyEvaluation` is false (it would need to be re-evaluated after callbacks run). The `frozen=True` on `StrategyEvaluation` is not a choice; it is the only option that prevents callbacks from corrupting evaluation results they are supposed to observe. But `frozen=True` doesn't prevent callbacks from mutating `retry_state`'s other fields — the fields that strategies read. The immutability constraint on the record doesn't close the influence pathway through the object.

The architecture's deepest structural property — now visible — is that it chose a single mutable object (`retry_state`) as the communication substrate for everything: strategy inputs, strategy outputs, callback observations, callback influences, and the per-attempt record. Every structural problem in the codebase traces to this choice. The Pipeline Simulacrum (L9), the IterState side channel (L9), the observation window (L10), and the influence/observation conflation (L10) are all symptoms of the same root: a design that made all communication uniform by making it all mutable-object mutation, and then discovered that uniformity prohibits the distinctions the architecture actually needs.
