## Pattern Recognition

This is a **Pub/Sub Mediator with middleware chain** — a hybrid of Observer, Chain of Responsibility, and Dead Letter Queue patterns. Its defining structural property is that a **single mutable `context` dict flows through the entire pipeline** (middleware → handlers → dead letter). That property generates the three most revealing analyses:

---

## 1. Mutation Flow Tracing (Concrete)

The `context` dict is created once and shared everywhere. This is the root of most bugs.

```python
# BUG: Shared mutable context across handlers
for _, handler in handlers:
    try:
        results.append(handler(context))  # handler 1 can mutate context["payload"]
    except Exception as e:                # and handler 2 sees the mutation
        context["error"] = e              # ← overwrites previous error!
        self._dead_letter.append(context) # ← appends a REFERENCE, not a copy
```

**Three concrete mutations bugs:**

| Bug | Consequence |
|-----|-------------|
| Multiple handlers share one `context` | Handler 1 mutates `payload`, handler 2 sees corrupted data |
| `context["error"] = e` in a loop | Only the *last* exception survives; earlier ones are silently overwritten |
| `_dead_letter.append(context)` stores a reference | Later mutations (adding `results`, overwriting `error`) retroactively corrupt dead letter entries |

```python
# BUG: Middleware can silently destroy the pipeline
for mw in self._middleware:
    context = mw(context)          # if mw forgets to return → context = None
    if context.get("cancelled"):   # → AttributeError, not a useful diagnostic
```

If any middleware returns `None` (a common mistake — forgetting `return context`), the entire bus crashes with an inscrutable `AttributeError`.

---

## 2. Contract Analysis (Structural)

The implicit contracts between components are underspecified in ways that compound:

**Middleware contract is ambiguous:**
```python
# Are these equivalent? The code treats them as different.
def middleware_a(ctx):
    ctx["timestamp"] = now()
    return ctx              # mutate-and-return: works

def middleware_b(ctx):
    ctx["timestamp"] = now()
                            # mutate-and-forget: pipeline dies
```

**Dead letter conflates two failure semantics:**
```python
if not handlers:
    self._dead_letter.append(context)   # "no one was listening"
    # ...
except Exception as e:
    self._dead_letter.append(context)   # "someone listened and failed"
```

These are categorically different failures (routing failure vs. processing failure) dumped into one undifferentiated queue.

**No deregistration contract:** There's `on()` but no `off()`. Handlers (and any objects they close over) accumulate forever — a structural memory leak.

---

## 3. Emergent Failure Modes (Systemic)

Zooming out to how this behaves in a real system:

**Re-entrancy is unguarded.** If a handler calls `self.bus.emit(...)`, you get recursive emission. The outer `emit`'s `for _, handler in handlers` loop continues with a `context` that may have been mutated by the inner emission's middleware chain. Nothing prevents or detects this.

**Unbounded memory growth.** `_dead_letter` grows without limit. No eviction, no cap, no drain mechanism. In a long-running process, this is a slow leak.

**Thread unsafety.** All shared state (`_handlers`, `_middleware`, `_dead_letter`) is unprotected. Concurrent `on()` + `emit()` causes races on the handler list — especially because `on()` re-sorts in place.

**Performance.** `on()` does a full `O(n log n)` re-sort on every registration. This should be an insertion into an already-sorted list (`bisect.insort`).

---

## Summary of Recommended Fixes

```python
# 1. Copy context per-handler to prevent cross-contamination
# 2. Accumulate errors as a list, not a single overwritten key
# 3. Enforce middleware return contract (or use in-place-only mutation)
# 4. Separate dead_letter into unhandled_events / handler_errors
# 5. Add off() / once() for handler lifecycle management
# 6. Guard against re-entrant emit (or make it explicit)
# 7. Deep-copy or snapshot context before appending to dead_letter
```

---

## Inversion: What Can't This Frame See?

My frame was **static single-component structural analysis**. What it *cannot* generate is **runtime interaction topology** — specifically, what happens when multiple `EventBus` instances exist in a system, or when the *graph of events triggering events* creates cycles, cascades, or ordering dependencies. That requires dynamic tracing or formal modeling (e.g., event dependency graphs), not code reading. The re-entrancy issue above is the boundary where my frame starts to fail — I can *name* it, but I can't fully characterize its consequences without knowing the call graph of the system it's embedded in.
