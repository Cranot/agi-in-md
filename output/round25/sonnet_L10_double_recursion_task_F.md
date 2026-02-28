# EventBus Deep Structural Analysis

---

## I. The Falsifiable Claim

**The deepest structural problem: this EventBus conflates event identity with event processing state by using a single mutable dict that simultaneously serves as the original event record, the middleware pipeline result, and the execution log — making no stage of processing independently verifiable, and making the dead letter queue semantically unusable.**

Falsifiable test: attempt to replay `bus._dead_letter[0]`. The stored context already contains `"error"`, `"results"`, and mutations from prior middleware. Re-emitting it sends a pre-corrupted object through the pipeline. The queue *promises* recoverability (it has a name, it accumulates) but *delivers* unstructured processing artifacts.

---

## II. Three Experts

**Expert A — Defender:** The claim holds. Consider:

```python
# Middleware A writes this:
context["authenticated"] = True

# Middleware B reads it back — fine.
# But handler writes:
context["error"] = SomeException(...)

# Now dead_letter[0] contains {"authenticated": True, "error": ...}
# Which field is the event? Which is the audit trail?
```

Any consumer of `_dead_letter` must defensively strip processing artifacts before reprocessing. The queue is architecturally present but operationally incoherent.

**Expert B — Attacker:** This overstates the problem. Mutable shared context is the dominant pattern in production middleware systems: Express.js `req/res`, Django's `request`, WSGI's `environ`. The "conflation" is intentional — it *is* a processing record. The actual bugs are mundane:

- `context["error"] = e` is last-writer-wins across handlers — multiple handler exceptions silently discard all but the last
- `sort()` on every `on()` call is O(n log n) per registration
- No thread safety anywhere
- `id(handler)` as an implicit registry key means two handlers can collide

**Expert C — Prober:** Both experts assume a dead letter queue should be replay-capable. Why? Neither asks whether `_dead_letter` is ever *consumed* in this codebase. If it's vestigial — appended to and never read — the conflation is real but dormant.

What both take for granted: that the *purpose* of the dead letter queue is defined. The code has the vocabulary of reliability engineering (dead letter is an AMQP concept) without the semantics. The professional naming *suppresses the question* of what you'd actually do with those entries.

---

## III. The Transformation

Original claim: *context conflates event identity with processing state.*

After dialectic: the conflation is a symptom. The disease is a **broken contract at the dead letter boundary** — the queue promises recoverability across two structurally different failure modes (no subscribers = routing failure; handler exception = execution failure) but stores both as the same mid-execution context object, making them neither safely replayable nor cleanly distinguishable.

The gap between original and transformed claim is diagnostic: I named a structural property (conflation) when the real problem is a broken promise (the queue exists but cannot fulfill its implied contract).

---

## IV. The Concealment Mechanism

**Functional completeness theater:** Each component works correctly in isolation — middleware chains, priorities sort, dead letters accumulate. Individual correctness *conceals* joint incoherence. The professional vocabulary does active work here: "dead letter queue" imports an entire operational model (poison messages, retry logic, manual inspection) that this code doesn't implement. The name licenses you to stop asking what the feature actually does.

Secondary mechanism: **error swallowing as feature.** `try/except` around every handler looks like defensive engineering. It is actually information destruction — exceptions are caught, stored on a shared mutable dict, and silently overwritten by subsequent handler failures.

---

## V. The Concealing Improvement

A legitimate improvement that deepens the concealment:

```python
import time
from typing import Callable, Optional

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[tuple[int, Callable]]] = {}
        self._middleware: list[Callable] = []
        self._dead_letter: list[dict] = []
        self._handler_registry: dict[int, tuple[str, Callable]] = {}

    def on(self, event_type: str, handler: Callable, priority: int = 0) -> int:
        """Register a handler. Returns handler_id for later deregistration."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        handler_id = id(handler)
        self._handler_registry[handler_id] = (event_type, handler)
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])
        return handler_id

    def off(self, handler_id: int) -> bool:
        """Deregister a handler by ID. Returns True if found and removed."""
        if handler_id not in self._handler_registry:
            return False
        event_type, handler = self._handler_registry.pop(handler_id)
        self._handlers[event_type] = [
            (p, h) for p, h in self._handlers[event_type] if h is not handler
        ]
        return True

    def use(self, middleware_fn: Callable) -> None:
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: dict) -> dict:
        context = {
            "type": event_type,
            "payload": payload,
            "cancelled": False,
            "timestamp": time.monotonic(),
        }
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(context)
            return context
        results = []
        for _, handler in handlers:
            try:
                results.append(handler(context))
            except Exception as e:
                context["error"] = e
                self._dead_letter.append(context)
        context["results"] = results
        return context
```

