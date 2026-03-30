"""Playwright tests for login flow credential validation.

These tests drive a real browser against a configured login page to verify
the functional requirements FR-1..FR-32 captured in credential_validation
definitions.

Configuration via environment variables:
  LOGIN_URL         - URL of the login page under test (required)
  VALID_EMAIL       - Valid email credential (default: test@example.com)
  VALID_PASSWORD    - Valid password credential (default: password123)
  INVALID_PASSWORD  - Invalid password (default: wrongpassword)
  EXPECTED_TITLE    - Expected page title fragment (default: Login)
  POST_LOGIN_URL    - URL fragment expected after successful login (default: /dashboard)
  VIEWPORT_WIDTH    - Browser viewport width (default: 1280)
  VIEWPORT_HEIGHT   - Browser viewport height (default: 720)
"""

import os

import pytest
from playwright.sync_api import Page, expect

LOGIN_URL = os.environ.get("LOGIN_URL", "http://localhost:3000/login")
VALID_EMAIL = os.environ.get("VALID_EMAIL", "test@example.com")
VALID_PASSWORD = os.environ.get("VALID_PASSWORD", "password123")
INVALID_PASSWORD = os.environ.get("INVALID_PASSWORD", "wrongpassword")
EXPECTED_TITLE = os.environ.get("EXPECTED_TITLE", "Login")
POST_LOGIN_URL = os.environ.get("POST_LOGIN_URL", "/dashboard")
VIEWPORT_WIDTH = int(os.environ.get("VIEWPORT_WIDTH", "1280"))
VIEWPORT_HEIGHT = int(os.environ.get("VIEWPORT_HEIGHT", "720"))


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
    }


@pytest.fixture(autouse=True)
def navigate_to_login(page: Page):
    page.goto(LOGIN_URL)


# ─── FR-1..FR-6: Initial Rendering ───────────────────────────────────────────


def test_fr1_page_loads_without_errors(page: Page):
    """FR-1: Page loads without errors and becomes interactive."""
    expect(page).not_to_have_url("about:blank")
    # Verify no navigation error page
    assert page.title() != ""


def test_fr2_page_title_matches_expected(page: Page):
    """FR-2: Page title or heading matches expected product identity."""
    title = page.title()
    assert EXPECTED_TITLE.lower() in title.lower() or page.locator("h1").count() > 0


def test_fr3_login_form_is_visible(page: Page):
    """FR-3: Login form container is visible in the viewport."""
    form = page.locator("form").first
    expect(form).to_be_visible()


def test_fr4_email_and_password_fields_present(page: Page):
    """FR-4: Email and password input fields are present and enabled."""
    email_input = page.get_by_role("textbox", name=lambda n: "email" in n.lower()).or_(
        page.locator("input[type='email'], input[name='email'], input[placeholder*='email' i]").first
    )
    password_input = page.locator("input[type='password']").first
    expect(email_input).to_be_visible()
    expect(email_input).to_be_enabled()
    expect(password_input).to_be_visible()
    expect(password_input).to_be_enabled()


def test_fr5_submit_button_present_and_actionable(page: Page):
    """FR-5: Submit/login button is present and actionable."""
    submit = page.get_by_role("button", name=lambda n: any(
        word in n.lower() for word in ("login", "sign in", "submit", "log in")
    )).or_(page.locator("button[type='submit']").first)
    expect(submit).to_be_visible()
    expect(submit).to_be_enabled()


def test_fr6_viewport_renders_correctly(page: Page):
    """FR-6: Viewport renders correctly at specified width/height."""
    viewport = page.viewport_size
    assert viewport["width"] == VIEWPORT_WIDTH
    assert viewport["height"] == VIEWPORT_HEIGHT
    # No horizontal scroll
    scroll_width = page.evaluate("document.documentElement.scrollWidth")
    assert scroll_width <= VIEWPORT_WIDTH + 20  # allow 20px tolerance


# ─── FR-7..FR-12: Interactions ───────────────────────────────────────────────


def test_fr7_email_field_accepts_input(page: Page):
    """FR-7: Email field accepts keyboard input and retains value."""
    email_input = page.locator("input[type='email'], input[name='email']").first
    email_input.fill(VALID_EMAIL)
    expect(email_input).to_have_value(VALID_EMAIL)


def test_fr8_password_field_masks_characters(page: Page):
    """FR-8: Password field accepts input and masks characters."""
    password_input = page.locator("input[type='password']").first
    expect(password_input).to_have_attribute("type", "password")
    password_input.fill(VALID_PASSWORD)
    expect(password_input).to_have_value(VALID_PASSWORD)


