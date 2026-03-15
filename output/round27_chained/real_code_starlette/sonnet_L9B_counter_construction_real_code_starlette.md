## Structure First: Level 9 Counter-Construction

---

### THE INITIAL CLAIM

**`Router.app` uses `match != Match.NONE` as the redirect trigger in `redirect_slashes` scanning, which causes `Match.PARTIAL` — whose primary meaning in the dispatch loop immediately above is "path matched, method rejected" — to authorize a 301 redirect. In the space of fifteen lines, the same enum value means "wrong method → accumulate for 405" and "path found → redirect is appropriate." These two readings are semantically incompatible. The code structure makes the flip invisible.**

Falsifiable: `Router([Route("/data", func, methods=["GET"])], redirect_slashes=True)` + `DELETE /data/`. The main dispatch loop produces `NONE` (path regex `^/data$` does not match `/data/`). The redirect loop checks `/data` with DELETE: `Route.matches()` returns `PARTIAL` (path matched, DELETE not in `{"GET", "HEAD"}`). `PARTIAL != Match.NONE` is True. Router issues `301 /data`. Client follows redirect. `DELETE /data` → 405. The 301 is permanent: RFC 7231 §6.4.2 specifies it "SHOULD be followed with the same method," so the client has cached a permanent redirect to a URI that rejects its method.

```python
# The two readings of PARTIAL in the same method — fifteen lines apart:

# READING 1 — dispatch loop: PARTIAL = wrong method → accumulate for 405
elif match == Match.PARTIAL and partial is None:
    partial = route
    partial_scope = child_scope

# READING 2 — redirect loop: PARTIAL treated as "path found → redirect valid"
for route in self.routes:
    match, child_scope = route.matches(redirect_scope)
    if match != Match.NONE:         # PARTIAL qualifies
        redirect_url = URL(scope=redirect_scope)
        response = RedirectResponse(url=str(redirect_url))
        await response(scope, receive, send)
        return
```

---

### THE THREE-EXPERT DIALECTIC

**Expert 1 — Defender:** The claim is correct and undersells the severity. The 301 is permanent and cacheable. A client that sends `DELETE /data/` once will receive a cached permanent redirect: subsequent `DELETE /data/` requests go directly to `DELETE /data` without consulting the server, permanently to a 405. This affects every API client that uses non-idempotent methods with any trailing-slash typo on any function endpoint with explicit method restrictions. The `redirect_slashes=True` default means every Starlette application with function-based routes has this behavior unless explicitly disabled.

**Expert 2 — Attacker:** The claim identifies the wrong fix. Changing `!= Match.NONE` to `== Match.FULL` doesn't solve the problem because `Match.FULL` is itself ambiguous. For class endpoints, `self.methods` is `None`, so the condition `if self.methods and scope["method"] not in self.methods` never fires — class endpoints return `Match.FULL` for every method regardless of whether they support it. A `Mount("/data", some_asgi_app)` returns `FULL` for `DELETE /data`, which would pass the `== Match.FULL` check and issue the redirect — but the ASGI app may return 405. The problem is not the condition; `Match.FULL` doesn't mean "this method is supported," it means "this method was not rejected at the routing layer."

**Expert 3 — Probing:** Both of you are arguing about when to redirect. Neither of you asked whether the routing system can know enough to redirect correctly at all. Trailing-slash canonicalization is a *resource identity* claim: "the canonical URI for this resource is `/data`, not `/data/`." But the routing system has no concept of resources — only routes. A route at `/data` and the absence of a route at `/data/` doesn't establish that they refer to the same resource. They could be different resources that happen to be adjacent in path space. The routing system cannot distinguish "these are URI variants for the same resource" from "these are different resources and one happens to be unregistered." Neither of you is asking: can the routing system know if a redirect is semantically appropriate, or is it always guessing?

---

### THE TRANSFORMATION

| | Claim |
|---|---|
| **Original** | `redirect_slashes` treats `Match.PARTIAL` (wrong method) as "path found → 301 appropriate," inverting its dispatch meaning |
| **Transformed** | The routing system has no resource primitive — only route objects — so it cannot determine whether trailing-slash canonicalization and method enforcement are the same concern, orthogonal concerns, or incommensurable concerns for a given URI. The redirect decision is structurally underdetermined: no condition written against `Route.matches()` return values can correctly capture "this redirect target will accept this method" |

