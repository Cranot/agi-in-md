# Knowledge Audit: Starlette Routing Analysis

## Classification of Claims

### SAFE — Verifiable from Source Structure
- The existence of `compile_path`, `Mount`, `Router` classes and their structural relationships
- Linear scan pattern in `for route in self.routes:` (structural observation of iteration)
- Conservation law as analytical framework (conceptual, not factual)
- Cache invalidation as a problem category (logical consequence of mutable state)
- "Developer ergonomics > runtime efficiency" as design philosophy inference

### KNOWLEDGE CLAIMS — Requiring External Verification

---

### **Claim 1: Line Number References**
> "compile_path function (lines 51-76)", "Mount class (lines 120-195)", "Router.app (lines 192-220)"

**Dependency:** The specific Starlette version analyzed matches the line numbers cited.

**Failure Mode:** Version drift. Starlette 0.27, 0.31, 0.36 all have different line counts. A refactoring that extracts a function shifts all subsequent line numbers.

**Confabulation Risk: HIGH.** Models frequently generate plausible-but-wrong line numbers. The specificity (51-76 vs 50-77) suggests either direct access or confident confabulation.

**With Documentation Access:** Would confirm or refute immediately. Either the lines exist as stated, or they don't.

---

### **Claim 2: Path Composition Behavior**
> "Mount("/api/{version}", routes=[Route("/users", users_endpoint)])  # becomes /api/v1/users"

**Dependency:** The `{version}` parameter substitutes `v1` when the route is matched with that path parameter value.

**Failure Mode:** This may be correct, but the comment conflates route *definition* with route *matching*. The mount defines the pattern; `v1` would only appear if a request came with `version="v1"`. The example is under-specified.

**Confabulation Risk: MEDIUM.** The behavior is plausible but the example is incomplete—it shows the pattern, not the matching request that produces `/api/v1/users`.

---

### **Claim 3: Quadratic Redirect Behavior**
> "Quadratic Redirect Behavior... when `redirect_slashes=True` (default), a request requiring redirect triggers two full linear scans. This is O(n) + O(n)... quadratic"

**Dependency:** Two definitions of "quadratic":
1. Mathematical: O(n²) — FALSE here. O(n) + O(n) = O(2n) = O(n), still linear.
2. Colloquial: "Twice as bad" — TRUE here.

**Failure Mode:** The claim is mathematically wrong. Two linear scans are still linear. "Quadratic" means the cost grows with the *product* of two variables, not the sum.

**Confabulation Risk: HIGH.** This is a category error—confusing "double scan" with "quadratic complexity." With benchmark data, this would be corrected to "linear with constant factor 2x."

**Additionally:** `redirect_slashes=True` being default requires verification against the actual Router `__init__` signature.

---

### **Claim 4: Absence of Freeze/Lock API**
> "No freeze/lock API exists after route registration"

**Dependency:** Complete knowledge of Starlette's entire public API.

**Failure Mode:** Starlette could have added `Router.freeze()` in any version. Or it could exist under a different name. Or in a subclass.

**Confabulation Risk: MEDIUM.** Absence claims are hard to verify without exhaustive search. With GitHub issues access: could search for "freeze route" or "lock router" to see if this was requested/added.

---

### **Claim 5: First Match Wins in url_path_for**
> "When nested mounts use `name=None`, identical route names in different branches collide. The first match wins"

**Dependency:** The actual search order in `Mount.url_path_for` iterates children sequentially and returns on first success.

**Failure Mode:** If the implementation searches breadth-first vs depth-first, or uses a different ordering, the "first match wins" behavior differs. Also, if there's deduplication logic, this claim is wrong.

**Confabulation Risk: MEDIUM.** Plausible given the code structure shown, but runtime behavior should be verified.

---

### **Claim 6: Root Path Duplication**
> "The scope mutation logic for `root_path` appears in both `Mount.matches` and `Route.matches`. Duplicated code"

**Dependency:** `Route.matches` contains similar `root_path` construction logic.

**Failure Mode:** If `Route.matches` uses a different mechanism (delegating to a helper, or using a different scope key), there's no duplication.

**Confabulation Risk: MEDIUM.** The claim is precise enough to be falsifiable with source access.

---

### **Claim 7: re.compile Error Behavior**
> "malformed paths can still cause `re.compile()` to raise `re.error` at runtime"

**Dependency:** Python's `re` module behavior—the `re.error` exception type exists and is raised on invalid patterns.

**Confabulation Risk: LOW.** This is Python standard library behavior, stable across versions. Official documentation confirms `re.error` is raised for malformed patterns.

---

## Improvement Construction

### With Official Documentation:
- **Confirm:** The `redirect_slashes` default value (check Router `__init__` signature)
- **Confirm:** The `re.error` exception type exists
- **Refute/Verify:** Line numbers across versions

### With CVE Database:
- Not directly applicable—this analysis describes design trade-offs, not vulnerabilities. However, if the linear scan is claimed to cause DoS, a CVE search for "Starlette routing DoS" would verify.

### With GitHub Issues:
- **Search:** "route cache", "freeze routes", "routing performance" — would reveal if the cache idea was discussed/rejected
- **Search:** "url_path_for namespace" — would reveal if collision bugs were reported
- **Search:** "quadratic routing" — would reveal if the complexity claim has been raised before

### With Benchmark Data:
- **Refute:** The "quadratic" claim definitively—benchmarks would show linear scaling with route count, not quadratic
- **Quantify:** The actual cost of the double scan (2x? 1.5x? negligible?)

### Claims That Remain Unfalsifiable:
- The conservation law itself (it's a conceptual framework, not a fact)
- "Developer ergonomics > runtime efficiency" as a design philosophy (requires mind-reading the authors)
- Whether the trade-offs are "deliberate" vs. incidental

---

## Conservation Law: Structural vs. Knowledge Claims

```
SPECIFICITY OF CLAIM × VERIFIABILITY FROM SOURCE = CONSTANT
```

The analysis exhibits an inverse relationship:

| Claim Type | Source-Derived | Externally-Dependent |
|------------|----------------|----------------------|
| **Structural** (iteration pattern, class relationships, mutation permits caching problems) | HIGH confidence | — |
| **Behavioral** (first-match-wins, default values, line numbers) | — | MEDIUM confidence |
| **Quantitative** (O(n) complexity) | MEDIUM (can reason from code) | — |
| **Categorical** ("quadratic" vs linear) | — | LOW confidence (error found) |

**The law:** The more specific and falsifiable a claim, the more it depends on external verification. The analysis's strongest insights (the conservation law, the design philosophy inference, the structural tensions) are *unfalsifiable* because they're interpretive. Its weakest claims (line numbers, "quadratic") are precisely the ones that require external verification—and precisely the ones most likely to be wrong.

This is not a flaw in the analysis but a structural property of interpretive work: **confidence trades against falsifiability**. The analysis is most confident where it cannot be proven wrong, and most vulnerable where it can be checked.
