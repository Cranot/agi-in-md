# EventBus Structural Analysis: Level 11 Acceptance Design

## Deepest Structural Problem (Initial Claim)

**The EventBus conflates execution control, effect observability, and handler ordering—three adversarial concerns—but provides only     -> Done (93s) -> 385 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/haiku_L11_acceptance_design_task_F.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
chitecture pretending incompatible goals are compatible.

---

## Expert Interrogation (Transformation)

**Defender:** "This is a standard event bus. Handlers register by type, emit triggers them in priority order, middleware pre-processes, dead-letter catches errors. What's the problem?"

**Attacker:** "Multiple problems. Handlers that throw break the loop mid-execution but other handlers already added their results. Dead-letter conflates 'no handlers' with 'handler crashed'—completely different failure modes mixed together. And results[3] might be None from a handler that crashed, or from a handler that successfully did nothing. How do you tell?"

**Prober:** "You're both assuming handlers have a clear semantic contract. They don't. What does a handler *mean*? If it returns None, did it handle the event? If it throws, should other handlers run? If middleware cancels, why run handlers at all? The code makes statements (handlers run if no error; all results collected; exceptions go to dead-letter) but never establishes what these statements *mean* for a caller trying to determine if their event was actually handled."

---

## The Concealment Mechanism

**Silent error accumulation with implicit success semantics via mutable context dictionary**

```python
except Exception as e:
    context["error"] = e
    self._dead_letter.append(context)
    # But loop continues — next handler doesn't know previous one failed
```

The context dict is passed through as a shared object, creating the illusion of a coherent flow. In reality:
- Middleware can cancel; handlers cannot
- Errors don't stop handler execution
- Dead-letter accepts both "no handlers found" AND "handler crashed"
- Results are collected regardless of whether execution reached them
- There's no protocol communicating what "handling" means

---

## Improvement 1: Legitimate Deepening of Concealment

```python
def emit(self, event_type, payload):
    context = {
        "type": event_type,
        "payload": payload,
        "cancelled": False,
        "handled": False,           # NEW
        "handler_metrics": {        # NEW
            "attempted": 0,
            "succeeded": 0,
            "failed": 0
        }
    }
    # ... middleware ...
    for _, handler in handlers:
        context["handler_metrics"]["attempted"] += 1
        try:
            result = handler(context)
            results.append(result)
            context["handler_metrics"]["succeeded"] += 1
            if result is not None:  # IMPLICIT: non-None = handled
                context["handled"] = True
        except Exception as e:
            context["handler_metrics"]["failed"] += 1
            context["error"] = e
            self._dead_letter.append(context)
    
    context["results"] = results
    return context
```

This **passes code review** (observability! metrics! tracking success!). It **deepens the problem** because:
- "Handled" is now defined implicitly by return value
- Metrics look meaningful but handler semantics remain undefined
- If one handler returns an int and another returns a string, which one "succeeded"?
- The true problem—lack of protocol—is now hidden under metrics

---

## Properties Visible Only Through Strengthening

By engineering this improvement, three properties emerged:

1. **Return values are semantically overloaded**: Non-None could mean "I handled it," "here's my result," "here's transformed data," or "here's a side effect identifier." The code has no commitment.

2. **Error and success are not symmetrical**: When handler throws, we record failure. When handler succeeds, we record... nothing explicit. Success is inferred from "no exception thrown."

3. **The handler contract is completely undefined**: There's no specification for what handlers *should* do, return, or declare. The system will accept anything and make implicit judgments about it.

---

## Improvement 2: Contradictory Direction

An improvement that contradicts Improvement 1:

```python
def emit(self, event_type, payload, chain_semantics="all-handlers"):
    """
    chain_semantics: "all-handlers" (run all) or "first-success" (stop at first non-error)
    Handlers MUST now return (handled: bool, data: any) tuple
    """
    handlers = self._handlers.get(event_type, [])
    results = []
    
    for _, handler in handlers:
        try:
            handled, data = handler(context)  # Explicit tuple required
            results.append(data)
            
            if chain_semantics == "first-success" and handled:
                context["stopped_at"] = handler.__name__
                break
                
        except Exception as e:
            context["error"] = e
            if chain_semantics == "first-success":
                break  # Stop propagation on error
    
    context["results"] = results
    return context
```

**The conflict is sharp**: 
- Improvement 1 = implicit success, backward-compatible, all handlers always run
- Improvement 2 = explicit success, requires rewriting all handlers, supports execution control

These cannot both be true. A handler written for Improvement 1 (returns data, assumes success) breaks under Improvement 2 (must return tuple). A handler written for Improvement 2 (returns tuple) returns nested tuples under Improvement 1.

