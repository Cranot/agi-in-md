## Pattern: Linear Transformation Pipeline (Monadic Chain)

Each step produces output consumed by exactly the next step, with a shared config object threading through as a parameter bundle. Classic ETL pipeline instantiation.

---

## Three Analytical Operations (Derived from This Code's Properties)

### Derived from: *linearity + shared config + embedded I/O*

**Op 1 — Failure Mode Tracing** (follows from the chain's brittleness)
**Op 2 — Dependency Graph Decomposition** (follows from the god-config object)
**Op 3 — Ordering/Parallelism Analysis** (follows from the strict sequential structure)

---

## Prediction Before Execution

I predict **Op 1 (Failure Mode)** yields deepest insight — because `fetch_external` is visibly embedded mid-chain, suggesting rich failure paths.

---

## Execution

### Op 1 — Failure Mode Tracing

```
validate → transform → enrich(fetch_external) → filter → group → aggregate → format
    ↑           ↑              ↑ ← network call         ↑
 silent?     None prop?     exception?             garbage in?
```

Every step can fail silently or raise, with **zero recovery paths**. Crucially, `fetch_external` is a side effect *buried inside argument position* — it executes eagerly, unconditionally, before `enrich` even starts. If the network call fails: entire pipeline dies at step 3.

```python
# What actually executes on line 3:
external_data = fetch_external(config.sources)  # ← I/O happens HERE
enriched = enrich(transformed, external_data)
```

No retry, no fallback, no partial completion.

---

### Op 2 — Dependency Graph Decomposition

Map each step to its *actual* config dependency:

| Step | Config field used | Data dep |
|---|---|---|
| `validate` | `config.rules` | `data` |
| `transform` | `config.mappings` | `validated` |
| `enrich` | `config.sources` | `transformed` |
| `filter` | `config.filters` | `enriched` |
| `group_by` | `config.group_key` | `filtered` |
| `aggregate` | `config.agg_func` | `grouped` |
| `format_output` | `config.output_format` | `aggregated` |

**Finding:** `config` is a god-object. No step uses more than one config field. The function's *true* signature is:

```python
def process(data, rules, mappings, sources, filters, group_key, agg_func, output_format):
```

The bundling hides coupling and makes the function untestable in isolation.

---

### Op 3 — Ordering/Parallelism Analysis

```
Current order:
validate → transform → enrich(EXPENSIVE) → filter → group → aggregate → format

What's wrong:
filter operates on ENRICHED data — we pay enrichment cost on data we'll discard
```

**Critical reordering opportunity:**

```
validate → transform → filter → enrich → group → aggregate → format
                          ↑
                   Filter FIRST on cheap data
                   Enrich ONLY what survives
```

If filtering removes 80% of records, you've paid 80% of your external I/O unnecessarily in the original. Additionally, `fetch_external` has *no data dependency* — it could be pre-fetched before the pipeline starts, or run concurrently with early steps.

---

## Inversion: Was My Prediction Right?

**No.** Op 1 (failure modes) was the *most visible* problem but not the deepest.

**Op 3 (ordering)** revealed the most structurally consequential flaw: the pipeline pays maximum I/O cost before filtering, making performance scale with *input size* rather than *output size*. This is an architectural mistake, not just missing error handling.

**What this reveals about my blind spot:**
> I anchor on *correctness absences* (no error handling) before *efficiency structure* (wrong ordering). Missing error handling is loud and visible; wrong step ordering is silent and looks fine. I underweight ordering analysis when scanning pipelines because code *reads* in the "natural" English narrative order (validate → enrich → filter sounds like a story), obscuring that the *logical* order should often differ from the *narrative* order.

---

## Revised Implementation

```python
from typing import TypeVar, Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

def pipe(value: T, *fns: Callable) -> T:
    """Makes the pipeline explicit and composable."""
    for fn in fns:
        value = fn(value)
    return value

def process(data, config):
    # Pre-fetch: no data dependency, do it once, handle failure here
    try:
        external = fetch_external(config.sources)
    except ExternalFetchError as e:
        logger.error("External fetch failed: %s", e)
        raise PipelineError("enrichment source unavailable") from e

    return pipe(
        data,
        lambda d: validate(d, config.rules),       # 1. validate
        lambda d: transform(d, config.mappings),    # 2. transform
        lambda d: apply_filters(d, config.filters), # 3. filter EARLY ← key change
        lambda d: enrich(d, external),              # 4. enrich only survivors
        lambda d: group_by(d, config.group_key),    # 5. group
        lambda d: aggregate(d, config.agg_func),    # 6. aggregate
        lambda d: format_output(d, config.output_format), # 7. format
    )
```

**Or, if you want composability and per-step error isolation:**

```python
@dataclass
class PipelineStep:
    name: str
    fn: Callable
    
class Pipeline:
    def __init__(self, steps: list[PipelineStep]):
        self.steps = steps
    
    def run(self, data):
        for step in self.steps:
            try:
                data = step.fn(data)
                logger.debug("Step '%s' completed, records: %d", 
                           step.name, len(data))
            except Exception as e:
                raise PipelineError(f"Failed at '{step.name}'") from e
        return data
```

**Three changes that matter most, ranked:**
1. **Filter before enrich** — correctness of performance at scale
2. **Extract `fetch_external`** — makes I/O explicit, testable, retryable
3. **Named steps with logging** — you can't debug what you can't observe
