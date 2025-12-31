"""
Caching Layer Module
Provides in-memory caching for performance optimization
"""

import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import asyncio
from collections import OrderedDict

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a single cache entry with TTL"""

    def __init__(self, value: Any, ttl: int):
        """
        Initialize a cache entry

        Args:
            value: The cached value
            ttl: Time to live in seconds
        """
        self.value = value
        self.created_at = datetime.now()
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if the cache entry has expired"""
        if self.ttl == 0:  # 0 means never expire
            return False
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl)


class LRUCache:
    """
    Least Recently Used (LRU) Cache implementation
    with Time To Live (TTL) support
    """

    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        """
        Initialize LRU Cache

        Args:
            max_size: Maximum number of items in cache
            default_ttl: Default time to live in seconds
        """
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]

        # Check if expired
        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: int = None):
        """
        Set a value in the cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self.default_ttl

        # Remove if already exists
        if key in self.cache:
            del self.cache[key]

        # Add new entry
        self.cache[key] = CacheEntry(value, ttl)

        # Remove oldest if cache is full
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def delete(self, key: str):
        """Delete a key from the cache"""
        if key in self.cache:
            del self.cache[key]

    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(hit_rate, 2)
        }

    def cleanup_expired(self):
        """Remove all expired entries"""
        expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]
        for key in expired_keys:
            del self.cache[key]
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")


class MemoryCache:
    """
    Main cache manager with multiple cache instances
    """

    def __init__(self):
        """Initialize the memory cache"""
        # Different caches for different purposes with appropriate TTLs
        self.session_cache = LRUCache(max_size=1000, default_ttl=1800)  # 30 minutes
        self.user_cache = LRUCache(max_size=5000, default_ttl=3600)     # 1 hour
        self.leaderboard_cache = LRUCache(max_size=50, default_ttl=300) # 5 minutes
        self.quiz_cache = LRUCache(max_size=500, default_ttl=1800)      # 30 minutes
        self.stats_cache = LRUCache(max_size=1000, default_ttl=600)     # 10 minutes

        # Start cleanup task
        self._cleanup_task = None

    def start_cleanup(self):
        """Start automatic cleanup task"""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(300)  # Run every 5 minutes
                self.cleanup_all_expired()

        try:
            self._cleanup_task = asyncio.create_task(cleanup_loop())
        except RuntimeError:
            # No event loop running, cleanup will be manual
            pass

    def cleanup_all_expired(self):
        """Cleanup expired entries from all caches"""
        self.session_cache.cleanup_expired()
        self.user_cache.cleanup_expired()
        self.leaderboard_cache.cleanup_expired()
        self.quiz_cache.cleanup_expired()
        self.stats_cache.cleanup_expired()

    # Session cache operations
    def get_session(self, user_id: int) -> Optional[Dict]:
        """Get cached session data"""
        return self.session_cache.get(f"session:{user_id}")

    def set_session(self, user_id: int, session_data: Dict, ttl: int = None):
        """Cache session data"""
        self.session_cache.set(f"session:{user_id}", session_data, ttl)

    def delete_session(self, user_id: int):
        """Delete cached session"""
        self.session_cache.delete(f"session:{user_id}")

    # User cache operations
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get cached user data"""
        return self.user_cache.get(f"user:{user_id}")

    def set_user(self, user_id: int, user_data: Dict, ttl: int = None):
        """Cache user data"""
        self.user_cache.set(f"user:{user_id}", user_data, ttl)

    def delete_user(self, user_id: int):
        """Delete cached user"""
        self.user_cache.delete(f"user:{user_id}")

    # Leaderboard cache operations
    def get_leaderboard(self, category: str = "global") -> Optional[list]:
        """Get cached leaderboard"""
        return self.leaderboard_cache.get(f"leaderboard:{category}")

    def set_leaderboard(self, leaderboard_data: list, category: str = "global", ttl: int = None):
        """Cache leaderboard data"""
        self.leaderboard_cache.set(f"leaderboard:{category}", leaderboard_data, ttl)

    def invalidate_leaderboards(self):
        """Invalidate all leaderboard caches"""
        self.leaderboard_cache.clear()

    # Quiz cache operations
    def get_quiz(self, quiz_name: str) -> Optional[Dict]:
        """Get cached quiz data"""
        return self.quiz_cache.get(f"quiz:{quiz_name}")

    def set_quiz(self, quiz_name: str, quiz_data: Dict, ttl: int = None):
        """Cache quiz data"""
        self.quiz_cache.set(f"quiz:{quiz_name}", quiz_data, ttl)

    def delete_quiz(self, quiz_name: str):
        """Delete cached quiz"""
        self.quiz_cache.delete(f"quiz:{quiz_name}")

    # Stats cache operations
    def get_stats(self, user_id: int) -> Optional[Dict]:
        """Get cached user statistics"""
        return self.stats_cache.get(f"stats:{user_id}")

    def set_stats(self, user_id: int, stats_data: Dict, ttl: int = None):
        """Cache user statistics"""
        self.stats_cache.set(f"stats:{user_id}", stats_data, ttl)

    def invalidate_stats(self, user_id: int):
        """Invalidate cached statistics for a user"""
        self.stats_cache.delete(f"stats:{user_id}")

    # General operations
    def clear_all(self):
        """Clear all caches"""
        self.session_cache.clear()
        self.user_cache.clear()
        self.leaderboard_cache.clear()
        self.quiz_cache.clear()
        self.stats_cache.clear()
        logger.info("All caches cleared")

    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all caches"""
        return {
            'session_cache': self.session_cache.get_stats(),
            'user_cache': self.user_cache.get_stats(),
            'leaderboard_cache': self.leaderboard_cache.get_stats(),
            'quiz_cache': self.quiz_cache.get_stats(),
            'stats_cache': self.stats_cache.get_stats()
        }

    def stop_cleanup(self):
        """Stop the cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()


# Global cache instance
_cache_instance = None


def get_cache() -> MemoryCache:
    """Get or create the global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MemoryCache()
        _cache_instance.start_cleanup()
    return _cache_instance
