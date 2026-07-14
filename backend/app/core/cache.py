"""Redis-based response caching for infrequently-written reference data."""

import json
import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Generic Redis cache with TTL and pattern-based invalidation."""

    def __init__(self, redis_url: str | None = None):
        """Initialize Redis connection."""
        self._redis = redis.from_url(
            redis_url or settings.CELERY_BROKER_URL,
            decode_responses=True,
        )

    @staticmethod
    def _build_key(prefix: str, *parts: str) -> str:
        cleaned = [p.replace(":", "_") for p in parts if p]
        suffix = ":".join(cleaned)
        return f"cache:{prefix}:{suffix}" if suffix else f"cache:{prefix}"

    @staticmethod
    def _serialize(obj: Any) -> str:
        return json.dumps(obj, default=str, ensure_ascii=False)

    def get(self, key: str) -> Any | None:
        """Get cached value by key."""
        try:
            data = self._redis.get(key)
            if data is not None:
                return json.loads(data)
        except redis.RedisError as e:
            logger.warning(f"Redis get failed for {key}: {e}")
        return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set a cached value with TTL."""
        try:
            serialized = self._serialize(value)
            self._redis.setex(key, timedelta(seconds=ttl), serialized)
        except redis.RedisError as e:
            logger.warning(f"Redis set failed for {key}: {e}")

    def get_or_set(self, key: str, factory: Callable[[], Any], ttl: int) -> Any:
        """Get cached value or compute and cache it."""
        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value, ttl)
        return value

    def invalidate(self, pattern: str) -> None:
        """Invalidate all cache keys matching the pattern."""
        try:
            cursor = 0
            while True:
                cursor, keys = self._redis.scan(
                    cursor, match=pattern, count=100
                )
                if keys:
                    self._redis.delete(*keys)
                if cursor == 0:
                    break
        except redis.RedisError as e:
            logger.warning(f"Redis invalidation failed for {pattern}: {e}")


cache_service = CacheService()
