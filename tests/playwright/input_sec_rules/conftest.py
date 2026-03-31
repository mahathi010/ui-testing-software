"""Shared fixtures and helpers for the AI Tube input security rules test suite.

This module provides pytest fixtures and utility functions shared across all
input_sec_rules test modules, covering FR-1..FR-20 for the AI Tube page.

Configuration via environment variables:
  AI_TUBE_URL           - Base URL of the AI Tube page (default: http://localhost:3000)
  API_URL               - Backend API base URL (default: http://localhost:8001)
  VIEWPORT_WIDTH        - Viewport width in pixels (default: 1280)
  VIEWPORT_HEIGHT       - Viewport height in pixels (default: 720)
  MOBILE_VIEWPORT_WIDTH - Mobile viewport width in pixels (default: 375)
  MOBILE_VIEWPORT_HEIGHT- Mobile viewport height in pixels (default: 667)
"""

import json
import os

import pytest
from playwright.sync_api import Page, Route

AI_TUBE_URL = os.environ.get("AI_TUBE_URL", "http://localhost:3000")
API_URL = os.environ.get("API_URL", "http://localhost:8001")
VIEWPORT_WIDTH = int(os.environ.get("VIEWPORT_WIDTH", "1280"))
VIEWPORT_HEIGHT = int(os.environ.get("VIEWPORT_HEIGHT", "720"))
MOBILE_VIEWPORT_WIDTH = int(os.environ.get("MOBILE_VIEWPORT_WIDTH", "375"))
MOBILE_VIEWPORT_HEIGHT = int(os.environ.get("MOBILE_VIEWPORT_HEIGHT", "667"))

AI_TUBE_PATH = "/ai-tube"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
    }


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
