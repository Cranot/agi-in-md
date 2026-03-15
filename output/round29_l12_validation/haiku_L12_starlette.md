# Structure First Analysis: Starlette routing.py
## Level 12 Meta-Conservation Law — Complete Analysis

---

## 1. INITIAL CLAIM

**The routing system achieves 405-specific errors (method not allowed) by having routes return PARTIAL when the path matches but the method doesn't. However, this creates a structural inversion: Route ownership is enforced by execution order, not by declaration. Multiple routes with identical paths but different methods will silently fail — only the first PARTIAL is saved in Router.app(), making the second route unreachable. The code disguises this as a routing status when it's actually a semantic claim of ownership.**

**Falsifiable prediction**: If you define two Route objects with path="/foo" — first with methods=["POST"], second with methods=["GET"] — the second route is unreachable on GET requests without any warning or error.

---

## 2. THREE INDEPENDENT VOICES

### Voice 1: Defender (Pro-Claim)
"The design is actually elegant. Match.PARTIAL means 'this route owns the path but has a decision to make.' Route.matches() returns PARTIAL when path matches but method doesn't, signaling to Router that this route is authoritative for that path. The Router honors this by saving the first PARTIAL and using it. This is correct because in REST, a single logical resource (same path) should be owned by a single Route object that handles all methods. If the developer defines two separate Route objects for the same path, that's a mistake. PARTIAL catches this implicitly."

### Voice 2: Attacker (Against-Claim)
"This is a silent failure mode. Look at Router.app(): it tries routes sequentially, saves the first PARTIAL, then uses it. If Route1 matches path but not method, and Route2 matches both path AND method, Route2 is never consulted because `partial is None` is already false. This is a bug. The framework should either (a) check all routes and pick the best match, or (b) allow developers to mix routes with overlapping paths. Currently, it does neither. It silently picks the worst match (first PARTIAL) and hopes handle() saves it. Python won't warn you. The tests won't catch you. You'll deploy, and GET /foo returns 405 when it should return 200."

### Voice 3: Prober (Questioning Both)
"You're both right about the behavior, but you're both wrong about what it means. The real question is: what is Router supposed to be — an ordered chain or a decision tree? If it's a chain, then execution order determining outcome is correct. If it's a decision tree, then routes should be independent and the best match should win, regardless of order. The code mixes both models: it checks routes in order (chain behavior), but stops at the first PARTIAL (decision tree behavior). This creates a hybrid that satisfies neither model cleanly. The deeper issue: matches() and handle() are separated. Why? Because you want PARTIAL to mean 'path matches but I have a reservation.' But who is 'I'? Is it the path matcher, or is it the HTTP semantics (method not allowed)? If path and method are both routing concerns, they should both be in matches(). If method is a validation concern, it should both be in handle(). But having method check split between them means you've embedded HTTP semantics into the routing abstraction. That's the real inversion."

### Synthesis of Three Voices
**Transformed Claim**: The routing system splits routing (path matching) from validation (method checking) across two functions to enable 405 errors. This creates a semantic overloading: Match.PARTIAL no longer means "partial match" — it means "this route claims ownership of this path and delegates method validation to handle()." This claim is invisible to the type system. If multiple routes with the same path are defined, only the first PARTIAL is used, making all others unreachable. This is enforced by execution order, not by declaration or contract. The code's apparent simplicity hides a coupling between route definition order and route reachability.

---

## 3. CONCEALMENT MECHANISM — HOW THE CODE HIDES ITS REAL PROBLEMS

**Layer 1: Semantic Overloading of Status Codes**
```
Match.FULL      = "path AND method match"
Match.PARTIAL   = "path matches, method doesn't"
Match.NONE      = "path doesn't match"
```

This reads like three matching results, but it actually encodes ownership semantics:
- FULL = "this route accepts the request"
- PARTIAL = "this route claims ownership of the path; go to my handle() for the verdict"
- NONE = "this route has no claim on this path"

The concealment: Status code language makes it look like routing-only information, but it actually claims responsibility.

**Layer 2: Deferred Validation Hides Ordering Dependency**

The code splits the decision across matches() and handle():
```python
# In Route.matches():
if self.methods and scope["method"] not in self.methods:
    return Match.PARTIAL, child_scope  # Method decision made here

# In Route.handle():
if self.methods and scope["method"] not in self.methods:
    # Decision re-confirmed here; 405 sent
```

