# Genesis Analysis: Click Core

## Step 1: Name the Trap

**Conservation Law: Convenience × Visibility = constant**

Click's architecture is built on a single, relentless trade-off: every mechanism that makes CLI authoring convenient (inheriting from parent Context, cascading `auto_envvar_prefix`, multi-source `ParameterSource` resolution, `default_map` lookups that chain through parents) makes runtime behavior invisible.

The trap manifests in three structural patterns:

1. **Context as inheritance avalanche**: 15+ properties inherit from parent with fallback logic. `auto_envvar_prefix` computes itself via string concatenation up the parent chain. Where does a value come from? You must trace the entire ancestry.

2. **Parameter resolution as priority maze**: `consume_value()` tries commandline → environment → default_map → default. Four sources, any of which can be overridden at any Context level. The `ParameterSource` enum records *which* source, but not *why* or *through what path*.

3. **Invocation as distributed state machine**: `Group.invoke()` mutates `ctx._protected_args`, `ctx.args`, creates `sub_ctx`, chains `super().invoke()`, conditionally processes results. Control flow is spread across inherited methods, each modifying shared state.

**What is sacrificed**: When you write `@click.option('--verbose', is_flag=True)`, you get convenience. When `verbose` appears in your callback and you need to know why it's `True` when you expected `False`, you sacrifice visibility. The conservation law is iron: you cannot have both implicit inheritance chains AND explicit provenance.

---

## Step 2: Break the Law

**System Design: The Configuration Manifest Architecture**

A fundamentally different architecture where Convenience AND Visibility are both maximized:

```
┌─────────────────────────────────────────────────────────────────┐
│                     MANIFEST BUILDER                            │
│  argv + env + config_files → ResolutionGraph (immutable)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MANIFEST (frozen)                           │
│  - all_params: dict[str, ResolvedValue]                         │
│  - provenance: dict[str, DecisionChain]                         │
│  - command_path: tuple[str, ...]                                │
│  - NO inheritance, NO lazy computation, NO mutation             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     COMMAND (pure function)                     │
│  def cmd(manifest: Manifest) → Result                           │
│  - No Context object, no parent chain, no callbacks to ctx      │
└─────────────────────────────────────────────────────────────────┘
```

**Components:**

1. **ResolvedValue** (replaces raw parameter values):
```python
@dataclass(frozen=True)
class ResolvedValue:
    value: Any
    source: Literal['cli', 'env', 'config', 'default']
    source_location: str  # argv[3], MYAPP_VERBOSE, config.yaml:5
    transform_chain: tuple[Transform, ...]  # every conversion applied
    precedence_reason: str  # "env overrides default because..."
```

2. **DecisionChain** (provenance for every parameter):
```python
@dataclass(frozen=True)
class DecisionChain:
    parameter_name: str
    candidates: tuple[Candidate, ...]  # all sources that COULD have provided value
    winner: Candidate  # which one did
    rejection_reasons: dict[str, str]  # why each loser lost
```

3. **ManifestBuilder** (replaces Context construction):
```python
class ManifestBuilder:
    def build(self, argv: list[str], env: dict, config: Mapping) -> Manifest:
        # ALL resolution happens HERE, in one place
        # Produces complete DecisionChain for every parameter
        # Manifest is frozen - no later mutation possible
```

4. **Command** (pure function signature):
```python
# Old: def callback(ctx: Context, verbose: bool) -> None
# New: def callback(manifest: Manifest) -> Result
# Access: manifest.verbose.value, manifest.verbose.explain()
```

**Visibility is maximized**: Every value has a complete decision chain. `manifest.verbose.explain()` returns: *"CLI argument `--verbose` at argv[2] overrode environment variable `MYAPP_VERBOSE=true` which overrode default `False`. Transform: string_to_bool applied."*

**Convenience is maximized**: The CLI author writes the same decorators. The builder handles all resolution. No manual inheritance traversal. No callback chains. Pure functions are easier to test than Context-dependent functions.

**Structural possibility proven**: Python's dataclasses, frozen=True, and functional patterns make this architecture straightforward. The key insight: resolve everything eagerly, record everything structurally, expose nothing lazily.

---

## Step 3: Name the New Trap

**New Conservation Law: Eager Resolution × Dynamic Configuration = constant**

The Manifest Architecture sacrifices the ability to:

1. **Late-bound defaults**: In Click, a `--config-file` option can specify a config file whose values become defaults for later options. In Manifest Architecture, all resolution happens before any option is processed.

