# Deep Structural Diagnosis: The State Machine That Isn't

---

## I. The Falsifiable Claim

> **The deepest structural problem is that this machine models *events* as primary entities and states as emergent byproducts of event sequences — the inverse of what a state machine should be. `_state` is not authoritative identity; it is a cache of the last `_history` entry.**

**Falsification test:** If you can answer "what states exist, which are terminal, and which are reachable?" from the machine's data structures without executing it — the claim is wrong.

You cannot. The machine has no state enumeration, no terminal state concept, and no initial state validation. It only knows about transitions it has been explicitly told about. States exist only insofar as they appear as keys or values in `_transitions`.

---

## II. Three Experts Debate

### Expert A — Defends the Claim

"The claim is correct, but let me sharpen it. Look at `send()` — it is simultaneously a *query* ("is this transition valid?") and a *command* ("execute the transition"). There is no way to ask the machine about its topology without committing to a state change. You cannot write a safety verifier, a planner, or a UI that previews available actions — because the only interface is the side-effectful `send()`. The topology exists as a dict, but it's inaccessible without mutation."

### Expert B — Attacks the Claim

"Expert A's critique is real but shallow — it's easily fixed by adding `can_send()`. The claim misses the actual structural catastrophe: **the machine writes `self._state = new_state` between the exit callback and the enter callback.** If either callback calls `send()`, the machine re-enters `send()` with a partially-committed transition in flight. There is no concept of 'in transition' vs. 'in state.' The machine cannot distinguish these conditions. The problem isn't topology vs. execution — it's that **committed state and in-flight transition are the same variable.**"

### Expert C — Probes What Both Take for Granted

"Both of you assume this *is* a state machine. Look at what's actually here: `_history` grows without bound, states are untyped hashables, callbacks receive data that is never stored, and the machine has no concept of terminal states or acceptance conditions. Both of you imported the semantics of XState or Harel statecharts from the *name* `StateMachine`. The deeper problem is that **vocabulary laundering hides the gap between the concept and the implementation.** The class uses authoritative state machine terminology — `on_enter`, `on_exit`, `send` — that causes reviewers to unconsciously fill in the implied formal semantics. The machine is actually a transition log with callback hooks."

---

## III. How the Claim Transformed

| | |
|---|---|
| **Original claim** | Conflation of topology-query and execution (structural/fixable) |
| **Transformed claim** | The machine lacks state identity entirely; states are byproducts of event records (ontological/requires reconceptualization) |

**The gap itself is diagnostic:** I started with a *separation-of-concerns* problem (a refactoring concern) and arrived at a *category error* about what the abstraction is. The transformation reveals that the structural problems are not fixable by reorganizing the existing code — they require a different model.

---

## IV. The Concealment Mechanism

### **Vocabulary Laundering Through Authoritative Naming**

The code deploys a vocabulary that pattern-matches to well-known formal systems — UML statecharts, XState, Harel charts — causing reviewers to *import semantics the implementation doesn't honor:*

- `_state` sounds like a well-typed domain object with invariants. It is `Any` hashable.
- `add_transition` implies a validated graph edge. It is an unchecked dict write.
- `on_enter`/`on_exit` imply state lifecycle with defined ordering. They are callbacks registered against string keys, called in an order that permits re-entrant mutation.
- `send` implies the formal event-processing semantics of Actor model or Mealy machines. It is a dict lookup followed by two arbitrary function calls.

**The mechanism:** Each name creates a *semantic contract* that the implementation doesn't honor. Reviewers validate the names against their mental model of state machines rather than against the actual code.

---

## V. The Trojan Horse Improvement

Here is a specific, legitimate-looking improvement that **deepens the concealment without fixing anything:**

