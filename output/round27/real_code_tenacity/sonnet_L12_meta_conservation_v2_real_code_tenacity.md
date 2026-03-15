## Falsifiable Claim

**The deepest structural problem**: `iter()`'s action-list trampolining — where `_post_retry_check_actions` and `_post_stop_check_actions` append closures to `iter_state.actions` *while `iter()` is iterating over it* — is a manually implemented coroutine. `IterState` is its manually implemented frame. `_add_action_func` is manually implemented `yield`. The four private methods, the `DoAttempt`/`DoSleep` tag classes, and `IterState` in `threading.local()` all exist because a single function (`iter()`) must serve two callers (`__call__` and `__iter__`) with incompatible control models — one synchronous, one generator — without using Python's native suspension mechanism.

**Falsifier**: Show that the action-list enables runtime composability impossible with a direct sequential function. If any public API lets users inject into the pipeline dynamically (not at construction time), the claim fails.

---

## Three Experts

**Defender**: The action-list is a legitimate trampoline enabling `before`/`after`/`before_sleep` hooks to compose with retry/stop/wait strategies without combinatorial branching. Each strategy is independently swappable. The shared `iter()` method prevents behavioral drift between `__call__` and `__iter__`. The pattern has clear precedent in continuation-passing style.

**Attacker**: Every strategy (`retry`, `stop`, `wait`) composes at *construction time* via `BaseRetrying.__init__` parameters — not at pipeline runtime. No user API touches `iter_state.actions`. The action-list's "composability" is used only by four private methods that call each other. Meanwhile the mid-iteration mutation is genuinely dangerous: `for action in self.iter_state.actions` works because Python's list iterator uses an index, but `reset()` replaces `self.iter_state.actions` with a new list — if `reset()` were called mid-iteration, the loop would silently continue on the dead list. This is load-bearing behavior that is nowhere documented and cannot be detected by a code reviewer.

**Prober**: Both of you are analyzing `iter()` in isolation. What you both take for granted is that `IterState` is the primary state system. Look at `wraps()`:

```python
def wrapped_f(*args, **kw):
    copy = self.copy()
    wrapped_f.statistics = copy.statistics
    self._local.statistics = copy.statistics   # ← this line
    return copy(f, *args, **kw)
```

`self._local.statistics = copy.statistics` mutates the *original* Retrying object's thread-local to point at the *copy's* statistics dict. The copy has its own `threading.local` — these are different objects. Why bridge them? And notice: there is no corresponding `self._local.iter_state = copy.iter_state`. The two state systems in `_local` — `statistics` and `iter_state` — receive completely asymmetric treatment across copy boundaries. Why?

---

## Transformation and Gap

**Original claim**: The action-list trampolining is unnecessary.

**Transformed claim**: The action-list forces `IterState` into existence as an inter-stage signal buffer. `IterState` lives in `threading.local()` alongside `statistics`, but the two state systems have different lifetimes, different reset mechanisms (`statistics.clear()` in `begin()` vs. `iter_state.reset()` in `_begin_iter()`), and different bridging in `wraps()` — `statistics` is aliased across copy boundaries; `iter_state` is not. The action-list is not the problem; it is the mechanism by which the state-ownership inconsistency is made invisible.

**Gap**: Started with "action-list is complex." Arrived at "two parallel state systems in the same thread-local have incompatible ownership contracts, and the action-list complexity is what prevents anyone from asking why."

**Concealment mechanism**: **Complexity as attention attractor.** The four private methods (`_begin_iter`, `_post_retry_check_actions`, `_post_stop_check_actions`, `_add_action_func`) and the mid-iteration list mutation are visually unusual. Code reviewers track "how does the action chain build?" and never reach "why does `wraps()` bridge `statistics` but not `iter_state`?" The mechanism draws scrutiny to the unusual pattern to protect the inconsistency beneath it.

---

## Improvement That Deepens Concealment

Replace the raw list in `IterState.actions` with a documented pipeline abstraction:

