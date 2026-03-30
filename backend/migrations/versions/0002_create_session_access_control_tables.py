"""Create session access control tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

session_state_enum = postgresql.ENUM(
    "authenticated",
    "guest",
    "expired",
    "blocked",
    name="session_access_control_session_state",
    create_type=True,
)

execution_status_enum = postgresql.ENUM(
    "pending",
    "running",
    "passed",
    "failed",
    "error",
    "skipped",
    name="session_access_control_execution_status",
    create_type=True,
)


def upgrade() -> None:
    session_state_enum.create(op.get_bind(), checkfirst=True)
    execution_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "session_access_control_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target_url", sa.Text, nullable=False),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("page_identity_indicator", sa.Text, nullable=True),
        sa.Column("viewport_width", sa.Integer, nullable=True),
        sa.Column("viewport_height", sa.Integer, nullable=True),
        sa.Column("session_states", postgresql.JSONB, nullable=True),
        sa.Column("protected_routes", postgresql.JSONB, nullable=True),
        sa.Column("guarded_actions", postgresql.JSONB, nullable=True),
        sa.Column("redirect_expectations", postgresql.JSONB, nullable=True),
        sa.Column("session_initialization", postgresql.JSONB, nullable=True),
        sa.Column("access_control_expectations", postgresql.JSONB, nullable=True),
        sa.Column("loading_state_expectations", postgresql.JSONB, nullable=True),
        sa.Column("empty_state_expectations", postgresql.JSONB, nullable=True),
        sa.Column("error_state_expectations", postgresql.JSONB, nullable=True),
        sa.Column("recovery_behavior", postgresql.JSONB, nullable=True),
        sa.Column("retry_behavior", postgresql.JSONB, nullable=True),
        sa.Column("requirements", postgresql.JSONB, nullable=True),
        sa.Column("clean_session_required", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "session_access_control_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "definition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "session_access_control_definitions.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("target_url", sa.Text, nullable=True),
        sa.Column("target_version", sa.String(50), nullable=True),
        sa.Column(
            "session_state",
            session_state_enum,
            nullable=True,
        ),
        sa.Column(
            "status",
            execution_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_outcome", postgresql.JSONB, nullable=True),
        sa.Column("requirement_results", postgresql.JSONB, nullable=True),
        sa.Column("failure_details", postgresql.JSONB, nullable=True),
        sa.Column("recovery_details", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_session_access_control_executions_definition_id",
        "session_access_control_executions",
        ["definition_id"],
    )
    op.create_index(
        "ix_session_access_control_executions_status",
        "session_access_control_executions",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_session_access_control_executions_status",
        table_name="session_access_control_executions",
    )
    op.drop_index(
        "ix_session_access_control_executions_definition_id",
        table_name="session_access_control_executions",
    )
    op.drop_table("session_access_control_executions")
    op.drop_table("session_access_control_definitions")
    execution_status_enum.drop(op.get_bind(), checkfirst=True)
    session_state_enum.drop(op.get_bind(), checkfirst=True)
