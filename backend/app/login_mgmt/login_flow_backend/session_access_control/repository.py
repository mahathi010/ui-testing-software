"""Data access layer for session access control. Repositories only flush, never commit."""

import uuid
from typing import Optional

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SessionAccessRecord, SessionProtectedResource

_RESOURCE_SORT_FIELDS = {
    "created_at", "updated_at", "resource_name", "resource_path", "protection_level", "is_active",
}
_RECORD_SORT_FIELDS = {
    "created_at", "updated_at", "session_status", "outcome", "action_type",
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

    # ─── Protected Resources ──────────────────────────────────────────────────

    async def create_resource(self, data: dict) -> SessionProtectedResource:
        obj = SessionProtectedResource(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_resource(self, resource_id: uuid.UUID) -> Optional[SessionProtectedResource]:
        result = await self.db.execute(
            select(SessionProtectedResource).where(
                SessionProtectedResource.id == resource_id
            )
        )
        return result.scalar_one_or_none()

    async def get_resource_by_path(self, resource_path: str) -> Optional[SessionProtectedResource]:
        result = await self.db.execute(
            select(SessionProtectedResource).where(
                SessionProtectedResource.resource_path == resource_path,
                SessionProtectedResource.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_resources(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        filters: Optional[dict] = None,
    ) -> tuple[list[SessionProtectedResource], int]:
        query = select(SessionProtectedResource)
        count_query = select(func.count()).select_from(SessionProtectedResource)

        if filters:
            if "is_active" in filters:
                query = query.where(SessionProtectedResource.is_active == filters["is_active"])
                count_query = count_query.where(SessionProtectedResource.is_active == filters["is_active"])
            if "protection_level" in filters:
                query = query.where(SessionProtectedResource.protection_level == filters["protection_level"])
                count_query = count_query.where(SessionProtectedResource.protection_level == filters["protection_level"])
            if "resource_name" in filters:
                query = query.where(SessionProtectedResource.resource_name.ilike(f"%{filters['resource_name']}%"))
                count_query = count_query.where(SessionProtectedResource.resource_name.ilike(f"%{filters['resource_name']}%"))

        if sort_by not in _RESOURCE_SORT_FIELDS:
            sort_by = "created_at"

        query = _apply_sort(query, SessionProtectedResource, sort_by, sort_dir)
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def update_resource(
        self, resource_id: uuid.UUID, data: dict
    ) -> Optional[SessionProtectedResource]:
        obj = await self.get_resource(resource_id)
        if obj is None:
            return None
        for key, value in data.items():
            setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_resource(self, resource_id: uuid.UUID) -> bool:
        obj = await self.get_resource(resource_id)
        if obj is None:
            return False
        await self.db.delete(obj)
        await self.db.flush()
        return True

    # ─── Access Records (append-only) ────────────────────────────────────────

    async def create_record(self, data: dict) -> SessionAccessRecord:
        obj = SessionAccessRecord(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_record(self, record_id: uuid.UUID) -> Optional[SessionAccessRecord]:
        result = await self.db.execute(
            select(SessionAccessRecord).where(
                SessionAccessRecord.id == record_id
            )
        )
        return result.scalar_one_or_none()

    async def list_records(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        filters: Optional[dict] = None,
    ) -> tuple[list[SessionAccessRecord], int]:
        query = select(SessionAccessRecord)
        count_query = select(func.count()).select_from(SessionAccessRecord)

        if filters:
            if "resource_id" in filters:
                query = query.where(SessionAccessRecord.resource_id == filters["resource_id"])
                count_query = count_query.where(SessionAccessRecord.resource_id == filters["resource_id"])
            if "session_status" in filters:
                query = query.where(SessionAccessRecord.session_status == filters["session_status"])
                count_query = count_query.where(SessionAccessRecord.session_status == filters["session_status"])
            if "outcome" in filters:
                query = query.where(SessionAccessRecord.outcome == filters["outcome"])
                count_query = count_query.where(SessionAccessRecord.outcome == filters["outcome"])

        if sort_by not in _RECORD_SORT_FIELDS:
            sort_by = "created_at"

        query = _apply_sort(query, SessionAccessRecord, sort_by, sort_dir)
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total
