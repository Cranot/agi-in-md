# EventBus: Structure-First Analysis

## Initial Falsifiable Claim

> **The deepest structural problem is that `context` is a single mutable dict passed through all middleware and handlers — making this semantically equivalent to global state with routing, not a message-passing system.**

---

## The Dialectic: Three Experts

### Expert 1 — Defender
The mutable context is intentional and useful. It mirrors Express.js `req/res`, Django middleware, and countless production patterns. `context["cancelled"]`, `context["results"]`, `context["error"]` — these are coordination mechanisms. You *want* middleware to enrich state. You *want* handlers to share a response accumulator. The mutability is the feature.

### Expert 2 — Attacker
The real problem isn't mutation itself — it's **unsynchronized, contract-free mutation**. There is no schema. No stage specifies which keys are valid, which are reserved, which are dangerous to overwrite. Handler A can silently clobber handler B's `context["error"]`. The dead letter queue receives a *live reference* to a dict that continues mutating after append. The problem is deeper than mutability: it's the **absence of a protocol** between the three execution stages.

### Expert 3 — Prober (surfaces what both take for granted)
Both of you assume this is a pub/sub system. You're debating *how* to route messages. But look at what the code actually does:
- Middleware transforms state **sequentially** (pipeline model)
- Handlers receive the same event **concurrently** (fan-out model)  
- Dead letter collects both unhandled AND errored events in the same bucket (error accumulator model)

These three models have **incompatible definitions of success, failure, and isolation**. Neither of you asked: *what is this system actually for?*

---

## The Transformed Claim

> **The deepest structural problem is that `emit()` has no coherent execution model — it simultaneously implements pipeline processing, pub/sub fan-out, and error accumulation, three paradigms with fundamentally incompatible assumptions about what isolation, causality, and failure mean.**

The gap between *mutable shared state* → *execution model identity crisis* is itself diagnostic: the mutation looked like the problem because it's the visible surface. It's actually the **load-bearing symptom** of a deeper confusion about what the system *is*.

---

## Concealment Mechanism #1: Cosmetic Robustness

The dead letter queue is the primary concealment device. It creates the *appearance* of error handling without the substance.

```python
# The illusion: errors are "captured"
except Exception as e:
    context["error"] = e
    self._dead_letter.append(context)   # ← appends a REFERENCE, not a copy

# What actually happens after this line:
results.append(handler(context))        # next handler mutates the same object
context["results"] = results            # overwrites the error record retroactively
return context                          # dead letter now contains THIS, fully mutated
```

**The concealment in action:**

```python
bus = EventBus()
bus.on("x", lambda ctx: (_ for _ in ()).throw(ValueError("boom")))
bus.on("x", lambda ctx: ctx.update({"stealth": "I ran after the crash"}))

bus.emit("x", {})
print(bus._dead_letter[0])
# → {"type": "x", "payload": {}, "cancelled": False,
#    "error": ValueError("boom"),
#    "stealth": "I ran after the crash",   ← dead letter is contaminated
#    "results": [None]}                    ← error is buried under results
```

The dead letter queue makes you *stop looking*. A queue exists, therefore errors are handled. But the queue contains mutated live references — a post-mortem that changes after death.

**Additional cosmetic robustness failures:**

```python
# 1. Middleware returning None crashes silently on next iteration
context = mw(context)           # if mw returns None...
if context.get("cancelled"):    # AttributeError: 'NoneType' has no attribute 'get'

# 2. Multiple exceptions: only the last one survives
context["error"] = e1           # handler 1 fails
# ... handler 2 also fails:
context["error"] = e2           # e1 is gone. silently.

# 3. Re-sorting on every subscription: O(n log n) per registration
self._handlers[event_type].sort(...)  # called inside on(), on every call
```

---

## Concealment Mechanism #2: Interface Symmetry Illusion

A completely different causal structure. The API presents `use()` and `on()` as symmetric — both add "processing stages." This **hides a radical asymmetry in power and failure semantics**.

```python
bus.use(auth_middleware)     # looks equivalent in weight to:
bus.on("event", handler)    # ← these are NOT equivalent
```

**Middleware has veto power. Handlers have no isolation:**

