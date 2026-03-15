## Structural Diagnosis: `process`

---

### The Pattern

This is a **linear pipeline** — each step consumes the previous output. It's readable, but readability is the mechanism of concealment.

---

### Falsifiable Claim (The Deepest Problem)

> **Config is a god object that serializes a decision graph into parameter lookups, while sequential variable binding erases the pipeline's actual dependency structure.**

This is falsifiable: if every `config.*` attribute were truly a uniform parameter (controlling *how* a step runs, not *whether* or *what kind*), the claim is wrong. But it isn't — `config.group_key` controls grouping strategy, `config.agg_func` controls aggregation *type*, `config.filters` could be empty/None. These are branches, not parameters.

---

### Three Experts Debate

**Defender** — The real failure is that `config` bundles seven distinct policy concerns (validation policy, transformation policy, I/O policy, selection policy, grouping policy, aggregation policy, presentation policy) into one opaque object. Fix the config, fix the function.

**Attacker** — Wrong target. `fetch_external` is embedded *inside* a function argument on line 3. Every other step is a pure transformation; this one is a hidden I/O operation. You could fix config without exposing this. The pipeline *looks* pure because the impurity hides in an argument position.

**Prober** — You're both assuming the ordering is necessary. `validate → transform → enrich` encodes a dependency graph as execution order. But `fetch_external` has *no dependency* on `validate` or `transform` — it could run concurrently. The real question neither of you asked: **why is an implicit, possibly-wrong ordering being treated as structural ground truth?**

---

### The Claim Transforms

**Original:** Config is a god object.

**Transformed:** The pipeline serializes an implicit dependency graph into explicit execution order, and config bundles policy decisions that *control* that graph into a single opaque object. Both the graph and its control surface are invisible simultaneously.

---

### Concealment Mechanism: *Sequential Variable Binding as Dependency Graph Erasure*

Writing `validated = validate(...)`, `transformed = transform(validated, ...)` makes the dependency structure appear linear and complete. This hides:
- Which steps are independent (parallelizable)
- Which steps are optional
- That `fetch_external` is an effect, not a transformation
- That some config attributes are behavioral switches, not parameters

---

### Legitimate-Looking Improvement That Deepens Concealment

```python
from dataclasses import dataclass
from typing import Callable, Any

@dataclass  
class PipelineStep:
    name: str
    fn: Callable
    config_key: str

def process(data, config):
    steps = [
        PipelineStep('validate',  validate,      'rules'),
        PipelineStep('transform', transform,     'mappings'),
        PipelineStep('enrich',    _enrich,       'sources'),   # ← buried here
        PipelineStep('filter',    apply_filters, 'filters'),
        PipelineStep('group',     group_by,      'group_key'),
        PipelineStep('aggregate', aggregate,     'agg_func'),
        PipelineStep('format',    format_output, 'output_format'),
    ]
    result = data
    for step in steps:
        result = step.fn(result, getattr(config, step.config_key))
    return result

def _enrich(data, sources):
    return enrich(data, fetch_external(sources))  # I/O now two layers deep
```

This passes code review. It's "data-driven," "extensible," "DRY." It is strictly worse on every axis that matters.

---

### Three Properties Visible Only Because We Strengthened It

1. **The uniform interface is a lie.** `_enrich` had to be created to force conformity — `enrich` originally took external *data*, not sources. The wrapper reveals that steps have *different dependency structures* being papered over by a forced signature.

2. **Ordering is load-bearing but now completely invisible.** The list implies the order is arbitrary. It isn't. Reordering step 3 and step 1 breaks everything, silently.

3. **Config attributes aren't uniform.** `getattr(config, step.config_key)` makes every access look identical. But `config.filters = None` means something different from `config.rules = None`. The refactoring forces this distinction into silence.

---

### Apply the Diagnostic to the Improvement

**What it conceals:** That the pipeline has two fundamentally different step *kinds* — pure transformations and impure effects. The uniform loop structure obliterates this distinction.

**Property of the original now visible through recreation:** In the original, `fetch_external(config.sources)` was at least *visible* in the call site. The improvement buries it. This reveals: **every improvement that maintains interface uniformity must push the impurity somewhere — it cannot eliminate it.**

---

### Second Improvement: Address the Recreated Property

```python
import asyncio

async def process(data, config):
    # Pure synchronous phase
    validated  = validate(data, config.rules)
    transformed = transform(validated, config.mappings)

    # ── Explicit I/O boundary ──────────────────────────
    external = await asyncio.to_thread(fetch_external, config.sources)
    # ──────────────────────────────────────────────────

    # Pure synchronous phase resumes
    enriched   = enrich(transformed, external)
    filtered   = apply_filters(enriched, config.filters)
    grouped    = group_by(filtered, config.group_key)
    aggregated = aggregate(grouped, config.agg_func)
    return format_output(aggregated, config.output_format)
```

**Apply the diagnostic again:** This concedes that `validate` and `fetch_external` are *independent* — they could now run concurrently. But by making `fetch_external` *the* visible effect boundary, it creates a false impression that everything else is pure. What if `validate` logs? Caches? Has its own I/O? We've named one impurity and hidden the others by contrast.

**What persists:** The dependency graph is *still implicit*. We've separated pure from impure, but we haven't made the structural question visible: which steps actually depend on which?

---

### The Structural Invariant

> **In a sequential pipeline with a shared config object, making any one concern explicit forces at least one other concern implicit.**

