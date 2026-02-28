# Three Experts Analyze an EventBus

---

## Expert 1 — The Architect: *"This is a coherent, well-structured design"*

The code implements three distinct, composable patterns that fit together correctly:

**The middleware pipeline** (borrowed from Express/Koa) is genuinely excellent for cross-cutting concerns:
```python
# Logging, auth, validation — all composable without touching core logic
bus.use(lambda ctx: {**ctx, "timestamp": time.time()})
bus.use(lambda ctx: {**ctx, "cancelled": True} if not is_authorized(ctx) else ctx)
```

**Priority-ordered handlers** solve a real coordination problem — you actually need this when multiple subsystems respond to the same event with ordering dependencies.

**Exception isolation** is the right default. One broken handler shouldn't cascade:
```python
try:
    results.append(handler(context))
except Exception as e:
    # Correct: other handlers still run
```

**The dead letter queue** shows genuine operational thinking — unhandled events are observable rather than silently dropped. This is the difference between a system you can debug and one you can't.

*To Expert 2:* Most of your "failure modes" are missing features, not design flaws. Thread safety is an infrastructure concern. No unsubscribe is a missing method. These don't invalidate the architecture.

---

## Expert 2 — The Risk Analyst: *"This has five genuine defects, not missing features"*

These aren't omissions — they're active hazards embedded in what's already written:

**Defect 1: Middleware with no return crashes everything**
```python
def bad_middleware(ctx):
    log(ctx)  # forgot to return ctx

context = mw(context)  # context is now None
if context.get("cancelled"):  # AttributeError: 'NoneType'
```
No guard, no contract — one middleware kills the bus silently.

**Defect 2: The dead letter queue accumulates per-error, not per-event**
```python
for _, handler in handlers:
    try:
        results.append(handler(context))
    except Exception as e:
        context["error"] = e
        self._dead_letter.append(context)  # same event, N times
```
If 5 handlers fail, the same event appears 5 times in dead letter — with only the *last* error recorded (each overwrites `context["error"]`). The queue is both lossy and duplicative simultaneously.

**Defect 3: Mutable shared context enables handler interference**
```python
def handler_a(ctx):
    ctx["payload"]["user"] = None  # mutates shared state
    
def handler_b(ctx):
    print(ctx["payload"]["user"].name)  # AttributeError from handler_a's side-effect
```
Handlers are supposed to be independent; this makes them secretly coupled.

**Defect 4: `_dead_letter` is an unbounded memory leak**
No eviction, no max size, no TTL. Long-running processes accumulate indefinitely.

**Defect 5: Middleware cancellation is only checked between middleware steps**
```python
for mw in self._middleware:
    context = mw(context)
    if context.get("cancelled"):
        return context  # ✓ checked here

for _, handler in handlers:
    # ❌ never checked — handlers can't cancel each other
    results.append(handler(context))
```

*To Expert 1:* "Observable rather than silently dropped" doesn't apply when your observability mechanism is itself broken. A dead letter queue that duplicates entries and loses errors is worse than a log statement.

---

## Expert 3 — The Systems Thinker: *"Both of you are arguing about the surface while the structural contradiction goes unexamined"*

Expert 1 sees elegant patterns. Expert 2 sees implementation bugs. Neither is asking: **what model of reality does this code encode, and is that model coherent?**

**The `context` dict is doing three incompatible jobs:**
```python
context = {
    "type": event_type,     # routing identity — what IS this event
    "payload": payload,      # domain data — what the event CARRIES
    "cancelled": False,      # execution state — how processing IS GOING
    "error": e,              # execution record — what HAS HAPPENED
    "results": results,      # execution record — what HAS HAPPENED
}
```

This collapses the *event* with the *execution trace of handling it*. The consequence: the context you pass *into* the system is not the context you get *out* — but there's no type or contract expressing this transformation. Handlers receive a mutable record of their own execution as it happens. This is what makes Expert 2's interference bug not just possible but structurally inevitable.

