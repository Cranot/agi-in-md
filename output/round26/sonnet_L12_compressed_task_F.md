## Structure First Diagnostic: EventBus

---

### Falsifiable Claim

**The deepest problem: `context` is simultaneously a control channel, a data accumulator, and a communication protocol between handlers — but it's a mutable dict with no enforcement of any of those roles.**

Falsifiable: register two handlers where handler A writes `context["x"] = 1` and handler B reads `context["x"]`. B sees A's mutation. This is either a feature or a catastrophic design flaw depending on which line you're reading — and the code cannot tell the difference.

---

### The Concealment Mechanism

**Dict-as-envelope hides shared mutable state as innocent data passing.**

The `context` dict looks like it's *carrying* information through the pipeline. It's actually a *live shared object* that every middleware and handler writes to simultaneously. The concealment works because Python dicts feel like value types semantically but behave like reference types structurally. The `results` key being appended *after* all handlers run, while `error` is set *mid-loop*, makes this visible only if you audit execution order.

There is a specific bug this conceals: a handler that throws an exception causes `context["error"] = e` to be set **and** `_dead_letter.append(context)` — but the loop continues. Subsequent handlers see a context already marked as errored. The event can simultaneously produce partial `results` and an `error`, and the caller receives both without knowing which handlers succeeded.

```python
# Bug: this event is both in dead_letter AND has partial results
for _, handler in handlers:
    try:
        results.append(handler(context))
    except Exception as e:
        context["error"] = e
        self._dead_letter.append(context)  # reference, not copy
# context["results"] = results  # set after — includes pre-error results
```

---

### Improvement 1: Structural Deepening

Isolate each handler with a context copy to prevent cross-handler mutation:

```python
import copy

for _, handler in handlers:
    handler_ctx = copy.copy(context)  # shallow: payload still shared
    try:
        result = handler(handler_ctx)
        results.append(result)
        # Merge control-flow mutations back
        if handler_ctx.get("cancelled"):
            context["cancelled"] = True
            break
    except Exception as e:
        self._dead_letter.append({**handler_ctx, "error": e})
```

**Diagnostic applied to Improvement 1:**

This reveals a second-order coupling that was hidden: `cancelled` and `results` are fundamentally different kinds of state:

- `cancelled` is **control flow** — it must propagate *forward*
- `results` is **data accumulation** — it must aggregate *upward*
- `error` is **observability** — it must route *sideways* to dead-letter

All three are collapsed into the same dict. Copying forces you to decide which mutations matter, which exposes that the current design has no answer.

---

### Improvement 2: Separate Control From Data

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Event:
    type: str
    payload: Any  # treat as immutable by convention
    cancelled: bool = False      # control flow — shared
    results: list = field(default_factory=list)   # accumulation — owned
    errors: list = field(default_factory=list)    # observability — append-only

class EventBus:
    def emit(self, event_type, payload):
        event = Event(type=event_type, payload=payload)
        
        for mw in self._middleware:
            mw(event)
            if event.cancelled:
                return event
        
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(event)
            return event
        
        for _, handler in handlers:
            try:
                event.results.append(handler(event))
            except Exception as e:
                event.errors.append(e)
                self._dead_letter.append(event)
                # Decision point: break or continue?
        
        return event
```

---

### The Structural Invariant

**Every `emit` is a fold over handlers with a shared accumulator.**

The context/event object IS the accumulator. Each middleware and handler is a function `f(accumulator) → accumulator` (or mutates in place). This is a classic left-fold: `reduce(handlers, initial_context)`.

---

### Inversion: Make the Impossible Trivial

The thing currently impossible: **retroactive subscription** — a handler registered after emission cannot receive past events.

Invert the invariant. Instead of *handlers folding over events*, make *handlers fold over the event log*:

```python
class EventBus:
    def __init__(self):
        self._handlers = {}
        self._event_log = []  # persistent log
    
    def on(self, event_type, handler, replay=False, since=0):
        ...
        if replay:
            for stored_event in self._event_log[since:]:
                if stored_event.type == event_type:
                    handler(stored_event)
    
    def emit(self, event_type, payload):
        event = Event(type=event_type, payload=payload)
        self._event_log.append(event)  # log first
        self._dispatch(event)
        return event
