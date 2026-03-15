```python
import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Dict, Optional, Tuple

class LRUCache:
    """
    A thread-safe LRU (Least Recently Used) cache with TTL (Time-To-Live) expiration.
    
    This cache combines LRU eviction policy with time-based expiration. Items are evicted
    either when they exceed their TTL or when the cache reaches capacity, in which case
    the least recently accessed items are removed first.
    
    Thread Safety:
    All public methods are thread-safe, using a lock to ensure atomic operations.
    """
    
    def __init__(self, capacity: int, default_ttl: float = 3600.0):
        """
        Initialize the LRUCache.
        
        Args:
            capacity: Maximum number of items the cache can hold.
            default_ttl: Default Time-To-Live for items in seconds. Defaults to 1 hour.
            
        Raises:
            ValueError: If capacity is not positive.
        """
        if capacity <= 0:
            raise ValueError("Cache capacity must be positive")
            
        self.capacity = capacity
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = Lock()
        self._current_time = time.time
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve an item from the cache.
        
        Args:
            key: The key to look up.
            
        Returns:
            The value associated with the key if it exists and hasn't expired,
            None otherwise.
            
        Invariant:
            If a non-None value is returned, the item is marked as most recently used.
        """
        with self._lock:
            current_time = self._current_time()
            
            if key not in self._cache:
                return None
                
            value, expiry_time = self._cache[key]
            
            if current_time > expiry_time:
                del self._cache[key]
                return None
                
            # Move to end to mark as most recently used
            self._cache.move_to_end(key)
            return value
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Add or update an item in the cache.
        
        Args:
            key: The key to associate with the value.
            value: The value to store.
            ttl: Time-To-Live in seconds. If None, uses default_ttl.
            
        Invariant:
            The cache size does not exceed capacity after this operation.
            The item is marked as most recently used.
        """
        with self._lock:
            current_time = self._current_time()
            item_ttl = ttl if ttl is not None else self.default_ttl
            expiry_time = current_time + item_ttl
            
            # If key exists, update it and move to end
            if key in self._cache:
                self._cache[key] = (value, expiry_time)
                self._cache.move_to_end(key)
            else:
                # Add new item
                self._cache[key] = (value, expiry_time)
                
                # Evict least recently used items if needed
                while len(self._cache) > self.capacity:
                    self._cache.popitem(last=False)
    
    def remove(self, key: str) -> bool:
        """
        Remove an item from the cache.
        
        Args:
            key: The key to remove.
            
        Returns:
            True if the key was found and removed, False otherwise.
            
        Invariant:
            The cache size is reduced by 1 if the key existed.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """
        Remove all items from the cache.
        
        Invariant:
            After this operation, the cache is empty.
        """
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """
        Get the current number of items in the cache.
        
        Returns:
            The number of non-expired items in the cache.
        """
        with self._lock:
            return len(self._cache)
    
    def contains(self, key: str) -> bool:
        """
        Check if a key exists in the cache and hasn't expired.
        
        Args:
            key: The key to check.
            
        Returns:
            True if the key exists and hasn't expired, False otherwise.
        """
        with self._lock:
            if key not in self._cache:
                return False
                
            current_time = self._current_time()
            _, expiry_time = self._cache[key]
            
            if current_time > expiry_time:
                del self._cache[key]
                return False
                
            return True
```
