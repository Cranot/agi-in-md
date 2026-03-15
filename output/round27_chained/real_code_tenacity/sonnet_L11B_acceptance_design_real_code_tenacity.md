## Structure First: Level 11 Diagnostic

---

### The Falsifiable Claim

> **`DoSleep` inheriting from `float` is the specific mechanism by which a typed boundary decision forecloses typed disambiguation in the interior. `DoSleep(float)` enables `time.sleep(do)` without unwrapping — but requires `upcoming_sleep: float` (not `float | None`). This forces "wait strategy not yet evaluated" to be encoded as `0.0` — the same value as "wait strategy evaluated and returned zero." L10 identified the observation window: `after` fires when `upcoming_sleep` is stale. L11 identifies why the obvious fix (type `upcoming_sleep` as `float | None`, use `None` for unevaluated) is architecturally foreclosed: the boundary type propagates as an interior field constraint through a chain that has no architectural representation.**

**Falsifiable in three steps:**

1. `DoSleep` inherits from `float`. `self.sleep(do)` in `Retrying.__call__` passes `do` directly to `time.sleep`. `DoSleep(None)` raises `TypeError: float() argument must be a string or a number, not 'NoneType'`. Therefore `upcoming_sleep` must be `float`-typed at the moment `lambda rs: DoSleep(rs.upcoming_sleep)` executes.

2. `RetryCallState.__init__` sets `self.upcoming_sleep = 0.0`. `wait_none()` returns `0.0`. After `_run_wait` with a `wait_none()` strategy, `upcoming_sleep` is still `0.0`. These two states — "wait has not run" and "wait ran and returned zero" — are value-identical with no runtime distinction available.

3. By contrast: `retry_state.outcome = None` successfully encodes "no attempt yet" because `outcome` is a reference type — `None` is a valid sentinel for `Future | None`. `upcoming_sleep` is a primitive. The reference/value asymmetry lets `outcome` use None-as-sentinel while `upcoming_sleep` cannot. The asymmetry is structurally present but never named.

---

### The Dialectic

**Expert 1 — Defender**

The `DoSleep(float)` → `upcoming_sleep: float` chain is consequential because it makes the observation window fix trigger a cascade. A developer reading L10 who attempts to resolve the `after` callback ambiguity by changing `upcoming_sleep` to `float | None`:

- Changes `RetryCallState.__init__` → now `upcoming_sleep = None`
- Reaches `lambda rs: DoSleep(rs.upcoming_sleep)` — `DoSleep(None)` fails
- Must guard the lambda: `lambda rs: DoSleep(rs.upcoming_sleep or 0.0)` — but now `wait_none()` and "not evaluated" produce the same lambda behavior, re-introducing the ambiguity downstream
- Or must change `DoSleep` to wrap float rather than inherit from it — then `time.sleep(do)` fails
- Must change to `self.sleep(float(do))` or `self.sleep(do.sleep_seconds)` throughout

Each fix cascades to another. The `DoSleep(float)` inheritance is an ergonomic choice that made the interior type constraint load-bearing without marking it as such. The constraint exists; the chain that creates it is invisible; the cascade of changes required to break the chain is undiscoverable from inspection of any single location.

**Expert 2 — Attacker**

The chain is locally severable. Change the problematic lambda to `lambda rs: DoSleep(rs.upcoming_sleep if rs.upcoming_sleep is not None else 0.0)` — a two-token modification that handles None without changing `DoSleep`. Type `upcoming_sleep` as `float | None`. Add a guard wherever `upcoming_sleep` is used as a float. The claimed "architectural foreclosure" dissolves into a handful of local patches. `DoSleep` inheriting from `float` is a convenience that constrains the lambda, not the field — the lambda can be modified while leaving `DoSleep` unchanged. The chain is tight only if you refuse to modify intermediaries.

Furthermore: the coupling `DoSleep(float)` → `time.sleep(float)` applies only to the default `sleep = time.sleep`. User-provided sleep functions have their own signatures. A custom `sleep(do)` that handles `DoSleep` directly could accept any value. The constraint is not global — it's conditional on the sleep implementation.

**Expert 3 — Prober**

Expert 2's "two-token fix" corrects the crash but not the semantic problem. If `upcoming_sleep` is `float | None`, then `after` callbacks see `None` (unevaluated) instead of `0.0` (stale). Now `after` must null-check: `if rs.upcoming_sleep is not None: ...`. The observation window problem is renamed — from "is this 0.0?" to "is this None?" — but not resolved. The callback must still know that `upcoming_sleep` is None when `after` fires. Nothing communicates that.

