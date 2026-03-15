## Structure First: Level 10 Diagnostic

---

### Falsifiable Claim

> The `for action in self.iter_state.actions:` loop in `iter()` processes items appended to `self.iter_state.actions` during iteration. This is not incidental: `_post_retry_check_actions` and `_post_stop_check_actions` are actions that append further actions mid-loop. Each reads IterState fields set by the immediately preceding action. `_post_retry_check_actions` reads `self.iter_state.retry_run_result`, which was set by `_run_retry` — the action appended one position earlier in `_begin_iter`. The only enforcement that `_run_retry` executes before `_post_retry_check_actions` is their append order. This is a **read-after-write dependency encoded as list position**, with no type, no assertion, no documentation. The failure mode is precisely silent: `reset()` initializes `retry_run_result = False` — the same value the retry strategy can legitimately return. If `_post_retry_check_actions` ran before `_run_retry` for any reason, it would read `False` (the reset default) and conclude "no retry needed." No exception, no wrong branch — the correct-looking success path runs. The retry strategy is bypassed with no observable signal.

Falsifiable test: in `_begin_iter`, reverse the append order — put `_post_retry_check_actions` before `_run_retry`. Run against a strategy that always retries. The first exception is swallowed as a success.

---

### The Dialectic

**Expert 1 — Defender**

The claim correctly identifies the execution model. The three scheduler methods form a continuation-passing chain through list mutation: `_post_retry_check_actions` doesn't just read IterState — it expands the action list based on IterState, adding work that executes in the *same loop pass*. This is a trampoline implemented through Python's list-append-during-iteration behavior. The read-after-write dependency is real, and its silent failure mode is exact: `retry_run_result = False` after `reset()` is observationally identical to `_run_retry` returning `False`. The "not yet set" state and the "set to the default value" state are indistinguishable to the reader. The concealment is total by structural coincidence.

**Expert 2 — Attacker**

The claim describes a vulnerability in hypothetical extension code, not a defect in existing code. The existing append sequences are correct. A developer implementing a new scheduler action would see `_begin_iter` and understand the pattern. `retry_run_result` is named after its writer — `_run_retry` — and the field name makes the dependency legible. No developer reverses this ordering by accident. The claim overstates by treating a convention as a hazard.

**Expert 3 — Prober**

Expert 2 argues the dependency is "legible." The prober's question is not about existing code or hypothetical misuse — it is: *why does `_post_retry_check_actions` read `self.iter_state.retry_run_result` rather than receiving `_run_retry`'s return value as an argument?*

Because `_run_retry` is called from within `for action in self.iter_state.actions: result = action(retry_state)`. Its return value is written to `result`. `result` is overwritten by the next action. There is **no mechanism in the loop to thread return values between consecutive actions**. Each action's return value is discarded before the next action runs. IterState fields are not a design choice for inter-action communication — they are the *only channel available* given the loop structure. If you wanted `_post_retry_check_actions` to receive `_run_retry`'s output as a parameter, you would need to change the loop. The loop structure makes shared mutable state mandatory, not optional.

Expert 2's "just name the fields well" prescription addresses the legibility of the channel, not its necessity.

---

### The Transformation

| | |
|---|---|
| **Initial claim** | Append order is the only enforcement of read-after-write dependencies between actions; reordering silently breaks retry |
| **Transformed claim** | The loop discards each action's return value before calling the next. IterState fields are not a communication design choice — they are the only communication channel the loop architecture permits. The read-after-write dependency is invisible as a constraint because it has no representation in the code that enforces it, only in the code that obeys it. The ordering convention is the dependency itself. |

These are epistemically different. The initial claim is about a fragile convention. The transformed claim is about structural necessity: the loop eliminates the alternative, so the convention is not a convention but a constraint expressed in the only available encoding.

---

### The Gap Is Itself Diagnostic

L9 performed sophisticated analysis of `iter_state.actions` — identifying terminal vs scheduler action distinctions, noting that `result` is overwritten, observing that `_run_retry`/`_run_wait`/`_run_stop`/`_post_retry_check_actions`/`_post_stop_check_actions` all return `None`. But L9 treated all of these as members of the same class ("scheduler actions, their purpose is to append to iter_state.actions and return"). They are not the same class. `_run_retry`, `_run_wait`, `_run_stop` do not append to `iter_state.actions` — they write to `iter_state` fields. `_post_retry_check_actions` and `_post_stop_check_actions` do append — and they read the fields the former group wrote. There are two distinct roles: **state-setters** and **continuation-appenders**. The continuation-appenders depend on the state-setters having already run. L9 saw both groups but did not distinguish them, and so could not see the read-after-write dependency between them.

