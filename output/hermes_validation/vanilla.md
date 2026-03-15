## Circuit Breaker Review

### Critical Bugs

**1. Thread-unsafe state property** (line 41-48)
```python
@property
def state(self) -> State:
    if self._state == State.OPEN:
        if self._last_failure_time and (...):
            self._state = State.HALF_OPEN  # Modifies without lock!
```
The `state` property reads and writes `self._state` without acquiring `self._lock`. Multiple threads could simultaneously transition to HALF_OPEN.

**2. TOCTOU race in `call()`** (line 52-62)
```python
state = self.state  # Thread A reads HALF_OPEN
# ... context switch ...
# Thread B reads HALF_OPEN, acquires lock, increments _half_open_calls
if state == State.HALF_OPEN:  # Thread A uses stale state
    with self._lock:
        if self._half_open_calls >= self.half_open_max_calls:
```
The state can change between reading it and acting on it. A thread could be in the HALF_OPEN block while the circuit has already transitioned to OPEN or CLOSED.

**3. Registry race condition** (line 118-120)
```python
def get_or_create(self, name: str, **kwargs) -> CircuitBreaker:
    if name not in self._breakers:  # Not thread-safe
        self._breakers[name] = CircuitBreaker(**kwargs)
```
Two threads could create duplicate breakers for the same name.

### Design Issues

**4. Class-level mutable default** (line 106)
```python
_breakers: dict[str, CircuitBreaker] = {}  # Shared across all instances!
```
This dict is shared if someone bypasses the singleton. Should be initialized in `__init__`.

**5. Property with side effects**
The `state` property mutates state, which violates least-surprise principle. Consider a `_transition_state()` method instead.

**6. Silent exception swallowing** (line 97-100)
```python
except Exception:
    pass  # Errors go to /dev/null
```
At minimum, log these failures.

**7. Missing reset in `_on_success()`**
When transitioning HALF_OPEN → CLOSED, `_half_open_calls` isn't reset (only `reset()` clears it). Could cause stale counter issues.

### Missing Features

- **Context manager support** (`__enter__`/`__exit__`) for `with breaker:` pattern
- **`__call__` method** for decorator usage `@breaker`
- **Async support** for modern Python apps

### Suggested Fix for Core Thread Safety

```python
@property
def state(self) -> State:
    with self._lock:
        if self._state == State.OPEN:
            if self._last_failure_time and (
                time.time() - self._last_failure_time >= self.recovery_timeout
            ):
                self._state = State.HALF_OPEN
                self._half_open_calls = 0
        return self._state
```

Or better, make state transitions explicit methods rather than hiding them in a property.
