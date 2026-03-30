"""Data access layer for session access control. Repositories only flush, never commit."""

import uuid
from typing import Any, Optional

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SessionAccessControlDefinition, SessionAccessControlExecution

_DEFINITION_SORT_FIELDS = {
    "created_at", "updated_at", "name", "is_active", "version",
}
_EXECUTION_SORT_FIELDS = {
    "created_at", "updated_at", "status", "started_at", "completed_at", "session_state",
}


def _apply_sort(query, model, sort_by: str, sort_dir: str):
    direction = asc if sort_dir.lower() == "asc" else desc
    column = getattr(model, sort_by, None)
    if column is not None:
        query = query.order_by(direction(column))
    return query


class SessionAccessControlRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── Definitions ─────────────────────────────────────────────────────────

    async def create_definition(self, data: dict) -> SessionAccessControlDefinition:
        obj = SessionAccessControlDefinition(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_definition(self, definition_id: uuid.UUID) -> Optional[SessionAccessControlDefinition]:
        result = await self.db.execute(
            select(SessionAccessControlDefinition).where(
                SessionAccessControlDefinition.id == definition_id
            )
        )
        return result.scalar_one_or_none()

    async def list_definitions(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        filters: Optional[dict] = None,
    ) -> tuple[list[SessionAccessControlDefinition], int]:
        query = select(SessionAccessControlDefinition)
        count_query = select(func.count()).select_from(SessionAccessControlDefinition)

        if filters:
            if "is_active" in filters:
                query = query.where(SessionAccessControlDefinition.is_active == filters["is_active"])
                count_query = count_query.where(SessionAccessControlDefinition.is_active == filters["is_active"])
            if "name" in filters:
                query = query.where(SessionAccessControlDefinition.name.ilike(f"%{filters['name']}%"))
                count_query = count_query.where(SessionAccessControlDefinition.name.ilike(f"%{filters['name']}%"))

        if sort_by not in _DEFINITION_SORT_FIELDS:
            sort_by = "created_at"

        query = _apply_sort(query, SessionAccessControlDefinition, sort_by, sort_dir)
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def update_definition(
        self, definition_id: uuid.UUID, data: dict
    ) -> Optional[SessionAccessControlDefinition]:
        obj = await self.get_definition(definition_id)
        if obj is None:
            return None
        for key, value in data.items():
            setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_definition(self, definition_id: uuid.UUID) -> bool:
        obj = await self.get_definition(definition_id)
        if obj is None:
            return False
        await self.db.delete(obj)
        await self.db.flush()
        return True

    # ─── Executions ──────────────────────────────────────────────────────────

    async def create_execution(self, data: dict) -> SessionAccessControlExecution:
        obj = SessionAccessControlExecution(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_execution(self, execution_id: uuid.UUID) -> Optional[SessionAccessControlExecution]:
        result = await self.db.execute(
            select(SessionAccessControlExecution).where(
                SessionAccessControlExecution.id == execution_id
            )
        )
        return result.scalar_one_or_none()

    async def list_executions(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        filters: Optional[dict] = None,
    ) -> tuple[list[SessionAccessControlExecution], int]:
        query = select(SessionAccessControlExecution)
        count_query = select(func.count()).select_from(SessionAccessControlExecution)

        if filters:
            if "definition_id" in filters:
                query = query.where(SessionAccessControlExecution.definition_id == filters["definition_id"])
                count_query = count_query.where(SessionAccessControlExecution.definition_id == filters["definition_id"])
            if "status" in filters:
                query = query.where(SessionAccessControlExecution.status == filters["status"])
                count_query = count_query.where(SessionAccessControlExecution.status == filters["status"])
            if "session_state" in filters:
                query = query.where(SessionAccessControlExecution.session_state == filters["session_state"])
                count_query = count_query.where(SessionAccessControlExecution.session_state == filters["session_state"])

        if sort_by not in _EXECUTION_SORT_FIELDS:
            sort_by = "created_at"

        query = _apply_sort(query, SessionAccessControlExecution, sort_by, sort_dir)
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def update_execution(
        self, execution_id: uuid.UUID, data: dict
    ) -> Optional[SessionAccessControlExecution]:
        obj = await self.get_execution(execution_id)
        if obj is None:
            return None
        for key, value in data.items():
            setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj
