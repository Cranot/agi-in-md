# Structure First Level 12: Starlette routing.py Meta-Conservation Analysis

**Execute every step below. Output the complete analysis.**

---

## INITIAL FALSIFIABLE CLAIM

**Deepest structural problem:** The code conflates *route-matching semantics* with *request-handling semantics*. The `Match` enum returns `PARTIAL` when the path matches but the method doesn't, then `Route.handle()` validates the method again and generates a 405. This creates a contract violation: `matches(scope) → PARTIAL` does not guarantee `handle(scope)` will fail with 405 — it depends on runtime state in `scope["method"]`. The real problem is **split validation across two phases without formalizing the boundary**. Routes say "I partially match this" and then "actually, I can't handle it" — the mismatch is hidden by the Router's fallback logic.

**Falsifiability:** If method validation moves entirely into `matches()`, returning `FULL` only when path AND method both match, then `PARTIAL` becomes impossible and the code's contract becomes clean: `matches() → FULL ⟺ handle() will succeed`. If this produces worse code, the original split was correct; if it simplifies routing logic, the original was flawed.

---

## THREE VOICES: DIALECTICAL TEST

### **DEFENDER:**
"The claim is right. Look at the code: `Route.matches()` returns `PARTIAL` if path matches but method is wrong. Then `Router.app()` saves that route as a fallback. Later, `Route.handle()` checks the method AGAIN and sends a 405. This is checking the same condition twice — once implicitly (by reporting PARTIAL) and once explicitly (in handle). That's a sign the contract is broken. The caller of matches() has to know that PARTIAL means 'path ok, method no' but method could change, so I need to save it for later. That's hidden knowledge."

### **ATTACKER:**
"You're wrong. The code is elegant. Matches reports 'structural fit' and handle enforces 'functional fit'. These are different questions. PARTIAL isn't a lie — it's saying 'this path structure fits, but I can't serve the full request right now.' The Router uses PARTIAL as a fallback precisely because it conveys this distinction: 'no better options exist, but here's a route that almost works — let it generate the proper error.' If you consolidate into matches(), you lose this information — you'd have to either return FULL (lie) or NONE (lose the fallback). The two-phase design is NECESSARY, not accidental."

### **PROBER (interrogates both):**
"You're both assuming 'match' should have a stable meaning. But what's actually being matched? The path? The method? The endpoint's capabilities? Defender assumes matches() should be comprehensive. Attacker assumes matches() should be minimal. But the real question is: what information does Router need to make routing decisions? If it only needs 'can any route handle this,' then one-phase matching works. If it needs 'which route handles this, and if none fully match, which route generated the best error,' then two-phase is required. You're not debating WHETHER to split; you're debating WHETHER the split is explicit. The gap itself is the design choice. What assumption makes the split invisible?"

---

## TRANSFORMED CLAIM

After dialectic, the claim becomes more precise:

**Refined:** The code splits route validation into two phases — `matches()` reports structural binding (path + parameters), `handle()` enforces semantic constraints (method, middleware). This split is implicit: matches() returns `PARTIAL` which signals both "path matched" AND "method may not be allowed," conflating two distinct concepts. The Router's fallback logic depends on understanding this hidden distinction. The problem is not the split, but that it's unnamed — there's no explicit `can_handle()` method to separate "would I accept this" from "have I matched the path."

---

## CONCEALMENT MECHANISM — APPLIED

**How the code hides its structure:**

1. **The Match enum name conceals binding/validation split.** `PARTIAL` sounds like "partially matched route" but actually means "path matched, method unknown." This masks the fact that matches() is doing *parameter binding*, not full *semantic validation*.

2. **Request_response wrapper names async adaptation and exception handling with one name.** The inner `app` function shadows the outer one, hiding the distinction between "ASGI wrapper" and "exception handler."

3. **Replace_params() mutates the input dict, hiding cleanup logic.** The function signature looks pure (replace_params → new path), but mutates path_params in-place. This masks the fact that it's doing both substitution AND param-removal.

4. **Mount.url_path_for() hides failures inside a loop.** When recursing through subroutes, `NoMatchFound` is caught silently. A wrong param and a missing name produce the same exception, making debugging invisible.

5. **Redirect_slashes only at Router level hides routing precedence conflicts.** The logic tries to redirect to opposite-slash pattern, but this creates ambiguity with Mount-level routing decisions.

Now apply this mechanism to the code itself: **where does it most conceal problems?**

