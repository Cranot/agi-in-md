## The Dialectic

**Defender** — The claim is correct. `emit()` returns the mutated `context` dict directly, leaking `results`, `error`, and `cancelled` as execution artifacts. Every middleware that adds a key makes that key visible to callers who never asked for it. The command (dispatch) and query (what happened) are inseparable. CQS is violated by construction.

**Attacker** — The claim names a symptom. Every event bus has CQS tension — dispatching *is* querying when you need delivery confirmation. The actual disease is subtler: all handlers share the same mutable context object in sequence, so Handler 1 can write state that changes Handler 2's behavior. Handler ordering becomes load-bearing but is only implicitly specified by priority. Worse: `context["error"] = e` overwrites silently on each exception — only the last error survives, while the loop continues processing. The dict leaking is downstream of a broken execution model.

**Prober** — Both of you assume `context` has one purpose being misused. But consider: the dict serves three structurally distinct protocols simultaneously. (1) Event envelope: `type` + `payload`. (2) Pipeline control signal: `cancelled`. (3) Execution audit trail: `results`, `error`. These roles have incompatible invariants — the audit trail grows *after* middleware runs; the pipeline control signal is only meaningful *during* middleware. Neither of you asked why three incompatible protocols inhabit one namespace.

---

## Claim Transformation

The original claim: *mutable context = CQS violation*. After the dialectic: the problem isn't mutation per se — it's that the context dict is an **untyped accumulator serving three distinct communication protocols** with no structural boundary between them. The mutation is the mechanism; the missing phase boundaries are the disease.

**The gap:** The original claim focused on the return value leaking state outward. What actually happens is that the context accumulates *inward* meaning: it begins as an event envelope, becomes a pipeline control object, then transforms into an audit log — all through side-effect, all within the same namespace. No single operation introduces the problem; it emerges from the sequence of individually reasonable mutations.

---

## Concealment Mechanism: Semantic Accretion Camouflage

Each individual mutation looks local and justified. Middleware reads `cancelled`, writes to `cancelled` — reasonable. Handler results append to `results` — reasonable. An exception writes to `error` — reasonable. But no single operation reveals that the dict is simultaneously three different things. The accumulation of meaning across execution phases is the concealment: every step looks like a natural extension of the previous step, so the tripartite protocol structure is never visible at any single inspection point.

**Applied to this specific code, it hides:**
1. The middleware-to-handler phase transition — the same dict that carries pipeline control (`cancelled`) later carries handler outputs (`results`), making two asymmetric phases (middleware transforms events; handlers observe them) look symmetric
2. Error handling is positional replacement: `context["error"] = e` silently overwrites every prior exception while `_dead_letter` captures each iteration's context, creating divergent records of what failed
3. Cancelled and dead-letter events both `return context` at structurally different pipeline stages but look identical at the call site, hiding that suppression and routing failure are different failure semantics

---

## Improvement 1: Typed Return Value

```python
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class DispatchResult:
    """Clean return type — callers see outcomes, not pipeline internals."""
    event_type: str
    cancelled: bool
    delivered: bool
    has_errors: bool
    handler_count: int

class EventContext:
    """Internal pipeline context. Deliberately opaque to callers."""
    def __init__(self, event_type: str, payload: Any):
        self._data = {"type": event_type, "payload": payload, "cancelled": False}

    def __getitem__(self, key): return self._data[key]
    def __setitem__(self, key, value): self._data[key] = value
    def get(self, key, default=None): return self._data.get(key, default)

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

    def emit(self, event_type, payload) -> DispatchResult:
        context = EventContext(event_type, payload)
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return DispatchResult(event_type, cancelled=True,
                                      delivered=False, has_errors=False, handler_count=0)
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(context)
            return DispatchResult(event_type, cancelled=False,
                                  delivered=False, has_errors=False, handler_count=0)
        results = []
        has_errors = False
        for _, handler in handlers:
            try:
                results.append(handler(context))
            except Exception as e:
                has_errors = True
                context["error"] = e          # ← original bug preserved inside wrapper
                self._dead_letter.append(context)
        context["results"] = results
        return DispatchResult(event_type, cancelled=False,
                              delivered=True, has_errors=has_errors,
                              handler_count=len(results))
```

This passes code review: frozen return type, named internal wrapper, clean caller API.

**Three properties visible only because I tried to strengthen it:**

1. **`emit()` is three functions sharing one name.** Designing `DispatchResult` forced a decision about what to put in three structurally different instances: cancellation (`handler_count=0`, meaningful), routing failure (`delivered=False`, semantically ambiguous — is finding no handlers an error?), and normal delivery. The frozen dataclass unifies all three exits, but `has_errors=False` on the dead-letter path is technically correct and semantically wrong — it looks like success when it's a routing miss. The improvement exposed that the three exits aren't three states of one operation.

