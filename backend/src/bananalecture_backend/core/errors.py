# ruff: noqa: D107

from fastapi import status


class BananalectureError(Exception):
    """Base application error with HTTP semantics."""

    def __init__(self, message: str, status_code: int) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(BananalectureError):
    """Raised when a resource does not exist."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND)


class BadRequestError(BananalectureError):
    """Raised when a request violates business rules."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class ConfigurationError(BananalectureError):
    """Raised when server-side configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExternalServiceError(BananalectureError):
    """Raised when an upstream service cannot fulfill the request."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=status.HTTP_502_BAD_GATEWAY)
