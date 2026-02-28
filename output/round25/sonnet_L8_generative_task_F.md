# EventBus: A Structural Autopsy

## The Falsifiable Claim

**Claim:** This EventBus's deepest structural problem is that `context` — a single mutable dict — serves simultaneously as the input envelope, the inter-stage communication channel, and the output record, making it impossible for any stage to reason about what it will receive, what it's allowed to modify, or what its mutations mean to downstream consumers.

*Falsifiable prediction:* Any middleware that adds a key to `context` risks silently overriding a key a handler depends on, with no error raised and no test capable of catching it without exhaustive key-enumeration of all possible middleware/handler combinations.

---

## The Three-Expert Crucible

### Expert A (Defender)

The mutable dict is the root. Every observable bug flows through it:

```python
# Middleware corrupts payload silently
def bad_middleware(ctx):
    ctx["payload"] = ctx["payload"].upper()  # handler expecting dict now gets string
    return ctx

# Error erasure — last exception wins, all others lost
for _, handler in handlers:
    try:
        results.append(handler(context))
    except Exception as e:
        context["error"] = e          # previous errors overwritten here
        self._dead_letter.append(context)  # same mutated dict reference stored
```

The shared dict is the God Object of pipeline state. This claim stands.

### Expert B (Attacker)

Shared mutable context is common and often correct — Express.js `req/res`, WSGI environ, Django middleware chains all use it. The *actual* deepest problem is **the absence of error propagation boundaries**. Two distinct failure modes are silently conflated into one queue:

```python
# Failure Mode 1: No handlers registered (infrastructure failure)
if not handlers:
    self._dead_letter.append(context)

# Failure Mode 2: Handler threw (application logic failure)
except Exception as e:
    context["error"] = e
    self._dead_letter.append(context)
```

These require completely different responses. Mixing them into `_dead_letter` makes the queue diagnostically useless. That's the structural rot — mutable context is just how it presents.

### Expert C (The Probe)

Both of you are assuming the semantic contract of "event" is settled. It isn't. Ask this: *what does a handler's return value mean?*

```python
results.append(handler(context))   # handlers return values...
# ...but context["payload"] is never updated from those values
# ...and subsequent handlers receive the ORIGINAL payload, not the accumulated result
```

Handlers both **return values** (suggesting a transformation pipeline: each stage processes and forwards) and **receive unmodified payload** (suggesting a notification bus: each subscriber sees the original event independently). These are incompatible models.

The code doesn't choose between them. It superimposes them. What looks like generality is actually **unresolved design ambiguity encoded as implementation**.

---

## The Transformed Claim

| | Claim |
|---|---|
| **Original** | "Shared mutable context is the root problem." |
| **Transformed** | "The code conflates two incompatible event semantics — *notification bus* and *transformation pipeline* — and uses shared mutable context as the mechanism that papers over the contradiction, making the conceptual incoherence invisible." |

**The diagnostic gap:** I moved from *how* the bug manifests (mutation) to *why* it exists (unresolved semantic contract). Mutable context is the symptom. The cause is that the code never answered: "Does a handler transform the event, or react to it?"

---

## The Concealment Mechanism

**Name:** *Feature-layer semantic laundering* — each individually reasonable feature (priority ordering, middleware chain, dead letter queue, result collection) creates the appearance of deliberate, coherent design, obscuring that the features serve two incompatible models simultaneously.

**Applied diagnostically:**

```python
# This looks like robust middleware architecture:
for mw in self._middleware:
    context = mw(context)          # looks like: "pipeline"

# This looks like fan-out notification:
for _, handler in handlers:
    results.append(handler(context))  # looks like: "broadcast"

# But context["payload"] never becomes context["results"]
# The two models never integrate — they just coexist, hiding the gap
```

The dead letter queue looks like enterprise-grade error handling. Priority sorting looks like a mature pub/sub feature. Each feature is a legitimizing surface that makes the incoherence beneath it harder to question.

