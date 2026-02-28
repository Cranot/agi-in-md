## The Comparison, Done Right

---

### Surface Verdict (Necessary but Insufficient)

Approach 1 is more honest about what it is. Approach 2 is more powerful but contains a subtle structural defect that matters more than any feature it adds.

---

## Falsifiable Claim

> **Approach 2's deepest problem is not its complexity — it is that `run()` secretly threads a hidden global input (`data`) through every node while pretending to model pure local dependencies. This makes the cache semantically incorrect and the graph model a lie.**

This is falsifiable: if every node function in a real use case can be written with consistent, locally-sourced signatures and the cache never returns stale results across dataset changes, the claim fails.

---

## The Three-Expert Dialectic

### Expert A — Defender
*"The graph correctly decouples topology from computation. Caching intermediate results is a real performance win. The `data` parameter is just a reasonable default for leaf nodes."*

This defense is accurate at the feature level. The graph **does** enable reuse and parallelism that Approach 1 cannot express.

### Expert B — Attacker
*"The cache is keyed only on node name, not on input data. Run this twice on different datasets — you get the first run's results silently on the second run. That's not a minor bug, it's a correctness failure by design. Also, look at this:"*

```python
result = self.nodes[name](data if not inputs else inputs)
#                         ^^^^                   ^^^^^^
#                    raw dataset          dict of dep results
```

*"Leaf node functions and non-leaf node functions must have incompatible signatures. There is no contract enforcing this. The graph infrastructure has made function signatures unpredictable."*

### Expert C — Prober (Assumption Auditor)
*"Both of you are fighting about symptoms. What assumption is Approach 2 making that it never states? It assumes the graph is **stateless across calls** — that `data` is a fixed global context, not a varying input. If that's true, the cache is fine. If `data` varies, the cache is a bug. The real question: **what computational model does this graph actually implement?**"*

---

## Why the Dialectic Transformed in THAT Direction

The argument moved from **"API design problem"** → **"correctness bug"** → **"wrong computational model"** — not randomly, but because of a specific structural force:

### The Structural Force: **Implicit Global State Masquerading as Graph Purity**

`data` is passed into every recursive call of `run()`. This means:

- Every node in the graph has **ambient access to the original dataset**
- The graph is not a DAG of pure transformations — it is a DAG of transformations with a **hidden shared environment**
- The cache treats the computation as **`f(node_name) → result`** when it should treat it as **`f(node_name, data) → result`**

This force shaped the dialectic predictably: the Defender sees the visible graph structure (clean). The Attacker finds the hidden `data` thread (broken). The Prober forces the realization that both are right because the model is incoherent — it makes two contradictory promises simultaneously.

---

## What This Force Predicts

**The next problem this code will face:**

> A developer will try to run the same `AnalysisGraph` instance in a loop over multiple datasets (batch processing, cross-validation, or A/B comparison). The cache will return stale results from the first run for all subsequent runs. Because the failure is silent — no exception, plausible-looking output — it will produce incorrect analysis that is difficult to diagnose.

Specifically, the force predicts this path:
1. Someone adds `graph.run("labeled", dataset_2)` after already running on `dataset_1`
2. Every cached node returns `dataset_1`'s results
3. The output looks structurally valid
4. The bug surfaces only when results are compared externally

**Secondary prediction:** Someone will attempt to fix this by clearing the cache between runs (`self.cache = {}`), which solves the correctness problem but eliminates the reuse benefit — collapsing Approach 2 back toward Approach 1's semantics while retaining Approach 2's complexity. The graph model will have paid its complexity tax without delivering its promised benefit.

---

## The Corrected Model

The fix requires making the computational contract explicit:

```python
def run(self, name, data):
    # Cache must key on BOTH node AND data identity
    cache_key = (name, id(data))  # or hash(data) for value semantics
    if cache_key in self.cache:
        return self.cache[cache_key]

    inputs = {dep: self.run(dep, data) for dep in self.edges[name]}
    
    # Node functions must have a UNIFORM signature
    # They always receive: (original_data, dep_results_dict)
    result = self.nodes[name](data, inputs)
    self.cache[cache_key] = result
    return result
```

Now the model is honest: every node receives both the global input and its local dependencies. Function signatures are uniform. The cache is correct.

---

## Summary Judgment

| Criterion | Approach 1 | Approach 2 (as written) | Approach 2 (corrected) |
|---|---|---|---|
| Readability | ✅ High | ⚠️ Medium | ⚠️ Medium |
| Correctness | ✅ Yes | ❌ Stale cache | ✅ Yes |
| Computational model | ✅ Honest | ❌ Incoherent | ✅ Honest |
| Extensibility | ❌ Low | ✅ High | ✅ High |
| Appropriate complexity | ✅ Yes | ❌ Pays cost, misses benefit | ⚠️ Justified only at scale |

**Approach 1 is better than Approach 2 as written.** Approach 2 corrected is better than Approach 1 — but only if the use case actually requires non-linear dependencies, reuse, or parallelism. If the pipeline is genuinely linear, Approach 1's honesty is itself a structural virtue.
