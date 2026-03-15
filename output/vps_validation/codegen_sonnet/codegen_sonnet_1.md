## Step 1: Requirement Decomposition

| Capability | Input | Output | Edge Case That Breaks Naive Implementation |
|------------|-------|--------|---------------------------------------------|
| **Key-Value Storage** | key, value | value or None | Key doesn't exist — must return None without error |
| **LRU Eviction** | capacity limit | automatic eviction | Updating existing key must move it to "most recent", not create duplicate entry |
| **TTL Expiration** | TTL duration | items expire after time | Item expires between existence check and return — returns stale data |
| **Thread Safety** | concurrent ops | consistent state | Race: Thread A evicts while Thread B reads; deadlock from lock ordering |
| **Cleanup** | trigger | removed expired items | Modifying dict during iteration — RuntimeError |

**Dependency Order:** Storage → LRU ordering → TTL tracking → Thread safety wrapper → Cleanup

## Step 2: Interface-First Design

```python
class LRUCacheWithTTL:
    """
    Thread-safe LRU cache with TTL expiration.
    
    Invariants:
    - Cache size never exceeds max_size (post-cleanup)
    - get() never returns expired items
    - LRU order updated on every get/set
    - All public methods are thread-safe
    """
    
    def __init__(self, max_size: int, default_ttl: Optional[float] = None): ...
    def get(self, key: Any) -> Optional[Any]: ...
    def set(self, key: Any, value: Any, ttl: Optional[float] = None) -> None: ...
    def delete(self, key: Any) -> bool: ...
    def clear(self) -> None: ...
    def size(self) -> int: ...
    def cleanup_expired(self) -> int: ...
```

## Step 3: Implementation with Failure Prediction