---

## The Structural Conflict

The conflict reveals the EventBus tries to simultaneously support two incompatible event models:

| Model | Implicit Success | Execution Control | Assumption |
|-------|-----------------|-------------------|-----------|
| **Fire-and-Forget** | Yes | No | "Run all handlers, tell me what happened" |
| **First-Responder** | No | Yes | "Stop when someone handles it, tell me who" |

The priority system exists because the designer intuitively knew execution order matters—but order only matters if you have First-Responder semantics. For Fire-and-Forget, order is irrelevant. This is why the priority feature feels vestigial: it solves the wrong problem.

---

## Improvement 3: The Failed Resolution

```python
class EventBus:
    def __init__(self, model="fire-and-forget"):
        # "fire-and-forget" or "first-responder"
        self.model = model
        self._handlers = {}
    
    def emit(self, event_type, payload):
        # ... middleware ...
        handlers = self._handlers.get(event_type, [])
        results = []
        
        for _, handler in handlers:
            try:
                result = handler(context)
                results.append(result)
                
                if self.model == "first-responder":
                    if result is not None:  # Implicit: stop if handled
                        break
                        
            except Exception as e:
                self._dead_letter.append(context)
                if self.model == "first-responder":
                    break
        
        return context
```

This looks elegant—just swap the strategy. But **it fails because**:

1. **It hides the conflict, not resolves it**: You're just choosing which model to be wrong with
2. **Handler semantics still undefined**: In fire-and-forget, what return value? In first-responder, non-None means stop, but what if I want to return data AND stop, or stop AND continue?
3. **Per-handler semantics needed**: Some handlers might need fire-and-forget (logging), others need first-responder (validation). This system forces a global choice
4. **Still conflates scenarios in dead-letter**: "No handlers" and "handler crashed" still go to the same place
5. **The real problem remains**: There's still no explicit handler contract

---

## What the Failure Reveals

Improvement 3's failure exposes a fundamental topology of the design space:

**You cannot make both execution control and effect observability implicit. One must be explicit in the handler contract, or the system becomes incoherent.**

More broadly, the design space contains multiple incompatible event models that cannot coexist in one system:

1. **Fire-and-Forget**: All handlers run; no order; no feedback
2. **First-Responder**: Stop at first "success"; order critical; feedback essential
3. **Chain of Responsibility**: Each handler can pass/transform/block; requires handler protocol
4. **Publish-Subscribe**: Handlers are observers, not responders; decoupled semantics
5. **Request-Reply**: Caller expects specific answers; requires type contracts

The original code attempts to support all five by specifying none of them. This is a constraint in the problem domain, not solvable by any code improvement.

---

## The Acceptance-Based Redesign

Rather than fighting toward "one EventBus for all," accept the design space's topology:

```python
from enum import Enum
from typing import Protocol

class HandlerAction(Enum):
    CONTINUE = "continue"   # Keep running handlers
    STOP = "stop"           # I handled it; stop processing
    ERROR = "error"         # Mark as error; stop processing
    SKIP = "skip"           # Retry later

class HandlerResult:
    def __init__(self, action: HandlerAction, data=None, reason=None):
        self.action = action
        self.data = data
        self.reason = reason

class EventHandler(Protocol):
    """Explicit contract: handlers must declare their action."""
    def __call__(self, event_type: str, payload: any) -> HandlerResult:
        ...

class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._journal = {
            "completed": [],      # Event handled successfully
            "unhandled": [],      # No handlers existed
            "failed": [],         # Handler error
            "skipped": [],        # Handler skipped (retry needed)
        }

    def on(self, event_type: str, handler: EventHandler, priority: int = 0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def emit(self, event_type: str, payload: any) -> dict:
        context = {"type": event_type, "payload": payload, "cancelled": False}
        
        # Middleware can cancel
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return {"status": "cancelled", "context": context}
        
        handlers = self._handlers.get(event_type, [])
        
        # No handlers: explicit failure mode
        if not handlers:
            entry = {
                "event_type": event_type,
                "payload": payload,
                "outcome": "no_handlers"
            }
            self._journal["unhandled"].append(entry)
            return {"status": "unhandled", "context": context}
        
        results = []
        for _, handler in handlers:
            try:
                handler_result = handler(event_type, payload)
                assert isinstance(handler_result, HandlerResult), \
                    f"{handler.__name__} must return HandlerResult, got {type(handler_result)}"
                
                results.append({
                    "handler": handler.__name__,
                    "action": handler_result.action.value,
                    "data": handler_result.data,
                    "reason": handler_result.reason
                })
                
                if handler_result.action == HandlerAction.STOP:
                    self._journal["completed"].append({
                        "event_type": event_type,
                        "payload": payload,
                        "stopped_by": handler.__name__,
                        "results": results
                    })
                    return {"status": "handled", "context": context, "results": results}
                
                elif handler_result.action == HandlerAction.ERROR:
                    self._journal["failed"].append({
                        "event_type": event_type,
                        "payload": payload,
                        "failed_at": handler.__name__,
                        "reason": handler_result.reason,
                        "results": results
                    })
                    return {"status": "error", "context": context, "results": results}
                
                elif handler_result.action == HandlerAction.SKIP:
                    self._journal["skipped"].append({
                        "event_type": event_type,
                        "handler": handler.__name__,
                        "reason": handler_result.reason,
                        "results": results
                    })
                    # Continue to next handler
                    continue
                    
            except Exception as e:
                self._journal["failed"].append({
                    "event_type": event_type,
                    "payload": payload,
                    "failed_at": handler.__name__,
                    "exception": str(e),
                    "results": results
                })
                return {"status": "error", "context": context, "results": results}
        
        # All handlers ran without stopping
        self._journal["completed"].append({
            "event_type": event_type,
            "payload": payload,
            "all_handlers_completed": True,
            "results": results
        })
        return {"status": "all_handlers", "context": context, "results": results}
```

