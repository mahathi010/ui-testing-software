"""FastAPI shared dependencies."""

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

__all__ = ["get_db", "DBSession"]

# Type alias for dependency injection
DBSession = Depends(get_db)
