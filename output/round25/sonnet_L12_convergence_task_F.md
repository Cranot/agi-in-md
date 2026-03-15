# EventBus: Design-Space Convergence Analysis

## Initial Claim

**Falsifiable claim**: The deepest structural problem is *context mutation aliasing* — a single mutable dict is shared across the middleware pipeline, handler invocations, dead letter storage, and return value simultaneously, making it impossible to determine which component legitimately owns context state at any moment.

Falsifiable as: *if context can be demonstrated to always be in a consistent state when any component reads it, the claim fails.*

---

## Three-Expert Dialectic

**Expert A (Defender)** confirms and sharpens: the aliasing is worse than it looks. After a handler throws, `context["error"] = e` mutates the *same object* already stored in `_dead_letter`. Dead letter doesn't capture error state at the moment of failure — it captures whatever context looks like *after subsequent handlers run*. A later successful handler appends to `context["results"]`, so dead letter entries contain success results alongside the error that triggered storage.

**Expert B (Attacker)** rejects the root cause: aliasing is a symptom. The real problem is that `emit` conflates three incompatible protocols sharing one execution path:
1. **Middleware protocol**: transform-or-cancel, single threaded value
2. **Handler dispatch protocol**: fan-out, independent invocations  
3. **Error/audit protocol**: stable snapshot for dead letter

Fix the mutation and the protocol collision remains.

**Expert C (Prober)** rejects the shared premise: both experts assume a context dict is a reasonable unit of communication. But what is the context *for*? Middleware treats it as a pipeline value. Handlers treat it as an event descriptor. Dead letter treats it as an audit record. The return value treats it as a result aggregate. Neither expert questions whether one object *should* carry all four roles.

### Claim Transformation

| | |
|---|---|
| **Original** | Context mutation aliasing |
| **Transformed** | **Role collapse**: one mutable object forced to play mutually incompatible roles; aliasing is merely how the collapse becomes observable |

---

## The Concealment Mechanism

**Name**: *Progressive decoration disguised as accumulation*

The code *appears* to enrich context over time — middleware adds `"cancelled"`, handlers add `"results"`, errors add `"error"`. This reads as healthy accretion. What actually happens is the object's *semantic identity* changes with each phase: pipeline control value → event descriptor → result aggregate → audit record. Python dicts have no schema, so each role redefinition is invisible at the language level. You never see a type error; you only see behavioral anomalies.

---

## Improvement 1: Deepens the Concealment

This passes code review by fixing the visible symptoms:

```python
from dataclasses import dataclass, field
from typing import Any, List, Optional
import copy

@dataclass
class EventContext:
    """Typed, structured event context."""
    type: str
    payload: Any
    cancelled: bool = False
    cancel_reason: Optional[str] = None
    error: Optional[Exception] = None
    results: List[Any] = field(default_factory=list)

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

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> EventContext:
        context = EventContext(type=event_type, payload=payload)

        for mw in self._middleware:
            context = mw(context)
            if context.cancelled:
                return context                        # ← clean early exit

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(copy.deepcopy(context))  # ← fixed aliasing
            return context

        for _, handler in handlers:
            try:
                context.results.append(handler(context))
            except Exception as e:
                context.error = e
                self._dead_letter.append(copy.deepcopy(context))  # ← snapshot at failure

        return context
```

**Why it passes review**: replaces untyped dict with typed dataclass ✓, fixes dead letter aliasing with `deepcopy` ✓, uses dot notation ✓, named fields prevent key typos ✓.

**Why it deepens the concealment**: `EventContext` *formalizes* the role collapse. The four incompatible roles are now documented in the type definition. The type system validates that the wrong abstraction is correctly spelled. The schema encodes a temporal lie — `cancelled` is meaningful only during middleware; `results` only after dispatch. Both fields coexist on the type as if they're co-valid, but no context instance can meaningfully have both populated.

### Three Properties Visible Only Because We Tried to Strengthen

1. **The schema encodes a temporal lie**: `EventContext` allows `cancelled=True` and `results=[...]` simultaneously. A context cannot meaningfully be both, but the type permits it. Improvement 1 makes the contradiction *permanent and named*.

2. **`deepcopy` reveals that dead letter needs a different type**: Dead letter needs a `PipelineFailureRecord` with different fields than a `DispatchResult`. The fact that `deepcopy(EventContext)` is the best available snapshot confirms that dead letter items *should not be* EventContext instances at all.

3. **Middleware's `type` field is decorative**: If middleware changes `context.type`, the new type is carried in `EventContext.type`, but `emit` dispatches on the original `event_type` parameter. The typed context *looks like* middleware can reroute events; it cannot.

---

## Improvement 2: Addresses Semantic Phase Dependency

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# ── Immutable phase-specific types ──────────────────────────────────────────

@dataclass(frozen=True)
class Event:
    """Stable event identity. Crosses all phase boundaries unchanged."""
    type: str
    payload: Any                        # ← the irreducible surface (see below)

