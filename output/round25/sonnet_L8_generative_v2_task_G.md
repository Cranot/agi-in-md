## The Structural Diagnostic

### Step 1: The Falsifiable Claim

**Approach 2's deepest structural problem:** The `run(name, data)` method has a semantically incoherent `data` parameter. Root nodes receive raw data; non-root nodes receive a `dict` of dependency outputs. This means no function can be both a root and a non-root node, the API contract is invisible, and you cannot actually compose a true DAG — you've built two incompatible calling conventions stapled together.

---

### Step 2: Three Experts Attack the Claim

**Expert A (Defender):** The incoherence is real and immediately fatal. Watch:

```python
graph.add_step("clean",     remove_nulls)             # receives raw data ✓
graph.add_step("normalize", scale_features,           # receives {"clean": ...}
               depends_on=["clean"])                  # scale_features(dict) → crashes

# The function signatures must secretly know their graph position.
# The graph doesn't compose functions — it discriminates between them.
```

**Expert B (Attacker):** You're diagnosing a bug, not the structural problem. The incoherence is *fixable* in 10 lines. What isn't fixable is that both approaches share a deeper assumption: **the pipeline is structurally determined at design time.** The moment `k=5` needs to be `k=7` based on cluster silhouette scores, neither architecture has a vocabulary for it. The graph gives you topological flexibility and nothing else.

**Expert C (Probing what both take for granted):** Both of you assume the problem is control flow. You're both ignoring that `hyperparameters` — `k=5`, the normalization scale, the feature selection threshold — are **invisible to the computation graph entirely**. They live inside closures. Neither architecture treats them as first-class citizens. The graph's nodes/edges structure draws your eye exactly away from this.

---

### Step 3: The Transformed Claim

| | Original Claim | Transformed Claim |
|---|---|---|
| **What** | Data flow incoherence | Parametric invisibility |
| **Where** | `run()` method signature | Inside closed-over function calls |
| **Type** | Bug | Design philosophy |
| **Fixable by** | Refactoring the method | Rethinking what a "node" is |

**The diagnostic gap:** I started diagnosing a *bug* and ended up diagnosing a *worldview*. The gap — from "API is broken" to "analysis is treated as static when it's a search problem" — is exactly the distance the concealment travels.

---

### Step 4: The Concealment Mechanism

**Infrastructural Elaboration:** Adding visible, meaningful-looking structure (nodes, edges, cache, dependency resolution) that appears to grant flexibility while actually *narrowing* what can be expressed. The architecture's elaborateness creates a **"look here" effect** — the graph topology is prominently visible, so the invisible hardcoded parameters feel like someone else's problem.

Approach 1 hides nothing because it claims nothing. Approach 2 hides more *because* it promises more.

---

### Step 5: The Legitimate-Looking Improvement That Deepens Concealment

This would pass code review. It adds documentation, observability, and performance monitoring:

```python
class AnalysisGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.cache = {}
        self.metadata = {}

    def add_step(self, name, fn, depends_on=None, description="", hyperparams=None):
        self.nodes[name] = fn
        self.edges[name] = depends_on or []
        self.metadata[name] = {
            "description": description,
            "hyperparams": hyperparams or {},   # ← documents them!
            "runs": 0,
            "last_runtime_ms": None
        }

    def run(self, name, data):
        if name in self.cache:
            return self.cache[name]
        inputs = {dep: self.run(dep, data) for dep in self.edges[name]}
        import time; t = time.time()
        result = self.nodes[name](data if not inputs else inputs)
        self.metadata[name]["last_runtime_ms"] = (time.time() - t) * 1000
        self.metadata[name]["runs"] += 1
        self.cache[name] = result
        return result

    def visualize(self):
        return {
            name: {
                "depends_on": self.edges[name],
                "hyperparams": self.metadata[name]["hyperparams"],  # visible!
                "cached": name in self.cache
            }
            for name in self.nodes
        }
```

Usage now looks responsible:

```python
graph.add_step(
    "cluster", 
    lambda inputs: kmeans(inputs["features"], k=5),
    depends_on=["features"],
    description="K-means clustering of feature vectors",
    hyperparams={"k": 5, "init": "k-means++"}   # documented!
)
```

This passes review because: it adds documentation, it makes hyperparameters *appear* visible, it adds timing for performance work, and `visualize()` looks like debugging infrastructure. A reviewer feels informed.

---

### Step 6: Three Properties Only Visible Because I Tried to Strengthen It

**1. The hyperparams field is documentation theater.**
The `hyperparams={"k": 5}` in metadata and the `k=5` inside the lambda are two separate values with no connection. Change one; the other doesn't know. By making this explicit, the improvement reveals that parametric coupling is *structural*, not incidental — the graph topology and the computation parameters exist in entirely different namespaces with no bridge between them.

**2. The cache makes the object single-use while looking reusable.**
Adding `runs` counter made it obvious: there is no cache invalidation tied to hyperparameter changes. If you try `k=5`, then want to compare `k=7`, you must reconstruct the entire graph. The elaborated version makes this concrete — `runs: 1` suggests the object is stateful and "has been run," implying it shouldn't be run again with different intent. What looked like optimization is actually a **use-once object** wearing reusable infrastructure as a costume.

**3. The `data` incoherence is now a versioning impossibility.**
With `runs` tracking, it becomes structural that the same graph instance cannot safely analyze two different datasets — the cache has no provenance. The improvement, by adding observability, makes it undeniable that the graph is coupled to exactly one execution context. Trying to serialize `metadata` for reproducibility reveals that you'd also need to serialize `data`, which isn't in scope anywhere. The thing that looked like a computation graph is actually a **frozen execution trace** after first run.

---

### The Actual Answer

Neither approach is better as written. Approach 1 is honestly limited. Approach 2 is dishonestly limited — it has real bugs *and* it hides its design constraints behind infrastructure that implies power it doesn't have.

**Approach 1 is better for:** auditability, debugging, simplicity, and cases where the pipeline is genuinely linear.

**Approach 2 would be better if:** nodes received explicit dependency outputs via properly typed parameters, the cache was keyed on `(name, data_hash, hyperparams_hash)`, and hyperparameters were nodes in the graph — not hidden inside closures.

The correct question isn't *which is better* but *what is actually needed*: if you need adaptive analysis (try k=3, 5, 7; branch on intermediate results), neither works, and you need something closer to a computation framework (Dask, prefect, or a proper DAG executor with parametric nodes).
