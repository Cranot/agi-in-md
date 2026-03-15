## The Dialectic

**Defender**: The claim holds. `_dead_letter` receives two structurally different things — a context with no error (undelivered) and a context with `context["error"] = e` (partially delivered, failed). These have different recovery semantics: undelivered events might be retried after handler registration; failed events need exception routing. Mixing them destroys both.

**Attacker**: The dead letter conflation is a symptom, not the disease. Look at what `emit()` returns when handler 2 of 3 throws: a context where `results` contains handlers 1 and 3's outputs, `error` is set, and the caller receives... a successful return value. The method has no semantics for partial failure. Fix the dead letter taxonomy and the caller still cannot distinguish "all handlers ran" from "some handlers exploded." The dead letter queue is downstream of the real problem: `emit()` doesn't know if it succeeded.

**Prober — what both take for granted**: Both assume `_dead_letter` is doing something. Who reads it? There's no subscription API, no drain mechanism, no notification. Events enter and nothing exits. The dead letter queue is not a feature — it's a black hole wearing a production pattern's name. Both expert positions are debating the labeling on a container that nobody ever opens.

**Claim transformation**: The original claim identified what the dead letter queue *misclassifies*. The real finding is what its *existence conceals*: the total absence of recovery infrastructure. The dead letter queue doesn't handle failures — it *performs* handling them. The name does all the work.

**Gap**: The concealment mechanism is **Structural Legitimacy Laundering** — the code imports the vocabulary of a production event bus (`_dead_letter`, `_middleware`, `priority`) without importing any of its operational behavior. Each named component signals architectural completeness. The implementation is hollow; the naming is load-bearing.

**Applied**: The middleware chain has the same property. `use()` accepts transformation functions, but there's no error-recovery middleware, no retry middleware, no circuit-breaking middleware — because none of those can be written without the recovery infrastructure that doesn't exist. Priority sorting in `on()` is also hollow: priority has no meaning when a handler exception doesn't halt subsequent handlers, making "priority" mean "execution order" rather than "precedence under failure."

---

## First Improvement — Deepens Concealment, Passes Code Review

Fix the stated problem (separate the failure modes) while making the actual problem (no recovery infrastructure) invisible behind a richer diagnostic API:

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable
import time

class DeadLetterReason(Enum):
    NO_HANDLERS = "no_handlers"
    HANDLER_EXCEPTION = "handler_exception"

@dataclass
class DeadLetterEntry:
    reason: DeadLetterReason
    context: dict
    handler_name: Optional[str] = None
    exception: Optional[Exception] = None
    timestamp: float = field(default_factory=time.time)

class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter: list[DeadLetterEntry] = []

    def on(self, event_type, handler, priority=0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type, payload):
        context = {"type": event_type, "payload": payload, "cancelled": False}
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(DeadLetterEntry(
                reason=DeadLetterReason.NO_HANDLERS,
                context=context.copy()
            ))
            return context
        results = []
        for _, handler in handlers:
            try:
                results.append(handler(context))
            except Exception as e:
                self._dead_letter.append(DeadLetterEntry(
                    reason=DeadLetterReason.HANDLER_EXCEPTION,
                    context=context.copy(),
                    handler_name=getattr(handler, '__name__', repr(handler)),
                    exception=e
                ))
        context["results"] = results
        return context

    def get_dead_letters(self, reason: Optional[DeadLetterReason] = None):
        if reason is None:
            return list(self._dead_letter)
        return [dl for dl in self._dead_letter if dl.reason == reason]

    def replay_unhandled(self):
        """Retry events that had no handlers registered at time of emission."""
        unhandled = self.get_dead_letters(DeadLetterReason.NO_HANDLERS)
        self._dead_letter = [dl for dl in self._dead_letter
                             if dl.reason != DeadLetterReason.NO_HANDLERS]
        for entry in unhandled:
            self.emit(entry.context["type"], entry.context["payload"])
