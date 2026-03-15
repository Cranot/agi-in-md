# Temporal Simulation: Click Core

## Cycle 1: New Developer Joins

**Misunderstands**: The `_protected_args` vs `args` distinction in Group. Why does `parse_args` return different values for chained vs non-chained groups? The `[*ctx._protected_args, *ctx.args]` reconstruction in `invoke()` looks like bookkeeping noise.

**Assumption violated**: That `Context` can be reused. They call `ctx.invoke()` twice on the same context, not understanding `_context_entered` flag prevents re-entry. Subtle breakage: callbacks fire once, cleanup happens early.

**What breaks**: The `forward()` method — they pass overlapping kwargs that conflict with `**self.params`, causing silent overwrites. Debugging leads them to add print statements in `consume_value()`, which calcify into "logging."

## Cycle 2: Dependency Updates

**Breaking change**: `contextlib.ExitStack` changes exception propagation semantics during cleanup. The `_close_callbacks` now fire in different order.

**Shock absorbed**: `ParameterSource` enum — internal, isolated.

**Shock propagated**: The `gettext` ngettext signature change ripples through every `ctx.fail()` call. The `collections.abc` import path deprecation forces `isinstance(commands, abc.Sequence)` rewrite.

**Calcifies**: Version pinning comments. A `try/except` around `with self:` in `invoke()` that "handles" the new exception wrapping. This patch becomes load-bearing when ExitStack behavior reverts.

## Cycle 3: Original Author Leaves

**Lost knowledge**:
- Why `Group.allow_extra_args = True` but `Command.allow_extra_args = False` — the chaining requirement
- The `resolve_command()` three-tuple return `(cmd_name, cmd, args)` exists for error message preservation
- `UNSET` sentinel vs `None` distinction: `None` is a valid parameter value, `UNSET` means "not provided"

**Cargo cult**: The entire `iter_params_for_processing()` call pattern. Developers copy it without understanding eager vs normal parameter ordering.

**Unfixable**: The `default_map` inheritance logic — `parent.default_map.get(info_name)` assumes string keys match command structure. Changing this breaks every config file in production.

## Cycle 4: Usage Grows 10x

**Failed assumptions**:
- Context creation per invocation was "cheap" — now visible in profiles
- Parent chain walks for every `lookup_default()` call compound: O(depth × lookups)
- `_opt_prefixes` set copied on every Context creation

**Permanent infrastructure**:
- A `@lru_cache` on `convert_type()` that shouldn't exist (types can be stateful)
- `default_map` pre-flattening in `make_context()` to avoid per-lookup walks
- A "context pool" that reuses Context objects with manual `__dict__.clear()` — a time bomb

## Cycle 5: Security Audit

**Hidden trust assumptions exposed**:
- `default_map` values can be callables: `if call and callable(value): value = value()` — arbitrary execution from config files
- `envvar` values pass through `type.convert()` without length limits — DoS vector on unbounded nargs
- `ctx.obj` inheritance: parent command's `obj` leaks to all subcommands, including ones added dynamically
- `_meta` dictionary copy is shallow — nested dicts shared across context siblings

**Boundaries that weren't**:
- The `callback` parameter accepts any callable — no validation, no sandbox
- `shell_complete` callbacks execute during tab-completion with full process privileges

---

## Derive: Conservation Law

**Conservation Law: Control Locality × State Propagation = K**

As local control flow becomes clearer (nice `invoke()` methods, clean `parse_args()`), state propagates further invisibly (parent chain lookups, default_map inheritance, `_meta` shallow copies). The code sacrifices **debuggability** for **composability**.

What calcifies across all five cycles: **implicit inheritance paths**. Each fallback (`if X is None and parent is not None`) adds a path that can never be removed because downstream code depends on the behavior, even if that behavior was accidental.

The invariant: **Every layer of fallback adds one layer of untestable coupling.**

---

## Diagnostic: Self-Analysis

**My temporal assumption**: I assumed this code remains in active, maintained use. A sixth cycle — **abandonment** — would reveal that my "calcification" predictions are too optimistic. Without active maintenance, it's not that workarounds become permanent; it's that the code becomes archaeology. The `UNSET` sentinel's purpose, the `_protected_args` semantics, the eager/normal parameter split — these become **undecidable**.

**What Cycle 6 reveals**: My analysis assumes a future where someone reads the code. In true abandonment, the conservation law shifts to **Artifact Complexity × Archaeological Effort = K**. The more complex the artifact, the less any future reader can know with certainty. My predictions about "what breaks" presume breakage is *noticed*.
