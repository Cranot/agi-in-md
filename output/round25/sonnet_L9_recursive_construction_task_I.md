# Recursive Structural Diagnosis: State Machine

---

## I. The Initial Falsifiable Claim

**Claim:** The deepest structural problem is that `self._state` is readable and writable in a partially-committed form during `send()` — between the moment callbacks fire and the moment the assignment completes — making every callback a potential site of silent state corruption through re-entrant `send()` calls.

This is falsifiable: call `send()` from inside an `on_exit` callback and observe that `self._state` is still the old state, so the recursive call processes a valid (but stale) transition, then the original call overwrites `_state` with its own `new_state`, discarding the recursive result.

---

## II. Three Experts Debate

### The Defender
The re-entrancy hazard is demonstrably real. During `exit_cb(old_state, event, data)`, `self._state` has not yet been updated. If that callback calls `self.send("x")`, the machine processes "x" from `old_state` — a transition the designer may have intended to be unreachable at this point. The original `send()` then unconditionally executes `self._state = new_state`, silently overwriting whatever the recursive call produced. History records both transitions, but the causal order is wrong. This isn't theoretical — any callback that triggers side effects on shared objects or calls `send()` for coordination hits this.

### The Attacker
This is a synchronous Python call stack. Re-entrancy is a *usage* mistake, not a structural defect. The real problems are simpler and more damaging in practice: `_on_enter` and `_on_exit` are plain dicts — registering a second callback silently drops the first, with no warning. There are no transition-level actions (only state-level callbacks), which is a fundamental FSM feature. Guards receive `data` but callbacks receive `(state, event, data)` — the interface is inconsistent. These are missing features that break real use cases every day. The re-entrancy concern is a ghost.

### The Probing Expert
Both of you are arguing about *execution*. You're both taking for granted that a state machine should be a *controller* — an object that executes side effects. But a finite automaton is a *declaration* — a graph of states and labeled edges. This implementation provides no way to introspect, validate, or statically verify the machine. Can you ask it: "Is this graph connected? Are there unreachable states? Is event X always handled?" No. The machine's behavior is determined by the side effects of callbacks at runtime, not by its declared structure. The re-entrancy bug and the missing-callback bug are both symptoms of this. The machine can't reason about itself.

---

## III. The Transformation

**Original claim:** Callbacks fire during a non-atomic transition window.

**Transformed claim:** The machine has no first-class representation of a *transition* — transitions are ephemeral computations, not values. Therefore the machine cannot protect, validate, introspect, or compose them. Every concrete bug (re-entrancy, history timing, interface inconsistency) is a symptom of the absence of the transition as a named thing.

**The diagnostic gap:** The original claim is a runtime bug. The transformed claim is an architectural absence. The gap itself is meaningful: you can fix the runtime bug and feel like you've solved the problem, while the architectural absence gets *harder* to see because the fix now demonstrates apparent correctness.

---

## IV. The Concealment Mechanism

**Mechanism: Transactional-looking return values create the illusion of atomicity.**

```python
return {"ok": True, "from": old_state, "to": new_state}
```

This return value *implies* that a complete, bounded operation occurred — here is what happened, where you were, where you are now. It looks like a receipt. But `from` and `to` are captured before callbacks fire; the machine may be in a different state by the time the caller reads this dict. The `{"ok": False, "error": "..."}` pattern reinforces the illusion: it looks like a proper result type.

More broadly: **the clean method names (`add_transition`, `add_guard`, `on_enter`, `on_exit`, `send`) imply a well-factored finite automaton, concealing that the execution model is an unguarded imperative loop with no transition semantics.**

The code reads like a textbook FSM. That legibility is the concealment.

---

## V. The Legitimate-Looking Improvement

Here is a specific improvement that passes code review — it addresses the re-entrancy concern using a well-known queue pattern:

```python
class StateMachine:
    def __init__(self, initial_state):
        self._state = initial_state
        self._transitions = {}
        self._guards = {}
        self._on_enter = {}
        self._on_exit = {}
        self._history = []
        self._in_transition = False
        self._pending_events = []          # NEW: re-entrancy queue

    def add_transition(self, from_state, event, to_state):
        key = (from_state, event)
        self._transitions[key] = to_state

    def add_guard(self, from_state, event, guard_fn):
        self._guards[(from_state, event)] = guard_fn

    def on_enter(self, state, callback):
        self._on_enter[state] = callback

    def on_exit(self, state, callback):
        self._on_exit[state] = callback

    def send(self, event, data=None):
        # NEW: if a transition is already running, queue this event
        if self._in_transition:
            self._pending_events.append((event, data))
            return {"ok": True, "status": "queued", "event": event}

        self._in_transition = True
        try:
            result = self._execute_transition(event, data)
        finally:
            self._in_transition = False
            # NEW: drain the queue after the transition completes
            while self._pending_events:
                next_event, next_data = self._pending_events.pop(0)
                self._in_transition = True
                try:
                    self._execute_transition(next_event, next_data)
                finally:
                    self._in_transition = False

        return result

    def _execute_transition(self, event, data):
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
        self._history.append({"from": old_state, "to": new_state, "event": event})

        enter_cb = self._on_enter.get(new_state)
        if enter_cb:
            enter_cb(new_state, event, data)

        return {"ok": True, "from": old_state, "to": new_state}
```

**Why this passes code review:**
- The `_in_transition` flag pattern is standard and recognizable
- The pending queue is an established pattern for re-entrancy in event systems
- The `finally` block guarantees cleanup
- The refactor into `_execute_transition` is a reasonable extraction
- The return value for queued events is honest: it says "queued"

---

## VI. Three Properties Only Visible Because of the Improvement

**1. Queued events have no validity guarantee at time of execution.**

When `exit_cb` calls `send("y")`, "y" is valid for the state that exists *during that callback*. But the queue processes "y" *after* the original transition completes. By then, the machine is in `new_state`. If "y" has no transition from `new_state`, it silently fails with `{"ok": False}` — but the caller that queued it already received `{"ok": True, "status": "queued"}`. The improvement makes the machine *more* likely to lie about success. This property was latent in the original code but invisible; the queue makes it explicit by deferring execution past the point of validity.

**2. The return value contract is now non-uniform in a way callers cannot handle.**

The original code had one return shape for errors, one for success. The improvement adds a third: `{"ok": True, "status": "queued"}`. A caller doing `if result["ok"]:` now believes the transition succeeded when it has only been scheduled. The caller has no way to know *when* (or whether) the queued event will execute, whether it will fail, or what state the machine will be in afterward. The improvement exposes that the original `send()` was implicitly promising synchronous completion, which was never formally specified.

**3. History order is now causally decoupled from invocation order.**

If `on_exit(A)` calls `send("y")` during a `send("x")` call, history will record `A→B` (from "x") before `B→C` (from "y"), even though "y" was *caused* by the exit of A, not by B's entry. The queue enforces a temporal ordering that is correct in execution but wrong in causation. This reveals that `_history` was always recording *what happened* not *why* — the improvement makes the causal gap visible because now the history order and the invocation order are formally different things.

---

## VII. Recursive Diagnostic: What Does the Improvement Conceal?

**The improvement conceals that the machine's behavior is now determined by callback execution order, not by the automaton's declared graph.**

The original code at least executed everything synchronously in one call: you could trace what happened. The improvement introduces a queue that processes events in FIFO order after the current transition — which means the machine's future state depends on what callbacks *happened to call* during execution, in what order they were called, and what events they queued.

None of this is visible in `add_transition`, `add_guard`, `on_enter`, `on_exit`. The graph of the automaton, as declared, is silent about it. Two machines with identical declared graphs but different callback implementations will exhibit radically different sequencing behavior under the improved code.

**What property of the original problem is visible only because the improvement recreates it:**

> **The machine has no boundary between its structural description and its runtime behavior.**

In the original code, this was invisible because everything happened in a single execution trace. The improvement breaks that trace into two phases (current transition, then queue drain) and immediately reveals that the *structure* of the machine (its graph) has no relationship to *when* things happen. The queue is itself not a first-class transition — it has no state, no guards, no validity check — it's just a list of deferred imperative calls. 

The improvement recreates the original problem at a higher level: just as the original machine had no first-class transition (only ephemeral computations), the improved machine has no first-class *queue entry* — only deferred invocations with no semantic relationship to the automaton they're attached to.

The real problem propagates upward through every layer that tries to fix it without naming what a transition *is*.
