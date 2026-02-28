# Structure First Analysis: Circuit Breaker with Retry

## 1. The Vocabulary That Terminates Inspection

**"Circuit Breaker" + "Retry with Backoff"** — two canonical resilience patterns from distributed systems literature (Nygard's *Release It!*, AWS architecture guides). Each term is so well-defined in isolation that their *composition* escapes scrutiny. A reader sees `CLOSED → OPEN → HALF_OPEN`, sees `_retry_with_backoff` with exponential delay and jitter, and thinks *"I know what both of these are, so I know what this is."*

Recognition terminates inspection. No one asks: **what does it mean for a probe to retry?**

---

## 2. The Legitimate Improvement That Deepens Concealment

Introduce a `RetryPolicy` abstraction, state-change listeners for observability, and exception filtering:

```python
class RetryPolicy:
    def __init__(self, max_retries=3, base_delay=1,
                 retriable=(Exception,)):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.retriable = retriable

class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=30,
                 half_open_max=3, default_policy=None,
                 on_state_change=None):
        self._default_policy = default_policy or RetryPolicy()
        self._on_state_change = on_state_change  # callback(old, new, metrics)
        # ... rest unchanged ...

    def execute(self, fn, *args, policy=None, **kwargs):
        policy = policy or self._default_policy
        # ... state check ...
        result = self._retry_with_backoff(fn, *args, policy=policy, **kwargs)
        # ...

    def _retry_with_backoff(self, fn, *args, policy, **kwargs):
        for attempt in range(policy.max_retries):
            try:
                return fn(*args, **kwargs)
            except tuple(policy.retriable) as e:
                if attempt == policy.max_retries - 1:
                    raise
                time.sleep(policy.base_delay * (2 ** attempt)
                           + random.uniform(0, 1))
```

This looks like a clean refactor. It promotes the retry parameters from hidden kwargs to a named object. It adds observability. It adds exception discrimination. **But it deepens the concealment** — every structural flaw below is made to look more intentional.

---

## 3. Three Properties Visible Only Because We Tried to Strengthen It

### Property A: The retry mechanism is load-multiplied behind the circuit breaker's threshold, and the `RetryPolicy` promotes this coupling to a feature

In the original code, with `failure_threshold=5` and `max_retries=3`, the circuit opens after 5 `execute()` calls — but those 5 calls represent **15 actual failed requests** against the downstream service. The circuit breaker's threshold is a lie; it actually tolerates `threshold × max_retries` real failures.

When you introduce `RetryPolicy` as a per-call configuration, the problem metastasizes: **different callers with different policies produce different real failure counts for the same circuit breaker threshold.** One caller with `max_retries=1` trips the breaker after 5 downstream failures; another with `max_retries=10` trips it after 50. The threshold ceases to be a property of the circuit breaker. It becomes a property of the *composition*, which neither component owns or names.

The `RetryPolicy` abstraction makes this look *designed* — "of course different callers have different retry budgets" — when it's actually **incoherent**: the failure threshold cannot mean anything stable if the retry multiplier varies per call.

### Property B: The `**kwargs` pass-through creates an invisible namespace collision, and the `RetryPolicy` exposes the caller-internal coupling it was hiding

Look at the original signatures:

```python
def execute(self, fn, *args, **kwargs):          # passes **kwargs through
def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
```

`execute` forwards all `**kwargs` to `_retry_with_backoff`, which **silently intercepts** `max_retries` and `base_delay` before forwarding the rest to `fn`. If `fn` accepts a parameter named `max_retries`, it will *never receive it*. The internal method's parameter names have become part of the public API's namespace constraints — but this is invisible because `**kwargs` doesn't declare what it captures.

When you try to introduce `RetryPolicy`, the incoherence surfaces: the policy object should be the *only* source of retry configuration, but removing `max_retries`/`base_delay` from the `**kwargs` interception **changes the public API**. Any caller who was (intentionally or accidentally) passing `max_retries` through `execute()` will now have that kwarg land on `fn` instead. The improvement reveals that the original API had **two undeclared contracts in one parameter space**, and there's no way to separate them without a breaking change.

### Property C: The `_on_failure()` path produces two irreconcilable failure shapes depending on state, and state-change listeners force you to name the incoherence

Add `on_state_change(old_state, new_state, metrics)` and try to define `metrics`. You must answer: what is `_failure_count` at each transition?

| Transition | `_failure_count` | Meaning |
|---|---|---|
| CLOSED → OPEN | 5 | "Consecutive failures reached threshold" ✓ |
| OPEN → HALF_OPEN | **still 5** | ??? |
| HALF_OPEN → OPEN (1 failure) | **6** | "Threshold exceeded" — but threshold is 5, and this is the first failure in HALF_OPEN |
| HALF_OPEN → CLOSED | gets reset to 0 | ✓ |

The listener callback forces you to serialize state, and the serialized state is **incoherent**. `_failure_count` means "consecutive failures toward tripping" in CLOSED but means "leftover count guaranteeing instant re-trip" in HALF_OPEN. The state-change listener can't report a coherent metric because the variable serves two incompatible roles. The listener makes the structural conflation undeniable — but without the listener, it's invisible.

---

## 4. The Problem ONLY Visible Through Construction

**HALF_OPEN is not a probe state; it is an instant-trip trap — and this is purely accidental.**

This is invisible by reading. The name `HALF_OPEN` activates the circuit breaker mental model: "let through a few test requests; if they succeed, close; if they fail, reopen." That model implies a *fresh assessment*. But trace the actual state:

1. `_failure_count` reaches 5 → state becomes OPEN
2. Timeout expires → state becomes HALF_OPEN, `_success_count` reset to 0
3. **`_failure_count` is never reset.** It's still 5.
4. First probe call enters `_retry_with_backoff`, which retries 3 times internally
5. If all 3 retries fail → `_on_failure()` increments `_failure_count` to 6
6. `6 >= 5` → state immediately returns to OPEN

**One probe failure (after 3 hidden retries) instantly re-opens the circuit.** The `_failure_threshold` of 5 is meaningless in HALF_OPEN — *any* threshold ≥ 1 would produce the same behavior, because the count is already at or above threshold when HALF_OPEN begins.

This only becomes visible through construction because:

- **Reading** the code, `_on_failure` looks uniform and correct — it increments, checks threshold, trips. Nothing looks wrong.
- **Adding the state-change listener** forces you to answer "what should I report as the failure count when entering HALF_OPEN?" The answer (5, the same as when we entered OPEN) makes the accidental semantics undeniable.
- **Adding `RetryPolicy`** makes it worse: a policy with `max_retries=10` means a HALF_OPEN probe makes 10 real requests against a potentially-down service before the single logical failure is recorded — and that single failure *always* re-trips the circuit. The probe is simultaneously too aggressive (10 retries) and too sensitive (one failure kills it).

The retry mechanism and the circuit breaker have **irreconcilable failure semantics that only compose incoherently**, but the vocabulary of both patterns is so well-established that no amount of reading reveals this. You have to try to build on top of it — add a listener, parameterize the policy, expose the metrics — before the structure confesses what it actually does.

---

## Summary

| Layer | Finding |
|---|---|
| **Vocabulary shield** | "Circuit Breaker" + "Retry with Backoff" — two known-good patterns whose *composition* is never inspected |
| **Improvement** | `RetryPolicy` + state-change listeners + exception filtering — makes every flaw look intentional |
| **Property A** | Failure threshold is meaninglessly multiplied by per-call retry counts |
| **Property B** | `**kwargs` creates an undeclared namespace collision between internal config and `fn`'s parameters |
| **Property C** | `_failure_count` means different things in different states; listeners can't serialize coherent metrics |
| **Construction-only** | HALF_OPEN is an accidental one-strike trap: `_failure_count` is never reset on entry, so the threshold is pre-exceeded, and any single probe failure (after hidden retries) instantly re-opens the circuit |
