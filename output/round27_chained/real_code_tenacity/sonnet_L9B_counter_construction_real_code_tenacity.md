## Structure First: Level 9 Diagnostic

---

### Original Falsifiable Claim

> **The `iter()` action loop — `for action in self.iter_state.actions: result = action(retry_state)` — performs **return-value collapse**: every non-final action's return value is silently overwritten. Because intermediate decision data (`retry_run_result`, `stop_run_result`) cannot reach subsequent stages through the return channel, the architecture routes all inter-stage communication through `IterState` side effects. This makes the ordering constraint between `_run_retry` and `_post_retry_check_actions` invisible and completely unenforced: reverse their registration order in `_begin_iter` and every outcome — successful, failed, any exception type — permanently reads as "no retry needed," with no error, no warning, and no observable difference in the action chain's outward structure.**

Proof by reordering:

```python
# Current (correct):
self._add_action_func(self._run_retry)           # sets iter_state.retry_run_result
self._add_action_func(self._post_retry_check_actions)  # reads iter_state.retry_run_result

# Reversed (silently broken):
self._add_action_func(self._post_retry_check_actions)  # reads retry_run_result = False (default)
self._add_action_func(self._run_retry)                 # sets retry_run_result AFTER it was read
```

In the reversed version: `_post_retry_check_actions` reads `iter_state.retry_run_result = False` (from `reset()`), concludes "no retry needed," adds `lambda rs: rs.outcome.result()`, returns. The for loop then executes `_run_retry`, which sets `retry_run_result = True` — after the consumer already ran. The actual retry strategy's evaluation result is written after it is read. Every retry strategy silently returns `False`. No exception is raised. The action chain structure looks identical.

---

### The Dialectic

**Expert 1 — Defender**

The claim holds and is more consequential than a refactoring hazard. The ordering constraint is an invisible interface contract between methods that look like independent evaluators. Consider extension: a developer adding `_run_result_check` (to support `retry_if_result` in `__call__` mode) reads `_begin_iter`:

```python
if not self.iter_state.is_explicit_retry:
    self._add_action_func(self._run_retry)
self._add_action_func(self._post_retry_check_actions)
```

They insert `self._add_action_func(self._run_result_check)` before `_post_retry_check_actions`. But `_post_retry_check_actions` reads only `retry_run_result` and `is_explicit_retry` — fields that `_run_result_check` doesn't write to. To participate in the decision, the new method must also write to an `IterState` field, and `_post_retry_check_actions` must also read that field — but neither requirement is visible anywhere. Every extension of the evaluation logic requires reverse-engineering `_post_retry_check_actions` to discover which `IterState` fields it consults, then writing to those fields from new methods, in the correct order, with no structural enforcement of correctness at any level.

**Expert 2 — Attacker**

The claim confuses implementation coupling with structural flaw. `_run_retry` and `_post_retry_check_actions` are private methods of `BaseRetrying`, not public extension points. The ordering constraint is no different from the ordering of statements within any private method — it is internal class invariant maintenance. The analysis would be valid if users could register actions in the `_run_retry` style. They cannot: users provide `retry`, `stop`, `wait`, `before`, `after`, `before_sleep` — none of these write to `IterState`. The side-channel protocol is sealed. Calling it "invisible and unenforced" implies it needs external enforcement. It does not.

**Expert 3 — Prober**

Both experts are arguing about who is affected. Neither has asked the structural question: **why does `_run_retry` use a side effect at all?**

The answer is architectural. `_run_retry` cannot pass its decision to `_post_retry_check_actions` through the return channel — that channel performs return-value collapse. Each action's return overwrites the previous. The side effect is not an implementation preference; it is the architecture's *only available inter-stage communication mechanism* given the loop's structure.

This reframes both experts. Expert 2 says "it's private, so it's fine" — but private methods can still have structural problems. Expert 1 says "extension is hard" — but the deeper problem is that the loop's fundamental data model makes inter-stage communication impossible through the normal channel.

The prober's key question: **what would the action chain look like if intermediate return values could reach their successors?** Each action would receive the previous action's result:

```python
result = None
for action in self.iter_state.actions:
    result = action(retry_state, result)  # successor receives predecessor's output
```

Or the actions would be composed functions. Neither exists. The uniform signature `(retry_state) -> result` was chosen to make actions interchangeable — but this uniformity makes return-value passing between stages structurally impossible. The `IterState` side channel is the mandatory consequence of that design choice, not an incidental implementation detail.

---

### The Transformation

