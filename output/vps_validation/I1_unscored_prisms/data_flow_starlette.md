## Step 1: Find the Transformations

1. **compile_path()**:
   - Input: raw path string with parameter placeholders (e.g., "/users/{id:int}")
   - Output: tuple of (regex pattern, path format, parameter converters)
   - Added: regex pattern for matching, parameter conversion logic
   - Preserved: original path structure, parameter names
   - Dropped: parameter details beyond type specification

2. **replace_params()**:
   - Input: path template, parameter converters, path parameters dictionary
   - Output: tuple of (filled path, remaining parameters)
   - Added: actual parameter values in path format
   - Preserved: parameter names that don't match the template
   - Dropped: parameters not in the path template

3. **Route.matches()**:
   - Input: ASGI scope, route path regex
   - Output: match status and child scope with path parameters
   - Added: converted parameter values, endpoint reference
   - Preserved: HTTP method, path structure
   - Dropped: unmatched path portions (handled separately)

4. **Mount.matches()**:
   - Input: ASGI scope, mount path regex
   - Output: match status and child scope with path parameters and root path
   - Added: converted parameter values, root path concatenation, app reference
   - Preserved: path structure, scope type
   - Dropped: unmatched path portions (stored as "path" parameter)

5. **Router.app()**:
   - Input: ASGI scope with route matching information
   - Output: processed ASGI response
   - Added: router reference in scope
   - Preserved: route matching results
   - Dropped: no information dropped, but filters based on match type

## Step 2: Find the Silent Corruption

1. **compile_path()**: Information dropped - parameter validation constraints. When parameters are converted later, there's no check if they meet original constraints defined in the path (like integer range).

2. **replace_params()**: Information dropped - remaining parameters. If parameters remain after replacement, they're silently dropped and not validated against what the route expects.

3. **Route.matches()**: Information dropped - unmatched path segments. Only the matched portion is processed, but there's no way to know how much of the path was matched.

4. **Mount.matches()**: Information corruption - remaining path handling. The "path" parameter is extracted and stored as a path parameter, but its format (with/without leading slash) isn't consistently normalized, causing issues in nested routes.

5. **Router.app()**: Information corruption - partial matches. When a partial match is found, it's used without checking if it's the best possible match, potentially leading to incorrect routing.

## Step 3: The Transformation Law

The most problematic transformation is **Mount.matches()** because it causes multiple downstream issues:

**Conservation Law**: All path information must be preserved through mount points, maintaining consistent path parameter formatting.

| Transformation | Input Shape | Output Shape | Info Dropped/Added | Wrong Result | Preservation Cost |
|----------------|------------|--------------|---------------------|--------------|------------------|
| Mount.matches() | ASGI scope with route path | Child scope with path params and root path | Adds "path" parameter with inconsistent formatting | Nested routes may fail due to path formatting issues | Need consistent path normalization (always with/without leading slash) |

The core issue is that the "path" parameter extracted by Mount.matches() can sometimes have a leading slash and sometimes not, depending on how the original path was structured. This inconsistency causes problems in nested routing where the expected format varies. Preserving all information would require implementing strict path formatting rules, ensuring all "path" parameters have consistent formatting regardless of where they appear in the URL hierarchy.
