# Level 11: The Protocol Synchronization Boundary

---

## I. The Falsifiable Claim

L10 established that boundary detection = context creation = non-separable, and that this forces all sub-contexts to be created before any execute. L10 analyzed the *lifecycle* consequences of this separation (orphaned cleanup, sibling ordering). What L10 could not see: context creation is not merely tokenization. It is full parameter resolution.

`make_context` calls `parse_args`, which calls `handle_parse_result`, which calls `consume_value` and `process_value`. `process_value` calls `self.type_cast_value`, checks `self.required`, and calls `ctx.invoke(self.callback, ...)` for parameter callbacks. `consume_value` calls `self.get_default(ctx)`, which evaluates callable defaults — `self.default()` — if `self.default` is callable.

**The Claim:**

> In chain mode, the callable default mechanism — `Parameter.default` as a callable, evaluated inside `consume_value` during the parse phase — fires for ALL sub-commands before ANY sub-command callback executes. A callable default in cmd2 that expects to read cmd1's execution-time result (from `ctx.obj`, `ctx.meta`, or shared state) finds that state absent: cmd1 has not run when cmd2's callable default is called. This is not a timing deficiency — it is a consequence of parameter resolution being an atomic synchronization protocol. `handle_parse_result` runs four coupled systems simultaneously under a shared error context: type conversion, required-value validation, parameter callback invocation, and error attribution via `with augment_usage_errors(ctx, param=self)`. All four must co-execute because they share an error context established at parse time. Moving callable default evaluation to execution time requires splitting this protocol — which requires splitting type conversion, validation, callback invocation, and error attribution between two time points. The protocol cannot be split without either abandoning type safety for execution-time defaults, or running independent (duplicate) type and error-attribution passes at execution time.

**Falsifiable test:**

