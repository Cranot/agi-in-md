# Analysis: Retry Mechanism + Circuit Breaker as Orthogonal Systems

## Structural Patterns

This code presents itself as a **circuit breaker** but implements **three distinct subsystems**:

1. **Exponential backoff retry loop** (lines 19-27) — retry up to 3 times with sleep
2. **3-state machine** (CLOSED → OPEN → HALF_OPEN → CLOSED) — manages circuit state
3. **Failure/success counters** — track state transitions

These operate on the **same exception**, creating hidden coupling.

---

## Concealment Mechanisms

### 1. **Retry Loop is Invisible to Callers**
- Callers see: `execute(fn)` → result or exception
- Callers don't see: **up to 3 retries with exponential backoff happen first**
- The "failure_count" is not the number of `execute()` calls that failed—it's the number of **exhausted retry sequences**
- **Impact**: A single function failure becomes 3 internal attempts before the circuit breaker even counts it as 1 failure

### 2. **Asymmetric HALF_OPEN Recovery**
- Failures in HALF_OPEN: increment counter but **never reopen circuit**
- Successes in HALF_OPEN: close circuit after N successes
- **Concealment**: There is no failure threshold in HALF_OPEN. You can fail 100 times and the circuit stays HALF_OPEN, silently degrading

### 3. **Stale Success Count**
- When transitioning OPEN → HALF_OPEN, line 15 sets `self._success_count = 0` ✓
- But there's no explicit reset of `_success_count` when HALF_OPEN → CLOSED
- `_on_success()` checks `if self._state == self.HALF_OPEN` only—when state is already CLOSED, `_success_count` is never touched
- **Concealment**: Next time you enter HALF_OPEN, the old `_success_count` might affect behavior

### 4. **Retry Parameters are Opaque to the Circuit**
- Circuit breaker doesn't know it's doing 3 retries with base_delay=1
- State transitions don't account for this overhead
- **Concealment**: `failure_threshold=5` actually means "5 exhausted retry sequences = 15 function calls" (worst case)

---

## Test Suite That Validates Observable Behavior

```python
import pytest
import time
from unittest.mock import Mock, patch

class TestCircuitBreaker:
    
    # State transitions
    def test_initial_state_closed(self):
        cb = CircuitBreaker()
        assert cb._state == CircuitBreaker.CLOSED
    
    def test_closed_to_open_on_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        fn = Mock(side_effect=Exception("fail"))
        
        for _ in range(3):
            with pytest.raises(Exception):
                cb.execute(fn)
        
        assert cb._state == CircuitBreaker.OPEN
    
    def test_open_rejects_immediately(self):
        cb = CircuitBreaker(failure_threshold=1)
        fn = Mock(side_effect=Exception("fail"))
        cb.execute(fn)  # Trigger OPEN
        
        fn.reset_mock()
        with pytest.raises(Exception, match="Circuit is open"):
            cb.execute(fn)
        assert fn.call_count == 0  # Function not called
    
    def test_open_to_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=1)
        fn = Mock(side_effect=Exception("fail"))
        cb.execute(fn)  # Open
        
        time.sleep(1.1)
        fn.side_effect = None
        fn.return_value = "ok"
        
        result = cb.execute(fn)
        assert cb._state == CircuitBreaker.HALF_OPEN
        assert result == "ok"
    
    def test_half_open_to_closed(self):
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.1, half_open_max=2)
        fn = Mock(side_effect=Exception("fail"))
        cb.execute(fn)  # Open
        
        time.sleep(0.2)
        fn.side_effect = None
        fn.return_value = "ok"
        
        cb.execute(fn)  # success_count=1
        assert cb._state == CircuitBreaker.HALF_OPEN
        
        cb.execute(fn)  # success_count=2 → CLOSED
        assert cb._state == CircuitBreaker.CLOSED
    
    # Retry logic
    def test_retry_on_intermediate_failure(self):
        cb = CircuitBreaker()
        fn = Mock(side_effect=[Exception(), Exception(), "ok"])
        
        result = cb.execute(fn)
        assert result == "ok"
        assert fn.call_count == 3  # Retried
    
    def test_retry_exhaustion_counts_as_one_failure(self):
        cb = CircuitBreaker()
        fn = Mock(side_effect=Exception())
        
        with pytest.raises(Exception):
            cb.execute(fn)
        
        assert fn.call_count == 3  # Three attempts
        assert cb._failure_count == 1  # But circuit sees 1
    
    def test_failure_count_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=5)
        fn = Mock(side_effect=Exception())
        
        for _ in range(2):
            with pytest.raises(Exception):
                cb.execute(fn)
        assert cb._failure_count == 2
        
        fn.side_effect = None
        fn.return_value = "ok"
        cb.execute(fn)
        assert cb._failure_count == 0
    
    def test_half_open_failure_does_not_reopen(self):
        """⚠️ This test passes but reveals the hidden contract violation"""
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.1, half_open_max=3)
        fn = Mock(side_effect=Exception())
        cb.execute(fn)  # Open
        
        time.sleep(0.2)
        for _ in range(10):  # Fail 10 times in HALF_OPEN
            try:
                cb.execute(fn)
            except:
                pass
        
        # Circuit is still HALF_OPEN, not OPEN (no re-opening on failure)
        assert cb._state == CircuitBreaker.HALF_OPEN
        assert cb._failure_count == 11  # Counts keep growing
```