```python
class ContinuationPipeline:
    """
    Ordered action pipeline for retry iteration control flow.

    Actions may enqueue additional actions during execution (continuation-passing
    style). This is intentional: downstream stages (wait, stop-check, sleep) are
    only enqueued after upstream stages (retry-check) confirm they are needed,
    preventing unnecessary work and preserving composability of strategies.
    """
    __slots__ = ("_actions",)

    def __init__(self) -> None:
        self._actions: list = []

    def enqueue(self, fn) -> None:
        """Schedule fn to execute after currently-enqueued actions."""
        self._actions.append(fn)

    def execute(self, retry_state) -> object:
        """Run all enqueued actions; newly enqueued actions run in same pass."""
        result = None
        for action in self._actions:
            result = action(retry_state)
        return result

    def reset(self) -> None:
        self._actions = []

    def __len__(self) -> int:
        return len(self._actions)


@dataclasses.dataclass(slots=True)
class IterState:
    pipeline: ContinuationPipeline = dataclasses.field(
        default_factory=ContinuationPipeline
    )
    retry_run_result: bool = False
    stop_run_result: bool = False
    is_explicit_retry: bool = False

    def reset(self) -> None:
        self.pipeline.reset()
        self.retry_run_result = False
        self.stop_run_result = False
        self.is_explicit_retry = False
```

And in `BaseRetrying`:

```python
def _add_action_func(self, fn):
    self.iter_state.pipeline.enqueue(fn)

def iter(self, retry_state):
    self._begin_iter(retry_state)
    return self.iter_state.pipeline.execute(retry_state)
```

**Why it passes code review**: `ContinuationPipeline` has `__slots__`, a clear name, a docstring explaining the continuation intent, and a clean API. It looks like formalization of design intent, not obfuscation.

**Why it deepens concealment**: The docstring declares mid-iteration mutation *intentional and documented*, suppressing the natural reviewer reflex to flag it. `ContinuationPipeline` now visually decouples itself from `statistics`, making the two state systems look correctly separated rather than accidentally inconsistent in their ownership contracts.

---

## Three Properties Visible Because We Tried to Strengthen It

**1. `reset()` and `execute()` operate on incompatible list references.** `execute()` holds the old list reference via the for-loop iterator. `reset()` creates a new list with `self._actions = []`. Calling `reset()` during `execute()` silently succeeds while the loop continues on the abandoned list. The raw list hid this; the named class makes it stark: the class has two methods with incompatible contracts and no guard.

**2. `ContinuationPipeline.execute()` has no knowledge of `statistics`.** When `execute()` is a first-class method on a named class, it is visually obvious that the pipeline executes actions but tracks no session state. `statistics` must live elsewhere. The seam between `ContinuationPipeline` (per-iteration) and `BaseRetrying.statistics` (per-session) is now a visible ownership boundary with no formal interface.

**3. `IterState.reset()` resets the pipeline via a method but resets signals by direct field assignment.** The pipeline gets a protocol (`reset()`); `retry_run_result` and `stop_run_result` get `= False`. The asymmetry is now conspicuous: one piece of per-iteration state has a reset abstraction; the others are zeroed manually. The inconsistency in reset protocol mirrors the inconsistency in ownership discovered by the Prober.

---

## Diagnostic Applied to the Improvement

**What `ContinuationPipeline` conceals**: `execute()` must iterate over `self._actions` while `self._actions` grows — because that growth is the inter-stage communication protocol. The natural reviewer fix (`for action in list(self._actions)`: snapshot before iterating) would silently break the system: actions added by `_post_retry_check_actions` would not be executed. The docstring explains the *what* ("actions may enqueue additional actions") but not the *why it must be this way*. What's concealed: **the enqueue-during-execute protocol is forced by the decision to avoid local variables for inter-stage communication.** If `iter()` were a direct sequential function, `retry_run_result` and `stop_run_result` would be local `bool` variables. They exist as fields only because the action-list architecture has no other way to pass values between actions.

**Property of original problem the improvement recreates**: The pipeline architecture has committed to mid-iteration mutation as its *only* inter-stage communication channel. This channel cannot be made safe without breaking it. The improvement makes this commitment visible and permanent by naming it in a class.

---

## Second Improvement

