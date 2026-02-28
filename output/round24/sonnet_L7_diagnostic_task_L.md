# Structure First: Level 7 Diagnostic Analysis

---

## I. The Initial Falsifiable Claim

**Claim:** The deepest structural problem is *temporal coupling masquerading as lifecycle management*. The binary `_started` flag and two-pass initialization (`on_init` then `on_start`) create the appearance of phased lifecycle control, but the system never enforces *what phase* a dependency must be in before it's consumed. A plugin receiving `get_plugin()` during `on_init` gets an instance that may only be initialized, not started — yet the system encodes no distinction and makes no guarantee. The dependency graph orders *invocation* but not *state readiness*.

Falsifiable: deploy two plugins where B consumes A's post-start state during B's `on_init`. The system will silently succeed while operating on invalid state.

---

## II. The Three-Expert Dialectic

### Expert A (Defender): Temporal Coupling Is Real

The two-pass loop is explicit acknowledgment that plugins need to *exist* before they can *interact*. But the system never captures *which lifecycle phase* a dependency needs to have reached. `get_plugin()` is available during `on_init`, returning a peer that's only initialized. This isn't accidental — it's a structural gap. The dependency graph tells you *order of invocation*, not *contracts about state*. Expert A holds: temporal coupling is the genuine core failure.

### Expert B (Attacker): Temporal Coupling Is a Red Herring

The temporal framing assumes plugins are cooperative. They're not guaranteed to be. The real problem is **absent capability boundaries**. `_get_api` gives every plugin unrestricted `get_plugin` access to every other plugin's live instance — not a proxy, not a versioned snapshot, the actual object. Plugin A can call methods on Plugin B that bypass B's lifecycle entirely. The dependency graph is purely advisory. There are no authorization checks, no interface contracts, no sandboxing. The lifecycle is theater if any plugin can reach into any other at any time.

### Expert C (Prober): Both of You Share a Broken Assumption

Both A and B assume the dependency graph is *legitimate* — that it accurately represents actual runtime coupling. It doesn't, and worse, it can't be made to.

First, the cycle detection in `_resolve_order` is **silently broken**:

```python
def visit(name):
    if name in visited:
        return          # ← not a cycle error, just early return
    visited.add(name)
    for dep in self._plugins[name]["depends_on"]:
        visit(dep)
    order.append(name)
```

A→B→A produces no error. It silently generates a wrong order. No plugin is ever told their dependency graph is circular.

Second — and more fundamentally — **the real dependency system is the hook system, not `depends_on`.** Plugin A registers a hook during `on_init`. Plugin B triggers that hook during `on_start`. This is a dependency that `depends_on` cannot express, the dependency graph cannot see, and the resolver cannot order. The formal dependency structure is a decoy.

---

## III. The Transformation

| | Claim |
|---|---|
| **Original** | Temporal coupling: the binary `_started` flag creates false lifecycle phase enforcement |
| **Transformed** | Graph illegitimacy: the explicit `depends_on` graph is presented as the authoritative model of plugin relationships, but actual runtime coupling flows through hooks, direct instance access, and shared mutable state — channels the graph cannot see, validate, or express |

The system doesn't just have an incomplete dependency graph. It has a **decoy dependency graph** that substitutes the appearance of principled architecture for the reality of untracked coupling.

---

## IV. The Gap as Diagnostic: Naming the Concealment Mechanism

The gap — moving from "temporal coupling" to "graph illegitimacy" — reveals the concealment mechanism:

### **Structural Legitimacy Laundering**

The system constructs visible formal structures (dependency graph, `_started` flag, lifecycle phases, hook registry with `plugin_name` attribution) that *look like* they govern the real complexity. They don't. They govern a simplified, well-behaved fiction. The real coupling system operates through entirely different channels — and the formal structures don't merely fail to capture this reality, they **actively displace it from attention**. You look at `depends_on` and feel the architecture is sound. That feeling is the mechanism.

The formal structure doesn't supplement the real structure. It launders it — converts invisible, unenforceable coupling into the appearance of declared, managed dependency.

---

## V. What the Entire Dialectic Failed to Surface

Now apply the mechanism: **what is structural legitimacy laundering still hiding that the three-expert dialectic never touched?**

The hook system's `plugin_name` attribution is stored but **never consulted for anything**:

```python
self._hooks[hook_name].append({"fn": callback, "plugin": plugin_name})
```

```python
def stop(self):
    for name in reversed(self._load_order):
        plugin["instance"].on_stop()   # ← hooks never unregistered
        plugin["state"] = "stopped"
```

When a plugin stops, its registered hooks remain active. When a plugin fails during `on_init` mid-pass, hooks it already registered continue to fire. The `plugin_name` metadata exists — the system *has the information* to perform ownership-based cleanup — but treats it as inert decoration.

This is the structural legitimacy laundering still operating: `plugin_name` makes the hook system *look like* it has an ownership model, while ownership is never enforced.

But the dialectic failed to surface something deeper than that:

### **The Hook System Has No Result Semantics**

```python
def trigger(self, hook_name, *args):
    results = []
    for entry in self._hooks.get(hook_name, []):
        results.append(entry["fn"](*args))
    return results
```

`trigger()` returns a list of results. But the system defines **no protocol for what those results mean**. When three handlers respond to `"pre_save"`:
- Can any of them veto the operation?
- Do their return values compose?
- Does order matter?
- What does `None` mean versus a raised exception versus a return value?

The entire hook architecture depends on **out-of-band conventions the system cannot express, enforce, or document**. Every plugin that uses `trigger()` meaningfully must implement its own result-interpretation logic — meaning the hook system is not actually a shared protocol, it's a shared *call dispatch mechanism* with no shared semantics.

This is what was fully hidden: the hook system is architecturally half-implemented. It can *invoke* handlers. It cannot *mean anything* by the invocation. Any real use of hooks requires conventions that live outside this system entirely — in comments, in README files, in tribal knowledge — which means the plugin system cannot be understood, extended, or safely modified from its own code alone.

The structural legitimacy laundering concealed this by making the hook API look complete: you can register, you can trigger, you get results back. The *shape* of a real event system is present. The *semantics* that make an event system useful are absent, and the completeness of the shape is what made the absence invisible.

---

## Summary Table

| Layer | Problem | Hidden By |
|---|---|---|
| Surface | No cycle detection error on circular deps | Silent early-return looks like correct handling |
| Structural | `depends_on` graph can't capture hook-based coupling | Formal graph creates appearance of complete dependency model |
| Architectural | Plugin stop doesn't unregister hooks | `plugin_name` attribution gives the *appearance* of ownership tracking |
| **Deepest** | Hook results have no defined semantics | Complete API shape (register/trigger/return) conceals semantic void |

The code's real problem is not any single bug or missing feature. It is that it has systematically built the *form* of sound architecture without the *substance* — and the form is precisely what makes the substance's absence invisible.
