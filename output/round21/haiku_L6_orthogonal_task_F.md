# Prediction First

**The singular most important thing these experts will collectively miss:** When a handler throws an exception, the code appends the **same mutable context object** to `_dead_letter`, then **continues mutating that object** through remaining handlers and the final `context["results"] = results` line. This creates **aliased references in the dead_letter queue** — multiple list entries pointing to a single dict that keeps changing, retroactively corrupting earlier records. The dead_letter queue doesn't record *state at time of failure*, but rather *final corrupted state*.

This is invisible because no single frame naturally traces mutation *through* the dead_letter data structure.

---

# Three Experts Argue

## Expert A: Pragmatist/Strengths 

> "This works. I see a clean pub/sub pattern — register handlers by priority, middleware for cross-cutting concerns, exception handling so one bad handler doesn't crash the bus. Good enough for internal tooling. You could use this in a project Monday."

*Points approvingly at:*
- Handler priority (elegant)
- Middleware hooks (extensible)
- Try/catch preventing cascade failure (responsible)
- Returns context for debugging (useful)

"The dead_letter queue is a nice touch for observability. Accumulating failed events gives you visibility."

---

## Expert B: Critic/Failure Modes

> "You're looking at multiple failures stacked here:"

1. **Memory leak**: `_dead_letter` grows unbounded. No pruning, no TTL. Leave this running for a week and it becomes a memory bomb.

2. **Performance**: Every call to `.on()` re-sorts the handler list. That's O(n log n) per add. Add 10,000 handlers? 160,000 comparisons just for ordering.

3. **Silent failure**: Exceptions are caught and buried in context["error"]. The caller gets a normal return. How do they know 3 handlers threw? They don't. The bus silently failed.

4. **Unsubscribe broken**: No way to remove a handler once added. If you register a handler in a test fixture and forget to clean up, it runs forever.

5. **Dead-letter semantics are wrong**: "No handlers found" is NOT a failure — it's normal pub/sub. Mixing it with exceptions is architecturally confused.

---

## Expert C: Functional/Orthogonal View

> "Both of you are fixing symptoms. The real problem is **the architecture fundamentally conflates incompatible patterns**."

"This code mixes:
- **Imperative mutation** (passing a mutable dict, adding keys like `context["error"]`)  
- **Declarative handler registration** (priority system suggests pure composition)  
- **Event sourcing** (dead_letter queue)  
- **Request/response** (returns results array)  

These don't belong together."

*Points at the core problem:*

```python
for _, handler in handlers:
    try:
        results.append(handler(context))
    except Exception as e:
        context["error"] = e        # ← Mutates shared dict
        self._dead_letter.append(context)  # ← Appends same object
    # Loop continues, context still mutable
context["results"] = results  # ← Mutates again
```

"**You're appending the same mutable object to dead_letter multiple times.** If handler[0] fails, you append context (with error='Handler0Failed'). Then handler[1] runs and mutates context. Then handler[2] fails, you append context again—but now it's got results from handler[1] baked in, and error is overwritten."

*The dead_letter queue contains multiple references to the same object. By the end, they all point to the final corrupted state.*

"This code needs immutable records, or at least defensive copies. The fact that you're returning context *and* mutating it *and* storing references to it is a recipe for debugging nightmares."

---

## Expert B Pushes Back at Expert C

"Wait, is that really the issue? I mean, yes, mutable shared state is gross, but in a single-threaded event loop it... mostly works?"

## Expert C Replies

"Mostly works *until you need to debug*. Suppose handler[0] fails, handler[2] fails, and now you pull `bus._dead_letter[0]` from a crash report. What do you have?
- The final combined state
- Corrupted with handler[1]'s results
- You have no idea what the state was when handler[0] actually failed

You can't audit, can't replay, can't test reliably. The dead_letter queue is a lie."

## Expert A

"...I mean, we could just not look at dead_letter too carefully? It's more of a logging thing—"

**Expert B & C in unison**: "No."

---

# Did They Miss The Prediction?

**Partial yes.** 

- **Expert C explicitly caught the dead-letter aliasing**, but framed it as one symptom of broader "immutable records" and "mutable state" problems, not as *the* core issue.
- **Expert B noticed the dead_letter design was confused** but didn't trace the specific aliasing bug in the exception-handling loop.
- **Expert A didn't look at it at all.**

**What this reveals:** The aliasing bug is invisible even when staring at the code because:

1. The bug requires tracing *through* a data structure (what's in dead_letter?), not just reading code linearly
2. It only manifests when *multiple handlers fail* — simple cases hide it
3. The symptom (corrupted records) doesn't crash the program, just silently breaks debugging
4. All three experts were drawn to higher-level patterns (strengths, perf, architecture) rather than micro-level object identity bugs

**The deepest invisible thing:** Even Expert C, who saw the mutation problem, didn't isolate that the dead_letter queue specifically becomes **unreliable data** — not just because it's mutable, but because it's a *collection of aliases to the same mutating object*. That requires thinking about collection semantics, not just code flow.
