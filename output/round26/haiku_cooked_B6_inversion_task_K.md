# Circuit Breaker: Control Boundary Inversion & Paradox

## 1. CONTROL BOUNDARY (Standard Version)

**What external thing controls THIS code?**

The **service function `fn`** controls CB state. CB is purely *reactive*:
- `fn` fails → CB counts
- N failures → CB opens
- CB's decisions are *consequences* of what `fn` does

**Data flow:** `fn behavior → CB state → CB action`

The boundary: **CB observes, service acts. CB reacts.**

---

## 2. INVERTED VERSION

Now flip: **THIS CODE (CB) controls the service.**

```python
class InvertedCircuitBreaker:
    def command_service(self, service):
        """CB issues imperatives, service obeys"""
        if self._state == self.CLOSED:
            service.accept_all_requests()
        elif self._state == self.OPEN:
            service.reject_all_requests()  
        elif self._state == self.HALF_OPEN:
            service.accept_limited(max_concurrent=self._half_open_max)
    
    # CB decides recovery time, service executes it
    def attempt_recovery(self):
        self._state = self.HALF_OPEN
        self.command_service(service)  # Commands come first
        # Service must obey, then report back (maybe)
```

**Data flow:** `CB state → service command → service behavior`

The boundary: **CB decides, service executes. Service is subordinate.**

---

## 3. CONTRACTS THAT BECOME IMPOSSIBLE IN INVERTED

| Contract | Standard | Inverted | Status |
|----------|----------|----------|--------|
| **Timeout-based recovery** | timeout + check → try HALF_OPEN | CB issues HALF_OPEN at timeout... but based on what observation? | ❌ IMPOSSIBLE |
| **Observation-driven state change** | see 5 failures → open | CB has no way to observe current failures after command issued | ❌ IMPOSSIBLE |
| **Gradual recovery test** | 3 consecutive successes in HALF_OPEN | Service has no feedback loop to know when it's "recovered enough." CB guesses. | ❌ IMPOSSIBLE |
| **Error-type discrimination** | failure from fn tells you what failed | CB's command doesn't tell service *why* it's degraded | ❌ IMPOSSIBLE |
| **Passive gating** | "block calls if open" | "force service to degrade" — service must be rewritten to accept commands | ⚠️ ARCHITECTURAL SHIFT |

**Core impossibility:** The entity that *controls* cannot *observe* what it controls without creating a feedback loop. The entity that *observes* cannot *decide* without reacting too slowly.

---

## 4. SILENT FAILURES → VISIBLE FAILURES

**Standard (current) - hidden:**
- Line 29: `self._retry_with_backoff()` — internal retries absorb 3 failures. CB sees only final result.
  - Service fails 2x, succeeds on retry 3 → CB records **1 success**, never sees the 2 failures.
  - Consequence: failure threshold becomes unreliable (never actually 5 "real" failures, 5 *first attempts*).

- Line 42: `if self._state == self.HALF_OPEN: self._success_count += 1` — only counts successes in HALF_OPEN.
  - Between CLOSED and OPEN, successes reset failure count (line 43: `self._failure_count = 0`).
  - Recovery from transient error = back to blank slate. Repeated transient errors look like separate incidents, not pattern.

**Inverted - becomes visible:**
- CB must command `service.reject_all_requests()` at line 9 (OPEN state).
- Service now sees: "I am closed. I reject requests."
- But *service had no input* — CB decided on stale data (timeout value, not actual recovery).
- Service is now degraded *by fiat*, not because it failed.
- If service **needed to reject anyway** (was already saturated), the command is redundant.
- If service **recovered unobserved**, the command makes it lie about its state.

**New visible failure:**
```python
# Inverted version: CB issues HALF_OPEN, service accepts 3 requests
# Service is actually ready for 1000 requests, but CB limited it to 3.
# The 3 succeed. CB sees success. CB issues CLOSED.
# All pending requests (1000) now rush in. Service crashes.
# But this looks identical to: "3 test requests succeeded, service is fine."
```

CB cannot distinguish:
- "Service recovered and handled 3 requests easily"
- "Service is still degraded but 3 requests happened to work"

---

## 5. THE PARADOX

**Standard:** Outside controls *reality*, inside controls *access*.
- Service is what fails (ground truth)
- CB controls whether you see it (policy)

**Inverted:** Inside controls *reality*, outside controls *compliance*.
- CB is what decides state (policy)
- Service must enact it (compliance)

**What must be true in BOTH?**

> **Exactly one entity holds decision authority for each decision point.**

- Standard: `fn` decides it failed. CB decides to open. (Two entities, two decisions, no conflict.)
- Inverted: CB decides service is open. Service decides to obey. (Two entities, one decision, conflict possible.)

The paradox: **Authority cannot be shared, but observation must flow backward or the system is blind.**

If CB controls service state, CB needs service's state to decide. But if service reports state to CB, service is now *partially deciding* (what to report?). 

**Unstated assumption in both versions:**
- Standard: "fn is honest. Its failures are real."
- Inverted: "CB is wise. Its commands are right."

Both assume the *observer* (or in inverted, the *commander*) has sufficient information. Neither does.

---

## 6. THE CONSERVATION LAW

**Name: The Authority-Information Asymmetry**

> **Information cost of state correctness is conserved. You pay it either as decision latency (standard) or decision error (inverted). You cannot reduce both.**

