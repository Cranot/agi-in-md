I'll analyze this EventBus using the degradation lens from the portfolio: **What decays over time without touching the code?**

## Concrete Problems (Diagnosis)

**Immediately visible:**
- No handler unsubscribe — only `on()`, no `off()`. Handlers accumulate forever.
- Priority sorting O(n log n) fires on every `on()` call, no deduplication.
- Middleware exceptions crash the pipeline; handler exceptions silently lose results on mixed success/failure.

**Silent failures (corruption without crashes):**
- Dead letter queue is unbounded append-only. Grows forever, no consumption mechanism.
- When a handler throws, `context["results"]` is overwritten with `context["error"]`, destroying successful results from earlier handlers.
- Handler identity is lost — results array has no correlation to which handler produced what.
- No instrumentation on handler execution — can't measure latency, concurrency, or failure rates per handler.

---

## Decay Timeline: What Breaks When

### **Month 6 of neglect**
| Component | State | Problem | Visibility |
|-----------|-------|---------|------------|
| Dead letter queue | 50K-500K entries | Slightly slows inspection queries | Visible (slow) |
| Handler list (hot events) | 10-100 duplicates | Tests/reloads register same handler repeatedly | Silent (duplicate invocations) |
| Memory | +5-50MB | Unnoticed in most systems | Invisible |
| Error reporting | No change | Dead letter contains failures but nobody reads it | Silent (data exists, no alerting) |

**Silent corruption mode:** Test suite registers handlers 50x. Same event fires 50 times per invocation. Tests pass (they expect idempotence). Production fires 5x instead of 1x, causing duplicate charges, duplicate messages, duplicate state mutations.

---

### **Month 12 of neglect**
| Component | State | Problem | Visibility |
|-----------|-------|---------|------------|
| Dead letter queue | 1M-5M entries | Query-time balloons; raw list scan takes seconds | Visible (slow, then timeout) |
| Handler list | 100s of duplicates | Hot event paths invoke 500+ handlers for what should be 5 | Visible (CPU spike) |
| Memory | +50-500MB | GC pauses start appearing in metrics | Visible (latency spikes) |
| Observability | Dead letter unreadable | Which handler failed? Why? When? No answers. | Silent (data unintelligible) |

**Silent corruption mode:** Middleware #3 caches a decision. Middleware order shifted during refactor. Now it makes stale decisions. Handlers execute in wrong logical order. State gets mutated incorrectly. No crash — just wrong data in database, gradually discovered over weeks.

---

### **Month 24 of neglect**
| Component | State | Problem | Visibility |
|-----------|-------|---------|------------|
| Dead letter queue | 10M-100M entries | OOM crashes OR forced aggressive truncation losing evidence | **Visible (crash or silent data loss)** |
| Handler list | 1000s of duplicates | emit() takes 10-100ms per invocation (should be <1ms) | Visible (timeout errors, cascading failure) |
| Memory | +500MB-5GB | System becomes GC-bound; every operation pauses | Visible (severe latency) |
| Error context | Completely opaque | "Error happened. Which handler? When? What state? Unknown." Need manual forensics. | **Visible (but un-debuggable)** |

**Silent corruption mode:** Dead letter queue was silently truncated to limit memory. Old failure data lost. New errors pile up, unread. A handler that was registered then "forgotten" (never unsubscribed) causes 1000s of duplicate state mutations. Nobody notices because errors aren't visible anymore — they're just missing.

---

## Degradation Law

**Information Density Decay:**

```
Δ(signal / noise) = -(failures/day × time_neglected) / (tools_to_query_dead_letter)
```

