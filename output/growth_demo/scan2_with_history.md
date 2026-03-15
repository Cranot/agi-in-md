## STEP 0: Constraint History Check

Found `.prism-history.md`. Previous analysis maximized thread-safety and race conditions. Sacrificed: **performance under load, observability, testing ergonomics, API design quality, failure type discrimination**.

→ This lens will target those sacrificed dimensions.

---

## STEP 1: Generated Lens

**"Performance + Observability + API Quality Lens"**

For each public method, construct a high-load scenario (10,000 concurrent calls) and trace the bottleneck. Identify every silent failure path where the caller cannot distinguish what went wrong. Build test cases that exercise each state transition and name which ones cannot be asserted without internal access. For the registry, construct three usage patterns that produce memory leaks or stale breaker references. Name the API contracts that are implicit rather than explicit. End with: performance ceiling predictions, observability gaps, and untestable behaviors.

---

## STEP 2: Execute the Lens

### Part 1: High-Load Performance Analysis

**Method: `call()` under concurrent load**

```python
# Simulated: 10,000 concurrent calls to a CLOSED breaker
```

Trace:
1. Each call invokes `self.state` property
2. `state` property acquires no lock but reads `self._last_failure_time` and modifies `self._state` 
3. In CLOSED state: no lock contention, but the property does a time comparison every single call
4. **Bottleneck identified**: The `state` property mutates `self._state` without holding a lock — this is cached in thread-local storage on some Python implementations, meaning different threads can see different states simultaneously

**Method: `_on_success()` and `_on_failure()` under load**

```python
# Every successful call acquires self._lock
with self._lock:
    if self._state == State.HALF_OPEN:
        # ... state transition ...
    self._success_count += 1  # ← ALWAYS executed, even in CLOSED state
```

**Critical finding**: `_success_count` is incremented on every success in CLOSED state but never used for anything. This is:
- Dead code under lock contention
- A performance tax on the happy path for zero benefit

**Performance ceiling prediction**: Under 10,000 TPS with 8 threads, lock contention on `self._lock` will serialize all success/failure callbacks. The `_success_count += 1` operation in CLOSED state is pure overhead.

---

### Part 2: Silent Failure Paths (Observability Gaps)

Construct caller perspective: "Why did my call fail?"

| Exception Raised | What Caller Knows | What Caller Cannot Distinguish |
|------------------|-------------------|-------------------------------|
| `CircuitOpenError` | Circuit is "open" | Is this OPEN or HALF_OPEN with limit reached? How long until retry? How many failures triggered this? |
| Wrapped exception | The underlying error | Was this counted toward threshold? Did it just trip the breaker? |

**Observability gap 1**: `CircuitOpenError` message includes `recovery_timeout` but not:
- Time remaining until recovery
- Current failure count
- Which state (OPEN vs HALF_OPEN blocked)

**Observability gap 2**: The `_notify()` system swallows all listener exceptions silently:
```python
for listener in self._listeners:
    try:
        listener(event, self)
    except Exception:
        pass  # ← Silent failure, no logging, no indication
```
If a metrics listener crashes, operations has no idea their observability is broken.

**Observability gap 3**: No metrics exposed:
- Total calls (success/failure)
- Current failure count (without accessing private `_failure_count`)
- Time in current state
- Last failure time

---

### Part 3: Testability Analysis

Construct test cases for each state transition:

| Transition | Testable Without Internal Access? | Problem |
|------------|-----------------------------------|---------|
| CLOSED → OPEN | **No** | Cannot observe `_failure_count` to assert threshold was reached. Must rely on behavior (exception raised) which conflates with OPEN state. |
| OPEN → HALF_OPEN | **No** | Cannot mock `time.time()` through public API. Must either wait real time or access `_last_failure_time`. |
| HALF_OPEN → CLOSED | **Partial** | Can assert no exception, but cannot verify `_failure_count` was reset without internal access. |
| HALF_OPEN → OPEN | **Partial** | Can assert exception raised, but cannot verify `_half_open_calls` was reset. |

**Testing ergonomics failure**: The only way to test state transitions reliably is to:
1. Access private `_state` directly (breaks encapsulation)
2. Subclass and expose internals
3. Use `time.sleep()` for timeout tests (slow, flaky)

