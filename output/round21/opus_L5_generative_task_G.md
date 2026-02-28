## Pattern: Control Flow Topology Choice

This is a **sequential composition vs. DAG composition** problem — choosing the shape of a computational pipeline when the same logical steps must execute.

From this problem's specific properties, three analytical operations emerge in increasing abstraction:

---

### Operation 1: Trace the Actual Dependency Structure

Before evaluating either approach, ask: *what does this specific problem's data flow actually look like?*

```
remove_nulls → scale_features → extract_features → kmeans → assign_labels → summarize
```

It's a **strict linear chain**. No step has two independent inputs. No two steps could run in parallel. This is the single most important observation, because the graph machinery in Approach 2 is designed to exploit structure that **doesn't exist here**.

### Operation 2: Evaluate Operational Affordances

| Property | Linear Pipeline | Dependency Graph |
|---|---|---|
| Readability | Instantly clear | Requires tracing registration |
| Debuggability | Stack trace points to exact step | Indirection through `run` recursion |
| Caching | Absent (but trivially added) | Built-in |
| Partial re-execution | No | Yes — change one node, reuse cache |
| Parallelism | Impossible | Possible on independent branches |
| Testability | Call any function in isolation | Must mock graph context |

But there's a **concrete bug** in Approach 2 that reveals a deeper design problem:

```python
# This line conflates two completely different function signatures
result = self.nodes[name](data if not inputs else inputs)
```

Root nodes receive raw `data`. Downstream nodes receive a `dict` of named dependency outputs. This means **every node function must know whether it's a root or not**, destroying the composability the graph was supposed to provide. The linear pipeline, by contrast, has a clean uniform contract: *each function takes one input, returns one output*.

### Operation 3: Assess the Abstraction's Cost-Benefit Threshold

Approach 1 is better for this problem. Here's the reasoning:

**Approach 2 pays upfront complexity costs** (indirection, recursive execution, cache management, ambiguous function signatures) **to purchase capabilities the problem doesn't need** (branching, merging, selective re-execution of subgraphs).

Approach 2 becomes the right choice when:
- The pipeline **branches** (e.g., two independent feature extraction methods that feed into an ensemble)
- Steps are **expensive** and parameters change frequently (caching pays off)
- The pipeline is **user-configured** at runtime (dynamic topology)
- Independent branches enable **parallelism** that matters at scale

For a 6-step linear chain, Approach 1 wins on every axis that matters: clarity, correctness, debuggability, and maintainability. If caching is needed, add a decorator:

```python
from functools import lru_cache  # or a simple memoize wrapper
```

---

### Inversion: What Operation Can't This Frame Generate?

The **topology choice** frame is blind to **failure semantics and recovery**. What happens when `kmeans` fails at step 4? The linear pipeline gives you a clean stack trace. The graph *could* offer retry, fallback paths, or partial results — but this implementation doesn't, and nothing in the topology framing naturally leads you to ask about it.

It also can't generate questions about **provenance and observability** — tracking *which version* of cleaned data produced *which* clusters. That's orthogonal to topology and arguably more valuable than either approach addresses.

**The bottom line:** Approach 1 is correct here. Approach 2 is a premature abstraction with an actual defect in its core dispatch logic. The right design principle: *match your control flow topology to your dependency topology*, don't aspirationally over-structure it.
