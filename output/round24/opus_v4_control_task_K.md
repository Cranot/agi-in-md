# Circuit Breaker + Retry: Analysis of Antagonistic Pattern Composition

## Pattern Recognition

This composes two resilience patterns: **Circuit Breaker** (Nygard, *Release It!*) and **Retry with Exponential Backoff**. The critical structural insight is that these patterns have **opposing goals**, and their composition here creates several subtle failures.

---

## The Core Design Flaw: Antagonistic Composition

```
Retry says:    "Try again — it might work."
Breaker says:  "Stop trying — the service is down."
```

Here, retry is **nested inside** the circuit breaker:

```python
def execute(self, fn, *args, **kwargs):
    # ... state check ...
    result = self._retry_with_backoff(fn, *args, **kwargs)  # 3 attempts
    self._on_success()   # counted as 1 success
    # ...
    self._on_failure()   # counted as 1 failure
```

The breaker sees **one** failure. The downstream service absorbed **three** failed requests. To trip the circuit at threshold 5, the service actually endures **5 × 3 = 15 failed calls** — exactly the thundering load the breaker exists to prevent.

**The fix requires choosing a composition order:**

```
Option A:  breaker.execute(single_call)        — breaker wraps each attempt
Option B:  retry(breaker.execute(single_call))  — retry wraps the breaker
Option C:  count individual attempt failures in the breaker, not just final
```

---

## Problem Catalog

### 1. Thread Safety — Absent Entirely (Critical)

Circuit breakers exist for concurrent systems. Every piece of shared state here is unguarded:

```python
# Thread A reads OPEN, starts transitioning to HALF_OPEN
if time.time() - self._last_failure_time > self._reset_timeout:
    self._state = self.HALF_OPEN        # Thread A writes
    # Thread B also reads OPEN, also enters this branch
    self._success_count = 0             # Both threads reset, both proceed
```

**Result:** Multiple threads flood through HALF_OPEN simultaneously, defeating its purpose of sending a controlled probe. Every state check and mutation is a race.

### 2. Keyword Argument Shadowing

```python
def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
    ...

def execute(self, fn, *args, **kwargs):
    result = self._retry_with_backoff(fn, *args, **kwargs)
```

If the caller writes `breaker.execute(my_api_call, max_retries=10)`, the value is silently captured by `_retry_with_backoff` instead of being forwarded to `fn`. This is a parameter interception bug with no warning.

### 3. HALF_OPEN → OPEN Works by Accident

Trace the failure count through the lifecycle:

```
CLOSED:    _failure_count climbs to 5 → OPEN
OPEN:      _failure_count stays at 5 (never reset)
HALF_OPEN: _failure_count still 5
           Any failure calls _on_failure():
               _failure_count becomes 6
               6 >= 5 → OPEN                    # "correct" but accidental
```

The `_failure_count` is never reset on HALF_OPEN entry. The transition back to OPEN on any probe failure is **accidental correctness** — it works because the count was already at the threshold, not because HALF_OPEN has explicit single-failure-trips-open logic. The count also grows unboundedly across cycles.

### 4. No Error Classification

```python
except Exception as e:    # catches everything identically
    if attempt == max_retries - 1:
        raise
```

A `400 Bad Request` (permanent, never retriable) and a `503 Service Unavailable` (transient, always retriable) receive identical treatment. The retry wastes time on deterministic failures; the breaker opens on client errors that say nothing about service health.

### 5. HALF_OPEN Allows Unbounded Concurrency

`_half_open_max` names the success count needed to close the circuit, **not** a concurrency limit. There is no gate limiting how many requests pass through during the probe phase:

```python
# HALF_OPEN: every thread passes through here simultaneously
self._state = self.HALF_OPEN
self._success_count = 0
# no semaphore, no request counting, no single-probe logic
```

### 6. Blocking Sleep Under Load

```python
delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
time.sleep(delay)  # holds thread for up to ~4 seconds per retry cycle
```

In a thread-pool server, blocked threads during backoff exhaust capacity. The circuit breaker should be *saving* resources; instead, threads accumulate sleeping in retry loops before the breaker even has a chance to trip.

### 7. Intermediate Exceptions Swallowed Silently

```python
for attempt in range(max_retries):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        if attempt == max_retries - 1:
            raise
        # attempts 0 and 1: exception silently discarded
```

No logging, no exception chaining. If attempt 0 fails with `ConnectionRefused` and attempt 2 fails with `Timeout`, only `Timeout` propagates. The diagnostic trail is destroyed.

---

## State Machine Summary

```
          success × half_open_max
    ┌──────────────────────────────────┐
    │                                  ▼
  HALF_OPEN ◄──── timeout ──── OPEN ◄───── failure_count ≥ 5
    │                            ▲              │
    │  failure (accidental)      │              │
    └────────────────────────────┘          CLOSED
                                            ▲   │
                                 success────┘   │failure
                                     (resets    │(increments
                                      count)    count)
                                        └───────┘
```

Missing transitions / controls:
- **No HALF_OPEN → OPEN on explicit single failure** (relies on stale count)
- **No concurrency gate in HALF_OPEN**
- **No monotonic clock** (`time.time()` is subject to NTP adjustments)

---

## Inversion: What Does This Framing Hide?

Framing this as "retry *with* circuit breaker" implies they're complementary. They are **not**. They are competing resource-allocation strategies that must be composed with explicit priority:

| Concern | Retry's Answer | Breaker's Answer |
|---|---|---|
| Service struggling | Send more requests | Send zero requests |
| Individual failure | Try again now | Record and maybe stop |
| Resource allocation | Spend time waiting | Fail fast, free resources |

The deeper issue: **this class has two responsibilities with conflicting objectives and no arbitration**. A correct design separates them and composes externally, where the caller decides which strategy dominates:

```python
# Retry is a policy. Breaker is a policy. Compose, don't nest.
breaker = CircuitBreaker(failure_threshold=5)
retry   = RetryPolicy(max_attempts=3, backoff=exponential)

# Breaker dominates: each attempt is individually monitored
retry.execute(lambda: breaker.execute(fn, *args))
```

This way, the breaker counts *individual* failures (protecting the service), and retry operates *around* the breaker (potentially catching `CircuitOpenError` and deciding whether to wait for reset).
