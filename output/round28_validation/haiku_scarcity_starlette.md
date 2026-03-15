## Starlette Routing: Scarcity Analysis

---

### **PROBLEM 1: Linear Route Matching (O(n) Scan)**

```python
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match == Match.FULL:
        scope.update(child_scope)
        await route.handle(scope, receive, send)
        return
```

**Concrete bottleneck**: Every request scans the entire `self.routes` list sequentially.

**Resource scarcity exposed**: **Route count budget**. The code assumes you'll never have more than ~100–500 routes before linear iteration becomes visibly slow. Beyond that, latency per request grows linearly.

**Alternative (gamble on opposite scarcity)**: Routes could number 10,000+. Optimize for scale, not simplicity.

```python
# Startup cost: Build routing trie/index
self._route_index = RouteTrie()
for route in self.routes:
    self._route_index.add(route.path_pattern, route)

# Per-request: O(log n) lookup instead of O(n)
route = self._route_index.lookup(route_path)
if route and route.matches(scope):
    await route.handle(scope, receive, send)
```

**Trade-off**:
- **Old**: Loose memory coupling (no structure), tight latency coupling (every request pays O(n))
- **New**: Tight memory coupling (trie overhead ~5–10x), loose latency coupling (O(log n) per request)
- **Hidden cost**: Dynamic route registration becomes O(log n) + rebalance. Mount hierarchies now require parent-level index rebuild. Startup time increases ~50–200ms for 1000+ routes.

---

### **PROBLEM 2: Scope Dictionary Mutation (Unsafe Composition)**

```python
# In Route.__call__:
scope.update(child_scope)  
await self.handle(scope, receive, send)

# In Mount.matches:
scope.update(child_scope)  
await route.handle(scope, receive, send)
```

Every layer mutates `scope` in place, accumulating path_params and metadata.

**Concrete risk**: If scope were ever shared across concurrent handlers (or if ASGI isolation failed), mutations would leak between requests.

**Resource scarcity exposed**: **Request isolation guarantee**. The code assumes:
- ASGI server guarantees each request gets its own scope dict
- No handler will accidentally share scope with siblings
- Mutation is always safe because isolation is external to the framework

This is *actually* guaranteed by ASGI spec, but it's an **implicit fragile dependency**.

**Alternative (gamble on opposite scarcity)**: Scope could be shared or accessed concurrently. Design for explicit safety.

```python
# Old: mutate scope globally
scope.update(child_scope)
await self.handle(scope, receive, send)

# New: build immutable chain at each layer
def _handle_with_scope(self, base_scope, child_scope):
    new_scope = {**base_scope, **child_scope}
    await self.handle(new_scope, receive, send)
```

**Trade-off**:
- **Old**: Fast (mutation is free), but fragile (depends on external isolation guarantee)
- **New**: Safe (no aliasing bugs, composable), but 2–4x more allocations per handler layer
  - For a request through 5 middleware/mounts, that's 10–20 extra dicts allocated and garbage-collected
  - GC pressure increases; request latency increases ~1–3%, but becomes deterministic and testable
  - Enables true concurrent request handling without hidden dependencies

---

### **PROBLEM 3: Trailing Slash Double-Scan + Redirect**

```python
# First scan: try exact match
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match == Match.FULL:
        # ... dispatch and return

# If first scan fails, try with slash variant:
if self.redirect_slashes and route_path != "/":
    redirect_scope["path"] = redirect_scope["path"] + "/" if not ends_with_slash else rstrip("/")
    for route in self.routes:  # SECOND FULL SCAN
        match, child_scope = route.matches(redirect_scope)
        if match != Match.NONE:
            response = RedirectResponse(...)  # 307 to client
            await response(scope, receive, send)
            return
```

**Concrete cost**: Requests with trailing slash mismatch incur a full second route scan, then a 307 redirect round-trip to the client.

**Resource scarcity exposed**: **Client-side latency tolerance**. The code assumes:
- Network latency (one 307 redirect round-trip) is cheaper than server CPU (one extra route scan)
- Clients can afford the extra hop without noticing
- HTTP semantics (explicit redirect) matter more than transparency

Essentially: "Server CPU is scarce; network latency is infinite."

**Alternative (gamble on opposite scarcity)**: Clients are latency-sensitive; server has spare CPU.

```python
# Normalize path transparently at startup
def _normalize_trailing_slash(self, path):
    if not path.endswith("/") and not path.endswith(match_any_extension):
        return path  # No convention, keep as-is
    # OR canonicalize: /foo/ → /foo
    return path.rstrip("/") if path != "/" else "/"

# Single scan with canonical path
canonical_path = self._normalize_trailing_slash(route_path)
canonical_scope = {**scope, "path": canonical_path}
for route in self.routes:
    match, child_scope = route.matches(canonical_scope)
    if match == Match.FULL:
        await route.handle(canonical_scope, receive, send)
        return

# Only redirect if BOTH slash variants fail (truly no match)
await self.default(scope, receive, send)
```

