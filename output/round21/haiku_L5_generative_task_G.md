# Pattern: Sequential vs. Declarative Composition

This instantiates the **Total-Order Sequencing vs. Partial-Order DAG Resolution** pattern—the fundamental difference between "execute these steps in fixed sequence" and "execute steps based on declared dependencies."

---

## Three Analytical Operations (Increasing Abstraction)

### Op 1: Dependency Cardinality Census (Concrete)
**What you can measure directly from the code:**

| Property | Approach 1 | Approach 2 | This Problem |
|----------|-----------|-----------|--------------|
| Fan-in per step | 1 always | 0 to N | 1 always |
| Fan-out per step | 1 always | 0 to M | 1 always |
| Reachable paths | 1 | 2^n theoretically | 1 |

**Finding**: Approach 2 has structural capability your problem doesn't use. It's like buying a truck to carry a single box.

---

### Op 2: Intermediate State Lifecycle (Medium Abstraction)
**How many intermediate results exist in memory simultaneously?**

- **Approach 1**: max = 1 (current output only; previous discarded immediately)
- **Approach 2**: max = N (all intermediates cached until run() completes)

For this 6-step pipeline: Approach 2 holds 5 unnecessary copies in memory. The caching feature—meant as optimization—becomes overhead when **nothing is reused**.

---

### Op 3: Constraint Encoding (Highest Abstraction)
**What computational model does each approach *embed*?**

- **Approach 1**: "These steps must execute in THIS fixed order"
- **Approach 2**: "These steps execute when dependencies are satisfied"

For a linear pipeline, Approach 2 is strictly weaker—it *allows* any order that respects the declared dependencies, but your actual problem *requires* a specific order. **You're encoding more generality than you need.**

---

## The Inversion: What You Cannot Derive

From the code structure alone, you cannot determine:

1. **Usage frequency**: Once vs. 1000x with parameter variations → Approach 2 worth it only for the latter
2. **Intermediate reuse**: Do you need `features` for other analyses beyond clustering? → Code doesn't answer this
3. **Failure recovery**: If `kmeans` fails, do you want `features` cached to retry? → Neither approach handles this naturally
4. **Streaming dynamics**: Does data arrive incrementally? → Both assume batch
5. **Modification velocity**: Will you swap algorithms monthly? → Structure assumes current design is stable

---

## Verdict

**Approach 1 is better for THIS problem because:**
- Matches problem structure exactly (linear, no branching, no reuse)
- Clarity = maintainability (function composition is immediately readable)
- No overhead (zero caching cost)

**Approach 2 would be better if:**
- You need multiple paths (feature extraction → clustering AND → anomaly detection)
- You run it repeatedly with parameter sweeps (caching amortizes cost)
- You need parallel execution (DAG structure enables it; sequential doesn't)

**The trap**: Approach 2 looks "more engineered," but engineering for flexibility you don't need is premature complexity. Choose Approach 1 now; refactor to Approach 2 *when* requirements demand it.