| | |
|---|---|
| **Original claim** | Ordering between `_run_retry` and `_post_retry_check_actions` is invisible and unenforced — reversing them silently breaks retry |
| **Transformed claim** | The uniform `(retry_state) -> result` action signature combined with the for loop's return-value collapse makes inter-stage decision communication architecturally impossible through the return channel. `IterState` side effects are not an implementation choice — they are the mandatory substrate for any pipeline that needs stages to communicate. The ordering constraints are not incidental; they are the only possible encoding of inter-stage dependencies in this architecture. |

The gap is an epistemic level: the original claim is a refactoring hazard ("someone could reverse the order"). The transformed claim is an architectural impossibility ("the return channel structurally cannot carry what the pipeline requires"). These are not the same claim at different zoom levels. One is about what someone might do wrong. The other is about what the architecture cannot do.

The translation was forced by the prober's question: *why does `_run_retry` use a side effect?* The original claim assumed the side effect was incidental. The transformed claim identifies it as structurally mandated.

---

### The Gap Is Itself a Diagnostic

The dialectic traveled from "invisible ordering constraint" to "return-value collapse makes the `IterState` side channel architecturally mandatory." This gap is large. The original is a code quality observation. The transformed is a statement about what the data model can express.

The gap was concealed by what I'll name the **Pipeline Simulacrum**: a structure that is syntactically indistinguishable from a functional pipeline but operates as an imperative decision tree coordinated through shared state. The for loop's sequential execution and accumulated return value pattern signal "pipeline," which signals "data flows through return values." Both signals are wrong for this code. The actual data flow is through `IterState` fields — but no reader, having seen the for loop, goes looking for a side channel to understand how `_run_retry` communicates with `_post_retry_check_actions`.

---

### The Concealment Mechanism: Pipeline Simulacrum

A for loop that executes a list of functions and accumulates their return values looks like a pipeline. Pipelines communicate through return values. This visual and conceptual inference is the concealment: readers who see the loop infer that each action's output is available to its successors. It is not.

The mechanism is distinct from L8's "Implementation Convergence as Semantic Proxy." L8 found that shared code between `__iter__` and `__call__` makes two protocols appear semantically equivalent when they are not. Here, the shared code *within* the state machine (`iter()`) makes a decision tree coordinated through shared state appear to be a functional pipeline. L8's mechanism operates at the protocol boundary; this one operates within the pipeline's internals. L8 saw wrong values entering the pipeline; I see the pipeline's data model as incompatible with what the pipeline needs to express.

**Applying it:** Every non-terminal action communicates through a side channel rather than its return value:

- `_run_retry` → `self.iter_state.retry_run_result` (IterState field, reset per call)
- `_run_stop` → `self.iter_state.stop_run_result` (IterState field, reset per call)
- `_run_wait` → `retry_state.upcoming_sleep` (retry_state field, reset per attempt)

Note that `_run_wait` writes to `retry_state`, not `IterState`. The side channel is not even uniform — some inter-stage communication goes to `IterState` (ephemeral, call-scoped), some to `retry_state` (persistent, attempt-scoped). A reader tracing data flow through the pipeline must examine three locations: return values (discarded for non-terminals), `IterState` (two fields), and `retry_state` (one field). None of these form a coherent data model. The Pipeline Simulacrum conceals all three channels behind the single visual idiom of a for loop.

---

### Engineering the Improvement

Introduce a `Verdict` return type that makes the return channel carry decision data, replacing `IterState` side effects with explicit return values:

```python
@dataclasses.dataclass
class Verdict:
    """Decision result from evaluation actions.
    
    Actions that make retry/stop decisions return Verdict instead of None.
    The iter() loop applies Verdict fields to the appropriate state objects,
    making data flow explicit through the return channel.
    
    Example — custom evaluation action:
        def my_action(retry_state):
            return Verdict(should_retry=my_condition(retry_state))
    """
    should_retry: bool | None = None
    should_stop: bool | None = None
    sleep_duration: float | None = None

    def apply(self, iter_state, retry_state):
        if self.should_retry is not None:
            iter_state.retry_run_result = self.should_retry
        if self.should_stop is not None:
            iter_state.stop_run_result = self.should_stop
        if self.sleep_duration is not None:
            retry_state.upcoming_sleep = self.sleep_duration
```

Update `iter()` to process `Verdict` returns:

```python
def iter(self, retry_state):
    self._begin_iter(retry_state)
    result = None
    for action in self.iter_state.actions:
        result = action(retry_state)
        if isinstance(result, Verdict):
            result.apply(self.iter_state, retry_state)
    return result
```

Update system actions to return their decisions:

```python
def _run_retry(self, retry_state):
    return Verdict(should_retry=self.retry(retry_state))

def _run_wait(self, retry_state):
    sleep = self.wait(retry_state) if self.wait else 0.0
    return Verdict(sleep_duration=sleep)

def _run_stop(self, retry_state):
    self.statistics["delay_since_first_attempt"] = retry_state.seconds_since_start
    return Verdict(should_stop=self.stop(retry_state))
```

This passes code review because: `Verdict` is well-documented and makes data flow explicit; `apply()` preserves the existing `IterState` field protocol (backward compatible); the `iter()` loop change is minimal; system actions now have meaningful return types; extension is cleaner.

It deepens concealment because: `Verdict` makes the return channel look like it carries decision data — readers see `_run_retry` returning `Verdict(should_retry=True)` and conclude "retry decisions flow through return values." They are wrong. `Verdict.apply()` writes to `iter_state.retry_run_result`, which `_post_retry_check_actions` reads via `self.iter_state.retry_run_result`. The ordering dependency (`_run_retry` must precede `_post_retry_check_actions`) is *completely unchanged* — `_post_retry_check_actions` still reads the `IterState` field set by `apply()`. But the improvement makes this look fixed: the data appears to flow through `Verdict` (visible) when it actually flows through `IterState` (invisible, via `apply()`). Developer confidence in the action chain increases precisely because the real structural problem is now one level deeper.

---

### Three Properties Visible Only Because We Tried to Strengthen It

**1. The ordering dependency is on action registration order, not on data receipt — and `Verdict` cannot affect registration order.**

Testing the improved chain: reverse `_run_retry` and `_post_retry_check_actions` in `_begin_iter`. Now: `_post_retry_check_actions` runs first, reads `iter_state.retry_run_result = False` (unchanged by `reset()`), decides "no retry needed," adds the result lambda. Returns `None` (it returns nothing — it adds more actions). Then `_run_retry` runs, returns `Verdict(should_retry=True)`. `apply()` sets `iter_state.retry_run_result = True`. But `_post_retry_check_actions` already ran with the wrong value.

The `Verdict` improvement makes the *forward data path* explicit (what `_run_retry` decides). It does nothing about the *backward consumption dependency* (`_post_retry_check_actions` requires `_run_retry` to have already run). The improvement reveals that the ordering constraint is not about data availability — it is about execution precedence. Even with explicit return types, the constraint cannot be enforced by any mechanism short of changing the action execution model entirely.

**2. `Verdict.apply()` writing to both `IterState` and `retry_state` reveals that the side channel has no coherent home — it is split across two objects with different lifetimes and reset protocols.**

`_run_wait` returns `Verdict(sleep_duration=x)`. `apply()` writes to `retry_state.upcoming_sleep`. `_run_retry` returns `Verdict(should_retry=y)`. `apply()` writes to `iter_state.retry_run_result`. A unified `Verdict` that routes to two different objects exposes what was invisible before: decision data has no canonical storage location. Some data (sleep duration) belongs to the attempt record (persists across `iter()` calls until `prepare_for_next_attempt()`). Other data (retry/stop results) belongs to the evaluation phase (valid only within a single `iter()` call, meaningless between calls). The improvement's `Verdict` carries both types uniformly. `apply()` routes them to different locations — making the split explicit for the first time. Before the improvement, `_run_wait`'s write to `retry_state` and `_run_retry`'s write to `iter_state` were syntactically identical (`self.X = value`). The `Verdict` type makes them structurally distinguishable, revealing that they model fundamentally different concerns sharing a single `Verdict` container.

**3. `Verdict` creates the expectation that terminal actions should also return typed results, which reveals that the terminal/non-terminal distinction has no architectural support.**

With `Verdict` introduced, developers naturally ask: should `DoAttempt()` become `Verdict(signal=DoAttempt())`? Should the success result become `Verdict(result=value)`? The answer is no — terminal signals (`DoAttempt`, `DoSleep`, the final result) are dispatched on by the *caller* of `iter()`, not by the loop itself. `Verdict` is consumed by the loop; terminal signals pass through it.

But nothing in the architecture distinguishes "processed by the loop" from "passed through the loop to the caller." Both are return values from actions. If a developer adds a post-processing action that returns `Verdict(...)` and that action happens to be last, `iter()` returns a `Verdict` object. The caller's `isinstance(do, DoAttempt)` and `isinstance(do, DoSleep)` checks fail. `else: break` terminates the generator silently. The `Verdict` object is discarded. The improvement's typing makes the terminal/non-terminal distinction feel architecturally significant — which reveals that no mechanism enforces it. The distinction exists only in the programmer's knowledge of which actions are last, which is precisely the ordering-constraint problem the improvement was meant to address.

