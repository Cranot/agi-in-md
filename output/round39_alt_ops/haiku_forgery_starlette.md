# Starlette Routing Analysis: Forging the Impostor

## Step 1: Build the Forgery

The impostor implementation would replace the current route matching strategy with a **Prefix Tree (Trie) approach** combined with a **WebAssembly-compiled regex engine**:

```python
class TrieNode:
    def __init__(self):
        self.children = {}
        self.param_routes = {}
        self.literal_routes = {}
        self.is_leaf = False

class RouteMatcher:
    def __init__(self):
        self.root = TrieNode()
        self.wasm_regex = WebAssemblyRegexEngine()
    
    def add_route(self, path, route):
        node = self.root
        segments = path.split('/')
        
        for i, segment in enumerate(segments):
            if segment.startswith('{'):
                # Handle parameter segments
                param_name = segment[1:-1]
                if ':' in param_name:
                    param_name, param_type = param_name.split(':')
                else:
                    param_type = 'str'
                
                if param_name not in node.param_routes:
                    node.param_routes[param_name] = {}
                
                if param_type not in node.param_routes[param_name]:
                    node.param_routes[param_name][param_type] = TrieNode()
                
                node = node.param_routes[param_name][param_type]
            else:
                # Handle literal segments
                if segment not in node.literal_routes:
                    node.literal_routes[segment] = TrieNode()
                node = node.literal_routes[segment]
        
        node.route = route
        node.is_leaf = True
```

**Key differences from original:**
1. **Data Structure**: Replace regex compilation with trie-based path segmentation
2. **Parameter Handling**: Store parameter converters per trie node instead of global compilation
3. **Matching Algorithm**: Use trie traversal + WASM-compiled regex for parameter validation
4. **URL Generation**: Traverse trie backwards with stored path formats

**Easy to replicate:**
- HTTP/WebSocket scope handling
- Middleware stack composition
- Redirect slash logic
- Basic endpoint dispatch

**Forced different approach:**
- The original's regex compilation in `compile_path()` is deeply tied to parameter validation
- Route matching performance optimizations in the current implementation
- The URL path generation's parameter replacement logic in `replace_params()`

## Step 2: Name the Unfakeable

1. **Exact Parameter Constraint Validation**: The original `compile_path()` function enforces strict parameter constraints during path compilation. The validation occurs upfront rather than during matching. The trie-based approach would need to replicate this exact behavior - rejecting paths with duplicated parameter names at definition time, not request time.

2. **Regex Pattern Compilation Semantics**: The original compiles regex patterns once per route definition and reuses them. The WASM-based approach would need to maintain identical regex behavior across different JavaScript engines. The compilation in `compile_path()` creates converters with specific `regex` and `convert` attributes that must be preserved.

3. **Path Parameter Scope Propagation**: The original maintains a clear separation between path parameters and matched parameters in `BaseRoute.__call__()`. The scope updates follow a specific pattern where `path_params` accumulates from parent routes through nested Mount compositions. The trie version must preserve this exact propagation mechanism.

4. **URL Format Reconstruction**: The original's `path_format` in `compile_path()` creates a template for URL reconstruction that preserves the exact original path structure with placeholders. The trie version would need to store additional metadata to reconstruct this same format.

## Step 3: Derive the Conservation Law

**Conserved Quantity**: Path Parameter Constraint Invariance

The gap reveals that regardless of implementation strategy, any correct routing system must preserve the invariant that **path parameter constraints are validated at definition time and maintained consistently across route matching and URL generation**.

**The Law**: Route Definition Rigidity × Path Matching Flexibility = Constant

The original implementation shows:
- High Route Definition Rigidity (strict parameter validation at compile time)
- Moderate Path Matching Flexibility (regex allows complex patterns)

The forgery would reverse this:
- Low Route Definition Rigidity (trie allows more dynamic parameter definitions)
- High Path Matching Flexibility (WASM regex enables complex pattern matching)

**Evidence from Original Code:**
1. `compile_path()` raises `ValueError` for duplicated parameter names immediately
2. The `param_convertors` dictionary maintains type constraints throughout the route's lifecycle
3. `url_path_for()` enforces exact parameter match requirements through `seen_params == expected_params`

**Over-engineering Revelation**: The current implementation's regex compilation could be simplified. The parameter validation logic in `compile_path()` could be extracted into a separate validation phase that builds a simpler matcher. The current coupling between path parsing, parameter validation, and regex creation represents unnecessary complexity that alternatives can avoid while maintaining correctness.
