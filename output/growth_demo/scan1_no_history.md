## STEP 0: Check for prior constraint knowledge

No `.prism-history.md` file detected in current project context. Proceeding with first analysis.

---

## STEP 1: Cook the Lens

## Generated Lens

Map every state transition path through this circuit breaker. For each transition, identify: what lock protects it, what read-modify-write gap exists. Construct three concrete interleavings where concurrent threads corrupt state or produce misleading errors: one exploiting the property that mutates without a lock, one where TOCTOU causes rejection of valid calls, one where the registry's singleton races. Trace exact line numbers. Derive the invariant this implementation silently violates. Output: specific failure modes with reproduction conditions, not hypothetical concerns.

---

## STEP 2: Execute the Lens

### State Transition Map

| Transition | Trigger | Lock Held? | Read-Modify-Write Gap |
|------------|---------|------------|----------------------|
| OPEN → HALF_OPEN | `state` property read | **NO** | Lines 44-47: reads `_state`, then mutates `_state` and `_half_open_calls` without lock |
| HALF_OPEN → CLOSED | `_on_success()` | Yes | Lines 73-77: check-then-act is protected, but the caller's prior state read (line 54) is stale |
| HALF_OPEN → OPEN | `_on_failure()` | Yes | Protected, but races with property mutation at line 46 |
| CLOSED → OPEN | `_on_failure()` | Yes | Protected |

### Concrete Interleaving #1: Property Mutates Without Lock

**Scenario:** Two threads read `state` property simultaneously while timeout expires.

```
Initial: _state = OPEN, recovery_timeout elapsed

T1: line 54  → state = self.state  (enters property getter)
T2: line 54  → state = self.state  (enters property getter)
T1: line 44  → reads _state == OPEN, timeout check passes
T2: line 44  → reads _state == OPEN, timeout check passes
T1: line 46  → _state = HALF_OPEN, _half_open_calls = 0  (NO LOCK!)
T2: line 46  → _state = HALF_OPEN, _half_open_calls = 0  (redundant write)
T1: line 60  → acquires lock, _half_open_calls = 1
T2: line 60  → acquires lock, _half_open_calls = 2  (EXCEEDS LIMIT!)
```

**Result:** `_half_open_calls = 2` when `half_open_max_calls = 1`. Two calls proceed in HALF_OPEN when only one should be allowed.

**Severity:** High — violates core circuit breaker invariant.

---

### Concrete Interleaving #2: TOCTOU Rejects Valid Call

**Scenario:** Thread reads HALF_OPEN, but state transitions to CLOSED before it acquires lock.

```
Initial: _state = HALF_OPEN, _half_open_calls = 1, half_open_max_calls = 1

T1: line 54  → state = self.state, returns HALF_OPEN (local variable)
T2: line 54  → state = self.state, returns HALF_OPEN (local variable)
T1: line 60  → acquires lock, _half_open_calls = 1, proceeds
T1: line 65  → func() succeeds
T1: line 73  → _on_success(), acquires lock
T1: line 75  → _state = CLOSED, _failure_count = 0
T2: line 60  → acquires lock
T2: line 61  → _half_open_calls (1) >= half_open_max_calls (1) → TRUE
T2: line 62  → raises CircuitOpenError("Half-open call limit reached")
```

**Actual state at T2's rejection:** CLOSED (circuit is healthy!)

**Result:** Thread T2 receives "Half-open call limit reached" error when the circuit is actually CLOSED and should accept all calls.

**Severity:** Medium — misleading error, but call would have been rejected anyway during the window. Causes confusion in logs and monitoring.

---

### Concrete Interleaving #3: Registry Singleton Race

**Scenario:** Two threads call `get_instance()` and `get_or_create()` concurrently.

```
Initial: _instance = None, _breakers = {}

T1: get_instance() → line 118: _instance is None? YES
T2: get_instance() → line 118: _instance is None? YES
T1: line 119 → _instance = CircuitBreakerRegistry()
T2: line 119 → _instance = CircuitBreakerRegistry()  (OVERWRITES T1's instance!)
T1: get_or_create("db") → line 122: "db" not in _breakers → creates breaker_a
T2: get_or_create("db") → line 122: "db" not in _breakers → creates breaker_b (OVERWRITES!)
```

**Result:** Two different `CircuitBreaker` instances created for "db". One is lost, any state in it is orphaned. Code using the old instance continues with stale circuit state.

**Severity:** High — violates singleton guarantee, causes split-brain circuit state.

---

### The Silent Invariant Violation

**Claimed Invariant:** "At most `half_open_max_calls` concurrent calls execute in HALF_OPEN state."

**Actual Behavior:** The `_half_open_calls` counter is:
- Incremented under lock (line 60-62)
- Reset in property getter WITHOUT lock (line 47)
- Never decremented when calls complete

The counter can be reset while calls are in-flight, allowing more than `half_open_max_calls` to execute.

---

### Listener Notification Holds Lock — Latency Amplification

```python
def _on_success(self) -> None:
    with self._lock:  # Line 72
        if self._state == State.HALF_OPEN:
            # ...
            self._notify("circuit_closed")  # Line 77 — STILL HOLDING LOCK!
```

If any listener blocks (network call, slow log, deadlock), **all other operations on this circuit breaker freeze**. The lock is held during arbitrary user code execution.

**Severity:** Medium — depends on listener behavior, but violates principle of minimizing lock scope.

---

### Conservation Law

> **This implementation trades correctness for read latency.** The `state` property is designed to be "fast" (no lock acquisition) but this speed comes at the cost of atomic state transitions. The conservation law: *You cannot have both lock-free state reads and consistent state updates.* Every implementation must choose where to sacrifice — this one sacrifices consistency at the OPEN→HALF_OPEN transition boundary.

---

## Findings Table

| Location | What Breaks | Severity | Fixable/Structural |
|----------|-------------|----------|-------------------|
| Lines 44-47 (`state` property) | Mutates `_state` and `_half_open_calls` without lock, races with `_on_success`/`_on_failure` | **High** | Fixable — acquire lock or make property pure and move transition logic |
| Lines 54-62 (`call` HALF_OPEN block) | TOCTOU: reads state without lock, then acts on stale value under lock | **Medium** | Fixable — read and check under same lock acquisition |
| Lines 72-77 (`_on_success`) | `_notify` called while holding lock, blocks all circuit operations | **Medium** | Fixable — copy listeners, release lock, then notify |
| Lines 118-120 (`get_instance`) | Singleton check-then-create race, creates multiple instances | **High** | Fixable — use `threading.Lock()` or `@classmethod` with lazy import |
| Line 122 (`get_or_create`) | Check-then-create race on dict, can create duplicate breakers | **High** | Fixable — use lock or `dict.setdefault` |
| Line 113 (`_breakers` class attr) | Mutable class attribute shared across all instances | **Low** | Fixable — move to `__init__` as instance attribute |

---

```
---
CONSTRAINT NOTE: This analysis maximized concurrency fault detection and state machine integrity.
It did not examine: error handling completeness, timeout value semantics, or API ergonomics.
For deeper analysis: /prism-full | For meta-analysis: /prism-reflect
```