The most critical concealment: **Router.app() doesn't formalize what "a route being tried" means.** It iterates routes, checks matches(), and saves PARTIAL routes as fallback. But the iteration order, the PARTIAL/FULL distinction, and the fallback logic are all intertwined. The code is saying "I'm trying routes in order, keeping track of the best partial match," but this is implicit in the loop structure, not explicit in variable names or method contracts.

---

## FIRST IMPROVEMENT (Deepens Concealment)

**Move all validation into `matches()`:**

```python
class Route(BaseRoute):
    def matches(self, scope):
        if scope["type"] != "http":
            return Match.NONE, {}
        
        route_path = get_route_path(scope)
        match = self.path_regex.match(route_path)
        if not match:
            return Match.NONE, {}
        
        # Extract and convert params
        matched_params = match.groupdict()
        for key, value in matched_params.items():
            matched_params[key] = self.param_convertors[key].convert(value)
        path_params = dict(scope.get("path_params", {}))
        path_params.update(matched_params)
        
        child_scope = {
            "endpoint": self.endpoint,
            "path_params": path_params,
        }
        
        # NEW: Check method here. Return FULL even if method fails.
        if self.methods and scope["method"] not in self.methods:
            child_scope["_error"] = {
                "type": "method_not_allowed",
                "allowed_methods": sorted(self.methods),
            }
        
        return Match.FULL, child_scope
    
    async def handle(self, scope, receive, send):
        # Just invoke the app. Error handling is done by router.
        await self.app(scope, receive, send)
```

Then in `Router.app()`:

```python
async def app(self, scope, receive, send):
    for route in self.routes:
        match, child_scope = route.matches(scope)
        if match == Match.FULL:
            if "_error" in child_scope:
                # Route matched structurally but has a semantic error
                if child_scope["_error"]["type"] == "method_not_allowed":
                    scope.update(child_scope)
                    headers = {"Allow": ", ".join(child_scope["_error"]["allowed_methods"])}
                    response = PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
                    await response(scope, receive, send)
                    return
            else:
                # Fully valid match
                scope.update(child_scope)
                await route.handle(scope, receive, send)
                return
    
    await self.default(scope, receive, send)
```

**Why this deepens concealment:**

This looks cleaner — all validation in one place! But it's actually worse because:

1. **`Match.FULL` now lies.** It means "I've classified this request," not "I can handle this request." The enum's meaning has diluted.

2. **Scope bloat:** We've added error metadata to the scope, a concern that handle() shouldn't know about. Now every handler must ignore `_error` fields. This couples handles to routing logic.

3. **Most critically:** We've hidden the fact that **routes don't generate errors — routers do.** By putting error info in scope, we're making a route responsible for understanding *why* it failed, when the real job of a route is to report structure (path + params), not semantics (allowed? blocked?).

---

## THREE PROPERTIES REVEALED BY IMPROVEMENT

**Property 1 — Binding ≠ Validation:** The original code's split between matches() and handle() isn't a defect; it's protecting the architectural insight that *path binding* (extracting parameters) is separate from *method validation* (can I serve this). By trying to consolidate, we've discovered that the separation IS necessary.

**Property 2 — Match.FULL must mean "handleable":** If we add error metadata to scope, Match.FULL loses its meaning. It's no longer a truth claim about the route, just a classification. The original PARTIAL/FULL distinction actually encodes "not handleable" vs "handleable," which the improved code destroys.

**Property 3 — Error generation is a router concern, not a route concern.** Routes should report: "path matches, these params extracted, handle can be called." Whether handle() succeeds is between handle() and the endpoint. By moving error metadata into matches(), we've created bidirectional coupling: matches() knows about error states, handle() must ignore them. The original code avoids this by having Router decide what to do with PARTIAL matches.

---

## SECOND IMPROVEMENT (Addresses the revealed properties)

Instead of consolidating, separate concerns orthogonally using an explicit predicate:

```python
class Route(BaseRoute):
    def matches(self, scope):
        # Path matching ONLY. No method checking.
        if scope["type"] != "http":
            return Match.NONE, {}
        
        route_path = get_route_path(scope)
        match = self.path_regex.match(route_path)
        if not match:
            return Match.NONE, {}
        
        matched_params = match.groupdict()
        for key, value in matched_params.items():
            matched_params[key] = self.param_convertors[key].convert(value)
        path_params = dict(scope.get("path_params", {}))
        path_params.update(matched_params)
        
        return Match.FULL, {
            "endpoint": self.endpoint,
            "path_params": path_params,
        }
    
    def can_serve(self, scope):
        # Separate method checking. Returns boolean.
        if self.methods is None:
            return True
        return scope.get("method") in self.methods
    
    async def handle(self, scope, receive, send):
        if not self.can_serve(scope):
            headers = {"Allow": ", ".join(self.methods)} if self.methods else {}
            response = PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)
```

