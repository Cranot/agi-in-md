## Structure First: Level 7 Diagnostic

---

### Original Falsifiable Claim

> **The code's deepest structural problem is that `iter_state.actions` is mutated by the functions currently being executed during the same `iter()` loop — making this a self-modifying execution model where complete control flow cannot be determined by reading the code.**

Proof by tracing:

```python
def iter(self, retry_state):
    self._begin_iter(retry_state)          # populates actions: [_run_retry, _post_retry_check_actions]
    for action in self.iter_state.actions: # iterates a growing list
        result = action(retry_state)       # action appends MORE items to the same list
    return result
```

`_post_retry_check_actions` calls `self._add_action_func(...)` which appends to `self.iter_state.actions` — the list Python's `for` loop is currently traversing by index. The loop grows its own queue at runtime. A 2-item list becomes 6–8 items by the time `iter()` returns. You cannot determine what executes without running the code.

---

### The Dialectic

**Expert 1 — Defender**

The claim stands. The continuation-injection is demonstrable and bounded only by the depth of the conditional chain (`_begin_iter` → `_post_retry_check_actions` → `_post_stop_check_actions`). Each layer's branching is invisible without runtime state. The only documentation of this behavior is the behavior itself. For a library whose entire purpose is predictable failure recovery, this is a genuine structural contradiction: the recovery mechanism is itself unreadable.

**Expert 2 — Attacker**

The original claim misidentifies a deliberate design pattern as a flaw. This *is* trampoline-style deferred execution — flat call stack, composable strategies. The self-modification is bounded and intentional. Attack the original claim and replace it with a more precise one:

The *actual* deepest problem is **bifurcated attempt state** — `RetryCallState.attempt_number` and `statistics["attempt_number"]` are two representations of the same fact, updated at different points in the same loop:

- `statistics["attempt_number"]` increments inside `_post_stop_check_actions`'s `next_action` lambda
- `RetryCallState.attempt_number` increments inside `prepare_for_next_attempt()` in `__iter__`/`__call__`

Between those updates, any consumer reading both sees an inconsistent snapshot. The action-list pattern is fine; the dual-state is fragile.

**Expert 3 — Prober**

Both of you are treating "execution model" and "state consistency" as the correct level of analysis. But neither has questioned the foundational assumption: **that `threading.local` is the right isolation primitive for execution context**.

`threading.local` gives per-thread isolation. This is correct for threaded code. But `__iter__` exists precisely to enable async usage (it's the protocol `AsyncRetrying` builds on). In async code, two coroutines that share a `Retrying` instance are likely in the same thread. They share `self._local`, share `self.iter_state`, and the `RetryCallState` objects (which are NOT thread-local, they're local variables in the loop) won't help them. The thread-local model doesn't just fail for async — it actively signals "concurrency is handled" while providing no isolation in the execution model it was built for.

---

### The Transformation

| | |
|---|---|
| **Original claim** | Self-modifying action list makes control flow unreadable |
| **Transformed claim** | Thread-local storage is the wrong isolation primitive for the async execution context this architecture was built to support |

These are not different emphases on the same problem. They point at different failure modes:
- Original: a *representation* problem (static reasoning is impossible)
- Transformed: an *execution context* problem (correctness fails at runtime under the intended use pattern)

---

### The Gap Is Itself the Diagnostic

The dialectic traveled from **"you can't read this code"** to **"this code is wrong in the execution model it was designed for."** That's a large gap. The first claim is a sophistication critique. The second is a correctness critique. Something translated one into the other.

What did the translation? The experts were drawn to `threading.local` as the site of analysis because it is a *visible, high-credibility signal* of "I have thought about concurrent execution." It's stdlib. It's correct for what it claims to do. Encountering it, a reader lowers their guard on the entire concurrency story.

**The Concealment Mechanism: Signal Substitution**

A correct partial solution acts as a proxy guarantee for the complete solution. `threading.local` works perfectly for the threaded case. Its presence induces confidence that the concurrency story is complete — the same confidence transfers, unearned, to the async case. The developer who wrote `threading.local` was solving a real threading problem and wasn't forced by the structure to notice that the solution is wrong for async. The architecture actively obscures this by making the async path (`__iter__`) look like a natural extension of the threaded path.

The mechanism is not deception. It's a structural blind spot where partial correctness radiates false completeness.

---

### Applying the Mechanism: What Is Still Hidden

Now look for everywhere a *correct partial solution is masking an incomplete solution*.

`Future` extends `concurrent.futures.Future` — the most credible thread-safe future primitive in Python's stdlib. Its presence signals: "exception handling is principled, concurrent access is safe." Every call to `.result()`, `.exception()`, `.set_result()` acquires a `threading.Lock`. This is the same signal substitution pattern, applied to exception handling.

**What it is hiding:**

**1. `BaseException` laundering.** `Retrying.__call__` does:

```python
except BaseException:
    retry_state.set_exception(sys.exc_info())
```

`sys.exc_info()[1]` can be a `KeyboardInterrupt`. The Future stores it. The retry strategy evaluates it. If the stop condition fires, `exc_check` runs:

```python
raise retry_exc from fut.exception()
```

This raises a `RetryError` — chained from a `KeyboardInterrupt` — rather than re-raising the interrupt directly. The interrupt is semantically transformed into a `RetryError`. The sophisticated `Future` abstraction makes this look like correct, principled exception plumbing. It is not.

**2. Lock overhead purchased for zero benefit.** All futures in this library are created, immediately set, and immediately read within the same thread, in sequence. They are never used for actual inter-thread synchronization. Every retry attempt pays lock acquire/release for zero concurrency benefit. The `Future` class signals "doing this correctly" while adding overhead that serves no purpose in practice. The partial solution (thread-safe Future) is correct for async/concurrent scenarios it never encounters.

**3. The unresolved-future hang trap.** `concurrent.futures.Future.result()` blocks indefinitely (by default) if the future is not yet resolved. In Tenacity, futures should always be resolved before `.result()` is called. But the mechanism guaranteeing this is the *self-modifying action list* — the very structure the original claim identified as opaque. If a bug in the action-list logic causes the wrong branch to execute (or no branch to execute), `iter()` returns `None`, `__call__` hits `else: return do` and silently returns `None`. The failure mode does NOT trigger the Future's blocking behavior. It silently returns the wrong value.

What this reveals: **the architectural dependency on `concurrent.futures.Future.result()` as a safety mechanism is never documented, never tested as a safety net, and in practice never fires** — because the actual failure mode routes around it entirely. The whole correctness model of the exception path rests on a guard that is functionally inert.

---

### What the Entire Dialectic Failed to Surface

The dialectic examined three things: execution model (action list), state consistency (dual attempt_number), and isolation primitive (thread-local). All three are about *when and how code runs*.

None of the experts examined **implicit behavioral contracts embedded in library choices**. The `Future` was invisible to all three because it appears solved. It radiates the same `threading.local`-style false completeness. `concurrent.futures.Future` is a well-understood tool, so it doesn't invite scrutiny.

The concealment mechanism is still operating: signal substitution means that *anywhere a well-known, correct library component is used*, the reader stops analyzing. The code has three such components (`threading.local`, `concurrent.futures.Future`, `functools.wraps`), and in each case the library's correctness for its intended use-case proxies as a guarantee of correctness in *this* use-case — which differs from the intended use-case in exactly the ways that matter.
