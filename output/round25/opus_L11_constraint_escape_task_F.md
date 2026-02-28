# Structural Diagnosis of the EventBus

## The Falsifiable Claim

**The deepest structural problem is that a single mutable `dict` (`context`) serves simultaneously as message, control-flow signal, error record, and result accumulator, creat    -> Done (105s) -> 176 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/opus_L11_constraint_escape_task_F.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
 no `off()`, no subscription handle, `_handlers` grows monotonically, priority re-sorts on every `on()`. The shared-mutation problem wouldn't matter if subscriptions were bounded and controllable.

**Prober:** Both of you assume the EventBus is a long-lived coordination object. But look at what happens *within a single `emit` call*: a handler exception writes `context["error"]`, appends the *same* `context` reference to `_dead_letter`, then execution **continues** — the next handler sees the error from the previous one. And only the *last* error survives because each overwrites the key. The mutable dict isn't a poor choice of container. It's that **there are no boundaries within a single emit call's lifecycle**.

### Transformed Claim

A single mutable dict flows through an uncontrolled pipeline where every participant can observe and corrupt every other participant's state through shared mutation, **and no phase boundaries prevent cross-stage contamination**.

### The Gap (Diagnostic)

My original instinct targeted macro-architecture (topology vs. execution). The real problem lives in the micro-structure — how data flows *within one method call*. The code's ~30-line brevity actively conceals this.

---

## The Concealment Mechanism

**Name: "Simplicity theater through dictionary polymorphism."**

The `dict` is a universal joint — it accepts any key, so the code never declares what `context` *is*. Four incompatible roles (message, signal, error, results) are never named, only implied by runtime key access. The code *looks* clean because the complexity is hidden in the protocol between stages, which exists nowhere in the source.

---

## Improvement #1: Legitimize the Shape

A code-review-passing "type safety" improvement that **deepens** concealment:

```python
from dataclasses import dataclass, field
from typing import Any, List, Optional

@dataclass
class EventContext:
    event_type: str
    payload: Any
    cancelled: bool = False
    error: Optional[Exception] = None
    results: List[Any] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)   # escape hatch
```

This *passes review* ("we added types!") but **deepens** concealment because it makes the single-object-multiple-roles problem look *intentional and designed* rather than accidental. The `metadata` dict preserves the original polymorphism problem entirely.

### Three Properties Visible Only Because I Tried to Strengthen

1. **Temporal aliasing** — `results` as a field reveals handler N+1 can see handler N's result during iteration, creating invisible ordering dependencies.
2. **Error non-isolation** — `error` as a single field reveals only the *last* exception survives; each overwrites the previous, yet every dead-letter entry is the same mutating object reference.
3. **Phase confusion** — `cancelled` alongside `results` reveals nothing prevents a *handler* from setting `cancelled=True`; the field exists on the object handlers receive, but it was meant for middleware only.

---

## Recursive Diagnostic on Improvement #1

**What it conceals:** The object is simultaneously `MiddlewareInput`, `HandlerInput`, `ErrorRecord`, and `DeadLetterEntry`. The dataclass makes this look like a coherent type.

**What it recreates from the original:** The single-object-as-universal-joint pattern persists. Dict became dataclass, but one mutable object still flows through the entire pipeline accumulating state.

---

## Improvement #2: Split by Phase

```python
@dataclass(frozen=True)
class Event:
    event_type: str
    payload: Any

@dataclass
class MiddlewareVerdict:
    event: Event
    cancelled: bool = False

@dataclass
class EmitResult:
    event: Event
    results: List[Any] = field(default_factory=list)
    errors: List[Exception] = field(default_factory=list)
    dead_lettered: bool = False
```

Now `emit` creates an immutable `Event`, middleware returns `MiddlewareVerdict`, handlers contribute to `EmitResult`. No shared mutable object crosses a phase boundary.

### Recursive Diagnostic on Improvement #2

**What it conceals:** The `emit` *method body* still owns the entire pipeline — it orchestrates middleware, dispatch, error handling, and result aggregation in a single synchronous control flow. The types are separate, but every policy decision is still fused into one method.

**What it recreates:** The locus-of-all-policy-decisions problem. We've separated the *data* by phase but the *control flow* remains monolithic.

---

## The Structural Invariant

> **Synchronous orchestration coupling:** In any synchronous EventBus where `emit()` returns a result, the emit method must encode the composition of middleware, dispatch, error, and aggregation policy as a single control flow — because the caller is blocking for a complete answer.

This persists through every improvement because it is a property of the **call-and-return execution model**, not the implementation.

---

## The Category Boundary

This invariant defines the category: **synchronous, return-value-bearing event dispatch.**

All designs in this category must fuse policies at a single orchestration point, because `result = bus.emit(...)` demands a complete, composed answer before the caller can proceed.

---

## The Adjacent Category: Declarative Reactive Pipelines

Where the invariant *dissolves*:

```python
class ReactiveBus:
    def __init__(self):
        self._pipelines = {}

    def pipeline(self, event_type):
        """Declare a pipeline as a topology of stages, not a sequence of steps."""
        p = Pipeline()
        self._pipelines[event_type] = p
        return p

    def emit(self, event_type, payload):
        """Fire-and-forget. Returns a handle, not results."""
        p = self._pipelines.get(event_type)
        if p is None:
            return self._dead_letter(event_type, payload)
        return p.submit(Event(event_type, payload))  # -> Future | None

class Pipeline:
    def middleware(self, fn):  ...  # stage with own input/output contract
    def handle(self, fn):      ...  # stage
    def on_error(self, fn):    ...  # independent error policy
    def on_dead_letter(self, fn): ...
```

**Why this succeeds where every improvement failed:**
- `emit` no longer orchestrates — it delegates to a pre-declared pipeline topology
- Error policy, dispatch, and aggregation are declared as *independent stages*, not coded into one method
- Each stage has its own input/output types — the universal-joint context has no reason to exist
- The pipeline topology is *data* (inspectable, composable) not *code* (a method body)

---

## The New Impossibility

**Synchronous result availability.** In the original category, this is trivial:

```python
result = bus.emit("validate", data)
if result["error"]:  # immediately available
    rollback()
```

In the reactive category, this is **impossible**. Results arrive asynchronously. Every caller that depends on `emit` returning handler results must be restructured into a callback or `await`.

---

## The Finding

| | Original Category (Sync EventBus) | Adjacent Category (Reactive Pipeline) |
|---|---|---|
| **Trivial** | Immediate result access from `emit` | Independent error/dispatch/aggregation policy |
| **Impossible** | Independent policies (fused by synchronous orchestration) | Immediate result access (results arrive later) |

**The EventBus's problems are not bugs — they are consequences of the synchronous-return contract.** Every improvement within the category rearranges which symptom is most visible while the structural invariant holds. Escaping to the reactive category dissolves the orchestration coupling but sacrifices the call-return simplicity that made `emit()` attractive. The "right" design is determined by whether your *callers* can tolerate asynchronous result delivery — a constraint that lives entirely outside this code.
