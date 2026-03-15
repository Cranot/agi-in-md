## Structure First: Level 11 Diagnostic

---

### THE INITIAL CLAIM

**`Route.__init__` establishes L10's `self.methods = None` sentinel not by design but by detection: runtime type inspection — `inspect.isfunction or inspect.ismethod` applied to the unwrapped endpoint — silently partitions every endpoint into one of two routing contracts (function-route: explicit method set, routing-layer enforcement; class-route: delegation, `self.methods = None`), then discards the type information into a value. Both contracts exit the constructor as `Route`. Every downstream mechanism — `matches`, `handle`, Allow-header generation, `url_path_for` annotation, aggregation probes — must re-run the same binary split (`if self.methods is None:`) the constructor already ran, because no type-level distinction survives construction. L8–L10's problems are not independent bugs at separate mechanisms; they are the same reconstruction effort, repeated at each mechanism, against the same discarded type information.**

Falsifiable:

```python
async def func_handler(request): ...

class ClassHandler:
    async def __call__(self, scope, receive, send): ...

r1 = Route("/path", func_handler, methods=None)  # identical call
r2 = Route("/path", ClassHandler, methods=None)  # identical call

assert r1.methods == {"GET", "HEAD"}  # None → ["GET"] → {"GET","HEAD"}
assert r2.methods is None

# Same argument. Same return type. Different routing contracts.
scope = {"type": "http", "method": "POST", "path": "/path", "path_params": {}}
assert r1.matches(scope)[0] == Match.PARTIAL   # wrong method → routing-layer partial
assert r2.matches(scope)[0] == Match.FULL      # no constraint → full match
```

The routing contract (PARTIAL vs FULL for a wrong-method POST) is determined by `self.methods is None` — a value check that reconstructs the binary classification the constructor ran and discarded. The constructor was the only oracle; the type information is gone.

---

### THE THREE-EXPERT DIALECTIC

**Expert 1 — Defender:** The claim is structurally exact. The unwrapping loop, the `inspect.isfunction or inspect.ismethod` branch, the `if methods is None: methods = ["GET"]` inside the function branch: this is the precise location where the routing system bifurcates. One branch wraps with `request_response`, defaults methods to GET; the other leaves both untouched. The type information — "this was a function," "this was a class" — is consumed and emitted as the value of `self.methods`. `Route.__init__` is an entropy point: information in, value out, type gone. Every downstream `if self.methods is None:` is evidence of lost information being reconstituted.

**Expert 2 — Attacker:** "Detection" is loaded. The Starlette documentation explicitly states that function-based views default to GET and class-based views handle their own method dispatch. The `inspect.isfunction` check is the mechanical enforcement of a documented convention. The downstream `if self.methods is None:` checks are not reconstituting lost information — they are reading a deliberately set feature flag. Calling this "entropy" misrepresents intentional design as accidental information loss.

**Expert 3 — Probing:** Both arguments assume the heuristic is accurate. Neither has asked: what does `inspect.isfunction or inspect.ismethod` actually classify? It classifies Python callables by their Python type, not by their HTTP semantics. A classmethod retrieved as `MyClass.my_classmethod` satisfies `inspect.ismethod` → function-route, `methods` defaults to GET. If `my_classmethod` was intended to handle POST, it silently never receives POST requests. A lambda satisfies `inspect.isfunction` → function-route, GET-only. A callable instance doesn't satisfy either → class-route, all-methods. The heuristic is a proxy: "is this a Python function?" substitutes for "what HTTP methods does this handle?" These are correlated for common cases and divergent for edge cases. The key question: when the proxy misclassifies, is there any mechanism to detect or correct it? The answer is no — the type information is gone after construction, and no downstream component can distinguish "correctly classified" from "incorrectly classified."

---

### THE TRANSFORMATION

