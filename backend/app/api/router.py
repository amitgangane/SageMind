from fastapi import APIRouter

from app.api.routes import documents, chat

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(documents.router)
api_router.include_router(chat.router)
