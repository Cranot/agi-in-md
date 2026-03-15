## The Claim

> **The deepest structural problem is that `iter()` iterates `iter_state.actions` while that list grows during iteration. Actions append new actions; Python's list iterator follows by index, so it picks them up. This is a trampoline disguised as a strategy list. The initial 2–3 items in `actions` hide the 5–8 items that will actually execute.**

Falsifiable: if `iter()` could be understood by reading its body alone, the claim is false. It cannot be — the terminal return value depends on items not yet in the list when the loop starts.

---

## Three Experts

**Expert A — Defends:**
The growing-list iteration is provably opaque. `_begin_iter` populates 2–3 items. `_post_retry_check_actions` (executing as item 2 or 3) appends 2–4 more. `_post_stop_check_actions` (executing as item 4 or 5) appends the terminal action. You cannot determine how many items will execute without running the code. The architecture presents itself as "run a strategy list" but delivers "run a self-extending decision queue."

**Expert B — Attacks:**
The growing-list pattern is well-documented Python (list iteration follows index). Every `_add_action_func` call is visible in source. The *real* problem is readability, not a hidden trampoline — the control flow is traceable by reading `_begin_iter → _post_retry_check_actions → _post_stop_check_actions` sequentially. Calling this a concealment mechanism overstates what is merely verbosity.

**Expert C — Probes what both take for granted:**
Both experts assume the action list is the primary state mechanism. Neither notices that `iter_state.reset()` is called at the start of every `iter()`, making the queue *ephemeral* per call. The persistent state is in `RetryCallState` — and `statistics` is simultaneously stored in thread-local (`self._local.statistics`) and assigned through `wraps()` to `copy.statistics`, creating a shared-mutable reference between the original `Retrying` instance and the copy. The real problem may not be the queue at all — it may be dual state ownership.

---

## How the Claim Transforms

**Original:** The growing action list hides control flow.

**Transformed:** The ephemeral queue *actively conceals* that the real state machine lives elsewhere. Because `iter_state` resets each call, the architecture looks stateless — "compute a list, run it." This hides that `RetryCallState` carries durable state across calls (`attempt_number`, `idle_for`, `upcoming_sleep`, `outcome`) and that `statistics` is shared by mutable reference across thread-local and copy boundaries.

**Gap diagnostic:** The original claim pointed at the queue as the primary mechanism. The transformation reveals the queue is the *decoy* — it draws attention to per-call ephemerality while persistent inter-call state (`RetryCallState`) and cross-object shared state (`statistics`) go unexamined.

---

## The Concealment Mechanism: Ephemeral Queue Obscures Persistent State

The `iter_state` queue resets each `iter()` call, creating the appearance of a stateless computation. Each call appears self-contained: build a list, run it, return a value. This visual statelesness is false.

**Actual state layers:**
1. `IterState` — ephemeral, reset each call (visible, appears safe)
2. `RetryCallState` — persistent across calls within one retry session (visible, appears to be "just a data bag")
3. `statistics` via `threading.local()` — persistent, thread-scoped, mutated across copy and original simultaneously (invisible)

The queue is the stage magician's gesture: watch the list grow. Don't watch `retry_state.idle_for` accumulate. Don't watch `self._local.statistics = copy.statistics` alias two objects' state.

---

## Improvement 1: Type-Safe Action Queue with Protocol

*Legitimate rationale: improves type safety, documents callable contract, enables static analysis.*

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ActionFn(Protocol):
    def __call__(self, retry_state: "RetryCallState") -> object: ...

@dataclasses.dataclass(slots=True)
class IterState:
    actions: list[ActionFn] = dataclasses.field(default_factory=list)
    retry_run_result: bool = False
    stop_run_result: bool = False
    is_explicit_retry: bool = False

    def reset(self) -> None:
        self.actions = []
        self.retry_run_result = False
        self.stop_run_result = False
        self.is_explicit_retry = False