This redesign:
- **Makes the handler contract explicit**: Must return `HandlerResult` with declared action
- **Separates outcome categories**: "completed," "unhandled," "failed," "skipped" are distinct
- **Is self-documenting**: Reading the code immediately reveals what event models are supported
- **Enforces correctness**: Handler must declare action; system enforces consequences
- **Supports multiple handlers, one model**: Handlers can STOP (first-responder), CONTINUE (fire-and-forget), or SKIP (intelligent retry)

---

## What the Redesign Sacrifices

1. **Backward compatibility**: All existing handlers need rewriting to return `HandlerResult`
2. **Ease of use**: Writing a handler now requires understanding the protocol
3. **Flexibility within a model**: You must commit to this semantic model; you can't invent new ones on the fly
4. **Type inference**: Can't accept "any callable"; must be explicit `EventHandler`

---

## What Was Never Actually a Flaw

The redesign reveals several design elements that were **not flaws, but the cost of attempting the impossible**:

### 1. The Priority System
Criticized as vestigial or overengineered. In reality, it's a symptom: the designer knew order mattered, but order *only* matters with execution control semantics. Priorities exist because the original tried to support First-Responder behaviors (where ordering is critical) while maintaining Fire-and-Forget syntax (where order is irrelevant).

**Cost being paid**: Sorting overhead, false sense of determinism, prioritization debates that miss the real issue

### 2. Mutable Context Dictionary
Criticized as implicit and unsafe. In reality, it's a way to let middleware and handlers communicate without establishing explicit contracts. The problem wasn't mutation—it was that mutation happened in service of undefined semantics.

**Cost being paid**: Silent side effects, debugging difficulty, implicit contracts no one reads

### 3. Silent Error Handling
Criticized as hiding failures. In reality, it's a deliberate fault-tolerance choice: let other handlers run even if one crashes. This is legitimate for Fire-and-Forget systems but breaks First-Responder systems.

**Cost being paid**: Unclear recovery guarantees, conflated failure modes (no handlers vs handler crash), impossible to distinguish "successfully did nothing" from "failed then recovered"

### 4. Dead-Letter Conflation
Criticized as mixing concerns (unhandled events with handler errors). In reality, it's what happens when you don't commit to a semantic model. If you don't distinguish between "nobody was able to handle this" and "somebody tried but failed," they end up in the same place.

**Cost being paid**: Opaque failure diagnostics, inability to retry intelligently, mixing transient and permanent failures

---

## The Final Diagnosis

**The deepest structural problem**: The EventBus provides no explicit semantics for what "handling" means. It hides this by using mutable context and implicit success assumptions, making it impossible for callers or handlers to establish a reliable protocol.

**The concealment mechanism**: Silent error accumulation + implicit context mutation + undefined return-value semantics

**What attempting to improve it revealed**: There are fundamentally incompatible event models (Fire-and-Forget vs First-Responder), and this code tries to support both by fully supporting neither.

**What the failed resolutions taught us**: The problem is not solvable by code improvements; it's solvable only by accepting a constraint in the problem domain and designing explicitly for one model (while documenting why others aren't supported).

**What was never a flaw**: Everything that looked like poor design was actually the cost of attempting an impossible goal. The priority system, context mutation, silent error handling, and dead-letter mixing all exist because the code was trying to be "everything to everyone." Once you accept the design space's topology, these problems evaporate—not because they're solved, but because they were never the problem.
