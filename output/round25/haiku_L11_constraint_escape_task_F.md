# EventBus Structural Analysis

## Initial Falsifiable Claim

**The code's deepest structural problem: it conflates three orthogonal concerns—*deployment verification*, *execution safety*, and *operational recovery*—into a single dead-lett    -> Done (76s) -> 240 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/haiku_L11_constraint_escape_task_F.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
 queue captures both missing handlers AND exceptions indistinguishably. If I want to retry exceptions but log-and-ignore missing handlers, the structure forces me to add metadata flags or abandon the shared mechanism entirely."

**Attacker**: "You're naming symptoms. The real problem is that 'dead-letter' is semantically underspecified. Missing handlers are *deployment errors*—they happened before runtime. Exceptions are *execution failures*—they happened during runtime. Treating both as 'dead-letter' conflates a configuration concern with an operational concern. Your claim confuses type-mixing with concern-mixing."

**Prober**: "Both miss something: the code makes deployment errors *look like* runtime phenomena by treating them in emit(). This disguises a static problem as a dynamic one. That disguise is the concealment mechanism."

---

## Transformed Claim (After Expert Dialogue)

**The code conceals a category error by making deployment failures appear as runtime phenomena. It treats "no handlers registered" (a static wiring problem) as an exception case that can be recovered from (a dynamic problem), inheriting deployment concerns into operational code.**

*The gap between claims*: Original was about data model conflation; transformed is about *concern-time* conflation—which things should happen at which phase.

---

## Concealment Mechanism

The code hides its structure via **treating all failures symmetrically as runtime events**, disguising deployment errors as if they occur dynamically:

```python
if not handlers:
    self._dead_letter.append(context)  # Makes missing handlers look "normal"
```

A missing handler is *never* normal at runtime if the system is deployed correctly. By putting it in the same queue as exceptions, the code forces this into the background.

---

## Engineering a Legitimate-Looking Improvement (Deepens Concealment)

Here's an improvement a code reviewer would approve:

```python
class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter = []
        self._stats = {}  # ← NEW: Observability
        
    def emit(self, event_type, payload):
        context = {"type": event_type, "payload": payload, "cancelled": False}
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context
        
        handlers = self._handlers.get(event_type, [])
        if event_type not in self._stats:
            self._stats[event_type] = {"handlers": 0, "errors": []}
        
        # ← NEW: Explicit differentiation
        if not handlers:
            context["failure_type"] = "NO_HANDLERS"
            self._dead_letter.append(context)
            return context
            
        results = []
        for _, handler in handlers:
            try:
                results.append(handler(context))
            except Exception as e:
                context["error"] = e
                context["failure_type"] = "EXECUTION"  # ← NEW
                self._dead_letter.append(context)
                self._stats[event_type]["errors"].append(str(e))
        
        context["results"] = results
        return context
```

**Why it passes review**: Adds observability, distinguishes cases explicitly, provides monitoring.

**Why it deepens concealment**: It makes the problem *more visible* by adding flags, which means the improvement itself demonstrates that flag-based discrimination is necessary—proving the original problem wasn't just sloppy, but **structural**. The addition of flags is a red flag (pun intended) that the type system needs restructuring, not observation.

---

## Properties Revealed Only By Attempting This Improvement

1. **Boolean flags expose a type system problem.** The improvement requires `context["failure_type"]` to distinguish cases, which is exactly what you'd write if you lacked a proper union type. The improvement *recreates the symptom* it's supposed to solve.

2. **The stats structure now needs to answer "what kind of error?"** — strings like `"NO_HANDLERS"` vs. exception messages. This is a type system red flag: you're encoding what should be a discriminated union into strings.

3. **The dead_letter queue still receives heterogeneous items.** A missing handler wants to answer "which event types have no listeners?" An exception wants to answer "which handler crashed?" But they're still in the same queue. The improvement doesn't solve this; it just makes the mixing more visible by labeling it.

---

## Second Improvement (Addresses the Flag Problem)

Move to type-based distinction:

