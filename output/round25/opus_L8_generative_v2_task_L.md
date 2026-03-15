# Generative Diagnostic: Plugin System with Lifecycle Hooks

## The Falsifiable Claim

**The dependency graph is a structural lie.** The `depends_on` mechanism declares relationships between plugins, but the API surface handed to every plugin during `on_init` grants uniform, unscoped, omnipotent access to the entire system — making the declared dependency graph cosmetic. The actual dependency graph is built silently at runtime through `hook()`, `trigger()`, and `get_plugin()` calls that the manager never sees.

---

## Three Experts Stress-Test the Claim

**Expert 1 (Defender):** The claim holds. Look at `_get_api`:

```python
def _get_api(self, plugin_name):
    return {
        "hook": self.hook,
        "trigger": self.trigger,
        "get_plugin": lambda n: self._plugins[n]["instance"]  # ANY plugin, not just deps
    }
```

Plugin `A` that declares `depends_on=[]` can call `get_plugin("B")` and directly invoke methods on `B`. The `_resolve_order` topological sort produces a correct initialization sequence for a graph that nothing enforces. Meanwhile, `_hooks` silently accumulates a second, invisible graph of runtime couplings. When `stop()` runs, it reverses `_load_order` — but the *hook graph* isn't reversed, cleaned, or even acknowledged.

**Expert 2 (Attacker):** The claim overstates the problem. Many successful plugin systems (pytest, WordPress, Webpack) use exactly this pattern: declared dependencies for load order, loose hooks for runtime coupling. The *real* failures are more mundane:

- `_resolve_order` has no cycle detection — `visit()` uses `visited` to prevent re-entry but not to detect back-edges, so circular dependencies silently produce wrong orderings
- A missing dependency name in `depends_on` causes a `KeyError` deep inside the recursion with no useful context
- `start()` has zero error handling — if the 3rd of 5 plugins throws in `on_init`, plugins 1-2 are "initialized" but never started, and the system is wedged
- `stop()` swallows all exceptions silently

These are the bugs that will actually ship broken. The "shadow graph" is a design philosophy debate, not a structural flaw.

**Expert 3 (Probing both assumptions):** Both experts assume the dependency graph *should* be the source of truth. But what if the real blind spot is deeper? The code manages **entity states** (`"registered"`, `"initialized"`, `"started"`, `"stopped"`) but not **relationship states**. Hook registrations, direct references from `get_plugin`, closures captured during `on_init` — these are all *edges* in the plugin graph, and none of them have a lifecycle. The real problem isn't access control (Expert 1) or missing validation (Expert 2). It's that **the lifecycle model is structurally incomplete** — it tracks nodes but not edges.

---

## The Transformed Claim

The deepest structural problem is that **the system manages plugin states but not relationship states**. Hook registrations, direct references, and API closures create inter-plugin bindings that have no creation tracking, no state, and no teardown. The `state` field on each plugin provides the *feeling* of lifecycle management while the actual failure surface — the web of inter-plugin connections — is invisible.

### The Diagnostic Gap

My original claim targeted **authority** (the API is too powerful). The transformed claim targets **lifecycle completeness** (relationships are unmanaged). This gap reveals I was drawn to access-control framing when the structural issue is about what the lifecycle model *omits entirely*.

---

## The Concealment Mechanism: State-Label Theater

The `state` field is updated at every transition:

```python
plugin["state"] = "initialized"   # after on_init
plugin["state"] = "started"       # after on_start
plugin["state"] = "stopped"       # after on_stop
```

This creates the appearance of rigorous lifecycle tracking. A reader sees state transitions and thinks "this system knows where every plugin is in its lifecycle." But the labels track only the **plugin's phase**, never:

- Whether its hooks are still registered (they always are)
- Whether other plugins hold live references to it (they always do)
- Whether its API closure is still callable (it always is)
- Which plugins will break when it stops (unknowable)

The labels make the unmanaged state *invisible by contrast* — the tracked state is so visible that the untracked state disappears.

---

## The Improvement That Deepens Concealment

This would pass code review. It looks like exactly the right fix:

