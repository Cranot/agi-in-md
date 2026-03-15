I'll execute a comprehensive security analysis of the Starlette routing system across five maintenance cycles, mapping calcification patterns and temporal security fragilities.

## Cycle 1: Path Traversal CVE Under Time Pressure

**The Fix:**
A path traversal vulnerability is discovered when Mount paths contain `../` sequences. The patch quickly modifies `get_route_path()` to normalize paths by resolving `.` and `..`:

```python
def get_route_path(scope):
    path = scope.get("path", "")
    # Added normalization
    normalized = []
    for part in path.split("/"):
        if part == "" or part == ".":
            continue
        if part == "..":
            if normalized:
                normalized.pop()
        else:
            normalized.append(part)
    return "/" + "/".join(normalized)
```

**Assumptions that Calcify:**
1. Path normalization is now considered the definitive solution to traversal attacks
2. `get_route_path()` becomes a trusted, sanitizing function developers rely on
3. The assumption that "normalized paths are safe" permeates the codebase

**Adjacent Code Paths That Become Unauditable:**
1. `Mount.matches()` uses normalized paths for matching but doesn't validate the residual path
2. `compile_path()` regex patterns now operate on pre-sanitized input, making it impossible to detect path injection in regex patterns
3. `Router.url_path_for()` constructs URLs from normalized components without checking for original traversal attempts

**Audit Blind Spots Created:**
- Developers stop inspecting Mount paths for traversal patterns
- Regex compilation no longer considers path context
- URL construction in `replace_params()` bypasses normalization checks

## Cycle 2: ReDoS Mitigation in Regex Engine

**The Fix:**
A ReDoS vulnerability is found in `compile_path()` when complex regex patterns are generated. The fix adds a complexity limit and forbids certain patterns:

```python
def compile_path(path):
    # Added complexity check
    max_complexity = 50  # arbitrary threshold
    complexity = 0
    for match in PARAM_REGEX.finditer(path):
        complexity += len(match.group())
        if complexity > max_complexity:
            raise ValueError(f"Path complexity exceeds maximum allowed: {path}")
    
    # Forbidden patterns
    forbidden_patterns = r"\(\?.*?<=.*?\)|\(\?.*?!.*?\)|\(\?[<>=]"
    if re.search(forbidden_patterns, path):
        raise ValueError(f"Path contains forbidden patterns: {path}")
```

**Forbidden Knowledge That Junior Developers Rediscover:**
1. Lookaround assertions in regex patterns cause ReDoS
2. Complex nested patterns exceed complexity thresholds
3. Certain regex features are permanently banned

**Bypass Techniques That Calcify:**
Internal documentation notes these workarounds:
- Use `[^/]+` instead of positive lookaheads
- Split complex paths into multiple simple routes
- Use `|` (OR) instead of complex lookbehind patterns
- Max 10 regex groups per path pattern

**Attack Surfaces Created:**
- Developers create complex workarounds that bypass compile-time checks
- Multiple simple routes increase the attack surface
- Alternative regex features that bypass the complexity check emerge

## Cycle 3: WebSocket Privilege Escalation Fix

**The Fix:**
WebSocket scope validation is added to prevent privilege escalation through child scope manipulation:

```python
class Mount:
    def matches(self, scope):
        # Added WebSocket scope validation
        if scope["type"] == "websocket":
            if "user" not in scope or scope.get("user") is None:
                raise WebSocketSecurityError("WebSocket connections require authenticated user")
            child_scope = child_scope.copy()
            child_scope["user"] = scope["user"]  # Ensure user context propagates
            return Match.FULL, child_scope
```

**Knowledge Lost When Author Leaves:**
1. The original purpose of `app_root_path` vs `root_path` distinction
2. Why WebSocket connections require different scope handling than HTTP
3. The rationale behind `child_scope` updates in routing logic

