"""Exception handlers for returning API errors in a consistent response envelope."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import DomainError
from app.schemas.envelope import ErrorDetail, ErrorInfo, ResponseEnvelope

logger = logging.getLogger(__name__)


def envelope_response(status_code: int, error: ErrorInfo) -> JSONResponse:
    """Create a JSON response containing the given error in the shared envelope."""
    envelope: ResponseEnvelope[None] = ResponseEnvelope(error=error)
    return JSONResponse(
        status_code=status_code, content=envelope.model_dump(mode="json")
    )


async def domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Handle domain errors and convert them to the standard error envelope."""
    assert isinstance(exc, DomainError)

    return envelope_response(
        exc.status_code,
        ErrorInfo(code=exc.code, message=exc.message, details=exc.details),
    )


async def validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Handle request validation errors and return structured field details."""
    assert isinstance(exc, RequestValidationError)

    details = [
        ErrorDetail(
            field=".".join(str(loc) for loc in err["loc"] if loc != "body"),
            code=err["type"].upper(),
            message=err["msg"],
        )
        for err in exc.errors()
    ]
    return envelope_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        ErrorInfo(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details=details,
        ),
    )


_STATUS_TO_CODE = {
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
}


async def http_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Handle HTTP exceptions and map their status codes to API error codes."""
    assert isinstance(exc, StarletteHTTPException)

    code = _STATUS_TO_CODE.get(exc.status_code, "HTTP_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "HTTP error"

    return envelope_response(
        exc.status_code,
        ErrorInfo(code=code, message=message, details=None),
    )


async def unhandled_exception_handler(request: Request, _: Exception) -> JSONResponse:
    """Handle unexpected exceptions, log them, and return a generic 500 error."""
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        extra={
            "event": "http.request.error",
            "context": {
                "http_method": request.method,
                "http_path": request.url.path,
            },
        },
    )

    return envelope_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorInfo(
            code="INTERNAL_SERVER_ERROR",
            message="An internal error occurred",
            details=None,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all application exception handlers with the FastAPI app."""
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
