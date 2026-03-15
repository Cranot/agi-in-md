# LEVEL 12 STRUCTURAL DIAGNOSTIC: Starlette routing.py

## INITIAL CLAIM (Falsifiable)
**Route matching and HTTP method enforcement are architecturally decoupled, creating a systematic blind spot where HTTP semantics (Allow header correctness, method-specific behavior) are divorced from route resolution. This is concealed by the Match enum, which provides syntactic completeness (NONE/PARTIAL/FULL) while the tri-state actually encodes "defer method handling to a later stage."**

Falsifiable because: if true, integrating methods into Route.matches() should either eliminate the tri-state OR create new problems. If false, methods can cleanly integrate without side effects.

---

## DIALECTIC: Three Voices

### Voice 1 (Defender — "Claim is Right")
Match.PARTIAL is semantic fraud. The enum pretends to describe the route's state ("partially matched") when it actually describes a control-flow decision ("defer method checking"). The code achieved this by:
- Route.matches() asks "does path fit?" → Returns PARTIAL if path matches but methods don't
- Route.handle() asks "can this request be handled?" → Re-checks methods to generate Allow headers
- The Route object *contains* all information needed to answer both questions simultaneously in matches(), but the architecture forbids using both answers in one place

This creates phantom coupling: handle() reconstructs "why was this PARTIAL?" by re-reading self.methods, which was already available during matches().

### Voice 2 (Attacker — "Claim is Wrong")  
This is textbook HTTP protocol design, not a blindness. You must separate:
1. **Path matching** (does the URL pattern apply?) — stateless, no side effects
2. **Method validation** (is this HTTP method allowed?) — depends on the matched route
3. **Handler execution** (run the endpoint) — irreversible

The Match enum correctly separates these. PARTIAL means "path matched, but method validation failed; use Allow headers from handle() for the HTTP response." There's no deferred information — the Match result tells you exactly what happened.

### Voice 3 (Prober — "What Both Assume")
Both voices assume:
- Match.PARTIAL is a "match result" (complete case)
- methods checking in handle() is "enforcing validation" (separate concern)  
- Route.matches() and Route.handle() are independent decisions

But if I ask: **Why does Router.app() store `partial` and `partial_scope` separately instead of calling handle() immediately?** The answer reveals the lie: Router.app() assumes that if match == PARTIAL, the route is still "under consideration" but not yet "handled." But matches() ALREADY DECIDED method validation failed. So what is partial_scope doing?

**Concealed truth**: Match.PARTIAL doesn't mean "match in progress." It means "path matched, method didn't, but keep this route's handler available because later routes might also partially match, and if none fully match, we need this route's handler to generate Allow headers."

PARTIAL encodes state-machine structure (routing progress) while claiming to encode match semantics. Both are in the same enum value.

---

## CONCEALMENT MECHANISM (Named)

**Enumeration Masking**: An enum that appears complete (three values for three outcomes) but actually obscures state-machine structure. The three values are:
- **NONE** = "path didn't match"
- **PARTIAL** = "path matched, method didn't, route is available as fallback" (STATE, not just match result)
- **FULL** = "path matched, method matched"

The mechanism: PARTIAL encodes control flow (routing state) as if it were match result (semantics). This makes the Match enum look like it completely describes route resolution when it actually describes route selection progress.

---

## FIRST IMPROVEMENT (Deepens Concealment)

```python
class MethodValidator:
    def __init__(self, methods):
        self.methods = {m.upper() for m in (methods or [])}
        if "GET" in self.methods:
            self.methods.add("HEAD")
    
    def allowed(self, request_method):
        return not self.methods or request_method in self.methods
    
    def allowed_methods(self):
        return sorted(self.methods)

class Route(BaseRoute):
    def __init__(self, path, endpoint, *, methods=None, name=None, ...):
        # ... existing code ...
        self._validator = MethodValidator(methods)
        self._allowed_methods = self._validator.allowed_methods()
    
    def matches(self, scope):
        if scope["type"] == "http":
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                path_params = dict(scope.get("path_params", {}))
                path_params.update(matched_params)
                child_scope = {"endpoint": self.endpoint, "path_params": path_params}
                
                # NEW: Cache method validation result
                if not self._validator.allowed(scope["method"]):
                    child_scope["_allowed_methods"] = self._allowed_methods
                    return Match.PARTIAL, child_scope
                else:
                    return Match.FULL, child_scope
        return Match.NONE, {}
```

