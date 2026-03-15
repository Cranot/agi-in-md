## STEP 0: Check for prior constraint knowledge

No `.prism-history.md` file found in the current project directory. Proceeding with fresh analysis.

---

## STEP 1: Cook the Lens

**Observations from artifact:**
- State machine with three states (CLOSED, OPEN, HALF_OPEN) and concurrent access
- A `state` property that performs hidden writes during reads (impure getter)
- Class-level `_breakers` dict on the Registry (shared across instances)
- Lock held during listener notification (re-entrancy risk)
- `_success_count` tracked but never consumed

**Generated Lens:**

> Map every state transition with its synchronization: which lock is held, what writes occur. The `state` property is impure — it mutates `_state` and `_half_open_calls` during a read without holding the lock. Construct the exact interleaving where this allows more than `half_open_max_calls` concurrent executions. The Registry's `_breakers` is class-level — trace cross-test contamination and the singleton creation race. Listeners are invoked under lock — construct the callback-that-calls-back deadlock. For each bug: line numbers, thread interleaving, observable failure. Derive the conservation law this implementation encodes.

---

## STEP 2: Execute the Lens

### State Machine Map

| From | To | Trigger | Lock Held? | Writes |
|------|-----|---------|------------|--------|
| CLOSED | OPEN | `_failure_count >= threshold` | Yes (in `_on_failure`) | `_state`, `_last_failure_time` |
| OPEN | HALF_OPEN | `state` property (timeout elapsed) | **NO** | `_state`, `_half_open_calls` |
| HALF_OPEN | CLOSED | Success in half-open | Yes (in `_on_success`) | `_state`, `_failure_count`, `_success_count` |
| HALF_OPEN | OPEN | Failure in half-open | Yes (in `_on_failure`) | `_state`, `_last_failure_time` |

**Critical finding:** The OPEN → HALF_OPEN transition occurs in the `state` property **without holding the lock**, while all other transitions hold the lock.

---

### Bug 1: Impure Property Causes Race on `_half_open_calls`

**Location:** Lines 43-49

```python
@property
def state(self) -> State:
    if self._state == State.OPEN:
        if self._last_failure_time and (
            time.time() - self._last_failure_time >= self.recovery_timeout
        ):
            self._state = State.HALF_OPEN        # WRITE WITHOUT LOCK
            self._half_open_calls = 0            # WRITE WITHOUT LOCK
    return self._state
```

**The invariant violation:** `_half_open_calls` is modified under `_lock` in `call()` (line 63) and `reset()` (line 113), but modified WITHOUT `_lock` in the `state` property.

**Reproduction scenario (with `half_open_max_calls=1`):**

```
T=0:     Circuit is OPEN, timeout has elapsed
T=1:     Thread A: calls call(), state property returns HALF_OPEN, sets _half_open_calls=0
T=2:     Thread A: acquires _lock, increments _half_open_calls to 1, releases _lock
T=3:     Thread A: begins executing func (slow operation)
T=4:     Thread B: calls call(), state property executes AGAIN
         - Sees _state == HALF_OPEN (not OPEN), skips transition block
         - Returns HALF_OPEN
T=5:     Thread B: acquires _lock, sees _half_open_calls=1 >= 1, rejected ✓
         
         BUT alternative path:
T=4':    Thread A's func FAILS, _on_failure() transitions HALF_OPEN → OPEN
T=5':    Thread C: calls call(), state property sees OPEN, timeout freshly elapsed
         - Sets _half_open_calls = 0  ← RACES WITH THREAD A's INCREMENT
T=6':    Thread A: still in _on_failure, holding lock, about to set _state=OPEN
         Thread C: has reset _half_open_calls to 0
         
Result: _half_open_calls corrupted, state machine integrity lost
```

**Observable failure:** With `half_open_max_calls=1`, two threads can both execute their functions during the same half-open window because the counter gets reset mid-flight.

**Severity:** High — violates core circuit breaker guarantee
**Fixable:** Yes — move the OPEN→HALF_OPEN transition into a locked section, or use atomic compare-and-swap semantics

---

### Bug 2: Listener Deadlock via Re-entrant Callback

**Location:** Lines 88-93, called from lines 76 and 91

```python
def _on_failure(self) -> None:
    with self._lock:                    # LOCK ACQUIRED
        ...
        self._notify("circuit_opened")  # LISTENER CALLED UNDER LOCK

def _notify(self, event: str) -> None:
    for listener in self._listeners:
        try:
            listener(event, self)       # IF LISTENER CALLS cb.call(), DEADLOCK
        except Exception:
            pass
```

**Reproduction scenario:**

```python
def my_listener(event, breaker):
    if event == "circuit_opened":
        # Try to send alert through the same breaker
        breaker.call(send_alert, "Circuit opened!")  # DEADLOCK

cb = CircuitBreaker()
cb.add_listener(my_listener)
cb.call(failing_function)  # Triggers failure → _on_failure → _notify → my_listener → cb.call → blocks on _lock
```

**Observable failure:** Application hangs. Thread dump shows Thread 1 holding `_lock` and blocked trying to acquire `_lock`.

**Severity:** High — causes production outages
**Fixable:** Yes — release lock before notifying listeners, or use re-entrant lock (`threading.RLock`), or document that listeners must not call back

---

### Bug 3: Class-Level `_breakers` Dict Causes Cross-Test Contamination

