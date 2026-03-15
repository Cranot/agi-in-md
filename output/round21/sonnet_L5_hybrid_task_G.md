## Pattern Identification

This instantiates the **Implicit vs. Explicit Dependency Graph** pattern — one approach embeds computational dependencies in execution order (topology as control flow), the other reifies them as first-class data structures (topology as data). It's a specific case of the broader **Representation Determines Power** problem: what you can't name, you can't manipulate.

---

## The Three Analytical Operations

Derived from *this problem's specific properties* — a data pipeline where steps have sequential and potentially shared dependencies, intermediate results are expensive to compute, and requirements change iteratively:

1. **Topology Analysis** — What computational shapes can each approach express? Linear chains, fan-out, shared ancestors, parallel branches?
2. **Failure Mode Analysis** — How does each approach behave when things go wrong: bad data, a step changes, partial re-runs are needed?
3. **Correctness Under Mutation Analysis** — What happens when the code is *changed*? Adding a step, trying different parameters, calling it twice with different data?

---

## Prediction

I predict **Topology Analysis** yields the deepest insight. The *structural difference* between the approaches — linear chain vs. DAG — is the root cause from which all other properties derive. Performance, reusability, and debuggability are downstream of topology. Understanding the shape of what each can represent should explain everything else.

---

## Execution

### Operation 1: Topology Analysis

**Approach 1** encodes topology as execution order. The dependency graph is:

```
data → cleaned → normalized → features → clustered → labeled → result
```

It's a *forced* linear chain. Want two normalization strategies? Fork the whole function. Want to share an expensive cleaning step across two analysis paths? You can't — not without restructuring.

**Approach 2** makes topology explicit as data:

```python
graph.add_step("clean",     remove_nulls,     depends_on=[])
graph.add_step("normalize", scale_features,   depends_on=["clean"])
graph.add_step("features",  extract_features, depends_on=["normalize"])
graph.add_step("cluster_5", kmeans_5,         depends_on=["features"])
graph.add_step("cluster_3", kmeans_3,         depends_on=["features"])  # free branch
```

Fan-out, shared ancestors, and parallel branches are *natural* here. The topology is *introspectable* — you can visualize it, serialize it, diff it. Approach 1's topology is invisible except by reading the code.

**Verdict**: Approach 2 is structurally superior for non-trivial pipelines.

---

### Operation 2: Failure Mode Analysis

**Approach 1**: Fails silently and expensively. If `kmeans` fails, you've lost everything — rerun from scratch. Want to try `k=3` instead of `k=5`? Rerun from scratch. No intermediate results are preserved. The upside: it's *transparent*. Failures have clear stack traces with no hidden state.

**Approach 2 has a critical correctness bug**:

```python
def run(self, name, data):
    if name in self.cache:
        return self.cache[name]          # ← Cache key is ONLY `name`
    ...
    self.cache[name] = result
```

The cache key is just the step name — not the data. Call `run("cluster", dataset_A)`, then `run("cluster", dataset_B)`: you silently get results from `dataset_A`. **This is a data poisoning bug.**

There's a second bug — the implicit node interface:

```python
result = self.nodes[name](data if not inputs else inputs)
```

Leaf nodes receive raw `data`. Non-leaf nodes receive `{"dep_name": dep_result, ...}`. This undocumented convention means every function must silently know its position in the graph. Add a dependency to a former leaf? You've broken its function signature with no error.

**Verdict**: Approach 1 fails loudly and predictably. Approach 2 fails silently and corruptly.

---

### Operation 3: Correctness Under Mutation Analysis

| Change | Approach 1 | Approach 2 |
|---|---|---|
| Add a step | Thread new variable through by hand | `graph.add_step(...)` — one line |
| Try different `k` | Duplicate function or add parameter | Add a new node depending on `features` |
| Re-run with new data | Safe — no state | **Broken** — cache returns stale results |
| Parallelize two branches | Requires major refactoring | Topology already enables it |
| Unit test one step | Call the function directly ✓ | Need fresh `AnalysisGraph()` per test or cache poisons results |

**Verdict**: Approach 2 is easier to *extend* but dangerous to *operate* due to mutable cached state.

---

## Synthesis: Which Is Better?

**Approach 1 is better *as written***. Approach 2 is better *in principle*, but the implementation is broken in ways that matter in production.

The correct answer is **a fixed Approach 2**:

```python
def run(self, name, data):
    # Fix 1: cache key must include data identity
    cache_key = (name, id(data))
    if cache_key in self.cache:
        return self.cache[cache_key]

    # Fix 2: uniform node interface — always pass inputs dict
    inputs = {dep: self.run(dep, data) for dep in self.edges[name]}
    if not inputs:
        inputs = {"__data__": data}   # source nodes get data under a known key

    result = self.nodes[name](inputs)
    self.cache[cache_key] = result
    return result
```

Once corrected, Approach 2 dominates for any real analysis pipeline because:
- **Shared computation** is free (cached once)
- **Branching** (try `k=3` and `k=5` from the same features) is structural
- **Partial re-runs** skip unchanged upstream steps
- **The topology is a first-class object** you can visualize, test, and version

Approach 1 remains preferable for: throwaway scripts, truly linear pipelines with no branching, or contexts where a new reader must understand the code instantly.

---

## Inversion: Was the Prediction Right?

**Partially wrong** — and the gap is instructive.

Topology Analysis *did* reveal Approach 2's structural superiority. But Failure Mode Analysis revealed something topology couldn't: **the better architecture was implemented incorrectly in ways that make it actively dangerous**. The cache bug isn't a minor issue — it causes silent data corruption, the worst kind of failure in data analysis.

**What this reveals about the analytical blind spot:**

Topology analysis activates *pattern recognition* — "DAG > linear chain, I've seen this before." That pattern fires *before* close reading of the implementation. The result is **sophistication bias**: the more architecturally impressive solution is assumed to be better, without verifying that the implementation correctly realizes its architecture.

The real question wasn't *"which design pattern is superior?"* but *"which code is correct?"* Structural elegance is only as valuable as its implementation. The lesson: **always check whether the code does what the architecture promises before evaluating the architecture.**
