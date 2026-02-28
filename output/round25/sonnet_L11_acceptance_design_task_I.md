# Deep Structural Analysis: State Machine

---

## The Claim

**The deepest structural problem is that this machine executes an unguarded sequence of irreversible operations with no coherent transaction model, while its `{"ok": True/False}` API     -> Done (178s) -> 308 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/sonnet_L11_acceptance_design_task_I.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
sert `self._state`. It will be `new_state`. The machine entered a state it never properly inhabited.

---

## Three Experts

**Expert A (Defender):** The ordering is correct UML behavior. Exit runs in the source state; entry runs in the target state. `self._state = new_state` before `on_enter` is intentional — that's how the machine *knows* where it is during entry. Complaint dismissed.

**Expert B (Attacker):** UML also defines failure semantics. This machine has none. The deeper problem isn't the ordering — it's that history is appended *between* state mutation and `on_enter`. History is supposed to be an audit log of *completed* transitions. It currently records transitions that may have never completed.

**Expert C (Prober):** Both of you are arguing about implementation of a contract neither of you defined. The guard system implies a "rejection" contract. The history implies an "audit" contract. The callbacks imply a "side-effect coordination" contract. These are three different reliability models. What does it mean for a transition to *succeed*?

**The claim transforms.** The original claim (bad exception ordering) was a symptom. The real claim:

> **The machine simultaneously attempts to satisfy three incompatible reliability contracts — guard-based rejection, side-effect coordination, and audit history — with a single execution sequence, without acknowledging they require different transaction semantics.**

---

## The Concealment Mechanism

**Callback indirection hides ownership of failure.**

The `{"ok": True/False}` return type creates the *appearance* of a uniform transaction model. But callbacks operate entirely outside it — they throw exceptions, not return values. The machine has two error channels:

- **Return values** — for guard failures (pre-transition, clean)
- **Exceptions** — for callback failures (mid-transition, dirty)

These are structurally indistinguishable to a caller doing `result = sm.send("event")`. The dirty path — where the machine has half-transitioned — *looks* like normal exception handling. The dict API is the fig leaf.

Secondary concealment: `self._on_enter[state] = callback` silently overwrites. Register two `on_enter` callbacks for the same state; the first disappears without warning.

---

## Improvement 1: Deepens the Concealment

Unify error reporting by catching callback exceptions and returning `{"ok": False}`:

```python
def send(self, event, data=None):
    key = (self._state, event)
    if key not in self._transitions:
        return {"ok": False, "error": f"No transition for {event} in {self._state}"}

    guard = self._guards.get(key)
    if guard and not guard(data):
        return {"ok": False, "error": "Guard rejected transition"}

    old_state = self._state
    new_state = self._transitions[key]

    try:
        exit_cb = self._on_exit.get(old_state)
        if exit_cb:
            exit_cb(old_state, event, data)
    except Exception as e:
        return {"ok": False, "error": f"Exit callback failed: {e}"}

    self._state = new_state
    self._history.append({"from": old_state, "to": new_state, "event": event})

    try:
        enter_cb = self._on_enter.get(new_state)
        if enter_cb:
            enter_cb(new_state, event, data)
    except Exception as e:
        # Looks like failure. Machine is in new_state. History records it. The lie is complete.
        return {"ok": False, "error": f"Enter callback failed: {e}"}

    return {"ok": True, "from": old_state, "to": new_state}
```

This passes review: it unifies error channels, prevents exception leakage, uses consistent return types. Every reviewer approves.

**It deepens the concealment because `{"ok": False}` now has two completely different meanings:**
- "Guard rejected; no transition occurred" → machine in `old_state`
- "Enter callback failed" → machine in `new_state`, history committed

The caller cannot distinguish them without inspecting `self._state` directly — which defeats the API entirely.

**Three properties visible only because we strengthened it:**

1. **State and reported-state can permanently diverge.** `{"ok": False}` is now a lie about the machine's actual state 50% of the time. There is no field in the return dict that tells the caller where the machine actually is after failure.

2. **History is not correlated with the success field.** History has an entry for every transition where `on_exit` succeeded, regardless of `on_enter`. History and `ok` are now independently incoherent — you can have `history[-1]["to"] == "X"` while `ok == False` and `self._state == "X"`.

3. **Guard rejection and callback failure are now indistinguishable but have opposite machine effects.** "Guard rejected" = no transition. "Callback failed" = transition happened. Same return shape, opposite semantics. The pre-transition/post-transition distinction is structurally invisible.