The concealment: By deferring the method check to handle(), the code makes it look like matches() is about path-only matching. But matches() also validates method. The full validation logic is split. This hides the fact that routing is a two-stage decision.

**Layer 3: Execution Order as the Enforcer**

```python
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match == Match.FULL:
        # Use this route, try no others
        ...
    elif match == Match.PARTIAL and partial is None:
        partial = route  # Save only the FIRST partial
        ...

if partial is not None:
    # Use the first PARTIAL found
    ...
```

The concealment: Route reachability is determined by position in the list, but this isn't documented or enforced. It looks like routes are independent, but they're actually ordered. The code doesn't say "routes are tried in order, first complete match wins, first partial match is reserved." It just loops through and picks the first of each type.

**Layer 4: The Code Passes Tests**

If you test the happy path (one route per method), everything works. If you test 405 errors, it works. The broken case (two routes, same path, different methods) is invisible in tests because you wouldn't naturally write that. The concealment is strongest where it would hurt most: in code that seems to work.

---

## 4. LEGITIMATE-LOOKING IMPROVEMENT THAT DEEPENS CONCEALMENT

**The Improvement**: Simplify Route.matches() by removing the method check:

```python
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
            # NEW: Always return FULL for path matches; remove method check
            return Match.FULL, child_scope
    return Match.NONE, {}

async def handle(self, scope, receive, send):
    # Method check stays here (unchanged from original)
    if self.methods and scope["method"] not in self.methods:
        headers = {"Allow": ", ".join(self.methods)}
        response = PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
        await response(scope, receive, send)
    else:
        await self.app(scope, receive, send)
```

**Why This Passes Code Review**:
1. It's simpler — one fewer conditional in matches()
2. Tests still pass — 405 errors still work identically
3. It looks more "correct" — matches() now only does path matching, handle() only does method handling
4. Performance is slightly better — no method check in the hot path (matches is called before handle)
5. It's a micro-optimization that looks professional

**Why It Deepens Concealment**:
1. **Ownership becomes completely invisible**: With PARTIAL removed, there's no signal that routes claim ownership. Both Route1 (POST) and Route2 (GET) now return FULL for path="/foo", but Router will use only the first one.
2. **The problem becomes undetectable**: In the original code, you could at least see that Route2 returned PARTIAL (if you read carefully). Now both routes look identical in their match result. The difference is only visible when you trace through the loop and see that partial is None.
3. **The ordering dependency is now purely implicit**: Nothing in the code suggests that "routes are tried in order, first FULL match wins." It just looks like routes are independent, and the Router picks the best match.
4. **The fix appears to be a simplification**: Developers will adopt this "improvement" thinking it's cleaner, spreading the bug pattern to new codebases.

---

## 5. THREE PROPERTIES VISIBLE ONLY BECAUSE OF THE IMPROVEMENT ATTEMPT

By trying to make the code "simpler," we expose three structural properties:

**Property 1: Match Results Must Encode Ownership, Not Just Matching**

The original PARTIAL is not a matching result — it's a claim. Removing it forces us to encode ownership in the loop structure instead of the enum. This reveals that the enum is semantically overloaded. A better design would have:
```python
class Match(Enum):
    NONE = 0           # Path didn't match
    ACCEPTED = 1       # Path and method matched
    PATH_ONLY = 2      # Path matched but method rejected (this route is responsible)
    NOT_RESPONSIBLE = 3 # Path didn't match; other routes may handle it
```

**Property 2: Routing and Validation Are Operationally Entangled**

The moment you remove method checking from matches(), you lose the ability to distinguish "no route" from "wrong method" without calling handle(). This reveals that routing can't be separated from HTTP semantics. The route must know about methods not because of path matching, but because of ASGI scope decoding and HTTP semantics.

**Property 3: Reachability Is a Graph Property, Not a Local Property**

The problem (Route2 unreachable) only becomes visible when you think about the set of all routes together. A single Route object has no idea if it's reachable — reachability is a property of the Router graph. This is invisible in the original code (PARTIAL hints at it), and completely hidden in the improved code.

---

## 6. APPLY DIAGNOSTIC TO THE IMPROVEMENT

