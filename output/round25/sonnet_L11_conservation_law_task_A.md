## Structural Pattern

This is a **linear sequential pipeline** — each step consumes the previous step's output, with a shared `config` object providing parameters throughout. Classic ETL/transformation chain.

---

## The Diagnostic

### Fa    -> Done (129s) -> 181 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/sonnet_L11_conservation_law_task_A.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
filter→group→aggregate→format) is a hardcoded policy masquerading as a data-driven process.

---

### Three Expert Challenge

**Defender:** Correct. The god object hides a structural decision. You can't skip, reorder, or compose steps without editing the function body. The config provides leaf-node flexibility while topology is completely rigid.

**Attacker:** Wrong target. `fetch_external(config.sources)` is called inline with no error handling — a network call buried in a pipeline with zero fault tolerance. The god object is a style complaint; the missing error boundary is what kills this in production.

**Probe:** Both of you assume this *should be a function*. The defender wants better topology parameterization; the attacker wants better error handling *within* the function. Neither asks whether all seven steps belong in a single callable unit at all. The function boundary itself is the concealed assumption.

---

### The Claim Transforms

The original claim (god object) is a symptom. The transformed claim:

> **The function treats pipeline topology as a constant when topology is actually a variable. By encoding topology as sequential Python statements, it makes the shape of the pipeline invisible as a design decision — neither injectable, nor composable, nor auditable.**

The god object critique, the missing error handling, and the function-boundary question are all *downstream* of this single root: **topology is hardcoded inside the function body**.

---

### Concealment Mechanism: Nominal Parameterization

The function accepts `config` as a parameter — this *signals* configurability. But the configuration only reaches leaves (how each step runs), never structure (which steps run, in what order). Surface-level flexibility conceals structural rigidity.

The variable names participate too: `validated`, `transformed`, `enriched`, `filtered`, `grouped`, `aggregated`, `formatted` describe the *state of data* at each point, which naturalizes the sequence as the only reasonable one — it reads as *inevitable* rather than *chosen*.

---

### Improvement 1: Legitimate-Looking, Deepens Concealment

```python
def process(data, config):
    pipeline = [
        partial(validate,      config.rules),
        partial(transform,     config.mappings),
        lambda d: enrich(d, fetch_external(config.sources)),
        partial(apply_filters, config.filters),
        partial(group_by,      config.group_key),
        partial(aggregate,     config.agg_func),
        partial(format_output, config.output_format),
    ]
    result = data
    for step in pipeline:
        result = step(result)
    return result
```

This passes code review immediately. "Pipeline is now a first-class list — composable, extendable, readable." But topology is still constructed inside the function body, on every call, producing the same structure every time. The list form makes the hardcoding *look* data-driven because lists feel malleable. The concealment deepens.

---

### Three Properties Visible Only Because We Tried to Strengthen It

1. **Topology is constructed at call time but is never variable.** The `pipeline = [...]` literal reveals that *defining* the pipeline and *running* it happen in the same breath, with no separation. This distinction was invisible in the sequential form.

2. **`config` is structurally seven objects.** With `partial` calls laid bare in a list, it's visually obvious that each step independently binds a different slice of `config`. The god object problem moves from implicit to explicit.

3. **`enrich` is categorically different from every other step.** Six steps follow `partial(fn, config.X)`; `enrich` requires a lambda because `fetch_external` is I/O that must execute *inside* the pipeline, not at construction time. The list form surfaces this exception; the sequential form buries it.

---

### Improvement 2: Address the Recreated Property

The recreated property: topology defined inside the function body is impossible to inject from outside.

```python
DEFAULT_PIPELINE = [
    ('validate',   lambda d, cfg: validate(d, cfg.rules)),
    ('transform',  lambda d, cfg: transform(d, cfg.mappings)),
    ('enrich',     lambda d, cfg: enrich(d, fetch_external(cfg.sources))),
    ('filter',     lambda d, cfg: apply_filters(d, cfg.filters)),
    ('group',      lambda d, cfg: group_by(d, cfg.group_key)),
    ('aggregate',  lambda d, cfg: aggregate(d, cfg.agg_func)),
    ('format',     lambda d, cfg: format_output(d, cfg.output_format)),
]

def process(data, config, pipeline=DEFAULT_PIPELINE):
    result = data
    for name, step in pipeline:
        result = step(result, config)
    return result
```

