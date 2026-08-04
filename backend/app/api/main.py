"""Include all the other routes into one router."""

from fastapi import APIRouter

from app.api.routers import auth, health

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(health.router)
