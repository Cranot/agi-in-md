# Archaeological Excavation: Tenacity Retry Library

## Layer 1 — Surface

A retry orchestration library exposing `@retry` decorator and strategy composition. Public API: decorate a function, configure stop/wait/retry predicates, optionally hook into before/after/before_sleep callbacks. Two execution paths: direct call via `Retrying.__call__` or generator protocol via `BaseRetrying.__iter__`. Tracks attempt history through `RetryCallState`, accumulates statistics per-thread. The design promises: compose strategies, inspect state, control execution flow.

## Layer 2 — Foundation

**The primitive tokens**: `DoAttempt` and `DoSleep`.

These two sentinel classes — one empty, one inheriting from `float` — are the bedrock. Everything else is scaffolding around them. The foundational decision: control flow as *token emission*, not exception throwing or boolean returns. The loop emits `DoAttempt` → user code runs → loop emits `DoSleep` → wait → repeat. This token-based protocol enables the dual execution models (iterator and direct call) to share logic.

Evidence: they're minimal, almost not classes at all. No configuration, no behavior. Pure identity objects. The entire `iter()` method exists to produce one of these three things: `DoAttempt`, `DoSleep`, or a final result.

## Layer 3 — Sediment

**Stratum A — Action Queue (newest)**: `IterState.actions` as deferred execution. Instead of direct calls, functions are appended to a list and executed in sequence. This accumulated to handle the complex branching between retry/no-retry/stop cases. Creates implicit coupling through closures.

**Stratum B — Context Variables**: `_iter_state_var` threading state through call stacks without parameter passing. Added for async/coroutine support where thread-local fails. Coexists uneasily with `threading.local` for statistics.

**Stratum C — Explicit Retry Bypass**: `RetrySignal` exception and `is_explicit_retry` flag. Users demanded forced retries outside strategy predicates. This sidesteps the strategy composition model — a pressure valve that accumulated rather than redesigned.

**Stratum D — Copy/Configuration Explosion**: The `copy()` method with 13 parameters and `_unset`/`_first_set` pattern. Each new strategy hook (before_sleep, retry_error_callback, name, enabled) left sediment here.

**Stratum E — Statistics Cap**: The `if len() > 100: clear()` in statistics property — defensive code from production memory leak. Preserved accident as policy.

## Layer 4 — Fossils

**`NO_RESULT = object()`**: Defined, never used. Vestigial sentinel from earlier outcome-tracking approach, replaced by `Future` wrapper.

**`RetryAction.REPR_FIELDS` / `NAME`**: Class attributes for a debugging/serialization system never completed. Only `sleep` attribute sees use.

**`RetrySignal` as Exception**: Uses exception for control flow despite token-based architecture. Fossil of pre-token design philosophy — exceptions were the original retry signal. Never fully replaced.

**`AttemptManager._result_set`**: Tracks whether user manually called `set_result()`, but no code path exposes this need. Dead capability.

**Dual execution models themselves**: `Retrying.__call__` and `BaseRetrying.__iter__` duplicate logic. One was probably sufficient; the other accumulated for a use case that may no longer exist.

## Layer 5 — Fault Lines

**Fault A — ContextVar vs threading.local**: `_iter_state_var` (ContextVar) for iteration state, `self._local` (threading.local) for statistics. These solve context isolation differently. In async scenarios, threading.local silently fails while ContextVar works. The split reveals incomplete migration to async-aware design.

**Fault B — Action List Closure Coupling**: Functions appended to `iter_state.actions` close over `self` and `retry_state`. The execution happens later, potentially in different context. Implicit dependencies hide in closures.

**Fault C — Statistics Divergence**: `RetryCallState.idle_for` and `statistics["idle_for"]` track identical data. They're updated together but stored separately. A change to one without the other creates silent corruption.

**Fault D — Explicit Retry Bypasses Strategy**: When `is_explicit_retry=True`, the `retry=` predicate is skipped entirely. Two parallel decision paths for "should retry" violate the strategy composition promise.

---

## Derive: Conservation Law

**Attempt Number × Outcome = Decision**

Across every geological layer — from primitive tokens to action queues to explicit retry bypasses — one quantity is conserved: the retry decision is determined entirely by the attempt count and the outcome. No random factors, no external state affects the pure function:

```
(attempt_number, outcome_exception_or_value) → {continue, stop, retry}
```

The tokens (`DoAttempt`, `DoSleep`, result) are just encodings of this decision. The action queue is deferred execution of this decision. The strategies are predicates on this decision. Everything preserves the invariant: same history, same decision.

---

## Diagnostic: What This Excavation Conceals

My analysis presents geological certainty but the actual history is invisible:

1. **I can't see git history** — my "foundation" might be wrong. `DoAttempt`/`DoSleep` could be refactoring artifacts, not original bedrock.

2. **I can't see `AsyncRetrying`** — the full file has an async implementation. ContextVars make sense there; threading.local is the fossil, not the future.

3. **I can't see strategy classes** — `stop_never`, `wait_none`, `retry_if_exception_type()` are referenced but not defined. Their design would reveal the original composition vision.

4. **I've naturalized accidents as layers** — the 100-entry statistics cap might be one person's PR, not a meaningful stratum.

5. **I've concealed the user** — real archaeology studies people. This code serves developers with flaky network calls, timeouts, rate limits. The geological metaphor hides that every "sediment" was someone trying to solve a real failure mode.

The deepest concealment: treating code as artifact rather than conversation. Every layer was someone's "best solution" to a pressure I can infer but never fully know.
