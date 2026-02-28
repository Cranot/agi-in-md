# Recursive Falsification Analysis: Two Pipeline Architectures

---

## Initial Orientation

Before the dialectic: Approach 1 is a linear composition of named functions. Approach 2 is a graph where nodes are functions and edges are dependencies, with memoization. The surface question is "which is better?" The structural question is *what does better even mean here?*

---

## First Claim (Specific and Falsifiable)

> **Approach 2's deepest structural problem is that its `run` method enforces two mutually incompatible calling conventions on node functions, making the graph topology undiscoverable at function-definition time.**

Specifically, this line:

```python
result = self.nodes[name](data if not inputs else inputs)
```

A **leaf node** (no dependencies) receives raw `data`. An **internal node** (has dependencies) receives a `dict` of results: `{"dep_name": dep_result, ...}`.

**Falsifiability test:** Write a single function that works correctly as *both* a leaf and an internal node. You can't — each position demands a different signature. The topology is declared in `add_step`, but the calling contract is baked into the function body invisibly. This is demonstrably true, not a matter of opinion.

---

## The Expert Panel

### Expert A — Defender

The claim is correct and the consequence is severe. Consider:

```python
# This works as a leaf:
def clean(data): return remove_nulls(data)

# This works as internal:
def normalize(inputs): return scale_features(inputs["clean"])

# Now try to reuse `clean` as a dependency of something else
# AND as a standalone step. You cannot write one function body
# that handles both cases.
```

The graph's *structure* is open and declarative; the node functions' *contracts* are closed and positional. You've added graph complexity without gaining graph flexibility.

---

### Expert B — Attacker

The calling convention is an ergonomic annoyance — fixable with a two-line adapter. It is *not* the deepest problem. The **cache is the deepest problem**, and it's a correctness failure, not a style failure:

```python
self.cache = {}  # Keyed only by step name, not by input data
```

```python
graph.run("clustered", dataset_A)  # Computes, caches under "clustered"
graph.run("clustered", dataset_B)  # Returns dataset_A's result. Silently.
```

The cache key ignores input entirely. The object *appears* reusable; it actually silently corrupts results on reuse. The calling convention makes the API awkward. The cache makes the system *wrong*.

---

### Expert C — Probing Assumptions

Both of you are assuming Approach 2 is meant to be instantiated once and reused across datasets. But hold that aside — both of you are also taking for granted something more foundational: **that node functions are the right unit of parameterization.**

Look at what's missing in *both* approaches:

```python
# Approach 1: k is hardcoded
clustered = kmeans(features, k=5)

# Approach 2: k lives inside a closure or lambda, invisible to the graph
graph.add_step("clustered", lambda inputs: kmeans(inputs["features"], k=5))
```

Neither approach has a mechanism for **parametric variation across runs** — asking "how does the result change as k varies from 2 to 10?" requires architectural surgery in *both*. The dependency graph purchases execution-order flexibility (real, but limited). It does not purchase parametric flexibility — which is the flexibility exploratory data analysis actually demands.

The calling convention and the cache are downstream symptoms of a more fundamental decision: treating the analysis as a *transformation* (data → result) rather than a *function* (data × parameters → result).

---

## The Claim Transforms

The original claim — that the calling convention is Approach 2's deepest problem — was accurate but localized. Expert B revealed a correctness failure more serious than ergonomics. Expert C revealed that both problems are *symptoms*: the architecture doesn't model parameters as first-class inputs.

**Transformed understanding:** Approach 2's graph structure is declarative about *topology* but opaque about *parameterization*. Parameters live inside node closures, invisible to the graph. This makes the graph replayable (given same data and parameters), but not explorable (given same data, varying parameters).

---

## Second Claim (Unreachable from First Pass)

> **Both approaches share a structural failure that is prior to their differences: they model the analysis as `f(data) → result` when exploratory data analysis requires `f(data, params) → result`. The dependency graph's added complexity is justified only if it unlocks something the linear pipeline cannot do. It unlocks DAG execution and memoization — but not parametric exploration — which means it pays architectural cost for the wrong kind of flexibility.**

More precisely:

| Flexibility Type | Approach 1 | Approach 2 |
|---|---|---|
| Reorder steps | ✗ (requires code edits) | ✓ (add/remove edges) |
| Share intermediate results | ✗ (recompute) | ✓ (cache) |
| Vary parameters across runs | ✗ | ✗ (cache masks it) |
| Test a single step in isolation | Awkward | Awkward |
| Express "how does k affect clusters?" | Requires loop outside | Requires graph rebuild |

Approach 2 is strictly more complex than Approach 1. Complexity is justified when it purchases capability that simpler code cannot provide. Approach 2 purchases DAG execution — useful when the dependency structure genuinely isn't linear. For this pipeline (which *is* linear), it purchases nothing but adds bugs.

---

## Is the Second Claim Categorically Deeper?

**Yes — categorically, not incrementally.**

| | First Claim | Second Claim |
|---|---|---|
| **Unit of analysis** | Approach 2's internal consistency | Both approaches' adequacy for their purpose |
| **Type of problem** | Bug (fixable with a patch) | Absent dimension (requires different architecture) |
| **Fix required** | Standardize calling convention; fix cache key | Reframe pipeline as `(data, params) → result` |
| **What it questions** | How Approach 2 works | What either approach *can express* |

The first claim found what was *broken*. The second claim found what was *absent*. Absence problems are categorically harder because no local fix addresses them — the code has no place to put the missing thing.

---

## What the Distance Reveals

The gap between the two claims reveals the structural limit of single-pass analysis:

**Single-pass analysis is essentially static analysis of what is present.** It finds bugs, inconsistencies, and code smells — all real, all tractable. Expert A and Expert B both operated in this mode.

**The recursive pass asks what is absent.** This requires understanding the *use context* (EDA = iterative, parametric exploration) and testing whether the architecture can even *accommodate* that context. Expert C opened this door; the second claim walked through it.

The practical implication: when evaluating architecture, the most important question isn't "does this work?" or even "does this have bugs?" It's: **"what questions can this code not ask, and are those the questions that matter?"**

For this pipeline, the question that matters is: *"What happens when I change a parameter?"* Neither approach answers it. That's the finding single-pass analysis cannot reach.

---

## Concrete Verdict

**Approach 1 is better for this code as written** — it is simpler, correct, and readable. Approach 2 is architecturally motivated (DAGs *are* more expressive) but the implementation is broken in ways that make it worse than the simple version it replaced.

**The architecture worth building** is neither — it's a parameterized pipeline:

```python
def analyze(data, params: AnalysisParams):
    # params carries k, normalization strategy, feature config, etc.
    # each step is a pure function of (data, params)
    # exploration becomes: [analyze(data, p) for p in param_grid]
```

That's the claim only the dialectic could produce.
