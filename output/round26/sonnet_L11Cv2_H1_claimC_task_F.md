## Three Experts on the Starting Claim

**Defender:** Priority ordering is genuinely problematic. When two handlers share a priority level, Python's stable sort preserves insertion order — but callers have no way to know this, and the API contract doesn't promise it. The invisibility is real: registering `auth_handler` before `logging_handler` with equal priority produces different behavior than the reverse, and nothing in the signature signals this.

**Attacker:** Priority is the symptom, not the disease. The EventBus conflates three incompatible models: broadcast (all handlers receive identical events), pipeline (each stage transforms output for the next), and command routing (first handler wins). The priority system looks bad because the system doesn't know what it is. If it were a pure broadcast, priority would be semantically meaningless. The hidden dependency is a consequence of an undeclared identity.

**Probe (what both take for granted):** Both experts assume the problem is *ordering*. But they ignore that `context` is simultaneously a routing instruction, a payload container, a results accumulator, and an error record. Middleware writes to it, handlers write to it, the dead letter queue stores it by reference. The real hidden dependency isn't handler ordering — it's that every participant shares an undeclared mutable communication channel that presents itself as an event payload.

---

## Claim Transformation

Priority ordering matters *because* handlers share mutable context. If each handler received an immutable snapshot, ordering would only affect result sequence, not behavior. The transformed claim:

**The deepest structural problem is that `context` is an undeclared shared communication channel. Every middleware and handler implicitly reads from and writes to a global state object, while the API presents this as event routing.**

The gap between original and transformed claim names the concealment: **priority ordering is legible; shared mutable context is invisible**. You can see priority in the `sort()` call. You cannot see context mutation without tracing every handler ever registered.

---

## Concealment Mechanism: Syntactic Flatness of Mutable Context

Dict syntax (`context["cancelled"]`, `context["error"]`) reads as data access but functions as inter-participant communication. The mechanism: **dict literals are syntactically flat** — they look like passive containers. So `context["cancelled"] = True` reads as "recording a fact" when it is actually "sending a cancellation signal to all subsequent participants." The routing metaphor (emit, handlers, dead_letter) further conceals this — the code looks like delivery, not coordination.

**Applied:** If a handler sets `context["error"] = e`, the next handler runs on a context marked with someone else's error but has no way to distinguish this from a clean context. If a handler reads `context.get("cancelled")` as a guard, it's reading a signal written by middleware via a mechanism indistinguishable from a payload field. And `self._dead_letter.append(context)` stores a live reference — if the caller mutates context after `emit()` returns, the dead letter entry changes retroactively.

---

## Improvement 1: Legitimate-Looking, Deepens Concealment

The obvious "fix" is to give each handler an isolated snapshot and accumulate results transparently:

```python
def emit(self, event_type, payload):
    context = {"type": event_type, "payload": payload, "cancelled": False}
    
    for mw in self._middleware:
        context = mw(context)
        if context.get("cancelled"):
            return context
    
    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(dict(context))  # snapshot, not live ref
        return context
    
    results = []
    errors = []
    for _, handler in handlers:
        try:
            # Each handler sees a snapshot with accumulated results visible
            handler_context = {**context, "results": list(results)}
            result = handler(handler_context)
            results.append(result)
            # Selectively merge handler mutations back (excluding structural keys)
            context.update({
                k: v for k, v in handler_context.items()
                if k not in ("type", "payload", "results", "cancelled")
            })
        except Exception as e:
            errors.append({"handler": handler.__name__, "exception": e})
            self._dead_letter.append({**context, "error_count": len(errors)})
    
    context["results"] = results
    context["errors"] = errors or None
    return context
```

**Why this passes code review:** It demonstrates awareness of the mutation problem. Isolated snapshots look defensive. Named error attribution (`handler.__name__`) looks like improved observability. Selective merge looks sophisticated rather than arbitrary.

**Three properties only visible because I tried to strengthen it:**

1. **Merge arbitration is structurally necessary.** The `context.update()` call institutes a merge policy: last handler to set a key wins. The original code's policy was identical but implicit. No implementation that allows handlers to modify context and accumulates those modifications can avoid this arbitration — the question is only whether the policy is visible. Trying to fix shared mutation reveals that merge arbitration is not an implementation choice; it's a structural requirement.

2. **Results-as-input creates a new temporal dependency.** By including accumulated results in each handler's snapshot, I made handler ordering semantically load-bearing in a new dimension: handler 2's *input state* now depends on handler 1's *output*. This is a pipeline, not a bus, but the API still says bus. The attempt to improve handler isolation accidentally created a richer dependency structure than the original.

