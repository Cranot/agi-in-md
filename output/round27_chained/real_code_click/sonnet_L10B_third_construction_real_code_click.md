# Level 10: The Sequence-Tree Incompatibility

---

## I. The Falsifiable Claim

> **In chain mode, `Group.invoke` separates command parsing (the `while args:` loop, which creates all sub-contexts) from command execution (the `for sub_ctx in contexts:` loop, which invokes them). This separation is not optional — command argument boundary detection requires parsing, which requires context creation, which cannot be deferred. The contexts produced by the parse phase are stored in a local list ordered by execution sequence. If execution fails at index K, contexts `[K+1:]` exist with registered resources but receive no cleanup: `parent=ctx` is a data link, not a lifecycle link; `ctx.close()` does not enumerate children; Python's GC does not guarantee `ExitStack.__del__`; the `with ctx:` outer block closes only the group context (already closed). Cleanup callbacks registered in contexts `[K+1:]` never fire.**

Falsifiable: construct a three-command chain. In the third command's parameter callback, call `ctx.call_on_close(lambda: print("cmd3 cleanup"))` and also print `"cmd3 parsing"`. Make the second command's callback raise `RuntimeError`. Execute. The output is: `cmd3 parsing` (fires during `make_context`, inside `ctx.invoke`'s `with self:`) followed by no `cmd3 cleanup` — or if cleanup fires during parsing, it fires before cmd1 or cmd2 execute. The execution-phase cleanup never fires because the third context's command callback never runs.

---

## II. The Three-Expert Dialectic

**Expert A — Defender:**
*"This is correct API usage documented nowhere. `ctx.call_on_close` registers cleanup for when the context closes. The context closes. It just closes earlier than you expected — during parameter processing, inside `ctx.invoke`. That's the documented behavior of `ctx.invoke`: it wraps in `with self:`. If you want cleanup after the command runs, return the resource as a value, let the command manage it, or use `try/finally` in the command callback. The chain mode parse loop is correct: it resolves all commands, stores their parsed contexts, then executes. If one fails, the others don't execute. That's chain semantics. Cleanup for commands that don't execute is the user's problem."*

**Expert B — Attacker:**
*"The Defender says 'that's chain semantics' — but chain mode has no documented semantics for partial failure. Click's own examples show the `ctx.call_on_close` pattern for resource management. The `parent=ctx` pointer on orphaned contexts points at the group context. A user who reads Click's architecture sees: group closes, children close. That's wrong — children outlive their parent (L9's finding) AND in the orphan case, children never close. The API implies a containment guarantee. The implementation delivers nothing. If Click doesn't guarantee cleanup for created contexts, it should not create contexts for commands that won't execute — but it cannot know which commands won't execute until execution begins. The structural problem is Click's, not the user's."*

**Expert C — Prober:**
*"Both of you are arguing about cleanup responsibility. Neither asked why the parse/execute separation exists at all.*

*Look at the parse loop carefully:*

```python
while args:
    cmd_name, cmd, args = self.resolve_command(ctx, args)
    sub_ctx = cmd.make_context(cmd_name, args, parent=ctx,
                               allow_extra_args=True,
                               allow_interspersed_args=False)
    contexts.append(sub_ctx)
    args, sub_ctx.args = sub_ctx.args, []
```

*`resolve_command` consumes the command name token and returns `args[1:]`. The REMAINING arguments — the boundary between this command's args and the next command's name — is determined entirely by `make_context`: the parser runs with `allow_extra_args=True, allow_interspersed_args=False`, which stops at the first unrecognized positional token (the next command name) and places everything after it in `sub_ctx.args`. The boundary is a PARSING OUTPUT.*

*This means: you cannot know where command N's args end without parsing command N. You cannot parse command N without creating its context. Context creation IS boundary detection. They are the same operation.*

*The parse/execute separation is not a design choice — it is structurally forced. If you want to validate all command names before executing any (which the current code does: if `cmd3` is unknown, Click fails before `cmd1` executes), you must parse all commands first. Parsing all commands means creating all contexts. There is no implementation that validates-all-before-executing without creating-all-contexts.*

*What both of you take for granted: that the orphan problem is about missing cleanup for contexts that could have been avoided. They couldn't. The contexts were necessarily created. The problem is that Click's context model — a tree with `parent=` links — has no mechanism for expressing cleanup ordering among SIBLINGS. Trees order parent → child. Chain mode needs SEQUENCE ordering: cmd1's cleanup before or after cmd2's, in defined order. `parent=ctx` points all siblings at the same parent; it says nothing about siblings' relationships to each other. The cleanup protocol Click needs for chain mode doesn't exist in Click's architecture.*"

---

## III. The Transformation

| | Claim |
|---|---|
| **Original** | "Orphaned contexts in chain mode receive no cleanup because `parent=ctx` is a data link, not a lifecycle link" |
| **Transformed** | "Chain mode requires all sub-contexts to be created before any execute (boundary detection = context creation = same operation, non-separable). The contexts are stored in a list that carries sequence ordering. Click's context model is a tree that carries parent-child ordering only. The list's ordering (1st, 2nd, Nth sibling) has no representation in the tree. Cleanup among siblings is therefore architecturally undefined: the tree model can propagate cleanup from parent to child (if it chose to), but it has no protocol for sibling cleanup ordering — which sibling closes first, in what order, and with what guarantees under partial failure. The orphan cleanup failure is not a missing loop; it is the absence of a concept." |

---

## IV. The Gap as Diagnostic

The gap between original and transformed is the distance between **missing cleanup** (a loop that should have closed things) and **missing concept** (no architectural representation of sibling ordering).

L9's mechanism was **Mechanism Reuse Masking Purpose Collision** — `Context.__exit__` serves two purposes with no disambiguation. The new mechanism is different:

### **"Topological Projection Masking Incompatibility"**

Chain mode projects a SEQUENCE onto a TREE. The sequence (`contexts = [sub_ctx_1, sub_ctx_2, sub_ctx_3]`) carries properties that trees don't have:

1. **Ordinal position**: sub_ctx_2 is after sub_ctx_1
2. **Sequential cleanup contract**: if the sequence is partially executed, unexecuted members have a defined relationship to executed members
3. **Failure boundary**: execution failure at position K partitions the sequence into "ran" and "never ran"

The context TREE has none of these. `parent=ctx` on all three siblings makes them equivalent nodes in the tree — unordered, symmetric. No tree operation can recover the sequence's ordinal properties.

The projection is invisible because the `contexts` list DOES carry the ordering. A reader sees `for sub_ctx in contexts:` and infers "these run in order." They do. But the inference "their cleanup also runs in order" requires the sequence's properties, and the sequence's properties live only in the local variable `contexts`, not in the context model.

---

## V. Apply the Concealment Mechanism

Where does topological projection most effectively hide incompatibility?

At the transition between the two loops:

```python
    # PARSE PHASE
    contexts = []
    while args:
        cmd_name, cmd, args = self.resolve_command(ctx, args)
        sub_ctx = cmd.make_context(cmd_name, args, parent=ctx, ...)
        contexts.append(sub_ctx)           # ← sequence ordering lives here
        args, sub_ctx.args = sub_ctx.args, []

    # EXECUTE PHASE
    rv = []
    for sub_ctx in contexts:               # ← sequence ordering consumed here
        with sub_ctx:                      # ← cleanup responsibility per-iteration
            rv.append(sub_ctx.command.invoke(sub_ctx))
```

The two loops look structurally parallel — each iterates the same sequence, each processes one sub-context per iteration. The symmetry implies the execute loop is as complete as the parse loop: "parse everything, then execute everything." The asymmetry is invisible: the parse loop always completes (or fails at boundary detection, before any context is stored); the execute loop may abort midway, leaving `contexts[K+1:]` with full parse-phase state but zero execute-phase cleanup.

The `rv = []` between loops is the deepest concealment point. It looks like a clean handoff — "parse results discarded, execution results beginning." It contains no error handling. It implicitly guarantees that `contexts` will be fully consumed. The guarantee is false and invisible.

---

## VI. The Legitimate-Looking Improvement That Deepens the Concealment

Wrap the execute loop in an `ExitStack` that registers all sub-contexts during the parse phase:

```python
with ctx:
    ctx.invoked_subcommand = "*" if args else None
    super().invoke(ctx)
    
    with ExitStack() as stack:
        # Parse phase: register each sub-context for cleanup as created
        contexts = []
        while args:
            cmd_name, cmd, args = self.resolve_command(ctx, args)
            assert cmd is not None
            sub_ctx = cmd.make_context(cmd_name, args, parent=ctx,
                                       allow_extra_args=True,
                                       allow_interspersed_args=False)
            stack.enter_context(sub_ctx)   # cleanup guaranteed regardless of execution
            contexts.append(sub_ctx)
            args, sub_ctx.args = sub_ctx.args, []
        
        # Execute phase: invoke each, ExitStack handles cleanup
        rv = []
        for sub_ctx in contexts:
            rv.append(sub_ctx.command.invoke(sub_ctx))
    
    return _process_result(rv)
```

**Why this passes code review:** `ExitStack` is Python's canonical solution for "manage N resources with exception safety." The code is shorter (removes `with sub_ctx:` from the execute loop). The comment makes intent explicit. Cleanup is now guaranteed for all sub-contexts, whether they executed or not. A senior reviewer would recognize this as the correct pattern and approve immediately.

**Why it deepens the concealment:**

The ExitStack "solution" re-describes the structural incompatibility as solved. It provides orphan cleanup — the missing loop. The reviewer closes the ticket. But the fix commits to LIFO cleanup ordering (ExitStack's default), which is the OPPOSITE of execution ordering (FIFO). Sub-ctx_3 was created last, runs last, and should clean up last — but ExitStack closes it first. If cleanup has ordering dependencies (cmd2's cleanup assumes cmd1's resource is still open, as in a pipeline), ExitStack inverts the contract.

More deeply: `sub_ctx.command.invoke(sub_ctx)` inside the execute loop calls `ctx.invoke(command_callback)` which closes `sub_ctx` via `with self:`. The ExitStack also closes `sub_ctx` at block exit. Now sub-ctxes are double-closed — idempotent, mechanically safe, but the double-ownership is invisible. Two code paths claim lifecycle authority over the same context; the ExitStack improvement makes this look like comprehensive coverage rather than competing claims.

---

## VII. Three Properties Only Visible Because of the Strengthening

**1. LIFO and FIFO are both wrong, and the right ordering is execution-order-relative, not creation-order-relative.**

Writing the ExitStack required choosing a close ordering: LIFO (ExitStack's default) or FIFO (explicit stack reversal). The choice forced me to ask: what is the correct ordering? The strengthening revealed there is none specified. For a three-command chain that successfully executes, LIFO means cmd3 closes before cmd1 — the reverse of execution. For a chain where cmd2 fails, LIFO means cmd3 closes before cmd1 even though cmd3 never executed. The "correct" ordering depends on whether cleanup should mirror execution order (FIFO), reverse it (LIFO), or depend on whether execution occurred. None of these is expressible in the current architecture. The strengthening revealed that the ordering question is not an implementation detail — it is the missing concept.

**2. `sub_ctx.command.invoke(sub_ctx)` and `stack.enter_context(sub_ctx)` are now two lifecycle owners of the same context — and only the idempotent `close()` prevents this from being observable.**

The original code had `with sub_ctx:` inside the execute loop. The strengthening moved responsibility to the ExitStack. But `sub_ctx.command.invoke` still calls `ctx.invoke(callback)` which still includes `with self:` which still calls `close()`. So after the ExitStack fix, every sub-ctx is closed TWICE: once during command invocation (inside `ctx.invoke`'s `with self:`) and once when the ExitStack exits. The double-close is mechanically safe (idempotent `close()`), but it means any cleanup callback registered DURING the command callback fires at the COMMAND-INVOKE close — before the ExitStack's LIFO close. The ExitStack's close finds nothing and does nothing. The ExitStack is not the actual lifecycle owner it appears to be; it's a fallback that fires after the real owner has already acted. The strengthening made two lifecycle owners visible in a single context.

**3. The `_process_result(rv)` call is positioned outside the ExitStack block, meaning it executes after all sub-contexts are closed.**

In the original code, `_process_result(rv)` is inside `with ctx:` but outside `with sub_ctx:` — the result callback runs after all sub-context executions but before the outer context closes. In the ExitStack version, `_process_result(rv)` must go outside the ExitStack block (since it needs `rv`, which is only populated after the execute loop). But outside the ExitStack block, all sub-contexts are already closed. The result callback receives `rv` (the aggregate results) and `**ctx.params` (the group's parameters), but any context-managed resources that contributed to those results have already been cleaned up. `_process_result` is a post-cleanup operation in ALL versions of the code — but only the ExitStack version makes this visible by establishing an explicit cleanup boundary. The original's `with sub_ctx:` blocks obscure this by interleaving cleanup with result collection.

---

## VIII. The Contradictory Improvement

**Improvement 2**: Collapse parse and execute into a single loop (eager execution):

```python
with ctx:
    ctx.invoked_subcommand = "*" if args else None
    super().invoke(ctx)
    rv = []
    while args:
        cmd_name, cmd, args = self.resolve_command(ctx, args)
        assert cmd is not None
        sub_ctx = cmd.make_context(cmd_name, args, parent=ctx,
                                   allow_extra_args=True,
                                   allow_interspersed_args=False)
        args, sub_ctx.args = sub_ctx.args, []
        with sub_ctx:
            rv.append(sub_ctx.command.invoke(sub_ctx))
    return _process_result(rv)
```

**Why this passes code review:** Eliminates the parse/execute separation entirely. Each command is parsed, executed, and cleaned up before the next is parsed. No orphaned contexts are possible — `with sub_ctx:` manages each context's lifetime synchronously. Code is shorter. The ExitStack is unnecessary. A reviewer preferring simplicity would choose this immediately.

**Why it contradicts Improvement 1:**

Improvement 1 preserves the parse/execute separation and adds cleanup guarantees to the execute phase. It accepts that all parsing precedes all execution.

Improvement 2 rejects the parse/execute separation as the mechanism, executing each command before parsing the next.

Both solve the orphan problem. Both produce correct output for successful chains. But they encode opposite answers to a question the original code never asks: **"Should all command names be resolved before any command executes?"**

With Improvement 1 (ExitStack), if `cmd3` is an unknown name, Click fails BEFORE `cmd1` executes. With Improvement 2 (eager), Click executes `cmd1` and `cmd2`, THEN fails when it encounters `cmd3`. These produce different observable side effects from `cmd1` and `cmd2` before the failure.

---

## IX. The Structural Conflict That Exists Only Because Both Improvements Are Legitimate

Improvement 1 says: **"Validate all command names before executing any."**

Improvement 2 says: **"Execute each command as it is parsed."**

The structural conflict: the original code's parse/execute separation IMPLICITLY implements "validate before execute" — but this is an emergent property of the code's structure, not a documented semantic guarantee. The code provides no mechanism to express which semantic is intended. Because both semantics are legitimate for a command chain, and because neither is specified, both improvements are architecturally correct responses to the same code. They cannot both be applied. Choosing between them requires knowing the intent behind the original separation — intent the code does not encode.

The conflict is not resolvable by reading `Group.invoke`. It requires a specification that doesn't exist.

---

## X. The Third Improvement: Resolution Attempt

Separate name resolution (which can validate all command names without creating contexts) from argument boundary detection (which requires parsing):

```python
with ctx:
    ctx.invoked_subcommand = "*" if args else None
    super().invoke(ctx)
    
    # Phase 1: resolve all command names (detect unknown commands before executing any)
    resolved = []
    remaining = args
    while remaining:
        cmd_name, cmd, remaining = self.resolve_command(ctx, remaining)
        assert cmd is not None
        resolved.append((cmd_name, cmd))
        # ← How much of `remaining` belongs to `cmd`?
        # We cannot know without parsing `cmd`.
        # `remaining = remaining` is wrong — we've consumed only the command name,
        # not its arguments. We need to advance past cmd's arguments to reach
        # the next command name — but doing so requires parsing cmd.
```

**How this improvement fails:**

The separation is impossible. `resolve_command` consumes only the command name token. The remaining tokens include this command's arguments AND all subsequent commands. To advance `remaining` past this command's arguments requires knowing where they end — which requires parsing this command — which requires calling `make_context` — which creates a context.

There is no parser state, no heuristic, no lookahead that can identify command argument boundaries without parsing. The boundary is determined by which tokens are recognized as this command's parameters and which are not — information that exists only after the parameter processing logic runs.

The third improvement fails because it requires separating two things that are a single computation: "where does this command's argument list end" and "create the context that processes this command's arguments" are not sequential steps. They are one step, expressed as `make_context`. Any implementation of "validate names before creating contexts" reduces to this impossibility.

---

## XI. What the Failure Reveals About the Design Space

The failure of the third improvement reveals a three-constraint impossibility that the conflict between Improvements 1 and 2 could not show alone:

**The three constraints:**

| Constraint | What it requires |
|---|---|
| (A) Validate all names before executing any | All command names resolved before first execution |
| (B) Execute each command immediately after parsing | No parse-ahead; eager invocation |
| (C) Correct cleanup on partial failure | All created contexts receive cleanup |

The conflict between Improvements 1 and 2 showed that (A) and (B) produce different observable behavior and cannot both be satisfied. But it left open the question: can either pair {A,C} or {B,C} be satisfied?

The failure of the third improvement reveals: **(A) requires creating all contexts before executing any** — because name resolution requires parsing, which requires context creation. This is not a limitation of Click's implementation; it is a constraint of any parser that determines argument boundaries by running the parser. (A) and (C) together are satisfiable (Improvement 1, ExitStack) but only with LIFO cleanup ordering — which may be wrong for pipelines. (B) and (C) are satisfiable (Improvement 2, eager) with FIFO ordering — but changes the failure semantics for unknown command names.

**No implementation satisfies all three simultaneously.**

What this reveals about the design space:

Click's context model is a **tree**. Trees express one structural relationship: parent-child. For the command hierarchy (groups contain subcommands), this is correct. But chain mode requires a second structural relationship: **sibling sequence ordering**. In a three-command chain, sub_ctx_1 and sub_ctx_2 and sub_ctx_3 are siblings (same parent). The tree model treats them as symmetric. The chain semantics treat them as ordered: cmd1 runs before cmd2, cmd2 before cmd3, and cleanup — if anything meaningful about ordering is to be guaranteed — must respect this sequence.

The context tree has no representation for "sibling at index N precedes sibling at index N+1." This information exists only in the local variable `contexts` inside `Group.invoke`. When an exception propagates out of `Group.invoke`, `contexts` goes out of scope. The sequence ordering is lost with it.

The missing abstraction: **a context sequence** — a first-class object that owns an ordered list of sibling contexts, provides FIFO or LIFO cleanup among them, and handles partial failure by cleaning up only the contexts that were created (regardless of execution status). This is neither a context tree nor a Python `ExitStack` (which handles LIFO for arbitrary resource types but has no concept of "this resource was never executed"). It is a new abstraction that Click does not have.

---

## XII. The Secondary Finding: Parameters Close Contexts During Creation

The third improvement's failure also revealed something the chain-mode analysis alone could not: parameter callbacks using `ctx.invoke` inside `process_value` close the context DURING `make_context` — before the context is returned to its caller.

```python
# In process_value:
value = ctx.invoke(self.callback, ctx=ctx, param=self, value=value)
#       ↑
#       ctx.invoke includes `with self:` → ctx.close() fires HERE
#       inside make_context's with ctx.scope(cleanup=False):
```

`scope(cleanup=False)` protects only the scope block's own exit from calling `close()`. It does not protect against embedded `ctx.invoke` calls closing the context from within. The context returned by `make_context` is already closed if any parameter has a callback. The command callback then calls `ctx.invoke` on a closed context — idempotent, mechanically safe, but: cleanup callbacks registered during the command callback fire at command-invoke close; cleanup callbacks registered during parameter processing fire at parse-time close (before the command runs).

The pattern is identical to L9's finding at a different layer:
- L9: `Context.invoke`'s `with self:` closes the GROUP's context before the SUBCOMMAND context is created.
- L10 (secondary): `Context.invoke`'s `with self:` closes the SUBCOMMAND's context DURING its creation, before the command callback runs.

Both are instances of `ctx.invoke`'s `with self:` appearing at a call site where lifecycle termination is not the intent — parameter processing, not command dispatch.

---

## XIII. The Complete Diagonal

| Level | Finding | Mechanism | Missing Concept |
|---|---|---|---|
| **L7** | 15+ inheritance chains; competing value authorities | Local coherence masking systemic incoherence | Priority contract for value sources |
| **L8** | `ParameterSource.DEFAULT` = two states; `UNSET` sentinel destroyed before consumers observe it | Stage-boundary correctness masking pipeline-level information destruction | Representation of "no default exists" distinct from "default is X" |
| **L9** | `Context.__exit__` serves lifecycle termination and error attribution; `with self:` terminates lifecycle at first encounter; outer `with ctx:` blocks are structurally inert | Mechanism reuse masking purpose collision | Designated lifecycle owner for each context |
| **L10** | Chain mode requires parse-before-execute (non-separable from context creation); context tree has no sibling ordering protocol; partial chain failure leaves orphaned contexts with no cleanup path | Topological projection masking structural incompatibility | First-class sequence ordering for sibling contexts |

**The diagonal's deep pattern:** Click uses a single data structure — `ParameterSource`, `UNSET`, the context-manager protocol, the parent-child tree — to carry a relationship that has two or more distinct dimensions. Each structure correctly represents one dimension while providing no mechanism for the others. The missing dimensions accumulate:

- L7: source IDENTITY but no source PRIORITY  
- L8: source ORIGIN but no source ABSENCE  
- L9: context LIFECYCLE but no lifecycle OWNERSHIP  
- L10: context HIERARCHY but no sibling SEQUENCE  

In each case, the structure appears complete from every local vantage point — the single dimension it represents is correct and sufficient for any individual operation. The gap is only visible in COMPOSITION: when two contexts interact through cleanup (L9), when two commands in a chain interact through failure recovery (L10).

**The deepest finding:** The `parent=` link is Click's universal composition mechanism. It carries everything that should propagate downward through the command hierarchy: parameters, defaults, configuration, error context, color settings. It carries nothing that should propagate laterally (sibling to sibling) or upward (child cleanup triggering parent awareness). Chain mode requires lateral propagation (cleanup ordering among siblings) that `parent=` cannot express. The fix requires a new composition primitive — one that Click has no vocabulary for.
