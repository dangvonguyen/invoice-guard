"""Include all the other routes into one router."""

from fastapi import APIRouter

from app.api.routers import auth, health, invoices, policies, review_queue, users

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(invoices.router)
api_router.include_router(review_queue.router)
api_router.include_router(policies.router)
api_router.include_router(health.router)
