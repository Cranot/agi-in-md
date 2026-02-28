# EventBus Analysis: Double Recursion Diagnostic

## INITIAL CLAIM (Level 1)

**"The dead-letter queue treats all failures as equivalent, concealing that the system cannot distinguish between 'no handler was registered' and 'a handler existed but crashed.' These failures require different solutions, but emit() defaults to the same behavior (append to DLQ) for both."**

---

## Three Experts Test This Claim

**Defender (confirms it):**  
"Exactly. Lines 22–23 and 30–32 both call `_dead_letter.append(context)`. You can't tell them apart post-mortem. The system is lossy."

**Attacker (rejects it):**  
"But that conflation is intentional, not accidental. Both cases represent 'the system didn't achieve its goal.' The dead-letter queue isn't a diagnostic tool; it's a catch-all. Distinguishing them adds complexity for a problem that doesn't exist."

**Prober (reveals the hidden boundary):**  
"Neither of you is wrong, which is the problem. You're both assuming dead-lettering serves a single purpose. Defender, you want it for *debugging* (so you need fine-grained reasons). Attacker, you want it for *monitoring* (so you need a simple catch-all). But **those requirements are contradictory.** An observability mechanism shouldn't distinguish; an error recovery mechanism must. The real issue is: **what is the dead-letter queue actually for?** The code has never answered this. It just appends to a list whenever something isn't explicitly handled."

### Transformed Claim (After Expert Collision)

**"The dead-letter queue's true purpose is ambiguous because emit() conflates three incompatible responsibilities: (1) *dispatch* (route to handlers), (2) *recovery* (decide what to do when dispatch fails), and (3) *observability* (record what happened). The code defaults all three to the same code path—appending to a list. This works because the default is generic enough, which is precisely why the design problem remains invisible."**

### Concealment Mechanism: **Indiscriminate Default-Case Handling**

When a case isn't explicitly handled, the code defaults to the same fallback behavior (append to `_dead_letter`). This default is convenient enough that you don't realize it's not actually *solving* anything—it's just *hiding* that the system has never decided what it's trying to do.

---

## FIRST IMPROVEMENT (Designed to Deepen the Concealment)

Here's a "better" version that passes code review:

```python
class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter = []
        self._failure_modes = {}  # NEW: Explicit categorization

    def on(self, event_type, handler, priority=0, failure_strategy="dead_letter"):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
            self._failure_modes[event_type] = failure_strategy
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
            # NEW: Now we can distinguish the failure mode
            self._dead_letter.append({
                "context": context,
                "failure_mode": "no_handlers",
                "recoverable": False  # NEW insight
            })
            return context
        results = []
        for _, handler in handlers:
            try:
                results.append(handler(context))
            except Exception as e:
                context["error"] = e
                strategy = self._failure_modes.get(event_type, "dead_letter")
                # NEW: Now we can distinguish this too
                self._dead_letter.append({
                    "context": context,
                    "failure_mode": "handler_exception",
                    "strategy": strategy,
                    "recoverable": strategy == "retry"
                })
        context["results"] = results
        return context
```

*This looks like a genuine improvement.* We've separated "no handlers" from "handler crash." We can now see why something failed. Perfect, right?

### Three Properties Visible *Only* Because We Tried to Strengthen It

**1. "Recoverability" is a post-hoc lie**  
We set `recoverable=False` for no-handlers, but what if a handler was registered dynamically *after* this emit() call? We set `recoverable=True` for retry strategy, but what if this is the sixth failure? The improvement reveals that the original code had **no semantic way to express recoverability as a property of system state.** We just hardcoded it based on failure type, but failure type doesn't determine recoverability—the evolving state does.

**2. The metadata is stored but never used**  
We now append `{"failure_mode": "...", "strategy": "..."}` to the DLQ, but **emit() doesn't consult this information while executing.** The handler has already failed; storing the strategy for later is post-hoc recordkeeping, not active recovery. This reveals the original problem wasn't "we don't know what to do"—it was **"we're making the decision after it's too late to matter."**

**3. Handlers are silent about their own failure mode**  
A handler that throws doesn't know if it's in a "retry" context or a "fail-fast" context. The improvement reveals that **the original code had no way for handlers to *participate* in failure semantics**—they can only throw or return, not explain *why* they're throwing or what kind of throw it is.

---

## Gap Analysis: What Changed Between Claims?

**Original claim:** "The system can't distinguish failure types."  
**Transformed claim:** "The system distinguishes failure types *after* the execution is already complete, which makes the distinction information-only, not control-flow-meaningful."