**Security-Critical Child Scope Manipulations:**
1. `Mount.matches()` sets `root_path` but not `app_root_path` in child scope
2. `Router.__call__()` adds `{"router": self}` to scope without considering WebSocket isolation
3. `Route.__call__()` updates scope with path_params before checking method permissions

**Invisible Security Operations:**
- Scope updates happen silently in multiple methods
- Security context propagation is implicit and not documented
- WebSocket-specific scope handling is scattered across routing classes

## Cycle 4: Middleware Stacking Ordering Manipulation

**The Fix:**
A middleware ordering vulnerability allows bypasses when middleware is not applied in reverse order. The fix codifies the reversed pattern:

```python
class Router:
    def __init__(self, routes=None, redirect_slashes=True, default=None,
                 lifespan=None, *, middleware=None):
        # Middleware application pattern is now documented as doctrine
        if middleware:
            for cls, args, kwargs in reversed(middleware):
                self.app = cls(self.app, *args, **kwargs)
```

**Doctrine That Becomes Received Wisdom:**
1. "Middleware must always be applied in reverse order"
2. "The last middleware added is the first to execute"
3. "Reversing middleware is security-critical and cannot be changed"

**New Fragilities When Reordered for Performance:**
1. Security middleware placed first for performance breaks the assumption
2. Dependency injection middleware that expects to run last fails
3. Rate limiting middleware bypassed if moved to execute before request parsing

**Ergonomics vs Security Tradeoffs:**
- The reversed pattern becomes "just how middleware works"
- Performance optimizations that reorder middleware create hidden vulnerabilities
- The original security intent is lost in the implementation detail

## Cycle 5: redirect_slashes as Open Redirect Vector

**The Fix:**
`redirect_slashes` is found to enable open redirects. The fix adds domain validation:

```python
class Router:
    async def app(self, scope, receive, send):
        # Added redirect validation
        if scope["type"] == "http" and self.redirect_slashes and scope["path"] != "/":
            redirect_scope = dict(scope)
            original_path = redirect_scope["path"]
            if original_path.endswith("/"):
                redirect_scope["path"] = redirect_scope["path"].rstrip("/")
            else:
                redirect_scope["path"] = redirect_scope["path"] + "/"
            
            # Only redirect to same domain
            if URL(scope=scope).origin() != URL(scope=redirect_scope).origin():
                await self.not_found(scope, receive, send)
                return
            
            # ... rest of redirect logic
```

**Unchecked URL Construction Assumptions:**
1. That `scope["path"]` contains only the URL path, not full URL
2. That `redirect_scope` creates a safe copy of scope
3. That redirects to the same domain are always safe
4. That URL construction via `URL(scope=scope)` is safe without validation

**Boring Audits That Never Happen:**
- No one checks redirect_scope construction for security implications
- Domain validation is added but URL fragment validation is not
- The assumption that "same domain = safe" goes untested

## Calcification Map

### Assumptions That Hardened Into Doctrine Without Verification:
1. **Path normalization is sufficient** - `get_route_path()` normalization became the only traversal defense, preventing review of other attack surfaces
2. **Regex compilation validates safety** - The belief that `compile_path()` regex patterns are safe because they're "compiled"
3. **Middleware order is security** - The reversed pattern became dogma without understanding why it was necessary
4. **Scope updates are transparent** - Developers stopped tracking security-critical scope changes

### Provably Wrong But Never Tested Assumptions:
1. **Path parameter type coercion is safe** - `convertor.convert()` never tested with crafted inputs that bypass validation
2. **Same-domain redirects are safe** - Added domain validation but didn't test for subdomain takeovers
3. **WebSocket scope isolation works** - Never tested scope mutation across WebSocket connections
4. **Complex regex patterns are caught** - Bypass techniques found in production after deployment