The original claim identified a condition that was wrong. The transformed claim identifies the missing concept that would make the correct condition *writable*. Expert 2 showed that `== Match.FULL` fails for class endpoints. A condition like "FULL and methods explicitly set" requires reading `Route.methods` from the Router — breaking the `BaseRoute` abstraction, since `Mount` has no `methods` attribute. There is no predicate over current routing primitives that means "the alternate URI will support this method," because the routing system has no way to commit to what any URI supports across all its routes.

---

### THE GAP AS DIAGNOSTIC: THE CONCEALMENT MECHANISM

**Context-stripped enum reuse across adjacent code blocks.**

The `Match` enum carries the context of its primary use site: `Route.matches()`, which generates PARTIAL by comparing `scope["method"]` against `self.methods`. In that context, PARTIAL encodes a specific causal structure: path regex matched, method not in allowed set. This context is encoded in the *value* but not in the *name* — `PARTIAL` is semantically neutral. It could mean "partially matched," "partially valid," or "incomplete match."

When `Router.app` reaches the redirect loop, it calls `route.matches(redirect_scope)` and receives the same enum. The condition `match != Match.NONE` reads in natural English as "if the route has any match on this path" — which is accurate: PARTIAL routes *did* partially match. The method-mismatch context that generated PARTIAL is invisible at the consuming site because the enum name doesn't encode it.

Three reinforcing layers:

1. **Spatial separation.** The dispatch loop and the redirect loop occupy the same method but are separated by the PARTIAL-accumulation block and an early return. A reviewer scanning `Router.app` correctly interprets PARTIAL in the dispatch loop, reaches `if partial is not None: ... return`, and mentally resets. The redirect loop reads as a new question about a new scope.

2. **Scope renaming as context reset.** `redirect_scope = dict(scope)` followed by path modification creates a new variable name that signals "different context, different URI." The reviewer's attention is on the path transformation. The method field in `redirect_scope` is unchanged — still the method that was rejected as PARTIAL moments earlier — but the new variable name makes this invisible.

3. **Feature naming focuses attention on the path dimension.** `redirect_slashes` is about slashes. The reviewer's mental frame is "does the alternate slash form exist?" PARTIAL reads as "alternate path exists." The question "does the alternate path support *this* method?" is not in the reviewer's mental frame because the feature name doesn't invoke method dispatch.

---

### THE LEGITIMATE IMPROVEMENT THAT DEEPENS CONCEALMENT

Extract `_get_slash_redirect_url`. The extraction names the semantic correctly at the wrong level of abstraction, then documents the inversion as a design decision:

```python
# Router.app — dispatch section unchanged, then:
route_path = get_route_path(scope)
if scope["type"] == "http" and self.redirect_slashes and route_path != "/":
    redirect_url = self._get_slash_redirect_url(scope, route_path)
    if redirect_url is not None:
        response = RedirectResponse(url=str(redirect_url))
        await response(scope, receive, send)
        return

await self.default(scope, receive, send)

def _get_slash_redirect_url(self, scope: Scope, route_path: str) -> URL | None:
    """
    Determine whether a trailing-slash canonical redirect should be issued.

    Checks whether the slash-variant of the requested path has a registered
    route. Both FULL matches (path + method) and PARTIAL matches (path
    registered, method enforcement handled downstream) qualify — this check
    concerns URI-space canonicalization, not method dispatch. The two concerns
    are intentionally orthogonal: a resource's canonical URI form is independent
    of which methods it accepts.

    Returns the redirect URL if a registration exists at the alternate form,
    None otherwise.
    """
    redirect_scope = dict(scope)
    if route_path.endswith("/"):
        redirect_scope["path"] = redirect_scope["path"].rstrip("/")
    else:
        redirect_scope["path"] = redirect_scope["path"] + "/"

    for route in self.routes:
        match, _ = route.matches(redirect_scope)
        if match != Match.NONE:  # Any registration at this path suffices
            return URL(scope=redirect_scope)
    return None
```

This passes code review: `Router.app` is shorter, the logic is documented, and the docstring explicitly addresses PARTIAL. It deepens concealment because:

- **"Method enforcement handled downstream" is accurate and misleading simultaneously.** Downstream enforcement *does* happen — at `/data` after the 301. But "handled downstream" implies the redirect respects enforcement, when it precedes and ignores it. The statement is true at the individual-step level and false at the system level. Documentation-as-accuracy replaces code-as-ambiguity: a future reviewer reading the docstring finds an explanation and stops investigating.

