## Structural Mechanisms

### Mechanism 1: Context Inheritance Chain

**What it enforces:** Not "configuration sharing" but **ambient authority propagation** — each child context inherits not just settings but the *right to override* parent decisions.

- **Input:** Parent context reference + override parameters
- **Output:** A context that can selectively shadow parent values while maintaining back-reference
- **What breaks:** Default resolution (`lookup_default` walks up the chain), auto_envvar_prefix cascading, help option inheritance
- **Hidden dependency:** Every context is *coupled to the existence depth* of its ancestors via `_depth`. Memory leak potential: `_meta.copy()` creates shallow copies that retain parent object references.

### Mechanism 2: Protected Args Reservation

**What it enforces:** Not "argument storage" but **parse state suspension** — `_protected_args` holds tokens that *cannot be interpreted yet* because subcommand resolution hasn't completed.

- **Input:** Unprocessed argument tokens during `parse_args`
- **Output:** Reserved argument slice that survives parent context cleanup
- **What breaks:** Chained commands (`chain=True`) collapse — the while-loop in `Group.invoke` drains `ctx._protected_args` then refills from `sub_ctx.args`. Single-command groups skip this entirely.
- **Hidden dependency:** The `args` vs `_protected_args` distinction is *invisible to callbacks* — they receive `ctx.params` but cannot know whether arguments were deferred. Creates temporal coupling between `parse_args` timing and `invoke` timing.

### Mechanism 3: Parameter Source Tracking

**What it enforces:** Not "provenance" but **priority inversion prevention** — the `ParameterSource` enum encodes a total ordering that `consume_value` must respect (COMMANDLINE > ENVIRONMENT > DEFAULT_MAP > DEFAULT > PROMPT).

- **Input:** opts dict from parser + environment variables + default_map + Parameter.default
- **Output:** Single resolved value + source tag
- **What breaks:** If removed, environment variables could override explicit command-line arguments, breaking the "explicit > implicit" contract users expect
- **Hidden dependency:** `consume_value` is called *inside* `handle_parse_result` which is called *inside* `iter_params_for_processing` order — the source hierarchy only works because eager parameters process before non-eager ones. The ordering is implicit in the iteration, not encoded in the resolution logic itself.

---

## Generative Modification

**Modification:** Add a `_shadow_params` dict to Context that stores *overridden* parameter values when a child context re-processes a parameter that already exists in `parent.params`.

```python
# In Context.__init__, after self.params = {}:
self._shadow_params = {}

# In Parameter.handle_parse_result, before ctx.params[self.name] = value:
if self.name in ctx.params and ctx.parent is not None:
    if self.name in ctx.parent.params:
        ctx._shadow_params[self.name] = ctx.params[self.name]
```

**What this preserves:** All external behavior — params still resolve correctly, callbacks still fire, commands still execute. The shadow dict is write-only from the interface perspective.

**What this conceals deeper:** The modification hides that *parameter resolution is not idempotent* — re-invoking the same command with the same arguments through different context depths produces different shadow states. The "purity" of parameter resolution is now explicitly tracked but inaccessible.

---

## Three Emergent Properties

### Property 1: Context Depth Creates Parameter Versioning

**Why invisible:** The original code treats each context's `params` as authoritative for that scope. There's no notion that a parameter "has a history."

**What surfaced it:** `_shadow_params` makes explicit that `ctx.params["verbose"]` at depth 3 might shadow `ctx.parent.params["verbose"]` at depth 2, which shadows root. The *path* through context tree determines which version you see — same parameter name, different values at different depths.

**Concrete manifestation:** A `--verbose` flag passed to a parent group could be silently overridden by a subcommand's callback that sets `ctx.params["verbose"] = False`. Child commands would never know verbosity was requested. The shadow would reveal this.

### Property 2: Eager Parameters Are Pre-Order, Not Depth-Order

**Why invisible:** `iter_params_for_processing` yields parameters in registration order, but "registration order" appears deterministic and neutral.

**What surfaced it:** With shadow tracking, you'd see that an eager parameter at depth 2 processes *before* a non-eager parameter at depth 1 finishes. The shadow dict would contain depth-1 values that were computed *after* depth-2 eager callbacks already ran. Temporal inversion becomes observable.

**Concrete manifestation:** A `--config` eager callback that modifies `ctx.obj` could affect parameter defaults for *sibling* commands that haven't been reached yet. The shadow would show parameters being resolved "out of tree order."

### Property 3: The UNSET Sentinel Is a Third Truth Value

**Why invisible:** `UNSET` is used as a sentinel for "no value resolved yet." Code treats it as equivalent to `None` in most contexts via `if value is UNSET` checks.

**What surfaced it:** Shadow tracking would accumulate `UNSET` values in `_shadow_params` when a parameter is *accessed* but not *resolved*. This reveals that the parameter system has three states: UNSET (never queried), None (explicitly set to None), and value. The distinction between "not set" and "set to nothing" is collapsed in `ctx.params` but preserved in shadow history.

**Concrete manifestation:** A callback that does `ctx.params.get("opt", None)` cannot distinguish between `--opt None` and no `--opt` passed. But `_shadow_params` would contain `UNSET` in the latter case, revealing the difference.

---

## Conservation Law

**Explicitness × Convenience = Constant**

The more convenient the parameter resolution (fewer explicit arguments, more inheritance, more defaults, more environment variables), the less explicit the final behavior. Every layer of inheritance adds convenience but removes observability. The product is conserved:

```
(1 / depth_of_inheritance) × (number_of_explicit_arguments) ≈ constant
```

A shallow context tree with many explicit arguments is equally "understandable" as a deep context tree with few explicit arguments — but they occupy opposite points on the same trade-off curve. You cannot maximize both inheritance convenience and parameter transparency simultaneously.
