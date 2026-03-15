## Structure First: Level 11 Diagnostic

---

### Falsifiable Claim

> `wraps()` creates three coreferential handles to the same per-call statistics dict: `copy._local.statistics`, `self._local.statistics`, and `wrapped_f.statistics`. The first two are thread-local and correctly isolate concurrent calls. The third is a non-thread-local attribute on a shared closure. The assignment `wrapped_f.statistics = copy.statistics` executes on every call without synchronization. In concurrent execution, the last writer wins: T1's `dict1` and T2's `dict2` are both correct in their respective thread-locals, but `wrapped_f.statistics` holds whichever dict's assignment executed last. The earlier thread's statistics are lost from the observable attribute with no exception, no flag, no distinguishable signal. The thread-local architecture correctly solves the execution isolation problem and then exposes the result through a non-thread-local surface — the only surface users can reach without knowing thread identity.

**Falsifiable test**: Decorate a function with `@retry(stop=stop_after_attempt(5))`. Call it from N concurrent threads, each with a distinct failure pattern. After all threads complete, `wrapped_f.statistics["attempt_number"]` will match exactly one thread's call. N−1 threads' statistics are unobservable through the public API. The test confirms N−1 calls happened (through their side effects) but only 1 call is statistically visible.

---

### The Dialectic

**Expert 1 — Defender**

The claim holds precisely. The GIL makes `wrapped_f.statistics = copy.statistics` atomic as a bytecode operation — no dict corruption. But the logical race is between the assignment and any read of the attribute from another thread. T1 sets `wrapped_f.statistics = dict1`, begins its call, populates `dict1`. T2 sets `wrapped_f.statistics = dict2`, overwriting T1's assignment before T1's call completes. T1's statistics are now orphaned: correct in `self._local.statistics` (T1's slot), unreachable through `wrapped_f.statistics`. The architecture correctly isolates execution state through thread-locals and then exports statistics through an attribute that has none of that isolation. The race is in the publication mechanism, not the computation.

**Expert 2 — Attacker**

Statistics observability under concurrent use is not a stated contract. `wrapped_f.statistics` is documented by convention as "the last call's statistics." In sequential use this is correct. Concurrent users who need per-call statistics attribution must structure their code to handle it — using `wrapped_f.retry.statistics` from within the calling thread, or aggregating through their own mechanisms. The claim identifies a limitation of the API under a usage mode the API was not designed for. The single-attribute statistics surface is a convenience for the overwhelmingly common sequential case.

**Expert 3 — Prober**

Expert 2 says users should access `wrapped_f.retry.statistics` from within their calling thread. But `wrapped_f.retry.statistics` accesses `self._local.statistics` — and `self._local.statistics` is set to `copy.statistics` (the aliasing on Line 2) before the call runs. This works: on T1, after T1's call, `self._local.statistics` correctly returns `dict1`. The thread-local API is correct. The question is: *why does `wrapped_f.statistics` exist at all, given that the correct value is in `self._local.statistics`?*

Because `copy` — the object that owns `copy._local.statistics` — is ephemeral. After `copy(f, *args, **kw)` returns and `copy` goes out of scope, `copy._local` is garbage-collected. Without Line 1 (`wrapped_f.statistics = copy.statistics`), the statistics dict would be released with the copy. `wrapped_f.statistics` is not a design choice — it is the **only persistence mechanism** for statistics given the copy-per-call architecture. The aliasing is necessary for the statistics to outlive the copy. The race condition is not an implementation bug in the aliasing — it is a structural consequence of needing a persistent handle for an ephemeral value, given that the only available persistent handle is a shared closure attribute.

Expert 2's prescription ("access from the calling thread") reaches the correct value, but only because `self._local.statistics = copy.statistics` (Line 2) provides a thread-local alias — itself an aliasing mechanism, now one level deeper. The thread-local alias is correct and survives per-thread. The closure attribute is incorrect and doesn't. Both exist because the copy must be ephemeral, and statistics must outlive it.

---

### The Transformation

