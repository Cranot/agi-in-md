# The Circuit Breaker's Discrimination Impossibility

## Feature That Becomes Impossible

**Exception-specific retry strategies (routed by failure type).**

You cannot implement:
```python
// CANNOT EXIST with this architecture
def execute_with_smart_retry(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except RateLimitError:
        # Use longer backoff, higher max_retries
        return self._retry_with_strategy("rate_limit", fn, *args, **kwargs)
    except TimeoutError:
        # Use short backoff, lower max_retries  
        return self._retry_with_strategy("timeout", fn, *args, **kwargs)
    except TransientError:
        # Use exponential backoff, up to 10 retries
        return self._retry_with_strategy("transient", fn, *args, **kwargs)
```

**Why it's impossible, not just "hard":**
- `execute()` catches all exceptions uniformly (`except Exception`)
- `_retry_with_backoff()` has hardcoded parameters (base_delay=1, max_retries=3)
- Control flow: execute → _retry_with_backoff → [exception swallowed] → _on_failure()
- Exception TYPE is lost at the dispatch boundary. By the time you're in _retry_with_backoff, you only have an exception object, no routing context.
- You cannot retrofit discriminated recovery without restructuring control flow itself.

The architecture **erases exception type information** at a boundary you cannot cross from the inside.

---

## Feature That Becomes Mandatory

**Exception-classified recovery dispatch layer.**

If users want adaptive recovery, this pattern becomes inevitable and must exist:

```python
class RecoveryDispatcher:
    """MANDATORY: The circuit breaker cannot be opaque anymore."""
    
    def __init__(self, circuit_breaker, strategies=None, fallbacks=None):
        self.cb = circuit_breaker
        # ← REQUIRED: Map exception types to strategies
        self.strategies = strategies or {}
        # ← REQUIRED: Map exception types to fallbacks
        self.fallbacks = fallbacks or {}
    
    def execute(self, fn, *args, **kwargs):
        """The circuit breaker is now a BLACK BOX.
        All discrimination happens here, outside it."""
        
        try:
            return self.cb.execute(fn, *args, **kwargs)
        
        except CircuitOpenError as e:
            # Circuit breaker gave up. Try fallback.
            if CircuitOpenError in self.fallbacks:
                return self.fallbacks[CircuitOpenError]()
            raise
        
        except Exception as e:
            exc_type = type(e)
            
            # ROUTE BY TYPE (was impossible inside CircuitBreaker)
            if exc_type in self.strategies:
                strategy = self.strategies[exc_type]
                return strategy.recover(fn, e, *args, **kwargs)
            
            if exc_type in self.fallbacks:
                return self.fallbacks[exc_type]()
            
            raise
```

With required configuration:

```python
strategies = {
    RateLimitError: RetryStrategy(
        base_delay=2.0,
        max_retries=10,
        backoff="linear"
    ),
    TimeoutError: RetryStrategy(
        base_delay=0.5,
        max_retries=3,
        backoff="exponential"
    ),
    ConnectionError: RetryStrategy(
        base_delay=1.0,
        max_retries=5,
        backoff="exponential"
    ),
}

fallbacks = {
    RateLimitError: lambda: use_cached_result(),
    CircuitOpenError: lambda: graceful_degrade(),
}

dispatcher = RecoveryDispatcher(circuit_breaker, strategies, fallbacks)
```

**Why it's mandatory:**
- Consumers WILL implement this anyway (as nested try-except outside the CB)
- Once moved outside, fault handling becomes fragmented (state in CB, strategy in caller)
- To unify fault handling, this dispatcher becomes architecturally necessary
- The original code makes it impossible; users build it anyway; the architecture breaks.

---

## Coupling Redistribution