2. **Handler-to-handler contamination is now legitimized.** `EventContext` wraps the dict but makes it look *intentionally* opaque. Handlers still receive this mutable object and can write to it, affecting subsequent handlers. Previously this looked accidental (raw dict mutation). Now it looks designed (a named internal type). The bug that handlers share a mutable context has been upgraded to a "feature."

3. **The error-overwrites-error bug became split-brain.** `has_errors = True` is now tracked correctly in a local variable, while `context["error"] = e` still replaces the previous error inside `EventContext`. `DispatchResult.has_errors` is truthful; the context held by `_dead_letter` entries is not. The improvement separated the error truth across two artifacts — the boolean (correct) and the key (last-error-only) — making the inconsistency invisible while each artifact looks correct individually.

---

## Diagnostic Applied to Improvement 1

**What it conceals:** `DispatchResult` gives all three exit paths the same type. But suppression (middleware cancelled), routing failure (no handlers), and execution (handlers ran) happen at different pipeline stages with different information available. A single struct cannot represent all three without field meanings diverging by path. The improvement hides this by making all three look like the same operation with different boolean flags.

**What property of the original is visible only because the improvement recreates it:** The original returned `context` at three points with different semantic contents. Improvement 1 returns `DispatchResult` at three points with fields that mean different things in each context. The recreation reveals: **the three exit paths of `emit()` are not implementation details — they are the fundamental structure of dispatch semantics.** No return type can unify them without losing information. Improvement 1 didn't fix the underlying structure; it gave it a type annotation.

---

## Improvement 2: Algebraic Exit Types

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Union

@dataclass(frozen=True)
class Suppressed:
    """Middleware cancelled dispatch before any handler ran."""
    event_type: str

@dataclass(frozen=True)
class Unroutable:
    """No handlers registered. Event preserved for dead-letter inspection."""
    event_type: str
    payload: Any

@dataclass(frozen=True)
class Executed:
    """Handlers ran. Results and errors are separate, complete lists."""
    event_type: str
    results: List[Any]
    errors: List[Exception]

    @property
    def succeeded(self) -> bool:
        return bool(self.results) and not self.errors

DispatchOutcome = Union[Suppressed, Unroutable, Executed]

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

    def emit(self, event_type, payload) -> DispatchOutcome:
        context = {"type": event_type, "payload": payload, "cancelled": False}
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return Suppressed(event_type)
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append({"type": event_type, "payload": payload})
            return Unroutable(event_type, payload)
        results, errors = [], []
        for _, handler in handlers:
            try:
                results.append(handler(context))
            except Exception as e:
                errors.append(e)
                self._dead_letter.append({**context, "error": e})
        return Executed(event_type, results, errors)
```

**Diagnostic applied to Improvement 2:**

This fixes two concrete bugs: errors accumulate rather than overwrite; exit paths carry distinct types. The output boundary is clean. But the *input* boundary remains broken: the `context` dict passed to every handler is shared and mutable, with a schema determined entirely at runtime by whichever middleware executed. A middleware that sets `context["user"] = authenticate(...)` creates a convention that every handler must know about via string literal. The algebraic output types are typed. The middleware-to-handler channel is not.

---

## The Structural Invariant

Through every version — original, Improvement 1, Improvement 2 — one property persists: **the context passed to handlers carries information injected by middleware, accessible only through string key conventions. The handler must already know what middleware added in order to use it.**

This is not a quality problem. It is a logical consequence of extensibility: if any middleware can augment the context with any key, the set of keys is open at design time, so no static type can represent it. Open middleware extension and typed handler input are mutually exclusive within this architecture.

---

## Inverting the Invariant

**Invariant:** Open middleware extension requires an untyped middleware-to-handler channel.

**Inverted design:** Each middleware declares its exact input and output types statically. The bus carries a type parameter representing the current context schema:

```python
from typing import Generic, TypeVar

CtxIn = TypeVar('CtxIn')
CtxOut = TypeVar('CtxOut')

class TypedBus(Generic[CtxT]):
    def use(self, mw: Middleware[CtxT, CtxU]) -> 'TypedBus[CtxU]':
        """Returns a NEW bus with refined context type."""
        ...
    def emit(self, event_type: str, payload: Any) -> DispatchOutcome:
        ...  # context is fully typed as CtxT for all registered handlers
