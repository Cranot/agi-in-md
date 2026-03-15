# Structural Diagnostic: AdaptiveRateGovernor

---

## I. The Initial Claim

**Specific, falsifiable claim:** The code's deepest structural problem is that `allow()` and `record_outcome()` share no causal linkage — a quality score can be recorded with no prior `allow()` call, and the rate adapts based on scores that cannot be attributed to specific controlled requests. The feedback loop has no causal closure.

*Falsifiable because:* if quality scores were causally linked to allowed requests, the adaptation would produce observably different behavior under adversarial inputs (e.g., inflated scores on requests that were never gated).

---

## II. Three Experts

**Defender:** The claim holds precisely. Nothing prevents a caller from calling `record_outcome(1.0)` a hundred times with no prior `allow()` calls. The rate will increase, gating real requests, based on phantom outcomes. The `_outcomes` deque contains timestamps and scores but zero information about which — or whether — a request was controlled.

**Attacker:** The claim misidentifies the symptom as the disease. Many real adaptive systems intentionally decouple control from feedback (TCP congestion control treats packet loss as ambient signal, not per-packet outcome). The actual errors are: (1) `_rate_limit` is a float being compared to `len(self._requests)` (integer), silently truncating; (2) multiplicative growth (`* 1.5` each step) with a fixed ceiling of 1000 means the system can reach max in ~7 steps but recovers slowly; (3) `_adjustments` is an append-only list that is never expired — unlike every other stateful structure in the class.

**Probe (what both take for granted):** Both assume `_rate_limit` is a well-defined quantity. Neither noticed that it serves three different roles simultaneously: a count threshold (used in `allow()`), a denominator in a ratio (used in `get_pressure()`), and a learning target (mutated in `_maybe_adjust()`). These roles have different consistency requirements. Both also assume the class has a single responsibility. But it is secretly two systems: an *enforcer* (binary, present-tense) and a *learner* (continuous, future-tense). Their consistency requirements are in direct tension — the enforcer needs `_rate_limit` to be stable during a decision; the learner needs it to be mutable in response to evidence.

---

## III. The Gap and the Transformation

**Original claim:** The feedback loop has no causal closure.

**Transformed claim:** The class maintains a *single mutable value* (`_rate_limit`) that is simultaneously the output of a learning function and the input to an enforcement function. The causal decoupling is the *symptom*; the enforcer/learner duality with shared mutable state is the *disease*. Every attempt to fix the symptom will recreate the disease in a new form.

**The gap:** I claimed the problem was about correlation tracking. The three-expert process revealed the problem is about role incompatibility — the class is trying to be two things with contradictory consistency requirements.

---

## IV. The Concealment Mechanism

**Metric Plausibility Masking**

The code generates three numerically plausible, continuously-changing outputs: `get_effective_rate()`, `get_pressure()`, and `_adjustments`. These outputs respond to inputs, stay within bounds, and accumulate history — all the hallmarks of a working feedback system. The structural problem (two incompatible roles sharing mutable state) is invisible because *each role individually produces locally correct output*. You cannot see the problem by examining any single value at any single moment. You can only see it by observing contradictions across time when both roles are simultaneously active.

---

## V. The Improvement That Deepens Concealment

This passes code review: it adds request correlation, input validation, adjustment throttling, and type annotations — all legitimate improvements.

```python
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

@dataclass
class RequestRecord:
    timestamp: float
    request_id: str
    quality_score: Optional[float] = None
    resolved_at: Optional[float] = None

class AdaptiveRateGovernor:
    def __init__(self, initial_rate=10, window=60, sensitivity=0.5):
        self._rate_limit = initial_rate
        self._window = window
        self._sensitivity = sensitivity
        self._requests: deque[RequestRecord] = deque()
        self._pending: dict[str, RequestRecord] = {}
        self._adjustments: list[dict] = []
        self._adjustment_cooldown = 10.0
        self._last_adjustment = 0.0

    def allow(self, request_id: str) -> bool:
        now = time.time()
        self._expire(now)
        if len(self._requests) >= int(self._rate_limit):
            return False
        record = RequestRecord(timestamp=now, request_id=request_id)
        self._requests.append(record)
        self._pending[request_id] = record
        return True

    def record_outcome(self, request_id: str, quality_score: float) -> None:
        if not 0.0 <= quality_score <= 1.0:
            raise ValueError(f"quality_score must be in [0, 1], got {quality_score}")
        now = time.time()
        if request_id in self._pending:
            record = self._pending.pop(request_id)
            record.quality_score = quality_score
            record.resolved_at = now
        self._maybe_adjust(now)

    def _expire(self, now: float) -> None:
        cutoff = now - self._window
        while self._requests and self._requests[0].timestamp < cutoff:
            old = self._requests.popleft()
            self._pending.pop(old.request_id, None)

    def _maybe_adjust(self, now: float) -> None:
        if now - self._last_adjustment < self._adjustment_cooldown:
            return
        resolved = [r for r in self._requests if r.quality_score is not None]
        if len(resolved) < 5:
            return
        avg_quality = sum(r.quality_score for r in resolved) / len(resolved)
        if avg_quality > 0.8:
            self._rate_limit = min(self._rate_limit * (1 + self._sensitivity), 1000)
        elif avg_quality < 0.3:
            self._rate_limit = max(self._rate_limit * (1 - self._sensitivity), 1)
        self._last_adjustment = now
        self._adjustments.append({
            "time": now, "new_rate": self._rate_limit,
            "quality": avg_quality, "samples": len(resolved)
        })

    def get_effective_rate(self) -> float:
        return self._rate_limit

    def get_pressure(self) -> float:
        if self._rate_limit == 0:
            return 1.0
        return len(self._requests) / self._rate_limit
```

