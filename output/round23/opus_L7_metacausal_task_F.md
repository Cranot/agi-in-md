# Structural Analysis of EventBus

## Falsifiable Claim

> **The deepest structural problem is that a single mutable `context` dict serves simultaneously as data carrier, control-flow signal, and error record — funneling three distinct architectural patterns through one shared, aliased object.**

---

## The Dialectic

### Expert 1 (Defender): "Shared mutable context is the root"

The `context` dict is created once and then **passed by reference** through the entire chain. Every participant — middleware, handlers, the bus itself — reads and writes the same object:

```python
# Middleware mutates it
context = mw(context)          # may return same ref or new dict — no contract

# The bus mutates it
context["error"] = e           # written mid-loop
self._dead_letter.append(context)  # appends a LIVE REFERENCE

# Handlers read it
results.append(handler(context))   # sees mutations from prior handlers
```

Handler 3 sees whatever Handler 1 and 2 did to `context`. This makes every handler's behavior **dependent on registration order and the side effects of all predecessors**. You cannot reason about any handler in isolation.

### Expert 2 (Attacker): "That's a symptom. The real disease is no contracts."

The shared context is only dangerous *because* there's no boundary enforcement. Consider:

```python
def use(self, middleware_fn):
    self._middleware.append(middleware_fn)  # any callable accepted
                                            # no return type enforced
                                            # no schema on context
```

A middleware can return `None`, crashing the bus. A handler can delete `context["payload"]`. There's no validation, no schema, no isolation. The shared dict is just the **medium through which the absence of contracts becomes lethal**.

### Expert 3 (Assumption Prober): "You're both describing a conflation problem."

This bus jams **three patterns** into one object:

| Pattern | Needs | What `context` does instead |
|---|---|---|
| **Middleware pipeline** | Immutable-pass-through or explicit `next()` | Mutable dict, no `next()` chain |
| **Pub/Sub dispatch** | Isolated handler invocation | Shared state across all handlers |
| **Dead letter queue** | Snapshot of failed state | Aliased reference to live object |

The conflation makes each pattern **incorrect**:

---

## Concrete Bugs This Produces

### 1. Dead Letter Aliasing (most severe)
```python
context["error"] = e
self._dead_letter.append(context)  # same reference!
# loop continues...
results.append(handler(context))   # next handler mutates same dict
context["results"] = results       # overwrites what dead_letter "captured"
```
Every dead letter entry is a **live reference** to the same object. By the time you inspect `_dead_letter`, the entries reflect the *final* state, not the state at time of error. **Dead letter replay is impossible.**

### 2. Error Swallowing with Continued Execution
```python
except Exception as e:
    context["error"] = e           # recorded...
    self._dead_letter.append(context)  # logged...
    # BUT: loop continues to next handler
    # AND: if handler 3 also fails, it OVERWRITES context["error"]
```
Only the **last** error survives. Earlier errors are silently erased.

### 3. Middleware Return Contract Violation
```python
context = mw(context)  # if mw returns None → NoneType has no .get()
if context.get("cancelled"):  # 💥 AttributeError
```
No guard against middleware returning non-dict values.

### 4. Re-sort on Every Registration
```python
self._handlers[event_type].sort(key=lambda x: -x[0])  # O(n log n) every .on()
```
Should use `bisect.insort` for O(log n) insertion, or defer sorting to emit-time.

### 5. No Unsubscribe Mechanism
Handlers are anonymous tuples. There's no way to remove one — a memory/lifecycle leak in any long-lived system.

---

## Why the Dialectic Transformed Toward Conflation

The structural force is this: **the `context` dict is the only interface surface in the entire system**. There are no separate types for middleware input vs. handler input vs. dead letter entries. Because everything flows through one dict, every new concern (cancellation, errors, results, middleware) adds another field to the same object, increasing the coupling multiplicatively.

This is a **convergent coupling attractor** — the dict becomes easier to extend than to decompose, so each new feature reinforces the anti-pattern.

## Prediction

The next problem this code will face: **async support**. When someone adds `async def` handlers or middleware:

```python
results.append(await handler(context))  # multiple coroutines sharing one mutable dict
```

The shared mutable context will produce **race conditions** — concurrent handlers mutating `cancelled`, `error`, and `payload` simultaneously. The conflation that today causes *ordering bugs* will tomorrow cause **data races**, and the dead letter aliasing will make debugging them impossible because the captured state is never the state-at-time-of-failure.

---

## Fix Direction

```python
# Separate the three concerns with distinct types:
@dataclass(frozen=True)
class Event:          # immutable data carrier
    type: str
    payload: Any

class MiddlewareResult: # explicit control flow
    event: Event
    cancelled: bool

class DeadLetter:       # snapshot, not alias
    event: Event
    error: Exception
    timestamp: float
```

Frozen dataclasses enforce isolation. Each pattern gets its own type. The convergent coupling attractor is broken by making extension require *new types* rather than *new fields on the same dict*.
