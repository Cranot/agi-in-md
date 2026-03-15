# EventBus: Deep Structural Analysis

---

## The Initial Claim

**Falsifiable claim:** This EventBus's deepest structural problem is that `context` — a plain mutable dict — simultaneously serves as event specification, middleware communication channel, and result accumulation record. Because these three roles are merged into one object, no handler or middleware can reason about what it receives without knowing the complete prior execution history. The system's observable behavior is a function of `(event_type, payload, middleware_order, handler_registration_order, prior_emit_side_effects)` — but the call site only expresses the first two.

---

## Three Experts Transform the Claim

**Expert A (Defender):** The mutable shared context is unambiguously the problem. If you freeze the context after middleware runs, handler behavior becomes deterministic given identical inputs. The culprit is `context["error"] = e` — an errored handler silently poisons the context seen by subsequent handlers. This is empirically falsifiable and the fix is obvious: copy-on-write semantics.

**Expert B (Attacker):** Mutation is a symptom. The actual problem is that `emit` returns a value. A *bus* doesn't return anything — it delivers messages. The moment `emit` returns `context`, you've built a pipeline that pretends to be a bus. The mutable dict is just what synchronous execution looks like when an architecture doesn't know what it is. Fix the mutation and you've cleaned the wound while ignoring the fracture.

**Expert C (Prober):** You're both assuming the bus's job is to deliver messages. Neither of you asked: what does the *caller* do with the returned context? If they branch on `context["results"]` or re-route on `context["error"]`, the caller is a participant in the computation chain — they're a handler that runs after all handlers. The assumption you share is that infrastructure should be transparent. But this code treats dispatch as computation with observable return values. The question isn't "how does context get corrupted?" It's "why does a bus have return values at all?"

**The transformed claim:** The deepest structural problem is that the system conflates **event dispatching** (infrastructure: fire and route) with **computation** (transformation: input → output). Every design decision downstream — mutability, error handling, dead letters, priority — is solving a problem in the wrong paradigm. An event bus that returns accumulated results isn't a bus; it's a pipeline. This code is trying to be both simultaneously, and that's not fixable by cleaning up the dict.

---

## The Gap as Diagnostic

Original claim: *mutable dict creates execution-order dependence.*
Transformed claim: *the system doesn't know if it's a bus or a pipeline.*

The gap is one level of abstraction. I started at the implementation and landed at architectural identity. The mutation wasn't the problem — it was evidence of the confusion.

**The concealment mechanism:** The `context` dict looks like a DTO — a neutral carrier, which is an accepted pattern in event systems. DTOs are boring and correct. But this dict is actually an implicit call stack and accumulator. The naming and structure (`dict` with string keys, named `context`) signals "data container" while behaving as "mutable computation state." The code hides an architectural ambiguity behind a pattern that nobody scrutinizes.

**Applied:** Notice that `context["results"]` and `context["cancelled"]` and `context["error"]` are categorically different things — lifecycle flags, failure records, and return value aggregation — collapsed into one flat dict. The concealment works because dicts are structureless; they absorb all concerns without announcing it.

---

## Improvement 1: Legitimate-Looking, Deepens Concealment

```python
from dataclasses import dataclass, field
from typing import Any, List, Optional

@dataclass(frozen=True)
class EventContext:
    type: str
    payload: Any
    cancelled: bool = False
    metadata: tuple = field(default_factory=tuple)  # immutable k/v pairs

    def cancel(self) -> "EventContext":
        return EventContext(
            type=self.type, payload=self.payload,
            cancelled=True, metadata=self.metadata
        )

    def with_meta(self, key: str, value: Any) -> "EventContext":
        return EventContext(
            type=self.type, payload=self.payload,
            cancelled=self.cancelled,
            metadata=self.metadata + ((key, value),)
        )

@dataclass
class DispatchResult:
    context: EventContext
    results: List[Any] = field(default_factory=list)
    errors: List[Exception] = field(default_factory=list)
    dead_lettered: bool = False

class EventBus:
    def __init__(self):
        self._handlers: dict = {}
        self._middleware: list = []
        self._dead_letter: List[EventContext] = []

    def on(self, event_type: str, handler, priority: int = 0):
        self._handlers.setdefault(event_type, [])
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> DispatchResult:
        ctx = EventContext(type=event_type, payload=payload)

        for mw in self._middleware:
            ctx = mw(ctx)          # middleware returns new frozen context
            if ctx.cancelled:
                return DispatchResult(context=ctx)

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(ctx)
            return DispatchResult(context=ctx, dead_lettered=True)

        result = DispatchResult(context=ctx)
        for _, handler in handlers:
            try:
                result.results.append(handler(ctx))
            except Exception as e:
                result.errors.append(e)
                self._dead_letter.append(ctx)

        return result
```

