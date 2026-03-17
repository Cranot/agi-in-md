# Historical Decision Tracing: Click Core

## Step 1: Decision Fossils

### 1. Parent-Cascading Configuration (Lines 37-98)
**Decision:** Configuration values inherit from parent Context through explicit fallback chains, not global state or explicit passing.

**Evidence:** The pattern `if X is None and parent is not None: X = parent.X` repeated 8+ times for `terminal_width`, `max_content_width`, `help_option_names`, `token_normalize_func`, `color`, `show_default`. The `obj` inheritance is special-cased: `if obj is None and parent is not None: obj = parent.obj`.

**Alternatives at decision time:**
- Global singleton configuration (simpler but not thread-safe)
- Explicit configuration objects passed through call stack
- Thread-local storage for CLI context
- Configuration registry with explicit lookup

**Why this won:** Enables nested command invocations where inner commands automatically respect outer settings while allowing per-command overrides. The `obj` special case (direct reference, not copy) allows sharing state across command hierarchy.

---

### 2. ParameterSource Enum (Lines 15-22)
**Decision:** Track where each parameter value originated via explicit enum, not just the value itself.

**Evidence:** `ParameterSource` enum with five values: `COMMANDLINE`, `ENVIRONMENT`, `DEFAULT`, `DEFAULT_MAP`, `PROMPT`. Used in `consume_value()` to track provenance, stored via `ctx.set_parameter_source()`.

**Alternatives at decision time:**
- No provenance tracking (just values)
- Debug-only tracking behind a flag
- String constants instead of enum
- Metadata dictionary on values

**Why this won:** Enables debugging ("why did this parameter have this value?"), testing (verify config file vs CLI override behavior), and documentation generation (show which defaults come from where). The enum provides type safety and exhaustive case handling.

---

### 3. `_protected_args` vs `args` Split (Lines 42-43, 228-233, 252-258)
**Decision:** Maintain two argument buffers — one reserved for subcommand resolution (`_protected_args`), one for current command consumption (`args`).

**Evidence:** `self._protected_args = []` initialized separately. In `Group.parse_args()`: `ctx._protected_args, ctx.args = rest[:1], rest[1:]` for non-chained, `ctx._protected_args = rest` for chained. In `Group.invoke()`: `args = [*ctx._protected_args, *ctx.args]` recombines before subcommand dispatch.

**Alternatives at decision time:**
- Single args list with position markers
- Full token stream with parsing state
- Recursive parsing without buffer separation
- Queue-based argument consumption

**Why this won:** Enables `chain` mode where multiple commands consume arguments sequentially without re-parsing. The protected buffer holds "not yet dispatched" arguments while `args` holds "current command's arguments". Without this split, chained commands would steal each other's arguments.

---

### 4. Divergent Defaults: `Command.allow_extra_args = False` vs `Group.allow_extra_args = True` (Lines 104, 200)
**Decision:** Groups tolerate extra arguments by default (they might be subcommand arguments); Commands do not (extra arguments are user error).

**Evidence:** `Command.allow_extra_args = False` (line 104), `Group.allow_extra_args = True` (line 200). Context constructor inherits from command: `if allow_extra_args is None: allow_extra_args = command.allow_extra_args`.

**Alternatives at decision time:**
- Same default for both (simpler but wrong for one case)
- No default, always explicit
- Parser-level configuration only

**Why this won:** Matches CLI semantics — `mytool extrafile.txt` is probably an error for a leaf command, but `mytool groupname extrafile.txt` might be arguments for a subcommand not yet resolved. The divergence anticipates the typical usage pattern.

---

### 5. `invoke()` as Wrapper + `callback` as Payload (Lines 79-85, 157-162, 259-295)
**Decision:** Commands are split into "invocation plumbing" (the `invoke` method, overridden in subclasses) and "user code" (the `callback` attribute, set at instantiation).

**Evidence:** `Command.invoke()` checks `if self.callback is not None: return ctx.invoke(self.callback, **ctx.params)`. `Group.invoke()` does complex subcommand resolution then calls `super().invoke(ctx)` which triggers callback. The callback is stored at construction, not overridden in subclasses.

