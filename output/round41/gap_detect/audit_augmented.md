# Knowledge Audit: Starlette Routing Analysis

## Conservation Law Observation

This analysis is **heavily structural** — most claims derive directly from code inspection. The knowledge claims cluster around **computational complexity assertions** and **theoretical impossibility claims**.

---

## KNOWLEDGE CLAIMS

### Claim 1: O(n) Complexity Assertion
> **Quote:** "This is O(n) complexity where n = route count"
> 
> **Dependency:** Python regex engine performance characteristics; no early-exit optimizations in iteration; `route.matches()` is not memoized or indexed.
>
> **Failure Mode:** If `Route.matches()` uses hash-based method filtering before regex, or if routes are pre-sorted by specificity with early termination, complexity could differ. Python's `re` module has unpredictable pathological-case behavior.
>
> **Confabulation Risk:** **MEDIUM.** Complexity claims are often stated confidently but hide constants and pathological cases. The "n" here conflates route count with regex pattern length.
>
> **With Perfect Knowledge:** Would be confirmed for average case, but qualified with "amortized" and "excluding regex backtracking."

---

### Claim 2: Trie Yields O(path_length) Lookup
> **Quote:** "Replace sequential iteration with prefix tree for O(path_length) lookup."
>
> **Dependency:** Trie traversal cost is proportional to key length; no hash collisions; path strings are the dominant cost.
>
> **Failure Mode:** Trie construction is O(total_pattern_length × alphabet_size). Memory overhead for sparse tries. Path parameters require backtracking — tries cannot handle `/{id}/suffix` efficiently without regex hybridization.
>
> **Confabulation Risk:** **MEDIUM.** "O(path_length)" is theoretically correct but misleading — it ignores trie construction cost and parameter extraction complexity.
>
> **With Perfect Knowledge:** Would be revised to "O(path_length) for static prefix matching, but dynamic parameters require regex fallback, defeating pure trie optimization."

---

### Claim 3: LRU Cache Gives O(1) Repeated Requests
> **Quote:** "Cache `(path, method) → (match, child_scope)` for O(1) repeated requests."
>
> **Dependency:** Hash table lookup is O(1); cache key construction is cheap; no cache thrashing.
>
> **Failure Mode:** Hash collisions degrade to O(n). Cache eviction under high cardinality paths. The analysis correctly identifies the real blocker (scope mutation), making the O(1) claim secondary.
>
> **Confabulation Risk:** **LOW.** Standard LRU behavior is well-documented.
>
> **With Perfect Knowledge:** Confirmed, but the analysis already identifies why this doesn't work — **this is a properly self-refuting claim.**

---

### Claim 4: Impossibility Theorem
> **Quote:** "You cannot have constant-time lookup AND arbitrary regex patterns AND simple sequential iteration."
>
> **Dependency:** No hybrid routing algorithm exists that combines these. Regex matching is fundamentally incompatible with trie indexing.
>
> **Failure Mode:** Radix trees with regex leaves (like httprouter in Go). DFA-based regex compilation with state machine traversal. JIT-compiled pattern matchers. The claim assumes Python's regex engine is the only implementation path.
>
> **Confabulation Risk:** **MEDIUM-HIGH.** "Cannot" claims in computer science are frequently falsified by clever algorithms. The analysis treats this as proven when it's an empirical observation about this codebase.
>
> **With Perfect Knowledge:** Would be revised to "constant-time lookup with arbitrary regex requires abandoning Python's `re` module or accepting exponential compilation cost."

---

### Claim 5: ASGI Scopes Are "Fundamentally Mutable"
> **Quote:** "ASGI scopes are fundamentally mutable"
>
> **Dependency:** ASGI specification mandates mutable dict structure; no frozen/immutable scope variant exists.
>
> **Failure Mode:** ASGI 3.5+ could introduce frozen scopes. Middleware could use copy-on-write. The word "fundamentally" is doing heavy lifting.
>
> **Confabulation Risk:** **MEDIUM.** Specification claims age poorly. Without version pinning, this claim has a half-life.
>
> **With Perfect Knowledge:** Would specify "ASGI 3.0 as of 2026-03-15" and note that immutability would require spec revision.

---

### Claim 6: Severity Ratings
> **Quote:** Defects 1, 2, 5, 6 rated as HIGH/MEDIUM with "STRUCTURAL" categorization.
>
> **Dependency:** Production usage patterns; typical route counts in Starlette applications; performance sensitivity of real workloads.
>
> **Failure Mode:** If most applications have <20 routes, O(n) is negligible and "HIGH" severity is alarmist. If route matching is dominated by database queries, routing performance is irrelevant.
>
> **Confabulation Risk:** **HIGH.** Severity claims require production data this analysis doesn't have.
>
> **With Perfect Knowledge:** Would cite benchmark data: "At 1000 routes, average lookup is Xms; at 10000 routes, Yms." Absent this, severity is speculation.

---

## Claims That Would CHANGE With Perfect Knowledge

| Claim | Current | With Benchmark Data | With Algorithm Literature |
|-------|---------|---------------------|---------------------------|
| "O(n) complexity" | Stated as fact | "O(n) with 0.3ms per 100 routes" | "O(n) where n=routes, but regex dominates after ~500 routes" |
| "Cannot have constant-time + regex" | Absolute | Unchanged | "See: RE2 library, Rust regex crate, DFA compilation" |
| Severity ratings | HIGH/MEDIUM | Quantified by route count thresholds | Unchanged |
| Trie optimization | Theoretical | "Trie would save Xms at Y routes" | "Hybrid trie-regex used by gorilla/mux achieves..." |

---

## Claims That Would Be CONFIRMED

- Sequential iteration exists (structural)
- Scope mutation prevents naive caching (structural + logical)
- `url_path_for()` searches linearly (structural)
- Method check happens after regex (structural)

---

## Claims That Are UNFALSIFIABLE

- **"FLEXIBILITY × PERFORMANCE = COMPILE-TIME BUDGET"** — This is a framing device, not a testable claim
- **"DECLARATIVE COMPLETENESS × RUNTIME MUTABILITY = FRAMEWORK BOUNDARY"** — Same category

These are interpretive lenses, not factual assertions. They cannot be wrong; they can only be useful or not useful.

---

## Conservation Law for This Analysis

**STRUCTURAL CONFIDENCE × THEORETICAL AMBITION = AUDIT RISK**

The analysis grounds itself in code-derived observations (high confidence) but **escalates to impossibility theorems** (unverifiable without external expertise). The more ambitious the theoretical claim, the less the source code can support it.

**Distribution:**
- 70% structural observation (source-verified)
- 20% complexity theory (requires CS knowledge)
- 10% severity judgment (requires production data)

The audit risk concentrates in the impossibility theorem (Claim 4) — a single wrong "cannot" undermines the entire conservation law narrative, even if all structural observations are correct.
