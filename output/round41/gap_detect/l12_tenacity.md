# Architectural Critique: Tenacity's Conservation Law Violations

## The Conservation Law Framework

Tenacity embodies a fundamental conservation law:

**Flexibility × Predictability = Constant**

As composability increases (flexible chaining of stop/wait/retry strategies), predictability decreases proportionally. This is not an implementation flaw but a **structural inevitability** of the action-list pattern.

## The Three Properties and Their Mutual Exclusion

### 1. **Composability** (Achieved)
The `IterState.actions` list enables dynamic strategy chaining:
```python
# Actions accumulate dynamically across execution phases
def _post_retry_check_actions(self, retry_state):
    if not (self.iter_state.is_explicit_retry or self.iter_state.retry_run_result):
        self._add_action_func(lambda rs: rs.outcome.result())
        return
    if self.after is not None:
        self._add_action_func(self.after)
    self._add_action_func(self._run_wait)
    self._add_action_func(self._run_stop)
    self._add_action_func(self._post_stop_check_actions)
```

### 2. **Predictability** (Sacrificed)
You cannot reason about execution without runtime simulation. The action list:
- Mutates during iteration (`self._add_action_func` called within `for action in list(self.iter_state.actions)`)
- Has branching logic that changes based on previous action outcomes
- Makes static analysis nearly impossible

### 3. **Performance** (Compromised)
Three layers of iteration overhead:
```python
# Layer 1: Outer while loop (line 298, 354)
while True:
    do = self.iter(retry_state=retry_state)
    
# Layer 2: Action list iteration (line 195)
for action in list(self.iter_state.actions):
    result = action(retry_state)
    
# Layer 3: Outcome checking (implicit in action return values)
if isinstance(do, DoAttempt):
```

## Recursive Depth: How Unpredictability Recreates Itself

### Level 1: The Action List Pattern
**Problem**: Dynamic action addition during iteration
```python
# In _begin_iter and _post_retry_check_actions:
self._add_action_func(fn)  # Modifies list while iterating
```

**Consequence**: To understand what executes, you must track:
1. When each action was added
2. What conditions triggered the addition
3. How `retry_run_result`/`stop_run_result` mutations affect subsequent additions
4. The execution order of dynamically-added lambdas

### Level 2: ContextVar State Threading
**Problem**: Invisible state flows
```python
@property
def iter_state(self):
    state = _iter_state_var.get()
    if state is None:
        state = IterState()
        _iter_state_var.set(state)
    return state
```

**Consequence**: State origin and mutation path are obscured:
- Which code path set the ContextVar?
- What previous operations mutated `retry_run_result`?
- In async contexts, which task owns this state?

## What the Conservation Law Conceals

### 1. **Complexity is not eliminated—only displaced**
The "flexibility" users experience is the framework **absorbing their complexity**. The 8 concrete defects below are the cost of that absorption.

### 2. **Predictability has multiple dimensions**
The framework optimizes **API predictability** (consistent interface) at the expense of:
- **Static predictability** (reading code reveals behavior)
- **Runtime predictability** (debugging shows clear execution path)

### 3. **Composability creates coupling**
The action pattern promises loose coupling but creates tight coupling through:
- Shared mutable state (`IterState`)
- Implicit execution order dependencies
- Hidden control flow branches

## Harvested Concrete Defects

### HIGH SEVERITY (Structural)

**1. Divergent Execution Paths: `__iter__` vs `__call__`**
```python
# BaseRetrying.__iter__ (line 298)
if isinstance(do, DoAttempt):
    yield AttemptManager(retry_state=retry_state)  # Delegates to user

# Retrying.__call__ (line 354)  
if isinstance(do, DoAttempt):
    try:
        result = fn(*args, **kwargs)  # Executes directly
    except BaseException:
        retry_state.set_exception(sys.exc_info())
```
**Impact**: Different exception handling semantics, different attempt management, different result propagation. Two code paths must be maintained in synchronization.

**3. ContextVar State Leakage in Async**
```python
@property
def iter_state(self):
    state = _iter_state_var.get()  # Can inherit from parent task
    if state is None:
        state = IterState()
        _iter_state_var.set(state)
    return state
```
**Impact**: In async/await, child tasks inherit parent ContextVar state. `IterState` from one retry operation can leak into nested async calls, causing `actions` from one retry to execute in another's context.