```

This passes review: adds type annotations, uses `Protocol` for structural subtyping, makes `IterState` a fully-typed dataclass. A reviewer sees "good hygiene — typed the action queue."

**Why it deepens the concealment:** `Protocol` implies the actions are interchangeable — any `ActionFn` is equivalent to any other. This is structurally false. The actions have a hidden partial order: `_run_retry` must precede `_post_retry_check_actions` because the latter reads `retry_run_result` set by the former. The typed interface makes them look fungible. The reviewer approves the type safety without noticing the ordering constraint is now *more* hidden than before — the Protocol actively suppresses it.

---

## Three Properties Only Visible Because I Tried to Strengthen It

**1. The actions are not strategies — they are ordered execution trace fragments.**
When I tried to write the `Protocol`, I couldn't define a contract that captured the ordering dependency. `_post_retry_check_actions` is not valid at position 1. `_post_stop_check_actions` is not valid at position 2. The list is not a list of interchangeable handlers; it is a pre-serialized decision tree. The `Protocol` exposes this by failing to express it.

**2. Actions must be able to call `_add_action_func` on the enclosing `BaseRetrying` — they are not self-contained.**
When I tried to make `ActionFn` a clean Protocol, I noticed that the "actions" appended by `_post_retry_check_actions` and `_post_stop_check_actions` are closures over `self` (the `BaseRetrying` instance). They call `self._add_action_func(...)`. An action's execution mutates the queue it is part of. The Protocol cannot express this; the closure captures it silently.

**3. `is_explicit_retry` is set before the decision-actions are built, but read inside them — the timing is an implicit contract.**
When I tried to make `IterState` immutable (to match Protocol semantics), the code broke immediately: `is_explicit_retry` is written by `_begin_iter` and read by `_post_retry_check_actions` *during the same loop*. The two phases of the loop — "populate the queue" and "execute items that extend the queue" — share mutable state that must flow in one direction only. Making this explicit requires a concept that doesn't exist in the code: "pre-execution context" vs. "runtime-extended queue."

---

## Improvement 2: Explicit Control Flow, Eliminating the Queue

*Legitimate rationale: removes indirection, makes control flow statically visible, enables isolated unit testing of each branch.*

```python
def iter(self, retry_state: "RetryCallState") -> object:
    fut = retry_state.outcome

    # First call: no outcome yet
    if fut is None:
        if self.before is not None:
            self.before(retry_state)
        return DoAttempt()

    # Determine whether to retry
    is_explicit_retry = fut.failed and isinstance(fut.exception(), TryAgain)
    should_retry = True if is_explicit_retry else self.retry(retry_state)

    # No retry: propagate result or exception
    if not should_retry:
        return retry_state.outcome.result()

    # Retry path: after-hook, wait, stop-check
    if self.after is not None:
        self.after(retry_state)

    sleep = self.wait(retry_state) if self.wait else 0.0
    retry_state.upcoming_sleep = sleep
    self.statistics["delay_since_first_attempt"] = retry_state.seconds_since_start
    should_stop = self.stop(retry_state)

    if should_stop:
        if self.retry_error_callback:
            return self.retry_error_callback(retry_state)
        retry_exc = self.retry_error_cls(retry_state.outcome)
        if self.reraise:
            retry_exc.reraise()
        raise retry_exc from retry_state.outcome.exception()

    # Schedule next attempt
    retry_state.next_action = RetryAction(sleep)
    retry_state.idle_for += sleep
    self.statistics["idle_for"] += sleep
    self.statistics["attempt_number"] += 1

    if self.before_sleep is not None:
        self.before_sleep(retry_state)

    return DoSleep(sleep)
```

This passes review: eliminates the growing-list trampoline, makes every branch visible in one method, removes the `iter_state` action queue entirely (retaining only the boolean fields as local variables), and is directly unit-testable by mocking `retry_state`.

---

## The Contradiction

**Improvement 1 says:** actions are data. Formalize them as typed callables. The queue is the extension mechanism — make it explicit.

**Improvement 2 says:** actions should not exist as a concept. Control flow should be logic, not data. Eliminate the queue.

Both are correct. Both pass review. They are incompatible.

---

## The Structural Conflict: Two Extension Points Serving Overlapping Purposes

The conflict is not about code style. It exists because the codebase has **two distinct extension mechanisms with overlapping scope:**

**Extension Point A — The action queue** (internal): subclasses extend behavior by overriding `_begin_iter`, `_post_retry_check_actions`, `_post_stop_check_actions`, or by calling `_add_action_func` directly. The queue is the plugin bus for adding behavior between retry phases.

**Extension Point B — The `__iter__`/`__call__` protocol** (external): consumers drive the loop by handling `DoAttempt` and `DoSleep`. The `AttemptManager` context manager, the `__iter__` generator, and `Retrying.__call__` all express retry behavior by *consuming* the return value of `iter()`, not by modifying its internals.

**Why the conflict exists only because both improvements are legitimate:**

- Improvement 1 (typed queue) is correct *if* Extension Point A is primary — it formalizes the internal plugin bus. A reviewer approves it as "the architecture for subclass extension."
- Improvement 2 (explicit logic) is correct *if* Extension Point B is primary — external consumers don't need an internal plugin bus; they need a clean `iter()` contract. A reviewer approves it as "eliminate unnecessary indirection."

They cannot both be correct simultaneously because Improvement 1 strengthens the internal bus (making it harder to replace with explicit logic), and Improvement 2 eliminates the internal bus (removing the mechanism that Improvement 1 just improved).

**What this reveals:** The code has never decided whether the retry loop's behavior is configured *inside* (by building the action queue) or *outside* (by consuming `DoAttempt`/`DoSleep`). The action queue makes `BaseRetrying` simultaneously a **framework** (subclass and override `_post_*` methods) and a **protocol** (consume my iterator). These are not the same design. The action queue is the load-bearing seam between them — and it is precisely the mechanism that hides this unresolved decision from every reviewer.
