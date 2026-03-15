## Pre-Prediction

> **What all three experts will fail to notice:** The linear variable chain (`validated → transformed → enriched → ...`) constitutes an *implicit type contract* between every adjacent pair of steps — but nothing enforces it. Each step's output must be the next step's valid input, yet this invariant exists only in the programmer's head. The pipeline's clean appearance actually *hides type fragility*; a drift in any function's return shape will manifest as an error *downstream*, not at the point of mismatch.

---

## The Pattern

This is a **linear transformation pipeline** (sometimes called a "threading" or "conveyor belt" pattern). Data flows unidirectionally through a fixed sequence of stages.

---

## Three Experts Argue

### 🟢 Expert A (Strengths): *"This is exemplary clarity."*

> Each line is a self-documenting stage. You can read top-to-bottom and understand the entire data lifecycle in 8 seconds. The naming is superb — `validated`, `transformed`, `enriched` — each variable name captures the *cumulative state* of the data. Compared to a nested call `format_output(aggregate(group_by(...)))`, this is vastly more debuggable. You can breakpoint any line and inspect intermediate state. This pattern is the *right* level of abstraction: concrete enough to follow, abstract enough to swap implementations.

### 🔴 Expert B (Failure Modes): *"This is a fragile happy-path fiction."*

> There is **zero error handling**. What happens when `validate()` rejects everything? When `fetch_external()` times out? Every remaining stage runs on garbage or crashes. There's no retry logic, no circuit breaker, no partial failure semantics. And `fetch_external()` is **side-effecting I/O buried inside what looks like a pure transformation pipeline** — it introduces latency, non-determinism, and network failures into an otherwise functional chain. This is a *lie of symmetry*: the stages look uniform but one of them is fundamentally different.

### 🟡 Expert C (What Both Miss): *"You're both staring at the steps. Look at the wiring."*

> The real problem is **rigidity**. This pipeline is *hard-coded topology*. You can't:
> - Reorder steps (can filtering happen before enrichment? maybe it should — to avoid expensive external calls on data you'll discard)
> - Skip steps conditionally
> - Parallelize independent steps (`validate` and `fetch_external` have no data dependency — they could run concurrently)
> - Compose pipelines from reusable fragments
>
> This should be a **pipeline-as-data** pattern — a list of stages that a runner executes — not imperative sequencing:
>
> ```python
> pipeline = Pipeline([
>     Step(validate,       config.rules),
>     Step(transform,      config.mappings),
>     Step(enrich,         Lazy(fetch_external, config.sources)),
>     Step(apply_filters,  config.filters),
>     Step(group_by,       config.group_key),
>     Step(aggregate,      config.agg_func),
>     Step(format_output,  config.output_format),
> ])
> return pipeline.run(data)
> ```
>
> Now you get middleware, observability, error handling, reordering, and conditional execution *for free*.

### The Argument

**Expert A fires back:** "Your `Pipeline` class is a textbook case of over-engineering. You've traded 8 readable lines for a framework that requires everyone to learn `Step`, `Lazy`, and `Pipeline.run()`. You've made it *harder* to debug — now I need to understand the runner's execution model to set a breakpoint."

**Expert B to C:** "Your pipeline-as-data doesn't solve my core concern. Whether it's imperative or declarative, `fetch_external` is I/O. You need an explicit architectural boundary — an `async` stage, a port/adapter separation — not just a `Lazy` wrapper."

**Expert C concedes partially:** "Fair — but a pipeline runner *can* enforce that boundary. The imperative version *can't*."

---

## Did They Miss My Prediction?

**Yes — all three missed it.**

No expert addressed the **inter-stage type contract problem**. Consider:

```python
# What if `transform` starts returning a DataFrame 
# but `enrich` expects a list of dicts?
transformed = transform(validated, config.mappings)
enriched = enrich(transformed, fetch_external(config.sources))  # 💥 runtime blow-up
```

- **Expert A** praised readability but readability doesn't surface type mismatches.
- **Expert B** focused on runtime *failures* (network, validation) but not on *structural incompatibility* between stages.
- **Expert C** proposed pipeline-as-data but `Pipeline([Step(...), Step(...)])` has the *same* type-gap problem — it just moves it from code to configuration. In fact, it makes it *worse* because the types are now even less visible.

### Why Was It Invisible to All Three Frames?

Because each expert's frame **assumes the pipeline already works and asks what could go wrong at runtime**. The type-gap is a **design-time / evolution-time** problem: it only manifests when someone *changes* one stage without updating its neighbors. It's invisible because:

1. The code *looks* like it flows — the variable names create a narrative of continuity
2. Python's duck typing means there's no compiler to complain
3. The linearity itself is seductive — it implies each step "obviously" produces what the next needs

### What I'd Actually Change

```python
from dataclasses import dataclass

@dataclass
class PipelineState:
    """Explicit type contract between stages."""
    records: list[dict]
    metadata: dict

def process(data, config) -> PipelineState:
    state = PipelineState(records=data, metadata={})
    state = validate(state, config.rules)
    state = transform(state, config.mappings)
    state = enrich(state, fetch_external(config.sources))
    state = apply_filters(state, config.filters)
    state = group_by(state, config.group_key)
    state = aggregate(state, config.agg_func)
    return format_output(state, config.output_format)
```

A **shared state type** makes the inter-stage contract *explicit and enforceable*. Every function's signature is `(PipelineState, config) → PipelineState`. Now a type checker can verify the chain, and adding a stage requires conforming to the protocol rather than hoping the shapes align.
