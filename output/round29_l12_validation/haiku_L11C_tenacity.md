# Conservation Law Analysis: Tenacity Retry Library

## Initial Claim
**Deepest structural problem**: The code conflates decisions with executions by deferring retry decisions from decision-time to execution-time through action queueing. The action pipeline (`iter_state.actions`) is built eagerly across `_begin_iter()`, `_post_retry_check_actions()`, and `_post_stop_check_actions()`, encoding decisions made under specific state conditions. But those decisions are executed later in `iter()`, when the state assumptions may have changed. This creates an invisible temporal contract: *the system commits to a decision sequence without re-validating that the state assumptions underlying those decisions still hold*.

---

## Three-Expert Transformation

**Defender** ("This is compositional design"):  
"The action queue is brilliant. It decouples decision-making from execution, lets you compose complex retry logic through method chaining, and keeps the main loop clean. You can build decision trees without deep nesting."

**Attacker** ("This is hidden mutation"):  
"The queue is fragmented across three methods. If `outcome` changes between `_begin_iter()` and `_post_retry_check_actions()`, you execute wrong actions. The state machine is implicit — buried in which methods call which."

**Prober** ("What's the actual contract?"):  
"Wait. When does `outcome` become immutable? Is it guaranteed stable between `_begin_iter()` and action execution? Who enforces that? And what if a queued action modifies something that another queued action depends on? The action list order is decision order, but is that the execution order you want?"

**Transformed claim** (synthesized):  
The real problem is that **decisions are encoded as state changes (action queueing), not as explicit conditionals**. Readers see method calls but not *why* they queue actions or *what conditions* those queue operations depend on. The coupling between decision and execution is neither transparent nor testable in isolation.

---

## Concealment Mechanism: "Sequential Deference"

**How this code hides its problems**:

The code hides that it's making critical decisions (should I retry? should I stop? should I sleep?) by translating those decisions into *side effects on a queue*. When you read `_post_retry_check_actions()`, you don't see:
```
IF retry==true THEN queue(after); queue(wait); queue(stop_check)
```

You see:
```python
if not (self.iter_state.is_explicit_retry or self.iter_state.retry_run_result):
    self._add_action_func(lambda rs: rs.outcome.result())
    return
# ... then queue more
```

The decision boundary is obscured by **re-interpreting state mutations as control flow**. Each `_add_action_func()` call is a decision, but it's presented as a side effect.

---

## Deepening Concealment: The "Smart Validator" Improvement

**Legitimate-looking improvement that strengthens concealment**:

```python
def _validate_and_cache_action_sequence(self):
    """Cache validated action sequences to avoid re-evaluation."""
    cache_key = (
        id(self.iter_state.retry_run_result),
        id(self.iter_state.stop_run_result),
        len(self.iter_state.actions)
    )
    if not hasattr(self, '_action_cache'):
        self._action_cache = {}
    
    if cache_key not in self._action_cache:
        self._action_cache[cache_key] = list(self.iter_state.actions)
    
    self.iter_state.actions = self._action_cache[cache_key]

# Call this in iter() before executing actions
def iter(self, retry_state):
    self._begin_iter(retry_state)
    self._validate_and_cache_action_sequence()  # NEW
    result = None
    for action in self.iter_state.actions:
        result = action(retry_state)
    return result
```

**Why it deepens concealment**:  
This "optimization" adds another layer of indirection (cache lookup based on state snapshots) while appearing to be a safety measure ("validated and cached"). It actually **makes the decision-to-execution gap MORE opaque**, because now you've explicitly cached a decision sequence — which commits you even harder to the assumption that state won't change. Readers see "validation" and "caching" and think safety; they don't see they're now *betting state is immutable*.

---

## Three Properties Revealed by the Attempted Improvement

1. **Decision-execution temporal gap is real and dangerous**: The caching mechanism exposes that there IS a gap. If you're caching decisions, you're admitting decisions made now may not be valid later. The cache key itself reveals which state variables "matter" — and the code doesn't prove they're immutable.

2. **Outcome stability is assumed but never enforced**: The cache key includes `id(self.iter_state.retry_run_result)` but not the actual outcome object. This reveals a hidden assumption: the outcome won't change its identity or content between `_begin_iter()` and action execution. But nothing in the code enforces this.

