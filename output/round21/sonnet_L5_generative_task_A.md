## Pattern: Sequential Transform Pipeline with Monolithic Configuration

Each stage consumes its predecessor's output and a slice of a shared config object. The structure is a **linear fold over a fixed stage sequence**, where data is the accumulator and config is the environment.

---

## Three Analytical Operations (Derived from This Structure)

### 1. Stage Typing — *What kind of thing is each step?* (Concrete)

Because the pipeline mixes operation *types* without distinguishing them, the first useful operation is classifying stages by their computational character:

| Stage | Type | Why It Matters |
|---|---|---|
| `validate` | Guard / predicate | Only stage that should *reject*, not transform |
| `transform` | Pure map | Deterministic, testable in isolation |
| `enrich` | **Effectful** (hidden I/O) | `fetch_external` is a side effect *buried inside* a positional argument |
| `apply_filters` | Pure predicate map | |
| `group_by` | Pure structural | |
| `aggregate` | Pure reduction | |
| `format_output` | Pure serialization | |

**Finding:** One stage is not like the others. The I/O is invisible at the call site.

---

### 2. Config Dependency Audit — *What does each stage actually need?* (Intermediate)

The monolithic `config` object makes every stage appear equally coupled to everything. Mapping actual dependencies reveals the real structure:

```
validate      → config.rules
transform     → config.mappings
enrich        → config.sources      ← also performs network I/O
apply_filters → config.filters
group_by      → config.group_key
aggregate     → config.agg_func
format_output → config.output_format
```

**Finding:** The config object is a **false unity** — these are seven independent parameter sets with no shared state. The function signature hides that `process` is actually a seven-argument function wearing a coat.

```python
# The honest signature:
def process(data, rules, mappings, sources, filters, group_key, agg_func, output_format):
```

This also reveals that `config` couples the *pipeline definition* to the *pipeline execution* — making partial reuse or stage substitution structurally awkward.

---

### 3. Failure Topology — *Where does linearity break down?* (Abstract)

A linear pipeline implicitly assumes all stages have equal failure semantics. They don't:

```
validate       → should short-circuit on failure (sentinel behavior)
fetch_external → can fail transiently (retry semantics)
aggregate      → should never fail if prior stages succeed (invariant)
```

The function has **no bulkheads**. A network timeout in `enrich` is indistinguishable from a validation error — both surface as uncaught exceptions from a single `process()` call. The linear structure erases the operational difference between:

- *This data is bad* (validation failure — caller's problem)
- *The network is down* (infrastructure failure — retry)
- *My aggregation logic is wrong* (programmer error — bug)

---

## Changes

```python
def process(data, config):
    # 1. Separate the effect — fetch before the pure pipeline
    external = fetch_external(config.sources)   # explicit, testable, retryable
    
    # 2. Make the pipeline a composable sequence
    stages = [
        lambda d: validate(d, config.rules),
        lambda d: transform(d, config.mappings),
        lambda d: enrich(d, external),          # now pure w/r/t the pipeline
        lambda d: apply_filters(d, config.filters),
        lambda d: group_by(d, config.group_key),
        lambda d: aggregate(d, config.agg_func),
        lambda d: format_output(d, config.output_format),
    ]
    
    return reduce(lambda acc, f: f(acc), stages, data)
```

Or, if the project warrants it, use a proper pipeline type that carries stage metadata (name, error class, retry policy).

---

## The Inversion: What This Frame Can't Generate

The linear pipeline frame is fundamentally **sequential and local** — it reasons about one datum moving through one fixed sequence. The operation this frame *cannot* generate is:

**Concurrent fan-out analysis** — whether stages could be restructured so that `fetch_external` runs *while* `validate` and `transform` are executing. The linear frame makes time invisible; it has no concept of stages that could overlap. You'd need a **dataflow / dependency graph frame** to see that `enrich` only depends on `transform`'s output and `config.sources`, neither of which depends on each other — meaning the fetch could start at invocation time, not mid-pipeline.

That's the question this frame forecloses by construction.
