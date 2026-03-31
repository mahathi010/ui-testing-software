"""SQLAlchemy ORM models for session access control."""

import enum
import uuid

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProtectionLevel(str, enum.Enum):
    public = "public"
    authenticated = "authenticated"
    elevated = "elevated"


class SessionStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    invalid = "invalid"
    anonymous = "anonymous"


class ActionType(str, enum.Enum):
    page_view = "page_view"
    guarded_action = "guarded_action"
    navigation = "navigation"
    media_access = "media_access"


class AccessOutcome(str, enum.Enum):
    allowed = "allowed"
    denied_guest = "denied_guest"
    denied_expired = "denied_expired"
    denied_invalid = "denied_invalid"
    denied_forbidden = "denied_forbidden"
    redirected = "redirected"
    error = "error"


protection_level_enum = PgEnum(
    ProtectionLevel,
    name="protection_level",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)

session_status_enum = PgEnum(
    SessionStatus,
    name="session_status",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)

action_type_enum = PgEnum(
    ActionType,
    name="action_type",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)

access_outcome_enum = PgEnum(
    AccessOutcome,
    name="access_outcome",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)


class SessionProtectedResource(Base):
    __tablename__ = "session_protected_resources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resource_path: Mapped[str] = mapped_column(Text, nullable=False)
    resource_name: Mapped[str] = mapped_column(String(255), nullable=False)
    protection_level: Mapped[ProtectionLevel] = mapped_column(
        protection_level_enum,
        default=ProtectionLevel.authenticated,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_requirements: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    access_records: Mapped[list["SessionAccessRecord"]] = relationship(
        "SessionAccessRecord", back_populates="resource", lazy="select"
    )


class SessionAccessRecord(Base):
    __tablename__ = "session_access_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("session_protected_resources.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_status: Mapped[SessionStatus] = mapped_column(
        session_status_enum,
        default=SessionStatus.anonymous,
        nullable=False,
    )
    user_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action_type: Mapped[ActionType] = mapped_column(
        action_type_enum,
        default=ActionType.page_view,
        nullable=False,
    )
    outcome: Mapped[AccessOutcome] = mapped_column(
        access_outcome_enum,
        default=AccessOutcome.allowed,
        nullable=False,
    )
    denial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    redirect_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    resource: Mapped["SessionProtectedResource | None"] = relationship(
        "SessionProtectedResource", back_populates="access_records"
    )
