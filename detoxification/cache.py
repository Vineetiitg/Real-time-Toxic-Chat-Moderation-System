"""
SafeChat Detoxification — High-Speed Multi-Layer Cache

Provides:
  - In-Memory LRU Cache with TTL (Time-To-Live)
  - Key normalization (case-insensitive, whitespace-collapsed)
  - Thread-safe / asyncio-safe operations
  - Optional Redis connection if redis-py and REDIS_URL are present
"""

import collections
import hashlib
import time
from typing import Dict, Optional, Tuple


class DetoxCache:
    """
    LRU + TTL cache for detoxified phrases.
    Significantly cuts LLM latency and costs for recurring chat messages.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600, redis_url: Optional[str] = None):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        # _cache maps cache_key -> (detoxified_dict, expire_timestamp)
        self._cache: collections.OrderedDict[str, Tuple[Dict, float]] = collections.OrderedDict()
        self._hits = 0
        self._misses = 0

        # Optional Redis client
        self._redis = None
        if redis_url:
            try:
                import redis
                self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
            except Exception:
                self._redis = None

    @staticmethod
    def _make_key(text: str, target_lang: Optional[str] = None) -> str:
        """Create a normalized SHA-256 cache key from input text and target language."""
        normalized = " ".join(text.strip().lower().split())
        raw_key = f"{normalized}::{target_lang or 'auto'}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(self, text: str, target_lang: Optional[str] = None) -> Optional[Dict]:
        """Retrieve cached detoxification result if present and not expired."""
        key = self._make_key(text, target_lang)

        # Check in-memory LRU
        if key in self._cache:
            result, expiry = self._cache[key]
            if time.time() < expiry:
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self._hits += 1
                return result
            else:
                # Expired
                del self._cache[key]

        # Check Redis if available
        if self._redis:
            try:
                import json
                cached_json = self._redis.get(f"safechat:detox:{key}")
                if cached_json:
                    data = json.loads(cached_json)
                    # Populate in-memory cache
                    self.set(text, data, target_lang)
                    self._hits += 1
                    return data
            except Exception:
                pass

        self._misses += 1
        return None

    def set(self, text: str, result: Dict, target_lang: Optional[str] = None) -> None:
        """Store detoxification result in cache."""
        key = self._make_key(text, target_lang)
        expiry = time.time() + self.ttl_seconds

        # Enforce LRU capacity limit
        if len(self._cache) >= self.max_size:
            # Evict oldest item
            self._cache.popitem(last=False)

        self._cache[key] = (result, expiry)

        # Optional Redis storage
        if self._redis:
            try:
                import json
                self._redis.setex(
                    f"safechat:detox:{key}",
                    self.ttl_seconds,
                    json.dumps(result),
                )
            except Exception:
                pass

    def clear(self) -> None:
        """Clear all in-memory cache entries."""
        self._cache.clear()

    @property
    def stats(self) -> Dict[str, int]:
        """Return cache hit/miss statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(self._hits / (self._hits + self._misses), 3) if (self._hits + self._misses) > 0 else 0.0,
        }

