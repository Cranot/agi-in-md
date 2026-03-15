# CHANGE RESISTANCE ANALYSIS: Starlette Routing System

## Step 1: New Requirement Seed

**Requirement:** Support for route-level caching headers to be automatically applied based on route configuration

**Trace:**
- **Must change:** `Route` class initialization and `handle` method, `Mount` class initialization and `handle` method
- **What resists:** The current separation between routing and response handling. The `request_response` wrapper creates a tight coupling that makes it hard to add route-specific metadata like cache headers without modifying every route handler.
- **Minimum change:** Add `cache_headers` parameter to `Route` and `Mount` constructors, then modify the `handle` methods to inject headers into the response. Requires ceremony because the current response generation flow is abstracted through the `request_response` decorator.

## Step 2: Contradictory Requirement Seed

**Requirement:** Routes must maintain insertion order for priority-based routing (first match wins) while supporting wildcard routes

**Map:**
- **Battle line:** The `Router.routes` is currently a list, but the matching logic in `Router.app()` doesn't preserve priority for wildcard routes that might match earlier routes partially.
- **What must be sacrificed:** The current partial match logic would need to be changed to track both partial and full matches separately, potentially breaking the current simple "first match wins" approach.
- **Hidden coupling:** The `Route.matches()` method returning `Match.PARTIAL` and `Match.FULL` creates implicit coupling between the route hierarchy and matching priority.

## Step 3: Scaling Seed

**Requirement:** 100x the current route count (thousands of routes instead of hundreds)

**Find:**
- **Wilts first:** The linear search in `Router.app()` (`for route in self.routes:`) - O(n) complexity that becomes apparent at scale
- **Surprisingly resilient:** The regex compilation in `compile_path()` - already pre-compiles patterns, making individual matching fast
- **Overbuilt:** The `URLPath` object creation in `url_path_for()` - the URL construction becomes a bottleneck when generating many URLs for route introspection

**Conservation Law:** A x B = constant (Speed x Flexibility)
When scaling, the tradeoff is between linear search speed (A) and the flexibility of the route matching system (B). The current code sacrifices speed for the flexibility of nested routing and parameter conversion.

## Summary of Change Resistance

1. **Structural rigidity in response handling:** The `request_response` wrapper makes it difficult to add cross-cutting concerns like caching headers without modifying core routing logic.

2. **Implicit coupling between matching and order:** The route matching system doesn't explicitly handle priority conflicts, making it difficult to add sophisticated routing behaviors while maintaining predictable matches.

3. **Linear scaling bottlenecks:** The sequential route matching will become a performance bottleneck at scale, requiring either a different data structure or matching strategy that would change the fundamental behavior of the router.

The code shows strong resistance to adding response-time concerns (Step 1), maintaining predictable routing order with complex patterns (Step 2), and scaling to thousands of routes (Step 3). These resistances stem from the clean but rigid separation of concerns and the simple, linear matching algorithm that makes the code easy to understand but difficult to extend in these specific dimensions.
