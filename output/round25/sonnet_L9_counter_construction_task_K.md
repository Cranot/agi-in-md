# Circuit Breaker: Counter-Construction Analysis

---

## I. The Falsifiable Claim

**The deepest structural problem is a policy collision hidden by co-location: retry and circuit breaking encode mutually contradictory assumptions about failure, fused into one object so neither policy can function correctly, but each individually looks correct.**

Specifically: retry assumes "this failure is transient, keep trying." Circuit breaking assumes "accumulated failures signal systemic collapse, stop trying." These are *logically incompatible stances toward the same event*, and fusing them means each policy's observable inputs are corrupted by the other's actions.

---

## II. Three Experts

### Expert A — Defender
The claim holds precisely. The corruption is measurable:

```
Actual failures required to open circuit = failure_threshold × max_retries
                                         = 5 × 3 = 15
```

The circuit breaker's state machine operates on *retry-exhausted events*, not *failure events*. `failure_threshold=5` is a lie — the real threshold is 15. This is not configurable, not documented, and not obvious. The state machine's semantics are incoherent as written.

### Expert B — Attacker
The claim is too narrow. The *actual* deepest problem is that there is **zero thread safety**. Every field — `_state`, `_failure_count`, `_success_count`, `_last_failure_time` — is unprotected mutable state. In any realistic deployment:

```python
# Thread A: reads _state == CLOSED
# Thread B: reads _state == CLOSED
# Thread A: fn() fails, _failure_count becomes 4
# Thread B: fn() fails, _failure_count becomes 4 (not 5)
# Circuit never opens despite threshold being met
```

Even if you fixed the retry/breaker fusion, you'd still have a broken circuit breaker. The policy collision is a *design* problem; the thread unsafety is a *correctness* problem that exists independently.

### Expert C — Probing Assumptions
Both of you assume the state machine *correctly models* failure in principle and the problems are implementation errors. But what do you both take for granted?

You assume **failure is binary** — exception or not. The code never asks: is this failure the same *kind* as previous failures? It also assumes `_last_failure_time` is a meaningful clock anchor. But notice: `_last_failure_time` is updated on *every* failure, so if failures are continuous, the reset window keeps sliding forward. In OPEN state this is actually fine (no new failures are recorded), but what about HALF_OPEN? In HALF_OPEN, retries can cause `_on_failure()` to fire, re-entering OPEN — the probe window collapses immediately. Neither of you examined what happens when these state transitions interact with the retry backoff timing.

---

## III. Claim Transforms

**Transformed claim:** The deepest structural problem is an *architectural category error*: the code uses a single object to implement two orthogonal failure philosophies (retry = "failures are local and transient"; circuit breaking = "failures are systemic and persistent") that cannot share a failure counter, a state machine, or a thread context without each corrupting the other's inputs. Thread unsafety means even a philosophically coherent design would malfunction at runtime.

**The gap:** My original claim identified semantic miscounting. The transformed claim reveals *active mutual interference* — retry doesn't just miscount for the breaker, it physically delays the breaker's response by inserting sleep inside the hot path, and the breaker doesn't just count wrong, it multiplies probe traffic in HALF_OPEN by `max_retries`. Each policy makes the other's worst-case behavior worse.

---

## IV. The Concealment Mechanism

**Structural Plausibility Through Named Pattern Co-location.**

Each component (exponential backoff retry, three-state circuit breaker) is a recognizable, named pattern. Code reviewers pattern-match to "circuit breaker with retry" and grant each piece independent credibility. The *interaction* between pieces is never reviewed as a first-class concern because it is not a separate piece — it is implicit in the method call chain:

```
execute() → _retry_with_backoff() → [implicit] → _on_success()/_on_failure()
```

The interaction lives in call order, not in the class interface. It is invisible to API-level review, invisible to unit tests of individual methods, and invisible to type checking. The named patterns act as *cognitive load reducers* that suppress scrutiny of the composition.

Three additional concealment layers:
- Thread safety is an *operational* concern that appears only at runtime under concurrency
- The miscounting (`5 × 3 = 15`) requires tracing two numerical parameters across two method boundaries
- HALF_OPEN probe amplification requires understanding state machine transitions *and* retry behavior simultaneously

---

## V. The Legitimate-Looking Improvement That Deepens Concealment

**Add exception classification to the retry mechanism:**

```python
def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1,
                        retryable=(ConnectionError, TimeoutError), **kwargs):
    """
    Retries only on transient errors. Non-retryable exceptions fail immediately.
    Prevents unnecessary load during hard failures (e.g., bad auth, 404s).
    """
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except retryable as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
        except Exception:
            raise  # Non-retryable: fail fast, let circuit breaker decide

    # Unreachable but explicit for static analysis
    raise RuntimeError("Retry loop exited without result")
```

**Why this passes code review:** Exception classification is correct engineering practice, documented, reduces unnecessary load, and the docstring is accurate. Any reviewer would approve this — it's an improvement.

**Why this deepens concealment:**

The improvement adds a new, silent axis: now `retryable` and `_failure_threshold` are *two independent definitions of "what counts as a failure"* that can diverge in production without warning.

