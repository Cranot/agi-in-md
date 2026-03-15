## Falsifiable Claim: The Deepest Problem

**The EventBus promises dispatch (one-to-many, isolated) but implements a pipeline (sequential mutation of shared state).** This is falsifiable: given any two handlers that write to `context`, their observable behavior depends on registration order — a property invisible from either handler's source code alone.

```python
bus = EventBus()
bus.on("price", lambda ctx: ctx["payload"].update({"value": ctx["payload"]["value"] * 2}), priority=2)
bus.on("price", lambda ctx: ctx["payload"].update({"value": ctx["payload"]["value"] + 1}), priority=1)
bus.emit("price", {"value": 5})  # → 11

# Swap priorities → 12. Same handlers. Different system.
```

The system's identity is not determined by its declared components but by their ordering — a hidden global state.

---

## Three Experts Transform It

**The Type Theorist** sees an `Any`-typed dict as the symptom: every handler has write access to every other handler's contract. The fix is a typed read surface: handlers receive `Event`, return `HandlerResult`. The dict's "flexibility" is actually a refusal to commit to an interface.

**The Systems Reliability Engineer** sees that error handling violates execution isolation. When handler A throws, `context["error"] = e` overwrites itself on the next exception. Handler B then runs on a context that is semantically corrupted but syntactically valid. The try/except *looks* protective but propagates corruption to subsequent handlers.

**The Domain Modeler** sees `priority` as a code smell: it encodes implicit dependencies between handlers without naming them. Priority is a workaround for the absence of an explicit causality model. It makes inter-handler dependencies invisible to both the handlers and the caller.

---

## The Concealment Mechanism: Nominal Isolation

The code syntactically performs independence — separate `try` blocks, a `results` list, named handlers — while structurally coupling all execution through the shared mutable `context` dict. The isolation is a naming convention, not an enforcement boundary.

This is distinct from a bug. It is a **structural lie**: the interface contract (independent handlers receiving "an event") is contradicted by the implementation contract (handlers sharing a mutable baton). The concealment works because Python dicts are invisible coupling surfaces.

---

## Improvement That Deepens the Concealment

```python
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class EventContext:
    type: str
    payload: Any
    cancelled: bool = False
    error: Optional[Exception] = None
    results: list = field(default_factory=list)

    def cancel(self):
        self.cancelled = True

    def mark_error(self, e: Exception):
        self.error = e
```

This is worse than the original, precisely because it looks better. The dataclass gives the shared mutable state a *type*, making it appear principled. The `cancel()` method looks like an API contract but is still mutating shared state. The structured appearance has increased the concealment's depth — a reader now trusts the design because it resembles good practice.

---

## Three Properties Only Visible Through Construction

**1. Handler interference latency.** Handler A's mutation of `payload` creates a semantic delay for handler B that only manifests under specific payload shapes and handler orders. No amount of reading the code reveals this — it requires observing two handlers at runtime with a payload both attempt to modify.

**2. Dead letter queue as a failure heap.** The `_dead_letter` list conflates two categorically different failures: events with no subscribers (a routing problem) and events whose handlers threw (an execution problem). This is invisible until you try to implement dead letter processing and discover the cases are indistinguishable.

**3. Middleware nullability catastrophe.** If any middleware forgets `return context`, the next line `context = mw(context)` silently sets context to `None`. The crash occurs not at the middleware but at `context.get("cancelled")`, two lines later, with no indication of which middleware is responsible. This property only becomes visible when writing the second middleware.

---

## Applying the Diagnostic to the Improvement

The `EventContext` dataclass improvement fails the falsifiability test identically to the original:

```python
def handler_a(ctx: EventContext): ctx.payload["value"] *= 2
def handler_b(ctx: EventContext): ctx.payload["value"] += 1

# Priority A > B: {value: 5} → 11
# Priority B > A: {value: 5} → 12
```

The dataclass adds a type signature to the coupling surface but does not remove it. The improvement *deepened* concealment by adding apparent structure while preserving the structural problem. This is the diagnostic in action: improvements that address symptoms while leaving the invariant intact make the system harder to reason about, not easier.

---

## Second Improvement: Break the Invariant

