# Level 11 Structural Diagnosis: Click `core.py`

---

## I. The Falsifiable Claim

> **In `handle_parse_result`, `ctx.set_parameter_source(self.name, source)` is called AFTER `self.process_value(ctx, value)`, which fires the parameter callback. The callback lives in the gap between `consume_value` knowing the winning source and `handle_parse_result` announcing it to `ctx`. During the callback's execution window, `ctx.get_parameter_source(param.name)` returns `None` — the source exists in `handle_parse_result`'s local scope but has not yet been written to `ctx._parameter_source`. The parameter callback is the only consumer of parameter state that simultaneously (a) can modify the parameter's final value and (b) cannot access the parameter's provenance via the standard API. These two properties — modifiability and provenance blindness — co-locate in exactly the callback window.**

**Falsifiable**: Define `@click.option('--x', envvar='X_VAR', callback=cb)` where `cb` calls `ctx.get_parameter_source(param.name)`. Invoke with `X_VAR=hello` and no commandline value. `cb` will see `value='hello'` but receive `ctx.get_parameter_source('x') == None`, not `ParameterSource.ENVIRONMENT`. Invoke the same command from a command callback (which runs after all `handle_parse_result` calls complete) and `ctx.get_parameter_source('x')` correctly returns `ParameterSource.ENVIRONMENT`. The same method on the same context returns different values depending on which callback type calls it. No documentation, no warning, no error.

---

## II. The Three-Expert Dialectic

### Expert A — Defender
*"The callback is for value transformation — validation, normalization, side effects. It receives `(ctx, param, value)`: everything it needs. If a callback needs to distinguish commandline from environment, it should inspect `os.environ` or compare against `param.default`. `ctx.get_parameter_source` is a post-processing query API designed for command callbacks implementing provenance-based policies. The parameter callback is the manufacturing floor; source tracking belongs to the shipping department. The design is correct: the callback transforms the value; `handle_parse_result` records the metadata."*

### Expert B — Attacker
*"Expert A's 'check os.environ directly' advice is wrong in two independent ways. First: Click's env var resolution handles `auto_envvar_prefix` construction, multiple envvar names per parameter, and `token_normalize_func` normalization. A callback that re-implements env var checking duplicates logic that can diverge from Click's behavior. Second: `ctx.get_parameter_source` EXISTS as a documented method on the Context object that is passed to every callback. The documentation says it returns the ParameterSource. Not 'returns the ParameterSource after processing.' Not 'returns None from parameter callbacks.' The method always returns a value — it's just wrong for a specific caller class. This is not a design decision; it is an implementation accident. The fix: one line, move `ctx.set_parameter_source` to before `process_value`. This is trivially correct."*

### Expert C — Prober
*"Both of you are arguing about the fix. Let me ask what you both take for granted: that `process_value` could be made aware of `source` if we wanted it to be.*

*Look at `process_value`'s signature: `process_value(self, ctx, value)`. Source is not in the interface. `consume_value` returns `(value, source)`. `handle_parse_result` calls `process_value(ctx, value)` — source is silently dropped at the call boundary. The callback is invoked inside `process_value`. It has no access to `source` through `process_value`'s interface because `process_value` doesn't receive `source`.*

*Why doesn't `process_value` receive `source`? Because `process_value` is designed as a generic value transformer: given a value, produce a (possibly transformed) value. Receiving source would make it a provenance-aware value transformer. That's a different abstraction. The callback's provenance blindness is not a timing accident — it is the inherited cost of `process_value`'s genericity.*

*Expert B says: 'one line, move the write earlier.' This makes `ctx.get_parameter_source` return a non-None value in the callback. But what value? For a parameter with no commandline arg, no env var, and no configured default — the common case for optional parameters — `consume_value`'s first line sets `source = ParameterSource.DEFAULT` before checking env or default_map. If no source provides a value, this initial `DEFAULT` assignment is the one that survives. The callback now gets `ParameterSource.DEFAULT` for a parameter that has no configured default and will become `None` via `parse_args`'s UNSET→None sweep. Expert B replaced a conspicuously wrong `None` with a plausible wrong `DEFAULT`. That is not a fix; it is concealment.*

*What neither of you asked: why is `process_value` called from exactly one place in this codebase — `handle_parse_result` — if its generic interface exists for reusability? It doesn't exist for reusability. The generic interface exists to separate 'value logic' from 'metadata logic.' The separation is an architectural decision, not a reuse decision. Its cost is that `source` must live in `handle_parse_result`'s scope, outside `process_value`, and the callback — called from inside `process_value` — cannot access it without either threading it through `process_value`'s interface (breaking the separation) or writing it to `ctx` before `process_value` returns (the premature write)."*

