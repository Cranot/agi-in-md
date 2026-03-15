# Circuit Breaker Analysis: Extracting the Inheritance Law

## V1's Emergent Properties (Reverse-Engineered)

Not in docstring, but callers discover:

1. **Retry transparency**: Retries are invisible to circuit state—only *final execute() outcome* increments failure counters. Internal `_retry_with_backoff()` failures don't trigger `_on_failure()`.
2. **Success amnesia**: Success unconditionally resets `_failure_count` (CLOSED) or advances close gate (HALF_OPEN). Previous bad period is *forgotten*.
3. **Failure-count isolation**: Only `execute()`-level failures count. If `fn()` fails, retries succeed—circuit sees 1 failure, not 3.
4. **Two independent knobs**: `failure_threshold` (count-based) and `reset_timeout` (time-based) operate orthogonally. Neither alone is sufficient.
5. **Half-open gating**: Recovery requires a *quota* (`half_open_max`) of successes, not infinite tries. This bounds recovery time.

---

## V2 Rewrites Violating Each Property

### V2-A: Retry leaks into state (violates #1, #3)
```python
def _retry_with_backoff(self, fn, *args, **kwargs):
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except:
            self._on_failure()  # Count each retry attempt
            if attempt == max_retries - 1:
                raise
```
**What breaks**: Single call with 3 failed retries now increments `_failure_count` by 3, not 1. A noisy upstream (recovers on retry-2) opens circuit faster than expected. Transient failures become persistent in the circuit's eyes.

### V2-B: No amnesia (violates #2)
```python
def _on_success(self):
    if self._state == self.HALF_OPEN:
        # ... close on quota
    # else: do nothing, never reset _failure_count
```
**What breaks**: One old failure from round 1 means the circuit is permanently "one failure away from opening." If service recovers then fails occasionally (10% rate), it opens on failure #2, stays open. Amnesia is the *only mechanism* that allows recovery and new trials.

### V2-C: Threshold-only (violates #4 — remove timeout)
```python
self._state = self.OPEN
# Never auto-resets. Manual intervention required or call with reset=True.
```
**What breaks**: Service recovers, but circuit stays open forever. No mechanism to test recovery. Operator must manually intervene or write wrapper code. Reliability is non-recoverable.

### V2-D: Timeout-only (violates #4 — remove count)
```python
def execute(self, fn, *args, **kwargs):
    if self._state == self.OPEN and time.time() - self._opened_at > 30:
        self._state = self.TESTING
    # No failure_threshold. Single failure opens.
```
**What breaks**: One transient glitch opens circuit. Service works 99% of the time, but brief hiccup takes it offline for 30s. Cannot distinguish noise from degradation. False-opens dominate.

---

## Across All Viable V2s: The Invariant

I can rewrite circuit in radically different ways—remove half_open_max, use sliding windows, use exponential moving averages—but *all viable versions* preserve:

**Invariant 1 (Failure-Retry Decoupling)**: 
Circuit state must not couple to retry logic's internal structure. Whether `fn()` uses 1 retry, 3, or exponential backoff, circuit sees only "final execute() result."

- Why conserved: Else changing retry strategy changes circuit behavior nonlinearly. Tuple (retry_count, circuit_state) explodes into impossible tuning space.
- Across V2s: Even a pure-count circuit (no timeout) preserves this. Retry wrapper above circuit preserves this.

**Invariant 2 (Threshold + Timeout Non-Substitution)**:
No viable circuit uses *only* count-based or *only* timeout-based recovery. Both are mathematically necessary.

- Count alone → eternal lockout if service recovers
- Timeout alone → false-opens on transient noise
- Both → graceful degradation

**Invariant 3 (Success-Reset in Baseline State)**:
When circuit is in its "normal operating" state (CLOSED), success must reset failure counters.

- Without this: Single old failure prevents *any* fresh tries.
- With this: Service can recover from transient spikes.

**Invariant 4 (Asymmetric Recovery Path)**:
Degradation (CLOSED→OPEN) can be *immediate* (if threshold crossed), but recovery (OPEN→CLOSED) must be *staged* and *time-gated*.

- Why: Recovery is dangerous (premature close causes cascade). Degradation is necessary (self-protection).

---

## Design a V2 Breaking the Invariant

**V2-BREAK: Merge timeout and threshold into single "confidence score"**

```python
def execute(self, fn, *args, **kwargs):
    try:
        result = fn(*args, **kwargs)
        self._confidence = min(1.0, self._confidence + 0.1)  # Success increases confidence
        if self._confidence > 0.8:
            self._state = self.CLOSED
        return result
    except:
        elapsed = time.time() - self._start_time
        self._confidence -= 0.2 * (elapsed / 30)  # Failures decay by time pressure
        if self._confidence < 0.2:
            self._state = self.OPEN
        raise
```

**Why breaking is forbidden**: 

Now timeout and count are entangled. Failures early in the window count more than failures late. Time affects failure weight. You've introduced *time-dependent severity*, which means:
1. Same failure sequence opens circuit faster or slower depending on *when* you try (non-idempotent)
2. An 8-hour-old bad period still shadows current decisions (memory bleed)
3. You can't tune the system: adjusting timeout changes failure weight implicitly.

This violates Invariant 2: threshold and timeout are no longer independent knobs. The system becomes **unmeasurable**.

V1's design is so "simple" it forces you to separate concerns. V2-BREAK's sophistication *hides* the coupling.

---

## The Inheritance Law

**Named: Graceful Degradation Requires Orthogonal Failure Axes**

**Formal statement**:
> Any circuit breaker implementation must maintain independence between (1) how many failures trigger opening, (2) how long opening lasts, and (3) how retry logic works internally. Violating this produces systems that are either permanently locked (no recovery), eternally fragile (false-opens), or unmeasurable (entangled parameters).

**Is it intentional, accidental, or emergent?**

**Intentional (bottom layer)**: Martin Fowler's pattern explicitly separates concerns:
- Retry = transient resilience
- Circuit = persistent degradation detection

**Accidental (middle layer)**: V1's author probably didn't think "I am preserving orthogonality of failure axes." They wrote what worked, and orthogonality fell out.

**Emergent (top layer)**: Teams discover this property by trying to tune the system. They find: "If I change max_retries, my circuit opens at different rates" (decoupling broken). So they revert and accept the current design.

---

## Feature or Bug-Turned-Feature?

**Success amnesia** (`_on_success()` resets `_failure_count` unconditionally in CLOSED state) is the key case:

**Originally a feature**: "Let the service retry transients and bounce back without circuit penalty."

**Became a bug**: A service with 10% error rate never opens circuit, because each success resets counters. Low-frequency persistent failures are invisible.

**Then turned back into a feature**: Teams realized they *want* this behavior—"If it recovers, I trust it again." So amnesia is actually the right call for CLOSED state. What was "too lenient" is actually "the only way to allow services to degrade gracefully without manual reset."

**The real bug is elsewhere**: The hidden failure mode is that you *can't distinguish* between:
- Service works 99%, occasional noise (amnesia is correct)
- Service works 60%, frequent failures (circuit should stay open longer)

Both look identical to the circuit. You'd need a *time window* ("count failures in the last 5 minutes") to fix this—which V1 *doesn't have*.

**Verdict**: Success amnesia is a **necessary bug—a feature implemented perfectly for the problem it's designed to solve, but that solution reveals an unfixable deeper problem: distinguishing transient from systemic requires context the circuit breaker doesn't have.**
