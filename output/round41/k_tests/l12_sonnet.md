# Level 12 Meta-Conservation Analysis: Starlette routing.py

## Falsifiable Claim

**The deepest structural problem in this code is that scope mutation creates implicit communication channels between routing layers that have no formal contract, causing failures when the implicit protocol is violated.**

The code relies on `scope.update(child_scope)` as a communication mechanism between `Route.matches()`, `Mount.matches()`, and `Router.app()`. This creates a hidden dependency graph where:
1. Mount expects `path_params` to exist in scope before it adds its own
2. Router expects `endpoint` to be set by Route/Mount
3. Routes expect `path_params` to accumulate correctly through nesting

This claim is falsifiable: if false, we would observe explicit contracts, type annotations, or validation at scope boundaries.

---

## Triangular Dialectic

### Voice 1: The Defender

The claim is overstated. Scope mutation is the **ASGI design pattern**—the spec explicitly defines scope as a mutable dictionary passed through middleware and routing layers. This isn't "implicit," it's the documented protocol. The code correctly:
- Uses `dict.get()` with defaults for optional keys
- Creates new dictionaries for child scopes before merging
- Follows the ASGI specification's intent

The real problems are surface-level: the duplicate `app` function shadowing in `request_response`, missing assertions on scope type in some branches. Not a "deep structural" issue.

### Voice 2: The Attacker

The defender is naive. The ASGI spec defines what keys *must* exist initially—it does not define what keys routing layers *may add* or *must preserve*. The code has:
- No schema for what keys exist after `Route.matches()` vs `Mount.matches()`
- No validation that required keys exist before access (`scope["method"]` assumes HTTP)
- No documentation of the `app_root_path` vs `root_path` distinction
- Silent data loss: `path_params` can be overwritten if a nested route uses the same param name

The claim understates the problem: it's not just implicit communication, it's **communication without versioning or compatibility guarantees**.

### Voice 3: The Prober (Synthesis)

Both voices assume scope is a *communication channel*. What if scope is actually a *shared memory region with uncoordinated access*?

The deeper issue: **no routing component owns its invariants**. When `Mount.matches()` modifies `root_path`, it assumes downstream handlers will use the modified value. When `Route.matches()` sets `endpoint`, it assumes Router will dispatch to it. But nothing enforces these assumptions—they're "social contracts" in code form.

The original claim misses that the problem isn't just mutation—it's **ownership ambiguity**. Who owns `scope["path_params"]`? Everyone and no one.

---

## The Gap

The transformed claim reveals what the original concealed: **not just implicit communication, but undefined ownership of shared state**.

The original claim framed this as a communication protocol problem (sender/receiver mismatch). The dialectic reveals it's actually a **property rights problem** (who owns what keys).

---

## Concealment Mechanism

**Protocol Theater**: The code performs the appearance of a well-defined protocol (Match enum, explicit return tuples, named scope keys) while the actual mechanism is unstructured dictionary mutation. The `Match` enum and `child_scope` return pattern create the illusion of a formal interface, but:
- Any key can be added to child_scope
- Any key can overwrite existing scope values
- No component declares what it reads vs writes

This conceals the **ownership vacuum** behind a facade of structure.

---

## Concealment-Strengthening Improvement

```python
class ScopeContract:
    """Defines the contract for scope modifications at each routing layer."""
    READS: FrozenSet[str] = frozenset()
    WRITES: FrozenSet[str] = frozenset()
    
    @classmethod
    def validate_transition(cls, scope: Dict, child_scope: Dict) -> Dict:
        """Validate scope transition and merge safely."""
        for key in cls.WRITES:
            if key in scope and key not in cls.READS:
                warnings.warn(f"Overwriting scope key '{key}' without reading it")
        merged = dict(scope)
        merged.update(child_scope)
        return merged

class RouteScopeContract(ScopeContract):
    READS = frozenset({"type", "method", "path_params"})
    WRITES = frozenset({"endpoint", "path_params"})

class MountScopeContract(ScopeContract):
    READS = frozenset({"type", "root_path", "app_root_path", "path_params"})
    WRITES = frozenset({"path_params", "root_path", "app_root_path", "endpoint"})
```

**Why this passes code review**: It adds documentation, validation, and warnings. It's "defensive programming."

**What it conceals**: It formalizes the *wrong abstraction*. By making keys explicit, it hides that the real problem is **mutual dependence between keys** (path_params depends on remaining_path, root_path depends on matched_path). The contract captures surface keys, not semantic relationships.

---

## Properties Visible Only Through Strengthening

