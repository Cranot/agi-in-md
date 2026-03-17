# Counterfactual Analysis: Tenacity Retry Library

## Step 1: Decision Extraction

### Decision 1: Dynamic Action Chain Construction
**What was chosen:** Instead of a fixed retry loop, the code dynamically builds a list of action functions (`_add_action_func`) that get executed in sequence. The `iter()` method constructs different action chains based on runtime state—first attempt, retry needed, stop conditions—each producing a different execution path.

**What was NOT chosen:** A traditional control-flow structure with explicit `if/elif/else` branches in a `while` loop, where each condition directly executes its logic inline.

**Evidence of deliberate choice:** The three-phase method structure (`_begin_iter` → `_post_retry_check_actions` → `_post_stop_check_actions`) with `_add_action_func` calls at each phase shows this is an intentional state machine pattern, not accidental complexity. The `list(self.iter_state.actions)` copy before iteration proves awareness of mutation during execution.

### Decision 2: ContextVar for Cross-Stack State Access
**What was chosen:** Using `contextvars.ContextVar('iter_state')` to store `IterState` that can be accessed from any function in the call stack without explicit parameter threading.

**What was NOT chosen:** Passing state explicitly through all function signatures, or storing state on `RetryCallState` which already threads through the system.

**Evidence of deliberate choice:** The `iter_state` property on `BaseRetrying` retrieves from ContextVar, while `RetryCallState` is passed explicitly. This dual approach shows intentional scoping: `RetryCallState` for per-call data, `IterState` for per-iteration control flow that nested functions need to modify.

### Decision 3: Generator Protocol with Sentinel Return Types
**What was chosen:** `__iter__` yields `AttemptManager` or `DoSleep` sentinel objects, and the caller (either `Retrying.__call__` or user code) interprets these to decide what to execute. Control flow is surrendered and resumed.

**What was NOT chosen:** A `run()` method that directly executes the function and handles retries internally, returning only the final result.

**Evidence of deliberate choice:** The `DoAttempt` and `DoSleep` classes exist solely as sentinels—they don't carry behavior, only identity. The `isinstance(do, DoAttempt)` checks in `__iter__` and `Retrying.__call__` show this is a communication protocol, not an accident.

---

## Step 2: Alternative Construction

### Alternative 1: Static Control Flow (Opposite of Dynamic Action Chain)

```python
class BaseRetrying(ABC):
    # ... same init ...
    
    def execute_with_retry(self, fn, args, kwargs):
        """Single method with explicit control flow."""
        self.begin()
        retry_state = RetryCallState(self, fn, args, kwargs)
        
        while True:
            # PHASE 1: Before hook
            if self.before:
                self.before(retry_state)
            
            # PHASE 2: Execute attempt
            try:
                result = fn(*args, **kwargs)
                retry_state.set_result(result)
            except BaseException as e:
                retry_state.set_exception(sys.exc_info())
            
            # PHASE 3: Retry decision - direct branch
            if retry_state.outcome.failed and isinstance(retry_state.outcome.exception(), RetrySignal):
                should_retry = True
            else:
                should_retry = self.retry(retry_state)
            
            if not should_retry:
                return retry_state.outcome.result()
            
            # PHASE 4: After hook
            if self.after:
                self.after(retry_state)
            
            # PHASE 5: Wait calculation
            sleep_time = self.wait(retry_state) if self.wait else 0
            retry_state.upcoming_sleep = sleep_time
            
            # PHASE 6: Stop check
            if self.stop(retry_state):
                if self.retry_error_callback:
                    return self.retry_error_callback(retry_state)
                raise self.retry_error_cls(retry_state.outcome)
            
            # PHASE 7: Sleep and prepare
            if self.before_sleep:
                self.before_sleep(retry_state)
            self.sleep(sleep_time)
            retry_state.prepare_for_next_attempt()
```

**What changes:**
- No `IterState`, no action list, no `_add_action_func`
- All hooks and checks are inline function calls
- Single linear method with early returns
- State exists only in `RetryCallState`

### Alternative 2: Explicit State Threading (Opposite of ContextVar)

```python
class BaseRetrying(ABC):
    # No _iter_state_var, no iter_state property
    
    def _run_retry(self, retry_state, iter_state):
        iter_state.retry_run_result = self.retry(retry_state)
    
    def _begin_iter(self, retry_state, iter_state):
        iter_state.reset()
        # ... all methods take iter_state as parameter ...
    
    def iter(self, retry_state, iter_state):
        self._begin_iter(retry_state, iter_state)
        for action in iter_state.actions:
            action(retry_state, iter_state)  # Pass through
    
    def __iter__(self):
        iter_state = IterState()  # Local variable, not ContextVar
        self.begin()
        retry_state = RetryCallState(self, fn=None, args=(), kwargs={})
        while True:
            do = self.iter(retry_state=retry_state, iter_state=iter_state)
            # ...


# User hooks must accept iter_state:
def before_hook(retry_state, iter_state):
    iter_state.is_explicit_retry = True  # Now user must handle it
```

