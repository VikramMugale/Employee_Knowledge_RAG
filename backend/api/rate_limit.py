"""
In-memory fixed-window rate limiter. Redis is not used.
"""

import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from backend.config.settings import settings


class InMemoryRateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, limit: Optional[int] = None):
        super().__init__(app)
        self.limit = limit or settings.rate_limit_per_minute
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/live", "/ready", "/docs", "/redoc", "/openapi.json"}:
            return await call_next(request)
        key = request.client.host if request.client else "unknown"
        now = time.time()
        window = self._hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.limit:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        window.append(now)
        return await call_next(request)