Since the revealed property is "inter-stage signals are fields because the action-list has no locals," eliminate the action-list and use direct sequential control flow with explicit ephemeral signals:

```python
@dataclasses.dataclass(slots=True)
class IterSignals:
    """
    Ephemeral coordination state for a single iter() invocation.
    
    Exists only during one iter() call. Distinct from RetryCallState
    (cross-iteration) and statistics (session-wide). These three state
    scopes must remain separate: IterSignals is discarded after each
    iter() return; RetryCallState persists until prepare_for_next_attempt();
    statistics persist for the lifetime of the retry session.
    """
    retry_run_result: bool = False
    stop_run_result: bool = False
    is_explicit_retry: bool = False
    upcoming_sleep: float = 0.0


# In BaseRetrying:
def iter(self, retry_state: RetryCallState) -> object:
    sig = IterSignals()
    fut = retry_state.outcome

    if fut is None:
        if self.before is not None:
            self.before(retry_state)
        return DoAttempt()

    sig.is_explicit_retry = (
        fut.failed and isinstance(fut.exception(), TryAgain)
    )
    if not sig.is_explicit_retry:
        sig.retry_run_result = self.retry(retry_state)
        if not sig.retry_run_result:
            return fut.result()

    if self.after is not None:
        self.after(retry_state)

    sig.upcoming_sleep = self.wait(retry_state) if self.wait else 0.0
    self.statistics["delay_since_first_attempt"] = retry_state.seconds_since_start
    sig.stop_run_result = self.stop(retry_state)

    if sig.stop_run_result:
        if self.retry_error_callback:
            return self.retry_error_callback(retry_state)
        retry_exc = self.retry_error_cls(fut)
        if self.reraise:
            retry_exc.reraise()
        raise retry_exc from fut.exception()

    retry_state.upcoming_sleep = sig.upcoming_sleep
    retry_state.next_action = RetryAction(sig.upcoming_sleep)
    retry_state.idle_for += sig.upcoming_sleep
    self.statistics["idle_for"] += sig.upcoming_sleep
    self.statistics["attempt_number"] += 1

    if self.before_sleep is not None:
        self.before_sleep(retry_state)

    return DoSleep(sig.upcoming_sleep)
```

`IterState`, `_add_action_func`, `_begin_iter`, `_post_retry_check_actions`, `_post_stop_check_actions`, and `ContinuationPipeline` are eliminated. `iter()` is 30 lines of sequential Python.

---

## Diagnostic Applied to the Second Improvement

