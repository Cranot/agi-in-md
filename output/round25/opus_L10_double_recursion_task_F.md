# Structural Diagnosis: EventBus Double Recursion

## Initial Claim (Specific, Falsifiable)

> The deepest structural problem is that `context` is a single mutable dictionary simultaneously serving as input message, control flow mechanism (`cancelled`), error channel (`error`), and result accumulator (`results`). This makes reliable error recovery structurally impossible: handler 3 sees handler 2's failure in the same dict it reads its input from, and `_dead_letter` holds a reference to a context that later handlers continue mutating.

---

## Three Experts Test the Claim

**Expert A (Defends):** Correct. Watch what happens concretely:

```python
# Handler 2 throws. context["error"] = e. context pushed to dead_letter.
# Handler 3 runs. Succeeds. Overwrites context["error"]? No — but:
# The dead_letter entry is THE SAME OBJECT as the live context.
# When context["results"] is assigned at the end, the dead_letter
# entry retroactively gains a "results" key. The dead letter is alive.
```

**Expert B (Attacks):** The mutable dict is a *symptom*. The real problem is that this code has **no event model** — no event ID, no lifecycle, no immutability contract. The dict is the cheapest way to avoid designing one. Fix the dict, and you still have: no unsubscribe, O(n log n) re-sort on every `on()`, middleware that can return `None` and crash everything, and handlers that are "prioritized" but share state — meaning priority implies independence that doesn't exist.

**Expert C (Probes assumptions):** Both of you assume this *should* provide handler isolation. But the implementation — shared mutable context flowing through middleware then handlers — is exactly Express.js middleware. The name says **EventBus** but the implementation says **middleware pipeline**. The code is *neither*. That's the actual problem.

## Transformed Claim

> The deepest structural problem is **contract ambiguity between pipeline semantics and broadcast semantics**. The code cannot decide whether `emit` is a pipeline (each stage transforms shared state for the next) or a broadcast (each handler independently processes an event). This is not an implementation bug — it is an architectural identity crisis.

**The gap:** My original claim treated a design confusion as an implementation defect — which is exactly what the code itself does. The vocabulary conceals the confusion.

---

## The Concealment Mechanism

**Vocabulary borrowing.** The API uses event-bus terms (`on`, `emit`, `handler`, `event_type`) to name pipeline operations. A reader sees "event bus" and expects broadcast semantics with handler isolation. The implementation delivers pipeline semantics with shared mutation. The names prevent you from seeing what the code does.

Evidence — this looks like a publish-subscribe API:
```python
bus.on("user.created", send_email, priority=1)
bus.on("user.created", update_cache, priority=2)
bus.emit("user.created", {"id": 42})
```
But `update_cache` can corrupt the context that `send_email` depends on. Priority *implies* independence. The implementation *enforces* coupling.

---

## Improvement 1: Engineered to Deepen Concealment

This would pass code review as "adding handler isolation":

```python
def emit(self, event_type, payload):
    context = {"type": event_type, "payload": payload, "cancelled": False}
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
            handler_context = dict(context)  # ← "isolation"
            results.append(handler(handler_context))
        except Exception as e:
            error_context = dict(context)
            error_context["error"] = e
            self._dead_letter.append(error_context)
    context["results"] = results
    return context
```

**Why it deepens concealment:** The shallow copy creates the *appearance* of isolation while sharing every nested object in the payload. It also makes middleware's continued shared-mutation look *intentional* by contrast. The fix makes the design look deliberate when it isn't.

### Three Properties Visible Only Because I Tried to Strengthen the Concealment

1. **The payload is the real shared state.** `dict(context)` copies context keys, but `payload` is still the same object. The problem lives one level deeper than the context wrapper.

2. **Middleware and handlers have fundamentally different contracts.** By isolating only handlers, the improvement *makes explicit* that middleware is pipeline but handlers should be broadcast. The original hid this by treating them identically.

3. **The return value of `emit` is structurally incoherent.** The returned context contains `results` from "isolated" handler executions but the payload reflects middleware mutations. There is no coherent "result of an emission" because broadcast and pipeline produce different kinds of results.

---

## Recursive Diagnostic on Improvement 1

**What does it conceal?** That shallow copy is not isolation. `context["payload"]["user"]["name"] = "evil"` in one handler mutates it for the caller. The concealment has merely moved one level of indirection inward.

**What property of the original does it recreate?** The original's "is this shared or isolated?" question reappears as a *depth* question: how far down does isolation go? The same ambiguity, relocated.

## Improvement 2: Addressing the Recreated Property

```python
import copy

def emit(self, event_type, payload):
    context = {"type": event_type, "payload": payload, "cancelled": False}

    for mw in self._middleware:
        context = mw(context)
        if context.get("cancelled"):
            return context

    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(copy.deepcopy(context))
        return context

    results = []
    for _, handler in handlers:
        try:
            handler_context = copy.deepcopy(context)  # ← full isolation
            results.append(handler(handler_context))
        except Exception as e:
            error_context = copy.deepcopy(context)
            error_context["error"] = e
            self._dead_letter.append(error_context)

    context["results"] = results
    return context
```

## Recursive Diagnostic on Improvement 2

**What does it conceal?** Three things:
- Payloads containing file handles, connections, or locks will raise `TypeError` on deepcopy — isolation *silently excludes non-copyable state*, which is usually the state that matters most.
- Performance goes from O(1) context passing to O(n × |payload|) per emission — a cliff invisible at the API level.
- **Middleware still operates under pipeline semantics (shared mutation). Handlers now operate under broadcast semantics (full isolation). Nothing in the API tells users which contract applies to their code.** A caller of `use()` and a caller of `on()` are operating under different consistency models with no way to know.

**What property of the original does it recreate?** The dual-contract problem. The ambiguity is no longer *within* a single phase — it's now *between* phases, which is harder to see and harder to fix. The boundary moved. The ambiguity didn't.

---

## The Structural Invariant

The property that persists through every improvement, because it belongs to the problem space, not the implementation:

> **An event system must choose between "events as messages" (broadcast, isolation, fire-and-forget) and "events as state transitions" (pipeline, shared state, accumulation). Any single API that serves both use cases will reproduce their ambiguity at whatever boundary separates the two modes.**

| Version | Where the ambiguity lives |
|---|---|
| Original | Everywhere — middleware and handlers share one mutable context |
| Improvement 1 | At the copy boundary — shallow copy leaks nested state |
| Improvement 2 | Between phases — middleware is pipeline, handlers are broadcast, API doesn't distinguish |

Every fix pushes the ambiguity to a different boundary. The invariant is the ambiguity itself. It cannot be eliminated by implementation changes because it reflects an **unresolved design decision about what events are in this system**: shared state transitions, or isolated messages. The code refuses to choose, and every improvement inherits that refusal.
