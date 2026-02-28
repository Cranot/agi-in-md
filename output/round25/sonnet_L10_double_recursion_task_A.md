## The Pattern and Its Real Problem

This is a **linear transformation pipeline**. Each step maps `data → data`, threaded through a single `config` object. Clean, readable, and deeply misleading about its own structure.

---

## Falsifiable Structural Claim

> **The deepest structural problem is that `fetch_external(config.sources)` embeds an I/O side effect at pipeline step 3 of 7, making the function's failure modes, testability, and purity all dependent on a network call that is completely invisible at the function signature.**

Falsifiable test: Can you call `process(data, config)` without network access? No. Does the signature reveal this? No.

---

## Three Expert Challenge

**Expert A (defends):** `fetch_external` is the structural landmine. Every other step is a pure transformation. Step 3 smuggles in non-determinism. A caller reading `process(data, config)` has no idea a network request fires. This is *concealment by embedding*.

**Expert B (attacks):** `fetch_external` is a symptom, not the root. The deepest problem is `config` — a **god-object** that encodes the entire pipeline's behavior across seven independent fields, with no structural enforcement that any of them are valid or mutually consistent. You discover config failures at runtime, at the specific step that consumes the broken field. `fetch_external` is just the noisiest failure mode, not the deepest one.

**Expert C (probes what both take for granted):** Both experts assume the sequential structure is the right abstraction. Neither questions *why this is one function*. Both assume steps are linearly dependent (each fully resolves before the next begins) and that `config` is a coherent unit. Neither asks: is this actually a DAG? Could `filter` run before `enrich`? Should it? The linear structure is itself a claim about the dependency topology — an unexamined claim.

---

## Claim Transformation

**Original:** There is a hidden side effect at step 3.

**Transformed:** The linear pipeline structure actively misrepresents the actual dependency topology. Steps depend on *different parts* of config in different ways. Some are pure, some are effectful. Some could be reordered or parallelized. The sequential syntax conceals all of this by making every step look structurally identical.

**The gap:** I started with "there's a hidden I/O call" and arrived at "the entire structure hides its own dependency graph."

**The concealment mechanism:** **Sequentialism as topology-hiding.** By expressing a dependency graph as a linear sequence, the code makes itself look simpler than it is and makes all structural asymmetries invisible.

---

## Improvement That Deepens Concealment

```python
class Pipeline:
    def __init__(self, config):
        self.config = config
        self.steps = [
            ('validate',   self._validate),
            ('transform',  self._transform),
            ('enrich',     self._enrich),      # <-- fetch_external is now 3 levels deep
            ('filter',     self._filter),
            ('group',      self._group),
            ('aggregate',  self._aggregate),
            ('format',     self._format),
        ]

    def run(self, data):
        result = data
        for name, step in self.steps:
            result = step(result)
        return result

    def _validate(self, data):   return validate(data, self.config.rules)
    def _transform(self, data):  return transform(data, self.config.mappings)
    def _enrich(self, data):     return enrich(data, fetch_external(self.config.sources))
    def _filter(self, data):     return apply_filters(data, self.config.filters)
    def _group(self, data):      return group_by(data, self.config.group_key)
    def _aggregate(self, data):  return aggregate(data, self.config.agg_func)
    def _format(self, data):     return format_output(data, self.config.output_format)
```

This **passes code review** because: it's properly OOP, steps are enumerable and named, `run()` is clean and generic, the class is "extensible," it looks like the textbook refactoring.

**It deepens concealment because:**
- `fetch_external` is now buried inside `_enrich` inside a class — you must read 7 methods to find the side effect
- `self.config` enshrines the god-object as structural state, not just a parameter
- The uniform `(name, callable)` step list makes all steps look *more* identical, flattening the pure/effectful distinction even further
- `run()` looks testable but still requires network access

---

## Three Properties Visible Only Through Strengthening

1. **The steps list is a structural lie.** Making steps enumerable as `(name, callable)` pairs reveals that the pipeline *treats all steps as equivalent units* — but they're not. Some are pure, some are effectful, some depend on one config field, some on several. Enumeration makes this asymmetry *more* invisible by giving it a uniform surface.

2. **Config coupling is load-bearing, not incidental.** Moving config to `self.config` showed that every single method depends on it, but on *different parts*. The god-object isn't removable without decomposing the pipeline. It's not a convenience — it's structural.

3. **The pipeline has no theory of failure.** By making `run()` look clean, I revealed there is no error handling, retry logic, or partial execution model. The improvement makes the pipeline look robust while making failure modes *less* visible than in the original flat function.

---

## Diagnostic Applied to the Improvement

**What does the Pipeline class conceal?** The `fetch_external` call is now 3 levels deep. The god-config is now `self.config` — structural state captured by every method. The loop makes pure and effectful steps syntactically identical.

**What property of the original is visible only because the improvement recreates it?**

In the original flat function, `fetch_external` was at least *visible at the call site*. The class buries it so thoroughly that you must inspect all 7 private methods to understand which ones have side effects. This reveals the invariant property:

> **The pipeline has no mechanism — structural or type-level — to distinguish between pure steps and effectful steps.**

They are all just `data → data` callables in the loop. The class made this *worse*, not better.

---

## Second Improvement: Address the Recreated Property

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class PureStep:
    name: str
    fn: Callable

@dataclass
class EffectfulStep:
    name: str
    fn: Callable
    effect_description: str  # forces declaration of the side effect

class Pipeline:
    def __init__(self, config):
        self.steps = [
            PureStep('validate',
                lambda d: validate(d, config.rules)),
            PureStep('transform',
                lambda d: transform(d, config.mappings)),
            EffectfulStep('enrich',
                lambda d: enrich(d, fetch_external(config.sources)),
                effect_description='network fetch: config.sources'),
            PureStep('filter',
                lambda d: apply_filters(d, config.filters)),
            PureStep('group',
                lambda d: group_by(d, config.group_key)),
            PureStep('aggregate',
                lambda d: aggregate(d, config.agg_func)),
            PureStep('format',
                lambda d: format_output(d, config.output_format)),
        ]

    def run(self, data):
        result = data
        for step in self.steps:
            result = step.fn(result)
        return result

    def effectful_steps(self):
        return [s for s in self.steps if isinstance(s, EffectfulStep)]
```

---

## Diagnostic Applied to the Second Improvement

**What does this conceal?**
- `run()` still treats `PureStep` and `EffectfulStep` identically — the distinction is *declared* but not *enforced*. Nothing prevents burying a network call in a `PureStep`.
- Config is now captured in closures — more tightly bound than ever, with no shared reference to inspect.
- `effect_description` is self-reported; there is no mechanism to verify it.

**What property of the original is visible because the improvement recreates it?**

The distinction between pure and effectful steps is declared in *type* but erased in *execution*. `run()` calls `step.fn(result)` regardless. This surfaces the real invariant:

---

## The Structural Invariant

> **In a parameterized pipeline, you cannot simultaneously have (a) encapsulated steps, (b) a minimal config interface, and (c) testable step isolation. You can have at most two.**

Every improvement made the same move: add structure to the *steps* while leaving *config* as a monolith — because decomposing config requires decomposing the pipeline, which requires answering the question the original function never asks:

**What is the unit of composition?**

The concealment mechanism at every level is **abstraction flattening**: expressing a parameterized transformation graph as a uniform sequence of `data → data` functions. This makes the function look simpler while hiding:
- The dependency topology (which steps depend on which config fields)
- The effect topology (which steps are pure, which are effectful)
- The execution topology (which steps could be parallelized, retried, or skipped)

This invariant is a property of the **problem space**, not the implementation. Any pipeline that (1) is sequentially composed, (2) is behaviorally parameterized through config, and (3) has heterogeneous step types will recreate this concealment — no matter how the code is organized — until the unit of composition is explicitly named and the config object is decomposed to match it.

---

**What to actually change:** Don't reorganize the pipeline. Decompose the config object so each step owns its own configuration type. Make effectful steps structurally distinct and pushed to the edges (inject `fetch_external`'s *result* as a parameter to `process`, not its *call*). Then ask whether the linear sequence is the right model at all, or whether you have a DAG.
