# Knowledge Boundary Analysis: Starlette Routing

## Step 1: Claim Classification

### STRUCTURAL Claims (Derivable from Source)

| Claim | Source Location | Verification |
|-------|-----------------|--------------|
| `Router.app()` iterates routes sequentially | Lines 225-234 shown | Direct code inspection |
| `route.matches()` executes per iteration | Lines 225-234 shown | Direct code inspection |
| `Mount.url_path_for()` iterates child routes | Lines 177-194 shown | Direct code inspection |
| `replace_params()` uses `pop()` on line 62 | Line 62 referenced | Code inspection |
| Method check occurs at line 116 | Line 116 referenced | Code inspection |
| `scope['path_params']` is mutated per request | Lines 106-114 shown | Direct code inspection |
| Middleware stack built in `reversed()` order | Lines 76-80, 143-145 | Direct code inspection |
| `{path:path}` capture used in `Mount.matches()` | Line 129 referenced | Code inspection |
| `redirect_slashes` logic at lines 248-258 | Lines 248-258 referenced | Code inspection |

### CONTEXTUAL Claims (Depend on External State)

| Claim | External Dependency |
|-------|---------------------|
| Trie provides O(path_length) lookup | Algorithm theory / data structures literature |
| LRU cache provides O(1) lookup | Cache algorithm literature |
| Regex matching has non-constant cost | Regex engine implementation details |
| Python `dict.pop()` mutates in place | Python language specification |

### TEMPORAL Claims (May Expire)

| Claim | Staleness Risk |
|-------|----------------|
| Line numbers (225-246, 177-194, etc.) | **HIGH** - Changes with every version |
| No middleware callable validation | **MEDIUM** - May be added in future version |
| These specific function signatures | **MEDIUM** - API stability |

### ASSUMED Claims (Untested/Interpretive)

| Claim | Nature of Assumption |
|-------|---------------------|
| "FLEXIBILITY × PERFORMANCE = COMPILE-TIME BUDGET" | Theoretical framework, not empirically validated |
| "The optimization defeats itself" | Interpretive conclusion |
| "Stateful routing breaks cache invalidation" | Theoretical claim about cache semantics |
| "DECLARATIVE COMPLETENESS × RUNTIME MUTABILITY = FRAMEWORK BOUNDARY" | Theoretical framework |
| "Dynamic nested routing requires exhaustive descendant search" | Claim about necessity, not verified |
| Severity ratings (HIGH/MEDIUM/LOW) | Subjective impact assessment |
| "you cannot optimize what you must search exhaustively" | Generalized theoretical claim |
| "ASGI scopes are fundamentally mutable" | Requires verification against ASGI spec |

---

## Step 2: Non-STRUCTURAL Claim Deep Dive

### TEMPORAL: Line Number References

