# Pattern: Pipeline (with Hidden Complexity)

## The Structure

This instantiates the **Pipeline Pattern** — sequential data transformation stages, each refining the previous output. Textbook examples show this working cleanly.

## Known Methods & Constraints

**What works here:**
- Linear clarity: easy to follow the data flow
- Testable stages (in isolation)
- Configuration-driven: decouples logic from control

**Critical failure modes:**
1. **No error handling** – where does validation fail? Does the function crash? Silent return?
2. **Hard-coded sequencing** – can't skip stages conditionally, reorder, or parallelize
3. **Side effects are invisible** – `fetch_external()` is performed eagerly; failures cascade
4. **Resource leaks** – what manages the lifecycle of fetched connections/handles?
5. **Intermediate state explosion** – 7 variables pollute the namespace; hard to debug which stage corrupted data

## Inversion: What This Framing Hides

The "neat pipeline" disguises that **real pipelines need**:

- **Error as data**, not exceptions – Result/Either types, not try/catch
- **Early termination** – one failed stage shouldn't trigger the rest
- **Observability** – timing, logging, retry-ability per stage
- **Conditional branching** – "if enrichment fails, use fallback" 
- **Parallelization** – some stages may be independent
- **Implicit contracts** – what schema does `transform()` output? Undocumented.
- **Mutation hiding** – is `config` or external state modified mid-pipeline?

## What Changes?

```python
class Pipeline:
    def __init__(self, *stages):
        self.stages = stages
    
    def execute(self, data, context=None):
        result = data
        for stage in self.stages:
            try:
                result = stage(result, context or {})
            except Exception as e:
                return Failure(stage=stage.__name__, error=e)
        return Success(result)

# Usage
pipeline = Pipeline(
    Validate(rules=config.rules),
    Transform(mappings=config.mappings),
    Enrich(sources=config.sources),
    # ... stages as objects, not functions
)

outcome = pipeline.execute(data)
if outcome.ok: return outcome.value
else: log_failure(outcome)
```

**Why this survives:** It separates *what* stages exist from *how* they're coordinated. That's the real answer hiding in the simple version.