---

## Reverse Application: Strengthening the Concealment

To make the real problem *harder* to detect, make each mode look more intentional:

```python
class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter = []
        self._mode = "auto"  # <-- NEW: looks like deliberate mode selection

    def on(self, event_type, handler, priority=0, mode="notify"):
        # mode="notify" | "transform"  <-- looks like the dual semantics are intentional
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler, mode))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def emit(self, event_type, payload):
        context = {"type": event_type, "payload": payload, 
                   "cancelled": False, "chain": []}  # "chain" implies pipeline
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append({"reason": "no_subscribers", "context": context})
            return context
        results = []
        for _, handler, mode in handlers:
            try:
                result = handler(context)
                results.append(result)
                context["chain"].append(result)  # looks like chaining, but payload unchanged
                if mode == "transform" and result is not None:
                    context["payload"] = result  # only transforms if explicitly opted in
            except Exception as e:
                self._dead_letter.append({"reason": "handler_error", 
                                          "handler": handler.__name__,  # named errors!
                                          "error": e, "context": context.copy()})
        context["results"] = results
        return context
```

**What each concealment move does:**

| Addition | What It Appears to Fix | What It Actually Does |
|---|---|---|
| `mode="notify"\|"transform"` | Makes dual semantics explicit | Encodes the ambiguity as a "feature toggle," normalizing it |
| `context["chain"]` | Suggests pipeline composition | Gives handlers the illusion of seeing prior results while payload mutation is opt-in and inconsistent |
| `handler.__name__` in dead letter | Looks like better diagnostics | Makes the conflation of failure modes *look* resolved while preserving it |
| `context.copy()` in dead letter | Snapshot isolation | Hides that live contexts are still mutated after dead-letter insertion |

---

## What This Reveals About the Problem's Actual Structure

The fact that I can construct a *more concealed* version using only **additive, legitimate-looking features** tells us three things:

**1. The problem reproduces through normal development.**
Every strengthening move I made is something a competent engineer would add in a code review: better error logging, more explicit modes, chain tracking. The problem doesn't get fixed by iteration — it gets *encoded deeper into the artifact*, because iteration adds features without resolving the foundational question.

**2. The problem is not in the code — it's between the code and the team's mental model.**
The `mode` parameter I added would cause different engineers to write handlers with different assumptions about what "transform" means and whether `payload` propagates. The code becomes a Rorschach test that different callers interpret differently, and integration only reveals the mismatch.

**3. The problem is stable under refactoring.**
You could rewrite this EventBus in Go, Rust, or TypeScript with full type safety, and the semantic conflation would survive if you don't make an explicit architectural decision first: *Is this a notification bus or a transformation pipeline?* Type systems, tests, and documentation will faithfully encode the ambiguity without resolving it.

**The actual structure of the problem is this:** The code is *answering a question that was never asked* — what is an event here? — with a default of "both, simultaneously." Every real bug this code produces in production will be traceable to a moment where a handler author assumed one answer and a middleware author assumed the other.

---

## What Should Actually Change

The fix is not implementation-level. It's a forced choice:

```python
# Option A: Notification Bus — handlers are independent side effects
class NotificationBus:
    def emit(self, event_type, payload):
        # payload is immutable, handlers return nothing meaningful,
        # context is not shared across handlers
        frozen_payload = types.MappingProxyType(payload)
        ...

# Option B: Transformation Pipeline — output of stage N is input of stage N+1  
class Pipeline:
    def process(self, event_type, payload):
        # each stage receives the OUTPUT of the previous stage
        result = payload
        for stage in self._stages[event_type]:
            result = stage(result)
        return result
```

The current code tries to be both. Making that choice explicit doesn't just fix bugs — it makes the *concealment impossible*, because you can no longer add features that look like they serve both models. The code's interface becomes its own constraint on confused usage.
