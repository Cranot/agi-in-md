# Structure First: EventBus Hypothesis

## The Falsifiable Claim

> **The deepest structural problem is that `context` is a single mutable dictionary shared by reference across all handlers, making handler-to-handler execution order a hidden contract. The same object that carries the event's identity (type, payload) also accumulates execution state (error, results, cancelled) — so what one handler writes, the next handler silently reads. This is not a bug that manifests sometimes; it is a coupling mechanism that is always present and never visible at the call site.**

This is falsifiable: if you can demonstrate that handlers in practice never read state written by prior handlers, or that a worse structural coupling exists, the claim fails.

---

## Three Experts Argue

### Expert 1 — The Defender

*The claim is correct, and here's the concrete mechanism:*

```python
# This is valid usage of this EventBus.
# It is also a silent disaster.

def handler_A(ctx):
    ctx["payload"]["discount"] = 0.10   # mutates payload

def handler_B(ctx):
    rate = ctx["payload"]["discount"]   # reads A's mutation
    return rate * ctx["payload"]["price"]

bus = on("checkout", handler_A, priority=10)
bus = on("checkout", handler_B, priority=5)
```

Handler B now **depends on Handler A having run first**. The priority numbers encode that dependency — but they do so invisibly. Nothing in the type signature, nothing in the registration API, nothing in the documentation forces you to declare this. The contract is load-bearing and unwritten.

The error path makes it worse:

```python
# After a handler throws:
context["error"] = e          # mutates shared context
self._dead_letter.append(context)  # appends the live object
# execution continues — next handler sees context["error"]
```

Three separate problems compound here:
1. The error field overwrites silently if two handlers throw (only the last error survives)
2. The dead_letter queue holds a **reference** to the live context, so later mutations are visible in the queue
3. Subsequent handlers receive a context that already carries an error they didn't cause

The claim holds. Mutable shared state is the gravity well everything else falls into.

---

### Expert 2 — The Attacker

*The claim misidentifies the symptom as the disease.*

Mutable context is a consequence, not the root. The actual deepest problem is **the absence of a capability boundary between middleware and handlers**. Both receive the same dict, both can write anything, and `emit()` doesn't distinguish what they're allowed to do.

Look at the middleware chain:

```python
for mw in self._middleware:
    context = mw(context)      # middleware can return None → crash
    if context.get("cancelled"):
        return context
```

If any middleware returns `None` (forgot a `return` statement), the next line calls `None.get(...)` and the entire bus crashes. This is not a theoretical edge case — it is the first bug a new contributor will write.

More critically: middleware is supposed to be a pipeline before delivery. But there's no structural separation between "middleware mutating context" and "handlers mutating context." A handler could add itself to `self._middleware` via closure. Nothing stops it.

The mutable-dict-as-shared-state problem the Defender describes is real, but it's downstream of a more fundamental absence: **there's no type boundary, no capability restriction, no contract about what each layer is allowed to read or write**. Fix mutability and you still have a system where a middleware and a handler are indistinguishable in power.

---

### Expert 3 — The Prober

*Both of you are arguing about implementation details and taking a deeper assumption for granted.*

The claim and its attack both assume that the EventBus's job is **delivery with controlled side effects**. That assumption is what makes mutable context look like a structural problem.

But ask: what is this EventBus actually modeling?

```python
def emit(self, event_type, payload):
    context = {"type": event_type, "payload": payload, "cancelled": False}
```

The dict is called `context`. It accumulates `results`, `error`, `cancelled`. By the time `emit()` returns, the caller gets back an object that is partly the event, partly the execution trace, partly an error report. **`emit()` is not fire-and-forget. It's a synchronous remote procedure call pretending to be an event.**

The name "EventBus" implies decoupling: emitters don't know who handles, handlers don't know who emits. But the return value of `emit()` couples them tightly:

```python
result = bus.emit("order.placed", order_data)
if result.get("error"):          # emitter checks handler errors
    ...
if result["results"][0] > 100:   # emitter reads handler return values
    ...
```

The claim about mutable shared state is true but secondary. The Defender's and Attacker's proposals (immutable context, capability boundaries) would make a cleaner version of the same wrong thing. 

**The unexamined assumption is that an EventBus should be synchronous and return handler results to the emitter.** Once you accept that, every other design decision follows as a consequence, including shared mutable context.

---

## Synthesis: What the Argument Revealed

| | Before the argument | After the argument |
|---|---|---|
| **The claim** | Mutable shared context = hidden coupling between handlers | Still true, but it's a *symptom* |
| **What it missed** | — | The deeper coupling is between emitter and handler via return value |
| **What both Defender and Attacker missed** | — | They both accepted synchronous emit-with-return as given |
| **The actual falsification test** | "Do handlers read each other's writes?" | "Does the emitter read handler results?" If yes, this isn't an event bus |

### What I know now that I couldn't know before

**The mutable-context problem and the middleware-boundary problem are both correct, but they're fighting over the wrong territory.** The system's deepest structural tension is that it conflates two different communication patterns:

```
Pattern A — True event bus:
  emit(type, payload) → void
  Handlers are side effects. Emitter is blind to them.

Pattern B — Request/response:
  result = call(type, payload) → results[]
  Caller needs handler output. Order matters. Errors propagate back.
```

This implementation tries to be both, and the mutable shared context is the scar tissue from that identity crisis.

### The transformed claim

> **The deepest structural problem is not mutable context — it's that `emit()` returns a result, making every "event" actually a synchronous broadcast RPC. Mutable context, undefined middleware contracts, and silent handler-to-handler coupling are all consequences of this original sin. You cannot fix them cleanly without deciding which thing this is.**

### The three concrete bugs that will happen in production

```python
# Bug 1: Middleware returns None → crash
bus.use(lambda ctx: ctx if not ctx["payload"].get("debug") else None)

# Bug 2: Dead letter holds live references — "immutable" audit log mutates
letter = bus._dead_letter[0]
bus.emit("same_type", new_payload)  # letter["results"] changes if context is reused

# Bug 3: Only last error survives; first handler's exception is lost
def h1(ctx): raise ValueError("constraint violation")
def h2(ctx): raise TypeError("wrong type")
# context["error"] = TypeError. The ValueError never existed.
```

The fix isn't patching these. It's choosing: **event bus, or request broker** — and building one of them completely.
