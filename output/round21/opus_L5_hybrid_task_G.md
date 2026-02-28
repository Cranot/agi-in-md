# Pipeline vs. Dependency Graph: A Deep Comparison

## Pattern Classification

This is the **Linear Composition vs. DAG Orchestration** trade-off — a recurring architectural decision in workflow design between sequential simplicity and graph-based flexibility.

---

## Three Analytical Operations

I'll derive these from the specific code properties, not generic principles:

| # | Operation | Derived From |
|---|-----------|-------------|
| 1 | **Structural Flexibility** — how each handles topology changes | The rigid 6-step chain vs. the `add_step`/`depends_on` API |
| 2 | **Runtime Behavior** — caching, recomputation, failure modes | The explicit `self.cache` in Approach 2, absent in Approach 1 |
| 3 | **Cognitive Load & Correctness** — hidden bugs, reasoning cost | The complexity gap and the suspicious `data if not inputs else inputs` line |

**My prediction:** Operation 3 will yield the deepest insight. The conventional reading favors Approach 2 as "more sophisticated," but that ternary expression smells like a fundamental design flaw that undermines the entire abstraction.

---

## Executing All Three

### Operation 1: Structural Flexibility → Advantage Approach 2

Approach 1 is a rigid chain. Want to run both K-means *and* DBSCAN on the same features? You refactor the whole function. Want to skip normalization? Conditional logic everywhere.

Approach 2 models a DAG. You can express diamonds, branches, and partial execution:

```
clean ──→ normalize ──→ features ──┬──→ kmeans
                                   └──→ dbscan
```

**Verdict:** Approach 2 wins on flexibility.

### Operation 2: Runtime Behavior → Advantage Approach 2, with caveats

The cache means shared upstream steps compute once. But three serious runtime issues lurk:

```python
# Problem 1: No cache invalidation
# If data changes, you get stale results silently

# Problem 2: No cycle detection  
# This creates infinite recursion, not a helpful error:
graph.add_step("a", fn_a, depends_on=["b"])
graph.add_step("b", fn_b, depends_on=["a"])

# Problem 3: No parallelism despite enabling topology
# Dependencies resolve sequentially in the dict comprehension
inputs = {dep: self.run(dep, data) for dep in self.edges[name]}
```

**Verdict:** Approach 2 wins on caching, but the implementation is fragile.

### Operation 3: Correctness & Cognitive Load → **Advantage Approach 1** ✦

This is where the real story is. Look at this line carefully:

```python
result = self.nodes[name](data if not inputs else inputs)
```

**This is a broken abstraction.** It creates two incompatible function signatures:

```python
# Root nodes receive raw data:
def clean(data):          # data = original dataset
    ...

# Non-root nodes receive a dict of named dependency outputs:
def cluster(inputs):      # inputs = {"features": array, ...}
    features = inputs["features"]  # must know string name of dependency!
    ...
```

This means:
- **Functions are coupled to their graph position.** A node function must know whether it's a root or not, and must know the *string names* of its dependencies to unpack them. Move a node in the graph, and the function breaks.
- **Functions aren't reusable.** You can't take `cluster()` and use it in a different graph with different dependency names without rewriting it.
- **Type signatures are inconsistent.** No type checker can help you here.

Now compare Approach 1:

```python
cleaned = remove_nulls(data)        # Clear input, clear output
normalized = scale_features(cleaned) # You can inspect 'cleaned' trivially
features = extract_features(normalized)
```

Every intermediate value is named, inspectable, and typed. Debugging is inserting a `print`. Onboarding a new developer takes 10 seconds.

**Verdict:** Approach 1 wins decisively on correctness and clarity.

---

## The Real Answer

**Neither is "better." They solve different problems, and Approach 2 as written is subtly broken.**

| Criterion | Winner | Margin |
|-----------|--------|--------|
| Readability | Approach 1 | Massive |
| Debuggability | Approach 1 | Large |
| Correctness | Approach 1 | Large (Approach 2 has a flawed core abstraction) |
| Flexibility | Approach 2 | Large |
| Caching/reuse | Approach 2 | Moderate (no invalidation) |
| Production-readiness | **Neither** | — |

**The right synthesis** would fix Approach 2's core flaw by giving nodes explicit typed inputs:

```python
# Each function declares what it needs, not where it is in a graph
def add_step(self, name, fn, inputs_map=None):
    """inputs_map: {'param_name': 'dependency_node_name'}"""
    ...

# Now functions have stable, position-independent signatures:
def cluster(features, k=5):  # No knowledge of graph topology
    return kmeans(features, k)

graph.add_step("cluster", cluster, inputs_map={"features": "extract"})
```

---

## Prediction Inversion

**Was I right?** Yes — Operation 3 produced the deepest insight. The `data if not inputs else inputs` line isn't just "a bit messy." It's a **fundamental contract violation** that makes the entire DAG abstraction leak.

**What does the gap reveal?** My prediction was accurate, which suggests a meta-blind-spot: when I correctly anticipate where the insight is, I risk *anchoring* on it and under-exploring the other operations. In this case, Operation 2's cycle-detection gap was nearly as important and deserved more attention.
