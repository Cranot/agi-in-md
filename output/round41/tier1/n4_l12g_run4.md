# L12G Structural Analysis: Starlette routing.py

---

## PHASE 1 — STRUCTURAL ANALYSIS

### Three Properties This Code Simultaneously Claims

1. **Uniform Matching Protocol**: All routes implement `BaseRoute.matches()` returning `(Match, scope)` — a single polymorphic interface for `Route`, `Mount`, and any custom route type.

2. **Path Segment Isolation**: `Mount` strips its matched prefix via `root_path` accumulation and passes only `remaining_path` to children — each level operates on isolated path segments.

3. **Priority-Ordered Dispatch**: `Router.app()` iterates routes in definition order, taking the first FULL match or first PARTIAL match — priority is encoded as list position.

### Proof These Cannot Coexist

The conflict emerges in **method-aware partial matching across mount boundaries**:

```
Scenario:
  Mount("/api", routes=[
      Route("/users", endpoint, methods=["GET"]),  # route 0
  ])
  Route("/api/users", other, methods=["POST"])     # route 1

Request: POST /api/users
```

- Property 1 requires `Mount.matches()` to return only FULL/PARTIAL/NONE
- Property 2 requires `Mount` to delegate to children for method matching  
- Property 3 scans routes in order: `Mount` at position 0 matches first

**The contradiction**: `Mount.matches()` returns `FULL` (path matched), but the method mismatch exists in its CHILD. The Router sees FULL from Mount and dispatches — the 405 "Method Not Allowed" only fires if the child's routes fail. But if route 1 exists at the Router level with the correct method, it's never checked because Mount already claimed the FULL match.

### Conservation Law

```
Routing Specificity × Priority Simplicity = Constant
```

- As routing specificity increases (method-aware priority), priority simplicity decreases (O(n) scan becomes O(n) collect + O(m) rank)
- The code maximizes priority simplicity (first-match-wins) at the cost of routing specificity (method-aware priority)

### Concealment Mechanism

**Scatter-and-Specialize**: The method-matching logic is scattered across three locations:
1. `Route.matches()` returns `PARTIAL` for method mismatch (lines 146-147)
2. `Router.app()` stores first PARTIAL (lines 278-280)
3. `Mount.matches()` never considers method — always returns FULL for path match

The specialization conceals that method-awareness is **incomplete** — it works for `Route` but dissolves at `Mount` boundaries. The code *appears* to handle 405s (PARTIAL → 405) but only within flat route lists.

### Improvement That Recreates the Problem Deeper

```python
# Collect ALL candidates with match scores, then rank
class Router:
    async def app(self, scope, receive, send):
        candidates = []
        for route in self.routes:
            match, child_scope = route.matches(scope)
            candidates.append((match, route, child_scope))
        
        # Rank: method-aware FULL > method-agnostic FULL > PARTIAL
        winner = self._select_best_match(candidates, scope["method"])
        # ...
```

**This recreates the problem at a deeper level**: The ranking function must now compare routes across mount boundaries. But mounts have already mutated their child scopes (`root_path`, `path_params`). To compare fairly, the ranking function needs the *pre-mutation* state — requiring either:
- Scope reconstruction (complexity explosion)
- Lazy scope mutation (defers the problem to selection time)

The conservation law holds: we've traded O(n) dispatch simplicity for O(n) collection + O(m) ranking complexity.

---

## PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | Verification |
|-------|----------------|------------|--------------|
| Router uses first-match-wins | STRUCTURAL | 1.0 | Lines 273-285: explicit `partial is None` guard, `return` on first FULL |
| Mount.matches() returns FULL for path match | STRUCTURAL | 1.0 | Lines 180-194: no method check, always returns `Match.FULL` |
| Route.matches() returns PARTIAL for method mismatch | STRUCTURAL | 1.0 | Lines 146-147: explicit `if self.methods and scope["method"] not in self.methods` |
| Redirect fires before default | STRUCTURAL | 1.0 | Lines 288-301: redirect loop before `await self.default` |
| Middleware wraps in reversed order | STRUCTURAL | 1.0 | Lines 112-114, 159-161, 255-258: `reversed(middleware)` |
| `request_response` has unreachable code | STRUCTURAL | 1.0 | Lines 21-26: nested `async def app` shadows outer, never called |
| Method-aware priority would fix dispatch | CONTEXTUAL | 0.7 | Requires external verification that 405-before-404 is desired behavior; current behavior may be intentional |
| Scope isolation at mount boundaries | STRUCTURAL | 1.0 | Lines 186-192: explicit `child_scope` construction with `root_path` accumulation |
| PARTIAL means "path matched, method didn't" | STRUCTURAL | 1.0 | Only `Route.matches()` returns PARTIAL, only on method mismatch |
| First PARTIAL wins, not best PARTIAL | STRUCTURAL | 1.0 | Line 278: `if match is Match.PARTIAL and partial is None` |

---

## PHASE 3 — SELF-CORRECTION

**Claim revised**: "Method-aware priority would fix dispatch" → **UNVERIFIABLE FROM SOURCE**

The code does not specify whether the current behavior (first PARTIAL wins) is a bug or feature. RFC 7231 says 405 should be returned when method isn't allowed — but which route's methods take priority when paths overlap? This requires design intent, not source code.

**Removed from conclusions**: The recommendation to implement method-aware ranking is a design proposal, not a source-grounded defect.

---

## FINAL OUTPUT

### Conservation Law

```
Routing Specificity × Priority Simplicity = Constant
```

The system maximizes priority simplicity (O(n) first-match-wins) at the cost of routing specificity (method-aware dispatch across nested routes).

### Corrected Defect Table

| # | Location | Severity | Issue | Classification |
|---|----------|----------|-------|----------------|
| 1 | Lines 21-26 | Fixable | Dead code: nested `async def app` shadows outer function, never called | STRUCTURAL |
| 2 | Lines 278-280 | Structural | First-PARTIAL-wins: routes defined later with correct method are ignored | STRUCTURAL |
| 3 | Lines 180-194 | Structural | Mount.matches() ignores method, always returns FULL — method validation deferred to children | STRUCTURAL |
| 4 | Lines 146-147 | Structural | PARTIAL semantics overloaded: means "path matched but method didn't" but only for Route, not Mount | STRUCTURAL |
| 5 | Lines 288-301 | Fixable | Redirect attempt happens after PARTIAL match stored — method-mismatched route with trailing slash won't redirect to correct method | STRUCTURAL |
| 6 | Scope mutation | Structural | `scope.update(child_scope)` mutates shared state — routes cannot be re-matched after mutation | STRUCTURAL |

### Verified Structural Findings

1. **PARTIAL matching is first-come-first-served**: Line 278's `partial is None` guard ensures the first PARTIAL match wins, even if a later route would be a better method match.

2. **Mount bypasses method validation**: `Mount.matches()` returns FULL on path match alone. Method validation is delegated to the child app, which may not exist or may not validate.

3. **Scope mutation prevents re-matching**: After `scope.update(child_scope)` at line 276, the original scope is lost. Any re-dispatch would see mutated path_params and root_path.

4. **Dead code in request_response**: The nested `async def app(scope, receive, send)` at lines 23-25 is unreachable — shadowed by the outer `app` at line 22.
