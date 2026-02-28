# Structural Diagnostic: Linear Pipeline vs. Dependency Graph

## The Falsifiable Claim

**The dependency graph (Approach 2) is structurally *less capable* than the linear pipeline (Approach 1), despite presenting as its generalization.** Specifically: the graph cannot express a node that needs both raw data and a computed dependency, due to this line:

```python
result = self.nodes[name](data if not inputs else inputs)
```

This is an XOR gate masquerading as a router. A node gets raw `data` **or** its dependency outputs. Never both. The linear pipeline has no such restriction.

---

## Three Experts Pressure-Test the Claim

**Expert A (Defender):** Correct. This isn't just an API wart — it reveals that the graph models *computational ordering* but not *data flow*. The edges say "what must run first" but cannot express "what each step actually receives." The graph is a scheduler pretending to be an architecture.

**Expert B (Attacker):** That's a surface bug. Fix it with `fn(data=data, deps=inputs)` and it disappears. The *deeper* problem is the cache. It's keyed by step name only — not by input data. Call `.run("cluster", dataset_A)` then `.run("cluster", dataset_B)` and you silently get dataset_A's clusters. The graph is **statefully wrong on reuse**, which is far more dangerous than a routing limitation.

**Expert C (Probes shared assumptions):** You're both assuming the graph *should* generalize the pipeline. But neither approach models what actually fails in data analysis: **schema and shape contracts between steps.** Does `kmeans` receive the shape `extract_features` produces? Neither approach can answer this at construction time. The linear pipeline at least makes the ordering human-verifiable. The graph makes compatibility *harder* to reason about while adding zero safety.

## The Transformed Claim

The graph adds three forms of complexity — **topology management, caching, recursive resolution** — each introducing independent failure modes:

| Added Complexity | Failure Mode |
|---|---|
| Dependency edges | Data routing incoherence (XOR gate) |
| Result cache | Silent staleness on reuse (keyed by name, not data) |
| Recursive resolution | Unbounded recursion on cycles (no detection) |

It provides **zero additional safety guarantees** over the linear pipeline. It trades legibility for an abstraction that doesn't abstract over the things that actually go wrong in data analysis (schema mismatches, shape errors, violated statistical assumptions).

**The diagnostic gap:** My original claim targeted a single bug. The transformed claim reveals that bug as a *symptom* of a design that doesn't understand what it's abstracting. The author modeled **computational dependency** when they should have modeled **data contracts**.

---

## The Concealment Mechanism

**"Structural sophistication as competence signal."** The graph pattern *looks* well-architected — DAGs, caching, dependency injection are recognized engineering patterns. This sophistication conceals that it solves problems the linear pipeline doesn't have while failing to solve problems both share.

## An Improvement That Deepens the Concealment

This would pass code review and looks like a legitimate fix:

```python
def run(self, name, data, force=False):
    if name in self.cache and not force:
        return self.cache[name]
    inputs = {dep: self.run(dep, data) for dep in self.edges[name]}
    context = {"data": data, "deps": inputs}
    result = self.nodes[name](**context)
    self.cache[name] = result
    return result
```

It fixes the XOR routing. It adds `force` for cache bypass. A reviewer sees two real bugs addressed. **But it deepens the concealment:**

## Three Properties Visible Only Because I Tried to Strengthen It

1. **The cache becomes more dangerous, not less.** Now that routing looks correct, reuse looks safe — but cache is still keyed by name alone. `run("clean", new_dataset)` returns the old dataset's results. The fix made the trap more inviting.

2. **`force=True` turns latent cycles into live infinite recursion.** Without `force`, a cycle would at least terminate (hitting cache on the second pass). With `force`, it spins forever. Adding a safety valve created a detonator.

3. **The `**context` unpacking silently imposes a function signature contract** (`data`, `deps`) that is nowhere declared or enforced. Every step function must now accept exactly these keyword arguments. The graph became both more coupled and more brittle — but the coupling is invisible because it lives in argument names, not in types or interfaces.

---

## The Verdict

**Approach 1 is better.** Not because linear pipelines are always superior, but because Approach 2 pays the complexity cost of a DAG framework while delivering none of its benefits. A well-built dependency graph would need: typed edges, cache keyed by content hash, cycle detection, and explicit data routing. Without those, you've replaced six readable lines with a framework that is harder to debug, silently stateful, and structurally less expressive than what it replaced.

The linear pipeline's greatest virtue is that **its failure modes are visible at the point of failure.** The graph's greatest vice is that its failure modes are visible only at the point of *consumption* — far downstream, in wrong results that look right.
