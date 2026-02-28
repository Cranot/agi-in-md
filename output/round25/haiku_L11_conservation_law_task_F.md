# Structure First Analysis: EventBus

## Initial Falsifiable Claim

**DEEPEST STRUCTURAL PROBLEM:**  
This EventBus exhibits **"observability collapse"** — it cannot distinguish between:
- (a) An event having genuinely no handlers (archite    -> Done (102s) -> 510 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/haiku_L11_conservation_law_task_F.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
."

**ATTACKER:** "Wrong level. The real problem is synchronous execution bottleneck. One slow handler blocks all events. You're treating observability as fundamental when the system is architecturally unscalable. Dead letter semantics are secondary."

**PROBER:** "Both assume 'events have a single truth value.' But the code doesn't preserve that — handler A succeeds, handler B fails, handler C doesn't exist. You've been arguing about a binary outcome when the structure *manages a multiplicity*. The real concealment: **the system forces every event into a binary fate despite handling multiple independent causalities.**"

---

## Transformed Claim (Synthesis)

**This EventBus exhibits "single-point-of-collapse semantics" — it forces every event into a binary outcome (dead-letter or implicit success) despite managing a multiplicity of independent handler states.**

---

## Concealment Mechanism: "Outward Simplicity Through Inward Degradation"

The `emit()` signature looks clean:
```python
emit(event_type, payload) → context
```

What it hides:
- Middleware silently modifies state
- Handlers produce partial successes
- Failures only recorded if they're exceptions (not error values)
- Dead letter conflates "no handlers" + "failures" into garbage collection

**The code achieves simplicity by refusing to represent the complexity it contains.**

---

## Deepening Improvement (Legitimate-Looking, Hiding More)

```python
class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter = []
        self._event_stats = {}  # ← LOOKS LIKE OBSERVABILITY FIX
        self._execution_log = {}  # ← LOOKS LIKE TRANSPARENCY

    def on(self, event_type, handler, priority=0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
            self._event_stats[event_type] = {"registered": 0, "executed": 0, "failed": 0}
        self._handlers[event_type].append((priority, handler))
        self._event_stats[event_type]["registered"] += 1
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def emit(self, event_type, payload):
        context = {"type": event_type, "payload": payload, "cancelled": False, 
                   "id": uuid4()}  # ← LOOKS LIKE TRACEABILITY
        
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context
        
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(context)
            self._execution_log[context["id"]] = {"status": "unhandled"}
            return context
        
        execution_record = {"handlers": []}
        for _, handler in handlers:
            try:
                result = handler(context)
                execution_record["handlers"].append({"success": True, "result": result})
                self._event_stats[event_type]["executed"] += 1
            except Exception as e:
                execution_record["handlers"].append({"success": False, "error": str(e)})
                self._event_stats[event_type]["failed"] += 1
                self._dead_letter.append(context)  # ← STILL PREMATURE
        
        self._execution_log[context["id"]] = execution_record
        context["execution"] = execution_record
        return context
    
    def get_event_metrics(self, event_type):
        return self._event_stats.get(event_type, {})
```

**Why code review approves this:**  
✓ Adds traceability (UUID)  
✓ Records execution details  
✓ Provides metrics endpoint  
✓ Looks "more observable"

**Why it deepens the concealment:**  
The execution log is *post-hoc and aggregate*. An event in `_dead_letter` now has matching entries in `_execution_log` showing which handlers succeeded and which failed. **This creates the illusion that failure is now transparent** — reviewers see metrics + detailed logs and assume the problem is solved.

But the fundamental conflation persists: a dead-lettered event could mean "no handlers" or "handler 1 succeeded and handler 2 failed." The new improvement just adds more granular bookkeeping on top of the same semantic confusion.

---

## Three Properties Visible Only Through This Attempt

**1. The Observer Effect Property:**  
Statistics are *computed from exceptions*, not intrinsic to event state. A handler returning `{"status": "error"}` is counted as "executed" not "failed." The metrics can be systematically wrong while the execution log appears detailed.

**2. The Causality Inversion Property:**  
The system records *effects* (which handlers threw) and infers *causes* (therefore "failed"). But handler B's success doesn't tell you why handler C failed. You're measuring outcomes and pretending they constitute explanation.

**3. The Bundling Trap Property:**  
By adding `execution_record["handlers"]`, we expose the original problem even more sharply: an event *can* have mixed outcomes (handler A success, handler B failure) but the system still bundles it into dead letter. The improvement reveals that **adding more detailed records doesn't solve the fundamental inability to represent partial success**.

---

## Diagnostic Applied to Improvement: What It Recreates

**What the improvement conceals:**  
That the fundamental problem is *semantic* (how do we represent ambiguous outcomes?), not *observational* (can we see what happened?).

**What property re-emerges:**  
The question: "Did this event succeed?" still has no single answer. An event with `handlers: [{"success": true}, {"success": false}]` is both succeeded and failed. The detailed execution log makes this more *obvious*, but the system's architecture still can't *represent* it coherently.

---

## Second Improvement: Addressing the Multiplicity

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class HandlerOutcome:
    handler_name: str
    succeeded: bool
    result: any = None
    error: Exception = None

@dataclass  
class EventResult:
    event_id: str
    event_type: str
    payload: any
    outcomes: List[HandlerOutcome]
    middleware_cancelled: bool = False
    
    @property
    def fully_successful(self):
        return not self.middleware_cancelled and all(o.succeeded for o in self.outcomes)
    
    @property
    def has_partial_failure(self):
        return any(not o.succeeded for o in self.outcomes) and any(o.succeeded for o in self.outcomes)
    
    @property
    def fully_failed(self):
        return any(o.succeeded for o in self.outcomes) and not all(o.succeeded for o in self.outcomes)
    
    @property
    def is_unhandled(self):
        return len(self.outcomes) == 0 and not self.middleware_cancelled

class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._results = {}  # ← Store IMMUTABLE result objects, not mutable dead letter

    def on(self, event_type, handler, priority=0, name=None):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        handler_name = name or handler.__name__
        self._handlers[event_type].append((priority, handler, handler_name))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type, payload):
        event_id = str(uuid4())
        context = {"type": event_type, "payload": payload, "cancelled": False, "id": event_id}
        
        # Middleware phase
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                result = EventResult(
                    event_id=event_id,
                    event_type=event_type,
                    payload=payload,
                    outcomes=[],
                    middleware_cancelled=True
                )
                self._results[event_id] = result
                return result
        
        # Handler phase
        handlers = self._handlers.get(event_type, [])
        outcomes = []
        
        for _, handler, handler_name in handlers:
            try:
                handler_result = handler(context)
                outcomes.append(HandlerOutcome(
                    handler_name=handler_name,
                    succeeded=True,
                    result=handler_result
                ))
            except Exception as e:
                outcomes.append(HandlerOutcome(
                    handler_name=handler_name,
                    succeeded=False,
                    error=e
                ))
        
        # ← KEY DIFFERENCE: Single immutable result object
        result = EventResult(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            outcomes=outcomes
        )
        self._results[event_id] = result
        return result
    
    def get_result(self, event_id):
        return self._results.get(event_id)
