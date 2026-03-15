# Starlette Routing: Structural Analysis and Conservation Laws

## Three Desirable Properties

1. **Instantaneous route lookup** – O(1) or O(log n) regardless of route count
2. **Full expressiveness** – nested mounts, path converters, method filtering, pattern matching
3. **Architectural simplicity** – maintainable, comprehensible codebase

## Proof of Incompatibility

Examining `Router.app()` (lines 225-246):

```python
for route in self.routes:  # Sequential iteration - O(n)
    match, child_scope = route.matches(scope)
    if match is Match.FULL:
        scope.update(child_scope)
        await route.handle(scope, receive, send)
        return
```

Each iteration calls `route.matches()` which executes compiled regex matching. **This is O(n) complexity where n = route count**, sacrificing property (1). The conservation law emerges:

**FLEXIBILITY × PERFORMANCE = COMPILE-TIME BUDGET**

Regex pre-compilation shifts cost to initialization, but runtime scales linearly. You cannot have constant-time lookup AND arbitrary regex patterns AND simple sequential iteration.

---

## First Recursion: Trie-Based Optimization

**Improvement:** Replace sequential iteration with prefix tree for O(path_length) lookup.

**Problem resurfaces in `Mount.url_path_for()` (lines 177-194):**

```python
for route in self.routes or []:  # Still O(n) linear search
    try:
        url = route.url_path_for(remaining_name, **remaining_params)
        return URLPath(path=path_prefix.rstrip("/") + str(url), protocol=url.protocol)
    except NoMatchFound:
        pass
```

And `Mount.matches()` uses `{path:path}` capture (line 129) which consumes arbitrary remaining paths. Dynamic nested routing requires exhaustive descendant search — **the trie cannot help when any branch might contain a match at arbitrary depth**. The optimization defeats itself.

---

## Second Recursion: LRU Cache

**Improvement:** Cache `(path, method) → (match, child_scope)` for O(1) repeated requests.

**Problem resurfaces in scope mutation:**

```python
# In Route.matches() (lines 106-114)
path_params = dict(scope.get("path_params", {}))
path_params.update(matched_params)
child_scope = {"endpoint": self.endpoint, "path_params": path_params}
```

Each request mutates `scope['path_params']` differently. Middleware stacks (lines 76-80, 143-145) are applied per-route during initialization:

```python
for cls, args, kwargs in reversed(middleware):
    self.app = cls(self.app, *args, kwargs)
```

**Caching prevents per-request isolation** — the cached result for path `/api/123` with params `{"id": "123"}` cannot be reused because subsequent requests need independent `path_params` dict instances. Stateful routing breaks cache invalidation.

---

## Diagnostic of Conservation Law

The law **FLEXIBILITY × PERFORMANCE = COMPILE-TIME BUDGET** conceals context coupling. It assumes routing is `f(pattern, path) → match`, but the code reveals:

**DECLARATIVE COMPLETENESS × RUNTIME MUTABILITY = FRAMEWORK BOUNDARY**

Starlette attempts to make routes fully declarative (compile-time regex in `compile_path()` lines 24-51) but ASGI scopes are fundamentally mutable:

| Declarative Intent | Runtime Reality |
|-------------------|-----------------|
| `compile_path()` builds static regex | `scope['path_params']` mutated per-request |
| Route methods fixed at init | Method check happens **after** regex match (line 116) |
| Middleware stack pre-built | `root_path` accumulation nested (line 144) |

The impedance mismatch creates permanent friction. The framework boundary is where declarative patterns meet mutable ASGI scopes.

---

## HARVEST: Concrete Defects

| # | Defect | Severity | Structural/Fixable |
|---|--------|----------|-------------------|
| 1 | Sequential iteration in `Router.app()` lines 225-234 | **HIGH** | **STRUCTURAL** – Predicted by conservation law |
| 2 | `Mount.url_path_for()` searches all child routes linearly lines 177-194 | **MEDIUM** | **STRUCTURAL** – Descendant search requires full traversal |
| 3 | Duplicate `path_params` logic in `Route.matches()` and `Mount.matches()` | **LOW** | **FIXABLE** – Extract to shared method |
| 4 | `replace_params()` mutates input via `pop()` line 62 | **MEDIUM** | **FIXABLE** – Copy dict before mutation |
| 5 | Method check AFTER regex in `Route.matches()` line 116 | **LOW** | **STRUCTURAL** – Match enum design couples concerns |
| 6 | `redirect_slashes` causes double iteration lines 248-258 | **MEDIUM** | **STRUCTURAL** – UX/performance trade-off |
| 7 | No validation that middleware is callable before wrapping | **LOW** | **FIXABLE** – Add `callable()` check in `__init__` |

**Structural defects** (1, 2, 5, 6) are consequences of the conservation law — fundamental to supporting flexible routing with simple architecture. **Fixable defects** (3, 4, 7) are implementation oversights correctable without architectural redesign.

The core limitation: **you cannot optimize what you must search exhaustively**. Starlette trades lookup performance for routing expressiveness, and this trade-off is embedded in every recursive optimization attempt.
