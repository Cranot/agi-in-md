## The Claim

**The EventBus's deepest structural problem is that `context` simultaneously serves as an event descriptor (what happened) and a mutable result accumulator (what is being done about it), making the system's causal direction ambiguous — handlers can retroactively redefine the event they're supposed to be responding to.**

This is falsifiable. It could be wrong if: mutation-as-communication is a documented design intent, if handlers contractually don't mutate context, or if the real problem is something else entirely (error handling, memory leaks, etc.).

---

## Three Experts

**Expert 1 — Defender:** The mutable context is correct. Express, Koa, and virtually every mature middleware system passes a mutable context through handlers. The claim attacks a pattern, not a bug. The real problem is missing immutability enforcement, not the concept. Your claim is too abstract to be actionable.

**Expert 2 — Attacker:** The claim is right but understates the damage. Shared mutable context means handlers are *implicitly coupled through state with no declared contract*. Handler A writes `context["user_verified"] = True`, Handler B reads it — an invisible dependency exists. Priority is the only ordering mechanism, but priority doesn't encode semantic dependencies. You've named the symptom; the disease is undeclared inter-handler coupling.

**Expert 3 — Prober:** Both of you assume EventBus's purpose is decoupled message-passing. But neither asked: *what is `context` for, ontologically*? The defender assumes it's a pipeline. The attacker assumes it should be isolated. But the code assumes it's both — and that assumption is what both of you take for granted.

### Transformation

The claim transforms from *"context serves dual roles"* (what context does) to *"the EventBus has no coherent model of what an event is"* (what an event is). The original claim diagnosed behavior. The transformed claim diagnoses ontology.

**The diagnostic gap:** I was looking at function when I should have been looking at identity. The code treats events as mutable shared state while the pub/sub contract requires events to be immutable facts about the past.

---

## The Concealment Mechanism

**Feature completeness as ontological concealment.**

Each component looks sophisticated in isolation:
- Middleware chain → mature extensibility pattern
- Priority sorting → thoughtful handler ordering  
- Dead letter queue → defensive error handling
- Per-handler try/except → resilience

The sophistication signals design maturity, which deflects the fundamental question: *what is an event?* You review the priority logic, you review the middleware chain, you review the dead letter queue — and nowhere in that review do you ask whether the event object should be mutable at all. The presence of four "advanced" features implies someone thought hard about this.

---

## Improvement 1: Deepening the Concealment

Add optional handler isolation — looks like it fixes the mutation problem:

```python
def emit(self, event_type, payload, *, isolate_handlers=False):
    context = {"type": event_type, "payload": payload, "cancelled": False}
    
    for mw in self._middleware:
        context = mw(context)
        if context.get("cancelled"):
            return context
    
    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(context)
        return context
    
    results = []
    for _, handler in handlers:
        handler_ctx = dict(context) if isolate_handlers else context
        try:
            results.append(handler(handler_ctx))
        except Exception as e:
            context["error"] = e
            self._dead_letter.append(dict(context))  # snapshot, not live reference
    
    context["results"] = results
    return context
```

This passes code review: "Add optional handler isolation to prevent unintended mutation side effects. Dead letter now captures snapshots for accurate post-mortem."

**How it deepens concealment:** The `isolate_handlers` flag signals that someone considered the mutation problem and made it optional. The dead letter snapshots signal careful engineering. Neither reviewer nor author will revisit the fundamental model question — it appears answered.

---

## Three Properties Visible Only Because I Tried to Strengthen It

1. **The payload is the real mutation vector, not the context wrapper.** `dict(context)` is a shallow copy. `context["payload"]` still points to the same object. The concealment improvement reveals that the context dict is nearly a red herring — the mutable danger lives in the payload, which no amount of context copying addresses.

2. **Isolation and shared-state are not dial positions — they're incompatible contracts.** The flag `isolate_handlers=False` as default reveals that the system is built for shared state and isolation is bolted on. But if you set it to `True`, handlers genuinely cannot see each other's enrichments — so priority stops encoding semantic dependencies and becomes pure execution order. These are architecturally different systems; a boolean cannot bridge them.

3. **The dead letter queue's semantics change during execution.** "Snapshot for dead letter" implies the context at the *moment of error* matters, which means dead letter is logging execution states, not events. A true dead letter queue stores undeliverable messages. This one stores time-indexed program states. The improvement makes this incoherence legible by formalizing it.

---

## Improvement 2: The Contradiction

If Improvement 1 moves toward isolation, move toward formalized shared state:

