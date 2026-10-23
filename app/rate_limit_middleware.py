"""General HTTP rate limiting for the GraphQL endpoint."""

import json

from app.rate_limit import (
    InMemoryRateLimiter,
    caller_key,
)


class GraphQLRateLimitMiddleware:
    """Limit ordinary GraphQL HTTP requests.

    WebSocket subscriptions are excluded because they need connection
    and event-specific limits rather than ordinary request counting.
    """

    def __init__(
        self,
        app,
        limit: int = 60,
        window_seconds: float = 60,
    ):
        self.app = app

        self.limiter = InMemoryRateLimiter(
            limit=limit,
            window_seconds=window_seconds,
        )

    async def __call__(
        self,
        scope,
        receive,
        send,
    ):
        should_limit = (
            scope.get("type") == "http"
            and scope.get("path") == "/graphql"
        )

        if not should_limit:
            await self.app(
                scope,
                receive,
                send,
            )
            return

        result = await self.limiter.check(
            caller_key(scope)
        )

        if not result.allowed:
            body = json.dumps({
                "errors": [
                    {
                        "message": (
                            "Too many GraphQL requests."
                        ),
                        "extensions": {
                            "code": "RATE_LIMITED",
                            "retryAfterSeconds": (
                                result.retry_after_seconds
                            ),
                        },
                    }
                ]
            }).encode("utf-8")

            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (
                        b"content-type",
                        b"application/json",
                    ),
                    (
                        b"cache-control",
                        b"no-store",
                    ),
                    (
                        b"retry-after",
                        str(
                            result.retry_after_seconds
                        ).encode("ascii"),
                    ),
                    (
                        b"x-ratelimit-limit",
                        str(
                            result.limit
                        ).encode("ascii"),
                    ),
                    (
                        b"x-ratelimit-remaining",
                        b"0",
                    ),
                    (
                        b"content-length",
                        str(len(body)).encode("ascii"),
                    ),
                ],
            })

            await send({
                "type": "http.response.body",
                "body": body,
                "more_body": False,
            })

            return

        async def send_with_rate_headers(message):
            if message["type"] == "http.response.start":
                headers = list(
                    message.get(
                        "headers",
                        [],
                    )
                )

                headers.extend([
                    (
                        b"x-ratelimit-limit",
                        str(
                            result.limit
                        ).encode("ascii"),
                    ),
                    (
                        b"x-ratelimit-remaining",
                        str(
                            result.remaining
                        ).encode("ascii"),
                    ),
                ])

                message["headers"] = headers

            await send(message)

        await self.app(
            scope,
            receive,
            send_with_rate_headers,
        )