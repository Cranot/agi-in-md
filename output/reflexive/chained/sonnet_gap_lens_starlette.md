## Five Lenses → Starlette Routing

**Pedagogy** | Teaches: Chain-of-Responsibility (routes tried in order), Strategy (Route/Mount behind BaseRoute), Decorator (middleware layered in reverse), two-phase matching (PARTIAL = wrong method, FULL = complete match), reverse routing as tree traversal.

**Claim** | Embeds: routes are static after startup; request identity = (method, path) only; first match wins; GET implies HEAD automatically; `assert` always active; scope is a safe shared channel; route names are globally unique; Allow header on 405 is complete and correct.

**Scarcity** | Assumes won't run out: route list size (O(n) linear scan), regex handle pool (compiled at startup), scope dict growth (merged at every Mount level), thread pool under sync handlers, redirect detection budget (zero — no loop guard), partial-match slots (exactly one: `if partial is None`).

**Rejected\_paths** | What wasn't built: trie/radix routing, per-path method index, immutable scope, compile-time duplicate-route detection, centralized name registry, loop-safe redirect resolution, typed routing (match on type, not string-then-convert), header/query routing.

**Degradation** | What rots without touching it: route ordering (append changes match priority silently), middleware latency stack (each layer invisible until measured), Allow header completeness (more routes → more omissions), name collisions (runtime NoMatchFound, not startup), scope dict size under deep Mount nesting, `assert` validity under `python -O`, the one `partial` variable (first-wins silently drops all later partials).

---

## Where They Most Sharply Disagree

Three disagreements, ranked by severity:

### 1. The Sharpest: Pedagogy × Scarcity × Claim on PARTIAL match

**Pedagogy** teaches: `Match.PARTIAL` is the correct signal for method mismatch → 405 response is handled correctly.

**Claim** embeds: 405 responses enumerate all allowed methods (the Allow header is correct).

**Scarcity** reveals: `partial` is a single variable. The code is `elif match == Match.PARTIAL and partial is None`. Only the **first** partial match is captured. Every subsequent partial match is silently dropped.

**Consequence**: The standard REST pattern — multiple routes for the same path with different methods — produces structurally incomplete 405 responses. The Allow header contains only the first-registered route's methods. The more correct your REST design, the more RFC 7231-violating your error responses.

```python
routes=[
    Route("/items/{id}", get_item,    methods=["GET"]),     # PARTIAL captured here
    Route("/items/{id}", update_item, methods=["PUT"]),     # PARTIAL — partial is not None → dropped
    Route("/items/{id}", delete_item, methods=["DELETE"]),  # PARTIAL — dropped
]
# PATCH /items/123: 405 Allow: GET, HEAD
# RFC 7231 requires: Allow: GET, HEAD, PUT, DELETE
```

**Degradation amplifies it**: scope.update(partial_scope) sets `scope["endpoint"]` to the first-partial's handler. Middleware accumulates over time — auth, tracing, rate-limiting all read `scope["endpoint"]`. On every 405 response, they see the wrong endpoint and make wrong decisions before the 405 is even sent.

### 2. Pedagogy × Degradation on scope mutation

**Pedagogy** teaches: "compose behavior by updating shared context" — scope mutation is the pattern.

**Degradation** reveals: as Mounts nest (Mount → Router → Mount → Router), scope accumulates keys from every level. No schema, no validation. Custom keys from third-party middleware can collide silently. The scope grows as a blackboard with no eraser.

### 3. Claim × Scarcity under `python -O`

**Claim** embeds: paths are always validated (`assert path.startswith("/")`).

**Scarcity** reveals: Python's optimization budget is zero for asserts. `python -O` or `PYTHONOPTIMIZE=1` (common in containerized deployments) silently removes every `assert` in Route and Mount `__init__`. `compile_path` catches some malformations but not all.

---

## Code That Lives Only in the Gap

The gap between disagreements 1 and 2: **fixing the incomplete Allow header requires internalizing method dispatch, which makes `scope["endpoint"]` opaque to middleware — the fix IS the new gap.**

