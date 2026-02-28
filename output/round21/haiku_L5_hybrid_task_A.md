# Pattern Analysis: Pipeline with Hidden Impurity

## Pattern Identification
This instantiates the **Pipeline Pattern**, but with a critical structural deception: it presents as a *pure data transformation pipeline* while containing an *embedded I/O operation* (`fetch_external()` in stage 3). This conflation of concerns is the defining property.

---

## Three Analytical Operations Derived from THIS Problem

Given the specific structure (linear sequence + configuration-driven + hidden I/O), these are most useful:

1. **Side-Effect Externalization Mapping** — Which operations are pure vs. impure, and what gets hidden by the abstraction?
2. **Failure-Path Propagation Analysis** — Which stage failures are recoverable, which cascade, which corrupt external state?
3. **Configuration-to-Capability Coupling** — How tightly is config schema bound to function behavior, and where will it ossify?

---

## Prediction Before Execution

**Deepest insight will come from:** Side-Effect Externalization

**Why:** I predict this reveals the *root cause*, while the other two reveal *symptoms*. The failure modes and config problems exist BECAUSE pure and impure operations are conflated. Identifying that conflation reframes the entire refactoring need.

---

## Execution

### Operation 1: Side-Effect Mapping
```
Pure (repeatable, testable, cached):
  validate, transform, apply_filters, group_by, aggregate, format_output

Impure (non-deterministic, non-repeatable, uncacheable):
  fetch_external(config.sources) — embedded in stage 3

Critical structural problem: 
  Stages 1-2 → pure
  Stage 3 → IMPURE (breaks assumption)
  Stages 4-7 → pure (but depend on impure stage's result)
  
This makes the entire pipeline impure, even though 6/7 stages are pure.
```

### Operation 2: Failure Propagation
```
Stage 1 (validate fails) → Stops cleanly. ✓
Stage 2 (transform fails) → Stops cleanly. ✓
Stage 3 (fetch_external fails) → ✗ DANGEROUS
  - Enrichment is partially applied
  - External system may have side effects (writes, caches, logs)
  - Stages 4-7 receive corrupted/incomplete data
  - No recovery path exists
  - Caller doesn't know whether failure is data-bad or network-bad

Stages 4-7 failures → Stop cleanly, but no rollback. 
```

### Operation 3: Configuration Coupling
```
config.rules, .mappings, .sources, .filters, .group_key, .agg_func, .output_format
  
Problem: Configuration schema must grow with each new stage.
  - No type hints on config fields
  - No schema validation at init time
  - Config keys are discovered at runtime only when used
  - "Missing config.sources" fails in the middle of execution
  - Can't validate config until you've built it and run it
```

---

## Inversion: Prediction vs. Reality

**Was my prediction right?** 

*Partially, but inverted.*

I predicted Side-Effect analysis would be deepest, and it *is*—but for a reason that surprised me: **it's not deep because it reveals complexity; it's deep because it reveals a category error.** This function doesn't have a failure mode *problem*; it has a *design* problem. The failures are symptoms.

**The gap reveals:** I initially conflated "deepest insight = most urgent operational risk" with "deepest insight = most fundamental structural misunderstanding." They're different. The side-effect analysis is deeper because it identifies why failure handling, configuration, and testability are all broken simultaneously—they're all broken because of *one mismatch*.

---

## What I'd Change

**Separate pure and impure concerns:**

```python
class DataPipeline:
    def __init__(self, config):
        self.config = ConfigValidator.validate(config)  # ← Validate once
    
    def execute(self, data):
        # Phase 1: Pure transformations (testable, no I/O)
        data = self._transform_phase(data)
        
        # Phase 2: I/O with explicit error handling
        external = self._fetch_phase()  # Isolated, retryable, mocked easily
        
        # Phase 3: Pure transformations on combined data
        return self._aggregate_phase(data, external)
    
    def _transform_phase(self, data):
        """No mocks needed. Repeatable. Fast test feedback."""
        data = validate(data, self.config.rules)
        data = transform(data, self.config.mappings)
        return apply_filters(data, self.config.filters)
    
    def _fetch_phase(self):
        """Explicit I/O: retries, fallbacks, circuit breakers go here."""
        return self._fetch_with_retry(
            self.config.sources, 
            max_retries=3,
            fallback=self.config.fallback_data
        )
    
    def _aggregate_phase(self, data, external):
        """Pure again. External data is now a value, not a function call."""
        data = enrich(data, external)
        data = group_by(data, self.config.group_key)
        data = aggregate(data, self.config.agg_func)
        return format_output(data, self.config.output_format)
```

**Why this matters:**
- Phases 1 and 3 are unit-testable without mocks
- Phase 2's failures are isolated and explicit
- Configuration is validated once, not at runtime
- The function's true dependencies are now visible in the code structure
