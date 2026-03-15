# Full Prism Analysis: Circuit Breaker Implementation

## PHASE 1: Cook the Pipeline

I've studied the artifact — a threaded circuit breaker with state machine logic, time-based transitions, a property with side effects, and a global singleton registry. Here's the custom pipeline:

### Generated Pipeline

| Pass | Lens Name | Role |
|------|-----------|------|
| 1 | **Concurrency Archaeology** | Excavate every threading assumption. Map where locks are held vs. where shared state escapes. Find the races. |
| 2 | **State Machine Formalist** | Build a complete transition table. Identify unreachable states, illegal transitions, and internal inconsistencies after each transition. |
| 3 | **Temporal Adversary** | Attack every time-based assumption. Zero timeouts, clock skew, rapid calls, stale timestamps. Predict corruption paths. |
| 4 | **Property/Invariant Hunter** | Find every implicit invariant. The `state` property has hidden mutations — trace the damage. Check if public methods preserve invariants. |
| 5 | **Integration Corruption** | The registry uses class-level mutable state. Trace multi-import scenarios, concurrent modification, listener list mutation during iteration. |

---

## PHASE 2: Execute the Pipeline

---

### PASS 1: Concurrency Archaeology

**Executing:** Find every threading assumption, map lock boundaries, identify races.

**Analysis:**

The `state` property reads and writes `self._state` without holding `self._lock`. This is the primary corruption vector.

```
Thread A: calls self.state (OPEN detected, timeout elapsed)
Thread A: sets self._state = State.HALF_OPEN  ← no lock
Thread B: calls self.state (OPEN detected)  
Thread B: sets self._state = State.HALF_OPEN  ← races with A
Thread A: sets self._half_open_calls = 0      ← no lock
Thread B: sets self._half_open_calls = 0      ← resets A's increment
```

In `call()`, the HALF_OPEN gate uses the lock correctly, but the initial `state = self.state` call happens outside the lock. A thread can see `HALF_OPEN`, get preempted, another thread transitions to `OPEN`, and the first thread proceeds with stale state.

**Race 1:** `state` property mutates `_state` and `_half_open_calls` without lock — TOCTOU window between state check and lock acquisition.

**Race 2:** `_notify()` is called inside `_lock` in `_on_failure`, but iterates over `_listeners` which is modified by `add_listener()` / `remove_listener()` without the lock. Concurrent modification during iteration.

**Race 3:** In `call()`, if state is `CLOSED`, no lock is acquired. `_on_success()` increments `_success_count` inside lock, but the decision path for CLOSED state touches nothing locked until success/failure. The `_failure_count` read in `_on_failure` races with other failures.

**Construction — Race Scenario:**
```
Initial: CLOSED, failure_count=4
Thread A: calls func(), it fails
Thread A: in _on_failure, about to acquire lock
Thread B: calls func(), it fails  
Thread B: in _on_failure, about to acquire lock
Thread A: acquires lock, failure_count=5, triggers OPEN
Thread B: acquires lock, failure_count=6, already OPEN (no double-notify)
Result: Two failures counted, one recovery timeout started correctly
BUT: If Thread B's failure happened BEFORE Thread A's lock release...
```

Actually worse: `_last_failure_time` gets set twice. The second thread overwrites with a later time, extending the recovery window invisibly.

---

### PASS 2: State Machine Formalist

**Executing:** Build complete transition table, find illegal states and inconsistencies.

**Analysis:**

**Legal States:** CLOSED, OPEN, HALF_OPEN

**Transition Table (as coded):**

| From | Event | To | Guard | Invariant Check |
|------|-------|-----|-------|-----------------|
| CLOSED | failure_count >= threshold | OPEN | None | ✗ `_success_count` NOT reset |
| OPEN | timeout elapsed | HALF_OPEN | Via `state` property | ✗ `_failure_count` preserved |
| HALF_OPEN | success | CLOSED | None | ✓ counters reset |
| HALF_OPEN | failure | OPEN | None | ✗ `_failure_count` NOT reset |
| HALF_OPEN | half_open_calls >= max | (rejected) | None | N/A |
| Any | reset() | CLOSED | Manual | ✓ all reset |

**Inconsistency 1:** When CLOSED → OPEN, `_success_count` is NOT reset. If circuit closes again (HALF_OPEN → CLOSED), it resets to 0, but if it stays OPEN, `_success_count` retains stale value. On transition OPEN → HALF_OPEN, `_success_count` is never touched. What does `_success_count` mean in HALF_OPEN? Undefined.

**Inconsistency 2:** When HALF_OPEN → OPEN (failure in half-open), `_failure_count` is NOT reset. It retains the count from before. If threshold is 5 and we had 5 failures, `_failure_count` is now 5+. When we eventually transition HALF_OPEN → CLOSED, it resets. But if we're tracking failure patterns across recovery attempts, this count is polluted.

