# Circuit Breaker: Embedded Claims and Corruption

## Primary Empirical Claim

**"A system that fails N times will recover to health if given T seconds of rest (no active load)."**

This claim is embedded in the reset_timeout logic: `if time.time() - self._last_failure_time > self._reset_timeout: self._state = self.HALF_OPEN`

---

## When That Claim Is False

**Corruption trace:** Structural failures (resource leaks, cascading backpressure, algorithmic pathologies) don't self-heal through silence. Time without remediation is meaningless.

**Execution under false assumption:**

```
t=0s    Request 1 → API hanging (API is under load spike)
t=1s    Request 2 → timeout, failure_count=1
t=2s    Request 3 → timeout, failure_count=2
...
t=5s    Request 5 → timeout, failure_count=5 ⟹ state=OPEN ✓

t=5s-30s    [Circuit OPEN, no requests sent]
            [Meanwhile: API is STILL overloaded - time changed nothing]

t=35s   execute() called
        → time.time() - last_failure_time = 30s > 30s
        → state=HALF_OPEN ✓ [Optimistic transition]
        
t=35s   Request 6 (first half-open test)
        → API responds (cache hit, or momentary load clearing)
        → success! _success_count=1, still _success_count < 3

t=36s   Requests 7-8: both succeed by luck
        → _success_count=3 ⟹ state=CLOSED ✓ [Circuit CLOSES]

t=37s   [100 pending requests waiting for circuit to close NOW FLOOD IN]
        
t=37s   The API, already fragile, is now crushed by amplified load
        → cascading timeout failures across all 100 requests
        → _failure_count spikes
        → state=OPEN (circuit opens again)

Result: **Oscillation loop**
  OPEN (wait 30s) → HALF_OPEN (test) → CLOSED (flood) → OPEN (crash) → repeat
  
  The circuit becomes a **load amplifier**, not a breaker.
```

---

## Secondary Claim: Failure Memory

**"Failure count accumulates and persists as a measure of system degradation."**

**False under:** Any success in CLOSED state.

```python
def _on_success(self):
    if self._state == self.HALF_OPEN:
        self._success_count += 1
    else:
        self._failure_count = 0  # ← Single success erases history
```

**Corruption:**
- Unreliable service: 50% success, 50% timeout
- Request sequence: [FAIL, FAIL, **SUCCESS** ← count resets to 0, FAIL, FAIL, **SUCCESS** ← count resets]
- Circuit **never** accumulates 5 failures → never opens
- Becomes a **noise filter** masking systemic unreliability
- Callers get silent failure: half their requests fail but circuit doesn't warn them

---

## Tertiary Claim: Retry Isolation

**"Exponential backoff and circuit opening independently protect the downstream system."**

**False under:** Resource-exhaustion failures or correlated load spikes.

**Corruption: Retry amplification + thundering herd**

```
100 concurrent callers, service degraded (slow, not timing out yet)

Each caller's _retry_with_backoff():
  Attempt 1 → slow_response (e.g., 5s)
  Sleep 1s, Attempt 2 → slow_response (5s)
  Sleep 2s, Attempt 3 → slow_response (5s)
  Total per caller: 3 requests + 3 seconds sleep = ~20s elapsed

All 100 callers' backoff timers expire IN SYNC (t=20s window)
→ All 100 send request attempt #4 simultaneously
→ Service, already at 80% saturation, receives 100 synchronized requests
→ Service collapses
→ All 100 requests timeout
→ Cascading failure reaches circuit threshold faster than without retry

Circuit breaker becomes a **request amplifier** under stress.
Instead of dampening load, it concentrates it (synchronized retry storms).
```

---

## What the Code Conceals

| What Code Claims | What Code Actually Does | Incompatibility |
|---|---|---|
| "Detects and isolates faults" | Detects *timing*, ignores *causation* | Structural failures don't heal on schedule |
| "Tracks system health" | Resets history on any success | Can't distinguish flakiness from stability |
| "Protects downstream" | Amplifies load via synchronized retries | Load spike → all callers retry in unison |
| "Soft recovery via half-open" | Optimistic state transition on clock time | No validation that system actually recovered |
| "Idempotent state machine" | Race conditions on state/counters (no locks) | Concurrent calls corrupt internal counts |

---

## Three Contradictory Constructions

**A: Active health verification** (inverts timeout assumption)
```python
# Instead of: wait T seconds, then assume healthy
# Do: explicitly verify health before closing
if self._state == self.OPEN and is_healthy_verified():
    self._state = self.HALF_OPEN  # Only if proof exists
```
**Reveals:** Code treated silence (time passing) as evidence of recovery.

**B: Rate-of-change not count** (inverts failure erasure)
```python
# Instead of: count absolute failures, reset on success
# Track: failure *rate* or *variance in success*
recent_success_rate = success_in_last_window / total_in_last_window
if recent_success_rate < threshold:  # Persistent low rate
    self._state = self.OPEN
```
**Reveals:** Code confused "occasional failure" with "systemic unreliability."

**C: Decouple retry from circuit breaking** (inverts amplification)
```python
# Circuit breaker: YES/NO gate only (no retry logic)
# Retry logic: caller-side with per-caller jitter
# This prevents synchronized retry storms
def execute(self, fn, *args, **kwargs):
    if self._state == self.OPEN:
        raise Exception("Circuit open")
    # Let *caller* decide retry strategy, not breaker
    return fn(*args, **kwargs)
```
**Reveals:** Code mixed two independent concerns (fault detection + resilience), making both worse.

---

## Core Impossibility

The circuit breaker tries to solve an impossible optimization simultaneously:
- **Minimize latency** (close circuit quickly, retest soon)
- **Minimize load on failing system** (stay open long, test rarely)
- **Detect genuine recovery** (confirm health != confirm one success)

Any mechanism that optimizes for all three at once **will oscillate under realistic failure modes**.

The code chose: "wait T, test once, close if test succeeds." Under cascading or structural failures, this becomes: "oscillate between load amplification and pessimistic blocking."
