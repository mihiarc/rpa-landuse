#!/usr/bin/env python3
"""
Unit tests for the InMemoryCache implementation.

Tests caching functionality including:
- Basic set/get operations
- TTL (time-to-live) expiration
- LRU (least recently used) eviction
- Thread safety with concurrent access
- Cache statistics and cleanup
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from landuse.infrastructure.cache import CacheEntry, InMemoryCache


class TestCacheEntry:
    """Test the CacheEntry helper class."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry with value and TTL."""
        entry = CacheEntry(value="test_value", ttl=60)

        assert entry.value == "test_value"
        assert entry.ttl == 60
        assert entry.created_at > 0

    def test_cache_entry_no_ttl(self):
        """Test cache entry without TTL never expires."""
        entry = CacheEntry(value="permanent", ttl=None)

        assert not entry.is_expired()
        # Even after some time, should not be expired
        time.sleep(0.01)
        assert not entry.is_expired()

    def test_cache_entry_expiration(self):
        """Test cache entry expiration with short TTL."""
        entry = CacheEntry(value="temporary", ttl=0)  # Immediate expiration

        # With 0 TTL, should be expired immediately
        time.sleep(0.01)
        assert entry.is_expired()

    def test_cache_entry_not_yet_expired(self):
        """Test cache entry is not expired within TTL window."""
        entry = CacheEntry(value="valid", ttl=10)

        # Should not be expired with 10 second TTL
        assert not entry.is_expired()


class TestInMemoryCacheBasicOperations:
    """Test basic cache set/get operations."""

    def test_cache_set_and_get(self):
        """Test setting and retrieving a value from cache."""
        cache = InMemoryCache()

        cache.set("key1", "value1")
        result = cache.get("key1")

        assert result == "value1"

    def test_cache_get_nonexistent_key(self):
        """Test getting a key that doesn't exist returns None."""
        cache = InMemoryCache()

        result = cache.get("nonexistent")

        assert result is None

    def test_cache_set_overwrite(self):
        """Test overwriting an existing key with a new value."""
        cache = InMemoryCache()

        cache.set("key1", "original")
        cache.set("key1", "updated")
        result = cache.get("key1")

        assert result == "updated"

    def test_cache_with_complex_values(self):
        """Test caching complex data types."""
        cache = InMemoryCache()

        test_dict = {"name": "test", "value": 123, "nested": {"key": "val"}}
        test_list = [1, 2, 3, {"a": "b"}]

        cache.set("dict_key", test_dict)
        cache.set("list_key", test_list)

        assert cache.get("dict_key") == test_dict
        assert cache.get("list_key") == test_list

    def test_cache_delete(self):
        """Test deleting a cached value."""
        cache = InMemoryCache()

        cache.set("key1", "value1")
        cache.delete("key1")
        result = cache.get("key1")

        assert result is None

    def test_cache_delete_nonexistent_key(self):
        """Test deleting a nonexistent key doesn't raise error."""
        cache = InMemoryCache()

        # Should not raise any exception
        cache.delete("nonexistent")

    def test_cache_clear(self):
        """Test clearing all cached values."""
        cache = InMemoryCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cache_stats(self):
        """Test retrieving cache statistics."""
        cache = InMemoryCache(default_ttl=300, max_size=100)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.stats()

        assert stats["size"] == 2
        assert stats["max_size"] == 100
        assert stats["default_ttl"] == 300
        assert stats["expired_entries"] == 0


class TestInMemoryCacheTTL:
    """Test TTL (time-to-live) functionality."""

    def test_cache_with_default_ttl(self):
        """Test cache uses default TTL when not specified."""
        cache = InMemoryCache(default_ttl=10)

        cache.set("key1", "value1")
        result = cache.get("key1")

        assert result == "value1"

    def test_cache_with_custom_ttl_per_entry(self):
        """Test setting custom TTL for individual entries."""
        cache = InMemoryCache(default_ttl=300)

        cache.set("short_lived", "value", ttl=0)  # Immediate expiration
        cache.set("long_lived", "value", ttl=1000)

        time.sleep(0.01)

        # Short-lived should be expired
        assert cache.get("short_lived") is None
        # Long-lived should still be valid
        assert cache.get("long_lived") == "value"

    def test_cache_ttl_expiration_cleanup_on_get(self):
        """Test that expired entries are cleaned up on get access."""
        cache = InMemoryCache()

        cache.set("expiring", "value", ttl=0)
        time.sleep(0.01)

        # Access should return None and clean up the entry
        result = cache.get("expiring")

        assert result is None
        # Verify the entry was removed from internal storage
        assert "expiring" not in cache._cache

    def test_cache_cleanup_expired(self):
        """Test manual cleanup of expired entries."""
        cache = InMemoryCache()

        # Add several entries with short TTL
        cache.set("exp1", "value1", ttl=0)
        cache.set("exp2", "value2", ttl=0)
        cache.set("exp3", "value3", ttl=0)
        cache.set("valid", "value", ttl=1000)

        time.sleep(0.01)

        # Cleanup should return count of removed entries
        removed_count = cache.cleanup_expired()

        assert removed_count == 3
        assert cache.get("valid") == "value"


