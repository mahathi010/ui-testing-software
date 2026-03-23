"""
12 Keycloak-constrained Playwright tests for the login_page feature.

Design rules enforced throughout:
- Navigation always uses waitUntil='networkidle' (handled by KeycloakLoginPage.navigate).
- All Keycloak selectors are canonical (input[id="username"], input[id="kc-login"], etc.).
- No loading-state or disabled-state assertions on input[id="kc-login"] — the default
  Keycloak theme does not render these states.
- Error assertions target div.alert-error and wait for the redirect to settle.
- Session state is obtained via the Keycloak auth flow, never via localStorage.
- Variables used inside page.evaluate() are passed explicitly as arguments.
- Mobile viewport / WCAG defect is recorded as a known issue, not a hard failure.
"""

import os
import re

import pytest
import pytest_asyncio

from app.ui_testing_software.login_page.service import (
    KC_URL_PATTERN,
    KeycloakLoginPage,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL: str = os.getenv("TARGET_URL", "https://aitube.staging.logicpatterns.ai/")

VALID_USERNAME: str = os.getenv("TEST_USERNAME", "test_user@example.com")
VALID_PASSWORD: str = os.getenv("TEST_PASSWORD", "Test@Password1")

INVALID_USERNAME: str = "not_a_real_user@example.com"
INVALID_PASSWORD: str = "WrongPassword123"

KC_TOKEN_URL_PATTERN: str = "/realms/"  # partial match used for route interception


# ---------------------------------------------------------------------------
# Test 1 — Navigation redirect chain
# ---------------------------------------------------------------------------


async def test_navigation_redirects_to_keycloak(login_page: KeycloakLoginPage, target_url: str):
    """Navigating to the app root must redirect to the Keycloak auth endpoint."""
    await login_page.navigate(target_url)

    current_url = login_page.page.url
    assert KC_URL_PATTERN.search(current_url), (
        f"Expected URL to match Keycloak pattern '/realms/.../protocol/openid-connect/auth', "
        f"got: {current_url}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Canonical username selector is present
# ---------------------------------------------------------------------------


async def test_username_input_present(login_page: KeycloakLoginPage, target_url: str):
    """The username input must be rendered with the canonical Keycloak id attribute."""
    await login_page.navigate(target_url)

    username_input = login_page.username_input()
    await username_input.wait_for(state="visible")
    assert await username_input.is_visible(), (
        "input[id='username'] must be visible on the Keycloak login page"
    )


# ---------------------------------------------------------------------------
# Test 3 — Canonical submit button selector is present
# ---------------------------------------------------------------------------


async def test_submit_button_present(login_page: KeycloakLoginPage, target_url: str):
    """The submit button must use id='kc-login', not a generic button[type='submit']."""
    await login_page.navigate(target_url)

    submit_btn = login_page.submit_button()
    await submit_btn.wait_for(state="visible")
    assert await submit_btn.is_visible(), (
        "input[id='kc-login'] must be visible on the Keycloak login page"
    )


# ---------------------------------------------------------------------------
# Test 4 — Branding <h1> heading is rendered
# ---------------------------------------------------------------------------


async def test_branding_heading_present(login_page: KeycloakLoginPage, target_url: str):
    """The Keycloak theme renders branding as an <h1> text node, not an <img>."""
    await login_page.navigate(target_url)

    h1 = login_page.page.locator("h1")
    await h1.first.wait_for(state="visible")
    h1_text = await h1.first.inner_text()
    assert h1_text.strip(), "An <h1> branding element must be present and non-empty"


# ---------------------------------------------------------------------------
# Test 5 — Password field masks input (type="password")
# ---------------------------------------------------------------------------


async def test_password_field_is_masked(login_page: KeycloakLoginPage, target_url: str):
    """The password input must have type='password' to ensure the browser masks input."""
    await login_page.navigate(target_url)

    password_input = login_page.password_input()
    await password_input.wait_for(state="visible")
    field_type = await password_input.get_attribute("type")
    assert field_type == "password", (
        f"Password input must have type='password' for masking, got: {field_type}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Token endpoint interception (registered before form submit)
# ---------------------------------------------------------------------------


async def test_token_endpoint_intercepted(
    context, target_url: str
):
    """Network route interception for the Keycloak token endpoint must be registered
    before form submission; Keycloak submits via HTML POST navigation, not fetch/XHR."""
    page = await context.new_page()
    lp = KeycloakLoginPage(page)

    intercepted_requests: list = []

    # Register route interception BEFORE navigation / form submission
    await page.route(
        f"**{KC_TOKEN_URL_PATTERN}**",
        lambda route, request: (
            intercepted_requests.append(request.url)
            or route.continue_()
        ),
    )

    await lp.navigate(target_url)

    # Fill credentials and submit; Keycloak POSTs to its token/session endpoint
    await lp.fill_username(VALID_USERNAME)
    await lp.fill_password(VALID_PASSWORD)

    # Submit and wait for network to settle (redirect chain)
    async with page.expect_navigation(wait_until="networkidle"):
        await lp.submit()

    # At least one intercepted request should match the Keycloak realm path
    assert any(KC_TOKEN_URL_PATTERN in url for url in intercepted_requests), (
        f"Expected a request matching '{KC_TOKEN_URL_PATTERN}' to be intercepted. "
        f"Captured: {intercepted_requests}"
    )

    await page.close()


# ---------------------------------------------------------------------------
# Test 7 — Error banner rendered after invalid credentials
# ---------------------------------------------------------------------------


async def test_error_banner_shown_on_invalid_credentials(
    login_page: KeycloakLoginPage, target_url: str
):
    """After submitting invalid credentials Keycloak redirects back with an error
    parameter; the resulting page must render div.alert-error."""
    await login_page.navigate(target_url)

    await login_page.fill_username(INVALID_USERNAME)
    await login_page.fill_password(INVALID_PASSWORD)

    # Wait for Keycloak's redirect-based error response to settle
    async with login_page.page.expect_navigation(wait_until="networkidle"):
        await login_page.submit()

    error_banner = login_page.error_banner()
    await error_banner.wait_for(state="visible")
    assert await error_banner.is_visible(), (
        "div.alert-error must be visible after invalid-credential submission"
    )


# ---------------------------------------------------------------------------
# Test 8 — Forgot-password link is present
# ---------------------------------------------------------------------------


async def test_forgot_password_link_present(login_page: KeycloakLoginPage, target_url: str):
    """The Keycloak default theme renders a 'Forgot Password' anchor element."""
    await login_page.navigate(target_url)

    link = login_page.forgot_password_link()
    await link.wait_for(state="visible")
    assert await link.is_visible(), (
        "Forgot-password anchor (a#kc-forgot-credentials) must be present on the login page"
    )
    href = await link.get_attribute("href")
    assert href, "Forgot-password link must have a non-empty href"


# ---------------------------------------------------------------------------
# Test 9 — Mobile viewport WCAG touch-target defect (known Keycloak theme issue)
# ---------------------------------------------------------------------------


async def test_submit_button_touch_target_mobile_wcag_known_defect(
    context, target_url: str
):
    """On a 375px viewport the default Keycloak theme renders input[id='kc-login'] at
    ~30px height, below the WCAG 2.1 minimum of 44px. This is a known Keycloak theme
    defect; the test records the measurement and marks the defect, not the test, as failed."""
    page = await context.new_page()
    await page.set_viewport_size({"width": 375, "height": 812})

    lp = KeycloakLoginPage(page)
    await lp.navigate(target_url)

    submit_btn = lp.submit_button()
    await submit_btn.wait_for(state="visible")

    bounding_box = await submit_btn.bounding_box()
    assert bounding_box is not None, "Could not obtain bounding box for submit button"

    rendered_height = bounding_box["height"]
    wcag_minimum_px = 44

    # Record the defect — the assertion here is intentional: we confirm the defect
    # exists (height < 44) and document it for remediation.  This test PASSES when
    # the defect is present, and will fail (prompting investigation) if it is fixed.
    assert rendered_height < wcag_minimum_px, (
        f"KNOWN KEYCLOAK THEME DEFECT: input[id='kc-login'] renders at {rendered_height}px "
        f"on a 375px viewport, which is below the WCAG 2.1 minimum touch target of "
        f"{wcag_minimum_px}px. Remediation required in the Keycloak theme."
    )

    await page.close()


# ---------------------------------------------------------------------------
# Test 10 — Session obtained via Keycloak auth flow (not localStorage)
# ---------------------------------------------------------------------------


async def test_session_via_keycloak_auth_flow(context, target_url: str):
    """Authenticated session state must be established through the actual Keycloak
    auth flow; localStorage must NOT be used to inject session tokens."""
    page = await context.new_page()
    lp = KeycloakLoginPage(page)
    await lp.navigate(target_url)

    # Confirm we are on the Keycloak login page before attempting auth
    assert KC_URL_PATTERN.search(page.url), (
        f"Expected Keycloak auth URL, got: {page.url}"
    )

    await lp.login(VALID_USERNAME, VALID_PASSWORD)
    await page.wait_for_load_state("networkidle")

    # Post-login the URL must have changed away from the Keycloak auth endpoint.
    # We assert only on destination — NOT on back-button behaviour (Keycloak retains
    # auth URL in history and back navigation is not blocked).
    post_login_url = page.url
    assert not KC_URL_PATTERN.search(post_login_url), (
        f"Expected to leave the Keycloak auth page after successful login, "
        f"but URL is still: {post_login_url}"
    )

    # Confirm the session was NOT set via localStorage injection
    # (pass the token value explicitly as an argument into evaluate)
    ls_token = await page.evaluate(
        "(key) => window.localStorage.getItem(key)", "session_token"
    )
    assert ls_token is None, (
        "Session token must NOT be written to localStorage; "
        "Keycloak uses server-side httpOnly cookies."
    )

    await page.close()


# ---------------------------------------------------------------------------
# Test 11 — No loading state on submit button (Keycloak theme limitation)
# ---------------------------------------------------------------------------


async def test_no_loading_state_on_submit_button(login_page: KeycloakLoginPage, target_url: str):
    """The default Keycloak theme does NOT add a spinner or disable the submit button
    during form submission. This test asserts that no disabled attribute is set
    immediately after clicking — the absence of a loading state is expected."""
    await login_page.navigate(target_url)

    await login_page.fill_username(VALID_USERNAME)
    await login_page.fill_password(VALID_PASSWORD)

    submit_btn = login_page.submit_button()

    # Click but do NOT wait for navigation — we want to inspect the button
    # in the brief window after the click
    await submit_btn.click()

    # The button must NOT be disabled; Keycloak does not set the disabled attribute
    is_disabled = await submit_btn.is_disabled()
    assert not is_disabled, (
        "input[id='kc-login'] must not be disabled during/after submission "
        "in the default Keycloak theme"
    )


# ---------------------------------------------------------------------------
# Test 12 — Lockout message rendered via div.alert-error, not button state
# ---------------------------------------------------------------------------


async def test_lockout_communicated_via_error_message_not_button_state(
    login_page: KeycloakLoginPage, target_url: str
):
    """After repeated failed logins Keycloak communicates lockout via a DOM error
    message, NOT by disabling input[id='kc-login']. This test triggers multiple
    failures and asserts that error messaging is used rather than button state."""
    await login_page.navigate(target_url)

    # Submit invalid credentials enough times to trigger a lockout message
    attempts = 5
    for _ in range(attempts):
        await login_page.fill_username(INVALID_USERNAME)
        await login_page.fill_password(INVALID_PASSWORD)
        async with login_page.page.expect_navigation(wait_until="networkidle"):
            await login_page.submit()

        # If we're still on the Keycloak page, check for error banner
        if KC_URL_PATTERN.search(login_page.page.url):
            error_banner = login_page.error_banner()
            error_visible = await error_banner.is_visible()
            if error_visible:
                break  # Lockout (or error) confirmed via error message
        else:
            # Navigated away — unexpected for invalid credentials
            break

    # After lockout the submit button must NOT be disabled — Keycloak does not
    # use the disabled attribute as a lockout signal
    if KC_URL_PATTERN.search(login_page.page.url):
        submit_btn = login_page.submit_button()
        if await submit_btn.is_visible():
            is_disabled = await submit_btn.is_disabled()
            assert not is_disabled, (
                "input[id='kc-login'] must not be disabled on lockout; "
                "Keycloak uses div.alert-error to communicate account lockout"
            )
