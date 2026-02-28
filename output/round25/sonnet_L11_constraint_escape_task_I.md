# State Machine Structural Analysis

## The Claim

**`send()` performs irreversible state mutation at a point where it has already spawned uncontrollable side effects and will spawn more — making every "transition" actually three separate non-    -> Done (213s) -> 423 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/sonnet_L11_constraint_escape_task_I.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
ition, and returns — then the outer call's `history.append()` records the wrong "from" state.

This is falsifiable: write a test where `on_enter` calls `send()` and observe that history is corrupted.

---

## Three Experts

**Defender:** The re-entrancy failure is real and testable. Any callback-triggered `send()` inside `on_enter` will mutate `_state` again before the outer `send()` appends its history entry. You can reliably produce history that logs transitions out of states the machine was never in.

**Attacker:** Re-entrancy is a symptom. The *deeper* problem is that the machine's *definition* is mutable concurrent to its operation. `add_transition()` and `add_guard()` can be called at any time — including from inside a callback. The claim about mutation ordering conceals that the machine's specification and execution share the same mutable object with no separation.

**Prober:** Both of you assume `_state` *is* the machine's state. But this machine has at minimum three state representations that must stay coherent: `_state` (the current symbol), `_history` (the trajectory), and whatever external state the callbacks produced. The claim about mutation ordering takes for granted that "state" is isolable. It isn't — callbacks are allowed to have side effects, and no rollback mechanism can touch those. What *is* the state this machine claims to manage?

---

## Claim Transforms

Original claim: *mutation ordering creates consistency failures*.

After dialectic: **The machine has no model of its own execution.** It cannot observe whether it is mid-transition, it cannot distinguish "definition" from "instance," and it cannot bound the meaning of "state" to the variables it controls. The ordering failure is a symptom of the machine being unaware that it *runs*.

**The gap:** The original claim is temporal (sequencing). The transformed claim is self-referential (the machine cannot represent its own execution context).

---

## Concealment Mechanism

**Functional decomposition that mimics separation of concerns.**

Five dictionaries — `_transitions`, `_guards`, `_on_enter`, `_on_exit`, `_history` — appear to cleanly separate concerns. This hides that all five must coordinate in strict order during every `send()` call, and that coordination is expressed solely as statement ordering inside a single method. The dictionary structure makes each concern look independent. The `send()` method reveals they are monolithically coupled during execution, but the data structure design actively conceals this.

---

## Improvement That Deepens Concealment

```python
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
import time

@dataclass
class TransitionContext:
    """Encapsulates all transition data for clean callback signatures."""
    from_state: str
    to_state: str
    event: str
    data: Any
    timestamp: float = field(default_factory=time.time)

class StateMachine:
    def __init__(self, initial_state: str):
        self._state = initial_state
        self._transitions: dict = {}
        self._guards: dict = {}
        self._on_enter: dict = {}
        self._on_exit: dict = {}
        self._history: list = []
        self._middleware: list[Callable] = []   # Added: middleware pipeline

    def add_transition(self, from_state, event, to_state):
        self._transitions[(from_state, event)] = to_state

    def add_guard(self, from_state, event, guard_fn):
        self._guards[(from_state, event)] = guard_fn

    def on_enter(self, state, callback):
        self._on_enter[state] = callback

    def on_exit(self, state, callback):
        self._on_exit[state] = callback

    def use(self, middleware_fn: Callable):
        """Add middleware that observes every transition."""
        self._middleware.append(middleware_fn)

    def _execute_transition(self, ctx: TransitionContext):
        """Encapsulated transition lifecycle — enter, commit, notify, exit."""
        if exit_cb := self._on_exit.get(ctx.from_state):
            exit_cb(ctx)

        self._state = ctx.to_state                          # Commit
        self._history.append({                              # Record
            "from": ctx.from_state,
            "to": ctx.to_state,
            "event": ctx.event,
            "timestamp": ctx.timestamp
        })

        for mw in self._middleware:                         # Notify observers
            mw(ctx)

        if enter_cb := self._on_enter.get(ctx.to_state):
            enter_cb(ctx)

    def send(self, event, data=None):
        key = (self._state, event)
        if key not in self._transitions:
            return {"ok": False, "error": f"No transition for {event} in {self._state}"}

        guard = self._guards.get(key)
        if guard and not guard(data):
            return {"ok": False, "error": "Guard rejected transition"}

        ctx = TransitionContext(
            from_state=self._state,
            to_state=self._transitions[key],
            event=event,
            data=data
        )
        self._execute_transition(ctx)
        return {"ok": True, "from": ctx.from_state, "to": ctx.to_state}
```

