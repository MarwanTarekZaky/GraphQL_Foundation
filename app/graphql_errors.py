"""Top-level GraphQL errors: give every error a machine-readable code,
and never leak the details of unexpected failures to clients."""

from graphql import GraphQLError
from strawberry.extensions import SchemaExtension

from app.errors import AuthenticationError, ValidationError


def with_code(
    error: GraphQLError,
    code: str,
    message: str | None = None,
) -> GraphQLError:
    return GraphQLError(
        message=message or error.message,
        nodes=error.nodes,
        source=error.source,
        positions=error.positions,
        path=error.path,
        original_error=error.original_error,
        extensions={**(error.extensions or {}), "code": code},
    )


def classify(error: GraphQLError) -> GraphQLError:
    original = error.original_error

    # No original exception: the document itself was invalid (syntax/validation).
    if original is None:
        return with_code(error, "GRAPHQL_VALIDATION_FAILED")

    if isinstance(original, AuthenticationError):
        return with_code(error, "UNAUTHENTICATED")

    if isinstance(original, ValidationError):
        return with_code(error, original.code.value)

    # Anything else is a bug or an outage: hide internals from the client.
    # The full traceback is still logged on the server.
    return with_code(error, "INTERNAL_SERVER_ERROR", message="Internal server error.")


class ErrorCodes(SchemaExtension):

    def on_operation(self):
        yield

        result = self.execution_context.result

        if result is not None and result.errors:
            result.errors = [classify(error) for error in result.errors]
