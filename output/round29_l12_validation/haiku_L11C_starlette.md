## Level 11C Conservation Law: Starlette Routing Analysis

### 1. INITIAL CLAIM (Specific & Falsifiable)

**The deepest structural problem in Starlette routing is the separation of **path matching from HTTP method validation into distinct code paths.** This creates an asymmetry: the scope is mutated (endpoint set, path_params updated) before the request is validated as actually dispatchable. Specifically:**

- `Route.matches()` returns `PARTIAL` when path matches but method doesn't, signaling "we matched you geometrically but can't handle you"
- But the scope is still updated with this partial match in `Route.__call__()`
- Method validation is deferred to `handle()`, running after scope mutation
- This means **endpoints can be invoked with pre-corrupted scope** from requests that never should have reached them
- The "Allow" header can't be computed until after this deferred validation

**The falsifiable prediction:** Any fix that tries to validate methods *before* scope mutation will create a new problem: you can't know what methods are allowed until you know *which route* matched. Early validation requires iterating routes twice.

---

### 2. THREE EXPERTS DEBATE THIS CLAIM

**Defender** (accepts the claim):
"Yes. The PARTIAL state is a temporal control-flow hazard. When Route.__call__ sees PARTIAL, it still calls `scope.update(child_scope)`, which is premature. The endpoint is being handed a scope that says 'you were matched' when you haven't actually been validated. This is worse than just inefficiency — it leaks the notion of 'partial routing' to endpoints that expect 'valid routing.' The proof is in Route.handle(): it re-checks methods, which should never be necessary if matches() was definitive."

**Attacker** (rejects it):
"No. The PARTIAL state isn't a bug, it's a feature. The code is deferring method validation *intentionally*, because:
1. You can't know valid methods until you know which endpoint matched (Route.endpoint could be a class-based view with different handler methods)
2. Mount routes never validate methods at all — it delegates entirely to child routes
3. The redundant check in handle() is cheap and catches late-binding edge cases
4. Endpoints receive the full scope including their local path_params, which is correct
The real issue is that you're describing a problem as if it's a flaw, but it's the necessary consequence of separating concerns between path matching and method validation."

**Prober** (questions both):
"What's really being assumed here? You're both treating 'method validation' as if it's a pure predicate: either the method is allowed or it isn't. But:
- Which methods are allowed isn't intrinsic to the Route — it's a property of Route.endpoint
- If endpoint is a function, methods comes from the decorator. If it's a class, methods are implied by the class handlers
- The PARTIAL state isn't actually answering the question 'can I handle this method?' — it's answering 'does the path match?'
The real asymmetry isn't path vs. method. It's **'I matched your path' vs. 'I decided your method is invalid' — and you're deciding that AFTER mutating scope, which couples two independent concerns that should be independent.** The actual problem might be that method validation shouldn't be Route's responsibility at all — it should be the endpoint's responsibility to reject invalid methods, with Route just forwarding the full request and letting the endpoint decide."

---

### 3. CONCEALMENT MECHANISM

**The code hides its real problem by treating the PARTIAL match state as "handled" (scope is updated) when it actually means "awaiting method validation."**

The concealment works through **temporal inversion of concern order**:
- Logically, you should: (1) match path, (2) validate method on that matched path, (3) handle or reject
- Physically, the code: (1) matches path + updates scope, (2) handles (which does method check), or (3) rejects in handle

This makes it **look like** matching and method-checking are separate concerns (good design), but they're actually **entangled through scope mutation timing**. The PARTIAL state conceals that the scope update is conditional on a later validation that isn't yet complete.

The result: anyone reading the code sees "Route matches or doesn't match, then we handle it" — they don't see the coupling between "what we matched" and "what we'll reject in handle()."

---

### 4. IMPROVEMENT THAT DEEPENS CONCEALMENT

**Engineer a "quick-allow" optimization:** Add a fast path in Router.app() that checks methods *before* iterating routes:

```python
async def app(self, scope, receive, send):
    assert scope["type"] in ("http", "websocket", "lifespan")
    if scope["type"] == "http":
        # Fast path: filter routes by method before matching
        method = scope["method"]
        matching_routes = [
            r for r in self.routes 
            if not hasattr(r, 'methods') or r.methods is None or method in r.methods or method == "HEAD"
        ]
    else:
        matching_routes = self.routes
    
    # ... rest of dispatch logic using matching_routes instead of self.routes
```

