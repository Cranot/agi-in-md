# Structural Diagnostic: EventBus Conservation Law

---

## I. The Falsifiable Claim

**The deepest structural problem:** `emit()` uses a single mutable dict as simultaneously the event's *identity*, the pipeline's *execution envelope*, and the handlers' *result accumulation* — three things with incompatible lifecycles collapsed into one object.

**Falsifiable prediction:** Store the return value of two `emit()` calls where the second handler errors, then inspect `dead_letter`. You will find:
- Multiple `dead_letter` entries that are **the same object** (same `id()`)
- Each entry showing the **last** error, not the one that caused it
- `context["results"]` on a dead-letter entry containing **partial results from before the error**

```python
bus = EventBus()
bus.on("x", lambda ctx: "ok")
bus.on("x", lambda ctx: 1/0)  # errors, overwrites context["error"]
bus.on("x", lambda ctx: "also ok")

r = bus.emit("x", {})

# Dead letter contains ONE reference to the shared context dict.
# It shows error=ZeroDivisionError BUT results=["ok", "also ok"]
# The dead-letter record is a lie: it describes a world that never existed.
assert bus._dead_letter[0] is r  # same object
assert bus._dead_letter[0]["results"] == ["ok", "also ok"]  # includes post-error results
```

---

## II. Three Experts Debate

**Defender:** The shared mutable context is the pipeline pattern — it's intentional. Middleware annotating context, handlers reading prior results, correlation via mutation — these are features of systems like Express.js middleware chains.

**Attacker:** The claim is too narrow. The mutation issue is a symptom. The real problem is that `emit()` has no defined return type contract. Sometimes it returns a cancelled context, sometimes a dead-letter context, sometimes a fully-resolved context. Callers cannot write correct error-handling code.

**Prober:** Both of you assume the problem is data-structural. But what do you both take for granted? That middleware runs before handlers and cannot run after. There is no post-handler phase. Middleware that wants to log what handlers did cannot — it only sees pre-handler state. You've both accepted the pipeline's temporal structure as given.

### Claim Transformation

| Stage | Claim |
|-------|-------|
| Original | Shared mutable dict creates bad dead-letter records |
| After defender | Mutation is the pipeline pattern; the problem is a missing contract |
| After attacker | The return type is polymorphic and unannounced |
| After prober | The pipeline has only one phase where it needs two |
| **Transformed** | **`emit()` conflates three concerns — event identity, pipeline phase, outcome accumulation — that have incompatible temporal validity windows** |

**The gap:** I started with *mutation as mechanism* and arrived at *temporal invalidity as structure*. That distance is significant.

---

## III. The Concealment Mechanism

**Dict homogeneity erases semantic distinctions.**

A Python dict makes `context["type"]` (immutable event identity), `context["cancelled"]` (middleware-phase state), `context["error"]` (handler-phase state), and `context["results"]` (post-handler output) look identical — they're all just string keys mapping to values. There is nothing in the code to indicate that reading `context["results"]` inside middleware is reading a field that doesn't exist yet.

Code review passes because passing dicts through pipelines is idiomatic Python. The structural problem looks like a style choice.

---

## IV. Improvement 1: Legitimate-Looking, Deepens Concealment

Add a `dataclass` to give the context a schema. This passes code review enthusiastically — it adds type hints, replaces a raw dict with a named structure, looks like a refactoring win.

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
    metadata: dict = field(default_factory=dict)  # "escape hatch"

class EventBus:
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

**Why this deepens concealment:**

1. The merged concerns now look *intentional* — a schema implies a design decision, not an accident. Future developers will defend the design rather than question it.
2. `metadata: dict` reinstates the original dict problem with a cleaner name and a blessing from the type system.
3. The `Optional[Exception]` type for `error` implies at most one error is expected — this is now a documented lie that type-checkers will enforce.

---

## V. Three Properties Visible Only Because I Strengthened It

**1. Fields have incompatible valid-read windows.**
When I wrote `error: Optional[Exception]`, I had to ask: what does `None` mean here — "no error occurred" or "handlers haven't run yet"? These are different states with the same representation. The dataclass made this visible by forcing me to name the field.

**2. `results` is not a field of the event; it's the bus's scratch space.**
When I added `results: List[Any]`, I saw that middleware receives an `EventContext` with `results=[]` — a field that middleware should never read or write, yet nothing prevents it. The field exists in middleware scope.

