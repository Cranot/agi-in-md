## Level 7 Diagnostic Analysis: Tenacity

---

### I. The Falsifiable Claim

> **The deepest structural problem is that `IterState.actions` simultaneously serves as a data container and a live execution stack — actions append new actions to the list they are currently iterating over — encoding control flow as a runtime mutation contract with no structural enforcement.**

The `iter()` loop iterates over `self.iter_state.actions` while `_post_retry_check_actions` and `_post_stop_check_actions` append new entries to it mid-iteration. Python's `for`-over-list implementation (index-based) picks up these additions — a behavior relied on silently, without comment. Execution order is an artifact of mutation order, not of any type or structural constraint.

---

### II. The Dialectic

#### Expert 1 — Defender
> "This is deliberate continuation-passing style, adapted for Python. The mutation pattern is more composable than nested conditionals: concerns are separated across methods, the action queue can be inspected mid-execution, and new strategies can be inserted without rewriting branch logic. The ordering contracts are stable and encoded by the method names themselves. Calling this a 'problem' ignores that it works correctly."

#### Expert 2 — Attacker
> "The claim misidentifies the symptom. The action queue is peculiar but functional. The structural failure is in `wraps()`. `copy = self.copy()` creates a fresh `Retrying` with its own `_local`, but then:"
> ```python
> wrapped_f.statistics = copy.statistics
> self._local.statistics = copy.statistics  # aliases copy's dict onto original's _local
> return copy(f, *args, **kw)
> ```
> "Now `self._local.statistics` and `copy._local.statistics` point to the same dict. When `copy.begin()` calls `self.statistics.clear()`, it clears through both references. And `wrapped_f.statistics` is non-atomic: two threads calling `wrapped_f` simultaneously race to overwrite it, and one thread's statistics are silently lost. The action queue is irrelevant; the ownership of state is broken."

#### Expert 3 — Prober (attacks shared assumptions)
> "Both of you assume thread-safety is the primary register of analysis. Step back: *why* does this code implement both `__iter__` and `__call__`? They contain the same state machine, written twice:"
> ```
> while True:
>     do = self.iter(retry_state)
>     if isinstance(do, DoAttempt): ...
>     elif isinstance(do, DoSleep): ...
>     else: break/return/yield
> ```
> "The `__iter__` path uses `self` directly — no copy, no isolation. The `__call__` path creates no special state either. The action queue exists *because* the code is trying to extract the state machine into something both contexts can share, without resolving which context is canonical. The action queue mutation pattern is a consequence of an unresolved architectural commitment, not the root cause."

---

### III. The Transformed Claim

**Original:** Action queue mutation creates indeterminate control flow.

**Transformed:** `BaseRetrying` simultaneously acts as a factory, a strategy container, and an execution context, without committing to any one identity. Two parallel execution models — `__iter__` (cooperative) and `__call__` (blocking) — each implement the same state machine, sharing thread-local state through an object that was never designed to own it. The action queue mutation pattern is an attempt to extract the state machine across both contexts without resolving the ownership question — and the attempt is incomplete.

---

### IV. The Diagnostic Gap

**The gap:** From *"visible structural anomaly in the action queue"* → *"unresolved identity of `BaseRetrying` driving dual-model duplication."*

**What it reveals:** The original claim was attracted to the most *locally visible* strangeness. The dialectic showed that this strangeness is downstream of something less visible: `BaseRetrying` never decides what it *is*, and all the patterns in the code exist to defer that decision.

---

### V. The Concealment Mechanism: **Pattern Density as Architectural Alibi**

The code simultaneously deploys:

| Pattern | Local Justification |
|---|---|
| Strategy pattern (`stop`, `wait`, `retry`) | Composable retry policies |
| Command pattern (action queue) | Deferred, inspectable execution |
| Thread-local storage | Per-thread statistics isolation |
| Sentinel objects (`DoAttempt`, `DoSleep`, `_unset`, `NO_RESULT`) | Type-safe control flow tokens |
| Iterator protocol (`__iter__`) | Cooperative/async adapter |
| Decorator pattern (`wraps`, `retry_with`) | Non-invasive wrapping |

Each pattern is locally reasonable. Together they function as an alibi: the code *looks* architecturally considered. The sheer number of patterns trains the analyst to evaluate each one in isolation — "is the thread-local use correct?" "is the mutation pattern valid?" — rather than asking the organizing question: *what is this object?*

The alibi is effective precisely because there is something to defend at every level. No pattern is obviously wrong. The wrongness is in what the patterns collectively conceal: **`BaseRetrying` has three incompatible identities and no resolution.**

---

### VI. What the Entire Dialectic Failed to Surface

All three experts — defender, attacker, prober — debated the action queue, the statistics aliasing, and the dual execution model. None asked: *what happens if the machinery itself fails?*

Every action handler is called inside `iter()` with no exception isolation:

```python
def iter(self, retry_state):
    self._begin_iter(retry_state)
    result = None
    for action in self.iter_state.actions:
        result = action(retry_state)  # no try/except anywhere
    return result
```

The strategy callables — `self.wait`, `self.stop`, `self.retry`, `self.before`, `self.after`, `self.before_sleep` — are all invoked here. If any of them raises:

1. The exception propagates through `iter()` into `__call__` or `__iter__`
2. It emerges **indistinguishable from the wrapped function's own exception**
3. It leaves `IterState`, `RetryCallState`, and `statistics` in partially-mutated states, because the action list was half-executed
4. The calling code has no mechanism to distinguish "my function failed" from "your retry machinery failed"

This is the final irony that pattern density concealed: **a library built to make code robust to failure has no error handling for failures in its own extension points.** The `wait` strategy could divide by zero. The `before` hook could raise an `AttributeError`. The `stop` strategy could have a bug. In every case, the retry framework — which exists to reason about failure — silently corrupts its own state and misattributes its own errors.

The dialectic missed this because all three experts were debating the action queue *as a mechanism* and the threading model *as a correctness domain*. The concealment mechanism — pattern density — ensured that the question "what if the patterns themselves fail?" never became salient. The library's implicit contract is that strategies are correct; the question of what happens when they aren't was never surfaced, because the elaborate machinery for handling function failures made it *look* like failure was already handled.

The code is a retry library that cannot retry its own failures.