@dataclass(frozen=True)
class MiddlewareResult:
    """Output of the middleware pipeline."""
    event: Event
    cancelled: bool = False
    cancel_reason: Optional[str] = None

@dataclass(frozen=True)
class DispatchResult:
    """Output of handler dispatch."""
    event: Event
    results: tuple = ()
    errors: tuple = ()

@dataclass(frozen=True)
class DeadLetterEntry:
    """Audit record — not an EventContext copy."""
    event: Event
    reason: str                         # 'no_handlers' | 'handler_error'
    error: Optional[Exception] = None

# ── Bus ─────────────────────────────────────────────────────────────────────

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list] = {}
        self._middleware: list[Callable[[Event], MiddlewareResult]] = []
        self._dead_letter: list[DeadLetterEntry] = []

    def on(self, event_type: str, handler: Callable[[Event], Any], priority: int = 0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn: Callable[[Event], MiddlewareResult]):
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> DispatchResult:
        current = Event(type=event_type, payload=payload)

        # Phase 1: Middleware — transforms event identity
        for mw in self._middleware:
            result = mw(current)
            if result.cancelled:
                return DispatchResult(event=current)
            current = result.event      # middleware CAN reroute; dispatch respects it

        # Phase 2: Handler dispatch
        handlers = self._handlers.get(current.type, [])
        if not handlers:
            self._dead_letter.append(DeadLetterEntry(event=current, reason='no_handlers'))
            return DispatchResult(event=current)

        results, errors = [], []
        for _, handler in handlers:
            try:
                results.append(handler(current))
            except Exception as e:
                errors.append(e)
                self._dead_letter.append(
                    DeadLetterEntry(event=current, reason='handler_error', error=e)
                )

        return DispatchResult(event=current, results=tuple(results), errors=tuple(errors))
```

### Diagnostic on Improvement 2

**What it conceals**: `frozen=True` on the wrapper types creates an *appearance* of immutability guarantees. But `payload: Any` can hold any mutable object. Freezing the container doesn't freeze the content. Multiple handlers receive the same `current` Event — they share the same `payload` reference. One handler mutating `payload` corrupts subsequent handlers' view. The frozen dataclass actively misleads: it signals "immutable, safe to share" while the payload is freely mutable.

**The property the improvement forces into view**: The *structural invariant*.

---

## The Structural Invariant

**Statement**: *Fan-out requires sharing the payload reference across handlers. Isolation requires each handler to see a pristine snapshot. The bus cannot satisfy both without copying. The bus cannot copy correctly without knowing the payload's copy semantics. The bus cannot know the payload's copy semantics without either mandating a serialization contract or abandoning type safety for payload.*

This persists through every improvement:

| Design | What persists |
|---|---|
| Original dict | `context["payload"]` shared across all handlers |
| Typed dataclass | `context.payload` shared, deepcopy not applied to handler invocations |
| Frozen dataclass | `event.payload: Any` shared, immutability is the wrapper only |

The invariant is not "mutation is bad." It is: **the bus cannot enforce payload isolation without knowing the payload's copy semantics, and it cannot know that without a contract it cannot impose.**

---

## Inverting the Invariant

**Impossible property**: Each handler receives an isolated payload snapshot.
**Inversion**: Make this trivially satisfiable by mandating serialization.

```python
import json
from typing import Any