---

## III. The Transformation

| | Claim |
|---|---|
| **Original** | "`ctx.get_parameter_source` returns `None` from a parameter callback because `set_parameter_source` is called after `process_value`." |
| **Transformed** | "The callback window is a structural information minimum in the parameter pipeline. `process_value`'s generic interface (`ctx, value`) excludes provenance from the value-transformation contract. The callback, called from within `process_value`, inherits this exclusion. `ctx.get_parameter_source` appears to restore what `process_value` excluded — provenance via context side-channel — but requires that `handle_parse_result` write provenance before calling `process_value`. Click does not do this. Moving the write earlier (the obvious fix) creates ghost sources when `type_cast_value` raises; threading `source` through `process_value` eliminates the architectural separation that motivated `process_value`'s design. The information gap between knowing-the-winner and announcing-the-winner is maintained by the interface boundary between `handle_parse_result` and `process_value` — not by a misplaced line." |

The claim shifted from **implementation ordering** to **pipeline architecture**: `process_value`'s generic interface is the source of the problem; the callback's blindness is its inherited cost; no write position for `set_parameter_source` satisfies both "no ghost sources" and "source visible in callback" simultaneously.

---

## IV. The Gap as Diagnostic

L10's gap: "chain-mode ordering quirk" → "context tree topology precludes horizontal communication; `_meta` ancestor-aliasing masquerades as peer-sharing."

L11's gap: "API ordering bug" → "`process_value`'s generic interface creates an information gap between knowing and announcing the resolution winner; the callback window coincides exactly with this gap."

**The self-similar structure across scales:**

| Level | Structure | Missing Property | Apparent Workaround | Workaround's Failure |
|---|---|---|---|---|
| **L8** | `ParameterSource` enum | Distinguishes DEFAULT-as-default from DEFAULT-as-absent | Add `ABSENT` value | Requires detecting "no source found" in a function that pre-labels `DEFAULT` before checking |
| **L9** | `ctx.invoke` dispatch | Callback type identity | Document protocol at call sites | Convention, no enforcement |
| **L10** | Context tree | Horizontal sibling edges | `_meta` aliased across tree | Ancestor-aliased, not peer-shared; chain mode exposes the topology |
| **L11** | Parameter pipeline | Provenance at callback stage | `ctx.get_parameter_source` | Written after callback fires; returns wrong data in callback window |

L10 found: the context tree's structural absence (no sibling pointers) is concealed by `_meta`'s appearance of horizontal access.

