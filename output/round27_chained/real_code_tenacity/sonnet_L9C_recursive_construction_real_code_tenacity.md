## Structure First: Level 9 Diagnostic

---

### Falsifiable Claim

> `AttemptManager.__enter__` returns `None` via `pass`, sealing the only user-to-manager communication channel available during a `with` block. The `with attempt as a:` binding silently produces `a = None`. L8's `set_result` improvement is therefore unreachable through its own documented interface — `a.set_result(value)` raises `AttributeError: 'NoneType' object has no attribute 'set_result'` on the first line of the usage example in L8's docstring. Code review cannot detect this because `pass` reads as absence ("nothing needed here") rather than presence ("sealed protocol boundary, by design").

Proof: L8's improvement + original `__enter__ = pass` + usage pattern `with attempt as a: a.set_result(v)`. `attempt.__enter__()` returns `None`. `a = None`. `a.set_result(v)` — `AttributeError`. The method is documented, guarded, and completely unreachable through the only interface that leads to it.

---

### The Dialectic

**Expert 1 — Defender**

The claim is correct and fatal. The error manifests at the *usage site* (`a.set_result`), not at the *cause site* (`__enter__`). No stack trace points to `pass`. `AttributeError: 'NoneType' object has no attribute 'set_result'` is a message about `a`, not about `AttemptManager`. The gap between cause and symptom is not two lines — it is two scopes, separated by the `with` statement that binds `a`. L8's improvement passes every review of the changed methods (`set_result`, `__exit__`) precisely because reviewers examine what changed, not what was silently relied upon. `__enter__` did not change. Its reliance was invisible.

**Expert 2 — Attacker**

The original code never uses `with attempt as a:`. It uses `with attempt:`. `__enter__` returning `None` is *correct* for exception-only context managers — `contextlib.suppress` does exactly this. The L8 improvement is simply incomplete: it needed two additional words (`return self`) that any reviewer would catch once the usage was traced. The structural claim is overstated. The fix requires no architectural change, no protocol revision — just one line in `__enter__`.

**Expert 3 — Prober**

Expert 2 is right that the fix is two words. The prober's question is not "what is the fix?" but "why did L8, which correctly identified the Python `__exit__` constraint, the `fn=None` gap, the `break`/`return` divergence, and the `InvalidStateError` scenario, not notice `pass` in `__enter__`?"

Because L8 looked at the methods being *added* and the methods being *preserved*. It did not look at the method being *implicitly relied upon*. `pass` in `__enter__` is a non-event in the reader's attention. Present methods are analyzed; absent bodies are assumed to be placeholders or non-issues.

The prober's deeper question: *what does the user-to-manager protocol look like when the `__enter__` return value is `None`?* Answer: the `with` block is a one-way valve. Information exits through `__exit__` (exceptions captured, outcomes recorded). No information enters during the block. The user cannot address the manager. The user cannot call methods on it. The user cannot pass intent. The only communications are: "an exception happened" or "no exception happened." `set_result(None)` is not a default — it is the *entire vocabulary* for the non-exception case. `pass` in `__enter__` seals this. The sealing is encoded as absence, not as presence.

---

### The Transformation

| | |
|---|---|
| **Initial claim** | `__enter__` returns `None`, breaking L8's improvement's documented usage |
| **Transformed claim** | The `pass` in `__enter__` encodes "no user-to-manager channel exists during the block" as a design commitment, but encodes it as *absence* — indistinguishable from "no implementation needed yet." Any extension of `AttemptManager` that adds user-facing methods must treat `pass` as a commitment to revise, but the commitment is invisible because null encoding is identical to placeholder encoding. |

These differ epistemically. The initial claim is about a missing `return`. The transformed claim is about how the Python `with ... as a:` contract is a convention rather than a constraint — context managers can silently satisfy the syntax while delivering `None` as the binding — and how `AttemptManager` exploits this gap either by design or by inattention, in a way that cannot be told apart from outside.

