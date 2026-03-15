# EventBus: Structure-First Diagnostic

---

## Step 1 — Falsifiable Claim: The Deepest Problem

**The context object is simultaneously the message envelope and the shared mutable accumulator, making handler isolation structurally impossible.**

This is falsifiable: write a test where two handlers with equal priority mutate `context["payload"]`. The second handler sees the first's mutation. The system *looks* like message-passing but is shared-memory mutation behind an `emit()` façade.

The secondary falsifiable: every `_dead_letter.append(context)` call inside the handler loop appends a *live reference*. After `emit` completes, all dead-letter entries from that call reflect the **final** state of context, not the state at the moment the error occurred. The dead letter queue does not record history — it holds aliases to one object.

---

## Step 2 — Three Experts Transform It

**Defender (pragmatist):** Context threading is intentional — handler B *should* see handler A's result. This is a pipeline, not pub/sub. Priority sort is stable for any fixed handler set. Dead letter queue shows the author considered failure. Practical, ships.

**Attacker (correctness):** Execution continues after an exception. `results.append(handler(context))` appends `None` for errored handlers *and* for handlers that legitimately return `None`. You cannot distinguish error from success returning `None`. Worse: `context["error"] = e` is overwritten by each subsequent exception — only the *last* error survives. The results list lies about what happened.

**Probe (assumptions):** Middleware is called as `context = mw(context)`. If `mw` returns `None`, the next line `context.get("cancelled")` raises `AttributeError` — silent crash. Meanwhile, handlers are not reassigned into context at all; their return values are collected separately. This asymmetry *assumes* middleware is transformational and handlers are terminal effectors — but nothing enforces this contract. A handler that returns a new context dict is silently ignored. A middleware that returns `None` destroys the bus. The design relies on caller discipline it never documents.

---

## Step 3 — The Concealment Mechanism: Aliasing Through Shared Mutable Reference

Every middleware invocation, every handler call, and every dead-letter append operates on **the same dict object**. The call site sees an `emit()` with a return value — it looks like a function with a result. What it actually is: a sequence of mutations to one object, with a reference returned at the end.

The concealment is specifically **temporal aliasing of the dead letter queue**:

```python
# current code — every append is the SAME object
for _, handler in handlers:
    try:
        results.append(handler(context))
    except Exception as e:
        context["error"] = e
        self._dead_letter.append(context)  # reference, not snapshot
        # ^ after emit() returns, this entry will show context["results"] = [...]
        #   and context["error"] = <last error>, not the error at this moment
```

The dead letter queue *appears* to record the state at failure time. It records nothing — it accumulates aliases to a still-mutating object.

---

## Step 4 — First Improvement: Deepening Concealment While Passing Review

Apply shallow copying to dead letter entries and guard the middleware `None` crash:

```python
def emit(self, event_type, payload):
    context = {"type": event_type, "payload": payload, "cancelled": False}
    
    for mw in self._middleware:
        result = mw(context)
        if result is not None:          # guard: middleware returning None no longer crashes
            context = result
        if context.get("cancelled"):
            return context

    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(dict(context))   # shallow copy: looks like a snapshot
        return context

    results = []
    for _, handler in handlers:
        try:
            results.append(handler(context))
        except Exception as e:
            context["error"] = e
            self._dead_letter.append(dict(context))   # shallow copy per error
    
    context["results"] = results
    return context
```

This passes review: "they fixed the `None` middleware crash, they copy context before appending to dead letter — aliasing addressed." But it deepens concealment:

1. `dict(context)` is a shallow copy. If `payload` is a dict or list (extremely common), the dead-letter entry and the live context still share the same payload reference. Payload mutations after the copy invalidate every dead-letter snapshot silently.
2. The `if result is not None` guard means middleware returning `None` is now a silent no-op rather than a crash. The bug now hides instead of failing loudly.
3. Dead-letter entries captured mid-loop are missing `context["results"]` (added after the loop). Entries captured at dead-letter-on-no-handlers have no `results` key at all. The snapshots represent **different moments in the event lifecycle** and are not comparable — but they look identical in structure.

---

## Step 5 — Three Properties Visible Only Because You Tried to Strengthen It