Construct a chain group with two commands. cmd2 has a callable default: `default=lambda: ctx_pipeline[0].get("cmd1_result", "MISSING")` where `ctx_pipeline[0]` is the shared pipeline dict (populated by cmd1's execution). Run the chain. Observe output order:

```
[parse phase]  cmd2 default evaluated → "MISSING"   ← fires during make_context for cmd2
[execute phase] cmd1 ran → stored "computed-value"
[execute phase] cmd2 received: MISSING               ← frozen at parse time, stale
```

cmd2's callable default fires during the parse loop, before cmd1's execute. The chain's temporal structure makes the parse phase's early firing observable.

---

## II. The Three-Expert Dialectic

**Expert A — Defender:**

*"This is the correct behavior of a correctly-designed system. Click parameters are INTERFACE declarations — typed, validated, documented in `--help`. Interface declarations are necessarily static: they must be resolvable at parse time for help generation, shell completion, and error attribution before any side effects occur. Callable defaults exist to compute fresh values from STABLE sources: environment, filesystem state, system configuration. They are not designed to access previous commands' outputs. For runtime data flow, Click provides `ctx.obj` and `ctx.meta` — unstructured but dynamic. The separation is intentional: parameters are declarative, state is imperative. Chain mode users who need cmd2 to depend on cmd1's result should use `ctx.obj`, not callable defaults."*

**Expert B — Attacker:**

*"The Defender says 'use `ctx.obj`' — but `ctx.obj` is untyped, undocumented, and invisible to `--help` and shell completion. If I build a pipeline where cmd1 produces a float and cmd2 consumes it, I want cmd2 to declare `@click.option('--value', type=float, default=...)` with a default that comes from cmd1. I want the help text to say 'Defaults to cmd1's output.' I want type validation. Click's parameter system is exactly designed for typed, documented, shell-completed values — and it cannot express the most common use case of a pipeline: typed data flow between commands. The callable default API explicitly implies dynamism — it's callable, it evaluates fresh, it can access runtime state. In chain mode, that implication is a lie."*

**Expert C — Prober:**

*"Both of you are arguing about whether callable defaults SHOULD access runtime state. Neither asked what parameter resolution structurally IS.*

*Read `handle_parse_result`:*

```python
def handle_parse_result(self, ctx, opts, args):
    with augment_usage_errors(ctx, param=self):
        value, source = self.consume_value(ctx, opts)   # callable default here
        value = self.process_value(ctx, value)           # type cast, validate, callback
    if self.expose_value:
        ctx.params[self.name] = value
    ...
```

*`with augment_usage_errors(ctx, param=self):` establishes a single error context that wraps BOTH `consume_value` (callable default) AND `process_value` (type conversion, required validation, parameter callback via `ctx.invoke`). These four operations share one error context. If any of them raises a `UsageError`, the context adds parameter identity, parameter type, and usage hint. They cannot be split between two time points without splitting the error context — and there is no mechanism in Click to maintain an error attribution context across time.*

*What both of you take for granted: that 'callable default evaluation' is a single extractable step in a pipeline. It is not. `consume_value` → `process_value` is a synchronization protocol where four systems co-execute:*

*1. **Type conversion**: the callable default's return value is immediately passed to `type_cast_value`. Moving callable defaults to execution time means running type conversion at execution time — but commandline values were type-cast at parse time. Two values for the same parameter (commandline vs callable default) would be type-cast at different times, with different error contexts.*

*2. **Required validation**: `if self.required and self.value_is_missing(value): raise MissingParameter`. This fires on CALLABLE DEFAULT OUTPUT. If the callable fires at execution time and returns None for a required parameter, `MissingParameter` is raised at execution time — after cmd1's side effects. 'Missing required parameter' after commands have run is a different contract than 'missing required parameter before any commands run.'*

*3. **Parameter callback invocation**: `ctx.invoke(self.callback, ...)` fires during `process_value`. `ctx.invoke` opens `with self:` on the sub-context, closing it. If this runs at execution time (inside the execute loop), it closes the sub-context before the command callback runs — L10's secondary finding reproduced at execution time.*

*4. **Error attribution**: `augment_usage_errors` establishes parse-time error context. At execution time, the context stack is different.*

*The structural question: why do all four need the same execution point? Because they share OUTPUT: the callable default produces a raw value, type conversion transforms it, validation checks the transformed value, and parameter callback may further transform it — all before the final value is stored in `ctx.params`. The chain is COMPOSITIONAL, not sequential and separable. There is no cut point where you can say 'everything before this point runs at parse time, everything after at execution time' without splitting the output chain.*"

---

## III. The Transformation

| | Claim |
|---|---|
| **Original** | "In chain mode, callable defaults fire during the parse phase before any command executes, so they cannot access previous commands' execution-time state." |
| **Transformed** | "Parameter resolution is an atomic synchronization protocol — type conversion, required validation, parameter callback invocation, and error attribution must co-execute because they form an output-compositional chain under a shared error context. Chain mode exposes that this protocol runs for ALL sub-commands before ANY sub-command executes. The callable default's callability creates an expectation of evaluation-time dynamism; the protocol's atomicity means evaluation time is fixed at parse time. The conflict between what 'callable' implies (dynamic, runtime-sensitive) and what the protocol requires (synchronous, parse-time) is invisible in single-command mode — where parse time and execution time coincide — and fully observable in chain mode, where they are separated by the entire duration of preceding commands' executions." |

---

## IV. The Gap as Diagnostic

The gap is the distance between **"callable defaults fire too early"** (a missing feature: move this step later) and **"parameter resolution is a co-executing protocol that cannot be split"** (a structural constraint: no cut point exists).

The mechanism:

### **"Dynamism Vocabulary Masking Phase Constraint"**

`self.default` is *callable*. In Python, `callable` implies: evaluated at call time, not at definition time; can access current state; produces different values on different calls. This vocabulary — the word "callable," the lambda syntax, the documentation "if the default is a function" — uniformly implies evaluation-time dynamism.

The phase constraint is buried in the call stack: `self.default()` is called inside `consume_value`, which is called inside `handle_parse_result`, which is called inside `parse_args`, which is called inside `make_context`'s `with ctx.scope(cleanup=False):` block, which is called inside the parse loop in chain mode.

"Callable" imports a semantics from Python's general programming model. "Inside the parse loop" is Click's structural reality. In single-command mode, these coincide: callable defaults fire "at runtime" because there is only one phase. In chain mode, they diverge: callable defaults fire "at parse time," which precedes execution by the full duration of preceding commands.

The concealment is precise: the word "callable" is true (it is called; the call is fresh each `main()` invocation; it can access environment state), but the implied semantics ("dynamism relative to the current execution context") exceeds what the phase constraint delivers.

---

## V. Apply the Concealment

Where does the mechanism most effectively hide?

In `consume_value`, at the transition from source-check fallthrough to default evaluation:

```python
if value is UNSET:
    default_map_value = ctx.lookup_default(self.name)
    if default_map_value is not UNSET:
        value = default_map_value
        source = ParameterSource.DEFAULT_MAP
if value is UNSET:
    default_value = self.get_default(ctx)    # ← callable fires HERE
    if default_value is not UNSET:
        value = default_value
        source = ParameterSource.DEFAULT
return value, source
```

The callable default is the LAST SOURCE consulted after commandline, environment, and default_map. Its position — last in a priority-descending sequence — implies it runs "when no other source was available, just before the value is needed." "Just before the value is needed" in single-command mode means "just before the command runs." The structural reality in chain mode: "just before the value is needed" means "during the parse loop, before any command in the chain runs."

The concealment is reinforced by `ctx.lookup_default`, which is also callable-aware:

```python
def lookup_default(self, name, call=True):
    if self.default_map is not None:
        value = self.default_map.get(name, UNSET)
        if call and callable(value):
            value = value()
        return value
    return UNSET
```

Default-map values are ALSO callable, ALSO called at parse time. The callable pattern is pervasive: both `self.default` and `default_map` values support callables, both fire at parse time. The pervasiveness makes "callable = parse-time" feel like a consistent choice, hiding that it conflicts with chain mode's temporal structure.

---

## VI. A Legitimate-Looking Improvement That Deepens the Concealment

Add an execution-time result registry, accessible via `ctx.meta`, that makes it *appear* that inter-command typed data flow is achievable:

```python
class ChainRegistry:
    """Typed result registry for chain command pipelines.
    Commands can publish outputs; subsequent commands can consume them."""

    def __init__(self):
        self._outputs: dict[tuple[str, str], t.Any] = {}
        self._types: dict[tuple[str, str], type] = {}

    def publish(self, cmd_name: str, key: str, value: t.Any, type_: type = object) -> None:
        self._outputs[(cmd_name, key)] = value
        self._types[(cmd_name, key)] = type_

    def consume(self, cmd_name: str, key: str, type_: type = None, default=None) -> t.Any:
        value = self._outputs.get((cmd_name, key), default)
        if type_ is not None and value is not default:
            return type_(value)
        return value

# In Group.invoke, chain case:
with ctx:
    ctx.invoked_subcommand = "*" if args else None
    super().invoke(ctx)

    registry = ChainRegistry()
    ctx.meta["_chain_registry"] = registry   # accessible everywhere via ctx.meta

    contexts = []
    while args:
        cmd_name, cmd, args = self.resolve_command(ctx, args)
        assert cmd is not None
        sub_ctx = cmd.make_context(cmd_name, args, parent=ctx,
                                   allow_extra_args=True,
                                   allow_interspersed_args=False)
        contexts.append(sub_ctx)
        args, sub_ctx.args = sub_ctx.args, []

    rv = []
    for sub_ctx in contexts:
        with sub_ctx:
            result = sub_ctx.command.invoke(sub_ctx)
            if isinstance(result, dict):
                for k, v in result.items():
                    registry.publish(sub_ctx.info_name, k, v)
            rv.append(result)

    return _process_result(rv)
```

**Why this passes code review:** `ChainRegistry` is a clean abstraction for inter-command communication. It's stored in `ctx.meta` (Click's documented shared-state channel). The `publish`/`consume` API is explicit and readable. The convention "commands return dicts to publish to the pipeline" is familiar from task frameworks (Luigi, Prefect). A senior reviewer would approve this as the correct solution to pipeline communication.

