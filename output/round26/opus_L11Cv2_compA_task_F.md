# Structural Diagnostic: EventBus Conservation Law Analysis

## Falsifiable Claim

**The deepest structural problem:** The `context` dictionary serves simultaneously as data transport, control flow signal, error container, and result accumulator — making the system's correctness depend on implicit mutation-ordering protocols that no participant can reason about locally.

## Three Experts Test It

**Defender:** The shared context is a deliberate flexibility mechanism. Middleware enriching context for downstream handlers is the *feature*. Plain dicts are idiomatic Python — this is readable, extensible, and avoids premature type hierarchies.

**Attacker:** The shared mutability produces real defects: (1) `context["error"]` is overwritten by each failing handler — only the *last* error survives; (2) if a handler mutates `payload`, subsequent handlers see the mutation silently; (3) the dead letter queue conflates two fundamentally different failure modes (no handlers registered vs. handler threw exception) making monitoring impossible; (4) middleware returns a transformed context (pipeline pattern) but handlers receive context and return arbitrary values (observer pattern) — two computational models forced through one channel.

**Assumption-Prober:** Is mutation ordering really *deeper* than the missing handler deregistration? Than the O(n log n) re-sort on every `on()` call? The claim assumes local reasoning is the goal — but if all participants are known at design time, the implicit protocol is fine. What makes this deeper than a missing `off()` method?

## The Diagnostic Gap

Under pressure, the claim transforms: it's not really about mutation — it's that **the system has no separation between the envelope (routing, lifecycle, cancellation) and the letter (payload, results)**. The `context` dict is both simultaneously.

## Concealment Mechanism: Legibility-as-False-Contract

The code hides its problems through **duck-typing fluency**. Every operation on `context` looks natural: `context.get("cancelled")` reads as clean, intentional design. The dict's openness makes every access look legitimate. The readability *is* the concealment — it creates the illusion that the implicit protocol is explicit.

---

## First Improvement (Deepens Concealment)

```python
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

@dataclass
class EventContext:
    event_type: str
    payload: Any
    cancelled: bool = False
    error: Optional[Exception] = None
    results: List[Any] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[tuple[int, Callable]]] = {}
        self._middleware: list[Callable] = []
        self._dead_letter: list[EventContext] = []

    def on(self, event_type: str, handler: Callable, priority: int = 0):
        self._handlers.setdefault(event_type, []).append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn: Callable[[EventContext], EventContext]):
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> EventContext:
        ctx = EventContext(event_type=event_type, payload=payload)
        for mw in self._middleware:
            ctx = mw(ctx)
            if ctx.cancelled:
                return ctx
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(ctx)
            return ctx
        for _, handler in handlers:
            try:
                ctx.results.append(handler(ctx))
            except Exception as e:
                ctx.error = e
                self._dead_letter.append(ctx)
        return ctx
```

This *deepens* the concealment: the dataclass creates a **false sense of type safety**. `payload: Any` and `metadata: dict` remain unbounded. The singular `error: Optional[Exception]` still silently drops all but the last failure. But it *looks* controlled.

## Three Properties Visible Only From Strengthening

1. **Errors are plural but the field is singular** — typing forces the choice `Optional[Exception]` vs `List[Exception]`, making visible that multiple handlers can fail but only one error survives.
2. **Results have no handler correspondence** — results are positional with no identity; if handler 3 of 5 throws, result indices no longer map to handler indices, and nothing records *which* handler produced *which* result.
3. **The `metadata` escape hatch recreates the original problem** — any attempt to close the dict's openness must provide an extension point, which reproduces the exact same uncontrolled mutation surface one level deeper.

## Diagnostic Applied to Improvement

**What it conceals:** The fundamental **asymmetry between middleware and handlers**. Middleware transforms-and-returns (pipeline). Handlers receive-and-side-effect (observer). These are two different computational models coerced through one type. The dataclass makes both look like they work with "the same well-typed thing" when their relationships to that thing are structurally different.

