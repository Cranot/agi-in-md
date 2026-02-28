# Three Experts, One Codebase

---

## Expert 1: The Production Engineer
*"Approach 2 is the better architecture — and it's not close."*

The linear pipeline locks you into a single execution path. Every run recomputes everything. Change your clustering step? Rerun normalization for no reason. Want to branch — try both k-means *and* DBSCAN on the same features? You duplicate the pipeline.

The dependency graph solves real problems:

- **Caching** eliminates redundant computation during iterative exploration
- **Declarative structure** lets you compose, extend, and rewire steps without rewriting control flow
- **Partial re-execution** — change one node, only its downstream dependents rerun

This is the architecture that tools like Airflow, dbt, and Make are built on. It's the correct structural insight: **data analysis is a DAG, not a sequence.** Approach 1 just happens to be a degenerate case (a chain is a trivial DAG).

---

## Expert 2: The Failure Analyst
*"Approach 2 has at least five latent bugs and a fundamentally broken interface contract."*

Let's read what the code *actually does*:

```python
result = self.nodes[name](data if not inputs else inputs)
```

This single line is a **design fracture**. It means:

| Condition | `fn` receives |
|---|---|
| Node has no dependencies | The raw `data` object |
| Node has dependencies | A `dict` of `{dep_name: result}` |

So every function must be written to accept **one of two completely different input shapes**, determined implicitly by its position in the graph. That's not polymorphism — it's a type ambiguity bug waiting to surface at runtime.

More failure modes the Engineer is ignoring:

1. **No cycle detection** — add a circular dependency and you get infinite recursion, not an error message
2. **No cache invalidation** — call `.run()` with new data and you get stale results from the old data silently
3. **`data` is passed to `run()` but only used by root nodes** — the parameter threading is incoherent
4. **Error propagation is opaque** — a failure in `remove_nulls` surfaces as a mysterious crash in `assign_labels`, six frames deep in recursion
5. **No execution ordering visibility** — you can't print the plan before running it

Approach 1 is dumb and honest. **Every bug in Approach 1 is visible on the line where it occurs.** Approach 2 trades that for abstraction and gets abstraction wrong.

---

## Expert 3: The Systems Epistemologist
*"Both experts are arguing about plumbing while the house has no foundation."*

Watch what both frameworks make invisible:

**Neither encodes the analytical decisions that actually matter.** Why `k=5`? Is that hardcoded because someone tested it, or because someone guessed? What's the sensitivity to that choice? Both approaches treat `kmeans(features, k=5)` as a step to *execute* rather than a hypothesis to *evaluate*.

**Neither supports the actual workflow of data analysis**, which is:
1. Run a step
2. *Inspect the intermediate result*
3. Change your mind about the next step
4. Go back and revise an earlier assumption

Approach 1 at least admits it's a script. Approach 2 pretends to be an engine but provides no observability, no checkpointing, no way to intervene between nodes.

**The Engineer's appeal to Airflow/dbt/Make actually undermines their argument.** Those tools took decades of engineering to handle exactly the problems the Failure Analyst identified — cycle detection, cache invalidation, execution plans, retries, logging. Approach 2 is a napkin sketch of a DAG runner presented as if the sketch *is* the solution.

**And the Failure Analyst's preference for "dumb and honest"** ignores that real analyses aren't six steps. They're sixty. With branches. With shared intermediate representations. The linear pipeline doesn't degrade gracefully — it becomes unreadable at scale, with duplicated sub-pipelines and invisible coupling.

**What's actually missing from both:**
- Provenance tracking (what data + what code + what parameters → what result)
- Schema contracts between steps
- The ability to *compare* pipeline variants, not just run one

---

## The Engagement

**Engineer to Failure Analyst:** "Every bug you listed is fixable — add cycle detection, fix the interface, add invalidation. The *architecture* is right."

**Failure Analyst back:** "If you have to fix the interface contract, the cache system, add cycle detection, add error handling, and add execution planning — you're not choosing Approach 2 anymore. You're writing a framework from scratch that happens to have started from Approach 2's skeleton. Meanwhile, Approach 1 works *now*."

**Epistemologist to both:** "You're debating whether to use a screwdriver or build a power drill from parts. The mature answer is: **use Approach 1 when your analysis is a script, use an existing DAG framework when it's a system, and never use Approach 2 as written in production.**"

---

## What the Argument Itself Reveals

The real lesson isn't "which is better." It's that **these two approaches represent different stages of a system's lifecycle**, and the danger lies in choosing based on aspiration rather than present reality.

| | Approach 1 | Approach 2 |
|---|---|---|
| **Best for** | Prototyping, one-shot analysis, small teams | Complex multi-branch pipelines (when mature) |
| **Fails when** | Analysis grows branches/shared steps | Implemented naively (as shown) |
| **Honest about** | Being a script | Nothing — it implies capabilities it doesn't have |

**The strongest answer:** Start with Approach 1. When you feel its constraints — when you're duplicating sub-pipelines or recomputing expensive steps — reach for a *proven* DAG framework (Prefect, Dagster, Luigi), not a hand-rolled 15-line graph runner. Approach 2 as written is the most dangerous artifact in software: **an abstraction that feels like it's solving your problem while quietly hiding the complexity it promised to manage.**