**Why it deepens the concealment:**

`ChainRegistry` provides a RUNTIME communication channel that looks like it solves typed inter-command dependency. A user writes cmd2 as:

```python
@cmd_group.command()
@click.pass_context
def cmd2(ctx):
    registry = ctx.meta["_chain_registry"]
    value = registry.consume("cmd1", "result", type_=float)
    # Typed access to cmd1's output — this works at execution time
```

This works. At execution time, cmd1 has run, the registry is populated. The improvement makes the impossible appear solved — typed, explicit inter-command data flow. The concealment: `registry.consume` is called INSIDE the command callback, bypassing the parameter system entirely. `value` is NOT a `@click.option` — it has no `--help` entry, no shell completion, no `required` checking, no `UsageError` attribution. The registry satisfies the RUNTIME need while making the parameter system's limitation disappear from view.

Deeper concealment: the registry is stored in `ctx.meta["_chain_registry"]` BEFORE sub-context creation. It is therefore accessible inside callable defaults (via `ctx.meta` during `make_context`). But the registry is EMPTY at parse time. A callable default that calls `registry.consume("cmd1", "result")` gets `None` (the default). The improvement makes it look like the channel is universally available (it IS accessible from callable defaults) while hiding that it contains nothing useful at the time those defaults fire. The empty registry is a temporal witness — visible but silent about why it's empty.

---

## VII. Three Properties Only Visible Because of the Strengthening

**1. The registry must be created before the parse loop to be accessible from callable defaults — but it is populated after the execute loop. Its creation time and population time are separated by the entire chain execution.**

