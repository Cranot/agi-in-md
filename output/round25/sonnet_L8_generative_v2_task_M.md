# Structural Diagnosis: LRU Cache with TTL

## The Claim

> **The deepest structural problem is that two competing eviction policies with genuinely incompatible contracts have their arbitration encoded in call-sequence order rather than explicit logic — making the cache's actual eviction behavior undocumented, untestable, and semantically invisible even to its author.**

This is falsifiable: one could argue TTL and LRU are naturally complementary, and the real problems are merely implementation bugs.

---

## Three Expert Dialectic

### Expert 1 (Defender): The Claim Holds

The entire codebase traces to one root: LRU says *recency determines value*, TTL says *age determines validity*. These aren't just different — they're orthogonal orderings of the same keyspace. When a hot key expires, which policy wins?

The code answers silently through call ordering:

```python
def get(self, key):
    self._evict_expired()   # TTL wins — expired hot keys die here
    if key in self._store:  # LRU is checked only among survivors
```

There is no policy object, no documented contract, no configurable arbitration. A user asking "will a key I accessed 1 second ago still be here?" gets two correct but contradictory answers depending on whether they're thinking about LRU or TTL. That ambiguity *lives in the architecture*.

---

### Expert 2 (Attacker): You've Named the Symptom, Not the Disease

Saying "two policies conflict" is observation, not diagnosis. Every cache with TTL has this property. Redis has it. Python's `functools.lru_cache` doesn't have TTL precisely *because* of this tension. The real problem is the **lazy-eager hybrid eviction**, which is a specific implementation failure:

```python
def get(self, key):
    self._evict_expired()  # scans ALL keys O(n) on every read
```

This is neither lazy (it doesn't defer until needed) nor eager (it doesn't maintain a heap). It's a full scan on every operation. Merge `_store` and `_ttls` into one dict of `CacheEntry` objects, add a min-heap for TTL ordering, and your "policy conflict" claim evaporates — the policies aren't the problem, the execution model is.

---

### Expert 3 (Prober): What Both of You Take for Granted

You both assume the cache *has* a real policy. Neither of you asked: **what should happen when a TTL-expired key is the LRU-newest key in the cache?**

The code gives a definite answer — TTL wins — but this answer is an accident of which method was called first in `get()`. Swap the two lines:

```python
def get(self, key):
    if key in self._store:   # LRU check first — now recency wins
        self._store.move_to_end(key)
        ...
    self._evict_expired()    # TTL now cleans up "behind" the access
```

This is an equally valid implementation with the *opposite contract*, and it's two lines swapped. Neither version is documented. Neither version is tested for this specific case. The Expert 1 / Expert 2 debate assumes the current answer is intentional. It probably isn't.

---

## Claim Transformation

| | Claim |
|---|---|
| **Original** | The deepest problem is parallel data structures (`_store`, `_ttls`) that can diverge |
| **After dialectic** | The deepest problem is **policy arbitration by accident of call sequencing** — an undocumented, untested contract that could invert with a two-line reorder |

**The gap between claims** is the difference between *structural* and *intentional*. The original claim is about data layout (fixable by refactoring). The transformed claim is about the absence of any design decision (unfixable by refactoring alone — you must first decide what the cache should *mean*).

---

## The Concealment Mechanism: Structural Symmetry Launders Semantic Conflict

The two eviction paths *look* like cooperative phases of one process:

```python
def put(self, key, value, ttl=None):
    self._evict_expired()           # Phase 1: clean expired
    ...
    while len(self._store) > self._capacity:  # Phase 2: enforce capacity
        self._store.popitem(last=False)
```

The visual symmetry — two cleanup operations, clean indentation, coherent naming — makes this read as *unified eviction logic*. It isn't. These are two independent policies with conflicting orderings, connected only by the fact that they share data structures. The symmetry launders the conflict into apparent cooperation.

Additionally, `_evict_expired()` is called defensively at the *start* of both `get()` and `put()`, which creates a false sense that expiration is eagerly enforced. It isn't — entries can be expired for arbitrary time between accesses, and in a read-heavy workload, expired LRU-dead entries accumulate silently.

---

## The Concealment-Deepening "Improvement"

This passes code review. It fixes real bugs. It makes things worse structurally.

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Generic, TypeVar
import time
from collections import OrderedDict

V = TypeVar('V')

class EvictionPolicy(Enum):
    """Controls arbitration between TTL and LRU eviction strategies."""
    TTL_PRIORITY  = "ttl_priority"   # Expire TTL before LRU eviction
    LRU_PRIORITY  = "lru_priority"   # Preserve recency across TTL boundaries

@dataclass
class CacheEntry(Generic[V]):
    value: V
    expires_at: float
    created_at: float = field(default_factory=time.time)

    def is_expired(self, now: Optional[float] = None) -> bool:
        return (now or time.time()) >= self.expires_at

    def ttl_remaining(self) -> float:
        return max(0.0, self.expires_at - time.time())


