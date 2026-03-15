## Structure First: Level 8 Diagnostic

---

### Original Falsifiable Claim

> **`AttemptManager.__exit__` always calls `set_result(None)`, permanently discarding the managed function's return value. Any strategy that evaluates the outcome's result receives `None` regardless of what the function actually returned, making result-based retry conditions silently and permanently broken in `__iter__` mode.**

Proof by tracing:

```python
def __exit__(self, exc_type, exc_value, traceback):
    if exc_type is not None and exc_value is not None:
        self.retry_state.set_exception((exc_type, exc_value, traceback))
        return True
    self.retry_state.set_result(None)   # ← always None
    return None
```

Then, in `_post_retry_check_actions`, `self.retry(retry_state)` is called where `self.retry` might be `retry_if_result(lambda r: r is None)`. The strategy calls `retry_state.outcome.result()`, which returns `None`. The condition is `True`. The loop retries. The function may never return `None`, but it retries forever. The strategy definition looks correct. The `AttemptManager` looks correct. The protocol is broken at the seam between them, and neither side shows it.

---

### The Dialectic

**Expert 1 — Defender**

The claim holds. The data path is unambiguous: `set_result(None)` → `Future.set_result(None)` → `retry_state.outcome.result() == None` → any result-checking strategy misfires. The damage isn't limited to `retry_if_result`: `after` callbacks that branch on `retry_state.outcome.result()` to log success values, or custom stop strategies that consider the outcome, all receive `None`. The `__iter__` protocol silently degrades every strategy that touches a successful outcome, and it does so without raising, without warning, and without any observable difference in the stack trace.

**Expert 2 — Attacker**

The original claim calls a design boundary a bug. The `__iter__` / `AttemptManager` protocol was explicitly built for exception-based retry, where the user writes the `try/except` themselves. The `with attempt` block is a context manager, and Python context managers structurally cannot observe their block's return value — `__exit__` receives only exception info. `set_result(None)` is not wrong; it encodes "the block exited normally, no exception." Result-based retry was always a `__call__`-only feature. The original claim should be replaced with a more precise one: **the two protocols share an entire strategy evaluation pipeline but differ in how outcomes are recorded, and this asymmetry is completely invisible at the interface level**. The shared `iter()` state machine, shared `RetryCallState`, shared strategy objects — all of these signal "same protocol, two spellings." The architecture guarantees that they aren't.

**Expert 3 — Prober**

Both experts are arguing about the wrong layer. Expert 1 says "the data is wrong." Expert 2 says "the protocol boundary is expected." Neither has asked why the protocols *look* equivalent. The shared implementation is doing work that no one has named.

Look at what `__iter__` and `__call__` share: the same `iter()` loop driver, the same `_begin_iter`, the same `_post_retry_check_actions`, the same `_post_stop_check_actions`, the same strategy instances. From any inspection point — reading `BaseRetrying`, reading strategy definitions, reading statistics — the two protocols are indistinguishable. The divergence lives in exactly one place: *how outcomes enter `RetryCallState` before the state machine sees them*. In `__call__`, outcomes are captured automatically (`fn(*args) → set_result`). In `__iter__`, outcomes are captured by `AttemptManager.__exit__`, which can't see the return value.

This is a Python-language constraint, not a design choice. `__exit__` cannot observe the expression value of the `with` block. So the architecture has not made a bad decision — it has run into a language boundary and papered over it with `set_result(None)`, which looks correct and is incorrect. The prober's question: *what does it mean for two protocols to share a state machine when they can't share the thing the state machine processes?*

---

### The Transformation

| | |
|---|---|
| **Original claim** | `set_result(None)` corrupts result-based strategy input in `__iter__` mode |
| **Transformed claim** | The Python context manager protocol makes `__iter__` structurally incapable of symmetric outcome capture, and the shared `iter()` state machine conceals this by making both protocols appear to be implementations of the same interface |

These are not the same claim at different zoom levels. The original identifies a wrong value. The transformed identifies a structural impossibility: `AttemptManager` cannot be made symmetric with `Retrying.__call__` without user cooperation, and the architecture does nothing to surface this requirement. The shared state machine actively suppresses the question of whether cooperation is needed.

