## Falsifiable Hypothesis

**The deepest structural problem is that `fetch_external` is buried inside `enrich`, collapsing an I/O boundary into the middle of what presents itself as a pure transformation pipeline — making every step after line 1 untestable without network access.**

---

## Three Experts Test the Claim

---

### Expert 1: The Defender

The claim is correct and understates the damage.

A pipeline of pure functions has a powerful property: any step can be tested, replaced, or reordered in isolation. The moment `fetch_external` is embedded inside `enrich`, that property collapses for **every downstream step** — not just enrichment.

```python
# You cannot test this without a live network call:
filtered = apply_filters(enriched, config.filters)
grouped  = group_by(filtered, config.group_key)
aggregated = aggregate(grouped, config.agg_func)  # ← still coupled to network
```

The fix makes the boundary explicit and moves I/O to the pipeline's edge:

```python
def process(data, config):
    external_data = fetch_external(config.sources)   # I/O here, once, visible
    validated   = validate(data, config.rules)
    transformed = transform(validated, config.mappings)
    enriched    = enrich(transformed, external_data)  # now pure
    ...
```

This is the Rule of Honest Functions: a function that looks pure but does I/O is lying about what it is.

---

### Expert 2: The Attacker

The claim identifies a symptom, not the disease. The deepest structural problem is **`config` is a god-object**.

```python
config.rules          # validation domain
config.mappings       # transformation domain  
config.sources        # I/O domain
config.filters        # filtering domain
config.group_key      # aggregation domain
config.agg_func       # aggregation domain
config.output_format  # presentation domain
```

`config` is doing the work of seven different collaborators. This is why `fetch_external` is buried — if `config` were properly decomposed into domain-specific arguments, the I/O boundary would become structurally obvious rather than needing discipline to maintain.

The hidden I/O is a consequence of a worse problem: **the function can only be understood by reading all of `config`'s implementation.** The signature tells you nothing about what this function actually does or what it depends on. Fix the god-object, and the I/O problem largely resolves itself.

---

### Expert 3: The Probe

Both experts assume **testability** is the primary virtue at stake. That assumption should be examined.

What neither argument addresses: this is not actually a pipeline. It is **an imperative sequence wearing a pipeline's clothes.**

A real pipeline is composable — stages can be swapped, short-circuited, or parallelized. This function has none of those properties. More critically:

```python
validated = validate(data, config.rules)
transformed = transform(validated, config.mappings)
enriched = enrich(transformed, fetch_external(config.sources))
```

**What happens when `validate` fails?** What happens when `fetch_external` times out? The function has no error semantics between steps. Each step implicitly trusts the previous one completely. This is fragile not because of I/O placement, but because **the control flow is invisible**.

Both experts are arguing about *where the I/O goes* while ignoring that there is no answer to *what happens when anything goes wrong*.

The deeper unexamined assumption: that sequential assignment is equivalent to a functional pipeline. It is not.

---

## Verdict: The Claim Was Transformed

| Before argument | After argument |
|---|---|
| Hidden I/O is the deepest problem | Hidden I/O is the most *visible* problem |
| Fix: move `fetch_external` to the edge | Fix requires three distinct changes |

**What I know now that I couldn't know before:**

The function has **three compounding structural failures**, ordered by depth:

```
1. DEEPEST: No error semantics between steps
   → Failures are invisible; the function is brittle by design

2. STRUCTURAL: config is a god-object
   → The signature is a lie; the function's dependencies are hidden

3. SURFACE: I/O buried inside a pipeline stage
   → A consequence of #2, and the easiest to see
```

The correct reconstruction separates all three concerns:

```python
def process(
    data: RawData,
    validation_rules: Rules,
    transform_mappings: Mappings,
    external_data: ExternalData,      # I/O resolved by caller
    filters: Filters,
    aggregation: AggregationSpec,
    output_format: OutputFormat,
) -> Result[FormattedOutput, ProcessingError]:
    return (
        validate(data, validation_rules)
        .and_then(lambda v: transform(v, transform_mappings))
        .and_then(lambda t: enrich(t, external_data))
        .and_then(lambda e: apply_filters(e, filters))
        .and_then(lambda f: aggregate(group_by(f, aggregation), aggregation))
        .map(lambda a: format_output(a, output_format))
    )
```

This makes the pipeline honest: explicit dependencies, explicit errors, pure transformation stages, I/O owned by the caller.

**The original claim was right about the symptom. The argument revealed the disease.**
