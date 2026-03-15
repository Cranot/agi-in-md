# Circuit Breaker Analysis

## What the Code Does (4 Steps)

1. **Initialize state machine** - Creates a circuit breaker with three states (CLOSED→OPEN→HALF_OPEN) and tracking counters for failures and successes

2. **Check circuit state on execution** - If OPEN, verifies if reset timeout has elapsed; if yes, transitions to HALF_OPEN; if no, immediately rejects with an exception

3. **Retry failed requests with backoff** - Attempts to execute the function up to 3 times with exponential backoff (1s, 2s delays) + random jitter, catching all exceptions

4. **Transition states based on success/failure** - On success: close circuit if in HALF_OPEN; reset failures if in CLOSED. On failure: increment counter, and if threshold (5) is exceeded, switch to OPEN

---

## Key Assumptions

| # | Assumption | Impact Level |
|---|-----------|---|
| **1** | **Function is idempotent** - No side effects from retries | 🔴 Critical |
| **2** | **All exceptions are transient** - A 404 or validation error is treated like a timeout | 🔴 Critical |
| **3** | **Single-threaded execution** - State mutations are not atomic | 🔴 Critical |
| **4** | **`_last_failure_time` is always set before state is OPEN** - Using it safely in timeout check | 🟡 Medium (only if API is misused) |
| **5** | **Failure counts don't account for success streaks** - Resets counter on each CLOSED success | 🟡 Medium |
| **6** | **`max_retries=3, base_delay=1` are adequate defaults** - Hardcoded in method, not configurable | 🟡 Medium |

---

## Test Case: Violating the "Permanent Errors" Assumption

```python
# ❌ PROBLEM: Retrying non-transient errors wastes time and fills circuit

import time
from unittest.mock import patch

def test_permanent_error_handling():
    """Circuit treats permanent errors (404, validation) same as transient (timeout)"""
    
    call_log = []
    
    def api_call(user_id):
        call_log.append(time.time())
        if user_id < 0:
            raise ValueError("Invalid user ID")  # ← PERMANENT, should fail fast
        return {"id": user_id}
    
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=30)
    start = time.time()
    
    # First call: permanent error
    try:
        cb.execute(api_call, -1)
    except ValueError as e:
        duration = time.time() - start
        print(f"❌ Result: Retried {len(call_log)} times, wasted {duration:.1f}s on permanent error")
        print(f"   Error: {e}")
        # Output: Retried 3 times, wasted ~3 seconds on a permanent -1 ID error!
    
    # Verify the damage: circuit health is hurt for a non-recoverable error
    print(f"   Failure count increased to {cb._failure_count}/2 (threshold)")
```

**What happens:** 
- ✗ **Wastes ~3 seconds** on exponential backoff for a permanent error
- ✗ **Fills the failure counter** (now 1/2 toward opening), even though the service didn't fail—the *input* was invalid
- ✗ **Silent degradation** - no distinction between "API is down" vs "you sent bad data"

---

## Test Case: Violating the "Idempotent Function" Assumption

```python
def test_side_effects_in_retry():
    """Retrying a non-idempotent function causes duplicate side effects"""
    
    charge_log = []
    
    def charge_payment(amount):
        charge_log.append(amount)
        if len(charge_log) < 3:
            raise IOError("Network timeout")
        return {"transaction_id": len(charge_log)}
    
    cb = CircuitBreaker()
    
    try:
        cb.execute(charge_payment, 99.99)
    except IOError:
        pass
    
    print(f"❌ Customer charged {len(charge_log)} times for 1 purchase!")
    print(f"   Total charged: ${sum(charge_log):.2f} instead of ${99.99:.2f}")
    # Output: Customer charged 3 times! Total charged: $299.97 instead of $99.99
```

---

## Test Case: Violating the "Thread Safety" Assumption

