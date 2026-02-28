## Structural Analysis: `process()`

### The Pattern

This is a **linear transformation pipeline** — each step consumes the previous step's output, with all configuration injected from a single `config` object. It's readable, sequential, and has an obvious test surface. It also has a deep structural problem.

---

## THE CLAIM

> **The function's deepest structural problem is that the pipeline definition is split across two locations — `config` (which carries *what* each step does) and the function body (which carries *which steps* and *in what order*) — such that neither location alone contains a complete, inspectable description of the pipeline. The topology is a hidden third artifact that exists nowhere explicitly.**

**Falsifiable form:** If you can modify the pipeline's step sequence, skip a step, or inspect the full pipeline structure without modifying the function body, the claim is wrong.

---

## THREE EXPERT TEST

**Expert A — Defender:**
The claim holds precisely. `config` carries `rules`, `mappings`, `sources`, `filters`, `group_key`, `agg_func`, `output_format` — that's seven operational parameters. The function body carries seven steps in fixed order. Neither location answers: *"what is this pipeline?"* You can't unit-test the topology. You can't inspect it at runtime. If the business requirement changes from `filter → group` to `group → filter`, you modify the function body — but nothing in the type system, config structure, or documentation captures that this is a meaningful change.

**Expert B — Attacker:**
The split-representation claim is too abstract to be actionable. The *real* structural problem is urgent and concrete: `fetch_external(config.sources)` is called **inline**, inside the middle of what looks like a pure transformation chain. I/O is embedded at position 3 of 7. This is a testability emergency — you cannot run this function without hitting the network. Every other step is a pure transform; this one isn't, and nothing marks it as different. The topology claim is an aesthetic concern. The I/O embedding is a correctness concern.

**Expert C — Probing assumptions both share:**
Both of you assume `config` is passive data. But look at what `config` actually holds: the complete operational specification of every step. `config` *is* the pipeline definition — it's just expressed as parameters rather than as a sequence of operations. Both improvements you'd propose would be attempts to reunify what the original design split apart. But you're both also assuming the pipeline *should* be a runtime artifact at all. What if this pipeline's topology is a compile-time fact — a fixed domain process — that we're mistakenly trying to make flexible?

---

## CLAIM TRANSFORMATION

| | Claim |
|---|---|
| **Original** | Pipeline sequencing is hardcoded instead of explicit |
| **After debate** | The pipeline definition is *split* — topology lives in the function body, parameters live in config, and the complete pipeline description lives nowhere |
| **After probing** | `config` is simultaneously *passive data* (a bag of parameters) and *active specification* (it contains everything needed to define the pipeline). The design hasn't committed to either role, so it's stuck doing both badly |

**The gap:** The original claim was about *location* of sequencing. The transformed claim is about an **unresolved identity crisis in the config object itself**.

---

## THE CONCEALMENT MECHANISM

**Parameter Distribution Concealment**

The function hides its structural ambiguity by distributing the pipeline definition across two namespaces that each look complete and coherent in isolation:

- `config` looks like clean dependency injection — passive, data-like, testable
- The function body looks like clean orchestration — readable, sequential, obvious

Neither location looks wrong. Together they constitute a pipeline definition that is untestable as a whole, unmodifiable without touching the function, and invisible to any runtime inspection. The cleanliness of each part conceals the incompleteness of both.

---

## IMPROVEMENT 1: DEEPENS CONCEALMENT (passes review)

```python
def process(data, config):
    """
    Executes the standard processing pipeline.
    Steps: validate → transform → enrich → filter → group → aggregate → format
    """
    steps = [
        ("validate",   lambda d: validate(d, config.rules)),
        ("transform",  lambda d: transform(d, config.mappings)),
        ("enrich",     lambda d: enrich(d, fetch_external(config.sources))),
        ("filter",     lambda d: apply_filters(d, config.filters)),
        ("group",      lambda d: group_by(d, config.group_key)),
        ("aggregate",  lambda d: aggregate(d, config.agg_func)),
        ("format",     lambda d: format_output(d, config.output_format)),
    ]
    result = data
    for name, step in steps:
        result = step(result)
    return result
```

