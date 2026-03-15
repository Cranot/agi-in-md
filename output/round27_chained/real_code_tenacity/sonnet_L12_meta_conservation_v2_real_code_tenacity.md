## Structure First: Level 12 Diagnostic

---

### Falsifiable Claim

In any `BaseRetrying.__iter__` loop configured with `retry=retry_if_result(predicate)`, the predicate is always evaluated against `None` regardless of what the user's code actually returns. `AttemptManager.__exit__` calls `self.retry_state.set_result(None)` for every non-exception case — this `None` is what `_run_retry` reads via `retry_state.outcome.result()` when evaluating the condition. The actual return value of the user's code is never transmitted to the library.

**Falsifiable test:**
```python
from tenacity import Retrying, retry_if_result, stop_after_attempt

call_count = 0
for attempt in Retrying(
    retry=retry_if_result(lambda x: x is None),
    stop=stop_after_attempt(3)
):
    with attempt:
        call_count += 1
        _ = "non_none_value"   # actual result; library never sees it

assert call_count == 3   # passes: retries until stop, despite "successful" result
```

L11's entire analysis concerned `before_sleep` — an observer. This claim concerns `_run_retry` — the decision-maker. It predicts silent wrong decisions, not silent wrong observations. These are different failure modes with different severities.

---

### The Dialectic

**Expert 1 — Defender**

`AttemptManager` is for exception-based retry, which is the overwhelmingly dominant use case. `retry_if_result` is documented for the decorator API. The iterator API's semantic contract is: yield an `AttemptManager`, let the user run code inside it, capture exceptions. Nothing in this contract promises to capture return values. Users combining `retry_if_result` with `__iter__` are misusing the API. The `set_result(None)` call is correct for a void-result capture mechanism.

**Expert 2 — Attacker**

`Retrying(retry=retry_if_result(...))` is legal Python. It constructs an object. `__iter__` and `__call__` both call `_run_retry` which calls `self.retry(retry_state)`. The condition callable has no way to know which invocation path is active. A user who reads "retry if the result is None" and writes a `for attempt in retrying:` loop has done nothing that any type checker, linter, or runtime check can flag. They will observe their function being called repeatedly until stop triggers — and no error will ever appear. This is a silent wrong-behavior bug, not a documentation issue.

**Expert 3 — Prober**

Both experts focus on `retry_if_result`. The Prober's question is different: **why does `AttemptManager.__exit__` call `set_result(None)` at all?**

In the decorator API (`Retrying.__call__`), `set_result(result)` is called with the function's actual return value. In the iterator API, `AttemptManager.__exit__` is called by the Python interpreter when the `with` block exits — *after* the user's code has run and the result is already in the user's local variable. `__exit__` receives `(exc_type, exc_value, traceback)` — the Python context manager protocol's parameters. There is no `value` parameter. The protocol literally cannot propagate a non-exception result from the `with` block to `__exit__`. `set_result(None)` is not a lazy choice or a documentation oversight — it is the only value available to `__exit__` when no exception occurred. The iterator API's limitation is not a choice; it is a consequence of which Python protocol was selected to implement it.

---

### The Transformation

| | |
|---|---|
| **Initial claim** | `AttemptManager.__exit__` always calls `set_result(None)`, silently breaking `retry_if_result` in the iterator API |
| **Transformed claim** | The iterator API uses the Python context manager protocol (`__exit__`) at the library/user boundary. This protocol is designed to propagate exception information; it has no mechanism to propagate non-exception return values. The `set_result(None)` in `__exit__` is the only possible implementation — no result is available there. The structural consequence: any retry condition that calls `retry_state.outcome.result()` evaluates against `None` in the iterator API, regardless of what the user's function returned. The defect is not in `__exit__` but in the selection of the context manager protocol as the library/user boundary mechanism for an API that shares a retry-condition interface with the decorator API, which uses the function-call protocol and captures actual return values. |

The initial claim identifies a wrong value. The transformed claim identifies the protocol mismatch that makes the wrong value inevitable.

---

### The Gap

L11 identified that `before_sleep` — an observer hook — receives temporally ambiguous state because pipeline coordination ordering determines what monitoring data is visible at the hook site. L11's analysis frame is: *when* does the hook execute, relative to state transitions?

