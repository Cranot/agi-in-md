# EventBus Analysis: Recursive Falsification

## First Claim (Specific, Falsifiable)

> **The deepest structural problem is that `emit` passes a single mutable dict through every stage of the pipeline, creating no isolation boundary between middleware, handlers, and the error system — any participant can corrupt the state that all subsequent participants observe.**

---

### Three Experts Test It

**Expert A — Defender:**
The evidence is concrete. A handler that errors sets `context["error"] = e` and execution *continues* — subsequent handlers receive a context already marked as failed. A middleware that enriches the context (e.g., adds `"user"`) and a handler that deletes `"user"` corrupt each other's assumptions silently. The `results` key doesn't exist until *after* all handlers run, so any handler reading `context["results"]` gets a `KeyError`. These aren't edge cases; they're guaranteed collisions on every non-trivial use.

**Expert B — Attacker:**
Shared mutable context is the *design*, not the bug — Express.js, Koa, and Django middleware all operate this way. The real failure is that there's *no protocol* governing mutation. `context = mw(context)` implies middleware should return a context, but it doesn't enforce what "return" means. If middleware mutates and returns the same dict, it works. If it returns a new dict, the emitter holds a reference to an orphaned object. The problem isn't mutation; it's that the pipeline contract is undefined — middleware can do anything and the system cannot distinguish valid transformations from corruption.

**Expert C — Probe (What Do Both Claims Take for Granted?):**
Both assume the bus *should* be a pipeline — that middleware and handlers belong in the same data-transformation chain. But ask: why can middleware *cancel* an event? Why can it *modify* the payload? Why does it return context at all? The code is simultaneously modeling: (1) an **event** (something happened), (2) a **command** (instruct handlers to act), (3) a **transaction** (can be cancelled), and (4) a **query** (accumulates `results` as a return value). These are categorically different things. The shared mutable dict isn't just an implementation weakness — it's the only way to hold together a system that doesn't know what it's modeling.

---

### The Claim Transforms

The first claim was about mechanics: *shared mutable state breaks isolation.* After the three-way test, it becomes something more fundamental: **the system has no coherent model of what `context` is.** It is simultaneously a signal, a transaction record, a data bag, and a result carrier — and each role adds keys that conflict with the others.

---

## Second Claim (Only Possible After Round One)

> **The EventBus conflates events (things that happened), commands (things to do), and queries (things to know) into one undifferentiated dict. Every specific defect — the broken error handling, the undefined middleware contract, the semantically mixed dead-letter queue — is a *symptom* of this category error, not the disease itself. No implementation fix can resolve it; the system requires an architectural decision about what it is routing.**

Here is the category error made concrete:

```python
# "event" reading of context: something happened
context = {"type": "user.login", "payload": {...}}

# "command" reading: the cancellation flag makes it a command
context["cancelled"] = True          # stop all further action

# "query" reading: results are aggregated for a caller who wants a return value
context["results"] = [...]           # emit() is now a function call

# "error record" reading: context becomes an incident log
context["error"] = SomeException()   # now it's a log entry

# All four roles, one dict, no protocol
self._dead_letter.append(context)    # which reading applies here?
```

The dead-letter queue is the most diagnostic symptom: it receives both *unrouted events* (nothing was listening) and *failed handler executions* (something broke during handling). These are incompatible states with incompatible remediation strategies — but the system cannot distinguish them because it never decided what it was routing in the first place.

---

## Is the Second Claim Categorically Deeper?

Yes — not a refinement. A taxonomy of the distance:

| | First Claim | Second Claim |
|---|---|---|
| **Level** | Implementation mechanics | Ontological design |
| **Diagnosis** | Isolation missing between stages | Categories missing between concerns |
| **Fix** | Make context immutable; copy on pass | Decide what the bus routes: events OR commands OR queries |
| **Evidence** | Specific line numbers | The shape of the whole system |
| **Falsifiability** | "Show me a failing test" | "Show me a coherent mental model" |

---

## What the Distance Reveals

Single-pass analysis finds what is *broken*. Recursive analysis finds what is *confused*. The gap between the two claims reveals the limit of bug-hunting as a methodology: you can patch every broken line in this code — add copying, fix error handling, unify the dead-letter queue — and still have a system whose participants cannot agree on what they're participating in.

The structural tell is that every patch would add *more keys* to the context dict. That's how you know the confusion is load-bearing: the dict grows because there is no concept that could replace it.

A genuinely different architecture would separate the three concerns:

```python
# Events: fire and forget, no return value
bus.emit("user.login", payload)

# Commands: routed to exactly one handler, returns result or raises
result = bus.dispatch(LoginCommand(payload))

# Queries: broadcast, collect all responses
answers = bus.query(WhoIsOnline())
```

The distance between Claim 1 and Claim 2 is exactly the distance between "this code has bugs" and "this code has the wrong shape."
