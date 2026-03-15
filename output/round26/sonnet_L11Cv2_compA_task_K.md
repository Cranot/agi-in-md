# Structural Analysis: Retry + Circuit Breaker

---

## I. The Falsifiable Claim

**Claim**: The retry loop runs *inside* the circuit breaker's state boundary, causing the HALF_OPEN probe mechanism to multiply its traffic by `max_retries`, and causing failure signals to arrive at the state machine with distorted temporal signatures — making the circuit slower to open than its thresholds imply and louder than intended during recovery.

**Testable prediction**: With defaults (`failure_threshold=5`, `max_retries=3`, `base_delay=1`), the circuit cannot open in less than ~52 seconds of real time, despite appearing to open after 5 failures. Each "failure" actually consists of 3 requests + ~7 seconds of sleep. And during HALF_OPEN with `half_open_max=3`, up to 9 requests reach the downstream service, not 3.

---

## II. Three Experts

**Defender**: "The retry-inside-circuit is appropriate. Each circuit *attempt* deserves a fair chance before counting as a failure. The circuit breaker is about sustained service degradation, not individual request outcome. Wrapping retries inside the breaker means the breaker only opens on genuine, retry-resistant failures."

**Attacker**: "HALF_OPEN exists specifically to send *controlled* probe traffic — a single exploratory request to check if the service recovered. `max_retries=3` means each probe is actually three requests. The service, already recovering from overload, receives triple the load the operator intended. The protection mechanism is its own attack. Further: in OPEN state, every concurrent thread independently reads `_last_failure_time`, computes the timeout, and races to set `_state = self.HALF_OPEN`. There's no lock. The 'controlled' probe is actually unlimited concurrent probes."

**Assumption-prober**: "What is the circuit breaker counting? It counts *outcomes-after-retries*, not *request-failures*. This embeds a hidden assumption: that failure is a binary property of an attempt, not a rate property of a stream. But a service failing instantly 3 times looks identical to one slow failure — both register as one `_on_failure()` increment. The code assumes failure *type* is irrelevant; only failure *count* matters. But a service that fails at 100ms (fast-failing, maybe overloaded) vs. one that fails at timeout (slow-failing, maybe hanging) produce identical signals to this circuit breaker."

**Gap between original and transformed claim**: The original claim was about *request count multiplication*. The expert debate reveals the deeper issue: *failure signals are temporally distorted*. The retry backoff turns fast failures into slow ones, meaning the circuit breaker's `reset_timeout=30` was implicitly calibrated against a failure velocity that doesn't exist — it's calibrated for raw failures, but receives smoothed, time-dilated ones.

---

## III. The Concealment Mechanism

**Name**: *Metric Shadow via Abstraction Boundary*

`_retry_with_backoff` is marked private, named as an "implementation detail," and called as the last thing before `_on_success`/`_on_failure`. The abstraction boundary between `execute` and `_retry_with_backoff` is precisely where the failure signal is transformed. The circuit breaker observes a *derived* metric (post-retry outcome) while believing it observes a *primary* metric (individual request fate). The private prefix makes the coupling invisible to callers; the layered call structure makes it invisible in review.

**Applied**: The concealment works because `_retry_with_backoff` looks like infrastructure (backoff is obviously "how" not "what"), while the circuit breaker looks like policy ("when to open"). The reader's mental model splits them cleanly. But they're not separate — the retry behavior determines *how fast* the circuit accumulates failures and *how much load* it sends during HALF_OPEN. The separation is syntactic, not semantic.

---

## IV. Improvement That Deepens the Concealment

```python
def execute(self, fn, *args, **kwargs):
    if self._state == self.OPEN:
        if time.time() - self._last_failure_time > self._reset_timeout:
            self._state = self.HALF_OPEN
            self._success_count = 0
        else:
            raise Exception("Circuit is open")

    # Limit retries during probe phase to protect recovering services
    max_retries = 1 if self._state == self.HALF_OPEN else 3

    try:
        result = self._retry_with_backoff(fn, *args, max_retries=max_retries, **kwargs)
        self._on_success()
        return result
    except Exception as e:
        self._on_failure()
        raise
```

**Why this passes review**: It directly addresses the stated probe-multiplication problem. A reviewer says "good catch on HALF_OPEN." The code now *appears* to understand circuit state semantics. Confidence increases.