This passes code review. Typed, immutable context, separated result object, errors collected cleanly. A reviewer would approve it. But:

---

## Three Properties Visible Only Because We Tried to Strengthen It

**Property 1 — The bus/pipeline confusion is now better furnished.**
`DispatchResult` gives the wrong architecture better vocabulary. A bus doesn't need a `DispatchResult` with accumulated `results`. We've made the architectural confusion more comfortable to inhabit, which is exactly what deepened concealment means.

**Property 2 — Middleware ordering is now exposed as a hidden schema.**
With a mutable dict, middleware order was a runtime concern — chaotic but fixable per-incident. With immutable context, each middleware must return a new `EventContext`, so accumulated `metadata` is the only channel for upstream→downstream communication. This makes the dependency chain explicit but invisible: middleware N implicitly depends on the keys middleware N-1 set, and there's no enforcement mechanism. The system now has a hidden schema with no schema registry.

**Property 3 — Error semantics changed without announcement.**
In the original, `context["error"] = e` was written into the shared context — subsequent handlers received a context with an error key set, which they could inspect. In this version, errors go into `DispatchResult.errors`, and the context passed to all handlers is pristine. Handlers can no longer observe that a prior handler failed. This is a behavioral change presented as a cleanup.

---

## Diagnostic of Improvement 1

**What it conceals:** `DispatchResult` makes the system look like a well-designed pipeline with separation of concerns. It hides that a pipeline knows its shape (fixed stages), while this system's shape is runtime-dynamic (arbitrary handler count, arbitrary middleware). A pipeline can optimize and reason statically; this cannot. The clean types make the wrong architecture legible, which makes it harder to question.

**Property of the original problem recreated:** Handlers now receive identical, unmodifiable context — they cannot coordinate. In the original, a handler could set `context["stop_propagation"] = True` to halt subsequent handlers. That's gone. So we've recreated the original problem in negation: **handler isolation and handler coordination are mutually exclusive, and the improvement forces isolation without acknowledging the choice.**

---

## Improvement 2: Addressing Handler Coordination

```python
@dataclass
class ExecutionContext:
    """Mutable dispatch-scoped coordination space. 
    Separate from event data; lives only for one emit call."""
    stop_propagation: bool = False
    shared: dict = field(default_factory=dict)

class EventBus:
    def emit(self, event_type: str, payload: Any) -> DispatchResult:
        event_ctx = EventContext(type=event_type, payload=payload)
        exec_ctx = ExecutionContext()

        for mw in self._middleware:
            event_ctx = mw(event_ctx, exec_ctx)  # middleware gets both
            if event_ctx.cancelled:
                return DispatchResult(context=event_ctx)

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(event_ctx)
            return DispatchResult(context=event_ctx, dead_lettered=True)

        result = DispatchResult(context=event_ctx)
        for _, handler in handlers:
            if exec_ctx.stop_propagation:
                break
            try:
                result.results.append(handler(event_ctx, exec_ctx))
            except Exception as e:
                result.errors.append(e)
                self._dead_letter.append(event_ctx)

        return result
```

**Diagnostic of Improvement 2:** Now two contexts flow through the system — `EventContext` (immutable: what the event is) and `ExecutionContext` (mutable: what is happening to it). This is genuinely cleaner. But it recreates the original problem at a higher level: middleware must now choose which context to communicate through. If through `EventContext` (immutable), middleware can't accumulate state. If through `ExecutionContext` (mutable), middleware ordering is a hidden runtime dependency again — now for two objects instead of one.

**The property this recreates:** We've drawn the boundary between event-identity and dispatch-state explicitly, which reveals there's no principled answer to *what belongs in each*. Is a rate-limit token event data or execution data? Is a correlation ID event metadata or dispatch metadata? The boundary we drew is arbitrary, and it persists as a system-wide convention with no enforcement.

---

## The Structural Invariant

Across every improvement, one property persists:

> **In any event system supporting ordered middleware, multiple handlers, handler coordination, and observable results — there must exist at least one mutable shared state space accessible across the dispatch lifecycle. Its location can change (dict, dataclass, ExecutionContext) but it cannot be eliminated.**

This is a property of the **problem space**, not the implementation. The requirements themselves necessitate it:

- Ordered middleware with cumulative effect → requires state accumulation
- Handler coordination (stop propagation, priority gates) → requires shared writable space
- Observable results at the call site → requires result accumulation
- Dead lettering → requires persistent state storage

Any single requirement independently demands shared mutable state. Together they make it structural.

---

## Inverting the Invariant

**Make the impossible trivially satisfiable:** Eliminate all shared mutable state by making dispatch a pure functional fold.

