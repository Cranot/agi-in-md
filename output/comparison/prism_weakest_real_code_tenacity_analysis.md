# STRUCTURE FIRST — Level 12 Meta-Conservation Analysis
## Tenacity Retry Library (jd/tenacity/__init__.py)

---

## STAGE 1: FALSIFIABLE CLAIM

**The deepest structural problem:** Tenacity **sacrifices exception-handling transparency for action-composition flexibility**. The code defers critical retry/stop decisions into a queue of callable actions, creating a false appearance of sequential control flow. In reality:

- `_run_retry()` and `_run_stop()` compute decisions and **store results in `self.iter_state`** (side effects)
- `_post_retry_check_actions()` **reads those stored results** and branches queue construction
- The decision point is invisible: decisions are **already made during queue construction**, not during action execution

The execution phase appears to make decisions; it actually enacts decisions made moments earlier. Exception handling is **transparent in action names** (`_run_retry`, `_run_stop`) but **opaque in timing** (when are decisions REALLY made?).

**Falsifiable**: I can trace when retry/stop decisions are computed vs. when they appear to execute.

---

## STAGE 2: DIALECTIC — THREE VOICES

### DEFENDER (structure is sound)
*"The action queue is brilliant precisely because it defers. Each phase constructs the next phase's actions based on previous results:*
- *`_begin_iter` sees the outcome, decides what to queue*
- *`_post_retry_check_actions` sees `retry_run_result`, decides next actions*
- *This is control-flow-as-data. Hooks integrate because actions are just functions."*

### ATTACKER (structure is fragmented)
*"No—exception state is FRAGMENTED across THREE places simultaneously:*
- *`retry_state.outcome` (a Future)*
- *`self.iter_state` bools (retry_run_result, stop_run_result)*  
- *the action queue itself*

*When you read `iter_state.retry_run_result`, you're reading a SHADOW of exception state computed moments ago. By the time you read it, outcome might be None (after `prepare_for_next_attempt()`). This isn't 'deferred control flow'—it's fragmented state hidden in queue syntax."*

### PROBER (questions both)
*"Wait. The queue resets every `iter()` call—it's LOCAL to one iteration, not global. So 'deferral' doesn't cross boundaries. BUT—look at `_run_retry`: it mutates `self.iter_state.retry_run_result`, then `_post_retry_check_actions` READS it. Why both mutations and reads of shared state? And why does outcome get set in `retry_state` but decision results in `iter_state`?*

*The real pattern: immediate mutation (`iter_state` flags) + deferred mutation (action queue). Both are mutations of shared state. The queue doesn't defer DECISIONS—it defers SIDE-EFFECTS on retry_state. Decisions are made immediately in `_run_retry`, stored in `iter_state`, then actions use those stored decisions to mutate `retry_state` again.*

*So the queue is a CONTAINER for state transformations, not a control-flow mechanism."*

---

### GAP BETWEEN ORIGINAL AND TRANSFORMED CLAIM

| Original | Transformed |
|----------|-------------|
| "Deferral hides when decisions fire" | "Queue is LOCAL to one iteration; exception state is FRAGMENTED across outcome/iter_state/actions; queue amplifies fragmentation, doesn't defer it" |

**Concealment Mechanism:** The code hides fragmentation by encoding **state mutations as action callables**. When you see `self._add_action_func(self._run_retry)`, you think "this runs later." But really it's "this function mutates `self.iter_state.retry_run_result`, and subsequent actions in the queue will READ that mutation." The action queue syntax makes the DEPENDENCY between mutations invisible.

---

## STAGE 3: APPLY CONCEALMENT MECHANISM

The code conceals its problems by letting state transformation hide inside function calls:

```python
# You see this:
self._add_action_func(self._run_retry)  # "retry happens later"
self._add_action_func(self._post_retry_check_actions)  # "check happens later"

# But really:
# (1) _run_retry() mutates self.iter_state.retry_run_result
# (2) _post_retry_check_actions() READS self.iter_state.retry_run_result
# (3) based on that bool, it queues more actions
# This is a DATA DEPENDENCY hidden inside function composition.
```

