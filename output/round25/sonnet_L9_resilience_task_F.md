# Structure First Analysis: EventBus

---

## I. The Falsifiable Claim

**The deepest structural problem is that `context` — a single mutable dict — serves simultaneously as event identity, middleware transformation channel, inter-handler communication bus, and error accumulator, with no mechanism to distinguish these roles, making the system's causality structurally unobservable.**

Falsifiable because: if true, then (a) a handler that mutates `context["payload"]` mid-chain cannot be distinguished from middleware augmentation or from accidental corruption, (b) the dead letter queue captures corrupted state rather than original events, and (c) no diagnostic tool built on top of this system can recover what the original event was.

---

## II. Three Expert Test

**The Defender** accepts the claim and extends it:

> "The priority system makes this catastrophic in a specific way. High-priority handlers get a clean context; low-priority handlers get whatever those handlers left behind. The error path compounds this — `context["error"] = e` mutates the same dict that subsequent handlers receive. You can have a handler that succeeds but silently operates on a context already marked with a prior handler's exception. The dead letter queue then preserves this corrupted context as if it were the event — you can't reconstruct what happened."

**The Attacker** says the claim overstates it:

> "Mutable shared context is a legitimate pattern — it's how HTTP middleware stacks work, how express.js works, how most event pipelines work. The problem isn't mutability; it's the absence of defensive copies. Add `copy.deepcopy(context)` before each handler call and you've fixed it without changing the architecture. The claim misidentifies the symptom (mutability) as the disease."

**The Prober** asks what both are taking for granted:

> "You're both arguing about *mutation*. But you're both assuming that 'context' is the right unit of analysis. What if the problem is upstream of that? This code conflates three semantically distinct activities — middleware enrichment (legitimate, expected to mutate), handler result accumulation (legitimate, should be isolated), and cross-handler contamination (illegitimate, invisible). The system provides one mechanism for all three. That's not a mutation problem; it's a *category problem*. Even if you make it immutable, you haven't given the system any way to tell these three things apart."

---

## III. The Transformation and Its Diagnostic Gap

**Original claim:** Mutable shared state is dangerous.

**Transformed claim:** The system provides an undifferentiated channel for three semantically distinct activities — *event description*, *middleware transformation*, and *handler result accumulation* — and has no structural capacity to enforce or observe the boundaries between them.

**The gap:** The original claim pointed at *mutability as the problem*. The transformed claim reveals that mutability is not the problem — undifferentiated mutability is. The attacker was right that `deepcopy` fixes something, but the prober showed it fixes the wrong thing: you'd have isolated copies of an entity whose categories are still confused.

**The gap itself is diagnostic:** This code was likely written by composing several individually reasonable decisions (dict-as-context, shared-across-middleware, accumulated-results) without ever asking whether these decisions were compatible. The confusion is structural, not incidental.

---

## IV. The Concealment Mechanism

**Feature Overcrowding.**

The code presents four legitimate engineering artifacts:
- A dead letter queue (looks like proper fault tolerance)
- A middleware chain (looks like proper extensibility)
- A priority system (looks like proper ordering control)
- Exception capture (looks like proper error isolation)

Each feature is real and partially functional. Together, they construct a surface of apparent competence that redirects reviewer attention toward whether each feature is *implemented correctly* rather than whether their shared substrate — the mutable dict — makes their combined guarantees incoherent.

The dead letter queue is the sharpest concealment: when a context appears there, the system appears to have *caught* the problem. It hasn't. It captured a corrupted event. The original is gone.

---

## V. The Legitimate-Looking Improvement That Deepens Concealment

Add middleware validation with schema enforcement and a context factory:

```python
_REQUIRED_CONTEXT_KEYS = frozenset({"type", "payload", "cancelled"})

def _make_context(self, event_type, payload):
    return {
        "type": event_type,
        "payload": payload,
        "cancelled": False,
        "metadata": {},
        "_version": 0,
    }

def _validate_context(self, ctx, stage):
    if not isinstance(ctx, dict):
        raise TypeError(f"[{stage}] Middleware must return a dict, got {type(ctx)}")
    missing = _REQUIRED_CONTEXT_KEYS - ctx.keys()
    if missing:
        raise ValueError(f"[{stage}] Middleware removed required keys: {missing}")
    return ctx

def emit(self, event_type, payload):
    context = self._make_context(event_type, payload)
    for i, mw in enumerate(self._middleware):
        result = mw(context)
        context = self._validate_context(result, f"middleware[{i}]")
        context["_version"] += 1
        if context.get("cancelled"):
            return context
    # ... rest unchanged
```

