"""In-memory CRUD repository for login_page TestRun records."""

from typing import Dict, List, Optional

from .models import TestRun


class LoginPageRepository:
    """Thread-unsafe in-memory store suitable for single-process testing scenarios."""

    def __init__(self) -> None:
        self._store: Dict[str, TestRun] = {}

    def find_all(self) -> List[TestRun]:
        return list(self._store.values())

    def find_by_id(self, run_id: str) -> Optional[TestRun]:
        return self._store.get(run_id)

    def create(self, run: TestRun) -> TestRun:
        self._store[run.id] = run
        return run

    def update(self, run: TestRun) -> TestRun:
        self._store[run.id] = run
        return run

    def delete(self, run_id: str) -> bool:
        if run_id in self._store:
            del self._store[run_id]
            return True
        return False
