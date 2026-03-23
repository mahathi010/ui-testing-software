"""Keycloak Login Page service: Page Object Model + business-logic service."""

import re
from typing import Any, Dict, List, Optional

import structlog

from .models import TestRun
from .repository import LoginPageRepository
from .schema import TestRunRequest

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Keycloak selectors (canonical — do NOT change to generic selectors)
# ---------------------------------------------------------------------------
SELECTOR_USERNAME = 'input[id="username"]'
SELECTOR_PASSWORD = 'input[id="password"]'
SELECTOR_SUBMIT = 'input[id="kc-login"]'
SELECTOR_ERROR_BANNER = "div.alert-error"
SELECTOR_FORGOT_PASSWORD = "a#kc-forgot-credentials"  # Keycloak default theme

KC_URL_PATTERN = re.compile(r"/realms/.+/protocol/openid-connect/auth")
KC_TOKEN_PATTERN = "/realms/"  # partial match used in route interception


class KeycloakLoginPage:
    """Page Object Model for the Keycloak-hosted login page.

    All navigation uses ``waitUntil='networkidle'`` to allow the full
    Keycloak redirect chain to settle before any assertions are made.
    """

    def __init__(self, page: Any) -> None:
        """
        Args:
            page: A Playwright ``Page`` instance.
        """
        self.page = page

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    async def navigate(self, url: str) -> None:
        """Navigate to *url* and wait for the Keycloak redirect to settle.

        After this method returns, ``self.page.url`` will match the
        Keycloak ``/realms/.../protocol/openid-connect/auth`` pattern.
        """
        await self.page.goto(url, wait_until="networkidle")

    # ------------------------------------------------------------------
    # Element accessors
    # ------------------------------------------------------------------

    def username_input(self):
        return self.page.locator(SELECTOR_USERNAME)

    def password_input(self):
        return self.page.locator(SELECTOR_PASSWORD)

    def submit_button(self):
        return self.page.locator(SELECTOR_SUBMIT)

    def error_banner(self):
        return self.page.locator(SELECTOR_ERROR_BANNER)

    def forgot_password_link(self):
        return self.page.locator(SELECTOR_FORGOT_PASSWORD)

    # ------------------------------------------------------------------
    # Interactions
    # ------------------------------------------------------------------

    async def fill_username(self, username: str) -> None:
        await self.username_input().fill(username)

    async def fill_password(self, password: str) -> None:
        await self.password_input().fill(password)

    async def submit(self) -> None:
        """Click the Keycloak submit button.

        Note: The default Keycloak theme does NOT render a loading state
        or disable the button during submission — this is expected behaviour.
        """
        await self.submit_button().click()

    async def login(self, username: str, password: str) -> None:
        """Fill credentials and submit the form."""
        await self.fill_username(username)
        await self.fill_password(password)
        await self.submit()

    # ------------------------------------------------------------------
    # Assertions (helpers used by tests)
    # ------------------------------------------------------------------

    def current_url_is_keycloak(self) -> bool:
        """Return True if the current page URL matches the Keycloak auth pattern."""
        return bool(KC_URL_PATTERN.search(self.page.url))


# ---------------------------------------------------------------------------
# LoginPageService
# ---------------------------------------------------------------------------


class LoginPageService:
    """Business-logic service that orchestrates test-run lifecycle."""

    def __init__(self, repository: LoginPageRepository) -> None:
        self.repository = repository

    def create_run(self, request: TestRunRequest) -> TestRun:
        run = TestRun(url=request.url)
        self.repository.create(run)
        logger.info("login_page.run.created", run_id=run.id, url=run.url)
        return run

    def get_run(self, run_id: str) -> Optional[TestRun]:
        return self.repository.find_by_id(run_id)

    def list_runs(self) -> List[TestRun]:
        return self.repository.find_all()

    def mark_running(self, run_id: str) -> Optional[TestRun]:
        run = self.repository.find_by_id(run_id)
        if run is None:
            return None
        run.status = "running"
        self.repository.update(run)
        return run

    def complete_run(
        self, run_id: str, result_json: Dict[str, Any], success: bool = True
    ) -> Optional[TestRun]:
        run = self.repository.find_by_id(run_id)
        if run is None:
            return None
        run.status = "completed" if success else "failed"
        run.result_json = result_json
        self.repository.update(run)
        logger.info("login_page.run.completed", run_id=run_id, status=run.status)
        return run