The prober's real question: **why is `upcoming_sleep` on `retry_state` at all?** Trace every consumer:

| Consumer | Location | Phase when accessed |
|---|---|---|
| `lambda rs: DoSleep(rs.upcoming_sleep)` | `_post_stop_check_actions` | POST_WAIT (always valid) |
| `next_action` closure: `sleep = rs.upcoming_sleep` | `_post_stop_check_actions` | POST_WAIT (always valid) |
| `before_sleep` callback | user code | POST_WAIT (always valid) |
| Stop strategies that inspect sleep | user strategies | POST_WAIT (always valid) |
| `after` callback | user code | PRE_WAIT (**always invalid**) |

Every consumer except `after` accesses `upcoming_sleep` after `_run_wait` has set it. `after` is the only callback that fires before `_run_wait`. The ambiguity exists for exactly ONE consumer out of five.

The prober's structural question: **is `upcoming_sleep` on `retry_state` because external consumers legitimately need it there, or because internal framework actions needed to pass a value between stages and `retry_state` was the available carrier?** The internal consumers — the `DoSleep` lambda and the `next_action` closure — could receive the sleep value as a closed-over local if `_run_wait` were refactored to return it. They are on `retry_state` not because `retry_state` is the right home for an inter-stage coordination value, but because `retry_state` is the only object that flows through all actions and was the path of least resistance.

---

### The Transformation

| | |
|---|---|
| **Original claim** | `DoSleep(float)` forecloses typing `upcoming_sleep` as `float | None`, preventing the fix for observation window ambiguity |
| **Transformed claim** | `upcoming_sleep` is an **inter-stage coordination field** — a value the framework passes between `_run_wait` and `DoSleep`/`next_action` — that was placed on `retry_state` because `retry_state` is the only object flowing through all actions. Its exposure to `after` callbacks is **incidental**, not contractual. The `DoSleep(float)` type constraint is downstream evidence of the field's internal role (float-typed for immediate DoSleep construction), colliding with its accidental external role (visible to callbacks expecting a meaningful value). The observation window ambiguity is not caused by a missing null check — it is caused by a field serving two roles that have incompatible type requirements: internal coordination requires `float`; external disambiguation requires `float | None`. |

The gap: the original is a type-constraint story (DoSleep forces float). The transformed is a role-conflict story (one field serving two roles with incompatible type requirements). The transformation was forced by the prober asking why `upcoming_sleep` is on `retry_state` — which required tracing consumers, which revealed that only `after` encounters the field invalidly, which revealed that the field's presence on `retry_state` is an architectural convenience rather than a semantic contract.

---

### The Concealment Mechanism: Coincident-Carrier Occlusion

`retry_state` holds two structurally different categories of data with no type or naming distinction:

**Category A — Callback Surface Data**: fields that legitimately belong on a shared state object for callbacks and strategies to observe. Produced by callers or by the framework on behalf of callers. Valid at predictable points in the retry sequence: `outcome`, `attempt_number`, `idle_for`, `fn`, `args`, `kwargs`, `seconds_since_start`.

**Category B — Inter-stage Coordination Data**: fields the framework uses to pass values between its own internal action stages. They happen to be on `retry_state` because `retry_state` is passed to all actions — not because they are semantically public. Valid only after specific framework actions have run: `upcoming_sleep` (valid after `_run_wait`), `next_action` (valid after the `next_action` closure in the stop=False path).

**Coincident-Carrier Occlusion**: Category B fields are placed on the same carrier as Category A fields with no structural distinction. From outside, all fields look like Category A — legitimately public, meaningful, observable. The Category B fields' actual role (internal coordination, incidentally exposed) is invisible. Their type constraints (enforced by their internal roles) appear as simple field types rather than as propagated constraints from architectural decisions elsewhere.

**Applying it — the full field census:**

| Field | True Category | Apparent Category | "Not yet set" encoding | Ambiguous? |
|---|---|---|---|---|
| `outcome` | Boundary (caller → framework) | Callback surface | `None` (reference type) | No |
| `attempt_number` | Strategy context | Callback surface | `1` (first attempt) | No |
| `idle_for` | Cumulative metric | Callback surface | `0.0` (valid: no sleep yet) | No |
| `upcoming_sleep` | **Inter-stage coordination** | Callback surface (false) | `0.0` **= same as wait_none()** | **Yes** |
| `next_action` | **Inter-stage coordination** | Callback surface (false) | `None` (branch-conditional) | Partially |
| `start_time` | Measurement anchor | Callback surface | Set in `__init__`, always valid | No |
| `retry_object` | Back-reference | Configuration access | Set in `__init__`, always valid | No — but mutable |
| `fn`, `args`, `kwargs` | Call metadata | Callback surface | `None`/`()`/`{}` (iter mode) | Yes (`fn=None`) |

