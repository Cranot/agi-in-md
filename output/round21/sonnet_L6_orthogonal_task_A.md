## Prediction First

**The pipeline performs enrichment before filtering — paying the cost of external data fetching for records that will subsequently be discarded.** The step ordering encodes a silent performance/correctness semantic that looks intentional precisely because it's explicit.

I predict all three experts will orbit around *how* the code is structured and miss *whether the steps are in the right order*.

---

## The Three Experts

---

### Expert A — The Strengths Advocate

This is textbook **pipeline composition**. Seven steps, each named, each single-purpose. The intermediate variables (`validated`, `transformed`, etc.) aren't noise — they're **execution traces written into the structure**. You can read this function like a sentence.

Compare to the alternative:

```python
return format_output(
    aggregate(group_by(apply_filters(
        enrich(transform(validate(data, config.rules), config.mappings),
        fetch_external(config.sources)), config.filters),
    config.group_key), config.agg_func), config.output_format)
```

The named-assignment form gives you free debugging. Each variable is a natural breakpoint. The `config` object is doing exactly what configuration objects should do: centralizing variation without polluting the pipeline's logic.

The pattern is correct. The clarity is load-bearing.

---

### Expert B — The Failure Mode Analyst

The clarity is **cosmetic**. This function has at least four unhandled failure surfaces:

```python
# fetch_external is called inline — no retry, no timeout, no fallback
enriched = enrich(transformed, fetch_external(config.sources))

# config attributes accessed directly — no guard against None or missing keys
grouped = group_by(filtered, config.group_key)
aggregated = aggregate(grouped, config.agg_func)
```

**The critical flaw:** if `aggregate` throws after `fetch_external` already succeeded, the entire pipeline restarts from zero. You've paid the network cost for nothing. There's no checkpoint, no partial recovery, no way to resume.

The config is also a **god object anti-pattern** — it carries eight different concerns simultaneously with zero self-validation. Pass a config with `agg_func=None` and you get a runtime error six steps deep.

The named variables give the *appearance* of observability. Without logging between steps, you have none.

---

### Expert C — The Observer

You're both describing the same tree from different sides. The real issue is **the function is structurally untestable** without major surgery.

`fetch_external` is hardcoded inside the call. You can't inject a mock without either patching the module or restructuring the function. Compare:

```python
# Current — fetch_external is locked inside
enriched = enrich(transformed, fetch_external(config.sources))

# Testable — inject the external data as a dependency
def process(data, config, external_fetcher=fetch_external):
    enriched = enrich(transformed, external_fetcher(config.sources))
```

The broader pattern: `config` contains both *data* (mappings, sources) and *behavior* (`agg_func`, `group_key`). These are different kinds of things. Behavior should be injected. Data can be configured. Mixing them makes both harder to test and impossible to compose.

The pipeline pattern is fine. The **dependency structure** is the problem.

---

## The Argument

**A:** You're both treating fragility as the primary concern. Premature resilience is its own complexity cost. A readable pipeline that fails loudly is better than a robust one no one can debug.

**B:** "Fails loudly" isn't a strategy when the failure happens after an expensive external call. You're describing a function that destroys work silently and then asks you to start over.

**C:** Neither of you are addressing *design*. Error handling is a band-aid if the dependencies are wrong. Fix the injection problem first, and you can wrap retry logic around just the step that needs it.

**B:** Agreed on injection. But that's still a local fix. The config god-object means you can't safely refactor any single step without auditing the whole config structure.

**A:** That's a call-site problem, not a function problem. The function's contract is clear. What you put in `config` is the caller's responsibility.

**C:** That's an abdication, not a design decision.

---

## Did They Miss My Prediction?

**Yes. Completely.**

Not one of them asked: *should filter come before enrich?*

The current order:
```
validate → transform → enrich (+ fetch_external) → filter → group → aggregate → format
```

The semantically cheaper order:
```
validate → transform → filter → enrich (+ fetch_external) → group → aggregate → format
```

If filtering discards 40% of records, you're currently fetching external data for all of them, then throwing that data away. The function hardcodes a **pay-then-discard** semantic that may be deeply wrong depending on what `apply_filters` actually filters on.

---

## Why Was It Invisible to All Three Frames?

**The pipeline pattern creates an ordering illusion.** When code is explicit and linear, the sequence *looks* intentional — as if whoever wrote it considered alternatives and chose this. Explicitness signals deliberateness. None of the standard analysis frames (readability, robustness, testability) naturally generate the question: *"is this the right order?"*

- Expert A was looking for structural elegance and found it — the order was part of what read well.
- Expert B was looking for failure surfaces — and found them in error handling, not step sequencing.
- Expert C was looking for coupling — and found it in dependency injection, not execution ordering.

My blind spot, if it exists: I assumed no expert would think about ordering semantics. An expert deeply familiar with **data pipeline optimization** (push-down predicates, filter-early rules from database query planning) would have caught this immediately. The prediction held because none of the three frames were database-informed. A fourth expert — the performance engineer — would have found it in the first pass.

**The invisible thing is often invisible because the right frame wasn't in the room.**