class LRUCache(Generic[V]):
    def __init__(
        self,
        capacity: int = 100,
        default_ttl: float = 300,
        eviction_policy: EvictionPolicy = EvictionPolicy.TTL_PRIORITY,
    ):
        self._capacity = capacity
        self._default_ttl = default_ttl
        self._eviction_policy = eviction_policy        # ← stored, never used
        self._store: OrderedDict[Any, CacheEntry[V]] = OrderedDict()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get(self, key: Any) -> Optional[V]:
        self._evict_expired()
        entry = self._store.get(key)
        if entry is not None and not entry.is_expired():  # ← redundant: always False
            self._store.move_to_end(key)
            self._stats["hits"] += 1
            return entry.value
        self._stats["misses"] += 1
        return None

    def put(self, key: Any, value: V, ttl: Optional[float] = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl  # ← fixes ttl=0 bug
        self._evict_expired()
        self._store[key] = CacheEntry(value=value, expires_at=time.time() + effective_ttl)
        self._store.move_to_end(key)
        self._enforce_capacity()

    def delete(self, key: Any) -> bool:
        return self._store.pop(key, None) is not None  # ← fixes double-delete

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, e in self._store.items() if e.is_expired(now)]
        for key in expired:
            del self._store[key]
            self._stats["evictions"] += 1

    def _enforce_capacity(self) -> None:
        while len(self._store) > self._capacity:
            self._store.popitem(last=False)
            self._stats["evictions"] += 1

    def stats(self) -> dict:
        total = self._stats["hits"] + self._stats["misses"]
        return {
            **self._stats,
            "size": len(self._store),
            "capacity": self._capacity,
            "hit_rate": self._stats["hits"] / max(1, total),
            "eviction_policy": self._eviction_policy.value,  # ← appears in output
        }
```

This would pass code review because:
- Real bugs are fixed (`ttl or default` → `ttl is not None`, double-delete race)
- Two structures merged into one (`CacheEntry` dataclass)  
- Generic typing added
- `EvictionPolicy` enum suggests explicit policy design
- `ttl_remaining()` signals observability care

---

## Three Properties Only Visible By Trying to Strengthen It

### 1. `EvictionPolicy` Has No Valid Implementation Site

When I tried to make the policy configurable, I had to find where to branch on it. There is no natural location. If I branch in `get()` before `_evict_expired()`, I expose expired values to LRU-priority mode. If I branch inside `_evict_expired()`, I must scan the LRU order to find the threshold. If I add a flag to skip `_evict_expired()` in `get()`, TTL becomes advisory-only on reads.

**What this reveals**: The policies aren't just competing — they're architecturally entangled at every point in the execution graph. There is no clean seam. The `EvictionPolicy` enum exposes this by being impossible to actually implement without restructuring the entire call graph. The original code hid this by never trying.

---

### 2. The `is_expired()` Double-Check in `get()` Is Always False — and That's Load-Bearing

The "improvement" adds `not entry.is_expired()` to `get()` as a safety check. This check **can never be true** — `_evict_expired()` was just called. It's dead code. But deleting it changes the code's *apparent* semantics: without it, the code looks like it trusts `_evict_expired()` to be complete. With it, the code looks like expiration is checked per-access.

**What this reveals**: The code's correctness *depends* on `_evict_expired()` being called immediately before any key access, making the entire LRU ordering semantically moot for expired keys. The double-check accidentally documents this dependency while making it look like defensive coding. The original code hid the coupling by having no check at all — it just *worked* because of call order.

---

### 3. `None` as Sentinel Is Unresolvable at This Abstraction Level

When I added `CacheEntry` and tried to fix the `None` return ambiguity, I could distinguish "key not present" (returns `None` from `.get()`) from "key present with `None` value" (returns `entry.value` which is `None`). But the `get()` signature returns `Optional[V]` — both cases are identical at the call site.

**What this reveals**: The `None` sentinel problem isn't a bug in the implementation — it's a contract mismatch baked into the interface design. The cache *cannot* distinguish cache-miss from stored-null without changing the return type to something like `Optional[CacheEntry[V]]` or a sentinel object — which then breaks every existing call site. Strengthening the internal structure made the external contract failure *more visible* because `CacheEntry` makes it obvious that `entry.value = None` is a valid state the cache intentionally stores, while the method's return type treats it identically to a miss.

---

## Summary

```
Original problem:  parallel data structures that can diverge
                          ↓
Real problem:      policy arbitration by accident of call sequence
                          ↓
Concealment:       structural symmetry launders semantic conflict
                          ↓
Deepened by:       EvictionPolicy enum (named but inert),
                   is_expired() double-check (documenting hidden coupling),
                   CacheEntry (exposing None sentinel as unresolvable)
```

The code doesn't fail because it's buggy. It fails because it *looks like* it has a design when it has only an implementation — and improvements that add design vocabulary without design decisions make that more true, not less.