**This gap reveals a deeper invariant:** All failure-handling mechanisms in this code are *callbacks executed after the failure has propagated up to emit().* As a result, no mechanism can **change the control flow that already happened.** It can only *record* what happened.

---

## SECOND IMPROVEMENT (Addresses the Recreated Property)

Let's move the decision point *before* the failure:

```python
class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter = []
        self._on_no_handlers_callback = None
        self._on_handler_failure_callback = None

    def on(self, event_type, handler, priority=0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def on_no_handlers(self, callback):
        # NEW: Pre-execution decision hook
        self._on_no_handlers_callback = callback

    def on_handler_failure(self, callback):
        # NEW: Can this handler throw be handled before dead-lettering?
        self._on_handler_failure_callback = callback

    def emit(self, event_type, payload):
        context = {"type": event_type, "payload": payload, "cancelled": False}
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            if self._on_no_handlers_callback:
                decision = self._on_no_handlers_callback(context)
                # NEW: Decision made *before* dead-lettering
                if decision == "skip":
                    return context
                elif decision == "raise":
                    raise ValueError(f"No handlers for {event_type}")
            self._dead_letter.append(context)
            return context
        results = []
        for _, handler in handlers:
            try:
                results.append(handler(context))
            except Exception as e:
                context["error"] = e
                if self._on_handler_failure_callback:
                    decision = self._on_handler_failure_callback(context, e)
                    if decision == "skip":
                        continue
                    elif decision == "raise":
                        raise
                self._dead_letter.append(context)
        context["results"] = results
        return context
```

*Better!* The caller can now make decisions *before* dead-lettering. But:

### What This Improvement Conceals (Recursive Diagnostic)

**The callbacks are still executing *inside* emit()'s control flow.** The caller appears to have agency, but they're actually registering instructions that emit() will invoke according to emit()'s logic. This is **inversion of control, disguised as control transfer.**

More critically: **emit() still has the dead-letter append as its default fallback.** If the callback doesn't raise or return a decision, execution falls through to dead-lettering. The improvement makes it *look* like the caller controls failure handling, but actually the function has just outsourced its decision-making to a callback—the dead-letter path is still inevitable if the callback doesn't explicitly prevent it.

---

## THE STRUCTURAL INVARIANT (Double Recursion Converges Here)

After applying the diagnostic to both improvements, an invariant emerges that **persists regardless of code changes:**

**"The function emit() has a fixed API boundary: it takes `(event_type, payload)` and returns `context`. All failure handling must fit within this boundary. As a result:**
- **All failure paths converge to the same return value**
- **Recovery decisions must complete before the function returns**
- **The dead-letter queue becomes the necessary catch-all for any case that doesn't have explicit inline handling**

**This is not a bug in the implementation. It is a structural property of the problem space.**

More precisely—the real invariant:

---

## THE DEEPEST STRUCTURAL INVARIANT

**"The code conflates two questions that have different answers and different decision-makers:**
1. ***Dispatch:* Did a handler exist and did it execute?** (the system must answer this)
2. ***Semantics:* Did the handler consider this event meaningful?** (only the handler knows this)

**By returning a single context object, emit() forces these into a single signal. Every improvement tries to enrich that signal (add metadata, add callbacks, add flags), but they're all working within the constraint that a single return value must answer both questions.**

**The invariant is not "the system can't distinguish failure types." The invariant is: "emit() cannot distinguish between operational failure (infrastructure) and semantic failure (application logic) in a way that lets different actors respond with different strategies, because all responses must complete before emit() returns."**

**If you split the function, you move the problem to the caller. If you add callbacks, you move it to callback handlers. If you add metadata, you move it to dead-letter consumers. But the fundamental constraint remains: some actor must decide "what do we do now?" while the function executes, and that actor will lack information that only emerges later.**

---

## Concealment Mechanism Summary

| Level | Mechanism | Hides |
|-------|-----------|-------|
| Original | **Default-case overloading** | That the system has never defined what dead-lettering is for |
| First improvement | **Metadata enrichment** | That metadata stored after failure doesn't change what already happened |
| Second improvement | **Inversion-of-control callbacks** | That the default (dead-letter) is still inevitable unless the callback explicitly short-circuits |
| All levels | **Reification of state** | That "what happened" is not a single object but a distributed decision across multiple actors |

The deepest concealment is the last one: **By treating the event's journey as a reifiable "context" object that can be passed, modified, and logged, the code makes it invisible that the journey actually involves multiple actors (middleware, handlers, policy callbacks, the DLQ) with different information and incompatible needs.** Each improvement adds more places to "fix" the problem, which makes it look increasingly solvable, which obscures that the problem is in the problem space itself, not the implementation.