**What property of the original is visible only because the improvement recreates it:** The original's plain dict makes the *accidental symmetry* between middleware and handlers visible — they both "just work with a dict." The improvement reveals they have different contracts, but then re-conceals this through the single `EventContext` type.

---

## Second Improvement

```python
from dataclasses import dataclass, field
from typing import Any, Callable, FrozenSet
import time

@dataclass(frozen=True)
class Envelope:
    event_type: str
    timestamp: float
    cancelled: bool = False
    tags: FrozenSet[str] = field(default_factory=frozenset)

    def cancel(self) -> "Envelope":
        return Envelope(self.event_type, self.timestamp, cancelled=True, tags=self.tags)

    def tag(self, *new_tags: str) -> "Envelope":
        return Envelope(self.event_type, self.timestamp, self.cancelled, self.tags | set(new_tags))

@dataclass(frozen=True)
class Letter:
    payload: Any

@dataclass
class HandlerError:
    handler_name: str
    exception: Exception

@dataclass
class DispatchResult:
    envelope: Envelope
    letter: Letter
    results: list[tuple[str, Any]] = field(default_factory=list)  # (handler_name, result)
    errors: list[HandlerError] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[tuple[int, str, Callable]]] = {}
        self._middleware: list[Callable[[Envelope], Envelope]] = []
        self._unhandled: list[tuple[Envelope, Letter]] = []    # no handlers registered
        self._error_log: list[tuple[Envelope, HandlerError]] = []  # handler failures

    def on(self, event_type: str, handler: Callable, *, name: str = "", priority: int = 0):
        handler_name = name or getattr(handler, "__name__", repr(handler))
        self._handlers.setdefault(event_type, []).append((priority, handler_name, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def off(self, event_type: str, handler: Callable):
        if event_type in self._handlers:
            self._handlers[event_type] = [
                (p, n, h) for p, n, h in self._handlers[event_type] if h is not handler
            ]

    def use(self, middleware_fn: Callable[[Envelope], Envelope]):
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> DispatchResult:
        envelope = Envelope(event_type=event_type, timestamp=time.time())
        letter = Letter(payload=payload)

        # Middleware: transforms envelope only, never sees payload
        for mw in self._middleware:
            envelope = mw(envelope)
            if envelope.cancelled:
                return DispatchResult(envelope, letter)

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._unhandled.append((envelope, letter))
            return DispatchResult(envelope, letter)

        result = DispatchResult(envelope, letter)
        for _, handler_name, handler in handlers:
            try:
                value = handler(envelope, letter)
                result.results.append((handler_name, value))
            except Exception as e:
                err = HandlerError(handler_name, e)
                result.errors.append(err)
                self._error_log.append((envelope, err))

        return result
```

## Diagnostic Applied to Second Improvement

**What it conceals:** The **temporal coupling problem**. The relationship between `on()` (registration time) and `emit()` (dispatch time) is unmediated. Events emitted before a handler registers are permanently lost. The `_unhandled` queue captures events with no handlers *right now*, but if a handler registers one millisecond later, those events remain in the dead pile. The clean envelope/letter separation makes this *harder* to see because the system looks so well-structured that you assume it handles lifecycle correctly.

---

## The Structural Invariant

Through every improvement, this persists:

> **The system must commit to a dispatch decision at emit-time using only registration-time information, but the correctness of that decision depends on the full lifecycle of all participants, which extends beyond both moments.**

This is a property of the problem space: any pub-sub system with independent publisher/subscriber lifecycles faces an irreducible gap between "when an event occurs" and "when all interested parties exist."

---

## Inversion: Make the Impossible Trivial

The "impossible" is: guaranteeing every event reaches every interested party regardless of registration timing. Make that trivial:

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator
import time

@dataclass(frozen=True)
class LogEntry:
    sequence: int
    event_type: str
    payload: Any
    timestamp: float

