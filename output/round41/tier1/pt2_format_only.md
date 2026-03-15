# Structural Analysis: Starlette routing.py

## Step 1: Name Three. Prove Incompatible. Which Sacrificed. Conservation Law.

**Three properties the routing system claims:**

1. **Composability** — Mount points nest arbitrarily deep with path parameters threading through each layer (`path_params.update(matched_params)` propagates state)
2. **Single-pass matching** — O(n) route traversal with early termination on FULL match, no backtracking
3. **Partial match semantics** — Routes can return PARTIAL (method mismatch) and Router retains for fallback handling

**Proof of incompatibility:**

Composability requires scope mutation at each nesting level. Partial semantics requires deferring commitment until all levels resolve. Single-pass requires immediate commitment on first acceptable match.

The contradiction manifests in `Router.app()` lines ~310-325:

```python
partial = None
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match is Match.FULL:
        scope.update(child_scope)  # COMMITS immediately
        await route.handle(scope, receive, send)
        return
    elif match is Match.PARTIAL and partial is None:
        partial = route
        partial_scope = child_scope  # BUFFERS for later
```

When a Mount returns PARTIAL at outer level, Router buffers it. But if that Mount contains nested routes that would FULL-match, Router never explores them—the PARTIAL at outer level "wins" over potential FULL at inner level.

**What's sacrificed: Composability.**

Nested route resolution is sacrificed for single-pass performance with partial fallback. The system can't compose partial states across nesting levels.

**Conservation Law:**
```
Matching Passes × Flexibility = Constant
```

Single pass = single-level flexibility. Multi-level flexibility = multiple passes (or state explosion).

---

## Step 2: How Input Conceals the Sacrifice

**Mechanism: Optimistic Scope Mutation**

The concealment operates through the `scope.update(child_scope)` pattern appearing in three places:

1. `BaseRoute.__call__()` line ~95
2. `Route.matches()` returning child_scope with path_params  
3. `Mount.matches()` constructing nested child_scope

**The concealment:** Scope mutation happens *before* the system knows if the match will ultimately succeed. This creates the illusion that nested matching is stateless—"we just pass scope down"—but actually the parent has already mutated scope based on a match the child might reject.

**User-facing symptom:** A route like `Mount("/api", routes=[Route("/users", endpoint)])` will 404 on `POST /api/users` if the Mount matched partially (e.g., wrong method constraint at Mount level) even though the inner Route would accept POST. The user sees "route not found" when the route exists—they just hit the composability sacrifice.

**Why it's hidden:** The API presents matching as a pure predicate (`matches(scope) -> (Match, child_scope)`), suggesting mathematical cleanliness. The imperative mutation (`scope.update()`) happens in control-flow locations users don't read (`__call__`, `handle`).

---

## Step 3: Engineer Simplest Fix. Prove Fix Recreates Problem Deeper.

**Simplest fix: Deferred Scope Commitment**

```python
async def app(self, scope, receive, send):
    # ... matching logic unchanged ...
    
    for route in self.routes:
        match, child_scope = route.matches(scope)
        if match is Match.FULL:
            # FIX: Don't mutate original scope, pass child_scope explicitly
            await route.handle(child_scope, receive, send)  # No mutation
            return
```

Remove `scope.update(child_scope)` from `BaseRoute.__call__()` and pass child_scope directly to handlers.

**Proof this recreates the original problem deeper:**

Handlers expect `scope["path_params"]` to contain accumulated params from all nesting levels. Without mutation, inner handlers only see their own params—`Mount("/users/{user_id}", routes=[Route("/posts", ...)])` loses `user_id` at the Route level.

To fix THIS, you need either:
1. **Explicit param threading** — every handler signature must accept path_params argument
2. **Scope reconstruction** — re-build scope at each level by re-matching parent routes
3. **State accumulation object** — introduce a new `PathContext` that accumulates across levels

Option 1 breaks every existing handler. Option 2 violates single-pass (now O(n²) worst case). Option 3 introduces the SAME matching-state problem the fix was supposed to solve—just wrapped in a new class.

**The fix moves the defect from "implicit scope corruption" to "explicit interface incompatibility."** Same structural impossibility, different manifestation level.

---

## Step 4: Apply to Own Law. What Does Analysis Conceal?

My conservation law: **Matching Passes × Flexibility = Constant**

**What this framing conceals:**

The law assumes "passes" and "flexibility" are the real variables. They're not. They're derivatives of a deeper trade-off:

```
State Buffer Size × Commitment Speed = Constant
```

- "Single-pass" = commit immediately, buffer nothing
- "Flexibility" = buffer partial states, commit later

The REAL variable is: **how much state must be buffered before commitment?**