`upcoming_sleep` is the only field where the "not yet set" encoding (`0.0`) is value-identical to a valid evaluated result (`wait_none()` → `0.0`). This is not coincidence — it is the direct consequence of the field's internal role (must be `float` for `DoSleep`) colliding with its accidental external position (readable by callbacks who cannot distinguish the two states).

`next_action` escapes this specific problem because its "not yet set" encoding is `None` — a reference type can safely use None as a sentinel. But `next_action` has a different concealment: it's only non-None on the `stop_run_result=False` path, making its validity branch-conditional rather than phase-conditional. Callbacks that encounter `next_action` on the stop=True path (which they cannot — no callback runs there except `retry_error_callback`) would see None. The branch-conditionality is invisible for the same reason as the phase-conditionality: Coincident-Carrier Occlusion makes all fields appear uniformly available.

---

### Engineering the Concealment-Deepening Improvement

Add a `RetryStateView` — a named accessor that organizes `retry_state` fields into a documented, category-organized view, making inter-stage coordination fields appear to be first-class public API:

```python
class RetryStateView:
    """Structured access to retry execution state.

    Provides named, documented access to retry state organized by semantic
    category. Use in callbacks and strategies for self-documenting access.

    Fields reflect current state at the moment of access. Fields that have
    not yet been determined for this retry cycle return their default values.

    Example::

        def my_after_callback(retry_state):
            v = retry_state.view
            print(f"Attempt {v.attempt} failed after {v.elapsed:.1f}s")
            if v.upcoming_sleep_seconds > 5:
                alert("Long retry delay detected")
    """

    __slots__ = ("_state",)

    def __init__(self, state: "RetryCallState"):
        self._state = state

    # ── Attempt Identity ──────────────────────────────────────────────────────
    @property
    def attempt(self) -> int:
        """1-indexed attempt number for the most recent attempt."""
        return self._state.attempt_number

    @property
    def elapsed(self) -> float:
        """Wall-clock seconds since the retry sequence began."""
        return time.monotonic() - self._state.start_time

    @property
    def total_slept(self) -> float:
        """Cumulative seconds slept across all completed wait intervals."""
        return self._state.idle_for

    # ── Attempt Outcome ───────────────────────────────────────────────────────
    @property
    def outcome(self):
        """Future representing the most recent attempt's result or exception."""
        return self._state.outcome

    @property
    def exception(self) -> "BaseException | None":
        """Exception from most recent attempt, or None if it succeeded."""
        o = self._state.outcome
        return o.exception() if o is not None and o.failed else None

    # ── Scheduling ────────────────────────────────────────────────────────────
    @property
    def upcoming_sleep_seconds(self) -> float:
        """Sleep duration the engine will use before the next attempt.

        Reflects the wait strategy's decision for the current retry cycle.
        Returns 0.0 before the wait strategy has evaluated for this cycle.
        """
        return self._state.upcoming_sleep

    @property
    def next_action(self):
        """RetryAction describing the upcoming retry, or None if not yet set."""
        return self._state.next_action


# Attached to RetryCallState:
@property
def view(self) -> RetryStateView:
    """Structured, documented view of current retry state."""
    return RetryStateView(self)
```

This passes code review: `RetryStateView` provides organized, named, documented field access; properties are self-descriptive; the example in the docstring demonstrates idiomatic use in `after` callbacks; category sections (Attempt Identity, Attempt Outcome, Scheduling) signal intentional organization.

**It deepens the concealment**: `upcoming_sleep_seconds` carries the docstring "Returns 0.0 before the wait strategy has evaluated for this cycle." This is true — and it is the clearest statement of the observation window problem anywhere in the codebase. But it frames the problem as a normal lifecycle property of a well-designed API field: "the field has a default before it's populated." This framing conceals three things:

1. A developer reading this will check `if v.upcoming_sleep_seconds > 0: ...` to test whether wait has evaluated — but `wait_none()` returns `0.0`, so this check fails on the most common production wait strategy. The docstring correctly describes the 0.0 default without revealing that 0.0 is also a valid evaluated result.

2. The 0.0 default is not a design choice for `RetryStateView` — it's inherited from the `float` type constraint imposed by `DoSleep`. The docstring implies the field was designed with this default; it was actually constrained by an upstream architectural decision in a different part of the codebase.