```python
def on(self, event_type, handler, priority=0, enriches=None, requires=None):
    """
    enriches: context keys this handler will write
    requires: context keys this handler needs from prior handlers
    """
    if event_type not in self._handlers:
        self._handlers[event_type] = []
    entry = (priority, handler, enriches or [], requires or [])
    self._handlers[event_type].append(entry)
    self._handlers[event_type].sort(key=lambda x: -x[0])

def emit(self, event_type, payload):
    context = {"type": event_type, "payload": payload, "cancelled": False}
    
    for mw in self._middleware:
        context = mw(context)
        if context.get("cancelled"):
            return context
    
    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(context)
        return context
    
    results = []
    for _, handler, enriches, requires in handlers:
        missing = [r for r in requires if r not in context]
        if missing:
            context["error"] = MissingContextError(f"Requires {missing}")
            self._dead_letter.append(context)
            continue
        try:
            results.append(handler(context))
        except Exception as e:
            context["error"] = e
            self._dead_letter.append(context)
    
    context["results"] = results
    return context
```

This also passes code review: "Add declarative handler dependency contracts to prevent silent missing-context bugs. Handlers now document what they produce and consume."

**The contradiction:** Improvement 1 says handlers should not see each other's state. Improvement 2 says handlers declaring `requires` should see prior handlers' state. One weakens shared context; the other formalizes and strengthens it.

---

## The Structural Conflict

**The EventBus conflates two incompatible communication patterns: broadcast (one-to-many, isolated, events as immutable facts) and pipeline (sequential enrichment, shared state, events as collaborative computations).**

Both improvements are legitimate because they're solving for different valid interpretations of the same class. Improvement 1 is correct if you're building a notification system. Improvement 2 is correct if you're building an enrichment pipeline. The conflict exists *only because both improvements are legitimate* — if one were wrong, you'd reject it. The fact that both are defensible reveals the class is simultaneously two different systems that happen to share an `emit` method.

---

## Improvement 3: The Resolution

Separate handler modes explicitly — observers get isolation, transformers get the pipeline:

```python
def on(self, event_type, handler, priority=0, mode='observe'):
    """
    mode='observe'   → handler receives a deep copy; cannot affect other handlers
    mode='transform' → handler receives live context; mutations are visible downstream
    """
    if event_type not in self._handlers:
        self._handlers[event_type] = []
    self._handlers[event_type].append((priority, handler, mode))
    self._handlers[event_type].sort(key=lambda x: -x[0])

def emit(self, event_type, payload):
    import copy
    context = {"type": event_type, "payload": payload, "cancelled": False}
    
    for mw in self._middleware:
        context = mw(context)
        if context.get("cancelled"):
            return context
    
    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(context)
        return context
    
    results = []
    for _, handler, mode in handlers:
        try:
            if mode == 'observe':
                results.append(handler(copy.deepcopy(context)))
            else:
                results.append(handler(context))
        except Exception as e:
            context["error"] = e
            self._dead_letter.append(context)
    
    context["results"] = results
    return context
```

Both Improvement 1 and 2 are now accommodated. Observers are isolated; transformers share the pipeline. It passes code review.

---

## How It Fails

**Handler ordering is governed by a single priority integer, but observe/transform mode creates a semantic ordering requirement that priority cannot encode.**

Consider: a transformer at priority 10, an observer at priority 5. The observer runs *after* the transformer and receives the post-transformation context in its deepcopy — defeating isolation. To achieve true isolation, every observer must have higher priority than every transformer. But priority is a shared namespace: user code can't enforce this invariant, there's no type system preventing it, and the sort has no concept of mode.

Worse: consider two transformers and one observer. Should the observer see the state after transformer A but before transformer B? Priority cannot express that. The deepcopy happens at execution time, not at emit time, so the snapshot the observer receives depends entirely on what happened to run before it — a function of priority values no one designed to carry that meaning.

---

## What the Failure Reveals About the Design Space

The conflict said: *choose between broadcast and pipeline.* That framing implied the problem was a design decision — pick one, implement it cleanly.

The failure of the resolution reveals something the conflict alone could not: **even if you support both models simultaneously, you require a causality system — a way to express "this observation happens before this transformation, regardless of their relative priorities" — and a scalar integer cannot encode causal structure.**

Priority is a collapsed, lossy projection of a dependency graph onto a single dimension. It works when all handlers are the same kind (all observers, or all transformers in a linear chain). The moment you introduce heterogeneous handler types with different state-access contracts, the scalar breaks because it cannot distinguish *temporal ordering* (this runs at time T) from *semantic ordering* (this sees the state produced by that).

**The true shape of the design space:** EventBus requires either  
(a) a full causal graph (DAG of handler dependencies, like a dataflow engine), or  
(b) strict immutability (events are values, handlers are pure functions, like functional reactive programming).

The concealment mechanism — feature completeness signaling design maturity — now fully exposes itself: middleware, priority, and dead letter are all scalar mechanisms applied to what is fundamentally a graph problem. The sophistication was always local. The system was always missing a model of causality. Every legitimate improvement to this codebase will eventually collide with that absence, because you cannot build a correct causal system out of sorted lists and shared dicts.
