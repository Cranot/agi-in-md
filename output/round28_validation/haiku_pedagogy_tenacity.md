# Tenacity Retry Module: Explicit Choices → Transferred Corruption

I'll analyze this using the **pedagogy lens** (your champion 9.5/10 model). This traces not just what the code *does*, but what it *teaches* — and what breaks when someone internalizes its patterns for a different problem.

---

## EXPLICIT CHOICES & INVISIBLE REJECTIONS

| Choice | Mechanism | Rejects |
|--------|-----------|---------|
| **Action Chain Queue** | Lambdas appended to list, executed sequentially in `iter()` | Recursive calls, event callbacks, coroutines, state machines |
| **IterState Reset-Per-Cycle** | `self.iter_state.reset()` at start of each iteration | Immutable event logs, transaction records, audit trails |
| **thread.local() State Isolation** | Per-thread storage `self._local` | Per-call context, explicit parameter passing, global state |
| **Binary Decision Trees** | `stop(retry_state)` returns True/False at fixed points | Continuous scoring, multi-criteria decisions, probabilistic outcomes |
| **Copy-on-Modify** | `copy(retry=_unset, ...)` creates new instance | In-place mutation, builder pattern, context managers |
| **Dual-Purpose Outcome (Future)** | One field holds both result AND exception | Separate success/failure channels, tagged unions, Result<T,E> types |
| **Timestamp-at-Mutation** | Capture `monotonic()` when state changes | Capture-at-creation, delayed aggregation, wall-clock only |
| **Generator Protocol** | `yield AttemptManager` for attempt blocks | Async/await, callback hell, explicit state machines |
| **Late-Binding Lambdas** | `lambda rs: ...` captures context NOW, executes LATER | Direct function calls, dependency injection, message passing |
| **Mutable Statistics Dict** | `self.statistics["attempt_number"] +=1` persists across cycles | Event stream, immutable snapshots, observer pattern |
| **Explicit Retry Exception** | Raise `TryAgain` to force retry | Flag fields, return values, side effects |

---

## NEW ARTIFACT: Request Pipeline Validator

Someone who internalized Tenacity's patterns faces a **different problem**: building a **multi-stage validation pipeline with response caching, health checks, and degraded fallbacks**.

They unconsciously resurrect:

```python
# Pipeline Validator: Tenacity's patterns applied to validation, not retry

import dataclasses, time, threading

@dataclasses.dataclass
class ValidationState:
    """Tenacity teaches: reset per attempt → reset per validation stage"""
    stages_run: list = dataclasses.field(default_factory=list)
    validation_passed: bool = False
    cache_hit: bool = False
    fallback_used: bool = False

    def reset(self):
        self.stages_run = []
        self.validation_passed = False
        self.cache_hit = False
        self.fallback_used = False


class ValidationPipeline:
    """Tenacity pattern: action chain + statistics dict + thread.local isolation"""
    
    def __init__(self, validate_schema, validate_auth, use_cache=True, 
                 fallback=None, before_validate=None):
        self.validate_schema = validate_schema
        self.validate_auth = validate_auth
        self.use_cache = use_cache
        self.fallback = fallback
        self.before_validate = before_validate
        self._local = threading.local()  # ← Tenacity pattern: per-thread isolation
        
    @property
    def statistics(self):
        """Tenacity taught this: metrics in a mutable dict"""
        if not hasattr(self._local, "statistics"):
            self._local.statistics = {
                "validations_run": 0,
                "cache_hits": 0,
                "validation_errors": [],  # ← PROBLEM: list doesn't reset!
                "latencies_by_stage": {},  # ← PROBLEM: dict merges across calls
            }
        return self._local.statistics

    @property
    def val_state(self):
        """Tenacity pattern: mutable state per call"""
        if not hasattr(self._local, "val_state"):
            self._local.val_state = ValidationState()
        return self._local.val_state

    def begin(self):
        """Tenacity pattern: clear stats at start"""
        self.statistics.clear()
        self.statistics["validations_run"] = 0
        self.statistics["cache_hits"] = 0
        self.statistics["validation_errors"] = []
        self.statistics["start_time"] = time.monotonic()

    def validate(self, request):
        """Parallel structure to Tenacity.iter() — but BROKEN"""
        self.begin()
        actions = []
        
        # Tenacity pattern: build action chain
        if self.before_validate:
            actions.append(self.before_validate)
        
        # Check cache (Tenacity: TryAgain analogue)
        def check_cache(req):
            if self.use_cache and hasattr(req, "_cached_result"):
                self.statistics["cache_hits"] += 1
                return ("cached", req._cached_result)
            return None

        actions.append(check_cache)
        
        # Validation stages
        def run_schema_validation(req):
            try:
                result = self.validate_schema(req)
                self.val_state.stages_run.append("schema")
                return ("valid", result)
            except ValueError as e:
                # Tenacity pattern: capture exception in state
                self.statistics["validation_errors"].append(e)  # ← SILENT CORRUPTION
                return None

        def run_auth_validation(req):
            try:
                result = self.validate_auth(req)
                self.val_state.stages_run.append("auth")
                return ("valid", result)
            except ValueError as e:
                self.statistics["validation_errors"].append(e)  # ← ACCUMULATES
                return None

        actions.append(run_schema_validation)
        actions.append(run_auth_validation)

        # Execute action chain (Tenacity pattern)
        result = None
        for action in actions:
            result = action(request)
            if result:
                break

        if result and result[0] == "valid":
            return result[1]
        
        # Fallback (Tenacity: retry_error_callback)
        if self.fallback:
            return self.fallback(request)
        
        raise ValueError(f"Validation failed: {self.statistics['validation_errors']}")

    def copy(self, use_cache=None, fallback=None):
        """Tenacity pattern: copy-on-modify"""
        return ValidationPipeline(
            validate_schema=self.validate_schema,
            validate_auth=self.validate_auth,
            use_cache=use_cache if use_cache is not None else self.use_cache,
            fallback=fallback if fallback is not None else self.fallback,
            before_validate=self.before_validate,
        )
```