3. The only callback that encounters the 0.0 default due to phase is `after`. The docstring is written for general use — any callback, any phase — which suggests the 0.0 default is a general concern. In reality it is a trap for exactly one callback type that the example in the docstring demonstrates using `upcoming_sleep_seconds`.

The `RetryStateView` promotes `upcoming_sleep` from an undocumented field to a named, documented, category-organized property — which makes it appear to be a first-class public API contract. The Coincident-Carrier Occlusion is deepened: the field that was accidentally on the public surface is now explicitly documented there, making its true role (internal inter-stage coordination) permanently invisible.

---

### Three Properties Visible Only Because We Tried to Strengthen It

**1. The "Scheduling" section contains fields with mutually incompatible availability guarantees.**

When writing `RetryStateView`, we must place `upcoming_sleep` and `next_action` in semantic categories. Both land in "Scheduling." But documenting them forces identifying their actual availability:

- `upcoming_sleep`: valid after `_run_wait` (POST_WAIT phase)
- `next_action`: valid after the `next_action` closure in `_post_stop_check_actions` — but ONLY on the stop=False path. On the stop=True path, no `next_action` closure runs and `retry_state.next_action` remains `None`.

`next_action` is branch-conditional, not just phase-conditional. Writing its docstring — "RetryAction describing the upcoming retry, **or None if not yet set**" — conceals that "not yet set" includes two structurally different cases: (a) `_post_stop_check_actions` has not run yet; (b) `_post_stop_check_actions` ran but chose the stop=True branch. Case (b) is permanent: no subsequent action will set `next_action` when stop=True. The callback cannot distinguish "will be set later" from "will never be set on this path." Writing the view property forced a docstring decision that reveals the branch-conditional validity problem — which is structurally identical to the phase-conditional validity problem but involves branches rather than phases. Both are invisible from outside; writing the view made both visible by forcing documentation.

**2. `upcoming_sleep_seconds` cannot be typed correctly without surfacing the `DoSleep(float)` constraint.**

When writing the `upcoming_sleep_seconds` property, the obvious return type annotation is `float`. But the semantics require distinguishing "not yet evaluated" from "evaluated to 0.0." The correct return type is `float | None` — where `None` means unevaluated. Writing `-> float | None` forces the question: what does `RetryStateView.upcoming_sleep_seconds` return when `upcoming_sleep == 0.0`? The view wraps `self._state.upcoming_sleep` — it cannot distinguish the cases. To return `None` for "not yet evaluated," it would need an `is_wait_evaluated()` method on `RetryCallState`. Adding that method requires either a separate flag or checking `upcoming_sleep >= 0` with a negative sentinel. Both require changing `RetryCallState`.

Writing the property type annotation surfaces the full chain: `-> float | None` requires a separate validity flag, which requires changing `RetryCallState`, which requires a non-zero sentinel, which must be float-compatible (for `DoSleep`), which means negative sentinel or NaN. The type annotation of the view property is a one-step derivation to the root problem — but only if you try to annotate correctly. The improvement made the chain visible by forcing type annotation decisions that expose the structural constraint.

**3. The view's "Scheduling" section fields are written by the framework, not by strategies — but the distinction is invisible.**

`upcoming_sleep` is set by `_run_wait`, not by the wait strategy. The wait strategy returns a value; `_run_wait` writes it to `retry_state.upcoming_sleep`. Writing the docstring "Reflects the **wait strategy's** decision" implies the strategy populates the field directly. It does not. A custom wait strategy that writes `retry_state.upcoming_sleep = 5.0` directly — bypassing the return-value protocol — would work (the field is plain-writable) but would also be called before `_run_wait` reads `self.wait(retry_state)` and overwrites the field. The strategy's direct write would be silently overwritten.

Similarly: a stop strategy that writes `retry_state.upcoming_sleep = 0.0` to "cancel" the wait would be silently overwritten if `_run_stop` runs after `_run_wait` (it does). Writing the view docstring required describing the contract — which required identifying who actually writes the field — which revealed that the field write is mediated by framework internals rather than strategies directly. The framework/strategy write boundary is invisible in the original code; writing the view made it visible by forcing contract documentation.

---

### The Contradicting Second Improvement

Remove `upcoming_sleep` from `retry_state` entirely. Thread it internally through closed-over locals. Expose sleep duration to callbacks via a typed event object:

```python
class SleepScheduledEvent:
    """Passed to before_sleep callbacks when a sleep interval has been determined.

    All fields are valid at the before_sleep callback's firing point.
    `sleep_seconds` is always non-negative and represents the actual
    duration that will be passed to the sleep function.
    """

    def __init__(self, retry_state: "RetryCallState", sleep_seconds: float):
        self._state = retry_state
        self.sleep_seconds = sleep_seconds  # always valid, always >= 0.0

    # Read-through for standard retry_state fields
    @property
    def attempt_number(self) -> int:
        return self._state.attempt_number

    @property
    def outcome(self):
        return self._state.outcome

    @property
    def idle_for(self) -> float:
        return self._state.idle_for

    # Write-through for callbacks that need to mutate state
    def __setattr__(self, name, value):
        if name in ("_state", "sleep_seconds"):
            object.__setattr__(self, name, value)
        else:
            setattr(self._state, name, value)


class BaseRetrying:
    def _run_wait(self, retry_state):
        # No longer writes to retry_state. Stores in iter_state.
        sleep = self.wait(retry_state) if self.wait else 0.0
        self.iter_state.planned_sleep = max(0.0, float(sleep))

    def _post_stop_check_actions(self, retry_state):
        if self.iter_state.stop_run_result:
            # ... stop path: planned_sleep never exposed externally ...
            return

        sleep = self.iter_state.planned_sleep  # closed over

        def next_action(rs):
            rs.idle_for += sleep
            rs.next_action = RetryAction(sleep)
            self.statistics["idle_for"] += sleep
            self.statistics["attempt_number"] += 1

        self._add_action_func(next_action)

        if self.before_sleep is not None:
            def before_sleep_dispatch(rs):
                event = SleepScheduledEvent(rs, sleep)
                self.before_sleep(event)   # typed: sleep_seconds always valid
            self._add_action_func(before_sleep_dispatch)

        self._add_action_func(lambda rs: DoSleep(sleep))  # local closure, not rs.upcoming_sleep
```

This passes code review independently: `upcoming_sleep` no longer exists on `retry_state` — removing the ambiguous field from the callback surface; `SleepScheduledEvent` gives `before_sleep` typed access with a `sleep_seconds` field that is always valid at the callback's firing point; `after` callbacks that attempt `retry_state.upcoming_sleep` get `AttributeError` immediately rather than silent 0.0; `DoSleep(sleep)` uses a closed-over local — no dependency on any `retry_state` field type.

**How it contradicts Improvement 1:**

Improvement 1 (`RetryStateView`) promotes `upcoming_sleep` to a documented first-class property, making it appear to be a stable public API field. Improvement 2 removes `upcoming_sleep` from `retry_state` entirely, making any access to it a runtime error. These are directly incompatible: Improvement 1 accepts `upcoming_sleep` as a legitimate callback surface field; Improvement 2 denies its legitimacy and eliminates it.

More fundamentally: Improvement 1 preserves the callback interface `(retry_state) -> None` unchanged — callbacks still receive `retry_state` and read whatever fields they want. Improvement 2 changes `before_sleep`'s effective interface from `(retry_state) -> None` to `(SleepScheduledEvent) -> None`, breaking every existing `before_sleep` callback. This is a breaking change to the public API that Improvement 1 explicitly avoids. The two improvements have opposite positions on whether the callback interface should be preserved or specialized.

---

### The Structural Conflict

Both improvements are legitimate:

- Improvement 1 (RetryStateView): addresses real usability needs. Callbacks that legitimately read `upcoming_sleep` in `before_sleep` (where it is always valid) deserve organized, documented access. The field is appropriate to expose — for that callback. Making it legible serves real users.

- Improvement 2 (remove upcoming_sleep): addresses real architectural integrity. An inter-stage coordination field should not be on the public callback surface. Its type constraint (`float`, not `float | None`) is forced by its internal role, not by external contract requirements. Removing it eliminates the ambiguity at its source.

**The structural conflict that exists only because both are legitimate:**

`upcoming_sleep` is appropriate to expose to `before_sleep` callbacks (POST_WAIT, always valid there) and inappropriate to expose to `after` callbacks (PRE_WAIT, always stale there). Both populations use `retry_state`. Improvement 1 serves the first population; Improvement 2 protects the second. A field cannot be simultaneously "should be on retry_state" and "should not be on retry_state" — unless exposure is conditional on which callback is running.