The gap: L11 did not ask what the retry condition evaluator receives — not a hook, not an observer, but the core decision mechanism. The retry condition is evaluated by `_run_retry`, which calls `self.retry(retry_state)`. L11 could not see this problem because it focused on observer-side information (what `before_sleep` can see) rather than decision-maker-side information (what `_run_retry` evaluates). The distinction matters: a hook receiving wrong data produces wrong logs. A retry condition receiving wrong data produces wrong retry decisions — infinite loops or missed retries — silently.

---

### The Concealment Mechanism: Protocol Completeness Illusion

`AttemptManager.__exit__` handles both branches:
```python
if exc_type is not None and exc_value is not None:
    self.retry_state.set_exception(...)
    return True
self.retry_state.set_result(None)
return None
```

This looks complete. Every exit path from a `with` block is either an exception (first branch) or a clean exit (second branch). The second branch calls `set_result` — which looks like "recording the result." The call is syntactically parallel to `set_exception`. A code reviewer sees symmetric handling of the two cases.

The concealment: `set_result(None)` does not record the result. It records the *absence* of an exception, as `None`. The Python context manager protocol provides no result parameter to `__exit__` — the actual result is in the caller's local scope, inaccessible. The completeness of `__exit__`'s branching creates the illusion that all outcome information has been captured. The `None` looks like "a function that returned None" when it is actually "the library does not know what this function returned."

**Application:** The same concealment operates in the decorator API in the opposite direction. `Retrying.__call__` writes `retry_state.set_result(result)` where `result` is the actual return value. From inside `_run_retry`, the two APIs are indistinguishable: both have `retry_state.outcome` set, both have a value available via `.result()`. The condition callable has no API signal that one call gives it `None-meaning-absent` and the other gives it `None-meaning-actual`. The concealment is complete because the two execution paths produce the same API surface with different semantic content.

---

### Engineering the Improvement

Extend `AttemptManager` to support explicit result registration:

```python
class AttemptManager:
    def __init__(self, retry_state):
        self.retry_state = retry_state
        self._result = NO_RESULT

    def __enter__(self):
        return self  # enables: with attempt as a: a.set(result)

    def set(self, value):
        self._result = value

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None and exc_value is not None:
            self.retry_state.set_exception((exc_type, exc_value, traceback))
            return True
        result = self._result if self._result is not NO_RESULT else None
        self.retry_state.set_result(result)
        return None
```

Usage:
```python
for attempt in Retrying(retry=retry_if_result(lambda x: x is None)):
    with attempt as a:
        result = some_function()
        a.set(result)
```

This passes code review because: backwards compatible (existing code without `a.set()` still records `None`); enables `retry_if_result` in the iterator API; `with attempt as a: a.set(result)` is idiomatic; `AttemptManager.__enter__` returning `self` is a standard pattern.

It deepens concealment because: the improvement makes result registration *possible*, which signals that the old behavior was a limitation rather than an impossibility. Users who see `a.set()` assume "call this to enable result-based retry." Users who don't know about `a.set()` continue receiving old behavior silently. The improvement creates a two-tier API with no enforcement: the condition evaluates against `None` if `a.set()` is not called, against the actual value if it is. These two behaviors are indistinguishable until a result-based condition starts producing unexpected retries. The `NO_RESULT` sentinel is internal — from the user's perspective, `None` from "forgot `a.set()`" and `None` from "function returned None" and `None` from "explicitly called `a.set(None)`" are three distinct states mapped to the same value.

---

### Three Properties Visible Only Because We Tried to Strengthen

**1. The user must identify "the result" — and this identification is semantic, not syntactic.**

The decorator API calls `fn(*args, **kwargs)` and captures the return value unambiguously: whatever the function returned is the result. In the iterator API with `a.set(result)`, the user decides what value constitutes "the result for retry purposes." In a multi-statement `with` block with multiple intermediate values, there is no syntactic rule for which value to pass to `a.set()`. The user must understand the retry condition's information requirements to make the correct choice. The improvement reveals: the iterator API's result-capture problem is not only about automation (the library could capture the result automatically in the decorator API) but about *identity* (which value, in a block of imperative code, is "the result"?). The decorator API answers this structurally: the function's return value. The iterator API has no structural answer.