| Dimension | Original | Mandatory Change |
|-----------|----------|------------------|
| **Where exception type is visible** | Never (caught, discarded) | Everywhere (in dispatcher signature) |
| **What couples to exception taxonomy** | Implementation detail (backoff function) | Configuration contract (_strategy_map) |
| **Binding time** | Runtime (heuristic: "try exponential backoff") | Configuration time (explicit registration) |
| **Responsibility boundary** | Circuit breaker owns recovery | Dispatcher owns recovery, CB owns state |
| **Coupling direction** | Implicit (CB doesn't name what it handles) | Explicit (dispatcher declares what it routes) |

**The critical move:**
- **Original**: Coupling to exception types is HIDDEN in algorithm choice (exponential backoff = implicit assumption about failure types)
- **Mandatory**: Coupling to exception types is EXPOSED in strategy map (explicit assumption, enforced by registration)

**Total coupling is conserved:**
$$\text{Hidden-Type-Coupling} + \text{Visible-Config-Burden} = \text{Total-Exception-Semantics-Coupling}$$

You cannot reduce coupling to exception semantics. You can only make it visible or hide it.

---

## Where Complexity Migrates

| Original | Mandatory |
|----------|-----------|
| Complexity is **temporal** (state machine: CLOSED→OPEN→HALF_OPEN) | Complexity is **taxonomic** (exception type → strategy mapping) |
| Hidden in time-based transitions | Exposed in configuration |
| Testing: "Does state transition work?" | Testing: "Do all exception types route correctly?" |
| Coupling: STATE + TIME | Coupling: EXCEPTION_TYPE + STRATEGY_REGISTRATION |
| Assumption: "All failures are temporary" | Assumption: "Failure type determines recovery" |

**Migration destinations:**

1. **Configuration burden**: Now must enumerate and register exception types (15+ types = 15 configuration decisions)
   
2. **Testability**: Testing moves from "state machine behavior" to "routing correctness"
   - Original: Test that open circuit rejects calls
   - New: Test that TimeoutError routes to 3-retry strategy, RateLimitError routes to 10-retry, etc.

3. **Fallback decision points**: Every unmapped exception type becomes a decision
   - Original: "Always retry with exponential backoff"
   - New: "What do I do with UnknownException? Is it retryable?"

4. **Coupling to exception hierarchy**: Code now depends on what exceptions exist, not just how many failures
   - Original: "Failure is a binary fact"
   - New: "Failure type is semantic information I must act on"

---

## The Architectural Law: "The Dispatch Concealment Conservation"

**Named precisely:**

> **The Type-Erasure Impossibility Law:** Any system that erases type information at a dispatch boundary makes type-specific routing structurally impossible across that boundary. The system conserves coupling to type semantics — hiding it costs explicit external dispatch; exposing it costs configuration burden. You cannot have both generic internal recovery (type-erased) and specific recovery strategies (type-aware) without introducing a new dispatch layer outside the abstraction.

**Or more sharply — The form the taxonomy reveals:**

> **The Circuit Breaker's Hidden Commitment:** By treating all exceptions uniformly in `execute()`, the code commits to a single recovery strategy for all failure types. This commitment is hidden, not explicit. Once users need type-specific recovery, that hidden commitment becomes an obstacle, not a feature. The architecture forbids what it should have made optional.

**The conservation law it instantiates:**

$$\text{Exception-Type-Awareness} = \text{Visibility} + \text{Configuration-Coupling}$$

Minimal visibility (hidden in exponential backoff) = maximum implicit coupling
Maximum visibility (exposed strategy map) = maximum explicit coupling
**Cannot reduce total coupling.**

---

## Deeper Pattern: What This Code Silently Imposes

This circuit breaker exports **three mandatory architectural commitments** to every system that depends on it:

1. **All failures are homogeneous** (they don't differ in recovery strategy)
2. **Recovery is the circuit breaker's responsibility** (not the caller's)
3. **Exception type information is not relevant to recovery** (binary: retryable or not)

Once you accept this code into your system, you cannot later:
- Add rate-limit-specific backoff (violates #1)
- Delegate recovery strategy to the caller (violates #2)
- Route based on exception semantics (violates #3)

These aren't bugs. They're **structural impossibilities the code imposes on architectures that depend on it.**

The mandatory feature (RecoveryDispatcher) exists only to **escape these commitments**. And escaping them makes the circuit breaker a black box again, fragmenting fault handling logic across two layers.

---

## The Reflexive Discovery (L13)

The code reveals that **the circuit breaker and its mandatory wrapper are the same impossibility viewed from opposite sides:**

- **Circuit breaker**: "All failures are uniform, we handle recovery"
- **RecoveryDispatcher**: "Not all failures are uniform, we route to different recovery"

Same structural impossibility: **Can recovery be generic (CB view) or specific (Dispatcher view)?**

The answer: **It must be both, layered.** Circuit breaker handles *availability* (state machine). Dispatcher handles *strategy* (routing). They address different impossibilities.

The law: **"Fault tolerance systems that conflate availability with strategy create the dispatcher. Fault tolerance systems that separate them require the dispatcher."** Either way, the dispatcher becomes mandatory once the circuit breaker exists.