1. **Key independence is false**: The contract model assumes keys are independent, but `root_path` and `app_root_path` have a semantic relationship the contract cannot express.

2. **Write order matters**: Mount's writes to `root_path` followed by Route's writes to `path_params` create an implicit ordering that the contract model treats as atomic.

3. **No contract for conditional writes**: Route only writes `endpoint` on match, but the contract declares it as always-written. The boolean conditions on writes are invisible.

---

## Second Improvement (Addressing Recreated Property)

```python
@dataclass(frozen=True)
class RoutingTransition:
    """Immutable snapshot of routing state at each layer."""
    path_params: Mapping[str, Any]
    endpoint: Optional[Callable]
    root_path: str
    remaining_path: str
    matched_path: str
    
    def apply_mount(self, mount: 'Mount') -> 'RoutingTransition':
        """Derive next state after mount matching. Fails if invariant violated."""
        if self.remaining_path == self.matched_path:
            raise RoutingInvariantError("Cannot distinguish matched from remaining path")
        return RoutingTransition(
            path_params={**self.path_params, **mount.extracted_params},
            endpoint=mount.app,
            root_path=self.root_path + self.matched_path,
            remaining_path=self.remaining_path[len(self.matched_path):],
            matched_path=""  # Reset for next layer
        )
```

**What this reveals**: By making the transition explicit, we discover that `remaining_path` and `matched_path` must always satisfy `remaining_path + matched_path == original_path`—an invariant that was implicit and never validated.

---

## Structural Invariant

**The Invariant**: `path_param_accumulation_preserves_totality`

At every routing level, the sum of:
- Parameters extracted at this level
- Parameters delegated to child routes

Must equal the total parameters in the path. The code maintains this through `path_params.update(matched_params)` but never validates it.

This is a property of the **routing problem space**, not the implementation. Any routing system that decomposes paths must maintain this invariant.

---

## Inverting the Invariant

**Make totality trivial by eliminating decomposition**:

```python
class FlatRouter:
    """Single-level routing with no nesting."""
    
    def __init__(self):
        self._routes: Dict[CompiledPattern, Handler] = {}
    
    def add_route(self, pattern: str, handler: Handler):
        """Register a complete path pattern. No nesting means no accumulation."""
        compiled = self._compile_global_pattern(pattern)
        self._routes[compiled] = handler
    
    def match(self, path: str) -> Optional[Tuple[Handler, Dict[str, Any]]]:
        """Match in one step. Parameters extracted atomically."""
        for pattern, handler in self._routes.items():
            if match := pattern.match(path):
                return handler, match.groupdict()
        return None
```

**New impossibility**: Cannot compose routes dynamically. A `Mount` that adds routes at runtime cannot exist because there's no nesting. The trade-off: **composition vs atomic parameter extraction**.

---

## Conservation Law

**Parameter Extraction Granularity × Composition Depth = Constant**

| Design | Extraction Granularity | Composition Depth | Product |
|--------|------------------------|-------------------|---------|
| Current Starlette | Per-level (accumulates) | Unlimited nesting | High × High |
| FlatRouter | Single-pass (atomic) | Zero nesting | Low × None |
| Hybrid | Two-level (prefix + route) | One level nesting | Medium × Low |

You cannot have both fine-grained parameter extraction at each layer AND deep composition—each extracted parameter creates a coordination point that constrains the next layer.

---

## Meta-Conservation Law

**What does the conservation law conceal?**

The law assumes **parameters are the only coordinated state**. But the code also coordinates:
- `endpoint` (which handler to call)
- `root_path` (for URL generation)
- `app_root_path` (for nested applications)
- `type` (http vs websocket vs lifespan)

**The real conserved quantity is Coordination Surface Area:**

```
(Parameter Types + State Types) × Composition Depth = Constant
```

The current code has 4 state types × high depth. FlatRouter has 1 state type × zero depth. The law concealed that **adding state types is equivalent to adding composition depth**—both increase coordination complexity.

---

## Meta-Law

**Coordination Dimensions × Composition Levels = Constant**

This is specific to routing, not general:
- Adding a new coordinated state type (e.g., `tenant_id` passed through all routes) is equivalent to adding a nesting level in terms of bug surface area
- A bug caused by incorrect `root_path` propagation in a 3-level Mount chain is isomorphic to a bug caused by coordinating 3 state types in a flat router
- **Prediction**: Any PR that adds a new scope key will have the same bug rate as a PR that adds a new Mount nesting level

This is NOT "complexity is bad"—it's that **spatial and dimensional complexity are fungible in routing systems**.

---

## Bug Harvest