The gap: L9 analyzed what the actions *do*. It did not ask what they *read from each other*.

---

### The Concealment Mechanism: Ordering as Invisible Contract

When a read-after-write dependency between two operations is expressed only as their sequential position in a list, the dependency becomes invisible to every analysis tool that treats position as incidental rather than semantic. Type checkers do not check that `_run_retry` executes before `_post_retry_check_actions`. Linters do not check that `retry_run_result` is populated before it is read. Code review sees `_begin_iter` append two functions in sequence and reads this as natural ordering, not as a contract.

The default value of `retry_run_result = False` completes the concealment. `reset()` initializes this field to `False`. `self.retry(retry_state)` can return `False`. `_post_retry_check_actions` reads the field and cannot distinguish "writer ran and returned False" from "writer has not yet run." The sentinel for "unset" and the value for "retry not needed" are the same. Any future action that reads this field before its writer runs will silently receive the same answer as the "no retry needed" case.

**Application across all IterState fields:**

- `retry_run_result = False`: reset default ≡ "retry not needed"
- `stop_run_result = False`: reset default ≡ "don't stop"
- `is_explicit_retry = False`: reset default ≡ "not a TryAgain"

All three fields fail identically: premature read returns the false-negative default with no distinguishable signal. The concealment is not a property of any individual field — it is a property of the pattern: using falsy initialization values as both the default sentinel and the meaningful "negative result." The pattern makes the dependency contract invisible by making its violation indistinguishable from its satisfaction with a specific input.

---

### Engineering the Improvement

Replace `IterState` with an `IterContext` passed as an explicit parameter, created fresh per `iter()` call, using `Optional[bool]` to distinguish "not yet evaluated" from `False`. Convert the for-loop to a while-loop to make the dynamic extension explicit:

```python
import dataclasses
from typing import Optional

@dataclasses.dataclass
class IterContext:
    """Execution context for a single iter() call. Created per-call; not reused.
    
    Fields transition from None (stage not yet run) to a typed result as
    pipeline stages execute. A None value explicitly indicates the corresponding
    stage has not yet produced output — distinct from False.
    """
    actions: list = dataclasses.field(default_factory=list)
    retry_needed: Optional[bool] = None   # Written by _run_retry; None = retry not yet evaluated
    stop_needed: Optional[bool] = None    # Written by _run_stop; None = stop not yet evaluated
    is_explicit_retry: bool = False       # Written by _begin_iter before any action runs


class BaseRetrying(ABC):
    # iter_state property removed: IterContext is now local to iter()

    def iter(self, retry_state: "RetryCallState") -> object:
        ctx = IterContext()
        self._begin_iter(retry_state, ctx)
        result = None
        idx = 0
        while idx < len(ctx.actions):
            result = ctx.actions[idx](retry_state)
            idx += 1
        return result

    def _begin_iter(self, retry_state: "RetryCallState", ctx: IterContext) -> None:
        fut = retry_state.outcome
        if fut is None:
            if self.before is not None:
                ctx.actions.append(self.before)
            ctx.actions.append(lambda rs: DoAttempt())
            return
        ctx.is_explicit_retry = fut.failed and isinstance(fut.exception(), TryAgain)
        if not ctx.is_explicit_retry:
            ctx.actions.append(lambda rs: self._run_retry(rs, ctx))
        ctx.actions.append(lambda rs: self._post_retry_check_actions(rs, ctx))

    def _run_retry(self, retry_state: "RetryCallState", ctx: IterContext) -> None:
        ctx.retry_needed = self.retry(retry_state)

    def _run_wait(self, retry_state: "RetryCallState") -> None:
        retry_state.upcoming_sleep = self.wait(retry_state) if self.wait else 0.0

    def _run_stop(self, retry_state: "RetryCallState", ctx: IterContext) -> None:
        self.statistics["delay_since_first_attempt"] = retry_state.seconds_since_start
        ctx.stop_needed = self.stop(retry_state)

    def _post_retry_check_actions(self, retry_state: "RetryCallState", ctx: IterContext) -> None:
        if not (ctx.is_explicit_retry or ctx.retry_needed):
            ctx.actions.append(lambda rs: rs.outcome.result())
            return
        if self.after is not None:
            ctx.actions.append(self.after)
        ctx.actions.append(self._run_wait)
        ctx.actions.append(lambda rs: self._run_stop(rs, ctx))
        ctx.actions.append(lambda rs: self._post_stop_check_actions(rs, ctx))

    def _post_stop_check_actions(self, retry_state: "RetryCallState", ctx: IterContext) -> None:
        if ctx.stop_needed:
            if self.retry_error_callback:
                ctx.actions.append(self.retry_error_callback)
                return
            def exc_check(rs):
                fut = rs.outcome
                retry_exc = self.retry_error_cls(fut)
                if self.reraise:
                    retry_exc.reraise()
                raise retry_exc from fut.exception()
            ctx.actions.append(exc_check)
            return
        def next_action(rs):
            sleep = rs.upcoming_sleep
            rs.next_action = RetryAction(sleep)
            rs.idle_for += sleep
            self.statistics["idle_for"] += sleep
            self.statistics["attempt_number"] += 1
        ctx.actions.append(next_action)
        if self.before_sleep is not None:
            ctx.actions.append(self.before_sleep)
        ctx.actions.append(lambda rs: DoSleep(rs.upcoming_sleep))
```