**Why this passes code review:**
- Type annotations signal professionalism
- `off()` fills a real feature gap (deregistration is a legitimate need)
- Returning `handler_id` matches standard observer pattern APIs
- `timestamp` in context looks like useful telemetry
- The improvement is additive — it doesn't touch the problematic core logic

**Why it deepens the concealment:**
The code now looks substantially more production-ready. The `off()` feature and typed signatures attract reviewer attention to the lifecycle management surface, away from the dead letter semantics. More critically: `id(handler)` as a stable identifier introduces a subtle bug (Python reuses memory addresses for garbage-collected objects) that is harder to see precisely because the API looks correct.

---

## VI. Three Properties Visible Because We Tried to Strengthen It

**Property 1 — Mutation-during-iteration hazard:**
`emit()` holds a reference to `self._handlers[event_type]` — the *same list* that `off()` mutates via list comprehension replacement. If a handler calls `bus.off(some_id)` during `emit()`, the list reference in `handlers` is now stale — it points to the old list that has been replaced in `self._handlers`, meaning `off()` silently fails to affect the current execution. This race is only visible because we tried to add lifecycle management, which forced the question: what is the ownership boundary of the handler list?

**Property 2 — The identity problem of `id()`:**
Using `id(handler)` as a stable registry key assumes object identity outlives registration. But:

```python
bus.on("click", lambda e: print(e))  # lambda immediately eligible for GC
# Python may reuse the same address for a completely different object
# _handler_registry now maps that id to a dead reference
```

This is only visible because we tried to give handlers stable, returnable identities — which forces the question: what *is* the identity of an event, a handler, or a context in this system? The original code had no answer; our improvement needed one and discovered the question was unanswered.

**Property 3 — Partial-execution records in dead letter:**
With `off()` available, a handler can deregister another handler mid-`emit()`. The dead letter entry appended during that execution captures a context where some handlers have run and some haven't — a partially-executed processing record. The improvement reveals that the dead letter queue doesn't just store corrupted contexts; it stores *partially-executed* states with no record of which handlers fired. Replay is not just semantically ambiguous — it's execution-order-dependent.

---

## VII. Recursive Diagnostic on the Improvement

**What the improvement conceals:**
`id(handler)` failure modes are silent. If a handler is garbage collected and its memory reused, `off(handler_id)` deregisters the *wrong* handler with no error. The improvement introduces a new class of incorrect behavior that looks like correct behavior until a specific memory allocation pattern triggers it.

**What property of the original problem is visible because the improvement recreates it:**
The original problem was mutable shared state with no ownership boundaries. The improvement recreates this one level up: `_handler_registry` and `_handlers` both hold references to the same handler functions, and `off()` mutates a list that `emit()` may be actively using. The structural property — **mutable shared state with undefined ownership** — reappears at the handler management layer. We fixed it at the context layer and it surfaced at the registry layer.

---

## VIII. The Second Improvement

Addressing the recreated property (mutation hazard + partial-execution dead letter):

```python
import time
import copy
from typing import Callable, Any

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[tuple[int, Callable]]] = {}
        self._middleware: list[Callable] = []
        self._dead_letter: list[dict] = []
        self._handler_registry: dict[int, tuple[str, Callable]] = {}
        self._next_id: int = 0  # monotonic, never reuses

    def on(self, event_type: str, handler: Callable, priority: int = 0) -> int:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        handler_id = self._next_id
        self._next_id += 1
        self._handler_registry[handler_id] = (event_type, handler)
        self._handlers[event_type].append((priority, handler_id))
        self._handlers[event_type].sort(key=lambda x: -x[0])
        return handler_id

    def off(self, handler_id: int) -> bool:
        if handler_id not in self._handler_registry:
            return False
        event_type, _ = self._handler_registry.pop(handler_id)
        self._handlers[event_type] = [
            (p, hid) for p, hid in self._handlers[event_type]
            if hid != handler_id
        ]
        return True

    def use(self, middleware_fn: Callable) -> None:
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> dict:
        # Freeze the original event — never mutated
        original_event = {"type": event_type, "payload": payload}

        context = {**original_event, "cancelled": False}
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context

        # Snapshot handler IDs to prevent mutation-during-iteration
        handler_snapshot = list(self._handlers.get(event_type, []))

        if not handler_snapshot:
            self._dead_letter.append({
                **original_event,
                "reason": "no_handlers",
                "timestamp": time.monotonic(),
            })
            return context

        results = []
        errors = []

        for _, handler_id in handler_snapshot:
            # Handler may have been deregistered since snapshot — skip cleanly
            if handler_id not in self._handler_registry:
                continue
            _, handler = self._handler_registry[handler_id]
            try:
                results.append(handler(context))
            except Exception as e:
                errors.append({
                    "handler_id": handler_id,
                    "handler_name": getattr(handler, "__name__", repr(handler)),
                    "error": e,
                })

        if errors:
            self._dead_letter.append({
                **original_event,
                "reason": "handler_errors",
                "errors": errors,
                "timestamp": time.monotonic(),
            })

        context["results"] = results
        if errors:
            context["errors"] = errors

        return context
```

