[36m3-Way Pipeline: WHERE/WHEN/WHY (domain='code_py')[0m
  [36mCooking 3-way pipeline...[0m
    [32mWHERE: traces current structure[0m (archaeology_where): [2mExecute every step below. Output the complete analysis.

You...[0m
    [32mWHEN: predicts temporal evolution[0m (simulation_when): [2mExecute every step below. Output the complete analysis.

You...[0m
    [32mWHY: proves architectural necessity[0m (structural_why): [2mExecute every step below. Output the complete analysis.

You...[0m
    [32mSYNTHESIS: cross-operation integration[0m (synthesis_3way): [2mExecute every step below. Output the complete analysis.

You...[0m

[1m[34m── WHERE: traces current structure ── real_code_tenacity.py ──[0m
[2mthinking...[0m                                        # Archaeological Excavation: Tenacity Retry Library

## Layer 1: API Surface Layer

### Visible Artifacts
The exposed surface consists of:
- **`@retry` decorator** — primary entry point, can be bare `@retry` or configured `@retry(stop=stop_after_attempt(3))`
- **`Retrying` class** — programmatic interface for non-decorator usage
- **`BaseRetrying.wraps()`** — transforms functions into retry-wrapped versions
- **`RetryError`** — terminal exception carrying `last_attempt` payload
- **Strategy slots**: `stop`, `wait`, `retry`, `before`, `after`, `before_sleep`

### Promises Made
1. **Transparent retry** — decorated function appears unchanged to callers
2. **Configurable failure handling** — stop conditions, wait strategies, retry predicates
3. **Observability hooks** — inspection points at every phase transition
4. **Statistics accumulation** — `wrapped_f.statistics` exposes runtime metrics
5. **Copy semantics** — `retry_with()` allows per-call configuration variants

### Implementation Concealment
The surface hides:
- The **action chain machinery** — no user sees `_add_action_func` or the dynamic construction of execution phases
- **Three-tier state architecture** — `RetryCallState`, `IterState`, and `threading.local` statistics exist beneath
- **Control flow markers** — `DoAttempt`, `DoSleep` are internal sentinel types, never exposed
- **The RetrySignal exception** — a "fake" exception used as control signal, hidden from user exception hierarchies

---

## Layer 2: State Transport Layer

### Visible Artifacts
```python
_iter_state_var = contextvars.ContextVar('iter_state', default=None)

@dataclasses.dataclass(slots=True)
class IterState:
    actions: list
    retry_run_result: bool
    stop_run_result: bool
    is_explicit_retry: bool
```

And in `BaseRetrying`:
```python
self._local = threading.local()  # For statistics
```

### Structural Foundation
This layer rests on:
- **Python 3.7+ `contextvars`** — async-safe context isolation
- **`threading.local()`** — thread-isolated mutable storage
- **`dataclasses` with slots** — memory-efficient mutable containers

### State Flow Tracing

**`IterState` flows through contextvars:**
```python
@property
def iter_state(self):
    state = _iter_state_var.get()
    if state is None:
        state = IterState()
        _iter_state_var.set(state)
    return state
```

**Statistics flows through threading.local:**
```python
@property
def statistics(self):
    if not hasattr(self._local, "statistics"):
        self._local.statistics = {}
    if len(self._local.statistics) > 100:
        self._local.statistics.clear()  # Prevent unbounded growth
    return self._local.statistics
```

### Vestigial Structures: The threading.local() Fossil

`threading.local()` for statistics is a **pre-async design remnant**. When this library was conceived, threading was the dominant concurrency model. The split reveals evolutionary pressure:

| State Container | Technology | Isolation Granularity | Era |
|-----------------|------------|----------------------|-----|
| `IterState` | contextvars | Per-async-task | Post-3.7 |
| `statistics` | threading.local | Per-thread | Pre-async |

**Tension point**: In an async application with multiple coroutines on one thread, `statistics` becomes **shared across concurrent coroutines** while `IterState` remains properly isolated. This creates semantic inconsistency — per-call retry state is isolated, but cumulative metrics leak between concurrent operations.

### The Copy Pattern's State Split
```python
def wrapped_f(*args, **kw):
    copy = self.copy()           # New instance with new threading.local
    wrapped_f.statistics = copy.statistics  # Re-expose the new local
    return copy(f, *args, **kw)
```

Each invocation creates a fresh `Retrying` copy, but statistics are then **reattached to the wrapped function** — a curious dance that suggests the original design didn't anticipate the current usage pattern.

---

## Layer 3: Strategy Composition Layer

### Visible Artifacts
The six strategy slots in `BaseRetrying.__init__`:
```python
stop=stop_never,
wait=wait_none(),
retry=retry_if_exception_type(),
before=before_nothing,
after=after_nothing,
before_sleep=None,
```

### Composition Mechanism
Strategies compose through **dynamic action chain building**:

```python
def _begin_iter(self, retry_state):
    self.iter_state.reset()
    fut = retry_state.outcome
    if fut is None:  # First attempt
        if self.before is not None:
            self._add_action_func(self.before)
        self._add_action_func(lambda rs: DoAttempt())
        return
    # Subsequent attempts
    self.iter_state.is_explicit_retry = fut.failed and isinstance(fut.exception(), RetrySignal)
    if not self.iter_state.is_explicit_retry:
        self._add_action_func(self._run_retry)
    self._add_action_func(self._post_retry_check_actions)
```

Each strategy is **not composed at instantiation** but **woven into a chain at execution time**. The chain structure:
```
_begin_iter
  └── _post_retry_check_actions
        └── _post_stop_check_actions
              └── (next_action + before_sleep + DoSleep)
```

### Hidden Coupling Patterns

**Conditional chain extension:**
```python
def _post_stop_check_actions(self, retry_state):
    if self.iter_state.stop_run_result:
        if self.retry_error_callback:
            self._add_action_func(self.retry_error_callback)
            return  # Chain ends here
        self._add_action_func(exc_check)  # Different termination
        return
    self._add_action_func(next_action)  # Continue chain
```

The presence/absence of `retry_error_callback` changes **control flow topology**, not just behavior — a coupling invisible from the API surface.

### Dead Pattern: The `retry` Strategy's Diminished Role

The `retry` strategy's output is stored but only checked in a negation:
```python
if not (self.iter_state.is_explicit_retry or self.iter_state.retry_run_result):
    self._add_action_func(lambda rs: rs.outcome.result())  # Return immediately
    return
```

When `RetrySignal` is used (explicit retry), the `retry` strategy is **completely bypassed**:
```python
if not self.iter_state.is_explicit_retry:
    self._add_action_func(self._run_retry)  # Only run if not explicit
```

This suggests `RetrySignal` was added later, creating an alternate path that **partially obsoletes** the `retry` strategy's decision-making role.

---

## Layer 4: Control Flow Substrate

### Visible Artifacts
```python
class RetrySignal(Exception):
    """Control signal for explicit retry, not a real exception."""
    pass

class DoAttempt:
    pass

class DoSleep(float):
    pass
```

### Foundation
These rest on:
- **Exception subclassing** — `RetrySignal` hijacks Python's exception machinery for control flow
- **Float subclassing** — `DoSleep` carries sleep duration while signaling control intent
- **Empty class** — `DoAttempt` is pure type marker

### Control Flow Interpretation

The `iter()` method returns one of three types, interpreted by callers:

```python
def __iter__(self):
    while True:
        do = self.iter(retry_state=retry_state)
        if isinstance(do, DoAttempt):
            yield AttemptManager(retry_state=retry_state)
        elif isinstance(do, DoSleep):
            retry_state.prepare_for_next_attempt()
            self.sleep(do)
        else:
            break  # Any other value: terminate
```

And in `Retrying.__call__`:
```python
if isinstance(do, DoAttempt):
    try:
        result = fn(*args, **kwargs)
    except BaseException:
        retry_state.set_exception(sys.exc_info())
    else:
        retry_state.set_result(result)
```

### Fault Line: Exception Handling Meets Return Paths

The `AttemptManager` context manager:
```python
def __exit__(self, exc_type, exc_value, traceback):
    if exc_type is not None and exc_value is not None:
        self.retry_state.set_exception((exc_type, exc_value, traceback))
        return True  # Suppress ALL exceptions
    if not self._result_set:
        self.retry_state.set_result(None)
    return None
```

**Critical**: `return True` suppresses **all exceptions**, including `RetrySignal`. This creates a semantic split:
- In `__iter__` mode: exceptions flow through `AttemptManager` and are suppressed
- In `__call__` mode: exceptions are caught by `except BaseException` and recorded

Both paths record to `retry_state`, but through **different mechanisms** with subtly different exception visibility.

---

## Fault Lines: Where Eras Collide

### Fault Line 1: IterState Initialization Divergence

```python
# In Retrying.__call__:
def __call__(self, fn, *args, **kwargs):
    _iter_state_var.set(IterState())  # EXPLICIT initialization

# In BaseRetrying.__iter__:
def __iter__(self):
    self.begin()
    # No explicit IterState initialization!
    # Relies on lazy creation in iter_state property
```

The `__call__` path explicitly resets `IterState`, while `__iter__` relies on the lazy property getter. If an outer context had set `_iter_state_var`, `__iter__` would inherit stale state — a **latent bug vector** for nested retry contexts.

### Fault Line 2: Statistics Lifecycle vs. IterState Lifecycle

```python
def begin(self):
    self.statistics.clear()  # Reset per-retry-session
    self.statistics["start_time"] = time.monotonic()
    # ...
```

But `statistics` lives in `threading.local`, while `IterState` lives in `contextvars`. In async code:
- Starting a new retry clears statistics (affecting concurrent coroutines on same thread)
- But IterState remains isolated per-task

**Observable symptom**: Concurrent async retries would have isolated per-attempt state but **interleaved statistics**.

### Fault Line 3: The Copy Semantics Scar

```python
def wraps(self, f):
    @functools.wraps(f, ...)
    def wrapped_f(*args, **kw):
        copy = self.copy()
        wrapped_f.statistics = copy.statistics  # Stitching
        return copy(f, *args, **kw)
    
    wrapped_f.statistics = {}  # Initialize
    return wrapped_f
```

The pattern creates a **fresh Retrying instance per call**, then **reattaches its statistics back** to the wrapped function. This suggests:
1. Original design assumed single-use `Retrying` instances
2. Reuse via decorator required copy mechanism
3. Statistics reattachment was retrofitted to preserve observability

The `wrapped_f.statistics = {}` initialization followed by `wrapped_f.statistics = copy.statistics` reassignment is a **scar of evolutionary pressure** — the original design didn't anticipate decorated function reuse patterns.

---

## Conservation Law

**Conservation Law: Hook Composability × Execution Traceability ≈ Constant**

### Property A: Hook Composability
Count of independently configurable intervention points:
```python
# From BaseRetrying.__init__:
stop, wait, retry, before, after, before_sleep, retry_error_callback
```
**A = 7** hook points

### Property B: Execution Traceability
Inverse of the depth of dynamic action chain construction:
```
_begin_iter → _post_retry_check_actions → _post_stop_check_actions → (exc_check | next_action)
```
Depth = 3-4 levels of conditional chain extension

**B = 1/4** (ability to statically trace execution path)

### Conservation Expression
**A × B ≈ 7 × 0.25 ≈ 1.75**

### Interpretation
The library has chosen **high hook composability** (many intervention points) at the cost of **low execution traceability** (control flow is determined dynamically at runtime through action chain construction). 

One cannot increase A without decreasing B:
- Adding more hooks requires more conditional action chain branches
- Making execution statically traceable would require fixing the action chain at construction time, eliminating conditional composition

This is visible in the code where every hook introduces a conditional `_add_action_func`:
```python
if self.after is not None:
    self._add_action_func(self.after)
```

Each optional hook creates a **runtime-determined control flow branch**, reducing static predictability in direct proportion to the flexibility gained.

  [2mSaved to .deep/findings/real_code_tenacity.md[0m

[1m[34m── WHEN: predicts temporal evolution ── real_code_tenacity.py ──[0m
[2mthinking...[0m                                        # Tenacity Temporal Evolution Simulation

## CYCLE 1 — INITIAL DEPLOYMENT

### What Works Immediately

The decorator pattern delivers instant gratification:

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def call_external_service():
    ...
```

Teams celebrate. The `Retrying.__call__` synchronous loop executes predictably. The `RetryCallState` tracks attempts cleanly. The action chain pattern (`_begin_iter` → `_post_retry_check_actions` → `_post_stop_check_actions`) flows logically.

### Common Configuration Mistakes

**Mistake 1: The Infinite Loop**
```python
@retry()  # stop=stop_never by default
def call_service():
    ...
```
Teams discover `stop_never` is the default only after a service outage causes threads to hang indefinitely. The `while True` in `__call__` never exits.

**Mistake 2: The Silent Swallower**
```python
@retry(retry=retry_if_exception_type())  # catches ALL exceptions
def important_function():
    raise CriticalBusinessError()  # gets retried forever
```
The empty `retry_if_exception_type()` catches everything. Nobody reads the default parameter.

**Mistake 3: Statistics Confusion**
```python
@retry(stop=stop_after_attempt(5))
def tracked_call():
    ...
# Later: tracked_call.statistics["attempt_number"] 
# Returns wrong value because statistics is on wrapped_f, not the copy
```
The `wrapped_f.statistics = copy.statistics` assignment in `wraps()` creates confusion about which statistics object is authoritative.

### Edge Cases Emerging After Weeks

**The ContextVar Bleed**: `_iter_state_var` is a module-level `ContextVar`. In thread pool executors where contexts are copied, stale `IterState` objects persist across calls. The `reset()` method exists but isn't always called at the right time.

**The Statistics Vanishing**: Line 117-119:
```python
if len(self._local.statistics) > 100:
    self._local.statistics.clear()
```
After 100 retry cycles, statistics silently disappear. Monitoring dashboards show mysterious gaps. Nobody remembers why 100 was chosen.

### The First Retry Storm

A downstream database starts returning transient errors. Ten services, all using `@retry(wait=wait_exponential(min=1, max=60), stop=stop_after_attempt(10))`, begin retrying simultaneously.

**What breaks**:
- No jitter in exponential backoff → all services retry at the same seconds
- The `sleep=time.sleep` default blocks threads
- No circuit breaker → retries continue even when downstream is clearly down
- Each service maintains independent statistics with no visibility into aggregate retry pressure

The database, already struggling, receives synchronized retry bursts at t=1s, t=2s, t=4s, t=8s... The `wait_exponential` coordination amplifies the problem rather than solving it.

**Knowledge captured**: "Add jitter to wait strategies." This becomes a post-hoc justification rather than upfront design.

---

## CYCLE 2 — CONFIGURATION DRIFT

### Calcified Doctrine

Six months in, a "standard retry configuration" emerges in the codebase:

```python
# sacred_config.py - DO NOT MODIFY
RETRY_CONFIG = {
    "stop": stop_after_attempt(3),
    "wait": wait_exponential(multiplier=1, min=4, max=10),
    "retry": retry_if_exception_type(
        ConnectionError,
        TimeoutError,
        HTTPStatusError  # someone added this later
    ),
    "reraise": True
}
```

**Origin story lost**: Why `min=4`? Why `max=10`? Why these three exception types? The original author left. The values are now sacred numbers.

### Cargo-Culted Patterns

**Pattern 1: The Decorator Stack**
```python
@retry(stop=stop_after_attempt(3))
@retry(stop=stop_after_attempt(5))  # This one is ignored!
def double_decorated():
    ...
```
Teams stack decorators thinking they combine. Only the outer one executes. The inner `wrapped_f` is created but never called through its retry logic.

**Pattern 2: The Copy Confusion**
```python
base_retry = Retrying(stop=stop_after_attempt(3))
service_retry = base_retry.copy(wait=wait_fixed(2))
# Teams assume this creates independent configs
# But copy() shares nothing - it's a fresh object
```
The `copy()` method's behavior becomes doctrine: "always use copy() for variations" without understanding it creates completely independent retry objects.

### Lost Knowledge: The WHY

| Configuration | Original Reason | Current Understanding |
|---------------|-----------------|----------------------|
| `stop_after_attempt(3)` | Downstream SLA of 30s with 10s timeouts | "3 is a good number" |
| `wait_exponential(min=4, max=10)` | Database recovery time measurement | "Exponential is always better" |
| `retry_if_exception_type(ConnectionError)` | Specific socket error in prod | "Retry connection errors" |
| `reraise=True` | Wanted original traceback in logs | "Always use reraise" |

### Unchecked Wrong Assumptions

**Assumption**: "Exponential backoff prevents retry storms"
**Reality**: Without jitter, synchronized clients create coordinated retry bursts. The `wait_exponential` implementation has no randomness.

**Assumption**: "stop_after_attempt(5) means quick failure"
**Reality**: With `wait_exponential(max=60)`, 5 attempts can take 1+2+4+8+16=31 seconds minimum, potentially 60+60+60+60+60=300 seconds.

**Assumption**: "Statistics show retry health"
**Reality**: `threading.local()` means each thread has independent statistics. Aggregated monitoring shows noise.

---

## CYCLE 3 — ERROR EVOLUTION

### New Exception Types Emerge

The downstream service switches from `requests` to `httpx`. Exception hierarchy changes:

| Old | New |
|-----|-----|
| `requests.ConnectionError` | `httpx.ConnectError` |
| `requests.Timeout` | `httpx.TimeoutException` |
| `requests.HTTPError` | `httpx.HTTPStatusError` |

**What breaks**:
```python
@retry(retry=retry_if_exception_type(ConnectionError, TimeoutError))
def call_service():
    # Now raises httpx.ConnectError, not in retry list
    # Fails immediately instead of retrying
```

The retry conditions calcified around specific exception types. The `retry_if_exception_type` checks use `isinstance()`, which is exact.

### Exception Wrapping Cascades

A new middleware layer wraps all exceptions:

```python
class ServiceMiddleware:
    def call(self, fn):
        try:
            return fn()
        except Exception as e:
            raise ServiceError(f"Middleware caught: {e}") from e
```

Now `retry_if_exception_type(ConnectionError)` never matches because the original exception is wrapped in `ServiceError`. The `__cause__` chain exists but tenacity doesn't traverse it.

### Brittle vs. Robust Conditions

**Brittle** (breaks on changes):
```python
retry=retry_if_exception_type(
    requests.exceptions.ConnectionError  # exact type match
)
```

**Robust** (survives changes):
```python
retry=retry_if_exception(
    lambda e: "connection" in str(e).lower()  # string matching
)
```

But robust conditions have their own failure mode: false positives on unrelated errors with "connection" in the message.

### Lost Error Semantics

**Original design intent**: The `RetrySignal` exception class was meant for explicit retry control:
```python
raise RetrySignal()  # force a retry regardless of retry condition
```

**Current understanding**: Teams treat all exceptions the same. The `isinstance(fut.exception(), RetrySignal)` check in `_begin_iter` is forgotten. `RetrySignal` is occasionally caught by `retry_if_exception_type(Exception)` and treated as a real error.

**The wrapping problem**:
```python
try:
    call_service()
except RetrySignal:
    raise  # should propagate for retry
except Exception as e:
    log_error(e)
    raise CustomError() from e  # wraps RetrySignal accidentally
```

The `RetrySignal` control flow breaks when wrapped. Line 139:
```python
self.iter_state.is_explicit_retry = fut.failed and isinstance(fut.exception(), RetrySignal)
```
This check fails if `RetrySignal` is wrapped.

---

## CYCLE 4 — ASYNC MIGRATION

### The Async Gradual Migration

The codebase begins adopting `async/await`. Tenacity's `Retrying` class has a synchronous `__call__`:

```python
def __call__(self, fn, *args, **kwargs):
    # ...
    while True:
        do = self.iter(retry_state=retry_state)
        if isinstance(do, DoAttempt):
            try:
                result = fn(*args, **kwargs)  # SYNCHRONOUS call
```

**What teams try**:
```python
@retry(stop=stop_after_attempt(3))
async def async_call():
    await some_async_operation()
```

**What happens**: The decorator wraps the coroutine function, not the coroutine execution. When `retry` calls `fn(*args, **kwargs)`, it gets a coroutine object (not awaited), treats it as a successful result, and returns immediately. No retries ever happen.

### threading.local() vs contextvars Divergence

The code maintains both:
- `self._local = threading.local()` for statistics (line 101)
- `_iter_state_var = contextvars.ContextVar(...)` for iteration state (line 14)

**In async context**:
- `threading.local()` is shared across all coroutines in the same thread
- `contextvars.ContextVar` is properly isolated per async task

**Divergence symptom**:
```python
@retry()
async def concurrent_calls():
    # Two coroutines in same event loop thread
    # Their statistics BLEED TOGETHER via threading.local()
    # But their iter_state is isolated via contextvars
    ...
```

Statistics become unreliable in async code. The `self._local.statistics` dictionary shows merged data from concurrent coroutines.

### The Sleep Blocking Problem

Line 99: `sleep=time.sleep` is the default.

In async code:
```python
@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=1))
async def blocking_retry():
    # time.sleep() BLOCKS THE EVENT LOOP
    # All other async operations halt during wait
```

Teams discover they need:
```python
@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=1), sleep=asyncio.sleep)
```

But passing `asyncio.sleep` to synchronous `Retrying.__call__` doesn't work—the sleep call isn't awaited.

### Knowledge That Fails to Transfer

| Sync Knowledge | Async Reality |
|----------------|---------------|
| Decorator just works | Decorator needs `AsyncRetrying` variant |
| `time.sleep` is fine | Must use `asyncio.sleep` |
| Statistics per thread | Statistics corrupted per event loop |
| Context is automatic | Must understand `contextvars` isolation |

The action chain pattern (`_add_action_func`) still works, but the `__call__` execution model is fundamentally incompatible with `await`.

---

## CYCLE 5 — MAINTENANCE ATROPHY

### Sacred Code: Do Not Touch

**Zone 1: The Action Chain Builder**

Lines 135-176 become untouchable:
```python
def _begin_iter(self, retry_state):
    self.iter_state.reset()
    # ... 40 lines of action chain construction
    
def _post_retry_check_actions(self, retry_state):
    # ... conditional action appending
    
def _post_stop_check_actions(self, retry_state):
    # ... more conditional action appending
```

**Why it's sacred**: Nobody fully understands the state machine. The `DoAttempt` / `DoSleep` return pattern (lines 48-55) is viewed as magic. Comments from original author have been lost. Any modification causes subtle bugs in production.

**Zone 2: The IterState Reset Logic**

```python
def reset(self):
    self.actions = []
    self.retry_run_result = False
    self.stop_run_result = False
    self.is_explicit_retry = False
```

The order matters but nobody knows why. Legend says removing the reset caused infinite loops in 2023.

**Zone 3: The Statistics Clearing**

```python
if len(self._local.statistics) > 100:
    self._local.statistics.clear()
```

This is now considered a "feature" for "memory management." Nobody questions why 100, or whether clearing is better than keeping the most recent entries.

### Opaque Configuration Options

| Option | Documented Purpose | Current Understanding |
|--------|-------------------|----------------------|
| `retry_error_cls` | Custom retry error class | "Don't touch this" |
| `before_sleep` | Callback before sleep | "Use for logging" (but when exactly?) |
| `after` | Callback after attempt | "Same as before_sleep?" |
| `before` | Callback before attempt | "Why three callbacks?" |
| `name` | Name for the retry object | "No visible effect" |

The interaction between `after`, `before_sleep`, and `before` is unclear. Teams use `before_sleep` for logging because "that's what the example showed."

### Calcified Doctrine from Implementation Accidents

**Doctrine 1**: "Always set `reraise=True`"
**Origin**: A bug in early versions where `RetryError` didn't preserve traceback. Fixed years ago, but the doctrine remains.

**Doctrine 2**: "Never modify wrapped functions after decoration"
**Origin**: The `wrapped_f.retry` and `wrapped_f.retry_with` attributes (lines 125-127) would be lost. Technically true, but rarely relevant.

**Doctrine 3**: "Statistics are unreliable"
**Origin**: The threading.local() behavior in async code and the > 100 clearing. Teams built external monitoring instead of fixing root cause.

**Doctrine 4**: "Copy the decorator config for each use case"
**Origin**: The `copy()` method exists, so it must be used. Creates massive configuration duplication across codebase.

### Lost Knowledge Inventory

| Knowledge | Status | Impact |
|-----------|--------|--------|
| Why `IterState` uses `contextvars` | Partially lost | Async behavior mysterious |
| Why action chain pattern was chosen | Completely lost | Fear of modification |
| Original exception hierarchy design | Lost | Retry conditions brittle |
| Purpose of `DoAttempt`/`DoSleep` types | Folklore | "It's magic" |
| Why statistics clear at 100 | Urban legend | "Memory leak prevention" |
| `RetrySignal` control flow intent | Forgotten | Treated as regular exception |

---

## CONSERVATION LAW: Retry Flexibility × Runtime Debuggability = k

As the tenacity library ages, I observe a conservation relationship:

**A = Configuration Surface Area** (number of distinct retry behaviors achievable through parameter combinations)

**B = Runtime Debuggability** (ability to determine why a specific retry decision was made from production logs/traces)

**A × B = k** (constant)

### Concrete Evidence

**Initial State** (Cycle 1):
- A is moderate (stop, wait, retry conditions)
- B is moderate (statistics, attempt tracking)
- Teams can reason about behavior

**Mid-Life** (Cycle 3):
- A has grown (exception hierarchies, callbacks, error handlers)
- B has decreased (exception wrapping hides reasons, statistics unreliable)
- Product is constant: more flexibility, less visibility

**Atrophy** (Cycle 5):
- A is maximal (all options, all combinations, cargo-culted configs)
- B is minimal (sacred code, opaque decisions, statistics mistrusted)
- Teams cannot explain why specific retry occurred

### The Mechanism

Every new configuration option (`before_sleep_log`, `retry_error_callback`, custom `retry_error_cls`) increases flexibility but adds a branch point in the action chain. Each branch point is a place where:
1. The execution path depends on runtime state
2. That state (`iter_state.retry_run_result`, `iter_state.stop_run_result`) is ephemeral
3. No trace remains after the retry completes

The `statistics` dictionary was meant to preserve information, but:
- It uses `threading.local()` (wrong for async)
- It clears at 100 entries (arbitrary limit)
- It doesn't capture decision reasons, only counts

### Mathematical Expression

```
Configuration_Options × Decision_Visibility = Constant

Where:
- Configuration_Options = |stop strategies| × |wait strategies| × |retry conditions| × |callbacks|
- Decision_Visibility = P(being able to answer "why did this retry?" from production data)

As Options → ∞, Visibility → 0
```

The library's action chain architecture (`_add_action_func`) makes this inevitable: each conditional action append is a flexibility point that doesn't log its reasoning. The `iter()` method executes actions but returns only `DoAttempt`, `DoSleep`, or a final result—no audit trail.

**Terminal state**: Maximum flexibility, zero debuggability. Teams surround tenacity with external logging, external monitoring, external circuit breakers. The library becomes a black box that "handles retries" but whose behavior can neither be predicted nor explained.

  [2mSaved to .deep/findings/real_code_tenacity.md[0m

[1m[34m── WHY: proves architectural necessity ── real_code_tenacity.py ──[0m
[2mthinking...[0m                                        # Structural Analysis: Tenacity's Impossibility Triangle

## The Three Properties

I identify these three properties that **cannot coexist** in tenacity:

1. **Zero overhead for successful attempts** — First-attempt success pays no allocation/cleanup cost
2. **Transparent exception semantics** — Exceptions flow naturally with correct chaining and typing
3. **Minimal state coupling** — Retry logic doesn't require shared mutable state across execution phases

## Proof of Impossibility

### The Structural Conflict

Examine `Retrying.__call__`:

```python
def __call__(self, fn, *args, **kwargs):
    _iter_state_var.set(IterState())           # ALLOCATION: always
    self.begin()                                # ALLOCATION: statistics dict
    retry_state = RetryCallState(...)          # ALLOCATION: full state object
    while True:
        do = self.iter(retry_state=retry_state)  # BUILDS: action list
        if isinstance(do, DoAttempt):
            try:
                result = fn(*args, **kwargs)
            except BaseException:
                retry_state.set_exception(sys.exc_info())  # BOXING: Future
            else:
                retry_state.set_result(result)              # BOXING: Future
```

**Trace the forced choice:**

To achieve **transparent exception semantics**, the code must:
- Capture exception info via `sys.exc_info()` (line preserves traceback)
- Wrap in `Future` object for uniform handling
- Enable `raise retry_exc from fut.exception()` for proper chaining

But this `Future` wrapping in `set_result`/`set_exception`:

```python
def set_result(self, val):
    ts = time.monotonic()
    fut = Future(self.attempt_number)  # ALLOCATION even on success
    fut.set_result(val)
    self.outcome, self.outcome_timestamp = fut, ts
```

**Every successful call allocates a `Future`**. This violates zero-overhead.

Could we avoid this? Only by checking success/failure BEFORE allocating state. But:

```python
def iter(self, retry_state):
    self._begin_iter(retry_state)
    for action in list(self.iter_state.actions):  # Actions read shared state
        result = action(retry_state)
    return result
```

The action chain (`self.iter_state.actions`) is built dynamically based on `outcome`:

```python
def _begin_iter(self, retry_state):
    self.iter_state.reset()
    fut = retry_state.outcome
    if fut is None:  # First attempt
        # ...
    else:  # Subsequent attempts - reads fut.failed
        self.iter_state.is_explicit_retry = fut.failed and isinstance(fut.exception(), RetrySignal)
```

**The coupling is mandatory**: actions depend on outcome, outcome requires Future, Future requires allocation.

### Which Property Was Sacrificed

**Zero overhead for successful attempts** was sacrificed.

The code explicitly chooses:
- **Transparent exceptions** ✓ (Future wraps all outcomes uniformly, exception chaining works)
- **Minimal state coupling** (via IterState sharing) ✓ (actions can read/write shared state)

**Evidence of sacrifice location:**

```python
# In wraps() - overhead even when retry is disabled
def wrapped_f(*args, **kw):
    if not self.enabled:
        return f(*args, **kw)  # Fast path exists ONLY for disabled
    copy = self.copy()          # But enabled path always copies
    wrapped_f.statistics = copy.statistics
    return copy(f, *args, **kw)
```

The fast path exists only when `enabled=False`. When retry is **enabled but not needed** (first-attempt success), full machinery runs.

---

## IMPROVEMENT 1: Speculative Fast Path

### Proposed Change

Add a pre-flight check before building retry machinery:

```python
class Retrying(BaseRetrying):
    def __call__(self, fn, *args, **kwargs):
        # SPECULATIVE FAST PATH
        if self._can_speculate():
            try:
                result = fn(*args, **kwargs)
                return result  # Success? No allocation. Zero overhead.
            except BaseException as e:
                # Check if this exception would trigger retry
                temp_state = _MockRetryState(e)
                if not self.retry(temp_state):
                    raise  # No retry? Reraise directly. No Future allocated.
                # Fall through to full machinery
        
        # SLOW PATH (existing code)
        _iter_state_var.set(IterState())
        self.begin()
        retry_state = RetryCallState(self, fn, args, kwargs)
        # ... rest unchanged
```

### How This Recreates the Problem Deeper

**New impossibility emerges: Code path bifurcation.**

The speculative path and slow path **must behave identically** for exception semantics to remain transparent. But:

```python
# In speculative path:
except BaseException as e:
    raise  # Native re-raise - preserves traceback perfectly

# In slow path:
def exc_check(rs):
    retry_exc = self.retry_error_cls(fut)
    if self.reraise:
        retry_exc.reraise()  # Goes through RetryError.reraise()
    raise retry_exc from fut.exception()
```

**The conservation law violated:**

```
Execution Uniformity × Performance = Constant
```

By optimizing the fast path, we've created **two different exception handling paths**:
1. Speculative: native `raise`, no `RetryError` wrapper
2. Slow: `RetryError` wrapper with explicit chaining

This means:
- Some `RetryError` exceptions now never get created (speculative success)
- Callbacks/hooks (`before`, `after`) don't fire on speculative path
- Statistics aren't updated on speculative path

**The complexity migrated** from "allocation overhead" to "semantic divergence between paths."

**New fault line:** What if user code checks `isinstance(e, RetryError)`? Now behavior depends on whether speculation succeeded — a hidden variable.

---

## IMPROVEMENT 2: Eliminate ContextVar State Coupling

### Proposed Change

Thread state explicitly instead of via `contextvars`:

```python
class BaseRetrying(ABC):
    def iter(self, retry_state, iter_state):  # iter_state now explicit
        self._begin_iter(retry_state, iter_state)
        result = None
        for action in list(iter_state.actions):
            result = action(retry_state, iter_state)  # Passed through
        return result

    def _add_action_func(self, fn, iter_state):  # iter_state explicit
        iter_state.actions.append(fn)

class Retrying(BaseRetrying):
    def __call__(self, fn, *args, **kwargs):
        iter_state = IterState()  # Local, not ContextVar
        self.begin()
        retry_state = RetryCallState(self, fn, args, kwargs)
        while True:
            do = self.iter(retry_state, iter_state)  # Explicit threading
            # ...
```

### How This Recreates the Problem Deeper

**New impossibility emerges: Async boundary erosion.**

The explicit parameter threading works for synchronous code. But tenacity also supports async (not shown in excerpt, but exists in full library):

```python
# Async version would need:
async def __call__(self, fn, *args, **kwargs):
    iter_state = IterState()
    # ...
    await self.async_iter(retry_state, iter_state)
```

At every `await` point, `iter_state` must be:
1. Captured in the coroutine frame
2. Restored when execution resumes
3. Accessible to any nested calls

**The problem deepens with callbacks:**

```python
# User registers a callback that needs to trigger retry
@retry(after=some_callback)
def my_function():
    some_callback.needs_to_call_retry()  # How does it access iter_state?
```

With ContextVar, `some_callback` could do:
```python
_iter_state_var.get().is_explicit_retry = True  # Access via global-ish handle
```

With explicit threading, callback needs `iter_state` passed somehow. Options:

1. **Add iter_state to every callback signature** — breaks existing user code
2. **Bind iter_state in closure** — but callback is registered at decoration time, not call time
3. **Use a different hidden mechanism** — we've moved the coupling, not eliminated it

**Conservation law:**

```
Implicit Context Reachability × Explicit Interface Simplicity = Constant
```

We traded "hidden global-ish state" for "parameter explosion across all interfaces."

**Where complexity migrated:** Function signatures. Every hook, callback, and action function now needs `(retry_state, iter_state)` parameters. The `@retry` decorator's API surface area increases.

**New constraint:** Async coroutines can't use explicit state threading without either:
- Making state part of every async context, or
- Reintroducing ContextVar (which async handles correctly), or
- Forcing users to manually pass state through their own call chains

---

## Diagnostic Analysis of the Conservation Law

### What the Law Conceals

The law `Execution Uniformity × Performance = Constant` assumes:

1. **"Uniformity" is binary** — paths are either identical or different. Reality: paths can be semantically equivalent but implementationally distinct.

2. **"Performance" is scalar** — a single number. Reality: performance has dimensions (allocation count, instruction count, branch predictability, cache behavior).

3. **The tradeoff is zero-sum** — gain one, lose the other. Reality: architectural changes can shift both (e.g., JIT compilation improves uniformity AND performance over time).

4. **The system is closed** — no external factors. Reality: Python's interpreter, GC, and optimization layer affect both sides.

### Apply the Law to the Law

The conservation law itself relies on:

**Simplification 1: Treating "complexity" as conserved**
But complexity can be *hidden* (moved to dependencies, runtime, or mental model of users) not just *conserved*.

**Simplification 2: Assuming fixed problem scope**
But the "retry problem" isn't fixed — different users need different subsets of functionality.

**Simplification 3: Ignoring meta-level interventions**
A sufficiently smart compiler/runtime could optimize away the apparent tradeoff.

**Where the meta-structure breaks down:**

The law assumes we're trading A for B. But in tenacity, we're actually trading:
- A1 (allocation overhead) for A2 (code duplication)
- B1 (exception transparency) for B2 (path equivalence)
- C1 (implicit state) for C2 (explicit parameters)

These are **different currencies**. The law treats them as commensurable, but they're not.

---

## The Meta-Law

**META-LAW: Information Locality × Access Dispatch = Constant Cognitive Surface**

Where:
- **Information Locality**: How far (in code distance) information travels from definition to use
- **Access Dispatch**: How many code paths must be examined to understand information flow
- **Cognitive Surface**: Total mental effort to trace a single execution path

**Formal expression:**

```
(distance from state definition to state use) × (number of paths touching state) = constant cognitive load
```

**Implications:**

1. **ContextVar approach**: State defined once, accessed everywhere → high locality convenience, but dispatch through hidden channels → cognitive surface is "where did this come from?"

2. **Explicit threading**: State passed at every call → low locality (verbose), but dispatch is visible → cognitive surface is "why does every function need this?"

3. **Fast-path speculation**: Two paths with different state models → dispatch doubles, locality varies → cognitive surface is "which path am I on and why?"

**What this meta-law reveals:**

The fundamental constraint isn't about performance or correctness. It's about **traceability**. Every architecture makes some aspect of the system easy to trace and some aspect hard.

Tenacity chose:
- Easy: "What will happen on retry?" (strategies are composable objects)
- Hard: "What exactly happened in this successful call?" (it went through Future, IterState, action list, but you don't care... until you do)

**The meta-meta-insight:**

The impossibility triangle isn't really about overhead, exceptions, and coupling. It's about **which questions the architecture makes easy to answer**. Every optimization changes the set of easy questions — and the set of hard questions.

The true invariant:

```
(Easy questions) ∪ (Hard questions) = All possible questions about execution
```

Architecture cannot reduce the size of "all questions." It can only move the boundary.

  [2mSaved to .deep/findings/real_code_tenacity.md[0m

[1m[34m── SYNTHESIS: cross-operation integration ── real_code_tenacity.py ──[0m
[2mthinking...[0m                                        # SYNTHESIS: Three Orthogonal Analyses of Tenacity

## 1. STRUCTURAL CERTAINTIES — Findings in ALL THREE Analyses

These represent the deepest truths about tenacity: structurally necessary, temporally persistent, and architecturally fundamental.

### 1.1 Mandatory State Allocation on Every Attempt

**Archaeology** documents the machinery: `IterState`, `RetryCallState`, `Future` objects allocated regardless of outcome. The `set_result()` method creates a `Future` even for successful calls.

**Simulation** traces the consequences: Cycle 1 shows the overhead, Cycle 4 shows how this allocation model collides with async execution where `time.sleep` blocks the event loop.

**Structural** proves this is not fixable: The impossibility triangle shows "zero overhead for successful attempts" was explicitly sacrificed. The action chain depends on `outcome`, outcome requires `Future`, `Future` requires allocation. This dependency chain is architectural, not incidental.

**Convergence**: The allocation is not a performance bug — it is the structural cost of uniform exception handling. The `Future` wrapper enables `raise retry_exc from fut.exception()` chaining. You cannot remove allocation without removing exception transparency.

---

### 1.2 The Flexibility-Traceability Conservation

**Archaeology** derives: Hook Composability × Execution Traceability ≈ 1.75 (7 hooks × 1/4 static traceability depth)

**Simulation** derives: Retry Flexibility × Runtime Debuggability = k (configuration options × ability to answer "why did this retry?")

**Structural** derives: Information Locality × Access Dispatch = Constant Cognitive Surface

**Convergence**: These are the same law in three vocabularies. All three analyses independently discovered that every intervention point (`before`, `after`, `before_sleep`, `retry_error_callback`) creates a branch in execution that does not log its reasoning. The `iter()` method returns `DoAttempt`, `DoSleep`, or a result — no audit trail.

**Deepest truth**: Tenacity's action chain architecture (`_add_action_func`) makes this conservation inevitable. Each conditional action append is a flexibility point that doesn't preserve decision provenance.

---

### 1.3 The Async/Threading Evolutionary Seam

**Archaeology** identifies Layer 2's "vestigial structure": `threading.local()` for statistics alongside `contextvars.ContextVar` for `IterState`. Documents this as "pre-async design remnant."

**Simulation** devotes Cycle 4 to the async migration problem: `threading.local()` shared across coroutines, `statistics` bleeding together, `time.sleep` blocking event loops.

**Structural** proves in Improvement 2 that eliminating `ContextVar` creates "async boundary erosion" — explicit parameter threading works for sync but fails at every `await` point.

**Convergence**: The split is not accidental — it represents a genuine architectural boundary. `IterState` (added later, uses contextvars) is per-task isolated. `statistics` (earlier, uses threading.local) is per-thread shared. In async code, these semantics diverge. This is visible in the code at lines 14 vs 101-102.

---

## 2. STRONG SIGNALS — Findings in Exactly TWO Analyses

### 2.1 WHERE + WHEN: The Copy Semantics Confusion

**Archaeology** identifies the "scar of evolutionary pressure" in `wraps()`:
```python
wrapped_f.statistics = {}  # Initialize
# ...
wrapped_f.statistics = copy.statistics  # Reassign
```

**Simulation** documents the consequences across Cycles 1-2: teams confused about which statistics object is authoritative, `tracked_call.statistics["attempt_number"]` returning wrong values.

**Missing from Structural**: The structural analysis focuses on architectural constraints, not the user-facing confusion from evolutionary scars.

**Insight**: The copy pattern was retrofitted. Original design assumed single-use `Retrying` instances. Decorator reuse forced the copy-and-reattach dance. This is visible archaeology and causes temporal confusion, but isn't a structural impossibility — just a design debt.

---

### 2.2 WHERE + WHY: Action Chain as Dynamic State Machine

**Archaeology** documents in Layer 3: strategies compose through "dynamic action chain building" — `_begin_iter` → `_post_retry_check_actions` → `_post_stop_check_actions`.

**Structural** proves this is the core of the impossibility: actions depend on `outcome`, which requires `Future`, which requires allocation. The action chain is the mechanism that couples everything.

**Missing from Simulation**: The temporal analysis sees the action chain become "sacred code" but doesn't explain WHY it's untouchable — only that teams fear it.

**Insight**: The action chain is tenacity's central architectural feature AND its central constraint. It enables the compositional flexibility (any combination of `stop`, `wait`, `retry`, callbacks) but creates the coupling that forces allocation and prevents speculative fast paths.

---

### 2.3 WHEN + WHY: Async Migration as Structural Boundary

**Simulation** Cycle 4: async adoption breaks assumptions — decorator doesn't await, `threading.local` semantics wrong, `time.sleep` blocks.

**Structural** Improvement 2: eliminating `ContextVar` for explicit threading creates "async boundary erosion" — at every `await`, state must be captured/restored.

**Missing from Archaeology**: The layer analysis documents the `threading.local` vs `contextvars` split but doesn't emphasize that this represents a hard boundary — not just a legacy remnant, but an architectural seam where two paradigms meet.

**Insight**: Async is not a migration problem to be solved — it's a structural boundary. The code has sync (`Retrying.__call__`) and async (presumably `AsyncRetrying` in full library) paths that share the action chain machinery but have fundamentally different execution models.

---

## 3. UNIQUE PERSPECTIVES — Findings in Only ONE Analysis

### 3.1 Unique to Archaeology (WHERE)

**The IterState Initialization Bug Vector**

Lines 111-113 in `Retrying.__call__`:
```python
def __call__(self, fn, *args, **kwargs):
    _iter_state_var.set(IterState())  # EXPLICIT
```

But in `BaseRetrying.__iter__`:
```python
def __iter__(self):
    self.begin()
    # No explicit IterState initialization!
```

The `__iter__` path relies on lazy creation in the `iter_state` property. If an outer context set `_iter_state_var`, `__iter__` inherits stale state.

**Why others missed this**: Simulation sees symptoms (ContextVar bleed) but not the exact code location. Structural focuses on constraints, not bugs.

---

**The Statistics >100 Clearing as Design Decision**

Lines 117-119:
```python
if len(self._local.statistics) > 100:
    self._local.statistics.clear()
```

Archaeology identifies this as a "vestigial structure" — why 100? Why clear instead of cap?

**Why others missed this**: Simulation mentions "mysterious gaps" in monitoring but doesn't find the code. Structural doesn't address specific implementation quirks.

---

**The Dead Pattern: Retry Strategy Diminished by RetrySignal**

Layer 3 documents that when `RetrySignal` is used, the `retry` strategy is "completely bypassed":
```python
if not self.iter_state.is_explicit_retry:
    self._add_action_func(self._run_retry)  # Only run if not explicit
```

This suggests `RetrySignal` was added later, partially obsoleting the `retry` strategy's role.

**Why others missed this**: Simulation documents RetrySignal being forgotten but not the structural change in control flow. Structural focuses on the main path, not the explicit-retry edge case.

---

### 3.2 Unique to Simulation (WHEN)

**The Retry Storm from Synchronized Exponential Backoff**

Cycle 1: Ten services with `wait_exponential` retry simultaneously. Without jitter, all retry at t=1s, t=2s, t=4s... The coordination amplifies the problem.

**Why others missed this**: Archaeology sees structure, not runtime behavior at scale. Structural sees constraints, not emergent phenomena from multiple independent instances.

---

**Sacred Config Cargo Culting**

Cycle 2: `min=4, max=10` becomes doctrine. Original author left. Values become "sacred numbers" without remembered justification.

**Why others missed this**: Archaeology documents what the code allows, not how teams use it. Structural proves what's possible, not what becomes folklore.

---

**Exception Type Migration Breaking Retry Conditions**

Cycle 3: `requests` → `httpx` migration. `retry_if_exception_type(ConnectionError)` no longer matches `httpx.ConnectError`. Retry conditions are brittle to dependency changes.

**Why others missed this**: Archaeology documents the `retry` strategy mechanism, not how it rots over time. Structural focuses on architecture, not ecosystem evolution.

---

### 3.3 Unique to Structural (WHY)

**The Speculative Fast Path Improvement and Its Recreated Problem**

Proposed improvement: try the function first, only build retry machinery if needed. Result: two execution paths with different exception semantics (native `raise` vs `RetryError` wrapper).

**Why others missed this**: Archaeology documents what exists. Simulation documents what happens. Only structural analysis asks "what if we tried to fix it?" and discovers the problem migrates, not disappears.

---

**The Meta-Law: Cognitive Surface Conservation**

```
Information Locality × Access Dispatch = Constant Cognitive Surface
```

This is deeper than the flexibility/traceability tradeoff — it explains WHY that tradeoff exists. Cognitive effort to trace execution is conserved, just redistributed.

**Why others missed this**: Archaeology and Simulation derive conservation laws within their domains. Only Structural steps back to ask what all conservation laws conserve.

---

**The Easy Questions / Hard Questions Invariant**

```
(Easy questions) ∪ (Hard questions) = All possible questions about execution
```

Architecture cannot reduce the set of questions — only move the boundary between easy and hard.

**Why others missed this**: This is a meta-structural insight about the nature of architectural decisions, not discoverable by examining layers or running time forward.

---

## 4. CONSERVATION LAW CONVERGENCE

### The Three Laws

| Analysis | Law | A (Flexibility) | B (Visibility) |
|----------|-----|-----------------|----------------|
| Archaeology | Hook Composability × Execution Traceability = k | 7 hook points | 1/4 static trace depth |
| Simulation | Retry Flexibility × Runtime Debuggability = k | Configuration surface area | P(answer "why") |
| Structural | Information Locality × Access Dispatch = k | Context reachability | Path count |

### Mapping the Vocabularies

**"Hook Composability" ≈ "Retry Flexibility" ≈ "Information Locality"**

All three measure: *How many distinct behaviors can be expressed and how easily can they be composed?*

- Hook points are compositional units
- Configuration options are behavioral units
- Information locality is how far influence can reach

**"Execution Traceability" ≈ "Runtime Debuggability" ≈ "1/Access Dispatch"**

All three measure: *How easily can a specific execution be reconstructed?*

- Trace depth is code distance
- Debuggability is question-answerability
- Access dispatch is path explosion

### META-CONSERVATION LAW

**Expressive Power × Reasoning Tractability = Constant**

Where:
- **Expressive Power** = |{distinct behaviors the system can express}|
- **Reasoning Tractability** = P(correctly explaining a specific execution)

This subsumes all three:

| Analysis | Expressive Power (A) | Reasoning Tractability (B) |
|----------|---------------------|---------------------------|
| Archaeology | Hook combinations | Static call graph following |
| Simulation | Configuration permutations | Production log interpretation |
| Structural | Information reach | Cognitive path tracing |

**Proof of subsumption**:

The action chain (`_add_action_func`) is the mechanism that enforces this conservation. Each conditional branch:
1. Increases expressive power (new behavior possible)
2. Multiplies execution paths (reasoning must consider more cases)
3. Does not add logging (reasoning tractability decreases)

The conservation is enforced by Python's control flow: `if` statements add paths but don't add traces. The action chain is a pure embodiment of this.

---

## 5. DIVERGENCE MAPPING — Where Analyses Disagree

### 5.1 Intentional Design vs. Accidental Calcification

**Archaeology**: Describes "Layer 3: Strategy Composition Layer" — sounds designed, intentional
**Simulation**: Describes "cargo-culted patterns", "sacred configs" — sounds accidental, emergent

**The divergence**: Archaeology sees structure as designed. Simulation sees structure as evolved.

**Resolution**: Both are true. The action chain was designed. The configuration values (`min=4, max=10`) and usage patterns evolved. Archaeology reveals the skeleton; simulation reveals the flesh that grew around it.

---

### 5.2 Bug vs. Inevitability

**Archaeology**: IterState initialization divergence is a "latent bug vector" — fixable
**Structural**: This coupling is "mandatory" — actions depend on outcome, outcome requires Future — architectural, not fixable

**The divergence**: Is the code wrong, or is the architecture constrained?

**Resolution**: They're different things. The `__iter__` vs `__call__` initialization difference is a bug (both paths should initialize). But the underlying allocation that makes `IterState` necessary is architectural. Archaeology finds local bugs; structural proves global constraints.

---

### 5.3 Knowledge Loss vs. Knowledge Redistribution

**Simulation**: "Lost Knowledge Inventory" — things once known, now forgotten
**Structural**: Questions move from "easy" to "hard" bucket — knowledge doesn't disappear, just becomes harder to access

**The divergence**: Is knowledge lost or hidden?

**Resolution**: Simulation is about team knowledge (social). Structural is about code traceability (technical). Team knowledge of "why min=4" is lost. Code traceability of "why did attempt 3 retry" is hard. Both are forms of the same conservation — as system grows, reasoning about it requires more effort.

---

### 5.4 The Most Significant Divergence: Is Improvement Possible?

**Archaeology**: Documents what exists, implies understanding enables modification
**Simulation**: Documents degradation, implies systems rot inevitably
**Structural**: Proves "improvements" recreate problems at deeper levels

**The divergence**: Can tenacity be improved?

| Analysis | Answer | Reasoning |
|----------|--------|-----------|
| Archaeology | Maybe | Understanding layers reveals modification points |
| Simulation | No | Systems calcify, knowledge rots |
| Structural | No* | Improvements migrate complexity, don't eliminate it |

*Structural's caveat: "You can choose which questions to make easy."

**Synthesis**: Improvement is possible but constrained. You cannot improve the current architecture along its current dimensions (more flexibility AND more traceability). You CAN choose different dimensions — make different questions easy by accepting different hard questions.

---

## 6. SYNTHESIS — The One Deepest Insight

### The Retry Uncertainty Principle

**"You can precisely specify WHAT conditions trigger retry, OR you can precisely determine WHY a specific retry occurred — but both at once is structurally impossible."**

This principle emerges only from integrating all three perspectives:

**From Archaeology (WHERE)**: The action chain (`_add_action_func`) dynamically constructs execution based on runtime state. The "what" is specified at decoration time (`stop=stop_after_attempt(3)`). The "why" is distributed across `iter_state.retry_run_result`, `iter_state.stop_run_result`, `is_explicit_retry` — ephemeral values that don't persist.

**From Simulation (WHEN)**: Over time, teams lose the ability to explain behavior. The "what" becomes sacred config (`min=4, max=10`). The "why" becomes folklore ("always use reraise"). Configuration options grow (expressive power), debuggability shrinks (reasoning tractability).

**From Structural (WHY)**: This is not a bug. It's the conservation of cognitive surface. The action chain architecture makes it easy to ask "what will happen?" (strategies are composable objects) but hard to ask "what happened?" (execution path is dynamically determined, unlogged).

### The Mechanism

```python
def _begin_iter(self, retry_state):
    self.iter_state.reset()  # Erase history
    fut = retry_state.outcome
    if fut is None:
        if self.before is not None:
            self._add_action_func(self.before)  # Conditional: no trace
        self._add_action_func(lambda rs: DoAttempt())
        return
    # Branch: depends on fut, which depends on prior execution
    self.iter_state.is_explicit_retry = fut.failed and isinstance(fut.exception(), RetrySignal)
    # ... more conditionals, none logged
```

Every `_add_action_func` is:
1. A flexibility point (composable behavior)
2. An unlogged branch (reasoning opacity)

The conservation is exact: each flexibility point adds a branch that doesn't explain itself.

### The Principle Restated

**Tenacity's architecture makes retry behavior specifiable but opaque.**

You can say precisely:
```python
@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=1, max=60),
       retry=retry_if_exception_type(ConnectionError, TimeoutError))
```

But you cannot, from production artifacts, reconstruct:
- "Did attempt 3 fail because of ConnectionError or TimeoutError?"
- "Why did the retry stop at attempt 4 when I configured 5?"
- "What was the actual wait duration between attempts 2 and 3?"

The `statistics` dictionary exists but:
- Is per-thread (wrong for async)
- Clears at 100 entries (arbitrary)
- Records counts, not decision reasons

### What This Means for Retry Libraries

**Any retry library faces the same constraint:**

Retry logic exists in the gap between expectation and reality. The more precisely you can specify expectations (exception types, predicates, conditions), the more possible executions exist, and the harder any specific execution is to explain.

The only degrees of freedom are:
1. **What to make easy**: Configuration simplicity? Debugging clarity? Performance?
2. **What to make hard**: The complement of the above

Tenacity chose:
- Easy: Specifying complex retry behavior compositionally
- Hard: Explaining why specific behavior occurred in production

Other libraries could choose differently:
- Make explanation easy: fixed retry policies, verbose logging, execution traces
- Make specification hard: fewer hooks, less composability, simpler model

**But the tradeoff is unavoidable.**

---

### Supporting Evidence Summary

| Claim | Archaeology | Simulation | Structural |
|-------|-------------|------------|------------|
| Action chain is dynamic/unlogged | Layer 3: `_add_action_func` pattern | Cycle 5: sacred code zones | Core of impossibility proof |
| Flexibility/traceability tradeoff | Hook × Traceability = k | Flexibility × Debuggability = k | Locality × Dispatch = k |
| Improvement migrates complexity | — | — | Both improvements recreate problem |
| Teams lose explanatory power | Copy semantics scar | Sacred configs, lost WHY | Cognitive surface constant |

---

### The Final Verdict

Tenacity is not poorly designed. It is designed for a specific question: "How can I express complex retry behavior?"

It answers that question well. The cost is that it cannot answer a different question well: "Why did this specific retry behave this way?"

**No retry library can answer both questions equally well.** The action chain architecture makes this explicit. Other architectures would make it implicit. But the tradeoff — between specification power and explanation power — is fundamental to the retry problem itself.

  [2mSaved to .deep/findings/real_code_tenacity.md[0m
  [2mSaved to .deep/findings/real_code_tenacity.md[0m

[32m3-Way Pipeline complete: 4 passes, models: sonnet[0m
  [2mUse /fix to pick issues, or /fix auto to fix all[0m
