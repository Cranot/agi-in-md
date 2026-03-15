# Structural Analysis: Starlette Routing

## Executive Summary

This is an ASGI routing implementation handling path matching, parameter extraction, nested mounting, and request dispatch. Three interconnected systems: **pattern compilation** (regex + convertors), **match resolution** (three-state enum with partial matching), and **scope propagation** (state accumulation down the route tree).

---

## 1. Conservation Laws

**Conservation Law 1: Path Context Completeness**
```
route_specificity × match_ambiguity = constant
```
Every route that matches more specifically (more params, tighter regex) creates more ambiguity in what remains unmatched. The `{path:path}` catch-all in Mount is the extreme case: matches everything, tells you nothing about what comes next.

**Conservation Law 2: Scope Mutation vs Route Depth**
```
child_scope_additions ∝ parent_scope_preservation
```
Each level can either add new scope keys OR preserve parent context — but aggressive mutation at one level forces defensive copying upstream. The `path_params.update()` pattern is the compromise: inherited dict with local mutations.

**Conservation Law 3: Middleware Wrapping vs Dispatch Transparency**
```
wrapping_depth × handler_visibility = constant
```
More middleware layers = harder to trace what actually handles the request. The `reversed(middleware)` pattern creates an execution stack invisible at any single point.

---

## 2. Structural Defects

### Critical Issues

| Location | Defect | Severity | Type |
|----------|--------|----------|------|
| `request_response:7-11` | **Nested `async def app` shadows outer** — inner function never used, outer calls itself recursively | **CRITICAL** | Fixable |
| `Route.matches:14-17` | `path_params` from scope can be mutated by multiple route matches in same request if match fails later | MODERATE | Structural |
| `Mount.url_path_for:8-20` | Complex branching logic with early returns makes partial-match debugging impossible | MODERATE | Structural |
| `Router.app:27-35` | `partial` capture only keeps FIRST partial match, discarding potentially better matches | MODERATE | Structural |

### The Nested Function Bug (Lines 7-11)

```python
async def app(scope, receive, send):
    request = Request(scope, receive, send)

    async def app(scope, receive, send):  # SHADOWS OUTER
        response = await f(request)
        await response(scope, receive, send)

    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
```

The inner `app` shadows the outer. `wrap_app_handling_exceptions` receives the **outer** `app` (a closure over `request`), which calls... what? This is either dead code or infinite recursion depending on `wrap_app_handling_exceptions` implementation. The inner function is unreachable.

---

## 3. Concealment Mechanisms

### Mechanism 1: Match State Drift
The `Match` enum suggests discrete states (NONE/PARTIAL/FULL), but actual behavior is continuous. A route can return `FULL` with method mismatch caught elsewhere, or `PARTIAL` that never gets a second chance. The three-state abstraction conceals a **fourth implicit state**: "matched but deferred."

### Mechanism 2: Scope as Communication Channel
`scope.update(child_scope)` makes the route tree communicate through mutation, not return values. This is efficient but conceals the dataflow — you can't trace what a route added without watching mutation happen. Side effects replace explicit contracts.

### Mechanism 3: Mount Path Prefix Stripping
`Mount.matches` strips the matched prefix and rewrites `root_path`:
```python
"root_path": root_path + matched_path
```
This is elegant but conceals the original request path. Downstream handlers see `root_path` as truth, but debugging requires reconstructing the original path from scattered pieces.

### Mechanism 4: Redirect Loop Potential
The `redirect_slashes` logic creates a redirect then immediately tries to match again. But if routes are added dynamically or middleware modifies scope, the redirect target may not exist — creating a client-side redirect loop invisible to the router.

---

## 4. Invariants (What Never Changes)

1. **Path params accumulate but never delete** — once a param is in `path_params`, it persists through all nested mounts
2. **First full match wins** — route order is semantically significant, not just declarative
3. **Middleware wraps in reverse order** — last in stack is first in execution
4. **Method 405 requires path match first** — you can't return "method not allowed" for a path that doesn't exist

---

## 5. Impossibility Results

**Cannot simultaneously have:**
1. Fast O(1) path lookup AND arbitrary parameter positions
2. Route independence AND path parameter inheritance (must couple via scope mutation)
3. Middleware transparency AND middleware that modifies scope (wrapping conceals mutation)
4. Partial match recovery AND first-match-wins semantics (partial is captured, not queued)

The design chose: **(2) inheritance via mutation**, **(4) single partial capture**, accepting the debugging complexity in exchange for simplicity.

---

## 6. Generative Improvement (and why it fails)

**Proposed fix:** Replace scope mutation with explicit return of `(scope_delta, handler)` tuples, threading state explicitly.

**Why it recreates the problem:**
Every call site now needs to merge `scope_delta`. The `Router.app` loop becomes:
```python
current_scope = scope
for route in self.routes:
    match, delta, handler = route.matches(current_scope)
    if match is Match.FULL:
        current_scope = merge(current_scope, delta)
        await handler(current_scope, receive, send)
```

This is exactly what `scope.update(child_scope)` does, but now we've made the mutation visible without preventing it. The "fix" exposes the coupling without reducing it. **The conservation law holds: explicit state threading = code duplication proportional to match points.**

---

## 7. Meta-Conservation Law

The analysis itself conceals: **I have focused on structural properties, not runtime behavior.** No mention of actual performance characteristics, concurrency under load, or real-world failure modes.

The conservation law of this analysis:
```
structural_depth × operational_coverage = constant
```

To go deeper on code structure, I necessarily abstracted away runtime dynamics. A performance profiling analysis would find different conservation laws (latency × throughput, memory × connection count).
