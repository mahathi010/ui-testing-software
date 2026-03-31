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

protection_level_enum = postgresql.ENUM(
    "public",
    "authenticated",
    "elevated",
    name="protection_level",
    create_type=True,
)

session_status_enum = postgresql.ENUM(
    "active",
    "expired",
    "invalid",
    "anonymous",
    name="session_status",
    create_type=True,
)

action_type_enum = postgresql.ENUM(
    "page_view",
    "guarded_action",
    "navigation",
    "media_access",
    name="action_type",
    create_type=True,
)

access_outcome_enum = postgresql.ENUM(
    "allowed",
    "denied_guest",
    "denied_expired",
    "denied_invalid",
    "denied_forbidden",
    "redirected",
    "error",
    name="access_outcome",
    create_type=True,
)


def upgrade() -> None:
    protection_level_enum.create(op.get_bind(), checkfirst=True)
    session_status_enum.create(op.get_bind(), checkfirst=True)
    action_type_enum.create(op.get_bind(), checkfirst=True)
    access_outcome_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "session_protected_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resource_path", sa.Text, nullable=False),
        sa.Column("resource_name", sa.String(255), nullable=False),
        sa.Column(
            "protection_level",
            protection_level_enum,
            nullable=False,
            server_default="authenticated",
        ),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("session_requirements", postgresql.JSONB, nullable=True),
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
        "session_access_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "session_protected_resources.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.Column("session_token", sa.Text, nullable=True),
        sa.Column(
            "session_status",
            session_status_enum,
            nullable=False,
            server_default="anonymous",
        ),
        sa.Column("user_identifier", sa.String(255), nullable=True),
        sa.Column(
            "action_type",
            action_type_enum,
            nullable=False,
            server_default="page_view",
        ),
        sa.Column(
            "outcome",
            access_outcome_enum,
            nullable=False,
            server_default="allowed",
        ),
        sa.Column("denial_reason", sa.Text, nullable=True),
        sa.Column("redirect_url", sa.Text, nullable=True),
        sa.Column("request_metadata", postgresql.JSONB, nullable=True),
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
        "ix_session_access_records_resource_id",
        "session_access_records",
        ["resource_id"],
    )
    op.create_index(
        "ix_session_access_records_session_status",
        "session_access_records",
        ["session_status"],
    )
    op.create_index(
        "ix_session_access_records_outcome",
        "session_access_records",
        ["outcome"],
    )


def downgrade() -> None:
    op.drop_index("ix_session_access_records_outcome", table_name="session_access_records")
    op.drop_index("ix_session_access_records_session_status", table_name="session_access_records")
    op.drop_index("ix_session_access_records_resource_id", table_name="session_access_records")
    op.drop_table("session_access_records")
    op.drop_table("session_protected_resources")
    access_outcome_enum.drop(op.get_bind(), checkfirst=True)
    action_type_enum.drop(op.get_bind(), checkfirst=True)
    session_status_enum.drop(op.get_bind(), checkfirst=True)
    protection_level_enum.drop(op.get_bind(), checkfirst=True)