---

## STAGE 4: GENERATIVE CONSTRUCTION #1 — IMPROVEMENT THAT DEEPENS CONCEALMENT

**Proposed "improvement": Explicit Action Protocol** (This looks MORE legitimate but DEEPENS the problem)

```python
from abc import ABC, abstractmethod

class Action(ABC):
    @abstractmethod
    def execute(self, retry_state, context):
        """Each action self-contained; no shared iter_state."""
        pass

class RetryDecisionAction(Action):
    def __init__(self, retry_strategy):
        self.retry_strategy = retry_strategy
    
    def execute(self, retry_state, context):
        # Compute decision, return it
        result = self.retry_strategy(retry_state)
        return {"should_retry": result}

class AfterAction(Action):
    def __init__(self, after_hook):
        self.after_hook = after_hook
    
    def execute(self, retry_state, context):
        if self.after_hook:
            self.after_hook(retry_state)
        return {}

# In _begin_iter:
def _begin_iter(self, retry_state):
    self.iter_state.reset()
    fut = retry_state.outcome
    
    if fut is None:
        self._enqueue_action(AttemptAction())
        return
    
    # Queue actions. Each carries its own "context" of prior decisions.
    decision = self._dequeue_prior_decision()  # Where does this come from?
    if not decision["should_retry"]:
        self._enqueue_action(SuccessAction())
        return
    
    self._enqueue_action(AfterAction(self.after))
    # ... more actions
```

**Why this deepens concealment:** It makes the code LOOK more like a "proper" action pipeline where each action is an independent object. But now the question "where do decision results go?" is even MORE hidden. In the original code, they're in `iter_state`—visible, if confusing. In the improved version, they're in... `_dequeue_prior_decision()`? A cache? A thread-local? The design pushes the fragmentation one layer deeper.

---

## STAGE 5: THREE PROPERTIES VISIBLE ONLY BECAUSE I TRIED TO STRENGTHEN IT

1. **Decision result threading is MANDATORY:** When I tried to make actions "pure" (self-contained), I discovered that RetryDecisionAction computes a bool, and AfterAction must READ that bool. The decision result must be THREADED between iterations or stored somewhere. In the original code, it's stored in `self.iter_state`—visible! In my improved version, I have to call `_dequeue_prior_decision()`, which exposes that decisions MUST be saved. The fragmentation is unavoidable.

2. **Two-phase action construction is structural:** My improvement revealed that iter() has TWO PHASES:
   - Phase 1: Compute decisions (retry_decision, stop_decision) based on exception
   - Phase 2: Branch queue construction based on those decisions
   
   In the original code, these phases are implicit in the ordering of `_begin_iter` → `_post_retry_check_actions`. When I tried to make it explicit, I discovered you CANNOT eliminate the two-phase structure. Phase 2 actions depend on Phase 1 decisions.

3. **Non-local state is not optional:**  My improved version's `_dequeue_prior_decision()` must store the decision SOMEWHERE (object attribute, cache, thread-local, closure). You cannot have Phase 2 decisions depend on Phase 1 results AND have all state be local to individual actions. It's mathematically impossible within a single iteration.

---

## STAGE 6: APPLY DIAGNOSTIC TO MY IMPROVEMENT

**What does my "improved" version conceal?**

- **The symmetry is a lie:** RetryDecisionAction and AfterAction look the SAME (both inherit from Action), but they are not. RetryDecisionAction is a GATE—it MUST complete before AfterAction can proceed. All other actions are sequential. By making them all inherit from Action, I've hidden that the design is a DAG (directed acyclic graph), not a pipeline. Some stages block; some don't.

- **Scope leakage is pushed out of view:** My `_dequeue_prior_decision()` must access state from OUTSIDE the current action. Whether I thread it or store it, I'm reaching out of scope. The original code makes this visible: `self.iter_state.retry_run_result` is RIGHT THERE, non-local. My improved code hides the non-locality behind a method call.

