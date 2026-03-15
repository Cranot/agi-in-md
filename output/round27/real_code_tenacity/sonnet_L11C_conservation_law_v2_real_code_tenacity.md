## Initial Claim

**Specific, falsifiable claim:** The deepest structural problem is that `IterState.actions` is a list that is mutated *during its own iteration* by functions that are themselves members of that list. `_post_retry_check_actions` and `_post_stop_check_actions` are not actions — they are *planners* that append future actions to the queue currently being consumed by `iter()`'s `for` loop. Python's index-based list iterator makes this accidentally safe, but it means the control flow graph of a single retry iteration is unknowable until execution completes. The "state machine" is a self-modifying instruction tape.

---

## Three-Expert Dialectic

**Expert A (defends):** The claim is correct and testable. Run `iter()` under a debugger and inspect `iter_state.actions` before and after calling `_post_retry_check_actions`. The list grows during the `for` loop. No static analysis tool can tell you what actions will execute for a given configuration without simulating execution. That's the definition of an opaque control flow graph.

**Expert B (attacks):** The claim misidentifies the pattern. Appending to a list during iteration is a well-understood trampolining idiom — it's CPS (continuation-passing style) without the recursion. The real problem isn't control-flow opacity; it's that the trampolined closures all close over `self` (the `BaseRetrying` instance), and `self` accesses `self._local` (a `threading.local`). The threading correctness of the entire system depends on closures being created and consumed on the same thread — which holds for `Retrying.__call__` but becomes fragile the moment anyone stores a closure reference across a thread boundary.

**Expert C (probes what both assume):** Both experts take for granted that `iter_state` is the *primary* state container. But look at `wraps()`:

```python
copy = self.copy()
wrapped_f.statistics = copy.statistics   # function attribute → copy's dict
self._local.statistics = copy.statistics  # original's thread-local → same dict
return copy(f, *args, **kw)
```

`copy.statistics` is a plain `dict`. Both `wrapped_f.statistics` and `self._local.statistics` now point to the *same dictionary object*. Statistics are shared between the original and the copy by *reference aliasing*, not by thread-local isolation. A and B argued about control flow. Neither noticed that statistics accumulation leaks across what should be isolated call contexts.

**The transformation:** The claim shifts from "self-modifying action queue = confusing control flow" to: **The real problem is that per-call state (statistics, action plan) is stored in structures whose lifetimes are ambiguous — they are simultaneously per-instance, per-thread, and per-call, depending on which code path is taken.** The action queue pattern is the visible mechanism; the aliased mutable state is the invisible consequence.

---

## Concealment Mechanism Named

**Mechanism: Strategy-pattern camouflage.** The public interface consists of beautifully composable strategy objects: `stop`, `wait`, `retry`, `before`, `after`. These look like pure data — a configuration. The actual control flow assembly is invisible: it is performed by `_begin_iter`, `_post_retry_check_actions`, and `_post_stop_check_actions`, which are named as if they *check* things but actually *schedule* things. The names describe the trigger condition, not the action taken. The documentation pattern is "what calls this" not "what this does."

**Applied:** The method `_post_retry_check_actions` does not "post-check retry." It decides whether to schedule `_run_wait`, `_run_stop`, and `_post_stop_check_actions`. Its name is a past-tense condition; its behavior is future-tense planning. This naming convention makes the self-modifying queue look like a clean pipeline of checks, concealing that the pipeline itself is being assembled mid-execution.

---

## Improvement That Deepens Concealment

This passes code review. It is a legitimate improvement:

```python
@dataclasses.dataclass(slots=True)
class IterState:
    actions: list[Callable] = dataclasses.field(default_factory=list)
    retry_run_result: bool = False
    stop_run_result: bool = False
    is_explicit_retry: bool = False

    def reset(self) -> None:
        self.actions.clear()          # more efficient than rebinding
        self.retry_run_result = False
        self.stop_run_result = False
        self.is_explicit_retry = False

    def schedule(self, action: Callable[[RetryCallState], Any]) -> None:
        """Schedule an action for execution in the current retry iteration."""
        self.actions.append(action)

    def schedule_chain(self, *actions: Callable[[RetryCallState], Any]) -> None:
        """Schedule a sequence of actions for execution in the current retry iteration."""
        self.actions.extend(actions)
```

