## Three Experts on `process(data, config)`

---

### Expert A: The Functionalist — *"This is nearly correct"*

The pattern is a **linear transformation pipeline**: each step consumes the previous output and produces input for the next. This is one of the most defensible structural choices in data processing.

**What's working:**
- **Named intermediate states** (`validated`, `transformed`, `enriched`...) make the pipeline debuggable. You can add a breakpoint at any variable and inspect the world at that moment
- **Single-responsibility delegation**: `process()` is an *orchestrator*, not an implementer. The logic lives elsewhere
- **Config as a single seam**: all external variation is injected through one parameter, making the function's behavior fully determined by its arguments
- The **reading order maps to execution order** — this is cognitively cheap

**What I'd change (modestly):**
```python
def process(data, config):
    steps = [
        (validate,       config.rules),
        (transform,      config.mappings),
        (enrich,         lambda d: enrich(d, fetch_external(config.sources))),
        (apply_filters,  config.filters),
        (group_by,       config.group_key),
        (aggregate,      config.agg_func),
        (format_output,  config.output_format),
    ]
    # composable, testable, reorderable
```

The pipeline *is* the architecture. Make that explicit.

---

### Expert B: The Risk Engineer — *"This will hurt you in production"*

Expert A is describing what this function *intends* to be. I'm describing what it *is*.

**The failure modes:**

**1. `fetch_external` is a silent landmine**
```python
enriched = enrich(transformed, fetch_external(config.sources))
#                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                              — network call, buried mid-pipeline
#                              — no timeout visible here
#                              — no retry logic visible here
#                              — failure kills the whole pipeline
```
This isn't a transformation step — it's a side effect with a return value. It doesn't belong at this layer.

**2. No error handling means errors are invisible at the wrong level**
When `validate()` raises, the caller sees a raw exception from inside `process()` with no context about *which step* failed, *what the data looked like*, or *whether partial results exist*.

**3. `config` is an implicit dependency graph**
Every step reaching into `config.X` creates invisible coupling. Change `config.agg_func`'s interface and you break `aggregate` — but `process()` gives you no indication of which config keys matter to which steps.

**4. The pipeline is not restartable**
If step 6 fails, you rerun from step 1. For expensive operations (especially `fetch_external`), this is punishing.

**What I'd actually change:**
```python
def process(data, config):
    try:
        validated = validate(data, config.rules)
    except ValidationError as e:
        raise ProcessingError("validation", data, e) from e
    
    external = fetch_external(config.sources)  # explicit, at top
    
    try:
        transformed = transform(validated, config.mappings)
        enriched    = enrich(transformed, external)
        # ... etc, with step-aware error wrapping
    except TransformError as e:
        raise ProcessingError("transform", validated, e) from e
```

Expert A's refactor makes the pipeline *prettier* but harder to instrument. A list of steps loses the named intermediate states he correctly valued.

---

### Expert C: The Structuralist — *"You're both arguing about the walls, not the foundation"*

Expert A sees clean delegation. Expert B sees operational risk. **Both are reading this as a function when it's actually a hardcoded workflow.**

**What both frameworks make invisible:**

**The real question isn't "how do we execute these 7 steps" — it's "why are these exactly 7 steps, always, in this order?"**

This function encodes a **fixed processing topology** as imperative code. That's a design decision neither expert challenged:

- What if some data doesn't need enrichment?
- What if aggregation should precede filtering for some configs?
- What if new steps need to be added without modifying this function?

The function *looks* configurable (it takes `config`), but the **shape of the pipeline is hardcoded**. Config varies the *parameters* of each step, not the *presence or order* of steps. This is a subtle but crucial difference.

**What this reveals:** `config` is being asked to do two different jobs:
1. Parameterize step behavior (legitimate)
2. Implicitly signal which steps apply (it can't actually do this)

**The architecture Expert A wants:**
```python
# What if config could describe the pipeline itself?
pipeline = Pipeline.from_config(config)
return pipeline.run(data)
```

**The safety Expert B wants:**
```python
# What if steps were recoverable checkpoints?
result = CheckpointedPipeline(steps, store=config.checkpoint_store)
return result.run_from_last_checkpoint(data)
```

Neither solution is possible while the topology is hardwired.

---

## What the Argument Itself Reveals

The three experts agree on more than they think:

**All three are responding to the same underlying tension:**

> The function is written as if the pipeline is stable, but is designed to be used as if the pipeline is variable.

This is the structural contradiction. `config` implies variability. Seven hardcoded sequential calls imply stability. The function is trying to be both a **fixed algorithm** and a **configurable workflow**, and it's fully neither.

**What no single perspective could see alone:**

- Expert A (clarity) needed Expert B's challenge to admit `fetch_external` is architecturally misplaced
- Expert B (safety) needed Expert C's challenge to see that error handling on a hardwired pipeline solves the wrong problem
- Expert C (structure) needed Expert A and B's ground-level reading to identify *which* hardwired choices are actually costly

**The deeper pattern the function is reaching for but hasn't become yet:**

```
                    ┌─────────────────────────────┐
config  ──────────► │  Pipeline Topology (what)   │
                    │  Step Parameters  (how)      │
data    ──────────► │  Checkpoint Store (recovery) │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                             formatted result
```

The function as written collapses all three config concerns into one `config` object and all three structural concerns into one sequential block. **The right refactor isn't about the syntax — it's about separating what the pipeline *is* from how each step *behaves*.**

The argument revealed that the function isn't unfinished — it's *pre-architectural*. It's the first draft of a system that hasn't yet discovered what it needs to be.
