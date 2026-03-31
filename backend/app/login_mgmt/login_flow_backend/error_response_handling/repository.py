"""Data access layer for error response handling. Repositories only flush, never commit."""

import uuid
from typing import Any, Optional

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ErrorResponseDefinition, ErrorResponseExecution

_DEFINITION_SORT_FIELDS = {
    "created_at", "updated_at", "name", "is_active", "version",
}
_EXECUTION_SORT_FIELDS = {
    "created_at", "updated_at", "status", "started_at", "completed_at",
}


def _apply_sort(query, model, sort_by: str, sort_dir: str):
    direction = asc if sort_dir.lower() == "asc" else desc
    column = getattr(model, sort_by, None)
    if column is not None:
        query = query.order_by(direction(column))
    return query


class ErrorResponseDefinitionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict) -> ErrorResponseDefinition:
        obj = ErrorResponseDefinition(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def find_by_id(self, definition_id: uuid.UUID) -> Optional[ErrorResponseDefinition]:
        result = await self.db.execute(
            select(ErrorResponseDefinition).where(
                ErrorResponseDefinition.id == definition_id
            )
        )
        return result.scalar_one_or_none()

    async def find_all(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        filters: Optional[dict] = None,
    ) -> tuple[list[ErrorResponseDefinition], int]:
        query = select(ErrorResponseDefinition)
        count_query = select(func.count()).select_from(ErrorResponseDefinition)

        if filters:
            if "is_active" in filters:
                query = query.where(ErrorResponseDefinition.is_active == filters["is_active"])
                count_query = count_query.where(ErrorResponseDefinition.is_active == filters["is_active"])
            if "name" in filters:
                query = query.where(ErrorResponseDefinition.name.ilike(f"%{filters['name']}%"))
                count_query = count_query.where(ErrorResponseDefinition.name.ilike(f"%{filters['name']}%"))

        if sort_by not in _DEFINITION_SORT_FIELDS:
            sort_by = "created_at"

        query = _apply_sort(query, ErrorResponseDefinition, sort_by, sort_dir)
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def update(
        self, definition_id: uuid.UUID, data: dict
    ) -> Optional[ErrorResponseDefinition]:
        obj = await self.find_by_id(definition_id)
        if obj is None:
            return None
        for key, value in data.items():
            setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, definition_id: uuid.UUID) -> bool:
        obj = await self.find_by_id(definition_id)
        if obj is None:
            return False
        await self.db.delete(obj)
        await self.db.flush()
        return True


class ErrorResponseExecutionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict) -> ErrorResponseExecution:
        obj = ErrorResponseExecution(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def find_by_id(self, execution_id: uuid.UUID) -> Optional[ErrorResponseExecution]:
        result = await self.db.execute(
            select(ErrorResponseExecution).where(
                ErrorResponseExecution.id == execution_id
            )
        )
        return result.scalar_one_or_none()

    async def find_all(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        filters: Optional[dict] = None,
    ) -> tuple[list[ErrorResponseExecution], int]:
        query = select(ErrorResponseExecution)
        count_query = select(func.count()).select_from(ErrorResponseExecution)

        if filters:
            if "definition_id" in filters:
                query = query.where(ErrorResponseExecution.definition_id == filters["definition_id"])
                count_query = count_query.where(ErrorResponseExecution.definition_id == filters["definition_id"])
            if "status" in filters:
                query = query.where(ErrorResponseExecution.status == filters["status"])
                count_query = count_query.where(ErrorResponseExecution.status == filters["status"])

        if sort_by not in _EXECUTION_SORT_FIELDS:
            sort_by = "created_at"

        query = _apply_sort(query, ErrorResponseExecution, sort_by, sort_dir)
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def update(
        self, execution_id: uuid.UUID, data: dict
    ) -> Optional[ErrorResponseExecution]:
        obj = await self.find_by_id(execution_id)
        if obj is None:
            return None
        for key, value in data.items():
            setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj
