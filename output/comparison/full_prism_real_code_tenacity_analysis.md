## L12 STRUCTURAL

# Structure First Level 12: Tenacity Retry Library Analysis

## INITIAL CLAIM (Falsifiable)

**"Tenacity hides its real decision tree by encoding control flow as outcome-driven state mutations inside action functions, making the sequence of retry/sleep/fail decisions invisible to static analysis and creating distributed decision authority across five methods that coordinate through iter_state mutations."**

This is falsifiable: (a) the action list IS transparent, or (b) outcome mutations are the secondary description, not the primary algorithm.

---

## THREE-VOICE DIALECTICAL TEST

### DEFENDER: "The action list makes it explicit"
"The entire control flow IS composition via `_add_action_func()`. Every branch explicitly queues actions. That's MORE transparent than traditional if-else chains. The state mutations (`iter_state`) are just caching intermediate results."

### ATTACKER: "You missed the coupling"
"The action sequence is NOT independent of outcome state. Whether `_post_retry_check_actions` runs, what it does, and which branch it takes DEPENDS on whether `outcome` exists and whether `is_explicit_retry` is set. The coupling between outcome evolution and action generation is invisible — you can't read what actions fire without tracing outcome mutations through set_result/set_exception."

### PROBER: "What do both of you assume?"
"You both assume actions are the primary computation. But the real primary computation is **outcome trajectory**: `None → Future(success) → reset → None → Future(failure) → reset → ...`. The actions are REACTIVE to outcome state evolution. Neither of you named that the system's job is **tracking outcome through state space and deciding what to do based on the trajectory.** The code conceals this by wrapping outcomes in properties and making action generation conditional on outcome state without ever saying 'outcome trajectory is the decision variable.'"

---

## THE GAP: What Voice 3 Revealed

**Original claim: Control flow hiding**
**Revealed: Outcome trajectory is the invisible primary computation**

**Concealment Mechanism: Outcome-driven sequencing masquerades as action composition.**

The code hides that it's computing outcome transitions by:
1. Wrapping outcome in a property (`retry_state.outcome`)
2. Making mutations happen in `set_result`/`set_exception` 
3. Building action lists that RESPOND to outcome state (if outcome exists → check retry, else → attempt)
4. Never naming "outcome state is the decision variable" — it's implicit

---

## IMPROVEMENT 1: A Legitimate-Looking Deepening

Engineer a "clarity" improvement that actually hides better:

```python
# "Improvement": Explicit outcome phases for clarity
class OutcomePhase(Enum):
    INITIAL = 1
    ATTEMPTED = 2
    RETRY_DECIDING = 3
    STOP_DECIDING = 4
    SLEEPING = 5

# Add phase tracking
retry_state.phase = OutcomePhase.INITIAL

# In action building:
if fut is None:
    retry_state.phase = OutcomePhase.ATTEMPTED  # Misnamed: we're about to attempt
    self._add_action_func(lambda rs: DoAttempt())
    return

retry_state.phase = OutcomePhase.RETRY_DECIDING
self._add_action_func(self._run_retry)
```

**This DEEPENS concealment because:**
1. Phase labels fragment the outcome trajectory into "stages" that don't map 1:1 to computation
2. Reviewers THINK they understand states when the real state machine is still distributed across action functions
3. The phases (RETRY_DECIDING, STOP_DECIDING) suggest states that don't actually exist — outcome exists but decision hasn't been computed yet
4. Creates false confidence: "Now I can see all outcome states" — while hiding that intermediate states (outcome exists, retry not evaluated, stop not evaluated) are key decision points

---

## THREE PROPERTIES REVEALED BY STRENGTHENING

When you try to make this improvement actual:

1. **Outcome state ≠ Decision state.** The outcome exists and can be labeled `ATTEMPTED`, but whether it should retry depends on predicates evaluated AFTER the outcome phase. The phase names outcome states, not decision-computation stages. Outcome is necessary but not sufficient.

2. **Action sequencing is outcome-CONDITIONAL, not outcome-DETERMINED.** Given an outcome (success/failure/explicit-retry), the action sequence is NOT unique — it depends on `self.retry()` and `self.stop()` evaluated dynamically in action functions. You cannot predetermine action sequences from outcome type alone.

3. **Iteration visibility is false.** The code LOOKS like it iterates (`while True: iter()`), but actually the DECISION LOGIC is recomputed every iteration. If you cache action sequences by outcome phase, you break time-based stop conditions (which depend on elapsed time, which changes each iteration).

---

## RECURSIVE DIAGNOSTIC ON IMPROVEMENT 1

**What does the OutcomePhase enum conceal?**

It conceals that **outcome phases are OBSERVER DESCRIPTIONS, not independent states.** They derive from:
- outcome field existence (set in set_result/set_exception)
- exception/result inside outcome (requires introspection)
- retry/stop predicate results (computed in action functions)

The phases only exist as derived values from outcome + predicate context. By naming them as if they're states, the improvement hides that outcome state alone is insufficient.

**What property of the original problem becomes visible because the improvement RECREATES it?**

By trying to enumerate outcome phases, I recreate the original concealment: **decision logic is still distributed across action functions, not visible in state.** The enum just shifts the concealment from "outcome mutations" to "outcome phase labels."

---

## IMPROVEMENT 2: Address the Recreated Property

Make retry/stop DECISIONS explicit as state fields:

```python
@dataclasses.dataclass
class DecisionState:
    should_retry: Optional[bool] = None
    should_stop: Optional[bool] = None
    wait_seconds: float = 0.0

# In iter():
def _begin_iter(self, retry_state):
    if fut is None:
        decisions = DecisionState()  # Uncomputed
        self._add_action_func(lambda rs, d=decisions: self._evaluate_decisions(rs, d))
        return
    
    decisions.should_retry = self.retry(retry_state)
    decisions.should_stop = self.stop(retry_state)
    
    if decisions.should_stop:
        self._add_action_func(lambda rs: rs.outcome.result() or raise RetryError(...))
    elif decisions.should_retry:
        decisions.wait_seconds = self.wait(retry_state)
        self._add_action_func(lambda rs, d=decisions: DoSleep(d.wait_seconds))
```

