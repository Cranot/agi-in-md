## Analysis: EventBus Patterns and Problems

### Patterns Present

| Pattern | Where | Purpose |
|---|---|---|
| Observer / Pub-Sub | `on()` / `emit()` | Decoupled event dispatch |
| Middleware Pipeline | `use()` / emit loop | Pre-handler transformation |
| Dead Letter Queue | `_dead_letter` | Absorb unhandled/failed events |
| Priority Queue | `sort(key=lambda x: -x[0])` | Ordered handler execution |
| Context Envelope | `context` dict | Shared mutable state across chain |

---

### The Concealment Mechanism: **Silent Error Laundering**

The `context` dict is an identity-state-result conflation envelope. It makes a failed emission *look like* a successful one:

```python
# Caller sees this — looks fine
result = bus.emit("payment.processed", data)

# But silently, inside emit():
context["error"] = e          # last error only, overwrites previous
self._dead_letter.append(context)  # failure disappears here
# ...execution continues anyway
```

The dict conceals three distinct things under one surface: **the event's identity**, **its processing state**, and **its accumulated results**. The caller cannot distinguish success from silent failure without inspecting internals.

---

### Problems (Ranked by Severity)

**Critical**

```python
# 1. Middleware chain silently voids on None return
context = mw(context)   # if mw() returns None → AttributeError on next mw
                         # or worse: None propagates, handlers get None

# 2. Handler errors poison shared context for subsequent handlers
for _, handler in handlers:
    try:
        results.append(handler(context))
    except Exception as e:
        context["error"] = e   # ← mutates context that remaining handlers see
        self._dead_letter.append(context)
        # execution continues — next handler gets error-poisoned context

# 3. Multiple errors: only last survives
context["error"] = e   # previous exception silently discarded
```

**Structural**

```python
# 4. Dead letter conflates two distinct failure modes
self._dead_letter.append(context)  # used for BOTH "no handlers" AND "handler threw"
                                    # semantically incompatible — debugging nightmare

# 5. Sort on every registration — O(n log n) at write time
self._handlers[event_type].sort(...)  # should be insort or sort-at-emit

# 6. Dead letter grows unboundedly — memory leak
self._dead_letter = []  # no eviction, no max-size, no TTL

# 7. No off() method — handlers registered forever
# 8. No intra-handler stopPropagation — only middleware can cancel
# 9. No thread safety
```

---

### Three Properties Visible Only Through Construction

Building this out reveals things the code doesn't state:

1. **Priority is eager, not lazy** — ordering is computed at `on()` time, so handlers registered *after* emit don't participate in that emit, even if they'd have higher priority. This is invisible until you register handlers mid-flight.

2. **Dead letter is semantically overloaded** — you only discover that orphaned events and errored events share the same queue when you try to build a dead-letter processor and find you can't distinguish them without inspecting `context.get("error")`.

3. **Middleware can erase event identity** — since `context = mw(context)` reassigns freely, a middleware can return a *completely different* dict with a different `type`. The original event is gone. This is invisible until you write a middleware that transforms event type and discover handlers for the *original* type never fire.

---

### Improved Implementation

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Iterator
import bisect
import threading


# ── Immutable event identity ──────────────────────────────────────────────────

@dataclass(frozen=True)
class Event:
    type: str
    payload: Any


# ── Typed result envelope (separates identity from state) ─────────────────────

@dataclass
class EventResult:
    event: Event                          # identity never mutated
    cancelled: bool = False
    errors: list[tuple[Callable, Exception]] = field(default_factory=list)
    results: list[Any] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return not self.cancelled and not self.errors

    def __iter__(self) -> Iterator[Any]:
        return iter(self.results)


# ── Typed dead letter ─────────────────────────────────────────────────────────

class DeadLetterReason(Enum):
    NO_HANDLERS      = auto()
    MIDDLEWARE_HALT  = auto()
    ALL_HANDLERS_FAILED = auto()
    PARTIAL_FAILURE  = auto()


@dataclass
class DeadLetter:
    result: EventResult
    reason: DeadLetterReason


# ── EventBus ──────────────────────────────────────────────────────────────────