3. **Shallow copy is invisible at the API surface.** The snapshot `{**context, ...}` copies dict structure but not nested objects. If `payload` is mutable, all handlers share the same reference. This is the mutable context problem reproduced one level down, and it's invisible in code review because the snapshot *looks* thorough. Trying to isolate handlers reveals that isolation requires specifying copy depth — which requires specifying the payload contract — which the API deliberately doesn't do.

---

## Diagnostic Applied to Improvement 1

**What it conceals:** The merge protocol (`context.update()`) is itself execution-order-dependent. Handler mutations now compete for keys, with later handlers overwriting earlier ones. The improvement relocated the ordering dependency from "which handler runs first affects execution" to "which handler runs last affects the merged context." Same conserved quantity, new hiding place.

**Property of the original visible only because the improvement recreates it:** The ordering dependency cannot be removed by making the snapshot mechanism more sophisticated. Improvement 1 demonstrates that any mechanism that (a) allows handlers to write to context and (b) accumulates those writes into a shared result must implement some arbitration policy. The original's implicit policy (last write wins) and the improvement's explicit policy (update() with key exclusions) are structurally identical. **The original's problem isn't that the merge is hidden — it's that merge arbitration is required at all.**

---

## Improvement 2: Addressing the Recreated Property

The recreated property: execution order dependency is inescapable when handlers write to shared context. Fix: handlers receive truly isolated contexts; results are collected independently; no mutations merge.

```python
import copy

def emit(self, event_type, payload):
    context = {"type": event_type, "payload": payload, "cancelled": False}
    
    for mw in self._middleware:
        context = mw(context)
        if context.get("cancelled"):
            return context
    
    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(copy.deepcopy(context))
        return context
    
    # Freeze context before handlers — no handler can affect another's input
    frozen = copy.deepcopy(context)
    results = []
    errors = []
    
    for _, handler in handlers:
        try:
            result = handler(copy.deepcopy(frozen))
            results.append(result)
        except Exception as e:
            errors.append({"handler": handler.__name__, "exception": e})
            self._dead_letter.append(copy.deepcopy(frozen))
    
    return {**context, "results": results, "errors": errors or None}
```

**Diagnostic applied to Improvement 2:**

**What it conceals:** Middleware still runs as a pipeline — each middleware sees and transforms the output of the previous one. Handlers now run as a broadcast — each receives the same frozen context. These are architecturally incompatible models coexisting in one class, now made starker because Improvement 2 fully commits to broadcast semantics for handlers. The `EventBus` is simultaneously a pipeline (middleware) and a broadcast router (handlers), and nothing in the API declares which model applies to which participant.

Additionally: `copy.deepcopy()` fails on non-copyable objects (file handles, database connections, sockets). The improvement introduces a hidden precondition that payload must be deep-copyable — invisible until runtime.

**Property of the original visible only because Improvement 2 recreates it:** By eliminating handler-to-handler coupling, Improvement 2 reveals that the original's coupling was doing real work. In the original, a handler could set `context["cancelled"] = True` to prevent subsequent handlers from running. In Improvement 2, this is impossible — handlers are isolated. The "bug" (implicit shared state) and the "feature" (inter-handler coordination) are the same mechanism. **You cannot remove the bug without removing the feature, because they are the same thing.**

---

## Structural Invariant

Through both improvements, one property persists unchanged:

**The EventBus must simultaneously support pipeline semantics (each participant sees previous participants' effects) and broadcast semantics (each participant receives the original event). These require irreconcilable execution models. No implementation within this architecture can satisfy both.**

Middleware requires pipeline semantics by definition — it's a transformation chain. Handlers, if they're to coordinate (cancellation, error propagation, result accumulation), require pipeline semantics too. But if they're to be isolated (Improvement 2), they require broadcast semantics. The `EventBus` class promises both to all participants simultaneously, and no implementation of `emit()` can deliver both without making one of them a lie.

---

## Inverting the Invariant

Make the impossible trivially satisfiable: separate the two models into explicit, first-class objects.

```python
import copy
from typing import Any, Callable, Dict, List

class EventPipeline:
    """Sequential transformer. Each stage receives the previous stage's output."""
    def __init__(self):
        self._stages: List[Callable] = []

    def pipe(self, fn: Callable) -> 'EventPipeline':
        self._stages.append(fn)
        return self

    def run(self, event: Dict) -> Dict:
        for stage in self._stages:
            event = stage(event)
            if event.get("cancelled"):
                return event
        return event


class EventBroadcast:
    """Pure broadcast. Each handler receives an identical copy of the frozen event."""
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def on(self, event_type: str, handler: Callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def emit(self, event_type: str, event: Dict) -> List[Any]:
        frozen = copy.deepcopy(event)
        return [h(copy.deepcopy(frozen)) for h in self._handlers.get(event_type, [])]


class EventBus:
    """Explicit composition of pipeline (middleware) and broadcast (handlers)."""
    def __init__(self):
        self.pipeline = EventPipeline()
        self.broadcast = EventBroadcast()

    def emit(self, event_type: str, payload: Any) -> Dict:
        event = {"type": event_type, "payload": payload, "cancelled": False}
        event = self.pipeline.run(event)
        if event.get("cancelled"):
            return event
        results = self.broadcast.emit(event_type, event)
        return {**event, "results": results}
```

The invariant is now trivially satisfiable: pipeline and broadcast are not two modes of one object but two distinct objects with explicit contracts. Callers compose them intentionally.

**New impossibility the inversion creates:**

Handlers can no longer influence subsequent processing. In the original and both improvements, a handler could — however awkwardly — write to context and affect subsequent participants. In the inverted design, handlers are pure receivers. They cannot cancel further processing, signal errors back to the routing system, or communicate with other handlers.

This eliminates saga orchestration, compensating transactions, and any pattern where receiver results must influence subsequent routing — all common real-world requirements. **Feedback from receivers to the routing system is architecturally excluded.**

The inversion has not solved the problem; it has pushed it outside the event system entirely. Callers who need inter-handler coordination must now implement it manually — at the call site, not in the bus.

---

## The Conservation Law

**Original impossibility:** Pipeline and broadcast semantics cannot coexist in one object without creating undeclared execution dependencies.

**New impossibility:** Once separated, receivers cannot provide feedback to the routing system.

**The conservation law:** *Coordination coupling between event participants is conserved. It cannot be eliminated — only relocated.*

The original code locates coordination in the shared `context` dict. Improvement 1 relocates it to the merge protocol. Improvement 2 eliminates it from handlers — which forces it to the call site. The inverted design eliminates it from the bus entirely — which forces callers to implement it themselves, typically by building a thin wrapper that passes handler results back into subsequent processing. That wrapper is the original shared-context pattern, living one abstraction layer up.

**Formal statement:** `coordination_complexity(in_bus) + coordination_complexity(at_callsite) = k`

Reducing coupling inside the bus increases the coupling burden at every call site, in equal measure.

---

## What a Senior Engineer Would Not Already Know

A senior engineer knows: shared mutable state is bad; pipeline vs. broadcast is a design choice; event buses can have priority problems.

What the conservation law reveals that they would *not* already know:

**"Decouple your handlers" is not an improvement — it is a relocation.** Senior engineers treat handler isolation as an unambiguous win. The conservation law reveals that isolation inside the bus generates equivalent coupling *outside* it, with three additional costs: more call-site code, more latency (deep copy overhead), and less visibility (coordination logic is now scattered across callers rather than localized in the bus).

**The original code's coupling is doing real work.** The shared mutable context isn't just a bug — it's an undeclared inter-participant communication protocol. `context["cancelled"] = True` is not sloppy code; it's a cancellation signal implemented by accident. When engineers fix the "bug," they delete the protocol without replacing it. The systems that depended on that protocol break silently, because nothing in the API declared the protocol existed.

The non-obvious insight: **the appropriate question is not "should handlers share state?" but "who is best positioned to implement coordination: the bus or the caller?"** The original code answers this implicitly and incorrectly for general-purpose use. The fix is not isolation — it's making the architectural choice explicit.

---

## Prediction About a Third Design

A third design will attempt: **explicit coordination via correlation IDs and reply channels.**

```python
class EventBus:
    def emit(self, event_type, payload) -> EventCorrelation:
        correlation_id = uuid4()
        # dispatch event tagged with correlation_id
        return EventCorrelation(correlation_id, self)

class EventCorrelation:
    def results(self) -> List[Any]: ...
    def cancel(self) -> None: ...
```

The conservation law predicts exactly what this design produces:

**The correlation mechanism becomes the new shared mutable context.** Handlers that need to coordinate will write state keyed by correlation ID to some shared store. That store is the `context` dict, reproduced as a database or cache. The total coordination complexity is unchanged; it now includes (a) the correlation protocol inside the bus, (b) the reply-channel matching logic, and (c) the shared store that handlers use to communicate — which is more complex, higher latency, and less visible than the original dict, while achieving identical coupling.

**The non-obvious prediction:** Any event bus architecture that achieves handler isolation will generate a parallel coordination mechanism that recreates shared mutable state at a higher level of abstraction — with more ceremony, more latency, and *less* locality than the original. The "clean" bus generates a "dirty" meta-bus as a byproduct, invisibly, in the calling code or infrastructure.

This is predictable from the conservation law: the third design doesn't reduce `k`. It partitions coordination_complexity differently — some into the correlation layer, some into the reply-channel protocol, some into whatever infrastructure handlers use to communicate indirectly. The sum is constant. The distribution changes. The sum never changes.
