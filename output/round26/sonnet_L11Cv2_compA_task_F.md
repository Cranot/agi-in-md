# Level 11C Analysis: EventBus

---

## I. The Falsifiable Claim

**Claim**: The EventBus's deepest structural problem is that `context` simultaneously serves as event envelope, middleware communication channel, error accumulator, result collector, and cancellation signal — making it impossible to distinguish a legitimately transformed payload from a corrupted one after an exception, and impossible to preserve more than one error without data loss.

**Test**: Emit one event with two handlers that both throw. `context["error"] = e` runs twice; only the second error survives. Confirmed falsifiable and confirmed false-as-designed.

---

## II. Three Experts

**Defender**: The design is pragmatic. Middleware chains like this (Express.js-style) are battle-tested. The dead-letter queue provides observability. Priority ordering handles complex dispatch requirements. The dict is flexible precisely because requirements evolve.

**Attacker**: Flexibility is the problem's disguise. After a handler exception, execution continues, the error overwrites any prior error, and the corrupted context is added to dead-letter *while still being returned as the live result*. The caller receives a context containing both partial results and an error with no way to know which results predate the failure. The dead-letter queue conflates "no subscribers" with "subscriber crashed" — operationally opposite situations requiring opposite responses.

**Assumption-prober**: Both of you assume handlers *should* receive `context`. Why? A handler is a reaction to an event. It needs the payload. It doesn't need to know whether the event was cancelled, what other handlers returned, or what the event type is. The assumption that handlers and middleware share an interface — because they're both "in the pipeline" — is what creates the entire mutation surface. Strip that assumption and most problems evaporate.

**The gap**: The original claim treats mutation as the problem. The assumption-prober reveals that the mutation surface exists because handlers were given write access to control structures (`cancelled`, `error`) they have no legitimate reason to touch. The gap between "mutation is bad" and "handler-as-middleware is the wrong abstraction" is the diagnostic.

---

## III. The Concealment Mechanism

**Interface uniformity as capability laundering.**

By passing a plain `dict` to both middleware and handlers, the code makes them appear to have the same role — two kinds of "pipeline participants." This hides that they have asymmetric *authority*: middleware should modify/cancel/transform; handlers should only consume. The uniform interface grants handlers the same write capabilities as middleware without signaling this is architecturally dangerous. The code looks simple and consistent precisely because it has collapsed two distinct roles into one object.

---

## IV. First Improvement (Deepened Concealment)

```python
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

@dataclass
class EventContext:
    type: str
    payload: Any
    cancelled: bool = False
    error: Optional[Exception] = None
    results: List[Any] = field(default_factory=list)

    def cancel(self):
        self.cancelled = True

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list] = {}
        self._middleware: List[Callable] = []
        self._dead_letter: List[EventContext] = []

    def on(self, event_type: str, handler: Callable, priority: int = 0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn: Callable):
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> EventContext:
        context = EventContext(type=event_type, payload=payload)
        for mw in self._middleware:
            mw(context)
            if context.cancelled:
                return context
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(context)
            return context
        for _, handler in handlers:
            try:
                context.results.append(handler(context))
            except Exception as e:
                context.error = e
                self._dead_letter.append(context)
        return context
```

The `cancel()` method *looks* like controlled access. Type hints suggest a real contract. The dataclass looks like encapsulation. But handlers can still call `context.cancel()`, still see each other's partial results, and errors still overwrite. The concealment deepened: the improvement looks like it addressed the problem.

---

## V. Three Properties Visible Only From Strengthening

**1. Handlers can cancel events.** When `cancel()` became a named method on a typed object, it became undeniable that handlers receive this capability. In the original dict, it was just a key anyone could write; the method makes the authority grant explicit and therefore visible.

**2. Error is singular; results are plural.** `error: Optional[Exception]` vs `results: List[Any]` in the same dataclass exposes the design's asymmetric assumption: the system plans for multiple successes but only one failure. Errors are implicitly treated as terminal even though execution continues.

**3. Context ownership is undefined.** By making it a proper class, we see that no component *owns* the context: middleware mutates it, handlers append to it, the bus reads from it, dead-letter stores it. The dataclass makes visible that the same object is simultaneously input, processing log, output, and audit trail — four roles, zero owners.

