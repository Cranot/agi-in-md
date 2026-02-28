# Three Experts Analyze This EventBus

**Prediction before they speak:** I predict **Expert 3** (the holistic thinker) will surface the deepest insight. The others will identify real bugs; Expert 3 will expose the architectural incoherence that *generates* those bugs. Here's why I think this: The system conflates three patterns (event broadcasting, middleware transformation, error resilience) without declaring what "success" means. That's not a bug—that's a design philosophy problem hiding inside what looks like clever code.

---

## The Argument

**Expert 1 (Architect, seeing strengths):**

"This is clean architecture. You've got separation of concerns—middleware handles cross-cutting logic, handlers handle business logic, dead letter handles observability. Priority-based execution lets you control ordering. The context object threads state through the pipeline elegantly."

---

**Expert 2 (Skeptic, hunting failure modes):**

"Stop. The dead letter queue is a disaster waiting to happen. When a handler throws an exception on line 37, you add context to dead letter. Then line 38 continues to the *next* handler. So I run 5 handlers, the 3rd one throws, and I've got:
- Results array with results from handlers 1, 2, 4, 5 (handler 3 is missing)
- An entry in dead letter
- No way to know *which* handler failed
- Next time this event is reprocessed, it'll fail the same way

That's a poison pill. You've conflated 'no handlers exist' (dead-letter line 33) with 'handler execution failed' (dead-letter line 39). These are completely different problems needing different remediation."

**Expert 1 responds:**

"But that's the *point*—resilience through partial execution. Continue processing with other handlers even if one fails."

**Expert 2:** 

"Then why isn't the *success case* also in dead letter for audit? The asymmetry proves you haven't decided what dead letter *means*. Is it 'errors I need to fix'? Or 'events I need to replay'? Or 'audit trail'? You're storing information without a purpose, which is how monitoring systems become write-only nightmares."

---

**Expert 3 (Holistic, seeing what both miss):**

"You're both right and both missing the real problem. Expert 1, you're right that the structure *looks* elegant. Expert 2, you're right that the dead letter is incoherent. But here's the actual issue: **this system never declares what 'success' means.**

Look at what happens:
- Event emitted
- Middleware *mutates* context (line 20: `context = mw(context)`)
- Handlers execute, some may throw
- Dead letter captures... events? Errors? Partial failures?

You're mixing immutable event facts with mutable transformations. Real event buses preserve the original event as the source of truth. This design loses it inside middleware mutations. And the dead letter isn't a reliable journal—it's a garbage bin."

**Expert 1:** 

"But middleware transformation is essential—enrichment, validation, routing decisions..."

**Expert 3:**

"Not in an event bus architecture. In event sourcing, the event *is* the immutable fact. Middleware transformations should produce *new* commands or side effects, not mutate the event itself. The fact that middleware can cancel execution (line 21) suggests this isn't really an event bus—it's a **command dispatcher** with event-like syntax. Command dispatchers *should* have early exit on validation failure. But then it's not an event bus anymore, and the dead letter queue concept breaks down."

**Expert 2 (joining Expert 3):**

"Yes! Look at the unsubscribe problem too. There's no way to remove handlers. If I subscribe inside a loop by accident, I'm leaking handlers forever. The dead letter queue will grow unbounded. And sorting handlers on *every registration* (line 12) is O(n log n) per subscription when you could use a heap—that's careless."

**Expert 1:**

"Those are implementation details, not architectural problems."

**Expert 3:**

"No, they reveal the same root issue: the design has no **operational contract**. It doesn't say:
- 'How do I unsubscribe?' (can't)
- 'What does failure mean?' (unclear)
- 'Can I observe my handlers?' (no introspection)
- 'What happens if middleware returns None?' (undefined)
- 'Are handlers ordered or race?' (sorted once, but ties are undefined)

Compare to a real event bus: structured logging statements about 'handler X executed' or 'middleware rejected this event at step Y'. This just accumulates errors in a side table."

**Expert 2:**

"The priority system itself is a smell. If handler A must run before handler B, that's a hidden dependency the system doesn't make visible. You're creating implicit execution order semantics. Better to make dependencies explicit or use async/await to sequence things."

**Expert 1 (weakening):**

"Okay, so what's a better design?"

**Expert 3:**

"You need to pick your philosophy:

1. **Event Bus (immutable facts):** Preserve original event, emit new events as side effects, handlers are subscribers that can't block. Dead letter only for 'this type has no subscribers' as a data routing issue.

2. **Command Dispatcher (mutable instructions):** Declare handler ordering explicitly in a DAG, fail-fast on any error, return structured error explaining *which step* failed and why.

3. **Saga Orchestrator (with compensation):** Track handler execution, provide rollback mechanism, dead letter means 'couldn't compensate—manual intervention needed.'

This implementation is a confused hybrid of all three."

---

## Was My Prediction Right?

**Yes, Expert 3 surfaced the deepest insight.** But not in the way I expected.

I predicted Expert 3 would identify the conflation of patterns. They did. But the *deeper* insight that emerged only through argument was that this code isn't architecturally flawed because it has bugs—it's flawed because **it makes implicit choices that prevent clear error handling.**

The dead letter queue isn't bad because it stores errors; it's bad because the system never declared what role it plays. Middleware mutation isn't bad because it mutates; it's bad because the system never declared whether events are facts (immutable) or instructions (mutable).

---

## What the Gap Reveals

**What both Expert 1 and 2 missed individually:**
- Expert 1 saw elegance and missed that elegance requires *constraints* the code doesn't enforce
- Expert 2 saw bugs and missed that bugs are *symptoms* of missing semantics

**What the argument revealed that no single voice could:**

The real failure mode isn't any single bug—it's **semantic ambiguity**. When code doesn't declare what success/failure/retry/cancel *mean*, every operator (middleware, handler, dead letter) becomes a guess about intent. This is why error handling breaks down.

**The hidden cost:** Future maintainers will add handlers, trigger edge cases, ask "why is this in dead letter?", and have no principled answer. They'll bolt on retry logic in middleware (Expert 1's instinct), making the semantic confusion worse. They'll add monitoring without understanding what they're monitoring (Expert 2's nightmare).

---

## What Would Fix This

Add explicit semantics, like:

```python
class EventBus:
    # Declare what "success" means
    class EmitPolicy(Enum):
        FAIL_FAST      # Stop on first handler error
        FAIL_THROUGH   # Run all, collect errors
        FIRE_AND_FORGET # Don't wait for results
    
    def emit(self, event, policy=EmitPolicy.FAIL_FAST):
        # Now dead_letter has ONE meaning: 
        # "handler threw when policy said don't"
        # Now middleware can't mutate, only observe
```

The principle: **Make the policy visible in the API itself.** Then dead letter actually means something.
