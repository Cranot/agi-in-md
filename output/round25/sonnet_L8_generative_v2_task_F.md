## The Claim

**Falsifiable structural claim:** `context` serves simultaneously as event descriptor, middleware state, result accumulator, and error container — meaning no component can reason about the object's validity at any point in the pipeline. This isn't incidental; it's load-bearing. Remove it, and the entire design collapses.

---

## Three Experts

**Defender:** The claim is tight and testable. If handler[0] throws, `context["error"] = e` is set before handler[1] runs. Handler[1] now receives a poisoned context it didn't cause and can't distinguish from a clean one. Write this test:

```python
def handler_1(ctx): raise ValueError("oops")
def handler_2(ctx): return ctx.get("error") is None  # will return False, wrongly

bus.on("x", handler_1, priority=10)
bus.on("x", handler_2, priority=0)
bus.emit("x", {})
# results: [False] — handler_2 reports error state it didn't produce
```
Falsified if you find a way to isolate handler error state without redesigning context. You can't, because the dict is the only communication channel.

**Attacker:** You've named a symptom. The deeper problem is that `emit()` returns a value and callers use it. Real pub/sub is fire-and-forget. The moment `emit()` returns `context["results"]`, this became a **synchronous request/response pipeline**. Context mutation is just what pipelines look like. Fix async support and you'd need to redesign context anyway — your claim dissolves.

**Prober (what both take for granted):** You both assume handlers and middleware are meaningfully different roles. Look again: both receive `context`, both can mutate it, both can cancel it. The only difference is registration API. You're arguing about *correctness within the design* while the design itself is misrepresented. The names — `EventBus`, `emit`, `on`, `handler` — are all borrowed from pub/sub. But `emit()` returns results, handlers return values into a `results` array, callers depend on those values. **This is not an event bus. It's an HTTP middleware chain with event-flavored vocabulary.** Every bug is downstream of that identity confusion.

---

## The Transformation

| | |
|---|---|
| **Original claim** | Context mutation prevents error isolation between handlers |
| **Transformed claim** | The pub/sub vocabulary launders the fact that this is a synchronous request/response pipeline; every correctness problem is a structural identity problem |

**The gap:** The original claim was about *correctness* (can handlers reason about state?). The transformed claim is about *semantic identity* (what kind of system is this?). The gap reveals the surface bugs aren't bugs to be fixed — they're *load-bearing features of the wrong abstraction.*

---

## The Concealment Mechanism: Vocabulary Laundering

Pub/sub vocabulary suppresses the right questions:

- `emit` implies fire-and-forget → suppresses "why does `emit()` return anything?"
- `on` implies independent listeners → suppresses "why do handlers execute sequentially in priority order?"
- `dead_letter` sounds like serious message-queue infrastructure → suppresses "why does a bus conflate 'no handlers found' with 'handler threw an exception'?"
- `priority` implies ordering of *independent* observers → suppresses "wait, do these handlers have ordering dependencies?"

The vocabulary works because it's *almost* right. You can read this code in 30 seconds and recognize the pattern. Recognition terminates inspection.

---

## The Legitimate-Looking Improvement That Deepens Concealment

Add wildcard matching, fix the `None`-return middleware bug, snapshot context on error, and add handler-level stop-propagation:

```python
import fnmatch
import time

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

    def off(self, event_type, handler):
        if event_type in self._handlers:
            self._handlers[event_type] = [
                (p, h) for p, h in self._handlers[event_type] if h is not handler
            ]

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type, payload):
        context = {
            "type": event_type,
            "payload": payload,
            "cancelled": False,
            "timestamp": time.monotonic(),
        }

        for mw in self._middleware:
            result = mw(context)
            # Fix: guard against middleware returning None
            context = result if result is not None else context
            if context.get("cancelled"):
                return context

        # Fix: wildcard matching — now looks like a real message bus
        matched = []
        for pattern, handlers in self._handlers.items():
            if fnmatch.fnmatch(event_type, pattern):
                matched.extend(handlers)
        matched.sort(key=lambda x: -x[0])

        if not matched:
            self._dead_letter.append(context)
            return context

        results = []
        for _, handler in matched:
            # Fix: respect stop-propagation set by a handler
            if context.get("cancelled"):
                break
            try:
                results.append(handler(context))
            except Exception as e:
                # Fix: snapshot so dead letter isn't aliased to live context
                snapshot = {**context, "error": e}
                self._dead_letter.append(snapshot)

        context["results"] = results
        return context
```

This **passes code review.** It fixes real bugs. It adds a genuinely useful feature (wildcard). It looks like a maturing event system.

---

## Three Properties Only Visible Because I Tried to Strengthen It

**1. Handler-level `cancelled` check exposes sequential dependency as a first-class feature.**

When I added `if context.get("cancelled"): break` inside the handler loop, it seemed natural. But it reveals that handlers were *already* sequentially dependent — handler[1] was always running after handler[0] mutated context. In true pub/sub, handlers are independent. The improvement didn't add sequential dependency; it *promoted* a hidden dependency to an intentional feature. The concealment deepens because now it looks designed.

**2. The return value of `emit()` has no principled semantics under wildcards.**

Once I added `fnmatch` matching, the question became unavoidable: if `user.created` matches both `user.*` and `*.created`, and three handlers each return different values, what does `context["results"]` mean to the caller? There's no answer. The `results` array is only coherent if you know exactly which handlers ran in which order — i.e., if callers are *coupled* to bus internals. This property was always true; trying to make `emit()` work with wildcards made it impossible to ignore.

**3. The dead letter queue has two irreconcilable purposes and no snapshot semantics.**

In message queuing, dead letter means: "could not deliver, preserve for retry." Here, contexts arrive in `dead_letter` for two completely different reasons: no handlers registered (delivery failure), and a handler threw (delivery succeeded, execution failed). The snapshot fix (`{**context, "error": e}`) made this visible by creating *two different object shapes* in the same queue — one without `"error"`, one with. A consumer of `dead_letter` must branch on key presence to know what kind of failure it's looking at. The queue is not a queue; it's two different diagnostic logs sharing a list.

---

## Summary Map

```
Vocabulary laundering
        │
        ▼
pub/sub names → suppresses "why does emit() return?"
        │
        ▼
context dict as universal carrier
        ├── handlers share mutable state (error pollution)
        ├── results array implies caller coupling
        └── dead letter conflates two failure modes
                │
                ▼
        "Improvement": wildcards + snapshots + stop-propagation
                ├── Makes sequential dependency a feature
                ├── Makes results semantics incoherent under fan-out
                └── Makes dead letter queue's dual purpose structural
```

The real problem isn't fixable at this level. The choice is: commit to pub/sub (remove `emit()` return value, make handlers truly independent, separate error logging from dead letter), or commit to pipeline (rename everything — `Pipeline`, `pipe()`, `step()`, `intercept()` — and own the sequential semantics). The current code is trapped between two designs, and the vocabulary is what keeps it there.
