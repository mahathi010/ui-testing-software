"""Pydantic request/response schemas for login_page feature."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TestRunRequest(BaseModel):
    """Request schema for triggering a login-page test run."""

    url: str = Field(
        default="https://aitube.staging.logicpatterns.ai/",
        description="Target URL to navigate to (will redirect to Keycloak)",
    )
    test_names: Optional[List[str]] = Field(
        default=None,
        description="Optional list of specific test names to run; runs all if omitted",
    )


class TestRunResult(BaseModel):
    """Response schema for a completed or in-progress test run."""

    id: str = Field(..., description="Unique test run identifier")
    url: str = Field(..., description="Target URL that was tested")
    status: str = Field(..., description="pending | running | completed | failed")
    result_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detailed per-test results once the run completes",
    )
    created_at: str = Field(..., description="ISO-8601 timestamp of run creation")

    model_config = {"from_attributes": True}
