## Recursive Structural Analysis: EventBus

---

### Step 1 — The Falsifiable Claim

**The deepest structural problem: this system has no model of event identity.** The single `context` dict simultaneously serves as execution request, in-flight state, error report, audit record, and return value. This is falsifiable: call `emit`, have one handler raise an exception, observe that `_dead_letter[-1]` and the return value are the **same object** — mutating one mutates both, and both have been mutated by the error that was supposed to merely *record* a failure.

---

### Step 2 — Three Experts Debate

**Expert A (defends):**
The aliasing is structurally disqualifying. Concretely:
```python
bus = EventBus()
bus.on("x", lambda ctx: (_ for _ in ()).throw(RuntimeError("boom")))
bus.on("x", lambda ctx: ctx)  # runs after error, ctx has "error" key

result = bus.emit("x", {})
# result IS bus._dead_letter[-1] — same object
# result["results"] = [None] even though handler threw
# The dead letter entry is NOT a snapshot of the failure; it's the live final state
```

**Expert B (attacks):**
Aliasing is a fixable bug, not a structural flaw. `deepcopy` before appending to dead letter, done. The *structural* problem is simpler and more damning: there's no `off()`. Every subscription is permanent. This isn't an aliasing problem — it's an incomplete contract. A bus with no unsubscribe is a memory leak with an API.

**Expert C (probes what both take for granted):**
Both experts assume the context dict is the correct unit of analysis. Neither asks: *what does this system believe a context is?* Expert A treats it as a state machine that gets corrupted. Expert B treats it as incidental. But look at what context *does*: it flows through middleware (becoming a processed request), it is passed to handlers (becoming an execution environment), it accumulates results and errors (becoming a report), and it is stored (becoming an audit record). These are four different things with four different correct lifecycles. The system uses one object for all four — not because someone was lazy, but because the design never differentiated them. The aliasing and the missing `off()` are symptoms of this missing ontology.

---

### Step 3 — The Transformed Claim

| | Claim |
|---|---|
| **Original** | Context aliasing makes correctness structurally impossible |
| **Transformed** | The system conflates four distinct concepts — event, execution context, error report, audit record — each with different correct mutability, ownership, and lifecycle. No instance of correctness is possible until these are separated, because any fix to one dimension violates another |

---

### Step 4 — The Gap as Diagnostic / Concealment Mechanism

The gap (from "aliasing bug" to "missing ontology") names the concealment mechanism:

**The context dict's apparent completeness hides the contradiction at its core.**

At any moment, `context` *looks* full: it has `type`, `payload`, `cancelled`, `results`, `error`. This fullness signals self-sufficiency. Code review reads it as a well-structured data transfer object. But it is simultaneously:
- A **pre-execution instruction** (type, payload)
- A **mutable execution environment** (cancelled, being passed into handlers)
- A **post-execution accumulation** (results)
- A **failure record** (error → dead_letter)

Each role demands different behavior (immutability, mutability, snapshots, copies). The dict satisfies all roles by violating all of them. **Fullness conceals contradiction.**

---

### Step 5 — The Legitimate Improvement That Deepens Concealment

This passes code review. It fixes the obvious bugs. It deepens the concealment.

```python
import copy
from dataclasses import dataclass, field
from typing import Any

@dataclass
class EventContext:
    """Structured context with clear fields and snapshot support."""
    type: str
    payload: Any
    cancelled: bool = False
    results: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def snapshot(self):
        return copy.deepcopy(self)

class EventBus:
    def __init__(self):
        self._handlers: dict = {}
        self._middleware: list = []
        self._dead_letter: list[EventContext] = []

    def on(self, event_type: str, handler, priority: int = 0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def off(self, event_type: str, handler):
        if event_type in self._handlers:
            self._handlers[event_type] = [
                (p, h) for p, h in self._handlers[event_type] if h is not handler
            ]

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> EventContext:
        ctx = EventContext(type=event_type, payload=payload)

        for mw in self._middleware:
            ctx = mw(ctx)
            if ctx.cancelled:
                return ctx

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(ctx.snapshot())
            return ctx

        for _, handler in handlers:
            try:
                ctx.results.append(handler(ctx))
            except Exception as e:
                ctx.errors.append(e)
                self._dead_letter.append(ctx.snapshot())  # snapshot at error point

        return ctx
```

**Why this passes review:** typed, structured, adds `off()`, fixes aliasing, collects errors properly, documents snapshot intent. Senior engineers approve it.

---

### Step 6 — Three Properties Visible Only Because We Tried to Strengthen

**Property 1: Dead letter entries have no consistent temporal semantics.**
The original code's aliasing made this moot — the dead letter entry was the live object anyway, so when it was wrong didn't matter. The `snapshot()` call forces the question: *when* is the snapshot taken? On no-handler path: pre-execution initial state. On error path: mid-execution state including prior handler results and prior errors. The same `_dead_letter` list now contains objects from different points in time with no metadata about which. The improvement made temporal inconsistency *visible* by making it *matter*.

**Property 2: Partial success has undefined semantics.**
In the original, one erroring handler set `context["error"]` and stopped being meaningful. In the improvement, `ctx.errors` and `ctx.results` coexist. This looks like a fix — but it exposes that the system has never defined whether `len(errors) > 0 and len(results) > 0` is a success, a failure, or a third state. The `dataclass` structure makes the ambiguity legible for the first time.

**Property 3: Middleware mutations are non-local and permanent.**
The deepcopy snapshots the post-middleware context. If middleware adds a `"user"` key (auth context), every dead letter entry contains the auth context of the emitter — including entries from handlers that ran *after* the auth middleware ran. The improvement makes visible that middleware and handler contexts should not be the same object, because middleware concerns (auth, tracing, logging) contaminate handler concerns (business data) in the audit trail.

---

### Step 7 — Recursive Application: What Does the Improvement Conceal?

**The improvement conceals:** that `EventContext` is still doing four jobs. It is now a *typed* object that does four jobs, which looks like structure but is the same problem with stronger aesthetics. The `dataclass` signals "this is a coherent concept" — but `type + payload` (the event) and `results + errors` (the execution report) have different correct owners, different correct mutability windows, and different correct lifetimes.

**The property of the original problem visible only because the improvement recreates it:**

The original's core failure was: *the caller receives the same object the system used internally, so there is no boundary between the bus's execution state and the caller's return value.*

The improvement recreates this exactly: `emit()` returns `ctx`, the same `EventContext` object the bus mutated throughout execution. The caller can do `result = bus.emit("x", data); result.results.append("injected")` and there is no protection. The `dataclass` and `snapshot()` method create the *appearance* of ownership discipline while the return value remains an internal mutable object handed to an external caller.

```
Original problem: one dict, zero boundaries
Improvement:      one dataclass, zero boundaries  ← identical structure, better typography
```

The recursive diagnostic: **every improvement that adds structure to a context object without separating the context's roles will recreate this problem at a higher level of apparent sophistication.** The concealment deepens with each iteration. The fix is not a better context — it is *no shared context*: separate event records, execution environments, and audit entries at the type level, not the naming level.
