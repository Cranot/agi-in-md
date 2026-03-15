## Structural Pattern: Linear Data Pipeline

The function is a **sequential transformation pipeline** — each stage consumes the previous stage's output. Clean, readable, single-entry/single-exit. That's genuinely good.

---

## The Falsifiable Claim

> **The deepest structural problem is not the pipeline shape — it's that `fetch_external` is called eagerly, mid-pipeline, making failure invisible and state unreachable at precisely the stage where both are most likely.**

This is falsifiable: if you can test stages 4–7 without mocking, resume from stage 3 after a network failure, or observe what `enrich` received — the claim is wrong.

---

## The Three-Expert Dialectic

**Defender** confirms the claim:
Embedding I/O at step 3 means stages 4–7 are untestable without hitting real infrastructure. A network timeout at `fetch_external` produces an exception with no information about what was already validated and transformed. The happy path runs fine; the failure path is a black hole.

**Attacker** redirects:
The `config` object is the real disease; `fetch_external` placement is a symptom. `config` carries implicit knowledge of *all seven stages* — `rules`, `mappings`, `sources`, `filters`, `group_key`, `agg_func`, `output_format`. It's a god object. Change any stage's interface and `config`'s structure silently breaks. That coupling predates and causes the I/O problem.

**Prober** goes deeper:
Both of you assume the pipeline is correct and the problems are in the details. But the pipeline has *no failure model at all*. What does `validate` return on invalid data? Does `apply_filters` silently drop records? The absence of error-as-data means no caller can distinguish "processed 0 records" from "crashed at stage 2." The I/O placement and god object are downstream of this.

---

## Why Did the Dialectic Transform in THAT Direction?

The argument moved: **I/O placement → god object coupling → error propagation absence**.

This specific trajectory happened because each critique uncovered the same underlying violation at a deeper layer of abstraction:

| Critique | Isolation Violated | Question Revealed |
|---|---|---|
| I/O placement | *Temporal* — when does external state enter? | "Can I control timing?" |
| God object | *Spatial* — where does knowledge live? | "Can I control scope?" |
| No failure model | *Causal* — what caused this state? | "Can I control meaning?" |

**The structural force** shaping this dialectic is:

> **The pipeline treats only its output as meaningful. Intermediate states, failures, and side effects are structurally invisible.**

Every critic was forced toward the same question — *what happens when this breaks?* — and found a different layer at which the answer is *we can't know.* The dialectic had to move in this direction because the code provides no purchase points for reasoning about failure. Each expert grabbed a different handle on the same underlying opacity.

---

## What This Force Predicts Next

The next problem this code will face: **observability collapse under production load.**

When something produces wrong output — not a crash, just wrong — you'll have no record of which stage introduced the error, no intermediate states to inspect, no per-stage timing to profile, and no way to replay the failure with the same data. The pipeline returns one value and reveals nothing else.

The force predicts this because: *a system that models only success will encounter failure only as mystery.*

---

## What I'd Actually Change

```python
from dataclasses import dataclass
from typing import TypeVar, Callable, Generic
import logging

T = TypeVar('T')

# 1. Decompose the god object
@dataclass
class PipelineConfig:
    validation: ValidationConfig
    transformation: TransformConfig
    enrichment: EnrichmentConfig   # external data fetched separately
    filtering: FilterConfig
    grouping: GroupConfig
    aggregation: AggConfig
    output: OutputConfig

# 2. Make failure first-class
def process(data, config: PipelineConfig, external_data=None):
    stages = [
        ("validate",   lambda d: validate(d, config.validation)),
        ("transform",  lambda d: transform(d, config.transformation)),
        ("enrich",     lambda d: enrich(d, external_data)),  # injected, not fetched
        ("filter",     lambda d: apply_filters(d, config.filtering)),
        ("group",      lambda d: group_by(d, config.grouping)),
        ("aggregate",  lambda d: aggregate(d, config.aggregation)),
        ("format",     lambda d: format_output(d, config.output)),
    ]
    
    result = data
    for stage_name, stage_fn in stages:
        try:
            result = stage_fn(result)
            logging.debug("stage=%s records=%s", stage_name, len(result))
        except Exception as e:
            raise PipelineError(stage=stage_name, cause=e, state=result) from e
    
    return result
```

**Key changes and why:**

| Change | Addresses |
|---|---|
| `external_data` injected, not fetched | Temporal isolation — I/O happens before the pipeline |
| `PipelineConfig` decomposed | Spatial isolation — each stage owns its config |
| `PipelineError` with `stage` + `state` | Causal isolation — failures are locatable |
| Named stages with logging | Observability — intermediate state is recorded |

The pipeline shape was never the problem. The problem was everything the pipeline refused to acknowledge.
