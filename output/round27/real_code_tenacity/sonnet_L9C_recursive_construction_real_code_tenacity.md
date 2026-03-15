# Recursive Structural Analysis: Tenacity Retry Library

---

## I. Initial Claim (Specific and Falsifiable)

**Claim**: `BaseRetrying.iter()` uses list mutation during its own iteration as the library's primary control-flow mechanism. `_post_retry_check_actions` and `_post_stop_check_actions` determine what happens next by appending to the same list currently being consumed in `iter()`'s `for` loop — making the execution graph invisible to static analysis, non-compositional, and untestable in isolation.

*Falsification condition*: Show that `iter_state.actions` is never modified while `iter()` is executing, or that some other verified mechanism controls execution branching.

The mechanism in concrete terms:

```python
def iter(self, retry_state):
    self._begin_iter(retry_state)         # populates actions list
    result = None
    for action in self.iter_state.actions:   # Python list: index-based, tolerates appends
        result = action(retry_state)      # action may append more actions to the same list
    return result

def _post_retry_check_actions(self, retry_state):
    if not (self.iter_state.is_explicit_retry or self.iter_state.retry_run_result):
        self._add_action_func(lambda rs: rs.outcome.result())  # <- append during for-loop
        return
    # ...
    self._add_action_func(self._post_stop_check_actions)       # <- and again
```

Python's `for x in list` uses an internal integer index that advances by one per step. Appending to the list during iteration is well-defined, but this is not a coincidence of implementation — it is the *entire control flow protocol*.

---

## II. Three Experts Destabilize the Claim

### Expert A — Defender

The claim is precisely correct. The consequence is that there is no static description of what `iter()` does. The execution path is a function of runtime state written *into* the action list as side effects. Consider what it takes to test `_post_stop_check_actions` in isolation:

- It reads `self.iter_state.stop_run_result` (set by `_run_stop`)
- It reads `self.iter_state.is_explicit_retry` (set by `_begin_iter`)
- Its "output" is a mutation of `self.iter_state.actions`
- That mutation only has meaning if it happens during an active `for action in self.iter_state.actions` loop

You cannot call `_post_stop_check_actions` in a test without reconstructing the entire execution context. The coupling is total and invisible.

### Expert B — Attacker

The mutation-during-iteration is real but not the deepest problem — it's Python's list semantics being used knowingly. The *actual* problem is what `threading.local()` is asked to do. A retry policy is configuration: you configure it once, it shouldn't carry mutable per-call state. Yet `BaseRetrying` stores `iter_state` and `statistics` in thread-local storage on the policy object itself. `copy()` tries to fix this but makes it worse — `wraps()` does:

```python
copy = self.copy()
wrapped_f.statistics = copy.statistics      # sets the function attribute
self._local.statistics = copy.statistics    # aliases original's local to copy's dict
return copy(f, *args, **kw)
```

Two threads calling `wrapped_f` simultaneously will both write `wrapped_f.statistics` — last writer wins. `threading.local()` protects `self._local` per-thread, but `wrapped_f` is a module-level object. The code *looks* thread-safe because of `threading.local()`. The thread-unsafe path is on a plain attribute.

### Expert C — Probes What Both Take for Granted

Both of you assume that `BaseRetrying` *should* be the class that contains both things. That assumption is the problem. You're both arguing about symptoms.

A retry *policy* is immutable configuration: which exceptions to retry, when to stop, how long to wait. A retry *execution context* is mutable per-call state: attempt count, elapsed time, last outcome, action queue. These have incompatible lifecycles. Policy lives as long as the decorator; context lives for one call.

The action-list mutation (Expert A) and the thread-local aliasing (Expert B) are both strategies for forcing a stateful execution context into an object that was designed to be configuration. The resets at `begin()` and `iter_state.reset()` create the *appearance* of proper scoping while the actual scope is "thread-local storage on a decorator object."

---

## III. Claim Transformation

**Original claim**: The deepest problem is list mutation during iteration as control flow.

**Transformed claim**: The list mutation during iteration is an artifact of the real problem — `BaseRetrying` cannot decide whether it *is* a retry policy or whether it *runs* a retry policy. Every design decision in the file follows from that unresolved identity. The action-list mechanism is how the code manages mutable execution state on what should be a configuration object — mutation during iteration is the only way to scope control flow decisions to a single call when the object persists across calls.

**Gap diagnostic**: The original claim was at the mechanism level (how actions are dispatched). The transformed claim is at the identity level (what the object *is*). The gap reveals that the mechanism question cannot be answered correctly without answering the identity question first. This is a diagnostic about the code's architecture: mechanism-level analysis always terminates at an identity confusion.

---

## IV. The Concealment Mechanism

**Name**: *Incremental state reset as lifecycle simulation.*

The code hides the policy/context conflation by resetting execution state at well-chosen points, making call-scoped state *look* like it's properly scoped:

