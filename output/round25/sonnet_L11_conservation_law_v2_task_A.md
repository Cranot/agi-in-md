## Pattern Identification

This is a **linear transformation pipeline** — each step consumes the previous output and a slice of `config`. Clean-looking, readable, common.

---

## The Falsifiable Claim

> **`config` is a god object that hides 7 independent dependencies behind one parameter, making the pipeline's real coupling invisible.**

Three experts contest this:

**Defense:** Confirmed. `config.rules`, `.mappings`, `.sources`, `.filters`, `.group_key`, `.agg_func`, `.output_format` are seven distinct concerns. You cannot unit test `transform` without constructing a full config object that also carries fields for every other stage. The signature lies.

**Attack:** Wrong target. God-config is a symptom. The real problem is `fetch_external(config.sources)` — inline I/O embedded as an argument to `enrich`. Every other step is a pure transformation. One step is a network call. The visual symmetry of the variable chain hides a category error: **side effects are not transformation steps**.

**Probe:** Both of you assume the stage ordering is correct. Why does filtering happen *after* enrichment? If filters eliminate 80% of records, you're enriching data you'll discard. You both also assume the pipeline must be a single function. What if different callers need validate→transform but not aggregate→format? The ordering is hardcoded; it's not a design decision — it's an accident of the first implementation.

**Claim transforms.** The original claim (god-config) was a surface symptom. The transformed claim:

> **The function conflates pure transformation with effectful I/O, and hardcodes a pipeline topology that encodes undocumented assumptions about ordering, as though these were the same kind of thing.**

---

## The Concealment Mechanism

**Linear variable chaining with symmetric naming.**

Every line reads `x = f(prev, config.something)`. This visual symmetry makes all seven steps look equivalent. `fetch_external(config.sources)` is hidden *as an argument* to `enrich` rather than as a separate line — it never gets a variable name, never appears in the left-hand column. The eye reads seven assignments and concludes there are seven equivalent transformations. There are six transformations and one I/O operation.

---

## Improvement 1: Legitimate-Looking, Deepens the Concealment

```python
def process(data, config):
    pipeline = [
        lambda d: validate(d, config.rules),
        lambda d: transform(d, config.mappings),
        lambda d: enrich(d, fetch_external(config.sources)),
        lambda d: apply_filters(d, config.filters),
        lambda d: group_by(d, config.group_key),
        lambda d: aggregate(d, config.agg_func),
        lambda d: format_output(d, config.output_format),
    ]
    return functools.reduce(lambda d, f: f(d), pipeline, data)
```

This **passes code review.** It looks like functional programming done right: explicit pipeline structure, composable stages, easy to add/remove steps, visually uniform.

**Three properties only visible because I tried to strengthen it:**

1. **`fetch_external` is now completely invisible.** It's buried inside a lambda with no variable name, no call site in the function body. The original code was bad; this is worse.

2. **The closures capture all of `config`, not just the relevant slice.** `lambda d: validate(d, config.rules)` closes over the entire config object. The god-object problem is structurally identical but now sealed inside a closure — it can't even be inspected at runtime without introspection tricks.

3. **The stages aren't actually composable.** They look like `data → data` functions, but each is a partial application of a two-argument function with config as the hidden fixed argument. Reordering the list doesn't reorder the pipeline — it reorders the *application* of config slices. These are not interchangeable steps.

---

## What Improvement 1 Conceals and Recreates

**Conceals:** That `fetch_external` is called exactly once, eagerly, per pipeline execution — not per record, not lazily. It looks like a uniform step. It isn't.

