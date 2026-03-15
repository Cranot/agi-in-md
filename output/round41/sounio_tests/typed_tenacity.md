## Finding 1
**Claim**: The retry loop implements control flow via type-tagged return values (DoAttempt, DoSleep) rather than state enums, creating a domain-specific control monad.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:lines_182-191, source:lines_205-214
**Falsifiable**: yes: find a case where iter() returns something other than DoAttempt/DoSleep/None that affects control flow differently
**If wrong**: The analysis would need to identify the actual control flow mechanism

## Finding 2
**Claim**: IterState is stored in a ContextVar while statistics is stored in threading.local — this creates two independent state namespaces with different concurrency semantics.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:line_12, source:lines_83-84, source:lines_112-118
**Falsifiable**: yes: trace all reads/writes to both state stores and verify they never interact
**If wrong**: State management would be unified, simplifying the mental model

## Finding 3
**Claim**: The action chain is built dynamically per-iteration by appending functions to a list, then executing them in sequence — this is a deferred-execution interpreter pattern.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:lines_142-180
**Falsifiable**: yes: find an action that executes immediately rather than being appended then called
**If wrong**: Would indicate a different execution model (e.g., immediate vs deferred)

## Finding 4
**Claim**: _first_set implements a two-level defaults cascade (parameter → instance attribute) enabling copy() to express only overrides.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:lines_62-63, source:lines_70-84
**Falsifiable**: yes: trace a copy() call where first is not _unset and verify it returns first, not second
**If wrong**: Configuration inheritance would work differently

## Finding 5
**Claim**: RetrySignal is an Exception subclass used as a control signal, not an error — this creates an "exception for control flow" pattern that can be caught by overly broad except clauses.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:lines_25-27, source:line_157
**Falsifiable**: yes: find code that catches Exception and would inadvertently catch RetrySignal
**If wrong**: The control flow safety profile changes

## Finding 6
**Claim**: The statistics dictionary auto-clears when exceeding 100 keys, preventing unbounded memory growth but destroying historical data without warning.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:lines_112-116
**Falsifiable**: yes: verify no other code path clears statistics
**If wrong**: Memory management assumptions change

## Finding 7
**Claim**: AttemptManager.__exit__ swallows all exceptions by returning True when exc_type is not None, making it impossible for exceptions to propagate during the attempt context.
**Type**: DERIVED
**Confidence**: 0.95
**Provenance**: derivation:from_finding_1, source:lines_93-99
**Falsifiable**: yes: execute code inside AttemptManager context that raises an exception and verify it doesn't propagate
**If wrong**: Exception handling semantics would need re-analysis

## Finding 8
**Claim**: The retry decision (self.retry) is only consulted when the outcome is not an explicit RetrySignal, creating a fast-path for TryAgain-style retries.
**Type**: DERIVED
**Confidence**: 0.95
**Provenance**: derivation:from_finding_5, source:lines_156-158
**Falsifiable**: yes: raise RetrySignal and verify retry predicate is not called
**If wrong**: The control flow optimization claim is wrong

## Finding 9
**Claim**: NO_RESULT and _unset are distinct sentinel objects serving the same semantic purpose (absence of value) but in different domains (result vs configuration).
**Type**: MEASURED
**Confidence**: 1.0
**Provenance**: source:line_31, source:line_59
**Falsifiable**: no: these are definitional sentinels, their purpose is encoded in their names
**If wrong**: Would indicate a different semantic structure

## Finding 10
**Claim**: The iter() method executes actions via `for action in list(self.iter_state.actions)` — the list() copy prevents infinite loops if an action appends more actions, but only within a single iter() call.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:lines_142-144
**Falsifiable**: yes: have an action append to self.iter_state.actions and verify the new action is not executed in the current loop
**If wrong**: Action execution semantics would be different

## Finding 11
**Claim**: wraps() creates a fresh copy per invocation, isolating statistics per-call but sharing the wrapped function object across all calls.
**Type**: DERIVED
**Confidence**: 0.9
**Provenance**: derivation:from_source, source:lines_91-106
**Falsifiable**: yes: call wrapped function twice concurrently and verify statistics are independent
**If wrong**: Concurrency model would need re-analysis