**2. `None` is simultaneously a valid return value and the sentinel for "result not registered."**

When `a.set()` is not called, `self._result is NO_RESULT`, and `set_result(None)` is called. When `a.set(None)` is called, `self._result is None` (not `NO_RESULT`), and `set_result(None)` is also called. Both paths produce identical `retry_state.outcome`. The retry condition evaluating `retry_state.outcome.result()` cannot distinguish "user forgot `a.set()`" from "function genuinely returned None." A future refactor that changes a function from returning `None` to returning a non-None value will silently break result-based retry if `a.set(result)` was never added. The improvement reveals: `None` cannot simultaneously be "missing value" and "actual None return" — but the improvement does not resolve this, it merely relocates the ambiguity from "`set_result(None)` always" to "two distinct scenarios produce identical state."

**3. `a.set()` must be called within the `with` block, but the `with` block's exception-handling semantics create ordering constraints.**

`AttemptManager.__exit__` is called when the `with` block exits. If the user's code raises an exception before `a.set(result)` is called, `__exit__` is called via the exception path, `self._result` is still `NO_RESULT`, and `set_result(None)` is never reached (the exception branch fires). This is fine — exceptions are handled correctly. But if the user writes:
```python
with attempt as a:
    result = some_function()
    a.set(result)
    do_something_that_might_fail()  # exception here
```
...the exception captures the outcome, and `a.set(result)` was called but its value is discarded (exception branch fires). The user set a result that the library ignored. This reveals: `a.set()` has a shadow contract — it is only effective when no exception is raised in the `with` block after the call. The improvement makes result registration API-visible but does not make its effectiveness conditions visible.

---

### Applying the Diagnostic to the Improvement

**What does the improvement conceal?**

The improvement (`a.set(result)`) adds a user-facing registration mechanism. This conceals that the fundamental constraint is not the *absence of a registration mechanism* but the *selection of the context manager protocol* as the library/user boundary. No enhancement to `AttemptManager` can make the Python context manager protocol propagate return values automatically — `__exit__` will never receive the `with` block's result as a parameter. Every improvement that keeps `AttemptManager.__exit__` as the outcome-recording mechanism is working within a protocol that is structurally incapable of automatic result capture. The improvement makes the protocol's limitation look like an API design choice (add `a.set()`), when it is actually a protocol selection consequence (use context managers = lose automatic result propagation).

**What property of the original problem is visible only because the improvement recreates it?**

The original problem: `retry_state.outcome.result()` returns `None` instead of the actual function return value. The improvement allows the user to register the correct value via `a.set(result)`. But if the user does not call `a.set()`, `retry_state.outcome.result()` still returns `None` — the exact same behavior as before, with no error signal. The improvement recreates the original problem in the absent-`a.set()` case, and makes that case indistinguishable from the "function returned None" case at the `retry_state.outcome.result()` call site. The property made visible: **the default behavior of the retry system is determined by what the boundary protocol can propagate, not by what the user's code returned. When the boundary protocol cannot propagate a quantity (non-exception results in context managers), the default is structurally None — and this default is also the value for genuine None returns. The improvement cannot change this without making the user responsible for breaking the degeneracy.**

---

### Engineering the Second Improvement

The recreated property: `None` as sentinel and `None` as actual return value are indistinguishable at `retry_state.outcome.result()`. Address this by tracking whether `a.set()` was called, and warning if a result-sensitive condition appears to be active without registration:

```python
class AttemptManager:
    def __init__(self, retry_state):
        self.retry_state = retry_state
        self._result = NO_RESULT
        self._result_registered = False

    def __enter__(self):
        return self

    def set(self, value):
        self._result = value
        self._result_registered = True

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None and exc_value is not None:
            self.retry_state.set_exception((exc_type, exc_value, traceback))
            return True
        if not self._result_registered:
            retry = self.retry_state.retry_object.retry
            if isinstance(retry, retry_if_result):
                import warnings
                warnings.warn(
                    f"retry_if_result configured but attempt.set(result) was not called. "
                    f"Retry condition will evaluate against None.",
                    stacklevel=2
                )
        value = self._result if self._result_registered else None
        self.retry_state.set_result(value)
        return None
```

