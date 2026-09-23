"""
Centralized API router aggregating sub-routes under /api/v1.
"""

from fastapi import APIRouter
from backend.api.routes import auth, chat, documents, feedback, admin

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(documents.router)
api_router.include_router(feedback.router)
api_router.include_router(admin.router)
