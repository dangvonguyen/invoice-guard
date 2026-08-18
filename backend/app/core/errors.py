"""Domain exception hierarchy — no HTTP awareness, so services stay transport-agnostic."""

from app.schemas.envelope import ErrorDetail


class DomainError(Exception):
    """Base for all business-logic errors. Subclass, don't raise this directly."""

    code: str = "DOMAIN_ERROR"
    status_code: int = 400

    def __init__(self, message: str, details: list[ErrorDetail] | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(DomainError):
    code = "NOT_FOUND"
    status_code = 404


class ForbiddenError(DomainError):
    code = "FORBIDDEN"
    status_code = 403


class ValidationError(DomainError):
    code = "VALIDATION_ERROR"
    status_code = 422