2. **Context-dependent parameter resolution**: Click's callbacks can modify `ctx` before subcommands run. A global `--verbose` can change how subcommand options are interpreted.

3. **Incremental command construction**: Click's `Group.chain = True` allows multiple commands to run sequentially, each seeing state modified by predecessors.

**C × D = constant**: The more eagerly you resolve (all at entry), the less dynamic configuration you support. The more dynamic configuration you support (resolution throughout execution), the more eager resolution becomes impossible.

**Which trap is worse?**

| Criterion | Click's Trap (Convenience × Visibility) | Manifest's Trap (Eager × Dynamic) |
|-----------|----------------------------------------|-----------------------------------|
| Debugging | **Worse**: Where did this value come from? | Better: Full provenance |
| Dynamic CLIs | Better: Callbacks can modify context | **Worse**: Can't do late binding |
| Testing | Worse: Must construct Context hierarchy | Better: Pure functions, frozen input |
| Error messages | Worse: "Missing parameter" with no context | Better: Full decision chain available |
| Common case (static CLIs) | Same: Works fine | Same: Works fine |
| Edge case (config-driven) | Better: default_map chains | **Worse**: Requires redesign |

**Verdict**: Click's trap is worse for the 90% use case. Most CLIs don't need late-bound dynamic configuration. But when you DO need it, Click's architecture is the only option. The Manifest trap is worse for the 10% who need dynamic config.

**The deeper insight**: Both traps assume resolution must be either fully eager OR fully lazy. What if resolution could be *staged* with explicit phase boundaries?

---

## Step 4: The Design Space Map

**The Hidden Design Variable: Resolution Phase Count**

```
Phase Count = 1     ─────────────────────────────────────────►  Phase Count = N
(Manifest Arch)                                            (Click Arch)
     │                                                           │
     ▼                                                           ▼
All resolved at entry                                    Each parameter resolved
                                                         at access time
     │                                                           │
     ▼                                                           ▼
MAX visibility                                            MAX flexibility
MIN dynamic config                                        MIN visibility
```

**The space between**: Neither architecture acknowledges that resolution can be *phased* with explicit boundaries:

```
Phase 0: Parse argv structure (command path, raw options)
Phase 1: Resolve global options (verbose, config-file)
Phase 2: Load config file (dependent on Phase 1)
Phase 3: Resolve command options (dependent on Phase 2 config)
Phase 4: Execute command
```

At each phase boundary, a **PhaseComplete** event emits the resolution graph for that phase. Visibility is maintained (every phase is traceable) while dynamic configuration is supported (later phases depend on earlier phase results).

**The concrete design decision for Click:**

Add a **ResolutionRecorder** to Context that accumulates decisions WITHOUT changing when they're made:

```python
# In Context.__init__:
self._resolution_trace: ResolutionTrace = parent._resolution_trace if parent else ResolutionTrace()

# In Parameter.consume_value:
def consume_value(self, ctx, opts):
    value, source = self._resolve_value(ctx, opts)
    ctx._resolution_trace.record(
        param=self.name,
        value=value,
        source=source,
        candidates=self._get_candidates(ctx, opts),
        why=self._explain_choice(value, source, ctx)
    )
    return value, source

# New Context method:
def explain(self, param_name: str) -> str:
    return self._resolution_trace.explain(param_name)
```

**Impact**: 
- 3 lines added to `Context.__init__`
- 5 lines added to `Parameter.consume_value`
- 1 new class `ResolutionTrace` (~50 lines)
- 1 new method `Context.explain()`
- Zero changes to existing behavior

**Result**: Click retains its dynamic resolution (late binding, callbacks, context modification) but gains visibility into every decision. The user can call `ctx.explain('verbose')` and get: *"Resolved from ENVIRONMENT (MYAPP_VERBOSE=true) because no CLI argument provided. Default False was available but overridden."*

This moves Click **along the axis** toward the Manifest Architecture without requiring the jump to pure eager resolution. The conservation law becomes: **Resolution Phase Count × Debugging Effort = constant**. More phases = more to trace, but the trace is built-in.

---

**The Genesis conclusion**: Click's fundamental design decision was to make Context an inheritance-based, lazily-resolved, mutable state container. The alternative is a phased-resolution architecture with built-in provenance. The minimum-disruption path is to add a ResolutionRecorder that observes decisions without changing when they happen—gaining visibility without sacrificing dynamic behavior.