**What this addresses:**
- Monotonic `_next_id` eliminates the `id()` address-reuse hazard
- Handler list stores IDs, not callables — `off()` and `emit()` share no mutable callable references
- Snapshot (`list(...)`) prevents mutation-during-iteration
- Deregistration during `emit()` is handled cleanly: `if handler_id not in self._handler_registry: continue`
- Dead letter stores clean `original_event` + structured metadata, not processing artifacts
- All errors collected, not last-error-wins

---

## IX. Recursive Diagnostic on the Second Improvement

**What this improvement conceals:**
The snapshot-and-skip pattern looks like it handles deregistration-during-emission correctly. It does handle it *mechanically*. But it conceals a semantic question: **what is the correct behavior when a handler deregisters another handler that hasn't run yet?** Should the deregistered handler run (snapshot says yes, it was registered when `emit` started) or not (it was deregistered before it ran)?

The code gives an answer — it *runs* the handler, because the snapshot precedes the skip check... wait, actually it checks `if handler_id not in self._handler_registry` for each handler, so deregistration takes effect mid-execution. This means the behavior depends on execution order, which depends on priority, which is user-controlled. The improvement trades one implicit behavior (mutation-during-iteration) for another (priority-dependent deregistration semantics).

**What property of the original problem is visible because the improvement recreates it:**

The original problem: *the returned `context` conflates "what the event was" with "what happened to it."*

The second improvement cleanly separates the dead letter record from the processing context. But:

```python
context["results"] = results
if errors:
    context["errors"] = errors
return context
```

The *returned value* still conflates event identity with execution results. `context` was `{"type": ..., "payload": ..., "cancelled": False}` before processing and is `{"type": ..., "payload": ..., "cancelled": False, "results": [...], "errors": [...]}` after. The caller cannot distinguish what they sent from what came back.

The original conflation persists in the return value because we only fixed it for the dead letter path. This reveals that the conflation is not a problem with the dead letter queue specifically — **it is a problem with the decision to return the context as both the event record and the result record.**

---

## X. The Structural Invariant

**The property that persists through every improvement, because it is a property of the problem space:**

> **An EventBus that passes a mutable context through a transformation chain cannot simultaneously satisfy: (1) events are stable records of what was requested, (2) processing results are accumulated on the same object, and (3) the return value of `emit()` is unambiguously interpretable by the caller.**

Any two of these three can be satisfied. All three cannot.

- Satisfy (1) and (2): accumulate results on a copy — but the copy and the original share no identity, so the caller cannot correlate them.
- Satisfy (1) and (3): return the original event unchanged — but then how does the caller get results?
- Satisfy (2) and (3): accumulate on the original and return it — but now the "event" and the "result" are the same object, which is what every version of this code does.

This is the **command-query conflation**. `emit()` is simultaneously a command (dispatch this event) and a query (what did the handlers return). The context is simultaneously an input (here is the event) and an output (here is what happened). No improvement that keeps this API shape escapes the invariant.

The only exits are architectural:
```python
# Exit 1: Separate event from result
result = bus.emit(event_type, payload)        # returns Result, not mutated event
# Event identity is never exposed to the caller

# Exit 2: Out-of-band results
bus.emit(event_type, payload, callback=fn)   # results delivered asynchronously
# emit() returns nothing — command only

# Exit 3: Immutable event + pure handlers
# Handlers receive event, return new state; bus reduces results
# Context is never mutated — processing state is separate
```

Every improvement attempted here was a local fix applied inside the invariant boundary. The boundary itself is the EventBus contract: `emit(type, payload) → context`. That signature encodes the conflation. The invariant cannot be fixed without changing it.
