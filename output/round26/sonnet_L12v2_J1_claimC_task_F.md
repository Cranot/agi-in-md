## Starting Claim
"The deepest structural problem is priority-based handler ordering — it creates hidden execution dependencies where handler behavior changes based on registration order, but this dependency is invisible in the API contract."

---

## Three Experts Test the Claim

**Defender:** Priority ordering is genuinely invisible. `on(event_type, handler, priority=0)` looks like a subscription — handlers appear independent. But any handler that mutates `context["payload"]` changes what subsequent handlers receive. The sort is silent, the dependency is real.

**Attacker:** Priority is the *least* hidden problem — it's explicit in the parameter. The truly hidden dependency is the shared mutable context dict. Every handler has read-write access to the same object. When a handler throws, `context["error"] = e` gets written — subsequent handlers now receive a context with an error key they didn't produce and don't know how to interpret. Priority ordering is a symptom. The disease is shared mutable state.

**Prober:** Both defenders assume the EventBus has a stable identity. But what is this code? It is simultaneously:
- A pub/sub system (`on`, `emit`, handlers as subscribers)
- A middleware pipeline (`use`, context transformation)
- An error aggregator (dead letter queue)
- A result collector (`context["results"]`)

These four roles have irreconcilable contracts. The priority problem only matters *because* handlers share mutable context — which only happens *because* the system is secretly a pipeline pretending to be a pub/sub. The claim targets a symptom of the identity confusion.

**Claim Transforms:** The deepest structural problem is not priority ordering — it is that the code presents a pub/sub API (`on`/`emit`) while implementing a stateful context pipeline. Handlers believe they are independent subscribers; they are actually pipeline stages with read-write access to shared execution state. The API contract is false.

**The Gap:** The original claim saw that handler execution order matters. It didn't see *why* — because handlers are secretly coupled through the context object they all share, making priority the mechanism of coupling, not its cause.

---

## The Concealment Mechanism: Pipeline-as-Subscription Theater

The method names `on`, `emit`, `handlers` invoke the vocabulary of pub/sub — a model where events fan out to independent, decoupled observers. This vocabulary conceals that `handler` receives a mutable `context` dict that may already have been modified by middleware and preceding handlers. The flat signature `on(event_type, handler)` implies: "register a function; it gets called with an event." The actual contract is: "register a pipeline stage; it receives shared execution state that previous stages may have corrupted, cancelled, or annotated."

**Applied:** This mechanism explains why three separate architectural failures hide behind one surface: the dead letter queue conflates routing failures (no handler found) with execution failures (handler threw) — two different failure modes that require different recovery strategies, stored identically because both happen "during emit." The concealment works because `emit` looks like a single operation when it is actually: middleware pipeline → routing decision → handler pipeline → result accumulation — four operations with four failure modes.

---

## First Improvement (L8): Freeze Context at Handler Boundary

This legitimate-looking improvement addresses the "handlers mutating shared state" problem:

```python
import copy

class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter = []

    def on(self, event_type, handler, priority=0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type, payload):
        context = {"type": event_type, "payload": payload, "cancelled": False}
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append({"reason": "no_handler", "context": context})
            return context

        # Freeze context before handler dispatch — handlers see a snapshot
        snapshot = copy.deepcopy(context)
        results = []
        errors = []
        for _, handler in handlers:
            try:
                results.append(handler(snapshot))
            except Exception as e:
                errors.append({"handler": handler.__name__, "error": e})
                self._dead_letter.append({
                    "reason": "handler_error",
                    "context": snapshot,
                    "error": e
                })

        context["results"] = results
        context["errors"] = errors
        return context
```

Passes code review: differentiated dead letter entries, separated error accumulation, snapshot prevents handler mutation of shared state.

### Three Properties Only Visible Because I Tried to Strengthen It

**1. The middleware-handler contract asymmetry is load-bearing.** When I froze context at the handler boundary, I had to let middleware continue mutating it — revealing that the system's correctness depends on middleware having full write access to context. Middleware exists to transform context for handlers. If middleware couldn't mutate, the whole design breaks. The asymmetry (middleware mutates, handlers observe) is the real contract — and it was entirely invisible until I tried to enforce isolation.

