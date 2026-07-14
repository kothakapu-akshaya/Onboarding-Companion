"""Redis-based claim service for exclusive record locking during review."""

import logging

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

KEY_PREFIX = "claim:record:"


class ClaimService:
    """Atomic record claiming via Redis SET NX with TTL expiry."""

    def __init__(self, redis_url: str | None = None):
        """Initialize with optional Redis URL (defaults to Celery broker)."""
        self._redis = redis.from_url(
            redis_url or settings.CELERY_BROKER_URL,
            decode_responses=True,
        )

    def claim(
        self,
        user_id: str,
        record_uids: list[str],
        ttl: int | None = None,
    ) -> list[str]:
        """Atomically claim records. Returns only successfully claimed UIDs."""
        if not record_uids:
            return []

        ttl = ttl if ttl is not None else settings.CLAIM_TTL
        try:
            pipe = self._redis.pipeline()
            for uid in record_uids:
                pipe.set(f"{KEY_PREFIX}{uid}", user_id, nx=True, ex=ttl)
            results = pipe.execute()
            claimed = [uid for uid, ok in zip(record_uids, results) if ok]
            if claimed:
                logger.info(
                    f"Claimed {len(claimed)}/{len(record_uids)} records "
                    f"for user {user_id}"
                )
            return claimed
        except redis.RedisError as e:
            logger.warning(f"Redis claim failed, returning all candidates: {e}")
            return record_uids

    def release(self, record_uid: str) -> None:
        """Release a claim on a record (e.g. after review is complete)."""
        try:
            self._redis.delete(f"{KEY_PREFIX}{record_uid}")
        except redis.RedisError as e:
            logger.warning(f"Redis release failed for {record_uid}: {e}")

    def get_claimed_uids(self, record_uids: list[str]) -> set[str]:
        """Check which UIDs from the list are currently claimed."""
        if not record_uids:
            return set()

        try:
            pipe = self._redis.pipeline()
            for uid in record_uids:
                pipe.exists(f"{KEY_PREFIX}{uid}")
            results = pipe.execute()
            return {uid for uid, exists in zip(record_uids, results) if exists}
        except redis.RedisError as e:
            logger.warning(f"Redis check failed, assuming none claimed: {e}")
            return set()
