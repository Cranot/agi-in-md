## Generated Lens

Map every shared mutable state variable in this rate limiter. For each, enumerate the execution interleavings that corrupt state — specifically where reads and writes cross thread boundaries. Identify every implicit invariant the author assumed: tokens ≤ capacity, refill is atomic, is_throttled is a pure read. For each invariant, construct the minimal 2-thread execution sequence that violates it. Then derive the conservation law: what fundamental trade-off exists between lock granularity and token accuracy? End with a taxonomy: which bugs are fixable implementation errors vs. which are structural tensions that any rate limiter must negotiate.

---

## Lens Execution

### Shared Mutable State Map

| Variable | Access Points | Thread Safety |
|----------|---------------|---------------|
| `self._tokens` | `_refill()` (read/write), `allow()` (read/write), `is_throttled` (read) | Protected only in `allow()` decrement — **exposed in _refill and is_throttled** |
| `self._last_refill` | `_refill()` (read/write) | **Completely unprotected** |
| `self._lock` | `allow()` only | `_refill()` and `is_throttled` bypass it |

---

### Invariant Violations

**Invariant 1: Tokens never exceed capacity**

The code comments flag this, but let me trace the structural cause:

```python
self._tokens += elapsed * self.rate  # No cap
```

This isn't just a missing `min()` — it's a **conceptual error**. Token buckets have two semantics:
- **Leaky bucket**: tokens drain at rate, requests add to bucket, overflow rejects
- **Standard token bucket**: tokens fill to capacity, requests consume, underflow rejects

The code attempts standard token bucket but implements refill without a ceiling. The invariant violation:

```
After 10 seconds idle with rate=10, capacity=10:
_tokens = 10 + (10 * 10) = 110  # Can burst 110 requests instantly
```

**Structural diagnosis**: This is a **fixable implementation error**, not a fundamental tension.

---

**Invariant 2: Refill is atomic**

The critical bug. `_refill()` is called *outside* the lock in `allow()`:

```python
def allow(self):
    self._refill()  # <-- OUTSIDE LOCK
    with self._lock:
        if self._tokens >= 1:
```

**Two-thread corruption sequence:**

```
Thread A: calls allow(), enters _refill(), reads _last_refill = T0
Thread B: calls allow(), enters _refill(), reads _last_refill = T0  (same!)
Thread A: computes elapsed = 0.1, writes _tokens = 10.1, _last_refill = T1
Thread B: computes elapsed = 0.1, writes _tokens = 10.2, _last_refill = T1
         ↑ DOUBLE REFILL — both threads credited for the same time window
```

The race allows **unbounded over-crediting** of tokens. Under high contention, the rate limiter permits rates far exceeding the configured limit.

**Severity**: Critical. Defeats the entire purpose of the class.

---

**Invariant 3: `is_throttled` is a pure read (no side effects)**

```python
@property
def is_throttled(self):
    self._refill()  # <-- MUTATION INSIDE A PROPERTY
    return self._tokens < 1
```

This violates Python conventions (properties should be side-effect free) and introduces the same race condition as `allow()`.

**Consequences:**
1. **Observation changes state**: Merely checking `is_throttled` advances `_last_refill`, causing time "loss"
2. **Debugging impossibility**: Logging `limiter.is_throttled` in a debugger alters program behavior
3. **Race condition**: Same double-refill bug as `allow()`

**Worst-case execution:**

```
Thread A: checks is_throttled, refills, credits 0.5 tokens, sets _last_refill = T1
Thread B: calls allow(), refills from T1 (not T0!), loses 0.5 tokens worth of time
```

Thread B is **under-credited** — the rate limiter becomes stricter than configured.

---

**Invariant 4: `wait()` terminates in bounded time**

```python
def wait(self):
    while not self.allow():
        deficit = 1.0 - self._tokens
        sleep_time = deficit / self.rate
        time.sleep(max(sleep_time, 0.001))
```

**Drift accumulation:**
- `time.sleep()` may sleep longer than requested (OS scheduling)
- Each iteration compounds drift
- Under high load, `wait()` may sleep 10-50% longer than necessary

**More critical: Race with concurrent consumers**

```
Thread A: in wait(), computes deficit = 0.5, sleep_time = 0.05
Thread B: consumes the token Thread A was waiting for
Thread A: wakes up, allow() returns False, loops again
```

This isn't a bug — it's correct behavior for a non-blocking rate limiter. But the **drift** is structural: any sleep-based wait accumulates timing error.

---

### Conservation Law for Rate Limiters

After analyzing the tensions, I derive:

> **The Atomicity-Precision Trade-off**: 
> A rate limiter can either (a) hold its lock for the entire refill+consume operation, blocking all other threads for the duration of a `time.time()` call, OR (b) release the lock between refill and consume, allowing interleaving that corrupts token accounting. There is no implementation that achieves both perfect concurrency and perfect token accuracy.

**However**, this code doesn't just suffer from this structural tension — it has **fixable bugs** that make it worse than necessary:

1. The lock exists but isn't used for refill
2. The capacity cap is trivial to add
3. The property mutation is unnecessary

---

### Findings Table

| Location | What Breaks | Severity | Classification |
|----------|-------------|----------|----------------|
| `_refill()` line: `self._tokens += ...` | Tokens exceed capacity, burst unbounded | High | **Fixable** — add `min(self._tokens, self.capacity)` |
| `allow()`: `_refill()` outside lock | Double-refill race, over-crediting | **Critical** | **Fixable** — move refill inside lock |
| `is_throttled`: calls `_refill()` | Mutation in property, time loss, races | High | **Fixable** — make property lock and read atomically without refill, or make it a method |
| `is_throttled`: no lock on read | Torn reads possible on 32-bit Python | Medium | **Fixable** — acquire lock for read |
| `wait()`: `time.sleep()` drift | Accumulates ~10-50% timing error | Low | **Structural** — inherent to sleep-based waiting; use condition variables for precision |
| `wait()`: no timeout parameter | Infinite loop if rate is 0 or system clock broken | Medium | **Fixable** — add timeout parameter |

---

### Corrected Implementation Sketch

```python
def _refill(self):
    now = time.time()
    elapsed = now - self._last_refill
    self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
    self._last_refill = now

def allow(self):
    with self._lock:
        self._refill()  # INSIDE lock
        if self._tokens >= 1:
            self._tokens -= 1
            return True
        return False

def is_throttled(self):  # Not a property
    with self._lock:
        self._refill()
        return self._tokens < 1
```

Or for a true non-mutating check:

```python
@property
def is_throttled(self):
    with self._lock:
        # Approximate check without advancing state
        now = time.time()
        elapsed = now - self._last_refill
        estimated = min(self.capacity, self._tokens + elapsed * self.rate)
        return estimated < 1
```

---

```
---
CONSTRAINT NOTE: This analysis maximized concurrent execution interleavings and implicit invariant violations.
It did not examine: memory model guarantees on different Python implementations, integration patterns with distributed systems.
For deeper analysis: /prism-full | For meta-analysis: /prism-reflect
```