Writing `ChainRegistry` forces a placement decision: where does `registry = ChainRegistry()` go? It must go before the `while args:` parse loop (callable defaults need it accessible during `make_context`). But it is populated inside `for sub_ctx in contexts:` (execute loop). No placement makes the registry simultaneously populated (for callable defaults) and created before the parse loop. The strengthening makes visible a temporal invariant: any resource created before the parse loop is necessarily empty during the parse loop. The phase boundary is not just a timing quirk — it is an absolute separation between "state that exists before any command parses" and "state that exists after any command executes."

**2. The registry's `consume` call inside a callable default accesses `ctx.meta` on the sub-context being created — which is the SAME dict object as the group context's `_meta`. But callable defaults fire inside `make_context`'s `with ctx.scope(cleanup=False):`, so `ctx` here is the sub-context being created, not the group context. The registry was stored on the GROUP context's `_meta`. It is accessible because `_meta` is a shared object (`self._meta = getattr(parent, "meta", {})` assigns the same dict). This sharing — previously an invisible design choice — becomes load-bearing for the registry's accessibility, and simultaneously reveals that the registry's emptiness is not a code error but a structural one: the registry is shared and reachable, but empty because execution precedes population.**

**3. Callable defaults that attempt to use the registry close their sub-context during the attempt.**