**Why it passes review:** Named steps, explicit list structure, documented order, separated definition from execution. Looks more "data-driven."

**Why it deepens concealment:** Each lambda captures `config` via closure — the config dependencies are now *less* visible than before, buried inside anonymous functions. The list *looks* like it could be reordered or subsetted (false affordance). `fetch_external` is more hidden than ever, enclosed in a lambda that looks identical to the pure-transform lambdas.

---

## THREE PROPERTIES VISIBLE ONLY FROM TRYING TO STRENGTHEN IT

**1. `config` is an indivisible monolith.**
Writing the lambda list forces you to notice: `config` must be fully constructed before any lambda executes. You cannot build a partial pipeline from partial config. This was hidden in the original because `config.x` scattered across a function body doesn't reveal its atomicity. The list form makes it visible: all-or-nothing.

**2. `fetch_external` has a categorically different lifecycle.**
When you list all seven steps, the I/O step becomes visually incongruous — it's the only one that reaches outside the process boundary. The lambda conceals this, but the act of listing them exposes the category error to anyone constructing this list. The pipeline isn't uniform; it has a seam.

**3. The steps are not fungible.**
The list structure implies swappability. Attempting to actually swap steps reveals a hidden **type chain**: `validate` must produce what `transform` expects; `transform` must produce what `enrich` expects; and so on. The steps aren't items in a list — they're links in a typed composition chain. The list metaphor is a lie the data structure tells about itself.

---

## IMPROVEMENT 2: CONTRADICTS IMPROVEMENT 1 (also passes review)

```python
@dataclass
class PipelineConfig:
    rules: Any
    mappings: Any
    sources: Any
    filters: Any
    group_key: str
    agg_func: Callable
    output_format: str

    def build_pipeline(self, data):
        """Config owns its own execution strategy."""
        external_data = fetch_external(self.sources)   # I/O lifted out of hot path
        steps = [
            lambda d: validate(d, self.rules),
            lambda d: transform(d, self.mappings),
            lambda d: enrich(d, external_data),        # pure from here
            lambda d: apply_filters(d, self.filters),
            lambda d: group_by(d, self.group_key),
            lambda d: aggregate(d, self.agg_func),
            lambda d: format_output(d, self.output_format),
        ]
        return reduce(lambda acc, f: f(acc), steps, data)

def process(data, config):
    return config.build_pipeline(data)
```

**Why it passes review:** `process()` is now trivially simple. `fetch_external` is called once at build time, not inline — I/O is cleanly separated from transformation. Config knows about its own execution strategy, which is coherent domain encapsulation.

**Why it contradicts Improvement 1:**

| | Topology ownership | Config role |
|---|---|---|
| **I1** | Function body | Passive (parameters only) |
| **I2** | Config object | Active (defines its own pipeline) |

They're opposite answers to: *who is responsible for knowing the pipeline structure?*

---

## THE STRUCTURAL CONFLICT

**The ownership ambiguity of pipeline topology.**

Both improvements are legitimate because the original code left a genuine design question unresolved: *is `config` passive data or active specification?*

- If `config` is passive → topology belongs in the function → Improvement 1's direction
- If `config` is active → topology belongs in config → Improvement 2's direction

The conflict is real because `config` currently holds *both roles simultaneously*, and each improvement is a consistent resolution of the ambiguity in one direction. The conflict exists only because both improvements are legitimate — if one were clearly wrong, there'd be no conflict, just a mistake.

---

## IMPROVEMENT 3: RESOLVES THE CONFLICT (passes review)