class SerializingEventBus:
    """
    Payload isolation is trivially enforced: each handler
    receives a fresh deserialization of the serialized payload.
    """
    def __init__(self, codec=json):
        self._handlers: dict = {}
        self._codec = codec

    def on(self, event_type: str, handler, priority: int = 0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def emit(self, event_type: str, payload: Any) -> list:
        wire = self._codec.dumps(payload)       # serialize once
        results = []
        for _, handler in self._handlers.get(event_type, []):
            fresh = self._codec.loads(wire)     # fresh copy per handler
            results.append(handler({"type": event_type, "payload": fresh}))
        return results
```

**Handler isolation is now trivially satisfiable.**

**New impossibility**: Payloads must be JSON-serializable (or pickle-able, or whatever the codec requires). Open file handles, database connections, lambda closures, C extension types, objects with circular references — none can be emitted. The constraint moves from *"the bus cannot know copy semantics"* to *"the bus mandates serialization semantics."*

---

## Finding 1: The Conservation Law

**In any event bus design, the product of *payload expressiveness* and *handler isolation* is bounded.**

Every design chooses which side of the tradeoff to expose:
- **Arbitrary payloads** → shared mutation risk (isolation violated)
- **Isolated copies** → serialization tax (expressiveness violated)

No implementation choice eliminates this. It only chooses which constraint to make explicit and which to hide from which stakeholder.

---

## Third Design: Escaping the Conservation Law

Move to an adjacent design category: **actor model**. Handlers run in isolated worker processes. Isolation is *architectural* (process boundary), not *operational* (copy on emit). The bus transmits through OS IPC queues; the payload is serialized by the infrastructure, not by the bus's application code.

```python
import multiprocessing
from typing import Any, Callable

class ActorEventBus:
    """
    Handlers are isolated worker processes.
    Payload mutation in one handler is physically impossible in another.
    Isolation is an architectural property, not an operational one.
    """

    def __init__(self):
        self._queues: dict[str, list] = {}
        self._workers: list[multiprocessing.Process] = []

    def on(self, event_type: str, handler_fn: Callable, priority: int = 0):
        q: multiprocessing.Queue = multiprocessing.Queue()
        p = multiprocessing.Process(
            target=self._worker_loop,
            args=(handler_fn, q),
            daemon=True
        )
        p.start()
        if event_type not in self._queues:
            self._queues[event_type] = []
        self._queues[event_type].append((priority, q))
        self._queues[event_type].sort(key=lambda x: -x[0])
        self._workers.append(p)

    @staticmethod
    def _worker_loop(handler_fn: Callable, q: multiprocessing.Queue):
        while True:
            event = q.get()
            if event is None:
                break
            try:
                handler_fn(event)
            except Exception:
                pass  # failure is isolated to this actor; bus is unaffected

    def emit(self, event_type: str, payload: Any) -> None:
        event = {"type": event_type, "payload": payload}
        for _, q in self._queues.get(event_type, []):
            q.put(event)   # multiprocessing serializes automatically; each process
                           # receives its own deserialized copy

    def shutdown(self):
        for qs in self._queues.values():
            for _, q in qs:
                q.put(None)
        for p in self._workers:
            p.join()
```

**What becomes possible**:
- True physical isolation — a handler crash does not affect the bus or other handlers
- Parallelism with no shared state
- Payload mutation in one handler is literally impossible in another
- The bus has no in-process aliasing surface at all

**New impossibility**:
- Payloads must be picklable — the serialization constraint reappears, now at the process boundary rather than at the bus API
- Synchronous return values from handlers are impossible without a per-handler result queue and explicit rendezvous
- Priority ordering is advisory — process scheduling is non-deterministic
- The bus cannot observe handler completion without external synchronization

---

## Finding 2: The Relationship Between the Conservation Law and the Escape's Impossibility

**The actor model does not eliminate the serialization constraint — it displaces it from the bus's responsibility to the infrastructure's responsibility.**

The new impossibility (pickle required, no synchronous returns) is the conservation law *re-expressed at the architectural level*. Moving from operation-space to architecture-space transforms the constraint's **form** (from "copy semantics the bus must know" to "pickle protocol the OS channel enforces") while preserving its **content** (some serialization contract is required for isolation).

**Finding 2**: Architectural escapes from bus-level conservation laws are re-expressions of those laws at the infrastructure level, not eliminations of them. The constraint is conserved; what changes is which stakeholder — bus author, event emitter, handler author, or infrastructure operator — bears it.

---

## The Meta-Conservation Law

**Statement**: *An event bus cannot simultaneously satisfy all four of:*

| Property | Description |
|---|---|
| **Payload Expressiveness** | Arbitrary objects can be emitted |
| **Handler Isolation** | No handler can observe or corrupt another's payload view |
| **Synchronous Composition** | Handlers return values that affect dispatch or the caller |
| **Topological Openness** | New handlers can be added without modifying the bus or existing handlers |

*Any design satisfies at most three.*

| Design | Satisfies | Violates |
|---|---|---|
| Original | 1, 3, 4 | 2 (shared context) |
| Improvement 1 | 1, 3, 4 | 2 (payload aliasing persists) |
| Improvement 2 | 1, 3, 4 | 2 (payload: Any shared) |
| Serializing bus | 2, 3, 4 | 1 (must be serializable) |
| Actor bus | 1, 2, 4 | 3 (no synchronous return) |

This is not a property of any implementation. It is a property of the problem space itself.

---

## Prediction for Future Designs

Any future EventBus that claims to satisfy all four properties will, upon examination, do exactly one of three things:

1. **Secretly violate one** by passing the constraint to the user ("you must ensure your payloads are copy-safe" is the bus violating isolation; "handlers must not block" is the bus violating synchronous composition).

2. **Introduce a fifth concept** that embeds the tradeoff — a `Transmittable[T]` bound, a `Future[T]` result type, a capability-based payload — which relocates where the constraint lives without eliminating it.

3. **Redefine one property** to be weaker than it sounds — "isolation" becomes "logical isolation by convention"; "synchronous" becomes "eventual with a blocking façade."

**The contest between event bus designs is not about which one solves the constraint. It is about which stakeholder — bus author, event emitter, handler author, or infrastructure operator — the design assigns the constraint to.** Every architectural decision in this space is a constraint-assignment decision wearing the costume of an engineering improvement.
