## Three Experts in Disagreement

---

### Expert 1: The Architect — "The Graph Is Clearly Superior"

Approach 1 is brittle by design. It's a hard-coded sequence with zero structural flexibility. Want to reuse `extract_features` for a different downstream task? You can't without copy-pasting. Want to skip `scale_features` for a categorical-only dataset? You're refactoring the entire function.

The dependency graph solves real problems:

- **Explicit dependencies** replace implicit ordering — you *see* what each step needs
- **Caching** prevents redundant computation when multiple nodes share an ancestor
- **Composability** — add, remove, or rewire steps without touching others

This is how production pipelines are built. Tools like Airflow, Prefect, and dbt all converge on DAG-based execution for exactly these reasons. Approach 1 is a script; Approach 2 is an architecture.

---

### Expert 2: The Engineer — "Approach 2 Has a Serious Bug, and Approach 1 Is Honest"

The architect is arguing for the *idea* of a dependency graph, not this implementation. Look closely:

**Bug 1 — Cache ignores input data:**
```python
def run(self, name, data):
    if name in self.cache:
        return self.cache[name]  # ← returns cached result regardless of what `data` is
```
Call `graph.run("labeled", dataset_A)`, then `graph.run("labeled", dataset_B)` — you silently get dataset A's results. This is a correctness failure, not a style issue.

**Bug 2 — Incoherent function contract:**
```python
self.nodes[name](data if not inputs else inputs)
```
Leaf nodes receive raw `data`. Interior nodes receive a `dict` of upstream results. Every registered function must know whether it's a leaf or not, coupling function signatures to graph topology. This breaks encapsulation entirely.

**Approach 1's honest virtues:**
- Debuggable — step through it linearly
- The contract is obvious — each function takes and returns transformed data
- No hidden state, no cache invalidation problem
- For a linear pipeline, a linear structure is *correct*

Premature abstraction has real costs. This graph introduces two failure modes the pipeline never had.

---

### Expert 3: The Epistemologist — "You're Both Debating the Wrong Thing"

Neither of you noticed that this code has a hardcoded `k=5` in the middle of a supposedly general-purpose architecture, and neither implementation lets you ask: *was k=5 right?*

Both frameworks treat the analysis as a black box execution problem. But the actual work of data analysis is **iterative and interrogative**:

- What if k should be 3 or 8? Neither approach makes experimentation easy
- What if `scale_features` *shouldn't* run before clustering for this data type? Neither approach surfaces that question
- Neither tracks **why** steps are chained this way, only **that** they are

The linear pipeline at least exposes its assumptions nakedly. The graph *hides* the k=5 inside a closure, wraps it in infrastructure, and makes it look like a solved problem.

Both of you are also ignoring the observable reality: this is a six-step pipeline. The complexity cost of Approach 2 is paid *now*; the benefit only accrues if the pipeline grows or fans out. For the code as written, you're debating whether to buy a forklift or carry the box.

---

## What the Argument Itself Reveals

The three experts can't resolve their disagreement because **they're optimizing for different futures:**

| Expert | Implicit Assumption |
|--------|-------------------|
| Architect | This pipeline will grow and branch |
| Engineer | This pipeline should work correctly first |
| Epistemologist | This pipeline will be questioned, not just run |

That tension is the real finding. The code comparison surfaces a deeper design question that neither snippet answers: **What is the rate of change of this pipeline?**

- If it's a one-time analysis: Approach 1 wins on honesty and debuggability
- If it branches (e.g., multiple clustering algorithms, multiple feature sets): a graph wins — but not *this* graph
- If it's experimental/research: neither wins; you want something like a notebook with checkpoints, not a pipeline at all

**The verdict on Approach 2 specifically:** the abstraction direction is right but the implementation is wrong in two load-bearing ways (cache keying, function contract). A correct dependency graph would look like:

```python
def run(self, name, data):
    cache_key = (name, id(data))  # or hash(data) if hashable
    if cache_key in self.cache:
        return self.cache[cache_key]
    
    # Uniform contract: every function receives a context dict
    inputs = {dep: self.run(dep, data) for dep in self.edges[name]}
    context = {"data": data, **inputs}
    result = self.nodes[name](context)
    
    self.cache[cache_key] = result
    return result
```

The deeper lesson: **structural sophistication and correctness are orthogonal.** Approach 2 looks more engineered and is less correct. Approach 1 looks naive and behaves predictably. The better question isn't "which pattern?" but "which failure modes can you afford?"