---

## Contract with Dependent Systems (That No Test Can Verify)

### Contract 1: "Failure Count = Actual Failure Magnitude"
**Promised**: When circuit opens at failure_threshold=5, the downstream has experienced 5 genuine failures.

**Actual**: The downstream experienced **5 × 3 = 15 attempts**, spread over **125+ seconds** of exponential backoff.

**Why unverifiable**: Tests correctly show failure_count increments. They don't measure what that count *means* to a dependent system.

---

### Contract 2: "OPEN State Protects Against Cascading Failure"
**Promised**: Fast-fail prevents overloading a failing service.

**Actual**: By the time the circuit opens, the service has already been hammered with 15 attempts over 125+ seconds of cumulative load.

**Why unverifiable**: Tests show OPEN rejects calls (correct). They don't measure the load that *preceded* the opening.

---

### Contract 3: "HALF_OPEN is Safe Recovery Probing"
**Promised**: Controlled, gradual transition back to CLOSED.

**Actual**: A function that fails repeatedly in HALF_OPEN will **never reopen the circuit**. The circuit stays HALF_OPEN indefinitely, each call still executing the retry loop 3 times.

**Why unverifiable**: Test above shows this behavior but passes anyway. There's no test of "what happens after 100 failures in HALF_OPEN"—because the answer is "nothing, the circuit stays HALF_OPEN."

---

### Contract 4: "Exception Type Tells You Why"
**Promised**: The caller can distinguish real failures from circuit protection.

**Actual**: All exceptions are the same. Callers can't tell:
- Real function failure (network timeout)
- Exhausted retries (3 attempts all failed)
- Circuit OPEN (rejected without trying)
- Degraded HALF_OPEN (failed but circuit didn't reopen)

**Why unverifiable**: The exception interface makes no promises about semantic meaning.

---

## Silent Failure in a Dependent System

### Scenario: REST API Gateway

```python
# Downstream service (remote, has latency/failure issues)
def api_call(url):
    return http_get(url, timeout=5)  # 5s timeout

# Your gateway
cb = CircuitBreaker(failure_threshold=5, reset_timeout=30, half_open_max=3)

def gateway(url):
    return cb.execute(api_call, url)
```

### Timeline of Silent Failure

| Time | Event | Load on Downstream |
|------|-------|---|
| T=0s | Downstream times out (5s timeout) | 1 attempt |
| T=6s | Retry 1: timeout (1s backoff + 5s) | 2 attempts total |
| T=13s | Retry 2: timeout (2s backoff + 5s) | 3 attempts total |
| T=22s | Retry 3: timeout (4s backoff + 5s) | 4 attempts total |
| T=22s | **failure_count=1**, circuit still CLOSED | **4 attempts, 22 seconds of load** |
| T=22-130s | Repeat 4 more times | **20 attempts total, 130 seconds of cumulative load** |
| T=130s | **Circuit opens** (failure_count=5) | ✓ Downstream finally gets rest |
| T=160s | Timeout expires, circuit → HALF_OPEN | — |
| T=160s | First HALF_OPEN call: timeout + 1s backoff + timeout + 2s backoff + timeout | **3 more attempts = 13 seconds** |
| T=173s | Still HALF_OPEN (failure does NOT reopen) | **17 attempts total in HALF_OPEN** |
| T=173s+ | Calls keep hitting retry loop in HALF_OPEN | **Downstream hammered again** |
| T=180s | 3 successes finally → CLOSED | — |
| T=180s+ | Back to CLOSED with retry loop active | **Back to 15 attempts per 5 failures** |

### The Silent Failure

**Dependent system expects**:
```
Service times out → after 5 failures, circuit opens → downstream rests
```

**Dependent system gets**:
```
Service times out → 15 attempts over 130 seconds (retry loop = 3× amplification)
→ Circuit finally opens → downstream rests
→ HALF_OPEN starts probing (retry loop STILL ACTIVE)
→ Fails 10 times without reopening (contract violated)
→ Each attempt = 3 retries (3× amplification again)
→ Finally 3 successes → CLOSED
→ Back to retrying everything
```

**Why it's silent**:
- The circuit breaker appears to work (states transition correctly)
- Tests pass
- Exceptions are raised as expected
- **But the dependent system receives 3× the load it should**, hidden inside the retry loop, until the circuit breaker opens
- Then it receives *another round* of 3× load in HALF_OPEN
- The **retry mechanism contradicts the circuit breaker semantics**, and this contradiction is invisible to callers

---

## Summary: The Unverifiable Contract

The code promises:
> "I will protect downstream by opening after threshold failures"

But it actually does:
> "I will attempt threshold × 3 function calls with exponential backoff before opening. Then I will stay HALF_OPEN indefinitely if failures continue, retrying each call 3 times."

**Tests cannot catch this** because they validate state transitions, not the *meaning of state transitions to dependent systems*.