```python
# Middleware: unilateral cancellation, stops everything
def auth_mw(ctx):
    ctx["cancelled"] = True
    return ctx              # entire emit() returns here. No handlers run.

# Handler exception: fails silently, other handlers continue
def bad_handler(ctx):
    raise RuntimeError("I failed")
    # execution continues to next handler
    # the exception is stored in ctx["error"]
    # then overwritten by ctx["results"]
    # then the whole context is returned as if success
```

**The asymmetry table that the symmetric interface hides:**

| Dimension | Middleware | Handlers |
|---|---|---|
| Failure effect | Can abort all subsequent stages | Isolated per-handler (kind of) |
| Cancellation | First-class (`cancelled` key) | Not supported |
| Result visibility | Cannot see handler results | Can see prior handler results via shared ctx |
| Order enforcement | Strict sequential | Priority-sorted, but share state |
| Error propagation | Crashes emit() (if returns None) | Stored, swallowed, overwritten |

**The illusion breaks when you try to compose:**

```python
# You expect this to work like middleware wrapping handlers:
bus.use(lambda ctx: {**ctx, "authenticated": True})
bus.on("data", lambda ctx: print(ctx.get("authenticated")))  # True ✓

# But this fails silently:
bus.use(lambda ctx: {**ctx, "authenticated": True})
bus.on("data", bad_handler)   # raises, gets stored in ctx["error"]
bus.on("data", lambda ctx: print(ctx.get("authenticated")))
# → ctx["authenticated"] is True, but ctx["error"] is also set
# → is this a success or failure? The system cannot say.
```

---

## The Contradiction and What It Reveals

| | Mechanism 1: Cosmetic Robustness | Mechanism 2: Symmetry Illusion |
|---|---|---|
| **Where** | Output side: what happens to errors | Input side: what controls execution |
| **How it hides** | Dead letter queue signals safety | Symmetric API signals equivalence |
| **Prescription** | Fix error handling: copy contexts, propagate exceptions, clear state between handlers | Fix architecture: separate pipeline from fan-out, give middleware response access |
| **Root cause** | Mutation contaminates diagnostic records | Power asymmetry is unrepresentable in the interface |

**These prescriptions contradict.** M1 says: keep the architecture, fix the error flow. M2 says: the architecture is the error. You cannot do both.

**What the tension surfaces that neither mechanism alone could:**

The `context` dict is not a message. It is the **execution environment** — the hidden shared memory of the entire dispatch process. This is the thing neither mechanism directly names:

```python
# What context APPEARS to be:
{"type": "user.login", "payload": {"user_id": 42}, "cancelled": False}
# ↑ looks like a value: immutable, passable, replayable

# What context ACTUALLY IS:
# - the middleware pipeline's accumulator
# - the handler fan-out's shared scratchpad
# - the error record
# - the result collector
# - the cancellation signal
# all in the same dict, at the same time
```

**The architectural identity fraud:**  
An event bus promises *message passing* semantics: messages are values, isolated, replayable, order-independent. This implementation delivers *shared execution environment* semantics: order-dependent, stateful, unreplayable, non-concurrent.

The consequences flow from this single fact:

```python
# You cannot replay an event — context has already been mutated
# You cannot run handlers concurrently — they share ctx["results"]  
# You cannot version the protocol — any key can appear at any time
# You cannot test handlers in isolation — they depend on prior handler state
# You cannot audit what happened — dead letter contains the final mutated state, not the initial event
```

**The fix isn't patching error handling OR fixing the interface symmetry.** Both mechanisms are symptoms of using the same object as both the input (the event) and the output (the execution record). The structural repair is separation:

```python
# Immutable event — what happened
event = Event(type="user.login", payload={"user_id": 42})

# Mutable execution context — how we're processing it  
ctx = ExecutionContext(event)

# Middleware gets both, transforms context only
def middleware(event: Event, ctx: ExecutionContext) -> ExecutionContext: ...

# Handlers receive the immutable event, return isolated results
def handler(event: Event) -> HandlerResult: ...

# Bus assembles results — no shared scratchpad
results = [handler(event) for _, handler in handlers]
```

The tension between "cosmetic robustness" and "symmetry illusion" reveals that this code is **architectural identity fraud**: it presents itself as a message-passing system while implementing shared mutable state. Every other problem — the dead letter aliasing, the asymmetric failure modes, the middleware/handler power imbalance — is a predictable consequence of that single foundational misrepresentation.
