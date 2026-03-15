## Analysis: EventBus Implementation

---

### **Immediate Pattern/Problem Inventory**

**Patterns present:**
- Priority-sorted observer queue
- Middleware pipeline (chain-of-responsibility)
- Dead-letter queue for undelivered/failed events

**Problems present:**

| Problem | Location | Effect |
|---|---|---|
| Error continuation | `except` block | Execution proceeds after handler failure; caller can't distinguish success from silent failure |
| Error overwrite | `context["error"] = e` | Multiple handler failures: only last error survives |
| Dead-letter conflation | Both branches write to `_dead_letter` | "No handler found" and "handler crashed" are indistinguishable |
| Mutable shared context | Dict passed to all layers | Any middleware/handler can corrupt state visible to subsequent handlers |
| Missing results for failures | `results.append()` only on success | Result count ≠ handler count; position in list meaningless |

---

## Level 11C: Structure First

---

### **Step 1 — Name the Concealment Mechanism**

**"Error laundering through context mutation."**

The `try/except` writes the exception *into* the shared dict and continues. The method returns `context` in both success and failure paths — the return value is structurally identical whether all handlers succeeded or all crashed. The bus *launders* failure into the appearance of a normal return.

The context dict is the mechanism: it serves simultaneously as input, output, and error log with no separation. This makes the protocol between layers implicit and invisible.

---

### **Step 2 — First Improvement: Deepen the Concealment into Explicit Structure**

"Deepening" means making the implicit protocol a first-class type, so the concealment becomes intentional abstraction rather than accidental opacity.

```python
from dataclasses import dataclass, field
from typing import Any, Optional
import traceback

@dataclass(frozen=True)
class Event:
    """Immutable input — the thing being communicated."""
    type: str
    payload: Any
    cancelled: bool = False

@dataclass
class DispatchResult:
    """Mutable output — what happened during dispatch."""
    event: Event
    results: list = field(default_factory=list)
    errors: list = field(default_factory=list)  # ALL errors, not just last

    @property
    def succeeded(self) -> bool:
        return not self.errors

    @property
    def fully_succeeded(self) -> bool:
        return not self.errors and len(self.results) > 0

class EventBus:
    def __init__(self):
        self._handlers: dict = {}
        self._middleware: list = []
        self._dead_letter: list = []

    def on(self, event_type, handler, priority=0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type, payload) -> DispatchResult:
        event = Event(type=event_type, payload=payload)

        # Middleware transforms the immutable event, returns new event
        for mw in self._middleware:
            event = mw(event)
            if event.cancelled:
                return DispatchResult(event=event)  # clean early exit

        result = DispatchResult(event=event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            self._dead_letter.append(
                {"reason": "no_handler", "event": event}
            )
            return result

        for _, handler in handlers:
            try:
                result.results.append(handler(event))
            except Exception as e:
                result.errors.append({
                    "handler": handler,
                    "exception": e,
                    "traceback": traceback.format_exc()
                })
                self._dead_letter.append(
                    {"reason": "handler_error", "event": event, "error": e}
                )

        return result
```

**What changed structurally:**
- `Event` (frozen dataclass) = immutable input; handlers cannot corrupt what subsequent handlers see
- `DispatchResult` = separate mutable output accumulator; all errors preserved, not overwritten
- Dead-letter entries carry typed `reason` field; failure modes are now distinguishable
- Caller can inspect `result.succeeded`, `result.errors` — no ambiguous return value

---

### **Step 3 — Diagnostic Applied to Improvement**

**Problem surfaced:** Middleware now returns a *new* `Event`, but `Event` is frozen with `cancelled: bool = False` default. Middleware that needs to cancel must return `Event(type=..., payload=..., cancelled=True)` — reconstructing the whole event. This is verbose and error-prone for complex payloads.

**Second problem:** Handler continuation after error is still implicit. Callers can check `result.errors` but the bus makes no policy decision — it always continues. There's no way to configure "stop on first error" vs. "collect all errors" at the bus level.

**Third problem:** The dead-letter queue holds both `Event` objects and raw dicts (`{"reason": ..., "event": ...}`) — heterogeneous structure.

---

### **Step 4 — Second Improvement: Policy Injection + Uniform Dead-Letter**

Address the diagnostic: make error policy configurable and dead-letter uniform.

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Literal
from enum import Enum
import traceback

class ErrorPolicy(Enum):
    CONTINUE   = "continue"    # collect all errors, run all handlers
    STOP_FIRST = "stop_first"  # stop at first handler error
    SILENT     = "silent"      # swallow errors entirely (original behavior)

@dataclass(frozen=True)
class Event:
    type: str
    payload: Any
    cancelled: bool = False

    def cancel(self) -> "Event":
        """Fluent cancellation — no reconstruction needed."""
        return Event(type=self.type, payload=self.payload, cancelled=True)

@dataclass(frozen=True)
class DeadLetter:
    """Uniform dead-letter structure."""
    reason: Literal["no_handler", "handler_error", "middleware_cancel"]
    event: Event
    handler: Any = None
    exception: Exception = None
    tb: str = ""

@dataclass
class DispatchResult:
    event: Event
    results: list = field(default_factory=list)
    errors: list[DeadLetter] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

