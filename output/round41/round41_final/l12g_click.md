# L12 Structural Analysis: Click Core

## PHASE 1 — STRUCTURAL ANALYSIS

### Three Properties Claimed

1. **Hierarchical Context Inheritance** — Child contexts automatically inherit 12+ properties from parent (obj, default_map, terminal_width, help_option_names, auto_envvar_prefix, _opt_prefixes, _meta, etc.)

2. **Independent Command Dispatch** — Each command in a group/chain executes with its own context, parameters resolved independently

3. **Unified Parameter Resolution** — Single precedence chain: commandline → environment → default_map → default, producing one canonical value per parameter

### Proof They Cannot Coexist

**The contradiction manifests in chain mode (lines 264-290):**

```python
# Line 264-265: Group.invoke modifies parent context state
args = [*ctx._protected_args, *ctx.args]
ctx.args = []
ctx._protected_args = []

# Line 276-277: Creates "independent" sub-contexts, BUT:
sub_ctx = cmd.make_context(cmd_name, args, parent=ctx,
                           allow_extra_args=True,        # FORCED
                           allow_interspersed_args=False) # FORCED
```

**The conflict:**
- Property 1 requires children inherit from parent
- Property 2 requires commands execute independently  
- Property 3 requires deterministic parameter resolution

**But:** In chain mode, command execution ORDER affects what args each receives (line 286-290 iterates sequentially, consuming args). Commands are NOT independent — they're coupled through shared arg consumption from parent context.

**Simultaneously:** Line 277 OVERRIDES the command's own `allow_extra_args` and `allow_interspersed_args` settings. A command that declares `allow_extra_args=False` is ignored in chains. The "independent" command's configuration is discarded.

### Conservation Law

**Parse State Continuity × Context Isolation = Constant**

- To preserve parse state (args flow through chain), contexts must share mutable state
- To preserve context isolation (independent commands), each must have immutable snapshot
- Click chooses: args consumed globally (line 264-265), contexts created fresh but with forced settings (line 277)
- The conservation: you cannot have BOTH continuous arg flow AND respect for command-level configuration

### Concealment Mechanism

**Distributed resolution across three locations:**

1. **Context.\_\_init\_\_** (lines 42-96): Inherits from parent, but scattered across 15+ if-blocks
2. **Parameter.consume_value** (lines 393-410): Precedence chain, but doesn't show that default_map itself may be inherited/nested
3. **Group.invoke** (lines 264-290): Creates sub-contexts, but silently overrides command settings

**The coupling is invisible at any single point.** Reading consume_value alone, you can't see that default_map might cascade from grandparent context. Reading Group.invoke alone, you can't see that the allow_extra_args override contradicts Command's declared settings.

### Improvement That Recreates Problem Deeper

Add explicit inheritance control:

```python
class Context:
    def __init__(self, ..., inherit=None, ...):
        # inherit=None: current behavior (inherit all)
        # inherit={}: inherit nothing
        # inherit={'obj', 'default_map'}: selective inheritance
        self._inherit = inherit
        if parent and (inherit is None or 'obj' in (inherit or [])):
            self.obj = parent.obj
        # etc.
```

**This "solves" inheritance but recreates the problem:**
1. Now callers must know which properties to inherit
2. Default (None = inherit all) preserves backward compatibility AND the original coupling
3. Chain mode still forces allow_extra_args=True regardless of inheritance settings
4. New ambiguity: if `inherit={}` but `obj=None` passed, did caller INTEND empty obj or forget to inherit?

---

## PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | If Wrong |
|-------|---------------|------------|----------|
| Context inherits 12+ properties from parent | STRUCTURAL (SAFE) | 1.0 | — |
| Group.invoke creates sub-contexts in chain mode | STRUCTURAL (SAFE) | 1.0 | — |
| Parameter precedence: cmdline→env→default_map→default | STRUCTURAL (SAFE) | 1.0 | — |
| Line 277 overrides command's allow_extra_args settings | STRUCTURAL (SAFE) | 1.0 | — |
| Chain commands coupled through arg consumption order | STRUCTURAL (SAFE) | 1.0 | — |
| Conservation: Parse Continuity × Context Isolation = constant | CONTEXTUAL | 0.85 | Conservation law formulated differently |
| Concealment via distributed resolution | STRUCTURAL (SAFE) | 1.0 | — |
| Improvement recreates problem deeper | CONTEXTUAL | 0.8 | Hypothetical, not verifiable from source |

---

## PHASE 3 — SELF-CORRECTION

**Revising contextual claims to structural grounding:**

The conservation law formulation is CONTEXTUAL. The STRUCTURAL fact is:

**Lines 264-265 consume ctx.args globally, then line 277 creates "independent" contexts with FORCED settings that override command declarations.** This is verifiable tension, not hypothetical.

**Verified defects from source:**

| Location | Defect | Severity | Type |
|----------|--------|----------|------|
| Line 43-44 | `obj=None` cannot explicitly clear inherited obj — `if obj is None and parent` means parent.obj ALWAYS wins | Medium | Structural |
| Line 48-50 | default_map inheritance skipped if info_name is None — silent data loss | Medium | Structural |
| Line 277 | Chain mode ignores command's allow_extra_args/allow_interspersed_args declarations | High | Structural |
| Line 98 | No depth limit on context nesting — unbounded recursion possible | Low | Structural |
| Line 174-175 | UNSET→None conversion AFTER callbacks run — callback sees UNSET, post-parse sees None | Medium | Structural |
| Line 426 | expose_value=False params don't appear in ctx.params, but ParameterSource still tracked — inconsistent state | Low | Structural |

---

## FINAL OUTPUT

### Conservation Law (Source-Grounded)

**Parse State Continuity × Context Isolation = Constant**

Evidence: Lines 264-265 (global arg consumption) × Lines 276-277 (fresh contexts with forced settings). Click chooses partial continuity + partial isolation, achieving neither fully.

### Defect Table (SAFE + Verified Only)

| # | Location | Defect | Severity | Fixable/Structural |
|---|----------|--------|----------|-------------------|
| 1 | L43-44 | Cannot explicitly set `obj=None` in child context — parent.obj always inherited when obj=None passed | Medium | Structural (requires API change) |
| 2 | L48-50 | default_map inheritance silently skipped when info_name=None | Medium | Fixable (add explicit inheritance flag) |
| 3 | L277 | Chain mode forcibly overrides command's `allow_extra_args` and `allow_interspersed_args` settings | High | Structural (chain semantics require this) |
| 4 | L98 | No maximum depth validation on context nesting | Low | Fixable (add depth check) |
| 5 | L174-175 | UNSET converted to None after callbacks execute — callbacks see different value than post-parse ctx.params | Medium | Fixable (convert before callbacks) |
| 6 | L393-410 | ParameterSource.PROMPT defined (L23) but never assigned in consume_value precedence chain | Low | Structural (prompt handled elsewhere, enum misleading) |
| 7 | L276-277 | Sub-contexts in chain are siblings (all parent=ctx), not sequential (parent=prev_sub_ctx) — order-dependent side effects on shared parent are visible | Medium | Structural (by design) |
