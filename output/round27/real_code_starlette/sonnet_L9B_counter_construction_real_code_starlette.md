## Initial Claim

**`Match.PARTIAL` is semantically incoherent: it encodes an HTTP-layer concern (method mismatch) using routing-layer vocabulary, splitting method dispatch logic across three locations without a coherent owner.**

Falsifiable prediction: if PARTIAL meant "routing partially resolved," Mount would use it. Mount never returns PARTIAL — only Route does, only when the path matches but the method doesn't. Therefore the routing loop's partial-fallback path exists solely to generate 405 responses, not to resolve routes.

---

## Three Expert Views

**Defender:** The design is intentional ASGI discipline. PARTIAL preserves the distinction between "route exists but method wrong" and "route doesn't exist," which matters for correct 405 vs 404 semantics. The scope is not mutated upstream; child_scope is a derived copy. The three-location method check is belt-and-suspenders: `matches()` classifies, `handle()` enforces. This is defense in depth.

**Attacker:** `Route.handle()` re-checks `self.methods` after `Router.app()` already used the PARTIAL signal to select the route. The information is duplicated and must be kept in sync. Worse, once `scope.update(partial_scope)` runs, the routing decision is irreversible — but no response has been sent. The "commitment" to a route precedes the "execution" of the response. If `handle()` raises, scope is already dirty.

**Prober (what both take for granted):** Both assume the Match enum describes routing states. Neither questions whether path resolution and method dispatch should share a type. The enum implies these are three points on one spectrum: "found nothing / found something partial / found exactly." But PARTIAL doesn't mean "found something partial" — it means "found exactly the right path, but the HTTP method is wrong." This is a full match in routing terms and a failure in HTTP terms. Both experts are debating inside a frame the code constructed.

---

## How the Claim Transforms

**Original:** Method logic is split across three locations with no clear owner.

**Transformed:** The real problem is that `BaseRoute` has no interface for "what methods do I accept?" Routes cannot advertise their capabilities; they can only react to requests. So method checking must be embedded in request processing, which forces routing (path resolution) and HTTP compliance (method enforcement) to be entangled. The split across three locations is a symptom. The cause is a missing declarative capability interface.

**The diagnostic gap:** I claimed the problem was structural disorder (logic in three places). The transformed claim reveals the problem is a missing abstraction (no `allowed_methods()` interface). The disorder is the shadow; the missing abstraction is the object.

---

## The Concealment Mechanism

**Vocabulary laundering through enum precision.**

The Match enum looks rigorous — three named states, an ordered integer backing, crisp semantics. This precision *performs* correctness without achieving it. PARTIAL sounds like it describes routing resolution degree. It actually describes HTTP method compliance. The enum borrows the authority of a well-typed sum type to smuggle a domain boundary violation into what looks like clean code.

Secondary mechanism: **symmetrical-looking duplication.** `Route.matches()` checks methods and returns PARTIAL. `Route.handle()` checks methods and returns 405. These look like the same check in two necessary contexts. They aren't — one is classification for the router, one is enforcement for HTTP. Making them look identical hides that they serve different masters.

---

## Improvement 1: Extract `_find_route` — Deepens Concealment

```python
# In Router:
def _find_route(self, scope):
    """
    Scan routes and return the best match.
    Returns (route, child_scope, is_definitive).
    is_definitive=False means a better match may exist elsewhere.
    """
    best_partial: BaseRoute | None = None
    best_partial_scope: dict | None = None

    for route in self.routes:
        match, child_scope = route.matches(scope)
        if match == Match.FULL:
            return route, child_scope, True
        elif match == Match.PARTIAL and best_partial is None:
            best_partial = route
            best_partial_scope = child_scope

    if best_partial is not None:
        return best_partial, best_partial_scope, False
    return None, None, False

async def app(self, scope, receive, send):
    assert scope["type"] in ("http", "websocket", "lifespan")
    if "router" not in scope:
        scope["router"] = self
    if scope["type"] == "lifespan":
        await self.lifespan(scope, receive, send)
        return

    route, child_scope, is_definitive = self._find_route(scope)

    if route is not None:
        scope.update(child_scope)
        await route.handle(scope, receive, send)
        return

    # redirect_slashes logic unchanged...
    route_path = get_route_path(scope)
    if scope["type"] == "http" and self.redirect_slashes and route_path != "/":
        redirect_scope = dict(scope)
        redirect_scope["path"] = (
            redirect_scope["path"].rstrip("/")
            if route_path.endswith("/")
            else redirect_scope["path"] + "/"
        )
        for route in self.routes:
            match, _ = route.matches(redirect_scope)
            if match != Match.NONE:
                redirect_url = URL(scope=redirect_scope)
                response = RedirectResponse(url=str(redirect_url))
                await response(scope, receive, send)
                return

    await self.default(scope, receive, send)
```

**Why this passes review:** It has a docstring. It names the concept (`is_definitive`). It simplifies `app()`. It makes the routing decision look like a single responsibility separated from dispatch. It's a textbook extraction refactor.

