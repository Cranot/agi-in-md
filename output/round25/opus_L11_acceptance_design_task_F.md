# Structural Analysis of EventBus

## The Claim

**The deepest structural problem:** The `context` dict serves simultaneously as the transport between middleware stages (pipeline semantics: shared, transformative), the dispatch payload to ha    -> Done (164s) -> 325 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/opus_L11_acceptance_design_task_F.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
 the *same dict* that now carries handler 3's error. Sibling handlers pollute each other.

**Attacker:** This is shallow. The dict is a *symptom*. The real problem is the code conflates two execution models — **pipeline** (middleware: sequential, each stage transforms for the next) and **broadcast** (handlers: fan-out, each should see the same event). The context dict is ugly because it's the data structure for both models simultaneously, and those models have contradictory mutation semantics.

**Prober:** You both assume the code *should* separate these. But what if the conflation is intentional — middleware influencing handlers, handlers influencing each other? The real problem neither of you names: **the code has no lifecycle model.** There's no concept of "an emission" as a bounded entity with distinct phases. The context dict isn't a god-object — it's the *scar tissue over the missing lifecycle.*

### Transformed Claim

The deepest structural problem is the **absence of an emission lifecycle**: the code treats emission as a single procedural pass through a flat sequence, when it actually needs to model distinct phases (transformation, dispatch, error resolution) with different mutation contracts per phase.

### The Diagnostic Gap

My original claim targeted a *data structure* (the dict). The transformed claim targets a *missing abstraction* (emission-as-lifecycle). I mistook the symptom for the disease. This is characteristic of code whose real problem is an **absent concept**, not a present defect.

---

## The Concealment Mechanism

**Name: "Procedural Plausibility."**

The code reads cleanly top-to-bottom. Each line is locally reasonable. The `for mw in self._middleware` loop looks like a proper chain. The `for _, handler in handlers` loop looks like clean dispatch. **Sequential readability disguises semantic incoherence** — the code *looks* like it has a model (middleware → dispatch → results) because it has a *sequence*. But sequence is not model.

---

## First Improvement: Deepens the Concealment

Extract named phases — pure refactoring that would sail through review:

```python
def emit(self, event_type, payload):
    context = {"type": event_type, "payload": payload, "cancelled": False}

    # Phase 1: Middleware pipeline
    context = self._apply_middleware(context)
    if context.get("cancelled"):
        return context

    # Phase 2: Handler dispatch
    return self._dispatch_to_handlers(event_type, context)

def _apply_middleware(self, context):
    for mw in self._middleware:
        context = mw(context)
        if context.get("cancelled"):
            break
    return context

def _dispatch_to_handlers(self, event_type, context):
    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(context)
        return context
    results = []
    for _, handler in handlers:
        try:
            results.append(handler(context))
        except Exception as e:
            context["error"] = e
            self._dead_letter.append(context)
    context["results"] = results
    return context
```

**Review comment:** *"Refactored emit into named phases for readability."* ✓ Approved.

**Why it deepens concealment:** It now *looks* like it has a lifecycle model — "Phase 1," "Phase 2," named methods suggesting bounded phases. But nothing actually separates the phases. The same mutable dict flows through. The method boundaries are cosmetic, not semantic. Worse: the named methods make it *harder* to notice the phases aren't actually bounded.

### Three Properties Visible Only Because I Tried to Strengthen Concealment

1. **Phase boundaries are illusory.** Extracting methods reveals there's nothing that *separates* phases — no snapshot, no copy, no seal. The refactoring makes this invisible by making it look like separation exists.

2. **Error bleed is cross-phase.** When `_dispatch_to_handlers` sets `context["error"]`, it mutates the same object middleware produced. The method extraction hides that error handling belongs to no phase — it's a side-effect stuffed into the transport.

3. **Dead letter has dual identity.** `_dead_letter` receives both "no handlers registered" (a routing failure) and "handler threw exception" (an execution failure) — two fundamentally different failure modes now buried together inside `_dispatch_to_handlers`, making the conflation harder to spot.

---

