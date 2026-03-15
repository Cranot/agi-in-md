# Falsifiable Claim

**The dependency graph (Approach 2) is structurally *worse* than the linear pipeline because its core execution contract is incoherent: the `run` method forces each node function to know its own topological position in the graph, destroying the very composability that justifies a DAG architecture in the first place.**

The critical line is this one:

```python
result = self.nodes[name](data if not inputs else inputs)
```

Root nodes receive raw `data`. Non-root nodes receive a `dict` of dependency outputs. These are completely different function signatures, which means nodes are not interchangeable — the fundamental promise of a graph-based design.

---

## The Argument

### Expert 1 (Defender): "The claim is correct and deeper than stated."

The problem isn't just the branching signature. Follow the `data` parameter through recursion:

```python
def run(self, name, data):
    ...
    inputs = {dep: self.run(dep, data) for dep in self.edges[name]}
    result = self.nodes[name](data if not inputs else inputs)
```

Every recursive call passes the **same original `data`** to every node. This means the graph doesn't actually *compose* — it *fans out from a single source and then prays* that non-root functions ignore the `data` argument. The cache also has no invalidation, so if you call `run` with different `data`, you get **stale results from the previous dataset**. The architecture has three compounding flaws, not one.

### Expert 2 (Attacker): "This is a fixable implementation bug, not a structural problem."

The claim confuses a *bad implementation* with a *bad architecture*. The fix is trivial:

```python
def run(self, name, data):
    if name in self.cache:
        return self.cache[name]
    deps = {dep: self.run(dep, data) for dep in self.edges[name]}
    result = self.nodes[name](data=data, deps=deps)  # always pass both
    self.cache[name] = result
    return result
```

Now every function has a uniform contract. The graph architecture still gives you caching, partial re-execution, and parallelizability — none of which the linear pipeline offers. Judging Approach 2 by its worst line of code rather than its structural affordances is a category error.

### Expert 3 (Presupposition Prober): "Both sides assume the graph needs to exist."

The linear pipeline processes **one path through six steps**. There are no diamonds, no shared intermediate results, no branches. When do you actually *need* a DAG?

- When steps have **shared dependencies** (diamond patterns)
- When you need **partial re-execution** after parameter changes
- When you want **parallel execution** of independent branches

None of these are demonstrated in the problem. The graph adds a cache, but the linear pipeline could add memoization to any individual function with a decorator. The real question isn't which implementation is better — it's whether the problem *has graph structure at all*. If it doesn't, Approach 2 is **accidental complexity** masquerading as generality.

---

## Verdict: Claim Transformed

The argument didn't falsify the claim — the incoherent data contract is real and serious. But Expert 3 reframed what matters.

### What I know now that I couldn't know before:

**Approach 1 is better for *this* problem**, but not because Approach 2 is architecturally wrong in general. The deeper insight is a **decision rule**:

| Choose the linear pipeline when... | Choose the dependency graph when... |
|---|---|
| Steps form a single chain | Steps form a diamond or fan-out DAG |
| You iterate on step logic | You iterate on step *topology* |
| Debuggability matters most | Partial re-execution matters most |
| The team is small | Multiple teams own different nodes |

Approach 2 isn't bad architecture — it's **premature architecture**. It pays the complexity cost of a graph (unclear data contracts, cache invalidation, implicit execution order) without having a problem that requires graph structure. The linear pipeline is honest about what the computation actually *is*: a chain. And a chain that calls itself a chain is always better than a chain that pretends to be a graph.