**What changes:**
- Every function signature grows an `iter_state` parameter
- User-provided hooks (`before`, `after`, `before_sleep`) must accept and thread the parameter
- No "magic" cross-stack access—everything explicit
- Cleaner stack traces, more verbose signatures

### Alternative 3: Direct Execution (Opposite of Generator Protocol)

```python
class Retrying(BaseRetrying):
    def run(self, fn, *args, **kwargs):
        """Execute and return result. No yielding, no sentinels."""
        self.begin()
        retry_state = RetryCallState(self, fn, args, kwargs)
        
        while True:
            # Execute attempt directly (no AttemptManager yielded)
            if self.before:
                self.before(retry_state)
            
            try:
                result = fn(*args, **kwargs)
                retry_state.set_result(result)
            except BaseException:
                retry_state.set_exception(sys.exc_info())
            
            # Inline retry logic (no iter() indirection)
            should_retry = self._should_retry(retry_state)
            if not should_retry:
                return retry_state.outcome.result()
            
            # Calculate and perform sleep inline
            sleep_time = self.wait(retry_state) if self.wait else 0
            if self.stop(retry_state):
                raise self.retry_error_cls(retry_state.outcome)
            
            if self.before_sleep:
                self.before_sleep(retry_state)
            self.sleep(sleep_time)
            retry_state.prepare_for_next_attempt()
    
    # No __iter__, no DoAttempt, no DoSleep, no AttemptManager
```

**What changes:**
- No `DoAttempt`, `DoSleep`, `AttemptManager` classes
- No `__iter__` method at all
- `Retrying.__call__` becomes `run()` with direct `while True`
- Async integration becomes impossible without separate implementation
- Testing requires mocking `time.sleep` directly

---

## Step 3: Comparative Analysis

### Pair 1: Dynamic Action Chain vs Static Control Flow

