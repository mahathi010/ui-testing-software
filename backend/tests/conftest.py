"""Pytest fixtures."""

import os
import pytest
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.ui_testing_software.login_page.service import KeycloakLoginPage

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

TARGET_URL: str = os.getenv(
    "TARGET_URL", "https://aitube.staging.logicpatterns.ai/"
)
SESSION_TOKEN: str = os.getenv("SESSION_TOKEN", "")


# ---------------------------------------------------------------------------
# Playwright browser / page fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def browser():
    """Launch a single Chromium browser instance shared across all tests in the session."""
    async with async_playwright() as playwright:
        _browser: Browser = await playwright.chromium.launch(headless=True)
        yield _browser
        await _browser.close()


@pytest.fixture()
async def context(browser: Browser) -> BrowserContext:
    """Create an isolated browser context per test."""
    ctx: BrowserContext = await browser.new_context()
    yield ctx
    await ctx.close()


@pytest.fixture()
async def page(context: BrowserContext) -> Page:
    """Open a new page within the test's browser context."""
    p: Page = await context.new_page()
    yield p
    await p.close()


@pytest.fixture()
def login_page(page: Page) -> KeycloakLoginPage:
    """Return a KeycloakLoginPage POM bound to the current test page."""
    return KeycloakLoginPage(page)


@pytest.fixture()
def target_url() -> str:
    """The base URL under test."""
    return TARGET_URL


@pytest.fixture()
def session_token() -> str:
    """A Keycloak-compatible session token loaded from the SESSION_TOKEN env var."""
    return SESSION_TOKEN
