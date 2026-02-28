## Pattern Identification

This instantiates **Decorated Observer with Convergent Mutable State** — a pub/sub registry (Observer) gated by a transformation pipeline (Chain of Responsibility), where a single shared context object is the convergence point for all stages. That shared-state convergence is the structural fact that determines which analyses matter most.

---

## Analytical Operations (Derived from Structure, Not Menu)

### Operation 1 — Mutation Ownership Tracing
*Because a single dict is the only communication channel through every stage, trace who owns it and when.*

```
emit() creates context
    │
    ▼
middleware_1(context) → returns new/mutated context  ← no schema contract
    │
middleware_2(context) → ...                          ← can silently DROP prior keys
    │
    ▼
handlers[0](context) → mutates freely               ← handler 1 can poison handler 2's input
handlers[1](context) → sees handler 1's mutations   ← hidden coupling channel
    │
    ▼
context["results"] = results
context["error"] = e  (overwrites — only LAST error survives)
```

**Concrete bugs from this:**

```python
# Bug 1: Middleware can return None, exploding the next .get()
def bad_middleware(ctx):
    if should_cancel(ctx):
        return None  # next line: None.get("cancelled") → AttributeError

# Bug 2: Handler mutations bleed into subsequent handlers
def handler_a(ctx):
    ctx["payload"] = transform(ctx["payload"])  # handler_b now sees transformed payload

# Bug 3: Only the last exception is recorded
for _, handler in handlers:
    try:
        results.append(handler(context))
    except Exception as e:
        context["error"] = e          # ← previous error destroyed
        self._dead_letter.append(context)
```

---

### Operation 2 — Error Propagation Topology
*Because there are three distinct exit paths and a dead letter queue, map exactly where failures go and what state they carry.*

```
                    emit()
                      │
          ┌───────────┴───────────┐
     middleware            [uncaught - crashes]
     cancels               no dead letter capture
          │
     no handlers
          │
    dead_letter.append(context)    ← snapshot or live reference?
          │
     handlers run
          │
    exception in handler_N
          │
    context["error"] = e           ← previous errors lost
    dead_letter.append(context)    ← SAME dict object, still mutating
          │
    context["results"] = results   ← dead letter entry NOW ALSO has results
                                      because it holds a reference, not a copy
```

**The dead letter reference problem:**

```python
# What you think is in dead_letter:
{"type": "X", "payload": ..., "error": RuntimeError(...)}

# What's actually there after emit() completes:
{"type": "X", "payload": ..., "error": RuntimeError(...), "results": [...]}
# Dead letter is a live reference — it gets post-hoc mutations silently
```

**Middleware exceptions are completely uncaptured:**

```python
def emit(self, event_type, payload):
    for mw in self._middleware:
        context = mw(context)   # if mw() raises → no dead letter, full crash
```

---

### Operation 3 — Ordering Invariant Analysis
*Because priority, middleware sequence, and handler sequence all compose, determine which ordering guarantees actually hold and where they collapse.*

| Guarantee | Holds? | Condition |
|---|---|---|
| Higher priority → earlier execution | ✓ | Stable sort on `-priority` |
| Equal priority → insertion order | ✓ | Python sort is stable |
| Middleware runs before handlers | ✓ | Unconditional |
| Sort is deferred until needed | ✗ | Sorts on every `on()` call — O(n log n) per registration |
| Handler sees original payload | ✗ | Any prior handler can mutate context |
| Priority isolates handler behavior | ✗ | High-priority handler can corrupt low-priority handler's input via shared context |

**The priority/isolation contradiction:**

```python
# Priority implies: "handler_A is more important, runs first"
# But the actual effect is: "handler_A has write access to handler_B's input"
# Priority becomes an implicit data-dependency ordering, not just execution ordering

bus.on("order.placed", validate_inventory, priority=10)   # runs first
bus.on("order.placed", charge_payment,     priority=5)    # sees validate_inventory's mutations

# If validate_inventory does ctx["payload"]["validated"] = True,
# charge_payment silently depends on that — coupling through priority, not interface
```

---

## Inversion: The Missing Operation

The three operations above are all **synchronous structural analysis** — they ask "what does this object do, in sequence, to shared state?" They cannot generate **temporal consistency analysis**: what happens across a *sequence of emissions over time*.

Specifically, this frame has no way to answer:

- **Re-entrant emission**: A handler calls `bus.emit()` — the `_handlers` dict is read mid-iteration with no guard. Python dicts are not re-entrancy-safe when being modified concurrently.
- **Registration-after-dead-letter**: Events dead-lettered before a handler is registered are never replayed. The bus has no replay semantics and no way to derive them from its current structure.
- **Handler deregistration**: `on()` exists but `off()` doesn't. There's no removal path, so priority-sorted lists grow monotonically and handlers can't be scoped to a lifetime.

The operation you'd need is **lifecycle/session modeling** — treating the bus not as a structure but as a *stateful actor over time*, tracking how its registry evolves relative to its emission history. That's a fundamentally different frame: not "what flows through the graph" but "how the graph changes between flows."

---

## Summary of Critical Fixes

```python
# 1. Snapshot context per-handler to prevent bleed
handler_ctx = {**context}  # shallow copy minimum; deep copy for nested payloads

# 2. Accumulate errors, don't overwrite
context.setdefault("errors", []).append(e)

# 3. Snapshot context before dead-lettering
self._dead_letter.append(dict(context))  # not the live reference

# 4. Guard middleware return type
result = mw(context)
if not isinstance(result, dict):
    raise TypeError(f"Middleware must return dict, got {type(result)}")
context = result

# 5. Catch middleware exceptions
try:
    context = mw(context)
except Exception as e:
    context["error"] = e
    self._dead_letter.append(dict(context))
    return context
```