3. **Action queue order encodes decision priority, not execution necessity**: By caching the sequence, you've made explicit that action order IS decision order. But now you can see that some actions (like `before`, `after`, `sleep`) are *decorations* around the core decision (`DoAttempt`, `DoSleep`, exception handling). The core decisions are buried in the sequence.

---

## Diagnostic Applied to the Improvement

The "smart validator" conceals that it's introducing **commit brittleness**. It looks like it's making the system safer by caching valid sequences. But what it actually does is **replace runtime re-evaluation with static commitment**. The original code re-evaluates conditions each time `iter()` is called; the "improved" code commits to a sequence based on state at cache-population time.

This reveals the original problem more sharply: **the action queue is a commitment device disguised as a data structure**. By queuing actions, you're saying "given the state right now, these are the decisions we make." But if state changes, that commitment is invalid.

---

## Second Improvement: Decision Checkpointing

**Addressing the re-validated property**:

```python
def iter(self, retry_state):
    self._begin_iter(retry_state)
    result = None
    for action in self.iter_state.actions:
        # CHECKPOINT: Verify state assumptions before each action
        self._verify_action_preconditions(action, retry_state)
        result = action(retry_state)
    return result

def _verify_action_preconditions(self, action, retry_state):
    """Validate that preconditions for this action still hold."""
    # If we queued this action assuming outcome exists, it must still exist
    if hasattr(action, '__name__') and 'outcome' in action.__name__:
        if retry_state.outcome is None:
            raise RuntimeError(
                f"Precondition violated: {action.__name__} requires outcome, "
                f"but it's None. State changed during action queueing."
            )
```

**What this reveals**: The action queue depends on implicit preconditions. The original code *assumes* that if you queued an action based on a certain state, that state will still be true during execution. This second improvement makes that assumption visible — and fragile.

---

## Structural Invariant

**The property that persists through every improvement**:

**Temporal Decoupling + State Coupling = Structural Impossibility**

