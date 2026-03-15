# L12G Analysis: Starlette routing.py

## PHASE 1 — STRUCTURAL ANALYSIS

### Three Properties Claimed

1. **Clean Match Semantics** — FULL/PARTIAL/NONE distinction is meaningful; PARTIAL means "path matched but method didn't"
2. **Scope Isolation Per Attempt** — Each route's match attempt is independent
3. **First-Match-Wins with Fallback** — Use first FULL, else first PARTIAL, else default

### Proof They Cannot Coexist

```python
# Router.app() lines 298-310:
partial = None
for route in self.routes:
    match, child_scope = route.matches(scope)  # child_scope CONTAINS path_params
    if match is Match.FULL:
        scope.update(child_scope)  # Clean case
        await route.handle(scope, receive, send)
        return
    elif match is Match.PARTIAL and partial is None:
        partial = route
        partial_scope = child_scope  # STORES path_params from PARTIAL match

# Later:
if partial is not None:
    scope.update(partial_scope)  # Applies path_params from wrong route
```

**The conflict:** `Route.matches()` (lines 169-182) populates `child_scope` with `path_params` BEFORE checking if method matches. When method doesn't match, it returns `Match.PARTIAL` with `child_scope` already containing those path parameters.

If Route A matches path `/users/{id}` with method GET, and Route B matches path `/users/{id}` with method POST:
- Request: POST `/users/123`
- Route A (GET): Returns PARTIAL with `path_params = {"id": "123"}`
- Route B (POST): Returns FULL with `path_params = {"id": "123"}`

This works. But consider:
- Request: DELETE `/users/123`
- Route A (GET): Returns PARTIAL with `path_params = {"id": "123"}`
- Route B (POST): Returns PARTIAL with `path_params = {"id": "123"}`
- No FULL match → `scope.update(partial_scope)` applies Route A's params

The params happen to be identical here, but with different route definitions:

```python
Route("/api/{version}/users/{id}", endpoint=handler, methods=["GET"])
Route("/v{version}/users/{user_id}", endpoint=handler, methods=["POST"])
```

Request: DELETE `/api/v1/users/123`
- Route A: PARTIAL with `{"version": "v1", "id": "123"}`
- Route B: No match (different path pattern)

Result: Scope polluted with `{"version": "v1", "id": "123"}` even though the handler that gets called is `not_found`.

### Conservation Law

**Parameter Cleanliness × Matching Precision = Constant**

The more precisely you distinguish match types (FULL vs PARTIAL), the more parameter contamination you introduce into the scope that reaches handlers.

### Concealment Mechanism

The `Match` enum creates an illusion of clean separation. The code LOOKS like it's asking "did this route match?" but it's actually asking "did this route match?" while simultaneously mutating state. The `child_scope` construction happens unconditionally; the match level only affects return value, not side effects.

### Improvement That Recreates The Problem Deeper

**Fix:** Defer `path_params` construction until after method check:

```python
def matches(self, scope):
    if scope["type"] == "http":
        match = self.path_regex.match(get_route_path(scope))
        if match:
            # DEFER: Don't build path_params yet
            if self.methods and scope["method"] not in self.methods:
                # Build minimal child_scope for PARTIAL
                return Match.PARTIAL, {"endpoint": self.endpoint}
            # NOW build full path_params
            matched_params = match.groupdict()
            for key, value in matched_params.items():
                matched_params[key] = self.param_convertors[key].convert(value)
            path_params = dict(scope.get("path_params", {}))
            path_params.update(matched_params)
            return Match.FULL, {"endpoint": self.endpoint, "path_params": path_params}
    return Match.NONE, {}
```

**Deeper problem:** Now `partial_scope` lacks `path_params`, but `not_found` handler might want them for error messages. The `NoMatchFound` exception (line 12) includes param names. We've traded parameter contamination for information loss. New conservation law: **Debug Richness × Scope Purity = Constant**.

---

## PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | Verification Needed |
|-------|----------------|------------|---------------------|
| Match enum has NONE/PARTIAL/FULL | STRUCTURAL | 1.0 | Lines 17-21 — SAFE |
| Router iterates routes, first FULL wins | STRUCTURAL | 1.0 | Lines 298-305 — SAFE |
| PARTIAL stored with child_scope | STRUCTURAL | 1.0 | Lines 306-307 — SAFE |
| Route.matches builds path_params before method check | STRUCTURAL | 1.0 | Lines 169-182 — SAFE |
| path_params from PARTIAL pollutes final scope | STRUCTURAL | 1.0 | Lines 313-315 — SAFE |
| Different route patterns can have different param names | STRUCTURAL | 1.0 | compile_path() creates param_convertors dict — SAFE |
| This causes actual bugs in practice | CONTEXTUAL | 0.7 | Need: runtime test with conflicting route patterns |
| not_found handler might want path_params | CONTEXTUAL | 0.6 | Need: check if NoMatchFound uses them (it references path_params in __init__) |
| Improvement recreates problem with debug richness | CONTEXTUAL | 0.5 | Need: verify NoMatchFound behavior with empty params |

**Low-confidence claims examined:**

- **"This causes actual bugs in practice" (0.7)**: The code path exists. Whether it triggers depends on route configuration. If wrong: the structural issue remains but may be rare in practice.
- **"not_found handler might want path_params" (0.6)**: Line 12 shows `NoMatchFound` receives `path_params.keys()`. But `not_found` (lines 270-279) doesn't use path_params directly. If wrong: the improvement's "deeper problem" is weaker.
- **"Improvement recreates problem" (0.5)**: Depends on whether NoMatchFound error messages matter. If wrong: the improvement is cleaner than claimed.

---

## PHASE 3 — SELF-CORRECTION

**DOWNGRADE:** "This causes actual bugs in practice" — The structural flaw is proven, but whether it manifests depends on route configuration. The CLAIM of contamination is STRUCTURAL; the CLAIM of "bugs" is speculative.

**DOWNGRADE:** "not_found handler might want path_params" — Checking `not_found` (lines 270-279): it does NOT use path_params. NoMatchFound is raised by `url_path_for`, not by routing. The improvement's "deeper problem" is WEAK.

**VERIFIED:** The scope contamination is real and STRUCTURAL. But the practical impact is narrower than initially claimed.

---

## FINAL OUTPUT

### Conservation Law
**Parameter Cleanliness × Matching Precision = Constant**

The `Route.matches()` method cannot simultaneously:
- Build rich `child_scope` with `path_params` (needed for handlers)
- Distinguish FULL from PARTIAL cleanly (needed for routing semantics)
- Isolate match attempts (needed for predictable behavior)

The code chooses richness + distinction, sacrificing isolation.

### Corrected Defect Table

| Location | Severity | Type | Defect | Evidence |
|----------|----------|------|--------|----------|
| `Route.matches()` L169-182 | MEDIUM | STRUCTURAL | Path parameters populated before method check; PARTIAL matches carry stale params | `child_scope` built at L177-180, method check at L181 |
| `Router.app()` L306-307 | MEDIUM | STRUCTURAL | PARTIAL scope stored without validation that params are relevant to fallback | `partial_scope = child_scope` captures any params |
| `Router.app()` L313-315 | LOW | STRUCTURAL | Scope mutation from non-matching route when no FULL match exists | `scope.update(partial_scope)` applies stored params |
| `Mount.url_path_for()` L237-249 | LOW | STRUCTURAL | Complex delegation logic with silent failure (catches NoMatchFound, continues) | `try: ... except NoMatchFound: pass` pattern |
| `request_response()` L28-36 | LOW | STRUCTURAL | Nested async function `app` defined inside outer `app` — name shadowing | Line 31 defines `async def app` inside line 29's `async def app` |
| `Router.__init__` L262 | INFO | FIXABLE | Deprecated lifespan patterns warned but still supported — maintenance debt | Lines 256-265 handle 3 deprecated patterns |

### What I Cannot Claim
- I cannot claim this causes runtime bugs without a specific route configuration to demonstrate it
- I cannot claim the improvement creates a "deeper problem" with error messages — `not_found` doesn't use path_params