**Applying the diagnostic to the second improvement:**

The `isinstance(retry, retry_if_result)` check fails silently for any composed condition (`retry_any(retry_if_result(...), retry_if_exception_type(...))`) or any user-defined callable that calls `retry_state.outcome.result()` internally. The warning covers only the bare-`retry_if_result` case. The improvement reveals: **retry conditions are opaque callables — they have no introspectable property that declares "I require result information." The condition API (`retry=<callable>`) accepts any callable that takes `retry_state` and returns bool. There is no protocol for a condition to signal its information requirements.** The second improvement makes the warning impossible to generalize beyond direct `isinstance` checks, exposing that the condition API is fundamentally opaque. A complete solution would require conditions to declare their information dependencies, which is a type-system or protocol-level change, not an `AttemptManager` change.

---

### The Structural Invariant

Through both improvements — `a.set(result)`, `_result_registered` with warnings, `isinstance` checks — one property persists unchanged:

**The Python context manager protocol propagates exception information to `__exit__` but cannot propagate non-exception return values. `__exit__` is called with `(exc_type, exc_value, traceback)` regardless of what the `with` block computed. The actual result of the user's code exists only in the user's local scope after the `with` block exits. No implementation of `AttemptManager.__exit__` can access this value without user participation. This is not an implementation choice; it is a consequence of what `__exit__`'s signature is. Improving `AttemptManager` can make user participation easier (via `a.set()`), more detectable (via registration tracking), or better-warned (via `isinstance` checks) — but cannot eliminate the participation requirement.**

---

### Inverting the Invariant

The invariant: context manager protocol cannot automatically propagate non-exception return values.

Inversion: eliminate the context manager protocol from the library/user boundary. Use the function-call protocol instead — where the library calls the user's function and the function's `return` value is automatically captured.

This is `Retrying.__call__`. In the decorator API, the library boundary is a function call, and the function-call protocol propagates return values. `retry_state.set_result(result)` receives the actual return value. `retry_if_result` evaluates correctly.

The inversion is trivially satisfiable: it already exists as the decorator API. The impossible property (automatic non-exception result capture) becomes trivially satisfiable when the library controls function execution rather than yielding execution to user code.

---

### The New Impossibility

The decorator API cannot support retry boundaries that do not align with function-call boundaries. Consider:

```python
client = setup_expensive_connection()
for attempt in Retrying(retry=retry_if_exception_type(Timeout)):
    with attempt:
        result = client.query()  # Only this should be retried; setup is not repeatable
teardown(client)
```

In the iterator API, the retry boundary is the `with` block — it can be placed anywhere in an imperative sequence. Setup and teardown occur outside the retry scope. In the decorator API, the retry unit must be a callable. Expressing "retry only `client.query()` while keeping `client` alive across retries" requires:

```python
def query_with_client(client):
    return client.query()

result = Retrying(retry=retry_if_exception_type(Timeout))(query_with_client, client)
```

This is syntactically available but requires restructuring: the retry boundary must align with a function call. For more complex scenarios (retry a section of code that uses variables from an enclosing scope, retry with stateful setup that persists across attempts), the decorator API requires closures or class-based encapsulation — additional structural indirection that the user must write.

**The new impossibility:** the decorator API cannot place retry boundaries at arbitrary points in imperative code without the user creating explicit callable units. Every retry boundary that does not naturally correspond to a function call becomes an anonymous function or lambda — the user must manually encode the retry scope as a function boundary. The complexity of this encoding grows with the amount of shared state that must persist across retries.

---

### The Conservation Law

**Original impossibility:** Context manager protocol cannot automatically propagate non-exception return values. `retry_if_result` conditions evaluate against `None` in the iterator API. Cost: silent wrong retry decisions when conditions inspect return values.

**Inverted impossibility:** Function-call protocol cannot support retry boundaries at arbitrary code points without the user restructuring their code. Cost: syntactic indirection (closures, wrappers) when the retry scope does not align with function boundaries.