```

**Why this addresses the multiplicity:**  
Now `EventResult` explicitly represents:
- Events with no handlers
- Events with partial successes  
- Events with complete failures
- Events with complete successes

Each is a distinct state, not conflated into dead letter.

---

## Diagnostic Applied to Second Improvement: New Concealment

**What it reveals:**  
The question "did this event succeed?" now has *three* answers (partial/full/none) instead of one binary answer.

**What new problem it recreates:**  
**Causality ordering**: The result object is built *after all handlers complete*. But in the original code, handlers were added to dead letter *on first failure*. This matters because:

```python
handlers = [A, B, C]
# Original: If A fails, event dead-lettered immediately
# Improved: All three execute, then result computed

# But what if:
# - A fails at time T1
# - B is waiting on result of A (implicit dependency)
# - B would fail if A failed, but succeeds if A succeeded
```

The improvement reveals that **the code structure forces premature result computation when exceptions interrupt the handler sequence**. We still can't represent "handler B depends on handler A" without external coordination.

---

## Structural Invariant (Through All Versions)

**INVARIANT: "An event's semantic truth must be derived from a multiplicity of handler outcomes, but the system architecture forces this derivation to happen before all outcomes are observed."**

- Original: Dead letter on first exception (compute before all handlers run)
- Improved 1: Add detailed logs (still dead letter on first exception)
- Improved 2: Create immutable result (compute after all handlers, but can't express dependencies)

Every version:
1. Has multiple handlers  
2. Needs a single answer ("was this successful?")  
3. Can't wait for full observation without losing something else (speed? responsiveness? clarity?)

---

## Invert the Invariant

**Original invariant:**  
"Event truth must be derived from handler multiplicity before the full multiplicity is observed"

**INVERTED:**  
"Event truth is never derived from handler outcomes. Instead, each event and each outcome are immutable facts. Truth is only constructed on query, never stored."

```python
import time

