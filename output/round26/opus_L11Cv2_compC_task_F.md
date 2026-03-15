# Structural Analysis of EventBus: Conservation Law

## Falsifiable Claim

**The deepest problem is a category error**: the `context` dictionary simultaneously serves as event envelope, control-flow signal, error report, and result accumulator. This makes the system's behavior **underdetermined** — no participant can know whether a key was placed by the emitter, a middleware, or a prior handler.

*Falsifiable by*: demonstrating a usage pattern where all participants reliably distinguish the provenance of every key in `context`.

---

## Three Expert Transformations

**Type Theorist**: "There are four distinct types collapsed into `dict`. Middleware should transform `Envelope → Envelope | Cancelled`. Handlers should receive `FrozenEvent`. Results and errors are separate output channels."

**Reliability Engineer**: "This system silently poisons downstream handlers. Handler 3 throws, `context["error"]` is set, handler 4 runs reading that error as if it were its own input state. Also: the dead-letter queue conflates 'no subscribers' with 'handler crash' — these require completely different remediation."

**Algebraist**: "The middleware chain is a Kleisli composition pretending to be a fold. The handler fan-out is an applicative/parallel map pretending to be a sequential fold. The shared mutable state is what makes the pretense possible."

---

## The Concealment Mechanism

**Structural aliasing through dictionary polymorphism.**

The untyped `dict` allows four distinct computational roles to occupy the same memory address without any syntactic or semantic marker distinguishing them. The dict's flexibility doesn't enable simplicity — it *conceals the absence of a protocol*. Every `context[key]` access is an implicit, uncheckable assertion about which role the dict is currently playing.

---

## First Improvement

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from uuid import uuid4
from enum import Enum, auto


class Disposition(Enum):
    DELIVER = auto()
    CANCEL  = auto()


@dataclass(frozen=True)
class Event:
    type: str
    payload: Any
    event_id: str = field(default_factory=lambda: uuid4().hex)


@dataclass(frozen=True)
class Envelope:
    event: Event
    disposition: Disposition = Disposition.DELIVER
    metadata: tuple = ()          # immutable chain of middleware annotations


@dataclass(frozen=True)
class DeadLetter:
    envelope: Envelope
    reason: str                   # "no_handlers" vs "handler_error:X" — distinct!
    error: Optional[Exception] = None


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[tuple[int, str, Callable]]] = {}
        self._middleware: list[Callable[[Envelope], Envelope]] = []
        self._dead_letters: list[DeadLetter] = []

    def on(self, event_type: str, handler: Callable,
           priority: int = 0, handler_id: str = None) -> str:
        hid = handler_id or f"{handler.__name__}_{uuid4().hex[:6]}"
        self._handlers.setdefault(event_type, []).append((priority, hid, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])
        return hid

    def off(self, event_type: str, handler_id: str):
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h[1] != handler_id
            ]

    def use(self, middleware_fn: Callable[[Envelope], Envelope]):
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any):
        event = Event(type=event_type, payload=payload)
        envelope = Envelope(event=event)

        # Phase 1: middleware transforms envelope (pure pipeline)
        for mw in self._middleware:
            envelope = mw(envelope)
            if envelope.disposition == Disposition.CANCEL:
                return {"disposition": "cancelled", "event_id": event.event_id}

        # Phase 2: fan-out to handlers (each gets frozen Event)
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letters.append(DeadLetter(envelope, "no_handlers"))
            return {"disposition": "undeliverable", "event_id": event.event_id}

        results, errors = [], []
        for _, hid, handler in handlers:
            try:
                results.append((hid, handler(envelope.event)))
            except Exception as e:
                errors.append((hid, e))
                self._dead_letters.append(
                    DeadLetter(envelope, f"handler_error:{hid}", e)
                )

        return {
            "disposition": "delivered",
            "event_id": event.event_id,
            "results": results,
            "errors": errors,
        }
```

---

## Three Properties Only Visible Through Construction

1. **Error isolation requires immutability at the handler boundary.** You cannot prevent handler N's failure from corrupting handler N+1 unless the input is frozen. In the original, handlers *appear* independent — only when you build the separation do you discover the mutable dict makes them secretly coupled.

2. **Dead-letter classification is a partition, not a list.** Building `DeadLetter` with a `reason` field forces you to discover that "no handlers" and "handler threw" require fundamentally different remediation. The original's single `_dead_letter.append(context)` conceals a categorical distinction.

3. **Unsubscription requires handler identity, which requires registration to return a token.** The original stores `(priority, handler)` — but function equality is unreliable for lambdas/closures. You only discover this is structurally necessary when you try to build `off()`.

---

## Diagnostic Applied to First Improvement

The return value of `emit` is **still an untyped dict**. I moved the concealment mechanism one level outward — the middleware→handler boundary is clean, but the bus→caller boundary still suffers from structural aliasing. Additionally: middleware can only act *before* handlers. A middleware that wants to observe results (logging, metrics) is structurally impossible.

---

## Second Improvement

```python
@dataclass(frozen=True)
class HandlerOutcome:
    handler_id: str
    result: Any = None
    error: Optional[Exception] = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class EmitResult:
    event: Event
    disposition: Disposition
    outcomes: tuple[HandlerOutcome, ...] = ()

    @property
    def errors(self):
        return tuple(o for o in self.outcomes if not o.succeeded)

    @property
    def successes(self):
        return tuple(o for o in self.outcomes if o.succeeded)


