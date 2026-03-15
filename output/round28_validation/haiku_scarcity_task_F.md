I'll analyze this EventBus using the **scarcity lens** from your portfolio—asking what resources this design assumes are infinite, then flipping the assumptions.

---

## CONCRETE PROBLEMS & SCARCITIES

| Problem | Resource Assumed Infinite | Evidence in Code |
|---------|--------------------------|------------------|
| **Dead-letter queue unbounded** | Memory | `self._dead_letter.append()` with no cap, retention, or cleanup |
| **Handlers re-sorted on every registration** | CPU / handler count stays small | `sort(key=lambda x: -x[0])` on every `on()` call is O(n log n) |
| **Context dict mutated implicitly by middleware** | Predictability / correctness | Middleware receives mutable dict, can corrupt state across handlers |
| **All handlers run synchronously, serially** | Latency budget / handler speed | No async, no parallelism, one slow handler blocks entire emit() |
| **No handler removal, no introspection** | Handler lifecycle brevity | Once registered, handlers live forever; no `off()`, no visibility |
| **Unstructured context (grows ad-hoc)** | Schema coordination | Keys appear organically: `type`, `payload`, `cancelled`, `error`, `results`—easy collisions |
| **No retry or backoff on failure** | Transient fault tolerance | Exception caught, stored, event abandoned in dead letter |
| **Exceptions abort handler chain** | Fault isolation | One exception stops remaining handlers for that event type |

---

## OPPOSITE SCARCITIES: ALTERNATIVE DESIGNS

### **Design A: Memory-Constrained EventBus** 
*Assumption: Memory is scarce, not latency.*

```python
from collections import deque
from time import time

class MemoryBoundedEventBus:
    def __init__(self, dead_letter_capacity=1000, ttl_hours=1):
        self._handlers = {}
        self._middleware = []
        self._dead_letter = deque(maxlen=dead_letter_capacity)  # Auto-drop oldest
        self._sample_every_nth = 1  # Could be 10 to sample 1-in-10 failures
        self._failure_count = 0
        self._ttl = ttl_hours * 3600
        self._timestamps = deque(maxlen=dead_letter_capacity)

    def emit(self, event_type, payload):
        # ... same as original ...
        except Exception as e:
            self._failure_count += 1
            # Only record if sampled or under TTL threshold
            if self._failure_count % self._sample_every_nth == 0:
                self._dead_letter.append(context)
                self._timestamps.append(time())
```

**Trade-off:** 
- ✓ Memory bounded (max 1000 entries, auto-evicts oldest)
- ✗ **Lose failure precision** — old bugs disappear, sampling creates deliberate blindness
- ✗ Can't debug cascading failures if you only see 1-in-10
- ✗ What if the missing 9 are the signal?

---

### **Design B: Latency-Constrained EventBus**
*Assumption: Handler latency is scarce, not memory or ordering.*

```python
import asyncio
from collections import defaultdict

class AsyncEventBus:
    def __init__(self):
        self._handlers = defaultdict(list)
        self._middleware = []
        self._dead_letter = []
        self._tasks = set()  # Background tasks

    async def on_async(self, event_type, handler, priority=0):
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    async def emit_fire_and_forget(self, event_type, payload):
        """Return immediately, process in background."""
        context = {"type": event_type, "payload": payload, "cancelled": False}
        
        # Middleware runs sync (fast path)
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context
        
        # Handlers run in background
        task = asyncio.create_task(self._handle_async(event_type, context))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        
        return {"status": "queued", "context_id": id(context)}  # Return immediately

    async def _handle_async(self, event_type, context):
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(context)
            return
        
        # Run handlers in parallel
        results = await asyncio.gather(
            *[handler(context) for _, handler in handlers],
            return_exceptions=True
        )
        context["results"] = results
```

**Trade-off:**
- ✓ Emit returns in microseconds (fire-and-forget)
- ✗ **Lose ordering guarantees** — handlers run in parallel, interleave
- ✗ **Lose synchronous feedback** — caller can't check results before returning
- ✗ Race conditions if events from different emits interleave
- ✗ Debugging becomes harder (async stack traces)
- ✓ Can handle 1000x more events/sec

---

### **Design C: Type-Safe, Pre-Registered EventBus**
*Assumption: Type correctness is scarce, not flexibility.*

```python
from typing import TypedDict, Callable, Type, Dict

class UserCreatedPayload(TypedDict):
    user_id: int
    email: str

class PaymentFailedPayload(TypedDict):
    user_id: int
    amount: float
    reason: str

# Pre-register all event types
EVENT_SCHEMAS: Dict[str, Type[TypedDict]] = {
    "user.created": UserCreatedPayload,
    "payment.failed": PaymentFailedPayload,
}

class TypedEventBus:
    def __init__(self):
        self._handlers: Dict[str, list] = {}
        self._schemas = EVENT_SCHEMAS
        self._dead_letter = []

    def on(self, event_type: str, handler: Callable, priority=0):
        if event_type not in self._schemas:
            raise ValueError(f"Unknown event type: {event_type}")
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))

    def emit(self, event_type: str, payload: dict):
        # Validate against schema
        if event_type not in self._schemas:
            raise ValueError(f"Unknown event type: {event_type}")
        
        schema = self._schemas[event_type]
        # Runtime validation (at least)
        for key in schema.__required_keys__:
            if key not in payload:
                raise ValueError(f"Missing required field: {key}")
        
        # Now handlers can trust payload structure
        # ...
```

