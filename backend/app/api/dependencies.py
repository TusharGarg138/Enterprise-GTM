"""FastAPI dependency injection helpers."""
from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.services.gemini_service import GeminiService, get_gemini_service


async def get_database(session: AsyncSession = Depends(get_db)) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for route handlers."""
    yield session


def get_ai_service() -> GeminiService:
    """Provide the Gemini service singleton."""
    return get_gemini_service()


class PaginationParams:
    """Reusable pagination dependency."""
    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