**Location:** Line 117

```python
class CircuitBreakerRegistry:
    _instance = None
    _breakers: dict[str, CircuitBreaker] = {}  # CLASS ATTRIBUTE, NOT INSTANCE
```

**Reproduction scenario:**

```python
# test_a.py
def test_database_breaker():
    registry = CircuitBreakerRegistry.get_instance()
    breaker = registry.get_or_create("database")
    # Test runs, breaker state becomes OPEN

# test_b.py (runs after test_a in same process)
def test_fresh_registry():
    # Developer expects a fresh registry
    CircuitBreakerRegistry._instance = None  # Reset singleton
    registry = CircuitBreakerRegistry.get_instance()
    breaker = registry.get_or_create("database")
    # BUG: breaker already exists in _breakers from test_a!
    # Its state is still OPEN, test fails mysteriously
```

**Observable failure:** Tests pass in isolation but fail when run together. State bleeds between test suites.

**Severity:** Medium — causes flaky tests, production issue if Registry is ever re-instantiated
**Fixable:** Yes — move `_breakers = {}` into `__init__`

---

### Bug 4: Singleton Creation Race

**Location:** Lines 120-123

```python
@classmethod
def get_instance(cls) -> "CircuitBreakerRegistry":
    if cls._instance is None:      # CHECK
        cls._instance = cls()      # CREATE (not atomic with check)
    return cls._instance
```

**Reproduction scenario:**

```
Thread A: calls get_instance(), sees _instance is None
Thread B: calls get_instance(), sees _instance is None (before A creates)
Thread A: creates instance #1, assigns to _instance
Thread B: creates instance #2, assigns to _instance (overwrites #1)
Thread A: returns instance #1 (now orphaned)
Thread B: returns instance #2

Result: Two different registry instances exist. Breakers registered in #1 
        are invisible to code holding #2.
```

**Observable failure:** Circuit breakers created in one thread are not found in another. Inconsistent behavior across the application.

**Severity:** Medium — rare but catastrophic when it occurs
**Fixable:** Yes — use `threading.Lock()` around singleton creation, or use module-level singleton pattern

---

### Bug 5: `_success_count` is Dead Code

**Location:** Lines 77-78

```python
def _on_success(self) -> None:
    with self._lock:
        if self._state == State.HALF_OPEN:
            ...
        self._success_count += 1  # Incremented but NEVER READ
```

The `_success_count` field is:
- Initialized to 0 (line 31)
- Reset to 0 when closing from half-open (line 75)
- Incremented on every success (line 78)
- **Never read anywhere**

**Observable failure:** None directly, but indicates incomplete implementation. A maintenance developer might assume this tracks something useful.

**Severity:** Low — code smell, not a runtime bug
**Fixable:** Yes — either remove it or implement the success-based recovery logic it suggests

---

### Bug 6: Silent Exception Swallowing in Listeners

**Location:** Lines 89-92

```python
def _notify(self, event: str) -> None:
    for listener in self._listeners:
        try:
            listener(event, self)
        except Exception:
            pass  # Completely silent
```

**Observable failure:** Listener has a bug (e.g., typo in logging code). Exception is swallowed. Developer has no idea their monitoring/alerting is broken until they investigate why no alerts are firing.

**Severity:** Low-Medium — masks integration bugs
**Fixable:** Yes — at minimum, log the exception; better, provide configurable error handler

---

### Conservation Law Derived

**The Circuit Breaker Conservation Law:**

> In any concurrent circuit breaker, you must choose one:
> 1. **Hold lock for entire decision+action** — safe but limits throughput
> 2. **Accept stale decisions** — high throughput but allows calls that "should" be blocked
> 
> This implementation attempts both: it holds locks for some transitions but not the critical OPEN→HALF_OPEN transition. The result is neither fully safe nor fully performant — it has the latency of locking with the races of lock-free code.

The persistent trade-off: **You cannot have both perfect state consistency and zero contention.** Any fix will either add more locking (slower) or explicitly accept that `half_open_max_calls` is advisory, not guaranteed.

---

## Findings Table

| # | Location | What Breaks | Severity | Fixable? |
|---|----------|-------------|----------|----------|
| 1 | Lines 43-49 (`state` property) | Impure getter modifies `_half_open_calls` without lock, allowing more concurrent half-open calls than configured limit | **High** | Yes — move transition to locked method |
| 2 | Lines 88-93 (`_notify` under lock) | Listeners that call back into circuit breaker cause deadlock | **High** | Yes — release lock before notify, or use RLock |
| 3 | Line 117 (`_breakers` class attr) | Class-level dict causes state to leak between test runs and across re-instantiations | **Medium** | Yes — move to `__init__` |
| 4 | Lines 120-123 (singleton) | Check-then-create race allows two instances, orphaning breakers | **Medium** | Yes — add lock or use module-level singleton |
| 5 | Lines 77-78 (`_success_count`) | Dead code — tracked but never consumed | **Low** | Yes — remove or implement |
| 6 | Lines 89-92 (exception swallow) | Listener failures are silently hidden, masking integration bugs | **Low-Medium** | Yes — log or configurable handler |

---

```
CONSTRAINT NOTE: This analysis maximized concurrent state machine integrity and lock discipline.
It did not examine: performance characteristics under load, memory leak patterns in long-running processes.
For deeper analysis: /prism-full | For meta-analysis: /prism-reflect
```
