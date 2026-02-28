# Recursive Structural Diagnosis of EventBus

## The Falsifiable Claim

**The deepest structural problem is that the shared mutable `context` dict is passed through the entire middleware→handler→return pipeline, creating invisible coupling between components that are architecturally presented as independent.**

---

## Three Experts Stress-Test the Claim

### Expert A (Defender)
The shared mutable context is catastrophic. Consider:
```python
# Handler 1 runs, mutates context
def handler_a(ctx):
    ctx["payload"]["processed"] = True  # mutates for all subsequent handlers

# Handler 2 sees handler_a's mutation
def handler_b(ctx):
    if ctx["payload"].get("processed"):  # invisible dependency on execution order
        ...
```
Worse: `context["error"] = e` is set mid-loop, so handler 3 sees the error from handler 2 *while still executing in the success path*. The error path and success path run simultaneously on the same object.

### Expert B (Attacker)
Shared mutable state is a **symptom**. Freeze the dict and you break middleware (`context = mw(context)` requires return-based mutation). The real disease: **the code simultaneously implements three incompatible dispatch models**:

| Pattern | Evidence | Contract |
|---------|----------|----------|
| **Pipeline** | Middleware chain with `cancelled` flag, sequential `context = mw(context)` | Each stage transforms for the next |
| **Broadcast** | Multiple handlers with priority, `results` list | Each handler is independent |
| **Delivery** | Dead letter queue | At-least-one-consumer guarantee |

These three models have contradictory requirements for mutability, ordering, and error semantics. The dict isn't the problem — it's the solvent that dissolves the contradictions.

### Expert C (Probing Assumptions)
Both of you assume the `context` dict *should* have a fixed shape. But look at what the code actually does — it *constructs* the shape progressively:

```
Creation:  {"type", "payload", "cancelled"}     ← emit() builds this
Middleware: arbitrary keys added/removed         ← mw() can do anything  
Error:     {"error"} injected mid-iteration      ← catch block mutates
Return:    {"results"} appended after all handlers
```

The dict has no schema because **the EventBus has no lifecycle model**. There's no distinction between "being constructed," "being dispatched," "being handled," and "being returned." It's all one undifferentiated phase.

---

## Transformed Claim

> The deepest structural problem is that the EventBus **conflates three incompatible dispatch semantics** (pipeline, broadcast, delivery) into a single `emit` path. The shared mutable context dict is the **mechanism by which this conflation is concealed** — it acts as a universal adapter that makes incompatible patterns appear compatible by absorbing all contradictions into an untyped namespace.

### The Diagnostic Gap
My original claim pointed at **data** (mutable dict). The transformed claim points at **identity** (the code doesn't know what it is). The gap reveals I was drawn to the most tangible symptom rather than the architectural incoherence that generates it.

---

## The Concealment Mechanism

**The Polymorphic Dict.** A Python dict can be anything, so it is never wrong. It absorbs:
- Cancellation flags (pipeline semantics)
- Result lists (broadcast semantics)  
- Error objects (delivery semantics)
- Arbitrary middleware mutations (no semantics)

...into one namespace, without collision *by accident*, making the code appear clean. No type errors, no interface mismatches. The dict is a contradiction sink.

---

## The Engineered Deepening: A "Fix" That Passes Code Review

```python
from dataclasses import dataclass, field
from typing import Any, Optional, List, Callable

@dataclass
class EventContext:
    """Structured context replacing the raw dict."""
    event_type: str
    payload: Any
    cancelled: bool = False
    error: Optional[Exception] = None
    results: List[Any] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)  # extensibility point

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[tuple[int, Callable]]] = {}
        self._middleware: list[Callable[[EventContext], EventContext]] = []
        self._dead_letter: list[EventContext] = []

    def on(self, event_type: str, handler: Callable, priority: int = 0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn: Callable[[EventContext], EventContext]):
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> EventContext:
        context = EventContext(event_type=event_type, payload=payload)
        for mw in self._middleware:
            context = mw(context)
            if context.cancelled:
                return context
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(context)
            return context
        for _, handler in handlers:
            try:
                context.results.append(handler(context))
            except Exception as e:
                context.error = e
                self._dead_letter.append(context)
        return context
```

**Why this passes code review:** Dict → dataclass is a universally-approved refactor. Type hints added. Docstring present. It looks like a genuine improvement. Every reviewer's heuristic says "approve."

---

## Three Properties Visible Only Because I Tried to Strengthen the Concealment

**1. `results` as a typed field forces the question: whose results?**
In broadcast semantics, results are independent per-handler. In pipeline semantics, each result feeds the next. The dict hid this question. The dataclass, by giving `results` a name and a type (`List[Any]`), makes the ambiguity *structurally visible* — but only to someone asking "why is this a flat list and not a mapping from handler→result?"

**2. `cancelled` and `error` coexisting reveals competing flow-control models.**
Cancellation is *cooperative* (middleware opts in). Error is *exceptional* (handler fails). Putting them as sibling fields on the same dataclass exposes that they represent **two different lifecycle models fighting for control of the same pipeline.** The dict absorbed this contradiction silently. The dataclass *displays* it.

**3. `metadata: dict` recreates the original problem at a smaller scale.**
The improvement needed an escape hatch — a place for middleware to stash arbitrary data. That escape hatch is `metadata: dict`, which is precisely the untyped polymorphic dict we "replaced." The improvement *reproduces its predecessor inside itself,* revealing that the original dict wasn't accidental — it was structurally necessary given the unresolved dispatch semantics.

---

## Recursive Application: Diagnosing the Improvement

**What does the improvement conceal?**
It conceals that **naming fields doesn't establish semantics.** You can write `cancelled: bool` without ever specifying: cancelled by whom? Checked when? Reversible? The dataclass creates the *appearance* of a contract without the *substance* of one. It makes the code harder to question because it looks like someone already answered the questions.

**What property of the original problem is visible only because the improvement recreates it?**

> The original code's use of a raw dict was **honest.** It accurately represented the fact that the context has no fixed schema because the EventBus has no fixed semantics. The dataclass **dishonestly suggests** a fixed schema exists, which makes the absence of fixed semantics *harder to discover* and therefore *harder to fix.*

The original code's worst property — its shapelessness — was also its most truthful property. The improvement trades truthful ugliness for deceptive clarity, which is the most dangerous kind of technical debt: the kind that looks like a payment.
