# Structural Diagnosis: State Machine Double Recursion

## Level 1: The Falsifiable Claim

**Claim**: `send()` conflates *transition authorization* (deciding whether to move) with *transition execution* (performing the move), creating a decision boundary and execution boundary that are inseparable — you cannot ask "would this transition succeed?" without actually attempting it.

*Falsifiability condition*: If you can extract a pure `can_send(event, data)` from the current code without duplicating logic, the claim is weak. Try it:

```python
def can_send(self, event, data=None):
    key = (self._state, event)
    if key not in self._transitions:
        return False
    guard = self._guards.get(key)
    return not (guard and not guard(data))
```

This duplicates the first half of `send()` exactly. The claim holds.

---

## Level 2: Three Experts in Conflict

**Defender**: The claim is correct and consequential. `send()` performs five distinct operations — lookup, guard evaluation, state mutation, callback invocation, history recording — in a single imperative sequence. State is mutated *before* `on_enter` fires but *after* `on_exit` fires. If `on_enter` raises, `self._state` is already the new state. The machine is broken and doesn't know it.

**Attacker**: The claim is trivially true of all state machines. Transition IS decision + execution — that's what the word means. The real problem is more specific: state has *no canonical declaration*. States only exist if you happen to add transitions involving them. You can transition to a state that was never registered for `on_enter` callbacks, and the machine can't tell you this is wrong. The "conflation" is a symptom, not the disease.

**Prober**: Both of you assume the problem is *inside* `send()`. But what does `send()` take for granted? It assumes:
- One callback per state (single dict slot: `_on_enter[state]`)
- One destination per event-from pair (no nondeterminism)
- `_history` is append-only and never read during execution
- `_state` is a *label*, not an object with behavior

The machine treats state as a hashable key into four independent registries. Those registries can be inconsistent with each other — a guard registered for a transition that doesn't exist, a callback for a state that's never reached. The machine has no coherent concept of what a "state" or "transition" *is*.

---

## Level 3: The Claim Transforms

**Original claim**: `send()` conflates authorization with execution.

**Transformed claim**: The machine treats state as a label (a hashable key) rather than as a behavioral entity. Behavior is distributed across four unrelated dicts that can be mutually inconsistent. `send()` must *reassemble* this distributed behavior at runtime. The conflation in `send()` is a runtime symptom of a structural absence at design time: neither "state" nor "transition" exists as a coherent concept in the codebase.

**The gap**: I moved from a problem with the execution method to a problem with the representational model. This gap is the diagnosis.

---

## The Concealment Mechanism

**Registration-time decomposition hiding runtime assembly cost.**

The API looks modular:
```python
sm.add_transition("idle", "start", "running")  # clean
sm.add_guard("idle", "start", guard_fn)         # clean
sm.on_enter("running", callback)                # clean
```

Separate methods, separate concerns. But `send()` must unseparate them:

```python
# send() secretly reassembles everything the API decomposed:
key = (self._state, event)
guard = self._guards.get(key)          # reassemble
exit_cb = self._on_exit.get(old_state) # reassemble
enter_cb = self._on_enter.get(new_state) # reassemble
```

The decomposition is cosmetic. It hides that no coherent "transition" object exists — only scattered facts about transitions, assembled on demand by `send()`.

---

## Level 4: Improvement That Deepens Concealment

This passes code review. It looks like a proper domain model:

```python
from dataclasses import dataclass, field
from typing import Callable, Optional, Any

@dataclass
class Transition:
    from_state: str
    event: str
    to_state: str
    guard: Optional[Callable[[Any], bool]] = None

@dataclass
class State:
    name: str
    on_enter: Optional[Callable] = None
    on_exit: Optional[Callable] = None

class StateMachine:
    def __init__(self, initial_state: str):
        self._state = initial_state
        self._transitions: dict[tuple, Transition] = {}
        self._states: dict[str, State] = {}
        self._history: list[dict] = []

    def add_state(self, state: State) -> None:
        self._states[state.name] = state

    def add_transition(self, transition: Transition) -> None:
        key = (transition.from_state, transition.event)
        self._transitions[key] = transition

    def send(self, event: str, data: Any = None) -> dict:
        key = (self._state, event)
        if key not in self._transitions:
            return {"ok": False, "error": f"No transition for {event} in {self._state}"}

        transition = self._transitions[key]

        if transition.guard and not transition.guard(data):
            return {"ok": False, "error": "Guard rejected transition"}

        from_state = self._states.get(self._state)
        to_state_obj = self._states.get(transition.to_state)

        if from_state and from_state.on_exit:
            from_state.on_exit(self._state, event, data)

        self._state = transition.to_state
        self._history.append({
            "from": transition.from_state,
            "to": transition.to_state,
            "event": event
        })

        if to_state_obj and to_state_obj.on_enter:
            to_state_obj.on_enter(self._state, event, data)

        return {"ok": True, "from": transition.from_state, "to": transition.to_state}
```

**Why it passes review**: Typed dataclasses, guard co-located with transition, callbacks co-located with state, type annotations throughout.

**Why it deepens concealment**: `Transition` and `State` look like first-class domain objects, but they have *no methods* — they're named tuples. `send()` still does all the work. The structural problem is now behind a prettier facade.

