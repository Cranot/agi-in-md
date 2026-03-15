## Claim

**The EventBus's deepest problem is that its `context` dict is simultaneously a transformation target, a return value, and an audit record — three roles with incompatible ownership semantics, collapsed into one mutable object.**

Falsifiable: if you can design a fix that separates these roles and the bus still works, the claim holds. If you can't separate them without breaking the architecture, the claim points at something deeper.

---

## Dialectic

**Defender:** The claim is precise. When a handler throws, `context["error"] = e` overwrites any previous error, then the poisoned context is appended to `_dead_letter`. The dead letter queue receives both unhandled events and errored events — routing failures and execution failures — stored identically. You cannot post-process the dead letter queue without re-categorizing what you find. The context is simultaneously being written by handlers, read by the caller via `emit()`'s return value, and stored as an audit record. Three writers, three readers, one object.

**Attacker:** This is too fine-grained. The real problem is simpler: `emit()` has no partial-failure semantics. If three handlers run and one throws, two results and one error accumulate — but the context returned to the caller mixes them without indicating whether the emit "succeeded." The shared-dict problem is a symptom, not the disease. Fix the return contract and the ownership problem dissolves.

**Prober:** Both of you assume you know what this thing is. It's an EventBus. But look at what it actually implements: a middleware pipeline (sequential transforms with cancellation), a priority-sorted handler dispatcher, and an audit log (dead letter accumulation). These are three different architectural patterns with three different state models. The pipeline owns state and transforms it. The dispatcher routes to independent handlers who own their own state. The audit log snapshots state for later inspection. The shared context problem exists because you've welded three systems together that have incompatible assumptions about who owns what.

**The gap:** I claimed the problem was *data ownership*. The dialectic revealed the problem is *architectural identity*. The EventBus doesn't know what it is — pipeline, dispatcher, or audit log — and the mutable context is the evidence, not the cause.

---

## Concealment Mechanism: Method Completeness Theater

The API surface — `on()`, `use()`, `emit()`, dead letter, priority, middleware chain — performs "complete event bus" so convincingly that the identity crisis is invisible. Each method is individually correct. The concealment is in their co-location: three incompatible architectural patterns look like one coherent system because they share a namespace.

**Applied:** The `emit()` method is where the three identities must simultaneously satisfy their incompatible contracts. As a pipeline, it must propagate transformed context. As a dispatcher, it must isolate handlers from each other's side effects. As an audit log, it must snapshot state at failure time. The method attempts all three. When a handler errors, it must simultaneously continue dispatch, record for audit, and... rollback pipeline transforms? It cannot. So it does none correctly, but each failure is local enough to look like a bug rather than a design contradiction.

---

## Improvement 1 (Passes Code Review, Deepens Concealment)

```python
from dataclasses import dataclass, field
from typing import Any, List, Optional

@dataclass
class DeadLetterEntry:
    reason: str          # "no_handlers" | "handler_error" | "middleware_cancelled"
    event_type: str
    payload: Any
    error: Optional[Exception] = None

class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter: List[DeadLetterEntry] = []

    def on(self, event_type, handler, priority=0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type, payload):
        context = {
            "type": event_type,
            "payload": payload,
            "cancelled": False,
            "results": [],
            "errors": [],
        }
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                self._dead_letter.append(DeadLetterEntry(
                    reason="middleware_cancelled",
                    event_type=event_type,
                    payload=payload,
                ))
                return context

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(DeadLetterEntry(
                reason="no_handlers",
                event_type=event_type,
                payload=payload,
            ))
            return context

        for _, handler in handlers:
            try:
                context["results"].append(handler(context))
            except Exception as e:
                context["errors"].append(e)
                self._dead_letter.append(DeadLetterEntry(
                    reason="handler_error",
                    event_type=event_type,
                    payload=payload,
                    error=e,
                ))

        return context
```

This passes code review cleanly. `DeadLetterEntry` is typed and structured. Errors accumulate rather than overwrite. Dead letter entries carry reason codes — you can now distinguish routing failures from execution failures. Middleware cancellations are also recorded. Every original complaint is addressed.

---

## Three Properties Only Visible Because I Tried to Strengthen It

**1. The `payload` in dead letter entries is the same object as in `context["payload"]` — not a snapshot.**
When I wrote `DeadLetterEntry(... payload=payload ...)`, I realized I was storing a reference to the caller's original payload object. Post-emit mutations by the caller retroactively corrupt the audit trail. In the original, this was invisible because the dead letter received the whole context dict (obviously live). The improvement created a *structural distinction* between the audit record and the return value — and then connected them to the same underlying data. The distinction is nominal.

**2. Middleware can corrupt `results` and `errors` before any handler runs.**
I initialized `results: []` and `errors: []` inside `context` at construction time, to make the return value "always complete." This means middleware receives a context with empty results/errors fields and can pre-populate, clear, or inspect them. Middleware now has structural access to the handler accumulation mechanism. I created this vulnerability by making the context "designed" — the original's lack of these fields in context was accidentally protective.

