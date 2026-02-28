# Structural Diagnosis: State Machine

---

## I. THE CLAIM

**Falsifiable claim:** This machine's deepest structural problem is that *callback utility and transition atomicity are mutually exclusive* within its protocol. Any callback powerful    -> Done (202s) -> 384 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/sonnet_L11_conservation_law_task_I.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
THREE EXPERTS

### Expert A — Defends the claim

The re-entrancy window is structural, not incidental. During `exit_cb`, `self._state` is still `old_state`. A re-entrant `send()` will find a valid transition from `old_state`, execute it completely — including updating `self._state` to some `intermediate_state` and appending to `_history` — and return. Then the outer `send()` resumes and executes `self._state = new_state`, overwriting `intermediate_state` silently. `_history` now records two transitions but the machine reflects only the outer one's destination. This is not a documentation problem. It is a consequence of callbacks having a reference to the live machine.

### Expert B — Attacks the claim

The atomicity framing is a distraction. The *actual* deepest problem is that callbacks have no return channel. The guard can reject a transition; the callbacks cannot. If `exit_cb` discovers that the resource it manages cannot be safely released, it has no mechanism to communicate this back to `send()`. The method returns `{"ok": True}` regardless of what the callbacks did. Re-entrancy is a misuse scenario you can document away. Silent callback failure is a *protocol* hole.

### Expert C — Probes what both assume

Both of you assume "state" means `self._state` — the scalar. But the machine's actual state includes `_transitions`, `_guards`, `_on_enter`, `_on_exit`. These are mutable at any time, before or after or *during* execution. You can call `add_transition()` from within a callback. Both of you are arguing about execution safety while ignoring that the schema itself is unstable. The deeper assumption you share: that configuration and runtime position are already separated. They are not. They live in the same object with no boundary between them.

### How the claim transforms

The original claim: *atomicity vs. callback utility*.

After Expert C's probe, the transformed claim: **The machine conflates three distinct concerns — schema (what transitions are valid), position (current state), and execution (side effects during transition) — and the absence of enforced boundaries between them means any fix to one concern reopens the other two.**

**The gap:** The original claim was about *execution order*. The transformed claim is about *category confusion*. This is deeper because atomicity problems are downstream effects of schema-runtime conflation. If schema were immutable, a re-entrant `send()` call couldn't corrupt the machine's definition — only its position. The atomicity problem is a symptom. The category confusion is the disease.

---

## III. THE CONCEALMENT MECHANISM

**Mechanism: Structural parallelism without structural coupling.**

```python
self._transitions = {}   # keyed by (state, event)
self._guards = {}        # keyed by (state, event)  ← same key type, no enforced relation
self._on_enter = {}      # keyed by state
self._on_exit = {}       # keyed by state
```

These four dictionaries look like a coherent model because they share key types and are queried together in `send()`. But they have zero mutual integrity guarantees:

- A guard can exist for a transition that doesn't exist → silently ignored
- A callback can exist for a state that's unreachable → silently ignored
- A transition can target a state with no callbacks → silently accepted
- All four can be mutated independently, at any time, by any caller

The code hides that **there is no schema** — only a bag of facts that may or may not be consistent. The named, separated dictionaries *look* organized. The organization is cosmetic. What looks like separation of concerns is separation of storage with no corresponding separation of integrity.

---

## IV. THE LEGITIMATE-LOOKING IMPROVEMENT THAT DEEPENS CONCEALMENT

This passes code review. It adds validation, co-locates guards with transitions, and introduces a fluent builder pattern:

```python
class StateMachine:
    def __init__(self, initial_state):
        self._state = initial_state
        self._states = set()
        self._transitions = {}   # (from, event) → {"to": state, "guard": fn|None}
        self._on_enter = {}
        self._on_exit = {}
        self._history = []

    def add_state(self, state, on_enter=None, on_exit=None):
        self._states.add(state)
        if on_enter:
            self._on_enter[state] = on_enter
        if on_exit:
            self._on_exit[state] = on_exit
        return self  # fluent

    def add_transition(self, from_state, event, to_state, guard=None):
        if from_state not in self._states:
            raise ValueError(f"Unknown state: {from_state}")
        if to_state not in self._states:
            raise ValueError(f"Unknown state: {to_state}")
        self._transitions[(from_state, event)] = {"to": to_state, "guard": guard}
        return self  # fluent

    def validate(self):
        if self._state not in self._states:
            raise ValueError(f"Initial state '{self._state}' not declared")
        return self

    def send(self, event, data=None):
        key = (self._state, event)
        transition = self._transitions.get(key)
        if not transition:
            return {"ok": False, "error": f"No transition for {event} in {self._state}"}

        guard = transition["guard"]
        if guard and not guard(data):
            return {"ok": False, "error": "Guard rejected transition"}

        old_state = self._state
        new_state = transition["to"]

        exit_cb = self._on_exit.get(old_state)
        if exit_cb:
            exit_cb(old_state, event, data)

        self._state = new_state
        self._history.append({"from": old_state, "to": new_state, "event": event})

        enter_cb = self._on_enter.get(new_state)
        if enter_cb:
            enter_cb(new_state, event, data)

        return {"ok": True, "from": old_state, "to": new_state}
```

**Why this passes code review:** Explicit state registration. Validation at `add_transition()`. Guard co-located with transition definition. Fluent API suggesting transactional construction.

**Why this deepens concealment:** The validation at `add_transition()` creates the *impression* of schema enforcement while leaving runtime completely unguarded. The fluent API makes construction *look* like a transaction — but the machine remains fully mutable after the first `send()`. The guard is now stored in `_transitions` rather than `_guards`, which looks like it collapsed the parallel-dict problem — but it didn't. `_on_enter` and `_on_exit` remain separate, `_states` is a third parallel structure with no enforced relationship to callbacks. The *surface area* of the coupling illusion expanded.

---

## V. THREE PROPERTIES VISIBLE ONLY BECAUSE WE TRIED TO STRENGTHEN IT

**1. The schema is never closed.**
Adding `add_state()` with validation forces the question: should `add_transition()` called *after* the first `send()` raise an error? The original never raised this question because it had no state registration. Now the absence of a "sealed" lifecycle is legible as a missing feature rather than ignorable as an implementation detail.

**2. Guards are definitionally part of transitions, not annotations on them.**
Moving `guard` into `add_transition()` reveals that in the original, guard and transition could be registered by different callers in any order. The improvement makes visible that the original treats guards as optional metadata detachable from the transition they govern — a semantics claim, not just a style choice.

**3. State identity is constructed, not intrinsic.**
Requiring `add_state()` reveals that in the original, a "state" is simply any hashable value that appears as a key or value in `_transitions`. The machine has no state concept — only transition facts. The improvement, by adding `_states`, makes visible that the original machine cannot distinguish between "state that is part of this machine's design" and "state that was a typo."

---

## VI. WHAT THE IMPROVEMENT CONCEALS, AND WHAT IT RECREATES

**What the improvement conceals:**
Validation at construction time cannot substitute for invariant enforcement at runtime. The `add_transition()` check confirms states are declared. But `send()` still:
- Does not prevent re-entrant calls during callbacks
- Does not rollback `self._state` or `_history` if a callback raises
- Returns `{"ok": True}` regardless of what callbacks did

Construction looks safe. Runtime is as exposed as before.

**The original problem property, recreated:**
The improvement recreates *registration-order-implied dependencies without enforcement*. `add_state()` must precede `add_transition()` — this is enforced. But `validate()` must precede `send()` — this is not enforced. The improvement traded one unenforceable ordering for another. The original problem: the machine has no lifecycle states, no notion of "being configured" vs. "running." The improvement makes this property *structurally conspicuous* by introducing a `validate()` method that should mark the transition but doesn't.

---

## VII. THE SECOND IMPROVEMENT

Address the lifecycle problem with a builder/runner separation:

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

@dataclass(frozen=True)
class StateConfig:
    on_enter: Optional[Callable] = None
    on_exit: Optional[Callable] = None

@dataclass(frozen=True)  
class TransitionConfig:
    to_state: str
    guard: Optional[Callable] = None

