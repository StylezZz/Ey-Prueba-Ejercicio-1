from fastapi import HTTPException, status, Request
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List
import asyncio


class RateLimiter:
    def __init__(self, max_requests: int = 20, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        # Store request timestamps per API key
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, api_key: str) -> bool:
        async with self._lock:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(seconds=self.time_window)

            # Get request history for this API key
            request_history = self.requests[api_key]

            # Remove old requests outside the time window
            request_history[:] = [
                timestamp for timestamp in request_history
                if timestamp > cutoff_time
            ]

            # Check if rate limit is exceeded
            if len(request_history) >= self.max_requests:
                # Calculate when the rate limit will reset
                oldest_request = min(request_history)
                reset_time = oldest_request + timedelta(seconds=self.time_window)
                wait_seconds = (reset_time - current_time).total_seconds()

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": f"Maximum {self.max_requests} requests per {self.time_window} seconds allowed",
                        "retry_after": int(wait_seconds) + 1,
                        "current_usage": len(request_history),
                        "limit": self.max_requests
                    },
                    headers={
                        "X-RateLimit-Limit": str(self.max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(reset_time.timestamp())),
                        "Retry-After": str(int(wait_seconds) + 1)
                    }
                )
            request_history.append(current_time)
            self.requests[api_key] = request_history

            return True

    def get_rate_limit_info(self, api_key: str) -> dict:
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(seconds=self.time_window)
        request_history = self.requests.get(api_key, [])
        active_requests = [
            timestamp for timestamp in request_history
            if timestamp > cutoff_time
        ]

        remaining = max(0, self.max_requests - len(active_requests))

        if active_requests:
            oldest_request = min(active_requests)
            reset_time = oldest_request + timedelta(seconds=self.time_window)
        else:
            reset_time = current_time + timedelta(seconds=self.time_window)

        return {
            "limit": self.max_requests,
            "remaining": remaining,
            "reset": int(reset_time.timestamp()),
            "used": len(active_requests),
            "window_seconds": self.time_window
        }

    async def clear_api_key(self, api_key: str):
        async with self._lock:
            if api_key in self.requests:
                del self.requests[api_key]

    async def clear_all(self):
        async with self._lock:
            self.requests.clear()


# Limitar a 20 requests por minuto, para evitar sobrecarga y/o bloqueos
rate_limiter = RateLimiter(max_requests=20, time_window=60)


async def check_rate_limit(request: Request, api_key: str) -> None:
    await rate_limiter.check_rate_limit(api_key)
    rate_info = rate_limiter.get_rate_limit_info(api_key)
    request.state.rate_limit = rate_info
