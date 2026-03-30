"""Data access layer for credential validation. Repositories only flush, never commit."""

import uuid
from typing import Any, Optional

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CredentialValidationDefinition, CredentialValidationExecution

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


class CredentialValidationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── Definitions ─────────────────────────────────────────────────────────

    async def create_definition(self, data: dict) -> CredentialValidationDefinition:
        obj = CredentialValidationDefinition(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_definition(self, definition_id: uuid.UUID) -> Optional[CredentialValidationDefinition]:
        result = await self.db.execute(
            select(CredentialValidationDefinition).where(
                CredentialValidationDefinition.id == definition_id
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
    ) -> tuple[list[CredentialValidationDefinition], int]:
        query = select(CredentialValidationDefinition)
        count_query = select(func.count()).select_from(CredentialValidationDefinition)

        if filters:
            if "is_active" in filters:
                query = query.where(CredentialValidationDefinition.is_active == filters["is_active"])
                count_query = count_query.where(CredentialValidationDefinition.is_active == filters["is_active"])
            if "name" in filters:
                query = query.where(CredentialValidationDefinition.name.ilike(f"%{filters['name']}%"))
                count_query = count_query.where(CredentialValidationDefinition.name.ilike(f"%{filters['name']}%"))

        if sort_by not in _DEFINITION_SORT_FIELDS:
            sort_by = "created_at"

        query = _apply_sort(query, CredentialValidationDefinition, sort_by, sort_dir)
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def update_definition(
        self, definition_id: uuid.UUID, data: dict
    ) -> Optional[CredentialValidationDefinition]:
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

    async def create_execution(self, data: dict) -> CredentialValidationExecution:
        obj = CredentialValidationExecution(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_execution(self, execution_id: uuid.UUID) -> Optional[CredentialValidationExecution]:
        result = await self.db.execute(
            select(CredentialValidationExecution).where(
                CredentialValidationExecution.id == execution_id
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
    ) -> tuple[list[CredentialValidationExecution], int]:
        query = select(CredentialValidationExecution)
        count_query = select(func.count()).select_from(CredentialValidationExecution)

        if filters:
            if "definition_id" in filters:
                query = query.where(CredentialValidationExecution.definition_id == filters["definition_id"])
                count_query = count_query.where(CredentialValidationExecution.definition_id == filters["definition_id"])
            if "status" in filters:
                query = query.where(CredentialValidationExecution.status == filters["status"])
                count_query = count_query.where(CredentialValidationExecution.status == filters["status"])

        if sort_by not in _EXECUTION_SORT_FIELDS:
            sort_by = "created_at"

        query = _apply_sort(query, CredentialValidationExecution, sort_by, sort_dir)
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def update_execution(
        self, execution_id: uuid.UUID, data: dict
    ) -> Optional[CredentialValidationExecution]:
        obj = await self.get_execution(execution_id)
        if obj is None:
            return None
        for key, value in data.items():
            setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj
