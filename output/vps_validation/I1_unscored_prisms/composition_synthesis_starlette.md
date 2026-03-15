# Composition Synthesis: Starlette Routing

## Step 1: The Overlapping Boundaries

The analyses share these boundaries:

1. **Route matching boundary** (`matches` method in `BaseRoute`)
   - Error view: Sees when no route matches (404 response)
   - Performance view: Sees partial matches and must continue searching

2. **Parameter processing boundary** (`replace_params` function)
   - Error view: Sees parameter conversion failures
   - Performance view: Sees unnecessary parameter copying

3. **Dispatch boundary** (`Router.__call__` and `Router.app`)
   - Error view: Sees exception propagation
   - Performance view: Sees middleware stack traversal

## Step 2: The Hidden Connection

1. **Route matching boundary**:
   - Error handling: Triggers 404 response immediately on no match
   - Performance workaround: Continues search on partial matches
   - Coupling: The faster failure (404) avoids costly partial match processing

2. **Parameter processing boundary**:
   - Error handling: Fails fast on parameter conversion errors
   - Performance workaround: Modifies path_params in-place to avoid copying
   - Coupling: Robust parameter validation prevents costly runtime failures

3. **Dispatch boundary**:
   - Error handling: Propagates exceptions through middleware
   - Performance workaround: Uses middleware stack for early returns
   - Coupling: Middleware stack overhead buys better error isolation

## Step 3: The Joint Law

The conservation law is **Information Tradeoff Between Certainty and Speed**.

| Boundary | Error View | Performance View | Coupling | Joint Conservation Law |
|----------|------------|------------------|----------|-----------------------|
| Route matching | 404 response on no match | Early termination on partial match | Early failure prevents costly search | Certainty (correct response) ↔ Speed (quick dispatch) |
| Parameter processing | Parameter conversion validation | In-place parameter modification | Robust validation prevents runtime costs | Correctness (valid params) ↔ Efficiency (minimal copying) |
| Dispatch | Exception propagation through middleware | Early returns in middleware stack | Stack overhead buys error isolation | Error containment ↔ Response latency |