| Claim | External Source | Staleness | Confidence |
|-------|-----------------|-----------|------------|
| `Router.app()` at lines 225-246 | [Starlette GitHub](https://github.com/encode/starlette) | Daily (per commit) | **UNKNOWN** - No version specified |
| `Mount.url_path_for()` at lines 177-194 | Starlette source | Daily | **UNKNOWN** |
| `Route.matches()` at lines 106-114 | Starlette source | Daily | **UNKNOWN** |
| `compile_path()` at lines 24-51 | Starlette source | Daily | **UNKNOWN** |

**Critical Gap:** Analysis does not specify Starlette version. Line numbers are unverifiable without version pinning.

### CONTEXTUAL: Algorithm Performance Claims

| Claim | External Source | Staleness | Confidence |
|-------|-----------------|-----------|------------|
| Trie = O(path_length) | CLRS or Knuth | Never | **HIGH** |
| LRU = O(1) amortized | Algorithm literature | Never | **HIGH** |
| Regex matching cost varies | [Python `re` module docs](https://docs.python.org/3/library/re.html) | Yearly | **HIGH** |

### ASSUMED: Theoretical Frameworks

| Claim | External Source | Staleness | Confidence |
|-------|-----------------|-----------|------------|
| Conservation law is valid | Would require formal proof or empirical validation | Never | **UNKNOWN** |
| Cache isolation impossible | [Python threading docs](https://docs.python.org/3/library/threading.html), ASGI spec | Yearly | **MEDIUM** |
| ASGI scopes "fundamentally mutable" | [ASGI Specification](https://asgi.readthedocs.io/) | Yearly | **MEDIUM** |
| Severity ratings accurate | Would require production incident data | Daily | **UNKNOWN** |

### ASSUMED: "Exhaustive Search Required"

| Claim | External Source | Staleness | Confidence |
|-------|-----------------|-----------|------------|
| Dynamic nested routing *requires* exhaustive search | Would require proof or counter-example in routing literature | Never | **LOW** - Alternative algorithms (e.g., radix tree with backtracking) may exist |

---

## Step 3: Gap Map

### API_DOCS
| Gap | Source |
|-----|--------|
| Python `dict.pop()` mutation semantics | https://docs.python.org/3/library/stdtypes.html#dict.pop |
| Python `re` module regex behavior | https://docs.python.org/3/library/re.html |
| Starlette version being analyzed | https://github.com/encode/starlette/releases |

### CVE_DB
| Gap | Source |
|-----|--------|
| None identified | N/A |

### COMMUNITY
| Gap | Source |
|-----|--------|
| Whether Starlette maintainers consider O(n) routing a known limitation | https://github.com/encode/starlette/issues |
| Whether alternative routing implementations exist | Starlette discussions, Discord |

### BENCHMARK
| Gap | Source |
|-----|--------|
| Actual performance impact of O(n) routing at scale | Would require custom benchmark |
| Whether cache would actually help despite scope mutation | Would require prototype + benchmark |
| Break-even point where trie outperforms linear search | Would require benchmark with varying route counts |

### MARKET
| Gap | Source |
|-----|--------|
| Production incident data supporting severity ratings | Not publicly available |
| Real-world route counts in Starlette applications | Survey or telemetry data |

### CHANGELOG
| Gap | Source |
|-----|--------|
| Whether line numbers match current Starlette version | https://github.com/encode/starlette/blob/master/CHANGELOG.md |
| Whether identified "fixable" defects already fixed | Git history |

---

## Step 4: Priority Ranking

### Tier 1: Analysis-Foundational Gaps (If wrong, conclusions collapse)

| Rank | Gap | Impact if Wrong |
|------|-----|-----------------|
| **1** | **Starlette version unspecified** | All line number references are unverifiable. Code may have moved, functions may not exist, defects may be fixed. |
| **2** | **"Exhaustive search required" claim** | If false (e.g., if backtracking radix trees could work), the entire conservation law and all structural defect classifications are invalid. |
| **3** | **Cache isolation claim** | If scope mutation doesn't actually prevent caching (e.g., if copy-on-write works), the "second recursion" failure analysis is wrong. |

### Tier 2: Evidence Gaps (If wrong, severity misestimated)

| Rank | Gap | Impact if Wrong |
|------|-----|-----------------|
| **4** | **No benchmark data** | O(n) may be negligible for typical route counts (< 100). HIGH severity claim lacks empirical support. |
| **5** | **ASGI mutability claim** | If ASGI spec actually recommends immutability, the "framework boundary" analysis is misplaced. |
| **6** | **Severity ratings** | Subjective HIGH/MEDIUM/LOW without production impact data. |

### Tier 3: Verification Gaps (If wrong, specific fixes affected)

| Rank | Gap | Impact if Wrong |
|------|-----|-----------------|
| **7** | **Line number accuracy** | Specific fix locations wrong, but defect may still exist. |
| **8** | **`replace_params()` mutation behavior** | If already fixed in current version, fix recommendation is obsolete. |
| **9** | **Middleware callable validation** | May already exist in newer versions. |

---

## Summary

| Category | Count | Critical Finding |
|----------|-------|------------------|
| STRUCTURAL | 9 | Solid code-derivable claims |
| CONTEXTUAL | 4 | Algorithm theory (high confidence) |
| TEMPORAL | 3 | Line numbers (unverifiable without version) |
| ASSUMED | 8 | Theoretical frameworks lack validation |

**Highest-Impact Knowledge Gap:** The unspecified Starlette version makes all line-number-based claims unverifiable. This is a **TEMPORAL** gap with **daily staleness risk** that could be closed by adding a single line: "Analysis based on Starlette v0.XX.Y."

**Second-Highest Gap:** The claim that "exhaustive search is required" for dynamic nested routing is an **ASSUMED** claim that, if false, invalidates the conservation law framework. This requires either formal proof or citation to routing algorithm literature.
