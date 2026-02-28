# Perspectival Analysis: Linear Pipeline vs. Dependency Graph

## Prediction

I predict **Expert C** (the one who sees what both miss) will surface the deepest insight. Both approaches encode strong assumptions about how data analysis *actually works in practice*, and the most important critique likely lives outside the frame both approaches share — not in their relative merits.

---

## Expert A — The Structural Advocate (Sees Strengths)

**Approach 2 is architecturally superior, and it's not close.**

The dependency graph gives you three things the linear pipeline fundamentally cannot offer:

```
Linear Pipeline          Dependency Graph
─────────────────        ─────────────────
Fixed execution order    Topology-driven order
No reuse                 Built-in caching
All-or-nothing runs      Partial re-execution
```

Consider what happens when your analysis evolves. You need clustering **and** a parallel correlation analysis, both depending on the same `extract_features` step:

```python
# Approach 2 handles this naturally:
graph.add_step("clean",      remove_nulls)
graph.add_step("normalize",  scale_features,    depends_on=["clean"])
graph.add_step("features",   extract_features,  depends_on=["normalize"])
graph.add_step("cluster",    kmeans_wrapper,     depends_on=["features"])  # branch 1
graph.add_step("correlate",  correlation_matrix, depends_on=["features"])  # branch 2
#                                                  ↑ features computed ONCE
```

In Approach 1, you'd either duplicate `extract_features` or hack in shared state. The graph **makes the dependency structure explicit**, which is the single most important property of maintainable pipeline code.

The caching alone justifies the complexity. In data work, you constantly re-run with tweaked parameters. Caching intermediate results is not a luxury — it's a requirement.

---

## Expert B — The Failure Analyst (Sees Failure Modes)

**Both approaches have serious problems, but Approach 2's are more dangerous because they're hidden.**

### Approach 2 has a concrete bug in its interface contract:

```python
def run(self, name, data):
    # ...
    inputs = {dep: self.run(dep, data) for dep in self.edges[name]}
    result = self.nodes[name](data if not inputs else inputs)
    #                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #        Root nodes get raw `data` (whatever type)
    #        Non-root nodes get `dict[str, Any]`
    #        EVERY function must handle BOTH calling conventions?
```

This means your node functions don't have a consistent signature. `remove_nulls` receives raw data. `extract_features` receives `{"normalize": <result>}`. This is a **type-system nightmare** that will produce silent bugs the moment someone reorders dependencies.

### Approach 1's failure mode is actually *visible*:

```python
# If this breaks, you know EXACTLY where to look:
cleaned = remove_nulls(data)        # line N
normalized = scale_features(cleaned) # line N+1  ← error here means
                                     #            scale_features or cleaned
```

### Approach 2's failure mode is a recursive stack trace:

```
Error in run("cluster") 
  → run("features") 
    → run("normalize") 
      → run("clean") 
        → actual error buried 4 frames deep
```

And the `cache` is a **stale data trap**. There's no invalidation strategy. Change your input data, forget to clear the cache, and you're analyzing yesterday's results with today's labels. In data analysis, **silent wrongness** is the worst failure mode.

I'd push back on Expert A directly: **the caching isn't a feature, it's a footgun** without explicit invalidation. And the "flexibility" is theoretical — most data analysis pipelines are linear 90% of the time. You're paying complexity tax for the 10%.

---

## Expert C — The Frame Analyst (Sees What Both Miss)

**Both approaches misunderstand the actual problem of data analysis.**

Expert A argues for graph flexibility. Expert B argues it's premature complexity. They're both debating *pipeline topology* while the real challenges are elsewhere:

### 1. Neither approach encodes what the data *should look like* between steps.

```python
# What both approaches ACTUALLY need:
cleaned = remove_nulls(data)
assert cleaned.shape[0] > 0,          "Lost all rows during cleaning"
assert no_nulls(cleaned),              "Cleaning failed"

normalized = scale_features(cleaned)
assert normalized.std().between(0.8, 1.2).all(),  "Normalization suspect"
```

The space between steps is where data analysis goes wrong in practice — not in the wiring of the steps themselves. **Neither approach has a concept of intermediate validation or data contracts.**

### 2. The hardcoded `k=5` is doing more damage than any architectural choice.

```python
clustered = kmeans(features, k=5)  # ← WHY 5?
```

Neither approach provides a way to express that `k` should be *determined by the data* (elbow method, silhouette score, etc.). The real pipeline isn't `clean → cluster → label`. It's:

```
clean → normalize → features → evaluate_k_range → select_k → cluster → validate_clusters → label
                                     ↑                              ↑
                               THIS is the hard part          AND THIS
```

Both approaches model data analysis as a **production system** (fixed transform sequence) when it's actually an **exploration system** (branching, backtracking, conditional paths). Neither supports:

- Running step N with 5 different parameter settings
- Comparing results across branches
- Deciding the next step based on intermediate results

### 3. Directly responding to Expert A and B:

Expert A says caching enables iteration. But **caching transforms without versioning parameters** means you can't compare `kmeans(k=3)` vs `kmeans(k=7)` — the cache has one slot per node name.

Expert B says linearity is fine 90% of the time. But that 90% figure hides the fact that **the other 10% is where all the analytical decisions live.** Optimizing for the 90% that's trivial is the wrong target.

---

## Was My Prediction Right?

**Yes, but the mechanism was more specific than I expected.**

I predicted Expert C would go deepest by questioning the shared frame. They did — but the most revealing specific insight wasn't abstract. It was concrete: **both approaches model analysis as a fixed-topology transform pipeline, when real data analysis is an iterative decision process with conditional branching and parameter exploration.**

The argument between A and B made something visible that neither could alone: Expert A's "caching enables iteration" and Expert B's "cache is a footgun" are **both correct simultaneously** because the cache is single-valued per node. This contradiction is only visible when the two claims collide — and it points directly to Expert C's deeper observation that the real need is *parameter-versioned* execution, not just *topology-flexible* execution.

## The Verdict

| Criterion | Approach 1 | Approach 2 |
|---|---|---|
| Readability | ✅ Immediate | ❌ Requires tracing |
| Debuggability | ✅ Linear stack | ❌ Recursive + cache |
| Extensibility | ❌ Copy-paste | ✅ Add nodes |
| Correctness risk | Medium (visible) | **High (silent)** |
| Real-world readiness | Neither — both lack validation, parameterization, and reproducibility |

**For a one-off analysis:** Approach 1. It's honest about what it is.
**For a production system:** Approach 2's *idea* is right, but this implementation has the interface bug Expert B identified and lacks the parameter/validation layer Expert C demands. You'd want something like Prefect, Dagster, or Hamilton — tools that solved these exact problems.

**The deepest answer:** the choice between these two is less important than what neither one does.