class Event:
    """An event is an immutable fact."""
    def __init__(self, event_id, event_type, payload, timestamp):
        self.id = event_id
        self.type = event_type
        self.payload = payload
        self.timestamp = timestamp

class HandlerExecution:
    """Each handler execution is a separate immutable fact."""
    def __init__(self, event_id, handler_name, succeeded, result=None, error=None, timestamp=None):
        self.event_id = event_id
        self.handler_name = handler_name
        self.succeeded = succeeded
        self.result = result
        self.error = error
        self.timestamp = timestamp or time.time()

class EventLog:
    """Not an EventBus. A log that records facts, not states."""
    def __init__(self):
        self._events = []  # immutable event facts
        self._executions = []  # immutable execution facts
        self._handlers = {}
        self._middleware = []

    def on(self, event_type, handler, priority=0, name=None):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        handler_name = name or handler.__name__
        self._handlers[event_type].append((priority, handler, handler_name))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type, payload):
        """Emit: record the event as an immutable fact."""
        event = Event(
            event_id=str(uuid4()),
            event_type=event_type,
            payload=payload,
            timestamp=time.time()
        )
        self._events.append(event)
        
        # Middleware processing
        context = {"id": event.id, "type": event.type, "payload": event.payload, "cancelled": False}
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                # Cancellation is a fact too
                self._executions.append(HandlerExecution(
                    event_id=event.id,
                    handler_name="<middleware>",
                    succeeded=False,
                    error="cancelled"
                ))
                return event
        
        # Handler execution: each execution is a separate fact
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._executions.append(HandlerExecution(
                event_id=event.id,
                handler_name="<none>",
                succeeded=False,
                error="no_handlers_registered"
            ))
            return event
        
        for _, handler, handler_name in handlers:
            try:
                result = handler(context)
                self._executions.append(HandlerExecution(
                    event_id=event.id,
                    handler_name=handler_name,
                    succeeded=True,
                    result=result
                ))
            except Exception as e:
                self._executions.append(HandlerExecution(
                    event_id=event.id,
                    handler_name=handler_name,
                    succeeded=False,
                    error=e
                ))
        
        return event
    
    def query_event(self, event_id):
        """Query 1: Get the event fact itself."""
        return next((e for e in self._events if e.id == event_id), None)
    
    def query_executions(self, event_id):
        """Query 2: Get all execution facts for an event."""
        return [e for e in self._executions if e.event_id == event_id]
    
    def query_handler_success_rate(self, handler_name, since_timestamp=None):
        """Query 3: Aggregate facts to compute derived insights."""
        relevant = [e for e in self._executions if e.handler_name == handler_name]
        if since_timestamp:
            relevant = [e for e in relevant if e.timestamp >= since_timestamp]
        if not relevant:
            return None
        successes = sum(1 for e in relevant if e.succeeded)
        return successes / len(relevant)
    
    def query_event_outcome(self, event_id):
        """Query 4: Construct event truth from execution facts.
        Note: This is derived, never stored."""
        executions = self.query_executions(event_id)
        if not executions:
            return {"event_id": event_id, "status": "unknown"}
        
        no_handlers = any(e.handler_name == "<none>" for e in executions)
        cancelled = any(e.handler_name == "<middleware>" for e in executions)
        handler_execs = [e for e in executions if e.handler_name not in ("<none>", "<middleware>")]
        
        if cancelled:
            return {"event_id": event_id, "status": "cancelled"}
        if no_handlers:
            return {"event_id": event_id, "status": "unhandled"}
        
        successes = [e for e in handler_execs if e.succeeded]
        failures = [e for e in handler_execs if not e.succeeded]
        
        if not failures:
            return {"event_id": event_id, "status": "fully_successful", "handlers": len(successes)}
        if not successes:
            return {"event_id": event_id, "status": "fully_failed", "handlers": len(failures)}
        
        return {
            "event_id": event_id,
            "status": "partially_successful",
            "successful_handlers": [e.handler_name for e in successes],
            "failed_handlers": [e.handler_name for e in failures]
        }
