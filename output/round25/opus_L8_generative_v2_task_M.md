# Generative Diagnostic: LRU Cache with TTL

## The Claim (Falsifiable)

**The deepest structural problem is that `get()` contains no per-key TTL check—it relies entirely on the O(n) full-scan `_evict_expired()` as its sole correctness guarantee that stale data is never served. The O(n) scan isn't a performance problem. It's a load-bearing correctness invariant disguised as a housekeeping routine.**

---

## Three-Expert Dialectic

**Expert 1 (Defender):** Correct. Trace `get()`: it calls `_evict_expired()`, which does a full dict scan, removing all expired keys. Only *then* does it check `if key in self._store`. There is no `if self._ttls[key] <= now` guard on the individual key lookup. Remove or weaken the scan, and you serve stale data. The scan isn't optimization—it's the contract.

**Expert 2 (Attacker):** The deeper problem is the *split state*. `_store` and `_ttls` are two dictionaries that must agree at all times, synchronized across four methods (`get`, `put`, `delete`, `_evict_expired`) with no single enforcement point. The missing per-key check is a *consequence* of this split: because TTL metadata lives outside the value, checking it at lookup time requires cross-referencing a second structure—so the author chose to batch-clean instead. Embed TTL in the stored value, and the per-key check becomes trivial and obvious.

**Expert 3 (Probing assumptions):** Both of you assume LRU and TTL should coexist in one structure. But they have fundamentally incompatible temporal semantics: LRU is *relative* (ordering by recency), TTL is *absolute* (anchored to wall-clock). The `_evict_expired` scan runs *before* LRU access reordering in `get()`, meaning TTL eviction can destroy LRU signal. A frequently-accessed key that expires and gets re-inserted loses its recency history. The two policies don't compose—they *interfere*, and the code has no concept of priority between them.

## Transformed Claim

> The cache fuses two temporally incompatible eviction policies (relative-order LRU and absolute-time TTL) into a split-state pair (`_store` + `_ttls`) with no formal synchronization invariant. The split makes per-key TTL checking non-obvious, which forces a full O(n) scan that is simultaneously the only correctness barrier against serving stale data *and* the mechanism by which TTL eviction silently destroys LRU ordering information.

### The Gap (Diagnostic of My Own Reasoning)

My original claim focused on the scan as a misidentified correctness invariant. The transformed claim reveals the scan is a **symptom of three entangled problems**: split state, policy interference, and a missing point-check—each of which independently makes the others harder to see. I initially mistook a *convergence point* for a *root cause*.

---

## The Concealment Mechanism

**Familiar API shape as correctness proxy.**

`OrderedDict`, `get`/`put`/`delete`, a `_stats` dict with `hit_rate`—this looks like every LRU cache tutorial ever written. Reviewers pattern-match to "standard implementation" and stop analyzing. The `_evict_expired` method has a clean, self-documenting name. The stats dictionary creates an aura of production-readiness. These are **legibility signals that substitute for structural analysis**. Nobody questions the invariants of code that *looks like it was copied from the right textbook*.

---

## The Engineered Concealment (Passes Code Review, Deepens the Problem)

```python
def _evict_expired(self, max_batch=64):
    """Evict expired entries in bounded batches for O(1) amortized performance.
    
    Mirrors Redis's probabilistic expiration strategy: process a bounded
    number of entries per call to avoid O(n) pauses under high load.
    """
    now = time.time()
    evicted = 0
    for key in list(self._ttls):
        if evicted >= max_batch:
            break
        if self._ttls[key] <= now:
            del self._store[key]
            del self._ttls[key]
            self._stats["evictions"] += 1
            evicted += 1
```

**Why this passes review:** It cites Redis. It addresses the obvious O(n) concern. It's a clean, bounded loop. The commit message writes itself: *"Bound TTL eviction to O(1) amortized, preventing latency spikes at high cache occupancy."*

**Why it's destructive:** Since `get()` has **no per-key TTL check**, any expired key that survives the batch cutoff will be served as valid. Under load with many expired entries, the cache silently serves stale data. The bug is non-deterministic, load-dependent, and nearly impossible to reproduce in unit tests.

---

## Three Properties Visible Only Because I Tried to Strengthen the Concealment

1. **The O(n) scan is silently load-bearing for correctness.** Only by trying to "optimize" it did I discover that removing it doesn't degrade performance—it introduces a **data correctness violation**. There is no secondary check. The scan is the only wall between expired data and the caller.

2. **The split state (`_store` / `_ttls`) makes the fix non-obvious.** If TTL were embedded in the stored value (e.g., `_store[key] = (value, expires_at)`), then `get()` would naturally check expiration at lookup time, and batch eviction *would be safe*. The split is what makes the "optimization" lethal—it separates the data from the metadata needed to validate it at the point of access.

3. **The `evictions` counter actively prevents diagnosis.** TTL expirations and LRU capacity evictions are counted identically. When the batched version starts serving stale data, the eviction count *drops* (fewer expired keys cleaned per call), which looks like *improved* cache efficiency in dashboards. The monitoring system rewards the bug.
