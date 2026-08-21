"""Shared OpenAPI `responses=` blocks for errors raised by auth dependencies.

FastAPI only documents responses declared on the route — exceptions raised
inside a dependency are invisible to the generated schema otherwise, which
leaves generated clients with no error type for those status codes.
"""

from typing import Any

from app.schemas.envelope import ResponseEnvelope

UNAUTHORIZED_RESPONSE: dict[int | str, dict[str, Any]] = {
    401: {
        "model": ResponseEnvelope[None, None],
        "description": "Missing or invalid bearer token",
    },
}