```python
# Gap-code: visible only when Pedagogy contradicts Scarcity contradicts Degradation
# Each lens individually approves this class. The combination reveals a new blindspot.

class PathRouter(BaseRoute):
    """
    Consolidates all methods for a path into one route object.
    
    Pedagogy approves  : teaches method dispatch, separation of concerns
    Claim approves     : single name, explicit methods, paths validated
    Scarcity approves  : O(1) dict lookup for method, no partial accumulation
    Rejected_paths approves : centralizes what Router.app() disperses
    Degradation approves   : adding methods doesn't change route ordering
    
    The gap this fixes: RFC 7231 Allow header completeness.
    The gap this creates: scope["endpoint"] is now PathRouter (self),
                          not the actual handler function.
    Middleware that reads scope["endpoint"] for auth/tracing/rate-limiting
    gets an opaque dispatcher object. The fix for gap-1 opens gap-2.
    The gap migrates; it does not close.
    """
    def __init__(self, path: str, *, name: str | None = None, **method_handlers):
        assert path.startswith("/"), "Routed paths must start with '/'"
        self.path = path
        self.name = name or path
        self._handlers: dict[str, Callable] = {}
        for method, handler in method_handlers.items():
            self._handlers[method.upper()] = handler
        if "GET" in self._handlers:
            self._handlers.setdefault("HEAD", self._handlers["GET"])
        self.path_regex, self.path_format, self.param_convertors = compile_path(path)

    def matches(self, scope: dict) -> tuple[Match, dict]:
        if scope["type"] != "http":
            return Match.NONE, {}
        route_path = get_route_path(scope)
        m = self.path_regex.match(route_path)
        if not m:
            return Match.NONE, {}
        matched_params = {
            k: self.param_convertors[k].convert(v)
            for k, v in m.groupdict().items()
        }
        path_params = {**scope.get("path_params", {}), **matched_params}
        # Always FULL: method dispatch is internal.
        # Scarcity fixed : no partial accumulation, correct Allow header coming.
        # Claim broken   : scope["endpoint"] = self (PathRouter), not the handler.
        # Degradation broken: auth/tracing middleware reads self, not the real function.
        return Match.FULL, {"endpoint": self, "path_params": path_params}

    async def handle(self, scope: dict, receive, send) -> None:
        method = scope["method"]
        handler = self._handlers.get(method)
        if handler is None:
            # Complete Allow header — RFC 7231 compliant. Gap-1 fixed.
            allow = ", ".join(sorted(self._handlers))
            if "app" in scope:
                raise HTTPException(status_code=405, headers={"Allow": allow})
            response = PlainTextResponse(
                "Method Not Allowed", status_code=405, headers={"Allow": allow}
            )
            await response(scope, receive, send)
            return
        # Scope updated with actual endpoint — but middleware already executed
        # against scope["endpoint"] = self. Too late for auth decisions.
        # Gap-2 opened at the moment gap-1 closed.
        scope["endpoint"] = handler
        request = Request(scope, receive, send)
        response = await handler(request)
        await response(scope, receive, send)

    def url_path_for(self, name: str, /, **path_params) -> URLPath:
        if name != self.name or set(path_params) != set(self.param_convertors):
            raise NoMatchFound(name, path_params)
        path, remaining = replace_params(
            self.path_format, self.param_convertors, dict(path_params)
        )
        assert not remaining
        return URLPath(path=path, protocol="http")


# Usage — appears correct to all five lenses:
router = Router(routes=[
    PathRouter("/items/{id}", name="item",
               get=get_item, put=update_item, delete=delete_item),
])
# PATCH /items/123 → 405 Allow: DELETE, GET, HEAD, PUT  ← RFC 7231 compliant ✓
# But scope["endpoint"] = PathRouter instance throughout middleware chain   ✗
# auth_middleware(scope["endpoint"]) → inspects PathRouter, not get_item   ✗
```

---

## What Becomes Visible When Lenses Contradict

The contradiction between Pedagogy (PARTIAL is correct) and Scarcity (first-partial-wins) reveals a **conservation law**: **405 correctness and scope["endpoint"] correctness cannot simultaneously hold in a multi-method-per-path routing architecture.**

- If method dispatch is external (current code): Allow header is incomplete, scope["endpoint"] is the first-partial handler → wrong but consistent.
- If method dispatch is internal (PathRouter above): Allow header is complete, scope["endpoint"] is the dispatcher → right on 405, wrong for middleware auth.

Every architectural attempt to fix one side opens the other. This is the L11-C pattern from the project: an impossibility that generates a conservation law. The conserved quantity is: **(Allow correctness) + (endpoint transparency) = constant**. You can redistribute between them but not increase the sum.

The gap is not a bug to be fixed. It's a structural property of the two-phase design (path match → method check).

---

## Recursive Application: Do Lenses Disagree About Their Own Disagreement?

Yes — and sharply.