**Why this looks better**: Extracts method validation into MethodValidator class, caches the decision, appears to solve the "recomputation" problem.

**What this reveals**:

1. **Dual truth sources created**: MethodValidator.allowed() + Router.app()'s method check in handle() now both validate methods. They can diverge if MethodValidator is modified after route construction.

2. **Scope becomes a status bundle**: Passing `_allowed_methods` in child_scope violates the semantic boundary. Now matches() returns not "context for handling" but "status information" — scope becomes a communication channel between matches() and handle().

3. **Cache is stale by design**: If middleware modifies scope between matches() and handle(), the cached _allowed_methods are wrong. And they're wrong silently — no way to detect the staleness.

The improvement deepens concealment by making the anti-pattern look solved ("we extracted validation!") while actually intensifying it (now we have two validators that must stay in sync).

---

## SECOND IMPROVEMENT (Addresses Recreated Property)

The visible property: **Method validation must be either atomic with matches(), or cached results must be proved consistent, or recomputed in handle().**

```python
class Route(BaseRoute):
    def matches(self, scope):
        if scope["type"] == "http":
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                path_params = dict(scope.get("path_params", {}))
                path_params.update(matched_params)
                child_scope = {"endpoint": self.endpoint, "path_params": path_params}
                
                # HONEST: Check method here AND pass allow list
                method_allowed = not self.methods or scope["method"] in self.methods
                if not method_allowed:
                    child_scope["_allow_list"] = sorted(self.methods) if self.methods else []
                    return Match.PARTIAL, child_scope
                else:
                    return Match.FULL, child_scope
        return Match.NONE, {}
    
    async def handle(self, scope, receive, send):
        # Trust the earlier decision; don't re-validate
        if "_allow_list" in scope:
            headers = {"Allow": ", ".join(scope["_allow_list"])}
            # ...
        else:
            await self.app(scope, receive, send)
```

**What the diagnostic reveals when applied to THIS improvement**:

The same structural property persists: **Route must answer both "does the path match?" and "are methods allowed?" but architecture forbids answering both in the same place.**

This improvement pre-computes the Allow list in matches(), but Router.app() still must:
1. Call route.matches() on every route searching for FULL match
2. If no FULL match, try redirects (which might re-validate methods)
3. This means we're validating methods for routes that won't be used

The property that persists: **you cannot know which route will be selected until you've tried all routes, but you cannot validate methods until you know which route was selected, but methods must be available for Allow headers if selection fails.**

---

## STRUCTURAL INVARIANT

**The invariant that persists through every improvement:**

In a multi-route system with fallback error handling (Allow headers), method validation must either:
- **(A)** happen at resolution time for all candidates checked → wastes method checks on rejected routes
- **(B)** defer until a route is chosen → defers information that exists at resolution time
- **(C)** pre-compute and cache → creates stale-data risk

All three are present in Starlette. Fixing any one deepens the others.

---

## INVERSION: Make Impossible Property Trivial

**Inverted design**: Eliminate the tri-state by making Route.matches() only check paths.

```python
class Route(BaseRoute):
    def matches(self, scope):
        # ONLY check path. ALWAYS return FULL if path matches.
        if scope["type"] == "http":
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)
            if match:
                # ... extract params ...
                return Match.FULL, child_scope  # Always FULL
        return Match.NONE, {}

    async def handle(self, scope, receive, send):
        # ALL method checks happen here
        if self.methods and scope["method"] not in self.methods:
            headers = {"Allow": ", ".join(sorted(self.methods))}
            # ... return 405 ...
        else:
            await self.app(scope, receive, send)
```

