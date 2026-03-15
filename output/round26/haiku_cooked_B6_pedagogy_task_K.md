# Structural Concealment Analysis: Circuit Breaker Pattern

## 1. EXPLICIT DESIGN CHOICES & REJECTED ALTERNATIVES

| Choice | What Code Commits To | What Code Invisibly Rejects |
|--------|-------|---------|
| **Three discrete states** (CLOSED/OPEN/HALF_OPEN) | Binary "callable/not" boundaries | Continuous degradation, probabilistic shedding, fuzzy state membership |
| **Failure COUNT as trigger** | `_failure_count >= threshold` | Failure RATE, latency percentiles, error-type discrimination, adaptive thresholds |
| **Timeout as recovery signal** | `time.time() - last_failure > reset_timeout` | Exponential backoff for state transitions, probe-based recovery, external health checks, adaptive timeout |
| **Success accumulation validates recovery** | `_success_count >= half_open_max` | Single-probe validation, continuous health observation, statistical confidence bounds |
| **Retry and breaker as sequential composition** | [state check] → [retry loop] → [state update] | Interleaved retry/breaker logic, circuit-aware retry count, concurrent validation |
| **Amnesia on success** (resets failure_count to 0) | `_failure_count = 0` when success in CLOSED | Sliding window counters, weighted history, decay functions, exponential forgetting |
| **Exception as sole information channel** | Re-raise propagates failure upward | Structured error types, failure mode discrimination, async/deferred failure handling |
| **Stateless retry signature** (max_retries=3 hardcoded) | Retry strategy independent of breaker state | Circuit-aware retry bounds, adaptive retry count, learning from state history |

---

## 2. CODE BY SOMEONE WHO INTERNALIZED THE PATTERN BUT FACED A DIFFERENT PROBLEM

**Original problem:** Transient network failures on a single service  
**New problem:** Adaptive load shedding for a queue-based system

```python
import time

class QueueLoadShedder:
    """Internalizes circuit breaker PATTERN: discrete states + counters + timeout + success validation"""
    ACCEPTING, SHEDDING, PROBING = "accepting", "shedding", "probing"

    def __init__(self, max_queue=1000, shed_threshold=0.8, 
                 recovery_timeout=30, probe_threshold=5):
        self.state = self.ACCEPTING
        self.queue_depth = 0
        self.shed_threshold = shed_threshold
        self.recovery_timeout = recovery_timeout
        
        # Transferred from circuit breaker
        self._overload_count = 0          # Mimic: _failure_count
        self._probe_success_count = 0      # Mimic: _success_count
        self._last_overload_time = None    # Mimic: _last_failure_time
        self._max_queue = max_queue

    def handle(self, work_fn, *args, **kwargs):
        """Mirrors execute() structure exactly"""
        # Mimic: OPEN state check
        if self.state == self.SHEDDING:
            if time.time() - self._last_overload_time > self.recovery_timeout:
                self.state = self.PROBING
                self._probe_success_count = 0
            else:
                raise Exception("Shedding load")

        self.queue_depth += 1
        try:
            # Mimic: _retry_with_backoff
            result = self._do_with_retry(work_fn, *args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
        finally:
            self.queue_depth -= 1

    def _do_with_retry(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
        """Mimic retry loop exactly"""
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(base_delay * (2 ** attempt))

    def _on_success(self):
        """Mimic: success amnesia pattern"""
        if self.state == self.PROBING:
            self._probe_success_count += 1
            if self._probe_success_count >= 5:
                self.state = self.ACCEPTING
                self._overload_count = 0  # AMNESIA - transferred pattern
        else:
            self._overload_count = 0  # AMNESIA - transferred pattern

    def _on_failure(self):
        """Mimic: threshold-triggered state change"""
        # Check if overloaded (measure in WRONG PLACE - after work done)
        if self.queue_depth / self._max_queue >= self.shed_threshold:
            self._overload_count += 1
            self._last_overload_time = time.time()
            
            if self._overload_count >= 3:
                self.state = self.SHEDDING
```

---

## 3. SILENT vs. VISIBLE CORRUPTION TRACE

