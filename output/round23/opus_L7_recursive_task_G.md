# Recursive Falsification: Linear Pipeline vs. Dependency Graph

## First Claim (Falsifiable)

> **Approach 2's dependency graph is over-engineering — it adds abstraction without enabling any capability the linear pipeline can't support, because this workflow is inherently sequential.**

### Three-Expert Dialectic

**Defender:** The pipeline *is* the correct model. You can't cluster before normalizing. You can't label before clustering. Every step depends on exactly one predecessor. The graph adds cache management, recursive resolution, and indirection — all for a problem with zero branching.

**Attacker:** Wrong. The graph enables real capabilities: branching (run two different clusterings on the same features), partial re-execution (change only labeling, reuse cached clustering), and explicit dependency declaration. The pipeline *hardcodes* topology; the graph *declares* it.

**Prober (what both sides take for granted):** Both are arguing about *capability* — what each approach *could* do. Neither is examining what happens when these approaches *fail*. Look at this line:

```python
result = self.nodes[name](data if not inputs else inputs)
```

This is where the real analysis begins.

---

## The Transformation

The prober cracks the argument open. That ternary expression is doing something structurally incoherent:

| Node position | What the function receives |
|---|---|
| Root node (no dependencies) | Raw `data` (original input) |
| Interior node (has dependencies) | `inputs` — a `dict` of named dependency outputs |

This means **node functions cannot have a uniform signature**. A root node expects raw data; an interior node expects a dictionary. Consider:

```python
graph.add_step("clean", remove_nulls)           # receives raw data
graph.add_step("normalize", scale_features,      # receives {"clean": ...}
               depends_on=["clean"])
```

`scale_features` was presumably written to accept cleaned data directly — not a dictionary `{"clean": <cleaned_data>}`. Every interior node must now **know its own position in the graph** and unpack its inputs accordingly. This destroys composability.

Additionally:
- **No cycle detection** — circular dependencies cause infinite recursion
- **No cache invalidation** — stale results persist silently
- **`data` is captured ambiguously** — it's passed through `run()` but only used by root nodes, yet carried through every recursive call

---

## Second Claim (Post-Transformation)

> **Approach 2 conflates two fundamentally different abstractions — *data flow* and *dependency resolution* — into a single mechanism. The seam where they meet (`data if not inputs else inputs`) creates an incoherent contract: node functions need incompatible signatures depending on graph position, which destroys the very composability that motivated the graph approach.**

The graph *promises* flexibility and recomposability. But a node written for one position cannot be moved to another without rewriting its function signature. **The abstraction undermines its own reason for existing.**

## Verdict

**Approach 1 is better for this problem**, and not for the naive reason ("it's simpler"). It's better because:

1. **Its structure matches its semantics.** Sequential code for a sequential workflow. No gap between what it promises and what it does.
2. **It fails transparently.** An exception at step 3 means steps 1–2 ran. The stack trace tells you exactly what happened.
3. **Approach 2 isn't a valid alternative yet.** It has a *semantic bug* in its core dispatch logic. Before it could be "better," it would need uniform node signatures (perhaps every node receives a context dict), cycle detection, and cache invalidation — at which point you've reinvented Airflow/Prefect/Dask.

## What the Distance Reveals

| | Claim 1 | Claim 2 |
|---|---|---|
| **Level** | *Between* approaches | *Within* Approach 2 |
| **Question** | Is the graph necessary? | Is the graph coherent *on its own terms*? |
| **Type** | Comparative | Internal-consistency |

The distance is categorical, not incremental. Single-pass analysis compares approaches *against each other*. Recursive falsification reveals that the more damning analysis evaluates each approach **against its own implicit promises**. The graph doesn't fail because it's unnecessary — it fails because it *can't deliver what it advertises*.
