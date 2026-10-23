"""Simple process-local sliding-window rate limiter."""

import asyncio
import hashlib
import time

from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class InMemoryRateLimiter:
    """Sliding-window limiter for one Python process."""

    def __init__(
        self,
        limit: int,
        window_seconds: float,
    ):
        if limit <= 0:
            raise ValueError(
                "Rate-limit count must be greater than zero."
            )

        if window_seconds <= 0:
            raise ValueError(
                "Rate-limit window must be greater than zero."
            )

        self.limit = limit
        self.window_seconds = window_seconds

        self._events: dict[str, deque[float]] = defaultdict(
            deque
        )

        self._lock = asyncio.Lock()

    async def check(
        self,
        key: str,
    ) -> RateLimitResult:
        now = time.monotonic()
        window_start = now - self.window_seconds

        async with self._lock:
            events = self._events[key]

            while events and events[0] <= window_start:
                events.popleft()

            if len(events) >= self.limit:
                retry_after = max(
                    1,
                    round(
                        self.window_seconds
                        - (now - events[0])
                    ),
                )

                return RateLimitResult(
                    allowed=False,
                    limit=self.limit,
                    remaining=0,
                    retry_after_seconds=retry_after,
                )

            events.append(now)

            return RateLimitResult(
                allowed=True,
                limit=self.limit,
                remaining=self.limit - len(events),
                retry_after_seconds=0,
            )


def caller_key(scope: dict) -> str:
    """Build a non-secret rate-limit key."""

    headers = {
        key.lower(): value
        for key, value in scope.get(
            "headers",
            [],
        )
    }

    authorization = headers.get(
        b"authorization"
    )

    if authorization:
        token_hash = hashlib.sha256(
            authorization
        ).hexdigest()

        return f"authorization:{token_hash}"

    client = scope.get("client")

    if client:
        return f"ip:{client[0]}"

    return "ip:unknown"