| | |
|---|---|
| **Initial claim** | `wrapped_f.statistics` races under concurrent assignment; last writer wins |
| **Transformed claim** | The copy-per-call architecture (correct for execution isolation) makes statistics ephemeral: they die with the copy. Making them observable requires a persistent handle. The only available persistent handles are the closure attribute (`wrapped_f.statistics`) and the original's thread-local (`self._local.statistics`). The thread-local is correct but thread-specific — inaccessible from monitoring contexts outside the calling thread. The closure attribute is accessible but thread-neutral — loses the thread-specificity that makes the thread-local correct. The race is not in the aliasing implementation; it is in the attempt to translate a thread-specific correct value into a thread-neutral observable. No thread-neutral persistent handle can represent a concurrent call's statistics correctly without serialization or per-caller indirection. |

---

### The Gap Is Itself Diagnostic

L10 analyzed intra-call value propagation: within a single call to `iter()`, inter-stage decisions (retry?, stop?, how long?) must flow between actions. L10 proved this requires shared mutable state because the loop discards return values.

L10's analytical lens — the action pipeline — cannot see cross-call dynamics. Each call to `iter()` resets `iter_state`, runs actions, and returns. The statistics problem is cross-call: each call produces state that must persist after the call ends and after the copy executing that call is GC'd.

The gap: L10 found the medium (IterState fields) that intra-call values flow through. L11 finds that cross-call values (statistics) must flow through a different medium (closure attribute, thread-local alias) because the intra-call medium (`iter_state`) is reset at the start of each call. L10's medium is reset-per-call. L11's medium is the only thing that survives a reset. They are the same structural problem at different scopes.

---

### The Concealment Mechanism: Triple Aliasing as Correctness Performance

The three-pointer aliasing in `wraps()` —

```python
copy = self.copy()
wrapped_f.statistics = copy.statistics  # Line A — persist across GC
self._local.statistics = copy.statistics  # Line B — thread-local access
return copy(f, *args, **kw)
```

— creates the appearance that the statistics are accessible through three consistent views. Both assignments execute before the call body runs. The dict begins empty; `copy.begin()` populates it; the call mutates it; after the call, all three references show the completed statistics. In sequential use, this is always correct. The three references' equivalence makes the mechanism look like redundant accessibility rather than what it is: an incompatible pair of access modes (thread-local for correctness, closure attribute for persistence) unified through an aliased dict that can only be correct for one mode at a time.

The concealment is completed by the dict interface itself. `wrapped_f.statistics["attempt_number"]` looks like accessing a property. Nothing in this access reveals that the dict's identity is reassigned on every call, that the assignment is unordered relative to concurrent calls, or that the correct value is in a thread-local inaccessible without thread identity. The dict is a transparent value container whose mutations are visible but whose identity assignment — the locus of the race — is invisible to the reader.

**Applying it across the aliasing pattern:**

- `self._local.statistics = copy.statistics`: makes `wrapped_f.retry.statistics` work by aliasing the copy's state into the original's thread-local. The original is never the executor; this assignment makes the original appear to have run the call, by adopting the copy's state as its own. This is state impersonation: the original's observable state is a dead copy's state.
- `wrapped_f.statistics = copy.statistics`: resolves the ephemeral copy problem by transferring ownership to the closure, but transfers into a non-thread-local. The transfer solves lifecycle but breaks concurrency.
- The `{}` initialization at `wraps()` time: makes `wrapped_f.statistics` appear to be a stable statistics accumulator before any call. It is not — it is discarded on the first call. The initial `{}` is a placeholder that creates the appearance of a stable attribute and is replaced silently.

---

### Engineering the Improvement

Replace the aliasing with a statistics registry that correctly separates per-thread (correct) from global-latest (documented as lossy):

