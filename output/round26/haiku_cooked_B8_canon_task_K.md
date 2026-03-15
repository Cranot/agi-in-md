# Circuit Breaker Analysis: Intended → Accidental → Permanent

## V1 Behavior: Intended vs Accidental

### Core Intended Behavior
- Three-state machine: CLOSED → OPEN → HALF_OPEN → CLOSED
- Execute function; open after N failures; re-test after timeout
- Clean circuit semantics

### Observable Accidents (That Could Be Mistaken for Intentional)

| Accident | Observable? | Inference Path | Callers Depend On? |
|----------|-------------|---------------|--------------------|
| **Retry built into execute()** | YES — timing shows ~7s max latency (1+2+4 exponential) | "execute() internally retries 3 times before throwing" | **YES** — structured code around this |
| **failure_threshold counts FINAL failures, not attempts** | YES — 15 internal attempts = 5 final failures → opens circuit | "failure_threshold=5 means 5 final throws, not 15 attempt-failures" | **YES** — deployed configs calibrated to this |
| **HALF_OPEN fails fast (→OPEN on first failure)** | YES — one failed call in HALF_OPEN re-enters OPEN | "HALF_OPEN is stricter than CLOSED: 1-strike rule vs 5-strike rule" | **YES** — callers test only safe ops in HALF_OPEN |
| **max_retries=3, base_delay=1 not configurable** | YES — constant 7s max retry duration | "All circuit breakers behave identically; that's the standard" | **YES** — operation timeouts tuned to this |
| **Jitter fixed at ±1s, not proportional** | NO — jitter is background noise, rarely inspected | "Jitter happens; exact value doesn't matter" | **NO — not reverse-engineered** |
| **No observability into retry vs circuit failure** | PARTIAL — throwing exception loses context | "If thrown and STATE≠OPEN, must be retry exhaustion" | **WEAK** — workaround-able |

---

## What Callers Reverse-Engineered from V1

### Three Tiers of Inference

**Tier 1: Structural Dependency (Unbreakable)**
```python
# Callers assume:
# "execute() = 3 retries + circuit breaker"
# They DON'T wrap it:

for fn in [flaky1, flaky2]:
    try:
        circuit.execute(fn)  # 3 attempts built-in
    except:
        # Truly unrecoverable
        fallback()

# NOT:
for fn in [flaky1, flaky2]:
    for attempt in range(3):  # Would be 9 attempts total!
        try:
            circuit.execute(fn)
        except:
            if attempt < 2:
                continue
            raise
```

**Tier 2: Semantic Dependency (Calibration)**
```python
# Deployed configs assume:
# "failure_threshold=5 means circuit opens after 5 FINAL failures"
# All timeouts tuned around: max 7 seconds retry span (1+2+4)

# If changed to count attempts, this becomes:
# "failure_threshold=5 means circuit opens after ~2 final failures"
# → All deployed circuits become 2.5x too sensitive
# → Cascades to 100+ services flipping to OPEN

circuit = CircuitBreaker(failure_threshold=5)  # This number assumes final-failure counting
```

**Tier 3: Behavioral Dependency (Mode Semantics)**
```python
# Callers know HALF_OPEN is stricter:
if circuit._state == CircuitBreaker.HALF_OPEN:
    # Only call operations that are proven-safe
    result = circuit.execute(health_check)
else:
    # CLOSED: can call normal ops
    result = circuit.execute(risky_op)
```

---

## V2 Fixes: Which Ones Break Production?

### ✅ Safe Fixes (No Caller Breakage)

1. **Make jitter proportional to base_delay**
   - Change: `jitter = base_delay * random.uniform(0, 0.1)` instead of fixed ±1s
   - Observable impact: NONE (jitter is background noise)
   - Cost: Zero

2. **Remove redundant `_failure_count = 0` reset in CLOSED success**
   - This line is a no-op (already zero)
   - Cost: Zero; pure clarity gain

3. **Add documentation of failure_threshold semantics**
   - Document: "Counts FINAL failures after all retries exhausted, not attempt failures"
   - Cost: Zero; eliminates need for reverse-engineering