| Reset site | What it resets | What it conceals |
|---|---|---|
| `begin()` | `statistics` dict cleared | Statistics live on the policy object between calls |
| `iter_state.reset()` at start of each `iter()` | Action list, flags | iter_state lives in thread-local on the policy object |
| `copy()` in `wraps()` | Creates fresh instance | Both instances share strategy callables (`stop`, `wait`, `retry`) |
| `prepare_for_next_attempt()` | Clears outcome, timestamp | State transitions are on RetryCallState; the main object never fully resets |

Each reset looks like careful lifecycle management. Collectively they simulate proper scoping while never establishing it. The result is that reading any single reset operation seems correct; only reading all of them together reveals that the reset pattern is compensating for an object that holds both configuration (permanent) and execution state (transient) in the same namespace.

---

## V. Legitimate-Looking Improvement That Deepens the Concealment

The obvious "fix" is to separate policy from context. This passes code review easily because it appears to solve the identified problem:

```python
@dataclasses.dataclass(frozen=True)
class RetryPolicy:
    """Immutable retry configuration. Separated from mutable execution context."""
    sleep: object = dataclasses.field(default_factory=lambda: time.sleep)
    stop: object = dataclasses.field(default_factory=lambda: stop_never)
    wait: object = dataclasses.field(default_factory=lambda: wait_none())
    retry: object = dataclasses.field(default_factory=lambda: retry_if_exception_type())
    before: object = None
    after: object = None
    before_sleep: object = None
    reraise: bool = False
    retry_error_cls: type = RetryError
    retry_error_callback: object = None
    name: str = None
    enabled: bool = True

    def with_overrides(self, **kwargs) -> "RetryPolicy":
        return dataclasses.replace(self, **kwargs)


class RetryExecutionContext:
    """
    Mutable per-call execution state. Created fresh for each retry sequence.
    Holds the action chain and statistics for a single call.
    """
    __slots__ = ("policy", "iter_state", "statistics")

    def __init__(self, policy: RetryPolicy):
        self.policy = policy
        self.iter_state = IterState()
        self.statistics: dict = {}

    def begin(self) -> None:
        self.statistics.clear()
        self.statistics["start_time"] = time.monotonic()
        self.statistics["attempt_number"] = 1
        self.statistics["idle_for"] = 0
        self.statistics["delay_since_first_attempt"] = 0

    def _add_action(self, fn) -> None:
        self.iter_state.actions.append(fn)

    def iter(self, retry_state: "RetryCallState") -> object:
        """Execute current action chain, which may extend itself during iteration."""
        self._build_iter(retry_state)
        result = None
        for action in self.iter_state.actions:   # still mutated during iteration
            result = action(retry_state)
        return result

    def _build_iter(self, retry_state: "RetryCallState") -> None:
        self.iter_state.reset()
        fut = retry_state.outcome
        if fut is None:
            if self.policy.before is not None:
                self._add_action(self.policy.before)
            self._add_action(lambda rs: DoAttempt())
            return
        self.iter_state.is_explicit_retry = (
            fut.failed and isinstance(fut.exception(), TryAgain)
        )
        if not self.iter_state.is_explicit_retry:
            self._add_action(self._run_retry)
        self._add_action(self._post_retry_check)

    def _run_retry(self, retry_state):
        self.iter_state.retry_run_result = self.policy.retry(retry_state)

    def _run_wait(self, retry_state):
        retry_state.upcoming_sleep = self.policy.wait(retry_state) if self.policy.wait else 0.0

    def _run_stop(self, retry_state):
        self.statistics["delay_since_first_attempt"] = retry_state.seconds_since_start
        self.iter_state.stop_run_result = self.policy.stop(retry_state)

    def _post_retry_check(self, retry_state):
        if not (self.iter_state.is_explicit_retry or self.iter_state.retry_run_result):
            self._add_action(lambda rs: rs.outcome.result())
            return
        if self.policy.after is not None:
            self._add_action(self.policy.after)
        self._add_action(self._run_wait)
        self._add_action(self._run_stop)
        self._add_action(self._post_stop_check)

    def _post_stop_check(self, retry_state):
        if self.iter_state.stop_run_result:
            if self.policy.retry_error_callback:
                self._add_action(self.policy.retry_error_callback)
                return
            def exc_check(rs):
                retry_exc = self.policy.retry_error_cls(rs.outcome)
                if self.policy.reraise:
                    retry_exc.reraise()
                raise retry_exc from rs.outcome.exception()
            self._add_action(exc_check)
            return

        def next_action(rs):
            rs.next_action = RetryAction(rs.upcoming_sleep)
            rs.idle_for += rs.upcoming_sleep
            self.statistics["idle_for"] += rs.upcoming_sleep
            self.statistics["attempt_number"] += 1

        self._add_action(next_action)
        if self.policy.before_sleep is not None:
            self._add_action(self.policy.before_sleep)
        self._add_action(lambda rs: DoSleep(rs.upcoming_sleep))


class Retrying:
    """Execution engine. Creates a fresh RetryExecutionContext per call."""
    def __init__(self, policy: RetryPolicy):
        self.policy = policy

    def __call__(self, fn, *args, **kwargs):
        ctx = RetryExecutionContext(self.policy)
        ctx.begin()
        retry_state = RetryCallState(retry_object=self, fn=fn, args=args, kwargs=kwargs)
        while True:
            do = ctx.iter(retry_state)
            if isinstance(do, DoAttempt):
                try:
                    result = fn(*args, **kwargs)
                except BaseException:
                    retry_state.set_exception(sys.exc_info())
                else:
                    retry_state.set_result(result)
            elif isinstance(do, DoSleep):
                retry_state.prepare_for_next_attempt()
                self.policy.sleep(do)
            else:
                return do
```