**Missing test hooks**:
- No `set_state()` for test setup
- No `set_time_provider()` for deterministic time
- No `get_failure_count()` for assertions

---

### Part 4: Registry Memory Leak Analysis

Construct three patterns that leak:

**Pattern 1: Unbounded growth**
```python
# Each unique name creates a new breaker, never removed
for i in range(100000):
    registry.get_or_create(f"service_{i}")  # 100,000 breakers live forever
```
**Finding**: No max size, no TTL, no cleanup. Memory grows unbounded.

**Pattern 2: Stale references after removal**
```python
breaker = registry.get_or_create("db")
registry.remove("db")
# breaker still exists and is usable, but not tracked
breaker.call(lambda: 1/0)  # This breaker is orphaned, will never be cleaned up
```
**Finding**: `remove()` doesn't invalidate the breaker object — it's a leak of the object and a potential source of confusion.

**Pattern 3: Thread-unsafe singleton initialization**
```python
@classmethod
def get_instance(cls) -> "CircuitBreakerRegistry":
    if cls._instance is None:  # ← Race condition
        cls._instance = cls()
    return cls._instance
```
Two threads can both see `None` and both create instances. The second one overwrites the first, orphaning any breakers created in the first instance.

---

### Part 5: Implicit API Contracts

| API | Explicit Contract | Implicit Contract (Hidden Assumption) |
|-----|-------------------|---------------------------------------|
| `call(func, *args)` | Returns func result or raises | func will be called synchronously; func exceptions are re-raised unchanged |
| `add_listener(listener)` | Appends to listeners | listener must accept `(event: str, breaker: CircuitBreaker)` — not type hinted; listener exceptions are swallowed |
| `state` property | Returns current State | **MUTATES state** (OPEN→HALF_OPEN) as side effect — property looks like read but writes |
| `reset()` | Resets to CLOSED | Thread-safe but doesn't notify listeners about reset — they won't know |

**Critical API design flaw**: The `state` property has a write side effect. Properties should be idempotent reads. This violates the principle of least surprise:

```python
# This innocent-looking read changes system behavior:
if breaker.state == State.OPEN:  # ← May transition to HALF_OPEN!
    # Now state is HALF_OPEN, but we checked for OPEN
```

---

## Findings Table

| Location | What Breaks | Severity | Fixable or Structural |
|----------|-------------|----------|----------------------|
| `_on_success()` line 78 | `_success_count` incremented under lock in CLOSED state for zero benefit — pure performance overhead | Medium | **Fixable** — only increment in HALF_OPEN |
| `state` property | Mutates `_state` without lock; appears to be read but writes; caller can't reason about state stability | High | **Fixable** — make state transition explicit method |
| `_notify()` line 94-97 | Listener exceptions swallowed silently; observability can fail without detection | Medium | **Fixable** — log or re-raise with option |
| Registry `get_instance()` | Race condition creates orphaned instances, potential memory leak | High | **Fixable** — use threading.Lock or `__new__` |
| Registry `_breakers` dict | No bounds, no TTL, unbounded memory growth | High | **Fixable** — add max_size + LRU eviction |
| `CircuitOpenError` message | Caller cannot distinguish OPEN from HALF_OPEN-blocked, cannot compute retry-after | Medium | **Fixable** — add `state`, `retry_after`, `failure_count` to exception |
| No public getters | `_failure_count`, `_last_failure_time` unreadable; tests must break encapsulation | Low | **Fixable** — add `get_stats()` method |
| No time injection | Timeout tests require real `time.sleep()` — slow and flaky | Medium | **Fixable** — accept `time_provider` in constructor |
| `reset()` no notification | Listeners not told about reset; external monitors will be wrong | Medium | **Fixable** — add `self._notify("circuit_reset")` |

---

```
---
CONSTRAINT NOTE: This analysis maximized performance under load, observability gaps, testing ergonomics, and API design quality.
It did not examine: thread-safety race conditions (covered in prior analysis), retry/backoff strategies, distributed systems concerns.
For deeper analysis: /prism-full | For meta-analysis: /prism-reflect
```