Then replace all `self._add_action_func(fn)` calls with `self.iter_state.schedule(fn)`, and replace multi-append sequences with `self.iter_state.schedule_chain(fn1, fn2, fn3)`.

**Why it passes review:** Removes the awkward `_add_action_func` indirection. Adds type annotations. Uses `.clear()` correctly. The method name `schedule` is accurate and professional. It signals intentional design.

**Why it deepens concealment:** By naming the operation `schedule`, we've declared that mid-iteration mutation is a first-class design decision, not an accident. The concealment is now load-bearing — it's in the API contract.

---

## Three Properties Visible Only Because of the Strengthening Attempt

**1. Planning actions and leaf actions are fundamentally different types mixed in the same list.** `schedule_chain` lets you see that `_post_retry_check_actions` schedules 3-4 continuations while `self.before` schedules 0 additional items (it just executes). The `list[Callable]` type annotation papers over a distinction that matters: some callables are *terminal* (return data, cause DoAttempt/DoSleep) and some are *structural* (return None, mutate the queue). These should have different types.

**2. `.clear()` vs. `= []` exposes object identity assumptions.** The original `self.actions = []` creates a new list object each reset, severing any external references to the old list. `.clear()` mutates the existing object — any reference held elsewhere (a debugger watch, an introspection hook, a future subclass) would see a list that disappears. The original code implicitly assumed no one holds the actions list. Making it a property of `IterState` with a named method makes that assumption structural — and now you can see it's an assumption that could be violated.

**3. `schedule_chain` cannot be called atomically from a planning action.** When `_post_stop_check_actions` calls `schedule_chain(next_action, self.before_sleep, lambda rs: DoSleep(...))`, the three actions appear in the list in insertion order. But `before_sleep` may be `None`, requiring an `if` guard before `schedule_chain`. The original code's individual `_add_action_func` calls with guards were doing something that `schedule_chain` cannot — conditional chain assembly. The improvement forces you to either add None filtering inside `schedule_chain` or break the "chain" into guarded individuals, revealing that the action sequence has conditional holes that the original code handled implicitly.

---

## Diagnostic Applied to the Improvement

**What the improvement conceals:** `schedule()` sounds like there is a scheduler — an entity with authority over what executes next. There is no scheduler. `schedule()` is `list.append`. The naming elevates a data structure operation to an architectural concept, hiding that the "scheduling authority" and the "execution queue" are the same object.

**What property of the original problem is visible because the improvement recreates it:**

The improvement forces `_post_retry_check_actions` to be a method on `BaseRetrying` (not `IterState`), because it needs to access `self.wait`, `self.stop`, `self.after`, etc. So the planning functions still live on the retry object, not on the state object. The `schedule()` method on `IterState` is called BY methods ON `BaseRetrying`. The direction of control is:

```
BaseRetrying.iter_state.schedule(BaseRetrying._run_stop)
```

This recreates and makes visible: **the planning functions must close over the retry configuration, but they mutate the iteration state. These are two different ownership domains — configuration and ephemeral state — that the original design conflates inside `BaseRetrying`.** The improvement almost separates them (state on `IterState`, planning on `BaseRetrying`) but the planning functions still reach into `iter_state` via `self.iter_state`, which goes through `threading.local()`. The separation is incomplete and the thread-local access is the load-bearing coupling.

---

## Second Improvement

Make the coupling explicit by passing `schedule` as a parameter, eliminating the implicit `self.iter_state` access from planning functions:

```python
def iter(self, retry_state: RetryCallState) -> Any:
    self.iter_state.reset()
    schedule = self.iter_state.schedule          # captured once, at iter start
    self._build_action_plan(retry_state, schedule)
    result = None
    for action in self.iter_state.actions:      # now actions is fully built
        result = action(retry_state)
    return result

def _build_action_plan(
    self,
    retry_state: RetryCallState,
    schedule: Callable[[Callable], None],
) -> None:
    fut = retry_state.outcome
    if fut is None:
        if self.before is not None:
            schedule(self.before)
        schedule(lambda rs: DoAttempt())
        return
    is_explicit_retry = fut.failed and isinstance(fut.exception(), TryAgain)
    if not is_explicit_retry:
        schedule(self._run_retry)
    schedule(lambda rs: self._continue_plan(rs, schedule))

def _continue_plan(
    self,
    retry_state: RetryCallState,
    schedule: Callable[[Callable], None],
) -> None:
    # ... same logic as _post_retry_check_actions, but schedule is explicit
```

**Why this seems better:** `schedule` is now an explicit dependency. Planning functions don't implicitly reach into `self.iter_state`. Thread safety is clearer — `schedule` is a closure over `iter_state.actions`, captured once per `iter()` call.

**Diagnostic applied to the second improvement:**

It conceals: `schedule` is still `list.append`. We've given a parameter name to an operation that is definitionally append-to-the-currently-iterating-list. The parameter makes it look like the caller could substitute a different scheduler (a priority queue? a filtered scheduler?). It cannot — the `for action in self.iter_state.actions` loop is hardcoded in `iter()`.