This passes code review. It solves the stated problem — `RetryPolicy` is frozen, `RetryExecutionContext` is created fresh per call, no thread-local storage, `wrapped_f.statistics` threading bug eliminated. The separation is real and the naming is accurate.

---

## VI. Three Properties Visible Only Because We Tried to Strengthen

**1. The action-list mutation has no principled termination condition.**

Once `RetryExecutionContext` is a standalone class, it becomes obvious that `iter()` should have a declared contract: inputs, outputs, loop invariants. But there are none. The loop terminates when no action appends another action that returns a non-None value — this is entirely implicit. In the original code this was hidden because `iter()` was a method on a large class full of other concerns. Extracted, the method is only eight lines and its implicit termination is immediately obvious. There is no mechanism preventing infinite action-chain growth.

**2. The strategy objects stored in `RetryPolicy` are not necessarily immutable.**

`frozen=True` on a dataclass prevents attribute reassignment, not mutation of referenced objects. `stop_after_attempt(3)` returns a stateful object that counts calls. When `dataclasses.replace()` creates a new `RetryPolicy`, the new policy shares the *same* strategy instances. Two `Retrying` instances derived from the same policy share state in their stop/wait/retry strategies. The original code's `copy()` had exactly this problem, but it was invisible because both the policy and its strategies lived under the same class hierarchy. `frozen=True` advertises immutability and makes the shared-mutable-strategies problem *harder* to see, not easier.

**3. `RetryExecutionContext` needs two incompatible APIs.**

Separating context from policy makes immediately visible that the library has two protocols: `__call__` (execution engine, handles DoAttempt/DoSleep internally) and `__iter__` (cooperative protocol, yields control to caller on DoAttempt/DoSleep). These two protocols are not different views of the same thing — they have different invariants about who holds `retry_state` and who decides what to do with DoAttempt. A single `RetryExecutionContext` class cannot cleanly serve both without either exposing internal state to the iterator caller or duplicating the entire action-chain dispatch. The original code hid this by burying both paths in a single large class. Extracting context makes the dual-protocol incoherence structural.

---

## VII. Recursive Application: What the Improvement Conceals, and What It Recreates

**What the improvement conceals:**

`frozen=True` is the new concealment mechanism. It replaces *incremental state reset* (the original mechanism) with *apparent value semantics*. A frozen dataclass looks like an immutable value. The code that creates `Retrying(policy)` looks like it's receiving an inert configuration value. The actual values stored in `policy.stop`, `policy.wait`, `policy.retry` may be stateful objects with their own hidden state, and `frozen=True` says nothing about them. The improvement makes this harder to notice because the visual marker of immutability (`frozen=True`) is present and prominent.

Additionally: `RetryExecutionContext.iter()` still mutates its action list during its own iteration. The improvement correctly separates *where* the execution state lives (on the context, not the policy). But it does nothing to change *how* control flow works. The mechanism is preserved exactly. Code review sees the clean separation and approves the PR. The list-mutation-during-iteration disappears from the review's frame of attention because the frame is now "policy vs. context" rather than "how does iter() work."

**What property of the original problem is visible only because the improvement recreates it:**

The original problem — that `BaseRetrying` is simultaneously a policy object and an execution context — was hidden by making it a single class. The improvement creates two classes with a clean boundary. But then `Retrying.__call__` must create a `RetryExecutionContext` and pass it `self.policy`. And `RetryExecutionContext` must accept a policy and call `policy.stop(retry_state)` and `policy.retry(retry_state)`. This means the execution context holds a reference to the policy and invokes it on every step — the two objects are not actually separated, they are coupled in the same direction as before (context depends on policy), with the same shared-strategy-object problem.

The property now visible: **the strategies (`stop`, `wait`, `retry`) are the true execution contexts**, not `RetryExecutionContext`. `stop_after_attempt(3)` is stateful per retry sequence. `wait_exponential()` may use attempt number from retry state. The correct separation is not policy vs. execution context — it is *stateless configuration* vs. *per-call strategy instances*. The original code's conflation hid this entirely. The improvement recreates it with better naming, which is why you can now see it: `frozen=True` on `RetryPolicy` holding strategy objects reveals that those strategy objects are the unfrozen things that matter.

The improvement is more honest about the wrong abstraction boundary, which makes the right boundary visible.