**3. The error semantics of `errors` (list, all errors) and `results` (list, only successes) are asymmetric without contract.**
Handlers that succeed append to `results`. Handlers that fail append to `errors` (and nothing to `results`). So `len(results) + len(errors)` equals total handlers only if no handler both returns a value AND raises — which is impossible in Python. But there's no invariant documented or enforced. Code that processes the return value cannot know if three successes and zero errors means "three handlers ran" or "six handlers ran, three failed silently before the try block." The improvement revealed that the result accumulation model has an unspecified cardinality contract.

---

## Diagnostic Applied to Improvement 1

**What the improvement conceals:** The three identities (pipeline, dispatcher, audit log) now have more distinct machinery — `DeadLetterEntry` for auditing, `context["results"]` for dispatch aggregation, middleware chain for pipeline — but they are still coupled through the `context` dict. The improvement made the coupling *look* like a feature (structured data flowing through a well-defined pipeline) while the actual flow is unchanged: middleware transforms the dict that handlers mutate that `emit()` returns.

**Property of the original visible because the improvement recreates it:** The original put the `context` dict in the dead letter queue directly. The improvement stores `payload` in `DeadLetterEntry` — but `payload` is the same object as `context["payload"]`. The improvement reproduced the live-reference audit problem at a different layer. This reveals: **the bus requires a channel between middleware and handlers, and any such channel, whether called "context dict" or "payload reference," creates the same contamination topology**. Renaming the shared state doesn't change its physics.

---

## Improvement 2 (Addresses the Recreated Property)

Separate the three roles into distinct typed objects with explicit ownership transfer:

```python
from dataclasses import dataclass, field
from copy import deepcopy
from typing import Any, List, Optional
import uuid

@dataclass(frozen=True)
class Event:
    """Immutable identity. Created once. Not mutated."""
    id: str
    type: str
    payload: Any  # caller owns; bus deep-copies on create

    @classmethod
    def create(cls, event_type: str, payload: Any) -> 'Event':
        return cls(id=str(uuid.uuid4()), type=event_type, payload=deepcopy(payload))

class PipelineContext:
    """Middleware's mutable workspace. NOT passed to handlers."""
    def __init__(self, event: Event):
        self.event = event          # immutable — middleware reads, cannot replace
        self.cancelled: bool = False
        self.cancel_reason: str = ""
        self.tags: dict = {}        # middleware metadata, invisible to handlers

@dataclass
class DispatchRecord:
    """Audit snapshot. Created after dispatch. Not a live reference."""
    event_id: str
    event_type: str
    results: List[Any]
    errors: List[Exception]
    dead_letter_reason: Optional[str] = None

class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter: List[DispatchRecord] = []

    def on(self, event_type, handler, priority=0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type, payload) -> DispatchRecord:
        event = Event.create(event_type, payload)   # bus owns this copy
        ctx = PipelineContext(event)

        # Middleware phase: operates on PipelineContext, not the event dispatch
        for mw in self._middleware:
            mw(ctx)
            if ctx.cancelled:
                record = DispatchRecord(
                    event_id=event.id,
                    event_type=event_type,
                    results=[],
                    errors=[],
                    dead_letter_reason=f"middleware_cancelled: {ctx.cancel_reason}"
                )
                self._dead_letter.append(record)
                return record

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            record = DispatchRecord(
                event_id=event.id,
                event_type=event_type,
                results=[],
                errors=[],
                dead_letter_reason="no_handlers"
            )
            self._dead_letter.append(record)
            return record

        results, errors = [], []
        for _, handler in handlers:
            # Each handler gets its own deep copy — handlers cannot interfere
            handler_event = Event(id=event.id, type=event.type, payload=deepcopy(event.payload))
            try:
                results.append(handler(handler_event))
            except Exception as e:
                errors.append(e)

        record = DispatchRecord(
            event_id=event.id,
            event_type=event_type,
            results=results,
            errors=errors,
            dead_letter_reason="handler_error" if errors else None,
        )
        if errors:
            self._dead_letter.append(record)
        return record
```

Now:
- `Event` is immutable (frozen dataclass), deep-copied at creation
- `PipelineContext` is middleware's private workspace — handlers never see it
- Each handler receives its own deep copy of the event payload
- `DispatchRecord` is a snapshot of completed dispatch state — not a live reference
- The three identities have three distinct objects with explicit ownership

---

## Diagnostic Applied to Improvement 2

**What it conceals:** The type separation is real. But `Event.payload` is typed as `Any` — if the caller passes a mutable object, `deepcopy` handles it at creation, and each handler gets a fresh copy. This actually works... for dispatch isolation. What it conceals is: **middleware can no longer enrich events for handlers.** `PipelineContext.tags` exists but is explicitly invisible to handlers. If middleware wants to inject an authentication token, a correlation ID, or a rate-limit decision into the event — it cannot. Middleware can only cancel or annotate its own private workspace. This is fine until you realize that enrichment is the *primary reason* most middleware exists.

**Property of the original visible because the improvement recreates it:** The original passed `context` through middleware, allowing middleware to add `context["user_id"]` that handlers then consumed. Improvement 2 eliminates this by making middleware and handlers receive completely separate objects. But in doing so, it reveals: **the shared context in the original wasn't a bug — it was the mechanism for middleware → handler information transfer.** The original's mutable context was load-bearing for enrichment. The improvement reveals this by destroying enrichment and showing what disappears.