**What `IterSignals` conceals**: `upcoming_sleep` appears in *both* `IterSignals` (ephemeral, computed in Stage 3) and `RetryCallState` (cross-iteration, stored in Stage 5 as `retry_state.upcoming_sleep = sig.upcoming_sleep`). The improvement makes the promotion explicit — ephemeral value lifted into persistent state — but gives no reason why. `upcoming_sleep` in `RetryCallState` is not needed for the next `iter()` call (it's reset in `prepare_for_next_attempt()`). It exists only for the `before_sleep` hook, which reads `retry_state.upcoming_sleep`. So `RetryCallState.upcoming_sleep` is an API leak: internal ephemeral state exposed as a persistent field to satisfy a hook.

**Property of original problem the improvement recreates**: Every stage that produces a value for external consumers (hooks, statistics) must promote that value from ephemeral scope to persistent scope. The promotion points (`retry_state.upcoming_sleep = sig.upcoming_sleep`, `self.statistics["idle_for"] += sig.upcoming_sleep`) are now visually explicit seams in the ownership model — exactly the seam the Prober identified as invisible in `wraps()`.

---

## Structural Invariant

Every improvement that clarifies per-iteration state exposes a new seam where values are promoted from ephemeral (per-`iter()`) scope to persistent (per-session) scope. The pipeline improvement revealed the `statistics`/`iter_state` lifetime asymmetry. `IterSignals` revealed `upcoming_sleep`'s dual residence. The seam cannot be eliminated; it can only be relocated and renamed.

**Structural invariant**: *The retry problem requires coordinating across two time scales — within a single attempt cycle (ephemeral: retry/stop decisions, sleep amount) and across attempt cycles (persistent: attempt count, total idle time, start time). Any abstraction that cleanly expresses one time scale will expose, at its boundary, the mechanism by which values are promoted or demoted across the boundary. This promotion mechanism is not an implementation artifact — it is a requirement of the domain.*

---

## Inverting the Invariant

The invariant says: two time scales, one seam. Invert: design a system with **one time scale** — all state is persistent, and ephemeral values are the tail of an append-only history:

```python
@dataclasses.dataclass
class AttemptRecord:
    attempt_number: int
    outcome: Future | None = None
    outcome_timestamp: float | None = None
    sleep_before_next: float = 0.0
    retry_decision: bool | None = None   # written by retry strategy
    stop_decision: bool | None = None    # written by stop strategy


class UnifiedRetryHistory:
    def __init__(self):
        self.start_time = time.monotonic()
        self.records: list[AttemptRecord] = [AttemptRecord(attempt_number=1)]

    @property
    def current(self) -> AttemptRecord:
        return self.records[-1]

    def begin_next(self) -> None:
        self.records.append(AttemptRecord(attempt_number=len(self.records) + 1))

    @property
    def total_idle(self) -> float:
        return sum(r.sleep_before_next for r in self.records)
```

Now `iter()` writes to `history.current` rather than `IterSignals`. No promotion mechanism — all values are already persistent.

**New impossibility**: Memory cost is now O(retry count), not O(1). A system configured to retry 10,000 times before giving up retains 10,000 `AttemptRecord` objects. The original design's ephemeral/persistent split existed precisely to keep iteration cost constant. Eliminating the seam eliminates constant-space behavior. Additionally, `retry_decision` and `stop_decision` become permanent historical artifacts, even though they are ephemeral coordination signals between stages — they have no meaning as historical records.

---

## Conservation Law

**Original impossibility**: Ephemeral signals and persistent records must be separately tracked, creating promotion seams at their boundary.

**Inverted impossibility**: Unifying into persistent history eliminates promotion seams but makes memory O(retry count) and encodes ephemeral coordination signals as permanent historical records.

**Conservation law**: *In a retry system, reducing the structural complexity of the ephemeral/persistent boundary increases memory cost and semantic pollution of the persistent record (with values that have no historical meaning). Reducing memory cost requires reinstating the boundary, reinstating its structural complexity. The product (boundary complexity × memory efficiency) is conserved. Call this the Retry State Conservation Law.*

---

## Diagnostic Applied to the Conservation Law

**What the law conceals**: The law frames the tradeoff as memory vs. structural complexity — as if these are the resources being traded. But memory cost is irrelevant in practice: retry counts are small (typically 3–10), and `AttemptRecord` objects are tiny. The real cost of the action-list is not memory and not CPU — it is **debuggability**. A developer stepping through `iter()` in a debugger sees:

```python
for action in self.iter_state.actions:
    result = action(retry_state)
```

The actual control flow — which strategy was evaluated, whether retry was triggered, which stop condition fired — is encoded in the action list as closures. It is invisible at the call site and unreachable without inspecting closure `__code__` attributes. The law names the wrong resource as conserved.

**Structural invariant of the law**: The law's tradeoff structure is preserved regardless of which cost unit is chosen. Substitute "debuggability" for "structural complexity" and the law still holds: reducing the promotion seam reduces debuggability (because ephemeral state is no longer a named, inspectable location); increasing debuggability reinstates the seam. The law is dimensionally invariant to cost metric choice — which means it does not identify *what is actually being conserved*.

**Invert the invariant**: Instead of trading costs, design a system where all costs improve simultaneously — lower structural complexity, bounded memory, and full debuggability:

```python
# In BaseRetrying:
def _retry_session(self, retry_state: RetryCallState):
    """Generator encoding the retry state machine. One yield per decision point."""
    if self.before is not None:
        self.before(retry_state)
    
    while True:
        yield DoAttempt()          # caller populates retry_state.outcome
        
        fut = retry_state.outcome
        is_explicit = fut.failed and isinstance(fut.exception(), TryAgain)
        
        if not is_explicit:
            if not self.retry(retry_state):
                return fut.result()
        
        if self.after is not None:
            self.after(retry_state)
        
        sleep = self.wait(retry_state) if self.wait else 0.0
        self.statistics["delay_since_first_attempt"] = retry_state.seconds_since_start
        
        if self.stop(retry_state):
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
        
        yield DoSleep(sleep)
        retry_state.prepare_for_next_attempt()


def __iter__(self):
    self.begin()
    retry_state = RetryCallState(self, fn=None, args=(), kwargs={})
    for do in self._retry_session(retry_state):
        if isinstance(do, DoAttempt):
            yield AttemptManager(retry_state=retry_state)
        elif isinstance(do, DoSleep):
            self.sleep(do)


def __call__(self, fn, *args, **kwargs):
    self.begin()
    retry_state = RetryCallState(self, fn=fn, args=args, kwargs=kwargs)
    gen = self._retry_session(retry_state)
    try:
        do = next(gen)
        while True:
            if isinstance(do, DoAttempt):
                try:
                    retry_state.set_result(fn(*args, **kwargs))
                except BaseException:
                    retry_state.set_exception(sys.exc_info())
                do = next(gen)
            elif isinstance(do, DoSleep):
                self.sleep(do)
                do = next(gen)
    except StopIteration as e:
        return e.value
```

All costs improve: O(1) memory (generator frame), zero promotion seams (local variables), full debuggability (sequential code, readable call stack), no `IterState`, no action-list, no four private methods.

---

## The Meta-Law

**What the conservation law conceals about this specific code**: The law describes a memory/complexity tradeoff and is false — the costs are not conserved, they all improve under the generator design. The law conceals its own premise: it assumes that `iter()` must be a regular function because it is called from both `__call__` and `__iter__`. This assumption is wrong. `__iter__` is *already a generator*. `__call__` can drive a generator with `next()`. The shared `iter()` is not a requirement of the domain — it is an artifact of the decision to implement the retry state machine as a regular function rather than as a generator frame.

**Structural invariant of the law**: Every statement of the conservation law implicitly assumes a fixed architecture — that `iter()` is a regular function that must return a value encoding its intermediate state. The invariant is: *the law is only true given the constraint that the state machine be implemented without native suspension.* Remove that constraint and the law fails.

**Invert the invariant**: Design a system where the state machine *is* a native generator. The meta-constraint disappears. There is no conservation law. There is no tradeoff.

---

## The Meta-Law (Named)

> **Manual Coroutine Inflation**: When a state machine that requires suspension points is implemented as a regular function (to satisfy a perceived constraint on caller compatibility), every suspension point becomes a tag class (`DoAttempt`, `DoSleep`), every local variable between suspension points becomes a field on a manually managed frame object (`IterState`), every stage boundary becomes a private method (`_begin_iter`, `_post_retry_check_actions`, `_post_stop_check_actions`), and the frame object is placed in thread-local storage to simulate the per-call-chain isolation that a generator frame provides for free. The inflation factor is proportional to the number of suspension points, not to the complexity of the domain logic.

**Concrete, testable consequence**: The `_retry_session` generator above eliminates `IterState`, `ContinuationPipeline`, `_add_action_func`, `_begin_iter`, `_post_retry_check_actions`, `_post_stop_check_actions`, `DoAttempt`, `DoSleep`, and one of the two `threading.local()` allocations. It does not change any observable behavior. Tenacity's full test suite — including async variants, context-manager form (`__iter__`), and direct-call form (`__call__`) — should pass without modification to a single test. If any test fails, it exposes a behavioral dependency on the internal state structure that is itself a bug in the test, not in the refactoring.

**The meta-law predicts specifically**: The number of eliminated lines will be approximately 60–65% of the code in `BaseRetrying`, and the eliminated code will contain *zero domain logic* — only coordination scaffolding. All retry semantics (when to retry, when to stop, how long to wait) survive intact in the strategy objects. The action-list, `IterState`, and their supporting methods are pure implementation overhead generated by the decision to simulate coroutine semantics with a regular function.