---

## Improvement 2: Contradicts Improvement 1

Add rollback: if `on_enter` fails, restore `old_state` and remove the history entry.

```python
def send(self, event, data=None):
    key = (self._state, event)
    if key not in self._transitions:
        return {"ok": False, "error": f"No transition for {event} in {self._state}"}

    guard = self._guards.get(key)
    if guard and not guard(data):
        return {"ok": False, "error": "Guard rejected transition"}

    old_state = self._state
    new_state = self._transitions[key]

    exit_cb = self._on_exit.get(old_state)
    if exit_cb:
        exit_cb(old_state, event, data)

    self._state = new_state
    history_entry = {"from": old_state, "to": new_state, "event": event}
    self._history.append(history_entry)

    enter_cb = self._on_enter.get(new_state)
    if enter_cb:
        try:
            enter_cb(new_state, event, data)
        except Exception as e:
            self._state = old_state          # rollback
            self._history.remove(history_entry)
            return {"ok": False, "error": f"Rolled back: {e}"}

    return {"ok": True, "from": old_state, "to": new_state}
```

This passes review: it's genuinely more correct, rollback is explicit, `{"ok": False}` now consistently means "no transition occurred."

**It directly contradicts Improvement 1:** I1 accepted that enter-callback failure could change state and called it "failed." I2 refuses this and reverses the state change. I1 made `{"ok": False}` a lie; I2 restores it as truth. One strengthens the concealment mechanism; the other dismantles it. Both are individually correct.

---

## The Structural Conflict

Both improvements pass review because each solves a real problem. I1 solves "two error channels." I2 solves "state diverges on failure."

**The conflict they reveal:** Rollback of `self._state` does not roll back `on_exit` side effects. `on_exit` ran. Its effects exist in the world. Then `on_enter` failed. Then we restored `old_state`. The machine says "I'm in `old_state`" — but `old_state`'s exit callback already fired. The machine re-enters `old_state` *without having entered it*, which may violate every invariant `on_enter[old_state]` was supposed to establish.

The structural conflict is:

> **The machine needs both "observable consistency" (state matches reported state) and "side-effect reversibility" (callbacks can be undone). But side effects are definitionally irreversible — that's what makes them side effects. Any rollback that doesn't roll back `on_exit` is lying about recovery.**

---

## Improvement 3: Resolves the Conflict

Separate pure state management from impure effect execution. Commit state atomically; run effects as observers that cannot affect machine integrity.

```python
def send(self, event, data=None):
    key = (self._state, event)
    if key not in self._transitions:
        return {"ok": False, "error": f"No transition for {event} in {self._state}"}

    guard = self._guards.get(key)
    if guard and not guard(data):
        return {"ok": False, "error": "Guard rejected transition"}

    old_state = self._state
    new_state = self._transitions[key]

    # Commit atomically — no callbacks can interrupt this
    self._state = new_state
    record = {"from": old_state, "to": new_state, "event": event}
    self._history.append(record)

    # Effects run after commit: their failure cannot corrupt state
    effect_errors = []
    for cb, ctx in [(self._on_exit.get(old_state), old_state),
                    (self._on_enter.get(new_state), new_state)]:
        if cb:
            try:
                cb(ctx, event, data)
            except Exception as e:
                effect_errors.append(str(e))

    result = {"ok": True, "from": old_state, "to": new_state}
    if effect_errors:
        result["effect_errors"] = effect_errors
    return result
```

This passes review: state is always consistent, history is always accurate, effects are non-blocking, errors are reported.

**How it fails:** `{"ok": True, "effect_errors": [...]}` is not actionable. Callers checking `if result["ok"]` proceed as if the transition completed cleanly. But `on_enter` may have been responsible for acquiring a lock, establishing a connection, allocating a resource — invariants the new state *requires*. The machine is officially in `new_state`. The world is not. The machine now lies to itself.

---

## What the Failure Reveals About the Design Space

The failure of I3 is not a fixable bug. It reveals the topology:

**There are three properties the machine can provide:**
1. **State consistency** — `self._state` always reflects a valid, fully-initialized state
2. **Effect atomicity** — entry/exit callbacks either fully execute or are fully reversed
3. **Caller transparency** — callers can determine exactly what happened from the return value