**3. Error collection is structurally wrong at the type level.**
`error: Optional[Exception]` accepts one error. N handlers can each throw. The type signature documents a design constraint (`at most one error matters`) that was never a real design decision — it was just how the dict happened to get overwritten.

---

## VI. Diagnostic Applied to Improvement 1

**What `EventContext` conceals:** Temporal invalidity behind apparent simultaneity. All fields exist at all times, but most are meaningless during most phases. A middleware function receives an `EventContext` where `.results` is `[]` not because no handlers ran, but because **no handlers have run yet** — same value, different meaning.

**What property of the original problem is visible because this recreates it:**

The original problem was three concerns in one bag. The dataclass recreates it with a schema, making explicit what was implicit:

- `type`, `payload` → belong to the **Event** (immutable, pre-pipeline)
- `cancelled`, `metadata` → belong to the **MiddlewareContext** (set during middleware phase)  
- `error`, `results` → belong to the **HandlerOutcome** (set during handler phase)

These are three objects that should exist at different times. The dataclass fields are labelled with what phase created them; the phase structure is now legible and obviously wrong.

---

## VII. Improvement 2: Address the Recreated Property

Split into three objects with enforced temporal validity. The bus's internal pipeline threads them sequentially; external contracts see only the types appropriate to their phase.

```python
from dataclasses import dataclass, field
from typing import Any, List, Tuple
import uuid

@dataclass(frozen=True)
class Event:
    """Immutable. Exists before the bus processes anything."""
    id: str
    type: str
    payload: Any

@dataclass
class MiddlewareEnvelope:
    """Mutable only by middleware. Handlers receive this read-only."""
    event: Event
    cancelled: bool = False
    metadata: dict = field(default_factory=dict)

@dataclass
class HandlerOutcome:
    """Created after middleware completes. Middleware never sees this."""
    envelope: MiddlewareEnvelope
    results: List[Any] = field(default_factory=list)
    errors: List[Tuple[Any, Exception]] = field(default_factory=list)  # (handler, exception)

    @property
    def succeeded(self) -> bool:
        return len(self.errors) == 0

class EventBus:
    def emit(self, event_type, payload) -> "MiddlewareEnvelope | HandlerOutcome":
        event = Event(id=str(uuid.uuid4()), type=event_type, payload=payload)
        envelope = MiddlewareEnvelope(event=event)

        for mw in self._middleware:
            mw(envelope)  # mutates in place; cannot return a new type
            if envelope.cancelled:
                return envelope  # ← still returns different types

        handlers = self._handlers.get(event_type, [])
        outcome = HandlerOutcome(envelope=envelope)

        if not handlers:
            self._dead_letter.append(outcome)
            return outcome

        for _, handler in handlers:
            try:
                outcome.results.append(handler(envelope, outcome))
            except Exception as e:
                outcome.errors.append((handler, e))
                self._dead_letter.append(outcome)  # snapshot? or reference?

        return outcome
```

---

## VIII. Diagnostic Applied to Improvement 2

**What the three-object design conceals:**

`emit()` returns `MiddlewareEnvelope | HandlerOutcome` — a union type that callers must discriminate. The temporal structure is now in the type system, but the **control-flow decision about which type to return** is implicit in `emit()`'s body. Nothing tells the caller they got a cancelled envelope vs. a complete outcome without `isinstance()`.

More critically: dead-letter still stores object **references**, not snapshots. If `outcome` is appended to dead-letter mid-loop, later handler results modify the same object in dead-letter. The dead-letter problem is conserved.

**What property of the original problem is visible because this recreates it:**

The three-object split makes the system's execution phases explicit — and immediately reveals that **`emit()` is a state machine with no formal state**. It transitions through phases (pre-middleware → mid-middleware → pre-handler → mid-handler → post-handler) but the transitions live in control flow, not in typed state. The result: callers can't know what state the bus is in when they receive a return value, because the return type is a union over phases.

The original problem was three concerns in one dict. The improvement reveals that the three concerns are not just different *data* — they are different *states of a process* — and the process has no formal model.

---

## IX. The Structural Invariant

**The property that persists through every improvement:**