**Property 1: Payload aliasing is irreducible without restricting what events can carry.**
The shallow copy reveals that the actual shared state lives *inside* payload, not in the envelope. You cannot deep-copy all payloads — sockets, database connections, file handles, and locks are valid event payloads in real systems. Any fix that stops at `dict(context)` is performing cosmetic surgery. The structural impossibility of general deep-copy was hidden until you tried to fix aliasing.

**Property 2: The dead letter queue has no coherent definition of "when."**
Trying to snapshot context at error time reveals that different dead-letter entries represent incomparable moments: before middleware ran, after middleware but before handlers, mid-handler-loop, post-loop. The queue claims to record failures but captures no agreed-upon lifecycle stage. This only becomes visible when you try to make the snapshots accurate.

**Property 3: The middleware/handler asymmetry is load-bearing, not accidental.**
Fixing the `None` middleware crash reveals why middleware returns context (it transforms the envelope) while handlers do not (they produce results). The asymmetry encodes a design intent — middleware shapes the message, handlers consume it. But nothing prevents a handler from trying to transform context, and the `if result is not None` guard makes this *more* invisible, not less. The architectural rule is now enforced by silence.

---

## Step 6 — Same Diagnostic Applied to the First Improvement

**Falsifiable deepest problem:** The first improvement is performing **snapshot theater** — the shallow copies create the *visual grammar* of immutability (reviewers see `dict(context)` and infer "aliasing fixed") while payload sharing continues. The fix passes review by satisfying the *appearance* of the invariant without satisfying its *substance*.

Test: Create a bus. Subscribe two handlers. Emit with `payload = {"count": 0}`. Handler 1 does `context["payload"]["count"] += 1` then raises an exception. Inspect `_dead_letter[0]["payload"]["count"]` after emit completes. It will not be `0`.

The concealment mechanism is identical: shared mutable reference, now one layer deeper.

---

## Step 7 — Second Improvement: Address the Recreated Property

Separate error recording from envelope mutation, and explicitly acknowledge the payload aliasing boundary:

```python
def emit(self, event_type, payload):
    context = {"type": event_type, "payload": payload, "cancelled": False}

    for mw in self._middleware:
        result = mw(context)
        if result is not None:
            context = result
        if context.get("cancelled"):
            return {"type": event_type, "cancelled": True}

    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append({**context, "reason": "no_handlers"})
        return context

    results = []
    errors = []
    for _, handler in handlers:
        try:
            results.append({"handler": handler.__name__, "value": handler(context)})
        except Exception as e:
            # Error recorded separately — never written into context
            errors.append({
                "handler": handler.__name__,
                "error": e,
                # Deliberately shallow: payload aliasing is now explicit, not hidden
                "envelope": {k: v for k, v in context.items() if k != "payload"},
            })

    context["results"] = results
    if errors:
        context["errors"] = errors
        self._dead_letter.append({**context})  # errors are now in context, not lost

    return context
```

Key changes: errors are never written into `context["error"]` (no overwriting, no mutation during handler loop); each error records which handler failed; the snapshot explicitly excludes payload and documents *why* — the aliasing is now **stated**, not hidden. Dead-letter entries are taken post-loop, so they have a consistent lifecycle stage.

---

## Step 8 — The Structural Invariant

> **The message IS the mailbox.**

In any dispatch system where the communication channel and the result accumulator are the same object, handler isolation and handler coordination are mutually exclusive. You cannot have both:

- **Isolation**: handler B's behavior is independent of handler A's side effects
- **Coordination**: handlers can influence each other's behavior or observe each other's outputs

Increasing one decreases the other by the same degree. This is not a Python problem, not a mutability problem, not a threading problem. It is a property of any system where one object plays both roles.

---

## Step 9 — Inversion: Design Where the Impossible Becomes Trivial

Separate message from mailbox completely. The event is read-only. Handlers write to a result collector no other handler can read. The bus aggregates after all handlers complete.

```python
from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass(frozen=True)
class Event:
    type: str
    payload: Any   # frozen envelope; payload immutability is caller's responsibility

class Emission:
    """The mailbox. Handlers never see this."""
    def __init__(self):
        self.results: list = []
        self.errors: list = []
    def record(self, handler_name, value):
        self.results.append({"handler": handler_name, "value": value})
    def record_error(self, handler_name, exc):
        self.errors.append({"handler": handler_name, "error": exc})

class IsolatedEventBus:
    def __init__(self):
        self._handlers: dict = {}
        self._dead_letter: list = []

    def on(self, event_type, handler, priority=0):
        self._handlers.setdefault(event_type, [])
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def emit(self, event_type, payload) -> Emission:
        event = Event(type=event_type, payload=payload)
        emission = Emission()
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(event)
            return emission
        for _, handler in handlers:
            try:
                emission.record(handler.__name__, handler(event))
            except Exception as e:
                emission.record_error(handler.__name__, e)
        return emission
```

