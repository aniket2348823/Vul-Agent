"""
Rate Limiting Utility for API Endpoints
Prevents abuse and DoS attacks with configurable limits per endpoint.
"""
import time
from collections import defaultdict
from typing import Dict, Tuple
import asyncio
from functools import wraps
from fastapi import HTTPException, Request
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with per-IP tracking.
    Thread-safe for async operations.
    """
    
    def __init__(self):
        # Structure: {ip: {endpoint: (tokens, last_refill_time)}}
        self._buckets: Dict[str, Dict[str, Tuple[float, float]]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        
        # Default limits (requests per minute)
        self._limits = {
            "default": 60,  # 60 req/min for most endpoints
            "/api/dashboard/stats": 120,  # Higher for dashboard polling
            "/api/reports/pdf": 10,  # Lower for expensive operations
            "/api/reports/consolidated": 5,  # Very expensive
            "/api/attack/fire": 30,  # Moderate for attack endpoints
            "/api/recon": 60,
            "/api/ai": 20,  # AI endpoints are expensive
        }
    
    def configure_limit(self, endpoint_pattern: str, requests_per_minute: int):
        """Configure custom rate limit for an endpoint pattern."""
        self._limits[endpoint_pattern] = requests_per_minute
        logger.info(f"Rate limit configured: {endpoint_pattern} = {requests_per_minute} req/min")
    
    def _get_limit(self, endpoint: str) -> int:
        """Get the rate limit for an endpoint (matches patterns)."""
        # Try exact match first
        if endpoint in self._limits:
            return self._limits[endpoint]
        
        # Try pattern matching
        for pattern, limit in self._limits.items():
            if pattern != "default" and endpoint.startswith(pattern):
                return limit
        
        return self._limits["default"]
    
    async def check_rate_limit(self, client_ip: str, endpoint: str) -> bool:
        """
        Check if request is within rate limit.
        Returns True if allowed, raises HTTPException if rate limited.
        """
        async with self._lock:
            limit = self._get_limit(endpoint)
            refill_rate = limit / 60.0  # tokens per second
            capacity = limit  # max tokens
            
            current_time = time.time()
            
            # Get or initialize bucket for this IP+endpoint
            if endpoint not in self._buckets[client_ip]:
                self._buckets[client_ip][endpoint] = (capacity, current_time)
            
            tokens, last_refill = self._buckets[client_ip][endpoint]
            
            # Refill tokens based on time elapsed
            time_elapsed = current_time - last_refill
            tokens = min(capacity, tokens + time_elapsed * refill_rate)
            
            # Check if we have tokens available
            if tokens >= 1.0:
                # Consume one token
                tokens -= 1.0
                self._buckets[client_ip][endpoint] = (tokens, current_time)
                return True
            else:
                # Rate limited
                retry_after = int((1.0 - tokens) / refill_rate) + 1
                logger.warning(
                    f"Rate limit exceeded: {client_ip} on {endpoint} "
                    f"(limit: {limit} req/min)"
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )
    
    async def cleanup_old_buckets(self, max_age_seconds: int = 3600):
        """Remove buckets for IPs that haven't made requests recently."""
        async with self._lock:
            current_time = time.time()
            ips_to_remove = []
            
            for ip, endpoints in self._buckets.items():
                endpoints_to_remove = []
                for endpoint, (tokens, last_refill) in endpoints.items():
                    if current_time - last_refill > max_age_seconds:
                        endpoints_to_remove.append(endpoint)
                
                for endpoint in endpoints_to_remove:
                    del endpoints[endpoint]
                
                if not endpoints:
                    ips_to_remove.append(ip)
            
            for ip in ips_to_remove:
                del self._buckets[ip]
            
            if ips_to_remove:
                logger.info(f"Cleaned up {len(ips_to_remove)} stale rate limit buckets")


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(endpoint_override: str = None):
    """
    Decorator for FastAPI endpoints to apply rate limiting.
    
    Usage:
        @router.get("/expensive")
        @rate_limit()
        async def expensive_endpoint(request: Request):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get('request')
            
            if request:
                # Get client IP
                client_ip = request.client.host if request.client else "unknown"
                
                # Use override endpoint or actual path
                endpoint = endpoint_override or request.url.path
                
                # Check rate limit
                await rate_limiter.check_rate_limit(client_ip, endpoint)
            
            # Call original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def start_cleanup_task():
    """Background task to periodically clean up old rate limit buckets."""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            await rate_limiter.cleanup_old_buckets()
        except Exception as e:
            logger.error(f"Rate limiter cleanup error: {e}")