**Alternatives at decision time:**
- Single `run()` method overridden in all commands
- Command classes with no separate callback concept
- Functional style: commands are just callables
- Event-based dispatch

**Why this won:** Enables two patterns simultaneously:
1. **Declarative CLI definition**: `@click.command() def myfunc(): ...` — callback is the decorated function
2. **Framework extension**: Subclass `Group` to override `invoke()` for custom dispatch logic (like the chain mode)

The callback/pattern split means framework hackers override `invoke`, while users provide `callback`.

---

## Step 2: Decision Dependencies

### The Inheritance Chain That Locks Everything Together

```
Decision A: Parent-cascading configuration
    ↓ forces
Decision B: Context constructor with 20+ parameters
    ↓ forces
Decision C: make_context() as factory method on Command
    ↓ prevents
Change C: Simple Context instantiation (can't create Context without Command)
```

**Longest dependency chain:**

```
Parent-cascading → Context needs parent reference → 
    Context must be created by something that knows parent →
        make_context() lives on Command →
            Commands own their Context lifecycle →
                Testing requires Command objects (can't test Context in isolation) →
                    Mock Command objects proliferate in test suites
```

**Cost to undo the root decision (parent-cascading configuration):**

- **Low:** Replace with explicit config object (300 lines changed)
- **Medium:** Replace with global registry (breaks nested invocation, 100 lines changed)
- **High:** Replace with thread-local storage (breaks asyncio compatibility, 150 lines changed)

The parent-cascading pattern is deeply embedded — removing it requires reworking every `if X is None and parent is not None` branch (8+ locations) plus the test fixtures that assume nested contexts inherit settings.

---

### The Protected Args Chain

```
Decision: _protected_args buffer
    ↓ forces
Decision: Group.parse_args() splits args into protected + current
    ↓ forces
Decision: Group.invoke() recombines before subcommand dispatch
    ↓ prevents
Change: Simple argument parsing (always must handle buffer management)
```

**Cost to undo:** Medium-high. The `_protected_args` concept is woven through Group's entire invocation flow. Removing it requires re-architecting chain mode entirely — currently chain mode depends on protected args accumulating across invocations.

---

## Step 3: Decision Conflicts

### Conflict 1: Callback Simplicity vs. Context Complexity

**Decision A:** `callback` is a simple callable — just a function, no framework knowledge required.
**Decision B:** Context has 20+ configuration knobs that affect callback behavior.

**Contradiction:** Users write simple `def myfunc(param):` callbacks, but those callbacks run inside a Context with `resilient_parsing`, `color`, `terminal_width`, `auto_envvar_prefix`, etc. The callback author doesn't control these — they're inherited from command-line invocation.

**Which breaks first:** The callback abstraction. Complex applications end up passing `ctx` to callbacks explicitly (`def myfunc(ctx, param)`), violating the "simple callable" promise. Evidence: `ctx.invoke(self.callback, **ctx.params)` — the callback receives params, not ctx, unless it explicitly requests ctx.

---

### Conflict 2: Inheritance Simplicity vs. Override Flexibility

**Decision A:** Child contexts automatically inherit parent settings (reduces configuration burden).
**Decision B:** Each context can override inherited settings (enables per-command customization).

**Contradiction:** If a child overrides `help_option_names`, does that affect sibling commands? No — each Context is independent. But `auto_envvar_prefix` is *computed* from parent: `parent.auto_envvar_prefix + "_" + self.info_name.upper()`. Some settings are inherited directly, some are transformed, some are not inherited at all (`params` is per-context, not inherited).

**Which breaks first:** The mental model. Users expect consistent inheritance semantics but get per-setting special cases. The `obj` is shared (same reference), `default_map` is looked up (nested lookup), `terminal_width` is copied. Three different inheritance semantics for three different settings.

---

### Conflict 3: Command Purity vs. Group Dispatch

**Decision A:** `Command.invoke()` should just call the callback — Command is a leaf, no subcommand logic.
**Decision B:** `Group.invoke()` must resolve subcommands, create sub-contexts, handle chain mode.

**Contradiction:** Group inherits from Command, so `Group.invoke()` calls `super().invoke(ctx)` *before* subcommand dispatch. This means the Group's callback runs before subcommands, not after. The result callback (`_result_callback`) runs after — a separate concept introduced to work around the inheritance order.

**Which breaks first:** Users who expect Group callbacks to run after subcommands. They discover `_result_callback` exists only after their callback runs at the wrong time. The `invoke_without_command` flag further complicates this — when is "no subcommand" determined?

---

### Conflict 4: Strict Parsing vs. Resilient Mode

**Decision A:** `resilient_parsing=False` means strict parsing — fail on unknown options, missing required params.
**Decision B:** `resilient_parsing=True` is checked in *multiple* places (Parameter.process_value, Command.parse_args, Group.resolve_command) to skip failures.

**Contradiction:** Resilient mode is not a parser configuration — it's a runtime flag checked throughout the codebase. This means parsing logic is scattered: `if not ctx.resilient_parsing: ctx.fail(...)`. Adding new failure conditions requires remembering to check resilient mode.

**Which breaks first:** New contributors who add validation without checking `resilient_parsing`. The pattern is "check before fail" not "configure parser to be strict/lenient". The `resilient_parsing` flag is a global bypass that every error site must respect.

---

## Step 4: Conservation Law

### The Conserved Quantity: **Explicitness × Convenience = Constant**

Every decision in Click trades explicit configuration for convenience, and the product is conserved:

| Decision | Explicitness Cost | Convenience Gain |
|----------|-------------------|------------------|
| Parent-cascading config | Hidden dependencies on parent state | No repeated configuration |
| ParameterSource enum | Extra bookkeeping for every param | Debugging visibility |
| `_protected_args` buffer | Two buffers to manage | Chain mode works |
| Callback + invoke split | Two places for "what command does" | Declarative + subclassable |
| `resilient_parsing` flag | Error sites must check flag | Shell completion works |
| `allow_extra_args` divergence | Different defaults per class | Common cases work |

**Conservation Law:**
```
Explicitness of control flow × Convenience of common cases = Constant
```

When convenience goes up (parent-cascading, default behaviors), explicitness goes down (hidden dependencies, scattered logic). When explicitness goes up (ParameterSource tracking), convenience goes down (extra bookkeeping).

---

### What Click ALWAYS Protects

**Protected:** The simple `@click.command()` decorator experience. A user can write a 3-line function and get a full CLI with help, error messages, and type conversion.

**Sacrificed:** Internals simplicity. The implementation is complex (20+ Context parameters, protected args buffer, multiple inheritance semantics) to preserve the simple user-facing API.

**Evidence:** The callback/pattern split (Decision 5) is the clearest example — framework complexity buys user simplicity. The `invoke()` method hierarchy is convoluted (Group.invoke calls super().invoke which calls callback, with result_callback separately) but users just write `def myfunc():`.

---

### What Click ALWAYS Sacrifices

**Sacrificed consistently:** Testability and internal conceptual integrity.

- Testing requires Command objects (can't instantiate Context standalone)
- Inheritance semantics vary per-setting (obj: shared, default_map: nested, terminal_width: copied)
- Parsing logic is scattered (resilient_parsing checks everywhere)
- Argument buffer management is manual (`_protected_args` manipulation in multiple methods)

**Protected consistently:** The decorated-function developer experience. Every complexity is justified by "but the user just writes `@click.command()`."

---

### Meta-Observation

The conservation law reveals Click's implicit priority hierarchy:

1. **User simplicity** (protected at all costs)
2. **Framework extensibility** (subclassable Command/Group/Context)
3. **Internal cleanliness** (sacrificed to protect 1 and 2)

This is why the codebase has structural fossils like `_protected_args` (complex, enables chain mode which enables complex CLIs) and divergent `allow_extra_args` defaults (inconsistent, but matches user mental model). Every wart protects the decorator experience.
