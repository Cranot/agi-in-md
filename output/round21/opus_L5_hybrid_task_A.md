# Analysis: Linear Pipeline (Pipes and Filters)

## The Pattern

This is a **sequential transformation pipeline** — the Pipes and Filters architectural pattern expressed as imperative variable chaining. Each step consumes the prior step's output plus one facet of a `config` god-object.

---

## Three Operations Derived From This Code's Specific Properties

Before executing, my **prediction**: Operation 2 (Failure Modes) will yield the deepest insight, because there's a hidden side effect (`fetch_external`) that breaks the otherwise pure chain — subtle and production-dangerous.

---

### Operation 1 — Coupling Analysis

Every line has **dual coupling**: data flows linearly, but `config` fans out to all 7 steps.

```
data ──→ step1 ──→ step2 ──→ step3 ──→ ... ──→ result
             ↑         ↑         ↑
          config.a   config.b  config.c  ...  (7 attributes)
```

**Implications:**
- **`config` is a god object.** It knows about every stage. You can't run a subset without a fully-populated config.
- **The signature `(data, config)` lies.** The real arity is ~9 logical parameters hidden behind one bundle.
- **Testability suffers.** Testing step 5 alone requires mocking the output of steps 1–4 *and* a config with the right attributes.

---

### Operation 2 — Failure Mode Analysis

```python
enriched = enrich(transformed, fetch_external(config.sources))  # ← HERE
```

- **`fetch_external` is a side effect buried mid-pipeline.** The function *looks* pure but isn't.
- If `fetch_external` fails at step 3, work from steps 1–2 is **wasted with no recovery path**.
- If step 5 fails, you **can't retry from step 5** without re-fetching external data.
- **Zero observability** — no per-step timing, logging, or error context without editing every line.
- No partial results. Step 7 fails? You get nothing.

---

### Operation 3 — Composability / Extensibility Analysis

This is the most rigid arrangement of a pipeline possible:

| Want to...              | Cost                                             |
|------------------------|--------------------------------------------------|
| **Add** a step          | Edit function body, insert variable, rewire chain |
| **Reorder** steps       | Manual editing; risk breaking shape contracts     |
| **Skip** a step         | Add conditional logic inline                     |
| **Branch** the pipeline | Duplicate or conditionalize the entire function   |
| **Reuse** steps 1–2     | Copy-paste                                       |

The pipeline **is not a data structure**. It's hardcoded control flow. It violates Open/Closed.

---

## Inversion: Was My Prediction Right?

**Partially wrong.** Operation 2 found the important hidden side effect, but **Operation 3 reveals the root cause**. The failure mode problems are *consequences* of structural rigidity — if the pipeline were composable, you could insert retry/checkpoint/logging middleware around any step for free. I over-weighted the "sneaky bug" and under-weighted the architectural leverage of composability.

**Blind spot revealed:** I gravitated toward the *symptom* (side effect) over the *structure* (non-composable pipeline), even though structure-first thinking should have prioritized the opposite.

---

## What I'd Change

Make the pipeline **a data structure**, not imperative code:

```python
from functools import reduce
from typing import Callable, Any

# Each step: (name, function that takes (data, context) -> data)
def build_pipeline(config) -> list[tuple[str, Callable]]:
    return [
        ("validate",   lambda d, _: validate(d, config.rules)),
        ("transform",  lambda d, _: transform(d, config.mappings)),
        ("enrich",     lambda d, ctx: enrich(d, ctx["external"])),
        ("filter",     lambda d, _: apply_filters(d, config.filters)),
        ("group",      lambda d, _: group_by(d, config.group_key)),
        ("aggregate",  lambda d, _: aggregate(d, config.agg_func)),
        ("format",     lambda d, _: format_output(d, config.output_format)),
    ]

def run_pipeline(data, config, observers=None):
    # Side effects are explicit and hoisted out
    ctx = {"external": fetch_external(config.sources)}

    pipeline = build_pipeline(config)
    result = data
    for name, step in pipeline:
        result = step(result, ctx)          # core execution
        if observers:                        # free observability hook
            for obs in observers:
                obs(name, result)
    return result
```

**What this buys you — all three problems at once:**

| Problem | Solution |
|---|---|
| **Coupling** | Each step is an independent callable; `config` is closed over at build time |
| **Failure modes** | Side effect (`fetch_external`) is **hoisted and explicit**; add try/retry/checkpoint per step trivially |
| **Composability** | Steps are a list — filter, reorder, conditionally include, compose sub-pipelines, all with list operations |

The deeper principle: **when your code _is_ a pipeline, represent it _as_ a pipeline.** The original code encoded structure in control flow, which made every cross-cutting concern (logging, retries, reordering, testing) require editing the core function.