```python
class PluginManager:
    VALID_TRANSITIONS = {
        "registered": "initialized",
        "initialized": "started",
        "started": "stopped",
    }

    def _transition(self, name, target_state, lifecycle_hook):
        plugin = self._plugins[name]
        current = plugin["state"]
        expected_target = self.VALID_TRANSITIONS.get(current)

        if expected_target != target_state:
            raise InvalidTransitionError(
                f"Plugin '{name}': cannot transition "
                f"'{current}' -> '{target_state}'"
            )

        instance = plugin["instance"]
        if hasattr(instance, lifecycle_hook):
            getattr(instance, lifecycle_hook)(
                *([self._get_api(name)] if lifecycle_hook == "on_init" else [])
            )

        plugin["state"] = target_state
        logger.info(f"Plugin '{name}' transitioned: {current} -> {target_state}")

    def start(self):
        self._started = True
        order = self._resolve_order()
        self._load_order = order
        for name in order:
            self._transition(name, "initialized", "on_init")
        for name in order:
            self._transition(name, "started", "on_start")

    def stop(self):
        for name in reversed(self._load_order):
            try:
                self._transition(name, "stopped", "on_stop")
            except Exception as e:
                logger.error(f"Failed to stop plugin '{name}': {e}")
                self._plugins[name]["state"] = "stopped"
        self._started = False
```

**Why it passes review:** Formal state machine. Validated transitions. Logging. Consistent error handling. Clean separation of lifecycle mechanics.

**Why it deepens the concealment:** It makes the state-label theater *professional*. Now there's a `VALID_TRANSITIONS` dict, validation logic, logging — a reviewer sees a proper finite state machine and signs off. The confidence that "lifecycle is handled" increases dramatically. Meanwhile:

```python
# After stop(), this still works perfectly:
stale_api["trigger"]("some_hook", dangerous_data)  # No check anywhere
stale_api["get_plugin"]("other")  # Returns live reference to stopped plugin

# And self._hooks still contains:
{"fn": <bound method of stopped plugin>, "plugin": "dead_plugin"}  # Will fire on next trigger()
```

---

## Three Properties Visible Only Because I Tried to Strengthen It

**1. Hook registrations are a parallel, unmanaged object system.**
When I tried to write `_transition`, I looked for where hook cleanup would go. There is no such place. Hook entries are created via `self.hook()` but never removed. There's no `unhook()`. There's no plugin-scoped cleanup. The strengthening revealed that hooks aren't a *feature* of the lifecycle — they're a *separate system* with no lifecycle at all. They accumulate monotonically until process death.

**2. The API closure is a permanent capability leak that invalidates the state machine.**
Making transitions strict forced me to confront: what enforces that a stopped plugin *behaves* as stopped? The `_get_api` closure captures `self` (the manager) and returns it raw. A plugin that stored its API during `on_init` retains full system access forever. The improved state machine validates the manager's *view* of the plugin, but the plugin's *capabilities* are stateless. The state machine becomes a lie that the manager tells itself.

**3. Partial failure creates ghost states that the state machine makes *more* dangerous.**
Without the improvement, a failure during `start()` leaves ambiguous state — bad, but visibly broken. *With* the improvement, if plugin 3 of 5 fails during initialization, plugins 1-2 have state `"initialized"` — a formally valid state that the state machine will refuse to transition to `"stopped"` because `VALID_TRANSITIONS["initialized"]` is `"started"`, not `"stopped"`. The system is now *formally wedged*: plugins that need cleanup are locked in a state from which the only valid exit is forward (to `"started"`), but the system is aborting. The rigorous state machine made the partial-failure case **unrecoverable by design**.

---

## Summary

| Layer | What's Hidden |
|---|---|
| **Surface** | Missing cycle detection, no error handling in `start()`, swallowed exceptions in `stop()` |
| **Structural** | The dependency graph is unenforced; `get_plugin` bypasses it entirely |
| **Deep** | The lifecycle manages *plugin states* but not *relationship states* — hooks, references, and API closures are edges with no lifecycle |
| **Concealment** | State-label theater — the `state` field's visibility makes the unmanaged state invisible by contrast |
| **Meta** | Strengthening the state machine makes partial failure *formally unrecoverable* — the improvement is load-bearing for the concealment |
