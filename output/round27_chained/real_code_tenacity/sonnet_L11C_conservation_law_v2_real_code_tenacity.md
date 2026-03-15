## Structure First: Level 11 Diagnostic

---

### Falsifiable Claim

During every `before_sleep` execution after the first failed attempt, `self.statistics["attempt_number"]` equals N+1 while `retry_state.attempt_number` equals N — where N is the number of the attempt that just failed. The divergence has a precise cause: `statistics["attempt_number"] += 1` lives inside the `next_action` closure in `_post_stop_check_actions`, which executes as a pipeline action before `before_sleep` is appended and called. `retry_state.attempt_number += 1` lives in `prepare_for_next_attempt()`, called by the caller loop after `iter()` returns `DoSleep`. The `before_sleep` window is the exact gap between these two increments.

No type annotation, assertion, or comment marks this divergence. A `before_sleep` hook reading `retry_state.attempt_number` sees N. The same hook reading `self.statistics["attempt_number"]` sees N+1. Both values are defensible interpretations of "attempt number." Outside the `before_sleep` window — before `begin()`, after `prepare_for_next_attempt()` returns, at the top of every `iter()` call — the two values are equal, so any inspection outside this window concludes they are interchangeable.

**Falsifiable test:** register `before_sleep=lambda rs: assert rs.retry_object.statistics["attempt_number"] == rs.attempt_number`. This assertion fails on every retry, precisely and permanently.

---

### The Dialectic

**Expert 1 — Defender**

The divergence is a real misuse hazard. The natural way to log retry progress in `before_sleep` is:

```python
def log_sleep(retry_state):
    n = retry_state.retry_object.statistics["attempt_number"]
    logger.info(f"Attempt {n} failed. Sleeping before retry.")
```

This logs "Attempt 2 failed" for the first failure — one ahead. `statistics` is the public monitoring API; users expect it to reflect "what happened," not "what's coming." The divergence between the public statistics API and the internal retry_state produces systematically wrong output with no observable error.

**Expert 2 — Attacker**

Both readings are correct for different questions. `retry_state.attempt_number = N` answers "which attempt just ran?" `statistics["attempt_number"] = N+1` answers "which attempt are we about to run?" `before_sleep` is semantically positioned before the next attempt — so N+1 is arguably the right value for its context. The hook has simultaneous access to both perspectives: the pre-transition view through `retry_state` and the post-transition view through `statistics`. This dual access is more informative than either alone.

**Expert 3 — Prober**

Expert 2 says `statistics["attempt_number"] = N+1` is "the attempt we're about to run." Expert 1 says it's "off by one." Both experts debate what `statistics["attempt_number"]` *means* at this point. The Prober's question is different: **why does `statistics["attempt_number"] += 1` appear inside the `next_action` closure at all?**

`next_action` also writes `rs.idle_for += sleep`, `self.statistics["idle_for"] += sleep`, and `rs.next_action = RetryAction(sleep)`. These are pipeline-coordination writes — they set up the state that enables the upcoming sleep and the next iteration. The `statistics["attempt_number"]` increment is not coordination: it updates an external monitoring dict. It is in `next_action` not because its timing was deliberately chosen to give `before_sleep` a specific view, but because `next_action` is the action that handles the transition to the next retry, and the statistics update was written there as part of that transition handling.

The divergence is not an intentional dual-view provision. It is an unintentional consequence of co-locating a monitoring write with coordination writes. Expert 2's "semantic plurality" claim attributes design intent to an implementation coincidence.

---

### The Transformation

| | |
|---|---|
| **Initial claim** | `statistics["attempt_number"]` and `retry_state.attempt_number` diverge during `before_sleep`, creating a misuse hazard |
| **Transformed claim** | The `next_action` closure performs two conceptually distinct operations: pipeline-coordination writes (setting `idle_for`, `next_action`, `upcoming_sleep` downstream) and monitoring writes (updating `statistics["attempt_number"]`, `statistics["idle_for"]`). These are bundled in one closure with no distinction. The monitoring write's position — after stop/wait evaluation, before `before_sleep` — is determined by the closure's coordination role, not by a decision about what the monitoring system should expose. `before_sleep`'s information content is therefore determined by where coordination writes happen to occur, not by a designed hook-observability contract. The divergence is a symptom of the pipeline having no separation between "coordination output" and "monitoring publication." |