| Level | Claim |
|---|---|
| **L10 transformed** | `url_path_for` projects 2D routing (URL × method) onto 1D; the dropped method dimension is where L8's sentinel and L9's closed boundary live |
| **L11 initial** | The `self.methods = None` sentinel is detected (runtime type inspection) rather than declared; the detection is lossy; every consumer re-runs the same binary split |
| **L11 transformed** | The routing system has no TYPE for routing contract. There is no `FunctionRoute` / `ClassRoute` distinction in the type system, no `MethodDeclaringEndpoint` / `MethodDelegatingEndpoint` protocol boundary. The routing contract — "which level enforces method matching?" — is an emergent value property (`self.methods is None`) rather than a designed type property. L8's sentinel, L9's closed boundary, and L10's dimensional projection are not three separate problems; they are the same missing type appearing at three call sites. Every component asks `if self.methods is None:` because there is no type that answers once. The structural question is not "how do we aggregate method information across routes?" — it is "why does every component in this system independently reconstruct the same binary classification?" |

**Gap**: L11 initial locates the problem in the constructor's detection mechanism. L11 transformed locates it in the **absence of a routing contract type**. The detection is a symptom: the constructor must detect because there is no type to declare. Every downstream `is None` check is a symptom: there is no type to dispatch on.

---

### THE CONCEALMENT MECHANISM: TYPE CONVERGENCE BEFORE DIVERGENCE

`Route(path, endpoint, *, methods=None, ...)` is a convergence point. Before it runs: structurally different inputs — functions, classes, partials of functions, bound methods, callable instances. After it runs: one type, `Route`. The structural information that distinguishes routing contracts is consumed and stored as a value. From the outside, you cannot determine which contract a `Route` implements without reading `self.methods`. That check is a value condition, not a type condition — it cannot be used for static dispatch, type narrowing, or Protocol checking. Every component that needs to branch on routing contract must implement its own detection.

Three things this concealment hides:

**1. The heuristic misclassifies silently.** `MyClass.my_classmethod` — in Python 3, a classmethod retrieved via the class — satisfies `inspect.ismethod`. Result: function-route contract, `self.methods` defaults to `{"GET", "HEAD"}`. If the classmethod was intended to handle POST, it is silently restricted to GET at construction time with no error, no warning, and no downstream signal. The uniform constructor makes this invisible because the type information that would reveal the misclassification — "this was a classmethod, not a regular method" — is gone before any caller can inspect it.

**2. The constructor applies two hidden transformations, not one.** `self.methods` (public) records the method contract. `self.app` (also public, but structurally opaque) records a second transformation: function endpoints get `request_response(endpoint)` wrapping — converting the `func(request) → response` convention to ASGI `(scope, receive, send)` — while class endpoints get the endpoint directly. These transformations are aligned (both depend on `isfunction`) but not stated in the constructor's public interface. Per-route middleware (the `middleware` parameter) wraps `self.app` after this transformation — meaning the middleware wraps `request_response(endpoint)` for function routes and wraps the raw endpoint for class routes. The same `middleware=` argument wraps different things depending on endpoint type. The concealment: route-level middleware appears uniform but is not.

**3. The detection is frozen at construction; the contract is consumed at every request.** `Route.__init__` runs once. `Route.matches` and `Route.handle` check `self.methods` at every request. For class endpoints, `self.methods = None` correctly defers to the endpoint — which handles its own dispatch at request time and is always current. But for class endpoints that COULD have declared their methods at construction time (endpoints with a fixed `supported_methods` class variable, or endpoints following the `get`/`post` naming convention), the routing layer will never see that information. The constructor's detection algorithm was the only moment to capture it. There is no mechanism to provide method information after construction.

---

### THE IMPROVEMENT

Add an explicit routing contract protocol that class endpoints can implement, replacing heuristic detection with explicit declaration:

