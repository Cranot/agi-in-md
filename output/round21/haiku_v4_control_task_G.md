# Pattern Analysis: Linear Pipeline vs. Dependency Graph

## Named Patterns

- **Approach 1**: Composition pipeline (sequential)
- **Approach 2**: DAG (directed acyclic graph) orchestration with memoization

## Known Constraints & Failure Modes

### Approach 1 — Simple but Brittle

**Wins when:**
- Single execution per data load
- Dependencies truly sequential
- Debugging matters (stack trace is execution trace)

**Breaks when:**
- Rerunning with different k values → must recompute extraction
- Wanting to test without normalization → must fork the whole function
- Feature extraction is expensive and parameters don't change → recomputed anyway
- Team needs intermediate results for inspection → requires code modification

### Approach 2 — Flexible but Complex

**Wins when:**
- Multiple downstream consumers
- Expensive intermediate steps
- Parameters/steps change between runs
- Can parallelize independent branches

**Breaks when:**
- Input data changes but cache key doesn't (silent stale data)
- Circular dependencies added (infinite loops)
- Over-engineered for one-shot analysis
- Error in step 3 is hard to isolate (which cache entry caused it?)

---

## The Inversion: What Each Approach Hides

**Approach 1 hides:** The assumption that problems stay simple. Real data analysis mutates—teams always want to skip normalization, try k=3 vs k=5, parallelize, or reuse feature extraction. The linear form *looks* simple but forces refactoring downstream.

**Approach 2 hides:** A critical bug in the code shown. The caching strategy is naive:
```python
def run(self, name, data):
    if name in self.cache:
        return self.cache[name]  # ← dangerous!
```
This doesn't account for:
- Changed input data (cache becomes stale)
- Different parameters to the same function
- Selective cache invalidation

---

## Verdict: **Context-Dependent, But Approach 2's Structure Survives**

| Scenario | Better Approach | Why |
|----------|-----------------|-----|
| One-off analysis, fixed steps | Approach 1 | Simplicity and debuggability win |
| Iterative experimentation | Approach 2 | Rerunning subsets saves computation |
| Production pipeline | Approach 2 | Must handle variable params/caching |

**The real lesson:** Approach 2's *idea* (explicit dependency declaration) is better for maintainability—even if you don't use its caching. But the *implementation* shown has hidden landmines.

**Better compromise:**
```python
# Linear pipeline + optional caching layer
def analyze(data, k=5, skip_normalization=False):
    cleaned = remove_nulls(data)
    normalized = cleaned if skip_normalization else scale_features(cleaned)
    features = extract_features(normalized)
    clustered = kmeans(features, k=k)
    labeled = assign_labels(clustered)
    return summarize(labeled)
```

This keeps Approach 1's clarity while permitting the flexibility Approach 2 addresses.
