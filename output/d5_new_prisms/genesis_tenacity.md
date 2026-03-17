# Genesis Analysis: Tenacity Retry Library

## Step 1: Name the Trap

**Conservation Law: Runtime Flexibility × Static Intelligibility = constant**

This code purchases its remarkable composability through action chain construction—strategies (`stop`, `wait`, `retry`, `before`, `after`) are independent callables assembled into a dynamic list at runtime. The `iter()` method doesn't execute a known algorithm; it builds and traverses an action graph whose shape depends on outcomes not yet observed.

What is ALWAYS sacrificed: **the ability to answer "what will this code do?" without running it.**

The trap manifests in three places:

1. **`_begin_iter()` conditionally appends to `iter_state.actions`** based on `outcome` state that changes during execution
2. **`_post_retry_check_actions()` and `_post_stop_check_actions()` extend the chain mid-traversal** — the path forward is constructed while walking it
3. **`_iter_state_var` contextvar** means control flow is invisible to debuggers that don't understand context-local state

You cannot draw a flowchart of a Tenacity retry loop. The flowchart IS the execution trace, constructed backwards from outcomes. Maximum flexibility purchased with maximum opacity.

---

## Step 2: Break the Law

**Design a system where Runtime Flexibility AND Static Intelligibility are BOTH maximized.**

The alternative architecture: **State Machine with Declarative Transitions**

Instead of an action chain built during execution, define a state machine where:
- All possible states are enumerated upfront
- Transitions are predicate functions (the current strategies)
- The graph structure is static; only the path taken is dynamic

```python
class RetryMachine:
    """State machine retry system — structure visible, predicates flexible."""
    
    STATES = ('ready', 'attempting', 'evaluating', 'waiting', 'done')
    
    def __init__(self):
        self.transitions = {
            ('ready', 'attempting'): lambda rs: True,  # always start
            ('attempting', 'evaluating'): lambda rs: rs.outcome is not None,
            ('evaluating', 'done'): lambda rs: not self._should_retry(rs),
            ('evaluating', 'waiting'): lambda rs: self._should_retry(rs) and not self._should_stop(rs),
            ('evaluating', 'done'): lambda rs: self._should_stop(rs),
            ('waiting', 'attempting'): lambda rs: True,  # after sleep
        }
        self._strategies = {}  # stop, wait, retry predicates registered here
    
    def register(self, name: str, predicate: Callable[[RetryState], bool]):
        """Strategies are still independent, pluggable callables."""
        self._strategies[name] = predicate
    
    def graph(self) -> str:
        """Static visualization of ALL possible paths."""
        return """
        ready → attempting → evaluating
                           ↓         ↓
                        waiting    done (no retry)
                           ↓
                       attempting (loop)
                           ↓
                       done (stop condition)
        """
    
    def next_state(self, current: str, rs: RetryState) -> str:
        """Deterministic: given state + retry_state, exactly one transition fires."""
        for (from_state, to_state), predicate in self.transitions.items():
            if from_state == current and predicate(rs):
                return to_state
        raise InvalidStateTransition(current)
```

**What this preserves:**
- Strategies are still independent callables (`register('stop', my_stop_fn)`)
- Composition still works (add any predicate)
- Runtime behavior still flexible (predicates can do anything)

**What this adds:**
- `graph()` shows ALL possible paths statically
- State transitions are enumerable without execution
- Debuggers can print "current state: evaluating, possible next: waiting, done"
- Type checkers can verify transition predicates match expected signatures

**Key structural change:** The action chain `list[Callable]` becomes a transition map `dict[tuple[str,str], Callable]`. The list's implicit ordering becomes explicit edge predicates. The hidden control flow becomes a visible state diagram.

---

## Step 3: Name the New Trap

The redesigned system obeys a NEW conservation law:

**State Visibility × Transition Expressiveness = constant**

The state machine makes paths visible, but introduces a new constraint: **every control flow decision must be expressible as a state transition.**

What gets sacrificed:

1. **Mid-transition mutation.** The original can append actions DURING `_post_retry_check_actions` execution. The state machine cannot — transitions are declared upfront.

2. **Ad-hoc control flow.** Want to add a "retry twice, then wait, then retry once more, then alert" pattern? In action-chain Tenacity, you append more actions. In state-machine Tenacity, you need new states (`attempting_1`, `attempting_2`, `alerting`) or a more complex predicate language.

3. **The `copy()` pattern.** Tenacity's `copy()` method creates a fresh retyer with modified strategies MID-EXECUTION. A state machine with static transitions cannot hot-swap its graph without becoming dynamic again (reintroducing the original opacity).

**Which is worse?**

The original trap (opacity) is worse for:
- Debugging production failures
- Onboarding new developers
- Static analysis tooling

The new trap (transition rigidity) is worse for:
- Complex retry choreography (circuit breaker integration, multi-phase backoff)
- Dynamic strategy adjustment based on observed failures

The original trap is **worse for the library's primary audience** (operators debugging why their retry isn't working). The new trap is worse for **edge cases** the library author might imagine but users rarely need.

---

## Step 4: The Design Space Map

**The Hidden Variable: Binding Time**

The space between action-chain Tenacity and state-machine Tenacity is governed by **WHEN the control flow graph is bound:**

| Architecture | Binding Time | Flexibility | Intelligibility |
|--------------|--------------|-------------|-----------------|
| Action chain (current) | Runtime, during traversal | Maximum | Minimum |
| State machine | Class definition | Moderate | Moderate |
| Macro-generated state machine | Compile time (import) | Low | Maximum |

**The axis is: "At what point does the shape of execution become fixed?"**

Tenacity: Never fixed — re-constructed every `iter()` call.
State machine: Fixed at class definition — transitions registered in `__init__`.
Generated: Fixed at import — decorators expand into explicit flow.

**The concrete design decision that moves this code toward the alternative with minimum disruption:**

Replace the action chain list with a **transition registry that accumulates but doesn't execute**:

```python
# In BaseRetrying.__init__:
self._transitions: list[tuple[str, str, Callable]] = []

# New method:
def register_transition(self, from_phase: str, to_phase: str, 
                        condition: Callable[[RetryCallState], bool]):
    self._transitions.append((from_phase, to_phase, condition))

# In iter(), replace action list traversal:
def iter(self, retry_state):
    current_phase = self._phase_for(retry_state)
    for from_phase, to_phase, condition in self._transitions:
        if from_phase == current_phase and condition(retry_state):
            return self._execute_phase(to_phase, retry_state)
```

This change:
- Preserves the current API entirely (decorators still work)
- Adds a `graph()` method that prints the transition registry
- Makes the implicit explicit without requiring a full rewrite
- Allows gradual migration: start with the current transitions as the default registry, then expose for customization

**Minimum disruption, maximum movement:** The action list becomes a transition list. Same callables, same composition, but now enumerable, printable, and debuggable.