This reveals what my analysis concealed: **The routing problem is a state management problem, not a matching problem.**

The regex compilation, path format strings, param convertors—these are all optimizations for the happy path. The actual complexity lives in: "What do we remember when matching fails partially?"

**Meta-conservation law:**
```
Analytical Frame Power × Frame Blindness = Constant
```

My "passes × flexibility" frame is powerful for understanding the matching loop. It blinds me to the state-buffer interpretation. A "state × commitment" frame would be powerful for understanding storage/reconstruction trade-offs. It would blind me to the route-structure implications.

---

## Step 5: Harvest Every Defect

| # | Location | Defect | Severity | Type |
|---|----------|--------|----------|------|
| 1 | `request_response()` L22-28 | Nested `async def app` shadows outer `app` — inner never registered with exception wrapper | **Critical** | Structural bug |
| 2 | `compile_path()` L59-60 | `duplicated_params` check happens AFTER param_convertors assignment — first occurrence wins silently, could confuse debugging | Low | Fixable |
| 3 | `Mount.__init__()` L162 | `self.path = path.rstrip("/")` — empty string `""` becomes `""` but `"/"` also becomes `""`, inconsistent with assert on L159 | Medium | Fixable |
| 4 | `Mount.matches()` L178-180 | `remaining_path` calculation uses `matched_params.pop("path")` — mutates dict that might be referenced elsewhere | Medium | Fixable |
| 5 | `Router.app()` L295-300 | `scope["router"] = self` mutates input scope — caller's scope polluted | Low | Design choice |
| 6 | `Router.app()` L312-313 | `partial_scope` captured but `partial.handle()` uses mutated `scope` not `partial_scope` — partial path_params lost | **High** | Structural bug |
| 7 | `Router.app()` L320-335 | redirect_slashes iterates routes TWICE after initial match loop — O(2n) not O(n), performance promise violated | Medium | Fixable |
| 8 | `Router.__init__()` L244-256 | Three different lifespan handling branches with deprecation warnings — maintenance burden, should consolidate | Low | Technical debt |
| 9 | `BaseRoute.__call__()` L91-98 | Scope mutation before handle means middleware sees different scope than matcher — debugging difficulty | Medium | Design choice |
| 10 | `Route.matches()` L127 | `path_params = dict(scope.get("path_params", {}))` copies but then mutates with update — shallow copy, nested structures shared | Low | Fixable |
| 11 | `Mount.url_path_for()` L195-212 | Complex branching with early returns — `path_kwarg` handling inconsistent between branches | Medium | Fixable |
| 12 | `replace_params()` L35 | Modifies `path_params` in-place (`pop`) — caller's dict mutated unexpectedly | Medium | Fixable |
| 13 | `Router.not_found()` L263-270 | Checks `"app" in scope` to decide exception vs response — implicit contract, not documented | Low | Documentation |
| 14 | `Route.__init__()` L116-117 | `self.methods.add("HEAD")` when GET present — implicit, no way to disable | Low | Design choice |
| 15 | `compile_path()` L48 | `assert convertor_type in CONVERTOR_TYPES` — assertion in production code, should raise ValueError | Medium | Fixable |

### Hidden Assumptions

1. **Scope is mutable state owned by Router** — callers shouldn't retain references
2. **Route order = priority** — first FULL match wins, no priority scoring
3. **Partial matches are single-level** — no nested partial state composition
4. **Path params are flat dictionaries** — no namespacing for nested mounts with same param names
5. **Middleware wraps outward** — `reversed(middleware)` means last in list is innermost wrapper

### Predictions

| Prediction | Confirm | Refute | Confidence |
|------------|---------|--------|------------|
| Defect #1 causes silent handler failures in production with exception-wrapping middleware | Add exception in handler, check if wrapper catches | — | 90% |
| Defect #6 causes 405 responses to lose path params in handlers | Mount with path param + method constraint + POST to GET-only route | Same test with GET succeeds with params | 95% |
| Redirect logic (#7) causes measurable latency on 404-heavy workloads | Benchmark 1000 404s vs 1000 matches | Latency difference < 5% | 80% |
| Nested mounts with same param name (e.g., `{id}` at two levels) causes shadowing | Create Mount("/org/{id}", routes=[Mount("/user/{id}")]) | Both params accessible in innermost handler | 85% |
| Moving scope mutation after FULL match check would break <5% of user code | A/B test on real Starlette apps | >20% breakage | 70% |

---

**Conservation law of this file:**
```
Route Expressiveness × Match Simplicity = Constant
```

Every path feature (optional params, type convertors, host matching) adds a branch in `matches()`. The file stays readable only by accepting limited expressiveness (no regex in paths, no conditional matching, no priority overrides).