Topology is now injectable. You can pass a custom pipeline. This looks genuinely clean.

**What it conceals:** Every step still takes `(data, cfg)` — the full config is threaded through every step even though each step uses exactly one attribute. Making topology external revealed that the configuration coupling was never a topology problem at all. The god object is still there, now threaded explicitly through each step signature.

**What property of the original problem is visible only because this improvement recreates it:**

> Each step's dependency on global `config` is now visually explicit in every lambda. The coupling was always there — every improvement just makes it more obvious that it cannot be removed by rearranging the pipeline.

---

### The Structural Invariant

Through every improvement, one property persists:

> **Each step requires a slice of centralized configuration, and no restructuring of the pipeline's topology can eliminate this coupling — because it is a property of the problem, not the implementation.**

Seven steps, seven distinct configuration concerns, one `config` object. You can make the topology flexible, external, injectable, or composable — but you cannot change the fact that *configuration knowledge is centralized and execution is decentralized*. Every improvement just moves this tension around.

---

### Invert the Invariant

Make configuration self-locating: each step carries its own.

```python
@dataclass
class ValidateStep:
    rules: RuleSet
    def __call__(self, data): return validate(data, self.rules)

@dataclass
class TransformStep:
    mappings: MappingSet
    def __call__(self, data): return transform(data, self.mappings)

@dataclass
class EnrichStep:
    sources: SourceConfig
    def __call__(self, data): return enrich(data, fetch_external(self.sources))

# ... remaining steps follow same pattern

@dataclass
class Pipeline:
    steps: list[Callable[[Any], Any]]
    
    def process(self, data: Any) -> Any:
        return reduce(lambda d, step: step(d), self.steps, data)
```

Topology is now trivially injectable. Configuration is decentralized. The god object is gone. The original impossibility — flexible topology — is trivially satisfied.

---

### The New Impossibility the Inversion Creates

**Cross-step configuration coherence becomes unenforceable.**

In the original, `config` was a single object — you could validate internally that `group_key` is compatible with `agg_func`, that `output_format` is consistent with `mappings`. In the inverted design, each step's configuration is encapsulated and independent. There is no single locus of configuration truth, no single place to ask "does this pipeline make sense as a whole?"

More operationally: **you cannot change any configuration without reconstructing step objects and potentially the entire pipeline**. The original let you swap `config` and call `process()` again. The inversion requires rebuilding the object graph.

---

## The Conservation Law

| Design | Topology Opacity | Configuration Coupling | Coherence Cost |
|--------|-----------------|----------------------|----------------|
| Original | Low (readable sequence) | High (hidden god object) | Zero (single object) |
| Improvement 1 | Medium (list, looks flexible) | High (explicit in partials) | Zero |
| Improvement 2 | Low (injectable) | High (threaded explicitly) | Zero |
| Inverted | Zero (fully external) | Zero (decentralized) | **High (no global view)** |

**The conservation law:**

> **The total information required to understand a pipeline's behavior is conserved across all architectural decisions. It can be centralized (god object: coherence is free, topology is rigid), distributed (step objects: topology is free, coherence is expensive), or hidden (sequential statements: topology reads naturally, coupling is invisible). No design eliminates the complexity — every design decides where to put it.**

Formally: `topology_opacity + configuration_coupling + coherence_enforcement_cost = constant`.

The original code chose to make topology obvious and pay with a hidden god object. The inverted design makes topology and coupling trivial but creates a new problem: a pipeline of self-contained steps has no way to know if it makes sense.

**The finding:** This function's problem isn't fixable by improving the function. It's a manifestation of a conservation law in pipeline design — the same total complexity will always reappear somewhere. The productive question isn't "how do I fix `process()`" but "which form of this complexity does my system's maintenance model handle best?"
