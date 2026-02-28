## Initial Claim (Falsifiable)

**The deepest structural problem: `send()` commits state mutation mid-execution, creating a window where the machine's state is inconsistent with any coherent semantic moment.**

*Falsifiable form*: Register an `on_enter` callback that calls `send()`. The outer call's return value will describe a transition to state A, but the machine will be in state B — a state the outer caller never requested and cannot detect.

```python
sm.on_enter("B", lambda s, e, d: sm.send("go"))  # fires during outer send()
result = sm.send("go")   # result says {"ok": True, "to": "B"}
sm.state                 # actually "C" — result is already stale on return
```

---

## Three Experts Transform the Claim

**Expert 1 (Defender):** Confirmed. The mutation sequence `exit_cb → self._state = new_state → history.append → enter_cb` creates three distinct inconsistency windows. The exit callback sees `old_state` in `self._state`; history records a transition before it completes; the enter callback runs against an already-committed state. Re-entrancy turns each window into a corruption vector.

**Expert 2 (Attacker):** Re-entrancy is a *symptom*. The root cause is **the transition has no rollback semantics**. Fix re-entrancy with a flag, and you've merely made the next problem visible: if `enter_cb` raises an exception, `self._state` is already `new_state`, history already has the entry, but `ok=True` was never returned. The machine committed a transition that never formally completed. Re-entrancy and exception unsafety are both consequences of treating mutation as instantaneous when it isn't.

**Expert 3 (Probing what both assume):** Both of you assume transitions are the right unit. But look at the schema: `(from_state, event) → to_state` is a *function* — one input, one output. Guards can *veto* a transition but cannot *route* it to a different destination. This encodes a structural constraint both of you are treating as a runtime problem. The machine's data model forces determinism even when the domain doesn't warrant it. You're both debating execution order inside a schema that may be wrong.

### The Transformed Claim

The original claim (re-entrancy causes inconsistency) must expand:

> The deepest structural problem is that the machine conflates **three concerns** — routing (the transition table), guarding (veto logic), and lifecycle (callbacks) — while providing no mechanism to reconcile their failure modes. Guards cannot affect routing, callbacks cannot signal errors without leaving the machine half-transitioned, and no single fix addresses all three without exposing the others.

**The gap between the original and transformed claim is itself diagnostic**: I initially named a runtime execution problem. The transformation revealed it's a *schema design* problem that makes correct runtime behavior impossible to express.

---

## The Concealment Mechanism: Completeness Theater via Parallel Dictionaries

```
_transitions   →  looks like: routing concern, handled
_guards        →  looks like: validation concern, handled
_on_enter      →  looks like: lifecycle concern, handled
_on_exit       →  looks like: lifecycle concern, handled
```

Four orthogonal dictionaries, four orthogonal `add_*` methods. This creates the *appearance* of separation of concerns. The concealment works because registration-time orthogonality is real — you genuinely can configure each independently. But execution-time coupling in `send()` is total and irreversible: the four concerns collapse into a single linear sequence where order and exception behavior determine correctness. The visual structure of the class hides that `send()` is doing something no dictionary can capture: managing a temporal protocol across four coupled concerns.

**Secondary concealment**: `{"ok": False, "error": ...}` makes it look like all failure modes are handled uniformly — but callbacks can raise exceptions (unhandled) while guard rejections return structured errors. Two callers using the same `send()` need different error handling strategies depending on whether callbacks are registered.

**Tertiary concealment**: `_history` looks like observability. It's appended after mutation and before `enter_cb` — so it records the transition at a moment when neither the old state's exit nor the new state's entry is complete. It's a log of *intentions*, presented as a log of *completions*.

---

## Improvement A: Exception Wrapper (Passes Review, Deepens Concealment)

```python
def send(self, event, data=None):
    key = (self._state, event)
    if key not in self._transitions:
        return {"ok": False, "error": f"No transition for {event} in {self._state}"}

    guard = self._guards.get(key)
    if guard and not guard(data):
        return {"ok": False, "error": "Guard rejected transition"}

    old_state = self._state
    new_state  = self._transitions[key]

    try:
        exit_cb = self._on_exit.get(old_state)
        if exit_cb:
            exit_cb(old_state, event, data)
    except Exception as e:
        return {"ok": False, "error": f"Exit callback failed: {e}"}
        # State unchanged — no transition occurred

    self._state = new_state
    self._history.append({"from": old_state, "to": new_state, "event": event})

    try:
        enter_cb = self._on_enter.get(new_state)
        if enter_cb:
            enter_cb(new_state, event, data)
    except Exception as e:
        # State IS changed — transition already committed
        return {"ok": False, "error": f"Enter callback failed: {e}", "state_changed": True}

    return {"ok": True, "from": old_state, "to": new_state}
```

This passes review because: exception handling! structured errors! even a `state_changed` flag for callers!