**Why it deepens concealment**:
1. It fixes the visible symptom (probe × retries in HALF_OPEN) while leaving the structural coupling intact in CLOSED state.
2. It introduces state-dependent retry policy *inside* the circuit, making them more coupled, not less — while looking like a decoupling fix.
3. The fix draws attention to HALF_OPEN as if it's the only state with this problem, reducing scrutiny of CLOSED state behavior.
4. It adds a state read (`self._state`) that is not protected by a lock, making a race condition *more consequential* (max_retries could be 1 or 3 based on a stale state read) while looking like careful state handling.

---

## V. Three Properties Visible Only From Attempting Strengthening

**1. State consistency requirements are now multi-point.**
By making `max_retries` depend on `self._state`, I revealed that the state must be consistent across the `execute` function's entire execution — from the initial state check through `_retry_with_backoff` to `_on_success`/`_on_failure`. The original code had a latent requirement that state not change mid-execution. The improvement makes this requirement load-bearing, which makes it visible.

**2. Retry policy is semantically part of circuit state.**
By conditioning max_retries on state, I revealed that the retry policy is not infrastructure — it *is* circuit behavior. This makes visible that the design question isn't "where does retry live?" but "should retry count be a first-class property of the circuit's state machine?" The original code answered this question implicitly (no) while appearing not to have considered it.

**3. HALF_OPEN has no concept of concurrent in-flight requests.**
Trying to fix HALF_OPEN probe behavior revealed that `half_open_max` counts *successful completions*, not *concurrent probes*. Multiple threads can all simultaneously enter HALF_OPEN and simultaneously dispatch probes. The improvement focuses attention on this state, making visible that the half-open semantics are structurally underspecified: there's no mechanism to limit concurrent probe traffic, only to count eventual successes.

---

## VI. What the Improvement Conceals

The improvement conceals: **the state machine has no model of concurrent execution**. By fixing HALF_OPEN probe multiplication (a correctness concern), the improvement makes the code *look* more state-aware, reducing scrutiny of thread safety. Every state read and write is a race condition. `_state`, `_failure_count`, `_success_count`, and `_last_failure_time` are all mutated without locks in a system where circuit breakers are used precisely when systems are under concurrent load.

**What property of the original is visible only because the improvement recreates it?**

The original's `max_retries=3` hardcoded in `_retry_with_backoff` was implicitly a parameter of the circuit's *failure velocity* — it determined how fast `_on_failure()` could be called, which determined whether `reset_timeout=30` was calibrated correctly. The improvement makes `max_retries` state-dependent, which reveals that the original parameters `reset_timeout`, `failure_threshold`, and the retry backoff schedule are *jointly calibrated* — changing one changes the meaning of the others. The improvement breaks this implicit joint calibration, making it visible by breaking it.

---

## VII. Second Improvement

```python
import threading

class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None
        self._lock = threading.RLock()
        self._half_open_inflight = 0

    def execute(self, fn, *args, **kwargs):
        with self._lock:
            state = self._current_state()
            if state == self.OPEN:
                raise Exception("Circuit is open")
            if state == self.HALF_OPEN:
                if self._half_open_inflight >= self._half_open_max:
                    raise Exception("Half-open probe slots exhausted")
                self._half_open_inflight += 1

        try:
            result = fn(*args, **kwargs)  # retries extracted to caller
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
        finally:
            with self._lock:
                if self._state == self.HALF_OPEN:
                    self._half_open_inflight -= 1

    def _current_state(self):
        """Must be called under lock."""
        if (self._state == self.OPEN
                and self._last_failure_time is not None
                and time.time() - self._last_failure_time > self._reset_timeout):
            self._state = self.HALF_OPEN
            self._success_count = 0
            self._half_open_inflight = 0
        return self._state

    def _on_success(self):
        with self._lock:
            if self._state == self.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._half_open_max:
                    self._state = self.CLOSED
                    self._failure_count = 0
            else:
                self._failure_count = 0

    def _on_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self._failure_threshold:
                self._state = self.OPEN
```

**Applying the diagnostic to the second improvement:**

**What does it conceal?** Removing retries from the circuit breaker didn't remove retries from the system — it removed them entirely. The second improvement reveals that retries were load-bearing: they provided transient-fault tolerance that the circuit breaker alone cannot provide. The improvement conceals that the caller now has no retry guidance, creating a new class of problem: callers that retry aggressively *around* the circuit breaker will defeat it from outside. The boundary moved; the problem didn't.

More subtly: the lock creates an apparent solution to concurrency while concealing a *liveness* risk. The `finally` block decrements `_half_open_inflight`, but if a thread dies between `_half_open_inflight += 1` and the `finally`, the slot is permanently consumed. In most Python runtimes this is unlikely, but the design *looks* correct while having a semantic hole.

**What property of the original is visible because the improvement recreates it?**

