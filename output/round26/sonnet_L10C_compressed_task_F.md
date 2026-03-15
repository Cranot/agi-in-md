## Analysis: EventBus Implementation

---

### Surface Patterns

- Priority-sorted handler chains per event type
- Cancellable middleware pipeline
- Dead-letter queue for unhandled/errored events
- Results aggregation returned from `emit`

These look like mature event system features. They are also the concealment.

---

### Falsifiable Claim: The Deepest Problem

**Claim**: `context` is a single mutable dict shared across all middleware and all handlers. Any handler that mutates it corrupts the input of every subsequent handler, and every dead-letter entry is a live reference to an object that may continue mutating after it is "recorded."

**Falsifiable in three lines:**

```python
bus = EventBus()
bus.on("x", lambda ctx: ctx["payload"].update({"injected": True}))
bus.on("x", lambda ctx: print(ctx["payload"]))  # sees the mutation
bus.emit("x", {"value": 1})
# prints: {'value': 1, 'injected': True}
```

There is a second falsifiable failure: when handler A throws, `context["error"] = e` is written, then handler B runs — against a context that now *contains a prior error as data*. Dead-letter entries point to the same object; the last error wins.

---

### The Concealment Mechanism

**Interface uniformity masquerades as pipeline isolation.**

Every participant — middleware, handler, caller — receives and returns the same `context` shape. This creates the visual grammar of a functional pipeline (input → transform → output). But the implementation is a shared mutable heap object passed by reference. The `emit` return value *looks like* a result snapshot. It is actually a pointer to the accumulated side effects of all participants. The dead-letter queue looks like a record of past events. Its entries are live references.

---

### First Improvement: Expose the Problem More Sharply

Naive fix — give each handler its own copy:

```python
def emit(self, event_type, payload):
    context = {"type": event_type, "payload": payload, "cancelled": False}

    for mw in self._middleware:
        context = mw(dict(context))          # shallow copy per middleware stage
        if context is None:
            raise TypeError("Middleware returned None")
        if context.get("cancelled"):
            return context

    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(dict(context))
        return context

    results = []
    for _, handler in handlers:
        isolated = dict(context)             # shallow copy per handler
        try:
            results.append(handler(isolated))
        except Exception as e:
            snapshot = dict(isolated)
            snapshot["error"] = e
            self._dead_letter.append(snapshot)

    context["results"] = results
    return context
```

**Diagnostic on First Improvement:**

Shallow copy solves primitive-field mutation. It *deepens* the concealment for the common case: if `payload` is a dict (almost always), handlers still mutate each other's payload internals. The improvement creates a false sense of safety — it passes a test suite that checks for top-level key mutations while remaining broken for nested ones.

A second new problem appears: handlers are now isolated from each other's *context* mutations, so `context["results"]` accumulates return values from handlers that ran against *different* inputs than the returned `context` represents. The return value is now incoherent: it shows results produced against `isolated` but reports them inside `context`.

The structural problem has not moved. It has forked.

---

### Second Improvement: Address the Fork Explicitly

Make the pipeline's stages explicit and separate the "what was dispatched" from "what each handler experienced":

```python
from copy import deepcopy

def emit(self, event_type, payload):
    base = {"type": event_type, "payload": deepcopy(payload), "cancelled": False}

    # Middleware: each stage owns its transformation
    for mw in self._middleware:
        result = mw(base)
        if not isinstance(result, dict):
            raise TypeError(f"Middleware must return dict, got {type(result)!r}")
        base = result
        if base.get("cancelled"):
            return {"dispatched": base, "handled": False, "results": [], "errors": []}

    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(deepcopy(base))
        return {"dispatched": base, "handled": False, "results": [], "errors": []}

    results, errors = [], []
    for _, handler in handlers:
        handler_view = deepcopy(base)        # each handler gets a true snapshot
        try:
            results.append({"ok": True,  "value": handler(handler_view)})
        except Exception as e:
            dead = deepcopy(handler_view)
            dead["error"] = repr(e)
            self._dead_letter.append(dead)
            results.append({"ok": False, "error": repr(e)})
            errors.append(e)

    return {"dispatched": base, "handled": True, "results": results, "errors": errors}
```

**Diagnostic on Second Improvement:**

Mutation isolation is now genuine. Dead-letter entries are stable snapshots. Error records are per-handler rather than last-write-wins.

The structural problem has regenerated in a new form:

The return value contains `dispatched` — the pre-handler context — plus a `results` list of what each isolated handler independently produced. There is **no representation of the final state** because there is no final state. Handlers were isolated; their effects did not compose. A caller who asks "what does the system believe about this event now?" cannot answer from the return value.

The cost is also now visible: `deepcopy` on every handler invocation makes emit cost O(payload_depth × handler_count). The improvement has traded hidden correctness bugs for visible performance problems — an honest trade, but not a resolution.

---

### The Structural Invariant

**Every improvement recreates the same tension because the tension is a property of the problem space, not the implementation.**

> **In any event bus where handlers are decoupled from each other, the result of event processing cannot simultaneously be (a) a coherent aggregate state and (b) a faithful record of each handler's independent experience.**

This is not fixable. It is a logical fork:

| Design choice | What you get | What you lose |
|---|---|---|
| Shared mutable context | Coherent final state; handlers compose | Handler isolation; error containment |
| Isolated context copies | Handler independence; safe error records | Coherent final state; handler composition |
| Immutable context + explicit return values | Both, locally | You've reinvented a monad / effect system |

Every implementation oscillates between these poles. Every improvement that adds isolation breaks aggregation. Every improvement that adds aggregation breaks isolation. The concealment mechanism in every version is identical: the `context` object (or its structural equivalent) presents a single unified interface that implies both properties are satisfied simultaneously, when satisfying one always degrades the other.

The invariant is: **shared-nothing execution and shared mutable state are mutually exclusive, and an event bus proposes to provide both in the same object.** The problem is not solvable at the implementation level. It requires an architectural commitment to which property is primary — typically expressed by choosing either an actor model (isolation-primary) or a transactional model (consistency-primary) — and then making the sacrifice of the other property explicit and visible in the API.
