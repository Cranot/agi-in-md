# Analysis: Starlette Routing Structure

## Explicit Choices and Rejected Alternatives

1. **Scope mutation pattern** (`scope.update(child_scope)`)
   - **Rejection**: Pure functional approach with immutable data structures
   - **Rationale**: Performance and ASGI spec compatibility

2. **Dictionary-based path parameters**
   - **Rejection**: Structured parameter objects with namespaces
   - **Rationale**: ASGI compatibility and simplicity

3. **"Last writer wins" parameter collision resolution**
   - **Rejection**: Error on collision or hierarchical parameter preservation
   - **Rationale**: Simplicity in implementation

4. **Match enum for routing decisions** (NONE, PARTIAL, FULL)
   - **Rejection**: Binary match/no-match with separate metadata for context
   - **Rationale**: Richer control flow for error handling

5. **Flat scope dictionary throughout entire routing stack**
   - **Rejection**: Nested scope structures
   - **Rationale**: Performance and ASGI compliance

## New Artifact: STARQL (SQL-Inspired Routing)

```python
class STARQLRouter:
    """
    A routing system inspired by SQL's relational model, where routes are 
    like relations and path parameters are like JOIN conditions.
    """
    
    def __init__(self):
        self.routes = []
        self.param_relations = {}  # Track parameter relationships
        
    def add_route(self, path, endpoint, methods=None):
        # Parse path like SQL table relations
        # /users/{id}/posts/{postId} becomes:
        # JOIN users.id JOIN posts.postId
        path_parts = path.split('/')
        param_join_order = []
        
        for part in path_parts:
            if part.startswith('{') and part.endswith('}'):
                param_name = part[1:-1]
                param_join_order.append(param_name)
                
        self.routes.append({
            'path': path,
            'endpoint': endpoint,
            'methods': methods or ['GET'],
            'param_join_order': param_join_order
        })
        
        # Record parameter relationships for collision resolution
        for i, param in enumerate(param_join_order):
            if param not in self.param_relations:
                self.param_relations[param] = {
                    'position': i,
                    'dependencies': param_join_order[:i]
                }
    
    def resolve_path(self, request_path, method):
        """
        Resolve path like SQL JOIN with dependency constraints
        """
        path_segments = request_path.strip('/').split('/')
        
        # Track which parameters are resolved at each position
        resolved_params = {}
        conflicts = []
        
        for route in self.routes:
            if method not in route['methods']:
                continue
                
            route_segments = route['path'].strip('/').split('/')
            
            # Check if path patterns match at each segment
            match = True
            param_values = {}
            
            for i, segment in enumerate(route_segments):
                if segment.startswith('{') and segment.endswith('}'):
                    param_name = segment[1:-1]
                    if i < len(path_segments):
                        # Parameter resolution with dependency checking
                        if self._resolve_param(param_name, path_segments[i], resolved_params):
                            param_values[param_name] = path_segments[i]
                            resolved_params[param_name] = True
                        else:
                            match = False
                            break
                    else:
                        match = False
                        break
                elif i < len(path_segments) and segment != path_segments[i]:
                    match = False
                    break
            
            if match:
                # Check for dependency violations
                for param in route['param_join_order']:
                    if param in param_values and param in self.param_relations:
                        dependencies = self.param_relations[param]['dependencies']
                        for dep in dependencies:
                            if dep not in resolved_params:
                                conflicts.append(f"Missing dependency: {dep} for {param}")
                
                if not conflicts:
                    return {
                        'match': True,
                        'endpoint': route['endpoint'],
                        'params': param_values,
                        'relations': self._build_relation_graph(route['param_join_order'], param_values)
                    }
        
        return {
            'match': False,
            'conflicts': conflicts,
            'resolved_at': len(resolved_params)
        }
    
    def _resolve_param(self, param_name, value, resolved_params):
        """Resolve parameter with dependency constraints"""
        if param_name not in self.param_relations:
            return True
            
        relations = self.param_relations[param_name]
        for dep in relations['dependencies']:
            if dep not in resolved_params:
                return False
        return True
    
    def _build_relation_graph(self, param_order, param_values):
        """Build SQL-like relation graph for dependency tracking"""
        graph = {}
        for i, param in enumerate(param_order):
            if param in param_values:
                graph[param] = {
                    'value': param_values[param],
                    'depends_on': param_order[:i],
                    'dependents': param_order[i+1:]
                }
        return graph
```

## Unconscious Resurrection of Rejected Alternatives

The STARQL design unintentionally revives these rejected alternatives from Starlette:

1. **Structured parameter relationships**: 
   - Starlette rejected this for flat dictionaries
   - STARQL resurrects it through `param_relations` and dependency tracking

2. **Rich metadata about routing decisions**:
   - Starlette simplified with Match enum
   - STARQL resurrects this with detailed relation graphs and conflict resolution

3. **Explicit dependency resolution**:
   - Starlette implicitly resolved conflicts with "last writer wins"
   - STARQL resurrects explicit dependency checking

## Transferred Patterns Creating Problems

### Silent Problems (From Starlette to STARQL)

1. **Path parameter collision handling**:
   - **Pattern transferred**: Implicit parameter resolution
   - **Result**: STARQL's dependency checking creates new edge cases where circular dependencies aren't detected
   - **Silent failure**: Routes with complex dependencies might silently ignore some parameters

2. **Routing scope accumulation**:
   - **Pattern transferred**: Progressive scope enrichment
   - **Result**: STARQL builds increasingly complex relation graphs that become expensive to maintain
   - **Silent failure**: Memory usage grows with routing complexity without obvious cause

### Visible Failures

1. **Method constraint coupling**:
   - **Pattern transferred**: Method checking during matching
   - **Result**: STARQL explicitly rejects routes based on methods before checking dependencies
   - **Visible failure**: Clear HTTP 405 responses but with confusing dependency error messages

2. **Path segment resolution**:
   - **Pattern transferred**: Segment-by-segment path matching
   - **Result**: STARQL makes route resolution visibly more complex with detailed error messages
   - **Visible failure**: Verbose error messages that overwhelm simple mismatches

## Pedagogy Law: The Interface Preservation Constraint

> **The Interface Preservation Constraint**: When internalizing patterns from a successful system, designers unconsciously transfer the constraint that the new system must maintain compatibility with the same interfaces, even when solving fundamentally different problems.

STARQL inherits this constraint from Starlette - it still uses HTTP methods and path segments as its primary interface, even though its internal model is relational. This creates cognitive dissonance between its SQL-inspired internals and HTTP-centric external interface.

## Predicted First Failure

The **circular dependency detection** will be the first silent failure and slowest to discover:

- **Why first**: Complex routes with implicit parameter dependencies will appear to work until a circular dependency is introduced
- **Why slow to discover**: Most real-world routing hierarchies are acyclic, so circular dependencies only appear during edge cases or refactoring
- **How manifests**: Routes that should match will silently fail without clear error messages, making debugging difficult

The failure occurs when STARQL's dependency tracking encounters circular references in `param_relations`, causing it to either enter an infinite loop or silently skip parameters without indicating the root cause.
