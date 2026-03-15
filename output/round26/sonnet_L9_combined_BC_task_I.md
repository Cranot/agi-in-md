# Structural Analysis: State Machine Diagnostic

---

## I. The Falsifiable Claim

**The deepest structural problem**: `send()` mixes state mutation with callback execution without a transaction boundary, creating a re-entrancy trap where a callback-triggered `send()` during `on_exit` has its final state **silently overwritten** by the outer call's unconditional `self._state = new_state`.

This is falsifiable:

```python
sm = StateMachine("idle")
sm.add_transition("idle", "start", "running")
sm.add_transition("idle", "emergency", "error")

def exit_idle(state, event, data):
    sm.send("emergency")  # fires, sets state to "error"

sm.on_exit("idle", exit_idle)
sm.send("start")
# Expected: "error" (inner transition won)
# Actual:   "running" (outer assignment overwrites it)
print(sm._state)  # "running" — wrong, silently
```

The history log records *both* transitions. The state reflects *neither* accurately.

---

## II. Three Experts

**Expert 1 (Defends):**
"The overwrite is provably destructive. The sequence is: exit_cb fires → inner `send()` completes fully, sets `_state = error` → outer `self._state = new_state` runs unconditionally, clobbers it. No exception, no log entry for the clobber. This is a corruption that looks like success — `send()` returns `{"ok": True}`."

**Expert 2 (Attacks):**
"Re-entrancy is exotic. Exception safety is universal. If `exit_cb` raises, state is still `old_state` but the transition was partially committed. If `enter_cb` raises, `self._state` is already `new_state` but enter didn't complete — the machine is in a state it formally entered but behaviorally never inhabited. Every callback user is one exception away from this. You're debugging the rare case while the common case is broken."

**Expert 3 (Probes what both take for granted):**
"You're both debugging execution ordering *within* the model. But notice: guards are keyed on `(from_state, event)` — per *transition* — while callbacks are keyed on `state` alone — per *node*. The machine has no consistent answer to: *what is behavior attached to?* If the same state is reachable via two different paths, you cannot differentiate callback behavior. Both of you assume the model is representationally adequate and argue about its execution. It isn't."

---

## III. The Transformation

| | Claim |
|---|---|
| **Original** | Execution ordering in `send()` creates a state overwrite vulnerability |
| **Transformed** | The machine collapses *transition identity* into *state identity* — callbacks attach to nodes, not edges — making different-path behavior structurally unrepresentable, with re-entrancy and exception safety as downstream symptoms |

**The gap is diagnostic**: I started in execution space (how code runs wrong) and arrived in model space (what code cannot represent). The gap names the concealment.

---

## IV. The Concealment Mechanism

**Name:** *Organizational completeness as representational adequacy.*

The four dictionaries `_transitions`, `_guards`, `_on_enter`, `_on_exit` look like a complete, well-separated design. Each method is clean. The structure performs thoroughness.

What it conceals: guards are keyed `(state, event)` — they see the transition. Callbacks are keyed `state` — they're blind to it. This asymmetry is buried in method signatures:

```python
def add_guard(self, from_state, event, guard_fn):   # (state, event) → transition-aware
def on_enter(self, state, callback):                 # state → transition-blind
```

A user building order processing where "payment_pending" is reached differently from checkout vs. admin override will discover the limitation only after construction. The API *invited* the wrong abstraction by making it the easiest one.

---

## V. Improvement 1: Deepens Concealment, Passes Review

Add per-transition callbacks alongside per-state callbacks:

```python
class StateMachine:
    def __init__(self, initial_state):
        self._state = initial_state
        self._transitions = {}
        self._guards = {}
        self._on_enter = {}
        self._on_exit = {}
        self._on_transition = {}   # NEW: (from_state, event) → callback
        self._history = []

    def add_transition(self, from_state, event, to_state, on_transition=None):
        key = (from_state, event)
        self._transitions[key] = to_state
        if on_transition:
            self._on_transition[key] = on_transition   # transition-aware hook

    def send(self, event, data=None):
        key = (self._state, event)
        if key not in self._transitions:
            return {"ok": False, "error": f"No transition for {event} in {self._state}"}

        guard = self._guards.get(key)
        if guard and not guard(data):
            return {"ok": False, "error": "Guard rejected transition"}

        old_state = self._state
        new_state = self._transitions[key]

        # Phase 1: exit old state
        exit_cb = self._on_exit.get(old_state)
        if exit_cb:
            exit_cb(old_state, event, data)

        # Phase 2: execute transition
        transition_cb = self._on_transition.get(key)
        if transition_cb:
            transition_cb(old_state, new_state, event, data)

        # Phase 3: enter new state
        self._state = new_state
        self._history.append({"from": old_state, "to": new_state, "event": event})

        enter_cb = self._on_enter.get(new_state)
        if enter_cb:
            enter_cb(new_state, event, data)

        return {"ok": True, "from": old_state, "to": new_state}
```

**Why it passes review:** "Added per-transition hooks — nice, more granular than state-level callbacks. Non-breaking addition."

**Why it deepens concealment:** It appears to solve the path-differentiation problem, but now there are *three* callback sites with *inconsistent signatures*, *no shared protocol*, and *three separate re-entrancy windows* — each at a different phase of state mutation. The re-entrancy danger is now harder to reason about because the state assignment moved, but the overwrite vulnerability migrated with it.

---

## VI. Three Properties Visible Only Because We Tried to Strengthen It

**Property 1: There is no principled location for state assignment.**
When adding `transition_cb`, I had to choose: does it fire before or after `self._state = new_state`? There's no correct answer. This reveals the machine has no concept of a *transition scope* — an execution context bracketing the entire transition. It has only a point mutation to `_state` floating in a sequence of callbacks.

