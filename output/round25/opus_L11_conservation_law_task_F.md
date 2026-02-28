# Structural Analysis of EventBus: A Conservation Law

## Initial Claim (Specific, Falsifiable)

> **The deepest structural problem is that `emit` routes all handlers through a single mutable `context` dict, making it impossible to reason     -> Done (111s) -> 168 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/opus_L11_conservation_law_task_F.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
 problem is that **success and failure are smeared together**. When a handler throws, `context["error"]` is set and the context is appended to `_dead_letter`—but execution *continues*. The next handler runs, may succeed, and its result is appended to `results` on the *same* context that's already in the dead letter queue. There is no model of outcome.

**Prober:** You're both assuming the problem is per-emission. Look at the system level: there is no `off()`. No `once()`. No middleware removal. `_dead_letter` grows without bound. `_handlers` accumulate forever. **The real problem is that the EventBus models accumulation without release, at every level.**

### Transformed Claim

> The EventBus models accumulation without release across every axis—handlers, middleware, dead letters, and per-emission context mutations—creating a system where every operation leaves permanent, uninspectable residue.

**The diagnostic gap:** My original claim saw a per-call problem (shared mutable context). The real problem is system-wide: append-only with no lifecycle, at every level of abstraction.

---

## The Concealment Mechanism

**Familiar API shape.** The `on`/`emit`/`use` surface is so recognizable from Node's `EventEmitter`, browser `addEventListener`, etc., that reviewers pattern-match to "I know what this is" and stop. This conceals:

1. No unsubscription mechanism
2. Unbounded dead letter accumulation (data leak disguised as a feature)
3. Error handling that doesn't halt processing
4. Middleware that can *replace* context entirely (`context = mw(context)`)
5. `context["error"]` is overwritten by each subsequent failure—only the last error survives

---

## Improvement 1: Legitimate-Looking, Deepens Concealment

```python
def on(self, event_type, handler, priority=0):
    if event_type not in self._handlers:
        self._handlers[event_type] = []
    entry = (priority, handler)
    self._handlers[event_type].append(entry)
    self._handlers[event_type].sort(key=lambda x: -x[0])
    return lambda: self._handlers[event_type].remove(entry)  # "unsubscribe"
```

**This passes code review** because it addresses the most obvious gap (no unsubscribe). But it *deepens* concealment:

- `list.remove()` uses equality matching—lambdas and closures don't compare equal, so unsubscription silently fails or raises `ValueError`
- The returned closure holds a reference to the handler list, preventing GC
- Middleware *still* has no removal mechanism, but now reviewers think lifecycle is handled
- The dead letter queue still grows forever, but attention is drawn away from it

### Three Properties Visible Only Because I Tried to Strengthen

1. **Handler identity is unmodeled.** You can't remove what you can't identify. `(priority, handler)` tuples have no stable identity.
2. **Asymmetric lifecycle.** Adding `off` for handlers but not middleware reveals an unmodeled distinction the code treats as identical (both are just lists of callables).
3. **Dead letter is a data leak, not a feature.** Nothing reads, processes, or bounds it. Logging around it only makes the leak look intentional.

---

## Recursive Diagnostic on Improvement 1

**What does it conceal?** That subscription identity requires a token/handle model, not value equality. That the unsubscribe closure is *itself* a form of unbounded accumulation (leaked references).

**What property of the original does it recreate?** The fix is append-only too. Closures capture handler lists, preventing GC. The system's fundamental character—accumulation without release—reasserted itself *through the fix*.

---

## Improvement 2: Address the Recreated Property

```python
class Subscription:
    __slots__ = ('id', 'event_type', 'priority', 'handler', 'active')
    def __init__(self, event_type, priority, handler):
        self.id = uuid.uuid4()
        self.event_type = event_type
        self.priority = priority
        self.handler = handler
        self.active = True
    def cancel(self):
        self.active = False

class EventBus:
    def __init__(self, dead_letter_limit=1000):
        self._subs = {}
        self._middleware = []
        self._dead_letter = collections.deque(maxlen=dead_letter_limit)

    def on(self, event_type, handler, priority=0):
        sub = Subscription(event_type, priority, handler)
        self._subs.setdefault(event_type, []).append(sub)
        self._subs[event_type].sort(key=lambda s: -s.priority)
        return sub

    def off(self, sub):
        self._subs[sub.event_type] = [
            s for s in self._subs.get(sub.event_type, []) if s.id != sub.id
        ]

    def emit(self, event_type, payload):
        context = {"type": event_type, "payload": payload}
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context
        active = [s for s in self._subs.get(event_type, []) if s.active]
        if not active:
            self._dead_letter.append(context)
            return context
        results, errors = [], []
        for s in active:
            try:
                results.append(s.handler(context))
            except Exception as e:
                errors.append({"subscription": s.id, "error": e})
        context["results"] = results
        context["errors"] = errors
        return context
```

### Recursive Diagnostic on Improvement 2

**What does it conceal?** The context dict is *still shared and mutable* across all handlers. Now it's *more* concealed because everything around it (identity, lifecycle, error separation, bounded queues) looks well-structured. The well-engineered frame makes the shared-mutation core harder to question.

**What property does it recreate?** Handler N still sees handler N-1's mutations to `context["payload"]`. Despite proper identity, bounded queues, and error separation, **implicit ordering dependencies through shared mutable state** are untouched. The core problem survived two rounds of improvement.

---

## The Structural Invariant

> **Broadcast dispatch and shared context are in tension.** A system that dispatches to multiple handlers through shared state must choose: **(a)** allow handlers to affect each other through mutation (implicit ordering dependencies), or **(b)** copy context per handler (lose the ability for handlers to communicate through the event system).

This is a property of the *problem space*, not the implementation. It persists through every improvement because no refactoring can eliminate a choice the domain forces.

---

## Inversion: Make the Impossible Trivially Satisfiable

Design where handlers are fully isolated AND can coordinate:

```python
def emit(self, event_type, payload):
    frozen = types.MappingProxyType({"type": event_type, "payload": payload})
    for sub in self._subs.get(event_type, []):
        result = sub.handler(frozen)           # isolation: immutable input
        if result and "emit" in result:
            self.emit(result["emit"], result["payload"])  # coordination: re-emission
```

**The new impossibility:** Handlers are isolated (frozen context) and can coordinate (derived events)—but **event processing may not terminate**. Handler for A emits B; handler for B emits A. We've traded *spatial coupling* (shared mutable state) for *temporal coupling* (unbounded causal chains).

---

## The Conservation Law

$$\text{Handler Independence} \times \text{Causal Boundedness} \leq k$$

| Design | Independence | Boundedness |
|---|---|---|
| **Original** (shared mutable context) | Low — handlers coupled through mutation | High — single linear pass, always terminates |
| **Inverted** (frozen context + re-emission) | High — handlers see immutable snapshots | Low — re-emission chains may diverge |

**The finding:** You cannot increase both simultaneously. The shared mutable context in the original is not a bug—it is the *price paid* for guaranteed termination and linear execution. Every fix that eliminates mutation reintroduces the cost as potential non-termination, and every fix that guarantees termination reintroduces shared state as the coordination channel.

The EventBus doesn't have an implementation problem. It has a **conservation law**: in broadcast-dispatch systems, handler isolation and causal boundedness are conjugate properties. Improving one necessarily degrades the other. The only design choice is *where the cost appears*.
