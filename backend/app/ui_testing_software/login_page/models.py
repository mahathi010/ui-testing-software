"""TestRun model for login_page feature."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional


class TestRun:
    """Represents a single test run execution record."""

    def __init__(
        self,
        url: str,
        status: str = "pending",
        result_json: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        self.id: str = id or str(uuid.uuid4())
        self.url: str = url
        self.status: str = status  # pending | running | completed | failed
        self.result_json: Optional[Dict[str, Any]] = result_json
        self.created_at: datetime = created_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "status": self.status,
            "result_json": self.result_json,
            "created_at": self.created_at.isoformat(),
        }
