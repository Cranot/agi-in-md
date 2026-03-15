# Level 12 Meta-Conservation Analysis: Tenacity Retry Library

## 1. Initial Claim

**Deepest structural problem**: The code conflates two incompatible responsibilities—**composable policy** (stop, wait, retry predicates presented as reusable components) and **execution choreography** (action sequencing and state tracking). This creates the illusion of modular composition while hiding a fixed temporal dependency. The action queue model obscures that "retry," "wait," and "stop" are not independent policies—they form an ordered logical sequence: *retry must be evaluated before wait, wait must be evaluated before stop*. The code hides this by using a composable API (copy(), wraps(), per-policy inheritance) that suggests interchangeable parts, when in fact the sequence is structurally invariant.

---

## 2. Three-Voice Dialectic

**DEFENDER**: "The design is actually modular. Policies ARE independent—they take a retry_state and return a decision. The engine orchestrates them. That's separation of concerns. The copy() method proves reusability: you can swap retry strategies, wait strategies, stop strategies independently. Statistics are just side effects of execution, not coupling."

**ATTACKER**: "It's broken modularity. The iter_state is mutable shared state living in thread-local storage. Multiple threads retry on the same Retrying object = iter_state collision. Policies can't see past decisions because they're ephemeral—each iteration resets the queue. The queue itself IS state coupling. And when _post_retry_check_actions calls _run_wait, it assumes _run_retry set iter_state.retry_run_result. That's implicit ordering hardcoded into method sequencing."

**PROBER**: "Both miss the core. The real problem is temporal: policies appear to be called 'as needed' but actually operate in a fixed sequence. The action queue is a symptom, not the disease. The disease is this: **the code must decide 'should we retry?' before it computes 'how long to sleep', but it must compute sleep before deciding 'should we stop?'** That ordering is not flexible—it's logical. Yet the API presents policies as composable. That gap between 'composable API' and 'fixed sequence' is where the concealment lives."

**Gap**: Original claim = "policies leak into state." Transformed claim = "the composable API hides that policies are not independent—they're sequential stages of a single decision process disguised as modular callbacks."

---

## 3. Concealment Mechanism

The code conceals its sequential nature through **action queue indirection**. When `_begin_iter()` populates `iter_state.actions`, it builds a list of callables. When `iter()` executes them in order, that order looks like it emerges from state (outcomes determining what gets queued), not from pre-ordained structure.

But the sequencing is actually hardcoded: `_begin_iter` → `_post_retry_check_actions` → `_post_stop_check_actions` always produces the same stage structure. The action queue makes this look *implicit* (determined by outcomes and conditions) when it's actually *explicit* (baked into method calls).

The concealment works because:
1. **Action queue looks dynamic**: It's built fresh each iteration—appears to adapt.
2. **Policies appear independent**: Each policy is a separate callable, passed at init.
3. **Sequence is buried in method calls**: `_post_retry_check_actions` calling `_run_wait` then `_run_stop` is harder to see than a comment saying "retry → wait → stop."

---

## 4. Legitimate-Looking Improvement That Deepens Concealment

**Improvement**: Introduce an explicit **PolicyResolver** that pre-computes the action sequence before iteration, separate from the execution engine.

```python
class PolicyResolver:
    def __init__(self, stop, wait, retry, after, before_sleep):
        self.stop = stop
        self.wait = wait
        self.retry = retry
        self.after = after
        self.before_sleep = before_sleep
    
    def resolve_sequence(self, retry_state):
        """Pre-compute the full action sequence for this state."""
        sequence = []
        
        if retry_state.outcome is None:
            # First attempt
            sequence.append(('before',))
            sequence.append(('attempt',))
            return sequence
        
        # Outcome exists—check if we retry
        if self.retry(retry_state):
            if self.after:
                sequence.append(('after',))
            sequence.append(('wait', self.wait(retry_state)))
            sequence.append(('check_stop',))
            
            if self.stop(retry_state):
                sequence.append(('raise_error',))
            else:
                sequence.append(('next_retry',))
        else:
            sequence.append(('return_result',))
        
        return sequence
```

