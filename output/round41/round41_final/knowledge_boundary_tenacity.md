# Knowledge Boundary Analysis: Tenacity Retry Library

## Step 1: Claim Classification

### STRUCTURAL Claims (Derivable from source alone)

| Claim | Evidence |
|-------|----------|
| Action chain architecture: retry logic is built by appending functions to `iter_state.actions` list, executed sequentially in `iter()` | Lines 169-175, 185-209 |
| `ContextVar` for cross-boundary state: `_iter_state_var` holds `IterState` accessible across async calls | Lines 11, 165-169 |
| Thread-local statistics: `self._local = threading.local()` isolates stats per thread | Line 107, 119-125 |
| Copy pattern for per-call isolation: `wraps()` creates `copy = self.copy()` so each invocation has independent state | Lines 128-140 |
| Control flow via marker types: `DoAttempt`, `DoSleep` returned from action chain to signal iteration behavior | Lines 27-31, 212-220 |
| `AttemptManager` context pattern: `__exit__` captures exceptions and sets result, swallowing exceptions via `return True` | Lines 62-76 |
| `RetrySignal` masquerades as `Exception` but is a control signal | Lines 21-23 |
| `Future` subclass wraps attempt outcomes with attempt number | Lines 229-244 |
| Statistics cleared at 100 entries: `if len(self._local.statistics) > 100: self._local.statistics.clear()` | Lines 121-123 |
| Dual decorator modes: `@retry` bare and `@retry(...)` with args | Lines 263-271 |

### CONTEXTUAL Claims (Depend on external state)

