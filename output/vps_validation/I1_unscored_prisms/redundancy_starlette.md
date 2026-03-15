# Redundancy Prism Analysis

## Step 1: Find the Repetitions

I've identified the following repeated patterns in the code:

1. **Parameter Handling Pattern**: Found in `Route.matches()` and `Mount.matches()`
   - Both extract path parameters from regex matches
   - Both convert parameter values using param_convertors
   - Both update child_scope with path_params
   - Both handle HTTP and WebSocket scope types

2. **Route Matching Logic**: Found in `BaseRoute.__call__()`, `Route.matches()`, and `Mount.matches()`
   - All check if scope["type"] matches supported types
   - All handle Match.NONE, Match.PARTIAL, and Match.FULL states
   - All update scope with child_scope

3. **Middleware Handling**: Found in `Route.__init__()`, `Mount.__init__()`, and `Router.__init__()`
   - All apply middleware by wrapping the app
   - All use reversed(middleware) and iterate through cls, args, kwargs

4. **Path Replacement Logic**: Found in `replace_params()` and used in both `Route.url_path_for()` and `Mount.url_path_for()`
   - Both use similar parameter replacement with path_format and param_convertors
   - Both handle remaining parameters similarly

5. **Not Found Handling**: Found in `BaseRoute.__call__()` and `Router.not_found()`
   - Both handle 404 responses for HTTP requests
   - Both handle WebSocket closing
   - Both check scope["type"] before taking action

## Step 2: Find the Drift Risk

1. **Parameter Handling Pattern**:
   - Drift risk: If one update changes how parameters are extracted or converted but not the other
   - Inconsistency: One might convert parameters differently, causing routing errors
   - No obvious drift detected currently

2. **Route Matching Logic**:
   - Drift risk: High - if Match handling logic changes in one place but not others
   - Inconsistency: Could cause some routes to match when they shouldn't or vice versa
   - No obvious drift detected currently

3. **Middleware Handling**:
   - Drift risk: Medium - middleware application logic could diverge
   - Inconsistency: Different middleware behavior between Route, Mount, and Router
   - No obvious drift detected currently

4. **Path Replacement Logic**:
   - Drift risk: High - path building is critical to routing correctness
   - Inconsistency: URL generation could produce different results for same parameters
   - No obvious drift detected currently

5. **Not Found Handling**:
   - Drift risk: Medium - response handling could diverge
   - Inconsistency: Different 404 responses or WebSocket handling in different contexts
   - No obvious drift detected currently

## Step 3: The Abstraction Law

The highest drift risk is in the **Route Matching Logic** pattern due to its central role in the routing system and potential for inconsistent handling of match states.

| Repeated Pattern | Locations | Drift Scenario | Wrong Behavior | Abstraction Cost |
|------------------|-----------|----------------|----------------|------------------|
| Route Matching Logic | BaseRoute.__call__, Route.matches, Mount.matches | One class updates Match handling but others don't | Routes match incorrectly or don't match when they should, causing 404 errors or wrong endpoints | Moderate - requires creating a shared matching strategy that maintains flexibility for each route type |
| Path Replacement Logic | replace_params function, Route.url_path_for, Mount.url_path_for | Parameter conversion logic changes in one place but not others | URL generation produces incorrect paths with wrong parameters or formatting | Low - simple refactoring to ensure consistent parameter handling |
| Not Found Handling | BaseRoute.__call__, Router.not_found | Response handling differs between contexts | Inconsistent 404 responses or websocket behavior | Very Low - can be unified with minimal changes |
| Parameter Handling Pattern | Route.matches, Mount.matches | Parameter extraction/conversion diverges | Route matching fails or converts parameters incorrectly | Medium - requires creating a shared parameter processing utility |
| Middleware Handling | Route.__init__, Mount.__init__, Router.__init__ | Middleware application logic differs | Inconsistent middleware behavior between route types | Low - can be unified with a shared middleware application utility |