**Inconsistency 3:** `_half_open_calls` is set to 0 in TWO places:
- `state` property when transitioning OPEN → HALF_OPEN (no lock)
- `reset()` method (with lock)

But it's NOT reset when HALF_OPEN → OPEN (failure). So if `half_open_max_calls=3`, call 1 fails, we go OPEN. Next recovery: `_half_open_calls` is... set to 0 by `state` property. OK, but what if the property was called multiple times during OPEN? Race condition resets it repeatedly.

**Inconsistency 4:** `_last_failure_time` is set on every failure. In HALF_OPEN → OPEN transition, it's set. Good. But it's NEVER cleared on any success path. So `_last_failure_time` always reflects the most recent failure, even after recovery. The `state` property checks `time.time() - self._last_failure_time >= self.recovery_timeout` — if a failure happened 60s ago, circuit was OPEN, then CLOSED, then 3 successes... `_last_failure_time` is still 60s ago. If we get 5 rapid failures now, we go OPEN, but `_last_failure_time` is already 60s old, so `state` immediately returns HALF_OPEN!

**This is catastrophic.** The recovery timeout check uses a stale timestamp from a PREVIOUS failure epoch.

---

### PASS 3: Temporal Adversary

**Executing:** Attack every time-based assumption.

**Analysis:**

**Attack 1: `recovery_timeout = 0`**
- `state` property: `time.time() - self._last_failure_time >= 0` is always true if `_last_failure_time` is set.
- Circuit becomes HALF_OPEN immediately after OPEN.
- But `_half_open_calls` is incremented in HALF_OPEN path. If `half_open_max_calls=1`, one call proceeds.
- Result: Circuit never truly "blocks" — it becomes a passthrough with extra steps.

**Attack 2: `recovery_timeout < 0`**
- Same as above. `>= -30` is always true.
- No validation on constructor args.

**Attack 3: `time.time()` called in rapid succession**
- `_last_failure_time = time.time()` called in `_on_failure` inside lock.
- `state` property calls `time.time()` WITHOUT lock.
- Between these calls, clock can advance (NTP sync, suspend/resume).
- If system clock jumps BACKWARD (NTP step), `time.time() - self._last_failure_time` could be negative, which is `< recovery_timeout`, so circuit stays OPEN forever until clock catches up.
- If system clock jumps FORWARD, circuit transitions to HALF_OPEN prematurely.

**Attack 4: Stale `_last_failure_time` (from Pass 2)**
```
T=0:   5 failures, circuit OPEN, _last_failure_time=0
T=30:  state returns HALF_OPEN (timeout elapsed)
T=31:  1 success, circuit CLOSED, _failure_count=0
T=35:  5 new failures, circuit OPEN, _last_failure_time=35
       BUT WAIT: _last_failure_time was SET to 35, so timeout check is fresh.
```
Actually I need to re-check Pass 2's finding. Let me trace again:
- `_last_failure_time` is set in `_on_failure()` on every failure.
- It's cleared to `None` in `reset()`.
- It's NOT cleared in `_on_success()`.

So after CLOSED → OPEN → HALF_OPEN → CLOSED, `_last_failure_time` still holds the timestamp from the OPEN transition failure. Then new failures overwrite it. The check `time.time() - self._last_failure_time >= self.recovery_timeout` uses the FRESH failure time, not stale.

**Retraction:** Pass 2's "catastrophic" finding about stale `_last_failure_time` is overstated. The timestamp IS updated on new failures. However, the finding about `_last_failure_time` not being cleared on success is still relevant for observability/logging — it's confusing but not fatal.

**Attack 5: `_last_failure_time = None` check**
```python
if self._last_failure_time and (
    time.time() - self._last_failure_time >= self.recovery_timeout
):
```
If `_last_failure_time = 0.0` (failure at epoch), the `and` short-circuits because `0.0` is falsy. Circuit stays OPEN forever. This is unlikely in practice (year 1970) but a real bug.

**Attack 6: Half-open call timeout**
- In HALF_OPEN, if `func()` takes longer than `recovery_timeout`, another thread calling `state` will see OPEN → HALF_OPEN transition (timeout elapsed again).
- The first thread is still inside `func()`.
- `_half_open_calls` was incremented. Now `state` resets it to 0.
- Second thread enters HALF_OPEN, increments `_half_open_calls`.
- Two threads executing "single allowed" half-open call.
- **This is a real concurrency bug.**

---

### PASS 4: Property/Invariant Hunter

**Executing:** Find implicit invariants, trace property side-effect damage.

**Analysis:**