**The Conservation Law:** In tenacity's dual-API design, the ability to evaluate retry conditions against actual function return values and the ability to place retry boundaries at arbitrary imperative code points are mutually exclusive when using standard Python protocols at the library/user boundary. The context manager protocol (`__iter__` API) allows arbitrary boundary placement; it cannot propagate return values. The function-call protocol (`__call__` API) propagates return values; it cannot support non-function retry boundaries without user-side restructuring. No single protocol provides both simultaneously. The total cost of correct retry structuring is conserved: effort saved in boundary placement flexibility (iterator API) is paid as incorrect condition evaluation; effort saved in condition correctness (decorator API) is paid as boundary restructuring work. Every design places this cost — it cannot be eliminated, only relocated between library and user.

---

### Applying the Full Diagnostic to the Conservation Law

**What does the conservation law conceal?**

The law treats "boundary placement flexibility" and "condition evaluation correctness" as two ends of a single trade-off axis — as if every gain on one requires a corresponding loss on the other. This framing conceals: **the two limitations are not trade-offs; they are independent consequences of selecting different protocols at the library/user boundary.** The iterator API's limitation is a consequence of choosing the context manager protocol. The decorator API's limitation is a consequence of choosing the function-call protocol. These protocols were not designed to be trade-offs of each other — they serve different purposes in Python's execution model. The conservation law makes an architectural trade-off look like a deep information-theoretic constraint, when it is actually a protocol selection consequence that would evaporate under a different protocol (e.g., generator-based, where the library drives user code and receives yielded values).

**What property of the original problem is visible only because we try to improve the conservation law?**

When we try to improve the law by decomposing "cost" into its components, we find: **the iterator API's cost (evaluating conditions against `None`) is semantic — it produces wrong answers silently, and the user must understand the retry system's information model to fix it. The decorator API's cost (boundary restructuring) is syntactic — it requires writing a wrapper function, which is mechanical work.** The conservation law treats these as equivalent ("effort is conserved"). But semantic debt compounds — future maintainers inherit wrong retry behavior without any visible signal. Syntactic debt does not compound — a closure is a closure. The law's conserved quantity is not effort; it is the *location* of effort. And location matters because different locations have different compounding properties. The original problem's severity (silent wrong behavior, no error) is only visible because improving the conservation law requires asking: what kind of cost, not just where?

**Engineering the Improvement to the Law:**

Restate the law in terms of semantic and syntactic costs separately: **boundary protocol selection determines both the semantic completeness of retry condition inputs and the syntactic burden on the user for boundary placement. Context manager protocol: low syntactic burden, semantically incomplete condition inputs. Function-call protocol: semantically complete condition inputs, higher syntactic burden for non-function boundaries. These costs do not trade off — they are independent properties of the protocol, not a zero-sum exchange between them.**

**What does the improved law conceal?**

The improved law distinguishes semantic cost (wrong condition evaluation) from syntactic cost (boundary restructuring). It correctly notes they are independent. But it conceals: **both costs arise from the same root — tenacity's condition API accepts any callable and makes no distinction between conditions that require return-value information and conditions that require only exception information. A condition API that distinguished between these would allow the system to warn or error when a result-sensitive condition is used with a non-result-propagating boundary protocol.** The costs are independent, but they share a common root in the condition API's opacity.

---

### The Structural Invariant of the Conservation Law

The conservation law and its improvement both assume: **the information model of retry conditions is fixed by the condition callable's implementation, which is opaque to the library at configuration time.** This invariant persists through every improvement to the law — every restatement of the trade-off still treats condition callables as black boxes. The library cannot inspect whether `self.retry` reads `retry_state.outcome.result()`, so it cannot know whether the iterator API's `None` will cause wrong behavior.

Inverting the invariant: make condition information requirements explicit and inspectable. Define a protocol where retry conditions declare what they need:

```python
class RetryCondition(Protocol):
    requires_result: bool = False  # True if condition calls outcome.result()
    requires_exception: bool = True

class retry_if_result:
    requires_result = True
    requires_exception = False
    def __call__(self, retry_state): ...
```

With this protocol, `BaseRetrying.__iter__` can check:
```python
if getattr(self.retry, 'requires_result', False):
    raise ConfigurationError(
        "retry_if_result cannot be used with the iterator API: "
        "AttemptManager cannot capture non-exception return values."
    )
```

