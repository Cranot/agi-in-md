## Analysis: EventBus

---

### Falsifiable Claim

**This EventBus cannot correctly preserve more than one failed handler per emission.** When two handlers throw, both dead-letter entries reference the same `context` dict — which has `context["error"]` set to whichever exception ran *last*. To falsify this: show me a multi-handler failure where the dead-letter queue independently preserves each handler's error with the context at the time of failure. You cannot. The implementation makes it structurally impossible.

```python
# Demonstration of the collapse:
bus = EventBus()
bus.on("x", lambda ctx: (_ for _ in ()).throw(ValueError("first")))
bus.on("x", lambda ctx: (_ for _ in ()).throw(TypeError("second")))
bus.emit("x", {})

# dead_letter has TWO entries — both the SAME dict object
# both show error=TypeError("second")
# ValueError is unrecoverable, permanently gone
assert bus._dead_letter[0] is bus._dead_letter[1]  # True
assert bus._dead_letter[0]["error"] == bus._dead_letter[1]["error"]  # True — both "second"
```

---

### The Concealment Mechanism

**Error-handling theater via continued-execution-with-shared-state.**

The `try/except → dead_letter.append(context)` structure *looks* like fault isolation. It reads as: "catch the error, route to dead-letter, continue." It signals competence through familiar patterns. But the mechanics are:

1. `context["error"] = e` mutates the *single shared object* all handlers see
2. `self._dead_letter.append(context)` appends a **live reference**, not a snapshot
3. Execution continues, and `context["results"] = results` retroactively mutates every dead-letter entry ever appended

The subsequent dead-letter read will be: *the final state of context after all handlers ran*, not the state at the moment of failure. The try/except block performs the *grammar* of error isolation without the *semantics*. This is what makes it pass casual review.

**Secondary concealment:** Middleware cancellation and handler-error paths both return `context`, making them look symmetric. They are not — middleware runs before handler count is known; cancellation is clean; handler errors are dirty state accumulated in-place.

---

### Engineered Improvement

```python
import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class HandlerResult:
    handler_id: str
    priority: int
    result: Any = None
    error: Optional[Exception] = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


@dataclass
class EmitResult:
    context: dict
    handler_results: list[HandlerResult] = field(default_factory=list)
    cancelled: bool = False

    @property
    def failed(self) -> list[HandlerResult]:
        return [r for r in self.handler_results if not r.succeeded]

    @property
    def succeeded(self) -> list[HandlerResult]:
        return [r for r in self.handler_results if r.succeeded]


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[tuple[int, str, Callable]]] = {}
        self._middleware: list[Callable[[dict], dict]] = []
        self._dead_letter: list[dict] = []

    def on(self, event_type: str, handler: Callable, priority: int = 0) -> str:
        """Returns handler_id for future off() calls."""
        handler_id = f"{event_type}:{handler.__qualname__}@{id(handler)}"
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler_id, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])
        return handler_id

    def off(self, event_type: str, handler_id: str) -> bool:
        if event_type not in self._handlers:
            return False
        before = len(self._handlers[event_type])
        self._handlers[event_type] = [
            (p, hid, h) for p, hid, h in self._handlers[event_type]
            if hid != handler_id
        ]
        return len(self._handlers[event_type]) < before

    def use(self, middleware_fn: Callable[[dict], dict]) -> None:
        self._middleware.append(middleware_fn)

    def emit(self, event_type: str, payload: Any) -> EmitResult:
        context: dict = {"type": event_type, "payload": payload, "cancelled": False}

        # Middleware phase: each middleware owns its own context mutation
        for mw in self._middleware:
            returned = mw(context)
            if not isinstance(returned, dict):
                raise TypeError(
                    f"Middleware {mw!r} must return dict, got {type(returned).__name__}"
                )
            context = returned
            if context.get("cancelled"):
                return EmitResult(
                    context=copy.deepcopy(context),
                    cancelled=True
                )

        handlers = self._handlers.get(event_type, [])

        if not handlers:
            # Unhandled event — snapshot cleanly
            self._dead_letter.append({
                **copy.deepcopy(context),
                "reason": "no_handlers",
            })
            return EmitResult(context=copy.deepcopy(context))

        emit_result = EmitResult(context=copy.deepcopy(context))

        for priority, handler_id, handler in handlers:
            # Each handler receives an isolated snapshot — no cross-handler pollution
            handler_context = copy.deepcopy(context)
            try:
                outcome = handler(handler_context)
                emit_result.handler_results.append(
                    HandlerResult(
                        handler_id=handler_id,
                        priority=priority,
                        result=outcome,
                    )
                )
            except Exception as e:
                hr = HandlerResult(
                    handler_id=handler_id,
                    priority=priority,
                    error=e,
                )
                emit_result.handler_results.append(hr)
                # Dead-letter entry is a true snapshot: frozen at time of failure
                self._dead_letter.append({
                    **copy.deepcopy(context),
                    "handler_id": handler_id,
                    "priority": priority,
                    "reason": "handler_error",
                    "error": e,
                })

        return emit_result
```

---

### Three Properties Only Visible Because I Tried to Strengthen It

**1. Handler identity was architecturally undefined.**
When I introduced `handler_id` for per-failure attribution, I discovered there was no stable identity concept for handlers. Two `lambda ctx: ...` expressions have the same `__qualname__`. The original concealed this by discarding handler identity entirely — you can never reconstruct *which* handler failed, only *that one did*. This means the dead-letter queue was always unreplayable; you can't retry without guessing.

**2. Middleware has an implicit, unverified return contract.**
Adding `isinstance(returned, dict)` exposed that the original `context = mw(context)` silently accepts any return type. A middleware that returns `None` on the cancellation branch causes `AttributeError: 'NoneType' has no attribute 'get'` on the next iteration's `context.get("cancelled")`. The original looked defensive (it checks `cancelled`) but created a hidden crash path that only surfaces with well-intentioned middleware that forgets to return.

**3. Handler-to-handler communication via context mutation is an undeclared architectural choice.**
When I passed `copy.deepcopy(context)` per handler for isolation, I made it impossible for handler A to enrich context for handler B. The original silently encoded *shared mutable context as the communication channel between handlers* — but never documented this as a design decision. Strengthening isolation revealed the original has a specific semantics (handlers are ordered pipelines, not independent subscribers) that directly contradicts the "event bus" mental model it implies.

---

### Summary Table

| Problem | Class | Visibility |
|---|---|---|
| Shared `context` dict aliased in dead-letter | **State aliasing** | Obvious on inspection |
| Error overwrite (`context["error"] = e`) | **Implicit last-write-wins** | Obvious on inspection |
| Middleware return type unchecked | **Missing contract** | Visible only when you add the check |
| Handler identity undefined | **Missing model** | Visible only when you try to attribute failures |
| Handlers as pipeline vs. independent subscribers | **Undeclared semantics** | Visible only when you add isolation |