Now apply the same diagnostic to the simplified code:

**What does the simplified code conceal?**
- It hides the ownership model by using execution order only
- It makes reachability depend on definition order but looks order-independent
- It treats all FULL matches as equivalent, hiding the difference between "method matches" and "method rejected"

**What property of the original problem is visible only because the improvement recreates it?**

In the original code with PARTIAL: if you have Route1(path="/foo", methods=["POST"]) and Route2(path="/foo", methods=["GET"]), a GET request will:
1. Route1.matches() returns PARTIAL (path matches, method doesn't)
2. partial = Route1
3. Route2.matches() returns PARTIAL (never checked because `partial is None` is false)
4. Route1.handle() returns 405

The original code makes it visible that "only the first partial is used" through the PARTIAL status itself.

In the simplified code: the same sequence happens, but without PARTIAL, it looks like Route1 and Route2 both returned FULL. The unreachability is now hidden in the loop logic, not visible in the match result.

The original problem was: **Routes with overlapping paths create a hidden dependency on definition order.**

The improved code recreates this problem while making it less visible. But it also reveals something: the improved code makes it obvious that `partial = route` on the first iteration is a filter operation, not a match quality operation. You can see that only the first partial is saved, and you think "why?"

---

## 7. SECOND IMPROVEMENT — ADDRESSING THE RECREATED PROPERTY

To fix the ordering dependency, add explicit conflict detection:

```python
class Router:
    def __init__(self, routes=None, ...):
        self.routes = [] if routes is None else list(routes)
        # NEW: Detect path ownership conflicts
        self._path_registry = {}
        for i, route in enumerate(self.routes):
            if hasattr(route, 'path_regex') and hasattr(route, 'path_format'):
                path = route.path_format
                if path in self._path_registry:
                    prev_idx = self._path_registry[path]
                    warnings.warn(
                        f"Route #{i} ({route.__class__.__name__} path={path}) "
                        f"shadows Route #{prev_idx}. Route #{prev_idx} will not be reached.",
                        RuntimeWarning
                    )
                self._path_registry[path] = i
        # ... rest of init
```

This makes the hidden constraint explicit: **one path, one route (per router level)**.

---

## 8. SECOND DIAGNOSTIC

Apply the diagnostic to the warning system:

**What does the warning system conceal?**
- It assumes path ownership is absolute (one route per path)
- But Mount routes operate on prefixes, not exact paths
- A Route(path="/foo") and Mount(path="/foo") aren't in conflict; they're complementary
- The warning system conflates them

**What structural invariant persists?**

No matter how much you improve the warnings, you can't actually prevent Route shadowing without changing the protocol. Even with a warning, if the developer ignores it, the second route is still unreachable. The warning is meta-level feedback, not a solution.

The invariant: **Route reachability cannot be enforced at the type level; it requires semantic understanding of all paths in the system.**

---

## 9. STRUCTURAL INVARIANT — THE PERSISTENT PROPERTY

What property persists through every improvement (original, simplified, warning-added)?

**The invariant: Routing must commit to a handler before receiving the complete request.**

Why? ASGI is streaming. The scope arrives first (contains path and method). The request body arrives later. But the router must pick a handler based only on scope. There's no way to "try a handler, receive the body, reject it, and try another handler." The commitment is irreversible.

This appears in:
- **Original code**: Path matches → store endpoint in scope → can't undo it
- **Simplified code**: Path matches → store endpoint → can't undo it
- **Warning system**: Still can't undo it; just warn about it

Every improvement is trying to make the system "smarter," but all of them are constrained by the same irreversible commitment.

---

## 10. INVERT THE INVARIANT

Engineer a design where early commitment becomes unnecessary:

```python
class DeferredRouter:
    async def app(self, scope, receive, send):
        candidates = []
        
        # Collect ALL matching routes (not just first)
        for route in self.routes:
            match, child_scope = route.matches(scope)
            if match != Match.NONE:
                candidates.append((route, child_scope, match == Match.FULL))
        
        if not candidates:
            await self.default(scope, receive, send)
            return
        
        # Prefer FULL over PARTIAL (method matches over path-only)
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        # Try each candidate until one succeeds
        for route, child_scope, is_full in candidates:
            try:
                # NEW: handle() can return success/failure
                result = await route.try_handle(scope, child_scope, receive, send)
                if result == "accepted":
                    return
                # result == "rejected" means try the next route
            except Exception:
                continue
        
        # All routes rejected or errored
        await self.default(scope, receive, send)
```

This inverts commitment: instead of "pick one route immediately," it's "collect all candidates, try them in preference order, stop when one succeeds."

---

## 11. NEW IMPOSSIBILITY CREATED BY INVERSION

But this creates a new impossibility: **The HTTP response is sent during handling, not before it. By the time handle() decides to "reject" the scope and try another route, headers might already be sent, making retry impossible.**

Original impossibility: Early commitment (can't retry).
Inverted impossibility: Can't unsend messages (can't backtrack).

---

## 12. CONSERVATION LAW

**Between original and inverted impossibilities:**

```
Commitment_earliness + Response_deferability = Constant
```

- **Commit early**: Decide on endpoint before calling handle(). Can send response immediately (streaming enabled). Can't retry if handle() rejects.
- **Defer commitment**: Collect all candidates, but can't send response until decision is final. Enables retry, but disables streaming.
- **The trade-off is conserved**: You gain one at the cost of the other.

More concretely for Starlette:
```
early_routing_decision + handler_flexibility = constant
```

Starlette chooses early decisions (FULL match -> handle immediately). This means handlers can't reject and retry. But it enables streaming responses and low latency.

---

## 13. APPLY DIAGNOSTIC TO THE CONSERVATION LAW

**What does this law conceal about the problem?**

The law assumes "commitment" means "pick an endpoint." But actually, there are three separate decisions:
1. Which endpoint handles this scope?
2. Is the request valid (method, headers, body)?
3. Can the response be sent immediately, or must it be buffered?

The law conflates (1) and (3). It says you can commit to an endpoint early (enabling streaming), OR defer commitment (requiring buffering). But actually:
- ASGI commits to an endpoint in scope (decision 1) — this is irreversible
- HTTP method validation can happen early or late (decision 2) — flexible
- Response sending can happen early or late (decision 3) — flexible

The law hides that decision 1 is independent from decisions 2 and 3. You could commit early (to enable streaming) but defer method validation (to enable routing improvements). The law's hidden assumption: once you commit to an endpoint, that endpoint is responsible for ALL validation.

**What structural invariant of the law persists when you try to improve it?**

No matter how you restructure the routing, the ASGI protocol itself enforces endpoint commitment. Once you pass the scope to an endpoint (send it up the stack), you've made a commitment. The endpoint is now responsible for the entire request/response cycle. This is a protocol-level constraint, not a code-level constraint.

---

## 14. INVERT THE CONSERVATION LAW'S INVARIANT

**The invariant**: ASGI endpoints are singular and delegative — once an endpoint receives a scope, it is responsible for the entire lifetime.

**Invert it**: Create a protocol where endpoints can return "rejected" and be replaced:

```python
# Inverted ASGI protocol (hypothetical)
async def app(scope, receive, send, alternatives=None):
    # alternatives is a list of other endpoints to try if this one rejects
    ...
    if request_is_invalid():
        if alternatives:
            return await alternatives[0](scope, receive, send, alternatives[1:])
        else:
            raise NoHandlerError()
```

This inverts: instead of endpoint singularity (one endpoint per scope), there's endpoint negotiation (try multiple endpoints until one succeeds).

**New impossibility created**: The protocol can now have cycles — what if endpoints keep rejecting in a circle? Or infinite chains of alternatives? You need a termination proof that wasn't needed before.

---

## 15. META-CONSERVATION LAW — THE CONSERVATION OF THE CONSERVATION LAW

**Original conservation law**: `commitment_earliness + response_deferability = constant`

This law hides that **ASGI protocol assumes endpoint singularity.**

**The meta-law**: 
```
endpoint_singularity + routing_flexibility = constant
```

More specifically:

**"A routing system can be only as flexible as the protocol it serves. Starlette's early-commitment routing (FULL matches picked first, no retry) is not a limitation of the code — it's a reflection of ASGI's assumption that each scope has a single responsible endpoint. To make routing more flexible (try multiple endpoints), you must change the protocol to support endpoint negotiation. The constraint is conserved at the protocol level."**

Or in inverse form:

**"The routing system's apparent limitation (can't retry after committing to an endpoint) is actually a feature of the protocol it correctly implements. You cannot improve Starlette's routing to support multi-endpoint retry without breaking ASGI semantics. The constraint lives at the boundary between code and protocol."**

---

## 16. WHAT THE META-LAW CONCEALS — TESTABLE PREDICTION

**What does the meta-law conceal about THIS problem?**

The meta-law says: "Routing flexibility is limited by protocol constraints." This is true, but it hides something specific about Starlette's routing.

The law conceals: **Different layer types (Route vs Mount) have different flexibility constraints.**

- Route(path="/foo", methods=["GET"]) — expects to be singular for that path
- Mount(path="/foo") — expects to share the path with child routes

These two types make conflicting assumptions about path ownership. A Route assumes it owns the path exclusively. A Mount assumes it owns only a prefix. But the code treats them the same in Router.app() — they're both just routes.

This hidden asymmetry means:
1. You can nest Mount inside Mount (flexible)
2. You can nest Route inside Mount (works, but only first method matches)
3. You cannot nest Route inside Route (impossible — Route is a leaf)
4. You can't have multiple Routes with the same path at the same level (silent shadowing)

**Concrete testable prediction**: If a developer defines:
```python
Router(routes=[
    Route(path="/foo", endpoint=handler_post, methods=["POST"]),
    Route(path="/foo", endpoint=handler_get, methods=["GET"]),
])
```

Then GET /foo will return 405 (Method Not Allowed) from handler_post's endpoint, not call handler_get.

But if they define:
```python
Router(routes=[
    Mount(path="", routes=[
        Route(path="/foo", endpoint=handler_post, methods=["POST"]),
        Route(path="/foo", endpoint=handler_get, methods=["GET"]),
    ])
])
```

Then GET /foo will work correctly (204 from handler_get).

The meta-law hides that **the solution is not to improve the routing code, but to use the correct route type (Mount, not Router) for multi-method endpoints.**

---

## SUMMARY TABLE

| Stage | Finding | Concealment | Invariant |
|-------|---------|-------------|-----------|
| **Initial** | Route ownership enforced by execution order | PARTIAL semantically overloaded as status code | Routing must commit before full request known |
| **Improvement** | Simplify matches() by removing method check | Ownership becomes completely invisible | Early commitment is irreversible |
| **Improved diagnosis** | Warning system detects path conflicts | Warns about symptom, not root cause | Route reachability depends on definition order |
| **Second improvement** | Add path registry and conflict warnings | Treats Route and Mount as equivalent | Protocol enforces endpoint singularity |
| **Conservation law** | Trade-off: early-commit enables streaming, late-commit enables retry | Hidden: decision about endpoint ≠ decision about validation | ASGI protocol limits routing flexibility |
| **Meta-law** | Routing flexibility is bounded by protocol constraints; Route vs Mount assume different ownership models | The real solution is using Mount for multi-method endpoints, not improving Router code | Different layer types have incompatible assumptions about path ownership |

---

## THE CORE META-LAW (Final)

**The framework's limitation (Route-level single-ownership) and its solution (Mount-level multi-ownership) are not two different things — they are the same thing viewed from different levels. The concealment is that Starlette conflates them by treating Route and Mount as equivalent in Router.app(). They shouldn't be. Mount should explicitly allow multiple paths to be handled by the same dispatcher. Route should explicitly prevent shadowing. By treating them the same, the code hides the distinction and makes both properties invisible.**

**Formal meta-law**: 

```
route_type_semantics + path_ownership_model = constant
```

"You cannot have both Route and Mount behave identically AND have well-defined ownership semantics. If routes are independent (Route model), then overlapping paths create ambiguity. If routes are ordered (Mount model), then shadowing is a feature, not a bug. Starlette tries to be both, and this creates a concealment. The code is trying to give Route (leaf handler) the flexibility of Mount (composite handler), but the naming and type system don't express this. The conservation law lives in the type system, not in the routing algorithm."

**Testable consequence**: The more complex the routing (more routes, more overlap), the more frequently developers will encounter silent shadowing. Solutions that work (moving to Mount) look like 'adding layers,' making the actual solution (using the right type) invisible. The problem is not in the routing logic — it is in the type system that conflates Route and Mount as "both are things Router can handle."