This passes code review because: `Optional[bool]` correctly distinguishes "not yet evaluated" from `False` — a genuine semantic improvement. Fresh `IterContext` per call eliminates `reset()` and the thread-local property. Explicit `ctx` parameter makes the dependency visible in signatures. `while idx < len(ctx.actions)` documents the dynamic extension as intentional. Removing `self.iter_state` removes unusual thread-local lifetime semantics. `_add_action_func` is eliminated — direct `ctx.actions.append` is cleaner.

It deepens concealment because: The closures `lambda rs: self._run_retry(rs, ctx)` capture `ctx` by reference. The mechanism is identical to `self.iter_state` — a shared mutable object written by some closures and read by others — but now expressed as a modern closure pattern rather than a thread-local property. The while-loop makes dynamic extension look intentional and eliminates the only design-level question the for-loop raised. `Optional[bool]` looks like it fixed the sentinel ambiguity — it fixed the `False` case while leaving `None` as a falsy sentinel for a new class of premature-read failures (see below). The removal of `self.iter_state` eliminates the last external signal that this object has unusual semantics.

---

### Three Properties Visible Only Because We Tried to Strengthen

**1. `ctx.actions` and the closures it contains form a reference cycle.**

`_begin_iter` appends `lambda rs: self._run_retry(rs, ctx)` to `ctx.actions`. This closure captures `ctx`. `ctx.actions` is a field of `ctx`. Therefore: `ctx` → `ctx.actions[i]` → closure → `ctx`. This is a reference cycle. In the original code, `self.iter_state` is accessed through `self` — no closure captures it, no cycle forms. The improvement, by making `ctx` a closure capture rather than a `self` attribute, creates the cycle. After `iter()` returns and `ctx` goes out of scope as a local variable, CPython's reference counter alone cannot collect it. The cycle-breaker (cyclic garbage collector) will eventually collect it — but only after a GC cycle, not immediately. In high-frequency retry scenarios, `iter()` is called in a tight loop, creating a new reference-cycled `IterContext` on each call. The original's thread-local `IterState` is one object for the thread's lifetime, mutated in place; the improvement's per-call `IterContext` creates N objects per N retries, each with a cycle, none promptly collected. The property — that closure capture creates reference cycles with the captured context — is visible only because the improvement introduced closure capture as the communication mechanism.

**2. `_run_wait` communicates through `retry_state`, not `ctx`, exposing a communication asymmetry the original concealed.**

`_run_retry` writes `ctx.retry_needed`. `_run_stop` writes `ctx.stop_needed`. But `_run_wait` writes `retry_state.upcoming_sleep`. The result of wait evaluation flows forward through `retry_state`, not through `ctx`. The downstream consumer of this value — the `next_action` closure — reads `rs.upcoming_sleep` from `retry_state`. Making `ctx` an explicit parameter reveals that wait has a different communication pattern from retry and stop: one communicates through the pipeline context, two communicate through the request state. In the original, both `self.iter_state` and `self.retry_state` are accessed through `self` in method bodies, making them appear equivalent as "object state." The improvement's explicit `ctx` parameter makes the asymmetry visible: some methods take `(retry_state, ctx)`, `_run_wait` takes only `(retry_state)`. The missing `ctx` parameter on `_run_wait` is now a legible signal of its different communication channel — a signal that was invisible when everything went through `self`.

**3. Eliminating `_add_action_func` reveals it was a false abstraction boundary.**

The original `_add_action_func` is a one-line wrapper: `self.iter_state.actions.append(fn)`. Its name implies abstraction — that "adding an action function" is a meaningful operation distinct from list appending, that the method could someday validate actions, enforce ordering, or track provenance. None of this is implemented. The method does nothing beyond delegation. Removing it in the improvement — replacing every call with `ctx.actions.append(...)` directly — produces simpler code with identical behavior. But the removal reveals what the method's presence implied: a design aspiration (encapsulate the action list behind an interface) that was never realized. The name `_add_action_func` was documentation of intent without implementation. Code review that sees `_add_action_func` infers there is something non-trivial about adding actions. Code review that sees `ctx.actions.append` infers there is nothing non-trivial. The aspiration was concealing the directness of the coupling. The property — that the action list is always accessed directly, with no validation, ordering check, or type enforcement — is visible only because the improvement collapsed the false abstraction.

---

### Applying the Diagnostic to the Improvement

**What does the improvement conceal?**

The `Optional[bool]` fix addresses the `False` ambiguity but installs `None` as a new falsy sentinel. In `_post_retry_check_actions`:

```python
if not (ctx.is_explicit_retry or ctx.retry_needed):
```

If `_post_retry_check_actions` runs before `_run_retry` sets `ctx.retry_needed`, it reads `None`. `not (False or None)` evaluates to `True` — the "no retry needed" branch executes. The failure mode is identical to the original: premature read of `retry_needed` silently returns the negative result. The improvement renamed the sentinel from `False` to `None` while preserving silent failure under premature reads. `None` is falsy; the fix was cosmetic for this case.

The improvement also conceals the extent of the coupling. Making `ctx` an explicit parameter to `_begin_iter`, `_run_retry`, `_run_stop`, `_post_retry_check_actions`, `_post_stop_check_actions` makes the coupling look like proper dependency injection. But all five methods receive the *same* `ctx` object and share it through mutation. Dependency injection conventionally provides *data* to functions; here it provides a *shared mutation target*. The explicit parameter makes the coupling look clean while the coupling is as tight as before.

**What property of the original problem is visible only because the improvement recreates it?**

The improvement's closures — `lambda rs: self._run_retry(rs, ctx)`, `lambda rs: self._post_retry_check_actions(rs, ctx)` — each capture `ctx` and mutate it. When `_run_retry`'s closure executes at `idx=0`, it sets `ctx.retry_needed`. When `_post_retry_check_actions`'s closure executes at `idx=1`, it reads `ctx.retry_needed` and appends more closures to `ctx.actions`. All of these closures capture the same `ctx` reference. The improvement has recreated the original coupling, now visible: **every scheduled action in the pipeline shares mutable access to the pipeline's coordination object through closure capture**. In the original, this was expressed as "methods access `self.iter_state` through `self`" — invisible because all methods access everything through `self`. The improvement makes the sharing explicit in the closure signatures. The property — that inter-action communication requires all actions to share a mutable reference — is now legible as a structural fact rather than an implementation detail.

---

### Engineering the Second Improvement

The recreated property: actions share a mutable `ctx` through closure capture, with ordering as the only dependency enforcement. The second improvement addresses this by making inter-action communication explicit through return values — replacing the flat mutable-context action list with a typed pipeline that threads outputs forward:

```python
from typing import NamedTuple, Optional, Union

class RetryEvaluation(NamedTuple):
    should_retry: bool
    is_explicit: bool

class WaitResult(NamedTuple):
    sleep_duration: float
    retry_evaluation: RetryEvaluation  # Carries forward the upstream decision

class StopEvaluation(NamedTuple):
    should_stop: bool
    wait_result: WaitResult            # Carries forward the upstream chain

class AttemptOutcome(NamedTuple):
    value: object                      # Terminal: the successful result

PipelineValue = Union[
    None,                              # Before any stage
    RetryEvaluation,
    WaitResult,
    StopEvaluation,
    AttemptOutcome,
    DoAttempt,
    DoSleep,
]

def _build_pipeline(self, retry_state: "RetryCallState") -> list[Callable]:
    """Build the ordered pipeline for this iteration. Stages receive the prior stage's output."""
    fut = retry_state.outcome
    if fut is None:
        stages = []
        if self.before is not None:
            stages.append(lambda rs, prev: (self.before(rs), DoAttempt())[1])
        stages.append(lambda rs, prev: DoAttempt())
        return stages
    is_explicit = fut.failed and isinstance(fut.exception(), TryAgain)
    if not is_explicit:
        stages = [
            lambda rs, prev: RetryEvaluation(self.retry(rs), is_explicit=False),
        ]
    else:
        stages = [
            lambda rs, prev: RetryEvaluation(should_retry=True, is_explicit=True),
        ]
    stages.append(lambda rs, prev: self._route_retry(rs, prev))
    return stages

def iter(self, retry_state: "RetryCallState") -> object:
    pipeline = self._build_pipeline(retry_state)
    prev: PipelineValue = None
    idx = 0
    while idx < len(pipeline):
        prev = pipeline[idx](retry_state, prev)
        if isinstance(prev, (DoAttempt, DoSleep)):
            return prev           # Terminal: caller handles these
        idx += 1
    if isinstance(prev, AttemptOutcome):
        return prev.value
    return prev
```