**Recreates the original problem:** The pipeline topology appears flexible (it's a list, you can append/remove) but isn't — the lambdas close over `config` at definition time. I've made the pipeline look configurable while making it more rigid. The appearance of flexibility deepens the illusion.

---

## Improvement 2: Addresses the Recreated Property

```python
def process(data, config, *, external_data=None):
    if external_data is None:
        external_data = fetch_external(config.sources)

    validated   = validate(data, config.rules)
    transformed = transform(validated, config.mappings)
    enriched    = enrich(transformed, external_data)
    filtered    = apply_filters(enriched, config.filters)
    grouped     = group_by(filtered, config.group_key)
    aggregated  = aggregate(grouped, config.agg_func)
    formatted   = format_output(aggregated, config.output_format)
    return formatted
```

I/O is now **injectable** (testable, mockable, pre-fetchable). The side effect is explicit at the call site. This is genuinely better.

**What this improvement conceals:** The ordering problem. Making I/O injectable solves testability but the topology remains hardcoded. What's now visible is that the pipeline is **atomic** — you cannot partially execute it. If a caller needs validate→transform without enrich→aggregate, they can't have it without duplicating logic. The pipeline has no seams.

---

## The Structural Invariant

Through every version — original, lambda pipeline, injectable I/O — this property persists:

> **Each stage has two independent dependency types: a data dependency (output of the previous stage) and a config dependency (external to the pipeline). No refactoring of the pipeline-as-a-function can make both simultaneously visible, because the function signature must privilege one as "primary argument" and hide the other.**

This isn't about style. It's structural: a pipeline *is* a partial application of a dependency graph. Partial application always hides the unapplied dimensions.

---

## Inversion: Make the Invariant Trivially Satisfiable

Make stages self-contained objects that carry their own config, so data flow is the *only* visible dependency:

```python
@dataclass
class Pipeline:
    stages: list[Callable[[Any], Any]]

    def run(self, data: Any) -> Any:
        return functools.reduce(lambda d, s: s(d), self.stages, data)

# Construction separates configuration from execution:
pipeline = Pipeline([
    Validator(config.rules),
    Transformer(config.mappings),
    Enricher(external_data),          # I/O resolved before construction
    Filter(config.filters),
    Grouper(config.group_key),
    Aggregator(config.agg_func),
    Formatter(config.output_format),
])
result = pipeline.run(data)
```

Config coupling is now invisible at the pipeline level — each stage is opaque. Data flow is fully explicit. Ordering is inspectable and genuinely reconfigurable.

**The new impossibility:** You cannot vary pipeline topology based on data. You cannot say "skip enrichment if the record already has external fields" without either (a) baking conditional logic inside a stage (hiding the topology change) or (b) constructing a different pipeline before calling `run` (requiring the caller to inspect data before the pipeline runs, breaking the abstraction). **Stages communicate only through data, and the runner never inspects intermediate results.** The pipeline is now statically committed at construction time.

---

## The Conservation Law

**Original impossibility:** You cannot simultaneously expose data-flow lineage and config provenance in a flat function — one must be implicit.

**Inverted impossibility:** You cannot simultaneously expose pipeline topology and data-dependent branching in an object pipeline — one must be implicit.

> **Conservation Law: In a transformation pipeline, structural explicitness is conserved across three orthogonal axes — data lineage, configuration provenance, and conditional topology. Every refactoring that increases explicitness on one axis decreases it on at least one other. This is not a readability/flexibility trade-off. It is a consequence of the fact that a pipeline is a projection of a dependency graph: each interface exposes one dimension of the graph while collapsing the others.**

---

## What This Reveals That a Senior Engineer Wouldn't Already Know

A senior engineer knows: inject your I/O, avoid god objects, make pipelines composable. They treat these as independent improvements.

**What the law reveals:** These axes are not independent. They are projections of the same underlying dependency graph onto different interfaces. Optimizing one projection necessarily degrades another. This is why "refactor the pipeline" feels like whack-a-mole — you're not fixing problems, you're rotating which dimension of the graph is currently hidden.

---

## Prediction About a Third Design

A team encountering this will eventually reach for a **pipeline framework** — Apache Beam, Luigi, Prefect, or a custom DAG runner with decorators. The prediction:

> **A framework-based solution does not break the conservation law — it exports the hidden dimension into the framework's DSL or configuration layer.**

Data lineage becomes explicit in the DAG. Config provenance becomes explicit in task parameters. Conditional topology becomes explicit in branching operators.

But now reasoning about *what the pipeline actually does* requires consulting three separate systems: the code, the DAG definition, and the framework's execution model. The hidden dimension hasn't been eliminated — it has **migrated outside the codebase**, where it is harder to test, harder to trace, and invisible to static analysis.

The conservation law predicts this failure mode before the framework is chosen.
