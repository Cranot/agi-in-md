## Structural Analysis: Retry Mechanism with Circuit Breaker

---

### The Claim

**The circuit breaker's `failure_threshold` parameter is semantically undefined.** It counts "exhausted retry-chain events," not "service invocation failures." With `failure_threshold=5` and `max_retries=3`, the circuit opens after 15 actual service calls — the opposite of what circuit breakers exist to do. This is falsifiable: instrument the code, call a permanently-failing service, count actual HTTP calls before the circuit opens. You will get `failure_threshold × max_retries`, not `failure_threshold`.

---

### Three Experts

**Defender:** Counting operation-level failures, not attempt-level, is intentional and correct. The circuit breaker should track whether logical operations succeed, not whether individual network calls succeed. Transient failures are the retry's domain; structural failures are the circuit breaker's. The composition is appropriate.

**Attacker:** The composition breaks the HALF_OPEN probe. HALF_OPEN is designed to send a single controlled test request to determine if the service recovered. Instead, `execute()` in HALF_OPEN sends up to `max_retries` requests per call. The probe is not a probe — it's a burst. The `half_open_max` parameter cannot control what it appears to control.

**Prober (what both take for granted):** Both assume the circuit breaker and retry mechanism share a coherent definition of time. The defender's "logical operation" and the attacker's "probe" both assume you can meaningfully separate retry time from circuit-breaker time. But the actual question neither asks: **what is the correct atomic unit of failure for this system?** Both take for granted that a failure threshold is meaningful at all when the unit being counted is undefined. The circuit breaker is measuring something, but neither expert can say what.

---

### Claim Transformation

**Original:** The circuit breaker counts the wrong unit — retry-chain exhaustion instead of service calls.

**Transformed:** The circuit breaker and retry mechanism have incompatible atomicity assumptions about what constitutes a failure event. The code silently resolves this conflict by choosing operation-level atomicity without declaring it, rendering `failure_threshold` semantically opaque — a number that appears tunable but cannot be reasoned about without knowing the hidden multiplier it contains.

**The Gap:** I started with a counting error. The three-expert process revealed this is a *semantic contract violation* — the parameter's name promises one thing, its implementation delivers another, and the gap is invisible at the call site.

---

### Concealment Mechanism: Parameter Plausibility

The code hides its real problem through **naming that implies a coherent model**.

`failure_threshold=5` looks like a tunable, domain-meaningful parameter. Reviewers read it as: "open the circuit after 5 failures." The implementation makes it: "open the circuit after 5 exhausted 3-attempt sequences." The parameter's name launders its semantics — the word "failure" is shared between the caller's mental model and the implementation's behavior, but they refer to different things. No single line of code is wrong. The problem exists only in the space between the signature and the implementation.

**Applied:** Trace any bug report. "The circuit isn't opening fast enough." The operator increases `failure_threshold` from 5 to 3. Nothing changes proportionally, because the real problem is `max_retries`. But `max_retries` isn't exposed at the `execute()` interface. The operator adjusts the visible knob; the hidden multiplier remains fixed.

---

### Improvement 1: Expose Retry Configuration (Deepens Concealment)

```python
def execute(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
    if self._state == self.OPEN:
        if time.time() - self._last_failure_time > self._reset_timeout:
            self._state = self.HALF_OPEN
            self._success_count = 0
        else:
            raise Exception("Circuit is open")

    try:
        result = self._retry_with_backoff(
            fn, *args,
            max_retries=max_retries,
            base_delay=base_delay,
            **kwargs
        )
        self._on_success()
        return result
    except Exception:
        self._on_failure()
        raise
```

**Why this passes review:** Increases flexibility. Callers can tune retry behavior per-operation. Standard good practice — configuration over hardcoding. A reviewer sees this and thinks: "finally, the retry parameters are exposed properly."

**Why this deepens concealment:** It makes the `failure_threshold` ↔ `max_retries` interaction caller-controllable and therefore invisible at the class level. The effective sensitivity of the circuit breaker now depends on how each caller happens to call it. A service with two callers — one using `max_retries=1`, one using `max_retries=10` — will have a circuit breaker whose behavior cannot be described without knowing the call distribution. This looks like flexibility. It is opacity with a better API.

---

### Three Properties Visible Only From Strengthening

**1. The threshold is not a threshold — it is a rate function.** By making `max_retries` per-call variable, it becomes clear that `failure_threshold` defines a relationship between call frequency, retry count, and circuit state that cannot be expressed as a single number. "5 failures" means nothing without knowing the retry multiplier, which is now variable. The parameter is not a threshold; it is one input to an implicit equation.

**2. HALF_OPEN is structurally unprobeable.** Once `max_retries` is caller-controlled, HALF_OPEN cannot guarantee controlled probing regardless of `half_open_max`. A caller passing `max_retries=50` in HALF_OPEN sends 50 requests in what should be a single probe. `half_open_max` controls how many *operation-level successes* trigger recovery, but cannot bound actual service calls. These two parameters control orthogonal things and the code presents them as if they are the same dimension.

