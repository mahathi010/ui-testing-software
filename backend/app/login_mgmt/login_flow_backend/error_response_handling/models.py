"""SQLAlchemy ORM models for error response handling."""

import enum
import uuid

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ExecutionStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    passed = "passed"
    failed = "failed"
    error = "error"
    skipped = "skipped"


execution_status_enum = PgEnum(
    ExecutionStatus,
    name="error_response_execution_status",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)


class ErrorResponseDefinition(Base):
    __tablename__ = "error_response_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    page_identity_indicator: Mapped[str | None] = mapped_column(Text, nullable=True)
    viewport_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    viewport_height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    visible_sections: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    actionable_controls: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_response_scenarios: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    empty_state_expectations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    invalid_content_expectations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    loading_state_expectations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recovery_conditions: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    requirements: Mapped[dict | None] = mapped_column(JSON, nullable=True)

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

    executions: Mapped[list["ErrorResponseExecution"]] = relationship(
        "ErrorResponseExecution", back_populates="definition", lazy="select"
    )


class ErrorResponseExecution(Base):
    __tablename__ = "error_response_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("error_response_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[ExecutionStatus] = mapped_column(
        execution_status_enum,
        default=ExecutionStatus.pending,
        nullable=False,
    )

    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    summary_outcome: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    requirement_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    failure_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recovery_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    definition: Mapped["ErrorResponseDefinition"] = relationship(
        "ErrorResponseDefinition", back_populates="executions"
    )