Then refactor `BaseRetrying.__iter__` to use it:

```python
def __iter__(self):
    self.begin()
    retry_state = RetryCallState(self, fn=None, args=(), kwargs={})
    resolver = PolicyResolver(self.stop, self.wait, self.retry, self.after, self.before_sleep)
    
    while True:
        sequence = resolver.resolve_sequence(retry_state)
        for action_tuple in sequence:
            action_type = action_tuple[0]
            if action_type == 'attempt':
                yield AttemptManager(retry_state)
            elif action_type == 'wait':
                sleep_duration = action_tuple[1]
                self.sleep(sleep_duration)
                retry_state.prepare_for_next_attempt()
            # ... handle other action types
```

**Why this LOOKS like an improvement**:
- Separates policy resolution from execution (SoC)
- Pre-computes the sequence before iteration (determinism)
- Makes the action graph explicit (clarity)

**Why it deepens concealment**:
1. The resolver itself EMBODIES the sequential logic. It's no longer distributed across `_begin_iter`, `_post_retry_check_actions`, `_post_stop_check_actions`. It's now concentrated in `resolve_sequence()`. This makes it HARDER to see that the sequence is hardcoded, because the hardcoding is now in one place (looks like "the resolver decides this") rather than across multiple methods.
2. By pre-computing, it suggests that policies are truly independent inputs to a generic decision engine—when in fact the resolver's decision tree IS the policy. Policies become slots in the resolver's if-statement.
3. It hides that the resolver has baked-in assumptions: "if retry, then maybe wait, then check stop." These assumptions are now implicit in the resolver's structure, not explicit in method names.

---

## 5. Three Properties Visible Only Through Attempting This Improvement

### Property 1: **Policy Entanglement**
The sequence of decisions cannot be separated from the sequence of actions. When you try to pre-compute the sequence, you discover that `retry()` decision determines whether `wait()` is even called. The wait result determines whether `stop()` sees that sleep duration. **Policies are not independent; they form a chain where output of one becomes input to the next.** The original design hides this by routing outcomes through method calls; the improvement exposes it by forcing the sequence into a single place.

### Property 2: **Outcome-Dependent Ordering**
The action sequence's structure depends on whether `retry_state.outcome` is None. The policies aren't deciding "what to do"—they're deciding "which branch to take." But the branches are mutually exclusive: if outcome is None, you attempt; if not, you retry/stop/sleep. **The code hides that there are really two different state machines (first attempt vs. retry attempt), not one flexible policy system.** Trying to pre-compute reveals you need conditional logic at the top level (if outcome is None) hardcoded into the resolver.

### Property 3: **State Reification**
Building the sequence upfront means `retry_state` must contain all information needed at all decision points. But which information? If a policy needs `outcome_timestamp`, you must compute it before calling policies. If policies need `upcoming_sleep`, you must compute wait duration before calling stop. **The pre-computation forces you to reify decisions as state fields.** This exposes that policies are not stateless callables—they're methods that depend on hidden state that must be computed in a specific order.

---

## 6. Apply Diagnostic to the Improvement

What does the PolicyResolver conceal?

**The resolver ITSELF is the policy.** The sequential logic (if outcome is None, do this; if retry and not stop, do that) is no longer distributed—it's now in `resolve_sequence()`. The concealment is deeper because it's *more centralized*: the resolver appears to be a neutral arbiter ("I'm just pre-computing what the policies say"), but it's actually the brain. Policies are now oracles that feed the resolver; the resolver is the decision-maker.

The improvement recreates the original temporal coupling problem: `resolve_sequence()` must be called at the right moment (after outcome is set, before execution). If you call it too early, retry_state is stale. The pre-computation suggests you can call it once and reuse the result, but you can't—outcomes change between iterations.

---

## 7. Second Improvement Addressing the Recreated Problem

