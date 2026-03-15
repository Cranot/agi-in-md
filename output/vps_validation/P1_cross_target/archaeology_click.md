# Archaeological Excavation: Click Core

## Layer 1 — Surface

A CLI framework exposing four primary classes: `Context` (execution state), `Command` (callable units), `Group` (command containers), and `Parameter` (argument handlers). The public contract: decorate functions, chain groups, invoke with `__call__`. Parameter resolution cascade: commandline → environment → default_map → default. Context inheritance enables nested command execution with propagated settings.

## Layer 2 — Foundation

**The parent-pointer Context pattern.** Evidence: `self.parent = parent` is the first assignment, and inheritance cascades appear 15+ times in `__init__` alone (`if X is None and parent is not None`). The `_depth` counter (`parent._depth + 1`) proves nested invocation was the founding decision. Every subsequent class ultimately creates or consumes Context objects. The `UNSET` sentinel enables the foundational distinction between "not provided" and "provided as None."

## Layer 3 — Sediment

| Stratum | Pressure | Hides |
|---------|----------|-------|
| `ParameterSource` enum | Debugging provenance | That values have 5+ confusing origins |
| `resilient_parsing` | Shell completion | Parse-without-execute needed separate mode |
| `deprecated` (bool\|str) | Organic deprecation | No planned deprecation system existed |
| `chain` mode | `cmd1 && cmd2` workflows | Group.invoke() is two functions in one |
| `_protected_args` | Single vs chain dispatch | Temporal coupling between parse and invoke |
| `ExitStack` | Resource cleanup | Late addition for managed lifecycles |

## Layer 4 — Fossils

- **`_help_option = None`** — Declared, never assigned. Vestigial caching optimization.
- **`forward()` method** — Odd signature passing `self` and params together. Remnant of discarded composition pattern.
- **`lookup_default(call=True)`** — Callable defaults in config maps. Feature never fully realized.
- **Dual-type `deprecated`** — `if isinstance(self.deprecated, str)` reveals collision between "add flag" and "add message" eras.

## Layer 5 — Fault Lines

1. **Context inheritance vs Command settings** — Both parent context and command object consulted for same values via `if X is None` chains. Source of truth ambiguous.

2. **`_protected_args` temporal coupling** — parse_args() populates, invoke() consumes. Calling invoke() without parse_args() silently breaks.

3. **Chain mode bifurcation** — `if not self.chain:` path shares nothing with chain path. Two designs welded at the invoke() method.

4. **UNSET → None collapse** — System tracks UNSET through entire pipeline, then `if value is UNSET: ctx.params[name] = None` discards the distinction.

## Derive

**Context depth × Resolution indirection = Semantic constant**

The product of nesting levels and parameter source lookups preserves what arrives at the callback: a flat `**kwargs` dict. Whether values traverse 5 parent contexts or 5 resolution sources, the callback receives identical interface.

---

## Diagnostic

This excavation conceals: I'm analyzing ~400 lines of a 3,418-line file. I inferred chronology from code patterns without git history — `deprecated` may be original, not accumulated. The `UNSET` constant I called foundational isn't shown. My conservation law is post-hoc pattern-matching, not verified invariant across versions. I confused code organization with geological time.