4. **Add observability hooks**
   - Expose `attempt_count`, `final_exception`, `retry_duration`
   - Callers can now log *why* circuit threw
   - Backward compatible (optional hooks)

### 🔴 Unsafe Fixes (BREAK PRODUCTION)

1. **Separate retry logic from circuit execute()**
   ```python
   # V2 attempt:
   def execute(self, fn):  # No retries!
       # Circuit logic only
       return fn()
   
   # BREAKS: Every caller loses built-in retries
   # Cascading fix: 100+ callsites must add retry loops
   # Cost: Massive; benefit: "cleaner architecture"
   ```
   - **Breakage**: Callers no longer get 3 automatic retries
   - **SLO Impact**: Latency expectations change from "max 7s" to "unbounded"
   - **Unacceptable**

2. **Change failure_threshold to count attempts instead of finals**
   ```python
   # V2 attempt:
   # Old: 5 final failures (=~15 internal attempts) → open
   # New: 5 attempt failures → open
   
   # BREAKS: All deployed configs become 3x too sensitive
   circuit = CircuitBreaker(failure_threshold=5)  # Now means 5 attempts, not 5 finals!
   ```
   - **Breakage**: Existing deployments flip to OPEN 3x faster
   - **Cascading fixes**: Every deployment needs recalibration
   - **Unacceptable**

3. **Make max_retries configurable with a different default**
   ```python
   # V2 attempt: "Let's use sensible defaults"
   def __init__(self, max_retries=1):  # "Faster failure detection"
       self._max_retries = max_retries  # Was hardcoded 3
   
   # BREAKS: Callers who didn't override get 1 retry instead of 3
   # Their 7s latency assumptions now cause 2s timeouts
   ```
   - **Breakage**: Timing assumptions violated
   - **Unacceptable**

4. **Make HALF_OPEN more lenient** (allow N failures before re-opening)
   ```python
   # V2 attempt:
   # Old: HALF_OPEN + any failure → OPEN (1-strike rule)
   # New: HALF_OPEN + 3 failures → OPEN
   
   # BREAKS: Callers now call riskier ops in HALF_OPEN, expecting fallback
   # If HALF_OPEN is lenient, no fallback triggers, cascading failures
   ```
   - **Breakage**: Reliability semantics violated
   - **Unacceptable**

---

## V2 Design: Preserving Reverse-Engineered Rules

```python
class CircuitBreakerV2:
    """
    Non-negotiable constraints:
    1. execute() MUST retry internally (callers depend on this)
    2. failure_threshold MUST count final failures (deployed configs assume this)
    3. max_retries=3, base_delay=1 MUST be defaults (latencies tuned to this)
    4. HALF_OPEN MUST fail fast (reliability semantics)
    """
    
    def __init__(self, 
                 failure_threshold=5,      # Counts FINAL failures (unchanged)
                 reset_timeout=30,
                 half_open_max=3,
                 max_retries=3,             # NEW: Configurable, but defaults to v1
                 base_delay=1,              # NEW: Configurable, but defaults to v1
                 jitter_fraction=0.1):      # FIXED: Now proportional
        
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None
        
        # PRESERVED: These defaults match v1 exactly
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._jitter_fraction = jitter_fraction  # IMPROVED: proportional instead of fixed
        
        # NEW: Observability (doesn't break anything)
        self._attempt_count = 0
        self._final_exception = None

    def execute(self, fn, *args, **kwargs):
        # UNCHANGED: Retry logic stays INSIDE execute()
        # (This is now a required feature, not an accident)
        
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
            else:
                raise Exception("Circuit is open")

        try:
            result = self._retry_with_backoff(fn, *args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._final_exception = e  # NEW: Observability
            self._on_failure()
            raise

    def _retry_with_backoff(self, fn, *args, **kwargs):
        # CHANGED: Use instance config instead of hardcoded
        # BUT: Defaults match v1 behavior exactly
        for attempt in range(self._max_retries):
            self._attempt_count += 1
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == self._max_retries - 1:
                    raise
                # FIXED: Jitter is now proportional
                delay = (self._base_delay * (2 ** attempt) + 
                        self._base_delay * random.uniform(0, self._jitter_fraction))
                time.sleep(delay)

    def _on_success(self):
        if self._state == self.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._half_open_max:
                self._state = self.CLOSED
                self._failure_count = 0
        # REMOVED: Redundant reset in CLOSED case
        # (Already zero from previous OPEN transition)

    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._failure_threshold:
            self._state = self.OPEN
        # UNCHANGED: HALF_OPEN still fails fast (1-strike rule)
```