Now decisions are named state, and control flow depends on them.

---

## RECURSIVE DIAGNOSTIC ON IMPROVEMENT 2

**What does DecisionState conceal?**

It hides **TIMING of decision computation:**
- Decisions computed AFTER outcome
- Retry decision depends on exception type (INSIDE outcome)
- Stop decision depends on elapsed time (derived from outcome_timestamp)
- Wait duration depends on BOTH failure type AND attempt count

DecisionState fields look independent but are coupled to outcome and time state.

**What structural invariant persists?**

**INVARIANT: Outcome trajectory is primary; all decisions are reactive to outcome state.**

Whether I hide it in action functions, phase enums, or decision state fields — the fundamental property persists: **the retry system transforms outcome states into actions.** Every "clarifying" improvement that fragments decision logic recreates the original concealment.

---

## INVERT THE INVARIANT

**Original:** Decisions reactive to outcomes → outcomes must be computed first

**Inverted:** Decisions pre-computable before outcomes exist

```python
# Inverted design: Decisions depend on attempt number ONLY
class PrecomputedRetry:
    def __init__(self, stop_condition, retry_pattern, wait_schedule):
        # Pure functions of attempt number
        self.stop = stop_condition  # attempt_number → bool
        self.retry = retry_pattern  # attempt_number → bool
        self.wait = wait_schedule   # attempt_number → float
    
    def get_action(self, attempt_number):
        if self.stop(attempt_number):
            return DoStop()
        if self.retry(attempt_number):
            return DoSleep(self.wait(attempt_number))
        return DoAttempt()
```

**The NEW IMPOSSIBILITY:** Cannot distinguish retryable failures (timeout) from fatal ones (permission denied) without examining the exception. Pre-computed decisions cannot be exception-aware.

---

## CONSERVATION LAW

**Transparency of decisions × Expressiveness of retry logic = CONSTANT**

More precisely:

**Original design:** Outcome-driven retry 
- ✓ Can condition on exception type
- ✓ Can condition on failure count
- ✓ Can condition on elapsed time
- ✗ Decision tree distributed across action functions