The single carrier (`retry_state`) forces a global decision on a field whose appropriate exposure is local (phase-dependent). If callbacks received phase-specific objects rather than a universal carrier, there would be no conflict: `before_sleep` callbacks would receive an object with `upcoming_sleep`; `after` callbacks would receive an object without it. The conflict exists because the single carrier makes field exposure a global property. Both improvements are locally correct for their intended population and globally incompatible because there is only one global decision to make.

---

### The Third Improvement That Resolves the Conflict

Wrap `retry_state` in a phase-specific proxy that permits access only to fields valid at the callback's firing point. The proxy is write-passthrough and type-compatible with `RetryCallState`:

```python
class PhaseFilteredState:
    """A proxy for RetryCallState that raises AttributeError for fields
    that have not yet been determined at the current callback's firing point.

    Write operations pass through to the underlying RetryCallState unchanged,
    preserving the ability of callbacks to influence subsequent strategy
    evaluations through retry_state mutation.

    Raises AttributeError immediately when a callback reads a field whose
    strategy evaluation has not yet run — making observation window violations
    visible during development rather than silently returning stale values.
    """

    __slots__ = ("_state", "_available")

    _AFTER_AVAILABLE = frozenset({
        "attempt_number", "outcome", "outcome_timestamp", "start_time",
        "idle_for", "fn", "args", "kwargs", "retry_object",
    })
    _BEFORE_SLEEP_AVAILABLE = _AFTER_AVAILABLE | frozenset({
        "upcoming_sleep", "next_action",
    })

    def __init__(self, state: RetryCallState, available: frozenset):
        object.__setattr__(self, "_state", state)
        object.__setattr__(self, "_available", available)

    def __getattr__(self, name: str):
        available = object.__getattribute__(self, "_available")
        if name not in available:
            raise AttributeError(
                f"{name!r} is not available at this callback's firing point. "
                f"It is set by a strategy evaluation that runs after this callback. "
                f"Available fields: {sorted(available)}"
            )
        return getattr(object.__getattribute__(self, "_state"), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_state"), name, value)


class BaseRetrying:
    def _post_retry_check_actions(self, retry_state):
        if not (self.iter_state.is_explicit_retry or self.iter_state.retry_run_result):
            self._add_action_func(lambda rs: rs.outcome.result())
            return
        if self.after is not None:
            after_view = PhaseFilteredState(
                retry_state, PhaseFilteredState._AFTER_AVAILABLE
            )
            self._add_action_func(lambda rs, v=after_view: self.after(v))
        self._add_action_func(self._run_wait)
        self._add_action_func(self._run_stop)
        self._add_action_func(self._post_stop_check_actions)

    def _post_stop_check_actions(self, retry_state):
        # ... stop-true branch ...
        if self.before_sleep is not None:
            sleep_view = PhaseFilteredState(
                retry_state, PhaseFilteredState._BEFORE_SLEEP_AVAILABLE
            )
            self._add_action_func(lambda rs, v=sleep_view: self.before_sleep(v))
        self._add_action_func(lambda rs: DoSleep(rs.upcoming_sleep))
```

This passes code review: `after` callbacks receive `PhaseFilteredState` with `_AFTER_AVAILABLE` — attempting `upcoming_sleep` raises `AttributeError` with an explanatory message; `before_sleep` callbacks receive a view that includes `upcoming_sleep` (valid at that phase); write-passthrough preserves the influence pathway that L10 identified as essential; backward-compatible for any callback that only reads valid fields.

---

### How the Third Improvement Fails

`PhaseFilteredState._AFTER_AVAILABLE` and `_BEFORE_SLEEP_AVAILABLE` are static class-level `frozenset` constants. They must be manually synchronized with the dynamic action ordering in `_post_retry_check_actions` and `_post_stop_check_actions`.

**The immediate failure:** `after_view` is constructed inside `_post_retry_check_actions` — a routing node that runs DURING iteration. The view wraps the live `retry_state` object. When `after_view.__getattr__("upcoming_sleep")` is called by an `after` callback, it checks membership in the static `_AFTER_AVAILABLE` set, finds `upcoming_sleep` absent, and raises `AttributeError`. But the proxy checks static policy, not dynamic state. If `_run_wait` had somehow already executed by the time `after` fires (e.g., because a developer reordered the actions added in `_post_retry_check_actions` to move `self._run_wait` before `self.after`), the proxy would still raise `AttributeError` — because the static constant was not updated. The proxy enforces a phase contract encoded in a frozen constant rather than derived from the actual ordering.

Conversely: if the static constant `_AFTER_AVAILABLE` were updated to include `upcoming_sleep` (perhaps by a well-intentioned developer who wants `after` to have access to it), the proxy would permit the read — but `_run_wait` might not have run. The static constant diverges from the action ordering, in either direction, with no detection mechanism.

