# Pattern: Linear Data Transformation Cascade

This is a **Pipeline** pattern, specifically a **declarative, configuration-driven processing cascade**. Each step is pure, sequenced, and parameterized—making the flow explicit but hiding its cost and failure surfaces.

---

## Three Analytical Operations (Derived from Structure)

### 1. **Stage Failure Atomicity Map** (Concrete)
*From the structure: each step depends on the previous, so failures cascade silently.*

**Operation:** Insert observability checkpoints at each stage.
```python
def process(data, config, observe=None):
    stages = [
        ("validate", validate, data, config.rules),
        ("transform", transform, ..., config.mappings),
        # ... etc
    ]
    for name, func, inp, param in stages:
        result = func(inp, param)
        if observe: observe(name, result)  # Expose failure/anomaly points
        inp = result
    return result
```

**Why derived from THIS structure:** The linear chaining makes one point of failure stop all downstream operations. You need to see where it broke.

---

### 2. **Cardinality Pressure Points** (Mid-Level)
*From the structure: each stage transforms data shape differently, but this is invisible.*

**Operation:** Track how data volume and structure change at each stage.
```python
# Audit: what's the actual cost profile?
- validate: 1M → 800K (20% filtered)
- groupby: 800K → 5 groups (!!)
- aggregate: 5 → 5 (why expensive?)
```

**Why derived from THIS structure:** `group_by` and `aggregate` are hidden complexity multipliers. The explicit naming of each stage makes this analysis possible but the function obscures it.

---

### 3. **Selective Recomputation via Dependency Inversion** (Abstract)
*From the structure: config fields could be traced to the stages they control.*

**Operation:** Build a minimal re-execution graph when config changes.
```python
# If only config.output_format changes, skip all prior stages
# If config.rules changes, restart from validate
# If config.sources changes, restart from enrich
```

**Why derived from THIS structure:** Each stage has an explicit config parameter. This structure *encodes* a dependency graph—you just can't see it yet.

---

## The Unsolvable Operation (Inversion)

**What you need that cannot be generated from this structure:**

**Semantic correctness validation** — You cannot determine from the code whether the *sequence itself makes sense*.

- Does `validate → transform → enrich → filter` prevent bugs, or does it just move garbage through stages?
- Why does `filter` come *after* `enrich`? (You might be enriching things you'll discard.)
- Does `group_by` + `aggregate` contradict your `filter` logic?

This requires **external domain knowledge**, not structural analysis.

---

## What I'd Change

```python
class Pipeline:
    def __init__(self, config):
        self.stages = [
            ("validate", validate, lambda c: c.rules),
            ("transform", transform, lambda c: c.mappings),
            ("enrich", enrich, lambda c: c.sources),
            ("filter", apply_filters, lambda c: c.filters),
            ("group", group_by, lambda c: c.group_key),
            ("aggregate", aggregate, lambda c: c.agg_func),
            ("format", format_output, lambda c: c.output_format),
        ]

    def process(self, data, config):
        state = data
        for name, func, param_getter in self.stages:
            state = func(state, param_getter(config))
            yield name, state  # Make failures observable
```

**Why:** Extracts the *pipeline pattern as data*, enabling introspection, instrumentation, and cost analysis without rewriting the logic.
