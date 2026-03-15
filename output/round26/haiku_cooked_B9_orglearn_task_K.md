# Production Failure Analysis: Circuit Breaker + Retry Coupling

## Structural Problems (Real Bugs)

1. **_failure_count never resets entering HALF_OPEN**
   - CLOSED→OPEN: _failure_count = 5
   - OPEN→HALF_OPEN: _failure_count still 5
   - First test failure: _failure_count = 6 → immediately OPEN again
   - Result: Stuck loop. Every recovery test fails instantly.

2. **Retry delays (7+ seconds) exceed reset_timeout (30 seconds) logic**
   - Each test in HALF_OPEN: 3 retries × exponential backoff = 1 + 2 + 4 sec ≈ 7 sec
   - Service recovers at T=20s, but test at T=37s doesn't succeed until T=44s
   - Service may have failed *again* by then
   - Retry mechanism masks what the circuit breaker is actually testing

3. **Retry and circuit breaking are incommensurable concerns**
   - Retry asks: "Is this request retryable?" (local, tactical)
   - Circuit breaker asks: "Is the service failing?" (global, strategic)
   - Code mixes them: every request retries 3 times before CB sees a signal
   - Result: CB is testing the retry policy, not the service health

## Production Failure Scenario

Service goes down at T=0, recovers at T=25s:
- T=0-7: Request attempts 3 retries, all fail → _failure_count = 5, state = OPEN
- T=7-37: Circuit rejects all requests immediately (good)
- T=37: Transition to HALF_OPEN, but _failure_count = 5 unchanged
- T=37-44: Test request retries 3 times, all fail, _failure_count = 6 → state = OPEN
- T=44-74: Circuit trapped. Service is healthy, but CB keeps reopening.
- T=74+: Endless cycle

---

## What the Organization Learns

**"Our circuit breaker can't detect recovery because the retry mechanism masks the service's actual state."**

They discover that retry-as-default-in-CB creates a two-tier timing problem:
- Local tier (retries): seconds
- Global tier (recovery test): tens of seconds  
- These are incompatible. Testing recovery requires 7-second delay per test.

---

## Adjacent System They'll Redesign (Not Fix the Code)

Instead of fixing the circuit breaker (trivial: reset counters), they'll **redesign the load balancer's health check and request shedding layer**.

**The redesign:**
- Move health checks *out of band* — separate from request execution, independent from the retry path
- Implement explicit readiness probes (fast, sub-second) that run continuously
- Replace the circuit breaker's HALF_OPEN recovery test with infrastructure-level health checks
- Make the load balancer the source of truth for "is this service accepting traffic"

**Why this instead of fixing CB:**
- Fixing CB requires changing the library (risk, testing)
- Redesigning the load balancer/service mesh affords better observability anyway
- The health-check pattern decouples recovery detection from request latency
- Once decoupled, you don't need HALF_OPEN state at all — you test health independently

**The system they permanently own:**
- **Service mesh / API gateway's health probe + request routing layer**
- Independent connection pooling with fast fail (not retry)
- Load balancer makes routing decisions, not the application

The circuit breaker lives on as a safety redundancy, but it's no longer the recovery mechanism. The adjacent system becomes the real controller.