**Why this passes code review:**
- It fixes the actual `None`-return bug (middleware returns nothing → AttributeError)
- It adds schema enforcement that looks like defensive programming
- The version counter implies auditability
- The stage label in errors looks like professional diagnostics

**Why it deepens concealment:**
Validation applies *only to middleware*. Handler-layer mutation — the more dangerous and more frequent path — is completely unaddressed. The improvement creates a false tier structure: "validated middleware" vs. unexamined handlers. Reviewers now focus on whether the schema is correct rather than whether the categories are confused. The code looks more mature while the structural problem migrates to a darker, less-examined corner.

---

## VI. Three Properties Visible Only From Trying to Strengthen

**1. The middleware/handler distinction is fictional at the structural level.**
When I tried to add middleware validation, I could not add equivalent handler validation — handlers return results, not contexts. This revealed that the "middleware" and "handler" labels are purely semantic; structurally, both receive the same mutable dict and can corrupt it equally. The distinction is enforced by convention, not by the type system or call signature.

**2. "Required keys" is a category error masquerading as a schema.**
When I tried to define what middleware must preserve, I had to choose between (a) protecting all keys — which breaks legitimate augmentation — or (b) protecting a few keys — which is arbitrary. This revealed that the code has no model of what "context" is *for*. It mixes event identity (`type`, `payload`) with processing state (`cancelled`, `error`) with results (`results`). Any schema built on this conflation enforces the wrong thing.

**3. The dead letter queue destroys the event before error handlers can observe it.**
When I tried to make the schema validator robust against cascading failures, I realized: if middleware raises an exception mid-chain, the context at that point may already be mutated from its original form. The error handler sees a corrupted context, not the original event. The dead letter queue preserves state *after* corruption, not *before*. This property is only visible when you try to build reliable error recovery.

---

## VII. The Revision

An engineer who has read this analysis addresses all three properties:

```python
import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class Event:
    """
    Immutable event identity. What happened. Cannot be modified after creation.
    Middleware and handlers receive this; only the bus creates it.
    """
    type: str
    payload: Any  # Caller is responsible for payload immutability


@dataclass
class ProcessingContext:
    """
    Mutable processing accumulator. What we are doing about the event.
    Structurally separated from the event it references.
    Middleware may write to metadata; handlers may read it.
    """
    event: Event
    metadata: Dict[str, Any] = field(default_factory=dict)
    cancelled: bool = False
    cancellation_reason: Optional[str] = None

    def cancel(self, reason: str = ""):
        self.cancelled = True
        self.cancellation_reason = reason


@dataclass
class HandlerResult:
    """
    Per-handler outcome. Isolated — one handler's error cannot corrupt another's result.
    """
    handler_id: str
    value: Any = None
    error: Optional[Exception] = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


@dataclass
class EmitResult:
    """The complete, structured result of a single emit call."""
    event: Event                        # Original, immutable
    context: ProcessingContext          # Final processing state
    handler_results: List[HandlerResult]
    dead_lettered: bool = False
    dead_letter_reason: Optional[str] = None


@dataclass
class DeadLetterRecord:
    """
    Preserves the original event alongside the reason and context at failure time.
    The event here is always the original — not corrupted state.
    """
    event: Event                # What was originally emitted — immutable
    reason: str                 # Why it was dead-lettered
    context: ProcessingContext  # Context at point of failure (may be partial)


class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[tuple]] = {}
        self._middleware: List[Callable] = []
        self._dead_letter: List[DeadLetterRecord] = []

    def on(
        self,
        event_type: str,
        handler: Callable[[Event, ProcessingContext], Any],
        priority: int = 0,
        name: Optional[str] = None,
    ) -> "EventBus":
        """
        Register a handler. Signature: handler(event: Event, ctx: ProcessingContext) -> Any
        Handlers receive the immutable Event directly — they cannot redefine what happened.
        They receive the shared ProcessingContext — they can signal to each other via metadata.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        handler_id = name or getattr(handler, "__name__", repr(handler))
        self._handlers[event_type].append((priority, handler_id, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])
        return self

    def use(self, middleware_fn: Callable[[ProcessingContext], None]) -> "EventBus":
        """
        Register middleware. Signature: middleware(ctx: ProcessingContext) -> None
        Middleware mutates context in-place. It cannot replace the event.
        """
        self._middleware.append(middleware_fn)
        return self

    def emit(self, event_type: str, payload: Any) -> EmitResult:
        event = Event(type=event_type, payload=payload)   # Created once; immutable hereafter
        context = ProcessingContext(event=event)

        # --- Middleware phase: transforms context; cannot touch event ---
        for i, mw in enumerate(self._middleware):
            try:
                mw(context)                               # Mutates in-place; returns nothing
            except Exception as e:
                reason = f"middleware[{i}] raised {type(e).__name__}: {e}"
                self._dead_letter.append(DeadLetterRecord(event, reason, context))
                return EmitResult(
                    event=event,
                    context=context,
                    handler_results=[],
                    dead_lettered=True,
                    dead_letter_reason=reason,
                )
            if context.cancelled:
                return EmitResult(event=event, context=context, handler_results=[])

        # --- Handler phase: each handler result is isolated ---
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            reason = "no handlers registered"
            self._dead_letter.append(DeadLetterRecord(event, reason, context))
            return EmitResult(
                event=event,
                context=context,
                handler_results=[],
                dead_lettered=True,
                dead_letter_reason=reason,
            )

        handler_results: List[HandlerResult] = []
        for _, handler_id, handler in handlers:
            try:
                # Handler receives immutable Event + shared ProcessingContext.
                # Its return value is captured in its own HandlerResult.
                # An exception here does not mutate context or affect sibling handlers.
                value = handler(event, context)
                handler_results.append(HandlerResult(handler_id=handler_id, value=value))
            except Exception as e:
                handler_results.append(HandlerResult(handler_id=handler_id, error=e))
                reason = f"handler '{handler_id}' raised {type(e).__name__}: {e}"
                # Dead letter records the original event — not the current context state
                self._dead_letter.append(DeadLetterRecord(event, reason, context))
                # Continue: other handlers are not contaminated

        return EmitResult(event=event, context=context, handler_results=handler_results)

    def drain_dead_letters(self) -> List[DeadLetterRecord]:
        records, self._dead_letter = self._dead_letter, []
        return records
```

---

## VIII. Final Assessment: What Is the Concealment Now?

**The concealment is transformed, not broken.**

**What is genuinely fixed:**

The three named properties are addressed structurally:
1. `Event` is a frozen dataclass — handlers cannot redefine what happened
2. `DeadLetterRecord` preserves the original `Event` before any processing — error recovery sees uncorrupted state
3. `HandlerResult` is per-handler — one handler's exception cannot contaminate another's result or the shared context

**What has transformed:**

`ProcessingContext.metadata` is now the locus of the original problem. It is a `Dict[str, Any]`, shared across all handlers, mutable, untyped, and undifferentiated. Handler A can write `context.metadata["auth_override"] = True` and handler B will see it. The system still has no mechanism to distinguish legitimate inter-handler signaling from accidental contamination — the problem has migrated from `context["payload"]` to `context.metadata`.

**The new concealment mechanism:**

**Structural Displacement.** The undifferentiated-mutation problem has been moved from a visible location (one flat dict) to a less visible location (`ProcessingContext`, a properly typed class with one mutable field). The typed structure around it — frozen `Event`, isolated `HandlerResult`, categorized `DeadLetterRecord` — creates an impression of rigor that makes the remaining shared mutable state harder to see, not easier.

**What would break the concealment entirely:**

Each handler would need its own read-only view of context metadata set by middleware, and a handler-scoped write channel visible only to itself. That is a different architecture — one that treats "what middleware prepared" and "what handlers signal" as structurally distinct things. This code cannot reach that without abandoning the shared-context model, which means the concealment is intrinsic to the architecture's choice of abstraction, not to any particular implementation.

The code is meaningfully better. The concealment is meaningfully subtler. Those are not the same thing.
