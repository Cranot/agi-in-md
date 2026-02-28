## Structural Analysis: EventBus

---

### I. The Falsifiable Claim

**The deepest structural problem:** The `context` dictionary is simultaneously the *message*, the *control-flow channel*, and the *result accumulator* — three objects with incompatible ownership, lifetime, and semantics collapsed into one mutable dict that flows through both a pipeline (middleware) and a broadcast (handlers). This makes it impossible to define when the context is "stable."

This is falsifiable: a handler that executes after a previous handler throws will observe `context["error"]` set by the error-handling code while simultaneously being expected to treat `context["payload"]` as valid input. The context is never in a defined state.

---

### II. The Expert Panel

**Expert A (Defends):** The mutable shared context is the root cause. Observe line by line: middleware mutates context and returns it. Then *all handlers* receive the same mutated object. Then `context["error"] = e` is written mid-loop — subsequent handlers see a context poisoned by a sibling's failure. This is a broadcast with shared mutable state. Even single-threaded, the execution order creates logical race conditions.

**Expert B (Attacks):** Mutability isn't the problem — Redux uses a single mutable store successfully. The real problem is that the code doesn't *commit* to either topology. A true pipeline has no broadcast; a true broadcast has no shared state. Blaming mutability is diagnosing the symptom. The actual defect is *undefined context ownership* — no point in execution where any participant can declare "I own this."

**Expert C (Probes what both take for granted):** Both of you assume context should be a message. Neither of you asked: *why does it need to be shared at all?* Middleware runs sequentially before handlers. Handlers run sequentially after middleware. These layers are never concurrent. The context dict isn't shared because of a concurrency requirement — it's shared because it's the *only return channel from the bus to the caller*. You're both seeing the mechanism and missing the architectural forcing function.

**Claim transformation:**
- **Original:** Mutable shared context creates entangled execution.
- **Transformed:** The context object is being used as a coordination channel between layers that are architecturally supposed to be decoupled, *because there is no separate return channel*. The mutability is a symptom; the root is that the context must serve as both the message and the only wire back to the caller.

**The diagnostic gap:** I initially located the problem in the context's mutability. The experts reveal the problem is structural: the context is load-bearing infrastructure disguised as a data carrier.

---

### III. The Concealment Mechanism

**Name:** Dictionary-as-coherent-domain-object.

The `context` dict contains three categorically distinct concerns:

| Key | Actual role | Owner |
|---|---|---|
| `type`, `payload` | Message | Caller → handlers |
| `cancelled`, `error` | Control flow | Middleware/error → next layer |
| `results` | Accumulator | Handlers → caller |

A dict makes these look equivalent. Its open-ended nature (`context["anything"] = x`) means new concerns attach without structural resistance. It *looks* clean because dicts always look clean — they impose no shape, and the absence of shape reads as flexibility rather than confusion.

**Applied:** The concealment works because `context["cancelled"]` looks like a message property, `context["error"]` looks like enrichment, and `context["results"]` looks like a summary. But `cancelled` is middleware-to-handler signal, `error` is handler-to-dead-letter signal, and `results` is handler-to-caller return data. They have different writers, different readers, and different validity windows. The dict makes them look like siblings.

---

### IV. Improvement 1: The Legitimate-Looking Deepener

Replace the untyped dict with a typed dataclass. This passes code review because it adds type safety, IDE support, and named fields.

```python
from dataclasses import dataclass, field
from typing import Any, Optional, List

@dataclass
class EventContext:
    type: str
    payload: Any
    cancelled: bool = False
    error: Optional[Exception] = None
    results: List[Any] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)  # middleware scratch space

class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter = []

    def on(self, event_type, handler, priority=0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type, payload):
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
                context.error = e
                self._dead_letter.append(context)
        return context
```

**Why this deepens concealment:** The conflation of message/control/accumulator now has a *name* (`EventContext`) and *type annotations*, making it look like an intentional domain model rather than a coordination hack. The `metadata: dict` field preserves the escape hatch — middleware still needs arbitrary scratch space, and now that need is invisible, tucked behind a named field. The structural problem has been *legitimized*.