**Standard version cost structure:**
- Pay in *time*: failures must accumulate to 5 before action
- Pay in *blindness*: CB doesn't know if service is recovering until timeout + test requests
- Pay in *amnesia*: transient errors reset counters

**Inverted version cost structure:**
- Pay in *guessing*: decide recovery timing without observation
- Pay in *brittleness*: command is binary (OPEN/CLOSED), reality is analog
- Pay in *compliance*: service must be rewritten to accept commands, creating coupling

**What's conserved:** The total information-debt. You cannot have:
- ✅ Fast decisions (short detection time)
- ✅ Accurate decisions (know state when deciding)  
- ✅ Decoupled components (service doesn't need to know CB exists)

**All three together are impossible.** Standard sacrifices (1). Inverted sacrifices (2) and (3). Both pay the same total cost, in different currencies.

---

## 7. BIDIRECTIONAL DEADLOCK (Inverted Applied Both Ways)

**Scenario: CB controls service AND service reports state back to CB.**

```python
# Both-ways system
class BidirectionalCircuitBreaker:
    def execute_and_control(self, service_obj):
        # CB issues command
        self.command_service(service_obj)  # OPEN, HALF_OPEN, CLOSED
        
        # Service reports back its state
        actual_state = service_obj.get_current_load()  
        
        # CB reads service state and adjusts
        if actual_state == "recovering":
            self._state = self.HALF_OPEN
        elif actual_state == "saturated":
            self._state = self.OPEN
```

**The deadlock emerges here:**

```
T=0:  CB sees 5 failures → issues OPEN command
T=1:  Service receives OPEN → rejects requests → load drops
T=2:  Service reports load = "low" 
T=3:  CB sees low load → interprets as "recovered" → issues CLOSED
T=4:  Service receives CLOSED → accepts all → backlog rushes in
T=5:  Service receives sudden spike → load = "saturated"
T=6:  CB sees saturated → issues OPEN
T=7:  Service rejects, load → "low"
T=8:  CB interprets "low" as recovery signal → issues HALF_OPEN
T=9:  Service in HALF_OPEN state but doesn't know CB expects it to be testing
      Service reports normal operation during HALF_OPEN
T=10: CB sees normal traffic during HALF_OPEN, thinks recovery succeeded → CLOSED
(loop restarts, oscillates forever)
```

**Why testing cannot detect this without breaking both invariants:**

Invariant A (Standard): *CB must not know when service's state changes internally.*
Invariant B (Inverted): *Service must not know why CB issued a command.*

**Testing to break the oscillation requires:**
- Scenario 1: Mock service to always report "recovered" → breaks Invariant B (service now has privileged knowledge)
- Scenario 2: Slow down CB's decision loop → breaks Invariant A (CB is now reacting too slowly to real failures)
- Scenario 3: Add a human observer to decide OPEN/CLOSED → breaks both (introduces third authority)

**No test harness can run this end-to-end** without one side having to "cheat" by either:
- Reporting false state (service lies about load)
- Issuing false commands (CB ignores its own logic)
- Trusting the other (which is what failed)

---

## 8. THE DESIGN PRINCIPLE CONSERVED IN BOTH VERSIONS

**Single Writer Principle for each decision loop:**

| Version | Who writes state? | Who reads state? | Who decides? |
|---------|-------------------|------------------|--------------|
| **Standard** | fn (via failure) | CB (via observe) | CB (via threshold) |
| **Inverted** | CB (via command) | service (via obey) | CB (via timeout) |
| **Bidirectional** | BOTH → DEADLOCK | BOTH ← DEADLOCK | DEADLOCK |

**The conserved law:**

> **Per decision loop, exactly one component decides; others observe or obey. If two components both decide the same state, they must use the same information source. If they use different sources, information asymmetry emerges.**

In bidirectional: 
- CB decides based on: timeout + recent failure history
- Service decides based on: current load + request queue
- **Different information → conflicting commands → oscillation**

**Why no testing protocol breaks this without breaking both invariants:**

Tests that *validate* the system require *observation*. But observation requires that one side is telling the truth. In bidirectional, both sides are lying (acting on stale data). The test can see the oscillation, but it cannot know *which command is wrong* without suspending both Invariant A and B simultaneously.

---

## Practical Implication for Your Code

**Current problem (standard version):**
```python
# Retries hide failures from CB state machine
for attempt in range(max_retries):
    try:
        return fn(*args, **kwargs)  # Line 30
    except Exception as e:
        if attempt == max_retries - 1:
            raise
        # Silently retry (CB never sees attempts 1-2)
```

**Symptom:** A service that fails 4/5 times but succeeds on retry-3 will never open the circuit, even if this pattern repeats constantly.

**Why it's hard to fix:**
- Remove retries → CB reacts faster, but transient errors now open circuit
- Keep retries inside → CB stays blind, or...
- Move retries outside → CB now counts retries as separate calls, asymmetric again

**The conservation law says:** You're paying for the latency of accurate detection. Retries buy you transient-error tolerance at the cost of failure blindness.

If you go inverted (CB commands service to degrade gracefully), you need service to accept `max_concurrent=3` and know what that means. Service is now coupled to CB's recovery strategy. If you change HALF_OPEN from 3 to 5, service code changes.
