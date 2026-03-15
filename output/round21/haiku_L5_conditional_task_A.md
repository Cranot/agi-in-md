# Pattern Analysis

This instantiates the **Pipeline/ETL (Extract-Transform-Load) Pattern**, specifically a **serial transformation chain** where each stage passes output to the next.

## Structural Diagnosis

### Hierarchical Decomposition

| Layer | Structure | Issue |
|-------|-----------|-------|
| **Execution** | 7 stages, fixed sequence | Overly rigid; no conditional skipping |
| **Configuration** | One monolithic config object | Couples unrelated concerns |
| **Dependencies** | Implicit data shape contracts | `enrich()` depends on `fetch_external()` but this is hidden |

**Compression Bottleneck:** The function conflates *what stages exist* with *how they're orchestrated* with *what enables them*. You can't see which operations are optional, commutative, or could be reordered.

---

## Two Branches & Their Inversions

### Branch A: Treat as Hierarchical (My Initial Path)
Recognize "group + aggregate" as a paired concern; "validate + transform" as a preprocessing phase.

```python
def process(data, config):
    data = preprocess(data, config)        # validate + transform
    data = enrich_stage(data, config)      # enrich
    data = aggregation_pipeline(data, config)  # filter + group + aggregate
    return format_output(data, config.output_format)
```

**What this reveals:** The flat structure hides the fact that some operations *belong together*.

### Branch B: Steelman the Flatness (The Path Not Taken)
This structure is actually **good** if:
- Order matters for **audit trails** (compliance, debugging)
- Each step is genuinely **independent** and testable
- This is a **fixed workflow** (reporting engine), not a flexible one

**What this reveals:** I assumed flatness was bad because of my OOP bias toward composability. But for a *deterministic pipeline*, flatness = transparency.

---

## What I'd Change (Reconciling Both Views)

```python
def process(data, config):
    # 1. Make optionality explicit
    if not config.validate:
        return None  # or raise
    data = validate(data, config.rules)
    
    # 2. Bundle operations that belong together
    data = transform(data, config.mappings)
    data = enrich_and_filter(
        data, 
        fetch_external(config.sources),
        config.filters
    )
    
    # 3. Clarify group-aggregate as a unit
    data = group_and_aggregate(
        data, 
        group_key=config.group_key,
        agg_func=config.agg_func
    )
    
    # 4. Add error boundaries
    return format_output(data, config.output_format)
```

### Or, if the pipeline itself should be configurable:

```python
class PipelineConfig:
    stages: List[Stage]  # Make pipeline composition explicit
    
pipeline = Pipeline(
    stages=[
        Validate(config.rules),
        Transform(config.mappings),
        Enrich(config.sources),
        Filter(config.filters),
        GroupAggregate(config),
        Format(config.output_format),
    ]
)
```

---

## The Inversion Question

**What property made me branch to "hierarchical"?** 
- The function's *length* (7 steps)
- My default bias toward abstraction/reuse
- Assumption that "flat = scalability problem"

**What did Branch B (flatness) see that I missed?**
- For **fixed workflows**, explicit linearity is a feature
- The problem isn't the structure—it's that **optionality is hidden**
- This is a *reporting pipeline*, not a framework

**The real fix:** Make the design intent explicit. If it's fixed, keep the flat imperative sequence but group related operations. If it's configurable, replace the function with a declarative pipeline builder.