```python
from typing import Tuple
from functools import reduce

# Events are pure data — named tuples
Event = tuple  # (type, payload)

# Each handler is a pure function: (event, state) -> (state_delta, result)
# Middleware is a pure transformer: event -> event | None (None = cancel)
# Dispatch is a fold — no shared mutable state exists inside the bus

def dispatch(
    event: Event,
    middleware: list,
    handlers: dict,
    initial_state: dict
) -> Tuple[dict, list, list]:
    
    # Middleware fold: pure event transformation
    processed = reduce(
        lambda e, mw: mw(e) if e is not None else None,
        middleware,
        event
    )
    if processed is None:
        return initial_state, [], []

    event_type, _ = processed
    relevant = handlers.get(event_type, [])

    if not relevant:
        # Dead letter is now the caller's problem — bus has no storage
        return initial_state, [], [processed]

    # Handler fold: pure state accumulation
    state = initial_state
    results, errors = [], []
    for handler in relevant:
        try:
            state_delta, result = handler(processed, state)
            state = {**state, **state_delta}
            results.append(result)
        except Exception as e:
            errors.append(e)

    return state, results, errors
```

**The new impossibility this creates:**

The pure functional design prohibits **intra-dispatch handler dependency** — handler N cannot see the *results* of handler N-1 (it can see their accumulated state delta, but not return values, and only if the fold exposes it). More critically:

1. **Stateful middleware is impossible.** Rate limiting, deduplication, request caching — all require state that persists across `dispatch` calls. That state now lives outside the bus, making the bus a pure function but pushing complexity to the caller.

2. **Dynamic event types are unsafe.** The pure design has no place to validate that a handler exists for an event type at registration time — only at call time. This makes the unhandled-event case a runtime failure mode that the caller must manage without the bus's help.

3. **Dead letters require the caller to implement them.** The bus cannot accumulate failure records; the tuple return makes failure explicit, but now every call site must decide what to do with undelivered events. The "feature" of dead letter queuing was hiding a responsibility — now that responsibility is visible and unassigned.

---

## The Conservation Law

**Original impossibility:** You cannot have an event bus with middleware, handler coordination, and observable results without shared mutable dispatch state that creates execution-order dependence and temporal coupling — invisible at the call site.

**Inverted impossibility:** You cannot have a pure functional event system without prohibiting intra-dispatch handler dependency, making dead-letter policy the caller's responsibility, and preventing stateful middleware — unless you externalize all state, which merely relocates the coupling rather than eliminating it.

### The Law

> **The information that makes handler behavior correct is always paid for exactly once. It can be encoded in the event (forcing emitters to know what handlers need), accumulated during dispatch (creating temporal coupling inside the bus), or derived from external state (coupling handlers to infrastructure outside the bus). Every event system design is a choice of where to pay — no design eliminates the cost, and the cost is always equivalent.**

### What This Reveals That a Senior Engineer Wouldn't Already Know

**1. The dead letter queue is a load-bearing tell.**

The presence of a dead letter queue in a *synchronous* event bus is a symptom that the bus has accumulated statefulness that it cannot acknowledge. A synchronous bus can return "no handlers found" as a value — it doesn't need persistent storage for it. The dead letter queue exists because someone wanted the bus to own failure responsibility. This makes the bus unsuitable for functional replacement without redesigning failure handling — but that constraint is *invisible* in the code until you try to invert the design.

**2. Middleware is a hidden API contract with no enforcement mechanism.**

Every `use(middleware_fn)` call creates an implicit ordering dependency. Middleware registered second implicitly assumes the context already has whatever the first middleware added. In the original dict-based version, this is a runtime convention. In every improved version, it remains a runtime convention with better aesthetics. The conservation law reveals that making this dependency explicit (making middleware order part of the event schema) creates a new impossibility: you cannot change middleware without changing event schema, which makes infrastructure changes into breaking API changes.

### What the Law Predicts About a Third Design

A third design — attempted by neither the original nor the functional inversion — would be a **static dependency graph**: handlers declare at registration time what context keys they read and write, and the bus validates the dependency DAG at registration, not at dispatch.

**The law predicts with precision:** This design will make dependency coupling *visible* but will create a new impossibility — **dynamic event types and dynamic handler registration become structurally prohibited.** The dependency graph can only be validated if the complete graph is known at registration time. Plugin architectures, user-defined event types, and runtime feature flags all require dynamic registration, which degrades to runtime checking — equivalent to the original problem.

Therefore: **any event system that supports both correct dependency ordering and dynamic extension will be forced to maintain some form of shared mutable runtime state.** The conservation law predicts that the third design will rediscover the original problem with better error messages, because the problem is not a design flaw — it is a property of what event systems are asked to do.