---

### The Contradicting Second Improvement

Instead of routing decision data through `Verdict` return values, move all decision state into `retry_state` — where `upcoming_sleep` and `next_action` already live:

```python
class RetryCallState:
    def __init__(self, retry_object, fn, args, kwargs):
        ...
        # Decision state: observable by any callback or strategy
        self.retry_evaluated: bool = False
        self.should_retry: bool = False
        self.stop_evaluated: bool = False
        self.should_stop: bool = False

    def prepare_for_next_attempt(self):
        self.outcome = None
        self.outcome_timestamp = None
        self.attempt_number += 1
        self.next_action = None
        self.retry_evaluated = False
        self.should_retry = False
        self.stop_evaluated = False
        self.should_stop = False
```

Update system actions to write directly to `retry_state`:

```python
def _run_retry(self, retry_state):
    retry_state.should_retry = self.retry(retry_state)
    retry_state.retry_evaluated = True

def _run_stop(self, retry_state):
    self.statistics["delay_since_first_attempt"] = retry_state.seconds_since_start
    retry_state.should_stop = self.stop(retry_state)
    retry_state.stop_evaluated = True
```

Update `_post_retry_check_actions` and `_post_stop_check_actions` to read from `retry_state`. Strip `retry_run_result` and `stop_run_result` from `IterState` entirely — `IterState` now holds only `actions` and `is_explicit_retry`.

This passes code review independently because: it unifies all decision state in `retry_state`, where `upcoming_sleep` and `next_action` already establish the pattern; decision data now survives beyond `iter()` (it's in `retry_state`, not cleared by `IterState.reset()`); `after`, `before_sleep`, and custom callbacks can observe `retry_state.should_retry` and `retry_state.should_stop` for the first time; `IterState` is simplified to its essential role.

**How it contradicts Improvement 1:** Improvement 1 routes decisions through `Verdict` return values (consumed and applied by the `iter()` loop), keeping storage in `IterState`. Improvement 2 routes decisions directly into `retry_state` fields, eliminating `IterState` as a decision bus entirely. Improvement 1 makes data flow visible in the return channel. Improvement 2 makes data flow visible in the per-attempt record. They are not reconcilable: you cannot simultaneously route decisions through the return channel (Improvement 1) and through `retry_state` direct writes (Improvement 2) without choosing one as canonical.

---

### The Structural Conflict

**The structural conflict that exists only because both improvements are legitimate:**

Retry and stop decisions are simultaneously:

- **Ephemeral computation artifacts** (valid only during a single `iter()` call; meaningless between calls) → belongs in `IterState` (current) or as return values consumed by the loop (Improvement 1)
- **Observable attempt properties** (the outcome of evaluating the retry strategy is a meaningful property of that attempt's evaluation, inspectable by `after`, `before_sleep`, monitoring systems) → belongs in `retry_state` (Improvement 2)

Both improvements are legitimate because both scopes are legitimate. Improvement 1 optimizes for the ephemeral computation model: decisions are computed, applied, discarded. Improvement 2 optimizes for the observable record model: decisions are computed, stored, inspectable across the attempt lifecycle.

These two requirements cannot be satisfied simultaneously by any single storage location. `IterState` fields are reset per `iter()` call: they satisfy ephemerality but sacrifice observability. `retry_state` fields persist per attempt: they satisfy observability but survive longer than the evaluation phase that produced them, making them stale after `prepare_for_next_attempt()` resets them. Return values (Improvement 1) are ephemeral but require the loop to consume and re-store them — routing them back into `IterState`.

The structural conflict, made visible only by both improvements being legitimate: **retry/stop decisions are owned by the evaluation phase but needed by the observation phase, and these phases have incompatible lifetime requirements.** The current architecture resolves the conflict by choosing ephemerality (`IterState`) and silently sacrificing observability — `after` and `before_sleep` callbacks receive `retry_state` but cannot read why the retry was decided. Improvement 1 adds return-channel visibility without changing ephemerality. Improvement 2 adds persistence without addressing the loop's data model. Neither resolves the conflict; each chooses a different partial answer.

The conflict itself is what L8's framework could not see: L8 looked at the boundary between `__iter__` and `__call__`, tracing data across the protocol divide. This analysis looks inward at the action chain and finds that the chain's own data model has no coherent answer to the question "when does a retry decision stop being valid?" — and that this question's unanswerability is the deepest structural property the Pipeline Simulacrum conceals.
