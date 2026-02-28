# EventBus: A Structural Autopsy

## The Deepest Structural Claim

**Falsifiable claim:** The `context` dict serves as simultaneous event identity, control flow signal, error record, and result accumulator — making the act of *handling* an event indistinguishable from the act of *describing* it. By the time the second handler runs, the context already encodes what the first handler did to it. Event identity is entangled with handler execution state.

---

## Three Experts Debate It

**Defender:** The claim holds. Look at the error path — when a handler throws, `context["error"] = e` is written onto the context object, and that same mutated context is then pushed into the dead letter queue *and* returned to the caller. The description of the event now contains the history of its own failed handling. They're the same object.

**Attacker:** This is the *context pipeline* pattern — standard in Express.js, ASP.NET, Koa. Shared mutable context is intentional; it's how middleware communicates with handlers. The real problem is the *lack of handler isolation*, not shared state. Fix that, and the mutation is fine.

**Prober:** Both of you are assuming this is supposed to be a *bus* — a decoupled broadcast mechanism. But `emit()` *returns results*. Fire-and-forget systems don't do that. What does it mean to observe an event *and* return a value from observing it? You're both arguing about shared state while taking for granted the question of *which communication model this is supposed to implement*.

### The Claim Transforms

The deepest problem is not shared mutable context. It is that **two incompatible communication paradigms are collapsed into one class**:

| Model | `emit` behavior | Handlers are | Results |
|-------|-----------------|--------------|---------|
| **Pub/Sub** | fire and forget | isolated observers | none |
| **Request/Response** | synchronous call | responders | collected |

The code implements both simultaneously. The context mutation is a *symptom* of the collapse, not the root cause.

**Diagnostic gap:** I started at the object level (dict serving too many masters) and arrived at the architectural level (two incompatible paradigms sharing one API). The original claim described *what* was wrong. The transformed claim explains *why it can't be fixed in place*.

---

## The Concealment Mechanism

**Syntactic symmetry masking semantic asymmetry.**

Three vocabulary choices from three different paradigms:

```python
bus.on(...)    # pub/sub vocabulary → implies passive observation
bus.use(...)   # pipeline vocabulary → implies transformation
bus.emit(...)  # event vocabulary → implies broadcast
```

But `emit()` *returns a value with results*. That's request/response semantics wearing pub/sub clothing. The method names are internally consistent in style, which creates the illusion of a unified model. Code review passes because everything *reads* like one coherent system.

---

## Improvement 1: Deepen the Concealment

Replace the raw dict with a typed dataclass. This passes code review easily — it looks like a responsible improvement:

```python
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class EventContext:
    type: str
    payload: Any
    cancelled: bool = False
    error: Optional[Exception] = None   # ← only holds ONE error
    results: list = field(default_factory=list)

class EventBus:
    def emit(self, event_type, payload) -> EventContext:
        context = EventContext(type=event_type, payload=payload)
        for mw in self._middleware:
            context = mw(context)
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
                context.error = e          # silently overwrites previous error
                self._dead_letter.append(context)
        return context
```

**Why this deepens concealment:** The dataclass gives the confused design a proper type signature. The mixed-concern object now *looks like intentional schema design*. The typed return `-> EventContext` makes the request/response pattern appear deliberate. The fundamental confusion has been promoted to a first-class API contract.

### Three Properties Now Visible

1. **`results: list` has no element type.** When we try to annotate it properly (`list[T]`), we realize there's no valid `T` — handlers can return anything. In pub/sub, observers return nothing; the untype-ability of `results` reveals it belongs to a paradigm the class isn't supposed to implement.

2. **`error: Optional[Exception]` is lossy.** When we formalize the error field, we see that multiple handlers can throw, but only the last exception survives — earlier ones are silently overwritten. The typing pressure exposed a silent data loss bug.

3. **Middleware and handlers have asymmetric access.** Middleware receives a context and *returns* one (replacement semantics). Handlers receive a context and *mutate* it (in-place semantics). Two different access models are invisible in the dict version but surface when you try to define method signatures.