---

## VI. Three Properties Visible Only Because We Tried to Strengthen It

1. **Dual ownership without a lifecycle contract.** `_requests` (deque) and `_pending` (dict) now jointly track each request, but `_expire()` cleans both via `_requests` expiry, while `record_outcome()` cleans `_pending` via resolution. A request expires from `_pending` through two independent paths with no coordination — neither structure is the authoritative owner of a request's lifecycle.

2. **The cooldown amplifies the instability it appears to suppress.** During the cooldown interval, quality scores accumulate silently in `RequestRecord` fields. When the cooldown lifts, all accumulated evidence triggers a single adjustment — making the system *more* bursty in its adaptation than the original, where every `record_outcome()` call triggered `_maybe_adjust()`. Throttling the learning step doesn't throttle the evidence accumulation.

3. **The enforcer/learner duality is now legible in the data model.** A `RequestRecord` with `quality_score=None` is an enforcement artifact; one with `quality_score` set is a learning artifact. The structural incompatibility that was in the runtime behavior is now written into the type: a single dataclass that is two different things depending on which phase of the object's lifecycle you're observing.

---

## VII. Applying the Diagnostic to the Improvement

**What the improvement conceals:** By adding request ID correlation, the improvement creates the appearance of causal closure. But `_maybe_adjust()` still aggregates *all* resolved scores in the window — the causal link exists at the record level and dissolves at the aggregation level. We added **traceability theater**: the infrastructure of accountability without its substance.

**Property of the original visible because the improvement recreates it:** `_adjustments` **still grows unboundedly**. The original had the same defect but it was invisible among other problems. By fixing `_requests` expiry, adding input validation, and adding a cooldown, the improvement made every other stateful structure well-behaved — which makes `_adjustments`'s unbounded growth conspicuous. The improvement didn't create this property; it *illuminated* it by cleaning up everything adjacent to it.

---

## VIII. The Second Improvement

The recreated property — **audit state and operational state are conflated in the same object** — is addressed by extracting the audit log behind a protocol:

```python
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional, Protocol

@dataclass
class AdjustmentRecord:
    time: float
    new_rate: float
    quality: float
    samples: int

class AuditLog(Protocol):
    def record(self, entry: AdjustmentRecord) -> None: ...

class BoundedAuditLog:
    def __init__(self, maxlen: int = 1000):
        self._records: deque[AdjustmentRecord] = deque(maxlen=maxlen)
    def record(self, entry: AdjustmentRecord) -> None:
        self._records.append(entry)
    def recent(self) -> list[AdjustmentRecord]:
        return list(self._records)

@dataclass
class RequestRecord:
    timestamp: float
    request_id: str
    quality_score: Optional[float] = None

class AdaptiveRateGovernor:
    def __init__(self, initial_rate=10, window=60, sensitivity=0.5,
                 audit_log: Optional[AuditLog] = None):
        self._rate_limit = initial_rate
        self._window = window
        self._sensitivity = sensitivity
        self._requests: deque[RequestRecord] = deque()
        self._pending: dict[str, RequestRecord] = {}
        self._audit = audit_log or BoundedAuditLog()
        self._adjustment_cooldown = 10.0
        self._last_adjustment = 0.0

    def allow(self, request_id: str) -> bool:
        now = time.time()
        self._expire(now)
        if len(self._requests) >= int(self._rate_limit):
            return False
        record = RequestRecord(timestamp=now, request_id=request_id)
        self._requests.append(record)
        self._pending[request_id] = record
        return True

    def record_outcome(self, request_id: str, quality_score: float) -> None:
        if not 0.0 <= quality_score <= 1.0:
            raise ValueError(f"quality_score must be in [0, 1], got {quality_score}")
        now = time.time()
        if request_id in self._pending:
            self._pending.pop(request_id).quality_score = quality_score
        self._maybe_adjust(now)

    def _expire(self, now: float) -> None:
        cutoff = now - self._window
        while self._requests and self._requests[0].timestamp < cutoff:
            self._pending.pop(self._requests.popleft().request_id, None)

    def _maybe_adjust(self, now: float) -> None:
        if now - self._last_adjustment < self._adjustment_cooldown:
            return
        resolved = [r for r in self._requests if r.quality_score is not None]
        if len(resolved) < 5:
            return
        avg_quality = sum(r.quality_score for r in resolved) / len(resolved)
        if avg_quality > 0.8:
            self._rate_limit = min(self._rate_limit * (1 + self._sensitivity), 1000)
        elif avg_quality < 0.3:
            self._rate_limit = max(self._rate_limit * (1 - self._sensitivity), 1)
        self._last_adjustment = now
        self._audit.record(AdjustmentRecord(
            time=now, new_rate=self._rate_limit,
            quality=avg_quality, samples=len(resolved)
        ))

    def get_effective_rate(self) -> float:
        return self._rate_limit

    def get_pressure(self) -> float:
        return len(self._requests) / max(self._rate_limit, 1)
```