```python
from typing import ClassVar, FrozenSet, Protocol, runtime_checkable

@runtime_checkable
class RoutingContract(Protocol):
    """
    Protocol for ASGI endpoint classes that declare their supported HTTP
    methods to the routing layer at construction time.

    Implementing this protocol allows the routing layer to enforce method
    matching (returning Match.PARTIAL for wrong-method requests rather than
    Match.FULL), to generate accurate Allow headers, and to annotate
    url_path_for results with correct method information — without heuristic
    type detection.

    Endpoints that do not implement this protocol retain the existing
    behavior: self.methods = None, all path-matching requests return
    Match.FULL regardless of method, and method dispatch is handled
    entirely within the endpoint's __call__ implementation.

    ``supported_methods`` must be a frozenset of uppercase HTTP method
    strings. HEAD is added automatically if GET is included.

    Example::

        class ItemsEndpoint:
            supported_methods: ClassVar[FrozenSet[str]] = frozenset(["GET", "POST"])

            async def __call__(self, scope, receive, send):
                if scope["method"] == "GET":
                    await self._list(scope, receive, send)
                elif scope["method"] == "POST":
                    await self._create(scope, receive, send)
    """
    supported_methods: ClassVar[FrozenSet[str]]


class Route(BaseRoute):
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

        if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
            self.app = request_response(endpoint)
            if methods is None:
                methods = ["GET"]
        else:
            self.app = endpoint
            # Opt-in: if the endpoint class explicitly declares its routing
            # contract via RoutingContract, use that declaration rather than
            # defaulting to None. Explicit declaration eliminates the heuristic.
            # Only applies when methods= is not specified by the caller.
            if methods is None and isinstance(endpoint_handler, RoutingContract):
                methods = list(endpoint_handler.supported_methods)

        if middleware is not None:
            for cls, args, kwargs in reversed(middleware):
                self.app = cls(self.app, *args, **kwargs)

        if methods is None:
            self.methods = None
        else:
            self.methods = {method.upper() for method in methods}
            if "GET" in self.methods:
                self.methods.add("HEAD")

        self.path_regex, self.path_format, self.param_convertors = compile_path(path)
```

This passes code review: `RoutingContract` is a `@runtime_checkable` `Protocol` with a single `ClassVar` — standard Python typing; the `isinstance` check is additive (conditional on `methods is None`); existing endpoints without the protocol continue to work identically; the improvement is fully backward-compatible; the docstring correctly explains the behavior differential and provides a usage example.

---

### THREE PROPERTIES VISIBLE BECAUSE OF THE IMPROVEMENT

**1. `@runtime_checkable isinstance` checks attribute PRESENCE, not type.** `isinstance(MyClass, RoutingContract)` returns True if `MyClass` has a `supported_methods` attribute — regardless of its type or value. An endpoint with `supported_methods = "GET"` (a string) passes the check. `list("GET")` → `["G", "E", "T"]` → `self.methods = {"G", "E", "T"}`. The route accepts no real HTTP method. The protocol annotation `ClassVar[FrozenSet[str]]` is documentation, not enforcement. Writing `isinstance(endpoint_handler, RoutingContract)` looks rigorous but is structurally unverified. The improvement trades heuristic detection (imprecise by type) for protocol checking (imprecise by value structure) without eliminating imprecision.

**2. `supported_methods` is a static declaration that must stay synchronized with the endpoint's internal dispatch.** An endpoint that declares `supported_methods = frozenset(["GET", "POST"])` and handles GET and POST in its `__call__` now has two sources of method truth: routing declaration and dispatch implementation. Adding a PUT handler in `__call__` without updating `supported_methods` causes routing-layer 405 for PUT even though the endpoint would handle it correctly. The original design deliberately avoided this synchronization requirement: class endpoints controlled their own dispatch precisely because the routing layer couldn't know their methods. By asking class endpoints to declare methods, the improvement creates a new class of desynchronization failure with no mechanical enforcement. The original problem — two independently maintained representations of method information — is moved from the framework/endpoint boundary into the endpoint class itself.

**3. The improvement reveals that the route is the wrong locus for the routing contract.** `RoutingContract` is checked against the endpoint class, but a single endpoint class is often reused across multiple routes with different method restrictions:

```python
routes = [
    Route("/items",       ItemsEndpoint, methods=["GET"],        name="items.read"),
    Route("/items",       ItemsEndpoint, methods=["POST"],       name="items.write"),
    Route("/items/{id}",  ItemsEndpoint, methods=["GET", "PUT"], name="item"),
]
```

`ItemsEndpoint.supported_methods` would need to cover all methods the endpoint might handle across all routes. But the specific restrictions are route-level concerns, not endpoint-level concerns. `RoutingContract` conflates endpoint capability ("what can it handle?") with route constraint ("what should reach it?"). This conflation only becomes visible when the same endpoint is reused at multiple routes — a standard pattern the protocol cannot represent correctly.

---

### DIAGNOSTIC APPLIED TO THE IMPROVEMENT

