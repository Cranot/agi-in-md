# Pattern: **Linear Data Pipeline** (Pipes and Filters)

Each step consumes the prior step's output and a slice of `config`, producing input for the next. It's a fold/reduction of a data value through a sequence of transformations.

---

## Three Analytical Operations (derived from *this* pipeline's properties)

### 1. **Identify Coupling Points** (structural)

Every step is hardcoded in sequence. You can't skip, reorder, or inject a step without editing this function. And each intermediate variable (`validated`, `transformed`, ...) is used exactly once — they're just connective tissue. This is *rigid sequential coupling disguised as readable code*.

### 2. **Factor into Composable Units** (compositional)

Every step shares the shape `(data, config_fragment) → data`. That uniformity is begging to be exploited:

```python
def process(data, config):
    steps = [
        (validate,       config.rules),
        (transform,      config.mappings),
        (enrich_step,    config.sources),   # see below
        (apply_filters,  config.filters),
        (group_by,       config.group_key),
        (aggregate,      config.agg_func),
        (format_output,  config.output_format),
    ]
    result = data
    for fn, cfg in steps:
        result = fn(result, cfg)
    return result
```

Now the pipeline is **data** — extensible, reorderable, introspectable. You can log between steps, time each one, or build pipelines dynamically from config.

### 3. **Separate Pure Computation from Effects** (semantic)

Six of seven steps are pure transforms. One is not:

```python
enriched = enrich(transformed, fetch_external(config.sources))
#                              ^^^^^^^^^^^^^^^^ side effect: I/O
```

This **contaminates the entire pipeline** — you can't cache, retry, or test it without hitting an external service. Fix: make `fetch_external` happen *before* the pipeline, or inject its results:

```python
def process(data, config, external_data=None):
    external_data = external_data or fetch_external(config.sources)
    # ... pure pipeline using external_data
```

Now the pipeline is pure and testable; effects live at the boundary.

---

## The Inversion: What operation can't this frame generate?

**Error accumulation and partial results.** The pipeline frame assumes every step succeeds completely. But what if `validate` rejects 30% of records? What if `fetch_external` fails for some items? You need a fundamentally different structure — a **monadic pipeline** (e.g., `Result`/`Either`) or a **split-stream** architecture where invalid items flow into an error channel while valid items continue. That's outside the linear pipe frame entirely, and it's probably the most important thing this function is missing.
