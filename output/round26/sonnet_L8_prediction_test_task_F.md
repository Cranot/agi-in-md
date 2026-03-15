## Level 8 Diagnostic: EventBus

---

### Step 1 — Initial Falsifiable Claim

> **Claim:** The deepest structural problem is the mutable shared `context` dict, passed by reference through middleware *and* handlers with no contract governing what either layer is permitted to mutate. Any non-trivial pipeline will produce silent corruption for downstream consumers.

Falsifiable form: *"Given two middleware functions and two handlers, it is impossible to reason about what `context` contains at any point without reading all of them."*

---

### Step 2 — Three Experts Attack the Claim

**Expert A (Defender):**
The claim holds. `context["error"]` is overwritten on every exception — only the *last* error survives. A middleware setting `context["payload"] = None` silently corrupts all handlers. The dict is the shared mutable crime scene.

**Expert B (Attacker):**
The claim misidentifies the deepest problem. Yes, the dict is messy, but there is **no unsubscription path**. `on()` appends forever with no handle returned, no `off()`, no weak references, no expiry. This is a subscription-leak machine. The mutable context is a symptom; the missing lifecycle is the disease.

**Expert C (Prober — what do both take for granted?):**
Both of you assume `emit` is the right unit of analysis, and both assume synchronous execution. Look at `results.append(handler(context))` — if any handler is async, `results` silently contains unawaited coroutines. More importantly: you both assume `_dead_letter` is a dead-letter queue. It isn't. It's an **unbounded append-only list with no consumer API**. Unhandled events and error events both land there. There is no flush, no size cap, no way to distinguish "no handler registered" from "handler threw." The shared assumption is that *naming a list after a pattern instantiates the pattern.*

---

### Step 3 — Transformed Claim

> **Transformed Claim:** The deepest structural problem is **identity fraud of features**. Each apparent design element — middleware pipeline, dead-letter queue, priority ordering, error capture — presents the *silhouette* of a real pattern while being structurally hollow. The middleware has no mutation contract. The DLQ has no consumer. Priority ordering has no unsubscription. Error capture overwrites itself. The bus doesn't route events; it accumulates state about failed routing with no recovery mechanism.

---

### Step 4 — The Gap Is Itself the Diagnostic

| | Original Claim | Transformed Claim |
|---|---|---|
| **Scope** | Local (one dict, one parameter) | Systemic (entire architecture) |
| **Mechanism** | Mutation without contract | Pattern silhouette without implementation |
| **Fix implied** | Freeze or copy the context | Redesign the feature contracts |

**Concealment Mechanism: Pattern Silhouette**

The code uses *recognizable names* to trigger pattern-recognition in reviewers, short-circuiting structural analysis:

- `_middleware` → reviewer thinks "Express.js interceptor chain" → mentally fills in the missing mutation contract
- `_dead_letter` → reviewer thinks "message broker DLQ" → assumes a consumer exists somewhere
- `priority` → reviewer thinks "task queue ordering" → doesn't notice the missing deregistration
- `context["error"]` → reviewer thinks "error propagation" → doesn't notice it overwrites on multiple failures

The names *do the concealing*. The implementation never needs to be complete because the pattern completes it in the reader's mind.

---

### Step 5 — Legitimate-Looking Improvement That Deepens the Concealment

This passes code review. It addresses every visible critique while making the real problems invisible.

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from collections import namedtuple

# Named tuple makes results look properly typed and traceable
HandlerResult = namedtuple('HandlerResult', ['handler_id', 'value', 'error'])

@dataclass
class EventContext:
    """
    Typed, structured event context replacing raw dict.
    Middleware should mutate only `metadata` for cross-cutting concerns.
    """
    type: str
    payload: Any
    cancelled: bool = False
    results: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)   # ← the escape hatch

