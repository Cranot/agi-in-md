# Approach 1 Is Better — But Approach 2 Fails for Specific, Structural Reasons

## The Quick Answer

Approach 1 (linear pipeline) is superior for this problem. Not because simplicity is always better, but because **Approach 2's abstraction is broken in ways that make it strictly worse**.

## The Deep Structural Problem

**Falsifiable claim:** The dependency graph's core defect is that it has *no coherent execution model* — it conflates graph topology with data flow semantics in the `run` method.

Look at this line:

```python
result = self.nodes[name](data if not inputs else inputs)
#                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                         The function signature CHANGES
#                         based on graph position
```

This means:
- **Root nodes** receive raw `data` (whatever type that is)
- **Interior nodes** receive a `dict` of named dependency results
- **A node function cannot be written without knowing its position in the graph**

This destroys the entire value proposition of a dependency graph.

## Three Problems That Flow From This Force

### 1. The Type Contract Is Invisible
```python
# Is this function a root or interior node? You can't tell.
def my_step(input):  # `input` is either raw data OR a dict. Good luck.
    ...
```

### 2. The Cache Defeats Reuse
```python
graph.run("summarize", dataset_A)
graph.run("summarize", dataset_B)  # Returns dataset_A's result! Cache never invalidates.
```

### 3. No Structural Validation
```python
graph.add_step("a", fn_a, depends_on=["b"])
graph.add_step("b", fn_b, depends_on=["a"])
graph.run("a", data)  # Infinite recursion. No cycle detection.
```

## Why Approach 1 Wins Here

| Dimension | Pipeline (v1) | Graph (v2) |
|---|---|---|
| **Readability** | Obvious data flow | Must trace recursive resolution |
| **Type safety** | Each function has a clear signature | Signatures depend on graph position |
| **Debuggability** | Insert a print between any two lines | Must inspect cache state + recursion |
| **Correctness** | Trivially correct ordering | No cycle detection, stale caching |
| **Honest complexity** | Looks simple, is simple | Looks powerful, is broken |

## When Would a Graph Actually Be Justified?

A dependency graph earns its complexity when you need **at least two** of these:

```
- Diamond dependencies    (A → B, A → C, B+C → D)
- Selective re-execution  (change one input, rerun only affected nodes)
- Parallel execution      (independent branches run concurrently)
```

And it would need to actually deliver them — which requires:

```python
# What a correct graph engine needs (and v2 lacks):
- Uniform node signature:    fn(named_inputs: dict) -> result  # ALWAYS
- Cache keyed on content:    cache[(name, hash(inputs))]        # not just name
- Topological validation:    detect cycles at add_step() time
- Explicit root declaration: mark which nodes receive raw data
```

## The Structural Force and Its Prediction

The underlying force here is **premature abstraction without commitment**: the graph promises generality but implements none of the invariants that make generality safe. This predicts the *next* failure precisely — someone will add a node that depends on two prior steps with different output shapes, and will discover that the `inputs` dict is unstructured, untyped, and gives no indication of what it contains.

**Bottom line:** Pick Approach 1. If you later genuinely need a DAG, use a proven framework (Airflow, Prefect, Dask, Hamilton) rather than hand-rolling one that collapses under its own abstractions.