```

This passes review: typed enum reasons, `DeadLetterEntry` dataclass with timestamps and handler identity, filtering API, replay for the recoverable case. All correct, idiomatic, apparently complete.

**Three properties visible only because you tried to strengthen it**:

1. **`replay_unhandled()` reveals that context is not a value object.** Replay re-emits with the original payload, creating a fresh context — any middleware state accumulated in the first emission is silently lost. Replay doesn't replay the event; it creates a new emission with the same payload that may behave differently if middleware has accumulated state. This was invisible before because there was no replay operation to expose it.

2. **`handler_name=getattr(handler, '__name__', repr(handler))` reveals that handler identity is underdetermined by design.** Lambdas return `<lambda>`. Bound methods lose their instance. The entry tells you *what* failed but not *which registration* failed — if the same function is registered three times on the same event (with different priorities or closures), all three failures are diagnostically identical. The improvement tried to capture identity and revealed that the registration model doesn't have one.

3. **`context.copy()` reveals that context mutation is viral.** The original mutates context in place; the improvement snapshots it. But `context.copy()` is shallow — mutable payloads are aliased, not copied. The `results` list continues to mutate after the snapshot. The improvement's attempt to create immutable diagnostic records revealed that the entire context model is mutable-by-assumption, and no snapshot within `emit()` can be authoritative.

---

## Diagnostic Applied to the First Improvement

**What the improvement conceals**: The `_dead_letter` is now *more elaborately* a black hole. `get_dead_letters()` returns a list. `replay_unhandled()` re-emits. But there is still no subscription mechanism — callers must poll. `get_dead_letters(reason=HANDLER_EXCEPTION)` returns failures that the caller must then do something with, which requires coupling to the event bus's internal structure. The improvement added diagnostic *API* without recovery *behavior*. It looks like a more complete system while being equally inert.

**Property visible only because the improvement recreates it**: The improvement tried to make `_dead_letter` a queue (with `replay_unhandled()` as consumption) and revealed that what exists is fundamentally a **log** with a queue's name. A queue implies consumption and routing; a log implies observation after the fact. The original code hid this by exposing no consumption API. The improvement created a partial one and made the distinction vivid: events go in, queries come out, nothing is routed.

---

## Second Improvement — Addresses the Recreated Property

Make the dead letter queue an actual queue: subscribable, consuming, routing-capable.

```python
class DeadLetterQueue:
    def __init__(self):
        self._entries: list[DeadLetterEntry] = []
        self._subscribers: list[Callable[[DeadLetterEntry], None]] = []

    def subscribe(self, handler: Callable[[DeadLetterEntry], None]):
        self._subscribers.append(handler)

    def append(self, entry: DeadLetterEntry):
        self._entries.append(entry)
        for subscriber in self._subscribers:
            try:
                subscriber(entry)
            except Exception:
                pass  # dead letter queue handlers cannot themselves dead-letter

    def drain(self, reason: Optional[DeadLetterReason] = None):
        if reason is None:
            drained, self._entries = self._entries, []
            return drained
        drained = [e for e in self._entries if e.reason == reason]
        self._entries = [e for e in self._entries if e.reason != reason]
        return drained

class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter = DeadLetterQueue()

    def on_dead_letter(self, handler: Callable[[DeadLetterEntry], None]):
        self._dead_letter.subscribe(handler)

    # ... emit() unchanged except using self._dead_letter.append(entry)
```

**Apply the diagnostic**: The `except Exception: pass` inside `DeadLetterQueue.append()` is the original problem reproduced inside the dead letter queue itself. Subscribers can fail silently. The dead letter queue is now a miniature event bus for dead-letter events — with the same silent failure mode. Adding recovery infrastructure created a new unhandled failure surface at the infrastructure's own boundary.

**The structural invariant**: Every new error-handling layer creates a new disappearance boundary at that layer's edge. The boundary between "error was handled" and "error disappeared" cannot be eliminated — it can only be relocated. Adding a dead letter queue moves the boundary from emit() to whoever reads `_dead_letter`. Adding subscriptions moves it to whoever handles subscriber exceptions. The total accountability deficit in the system is constant.

---

## Invert the Invariant

**Original invariant**: The disappearance boundary cannot be eliminated, only relocated.

**Inverted design**: A system where the boundary IS eliminated — where `emit()` refuses to complete until the caller has explicitly acknowledged every failure:

```python
class EventResult:
    def __init__(self):
        self.successes = []
        self.failures: list[tuple] = []  # (handler, exception)
        self._acknowledged = False

    def acknowledge_failures(self):
        self._acknowledged = True

    def __del__(self):
        if self.failures and not self._acknowledged:
            raise RuntimeError(
                f"{len(self.failures)} handler failures were not acknowledged. "
                f"Inspect result.failures and call result.acknowledge_failures()."
            )

