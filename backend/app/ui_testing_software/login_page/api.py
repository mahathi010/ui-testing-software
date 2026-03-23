"""FastAPI router for login_page test-run endpoints."""

from fastapi import APIRouter, HTTPException, status

from .models import TestRun
from .repository import LoginPageRepository
from .schema import TestRunRequest, TestRunResult
from .service import LoginPageService

router = APIRouter(prefix="/login-page", tags=["login-page"])

# Module-level singleton repository and service (suitable for in-process use)
_repository = LoginPageRepository()
_service = LoginPageService(_repository)


def _run_to_result(run: TestRun) -> TestRunResult:
    return TestRunResult(
        id=run.id,
        url=run.url,
        status=run.status,
        result_json=run.result_json,
        created_at=run.created_at.isoformat(),
    )


@router.post(
    "/run-tests",
    response_model=TestRunResult,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue a new login-page test run",
)
async def run_tests(request: TestRunRequest) -> TestRunResult:
    """Create and enqueue a login-page test run against the given *url*.

    Returns the newly created ``TestRun`` record in ``pending`` state.
    The actual Playwright execution happens out-of-band; poll
    ``GET /login-page/results/{id}`` for completion.
    """
    run = _service.create_run(request)
    return _run_to_result(run)


@router.get(
    "/results/{run_id}",
    response_model=TestRunResult,
    summary="Retrieve test-run results by ID",
)
async def get_results(run_id: str) -> TestRunResult:
    """Fetch the current state (and results, once complete) for a test run."""
    run = _service.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run '{run_id}' not found.",
        )
    return _run_to_result(run)
