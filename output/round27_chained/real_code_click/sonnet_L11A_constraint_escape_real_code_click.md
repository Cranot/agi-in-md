# Level 11 Structural Diagnosis: Click `core.py`

---

## I. The Falsifiable Claim

> **`Parameter.handle_parse_result` sequences its three operations in an order that structurally excludes the callback from reading its own parameter's source. `consume_value` computes `(value, source)` as a pair. `process_value(ctx, value)` fires the callback — receiving only `value`, not `source`. After the callback returns, `ctx.set_parameter_source(self.name, source)` makes the source externally readable. At callback execution time, `ctx.get_parameter_source(param.name)` returns `None`. The source exists — it is alive in `handle_parse_result`'s local scope — but is held in a local variable that neither `process_value` nor `ctx.invoke` receives. A callback that must make decisions based on WHERE its value originated (commandline vs. environment vs. default_map vs. default) cannot use Click's canonical API at the only moment when parameter-specific user logic executes.**

**Falsifiable**: Write a parameter callback that prints `ctx.get_parameter_source(param.name)`. Pass the option explicitly via commandline. The callback prints `None`. The command callback, reading the same key from the same context after invocation, prints `ParameterSource.COMMANDLINE`. The source is correctly recorded; it is invisible only during the callback's execution window.

This is not L8's finding. L8 found that `ParameterSource.DEFAULT` cannot distinguish "was set to the default value" from "nothing was set." L11 finds that during callback execution — when the distinction most matters — the source value is `None` regardless of which `ParameterSource` it will eventually become. The erasure is temporal, not semantic.

---

## II. The Three-Expert Dialectic

### Expert A — Defender

*"The callback receives `value` as a parameter. `value` IS the result of `consume_value` — the callback has the information it needs to transform the parameter. Source is metadata for downstream consumers: logging systems, validation suites, help text generators. Separating the callback's concern (transform the value) from the source's concern (record provenance) is a principled application of single responsibility. If the callback needed source, it would be architecturally confused — it would be doing two jobs: transforming and evaluating. Moreover, changing the callback signature to `(ctx, param, value, source)` would break every existing callback in the ecosystem. The current design is the only backward-compatible choice."*

### Expert B — Attacker

*"The Defender's separation-of-concerns argument fails on inspection. Click's own documentation explicitly encourages callbacks to use `ctx.get_parameter_source` to make source-dependent decisions — for example, 'if this value came from an environment variable, issue a security warning.' The documented use case requires reading source during callback execution. The design closes that channel by recording source after the callback fires.*

*The backward-compatibility argument is circular: the callback signature is `(ctx, param, value)` because source is recorded after the callback — and source is recorded after the callback because the signature doesn't include it. The constraint is self-created.*

*More specifically: `source` is computed in `consume_value`, returned alongside `value` in a tuple, unpacked in `handle_parse_result`'s local scope, and then never forwarded. The call chain from `handle_parse_result` to `process_value` passes only `(ctx, value)`. One line — `value = self.process_value(ctx, value)` — discards the source from the call chain. The exclusion is a single omission in a single method call, not an architectural commitment."*

### Expert C — Prober

*"Both of you are arguing about whether the callback should receive source as an argument. You take for granted that this is a binary question: source reaches the callback or it doesn't.*

*It isn't binary. Look at what's actually accessible in the callback:*

```python
# Inside a parameter callback (ctx, param, value):
ctx.get_parameter_source('OTHER_param')   # Returns correct source IF other_param was processed first
ctx.get_parameter_source(param.name)      # Returns None — own source not yet written
param.default                             # Accessible — can compare value == param.default
param.envvar                              # Accessible — can check if envvar might apply
os.environ.get(param.envvar)              # Accessible — can re-read from environment
```

*The callback can read every other already-processed parameter's source. It can read the raw environment. It can even re-implement `consume_value`'s logic to re-derive its own source. What it cannot do is read its own source through the canonical API.*