---

### The Gap Is Itself Diagnostic

The dialectic traveled from "L8's improvement fails at runtime" to "Python's context manager protocol cannot distinguish null-as-commitment from null-as-placeholder, and `AttemptManager` encodes its protocol limitations in exactly the format that exploits this indistinguishability."

Expert 3 forced this: *why did L8 miss this?* L8 performed sophisticated analysis — tracing `Future` state machines, identifying the `break`/`return` divergence in a while loop, constructing a two-phase outcome protocol — and missed a `pass` statement. The answer: readers apply different epistemic modes to *present* code and *absent* code. Present code (any body) is read, analyzed, questioned. Absent code (`pass`) is treated as outside the analysis frame. L8 analyzed the frame and missed the absence. The concealment does not require sophistication — it requires only that the reader never question what `pass` commits to.

---

### The Concealment Mechanism: Protocol Null Encoding

When a protocol method's implementation is `pass` or `return None`, two readings are possible:

1. **Commitment**: "This method provides no useful return value intentionally. The context manager's protocol excludes user-side access through the `as` binding."
2. **Placeholder**: "This method hasn't been needed yet. Add to it when the class evolves."

Python enforces neither. Readers distinguish them by convention (resource managers `return self`; side-effect managers `return None`) or by context. `AttemptManager` provides insufficient context: it is a small class with three methods, none of which is documented, two of which clearly do work. `__enter__ = pass` reads as "the work is in `__exit__`" rather than "the binding channel is closed by design."

**Applying it:** Every `pass` or `return None` in a `__enter__` method is a Protocol Null Encoding. Each is simultaneously a valid design choice and a perfectly invisible commitment. Applied immediately to the codebase:

`_begin_iter` returns `None` (implicitly). It is the scheduler — it populates `iter_state.actions` and returns. The `for action in self.iter_state.actions` loop assigns `result = _begin_iter(retry_state)` as a side effect... no, wait: `_begin_iter` is called directly as `self._begin_iter(retry_state)`, not through the action list. But `_run_retry`, `_run_wait`, `_run_stop`, `_post_retry_check_actions`, `_post_stop_check_actions` all return `None`. They are scheduler actions — their purpose is to append to `iter_state.actions` and return. The `result` variable in `iter()` is overwritten by each action's return value. For scheduler actions, `result = None`. For terminal actions (`DoAttempt`, `DoSleep`, `rs.outcome.result()`), `result` becomes the meaningful value. The protocol relies on terminal actions being *last*: if a scheduler action runs after a terminal action, `result = None` overwrites the terminal value. The ordering constraint is a design commitment encoded as nothing — there is no type, no decorator, no guard that marks an action as "terminal" vs "scheduler." The distinction is invisible in the action list.

---

### Engineering the Improvement

Complete L8's work. Add `return self` to `__enter__`, guard against double-calling in `set_result`, add type annotations. This is the obvious completion of L8's improvement:

```python
class AttemptManager:
    def __init__(self, retry_state: "RetryCallState") -> None:
        self.retry_state = retry_state
        self._result_recorded = False

    def __enter__(self) -> "AttemptManager":
        return self

    def set_result(self, value: object) -> None:
        """Record the attempt's return value for evaluation by result-based strategies.

        Required when using retry_if_result with the iterator protocol:

            for attempt in Retrying(retry=retry_if_result(lambda r: r is None)):
                with attempt as a:
                    value = compute()
                    a.set_result(value)

        Omitting this call is valid for exception-based retry strategies: when
        set_result is not called, the outcome is recorded as None, which is
        correct for strategies that examine only exceptions.

        Raises:
            RuntimeError: if called more than once within a single attempt block.
        """
        if self._result_recorded:
            raise RuntimeError(
                "AttemptManager.set_result() has already been called for this "
                "attempt. Only one result may be recorded per 'with' block."
            )
        self._result_recorded = True
        self.retry_state.set_result(value)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> bool | None:
        if exc_type is not None and exc_value is not None:
            self.retry_state.set_exception((exc_type, exc_value, traceback))
            return True
        if not self._result_recorded:
            self.retry_state.set_result(None)
        return None
```