### Attack Surfaces the Original Threat Model Couldn't Predict:
1. **Composed Mount paths creating traversal opportunities** - Mount composition allows traversal that single routes can't detect
2. **Scope propagation vectors** - Child scope updates create security context leaks
3. **Redirect chain exploitation** - Multiple redirect layers bypass individual security checks
4. **Regex complexity bypasses** - Workarounds to compile-time checks create new vulnerabilities

## Temporal Conservation Law

**Route Definition Ergonomics × Attack Surface Opacity = Constant**

Every convenience added to path specification creates a proportional blind spot in security auditing:

1. **Parametric paths** - Added convenience enables parameter injection
2. **Mount composition** - Added convenience enables traversal through nested paths
3. **Regex patterns** - Added convenience enables ReDoS and bypass techniques
4. **Middleware stacking** - Added convenience enables ordering exploits
5. **Redirect handling** - Added convenience enables open redirects

## Temporal Security Fragilities

### 1. Path Parameter Type Coercion
**Calcified Assumption:** "Path params are sanitized by convertors"
**What Breaks:** `convertor.convert()` methods fail on crafted inputs that exploit type coercion edge cases
**Timeline Until Exploitation:** 6-12 months (developer turnover, major version updates)
**Type:** Structural (emerges from route matching model)

### 2. Scope Mutation Patterns
**Calcified Assumption:** "Child scope updates preserve security context"
**What Breaks:** Security-critical context (`user`, `auth`) is lost when scope is updated
**Timeline Until Exploitation:** 3-6 months (when security context is expected but missing)
**Type:** Preventable (could be caught by temporal audit)

### 3. Regex Compilation Safety
**Calcified Assumption:** "compile_path validates regex patterns"
**What Breaks:** Bypass techniques complex patterns from forbidden features
**Timeline Until Exploitation:** 9-18 months (bypasses discovered in production)
**Type:** Structural (emerges from regex compilation model)

### 4. Middleware Order Doctrine
**Calcified Assumption:** "Reversed middleware order is required"
**What Breaks:** Performance optimizations break security assumptions
**Timeline Until Exploitation:** 1-3 months (when middleware is reordered)
**Type:** Preventable (documented but ignored)

### 5. Redirect Domain Validation
**Calcified Assumption:** "Same-domain redirects are safe"
**What Breaks:** Subdomain takeover attacks bypass domain validation
**Timeline Until Exploitation:** 12-24 months (vulnerability discovered in infrastructure)
**Type:** Structural (emerges from redirect handling model)

### 6. Path Normalization Doctrine
**Calcified Assumption:** "Normalized paths are safe"
**What Breaks:** Mount composition creates traversal that normalization can't prevent
**Timeline Until Exploitation:** 6-12 months (when complex Mounts are used)
**Type:** Structural (emerges from routing composition)

### 7. WebSocket Scope Isolation
**Calcified Assumption:** "WebSocket scope is isolated"
**What Breaks:** Child scope manipulation propagates security context incorrectly
**Timeline Until Exploitation:** 3-9 months (when WebSocket security is implemented)
**Type:** Preventable (could be caught by audit)

### 8. URL Construction Assumptions
**Calcified Assumption:** "URL construction from scope is safe"
**What Breaks:** Redirect chains and URL fragments create new attack vectors
**Timeline Until Exploitation:** 9-15 months (complex URL features used)
**Type:** Preventable (could be caught by audit)

## Knowledge Loss Patterns Across Maintenance Cycles

The most critical security knowledge loss occurs in these areas:

1. **Original Intent Doctrine** - Security fixes become implementation details without understanding why
2. **Scope Propagation Models** - Developers lose track of what scope contains and how it changes
3. **Attack Surface Composition** - Individual fixes create new vulnerabilities when composed
4. **Ergonomics-Security Tradeoffs** - Convenience features override security considerations
5. **Temporal Audit Practices** - Security reviews focus on current state, not historical context

The routing system demonstrates that each security fix creates a new vulnerability when it becomes calcified doctrine, as the system evolves faster than security understanding can propagate.