**Why it deepens concealment**: Callers check `result["ok"]`. Both failure cases return `ok=False`. But exit-callback failure leaves the machine in `old_state`; enter-callback failure leaves it in `new_state`. The same error-checking idiom produces opposite behaviors. The explicit `"state_changed": True` key makes it look like the asymmetry is documented — but it's only present in one of the two failure cases, and nothing enforces that callers check for it. The concealment mechanism is now *named and visible* in the return value, making it feel handled.

---

## Three Properties Only Visible Because I Tried to Strengthen It

**1. The state commitment point is a semantic boundary, not an implementation detail.**
When I tried to decide where to put `try/except`, I had to choose: does `self._state = new_state` go inside or outside the try block? There is no correct answer. Either choice creates an asymmetry. This reveals that the commit point is doing semantic work the code never acknowledges — it's the boundary between "pre-transition" and "post-transition" worlds, and no surrounding infrastructure can make it atomic without a fundamentally different design.

**2. The `{"ok": bool}` contract is load-bearing but completely implicit.**
Adding `"state_changed": True` forced me to notice that the contract never specifies what callers *must do* when `ok=False`. Guards, missing transitions, and callback failures all return `ok=False` — but they represent three structurally different situations (no-op, no-op, and partial-commit respectively). Callers cannot distinguish them without checking fields that may or may not exist. The improvement revealed a hidden caller contract that lives nowhere in the code.

**3. `_history` is a success log masquerading as an audit log.**
When deciding whether to write history before or after the enter callback's try block, I realized: if enter fails, `history` already has the entry. That means `_history` cannot be used to reconstruct actual machine state — it records transitions that were *intended* and *partially executed*, not transitions that *completed*. The improvement revealed that the audit trail is structurally misleading, and the more exception-safe the code looks, the more confidently wrong the history becomes.

---

## Improvement B: Re-entrancy Guard (Passes Review, Contradicts A)

```python
def __init__(self, initial_state):
    # ... existing fields ...
    self._in_transition = False

def send(self, event, data=None):
    if self._in_transition:
        raise RuntimeError(
            f"Re-entrant send('{event}') rejected: transition already in progress"
        )

    key = (self._state, event)
    if key not in self._transitions:
        return {"ok": False, "error": f"No transition for {event} in {self._state}"}

    guard = self._guards.get(key)
    if guard and not guard(data):
        return {"ok": False, "error": "Guard rejected transition"}

    old_state = self._state
    new_state  = self._transitions[key]

    self._in_transition = True
    try:
        exit_cb = self._on_exit.get(old_state)
        if exit_cb:
            exit_cb(old_state, event, data)

        self._state = new_state
        self._history.append({"from": old_state, "to": new_state, "event": event})

        enter_cb = self._on_enter.get(new_state)
        if enter_cb:
            enter_cb(new_state, event, data)
    finally:
        self._in_transition = False

    return {"ok": True, "from": old_state, "to": new_state}
```

This passes review because: prevents a genuine bug class, clear error message, uses `finally` correctly to always release the lock.

**Why it contradicts Improvement A**: Improvement A's contract is *errors are values* — all failures return `{"ok": False}`. Improvement B's contract is *some failures are exceptions* — re-entrancy raises `RuntimeError`. A caller written against Improvement A checks `result["ok"]`. A caller written against Improvement B uses `try/except`. They are incompatible error handling idioms applied to the same public method.

---

## The Structural Conflict That Only Exists Because Both Are Legitimate

Apply both improvements together. Now examine what happens when an `on_enter` callback calls `send()`:

```
Outer send("go") begins
  → _in_transition = True
  → exit_cb runs (ok)
  → self._state = new_state (committed)
  → history written
  → enter_cb runs
      → inner send("go2") called
          → _in_transition is True
          → raises RuntimeError("Re-entrant send rejected")   ← Improvement B
      → RuntimeError propagates to Improvement A's try/except
          → caught, returns {"ok": False, "error": "Enter callback failed: Re-entrant..."}
                                                               ← Improvement A swallows it
  → _in_transition = False (finally)
outer send() returns {"ok": False, "error": "...", "state_changed": True}
```

Improvement B's guard raises an exception to *enforce* a protocol. Improvement A's wrapper catches that exception to *absorb* it as a return value. They annihilate each other: the re-entrancy guard fires correctly, but its exception is indistinguishable from a user callback raising any other error.

**The structural conflict, named precisely:**

> **State and execution context are not distinguished in the design.**

The machine knows *where it is* (`self._state`). It has no concept of *what it's doing* (a transition is in progress, with specific semantics attached to that progress). Improvement B tries to add execution context as a boolean flag. Improvement A tries to add error handling as value-return semantics. Both are legitimate responses to real problems. But they conflict because *neither can see what the other is protecting* — they're both patching the same surface (`send()`'s error behavior) from opposite directions, and the surface has no structure to make their patches compatible.

The machine needs a *transition object* — a first-class representation of an in-progress transition that both error handling and re-entrancy can reference. Without it, every improvement to one concern silently undermines another. Both improvements are correct. Their conflict is a proof that the design is structurally incomplete.
