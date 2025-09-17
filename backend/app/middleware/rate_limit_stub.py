from __future__ import annotations
from typing import Callable
from fastapi import Request

class RateLimitStubMiddleware:
    """No-op rate limit stub for M0.

    Logs enabled state at startup; does not enforce limits.
    """

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            # Could emit lightweight headers or noop markers here
            pass
        await self.app(scope, receive, send)
