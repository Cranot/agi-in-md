# Level 8: Retry + Circuit Breaker (Generative Diagnostic)

## Concrete Bugs

**Bug 1 (Critical)**: No HALF_OPEN → OPEN path when failures continue  
When `_on_failure()` is called in HALF_OPEN state, the code increments `_failure_count` but never reopens the circuit. The circuit stays in HALF_OPEN state indefinitely if the service remains broken. The state machine is incomplete.

**Bug 2 (Critical)**: Retry logic is unconditionally baked into the state machine  
`execute()` always calls `_retry_with_backoff()` regardless of state. In OPEN state, the code returns early, so retries don't happen, but the design conflates "should I call this function?" with "how many times should I retry?" These are separate concerns.

**Bug 3 (Moderate)**: No mechanism to distinguish transient vs. permanent failures  
All exceptions increment `_failure_count` equally. A 404 (endpoint doesn't exist) and a timeout (service is down) both count as failures. Only the caller knows which should open the circuit, but the circuit breaker doesn't provide a classification interface.

**Bug 4 (Moderate)**: Concurrency creates indeterminacy in HALF_OPEN  
If multiple threads call `execute()` during HALF_OPEN, each can increment `_success_count`. The "controlled probing" phase becomes uncontrolled—you might have 10 concurrent threads testing the service, not 3.

---

## Shadow Code (Required Compensating Patterns)

### Pattern 1: Outer-layer retry with jitter
```python
def call_with_outer_safety(circuit, fn, max_attempts=5):
    """Caller must implement retry OUTSIDE circuit breaker"""
    for attempt in range(max_attempts):
        try:
            return circuit.execute(fn)
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            # Exponential backoff with jitter
            delay = (2 ** attempt) + random.random() * 10
            time.sleep(delay)
            # If circuit is stuck in HALF_OPEN and keeps failing,
            # outer layer eventually gives up
```
**Why**: Bug 1 means the circuit never reopens if failures continue in HALF_OPEN. Without outer backoff, the code enters a tight failure loop. Callers must implement their own backoff as a safety net.

### Pattern 2: Idempotency key wrapper
```python
class IdempotentCircuitBreaker:
    def __init__(self, circuit):
        self.circuit = circuit
        self.completed_calls = {}
    
    def execute(self, fn, idempotency_key, *args, **kwargs):
        if idempotency_key in self.completed_calls:
            return self.completed_calls[idempotency_key]
        
        result = self.circuit.execute(fn, *args, **kwargs)
        self.completed_calls[idempotency_key] = result
        return result
```
**Why**: Bug 2 means `execute()` calls `_retry_with_backoff()`, which calls `fn()` multiple times. If `fn` has side effects (payment, message, etc.), retries cause duplicates. Caller must add idempotency layer that the circuit breaker should own.

### Pattern 3: State inspection via private access
```python
def is_circuit_probing():
    """Caller forced to use private variables"""
    return circuit._state == CircuitBreaker.HALF_OPEN

def circuit_health():
    """No public API for observability"""
    return (circuit._failure_count, 
            circuit._failure_threshold,
            circuit._last_failure_time)
```
**Why**: No public state API. Callers who need to know "is the circuit currently testing the service?" must directly access private variables, violating encapsulation.

### Pattern 4: Failure classification pre-filter
```python
def classify_and_call(circuit, fn, *args, **kwargs):
    """Caller must pre-filter which exceptions count"""
    try:
        return circuit.execute(fn, *args, **kwargs)
    except HttpError as e:
        if e.code == 404:
            # Endpoint doesn't exist, but service is UP
            # We WANT this to succeed and NOT count as failure
            # But it already incremented _failure_count
            # Too late. Circuit breaker treats it as service failure.
            raise
        elif e.code in (500, 502, 503):
            # Actual service failure; circuit should open
            raise
```
**Why**: Bug 3. All exceptions are treated identically. Caller must pre-wrap the function to catch and decide which exceptions are "real failures" vs. "service-is-actually-fine failures." But once the exception is raised from the wrapped function, the circuit breaker has already counted it.

### Pattern 5: Serialize HALF_OPEN to prevent concurrent probes
```python
class SerializedCircuitBreaker:
    def __init__(self, circuit):
        self.circuit = circuit
        self.half_open_lock = threading.Lock()
    
    def execute(self, fn, *args, **kwargs):
        if self.circuit._state == CircuitBreaker.HALF_OPEN:
            with self.half_open_lock:
                # Only one thread probes at a time
                return self.circuit.execute(fn, *args, **kwargs)
        return self.circuit.execute(fn, *args, **kwargs)
```
**Why**: Bug 4. In HALF_OPEN, multiple concurrent threads can each succeed and increment the shared `_success_count`, but the lock ensures the "controlled probe phase" is actually controlled.

---

## Which patterns persist if you fix the bugs?

**Fix Bug 1**: Add `if self._state == HALF_OPEN: self._state = OPEN` in `_on_failure()`  
→ Pattern 1 (outer retry) **PARTIALLY PERSISTS**. Circuit now reopens correctly, but there's still a window where failures accumulate before the circuit opens. Outer backoff still needed for safety.

**Fix Bug 2**: Decouple retry logic from state machine  
→ Pattern 2 (idempotency key) **PERSISTS ENTIRELY**. Retry happens at every execution layer. Whether it's internal or external, the caller can't control call multiplicity.

**Fix Bug 3**: Add exception classification in `__init__`  
→ Pattern 5 (failure classification) **PERSISTS ENTIRELY**. Only the caller knows which exceptions indicate "service is down" vs. "this specific request failed." Exception semantics are domain-specific (HTTP vs. gRPC vs. database).

**Fix Bug 4**: Add lock in HALF_OPEN  
→ Pattern 4 (serialization) **GONE**. Serialization is now internal to the circuit breaker.

**All code**:  
→ Pattern 3 (state inspection) **PERSISTS ENTIRELY**. No public API; callers needing observability have no alternative.

---

## What this reveals: The three hidden properties

**Property 1 — State abstraction is incomplete**  
You can only OBSERVE state (CLOSED/OPEN/HALF_OPEN), but you cannot EXPLAIN it. The caller sees "circuit is HALF_OPEN" but doesn't know:
- How long will it probe for?
- How many successes does it need?
- When did the last failure happen?
- Are concurrent threads currently testing?

The state is opaque by design, forcing callers to either guess or access private variables. This reveals that the circuit breaker treats state as implementation detail, not as a contract with its users.

**Property 2 — Retry and circuit-breaking are fundamentally different operations, but this code treats them as one**  
- **Retry** = "this call failed transiently, try again soon" (transient failure handling)
- **Circuit break** = "this service is down, stop trying for a while" (cascading failure prevention)

By embedding retry inside the state machine, the code obscures which operation is happening. If a caller sees an exception from `execute()`, they can't tell if it's "we retried 3 times and all failed" or "circuit is open and we're not trying." Different operations need different caller handling, but they're bundled here.

**Property 3 — The circuit breaker assumes all exceptions have the same severity**  
In the real world:
- HTTP 404 = "service is up, endpoint doesn't exist" (don't open circuit)
- HTTP 503 = "service is down" (do open circuit)
- Timeout = "service is not responding" (do open circuit)
- SSL verification error = "configuration error" (don't open circuit, would never recover)

But this code treats all exceptions as "service failure." The circuit breaker has no way to classify them. This reveals a fundamental assumption: **the circuit breaker believes its caller will only invoke it on operations where ALL exceptions indicate the service is broken.** This is false in practice (HTTP, multi-operation workflows, etc.). The boundary is at the exception classification layer, not at the circuit breaker layer.

---

## The architectural boundary this reveals

This code was designed for **a world where:**
- Functions are idempotent (safe to retry)
- All exceptions mean "service is unavailable" (not "this specific request is invalid")
- Callers don't need real-time state observability
- There's a clear separation between "transient" and "permanent" failures that the code can be told about

**But it's being used in a world where:**
- Functions have side effects (payments, state mutations)
- Most modern services return semantically meaningful error codes (404 ≠ 503)
- Production systems need to know if the circuit is currently probing
- Different failure types need different handling strategies (retry 404? No. Retry 503? Maybe.)

The shadow code patterns show where callers are patching these gaps. The patterns that persist even after fixing bugs (idempotency, failure classification, state observability) reveal the **architectural contract this code was never designed to support**, but that users believe it should.