Handler isolation is now trivial: `Event` is a frozen dataclass; handlers cannot mutate it. One handler's exception does not affect another. Dead letter holds the event, not a mutated context snapshot.

---

## Step 10 — The New Impossibility

**Late-binding orchestration is impossible.**

Handler A cannot:
- Signal handler B to stop running
- Transform what handler B receives
- Make its own success a precondition for handler B's execution

Cancellation, conditional chaining, and handler-to-handler communication are structurally prohibited. You traded *isolation failure* for *coordination impossibility*.

A secondary impossibility: dynamic routing based on handler output. If handler A returns a value indicating "route to EventTypeX next," the bus cannot act on this — it receives results only after all handlers have run, and the routing graph is fixed at emit time.

---

## Step 11 — The Conservation Law

> **In any event dispatch system, coordination capacity and handler isolation sum to a constant determined by the dispatch topology, not the implementation.**

Let *I* = degree to which a handler's behavior is independent of other handlers' side effects.  
Let *C* = degree to which handlers can influence each other's behavior or observe each other's outputs.

*I + C = k*, where *k* is fixed by the dispatch topology.

The original design chose low *I*, high *C* (shared mutable context — handlers fully coordinate, zero isolation).  
The inverted design chose high *I*, zero *C* (frozen event, separate collector — handlers are isolated, cannot coordinate).

Neither implementation can increase *k*. To increase *k* — to gain both more isolation and more coordination simultaneously — you must change the topology: add a coordination channel, introduce a hierarchical bus, use continuation-passing. The constant is conserved *per topology layer*.

This does not restate "mutable state is bad." It states that isolation and coordination are not independent design dimensions. They are dual. Every architectural decision that increases one decreases the other, and the exchange rate is fixed by structure, not code.

---

## Step 12 — Prediction: The Third Design

Consider a **reactive/stream-based event bus** — neither design attempted. RxPY-style observables: `emit()` pushes to a stream, handlers subscribe, operators (`filter`, `merge`, `scan`, `share`) compose behavior.

**The conservation law predicts:**

The reactive design will *appear* to escape the tradeoff. Handlers look isolated (each receives stream events, not shared state). Coordination looks free (operators compose outputs declaratively). The tradeoff will have been **relocated, not resolved**.

Specifically:
- `scan` (stream reduce) accumulates handler results — this is the mutable context dict rewritten as a fold over time. The accumulator is the aliasing problem, now inside the operator.
- `share()` / `publish()` causes multiple subscribers to share upstream state. Subject a shared observable to a slow handler — all downstream subscribers see the backpressure effect. Aliasing through shared stream state is identical to aliasing through shared dict, expressed in different notation.
- Cancellation (the new impossibility from Design 2) is solved by `takeUntil()` — but `takeUntil()` requires a *separate cancellation signal stream*, which is a new coordination channel. The total coordination capacity hasn't increased; a second topology layer was added.

**The falsifiable prediction:** Find any reactive event bus that supports both (a) handler isolation — one handler's exception does not affect another — and (b) cross-handler coordination — cancel-on-first-success, or conditional chaining. The mechanism implementing (b) will contain shared mutable state equivalent in complexity to the original context dict, located inside a stream operator. The law will be conserved. The state will just have a better name.

---

## Summary Map

| Design | *I* (Isolation) | *C* (Coordination) | What's hidden |
|---|---|---|---|
| Original | Low | High | Context is shared memory; dead letter is aliased |
| First improvement | Low+ | High | Shallow copy performs correctness theater |
| Second improvement | Medium | Medium | Payload aliasing acknowledged; handler coordination reduced |
| Inverted (IsolatedEventBus) | High | Zero | Coordination is structurally impossible |
| Reactive (predicted) | Medium | Medium | Coordination capacity moves into operators; aliasing survives as stream state |

The conservation law holds across all five. The sum *I + C* is reallocated, never increased, until the topology itself is extended.