```python
from dataclasses import dataclass
from typing import Union

@dataclass
class DeploymentFailure:
    event_type: str
    payload: dict

@dataclass
class ExecutionFailure:
    event_type: str
    payload: dict
    error: Exception
    partial_results: list

class EventBus:
    def emit(self, event_type, payload) -> Union[list, DeploymentFailure, ExecutionFailure]:
        handlers = self._handlers.get(event_type, [])
        
        if not handlers:
            return DeploymentFailure(event_type, payload)  # ← TYPE, not flag
        
        results = []
        for _, handler in handlers:
            try:
                results.append(handler(context))
            except Exception as e:
                return ExecutionFailure(event_type, payload, e, results)  # ← TYPE
        
        return results
```

**But this reveals**: You've moved the problem behind types, making it less visible—but the fundamental issue persists. The dead_letter queue still mixes two different semantics. You're choosing to handle both the same way, but the *structure still conflates them*. The type system just hides this more elegantly.

---

## Structural Invariant (The Fundamental Boundary)

Through every improvement, this persists:

**The code cannot simultaneously achieve:**
1. Treating deployment failures as programming errors (fail fast, logged, not recoverable)
2. Treating execution failures as operational concerns (retryable, circuit-breakable)  
3. A single symmetric emit() interface

**This defines a category: "Event systems where all failure modes flow through one channel."** Every improvement within this category just relocates or relabels the conflation.

---

## The Adjacent Category (Escape)

What if we *separate concerns completely*—making deployment verification a distinct phase?

```python
class EventRegistry:
    """Deployment-time: verify structure."""
    def __init__(self):
        self._handlers = {}
        self._required = set()
    
    def register(self, event_type, handler, priority=0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])
    
    def require(self, event_type):
        self._required.add(event_type)
    
    def verify(self):
        """Call at APPLICATION STARTUP. Raises if incomplete."""
        missing = self._required - set(self._handlers.keys())
        if missing:
            raise DeploymentError(f"Missing handlers: {missing}")

class EventDispatcher:
    """Runtime: only execution failures possible."""
    def __init__(self, registry: EventRegistry):
        self._registry = registry  # Already verified
        self._middleware = []
    
    def emit(self, event_type, payload) -> Union[list, ExecutionFailure]:
        # Handlers guaranteed to exist (registry.verify() already ran)
        handlers = self._registry._handlers[event_type]
        
        results = []
        for _, handler in handlers:
            try:
                results.append(handler(context))
            except Exception as e:
                return ExecutionFailure(event_type, payload, e, results)
        return results

# Usage:
registry = EventRegistry()
registry.register("user.created", send_email)
registry.require("user.created")
registry.require("order.placed")
registry.verify()  # FAILS if order.placed missing—at startup, not runtime

dispatcher = EventDispatcher(registry)
result = dispatcher.emit("user.created", {})
# Result is ONLY list or ExecutionFailure, never missing handlers
```

---

## How the Escape Succeeds Where Improvements Failed

1. **Deployment failures are completely *out of the runtime path*.** emit() never handles "no handlers"—the type system proves it.

2. **The invariant dissolves.** You can now have correct error semantics AND operational recovery, because they're on different code paths.

3. **Recovery is *possible*.** Deployment failures trigger startup errors. Execution failures trigger runtime retries. They're not fighting over the same mechanism.

---

## The New Impossibility (The Trade-Off)

**Original design allowed**: Dynamic handler registration. You could emit any event type; missing handlers just went to dead-letter.

**Escape design forbids**: This entirely. All events must be declared upfront. emit("unknown.event") fails unless you registered or required it.

---

## The Finding

| Aspect | Original EventBus | EventRegistry + Dispatcher |
|--------|------|---------|
| **Allows** | Dynamic flexibility, single-path simplicity | Correct error semantics, clean concern separation |
| **Forbids** | Correct error semantics, clean separation | Dynamic flexibility, single-path simplicity |

**The key insight**: The original code *hides* this tradeoff by conflating concerns, making it feel simple while forcing manual failure discrimination. The escape *reveals* the tradeoff by separating concerns, which feels less simple (two classes, startup verification) but eliminates discriminative work and enables correct recovery strategies.

**The concealment was valuable**: dynamic flexibility. **The cost was high**: you can never build correct operational handling without leaving the framework.
