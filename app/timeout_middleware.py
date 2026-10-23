"""Timeout protection for ordinary GraphQL HTTP operations."""

import asyncio
import json

from collections.abc import Awaitable, Callable
from typing import Any


ASGIApp = Callable[
    [
        dict[str, Any],
        Callable[[], Awaitable[dict[str, Any]]],
        Callable[[dict[str, Any]], Awaitable[None]],
    ],
    Awaitable[None],
]


class GraphQLTimeoutMiddleware:
    """Apply a timeout to GraphQL HTTP POST requests.

    WebSocket subscriptions are intentionally excluded because they are
    long-lived operations.

    Upload endpoints are also excluded because they need separate upload
    timing and size controls.
    """

    def __init__(
        self,
        app: ASGIApp,
        timeout_seconds: float,
    ):
        self.app = app
        self.timeout_seconds = timeout_seconds

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[
            [],
            Awaitable[dict[str, Any]],
        ],
        send: Callable[
            [dict[str, Any]],
            Awaitable[None],
        ],
    ) -> None:
        request_type = scope.get("type")
        path = scope.get("path")
        method = scope.get("method")

        should_apply_timeout = (
            request_type == "http"
            and path == "/graphql"
            and method == "POST"
        )

        if not should_apply_timeout:
            await self.app(
                scope,
                receive,
                send,
            )
            return

        response_started = False

        async def tracked_send(
            message: dict[str, Any],
        ) -> None:
            nonlocal response_started

            if message["type"] == "http.response.start":
                response_started = True

            await send(message)

        try:
            await asyncio.wait_for(
                self.app(
                    scope,
                    receive,
                    tracked_send,
                ),
                timeout=self.timeout_seconds,
            )
        except TimeoutError:
            # Once response headers have started, sending a new 504 response
            # is no longer valid. This should not normally happen for the
            # non-streaming GraphQL JSON responses protected here.
            if response_started:
                return

            body = json.dumps({
                "errors": [
                    {
                        "message": (
                            "GraphQL request timed out."
                        ),
                        "extensions": {
                            "code": (
                                "GRAPHQL_REQUEST_TIMEOUT"
                            ),
                        },
                    }
                ]
            }).encode("utf-8")

            await send({
                "type": "http.response.start",
                "status": 504,
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