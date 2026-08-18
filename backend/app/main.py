"""Create and configure the FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from app.api.handlers import register_exception_handlers
from app.api.middleware import RequestBodyLimitMiddleware, RequestLoggingMiddleware
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.queue import get_extraction_queue
from app.queueing import reconcile

# Set up CORS
cors_list = [
    origin.strip()
    for origin in get_settings().CORS_ORIGINS.split(",")
    if origin.strip()
]
log_exclude_paths = [
    path.strip() for path in get_settings().LOG_EXCLUDE_PATHS.split(",") if path.strip()
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Lifespan function Replaces the previous startup/shutdown functions"""
    configure_logging(get_settings().LOG_LEVEL)

    # Seed the self-rescheduling reconcile chain on every start. Safe per
    # replica because the tick id is a shared UTC epoch bucket.
    await run_in_threadpool(reconcile.schedule_next, get_extraction_queue())

    yield


app = FastAPI(
    title=get_settings().API_TITLE,
    root_path=get_settings().API_ROOT,
    lifespan=lifespan,
)

# Register the API routes
app.include_router(api_router)

# Convert domain errors and HTTP exceptions into the shared response envelope
register_exception_handlers(app)

# Register CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Allow a bounded multipart envelope beyond the file-size limit.
# This guard runs before FastAPI constructs and spools an UploadFile.
app.add_middleware(
    RequestBodyLimitMiddleware,
    max_body_bytes=get_settings().UPLOAD_MAX_BYTES + 64 * 1024,
    paths={"/invoices"},
)
app.add_middleware(
    RequestBodyLimitMiddleware,
    max_body_bytes=get_settings().POLICY_DOCUMENT_MAX_BYTES + 64 * 1024,
    paths={"/policies/documents"},
)

# Add logging middleware last so it wraps CORS responses, including preflights
app.add_middleware(RequestLoggingMiddleware, exclude_paths=log_exclude_paths)
