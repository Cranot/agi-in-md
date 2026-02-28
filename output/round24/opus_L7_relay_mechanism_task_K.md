# Idiomatic Fragment Camouflage Analysis

## Step 1: The Individually Correct Fragments

This code assembles three well-known idioms. Each one looks textbook-correct in isolation:

---

**Fragment A — Circuit Breaker State Machine**
The CLOSED → OPEN → HALF_OPEN cycle, failure threshold, reset timeout, success-count promotion. Matches the Nygard *Release It!* pattern. A reviewer checks it against that pattern and nods.

**Fragment B — Retry with Exponential Backoff + Jitter**
`base_delay * (2 ** attempt) + random.uniform(0, 1)` — canonical implementation. A reviewer recognizes AWS architecture blog best practice and nods.

**Fragment C — Success/Failure Callbacks**
`_on_success` promotes HALF_OPEN → CLOSED after sufficient successes; `_on_failure` trips CLOSED → OPEN after threshold. Standard event-driven state transition. A reviewer nods.

Every fragment, audited against its source idiom, passes.

---

## Step 2: How Combination Creates Invisible Incoherence

### Contradiction 1: Retry *inside* Circuit Breaker inverts both contracts

The **circuit breaker's contract**: *fail fast* when a service is unhealthy.
The **retry's contract**: *persist* through transient failures.

These are **philosophically opposed** when composed this way. The retry loop is *nested inside* the circuit breaker's execution path, meaning:

```
execute()          →  counts 1 failure (or 1 success)
  └─ _retry_with_backoff()  →  silently makes up to 3 actual calls
```

The circuit breaker **cannot observe individual failures**. It only sees "retry-exhaustion events." The advertised `failure_threshold=5` is actually a threshold of **15 real failed requests** (5 × 3 retries). Neither fragment's review reveals this — the circuit breaker looks right, the retry looks right.

### Contradiction 2: HALF_OPEN becomes the opposite of itself

HALF_OPEN exists to send **minimal, cautious probe traffic** to a recovering service. But each "probe" passes through `_retry_with_backoff`, meaning:

- Each probe sends **up to 3 requests** with sleep delays
- `_half_open_max=3` requires 3 successful probes → up to **9 actual requests**
- With backoff sleeps, a "cautious probe" sequence takes **~21 seconds of hammering**

The gentle probe is actually an aggressive assault. This is invisible because the HALF_OPEN logic looks correct and the retry logic looks correct — the problem exists only in their intersection.

### Contradiction 3: The accidental correctness time bomb

In `_on_failure`, a HALF_OPEN failure should immediately re-trip to OPEN. There's no special HALF_OPEN case in `_on_failure` — yet it *does* re-trip immediately. Why? Because `_failure_count` is never reset on the OPEN → HALF_OPEN transition, so it's still ≥ `_failure_threshold` from when the circuit originally opened.

This is **correct by accident**. The moment someone "cleans up" the code by resetting `_failure_count` when entering HALF_OPEN (which looks like an obvious improvement), the circuit breaker breaks — it would need 5 *more* failures in HALF_OPEN to re-trip, defeating the entire purpose.

---

## Step 3: What the Whole Actually Does vs. What Fragments Claim

| Fragment Claims | Assembled Reality |
|---|---|
| "Fails fast after 5 failures" | Fails slow after 15 real failures, spread across ~50s of retry sleeps |
| "Cautiously probes with HALF_OPEN" | Aggressively retries during probe, potentially overwhelming recovering service |
| "Exponential backoff protects the server" | Backoff runs *inside* the circuit breaker, delaying the state machine's ability to react to cascading failure |
| "Clean state transitions" | HALF_OPEN→OPEN works only by accident of unreset state |

---

## Step 4: The Problem ONLY Visible Through This Mechanism

### Silent Parameter Theft via Kwargs Forwarding

Trace the parameter flow across fragments:

```python
# User calls:
cb.execute(my_api_call, endpoint, max_retries=10)

# execute signature:
def execute(self, fn, *args, **kwargs):        # kwargs = {"max_retries": 10}
    result = self._retry_with_backoff(fn, *args, **kwargs)

# _retry_with_backoff signature:
def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
    #                                    ^^^^^^^^^^^^ CAPTURES IT
```

The user's `max_retries=10` — intended for `my_api_call` — is **silently intercepted** by `_retry_with_backoff`. It never reaches `fn`. No error is raised. The function quietly retries 10 times instead of 3, and `my_api_call` never receives its parameter.

Similarly, `base_delay=X` is stolen. Any function expecting these common keyword names will silently malfunction.

**Why standard review misses this:** The `execute` signature (`fn, *args, **kwargs`) is the standard callable-wrapper idiom. The `_retry_with_backoff` signature (`fn, *args, max_retries=3, **kwargs`) is the standard configurable-retry idiom. Each is locally correct. The parameter theft only exists in the *forwarding boundary between two correct idioms* — a place no fragment-level review examines.

---

## Summary

The concealment works because every reviewer has a mental **pattern-match shortcut**: *"I recognize this idiom; it's fine."* The circuit breaker fragment matches the circuit breaker pattern. The retry fragment matches the retry pattern. The callbacks match the state-machine pattern. But the **assembled whole** is a system that retries aggressively when it should fail fast, hammers recovering services when it should probe gently, maintains correct state transitions by accident, and silently steals user parameters — none of which is visible from inside any single fragment.