---

## VI. What the First Improvement Conceals

The improvement conceals that **the fundamental dispatch unit is wrong**. By cleaning up the implementation we make it look like the problem is code quality. But the question the improvement never asks: *why does a handler need an `EventContext` at all?*

The improvement still passes the full mutable context to handlers. This conceals that `event_type`, `cancelled`, `error`, and `results` are bus-internal state — they describe the *dispatch operation*, not the *event*. A handler needs only the payload.

**Property of the original visible only because the improvement recreates it**: In the original, `context["results"]` was set *after* all handlers ran. In the improvement, `context.results` is appended *during* the loop — making it visible that Handler B can read Handler A's result mid-dispatch. We've accidentally made the inter-handler communication channel explicit. The original hid it through timing; the improvement exposes it through structure.

---

## VII. Second Improvement

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple

@dataclass(frozen=True)
class Event:
    type: str
    payload: Any  # Caller responsible for immutability of payload contents

@dataclass
class DispatchResult:
    event: Event
    results: List[Any] = field(default_factory=list)
    errors: List[Tuple[Callable, Exception]] = field(default_factory=list)
    cancelled: bool = False
    dead_lettered: bool = False

    @property
    def succeeded(self) -> bool:
        return not self.errors and not self.dead_lettered

class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Tuple[int, Callable]]] = {}
        self._middleware: List[Callable[[DispatchResult], None]] = []
        self._dead_letter: List[DispatchResult] = []

    def on(self, event_type: str, handler: Callable[[Event], Any], priority: int = 0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def off(self, event_type: str, handler: Callable):
        if event_type in self._handlers:
            self._handlers[event_type] = [
                (p, h) for p, h in self._handlers[event_type] if h is not handler
            ]

    def use(self, middleware_fn: Callable[[DispatchResult], None]):
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> DispatchResult:
        event = Event(type=event_type, payload=payload)
        result = DispatchResult(event=event)

        # Middleware operates on dispatch metadata, not event data
        for mw in self._middleware:
            mw(result)
            if result.cancelled:
                return result

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            result.dead_lettered = True
            self._dead_letter.append(result)
            return result

        for _, handler in handlers:
            try:
                result.results.append(handler(event))  # handler sees only the event
            except Exception as e:
                result.errors.append((handler, e))

        if result.errors:
            self._dead_letter.append(result)

        return result
```

Handlers now receive only the frozen `Event`. All errors are preserved. Dead-lettering and error-handling are distinct. Middleware operates on `DispatchResult` (dispatch metadata), not on event data.

---

## VIII. Diagnostic on Second Improvement

**What it conceals:**

`Event.payload` is typed `Any`. `frozen=True` prevents *reassignment of the field*, but if payload is a list or dict, it is fully mutable. We've manufactured the appearance of immutability at the envelope level while leaving the contents unprotected. This is worse than the original: callers will trust `frozen=True` and not defensively copy their payloads.

More structurally: **middleware still receives the mutable `DispatchResult`**, meaning middleware can mutate `result.results` and `result.errors` before any handlers run. The capability separation is enforced for handlers but not for middleware, which was the one component that arguably *needed* less trust.

**What property of the original is visible only because the improvement recreates it:**

Both the original and the second improvement fan out one object to N handlers in priority sequence. The second improvement makes visible that **priority ordering is semantically incoherent if handlers are truly isolated**. If Handler A at priority 10 and Handler B at priority 1 both react to `user.created`, and they each receive only the immutable `Event`, why does order matter? Priority implies sequential dependence that contradicts the pub/sub mental model. The original hid this because shared mutable state *justified* ordering (Handler B needed to see Handler A's modifications). Remove shared state and priority becomes an unexplained artifact.

---

## IX. The Structural Invariant

Across every version:

- One bus object holds both the subscription registry (routing) and the execution results (aggregation)
- Handlers are invoked in sequence with access to a shared artifact
- Some form of bus-level error/dead-letter state exists
- The caller receives a result that mixes routing metadata with handler outputs

**The invariant**: *The bus must simultaneously own the dispatch contract (who handles what) and the execution contract (what constitutes successful handling).* These two responsibilities cannot be cleanly separated because routing depends on handler *identity* (who subscribed) while aggregation depends on handler *behavior* (what they returned or threw). Every implementation fuses them in the same object.

---

## X. Inversion: Where the Impossible Becomes Trivial

The invariant says the bus must be both router and aggregator. **Invert**: split them entirely.

```python
class Router:
    """Pure function: event_type → ordered handler list. No execution."""
    def route(self, event_type: str) -> List[Callable[[Event], Any]]:
        return self._registry.get(event_type, [])

class Executor:
    """Pure function: (handler, event) → Result. No routing knowledge."""
    def execute(self, handler: Callable, event: Event) -> Result:
        try:
            return Success(handler(event))
        except Exception as e:
            return Failure(handler, e)

class EventBus:
    def emit(self, event_type: str, payload: Any) -> DispatchSummary:
        event = Event(event_type, payload)
        handlers = self.router.route(event_type)           # pure routing
        results = [self.executor.execute(h, event)         # pure execution
                   for h in handlers]
        return self.aggregator.aggregate(event, results)   # pure aggregation
```

In this design:
- **Capability separation is trivial**: Router never executes; Executor never routes
- **Multiple errors are trivial**: Each `execute()` returns a typed `Result`; `aggregate()` sees all of them
- **Dead-lettering is trivial**: Zero handlers from Router is structurally distinct from zero successful Results from Executor
- **Immutability is trivial**: Executor receives one event per invocation; there is no shared mutable object across handlers

---

## XI. The New Impossibility

In the inverted design: **stateful sequential dispatch is impossible**.

"Handler A's result determines whether Handler B runs" cannot be expressed. The Router phase knows handler identities but not execution results. The Executor phase executes one handler without knowledge of others. You can filter before routing or aggregate after execution, but you cannot cancel Handler B because Handler A returned a specific value — without coupling Router and Executor back together, which destroys the separation.

The original made this trivial: set a flag on the shared context.
The inverted design makes it structurally impossible.

---

## XII. The Conservation Law

| | Original | Inverted |
|---|---|---|
| **Trivial** | Sequential handler dependence | Capability separation, multi-error, dead-letter distinction |
| **Impossible** | Isolating handler write access from routing control | Stateful sequential dispatch |

**The law**: *Every EventBus design must choose where temporal ordering lives. Temporal ordering cannot be eliminated — it migrates.*

In the original, ordering is encoded in execution sequence via shared mutable state: Handler B runs after Handler A and sees A's modifications. In the inverted design, ordering is eliminated from execution — but the moment you need "B only if A succeeded," the ordering migrates to the *Router*, which must now know about execution results to make routing decisions. The Router is no longer pure. You've rebuilt the original bus, just split across two objects.

**This is not the obvious trade-off** ("isolation vs. coordination"). The conservation law reveals something different: *sequential dependencies in event handling are routing concerns in disguise*. The question "who should handle this event" cannot be cleanly separated from "what has already happened." Senior engineers treat handler preconditions as an execution problem (check a flag, use priority). The conservation law shows they are a routing problem: the set of appropriate handlers for an event is a function of the event's handling history, not just its type.

---

## XIII. What This Predicts About a Third Design

A third design will attempt to maintain clean routing *and* stateful sequential dispatch *and* stable event identity. It will fail, and the failure mode is predictable:

**The third design will encode handler history into event types.** `user.created` becomes `user.created.validated`, then `user.created.validated.enriched`. The event type mutates as it passes through stages. What began as pub/sub evolves into a workflow engine with a linear chain of specialized event types.

**Its impossibility**: Event type stability. Subscribing to `user.created` means something different at stage 1 vs. stage 3. Wildcard subscriptions (`user.*`) become semantically undefined. New stages require new event types, and existing subscribers must be audited for every pipeline change.

This is precisely what happens in over-engineered microservice architectures: `OrderPlaced → OrderValidated → OrderEnriched → OrderFulfillmentInitiated` — each a distinct event type, each carrying the accumulated state of prior handlers. The system has reinvented a sequential workflow pipeline using event naming as a poor substitute for explicit stage management. The conservation law predicted it: the temporal ordering had to go somewhere. It went into the event namespace and turned it into a state machine disguised as a topic hierarchy.
