## Structural Patterns

The code combines two distinct patterns: **circuit breaker** (state machine guarding calls) and **retry with exponential backoff** (resilience inside each call). These are legitimate patterns, but the nesting creates friction.

---

## Problems

### 1. Retry swallows `max_retries` and `base_delay` from caller kwargs (silent parameter collision)

```python
def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
```

If the caller passes `max_retries` to configure the retry count, it works. But if `fn` itself accepts a `max_retries` parameter, it will never receive it — `_retry_with_backoff` intercepts it silently. No error, wrong behavior.

### 2. `_last_failure_time` keeps updating while OPEN — recovery can be indefinitely deferred

In `_on_failure()`, `_last_failure_time = time.time()` runs even when `self._state == self.OPEN`. If failures arrive at any rate faster than `reset_timeout`, the circuit never recovers. The timer should freeze when the circuit opens.

### 3. Failure threshold is multiplied by retry count — circuit is ~3× harder to open than intended

`_retry_with_backoff` retries 3 times internally, then raises. Only then does `execute()`'s except block call `_on_failure()` — once. So `failure_threshold=5` actually requires 5 `execute()` call failures, each of which may represent 3 attempts. The circuit opens much later than the threshold implies.

Whether this is a bug or a feature depends on intent, but it's not documented and likely surprising.

### 4. HALF_OPEN doesn't limit concurrent probes

```python
# execute():
if time.time() - self._last_failure_time > self._reset_timeout:
    self._state = self.HALF_OPEN
    self._success_count = 0
```

Multiple threads can all pass this check before any of them complete. They all set `_state = self.HALF_OPEN` (harmless but wasteful) and all execute against the potentially-recovering service. The half-open state is supposed to probe with limited traffic; without a semaphore, it sends unrestricted traffic.

### 5. No thread safety anywhere

`_state`, `_failure_count`, `_success_count`, and `_last_failure_time` are all modified without locks. Classic TOCTOU: two threads can both read `_state == OPEN`, both compute the timeout elapsed, both flip to HALF_OPEN simultaneously, and both proceed. The success counter in `_on_success()` has a check-then-act race:

```python
if self._success_count >= self._half_open_max:
    self._state = self.CLOSED   # two threads can both enter this branch
```

### 6. Single success resets all failure history in CLOSED state

```python
def _on_success(self):
    ...
    else:
        self._failure_count = 0
```

4 failures + 1 success → failure count resets to 0. The circuit effectively has no memory across successes. A flapping service (fail/succeed/fail/succeed) never triggers the breaker regardless of threshold.

### 7. `Exception("Circuit is open")` is untyped

Callers cannot distinguish "service failed after retries" from "circuit refused the call." Should be a named exception (`CircuitBreakerOpenError`) so callers can handle them differently (e.g., return cached data vs. surface error).

---

## Summary

| Problem | Severity | Type |
|---|---|---|
| Parameter collision in kwargs | High | Correctness |
| `_last_failure_time` updates while OPEN | High | Logic |
| Threshold effectively multiplied by retries | Medium | Design |
| HALF_OPEN unlimited concurrency | Medium | Design |
| No thread safety | High | Concurrency |
| Single success resets failure history | Medium | Design |
| Untyped circuit-open exception | Low | API |

The deepest issue is structural: retry and circuit breaker have **conflicting accountability models**. Retry counts individual attempts. Circuit breaker counts operation outcomes. Nesting one inside the other means neither operates on the granularity it was designed for.
