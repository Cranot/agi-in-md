# Miniaturization Analysis: Starlette Routing

## Part 1: The Three Impossible Properties

This code simultaneously claims:

1. **Arbitrary Composition** — Mounts nest infinitely, each with independent path parameters
2. **Bidirectional Routing** — `url_path_for()` reconstructs URLs from names and parameters
3. **Flat Parameter Namespace** — All route parameters share a single dictionary without hierarchical scoping

**Proof of Impossibility:**

Consider nested mounts:
```
Mount("/users/{id}", routes=[
    Mount("/posts/{id}", routes=[
        Route("/{id}", handler)  # Three parameters, all named "id"
    ])
])
```

When `url_path_for("handler", id=5)` is called:
- Which `id` corresponds to which path segment?
- The flat namespace cannot disambiguate

The code attempts escape via naming convention (`"mount:submount:route"` at line 221), but this **couples naming to structure** — you cannot rename a mount without breaking all URL generation downstream.

**What was sacrificed:** *Parameter provenance*. Once a parameter enters `path_params`, its origin is lost. The system cannot distinguish between `{id}` from layer 1 vs layer 3.

---

## Part 2: Minimal Viable Router

```python
import re

class Route:
    def __init__(self, path, handler):
        self.path, self.handler, self.regex = path, handler, re.compile(f"^{path}$")
    
    def match(self, p): 
        m = self.regex.match(p)
        return m.groupdict() if m else None

class Router:
    def __init__(self, routes): 
        self.routes, self._names = routes, {r.handler.__name__: r for r in routes}
    
    async def __call__(self, scope, receive, send):
        for r in self.routes:
            if (p := r.match(scope["path"])):
                scope["path_params"] = p
                return await r.handler(scope, receive, send)
    
    def url_for(self, name, **kw): 
        return self._names[name].path.format(**kw)
```

**18 lines. Preserves core contract: path→handler dispatch, handler→path reversal.**

| Dropped | Why |
|---------|-----|
| Mount composition | Requires parameter namespace solution |
| WebSocket/Lifespan | Secondary protocols, not routing core |
| Middleware stacking | Orthogonal concern |
| Partial matches (method filtering) | Optimization, not essence |
| Path convertors | Syntactic sugar over string matching |
| Redirect slashes | Convenience feature |
| Error handling | Robustness, not functionality |

**What stays:** The mapping function. Everything else is engineering.

---

## Part 3: Conservation Law

```
Expressiveness × Determinism = Constant
```

| Scale | Expressiveness | Determinism |
|-------|---------------|-------------|
| Full (747 lines) | Arbitrary nesting, middleware, protocols | Ambiguous dispatch order, parameter collisions |
| Mini (18 lines) | Flat routes only | Trivially predictable |

The quantity preserved: **Information bandwidth of the path ↔ handler mapping**. Both versions transmit exactly the same essential information. The full version adds channels (middleware hooks, protocol variants) but cannot increase the fundamental bandwidth of the routing decision.

Alternative formulation:
```
Abstraction Depth × Debuggability = Constant
```

---

## Part 4: Meta-Analysis — What My Miniaturization Conceals

My 18-line router conceals:

1. **The parameter type system** — `CONVERTOR_TYPES` provides int validation, path encoding safety
2. **The Match.PARTIAL optimization** — Method filtering before full match enables 405 responses
3. **The scope mutation contract** — Original code carefully layers `path_params` without destroying parent values

**What my analysis miniaturization conceals:**

The 3-bug structure conceals that the **shadowed `app` function (lines 28-32)** is not merely a bug but a **category error** — it reveals the code was never executed in its current form. The inner function takes `(scope, receive, send)` as parameters but **never uses them**. It's a closure masquerading as an ASGI app.

**Meta-Conservation Law:**
```
Explanation Brevity × Edge Case Visibility = Constant
```

My condensed analysis necessarily hides the long tail of interactions between middleware stacking and route matching, the subtle ways `root_path` propagation affects mounted applications, and the lifespan context manager state machine.

---

## Part 5: Concrete Bugs

| # | Location | Severity | Description | Fixable? |
|---|----------|----------|-------------|----------|
| 1 | Lines 28-32 | **CRITICAL** | `request_response` defines `async def app` nested inside `async def app`. Inner function shadows outer, and inner's `(scope, receive, send)` parameters are never used — it closes over outer's `request`. Code is dead/never-tested. | **Fixable:** Rename inner function or flatten structure |
| 2 | Lines 39-45 | MODERATE | `replace_params` mutates `path_params` dict via `.pop()`. Caller's dictionary is modified unexpectedly. | **Fixable:** Operate on `dict(path_params)` copy |
| 3 | Line 204 | STRUCTURAL | Mount always appends `/{path:path}` to pattern. Parameter name `path` is reserved and cannot be used by user routes under a Mount. | **Structural:** Requires API redesign |
| 4 | Lines 142-143 | LOW | `self.param_convertors[key]` assumes regex groups match convertor keys. If they diverge, KeyError. | **Fixable:** Add defensive `if key in self.param_convertors` |
| 5 | Lines 159-162 | LOW | `url_path_for` uses `assert not remaining_params`. Assertions can be disabled with `-O` flag, changing runtime behavior. | **Fixable:** Replace with explicit check + exception |
| 6 | Lines 269-271 | LOW | `middleware` assumed iterable of 3-tuples. Invalid input produces confusing TypeError. | **Fixable:** Add type validation with clear error message |
| 7 | Throughout | EXTERNAL | Uses undefined imports: `Request`, `PlainTextResponse`, `WebSocketClose`, `URLPath`, `CONVERTOR_TYPES`, etc. | **Contextual:** These exist in full Starlette codebase |

---

## Summary

The conservation law governing all routing systems:

```
Route Complexity × Dispatch Predictability = Constant
```

Starlette chose complexity. The miniature reveals that routing, at its heart, is **pattern matching plus function dispatch** — everything else (middleware, nesting, protocols, convertors) is scaffolding that conceals this simplicity while enabling scale.

The critical bug (nested `app` function) proves this code was extracted from a larger working system but became non-functional in isolation — a fitting metaphor for miniaturization itself.
