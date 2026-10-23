"""GraphQL-over-HTTP rules that Strawberry doesn't apply by default."""

from starlette.requests import Request
from strawberry.fastapi import GraphQLRouter


def set_cache_headers(request: Request, result) -> None:
    headers = request.state.sub_response.headers

    # Only anonymous, successful GET queries may be stored by browsers and CDNs.
    # Every anonymous viewer gets the same answer, so sharing it is safe.
    is_shareable = (
        request.method == "GET"
        and "authorization" not in request.headers
        and not result.errors
    )

    if is_shareable:
        headers["Cache-Control"] = "public, max-age=60"
    else:
        headers["Cache-Control"] = "no-store"

    # The same URL can return different data for different tokens.
    headers["Vary"] = "Authorization"


class GraphQLOverHTTPRouter(GraphQLRouter):

    async def get_sub_response(self, request: Request):
        # Keep this request's response object so process_result can set its status.
        sub_response = await super().get_sub_response(request)
        request.state.sub_response = sub_response
        return sub_response

    async def process_result(self, request, result):
        response = await super().process_result(request, result)

        # Errors before execution (syntax/validation) have no path:
        # "data" must not be present, and the request was bad -> 400.
        if result.errors and all(error.path is None for error in result.errors):
            response.pop("data", None)
            request.state.sub_response.status_code = 400

        return response