**3. The `_on_failure()` call site is in the wrong scope.** It is called once per `execute()` invocation, regardless of how many retries occurred. Making retries configurable makes this visible: if a caller passes `max_retries=1`, the circuit breaker is more responsive. If they pass `max_retries=10`, less responsive. The failure accounting is anchored to the wrong scope, and the scope is now clearly caller-dependent. Before this improvement, the scope was at least consistently wrong.

---

### Improvement 2: Count Individual Attempt Failures (Contradicts Improvement 1)

```python
def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            self._last_failure_time = time.time()
            self._failure_count += 1
            if self._failure_count >= self._failure_threshold:
                self._state = self.OPEN
                raise Exception("Circuit opened mid-retry") from e
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

**Why this passes review:** Makes the circuit breaker more responsive. Every failed attempt now counts toward opening. This is arguably more correct — each actual service call failure is evidence of service health. Reviewer thinks: "good, now the circuit reacts to real failures, not just retry exhaustion."

**Why this contradicts Improvement 1:** Improvement 1 treats retry and circuit-breaking as separable concerns that can be independently configured. Improvement 2 fuses them — the retry loop directly mutates circuit breaker state. You cannot take Improvement 1's per-call `max_retries` and combine it with Improvement 2's internal state mutation without making the circuit breaker's behavior fully dependent on call-site decisions the circuit breaker cannot see or control.

---

### The Structural Conflict

Improvement 1 requires that retry and circuit-breaking are **independent concerns with a clean interface between them** — the circuit breaker receives an outcome, the retry mechanism produces one, they are composed but not coupled.

Improvement 2 requires that retry and circuit-breaking are **unified concerns sharing state** — the retry loop is an internal mechanism of the circuit breaker, not a separate component being coordinated.

Both improvements are legitimate within their own frame. The conflict exists only because both are legitimate. If one were clearly wrong, we would pick the other and the conflict would dissolve. Instead, the conflict is irreducible:

> **The circuit breaker cannot decide whether it is a policy owner (Improvement 2) or a policy enforcer over external policies (Improvement 1), because the original code made that decision implicitly and then named it wrong.**

This conflict is a finding: **the architecture has a hidden ownership boundary that was never drawn.** Both improvements draw it differently, both are defensible, and the artifact cannot accommodate both simultaneously. That is not a design tradeoff. It is a design decision that was not made.

---

### What Category Does the Conflict Assume?

Both improvements assume this artifact belongs to the category: **reliability primitive** — a composable building block like a lock, a semaphore, or a rate limiter. Primitives can be configured (Improvement 1) or made more precise (Improvement 2) without changing what they fundamentally are.

This assumption is why both improvements feel right and why both fail.

---

### What the Artifact Actually Is

The artifact is a **reliability workflow controller**.

A circuit breaker *primitive* owns state (OPEN/CLOSED/HALF_OPEN) and exposes a gate (`can_attempt()`, `record_success()`, `record_failure()`). It does not own retry strategy.

A retry primitive owns backoff logic and attempt counting. It does not own circuit state.

This code owns both, has permanently composed them into a specific workflow (`retry-then-report-to-circuit-breaker`), and named the result after one of its components. The class name "CircuitBreaker" claims primitive identity. The implementation is a workflow with a hardcoded composition of two primitives, neither of which exists independently.

This identity is only visible because:
- Improvement 1 tried to treat it as a configurable primitive → created an uncontrollable multiplier
- Improvement 2 tried to make the workflow coherent → destroyed the separation both improvements assumed

The artifact resists both because it is neither primitive nor clean workflow. It is a **specific, unnamed composition** that cannot be improved at the component level because the components were never separated. The real structural problem is not the retry-inside-circuit-breaker logic. It is that the code **conceals its composition as a component**, and every legitimate improvement reinforces the concealment by engaging with the component interface rather than surfacing the composition.

The fix is not to improve `CircuitBreaker`. It is to decompose it:

```python
# What the code actually is, made visible
breaker = CircuitBreaker(failure_threshold=5, reset_timeout=30)
retry = RetryPolicy(max_retries=3, base_delay=1)

def execute(fn, *args, **kwargs):
    breaker.guard()                          # raises if OPEN
    try:
        result = retry.execute(fn, *args, **kwargs)
        breaker.record_success()
        return result
    except Exception:
        breaker.record_failure()             # counts once per operation
        raise
```

Now `failure_threshold` means what it says. Now HALF_OPEN probes are controllable. Now retry policy and circuit policy are independently tunable. The conflict dissolves not because a better improvement was found, but because the hidden composition was made explicit and the false component identity was abandoned.
