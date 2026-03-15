# Three Experts Analyze EventBus

## Expert 1: The Pragmatist ✓

**"This solves real problems elegantly."**

I see three good design moves:

1. **Priority handlers** are genuinely useful—auth before business logic, cache-warming before processing. Solves a real ordering need without explicit sequencing.

2. **Middleware pattern is proven** (Express, Koa). Cross-cutting concerns (logging, metrics, auth, validation) separate from emit logic. The context threading is clean.

3. **Dead letter queue shows production thinking**—you're not swallowing errors silently or crashing. You capture failure for later inspection/retry.

4. **Simplicity wins**. ~30 lines, readable in 5 minutes. For in-process domain events (cache invalidation, audit logging, notification), this is solid.

**This works if**: Events are fire-and-forget, handlers are trusted, errors are rare, the process is short-lived.

---

## Expert 2: The Skeptic ⚠️

**"This will fail catastrophically at scale."**

I count seven critical flaws:

1. **No async support**: One slow handler blocks everything. A payment event processing waits for a logging handler? The entire emit stack backs up.

2. **Exception handling is incoherent**: Handler A fails → logged to dead letter → Handler B still runs. But Handler B might depend on A's side effects. You've created *silent corruption*.

3. **Unbounded dead letter = memory leak**: Accumulates infinitely in long-running processes. No expiration, draining, or size limits.

4. **No handler cleanup**: Handlers persist forever. Dynamic handlers (per-request listeners) never unsubscribe → handler accumulation → memory leak.

5. **No thread safety**: Race between emit() on thread A and on() on thread B corrupts `_handlers`. Zero synchronization.

6. **Middleware mutation is invisible coupling**: Any middleware can rewrite context. Handlers get mutated data, creating implicit dependencies between middleware and handlers.

7. **No introspection/removal**: Can't test handlers alone, can't toggle them, can't clean up. You're permanently bound to this bus.

**This fails if**: Events are critical paths, handlers are unreliable, the process runs indefinitely, or errors are normal.

---

## Expert 3: The Meta-Analyst 🔍

**"You're both right. But you're arguing about the wrong thing."**

Your disagreement **proves the code's actual problem**: *It makes implicit contracts that aren't visible.*

Watch what's happening:

- **Pragmatist assumes**: In-process, trusted, short-lived, errors exceptional
- **Skeptic assumes**: Long-running, untrusted, errors normal, critical path

Neither assumption is stated. The code doesn't communicate its operating context.

**The deeper invisible problems:**

1. **Failure contract is contradictory**: 
   - Middleware can cancel (returns early)
   - Missing handlers go to dead letter (continues)
   - Handler errors go to dead letter (continues)
   - What does the caller actually know? Nothing.

2. **Two conflicting patterns mixed**:
   - **Notification pattern**: "Something happened; tell interested parties" (async-friendly, stateless)
   - **Transactional pattern**: "This must happen; if it fails, the whole operation fails" (dead letter queue)
   
   You're using both API signatures but haven't chosen which semantics you're implementing.

3. **Ordering is inconsistent**:
   - Middleware runs before handlers ✓
   - Handlers run by priority ✓
   - But what if middleware errors? What if first-priority handler errors? Are subsequent handlers still responsible-shippers or passengers on a corrupted ship? **Undocumented.**

4. **The dead letter queue is a *symptom*, not a solution**:
   - It captures the problem: "This handler failed"
   - But not the answer: "Now what?" Is the operation invalid? Is it retried? Does the caller know?

---

## What the Argument Itself Reveals

The three-way disagreement shows that **this code's real failure isn't implementation—it's communication**.

**The EventBus isn't failing because of bugs; it fails because it makes invisible bets:**

| Assumption | What Code Implies | What's Actually True |
|-----------|-------------------|---------------------|
| Error handling | "Errors are queued, process continues" | "But are downstream handlers valid? Is the transaction poisoned?" |
| Performance | "Handlers run synchronously" | "So one slow handler blocks the entire system" |
| Lifetime | "Dead letter accumulates" | "In 30 days of normal operation: OOM" |
| Cleanup | "Handlers are fire-and-forget" | "No way to unsubscribe; memory leak if handlers are per-request" |
| Scope | "Works for any event type" | "Actually designed for only certain failure modes" |

---

## Core Insight

**Good code doesn't just implement patterns—it communicates its contracts, especially the invisible ones.**

This EventBus needs to answer:

1. **"When does emit() guarantee the handler ran?"** (Never? If no error? If you wait?)
2. **"What does the caller do if dead letter has an event?"** (Retry? Alert? Ignore?)
3. **"Are handlers ordered or independent?"** (You say both, which is neither)
4. **"Is this async-capable or forever-synchronous?"** (Design suggests forever, but needs to say it)
5. **"Who owns cleanup—the caller or the bus?"** (No answer = memory leaks)

The code works perfectly *for one unstated use case* and fails catastrophically *for others*. The problem isn't the implementation—it's that the implementation doesn't announce which case it chose.