The initial claim identifies an inconsistency. The transformed claim identifies its cause: monitoring and coordination are structurally identical in this codebase — both are side effects of pipeline actions, written through `self` and `rs`, with no type distinction between them. When a pipeline action does both, its position in the pipeline determines both its coordination effect and its monitoring effect simultaneously. Hook observers receive whatever monitoring state happens to be current at their execution point, determined by coordination ordering.

---

### The Gap Is Itself Diagnostic

L10 analyzed what pipeline stages communicate to *each other* through IterState fields. L10's structural invariant is about how the pipeline schedules its own continuation.

The gap: L10 did not ask what pipeline stages communicate to *hooks*. `before_sleep` is not a pipeline stage — it is an observer that executes inside the pipeline. The `next_action` closure publishes monitoring state (`statistics["attempt_number"]`) that `before_sleep` reads, but this publication is not visible as communication — it looks like bookkeeping. L10 found that IterState fields are the only inter-stage communication channel because the loop discards return values. I'm finding that statistics fields (written by pipeline actions) are simultaneously the hook-observation channel, and the coordination ordering that governs stage communication also governs hook observability — without this being represented anywhere in the code.

The gap: L10 analyzed what stages read from each other. Neither L10 nor any prior level asked what hooks read from the pipeline, or how pipeline-internal ordering determines what hooks can observe.

---

### The Concealment Mechanism: Identical Naming at Different Temporal Scopes

`statistics["attempt_number"]` and `retry_state.attempt_number` share the string `"attempt_number"` as their identifier. They appear to be the same value accessed through two paths. The naming convention says: "these are the same thing." During `before_sleep`, they are not.

The concealment is reinforced by convergence: outside the `before_sleep` window, both values are equal. After `begin()`, both are 1. After `prepare_for_next_attempt()`, both are N+1. At the top of every `iter()` call, both are N. A developer inspecting either in any context other than `before_sleep` concludes they are interchangeable — and this conclusion is correct for every context they can easily test.

**Application:** `statistics["idle_for"]` and `retry_state.idle_for` are also both updated in `next_action` — but they are updated identically (same increment, same closure), so they stay synchronized throughout. The `idle_for` pair has no convergence/divergence pattern; it is always equal. This uniformity makes the `attempt_number` divergence harder to notice: it appears to be a coincidence of the `idle_for` pair, not a structural feature of two counters with different increment points.

The concealment is complete: the field that diverges has the same name in both objects, diverges only in one execution window (`before_sleep`), and appears equal in all easily inspected contexts.

---

### Engineering the Improvement

Move `statistics["attempt_number"] += 1` from the `next_action` closure to `prepare_for_next_attempt()`, unifying both increments at the caller level:

```python
# RetryCallState — unified attempt-number transition
def prepare_for_next_attempt(self):
    self.outcome = None
    self.outcome_timestamp = None
    self.attempt_number += 1
    self.next_action = None
    # Unified increment: statistics["attempt_number"] now always equals attempt_number
    self.retry_object.statistics["attempt_number"] = self.attempt_number


# BaseRetrying._post_stop_check_actions — coordination-only next_action
def _post_stop_check_actions(self, retry_state):
    if self.iter_state.stop_run_result:
        # ... stop path unchanged ...
        return

    def next_action(rs):
        sleep = rs.upcoming_sleep
        rs.next_action = RetryAction(sleep)
        rs.idle_for += sleep
        self.statistics["idle_for"] += sleep
        # statistics["attempt_number"] increment removed: now in prepare_for_next_attempt

    self._add_action_func(next_action)
    if self.before_sleep is not None:
        self._add_action_func(self.before_sleep)
    self._add_action_func(lambda rs: DoSleep(rs.upcoming_sleep))
```

This passes code review because: `prepare_for_next_attempt()` is the natural site for attempt-transition bookkeeping; a single increment point eliminates the divergence; `next_action` is simplified to pure coordination; the change is small and self-contained; the dual-counter assertion failure from the falsifiable test now passes.

