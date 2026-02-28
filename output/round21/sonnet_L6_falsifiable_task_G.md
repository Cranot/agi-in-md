## Falsifiable Hypothesis

**Claim:** Approach 2's deepest structural problem is its *dual calling convention*—leaf nodes receive raw `data`, non-leaf nodes receive a `{dep_name: result}` dict—making individual nodes untestable in isolation and the graph non-composable. This makes Approach 2 structurally worse than Approach 1 for any real-world use case.

---

## Three Experts Argue

### Expert 1: Defender

The dual calling convention isn't just a bug—it's an architectural failure baked into the design. Look at the code directly:

```python
result = self.nodes[name](data if not inputs else inputs)
#                         ^^^^                   ^^^^^^
#                    raw data              {dep_name: output}
```

A function's expected signature now depends on its *position in the graph*, not its contract. You cannot unit-test `scale_features` without constructing a partial graph. You cannot reuse `remove_nulls` as both a leaf and a mid-graph node. The cache compounds this: it's mutable instance state tied to raw data, meaning you cannot run the same graph on different datasets without creating a new instance. The graph conflates *topology* (which nodes connect to which) with *execution state* (cached results). These must be separate concerns.

---

### Expert 2: Attacker

The defender is criticizing a specific implementation, not the architecture. Any graph engine has a calling convention; this one is fixable in 10 lines. The *actual* deep structural problem is in **Approach 1**:

```python
def analyze_v1(data):
    cleaned = remove_nulls(data)       # ← what if something else needs `cleaned`?
    normalized = scale_features(cleaned)
    features = extract_features(normalized)
    ...
```

This is a single-entry, single-exit linear chain. The moment requirements change—add anomaly detection that also consumes `cleaned`, run two clustering algorithms and compare—you must either recompute `remove_nulls` twice, introduce globals, or restructure the entire function. The pipeline's rigidity *is* the structural problem. Approach 2's architecture is correct; its implementation is just immature.

---

### Expert 3: Assumption Prober

Both arguments assume the primary structural virtues are *reusability* and *testability*. But they take for granted something deeper: **what problem is actually being solved?**

Neither approach encodes data schemas at step boundaries. When `scale_features` receives the wrong shape from `remove_nulls`, both approaches fail silently at runtime. Neither makes the *data contract* between steps explicit. Approach 1 fails invisibly when signatures don't match. Approach 2 fails invisibly *and* hides which convention a function even needs to satisfy.

More critically: the cache assumes analysis is **pure and deterministic**. What if `remove_nulls` should behave differently based on context, or data mutates? The cache doesn't know. There's also no invalidation strategy at all. This is a structural assumption neither expert examined.

---

## What the Argument Revealed

| Assessment | Detail |
|---|---|
| **Partially falsified** | The dual calling convention is a *fixable implementation flaw*, not an architectural condemnation of graph-based approaches |
| **Strengthened** | The interface inconsistency is real and consequential—it's harder to fix correctly than it appears, because it requires redesigning how `data` flows through every node |
| **Transformed** | The *deepest* structural problem is that **neither approach encodes data contracts at boundaries**—Approach 1 silently mismatches types, Approach 2 silently mismatches calling conventions |

---

## What I Know Now That I Couldn't Before

The question "which is better?" was the wrong frame. Here's the honest map:

```
Fixed pipeline, known steps:     Approach 1 wins (readable, debuggable, obvious)
DAG with shared intermediates:   Approach 2's architecture wins, implementation loses
Either approach at scale:        Both lose to typed, schema-validated pipelines (e.g., Prefect, Dagster, or even dataclasses at boundaries)
```

Approach 2's implementation has **three concrete, fixable bugs** that the debate surfaced:

```python
# Bug 1: Dual calling convention — fix by always passing inputs dict, even for roots
inputs = {dep: self.run(dep, data) for dep in self.edges[name]}
result = self.nodes[name](inputs or {"__data__": data})  # uniform interface

# Bug 2: Cache tied to instance — separate graph topology from execution context
class ExecutionContext:
    def __init__(self): self.cache = {}

# Bug 3: No cache invalidation — cache assumes purity it cannot enforce
# Fix: Either enforce pure functions (typing) or make cache opt-in per node
```

The real structural lesson: **Approach 2 chose complexity without buying safety**. A graph engine earns its complexity when it provides parallelism, explicit contracts, and composability. This implementation provides none of those—it adds indirection while remaining just as fragile as the linear pipeline, only harder to read.