**Invariant 1:** " `_state` is only modified under `_lock`"
- **VIOLATED** by `state` property which modifies `_state` and `_half_open_calls` without lock.

**Invariant 2:** " `_failure_count` reflects failures since last CLOSED entry"
- **VIOLATED** when HALF_OPEN → OPEN (failure) preserves `_failure_count`. Next CLOSED entry resets it, but the count in OPEN state is semantically ambiguous.

**Invariant 3:** " `_half_open_calls` is 0 when not in HALF_OPEN"
- **VIOLATED** in `call()`. If state is HALF_OPEN, we increment `_half_open_calls`. Then `func()` succeeds, `_on_success()` is called, which changes `_state` to CLOSED but does NOT reset `_half_open_calls`. It stays at 1 (or higher).
- Next time we enter HALF_OPEN, `_half_open_calls` is reset to 0 by `state` property. But what if `state` property is not called? What if someone reads `_half_open_calls` directly for monitoring?

**Invariant 4:** "Listeners are called with consistent circuit state"
- **VIOLATED** because `_notify` is called inside `_lock`, but by the time listener executes (even synchronously), another thread may have changed state. The listener receives `self` and can read `self.state`, which may have changed.

**The `state` property is a mutation bomb:**
```python
@property
def state(self) -> State:
    if self._state == State.OPEN:
        if self._last_failure_time and (...):
            self._state = State.HALF_OPEN      # MUTATION
            self._half_open_calls = 0          # MUTATION
    return self._state
```

Every read of `state` can mutate object state. This violates the principle that property access should be idempotent. Callers who inspect `state` for logging, monitoring, or debugging are unknowingly triggering state transitions. If monitoring code polls `state` every second, it keeps resetting `_half_open_calls` to 0, preventing any half-open call from ever succeeding.

**Construction — Monitoring Death Spiral:**
```
T=0: Circuit OPEN, _last_failure_time=0, recovery_timeout=30
T=31: Monitoring polls state → returns HALF_OPEN, sets _half_open_calls=0
T=31.001: Real call comes in, state=HALF_OPEN, increments _half_open_calls=1
T=32: Monitoring polls state → returns HALF_OPEN, sets _half_open_calls=0
T=32.001: Real call's func() returns success, _on_success() called
T=32.002: Circuit CLOSED, _half_open_calls=1 (not reset)
```
In this case it works out. But:
```
T=31: Monitoring polls state → HALF_OPEN, _half_open_calls=0
T=31.5: Real call enters, _half_open_calls=1, func() executing
T=32: Monitoring polls state → HALF_OPEN, _half_open_calls=0 ← RESETS IT
T=32.5: Another real call enters, _half_open_calls=1 ← ALLOWED, should have been blocked
```
The monitoring poll reset the counter, allowing a second call through.

---

### PASS 5: Integration Corruption

**Executing:** Attack singleton pattern, class-level mutable state, listener iteration.

**Analysis:**

**Bug 1: Class-level mutable default**
```python
class CircuitBreakerRegistry:
    _breakers: dict[str, CircuitBreaker] = {}
```
This is a CLASS attribute, not an instance attribute. If multiple `CircuitBreakerRegistry` instances are created (bypassing `get_instance()`), they ALL share the same `_breakers` dict.

But `get_instance()` returns a singleton via `_instance` class variable, so in practice, only one instance exists... unless:

**Bug 2: Singleton is not thread-safe**
```python
@classmethod
def get_instance(cls) -> "CircuitBreakerRegistry":
    if cls._instance is None:
        cls._instance = cls()
    return cls._instance
```
Two threads can both see `_instance is None`, both create instances, both assign to `_instance`. One instance is orphaned but its `_breakers` mutations affect the shared dict. Actually wait — `_breakers` is a class attribute, so both instances share it. The orphaned instance's mutations would still affect the shared dict.

But the REAL problem: `get_or_create` is not atomic.
```python
def get_or_create(self, name: str, **kwargs) -> CircuitBreaker:
    if name not in self._breakers:
        self._breakers[name] = CircuitBreaker(**kwargs)
    return self._breakers[name]
```
Two threads both call `get_or_create("db")`. Both see `"db" not in self._breakers`. Both create `CircuitBreaker()` instances. One overwrites the other. The loser circuit breaker is orphaned — any state it held is lost. Callers who cached a reference to it are now operating on a circuit breaker not in the registry.

**Bug 3: `remove()` during concurrent calls**
```python
def remove(self, name: str) -> None:
    self._breakers.pop(name, None)
```
If thread A is inside `breaker.call()` and thread B calls `registry.remove("db")`, the breaker is removed from registry but thread A continues executing. If thread B then calls `get_or_create("db", **different_kwargs)`, a NEW breaker is created. Now two breakers exist for "db" — the one thread A is using (orphaned) and the new one. They maintain separate state.