- **"Intentionally orthogonal" canonizes a decision the original code made by omission.** The original code never decided that canonicalization and method dispatch are orthogonal — it simply used `!= Match.NONE` without considering PARTIAL's method-mismatch semantics. The docstring promotes the omission into an architectural principle. Future challenges to the behavior must now defeat explicit documentation rather than supply missing reasoning.

- **The extracted method becomes the trace terminus.** Someone debugging `DELETE /data/` → 301 → 405 will find `_get_slash_redirect_url`, read "URI-space canonicalization, not method dispatch," and conclude "that's by design." The original inline code required engaging with the condition itself; the extraction provides an answer that ends the investigation.

---

### THREE PROPERTIES VISIBLE FROM STRENGTHENING

**1. The docstring was forced to invent a theory that the implementation falsifies.**

Writing "URI-space canonicalization is independent of which methods a resource accepts" required articulating *why* PARTIAL qualifies. The theory is: URI form and method support are orthogonal. But after the redirect, the method outcome at the canonical URI becomes the user-visible result of the canonicalization — if the resource at `/data` doesn't support DELETE, the canonicalization produced a permanent redirect to a 405, which is the opposite of orthogonality. The docstring stated a principle that the system's behavior contradicts. Writing the docstring made this visible; the original `!= Match.NONE` hid it by providing no rationale to contradict.

**2. The return type `URL | None` forced the function to collapse three cases into two.**