A `ValueError` (non-retryable) reaches `_on_failure()` immediately — counts as 1 failure event.  
A `TimeoutError` (retryable) exhausts 3 retries before reaching `_on_failure()` — also counts as 1 failure event.

The circuit breaker now receives a *mixed, non-homogeneous signal* and treats it as homogeneous. The improvement made the system look more sophisticated while making the failure signal *more* semantically corrupt. Reviewers see the classification and think "good, the breaker only sees real failures now" — but the threshold's calibration is now *less* meaningful, not more.

---

## VI. Three Properties Visible Only Because I Tried to Strengthen It

**1. Exception classification and circuit-trip conditions are semantically independent axes that the architecture forces into a single counter.**

When you add `retryable`, you're forced to ask: "Should a `ValueError` trip the circuit?" The code says yes — it reaches `_on_failure()`. But a `ValueError` might indicate a bug in the *caller*, not a systemic failure in the *service*. The architecture has no concept of failure *attribution*. This was invisible before because all exceptions looked the same.

**2. The `failure_threshold` is uncalibratable without knowing the retry configuration.**

With exception classification in place, you realize: if most failures are `TimeoutError` (retryable), `failure_threshold=5` means the service must fail 15 times. If most failures are `ValueError` (non-retryable), it means 5 times. The same parameter means different things depending on the failure distribution, which is runtime-determined. This incoherence was always present but the improvement made it *observable* by creating a path where single failures reach the counter.

**3. HALF_OPEN retry amplification is the most dangerous combination the architecture can produce.**

The improvement adds a fast-fail path for non-retryable exceptions, which exposes by contrast that *retryable* exceptions in HALF_OPEN state will each trigger up to 3 actual requests to the downstream system. HALF_OPEN is supposed to send *minimal probe traffic*. The improvement makes you realize that `half_open_max=3` combined with `max_retries=3` means up to 9 actual requests before the circuit closes — and this is only after 3 *successful* exhausted-retry events, which is architecturally incoherent. You can't have a "successful retry" count toward HALF_OPEN recovery.

---

## VII. The Contradicting Improvement

**Dissolve the retry subsystem and give the circuit breaker direct failure observation:**

```python
class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3,
                 max_attempts=1, base_delay=1.0):
        """
        max_attempts: total attempts per execute() call (1 = no retry).
        Circuit breaker observes EVERY failure attempt, not retry-exhausted events.
        """
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._last_failure_time = None

    def execute(self, fn, *args, **kwargs):
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
            else:
                raise Exception("Circuit is open")

        last_exception = None
        for attempt in range(self._max_attempts):
            try:
                result = fn(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                last_exception = e
                self._on_failure()          # Circuit breaker sees every attempt
                if self._state == self.OPEN:
                    raise                   # Stop immediately if circuit just opened
                if attempt < self._max_attempts - 1:
                    delay = self._base_delay * (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(delay)

        raise last_exception
```

**Why this passes code review:** Simpler, more direct, correctly documented (`max_attempts=1` defaults to no retry, easy to reason about). The circuit breaker now observes actual failure events. Any reviewer would approve this — it's cleaner and the semantics are explicit.

**Why it contradicts Improvement 1:**

| | Improvement 1 | Improvement 2 |
|---|---|---|
| Retry responsibility | Separate method, rich exception classification | Inlined in `execute`, no classification |
| Failure signal to breaker | Coarse (retry-exhausted events only) | Fine (every attempt) |
| Threshold meaning | Retry-cascade events | Individual failure attempts |
| HALF_OPEN probes | Multiplied by retries | Exactly `max_attempts` per call |

Improvement 1 says: *retry filters failures before the breaker sees them.*  
Improvement 2 says: *the breaker should see all failures, retry is just repeated attempts.*

Both are legitimate architectural positions. Both are documented. Both pass review. Both are genuine improvements over the original. They are *incompatible*.

---

## VIII. The Structural Conflict

**The Granularity of Failure Observation Is Architecturally Undefined.**

The original code never answers: *at what granularity should the circuit breaker count failures?* It accidentally implemented coarse granularity (retry-exhausted events) without documenting it.

Improvement 1 made coarse granularity *explicit and richer* — the filter is sophisticated.  
Improvement 2 switched to fine granularity *also explicitly* — the breaker sees everything.

The conflict is not "which improvement is better" — it is that **the original architecture contains no structure that could adjudicate between them.** Both improvements are legitimate precisely because the original code left the granularity question unanswered. The answer you choose changes:

- The effective failure threshold by a factor of `max_retries`
- HALF_OPEN probe load by a factor of `max_attempts`
- Whether `failure_threshold` is calibrated against requests or against operations

**The concealment mechanism succeeds here:** reviewers of the original saw "circuit breaker with retry" and imported a mental model from one of the two legitimate architectures. They never asked which one, because the named patterns made the code feel complete. The structural conflict exists *only* because both improvements are legitimate — if one were wrong, the question would be answered. The wrongness would be diagnostic. But both are right, which means the original code has a load-bearing ambiguity that no amount of local improvement can resolve without an explicit architectural decision about the responsibility boundary between retry and circuit breaking.

**The real fix is separation:** `RetryPolicy` and `CircuitBreaker` as independent objects, composed at a higher level, with explicit contracts about what events cross the boundary.
