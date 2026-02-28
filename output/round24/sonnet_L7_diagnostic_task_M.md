# Level 7 Structural Diagnosis: LRU Cache with TTL Eviction

---

## I. The Initial Falsifiable Claim

**Claim:** The deepest structural problem is that TTL eviction and LRU eviction are implemented as two parallel, unsynchronized ordering systems — `OrderedDict` tracking access recency, `_ttls` dict tracking absolute time — that must stay in sync but share no coordinating invariant, producing O(n) scan cost on every operation and a cache that can simultaneously consider a key both "present" and "logically dead."

*Falsifiable how:* Run `_evict_expired()` in isolation; measure its cost grows linearly with store size regardless of how many entries are expired. Demonstrate a key existing in `_store` with `_ttls[key] <= time.time()` between operations.

---

## II. The Three-Expert Dialectic

### Expert A — Defender

The dual-structure split is the genuine root. Two dictionaries that must stay perfectly synchronized, but where *neither has authority over the other*, is a structural antipattern. Every operation becomes a two-phase commit with no rollback:

```python
# In delete(): what if _store deletion succeeds but _ttls deletion raises?
del self._store[key]
del self._ttls[key]  # orphaned state if anything goes wrong
```

The O(n) scan isn't incidental — it's *necessitated* by the structural choice. If you merge TTL into the ordered structure (e.g., store `(value, expiry)` tuples, or use a heap for expiry ordering), the scan disappears. The claim holds.

### Expert B — Attacker

The O(n) scan is a performance footnote, not an architectural wound. For n=100 (the default capacity), O(n) is irrelevant. The *actual* deepest problem is **absent thread safety with an appearance of correctness**. Every operation is a non-atomic multi-step mutation of shared state:

```python
def put(self, key, value, ttl=None):
    self._evict_expired()          # reads _ttls, mutates _store and _ttls
    if key in self._store:         # race window
        self._store.move_to_end(key)
    self._store[key] = value       # race window
    self._ttls[key] = time.time()  # race window
```

Two threads calling `put()` concurrently can corrupt both dictionaries, produce wrong stats, or evict entries they shouldn't. The dual-structure claim is identifying a symptom and calling it a cause.

### Expert C — Prober (attacks shared assumptions)

Both of you are assuming there's a *correct behavior* that this implementation is approximating. But you've both taken for granted something neither of you has questioned: **what does it mean for a key to "exist" in this cache?**

The cache internally tracks three distinct key states:
1. **Absent** — never inserted, or explicitly deleted
2. **Present-valid** — in `_store`, `_ttls[key] > now`  
3. **Present-expired** — in `_store`, `_ttls[key] <= now`, but `_evict_expired()` hasn't run yet

Yet `get()` collapses states 1 and 3 into identical behavior — returning `None`, incrementing `"misses"`. The structural problem isn't the data structures or the threading model. It's that **the cache's semantic contract is undefined**. No caller can know whether a `None` return means "absent," "expired," or "was evicted under LRU pressure." The eviction model is operation-triggered, not time-triggered, so TTL is not a time guarantee — it's a *"next-operation-after-expiry"* guarantee.

---

## III. The Transformation

| Dimension | Original Claim | Transformed Claim |
|---|---|---|
| **Level** | Implementation (data structures) | Semantic (contract) |
| **Scope** | Internal consistency | External observability |
| **Problem** | O(n) scan / dual-dict coupling | Undefined key identity / non-deterministic observable behavior |
| **Symptom** | Performance overhead | Callers cannot reason about cache state |

The claim transformed from *"how the internals work"* to *"what the cache promises."*

---

## IV. The Concealment Mechanism: Operational Legibility Masking Semantic Void

The gap between the two claims is not random — it reveals a specific concealment pattern:

**Every method is locally coherent. The overall contract is globally absent.**

`get()` reads correctly. `put()` writes correctly. `delete()` deletes correctly. `_evict_expired()` evicts correctly. You can read each method and convince yourself it "works." The code achieves *operational completeness* — every path terminates, every branch handles its case — while maintaining *semantic incompleteness*: no invariant is stated, no contract is defined, no behavior is guaranteed across time.

This is the mechanism: **Working code generates the illusion that meaning has been specified.** The implementation looks like a proof of a contract that was never written. Reviewers fix bugs in the implementation rather than questioning whether the implementation implements anything coherent.

---

## V. What the Entire Dialectic STILL Missed

The dialectic surfaced: dual-structure coupling, thread safety, undefined key states, operation-triggered eviction timing. But the concealment mechanism is *still operating* at a deeper layer. Here is what nobody questioned:

### The cache cannot store `None`

```python
cache.put("result", None)   # storing a valid computed result of None
val = cache.get("result")   # returns None
if val is None:             # caller interprets as miss — always
    recompute()             # infinite recomputation
```

`get()` returns `None` for three distinct situations:
- Key was never inserted
- Key was inserted with value `None`  
- Key expired or was evicted

The return type conflation is **invisible to the stats system**. Every `get()` on a `None`-valued key registers as a `"miss"` and increments `self._stats["misses"]`. The `hit_rate` reported by `stats()` will show 0% for this usage pattern — actively lying about cache effectiveness.

### The stats are measuring the wrong thing, in a way that hides it

```python
def stats(self):
    return {**self._stats, 
            "hit_rate": self._stats["hits"] / max(1, self._stats["hits"] + self._stats["misses"])}
```

`hit_rate` measures *operational frequency of the hit branch*, not cache utility. A cache that returns stale data on every call (because `_evict_expired()` is never triggered during a write-heavy workload on stable keys) would show 100% hit rate. A cache correctly storing `None` results would show 0% hit rate. The metric and the reality are decoupled.

The `evictions` counter merges LRU evictions (capacity pressure) and TTL evictions (staleness) — two operationally and semantically distinct events — into one number, destroying the diagnostic signal that would tell you *why* you're missing.

### The concealment mechanism's final layer

The stats don't just fail to reveal the problem — **they actively generate confidence that the system is working**. A dashboard showing hit_rate: 0.94 looks healthy. The operational legibility extends outward from the code into the observability layer. The code conceals its semantic void not just through readable methods but through credible-looking metrics that measure implementation activity rather than semantic correctness.

---

## Summary Diagram

```
Surface problem:      O(n) scan / dual-dict coupling
                              ↓ (dialectic transforms)
Deeper problem:       Undefined semantic contract / key identity
                              ↓ (concealment mechanism revealed)
Mechanism:            Operational legibility masks semantic void
                              ↓ (mechanism still operating)
Hidden deeper:        None-value conflation + stats measuring wrong
                      abstraction level, generating false confidence
                              ↓ (final concealment)
Root:                 No theory of correctness exists; the code
                      IS the spec, so its failures are invisible
                      by definition
```

The fix is not adding a sentinel value or a lock. It is writing the contract first: *what does this cache promise, to whom, under what conditions?* Every structural problem is downstream of that missing document.
