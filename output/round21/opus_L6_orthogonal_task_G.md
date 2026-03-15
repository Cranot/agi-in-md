## Prediction (before expert analysis)

> **The thing all three will miss:** The `run()` method's `data if not inputs else inputs` bifurcation creates a silent contract violation — intermediate nodes receive a `dict` of dependency outputs while root nodes receive raw `data`, but nothing in the interface distinguishes these two completely different function signatures. This means the graph doesn't actually compose correctly for real pipelines without every node function being written with hidden knowledge of its position in the graph.

---

## The Three Experts Argue

### Expert 1 (The Architect) — *Approach 2 is clearly superior*

Approach 2 wins on almost every engineering axis:

```
Linear Pipeline (v1)          Dependency Graph (v2)
─────────────────────          ──────────────────────
Fixed execution order    →     Declarative dependencies
No reuse of intermediates →    Built-in memoization (self.cache)
Monolithic                →    Composable, extensible
Cannot parallelize        →    Parallelizable (independent branches)
```

The graph approach gives you **incremental computation** for free. Change one upstream step? Only downstream dependents recompute. In a real data analysis workflow — where you're iterating on feature engineering while clustering parameters stay fixed — this is transformative. The linear pipeline forces you to re-run everything or manually manage intermediate state.

The dependency graph also makes the **topology explicit**. You can visualize it, validate it for cycles, and reason about it as data. The linear pipeline buries its structure inside imperative control flow.

---

### Expert 2 (The Pragmatist) — *Approach 2 is overengineered and broken*

Let me count the actual failure modes:

**1. Unbounded recursion with no cycle detection:**
```python
graph.add_step("a", fn_a, depends_on=["b"])
graph.add_step("b", fn_b, depends_on=["a"])
graph.run("a", data)  # 💥 RecursionError
```

**2. The cache is never invalidated:**
```python
graph.run("cluster", data_v1)   # caches result
graph.run("cluster", data_v2)   # silently returns stale data_v1 result!
```
This is a **correctness bug**, not a performance feature. The cache has no concept of input identity.

**3. No error handling or partial failure recovery.** If step 3 of 6 fails, you get an unhandled exception with no context about which graph node failed or what state the cache is in.

**4. Approach 1 is readable in 10 seconds.** Approach 2 requires building a mental model of lazy recursive evaluation. For a 6-step pipeline, this is pure accidental complexity. The linear version is:
- Easier to debug (stack traces map to steps)
- Easier to test (each line is independently verifiable)
- Easier to onboard new team members

**The graph becomes worth it at ~20+ steps with diamond dependencies. For this problem, it's not.**

---

### Expert 3 (The Semanticist) — *Both miss the real problem*

Both approaches commit the same fundamental sin: **they conflate the pipeline definition with its execution strategy.**

Approach 1 hardcodes eager sequential execution. Approach 2 hardcodes lazy recursive execution with memoization. Neither separates the *what* from the *how*.

What you actually want is:

```python
# Define the computation (pure structure)
pipeline = Pipeline()
pipeline.step("clean",     remove_nulls,      inputs=["raw"])
pipeline.step("normalize", scale_features,     inputs=["clean"])
pipeline.step("features",  extract_features,   inputs=["normalize"])
pipeline.step("cluster",   kmeans,             inputs=["features"], params={"k": 5})

# Choose execution strategy separately
result = pipeline.run(data, strategy=Eager())      # like v1
result = pipeline.run(data, strategy=Cached())     # like v2
result = pipeline.run(data, strategy=Parallel())   # neither offers this
```

This is exactly what tools like Airflow, Prefect, Dagster, and dbt figured out. Both approaches here are reinventing a wheel — one poorly, one naively.

Also: **neither approach addresses the actual data science concerns** — reproducibility, experiment tracking, feature lineage, or parameter sensitivity. The `k=5` in Approach 1 is a hardcoded magic number. Where's the experiment log? Where's the ability to sweep `k=3..10`?

---

## The Argument

> **Expert 1:** The graph's extensibility is the whole point. You *build* cycle detection and cache invalidation on top of the structure. You can't retrofit those onto a linear pipeline.
>
> **Expert 2:** "You can add it later" is how every over-engineered system defends itself. The linear pipeline *works correctly right now*. The graph has two bugs and an ambiguous interface.
>
> **Expert 3:** You're both arguing about plumbing. The linear pipeline is a fine prototype. The graph is a half-built framework. Neither is a *system* for doing data analysis.
>
> **Expert 2:** That's a non-answer. The question is "which is better for this problem," not "what would a perfect system look like."
>
> **Expert 1:** And the answer is obviously the one that gives you a foundation to grow.
>
> **Expert 2:** A foundation with bugs *is not a foundation*.

---

## Did They Miss My Prediction?

**Yes — all three missed it.**

No expert examined the actual data-flow semantics of `run()`:

```python
result = self.nodes[name](data if not inputs else inputs)
```

This single line means:
- **Root nodes** receive the original `data` (e.g., a DataFrame)
- **All other nodes** receive `{"dep_name": dep_result, ...}` (a dict)

These are **incompatible function signatures**. You cannot write a function like `scale_features` that works as both a root and a non-root node without explicitly coding around this. The graph's composability — Expert 1's core argument — is an illusion because **you cannot freely rearrange nodes** without rewriting their functions.

### Why was it invisible to all three frames?

Each expert analyzed at their preferred **level of abstraction**:
- Expert 1 saw architecture (boxes and arrows)
- Expert 2 saw failure modes (cycles, cache, errors)  
- Expert 3 saw system design (separation of concerns)

The bug lives in the **semantic gap between the interface contract and the runtime behavior** — a level of abstraction that falls *between* architecture and failure modes. It's the kind of thing you only find when you **trace a concrete execution by hand**, which none of the three frameworks encourage. It's a type error in a dynamically typed system, which makes it invisible until you actually run it with real functions.

---

## Verdict

**Approach 1 is better for this problem** — not because linear pipelines are generally superior, but because:

1. It **works correctly** as written
2. Approach 2 has bugs (cache invalidation, no cycle detection) **and** a design flaw (the data-passing bifurcation) that undermines its core value proposition
3. The linear pipeline's simplicity is an honest representation of a simple problem

Approach 2 becomes worthwhile when you have diamond dependencies, expensive recomputation, and the budget to fix its semantic issues. At that point, consider using an established framework (Dagster, Prefect) rather than hand-rolling one.