class EventBus:
    _MAX_DEAD_LETTER = 1000

    def __init__(self):
        self._handlers: dict[str, list[tuple[int, Callable]]] = {}
        self._middleware: list[Callable] = []
        self._dead_letter: list[DeadLetter] = []
        self._lock = threading.Lock()

    # ── Registration ──────────────────────────────────────────────────────────

    def on(self, event_type: str, handler: Callable, priority: int = 0) -> Callable:
        """Register handler; returns unsubscribe callable."""
        with self._lock:
            bucket = self._handlers.setdefault(event_type, [])
            entry = (-priority, handler)   # negate for bisect (ascending = highest first)
            bisect.insort(bucket, entry, key=lambda x: x[0])

        def off():
            with self._lock:
                try:
                    bucket.remove(entry)
                except ValueError:
                    pass
        return off

    def use(self, middleware_fn: Callable) -> None:
        self._middleware.append(middleware_fn)

    # ── Emission ──────────────────────────────────────────────────────────────

    def emit(self, event_type: str, payload: Any) -> EventResult:
        event  = Event(type=event_type, payload=payload)
        result = EventResult(event=event)

        # Middleware — each receives (event, result) read-only, returns bool to cancel
        for mw in self._middleware:
            try:
                should_cancel = mw(event, result)
            except Exception as e:
                result.errors.append((mw, e))
                should_cancel = True          # middleware failure halts chain

            if should_cancel:
                result.cancelled = True
                self._archive(DeadLetter(result, DeadLetterReason.MIDDLEWARE_HALT))
                return result

        # Handlers
        with self._lock:
            handlers = list(self._handlers.get(event_type, []))

        if not handlers:
            self._archive(DeadLetter(result, DeadLetterReason.NO_HANDLERS))
            return result

        for _, handler in handlers:
            try:
                result.results.append(handler(event, result))
            except Exception as e:
                result.errors.append((handler, e))   # all errors preserved

        if result.errors:
            reason = (
                DeadLetterReason.ALL_HANDLERS_FAILED
                if len(result.errors) == len(handlers)
                else DeadLetterReason.PARTIAL_FAILURE
            )
            self._archive(DeadLetter(result, reason))

        return result

    # ── Dead letter management ────────────────────────────────────────────────

    def _archive(self, letter: DeadLetter) -> None:
        self._dead_letter.append(letter)
        if len(self._dead_letter) > self._MAX_DEAD_LETTER:
            self._dead_letter = self._dead_letter[-self._MAX_DEAD_LETTER:]

    def drain_dead_letters(
        self,
        reason: DeadLetterReason | None = None
    ) -> list[DeadLetter]:
        with self._lock:
            if reason is None:
                taken, self._dead_letter = self._dead_letter, []
                return taken
            kept, taken = [], []
            for dl in self._dead_letter:
                (taken if dl.reason == reason else kept).append(dl)
            self._dead_letter = kept
            return taken
```

---

### Diagnostic Applied to the Improvement

**What does the improvement conceal?**

The `frozen=True` `Event` dataclass conceals allocation cost — every `emit()` now constructs a new `Event` object. In the original, the dict was reused; here the immutability guarantee silently introduces per-call heap allocation. The improvement also conceals **handler signature breakage**: original handlers accepted `(context)`, improved handlers accept `(event, result)` — migrating is a hidden contract change.

The `bisect.insort` with `key=` conceals a subtle behavior: entries with *equal priority* are ordered by insertion time (stable), but the negation of priority (`-priority`) means the sort key is the *negated* value, so bisect sorts ascending-by-negated = descending-by-actual. This is correct but the inversion is invisible at the call site.

**What property of the original is visible *only because* the improvement recreates it?**

The original's `context` dict was doing triple duty: **event identity + live processing state + result accumulation**. This only becomes *visible as a design flaw* when the improvement separates them into `Event` (frozen identity), `EventResult` (accumulated state), and `DeadLetter` (archival record). Before the separation, the conflation was invisible — it looked like simplicity. The reconstruction reveals it was **load-bearing ambiguity**: the original worked *because* identity and state were merged, since middleware could rewrite event type by mutating the same dict. The improvement's separation makes that capability structurally impossible, exposing that the original implicitly permitted event identity mutation as a (dangerous) feature.