class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []

    def emit(self, event_type, payload) -> EventResult:
        context = {"type": event_type, "payload": payload, "cancelled": False}
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                r = EventResult(); r.acknowledge_failures(); return r

        handlers = self._handlers.get(event_type, [])
        result = EventResult()
        if not handlers:
            result.failures.append((None, LookupError(f"No handlers: '{event_type}'")))
            return result
        for _, handler in handlers:
            try:
                result.successes.append(handler(context))
            except Exception as e:
                result.failures.append((handler, e))
        return result
```

**The new impossibility**: Forcing acknowledgment eliminates the disappearance boundary but destroys decoupling. Callers must now synchronously account for every consumer failure before completing their own operation. The event bus was supposed to decouple emitters from consumers — this design makes emitters responsible for every downstream handler's exception contract. It is not publish-subscribe; it is RPC with multiple return channels.

The inverted impossibility: **An event bus cannot simultaneously decouple emitters from consumers AND guarantee that emitters account for consumer failures.**

---

## The Conservation Law

Original impossibility: In a fully decoupled event bus, errors cannot be accounted for — the accountability surface migrates to infrastructure layers that observers may never reach.

Inverted impossibility: In a system that forces error accountability, decoupling is eliminated — emitters must be coupled to consumer failure semantics.

**The conservation law: `decoupling × error accountability = constant`**

In any event dispatch system, the total failure accountability cannot be increased without an equal decrease in emitter-consumer decoupling, and vice versa. The quantity is conserved across all designs.

---

## What a Senior Engineer Would Not Already Know

A senior engineer would say: "Obviously there's a tension between decoupling and error handling — that's why we use event buses for things that can fail independently." This is the obvious trade-off the law must not restate.

What the law reveals that is non-obvious: **the accountability deficit is not reduced by adding infrastructure — it is redistributed to the infrastructure's own failure surface.** The total deficit is constant. Each tool added to handle dead letters (the typed entry, the subscription API, the `except: pass` in the subscriber) creates a new disappearance zone at that tool's boundary. The system with one disappearance layer (the original) is structurally equivalent in total accountability to the system with three disappearance layers (the improved version). The number of layers increased; the total accountability did not.

The corollary: **the right question is not "where does accountability live?" but "how many layers of infrastructure exist between the original failure and a human decision point?"** Each layer is a new disappearance opportunity. The original code with `_dead_letter = []` and the third design with typed entries, subscriptions, and subscriber exception handling have identical total accountability — but the third design's accountability deficit is now distributed across more locations, making it harder to find.

---

## Prediction About a Third Design

Both the original (maximize decoupling) and the inverted (maximize accountability) are scalar points on the `decoupling × accountability = k` curve. Neither explores whether the curve's dimensionality is fixed.

**Predicted third design**: A schema-based event bus where failure contracts are declared per event type:

```python
@event_schema("user.created", on_no_handlers="raise", on_handler_failure="collect")
class UserCreatedEvent:
    user_id: str
    email: str
```

This design predicts that coupling is not global — it is **localizable to specific event types**. Critical events get `on_handler_failure="raise"` (full coupling, full accountability). Fire-and-forget events get `on_no_handlers="ignore"` (full decoupling, zero accountability). The conservation law's constant is not system-wide; it is per-schema. The scalar conservation law becomes a vector.

**What the prediction reveals**: The conservation law does not predict the schema design's failure mode, which is the most important finding. `on_no_handlers="warn"` emits a warning to... where? A logger the caller may not monitor? The schema declaration relocates the accountability question one level above the code — to whoever authored the schema — and that person is the developer, not the runtime.

This is what the conservation law actually predicts: **accountability cannot be destroyed by code; it resurfaces at the nearest human decision point above the implementation.** The schema design makes this visible for the first time. Every design in this space terminates accountability at a human: the caller who never checks `_dead_letter`, the subscriber author who catches silently, the schema author who chose "warn." The conservation law's constant is not `k` — it is the developer.
