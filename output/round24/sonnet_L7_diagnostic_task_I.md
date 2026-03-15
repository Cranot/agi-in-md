# Level 7 Diagnostic: State Machine Structural Analysis

---

## I. The Initial Falsifiable Claim

**Claim:** The deepest structural problem is **atomicity violation during transition execution**: `self._state` is mutated before history is recorded and before `enter_cb` fires, creating a window where re-entrant `send()` calls observe a machine that has moved states without a recorded basis for being there. Specifically: if `enter_cb` calls `send()`, `self._history` will be missing the parent transition while `self._state` already reflects the child transition's destination.

**Falsifiability test:**
```python
def corrupting_enter(state, event, data):
    sm.send("next")  # re-entrant call

sm.on_enter("B", corrupting_enter)
sm.add_transition("A", "go", "B")
sm.add_transition("B", "next", "C")
sm.send("go")

# sm._state == "C"
# sm._history == [{"from": "B", "to": "C", ...}]  # A→B transition MISSING
# The machine is in C with no recorded path to A
```

---

## II. Three Experts Transform the Claim

### Expert 1 (Defender): The Atomicity Problem is Real

The violation is genuine and provable. A state machine's core invariant is that `history[-1]["to"] == current_state`. This code breaks that invariant during every transition. You could add a re-entrancy lock, but the *ordering* of `state mutation → history append → callback` is itself wrong. History should capture the completed transition, not be appended mid-flight while callbacks can still observe the old history. The fix requires a commit/finalize pattern.

### Expert 2 (Attacker): Atomicity is a Symptom, Not the Root

Re-entrancy exposes the problem but doesn't cause it. The actual root: **transitions are not first-class objects.** They're fragmented across five separate dictionaries (`_transitions`, `_guards`, `_on_enter`, `_on_exit`, `_history`) with no cohesive representation. Consequences:

```python
# One guard per (state, event) — no conditional branching
add_guard("A", "go", guard1)
add_guard("A", "go", guard2)  # silently overwrites guard1

# One target per (state, event) — no probabilistic/conditional forks
add_transition("A", "go", "B")
add_transition("A", "go", "C")  # silently overwrites B
```

Fix atomicity and you still can't express "go to B if condition X, go to C if condition Y." The architecture can't represent real transition semantics.

### Expert 3 (Prober): Both Assume the Machine Should be Executed, Not Examined

Both experts are thinking about the machine *running*. What they're not questioning: **can this machine describe itself?**

```python
# Can the machine answer these questions?
sm.get_valid_states()        # No — states are implicit in transition values
sm.get_valid_events()        # No — events are implicit in transition keys  
sm.is_terminal(state)        # No — unreachable vs. dead-end is indistinguishable
sm.validate()                # No — the machine cannot verify its own consistency
sm.get_transitions_from(s)   # No — no inverse index exists
```

Neither expert questioned whether `self._state = "nonexistent_state"` is possible (it is — no validation). Neither questioned how you detect that you've added a guard for a transition that doesn't exist (you can't). Both took for granted that the machine's *structure* is correctly communicated to its users. It isn't.

---

## III. The Claim Transforms

| | Claim |
|---|---|
| **Original** | Runtime atomicity violation (dynamic, execution-time) |
| **Transformed** | Absence of self-model — the machine cannot represent, validate, or communicate its own structure (static, architectural) |

**The gap:** I initially analyzed the code *as if it were running*. I was tracking callback firing order, re-entrant call stacks, history list mutations. The transformed claim analyzes the code *at rest* — what the data structures encode, what questions they can answer, what the machine knows about itself.

---

## IV. The Concealment Mechanism: **Operational Masking**

The API is composed entirely of *verbs*: `send`, `add_transition`, `on_enter`, `on_exit`. Every method name implies *doing something to a running machine*, not *describing a structure*. This is operational masking: **the interface presents itself as a mechanism for performing actions rather than as a representation of something**, which conceals that the underlying representation is structurally impoverished.

The clean `send() → {"ok": True/False}` contract feels complete. You get a result. The machine moved. Done. This fluency actively prevents you from asking: *what is the machine, rather than what does it do?*

---

## V. What the Entire Dialectic Failed to Surface

The three experts argued about **how to fix the machine**. None asked what the machine **silently conflates**.

### The Hidden Problem: Semantic Conflation of Absence

```python
def send(self, event, data=None):
    key = (self._state, event)
    if key not in self._transitions:
        return {"ok": False, "error": f"No transition for {event} in {self._state}"}
```

This single return path encodes **three semantically distinct situations** as one:

| Situation | Meaning | Correct Response |
|---|---|---|
| Event never considered for this state | Unknown territory | Log warning, possibly raise |
| State is terminal; no exits intended | Expected end condition | Return success, signal completion |
| Event explicitly forbidden here | Business rule violation | Return error with domain meaning |

The machine cannot distinguish "transition not defined" from "transition explicitly prohibited" from "this is a final state." This means:

- **Dead states are invisible.** `StateMachine("typo")` starts in a state with no outgoing transitions. Every `send()` returns `ok: False`. The machine appears to be "working" (returning results) while being permanently stuck.
- **Terminal states look broken.** A workflow reaching its designed end state returns `{"ok": False, "error": "No transition"}` — indistinguishable from an error.
- **Missing guards are silent dead code.** `add_guard("A", "missing_event", fn)` — the guard is stored, consulted never, and never flagged.

### The Deeper Hidden Problem: The API is a Debt Instrument

The dialectic treated this as a design problem with known solutions. What it missed entirely:

**The simplicity of this API is not a feature — it's a liability that accrues interest.** The `add_transition` / `send` interface is optimized to make simple cases trivially easy. This means the machine will be adopted for simple cases (where it works), then gradually extended with workarounds for complex cases (hierarchical states, parallel regions, history states, guarded forks, internal vs. external transitions) — none of which this flat dictionary architecture can express without fundamental restructuring. By the time the limitations become undeniable, the code has enough usage that replacement is expensive.

The operational masking mechanism isn't just hiding the self-model problem. It's hiding that **the entire architecture is shaped like a simple case pretending to be a general solution** — and the cleaner the simple API feels, the more effectively it obscures how far the structure is from real state machine semantics.

---

## VI. Structural Summary

```
Surface Problem (Expert 1):    Atomicity violation during transition
                                        ↓
Deeper Problem (Expert 2):     Transitions aren't first-class objects
                                        ↓
Deeper Still (Expert 3):       Machine has no self-model
                                        ↓
Concealment Mechanism:         Operational masking (verbs hide absent nouns)
                                        ↓
Hidden by the Dialectic:       Semantic conflation of absence + API as debt
```

The code reads as a competent implementation of a state machine. It is actually a competent implementation of **one specific usage pattern of a state machine**, wearing the API of a general-purpose one — and the operational masking mechanism ensures you won't notice the difference until you need the parts that aren't there.
