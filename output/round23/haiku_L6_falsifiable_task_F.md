# Falsifiable Hypothesis

**"The EventBus's deepest structural problem is that it conflates three incompatible models—message queue, middleware pipeline, and transaction system—without committing fully to any. Specifically: handlers execute as an unsynchronized sequence with error accumulation, which makes it impossible to express failure atomicity, handler ordering dependencies, or consistent state guarantees. Any real application will either abandon this bus for a real queue, or add external orchestration that recreates the logic this bus should own."**

This is falsifiable because: an expert could demonstrate a production use case where independent error-accumulating handlers are the correct model, or show that my assumption about "what should be owned" is wrong for the problem domain.

---

## Three Expert Perspectives

### **DEFENDER (Reliability Engineer)**
> "The hypothesis identifies a critical gap: you cannot reason about postconditions. After `emit()` returns, what's true? With partial handler execution on exceptions:
> 
> - If handler A succeeds, handler B fails, handler C succeeds: what state is the system in? 
> - The dead letter entry tells you *something broke*, but not whether to retry, skip, or abort downstream processing
> - A handler registering with priority=100 expecting to run before priority=0 handlers has no way to implement a pre-condition check that would cancel the event
>
> The hypothesis is *too narrow* though. The real problem is: **this design gives up on handler-level failure semantics entirely.** It should either:
> 1. Stop-on-first-error (like Promises)
> 2. Collect results with explicit success/failure status per handler
> 3. Support handler assertions/contracts
>
> Any handler that depends on another handler's side effects is already broken code."

---

### **ATTACKER (Event Sourcing Architect)**
> "You're confusing *distribution* with *coordination*. An EventBus shouldn't guarantee transaction semantics—that's not its job. Kafka doesn't. Redis doesn't. 
>
> The real issue here is **observability deficit**, not atomicity deficit:
> - No handler execution trace (what ran, in what order, with what results)
> - Dead letter conflates 'no handlers' with 'handler failure' 
> - No way to correlate a result back to the handler that produced it
> - No middleware introspection (can you see what each middleware modified?)
>
> If you build an audit trail, the partial execution becomes *a feature*: you can replay, debug, recover per-handler. The hypothesis assumes you *should* fail atomically, but that's only true if your handlers are tightly coupled. This bus is designed for *loose coupling*—and in that model, atomic failure is wrong.
>
> The structure isn't broken. It's just incomplete."

---

### **PROBER (Philosopher of Code)**
> "Both of you are assuming different things about what 'correct' means. Let me name the unstated assumptions:
>
> **Defender assumes:** Handlers have *semantic dependencies*—if one fails, others shouldn't run. This assumes handlers are part of a *single logical transaction*.
>
> **Attacker assumes:** Handlers are *independent services*—failure in one is data, not a stop condition. This assumes handlers are part of an *asynchronous gossip system*.
>
> The code doesn't declare which model it is. So:
> - If you're in the defender's world: why does the bus *allow* exceptions to not stop the chain?
> - If you're in the attacker's world: why does the bus *suggest* that handlers run synchronously, all in one call stack?
>
> **The unfalsifiable claim hiding here:** 'This bus knows its own use case.' It doesn't. It's a hybrid that assumes you'll figure it out. That's the structural problem—not transaction semantics, not observability. It's **model ambiguity**. 
>
> The falsifiable version: Can you find a code path where the handler's result in `context['results']` is actually *used by the caller*? Or is the dead letter queue the only real output?"

---

## What Changed

**Did the hypothesis survive?** It *transformed*, not falsified:

| What I Claimed | What Stands | What Was Wrong |
|---|---|---|
| "Transaction semantics" | ✓ Real gap, but only if handlers are dependent | ✗ Assumed dependency model without evidence |
| "Error accumulation is broken" | ✓ True—but *which* model breaks on it? | ✗ Didn't distinguish use cases |
| "Deepest problem" | ? Moved from "atomicity" to "model clarity" | **Defender and Attacker could both be right in different domains** |

**What I know now that I couldn't before:**

1. **The bug isn't the code—it's the contract.** The EventBus doesn't declare: "I handle independent handlers" or "I enforce sequential consistency." It does both halfway.

2. **The real red flag:** `context["results"]` is never consumed. The return value is dead code. If you're calling `emit()`, you either:
   - Ignore the result (why return it?)
   - Check dead letter (why not just raise on first error?)

3. **The unfixable design choice:** Should `emit()` block on all handlers or enqueue them? The code assumes synchronous, single-threaded execution—but never *says* so. Add two handlers that call HTTP APIs, and you've bottlenecked your entire system, with no way to parallelize.

---

## Refined Hypothesis

**"The EventBus's deepest structural problem is not architectural—it's semantic. The handler execution contract is ambiguous: it's unclear whether handlers form a coordinated transaction (fail atomically) or independent subscribers (fail gracefully). This ambiguity forces every caller to invent external coordination. The code should either rename itself to make its model explicit (`TransactionalEventBus` vs. `PubSubBus`), or add a handler contract mechanism that lets handlers declare: 'I depend on X' or 'I can tolerate others failing.'"**

This *is* falsifiable: show me production code using this EventBus successfully where ambiguity didn't cause bugs.
