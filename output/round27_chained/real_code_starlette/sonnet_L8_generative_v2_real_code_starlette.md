## Structure First: Level 8 Diagnostic

---

### THE INITIAL CLAIM

**`Route.__init__` uses Python type identity to bifurcate HTTP method enforcement at construction time: function/method endpoints get `self.methods = {"GET", "HEAD"}` by default (enforced by the router), while all other endpoints get `self.methods = None` by default (unenforced by the router). This bifurcation is invisible at the routing API layer, undocumented in any routing interface, and produces opposite security defaults based on Python object taxonomy.**

Falsifiable: register `Route("/data", SomeASGIApp)` where `SomeASGIApp` is a callable class instance, then send `DELETE /data`. The route returns `Match.FULL` because `self.methods` is `None` (falsy), and `handle` also skips method enforcement. The same path registered as `Route("/data", some_function)` returns `Match.PARTIAL` for `DELETE` and generates a 405.

```python
# The mechanism — a single if-branch encodes routing policy as type plumbing:
if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
    self.app = request_response(endpoint)
    if methods is None:
        methods = ["GET"]         # function endpoints: restrict by default
else:
    self.app = endpoint           # class endpoints: methods stays None — no restriction
```

---

### THE THREE-EXPERT DIALECTIC

**Expert 1 — Defender:** The claim holds and is underspecified. The two tiers aren't symmetric variations — they have *opposite* default security postures. Function endpoints are deny-by-default (only GET/HEAD unless explicitly opened). Class endpoints are allow-by-default (any method passes through to the endpoint). A developer migrating an endpoint from a function to a class-based view, without changing the `Route(...)` registration, silently switches from a restricted to an unrestricted posture. No routing-layer API exposes this switch. `Route.methods` returns `None` for class endpoints — a value that is structurally identical to "explicitly unrestricted" but semantically means "enforcement not engaged."

**Expert 2 — Attacker:** The claim identifies the mechanism but misnames the pathology. The real structural problem is that `None` is doing three-valued work: (a) "restriction not set, will default," (b) "explicitly unrestricted," and (c) "enforcement delegated to endpoint." The type dispatch is just what causes `methods` to enter state (c). Fix the type dispatch and you still have two routes to reaching `None` — explicit `methods=None` (the parameter default) and the else-branch — with no runtime distinction between them. The problem is `None` as an overloaded sentinel, not the type check.

**Expert 3 — Probing:** Both of you are accepting the premise that method enforcement belongs at the Route level. Examine what `Route.handle` does with `self.methods`:

```python
async def handle(self, scope, receive, send):
    if self.methods and scope["method"] not in self.methods:
        headers = {"Allow": ", ".join(self.methods)}
```

The `Allow` header is constructed from `self.methods` — a single route's methods. But RFC 7231 requires the `Allow` header to list all methods supported by the *resource at the request URI*, which may span multiple routes. Both of you are arguing about whether `self.methods` is correctly set, while sharing the assumption that `self.methods` is the right place to look. The question neither of you asked: can any component of this system enumerate the full allowed method set for an arbitrary path?

---

### THE TRANSFORMATION

| | Claim |
|---|---|
| **Original** | Type dispatch in `__init__` gives class/function endpoints opposite method-enforcement defaults, invisibly |
| **Transformed** | The routing system has no model of *path-level* method contracts — it has route-level method sets, where `None` means at least three different things and the set is undefined for class endpoints — making it structurally unable to enumerate allowed methods for any given URI |

The original claim was about a **construction-time bifurcation** (fixable by unifying defaults). The transformed claim is about a **model mismatch**: the routing system's primitive is the route, but HTTP's primitive for method semantics is the resource (identified by URI path). These don't align, and no refactor of `Route.__init__` can close the gap.

---

### THE GAP AS DIAGNOSTIC: THE CONCEALMENT MECHANISM

The gap between claims reveals **construction-time policy laundered as runtime infrastructure**.

The type dispatch sits inside `__init__`, the initialization block. Code reviewers read `__init__` as "plumbing" — object construction, adapter selection, type coercion. The `if inspect.isfunction(endpoint_handler)` branch reads as "choosing the right wrapper for the endpoint type" — a compatibility shim, not a policy decision. The words `request_response` (infrastructure) and `self.app = endpoint` (direct assignment) reinforce this reading. Nothing in the code signals that this branch is also choosing a security posture.

This conceals:

1. **The policy is construction-time, not request-time.** Method enforcement for class endpoints cannot be changed by middleware, scope mutation, or routing configuration after construction. The posture is baked in. But because it lives in `__init__` alongside object initialization, it reads as infrastructure, not policy.

2. **The `None` sentinel launders three distinct states.** `self.methods = None` reaches the same runtime branch from: (a) class endpoint with no explicit `methods` (enforcement not engaged), (b) explicit `methods=None` parameter (the Python default — identical semantically to case a, different conceptually), or (c) internal representation of "any method allowed" for hypothetical future use. No caller can distinguish these states.

3. **The Allow header generation reads from the wrong granularity.** `handle` generates `Allow: ", ".join(self.methods)`. For class endpoints, `self.methods` is `None`, so this block never runs — the class endpoint must generate its own 405/Allow internally, or doesn't generate one at all. The routing system silently delegates 405 handling to class endpoints without any verification that they perform it. The contract is assumed, not enforced.

---

### THE LEGITIMATE IMPROVEMENT THAT DEEPENS CONCEALMENT

This refactor extracts the type dispatch into a documented static method. It will pass code review; it looks like proper separation of concerns with explanatory documentation:

```python
class Route(BaseRoute):
    
    @staticmethod
    def _resolve_endpoint(endpoint_handler, methods):
        """
        Determine the appropriate app adapter and effective method set for an endpoint.

        - Function/method endpoints are wrapped in request_response() for Request
          object creation and defaulted to GET-only per REST conventions.
        - ASGI app endpoints are used directly; method routing is their responsibility,
          so no default method restriction is applied (methods=None).

        Returns (app, resolved_methods).
        """
        if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
            return request_response(endpoint_handler), methods if methods is not None else ["GET"]
        return endpoint_handler, methods  # None if not specified — ASGI app owns its dispatch

    def __init__(self, path, endpoint, *, methods=None, name=None,
                 include_in_schema=True, middleware=None):
        assert path.startswith("/"), "Routed paths must start with '/'"
        self.path = path
        self.endpoint = endpoint
        self.name = get_name(endpoint) if name is None else name
        self.include_in_schema = include_in_schema

        endpoint_handler = endpoint
        while isinstance(endpoint_handler, functools.partial):
            endpoint_handler = endpoint_handler.func

        self.app, resolved_methods = self._resolve_endpoint(endpoint_handler, methods)

        if middleware is not None:
            for cls, args, kwargs in reversed(middleware):
                self.app = cls(self.app, *args, **kwargs)

        if resolved_methods is None:
            self.methods = None
        else:
            self.methods = {method.upper() for method in resolved_methods}
            if "GET" in self.methods:
                self.methods.add("HEAD")

        self.path_regex, self.path_format, self.param_convertors = compile_path(path)
```

This improves readability (the `__init__` is shorter), adds documentation (the docstring explains the design), and passes the "extract method" heuristic. It deepens concealment because:

- **Naming launders policy as infrastructure.** `_resolve_endpoint` sounds like it resolves which endpoint to use. Naming it `_assign_method_enforcement_tier` would expose the security bifurcation. The chosen name buries it under "adapter selection."
- **The docstring's last line canonizes the unenforceable contract.** "ASGI app owns its dispatch" is written as architecture decision, not aspiration. The code has no mechanism to verify this. The improvement turns an implicit assumption into official documentation — making future challenge of the assumption feel like a documentation dispute, not a structural critique.
- **The static method placement removes the bifurcation from `__init__`'s flow.** A reviewer reading `__init__` now sees `self.app, resolved_methods = self._resolve_endpoint(...)` — a single line that looks like a lookup. The policy decision has been moved out of the scanning path.

---

### THREE PROPERTIES VISIBLE FROM STRENGTHENING

**1. The docstring had to falsely claim a contract the code cannot verify.**  
When writing `_resolve_endpoint`'s docstring, any honest description of what happens for class endpoints requires explaining that method enforcement is "their responsibility." But the code never checks this. Writing the docstring forced articulation of an assumption treated as a guarantee: the concealment mechanism *requires* a lie at the documentation layer to hold together. The original code hides this by saying nothing.

**2. The return type of `_resolve_endpoint` cannot be written correctly.**  
The signature `-> tuple[app_type, list[str] | None]` forces the `None` question. If `None` means "all methods allowed," the type is misleading. If `None` means "method enforcement not engaged," then callers of the method need a three-way branch, not a two-way one. Writing the type annotation made the `None` sentinel's overloaded semantics impossible to paper over — the type system demanded resolution of an ambiguity the code was hiding in a falsy check.

**3. The method name chose a level of abstraction that makes its own purpose invisible.**  
When choosing between `_resolve_endpoint`, `_resolve_methods`, `_assign_method_enforcement`, and `_wrap_endpoint_for_dispatch`, each name exposes a different aspect of what the function does. No name can honestly cover all the things the function does (type check, wrapper selection, security posture assignment) without implying they belong together — which raises the question of why they belong together. The original inline code hides the question of *why* adapter selection and method default assignment co-occur by never naming the combination.

---

### WHAT THIS ANALYSIS STILL CONCEALS

Everything above — including the two-tier enforcement finding — analyzed method enforcement as a **route-level property**.

The analysis never asked the question: *is a route the correct unit for method enforcement in HTTP?*

RFC 7231 §6.5.5 specifies that the Allow header field in a 405 response "MUST generate an Allow header field containing the list of methods currently supported by the target resource." The *target resource* is identified by URI — not by route object. A URI can match multiple routes (the PARTIAL bug from L7, plus the two-tier class/function split identified here). The "allowed methods for this URI" question requires:

1. Collecting **all** routes whose path matches the URI
2. Unioning their method sets
3. Handling the case where some matched routes have `self.methods = None` (class endpoints that could accept anything)

The current architecture makes all three steps impossible in a single pass. The `Router.app` loop stops at the first `FULL` match, and the PARTIAL collection only retains the first PARTIAL. There is no accumulator for method sets across all matching routes.

The routing system's fundamental primitive is **route → handler dispatch**: given a request, find the right handler. This is the right primitive for dispatch. But method enumeration requires the inverse operation: **path → method set**, which requires a full scan and reduction across all matching routes, not a scan-and-stop. These two operations have different computational shapes. The existing architecture implements only the first.

The concealment: because `Route` objects carry `self.methods` (a plausible place to look for method information), the routing system *looks like* it has a method model. It has method sets per route, which are a necessary component of a method model. But the aggregation operation — union across all routes matching a given path — is not implemented anywhere. The presence of the part conceals the absence of the whole. Any attempt to fix 405 handling within the current architecture (fix PARTIAL collection, unify None semantics) will fail to produce RFC-correct Allow headers because the model mismatch is architectural, not implementational.