> `emit()` is the site where event publication (what happened), pipeline policy (how it's processed), and outcome retrieval (what handlers did) are coupled into a single synchronous call. This coupling cannot be removed by restructuring the data inside `emit()` — it is a property of what `emit()` means.

Every improvement moves the coupling but cannot dissolve it:

| Improvement | Where coupling lives |
|-------------|---------------------|
| Original dict | Inside the dict keys |
| `EventContext` dataclass | Inside the dataclass fields |
| Three-object split | Inside `emit()`'s return type union |

The coupling between "I published an event" and "I know what handlers did" is irreducible if `emit()` is synchronous and returns results.

---

## X. Invert the Invariant

The invariant: `emit()` must carry event identity + pipeline state + outcome.

**Inversion:** Make `publish()` know only about event identity. Outcome is retrieved separately. The bus is the only thing that knows about pipeline policy.

```python
import uuid
from collections import defaultdict
from typing import Callable

class DecoupledEventBus:
    def __init__(self):
        self._handlers = defaultdict(list)
        self._middleware = []
        self._outcomes: dict[str, HandlerOutcome] = {}
        self._dead_letter: list[str] = []  # stores event IDs, not objects

    def publish(self, event_type: str, payload: Any) -> str:
        """Only concerns: what happened and when. Returns an ID."""
        event_id = str(uuid.uuid4())
        event = Event(id=event_id, type=event_type, payload=payload)
        self._dispatch(event)  # internal; caller doesn't observe it
        return event_id

    def get_outcome(self, event_id: str) -> HandlerOutcome | None:
        """Outcome retrieval is separate from publication."""
        return self._outcomes.get(event_id)

    def _dispatch(self, event: Event):
        envelope = MiddlewareEnvelope(event=event)
        for mw in self._middleware:
            mw(envelope)
            if envelope.cancelled:
                return  # outcome simply doesn't exist for cancelled events

        handlers = self._handlers[event.type]
        outcome = HandlerOutcome(envelope=envelope)
        self._outcomes[event.id] = outcome  # stored by ID

        if not handlers:
            self._dead_letter.append(event.id)
            return

        for _, handler in handlers:
            try:
                outcome.results.append(handler(envelope))
            except Exception as e:
                outcome.errors.append((handler, e))
                self._dead_letter.append(event.id)
```

**The invariant is now trivially satisfied:** `publish()` returns a string. It knows nothing about pipeline state or handler outcomes. Event identity, pipeline policy, and outcome accumulation are separated across `publish()`, `_dispatch()`, and `get_outcome()`.

---

## XI. The New Impossibility

By decoupling publication from outcome:

> **You cannot have both clean event publication decoupling AND synchronous caller-knows-outcome semantics.**

Concretely: the caller publishes, gets an ID, then must either:
1. **Poll** `get_outcome(id)` — but when? After what delay?
2. **Subscribe** to a result event — adding another layer of event handling
3. **Block** until the outcome exists — but this is just `emit()` renamed
4. **Accept** that they may never know — fire-and-forget

The synchronous feedback loop — the thing that lets callers write `if result.succeeded: ...` immediately — is broken. Error propagation from handler to publisher is now a **separate distributed systems problem**.

---

## XII. The Conservation Law

| | Original Design | Inverted Design |
|--|----------------|-----------------|
| **What's easy** | Synchronous result access | Clean event publication |
| **What's impossible** | Decoupled publication | Synchronous result access |
| **Where coupling lives** | Inside `emit()` return value | Inside `get_outcome()` + caller state |

**The Conservation Law:**

> *Causal coupling between event publisher and handler outcome is conserved across all designs. Any architecture that reduces coupling at the publication site must increase coupling elsewhere: in result retrieval (caller maintains event IDs), in time (caller must wait or poll), in the event model (events carry result channels), or in coordination infrastructure (a result bus). The total accountability — someone must know that this event caused these effects — cannot be eliminated; it can only be relocated.*

**Corollary for the original code:**

The EventBus's actual problem is not that it has coupling — coupling is *required* by its use case (callers need results). The problem is that it hides **where the coupling lives** inside a mutable dict with no lifecycle semantics. Every "improvement" that adds structure makes the coupling's true location visible — which is why each improvement reveals a new problem. You are not finding new bugs. You are finding the **same coupling** as it migrates through the structure under pressure.

The real design question the code never asks: *Does the caller actually need synchronous results from handlers?* If yes, `emit()` returning results is correct and the dict is just badly structured. If no, the entire return-value contract is wrong and should be replaced with the decoupled design — accepting that synchronous error handling at the call site is now the caller's problem to solve.