- **The choice between parameter threading and object state is false:** If I thread decisions through all actions (parameter), every action becomes stateful and the "pure action" promise breaks. If I store decisions in object state, I'm right back to `self.iter_state` fragmentation. My improvement conceals that **there is no third option within a single-threaded-iteration model**.

---

## STAGE 7: SECOND IMPROVEMENT — ADDRESSING THE RECREATED PROPERTY

The property I recreated: **Gates are hidden inside the action pipeline.**

**New improvement: Make gates explicit and first-class.**

```python
@dataclasses.dataclass(slots=True)
class DecisionGate:
    name: str
    decision_fn: callable
    result_field: str
    blocking: bool = True

class BaseRetrying:
    def __init__(self, ...):
        self.decision_gates = [
            DecisionGate("retry", self.retry, "retry_result", blocking=True),
            DecisionGate("stop", self.stop, "stop_result", blocking=True),
        ]
    
    def iter(self, retry_state):
        # GATES FIRST: execute all blocking gates before queue construction
        for gate in self.decision_gates:
            if gate.blocking:
                result = gate.decision_fn(retry_state)
                setattr(retry_state, gate.result_field, result)
        
        # NOW construct action queue based on gate results
        self.iter_state.reset()
        if not retry_state.retry_result and retry_state.outcome:
            return retry_state.outcome.result()
        
        # Construct actions...
```

**This reveals:** Gates are FIRST-CLASS and execute before ANY action queue. Decisions happen synchronously, not hidden in action functions.

---

## STAGE 8: APPLY DIAGNOSTIC TO SECOND IMPROVEMENT

**What does EXPLICIT GATES conceal?**

- **Gate serialization is necessary:** By making gates execute sequentially, I've hidden that the retry decision MUST complete before the stop decision can be meaningful. Could they be parallel? No—stopping only makes sense after retry has determined "yes, we're retrying." The serialization is structural, but by making it explicit, I've hidden that the DECISION GRAPH has only one topological order.

- **The "decision → action" dependency is now asymmetrical:** Gates return values; actions consume values. But I've hidden that actions are not truly "consuming" decisions—they're READ-ONLY views of decision results stored on `retry_state`. If an action needed to CHANGE the decision (e.g., a hook that says "actually, don't retry"), it couldn't. The gate protocol hides that decisions are IMMUTABLE once made.

- **Stateless vs. stateful is a false choice:** I've stored gate results on `retry_state` (fields like `retry_result`). The original stored them on `self.iter_state`. Both are mutable objects that persist. Moving them revealed nothing—just shifted where non-locality lives.

---

## STAGE 9: STRUCTURAL INVARIANT (PERSISTS THROUGH ALL DESIGNS)

**The invariant that CANNOT be eliminated:**

***Decision state is always non-local to the action that consumes it.***

- **Original**: `_run_retry` mutates `self.iter_state`, then `_post_retry_check_actions` reads it
- **Improvement #1**: Decision results are stored in a queue-external cache, actions read from it
- **Improvement #2**: Decision results are stored on `retry_state`, gates compute them, actions read them

In ALL designs:
1. Decisions are computed by one function/stage
2. Decisions are stored somewhere (iter_state, cache, retry_state, closure)
3. Actions/subsequent stages READ from that storage

**WHY IS THIS INVARIANT NECESSARY?**

Because retry and stop decisions depend on the SAME exception state (`retry_state.outcome`), they are COUPLED. But they're computed by DIFFERENT strategies (`self.retry`, `self.stop`). Once computed, the results must be available to the NEXT PHASE (queue construction or action execution), which needs BOTH results to decide what to do next.

This creates an unavoidable two-phase structure:
- Phase 1: Compute decisions (retry, stop)
- Phase 2: Use decisions to branch control flow

Decision results CANNOT be local to Phase 1 (Phase 2 needs them). Decision results CANNOT be local to Phase 2 (Phase 1 computed them). Hence, non-locality is STRUCTURAL.