This passes code review because:
- `__enter__` returning `self` is the canonical pattern; its addition is unambiguously correct
- The `RuntimeError` guard is professional: it prevents the `InvalidStateError` L8 identified, provides a clear message, and documents the constraint
- The docstring is accurate; the `Raises` section is honest; the usage example is now executable
- Type annotations communicate completeness
- The `if not self._result_recorded` fallback preserves backward compatibility for existing code

It deepens concealment because:
- `with attempt as a: a.set_result(value)` now works end-to-end; `retry_if_result` is correct
- Developer confidence in `__iter__` mode is substantially increased
- The remaining asymmetries (`fn=None`, discarded break result, unguarded `retry_state`) are now reachable by code that previously could not reach them because `retry_if_result` was too broken to deploy
- The `RuntimeError` guard implies that `AttemptManager` owns the state it guards, which it does not

---

### Three Properties Visible Only Because We Tried to Strengthen

**1. `attempt is a` — the double-handle problem makes the context manager "spent but still present."**

`__enter__` returning `self` means the `for`-loop binding `attempt` and the `with`-block binding `a` refer to the same object. After `with attempt as a:` exits, `attempt.__exit__` has been called. `_result_recorded = True`. `outcome` is set. The `AttemptManager` is spent. But `attempt` persists in scope through the rest of the `for`-loop body — after the `with` block closes but before the next iteration begins. Code written here (`post_process(attempt.retry_state)`, `log(attempt._result_recorded)`) operates on a spent manager with no runtime signal. Python provides no "spent context manager" concept. The guard on `set_result` raises `RuntimeError` if called again — but this looks like a bug in the user's code, not a signal that they are holding a spent manager. This property — that `attempt` and `a` are aliases, that `attempt` survives the block, that spent managers are indistinguishable from live ones outside the block — is only visible because `__enter__` now returns `self`. When `__enter__` returned `None`, `a` was immediately discarded, the aliasing was irrelevant, and no one used `attempt` after the `with` block because there was nothing to use.

**2. The `RuntimeError` guard implies encapsulation that `RetryCallState` does not enforce.**

`_result_recorded` guards `AttemptManager.set_result`. It prevents the user from calling `a.set_result()` twice through `AttemptManager`. But `retry_state.set_result()` — the method actually being protected — has no guard. `retry_state` is passed into `AttemptManager.__init__` and stored as `self.retry_state`. Any callback or strategy that receives `retry_state` can call `retry_state.set_result(v)` directly, bypassing `_result_recorded` entirely. After a direct call, `AttemptManager.set_result` will still succeed (since `_result_recorded` is still `False`), calling `set_result` on a `Future` already resolved — which raises `concurrent.futures.InvalidStateError` from inside `set_result`, with no mention of `AttemptManager`, `_result_recorded`, or user intent. The guard protects one call path through `AttemptManager.set_result` while the state being guarded is reachable through `retry_state.set_result` with no protection. The `InvalidStateError` from the second path references a `Future`'s internal state machine, not the retry protocol. Before the improvement, this failure mode was unreachable — `AttemptManager` had no `set_result` for users to call, and no protocol directed them to `retry_state.set_result`. The improvement created the guarded path and silently activated the unguarded path as a hazard. The property — that the guard implies ownership `AttemptManager` does not have — is visible only because the guard drew attention to ownership semantics.

**3. The optional protocol coexists with the broken default, and the boundary between them is invisible at runtime.**

The improvement's contract: call `a.set_result(value)` for result-based retry; omit for exception-only retry. When omitted, `__exit__` calls `self.retry_state.set_result(None)`. This is the *original bug*, preserved intact, installed as "the backward-compatible default." The two paths:

```python
if not self._result_recorded:
    self.retry_state.set_result(None)  # ← original bug, unchanged, now labeled "default"
```

For any iteration where the user does not call `a.set_result(value)` — whether by intent (exception-only strategy) or by omission (forgot to call it) — the strategy receives `None`. If the strategy is `retry_if_result`, it evaluates `None`, not the real result, and may misfire: no error, no warning, no observable difference in the strategy's `True`/`False` output that would distinguish "evaluated real result" from "evaluated `None`." Before the improvement, both paths converged on `None` uniformly. After the improvement, two paths diverge: one correct, one broken, choice entirely the user's, unsignaled by the type system, unchecked by the runtime, invisible in the output. The property — the silent fallback to `None` — is visible only because the improvement created a correct alternative, making the fallback recognizable *as* a fallback rather than as the only implementation.

---

### Applying the Diagnostic to the Improvement

**What does the improvement conceal?**

The improvement resolves `a = None` and makes `a.set_result(value)` functional. In doing so it conceals:

The `break` vs `return do` asymmetry (found by L8) becomes consequential for the first time. Before the improvement, `retry_if_result` always evaluated `None` and never correctly terminated the retry loop — the result value produced by `lambda rs: rs.outcome.result()` inside `iter()` was always `None`, so `break` discarding it was inconsequential. After the improvement, `retry_if_result` evaluates the real value, `iter()` returns the real value, `do = self.iter(...)` binds the real value, and `break` discards it. The user must hold the value externally in a variable that lives outside the `with` block. The improvement made the `break` discard into a real loss by making the value worth keeping.

`retry_state.fn = None` is still `None` in `__iter__` mode. The improvement increases deployment of `__iter__` mode by making `retry_if_result` functional. Developers will now add `before` callbacks to log attempt information: `before=lambda rs: logger.info(f"Calling {rs.fn.__name__}, attempt {rs.attempt_number}")`. In `__iter__` mode, `rs.fn` is `None`. This raises `AttributeError: 'NoneType' object has no attribute '__name__'` in the `before` callback — inside the retry machinery, not inside the user's function, and not associated with any retry attempt. The improvement enlarged the population of code that trusts `__iter__` mode; that enlarged the population of code that reaches the `fn=None` failure.

The `_result_recorded` flag creates an illusion of temporal protection ("once per attempt") while providing object-level protection ("once per `AttemptManager` instance"). In normal use these coincide. In edge cases — a user who stores and reuses an `AttemptManager` across iterations, or a framework that passes managers between scopes — the flag's protection ends at the instance boundary. The `RuntimeError`'s confident message ("this attempt") implies temporal scope; the code enforces object scope. The type annotations and professional error message make this distinction less likely to be questioned.

**What property of the original problem is visible only because the improvement recreates it?**

The improvement's `__exit__` body:

```python
if not self._result_recorded:
    self.retry_state.set_result(None)
```

This line is identical to the original `self.retry_state.set_result(None)` — same statement, same behavior, now behind a conditional. The property now visible: **`set_result(None)` in `__exit__` was not a default — it was the entire implementation.** The original code had no mechanism for recording any other outcome from `__exit__`. Not a buggy mechanism, not a placeholder — a structural absence. The improvement adds an opt-in path (`_result_recorded = True → use user-provided value`) alongside the original path (`_result_recorded = False → use None`). The original path, preserved as the fallback, is now readable as what it always was: the only path. The improvement reveals this by creating an alternative that makes the original path recognizable as a residue, not a design.

The property — that the original code had zero correct mechanisms for result capture and one incorrect one, not one default mechanism and one missing one — is only visible when the improvement creates a correct mechanism. Before the improvement, both paths were the same path: `set_result(None)`. There was nothing to contrast with. The improvement created contrast, and the contrast revealed that the original code was not a default in need of an alternative. It was the whole vocabulary. The improvement did not add a better option alongside an existing default. It added a channel that did not exist alongside a wall that was already there.