**5. AttemptManager Silently Suppresses All Exceptions**
```python
def __exit__(self, exc_type, exc_value, traceback):
    if exc_type is not None and exc_value is not None:
        self.retry_state.set_exception((exc_type, exc_value, traceback))
        return True  # ⚠️ Suppresses ALL exceptions
```
**Impact**: Exceptions that should escape (like `KeyboardInterrupt`, `SystemExit`) are captured and converted to retry attempts. User cannot interrupt execution during retry loop.

### MEDIUM SEVERITY (Structural)

**2. Dynamic Action List Modification During Iteration**
```python
def _post_retry_check_actions(self, retry_state):
    # ...adds more actions to self.iter_state.actions
    self._add_action_func(self._post_stop_check_actions)
```
**Impact**: Modifying the action list while iterating over it creates cognitive load. Debugging requires tracing through multiple `_add_action_func` calls to understand what will execute.

**7. RetryError.reraise() Conditional Logic**
```python
def reraise(self):
    if self.last_attempt.failed:
        raise self.last_attempt.result()  # Raises exception() from Future
    raise self  # Raises RetryError itself
```
**Impact**: Inconsistent exception types raised depending on failure state. Callers cannot predict what exception type to catch.

**8. ThreadLocal Statistics Mixed with Instance State**
```python
@property
def statistics(self):
    if not hasattr(self._local, "statistics"):
        self._local.statistics = {}  # Thread-local but instance-initialized
    if len(self._local.statistics) > 100:
        self._local.statistics.clear()  # Silent data loss
    return self._local.statistics
```
**Impact**: Statistics behavior differs across threads. Silent clearing at 100 entries can lose critical diagnostic data.

### LOW/MEDIUM SEVERITY (Fixable)

**4. Silent Statistics Data Loss**
```python
if len(self._local.statistics) > 100:
    self._local.statistics.clear()  # No warning, no logging
```
**Impact**: Users monitoring retry behavior may miss patterns after 100 attempts.

**6. Duplicated DoAttempt Handling**
```python
# In __iter__: yield AttemptManager(...)
# In __call__: direct fn(*) execution with try/except
```
**Impact**: Code duplication increases maintenance burden and risk of divergence.

## Architectural Synthesis

Tenacity's architecture demonstrates a **conservation law violation**: the pursuit of maximal composability has sacrificed predictability to a degree that cannot be remedied without structural changes.

### The Fundamental Tension

The action-list pattern centralizes decision-making but **recreates unpredictability at multiple depths**:

```
┌─────────────────────────────────────────────────────┐
│ Surface: Flexible API, easy composition             │
├─────────────────────────────────────────────────────┤
│ Depth 1: Dynamic action list → hidden control flow  │
├─────────────────────────────────────────────────────┤
│ Depth 2: ContextVar state → invisible dependencies  │
├─────────────────────────────────────────────────────┤
│ Depth 3: Dual execution paths → divergent semantics │
└─────────────────────────────────────────────────────┘
```

### The Cost of "Flexibility"

Every "convenience" feature compounds the complexity budget:
- **Copy protocol** (`self.copy()`) → 8 concrete defects
- **Action list pattern** → unpredictable execution  
- **ContextVar threading** → state leakage
- **Dual iterator/callable paths** → maintenance nightmare

### Conservation Law Reality

The equation `Flexibility × Predictability = constant` conceals:
1. **Zero-sum game**: More flexibility = less predictability
2. **Complexity displacement**: User complexity becomes framework complexity
3. **Hidden trade-offs**: API simplicity creates implementation complexity

## Recommendation Path

Tenacity requires **architectural reduction**:
1. Choose **one** execution path (iterator OR callable, not both)
2. Eliminate dynamic action addition (declare actions upfront)
3. Remove ContextVar state threading (explicit state passing)
4. Make state mutations visible (observable transitions)

The current architecture trades 8 structural defects for composability—a trade that becomes increasingly expensive as the codebase scales. The conservation law suggests: **you cannot have maximum flexibility and maximum predictability. Choose which to optimize.**