---

### The Gap Is Itself the Diagnostic

The dialectic traveled from **"wrong value"** to **"Python-protocol-level structural asymmetry concealed by shared implementation."** That gap is large. The original claim is a data observation. The transformed claim is about what the language permits and what the code's structure implies — two different epistemic levels.

The translation was forced by Expert 3's question: *why do the protocols look equivalent?* The shared state machine *does the looking for you*. The reader sees the same `iter()` code, infers "same pipeline," and stops asking whether the inputs to that pipeline were prepared the same way. The concealment does not require any deception. It requires only that the reader trust the shared implementation to signal shared semantics.

---

### The Concealment Mechanism: Implementation Convergence as Semantic Proxy

When two execution paths share a state machine, readers infer they share semantics. The shared `iter()`, shared `RetryCallState`, shared strategy instances, shared `_post_retry_check_actions` — these are not just code reuse. They are signals. A reader encounters the shared pipeline and concludes: "whatever is different between these paths is syntax, not semantics." This inference is wrong and it is the mechanism.

The mechanism is distinct from L7's Signal Substitution. L7 found that a *correct library component* (threading.local, Future) proxies for correctness in a domain it doesn't cover. Here, a *correct implementation decision* (sharing the state machine) proxies for semantic equivalence that cannot exist because of a language-level constraint the implementation never acknowledges. The concealment is not about correctness radiating false completeness — it is about *shared code radiating false symmetry*.

**Applying it:** Anywhere two paths share substantial infrastructure, readers will assume they share semantics. Look for cases where the infrastructure is shared but the *preconditions* for using that infrastructure are not.

Found immediately: `__iter__` creates `RetryCallState(self, fn=None, args=(), kwargs={})`. The `fn`, `args`, and `kwargs` fields are always `None`/empty in `__iter__` mode. Every callback and strategy that receives `retry_state` and accesses `retry_state.fn` or `retry_state.args` receives `None` or `()`. The shared pipeline processes `retry_state` identically in both modes. The divergence exists only in `RetryCallState.__init__`, two lines before the state machine begins. Every strategy that uses function identity, argument logging, or argument-based retry decisions silently operates on missing data. The shared state machine conceals this by consuming `retry_state` as if it were fully populated.

---

### Engineering the Improvement

Add result capture to `AttemptManager`. This is the obvious fix, would pass code review, and deepens concealment by making the two protocols appear more symmetric than they have ever been:

```python
class AttemptManager:
    def __init__(self, retry_state):
        self.retry_state = retry_state
        self._result_recorded = False

    def __enter__(self):
        return self

    def set_result(self, value):
        """Record the attempt's result for evaluation by result-based strategies.

        Required when using retry_if_result with the iterator protocol:

            for attempt in Retrying(retry=retry_if_result(lambda r: r < 0)):
                with attempt as a:
                    value = compute()
                    a.set_result(value)

        Without this call, result-based strategies receive None for all
        successful attempts and will not evaluate correctly.
        """
        self._result_recorded = True
        self.retry_state.set_result(value)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None and exc_value is not None:
            self.retry_state.set_exception((exc_type, exc_value, traceback))
            return True
        if not self._result_recorded:
            self.retry_state.set_result(None)
        return None
```

This passes code review because:
- The docstring is accurate and complete
- The `_result_recorded` flag correctly prevents double-setting
- The fallback `set_result(None)` preserves backward compatibility for exception-only use cases
- The API is minimal and obvious
- `retry_if_result` now works correctly when the user calls `a.set_result(value)`

It deepens concealment because:
- The two protocols now appear genuinely equivalent for result-based retry
- Developer confidence in `__iter__` increases, broadening its use
- The remaining asymmetries — `fn=None`, discarded return values from `iter()`, invalid Future state transitions — become active liabilities in code that previously would never reach them

---

### Three Properties Visible Only Because We Tried to Strengthen It

**1. `retry_state.fn = None` is not an oversight — it is a permanent structural gap that the fix exposes.**

