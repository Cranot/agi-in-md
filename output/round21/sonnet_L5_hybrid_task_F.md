## Pattern Identification

This instantiates **Mediator + Observer + Chain of Responsibility + Dead Letter Channel** — a synchronous event bus combining four Enterprise Integration Patterns. The specific properties that drive the analysis are:

1. **Shared mutable context dict** passed through a pipeline
2. **Two failure modes conflated** into one dead letter queue
3. **Reference aliasing**: context appended to dead letter before mutation is complete

---

## Deriving Three Analytical Operations

From *these specific properties*, the useful operations are:

| Operation | Derived From |
|---|---|
| **A. State Mutation Trace** | Mutable context dict shared across middleware, handlers, and dead letter |
| **B. Failure Mode Taxonomy** | Two semantically different error paths collapsed into one queue |
| **C. Contract Violation Analysis** | Gaps between what the API promises and what the implementation delivers |

**Prediction**: Operation A (State Mutation Trace) will yield deepest insight. The central structural risk is reference aliasing — the same dict object being stored and then mutated — which produces bugs that are invisible at the call site and corrupt diagnostic data silently.

---

## Execution

### Operation A: State Mutation Trace

Tracing every mutation of shared state and when it happens:

```python
# Mutation 1: on() — sort on every registration, not insert
self._handlers[event_type].sort(key=lambda x: -x[0])
# O(n log n) per call. Use bisect.insort for O(n) with O(log n) search.

# Mutation 2 (CRITICAL): dead_letter stores reference BEFORE context is fully built
context["error"] = e
self._dead_letter.append(context)      # ← reference stored here
# ... execution continues ...
context["results"] = results           # ← MUTATES the dict already in dead_letter
```

**The aliasing bug**: Every dead letter entry is a live reference to the same dict. The dict gets mutated after storage, so dead letter entries reflect *final* state, not *failure* state. You cannot reconstruct what the context looked like when failure occurred.

**The multi-error corruption**:
```python
# If handler_1 and handler_2 both raise:
context["error"] = e1
self._dead_letter.append(context)   # entry 1 → same dict
context["error"] = e2               # overwrites e1 in BOTH entries
self._dead_letter.append(context)   # entry 2 → same dict

# dead_letter now has: [context, context]
# Both entries only show e2. e1 is gone forever.
```

**The middleware None trap**:
```python
def logging_middleware(ctx):
    ctx["logged"] = True
    # forgot: return ctx

bus.use(logging_middleware)
bus.emit("order.placed", data)
# → context = None → AttributeError: 'NoneType' object has no attribute 'get'
```

**Concurrent modification during iteration**:
```python
handlers = self._handlers.get(event_type, [])  # reference to the live list
for _, handler in handlers:
    handler(context)  # if handler calls bus.on(event_type, ...), the list
                      # is sorted mid-iteration → undefined skip/repeat behavior
```

---

### Operation B: Failure Mode Taxonomy

Two structurally different failures collapse into `_dead_letter`:

```
"No handlers registered"  →  architectural gap (routing problem)
"Handler raised exception" →  runtime error (execution problem)
```

These require different recovery strategies. Mixing them means you cannot write a general dead letter processor — you must inspect each entry to determine what kind of failure it represents, and there's no field marking which case applies.

**Results misalignment** — callers cannot correlate results to handlers:
```python
# 3 handlers registered; handler_2 raises
results = [result_1, result_3]   # length 2, no gap marker
# Which result belongs to which handler? Unknowable.
```

**Error suppression is invisible**:
```python
context["results"] = results  # caller sees results; no signal that errors occurred
return context
# Caller must know to check context.get("error"), which may be e2 not e1
```

**Failure mode matrix**:

| Scenario | What caller sees | What's lost |
|---|---|---|
| No handlers | `context` with no results key | Dead letter has correct snapshot |
| 1 handler raises | `context["error"] = e`, results=[] | Error stored, but context mutated after |
| 2+ handlers raise | `context["error"] = last_e` | All prior errors destroyed |
| Middleware raises | Exception propagates | Dead letter never updated |
| Middleware returns None | `AttributeError` | Full pipeline lost |