---

## The Structural Invariant

Through every improvement, one property persists:

**In any sequential architecture where middleware runs before handlers on the same event, middleware and handlers must either share mutable state (allowing enrichment but destroying isolation) or receive separate copies (providing isolation but eliminating enrichment). The choice between enrichment and isolation is forced by the sequential middleware → handler ordering. No type system, naming convention, or copy strategy can satisfy both simultaneously.**

This is an invariant of the problem space, not the implementation. Every improvement redistributed the coupling — dict → typed objects → separate copies — but never eliminated the forced choice. Improvement 1 preserved enrichment, eliminated isolation. Improvement 2 preserved isolation, eliminated enrichment.

---

## Inverting the Invariant

Make enrichment AND isolation simultaneously satisfiable. The inversion: **handlers declare what middleware-enriched fields they need, and the bus assembles a typed, immutable view for each handler from the middleware output.**

```python
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

@runtime_checkable
class EnrichedHandler(Protocol):
    enrichment_keys: tuple  # handler declares what it needs from middleware

class EventBus:
    def emit(self, event_type, payload):
        event = Event.create(event_type, payload)
        enrichments = {}  # middleware writes here
        ctx = PipelineContext(event, enrichments)  # middleware's workspace

        for mw in self._middleware:
            mw(ctx)
            if ctx.cancelled:
                ...

        for _, handler in self._handlers.get(event_type, []):
            # Build isolated view: handler gets its copy + only its declared enrichments
            needed = getattr(handler, 'enrichment_keys', ())
            handler_enrichments = {k: deepcopy(enrichments[k]) for k in needed if k in enrichments}
            handler_event = HandlerEvent(
                id=event.id, type=event.type,
                payload=deepcopy(event.payload),
                enrichments=handler_enrichments  # deep-copied, isolated
            )
            handler(handler_event)
```

Now: middleware enriches `enrichments` dict. Each handler declares which keys it needs. The bus builds an isolated copy with exactly those keys. Middleware cannot corrupt handler state. Handlers cannot see middleware's full workspace. Enrichment and isolation coexist.

---

## The New Impossibility

The inversion makes enrichment + isolation trivially satisfiable — but creates a new impossibility:

**Handlers must statically declare their enrichment dependencies before middleware runs. But middleware is dynamic — it decides what to enrich based on the event. The contract requires handlers to know what middleware will produce before middleware produces it.**

This is the dependency declaration problem: `enrichment_keys` on the handler is a static declaration of runtime middleware behavior. If middleware conditionally adds `user_id` only for authenticated requests, handlers that declare `enrichment_keys = ("user_id",)` will silently receive an empty dict for unauthenticated events — with no error, no dead letter, no indication the enrichment was absent.

The new impossibility: **You cannot have middleware-driven enrichment with handler-declared dependencies without either making the middleware contract static (defeating the purpose of middleware) or making handler enrichment-dependency declarations unreliable.**

---

## The Conservation Law

**Original impossibility:** Sequential middleware → handler architecture cannot provide both enrichment (middleware writes what handlers read) and isolation (handlers cannot be affected by middleware mutations).

**Inverted impossibility:** When enrichment and isolation are both satisfied, the middleware–handler contract becomes undecidable at runtime — handlers declare dependencies on middleware outputs whose presence depends on runtime conditions the handlers cannot see.

The conservation law:

> **In any event bus, the product of middleware authority (what middleware can write that handlers read) and handler contract stability (whether handlers can rely on their declared enrichment being present) is constant. Increasing middleware authority reduces contract stability; increasing contract stability reduces middleware authority.**

This is not the obvious isolation↔coupling trade-off. It's more specific: **the conservation is between middleware's expressiveness and the bus's reliability guarantees.**

---

## What a Senior Engineer Would Not Already Know

A senior engineer knows: shared mutable state creates coupling. Copying creates isolation. Enrichment requires sharing. These are standard trade-offs.

**What the conservation law reveals that they don't know:**

The EventBus pattern structurally requires middleware to be simultaneously a *predicate* (should this event proceed?) and a *transformer* (what should handlers see?). These are different computational roles with different contracts — predicates require no shared state; transformers require write access to handler inputs. Any architecture that makes both roles available to middleware functions forces the bus to choose, at every emit, whether middleware output is *authoritative* (handlers must see it, reliability guaranteed) or *advisory* (handlers see it if present, no guarantee). 

The conservation law reveals that the popular middleware pattern — chain of functions that can modify context — is not a single design but two incompatible designs welded together by the convention that middleware functions return or mutate the same object they receive. The "improvement" every engineer reaches for (better types, immutability, copying) doesn't resolve this because it's not an implementation problem. It's a category error: you're asking one pipeline slot to do two jobs that have opposite state requirements. The conservation law names the quantity being redistributed — not performance or coupling, but **decision-time authority** — and shows that every refactoring of this pattern is moving that authority around, never eliminating the tension its existence creates.