---

## Improvement 2: Contradict the First

Where Improvement 1 *unified* the context object, Improvement 2 *separates* event from response. This also passes code review — it's a legitimate architectural improvement:

```python
@dataclass(frozen=True)   # ← immutable, handler-safe
class Event:
    type: str
    payload: Any

@dataclass
class DispatchResult:
    event: Event
    results: list = field(default_factory=list)
    errors: list = field(default_factory=list)  # ← captures ALL errors
    cancelled: bool = False

class EventBus:
    def emit(self, event_type, payload) -> DispatchResult:
        event = Event(type=event_type, payload=payload)
        result = DispatchResult(event=event)

        current = event
        for mw in self._middleware:
            current, cancelled = mw(current)
            if cancelled:
                result.cancelled = True
                return result

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(event)
            return result

        for _, handler in handlers:
            try:
                result.results.append(handler(current))
            except Exception as e:
                result.errors.append(e)          # ← no data loss
                self._dead_letter.append(current)

        return result
```

Improvement 1 made the shared object more formal. Improvement 2 makes the event immutable and separates concerns. Both are individually correct.

---

## The Structural Conflict

Both improvements are legitimate. Their conflict: **Improvement 1 enables middleware to enrich the context that handlers receive. Improvement 2 makes events immutable, so middleware can only gate — it cannot enrich.**

The question this surfaces: **What is middleware for?**

- **If middleware is a filter** (decides whether the event proceeds): Improvement 2 is correct. Middleware sees an immutable event and returns `(event, cancelled)`.
- **If middleware is a transformer** (enriches the event with auth info, tracing IDs, derived fields): Improvement 1 is correct. Middleware mutates or replaces the context.

These are compatible in a dict (dicts absorb anything), but incompatible when you attempt proper typing. The conflict exists *only because both improvements are legitimate* — it reveals that middleware is simultaneously doing two things whose type signatures are mutually exclusive.

---

## Improvement 3: Resolve the Conflict

Add `metadata` to the frozen event — a typed escape hatch that lets middleware enrich without violating immutability:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class Event:
    type: str
    payload: Any
    metadata: tuple = ()    # ← immutable container for middleware annotations

class EventBus:
    def emit(self, event_type, payload):
        event = Event(type=event_type, payload=payload)

        for mw in self._middleware:
            enrichment = mw(event)
            if enrichment is None:
                return                    # filtered
            new_meta = dict(event.metadata) | enrichment.get('metadata', {})
            event = Event(                # ← new immutable event per middleware
                type=event.type,
                payload=event.payload,
                metadata=tuple(new_meta.items())
            )

        for _, handler in self._handlers.get(event_type, []):
            handler(event)
```

### How It Fails

`metadata: tuple = ()` encoding key-value pairs as `(('key', value), ...)` is untyped in exactly the same way as the original dict. We've added a typed *container* around an untyped *schema*. Worse: `frozen=True` prevents attribute reassignment but doesn't prevent mutations to mutable *values* inside `metadata` — if any value is a list or dict, it can be mutated by any handler despite the frozen annotation.

**The deeper failure:** Middleware enrichment requires extensible schema. Extensible schema requires accepting arbitrary keys and arbitrary value types. That is structurally equivalent to a dict. We have reconstructed the original dict inside a typed wrapper and called it a solution.

---

## What the Failure Reveals

The conflict alone told us: middleware needs to both gate and enrich, and these have incompatible type signatures.

The failure of the resolution reveals something the conflict could not: **there is no Python type that is simultaneously strongly typed and open to arbitrary enrichment.** The design space has a hard topological constraint:

```
Type Safety ←————————————→ Schema Extensibility
      ↑                              ↑
   Closed                          Open
  (frozen)                        (dict)