---

## STAGE 10: INVERT THE INVARIANT

**Inverted invariant: Decision state is always LOCAL to the action that uses it.**

This means: every action carries its own decision context; no state is shared between actions.

```python
@dataclasses.dataclass(slots=True)
class ActionContext:
    retry_state: RetryCallState
    retry_decision: bool
    stop_decision: bool
    exception_info: tuple
    seconds_since_start: float

def iter(self, retry_state):
    self.iter_state.reset()
    fut = retry_state.outcome
    
    if fut is None:
        context = ActionContext(
            retry_state=retry_state,
            retry_decision=True,  # Always try at least once
            stop_decision=False,
            exception_info=None,
            seconds_since_start=0
        )
        self._enqueue_action(AttemptAction(context))
        return
    
    # Compute decisions ONCE, IMMEDIATELY
    retry_decision = self.retry(retry_state)
    stop_decision = self.stop(retry_state)
    
    context = ActionContext(
        retry_state=retry_state,
        retry_decision=retry_decision,
        stop_decision=stop_decision,
        exception_info=(..., ..., ...),
        seconds_since_start=retry_state.seconds_since_start
    )
    
    # Now each action is a closure with its own context; no shared iter_state
    if not retry_decision:
        self._enqueue_action(SuccessAction(context))
    else:
        self._enqueue_action(AfterAction(context))
        self._enqueue_action(WaitAction(context))
        self._enqueue_action(StopCheckAction(context))

class SuccessAction:
    def __init__(self, context):
        self.context = context
    
    def __call__(self, retry_state):
        return self.context.retry_state.outcome.result()

class StopCheckAction:
    def __init__(self, context):
        self.context = context
    
    def __call__(self, retry_state):
        if self.context.stop_decision:
            raise RetryError(self.context.retry_state.outcome)
```

**Result:** No `self.iter_state` mutations. Each action is a closure over its own context. Decisions are computed once and frozen.

---

## STAGE 11: NEW IMPOSSIBILITY CREATED BY INVERSION

**Original design can support:** Hooks that see LIVE statistics updated during action execution.

```python
# Original design allows this:
def my_before_sleep_hook(retry_state):
    current_attempts = self.statistics["attempt_number"]  # ← LIVE, updated in real-time
```

**Inverted design CANNOT support:** Hooks cannot see live state because state is frozen in ActionContext.

```python
# Inverted design: hooks see snapshot state, not live
class StopCheckAction:
    def __init__(self, context):
        self.context = context  # Frozen at iter() entry
    
    def __call__(self, retry_state):
        # context.seconds_since_start is stale by the time hook executes
        # self.statistics might have been updated by other actions
```

**New impossibility:** **Hooks cannot have both LOCAL decision context AND FRESH live state.**

---

## STAGE 12: CONSERVATION LAW (BETWEEN ORIGINAL AND INVERTED)

**Original:** Non-local decision state, but hooks can see live statistics.
**Inverted:** Local decision state (frozen in context), but hooks see stale state.

**The conservation law:**

***`(Non-local decision state) ↔ (Non-local hook visibility)`***

You can shift where non-locality lives, but you CANNOT eliminate it.

- **Original** trades decision transparency for state freshness
- **Inverted** trades state freshness for decision transparency

**The product is conserved:**
- Original: LOW decision transparency × HIGH state freshness
- Inverted: HIGH decision transparency × LOW state freshness

Maximize one, minimize the other.

---

## STAGE 13: APPLY DIAGNOSTIC TO THE CONSERVATION LAW

**What does the conservation law conceal?**

It conceals **WHY the choice is forced.** Three stakeholders with conflicting timing requirements:

1. **Decision computation** — must happen after exception is captured
2. **Action execution** — must happen after decisions are made
3. **Hook side-effects** — must happen during action execution AND see current state

**The cycle:** Decisions depend on exceptions. Actions depend on decisions. Hooks depend on actions and live state. Live state is updated by actions. **There is NO total ordering that satisfies all three.**

**Structural invariant of the conservation law itself:**

***The three timing constraints form a CYCLE with no topological order.***

You cannot make all three constraints satisfied simultaneously. You MUST defer one of them.

---

## STAGE 14: META-LAW (CONSERVATION LAW OF CONSERVATION LAWS)

**Invert the invariant:** The three constraints CAN be linearized by deferring one entirely.

- **Option A:** Defer hooks entirely (disable live state access)
- **Option B:** Defer state freshness (freeze state in context, let hooks see snapshots)  
- **Option C:** Defer decision transparency (hide decisions in iter_state)

**The meta-law (specific to Tenacity):**

***All three timing constraints are CONSERVED. Deferring a constraint does not eliminate it; it MOVES the constraint to a different phase, requiring a COMPREHENSIBILITY COST to understand the system.***

- **Original (Option C):** Hides decisions, but readers must reverse-engineer what `iter_state` bools mean — COMPREHENSIBILITY COST = understanding decision timing
- **Inverted (Option B):** Freezes state, but hooks must explicitly reach into non-local `self.statistics` to see live state — COMPREHENSIBILITY COST = understanding state staleness
- **Option A:** Disables hooks, but users must implement retry logic themselves — COMPREHENSIBILITY COST = reimplementing what was removed

**Meta-law equation:** 

***`Comprehensibility_cost(decision_transparency) × Comprehensibility_cost(state_freshness) × Comprehensibility_cost(hook_capability) = constant`***

**You cannot make ALL THREE easy to understand. Pick two.**

The original Tenacity design picks state_freshness + hook_capability, sacrificing decision_transparency. This is why debugging "why did it retry?" is hard—you must trace through iter_state mutations. It's also why the code is fragmented (decisions are shadows in iter_state, exceptions are Futures in retry_state, outcomes are in actions).

---

## STAGE 15: COMPLETE BUG INVENTORY

| # | Location | Bug | What Breaks | Severity | Fixable? | Predicted by Conservation Law? |
|---|----------|-----|-------------|----------|----------|------|
| **1** | `@property statistics` + all mutations | Not thread-safe | Multiple threads updating same dict via threading.local() | **HIGH** | Yes | YES — decision state is non-local; once non-local, thread safety is mandatory |
| **2** | `RetryError.reraise()` | Loses retry context | Original exception is re-raised without `from` chain; retry history invisible | **MEDIUM** | Yes | YES — exception state is stored separately from retry history; reraise chooses which to expose |
| **3** | `iter_state.actions` reset + bound methods | Concurrent iterations corrupt state | If same Retrying used in async context, multiple coroutines share iter_state from threading.local() | **CRITICAL** | Yes (need contextvars) | YES — decision state is thread-local but not task-local |
| **4** | `seconds_since_start` property | Returns None prematurely | If called before outcome_timestamp is set, subsequent code sees None | **MEDIUM** | Yes | YES — exception state timeline is non-linear; outcome_timestamp depends on execution phase |
| **5** | `copy()` method | Doesn't preserve statistics/iter_state | Copying a Retrying mid-retry loses history; fresh state hides prior decisions | **LOW** | Design choice | YES — decision state is non-local; copy() must decide whether to clone or reset |
| **6** | `wraps()` function | `statistics` attribute is non-atomic | Multiple threads call wrapped_f concurrently; each writes to `wrapped_f.statistics`, causing data loss | **MEDIUM** | Yes | YES — statistics are non-local and thread-unsafe |
| **7** | `AttemptManager.__exit__` | Suppresses exceptions silently | Returns `True`, which suppresses the original exception; appears to swallow exceptions | **LOW** | Design choice | PARTIAL — exception handling is deferred into action queue; suppression is intentional but subtle |
| **8** | `prepare_for_next_attempt()` | Clears outcome while actions reference it | Actions queued before `prepare_for_next_attempt()` might reference outcome; design assumes safe timing but is fragile | **LOW** | Yes | YES — decision state is cleared between iterations; actions must not reference cleared state |
| **9** | `_run_wait()` | Sets `upcoming_sleep` to None | If `self.wait` strategy returns None, subsequent actions see None; creates TypeError in `RetryAction(None)` | **MEDIUM** | Yes | YES — wait decision is computed by user strategy; code assumes type safety |
| **10** | `before_sleep` hook | Return values are ignored | Hook can return a new sleep value, but action queue ignores it; hooks must use side-effects, not return values | **MEDIUM** | Yes | YES — hooks are integrated into action queue; action queue ignores return values except DoAttempt/DoSleep |
| **11** | `IterState` mutability | Closures might capture stale state | Action closures capture `self`, which points to iter_state; if iter_state is reset, closures see new state (usually correct, but fragile design) | **LOW** | Yes | YES — iter_state is mutable and shared; closures over `self` are late-binding |
| **12** | `__init__` default params | `retry=None` causes AttributeError | If someone explicitly passes `retry=None`, `_run_retry()` fails with 'NoneType' is not callable | **MEDIUM** | Yes | YES — retry strategy is assumed callable; no validation |
| **13** | `Future.construct()` | No type validation | If `has_exception=True` and `value` is not an Exception, `set_exception()` fails or behaves incorrectly | **LOW** | Yes | YES — exception state must be a real Exception; no validation at construction |

---

## KEY FINDINGS

### Conservation Laws Discovered

1. **Decision Transparency ↔ State Freshness** (Primary)
   - Original: sacrifices decision transparency for hook freshness
   - Inverted: sacrifices hook freshness for decision transparency
   - Product is conserved

2. **Comprehensibility Cost is Conserved** (Meta-law)
   - Cannot make decision transparency + state freshness + hook capability all easy to understand
   - Original chose freshness + capability, lost transparency
   - Pick two; the third becomes a comprehensibility tax

### Root Cause of All 13 Bugs

**Non-local state is structural:** Decision state (retry_run_result, stop_run_result) must be computed in one phase and read in another. The code chose to store this in `self.iter_state`, a mutable object shared across iterations. This creates:

- Thread-safety problems (statistics)
- Async-safety problems (iter_state)
- Closure staleness (actions over self)
- Hook side-effect dependencies (before_sleep return values)

### What the Original Design Gets Right

The action queue pattern is INTENTIONAL and CORRECT. It allows hooks (before, after, before_sleep, after) to integrate cleanly because they execute during action execution, seeing live state. The design chose to maximize hook capability and state freshness.

### What the Inverted Design Would Fix

1. Thread-safety: Each action has its own context snapshot; no shared iter_state
2. Clarity: Decisions are computed upfront in `iter()`, not hidden in action functions
3. Type safety: Decisions are dataclass fields, not bool shadows in iter_state
4. Traceability: `ActionContext` is explicit; you can inspect what decisions each action carries

### What the Inverted Design Would Break

1. **Hook freshness:** Hooks see snapshot state, not live `self.statistics`
2. **Dynamic retry policies:** A hook cannot say "wait, change the sleep duration" (it would need to mutate context)
3. **Debugging live retry:** Can't inspect `self.statistics` during action execution to see real-time retry progress

---

## CONCLUSION: THE STRUCTURAL IMPOSSIBILITY

**Tenacity's "fragmentation" is not a bug—it's the cost of supporting live, stateful hooks within a deferred-execution model.** The action queue is a consequence of trying to satisfy three incompatible constraints:

1. Decisions must be made after exceptions are captured
2. Hooks must execute during action execution  
3. Hooks must see fresh state

No sequential ordering satisfies all three. The code chose to defer decision transparency, trading it for hook freshness. This is why the code is harder to understand (where do decisions come from?), but why hooks work (they see live state).

**The meta-law predicts:** Any redesign that improves decision transparency will reduce hook freshness, and vice versa. You cannot have both without moving the non-locality elsewhere. All 13 bugs are manifestations of this deeper structural trade-off.