# Knowledge Audit: Tenacity Retry Library

**No analysis provided to audit.** The source code is present but there's no analytical text making claims about it. I'll demonstrate the audit methodology by classifying what claims would be SAFE (source-derived) vs KNOWLEDGE CLAIMS (external-dependent) for this codebase.

---

## Structural Claims — SAFE (Source-Verifiable)

These require no external knowledge. Any analyst with the source can verify:

| Claim Type | Examples from Code | Verification |
|------------|-------------------|--------------|
| **Architecture** | Action chain pattern via `_add_action_func` | Line 143-147, 177-211 |
| **State isolation** | `contextvars.ContextVar` for iteration state | Line 10, 159-164 |
| **Thread safety** | `threading.local()` for statistics | Line 117, 120-125 |
| **Control flow** | `DoAttempt`/`DoSleep` as continuation markers | Line 33-39, 226-235 |
| **Composition** | Strategies passed as callables: `stop`, `wait`, `retry` | Line 93-100 |
| **Copy semantics** | `_first_set` for partial override | Line 53-54, 127-142 |
| **Statistics lifecycle** | Clear on begin, accumulate through attempts | Line 166-170 |

---

## Knowledge Claim Categories — AUDIT REQUIRED

These assertions about the code require external verification:

### 1. **API Correctness Claims**

| Claim | Dependency | Failure Mode | Confabulation Risk |
|-------|------------|--------------|-------------------|
| "The `retry_if_exception_type()` default catches all exceptions" | Documentation of default args | Default may be `Exception` (not `BaseException`), or may have changed | **HIGH** — defaults are commonly misremembered |
| "`before_sleep` is called with `RetryCallState`" | Function signature in docs/modules | May receive different args, or be deprecated | **MEDIUM** |
| "The decorator works with async functions" | Async implementation testing | Async may require `AsyncRetrying` subclass | **HIGH** — common assumption, often wrong |

### 2. **Behavioral Claims**

| Claim | Dependency | Failure Mode | Confabulation Risk |
|-------|------------|--------------|-------------------|
| "Statistics are cleared after 100 entries" | Line 122-124 behavior | The `> 100` check may be bug or intentional — version-dependent | **LOW** — visible in source |
| "The library is thread-safe" | Threading documentation, race condition testing | `contextvars` isolates coroutine state but `threading.local` has known edge cases | **MEDIUM** |
| "Idle time accumulates across retries" | Runtime verification | Off-by-one in sleep accumulation | **LOW** — visible in source |

### 3. **Best Practices Claims**

| Claim | Dependency | Failure Mode | Confabulation Risk |
|-------|------------|--------------|-------------------|
| "This is the canonical retry pattern" | Python ecosystem conventions | Alternative patterns (decorator stacking, middleware) may be preferred | **MEDIUM** |
| "Strategy objects should be stateless" | Library author guidance | Some strategies may legitimately hold state | **MEDIUM** |
| "Use `retry_with()` for per-call customization" | API design intent | May be discouraged or deprecated | **HIGH** |

### 4. **Security/Reliability Claims**

| Claim | Dependency | Failure Mode | Confabulation Risk |
|-------|------------|--------------|-------------------|
| "No memory leak from unbounded action list" | Runtime profiling | Actions accumulate within iteration but reset per-attempt | **LOW** — visible in source |
| "Exception chaining preserves traceback" | Python version compatibility | `raise ... from` behavior varies by Python version | **HIGH** |
| "Context variable isolation prevents cross-request contamination" | Python contextvars semantics | Contextvars have subtle async behavior | **MEDIUM** |

---

## Confabulation Hot Spots

The most dangerous claims an analyst might make:

1. **"This works with asyncio"** — HIGH risk. The code shows `Retrying.__call__` as synchronous. Async would require `AsyncRetrying` (not shown here but exists in full library).

2. **"The default retry catches everything"** — HIGH risk. `retry_if_exception_type()` without args may have specific default behavior not visible in source.

3. **"Statistics are thread-safe"** — MEDIUM risk. `threading.local()` is used but the `> 100` clear could race with concurrent reads.

4. **"This is production-ready code"** — MEDIUM risk. No visibility into test coverage, maintainer activity, or known issues.

---

## Improvement with External Resources

| Resource | Claims It Would Confirm/Refute |
|----------|-------------------------------|
| **Official docs** | Default args, async support, recommended patterns |
| **GitHub issues** | Known bugs, race conditions, deprecation notices |
| **CVE database** | Security vulnerabilities in retry logic |
| **Changelog** | API stability, breaking changes across versions |
| **Benchmark data** | Performance claims about overhead |

---

## Conservation Law

**STRUCTURAL_FINDINGS × KNOWLEDGE_CLAIM_CONFIDENCE = CONSTANT**

The more detailed the structural analysis (pure source derivation), the more it exposes gaps requiring external verification. Deep structural analysis **generates** knowledge claims at a predictable rate:

- Each composition point (`copy()`, strategy injection) → API contract claim
- Each threading/async primitive → concurrency safety claim  
- Each default argument → configuration behavior claim
- Each state transition → temporal correctness claim

**The audit reveals: structural depth doesn't eliminate knowledge dependencies — it surfaces them.** An analysis that makes no knowledge claims has either (a) not gone deep enough structurally, or (b) tacitly assumed external facts without acknowledgment.