```

You cannot be at both ends simultaneously. Every attempt to resolve the conflict relocates the untyped blob rather than eliminating it. The design space is **not convex** — you cannot reach arbitrary combinations by interpolation. There is no feasible point that satisfies all four desiderata:

1. Type-safe event schema
2. Middleware-enrichable event metadata
3. Handler immutability guarantees
4. Single unified API for pub/sub and request/response

---

## The Redesign: Accepting the Topology

Don't improve the EventBus. Decompose it into two classes that each inhabit a *feasible* point in the design space.

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# ── Pub/Sub ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Event:
    """Immutable. Described once. Never accumulates results."""
    type: str
    payload: Any

class EventBus:
    """Fire and forget. Observers cannot respond."""
    def __init__(self):
        self._handlers: dict[str, list[tuple[int, Callable[[Event], None]]]] = {}
        self._filters: list[Callable[[Event], bool]] = []
        self._dead_letter: list[Event] = []

    def subscribe(self, event_type: str, handler: Callable[[Event], None],
                  priority: int = 0) -> None:
        self._handlers.setdefault(event_type, [])
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def add_filter(self, fn: Callable[[Event], bool]) -> None:
        """Filters gate. They do not enrich. Enrichment is the caller's job."""
        self._filters.append(fn)

    def publish(self, event_type: str, payload: Any) -> None:
        """Returns nothing. Handlers are observers, not responders."""
        event = Event(type=event_type, payload=payload)
        if not all(f(event) for f in self._filters):
            return
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(event)
            return
        for _, handler in handlers:
            try:
                handler(event)
            except Exception:
                self._dead_letter.append(event)


# ── Request/Response ──────────────────────────────────────────────────────────

@dataclass
class Command:
    """Mutable. One handler. Enrichment is explicit."""
    type: str
    payload: Any
    metadata: dict[str, Any] = field(default_factory=dict)  # ← enrichment lives here
    result: Any = None
    error: Optional[Exception] = None

class CommandBus:
    """Dispatches to exactly one handler. Returns a result."""
    def __init__(self):
        # One handler per command type — request/response demands it
        self._handlers: dict[str, Callable[[Command], Any]] = {}
        self._middleware: list[Callable[[Command], Optional[Command]]] = []

    def register(self, command_type: str, handler: Callable[[Command], Any]) -> None:
        self._handlers[command_type] = handler

    def use(self, fn: Callable[[Command], Optional[Command]]) -> None:
        self._middleware.append(fn)

    def dispatch(self, command_type: str, payload: Any,
                 metadata: Optional[dict] = None) -> Command:
        cmd = Command(type=command_type, payload=payload,
                      metadata=metadata or {})
        for mw in self._middleware:
            cmd = mw(cmd)
            if cmd is None:
                raise RuntimeError(f"Command '{command_type}' rejected by middleware")
        handler = self._handlers.get(command_type)
        if not handler:
            raise KeyError(f"No handler registered for: {command_type}")
        try:
            cmd.result = handler(cmd)
        except Exception as e:
            cmd.error = e
        return cmd
```

### What the Redesign Sacrifices

- **The unified API.** Callers must know whether they're publishing or dispatching.
- **Multiple handlers per command.** `CommandBus` enforces one handler per command type — which is correct for request/response, but loses the priority-ordered fan-out.
- **Dead letter queues for commands.** A command with no handler raises immediately; there's no "maybe someone will handle this later" semantics.
- **The single object to pass around.** Middleware now lives in two different classes with different signatures.

---

## What Was Never a Flaw

The original `emit()` returning a mutable dict with accumulated results was not carelessness.

It was the **only schema compatible with both paradigms simultaneously.**

A dict absorbs pub/sub (ignore the `results` key) and request/response (read the `results` key) without forcing a choice. The price of the unified API — one bus, one method, works for everything — is exactly that mixed-concern object. The "messiness" was not a failure of design discipline. It was the *necessary cost of the ergonomic goal*.

The original design's real property, visible only now: **`emit()` returning `context` was not a bug. It was the load-bearing member of the unified API.** Remove it and you get two buses. Keep it and you carry the entanglement forever.

The impossible design goal was: *one class that is simultaneously a broadcast mechanism and a synchronous dispatcher*. The original dict was not hiding that goal — it *was* that goal, expressed in the only form that doesn't immediately break.