```python
from functools import partial
from typing import Callable

class Pipeline:
    """Explicit, inspectable pipeline as a first-class object."""

    def __init__(self, steps: list[tuple[str, Callable]]):
        self._steps = steps

    def run(self, data):
        result = data
        for _name, step in self._steps:
            result = step(result)
        return result

    def step_names(self) -> list[str]:
        return [name for name, _ in self._steps]

    @classmethod
    def from_config(cls, config: PipelineConfig) -> "Pipeline":
        external_data = fetch_external(config.sources)   # I/O at construction
        return cls([
            ("validate",   partial(validate,      rules=config.rules)),
            ("transform",  partial(transform,     mappings=config.mappings)),
            ("enrich",     partial(enrich,        external=external_data)),
            ("filter",     partial(apply_filters, filters=config.filters)),
            ("group",      partial(group_by,      key=config.group_key)),
            ("aggregate",  partial(aggregate,     func=config.agg_func)),
            ("format",     partial(format_output, fmt=config.output_format)),
        ])

def process(data, config):
    return Pipeline.from_config(config).run(data)
```

**Why it satisfies both:**
- `process()` is trivially simple ✓ (I1's spirit)
- `config` is passive; `Pipeline` owns topology ✓ (I1's direction)
- `fetch_external` is called at construction time, not inline ✓ (I2's fix)
- The pipeline is now an inspectable, named, first-class object ✓ (new gain)

---

## HOW IT FAILS

**`Pipeline.from_config` is still a hardcoded 7-step sequence with better syntax.**

The `Pipeline` class *looks* like an abstraction over pipeline topology, but `from_config` simply reconstructs the same fixed sequence using `partial` instead of lambdas. Concretely:

- You cannot create a 5-step or 8-step pipeline using this `Pipeline` class without modifying `from_config`
- The step names are decorative — nothing in the system uses them to enforce order, detect conflicts, or enable partial execution
- `partial()` requires knowing every downstream function's keyword signature — `from_config` is now tightly coupled to the internal API of `validate`, `transform`, `enrich`, and every other function
- The class creates the visual impression of a general-purpose pipeline engine but it's a specific 7-step process in a trench coat

The improvement *moved* the hardcoding without *eliminating* it.

---

## WHAT THE FAILURE REVEALS ABOUT THE DESIGN SPACE

The conflict asked: *who owns the topology?*
The failure reveals: **the topology is not a runtime fact. It's a type-level fact. All three improvements failed because they tried to treat a compile-time constraint as a value.**

Each step has a specific output type that is the next step's required input type. This is a **linear type chain** — a sequence of type-level constraints. It cannot be safely represented as a `list[Callable]` without losing those constraints. The list suggests the steps are interchangeable; they are not. The `partial` wrappers suggest the steps are uniform; they are not.

The design space the conflict alone could not reveal:

```
┌─────────────────────────────────────────────────────────────┐
│              THE ACTUAL SOLUTION SPACE                      │
│                                                             │
│  Option A: Typed composition chain                          │
│    Make the type constraints explicit. Each step returns    │
│    a typed result that constrains what can follow.          │
│    Cost: verbose in Python; requires Protocol/TypeVar work  │
│                                                             │
│  Option B: Genuine runtime plugin system                    │
│    Accept loss of type safety. Steps register themselves,   │
│    declare input/output contracts, runtime validates.       │
│    Cost: you're building middleware infrastructure          │
│                                                             │
│  Option C: Accept the hardcoding                            │
│    This pipeline IS a fixed domain process. The topology    │
│    is not a variable. Stop trying to make it flexible.      │
│    Cost: nothing — this is the honest design                │
└─────────────────────────────────────────────────────────────┘
```

The original concealment — splitting the pipeline definition across `config` and the function body — was accidentally protecting us from a harder truth: **this pipeline's topology is a domain invariant, not a configuration variable.** Every improvement that tried to make the topology more "explicit" or "flexible" was fighting the domain.

The concealment mechanism wasn't hiding bad code. It was hiding a **category error** — the assumption that a fixed domain process should be architecturally treated as a configurable pipeline.

The `process` function, warts and all, may be the most honest version of itself.
