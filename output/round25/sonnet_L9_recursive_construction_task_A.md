## Structural Pattern: Linear Pipeline Coordinator

The function follows a **staged pipeline** — sequential transformation of a single data artifact through named stages. It reads cleanly. That readability is the first problem.

---

## The Falsifiable Claim

> **The deepest structural problem is that `config` is a disguised argument list, and this disguise is what makes every other problem invisible.**

The function appears to take two parameters. It actually takes **eight**: `data` plus seven independent stage-specific parameters compressed into one object. This compression hides arity, hides coupling, and hides an I/O side effect inside a pure-looking transformation chain.

---

## Three Experts Disagree

**Expert A (Defender):** The claim is correct. This is a *frozen pipeline* — it cannot be entered mid-stage, exited early, partially executed, or tested in isolation. The config object is precisely what makes the rigidity invisible. Need to skip validation on pre-validated data? You cannot call `process()`. You must duplicate logic or add a flag parameter.

**Expert B (Attacker):** The claim is too architectural. The *real* deepest problem is this specific line:

```python
enriched = enrich(transformed, fetch_external(config.sources))
```

A hidden I/O call, eager, uncached, unhandled, buried inside what reads as a pure data transformation. The pipeline framing is a distraction from a concrete defect.

**Expert C (Prober of shared assumptions):** Both experts assume the pipeline shape is the problem. Both take `config` as reasonable. But notice: `config` carries exactly one field per stage — `config.rules`, `config.mappings`, `config.sources`, `config.filters`, `config.group_key`, `config.agg_func`, `config.output_format`. That is not configuration. That is **seven function parameters wearing a trenchcoat**. Every caller must construct a fully-populated config even if they need three stages. The `config` object is the mechanism that makes the pipeline's rigidity *look like* flexibility.

---

## Claim Transformation

| | |
|---|---|
| **Original claim** | Frozen pipeline — cannot be entered, exited, or modified at any stage |
| **Transformed claim** | Config-as-arity-compression makes hidden rigidity, hidden I/O, and hidden coupling look like a clean 2-parameter interface |
| **The gap** | I started with pipeline shape and arrived at object structure as the primary concealment device |

---

## The Concealment Mechanism: Config Object as Arity Compression

The `config` object does four things that make the real structure invisible:

1. Collapses 7 required stage-specific parameters into 1, making the signature look clean
2. Buries `fetch_external` (I/O, latency, failure modes) inside a positional argument with no marker
3. Prevents partial application — no config exists that covers only stages 1–3
4. Makes the function look mockable (`mock config`) when each field requires specific structure

---

## The Legitimate-Looking Improvement

This passes code review. It will be praised.

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class PipelineConfig:
    rules: dict
    mappings: dict
    sources: list
    filters: list
    group_key: str
    agg_func: Callable
    output_format: str

PIPELINE_STAGES = [
    ("validate",   lambda d, c: validate(d, c.rules)),
    ("transform",  lambda d, c: transform(d, c.mappings)),
    ("enrich",     lambda d, c: enrich(d, fetch_external(c.sources))),
    ("filter",     lambda d, c: apply_filters(d, c.filters)),
    ("group",      lambda d, c: group_by(d, c.group_key)),
    ("aggregate",  lambda d, c: aggregate(d, c.agg_func)),
    ("format",     lambda d, c: format_output(d, c.output_format)),
]

def process(data, config: PipelineConfig):
    result = data
    for _stage_name, stage_fn in PIPELINE_STAGES:
        result = stage_fn(result, config)
    return result
```

**Why it passes review:** Named stages, type annotations, DRY loop, named config fields, looks extensible.

**Why it deepens concealment:** The loop *looks* like it enables reordering, skipping, and extension. None of those are true. Reordering stages doesn't work because `c.rules`, `c.mappings`, etc. are bound to specific positions. `fetch_external` is now inside a lambda in a list — *more* hidden, not less. The `dataclass` enshrines that all seven fields are required, making partial pipelines structurally impossible rather than just inconvenient.

---

## Three Properties Visible Only Because I Tried to Strengthen It

**1. The config-stage coupling is 1:1 and irreducible.**
When I tried to make stages enumerable, I had to map each lambda to exactly one config field. There is no stage that consumes more than one config field, and no config field that feeds more than one stage. `config` is not shared configuration — it's seven independent parameter slots. This was invisible in the original; the lambda list makes it explicit.

**2. `fetch_external` cannot be moved without changing semantics.**
When I placed it inside the `"enrich"` lambda, it became obvious that the I/O is structurally required at position 3. You cannot lazily defer it, hoist it, or reorder it without changing *when* network calls happen. The improvement exposes that this isn't a detail — it's a load-bearing assumption about execution order.

**3. All seven stages are mandatory — none is optional.**
When I tried to make `PipelineConfig` support partial pipelines, I couldn't — without a complete redesign. The dataclass makes this visible: there are no defaults, no `Optional` fields. The original hid this through duck typing; the improvement makes the constraint legible.

---

## Applying the Diagnostic to the Improvement

**What does the improvement conceal?**

`PIPELINE_STAGES` is not a general, reorderable pipeline. It's a fixed sequence masquerading as a configurable list. The loop looks generic; the lambdas are not. Extending the pipeline requires understanding the internal coupling, but the structure suggests otherwise.

**What property of the original is visible *only* because the improvement recreates it?**

The improvement makes the **1:1 config-stage binding explicit in syntax** for the first time. In the original, you might believe `config` flows as a context object through stages that each pull what they need. The lambda list removes that illusion: each stage pulls *exactly one field*, and each field feeds *exactly one stage*.

This exposes the true original problem with precision it couldn't achieve alone:

> **`config` is not a configuration object. It is seven function signatures collapsed into one, and that collapse is how the function hides that it is seven functions pretending to be one.**

The "improvement" is structurally identical to the original. It just makes the original's skeleton visible.
