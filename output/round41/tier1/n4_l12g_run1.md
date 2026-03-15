# L12 Structural Analysis: Starlette routing.py

## PHASE 1 — STRUCTURAL ANALYSIS

### Three Properties This Code Claims

1. **Composable routing** — Routes can be nested via `Mount` to arbitrary depth, with `url_path_for` delegating through the hierarchy
2. **Complete matching** — Every request receives a definitive resolution: `Match.FULL`, `Match.PARTIAL`, or falls through to `default`
3. **Strict parameter exactness** — `Route.url_path_for` enforces `seen_params == expected_params` (set equality)

### The Impossibility Proof

These three cannot coexist:

- **Composable routing** requires `Mount` to accumulate `path_params` across levels (line 147-149: `path_params.update(matched_params)`)
- **Strict parameter exactness** requires each `Route` to receive only its declared params (line 108: `seen_params != expected_params` raises `NoMatchFound`)
- **Complete matching** requires the resolution to succeed regardless of route depth

**Contradiction**: In a nested `Mount` → `Route` structure, the inner `Route` inherits accumulated `path_params` from outer `Mount`. But `url_path_for` demands exact param sets at each level. The `Mount` must strip its own params before delegating (line 165-170), but this creates an undocumented contract: callers must know the mount depth and provide params at the correct granularity.

### Conservation Law

```
Route_Count × Match_Ambiguity = constant
```

As routes increase, the probability that `redirect_slashes` or partial-matching logic routes to the *wrong* handler increases proportionally. The Router.conceals this by processing routes sequentially—order determines outcome, but order is external to any individual route.

### Concealment Mechanism

**Sequential matching with first-match-wins** (lines 207-216):

```python
partial = None
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match is Match.FULL:
        # ...return immediately
    elif match is Match.PARTIAL and partial is None:
        partial = route  # FIRST partial wins
```

The loop structure hides that:
- Route *position* is semantically significant but not encoded in route definitions
- Adding a route can silently change which handler receives requests that previously matched differently
- `redirect_slashes` creates ghost routes (lines 221-232) that can intercept before `default`

### Improvement That Recreates The Problem

Add priority scoring to routes:

```python
# "Fix": explicit precedence instead of implicit ordering
def score_match(match, route):
    if match is Match.FULL:
        return 100 - len(route.path)  # Specificity wins
    elif match is Match.PARTIAL:
        return 50 - len(route.path)
    return -1

best = max((score_match(r.matches(scope), r), r, cs) for r in self.routes)
```

**Recreation**: Now specificity competes with explicit ordering. A more specific route added *later* silently overrides a less specific route added *earlier*. The conservation law holds: `Explicit_Control × Implicit_Behavior = constant`. We've moved the ambiguity from "position in list" to "specificity scoring rules."

---

## PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | Verification |
|-------|---------------|------------|--------------|
| `Mount` accumulates `path_params` via `.update()` | STRUCTURAL | 1.0 | Lines 147-149 |
| `Route.url_path_for` requires exact param set equality | STRUCTURAL | 1.0 | Line 108 |
| Router uses first-match-wins for partials | STRUCTURAL | 1.0 | Lines 211-214 |
| `redirect_slashes` can intercept before `default` | STRUCTURAL | 1.0 | Lines 221-232 |
| Route position is semantically significant | STRUCTURAL | 1.0 | Derived from sequential loop |
| `request_response` has nested function bug | STRUCTURAL | 1.0 | Lines 28-34 (inner `app` shadows outer) |
| "Adding routes can silently change behavior" | CONTEXTUAL | 0.85 | Requires external knowledge of how routes are typically added |
| "Priority scoring recreates the problem" | STRUCTURAL | 1.0 | By construction in the improvement |
| Conservation law form `Route_Count × Match_Ambiguity` | STRUCTURAL | 0.9 | Derivable from sequential matching semantics |

### Low-Confidence Claim Analysis

**Claim**: "Adding a route can silently change which handler receives requests"

- **Confidence**: 0.85
- **Source needed**: External knowledge of deployment patterns, whether routes are dynamically added
- **If wrong**: Conservation law becomes `Route_Depth × Param_Complexity = constant` instead

---

## PHASE 3 — SELF-CORRECTION

### Verified Findings Only

**Defect Table (SAFE only):**

| Location | Severity | Type | Description |
|----------|----------|------|-------------|
| Lines 28-34 | CRITICAL | fixable | `request_response` decorator defines `async def app` inside `async def app`. Inner function shadows outer; outer never calls inner. The `wrap_app_handling_exceptions` wrapper receives `scope, receive, send` but the outer `app` signature expects `request`. |
| Line 211 | MODERATE | structural | First partial match wins—subsequent partials ignored even if more specific |
| Lines 221-232 | MODERATE | structural | `redirect_slashes` creates implicit routes not in `self.routes`, making route enumeration incomplete |
| Line 108 | LOW | structural | Exact param equality prevents param-forwarding patterns without Mount awareness |

**Conservation Law (verified):**

```
Route_Count × Match_Predictability = constant
```

Proof: Sequential matching means each route's match probability is conditional on all preceding routes failing to match. Adding route N+1 can only *reduce* the match probability of routes 1..N. The total "match space" is partitioned by route order, and this partitioning is zero-sum.

**Concealment Mechanism (verified):**

The `for route in self.routes` loop (line 208) treats routes as a sequence but routes are defined as a collection. The semantic weight of *position* is concealed from the route definitions themselves.

---

## Final Output

**Conservation Law**: `Route_Count × Match_Predictability = constant`

**Defect Table**:

| # | Location | Severity | Type | Finding |
|---|----------|----------|------|---------|
| 1 | Lines 28-34 | **CRITICAL** | fixable | `request_response` contains nested `async def app` — inner shadows outer, decorator broken |
| 2 | Line 211 | MODERATE | structural | Partial match first-come-first-served loses potentially better matches |
| 3 | Lines 221-232 | MODERATE | structural | `redirect_slashes` ghost routes bypass route enumeration |
| 4 | Line 147-149 + 108 | LOW | structural | Param accumulation vs exact equality creates undocumented depth-awareness contract |