---

## The Canonization Law

**Name: "The Reverse-Engineered Stability Theorem"**

> An accidental implementation detail becomes a permanent architectural feature when:
> 
> 1. **Observable**: Callers can reliably infer its behavior (by timing, testing, or code inspection)
> 2. **Actionable**: Callers structure their code around the inference (timeouts, retry loops, config values)
> 3. **Expensive to Break**: The cost of changing it (cascading fixes across 100+ callsites) exceeds the benefit (architectural cleanliness)
> 
> **Consequence**: The accident becomes sacred law. Future versions cannot remove it without a major version break and migration plan.

Applied:
- **Accident**: Retry logic mixed into execute() (poor separation of concerns)
- **Observable**: Callers measure ~7s latency from exponential backoff
- **Actionable**: Callers DON'T wrap execute() in retry loops; they set timeouts expecting built-in retries
- **Expensive to Break**: Removing retries requires recoding 100+ callsites + changing all timeout configs
- **Result**: Mixed retry + circuit logic is now a **required feature of the public API**, not a bug

---

## Which V1 Accidents Cannot Be Fixed Without Breaking Callers Architecturally?

| Accident | Why Unfixable |
|----------|---------------|
| **Built-in retry in execute()** | Callers have written code around "execute() = 3 attempts". Removing it breaks every single caller's latency assumptions. **Architectural breakage**: No graceful degradation. |
| **failure_threshold counts final failures** | All deployed CircuitBreaker(failure_threshold=5) configs assume "5 final throws". Changing to "5 attempts" makes deployed circuits 3x more aggressive. **Architectural breakage**: Cascading config recalibration across 100+ services. |
| **max_retries=3 default** | Callers have tuned operation timeouts, circuit timeouts, and upstream timeouts assuming ~7 second max backoff (1+2+4). Changing default to 1 or 10 breaks all these assumptions. **Architectural breakage**: SLO violations across the board. |
| **HALF_OPEN 1-strike failure rule** | Callers only call *safe* operations in HALF_OPEN (health checks), assuming any failure re-opens. Making HALF_OPEN more lenient causes callers to call *risky* operations and expect fallbacks that never trigger. **Architectural breakage**: Cascading failures. |

---

## What V1 Bug Is Now a Required V2 Feature?

**The bug**: "Retry logic and circuit breaker logic are mixed in the same execute() method, making the code hard to test and reasoning about failure modes ambiguous."

**Why it's now required**: 
- Callers depend on execute() incorporating retries
- Separating them breaks the implicit contract: "one call to execute() ≈ 3 internal attempts"
- Every operation timeout in the system is tuned to this contract

**What would fix it architecturally**:
1. **Keep execute() retrying** (unbreakable)
2. **Add observability** (new exception details, attempt counts)
3. **Document the semantics** (make the contract explicit)
4. **Add optional configuration** (max_retries, base_delay as parameters, defaulting to v1 behavior)

**What cannot be fixed**: Logically separating "retries" from "circuit breaker" in the API boundary, because that separation IS the bug that became a required feature.

---

## Summary: The Permanent Architecture

```
V1 Accident:          "Retry logic embedded in execute()"
↓
V1 Observable:        "~7s max latency, 3 exponential backoff attempts"
↓
V1 Actionable:        "Callers write: circuit.execute(fn); don't wrap in retry loop"
↓
V1 Config:            "failure_threshold=5 tuned for final failures, not attempts"
↓
V2 Constraint:        "execute() MUST retry or break 100+ callsites"
↓
Canonization:         "Accidental implementation detail → required feature"
↓
Forbidden Improvement: "Extract retries into separate Retrier layer"
```

The circuit breaker cannot be refactored to separate concerns without a major breaking change because the boundaries ARE the stable interface that callers have built around.
