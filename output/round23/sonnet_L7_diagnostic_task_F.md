# Level 7 Diagnostic: EventBus

---

## I. The Initial Falsifiable Claim

**Claim:** The code's deepest structural problem is that `context` is a single mutable dict passed by reference through all middleware and handlers, making system state unpredictable — any component can corrupt the execution environment for all subsequent components with no isolation or rollback.

*Falsifiable because:* if we can demonstrate that no handler's mutations ever materially affect another handler's execution, the claim fails.

---

## II. The Three-Expert Dialectic

### Expert A — Defender
The mutable context is the *feature*, not the bug. This is the Express.js middleware pattern: shared context is how cancellation propagates, how results accumulate, how errors are communicated. Calling this the "deepest problem" mistakes intentional design for defect. The real fix is just copy-on-write for `payload` specifically.

### Expert B — Attacker
Mutability is symptomatic. The *actual* deepest problem is the dead letter queue conflating two completely different failure modes into one undifferentiated list:

```python
# Failure Mode 1: no handlers registered
if not handlers:
    self._dead_letter.append(context)  # ← semantic: "nobody listened"

# Failure Mode 2: handler threw exception  
except Exception as e:
    self._dead_letter.append(context)  # ← semantic: "someone listened and crashed"
```

These require opposite recovery strategies. The system has no coherent failure model.

### Expert C — Prober *(challenges what both take for granted)*
Both experts assume `emit()` *should* return something. Both assume synchronous, single-process execution. Neither questions this:

```python
context["results"] = results
return context  # ← why does an event bus return aggregated handler results?
```

**An event bus is fire-and-forget.** The moment `emit()` returns `results`, this is no longer an event bus — it's an RPC dispatcher. But it also has a middleware pipeline. The code is simultaneously implementing three architecturally incompatible patterns:

| Pattern | Contract |
|---|---|
| Event Bus | One-to-many, fire-and-forget, caller doesn't care about results |
| Middleware Pipeline | Sequential, transformative, output of step N feeds step N+1 |
| RPC Dispatcher | Call-and-response, aggregates return values for caller |

Neither expert questioned the architectural identity of the thing itself.

---

## III. The Transformed Claim

**Original:** Shared mutable context causes state unpredictability.

**Transformed:** This system has an **architectural identity crisis**. Its three subsystems — middleware pipeline, event dispatch, result aggregation — carry mutually incompatible contracts. The mutable context isn't the disease; it's a symptom of a system that cannot decide what it is.

---

## IV. The Gap as Diagnostic

The gap between claims:
- `[mutable dict] → [state unpredictability]` (safety/implementation level)
- `[three incompatible patterns] → [undefined behavioral contract]` (architecture level)

reveals that **the original claim audited the code against itself** — asking "is this implementation internally consistent?" The transformed claim audited the code against the *world* — asking "does this implementation have a coherent identity at all?"

The gap is a full level of abstraction. This means the code's real problems are invisible at the implementation level.

---

## V. The Concealment Mechanism: **Idiomatic Fragment Camouflage**

Each subsystem individually pattern-matches to a well-known, trusted idiom:

```python
# Looks exactly like Express.js middleware ✓
for mw in self._middleware:
    context = mw(context)
    if context.get("cancelled"): return context

# Looks exactly like Node's EventEmitter ✓
handlers = self._handlers.get(event_type, [])

# Looks exactly like a standard result collector ✓
results.append(handler(context))
```

The reader audits each fragment against its source idiom's norms and finds it locally coherent. The fragments *individually* pass inspection. This prevents stepping back to see that the assembled whole has no coherent contract.

**The concealment mechanism:** local idiomatic correctness launders global architectural incoherence.

---

## VI. What the Entire Dialectic Failed to Surface

Applying the mechanism: *what else looks locally correct but is globally incoherent?*

### Hidden Problem 1: Priority is Semantically Hollow — And Dangerous

```python
self._handlers[event_type].sort(key=lambda x: -x[0])  # priority ordering
```

Priority implies execution order matters. Execution order only matters if handler N's output affects handler N+1's input. But handlers don't receive each other's return values — those go to `results`. The *only* way priority matters is if handlers **mutate `context`** as a side effect.

This means the system has built an **implicit, untyped, undocumented pipeline** on top of what appears to be isolated dispatch. The "interface" between handlers is the entire context dict with no schema, no versioning, no contract. This is worse than explicit coupling because it *looks* like isolation while delivering the brittleness of coupling.

### Hidden Problem 2: The Dead Letter Queue Records Corrupted State

This is the most dangerous hidden problem:

```python
for _, handler in handlers:
    try:
        results.append(handler(context))  # handler mutates context
    except Exception as e:
        context["error"] = e
        self._dead_letter.append(context)  # appends post-mutation context
```

Consider the sequence:
1. `emit("payment.process", {"amount": 100})`
2. Handler 1 mutates: `context["payload"]["amount"] = 0` (normalization bug)
3. Handler 2 raises exception
4. Mutated context goes to dead letter queue

The dead letter queue stores **what the context looked like when the failure occurred** — not the original event. Anyone using the dead letter queue for **replay or audit** (its primary use cases) will replay the corrupted, mid-processing state, not the original intent.

```python
# What the caller thinks they're getting:
dead_letter[0]  # → {"type": "payment.process", "payload": {"amount": 100}}

# What they actually get:
dead_letter[0]  # → {"type": "payment.process", "payload": {"amount": 0}, "error": ...}
```

The dead letter queue *looks* like an audit log. It is actually a log of **failure-state snapshots of a shared mutable object**. It silently provides false provenance.

### The Master Hidden Problem

The idiomatic fragment camouflage operates at the system boundary too. This class is named `EventBus`, which sets a contract in the reader's mind (fire-and-forget, loose coupling, observable side effects). But it actually implements a **synchronous, tightly-coupled, result-aggregating pipeline with state-sharing across handlers**.

Every caller who treats this as an event bus — not checking return values, not knowing that handler order matters, assuming their handler runs in isolation — is operating on a false model. The code will silently deliver wrong behavior while appearing to work correctly.

```python
# Caller's mental model:
bus.emit("user.created", user_data)  # I fired an event, I don't care what happens

# Actual behavior:
# - Middleware may silently cancel it
# - Handlers execute in priority order, sharing and potentially corrupting each other's state  
# - Exceptions in any handler corrupt the shared context for subsequent handlers
# - The "dead letter" may contain a post-corruption snapshot recorded as the "original" event
# - All of this returns silently as a dict the caller discards
```

**The name `EventBus` is itself the final concealment** — it's an identity claim that makes the architectural incoherence invisible until something breaks in production in a way that's almost impossible to trace.