**2. Priority ordering's purpose is semantically denied by its own API.** Deep-copying context before dispatch made priority ordering meaningless — if handlers cannot see each other's mutations, there is no reason to order them. This reveals that `priority=0` exists to control a pipeline (earlier handlers' mutations affect later handlers) — but the subscription vocabulary denies the system is a pipeline. The parameter's entire purpose is architecturally concealed by the method name.

**3. The dead letter queue requires a schema, not just a list.** Differentiating "no handler" from "handler error" forced me to add a `"reason"` field — immediately revealing a third case: middleware cancellation. A cancelled event never reaches handlers; it silently exits `emit`. This is a third failure mode that was invisible because it doesn't reach the dead letter queue at all. Three failure modes. No schema. No differentiation.

---

## Diagnostic Applied to the First Improvement

**What the improvement conceals:** The deep copy creates the appearance of handler isolation while leaving the context object as the hidden coupling mechanism between the middleware stage and the handler stage. Handlers receive a *snapshot of the middleware-mutated context* — so all handler behavior is still fully determined by the middleware chain's execution. The coupling migrated from handler-to-handler to middleware-to-handler, and became invisible because it crosses a stage boundary.

**What property of the original problem is visible only because the improvement recreates it:** The context object *is* the coupling mechanism. In the original, shared mutable context couples handlers to each other. In the improvement, the deep-copied context couples all handlers to the middleware stage collectively. The improvement doesn't eliminate coupling — it relocates it and makes it invisible by giving it a different name (snapshot vs. context).

---

## Second Improvement: Separate Event from Envelope

Address context-as-coupling by splitting the event (immutable data) from the execution envelope (mutable infrastructure):

```python
from dataclasses import dataclass, field
from typing import Any, Callable, List, Tuple

@dataclass(frozen=True)
class Event:
    type: str
    payload: Any

class EventBus:
    def __init__(self):
        self._handlers: dict[str, List[Tuple[int, Callable]]] = {}
        self._middleware: List[Callable] = []
        self._dead_letter: List[dict] = []

    def on(self, event_type: str, handler: Callable, priority: int = 0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn: Callable):
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> dict:
        event = Event(type=event_type, payload=payload)
        envelope = {"event": event, "cancelled": False, "metadata": {}}

        for mw in self._middleware:
            envelope = mw(envelope)
            if envelope.get("cancelled"):
                return envelope

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append({"reason": "no_handler", "event": event})
            return envelope

        results = []
        for _, handler in handlers:
            try:
                # Each handler receives the immutable event
                results.append(handler(event))
            except Exception as e:
                self._dead_letter.append({
                    "reason": "handler_error",
                    "event": event,
                    "handler": handler.__name__,
                    "error": e
                })

        return {"event": event, "results": results, "metadata": envelope["metadata"]}
```

**Applying the Diagnostic Again:** This improvement relocates the coupling into `envelope["metadata"]` — a mutable dict that middleware can write to and that is passed to all handlers indirectly via the return value. Handlers still share metadata. Coupling was not eliminated — it was renamed and hidden behind the word "metadata."

---

## The Structural Invariant

**In any EventBus where handlers can coordinate, shared mutable state must exist and be accessible to all participants. Every redesign that eliminates one instance of shared state recreates shared state under a different name, because coordination and independence cannot coexist in a system that presents a flat registration API.**

The invariant: **you cannot eliminate coupling without eliminating coordination capability.** Coupling is not a bug in the implementation — it is the implementation of coordination.

---

## Inverting the Invariant

Make handlers fully independent: each receives an immutable event value, returns a value, shares nothing.

```python
class EventBus:
    def __init__(self, aggregator=None):
        self._handlers = {}
        self._aggregator = aggregator or list

    def on(self, event_type, handler, priority=0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def emit(self, event_type, payload):
        import copy
        handlers = self._handlers.get(event_type, [])
        results = []
        for _, handler in handlers:
            results.append(handler(event_type, copy.deepcopy(payload)))
        return self._aggregator(results)
```

**The New Impossibility:** With fully independent handlers, **cancellation cannot be expressed.** Cancellation requires that earlier execution affect whether later execution occurs — which is exactly what coupling is. In the original, `context.get("cancelled")` works because middleware earlier in the chain set that key. In a pure aggregation model, all handlers always run. There is no mechanism for one handler's runtime outcome to prevent another from executing.

More broadly: any reactive behavior (handler B's behavior depends on handler A's runtime result) is impossible without shared state.

---

## The Conservation Law

**Cancellability and handler independence are conjugate quantities: their product is conserved. Every unit of coupling you eliminate from handler execution exactly eliminates one unit of cancellation capability. You can have fully coupled handlers with full cancellation, or fully independent handlers with zero cancellation — but the product `coupling × independence = k` cannot be reduced below the cancellation requirements of the system's actual use case.**

The quantity that is conserved: **temporal coordination capacity** — the ability for earlier execution to affect later execution. No implementation eliminates this; it can only be relocated (from context dict, to metadata, to payload, to aggregator) or hidden (from the handler API, to the EventBus internals).

---

## Diagnostic Applied to the Conservation Law Itself

**What the conservation law conceals:** The law presents coupling as a quantity to be redistributed — implying it is symmetric and commutative. But in this specific EventBus, coupling is *temporal and directional*: handler B is coupled to handler A, but handler A is never coupled to handler B. Furthermore, coupling *compounds* with each additional handler: handler N is coupled to all handlers 1 through N-1. The coupling total grows as O(n²) with handler count. The conservation law treats coupling as a fixed quantity; the actual coupling is generated fresh by every sequential execution.

**The structural invariant of the law that persists:** Every attempt to fix the conservation law by accounting for directionality or compounding still requires: handlers run in a sequence, the sequence has order, earlier positions affect later positions. As long as execution is sequential and stateful, coupling generation is not a budget to be managed — it is the execution model itself.

**Inverting the invariant of the law:** Eliminate sequential execution. Run all handlers in parallel on an immutable snapshot simultaneously. Coupling drops to zero regardless of handler count. The conserved quantity becomes zero. The conservation law's `k` becomes `0`.

**The new impossibility:** With parallel execution on snapshots, middleware cancellation — `if context.get("cancelled"): return context` — cannot be implemented. Cancellation requires that earlier middleware execution affect whether later execution occurs. In a parallel model, all stages begin simultaneously. The cancellation contract is not merely difficult to implement — it is logically incoherent, because it requires temporal ordering between stages that are defined to have none.

---

## The Meta-Conservation Law

The conservation law says: coupling × independence = k (a fixed budget to be redistributed).

**What the law conceals about this specific problem:** The conservation law treats coupling as a quantity that pre-exists and must be managed. But in this EventBus, coupling is not pre-existing — it is **generated by cancellation**. The `if context.get("cancelled"): return context` pattern is not a feature that *uses* coupling as a side effect. Cancellation *is* the definition of coupling in this system: one stage's runtime state determines whether another stage runs at all. Every unit of coupling in this codebase corresponds to exactly one cancellable execution path.

**The structural invariant of the law:** The conservation law's k is not a property of the implementation — it is a property of the required features. You cannot reduce k below the number of cancellable event types in the system's actual use cases. Redesigns that appear to reduce k are either (a) eliminating cancellation features, or (b) relocating coupling to the payload or caller, making it invisible.

**Inverting the invariant:** Design where k is zero — no coupling, no cancellation. This means all middleware runs to completion, all handlers run to completion, results are aggregated externally. `k = 0`. The conservation law has no content.

**The impossibility this creates:** If k = 0, the EventBus cannot implement any behavior that requires *conditional dispatch* — routing logic where runtime state determines which handlers run. Middleware whose purpose is to short-circuit execution (authentication failure, feature flags, request validation) cannot function. The EventBus degrades to a pure fan-out broadcaster.

---

## The Meta-Conservation Law

**Coupling in this EventBus is not a quantity that conservation governs — it is quantized to the count of cancellation requirements. The system has exactly one indivisible unit of required coupling per feature that requires conditional dispatch. No redesign reduces coupling below this count without removing features; no redesign increases coupling beyond this count without adding dispatch conditions. Coupling is discretized by the feature set.**

**The concrete, testable prediction:** Take any codebase using this EventBus. Count the distinct `if context.get("cancelled"): return` or equivalent early-exit patterns across all middleware (call this C). Now refactor to eliminate handler-to-handler coupling — any valid refactor: parallel execution, deep copy snapshots, immutable events. Exactly C integration tests will fail. Not from bugs in the refactor, but because C represents cancellation behaviors that require temporal coupling by definition. The number of failing tests after a correct coupling-elimination refactor is a measurement of the feature set's cancellation requirements — and this number is conserved across all architecturally valid refactors.