```

**Why this inverts the problem:**

| Original EventBus | Inverted EventLog |
|---|---|
| Tries to compute event state during execution | Never computes event state; only records facts |
| Loses information (dead letter bundles multiple causes) | Preserves all information (facts are immutable) |
| Fast: state is stored | Slower: state is derived on query |
| Answers "what happened?" at emit time | Answers "what happened?" whenever you ask |

**The inversion makes trivially satisfiable:**  
Representing multiple incompatible handler outcomes — just record each as a separate fact.

---

## New Impossibility Created by Inversion

**CRITICAL NEW PROBLEM: "In an immutable event log with separate execution facts, you cannot prevent handler re-execution across system failures without an external transaction coordinator."**

Why:
1. Event recorded to log
2. Handler executed
3. Execution recorded to log
4. System crashes at step 2.5
5. On restart: event is in log, but execution isn't recorded
6. Handler executes again

The original EventBus avoided this: the handler and the event were bundled. The inverted EventLog separates them.

---

## Conservation Law of Event Semantics

**When transforming from EventBus → EventLog:**

| Dimension | EventBus | EventLog |
|---|---|---|
| **Single definite truth value per event** | ✓ (binary) | ✗ (derived on query) |
| **Complete historical visibility** | ✗ (hidden in dead letter) | ✓ (all facts preserved) |
| **Handler idempotency across failures** | ✓ (bundled execution) | ✗ (split facts) |
| **Decoupled handler code** | ✗ (handlers see mutable context) | ✓ (handlers are pure) |

**THE CONSERVATION LAW:**

*In event-driven systems, you cannot simultaneously optimize for:*
1. *Determinate semantic answers ("did it succeed?")*
2. *Historical transparency ("what happened?")*
3. *Idempotent replay safety ("handlers won't run twice")*
4. *Decoupled handler logic ("handlers are pure functions")*

*Each architectural choice trades three properties against the fourth.*

**Specifically: The impossibility that was hidden (conflation of "no handlers" vs "all failed") becomes visible (conflation of "handler didn't record outcome" vs "handler didn't execute") when you try to fix the first.**

**The deeper law:**  
*When you separate the observation of handler outcomes from the recording of event state (to gain transparency), you must choose between:*
- ***Idempotency without coordination*** (sacrifice transparency)
- ***Transparency without idempotency*** (require external consensus)

*No amount of detailed logging bridges this gap because the gap is about ordering of updates, not granularity of records.*

---

## Summary: What the Code Hides

1. **The cost of simplicity**: The single-context-object design *looks* elegant but forces conflation of incompatible states
2. **The cost of improvement**: Adding observability (detailed logs, stats) deepens the concealment by making the system *look* transparent while preserving the underlying semantic confusion
3. **The ordering problem**: Every improvement reveals that the system computes "success" at the wrong time relative to when handlers execute
4. **The conservation law**: You cannot solve event semantics problems by adding more records; you must change *what you record* and *when you record it*, which trades one impossibility for another

The EventBus doesn't have a bug. It has a **structural asymmetry**: it demands to know "did this succeed?" before all the facts are in.
