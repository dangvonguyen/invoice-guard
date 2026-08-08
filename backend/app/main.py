"""Create and configure the FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings

# Set up CORS
cors_list = [
    origin.strip()
    for origin in get_settings().CORS_ORIGINS.split(",")
    if origin.strip()
]

app = FastAPI(
    title=get_settings().API_TITLE,
    root_path=get_settings().API_ROOT,
)

# Register the API routes
app.include_router(api_router)

# Register CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
