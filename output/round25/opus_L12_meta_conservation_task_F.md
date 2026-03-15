# EventBus Analysis: Structure First (Level 12)

## The Initial Claim

**Falsifiable claim:** The deepest structural problem is that the `context` dict serves simultaneously as event identity, processing state, error record, and inter-handler communication channel. This isn't a "shared mutable state bug" — it's **architectural identity diffusion**. The EventBus implements four patterns (pub/sub, middleware chain, command dispatch, dead-letter queue) through one shared mutable dict and *cannot enforce the invariants of any single pattern without breaking the others*.

---

## Three Experts Test the Claim

**Defender:** Correct — observe how `context` is created in `emit()`, then mutated by middleware, conditionally added to `_dead_letter`, handed to each handler (who can mutate it for the next handler), sometimes stamped with `"error"` *while iteration continues*, and finally decorated with `"results"`. The dead-letter queue holds *live references* to contexts still being modified. Handler 2 sees handler 1's mutations. The dead-letter queue for two different exceptions contains two references to the *same dict*, showing only the *last* error.

**Attacker:** The real problem is simpler. Error handling is outright broken:
```python
except Exception as e:
    context["error"] = e                    # overwrites previous error
    self._dead_letter.append(context)       # same reference every time
    # ...and then iteration continues to the next handler
```
This isn't "identity diffusion" — it's a straightforward control-flow bug. The handler loop should `break` or collect errors into a list. And the dead-letter queue conflates "no handlers registered" with "handler threw an exception" — two categorically different situations.

**Prober (interrogating what both assume):** Both assume the EventBus *should* maintain processing-stage isolation. But look at `priority` — handlers are explicitly ordered. Ordering implies *intended sequential dependency*. The code has **no model of itself**: it doesn't know if it's a decoupled pub/sub system or an ordered processing pipeline. Shared mutable state isn't the problem; it's the *mechanism through which the EventBus's lack of self-knowledge manifests*.

### The Transformed Claim

The EventBus has no model of its own processing semantics. It supports priority-ordered handlers (implying coordination), middleware (implying pipeline), dead-letter (implying reliability guarantees), and fire-and-forget emit (implying decoupling) — but has no mechanism to reconcile any two of these.

### The Gap