This passes code review because: `TransitionContext` looks like domain modeling; `_execute_transition` looks like single-responsibility extraction; `use()` looks like extensible middleware. Each is a recognizable pattern.

**Why it deepens concealment:** The method name `_execute_transition` asserts atomicity it does not provide. The `TransitionContext` dataclass suggests the transition is a first-class value — but it's read-only during execution; nothing can pause or replay it. The middleware pipeline (`_middleware`) runs *after* state mutation but *before* `on_enter`, adding a third implicit ordering phase that looks like observability but is actually another sequencing dependency with the same re-entrancy hazard.

---

## Three Properties Visible Only Because We Strengthened It

**1. The transition holds no reference to itself while executing.**  
`TransitionContext` is passed *to* callbacks but the machine holds no reference to the in-progress context. A re-entrant `send()` inside `on_enter(ctx)` cannot detect there is already a `ctx` in flight. The improvement created a value object that *looks* like it represents the transition, but the transition has no self-knowledge.

**2. The mutation point is non-negotiable — only its neighbors are negotiable.**  
`self._state = ctx.to_state` must appear somewhere in `_execute_transition`. Moving it before the exit callback, after middleware, after enter callback — these are the only degrees of freedom. The mutation itself cannot be conditional, deferred, or two-phase within this structure. Naming the method forced the decision to be visible.

**3. History and state are siblings with no parent.**  
In the original, `_history.append()` and `self._state = new_state` appeared sequentially in `send()`. The extraction to `_execute_transition` shows they are co-updated manually with no derivation relationship. History doesn't *follow from* state — it must be explicitly maintained alongside it. Any divergence (exception between the two lines) creates permanent incoherence.

---

## Diagnostic on the Improvement

**What it conceals:** `_execute_transition` suggests a completed, bounded operation. It hides that after it returns, `self._state` might not equal `ctx.to_state` — if `on_enter` called `send()` re-entrantly, the machine executed further transitions inside the call and the outer `send()` is unaware. The method name claims encapsulation it does not provide.

**Property of the original problem that the improvement recreates:**  
The improvement forces an explicit decision about where `self._state = ctx.to_state` lives. This reveals: **there is no principled placement for the mutation point**. Before `on_exit`: callbacks see stale state. After `on_enter`: enter callback runs in the wrong state. In the middle (as implemented): both callbacks run in their correct state, but re-entrant calls see committed state mid-transition. There is no position that is correct. The improvement makes this forced choice undeniable.

---

## Second Improvement: Address the Mutation Point

The recreated property: *the mutation point has no principled position because `_state` is committed in the same call frame as callbacks that can re-enter.*

Fix: serialize all events so re-entrant `send()` calls are queued, not nested.

```python
from collections import deque

class StateMachine:
    def __init__(self, initial_state: str):
        self._state = initial_state
        self._transitions: dict = {}
        self._guards: dict = {}
        self._on_enter: dict = {}
        self._on_exit: dict = {}
        self._history: list = []
        self._queue: deque = deque()
        self._processing: bool = False

    def add_transition(self, from_state, event, to_state):
        self._transitions[(from_state, event)] = to_state

    def add_guard(self, from_state, event, guard_fn):
        self._guards[(from_state, event)] = guard_fn

    def on_enter(self, state, callback):
        self._on_enter[state] = callback

    def on_exit(self, state, callback):
        self._on_exit[state] = callback

    def send(self, event, data=None):
        self._queue.append((event, data))
        if self._processing:
            return {"ok": True, "queued": True}      # Re-entrant: deferred
        return self._drain()

    def _drain(self):
        self._processing = True
        last = None
        try:
            while self._queue:
                event, data = self._queue.popleft()
                last = self._step(event, data)
        finally:
            self._processing = False
        return last

    def _step(self, event, data):
        key = (self._state, event)
        if key not in self._transitions:
            return {"ok": False, "error": f"No transition for {event} in {self._state}"}

        guard = self._guards.get(key)
        if guard and not guard(data):
            return {"ok": False, "error": "Guard rejected"}

        old_state, new_state = self._state, self._transitions[key]

        if exit_cb := self._on_exit.get(old_state):
            exit_cb(old_state, event, data)

        self._state = new_state
        self._history.append({"from": old_state, "to": new_state, "event": event})

        if enter_cb := self._on_enter.get(new_state):
            enter_cb(new_state, event, data)

        return {"ok": True, "from": old_state, "to": new_state}
```