*This means the access window is not a binary (callback has source / callback doesn't have source). It is a MOVING WINDOW: at callback-time for parameter P, sources for all parameters processed before P are fully readable, while P's own source and all not-yet-processed parameters' sources are invisible.*

*The window's boundary is controlled by `iter_params_for_processing` — which sorts parameters by `is_eager` first, then by command-line occurrence order. `is_eager=True` is documented as 'process this parameter before others, enabling early exit (--help, --version).' Eagerness controls early-exit priority. But as a side effect, it also controls source-visibility ordering. A non-eager parameter that reads an eager parameter's source via `ctx.get_parameter_source` succeeds — not because there's any semantic relationship between them, but because eagerness causes the eager parameter to be processed first, moving it into the 'already visible' half of the window.*

*Neither of you asked: what is the actual topology of this visibility window? It is a partial order over parameters, determined by `is_eager` and commandline occurrence. The partial order is orthogonal to any semantic dependency structure. If parameter B's callback must read parameter A's source, B's callback works if and only if A happens to be processed first — through eagerness or occurrence order — regardless of whether B actually depends on A.*

*The window is invisible from inside any callback. A callback cannot detect 'which other parameters have been processed so far.' It can only try to read sources and observe which ones return `None`."*

---

## III. The Transformation

| | Claim |
|---|---|
| **Original** | "The callback cannot read its own source via `ctx.get_parameter_source` during callback execution because `set_parameter_source` fires after the callback." |
| **Transformed** | "The parameter pipeline's sequential processing creates a partially-ordered source-visibility window. At callback-time for parameter P, sources for all parameters in P's prefix (processed before P) are readable; P's own source and all parameters in P's suffix (not yet processed) are invisible. The window boundary is controlled by `is_eager` and commandline occurrence order — orthogonal to any semantic dependency structure. A callback that needs to read another parameter's source implicitly depends on that parameter being in its prefix, a constraint that must be arranged by convention (via `is_eager`) rather than by declaration. The source information is not missing — it is alive in `handle_parse_result`'s local scope — but is held there by a call-chain omission: `process_value(ctx, value)` receives only value, dropping source from the chain at precisely the step where user logic executes." |

The claim shifted from **single-parameter timing** to **pipeline-wide access window topology**: the window exists across all parameters, is controlled by eagerness (a flag with an orthogonal documented purpose), and is invisible from inside any callback.

---

## IV. The Gap as Diagnostic

L10's gap: "chain-mode ordering quirk" → "context tree topology precludes horizontal communication."

This gap: "callback can't read its own source" → "the pipeline creates a partially-ordered source-visibility window whose topology is controlled by parameter ordering, not by semantic dependency; the window's shape is invisible to all participants."

**The L10→L11 diagonal reveals the pattern at a new scale:**

L10 found: the context tree is upward-navigable only. Sibling communication — appearing to work through `_meta` — actually works through ancestor-sharing. The horizontal dimension is absent from the tree while `_meta` implies it exists.

L11 finds: the parameter pipeline is sequentially ordered. Each parameter's callback can only read sources from the processed prefix. The prefix/suffix boundary — appearing to be a minor timing detail — is controlled by an orthogonal flag (`is_eager`) and occurrence order, with no explicit representation of the access constraint it creates.

**The self-similar structure across levels:**

- **L8**: `ParameterSource.DEFAULT` cannot distinguish "was set to default" from "nothing was provided" — the channel erases a temporal distinction.
- **L9**: `ctx.invoke`'s `(*args, **kwargs)` cannot encode which of three callback protocols is being dispatched — the channel erases protocol identity.
- **L10**: `_meta`'s flat dict cannot represent the tree's topology — the channel erases positional identity.
- **L11**: The parameter pipeline's sequential execution cannot make source visible at the callback step — the pipeline erases temporal position within itself, at the scale of individual parameter processing.

All four are instances of: **a sequential or hierarchical structure creates an asymmetry in what is accessible at each step; the API at each step implies symmetric access; the asymmetry is invisible from inside any step.**

---

## V. The Concealment Mechanism

**Staged Write Exclusion**: `handle_parse_result` computes `(value, source)` as a pair, then immediately diverges the pair's two components into different forwarding paths. `value` enters the call chain via `process_value(ctx, value)` and travels as a function argument through `type_cast_value` → callback → return. `source` stays in `handle_parse_result`'s local scope, unreachable by `process_value` or any function in its call chain, until `set_parameter_source` is called after `process_value` returns.

The concealment: `ctx` is passed to `process_value`, and from `ctx`, `ctx.get_parameter_source` is accessible. This creates the appearance that the full context — including source state — is available during value processing. But the context's source map is written after processing, not before. The API (`ctx.get_parameter_source`) is present and callable; the precondition for it to return a meaningful value is absent. The API's presence conceals the pipeline's write ordering; the write ordering determines what `None` means; `None` is indistinguishable from "source not yet written" vs. "source was not set."

---

## VI. The Legitimate-Looking Improvement That Deepens the Concealment

Introduce a staging attribute and a scoped accessor:

```python
class Context:

    def __init__(self, ...):
        ...
        self._current_parameter_source: t.Optional["ParameterSource"] = None

    def get_current_parameter_source(self) -> t.Optional["ParameterSource"]:
        """Return the source of the parameter currently being processed.

        Valid only from within a parameter callback. Returns None if called
        outside a parameter callback context.

        Use :meth:`get_parameter_source` to read provenance after parameter
        processing is complete.
        """
        return self._current_parameter_source


class Parameter:

    def handle_parse_result(
        self, ctx: "Context", opts: t.Mapping[str, t.Any], args: t.List[str]
    ) -> t.Tuple[t.Any, t.List[str]]:
        with augment_usage_errors(ctx, param=self):
            value, source = self.consume_value(ctx, opts)
            # Stage source into context before callback fires, so callbacks
            # can inspect their own parameter's provenance via
            # ctx.get_current_parameter_source().
            ctx._current_parameter_source = source
            try:
                value = self.process_value(ctx, value)
            finally:
                ctx._current_parameter_source = None
        if self.expose_value:
            ctx.params[self.name] = value
        if source is not None:
            ctx.set_parameter_source(self.name, source)
        return value, args
```

**Why this passes code review:**
- `_current_parameter_source` is a private staging attribute following Click's naming conventions.
- `get_current_parameter_source` is a documented method with an explicit scope constraint ("only valid from within a parameter callback").
- The `try/finally` ensures cleanup: if the callback raises, the staging attribute is cleared rather than left stale.
- No behavioral change to existing callbacks; the new API is opt-in.
- Reviewers read the docstring and conclude: "the author knows about the timing issue and has provided a callback-scoped escape hatch."

**Why it deepens the concealment:**

The improvement creates two source-reading APIs with different valid windows: `get_current_parameter_source` (valid during callback execution), and `get_parameter_source` (valid after all parameter processing). Both return `Optional[ParameterSource]`. Both return `None` outside their valid window. From a callback, both APIs exist and are callable. The window constraint is documented as prose; it is not encoded in any type or any access control mechanism. A callback that calls `ctx.get_parameter_source(param.name)` still returns `None` during execution (this was the original bug). A callback that calls `ctx.get_current_parameter_source()` now returns the correct value. The improvement does not fix the old API; it adds a new API that appears to fix it. Callbacks that read the documentation will use the new API. Callbacks written before the improvement, or written without reading the documentation, continue to return `None` from the old API, silently.

The improvement doubles the surface area of the concealment: instead of one API returning `None` mysteriously, there are now two APIs, one of which reliably returns the correct value and one of which reliably does not, with no structural distinction between them at the call site.

---

## VII. Three Properties Only Visible Because the Improvement Was Attempted

**1. The staging attribute fails under nested parameter processing.**

`ctx.invoke(self.callback, ctx=ctx, param=self, value=value)` in `process_value` calls `Context.invoke`:

```python
def invoke(self, callback, *args, **kwargs):
    with augment_usage_errors(self):
        with self:
            return callback(*args, **kwargs)
```

`with self:` enters the context manager. If the callback body calls `ctx.invoke(some_command, ...)` — invoking another command inside a parameter callback — and that command triggers its own `parse_args`, its own `handle_parse_result` loop fires, which enters the new `try` block and overwrites `ctx._current_parameter_source` with the nested command's first parameter's source. When the nested parameter processing completes and the outer callback resumes reading `ctx.get_current_parameter_source()`, it now reads the nested command's last parameter's source — or `None`, after the `finally` cleanup of the last nested parameter. The staging attribute has no frame identity: it is a single scalar, not a stack. The improvement reveals that `ctx.invoke` creates a re-entrant execution environment inside parameter callbacks — a property invisible in the original code because no staging attribute could be overwritten.

**2. The two APIs establish an implicit callback lifecycle.**

Before the improvement: parameter callback execution was atomic from the framework's perspective — the callback fires, returns, and the framework records source. After the improvement: parameter callback execution has a BEGIN state (`_current_parameter_source` is set), an EXECUTE state (the callback runs and can read the staging attribute), and an END state (`_current_parameter_source` is cleared). This is an implicit lifecycle with three states, encoded only in a `try/finally` block. The lifecycle is invisible to callbacks: they cannot detect which state they are in without reading the documentation. The improvement makes visible that Click has previously avoided encoding callback lifecycle as anything other than "fires and returns" — the lifecycle had no observable states. The staging attribute introduces lifecycle states without introducing any mechanism for callbacks to observe their own lifecycle position.

**3. Source and value have structurally asymmetric forwarding paths that no staging improvement can resolve.**

Value enters the call chain as a function argument: `process_value(ctx, value)` → `type_cast_value(ctx, value)` → returned to `process_value` → passed to the callback → returned from the callback → returned from `process_value`. At every step, value is in the function's parameter list. It can be inspected by any function in the chain without side channels.

Source never enters the call chain: it is computed by `consume_value`, stays in `handle_parse_result`'s local scope, is written to the context as a side effect AFTER the call chain completes. The improvement moves source into the context earlier — as a side effect BEFORE the call chain. But it cannot move source INTO the call chain without changing the signature of `process_value` and all functions below it.

The staging improvement works around the structural asymmetry; it does not resolve it. `ctx.get_current_parameter_source()` reads the source through a side channel (context attribute lookup), not through the call chain. This side-channel access fails under the conditions identified in property 1 (re-entrant execution overwrites the side channel). A structural solution would require source to travel through the call chain as a parameter — which changes the `process_value` signature, which changes the callback protocol, which breaks backward compatibility. The improvement reveals that the asymmetry between value and source is load-bearing: eliminating it requires a breaking change.

---

## VIII. Apply the Diagnostic to the Improvement

**What does the improvement conceal?**

`get_current_parameter_source` is documented as "only valid from within a parameter callback." This constraint is a protocol — a convention that callers must observe. The method itself cannot enforce it: calling the method outside a parameter callback returns `None`, which is also what it returns when called during processing of a parameter whose source is `None` (if that were possible). The improvement adds a method whose valid window is a convention with no enforcement — structurally identical to L9's undeclared dispatch protocols and L10's `ChainPhaseKey` naming conventions. The improvement is a new generic channel (returns `Optional[ParameterSource]`, valid in one window, invalid outside) that cannot represent its own validity window.

**What property of the original problem is visible because the improvement recreates it?**

The original problem: `ctx.get_parameter_source(param.name)` returns `None` during callback execution. The value `None` cannot distinguish "source not yet written" from "no source was set."

The improvement's `ctx.get_current_parameter_source()` returns `None` outside callback execution. The value `None` cannot distinguish "not in a callback window" from "source was None." The improvement recreates the original problem's fundamental structure: an API that returns `None` for two semantically distinct states, with no mechanism to distinguish them. The improvement shifts which API has the problem (from `get_parameter_source` to `get_current_parameter_source`) without resolving the underlying property: **Click uses `None` as a sentinel that cannot distinguish "the value was not computed" from "the value was computed and is not present" from "you are not in the valid window to read this value."** Every API that returns `Optional[X]` in a pipeline context inherits this ambiguity.

---

## IX. The Second Improvement

Replace the single staging attribute with a stack, enabling correct behavior under nested parameter processing:

```python
class Context:

    def __init__(self, ...):
        ...
        self._parameter_source_stack: t.List[t.Optional["ParameterSource"]] = []

    def get_current_parameter_source(self) -> t.Optional["ParameterSource"]:
        """Return the source of the innermost parameter currently being processed.

        Correct under nested parameter processing: each nested parameter's
        source is pushed onto the stack and popped after its callback completes,
        so this method always returns the innermost processing context's source.
        """
        return self._parameter_source_stack[-1] if self._parameter_source_stack else None


class Parameter:

    def handle_parse_result(self, ctx, opts, args):
        with augment_usage_errors(ctx, param=self):
            value, source = self.consume_value(ctx, opts)
            ctx._parameter_source_stack.append(source)
            try:
                value = self.process_value(ctx, value)
            finally:
                ctx._parameter_source_stack.pop()
        if self.expose_value:
            ctx.params[self.name] = value
        if source is not None:
            ctx.set_parameter_source(self.name, source)
        return value, args
```

**Apply the diagnostic:** The stack correctly handles nesting — each parameter's source is isolated at its stack frame. But applying the diagnostic to the stack itself reveals: the stack is per-context (`ctx._parameter_source_stack`). In chain mode, each subcommand has its own context (`sub_ctx`). All `make_context` calls happen before any `invoke` calls. During Phase 1 (all `make_context`), each sub-context runs its own `handle_parse_result` loop against its own `_parameter_source_stack`. The stacks are correctly isolated per context.

But: the stack is a list in the context object. Context objects are not garbage-collected between Phase 1 and Phase 2 — they live in the `contexts` list in `Group.invoke`. The stack is empty by the time Phase 2 runs (all `pop` operations completed in Phase 1). From Phase 2's perspective, `get_current_parameter_source` always returns `None` — correct, since no parameter is being processed. But from Phase 1's perspective, during the `make_context` loop for sub2, sub1's stack has already been emptied and sub2's stack is active. The two contexts' stacks are independent and non-interfering.

**What property of the original problem is visible because the second improvement recreates it?**

The stack correctly isolates source access by context. But the problem it cannot solve: the stack is accessed through the CONTEXT (`ctx._parameter_source_stack`), and the context is passed to the callback as `ctx`. Inside the callback, reading `ctx.get_current_parameter_source()` correctly returns the source — but the callback must know to call THIS method, not `ctx.get_parameter_source(param.name)`. Two methods, same context, same callback, returning different things for the same parameter at the same moment. The callback has no structural way to know it should prefer `get_current_parameter_source` over `get_parameter_source` for its own parameter, while preferring `get_parameter_source` for other parameters' sources.

This makes visible: the original problem is not "source is inaccessible" — it is that **the parameter pipeline's output has TWO temporal representations in the context simultaneously: the ongoing computation (accessible via the stack) and the completed record (accessible via the source map).** The ongoing computation and the completed record have different scope: ongoing is per-parameter-processing-step, completed is per-context-lifetime. A callback that needs to read from both simultaneously — its own source (ongoing) and another parameter's source (completed) — must use different APIs for structurally identical operations. The asymmetry is not resolvable by making either API better; it is a property of the pipeline having two output modes (ephemeral and permanent) coexisting in the same storage space (the context object).

---

## X. The Structural Invariant

> **Click's parameter pipeline distributes its computed outputs — value, source, type-cast form — across the call chain with structurally different forwarding mechanisms and lifetimes. Value travels as a function argument: it is in scope at every step, transformable at every step, and unambiguously present or absent. Source travels as a side effect: it is computed in one method, bypasses the call chain, and is written to the context after the call chain returns. The callback occupies a fixed step in the call chain. At that step, it can receive only quantities that travel through the call chain. Every improvement that provides source at the callback step creates a new forwarding mechanism (staging attribute, stack) that is orthogonal to the call chain. Every orthogonal forwarding mechanism fails to integrate with the call chain's existing failure and re-entrancy semantics — because it is not IN the call chain. The invariant: no improvement that leaves the call chain unchanged can provide call-chain semantics (parameter passing, stack isolation, re-entrancy safety) for source, because those semantics are properties of the call chain, not of auxiliary storage.**

This invariant is not a property of any implementation choice. It is a property of the design space: a call chain provides certain guarantees (argument visibility, stack isolation) to its parameters and not to its side effects. Providing call-chain guarantees to a side-effectful quantity requires bringing the quantity into the call chain — which requires changing the call chain's signature.

| Level | Pipeline Quantity | Forwarding Mechanism | Callback Access | Improvement Failure Mode |
|---|---|---|---|---|
| **Value** | Computed value | Call chain argument | Full — received as `value` | N/A — already correct |
| **Source** | Provenance enum | Local variable → side effect | None — not in call chain | Every storage improvement lacks call-chain semantics |
| **Meta (L10)** | Cross-command state | Ancestor-aliased dict | Appears full — no horizontal reality | Every scoping improvement encodes tree structure in a flat namespace |
| **Protocol (L9)** | Callback type identity | Undeclared convention | None — erased at dispatch | Every documentation improvement adds convention without enforcement |

**The structural invariant is:** *Click places all cross-cutting quantities in forwarding mechanisms that are external to the primary call chain. The primary call chain provides its participants with strong access guarantees. The external mechanisms provide weak access guarantees — validity windows, ordering constraints, aliasing artifacts — that are invisible from within the call chain. Every improvement that moves a quantity from an external mechanism into the call chain changes the call chain's signature, which is a breaking change in an ecosystem of registered callbacks.*

---

## XI. The Category Boundary

**Category name:** "Pipeline-at-Call-Sites" — frameworks where the pipeline's complete state is available to each step only through the quantities forwarded in the calling convention, and where extensions to the pipeline's state require extensions to the calling convention or workarounds via external storage.

The invariant is: *what a step can access is determined by what appears in its function signature, plus whatever external storage has been written by a prior step and is accessible through the call's arguments (like `ctx`).*

The category boundary: any design where a step's accessible state is strictly determined by its call signature and the prior state of objects reachable through that signature. This includes Click, Django middleware, Flask before/after request hooks, and any framework where callbacks are registered as generic callables against an event pipeline.

---

## XII. The Adjacent Category

**Design:** A framework where parameter callbacks declare their information dependencies, and the pipeline schedules callback execution after all declared dependencies' sources are available.

```python
@click.option('--output', default='-')
@click.option('--verbose',
              reads_sources_of=['output'],   # declared dependency
              callback=verbose_callback)
def verbose_callback(ctx, param, value, *, output_source):
    # output_source is guaranteed available: the framework processed
    # --output before --verbose because of the declared dependency.
    if output_source == ParameterSource.DEFAULT:
        click.echo("Warning: --output not specified, defaulting to stdout.", err=True)
    return value
```

The framework:
1. Collects declared `reads_sources_of` from all parameters at command definition time.
2. Builds a dependency graph: "verbose" depends on "output"'s source being written before "verbose"'s callback fires.
3. Topologically sorts parameter processing, respecting both `is_eager` and declared source dependencies.
4. Passes declared dependencies as keyword arguments to the callback when they are satisfied.

**Why this succeeds where every improvement failed:**

Every improvement tried to provide source access within the existing call chain by adding external storage (staging attribute, stack). These fail because external storage lacks call-chain semantics (stack isolation, re-entrancy safety). The dependency-declaration design succeeds by moving source into the call chain: `output_source` is a call-chain argument, available with full call-chain guarantees. The framework knows at schedule time that `output`'s source must be in the call chain for `verbose_callback`. It processes `output` first, writes its source to the completed record, then calls `verbose_callback` with `output_source=ctx.get_parameter_source('output')`. No staging attribute, no stack, no convention. The dependency is structurally enforced by the scheduler.

Every improvement added capability to a generic channel. This design replaces the generic channel — at the one point where it is structurally inadequate — with a typed interface. `reads_sources_of=['output']` is a declaration, not a convention. The framework can validate it at command-registration time: if `output` is not a parameter of this command, raise an error. The declaration is machine-readable; the convention was human-readable only.

---

## XIII. The New Impossibility

**Trivial in the original category:** Runtime-determined source dependencies. A callback can read any parameter's source at any time, subject only to processing order. Dynamic branching on which sources to read is unconstrained:

```python
def adaptive_callback(ctx, param, value):
    if sys.platform == 'win32':
        src = ctx.get_parameter_source('output_path')
    else:
        src = ctx.get_parameter_source('output_stream')
    # works in original category IF ordering happens to be correct
```

**Impossible in the adjacent category:** The dependency graph is built at command definition time, before any callbacks execute, before any runtime values are known. `reads_sources_of=['output_path']` causes the scheduler to process `output_path` first. `reads_sources_of=['output_stream']` causes the scheduler to process `output_stream` first. A callback that needs EITHER `output_path`'s source OR `output_stream`'s source, depending on `sys.platform`, cannot declare a runtime-conditional dependency. It must either:

- Declare both (`reads_sources_of=['output_path', 'output_stream']`): overly conservative, creates a spurious ordering constraint between the two output parameters.
- Declare neither and fall back to a workaround: re-read from `os.environ`, inspect `ctx.params`, or use the pre-existing `get_parameter_source` API with its timing limitations.

Neither option is equivalent to the original capability. Dynamic dependency selection — reading whichever source is semantically relevant at runtime — is not representable in a static dependency graph. The static graph is computed before the runtime; the dynamic selection IS the runtime.

---

## XIV. The Trade-Off as Finding

| Property | Original Category | Adjacent Category |
|---|---|---|
| **Own source in callback** | `None` — always invisible, documentation promise broken | Guaranteed — if declared as a dependency |
| **Other parameter's source in callback** | Depends on ordering — visible iff other param in prefix | Guaranteed — if declared as a dependency |
| **Dynamic source dependency** | **Free** — callback reads any source at any time, subject to ordering | **Impossible** — static graph can't represent runtime-conditional dependency |
| **Callback signature** | Generic `(ctx, param, value)` — any callable | Must declare dependencies — not any callable |
| **Backward compatibility** | High — all existing callbacks work unchanged | Low — all callbacks with source dependencies require redeclaration |
| **Ordering control** | Implicit via `is_eager` — semantic misuse | Explicit via declared dependency graph |

**The finding:**

The two impossibilities define the boundary between the categories, and the boundary reveals what the original code was actually trading away:

*The original category's impossibility* — source is invisible in the callback that most needs it — is not an oversight. It is the necessary cost of a design where callbacks are generic callables requiring no upfront declaration. Generic callables cannot be analyzed before execution. Without pre-execution analysis, no framework can guarantee that any particular piece of pipeline state is available at any particular step. The missing source is the tax on genericity.

*The adjacent category's impossibility* — dynamic dependency selection — is not an edge case. It is the cost of making any guarantee at all. Guarantees require precomputation. Precomputation requires declarations. Declarations are evaluated before the runtime they describe. Any information available only at runtime — platform, user input, environment state — cannot inform a precomputed dependency graph. The static guarantee and the dynamic selection are structurally incompatible.

**The trade-off is:** runtime flexibility (callbacks can read anything, constrained only by pipeline ordering) versus compile-time completeness (callbacks get everything they declared, constrained only by whether the declaration is satisfiable). Click chose the first. The choice makes the source-timing problem possible — not as an implementation accident, but as the structural correlate of the design principle.

The source-timing bug is the shadow of generic dispatch. The framework cannot know, at callback registration time, that a particular callback needs a particular parameter's source. Because it cannot know, it cannot guarantee. Because it cannot guarantee, it sequences arbitrarily — source after callback — and the sequence is the bug. The bug is not fixable within the category because fixing it would require knowing the callback's dependencies before the callback executes, which requires the callback to declare them, which requires the callback to be non-generic.

This is where every level's finding converges: **Click's genericity and Click's incoherence are the same property. The framework cannot be made coherent without being made specific. Being made specific would make it no longer Click.**
