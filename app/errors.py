"""Domain errors raised by the business logic layer. No GraphQL here."""

from enum import Enum


class ErrorCode(Enum):
    STARS_OUT_OF_RANGE = "STARS_OUT_OF_RANGE"
    NICKNAME_EMPTY = "NICKNAME_EMPTY"
    REVIEW_NOT_FOUND = "REVIEW_NOT_FOUND"
    UPLOAD_NOT_FOUND = "UPLOAD_NOT_FOUND"
    UPLOAD_NOT_RECEIVED = "UPLOAD_NOT_RECEIVED"
    INVALID_IMAGE_TYPE = "INVALID_IMAGE_TYPE"
    INVALID_PAGE_SIZE = "INVALID_PAGE_SIZE"
    INVALID_CURSOR = "INVALID_CURSOR"


class AuthenticationError(Exception):
    pass


class ValidationError(Exception):
    """An expected failure: the request broke a business rule."""

    def __init__(
        self,
        message: str,
        code: ErrorCode,
        field: list[str] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.field = field
