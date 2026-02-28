# Generative Diagnostic: State Machine

## The Claim (Specific, Falsifiable)

**This code's deepest structural problem is that it has no reified concept of a "transition."** A transition — the fundamental unit of a state machine — is scattered across four separate dictionaries with *incompatible key schemas*, and nothing binds them into a coherent entity.

---

## Three Experts Stress-Test This Claim

### Expert A (Defends)
The fragmentation is real and worse than stated. `_transitions` and `_guards` key on `(state, event)` — identifying a *transition*. But `_on_enter`/`_on_exit` key on `state` alone — identifying a *node*. These are different entities with different cardinalities. You can register a guard for a transition that doesn't exist. You can register two `on_enter` callbacks for the same state and the second silently annihilates the first. The code gives you no way to even *ask* "what constitutes this transition?"

### Expert B (Attacks)
The real problem isn't fragmentation — it's **broken atomicity in `send()`**. Look:

```python
# Step 3: exit callback fires — can throw, state unchanged ✓
exit_cb(old_state, event, data)
# Step 4: state mutates
self._state = new_state              # ← POINT OF NO RETURN
# Step 5: history appended
self._history.append(...)
# Step 6: enter callback fires — can throw, state ALREADY changed ✗
enter_cb(new_state, event, data)
```

If `enter_cb` throws, the state has changed, history is written, but the caller gets an exception instead of `{"ok": True}` — a protocol violation. Also: **nothing prevents `enter_cb` from calling `send()` recursively**, creating re-entrant transitions where `self._state` is already the new state mid-callback. Fragmented storage is a secondary concern — non-atomic transitions are the live grenade.

### Expert C (Probes assumptions)
Both experts assume this *is* a state machine. It isn't. It's a **transition lookup table with side effects**. No final states, no self-transitions (enter/exit always fire), no hierarchical states, no event validation, no state validation — any string silently becomes a "state." The identity problem is upstream of both the fragmentation and atomicity problems.

---

## Transformed Claim

The deepest problem is that **transitions don't exist as entities**, and therefore:
1. **Atomicity is impossible** — there's no transaction boundary to roll back
2. **Reentrancy is invisible** — no transition-in-progress flag can exist
3. **Configuration integrity is uncheckable** — orphan guards, silently overwritten callbacks
4. **The per-state/per-transition cardinality clash** is unrepresentable

### The Diagnostic Gap
My original claim pointed at *structural fragmentation*. The transformed claim reveals fragmentation as a symptom of **ontological absence** — the core domain concept (transition) was never made into a thing. You cannot make transitions atomic, composable, or validatable if transitions aren't objects.

---

## The Concealment Mechanism

**Dictionary-key coherence mimicry.**

The matching `(from_state, event)` tuple pattern across `_transitions` and `_guards` creates a *visual* impression of unified design — like a database with matching column names but no foreign keys. It draws your eye toward the consistent pattern and away from the fact that `_on_enter`/`_on_exit` use an entirely different key schema, that nothing cross-validates keys, and that callbacks are silently last-write-wins.

---

## The Engineered Concealment (Would Pass Review)

```python
def add_transition(self, from_state, event, to_state, 
                   guard=None, on_exit=None, on_enter=None):
    """Define a complete transition with all its behaviors."""
    key = (from_state, event)
    self._transitions[key] = to_state
    if guard:
        self._guards[key] = guard
    if on_exit:
        self._on_exit[from_state] = on_exit
    if on_enter:
        self._on_enter[to_state] = on_enter
```

A reviewer sees: *"Nice — unified API, transitions defined atomically, cleaner than registering pieces separately."* It would pass review easily. It **deepens the concealment** because:

- It creates the **illusion** that guard + callbacks are bound to *this* transition
- But `on_exit` is still stored per-`from_state` — a second transition from the same state **silently overwrites** the previous exit callback
- And `on_enter` is stored per-`to_state` — two transitions targeting the same state clobber each other
- The guard *is* per-transition (tuple key) but the callbacks *aren't* — the unified API makes this divergence **invisible**

---

## Three Properties Visible Only Because We Tried to Strengthen the Concealment

1. **The cardinality mismatch is the load-bearing error.** Trying to bundle per-transition and per-state storage into one API call *exactly produces* silent-overwrite bugs. This proves the storage model and mental model are fundamentally misaligned — no API sugar can bridge them without changing the storage.

2. **The return-value protocol is a secondary concealment layer.** The `{"ok": bool}` return convention implies controlled failure, but any callback exception bypasses it entirely. The "improved" unified API makes callback registration *easier and more likely*, thereby *increasing* the probability of unhandled exceptions — while appearing to reduce surface area.

3. **The silent-overwrite pattern is self-reinforcing.** Once you see that `_on_enter["StateA"] = callback` is last-write-wins, you realize this isn't just a missing-list bug. It reveals that the code models *states as having singular behavior* when in reality behavior depends on *which transition brought you there*. The per-state callback model is architecturally wrong, not merely incomplete — and the unified API makes it look architecturally right.
