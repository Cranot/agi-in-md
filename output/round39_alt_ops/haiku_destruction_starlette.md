# Analysis of Starlette Routing System Sabotage Potential

## Step 1: Engineer Three Sabotages

### Sabotage 1: Route Matching Method Override
**Location**: `starlette/routing.py`, `Route.__init__` method, lines 82-84
**Change**: Replace:
```python
if methods is None:
    self.methods = set()
else:
    self.methods = {method.upper() for method in methods}
```
With:
```python
if methods is None:
    self.methods = {"GET"}  # Always default to GET instead of empty set
else:
    self.methods = {method.upper() for method in methods}
```

**Wrong behavior**: All routes without explicit methods will now respond to GET requests, even when they should only accept other methods like POST or be method-agnostic. This violates the intended behavior where unspecified methods should not match any request.

### Sabotage 2: Mount Path Truncation Vulnerability
**Location**: `starlette/routing.py`, `Mount.__init__` method, lines 145-146
**Change**: Replace:
```python
self.path = path.rstrip("/")
```
With:
```python
self.path = path.rstrip("/") if path != "/" else "/"  # Special case handling that creates inconsistency
```

**Wrong behavior**: When a Mount is created with path="/", it will no longer be treated as a special case, breaking the assumption that root mounts handle all paths correctly. This causes subtle routing failures where mount-based routes with root paths fail to match correctly.

### Sabotage 3: Path Parameter Propagation Bug
**Location**: `starlette/routing.py`, `Mount.matches` method, lines 172-177
**Change**: Replace:
```python
matched_path = route_path[: -len(remaining_path)]
path_params = dict(scope.get("path_params", {}))
path_params.update(matched_params)
```
With:
```python
matched_path = route_path[: -len(remaining_path)]
path_params = dict(scope.get("path_params", {}))
path_params.update(matched_params)
if "path" not in path_params:  # This creates inconsistent parameter handling
    path_params["path"] = ""
```

**Wrong behavior**: Path parameters from parent scopes are now incorrectly modified, adding empty "path" parameters when they shouldn't exist. This breaks URL generation for nested routes and causes subtle parameter mismatches in complex routing hierarchies.

## Step 2: Name What You Had to Understand

### Sabotage 1: Route Matching Method Override
**Structural property**: The system relies on the invariant that `self.methods` being `set()` indicates method-agnostic routing, while non-empty sets indicate method-specific routing.
**Implicit invariant**: A route with empty methods should not match HTTP requests by default, but the code assumes it might accept some method.
**Trust assumption**: That method specification is binary (either method-agnostic or explicitly specified) and no middle ground exists.

### Sabotage 2: Mount Path Truncation Vulnerability
**Structural property**: The system treats mount paths as hierarchical segments where the root path ("/") is a special case that handles all sub-paths.
**Implicit invariant**: That all paths are normalized by removing trailing slashes except for the root path which must remain "/".
**Trust assumption**: That path normalization is consistent across all route types and doesn't create special cases that break the routing hierarchy.

### Sabotage 3: Path Parameter Propagation Bug
**Structural property**: The system maintains a clear separation between mount-specific parameters and nested route parameters.
**Implicit invariant**: That `path_params` from parent scopes are immutable and should only be extended, not modified with new keys.
**Trust assumption**: That parameter dictionaries are cleanly passed through the routing hierarchy without contamination from intermediate routing levels.

## Step 3: Derive the Conservation Law

All three sabotages exploit the same fundamental structural property: **parameter propagation consistency**.

**Conserved quantity**: The system protects against inconsistent parameter propagation through the routing hierarchy.

**The law**: `Parameter Purity × Route Fidelity = constant`

**Explanation**: The routing system maintains a balance between parameter purity (ensuring path parameters don't get corrupted or polluted as they pass through route hierarchies) and route fidelity (ensuring routes match exactly as specified). Each sabotage violates this balance by introducing inconsistent parameter handling:

1. Sabotage 1 violates route fidelity by making method-agnostic routes suddenly responsive to GET requests
2. Sabotage 2 violates parameter purity by creating special cases in path normalization
3. Sabotage 3 directly corrupts parameter propagation by modifying parent-scope parameters

This reveals that while the system claims to protect against routing errors, it actually primarily protects against **parameter corruption** - the assumption that path parameters flow cleanly through the hierarchy without being modified or polluted at each level. The routing system's true security model is built on maintaining parameter purity, not just route matching correctness.
