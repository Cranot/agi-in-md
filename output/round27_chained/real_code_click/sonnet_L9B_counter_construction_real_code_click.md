# Level 9: Counter-Construction

---

## I. The Falsifiable Claim

> **`Context.invoke`'s `with self:` makes every context its own terminal lifecycle manager — which is locally correct for any single context, but which causes the group context to close BEFORE the subcommand context is created in `Group.invoke`'s non-chain path. The `parent=ctx` relationship in `cmd.make_context(cmd_name, args, parent=ctx)` is established on a `ctx` whose cleanup has already executed. Every cleanup callback registered during the group's callback fires before the subcommand begins — inverting the LIFO ordering that `parent=` containment implies and that Python's context manager protocol guarantees for properly nested `with` blocks.**

Falsifiable: instrument a `@group` callback with `ctx.call_on_close(lambda: log("group close"))` and a `@command` callback with `ctx.call_on_close(lambda: log("sub close"))`. Execute. Log reads `["group close", "sub close"]` — not `["sub close", "group close"]`. The parent cleans up before the child exists.

---

## II. The Three-Expert Dialectic

**Expert A — Defender:**
*"`parent=` is for PARAMETER INHERITANCE — `ctx.params`, `default_map`, `auto_envvar_prefix`. It is not a lifecycle containment guarantee. Python's `ExitStack` guarantees LIFO for resources registered with the SAME stack. Click has separate stacks per context. Separate stacks have separate LIFO guarantees. Cross-context LIFO is not Click's contract. If you want the group to outlive the subcommand, structure your cleanup accordingly. `ctx.call_on_close` scopes to THIS context's close, not to the logical command hierarchy."*

**Expert B — Attacker:**
*"The Defender says 'separate stacks, separate LIFO.' But Click chose the name PARENT. In every other Python framework using parent/child, parent outlives child. `ExitStack` composition is designed so outer stacks outlive inner stacks. Click's `Context.invoke`'s `with self:` closes the outer (group) context before the inner (subcommand) context is even created. The name `parent=` creates a containment contract. The implementation violates it. If Click doesn't guarantee LIFO across parent-child contexts, it should not use the word parent."*

**Expert C — Prober:**
*"Both of you are arguing about LIFO. Neither of you asked: why does `Group.invoke` have `with ctx:` at all, if `Context.invoke` already closes `ctx` via `with self:`?*

*Look at what's actually happening:*

```python
with ctx:                         # (A)
    super().invoke(ctx)           # (B) → ctx.invoke → with self: → ctx.close()
    # ... ctx._close_callbacks == [] here ...
    sub_ctx = make_context(...)   # (C) parent=closed ctx
    with sub_ctx:                 # (D)
        return sub_ctx.invoke()   # (E) → with self: → sub_ctx.close()
# (F) ctx.close() — no-op
# (G) sub_ctx.close() — no-op
```

*Block (A) does not manage the group callback's lifetime — `(B)` does. Block (D) does not manage the subcommand's lifetime — `(E)` does. Both outer `with:` blocks are structurally inert as lifecycle managers under normal execution.*

*Why do they exist? Error attribution. `with ctx:` in `Group.invoke` ensures that errors from `resolve_command`, `make_context`, and `_process_result` — code that runs BETWEEN callback invocations — are attributed to the right context. This is a DIFFERENT purpose from lifecycle management.*

*What both of you take for granted: that `with ctx:` is a lifecycle manager. It's serving two purposes simultaneously — lifecycle termination (as a side effect of `Context.__exit__`) and error attribution (as its intended use). `Context.__exit__` calls `close()` regardless of which purpose motivated the `with` statement. There's no mechanism to distinguish "this `with ctx:` is lifecycle management" from "this `with ctx:` is error attribution." Both trigger `close()`. The lifecycle terminates at the first `with ctx:` exit encountered in execution — which is inside `Context.invoke`'s `with self:`, not at the outer `with ctx:` blocks. The outer blocks provide correct error attribution and zero lifecycle management. They LOOK like they manage lifetime. They don't.*"

---

## III. The Transformation