```python
from dataclasses import dataclass, field
from typing import Any, Callable
import threading
import logging
import time

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TransitionRecord:
    """Immutable record of a completed state transition."""
    from_state: Any
    to_state: Any
    event: str
    timestamp: float = field(default_factory=time.monotonic)


class StateMachineError(Exception):
    pass


class StateMachine:
    def __init__(self, initial_state, name: str = "unnamed"):
        self._state = initial_state
        self._name = name
        self._transitions: dict[tuple, Any] = {}
        self._guards: dict[tuple, Callable] = {}
        self._on_enter: dict[Any, Callable] = {}
        self._on_exit: dict[Any, Callable] = {}
        self._history: list[TransitionRecord] = []
        self._lock = threading.RLock()           # <-- key deception #1
        logger.info(f"[{name}] initialized → '{initial_state}'")

    def add_transition(self, from_state, event, to_state) -> "StateMachine":
        with self._lock:
            self._transitions[(from_state, event)] = to_state
        return self  # fluent builder pattern — looks professional

    def add_guard(self, from_state, event, guard_fn: Callable) -> "StateMachine":
        with self._lock:
            self._guards[(from_state, event)] = guard_fn
        return self

    def on_enter(self, state, callback: Callable) -> "StateMachine":
        with self._lock:
            self._on_enter[state] = callback
        return self

    def on_exit(self, state, callback: Callable) -> "StateMachine":
        with self._lock:
            self._on_exit[state] = callback
        return self

    def can_send(self, event, data=None) -> bool:
        """Non-mutating check: is this transition currently valid?"""  # <-- key deception #2
        with self._lock:
            key = (self._state, event)
            if key not in self._transitions:
                return False
            guard = self._guards.get(key)
            return not guard or guard(data)

    @property
    def state(self) -> Any:
        return self._state

    @property
    def history(self) -> list[TransitionRecord]:
        return list(self._history)  # defensive copy — signals careful design

    def send(self, event, data=None) -> dict:
        with self._lock:
            key = (self._state, event)
            if key not in self._transitions:
                return {"ok": False, "error": f"No transition for '{event}' in '{self._state}'"}

            guard = self._guards.get(key)
            if guard and not guard(data):
                return {"ok": False, "error": "Guard rejected transition"}

            old_state = self._state
            new_state = self._transitions[key]

            exit_cb = self._on_exit.get(old_state)
            if exit_cb:
                try:
                    exit_cb(old_state, event, data)
                except Exception as e:
                    raise StateMachineError(f"Exit callback failed: {e}") from e  # <-- key deception #3

            self._state = new_state
            self._history.append(TransitionRecord(old_state, new_state, event))

            enter_cb = self._on_enter.get(new_state)
            if enter_cb:
                try:
                    enter_cb(new_state, event, data)
                except Exception as e:
                    raise StateMachineError(f"Enter callback failed: {e}") from e

            logger.info(f"[{self._name}] '{old_state}' --{event}--> '{new_state}'")
            return {"ok": True, "from": old_state, "to": new_state}
```

**Why this passes code review:** typed hints, immutable history records, fluent builder, structured logging, explicit error types, thread safety, a `can_send()` predicate, defensive property copies. Every visible problem has an apparent fix.

**Why it deepens the concealment:** Each apparent fix occludes a worse problem.

---

## VI. Three Properties Visible Only Because We Tried to Strengthen It

### Property 1: Re-entrancy is not a bug — it is an implicit design contract

When adding thread safety, you must choose between `threading.Lock` and `threading.RLock`. `Lock` would deadlock immediately when any callback calls `send()` — which is a completely normal use case for a state machine with actions. `RLock` is the only viable choice. **The act of choosing `RLock` reveals that the design tacitly requires callbacks to be able to trigger further transitions.** This is an architectural commitment — re-entrant event processing — that is never stated, never documented, and completely invisible in the original. The "improvement" doesn't add thread safety; it formalizes an undocumented execution model.

### Property 2: There is no rollback semantics, and adding error handling exposes it catastrophically

When you add `try/except` around the enter callback and raise `StateMachineError`, you create a machine that can raise an exception *after* `self._state = new_state` has committed. The caller receives an exception, but the machine is now in `new_state` with a `TransitionRecord` in history showing a completed transition — while the `on_enter` callback believes the transition failed. **This was invisible before because the original code silently swallowed the callback's exception and returned `{"ok": True}`.** The "improvement" doesn't fix the inconsistency — it makes it observable to callers who now have no way to distinguish "transition failed before commit" from "transition committed but callback raised."

### Property 3: Guards are assumed to be pure, but `can_send()` proves they never were

Adding `can_send()` creates a public API that calls guard functions without triggering state change. This immediately creates a TOCTOU (time-of-check / time-of-use) race: external state could change between `can_send()` and `send()`, making the guard's answer stale. More critically: **many guard functions in practice have side effects** — they log, they query databases, they increment counters. Calling `can_send()` then `send()` invokes the guard twice. The original design never needed guards to be idempotent because there was only one call path. **The addition of `can_send()` — which directly addresses Expert A's critique — reveals that guards were never designed to be pure predicates.** The improvement exposes a load-bearing assumption that the interface is now advertising as optional.

---

## Summary: The Structural Topology of the Problem

```
Vocabulary laundering
        │
        ▼
"State machine" semantics imported by reader ──────────────────┐
        │                                                       │
        ▼                                                       ▼
Transitions appear valid           Re-entrancy appears to be
(dict lookup looks like           an edge case
formal topology)                  (not a load-bearing design commitment)
        │                                                       │
        └──────────────┬────────────────────────────────────────┘
                       ▼
         State identity is a runtime artifact,
         not an architectural invariant.
         You cannot reason about this machine
         without running it.
                       │
                       ▼
         Every "improvement" that uses the
         existing vocabulary deepens the
         concealment rather than fixing it.
```

The machine needs a different model: explicit state enumeration, transition as a validated graph operation with atomicity guarantees, and callbacks as post-commit notifications rather than in-transaction side effects.