The original conflated retry and circuit behavior. By separating them, the second improvement reveals that *whoever provides retry behavior must share state with the circuit breaker* — otherwise retries defeat the circuit. The original's conflation was not just sloppiness; it was a real coupling that the system requires. The improvement doesn't resolve this coupling; it externalizes it and makes it someone else's problem to manage.

---

## VIII. The Structural Invariant

**Across every version, one property persists unchanged:**

> The circuit breaker must make a binary present-moment decision (allow/deny) using only information from a closed past window, but its decision alters the information that future windows will contain.

Every improvement moves the boundary of the past window (with locks, with inflight tracking, with retry policy) but cannot escape this structure. The circuit breaker's observations and its interventions are causally entangled: opening the circuit prevents failures that would have been observed; closing it admits load that produces the failures it measures. The state machine is modeling a system of which it is a component — it is not an external observer.

---

## IX. Inversion

**The impossible in every design above**: you cannot simultaneously minimize the lag between failure events and state transitions AND minimize the circuit breaker's influence on the service state it's measuring. Faster response to failure = more influence over load = more distorted future observations.

**Invert it — engineer a design where this is trivially solved:**

```python
class CooperativeCircuitBreaker:
    """
    The service reports its own state. The circuit breaker does not observe
    outcomes — it relays the service's self-assessment.
    """
    def __init__(self, health_endpoint):
        self._health_endpoint = health_endpoint
        self._open = False

    def execute(self, fn, *args, **kwargs):
        # No observation of outcomes. Service decides circuit state.
        status = requests.get(self._health_endpoint, timeout=0.1).json()
        if status["circuit"] == "open":
            raise Exception("Service requested circuit open")
        return fn(*args, **kwargs)
        # No _on_success, no _on_failure.
```

The service now controls its own circuit: it publishes `{"circuit": "open"}` when overloaded, `{"circuit": "closed"}` when ready. The observer/intervention entanglement is dissolved — the circuit breaker no longer influences the signal it observes, because it no longer generates the signal. Zero information lag (the service reports current state). Zero self-influence (the breaker doesn't count or distort anything).

**The new impossibility**: The health endpoint is a network request. It can fail. It will fail hardest precisely when the service is in the state where circuit intervention is most needed — during overload, the health endpoint is the first thing to timeout. The cooperative circuit breaker cannot reach the service to learn it should open the circuit, in exactly the moment it most needs to open it. The mechanism for communicating state requires the channel the circuit is supposed to protect.

Further: the service's self-report is a prediction about its own future behavior, which is a function of the load the circuit allows, which is a function of the service's self-report. The cooperative design moves the feedback loop inside the service, where it's harder to observe, not outside it.

---

## X. The Conservation Law

**Statement**: 

> Whatever information channel a circuit breaker uses to observe system state is simultaneously the channel it cannot observe without bias, because circuit intervention alters that channel's signal in proportion to the circuit's effectiveness.

This is not the sensitivity/specificity trade-off (senior engineers already know that). It's not the threshold-tuning problem (also known). 

**What it reveals beyond senior-engineer knowledge:**

The conservation law says circuit breaker design is a *choice of projection*, not a choice of parameters. Every circuit breaker projects a high-dimensional service state (request rate, error rate by type, latency distribution, downstream dependency health, load shedding status) onto a 1-dimensional axis (open/closed). The projection discards information. The discarded information always includes the dimensions that would distinguish "my intervention is helping the service recover" from "my intervention is masking a different problem." 

This is not tunable. It's structural. Parameters tune the *sensitivity* of the projection; they don't change what the projection discards. The reason circuit breakers are hard to configure in production is not that engineers pick wrong thresholds — it's that every threshold implicitly defines a projection, and different failure modes require different projections. A single circuit breaker can be optimally configured for one failure mode and systematically wrong about all others.

**What it predicts about a third design (cooperative):**

The cooperative design will fail to achieve coordination in exactly the scenario it was designed for. The prediction: teams deploying cooperative circuit breakers will add a fallback — a timeout or error-count threshold on the health endpoint itself — that recreates the original circuit breaker's structure *as a meta-circuit for the health channel*. The conservation law says this meta-circuit will have the same problem: its observation channel (health endpoint responses) is exactly what is unavailable during the failure it's supposed to detect. The third design doesn't escape the law; it instantiates a second copy of the original problem, one level up, with less visibility into it.

The law's conservation form: *the impossibility doesn't move — it reflects.* The original design couldn't observe the effect of its interventions. The inverted design can't reach the observer to intervene. These are the same impossibility, mirrored across the service boundary. Any third design that tries to bridge them will instantiate the impossibility at the bridge itself.