L11 finds: the parameter pipeline's temporal gap (source known but not yet announced) is concealed by `ctx.get_parameter_source`'s appearance of complete API availability. The gap operates at a finer grain: not between parse-phase and execute-phase (L10's scale), but within a single parameter's processing — between `consume_value` and the post-`process_value` write.

**The diagonal**: L10 is topological (the tree lacks edges). L11 is temporal (the pipeline has a gap). Both manifest as: an API that implies symmetric access implements asymmetric access in exactly the dimension the use case requires. The self-similarity is structural, not coincidental.

---

## V. The Concealment Mechanism

**Temporal Tunneling**: `source` is a local variable in `handle_parse_result`. It exists from `consume_value`'s return through `ctx.set_parameter_source`'s call — the entire body of `handle_parse_result`. During this interval, `source` is available to `handle_parse_result` but not to any code running inside `process_value`. The callback fires during this interval, inside `process_value`, below the scope boundary. `ctx.get_parameter_source` is the standard access path to source information; it reads from `ctx._parameter_source`, which is only populated after `process_value` returns. The method is always callable, always returns a Python object (None or a ParameterSource), and carries no documentation marking the callback window as an incorrect-return window.

This differs from L10's Topological Aliasing in kind. L10's concealment hid the **permanent structural absence** of horizontal edges: `_meta` appeared to provide what the tree cannot structurally have. L11's concealment hides a **transient temporal unavailability**: `ctx.get_parameter_source` will provide the correct answer — just not yet. The source is coming. The mechanism conceals not that the structure lacks a property, but that a property the structure will have has not been acquired at this moment.

The concealment is self-reinforcing: `ctx` is always passed to the callback; `ctx.get_parameter_source` is always on the object; the return value `None` is a valid Python value that blends into unset-state handling. A developer who sees `None` and wonders "was the parameter set?" will investigate `ParameterSource`, find four values, and not find any documentation of a fifth temporal state ("source not yet recorded").

---

## VI. The Legitimate-Looking Improvement

Move `ctx.set_parameter_source` to before `process_value`, with explanatory documentation:

```python
class Parameter:

    def handle_parse_result(
        self,
        ctx: "Context",
        opts: t.Mapping[str, t.Any],
        args: t.List[str],
    ) -> t.Tuple[t.Any, t.List[str]]:
        """Resolve, validate, and record a parameter's value.

        The parameter source is recorded before the callback fires, making it
        available via ``ctx.get_parameter_source(param.name)`` during callback
        execution. Callbacks that override a value may call
        ``ctx.set_parameter_source`` to update the recorded source accordingly.
        """
        with augment_usage_errors(ctx, param=self):
            value, source = self.consume_value(ctx, opts)

            # Record source before process_value so callbacks can read it via
            # ctx.get_parameter_source. This is safe because source is
            # determined by consume_value and does not change during processing.
            if source is not None:
                ctx.set_parameter_source(self.name, source)

            value = self.process_value(ctx, value)

        if self.expose_value:
            ctx.params[self.name] = value

        return value, args
```

**Why this passes code review:**
- Addresses a real, testable discrepancy: `ctx.get_parameter_source` returned `None` in callbacks; now it returns the correct value
- Minimal change (three lines moved, one added)
- The comment explains the rationale and documents an escape hatch for edge cases
- `set_parameter_source` is idempotent in practice; existing code that doesn't call `get_parameter_source` from callbacks is unaffected
- The docstring disclosure appears thorough

**Why it deepens the concealment:**

The improvement replaces a conspicuously wrong answer (`None`) with a superficially correct wrong answer (`ParameterSource.DEFAULT`). For parameters with no configured default and no commandline/env/default_map value — which is the common case for optional parameters — `consume_value`'s first line sets `source = ParameterSource.DEFAULT` before checking env vars or defaults. If no source provides a value, this pre-label survives unchanged. A callback that now reads `ParameterSource.DEFAULT` concludes "this parameter got its configured default value" and handles it accordingly. But the parameter has no configured default; its value is UNSET and will become `None` only after `parse_args` completes its post-processing sweep.

Before the improvement: `None` is conspicuously wrong, may prompt investigation, may surface L8.
After the improvement: `DEFAULT` is superficially correct, discourages investigation, conceals L8's ambiguity behind a legitimate-looking ParameterSource value. The improvement actively widens L8's attack surface by bringing parameter callbacks into contact with `DEFAULT`'s dual semantics, while hiding L8's ambiguity behind a now-working API call.

---

## VII. Three Properties Visible Only Because the Improvement Was Attempted

**1. Source and value now have independent lifecycles — source is frozen at resolution, value is mutable through the callback.**

After the improvement, `ctx.set_parameter_source(name, source)` is called before `process_value`. If the callback receives `value=5` (commandline, source=COMMANDLINE) and returns `value=100` — a business-logic transformation — `ctx.params[name] = 100` and `ctx._parameter_source[name] = COMMANDLINE`. A command callback reading `ctx.params['x']` gets `100`; reading `ctx.get_parameter_source('x')` gets `COMMANDLINE`. The source accurately tracks where the raw value came from; it does not track where the final value came from. Source and value now have independent provenance. Before the improvement, the callback couldn't read source at all, so this divergence was invisible. The improvement makes it observable: the parameter callback is the only transformation point in the pipeline, and its transforms are not reflected in source tracking.

**2. Source is recorded before `type_cast_value` runs — ghost sources appear when type conversion fails.**

`process_value` calls `type_cast_value` before invoking the callback. In the improved code: source is recorded → `type_cast_value` runs → if conversion raises `BadParameter`, execution exits `process_value` → `ctx.params[name]` is never set → the exception propagates. At this point, `ctx._parameter_source[name]` holds a valid ParameterSource for a parameter whose value was never successfully resolved. `ctx.get_parameter_source('x')` returns `COMMANDLINE` while `ctx.params` has no entry for `x`. The original code avoided this by writing source only after processing succeeded. The improvement creates a window — after source-write, before successful processing — where source tracking is inconsistent with parameter resolution.

**3. The improvement's comment creates a new undeclared protocol in the same channel.**

`"Callbacks that override a value may call ctx.set_parameter_source to update the recorded source accordingly."` This adds a convention: parameter callbacks that transform values should update the source. The convention has no enforcement (no validation), no type marker (any ParameterSource value is accepted), and no signal distinguishing "I updated the source intentionally" from "I forgot to update the source." The convention coexists with every existing callback that does NOT update the source — they all become implicitly non-compliant with the new convention, silently. This is structurally identical to L9's undeclared callback protocol convention and L10's `_meta` usage convention: a new protocol added to a generic channel that the channel cannot enforce. The improvement recreates Click's organizing invariant — conventions without enforcement — at the parameter callback level.

---

## VIII. The Improvement Applied Diagnostically

**What the improvement conceals:**

The improvement makes `ctx.get_parameter_source` available in callbacks, suggesting that provenance is now fully accessible. This conceals that the callback still cannot access the values of sources that LOST the resolution waterfall. A callback receiving `(source=COMMANDLINE, value=5)` has no way to know what the environment variable said, whether it was defined, or what the default_map would have returned — because `consume_value`'s waterfall terminated at the commandline source and discarded the rest. The improvement makes the WINNING source visible while leaving the losing sources as inaccessible as before.

**What property of the original problem is visible because the improvement recreates it:**

The improvement's ghost-source problem (property #2) reveals the original problem's structural core: `source` and `value` should be co-written atomically, because they represent two properties of the same resolved state. Writing them at different times (source before `process_value`, value after) creates windows of inconsistency. The original code's "write both after processing" was the correct atomicity choice; the improvement broke it. This makes visible: the original ordering is not an accident but a structural requirement for consistency — specifically, the requirement that `ctx._parameter_source[name]` and `ctx.params[name]` are always simultaneously present or simultaneously absent.

---

## IX. The Second Improvement

The ghost source problem requires that source and value be written together. The only way to provide source to the callback AND write both source and value atomically after processing is to thread `source` through `process_value`:

```python
class Parameter:

    def process_value(
        self,
        ctx: "Context",
        value: t.Any,
        source: t.Optional["ParameterSource"] = None,
    ) -> t.Any:
        """Transform and validate a resolved parameter value.

        ``source`` is threaded through so callbacks may inspect provenance
        via ``ctx.get_parameter_source`` without requiring premature writes
        to the context's source tracking.
        """
        value = self.type_cast_value(ctx, value)

        if self.required and self.value_is_missing(value):
            raise MissingParameter(ctx=ctx, param=self)

        if self.callback is not None and not ctx.resilient_parsing:
            # Temporarily expose source via ctx for callback access.
            # Removed after callback; handle_parse_result writes the final value.
            _prior = ctx._parameter_source.pop(self.name, _UNSET)
            if source is not None:
                ctx._parameter_source[self.name] = source
            try:
                value = ctx.invoke(self.callback, ctx=ctx, param=self, value=value)
            finally:
                # Restore prior state; handle_parse_result will record final source.
                if _prior is _UNSET:
                    ctx._parameter_source.pop(self.name, None)
                else:
                    ctx._parameter_source[self.name] = _prior

        return value


    def handle_parse_result(self, ctx, opts, args):
        with augment_usage_errors(ctx, param=self):
            value, source = self.consume_value(ctx, opts)
            value = self.process_value(ctx, value, source=source)

        if self.expose_value:
            ctx.params[self.name] = value
        if source is not None:
            ctx.set_parameter_source(self.name, source)
        return value, args
```

**Apply the diagnostic:**

This improvement threads `source` through `process_value` and temporarily exposes it during the callback via `ctx._parameter_source`, then removes it. It avoids ghost sources (the final write happens after processing, atomically with `ctx.params`). But it reveals: `process_value` is now a stateful object that temporarily mutates `ctx._parameter_source` and restores it in a `finally` block. It's a parameter-scoped transaction over the same shared dict that L10 identified as the ancestor-aliased cross-command channel. The "temporary write, restore on exit" pattern transforms the simple dict mutation into a savepoint-based access pattern — in a dict that has no savepoint semantics.

**What property of the original problem is visible because the second improvement recreates it:**

Threading `source` through `process_value` reveals that `process_value` is called from exactly one place: `handle_parse_result`. There are no other callers in the codebase. The "generic interface" that excluded `source` was not designed for reusability — `process_value` is not reused. It was designed for SEPARATION: value logic here, metadata logic there. The separation's entire cost — the callback's provenance blindness — was paid to maintain an architectural boundary between two functions that only communicate in one direction. The improvement makes this visible by attempting to close the boundary: threading `source` through immediately transforms `process_value` from "generic value transformer" to "provenance-aware value transformer with ctx mutation." The boundary collapses, and with it the last structural justification for keeping source out of `process_value`'s interface.

---

## X. The Structural Invariant

> **The parameter resolution pipeline is partitioned into a value-transformation zone (`process_value` and its callback) and a metadata-management zone (`handle_parse_result`'s outer scope). This partition is enforced by `process_value`'s interface, which receives `(ctx, value)` and excludes provenance. The callback, embedded in the value-transformation zone, inherits the zone's interface contract: it operates on values without provenance. `ctx` is present in the callback as a cross-cutting reference — it leaks metadata-zone information into the value-transformation zone — but only carries information that has already been written to it. `source` is not written to `ctx` until `handle_parse_result`'s metadata-management code runs, which is after `process_value` returns. Every improvement that attempts to give the callback access to `source` either (a) moves the write earlier, creating ghost sources when `type_cast_value` raises and decoupling source tracking from successful value resolution; (b) threads `source` through `process_value`'s interface, collapsing the partition that was the invariant's structural basis; or (c) uses temporary `ctx` mutations with savepoint semantics that the shared dict cannot enforce. No improvement satisfies all three constraints simultaneously: atomic source-value writes, source availability in callback, `process_value` interface stability. The invariant is the mutual exclusivity of these three constraints.**

---

## XI. The Inversion and the Conservation Law

**Invert the invariant**: design a pipeline where the callback is the information maximum — it receives not just the winning source and value, but the full resolution trace: all sources that were consulted, their raw values, and which ones were discarded:

```python
@dataclass
class ResolutionTrace:
    commandline_value: t.Any      # UNSET if not on commandline
    env_value: t.Any              # UNSET if env var not defined  
    default_map_value: t.Any      # UNSET if not in default_map
    default_value: t.Any          # UNSET if no default configured
    winning_source: ParameterSource
    winning_value: t.Any

def consume_value_full(self, ctx, opts) -> ResolutionTrace:
    """Evaluate ALL sources regardless of priority."""
    return ResolutionTrace(
        commandline_value=opts.get(self.name, UNSET),
        env_value=self.value_from_envvar(ctx),         # ALWAYS evaluated
        default_map_value=ctx.lookup_default(self.name), # ALWAYS evaluated  
        default_value=self.get_default(ctx),            # ALWAYS evaluated
        ...
    )
```

**The new impossibility:**

Evaluating all sources regardless of priority:

1. **Callable defaults run unconditionally.** A parameter defined as `default=lambda ctx: load_from_database(ctx)` now queries the database on every invocation, even when the commandline provides the value. Click's waterfall exists precisely because callable defaults may be expensive or have side effects. The inverted design assumes source evaluators are cheap and side-effect-free — a constraint that Click's interface for callable defaults does not enforce and cannot enforce.

2. **Env var readers run unconditionally.** For a group with 20 parameters each using `auto_envvar_prefix`, the inverted design performs 20 env lookups per invocation even when all 20 values are provided on the commandline. The original design performs 0. More critically: some production systems implement env var access through audit-logging middleware (security, compliance). The inverted design would trigger audit events for env vars the program neither needed nor used.

3. **The `ResolutionTrace` must record "not defined" vs. "defined but empty" for env vars.** `value_from_envvar` as currently implemented collapses "env var not defined" and "env var defined but empty (for non-string params)" to the same return: `None`. The full trace can only distinguish them by checking `os.environ` directly, re-implementing the normalization logic, and potentially diverging from Click's behavior on edge cases.

**The Conservation Law:**

**The Resolution Terminus Law**: *In a waterfall priority pipeline, the callback fires at the resolution terminus — the moment after the winning source is determined and before the winning source is announced to any external store. At this moment, the pipeline has discarded all non-winning candidates. The information available to a callback at the terminus equals: the winning value, the winning source. The information unavailable equals: the values of all candidates that were discarded to reach the terminus. Providing the callback with the discarded candidates requires evaluating them before the waterfall terminates — which transforms the waterfall into a full eager evaluation. The candidates' values and the efficiency of the waterfall's early termination are conserved: gaining one costs the other.*

Formally: **`full_candidate_observability + waterfall_early_termination_efficiency = constant`**. Every design decision moves along this constraint curve. Click chose maximum efficiency (stop at first winner) and minimum candidate observability. The inverted design chose maximum candidate observability and zero efficiency advantage from early termination.

**The diagonal with L10:**

L10's conservation law (implicit): **Genericity ↔ Enforceability**. Generic channels enable extensibility at the cost of unenforceability of cross-cutting invariants. L10's problem is a carrier problem: the channels don't carry the structural properties needed for enforcement.

L11's conservation law: **Early Termination Efficiency ↔ Candidate Observability**. Waterfall pipelines discard non-winning candidates for efficiency; discarding them makes them unobservable. L11's problem is a production problem: the information was never computed, so there is nothing to carry.

These are orthogonal laws:

- A lazy but typed pipeline (typed channels, waterfall resolution): has L11's problem (non-winning candidates unobservable) but not L10's problem (the typed channels enforce what they carry).
- An eager but generic pipeline (generic channels, full evaluation): has L10's problem (unenforceability) but not L11's problem (all candidates observed).
- Click's pipeline is both lazy AND generic, inheriting both problems.

**The diagonal's key finding**: L10 observed that Click's channels do not carry the information needed for cross-cutting policies. L11 identifies why they cannot carry it: for non-winning sources, the information was never produced. L10's carrier problem could be addressed by enriching what the channels carry. L11's production problem cannot be addressed by enriching channels — there is nothing to put in them. The information does not exist to be carried.

**What a senior engineer would not already know:**

A senior engineer who encounters `ctx.get_parameter_source` returning `None` from a callback diagnoses a timing bug. They move the write earlier. They encounter ghost sources. They thread `source` through `process_value`. They discover that `process_value` is called from one place, making its generic interface an architectural fiction. They conclude: "this was a design error; `process_value` should receive `source`."

What the law reveals that the senior engineer's analysis misses: fixing the timing (making source available to the callback) does not address the fundamental impossibility for callbacks that need non-winning candidate values. A callback implementing **"warn if the environment variable overrides the default value"** needs BOTH the env var's value AND the default value — even when commandline provides the winner and both env and default "lost." After every possible fix to the timing bug, this callback must re-evaluate `os.environ` and `param.default` itself. Those re-evaluations may produce different results from what `consume_value` saw (env var modified by another thread, callable default returning a different value on second call). The callback cannot get a consistent snapshot of all sources, because Click never took such a snapshot.

The cross that a senior engineer would not name: **the parameter callback is the only consumer that can modify parameter values; it is also the only consumer for which the resolution timestamp of non-winning candidates — the moment when they were discarded — has passed irreversibly before the callback runs.** Command callbacks (the only other modifying consumer, via `ctx.params` mutation) can see all ParameterSources correctly, but parameter values are already final by then. The consumers who most need non-winning candidate information (parameter callbacks that conditionally transform values based on competing sources) are architecturally positioned at the one point in the pipeline where that information is unrecoverable.

**What it predicts about a third design:**

A third design that (1) moves `set_parameter_source` before `process_value` (fixing the timing), (2) adds `ParameterSource.ABSENT` for the no-source case (fixing L8's ambiguity), and (3) adds a lightweight `ResolutionSummary` carrying only the winning source and a boolean "was another source also present?" (a minimal non-eager addition) — would be the optimal design achievable without eager evaluation.

The Resolution Terminus Law predicts this third design's exact residual impossibility: the "was another source also present?" boolean, while useful for simple policies ("warn if commandline was provided alongside an env var"), still cannot answer "what value would the competing source have produced?" A callback implementing the security policy "reject if commandline and environment disagree" still needs both values. The boolean tells the callback whether to look; it doesn't provide what to look at. The callback must still re-evaluate the competing source, and that re-evaluation cannot be guaranteed consistent with what `consume_value` observed.

This prediction is precise and non-obvious: it says the third design's failure mode will appear not in common use but specifically in policies that compare source values against each other. Such policies are the motivating use case for having multiple resolution sources in the first place — the reason default_map, env vars, and commandline coexist is that administrators, operators, and users set values from different sources, and policies that reconcile these sources are the natural application. The third design makes these policies easier to detect (the boolean signals "another source was present") while keeping them impossible to implement correctly without re-running resolution (you can't compare without values).

The third design's gap is the conservation law in its sharpest form: **make it easy to know that comparison is needed, impossible to do the comparison safely, and unable to resolve that tension without either eager evaluation or a consistent-snapshot API that Click's process model cannot provide.**