Instead of pre-computing, **make policies explicit about their dependencies**:

```python
@dataclasses.dataclass
class PolicyRequirement:
    name: str
    required_fields: set  # {'outcome', 'attempt_number', 'upcoming_sleep', ...}

class Policy(ABC):
    @abstractmethod
    def requires(self) -> PolicyRequirement:
        """Declare what fields from retry_state this policy needs."""
        pass
    
    @abstractmethod
    def decide(self, retry_state) -> Any:
        """Return decision (bool, float, etc.)."""
        pass

class DeclaredRetryPolicy(Policy):
    def requires(self):
        return PolicyRequirement('retry', {'outcome'})
    
    def decide(self, retry_state):
        return isinstance(retry_state.outcome.exception(), TransientError)

class DeclaredStopPolicy(Policy):
    def requires(self):
        return PolicyRequirement('stop', {'attempt_number', 'upcoming_sleep', 'outcome'})
    
    def decide(self, retry_state):
        return retry_state.upcoming_sleep > 60  # Stop if next sleep > 60s
```

The engine now **validates** that policies are called in an order that satisfies their dependencies:

```python
def _validate_call_order(self):
    """Ensure stop() never called before upcoming_sleep is set."""
    retry_deps = self.retry.requires().required_fields
    wait_deps = self.wait.requires().required_fields
    stop_deps = self.stop.requires().required_fields
    
    # If stop requires 'upcoming_sleep', it must be called after wait
    if 'upcoming_sleep' in stop_deps and wait_deps:
        # Enforce: wait() must be in the sequence before stop()
        pass
```

This second improvement **forces dependency ordering to be explicit**, which forces the engine to guarantee those fields exist before calling each policy.

---

## 8. Apply Diagnostic to Second Improvement

What does this improvement conceal?

**Declaring dependencies suggests the problem is missing visibility.** But the improvement recreates the original problem in a new form: if `stop()` requires `upcoming_sleep`, then `wait()` must be called first. The improvement doesn't eliminate the ordering constraint—it just moves it from implicit (buried in method calls) to explicit (buried in dependency graphs).

The second improvement hides that **policies form a DAG (directed acyclic graph) of dependencies, not a set of independent decisions.** By declaring requirements, the design suggests "if we just make dependencies visible, the engine can handle any order." But you can't. If a policy requires a field computed by another policy, the ordering is mandatory.

---

## 9. Structural Invariant

**Invariant**: "The retry decision (should we retry?) cannot be separated from the sleep decision (how long?) without creating either (a) stale policy inputs or (b) implicit ordering constraints."

This invariant persists across all three designs:

- **Original design** (action queues): `_run_retry` sets `iter_state.retry_run_result` → `_run_wait` reads it implicitly via sequencing.
- **PolicyResolver**: `resolve_sequence()` calls `retry()` then `wait()` in code order.
- **Dependency declarations**: `wait()` requires outcome; `stop()` requires `upcoming_sleep` (transitively requires wait).

The invariant holds because the problem is STRUCTURAL: "You must evaluate whether to retry BEFORE you can decide to stop, but you must compute sleep duration IN BETWEEN."

---

## 10. Invert the Invariant

**Original invariant**: "Retry and sleep decisions are coupled; they must be made sequentially."

**Inverted**: "Make sleep and stop decisions independent; compute both before evaluating retry."

**New design** (inverted):

```python
def iter_inverted(self, retry_state):
    """Decide 'how long to sleep' and 'when to stop' BEFORE deciding to retry."""
    
    # Stage 1: Decide the sleep duration (speculative, for all attempts)
    sleep_duration = self.wait(retry_state)
    
    # Stage 2: Decide the stop condition (knowing the sleep duration)
    should_stop = self.stop(retry_state)  # Now sees upcoming_sleep!
    
    if should_stop:
        # We've decided to stop. Now check: should we even retry?
        if not self.retry(retry_state):
            # Didn't want to retry anyway
            raise RetryError(retry_state.outcome)
        else:
            # Wanted to retry but hit the stop condition
            raise RetryError(retry_state.outcome)
    
    # We're not stopping. So retry applies.
    if self.retry(retry_state):
        return RetryAction(sleep_duration)
    else:
        return retry_state.outcome.result()
```

