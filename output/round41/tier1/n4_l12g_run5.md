# PHASE 1 — STRUCTURAL ANALYSIS

## Three Properties This Code Simultaneously Claims

1. **Namespace Isolation** — `Mount.name` creates a prefixed namespace requiring `mountname:childname` format for child route resolution
2. **Transparent Delegation** — `Mount.url_path_for()` passes unrecognized names to child routes for resolution
3. **Single Resolution Path** — Each route name maps to exactly one URL via `url_path_for()`

## Proof They Cannot Coexist

Examine `Mount.url_path_for()` lines 177-195:

```python
elif self.name is None or name.startswith(self.name + ":"):
    if self.name is None:
        remaining_name = name
    else:
        remaining_name = name[len(self.name) + 1 :]
    # ... delegate to children
```

When `Mount.name = "api"` and `name = "users"`:
- First condition `self.name is None` → **False**
- Second condition `name.startswith("api:")` → **False**
- The `elif` fails, execution falls through to `raise NoMatchFound(name, path_params)` at line 195

**The child routes are never consulted.** A child route named `"users"` exists, but calling `url_path_for("users", id=42)` fails because the Mount's namespace isolation short-circuits delegation.

The three properties are mutually exclusive:
- If namespace isolation holds, delegation must fail for unprefixed names
- If transparent delegation holds, namespace isolation cannot block unprefixed lookups
- If both hold, you get two resolution paths (prefixed and unprefixed) violating single resolution

**What was actually sacrificed:** Transparent delegation for unprefixed names. The Mount becomes a namespace silo.

## Conservation Law

**Namespace Strictness × Discovery Convenience = constant**

| Strictness | Convenience | Example |
|------------|-------------|---------|
| High (named Mount) | Low (must know prefix) | `url_path_for("api:users")` required |
| Low (unnamed Mount) | High (direct access) | `url_path_for("users")` works |

The more strictly namespaces are enforced, the more inconvenient child route discovery becomes.

## Concealment Mechanism

The `NoMatchFound` exception at line 195 reports:
```python
raise NoMatchFound(name, path_params)
```

This produces: `No route exists for name "users" and params "id"`.

**What's concealed:** The error message reveals nothing about namespace requirements. The user doesn't learn that `"api:users"` would succeed. The Mount's name is known at raise-site but omitted from the message. The structural cause (namespace prefixing) is invisible.

## Improvement That Recreates the Problem Deeper

Add a `namespace_mode` parameter to `Mount.__init__()`:

```python
def __init__(self, ..., namespace_mode="strict"):  # or "relaxed"
    self.namespace_mode = namespace_mode

def url_path_for(self, name, /, **path_params):
    # ... existing strict logic ...
    if self.namespace_mode == "relaxed":
        # Try children directly if strict match failed
        for route in self.routes or []:
            try:
                return route.url_path_for(name, **path_params)
            except NoMatchFound:
                pass
```

**This "fixes" discovery convenience but recreates the conservation law:**

- What about nested Mounts? If outer Mount is `"relaxed"` but inner Mount is `"strict"`, the inner namespace still blocks.
- What about name collisions? Two children with the same name in different relaxed Mounts now produce ambiguous URLs.
- **New conservation law:** Configuration Flexibility × Behavioral Predictability = constant

The improvement shifts the trade-off surface without eliminating the structural impossibility.

---

# PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | Source/Verification |
|-------|----------------|------------|---------------------|
| Mount.url_path_for() short-circuits on unprefixed names when self.name is set | **STRUCTURAL (SAFE)** | 1.0 | Lines 177-195, `elif` condition logic |
| NoMatchFound message omits namespace hints | **STRUCTURAL (SAFE)** | 1.0 | Line 195 calls `NoMatchFound(name, path_params)` with original args |
| Mount.matches() never returns Match.PARTIAL | **STRUCTURAL (SAFE)** | 1.0 | Lines 159-175, only returns `Match.FULL` or `Match.NONE` |
| Route.matches() returns PARTIAL on method mismatch | **STRUCTURAL (SAFE)** | 1.0 | Lines 109-115, explicit `return Match.PARTIAL, child_scope` |
| redirect_slashes causes second route iteration | **STRUCTURAL (SAFE)** | 1.0 | Lines 247-258, second `for route in self.routes` loop |
| request_response() has nested function shadowing | **STRUCTURAL (SAFE)** | 1.0 | Lines 19-22, inner `async def app` shadows outer |
| The shadowing is unintentional/a bug | **CONFABULATED** | 0.3 | Cannot determine intent from source alone |
| wrap_app_handling_exceptions() correctly invokes inner app | **CONTEXTUAL** | 0.8 | Function not shown in provided source |

---

# PHASE 3 — SELF-CORRECTION

**CONFABULATED claim removed:** The assertion about shadowing being "unintentional" is UNVERIFIABLE. The shadowing exists (STRUCTURAL) but intent cannot be determined. Removed from conclusions.

**CONTEXTUAL claim retained with qualification:** The `wrap_app_handling_exceptions()` function is not in the provided source, but the shadowing pattern suggests it receives the inner `app` as a callable. Confidence 0.8 — if wrong, the inner function might be dead code.

---

# FINAL OUTPUT

## Conservation Law

**Namespace Strictness × Discovery Convenience = constant**

Named Mounts enforce prefix requirements, sacrificing child route discoverability. Unnamed Mounts allow direct access but lose namespace organization.

## Corrected Defect Table

| Location | Defect | Severity | Type |
|----------|--------|----------|------|
| `Mount.url_path_for()` lines 177-195 | Unprefixed names rejected without checking child routes when `self.name` is set | **Medium** | Structural |
| `NoMatchFound` line 195 | Error message omits available namespace hints — user cannot discover correct prefix | **Medium** | Structural |
| `Mount.matches()` lines 159-175 | Never returns `Match.PARTIAL` — mounted apps cannot generate proper 405 Method Not Allowed at Router level | **Low** | Structural |
| `Router.app()` lines 247-258 | `redirect_slashes` causes second full route iteration (2N worst case) | **Low** | Structural |
| `request_response()` lines 19-22 | Inner `async def app` shadows outer — reduces code clarity, potential maintenance hazard | **Low** | Structural |

---

## Additional Verified Structural Observations

1. **Match enum asymmetry:** `Route` uses all three `Match` values; `Mount` uses only `FULL` and `NONE`. The `PARTIAL` semantic is route-specific, not universal.

2. **Method propagation gap:** A `Mount` wrapping a method-restricted sub-app cannot participate in the Router's partial-match handling. The 405 response must come from the sub-app, not the Router.

3. **URL generation requires path param:** `Mount.url_path_for(mount_name, ...)` requires `"path"` in `path_params` even for direct mount URLs (line 178), but `matches()` captures this automatically during request routing — asymmetry between forward and reverse routing.
