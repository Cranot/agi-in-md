## The Analysis

---

### Falsifiable Claim

> **The machine conflates three distinct concerns — state recording (`_history`), transition execution (`_state`), and effect execution (callbacks) — into a single non-atomic sequence with no compensation mechanism, making the machine's state semantics undefined after any callback exception.**

**Falsifiable test**: Throw an exception in any `on_enter` callback. Then inspect the machine. You'll find `_state = new_state` (transition committed), `_history` updated, `send()` propagating the exception — with no indication that the transition half-executed. Future `send()` calls proceed from `new_state` as if entry was clean.

---

### Three Expert Debate

**Expert A (Defends)**

The claim is precise. The ordering is:

```python
exit_cb(...)          # side effects run
self._state = new_state  # point of no return
self._history.append(...) # recorded
enter_cb(...)         # can throw HERE
```

If `enter_cb` throws, the machine has committed to `new_state` in both `_state` and `_history`, but with incomplete entry semantics. No rollback. No partial-transition signal in the return value. The `{"ok": True}` that never arrives is replaced by a propagated exception — callers have no way to distinguish "transition failed" from "transition committed but corrupted." The machine is lying about its own state.

**Expert B (Attacks)**

This is real but shallow — a symptom. The deeper problem is that there's no distinction between **declarative transitions** and **imperative effects**. The machine allows callbacks to call external services, mutate shared state, or trigger other machines. This makes the machine non-compositional. You can't reason about it in isolation because its behavior is co-defined by whatever the callbacks happen to do. Atomicity is just one consequence of allowing unconstrained effects. Fix the atomicity and the compositionality failure remains.

**Expert C (Probes what both take for granted)**