Writing the signature forced a choice: return URL (redirect) or return None (don't redirect). But there are three distinct situations: (a) redirect target fully supports method → redirect valid, (b) redirect target path exists but method rejected → redirect produces 301 → 405, (c) redirect target unregistered → don't redirect. The binary return type collapses (a) and (b) into the same return value. The original code had the same collapse, but it was invisible because there was no return type to count states. Writing the signature made the missing third return value visible: there is no way to tell the caller "a path registration exists but the redirect will fail."

**3. The method wanted to live on `Route`, not on `Router`.**

When designing `_get_slash_redirect_url`, the natural primitive would be `route.path_matches(path)` — a predicate that checks the path regex without method comparison. Instead, the implementation calls `route.matches(redirect_scope)` and discards the FULL/PARTIAL distinction, which is exactly the method information `matches()` went to the trouble of computing. The extraction revealed a missing primitive: path-only matching, independent of method. The original code hid the missing primitive by using `!= Match.NONE` — implicitly discarding the method dimension without naming the operation that discards it.

---

### THE SECOND IMPROVEMENT (Contradiction)

The first improvement normalizes "PARTIAL = path registered → redirect appropriate." The contradicting improvement enforces "PARTIAL = method mismatch → redirect inappropriate":

```python
def _get_slash_redirect_url(self, scope: Scope, route_path: str) -> URL | None:
    """
    Determine whether a trailing-slash canonical redirect should be issued.

    Only issues a redirect if the alternate path has a FULL match — meaning
    a route that covers both the path pattern AND the request method. A PARTIAL
    match (path registered, method not allowed) means the resource exists but
    will reject this method; redirecting in that case produces the anti-pattern:

        301 (permanent) to a URI → 405

    This is worse than a direct 405: the 301 is cached, permanently directing
    clients to a failing URI. The conservative check prevents this.
    """
    redirect_scope = dict(scope)
    if route_path.endswith("/"):
        redirect_scope["path"] = redirect_scope["path"].rstrip("/")
    else:
        redirect_scope["path"] = redirect_scope["path"] + "/"

    for route in self.routes:
        match, _ = route.matches(redirect_scope)
        if match == Match.FULL:          # Only fully-matched routes are redirect targets
            return URL(scope=redirect_scope)
    return None
```

This also passes code review. The anti-pattern it prevents (301 → 405 permanent caching) is immediately comprehensible. The change from `!= Match.NONE` to `== Match.FULL` is a single token with explicit justification. Both improvements inhabit the same extracted method with the same signature and differ by one condition. Both have PR descriptions that would receive approval.

---

### THE STRUCTURAL CONFLICT

**The conflict that exists only because both improvements are legitimate:**

Improvement 1 (PARTIAL qualifies) correctly handles class endpoints. A class endpoint at `/data` has `self.methods = None`, so `Route.matches()` returns `Match.FULL` for all methods — including DELETE. Improvement 1 would correctly redirect `DELETE /data/` to `DELETE /data` where the class endpoint accepts any method. But Improvement 1 also redirects when the route is a function endpoint with `methods=["GET"]` — where PARTIAL correctly signals "method rejected."

Improvement 2 (FULL only) correctly prevents the 301 → 405 caching anti-pattern for function endpoints. But `Match.FULL` has two distinct meanings: (a) "path matched AND method is in the allowed set" for function endpoints, and (b) "path matched AND method enforcement was not consulted" for class endpoints. Improvement 2 treats both as "redirect appropriate." For case (b), FULL doesn't mean the method is supported — it means the routing layer deferred the question to the endpoint, which may return 405 itself.

**The structural conflict:** `Match.FULL` cannot distinguish "method explicitly permitted" from "method enforcement not engaged." Any condition that checks `match == Match.FULL` cannot separate these cases without reading `route.methods` — which violates the `BaseRoute` abstraction (Mount has no `methods`). Any condition that checks `match != Match.NONE` cannot separate "path exists with method support" from "path exists without it."

Neither condition can be correct for both endpoint types because the Match enum's FULL value is semantically overloaded: it maps two distinct routing states (method confirmed, method deferred) to the same symbol.

**The conflict is the L8 bifurcation propagating through the Match enum to the redirect decision.**

L8 identified that `Route.__init__` creates two security postures at construction time — function endpoints get explicit method restriction, class endpoints get method enforcement deferred. The structural conflict between Improvement 1 and Improvement 2 is the same bifurcation, now visible at the redirect-decision level. The construction-time split (function: `self.methods = {"GET", "HEAD"}`, class: `self.methods = None`) produces a matching-time split (`PARTIAL` vs `FULL` for the same path with a wrong method), which produces a redirect-time split (both improvements fail for one of the two cases). L8 called this "construction-time policy laundered as runtime infrastructure." What L8 did not see: the laundering succeeds because the Match enum propagates the policy forward — the `__init__` bifurcation is not contained in `__init__`. It infects every consumer of `route.matches()`.

The structural conflict exists only because both improvements are legitimate: there genuinely ARE two endpoint types that require different redirect behavior, and the routing system has no way to distinguish them at the point where the redirect decision must be made. The conflict between Improvement 1 and Improvement 2 is not resolvable without either collapsing the two-tier endpoint model (the L8 fix) or extending the Match enum to carry the information that was discarded at construction time.

---

### WHAT THIS ANALYSIS STILL CONCEALS

Both this analysis and L8 analyzed the routing system as a *dispatch* system. Neither asked what happens when the routing system is used as a *query* system.

The redirect loop is a registration-level query — "is a route registered at this path?" — executed using a request-level API. The call `route.matches(redirect_scope)` creates a full scope, performs a full regex match, performs a method comparison, and returns a three-valued match result. The redirect loop needs only the path-regex match; the method comparison is wasted work whose result is then discarded via `!= Match.NONE`. The routing system has no API for "does any route's path pattern cover this path?" — which is a *structural* query, not a *dispatch* query. The only available operation is request matching, which conflates path coverage with method dispatch.

This gap recurs. `url_path_for` is also a registration-level query (given a route name and parameters, construct a URL). It's implemented as a linear search over route objects, each of which raises `NoMatchFound` as control flow. The exception-as-control-flow in `url_path_for` is the registration-query pattern executed via a dispatch API — the same structural mismatch, in a different place.

The routing system implements one operation well: *given a request, find the right handler.* It implements two other operations by pressing dispatch into service: *given a path, find a registration* (redirect_slashes) and *given a name, find a URL* (url_path_for). Both secondary operations fail in ways that are traceable to using the wrong primitive. The redirect-slashes bug (method information leaks into a path-existence check) and the url_path_for exception-as-control-flow (exception is the normal path, not an error path) are both symptoms of a system with one primitive being used for three distinct query shapes.

The concealment: `route.matches()` is a plausible API to call for "does a route exist here?" — it returns `Match.NONE` when the path doesn't match, which looks like "no, nothing here." The API's name and return values support the misuse. The fact that `matches()` returns *more* than the path-existence answer (it also returns method disposition) is not an error — in the dispatch context, that extra information is useful. It becomes a bug only when the caller discards the extra information incorrectly, which `!= Match.NONE` does silently. The routing system has one well-designed API used for three operations, with no indication at the call site which operation is intended. The missing primitives — `path_covered_by(path)`, `method_supported_at(path, method)` — are invisible because the existing API is expressive enough to approximate them, badly.