**Trade-off:**
- ✓ Payload structure guaranteed at runtime
- ✗ **Lose flexibility** — can't emit arbitrary events
- ✗ Schema boilerplate
- ✗ Adding new fields requires bus restart
- ✓ Self-documenting, collision-proof

---

### **Design D: Introspectable, Removable Handlers**
*Assumption: Handler lifecycle management is scarce.*

```python
class ManagedEventBus:
    def __init__(self):
        self._handlers = {}
        self._handler_ids = {}  # Map handler func to UUID
        self._middleware = []
        self._dead_letter = []

    def on(self, event_type, handler, priority=0, handler_id=None):
        handler_id = handler_id or id(handler)
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler, handler_id))
        self._handlers[event_type].sort(key=lambda x: -x[0])
        self._handler_ids[handler_id] = (event_type, handler)

    def off(self, handler_id):
        """Remove a handler by ID."""
        if handler_id not in self._handler_ids:
            return False
        event_type, handler = self._handler_ids[handler_id]
        self._handlers[event_type] = [
            (p, h, hid) for p, h, hid in self._handlers[event_type]
            if hid != handler_id
        ]
        del self._handler_ids[handler_id]
        return True

    def list_handlers(self, event_type=None):
        """Inspect what's registered."""
        if event_type:
            return [(p, h, hid) for p, h, hid in self._handlers.get(event_type, [])]
        return self._handler_ids

    def metrics(self):
        """Get bus state."""
        return {
            "events": len(self._handlers),
            "handlers": sum(len(h) for h in self._handlers.values()),
            "dead_letters": len(self._dead_letter),
        }
```

**Trade-off:**
- ✓ Handlers can be removed dynamically
- ✗ **More state to track** — handler IDs, reverse mapping
- ✗ Function identity is fragile (what if you wrap a handler?)
- ✓ Debugging and monitoring now possible

---

### **Design E: Resilient with Retry**
*Assumption: Failure resilience is scarce, not simplicity.*

```python
import time
from math import exp

class ResilientEventBus:
    def __init__(self, max_retries=3, base_backoff=0.1):
        self._handlers = {}
        self._middleware = []
        self._dead_letter = []
        self._max_retries = max_retries
        self._base_backoff = base_backoff

    def emit(self, event_type, payload):
        context = {"type": event_type, "payload": payload, "cancelled": False}
        
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context
        
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(context)
            return context
        
        results = []
        for _, handler in handlers:
            result = self._call_with_retry(handler, context)
            results.append(result)
        
        context["results"] = results
        return context

    def _call_with_retry(self, handler, context):
        for attempt in range(self._max_retries + 1):
            try:
                return handler(context)
            except Exception as e:
                if attempt == self._max_retries:
                    # Final failure
                    context["error"] = e
                    context["failed_after_retries"] = self._max_retries
                    self._dead_letter.append(context)
                    return None
                # Exponential backoff
                wait = self._base_backoff * (2 ** attempt)
                time.sleep(wait)
```

**Trade-off:**
- ✓ Transient failures auto-recover
- ✗ **Complexity** — retry state machine, backoff logic
- ✗ Masks real failures (you only see the last exception)
- ✗ Blocking sleep—can't parallelize
- ✗ Retrying idempotent handlers—ok. Retrying payment handlers—disaster.

---

## CONSERVATION LAW

**What is preserved across ALL designs?**

```
INVARIANT: A failure still occurs. You only redistribute it.

Total Unhandled Failures = 
    Failures Noticed Early (sync) 
    + Failures Discovered Late (async)
    + Failures Never Discovered (memory-bounded sampling)

What you trade:
  • When discovered: during emit() vs later in metrics
  • How stored: dead-letter list vs metrics counter vs logs vs honeycomb
  • How long remembered: forever vs TTL vs sampled
  • What costs: latency vs memory vs correctness

THE AXIS: Visibility vs Resource Cost

You cannot have high visibility AND bounded memory AND low latency 
AND strict ordering simultaneously. You pick three.
```

**Formal statement:** The failure rate is fixed (external to bus). What varies is your ability to *observe* and *react to* it.

---

## WHAT REMAINS UNMOVABLE IN 6 MONTHS

Three constraints will not budge no matter how you redesign:

1. **Handler code is still the bottleneck.** Whether you run async, parallel, or with retries, the handler itself is O(handler execution time). You can't redesign away a slow handler. The bus optimization is worthless if the handler blocks I/O. *(The bottleneck is external.)*

2. **You must still decide what happens when no handlers match.** Silent drop? Dead-letter? Exception? This decision is *forced*. There's no "neutral" option. Every design makes a choice; none eliminates the choice. *(The absence is permanent.)*

3. **You still can't have both strict ordering AND parallelism.** One design path buys you speed, the other buys you guarantees. In 6 months you'll still be making that trade-off. *(The constraint is topological, not technological.)*

---

## RECOMMENDATION

Your original design assumes **memory and latency are free**. For most production buses, that's actually correct—the real pressure is **visibility + resilience**. 

**Hybrid: Use Design D + E**
- Add handler management (on/off/list)
- Add exponential backoff + circuit breaker
- Keep synchronous (no async unless latency tests fail)
- Add metrics endpoint
- Cap dead-letter to recent 1000 entries + TTL to 1 hour

This trades *implementation simplicity* for *operability*. In 6 months, you'll wish you had visibility. You'll never wish for a simpler bus.
