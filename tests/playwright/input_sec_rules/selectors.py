"""Centralized selectors for the AI Tube page under test.

These selectors prefer test-IDs, roles, and accessible names over brittle CSS
paths so that minor style refactors do not break the suite. Each constant is a
CSS selector string that Playwright can consume directly.
"""

# ─── PAGE IDENTITY ────────────────────────────────────────────────────────────

PAGE_TITLE = "h1, h2, [role='heading'], [data-testid='page-title']"
MAIN_CONTAINER = "[data-testid='main-container'], [data-testid='ai-tube-container'], main, [role='main']"

# ─── SEARCH ───────────────────────────────────────────────────────────────────

SEARCH_INPUT = (
    "[data-testid='search-input'], "
    "input[type='search'], "
    "input[name='search'], "
    "input[placeholder*='search' i], "
    "input[aria-label*='search' i]"
)
SEARCH_BUTTON = (
    "[data-testid='search-button'], "
    "button[type='submit'], "
    "button[aria-label*='search' i]"
)
SEARCH_RESULTS = (
    "[data-testid='search-results'], "
    "[role='list'][aria-label*='result' i], "
    ".search-results"
)

# ─── CONTENT ──────────────────────────────────────────────────────────────────

CONTENT_CARD = (
    "[data-testid='content-card'], "
    "[data-testid*='video-card'], "
    ".video-card, "
    "[role='listitem']:has(img), "
    "article"
)
CONTENT_GRID = (
    "[data-testid='content-grid'], "
    "[data-testid='video-grid'], "
    ".content-grid, "
    "[role='list']"
)
CONTENT_TITLE = (
    "[data-testid='content-title'], "
    ".video-title, "
    ".card-title, "
    "h3"
)
THUMBNAIL = (
    "img[data-testid='thumbnail'], "
    "img.thumbnail, "
    "[data-testid='content-card'] img"
)

# ─── PLAYER / DETAIL ──────────────────────────────────────────────────────────

VIDEO_PLAYER = (
    "[data-testid='video-player'], "
    "video, "
    "[role='dialog'] video, "
    ".player-container"
)
PLAYER_MODAL = (
    "[data-testid='player-modal'], "
    "[role='dialog'][aria-modal='true'], "
    ".modal.active"
)
MODAL_CLOSE = (
    "[data-testid='modal-close'], "
    "[aria-label*='close' i], "
    "[aria-label*='dismiss' i], "
    "button:has-text('Close'), "
    "button:has-text('×')"
)
DETAIL_PANEL = (
    "[data-testid='detail-panel'], "
    ".detail-view, "
    ".video-detail"
)

# ─── NAVIGATION ───────────────────────────────────────────────────────────────

NAV_TABS = "[data-testid='nav-tabs'], [role='tablist'], .nav-tabs"
NAV_TAB = "[role='tab'], .nav-tab, [data-testid*='tab']"
PAGINATION = (
    "[data-testid='pagination'], "
    "[aria-label*='pagination' i], "
    ".pagination"
)
NEXT_PAGE = (
    "[data-testid='next-page'], "
    "[aria-label*='next' i], "
    "button:has-text('Next')"
)
FILTER_CONTROL = (
    "[data-testid='filter'], "
    "[role='combobox'], "
    "select, "
    "[aria-label*='filter' i]"
)

# ─── EMPTY / ERROR STATE ──────────────────────────────────────────────────────

EMPTY_STATE = (
    "[data-testid='empty-state'], "
    ".empty-state, "
    ".no-content, "
    "[role='status']:has-text('No'), "
    "p:has-text('No results'), "
    "p:has-text('Nothing')"
)
ERROR_BANNER = (
    "[data-testid='error-banner'], "
    "[role='alert'], "
    ".error-banner, "
    ".error-message, "
    "[aria-live='assertive']"
)
RETRY_BUTTON = (
    "[data-testid='retry'], "
    "button:has-text('Retry'), "
    "button:has-text('Try again'), "
    "button:has-text('Reload')"
)

# ─── LOADING ──────────────────────────────────────────────────────────────────

LOADING_INDICATOR = (
    "[aria-busy='true'], "
    ".loading, "
    ".spinner, "
    "[data-testid='loading'], "
    "[data-testid='skeleton'], "
    ".skeleton"
)