**Trade-off**:
- **Old**: Explicit redirect (transparent to server logging), client sees 307, incurs latency
- **New**: Transparent rewrite (server CPU ~2% increase), client latency same, but path rewriting becomes **invisible**
  - Browser address bar still shows `/users` even if server treated it as `/users/`
  - Breaks URL identity and canonical form discovery
  - Search engines may index both `/foo` and `/foo/` as different pages (duplicate content penalty)
  - Debugging becomes harder: logs show canonicalized path, but client sees original
  - SEO/analytics break: cannot track which form users actually requested

---

### **Additional Concrete Problems**

| Problem | Scarcity Assumption | What Gets Expensive If Wrong |
|---------|---|---|
| **Parameter type mismatch** (assert in `compile_path`) | Convertor type correctness | If you typo `{id:intx}`, you get compile-time failure, not graceful handling. Assumes no bad convertor specs in production. |
| **Name-based route lookup** in `url_path_for()` | Route count budget (again) | Linear search by name: O(n) for reverse URL lookup. For 1000+ routes, URL generation becomes slow. |
| **Regex compilation** at route init | Regex cost per route | Assumes regex compilation cost is paid once, not per-request. Currently correct, but assumes regex patterns are simple (no catastrophic backtracking). |
| **Middleware composition depth** | Middleware count budget | Each middleware wraps the next: `mw1(mw2(mw3(app)))`. For 50+ middleware, stack depth becomes visible in profiler. |
| **Mount recursion depth** | Nesting budget | Deeply nested Mount hierarchies (e.g., `/api/v1/users/profile/settings/notifications/email`) create many scope updates. At 10+ levels, overhead becomes measurable. |

---

### **Conservation Law**

**What is preserved across all alternative designs?**

The **routing decision tree topology** is invariant:
1. Does this route's path pattern match the request path?
2. Does the HTTP method fit the route's allowed methods?
3. For Mount, does the remaining path recursively match a child?

This tree structure cannot be eliminated — it's fundamental to HTTP routing.

**More precisely**: Any successful request must traverse a fixed decision tree of predicates. Redesigning the implementation shuffles CPU/memory/latency costs *among* the nodes, but the **number and order of decisions remains constant**.

**Deeper conservation law**: 
$$\text{Total Cost per Request} \approx \text{Latency} + \text{Memory Overhead} + \text{Request Round-Trips}$$

You cannot reduce all three:
- **Optimize latency** → pay in memory (build index)
- **Optimize memory** → pay in latency (linear search)
- **Optimize request round-trips** → pay in opaque state threading (transparent rewrites break URL identity)

The **sum is approximately constant** because each redesign redistributes the budget, not increases total capacity.

---

### **What Remains Unmovable in 6 Months**

1. **ASGI Protocol Contract**: The `(scope, receive, send)` interface is standardized across frameworks. Scope must be dict-like. This binds all state-threading patterns. **Unmovable: ASGI is a standard; Starlette cannot unilaterally change it.**

2. **First-Match-Wins Semantics**: Route order determines precedence. This is embedded in every handler's assumptions. Changing to "best match" or "weighted match" would require rewriting all route definitions across all codebases using Starlette. **Unmovable: too much downstream code depends on it.**

3. **Parameter Conversion Timing**: Path params must convert to native types before the handler runs (not after, not pre-computed). Handlers expect `user_id: int`, not `user_id: str`. **Unmovable: baked into Python's type system and handler contracts.**

4. **Trailing Slash Ambiguity**: `/foo` and `/foo/` are semantically different in HTTP (different cache keys, different canonical URLs). Users treat them as the same. The double-scan is a permanent band-aid for bad route definitions. **Unmovable: this is a user error, not a code defect — it will still need either redirect or transparent rewrite in 6 months.**

5. **Mount Composition State Threading**: To support nested apps (Mount), you must thread `path_params`, `root_path`, `app_root_path` through scope. This cannot be factored out. **Unmovable: it's required for ASGI app composability.**

6. **URL Reversal Without Request Context**: `url_path_for()` is called from templates, not handlers — without request context. This requires a global name→route index. Linear search is unavoidable unless you pre-index (which adds memory). **Unmovable: the interface assumes no request context; you must trade latency or memory.**

7. **Regex for Path Patterns**: Even with perfect route indexing (trie, hash), the final match still needs regex/pattern matching for `{id:int}` convertor validation. You cannot escape pattern-matching overhead for the last segment. **Unmovable: baked into the path syntax.**

---

### **Summary Table**

| Problem | Old Design (Scarcity) | New Design (Opposite Gamble) | Conservation |
|---------|---|---|---|
| **Route matching** | Assumes route count ≤ 500 (latency cheap) | Assumes routes could be 10k+ (memory cheap) | Decision tree topology invariant |
| **Scope mutation** | Assumes ASGI isolation is sufficient (CPU cheap) | Assumes isolation could fail (memory cheap) | Request state must be threaded somehow |
| **Trailing slash** | Assumes network latency is free (CPU scarce) | Assumes client latency is precious (CPU abundant) | Either client round-trip OR opaque rewrite |
| **Name lookup** | Assumes routes are few enough to scan (memory cheap) | Assumes reverse lookup is hot (memory for index) | Name→route mapping must exist somewhere |

**Core insight**: Starlette routing is optimized for **small-to-medium apps with simple deployment** (hundreds of routes, single server, trusted ASGI isolation). Every resource assumption breaks at different scales.