```python
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeAlias
import copy

@dataclass(frozen=True)
class Event:
    type: str
    payload: Any  # Note: payload itself must also be immutable for full isolation

@dataclass(frozen=True)
class HandlerResult:
    handler_id: str
    value: Any
    error: Optional[Exception] = None

    @property
    def failed(self) -> bool:
        return self.error is not None

HandlerFn: TypeAlias = Callable[[Event], Any]
MiddlewareFn: TypeAlias = Callable[[Event], Optional[Event]]

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[tuple[int, str, HandlerFn]]] = {}
        self._middleware: list[MiddlewareFn] = []
        self._unrouted: list[Event] = []        # No subscribers
        self._faulted: list[tuple[Event, HandlerResult]] = []  # Execution errors

    def on(self, event_type: str, handler: HandlerFn,
           handler_id: str, priority: int = 0) -> None:
        self._handlers.setdefault(event_type, [])
        self._handlers[event_type].append((priority, handler_id, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn: MiddlewareFn) -> None:
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> list[HandlerResult]:
        event = Event(type=event_type, payload=payload)

        for mw in self._middleware:
            result = mw(event)
            if result is None:
                return []          # Explicit cancellation; no silent None-crash
            event = result         # Functional transform, not mutation

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._unrouted.append(event)
            return []

        results = []
        for _, handler_id, handler in handlers:
            try:
                value = handler(event)  # Immutable event: no handler can affect another
                results.append(HandlerResult(handler_id=handler_id, value=value))
            except Exception as e:
                r = HandlerResult(handler_id=handler_id, value=None, error=e)
                self._faulted.append((event, r))
                results.append(r)   # Error is recorded but execution continues cleanly

        return results
```

The key structural changes:

| Property | Before | After |
|---|---|---|
| Handler input | Shared mutable dict | Immutable `Event` |
| Handler output | Side-effect on context | Return value |
| Middleware effect | Mutation | Functional transform |
| Dead letter | One queue, two semantics | Two queues, one semantic each |
| Error isolation | Overwrites; corrupts | Isolated per handler |

---

## The Structural Invariant of the Original

**A single mutable object traverses all execution paths.** Middleware, handlers, error recording, and result collection all read from and write to the same dict. This is not incidental — it is the load-bearing structure. Every feature of the system depends on it: handler communication, middleware chaining, error propagation.

The invariant can be stated as a conservation principle: **in the original design, information only moves through mutation of the shared context**.

---

## Inversion: Where the Impossible Becomes Trivial

Invert the invariant: **no shared mutable state at any point**. Each handler receives an immutable snapshot and produces an independent result.

Things that were impossible become trivial:

- **Parallel execution**: Handlers can run concurrently — they share no mutable state.
- **Retroactive replay**: Events are values; any event can be replayed to any handler at any point in time. The original event is never consumed.
- **Deterministic testing**: Each handler is a pure function of an immutable event; no test requires constructing a prior handler chain.
- **Partial failure recovery**: A handler's exception is isolated in its `HandlerResult`; the event and all other results remain uncorrupted.

---

## The New Impossibility and the Conservation Law

**The new impossibility**: handlers cannot communicate with each other. In the original, handler A could write `context["validated"] = True` and handler B could skip expensive validation. This coordination pattern is now structurally impossible.

**The Conservation Law:**

> **Coupling is conserved. It cannot be eliminated — only relocated and made visible.**

In the original design: coupling is *implicit*, *temporal*, *distributed across all handlers*, and *invisible in any single handler's source*.

In the inverted design: coupling is *explicit*, *structural*, *localized in the event schema*, and *visible in type signatures*.

The total coupling in the system is constant. When you eliminate implicit coupling (shared mutable context), you produce an equal quantity of explicit coupling (the event type must now carry everything handlers need to coordinate). The "cheaper" handlers of the original design were cheap because they were borrowing coupling budget from the system's hidden state.

This is non-obvious because it resembles an engineering law rather than a software pattern: you can transform coupling from one form to another, but the system's total coordination requirements do not change. Immutability is not a reduction in coupling — it is a *legibility transformation* of coupling.

---

## Prediction: What a Third Design Reveals

A third design would attempt to recover inter-handler communication without returning to shared mutable state. The natural solution: **handlers communicate through the event bus itself** — handler results can emit new events, and those events are processed by other handlers. Each handler remains a pure function, but causality is expressed through event emission rather than context mutation.

This third design would reveal the original implementation's **root contradiction**: it conflated two categorically incompatible patterns.

The **Observer pattern** requires: broadcast, isolated handlers, no handler affects another, order is irrelevant.

The **Chain of Responsibility pattern** requires: sequential, each step transforms state, order is the definition of behavior.

These patterns have incompatible structural requirements. The original EventBus served both use cases with one mechanism — the shared mutable context — which is why it fails at both: it cannot safely broadcast (handlers interfere) and cannot reliably chain (errors corrupt the shared state mid-chain).

The third design would make this explicit: you would be forced to choose, for each event type, whether handlers *observe* it or *transform* it. The attempt to unify both in a single `emit()` call is the original contradiction, and the conservation law ensures it cannot be dissolved — only moved into the open where it can be named and managed.
