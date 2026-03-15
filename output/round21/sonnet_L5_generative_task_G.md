## Pattern: Implicit vs. Explicit Dependency Graph

The problem instantiates **Structure-as-Execution vs. Structure-as-Data** — the question of whether computational dependencies are *encoded in ordering* or *declared as relationships*. This specific tension generates the three most useful operations to apply here.

---

## Operation 1 (Concrete): Coupling Audit — What breaks when one step changes?

Trace a single change through each design.

**V1:** Change `k=5` to adaptive k-selection, or insert a deduplication step before normalization.

```python
# Must manually re-sequence. The pipeline IS the dependency structure.
def analyze_v1(data):
    cleaned = remove_nulls(data)
    deduplicated = dedup(cleaned)        # inserted — but where? you must know context
    normalized = scale_features(deduplicated)  # downstream rename cascades
    ...
```

Every change requires *reading the full pipeline* to understand impact. The dependency structure is implicit in variable names.

**V2:** Declare the new node, declare its edges. Unaffected paths don't change.

```python
graph.add_step("dedup", dedup_fn, depends_on=["remove_nulls"])
graph.add_step("normalize", scale_fn, depends_on=["dedup"])  # one edge change
```

**Finding:** V1's coupling is tight and positional. V2's coupling is explicit and local. Advantage: V2 — *for non-trivial graphs*.

---

## Operation 2 (Intermediate): Execution Topology — What shapes can each approach actually represent?

V1 can only represent a **chain** (linear DAG). V2 can represent an **arbitrary DAG** — one node's output feeding multiple downstream nodes without recomputation, thanks to `self.cache`.

```
V1 topology:      A → B → C → D → E → F    (chain only)

V2 topology:      clean ──→ feature_A ──→ cluster_A ─→ summary
                        ↘                              ↗
                          feature_B ──→ cluster_B ──→
```

V2's cache is the critical mechanism here — it makes diamond dependencies (`A → B, A → C, B+C → D`) computationally sound. V1 would require duplicating `A` or pulling it out of the function entirely.

**However — V2 has a structural bug in its `run` method:**

```python
# THE BUG:
result = self.nodes[name](data if not inputs else inputs)
```

This creates a **broken API contract**:
- Leaf nodes receive raw `data`
- Non-leaf nodes receive only `{dep_name: result}` — **raw data is silently discarded**

Any node needing both upstream results *and* the original data (e.g., a validator comparing normalized output against raw) receives neither correctly. The ternary makes the calling convention *depend on graph position*, which is hidden from the function author.

A correct signature would be:

```python
result = self.nodes[name](data, inputs)  # always pass both; function decides what to use
```

**Finding:** V2's topology is strictly more expressive, but the implementation has a latent data-loss bug that V1 — despite its rigidity — cannot suffer.

---

## Operation 3 (Abstract): Representational Overhead vs. Capability Gain

Ask: what does each approach *cost to encode*, and what does it *make possible* at that cost?

| Dimension | V1 | V2 |
|---|---|---|
| **To encode a 6-step linear pipeline** | 6 lines | ~12 lines + wiring |
| **To add memoization** | Wrap each function manually | Free via cache |
| **To add parallelism** | Rewrite control flow | Topological sort → thread pool |
| **To inspect dependencies** | Read source code | Query `self.edges` |
| **To test one step in isolation** | Mock all predecessors | Inject into graph at named node |
| **To catch the API bug above** | N/A | Requires interface discipline V1 doesn't |

**The crossover point:** V2 earns its overhead when the graph has branching, shared computation, or needs to be *reasoned about as data* (serialized, visualized, modified at runtime). For a strict 6-step linear pipeline that never changes, V2 is overhead without return.

**Finding:** Neither is categorically better. V1 is correct and sufficient for the shown use case. V2 is architecturally superior *for the class of problems it's designed for*, but the shown implementation is not yet correct.

---

## The Inversion: What Operation Can't This Frame Generate?

The **Structure-as-Data** frame assumes **static topology** — dependencies are declared before execution and don't change. Neither approach can represent:

> **Runtime-adaptive dependency graphs** — where the structure of computation is itself a function of intermediate results.

Example: after clustering, discovering that one cluster is degenerate and needs a *different* feature extraction branch only for that cluster. The dependency graph isn't known until partial execution has occurred.

The missing operation is **conditional graph rewriting** — generating new nodes and edges mid-execution based on computed values. Neither approach reaches for this because both treat the graph as a fixed structure over data, when sometimes the data should determine the graph. Frameworks like Dask or JAX's `jit` trace touch this, but no simple graph class generates it naturally from the dependency-declaration frame.

---

## Verdict

**Use V2's architecture, fix its API contract, and only adopt it when your pipeline is non-linear.** For the exact code shown: V1 is more correct (no bugs), V2 is more capable (wrong implementation). The right answer is V2 with the `run` signature fixed.