```

Retroactive subscription becomes a one-liner. Time becomes a first-class parameter.

---

### The New Impossibility and Conservation Law

**New impossibility: safe event log garbage collection.**

If every event is stored for replay, you cannot know when it's safe to discard one. Every event must either be kept forever or you introduce TTL/compaction/subscription epoch tracking — a new layer of complexity.

**Conservation Law:**

> **Handler-coupling complexity is conserved. You can move coupling from spatial (shared mutable dict) to temporal (shared immutable log), but you cannot eliminate it.**

The original design couples handlers through space (they share the same live dict). The inverted design decouples handlers from each other but couples them to the log through time (they must agree on what "past" means).

**Non-obvious aspect:** The `_dead_letter` queue in the original design is already a degenerate event log — but only for failures. The original author intuited temporal coupling was needed but hid it behind an error-handling concept. Dead-letter IS a log with an implicit filter of `event.failed == True`. The conservation law was already operating; it was just concealed.

---

### Predicted Third Design

**Event sourcing with projections.** Handlers become stateful projections that define a starting offset into the log. The bus becomes append-only. Garbage collection becomes principled via log compaction (discard events all subscribers have consumed). Retroactive subscription is trivial. Priority becomes replayable.

New impossibility in Design 3: **synchronous causality** — you cannot guarantee that emitting event A and immediately reading its effects will see the projection updated. Request-response patterns become impossible without explicit synchronization primitives.

---

### Diagnostic Applied to the Conservation Law

**What does the conservation law conceal?**

The law says "coupling is conserved." Applied here, it points toward the log vs. dict tradeoff. But it conceals something more specific:

**The `_dead_letter` list creates an implicit third participant in every event emission.**

Every `emit` is not a two-party interaction (emitter → handlers). It's three-party: emitter → handlers → error monitor. The error monitor (`_dead_letter`) is never registered as a handler in `_handlers`. It cannot be filtered, prioritized, or removed. It observes every errored event without being a first-class subscriber.

The conservation law talks about coupling in the abstract. What it conceals here is that the *error observer is unaddressable*. You cannot unsubscribe it. You cannot filter it. You cannot give it priority. It is permanently coupled to the error path without any of the machinery the bus provides to actual handlers.

---

### The Meta-Conservation Law

> **Observability is conserved. Making an observer implicit does not eliminate it — it makes it unaddressable.**

Every design decision that hides an observer (like dead-letter hiding the error monitor as a side-effect of the catch block) doesn't save complexity. It pays for apparent simplicity with debuggability debt. The observer still exists; you've merely removed your ability to interact with it.

---

### What the Meta-Conservation Law Conceals About This Specific Problem

The meta-law says observability is conserved. It sounds universal — applicable to any system. But applied here it points *away* from the specific bug.

**What it conceals:** The dead-letter queue holds *references*, not copies. When a handler throws and `self._dead_letter.append(context)` runs, the appended object is the *live context dict* that subsequent handlers continue mutating. The dead-letter queue does not record *what the event looked like when it failed*. It records a reference to the event's final mutated state after all remaining handlers ran.

This is not an observability problem. It is a **snapshot problem**: the dead-letter queue's purpose is forensic (understand what went wrong), but it accumulates post-mortem mutations, making forensics structurally impossible with the current reference semantics.

The meta-conservation law conceals this because "observability" sounds like a property of the observer. The real problem is a property of the *observed*: the event object has no notion of its own history. It can only exist in one state. The `_dead_letter` queue believes it is recording a moment in time; it is actually recording a reference to a thing that no longer exists in that state.

```python
# What _dead_letter thinks it's storing:
{"type": "purchase", "payload": {...}, "error": TimeoutError}

# What it actually stores (after subsequent handlers mutate context):
{"type": "purchase", "payload": {...}, "error": TimeoutError, 
 "results": [result_from_handler_2, result_from_handler_3],
 "x": "mutation from handler 3"}
```

The conservation law this exposes — specific to this problem, non-generalizable:

> **In a system where the error path and the success path share an accumulator, forensic observability and operational correctness are in fundamental tension.** You cannot simultaneously use the context dict to accumulate results (operational) and to record failure state (forensic) without either corrupting the forensic record or halting the operational pipeline.

This is not about observers in general. It is about what happens when a single mutable object serves as both the pipe and the drain.
