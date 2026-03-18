# Contrast Operation on Tenacity Analysis

## STEP 1: Inverted Alternative — Inline State Machine

The core architectural choice in Tenacity is **deferred execution through runtime-constructed action chains with type-based dispatch**. The inversion is **immediate execution through a hardcoded state machine with explicit transitions**.

```python
class InlineRetry:
    """Inverted architecture: no action chains, no type signals, direct execution."""
    
    def __init__(self, stop, wait, retry, before, after, before_sleep, sleep):
        self.stop = stop
        self.wait = wait
        self.retry = retry
        self.before = before
        self.after = after
        self.before_sleep = before_sleep
        self.sleep_fn = sleep
        self.attempt_number = 1
        self.start_time = None
    
    def execute(self, fn, args, kwargs):
        """Single method, all logic inline, no indirection."""
        self.start_time = time.monotonic()
        
        while True:
            # STATE: ATTEMPT
            if self.before:
                self.before(self._make_state(fn, args, kwargs))
            
            try:
                result = fn(*args, **kwargs)
                outcome = ('success', result, None)
            except BaseException as e:
                outcome = ('failure', None, e)
            
            # STATE: EVALUATE
            state = self._make_state(fn, args, kwargs, outcome)
            
            if outcome[0] == 'success':
                if self.after:
                    self.after(state)
                return outcome[1]  # TERMINAL: return result
            
            # STATE: RETRY_DECISION
            should_retry = self.retry(state)
            
            if not should_retry:
                if self.after:
                    self.after(state)
                raise RetryError(state)  # TERMINAL: exhausted
            
            # STATE: WAIT_DECISION
            if self.after:
                self.after(state)
            
            wait_time = self.wait(state)
            
            if self.before_sleep:
                self.before_sleep(state)
            
            # STATE: SLEEP
            self.sleep_fn(wait_time)
            self.attempt_number += 1
            # LOOP: back to ATTEMPT
    
    def _make_state(self, fn, args, kwargs, outcome=None):
        """State object passed through — no contextvars needed."""
        return SimpleNamespace(
            fn=fn, args=args, kwargs=kwargs,
            attempt_number=self.attempt_number,
            outcome=outcome,
            start_time=self.start_time
        )
```

**Key inversions:**
- No `iter()` returning marker objects → direct execution loop
- No `DoAttempt`/`DoSleep` type signals → explicit `if/elif` branches
- No action chain construction → all logic in one method
- No `ContextVar` state isolation → state passed as parameter
- No `_add_action_func` queueing → immediate execution

---

## STEP 2: Comparison

### Claims that SURVIVE inversion (problem invariants)

| Claim | Survives? | Why |
|-------|-----------|-----|
| Retry requires a termination condition | **YES** | Both designs must decide when to stop |
| Retry requires state tracking (attempt count, outcome) | **YES** | Both track `attempt_number` and `outcome` |
| Retry requires a sleep/wait mechanism | **YES** | Both need to pause between attempts |
| Callbacks (before/after/before_sleep) must be invoked at specific points | **YES** | Both call same hooks at same logical points |
| Exception handling must distinguish retryable from fatal | **YES** | Both filter exceptions through `retry()` predicate |

### Claims that COLLAPSE under inversion (implementation artifacts)

| Claim | Collapses? | Why |
|-------|------------|-----|
| "Type as control signal" (DoAttempt/DoSleep) | **YES** | Inline version uses explicit branches, no type-based dispatch |
| "Deferred action chain construction" | **YES** | Inline executes immediately, no queue |
| "Context-local state isolation" | **YES** | Inline passes state as parameter, no ContextVar |
| "Action list order differs between explicit and implicit retry" | **YES** | Inline has single code path, no action list |
| "Callers depend on action chain order" | **YES** | Inline has no action chain, no hidden ordering dependency |

### What becomes visible ONLY through comparison

**The callback ordering problem is structural, not architectural.**