### **SILENT CORRUPTION #1: Amnesia Teaches Wrong Recovery Model**

**In original CircuitBreaker:**
```python
self._failure_count = 0  # Correct: external service recovered, history irrelevant
```
✓ Works: Network error is transient, one success = service is now responsive

**In QueueLoadShedder:**
```python
self._overload_count = 0  # WRONG: queue depth is a function, not a binary state
```
✗ Silent: Code looks identical, semantics inverted:
- Queue depth = 850/1000 → shed → drop to 200/1000 → _on_success() → amnesia → ACCEPTING
- Next work batch arrives → queue depth = 900/1000 → but _overload_count = 0, so no alarm
- Pattern doesn't re-trigger until _overload_count accumulates again
- Result: **Load shedding oscillates instead of learning**

**Discovery**: Days-weeks. Observed as "periodic shedding cycles" (looks like workload is bursty), not "algorithm doesn't learn patterns"

---

### **SILENT CORRUPTION #2: Success Counter Measures Wrong Dimension**

**In original:**
```python
self._success_count >= self._half_open_max  # Means: "N consecutive calls succeeded"
```
Validates: Service is responding

**In new code:**
```python
self._probe_success_count >= probe_threshold  # Means: "N requests completed"
```
BUT measures: Request success, NOT queue health

**Sequence under load:**
1. Queue depth = 950/1000, state = SHEDDING
2. Timeout expires → state = PROBING  
3. One thread's request succeeds (work_fn completes) → _probe_success_count = 1
4. Four more succeed → _probe_success_count = 5 → state = ACCEPTING
5. But queue_depth is STILL 900/1000
6. Immediately reverts to SHEDDING

**Result**: Rapid state oscillation, thrashing

**Discovery**: Hours-days. Visible in monitoring as rapid state changes but causation is hidden

---

### **VISIBLE CORRUPTION #1: State Check Happens Too Late**

```python
def _on_failure(self):
    if self.queue_depth / self._max_queue >= self.shed_threshold:  # <-- Checked AFTER work done
        self._overload_count += 1
```

**Sequence:**
1. Request arrives, increments queue_depth
2. Work executes (takes 500ms)
3. Work fails → _on_failure() called
4. Check queue depth (but 500ms has passed, 10 more requests queued behind)
5. Decision made on stale data

**Result**: Shedding threshold breached before mitigation activates  
**Discovery**: Immediate (minutes). Visible in monitoring: queue fills dangerously before shedding

---

### **VISIBLE CORRUPTION #2: Race Condition on State Transitions**

```python
if self.state == self.SHEDDING:
    if time.time() - self._last_overload_time > self.recovery_timeout:
        self.state = self.PROBING      # <-- RACE: multiple threads can execute
        self._probe_success_count = 0
```

**Under concurrent load:**
- Thread A checks `self.state == SHEDDING` ✓
- Thread B checks `self.state == SHEDDING` ✓
- Both threads check timeout ✓
- Both execute `self.state = self.PROBING`
- Multiple threads increment `_probe_success_count` unsynchronized
- Counter becomes unreliable, state transitions become unpredictable

**Result**: State machine violates its own invariants  
**Discovery**: Fast (1-10 minutes). Visible as: "state changed spontaneously", "Thread A sees PROBING while Thread B sees SHEDDING"

---

### **VISIBLE CORRUPTION #3: Threshold Metric Wrong**

```python
if self._overload_count >= 3:  # Hardcoded
    self.state = self.SHEDDING
```

Original context: 3 failures in series = circuit opens (reasonable)  
New context: 3 requests under load = overload event? (unreasonable)

**Under load:**
- 100 concurrent requests, queue depth exceeds threshold
- All 100 fail → _on_failure() called 100 times
- _overload_count increments 100 times in ~50ms
- Threshold of 3 hit immediately

**Result**: Shedding activates too aggressively, sheds more than necessary  
**Discovery**: Hours. Visible as shed_rate metrics suddenly spiking (but causation unclear)

---

## 4. THE PEDAGOGY LAW