**What Alternative GAINS:**
- Immediate readability: control flow is visible in one place
- Simpler debugging: stack traces show actual execution path
- ~100 fewer lines of code (no IterState, no action list machinery)
- Easier to add new phases (just add code, don't modify action builders)

**What Alternative SACRIFICES:**
- Extensibility: cannot inject new actions between phases without modifying `execute_with_retry`
- The `retry_with()` pattern becomes harder—no way to intercept and modify behavior
- Conditional action ordering becomes messy (current code can skip `_post_retry_check_actions` entirely)

**Bugs that DISAPPEAR in Alternative:**
- **Action list mutation during iteration bug**: Line `for action in list(self.iter_state.actions)` copies the list because actions can append more actions. This complexity vanishes.
- **IterState reset timing bug**: If `reset()` is called at wrong time, stale actions execute. Static flow has no such state.

**Bugs that APPEAR in Alternative:**
- **Copy-paste consistency bugs**: The `Retrying.__call__` and `__iter__` would duplicate logic. Current code shares `iter()` method.
- **Harder to test individual phases**: Cannot mock just the retry decision without mocking the whole method.

**Conservation Law:** `Extensibility × Locality = constant`
- Dynamic chain: high extensibility (inject anywhere), low locality (scattered logic)
- Static flow: low extensibility, high locality (all in one method)

---

### Pair 2: ContextVar vs Explicit Threading

**What Alternative GAINS:**
- Explicit data flow: every function signature documents its dependencies
- No hidden state access: bugs can't arise from "someone modified iter_state from elsewhere"
- Works in environments without contextvars (older Python, some async frameworks)
- Cleaner mental model for new developers

**What Alternative SACRIFICES:**
- User hook simplicity: `before`, `after`, `before_sleep` callbacks must accept extra parameter
- Backward compatibility: all existing user code breaks
- Ergonomics: every internal method has `iter_state` in signature

**Bugs that DISAPPEAR in Alternative:**
- **Context leakage bug**: If `Retrying.__call__` forgets `_iter_state_var.set(IterState())`, it reuses state from previous call in same context. Alternative makes this impossible.
- **Async context confusion**: In async code, ContextVar semantics are subtle. Explicit threading has no such ambiguity.

**Bugs that APPEAR in Alternative:**
- **Parameter drilling bugs**: Easy to forget passing `iter_state` to a deeply nested call, causing `NameError` or stale state.
- **Signature explosion**: Every callback must change signature, breaking existing code.

**Conservation Law:** `Ergonomics × Explicitness = constant`
- ContextVar: high ergonomics (invisible access), low explicitness
- Explicit: low ergonomics, high explicitness (everything visible in signatures)

---

### Pair 3: Generator Protocol vs Direct Execution

**What Alternative GAINS:**
- Simplicity: no sentinel classes, no `isinstance` checks
- Performance: no generator overhead, no yield/resume machinery
- Direct stack traces: exception shows actual line, not generator machinery

**What Alternative SACRIFICES:**
- Async support: `AsyncRetrying` would need entirely separate implementation (cannot `yield` in async function)
- Testability: cannot intercept and control timing without mocking `time.sleep`
- Composability: cannot wrap retry logic in another generator-based system

**Bugs that DISAPPEAR in Alternative:**
- **Sentinel confusion bug**: If someone returns `DoAttempt()` or `DoSleep()` from user code, it's misinterpreted as control signal.
- **Yield without consumption bug**: If caller doesn't iterate fully, state is inconsistent.

**Bugs that APPEAR in Alternative:**
- **Sleep mocking bugs**: Tests must mock `time.sleep` globally, risking test pollution.
- **No early exit protocol**: Cannot pause retry loop for external inspection.

**Conservation Law:** `Composability × Simplicity = constant`
- Generator: high composability (yields control), low simplicity (sentinel protocol)
- Direct: low composability, high simplicity (single execution path)

---

## Step 4: The Unchosen Path

**Maximally-different architecture:** Static control flow + Explicit state threading + Direct execution

```python
class SimpleRetrying:
    """Everything the opposite: no action chains, no ContextVar, no generators."""
    
    def __init__(self, stop=stop_never, wait=wait_none(), retry=retry_if_exception_type(),
                 before=None, after=None, before_sleep=None, sleep=time.sleep):
        self.stop = stop
        self.wait = wait
        self.retry = retry
        self.before = before
        self.after = after
        self.before_sleep = before_sleep
        self.sleep_fn = sleep
    
    def __call__(self, fn, *args, **kwargs):
        attempt = 1
        start_time = time.monotonic()
        idle_for = 0.0
        
        while True:
            retry_state = SimpleState(
                attempt_number=attempt,
                start_time=start_time,
                idle_for=idle_for,
                fn=fn, args=args, kwargs=kwargs
            )
            
            if self.before:
                self.before(retry_state)
            
            try:
                result = fn(*args, **kwargs)
                retry_state.result = result
                retry_state.failed = False
            except BaseException as e:
                retry_state.exception = e
                retry_state.failed = True
            
            if not self.retry(retry_state):
                if retry_state.failed:
                    raise retry_state.exception
                return result
            
            if self.after:
                self.after(retry_state)
            
            sleep_time = self.wait(retry_state)
            idle_for += sleep_time
            
            if self.stop(retry_state):
                raise RetryError(retry_state)
            
            if self.before_sleep:
                self.before_sleep(retry_state)
            
            self.sleep_fn(sleep_time)
            attempt += 1


@dataclass
class SimpleState:
    attempt_number: int
    start_time: float
    idle_for: float
    fn: callable
    args: tuple
    kwargs: dict
    result: Any = None
    exception: BaseException = None
    failed: bool = False
```

**Is it coherent?** YES. This is a fully functional, ~50-line retry library. It would work for 90% of use cases.

**Do the opposite choices conflict?** NO—they're mutually reinforcing:
- Static flow + Direct execution both reduce indirection (coherent)
- Explicit threading pairs naturally with direct execution (no generator boundary to cross)
- The three "simplifications" compose cleanly into one simple implementation

**The hidden coupling revealed:**
The actual Tenacity design has **two** coupled decisions, not three:

1. **Generator Protocol ↔ Dynamic Action Chain** are coupled. Generators *require* a way to communicate what should happen next. The action chain provides that communication mechanism. Without sentinels, you'd need action chains to return values. Without action chains, sentinels have nothing to orchestrate.

2. **ContextVar is the INDEPENDENT decision.** It exists to make the action chain pattern ergonomic—nested functions can modify state without threading. But if you remove action chains (static flow), ContextVar becomes unnecessary. If you keep action chains but use explicit threading, it works but is verbose.

**The true design space is 2D, not 3D:**

| | Action Chain | Static Flow |
|---|---|---|
| **Generator** | Tenacity (actual) | Possible but weird—sentinels with inline handling |
| **Direct** | Unnecessary complexity | SimpleRetrying (opposite) |

| | ContextVar | Explicit |
|---|---|---|
| **With Action Chain** | Tenacity (actual) | Verbose but works |
| **With Static Flow** | Unnecessary | SimpleRetrying (opposite) |

**Conservation law for the whole system:**
`Flexibility × Lines of Code = constant`

Tenacity chose ~350 lines for maximum extensibility (async, sync, hooks, callbacks, custom strategies all supported). The opposite chooses ~50 lines for the 90% use case. Both are correct—Tenacity for library authors, SimpleRetrying for application authors who just need retries.