```python
import threading

def test_concurrent_state_mutations():
    """Race conditions cause inconsistent circuit state"""
    
    def always_fails():
        raise Exception("Service error")
    
    cb = CircuitBreaker(failure_threshold=5)
    exceptions_caught = []
    
    def worker(thread_id):
        for i in range(10):
            try:
                cb.execute(always_fails)
            except Exception as e:
                exceptions_caught.append((thread_id, str(e)))
            time.sleep(0.0001)  # Yield to increase race window
    
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    open_count = sum(1 for _, msg in exceptions_caught if "open" in msg)
    print(f"❌ Final state: {cb._state}, Failure count: {cb._failure_count}")
    print(f"   Expected ~25 'open' exceptions, got {open_count}")
    print(f"   Race condition: State and counters are INCONSISTENT")
    # Output shows off-by-one errors, unpredictable state, non-deterministic behavior
```

---

## Structural Problems Identified

### 🔴 Critical Issues

| Problem | Why It Matters |
|---------|---|
| **No error classification** | Treats `404 Not Found` (permanent) same as `ConnectionTimeout` (transient). Retries non-retriable errors and wastes circuit health. |
| **Non-thread-safe state mutations** | Multiple threads cause race conditions: `self._failure_count += 1` and state transitions aren't atomic. Circuit opens unpredictably or not at all. |
| **Side effect vulnerability** | If function has side effects (payment, data write, message send), each retry duplicates them. **Can cause data corruption.** |

### 🟡 Moderate Issues

| Problem | Effect |
|---------|--------|
| **Hardcoded retry parameters** | `max_retries=3, base_delay=1` buried in method signature—difficult to tune for different scenarios |
| **Success resets counter in CLOSED** | One success wipes all failure history (Fail→Fail→Fail→Success→Fail→Fail→Fail→Fail→Fail = only 5 fails, opens circuit at last one). Doesn't detect recent degradation trends. |
| **No failure type distinction** | No way to mark errors as non-retriable (HTTP 400, 401, 403, validation errors) |
| **Stale success_count in HALF_OPEN** | `_success_count` isn't reset when returning to OPEN, causing circuit to close too easily on second recovery attempt |
| **No logging/metrics** | Silent failures—no visibility into why circuit opened or state transitions |

---

## The Most Fragile Assumption

### 🏆 **Thread Safety**  (Most Fragile)

**Why?**
- ✗ Easiest to violate accidentally (just call from async/web framework)
- ✗ Failures are **non-deterministic**—same code fails intermittently
- ✗ Silently corrupts state without raising errors
- ✗ Very hard to debug (Heisenbugs)
- ✗ No guards or warnings in the code

**Example:** With 3 threads, `_failure_count` might be 3, 4, 5, or 6 depending on timing—the circuit opens unpredictably.

### 🥈 **Function is Idempotent** (Second Fragile)

- Easy to violate (DB writes, payments, notifications)
- **Causes permanent damage** (data duplication, duplicate charges)
- Silent—you won't notice until auditing logs

### 🥉 **All Exceptions are Transient** (Third Fragile)

- Common to violate (validation errors, auth failures, 404s)
- Wastes resources on non-recoverable errors
- Fills circuit unnecessarily
- **Behavior: Wastes time and false opens circuit**

---

## How to Fix

```python
import threading
from enum import Enum

class ErrorType(Enum):
    TRANSIENT = "transient"      # Retry (timeout, 429, 503)
    PERMANENT = "permanent"       # Fail fast (400, 401, 403, 404)
    UNKNOWN = "unknown"

class CircuitBreakerFixed:
    def __init__(self, *args, **kwargs):
        # ... existing code ...
        self._lock = threading.RLock()  # ← Add thread safety
    
    def execute(self, fn, *args, classify_error=None, **kwargs):
        with self._lock:  # ← Atomic state checks
            if self._state == self.OPEN:
                if time.time() - self._last_failure_time > self._reset_timeout:
                    self._state = self.HALF_OPEN
                    self._success_count = 0
                else:
                    raise Exception("Circuit is open")
        
        try:
            # Only retry TRANSIENT errors
            result = self._retry_with_backoff(
                fn, *args, 
                classify_error=classify_error,  # ← Pass classifier
                **kwargs
            )
            with self._lock:
                self._on_success()
            return result
        except Exception as e:
            with self._lock:
                self._on_failure()
            raise
```

This code assumes **too much** about reliability and safety for production use.