This inverts the sequence: **sleep → stop → retry** instead of **retry → sleep → stop**.

---

## 11. New Impossibility

The inversion creates a new impossibility: **"The stop decision (stage 2) now must see the sleep duration (stage 1), but the retry decision (stage 3) might want to veto the stop condition. Stage 3 might say 'actually, don't retry,' which makes the sleep duration irrelevant. So you've computed the sleep speculatively, without knowing if you'll use it."**

More concretely: In the original design, you compute sleep duration *only if you're going to retry*. In the inverted design, you compute it speculatively, even if you'll end up not retrying.

---

## 12. Conservation Law (Original vs. Inverted)

**Original design**: retry → wait → stop. **Sequence**: outcome determines all three in order. **Cost**: You only compute sleep if retrying.

**Inverted design**: wait → stop → retry. **Sequence**: You compute sleep speculatively. **Cost**: Wasted computation when you don't retry.

**Conservation law**: "The temporal ordering of decisions is redistributed, but the total dependencies are conserved. In the original, 'retry result influences sleep (implicitly via iter_state)' and 'sleep result influences stop (implicitly via upcoming_sleep).' In the inverted, 'wait result influences stop (explicitly in the signature).' Both have three policies with two dependency edges. The graph topology is the same; only the direction changed."

**More specifically**: "You cannot eliminate the coupling between 'sleep decision' and 'stop decision.' In the original, sleep comes first; stop sees it. In the inverted, stop must see sleep before deciding. The fundamental constraint is: **stop's decision may depend on sleep's output, so stop cannot be called before sleep is computed.** This is not a design choice; it's a logical requirement (if the stop condition is 'sleep duration exceeds timeout,' stop must come after sleep)."

---

## 13. Apply Diagnostic to the Conservation Law

What does the conservation law conceal?

The law states: "Coupling shifts but does not vanish; the graph has the same edges." 

**This conceals that the laws of different designs are measuring different things.** In the original, we're measuring "how many dependencies exist between policies." In the inverted, we're measuring "in what order are they called." These are not commensurable. You could have the same dependency graph but different call orders if policies were lazy (computed only when needed) rather than eager (computed before use).

The conservation law hides the NATURE of coupling. It says "coupling is conserved" as if coupling is a substance. But coupling is not substance—it's **information flow**. In the original, the information flows outward from the outcome: outcome determines retry, retry determines wait, wait determines stop. In the inverted, the information flows sideways: wait and stop are independent; they don't feed each other. The graph topology is the same (three nodes, two edges), but the **semantics** are different.

---

## 14. Invariant of the Conservation Law

The invariant that persists through improvement attempts is:

**"Any retry system must couple 'stop decision' and 'sleep decision' because stop might need to depend on how long the next sleep will be. The order (wait → stop or stop → wait) can flip, but the dependency cannot be severed."**

This is true: if `stop` has a condition like "abort if next sleep > 60 seconds," then `wait` must be called first.

---

## 15. Invert the Conservation Law's Invariant

**Original invariant**: "Stop and sleep decisions must be coupled because stop might depend on sleep duration."

**Inverted**: "Create a design where stop NEVER depends on sleep duration; make them fully independent."

How? **Separate the two decision types**.

```python
class SeparatedRetry:
    def __init__(self, retry_predicate, stop_predicate, wait_calculator, 
                 stop_on_sleep_exceeds=None):  # If None, stop is independent of sleep
        self.retry = retry_predicate
        self.stop = stop_predicate
        self.wait = wait_calculator
        
        if stop_on_sleep_exceeds is not None:
            # Couple them: stop depends on sleep
            self.stop = lambda rs: (stop_predicate(rs) or 
                                    wait_calculator(rs) > stop_on_sleep_exceeds)
        # Else: stop is independent, even if sleep is large
```