class StateMachineBuilder:
    def __init__(self, initial_state: str):
        self._initial = initial_state
        self._states: dict[str, StateConfig] = {}
        self._transitions: dict[tuple, TransitionConfig] = {}

    def state(self, name: str, on_enter=None, on_exit=None):
        self._states[name] = StateConfig(on_enter=on_enter, on_exit=on_exit)
        return self

    def transition(self, from_state: str, event: str, to_state: str, guard=None):
        if from_state not in self._states:
            raise ValueError(f"Undeclared state: {from_state}")
        if to_state not in self._states:
            raise ValueError(f"Undeclared state: {to_state}")
        self._transitions[(from_state, event)] = TransitionConfig(to_state, guard)
        return self

    def build(self) -> "StateMachine":
        if self._initial not in self._states:
            raise ValueError(f"Initial state '{self._initial}' not declared")
        # Schema is frozen at build time — no further mutations possible
        return StateMachine(
            initial_state=self._initial,
            states=dict(self._states),
            transitions=dict(self._transitions),
        )

class StateMachine:
    def __init__(self, initial_state, states, transitions):
        self._state = initial_state
        self._states = states        # frozen: no add_state() post-build
        self._transitions = transitions  # frozen: no add_transition() post-build
        self._history: list = []

    def send(self, event, data=None):
        key = (self._state, event)
        transition = self._transitions.get(key)
        if not transition:
            return {"ok": False, "error": f"No transition for '{event}' in '{self._state}'"}

        if transition.guard and not transition.guard(data):
            return {"ok": False, "error": "Guard rejected transition"}

        old_state = self._state
        new_state = transition.to_state

        exit_cb = self._states[old_state].on_exit
        if exit_cb:
            exit_cb(old_state, event, data)  # ← still mid-transition

        self._state = new_state
        self._history.append({"from": old_state, "to": new_state, "event": event})

        enter_cb = self._states[new_state].on_enter
        if enter_cb:
            enter_cb(new_state, event, data)  # ← still mid-transition

        return {"ok": True, "from": old_state, "to": new_state}
```

**Apply the diagnostic to this second improvement:**

*What does it conceal?* The builder pattern resolves schema mutation. It conceals that **the execution problem is completely unchanged**. Callbacks still receive `self` implicitly through closures. They can still call `self.send()` re-entrantly (via captured reference). They still have no return channel. `_history` can still diverge from `self._state` if a callback raises after `self._state = new_state` but before the history append. The schema is now frozen. The execution is not.

More subtly: `StateConfig` and `TransitionConfig` are frozen dataclasses. But their fields are callbacks — closures that may close over mutable external state. Freezing the dict doesn't freeze the semantics of what the callbacks do.

*What property of the original problem is visible because the improvement recreates it?*
The comment `# ← still mid-transition` is now the entire problem. The builder pattern makes visible that schema integrity and execution integrity are **orthogonal dimensions** that the original conflated. Every improvement so far has addressed one dimension. Neither has touched both. The original problem has a structure that improvements reveal through subtraction.

---

## VIII. THE STRUCTURAL INVARIANT

**The invariant that persists through every improvement:**

*Callbacks must observe state in order to be useful, but any state they can observe is state they can use to trigger new transitions, and any transition triggered during callback execution corrupts the atomicity of the outer transition.*

This persists because it is a property of the problem space, not the implementation:

1. Callbacks are useful only if they receive context (what state changed, why, from where)
2. Context about a transition includes the machine's current position
3. Any reference to the machine's current position is a reference to a live, mutable object
4. A reference to a live mutable object is a mechanism for re-entrant mutation

No amount of dict reorganization, validation, or builder patterns changes this. The invariant lives in the protocol, not the code.

---

## IX. INVERT THE INVARIANT

**The inversion:** Make the machine's position *immutable during callback execution*. Callbacks receive a snapshot. The machine completes the transition before notifying observers.

