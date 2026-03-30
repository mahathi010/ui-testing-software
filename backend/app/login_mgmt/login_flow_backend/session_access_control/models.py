"""SQLAlchemy ORM models for session access control."""

import enum
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SessionState(str, enum.Enum):
    authenticated = "authenticated"
    guest = "guest"
    expired = "expired"
    blocked = "blocked"


class ExecutionStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    passed = "passed"
    failed = "failed"
    error = "error"
    skipped = "skipped"


session_state_enum = PgEnum(
    SessionState,
    name="session_access_control_session_state",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)

execution_status_enum = PgEnum(
    ExecutionStatus,
    name="session_access_control_execution_status",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)


class SessionAccessControlDefinition(Base):
    __tablename__ = "session_access_control_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    page_identity_indicator: Mapped[str | None] = mapped_column(Text, nullable=True)
    viewport_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    viewport_height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    session_states: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    protected_routes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    guarded_actions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    redirect_expectations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    session_initialization: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    access_control_expectations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    loading_state_expectations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    empty_state_expectations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_state_expectations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    recovery_behavior: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    retry_behavior: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    requirements: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    clean_session_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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

    executions: Mapped[list["SessionAccessControlExecution"]] = relationship(
        "SessionAccessControlExecution", back_populates="definition", lazy="select"
    )


class SessionAccessControlExecution(Base):
    __tablename__ = "session_access_control_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("session_access_control_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    session_state: Mapped[SessionState | None] = mapped_column(
        session_state_enum,
        nullable=True,
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        execution_status_enum,
        default=ExecutionStatus.pending,
        nullable=False,
    )

    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    access_outcome: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    requirement_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    failure_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    recovery_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    definition: Mapped["SessionAccessControlDefinition"] = relationship(
        "SessionAccessControlDefinition", back_populates="executions"
    )
