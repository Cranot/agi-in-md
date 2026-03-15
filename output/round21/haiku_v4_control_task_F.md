# EventBus Analysis: Patterns & Problems

## Pattern: Observer + Middleware + Dead Letter Queue

This combines three patterns—but with critical friction points.

---

## 🔴 Severe Issues

### 1. **Dead Letter Queue as Data Dump (Memory Leak)**
```python
self._dead_letter.append(context)  # Unbounded growth
```
- Grows infinitely in long-running services
- No purge, callback, or external sink
- "No handlers" and "handler crash" are conflated
- **Fix**: Dead letter should be a callback sink, not storage

### 2. **Middleware Contract Violation**
```python
context = mw(context)  # What if mw returns None?
if context.get("cancelled"):  # Will crash
```
- No validation that middleware returns a dict
- Middleware can silently corrupt context
- No rollback if middleware fails
- **Fix**: Validate return, wrap in try/except, or use immutable event data

### 3. **Handler Error Isolation is Broken**
```python
except Exception as e:
    context["error"] = e  # Only latest error kept
    self._dead_letter.append(context)  # Appended on EVERY error
```
- First handler exception adds to dead letter
- Then subsequent handlers still run
- But they don't know about the prior failure
- `context["error"]` only holds the last error
- **Fix**: Track all failures or stop-on-first-error strategy

### 4. **No Unsubscribe Mechanism**
- Handlers registered but never removed → memory leak over time
- Same handler can register multiple times
- No way to pause/resume/cleanup

---

## 🟡 Design Issues

### 5. **Implicit Async Incompatibility**
```python
results.append(handler(context))
```
- No support for async handlers
- If handler returns a coroutine, it's added to results unawaited
- Caller can't tell if work is actually done

### 6. **Handler Priority Sort Inefficiency**
```python
self._handlers[event_type].sort(key=lambda x: -x[0])  # On every registration
```
- O(n log n) on every `.on()` call instead of binary insertion
- Re-sorts even if handlers already sorted

### 7. **Cancellation Signal is Silent**
```python
if context.get("cancelled"):
    return context  # Handlers don't know WHY they didn't run
```
- Handler has no way to distinguish: cancelled vs no handlers vs error
- Middleware can cancel without explanation

### 8. **No Type Hints or Validation**
- Handler signature unknown
- Middleware return type unchecked
- Payload structure undefined

---

## 🔍 Hidden Assumptions (The Inversion)

**This design assumes:**
- Handlers are synchronous, fast, and well-behaved ✓
- Dead letters are temporary/debug-only ✗ (grows unbounded)
- Handlers are stateless ✓
- Errors are rare ✗ (error path is primary concern)
- Single-threaded execution ✗ (not thread-safe)

**When you flip any assumption:**
- Add async handlers → breaks completely
- Add concurrency → race conditions
- Add handler cleanup → no interface exists
- Add observability → dead letter design fails
- Add timeout requirements → no mechanism

---

## 🛠️ Minimal Fixes (Priority Order)

```python
class EventBus:
    def __init__(self, on_dead_letter=None):
        self._handlers = {}
        self._middleware = []
        self._on_dead_letter = on_dead_letter or (lambda e: None)
        self._handler_ids = {}  # For unsubscribe

    def off(self, event_type, handler_id):
        """Unsubscribe"""
        if event_type in self._handler_ids:
            del self._handler_ids[handler_id]

    def emit(self, event_type, payload):
        context = {
            "type": event_type, 
            "payload": payload, 
            "cancelled": False,
            "failures": [],  # Track all errors
        }
        
        # Middleware with validation + error handling
        for mw in self._middleware:
            try:
                result = mw(context)
                if result is not None:
                    context = result
                if not isinstance(context, dict):
                    raise TypeError("Middleware must return dict")
            except Exception as e:
                context["failures"].append({"phase": "middleware", "error": e})
                self._on_dead_letter(context)
                return context
                
            if context.get("cancelled"):
                return context
        
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._on_dead_letter({"type": "no_handlers", "context": context})
            return context
        
        results = []
        for _, handler in handlers:
            try:
                results.append(handler(context))
            except Exception as e:
                context["failures"].append({"handler": handler.__name__, "error": e})
                # Continue but track failure
        
        context["results"] = results
        if context["failures"]:
            self._on_dead_letter(context)
        
        return context
```

**The real question:** Should this be async-first instead?