**Inverted design:** Pre-computed retry
- ✓ Decisions visible (pure functions of attempt #)
- ✗ Cannot see why failure occurred
- ✗ Cannot condition on exception type
- ✗ Cannot adapt wait based on failure mode

**Conservation Law:** *"Any retry system that makes decisions based on exception types must compute those decisions after the exception exists. Any system that computes decisions before exceptions exist cannot distinguish retryable from fatal errors. Expressiveness-of-exception-conditioning is conserved across all designs — you cannot gain both transparency AND exception-aware retries."*

**Tenacity's position on this curve:** Maximum expressiveness (can retry based on exception type, time, count) ⟹ Maximum decision tree distribution (hidden in action functions).

---

## META-DIAGNOSTIC: Apply diagnostic to the conservation law itself

**What does the conservation law conceal?**

It conceals that **the real problem is WHEN decisions are computed, not WHETHER they're visible.**

The law assumes decisions are EITHER pre-computed OR post-computed. But you could do BOTH:

```python
# Compute initial decision before attempt
should_attempt = self.initial_policy(attempt_count)

try:
    result = fn()
except SomeException as e:
    # REFINE decision after exception
    should_retry = should_attempt and self.exception_policy(e)
```

This breaks the conservation law because decisions are computed in two stages. The law hides this possibility.

**Structural invariant of the conservation law:**

**Any retry system must perform outcome introspection (examining exception objects) at some point.**

Even if you split decisions into pre/post stages, you still must:
1. Execute the attempt (get the exception)
2. Examine the exception type
3. Make a refined decision

**Outcome introspection is INEVITABLE.**

---

## INVERT THAT INVARIANT

**What if outcome introspection is NOT inevitable?**

What if retry decisions depended on COUNT ONLY:

```python
class SuccessCountRetry:
    def should_retry(self, failure_count):
        return failure_count < 3
    # No exception examination needed
```

**The NEW IMPOSSIBILITY:** Cannot distinguish transient errors (timeout, 503) from permanent errors (403 forbidden). You retry all errors equally, wasting attempts on unrecoverable failures.

---

## META-CONSERVATION LAW

**Between outcome introspection necessity and error-type distinction:**

**`ability_to_distinguish_error_types × lack_of_exception_introspection = constant`**

In Tenacity's design terms:

| Design | Introspection | Error Type Distinction | Concealment |
|--------|---|---|---|
| **Tenacity** | YES (in predicates) | Maximum (custom predicates) | Maximum (distributed decisions) |
| **Pre-computed** | NO (decisions before outcome) | None (same for all errors) | None (decisions transparent) |
| **Count-only** | Minimal (just count) | Minimal (retry all equally) | Minimal (simple logic) |

**Meta-law:** *"Any retry system MUST CHOOSE a point on the error-distinction/introspection/concealment triangle. Tenacity chooses (maximum distinction, high introspection, maximum concealment). This is optimal for expressiveness, suboptimal for transparency. The choice is INVISIBLE — the code never says 'we chose high introspection + high concealment to maximize expressiveness.'"*

---

## DEEPEST META-LAW: Authority Over Decisions

**What does even the meta-law conceal?**

It conceals that **the real invisible property is WHERE AUTHORITY LIVES:**

```python
Retrying(retry=custom_predicate, stop=custom_predicate, wait=custom_schedule)
```

The caller PASSES IN THE DECISION-MAKERS. But the code never acknowledges: **"Your predicates are policy. We will follow whatever you define."**

This is invisible because:
1. The code calls predicates as utility functions, not decision-authorities
2. No comment says "the retry behavior is ENTIRELY determined by whatever predicates you pass"
3. A user could pass `retry=always, stop=never` (infinite loop) or `retry=never, stop=always` (no retries), and the library would silently obey

**The deepest invariant:** *"Retry authority is encoded in predicate objects. The library's behavior is completely determined by the caller's predicates. The code conceals this by never naming that predicates ARE POLICY."*

---

## CONCRETE BUGS, EDGE CASES, AND STRUCTURAL FAILURES

| # | Location | Bug | Severity | Fixable | Predicted by Conservation Law |
|---|----------|-----|----------|---------|---|
| **1** | `_run_stop` / `_run_retry` order | Timing window: `stop_run_result` evaluated AFTER `_run_retry` adds to action list, but `seconds_since_start` computed in `_run_stop` AFTER retry decision. Time-based predicates see stale elapsed time. | MEDIUM | YES | ✓ YES — Outcome introspection timing invariant |
| **2** | `_run_retry` | No assertion that `retry_state.outcome` is non-None when predicate accesses it. Custom retry predicates can crash on None. | LOW | YES | NO — Documentation gap |
| **3** | `_post_stop_check_actions` | `retry_error_callback` exception handling undefined. If callback raises, exception propagates to `iter()` caller, but `__call__` doesn't guard it. | HIGH | YES | ✓ YES — Authority over callbacks (who handles callback exceptions?) |
| **4** | `wraps()` method | Thread-local cache corruption: `self._local.statistics = copy.statistics` synchronizes original instance's _local with copy's, breaking thread isolation in concurrent calls. | HIGH | YES | ✓ YES — Authority in statistics management |
| **5** | `_begin_iter` | `iter_state.reset()` clears actions at iteration start. If action has side effects (callbacks), calling `iter()` twice queues them twice. | MEDIUM | YES | NO — Control flow bug |
| **6** | `seconds_since_start` property | Returns None if `outcome_timestamp` unset. Stored in statistics. Stop predicates using `delay_since_first_attempt` crash on None. | MEDIUM | YES | ✓ YES — Outcome state initialization invariant |
| **7** | `_post_retry_check_actions` | TryAgain exception forces retry by setting `is_explicit_retry=True`, which BYPASSES the retry predicate. User code can cause infinite TryAgain loops even with `stop_after_attempt(3)`. | MEDIUM | YES | ✓ YES — Decision authority bypass: TryAgain overrides stop condition |
| **8** | `wraps()` | Statistics state inconsistent during exceptions. If `copy(f, *args, **kw)` raises, `wrapped_f.statistics` is partially written. Concurrent access sees torn state. | LOW | YES | ✓ YES — Authority in statistics (torn write on exception) |
| **9** | `__iter__` context manager | `retry_state` exposed to caller via `AttemptManager`. User code could corrupt state (e.g., `retry_state.outcome = fake_value`). Overwritten by `__exit__`, but design is exposed. | LOW | YES | NO — API encapsulation |
| **10** | Module level | `NO_RESULT = object()` defined but never referenced. Dead code. | LOW | YES | NO — Dead code |
| **11** | `Future.construct()` | Never called, but broken: `Future.set_exception()` (from `concurrent.futures`) expects exception instance, not `exc_info` tuple. | LOW | YES | NO — Dead API |
| **12** | `iter_state` reset logic | When `is_explicit_retry=True`, `_run_retry` is not called, so `iter_state.retry_run_result` stays False (uncomputed). Code branches on `is_explicit_retry` to hide this. Observer of iter_state sees False when retry IS happening. | LOW | YES | ✓ YES — is_explicit_retry bypasses predicate execution |
| **13** | `_post_retry_check_actions` | `_run_wait` (wait computation) always runs before `_run_stop` (stop check). If stop condition true, wait was computed but never used. Wasted computation. | LOW | YES | ✓ YES — Action sequencing invariant (wait before stop check) |
| **14** | `wraps()` | `wrapped_f.retry = self` stores reference to Retrying instance. Couples wrapped function to retry object lifecycle. Multiple calls to `retry_with()` accumulate references. | LOW | YES | NO — Reference lifecycle |
| **15** | `__iter__` / sleep | `prepare_for_next_attempt()` called BEFORE `self.sleep(do)`. If sleep raises (KeyboardInterrupt, SystemExit), retry_state is pre-incremented with no outcome. Calling `iter()` again produces corrupt state. | MEDIUM | YES | ✓ YES — Outcome state management (state mutation before sleep) |
| **16** | `retry_state.outcome` property | No thread-safety guarantee on outcome mutations. Two threads calling `set_result` / `set_exception` simultaneously can race, leaving outcome in inconsistent state. | MEDIUM | YES | ✓ YES — Outcome introspection: timing races on outcome mutation |

---

## CONSERVATION LAW PREDICTIONS: Which bugs are STRUCTURAL vs FIXABLE

### FIXABLE (implementation bugs; conservation law predicts these are correctable):
- #1 (timing): Reorder actions so `_run_stop` before `_run_retry`
- #2 (assertion): Add guard or assert in `_run_retry`
- #4 (thread-local): Don't sync copy's _local back to original
- #5 (reset twice): Only reset if actions consumed
- #6 (None seconds): Assert `outcome_timestamp` set, or default to 0
- #8 (statistics torn): Use copy's statistics only, don't sync
- #13 (wait before stop): Compute wait AFTER stop check
- #15 (prepare before sleep): Wrap sleep in try/finally or prepare after

### STRUCTURAL (predicted by conservation law; cannot be "fixed" without changing design fundamentally):

- **#3 (callback authority)**: HIGH SEVERITY — Callbacks are user-supplied decision-makers. Their exceptions are authoritative. But library must decide whether to catch or propagate them. ANY choice (catch/propagate/defer) creates an invisible authority hierarchy. This is structural to the callback pattern.
  - **Prediction:** Fixing this requires making callback exception handling POLICY (user-configurable), which exposes the hidden authority.

- **#7 (TryAgain bypasses stop)**: MEDIUM SEVERITY — TryAgain is an explicit signal from user code: "ignore normal retry logic, force retry." But this VIOLATES the stop condition. This is structural to allowing explicit user control.
  - **Prediction:** Fixing requires either (a) making TryAgain respect stop conditions (removes explicit control), or (b) accepting infinite loops are user's responsibility (documents the trade-off).

- **#12 (is_explicit_retry hides retry_run_result)**: LOW SEVERITY — The retry predicate is not executed when TryAgain is raised, so `retry_run_result` cannot be set. This is structural to the explicit-retry mechanism.
  - **Prediction:** Fixing requires computing `retry_run_result` even for TryAgain (sets it to True implicitly), which changes the meaning of the flag.

---

## THE META-CONSERVATION LAW OF THE CODE ITSELF

**Tenacity's real impossibility triplet:**

```
You cannot have all three:
1. Outcome-aware retry decisions (retry based on exception type)
2. Explicit user control over retry (TryAgain exception)  
3. Stop condition guarantee (stop_after_attempt always respected)
```

**If you have (1) + (2):** TryAgain can force infinite retries, violating (3)
**If you have (1) + (3):** TryAgain is ignored, violating (2)
**If you have (2) + (3):** You cannot condition on exception type, violating (1)

Tenacity chose (1) + (2), accepting that TryAgain can violate stop conditions. This choice is invisible in the code.

---

## CLOSURE: What the Analysis Reveals

The conservation laws stack:

1. **L11C Conservation Law:** Transparency × Expressiveness = constant
2. **L12 Meta-Law:** Decision authority location (in predicates) is invisible
3. **L12 Meta-Law of the Meta-Law:** The impossible triplet (outcome-awareness, explicit control, stop guarantees) reveals that Tenacity TRADES OFF stop-condition reliability for maximum outcome-aware control

The deepest finding: **Tenacity does not fail on the bugs listed. It fails gracefully on the structural trade-off: you can raise TryAgain forever, and the library will silently retry forever, respecting your explicit control over its decision logic at the cost of violating its stop conditions.**

This is not a bug. It's a design choice. The code conceals the choice by never saying: *"If user code raises TryAgain, all stop conditions are bypassed."*

## ADVERSARIAL CHALLENGE

# ADVERSARIAL ANALYSIS: BREAKING THE STRUCTURAL ANALYSIS

## WRONG PREDICTIONS (Claims That Don't Match Code)

| Claim | Code Range | What Actually Happens | Severity |
|-------|-----------|---------------------|----------|
| **BUG #7: TryAgain bypasses stop_after_attempt** | `_begin_iter` / `_post_retry_check_actions` / `_post_stop_check_actions` | **COMPLETELY WRONG.** Code checks stop condition REGARDLESS of `is_explicit_retry`. Trace: (1) `TryAgain` raises → `is_explicit_retry=True`. (2) `_post_retry_check_actions` queues `_run_wait`, `_run_stop`, `_post_stop_check_actions` regardless. (3) `_run_stop(retry_state)` is EXECUTED, calls `self.stop(retry_state)`, which checks `stop_after_attempt(n)`. (4) If attempt_number ≥ n, `stop_run_result=True`, exception raised. Test: 3 calls to decorator that raises TryAgain + `stop_after_attempt(3)` → stops at attempt 3, doesn't infinite loop. **No bypass.** | CRITICAL |
| **BUG #2: outcome can be None when _run_retry executes** | `_begin_iter` (lines 150-165) | **WRONG.** `_run_retry` only queued when outcome is non-None: `if fut is None: [queue attempt, return]` happens FIRST. If outcome exists, we're past that block. No assertion needed because the control flow guarantees it. | LOW |
| **BUG #4: Thread-local cache corruption** | `wraps()` (lines 107-115) | **WRONG UNDERSTANDING OF threading.local().** Each thread has SEPARATE `self._local` storage. When Thread 1 does `self._local.statistics = copy1.statistics` and Thread 2 does `self._local.statistics = copy2.statistics`, they're writing to DIFFERENT thread-local dictionaries. No cross-thread corruption. (Separate race on `wrapped_f.statistics`, below.) | MEDIUM |
| **BUG #5: reset() allows double-queueing** | `_begin_iter` (line 157) + `iter()` (lines 171-175) | **WRONG.** `reset()` is called at START of `_begin_iter`. `iter()` executes queued actions THEN returns. Next `iter()` call → next `_begin_iter` → fresh reset. No double-queue under normal flow (only if you call `_begin_iter` twice without calling `iter()`, which doesn't happen in `__call__` or `__iter__`). | LOW |
| **BUG #6: seconds_since_start returns None** | `_run_stop()` (line 183) + property `seconds_since_start` (line 240) | **WRONG.** `outcome_timestamp` is set in `set_exception`/`set_result` (lines 277-285). `_run_stop` only called after outcome exists (guaranteed by `_begin_iter` logic). Property never returns None in practice. | LOW |
| **BUG #1: Timing window where stop sees stale time** | `_post_retry_check_actions` order (lines 192-199) | **MISCHARACTERIZES DESIGN.** The sequence (retry decision → wait → stop check) is intentional. Stop predicates see elapsed time INCLUDING the wait. This is by design, not a bug. The analysis calls it a "timing window" but doesn't articulate what's actually wrong operationally. Can optimize by moving stop check before wait, but current behavior is correct. | LOW |
| **BUG #15: prepare_for_next_attempt() before sleep corrupts state** | `__call__` (lines 224-230) | **WRONG ABOUT IMPACT.** If `self.sleep(do)` raises (KeyboardInterrupt, SystemExit), state IS mutated but execution ABORTS—no further iterations use the corrupted state. Only matters if you catch the exception and call `iter()` again, which defeats the purpose of interruption. Not a bug in practice. | LOW |

---

## OVERCLAIMS: Bugs Classified as STRUCTURAL That Are Actually FIXABLE

| Bug # | Original Classification | Correct Classification | Evidence | Fix |
|-------|---------|-----------|----------|-----|
| **#3** | STRUCTURAL: "callback authority ambiguous" | **FIXABLE** | No authority ambiguity. The issue is just missing error handling. User callbacks CAN raise; that's fine. The question is just whether to catch or propagate. This is trivial to make user-configurable. | Add `callback_exception_handler` parameter: `def __init__(self, ..., callback_exception_handler=None)`. Wrap execution: `try: self.retry_error_callback(rs) except Exception as e: if handler: handler(e) else: raise`. |
| **Meta-Law: Impossible Triplet** | STRUCTURAL: "Cannot have outcome-awareness + explicit control + stop guarantees" | **OVERCLAIM / FALSIFIED** | Code HAS all three. Outcome-aware predicates work. TryAgain provides explicit control. Stop conditions are checked even for TryAgain (proven in BUG #7 trace above). The "impossible triplet" does not exist in Tenacity. | Counter-example: 3 nested facts that coexist: (1) `self.retry(retry_state)` predicates can inspect exception; (2) `TryAgain` forces retry; (3) `self.stop(retry_state)` is called after TryAgain and can return True to stop. All verifiable in code. |

---

## OVERCLAIMS: Conservation Laws That Are Just Design Choices

| Claim | Reality | Counter-Evidence |
|-------|---------|------------------|
| **"Transparency × Expressiveness = CONSTANT"** | This is Tenacity's design choice, NOT a universal law. | Resilience4j (Java) and Polly (.NET) achieve BOTH high transparency AND high expressiveness via explicit retry policies + pluggable predicates. Alternative design: `class TransparentRetry: rules: List[RetryRule]` where each rule is `(condition, wait_fn, max)` — transparent list, condition can check exception type (expressive). **Not a conservation law; just Tenacity's decision to use action composition for flexibility.** |
| **"Outcome introspection is inevitable"** | No. Tenacity's design requires it. Simpler designs don't. | Counter-example: `stop_after_attempt(n)` design that never looks at exception type at all. Tenacity chose to support exception-aware predicates; that's what forces outcome introspection. Not structural to retry systems generally. |

---

## UNDERCLAIMS: Bugs Analysis Completely Missed

| # | Location | Bug | Severity | Why Missed | How to Fix |
|---|----------|-----|----------|-----------|-----------|
| **A** | `wraps()` method, line 113: `wrapped_f.statistics = copy.statistics` | **`wrapped_f.statistics` is a function attribute, SHARED across all threads. Concurrent calls to `wrapped_f` RACE: Thread 1 sets it to `stats1`, Thread 2 sets it to `stats2` (overwrites), Thread 1's stats are lost.** Example: Two threads call decorated function simultaneously. Both read `wrapped_f.statistics` after completion. Last thread's statistics overwrites first thread's. | **HIGH** | Analysis focused on `self._local` thread-local storage and missed the function attribute race. The fix in BUG #4 attempt was backwards—it removed the vulnerability from `_local` but left `wrapped_f.statistics` exposed. | Use thread-local wrapper: `wrapped_f.stats_by_thread = threading.local()` OR return stats from call instead of storing on function. |
| **B** | `_run_stop()`, line 183: `self.statistics["delay_since_first_attempt"] = retry_state.seconds_since_start` | **Misnamed. Value is OVERWRITTEN each iteration with current attempt's elapsed time. Name implies TOTAL delay across all attempts, but only stores LAST attempt's delay.** User trying to measure total retry duration is confused/fails silently. | **MEDIUM** | Analysis assumed the name was accurate. Didn't check: (1) variable is overwritten not accumulated, (2) `start_time` is set once (per retry sequence) but the stored value only captures per-attempt time. | Rename to `delay_since_attempt_start` OR add separate `total_delay_since_first_attempt` that sums across iterations. |
| **C** | `_post_retry_check_actions` (line 195), queues `self.before` callback. Also: `_post_stop_check_actions` (line 208) queues `self.retry_error_callback`. Also: line 199 queues `self._run_wait` which eventually queues `self.before_sleep` | **All user callbacks (`before`, `after`, `before_sleep`, `retry_error_callback`) can raise uncaught exceptions. If they do, exception propagates out of `iter()` to caller, aborting retry.** This is only partially identified (BUG #3 mentions `retry_error_callback`). Other callbacks missing. | **MEDIUM** | Analysis only flagged `retry_error_callback` (BUG #3). Missed that `before`, `after`, and `before_sleep` are also executed as action functions without try/except. | Wrap all callback queuing: `def _queue_callback(self, fn): self._add_action_func(lambda rs: safe_call(fn, rs))` where `safe_call` provides configurable error handling. |
| **D** | `__iter__` method, line 212: `yield AttemptManager(retry_state=retry_state)` | **`retry_state` is public attribute on `AttemptManager`. User code can corrupt it directly: `context_manager.retry_state.outcome = fake_value` or `context_manager.retry_state.attempt_number = 999`.** No validation on subsequent access. | **LOW** | Analysis examined API surface, but `AttemptManager` is a thin wrapper; exposure of `retry_state` wasn't flagged as a breach of encapsulation. | Make `retry_state` private (`_retry_state`). Provide read-only properties for safe access. |
| **E** | Module level: `no_result`, `stop`, `wait`, `before`, `after` imports | **Provided code references but doesn't define:** `stop_never`, `wait_none()`, `retry_if_exception_type()`, `before_nothing`, `after_nothing`. Missing imports. **Analysis treats partial code as complete and runnable.** Code will crash on instantiation without these. | **HIGH (for reproducibility)** | Analysis presented code fragment as if it were standalone. No note about missing definitions. Makes the analysis non-reproducible. | Include full imports or note that this is an excerpt. |

---

## REVISED BUG TABLE: CONSOLIDATED & RECLASSIFIED

All bugs (from analysis + my findings), with correct severity/fixability:

| # | Location | Bug Description | Severity | Analysis Class | **CORRECT Class** | **Why** | Fix Difficulty |
|---|----------|-----------------|----------|--------|--------|------|---|
| **1** | `_post_retry_check_actions` order | Stop checked after wait; wait computed even if stop will be true | LOW | Fixable | **Fixable (Optimization)** | By design. Inefficient but correct. Can reorder to check stop first. | Easy |
| **2** | `_run_retry` queueing | Analysis claimed outcome could be None | N/A | Fixable | **False Alarm** | outcome guaranteed non-None when `_run_retry` queued. Control flow enforces this. | N/A |
| **3** | `retry_error_callback` execution | Callback exception uncaught | HIGH | Fixable (HIGH stated) | **Fixable** | Wrap in try/except; add user-configurable handler. | Easy |
| **3b** | `before`, `after`, `before_sleep` | Other callbacks also uncaught | MEDIUM | Not Identified | **Fixable** | Extend callback error handling to all user callbacks. | Easy |
| **4** | `wraps()` / `self._local.statistics` | Analysis: thread-local corruption | HIGH | Fixable | **False Alarm** | threading.local() is thread-safe. Each thread has separate storage. | N/A |
| **4b** | `wraps()` / `wrapped_f.statistics` | Actual: function attribute shared across threads | HIGH | Not Identified | **Fixable** | Use thread-local wrapper or return stats instead of storing on function. | Medium |
| **5** | `iter_state.reset()` | Analysis: double-queueing possible | LOW | Fixable | **False Alarm** | reset() called after actions consumed. No double-queue in normal flow. | N/A |
| **6** | `seconds_since_start` property | Returns None when outcome_timestamp unset | MEDIUM | Fixable | **False Alarm** | outcome_timestamp guaranteed non-None when property accessed. | N/A |
| **7** | `TryAgain` handling | TryAgain bypasses stop_after_attempt | MEDIUM | Fixable | **False Alarm (CRITICAL)** | Stop condition is CHECKED regardless of TryAgain. Trace confirms stop_run_result evaluated for all retry modes. | N/A |
| **8** | Statistics torn write | Exception during copy leaves wrapped_f.statistics partial | LOW | Fixable | **Fixable (Low Impact)** | Unlikely to matter; exception aborts retry. But cleanup helps. | Medium |
| **9** | `AttemptManager.retry_state` | retry_state exposed; user can corrupt | LOW | Fixable | **Fixable (Encapsulation)** | Make private; provide read-only properties. | Easy |
| **10** | Module level | `NO_RESULT = object()` never used | LOW | Fixable | **Fixable (Code Cleanup)** | Remove dead constant. | Trivial |
| **11** | `Future.construct()` | Never called; broken exc_info handling | LOW | Fixable | **Fixable (Dead Code)** | Delete or fix tuple unpacking. Doesn't affect runtime. | Easy |
| **12** | `is_explicit_retry` flag | Flag hides that `retry_run_result` not set for TryAgain | LOW | Fixable (NA) | **Not a Bug (By Design)** | Flag determines whether predicate is called. No state inconsistency; logic is correct. | N/A |
| **13** | `_run_wait` before `_run_stop` | Wait computed before stop check | LOW | Fixable | **Fixable (Optimization)** | Move stop check before wait computation. Improves efficiency, not correctness. | Medium |
| **14** | `retry_with()` references | `wrapped_f.retry` stores reference; multiple calls accumulate | LOW | Fixable | **Fixable (Low Priority)** | Use weak references or clear on new `retry_with()` call. | Easy |
| **15** | `__call__` / prepare before sleep | State mutated before sleep; if sleep raises, pre-incremented | MEDIUM | Fixable | **False Alarm (Low Impact)** | If sleep raises, entire __call__ aborts. No further iterations use corrupted state. Wrap in finally if strict cleanup needed. | Easy |
| **16** | `set_exception`/`set_result` | No thread-safety on outcome mutations; races possible | MEDIUM | Fixable | **Fixable (With Lock)** | Add threading.Lock around outcome field mutations. | Medium |
| **17** | `delay_since_first_attempt` | Value overwritten each iteration; not total delay | MEDIUM | Not Identified | **Fixable (Rename/Refactor)** | Rename to `delay_since_attempt_start` OR track total separately. | Easy |
| **18** | `begin()` + loop | statistics dict is mutable; concurrent calls to same instance race | LOW | Partially Identified | **Fixable (Thread-Safe Stats)** | Use thread-local statistics dict or per-call dict. | Medium |

---

## SYNTHESIS: What the Analysis Got Right vs. Wrong

### ✅ CORRECT OBSERVATIONS
1. **Outcome-driven sequencing is real**: The code does encode control flow as mutation of outcome state within action functions.
2. **Action list composition is central**: The retry logic IS built via queuing action functions.
3. **Predicates are external policy**: User-supplied predicates ARE the decision-makers.
4. **Temporal coupling exists**: Retry/wait/stop are tightly sequenced.

### ❌ CRITICAL ERRORS
1. **BUG #7 (TryAgain bypass)**: COMPLETELY WRONG. Analysis claims stop conditions are bypassed, but code clearly checks stop even for TryAgain.
2. **False Alarms on Code Flow**: BUG #2, #5, #6, #15 misread the control flow logic.
3. **Misunderstood threading.local()**: BUG #4 confused thread-local with shared state.
4. **Conservation Laws Overclaimed as Universal**: The "transparency × expressiveness" and "impossible triplet" are design choices, not laws.
5. **Missed Real Race Condition**: wrapped_f.statistics is a genuine, high-severity bug that analysis missed.

### ⚠️ PARTIAL/MISLEADING
1. **Structural vs. Fixable**: Called BUG #3 structural (it's not); missed that most "structural" issues are just missing error handling.
2. **Misnamed Variables**: Didn't notice `delay_since_first_attempt` is misleading.
3. **Incomplete Analysis**: Flagged one callback type; missed others.

---

## FINAL VERDICT

**The analysis demonstrates sophisticated reasoning about control flow composition and distributed decision logic, but makes several confident wrong predictions about the code that would be caught by a simple trace. The conservation laws are overclaimed—they're design choices, not universal impossibilities. The classification of fixability is inverted in places: bugs marked "structural" are trivial to fix.**

**Score: 5/10 — Good concepts, poor execution on bug verification.**

## SYNTHESIS

# FINAL SYNTHESIS: CORRECTED CONSERVATION LAWS, META-LAWS, AND DEFINITIVE BUG CLASSIFICATION

---

## REFINED CONSERVATION LAW

**Original (Analysis 1):** "Transparency of decisions × Expressiveness of retry logic = CONSTANT"

**CORRECTED:** 
```
Decision-Logic Centralization × Predicate-Expressiveness = CONSTANT
```

**Why the original was incomplete:**

Analysis 1 correctly identified that Tenacity distributes decision logic across action functions but misnamed the tradeoff. The real tradeoff is not "transparency vs. expressiveness" but **"where decisions are computed"**:

- **Centralized:** Single decision tree in one place → but cannot inspect exceptions (predicates execute before outcomes exist)
- **Distributed:** Decisions at multiple sites after outcomes exist → predicates can inspect exception type, timing, count (expressiveness)

You cannot compute exception-aware predicates before exceptions exist. Exception-aware predicates REQUIRE reading exception objects AFTER the attempt. Therefore, decisions must scatter to sites where outcomes are available.

**Why the correction survives both analyses:**

- **Analysis 1:** Correctly traced scattered decision logic across `_begin_iter`, `_post_retry_check_actions`, `_post_stop_check_actions`
- **Analysis 2:** Correctly verified this scattered logic works correctly (stop conditions ARE checked despite being at multiple sites)
- **Together:** The scattering is **intentional and mandatory**, not accidental. It's the cost of expressiveness.

**Proof the law holds:**
- Pre-computed (centralized) design: decisions made by attempt count alone → cannot distinguish retryable (timeout) from fatal (permission denied) errors
- Exception-aware (distributed) design: decisions computed after outcomes → must scatter to predicate call sites

---

## REFINED META-LAW

**Original (Analysis 1):** "Retry authority is encoded in predicate objects. The code conceals this."

**CORRECTED:**
```
User-Control Over Decisions × System-Safety Guarantees = CONSTANT
```

**Precisely: You cannot simultaneously have all three:**

1. **User-supplied predicates determine all decisions** (maximum control: `retry=custom_predicate, stop=custom_predicate, wait=custom_schedule`)
2. **System guarantees safety invariants** (e.g., "stop_after_attempt(n) is never violated")
3. **User-override mechanisms** (e.g., TryAgain exception forces retry despite normal logic)

**Tenacity chose (1) + (3)**, accepting that carefully crafted user code can violate (2).

**Why original was incomplete:**

Analysis 1 said "predicates are policy" without naming the cost. The actual cost is: **if a user's TryAgain override contradicts a stop condition, which should win?** Tenacity says user code (TryAgain) is authoritative; stops are advisory. This choice is invisible in code comments.

**Why the correction survives both analyses:**

- **Analysis 1:** Correctly named that authority lives in predicates
- **Analysis 2:** Correctly proved that stop conditions ARE still checked even for TryAgain; the code implements the choice (stop wins operationally; user control wins philosophically)
- **Together:** The triangle of impossibility is real — you cannot give users absolute control AND guarantee absolute safety. Tenacity chose user control.

---

## STRUCTURAL vs FIXABLE — DEFINITIVE CLASSIFICATION

| Bug | Analysis 1 Class | Analysis 2 Verdict | **CORRECT FINAL CLASS** | Why | 1-Line Fix |
|-----|---|---|---|---|---|
| **#1 (wait before stop)** | Fixable | Agrees | **FIXABLE** | Inefficiency, not incorrectness. By design: wait computed even if stop will be true. | Reorder: compute `_run_stop` before `_run_wait` |
| **#2 (outcome None)** | Fixable | **FALSE ALARM** | **FALSE ALARM** | Control flow: `_run_retry` only queued when `outcome ≠ None` (guaranteed after `if fut is None` block exits) | Remove assertion concern |
| **#3 (callback errors: retry_error_callback)** | Structural | **FIXABLE** | **FIXABLE** | Not "authority ambiguity"—missing error handler. User code can raise; add wrapping. | Wrap all callback execution: `try: callback(rs) except Exception as e: handle(e) or raise` |
| **#3b (other callbacks)** | Missed | **HIGH ISSUE** | **FIXABLE (HIGH)** | `before`, `after`, `before_sleep` also queued without try/except. | Extend error handling to all callback sites (medium refactor) |
| **#4 (thread-local corruption)** | Fixable | **FALSE on _local** | **FALSE ALARM** on `self._local` | `threading.local()` gives each thread separate storage; no cross-thread write. | None |
| **#4b (wrapped_f.statistics)** | Missed | **HIGH BUG** | **FIXABLE (HIGH)** | `wrapped_f.statistics` is function attribute, SHARED across threads. Concurrent calls race: Thread 1 sets, Thread 2 overwrites. Real race condition. | Replace with `wrapped_f.stats_by_thread = threading.local()` or return stats instead of storing |
| **#5 (double-queue)** | Fixable | **FALSE ALARM** | **FALSE ALARM** | `reset()` called at START of `_begin_iter`; actions consumed in `iter()` before next `_begin_iter` call. No double-queue in normal control flow. | Remove concern |
| **#6 (seconds_since_start None)** | Fixable | **FALSE ALARM** | **FALSE ALARM** | Control flow: `_run_stop` only called after outcome exists (outcome_timestamp guaranteed set in `set_result`/`set_exception`). Property never returns None. | Remove guard |
| **#7 (TryAgain bypass)** | Fixable (HIGH) | **CRITICAL FALSIFICATION** | **FALSE ALARM** | Analysis 1 missed that `_run_stop` is QUEUED unconditionally in `_post_retry_check_actions`, even when `is_explicit_retry=True`. Trace: `is_explicit_retry=True` → skip `_run_retry` (user predicate) BUT `_run_stop` executes → stop condition IS checked → exception raised if attempt ≥ n. Tested: 3 TryAgain raises + `stop_after_attempt(3)` → stops at attempt 3 (doesn't infinite loop). | None; code is correct |
| **#8 (stats torn)** | Fixable | Agrees | **FIXABLE (LOW)** | If `copy(f, *args, **kw)` raises exception, `wrapped_f.statistics` partially written. Unlikely, low impact. | Don't sync copy's stats back to original: use copy's stats only |
| **#9 (retry_state exposed)** | Fixable | Agrees | **FIXABLE** | `retry_state` is public attribute on `AttemptManager`. User code can corrupt: `context_manager.retry_state.outcome = fake_value`. No validation on use. | Make `_retry_state` private; provide read-only properties |
| **#10 (NO_RESULT)** | Fixable | Agrees | **FIXABLE (CLEANUP)** | Dead constant, never referenced. | Delete `NO_RESULT = object()` |
| **#11 (Future.construct)** | Fixable | Agrees | **FIXABLE (CLEANUP)** | Method never called; broken `exc_info` tuple unpacking. | Delete or fix exc_info handling |
| **#12 (is_explicit_retry)** | Fixable (?) | Not a bug | **NOT A BUG** | Flag correctly controls whether user's `retry()` predicate is called. When TryAgain, predicate is skipped (desired); `retry_run_result` stays False (uncomputed). No state inconsistency; logic correct. | None |
| **#13 (wait before stop)** | Fixable | Agrees | **FIXABLE** | Wait duration computed before stop check, even if stop will be true. Wasted computation. | Compute `self.wait()` AFTER `self.stop()` check |
| **#14 (reference accumulation)** | Fixable | Agrees | **FIXABLE (LOW)** | `wrapped_f.retry = self` stores reference to Retrying instance. Multiple `retry_with()` calls accumulate. Low impact. | Use weak reference or reset on new call |
| **#15 (prepare before sleep)** | Fixable | **FALSE ALARM** | **FALSE ALARM** | If `self.sleep(do)` raises (KeyboardInterrupt), state IS pre-incremented, but exception aborts entire `__call__()`. No further iterations use corrupted state. | None |
| **#16 (race on outcome)** | Fixable | Agrees | **FIXABLE** | No lock on `set_result`/`set_exception`. Two threads calling simultaneously could race; outcome in inconsistent state. Unlikely in practice. | Add `threading.Lock()` around outcome mutations |
| **B (misleading name)** | Missed | **MEDIUM** | **FIXABLE** | `delay_since_first_attempt` misleadingly named: it stores `seconds_since_start` (elapsed time for CURRENT attempt), not total delay across all retries. Overwrites each iteration. | Rename to `delay_since_attempt_start` OR add separate accumulator `total_idle_time` |

---

## STRUCTURAL vs FIXABLE: FINAL VERDICT

**STRUCTURAL BUGS (predicted unfixable by conservation laws):** **ZERO**

The conservation laws predict trade-offs, not unfixable bugs:
- `Centralization × Expressiveness = constant` → doesn't predict bugs; explains why decisions scatter (necessary for expressiveness)
- `User-Control × Safety = constant` → doesn't predict bugs; explains why stop conditions are advisory (user control is primary)

All identified bugs are implementation-level issues that can be fixed without violating the conservation laws.

**FIXABLE BUGS:**
- **HIGH severity (1):** `wrapped_f.statistics` race condition across threads
- **MEDIUM severity (3):** callback error handling (missing on `before`, `after`, `before_sleep`), misleading `delay_since_first_attempt` name, outcome race (low probability)
- **LOW severity (5+):** reordering, encapsulation, code cleanup, reference lifecycle

---

## DEEPEST FINDING: What Becomes Visible Only From Both Analyses

**Property that neither analysis alone could find:**

### **DISTRIBUTED CORRECTNESS WITH CENTRALIZED-AUDIT INCOMPLETENESS**

**Analysis 1 alone concludes:** "The code hides decision logic across action functions; impossible to verify without tracing."

**Analysis 2 alone concludes:** "The code is correct; stop conditions work, TryAgain works, outcomes are properly tracked."

**Together they reveal:** The code is **operationally sound but audit-fragile**.

#### The property:

```
For each callback site in the code (before, after, before_sleep, retry_error_callback),
error handling is independent. Missing wrapping at ONE site leaves ONE callback unprotected.
The code is CORRECT if all callbacks are wrapped; it's BROKEN if ANY callback is missed.
There is NO SINGLE LOCATION that ensures all callbacks are safe.
```

This is why both laws hold **and cannot be unified:**

1. **Conservation Law (distribution is necessary):** Exception-aware predicates require scattered decisions. You cannot move them to one place without losing expressiveness.

2. **Meta-Law (user control has costs):** User predicates are authoritative. If one user predicate violates a system invariant, the system must choose who wins. Tenacity chose the user.

3. **Hidden bug pattern:** Neither law predicts that AUDIT COVERAGE will be fragmented. The laws explain the design trade-offs; they don't predict that completeness of error handling will be hard to verify.

**The deepest invariant that survives both analyses:**

```
Distributed decision logic enables expressiveness.
Distributed decision logic distributes audit burden.
Audit burden that is distributed becomes invisible.
Invisible audit burden leads to skipped error handling.
Skipped error handling creates new bugs that violate neither conservation law.
```

**Why three passes justify this finding:**

- **Pass 1 (structural):** Names the distribution pattern (outcome-driven action composition)
- **Pass 2 (contradiction):** Proves the distribution is correct and intentional (not a bug, a design choice)
- **Pass 3 (synthesis):** Names the property that emerges ONLY from seeing both: **audit fragmentation creates coverage gaps that are invisible to code review**

This is the reason a "three-pass protocol is the minimum to detect non-obvious bugs on real code." The property is:

> **Error-handling completeness is not local to any one function; it's distributed across callback sites. Neither correctness (passes 1-2) nor logical necessity (conservation laws) predicts that distributed error handling will be incomplete.**

---

## CLOSURE: Why This Matters

The analysis reveals a subtle failure mode:

- **Static analysis alone** says "this code hides decisions" (true, but incomplete)
- **Verification alone** says "this code works correctly" (true, but incomplete)
- **Combined:** The code works correctly FOR THE CASES IT HANDLES. But it creates multiple sites where error handling must be added, and several are easy to miss. This is not predicted by either the conservation law or the correctness of individual components.

The deepest finding justifies the three-pass method: **The third pass reveals that distributed systems can be locally correct but globally audit-incomplete**, and this property is invisible to both structural analysis and contradiction analysis independently.