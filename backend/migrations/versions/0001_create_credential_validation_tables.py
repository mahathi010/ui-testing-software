"""Create credential validation tables

Revision ID: 0001
Revises:
Create Date: 2026-03-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    coverage_area_enum = postgresql.ENUM(
        "RENDERING",
        "CONTENT_INTERACTIONS",
        "NAVIGATION",
        "CREDENTIAL_SUBMISSION",
        "ERROR_RECOVERY",
        name="coverage_area_enum",
        create_type=False,
    )
    coverage_area_enum.create(op.get_bind(), checkfirst=True)

    rule_type_enum = postgresql.ENUM(
        "PAGE_TITLE",
        "ELEMENT_VISIBLE",
        "ELEMENT_CLICKABLE",
        "INPUT_ACCEPTS",
        "NAVIGATION_TARGET",
        "VALIDATION_MESSAGE",
        "ERROR_MESSAGE",
        "EMPTY_STATE",
        "AUTH_GATE",
        name="rule_type_enum",
        create_type=False,
    )
    rule_type_enum.create(op.get_bind(), checkfirst=True)

    execution_status_enum = postgresql.ENUM(
        "PENDING",
        "RUNNING",
        "PASSED",
        "FAILED",
        "ERROR",
        name="execution_status_enum",
        create_type=False,
    )
    execution_status_enum.create(op.get_bind(), checkfirst=True)

    # Create credential_validation_scenarios table
    op.create_table(
        "credential_validation_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_url", sa.String(2048), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "coverage_area",
            postgresql.ENUM(
                "RENDERING",
                "CONTENT_INTERACTIONS",
                "NAVIGATION",
                "CREDENTIAL_SUBMISSION",
                "ERROR_RECOVERY",
                name="coverage_area_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("requirement_ref", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenarios_coverage_area", "credential_validation_scenarios", ["coverage_area"])
    op.create_index("ix_scenarios_is_active", "credential_validation_scenarios", ["is_active"])
    op.create_index("ix_scenarios_requirement_ref", "credential_validation_scenarios", ["requirement_ref"])

    # Create validation_rules table
    op.create_table(
        "validation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "rule_type",
            postgresql.ENUM(
                "PAGE_TITLE",
                "ELEMENT_VISIBLE",
                "ELEMENT_CLICKABLE",
                "INPUT_ACCEPTS",
                "NAVIGATION_TARGET",
                "VALIDATION_MESSAGE",
                "ERROR_MESSAGE",
                "EMPTY_STATE",
                "AUTH_GATE",
                name="rule_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("selector", sa.String(512), nullable=True),
        sa.Column("expected_value", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["credential_validation_scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rules_scenario_id", "validation_rules", ["scenario_id"])

    # Create test_executions table
    op.create_table(
        "test_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "RUNNING",
                "PASSED",
                "FAILED",
                "ERROR",
                name="execution_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_rules", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_rules", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_rules", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["credential_validation_scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_executions_scenario_id", "test_executions", ["scenario_id"])
    op.create_index("ix_executions_status", "test_executions", ["status"])

    # Create test_results table
    op.create_table(
        "test_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("actual_value", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["test_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["validation_rules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_results_execution_id", "test_results", ["execution_id"])
    op.create_index("ix_results_rule_id", "test_results", ["rule_id"])
    op.create_index("ix_results_passed", "test_results", ["passed"])


def downgrade() -> None:
    op.drop_table("test_results")
    op.drop_table("test_executions")
    op.drop_table("validation_rules")
    op.drop_table("credential_validation_scenarios")

    op.execute("DROP TYPE IF EXISTS execution_status_enum")
    op.execute("DROP TYPE IF EXISTS rule_type_enum")
    op.execute("DROP TYPE IF EXISTS coverage_area_enum")