class EventBus:
    def __init__(self):
        self._handlers: dict = {}
        self._middleware: list = []
        self._dead_letter: list = []
        self._handler_counter: int = 0

    def on(self, event_type: str, handler: Callable, priority: int = 0) -> int:
        """Returns handler_id for later deregistration."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        handler_id = self._handler_counter
        self._handler_counter += 1
        self._handlers[event_type].append((priority, handler_id, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])
        return handler_id

    def off(self, event_type: str, handler_id: int) -> None:
        """Deregister a handler by its id."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                (p, hid, h) for p, hid, h in self._handlers[event_type]
                if hid != handler_id
            ]

    def use(self, middleware_fn: Callable) -> None:
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> EventContext:
        context = EventContext(type=event_type, payload=payload)
        for mw in self._middleware:
            context = mw(context)
            if context.cancelled:
                return context
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(context)
            return context
        for _, handler_id, handler in handlers:
            try:
                value = handler(context)
                context.results.append(
                    HandlerResult(handler_id=handler_id, value=value, error=None)
                )
            except Exception as e:
                context.results.append(
                    HandlerResult(handler_id=handler_id, value=None, error=e)
                )
                self._dead_letter.append(context)
        return context

    def flush_dead_letters(self, consumer: Callable[[EventContext], None]) -> int:
        """Drain dead-letter queue into a consumer callback. Returns count flushed."""
        letters = self._dead_letter[:]
        self._dead_letter.clear()
        for letter in letters:
            consumer(letter)
        return len(letters)
```

**Why this passes review:**
- `EventContext` dataclass signals type discipline
- `HandlerResult` namedtuple signals traceable result handling  
- `on()` returning `handler_id` signals lifecycle management exists
- `off()` directly answers the "no unsubscribe" critique
- `flush_dead_letters` signals the DLQ now has a consumer API
- Docstrings signal intentional design

---

### Step 6 — Three Properties Only Visible Because I Tried to Strengthen It

**Property 1: The architecture requires an untyped escape hatch — `metadata` is structural, not incidental**

When I added the typed `EventContext` dataclass, I immediately needed somewhere for middleware to store arbitrary cross-cutting data (request IDs, trace spans, auth tokens). I added `metadata: dict`. This is structurally *identical* to the original problem — an uncontracted mutable bag — just renamed. The pressure for this escape hatch doesn't go away with better typing. This reveals that the mutable-context problem isn't a bug to be fixed; it's a **load-bearing requirement of the middleware model**. The original code is honest about this in a way the improved version isn't.

**Property 2: `_dead_letter` conflates two irreconcilably different failure modes**

When I implemented `flush_dead_letters(consumer)`, I had to think about what `consumer` receives. Both "event with no registered handlers" and "event whose handler threw an exception" land in the same list. These require fundamentally different recovery strategies:
- No handlers → retry after registration, or discard
- Handler exception → retry with fixed payload, alert, or poison-pill

A single `consumer: Callable[[EventContext], None]` cannot distinguish these without inspecting opaque context state. My improvement added an API around a category error. The conflation was invisible before I tried to give it a consumer.

**Property 3: `handler_id` unsubscription creates false lifecycle confidence without lifecycle semantics**

`off(event_type, handler_id)` looks like it solves the subscription leak. But `handler_id` is a bare integer encoding no information about what event type it belongs to, when it was registered, or whether it's still valid. The caller must store both `event_type` and `handler_id` to use `off()` — meaning the caller is managing the lifecycle, not the bus. Worse: any handler registered before a bus restart has an id that maps to nothing, silently. The `off()` method doesn't solve subscription lifecycle; it **transfers responsibility for it to the caller while making the bus look like it's handling it**. This is only visible because I tried to implement proper unsubscription and discovered it requires a fundamentally different registration model — a `Subscription` handle object that knows its own type, id, and validity.

---

### Summary Table

| Feature | What it looks like | What it is | Deepened by improvement |
|---|---|---|---|
| `_middleware` | Interceptor pipeline | Uncontracted mutation chain | `metadata` escape hatch makes contract *look* present |
| `_dead_letter` | Message broker DLQ | Append-only memory growth | `flush_dead_letters` hides the category error |
| `priority` | Ordered dispatch | One-way registration | `handler_id` creates false lifecycle confidence |
| `context["error"]` | Error propagation | Last-write-wins overwrite | `HandlerResult` per-handler hides bus-level error ambiguity |

The concealment mechanism is that **well-named structural holes read as implemented features**. Every improvement that adds a name to the hole makes the hole harder to see.