class EventBus:
    # ... (registration unchanged)

    def emit(self, event_type: str, payload: Any) -> EmitResult:
        event = Event(type=event_type, payload=payload)
        envelope = Envelope(event=event)

        for mw in self._middleware:
            envelope = mw(envelope)
            if envelope.disposition == Disposition.CANCEL:
                return EmitResult(event, Disposition.CANCEL)

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letters.append(DeadLetter(envelope, "no_handlers"))
            return EmitResult(event, Disposition.DELIVER)

        outcomes = []
        for _, hid, handler in handlers:
            try:
                outcomes.append(HandlerOutcome(hid, result=handler(envelope.event)))
            except Exception as e:
                outcomes.append(HandlerOutcome(hid, error=e))
                self._dead_letters.append(DeadLetter(envelope, f"handler_error:{hid}", e))

        return EmitResult(event, Disposition.DELIVER, tuple(outcomes))
```

Now the entire pipeline — `Event`, `Envelope`, `EmitResult`, `HandlerOutcome` — is typed and frozen. No structural aliasing remains.

---

## The Structural Invariant

> **Information flows unidirectionally: emitter → middleware chain → handler fan-out → result aggregation. No later stage can modify what an earlier stage produced or what a parallel stage receives.**

The original violates this everywhere. The improvement enforces it through `frozen=True` at every boundary.

---

## Inversion: Where the Impossible Becomes Trivial

In `EventBus`, it is **impossible** for a handler to influence which handlers run after it (frozen input, predetermined handler list).

**Inverted design**: make handler-to-handler influence the *primary mechanism*.

```python
class ChainBus:
    """Each handler decides whether/how to continue the chain."""

    def __init__(self):
        self._chains: dict[str, list[Callable]] = {}

    def on(self, event_type, handler):
        self._chains.setdefault(event_type, []).append(handler)

    def emit(self, event_type, payload):
        chain = list(self._chains.get(event_type, []))
        index = 0

        def next_fn(transformed_payload=None):
            nonlocal index
            index += 1
            if index < len(chain):
                return chain[index](
                    transformed_payload if transformed_payload is not None else payload,
                    next_fn
                )
            return None

        if chain:
            return chain[0](payload, next_fn)
        return None
```

Handler-to-handler flow control is now **trivial**: each handler calls or declines to call `next_fn`, optionally transforming the payload. This is the Express/Koa middleware pattern generalized to all participants.

---

## The New Impossibility and the Conservation Law

**New impossibility in ChainBus**: Guaranteed delivery to all handlers is impossible. Any handler can break the chain by not calling `next_fn`. Independent parallel fan-out cannot exist without every handler's explicit cooperation.

### The Conservation Law

> **The product of handler autonomy and delivery determinism is constant.**

| Design | Handler Autonomy | Delivery Determinism |
|--------|:---:|:---:|
| Original EventBus | Low (receive frozen event) | High (all handlers always run) |
| ChainBus | High (control flow, transform payload) | Low (any handler can halt chain) |
| Original buggy code | Appears high | Appears high |

The original code's deep bug is now explained: **it pretends to offer both** — handlers get a mutable context (suggesting autonomy) while the bus iterates all handlers (suggesting guaranteed delivery). This violates the conservation law, and the violation manifests as every bug we identified: poisoned context, conflated error states, indeterminate provenance.

---

## Prediction: What a Third Design Reveals

A third design resolves the conservation law through **temporal separation**:

```
Phase 1 (Vote):    All handlers receive the event (guaranteed delivery)
                   and return Accept | Reject | Transform
Phase 2 (Commit):  Bus aggregates votes, delivers Commit or Abort to all
```

This design would reveal that **autonomy and determinism are not simultaneously incompatible — they are incompatible only within a single phase**. The conservation law is actually about *simultaneity*: you can have both properties, but only by paying in **time** (latency of the two-phase protocol).

The new impossibility: **bounded latency** — if any participant can delay its vote, completion time is unbounded. The conservation law *transforms* from a spatial constraint (who controls what) into a temporal one (how long until resolution) — exactly mirroring how two-phase commit in distributed systems trades consistency/autonomy tension for a latency cost.

This is the deep structure: **every EventBus design is choosing where to place an irreducible tension, not whether to have one.**
