# Three Experts on a Pipeline

## Expert 1: The Advocate — "This is clean, and here's why"

This is a **linear pipeline** (sometimes called a sequential transformation chain). It's one of the oldest and most legible patterns in computing.

What's working:

- **Each line is a complete thought.** Input → transform → named output. You can read it top to bottom like a recipe.
- **No mutation.** Each step produces a new binding. Nothing is modified in place.
- **The `config` object is a coherent abstraction.** All behavioral variation lives in one place, making this function a *skeleton* that config *animates*.
- **Debugging is trivial.** Insert a `print` or breakpoint between any two lines and inspect the intermediate state.

This is essentially a **pipes-and-filters architecture** collapsed into a single function. Unix got decades of mileage from exactly this shape.

---

## Expert 2: The Critic — "Here are the failure modes"

This *looks* clean but hides real problems:

1. **Rigid ordering.** What if you need to filter *before* enrichment (to avoid expensive `fetch_external` calls on data you'll discard)? The sequence is hardcoded. You'd fork the function or add conditionals, and the elegance collapses.

2. **Hidden side effect.** `fetch_external(config.sources)` is **I/O buried in the middle of a pure-looking chain**. This function *looks* like a pure transformation but *isn't*. That makes it:
   - Hard to test (you need to mock network calls)
   - Unpredictably slow
   - A failure point with no visible error handling

3. **Error handling is absent.** Seven steps, any of which can fail, with no recovery strategy. What does a validation failure do? Throw? Return partial data? Silently pass through?

4. **`config` is a god object.** It carries `.rules`, `.mappings`, `.sources`, `.filters`, `.group_key`, `.agg_func`, `.output_format` — seven distinct concerns. That's not cohesion, that's a junk drawer with a nice label.

5. **Not composable.** You can't reuse "just the enrichment and filtering part." It's all or nothing.

---

## Expert 3: The Meta-Analyst — "What both frameworks miss"

The Advocate sees *legibility*. The Critic sees *rigidity*. Both are evaluating the function **as architecture**. But it's not architecture — it's a **specification of intent**.

What this function *actually* does is **name a business process**: validate → transform → enrich → filter → group → aggregate → format. That sequence isn't an implementation detail. It's a **domain concept**. The Critic wants to make the ordering flexible, but maybe the ordering *is the point* — maybe enrichment *must* follow transformation because the domain requires it.

What both miss: **the function's real problem isn't its shape — it's that it sits at the wrong abstraction level.** It's too concrete to be a framework (the steps are hardcoded) and too abstract to be auditable (every step is a black box delegated elsewhere). It's a *table of contents* pretending to be a *chapter*.

---

## The Synthesis — What I'd Actually Change

```python
# Make the pipeline shape explicit and composable
# Separate the pure chain from the effectful step

from dataclasses import dataclass
from typing import Callable, Sequence

@dataclass(frozen=True)
class Step:
    name: str
    execute: Callable
    
def run_pipeline(data, steps: Sequence[Step]):
    result = data
    for step in steps:
        result = step.execute(result)
    return result

# Construction — the *caller* decides the shape
def build_pipeline(config):
    return [
        Step("validate",   lambda d: validate(d, config.rules)),
        Step("transform",  lambda d: transform(d, config.mappings)),
        Step("enrich",     lambda d: enrich(d, fetch_external(config.sources))),  # still flagged as I/O
        Step("filter",     lambda d: apply_filters(d, config.filters)),
        Step("group",      lambda d: group_by(d, config.group_key)),
        Step("aggregate",  lambda d: aggregate(d, config.agg_func)),
        Step("format",     lambda d: format_output(d, config.output_format)),
    ]
```

This preserves the original's legibility while gaining:
- **Reorderable steps** (the Critic's concern)
- **Named steps** for logging/debugging (the Advocate's value)
- **Composability** — skip steps, inject steps, test subsets
- **A seam** where you can add error handling, timing, or retry logic *once* in `run_pipeline` rather than seven times

But honestly? **If the original function works and the sequence is stable**, it's fine. The simplest version of a pipeline is a pipeline written out plainly. The refactor earns its complexity only when you actually need the flexibility. The original's greatest virtue — and risk — is that it makes you *feel* like nothing needs to change.