It deepens concealment because: during `before_sleep`, both counters now equal N. The hook has a "consistent" view — but the N+1 information is silently gone. A `before_sleep` hook that was using `statistics["attempt_number"]` to observe the upcoming attempt number now sees the completed attempt number; no test fails, no exception is raised, no code review signal warns of this semantic change. The `statistics` dict now contains one field (`idle_for`) updated before `before_sleep` and one field (`attempt_number`) updated after — a heterogeneous update-timing structure hidden inside a flat dict where all fields are accessed identically. And `prepare_for_next_attempt()` now writes to `self.retry_object.statistics` — a cross-object dependency from `RetryCallState` into `BaseRetrying`, reversing a coupling direction that was previously unidirectional and invisible in the type signatures.

---

### Three Properties Visible Only Because We Tried to Strengthen

**1. `statistics["idle_for"]` must remain in the pipeline and cannot be unified.**

The improvement removes `statistics["attempt_number"] += 1` from `next_action` but cannot remove `self.statistics["idle_for"] += sleep` without breaking `before_sleep` observability. If `idle_for` were moved to `prepare_for_next_attempt()`, `before_sleep` would see the cumulative sleep time *excluding* the upcoming sleep — which defeats the purpose of a hook that exists to observe "what is about to happen." `idle_for` must be updated in the pipeline, before `before_sleep` runs, precisely because `before_sleep` is designed to observe it. This reveals: the `next_action` closure is not an arbitrary collection of updates; it is specifically the action whose writes are meant to be observable by `before_sleep`. Removing `statistics["attempt_number"]` from this closure while leaving `statistics["idle_for"]` exposes that each field has an independent hook-observability contract determining its position. The unification attempt reveals this per-field constraint invisibly present in the original.

**2. `before_sleep` silently loses the N+1 view of attempt count.**

After the improvement, `before_sleep` cannot directly observe "which attempt number comes next" — both `statistics["attempt_number"]` and `retry_state.attempt_number` equal N. A hook wanting to log "sleeping before attempt N+1" must compute `retry_state.attempt_number + 1`. This computation is trivial, but the information that N+1 is the right value for this purpose was previously encoded in `statistics["attempt_number"]`'s value at the hook site. It is now absent. No API break, no test failure, no exception. The information degradation is silent because the hook receives the same objects (`retry_state`, `statistics`) with the same types — only the values changed. The improvement reveals that `statistics["attempt_number"] = N+1` during `before_sleep` was not a synchronization bug but a deliberate (if undocumented) provision of the post-transition view at the hook site.

**3. `prepare_for_next_attempt()` acquires a cross-object dependency and mixed concerns.**

Originally, `prepare_for_next_attempt()` was self-contained: every write was to `self` (a `RetryCallState` field). After the improvement, it writes to `self.retry_object.statistics` — a field on a different object of a different type. The method's purpose was "prepare state for next attempt" (state transition); it now also "records what occurred" (monitoring). These are distinct concerns coexisting in one method, coupled by the implementation choice. In the original, this coupling was invisible: the monitoring write was in a `BaseRetrying` method closure that accessed `self` (the `BaseRetrying` instance), making the coupling look like a method naturally accessing its own state. The improvement makes the coupling visible: `RetryCallState` explicitly reaching into `BaseRetrying`. The cross-object coupling existed before; moving the write makes it legible as coupling.

---

### Applying the Diagnostic to the Improvement

**What does the improvement conceal?**

The improvement conceals that `statistics["idle_for"]` has the same temporal-scope problem as `statistics["attempt_number"]` had before the fix. After the change, `statistics` contains fields updated at two distinct temporal positions: `idle_for` in the pipeline (pre-`before_sleep`) and `attempt_number` in the caller (post-`before_sleep`). The `statistics` dict presents all fields identically — a flat `{}` with no temporal metadata. A developer reading `statistics["idle_for"]` and `statistics["attempt_number"]` after a failed attempt cannot determine that one was written before `before_sleep` ran and the other after. The improvement eliminated one form of dual-position updating while creating a different, less visible form.