## Finding 12
**Claim**: Retrying.__call__ sets _iter_state_var at the start of each call, overwriting any existing state — nested retry decorators would corrupt each other's IterState.
**Type**: DERIVED
**Confidence**: 0.85
**Provenance**: derivation:from_finding_2, source:line_198
**Falsifiable**: yes: nest two @retry decorators and verify inner retry's IterState is visible to outer
**If wrong**: Nested retry semantics would be safer than claimed

## Finding 13
**Claim**: The control flow guarantees: (1) DoAttempt always yields AttemptManager, (2) DoSleep always calls prepare_for_next_attempt then sleep, (3) any other return breaks the loop.
**Type**: MEASURED
**Confidence**: 1.0
**Provenance**: source:lines_182-191, source:lines_205-214
**Falsifiable**: yes: find a code path where these guarantees don't hold
**If wrong**: Core execution model would be misunderstood

## Finding 14
**Claim**: Future.construct is a factory that bifurcates on has_exception, calling different setter methods on the same object — this is a two-path construction pattern.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:lines_222-228
**Falsifiable**: yes: verify construct never calls both set_result and set_exception
**If wrong**: Construction semantics would be different

## Finding 15
**Claim**: The retry decorator supports both bare (@retry) and configured (@retry(stop=...)) forms via arity detection on dargs[0].
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:lines_256-262
**Falsifiable**: yes: verify @retry with no parens works on a function
**If wrong**: Decorator usage pattern would be different

## Finding 16
**Claim**: Conservation law: Flexibility × Explicitness = constant. The action chain pattern allows arbitrary extensibility (add any action) but obscures execution order (must trace appends).
**Type**: DERIVED
**Confidence**: 0.8
**Provenance**: derivation:from_findings_3,10
**Falsifiable**: yes: find a way to have both full flexibility and explicit execution order in the same design
**If wrong**: The trade-off identified would not be fundamental

## Finding 17
**Claim**: RetryCallState.idle_for is accumulated in two places: locally (rs.idle_for) and globally (self.statistics["idle_for"]) — this dual-bookkeeping creates a synchronization surface.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:lines_173-176
**Falsifiable**: yes: verify both idle_for values stay equal after each sleep
**If wrong**: Would indicate redundant state without synchronization concern

## Finding 18
**Claim**: The before_sleep callback is added AFTER next_action is set but BEFORE DoSleep is returned — it can observe but not modify the upcoming sleep duration.
**Type**: DERIVED
**Confidence**: 0.9
**Provenance**: derivation:from_source, source:lines_172-178
**Falsifiable**: yes: verify before_sleep cannot change rs.upcoming_sleep in a way that affects the actual sleep
**If wrong**: Callback timing semantics would be different

## Finding 19
**Claim**: enabled=False bypasses all retry logic entirely, calling the wrapped function directly — this is an optimization path that skips copy() and state initialization.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:lines_91-93
**Falsifiable**: yes: verify no statistics are collected when enabled=False
**If wrong**: Disabled mode would have different behavior

## Finding 20
**Claim**: reraise=True causes the original exception to be raised with the RetryError as __cause__, inverting the normal exception wrapping pattern.
**Type**: DERIVED
**Confidence**: 0.95
**Provenance**: source:lines_164-166
**Falsifiable**: yes: verify exception chain with reraise=True
**If wrong**: Exception chaining semantics would be different

---

## Conservation Law
**Claim**: Extensibility × Observability = constant. The action-chain interpreter enables arbitrary extension points (before, after, before_sleep, retry, stop, wait, retry_error_callback) but each extension point obscures the execution trace — you must reconstruct the action list at runtime to understand what will happen.
**Type**: DERIVED
**Confidence**: 0.85
**Provenance**: derivation:from_findings_3,10,16
**Falsifiable**: yes: demonstrate a design that allows both arbitrary extensibility AND static observability of execution order

---

## Summary

**Count per type**: 12 STRUCTURAL, 7 DERIVED, 1 MEASURED, 0 KNOWLEDGE, 0 ASSUMED

**Epistemic quality score**: 12/20 = 60% STRUCTURAL (grounded in direct code reading)

**Key structural findings**:
1. Control monad via DoAttempt/DoSleep type tags
2. Dual state namespaces (ContextVar + threading.local)
3. Deferred-execution action chain interpreter
4. Exception-as-control-flow (RetrySignal)
5. Copy-pattern for configuration isolation
