"""SQLAlchemy ORM models for credential validation."""

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class CoverageArea(str, enum.Enum):
    RENDERING = "RENDERING"
    CONTENT_INTERACTIONS = "CONTENT_INTERACTIONS"
    NAVIGATION = "NAVIGATION"
    CREDENTIAL_SUBMISSION = "CREDENTIAL_SUBMISSION"
    ERROR_RECOVERY = "ERROR_RECOVERY"


class RuleType(str, enum.Enum):
    PAGE_TITLE = "PAGE_TITLE"
    ELEMENT_VISIBLE = "ELEMENT_VISIBLE"
    ELEMENT_CLICKABLE = "ELEMENT_CLICKABLE"
    INPUT_ACCEPTS = "INPUT_ACCEPTS"
    NAVIGATION_TARGET = "NAVIGATION_TARGET"
    VALIDATION_MESSAGE = "VALIDATION_MESSAGE"
    ERROR_MESSAGE = "ERROR_MESSAGE"
    EMPTY_STATE = "EMPTY_STATE"
    AUTH_GATE = "AUTH_GATE"


class ExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"


class CredentialValidationScenario(Base):
    __tablename__ = "credential_validation_scenarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_url = Column(String(2048), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    coverage_area = Column(
        Enum(CoverageArea, values_callable=lambda x: [e.value for e in x], name="coverage_area_enum"),
        nullable=False,
    )
    requirement_ref = Column(String(50), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    rules = relationship("ValidationRule", back_populates="scenario", cascade="all, delete-orphan")
    executions = relationship("TestExecution", back_populates="scenario", cascade="all, delete-orphan")


class ValidationRule(Base):
    __tablename__ = "validation_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("credential_validation_scenarios.id", ondelete="CASCADE"), nullable=False)
    rule_type = Column(
        Enum(RuleType, values_callable=lambda x: [e.value for e in x], name="rule_type_enum"),
        nullable=False,
    )
    selector = Column(String(512), nullable=True)
    expected_value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    scenario = relationship("CredentialValidationScenario", back_populates="rules")
    results = relationship("TestResult", back_populates="rule", cascade="all, delete-orphan")


class TestExecution(Base):
    __tablename__ = "test_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("credential_validation_scenarios.id", ondelete="CASCADE"), nullable=False)
    status = Column(
        Enum(ExecutionStatus, values_callable=lambda x: [e.value for e in x], name="execution_status_enum"),
        nullable=False,
        default=ExecutionStatus.PENDING,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_rules = Column(Integer, nullable=False, default=0)
    passed_rules = Column(Integer, nullable=False, default=0)
    failed_rules = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    scenario = relationship("CredentialValidationScenario", back_populates="executions")
    results = relationship("TestResult", back_populates="execution", cascade="all, delete-orphan")


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("test_executions.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("validation_rules.id", ondelete="CASCADE"), nullable=False)
    passed = Column(Boolean, nullable=False)
    actual_value = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    execution = relationship("TestExecution", back_populates="results")
    rule = relationship("ValidationRule", back_populates="results")
