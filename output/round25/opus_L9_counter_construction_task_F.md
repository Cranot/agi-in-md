# EventBus Structural Analysis

## Falsifiable Claim

**The deepest structural problem:** `emit()` operates on a single mutable `context` dict using two contradictory data-flow models simultaneously — *value-semantic replacement* for middleware (`context = mw(context)`) and *reference-semantic mutation* for handlers and error paths — with no boundary between them. This makes the context's lifecycle ungovernable.

---

## Three-Expert Adversarial Test

**Defender:** The shared mutable dict is passed to middleware, handlers, dead_letter, *and* returned to the caller. Five simultaneous owners, zero contracts. A handler mutating `context` corrupts the dead_letter historical record. This is the real bug.

**Attacker:** Shared mutability is a *feature* (see Express.js). The real problem is the error path: when a handler throws, the exception is caught, `context["error"]` is set, the context is pushed to `_dead_letter`, *but the loop continues*. A second throwing handler *overwrites* `context["error"]` and pushes the *same dict* to dead_letter again. The control flow after failure is broken, not just the data model.

**Prober:** Both of you assume the problem is runtime behavior. The unexamined assumption is the *ownership model*. Look at lines 14-15 vs lines 22-27:

```python
# Middleware: value semantics — replacement
context = mw(context)          # "I receive a new context"

# Handlers: reference semantics — mutation  
context["error"] = e           # "I modify THE context"
self._dead_letter.append(context)  # "I store THE context"
```

These are two incompatible protocols operating on the same object in the same function. Neither is declared.

## Transformed Claim

The deepest problem is an **unresolved ownership conflict**: `emit()` is simultaneously a *pipeline* (sequential context transformation through middleware) and a *broadcast* (parallel context distribution to handlers). These topologies have contradictory requirements for shared state, but the code uses a single mutable dict for both.

**Diagnostic gap:** My original claim saw shared mutability (a symptom). The transformed claim identifies that mutability is only dangerous *because* two incompatible ownership models coexist without either being declared.

---

## Concealment Mechanism: Protocol Mimicry

Each 3–5 line block mimics a well-known pattern:

| Lines | Mimicked Pattern | Looks Like |
|-------|-----------------|------------|
| 14–17 | Express.js middleware chain | ✅ Correct |
| 18–21 | Message broker dead letter queue | ✅ Correct |
| 22–28 | Pub/sub with error isolation | ✅ Correct |

No single block is wrong. The wrongness exists **only in their composition**. Code review passes because reviewers recognize each idiom independently.

---

## Improvement 1: Deepen the Concealment

*"Protect against middleware mutation side effects"* — passes review easily:

```python
def emit(self, event_type, payload):
    context = {"type": event_type, "payload": payload, "cancelled": False}
    for mw in self._middleware:
        context = mw(dict(context))  # ← shallow copy before each middleware
        if context.get("cancelled"):
            return dict(context)     # ← return a copy too
    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(dict(context))  # ← copy into dead letter
        return context
    # ... rest unchanged
```

This **deepens concealment** because it makes the middleware path look even more carefully value-semantic, while the handler path remains fully reference-semantic. The code now *looks more careful* while the contrast between models is actually **greater**.

### Three Properties Visible Only Because I Tried to Strengthen It

1. **Shallow copy doesn't protect nested payloads.** If `payload` is a dict, middleware and handlers still alias the inner object. The "fix" creates false isolation — real aliasing persists one level deeper, now harder to detect.

2. **The handler loop's `context["error"]` overwrite is invisible from the middleware boundary.** Copying at middleware boundaries is irrelevant because corruption happens *after* middleware — in the handler loop where errors cause the same dict to be both stored in dead_letter and returned. The fix protects the wrong boundary.

3. **`context["results"]` grows during handler iteration.** Later handlers see a context containing partial results from earlier handlers, making execution order semantically load-bearing. The priority system enables this dependency but doesn't document it. Copying at middleware boundaries makes this *less* visible, not more.

---

## Improvement 2: Contradicts Improvement 1

*"Provide a clear API contract for context manipulation"* — also passes review:

```python
class EventContext:
    __slots__ = ('type', 'payload', 'cancelled', 'error', 'results', 'meta')
    
    def __init__(self, event_type, payload):
        self.type = event_type
        self.payload = payload
        self.cancelled = False
        self.error = None
        self.results = []
        self.meta = {}

    def cancel(self):
        self.cancelled = True

def emit(self, event_type, payload):
    context = EventContext(event_type, payload)
    for mw in self._middleware:
        context = mw(context)  # middleware can return same or new context
        if context.cancelled:
            return context
    # ... handlers receive typed context with controlled mutation
```

This **contradicts Improvement 1**:

| Property | Improvement 1 (Copy) | Improvement 2 (Type) |
|----------|---------------------|---------------------|
| Philosophy | Prevent mutation via isolation | Embrace mutation via contract |
| Strengthens | Stage independence | Inter-stage communication |
| Weakens | Ability to communicate across stages | Isolation between stages |

---

## The Structural Conflict

Both improvements are independently legitimate because the EventBus **genuinely needs both properties simultaneously**:

- **As a pipeline** (middleware): context must be *transformable* — each stage produces a new or modified context for downstream consumers. This demands either replacement semantics or controlled mutation.
- **As a broadcast** (handlers): context must be *stable* — each handler should see the same input uncontaminated by other handlers' side effects. This demands either copies or immutability.

**Pipeline needs shared mutable state. Broadcast needs isolated immutable state. The EventBus is both at once.**

Any improvement that serves one topology undermines the other. The code hides this by being 30 lines long — simple enough that the contradiction between *sequential transformation* and *parallel distribution* never surfaces until you try to fix it. That is the structural conflict: it exists *only because both improvements are legitimate*, and it cannot be resolved without splitting `emit()` into two phases with an explicit boundary between the pipeline topology and the broadcast topology.
