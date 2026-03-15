## Deep Analysis: Starlette Routing Module

I'll trace the fix→new-bug dependencies across seven concrete patterns:

---

### **Problem 1: Scope Mutation Creates Silent State Dependencies**

**Visible Problem:**
```python
scope.update(child_scope)  # Line ~190, ~280
```
Routes mutate the shared `scope` dict, making state flow opaque. Debugging requires tracing through all matched routes to understand what's in scope.

**Decision Enabled This:**
- Need to carry matched path_params + endpoint down the call stack
- Dict mutation was cheaper than creating new scope objects per route match

**Rejected Path:** Immutable scope (return new scope, don't mutate)
```python
# Would require:
new_scope = {**scope, **child_scope}
await route.handle(new_scope, receive, send)
```
**Hidden Danger:** Object churn at O(routes matched). Each mount+route nesting level creates new dicts. On deep nesting (Mount → Mount → Mount → Route), every dispatch allocates 3+ scope dicts. Memory pressure under load, GC pauses on high-concurrency servers.

**Conservation Law (Mutability Migration):** 
- **Current:** Mutation-based (debug-hard, memory-efficient)
- **Rejected:** Immutable-based (debug-easy, GC-intensive)
- **Under pressure:** Practitioner discovers GC pauses before scope aliasing bugs. Framework never shows mutation problems until two parallel requests corrupt each other's path_params (rare race condition, impossible to reproduce).

---

### **Problem 2: Partial Match Storage Selects First, Not Best**

**Visible Problem:**
```python
if match == Match.PARTIAL and partial is None:
    partial = route
    partial_scope = child_scope
```
When a route partially matches (path OK, method wrong), it's stored. If no full match exists, *the first partial is used*. No selection among multiple partials.

**Decision Enabled This:**
- Routing is O(n) linear scan; storing one partial avoids re-scanning
- Simple state: either have a partial or don't

**Rejected Path:** Collect all partials, score by specificity
```python
# Would require:
partials = [(route, child_scope, specificity_score) for match in...]
best_partial = max(partials, key=lambda x: x[2])
```
**Hidden Danger:** Specificity scoring is ambiguous. Is `/users/{id}` more specific than `/users/{id}/posts`? By parameter count? By regex complexity? By segment depth? Each scoring function creates a different tie-breaking rule, and rules *compose unexpectedly* when routes are reordered. You solve "wrong route selected" and create "route selection now non-deterministic when routes are added dynamically."

**Conservation Law (Selection Determinism Migration):**
- **Current:** Deterministic but possibly wrong (first partial)
- **Rejected:** Potentially optimal but ambiguously scored (best partial)
- **Under pressure:** Practitioner finds non-determinism first. They add a new route, tests pass locally, fail in production where route order differs (database migration, config reload). Debugging a scoring function's hidden tie-breaker is harder than fixing "wrong method" errors.

---

### **Problem 3: Reserved Parameter Name "path" Creates Namespace Collision**

**Visible Problem:**
```python
# Mount.matches():
remaining_path = "/" + matched_params.pop("path")
matched_params[key] = self.param_convertors[key].convert(value)
path_params.update(matched_params)
```
Mount steals the parameter name `"path"` to inject the remaining unmatched URL. User cannot define a route parameter named `{path:...}`.

**Decision Enabled This:**
- Need to pass remaining path down to nested routers
- Reusing path_params dict for this was simplest

**Rejected Path:** Separate field in scope
```python
child_scope = {
    "path_params": path_params,
    "remaining_path": "/" + remaining_path,  # Not in path_params
}
```
**Hidden Danger:** The `url_path_for()` contract changes. Downstream code that expects to find `path` in `path_params` (or expects it to be absent) breaks. `Route.url_path_for()` and `Mount.url_path_for()` now have different scope contracts. This is visible but creates a new problem: **cascading interface divergence**. When you fix scoping, you discover that path reconstruction code is split between three places (Route, Mount, Router) each making different assumptions about what "path_params" contains.

**Conservation Law (Namespace Pollution Migration):**
- **Current:** Single param dict, collision via naming (visible, easily worked around by renaming routes)
- **Rejected:** Separate fields, no collision (invisible coupling between url_path_for implementations)
- **Under pressure:** Practitioner discovers interface divergence, not namespace collision. They refactor to use separate fields, tests pass, then find that a custom Mount subclass broke because it still expects `path` in path_params. Namespace collision is a syntax error (caught at development); interface divergence is a semantic error (found at integration test time).

---

### **Problem 4: Regex Compilation at Route Init Bakes Static Paths**

**Visible Problem:**
```python
# Route.__init__:
self.path_regex, self.path_format, self.param_convertors = compile_path(path)
```
Each route compiles its regex once at initialization. Regex objects are frozen. If path pattern needs to change (dynamic routing, feature flags), you must re-create the Route object.

**Decision Enabled This:**
- Regex compilation is expensive; do it once
- Routes are typically static during server lifetime

**Rejected Path:** Lazy compilation or regex caching
```python
# Lazy: compile regex on first match()
def matches(self, scope):
    if not hasattr(self, '_compiled'):
        self._compiled = compile_path(self.path)
    return self._compiled.match(route_path)

# Or: global cache
REGEX_CACHE = {}
regex = REGEX_CACHE.setdefault(self.path, re.compile(...))
```
**Hidden Danger:** 
- **Lazy:** First request pays compilation cost. Under load spikes, first request to a rarely-used route becomes a latency outlier. Second issue: if route is never used, you pay no cost (good), but if routes are hot-reloaded, you have stale compiled regexes.
- **Global cache:** Cache invalidation becomes a problem. Add a new route dynamically, but old Route objects still use cached regexes. Or: regex cache grows unbounded if routes are ephemeral (WebSocket handlers, request-scoped routes).

**Conservation Law (Compilation Timing Migration):**
- **Current:** Eager (startup overhead, all regexes ready, no request-time surprises)
- **Rejected:** Lazy (first-request latency spike, unbounded cache, stale regexes on reload)
- **Under pressure:** Practitioner discovers this in load tests. Eager compilation adds 50ms to server startup (visible, documented). Lazy compilation creates a request that takes 500ms while regex compiles (invisible, not in critical path until peak load, blames "database slow" instead). The second-order issue: they optimize by pre-compiling in a warmup phase, but then the lazy code is never exercised in tests.

---

### **Problem 5: GET→HEAD Auto-Addition Hides Method Support**

**Visible Problem:**
```python
if "GET" in self.methods:
    self.methods.add("HEAD")
```
Defining a GET route implicitly supports HEAD. No explicit HEAD handler exists. The framework strips the response body for HEAD requests.

**Decision Enabled This:**
- HTTP spec says HEAD = GET + no body
- Magic makes REST easier (users don't think about HEAD)

**Rejected Path:** Make HEAD explicit or require opt-out
```python
# A) Explicit: require @route(methods=["GET", "HEAD"])
# B) Opt-out: methods=["GET"], auto_head=False
```
**Hidden Danger:** 
- Custom middleware that assumes HEAD routes don't exist breaks. Example: content-length middleware that treats HEAD differently will be bypassed by the auto-addition, leading to silent 200 responses with Content-Length but no body (correct by HTTP spec, but custom middleware never gets to see the HEAD request to optimize it).
- Worse: User adds a custom HEAD handler because they didn't know GET auto-adds it. Two handlers now fight over the same method. Whose runs? This creates a hidden coupling: the order of middleware registration determines which HEAD handler wins.

**Conservation Law (Method Magic Migration):**
- **Current:** Implicit (users don't define HEAD, spec compliant, hidden coupling with middleware)
- **Rejected:** Explicit (users must define HEAD, breaks REST automation, visible coupling)
- **Under pressure:** Practitioner discovers this when implementing custom response streaming for HEAD. They add a HEAD-specific handler, tests pass in development (no concurrent requests), fail in production (race condition between implicit HEAD handler from GET and explicit HEAD handler). They file a bug: "HEAD handler runs twice" — actually, both handlers run in undefined order.

---

### **Problem 6: redirect_slashes Double-Iterates Routes**

**Visible Problem:**
```python
# Router.app():
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match == Match.FULL:
        return
if redirect_slashes and route_path != "/":
    redirect_scope = dict(scope)
    redirect_scope["path"] = redirect_scope["path"].rstrip("/") or redirect_scope["path"] + "/"
    for route in self.routes:  # <-- Second iteration
        match, child_scope = route.matches(redirect_scope)
```
If no route matches and `redirect_slashes=True`, routes are scanned again with modified path.

**Decision Enabled This:**
- Trailing slash normalization is a UX feature (many frameworks do this)
- Second iteration is only on no-match (not on critical path normally)

**Rejected Path:** Normalize paths at request ingress or in regex
```python
# Option A: Normalize before routing
route_path = route_path.rstrip("/") or "/"
# Then match once

# Option B: Regex matches both /foo and /foo/
path_regex = re.compile(f"^{pattern}/?$")  # Optional trailing slash
```
**Hidden Danger:**
- **Option A (normalize early):** Mounts with trailing slashes fail. `/api/v1/` mounted on `/api` should strip the `/api` part, leaving `v1/` for nested routing. Normalize early and you lose this. Also breaks relative URLs if the mount itself has a slash.
- **Option B (regex both):** Regex becomes ambiguous. Does `/foo` match `/foo` or `/foo/`? Both. url_path_for now has to choose which to generate. Also, the double-iteration optimization is lost — every request pays the cost of more complex regex.

**Conservation Law (Normalization Coupling Migration):**
- **Current:** Deferred (simple regex, double-iteration on edge case, visible latency spike on missing trailing slash)
- **Rejected:** Early (complex regex or pre-processing, breaks mount semantics, invisible coupling with mount paths)
- **Under pressure:** Practitioner discovers latency spike under load with many 404s (redirect attempts). Or: they notice that mounted apps with trailing slash semantics break. The first is visible and easy to fix (cache redirects, add metrics). The second is invisible until a specific API design is attempted.

---

### **Problem 7: url_path_for Requires All Parameters Upfront**

**Visible Problem:**
```python
# Route.url_path_for():
expected_params = set(self.param_convertors.keys())
if seen_params != expected_params:
    raise NoMatchFound(name, path_params)
```
Building a URL requires providing *all* path parameters. No optional parameters, no partial construction, no defaults.

**Decision Enabled This:**
- Simplest validation: exact set match
- No ambiguity in URL generation

**Rejected Path:** Optional parameters with defaults
```python
# Hypothetical
params_with_defaults = {
    "id": (convertor, None),  # Optional, defaults to None
    "version": (convertor, "v1"),  # Optional, defaults to "v1"
}
```
**Hidden Danger:** URL generation becomes ambiguous. Should `url_path_for("user", id=123)` return `/users/123/` or `/users/123/v1/`? What if the user meant version? You add a priority rule (positional params first), but then somebody expects (version first). URL generation now has implicit conventions that are invisible in the type signature.

Worse: building relative URLs becomes hard. You want to build `/users/{id}/posts` where {id} is filled in by parent Mount, but {user_version} is filled by your code. There's no way to express "this URL has some parameters already in scope". You must track manual state, creating coupling.

**Conservation Law (Parameter Completeness Migration):**
- **Current:** Strict (all required, unmissable validation, explicit intent)
- **Rejected:** Loose (some optional, ambiguous defaults, implicit coupling with scope)
- **Under pressure:** Practitioner discovers this when building nested Mount URL generation. They want to create a URL to a nested route but only have some of the parameters. Solution: pull remaining params from `scope["path_params"]`, creating hidden state coupling. Now url_path_for behavior depends on scope state (invisible). Tests pass in isolation (where they manually provide all params), fail in integration (where scope is pre-filled by outer routes).

---

## Synthesis: The Routing Impossibility

**The law:** All problems migrate from **runtime visibility (semantic errors) to static invisibility (structural coupling)** as you fix them.

| Problem | Visible Now | Hidden After Fix |
|---------|-------------|------------------|
| Scope mutation | Hard to debug state | GC pauses, allocation overhead |
| Partial selection | Wrong route picked | Tie-breaking rules non-deterministic |
| Reserved "path" param | Naming conflict | Divergent url_path_for contracts |
| Static regex | Slow startup or reload | Stale regexes, unbounded caches |
| Implicit HEAD | Hidden coupling | Middleware ordering determines behavior |
| Double-iteration on 404 | Latency spike | Breaks Mount trailing-slash semantics |
| url_path_for strict params | Missing param error (clear) | Implicit scope coupling (invisible) |

**Root Impossibility:** You cannot simultaneously have:
1. **Simple dispatch** (linear route scan)
2. **Optimal matching** (best-partial selection)
3. **Flexible scoping** (param defaults, optional parts)
4. **Debuggable state** (no mutation)
5. **Static compilation** (no lazy/cache issues)

The current design trades: Chooses **dispatch simplicity** and **static compilation**, sacrifices **optimal matching** and **debuggable state**.

**What practitioners discover first under pressure:**
- **In tests:** Scope mutation bugs (aliasing between requests). *Symptoms:* Race condition only visible with concurrent requests, impossible to reproduce consistently.
- **In load tests:** GC pressure (if you fix mutation with immutable scope). *Symptoms:* P99 latency spike, blames "garbage collection."
- **In integration:** url_path_for scope coupling. *Symptoms:* Works in unit tests, breaks in full stack. Path params mysteriously missing.
- **In operations:** Latency spike on 404s (redirect_slashes). *Symptoms:* Every request to missing endpoint takes 2x routing time.

**The most likely to hit first:** Scope mutation race condition, because the code *looks simple* (no deep nesting, tests pass), but breaks under realistic concurrency (3+ concurrent long-lived requests with overlapping routing delays).