---

## WHICH REJECTED ALTERNATIVES GET RESURRECTED?

The pipeline validator **resurrects patterns Tenacity explicitly rejected for its problem**:

| Resurrected Pattern | Why Tenacity Rejected | Why Pipeline Dev Brings It Back | Problem |
|---|---|---|---|
| **Mutable list in statistics** | Tenacity: numeric metrics only (attempt_number, idle_for) | Pipeline needs "all errors seen" — looks like natural extension | List doesn't reset; accumulates across validations |
| **Timestamp per stage** | Tenacity: one timestamp per outcome (clear boundary) | Pipeline: latency per validation stage (seems more granular) | Monotonic() may not differentiate sub-ms stages; precision illusory |
| **thread.local for copy() isolation** | Tenacity: necessary for wraps() re-entrance | Pipeline: "copies should be isolated" (wrong assumption) | Both p1=pipe.copy(cache=True) and p2=pipe.copy(cache=False) share self._local |
| **Copy-on-modify for config** | Tenacity: immutable decision params (stop, wait, retry) | Pipeline: "I want different validation rules per instance" | State mutation affects all instances in same thread |
| **Binary decisions only** | Tenacity: retry yes/no is fundamental | Pipeline: "cache hit/miss is yes/no decision" | Loses semantic difference: cache-miss vs cache-stale (both "no hit") |

---

## SILENT PROBLEMS: Transfer as Hidden Assumption

**The Pedagogy Law That Transfers:**
> *"State is only needed for bookkeeping and metrics. All decisions are pure functions of attempt/cycle history."*

In Tenacity: True. Retry at attempt N depends only on outcomes 1..N-1.

In Pipeline: **Silently False.** Validation decisions depend on:
- Whether THIS request was cached (side effect)
- Whether auth token expired (time, not history)
- Whether rate limit counter decremented (external state)

**What The Pattern Teaches (Invisibly):**

1. **"Mutable dict for metrics is safe"** → Pipeline dev copies it, but dict values have different lifecycles:
   - `attempt_number`: scalar, safe to increment
   - `validation_errors`: list, unsafe to append (no reset boundary)
   
2. **"thread.local isolation works"** → Copy pattern makes dev think: "I'll create p1 and p2 with different configs, they'll be independent." But thread.local is shared:
   ```python
   p1 = pipe.copy(use_cache=True)
   p2 = pipe.copy(use_cache=False)
   
   p1.validate(req_A)  # statistics["cache_hits"] += 1 → thread.local.statistics
   p2.validate(req_B)  # reads thread.local.statistics (still has cache_hits=1!)
   ```

3. **"Action lambdas capture context correctly"** → In Tenacity, they capture `self` (constant). In pipeline:
   ```python
   actions.append(lambda req: validate_schema(req))  # req is CURRENT request
   # later...
   result = action(modified_request)  # WHICH request?
   ```

---

## VISIBLE FAILURE: Copy-on-Modify Doesn't Isolate

```python
# Developer expects this to work:
validator_with_cache = pipeline.copy(use_cache=True)
validator_no_cache = pipeline.copy(use_cache=False)

# They run in the SAME THREAD:
result_A = validator_with_cache.validate(request_A)
# validator_with_cache.statistics["cache_hits"] → incremented

result_B = validator_no_cache.validate(request_B)
# validator_no_cache.statistics["cache_hits"] → ALSO incremented!
# Because both share self._local in the same thread

print(validator_no_cache.statistics["cache_hits"])  # Expect 0, get 1 ← VISIBLE BUG
```

