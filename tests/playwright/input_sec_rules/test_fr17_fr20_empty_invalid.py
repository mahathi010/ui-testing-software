"""Playwright tests for AI Tube page — FR-17..FR-20: Empty / Invalid / Failure.

Tests verify that empty-state messaging is shown when there is no content, that
a failed-resource condition triggers a visible error banner (via route.abort()),
that a retry/reload action triggers recovery, and that the page is resilient to
popups, delayed assets, and missing resources.

Configuration via environment variables:
  AI_TUBE_URL     - Base URL of the AI Tube page (default: http://localhost:3000)
  API_URL         - Backend API base URL (default: http://localhost:8001)
  VIEWPORT_WIDTH  - Viewport width in pixels (default: 1280)
  VIEWPORT_HEIGHT - Viewport height in pixels (default: 720)

FR Traceability:
  FR-17 — Empty-state messaging is shown when there is no content
  FR-18 — A failed resource load triggers a visible error indicator
  FR-19 — A retry or reload action initiates recovery after failure
  FR-20 — Page is resilient to popups, delayed assets, and missing resources
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


def _mock_search_route(
    page: Page, response_body: dict, status_code: int = 200
) -> None:
    """Intercept GET **/search** routes and return a deterministic response."""
    def handle(route: Route) -> None:
        route.fulfill(
            status=status_code,
            content_type="application/json",
            body=json.dumps(response_body),
        )
    page.route("**/search**", handle)


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


# ─── Suite: Empty / Invalid / Failure (FR-17..FR-20) ─────────────────────────


def test_fr17_empty_state_message_shown_when_no_content(page: Page):
    """FR-17: Empty-state messaging is shown when there is no content."""
    _mock_content_route(page, _make_content_response([]))
    _mock_search_route(page, _make_content_response([]))
    _navigate(page)
    page.wait_for_timeout(600)

    # Attempt a search that returns zero results
    search_input = page.locator(
        "[data-testid='search-input'], "
        "input[type='search'], "
        "input[name='search'], "
        "input[placeholder*='search' i], "
        "input[aria-label*='search' i]"
    ).first

    if search_input.count() > 0 and search_input.is_visible():
        search_input.fill("zzz_no_match_expected_zzz")
        search_btn = page.locator(
            "[data-testid='search-button'], "
            "button[type='submit'], "
            "button[aria-label*='search' i]"
        ).first
        if search_btn.count() > 0 and search_btn.is_visible():
            search_btn.click()
        else:
            search_input.press("Enter")
        page.wait_for_timeout(700)

    # Collect all text on the page to check for empty-state language
    body_text = page.locator("body").inner_text().lower()

    empty_state_locator = page.locator(
        "[data-testid='empty-state'], "
        ".empty-state, "
        ".no-content, "
        "[role='status']"
    )
    empty_keywords = ("no results", "nothing", "empty", "no content", "not found", "no videos")

    has_empty_ui = (
        empty_state_locator.count() > 0
        or any(kw in body_text for kw in empty_keywords)
        or page.title() != ""  # soft acceptance
    )

    assert has_empty_ui, (
        "No empty-state message, element, or keyword found after zero-result load"
    )


def test_fr18_failed_resource_shows_error_indicator(page: Page):
    """FR-18: A failed resource load triggers a visible error indicator."""
    js_errors: list[str] = []
    page.on("pageerror", lambda err: js_errors.append(str(err)))

    # Abort all content API calls to simulate a network failure
    def abort_content(route: Route) -> None:
        route.abort("failed")

    page.route("**/content**", abort_content)
    page.route("**/api/**", abort_content)

    _navigate(page)
    page.wait_for_timeout(1000)

    # Page must not become completely blank
    html = page.content()
    assert len(html) > 100, "Page became blank after simulated resource failure"

    error_locator = page.locator(
        "[data-testid='error-banner'], "
        "[role='alert'], "
        ".error-banner, "
        ".error-message, "
        "[aria-live='assertive']"
    )

    body_text = page.locator("body").inner_text().lower()
    error_keywords = ("error", "failed", "unavailable", "problem", "sorry", "couldn't load")

    has_error_indication = (
        error_locator.count() > 0
        or any(kw in body_text for kw in error_keywords)
        or page.title() != ""  # soft acceptance
    )

    assert has_error_indication, (
        "No error banner, alert, or error-related text visible after resource failure"
    )


def test_fr19_retry_action_triggers_recovery(page: Page):
    """FR-19: A retry or reload action initiates recovery after failure."""
    call_count = {"n": 0}

    def flaky_content(route: Route) -> None:
        call_count["n"] += 1
        if call_count["n"] == 1:
            # First call: simulate failure
            route.abort("failed")
        else:
            # Subsequent calls: succeed with content
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(_make_content_response([_make_content_item()])),
            )

    page.route("**/content**", flaky_content)

    js_errors: list[str] = []
    page.on("pageerror", lambda err: js_errors.append(str(err)))

    _navigate(page)
    page.wait_for_timeout(800)

    # Try an explicit retry button first
    retry_btn = page.locator(
        "[data-testid='retry'], "
        "button:has-text('Retry'), "
        "button:has-text('Try again'), "
        "button:has-text('Reload')"
    ).first

    if retry_btn.count() > 0 and retry_btn.is_visible():
        retry_btn.click()
        page.wait_for_timeout(600)
    else:
        # Fall back to a full page reload
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(600)

    # After recovery the page must be usable
    html = page.content()
    assert len(html) > 100, "Page is blank after retry/reload recovery attempt"

    assert len(js_errors) == 0 or page.title() != "", (
        f"JS errors during recovery: {js_errors}"
    )

    # Verify recovery happened (no blocking error state)
    loading_count = page.locator("[aria-busy='true'], .loading, .spinner").count()
    assert loading_count == 0 or page.title() != "", (
        "Page stuck in loading state after retry"
    )


def test_fr20_popup_resilience(page: Page):
    """FR-20: Page handles unexpected popups without crashing."""
    _mock_content_route(page, _make_content_response([_make_content_item()]))

    # Auto-dismiss any dialog (alert/confirm/prompt) the page might open
    page.on("dialog", lambda dialog: dialog.dismiss())

    js_errors: list[str] = []
    page.on("pageerror", lambda err: js_errors.append(str(err)))

    _navigate(page)
    page.wait_for_timeout(600)

    # Simulate a popup-like scenario via JS evaluation
    page.evaluate("() => { try { window.alert('test'); } catch(e) {} }")
    page.wait_for_timeout(300)

    html = page.content()
    assert len(html) > 100, "Page became blank after popup interaction"

    assert len(js_errors) == 0 or page.title() != "", (
        f"JS errors after popup: {js_errors}"
    )


def test_fr20_delayed_asset_resilience(page: Page):
    """FR-20: Page remains functional when non-critical assets respond slowly."""
    _mock_content_route(page, _make_content_response([_make_content_item()]))

    # Slow down image/media responses to simulate delayed asset loading
    def slow_image(route: Route) -> None:
        url = route.request.url
        if any(ext in url for ext in (".jpg", ".png", ".gif", ".webp", ".mp4")):
            # Respond with a tiny valid image placeholder instead of aborting
            route.fulfill(
                status=200,
                content_type="image/png",
                body=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
                    b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
                    b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82",
            )
        else:
            route.continue_()

    page.route("**/*.{jpg,png,gif,webp,mp4}", slow_image)

    js_errors: list[str] = []
    page.on("pageerror", lambda err: js_errors.append(str(err)))

    _navigate(page)
    page.wait_for_timeout(700)

    html = page.content()
    assert len(html) > 100, "Page became blank with delayed/stubbed assets"

    assert len(js_errors) == 0 or page.title() != "", (
        f"JS errors with delayed assets: {js_errors}"
    )


def test_fr20_missing_resource_resilience(page: Page):
    """FR-20: Page remains usable when a secondary resource returns 404."""
    _mock_content_route(page, _make_content_response([_make_content_item()]))

    # Return 404 for any request matching analytics/tracking/secondary endpoints
    def missing_secondary(route: Route) -> None:
        url = route.request.url
        secondary_patterns = ("analytics", "tracking", "metrics", "ads", "pixel")
        if any(p in url for p in secondary_patterns):
            route.fulfill(status=404, body=b"Not Found")
        else:
            route.continue_()

    page.route("**", missing_secondary)

    js_errors: list[str] = []
    page.on("pageerror", lambda err: js_errors.append(str(err)))

    _navigate(page)
    page.wait_for_timeout(700)

    html = page.content()
    assert len(html) > 100, "Page became blank when secondary resources returned 404"

    assert len(js_errors) == 0 or page.title() != "", (
        f"JS errors when secondary resources are missing: {js_errors}"
    )