**Why this deepens concealment:** It makes the code *appear* to solve the problem (method filtering is now explicit, early) while actually making it worse:
- You're now filtering routes before you know their full structure (Mount contains routes whose methods you can't know)
- You're assuming methods are statically known, but Route can wrap class-based views with dynamic methods
- The fast path works only for simple Route objects, not for Mount or other custom BaseRoute subclasses
- This creates the illusion of separation (methods are checked early!) while hiding the fact that you can't actually check methods until you've resolved routing paths all the way down

This is the classic concealment: **it makes the code more explicit about what it's doing, which makes the actual coupling invisible.**

---

### 5. THREE PROPERTIES REVEALED BY THIS IMPROVEMENT

**Trying to implement the "quick-allow" optimization reveals:**

1. **Methods are path-dependent, not route-independent.** You can't know valid methods until you know which endpoint is reachable at that path. For Mount routes, the method set is the union of all methods in all child routes. For Routes with class-based endpoints, the methods are determined by what handlers the class defines. The optimization forces you to either:
   - Compute method sets recursively through Mount hierarchies (expensive, defeats "quick" path)
   - Assume all routes are simple and allow everything (defeats the optimization)
   - Hard-code method sets on Route.__init__ (loses the ability to have dynamic endpoints)

2. **Scope mutation is the commitment point, not the validation point.** Once you mutate scope to set endpoint and path_params, you've told the downstream code "I know who you're routing to." But PARTIAL match means "not really." The improvement forces you to choose: either mutate scope only after full validation (defeats the deferred-checking architecture) or live with the fact that scope is pre-populated with partial information.

3. **The Allow header is a route discovery problem, not a validation problem.** To know what methods are allowed for a given path, you need to explore all routes that could match that path, extract their method constraints, and compute the union. This is expensive and path-dependent. The current code hides this cost by treating "what methods are allowed" as a side effect of routing failure, not a primary operation. The optimization exposes that you're actually doing hidden route discovery.

---

### 6. SECOND IMPROVEMENT (Addressing the Recreated Problem)

**Engineer a "method-first routing" redesign:**

```python
class MethodConstrainedRouter:
    def __init__(self, routes=None):
        self.routes = list(routes) if routes else []
        # Precompute method set for each path pattern
        self.path_methods = {}  # path_pattern -> set(methods)
        for route in self.routes:
            if hasattr(route, 'path'):
                key = route.path
                if key not in self.path_methods:
                    self.path_methods[key] = set()
                if hasattr(route, 'methods') and route.methods:
                    self.path_methods[key].update(route.methods)
                else:
                    self.path_methods[key] = None  # accepts all methods
    
    async def app(self, scope, receive, send):
        # Validate method against precomputed constraints BEFORE dispatching
        if scope["type"] == "http":
            route_path = get_route_path(scope)
            # Find which route patterns this path could match
            for pattern, methods in self.path_methods.items():
                if self._pattern_matches(pattern, route_path):
                    if methods is not None and scope["method"] not in methods:
                        # Known invalid method for this pattern
                        allowed = ", ".join(sorted(methods))
                        response = PlainTextResponse(
                            "Method Not Allowed", 
                            status_code=405,
                            headers={"Allow": allowed}
                        )
                        await response(scope, receive, send)
                        return
            # If we get here, method is valid for at least one route
        # ... dispatch to routes
```