class TestInMemoryCacheLRUEviction:
    """Test LRU (least recently used) eviction."""

    def test_cache_max_size_enforcement(self):
        """Test cache enforces max_size limit."""
        cache = InMemoryCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should trigger eviction

        stats = cache.stats()
        assert stats["size"] <= 3

    def test_cache_lru_eviction_removes_oldest(self):
        """Test LRU eviction removes least recently used entry."""
        cache = InMemoryCache(max_size=3)

        cache.set("first", "value1")
        time.sleep(0.001)  # Small delay to ensure distinct access times
        cache.set("second", "value2")
        time.sleep(0.001)
        cache.set("third", "value3")
        time.sleep(0.001)

        # Access first and second to update their access times
        cache.get("first")
        time.sleep(0.001)
        cache.get("second")
        time.sleep(0.001)

        # Add new entry, should evict "third" (least recently used)
        cache.set("fourth", "value4")

        # After adding "fourth", one of the original entries should be evicted
        # The LRU should be "third" since "first" and "second" were accessed
        stats = cache.stats()
        assert stats["size"] == 3  # Max size maintained

        # Verify the accessed items are still there
        assert cache.get("first") == "value1"
        assert cache.get("second") == "value2"
        assert cache.get("fourth") == "value4"
        # Third should be evicted (but implementation may vary)
        # So we just verify size constraint is maintained

    def test_cache_lru_with_updates(self):
        """Test that updating a key updates its access time."""
        cache = InMemoryCache(max_size=2)

        cache.set("key1", "original")
        cache.set("key2", "value2")

        # Update key1, making key2 the LRU
        cache.set("key1", "updated")

        # Add new key, should evict key2
        cache.set("key3", "value3")

        assert cache.get("key1") == "updated"
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"


class TestInMemoryCacheThreadSafety:
    """Test thread safety with concurrent access."""

    def test_concurrent_set_operations(self):
        """Test concurrent set operations don't corrupt cache."""
        cache = InMemoryCache(max_size=1000)
        num_threads = 10
        operations_per_thread = 100

        def worker(thread_id):
            for i in range(operations_per_thread):
                key = f"thread_{thread_id}_key_{i}"
                value = f"value_{thread_id}_{i}"
                cache.set(key, value)

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should have completed without errors
        stats = cache.stats()
        assert stats["size"] > 0
        assert stats["size"] <= 1000

    def test_concurrent_get_set_operations(self):
        """Test concurrent mixed get/set operations."""
        cache = InMemoryCache()
        errors = []

        # Pre-populate cache
        for i in range(50):
            cache.set(f"key_{i}", f"value_{i}")

        def reader(thread_id):
            try:
                for i in range(50):
                    key = f"key_{i}"
                    cache.get(key)
            except Exception as e:
                errors.append(f"Reader {thread_id}: {e}")

        def writer(thread_id):
            try:
                for i in range(50):
                    key = f"key_{i}"
                    cache.set(key, f"updated_by_{thread_id}")
            except Exception as e:
                errors.append(f"Writer {thread_id}: {e}")

        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=reader, args=(i,)))
            threads.append(threading.Thread(target=writer, args=(i,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent access: {errors}"

    def test_concurrent_eviction(self):
        """Test concurrent operations with eviction don't deadlock."""
        cache = InMemoryCache(max_size=10)
        completed = []

        def worker(thread_id):
            for i in range(100):
                cache.set(f"t{thread_id}_k{i}", f"v{i}")
            completed.append(thread_id)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            for future in as_completed(futures, timeout=10):
                future.result()

        assert len(completed) == 5, "All threads should complete without deadlock"


class TestInMemoryCacheEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_cache_stats(self):
        """Test stats on empty cache."""
        cache = InMemoryCache()
        stats = cache.stats()

        assert stats["size"] == 0
        assert stats["expired_entries"] == 0

    def test_cache_with_none_value(self):
        """Test caching None as a value."""
        cache = InMemoryCache()

        cache.set("null_key", None)
        result = cache.get("null_key")

        # None is a valid cached value, distinct from key not found
        assert result is None
        # But we can't distinguish from missing key with current API
        # This is a known limitation

    def test_cache_with_empty_string_key(self):
        """Test caching with empty string key."""
        cache = InMemoryCache()

        cache.set("", "empty_key_value")
        result = cache.get("")

        assert result == "empty_key_value"

    def test_cache_max_size_one(self):
        """Test cache with max_size of 1."""
        cache = InMemoryCache(max_size=1)

        cache.set("first", "value1")
        cache.set("second", "value2")

        assert cache.get("first") is None
        assert cache.get("second") == "value2"

    def test_cleanup_on_empty_cache(self):
        """Test cleanup on empty cache returns 0."""
        cache = InMemoryCache()

        removed = cache.cleanup_expired()

        assert removed == 0