Formally:
- *Decisions are made at time T₁* (when `_begin_iter()` and subsequent methods run)
- *Decisions are executed at time T₂* (inside `iter()`'s for loop)
- *State assumptions are encoded in the decision (action queue)* but state can change between T₁ and T₂
- *No mechanism re-validates preconditions at execution time*

The invariant: **You cannot fully decouple decision-making from state updates without either (a) freezing state, (b) re-checking preconditions, or (c) risking broken assumptions.**

Every improvement (caching, checkpointing, reordering) either makes the commitment MORE explicit (hidden worse) or adds re-validation (higher cost). You cannot eliminate the problem without changing the architecture.

---

## Inversion: Synchronous Decision-Execution

**Making the impossible property trivially satisfiable**:

Design where decisions happen *exactly* when actions execute:

```python
def iter(self, retry_state):
    self.begin()
    while True:
        # DECIDE NOW based on CURRENT STATE
        if retry_state.outcome is None:
            # First attempt: decide inline
            if self.before:
                self.before(retry_state)
            action = DoAttempt()
        else:
            # Mid-retry: decide based on current outcome
            should_retry = self.retry(retry_state)
            if not should_retry:
                return retry_state.outcome.result()
            
            if self.after:
                self.after(retry_state)
            
            sleep_time = self.wait(retry_state) if self.wait else 0
            should_stop = self.stop(retry_state)
            
            if should_stop:
                raise self.retry_error_cls(retry_state.outcome)
            
            action = DoSleep(sleep_time)
        
        # EXECUTE ACTION based on decision just made
        if isinstance(action, DoAttempt):
            yield AttemptManager(retry_state)
        elif isinstance(action, DoSleep):
            retry_state.prepare_for_next_attempt()
            self.sleep(action)
        else:
            break
```

In this design, there's no temporal gap — decisions are made inline. State assumptions can't be violated because you're reading state and acting on it in the same scope.

---

## New Impossibility Created by Inversion

**The inverted design creates**: **State explosion and decision entanglement**.

Without the action queue to buffer decisions, retry state now has to carry:
- Outcome (which attempt succeeded/failed)
- Retry decision (should we try again?)
- Wait time (how long to sleep?)
- Stop decision (have we exhausted retries?)
- Whether we already ran `before`/`after` callbacks
- Whether the next action is sleep or attempt

The original design was solved the problem with a queue; now you solve it with more *direct state tracking*. You've made decision-execution synchronous, but you've made state management implicit again.

---

## Conservation Law

**State Transparency ↔ Behavioral Coupling**

| Dimension | Original (Queue) | Inverted (Sync) |
|-----------|------------------|-----------------|
| Decision visibility | Low (encoded as actions) | High (inline conditionals) |
| State decoupling | High (queue separates decisions from execution) | Low (state tightly bound to control flow) |
| Precondition checking | Implicit (assumed stable) | Explicit (re-evaluated per iteration) |
| Cognitive load to understand | "What actions get queued?" | "What state determines which branch?" |

**The Conservation Law**: 
$$\text{Decision-Execution Coupling} \times \text{State Transparency} \approx \text{constant}$$

**Precise formulation**: *The less tightly coupled decisions are to their execution context, the less transparent the decision criteria become. Conversely, the more transparent decision criteria are (made explicit via inline conditionals), the tighter the coupling to current state.*

Original design: HIGH decoupling, LOW transparency → action queue hides decisions  
Inverted design: LOW decoupling, HIGH transparency → state coupling hides what state variables matter

**What a senior engineer would NOT already know**:

1. **The action queue is solving a *transparency/decoupling trade-off*, not just enabling composition.** They'd think it's about code reuse; it's actually about being able to build complex decision trees without making every decision criterion visible in the code.

2. **The retry library's architecture is fundamentally *non-linear* in its complexity.** Adding one more callback (before_sleep) or one more stop condition doesn't linearly add state tracking burden — the queue lets you add new decision points without re-architecting precondition management.

3. **Retry logic is structurally *isomorphic to event sourcing*.** The action queue IS an event log. Each action represents "given the state at this point, do this." The library just doesn't persist it. If you tried to add distributed retry (across processes), you'd immediately reinvent event sourcing to solve the same problem: how do you commit to decisions made under old state assumptions?

---

## Prediction: Event-Sourced Hybrid

**A third design that neither original nor inverted attempted**:

```python
@dataclass
class Decision:
    decision_point: str  # "retry_check", "stop_check", "sleep_duration"
    preconditions: dict  # What state had to be true
    outcome: Any        # What decision was made
    timestamp: float    # When was it made

class Retrying(BaseRetrying):
    def __init__(self, *args, audit_decisions=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.audit_decisions = audit_decisions
        self._decision_log = []
    
    def iter(self, retry_state):
        self._begin_iter(retry_state)
        result = None
        
        for action in self.iter_state.actions:
            if self.audit_decisions:
                # Log preconditions for this action
                preconditions = self._extract_preconditions(action)
                decision = Decision(
                    decision_point=getattr(action, '__name__', 'unknown'),
                    preconditions=preconditions,
                    outcome=action,
                    timestamp=time.monotonic()
                )
                self._decision_log.append(decision)
            
            result = action(retry_state)
        
        return result
```

**This design predicts you'd discover:**

1. **Preconditions are NOT uniformly distributed** — some decisions (retry_check) require outcome to exist; others (sleep_duration) require retry was true. The decision tree has implicit *layers* of dependencies that the action queue obscures.

2. **Decision coupling creates a "critical path"** — some actions can only run if previous actions ran. By making decisions explicit, you'd see that `_post_stop_check_actions` *depends* on `_run_stop` having run first. The queue enforces this ordering implicitly; an audit log would make it explicit and enable optimization (run independent decisions in parallel).

3. **The retry library could support transactional rollback of decisions** — if `before_sleep` callback fails, you could use the decision log to "undo" the decision to sleep and re-enter from a decision checkpoint, rather than letting the exception propagate.

**And the conservation law still holds**: By making decisions explicit (via audit logging), you've made it possible to parallelize independent decisions or roll back failed decisions. But you've added overhead — every decision now generates a log entry, and you need to manage the lifetime of that log. You've traded execution simplicity for decision auditability.