class EventBus:
    def __init__(self, error_policy: ErrorPolicy = ErrorPolicy.CONTINUE):
        self._handlers: dict[str, list] = {}
        self._middleware: list[Callable] = []
        self._dead_letter: list[DeadLetter] = []
        self._error_policy = error_policy

    def on(self, event_type: str, handler: Callable, priority: int = 0):
        bucket = self._handlers.setdefault(event_type, [])
        bucket.append((priority, handler))
        bucket.sort(key=lambda x: -x[0])

    def use(self, middleware_fn: Callable):
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> DispatchResult:
        event = Event(type=event_type, payload=payload)

        for mw in self._middleware:
            event = mw(event)
            if event.cancelled:
                dl = DeadLetter(reason="middleware_cancel", event=event)
                self._dead_letter.append(dl)
                return DispatchResult(event=event)

        result = DispatchResult(event=event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            dl = DeadLetter(reason="no_handler", event=event)
            self._dead_letter.append(dl)
            return result

        for _, handler in handlers:
            try:
                result.results.append(handler(event))
            except Exception as e:
                dl = DeadLetter(
                    reason="handler_error",
                    event=event,
                    handler=handler,
                    exception=e,
                    tb=traceback.format_exc()
                )
                result.errors.append(dl)
                self._dead_letter.append(dl)

                if self._error_policy == ErrorPolicy.STOP_FIRST:
                    break
                elif self._error_policy == ErrorPolicy.SILENT:
                    result.errors.clear()  # drop it

        return result
```

---

### **Step 5 — Name the Structural Invariant**

**"Context is simultaneously input and output."**

In the original (and implicitly in any event bus), the same carrier object serves as:
1. The specification of *what* is being dispatched (input)
2. The record of *what happened* during dispatch (output)

This dual role is the invariant. The original enforces it via mutation of a shared dict. The improvements don't eliminate it — they bifurcate it into `Event` (input) and `DispatchResult` (output), but both must exist and must reference each other. The invariant persists: you cannot represent a completed dispatch with only an input or only an output.

---

### **Step 6 — Invert the Invariant**

**Inverted invariant: "Input and output have no identity relationship."**

In the inverted model, events are not traced to their results. Emitting is fire-and-forget into a log; results are independently observable in a separate log. No `DispatchResult` holds a reference to its `Event`. Correlation is possible but not structural.

```python
# Inverted structure:
event_log:  list[Event]          # append-only, all emitted events
result_log: list[HandlerOutcome] # append-only, all handler executions

# Correlation happens externally via event_id, not via object reference
```

The original structure's impossibility: you cannot have an event *without* knowing its dispatch outcome (they're coupled). The inverted structure's impossibility: you cannot have a dispatch result that *guarantees* traceability to its originating event (they're decoupled by default).

---

### **Step 7 — Conservation Law Between Impossibilities**

**"Dispatch information is topologically conserved; only its coupling geometry varies."**

The total information required to fully describe a dispatch event — `{event_identity, payload, handler_outcomes, errors, timing}` — is invariant across all designs. No design eliminates this information set; designs only choose how to **couple** the pieces:

| Design | Coupling geometry |
|---|---|
| Original | Single mutable dict — everything co-located, fully coupled |
| Improvement | Bifurcated — Event/Result separated but structurally linked |
| Inverted | Decoupled logs — no structural link, correlation is external |

The **conservation law**: *You cannot reduce the total information about a dispatch. You can only choose whether its parts share identity (tight coupling) or are correlated by reference (loose coupling) or are correlated by convention (decoupled logs). The information mass is constant.*

**Named:** **Dispatch Information Conservation** — the impossibility of the original (you can't know if it succeeded without inspecting the mutated context) and the impossibility of the inverted design (you can't guarantee trace linkage between emission and outcome) are dual expressions of the same constraint: somewhere, the correlation must exist.

---

### **Step 8 — Predicted Third Design**

Given the conservation law — information must exist somewhere, coupling is the only variable — the third design emerges at the **extreme of explicit externalization**:

**Event Sourcing Bus**: Every dispatch is an append to an immutable event store. Handlers produce *new events* (not return values). The "result" of emitting `UserCreated` is itself an event (`WelcomeEmailQueued`) appended to the same log.

```python
@dataclass(frozen=True)
class Event:
    id: str          # UUID
    type: str
    payload: Any
    caused_by: str | None = None  # parent event id — the correlation

class EventSourcingBus:
    def __init__(self):
        self._log: list[Event] = []          # append-only, immutable history
        self._handlers: dict = {}

    def emit(self, event: Event):
        self._log.append(event)              # record before dispatch
        for _, handler in self._handlers.get(event.type, []):
            child_events = handler(event)    # handlers return new events
            for child in (child_events or []):
                child = Event(              # child carries caused_by link
                    id=new_id(),
                    type=child.type,
                    payload=child.payload,
                    caused_by=event.id
                )
                self.emit(child)            # recursive — causal tree, not flat list
```

**What the conservation law predicts about this design:**
- The information that was *hidden in context mutation* (original) or *made explicit in DispatchResult* (improvements) is now *structurally encoded in the causal chain* (`caused_by` links)
- The impossibility: you cannot emit a "result" that isn't itself an event — everything is observable, nothing is private
- This is the dual of the original's impossibility: in the original, results were invisible; here, results are *only* visible as events, nothing else exists

The three designs form a progression: **coupled mutation → bifurcated objects → causal log** — each step moves correlation from implicit shared state toward explicit structural relationship, conserving total information throughout.