---

## Level 5: Three Properties Visible Only From Strengthening

**Property 1: Guards don't execute themselves.**
`Transition` has a `guard` field but no `execute(context)` method. By making `Transition` a dataclass, I made undeniable that the guard is data the machine reads, not behavior the transition performs. The transition cannot protect itself.

**Property 2: `State` objects are optional — there are two separate notions of "state."**
`self._states.get(self._state)` returns `None` if nobody called `add_state()`. A state can exist in the *transition graph* (as a string) without existing as a *behavioral entity* (as a `State` object). This split was always there; the dataclass makes it glaring. The machine has no canonical state space.

**Property 3: The history records the wrong source.**
In my version: `"from": transition.from_state`. This is identical to `self._state` — except now they're different variables. This makes visible that during a transition, the machine has *two claims about the current state* that must be kept synchronized. The original had this too, but it was hidden by using `old_state = self._state` directly.

---

## Level 6: Diagnostic Applied to the Improvement

**What my improvement conceals**: It makes the machine look *safe* (typed, structured) while hiding that `State` objects are still optional. Code that calls `sm.add_transition(...)` without calling `sm.add_state(...)` for the same state names will silently skip all callbacks.

**What property of the original problem is visible because my improvement recreates it**: The optional `State` lookup surfaces that **the machine has no explicit, closed state space**. States are implied by the transition graph, never declared. My improvement offered `add_state()` but didn't require it.

---

## Level 7: Second Improvement

Addresses the unclosed state space:

```python
class StateMachine:
    def __init__(
        self,
        states: list[State],
        transitions: list[Transition],
        initial_state: str
    ):
        declared = {s.name for s in states}

        # Validate closed world at construction time
        errors = []
        for t in transitions:
            if t.from_state not in declared:
                errors.append(f"Transition from undeclared state: {t.from_state!r}")
            if t.to_state not in declared:
                errors.append(f"Transition to undeclared state: {t.to_state!r}")
        if initial_state not in declared:
            errors.append(f"Initial state {initial_state!r} not declared")
        if errors:
            raise ValueError("\n".join(errors))

        self._state = initial_state
        self._states: dict[str, State] = {s.name: s for s in states}
        self._transitions: dict[tuple, Transition] = {
            (t.from_state, t.event): t for t in transitions
        }
        self._history: list[dict] = []

    def send(self, event: str, data: Any = None) -> dict:
        key = (self._state, event)
        if key not in self._transitions:
            return {"ok": False, "error": f"No transition for {event!r} in {self._state!r}"}

        transition = self._transitions[key]

        if transition.guard and not transition.guard(data):
            return {"ok": False, "error": "Guard rejected transition"}

        from_state = self._states[self._state]       # guaranteed by construction
        to_state = self._states[transition.to_state]  # guaranteed by construction

        if from_state.on_exit:
            from_state.on_exit(self._state, event, data)

        self._state = transition.to_state             # ← the seam
        self._history.append({
            "from": from_state.name,
            "to": to_state.name,
            "event": event,
        })

        if to_state.on_enter:
            to_state.on_enter(self._state, event, data)  # ← after seam

        return {"ok": True, "from": from_state.name, "to": to_state.name}
```

---

## Level 8: Diagnostic Applied to Second Improvement

**What this conceals**: Construction-time validation makes the machine look *correct by construction*. It hides that there is still a window — marked `← the seam` — between `self._state = transition.to_state` and `to_state.on_enter(...)` where:

- The machine's label says: `new_state`
- The callbacks that define `new_state`'s behavior: *have not run*
- If `on_enter` raises: the label is `new_state`, history records a complete transition, but the behavioral initialization failed silently

**What property of the original problem is visible because this improvement recreates it**: By removing optional lookups and making `State` objects mandatory, the seam becomes *unavoidable and undeniable*. Every improvement forces us to ask: **when exactly does a state become "current"?** The label changes at one line; the behavior is initialized at another. These are never simultaneous.

---

## The Structural Invariant

**The machine cannot atomically transition. The label change and the behavioral change are always sequenced, never simultaneous.**

This persists through every improvement because it is a property of the *problem space*, not the implementation:

```
on_exit needs: old state is "current"   (label = old)
on_enter needs: new state is "current"  (label = new)
The label can hold one value.
Therefore: no single moment is correct for both.
```

The only three positions for `self._state = new_state`:

| Position | Problem |
|---|---|
| Before `on_exit` | Exit callback fires while machine claims it's already left |
| Between exit and enter | Window where behavior and label are inconsistent |
| After `on_enter` | Enter callback fires while machine claims it hasn't arrived |

Every implementation chooses the middle option and every implementation inherits the window. The invariant conceals itself by appearing to be an *implementation choice* (where to put the assignment line) rather than a *fundamental limitation* — that sequential execution plus single-valued state makes atomic behavioral transition impossible without either:

1. **Pure callbacks** (no external side effects — defeats the purpose)
2. **Transactional rollback** (requires knowing what "undo on_exit" means)
3. **Two-phase commit** (prepare → commit, requiring all callbacks to participate)

Every code review will suggest cosmetic improvements to `send()`. None will escape the invariant, because the invariant lives in the semantics of "transition," not in the code.