**Applying the diagnostic to the second improvement:**

**What it conceals:** Separating the audit log makes `AdaptiveRateGovernor` visually cleaner, which *obscures* that `_rate_limit` is still the single mutable value shared between the enforcer role and the learner role. In a concurrent environment, `_maybe_adjust()` could change `_rate_limit` between two `allow()` calls in the same burst — and neither the cooldown, the audit separation, nor the request tracking fixes this. The structural problem is now aesthetically invisible.

**Property of the original visible because the second improvement recreates it:** We now have *three* data structures tracking each request: `_requests`, `_pending`, and `_audit` (implicitly, via `samples`). Separating concerns has distributed the request lifecycle across more owners, not fewer. The original had this problem with two structures; the improvement added a third while appearing to reduce complexity. The dual-ownership problem is not a bug in any particular structure — it is a symptom of the enforcer and learner sharing operational state.

---

## IX. The Structural Invariant

**The invariant:** In any design where a single object both enforces a policy and learns a new policy, the enforcement predicate (allow/deny) and the learning target are necessarily the same mutable value. Every improvement must either mutate this value less frequently, add indirection around it, or track it more carefully — but cannot separate the roles without dissolving the object's identity.

This invariant persists through every improvement because it is a property of the **design category**, not the implementation:

> **Monolithic Adaptive Controllers**: a class that enforces current policy and updates that policy based on observations. Defined by: enforcement and learning share mutable state and execute in the same object. Bounded by: it is impossible to give independent consistency guarantees to the enforcer and the learner because they are the same object reading and writing the same value.

---

## X. The Adjacent Category: Separated Policy and Enforcement

The invariant dissolves when we recognize:
- The **enforcer** consumes an *immutable* policy snapshot: "given this frozen policy, is this request allowed?"
- The **learner** *produces* a new policy: "given this evidence, what should the next policy be?"

These are different functions over different types. The policy becomes an immutable value that is replaced, not mutated.