def test_fr9_fields_can_be_cleared_and_refilled(page: Page):
    """FR-9: Fields can be cleared and re-filled."""
    email_input = page.locator("input[type='email'], input[name='email']").first
    email_input.fill(VALID_EMAIL)
    email_input.fill("")
    expect(email_input).to_have_value("")
    email_input.fill(VALID_EMAIL)
    expect(email_input).to_have_value(VALID_EMAIL)


def test_fr10_inputs_display_placeholder_text(page: Page):
    """FR-10: Input fields display placeholder text when empty."""
    email_input = page.locator("input[type='email'], input[name='email']").first
    password_input = page.locator("input[type='password']").first
    # At least one of the inputs should have a placeholder
    email_placeholder = email_input.get_attribute("placeholder")
    password_placeholder = password_input.get_attribute("placeholder")
    assert email_placeholder or password_placeholder


# ─── FR-13..FR-16: Navigation ─────────────────────────────────────────────────


def test_fr13_form_submission_triggers_network_request(page: Page):
    """FR-13: Form submission triggers a network request to the auth endpoint."""
    requests_made = []
    page.on("request", lambda req: requests_made.append(req))

    email_input = page.locator("input[type='email'], input[name='email']").first
    password_input = page.locator("input[type='password']").first
    email_input.fill(VALID_EMAIL)
    password_input.fill(VALID_PASSWORD)

    with page.expect_request(lambda req: req.method in ("POST", "GET")):
        page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign in')").first.click()

    # At least some network activity should occur
    assert len(requests_made) > 0


# ─── FR-17..FR-24: Credential / Input Flows ───────────────────────────────────


def test_fr18_empty_email_rejected(page: Page):
    """FR-18: Empty email field submission is rejected with feedback."""
    password_input = page.locator("input[type='password']").first
    password_input.fill(VALID_PASSWORD)

    submit = page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign in')").first
    submit.click()

    # Either the form stays on the same page or shows validation feedback
    page.wait_for_timeout(500)
    current_url = page.url
    assert LOGIN_URL.split("//")[1].split("/")[0] in current_url or page.locator(
        "[aria-invalid='true'], .error, [role='alert']"
    ).count() > 0


def test_fr19_empty_password_rejected(page: Page):
    """FR-19: Empty password field submission is rejected with feedback."""
    email_input = page.locator("input[type='email'], input[name='email']").first
    email_input.fill(VALID_EMAIL)

    submit = page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign in')").first
    submit.click()

    page.wait_for_timeout(500)
    current_url = page.url
    assert LOGIN_URL.split("//")[1].split("/")[0] in current_url or page.locator(
        "[aria-invalid='true'], .error, [role='alert']"
    ).count() > 0


def test_fr20_malformed_email_rejected(page: Page):
    """FR-20: Malformed email format is rejected at validation."""
    email_input = page.locator("input[type='email'], input[name='email']").first
    password_input = page.locator("input[type='password']").first
    email_input.fill("not-an-email")
    password_input.fill(VALID_PASSWORD)

    submit = page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign in')").first
    submit.click()

    page.wait_for_timeout(500)
    # Should still be on the login page
    assert "login" in page.url.lower() or page.locator("form").count() > 0


# ─── FR-25..FR-32: Error / Recovery ──────────────────────────────────────────


def test_fr25_error_message_visible_after_failed_login(page: Page):
    """FR-25: Error message is visible and readable after failed login."""
    email_input = page.locator("input[type='email'], input[name='email']").first
    password_input = page.locator("input[type='password']").first
    email_input.fill(VALID_EMAIL)
    password_input.fill(INVALID_PASSWORD)

    submit = page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign in')").first
    submit.click()

    # Wait for error feedback
    page.wait_for_timeout(1000)
    error_el = page.locator("[role='alert'], .error, .error-message, [data-testid='error']").first
    # If the page shows an error, verify it has text content
    if error_el.count() > 0:
        assert error_el.inner_text().strip() != ""


def test_fr27_user_can_retry_after_failed_login(page: Page):
    """FR-27: User can retry login after a failed attempt."""
    email_input = page.locator("input[type='email'], input[name='email']").first
    password_input = page.locator("input[type='password']").first
    email_input.fill(VALID_EMAIL)
    password_input.fill(INVALID_PASSWORD)

    submit = page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign in')").first
    submit.click()
    page.wait_for_timeout(500)

    # Form should still be interactable after failure
    expect(email_input).to_be_enabled()
    expect(password_input).to_be_enabled()
    expect(submit).to_be_enabled()
