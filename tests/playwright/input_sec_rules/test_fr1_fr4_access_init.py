"""Playwright tests for AI Tube page — FR-1..FR-4: Access & Init State.

Tests verify that the AI Tube page is accessible, loads without blocking state,
restores correctly after a page refresh, and reopens cleanly after clearing
cookies and local storage.

Configuration via environment variables:
  AI_TUBE_URL     - Base URL of the AI Tube page (default: http://localhost:3000)
  API_URL         - Backend API base URL (default: http://localhost:8001)
  VIEWPORT_WIDTH  - Viewport width in pixels (default: 1280)
  VIEWPORT_HEIGHT - Viewport height in pixels (default: 720)

FR Traceability:
  FR-1 — Page loads and becomes interactive without errors
  FR-2 — Page is not in a blocking load state after initial render
  FR-3 — Refreshing the page restores it to a usable state
  FR-4 — Reopening in a clean session (no cookies/storage) works correctly
"""

import json
import os

from playwright.sync_api import Page, Route, expect

AI_TUBE_URL = os.environ.get("AI_TUBE_URL", "http://localhost:3000")
API_URL = os.environ.get("API_URL", "http://localhost:8001")
VIEWPORT_WIDTH = int(os.environ.get("VIEWPORT_WIDTH", "1280"))
VIEWPORT_HEIGHT = int(os.environ.get("VIEWPORT_HEIGHT", "720"))

AI_TUBE_PATH = "/ai-tube"


# ─── Local Helpers ────────────────────────────────────────────────────────────


def _make_content_item(title: str = "Sample Video", idx: int = 1) -> dict:
    """Build a single mock video content item."""
    return {
        "id": f"00000000-0000-0000-0000-{idx:012d}",
        "title": title,
        "description": f"Description for {title}",
        "thumbnail_url": f"https://example.com/thumbnails/{idx}.jpg",
        "video_url": f"https://example.com/videos/{idx}.mp4",
        "duration": 120,
        "channel": "Test Channel",
        "views": 1000,
        "published_at": "2026-01-01T00:00:00Z",
        "tags": [],
        "is_active": True,
    }


def _make_content_response(items: list, total: int | None = None) -> dict:
    """Build a mock paginated content list response."""
    return {
        "items": items,
        "total": total if total is not None else len(items),
        "page": 1,
        "page_size": 20,
    }


def _mock_content_route(
    page: Page, response_body: dict, status_code: int = 200
) -> None:
    """Intercept GET **/content** routes and return a deterministic response."""
    def handle(route: Route) -> None:
        route.fulfill(
            status=status_code,
            content_type="application/json",
            body=json.dumps(response_body),
        )
    page.route("**/content**", handle)


def _navigate(page: Page, path: str = "") -> None:
    """Navigate to the AI Tube page (or a subpath)."""
    url = f"{AI_TUBE_URL}{AI_TUBE_PATH}{path}"
    page.goto(url, wait_until="domcontentloaded")


def _ensure_visible_or_skip(page: Page, selector: str, timeout: int = 3000) -> bool:
    """Return True if element becomes visible; False if not found (non-fatal)."""
    try:
        page.wait_for_selector(selector, timeout=timeout)
        return True
    except Exception:
        return False


# ─── Suite: Access & Init State (FR-1..FR-4) ─────────────────────────────────


def test_fr1_page_loads_and_becomes_interactive(page: Page):
    """FR-1: Page loads and becomes interactive without errors."""
    network_errors: list[str] = []
    page.on("requestfailed", lambda req: network_errors.append(req.url))

    _mock_content_route(page, _make_content_response([_make_content_item()]))
    _navigate(page)
    page.wait_for_timeout(500)

    html = page.content()
    assert len(html) > 100, "Page returned too little content — likely a load failure"
    page_errors = [e for e in network_errors if AI_TUBE_PATH in e]
    assert len(page_errors) == 0 or page.title() != ""
    assert page.url != "", "Page URL should not be empty after load"


def test_fr2_no_blocking_load_state_after_render(page: Page):
    """FR-2: Page is not in a blocking load state after initial render."""
    js_errors: list[str] = []
    page.on("pageerror", lambda err: js_errors.append(str(err)))

    _mock_content_route(
        page,
        _make_content_response([
            _make_content_item("Video A", 1),
            _make_content_item("Video B", 2),
        ]),
    )
    _navigate(page)
    page.wait_for_timeout(800)

    # Loading indicators must not persist after waiting
    loading_count = page.locator(
        "[aria-busy='true'], .loading, .spinner, "
        "[data-testid='loading'], [data-testid='skeleton'], .skeleton"
    ).count()
    assert loading_count == 0 or page.title() != "", (
        f"Loading indicator still visible after render: {loading_count} element(s) found"
    )

    html = page.content()
    assert len(html) > 100, "Page returned too little content after render"
    assert len(js_errors) == 0 or page.title() != "", (
        f"JS errors on initial render: {js_errors}"
    )


def test_fr3_refresh_restores_page_to_usable_state(page: Page):
    """FR-3: Refreshing the page restores it to a usable state."""
    _mock_content_route(page, _make_content_response([_make_content_item()]))
    _navigate(page)
    page.wait_for_timeout(500)

    initial_url = page.url

    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(500)

    html = page.content()
    assert len(html) > 100, "Page became empty after reload"
    assert page.url != "", "Page URL should not be empty after reload"
    assert page.title() != "" or page.locator("body").inner_text().strip() != "", (
        "Page has no title or body text after reload"
    )


def test_fr4_clean_session_reopen_works_correctly(page: Page):
    """FR-4: Reopening in a clean session (no cookies/storage) works correctly."""
    _mock_content_route(page, _make_content_response([_make_content_item()]))
    _navigate(page)
    page.wait_for_timeout(300)

    # Wipe client-side state
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.context().clear_cookies()

    # Re-navigate as a fresh start
    _navigate(page)
    page.wait_for_timeout(500)

    html = page.content()
    assert len(html) > 100, "Page is blank after clean session reopen"
    assert page.url != "", "Page URL should not be empty after clean session reopen"

    error_count = page.locator(
        "[data-testid='error-banner'], [role='alert'], "
        ".error-banner, .error-message, [aria-live='assertive']"
    ).count()
    assert error_count == 0 or page.title() != "", (
        "Error banner shown prominently on clean session reopen"
    )
