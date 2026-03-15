# Structural Diagnosis: Level 7 Diagnostic Gap

## Initial Claim (Falsifiable)

> **The deepest structural problem is that this is a rigid linear pipeline whose topology is frozen in imperative control flow rather than represented as a manipulable data structure.** You cannot reorder, skip, insert, or conditionally branch steps without rewriting the function body.

---

## The Dialectic

**Expert A (Defender):**
"Exactly right. This is a pipeline that doesn't know it's a pipeline. `config` parameterizes each step's *behavior*, but the pipeline's *structure* — which steps run, in what order — is a hardcoded secret of the function body. You can't inspect, test, or compose partial pipelines."

**Expert B (Attacker):**
"Overengineered diagnosis. The code is clear and debuggable. The *actual* structural defect is simpler: `fetch_external` is a **side effect buried inside a pure-looking transformation chain**. Line 4 does I/O. Every other line is a pure data transform. That boundary is invisible and is the real problem."

**Expert C (Probing both):**
"You're both assuming the pipeline metaphor is the correct lens. Neither of you has asked: what happens when `enrich` fails for 3 out of 1,000 records? The answer: **the entire pipeline halts or silently drops data**. There's no structural provision for per-record failure accumulation. This isn't just a linear pipeline — it's an **all-or-nothing** linear pipeline."

---

## Transformed Claim

The deepest problem is not rigid topology alone, but **three fundamentally distinct concerns conflated into one sequential flow**:

| Concern | Where it hides |
|---|---|
| **Pipeline topology** | Hardcoded in statement ordering |
| **Purity boundary** | `fetch_external` buries I/O amidst pure transforms |
| **Failure semantics** | All-or-nothing; no per-record error tracking |

---

## The Gap as Diagnostic

| | Claim |
|---|---|
| **Original** | Rigid topology |
| **Transformed** | Three conflated architectural concerns |

**The concealment mechanism: legibility as camouflage.**

Every line "does one thing." Names are descriptive. The shape is satisfying. This surface-level clarity *actively discourages structural questioning*. It passes a naive SRP check at the line level while violating separation of concerns at the architectural level.

---

## Applying the Mechanism: What Is STILL Hidden?

If legibility is camouflaging structural problems, apply the lens to what no expert questioned: **the `config` parameter itself**.

```
config.rules
config.mappings
config.sources
config.filters
config.group_key
config.agg_func
config.output_format
```

`config` is a **dependency laundering mechanism**. This function has **seven distinct dependencies** but declares **two parameters**. Every pipeline step is coupled to every other step *through* `config`. It is a god object that:

- Makes the true dependency graph invisible at the call site
- Makes it impossible to know which step needs which config subset
- Means any schema change to `config` can silently ripple across all seven stages
- Defeats static analysis, type narrowing, and independent testability

**The function's signature is a lie.** It says: *"I need data and configuration."* It means: *"I need data, validation rules, field mappings, external source descriptors, filter predicates, a grouping key, an aggregation strategy, and an output format specification — and I refuse to say so."*

---

## What I'd Actually Write

```python
def process(data, config):
    # 1. Make the pipeline a data structure
    # 2. Separate the impure step
    # 3. Narrow config per stage
    # 4. Accumulate errors, don't halt

    external_data = fetch_external(config.sources)  # impure: do first, explicitly

    pipeline = Pipeline([
        Step(validate,      config=config.rules),
        Step(transform,     config=config.mappings),
        Step(enrich,        context=external_data),
        Step(apply_filters, config=config.filters),
        Step(group_by,      key=config.group_key),
        Step(aggregate,     func=config.agg_func),
        Step(format_output, fmt=config.output_format),
    ])

    return pipeline.run(data)   # with per-record Result types
```

This makes topology manipulable, hoists side effects to the boundary, narrows each step's config surface, and opens a path to per-record error accumulation — addressing all three concealed structural defects, including the one the dialectic itself almost missed.
