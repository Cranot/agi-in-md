# Recursive Falsification Analysis of `EventBus`

## Round 1: Initial Falsifiable Claim

> **Claim 1:** The deepest structural problem is that `context` is a shared mutable reference serving simultaneously as middleware communication channel, live processing state, error record, dead-letter archive entry, and return value — creating an aliasing defect where mutation at any stage silently corrupts all others.

### Three Experts Test This Claim

**Defender:** The evidence is concrete. Consider this execution trace:

```python
bus = EventBus()
bus.on("x", handler_a)          # succeeds, appends to results
bus.on("x", handler_b)          # raises ValueError
bus.on("x", handler_c)          # succeeds — but context["error"] is still set

bus.emit("x", {"data": 1})
```

When `handler_b` fails, the code does `self._dead_letter.append(context)` — appending a *reference*, not a snapshot. Then `handler_c` runs, mutating the same dict. The dead-letter entry is now corrupted. Worse, `context["error"]` persists into `handler_c`'s execution, polluting its input. The caller gets back a `context` where `"error"` is set *and* `"results"` contains successful outcomes — an incoherent state.

**Attacker:** This is a bug, not a structural problem. You fix it with `self._dead_letter.append(dict(context))` and a `context.pop("error")` after recording. The *structural* problem lies elsewhere: the dead-letter queue conflates two fundamentally different failure modes:

1. **No handlers registered** → the event is genuinely undeliverable
2. **A handler among several threw** → a *partial success* that demands different recovery

These require categorically different responses, yet they land in the same `_dead_letter` list with no way to distinguish them. That's a design-level semantic gap, not a mutation bug.

**Prober (examines what both take for granted):** You both assume `emit()` is non-reentrant. Nothing enforces this. If `handler_a` calls `bus.emit("y", ...)` internally:

```
emit("x")
  → middleware runs for "x"
    → handler_a runs
      → emit("y")                    ← reentrant call
        → middleware runs for "y"    ← same middleware list, maybe stateful
        → handler for "y" fails
        → dead_letter gets "y"'s context
      ← returns
    → handler_b runs for "x"
```

The middleware pipeline is shared and unguarded. A stateful middleware (e.g., a rate limiter that mutates its own closure) will see interleaved calls from different causal chains. The dead-letter list now mixes entries from different causal depths with no way to reconstruct which emission triggered which. **The code implicitly assumes a linear, non-reentrant processing model but provides no mechanism to enforce or even detect reentrance.**

### Transformed Understanding

The aliasing bug is real but mechanical. What it *symptomizes* is that the code has **no concept of an event-processing lifecycle as a first-class entity**. There's no isolation boundary between processing stages, no identity for a given emission, and no protection against reentrance. The `context` dict is ad-hoc precisely because no lifecycle object exists to own it.

---

## Round 2: The Deeper Claim (unreachable from single-pass analysis)

> **Claim 2:** The EventBus lacks **causal identity** — it cannot represent, distinguish, or track the distinct outcome states its own operations produce. This is not a bug to fix but a missing ontological concept that makes correct error recovery *unrepresentable* within the current design.

Here's what I mean concretely. A single `emit("x", data)` call can produce **four** categorically different outcomes:

| Outcome | What happened | What dead-letter should mean | What actually happens |
|---|---|---|---|
| Clean delivery | All handlers succeed | Nothing recorded | ✓ Works |
| Undeliverable | No handlers registered | "Route this event elsewhere" | Recorded, but indistinguishable from case 3 |
| Partial failure | Handler 2 of 4 throws | "Some succeeded, one failed, investigate" | Same list, same shape, no success record |
| Middleware cancellation | Middleware sets `cancelled` | Nothing recorded (but *why* is lost) | Returns early, no trace at all |

The system needs four distinct outcome types. It has one: a mutating dict. No amount of defensive copying fixes this because **the vocabulary to express these states doesn't exist in the design**. You'd need something like:

```python
@dataclass
class EmitResult:
    emission_id: UUID           # causal identity
    event_type: str
    outcome: Outcome            # DELIVERED | UNDELIVERABLE | PARTIAL_FAILURE | CANCELLED
    succeeded: list[HandlerResult]
    failed: list[HandlerFailure]
    cancellation_reason: str | None
    parent_emission_id: UUID | None   # reentrance tracking
```

This isn't an incremental improvement — it's a different *ontology*.

---

## What the Distance Between Claims Reveals

| | Claim 1 | Claim 2 |
|---|---|---|
| **Level** | Mechanical (data structure) | Ontological (domain model) |
| **Fix** | Copy dicts, clear fields | Redesign around outcome types and causal identity |
| **Detectable by** | Reading the code once | Only after understanding *why* the mechanical fix is insufficient |

**Claim 2 is categorically deeper**, not a refinement. Claim 1 says "this dict is shared when it shouldn't be." Claim 2 says "a dict is the wrong *kind of thing* to represent what this system needs."

The distance between them reveals the core limit of single-pass analysis: **a single reading finds what the code *does wrong*; it takes adversarial recursion to find what the code *cannot express*.** The most important structural defects aren't incorrect behaviors — they're missing concepts that would make correct behavior representable in the first place.
