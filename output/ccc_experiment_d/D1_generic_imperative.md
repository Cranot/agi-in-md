I'll apply the L12 meta-conservation prism to analyze this Starlette routing code and identify what it conceals.

## Structural Analysis

### Claim
Starlette's routing system provides clean, declarative route matching with full parameter conversion and flexible mounting.

### Dialectic
The code excels at: precise regex-based path matching, sophisticated parameter conversion, elegant middleware composition, and clean Mount/Route/Router hierarchy. It handles both HTTP and WebSocket with proper 404/redirect logic.

### Gap
The routing system cannot simultaneously guarantee: (1) precise path matching, (2) arbitrary parameter flexibility, and (3) performance at scale. The system sacrifices performance when requiring arbitrary parameter validation and type conversion.

### Mechanism
The mechanism is: **Information Laundering**. Path parameters launder raw string input through type conversion, losing context about original input format and validation boundaries. This enables clean URL generation but obscures potential security risks and conversion failures.

Application: The `compile_path()` function transforms path patterns like `/users/{user_id:int}` into regex `(?P<user_id>[0-9]+)` and conversion functions. When a request comes in, the raw path segment is matched against the regex, then passed through `param_convertors[key].convert(value)`. The original string format information is lost, making it impossible to distinguish between "123" (int) and "00123" (string → int).

### What This Conceals

1. **Path Ambiguity at Scale**: With many routes, partial matches can dominate processing. The Router iterates all routes, and with complex regex patterns, CPU usage grows non-linearly with route count.

2. **Parameter Validation Boundaries**: Type conversion silently accepts invalid inputs. `{user_id:int}` converts "abc" to error, but "123" and "00123" both become 123, losing precision information that might be significant for routing logic.

3. **Mount Fragmentation**: Mount routes create regex with `/{path:path}` which matches everything, effectively swallowing any subsequent route definitions. The system relies on route ordering but doesn't warn about shadowed routes.

4. **Method Matching Costs**: Checking `scope["method"] not in self.methods` for every route creates O(n) method checks. With many routes, this becomes a bottleneck.

5. **URL Generation Complexity**: The `url_path_for()` method requires exact parameter matching, but doesn't validate that generated URLs would actually match the route back - creating a potential inconsistency between routing and URL generation.

The system conceals that routing is actually a sequence of information transformations with accumulating costs and potential information loss at each step.