---

### V. Three Properties Visible Because We Tried to Strengthen It

1. **`results: List[Any]` has no natural type.** When we typed the dataclass, we were forced to write `List[Any]` for results, because handlers can return anything. This reveals that the accumulator concern doesn't belong in the message object — a message has a defined schema; a result accumulator inherently doesn't.

2. **`cancelled` and `error` have different writers than `payload`.** The dataclass puts them in the same namespace, but `payload` is written by the caller, `cancelled` by middleware, and `error` by the error handler. The type system can name the fields but cannot express ownership or write-once semantics. The design demands a property the language cannot enforce here.

3. **`metadata: dict` is load-bearing.** It appeared because middleware needs to pass state to *other middleware* without touching the "official" fields. This reveals a hidden requirement: middleware-to-middleware coordination is a real use case the design smuggles through the open dict, now relocated to a named escape hatch.

---

### VI. Diagnostic Applied to Improvement 1

**What Improvement 1 conceals:** The context has no point of commitment — no moment where we can say "this object is now complete." `EventContext.error` can be set while `EventContext.results` is still being populated (handlers after the failing one still run and append). The typed fields make this look designed-in rather than accidental.

**Property of the original recreated:** A handler executing after a failure sees `context.error` set — it receives a context that is simultaneously "in-flight" (results still accumulating) and "terminated" (an error has occurred). The dataclass doesn't prevent this; it makes it look intentional.

---

### VII. Improvement 2: Address the Recreated Property

Stop processing handlers after the first error. Add `break` to prevent downstream handlers from seeing a poisoned context:

```python
def emit(self, event_type, payload):
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
            context.error = e
            self._dead_letter.append(context)
            break  # ← handlers after error no longer see poisoned context
    
    return context
```

**Diagnostic applied to Improvement 2:** The `break` conceals that `context.results` is now a *partial result set*, indistinguishable to the caller from a *complete result set*. The caller receives `results=[r1]` and `error=SomeException` with no indication that handlers 3, 4, and 5 were skipped. Dead letter receives a context mid-flight. The system is now designed to abandon silently.

**New visible property:** The design has no mechanism to express "partially completed dispatch." The caller cannot know whether the results they received represent all registered handlers or a subset. This was always latent; the `break` makes it structurally explicit.

---

### VIII. The Structural Invariant

**Invariant:** *The context object must serve as both the input to every handler and the accumulation point for their outputs, because there is no separate return channel from the bus to the caller.*

This persists through every improvement because:
- Separating input-context from output-context breaks the middleware chain (middleware passes state forward through the context)
- Giving each handler an isolated view breaks handler-to-handler communication through context
- `return context` at the end means the wire going in is the wire coming back

This is a property of the **problem space**, not the implementation. A synchronous event bus with a single call site must return something. The thing it returns must be entangled with the thing passed in unless there is a dedicated return channel.

---

### IX. The Category This Invariant Defines

**Category: Synchronous shared-context buses** — designs where:
- The bus call is synchronous (caller blocks until all handlers complete)
- A single mutable context flows through middleware and handlers
- The caller's return value reflects the accumulated state of that context

Member designs: jQuery's event system, Python's `logging` handler chain, WSGI middleware stacks, many Redux middleware implementations.

**Bounded by:** The invariant that context-as-message and context-as-coordination-channel are the same object.

---

### X. The Adjacent Category: Where the Invariant Dissolves

The invariant dissolves when message, control flow, and result accumulation become *separate objects* with separate return channels.