**"Discrete states with counter-driven transitions embody recoveryability. Measurement (counting external events) and validation (success accumulation) are separable concerns."**

The original code transfers these assumptions:
1. **Atomic Assumption**: Failures are discrete, countable events
2. **Validation Assumption**: N successes prove system recovered
3. **Time Assumption**: Time passage enables recovery
4. **State Accuracy Assumption**: Being in a state accurately reflects reality

**When transferred to queue management:**
- ✗ Atomic Assumption breaks: 100 failing requests ≠ 1 overload event (cumulative vs. instantaneous)
- ✗ Validation Assumption breaks: Request success ≠ queue is healthy (local vs. global)
- ✗ Time Assumption breaks: Waiting doesn't fix overload; need external load to decrease
- ✗ State Accuracy Assumption breaks: Being in PROBING ≠ actively probing; could be in steady high load

The hidden constraint being transferred: **"The phenomenon you're trying to control is decoupled from the system's internal requests."** This is TRUE for network failures (external to your service) but FALSE for queue depth (created by your own workload).

---

## 5. WHICH INVISIBLE DECISION FAILS FIRST AND SLOWEST?

### **FAILS FIRST (Visible, Fast Discovery)**

**Race condition on state variables**

```python
if self.state == self.SHEDDING:
    if time.time() - self._last_overload_time > self.recovery_timeout:
        self.state = self.PROBING  # <-- RACE CONDITION
```

- **Discovery time**: 1-10 minutes under sustained load
- **Why fast**: Concurrent threads immediately conflict on shared state
- **Symptom**: Logs show state transitions that don't match trigger conditions ("SHEDDING → PROBING without timeout"), monitoring shows simultaneous conflicting states
- **Why it's discovered first**: Thread safety failures are immediate and unambiguous under load

### **FAILS SLOWEST (Silent, Slowest Discovery)**

**Amnesia prevents learning load patterns**

```python
def _on_success(self):
    if self.state == self.PROBING:
        # ... 
        self._overload_count = 0  # Amnesia: never learn "load spikes recur"
```

- **Discovery time**: Days-weeks
- **Why slow**: Appears as normal operational pattern (bursty workload)
- **Symptom**: Periodic 5-10 minute cycles: ACCEPTING → (load spike) → SHEDDING → (timeout) → PROBING → (few successes) → ACCEPTING → (load spike again)
- **Misleading diagnosis**: "Workload is variable and bursty" (true but missing the point: the algorithm doesn't learn the pattern)
- **Why it's discovered last**: 
  - Looks like correct behavior (responding to spikes)
  - Monitoring shows shedding is working
  - Root cause analysis concludes "resize capacity" not "fix the algorithm"
  - Requires multi-day observation to see the cycling pattern
  - Requires understanding that amnesia is the root cause

**Production evidence**: SRE observes load shedding kicks in ~40% of operating hours. Capacity is provisioned for this "bursty pattern." Investigation concludes workload is inherently spiky. Real answer: algorithm oscillates because it can't learn the spike occurs at 2:00 AM every night.

---

## Summary Table

| Failure | Speed | Type | Root Cause | Symptom | Discovery Method |
|---------|-------|------|-----------|---------|------------------|
| Race condition on state | **Minutes** | **Visible** | No locks on shared state | State changes unpredictably | Thread dump, state monitoring |
| Retry delay under load | **Seconds** | **Visible** | Retry loop before failover | p99 latency spikes | Request timing metrics |
| Stale queue check | **Hours** | **Mixed** | Measure after work done | Queue fills before shedding | Queue depth timeseries |
| Threshold too aggressive | **Hours** | **Visible** | Counting requests not events | Shed rate spikes suddenly | Shed metrics analysis |
| Amnesia prevents learning | **Days-weeks** | **Silent** | Success = restart counter | Periodic cycling patterns | Multi-day SLO analysis |
| Success ≠ health | **Hours-days** | **Silent** | Measuring wrong metric | Rapid state oscillation | State transition logs |

The **deepest structural problem** is that the pattern teaches: *"Restart after state change"* without teaching *"Understand whether past data should inform new state."* This transfers silently and causes the slowest failures.