In Tenacity, I claimed the action chain "conceals" the callback order. But the inline version *also* has callback ordering constraints:
- `before` must run before the attempt
- `after` must run after outcome known but before sleep decision
- `before_sleep` must run after retry decision but before sleep

**Neither design can reorder these callbacks arbitrarily.** The ordering is dictated by the *problem*, not hidden by the implementation. The action chain makes ordering *configurable* (you could inject actions), but the logical constraints remain.

**What I missed:** The action chain doesn't conceal ordering — it *externalizes* ordering so callers can modify it. The inline version hardcodes ordering but can't be extended. This is the genuine trade-off.

---

## STEP 3: Revised Conservation Law

**Original law:** Deferral Depth × Execution Transparency = Constant

**Problem:** This law fails under inversion. The inline version has zero deferral and maximum transparency. If the product were constant, the deferred version would have zero transparency — but it doesn't. You *can* trace Tenacity's control flow; it just requires simulating the action list.

**Deeper law:**

**Extensibility Surface × Locality = Constant**

Where:
- **Extensibility Surface** = number of injection points where behavior can be modified without code changes
- **Locality** = fraction of control flow visible within a single method

| Design | Extensibility Surface | Locality | Product |
|--------|----------------------|----------|---------|
| Tenacity (action chains) | 7+ injection points (stop, wait, retry, before, after, before_sleep, retry_error_callback) + arbitrary action injection via `_add_action_func` | Low (must trace through `iter()`, `_begin_iter()`, `_post_retry_check_actions()`, `_post_stop_check_actions()`) | High × Low = Constant |
| Inline State Machine | 7 injection points (same callbacks) but NO action injection | High (all logic in `execute()`) | Low × High = Constant |

**The product is conserved:** You can have many extension points with scattered control flow, or fewer extension points with localized control flow. The callbacks are invariant (required by the problem), but the *action injection capability* is the architectural variable.

---

## STEP 4: What the Contrast Reveals

### What my original analysis concealed:

**1. I conflated "hidden" with "scattered."**

My original analysis claimed the action chain "conceals" the retry path. It doesn't conceal — it *distributes*. The control flow is fully visible if you read four methods in sequence. The inline version makes me read 40 lines in one method. Neither is "concealed"; both require reading ~40 lines of code. The difference is *spatial*, not *informational*.

**2. I misidentified the trade-off.**

The trade-off isn't "deferral vs. transparency" — it's **"plugin architecture vs. debuggability."** Tenacity's action chain exists so users can inject custom behavior between retry phases. My analysis treated this as an implementation quirk rather than the *defining feature*.

**3. The type-based dispatch is not about indirection.**

`DoAttempt` and `DoSleep` exist because `iter()` must *yield* control back to the caller (the `__iter__` loop). The inline version doesn't need them because it *executes* the function directly. The type signals solve a specific problem: **separating the retry logic from the function execution.** Tenacity's `iter()` doesn't know how to call the function — it only knows *when* to attempt. The types signal intent across that boundary.

**4. The real structural property I missed:**

**Boundary Granularity × Coupling = Constant**

Tenacity draws a boundary at the `iter()` level — retry logic on one side, function execution on the other. Communication across this boundary requires signaling (types). The inline version draws no boundary — retry and execution are coupled in one method.

The finer the boundary, the more signaling needed. The coarser the boundary, the more coupling. This trade-off is invisible when analyzing only one design.

---

## Summary

My original analysis was **architecturally accurate but causally inverted**. I described *how* Tenacity works (deferred action chains, type signals, context isolation) correctly. But I misidentified *why* these mechanisms exist — not to "conceal" control flow, but to **enable plugin extensibility while maintaining boundary separation**.

The contrast operation reveals: **The action chain is not a clever trick — it's the minimum mechanism required to support arbitrary callback injection without hardcoding.** The inline alternative proves this: remove the action chain, and you lose the ability to modify retry behavior without editing the core loop.