class EventLog:
    """Append-only event log with retroactive subscription."""

    def __init__(self):
        self._log: list[LogEntry] = []
        self._cursors: dict[str, int] = {}  # subscriber_id -> last-read position

    def append(self, event_type: str, payload: Any) -> int:
        entry = LogEntry(len(self._log), event_type, payload, time.time())
        self._log.append(entry)
        return entry.sequence

    def subscribe(
        self,
        subscriber_id: str,
        filter_fn: Callable[[LogEntry], bool] = lambda _: True,
        replay_from: int = 0,
    ) -> Iterator[LogEntry]:
        """Subscribe and replay all matching historical events from any point."""
        self._cursors[subscriber_id] = replay_from
        for entry in self._log[replay_from:]:
            if filter_fn(entry):
                yield entry
        self._cursors[subscriber_id] = len(self._log)

    def poll(self, subscriber_id: str,
             filter_fn: Callable[[LogEntry], bool] = lambda _: True) -> list[LogEntry]:
        cursor = self._cursors.get(subscriber_id, 0)
        matches = [e for e in self._log[cursor:] if filter_fn(e)]
        self._cursors[subscriber_id] = len(self._log)
        return matches

    def snapshot(self, up_to: int) -> list[LogEntry]:
        return list(self._log[:up_to])
```

Late subscribers seeing past events is now trivial — it's just reading the log from any offset.

## The New Impossibility

1. **Unbounded memory**: The log must grow without limit or be compacted, which reintroduces the original problem (events compacted away are invisible to future subscribers).
2. **No in-flight transformation**: Events are immutable facts. Middleware-as-transformation is structurally impossible — you cannot cancel or reshape what has already been recorded.

---

## The Conservation Law

| | EventBus (Original) | EventLog (Inverted) |
|---|---|---|
| **Trivial** | In-flight transformation, cancellation, middleware | Retroactive delivery, temporal completeness |
| **Impossible** | Reaching future subscribers, temporal completeness | In-flight transformation, bounded resources |

**The conservation law:**

> **In any event system, _commitment to the past_ and _freedom in the present_ are conserved. You cannot simultaneously guarantee that all events are replayable to future participants AND that events can be transformed, cancelled, or discarded in-flight. The total of "what you can promise about history" plus "what you can change about events in transit" is fixed.**

This is **not** the obvious memory-vs-completeness trade-off. It is a statement about **mutability and temporality being dual**: middleware *requires* that events be ephemeral (you can only transform what hasn't been committed), while replay *requires* that events be immutable (you can only replay what hasn't been transformed). These are the positive and negative expressions of the same structural constraint.

## What This Reveals Beyond Senior-Engineer Knowledge

**Middleware and event sourcing are duals of the same impossibility.** A system claiming to offer both — "middleware that transforms events before they're stored in the log" — is secretly implementing a two-phase protocol between two separate event systems, not one unified system. The boundary between those two phases is the *real* architectural decision, and it's the one that's never made explicit in any EventBus or EventLog API. Every "event-driven architecture" debate about "should we use a bus or a log" is actually a debate about where to place the phase boundary between mutable-present and immutable-past.

## Prediction About a Third Design Neither Attempted

A **reactive streams / windowed-backpressure design** (à la Kafka Streams, RxPY) will attempt to cheat the conservation law by offering *bounded replay* (time-windowed retention) and *limited transformation* (stream operators). The conservation law predicts it will pay with a **third currency: causal ordering**. Specifically:

- Partitioned windows will allow some replay (partial temporal completeness) and some transformation (partial present-freedom)
- But events processed through different operators/partitions will **not see a consistent causal history**
- The system will exhibit "causal incompleteness" — the inability to guarantee that two consumers of the same event stream observe the same ordering of effects

This is exactly what we observe empirically in every streaming system (Kafka's partition-local ordering, Flink's watermark heuristics, RxPY's scheduler-dependent ordering). The conservation law predicts this is not an implementation limitation but a structural necessity: the third design borrows from both sides of the conservation law and pays the cost in a third dimension that neither the EventBus nor the EventLog needed to sacrifice.