If a callable default is a parameter CALLBACK (registered via `callback=` on a parameter), `process_value` calls `ctx.invoke(self.callback, ...)`. `ctx.invoke` opens `with self:` on the sub-context being created. The callback accesses the empty registry. When `ctx.invoke`'s `with self:` exits, the sub-context is closed. This is L10's secondary finding reproduced inside the strengthening. The registry access is not just too early (empty) — the ATTEMPT to access it via a parameter callback closes the sub-context. The two problems (wrong time, wrong lifecycle) are co-located: both manifest in the same call site (`ctx.invoke` inside `process_value`). The strengthening reveals they are not independent bugs but the same mechanism (`ctx.invoke`'s `with self:`) producing two different problems depending on which expectation is violated.

---

## VIII. The Contradictory Improvement

**Improvement 2**: Introduce a `lazy_default` marker that defers callable default evaluation to execution time:

```python
class _LazyDefault:
    """Wraps a callable to be evaluated at command execution time, not parse time.
    Use when the default value depends on a previous command's result."""
    
    def __init__(self, factory: cabc.Callable[[], t.Any]):
        self.factory = factory
    
    def __call__(self) -> _LazyDefault:
        return self  # Return self when called by get_default's `if callable(default): default()`
    
    def resolve(self) -> t.Any:
        return self.factory()

_LAZY = object()  # sentinel stored in ctx.params for lazy-default parameters

# In Parameter.consume_value, detect lazy defaults:
def consume_value(self, ctx, opts):
    value = opts.get(self.name, UNSET)
    source = ParameterSource.COMMANDLINE if value is not UNSET else ParameterSource.DEFAULT
    if value is UNSET:
        envvar_value = self.value_from_envvar(ctx)
        if envvar_value is not None:
            value = envvar_value
            source = ParameterSource.ENVIRONMENT
    if value is UNSET:
        default_map_value = ctx.lookup_default(self.name)
        if default_map_value is not UNSET:
            value = default_map_value
            source = ParameterSource.DEFAULT_MAP
    if value is UNSET:
        raw = self.default
        if isinstance(raw, _LazyDefault):
            return _LAZY, ParameterSource.DEFAULT  # defer; bypass type/validate
        if callable(raw):
            raw = raw()
        if raw is not UNSET:
            value = raw
            source = ParameterSource.DEFAULT
    return value, source

# In Command.invoke, resolve lazy parameters before invoking callback:
def invoke(self, ctx):
    if self.deprecated:
        ...
    for param in self.params:
        if ctx.params.get(param.name) is _LAZY:
            assert isinstance(param.default, _LazyDefault)
            resolved = param.default.resolve()
            resolved = param.type_cast_value(ctx, resolved)
            ctx.params[param.name] = resolved
    if self.callback is not None:
        return ctx.invoke(self.callback, **ctx.params)
```

**Why this passes review:** `lazy_default` is an explicit opt-in for execution-time evaluation. The `_LAZY` sentinel clearly marks deferred values. Resolution happens in `Command.invoke` before the callback — the callback always receives fully resolved parameters. The API is minimal and the changes are localized.

**Why it contradicts Improvement 1:**

Improvement 1 accepts that parameters are parse-time; it adds a runtime channel ALONGSIDE the parameter system. It says: "parameters declare static interfaces; use the registry for runtime dependencies."

Improvement 2 extends the parameter system to support runtime evaluation. It says: "parameters CAN carry runtime dependencies if marked with `lazy_default`."

These encode opposite answers to: **"Is the parameter layer the right place to express execution-time inter-command dependencies?"**

With Improvement 1: no — parameters are static; a separate channel handles dynamics.  
With Improvement 2: yes — parameters can be dynamic if opted in.

Both pass code review independently. They cannot both be applied. Choosing between them requires knowing whether the parameter system's parse-time guarantee is a FEATURE (preserve it; use a separate channel) or a LIMITATION (override it; make defaults lazy). The original code encodes neither position.

---

## IX. The Structural Conflict

Improvement 1 says: **"Preserve parse-time parameter semantics; runtime dependencies use a separate, untyped channel."**

Improvement 2 says: **"Extend the parameter system to support execution-time defaults."**

The conflict: the parameter system serves four masters simultaneously — type safety, required-value validation, `--help` generation, and error attribution. ALL FOUR assume parse-time availability:

- **`--help` generation**: calls `get_default(ctx)` to display the current default value. For a `_LazyDefault`, this calls `self.factory()` during help generation — accessing state that doesn't exist (no prior commands have run in a `--help` invocation).
- **`MissingParameter`**: raised at parse time, before any side effect. With `_LAZY`, `required` parameters that receive no commandline value silently pass `_LAZY` through parse time. `MissingParameter` is never raised at parse time. At execution time, `param.default.resolve()` might return `None` — but the `required` check already passed. The required-value contract is violated.
- **Error attribution**: `augment_usage_errors(ctx, param=self)` establishes a parse-time context. The `_LAZY` resolution in `Command.invoke` has no equivalent error attribution — errors in `param.default.resolve()` or `param.type_cast_value` appear without parameter context.
- **Shell completion**: during `resilient_parsing=True`, callbacks are skipped but parameters are still resolved. `_LAZY` at resilient-parse time leaves `ctx.params[name] = _LAZY` — completions that depend on this parameter's value receive the sentinel object, not a valid value.

The conflict is not between Improvement 1 and Improvement 2 as designs. It is between "the parameter system has parse-time invariants baked into four independent subsystems" and "some parameters need execution-time evaluation." These cannot be reconciled without modifying all four subsystems — which is not an improvement but a redesign.

---

## X. The Third Improvement: Resolution Attempt

Separate the STATIC METADATA of a parameter (type annotation, required flag, help text) from its VALUE RESOLUTION, and run a staged protocol: metadata at parse time, value at execution time:

```python
class StagedParameter(Option):
    """Two-stage parameter: metadata resolved at parse time, value resolved at execution time.
    Stage 1 (parse): commandline/env/default_map → type-cast and validate immediately.
    Stage 2 (execute): callable default → type-cast and validate at invocation.
    Full type/validation/error protocol runs in both stages."""
    
    def __init__(self, *args, stage2_default: cabc.Callable = None, **kwargs):
        super().__init__(*args, default=UNSET, required=False, **kwargs)
        self._stage2_default = stage2_default
        self._stage2_required = kwargs.get("required", False)
    
    def consume_value(self, ctx, opts):
        # Stage 1: static sources only; do not evaluate stage2_default
        value = opts.get(self.name, UNSET)
        source = ParameterSource.COMMANDLINE if value is not UNSET else ParameterSource.DEFAULT
        if value is UNSET:
            envvar_value = self.value_from_envvar(ctx)
            if envvar_value is not None:
                value = envvar_value
                source = ParameterSource.ENVIRONMENT
        if value is UNSET:
            default_map_value = ctx.lookup_default(self.name)
            if default_map_value is not UNSET:
                value = default_map_value
                source = ParameterSource.DEFAULT_MAP
        return value, source   # returns UNSET if no static source provided
    
    def stage2_resolve(self, ctx: Context) -> None:
        """Resolve execution-time default. Called by Command.invoke before callback."""
        if ctx.params.get(self.name) is not UNSET:
            return  # static source resolved this; no stage 2 needed
        with augment_usage_errors(ctx, param=self):
            value = self._stage2_default() if self._stage2_default is not None else None
            value = self.type_cast_value(ctx, value)
            if self._stage2_required and self.value_is_missing(value):
                raise MissingParameter(ctx=ctx, param=self)
            if self.callback is not None and not ctx.resilient_parsing:
                value = ctx.invoke(self.callback, ctx=ctx, param=self, value=value)
            ctx.params[self.name] = value

# In Command.invoke:
def invoke(self, ctx):
    if self.deprecated:
        ...
    for param in self.params:
        if isinstance(param, StagedParameter):
            param.stage2_resolve(ctx)
    if self.callback is not None:
        return ctx.invoke(self.callback, **ctx.params)
```

**How this fails:**

`stage2_resolve` calls `ctx.invoke(self.callback, ctx=ctx, param=self, value=value)` — the parameter's callback, run at execution time. `ctx.invoke` opens `with self:` on `ctx` (the sub-context). The sub-context closes. `stage2_resolve` returns. Then `Command.invoke` calls `ctx.invoke(self.callback, **ctx.params)` — the COMMAND callback, also calling `with self:` on the same now-closed sub-context.

The sub-context is closed twice: once during `stage2_resolve`'s parameter callback, once during the command callback. Close is idempotent — mechanically safe. But: any resource registered during the stage-2 parameter callback via `ctx.with_resource(resource)` is pushed onto `ctx._exit_stack`. When the stage-2 parameter callback's `ctx.invoke` exits, `ctx.close()` runs, `ctx._exit_stack.close()` runs, the resource is cleaned up. Then the command callback runs. The resource is gone. The command callback cannot access resources acquired by the stage-2 parameter callback.

This is L10's secondary finding reproduced at execution time. The mechanism is identical: `ctx.invoke`'s `with self:` closes the context before the "next" phase of execution. At parse time, the "next phase" is the execute loop. At execution time, the "next phase" is the command callback. The problem does not move in time; it moves in call depth.

Additionally: `stage2_resolve` calls `with augment_usage_errors(ctx, param=self):` inside `Command.invoke`. But `Command.invoke` is itself called inside `with sub_ctx:` inside the execute loop, which is inside `with ctx:` in `Group.invoke`. The error attribution context stack at this call site is different from parse time — it contains group-level wrappers. A `UsageError` raised by `type_cast_value` during stage 2 exits through `augment_usage_errors(ctx, param=self)` (adding parameter info) and then propagates through `Group.invoke`'s `with ctx:` block — potentially triggering group-level error handling before reaching the user. The error message format differs from parse-time errors. Two invocations of the same chain with the same invalid input may produce different error messages depending on whether the error originates in stage 1 or stage 2.

---

## XI. What the Failure Reveals

The three-constraint impossibility L10 found ({validate-all, execute-eager, correct cleanup}) appears in a different space here. The failure of `StagedParameter` reveals a constraint L10 could not see from the lifecycle analysis alone:

**The parameter resolution protocol and the context lifecycle protocol share one mechanism — `ctx.invoke`'s `with self:` — that serves as both parameter callback executor AND context lifecycle terminator. The sharing produces opposite problems at opposite phase boundaries:**

- At **parse time** (L10's secondary finding): `ctx.invoke` inside `process_value` closes the sub-context during `make_context`. Resources acquired by parameter callbacks are unavailable when the sub-context enters the execute loop.
- At **execution time** (`StagedParameter`'s failure): `ctx.invoke` inside `stage2_resolve` closes the sub-context during `Command.invoke`. Resources acquired by stage-2 parameter callbacks are unavailable when the command callback runs.

The shared mechanism does not produce the same problem at both locations — it produces MIRROR PROBLEMS: parse-time invocation kills pre-execute resources; execution-time invocation kills pre-callback resources. Moving parameter callback invocation from parse time to execution time relocates the resource unavailability window but cannot eliminate it, because `ctx.invoke`'s `with self:` closes the context at every use site regardless of which phase it's called from.

**What the failure reveals about the design space that the conflict alone could not:**

The conflict (Improvement 1 vs 2) showed that you cannot satisfy "parse-time parameter semantics" and "runtime-evaluated parameters" simultaneously for the same parameter. This looked like a TIMING problem: parameters resolve at the wrong time. The failure of `StagedParameter` reveals it is a MECHANISM problem: `ctx.invoke` is both the parameter callback executor and the context lifecycle terminator. Any attempt to run parameter callbacks at execution time NECESSARILY uses `ctx.invoke`, NECESSARILY closes the context, NECESSARILY makes resources acquired during those callbacks unavailable to the command callback.

The design space has a hard boundary: if you want parameter callbacks to run, you need `ctx.invoke`. If you need `ctx.invoke`, you close the context. You cannot run parameter callbacks at execution time without closing the context before the command callback runs. The resource window that "staged parameter resolution" tries to establish does not exist — `ctx.invoke` collapses it.

---

## XII. The Fourth Construction: Accepting the Topology

The design space has a feasible region: parameters resolve at parse time (giving up runtime defaults), OR runtime dependencies flow through untyped state channels (giving up type safety and documentation for cross-command dependencies). The infeasible region is the intersection: typed, documented, shell-completed runtime inter-command parameter dependencies.

Accept the topology. Design for the feasible point where the parameter layer and the runtime data-flow layer are EXPLICITLY separated with a typed interface between them:

```python
@dataclass(frozen=True)
class PipelineOutput:
    """A typed, named output from a chain command.
    Declared by the command; consumed explicitly by subsequent commands."""
    cmd_name: str
    key: str
    value: t.Any
    python_type: type

class TypedPipeline:
    """Execution-time typed data flow for chain commands.
    Provides type-checked access to previous commands' declared outputs.
    Intentionally NOT integrated with Click's parameter system."""

    def __init__(self):
        self._store: dict[tuple[str, str], PipelineOutput] = {}

    def publish(self, cmd_name: str, key: str, value: t.Any, type_: type = object) -> None:
        if not isinstance(value, type_):
            try:
                value = type_(value)
            except (TypeError, ValueError) as e:
                raise RuntimeError(
                    f"Pipeline type error: {cmd_name!r}.{key!r} "
                    f"expected {type_.__name__}, got {type(value).__name__}: {e}"
                ) from e
        self._store[(cmd_name, key)] = PipelineOutput(cmd_name, key, value, type_)

    def consume(self, cmd_name: str, key: str, type_: type = object, default: t.Any = None) -> t.Any:
        entry = self._store.get((cmd_name, key))
        if entry is None:
            return default
        if not issubclass(entry.python_type, type_):
            raise TypeError(
                f"Pipeline type mismatch: {cmd_name!r}.{key!r} "
                f"was published as {entry.python_type.__name__}, requested as {type_.__name__}"
            )
        return entry.value

    def available(self) -> list[PipelineOutput]:
        return list(self._store.values())

# In Group.invoke, chain case — TypedPipeline as first-class execution state:
_PIPELINE_KEY = "__typed_pipeline__"

with ctx:
    ctx.invoked_subcommand = "*" if args else None
    super().invoke(ctx)

    pipeline = TypedPipeline()
    ctx.meta[_PIPELINE_KEY] = pipeline

    contexts = []
    while args:
        cmd_name, cmd, args = self.resolve_command(ctx, args)
        assert cmd is not None
        sub_ctx = cmd.make_context(cmd_name, args, parent=ctx,
                                   allow_extra_args=True,
                                   allow_interspersed_args=False)
        contexts.append(sub_ctx)
        args, sub_ctx.args = sub_ctx.args, []

    rv = []
    for sub_ctx in contexts:
        with sub_ctx:
            result = sub_ctx.command.invoke(sub_ctx)
            rv.append(result)

    return _process_result(rv)
```

Command authors use the pipeline explicitly:

```python
@cmd_group.command()
@click.pass_context
@click.option("--threshold", type=float)
def analyze(ctx, threshold):
    pipeline: TypedPipeline = ctx.meta[_PIPELINE_KEY]
    count = pipeline.consume("collect", "count", type_=int, default=0)
    # ... process
    pipeline.publish("analyze", "result", result_value, type_=float)
```

**What it sacrifices:**

The `TypedPipeline` redesign sacrifices DECLARATIVE INTERFACE for inter-command dependencies. `analyze --help` shows `--threshold` as a parameter. It shows nothing about `analyze`'s dependency on `collect`'s `count` output. The dependency exists — it's typed and checked at runtime — but it is invisible to Click's documentation infrastructure, shell completion, and the user reading `--help`. A user cannot know from the interface that `analyze` only produces meaningful results after `collect` has run.

The redesign also sacrifices PROTOCOL SYMMETRY: the parameter layer and the pipeline layer use different type systems. `@click.option("--threshold", type=float)` gives Click-integrated type conversion with `UsageError` formatting. `pipeline.consume(..., type_=int)` gives Python `TypeError` with no CLI context. Two type systems, no integration. A command author must mentally track which errors come from which layer, and users see inconsistent error formatting depending on whether the error originates in parameter parsing or pipeline consumption.

Additionally, `TypedPipeline` requires commands to know the names of previous commands (`pipeline.consume("collect", "count", ...)`). This is a HARD COUPLING by name string. If `collect` is renamed, every downstream `consume` call silently falls back to `default`. There is no mechanism to detect the coupling breakage at parse time, at registration time, or during help generation. The coupling is invisible and silent-failure.

**What the original design reveals was never a flaw:**

The `TypedPipeline` redesign's sacrifices — invisible inter-command dependencies, split type systems, silent name-coupling — reveal that the original design's SEPARATION of the parameter layer from the state layer was not a deficiency. It was the correct response to an architectural incompatibility.

Click's parameter system is a **declarative interface protocol**: the command's `--help` output, shell completion hints, required-argument checking, and type validation all require that parameter values be determinable at parse time from stable sources (commandline tokens, environment, defaults). These four capabilities exist because parameters are declarations — they describe the command's interface, which is fixed.

Chain mode's inter-command dependencies are an **imperative execution protocol**: cmd1 runs, produces a result, cmd2 consumes it. This is runtime behavior, contingent on execution order, unavailable before execution begins.

These two protocols require fundamentally opposite temporal semantics. The parameter protocol requires parse-time determinism. The execution protocol requires execution-time contingency. They cannot share a mechanism without one breaking the other.

What the original code was APPARENTLY attempting: provide both protocol layers through a unified mechanism (callable defaults as the bridge). The ACTUAL design delivered only one: the parameter layer's parse-time protocol. Callable defaults, despite their name, participate only in the parameter layer — they run at parse time, inside the parameter resolution protocol, with the same type/validation/error-attribution protocol as static defaults.

The property the redesign reveals was never a flaw: **Click's parameter system's parse-time guarantee is not a limitation of chain mode — it is the correct implementation of what a parameter IS.** Parameters are typed, documented, shell-completed interface declarations. Interface declarations must be knowable before execution; that is what "interface" means. Chain mode reveals this correctness by making the temporal separation explicit: ALL interfaces declared, THEN ALL commands executed. The separation is not a chain-mode bug. It is the correct temporal structure for a system that maintains a clear boundary between declaring what commands need and executing what commands do.

The cost of attempting to express runtime contingency through declarative parameters: the callable default mechanism creates a false impression that parameters can be dynamically runtime-sensitive, while delivering parse-time evaluation. Chain mode does not CREATE this tension — it REVEALS it. The impossible thing the original design implicitly attempts is not having chain mode; it is having parameters that are simultaneously DECLARATIONS (knowable at parse time, documentable) and PIPELINE CONNECTORS (contingent on execution order). These are different things. Click built a parameter system. It did not build a pipeline connector system. Chain mode reveals, rather than creates, the absence of the second thing.

---

## XIII. The Updated Diagonal

| Level | Finding | Mechanism | Missing Concept |
|---|---|---|---|
| **L7** | 15+ value-source authorities, no priority contract | Local coherence masking systemic incoherence | Priority contract for value sources |
| **L8** | `DEFAULT` = two states; `UNSET` destroyed before consumers observe it | Stage-boundary correctness masking pipeline-level information destruction | Representation of "no default exists" |
| **L9** | `Context.__exit__` closes at first encounter; outer blocks structurally inert | Mechanism reuse masking purpose collision | Designated lifecycle owner per context |
| **L10** | Chain mode parse/execute separation forced; context tree has no sibling protocol; partial failure orphans contexts | Topological projection masking structural incompatibility | First-class sibling sequence |
| **L11** | Parameter resolution is an atomic co-execution protocol (type, validate, callback, error attribution) synchronizing at parse time; callable defaults participate in this protocol and therefore fire before any chain command executes; no split point exists | Dynamism vocabulary masking phase constraint | Staged parameter resolution (impossible: the protocol's output-compositional chain cannot be split without redesigning all four co-executing systems) |

**The evolved deep pattern:**

Each level has found a SYNCHRONIZATION POINT where multiple systems must coincide in time. Single-command mode provides the synchronization by collapsing all phases into one. Chain mode breaks the synchronization by making the phase separation temporal and observable.

- L7: value-source systems synchronize at `consume_value` — PRIORITY is missing  
- L8: source-annotation and source-presence synchronize at `consume_value` — ABSENCE is missing  
- L9: lifecycle and ownership synchronize at `Context.__exit__` — OWNERSHIP is missing  
- L10: context-creation and boundary-detection synchronize at `make_context` — SIBLING SEQUENCE is missing  
- L11: type, validation, callback, and error-attribution synchronize at `handle_parse_result` — STAGING is impossible (not just missing: the co-execution protocol cannot be split without disintegrating all four systems simultaneously)

The diagonal's terminal finding: the accumulation of missing concepts is not a list of independent deficiencies. Each missing concept corresponds to a DIMENSION of the single operation `make_context` that Click conflates into one: source priority (L7), source presence (L8), lifecycle ownership (L9), sibling ordering (L10), evaluation staging (L11). All five dimensions are resolved simultaneously, inside a single call to `make_context`. The architectural problem is not that each dimension's resolution mechanism is wrong — it is that they are all bound to the same operation, making them inseparable. Chain mode requires that some dimensions be resolved at different times for different commands. Because the dimensions are bound together in `make_context`, none can be resolved independently. The impossible thing Click is attempting is sequential per-command resolution while maintaining simultaneous multi-dimensional binding. These are incompatible, and chain mode makes the incompatibility visible by creating temporal distance where single-command mode provided temporal coincidence.