```python
from collections import OrderedDict
from threading import RLock
from time import time
from typing import Any, Optional


class LRUCacheWithTTL:
    """
    Thread-safe LRU cache with TTL (time-to-live) expiration.
    
    Invariants maintained:
    - Cache never exceeds max_size items
    - get() returns None for missing or expired keys (never stale data)
    - LRU order is correctly maintained on all accesses
    - All operations are thread-safe via reentrant lock
    """

    def __init__(self, max_size: int, default_ttl: Optional[float] = None):
        """
        Initialize the LRU cache.
        
        Args:
            max_size: Maximum number of items. Must be >= 1.
            default_ttl: Default TTL in seconds. None means no expiration.
        
        Raises:
            ValueError: If max_size < 1
        
        Postcondition: Cache is empty and ready for use.
        """
        # BUG PREVENTION: Validate max_size to avoid division by zero
        # and meaningless cache behavior
        if max_size < 1:
            raise ValueError("max_size must be at least 1")
        
        self._max_size = max_size
        self._default_ttl = default_ttl
        
        # OrderedDict maintains insertion order; move_to_end() gives O(1) LRU
        # First item = least recently used, Last item = most recently used
        self._cache: OrderedDict[Any, Any] = OrderedDict()
        
        # Separate dict for expiration times (epoch seconds)
        # Key -> expiration timestamp (None means no expiration)
        self._expiry: dict[Any, Optional[float]] = {}
        
        # RLock (reentrant) prevents deadlock when same thread acquires lock
        # multiple times (e.g., set() calling cleanup_expired())
        self._lock = RLock()

    def get(self, key: Any) -> Optional[Any]:
        """
        Retrieve value by key if it exists and hasn't expired.
        
        Postcondition: 
        - If key exists and valid, it's moved to most-recently-used position
        - If key is expired, it's deleted and None is returned
        - Returns None for missing keys (no exception raised)
        """
        with self._lock:
            # BUG PREVENTION: Check existence first to avoid KeyError
            if key not in self._cache:
                return None
            
            # BUG PREVENTION: Check expiration BEFORE returning
            # Naive impl would return stale data
            if self._is_expired(key):
                # Lazy expiration: remove on access
                self._delete_internal(key)
                return None
            
            # BUG PREVENTION: Must update LRU order on hit
            # move_to_end() is O(1) in OrderedDict
            self._cache.move_to_end(key)
            return self._cache[key]

    def set(self, key: Any, value: Any, ttl: Optional[float] = None) -> None:
        """
        Store key-value pair with optional TTL.
        
        Args:
            key: Cache key
            value: Cache value
            ttl: Time-to-live in seconds. None uses default_ttl.
        
        Postcondition:
        - Key is stored and marked most-recently-used
        - If at capacity, least-recently-used item is evicted
        - If key already existed, old value is replaced (no duplicate entry)
        """
        with self._lock:
            # Calculate expiration timestamp
            effective_ttl = ttl if ttl is not None else self._default_ttl
            expiration = time() + effective_ttl if effective_ttl is not None else None
            
            # BUG PREVENTION: If key exists, delete first to avoid
            # duplicate entries and stale expiry times
            if key in self._cache:
                # Don't count as eviction - just replacing
                del self._cache[key]
                del self._expiry[key]
            
            # BUG PREVENTION: Check capacity BEFORE inserting
            # Off-by-one error would allow max_size + 1 items
            if len(self._cache) >= self._max_size:
                self._evict_lru()
            
            # Insert at end (most recently used position)
            self._cache[key] = value
            self._expiry[key] = expiration

    def delete(self, key: Any) -> bool:
        """
        Remove a key from the cache.
        
        Returns:
            True if key existed (even if expired), False otherwise
        
        Postcondition: Key is completely removed from cache and expiry tracking
        """
        with self._lock:
            return self._delete_internal(key)

    def clear(self) -> None:
        """
        Remove all items from cache.
        
        Postcondition: Cache is empty, both data structures cleared
        """
        with self._lock:
            self._cache.clear()
            self._expiry.clear()

    def size(self) -> int:
        """
        Return current number of items in cache.
        
        Note: May include expired items not yet cleaned up.
        """
        with self._lock:
            return len(self._cache)

    def cleanup_expired(self) -> int:
        """
        Remove all expired items from cache.
        
        Returns:
            Number of items removed
        
        Postcondition: No expired items remain in cache
        """
        with self._lock:
            current_time = time()
            
            # BUG PREVENTION: Collect keys first, don't modify dict during iteration
            # This avoids RuntimeError from changing dict size while iterating
            expired_keys = [
                key for key, exp in self._expiry.items()
                if exp is not None and exp <= current_time
            ]
            
            for key in expired_keys:
                self._delete_internal(key)
            
            return len(expired_keys)

    def _is_expired(self, key: Any) -> bool:
        """
        Check if a key has expired. Assumes key exists and lock is held.
        
        BUG PREVENTION: Must handle None expiration (no TTL) correctly.
        """
        expiration = self._expiry.get(key)
        if expiration is None:
            return False
        return time() > expiration

    def _delete_internal(self, key: Any) -> bool:
        """
        Delete key without acquiring lock. For internal use only.
        
        Returns: True if key existed, False otherwise
        """
        if key in self._cache:
            del self._cache[key]
            del self._expiry[key]
            return True
        return False

    def _evict_lru(self) -> None:
        """
        Evict least recently used item. Assumes lock is held.
        
        Postcondition: One item removed from front of LRU order.
        
        BUG PREVENTION: Must also remove from expiry dict,
        not just cache dict (memory leak in naive impl).
        """
        # popitem(last=False) removes first item (LRU) in O(1)
        if self._cache:
            key, _ = self._cache.popitem(last=False)
            # BUG PREVENTION: Don't forget to clean up expiry tracking
            self._expiry.pop(key, None)

    def __len__(self) -> int:
        """Allow len(cache) syntax."""
        return self.size()

    def __contains__(self, key: Any) -> bool:
        """
        Allow 'key in cache' syntax.
        
        Note: Returns False for expired keys (they're lazily removed).
        """
        with self._lock:
            if key not in self._cache:
                return False
            if self._is_expired(key):
                self._delete_internal(key)
                return False
            return True

    def __repr__(self) -> str:
        with self._lock:
            items = []
            for key, value in self._cache.items():
                if self._is_expired(key):
                    continue
                items.append(f"{key!r}: {value!r}")
            return f"LRUCacheWithTTL({{{', '.join(items)}}})"
```

**Mental Execution Against Requirements:**

1. ✅ **Storage**: get/set work, None returned for missing keys
2. ✅ **LRU**: OrderedDict + move_to_end() maintains order; _evict_lru() removes from front
3. ✅ **TTL**: _is_expired() checked on get(); expiration timestamp calculated on set()
4. ✅ **Thread Safety**: RLock wraps all public methods; reentrant for internal calls
5. ✅ **Cleanup**: cleanup_expired() collects keys first to avoid iteration-modification bug
6. ✅ **Edge cases**: max_size validation, existing key replacement, expiry cleanup in both dicts