This passes code review because: each stage receives the prior stage's typed output — the dependency is explicit in the type signature. `RetryEvaluation` → `WaitResult` → `StopEvaluation` creates a visible chain. No shared mutable context object. No field-naming conventions to enforce. `Union[...]` documents what can flow through the pipeline. `isinstance(prev, (DoAttempt, DoSleep))` provides early exit for terminal stages.

**Applying the diagnostic to the second improvement:**

`_build_pipeline` must decide which stages to include — but the decision depends on `fut` (whether the previous attempt has completed), which is available before the pipeline runs. Good. But `_route_retry` — the stage that decides "retry path or success path" — reads the prior stage's `RetryEvaluation` and must return either: the success result (which requires calling `rs.outcome.result()`) or a `WaitResult` (which requires evaluating `self.wait`). If it returns the success result, the pipeline terminates. If it returns `WaitResult`, the pipeline continues with stop evaluation. The pipeline's length after `_build_pipeline` is therefore incomplete: `_build_pipeline` doesn't know whether to include the wait/stop stages because that depends on `RetryEvaluation.should_retry`, which isn't available until the `RetryEvaluation` stage runs. The improvement has recreated the dynamic extension: `_route_retry` must either dynamically add stages to the pipeline (recreating the original mechanism) or contain the entire conditional subtree inline (eliminating the pipeline abstraction for the retry path). The typed return values moved the coordination problem from IterState fields to the pipeline's shape itself.

More precisely: the second improvement must choose between (a) building the complete pipeline before running it — impossible without executing some stages first — or (b) growing the pipeline during execution — which is the original mechanism, now with typed outputs rather than IterState fields. Option (b) recreates the original at higher abstraction. The original property that forced this choice — **that retry decisions are conditional on their own prior outputs, so the decision sequence cannot be fully determined before execution begins** — is now visible in the typed pipeline's incompleteness.

Additionally: the improvement's `isinstance(prev, (DoAttempt, DoSleep))` early-exit reveals the exception-as-terminal-action problem. The original's `exc_check` action terminates the pipeline by raising — the exception propagates out of the while-loop naturally. The typed pipeline has no equivalent: `exc_check` cannot return a `StopEvaluation` that the loop knows to treat as "raise." It must either raise (bypassing the typed protocol) or return a sentinel type (`ErrorTerminal`) that the loop must then re-raise. Either way, exceptions are terminal actions that cannot be uniformly expressed as values in the typed pipeline. The typed pipeline resolves the shared-mutable-state problem while exposing that exception semantics are outside its protocol.

---

### The Structural Invariant

Through every improvement — IterContext as explicit parameter, while-loop with index, Optional[bool] sentinels, typed PipelineValue chain, NamedTuple result threading — one property persists, unmodified in form or necessity:

**The retry pipeline requires sequential conditional decisions (retry?, how long?, stop?) where each decision gates whether subsequent decisions should run at all. The gating is data-dependent: "evaluate stop only if retry is needed" requires knowing whether retry is needed, which requires executing the retry evaluation stage. No pipeline whose shape is fully determined before execution can express this — the shape of the pipeline is itself a function of its own execution. Therefore, the pipeline must either: share intermediate decision results through a mutable container that later stages read (IterState, IterContext), or grow during execution based on intermediate results (dynamic list extension). Both options require a mechanism that is invisible as a constraint in individual stage signatures — the mutable container hides the ordering dependency in field access patterns; the dynamic extension hides the branching logic in append sequences. No improvement within the action-list architecture eliminates this choice because the choice is not architectural — it is a consequence of the computation's structure. Sequential conditional decisions with data-dependent branching cannot be linearized without some form of inter-stage communication that must be established before the pipeline's full extent is known.**

The invariant is not IterState, nor the for-loop, nor append ordering, nor closure capture, nor typed outputs. The invariant is: **the computation requires communicating intermediate decisions to stages that cannot be scheduled without them.** Every implementation encodes this communication in some medium — shared fields, closure references, pipeline values. The medium's form determines what is visible and what is concealed. The necessity of the medium is not a design choice. It is a property of the problem space, irreducible through any improvement that remains a retry pipeline.