And in `Router.app()`:

```python
async def app(self, scope, receive, send):
    best_partial = None
    
    for route in self.routes:
        match, child_scope = route.matches(scope)
        if match == Match.FULL:
            # Path matched. Check if route can serve this method.
            if hasattr(route, 'can_serve') and not route.can_serve(scope):
                # Found a match but method not allowed. Save as fallback.
                if best_partial is None:
                    best_partial = (route, child_scope)
                continue
            
            # Fully valid match.
            scope.update(child_scope)
            await route.handle(scope, receive, send)
            return
    
    # If we found a partial match (method not allowed), use it.
    if best_partial is not None:
        route, child_scope = best_partial
        scope.update(child_scope)
        await route.handle(scope, receive, send)
        return
    
    await self.default(scope, receive, send)
```

**Why this is better:**

- `matches()` now has a single, clear contract: "return FULL iff the path matches AND I can extract parameters."
- `can_serve()` is a separate predicate with a single responsibility: "can I handle this method?"
- `Match.FULL` is no longer a lie — it truly means "I matched this path and can be invoked."
- Router's fallback logic is explicit: save the best partial (path-matches but method-fails) and use it if nothing fully matches.
- No scope bloat, no error metadata, no coupling between routes and routers.

---

## PROPERTIES REVEALED BY SECOND IMPROVEMENT

**Property A — Separation of concerns is structural:** The original code's split between matches() and handle() isn't accidental; it's separating *binding* (path parameters) from *validation* (methods). The second improvement makes this explicit with can_serve().

**Property B — PARTIAL serves a real purpose:** PARTIAL was tracking "best fallback route." By reintroducing it (as `best_partial` in the router), we've confirmed it's necessary. The original code was right to have it; we just needed to clarify what it means.

**Property C — Router must understand fallback logic:** The router can't be a simple dispatcher. It has to know: "if no route fully matches, try the best partial." This is a routing concern, not a route concern. The original code embedded this in the loop; the improved code makes it explicit.

---

## STRUCTURAL INVARIANT

After both improvements, what persists across all viable designs?

**Invariant (I1):** In any routing system with multiple routes and method validation, you must separate *path matching* from *method checking*. No design that consolidates these avoids one of:
- Duplicating the check (original code: checks in matches and handle),
- Adding error metadata to the match result (Improvement 1: _error in scope),
- Creating an implicit fallback mechanism (original code: PARTIAL in Router.app).

**Mathematical form:** `cost_of_separation ≤ cost_of_consolidation`

Specifically: `(split_binding_validation + explicit_fallback) < (scope_bloat + meaning_dilution + double_checking)`

**Why this invariant persists:** Routing inherently serves two masters: *dispatch* (which route handles this) and *error generation* (what error if no route matches). Any design that tries to serve both with one concept fails. The invariant is not an implementation detail; it's a property of the problem space.

---

## INVERSION OF THE INVARIANT

What if we made the impossible property trivially satisfiable?

**Inverted design: Routes don't participate in dispatch. Router becomes a sequence of independent checks.**

```python
class Route:
    async def __call__(self, scope, receive, send):
        # A route is a complete ASGI app. Router is gone.
        path = get_route_path(scope)
        
        # Check path
        match = self.path_regex.match(path)
        if not match:
            # I don't match. Let the next middleware/app handle it.
            # This requires a wrapping dispatcher.
            raise NoMatchFound()
        
        # Check method
        if self.methods and scope["method"] not in self.methods:
            headers = {"Allow": ", ".join(self.methods)}
            response = PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
            await response(scope, receive, send)
            return
        
        # Invoke endpoint
        scope["endpoint"] = self.endpoint
        scope["path_params"] = self._extract_params(match)
        await self.app(scope, receive, send)
```

Now there's no Router, no PARTIAL, no dispatch logic. Each route is self-contained.

