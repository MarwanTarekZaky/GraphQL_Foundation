"""GraphQL-over-HTTP rules that Strawberry doesn't apply by default."""

from starlette.requests import Request
from strawberry.fastapi import GraphQLRouter


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
