# Structural Analysis via Falsifiable Debate

## Initial Falsifiable Claim

**"The EventBus's deepest structural problem is that when a handler fails, the context is immediately committed to dead_letter (marking the event as failed), yet execution continues and results accumulate, creating an incoherent state where the same event is simultaneously marked as failed and partially processed—violating the basic invariant that each event has a single, deterministic outcome."**

This is falsifiable because experts could show this either doesn't matter in practice, enables valuable patterns, or isn't actually the deepest problem.

---

## Three-Expert Debate

### Expert 1: DEFENDER (Pragmatist)
*Argues the implementation is sound for real systems*

"This 'incoherence' is actually resilience. In distributed systems, you want cascading cleanup: if handler A fails, handlers B and C should still run to perform compensating actions, log, retry, or notify. 

The dead_letter entry doesn't mean 'abandon completely'—it means 'this had issues.' Context["error"] is visible to subsequent handlers, which is exactly right. Each handler should be independent enough to handle failures upstream.

Your 'single outcome' assumption is transactional thinking. Events aren't transactions. An event might be 30% processed by handler A, 80% by handler B, and crash at C. That's fine. Users need the partial results AND the error tracking."

**Verdict on claim:** *Misframes the problem as a bug when it might be intentional design.*

---

### Expert 2: ATTACKER (Rigorous Engineer)  
*Exposes the coherence problem and identifies a real isolation failure*

"The Defender misses what's actually happening. Look closely:

```python
except Exception as e:
    context["error"] = e
    self._dead_letter.append(context)  # ← committed to DLQ HERE
    # ...execution continues

context["results"] = results  # ← still accumulating AFTER DLQ commit
return context  # ← returns context with BOTH error AND results
```

The context object is **simultaneously persisted as failed and returned as in-progress**. A caller gets both context["error"] and context["results"]. That's incoherent.

More critically: the shared mutable context **prevents handler isolation**. If Handler 1 fails and sets context["error"] = SomeException, Handler 2 runs seeing that error. You cannot parallelize these handlers. The Defender's 'independent handlers' are actually tightly coupled through context mutation.

The problem isn't just incoherence—it's that **the architecture is incompatible with actual handler resilience patterns**."

**Verdict on claim:** *Strengthens it substantially. The claim underestimated the severity.*

---

### Expert 3: PROBER (Architectural Questioner)
*Challenges both the framing and unstated assumptions*

"Both of you are arguing about the symptom. Let me probe the assumptions:

**Q1:** What does 'dead_letter' actually mean here? 
- Is it 'event failed, stop'? 
- Or 'something notable happened, log it'?
- *The code doesn't specify.*

**Q2:** Who decides if a failure is fatal?
- The framework (by moving to DLQ immediately)? 
- The handler (by what it throws)?
- The caller (by how they interpret results)?
- *Right now: all three, implicitly.*

**Q3:** Is the problem the incoherent state, or the **lack of error semantics specification**?
- You could fix this by specifying: 'on handler exception, stop immediately and mark event failed, don't run remaining handlers'
- You could also specify: 'on handler exception, isolate failure to that handler, continue others, return both failed and succeeded results'
- Either way, the *specification is missing*.

**Q4:** What's the actual invariant you need?
- Transactional: all-or-nothing ← this code violates that
- Eventual consistency: handlers eventually process, failures are logged ← this code supports that
- Choreography: handlers coordinate via context ← this code enables that but makes it fragile

**The root issue isn't incoherence—it's underspecified error handling enabled by mutable shared context.**"

**Verdict on claim:** *Transforms it. The incoherence is a symptom of deeper architectural underspecification.*

---

## What Changed Through the Debate

| | Before | After Debate |
|---|---|---|
| **Problem identified** | Incoherent event state | Underspecified error semantics + mutable context coupling |
| **Severity** | Architectural concern | Fundamental: blocks any coherent error strategy |
| **Root cause** | Continuing after DLQ commit | Shared mutable context makes error semantics impossible to specify clearly |
| **Solution space** | Fix the DLQ logic | Redesign error flow + isolate handler contexts |

## Refined Claim (Transformed)

**"The EventBus's deepest structural problem isn't the incoherent state symptom, but that it provides **no way to specify error semantics**: the framework immediately persists failures to dead_letter while continuing execution, yet there's no abstraction layer to enforce whether errors are fatal, isolated, or recoverable. The shared mutable context through handlers makes it impossible to implement any consistent error strategy."**

### This is more falsifiable because:
- You could show that adding explicit error policies fixes the problem
- You could show that handler isolation removes the coupling problem  
- You could test whether mutable context is actually preventing resilience patterns

---

## Critical Insight

The code conflates three layers that should be separate:
1. **Error detection** (exception caught)
2. **Error persistence** (added to DLQ)
3. **Error propagation** (context["error"] passed onward)

These happen at different points with no clear orchestration. A system can't be both resilient AND coherent without clarifying which layer is responsible for each decision.