```python
import threading
from typing import Optional

class StatisticsRegistry:
    """Thread-safe registry for per-call statistics.
    
    thread_stats: statistics for the most recent call on THIS thread.
                  Always correct regardless of concurrent activity.
    latest_stats: statistics for the most recently completed call on ANY thread.
                  Last-write-wins; documented as non-deterministic under concurrency.
    """
    def __init__(self):
        self._local = threading.local()
        self._lock = threading.Lock()
        self._global: dict = {}

    def record(self, stats: dict) -> None:
        self._local.stats = stats
        with self._lock:
            self._global = stats  # Intentionally lossy; see class docstring

    @property
    def thread_stats(self) -> Optional[dict]:
        return getattr(self._local, 'stats', None)

    @property
    def latest_stats(self) -> dict:
        return self._global

    def __getitem__(self, key):
        """Dict-like access; reads from latest_stats for API compatibility."""
        return self._global[key]


class BaseRetrying(ABC):
    def wraps(self, f):
        registry = StatisticsRegistry()

        @functools.wraps(f, functools.WRAPPER_ASSIGNMENTS + ("__defaults__", "__kwdefaults__"))
        def wrapped_f(*args, **kw):
            if not self.enabled:
                return f(*args, **kw)
            copy = self.copy()
            try:
                result = copy(f, *args, **kw)
            finally:
                registry.record(copy.statistics)
            return result

        wrapped_f.retry = self
        wrapped_f.retry_with = lambda *a, **kw: self.copy(*a, **kw).wraps(f)
        wrapped_f.statistics = registry
        return wrapped_f
```

This passes code review because: `StatisticsRegistry` documents the two access semantics explicitly. The lock prevents dict corruption on `_global`. `thread_stats` property provides the correct per-thread value with a legible name. `__getitem__` maintains backward compatibility for `wrapped_f.statistics["attempt_number"]`. The `finally` block ensures statistics are recorded even if the call raises `RetryError`.

It deepens concealment because: `registry.record(copy.statistics)` is called after `copy(f)` returns. During the call — while retries are happening, while callbacks are running — `registry.thread_stats` returns the PREVIOUS call's statistics (or `None` on first call). The improvement eliminated the race by eliminating in-call visibility. Any code that reads `wrapped_f.statistics` during a call (a monitoring hook, a `before_sleep` callback that inspects the function's statistics) now sees stale data. The original's aliasing, despite being racy, provided live statistics through the dict reference because the dict being mutated was the same object held by `wrapped_f.statistics`. The improvement records a snapshot after completion, making the dict change from caller's perspective only at call boundaries.

Additionally: `registry.record(copy.statistics)` records `copy.statistics` — which is `copy._local.statistics`, the dict populated during the call. But this dict is now the `_global` in the registry. If a subsequent call from another thread calls `registry.record(dict2)`, `self._global = dict2` replaces the reference. `dict1` still exists if `registry.thread_stats` on T1 holds it. But `registry.latest_stats` now returns `dict2`. The improvement documents this ("Last-write-wins") rather than eliminating it. The lock prevents corruption but not logical loss. Documenting the behavior as "non-deterministic under concurrency" is progress in honesty but not in correctness.

---

### Three Properties Visible Only Because We Tried to Strengthen

**1. In-call statistics visibility was a structural side effect of aliasing, not a design decision.**

The original's `wrapped_f.statistics = copy.statistics` (executed before the call) made the statistics dict simultaneously: (a) a pre-call empty placeholder, (b) a live call-in-progress view, (c) a post-call historical record. All three were the same dict. A `before_sleep` callback that reads `wrapped_f.statistics["attempt_number"]` during a retry sees the live value because `copy.begin()` has already run and `next_action` has already incremented the count. This is correct behavior that emerges from the aliasing mechanism, not from any design intention. The improvement, by recording only after completion, destroys this. The absence reveals the original had it only accidentally: the aliasing was not implemented to provide in-call visibility, but in-call visibility was an emergent property of the aliasing. The property was invisible because it was never stated.

**2. The statistics dict's identity changes on every call; the dict interface conceals this.**