| # | Location | What Breaks | Severity | Fixable/Structural |
|---|----------|-------------|----------|-------------------|
| 1 | `request_response` L24-31 | Nested `async def app` shadows outer `app`, causing `wrap_app_handling_exceptions` to receive wrong function. Exception handling broken. | **Critical** | Fixable (rename inner function) |
| 2 | `Mount.matches` L159 | `matched_path = route_path[:-len(remaining_path)]` when `remaining_path == route_path` (path matches exactly with no remaining) produces empty string instead of full path. Edge case: Mount at "/" with path param. | **High** | Fixable (add conditional) |
| 3 | `compile_path` L76 | `is_host` branch handles hostname routing but `Route.__init__` asserts `path.startswith("/")` — host routing only works via direct Mount construction, never Route. Undocumented limitation. | **Medium** | Structural (document or remove is_host) |
| 4 | `Route.matches` L118 | `scope.get("path_params", {})` then `update()` — if parent Mount passed `path_params` with same key name, child silently overwrites. Data loss. | **High** | Structural (requires key namespacing) |
| 5 | `Router.app` L232 | `scope.update(child_scope)` after partial match — if partial route set `endpoint` and default handler reads it, wrong handler called. | **Medium** | Fixable (clear endpoint on default) |
| 6 | `Mount.url_path_for` L175 | `path_params["path"] = path_params["path"].lstrip("/")` mutates caller's dict. Side effect escapes function boundary. | **Low** | Fixable (copy dict first) |
| 7 | `Router.__init__` L189 | `self.routes = [] if routes is None else list(routes)` — creates copy, but `Mount.routes` property returns reference to internal list. Inconsistent mutability. | **Low** | Fixable (return tuple or document) |
| 8 | `BaseRoute.__call__` L99 | `scope.update(child_scope)` mutates scope BEFORE checking `match is Match.NONE` — if match is NONE, scope is already polluted with partial child_scope. | **Medium** | Fixable (move update after check) |
| 9 | `Router.app` L247 | Redirect logic creates `redirect_scope = dict(scope)` but doesn't copy nested objects. If `scope["headers"]` is mutated downstream, redirect scope affected. | **Low** | Structural (shallow vs deep copy trade-off) |
| 10 | `compile_path` L64 | `assert convertor_type in CONVERTOR_TYPES` — assertion can be disabled with `-O` flag. Should be explicit validation. | **Low** | Fixable (raise ValueError) |
| 11 | `Mount.__init__` L140 | `self.path = path.rstrip("/")` — empty string path "/" becomes "". Then `compile_path(self.path + "/{path:path}")` produces "/{path:path}" for root mount. Correct but confusing. | **Info** | Fixable (document behavior) |
| 12 | `Router.not_found` L198 | Checks `if "app" in scope` to decide between raising HTTPException and returning PlainTextResponse. Key may or may not exist depending on call path. Undocumented contract. | **Medium** | Structural (scope content undefined) |
| 13 | `replace_params` L32 | Iterates `list(path_params.items())` while mutating `path_params.pop(key)`. Works but confusing. If convertor.to_string fails mid-iteration, partial mutation. | **Low** | Fixable (collect then mutate) |
| 14 | `Route.__init__` L111 | `if methods is None: methods = ["GET"]` inside the function/branch check, but `if methods is None: self.methods = set()` outside. Inconsistent: function endpoint defaults to GET, class endpoint defaults to empty. | **Medium** | Fixable (unify logic) |
| 15 | `Router.app` L229 | `partial` and `partial_scope` declared but `partial_scope` only set when `partial is None` check passes first time. If second route is PARTIAL, `partial_scope` is stale from first partial. | **High** | Fixable (move assignment) |

**Conservation Law Prediction**: Bug #4 (path_params overwrite) and Bug #15 (stale partial_scope) are both manifestations of the same structural issue—uncoordinated state accumulation. The conservation law predicts they cannot both be fixed without either adding explicit coordination (contracts) or removing accumulation (flat routing). Fixable in code, but fixes will increase coordination surface elsewhere.

---

## Summary

The Starlette routing system's deepest structural property is **coordination through undocumented scope mutation**. The conservation law (Coordination Dimensions × Composition Levels = Constant) explains why adding new scope keys or new nesting levels produces equivalent bug rates. The meta-law reveals that spatial and dimensional complexity are fungible in routing—a 3-level nested router with 2 state types has the same bug surface as a flat router tracking 6 state types.

The most severe immediate bugs are:
1. **Critical**: `request_response` function shadowing breaks exception handling
2. **High**: `path_params` silent overwrite in nested routes
3. **High**: Stale `partial_scope` when multiple routes return PARTIAL