```python
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

@dataclass(frozen=True)
class TransitionSnapshot:
    """Immutable. Callbacks cannot call send() through this."""
    from_state: str
    to_state: str
    event: str
    data: Any

    # schedule() enqueues; it does not execute
    def schedule(self, event: str, data=None):
        # Injected by StateMachine, not stored as live ref
        raise NotImplementedError  # replaced at call time

class StateMachine:
    def __init__(self, initial_state, states, transitions):
        self._state = initial_state
        self._states = states
        self._transitions = transitions
        self._history = []
        self._queue: deque = deque()
        self._processing = False

    def send(self, event, data=None):
        self._queue.append((event, data))
        if not self._processing:
            self._drain()

    def _drain(self):
        self._processing = True
        try:
            while self._queue:
                event, data = self._queue.popleft()
                self._execute(event, data)
        finally:
            self._processing = False

    def _execute(self, event, data):
        key = (self._state, event)
        transition = self._transitions.get(key)
        if not transition:
            return {"ok": False, "error": f"No transition"}

        if transition.guard and not transition.guard(data):
            return {"ok": False, "error": "Guard rejected"}

        old_state = self._state
        new_state = transition.to_state

        # --- ATOMIC SECTION: no callbacks, no re-entrancy possible ---
        self._state = new_state
        self._history.append({"from": old_state, "to": new_state, "event": event})
        # --- END ATOMIC SECTION ---

        # Build snapshot AFTER state is committed
        snapshot = TransitionSnapshot(old_state, new_state, event, data)

        # Inject schedule capability without exposing live machine ref
        def schedule(evt, d=None):
            self._queue.append((evt, d))
        
        object.__setattr__(snapshot, 'schedule', schedule)

        # Callbacks observe a completed transition
        exit_cb = self._states[old_state].on_exit
        if exit_cb:
            exit_cb(snapshot)

        enter_cb = self._states[new_state].on_enter
        if enter_cb:
            enter_cb(snapshot)
```

**The previously impossible property is now trivially satisfiable:**
Re-entrancy during callback execution is structurally eliminated. Callbacks receive a `TransitionSnapshot` — not a live machine reference. The only machine operation available to them is `schedule()`, which enqueues rather than executes. The queue drains sequentially after the current `_execute()` returns. The state is consistent at all observable moments.

---

## X. THE NEW IMPOSSIBILITY

**The inversion creates this impossibility:**

*Callbacks cannot veto or rollback a transition they observe.*

By the time callbacks run, `self._state = new_state` has already executed. If `exit_cb` discovers that cleanup failed — the resource couldn't be released, the external system rejected the transition, the precondition was violated — it has no mechanism to return the machine to `old_state`. The guard handles pre-transition rejection, but guards run before exit logic. A guard cannot observe what the exit side-effect would reveal.

The veto authority (guards, pre-transition) and the observability (callbacks, post-transition) are now structurally separated — and the information needed to make a correct veto decision is only available at the observation point that cannot veto.

---

## XI. THE CONSERVATION LAW

**Original impossibility:** Callbacks can observe state mid-transition (they have live machine access) but cannot do so safely (re-entrancy corrupts outer transition).

**Inverted impossibility:** Callbacks observe state safely (they receive a completed snapshot) but cannot influence the transition outcome (it is already committed).

**The conservation law between them:**

> **Veto authority and observability completeness are temporally anti-correlated across a transition boundary. The sum is conserved: any increase in one requires an equal decrease in the other.**

More precisely:

| Position | Observability | Veto Authority |
|----------|--------------|----------------|
| Pre-transition (guard) | Low — exit effects unknown | High — transition not started |
| Mid-transition (original callbacks) | Medium — partial state visible | Zero — re-entrancy corrupts |
| Post-transition (inverted callbacks) | High — full effects visible | Zero — state committed |

No protocol position offers both high observability and meaningful veto authority. This is not a deficiency of any implementation — it is a consequence of causality applied to sequential state machines:

**You cannot observe the complete effect of an action and simultaneously prevent the action from occurring, because observing the complete effect requires the action to have occurred.**

The original code's bug is not that it chose the wrong position on this tradeoff. The bug is that it appeared to offer mid-transition observability while hiding that the veto mechanism (by omission) was simultaneously zero. The code's concealment mechanism — structural parallelism without coupling — hid not just the schema problems, but this deeper law. Every improvement made the law more visible by failing to escape it.

The finding: **this is not a fixable bug. It is a protocol design decision that must be made explicitly:** choose pre-transition authority (guards with full context, requiring two-phase commit semantics) or post-transition observability (snapshot callbacks with compensation patterns for failure). The current code implicitly chose a position between them that satisfies neither.
