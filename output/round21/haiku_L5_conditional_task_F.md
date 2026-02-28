# Structure Analysis: EventBus Implementation

## Pattern Identified
**Observer/Pub-Sub with Middleware Pipeline** — this is a hierarchical pattern with **three layers**:
1. **Middleware layer** (transformation/cancellation)
2. **Handler dispatch layer** (priority-ordered execution)  
3. **Aggregation layer** (result collection + dead-letter routing)

The problem is that layers 2 and 3 are **tangled**, not cleanly separated.

---

## Hierarchical Decomposition & Compression Bottleneck

```
emit(event_type, payload)
├─ Middleware chain (can cancel)
│  └─ BOTTLENECK: Handler execution has no equivalent control
├─ Handler dispatch (priority ordered)
│  ├─ Find handlers
│  ├─ Execute in priority order
│  └─ Collect results
└─ Aggregation
   ├─ Dead-letter (mixes 2 semantic cases)
   └─ Return context
```

**The bottleneck**: Error handling semantics are **undefined and conflated**.

---

## Critical Problems

| Issue | Severity | Why It Matters |
|-------|----------|---|
| **Unclear exception handling** | 🔴 Critical | Does one handler exception stop others? Code continues but also adds to dead-letter—is this intentional? |
| **Dead-letter semantic collapse** | 🔴 Critical | "No handlers found" and "handler crashed" both go to dead-letter. These are operationally different (no handlers = silent; crash = alert-worthy). |
| **Handler execution modifies shared context** | 🔴 Critical | If handler 1 does `context["user"] = new_user` and handler 2 reads it, you have coupling. No isolation. |
| **Priority re-sorting on every `on()` call** | 🟡 High | O(n log n) on registration; should be lazy (sort once at emit time). |
| **No unsubscribe mechanism** | 🟡 High | Memory leak risk; no way to remove handlers. |
| **Middleware can cancel; handlers cannot** | 🟡 High | Asymmetric control flow. Handler can't prevent other handlers from executing (unlike middleware). |

---

## Steelman of the Alternative Path

*What if this **is** intentionally "resilient execution"?*

If the design intent is:
- All handlers execute regardless of failures (like `Promise.allSettled`)
- Middleware acts as a gatekeeper
- Dead-letter is an observability queue for "things worth noting"

Then the current code is **directionally correct but under-specified**. It should explicitly declare this via:
```python
# self._suppress_handler_exceptions = True  # ← intention not visible
# self._dead_letter_categories = {"no_handlers": [], "error": []}  # ← unclear categorization
```

---

## The Inversion: What Property Made Me Branch?

**I branched because**: The code has a **linear loop** (`for _, handler in handlers`) with **no visible control flow** (no `return`, `break`, or re-raise after exception). This ambiguity is the crack.

**What the other branch saw**: That dead-letter is **intentional resilience infrastructure**, not a bug catch. The other design would add metrics, separate dead-letter buckets, and explicit suppression flags.

**The inverted question I should have asked first**: 

> *"Is context a mutable collaboration object, or should each handler operate on an immutable snapshot?"*

This single property choice cascades:
- **Mutable context** (current): handlers interfere; errors cascade
- **Immutable snapshots** (alternative): handlers are isolated; each has its own result envelope

Your code hints at the better model with `results.append(handler(context))`, but stores results separately while mutating context for all to see.

---

## Recommended Fixes (Priority Order)

1. **Separate dead-letter categories**:
```python
self._unhandled_events = []  # No handlers found
self._failed_handlers = []   # Handler exceptions
```

2. **Make context immutable per handler**:
```python
for _, handler in handlers:
    try:
        result = handler(context.copy())  # Snapshot isolation
        results.append({"handler": handler, "result": result})
    except Exception as e:
        self._failed_handlers.append({"handler": handler, "error": e})
```

3. **Add explicit control flow** — let handlers return a signal:
```python
class HandlerResult:
    CONTINUE, STOP, RETRY = 0, 1, 2
```

4. **Lazy priority sort**:
```python
def emit(self, event_type, payload):
    handlers = self._handlers.get(event_type, [])
    handlers.sort(key=lambda x: -x[0])  # ← once here, not on every on()
```

5. **Add unsubscribe**:
```python
def off(self, event_type, handler):
    self._handlers[event_type] = [
        (p, h) for p, h in self._handlers[event_type] if h != handler
    ]
```

The core insight: **your bottleneck isn't performance, it's semantics**. Name your invariants.