## Second Improvement: Contradicts the First

Isolate handler contexts — strengthening what the first weakened:

```python
def _dispatch_to_handlers(self, event_type, context):
    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(context)
        return context
    results = []
    errors = []
    for _, handler in handlers:
        handler_ctx = {**context}  # isolated copy per handler
        try:
            results.append(handler(handler_ctx))
        except Exception as e:
            errors.append({"handler": handler, "error": e})
    context["results"] = results
    if errors:
        context["errors"] = errors
        for err in errors:
            self._dead_letter.append(err)
    return context
```

**Review comment:** *"Isolate handler contexts so one handler's mutation doesn't affect siblings."* ✓ Approved.

### The Structural Conflict

Both improvements are independently legitimate. But they contradict:

- **Improvement 1** says: *"Context flows through phases"* — a **pipeline** that values the shared transformation chain.
- **Improvement 2** says: *"Context forks at dispatch"* — a **broadcast** that values handler isolation.

The conflict: **a single data structure cannot be simultaneously shared-and-transformed (pipeline) and copied-and-isolated (broadcast)**. Both are needed. Middleware genuinely requires pipeline semantics (each middleware sees the previous one's changes). Handlers genuinely require broadcast semantics (each gets the same pristine event). Both pass review because both needs are real.

---

## Third Improvement: Resolves the Conflict

Introduce an explicit phase transition — `freeze` — where the context shifts from pipeline to broadcast semantics:

```python
import copy

class EmissionContext:
    def __init__(self, event_type, payload):
        self.type = event_type
        self.payload = payload
        self.cancelled = False
        self._frozen = None

    def freeze(self):
        self._frozen = copy.deepcopy(self.payload)

    def handler_view(self):
        return {"type": self.type, "payload": copy.deepcopy(self._frozen)}

class EventBus:
    # ... (on, use unchanged) ...

    def emit(self, event_type, payload):
        ctx = EmissionContext(event_type, payload)

        # Pipeline phase: middleware transforms shared state
        for mw in self._middleware:
            mw(ctx)
            if ctx.cancelled:
                return ctx

        # Phase transition
        ctx.freeze()

        # Broadcast phase: handlers receive isolated views
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(ctx)
            return ctx

        results = []
        for _, handler in handlers:
            try:
                results.append(handler(ctx.handler_view()))
            except Exception as e:
                self._dead_letter.append({"context": ctx, "error": e})

        ctx.results = results
        return ctx
```

**Review comment:** *"Typed context with explicit phase transition. Middleware gets mutable access, handlers get isolated views."* ✓ Approved.

### How It Fails

It creates a **one-way valve**. Information flows from middleware into handlers but never back:

1. **Handlers can't cascade.** A handler receiving a frozen view has no reference to the bus. It can't emit sub-events.
2. **Handlers can't signal.** "I handled this, others should skip" is impossible — isolation prevents cross-handler communication.
3. **Results re-introduce shared mutation.** `ctx.results = results` writes back onto the shared context *after* the freeze, violating the very model the freeze established.
4. **Middleware can't react to handler outcomes.** There's no "post-dispatch" phase. Middleware that needs to log results, retry on failure, or clean up resources has no hook.

### What the Failure Reveals

The conflict alone showed: *pipeline and broadcast need different mutation semantics.*

The failure of the resolution reveals something the conflict could not: **there are no separable phases.** The need for bidirectional flow — handlers informing the system, triggering cascades, influencing each other — means the emission lifecycle cannot be decomposed into sequential phases with distinct contracts. The design space is not a line (pipeline → freeze → broadcast). It's a **cycle**: participants both produce and consume mutations, and any model that commits to a direction (upstream → downstream) will fail at the boundary where information must flow back.

---

## Fourth Construction: The Acceptance Redesign

Stop fighting the topology. Accept: **events are immutable, participants are uniform, communication happens through new emissions, not context mutation.**

```python
import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


class Event:
    """Immutable once created. The payload is snapshot at emission time."""
    __slots__ = ('type', 'payload')

    def __init__(self, event_type: str, payload: Any):
        self.type = event_type
        self.payload = copy.deepcopy(payload)


class Propagation:
    """Per-subscriber control surface. Scoped, not shared."""
    def __init__(self, bus: 'EventBus', event: Event):
        self._bus = bus
        self.event = event
        self._stopped = False

    def stop(self):
        """Absorb the event. Lower-priority subscribers won't see it."""
        self._stopped = True

    @property
    def stopped(self) -> bool:
        return self._stopped

    def emit(self, event_type: str, payload: Any):
        """The ONLY way handlers communicate: by emitting new events."""
        self._bus._defer(event_type, payload)


@dataclass
class EmissionResult:
    event: Event
    results: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def handled(self) -> bool:
        return bool(self.results)


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[tuple[int, Callable]]] = {}
        self._unhandled: list[Event] = []
        self._depth: int = 0
        self._deferred: list[Event] = []

    def on(self, event_type: str, handler: Callable, priority: int = 0):
        subs = self._subscribers.setdefault(event_type, [])
        subs.append((priority, handler))
        subs.sort(key=lambda x: -x[0])

    def emit(self, event_type: str, payload: Any) -> EmissionResult:
        event = Event(event_type, payload)
        is_root = self._depth == 0
        self._depth += 1

        try:
            result = self._deliver(event)

            # Only the root emission drains deferred events
            if is_root:
                while self._deferred:
                    deferred = self._deferred.pop(0)
                    self._deliver(deferred)

            return result
        finally:
            self._depth -= 1

    def _defer(self, event_type: str, payload: Any):
        self._deferred.append(Event(event_type, payload))

    def _deliver(self, event: Event) -> EmissionResult:
        subscribers = self._subscribers.get(event.type, [])

        if not subscribers:
            self._unhandled.append(event)
            return EmissionResult(event)

        result = EmissionResult(event)

        for _, handler in subscribers:
            prop = Propagation(self, event)
            try:
                ret = handler(prop)
                if ret is not None:
                    result.results.append(ret)
            except Exception as e:
                result.errors.append((handler, e))

            if prop.stopped:
                break

        return result
```

No middleware. No context dict. No phases. The design accepts five structural decisions:

| Original concept | Redesign equivalent |
|---|---|
| Middleware chain | High-priority subscribers that call `prop.stop()` |
| Context mutation | Impossible. `Event` is immutable, `Propagation` is per-subscriber |
| Handler-to-handler communication | `prop.emit()` — deferred new event, drained after current delivery |
| Dead letter queue | `_unhandled` — only for routing failures, not execution errors |
| Shared mutable results | `EmissionResult` — constructed *after* delivery, never seen by handlers |

### What It Sacrifices

**Middleware-as-transformation.** In the original, a middleware could do `context["payload"]["user"] = enrich(context["payload"]["user"])` and every handler would see the enriched version. In the redesign, a high-priority subscriber would need to `prop.stop()` the original event and `prop.emit("user.loaded", enriched_payload)` — forcing all downstream subscribers to listen to the *new* event type. This is more verbose, less ergonomic, and requires subscribers to know the enrichment topology.

**Implicit shared context as coordination.** Handlers can no longer "leave notes" for each other on the context. All coordination is explicit: new events with new types.

### What Was Never a Flaw

The original design's **shared mutable context was never a flaw**. It was the **cost of attempting the impossible**: supporting pipeline, broadcast, and conversation semantics simultaneously through a single mechanism. The mutability wasn't sloppiness — it was *load-bearing*. It was the minimum price of the aspiration to let middleware transform for handlers, handlers see results from siblings, and errors propagate through the same channel as data.

The redesign, by accepting immutable events and uniform subscribers, reveals that the original's context dict was doing the only thing a single data structure *can* do when asked to serve three contradictory roles: be mutable and shared and hope for the best. Calling it a "god object" was misidentifying a structural necessity as a defect. The redesign doesn't fix the original. It *retreats to a smaller ambition* — and the gap between the two ambitions is exactly the space the mutable context was trying to inhabit.