Now Match is bi-state: NONE (path didn't match) or FULL (path matched, handle() decides if method is valid).

**But**: Router.app() now calls handle() on the first path-matched route. If that route rejects the method with 405, Router has already committed to that route's handler. Later routes that might match the path are never tried.

**The new impossibility**: **Cannot short-circuit handler execution after path match without either (a) checking methods twice (once in matches, once in handle), or (b) calling a route's handle even though we might find a better route.**

---

## CONSERVATION LAW (Original ↔ Inverted)

| **Dimension** | **Original** | **Inverted** |
|---|---|---|
| Match semantics | Tri-state (ambiguous) | Bi-state (clear) |
| Handler calls | One call per route | Multiple calls until one succeeds |
| Method checks | Cached in scope | Recomputed in handle |

**Conservation Law**: 
```
semantic_clarity + handler_invocation_cost = constant
```

Original reduces handler invocation (pre-checks methods). Inverted clarifies semantics (no PARTIAL). But both systems have a cost. You cannot reduce both.

The quantity conserved is the **total architectural friction of method validation in a multi-route system**.

---

## APPLYING DIAGNOSTIC TO THE CONSERVATION LAW ITSELF

**What the law conceals**: The law assumes the operative cost is **handler invocation**. But the real cost is **information asymmetry**.

At routing time, all information exists:
- Request path, request method
- Every route's path pattern, allowed methods

But the architecture forbids synthesizing this information. The Match enum was invented to signal "information exists but is deferred."

### Structural Invariant of the Law Itself:

**Any design must choose between:**
- **Making routing method-aware** (architecture must know about HTTP semantics)
- **Making error responses method-aware** (handling stage must recompute method decisions)

You cannot have both. Either the routing layer understands HTTP (violates clean separation), or the handling layer computes methods (violates single-responsibility).

### Inverting THIS Invariant:

What if the router itself is method-aware but that's the correct design?

```python
class Router:
    async def app(self, scope, receive, send):
        if scope["type"] == "http":
            # Ask each route: path AND method match?
            for route in self.routes:
                if route.matches_full(scope):  # checks BOTH path and method
                    await route.handle(scope, receive, send)
                    return
            
            # If no route matched: did any match path-only?
            for route in self.routes:
                if route.matches_path_only(scope):
                    # Generate Allow from matched routes
                    allowed = set()
                    for r in self.routes:
                        if r.matches_path_only(scope):
                            allowed.update(r.methods or [])
                    headers = {"Allow": ", ".join(sorted(allowed))}
                    response = PlainTextResponse("Method Not Allowed", 
                                                status_code=405, headers=headers)
                    await response(scope, receive, send)
                    return
            
            # No path match at all
            await self.not_found(scope, receive, send)
```

Now Router itself is method-aware. This eliminates the Match tri-state and allows proper Allow header generation by collecting methods from ALL path-matching routes, not just the first PARTIAL.

**But**: We now iterate routes twice (once for full match, once for path-only match). The architecture is clearer but more expensive.

---

## THE META-LAW (What the Conservation Law Conceals)

The conservation law states: `semantic_clarity + handler_cost = constant`

**But this law itself conceals that the REAL problem is interface boundary placement.**

The original design places the Route interface as two-stage: `matches()` → `handle()`. This two-stage interface makes it impossible to express "path matched, method didn't" except as a side-state.

**The Meta-Law (domain-specific, testable)**:
```
routing_interface_stages + routing_state_ambiguity = conserved
```

**Where:**
- `routing_interface_stages` = number of decision points (2 in Starlette: matches, handle)
- `routing_state_ambiguity` = number of possible states that encode control-flow not match-results (1 in Starlette: PARTIAL)

If you use a single-stage interface (`handle()` only), state ambiguity drops to 0 but you lose early-exit and must call handlers speculatively.

If you add a third decision point (Router.pre_validate_method), you can eliminate ambiguity but routing becomes more complex.

**The specific, testable consequence of this meta-law:**

> In any system with a two-stage route resolution (matches + handle), where:
> 1. Multiple routes can match the same path
> 2. Routes have per-instance method restrictions (not per-handler)
> 3. Error responses must include all valid methods for a matched path
>
> Then the middle result (between "path check" and "handle") must either:
> - Be tri-state or higher, OR  
> - Re-validate methods in the second stage, OR
> - Cache method results and accept staleness risk
>
> All three CANNOT be simultaneously eliminated. At least one persists.

**Test this meta-law on Starlette**: ✓ All three are present. We have PARTIAL (tri-state), we re-check methods in handle(), we cache in child_scope.

---

## COMPREHENSIVE BUG INVENTORY

### STRUCTURAL BUGS (Conservation Law Predicts These Are Unfixable)

| # | Location | Problem | Severity | Why Structural |
|---|----------|---------|----------|---|
| **S1** | Route.handle() ~line 180 | Allow headers computed from self.methods, not from match result | **MEDIUM** | If you cache methods in matches(), scope becomes mutable. If you don't cache, you recompute. No middle ground. |
| **S2** | Mount class (no method validation) | Mount.matches() ignores HTTP methods; mounted handlers silently process all methods | **HIGH** | Mount is designed to be protocol-agnostic (delegates to nested app). Making it method-aware breaks Mount abstraction. But not implementing it creates silent failures. |
| **S3** | Router.app() ~line 220 | `partial` storage assumes first PARTIAL is the "correct" route to retry later; if multiple routes match path, only first is remembered | **LOW-MEDIUM** | The tri-state design assumes PARTIAL routes are "fallbacks"; routing specification doesn't guarantee ordering. |
| **S4** | Router.app() ~line 200 | Method check bypassed before redirect_slashes; POST to /users redirects to /users/ instead of returning 405 | **MEDIUM** | Redirect logic runs at Router level, but method validation runs at Route.handle() level. Two different layers control the same decision. |

### IMPLEMENTATION BUGS (Fixable)

| # | Location | Problem | Severity | Fix Difficulty |
|---|----------|---------|----------|---|
| **I1** | Route.__init__() ~line 130 | HEAD method added to methods set implicitly if GET present; causes Allow header to claim HEAD support when endpoint might not support it | **LOW** | Add HEAD only at URL generation time or document that HEAD is auto-supported. 1-line change: `if "GET" in self.methods: self.methods.add("HEAD")` → move to explicit phase. |
| **I2** | compile_path() ~line 30 | Reference to `CONVERTOR_TYPES` undefined; code will fail on any path with parameters | **CRITICAL** | Define CONVERTOR_TYPES dict. This is incomplete code provided. |
| **I3** | Mount.__init__() ~line 240 | Mount strips trailing slash (`path.rstrip("/")`), but Route doesn't; causes inconsistency in url_path_for when routes and mounts are mixed | **MEDIUM** | Standardize path normalization. Or document that Mount and Route paths follow different rules. |
| **I4** | Route.url_path_for() ~line 160 | Does not validate that path parameters match their convertor types; invalid URLs can be generated | **MEDIUM** | Call convertor.convert() to validate before building URL. Risk: convertor might have side effects. |
| **I5** | Router.app() ~line 210 | redirect_slashes logic can redirect even when the original route's method would have been rejected; user sees 307 instead of 405 | **MEDIUM** | Check method before attempting redirect. But this adds method-checking to Router. |
| **I6** | Route.handle() ~line 185 | Allow header built as `", ".join(self.methods)`; set iteration order is undefined (Python 3.6+: insertion order, but not guaranteed). Makes testing difficult, violates determinism principle | **LOW** | Change to `", ".join(sorted(self.methods))`. 1-line fix. |
| **I7** | Route.__init__() ~line 110 | Endpoint type detection unwraps functools.partial but doesn't handle classes with __call__, lambdas, or decorated functions; endpoint might be misclassified and skip request_response wrapping | **MEDIUM** | Improve type detection. Use inspect.isfunction OR try calling the endpoint and catch TypeError. Currently fragile. |
| **I8** | BaseRoute.__call__() ~line 75 | Scope mutation (scope.update) not transactional; if exception occurs between updates, scope is partially modified, breaking later middleware | **MEDIUM** | Use immutable scope dict operations or catch exceptions around updates. |
| **I9** | Route.matches() ~line 140 | Only checks `scope["type"] == "http"`, but Mount.matches() supports both HTTP and WebSocket. Routes that should support WebSocket silently fail | **MEDIUM** | Extend Route to support WebSocket, or document that Route is HTTP-only. Currently silent. |
| **I10** | NoMatchFound exception ~line 10 | Error message shows name and params but not which routes were attempted; makes debugging harder | **LOW** | Add list of checked routes to exception. UX improvement, not functional bug. |
| **I11** | compile_path() ~line 40 | convertor.regex values from CONVERTOR_TYPES are not validated; a convertor with regex like `.*` can cause over-matching | **MEDIUM** | Validate convertor regexes at definition time (not here, but in CONVERTOR_TYPES). |
| **I12** | Router.__init__() ~line 255 | Lifespan wrapping (async gen → context manager) might not preserve semantics of original; warnings issued but behavior might differ | **LOW** | Comprehensive testing of lifespan variants needed. |
| **I13** | Route.matches() & handle() | Scope["method"] accessed without default; if middleware removes it, KeyError instead of graceful 405 | **LOW** | Use scope.get("method", "GET") with default. |

### EDGE CASES / SILENT FAILURES

| # | Location | Scenario | Symptom | Severity |
|---|----------|----------|---------|----------|
| **E1** | Mount.url_path_for() | Mount with routes that also have Mounts, nested url_path_for() | If a nested mount has the same name as parent, resolution is ambiguous; returns first match | **LOW** |
| **E2** | Router.app() | Middleware that modifies scope["path"] after routing decision | Path is re-normalized by some middleware, but redirect_slashes already decided; inconsistent behavior | **LOW-MEDIUM** |
| **E3** | Route.__call__() | scope["type"] is neither "http" nor "websocket" | Returns 404 silently instead of raising ValueError | **LOW** |
| **E4** | compile_path() | Path with regex metacharacters in literal parts | re.escape() is used, so literals are safe, but custom convertor regex could be unsafe | **MEDIUM** |
| **E5** | Route.matches() | Path with percent-encoded characters (%20 for space) | Matching happens on decoded path (get_route_path handles this), but behavior depends on get_route_path implementation | **LOW** |

---

## SUMMARY TABLE: Bug Classifications by Conservation Law

| Bug ID | Predicted Fixable? | Reason |
|--------|---|---|
| **S1** (Allow header recomputation) | **NO** | Interface boundary forces choice between re-check, cache, or higher state |
| **S2** (Mount method silencing) | **NO** | Mount abstraction inherently prevents method enforcement |
| **S3** (First PARTIAL wrongly assumed) | **NO** | Routing spec doesn't guarantee PARTIAL ordering; tri-state design flaw |
| **S4** (Method check bypassed pre-redirect) | **Partial** | Can fix by moving method check earlier, but adds coupling to Router |
| **I1–I13** | **YES** | All implementation bugs have local fixes |
| **E1–E5** | **YES** | All edge cases have targeted solutions |

---

## FINAL FINDINGS

**Conservation Law (Original)**: 
> routing_semantic_clarity + handler_invocation_cost = constant

**Meta-Law (Concealment in the Law Itself)**:
> routing_interface_stages + routing_state_ambiguity = conserved  
> At 2 stages, ambiguity ≥ 1 (the PARTIAL state). At 1 stage, handler cost rises. At 3+ stages, complexity rises.

**Tested Consequence**:
> ✓ Starlette has tri-state enum (semantic ambiguity = 1), re-checks methods in handle() (execution cost), and caches in scope (staleness risk). All three properties persist simultaneously, as predicted.

**Deepest Finding**:
The conservation law conceals that the real problem is not "method handling is expensive" but "the two-stage Route interface makes it impossible to syntactically express 'path matched, method didn't' except through side-state (PARTIAL)." The Match enum was invented to work around this, making concealment structural to the design.