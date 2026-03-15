# EventBus: Counter-Construction Analysis

## The Falsifiable Claim

**The EventBus has no coherent model of event identity or state ownership. The `context` dictionary simultaneously serves as event identity, routing state, execution state, and error record — making it structurally impossible to distinguish state that belongs to the event from state accumulated during its handling.**

Falsifiable: if you can demonstrate handler execution order never corrupts another handler's inputs via shared context mutation, the claim is wrong.

---

## Three Experts Transform the Claim

### Expert 1 — Defends

The shared mutable context creates invisible execution-order coupling. Handler B can read `context["error"]` written by handler A and silently alter behavior. The system *appears* to be fan-out but *behaves* as sequential coupling. The `results` list appended at the end doesn't capture per-handler errors; a failed handler still "ran" from the bus's perspective.

### Expert 2 — Attacks

Context mutation is real but secondary. The *actual* deepest problem is that `context = mw(context)` silently accepts `None` if middleware forgets a return — making the next middleware crash on `.get("cancelled")`. Middleware corruption is total and silent; handler corruption is at least caught. Also: `_dead_letter` conflates two different failure modes — unrouted events and execution errors — into one undifferentiated list.

### Expert 3 — Probes What Both Take for Granted

Both of you assume the bus should be stateless between emissions. What if it's not? `_dead_letter` grows unboundedly with no drainage mechanism. The bus treats every emission as independent but accumulates cross-emission state with no eviction. The real problem: **this bus is neither stateless nor properly stateful — it is accidentally stateful.**

### The Transformed Claim

**The bus has no theory of what state belongs to an event versus what belongs to the bus. Context is mutable per-emission; `_dead_letter` is permanent across emissions. The handler-coupling problem is a symptom. The disease is the absence of any event lifecycle model.**

---

## The Gap as Diagnostic

| Original claim | Transformed claim |
|---|---|
| Context mutation couples handlers | Bus has no state ownership theory and no event lifecycle |

This gap exposes the **concealment mechanism**: **feature-level local correctness masking system-level incoherence.** Each feature — try/except, priority sort, dead letter, middleware chain — looks reasonable in isolation. Together, they perform error-handling while actually making errors *harder* to trace, not easier. The code looks like it handles failure. It accumulates it.

---

## Improvement 1: Immutable Context With Copy-on-Write

*Legitimate-looking. Passes review. Deepens concealment.*

```python
from copy import deepcopy
import uuid

def emit(self, event_type, payload):
    context = {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "payload": payload,
        "cancelled": False
    }
    
    for mw in self._middleware:
        next_ctx = mw(deepcopy(context))
        if next_ctx is None:
            raise ValueError(f"Middleware {mw.__name__!r} must return context")
        context = next_ctx
        if context.get("cancelled"):
            return context
    
    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(deepcopy(context))
        return context
    
    results = []
    for _, handler in handlers:
        handler_ctx = deepcopy(context)          # each handler sees clean input
        try:
            results.append(handler(handler_ctx))
        except Exception as e:
            snapshot = deepcopy(context)
            snapshot["error"] = e
            snapshot["handler"] = handler.__name__
            self._dead_letter.append(snapshot)
    
    context["results"] = results
    return context
```

**Why it passes review:** Fixes handler coupling (isolated copies), fixes silent middleware `None` bug, adds event IDs for tracing, snapshots context properly for dead letters. A reviewer sees defensive programming and is satisfied.

**Why it deepens concealment:**

1. Each dead-letter entry now contains a deep copy of payload — `_dead_letter` grows faster and larger, but the improvement makes individual entries look *richer*, distracting from the queue's unbounded growth.
2. By fixing the most *visible* symptom (handler coupling), it removes the evidence that would have led a debugger to discover the lifecycle problem.
3. The deep-copy snapshots create a false sense that dead letters are faithful failure records — but they snapshot *routing state*, not system state. There is no timestamp, no emission sequence number, no way to correlate entries across events.

---

## Three Properties Only Visible Because We Strengthened It

1. **Dead letters have no temporal or causal identity.** When deepcopy makes entries self-contained, you notice there is no emission sequence number, timestamp, or correlation ID. You cannot reconstruct the sequence of events that produced a failure.

2. **The `results` field is appended to the original context, not to any handler context.** The return value of `emit` is a hybrid: handler-isolated inputs, centralized result aggregation. The improvement makes this asymmetry structurally explicit.

3. **There is no API for the dead letter queue.** Making entries richer makes the absence of `drain()`, `replay()`, `inspect()`, or any eviction policy *conspicuous*. The queue is write-only. It is a black hole that looks like an error-recovery mechanism.

---

## Improvement 2: Shared Context With Explicit Handler Protocol

*Also legitimate. Also passes review. Directly contradicts Improvement 1.*

```python
def emit(self, event_type, payload):
    context = {
        "type": event_type,
        "payload": payload,
        "cancelled": False,
        "results": [],          # pre-declared, not appended ad-hoc
        "errors": []
    }
    
    for mw in self._middleware:
        updated = mw(context)
        if updated is not None:  # None means "pass through unchanged"
            context = updated
        if context.get("cancelled"):
            return context
    
    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append({"context": context, "reason": "no_handlers"})
        return context
    
    for _, handler in handlers:
        try:
            result = handler(context)      # shared context: handlers can coordinate
            context["results"].append(result)
        except Exception as e:
            context["errors"].append({
                "handler": handler.__name__,
                "error": e,
                "error_type": type(e).__name__
            })
            self._dead_letter.append({
                "context": context,
                "reason": "handler_error"
            })
    
    return context
```

**Why it passes review:** Pre-initializes `results` and `errors` (cleaner than ad-hoc appending), formalizes middleware pass-through semantics, adds `reason` to dead letter entries, includes `handler.__name__` and `error_type` for diagnostics. Looks like a thoughtful cleanup.

**Why it directly contradicts Improvement 1:**

| | Improvement 1 | Improvement 2 |
|---|---|---|
| Handler context | Isolated deep copy | Shared reference |
| Handler coupling | Explicitly prohibited | Explicitly permitted |
| Middleware None | Raises ValueError | Treated as pass-through |
| Philosophy | Handlers are independent | Handlers are collaborative |

Both are correct. Neither is wrong. They cannot coexist.

---

## The Structural Conflict

**The EventBus has no declared opinion on whether events are commands or notifications.**

- If events are **commands** — one handler owns the response, others are secondary — Improvement 1 is correct. Handler isolation prevents first-handler side effects from contaminating subsequent handlers.
- If events are **notifications** — all handlers observe and augment a shared result — Improvement 2 is correct. Context accumulation is the entire point.

The original code implements **fan-out** (notification semantics: all handlers receive the event) but **returns a single aggregated context** (command semantics: there is one answer). It supports priority ordering (implying some handlers matter more) but gives every handler equal access to mutate shared state (implying none has authority).

This conflict cannot be resolved by any local improvement because it is not an implementation bug. It is an **undeclared contract**. The original code's apparent "flexibility" is the structural absence of a decision about what the bus *is*.

The conflict is only visible because Improvement 1 and Improvement 2 are both legitimate — each one makes explicit a hidden assumption the original code carries implicitly without acknowledging. Every production EventBus built on this foundation will eventually bifurcate: some emitters will treat it as pub/sub, others as a pipeline, others as request-response. The bus will silently support all three until the day it cannot.
