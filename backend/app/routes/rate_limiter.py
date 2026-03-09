"""
Nexus Mail — Rate Limiter
Redis-backed sliding window rate limiter for API endpoints.
"""

import time
from fastapi import HTTPException, status, Request
from app.core.redis_client import get_redis
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """
    Redis-backed sliding window rate limiter.
    To be used as a FastAPI dependency.
    """
    def __init__(self, requests: int = 60, window_seconds: int = 60, key_prefix: str = "rate"):
        self.max_requests = requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
        
    async def __call__(self, request: Request):
        """
        FastAPI dependency implementation.
        Extracts user_id from token (if available) or IP address.
        """
        # Try to identify the user
        identity = request.client.host if request.client else "unknown"
        
        # If the request goes through the auth middleware, request.state.user might exist
        if hasattr(request, "state") and getattr(request.state, "user_id", None):
            identity = f"user:{request.state.user_id}"
            
        return await self.check_rate_limit(identity)
        
    async def check_rate_limit(self, identity: str) -> bool:
        """
        Implement the sliding window logic using Redis sorted sets.
        """
        redis = get_redis()
        current_time = int(time.time() * 1000)  # ms
        window_start = current_time - (self.window_seconds * 1000)
        
        key = f"{self.key_prefix}:{identity}"
        
        # Redis transactional pipeline
        async with redis.pipeline(transaction=True) as pipe:
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count remaining entries inside the window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiry on the set to clean up inactive users
            pipe.expire(key, self.window_seconds)
            
            # Execute pipeline
            results = await pipe.execute()
            
        # results[1] is the output of zcard
        request_count = results[1]
        
        if request_count >= self.max_requests:
            logger.warning("Rate limit exceeded", identity=identity, limit=self.max_requests)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_seconds} seconds."
            )
            
        return True

# Pre-defined rate limiters to use as dependencies
standard_limiter = RateLimiter(requests=60, window_seconds=60, key_prefix="rate:std")
ai_limiter = RateLimiter(requests=10, window_seconds=60, key_prefix="rate:ai")
