"""Safe top-level GraphQL error formatting.

Development:
- Keep detailed parsing and validation messages.
- Mask unexpected execution failures.

Production:
- Hide detailed parsing and validation suggestions.
- Mask unexpected execution failures.
- Preserve safe domain-error messages and machine-readable codes.
"""

from graphql import GraphQLError
from strawberry.extensions import SchemaExtension

from app.config import IS_PRODUCTION
from app.errors import AuthenticationError, ValidationError


def with_code(
    error: GraphQLError,
    code: str,
    message: str | None = None,
) -> GraphQLError:
    """Return a new GraphQL error with a machine-readable code."""

    return GraphQLError(
        message=message or error.message,
        nodes=error.nodes,
        source=error.source,
        positions=error.positions,
        path=error.path,
        original_error=error.original_error,
        extensions={
            **(error.extensions or {}),
            "code": code,
        },
    )


def classify(error: GraphQLError) -> GraphQLError:
    """Convert an internal GraphQL error into a client-safe error."""

    original = error.original_error

    # No original Python exception normally means that parsing,
    # validation, variable coercion, or another request-level check failed.
    if original is None:
        message = (
            "Invalid GraphQL request."
            if IS_PRODUCTION
            else error.message
        )

        return with_code(
            error,
            "GRAPHQL_VALIDATION_FAILED",
            message=message,
        )

    # Safe authentication failure.
    if isinstance(original, AuthenticationError):
        message = (
            "Authentication required."
            if IS_PRODUCTION
            else error.message
        )

        return with_code(
            error,
            "UNAUTHENTICATED",
            message=message,
        )

    # Expected business-rule failure.
    # These messages are deliberately authored for clients.
    if isinstance(original, ValidationError):
        return with_code(
            error,
            original.code.value,
            message=original.message,
        )

    # Anything else is an unexpected programming error,
    # infrastructure failure, or outage.
    # Never expose its internal details to GraphQL clients.
    return with_code(
        error,
        "INTERNAL_SERVER_ERROR",
        message="Internal server error.",
    )


class ErrorCodes(SchemaExtension):
    """Classify and sanitize GraphQL errors before serialization."""

    def on_operation(self):
        try:
            yield
        finally:
            result = self.execution_context.result

            if result is not None and result.errors:
                result.errors = [
                    classify(error)
                    for error in result.errors
                ]