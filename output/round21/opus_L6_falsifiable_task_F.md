## Falsifiable Claim

> **The deepest structural problem is that `context` is a single shared mutable dictionary simultaneously serving as middleware transport, handler input, error record, and dead-letter evidence — making the system's behavior order-dependent in unrecoverable ways, and rendering the dead-letter queue forensically useless because it holds live references to an object that continues to mutate after enqueueing.**

---

## The Three-Expert Argument

### Expert A (Defender)

The evidence is right in `emit`. Walk the execution when handler 2 of 4 raises:

```python
# Handler 2 throws
except Exception as e:
    context["error"] = e              # mutates the shared dict
    self._dead_letter.append(context) # enqueues a REFERENCE

# Handler 3 runs next — receives context WITH "error" key from handler 2
# Handler 4 throws too:
    context["error"] = e              # OVERWRITES handler 2's error
    self._dead_letter.append(context) # enqueues the SAME reference again
```

After `emit` returns, the dead-letter queue contains **two entries pointing to the same dict**, which now has:
- `"error"` set to handler 4's exception (handler 2's is lost)
- `"results"` containing handler 3's and handler 4's outputs (appended after the errors)

This isn't a minor bug. It's a **structural impossibility**: you cannot reconstruct which handler failed with which error from the dead-letter queue. The forensic record destroys itself.

The same aliasing problem hits middleware. A middleware that decorates `context["payload"]` mutates it for every downstream consumer. There's no isolation boundary anywhere in the pipeline.

### Expert B (Attacker)

The aliasing is real, but calling it the *deepest* problem overstates it. The deeper issue is the **broken control-flow contract**:

1. **Errors don't halt iteration.** The `try/except` catches the exception and then *continues to the next handler*. This means the EventBus has **no transactional semantics** — it can't guarantee all-or-nothing delivery. That's an architectural decision that makes the bus unsuitable for any event where partial execution is dangerous.

2. **Middleware can silently annihilate context.** If a middleware returns `None` (easy mistake — forgetting `return context`), the very next line `context.get("cancelled")` throws `AttributeError`. The middleware contract is unenforceable.

3. **No unsubscribe.** You can add handlers but never remove them — a *memory leak by design* in any long-lived application.

The mutable-context problem is fixable with a one-line `copy.deepcopy`. The control-flow problems require redesigning the API surface. That makes the control-flow contract the deeper structural issue.

### Expert C (Probe — questioning assumptions)

Both of you assume the dead-letter queue is *meant* to be forensic and that error isolation *matters*. But what if this is designed as a fire-and-forget bus where dead-letter is just a "something went wrong" signal?

More importantly, **you're both describing symptoms of the same root cause**: the `context` dict is the *only* coordination mechanism. It's the pipeline state, the result accumulator, the error channel, and the cancellation signal. Expert A says "it mutates"; Expert B says "the flow around it is wrong." But both problems vanish if you **separate the concerns into distinct structures**:

| Concern | Current home | Proper home |
|---|---|---|
| Cancellation signal | `context["cancelled"]` | Return value / exception from middleware |
| Error record | `context["error"]` | Per-handler result wrapper (`Ok`/`Err`) |
| Handler results | `context["results"]` | Returned from `emit`, not stuffed into context |
| Dead-letter evidence | Reference to live `context` | Immutable snapshot / frozen dataclass |

The real claim should be: **`context` is an [anemic god-object](https://en.wikipedia.org/wiki/God_object)** — a flat dict that absorbs every cross-cutting concern because the design has no other coordination primitive.

---

## Verdict: Transformed

My original claim (mutable aliasing) was **not falsified** — the dead-letter corruption is real and demonstrable. But it was **incomplete**. Expert B showed that control-flow failures (non-halting errors, unenforced middleware contracts) are equally structural. Expert C revealed that both are symptoms of a single architectural absence: **there is no separation between the event's identity, the pipeline's control state, and the accumulated results.**

### What I know now that I couldn't know before the argument:

The deepest problem is not *mutation*. It's **role conflation**. A single `dict` simultaneously acts as:
1. **Immutable event envelope** (type + payload)
2. **Mutable pipeline state** (cancelled, error)
3. **Result accumulator** (results)
4. **Forensic snapshot** (dead-letter evidence)

These four roles have incompatible lifecycle and mutability requirements. Every concrete bug — aliased dead-letter entries, error bleed-through, silent middleware failures, unenforceable contracts — is a direct consequence of jamming them into one untyped, mutable, shared dictionary. The fix is not `deepcopy`. It's **introducing distinct types for each role**, at which point the control-flow problems Expert B raised become trivially solvable.
