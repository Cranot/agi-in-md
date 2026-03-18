## What the Second Analysis Conceals

**Mount's Synthetic Path Parameter** — the first analysis identified the specific mechanism at line 144 where Mount compiles `self.path + "/{path:path}"` to capture delegation remainder. The second analysis sees scope mutation but not the *input transformation* that makes delegation possible.

---

## Dependency Chain the Second Analysis Missed

```
Mount.__init__ (line 144)
    → compile_path(self.path + "/{path:path}") creates synthetic parameter
    → regex captures remainder after mount prefix
    
Mount.matches (lines 149-156)
    → matched_params.pop("path") extracts remainder
    → remaining_path = "/" + remainder
    → matched_path = route_path[:-len(remaining_path)]
    
Mount.matches (line 160)
    → "root_path": root_path + matched_path
    → sub-app receives scope with path context rewritten
    
Result:
    → Sub-app operates as if mounted at root
    → Illusion of independent apps requires no sub-app awareness
```

The second analysis's "Scope as Accumulator" describes *what gets written* but not *how the synthetic parameter enables the write*. The `path` parameter doesn't exist in user code — it's manufactured by Mount to enable path delegation.

---

## Conservation Law

**Mount Transparency × Parameter Synthesis Complexity = constant**

The first analysis: `Automatic Resolution × Control Flow Visibility = constant`
The second analysis: `Routing Implicitness × Debuggability = constant`

These are surface variants. The deeper conservation the second analysis conceals:

**Delegation Seamlessness × Delegation Mechanism Visibility = constant**

The more Mount makes sub-apps "just work" (no awareness of mount point, no path stripping logic), the more machinery must exist to manufacture that illusion:

| What sub-app sees | What Mount must do |
|-------------------|-------------------|
| `path = "/users/42"` | Extract `remaining_path` from synthetic `path` parameter |
| `root_path = ""` | Compute `root_path + matched_path` and inject |
| No knowledge of siblings | Manufacture `{path}` in regex, never expose it |

The second analysis's scope mutation is the *output* of this mechanism. The first analysis identified the *input* — the synthetic parameter that captures what the mount prefix doesn't match. Without the synthetic parameter, there's no remainder to delegate, and the entire Mount abstraction collapses into explicit path manipulation in every sub-app.