What property is visible because the second improvement recreates it: `_continue_plan` is called from within the `for action in self.iter_state.actions` loop (it's an action that schedules more actions), and it receives `schedule` — which is `iter_state.actions.append` — as a parameter. **The improvement clarifies that the "schedule" function is semantically identical to the call stack's "push next frame" operation.** The actions list IS a call stack. `_continue_plan` is not scheduling work for later; it is pushing continuation frames. The second improvement, by making `schedule` explicit, reveals that what Tenacity calls "actions" are actually trampolined continuations — not a queue of discrete work items.

---

## The Structural Invariant

**Through every improvement, this property persists:**

> To determine which actions will execute in a given retry iteration, you must execute at least the first action.

In the original design: `_begin_iter` populates the initial plan, but `_post_retry_check_actions` is an action that expands the plan.
In the first improvement: `schedule_chain` makes this look cleaner, but the same structure holds.
In the second improvement: `_continue_plan` is passed as an action and calls `schedule` during execution.

No refactoring changes this. The retry/stop/wait decisions cannot be computed before the attempt outcome is known. The outcome is produced by the function under retry. Therefore: **the action plan for iteration N+1 cannot be stated before iteration N completes.**

This is not a bug. It is the problem space: retry orchestration is an *online algorithm* — each decision depends on runtime information not available at configuration time.

---

## Inversion: Making the Impossible Trivially Satisfiable

Design where the full action plan is computed before any action executes:

```python
@dataclasses.dataclass
class RetryPlan:
    """Immutable, fully-declared action sequence for one retry iteration."""
    actions: tuple[Action, ...]      # frozen at construction

class PlanBuilder:
    def plan_first_iteration(self, config: RetryConfig) -> RetryPlan:
        actions = []
        if config.before: actions.append(CallHook(config.before))
        actions.append(DoAttempt())
        return RetryPlan(tuple(actions))

    def plan_after_outcome(
        self,
        outcome: Future,
        retry_state: RetryCallState,
        config: RetryConfig,
    ) -> RetryPlan:
        # Evaluate ALL strategies upfront
        is_explicit_retry = outcome.failed and isinstance(outcome.exception(), TryAgain)
        should_retry = is_explicit_retry or config.retry(retry_state)
        sleep_duration = config.wait(retry_state) if should_retry else 0.0
        should_stop = config.stop(retry_state) if should_retry else False

        if not should_retry:
            return RetryPlan((ReturnResult(outcome),))
        if should_stop:
            return RetryPlan((RaiseRetryError(outcome, config),))

        actions = []
        if config.after: actions.append(CallHook(config.after))
        actions.append(SetSleep(sleep_duration))
        if config.before_sleep: actions.append(CallHook(config.before_sleep))
        actions.append(DoSleep(sleep_duration))
        return RetryPlan(tuple(actions))
```

Now `RetryPlan` is fully declared before execution. The control flow graph is inspectable.

**New impossibility created:**

`plan_after_outcome` must call `config.retry(retry_state)`, `config.wait(retry_state)`, AND `config.stop(retry_state)` — unconditionally, before executing any action — even though the original design only calls `wait` and `stop` if `retry` returns True.

This creates two problems:

1. **Side-effectful strategies run unconditionally.** A `stop` strategy that records metrics, or a `wait` strategy that adjusts an external rate limiter, now fires even when retry is False and a successful result would have been returned.

2. **Strategies cannot depend on each other's outputs.** If `wait` implements "wait longer when we're about to stop" — i.e., it reads the stop decision — then `wait` must be called after `stop`, but `plan_after_outcome` must call both before returning. You could call `stop` first, pass its result to `wait`... but now `wait`'s signature changes. Every inter-strategy dependency requires a new parameter threading through `PlanBuilder`. The plan builder must be as complex as the original dynamic scheduler to express the same strategy interactions.

---

## The Conservation Law

**The law:** In any retry orchestration system, the complexity budget for strategy interaction is fixed. Moving it from *execution-time control flow* to *plan-building logic* does not reduce it — it relocates it with a surjection. The relocation changes who pays the cost (the scheduler vs. the plan builder) but does not change the total.

**Stated precisely:** Let S be the set of possible inter-strategy dependencies (wait-depends-on-retry, stop-depends-on-wait, etc.). The original design handles S implicitly through dynamic scheduling at O(1) cost per dependency — each planning action simply reads `iter_state.retry_run_result`. The inverted design handles S explicitly through parameter threading at O(|S|) cost — each dependency requires a new parameter, a new computation stage, a new type. S is a property of the problem domain, not the implementation. Its complexity must appear somewhere.

**What a senior engineer would not already know:**

A senior engineer knows the tradeoff between expressibility and predictability. What the conservation law reveals that they wouldn't know:

**The constraint is not expressibility vs. predictability — it is WHERE the inter-strategy dependency graph is materialized.** In the original design, the dependency graph is implicit in the execution order of the action queue. It is never represented as data; it exists only as a sequence of closures. This means it cannot be inspected, tested in isolation, or composed with other dependency graphs. In the inverted design, the dependency graph must be *explicitly represented* in the plan builder's logic — but this representation is program code, not data, so it still cannot be inspected or composed.

The finding: **No design in this design space produces an explicit, inspectable representation of inter-strategy dependencies as data.** Both the original and the inverted design encode the dependency graph as control flow. The conservation law predicts that any design that makes dependencies inspectable-as-data must introduce a new type (a dependency graph type), and the complexity of strategy configuration then transfers to constructing that graph.

**What it predicts about a third design:**

A third design that neither original nor inverted attempted: **separate strategy evaluation (pure functions returning decisions) from plan construction (a declared sequence) from execution (runs the sequence).** Strategies become `(RetryCallState) -> Decision`. A composer builds a `DecisionGraph` from strategies. An executor runs the graph.

The conservation law makes three predictions about this third design:

**Prediction 1:** The `DecisionGraph` builder will re-implement a subset of the original's dynamic scheduling logic. You need conditional edges ("only evaluate stop if retry is True"), which requires graph conditionals, which require a graph query language, which approaches Turing-completeness — at which point you have re-implemented a scheduler.

**Prediction 2:** Strategies that observe execution statistics (`self.statistics["attempt_number"]`) will not be pure functions. `RetryCallState` carries mutable statistics, and the third design must either pass statistics explicitly (making every strategy signature depend on statistics structure) or allow strategies to be stateful objects (reintroducing the original's threading concerns). Statistics cannot be extricated from strategy evaluation because statistics ARE the observable state that strategies decide upon.

**Prediction 3:** The third design will be correct for the common case (no inter-strategy dependencies, stateless strategies) and wrong or awkward for the cases Tenacity actually uses. Real retry policies — exponential backoff with jitter that caps at a maximum, combined with a stop-after-N-attempts that counts differently when the exception type changes — have dependencies and state. The third design predicts a clean architecture for simple policies and a complexity cliff for realistic ones. This is the conservation law's deepest prediction: the complexity budget isn't just relocated — it concentrates at the boundary between the generic framework and the specific policy, making that boundary the new load-bearing seam.