`wrapped_f.statistics["attempt_number"]` reads from whatever dict `wrapped_f.statistics` currently references. After call 1: `wrapped_f.statistics` is `dict1`. After call 2: `wrapped_f.statistics` is `dict2`. `dict1` is still alive (referenced by T1's thread-local) but unreachable through `wrapped_f.statistics`. Users who store `my_dict = wrapped_f.statistics` and then call the function again are holding a stale dict — `my_dict` still refers to `dict1`, while `wrapped_f.statistics` now refers to `dict2`. The improvement's `StatisticsRegistry` has stable identity (the registry object doesn't change), making `wrapped_f.statistics is wrapped_f.statistics` always True. This reveals that in the original, `wrapped_f.statistics is wrapped_f.statistics` is True only if no concurrent call ran between the two reads — a nondeterministic property. The dict interface made this invisible.

**3. Statistics must be observable after exception, and the aliasing was established before the call to ensure this.**

The original establishes the alias before `copy(f, *args, **kw)`. If the call ultimately raises `RetryError`, `wrapped_f.statistics` still points to the populated dict — `attempt_number` tells you how many attempts occurred before giving up. This is essential diagnostic information. The improvement records in `finally`, which does preserve post-exception stats — this is correct. But the `finally` reveals that the original's pre-call aliasing was not the only way to achieve post-exception visibility; `finally` also works, and more clearly. The original's approach (alias before call) was not selected for clarity — it was selected because it is the only way to make the dict identity visible DURING the call. Pre-call aliasing solves three problems simultaneously (pre-call placeholder, in-call live view, post-call record) through one mechanism. The improvement, which only needs one of the three (post-call record), makes the others visible by their absence.

---

### Applying the Diagnostic to the Improvement

**What does the improvement conceal?**

`registry.record(copy.statistics)` calls `copy.statistics` — accessing the `statistics` property on `copy`. But `copy.statistics` was already accessed during `wrapped_f` setup (to initialize the dict and establish aliasing). In the improvement, no aliasing is established before the call. During the call, `copy.statistics` is the live execution dict: `copy.begin()` populated it, `_run_stop` writes to it, `next_action` increments `attempt_number` in it. After the call, `registry.record(copy.statistics)` records THIS dict. But: `copy.statistics` is `copy._local.statistics` — a thread-local. After `copy` goes out of scope (end of `wrapped_f`), `copy._local` is GC'd. The dict is now referenced by `registry._local.stats` (T's slot) and `registry._global`. Both keep it alive. But the registry holds a reference to a dict that was originally a thread-local on a now-GC'd object. This creates a reference pattern where the dict outlives its owning thread-local by virtue of the registry's references — correct behavior, but invisible: the dict's lifetime is now determined by registry membership, not by the thread-local lifetime, even though the dict IS a thread-local value.

**What property of the original problem is visible only because the improvement recreates it?**

The improvement records `copy.statistics` — a single dict. But `copy.statistics` is populated by actions distributed throughout the action pipeline: `copy.begin()` sets four initial keys, `_run_stop` updates `"delay_since_first_attempt"`, the `next_action` closure updates `"idle_for"` and `"attempt_number"`. These writes are not in one place — they are side effects of pipeline actions that also call user callbacks and schedule further actions. Separating the statistics concern from the action pipeline would require changing all N write sites. The improvement operates at the `wraps()` level — above the pipeline — and records the result, but cannot change what the pipeline wrote or where. The improvement reveals that **statistics are pipeline side effects, not pipeline outputs**: they are written as incidental mutations by stages whose primary purpose is to run callbacks, schedule actions, and signal the stop/retry decision. The statistics concern is not a separate concern from the action pipeline — it is woven into it. This is the same structural fact that L10 found for inter-stage signaling: both are encoded as `self`-mutations distributed across pipeline stages.

---

### Engineering the Second Improvement

The recreated property: statistics writes are distributed as side effects throughout action closures. The second improvement makes statistics writes explicit by extracting them from pipeline closures into a statistics-aware pipeline stage:

```python
@dataclasses.dataclass
class StatsDelta:
    """Statistics changes produced by one pipeline stage. Aggregated at pipeline exit."""
    attempt_number_delta: int = 0
    idle_for_delta: float = 0.0
    delay_since_first_attempt: Optional[float] = None  # Override, not delta


@dataclasses.dataclass  
class PipelineResult:
    action: object           # DoAttempt, DoSleep, or the return value
    stats_delta: StatsDelta  # What this stage's execution cost


class BaseRetrying(ABC):
    def _run_stop_pure(self, retry_state: "RetryCallState") -> tuple[bool, StatsDelta]:
        """Returns stop decision and statistics delta, without writing to self.statistics."""
        delay = retry_state.seconds_since_start
        stop_result = self.stop(retry_state)
        return stop_result, StatsDelta(delay_since_first_attempt=delay)

    def _next_action_pure(self, sleep: float) -> tuple[RetryAction, StatsDelta]:
        """Returns next action and statistics delta, without writing to self.statistics."""
        return (
            RetryAction(sleep),
            StatsDelta(
                idle_for_delta=sleep,
                attempt_number_delta=1,
            )
        )

    def _apply_stats_delta(self, delta: StatsDelta) -> None:
        """Single write point for all statistics updates."""
        if delta.attempt_number_delta:
            self.statistics["attempt_number"] += delta.attempt_number_delta
        if delta.idle_for_delta:
            self.statistics["idle_for"] += delta.idle_for_delta
            self.statistics["delay_since_first_attempt"] = (
                self.statistics.get("delay_since_first_attempt", 0) + delta.idle_for_delta
            )
        if delta.delay_since_first_attempt is not None:
            self.statistics["delay_since_first_attempt"] = delta.delay_since_first_attempt
```

This passes code review because: `StatsDelta` makes statistics updates explicit values rather than implicit side effects. `_run_stop_pure` returns the delta instead of writing to `self.statistics`. A single `_apply_stats_delta` method is the only write site. The pipeline stages become pure functions of their inputs.

**Applying the diagnostic to the second improvement:**

`_apply_stats_delta` is the single write point. But it writes to `self.statistics` — the thread-local dict. The improvement eliminated distributed write sites but preserved the shared mutable medium. Now: `_apply_stats_delta` is called from within pipeline actions. Those actions are closures in the action list. They close over `self`. So: the action closure calls `self._apply_stats_delta(delta)`, which writes to `self.statistics`. The statistics write is now centralized (one write point) but the statistics object is still the thread-local dict on `self` — the same medium, now written through a single method rather than multiple direct accesses. The structural form is unchanged.

More precisely: `_run_stop_pure` returns a `StatsDelta`. Something must call `_run_stop_pure`, receive the delta, and pass it to `_apply_stats_delta`. The action pipeline's current structure returns `None` from all actions and communicates through IterState fields. To use `StatsDelta`, either: the action list stores `(action, post_action)` pairs (doubling the mechanism), or actions return `StatsDelta` (making the loop no longer able to store the last result as `result`), or `StatsDelta` is communicated through — another IterState field. The second improvement recreates the original communication problem at the statistics level: how does the statistics delta produced by one pipeline stage reach the statistics accumulator? Through shared state — a new IterState field, or a new `ctx` attribute. The pipeline's loop-result-discarding property (L10's finding) affects statistics as much as it affects retry decisions.

---

### The Structural Invariant

Through every improvement — statistics registry with thread-local, lock-protected global, `RetryExecutionContext` separation of live state from historical record, `StatsDelta` extraction of write sites from pipeline closures — one property persists:

**Any value computed inside the pipeline (retry decision, stop decision, statistics delta) that must be observable outside the pipeline — whether outside the action loop (to the control loop's `return do`), outside the call (to `wrapped_f.statistics`), or outside the copy's lifetime (across GC boundaries) — must cross a scope boundary. Every scope boundary in this architecture is crossed through shared mutable state: IterState fields for intra-pipeline communication, thread-local aliasing for intra-call-to-persistent-handle communication. The medium changes (fields, dicts, thread-locals, closure captures) but the structure is constant: a value is computed in an inner scope, a shared mutable pointer in an outer scope is updated to reference it, and the outer scope reads through the pointer. No improvement eliminates a shared mutable pointer; each improvement relocates or refactors one.**

The invariant is not about IterState, nor about thread-locals, nor about closures. It is: **scope-crossing value propagation requires a shared mutable reference, and the reference's lifetime and thread-affinity constraints propagate from the value's scope to the reference's semantics — constraints that are invisible at the reference's declaration site**.

---

### The Category Defined by the Invariant

This invariant defines the category of **shared-context architectures**: designs where cross-boundary values flow through named slots in shared objects (`self.statistics["attempt_number"]`, `self.iter_state.retry_run_result`, `retry_state.upcoming_sleep`). Members of this category share:
- Cross-boundary values have no type at the boundary — they are dict entries, object attributes, or thread-local slots
- The dependency between writer and reader is expressed only by convention (field naming, method ordering, documentation)
- The shared object's lifetime must span both writer and reader scopes, creating lifetime coupling
- Concurrency affects the reference but the reference has no concurrency semantics — it is just a Python attribute or dict key

---

### The Adjacent Category: Call Graphs With Explicit Effect Types

In the adjacent category, the invariant dissolves: **cross-boundary values are carried in explicit typed return values, not written to shared objects**. Every scope boundary has a typed signature. No value crosses a boundary without appearing in a type.

The design:

```python
from typing import TypeVar, Generic, NamedTuple, Union

T = TypeVar('T')

class RetryEffect(NamedTuple):
    """The side-effecting output of a retry decision stage."""
    sleep: float
    attempt_delta: int
    delay_snapshot: float

class RetryDecision(NamedTuple):
    should_retry: bool
    is_explicit: bool

class StopDecision(NamedTuple):
    should_stop: bool

class RetryEvaluation(NamedTuple):
    """Complete output of one retry cycle evaluation."""
    retry: RetryDecision
    wait: RetryEffect
    stop: StopDecision

class RetryOutcome(NamedTuple, Generic[T]):
    """The fully-typed result of a single iter() call."""
    action: Union['DoAttempt', 'DoSleep', T, None]  
    evaluation: Optional['RetryEvaluation']  # Present if a retry cycle ran
    statistics_snapshot: dict  # Immutable snapshot, not a shared dict


class ExplicitRetrying(BaseRetrying):
    def iter(self, retry_state: 'RetryCallState') -> 'RetryOutcome':
        fut = retry_state.outcome
        if fut is None:
            if self.before:
                self.before(retry_state)
            return RetryOutcome(action=DoAttempt(), evaluation=None, 
                                statistics_snapshot=dict(self.statistics))

        is_explicit = fut.failed and isinstance(fut.exception(), TryAgain)
        should_retry = True if is_explicit else bool(self.retry(retry_state))

        if not should_retry:
            return RetryOutcome(action=fut.result(), evaluation=None,
                                statistics_snapshot=dict(self.statistics))

        sleep = self.wait(retry_state) if self.wait else 0.0
        delay = retry_state.seconds_since_start
        should_stop = bool(self.stop(retry_state))

        evaluation = RetryEvaluation(
            retry=RetryDecision(should_retry=True, is_explicit=is_explicit),
            wait=RetryEffect(sleep=sleep, attempt_delta=1, delay_snapshot=delay),
            stop=StopDecision(should_stop=should_stop),
        )

        if should_stop:
            if self.retry_error_callback:
                return RetryOutcome(action=self.retry_error_callback(retry_state),
                                    evaluation=evaluation,
                                    statistics_snapshot=dict(self.statistics))
            retry_exc = self.retry_error_cls(fut)
            if self.reraise:
                retry_exc.reraise()
            raise retry_exc from fut.exception()

        # Apply effects here — single site
        self.statistics['idle_for'] += sleep
        self.statistics['attempt_number'] += 1
        self.statistics['delay_since_first_attempt'] = delay
        retry_state.upcoming_sleep = sleep
        retry_state.next_action = RetryAction(sleep)
        retry_state.idle_for += sleep

        if self.after:
            self.after(retry_state)

        return RetryOutcome(action=DoSleep(sleep), evaluation=evaluation,
                            statistics_snapshot=dict(self.statistics))
```

**How this succeeds where every improvement failed:**

Every cross-boundary value is explicit in the return type: `evaluation.retry.should_retry`, `evaluation.wait.sleep`, `evaluation.stop.should_stop`. No shared IterState fields. No read-after-write ordering dependencies — the function is called once and returns all decisions simultaneously. Statistics are returned as an immutable snapshot in `statistics_snapshot`, not as a shared dict handle that changes identity on the next call. Each `iter()` call returns its complete output; the control loop doesn't need to inspect IterState to understand what happened. The inter-stage dependency (`stop` is only evaluated if `retry` is needed) is expressed as Python control flow (`if not should_retry: return ...`), not as conditional list appending. The concealment mechanisms — ordering as invisible contract, aliased dict as statistics surface, distributed write sites — are eliminated because there is one call and one return value, not a sequence of action closures communicating through shared slots.

---

### The New Impossibility

In the original category, what is trivial: dynamically extending the action sequence based on runtime conditions. `_post_retry_check_actions` decides at runtime whether to add wait/stop stages. The action list grows based on what `_run_retry` found. Adding a new conditional stage — "if retry_count mod 10 == 0, run extra logging" — requires appending one action in one conditional. The dynamic extension is a first-class mechanism.

In the adjacent category, this is impossible without restructuring the return type. The `iter()` function in `ExplicitRetrying` is a sequential function: it evaluates retry, then (conditionally) wait, then stop. Adding "if retry_count mod 10 == 0, run periodic health check, and if health check fails, fail fast" requires: either a new branch in the function body (fine for known extensions), or a hook point in the type (adding an optional `PeriodicEffect` to `RetryEvaluation`), or a runtime-configurable pipeline — which re-introduces the dynamic action list, collapsing back into the original category. The explicit-type design is closed: the return type enumerates what `iter()` can produce, and every new protocol extension requires changing the type.

The adjacent category also cannot express the continuation pattern at all: `DoAttempt` and `DoSleep` are returned to the control loop as instructions. In `ExplicitRetrying`, `DoSleep(sleep)` is returned in `RetryOutcome.action`. The control loop must inspect `outcome.action` and dispatch. This is the same dispatch — `isinstance(do, DoAttempt)` — now operating on a typed wrapper rather than on `iter()`'s raw return value. The protocol tokens have not been eliminated; they have been wrapped. The wrapper makes them appear in the type, but the dispatch is identical in structure.

---

### The Trade-Off: The Finding

The trade-off between the two impossibilities is not symmetric.

**The old impossibility — concurrent statistics attribution** — is correctness-critical. Users who call `@retry`-decorated functions from thread pools and inspect `wrapped_f.statistics` get nondeterministic data with no indication of the nondeterminism. The failure is silent, the symptom is confusing (statistics look correct but reflect one arbitrary call among many), and the diagnosis requires understanding the aliasing mechanism that is entirely absent from the public interface. The impossibility is invisible.

**The new impossibility — open protocol extension** — is ergonomics-costly. Adding a new conditional stage in `ExplicitRetrying` requires changing the function body or the return type. This is visible work: the type system will fail to compile if the return type is incomplete, the control loop will fail to dispatch if a new action type is unhandled. The failure is loud. The extension cost is proportional and predictable.

The original architecture chose the worse trade: it made the correctness failure invisible and the extension cost negligible. The adjacent architecture inverts this: it makes the correctness guarantee structural (types enforce it) and the extension cost proportional (types require it).

The finding is not that tenacity made the wrong choice. It is that the choice was made invisibly. The action-list pipeline and the aliased statistics surface do not appear to be a design choice — they appear to be implementation details. The type-safety properties they sacrifice and the extension flexibility they provide are not stated anywhere in the code. The trade-off is present in the architecture and absent from its documentation. The concealment mechanism is not just aliasing-as-correctness-performance in `wraps()` — it is the entire architecture performing as if its trade-offs are implementation details rather than design decisions. **The deepest structural problem is that the architecture has taken a position on the correctness–extensibility trade-off without recording that it has taken a position.** Future implementers who encounter the statistics race or the ordering dependency will see a bug to fix, not a trade-off to renegotiate.