**Why it deepens concealment:** `is_definitive` is a boolean that erases the reason for non-definitiveness. The caller doesn't know whether `is_definitive=False` means "method mismatch" or "path partially resolved" or anything else. The enum distinction between PARTIAL and FULL is now hidden behind a bool, making it *harder* to ask "why is this non-definitive?" The vocabulary laundering moved one level deeper.

---

## Three Properties Visible Only Through Strengthening

**1. `Match.PARTIAL` has no legitimate users after extraction.** When `_find_route` is clean enough to reason about independently, you notice that nothing can return PARTIAL except Route's method check — and you'd naturally want to express that as something other than a routing state. The improvement forces this vacancy into view.

**2. The routing loop's fallback priority is underdetermined.** Inside `_find_route`, a docstring demands you specify: what if two routes both return PARTIAL? What if a PARTIAL match appears before the only FULL match? The original code hides this through inline flow control that doesn't invite scrutiny. The extraction forces a signature that demands a return type, and the return type has no principled way to represent "best of several partials."

**3. Mount and Route produce incompatible FULL semantics.** When `_find_route` treats all FULL matches identically, it becomes obvious that Route's FULL means "path + method resolved" while Mount's FULL means "prefix consumed, defer to sub-app." These are not the same guarantee. The is_definitive bool was supposed to add precision but exposed that FULL itself is overloaded.

---

## Improvement 2: Collapse PARTIAL — Contradicts Improvement 1

```python
class Match(Enum):
    NONE = 0
    FULL = 1  # Path resolved. Method compliance is the handler's concern.


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
                return Match.FULL, child_scope  # Always full if path resolves
        return Match.NONE, {}

    async def handle(self, scope, receive, send):
        if self.methods and scope["method"] not in self.methods:
            # Collect allowed methods across all matching routes (injected by Router)
            allowed = scope.get("_allowed_methods", self.methods)
            headers = {"Allow": ", ".join(sorted(allowed))}
            if "app" in scope:
                raise HTTPException(status_code=405, headers=headers)
            response = PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)


# Router.app() gains a two-phase scan for correct Allow header construction:
async def app(self, scope, receive, send):
    assert scope["type"] in ("http", "websocket", "lifespan")
    if "router" not in scope:
        scope["router"] = self
    if scope["type"] == "lifespan":
        await self.lifespan(scope, receive, send)
        return

    for route in self.routes:
        match, child_scope = route.matches(scope)
        if match == Match.FULL:
            scope.update(child_scope)
            await route.handle(scope, receive, send)
            return

    # No path match. Compute allowed methods for 405 if applicable.
    if scope["type"] == "http":
        allowed_methods = set()
        for route in self.routes:
            # Re-probe with method stripped to detect path-only matches
            if isinstance(route, Route):
                probe = self.path_regex.match(get_route_path(scope))
                if probe and route.methods:
                    allowed_methods |= route.methods
        if allowed_methods:
            headers = {"Allow": ", ".join(sorted(allowed_methods))}
            if "app" in scope:
                raise HTTPException(status_code=405, headers=headers)
            response = PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
            await response(scope, receive, send)
            return

    # redirect_slashes and default unchanged...
    await self.default(scope, receive, send)
```

**Why this passes review:** It aligns with HTTP's resource model: routing resolves the resource, the resource enforces its own method constraints. It simplifies the enum. It eliminates the redundant method check in `matches()`. It correctly aggregates allowed methods for the Allow header. The logic for method errors is now in one place per responsibility layer.

---

## The Structural Conflict

**Improvement 1 says:** The routing layer must record method information during matching (via PARTIAL or a finer-grained mechanism) because the router is the only entity that can enumerate all routes for a given path and construct the correct `Allow` header.

**Improvement 2 says:** The routing layer must not concern itself with methods because path resolution and HTTP method dispatch are orthogonal concerns. Method enforcement belongs in handlers; routers resolve paths.

Both improvements are responding to the same defect (the ownership gap for method enforcement) and both are internally coherent. Neither is wrong.

**The conflict only exists because both are legitimate:** If Improvement 1 were over-engineering, Improvement 2 would simply be correct simplification. If Improvement 2 were under-specification, Improvement 1 would simply be correct precision. They conflict because `BaseRoute` has no interface for "what methods am I capable of serving?" — no `allowed_methods()` declaration, no capability advertisement separate from request handling.

**The structural conflict:** *Method matching is not a routing concern, but it must be a routing concern, because routes are the only objects with method knowledge and the router is the only object with visibility across all routes.* Until routes can declare capabilities independently of processing requests, method enforcement must live in routing's vocabulary — and every improvement to the routing layer will either reinforce that coupling (Improvement 1) or suppress it temporarily (Improvement 2) while the fundamental tension remains.

The code's real concealment is this: it presents the problem as "where does the method check go?" when the actual missing abstraction is the question it never asks — "how does a route advertise what it can do?"