**Why it's visible:** Test runner creates request_A, then request_B in sequence. Cache metrics don't match intent. Developer sees "why does the no-cache pipeline report cache hits?"

---

## SILENT FAILURE: Mutable List in Statistics

```python
# Run 1: validate request_A
validator.validate(request_A)
print(validator.statistics["validation_errors"])  # [ValueError("Missing field")]

# Run 2: validate request_B (different validator instance, same thread.local!)
validator2 = pipeline.copy()  # shares self._local
validator2.validate(request_B)
print(validator2.statistics["validation_errors"])  
# Expect: [ValueError("Invalid auth")]
# Get: [ValueError("Missing field"), ValueError("Invalid auth")]  ← silent accumulation
```

**Why it's silent:** 
- No crash, just wrong metrics
- Only visible if you inspect statistics between runs
- Looks like "concurrent error reporting" rather than a bug
- Developer attributes it to "oh, we must still be accumulating from previous…"
- Takes **3-5 hours of debugging** to realize `begin()` clears dict but NOT the list references

---

## THE PEDAGOGY LAW: What Constraint Transfers as Assumption?

**Tenacity's Constraint:**
> Retry decisions are **stateless except for this one outcome + attempt count**. All metrics are **scalars** (attempt_number: int, idle_for: float).

**Transfers As Assumption in Pipeline:**
> Validation decisions are **stateless except for pass/fail + stage history**. All metrics can be **any JSON-serializable value**.

**The Hidden Transfer:**
Tenacity's constraint was: *"Use dict only for scalar metrics because they're idempotent across retry cycles."* 

Pipeline dev inherits: *"Use dict for any metric because it's a 'statistics' pattern."*

The word "statistics" becomes a permission structure that hides the assumption.

---

## PREDICTED FIRST FAILURE: Slowest to Discover

**The Invisible Transferred Decision:**

**Decision Point:** "State cleared at call boundary, not at instance boundary"

**In Tenacity:** Works because `begin()` is called at START of Retrying.__call__():
```python
def __call__(self, fn, *args, **kwargs):
    self.begin()  # ← clears statistics every call
    retry_state = RetryCallState(...)
```

**Transfers To Pipeline As:** "I'll call begin() too"
```python
def validate(self, request):
    self.begin()  # ← clears statistics
    actions = [...]
    for action in actions:
        ...
```

**But:**
- Tenacity's begin() clears a dict: `self.statistics.clear()`
- Pipeline's begin() also clears a dict: `self.statistics.clear()`
- BUT the dict reference is SHARED via thread.local
- And begin() is called INSIDE validate()
- So: clear dict, populate dict, populate list in dict — all in one call ✓

**Failure Point (Hard to Discover):**

After the SECOND validate() call on the SAME thread:
```python
val = ValidationPipeline(...)

# Call 1
val.validate(request_A)  # begin() clears dict, populates validation_errors=[e1]
assert len(val.statistics["validation_errors"]) == 1  # ✓ Pass

# Different context, same thread
val.validate(request_B)  # begin() clears dict... 
# BUT validation_errors was a LIST REFERENCE, not recreated
# dict.clear() removes the KEY, but...

print(val.statistics)  # Fresh dict, no validation_errors key
# OR: validation_errors is STILL the old list if begin() didn't clear it right
```

**Why Slowest to Discover:**
1. **Not a crash** — silent metric corruption
2. **Looks intentional** — "oh, we're tracking all errors"
3. **Emerges in production** — happens across request boundaries, hard to reproduce in unit tests
4. **Debugging leads nowhere** — metrics "look right" in isolation, wrong in aggregate
5. **The code IS correct in Tenacity** — pattern transfer was "sound"
6. **Developer blames timing** — "maybe requests are overlapping?" (no, same thread)
7. **Root cause is invisible** — the assumption "lists don't survive dict.clear()" was never stated, so it was never questioned

**Time to diagnosis:** 2-4 weeks (metric accumulation only noticed in production dashboards, post-mortems take time).

---

## SUMMARY: What This Artifact Teaches

Tenacity teaches through its patterns:
- ✓ Action chains compose well
- ✓ State isolation via thread.local is safe
- ✗ (Invisibly) Metrics ARE state-local; reset boundaries matter
- ✗ (Invisibly) Mutable structures in dicts need explicit reset logic

When generalized to "pipeline validation," the ✗ assumptions kill you first, slowest.

**The pedagogy debt:** The code pattern is elegant enough to be copied blindly, but the constraint it encodes (state cleared at call boundary) doesn't transfer to the new problem.