**The deeper failure:** `after_view` wraps `retry_state` by reference, not by snapshot. After `_post_retry_check_actions` runs and `after_view` is captured in the lambda, the iteration loop continues: `_run_wait` executes and sets `retry_state.upcoming_sleep = 5.0`. If the `after` callback were somehow called again (hypothetically), `after_view.__getattr__("upcoming_sleep")` would still raise `AttributeError` — but the underlying `retry_state.upcoming_sleep` is now `5.0`. The proxy enforces a policy made at construction time against a live object that has since advanced. The view is not a snapshot of the state; it is a filter whose validity is time-indexed at construction but applied at access time.

---

### What the Failure Reveals About the Design Space

The structural conflict appeared to be a field exposure problem: `upcoming_sleep` should be visible to some callbacks and not others. The third improvement resolved this by phase-filtering per callback. Its failure reveals that this framing is incomplete.

**The canonical representation of "which fields are valid for which callback" is the action ordering in `_post_retry_check_actions` and `_post_stop_check_actions`.** The ordering encodes: `after` fires before `_run_wait` (so `upcoming_sleep` is pre-evaluation); `before_sleep` fires after `_run_wait` and `_run_stop` (so both are post-evaluation). This is the single source of truth for observation window contracts. Every other representation — `_AFTER_AVAILABLE`, `_BEFORE_SLEEP_AVAILABLE`, property docstrings, `RetryStateView` categories — is a **copy** of the canonical ordering. Copies diverge.

The design space constraint: **there is no mechanism by which a static representation of field validity can remain synchronized with a dynamic action ordering without becoming the ordering itself.** Becoming the ordering itself means using the ordering as the specification — which returns to the original problem (the ordering is invisible, assembled during execution, and unreadable before it completes).

The conflict between Improvement 1 and Improvement 2 was: expose the field (to serve before_sleep) vs. hide it (to protect after). This appeared to be a field-scope decision. The third improvement's failure reveals the deeper constraint: **field validity is phase-indexed by the action ordering, and any external representation of phase-indexed validity is a dependent artifact that diverges from the ordering when the ordering changes.** The conflict cannot be resolved by choosing which callbacks see which fields — because the specification of "which callbacks see which fields" cannot be maintained independently of the ordering that generates it.

What the structural conflict alone could not show: the observation window is not just invisible — it is the ONLY canonical specification of field validity. There is no alternative home for this information. Any attempt to duplicate it elsewhere (static constants, proxy field sets, type annotations, property docstrings) creates a divergence problem. The design space does not contain a solution where field validity is simultaneously (a) explicit and readable before execution, (b) automatically synchronized with execution ordering, and (c) enforced without changing the callback interface. Any two of these three can be satisfied; all three cannot.

---

### The Redesign: Inhabiting the Topology

**Accepted topology:**
- `retry_state` is the unified carrier; the callback interface is `(retry_state) -> None`
- Field validity is encoded in action ordering, which cannot be copied without divergence
- `DoSleep(float)` constrains `upcoming_sleep: float`, preventing `None` as sentinel
- Callbacks need runtime visibility into which fields are phase-valid

**Feasible point**: replace the `0.0` initialization of `upcoming_sleep` with a negative sentinel value that is type-compatible with `float` (satisfying `DoSleep(float)`) but physically distinct from any valid sleep duration:

```python
class RetryCallState:
    _SLEEP_NOT_YET_SCHEDULED: float = -1.0
    """Sentinel: wait strategy has not evaluated for this cycle.
    
    Negative values are never valid sleep durations. After _run_wait
    executes, upcoming_sleep is always >= 0.0. Callbacks can test
    `retry_state.upcoming_sleep < 0` to determine whether wait has
    evaluated, without requiring a separate boolean flag.
    """

    def __init__(self, retry_object, fn, args, kwargs):
        ...
        self.upcoming_sleep: float = self._SLEEP_NOT_YET_SCHEDULED

    @property
    def sleep_scheduled(self) -> bool:
        """True after the wait strategy has evaluated for this retry cycle."""
        return self.upcoming_sleep >= 0.0

    @property
    def scheduled_sleep(self) -> "float | None":
        """Sleep duration from wait strategy, or None if not yet evaluated."""
        return self.upcoming_sleep if self.sleep_scheduled else None


class BaseRetrying:
    def _run_wait(self, retry_state):
        sleep = self.wait(retry_state) if self.wait else 0.0
        retry_state.upcoming_sleep = max(0.0, float(sleep))  # always non-negative post-evaluation
```

