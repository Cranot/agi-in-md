## Structural Mechanism Analysis

### Mechanism 1: Scope Mutation Chain

**What it actually enforces:** A hidden data-flow contract where each route silently injects state into a mutable dictionary that all downstream handlers depend on but cannot declare.

**Input:** Immutable ASGI scope (nominally) + route-specific extraction (path_params, endpoint reference)

**Output:** Mutated scope with accumulated state (`path_params`, `endpoint`, `root_path`, `app_root_path`, `router`)

**What breaks if removed:** The entire system collapses. Handlers expect `scope["path_params"]` and `scope["endpoint"]` to exist, but these are injected by routes, not the ASGI server. Remove the mutation and handlers receive incomplete context.

**Hidden dependency:** Every handler has an undeclared dependency on `Route.matches()` having run first. The `scope` parameter appears to come from the ASGI server, but critical keys are route-injected. This creates temporal coupling invisible in handler signatures.

---

### Mechanism 2: Reversed Middleware Wrapping

**What it actually enforces:** A control-flow inversion where the *last* middleware in the list becomes the *outermost* wrapper, making execution order the reverse of declaration order.

**Input:** Ordered list of middleware `(class, args, kwargs)` tuples

**Output:** Nested call stack where `middleware[-1]` wraps `middleware[-2]` wraps ... wraps `app`

**What breaks if removed:** Request/response processing still works, but all cross-cutting concerns (auth, logging, error handling) execute in wrong order. An auth middleware declared before logging would execute *after* logging on response.

**Hidden dependency:** Middleware authors assume they can short-circuit the chain. This only works because reversal creates the correct "first-declared, first-executed" illusion. The reversal is the mechanism that makes declarative order match intuitive execution order.

---

### Mechanism 3: Partial Match Reservation

**What it actually enforces:** A silent fallback state machine where routes that match path but fail method-validation are held in reserve, only activated if *no* route fully matches.

**Input:** Request scope with path + method

**Output:** Either immediate dispatch (FULL), deferred dispatch with 405 implications (PARTIAL), or continuation to next route (NONE)

**What breaks if removed:** Without PARTIAL, a POST to a GET-only route would return 404 instead of 405. The distinction between "route doesn't exist" and "route exists but wrong method" would vanish.

**Hidden dependency:** The `partial` variable in `Router.app()` creates hidden control flow. Routes don't know they're being "held" — the Router silently remembers PARTIAL matches and resurrects them. This creates a temporal coupling between the match loop and the fallback path.

---

## Concealment-Deepening Modification

**Modification:** Change `Route.matches()` to return `Match.FULL` for path-match/method-mismatch, but inject a special `scope["_method_blocked"] = True` marker instead of returning `Match.PARTIAL`.

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
            if self.methods and scope["method"] not in self.methods:
                child_scope["_method_blocked"] = True  # Concealed rejection
                child_scope["_allowed_methods"] = self.methods
            return Match.FULL, child_scope  # Always FULL
    return Match.NONE, {}
```

The Router's dispatch loop now has no PARTIAL handling — it dispatches immediately. The handler (or a wrapper) checks `_method_blocked` and returns 405. External behavior identical, but the fallback state machine is now invisible from Router's perspective.

---

### Emergent Property 1: Handler Becomes Method Validator

**Why invisible:** In original, method validation happens at match-time. Routes self-filter. The Router never sees a method-blocked request reach a handler.

**What surfaced:** The modification forces handlers (or their wrappers) to validate method. This reveals that "method validation" was never inherently a routing concern — it was an optimization that conflated matching with filtering. The handler now owns its own preconditions.

---

### Emergent Property 2: Scope Becomes Control-Flow Carrier

**Why invisible:** In original, `Match` enum controls flow. PARTIAL means "wait." Scope is data, not control.

**What surfaced:** The `_method_blocked` key makes scope a control-flow mechanism. This reveals that scope was always a hidden communication channel — routes already injected `endpoint` to signal "this is the handler." The modification makes the pattern explicit and extensible. Routes could now inject arbitrary directives.

---

### Emergent Property 3: Partial Match Reservation Was Defensive, Not Fundamental

**Why invisible:** The PARTIAL/FULL distinction appears to encode semantic truth about match quality. A PARTIAL match is "incomplete."

**What surfaced:** With modification, 405s work without PARTIAL. This reveals that PARTIAL was an implementation choice (optimization: check method during match, not during handle), not a structural necessity. The "reservation" pattern was defensive — it let the Router handle method validation without trusting handlers to do it. The modification removes this indirection and trusts handlers.

---

## Conservation Law

**Expressiveness × Safety = Constant**

Where:
- **Expressiveness** = the range of routing behaviors the system can encode (method filtering, path params, mounts, redirects, fallbacks)
- **Safety** = the guarantees the system provides (no handler runs without validation, no scope mutation surprises, no hidden control flow)

Increasing expressiveness (allowing routes to inject arbitrary scope keys, removing PARTIAL to let handlers decide) decreases safety (handlers must validate their own preconditions, scope becomes a backchannel). Increasing safety (Router validates everything, scope is immutable data) decreases expressiveness (routes cannot extend the protocol, handlers are constrained).

The Starlette design occupies a specific point on this curve: routes inject specific known keys (moderate expressiveness) but Router handles method fallback (moderate safety). The modification moves toward higher expressiveness (routes can inject `_method_blocked` and anything else) and lower safety (handlers must check, Router trusts blindly).