Original claim: shared mutable state corruption.  
Transformed claim: the absence of a processing model.  
**The gap reveals I diagnosed a symptom (mutation) instead of the cause (the system doesn't know what it is).**

---

## The Concealment Mechanism

**Name: "Polymorphic Adequacy"**

The code *appears to work* for each feature in isolation. Use it as pub/sub alone? Fine. Use only middleware? Fine. Dead-letter? Fine. Problems emerge only at **feature intersections** — middleware + errors, priority + shared state, dead-letter + continued iteration. Since tests tend to exercise features independently, the intersections go untested, and the code appears clean.

---

## First Improvement (Designed to Pass Review While Deepening Concealment)

```python
def emit(self, event_type, payload):
    context = {"type": event_type, "payload": payload, "cancelled": False}

    for mw in self._middleware:
        context = mw(context)
        if context.get("cancelled"):
            return context

    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(dict(context))       # snapshot copy
        return context

    results = []
    errors = []
    for _, handler in handlers:
        try:
            results.append(handler(dict(context)))     # isolated copy per handler
        except Exception as e:
            error_snapshot = dict(context)
            error_snapshot["error"] = e
            errors.append(error_snapshot)
            self._dead_letter.append(error_snapshot)

    context["results"] = results
    context["errors"] = errors
    return context
```

**PR message:** *"Fix shared mutable state — each handler gets a copy, dead letter gets snapshots, errors collected into list instead of overwritten."*

This passes code review. It looks correct.

### Three Properties Visible Only Because We Tried to Strengthen

1. **Shallow copy is a lie.** `dict(context)` is shallow. If `payload` is `{"user": {"name": "Alice"}}`, every handler's "isolated" copy shares the same nested `{"name": "Alice"}` dict. The fix *conceals* shared state behind the *appearance* of isolation.

2. **Isolation destroys the purpose of priority.** If handlers get copies, a high-priority handler's work (enriching context, validating payload) becomes invisible to lower-priority handlers. The priority system *implied* coordination; copies *prevent* it. We've revealed that shared state was load-bearing — an **implicit inter-handler communication channel**.

3. **Middleware is still unprotected.** `context = mw(context)` has no copy discipline — middleware can return the same mutated dict or a new one, and the code treats both identically. The improvement reveals that the "shared state problem" was actually **two different problems** in two subsystems (middleware vs. handlers) that merely *looked* the same.

---

## Diagnostic Applied to the Improvement

**What does the improvement conceal?** That isolation and coordination are **dual requirements** the EventBus has no mechanism to reconcile. Priority ordering *implies* coordination (handlers run in that order for a reason). Copying *prevents* coordination. The improvement makes the contradiction invisible by making one half look "fixed."

**What property of the original problem does the improvement recreate?** The original entangled two things: (a) accidental aliasing (bug) and (b) implicit coordination (feature). The improvement kills both, resurfacing the problem as: **you cannot copy what you need to share, and you cannot share what you need to isolate.**

---

## Second Improvement

Address the recreated property by making coordination explicit and isolation structural:

```python
from copy import deepcopy

class EventContext:
    """Separates isolated payload from explicit shared coordination state."""
    def __init__(self, event_type, payload):
        self.type = event_type
        self._payload = deepcopy(payload)
        self._shared = {}
        self.cancelled = False
        self.errors = []
        self.results = []

    @property
    def payload(self):
        return deepcopy(self._payload)          # every read is isolated

    def share(self, key, value):
        """Explicit inter-handler coordination (visible, auditable)."""
        self._shared[key] = value

    def read_shared(self, key, default=None):
        return self._shared.get(key, default)
```

Now handlers get true payload isolation via `deepcopy` on every access, but can explicitly coordinate through `share()`/`read_shared()`.

### Diagnostic Applied Again

**What does this conceal?** That `share()`/`read_shared()` ordering depends on `priority` — an integer set at registration time by subscribers who **don't know about each other**. Pub/sub's core promise is subscriber independence; explicit coordination *requires* subscriber awareness. The `EventContext` formally separates isolation from coordination but introduces **temporal coupling** that is explicit yet **unvalidatable**.

---

## The Structural Invariant

> **Any mechanism enabling handler coordination introduces ordering dependencies. Any mechanism enforcing isolation prevents coordination. The EventBus must support both. Their composition produces temporal coupling that cannot be statically verified.**

This persists through every improvement because it is a property of **the problem space** (reactive event processing with ordered observers), not of any implementation.

---

## Invert the Invariant

Make isolation + coordination coexist without temporal coupling:

```python
class DeclarativeEventBus:
    """Handlers declare data dependencies. Bus resolves execution order."""

    def on(self, event_type, handler, reads=(), writes=()):
        # Register handler with declared shared-state dependencies
        # Bus topologically sorts handlers at emit-time
        ...

    def emit(self, event_type, payload):
        # Build DAG from declared reads/writes
        # Execute in dependency order
        # Each handler receives: isolated payload + only its declared shared inputs
        ...
```

Isolation + coordination is now **trivially satisfiable**: the bus resolves order from declared data dependencies. No temporal coupling. Priority is *computed*, not declared.

### The New Impossibility

**Dynamic event-driven behavior becomes impossible.** If handler A decides *at runtime* (based on payload content) to produce a value handler B needs, this cannot be declared statically. The system gains static safety but loses runtime expressiveness. Emergent coordination is impossible when all coordination must be declared in advance.

---

## The Conservation Law

> **In an event bus with ordered observers, the sum of *static verifiability of coordination* and *dynamic expressiveness of handlers* is conserved.**

The original code: maximum expressiveness (shared mutable dict = anything goes), zero verifiability.  
The inverted design: maximum verifiability (declared DAG), zero dynamic expressiveness.  
Every design between them trades one for the other at a fixed exchange rate.

---

## Diagnostic Applied to the Conservation Law

**What does the law conceal?** That "static verifiability" and "dynamic expressiveness" are **proxies**. The actual conserved quantity is **the location of knowledge about inter-handler dependencies**:

| Design | Knowledge Location | Tradeoff |
|---|---|---|
| Original code | *Nowhere* (implicit in runtime) | Maximally distributed, minimally useful |
| Inverted design | *In declarations* (static) | Maximally centralized, minimally flexible |
| **Hidden third option** | *In a runtime protocol* | Negotiated at emit-time |

The law's binary framing conceals this third option.

**Structural invariant of the law:** It assumes dependency knowledge must be bound either at *declaration time* or at *runtime with no structure*. This binary persists because every concrete mechanism must choose *when* information is bound.

**Invert that invariant:** Make binding time itself dynamic — handlers declare partial dependencies, the bus lazily resolves the rest via constraint propagation at emit-time.

**New impossibility:** If binding time is dynamic, the bus cannot guarantee termination of dependency resolution. (It reduces to constraint satisfaction, which is NP-complete in general.) **The cost of flexible binding time is undecidable completion.**

---

## The Meta-Conservation Law

> **In any reactive system with multiple observers:**
>
> *flexibility of inter-observer coordination* × *decidability of system behavior* ≤ *k*
>
> **where *k* is bounded by the expressiveness of the coordination language.**

This is Rice's theorem applied to event architectures: the more expressive the coordination mechanism, the less you can statically decide about the system's behavior.

---

## What the Meta-Law Predicts (Invisible from Code Analysis Alone)

This EventBus, deployed in any sufficiently complex application, will evolve toward exactly **one of two attractors**:

**Attractor 1 — The Implicit Protocol.** Teams will develop undocumented conventions: "handlers must not mutate payload," "priority 100–199 is reserved for validation," "context keys starting with `_` are private." These conventions constitute an *informal coordination language* whose expressiveness will grow until a violation is **undetectable by any automated means**. The system will eventually suffer a coordination failure that cannot be diagnosed from the code.

**Attractor 2 — The Formalization Trap.** Someone will formalize the conventions (typed events, handler schemas, declared dependencies). The formalization will progressively restrict the system until event-driven architecture offers **no benefit over direct function calls**. The EventBus will be bypassed — some things go through it, some don't — and the boundary between "bus" and "direct" will itself become an undocumented convention, **recreating Attractor 1 at a higher level**.

**The meta-law's prediction:** This bifurcation is not a failure of engineering discipline. It is a *mathematical consequence* of the problem space. The code's current shape — shared mutable context, absent processing model, features that work in isolation and fail at intersections — is not a mistake to be refactored away. It is the **first move in a game with no winning strategy**, only a choice of which impossibility to accept.

The only actionable engineering decision is: **choose your impossibility deliberately**. For most EventBus use cases, accept Attractor 1 but make the implicit protocol *visible* — not through types or declarations, but through runtime observability: log every context mutation, trace handler ordering, alert on unexpected shared-key access patterns. You can't prevent the coordination problem, but you can make it **diagnosable**.