**Why this matters:** This second improvement tries to address what the first one revealed (method sets are path-dependent), by precomputing them. But it **recreates the original problem**: you're now precomputing method sets at initialization time, which means:
- Routes added dynamically after init won't have their methods registered
- Mount's method set can't be precomputed (it's determined by its child routes, which might be added later)
- The precomputation is brittle and decoupled from actual routing logic

---

### 7. THE STRUCTURAL INVARIANT

**After examining both improvements and both failures, the invariant emerges:**

**"For any routing system that separates path-matching from method-validation, the information needed to validate methods (which methods the endpoint accepts) cannot be known until after the matching process selects the endpoint."**

This invariant is true for:
- Simple Route + endpoint function: methods come from the decorator, which wraps the endpoint
- Route + class-based endpoint: methods come from the class definition
- Mount + nested routes: methods come from child routes, which are determined at route-walk time
- Dynamic route registration: method set is mutable and only knowable after the endpoint is loaded

**The invariant is: Validation_readiness is always AFTER matching, never before.**

No matter how you structure the code, you cannot move method validation *before* path matching, because the methods to validate against are properties of *the matched endpoint*, not properties of *the path pattern*.

---

### 8. INVERT THE INVARIANT

**Original:** "Method validation must happen after matching, because validation parameters come from the matched endpoint."

**Inverted:** "What if method validation happened *as part of* matching, with the endpoint providing validation rules *up front* as part of the route configuration?"

**New design where this is trivially satisfiable:**

```python
class ValidatingRoute(BaseRoute):
    def __init__(self, path, endpoint, *, method_provider=None, **kwargs):
        self.path = path
        self.endpoint = endpoint
        # method_provider is a callable that returns valid methods (can be pre-computed)
        self.method_provider = method_provider or lambda: None  # None = all methods valid
        self.methods = self.method_provider()
        # ... rest of init
    
    def matches(self, scope):
        if scope["type"] == "http":
            if self._path_matches(scope):
                valid_methods = self.methods  # Pre-known!
                if valid_methods is None or scope["method"] in valid_methods:
                    return Match.FULL, {...child_scope...}
                else:
                    # Return method constraint info in the exception itself
                    return Match.METHOD_INVALID, {
                        "allowed_methods": valid_methods,
                        "endpoint": self.endpoint
                    }
        return Match.NONE, {}
```

**New impossibility this creates:** 

If method_provider is a callable, it can return different values on different calls. Now you have a new problem: **"Is method validation static or dynamic?" If dynamic, you can't pre-filter routes. If static, you can't support endpoints with runtime-determined method sets.**

The inversion trades:
- Old: Method validation happens late, scope is pre-mutated
- New: Method validation is early, but method sets must be static/pre-computed

---

### 9. CONSERVATION LAW

**Between the original and inverted designs:**

### **CLARITY_OF_VALIDATION ⟷ TRANSPARENCY_OF_METHOD_RESOLUTION**

In the **original design** (Starlette):
- Validation timing is *implicit*: methods are checked in handle(), after scope update. Developers must read code flow to find it.
- Method resolution is *transparent*: routes declare methods upfront. You can look at a Route and immediately see what methods it accepts.
- Trade-off: you get clear method declarations, but you lose clear validation timing

In the **inverted design** (ValidatingRoute):
- Validation timing is *explicit*: methods are part of the match result. The validation happens in matches(), you can see it right there.
- Method resolution is *opaque*: if methods come from a callable, you don't know what will be accepted until runtime. You can't look at a route definition and see its method set.
- Trade-off: you get clear validation timing, but you lose clear method declarations

**The conservation law states: "Across all designs, clarifying WHERE method validation happens (matching vs. handling) necessarily obscures HOW methods are determined (static vs. dynamic). You cannot make both transparent simultaneously."**

More precisely: **visibility_of_validation_point + visibility_of_method_set = constant**

---

### 10. WHAT THIS REVEALS & PREDICTS

**What the law reveals that a senior engineer wouldn't know:**

1. The current design isn't "sloppy" — it's a *specific choice* to keep method resolution transparent at the cost of validation timing. If Starlette changed to make validation explicit, it would immediately lose the ability to support class-based endpoints with unknown method sets.

2. **The Allow header problem (RFC 7231 violation) is structurally necessary.** The code can't generate a complete Allow header in PARTIAL match state because it hasn't resolved which endpoint will handle the request. You're always choosing: either return a generic "here's what paths we know about" Allow header (wrong), or defer it until you know the endpoint (current behavior).

3. The PARTIAL match state isn't a bug or a feature — it's a **category error**. It's mixing "path-matching results" (NONE/FULL) with "method-validation results" (PARTIAL = "path yes, method no"). These are different concerns, and conflating them into a single Match enum is what creates the temporal asymmetry.

**What it predicts about a third design that neither attempted:**

A design that treats **path matching and method matching as separate routing dimensions** would be able to:
- Return the full Allow header immediately (by matching paths first, then computing all methods for those paths, before checking the requested method)
- Make validation timing explicit (both path and method are validated in the same place)
- Support dynamic method resolution (by separating "what routes match this path?" from "what methods do those routes support?")

But it would create: **"Can the same endpoint be mounted at multiple paths with different method sets?" — If yes, then you now have routing complexity × method complexity. If no, you've constrained endpoint reuse.**

The conservation law predicts: **"Any design that makes Allow header generation explicit and early-validated must either restrict how endpoints are reused across paths, or accept that computing the Allow header requires exploring the entire route tree."**

---

### VALIDATION

This analysis predicts: **If you fix the method validation timing (move it earlier), you must either:**
- Pre-compute method sets (loses dynamic endpoints)
- Explore the full route tree for Allow headers (expensive)
- Restrict endpoint reuse patterns (architectural constraint)

**Current Starlette accepts none of these — it lives with late validation instead. The trade-off is worth it for flexibility.**
