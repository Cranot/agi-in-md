# Falsifiable Hypothesis

**Claim:** The deepest structural problem is not the rigid pipeline ordering (the obvious critique), but the **undeclared effect boundary**: `fetch_external()` is an impure I/O call buried inside what presents itself as a pure data-transformation pipeline. This conflation makes the function structurally dishonest about its dependencies and untestable at the level that matters most.

---

## The Three-Expert Test

### Expert 1 (Defender): "The claim is correct and underestimated."

Every other step follows `f(data, config_fragment) → data`. But step 3 breaks the contract:

```python
# Steps 1,2,4,5,6,7: pure — deterministic, instant, testable
# Step 3: impure — network I/O, latency, failure modes, non-determinism
enriched = enrich(transformed, fetch_external(config.sources))  # ← the liar
```

This means you **cannot** unit test this pipeline without mocking network calls. You cannot retry the I/O independently of the transformation. You cannot cache the external fetch across runs. The function's signature `(data, config) → result` *promises* purity but *delivers* side effects. That's structural dishonesty.

### Expert 2 (Attacker): "The real problem is the rigid monolith, not the effect."

The effect is *a* problem, but the **deepest** problem? No. Even if you removed `fetch_external`, this function is still a hardcoded sequence of seven steps that cannot be:
- **Reordered** (what if filtering before enrichment is faster?)
- **Skipped** (what if no aggregation is needed?)
- **Extended** (what if a new step must be inserted?)

The real fix is making it a **composable pipeline**, which *incidentally* also solves the effect problem:

```python
pipeline = Pipeline([
    Step(validate,       config.rules),
    Step(transform,      config.mappings),
    Effect(fetch_enrich, config.sources),   # effect is now declared
    Step(apply_filters,  config.filters),
    Step(group_by,       config.group_key),
    Step(aggregate,      config.agg_func),
    Step(format_output,  config.output_format),
])
result = pipeline.run(data)
```

### Expert 3 (Probing assumptions): "You're both assuming the pipeline *should* vary."

Both arguments assume composability is desirable. But maybe this is a **domain-specific workflow** where the order is invariant by business rule. Validation *must* precede transformation. Enrichment *must* precede filtering. If the sequence is semantically fixed, then reorderability is a non-feature — it introduces bugs.

However — even under that assumption, **the effect boundary problem survives**. A fixed pipeline still needs testability, retry logic, and failure isolation. The impure step is the structural problem precisely because it's the one issue that matters *regardless of whether the pipeline is rigid or flexible*.

---

## Verdict: Strengthened, with refinement

Expert 2's composability argument is real but **conditional** — it only matters if the domain permits variation. Expert 3 showed that the effect boundary is the problem that survives under *all* assumptions. The minimum structural fix:

```python
def process(data, config, external_data=None):
    # Effect boundary pushed to the caller or injected
    external_data = external_data or fetch_external(config.sources)
    ...
```

**What I know now that I couldn't before:** The litmus test for "deepest structural problem" is *invariance under assumption changes*. Composability is contingent. The hidden effect is not.
