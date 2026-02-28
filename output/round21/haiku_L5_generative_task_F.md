# Structural Analysis: EventBus Implementation

## Pattern Name
**Pub/Sub with Middleware Chain + Dead Letter Queue**

This instantiates three entangled patterns: Observer (event distribution), Chain of Responsibility (middleware), and Error Recovery (dead letter). The novelty is their coupling.

---

## Three Analytical Operations (Derived from THIS Structure)

### Operation 1: Flow-Path Saturation Mapping
*Concrete level — where can events get lost?*

Trace every execution path to terminal states:
```
Event → Middleware (cancellation point) 
      → No handlers? → Dead letter [LOSS POINT 1]
      → Handler error? → Dead letter [LOSS POINT 2]
      → Handler success? → results[] [RETENTION]
```

**Finding:** Events CAN disappear silently (dead letter) but handlers can partially fail (some succeed, some fail, context is poisoned anyway).

---

### Operation 2: Invariant-Violation Detection  
*Medium abstraction — what promises does the code break?*

The code implies but doesn't maintain:
- **Promise:** Handlers execute in priority order
  - **Reality:** Same priority = unstable order (dict + append)
  
- **Promise:** Dead letter = error recovery 
  - **Reality:** Mixed semantics (no handlers ≠ handler failure, but both send to dead letter)
  
- **Promise:** Middleware can intercept and transform
  - **Reality:** Only pre-handlers; can't inspect handler results or post-process

---

### Operation 3: Responsibility Entanglement Analysis
*High abstraction — what should be separate?*

Four distinct concerns fused into one emit() cycle:

| Concern | Current | Should Be |
|---------|---------|-----------|
| Registration | `on()` + `use()` separate | ✓ isolated |
| Middleware | Pre-processing only | Bidirectional pipeline |
| Handler invocation | Error → dead letter mixed | Distinct paths |
| Recovery semantics | One dead letter queue | Separate missing-handler vs. failed-handler buckets |

---

## The Inverted Question: What Can't This Frame Reveal?

Your analysis lens is **structural/architectural**. It *cannot* answer:

**Missing Operation: Semantic Validation**

- *What does success mean for THIS event?* (Requires domain knowledge)
- *Are handlers idempotent?* (Requires behavioral inspection)
- *Can handlers be safely retried from dead letter?* (Requires intent of the handlers)

You'd need a **secondary frame**: map code structure → domain contracts → verify alignment.

**Example blind spot:**
```python
self._dead_letter.append(context)  # Recoverable? Unknown.
```
Structurally: "Events are stored." Semantically: "Can this event be replayed? Are handlers side-effect-free?" — *unspeakable in your frame*.

---

**Recommendation:** Add a fourth analytical operation: **replay-safety inference** — identify which dead-lettered events are deterministic enough to retry without external state mutation.