```python
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple

@dataclass(frozen=True)
class Event:
    """Immutable. Once created, no participant can alter what was sent."""
    type: str
    payload: Any

@dataclass
class DispatchResult:
    """Separate return channel. Not the event; the event's aftermath."""
    event: Event
    results: List[Any]
    cancelled: bool
    errors: List[Tuple[Callable, Exception]]
    dead_lettered: bool

    @property
    def succeeded(self) -> bool:
        return not self.cancelled and not self.errors and not self.dead_lettered

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list] = {}
        self._middleware: list[Callable] = []
        self._dead_letter_sink: Optional[Callable[[DispatchResult], None]] = None

    def on(self, event_type: str, handler: Callable, priority: int = 0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn: Callable[[Event], Optional[Event]]):
        """Middleware receives an Event, returns a transformed Event or None to cancel."""
        self._middleware.append(middleware_fn)

    def on_dead_letter(self, sink: Callable[[DispatchResult], None]):
        """Dead letter is a sink, not a list. The bus does not own failed events."""
        self._dead_letter_sink = sink

    def emit(self, event_type: str, payload: Any) -> DispatchResult:
        event = Event(type=event_type, payload=payload)

        # Middleware: transform the event (returns new Event) or cancel (returns None)
        for mw in self._middleware:
            result = mw(event)
            if result is None:
                dr = DispatchResult(
                    event=event, results=[], cancelled=True,
                    errors=[], dead_lettered=False
                )
                return dr
            event = result  # each middleware sees the previous one's output event

        handlers = self._handlers.get(event.type, [])
        if not handlers:
            dr = DispatchResult(
                event=event, results=[], cancelled=False,
                errors=[], dead_lettered=True
            )
            if self._dead_letter_sink:
                self._dead_letter_sink(dr)
            return dr

        results = []
        errors = []
        for _, handler in handlers:
            try:
                results.append(handler(event))  # handlers receive immutable Event
            except Exception as e:
                errors.append((handler, e))
                # All handlers run. Errors are collected, not state-polluting.

        dr = DispatchResult(
            event=event, results=results, cancelled=False,
            errors=errors, dead_lettered=False
        )
        if errors and self._dead_letter_sink:
            self._dead_letter_sink(dr)
        return dr
```

**How this succeeds where every improvement failed:**

| Problem | Original | Every Improvement | Adjacent Category |
|---|---|---|---|
| Context poisoning between handlers | ✗ | ✗ | ✓ Event is frozen |
| Partial results indistinguishable from complete | ✗ | ✗ (worsened by `break`) | ✓ All handlers always run; `errors` is separate |
| Dead letter owns mutable in-flight context | ✗ | ✗ | ✓ Dead letter receives immutable `DispatchResult` |
| Caller cannot determine what happened | ✗ | ✗ | ✓ `DispatchResult` separates results, errors, cancellation |
| Middleware cannot transform the message | ✗ (mutates context) | ✗ | ✓ Middleware returns new `Event` |

The invariant has dissolved: `Event` is the message. `DispatchResult` is the return channel. They are never the same object.

---

### XI. The New Impossibility

**What was trivial in the original category, impossible in the adjacent one:**

Handler-to-handler communication through the event.

In the original category, this is zero cost:

```python
# Handler A
def resolve_user(context):
    context["user"] = db.get_user(context["payload"]["user_id"])

# Handler B — depends on Handler A having run first
def send_welcome(context):
    email(context["user"].email, "Welcome!")
```

In the adjacent category, `Event` is frozen. Handler B cannot read what Handler A computed. There is no shared mutable surface.

Workarounds exist but each has a cost:
- **Pre-computation in middleware:** Move shared computation into a middleware that enriches the event before broadcast — but this couples the middleware to handler implementation details
- **Side-channel:** Handlers communicate through an external store (cache, DB) — but this pushes coordination outside the bus entirely
- **Chain-of-responsibility:** If handlers are dependent, use a pipeline, not a broadcast — but then it's a different pattern

---

### XII. The Finding: The Trade-Off

| | Original Category | Adjacent Category |
|---|---|---|
| **Impossibility** | Reasoning about context state — it means different things before middleware, between middleware and handlers, between handlers, and after handlers. You cannot know what the context represents at any given point. | Handler-to-handler communication within a single dispatch — handlers are truly isolated; one cannot read what another computed. |
| **What you buy** | Handlers can cooperate through shared context; one handler's output becomes another's input | Context is always in a defined state; reasoning about what any participant sees is trivial |
| **What you lose** | Ability to reason about when context is valid | Handler cooperation as a first-class feature |

