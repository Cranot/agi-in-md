# Cultivation Analysis: Tenacity Retry Library

## Seed 1 — New Requirement: Async/await support

**Plant**: Add native `async def` function retry with `asyncio.sleep`.

**What must change**:
- `Retrying.__call__` — needs `AsyncRetrying` variant with `await fn(*args, **kwargs)`
- `self.sleep(do)` — must become `await asyncio.sleep(do)` in async path
- `BaseRetrying.__iter__` — the generator protocol doesn't compose with async; needs `__aiter__`
- `wraps()` — must detect coroutines and wrap differently
- `AttemptManager.__exit__` — can't handle async exceptions; needs `__aenter__`/`__aexit__`

**What resists**:
The action chain pattern (`_add_action_func` appending lambdas to a list) is **synchronously baked**. Each action returns a value, not a coroutine. The dispatch in `iter()` does `result = action(retry_state)` — no await point exists. To add async, you'd need parallel action chains or a complete rewrite to async generators.

**Casualties**: The elegant single-path `iter()` method that handles all control flow.

---

## Seed 2 — Contradictory Requirement: Return-value-based retry (no exceptions)

**Plant**: Retry on specific return values (e.g., `None`, `False`, `-1`), not just exceptions.

**Battle lines**:
- `Future.failed` property: `return self.exception() is not None` — **takes exception side**
- `RetryError.reraise()`: `if self.last_attempt.failed: raise self.last_attempt.result()` — assumes result is throwable
- `_post_retry_check_actions`: handles `RetrySignal` as an exception type
- The entire `outcome` model: success = set_result, failure = set_exception

**What must be sacrificed**:
The binary `failed` property itself. You'd need `failed_exceptionally` vs `failed_by_return_value`, or replace the exception-centric `Future` with a unified `Outcome[T]` type that carries either success, exception-failure, or value-failure.

**The conflict**: The library treats **exception as the only failure signal**. Return-value retry makes "success" and "failure" negotiated between caller and strategy, breaking `Future`'s invariant.

---

## Seed 3 — Scaling Requirement: 10,000 concurrent retry loops

**What wilts first**:
- `IterState.actions` list — rebuilt every iteration with fresh closures; 10K loops × N attempts = millions of short-lived lambda objects
- Context variable lookup (`_iter_state_var.get()`) on every action execution — contention-free but allocation-heavy
- `statistics` dict per thread — survives 100 iterations then clears, but 10K threads = 10K dicts

**What's surprisingly resilient**:
- Strategy functions (`stop`, `wait`, `retry`) — stateless callables, no allocation per use
- `RetryCallState` — plain dataclass, no hidden costs
- The core `while True` loop — just control flow, no hidden complexity

**What was already overbuilt**:
- `copy()` method creates a full object copy per wrapped call — defensive but expensive
- The entire action chain machinery is more flexible than needed for the actual use cases

---

## Harvest

All three seeds reveal: **Control flow is mediated through closure chains over a mutable outcome object.**

The structural constant: The code optimizes for **strategy configurability** by indirection through lambdas stored in lists, at the cost of **execution model rigidity**. Async doesn't fit because actions aren't awaitable. Return-value retry doesn't fit because outcomes are exception-typed. Scaling suffers because actions are freshly allocated each iteration.

---

## Derive

**Conservation Law**: Strategy extensibility × Execution model flexibility = constant

The library buys plug-in strategies (stop, wait, retry, before, after, before_sleep) by committing hard to a synchronous, exception-based, closure-chained execution model. Every strategy point is a flexibility gain that locks in a rigidity elsewhere.

---

## Diagnostic

**What this cultivation conceals**: I focused on structural constraints, not domain fitness. The library is actually **well-adapted to its niche** — synchronous Python code with exception-driven retry. The "problems" I identified are only problems if you want to leave that niche.

**Seed that would break the conservation law**: **A state-machine-based retry core** where strategies return tokens (RETRY, STOP, YIELD) instead of being called as closures. This would allow async tokens, return-value tokens, and pre-allocated state machines — gaining extensibility AND execution flexibility simultaneously. The law holds only because the current architecture conjoins strategy invocation with control flow.