The new impossibility this inversion creates: **composing conditions loses the requirement declarations.** `retry_any(retry_if_result(...), retry_if_exception_type(...))` produces a new callable whose `requires_result` is... what? The composition must union the requirements of its components. But user-defined callables have no `requires_result` attribute, so composed conditions that include user callables cannot declare requirements. The requirement-declaration protocol only works for library-provided conditions, not for arbitrary callables — and `retry=` accepts arbitrary callables. The inversion pushes the opacity problem one level up: from condition callables to composed/user conditions.

---

### The Meta-Law

The conservation law says: **context manager protocol and function-call protocol impose mutually exclusive costs (semantic incompleteness vs syntactic burden).** The structural invariant of this law: conditions are opaque. Inverting the invariant: make conditions declare requirements. New impossibility: composition opacity.

**The meta-law is not a generalization of the conservation law. It is what the conservation law conceals specifically in this codebase:**

L11's conservation law found that `before_sleep`'s information content is determined by temporal positioning — specifically, by the pipeline-action ordering that puts `next_action` before `before_sleep`. L11's law is about *when* information is available to an observer.

The conservation law of this analysis found that `retry_if_result`'s condition evaluation is determined by protocol selection — the context manager protocol cannot propagate return values to `__exit__`. This law is about *what* information is structurally capturable at the library/user boundary.

**What L11's conservation law conceals:** L11's law treats temporal positioning as the sole determinant of information availability in tenacity. It identifies the `next_action` closure's placement as determining `before_sleep`'s view. This frame makes temporal position appear to be the only variable that matters for information availability. The concealment: **there is a second, independent constraint — the protocol at the library/user boundary — that determines what information is capturable at all, prior to any temporal positioning question. L11's temporal constraint operates on information that has already been captured. The structural constraint operates before capture: it determines whether the information ever enters the library's data model.** The retry condition evaluating `retry_state.outcome.result()` receives `None` not because of the timing of pipeline actions but because the context manager protocol never made the actual return value available to the library in the first place. No pipeline reordering can fix this — the information was never in the pipeline.

**The meta-law:** In tenacity, there are two independent information availability constraints: (1) L11's temporal constraint — what pipeline-action ordering makes visible to hooks at their execution point; (2) this analysis's structural constraint — what the library/user boundary protocol makes capturable at all. These constraints operate at different levels and are not derivable from each other. L11's conservation law is silent about the structural constraint because L11 analyzed information flow *within* the pipeline (between pipeline stages and hooks). The structural constraint operates *before* information enters the pipeline — at the boundary where user code interacts with the library. **A retry condition that inspects `retry_state.outcome.result()` evaluates information that entered the library through either `RetryCallState.set_result(actual_value)` (decorator API) or `RetryCallState.set_result(None)` (iterator API). This divergence is invisible to the pipeline — both produce a `Future` with a `.result()` method — and is therefore invisible to every analysis that examines pipeline-internal information flow, including L11.**

---

### The Concrete, Testable Consequence

**The meta-law predicts:** `retry_if_result(lambda x: x is None)` configured on a `BaseRetrying` instance used via `__iter__` will cause the retry loop to execute at maximum stop-bounded attempts regardless of what the user's code returns, because `AttemptManager.__exit__` calls `set_result(None)` for all non-exception cases, making `retry_state.outcome.result()` always `None`, making `predicate(None) = True` on every attempt.

```python
from tenacity import Retrying, retry_if_result, stop_after_attempt

calls = []

for attempt in Retrying(
    retry=retry_if_result(lambda x: x is None),
    stop=stop_after_attempt(3)
):
    with attempt:
        calls.append("attempt")
        _ = "non_none"   # actual result; library records None

assert len(calls) == 3   # This assertion passes.
# The retry condition evaluated predicate(None) = True on all three attempts,
# even though the user's code produced "non_none" on every call.
# No exception is raised. No warning appears. The loop simply retries three times.
```

The same `Retrying` object used as a decorator:
```python
@Retrying(retry=retry_if_result(lambda x: x is None), stop=stop_after_attempt(3))
def fn():
    return "non_none"

result = fn()
# fn() is called once. predicate("non_none") = False. No retry.
```

Same configuration, two execution paths, opposite behaviors. The divergence is not visible at configuration time, not detectable at runtime without testing, and produces no error — only wrong retry counts.