```python
import time
from collections import deque
from dataclasses import dataclass, replace
from typing import Sequence

# --- Policy: immutable value object ---
@dataclass(frozen=True)
class RatePolicy:
    rate_limit: float
    window: float
    sensitivity: float
    MIN_RATE: float = 1.0
    MAX_RATE: float = 1000.0

    def with_rate(self, new_rate: float) -> 'RatePolicy':
        return replace(self, rate_limit=max(self.MIN_RATE, min(self.MAX_RATE, new_rate)))

# --- Learning: pure function, no side effects ---
def adapt_policy(policy: RatePolicy, scores: Sequence[float], min_samples: int = 5) -> RatePolicy:
    if len(scores) < min_samples:
        return policy
    avg = sum(scores) / len(scores)
    if avg > 0.8:
        return policy.with_rate(policy.rate_limit * (1 + policy.sensitivity))
    if avg < 0.3:
        return policy.with_rate(policy.rate_limit * (1 - policy.sensitivity))
    return policy

# --- Enforcer: reads immutable policy snapshot, never mutates it ---
class RateEnforcer:
    def __init__(self, policy: RatePolicy):
        self._policy = policy
        self._requests: deque[float] = deque()

    def allow(self) -> bool:
        now = time.time()
        cutoff = now - self._policy.window
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()
        if len(self._requests) >= int(self._policy.rate_limit):
            return False
        self._requests.append(now)
        return True

    def pressure(self) -> float:
        return len(self._requests) / max(self._policy.rate_limit, 1)

    @property
    def policy(self) -> RatePolicy:
        return self._policy

# --- Governor: coordinates enforcer replacement ---
class AdaptiveRateGovernor:
    def __init__(self, policy: RatePolicy, update_interval: float = 10.0):
        self._enforcer = RateEnforcer(policy)
        self._outcomes: deque[tuple[float, float]] = deque()
        self._update_interval = update_interval
        self._last_update = time.time()
        self._policy_history: list[RatePolicy] = [policy]

    def allow(self) -> bool:
        return self._enforcer.allow()

    def record_outcome(self, quality_score: float) -> None:
        if not 0.0 <= quality_score <= 1.0:
            raise ValueError(f"quality_score must be in [0, 1], got {quality_score}")
        now = time.time()
        self._outcomes.append((now, quality_score))
        self._expire(now)
        if now - self._last_update >= self._update_interval:
            self._maybe_replace_enforcer(now)

    def _expire(self, now: float) -> None:
        cutoff = now - self._enforcer.policy.window
        while self._outcomes and self._outcomes[0][0] < cutoff:
            self._outcomes.popleft()

    def _maybe_replace_enforcer(self, now: float) -> None:
        scores = [s for _, s in self._outcomes]
        current = self._enforcer.policy
        updated = adapt_policy(current, scores)
        if updated is not current:
            self._enforcer = RateEnforcer(updated)   # replacement, not mutation
            self._policy_history.append(updated)
        self._last_update = now

    def get_effective_rate(self) -> float:
        return self._enforcer.policy.rate_limit

    def get_pressure(self) -> float:
        return self._enforcer.pressure()
```

---

## XI. How This Succeeds Where Every Improvement Failed

Every monolithic improvement failed for the same reason: it tried to add clarity to a shared mutable value (`_rate_limit`) while preserving the object that shared it. This design eliminates the shared mutable value:

| Property | Monolithic (all improvements) | Separated |
|---|---|---|
| Enforcer consistency | Violated whenever `_maybe_adjust` fires | Guaranteed: enforcer reads frozen `RatePolicy` |
| Learner independence | Impossible: shares state with enforcer | Achieved: `adapt_policy` is a pure function |
| Testability | Requires full object setup | Enforcer and `adapt_policy` are independently unit-testable |
| Policy transition | Silent mutation of `_rate_limit` | Explicit enforcer replacement with logged history |
| Audit log growth | Unbounded (all three implementations) | Naturally bounded: `_policy_history` is a log of immutable snapshots |

The concealment mechanism (Metric Plausibility Masking) no longer works because there is no single metric to mask behind — the enforcer and the learner produce outputs over different types, and their interaction is explicit in `_maybe_replace_enforcer()`.

---

## XII. The New Impossibility

**Enforcement continuity across policy transitions.**

In the monolithic category, `_rate_limit` changes by a small factor while `_requests` persists. The request history from the prior policy continues to count against the new policy's window. The transition is smooth.

In the separated category, when `self._enforcer = RateEnforcer(updated)` executes, the new enforcer starts with an empty `_requests` deque. All requests counted in the old enforcer's window evaporate. If the rate drops from 100 to 2 (a quality collapse), requests already served in the current window are no longer counted — the new enforcer will allow up to 2 *additional* requests before stopping, even if 98 were already served. The window amnesia is structurally guaranteed by enforcer replacement.

---

## XIII. The Finding: The Trade-off

| Category | What it achieves | What it makes impossible |
|---|---|---|
| **Monolithic Adaptive Controller** | Enforcement continuity — request history is preserved across rate changes; the transition is smooth | Semantic independence — you cannot reason about, test, or guarantee the enforcer and learner separately; they are the same object reading and writing the same value |
| **Separated Policy and Enforcement** | Semantic independence — enforcer and learner are distinct, testable, independently consistent | Enforcement continuity — policy transitions create window amnesia; in-flight request state cannot cross the structural boundary |

**The finding:**

The trade-off is between **semantic consistency** (knowing exactly what the system is doing and being able to reason about each part independently) and **behavioral continuity** (enforcement state persisting across policy transitions without discontinuity).

The monolithic implementations achieved continuity by making the enforcer and learner *the same thing* — which is also why they were impossible to reason about. Every improvement tried to add clarity to that merger. The merger was the problem.

The deeper finding: every improvement in the monolithic category was making the illusion of continuity more convincing — more correlation, more metrics, more history. The code's concealment mechanism was not hiding that the system was broken. It was hiding that **adaptive rate control is a governance problem** (what policy should we have?) disguised as an **engineering problem** (how do we control the rate?). These require different answers. Separating them makes the governance decision explicit — and reveals that the cost of making it explicit is losing the fiction that rate adaptation is a smooth, continuous process rather than a sequence of discrete policy replacements.