- Making ordering explicit → hides purity/impurity distinction
- Making purity explicit → hides ordering optionality and parallelism
- Making config explicit → hides pipeline structure
- Making pipeline structure explicit (data-driven) → hides config's role as behavioral switch

This persists through every improvement because it is a property of the *problem space*, not the implementation: **a sequential pipeline with heterogeneous steps cannot simultaneously make ordering, purity, dependency, and parameterization explicit in a single linear representation.**

---

### Invert the Invariant

Design where all four properties are trivially satisfiable simultaneously:

```python
pipeline = DAG([
    Step('validate',   deps=[],                      effect=Pure, params=ValidationParams(config.rules)),
    Step('transform',  deps=['validate'],             effect=Pure, params=MappingParams(config.mappings)),
    Step('fetch',      deps=[],                       effect=IO,   params=SourceParams(config.sources)),
    Step('enrich',     deps=['transform', 'fetch'],   effect=Pure, params=EnrichParams()),
    Step('filter',     deps=['enrich'],               effect=Pure, params=FilterParams(config.filters)),
    Step('group',      deps=['filter'],               effect=Pure, params=GroupParams(config.group_key)),
    Step('aggregate',  deps=['group'],                effect=Pure, params=AggParams(config.agg_func)),
    Step('format',     deps=['aggregate'],            effect=Pure, params=FormatParams(config.output_format)),
])
```

Notice: `fetch` and `validate/transform` now have **no dependency edge between them** — the DAG makes parallelism trivially visible. Ordering, purity, dependency, parameterization: all explicit.

**The new impossibility the inversion creates:** The DAG reveals that `fetch` and `validate/transform` can fail *independently*. If `fetch` fails after `transform` succeeds, what happens? The sequential pipeline hid this by crashing at the first failure. The DAG forces you to confront **partial failure and error topology** — a design problem the original didn't have to answer because execution order suppressed it.

---

### The Conservation Law

> **The total complexity of {dependency structure + error topology + effect boundaries + control flow} is conserved across pipeline designs. Making any subset explicit forces the remainder implicit; making all explicit forces error handling strategy to become a new first-class design problem.**

The original had D, P, O, E all implicit. The inversion makes D, P, O explicit — and E surfaces as the new impossibility. The *sum of what must be designed* doesn't decrease; it transforms.

---

### Prediction About a Third Design

**Railway-Oriented Programming (Result monad chain):**

```python
def process(data, config):
    return (Ok(data)
        .bind(lambda d: validate(d, config.rules))
        .bind(lambda d: transform(d, config.mappings))
        .bind(lambda d: enrich(d, fetch_external(config.sources)))
        ...)
```

**Concrete, testable prediction:** This design will implicitly re-solve ordering (monadic bind encodes sequence) and partially solve error handling (short-circuit on `Err`). But the conservation law predicts it will **recreate the parallelism impossibility** — `fetch_external` will be forced sequential with `validate/transform` again because `.bind()` is inherently sequential. Moreover, the *kind* of error handling it provides (short-circuit) will actively prevent the partial-failure topology the DAG made explicit.

**Test:** Implement Railway-oriented programming on this pipeline. Measure whether `fetch_external` can execute concurrently with `validate/transform` without breaking the monadic structure. The conservation law predicts it cannot — and that any attempt to add concurrency will require breaking out of the monad entirely, recreating the explicit seam that the second improvement introduced.

The law holds: the complexity doesn't vanish. It migrates.
fication burden. We have elevated it: the contract language itself becomes the new implicit, globally-coordinated, locally-unverifiable system.

---

## XI. The Conservation Law

> **Verification Burden is Conserved.**
>
> In a sequential transformation pipeline, the total burden of ensuring correctness is invariant under refactoring. It can be *moved* between levels of abstraction — from the pipeline to the stages, from the stages to the contracts, from the contracts to the contract language — but it cannot be *eliminated*. Every design that achieves local verifiability at level N creates global unverifiability at level N+1.

| Design | What Is Local | What Is Global / Unverifiable |
|---|---|---|
| Original pipeline | Nothing | Pipeline correctness |
| Typed stage list | Type structure | Semantic contracts |
| Self-verifying stages | Stage behavior | Inter-contract implication |
| (Predicted third design) | Contract implication | *Graph topology* |

---

## XII. The Concrete, Testable Prediction

**Third design not attempted:** A **dataflow graph** — stages as DAG nodes, edges as typed contracts — which allows parallel execution, stage reordering, and formal contract composition along edges.

**The prediction:**

> In any dataflow graph implementation of this pipeline, there exists at least one graph configuration that is **topologically valid** (all edge contracts are satisfied) but **semantically incorrect** (produces wrong results for some input class). The count of such configurations grows monotonically with the number of edges whose input and output contract types are symmetric (i.e., stages that accept and produce the same abstract type).

**Why the conservation law generates this prediction:** The graph design achieves local stage verifiability *and* formally composable edge contracts. Per the conservation law, this moves the burden to the next level: the *topology itself* — which edges exist, in which direction — becomes the new unspecified global state. Symmetric contracts make topology ambiguous: a stage that accepts and produces `RecordSet` can be inserted anywhere, and the graph validator will approve it, while the semantics break.

**How to test it:** Take any real dataflow pipeline framework (Apache Beam, Luigi, Prefect). Define stages with symmetric input/output types. Enumerate valid topological configurations. Count configurations that produce incorrect output on a known test case. The conservation law predicts: this count is always greater than zero, and is proportional to the number of symmetric-contract stages. 

The impossibility has not moved. It has changed shape.