**What does it conceal?** `RoutingContract` looks like it eliminates coupling between endpoint and routing layer by replacing detection with declaration. But it introduces a new coupling: the endpoint class must now reference a routing-layer protocol (`RoutingContract`), know that `supported_methods` is a routing concern, and keep it synchronized with dispatch logic. The original design's key property — any ASGI callable can be an endpoint with no knowledge of Starlette's routing layer — is weakened. An endpoint implementing `RoutingContract` is no longer a pure ASGI app; it is a Starlette-routing-aware component. The improvement conceals this architectural coupling behind a lightweight surface (`supported_methods: ClassVar[FrozenSet[str]]` looks like a simple annotation), while its implications are structural: the endpoint layer now has a runtime dependency on routing-layer conventions.

**What property of the original problem is visible only because the improvement recreates it?** The improvement forces a new declaration site for method information: `supported_methods` at the routing layer, and the dispatch logic at the endpoint layer. These must agree. L9 identified the same split at the framework level — `Route.matches` checks `self.methods` AND `Route.handle` re-checks `self.methods`, independently, with no mechanical enforcement of their agreement. The improvement moves this split from the framework to the application: developers now maintain `supported_methods` (routing representation) and `__call__` dispatch (endpoint representation) with the same structural gap. **The property visible because of the improvement: the split between routing-layer method declaration and endpoint-layer method dispatch is not a Starlette implementation choice — it is a property of any system that has both layers. No improvement to the routing layer's protocol eliminates the split; it relocates it.**

---

### THE SECOND IMPROVEMENT

Addresses the synchronization requirement by making method discovery automatic — introspecting the endpoint class rather than requiring explicit declaration:

```python
_HTTP_VERB_NAMES: frozenset[str] = frozenset(
    ["get", "post", "put", "patch", "delete", "head", "options", "trace"]
)


def _discover_class_methods(cls: type) -> Optional[frozenset[str]]:
    """
    Discover the HTTP methods a class endpoint handles by inspecting its MRO
    for HTTP-named handler methods, following the HTTPEndpoint convention.

    Walks the class MRO, stopping before ``object``, and collects callable
    attributes whose names match HTTP method verbs. This correctly handles
    class inheritance: a method defined in a base class is visible to
    subclasses via the MRO walk.

    Returns a frozenset of uppercase HTTP method strings, or None if no
    HTTP-named methods are found (indicating the class uses a non-convention
    dispatch mechanism and should retain self.methods = None).

    HEAD is added automatically if GET is discovered.
    """
    if not inspect.isclass(cls):
        return None

    found: set[str] = set()
    for klass in cls.__mro__:
        if klass is object:
            break
        for verb in _HTTP_VERB_NAMES:
            if verb in vars(klass) and callable(vars(klass)[verb]):
                found.add(verb.upper())

    if not found:
        return None
    if "GET" in found:
        found.add("HEAD")
    return frozenset(found)


class Route(BaseRoute):
    def __init__(self, path, endpoint, *, methods=None, name=None,
                 include_in_schema=True, middleware=None):
        ...
        endpoint_handler = endpoint
        while isinstance(endpoint_handler, functools.partial):
            endpoint_handler = endpoint_handler.func

        if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
            self.app = request_response(endpoint)
            if methods is None:
                methods = ["GET"]
        else:
            self.app = endpoint
            if methods is None:
                discovered = _discover_class_methods(endpoint_handler)
                if discovered is not None:
                    methods = list(discovered)
                # If still None: endpoint handles dispatch internally
        ...
```

---

### DIAGNOSTIC APPLIED TO THE SECOND IMPROVEMENT

**What does it conceal?** `_discover_class_methods` stops the MRO walk at `object`. The rationale is: non-`object` classes define endpoint behavior. But consider:

```python
class DefaultMethodHandler:
    """Base class that provides 405 responses for all HTTP methods."""
    async def get(self, request): return Response("Method Not Allowed", 405)
    async def post(self, request): return Response("Method Not Allowed", 405)
    # ... all verbs
```