| Claim | External Source | Staleness | Confidence |
|-------|-----------------|-----------|------------|
| `contextvars` is the correct approach for async-safe state in Python 3.7+ | [Python docs: contextvars](https://docs.python.org/3/library/contextvars.html) | Yearly (stable API) | High |
| `threading.local` is appropriate for sync thread isolation | [Python docs: threading](https://docs.python.org/3/library/threading.html#thread-local-data) | Yearly | High |
| `functools.WRAPPER_ASSIGNMENTS + ("__defaults__", "__kwdefaults__")` preserves all function metadata | [Python docs: functools](https://docs.python.org/3/library/functools.html) | Yearly | High |
| `futures.Future` is designed for concurrent execution results | [Python docs: concurrent.futures](https://docs.python.org/3/library/concurrent.futures.html) | Yearly | High |
| `time.monotonic` is preferred over `time.time` for elapsed measurement (unaffected by system clock changes) | [Python docs: time](https://docs.python.org/3/library/time.html#time.monotonic) | Yearly | High |
| Action-chain pattern is a known continuation-passing style variant | Academic CS literature | Never | High |
| `@dataclasses.dataclass(slots=True)` requires Python 3.10+ | [Python 3.10 release notes](https://docs.python.org/3/whatsnew/3.10.html) | Never | High |

### TEMPORAL Claims (May have expired)

| Claim | External Source | Staleness | Confidence |
|-------|-----------------|-----------|------------|
| No known security vulnerabilities in this implementation | [CVE Database](https://cve.mitre.org/), [GitHub Advisory](https://github.com/advisories) | Daily | Unknown |
| `slots=True` in dataclass is current best practice (was `@dataclass` + separate `__slots__` pre-3.10) | [PEP 557](https://peps.python.org/pep-0557/), Python 3.10 changelog | Yearly | High |
| This is the current/recommended retry library (vs `retrying` package it forked from) | [Tenacity GitHub](https://github.com/jd/tenacity), PyPI download stats | Monthly | High |
| No deprecated APIs in use (vs `threading.Thread.setDaemon` style patterns) | Python deprecation tracker | Yearly | High |

### ASSUMED Claims (Untested assumptions)

| Claim | What Would Test It | Confidence |
|-------|-------------------|------------|
| Statistics 100-entry clear limit is sufficient for typical use cases | Benchmark: memory profile of long-running retries with various clear thresholds | Low |
| `ContextVar` approach correctly handles nested retry decorators on same function | Unit test: `@retry @retry def f()` — which state wins? | Medium |
| `DoAttempt`/`DoSleep` marker class pattern has acceptable performance vs enum/int constants | Microbenchmark: 10^6 iterations comparing marker types | Medium |
| Thread-local + ContextVar dual approach has no edge cases in mixed sync/async code | Integration test: sync function calling async retry-wrapped function | Low |
| `RetrySignal` as `Exception` subclass doesn't interfere with `except Exception` handlers | Test: `try: retry_func() except Exception: pass` — does retry continue? | Medium |
| `copy()` deep-copy semantics are correct for nested strategy objects | Test: `retry(wait=wait_chain(...)).copy().wait is retry(...).wait` | Medium |

---

## Step 3: Gap Map

### API_DOCS (Verifiable from official documentation)

| Gap | Source URL | Impact if Wrong |
|-----|------------|-----------------|
| `contextvars` async safety guarantees | https://docs.python.org/3/library/contextvars.html | **CRITICAL** — If ContextVar doesn't work as assumed, nested async retries corrupt state |
| `functools.wraps` metadata preservation completeness | https://docs.python.org/3/library/functures.html | **MODERATE** — Missing metadata breaks introspection-heavy frameworks |
| `time.monotonic` clock guarantee | https://docs.python.org/3/library/time.html | **LOW** — Would affect timing accuracy only |

### CVE_DB (Security advisory databases)

| Gap | Source URL | Impact if Wrong |
|-----|------------|-----------------|
| No DoS vulnerability via statistics unbounded growth | https://cve.mitre.org/, https://github.com/advisories | **HIGH** — The 100-entry clear is arbitrary; malicious input could exploit |
| No exception injection via `RetrySignal` in production code | Security audit | **MODERATE** — Control-flow-as-exception could bypass security handlers |

### COMMUNITY (Stack Overflow, GitHub issues)

| Gap | Source URL | Impact if Wrong |
|-----|------------|-----------------|
| Nested `@retry` decorators behavior | GitHub issues, Stack Overflow | **MODERATE** — Undocumented interaction |
| Thread-local + ContextVar interaction in mixed code | https://discuss.python.org/, Stack Overflow | **HIGH** — Potential silent state corruption |

### BENCHMARK (Requires running measurements)

| Gap | Test Design | Impact if Wrong |
|-----|-------------|-----------------|
| Marker class performance vs primitives | Microbenchmark 10^6 iterations | **LOW** — Performance degradation only |
| Statistics clear threshold sufficiency | Memory profile over 24hr retry storm | **HIGH** — Production OOM risk |
| Action chain overhead at scale | Profile with 50+ chained strategies | **MODERATE** — Latency accumulation |

### CHANGELOG (Release notes)

| Gap | Source URL | Impact if Wrong |
|-----|------------|-----------------|
| Python version compatibility (`slots=True`) | https://docs.python.org/3/whatsnew/3.10.html | **HIGH** — Runtime error on Python < 3.10 |
| `contextvars` availability (3.7+) | https://docs.python.org/3/whatsnew/3.7.html | **MODERATE** — Import error on old Python |

---

## Step 4: Priority Ranking

### 1. CRITICAL: ContextVar + threading.local dual state management
**Why #1:** The code uses TWO different state isolation mechanisms (`ContextVar` for `iter_state`, `threading.local` for `statistics`). In mixed sync/async code or thread pool executors running async code, these could diverge.
- **If wrong:** Silent state corruption, cross-talk between retry invocations, lost statistics
- **Verification:** Integration test suite with `asyncio.run_in_executor` calling retry-wrapped functions

### 2. HIGH: Statistics clear threshold (100 entries)
**Why #2:** Arbitrary magic number with no documented justification. Long-running services with many retry attempts could hit this repeatedly.
- **If wrong:** Memory leak (if too high) or lost observability (if too low/cleared too often)
- **Verification:** Memory profiling under sustained retry load; analyze real-world retry patterns

### 3. HIGH: Nested `@retry` decorator behavior
**Why #3:** Code doesn't explicitly handle being wrapped by another `@retry`. The `ContextVar` would be shared, creating ambiguous state.
- **If wrong:** Outer retry's `iter_state` corrupted by inner retry, or vice versa
- **Verification:** Unit test: `@retry(stop=stop_after_attempt(3)) @retry(stop=stop_after_attempt(5)) def f(): ...`

### 4. MODERATE: `RetrySignal` exception-class hierarchy interaction
**Why #4:** `RetrySignal(Exception)` means `except Exception` catches it. User code with broad exception handlers could inadvertently suppress retry control flow.
- **If wrong:** Retries silently stop, or retry signal propagates to caller unexpectedly
- **Verification:** Test retry behavior inside `try/except Exception` blocks

### 5. MODERATE: `copy()` shallow vs deep copy semantics
**Why #5:** `copy()` creates new instance but strategy objects (wait, retry, stop callables) are referenced, not copied.
- **If wrong:** Shared mutable state in strategy objects across retry invocations
- **Verification:** Mutation test: modify strategy state during retry, observe sibling invocations

### 6. LOW: Python version compatibility (`slots=True`)
**Why #6:** Already encoded in code (`slots=True`), but if deployed on Python < 3.10, immediate failure.
- **If wrong:** Import-time error
- **Verification:** CI matrix testing 3.7, 3.8, 3.9, 3.10, 3.11, 3.12

---

## Summary Statistics

| Category | Count | Impact Range |
|----------|-------|--------------|
| STRUCTURAL | 10 | N/A (verifiable from source) |
| CONTEXTUAL | 7 | Low-Medium |
| TEMPORAL | 4 | Low-High |
| ASSUMED | 6 | Medium-High |

**Total claims analyzed:** 27

**Gaps requiring external verification:** 17 (63%)

**Highest-impact unverified claims:**
1. Dual state management correctness (ContextVar + threading.local)
2. Statistics threshold sufficiency
3. Nested decorator behavior
