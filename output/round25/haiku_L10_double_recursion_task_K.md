# Structural Analysis: The Deceptive Signal Problem

## INITIAL CLAIM

**"The circuit breaker's failure_threshold is fundamentally miscalibrated because it measures post-retry outcomes, not pre-retry system failures. The retry logic embeds a filter inside the circuit breaker's observation loop, making failure_threshold = 5 actually mean 'stop when 5 retry-exhaustion events occur' rather than 'stop when the system fails 5 times.' Changing max_retries from 3 to 10 silently changes what failure_threshold=5 measures, creating hidden coupling that breaks observability."**

Falsifiable by: Generate a system with known failure rate X, measure exceptions reaching _on_failure(), show the ratio varies with retry config but is never disclosed.

---

## THREE EXPERT EVALUATIONS

**DEFENDER** (preserving current design):
> "This is exactly what we want. Retries absorb transient failures—if every transient failure opened the circuit, the system would oscillate. The elegance here is that from the circuit's perspective, a call either succeeds (maybe after retries) or definitively fails. Retry details are encapsulated."

**ATTACKER** (challenging the claim):
> "The defender confuses 'not oscillating' with 'working correctly.' Yes, the circuit doesn't oscillate. But here's what actually happens: You configure failure_threshold=5 based on 'I want to tolerate 5 failures.' Then the system has 20 actual failures, retries absorb 15 of them (3 retries each = ~5 visible exceptions), circuit opens. Now you think 'I'm detecting failures'—but you're detecting retry-exhaustion events. The coupling is real, and it breaks the moment someone sets max_retries=10 expecting it won't affect circuit behavior."

**PROBER** (examining assumptions):
> "Both of you assume we know what failure_threshold should count. But define 'failure':
> - Is it a pre-retry fault? (Then max_retries should be invisible to the circuit.)
> - Is it a retry-exhaustion event? (Then failure_threshold should depend visibly on max_retries.)
> - Is it a client experience metric? (Then _on_failure should track latency, not just exceptions.)
> The code treats these as interchangeable. They're not. What makes you confident that in CLOSED state, resetting failure_count to 0 after one success is correct? What if the system is flaky? You've lost the failure history."

---

## THE CONCEALMENT MECHANISM

**How this code hides its real problem:**

Three layers of opacity:

1. **Temporal coupling hidden by exception identity**: When _retry_with_backoff exhausts retries and raises, the exception is structurally identical to any other exception. The circuit breaker cannot ask: "Did this come from attempt 1 or attempt 3?" Hiding the attempt count hides the signal distortion.

2. **Naming that creates false equivalence**: Both the parameter `failure_threshold` and the behavior suggest "count failures." But the code counts "exceptions after retries," not "failures." The name conceals the distinction.

3. **Configuration that implies independence but creates coupling**: max_retries and failure_threshold are separate parameters in different locations, implying they're independent. But they're not—failure_threshold's meaning changes when you change max_retries. The separation hides the coupling.

Together: developers configure the system believing they're tuning independent knobs (retries for transients, threshold for systemic failures) when they're actually tuning a single coupled parameter. The system works until it doesn't, and the failure is invisible.

---

## FIRST IMPROVEMENT (Deepening Concealment)

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3,
                 max_retries=3, base_delay=1):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._max_retries = max_retries  # Now explicit!
        self._base_delay = base_delay
        self._last_failure_time = None

    def execute(self, fn, *args, **kwargs):
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
            self._on_failure()
            raise

    def _retry_with_backoff(self, fn, *args, **kwargs):
        for attempt in range(self._max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == self._max_retries - 1:
                    raise
                delay = self._base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)

    # _on_success, _on_failure unchanged
