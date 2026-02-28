# Pattern Analysis: Implicit vs. Explicit Structure

## Named Pattern
This instantiates the **Representation of Computation** problem—the tension between **sequential coupling** (Approach 1) and **declarative dependency graphs** (Approach 2). But critically: the problem statement is *latent*—it hides whether the dependencies are actually linear.

---

## The Hierarchy Question Reveals a Non-Hierarchy

This looks hierarchical (linear stack) but is actually **flat and tangled**. Here's why:

**Approach 1 assumes**: "These 6 steps are inherently sequential"
**Approach 2 asks**: "What if they're not?"

Neither code shows the *actual* data dependencies. The real question is compressed into the problem statement itself.

---

## Branches and What They Miss

### **Branch A: Approach 1 is better (linear simplicity)**
**Steelman**: 
- Readability: The function reads like prose
- No infrastructure overhead
- Debugging is trivial (step through line by line)
- Honest if the problem *is* sequential

**What it misses**:
- ❌ Can't recompute just `extract_features` if data changes
- ❌ Can't parallelize independent branches (future: what if `scale_features` and `extract_features` were independent?)
- ❌ Locks you into one execution order
- ❌ If step 3 fails, you've wasted time on steps 1-2

### **Branch B: Approach 2 is better (graph flexibility)**
**Steelman**:
- Memoization handles repeated analysis
- Extensible to non-linear DAGs
- Can query intermediate results
- Can conditionally skip steps

**What it misses**:
- ❌ **Huge cognitive overhead**: You now manage a separate dependency declaration
- ❌ **Validation burden**: Dependencies are declared but not validated (cycles? missing deps?)
- ❌ **Caching hazard**: Returns stale results silently
- ❌ **Debuggability nightmare**: When step 4 is wrong, is it because step 2 changed? You don't know what was cached.
- ❌ **Graph code is harder to read than linear code** (ironic, given the goal)

---

## The Inversion: What Property Made Me Branch?

I branched because **the problem specification is hidden**. 

The deciding property: **Does this pipeline have non-linear dependencies?**

But you didn't tell me! So each approach encodes a different assumption:
- Approach 1: "I'm confident this is sequential"
- Approach 2: "I'm uncertain, so I defer the decision"

**What if I'm wrong about the branch?**

- If the pipeline IS linear (most real pipelines are), Approach 1 wins decisively. Approach 2's graph machinery is wasted complexity.
- If the pipeline ISN'T linear (step 3 and 4 could run in parallel), Approach 1 fails catastrophically.

---

## The Honest Answer

**Neither is better. They're solving different problems:**

| Scenario | Winner | Why |
|----------|--------|-----|
| One-off analysis, sequential steps | **Approach 1** | Simplicity |
| Repeated analysis, reusable intermediate steps | **Approach 2** | Caching + reusability |
| Conditionally-executed steps | **Approach 2** | Flexibility |
| Unknown dependencies | **Approach 1 first**, then refactor | Validate simplicity before abstracting |

---

## If Forced to Choose: A Third Way

Use **Approach 2's structure**, but **improve it dramatically**:

```python
class AnalysisGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.cache = {}
        self.logs = {}  # NEW: trace what ran
        
    def run(self, name, data):
        if name in self.cache:
            self.logs.setdefault(name, []).append("cache_hit")
            return self.cache[name]
        
        # NEW: validate dependencies exist
        for dep in self.edges.get(name, []):
            if dep not in self.nodes:
                raise ValueError(f"{name} depends on undefined {dep}")
        
        inputs = {dep: self.run(dep, data) for dep in self.edges.get(name, [])}
        result = self.nodes[name](data if not inputs else inputs)
        self.cache[name] = result
        self.logs.setdefault(name, []).append("executed")
        return result
    
    def visualize(self):
        """Draw the DAG so you can see what you built"""
        pass  # Render to graphviz
```

**Key improvements:**
- Validates the graph before running (find errors early)
- Logs execution to make caching visible (no silent bugs)
- Supports visualization (you can now *see* if it's linear)

---

## The Meta-Lesson

The *real* pattern is: **Structure should be explicit only when it's non-obvious.** 

For linear pipelines, make them linear. For complex DAGs, make them explicit with validation. The question as posed forces a false choice because it hides the actual dependency structure—which is where the decision should be made.

What's your actual pipeline structure?