**The structural finding:**

An event bus serves two incompatible masters: **decoupling** (producers don't know consumers; consumers are independent) and **chaining** (consumers build on each other's work). The shared mutable context is the mechanism by which the original design supports chaining — at the cost of making decoupling a fiction. Every improvement within the original category trades one manifestation of this tension for another.

The adjacent category resolves the tension by committing: handlers are genuinely independent. This gains the entire reasoning surface of immutable messages and clean return channels, and surrenders handler cooperation to the problem's outside.

**The real design question this code was never asked:** *Are the handlers independent or dependent?*

- If independent → the adjacent category is correct, and the context dict was always a fiction
- If dependent → this is not an event bus; it is a pipeline or chain-of-responsibility, and the event bus framing is the concealment

The `context` dict was concealing an unanswered architectural question about what the system actually is.

| Shared mutable context | Relocates the mutation | `Message` is frozen; no shared object crosses the publish/dispatch boundary |
| Handler result contamination | Mitigated by snapshots | `DeliveryRecord` created by bus infrastructure; handlers cannot write to it |
| Dead letter vs. error conflation | Both stored in same queue | `None` from middleware = intentional drop (no record); handler exception = `DeliveryRecord(success=False)` |
| Global middleware | Unresolved | Middleware still global — same problem, different category |
| Cancellation coupling | Always required a shared reference | Middleware returns `None`; no result object exists yet; no coupling |

---

## XI. The New Impossibility

**Properties trivial in Category A, impossible in Category B:**

**1. Synchronous return value.**
`emit()` returns handler results. A caller can write:
```python
result = bus.emit("validate", order)
if result.results[0].approved:
    bus.emit("charge", order)
```
In Category B, `publish()` returns a message ID. The results don't exist when publish returns. This entire pattern dissolves.

**2. Request-response in a single function body.**
In Category A, event-driven code can look like procedure calls. This is simultaneously the design flaw (tight coupling) and the utility (simple mental model, easy debugging, synchronous reasoning). Category B makes this impossible without a separate query mechanism and an explicit `await`.

**3. Deterministic handler ordering.**
Priority sort is meaningful in Category A: handler at priority 10 always runs before priority 5, within the same `emit` call. In Category B with concurrent dispatch, ordering becomes a contract that requires explicit serialization. The priority field becomes a fiction.

---

## XII. The Finding

The original EventBus's problems are not bugs — they are the **necessary costs of its implicit contract:** *"I will make calling a function feel like publishing an event."*

That contract is genuinely valuable. It is why Django signals, Python's `signal`, and JavaScript's synchronous event model exist and persist. The synchronous call-through gives you: return values that flow back, ordering that is deterministic, errors that propagate up the call stack, and a mental model requiring no new infrastructure.

Category B dissolves every structural problem and creates one new impossibility: **the caller cannot use the result of event processing in the same execution context.** This is not a small loss. It eliminates the request-response pattern, requires new infrastructure (queue, run loop, delivery log, message IDs), and replaces synchronous reasoning with eventual consistency.

**The structural invariant names the real question — not "how do we fix the EventBus?" but "which coupling do we accept?"**

- **Category A** couples *time* (caller blocks) to gain *information* (caller receives results)
- **Category B** decouples *time* to gain *isolation* (handlers cannot affect each other), but surrenders the information flow

**The code's actual concealment:** It is named and structured as a Category B system — *bus, emit, dead letter, middleware* — while implementing Category A coupling. It promises decoupling and delivers dispatch. Every improvement deepens that disguise by adding more Category B vocabulary to Category A machinery.

**The finding:** A synchronous event bus is not a degenerate message broker. It is a different artifact with different trade-offs, and the gap between what it is named and what it does creates a semantic debt that no refactoring can repay. The options are a rename (call it `PriorityDispatcher`), a rebuild in Category B, or conscious acknowledgment of which coupling you are choosing — and why.