Both of you assume `_state` *is* the machine's state. But look at `_history` — it grows unboundedly, is never read internally, and its contents mirror `_transitions` using the same vocabulary (`from`, `to`, `event`). If `_history` can't be used for replay (callbacks aren't recorded), what is it for?

The machine actually maintains **two parallel state representations**:
- `_state` — what the machine *is* 
- `_history` — what the machine *was*

Expert A's atomicity claim and Expert B's compositionality claim both take it for granted that `_state` is the complete state. But neither representation can reconstruct the other under callback side-effects. The machine presents itself as self-auditing while being fundamentally non-replayable.

---

### The Claim Transforms

| | |
|---|---|
| **Original** | Non-atomic sequence with no compensation mechanism |
| **Transformed** | Two parallel state representations with no formal consistency guarantee and no mechanism to make them consistent without also recording callback effects |

**The gap**: I started with a *temporal* problem (ordering during execution) and ended with a *representational* problem (what "state" actually is). The original claim was about what could go wrong. The transformed claim is about what the machine fundamentally *cannot be* — not a recoverable state recorder, but two loosely coupled state representations performing the role of one.

---

### The Concealment Mechanism

**Vocabulary homomorphism masking semantic divergence.**

`_transitions` and `_history` use identical vocabulary: `from`, `to`, `event`. A reviewer sees structural consistency and infers semantic completeness. The same naming convention implies the same fidelity — that `_history` captures transitions as faithfully as `_transitions` defines them. But `_history` captures only the machine's internal perspective (which states were visited) while `_transitions` defines only the machine's routing logic. Neither captures effects. The shared vocabulary creates the appearance of a complete audit trail while providing none.

**Applied**: A code reviewer who sees `_history.append({"from": old_state, "to": new_state, "event": event})` and `_transitions[(from_state, event)] = to_state` registers them as the same kind of thing. They aren't. One is a routing table; the other is a log of routing decisions — without the effects those decisions caused.

---

### Improvement 1: Deepens the Concealment

Add timestamps, data capture, and a `replay()` method. This passes review because it looks like a move toward event sourcing — more data, better auditability, defensive copies.

```python
import time

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
    self._history.append({
        "from": old_state,
        "to": new_state,
        "event": event,
        "timestamp": time.monotonic(),  # ← audit-grade timestamps
        "data": data                     # ← full event payload captured
    })

    enter_cb = self._on_enter.get(new_state)
    if enter_cb:
        enter_cb(new_state, event, data)

    return {"ok": True, "from": old_state, "to": new_state}

def replay(self, up_to_index=None):
    """Reconstruct state from history."""
    entries = self._history[:up_to_index]
    return entries[-1]["to"] if entries else None   # ← looks like event sourcing

def get_history(self):
    return list(self._history)   # ← defensive copy signals carefulness
```

**Why it passes review**: Timestamps are obviously good. Capturing `data` looks like complete event sourcing. `replay()` has the right name and signature. The defensive copy in `get_history()` signals the author is thinking about mutability.

**Why it deepens concealment**: `replay()` returns a state label, not a reconstructed machine. Two machines with identical histories but different callback registries behave differently. The `data` capture makes it look like full event sourcing — but callback effects aren't captured. The history now looks more complete while remaining equally unreplayable.

---

### Three Properties Visible Only From Trying to Strengthen

**1. Data is an input; effects are outputs. Only inputs are recorded.**

Adding `data` to history made visible that guards and callbacks consume `data` and produce effects — but only `data` (input) is now stored. A guard `guard(data) → bool` can cause a reject based on data that's recorded; but the same data passed to `on_enter` and acted upon is not recorded as an action. History captures inputs but not their transformations.

**2. `replay()` exposes that state labels and state semantics are different things.**

Writing `replay()` forced the question: "what does it mean to be in a state?" The answer you can derive from history is only a label (`"to"`). The full semantics of being in a state — what enter callbacks have run, what side effects have occurred — cannot be derived. The history is rich in labels and empty in semantics.

**3. Guard rejection and data are entangled in a way the machine can't represent.**

Storing `data` in history revealed that guards make decisions based on data — but a guard-rejected transition produces no history entry. You can't replay to find out *why* a guard fired. A guard that rejects based on `data={"user": "admin"}` is indistinguishable in history from one that rejects based on `data={"user": "guest"}`. The history is complete for successful transitions and absent for failed ones.

---

### Improvement 2: Contradicts Improvement 1

Improvement 1 assumed effects are real, inevitable, and should be observed after the fact. Improvement 2 assumes effects should be controlled, deferred, and constrained — preventing the problem at the source.

```python
from dataclasses import dataclass, field
from typing import Callable, Any, List

@dataclass
class TransitionContext:
    """Immutable view passed to callbacks. Callbacks schedule work; they don't execute it."""
    from_state: str
    to_state: str
    event: str
    data: Any
    _scheduled: List[Callable] = field(default_factory=list, repr=False)

    def schedule(self, fn: Callable) -> None:
        """Defer a side effect to run after state is fully committed."""
        self._scheduled.append(fn)

def send(self, event, data=None):
    key = (self._state, event)
    if key not in self._transitions:
        return {"ok": False, "error": f"No transition for {event} in {self._state}"}

    guard = self._guards.get(key)
    if guard and not guard(data):
        return {"ok": False, "error": "Guard rejected transition"}

    old_state = self._state
    new_state = self._transitions[key]
    ctx = TransitionContext(old_state, new_state, event, data)

    # Callbacks declare intent — they don't execute effects
    exit_cb = self._on_exit.get(old_state)
    if exit_cb:
        exit_cb(ctx)

    self._state = new_state
    self._history.append({"from": old_state, "to": new_state, "event": event})

    enter_cb = self._on_enter.get(new_state)
    if enter_cb:
        enter_cb(ctx)

    # Effects run after all machine state is committed
    for fn in ctx._scheduled:
        fn()

    return {"ok": True, "from": old_state, "to": new_state}
```

**Why it passes review**: `TransitionContext` is a recognized pattern (similar to XState's action model). Deferring side effects to post-commit is principled concurrency hygiene. Clean separation of declaration from execution.

**Why it contradicts Improvement 1**:
- Improvement 1 assumes callbacks will act freely and should be observed. Record everything.
- Improvement 2 assumes callbacks should be constrained and controlled. Restrict everything.
- Improvement 1 captures `data` because callbacks use it to produce effects worth recording.
- Improvement 2 treats callbacks as declarative — effect scheduling, not effect execution.

Both pass review independently. Neither can coexist with the other without picking a side.

---

### The Structural Conflict

> **The machine cannot decide whether it is a transition recorder or a transition executor.**

A recorder's job is to faithfully capture what happened — it should be maximally permissive about what callbacks can do and maximally comprehensive about what gets stored. A recorder is optimized for observation.

An executor's job is to reliably produce correct outcomes — it should constrain what callbacks can do and ensure that only valid, committed effects are produced. An executor is optimized for control.

This conflict **exists only because both improvements are legitimate**. Before attempting them, you might argue that this is "just a callbacks problem" or "just an auditability problem." After attempting both improvements, the conflict reveals that these two requirements are genuinely in tension at the architectural level: every choice that makes the machine a better recorder makes it a worse executor, and vice versa.

---

### Improvement 3: Resolves the Conflict

Make effects first-class — **named, registered, executable, and recordable** — so that the history captures what actions fired (satisfying the recorder) and the machine controls how actions fire (satisfying the executor).

```python
from typing import Callable, Dict, List, Optional, Any

class Action:
    def __init__(self, name: str, fn: Callable):
        self.name = name
        self._fn = fn

    def execute(self, ctx: dict) -> Any:
        return self._fn(ctx)


class StateMachine:
    def __init__(self, initial_state: str):
        self._state = initial_state
        self._transitions: Dict[tuple, tuple] = {}   # (state, event) → (new_state, [action_names])
        self._guards: Dict[tuple, Callable] = {}
        self._actions: Dict[str, Action] = {}         # name → Action
        self._history: List[dict] = []

    def register_action(self, name: str, fn: Callable) -> None:
        self._actions[name] = Action(name, fn)

    def add_transition(
        self,
        from_state: str,
        event: str,
        to_state: str,
        actions: Optional[List[str]] = None
    ) -> None:
        self._transitions[(from_state, event)] = (to_state, actions or [])

    def add_guard(self, from_state: str, event: str, guard_fn: Callable) -> None:
        self._guards[(from_state, event)] = guard_fn

    def send(self, event: str, data: Any = None) -> dict:
        key = (self._state, event)
        if key not in self._transitions:
            return {"ok": False, "error": f"No transition for {event} in {self._state}"}

        guard = self._guards.get(key)
        if guard and not guard(data):
            return {"ok": False, "error": "Guard rejected transition"}

        old_state = self._state
        new_state, action_names = self._transitions[key]
        ctx = {"from": old_state, "to": new_state, "event": event, "data": data}

        self._state = new_state

        executed, failed = [], []
        for name in action_names:
            action = self._actions.get(name)
            if action:
                try:
                    action.execute(ctx)
                    executed.append(name)
                except Exception as e:
                    failed.append({"action": name, "error": str(e)})

        self._history.append({
            "from": old_state,
            "to": new_state,
            "event": event,
            "actions_executed": executed,
            "actions_failed": failed,
        })

        return {"ok": True, "from": old_state, "to": new_state, "failed_actions": failed}
```

**How it satisfies both**:
- History records which actions fired and which failed — recorder is satisfied
- Actions are registered, named, and called through a controlled interface — executor is satisfied
- Both improvements can coexist because effects are now typed entities, not opaque closures

---

### How It Fails

The machine now records action *names* but not action *implementations*. Two machines with identical histories (`actions_executed: ["send_email", "log_audit"]`) but different action registries will behave completely differently on any future event. The history looks serializable but isn't. Specifically:

1. **Actions are closures over external state.** `register_action("send_email", lambda ctx: mailer.send(...))` captures `mailer` at registration time. The name `"send_email"` is recorded; `mailer`'s state at execution time is not.

2. **Failed actions produce no compensation.** The machine records `"actions_failed": [{"action": "send_email", ...}]` and returns `ok: True`. The transition committed. The email didn't send. The machine has no concept of a partially-executed transition, and the caller gets a success response with a buried failure list.

3. **Action order is load-bearing but invisible.** Actions are executed in `action_names` order. If `"charge_card"` runs before `"reserve_inventory"` and `"reserve_inventory"` fails, you have a charge without inventory. The order is defined at `add_transition` time, not visible in history, and not reversible.

---

### What the Failure Reveals About the Design Space

The recorder/executor conflict made us think the problem was about *capturing* effects vs. *controlling* them. Improvement 3's failure reveals something the conflict alone could not:

> **The design space assumes that state and effects are separable. They are not.**

The name `"send_email"` is separable from the state machine. The act of sending an email is not — it modifies external state that will affect future guards, future actions, and future behavior of any system this machine interacts with. By naming actions, we made effects *look* separable (they have names, they're registered, they're recorded) while remaining semantically entangled with external state.

This exposes the true constraint of the design space: **you cannot build a self-consistent, self-auditable state machine that is also externally useful without choosing one of**:

| Choice | Cost |
|--------|------|
| **Accept non-auditability** — callbacks do anything | History is decoration. Discard it. |
| **Accept non-compositionality** — machine owns all state | The machine becomes a database. |
| **Accept non-executability** — effects are pure functions of state | The machine becomes a calculator. Execution is someone else's problem. |

This code tries to be all three simultaneously. That's not a bug in the implementation — it's an impossibility in the problem statement. The deepest structural problem is not in the code. It's in the requirement that a single object be simultaneously an executor, a recorder, and a self-consistent state representation under external side effects. No implementation of this interface can satisfy all three.

The three improvements didn't fail because they were poorly engineered. They failed because they were trying to satisfy contradictory requirements — and the third improvement, by being the most sophisticated, made that contradiction maximally clear.
