"""Caching implementations for the application."""

import threading
import time
from typing import Any, Dict, Optional

from landuse.core.interfaces import CacheInterface


class CacheEntry:
    """Cache entry with TTL support."""

    def __init__(self, value: Any, ttl: Optional[int] = None):
        """Initialize cache entry."""
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl


class InMemoryCache(CacheInterface):
    """
    Thread-safe in-memory cache implementation with TTL support.

    Features:
    - Thread-safe operations
    - TTL (time-to-live) support
    - Automatic cleanup of expired entries
    - Memory-efficient storage
    """

    def __init__(self, default_ttl: Optional[int] = None, max_size: int = 1000):
        """
        Initialize in-memory cache.

        Args:
            default_ttl: Default TTL in seconds (None for no expiration)
            max_size: Maximum number of entries to cache
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._access_times: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get cached value by key."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            if entry.is_expired():
                # Clean up expired entry
                del self._cache[key]
                self._access_times.pop(key, None)
                return None

            # Update access time for LRU
            self._access_times[key] = time.time()
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with optional TTL."""
        with self._lock:
            # Use provided TTL or default
            effective_ttl = ttl if ttl is not None else self.default_ttl

            # Ensure we don't exceed max size
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()

            # Store the entry
            self._cache[key] = CacheEntry(value, effective_ttl)
            self._access_times[key] = time.time()

    def delete(self, key: str) -> None:
        """Delete cached value."""
        with self._lock:
            self._cache.pop(key, None)
            self._access_times.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._access_times:
            return

        # Find least recently used key
        lru_key = min(self._access_times, key=self._access_times.get)

        # Remove it
        self._cache.pop(lru_key, None)
        self._access_times.pop(lru_key, None)

    def cleanup_expired(self) -> int:
        """Clean up expired entries and return count removed."""
        with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

            for key in expired_keys:
                del self._cache[key]
                self._access_times.pop(key, None)

            return len(expired_keys)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "default_ttl": self.default_ttl,
                "expired_entries": sum(1 for entry in self._cache.values() if entry.is_expired()),
            }