**The property that worsens monotonically:**
- **Ratio of accumulated events to meaningful analysis tools** = dead_letter_size / 0 (no tooling)
- After 6 mo: 100K events, can scan manually
- After 12 mo: 1M events, scan times out
- After 24 mo: 100M events, completely opaque (binary search fails, can't even enumerate)

**Alternatively: Observability Cliff**
- Mean time to answer "which handler failed?" = O(dead_letter_size / query_capability)
- 6 months: 10 seconds
- 12 months: 10 minutes
- 24 months: ∞ (no answer possible)

---

## Where Brittleness Increases

1. **Handler list bloat** — Each `emit()` invokes 1000x handlers instead of 5. Brittleness = handler_count * middleware_count. Failure scenarios compound combinatorially.

2. **Dead letter queue becomes a liability** — Originally meant to capture failures for debugging. After 12 months, it's consuming more memory than the handlers themselves. Any new feature that adds logging will trigger OOM.

3. **Memory pressure → GC hell** — System gets paused by garbage collection for seconds per minute. Every operation becomes unpredictable. Monitoring fails (alerts timeout).

4. **Silent error swallowing** — Exception stored in context["error"] but never read. After 24 months, production is failing silently, failures aren't propagating, and alerting is dead.

---

## Tests That Predictably Break By Only Waiting

```python
# Test 1: Dead letter OOM
def test_dead_letter_exhaustion():
    bus = EventBus()
    # Simulate 24 months of failed events
    for i in range(100_000):
        bus.emit("order.process", {"id": i})
    
    # After 6 months in prod (10x scale), memory usage?
    import sys
    initial = sys.getsizeof(bus._dead_letter)
    assert initial < 100_000_000, "Dead letter exceeded 100MB — add truncation"

# Test 2: Handler duplication slowdown
def test_handler_duplicate_latency():
    bus = EventBus()
    def handler(ctx): pass
    
    # Register same handler 100x (simulates 1 year of test reloads)
    for _ in range(100):
        bus.on("order.ready", handler)
    
    import time
    start = time.time()
    for _ in range(1000):
        bus.emit("order.ready", {})
    elapsed = time.time() - start
    
    # After 24 months, this would be 1000x slower
    assert elapsed < 0.1, f"emit() took {elapsed}s with 100 duplicate handlers"

# Test 3: Result loss on mixed success/failure
def test_result_preservation_on_handler_failure():
    bus = EventBus()
    results = []
    
    bus.on("order.ready", lambda ctx: results.append("handler1_success"))
    bus.on("order.ready", lambda ctx: 1/0)  # Fails
    bus.on("order.ready", lambda ctx: results.append("handler3_success"))
    
    ctx = bus.emit("order.ready", {})
    
    # After 24 months, users report: "why did handler1 run but I didn't see results?"
    assert "handler1_success" in results, "Results lost when middle handler fails"
    assert "handler3_success" in results, "Handlers after failure never run"

# Test 4: Dead letter unreadability
def test_dead_letter_query_latency():
    bus = EventBus()
    bus.on("order.process", lambda ctx: 1/0)  # Always fails
    
    # Simulate 12 months: 1M failed events
    for i in range(1_000_000):
        bus.emit("order.process", {"id": i})
    
    import time
    start = time.time()
    failed_by_handler = [e for e in bus._dead_letter if "order.process" in str(e)]
    elapsed = time.time() - start
    
    # After 24 months, this query is O(n) on 100M entries
    assert elapsed < 1.0, f"Querying dead_letter took {elapsed}s — add indexing"
```

---

## The Three-Level Corruption Cascade

**Layer 1 (visible):** Dead letter grows. Memory pressure. GC pauses visible in latency.

**Layer 2 (semi-silent):** Handler duplicates cause N×duplicated side effects. "Why did we charge the customer 5 times?" Discoverable with audit trail, but takes forensics.

**Layer 3 (fully silent):** Middleware order dependency corruption. State mutations happen in wrong order. Data is silently wrong. Discovered weeks later through business metrics degradation, not through error logs.

---

## Recommendation: Tend the Decay

Add to every system:
1. **Handler registry** with `off(event_type, handler_id)` and identity tracking
2. **Dead letter quota** with retention policy (FIFO eviction at 100K entries)
3. **Handler invocation instrumentation** (per-handler latency, error rate)
4. **Middleware dependency verification** (fail fast if order changes unexpectedly)
5. **Result preservation** on partial failure (all successful results preserved even if some handlers fail)

Without these, the EventBus becomes unmaintainable by month 12.