If stop is truly independent (doesn't depend on sleep), then you can compute them in any order or in parallel.

But this reveals the new impossibility: **"If you allow stop to be independent of sleep, you must prevent stop conditions that reference sleep. The system loses expressiveness."**

In other words: Generality (stop can reference sleep) conflicts with Independence (stop and sleep are decoupled).

---

## 16. Meta-Law: Conservation Law of the Conservation Law

**Meta-law of Tenacity's retry design**:

The code architecture hides a fundamental trade-off: **"Composability (presenting retry, wait, and stop as independent policies) conceals that these three form a LOGICAL SEQUENCE, not a composition. The sequence exists because of information dependencies, not arbitrary design. The code presents variants as 'flexible compositions' (via copy() and wraps()) when they are actually 'instantiations of a fixed template.' The flexibility is only in the policy payloads (you can swap the retry predicate), not in the structure (the sequence always goes retry → wait → stop)."**

The conservation law that holds at every level is: **"Coupling point shifts but cannot vanish. Original form: policy sequence determines execution order. Inverted form: outcome type determines policy selection. Both require the same information (outcome or exception type), just at different times."**

**The deeper meta-law that persists across all attempts to improve it**:

"**Composability conceals temporal ordering. The fact that the code uses an API pattern (copy(), wraps(), inheritance) makes it APPEAR that policies are independent components that can be mixed and matched. But the ACTUAL independence is shallow: you can change the retry predicate, but you cannot change the fact that stop() is evaluated after wait(). The composability is in the parameters (the predicates themselves), not in the structure (the sequence). The system conserves this illusion across all improvements because every improvement (PolicyResolver, dependency declarations, inversion) still embeds the sequence somewhere—in the resolver's if-statement, in the dependency DAG, or in the inverted call order."**

---

## 17. Concrete Testable Consequence

**If the meta-law holds, you should be able to test this**: 

Create a policy that **violates the assumed sequence** — a policy that wants to make both "should retry?" AND "how long to sleep?" in one atomic decision, without the engine decomposing it into separate calls.

```python
# Attempt: Single unified retry-decision policy
class UnifiedRetryPolicy:
    def decide(self, outcome):
        if isinstance(outcome, ConnectionError):
            return ('retry', 5.0)  # Retry with 5s sleep
        elif isinstance(outcome, TimeoutError):
            return ('retry', 10.0)  # Retry with 10s sleep
        else:
            return ('return', outcome)  # Don't retry, return result
```

**Expected result**: Tenacity **cannot represent this** because it pre-commits to a sequence where retry decisions are separate from sleep decisions. The library requires you to provide three separate objects: a retry predicate, a wait calculator, and a stop predicate.

This is the evidence that composability is illusory: you can't truly compose retry and sleep—they are bound by the sequence.

---

## 18. Summary: The Meta-Law Itself

**The meta-law of Tenacity's retry design is**: 

"**Composability is conserved as illusory across all forms. The code presents a composable API (policies as interchangeable components), but the sequence (retry → wait → stop) is structurally invariant. This invariant cannot be removed without eliminating some policies or collapsing others. Any attempt to 'improve' the design (pre-compute, declare dependencies, invert order) relocates the sequence constraint but cannot eliminate it. The deepest concealment is that the framework suggests policies can be reordered via composition, when in fact policy order is a logical consequence of information dependencies. The 'meta-impossibility' is this: a truly composable retry framework would need to let users specify the call order, but once you allow that, you must prevent invalid orders (where stop is called before wait has computed sleep duration). This requires the framework to have runtime validation, which brings back the implicit coupling. In other words: explicit sequencing (what Tenacity uses) vs. validated composition (checking policy dependencies) both hide temporal ordering. The code hides it via method structure; runtime validation would hide it via dependency checking. Either way, the sequence persists as a hidden constraint."**
