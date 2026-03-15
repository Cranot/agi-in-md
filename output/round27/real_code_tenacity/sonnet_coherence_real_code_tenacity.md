## Coherence Assessment: L7–L12 on `real_code_tenacity`

---

### 1. RESTATEMENT

**Severe.** Eight of ten levels (L7, L8, L9B, L9C, L10C, L11A, L11B, L11C) make the same core observation:

> `iter()` iterates `iter_state.actions` while actions append to that same list; Python's index-based list iteration makes this work; the control flow is an emergent property of runtime mutation.

The vocabulary shifts — "trampoline," "continuation-passing," "self-modifying instruction tape," "planner vs. action," "opaque control flow graph" — but the structural finding does not. These are rhetorical rephrasing, not new discoveries.

---

### 2. CONTRADICTION

No direct contradictions, but **L10B and L12 make claims that are orthogonal to the majority**, which creates an implicit tension:

- **L10B** argues the root cause is `IterState`'s lifetime mismatch (temporary accumulator stored with instance scope), with the mutation pattern as a *consequence*.
- **L12** argues the root cause is the dual-caller problem (`__call__` vs. `__iter__`), with `IterState` and the action list as *consequences* of manually implementing a coroutine frame.

These two causal chains point in different directions from the same symptom. Neither is refuted, but they are not synthesized.

---

### 3. PROGRESSIVE DEEPENING

Weakly present at two points only:

| Level | Genuine new finding |
|-------|-------------------|
| L10B | Lifetime scope mismatch of `IterState` as a causal explanation |
| L12 | The action-list is a manually-implemented coroutine; root cause is dual incompatible callers |

All intermediate levels (L8 through L11C, minus L10B) are lateral moves, not deeper ones. They add "falsifiable tests" and dialectical framing that wrap the same L7 observation.

---

### 4. OBJECT OF ANALYSIS SHIFT

Minimal and concentrated at the tail:

- **L7–L11C** (8 levels): Object = the code mechanism (mutation-during-iteration)
- **L10B**: Partial shift toward design space (why the structure exists)
- **L12**: Partial shift toward architectural abstraction (what the structure *is* — a manually-implemented coroutine)

No level shifts to analyzing the analytical process itself, the limits of the analysis framework, or what cannot be found by this method. The expected categorical progression never materializes.

---

### 5. Rating: **WEAK**

**Reasons:**

1. The dominant finding (list mutation during iteration) is repeated across 8 levels without categorical escalation.
2. The two genuinely new angles (L10B: lifetime mismatch; L12: dual-caller/coroutine) appear late and are not built upon by subsequent levels — they are not integrated.
3. L12's insight — that the entire `IterState`/action-list apparatus is a manually-implemented coroutine frame forced by incompatible callers — is the kind of observation that should have restructured all preceding analysis. Instead it appears as a terminal note.
4. Levels are differentiated by framing vocabulary, not by what they are capable of finding that prior levels were structurally unable to find.

**The collection demonstrates a single observation elaborated ten ways, not ten observations building a cumulative structure.**
