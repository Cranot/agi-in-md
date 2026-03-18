# Structural Analysis: Tenacity Retry Library

## Three Deepest Structural Mechanisms

### 1. Deferred Action Chain Construction

**What it actually enforces:** Not a state machine, but a *runtime-constructed function chain* where each iteration rebuilds the action list based on current state. The `iter()` method doesn't directly execute logic—it queues functions (`_add_action_func`) that get invoked in sequence.

- **Input:** `RetryCallState` with current attempt outcome
- **Output:** A marker object (`DoAttempt`, `DoSleep`, or result) that signals the outer loop
- **What breaks if removed:** The entire plugin architecture—`before`, `after`, `before_sleep`, `retry`, `stop`, `wait` callbacks would need hardcoding into a single method
- **Hidden dependency:** Callers assume a simple "try again" loop, but actually depend on the *order* of action chain construction, which differs between explicit retry (`RetrySignal`) and implicit retry (exception matching)

### 2. Context-Local State Isolation

**What it actually enforces:** Thread- and async-context safety through `contextvars.ContextVar` storing `IterState`. The `iter_state` property doesn't just "get" state—it *creates* state on first access, making every context implicitly stateful.

- **Input:** Nothing visible (property access)
- **Output:** An `IterState` instance unique to the current context
- **What breaks if removed:** Concurrent retries in the same thread (async tasks) would share action lists, causing action cross-contamination
- **Hidden dependency:** The `threading.local()` for statistics vs. `ContextVar` for iter_state creates a split-brain: statistics are thread-local but action chains are context-local. Async code in one thread can have multiple action chains but one statistics dict.

### 3. Type as Control Signal

**What it actually enforces:** `DoAttempt` (empty class) and `DoSleep` (float subclass) are not data—they are *type-level signals* that the `__iter__` loop switches on. The return type *is* the instruction.

- **Input:** An action function's return value
- **Output:** Control flow decision in the caller
- **What breaks if removed:** The `iter()` method would need to return tuples like `("attempt", None)` or `("sleep", 0.5)`, making the protocol visible and brittle
- **Hidden dependency:** `DoSleep` being a `float` subclass means `sleep(do)` works directly—the numeric value *is* the sleep duration, but this inheritance is invisible to callers who just see "call sleep with result"

---

## Modification: Continuation-Passing Action Loop

**The simplest modification that deepens concealment:**

Replace the type-checking loop with continuation-passing style. Each action returns the *next action* directly, eliminating the `isinstance` dispatch:

```python
def iter(self, retry_state):
    self._begin_iter(retry_state)
    action = self.iter_state.actions[0] if self.iter_state.actions else None
    
    while action is not None:
        next_signal = action(retry_state)
        if callable(next_signal) and next_signal is not action:
            action = next_signal  # Continuation returned
        elif isinstance(next_signal, DoSleep):
            retry_state.prepare_for_next_attempt()
            self.sleep(next_signal)
            action = None  # Loop continues externally
        else:
            action = None  # Terminal value
```

Actions now return *what to do next* rather than *what type this is*. The `DoAttempt` marker becomes unnecessary—the continuation *is* the attempt.

**What this conceals:** The decision point moves from the loop (visible) into the return values (invisible). Reading `iter()` no longer reveals the three-way branch; you must trace each action's return path.

---

### Three Emergent Properties Revealed

**1. Tail-Call Decision Invisibility**
- *Why invisible in original:* The `isinstance` checks make branch points explicit
- *What surfaces it:* Continuations hide branching inside return values. A callback could return itself forever, creating an infinite loop with no external evidence. The control flow graph becomes undecidable from the loop structure alone.

**2. State Capture Through Closure**
- *Why invisible in original:* State is explicitly passed through `retry_state` parameter
- *What surfaces it:* Actions could return closures that capture and mutate `retry_state` without it appearing in the signature. The boundary between "action uses state" and "action becomes state" dissolves.

**3. Non-Local Control Flow**
- *Why invisible in original:* The loop always returns to `__iter__`, which dispatches based on type
- *What surfaces it:* A continuation can return *any callable*, including functions that skip multiple steps. An action could return `self._post_stop_check_actions` directly, bypassing `_post_retry_check_actions`. The action chain is no longer linear—it's a directed graph that the loop cannot see.

---

## Conservation Law

**Deferral Depth × Execution Transparency = Constant**

Where:
- **Deferral Depth** = how many layers of indirection between "decision made" and "decision executed"
- **Execution Transparency** = ability to trace control flow by reading code structure

The action chain architecture maximizes deferral (decisions built at runtime, executed later) at the cost of transparency (you cannot trace a retry path by reading `iter()` alone—you must simulate the action list construction).

All valid retry implementations preserve this trade-off:
- **Inline retry loop** → high transparency, zero deferral
- **Callback-based chain** → medium deferral, medium transparency  
- **Continuation-passing** → maximum deferral, opacity

The product is conserved: you cannot increase both deferral (flexibility) and transparency (debuggability) simultaneously.