| | Claim |
|---|---|
| **Original** | "`Group.invoke` creates the subcommand context after the group context closes, inverting LIFO cleanup order" |
| **Transformed** | "Click uses `Context.__enter__`/`__exit__` for two structurally distinct purposes — **lifecycle termination** (`Context.invoke`'s `with self:`) and **error attribution** (`Group.invoke`'s `with ctx:`, `main`'s `with ctx:`) — with no mechanism to distinguish them. Because `Context.__exit__` always calls `close()`, every use of a context as a context manager is a lifecycle termination event, whether or not termination is the intent. The outer `with ctx:` blocks were written for error attribution; they terminate the lifecycle as a side effect. `Context.invoke`'s `with self:` was written for lifecycle termination; it provides error attribution as a side effect. The two uses are semantically opposite but syntactically identical. The composition of both on the same context produces a structure where the lifecycle terminates at the FIRST `with ctx:` exit (inside `Context.invoke`), and all subsequent `with ctx:` exits are inert as lifecycle managers but still syntactically present — creating the appearance of managed lifetime where the lifetime has already ended." |

---

## IV. The Gap as Diagnostic

The gap between original and transformed claim is the distance between **ordering error** (LIFO inverted) and **semantic collision** (`Context.__exit__` is a single mechanism pressed into two incompatible purposes).

L8 found that `ParameterSource.DEFAULT` carries two meanings — "not yet determined" and "legitimately defaulted" — with no mechanism to distinguish them. The same structure appears in the execution pipeline: `Context.__exit__` carries two meanings — "close this context's lifecycle" and "attribute this block's errors to this context" — with no mechanism to distinguish them.

L8's mechanism was **stage-boundary correctness masking pipeline-level information destruction**. The new mechanism is different:

### **"Mechanism Reuse Masking Purpose Collision"**

`Context.__exit__` is used wherever a context appears in a `with` statement. It's always syntactically identical. But it serves three distinct purposes across the codebase:

1. **Terminal lifecycle management**: "This is the context's final close; run cleanup." (`Context.invoke`'s `with self:`)
2. **Error attribution**: "Attribute errors in this block to this context." (`Group.invoke`'s `with ctx:`, `main`'s `with ctx:`)
3. **Backup cleanup**: "If everything else fails, this will close the context." (The structurally inert outer blocks)

Because all three use identical syntax, a reader sees `with ctx:` and cannot determine which purpose is intended. The idempotent `close()` makes all three mechanically safe — but only the first encountered in execution order actually terminates the lifecycle. The code cannot signal which `with ctx:` is the terminal one. Readers who audit each `with ctx:` find it correct in isolation and stop. The failure lives only in the composition.

---

## V. Apply the Concealment Mechanism

Where does mechanism reuse most effectively mask the purpose collision?

At the `Group.invoke` / `Context.invoke` boundary:

```python
with ctx:                    # LOOKS LIKE: lifetime manager
    super().invoke(ctx)      # ← ctx is closed HERE, inside Context.invoke's with self:
    # everything below runs on a closed ctx
    sub_ctx = make_context(..., parent=ctx)
    with sub_ctx:            # LOOKS LIKE: lifetime manager
        return sub_ctx.invoke(...)  # ← sub_ctx closes HERE
# ← these two with-block exits are no-ops
```

The concealment is most effective because the outer `with ctx:` CONTAINS the code that closes `ctx`. It looks like the outer block manages the inner block's resources. In reality, the inner close happens first, and the outer exits are no-ops. The containment relationship expressed syntactically is the inverse of the containment relationship that actually controls cleanup.

---

## VI. The Legitimate-Looking Improvement That Deepens the Concealment

Refactor `Group.invoke` (non-chain) to make the two lifecycle phases explicit:

```python
def invoke(self, ctx):
    def _process_result(value):
        if self._result_callback is not None:
            value = ctx.invoke(self._result_callback, value, **ctx.params)
        return value

    if not ctx._protected_args:
        if self.invoke_without_command:
            with ctx:
                rv = super().invoke(ctx)
                return _process_result([] if self.chain else rv)
        ctx.fail(_("Missing command."))

    args = [*ctx._protected_args, *ctx.args]
    ctx.args = []
    ctx._protected_args = []

    if not self.chain:
        with ctx:
            cmd_name, cmd, args = self.resolve_command(ctx, args)
            assert cmd is not None
            ctx.invoked_subcommand = cmd_name

            # Phase 1: execute this group's own callback (if any)
            super().invoke(ctx)

            # Phase 2: dispatch to subcommand (group's callback phase is complete)
            sub_ctx = cmd.make_context(cmd_name, args, parent=ctx)
            with sub_ctx:
                return _process_result(sub_ctx.command.invoke(sub_ctx))
```

**Why this passes code review:** No behavioral change. The comments make the two-phase structure legible and defensible. "Group's callback phase is complete" accurately describes what happened. The code is shorter and cleaner than the original.

**Why it deepens the concealment:**

The comment `# Phase 2: dispatch to subcommand (group's callback phase is complete)` re-describes the LIFO inversion as a design decision. "Phase is complete" sounds like intentional sequencing, not lifecycle inversion. A reviewer who might have asked "why is `ctx` closed before `sub_ctx` is created?" now reads the comment and answers their own question: "the group's phase completes first, then the subcommand runs — by design."

The improvement makes the inverted LIFO look like documented phased execution. The structural bug becomes the documented spec.

---

## VII. Three Properties Only Visible Because of the Strengthening

**1. `ctx.invoked_subcommand` assignment before `super().invoke(ctx)` is a deliberate information contract, not incidental ordering.**

The original sets `ctx.invoked_subcommand = cmd_name` BEFORE `super().invoke(ctx)`. This is intentional: the group callback can read `ctx.invoked_subcommand` to make decisions based on which subcommand was selected. When writing the phased refactoring, I had to decide where this assignment goes relative to Phase 1. Placing it inside `with ctx:` but before `super().invoke(ctx)` is identical to the original — but the "Phase 1 / Phase 2" framing actively obscures this: a reader sees "Phase 1: group callback, Phase 2: subcommand dispatch" and doesn't notice that Phase 1's callback receives Phase 2's target as input. This cross-phase data flow is a semantic coupling that the phased framing conceals. The strengthening revealed the coupling by forcing me to position the assignment explicitly.

**2. The outer `with ctx:` exists to attribute DISPATCH errors, not callback errors — and these are categorically different error classes.**

When structuring the phases, I had to decide which code goes inside `with ctx:`. The decision revealed: `resolve_command`, `make_context`, and `_process_result` can raise errors that need to be attributed to the GROUP context (so users see "Error: in group X"). These are dispatch/infrastructure errors. The group callback's errors are attributed by `Context.invoke`'s `with self:` via `augment_usage_errors`. The outer `with ctx:` was written for a completely different error class: dispatch-infrastructure errors BETWEEN callbacks. The strengthening forced me to discover that the two `with:` mechanisms are serving categorically different error populations — not redundant implementations of the same thing.

**3. `_process_result`'s `ctx.invoke(...)` constitutes a third close of `ctx`, and the count is non-deterministic from reading `Group.invoke` alone.**

Writing the phased refactoring made me count the closes:

- Close 1: `super().invoke(ctx)` → inside `Context.invoke`'s `with self:` (if group has a callback)
- Close 2: `ctx.invoke(result_callback, ...)` inside `_process_result` → inside `Context.invoke`'s `with self:` (if result callback exists)
- Close 3: The outer `with ctx:` in `Group.invoke` exits

The count of actual lifecycle-terminating closes (1 or 2) depends on whether a group callback and result callback exist — properties of the GROUP configuration, not visible in `Group.invoke`'s code. The phased labeling makes the code look like it has one clean close per phase. But the close count is an emergent property of which callbacks are configured. This is only visible because the strengthening made me trace through each `ctx.invoke` call explicitly.

---

## VIII. The Contradictory Improvement

**Improvement 2**: Separate `Context.invoke` into two methods — one that does not close the context, and one that does:

```python
def invoke(self, callback, *args, **kwargs):
    """Invoke a callback in this context's error scope.
    
    Does not manage context lifecycle. The context remains open after
    this call. Use for intermediate callbacks (parameter callbacks,
    sub-invocations within a multi-step operation).
    """
    with augment_usage_errors(self):
        return callback(*args, **kwargs)

def call(self, callback, *args, **kwargs):
    """Invoke a callback as this context's terminal action.
    
    The context closes when the callback returns. Use for the
    primary command callback — the action that should complete
    this context's lifetime.
    """
    with augment_usage_errors(self):
        with self:
            return callback(*args, **kwargs)
```

`Command.invoke` uses `ctx.call`. `process_value`'s parameter callback uses `ctx.invoke`. The outer `with ctx:` blocks in `main` and `Group.invoke` become the actual lifecycle managers.

**Why this passes code review:** Separates two concerns with precise names and accurate docstrings. `invoke` is non-destructive; `call` is terminal. Parameter callbacks correctly use `invoke`. Command callbacks correctly use `call`. The outer `with ctx:` blocks become the authoritative lifetime managers they appear to be.

**Why it contradicts Improvement 1:**

Improvement 1 accepts that "`Context.invoke` closes the context" and reorganizes callers around this. The `with self:` stays in `Context.invoke`.

Improvement 2 rejects that "`Context.invoke` closes the context." The `with self:` moves to `call`. Callers explicitly choose between terminal and non-terminal invocation.

Both pass independent review. Both are legitimate responses to the same structural ambiguity. But they encode irreconcilable architectural choices: one says the context closes inside `invoke`, one says it closes at the outer `with ctx:` boundary.

---

## IX. The Structural Conflict That Exists Only Because Both Improvements Are Legitimate

Improvement 1 says: **"The context's lifecycle owner is `Context.invoke`. Callers structure themselves around this."**

Improvement 2 says: **"The context's lifecycle owner is the outer `with ctx:` block. `Context.invoke` should not usurp this."**

If both coexist:
- Improvement 1's `Context.invoke` (with `with self:`) + Improvement 2's `ctx.call(callback)` = two lifecycle terminators, double-close. Original bug restored.
- Improvement 2's `ctx.invoke` (no `with self:`) + Improvement 1's reorganized `Group.invoke` = `Group.invoke` expects `Context.invoke` to close ctx, but now it doesn't. No lifecycle terminator at all. Context leaks.

**The structural conflict:**

The original architecture provided TWO lifecycle terminators for the same context — `Context.invoke`'s `with self:` and the outer `with ctx:` blocks. The idempotent `close()` made this mechanically safe while leaving it semantically undefined. Both improvements resolve the ambiguity — in opposite directions. Because the original architecture expressed no preference, both directions are architecturally correct. Neither can be chosen without knowing the intent behind the original design, and the original design provides no mechanism to express that intent.

This is structurally identical to L8's finding: `ParameterSource` has no `MISSING` variant, so any implementation distinguishing "has default of None" from "has no default" can only do so by extending the enum — and the extension direction has no architectural specification. Both improvements to L8's problem are legitimate; both change the gap in different directions.

---

## X. The Structural Summary

| Level | Finding | Mechanism | What It Conceals |
|---|---|---|---|
| **L7** | 15+ inheritance chains; dead `type_cast_value`; three competing value authorities | Local coherence masking systemic incoherence | `_meta` aliasing creates shared mutable state across all contexts |
| **L8** | `consume_value` produces `(UNSET, DEFAULT)` for absent parameters; two incompatible absence sentinels; `ParameterSource` cannot represent MISSING | Stage-boundary correctness masking pipeline-level information destruction | No stage owns the cross-cutting UNSET-preservation contract; information destruction is irreversible before any consumer can observe it |
| **L9** | `Context.invoke`'s `with self:` closes the group context before the subcommand context is created; `parent=ctx` delivers data inheritance without lifecycle nesting; LIFO cleanup ordering is inverted | Mechanism reuse masking purpose collision (`Context.__exit__` serves lifecycle termination and error attribution with no disambiguation) | The context's terminal lifecycle owner is unspecified; `Context.invoke`'s `with self:` and the outer `with ctx:` blocks both claim ownership; idempotent `close()` defers the conflict rather than resolving it |

**The Diagonal:**

L7: value **authorities** have no priority contract — which source wins?  
L8: value **attribution** has no correctness contract — how is "no default" recorded?  
L9: context **ownership** has no lifecycle contract — who closes the context?

All three are instances of one structural pattern: **Click uses a single token — a sentinel value (UNSET), an enum variant (DEFAULT), a parameter name (`parent=`), a Python protocol (`with self:`) — to represent a relationship that requires two concepts, delivers one, and leaves the gap structurally invisible because the token appears complete from every local vantage point.**

The deepest finding: Click's idempotent `close()` is not an implementation convenience — it is a **conflict deferral mechanism**. It makes multi-ownership mechanically safe while leaving it semantically undefined. The question "who closes this context?" has no answer in Click's architecture. `close()`'s idempotence ensures the question never surfaces as an exception — until a user needs to know WHEN cleanup runs, at which point the architecture cannot answer.

What L9's analysis cannot see: if there is a fourth level of the same pattern, it will be in the **result aggregation layer** — not in how values flow (L8), not in how contexts close (L9), but in how `_process_result` and the `result_callback` compose return values across a chain when individual commands fail mid-sequence. In chain mode, `contexts` is fully built before any command executes. If command N's `invoke` raises an exception, commands N+1 through end are abandoned — but their contexts exist, were created with `parent=ctx`, and are never explicitly closed. The `ExitStack` and `_close_callbacks` for each abandoned context are orphaned. The same "single-token overload" pattern appears in `chain=True`'s creation loop: `sub_ctx.args = []` after parsing each command treats args extraction as both "giving remaining args to the next command" and "confirming this command's parse is complete" — two meanings, one operation, no mechanism to express which failed if the loop exits abnormally.
