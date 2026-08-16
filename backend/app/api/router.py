"""Include all the other routes into one router."""

from fastapi import APIRouter

from app.api.routers import auth, health, invoice, policies, user

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(user.router)
api_router.include_router(invoice.router)
api_router.include_router(policies.router)
api_router.include_router(health.router)