**What property of the original problem is visible only because the improvement recreates it?**

The original code updated `statistics["attempt_number"]` and `statistics["idle_for"]` in the same closure (`next_action`), giving both identical temporal scope. The improvement moves `attempt_number` out, leaving `idle_for` alone in the pipeline. The isolation reveals: **each statistics field's position in the pipeline is independently constrained by which hook observes it and what value that hook needs.** `idle_for` is in the pipeline because `before_sleep` must see the cumulative sleep including the upcoming sleep. `attempt_number` was in the pipeline for the analogous reason (providing N+1 to `before_sleep`). Moving one exposes that the other's position is not arbitrary. The original concealed this by making all statistics updates look like a single accounting operation; the improvement exposes that they are individually constrained observations.

---

### Engineering the Second Improvement

The recreated property: statistics fields have heterogeneous temporal positions because each has an independent hook-observability requirement, and `statistics` as a flat dict does not represent these distinctions. The second improvement addresses this by moving `before_sleep` execution out of the pipeline entirely — into the caller loop, after `prepare_for_next_attempt()`, where both counters are synchronized:

```python
# BaseRetrying._post_stop_check_actions:
# Remove: if self.before_sleep is not None: self._add_action_func(self.before_sleep)
# Pipeline now terminates at DoSleep with no hooks between next_action and DoSleep:
def _post_stop_check_actions(self, retry_state):
    if self.iter_state.stop_run_result:
        # ... stop path unchanged ...
        return

    def next_action(rs):
        sleep = rs.upcoming_sleep
        rs.next_action = RetryAction(sleep)
        rs.idle_for += sleep
        self.statistics["idle_for"] += sleep

    self._add_action_func(next_action)
    # before_sleep removed from pipeline
    self._add_action_func(lambda rs: DoSleep(rs.upcoming_sleep))


# Retrying.__call__ and BaseRetrying.__iter__:
elif isinstance(do, DoSleep):
    retry_state.prepare_for_next_attempt()  # attempt_number = N+1, outcome = None
    if self.before_sleep is not None:
        self.before_sleep(retry_state)       # Both counters = N+1; no divergence
    self.sleep(do)
```

This passes code review because: caller loops are the natural place to invoke side-effectful hooks (before, after, before_sleep all conceptually belong to the retry session, not the pipeline); the pipeline is now purely decisional; both counters are synchronized when `before_sleep` runs; the statistics dict is now entirely consistent during `before_sleep` (all updates have occurred: `prepare_for_next_attempt` ran first).

**Applying the diagnostic to the second improvement:**

