"""
Nexus Mail — Redis Client & Distributed Locking
Prevents race conditions (e.g., duplicated emails) during concurrent sync/processing.
Uses Redis locking to guarantee mutually exclusive execution.
"""

from redis import asyncio as aioredis
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from app.core.config import get_settings
import structlog

logger = structlog.get_logger(__name__)

# Module-level connection pool
redis_pool: aioredis.Redis | None = None


async def connect_to_redis():
    """Initialize the Redis connection pool."""
    global redis_pool
    settings = get_settings()
    
    logger.info("Connecting to Redis", url=settings.redis_url)
    redis_pool = aioredis.from_url(
        settings.redis_url, 
        encoding="utf-8", 
        decode_responses=True
    )
    
    # Test connection
    await redis_pool.ping()
    logger.info("Redis connected")


async def close_redis_connection():
    """Close the Redis connection pool."""
    global redis_pool
    if redis_pool:
        await redis_pool.aclose()
        redis_pool = None
        logger.info("Redis connection closed")


def get_redis() -> aioredis.Redis:
    """Get the Redis client."""
    if redis_pool is None:
        raise RuntimeError("Redis not initialized")
    return redis_pool


@asynccontextmanager
async def redis_lock(lock_name: str, timeout: int = 60, blocking: bool = True) -> AsyncGenerator[bool, None]:
    """
    Distributed lock context manager using Redis.
    Guarantees mutual exclusion for critical sections across workers.
    
    Args:
        lock_name: Unique key for the lock (e.g. 'sync:{user_id}')
        timeout: How long to hold the lock before auto-release (seconds)
        blocking: If False, raises immediately if lock is unavailable.
                  If True, waits to acquire it.
    """
    redis = get_redis()
    lock = redis.lock(name=f"lock:{lock_name}", timeout=timeout, blocking=blocking)
    
    acquired = False
    try:
        acquired = await lock.acquire()
        if not acquired:
            if not blocking:
                raise TimeoutError(f"Could not acquire lock: {lock_name}")
            else:
                # In blocking=True, acquire() normally waits until it gets it, 
                # but if we get here and it's False, something failed.
                raise TimeoutError(f"Failed to acquire blocking lock: {lock_name}")
                
        yield True
    finally:
        if acquired:
            try:
                await lock.release()
            except Exception as e:
                # Ignoring release errors (e.g. lock expired on its own)
                logger.debug("Lock release suppressed", lock=lock_name, error=str(e))