The sentinel `-1.0` satisfies `DoSleep(float)` as a type but is never a valid sleep argument — `DoSleep(-1.0)` would produce a `DoSleep` with value `-1.0`, which is nonsensical as a sleep duration. But `DoSleep(rs.upcoming_sleep)` runs AFTER `_run_wait`, at which point `upcoming_sleep >= 0.0`. The lambda is never called with the sentinel value. `after` callbacks can now test `retry_state.sleep_scheduled → False` to confirm wait has not yet evaluated. `wait_none()` returning `0.0` is distinguishable from "not yet evaluated" (`-1.0`). The ambiguity L10 identified is resolved without changing `DoSleep`'s type, without changing the callback interface, and without any proxy or phase-filter.

**What it sacrifices:**

1. **The invariant that `upcoming_sleep` is always a valid sleep duration.** Between `__init__` and `_run_wait`, `upcoming_sleep = -1.0`. Any code path that reads `upcoming_sleep` and uses it for sleep without checking `sleep_scheduled` first would pass `-1.0` to `time.sleep`. Python 3.11+ accepts negative values to `time.sleep` (treats as 0.0); earlier versions raise `ValueError: sleep length must be non-negative`. The sentinel is type-safe but runtime-unsafe in the wrong phase — which is exactly the problem it documents, now with a new failure mode (ValueError rather than silently wrong 0.0).

2. **Composability with wait-none as default.** `wait_none()` returns `0.0`. The sentinel changes the "unset" value from `0.0` to `-1.0`, so `wait_none()` is no longer indistinguishable from "not evaluated." But a developer who was checking `upcoming_sleep == 0.0` as a proxy for "wait not evaluated" now gets correct behavior. The sentinel removes one false equivalence at the cost of requiring explicit checking.

3. **The guarantee that every `float` field on `retry_state` is always a valid value for its semantic type.** The sentinel `_SLEEP_NOT_YET_SCHEDULED = -1.0` introduces a distinguished invalid float value that the framework must not pass to sleep functions. This is an implicit precondition that callers of `time.sleep` must respect, enforced by documentation convention rather than type. It is the same kind of "value as marker" pattern that the analysis has been criticizing — applied as the fix.

**What in the original design was never a flaw:**

`upcoming_sleep = 0.0` in `RetryCallState.__init__` was never a flaw. It was the cost of attempting four properties simultaneously:

1. **Float-typed throughout**: `upcoming_sleep: float` at all times, enabling `DoSleep(rs.upcoming_sleep)` with no null-check
2. **Zero-cost initialization**: no sentinel logic, no flag, just the natural float default  
3. **wait_none composability**: `wait_none()` returns `0.0` — the same as the initialized value — enabling `wait_none()` to require no special handling
4. **Phase-transparent callbacks**: callbacks receive `retry_state` directly, reading whatever they access without any filtering or guard

These four requirements have exactly one solution for `upcoming_sleep`'s initialization: `0.0`. It is the only value that satisfies all four simultaneously — it is float-typed (satisfying 1), is a natural default (satisfying 2), equals `wait_none()` (satisfying 3), and requires no special guard on the callback side (satisfying 4). The "flaw" — that `0.0` cannot distinguish "wait not run" from "wait returned zero" — is the cost of making all four properties simultaneously true.

The redesign (`-1.0` sentinel) achieves (1), partially achieves (2) and (3), and partially sacrifices (4) — callbacks that read `upcoming_sleep` now must check `sleep_scheduled` to avoid the sentinel, which is a form of implicit phase tracking embedded in read-time null checking. The redesign achieves disambiguation by introducing a per-read precondition — proving that eliminating the ambiguity IS eliminating part of the simplicity that generated it.

`DoSleep(float)` — which opened this analysis — was similarly never a flaw. It was the cost of transparent float delegation: `time.sleep(do)` rather than `time.sleep(do.value)`. That delegation propagated a type constraint (`upcoming_sleep: float`) into the interior through a chain with no architectural representation. The propagation went unnoticed because the constraint was already being satisfied — accidentally, by the `0.0` initialization that was chosen for entirely different reasons. The original design's three choices — `DoSleep(float)`, `upcoming_sleep = 0.0`, `wait_none() → 0.0` — were each individually correct for their local purpose. Their joint consequence (ambiguous sentinel) was a collective emergent property of correct local decisions whose interaction was never examined. Calling it a flaw assigns blame to a system of mutual constraints, none of which is culpable alone.