**These form a 2-simplex.** Any two are achievable. All three require a coordination mechanism that a state machine cannot itself be — a saga, a two-phase commit, an external transaction manager. I1 sacrificed transparency. I2 sacrificed atomicity (by not rolling back `on_exit`). I3 sacrificed consistency (states without entry invariants are fictionally inhabited).

The conflict revealed *that a tradeoff existed.* The failures of I3 revealed *which tradeoff is mandatory given a machine's scope.* A machine cannot coordinate its own transactions; it can only commit its own state.

---

## The Redesign

Accept the topology. Commit to **state consistency as primary invariant**. Demote effects to **non-authoritative observers**.

```python
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

@dataclass(frozen=True)
class Transition:
    from_state: str
    to_state: str
    event: str
    data: Any = None

@dataclass
class TransitionResult:
    ok: bool
    transition: Optional[Transition] = None
    error: Optional[str] = None
    observer_failures: List[str] = field(default_factory=list)

class StateMachine:
    def __init__(self, initial_state: str):
        self._state = initial_state
        self._transitions: dict = {}
        self._guards: dict = {}
        self._observers: List[Callable] = []   # Not per-state: per-machine
        self._history: List[Transition] = []

    def add_transition(self, from_state, event, to_state):
        self._transitions[(from_state, event)] = to_state

    def add_guard(self, from_state, event, guard_fn):
        self._guards[(from_state, event)] = guard_fn

    def observe(self, callback: Callable[[Transition], None]):
        """Register a transition observer. Runs after commit. Failures are isolated."""
        self._observers.append(callback)
        return lambda: self._observers.remove(callback)  # Returns unsubscribe handle

    def send(self, event, data=None) -> TransitionResult:
        key = (self._state, event)
        if key not in self._transitions:
            return TransitionResult(ok=False, error=f"No transition for '{event}' in '{self._state}'")

        guard = self._guards.get(key)
        if guard and not guard(data):
            return TransitionResult(ok=False, error="Guard rejected transition")

        # Atomic commit: these two operations are inseparable
        transition = Transition(self._state, self._transitions[key], event, data)
        self._state = transition.to_state
        self._history.append(transition)

        # Observers: best-effort, isolated, non-blocking
        failures = []
        for observer in self._observers:
            try:
                observer(transition)
            except Exception as e:
                failures.append(f"{observer.__name__}: {e}")

        return TransitionResult(ok=True, transition=transition, observer_failures=failures)

    @property
    def state(self) -> str:
        return self._state
```

---

## What It Sacrifices

- **Per-state entry/exit callbacks.** There is no `on_enter`/`on_exit`. Observers receive a `Transition` and must themselves dispatch on `from_state` or `to_state`. The machine no longer *coordinates* effects — it *announces* them.
- **Effect participation in transitions.** Observers cannot veto, modify, or sequence relative to each other. They have no ordering guarantees. They cannot establish state invariants before the machine proceeds.
- **Causal coupling.** The original design's power was that `on_enter` could make the new state *ready*. This machine has no mechanism for that.

---

## What the Original Design Reveals Was Never a Flaw

The original `on_enter`/`on_exit` design was widely diagnosed as flawed: bad exception ordering, no rollback, inconsistent history. Every improvement attempted to fix this. Every improvement failed or deepened another problem.

But the redesign reveals something: **the original design needed causal coupling between state transitions and side effects because its domain required it.**

Real systems where state machines are useful — protocol handlers, order management, device drivers, workflow engines — have states with **entry invariants**: entering `CONNECTED` means a socket must be open; entering `LOCKED` means a mutex must be held; entering `PAID` means a charge must have succeeded. These invariants cannot be observers. They cannot be best-effort. They are what the state *means*.

The original callbacks were not a design error. They were the cost of modeling something real: **that states are not labels but contracts, and transitions are not assignments but operations that must make those contracts true.**

The redesign is only valid for machines where states are pure labels — where being in state `X` makes no demands on the world. The original design attempted to model machines where states are inhabited — where being in state `X` means something has been done, something is being held, something is in effect.

**That's impossible to do safely with a simple state machine.** It requires a saga, a process manager, a transaction coordinator — something with a broader scope than a single object's `send()` method.

The original "flaw" was the visible cost of trying to do real coordination inside a boundary too small for coordination to be possible. The attempts to fix it were attempts to make a `StateMachine` do what only an orchestration layer can. The flaw was never in the implementation. It was in the scope assigned to the class.