Testing the improved `AttemptManager` with `retry_if_result`, you naturally add companion callbacks. A `before` callback that logs `f"Calling {retry_state.fn.__name__}, attempt {retry_state.attempt_number}"` raises `AttributeError: 'NoneType' object has no attribute '__name__'`. `RetryCallState` is created with `fn=None` in `__iter__` because the user — not the `Retrying` object — holds the callable. The fix enables strategies to make correct *retry decisions* based on results, but those strategies still operate inside a `RetryCallState` that is missing function identity, argument list, and keyword arguments. Any strategy or callback that uses these fields enters an undefined state. Before the fix, result-based strategies always saw `None` and malfunctioned uniformly. After the fix, they work correctly — which means developers now deploy them in production, at which point the `fn=None` gap encounters real code. The fix didn't introduce this property; it made the code reach it for the first time.

**2. `set_result(value)` followed by an exception in cleanup creates an `InvalidStateError` that destroys both the result and the original exception.**

```python
with attempt as a:
    result = compute()
    a.set_result(result)   # Future resolved with result
    finalize()             # raises IOError
```

`__exit__` receives `IOError`. It calls `self.retry_state.set_exception((IOError, ...))`. But `retry_state.outcome` is already a resolved `concurrent.futures.Future`. `Future.set_exception()` on an already-resolved Future raises `concurrent.futures.InvalidStateError`. The `IOError` from `finalize()` is replaced by `InvalidStateError`, whose message reveals nothing about the original error or the previously-set result. Both are gone. Without the `set_result` method, this code path was unreachable — `__exit__` called `set_result(None)` or `set_exception`, never both on a resolved Future. The fix introduced a two-phase outcome protocol (voluntary `set_result` + mandatory `__exit__` check) with no atomicity guarantee. The `_result_recorded` flag is not synchronized with the Future's state machine. The error mode is only reachable because we created the API that makes it reachable.

**3. Result-based *branching decisions* now work correctly, but the value that caused the branching decision is still discarded by `__iter__`'s return loop.**

After the fix, when `retry_if_result(lambda r: r is None)` correctly evaluates a non-`None` result and decides not to retry, `_post_retry_check_actions` adds `lambda rs: rs.outcome.result()` to the action list. `iter()` returns the actual result value. Then `__iter__`'s while loop:

```python
do = self.iter(retry_state=retry_state)
if isinstance(do, DoAttempt): ...
elif isinstance(do, DoSleep): ...
else:
    break
```

The actual result value — correct, non-None, the value that correctly terminated the retry loop — is bound to `do` and then `break` discards it. The loop's caller receives nothing from the generator. The user must capture the value externally, independently of the retry machinery:

```python
final = None
for attempt in retrying:
    with attempt as a:
        final = compute()
        a.set_result(final)
# retry machinery branched on final correctly; user holds final separately
```

The fix separated two concerns that were previously fused (and broken together): *branching on result* (now works) and *returning result* (still broken). Before the fix, both were broken uniformly and the question "what does `__iter__` return on success?" was never relevant. The fix makes branching work, which makes the discarded return value matter for the first time. The property was always present in the `break` statement — it became visible only by making the value worth returning.

---

### What the Entire Dialectic Failed to Surface

The three experts examined result capture, protocol equivalence, and language constraints. None examined what `__iter__` returns on success and what the caller receives. The generator simply ends. The `while True` loop breaks. The return value of the last `iter()` call is discarded. If the retry sequence succeeds on attempt 3, `iter()` returns `the_result_value`, `do = the_result_value`, `isinstance(do, DoAttempt)` is False, `isinstance(do, DoSleep)` is False, `break`. The value is gone.

In `__call__`, the equivalent is `return do` — the result is returned to the caller. The two paths diverge at a single keyword: `break` vs `return`. No strategy, no callback, no state machine difference — one word. The concealment mechanism is operating at the smallest possible granularity: a `break` in a while loop is indistinguishable from a `return do` when you are reading `_post_retry_check_actions`, reading `iter()`, reading the strategy evaluation chain. You have to read *the caller's loop* to see that `__iter__` throws away what `__call__` returns.

The shared state machine draws attention upward, toward the abstract. The divergence lives in the concrete loop statement of the caller. Readers who followed the sophisticated machinery did not look at the two-line while loop that consumes it.