```

**Why this deepens concealment:**

- ✗ **Appears to solve the "coupling" problem**: "Now max_retries is right here in __init__, visible and tunable!"
- ✗ **Creates false confidence in calibration**: Developers think, "Now I can set both parameters and my circuit will work correctly."
- ✓ **Hides the real problem further**: The code is now *more elegant*, making the semantic incoherence *less obvious*. An operator can reason about the code without realizing the measurement contract is broken.
- ✓ **Makes the coupling more dangerous**: Before, max_retries was scattered in method signatures. Now it's centralized, suggesting it's been "properly handled," when actually the hidden coupling has just been repackaged.

**Code review would pass**: "Good—retry config is explicit. This is more maintainable."

**Reality**: The measurement contract is still undefined, and now that's harder to see.

---

## THREE PROPERTIES NOW VISIBLE ONLY BECAUSE OF THIS IMPROVEMENT

1. **The hidden dependency has been elevated to the surface but not made explicit**
   - Parameters sit together in __init__, making it obvious they should be related
   - But their relationship (how to calibrate one from the other) is still implicit
   - The improvement exposes that the problem exists without providing a solution

2. **Retry logic solves a different problem than failure detection**
   - max_retries answers: "How many times should we try?"
   - failure_threshold answers: "When is systemic failure so bad we stop trying?"
   - Putting them in the same __init__ falsely suggests they're aspects of the same problem
   - The improvement makes this category error visible by treating them as siblings

3. **The measurement contract is fundamentally undefined**
   - By making retries configurable, we've exposed that "what does failure_threshold measure?" is still unanswered
   - Failure_threshold measured in: call-failures? Retry-exhaustion events? Something else?
   - The code's silence on this question is now *louder* because we've centralized configuration

---

## DIAGNOSTIC APPLIED TO FIRST IMPROVEMENT

**What does this improvement conceal?**

The need for an explicit, verifiable contract about what the circuit breaker is actually measuring. The improvement gives the impression of control: "I can tune max_retries and failure_threshold together," which creates false confidence that the system is under control.

**What property of the original problem becomes visible ONLY through attempting this improvement?**

The property that **separating concerns at the code level doesn't separate them at the semantic level**. 

By attempting to "fix" the problem through configuration, we've revealed something: the core issue isn't sloppy code, it's that the problem itself is semantically incoherent. You cannot have:
- Retries that filter the signal AND
- A circuit breaker that measures the true signal AND  
- A configuration that works independent of retry settings

Choose two. The code tries all three and fails invisibly.

---

## SECOND IMPROVEMENT (Addressing the Recreated Property)

Separate the semantic concerns:

```python
class CircuitBreaker:
    """Measures system health: when failures accumulate, open circuit."""
    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None

    def execute(self, fn, *args, **kwargs):
        # NO RETRIES HERE - circuit sees raw system behavior
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
            else:
                raise Exception("Circuit is open")
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        if self._state == self.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._half_open_max:
                self._state = self.CLOSED
                self._failure_count = 0
        else:
            self._failure_count = 0

    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._failure_threshold:
            self._state = self.OPEN


class RetryPolicy:
    """Handles transient failures: retry with backoff."""
    def __init__(self, max_retries=3, base_delay=1):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def execute(self, fn, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)


def resilient_call(circuit_breaker, retry_policy, fn, *args, **kwargs):
    """Composition: retry layer → circuit breaker layer"""
    try:
        # First, try retries (handle transients)
        return retry_policy.execute(fn, *args, **kwargs)
    except Exception:
        # If retries fail, circuit breaker sees a real failure
        return circuit_breaker.execute(fn, *args, **kwargs)
```

**Why this addresses the problem:**

- Retries are now a separate concern with its own contract: "Try up to N times with backoff"
- Circuit breaker has a clear contract: "If X failures occur, open the circuit"  
- They're independent: changing RetryPolicy doesn't change what CircuitBreaker measures
- The composition is explicit: resilient_call shows the order and interaction

---

## DIAGNOSTIC APPLIED TO SECOND IMPROVEMENT

**What does this improvement conceal?**

It conceals the fact that **separating the code doesn't separate the measurement problem**.

Consider what happens:
- retry_policy.execute() tries 3 times, all fail
- resilient_call catches the exception
- circuit_breaker._on_failure() is called
- Circuit breaker now thinks: "1 failure occurred"

But actually: **3 failures occurred**. The circuit breaker is *still* measuring post-retry outcomes. We've just refactored the code, not solved the semantic problem.

Moreover: The ordering in resilient_call is wrong. If retry_policy exhausts retries and then calls circuit_breaker.execute(), we're sending a failed request *through* the circuit breaker. The circuit breaker will try *again*—but won't retry. This creates asymmetric behavior.

**What property of the original problem becomes visible ONLY through this improvement?**

The property that **code structure cannot fix semantic incoherence**.

By attempting to separate retries and circuit breaking into different classes, we've exposed: even with clean architecture, the measurement problem persists. We can:
- Make the code readable ✓
- Make the code modular ✓
- Make the concerns separable ✓

But we still haven't answered: **"What does the circuit breaker actually measure?"**

The code now makes this question *inescapably visible*, because the separation forces us to ask: in what order do retries and circuit breaking apply? What should the circuit breaker see—pre-retry or post-retry failures?

---

## THE STRUCTURAL INVARIANT

**"A circuit breaker must measure the health of a system to decide when to shed load. Any retry mechanism—whether internal or external—creates a filter between actual system failures and observed exceptions. This filter distorts the measurement. Therefore:**

**No circuit breaker configuration can simultaneously achieve:**
1. **Accurate measurement of pre-retry failure rates** AND
2. **Automatic recovery from transient failures** AND  
3. **Independence between retry configuration and failure threshold calibration**

**At least one must be sacrificed.**

The original code sacrifices #1 (accurate measurement). The first "improvement" sacrifices #3 (independence) while hiding it. The second improvement sacrifices #2 (it can't retry failures) or creates new asymmetries (different retry behavior depending on circuit state).

**This invariant persists through every code refactoring because:**
- It's not a property of implementation
- It's a property of the problem space (what exists between the circuit breaker and the actual system)
- The math is immutable: (actual failures) ≠ (observed exceptions after retries)
- You cannot engineer around a mathematical constraint with code structure

**The only way to break the invariant is to change the problem statement:**
- Remove retries entirely (measure true failure rate, accept higher latency)
- Make retries aware of circuit state (couple the layers, sacrificing modularity)
- Stop measuring system health, measure client experience instead (different metric entirely)

The original code avoids this choice, creating permanent incoherence. All improvements either hide the choice or relocate it to a different layer.
