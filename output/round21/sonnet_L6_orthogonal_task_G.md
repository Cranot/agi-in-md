## Prediction (Before the Experts Argue)

**What all three will miss:** The `run` method has a broken calling convention. Leaf nodes get called as `fn(data)`, but nodes with dependencies get called as `fn({"dep_name": result, ...})`. Every real analysis function would need to be rewritten to handle a dict-of-results instead of actual data — the graph is architecturally interesting but mechanically non-functional as written.

---

## The Expert Debate

---

### Expert 1: The Architect (Sees Strengths)

Approach 2 is categorically better. Approach 1 is a procedural script pretending to be architecture. It has six hidden coupling points — change `scale_features` to produce a different shape and you silently break everything downstream. You only discover this at runtime.

The `AnalysisGraph` solves real problems:

```python
# Approach 1: want to skip normalization for one analysis? You rewrite the function.
# Approach 2:
graph.add_step("features_raw", extract_features, depends_on=["cleaned"])
graph.add_step("features_norm", extract_features, depends_on=["normalized"])
# Two paths, zero duplication
```

The cache is the killer feature. In exploratory data science, you re-run analyses constantly. With Approach 1, cleaning and normalizing 10 million rows runs every time. With `AnalysisGraph`, you pay once. The cache turns iterative development from O(n × steps) to O(n + steps).

The dependency graph also enables parallelism that Approach 1 physically cannot express:

```python
# These have no dependency relationship — run them concurrently
graph.add_step("cluster_features", kmeans, depends_on=["normalized"])
graph.add_step("anomaly_score", isolation_forest, depends_on=["normalized"])
```

Approach 1 serializes everything. Approach 2 makes the execution topology explicit and therefore optimizable.

---

### Expert 2: The Reliability Engineer (Sees Failure Modes)

The Architect is describing an idealized version of Approach 2. The actual code has several defects that make it unreliable in practice.

**The cache is data-blind:**

```python
self.cache = {}  # keyed by name only, not by (name, data)
```

```python
graph.run("labeled", dataset_A)  # caches results for dataset_A
graph.run("labeled", dataset_B)  # returns cached dataset_A results silently
```

This is the single most dangerous line in the codebase. It fails silently, with plausible-looking results. The `AnalysisGraph` is not a reusable component — it's a single-use object masquerading as one. Every reuse after the first is a data corruption bug.

**The error handling is nonexistent:**

```python
inputs = {dep: self.run(dep, data) for dep in self.edges[name]}
```

If any dependency fails, the exception propagates with a bare stack trace that tells you nothing about *which node* failed, *which dependency chain* led there, or *what the input state was*. In a 20-node graph you get `KeyError: 'normalized'` and then you're debugging execution order by hand.

**The recursion has no cycle detection:**

```python
# add_step("A", fn, depends_on=["B"])
# add_step("B", fn, depends_on=["A"])
# graph.run("A", data)  → RecursionError: maximum recursion depth exceeded
```

No visited-set, no topological sort pre-validation, no cycle guard. Approach 1 cannot have cycles by construction. Approach 2 introduces the possibility and provides no defense.

Approach 1 is correct. Approach 2 is a prototype that needs another month of work before it's production-worthy.

---

### Expert 3: The Pragmatist (Sees What Both Miss)

Both of you are treating this as a religious question — architecture vs. reliability — and missing the actual frame.

**The comparison is false.** Approach 1 and Approach 2 don't solve the same problem. Approach 1 solves *running this analysis once on this data*. Approach 2 solves *expressing a family of analyses that share computational subgraphs across multiple runs*. If you have one pipeline and one dataset, Approach 2 adds complexity with no payoff. If you have 15 analysts running variants of the same pipeline on streaming data, Approach 1 can't express the problem at all.

**The Architect is right about the value proposition but wrong about the implementation being there.** The Reliability Engineer is right about the bugs but wrong about concluding Approach 1 is better — fixing those bugs is mechanical, not architectural.

**The real question both of you ignore:** What happens to Approach 1 when requirements change?

```python
# Six months later:
def analyze_v1(data):
    cleaned = remove_nulls(data)
    normalized = scale_features(cleaned)
    # New requirement: try two clustering algorithms and pick the better one
    features = extract_features(normalized)
    clustered_k = kmeans(features, k=5)        # added
    clustered_db = dbscan(features, eps=0.3)   # added
    best = pick_best(clustered_k, clustered_db) # added
    labeled = assign_labels(best)              # now depends on pick_best, not clustered
    return summarize(labeled)
```

Approach 1 has become spaghetti. Not because it was designed badly, but because linear pipelines have no natural representation for branching. Approach 2's graph structure makes branching first-class. The Architect's argument is really about *evolvability*, which neither of you named.

---

## Assessment: Did They Miss My Prediction?

**Yes. All three missed it entirely.**

Not one expert noticed that the calling convention is broken:

```python
# Node with no dependencies — receives raw data
result = self.nodes[name](data if not inputs else inputs)
# fn(DataFrame)  ← what the function expects

# Node with dependencies — receives a dict of results  
result = self.nodes[name](data if not inputs else inputs)
# fn({"cleaned": DataFrame, "normalized": DataFrame})  ← what it actually gets
```

`scale_features` in any real implementation expects a DataFrame. In this graph, if it has dependencies, it receives `{"cleaned": DataFrame}`. The function will fail with a type error on first use. You cannot port Approach 1's functions into Approach 2 without wrapping every single one:

```python
# What you'd actually need:
def scale_features_wrapped(inputs):
    return scale_features(inputs["cleaned"])  # manually unpack every time
```

This means Approach 2 doesn't reduce coupling — it *relocates* it into implicit naming conventions inside each wrapper function.

---

### Why Was It Invisible to All Three Frames?

Each expert had a frame that immunized them against seeing it:

| Expert | Frame | Why the bug was invisible |
|--------|-------|--------------------------|
| Architect | "Does the architecture compose?" | Yes, nodes connect to nodes. Calling convention is below the level of abstraction being evaluated. |
| Reliability Engineer | "Does the system fail safely?" | Found the cache bug and stopped there — confirmation bias, one major bug felt sufficient. |
| Pragmatist | "Does the design express the problem?" | Focused on the meta-question of evolvability, treating the code as pseudocode rather than executable. |

The deeper reason: all three argued about *design intent* rather than *execution mechanics*. The bug lives in a single conditional expression — `data if not inputs else inputs` — which is syntactically small and semantically catastrophic. Big-picture thinking creates systematic blind spots for small-but-fatal details.

**What this reveals about my own predictive process:** I found the bug by reading the code mechanically before forming an opinion. The experts formed opinions and then read the code to confirm them. The orthogonal prediction worked because it required no position on the "which is better" question — only attention to what the code actually does, divorced from what it tries to do.