---

## Diagnostic on the Second Improvement

**What it conceals:** `send()` now has two distinct return types — a real transition result, or `{"ok": True, "queued": True}`. The latter is not a result; it's an acknowledgment. Callers cannot inspect whether a queued event was rejected by a guard, succeeded, or caused an error. The queue makes re-entrancy safe but destroys the causal chain between event dispatch and outcome.

**Property of the original problem recreated:** The second improvement reveals: **`send()` conflates event dispatch with event result.** The original code asserted these were the same (dispatch → execute → return result). The queue makes them visibly different: dispatch happens at call time, execution happens at drain time, and results are only available to the draining frame. The machine was always pretending dispatch-and-result were atomic. The queue makes this pretense explicit as a `{"queued": True}` lie.

---

## The Structural Invariant

Every improvement preserves: **`send()`'s return value is computed at dispatch time, encoding the result of execution that spans callback side-effects that are not bounded by `send()`'s return.**

More precisely: **The machine cannot distinguish between "a transition was initiated" and "a transition completed."** Every implementation implicitly equates them. This invariant survives because:

1. Callbacks are executed inside `send()`'s call frame
2. Callbacks can have unbounded side effects
3. The return value must be computed in that same frame
4. The return value must therefore lie about completion — it can only report initiation

This is not fixable by reordering statements, adding context objects, or queuing events. Every improvement that preserves "callbacks are callables invoked during `send()`" preserves the invariant.

---

## The Category

This invariant defines the category of **synchronous-effect state machines**: machines where transitions, callbacks, and return values share a single execution context. The invariant is:

> **Effect ordering is expressed as statement ordering within a single mutable execution frame.**

Every design in this category — however well-refactored — is bounded by this property. Re-entrancy safety, context objects, middleware pipelines, history recording: all are rearrangements within the same frame.

---

## The Adjacent Category: Pure Specification Machines

The invariant dissolves when **`send()` returns a description of what should happen, rather than executing it.** The machine becomes a pure function from (state, event) to (next-state, effects-as-values). An external interpreter owns all mutation and effect execution.

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Union

# ── Effects as values, not callables ────────────────────────────────────────

@dataclass(frozen=True)
class Effect:
    name: str
    payload: Any = None