A class inheriting from `DefaultMethodHandler` without overriding any method has `get` and `post` in the MRO walk (found in `vars(DefaultMethodHandler)`). The discovery returns `{"GET", "HEAD", "POST", ...}`. `self.methods` is set to the full set. The routing layer now ALLOWS all methods (routing-layer FULL match), and passes them to the endpoint, which returns 405 internally. The routing-layer 405 (PARTIAL → correct Allow header via L9's closed boundary) never fires. The discovery incorrectly upgrades `self.methods = None` (endpoint controls dispatch) to `self.methods = {"GET", "HEAD", "POST", ...}` (routing layer enforces), when the endpoint's convention-named methods are sentinel 405 handlers, not real HTTP handlers. The concealment: `verb in vars(klass)` conflates "callable attribute named 'get'" with "HTTP GET handler." These are correlated by convention, not by enforcement.

**What property of the original problem is visible only because the improvement recreates it?** `_discover_class_methods` walks `cls.__mro__` — a hierarchy — and aggregates information across levels. This is structurally identical to the Router-level aggregation L10's second improvement attempted: iterating `self.routes` — a hierarchy of route objects — to aggregate method information across sibling routes. Both improvements face the same problem: the correct answer for the WHOLE (what methods does this resource/endpoint handle?) requires aggregation across PARTS (all routes at this path / all classes in the MRO), and no single part has the complete picture. Both face the same stopping-criterion problem: where does the "relevant" hierarchy end? (`object` for the MRO; the full route list for the router — but what about Mounts?). Both produce incorrect results for hierarchies that don't match the assumed shape. **The self-similar structure is now explicit: the per-route / per-resource gap L10 identified at the route level reappears at the class level as per-class / per-MRO gap. The improvement at one level recreates the problem at the adjacent level.**

---

### THE STRUCTURAL INVARIANT

The property that persists through every improvement, at every level — through L8's sentinel, L9's closed boundary, L10's dimensional projection, L11's detection mechanism, the protocol opt-in, and the MRO introspection:

**Method-correctness is a whole-hierarchy property, but the routing system provides only part-level access. The correct answer to "what methods does this resource/endpoint handle?" requires aggregating across the relevant whole — route list, class MRO — and no single element of any hierarchy holds the complete picture. Every improvement relocates the aggregation problem to a different hierarchy level, where the same incompleteness recurs. This self-similarity is not an implementation artifact; it is a consequence of information structure: method information is distributed across hierarchies by design (routes are registered independently, classes inherit independently), and no element of any hierarchy was intended to know the whole. L10's formulation — "method dispatch at two levels with `None` as boundary" — is a surface expression of this invariant. The `None` sentinel is where the invariant breaks surface at one particular level. The invariant is what makes the `None` necessary.**

---

### THE CATEGORY BOUNDARY

The invariant defines the category of designs where: **routes are the basic unit of routing identity, and resources — paths with complete method sets — are reconstructed from routes by aggregation at runtime.**

In this category: method information is partial at the route level (one route knows one method subset, or delegates via `None`); every correct aggregate (resource method set, Allow headers, `url_path_for` annotation) requires scanning the full route list; class endpoint method information requires the full MRO; the same aggregation problem appears self-similarly at every hierarchy level.

Starlette's routing system is in this category. Every framework that uses "register routes independently, then dispatch" is in this category — Flask, FastAPI, Django URL patterns, Express. The category is large; the structural problems are shared.

---

### THE ADJACENT CATEGORY: RESOURCE-FIRST ROUTING

The adjacent category is where the invariant dissolves: **resources are the basic unit of routing identity, and routes are method contributions to resources rather than independent objects.**

In this design:
- A resource owns a path pattern, a name, and a complete method → handler mapping
- Method handlers are added to resources; they are not registered as independent routes
- The resource's method set is always current — it IS the resource's own data, not reconstructed from sibling routes
- `url_path_for(resource_name)` resolves to one resource → one URL, with no per-route ambiguity
- 405 Allow headers are read from the resource's method map — no aggregation, no scanning
- Class endpoints implement resources (they supply the method map) rather than being passed as opaque callables to routes; the `None` sentinel dissolves because every resource has an explicit method map by construction

Concretely:

```python
# Current design (route-list category):
routes = [
    Route("/items", list_handler,   methods=["GET"],  name="items.list"),
    Route("/items", create_handler, methods=["POST"], name="items.create"),
]

# Adjacent design (resource-first category):
items = Resource("/items", name="items")
items.add_handler("GET",  list_handler)
items.add_handler("POST", create_handler)
router = Router(resources=[items])
```

`router.url_path_for("items")` → `/items` with `methods={"GET","HEAD","POST"}`, no aggregation. `DELETE /items` → 405 with `Allow: GET, HEAD, POST` from the resource map directly.

**How this succeeds where every improvement failed:** every improvement attempted to aggregate method information from existing route objects. Aggregation fails because routes are independent with partial information; any stopping criterion for the aggregation scan is a heuristic. The resource-first design makes aggregation unnecessary: method information is complete AT THE RESOURCE LEVEL BY DEFINITION. There is no `self.methods = None` sentinel — resources do not accept method handlers without explicit method declarations. The question "what methods does this endpoint handle?" never arises unanswered, because the resource IS the answer.

---

### THE NEW IMPOSSIBILITY

In the adjacent category, the property trivial in the current design — **independent route identity** — becomes impossible.

In the current design:

```python
routes = [
    Route("/items", list_handler,   methods=["GET"],  name="items.list"),
    Route("/items", create_handler, methods=["POST"], name="items.create"),
]
```

- `url_path_for("items.list")` and `url_path_for("items.create")` both resolve, independently, to `/items`
- Per-route middleware: `Route("/items", create_handler, methods=["POST"], middleware=[auth])` — only POST requires auth
- Per-route schema: `Route("/items", list_handler, include_in_schema=False)` — GET hidden from generated schema while POST remains visible
- Each route has a distinct name, a distinct handler, and an independent lifecycle

These are TRIVIALLY supported because each route object is an independent entity.

In the resource-first design, the `/items` resource is ONE unit:
- `url_path_for("items")` → `/items` — one name, one URL; there is no `url_path_for("items.create")` because `items.create` is not a routing target, it is a method handler within the `items` resource
- Method-specific middleware must be expressed inside the resource or inside individual handlers — not as a property of an independent route
- Schema inclusion is a resource-level property — you cannot hide GET and expose POST without the resource knowing about schema
- A template generating a link to "the URL that creates items" and a template generating a link to "the URL that lists items" resolve to the same URL with no type-level distinction

The collapse of per-route identity into per-resource identity is not a minor API inconvenience — it eliminates the expressive distinction between "what URL should this form submit to?" and "what URL should this link point to?" In the resource-first model, these questions have the same answer: the resource URL.

---

### THE FINDING

**The routing system's expressiveness and its correctness are in structural opposition.**

**Old impossibility (route-list design):** Correct, complete method information at any hierarchy level — the correct Allow header (L9), the accurate `url_path_for` method annotation (L10), the correct routing contract type (L11) — cannot be derived from any route's local information alone. Every mechanism that needs it must aggregate. Every aggregation faces the same self-similar incompleteness: sibling routes are invisible to per-route logic; mounted routes are opaque to outer-Router aggregation; base-class methods are ambiguous to per-class MRO introspection. No improvement eliminates the aggregation requirement; it only relocates it to a level where the same problem recurs.

**New impossibility (resource-first design):** Independent route identity — the ability to name, annotate, middleware-wrap, and schema-include individual method handlers at a path as independent routing targets — cannot exist when routes are method contributions to resources rather than independent objects. The per-route names, per-route middleware, per-route schema flags, and per-route `url_path_for` identities that make the current system expressive require route independence. Route independence is exactly what makes the current system incorrect.

**The finding:** The structural problems identified in L8 through L11 — three-valued sentinel, closed boundary, dimensional projection, self-similar aggregation — are not implementation deficiencies to be fixed. They are the cost of route independence. Route independence is also the source of the API expressiveness that makes Starlette usable: `Route("/items", handler, name="items.create", middleware=[auth], include_in_schema=True)` treats a method handler as a first-class, independently addressable entity. The routing system **cannot** be simultaneously route-independent and resource-correct. Every framework that chooses route independence pays the cost in aggregation failures. Starlette pays it in `self.methods = None`, incorrect Allow headers, dimensional projection, and self-similar MRO incompleteness. The trade-off is real and irreducible: **routing flexibility demands route independence; routing correctness demands resource aggregation; and these demands are structurally incompatible within a single routing primitive.**