What it conceals: `before_sleep` now executes after `prepare_for_next_attempt()`, which sets `retry_state.outcome = None`. The hook can no longer access the failure that triggered the retry — `rs.outcome` is `None`. A `before_sleep` hook reading `rs.outcome.exception()` to log the retry reason now receives a `NoneType` error, silently, with no change to the method signature (`before_sleep` still receives `retry_state`, still has `.outcome` as an attribute — it's just None). The information available to the hook has changed structurally while the API has not.

What property of the original problem is visible because the improvement recreates it: the original placed `before_sleep` in the pipeline because both the failure context (`retry_state.outcome`) and the sleep duration (`retry_state.upcoming_sleep`) are available there. Moving `before_sleep` out of the pipeline preserves access to the sleep duration (carried in `do`, the `DoSleep` value) but destroys access to the failure context. The improvement recreates the finding: **`before_sleep`'s full information content — failure cause, sleep duration, upcoming attempt number — is only simultaneously available in the window between "sleep duration computed" and "`prepare_for_next_attempt()` called." This window is not an implementation convenience; it is the only temporal position where all three pieces of information coexist. Any improvement that moves `before_sleep` outside this window loses at least one piece.**

---

### The Structural Invariant

Through every improvement — unifying increment points, making update policies explicit, relocating `before_sleep` to the caller — one property persists without change:

**`before_sleep` requires simultaneous access to three pieces of information: (1) the failure context from attempt N (`retry_state.outcome`), destroyed by `prepare_for_next_attempt()`; (2) the computed sleep duration, available from `retry_state.upcoming_sleep` after `_run_wait`; (3) the upcoming attempt number N+1, not yet present in `retry_state.attempt_number` until `prepare_for_next_attempt()` runs. These three requirements create exactly one temporal window where all three coexist: after `_run_wait` has written `upcoming_sleep`, before `prepare_for_next_attempt()` clears `outcome`. This window is fixed by the computation's information structure, not by architectural choices. The pipeline's `next_action` closure marks the entry into this window; `DoSleep` marks its exit. `before_sleep` in the original code executes in this window because that is the only place all three are available. Every improvement that changes what `before_sleep` sees does so by moving it out of this window — gaining consistency on one dimension while losing information on another.**

The invariant is not about counters, statistics, or any specific field. It is: **`before_sleep`'s maximal information content is determined by a temporal window defined by information availability, not by architecture. No architectural change can move this window without also changing what information is available at the hook site.**

---

### Inverting the Invariant

The invariant says `before_sleep` must execute in the transition interior to have maximum information. The inversion: eliminate the need for a transition-interior hook by replacing `before_sleep` with two hooks at state boundaries:

```python
class BaseRetrying(ABC):
    def __init__(self, ...,
                 after_attempt_failed=None,   # Called post-failure; outcome=N, attempt_number=N
                 before_attempt=None,         # Called pre-attempt; outcome=None, attempt_number=N+1
                 ...):
        self.after_attempt_failed = after_attempt_failed
        self.before_attempt = before_attempt
        # before_sleep removed


# _post_stop_check_actions (no-stop path):
def next_action(rs):
    sleep = rs.upcoming_sleep
    rs.next_action = RetryAction(sleep)
    rs.idle_for += sleep
    self.statistics["idle_for"] += sleep
    self.statistics["attempt_number"] += 1

self._add_action_func(next_action)
if self.after_attempt_failed is not None:
    # State: outcome = failure, attempt_number = N, sleep duration known
    self._add_action_func(self.after_attempt_failed)
self._add_action_func(lambda rs: DoSleep(rs.upcoming_sleep))


# Caller loops:
elif isinstance(do, DoSleep):
    retry_state.prepare_for_next_attempt()  # outcome=None, attempt_number=N+1
    self.sleep(do)


# _begin_iter (non-first attempts):
if self.before_attempt is not None:
    # State: outcome=None, attempt_number=N+1
    self._add_action_func(self.before_attempt)
self._add_action_func(lambda rs: DoAttempt())
```

`after_attempt_failed` has unambiguous semantics: attempt_number = N, the failure is in `outcome`, sleep duration is in `upcoming_sleep`. `before_attempt` has unambiguous semantics: attempt_number = N+1, outcome is None, the attempt is about to start. No dual-counter, no mid-transition state, no positional convention.

---

### The New Impossibility the Inversion Creates

A user wanting to log: **"Attempt N failed with exception X. Sleeping D seconds. Will retry as attempt N+1."**

requires:
- Exception X → `retry_state.outcome.exception()` → available to `after_attempt_failed` (outcome present)
- Sleep duration D → `retry_state.upcoming_sleep` → available to `after_attempt_failed`
- Upcoming attempt N+1 → `retry_state.attempt_number` → available to `before_attempt` (after `prepare_for_next_attempt()`), but by then `retry_state.outcome` is None and `retry_state.upcoming_sleep` is stale

No single hook in the inverted design has all three simultaneously. `after_attempt_failed` has X, D, and N — can compute N+1 as N+1. `before_attempt` has N+1 — but not X (outcome cleared) and not D (upcoming_sleep carries the previous iteration's value or 0.0 after a hypothetical reset). A user needing all three must maintain state between hooks: save X and D from `after_attempt_failed`, use them in `before_attempt`. This cross-hook state is the user's implementation of exactly what the library's transition-interior position was providing.

The new impossibility: **no single boundary hook can simultaneously observe the failure cause (pre-transition), the sleep duration (transition artifact), and the upcoming attempt number (post-transition). These three coexist only at the transition interior. The inversion's semantic clarity comes at the direct cost of cross-transition information availability: every user who needs all three must reimplement cross-hook correlation in userspace.**

---

### The Conservation Law

**Original impossibility:** One hook at the transition interior (`before_sleep`) observes N from `retry_state` and N+1 from `statistics` simultaneously. The attempt count is semantically ambiguous — two valid readings, no canonical one. Maximum cross-transition information, semantic ambiguity of transitioning quantities, cost borne by the library.

**Inverted impossibility:** Two hooks at state boundaries, each with unambiguous attempt count. No transitional state, no dual readings. But no single hook has the full cross-transition information set — failure cause, sleep duration, and upcoming attempt number are distributed across hooks. Cost borne by users who need cross-transition correlation.

**The conservation law:** In a retry system, cross-transition information availability at a single callback and semantic unambiguity of transitioning quantities at that callback are inversely related, with their product conserved across all hook-placement architectures. A callback at a state transition receives maximum information about both adjacent states; any quantity in transition is ambiguous (two readings, both valid). Callbacks at state boundaries receive unambiguous readings; cross-transition information is distributed across multiple callbacks, recoverable only through user-side accumulation. Every design choice determines *where* the cost is borne — inside the library (ambiguous hook semantics) or in user code (cross-callback correlation) — but not whether it is paid.

---

### What a Senior Engineer Would Not Already Know

The senior engineer knows: "hooks near state transitions see partially updated state." This is a recognized hazard.

What they do not know: **`statistics["attempt_number"] += 1` in the `next_action` closure is load-bearing for `before_sleep`'s information content.** It is not in the pipeline for bookkeeping convenience — it is in the pipeline because that is the only position where `before_sleep` can observe the post-transition attempt number (N+1) while the pre-transition failure context (`retry_state.outcome`) is still intact. Moving it to `prepare_for_next_attempt()` — a change that passes code review, produces no test failures, and appears strictly simpler — silently eliminates `before_sleep`'s direct N+1 view. The semantic degradation is invisible: the hook still receives `retry_state` and `statistics`, still has access to `attempt_number` through both paths, but both now say N instead of N and N+1.

The load-bearing quality of this increment's position is not documented anywhere in the code. A developer who moves it as a refactor makes a change that is locally correct, globally harmful, and undetectable until a `before_sleep` hook that was using `statistics["attempt_number"]` to observe the upcoming attempt starts logging the wrong value.

---

### What It Predicts About a Third Design

A third design introduces `BeforeSleepContext`:

```python
@dataclass
class BeforeSleepContext:
    failed_attempt: int        # = retry_state.attempt_number (pre-transition)
    next_attempt: int          # = retry_state.attempt_number + 1
    sleep_seconds: float       # = retry_state.upcoming_sleep
    last_outcome: Future       # = retry_state.outcome
```

This eliminates the dual-counter ambiguity: both views are named fields. It passes all tests, passes code review, and makes the cross-transition information explicit and unambiguous.

The conservation law predicts: `next_attempt = failed_attempt + 1` hardcodes that each retry cycle involves exactly one attempt increment — that is, the transition count per cycle is always 1. This is currently true because every failed attempt leads to exactly one sleep, which leads to exactly one subsequent attempt. If the system were extended to support "fast retry" (multiple attempts before sleeping) or "conditional skip" (advancing attempt count by more than 1 under certain conditions), `next_attempt = failed_attempt + 1` would be wrong: it should be `failed_attempt + K` where K is the per-cycle transition count.

The third design conceals K=1 as an unnamed structural constant inside the `BeforeSleepContext` constructor, precisely as the original code concealed it as the `+= 1` in `next_action`. The conservation law's finding is this: **every representation of cross-transition information in a retry system must encode the transition structure — how much the attempt count advances per cycle. When this structure is fixed (K=1), it is always tempting to hardcode it, and every design that correctly exposes cross-transition information will conceal K at whatever abstraction level the representation occupies.** The third design moves the concealment from a visible pipeline action (`statistics["attempt_number"] += 1`) to a hidden constructor assumption (`next = failed + 1`). The problem is not eliminated — it is concealed one level deeper, in a location where it will be even harder to find when a future "fast retry" extension violates the K=1 invariant.