@dataclass(frozen=True)
class Transition:
    next_state: str
    effects: tuple[Effect, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class Rejection:
    current_state: str
    event: str
    reason: str

# ── Pure machine: a specification, not an executor ───────────────────────────

class MachineSpec:
    """Immutable. Pure function from (state, event) → Transition | Rejection."""

    def __init__(self,
                 transitions: dict,
                 guards: dict | None = None,
                 effects: dict | None = None):
        self._transitions = dict(transitions)          # (from, event) → to
        self._guards = dict(guards or {})              # (from, event) → predicate
        self._effects = dict(effects or {})            # (from, event, to) → [Effect]

    def step(self,
             current_state: str,
             event: str,
             data: Any = None) -> Union[Transition, Rejection]:
        """Pure. No mutation. No side effects. Returns a value."""
        key = (current_state, event)

        if key not in self._transitions:
            return Rejection(current_state, event,
                             f"No transition for '{event}' in '{current_state}'")

        guard = self._guards.get(key)
        if guard and not guard(data):
            return Rejection(current_state, event, "Guard rejected")

        next_state = self._transitions[key]
        effects = self._effects.get((current_state, event, next_state), ())
        return Transition(next_state=next_state, effects=tuple(effects))

# ── Interpreter: owns all mutation and effect execution ──────────────────────

class Interpreter:
    """Stateful. Executes plans from a MachineSpec. Completely separate."""

    def __init__(self,
                 spec: MachineSpec,
                 initial_state: str,
                 handlers: dict[str, Callable]):
        self._spec = spec
        self._state = initial_state
        self._history: list = []
        self._handlers = handlers    # effect name → callable

    @property
    def state(self) -> str:
        return self._state

    def send(self, event: str, data: Any = None) -> dict:
        result = self._spec.step(self._state, event, data)

        if isinstance(result, Rejection):
            return {"ok": False, "error": result.reason}

        # All mutation is here, by explicit decision, not statement ordering.
        old_state = self._state
        self._state = result.next_state
        self._history.append({
            "from": old_state,
            "to": result.next_state,
            "event": event
        })

        # Effects execute after state is committed — by design, transparently.
        for effect in result.effects:
            handler = self._handlers.get(effect.name)
            if handler:
                handler(effect.payload)

        return {"ok": True, "from": old_state, "to": result.next_state}
```

**Usage:**

```python
spec = MachineSpec(
    transitions={
        ("locked",   "coin",  "unlocked"),
        ("unlocked", "push",  "locked"),
        ("unlocked", "coin",  "unlocked"),
    },
    effects={
        ("locked",   "coin", "unlocked"): [Effect("unlock_hardware")],
        ("unlocked", "push", "locked"):   [Effect("lock_hardware"),
                                           Effect("log_passage")],
    }
)

interpreter = Interpreter(spec, "locked", handlers={
    "unlock_hardware": lambda _: print("Click!"),
    "lock_hardware":   lambda _: print("Clunk!"),
    "log_passage":     lambda _: print("Passage logged."),
})

interpreter.send("coin")   # → {"ok": True, "from": "locked", "to": "unlocked"}
interpreter.send("push")   # → {"ok": True, "from": "unlocked", "to": "locked"}
```

---

## How This Design Succeeds Where Every Improvement Failed

| Problem | Original / Improvements | Pure Spec |
|---|---|---|
| Re-entrancy | Callbacks can call `send()` — state corrupts | Handlers have no `send()` reference — structurally impossible |
| Mutation point | No principled position; hidden by statement order | Explicit: always after `step()`, always before effects |
| Machine definition mutates during execution | `add_transition()` callable anytime | `MachineSpec` is frozen after construction |
| History/state coherence | Co-updated manually, can diverge on exception | Interpreter owns both in same scope, sequential, no interleaving |
| Return value meaning | Conflates initiation with completion | `step()` returns the plan; `send()` executes and reports completion |

`MachineSpec.step()` is a pure function. It can be tested without an interpreter. It can be run in parallel against the same spec. The interpreter's mutation sequence is visible, explicit, and unchallengeable — not an artifact of statement ordering inside a callback chain.

---

## The New Impossibility

In the original category, **self-referential transitions are trivial.** An `on_enter` callback calls `send("retry")` and the machine responds immediately, cascading through further transitions. The machine is self-responsive by default — callbacks have a live reference to the machine and can drive it.

In the adjacent category, **self-referential transitions are structurally impossible.** Effect handlers are named strings resolved by the interpreter. They have no reference to the interpreter. A handler cannot call `send()`. To implement "on entering state X, automatically send event Y," you must either:

1. Return a special `AutoTransition` effect that the interpreter recognizes and re-processes, or
2. Make the interpreter explicitly recursive with a chosen re-entrancy policy, or
3. Model the auto-transition as a separate event fed back into the interpreter from outside

None of these are implicit — each requires a deliberate architectural decision that cannot be hidden inside a callback.

---

## The Finding

| | Original Category | Adjacent Category |
|---|---|---|
| **Trivial** | Self-referential transitions (callbacks call `send()`) | Atomic transitions (state + effects commit or don't) |
| **Impossible** | Atomic transitions (mutation always mid-callback) | Self-referential transitions (handlers have no machine reference) |

**The trade-off:** The original design's *feature* — that callbacks can drive the machine — is the direct cause of its *impossibility* — that transitions cannot be atomic. These are not separable. Every improvement that preserves callback-driven behavior preserves the atomicity failure.

The pure specification design achieves atomicity by removing the machine from the callback's scope. The cost is that any self-referential behavior — state X triggers event Y — must be **named**, **explicit**, and **owned by the interpreter**, not implicit in a callback's closure.

**What this reveals about the original code:** The original isn't buggy. It made an implicit choice to prioritize expressive self-reference over transaction integrity. The concealment mechanism — functional decomposition into five dictionaries — hid this as a design choice and presented it as neutral infrastructure. Every "improvement" that reorganizes the infrastructure while preserving callbacks re-conceals the same choice. The only honest response is to name the trade-off and choose a side.
