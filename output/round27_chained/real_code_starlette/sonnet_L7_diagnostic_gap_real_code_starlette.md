## Structure First: Level 7 Diagnostic

---

### THE INITIAL CLAIM

**`Match.PARTIAL` encodes method-mismatch semantics inside a path-matching concept, making 405 `Allow` headers structurally miscalculated: only the first method-mismatched route contributes to the response, silently discarding allowed methods from all subsequent matching routes.**

Falsifiable because: register `Route("/users", a, methods=["GET"])` and `Route("/users", b, methods=["POST"])`, send `DELETE /users`, and the 405 Allow header will list only GET/HEAD — POST is structurally unreachable.

```python
# The mechanism:
elif match == Match.PARTIAL and partial is None:  # "and partial is None" seals the bug
    partial = route
    partial_scope = child_scope
# Subsequent PARTIAL matches are silently dropped
```

---

### THE THREE-EXPERT DIALECTIC

**Expert 1 — Defender:** The claim holds precisely. `Match.PARTIAL` is a two-valued concept doing three-valued work: "path matched," "path matched and method matched," and implicitly "path matched but method didn't." The enum encoding forces the router loop to collapse all method-mismatched routes to the first one. This is not a corner case — any REST API with separate route objects for each HTTP method on the same path will silently produce incomplete Allow headers.

**Expert 2 — Attacker:** The claim identifies a symptom and misnames the pathology. The actual structural problem is `scope.update(child_scope)` — shared mutable state mutation as the primary coordination mechanism. The code commits to a routing decision by *side-effecting* the scope before the handler runs:

```python
scope.update(child_scope)          # routing decision already made
await route.handle(scope, receive, send)  # handler sees consequences
```

After this update, `scope["endpoint"]`, `scope["path_params"]`, and `scope["root_path"]` have been permanently altered in the dict passed in from the ASGI server. The PARTIAL bug is a local defect. Scope mutation is a global architectural defect.

**Expert 3 — Probing:** Both of you are arguing about *which operation* is the culprit while sharing an assumption that needs examination: that routing has distinguishable phases. You both treat "matching" and "handling" as separable acts. But look at what `matches` actually does — it doesn't evaluate a predicate, it *constructs* `child_scope`:

```python
child_scope = {"endpoint": self.endpoint, "path_params": path_params}
return Match.FULL, child_scope
```

And `url_path_for` reconstructs equivalent information from route configuration at a completely different time. The assumed premise is **separability** — that you can ask "does this match?" independently of "what does this match produce?" The code shows these are structurally inseparable. Both of you are analyzing methods as if they have encapsulated responsibilities. But every method is just a different access pattern on the same mutable dict.

---

### THE TRANSFORMATION

| | Claim |
|---|---|
| **Original** | `Match.PARTIAL` encoding makes 405 method aggregation wrong |
| **Transformed** | The routing system has no stable encapsulation unit: every routing operation transforms a shared mutable dict, making semantics invisible at any single layer |

The original claim was **local and fixable** (five lines). The transformed claim is **architectural** (a design property). The gap is not bridged by refactoring — it requires reconceptualizing what a "route" is.

---

### THE GAP AS DIAGNOSTIC: THE CONCEALMENT MECHANISM

The gap reveals **interface-as-architecture**.

The code presents three clean interfaces — `matches`, `handle`, `url_path_for` — that create the *appearance* of a layered architecture with separation of concerns. These interfaces look like they implement routing as a pipeline: first match, then commit, then handle. This appearance causes all three experts to analyze methods in isolation, looking for the defective method.

But the interfaces correspond to no real encapsulation boundary. All three share `scope` as their medium of communication. `matches` builds a dict fragment. `scope.update()` merges it. `handle` reads from what `update` merged. `url_path_for` re-derives what `matches` would have built, from scratch, using route configuration rather than runtime state. 

The interfaces perform encapsulation symbolically while structurally the system is a single mutable-state transformation pipeline with no phase boundaries. Every bug hunt becomes a hunt for the *wrong method* when the real problem is that no method owns its data. The vocabulary (`Route`, `Match`, `handle`) launders what is actually scope surgery.

---

### WHAT THE MECHANISM IS STILL HIDING

The entire dialectic — including the surfaced concealment mechanism — operated within the **runtime routing** system. It never asked about the relationship between runtime routing and URL generation. This is what remains hidden:

**The forward/reverse routing systems are structurally independent with no consistency guarantee.**

`Route.matches` (forward: request → handler) and `Route.url_path_for` (reverse: name + params → URL) are initialized from the same `compile_path` call. This looks like a single source of truth. But they execute in completely different computational models with no shared runtime state:

- **Forward routing** is imperative and stateful: iterates routes in registration order, mutates scope, stops at first FULL match, handles redirects via a second full traversal.
- **Reverse routing** is recursive and exception-driven: throws `NoMatchFound` up a traversal tree, reconstructs URLs by concatenating `path_format` strings.

The specific incoherence: **a URL returned by `url_path_for` is not guaranteed to directly match via `matches` without a redirect.**

`Router.app` implements redirect-slash logic as a *second routing pass*:

```python
# First pass: no match
# Then: try with slash added/removed
for route in self.routes:
    match, child_scope = route.matches(redirect_scope)
    if match != Match.NONE:
        redirect_url = URL(scope=redirect_scope)
        response = RedirectResponse(url=str(redirect_url))
```

This creates a class of URLs that are *reachable* (redirect → match) but not *directly routable* (no direct match). `url_path_for` generates the canonical form — but canonical under whose normalization? `Mount.__init__` strips trailing slashes (`self.path = path.rstrip("/")`). `url_path_for` strips them again (`path_prefix.rstrip("/")`). The generated URL is normalized, but `matches` may accept both normalized and un-normalized forms, with redirect-slash logic handling the difference silently.

There is no assertion, test, or structural guarantee anywhere in this code that:

```
url = router.url_path_for(name, **params)
# url, when requested, will directly match the route owning `name`
```

The forward and reverse systems were written to be consistent, and mostly are. But the code implements two separate surjections from URL-space to handler-space with no formal composition. The routing system claims to be a bijection; structurally it is two independent traversals that must agree by convention.

This remained hidden because the dialectic exhausted itself on runtime scope mutation — the visible pathology — and never asked the type-theoretic question: **what is the routing system's claim about URL-space, and is that claim structurally enforced?** Interface-as-architecture concealed the runtime problem. The runtime problem concealed the model-consistency problem underneath it.
