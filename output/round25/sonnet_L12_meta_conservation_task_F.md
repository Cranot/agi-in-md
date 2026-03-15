# EventBus Diagnostic: Structure First (Level 12)

---

## I. The Falsifiable Claim

**The deepest structural problem: a single mutable `context` dict is both the event record and the processing transcript simultaneously, making every participant's behavior contingent on every prior participant's discipline — with no mechanism to detect or recover from contamination.**

Falsifiable because: any handler that mutates context produces undefined behavior in all subsequent handlers. This is testable. It predicts that a handler writing `context["payload"] = modified_payload` will silently corrupt every downstream handler's view of the original event.

---

## II. Three Experts Transform the Claim

**Expert A (Defends):** Confirmed. Look at line `context["error"] = e` — this overwrites a *shared* key mid-execution. If handler 2 fails, handler 1's already-executed results are retrospectively associated with an error context that wasn't true when handler 1 ran. The mutation problem is real and specific.

**Expert B (Attacks):** The claim identifies the symptom. The actual cause: *the system conflates the event (what happened) with the processing context (how we're handling it)*. `payload` is domain data; `cancelled`, `error`, `results` are pipeline metadata. They inhabit the same dict because the bus is trying to be both a **delivery mechanism** and a **result orchestrator** simultaneously. Shared mutable state is *structurally necessary* given those conflated responsibilities — it's not a fixable implementation detail.

**Expert C (Probes what both assume):** You both assume the fundamental unit should be per-handler isolation. But you're taking for granted *why the bus collects results at all*. Why does `emit()` return handler outputs? Why does the bus know about errors? The smuggled assumption: the EventBus is responsible for the *outcome* of handling, not just *delivery*. That assumption — not the mutable dict — is load-bearing.

**Transformed claim:** The deepest structural problem is that the EventBus conflates delivery with orchestration. This makes shared mutable context a structural *necessity*, not an implementation mistake.

---

## III. The Gap Is Itself Diagnostic

| | Location of problem |
|---|---|
| **Original claim** | In the mechanism (shared mutable dict) |
| **Transformed claim** | In the responsibility model (delivery + orchestration) |

The gap reveals the **concealment mechanism**: this code imports the *vocabulary* of good architecture — middleware (from Express), dead letter queue (from message brokers), priority (from event systems) — without importing the *responsibility separations* that make those patterns coherent. Each pattern originates in a domain where delivery and orchestration *are* separated. Assembled here without that separation, they look like sophistication while hiding that they contradict each other. The code's architectural fluency is what makes it illegible.

---

## IV. Improvement #1 — Legitimate-Looking, Deepens Concealment

```python
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
        # Separate immutable event from mutable processing context
        event = {"type": event_type, "payload": payload}
        context = {"event": event, "cancelled": False, "results": [], "errors": []}

        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append({"reason": "no_handlers", "event": event})
            return context

        for _, handler in handlers:
            try:
                result = handler(event, context)   # handler receives event separately
                context["results"].append(result)
            except Exception as e:
                context["errors"].append({
                    "handler": getattr(handler, "__name__", repr(handler)),
                    "error": e
                })
                self._dead_letter.append({
                    "reason": "handler_error",
                    "event": event,
                    "error": e
                })

        return context
```

**Why this passes code review:** Separates event from context (looks like the fix), adds structured error list (looks like improved observability), dead letter records reason (looks like better diagnostics), handler gets clean event signature (looks like better API design).

**Why this deepens concealment:** The separation of `event` and `context` makes the mutable state look *intentional* — like aggregation, not corruption. The two-list structure (`results`, `errors`) implies the bus has a coherent view of what happened. But context is *still* shared across all handlers. Handler N can observe handler N-1's results through the shared context, which is either a hidden feature or a hidden coupling — the code doesn't say which.

---

## V. Three Properties Visible Only Because I Strengthened It

**1. The handler signature problem.** When I changed `handler(context)` to `handler(event, context)`, I revealed that the original code's handler interface forces handlers to receive a *processing artifact* (context) instead of a *domain event*. The original was giving handlers the bus's internal state as their primary input. This was invisible because everything was in one dict.

**2. The dead letter queue has two incompatible purposes.** When I added `"reason"`, I revealed that the original queue conflates *delivery failure* (no handlers registered) with *processing failure* (handler threw an exception). These require entirely different recovery strategies: delivery failure means retry routing; processing failure means retry the handler or route to an error handler. The original silently conflated them.

**3. Middleware and handlers have irreconcilable contracts.** Separating event from context revealed that middleware operates on *pipeline state* (how we're processing) while handlers should operate on *domain events* (what happened). They cannot both work on the same object without one contaminating the other's semantic layer.

---

## VI. Recursive Diagnostic: What Does Improvement #1 Conceal?

Improvement #1 conceals: **every handler can implicitly observe every prior handler's results through the shared context**. By making context look structured (`results: []`, `errors: []`), the improvement makes global mutable state look like intentional aggregation. Handler N can read `context["results"][0]` and branch on it — creating invisible handler-to-handler coupling that bypasses the entire event model.

**Property of original recreated by improvement:** The original's single flowing context was obviously suspicious. The improvement's structured context makes the same flow look designed. But this recreates and makes *visible* the core property: **the system cannot distinguish between a handler (reacts to event) and an observer (watches pipeline state)**. Every handler is implicitly an observer of every other handler's outcomes, with no API to express which is which.

---

## VII. Improvement #2 — Addresses Handler/Observer Conflation

```python
from copy import deepcopy

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
        event = {"type": event_type, "payload": payload}
        pipeline_ctx = {"event": event, "cancelled": False}

        for mw in self._middleware:
            pipeline_ctx = mw(pipeline_ctx)
            if pipeline_ctx.get("cancelled"):
                return {"event": event, "cancelled": True, "results": [], "errors": []}

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append({"reason": "no_handlers", "event": event})
            return {"event": event, "cancelled": False, "results": [], "errors": []}

        results, errors = [], []
        pipeline_snapshot = deepcopy(pipeline_ctx)  # handlers see pipeline state, not each other

        for _, handler in handlers:
            handler_ctx = {**pipeline_snapshot, "event": event}   # fresh per handler
            try:
                results.append(handler(handler_ctx))
            except Exception as e:
                errors.append({"handler": getattr(handler, "__name__", repr(handler)), "error": e})
                self._dead_letter.append({"reason": "handler_error", "event": event, "error": e})

        return {"event": event, "cancelled": False, "results": results, "errors": errors}
```

**What this improvement conceals:** Each handler gets a snapshot of `pipeline_ctx`, but the *bus itself* still assembles a shared `results` list. The handler-isolation problem is solved for handlers, but now the bus must decide what to do when handler A's result affects what handler B should do — and it has no mechanism for this. The coupling moved from handler-to-handler (through shared context) to handler-to-bus (through the results aggregation model). More deeply: we've created a two-tier context system (pipeline vs. handler) with no documented contract for what belongs in each tier.

**Property of original that improvement recreates:** Every improvement must answer the question "what information flows from the pipeline to each handler, and what flows back?" The original never answered it. This improvement answers it structurally (pipeline → snapshot → handler → result → bus) but doesn't answer it *semantically* (what does a result mean? can it affect other handlers?). The question is unanswerable within this responsibility model.

---

## VIII. The Structural Invariant

Through every improvement, one property persists unchanged:

> **The bus must route information between the pipeline stage and individual handlers, but the system provides no semantic model for what that information means, who owns it, or what constitutes a valid transformation of it.**

This is not an implementation failure. It is a consequence of the feature set:

- Middleware requires information to flow *into* the handler stage
- Result collection requires information to flow *out of* the handler stage  
- Error propagation requires the bus to observe handler internals
- Priority requires handlers to be sequenced, creating implicit ordering dependencies
- Cancellation requires pipeline state to affect handler execution

Each feature requires a specific information flow across the pipeline/handler boundary. The invariant: **this boundary cannot be both clean (for isolation) and permeable (for coordination) simultaneously**. Any architecture must choose, and each choice recreates what the other would have prevented.

---

## IX. Invert the Invariant

**Original constraint:** Context cannot be simultaneously private (per-handler isolation) and shared (pipeline communication).

**Inversion:** Make the bus own all state. Handlers declare *effects* instead of mutating context. The bus applies effects after all handlers complete.

```python
# Sketch of inverted design
class EventBus:
    def emit(self, event_type, payload):
        event = Event(type=event_type, payload=payload)
        pipeline_state = self._run_middleware(event)
        if pipeline_state.cancelled:
            return Outcome.cancelled(event)

        effects = []
        for _, handler in self._handlers.get(event_type, []):
            read_view = pipeline_state.immutable_snapshot()
            effect = handler.handle(event, read_view)   # returns Effect, mutates nothing
            effects.append(effect)

        resolved = self._resolve_effects(effects)        # bus owns conflict resolution
        return Outcome.completed(event, resolved)
```

**New impossibility created:** If handlers return effects instead of mutating context, the bus must know how to *apply and resolve* those effects. But effect resolution requires:
- A **type system** for effects (what kinds of effects exist?)
- A **conflict resolution strategy** (what if two handlers produce contradictory effects?)  
- A **dependency model** (can effect B depend on effect A's result?)

This is a full **algebraic effect system**. The coupling isn't eliminated — it moves from runtime shared state to a compile-time effect type hierarchy. In a dynamically typed language, this is more complex to specify than the original problem. The bus that owns nothing (delivery only) is coherent; the bus that owns everything (effect system) is coherent; the bus that half-owns (this code's model) is not.

---

## X. The Conservation Law

| | Impossibility |
|---|---|
| **Original design** | Context cannot be private (isolation) *and* shared (coordination) |
| **Inverted design** | Effects cannot be applied without the bus knowing handler semantics |

**Conservation Law:**

> **The semantic coupling required by an event system equals the total information that must cross the pipeline/handler boundary. Architectural changes redistribute this coupling across different mechanisms (runtime state, type systems, effect algebras) but cannot reduce its total magnitude. Coupling is conserved.**

Formally: every feature in `{middleware, result collection, error propagation, priority, cancellation}` contributes a fixed quantum of required information flow. No architecture eliminates these quanta — it only chooses where to make them visible.

---

## XI. Apply the Diagnostic to the Conservation Law Itself

**What the conservation law conceals:** It treats coupling as a single homogeneous substance that moves around. This hides that coupling types are *qualitatively different*: runtime coupling (shared mutable dict) and compile-time coupling (effect type system) have different failure modes, different debuggability, different maintainability profiles, different team skill requirements. Calling them "the same amount of coupling" obscures the most important design decisions.

**Structural invariant of the law:** When we refine it — distinguishing coupling types — we find: different coupling types can be converted into each other, but each conversion preserves the *information flow requirement* between pipeline and handlers. The invariant is not "coupling is conserved" but: **the information flow requirement is fixed by the feature requirements, not the implementation.**

**Invert this invariant:** If information flow is fixed, what happens at zero information flow? A bus with zero coupling between pipeline and handlers: no middleware transformation, no result collection, no error propagation, no priority sequencing. A pure fire-and-forget bus. This *is* coherent — and it's coherent precisely because it has no features.

**New impossibility:** A zero-coupling event bus cannot support *any* of the features this code attempts. Each feature is exactly one quantum of forced coupling.

---

## XII. The Meta-Law

> **The minimum viable event bus has zero coupling and zero features. Every feature added to an event bus contributes exactly one irreducible quantum of coupling between the pipeline and handlers. The "deep structural problems" of any event bus are not implementation bugs — they are the exact coupling cost of the feature set it supports, made visible.**

This is the conservation law of the conservation law.

---

## XIII. The Prediction No Code Analysis Could Reveal

The meta-law predicts something about this codebase that is invisible in the code itself:

> **Any team that rewrites this EventBus — in any language, using any architectural pattern (Actor model, Reactive Streams, algebraic effects, immutable event sourcing) — will rediscover exactly the same set of structural tensions. The debates will recur at every feature addition. Each resolution will move coupling rather than eliminate it. The team will attribute this to prior implementers' mistakes rather than recognizing it as the feature set's geometric shape.**

More specifically: the meta-law predicts that this codebase will generate a **recurring, irresolvable architectural debate** about "whose responsibility is the processing context?" This question is unanswerable within any single coherent model that supports the current feature set. It will be re-litigated with each new feature request, each new team member, and each "cleanup" sprint — not because the team is unskilled, but because the feature requirements *make the question unanswerable*. The code's real problem is not in the code. It is in the requirements document that specified middleware + results + error propagation + priority without specifying who owns the processing context — and that document is invisible to code review.

---

## Summary Table

| Stage | Finding |
|---|---|
| Original claim | Shared mutable context creates discipline-dependent correctness |
| Transformed claim | Delivery + orchestration conflation makes shared state structurally necessary |
| Concealment mechanism | Architectural vocabulary imported without the responsibility separations that make it coherent |
| Structural invariant | Pipeline/handler information boundary cannot be simultaneously clean and permeable |
| Conservation law | Coupling is conserved across architectural changes |
| Meta-law | Every feature = one irreducible coupling quantum; structural problems are feature costs made visible |
| Prediction | Any rewrite with the same feature set will rediscover the same tensions; the problem is in the requirements, not the code |