```

Adding `AuthMiddleware[BaseCtx, AuthCtx]` transforms the bus from `TypedBus[BaseCtx]` to `TypedBus[AuthCtx]`. Every handler's input type is now fully specified. Type safety is complete.

**The new impossibility:** `use()` now returns a new bus with a new type — middleware composition is a compile-time type transformation, not a runtime append. You cannot call `bus.use(new_middleware)` after handlers register, because this would invalidate every handler's expected input type. Dynamic middleware registration — the entire point of the `use()` method — becomes impossible without type erasure. Middleware stack must be finalized before any handler can register. The original's runtime `self._middleware.append(middleware_fn)` is categorically unavailable.

---

## Conservation Law

**Original impossibility:** Open middleware extension → untyped channel → handlers cannot know what middleware added at compile time  
**Inverted impossibility:** Typed channel → locked middleware composition → middleware cannot be added after handler registration

**Conservation law:** `middleware_openness × handler_type_safety = constant`

For this EventBus architecture: the total implicit knowledge required between middleware and handlers is conserved. Gaining type safety relocates that knowledge into type definitions — explicit but rigid. Gaining runtime configurability relocates it into string key conventions — flexible but implicit. The knowledge cannot be eliminated; only its representation changes.

---

## Diagnostic Applied to the Conservation Law

**What the law conceals:** It frames the problem as a two-party trade-off: middleware authors (who want openness) versus handler authors (who want safety). But it conceals a third party — the **bus operator**, who configures the middleware stack and must ensure handlers are compatible with whatever was configured. Both costs fall on this one actor in most deployments. The operator who registers `AuthMiddleware` is responsible for both the runtime flexibility and the broken type contracts in every handler. The law treats these as opposing forces held by opposing parties; in practice they're the same person's problems.

More precisely: the law conceals that "implicit knowledge" has a specific *location* in this code. It is not distributed abstractly across a trade-off space. It lives in **string key literals**: `context["user"]`, `context["error"]`, `context["cancelled"]`, `context["results"]`. These literals *are* the schema. Every architectural improvement transforms them into something else (class attributes, type annotations, protocol methods), but the string literals are the actual interface. The conservation law describes a principle; the code contains a specific, countable set of commitments.

**Structural invariant of the conservation law itself:** When I try to improve the law — add the third party, reformulate it, change the quantities — one form persists: it always describes a trade-off between two properties, but which two properties I select depends on which stakeholder's problem I center. From the type system frame: `openness × safety = k`. From the deployment frame: `flexibility × lock-in = k`. From the schema frame: `implicit × explicit encoding = k`. Every frame produces a valid conservation law. The conservation *form* is frame-invariant; the quantities named within it are not.

**Inverting the invariant of the law:** Find a quantity that is genuinely frame-invariant — conserved regardless of which two properties I select as A and B, regardless of which stakeholder I center.

---

## The Meta-Law

**The frame-invariant quantity:** In every frame, every conservation law I can construct about this EventBus describes the same phenomenon from a different angle: the **count of semantic commitments** between middleware output and handler input. Each distinct key that middleware writes and a handler reads constitutes exactly one commitment. This count is frame-invariant because it is a property of the information flow, not the framing: if `AuthMiddleware` writes `context["user"]` and three handlers call `context.get("user")`, that is one middleware commitment accessed by three handlers — the commitment count is 1, the access count is 3, and no refactoring changes the first number.

**The meta-conservation law:** In this EventBus implementation, the count of semantic commitments between middleware output and handler input is conserved across all architectural improvements. Every string key that middleware writes and any handler reads is one commitment. Typed refactoring transforms each commitment from a string literal into exactly one new artifact — one class attribute, one type annotation, one protocol method. The transformation is 1:1. The total schema obligation between middleware and handlers cannot be reduced by any implementation choice within the event-bus architecture.

**Concrete, testable consequence:**

Add `AuthMiddleware` to the original code:

```python
def auth_middleware(context):
    context["user"] = authenticate(context["payload"].get("token"))
    return context
```

Count every distinct string key access in handler code that depends on what middleware injected: `context["user"]`, `context.get("user", None)`, etc. For a single middleware adding one field, S = 1.

Now migrate to any improved design — `EventContext` class wrapper, algebraic return types, or phantom-type chain. Count the new artifacts encoding the `user` commitment: the class attribute `ctx.user`, the type annotation `user: User`, the protocol method `get_user() -> User`, the adapter field `AuthCtx(BaseCtx, user=...)`.

**Prediction:** The post-migration artifact count will equal S. One middleware commitment produces exactly one new typed artifact. Adding a second middleware field (`context["permissions"]`) will require exactly one additional artifact in any improved design. No migration produces fewer artifacts than there are committed keys.

The only exception: eliminating S requires removing the information asymmetry itself — making handlers independent of what middleware injects. This requires either (a) middleware becoming a typed event factory rather than a context mutator, or (b) merging middleware and handler execution. Both moves dissolve the EventBus pattern entirely. The commitment count is not a defect — it is the minimum description complexity of middleware-augmented dispatch. Any implementation that appears to reduce it has moved the commitments somewhere the count isn't being taken.
