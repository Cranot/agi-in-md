## Claim (Falsifiable)

> **The deepest structural problem is that `depends_on` encodes only temporal ordering constraints, not capability contracts — making the dependency graph semantically empty while appearing architecturally meaningful.**

---

## Three-Expert Debate

### Expert A (Defender)
The evidence is clear. `depends_on` is a list of names. The DFS produces a topological sort. Nothing in the system represents *what* A needs from B — only that B must come first. `_get_api` compounds this: it hands every plugin the manager's own internal methods, so plugins can reach into each other with no declared interface:

```python
# Plugin A can do this. The system has no opinion about it.
api["get_plugin"]("payment_service").process(api["get_plugin"]("user_db").get_all())
```

The dependency graph has the *vocabulary* of real dependency injection with none of its *semantics*.

---

### Expert B (Attacker)
The access problem is a feature in disguise — most production plugin systems (pytest, Babel, webpack) give plugins broad access intentionally. The *real* deepest problem is more concrete and more immediately dangerous: `_resolve_order` silently produces a wrong answer on cycles instead of failing:

```python
def visit(name):
    if name in visited:
        return          # ← Silent return. Cycle? Wrong order? Don't care.
    visited.add(name)
    for dep in self._plugins[name]["depends_on"]:
        visit(dep)
    order.append(name)
```

If A→B→A, you get an arbitrary order with no error. This is a correctness failure in the one place the system claims to provide safety guarantees.

---

### Expert C (Prober — attacking what both take for granted)
Both of you treat the lifecycle state machine as real infrastructure. It isn't. The `state` field transitions `registered → initialized → started → stopped` with no guards:

```python
plugin["state"] = "initialized"   # Set unconditionally, even if on_init raised
plugin["state"] = "started"       # No check that "initialized" was reached
```

And `stop()` swallows all exceptions silently. But the deeper issue you're both circling is this: **the system cannot be introspected**. You cannot ask "which plugins consume hook X?", "what does plugin A export?", or "what would break if plugin B were removed?" The system *looks* inspectable — it has `_plugins`, `_hooks`, `_load_order` — but these are storage, not knowledge. The real concealment is that a system claiming to manage complexity has no model of its own structure.

---

## Claim Transformation

| | Statement |
|---|---|
| **Original** | "The API collapses the distinction between plugin participant and system controller" |
| **After debate** | "The system models plugin relationships as ordering constraints, making the dependency graph a topological sort algorithm wearing the costume of an architecture" |
| **The gap** | I initially saw an *access control* problem. The transformed claim reveals an *epistemic* problem: the system cannot know what it manages. |

---

## The Concealment Mechanism: **Structural Mimicry**

The code uses the precise vocabulary of sophisticated systems — `depends_on`, `_resolve_order`, lifecycle hooks, a plugin API — while implementing only the minimum surface behavior of each concept. The vocabulary performs the *idea* of a dependency injection system. This hides:

- That `depends_on` is a sort key, not a contract
- That `_get_api` is `self` with a different name
- That state transitions have no guards or rollback
- That hook registration has no lifecycle binding
- That the system cannot answer any structural question about itself

---

## The Trojan Improvement

Here is a specific, legitimate-looking fix that passes code review but deepens the concealment:

```python
def _resolve_order(self):
    """Topological sort via Kahn's algorithm with cycle detection and dependency validation."""
    from collections import deque

    in_degree = {name: 0 for name in self._plugins}
    dependents = {name: [] for name in self._plugins}

    for name, plugin in self._plugins.items():
        for dep in plugin["depends_on"]:
            if dep not in self._plugins:
                raise ValueError(
                    f"Plugin '{name}' declares dependency on unknown plugin '{dep}'"
                )
            dependents[dep].append(name)
            in_degree[name] += 1

    queue = deque(name for name, d in in_degree.items() if d == 0)
    order = []

    while queue:
        name = queue.popleft()
        order.append(name)
        for dependent in dependents[name]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(order) != len(self._plugins):
        cycle = [n for n, d in in_degree.items() if d > 0]
        raise RuntimeError(f"Circular dependency detected among plugins: {cycle}")

    return order
```

**Why it passes review:** Replaces buggy DFS, adds cycle detection, validates unknown dependencies, uses standard CS algorithm, includes descriptive errors.

**Why it deepens the concealment:** It makes `depends_on` look *more* like a real dependency system. The validation (`dep not in self._plugins`) creates the impression of type safety at the dependency boundary. Reviewers will feel the dependency model is now correct — and will stop looking at whether the model expresses anything real.

---

## Three Properties Only Visible Because We Tried to Strengthen It

### 1. The Validation Asymmetry Is Structurally Enforced

Adding `dep not in self._plugins` at registration time immediately reveals that `get_plugin(n)` at runtime has *no such check*:

```python
# Validated at resolve time:
if dep not in self._plugins: raise ValueError(...)

# Completely unchecked at runtime:
"get_plugin": lambda n: self._plugins[n]["instance"]  # KeyError if n missing
```

The improvement makes the asymmetry visible: the system validates the dependency graph but not the actual graph traversal. This asymmetry was invisible before because both sides were equally weak.

### 2. Hooks Have No Lifecycle — They're Immortal

While auditing the improvement, you notice `stop()` sets `state = "stopped"` but never removes the plugin's hooks from `self._hooks`. A stopped plugin's callbacks remain live indefinitely:

```python
def stop(self):
    for name in reversed(self._load_order):
        plugin["instance"].on_stop()
        plugin["state"] = "stopped"
        # ← hooks registered by this plugin during on_init still fire
        # ← self._hooks is never cleaned up
```

The improved cycle detection draws attention to the lifecycle machinery, which reveals that hooks exist outside the lifecycle entirely. This was not visible before because both the dependency resolution and the hook system looked equally "complete."

### 3. `depends_on` Cannot Be Upgraded Without Breaking Redesign

When you try to extend the improvement to add interface validation — *what* does A need from B, not just *when* — you hit a wall:

```python
# You want this:
manager.register("A", plugin_a, depends_on=[("B", IBLogger)])

# But _get_api returns this with no interface information:
"get_plugin": lambda n: self._plugins[n]["instance"]
```

There is no slot in the data model for capability declarations. `depends_on` is `List[str]`. `_plugins` stores `instance`, `depends_on`, `state`. The system has no layer where interface contracts could live. The shallow structure isn't an implementation oversight — **it is the architecture**. Trying to deepen the dependency resolution reveals that the entire data model would need to change, which means the semantic emptiness is load-bearing, not incidental.