| Lens | How it explains the inter-lens disagreement |
|------|----------------------------------------------|
| **Pedagogy** | "Disagreement is productive — triangulation teaches what no single frame can." Absorbs the gap as curriculum. |
| **Claim** | "Each lens embeds a claim of sufficiency. The disagreement reveals false claims." Diagnoses other lenses. |
| **Scarcity** | "Analytical bandwidth is finite. Applying five lenses is wasteful — the disagreement is a resource allocation problem." |
| **Rejected\_paths** | "A unified framework was rejected in favor of five specialized lenses. Disagreement is the cost of that choice." |
| **Degradation** | "Lenses drift from original intent with repeated application — finding what they expect, not what's there. Disagreement is lens drift." |

Each lens explains the disagreement in terms that **vindicate itself**. Pedagogy sees it as a teaching opportunity (for pedagogy). Scarcity sees it as waste (that scarcity tracks). This is the meta-disagreement: the lenses cannot agree on whether inter-lens disagreement is good (Pedagogy), bad (Scarcity), inevitable (Rejected\_paths), or symptomatic (Degradation).

**The meta-blindness**: No lens can see that the gaps between lenses are **not properties of the analyzed code** — they're properties of the five-lens coordinate system itself. Applied to any routing code, these same five lenses would produce the same structural disagreements in different positions. The gaps are in the lenses, not in Starlette. The five lenses cannot generate the sixth lens needed to see this, because that lens would need to stand outside the five-dimensional space — and the fifth lens (Degradation) would immediately say "the sixth lens will also drift."

**Meta-meta-blindness**: The five lenses cannot discover that their own coordinate system has boundaries. They can find things within their combined coverage, but cannot find the shape of what's outside it. The analysis terminates not because everything is found, but because the tools for finding more have been exhausted. This is isomorphic to the L13 reflexive ceiling in the project taxonomy: the framework, applied to itself, finds its own fixed point — not truth, but the limit of self-application.

---

## Production Failures Hiding in the Gaps

Ranked by probability and severity:

### 1. Auth middleware 403-masking-405 (Gap 1 × Degradation) — **High probability**

```
Timeline: App ships with 3 middleware (logging, cors, auth).
Month 3: REST endpoints added as separate Route objects (standard pattern).
Month 6: auth middleware updated to check endpoint-level permissions.
Month 7: Support ticket — "OPTIONS /api/users/123 returns 403, not 405."
```

Root cause: PATCH/OPTIONS/DELETE requests trigger PARTIAL on the GET route. `scope["endpoint"]` = `get_user`. Auth middleware sees GET handler → checks read permissions → 403 if user lacks read. The method-not-allowed (405) is permanently hidden behind a permissions error. The endpoint has never supported that method; the user was never unauthorized. The 403 is structurally false.

**Detection lag**: weeks to months, because 403 and 405 look similar in logs and both indicate "request failed."

### 2. RFC 7231 Allow header violation → broken API clients (Gap 1 × Scarcity) — **Near-certain in production**

Any application using separate Route objects for GET/PUT/DELETE on the same path — which is the documented pattern — silently ships incomplete Allow headers. API clients that use Allow to discover supported methods (OpenAPI validators, certain HTTP libraries, CORS preflights for non-standard methods) will malfunction. CORS preflight for `PUT /items/{id}` will fail if GET is registered first and CORS middleware reads the Allow header.

**Detection lag**: never, without explicit RFC 7231 compliance testing.

### 3. url\_path\_for name shadow silently corrupts URLs (Gap between Claim × Degradation) — **Low probability, catastrophic when hit**

```python
# Month 1: shipped
routes = [Route("/confirm/{token}", confirm_email, name="confirm")]

# Month 8: new admin mount added early in list
routes = [
    Mount("/admin", app=admin_app, name="confirm"),  # same name, added first
    Route("/confirm/{token}", confirm_email, name="confirm"),
]
```

`url_path_for("confirm", token="abc123")` now returns the admin Mount URL. Confirmation emails start linking to the admin panel. No exception. No warning. Linear search returns first match.

**Detection lag**: until users report broken confirmation links, which requires monitoring email click-through rates.

### 4. Assert evacuation under container optimization (Claim × Scarcity under -O) — **Latent**

`PYTHONOPTIMIZE=1` (common in production Docker images for minor speed gains) removes every `assert` in Route/Mount `__init__`. A route registered without a leading `/` compiles to a host-matching regex (`compile_path` branches on `not path.startswith("/")`). The route silently becomes a hostname matcher, never matching any path. Zero errors at startup or runtime — just a route that matches nothing, discovered only when a user reports a 404.

---

**The structural prediction**: The production failure you cannot predict is the one that requires lens six — the gap lens — to see. The five lenses together produce a complete picture of their own coverage. The failure outside that coverage is, by construction, invisible until it fails. The routing code is correct within the five-lens coordinate system. The production incident will come from outside it.
