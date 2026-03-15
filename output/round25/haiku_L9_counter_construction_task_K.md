# Structural Analysis: Temporal Semantics Collapse

## Initial Claim (Falsifiable)

**The circuit breaker conflates two incompatible temporal models of recovery: it resets failure memory on any single success in CLOSED state, which assumes failures are transient, yet it opens on absolute counts, which assumes failures are deterministic. These models can't both be true, and the code hides this by treating success as a binary event rather than a temporal pattern.**

---

## Three Expert Perspectives & Transformation

**Defender**: "This is actually correct. A single success proves the service recovered. Why hold a grudge if it's working?"

**Attacker**: "That's the problem. A service failing 5 times, succeeding once, then failing 5 times again will cycle forever without the circuit ever *protecting* the system—it just delays failure."

**Probe-asker**: "But you're both assuming 'failure' is the same concept in both of you. Defender treats success as sufficient proof of recovery (Poisson model—random failures, system self-heals). Attacker treats failures as clustered evidence of systemic issues (burst model—if it failed 5 times recently, something's wrong). What if the code is ambiguous about which model it's actually using?"

**TRANSFORMED CLAIM**: The code makes contradictory hidden assumptions about what constitutes system recovery. It simultaneously models:
- Recovery by **success proof** (success-resets-counter, Poisson-like)
- Detection by **absolute counting** (5 failures = broken, regardless of timing)

These are incompatible. The code hides this incompatibility.

---

## Concealment Mechanism

**"Primitive Observability"** — The code only tracks binary success/failure without capturing:
- *Why* it failed (rate-limited? crashed? timeout?)
- *When* failures cluster (5 failures in 10 seconds vs. spread over a week)
- *Whether* a success is stable or lucky

This opacity allows contradictory recovery theories to coexist invisibly.

---

## Deepening "Improvement" #1 (Deceptively Smart)

```python
def _on_success(self):
    if self._state == self.HALF_OPEN:
        self._success_count += 1
        if self._success_count >= self._half_open_max:
            self._state = self.CLOSED
            self._failure_count = 0
    else:
        # NEW: Graduated confidence
        self._success_count = min(self._success_count + 1, self._half_open_max)
        self._failure_count = max(0, self._failure_count - 1)  # Linear decay
```

**Review passes as**: "Smart—success in CLOSED state gradually decays failure memory. More nuanced than binary reset."

### Three Properties Visible Only via This Attempt:

1. **Asymmetrical failure memory**: The reset mechanism was implicit. Now explicit: successes decay failures *linearly*. But this reveals the code never specified *what decay rate is correct*. If 5 failures require 5 successes to recover, the circuit is fragile (one failure re-triggers easily). If we use exponential decay instead, it's too forgiving. The original code hid this question entirely.

2. **HALF_OPEN state now has undefined recovery semantics**: By requiring "success_count ≥ 3," I'm claiming 3 consecutive-ish successes = definitely recovered. But the code doesn't specify: Does order matter? (FAIL, SUCCESS, SUCCESS, SUCCESS ≠ SUCCESS, SUCCESS, SUCCESS, FAIL?) Does timing matter? Recovery velocity is hidden.

3. **Redundant state variables that can diverge**: Now tracking `_success_count`, `_test_count`, `_failure_count`, and implicit `_closed_success_rate`. These overlap. Without atomic updates, they can fall out of sync. The code gains surface area for bugs while pretending to gain sophistication.

---

## Contradictory "Improvement" #2 (Also Legitimate)

```python
def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3, 
             failure_window=300):  # NEW: 5-minute window
    self._failure_times = []
    self._failure_window = failure_window

def _on_failure(self):
    self._failure_times.append(time.time())
    # NEW: Purge old failures—they don't count
    self._failure_times = [t for t in self._failure_times 
                           if time.time() - t < self._failure_window]
    
    if self._state == self.HALF_OPEN:
        self._state = self.OPEN
    elif len(self._failure_times) >= self._failure_threshold:
        self._state = self.OPEN

def _on_success(self):
    if self._state == self.HALF_OPEN:
        self._success_count += 1
        if self._success_count >= self._half_open_max:
            self._state = self.CLOSED
            self._failure_times = []  # Only window-aware, not success-driven
```

**Review passes as**: "Sophisticated—failure concentration within a time window, not just absolute counts. Ignores ancient history."

### Why This Contradicts #1:

| Model | Improvement #1 | Improvement #2 |
|-------|---|---|
| **Recovery mechanism** | Success-driven (active) | Time-driven (passive) |
| **Failure amnesia** | Requires N successes | Requires window timeout |
| **Silent system** | Stays broken forever (no calls = no recovery) | Recovers automatically (window expires) |

**Scenario**: 5 failures at T=0-210s, then nothing:
- **Improvement 1**: Needs 5 successes to reach failure_count=0 (circuit can close in HALF_OPEN)
- **Improvement 2**: After 300 seconds with no new failures, failure_times is empty (circuit can close without any calls)

Both pass code review independently. Both are defensible. **They cannot both be correct.**

---

## Structural Conflict (Hidden Until Both Improvements Are Attempted)

**"Temporal Semantics Commitment Avoidance"**

The code doesn't explicitly model *when failures matter*. It simultaneously implies three different temporal models:

1. **Absolute counting** (original): Failures accumulate eternally until success clears them
2. **Success-based decay** (Improvement 1): Failures fade if you prove recovery through successful calls
3. **Time-windowed concentration** (Improvement 2): Failures fade with time alone; success is irrelevant to CLOSED-state recovery

The code hides this because:
- `_last_failure_time` is tracked but unused (except checking reset timeout)
- Success resets only `_failure_count`, never `_failure_times`
- No time-window exists, making both time-aware and time-oblivious interpretations valid
- The exception handler in `execute()` is the single source of truth, so both "success proves recovery" and "time proves recovery" can coexist as theories

**The conflict only becomes visible when you try to improve the code**, because each improvement clarifies one temporal model by crystallizing it—which simultaneously reveals it contradicts the other models the code was silently assuming.

---

## Bottom Line

The deepest structural problem isn't a bug—it's **ambiguous commitment**. The code presents a unified interface while solving multiple incompletely-specified temporal problems. You can legitimately argue it should recover by:
- Success (active resilience)
- Time (passive degradation)  
- Failure concentration (temporal clustering)

Each is defensible. The code hides that it's not committing to any of them.
