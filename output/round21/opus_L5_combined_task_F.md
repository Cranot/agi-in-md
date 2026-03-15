# EventBus Analysis: Three-Expert Perspectival Breakdown

## Prediction

**Expert C** (the one who sees what both miss) will surface the deepest insight. My bet: the most consequential problem isn't any single bug — it's that the `context` dict serves as event envelope, middleware state, cancellation flag, error container, *and* results accumulator simultaneously. This shared-mutable-everything architecture makes the system's behavior increasingly unpredictable as it scales, and that structural flaw generates most of the specific bugs the failure-mode expert will find.

---

## Expert A — The Advocate (Strengths)

This is a surprisingly well-considered design for its size. Several real patterns are at work:

**Middleware pipeline.** The `use()`/`emit()` chain mirrors Express.js-style middleware. Each middleware transforms context, and any can cancel propagation — giving cross-cutting concerns (auth, logging, validation) a clean injection point.

**Priority-ordered handlers.** The `on()` method with `priority` and descending sort means critical handlers fire first. This is a pattern you'd find in WordPress hooks or Android BroadcastReceivers.

**Dead letter queue.** Events with no handlers aren't silently dropped — they're captured. This is straight from enterprise messaging (RabbitMQ, Azure Service Bus) and is essential for debugging event-driven systems.

**Cancellable events.** Middleware returning `cancelled: True` short-circuits, analogous to DOM `event.preventDefault()`. This enables gating patterns (rate limiting, circuit breakers).

**Clean return semantics.** `emit()` returns the context with accumulated results — the caller can inspect what happened synchronously.

---

## Expert B — The Adversary (Failure Modes)

Expert A is describing *intentions*. I'll describe *what actually happens.*

### 1. The Shared Mutable Context Is a Landmine

```python
# Middleware 1 does this:
def mw1(ctx):
    ctx["payload"]["user"] = "injected"  # mutates original payload
    return ctx

# Handler 1 does this:
def h1(ctx):
    ctx["cancelled"] = True  # doesn't stop remaining handlers!
    # (cancellation only works in middleware loop)
```

Every middleware and handler receives **the same dict**. Mutations propagate invisibly. There's no copying, no freezing, no isolation.

### 2. Error Handling Is Actively Broken

```python
except Exception as e:
    context["error"] = e                    # overwrites previous errors!
    self._dead_letter.append(context)       # appends same dict each time
```

Three problems in two lines:
- If handlers 2 and 3 both fail, only handler 3's error survives in `context["error"]`
- The *same mutable context reference* is appended to `_dead_letter` multiple times — later mutations retroactively change what's "in" the dead letter queue
- **Execution continues** after an error. Handler 3 runs even if handler 2 exploded. Is that intentional? Nothing in the API communicates this.

### 3. Middleware Can Crash the Bus

```python
context = mw(context)      # if mw returns None...
if context.get("cancelled"):  # AttributeError: 'NoneType' has no attribute 'get'
```

No validation on middleware return value. A single `None` return kills every subsequent `emit()` call.

### 4. Unbounded Memory Growth

```python
self._dead_letter.append(context)  # never evicted, never consumed
```

No size cap, no TTL, no drain method. In a long-running service, this is a memory leak by design.

### 5. No Unsubscribe

There's `on()` but no `off()`. Handlers are registered forever. Objects referenced in closures can never be garbage collected.

### 6. O(n log n) on Every Registration

```python
self._handlers[event_type].sort(key=lambda x: -x[0])
```

Sorting the full list on *every* `on()` call. Should use `bisect.insort` for O(n) insertion into a sorted list.

### 7. Not Thread-Safe

Concurrent `emit()` and `on()` calls can corrupt `_handlers` during iteration. No locks, no atomic operations.

---

## Expert C — The Structural Thinker (What Both Miss)

Expert A sees good patterns. Expert B sees bugs. **I see a category error baked into the data model.**

### The `context` Dict Is Doing Five Jobs

| Role | Evidence |
|---|---|
| Event envelope | `type`, `payload` |
| Middleware state | mutated and returned by each `mw()` |
| Control flow signal | `cancelled` |
| Error container | `error` |
| Result accumulator | `results` |

This isn't a "mutable state" problem that Expert B identified — it's a **responsibility collapse**. The `context` dict is the *only* coordination mechanism in the entire system. Every concern writes to and reads from the same untyped namespace.

This means:
- **You cannot reason about event identity.** Is the context after middleware the "same event"? After handler mutation? There's no immutable event — just a dict that everyone touches.
- **You cannot distinguish failure types.** Dead letter captures both "no handlers exist" (a routing problem) and "a handler threw" (a runtime problem). These demand fundamentally different responses — retry vs. alert vs. add a handler — but they're mixed in one list.
- **You cannot add post-handler middleware.** The middleware pipeline is linear — fire-and-forget before handlers. There's no Koa-style "onion" where middleware wraps execution. Want to measure handler duration? Log results? You can't — middleware runs *only* before handlers.

### What This Actually Needs Is Separation

```
Event (immutable)  →  Pipeline Context (per-emit, scoped)  →  Results (returned)
                       ↕
                   Error Channel (separate from dead letter)
                       ↕  
                   Dead Letter (unroutable events only)
```

Expert B would fix bugs. **The real fix is making these five roles into distinct objects** so the system can be reasoned about compositionally.

### The Hidden Coupling Problem

Here's something neither expert mentioned: **the priority sort creates implicit dependencies without making them visible.** When handler A at priority 10 mutates context and handler B at priority 5 reads it, you have *de facto coupling* between A and B — but nothing in the code expresses or enforces that. Reorder priorities and the system silently breaks. This is the event-bus version of "spooky action at a distance."

---

## Was My Prediction Right?

**Yes, but incompletely.** I predicted Expert C would identify the shared-mutable-context-as-everything problem, and they did — framing it as a responsibility collapse rather than a bug. But Expert C also surfaced something I didn't predict: the **implicit coupling through priority ordering** combined with context mutation. That's the real sleeper issue, because it means the system's correctness depends on handler registration *order*, which is invisible at any single call site.

## What the Argument Made Visible

The gap between Expert B and Expert C reveals a recurring pattern in code review: **bug-finding and architecture-finding are different activities that feel the same.** Expert B's fixes (copy context, cap the dead letter queue, validate middleware returns) would make the code *safer*. Expert C's restructuring would make the code *reasonable about*. A team that only does Expert B's work ships a system that passes tests but surprises them in production — because the structural ambiguity is still there, generating new categories of bugs faster than you can patch old ones.