**The `_dead_letter` queue is a hidden secondary state machine.** It's not observability infrastructure — it's a place where the system silently shifts to a different mode. Errors and unhandled events go into the same bucket. You cannot distinguish "no handler registered" from "handler crashed" from the outside.

**The deeper question both experts miss:** Is this an event system for *notification* (fire-and-forget), *coordination* (handlers affect each other), or *command routing* (one canonical response)? The code tries to be all three:
- `results` array implies coordination/aggregation
- `cancelled` flag implies command routing
- `dead_letter` implies notification durability

These have mutually exclusive contracts. A notification bus shouldn't have priority ordering. A command router shouldn't silently continue after failure.

*To Expert 1:* The patterns are real, but they don't fit together — they each imply different semantics. *To Expert 2:* Your bugs aren't independent — they're symptoms of the context conflation problem. Fix the model, and most bugs become impossible.

---

## What the Argument Itself Reveals

The three-way dispute maps onto something the code itself is enacting: **the confusion between a prototype and a contract.**

Every feature in this class — middleware, priority, dead letter, cancellation, results collection — is a production-grade concern. But none of them have production-grade *guarantees*. There is no:
- Contract on what middleware must return
- Defined lifecycle for handlers (subscribe → active → unsubscribe)
- Separation between "this event happened" (immutable) and "this is how we processed it" (mutable record)
- Clear answer to: *who owns the context object?*

Expert 1 sees the features and reads "production-ready." Expert 2 sees the missing guarantees and reads "broken." Expert 3 sees that both readings are correct simultaneously — this is what prototype code that has acquired production features *looks like*. It has grown past its original assumptions without those assumptions ever being made explicit.

The argument reveals a threshold problem: **this code is exactly at the complexity point where implicit contracts must become explicit ones.** The next correct step isn't fixing the bugs (Expert 2's agenda) or defending the patterns (Expert 1's agenda) — it's deciding what this system *is*, and encoding that as structure:

```python
@dataclass(frozen=True)
class Event:
    """Immutable. The thing that happened."""
    type: str
    payload: Any
    id: str = field(default_factory=uuid4)

@dataclass  
class ExecutionContext:
    """Mutable. The record of handling it."""
    event: Event
    cancelled: bool = False
    errors: list[Exception] = field(default_factory=list)
    results: list[Any] = field(default_factory=list)
```

That separation — event vs. execution context — dissolves Expert 2's interference bug, clarifies Expert 3's model problem, and makes Expert 1's patterns actually composable. The debate points directly at the fix: **give the system a stable ontology, and the implementation follows.**
patterns from larger systems)
- **Fails at scale** along exactly the axes the patterns were designed to address

The argument between the experts is actually the argument *future developers will have* when this code breaks — and they'll have it without a map, because the code's vocabulary pointed them toward distributed-systems debugging when the actual failure is a Python dict mutation or a missing `return` statement.

The code doesn't need more features. It needs **a stated contract**:

```python
class EventBus:
    """
    Synchronous, single-threaded event dispatcher.
    - Handlers execute in priority order, blocking the caller.
    - Context dict is SHARED and MUTABLE across handlers (by design).
    - Dead-letter is bounded to MAX_DEAD_LETTER entries.
    - No async support. No thread safety.
    """
```

Once you write that docstring, every expert's critique becomes actionable rather than structural. Without it, they're all right — and nothing gets fixed.

---

## Concrete Fix Surface (What All Three Experts Agree On)

| Issue | Severity | Fix |
|---|---|---|
| Middleware can return `None` | **Critical** | Validate return; raise `TypeError` if not dict |
| Error overwrites error | **High** | Use `context["errors"] = []` and append |
| Dead-letter unbounded | **High** | `maxlen=` via `collections.deque` |
| No unsubscribe | **High** | Return handler ID from `on()`; add `off(id)` |
| Mutable shared context | **Medium** | Deep-copy context per handler, or document the contract |
| Thread safety | **Medium** | `threading.RLock` around mutations |
| No async support | **Low→High** (depends on use) | Separate `AsyncEventBus` class |
| Caller receives handler results | **Design** | Consider fire-and-forget; drop return value |