---

### Operation C: Contract Violation Analysis

**Priority ordering is not preserved under mutation**:
```python
bus.on("click", fast_handler, priority=10)
bus.on("click", slow_handler, priority=1)
bus.on("click", medium_handler, priority=5)  # triggers sort: correct order
# BUT: if fast_handler calls bus.on("click", new_handler) during emit(),
# sort fires mid-iteration on the live list
```

**Handler isolation is illusory**:
```python
def handler_a(ctx):
    ctx["payload"]["user"] = "modified"  # mutates shared payload

def handler_b(ctx):
    print(ctx["payload"]["user"])  # sees handler_a's modification
```

Handlers appear independent but share a mutable context. There's no copy or freeze boundary.

**Cancellation is asymmetric**:
- Middleware CAN cancel subsequent middleware via `context["cancelled"]`
- Handlers CANNOT cancel subsequent handlers — no equivalent mechanism
- A handler that wants to stop propagation has no API for it

**Dead letter is diagnostic but unreliable**:
The dead letter queue promises post-mortem inspection, but the aliasing bug means the stored contexts reflect *post-processing* state, not failure state.

---

## Inversion: Was the Prediction Right?

**Partially wrong.** I predicted Operation A would dominate. It did surface the most critical bugs (aliasing, multi-error corruption). But the gap is revealing:

**What I underweighted**: Operation B's failure mode taxonomy identified the *architectural* conflation — two different failure semantics in one queue — which is not visible from mutation tracing alone. The aliasing bug is a consequence of bad implementation; the dead-letter conflation is a consequence of bad design. They operate at different abstraction levels.

**The blind spot this reveals**: I was primed to look for *execution-time* bugs (what goes wrong when code runs) rather than *semantic-level* bugs (what the API is trying to mean vs. what it actually means). The mutation trace is mechanistic; the contract analysis is conceptual. My prediction weighted the mechanistic over the conceptual — which is a common bias when reading code rather than reading specifications.

---

## Corrected Implementation (Key Fixes)

```python
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
import bisect

@dataclass
class EventContext:
    type: str
    payload: Any                          # consider deep-copying at emit boundary
    cancelled: bool = False
    results: list = field(default_factory=list)
    errors: list = field(default_factory=list)  # list, not single value

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list] = {}
        self._middleware: list[Callable] = []
        self._unhandled: list[EventContext] = []   # "no handlers" case
        self._errors: list[tuple] = []             # "handler raised" case
        self._lock = threading.RLock()             # reentrant: handlers may call on()

    def on(self, event_type: str, handler: Callable, priority: int = 0):
        with self._lock:
            handlers = self._handlers.setdefault(event_type, [])
            # bisect for O(log n) insertion into sorted list
            bisect.insort(handlers, (-priority, id(handler), handler))

    def emit(self, event_type: str, payload: Any) -> EventContext:
        ctx = EventContext(type=event_type, payload=payload)
        
        for mw in self._middleware:
            result = mw(ctx)
            if result is None:
                raise ValueError(f"Middleware {mw} must return context")
            ctx = result
            if ctx.cancelled:
                return ctx

        with self._lock:
            handlers = list(self._handlers.get(event_type, []))  # snapshot

        if not handlers:
            self._unhandled.append(ctx)          # separate queue, clean semantics
            return ctx

        for _, _, handler in handlers:
            try:
                ctx.results.append(handler(ctx))
            except Exception as e:
                ctx.errors.append((handler, e))  # preserve all errors, with source

        if ctx.errors:
            self._errors.append(ctx)             # snapshot AFTER full execution

        return ctx
```

**Key changes**:
- `_dead_letter` split into `_unhandled` and `_errors` with distinct semantics
- Context appended to error queue *after* full execution (no aliasing bug)
- `errors` is a list preserving all failures with their source handler
- `RLock` for thread safety including reentrant handler→on() calls
- Middleware None return raises explicitly rather than failing opaquely
- Handler list snapshot before iteration prevents mid-iteration mutation