**Property 2: Callbacks accumulate without a protocol.**
```
exit_cb(old_state, event, data)                      # 2 args + data
transition_cb(old_state, new_state, event, data)     # 3 args + data  
enter_cb(new_state, event, data)                     # 2 args + data
```
Each callback type has a different signature. Adding a fourth type would require a fourth signature. The machine has no unified callback contract — each hook is ad hoc.

**Property 3: The dictionary structure actively invites the problem.**
When I added `self._on_transition = {}`, it fit *perfectly* into the existing pattern. The structure made the wrong thing easy. A fifth dictionary is always the path of least resistance. This reveals that the dictionary-per-concern layout is load-bearing for the concealment — its symmetry signals thoroughness while encoding the flawed model.

---

## VII. Improvement 2: Contradicts Improvement 1, Also Passes Review

Collapse all callbacks into the transition object — make the transition the *only* unit of behavioral identity:

```python
from dataclasses import dataclass, field
from typing import Callable, Optional, Any

@dataclass
class Transition:
    from_state: str
    event: str
    to_state: str
    guard: Optional[Callable] = None
    on_exit: Optional[Callable] = None    # fires leaving from_state via THIS transition
    on_enter: Optional[Callable] = None   # fires entering to_state via THIS transition

class StateMachine:
    def __init__(self, initial_state):
        self._state = initial_state
        self._transitions: dict[tuple, Transition] = {}
        self._history = []

    def add_transition(self, from_state, event, to_state,
                       guard=None, on_exit=None, on_enter=None):
        key = (from_state, event)
        self._transitions[key] = Transition(
            from_state, event, to_state, guard, on_exit, on_enter
        )

    def send(self, event, data=None):
        key = (self._state, event)
        t = self._transitions.get(key)
        if not t:
            return {"ok": False, "error": f"No transition for {event} in {self._state}"}

        if t.guard and not t.guard(data):
            return {"ok": False, "error": "Guard rejected transition"}

        old_state = self._state

        if t.on_exit:
            t.on_exit(old_state, event, data)

        self._state = t.to_state
        self._history.append({"from": old_state, "to": t.to_state, "event": event})

        if t.on_enter:
            t.on_enter(t.to_state, event, data)

        return {"ok": True, "from": old_state, "to": t.to_state}
```

**Why it passes review:** "Good refactor — single source of truth, clean `Transition` dataclass, removes five separate dictionaries. Cohesive design."

**Contradiction with Improvement 1:**
- Improvement 1: *State-level callbacks are correct; add transition-level callbacks alongside them*
- Improvement 2: *State-level callbacks are wrong; replace them with transition-level callbacks*

Improvement 1 says: state has inherent behavioral meaning.
Improvement 2 says: only the path through states has meaning.
Both pass independent review. Neither is wrong for all use cases.

---

## VIII. The Structural Conflict

**Name:** *The unit of behavioral identity is undefined.*

The conflict exists because the machine was never designed around a consistent answer to: *what does behavior attach to — a node or an edge?*

The original code answered inconsistently:
- Guards → edges (transition-aware)
- Callbacks → nodes (transition-blind)

Improvement 1 made this inconsistency *explicit* — now you have both, and must choose per use case.
Improvement 2 hid it *differently* — transition-level on_enter means registering the same callback on every incoming transition if you want "state-level" behavior, trading inconsistent abstraction for registration duplication.

**Both improvements are legitimate precisely because they resolve a question the original left open — but the question has no single correct answer.**

---

## IX. What the Conflict Itself Conceals

Applying the diagnostic to the conflict:

The state-vs-transition identity conflict conceals a deeper question: **what does this machine claim to model?**

- *State-level callbacks* assert: being in a state has inherent meaning independent of arrival path
- *Transition-level callbacks* assert: the causal path through states has meaning

These are different semantic models. The original machine mixed them without choosing — which is why both improvements are simultaneously legitimate and contradictory.

**Property visible only because the conflict recreates it:**

The machine has no *causal model of transition execution*. It records `{"from": A, "to": B, "event": e}` — correlation. It does not record *why* B follows A, what context the transition executed in, or what it means for the system's invariants.

This causal blindness is why **re-entrancy and exception safety are unfixable within the current model**. To handle them correctly, the machine would need to distinguish "I am in the middle of a transition" from "I am stably in a state." It would need a *transaction concept* — a scope within which the transition is executing and inside which re-entrancy can be detected or serialized, and at the boundary of which exceptions can be handled atomically.

```
Original problem:      no transaction boundary
Improvement 1:         adds callbacks, multiplies the problem  
Improvement 2:         consolidates callbacks, same missing boundary
Structural conflict:   node vs. edge identity
What conflict conceals: the machine models state correlation, not state causation
```

The machine can tell you *that* a transition happened. It cannot tell you *what* a transition *is* — a scope, a commitment, a reversible action. That's the property concealed at every level, visible finally because every attempt to improve the code requires taking a position on it.

---

## Summary Table

| Layer | Claim | Concealment |
|---|---|---|
| Execution | Re-entrancy causes state overwrite | `send()` looks like a simple dispatcher |
| Model | Transition identity collapses into state identity | Four clean dictionaries look like completeness |
| Semantic | No consistent unit of behavioral identity | Both improvements are "correct" |
| Foundational | No causal model of transition execution | History log looks like observability |

The machine's real problem is that it is a *correlation engine* presenting itself as a *behavioral model*. Every structural fix that stays within its current abstraction will be legitimate, will pass review, and will leave the foundational gap untouched.
