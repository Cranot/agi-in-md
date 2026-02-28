# Recursive Falsification of a Linear Pipeline

## The Code's Obvious Pattern
A **linear transformation pipeline** — each step consumes the prior step's output plus a slice of `config`. It's the "assembly line" pattern.

---

## Round 1: First Falsifiable Claim

> **Claim:** The deepest structural problem is **rigidity** — steps, order, and composition are hardcoded, violating Open/Closed. Any pipeline change requires editing this function.

### Three Experts Stress-Test This

**Defender:** Correct. Adding a caching step, skipping enrichment, reordering filtering before transformation — all require surgery on `process()`. The pipeline topology is fused with execution.

**Attacker:** This is a *surface* observation, not a deep one. Pipelines *should* often have fixed order — validation *must* precede transformation. The "make it configurable" reflex produces over-abstracted, harder-to-debug code. This function is readable and traceable. You're prescribing a solution (composable pipeline), not diagnosing a real problem.

**Presupposition Prober:** You're both assuming the *linear shape* is the right unit of analysis. But look at step 3:

```python
enriched = enrich(transformed, fetch_external(config.sources))
```

`fetch_external` is **a side effect** — network I/O, latency, failure modes — buried inside what the syntax presents as a pure data transformation chain. You're both debating *flexibility* while ignoring that the steps aren't even the same *kind of thing*.

### Claim 1 Transforms
Rigidity isn't the deepest problem. The prober exposes something the attacker and defender both missed.

---

## Round 2: The Deeper Claim (Unreachable in Round 1)

> **Claim:** The deepest structural problem is **deceptive syntactic uniformity**. The pipeline's notation — `result = step(prev, config.x)` — makes every step *look* identical, but they are **categorically different operations**:

| Step | Actual Category |
|---|---|
| `validate` | **Guard** — may reject/raise, produces no new data |
| `transform` | **Pure map** — deterministic reshaping |
| `fetch_external` | **Side effect** — I/O, latency, failure, non-determinism |
| `enrich` | **Join** — merges two data sources |
| `apply_filters` | **Reduction** — removes elements |
| `group_by` | **Structural reshape** — changes data topology |
| `aggregate` | **Fold** — collapses structure |
| `format_output` | **Serialization** — changes representation, not content |

The uniform syntax **prevents** the developer from reasoning about:
- 🔴 **Error propagation** — where can this fail, and how?
- 🔴 **Retry semantics** — only `fetch_external` is retryable, but nothing marks it
- 🔴 **Caching boundaries** — everything before `fetch_external` is cacheable; nothing after is without it
- 🔴 **Parallelizability** — `validate` and `fetch_external` could run concurrently, but the chain forbids it
- 🔴 **Testability** — you can't test the pure core without mocking the I/O middle

## What I'd Actually Change

```python
def process(data, config):
    # Phase 1: Pure validation & transformation (deterministic, testable)
    prepared = prepare(data, config.rules, config.mappings)

    # Phase 2: Side-effectful enrichment (retriable, cacheable, mockable)
    external = fetch_external(config.sources)
    enriched = enrich(prepared, external)

    # Phase 3: Pure reshaping & output (deterministic, testable)
    return reshape_and_format(enriched, config.filters,
                              config.group_key, config.agg_func,
                              config.output_format)
```

Make the **categorical boundaries** architecturally visible: pure → effectful → pure. This is a "functional core, imperative shell" decomposition applied *within* a single pipeline.

---

## Meta: What Does the Distance Between Claims Reveal?

| | Claim 1 | Claim 2 |
|---|---|---|
| **Level** | Mechanical / syntactic | Semantic / epistemological |
| **Diagnosis** | "Can't rearrange steps" | "Can't *reason* about steps" |
| **Prescription** | Composable pipeline DSL | Categorical phase separation |
| **Framing** | The code is inflexible | The code is *misleading* |

The distance is **categorical, not incremental**. Claim 1 treats all steps as homogeneous and asks "how do I reorder them?" Claim 2 recognizes they were never homogeneous and asks "why does the code *lie* about that?"

**This is exactly what single-pass analysis misses.** A first reading pattern-matches *pipeline → make it configurable*. Only by falsifying that instinct do you reach the real insight: the deepest problem with this code isn't what it *does* — it's what it **hides**.