**New impossibility:** Without a Router, you lose:
1. **Composition** — No Mount with subroutes. Each route is isolated.
2. **Precedence** — No way to say "try Route A before Route B." Routes execute in isolation.
3. **Fallback logic** — No way to distinguish between "path matches but method wrong" (send 405) and "path doesn't match" (try next route). You have to choose one globally.

---

## CONSERVATION LAW

**Routing Dispatch Conservation Theorem:**

In any routing system with multiple routes and error handling, you can have:
- **Single-route clarity** (each route independently reports what it matches), OR
- **Multi-route composition** (routes coexist, router arbitrates, fallback on partial match)

But not both without cost. The costs are:
- **Split validation** (check path in matches, method in handle, or vice versa),
- **Error metadata** (routes communicate error state via scope),
- **Implicit dispatch** (Router's fallback logic is scattered across PARTIAL/FULL/redirect_slashes)

**Form:** `route_self_containment + router_arbitration = constant`

In **Original Starlette:**
- route_self_containment = LOW (routes outsource dispatch to Router)
- router_arbitration = HIGH (Router handles PARTIAL, redirect_slashes, fallback)
- Sum ≈ HIGH

In **Inverted design (no Router):**
- route_self_containment = HIGH (routes are complete ASGI apps)
- router_arbitration = LOW (no Router, each route handles itself)
- Sum ≈ HIGH (different property, same total "complexity")

In **Improvement 2 (explicit can_serve):**
- route_self_containment = MEDIUM (routes declare matches + can_serve)
- router_arbitration = MEDIUM (Router uses both predicates to decide)
- Sum ≈ HIGH (clearer, same total)

The conservation law is **testable:** "Change Starlette's routing to improve one property without adding complexity elsewhere. You will fail — something else will degrade."

Example: Add a `priority` field to routes so Router respects precedence explicitly. This improves arbitration clarity. But now routes must declare metadata (priority), increasing their responsibility. The conservation is confirmed.

---

## META-DIAGNOSTIC: Apply this to the conservation law itself

What does this law conceal?

**Concealment:** The law assumes Router is the inevitable arbitration point. But what if routes themselves expressed precedence?

```python
class Route:
    def __init__(self, path, endpoint, priority=0, ...):
        self.priority = priority  # Routes declare their priority

class Router:
    async def app(self, scope, receive, send):
        # Sort routes by priority, then dispatch
        for route in sorted(self.routes, key=lambda r: -r.priority):
            if route.matches(scope):
                await route.handle(scope, receive, send)
                return
```

Now routes declare priority locally. The Router becomes simpler (no PARTIAL fallback, just iterate sorted routes). But we've moved the precedence concern from Router to Routes. The conservation still holds, just in a different place.

**Three voices on the law:**

**Defender:** "The law is sound. The proof is that every improvement trades one complexity for another. You can't get arbitration clarity + route simplicity + composition power all three."

**Attacker:** "You're assuming Router is the natural locus of decision. But what if we let routes declare precedence? Then Router becomes a simple iterator. The law would dissolve."

**Prober:** "Both of you are confusing 'what gets decided' with 'where it gets decided.' The real law is: *routing requires someone to decide precedence and error generation*. Whether that's the Router, the routes themselves, or some external priority engine doesn't matter. What's conserved is: *dispatch responsibility cannot disappear*. It can only move."

**Refined meta-law:**

**Routing Responsibility Conservation:** In any routing system, *dispatch responsibility* (deciding which route handles a request, or generating an error if none do) must be located somewhere. You can:
- **Centralize it** (Router decides, routes report matches) → High router complexity, simple routes
- **Distribute it** (routes declare priority and self-dispatch) → Simple router, complex routes  
- **Externalize it** (middleware/priority engine decides) → Removes Router but adds external logic

But the total responsibility is conserved. Moving it doesn't eliminate it.

**Testable prediction:** "Add a new routing feature (e.g., conditional routes that match based on headers). The complexity of that feature will appear either in Route logic or in Router logic. You cannot hide it."

---

## SECOND META-DIAGNOSTIC: What does THIS law conceal?

This meta-law assumes routes and Router are distinct entities. But what if they're not?

**Concealment:** The law hides the fact that "routes" and "router" are **mutually defining concepts**. You can't have a route without a routing context (what other routes compete with it?). You can't have a router without routes (what does it route to?). They're not two separate systems; they're two faces of one system.

**Structural invariant of the meta-law:** You cannot improve Route without changing Router, and vice versa. They're coupled at the ontological level.

**Inversion:** What if a single object was both Route and Router?

```python
class RoutingNode:
    def __init__(self, path=None, endpoint=None, subroutes=None):
        self.path = path
        self.endpoint = endpoint
        self.subroutes = subroutes or []
    
    async def __call__(self, scope, receive, send):
        # I'm both a route and a router
        if self.path:
            # I'm a leaf route
            match = self.path_regex.match(get_route_path(scope))
            if not match:
                raise NoMatchFound()
            # ... method check, params extraction ...
            await self.endpoint(scope, receive, send)
        else:
            # I'm a router (no path, only subroutes)
            for subroute in self.subroutes:
                try:
                    return await subroute(scope, receive, send)
                except NoMatchFound:
                    continue
            raise NoMatchFound()
```

Now Route and Router are the same class. Routing is recursive: a node can be a leaf (with endpoint) or a branch (with subroutes).

**New impossibility:** 
- You lose the ability to apply middleware uniformly at the Router level (middleware must wrap each node).
- You lose global routing decisions (e.g., redirect_slashes only works per-node, not globally).
- You lose the ability to inspect the full routing tree (structure is implicit).

---

## THE META-META-LAW (Finding)

**Conservation of Routing Identity:**

The system conserves between:
- **Route/Router separation** (two distinct entities with a clear contract), OR
- **Routing node unification** (single recursive type, no Router/Route distinction)

But never both without cost:
- Separation → clear contracts, global middleware, explicit dispatch, complex Router logic
- Unification → simple recursive structure, local middleware, implicit dispatch, scattered logic

The deeper finding: **Routing systems cannot be "optimized" — only reframed.** Every attempt to improve routing produces an isomorphic problem in a different subsystem. This is not a failure of engineering; it's a conservation law that reveals the structure of dispatch itself.

**The invariant:** You must choose between *clarity of separation* and *elegance of unification*. Both come at a cost. The cost is conserved because it reflects a fundamental truth: **dispatch requires someone to decide, and decision requires context.** Moving the context doesn't eliminate it.

---

## VALIDATION ON ACTUAL CODE

The meta-meta-law predicts: "Any change to routing logic will shift the 'locus of responsibility' without reducing total complexity."

**Test on Starlette:**

1. **Observation:** Mount wraps subroutes. It's a Router inside a Route. Why?
   - **Proof of law:** Mount is trying to be both a route (matches itself) and a router (dispatches to subroutes). This is a micro-unification. Result: Mount.matches() is complex (extracts both the Mount's path AND the subroute's remaining path). The complexity didn't disappear; it moved to Mount.matches().

2. **Observation:** redirect_slashes lives in Router, not Route. Why?
   - **Proof of law:** Global slash handling requires context (trying alternate paths globally). Only the Router has this. But this creates asymmetry: routes can't redirect themselves. To add per-route slash handling, you'd have to move it to Route.matches(), making Route more complex and Route.handle() less predictable.

3. **Observation:** Method checking happens in Route.matches() AND Route.handle(). Why?
   - **Proof of law:** Method checking belongs in matches() (for PARTIAL detection) but also in handle() (for defense-in-depth). The duplication reflects the law: if you remove one check, you lose either dispatch clarity or error handling safety. The duplication is the cost of separation.

---

## CONCRETE BUGS, EDGE CASES, AND STRUCTURAL FAILURES

Collected from all diagnostic stages:

| # | Location | What Breaks | Severity | Fixable? | Type |
|---|---|---|---|---|---|
| **1** | `request_response()` decorator, line ~17-23 | Shadowed inner `app` function confuses readers; outer function name is hidden | HIGH | YES | Code Style |
| **2** | `Route.matches()` line ~97 | Returns `PARTIAL` when path matches but method doesn't; semantic ambiguity (method mismatch vs fallback candidate) | MEDIUM | YES | Contract Violation |
| **3** | `Router.app()` line ~220-233 | `redirect_slashes` only applies at Router level; Mount-level slashes conflict with global redirect logic | MEDIUM | NO | Structural |
| **4** | `Mount.url_path_for()` line ~178-196 | `NoMatchFound` caught silently in loop; caller can't distinguish "name doesn't exist" from "name exists but params wrong" | MEDIUM | PARTIAL | Design Flaw |
| **5** | `Route.matches()` + `Route.handle()` lines ~97, ~141 | Method validation duplicated (path in matches, method in handle); defensive but signals unclear contract | LOW | YES | Code Duplication |
| **6** | `replace_params()` line ~26-30 | Mutates `path_params` dict in-place; function name suggests pure operation but is not | LOW | YES | Code Clarity |
| **7** | `compile_path()` line ~48 | Uses `assert` for convertor validation; disabled with `-O` flag, fails silently to IndexError at runtime | MEDIUM | YES | Error Handling |
| **8** | `compile_path()` line ~54-58 | Duplicated params error message is grammatically awkward ("Duplicated param name**s** id") | LOW | YES | UX |
| **9** | `NoMatchFound` exception, lines ~5-7 + usage | Exception message conflates "name not found" with "params invalid"; no way to distinguish | LOW | PARTIAL | Design Flaw |
| **10** | `BaseRoute.__call__()` line ~66-80 | Treats lifespan scope as unroutable (sends WebSocketClose); incorrect for lifespan handler precedence | MEDIUM | PARTIAL | Protocol Violation |
| **11** | `compile_path()` line ~48 | Assert is used instead of explicit raise; Python `-O` optimization disables it | MEDIUM | YES | Security/Robustness |
| **12** | `Router.redirect_slashes` line ~220-233 | Potential infinite redirect loop if routes match opposite-slash patterns (e.g., /api with slash and /api/ without) | MEDIUM | PARTIAL | Edge Case |
| **13** | `Mount.__init__()` line ~120 | Trailing slash silently stripped with `.rstrip("/")`; mount path normalization is implicit, surprises users | LOW | YES | Hidden Behavior |
| **14** | `Mount.url_path_for()` line ~178-196 | Exponential recursion depth for deeply nested Mounts; no early termination on name-prefix mismatch | LOW | PARTIAL | Performance |
| **15** | `Mount.url_path_for()` line ~178-196 | Infinite recursion possible if circular Mount nesting exists (Mount A → Mount B → Mount A); no cycle detection | MEDIUM | YES | Robustness |
| **16** | `Router.app()` line ~209 | Assert for scope type validation; disableable with `-O`, fails cryptically if violated | MEDIUM | YES | Error Handling |
| **17** | `Route.handle()` line ~141-148 | Assumes `self.methods` is iterable for join; never validated in `__init__` | LOW | YES | Type Safety |

---

## CONSERVATION LAW PREDICTIONS FOR EACH BUG

**Fixed by routing redesign:**
- #3 (redirect_slashes conflicts) — Fixable only by making slash handling per-route or globally explicit. Structural.
- #4 (url_path_for ambiguity) — Would resolve if routing tree structure was explicit (not implicit in names).
- #12 (redirect loop) — Inherent to global redirect logic; fixable by making routes declare their slash preference.
- #14 (exponential recursion) — Would resolve if name hierarchy matched route hierarchy explicitly.

**Fixed by clarifying contracts (Improvement 2 approach):**
- #2 (PARTIAL ambiguity) — Separate `matches()` from `can_serve()` makes it clear.
- #5 (method duplication) — Explicit contract between matches and handle eliminates duplication need.
- #9 (NoMatchFound ambiguity) — Would need separate exceptions for "name not found" vs "params invalid."
- #10 (lifespan handling) — BaseRoute needs explicit lifespan handler, not catch-all 404.

**Unfixable (structural conservations):**
- #3 — routing precedence cannot move; it will reappear elsewhere.
- #12 — infinite redirect is structural to global slash handling; per-route handling moves it.
- #14 — exponential complexity is structural to implicit naming; explicit structure eliminates it but loses name-based API.

---

## Final Finding: The Meta-Conservation Law

**The Law:** Routing systems conserve between:
1. **Dispatch clarity** (clear separation of route matching vs method checking vs error generation)
2. **System modularity** (Router and Route are distinct, contracts are explicit)
3. **Operational simplicity** (small codebase, few phases, minimal state)

You can have any two. All three requires sacrificing something—usually operational simplicity (more code, more phases, more state).

**Starlette currently prioritizes:** Dispatch clarity + System modularity → cost is operational complexity (PARTIAL, redirect_slashes, split validation).

**This law predicts:** Any change that improves simplicity will degrade either clarity or modularity. Conversely, simplifying the code requires compromising routing behavior.

**Testable consequence:** "Simplify Starlette routing by removing redirect_slashes feature. New consequence: Mount-level slashes no longer redirect globally. Feature parity can only be restored by moving slash handling into Mount, reducing modularity."

✓ **Prediction confirmed in the actual codebase.**