**Bug 4: Listener list mutation during iteration**
```python
def _notify(self, event: str) -> None:
    for listener in self._listeners:
        try:
            listener(event, self)
        except Exception:
            pass
```
If a listener calls `remove_listener()` (on itself or another listener), Python's list modification during iteration causes:
- If removing self: iteration continues, but indices shift. Next listener may be skipped.
- If removing a later listener: RuntimeError or silent skip depending on timing.

If a listener calls `add_listener()`, the new listener may or may not be called in this iteration (undefined behavior).

**Bug 5: Exception swallowing in listeners**
```python
except Exception:
    pass
```
All listener exceptions are silently swallowed. If a listener has a bug (e.g., logging fails due to disk full), no one knows. The circuit breaker appears to work but monitoring/alerting is broken.

---

## Final Findings

### Conservation Law

**"State transitions must be atomic with respect to the lock."**

Every single critical bug in this code traces back to the same root: the `state` property performs state transitions outside the lock, and multiple code paths read/mutate shared state without coordination. The lock exists but is bypassed by the property accessor. All implementations of circuit breaker must either: (a) hold the lock for ALL state reads and writes, or (b) use lock-free atomic primitives. Mixing locked and unlocked access to the same variables is structurally unsound.

### Findings Table

| # | Location | What Breaks | Severity | Fixable? |
|---|----------|-------------|----------|----------|
| 1 | `state` property | Mutates `_state` and `_half_open_calls` without `_lock`. Races with all other state transitions. | **Critical** | Yes — move transition logic into locked method, make property read-only |
| 2 | `call()` initial state check | Reads `self.state` outside lock, then acts on it. TOCTOU race — state can change before lock acquisition. | **Critical** | Yes — acquire lock before reading state |
| 3 | `state` property idempotency | Reading `state` for monitoring resets `_half_open_calls`, allowing extra half-open calls | **High** | Yes — separate transition logic from accessor |
| 4 | `_last_failure_time = 0.0` edge case | If failure occurs at Unix epoch, `if self._last_failure_time` is falsy, circuit never transitions to HALF_OPEN | **Medium** | Yes — use `is not None` check |
| 5 | Half-open call racing timeout | If half-open call takes longer than `recovery_timeout`, another thread can re-trigger HALF_OPEN transition, allowing parallel half-open calls | **High** | Yes — track call start time, don't reset mid-call |
| 6 | `CircuitBreakerRegistry.get_instance()` | Not thread-safe. Two threads can create instances. | **Medium** | Yes — use threading.Lock or `__new__` |
| 7 | `get_or_create()` | Not atomic. Two threads can create duplicate breakers for same name, one is orphaned. | **High** | Yes — use lock or `setdefault` |
| 8 | `remove()` during active calls | Orphans in-flight calls, creates duplicate breakers on re-create. | **Medium** | Yes — reference counting or mark-and-sweep |
| 9 | `_notify()` listener iteration | Listeners can mutate `_listeners` list during iteration. Skips listeners or raises RuntimeError. | **Medium** | Yes — iterate over copy: `for listener in list(self._listeners)` |
| 10 | Listener exception swallowing | Silent failures in monitoring/alerting listeners. | **Low** | Yes — log exceptions or provide callback |
| 11 | No input validation | `failure_threshold=0`, `recovery_timeout=-1`, `half_open_max_calls=0` all accepted. | **Medium** | Yes — validate in `__init__` |
| 12 | `_success_count` never used | Tracked but never affects any behavior. Dead code or incomplete feature. | **Low** | Yes — remove or implement success-based transitions |
| 13 | `_half_open_calls` not reset on HALF_OPEN → CLOSED | Counter retains value after recovery, confusing for monitoring. | **Low** | Yes — reset in `_on_success()` |

### Deepest Finding

**The monitoring system itself becomes an attack vector.**

Pass 4 revealed that the `state` property is a mutation bomb disguised as a read accessor. Pass 1 found that it bypasses the lock. Pass 3 showed that monitoring polls can reset `_half_open_calls`. The synthesis:

A properly implemented health check that polls `circuit.state` every 10 seconds will, under the right timing, allow multiple calls through the half-open gate that should have been serialized. The monitoring system — intended to observe — becomes an active participant in corrupting the circuit breaker's guarantees.

This is visible ONLY because we traced the property's side effects through the concurrency model. A surface-level code review would miss it because "property access is just a read, right?"

The fix is architectural: **separate observation from transition**. The `state` property must be pure (read-only). Transitions must be explicit methods that acquire the lock. Any implicit state change on read access is a design flaw.
