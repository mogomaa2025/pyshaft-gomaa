# PyShaft — TODO Tracker

> **Current Phase**: Phase 1 — Foundation (Weeks 1–2)  
> **Status**: 🟢 Ready to Start

---

## Phase 1 — Foundation (Weeks 1–2)

### 1. Package Skeleton
- [ ] Create `pyshaft/` package directory structure
- [ ] Create `pyshaft/__init__.py` with version string (`__version__ = "0.1.0"`)
- [ ] Create `pyproject.toml` with:
  - Package metadata (name, description, authors)
  - Python ≥ 3.10 requirement
  - Dependencies: `selenium`, `webdriver-manager`, `httpx`, `pytest-xdist`, `pytest-rerunfailures`
  - Build backend: `setuptools` or `hatchling`
  - Optional deps: `ffmpeg-python` (video), `pytest-asyncio` (async)
- [ ] Create `pytest_pyshaft/` package directory
- [ ] Create `tests/` directory with `unit/`, `integration/`, `examples/` subdirs
- [ ] Create `docs/` directory placeholder
- [ ] Create initial `README.md` with project description + "coming soon"

### 2. Config System (`pyshaft/config.py`) — Expanded 7-Section Config
- [ ] Define all config dataclasses with defaults:
  - `BrowserConfig`: browser="chrome", headless=False, window_size="1920x1080", base_url="", navigation_timeout=30
  - `ExecutionConfig`: parallel=False, workers="auto", retry_attempts=0, scope="session"
  - `WaitsConfig`: default_element_timeout=10, polling_interval=0.25, stability_threshold=0.3, network_idle_timeout=3, navigation_timeout=30, respect_native_waits=True
  - `ValidationsConfig`: force_element_visibility=True, force_locator_unique=True, force_text_verification=False, force_navigation_check=True
  - `ActionsConfig`: js_click_fallback=True
  - `ReportConfig`: output_dir="pyshaft-report", screenshot_on_fail=True, screenshot_on_step=False, video_on_fail=False, junit_xml=True, json_report=True
  - `ApiConfig`: base_url="", timeout=30, verify_ssl=True
- [ ] Implement `load_config(path: str | None = None) -> Config`:
  - Search for `pyshaft.toml` in current dir, parent dirs
  - Merge user config with defaults (deep merge)
  - Validate values (e.g., scope must be session/module/function, browser must be chrome/firefox/edge)
- [ ] Implement `get_config() -> Config` singleton accessor
- [ ] Handle missing file gracefully (return all defaults)
- [ ] Support environment variable overrides: `PYSHAFT_BROWSER=firefox`

### 3. Session Management (`pyshaft/session.py`)
- [ ] Create `SessionContext` class:
  - Thread-local storage for driver instance
  - Worker-ID keyed for parallel execution (`threading.get_ident()`)
  - Methods: `get_driver()`, `set_driver()`, `close()`, `close_all()`
  - Track session state (active/closed), browser_name, start_time
- [ ] Implement thread-safety with `threading.local()`
- [ ] Support parallel execution: each pytest-xdist worker gets isolated session
- [ ] Scope-based cleanup: function/module/session teardown

### 4. Driver Factory (`pyshaft/core/driver_factory.py`)
- [ ] Create `DriverFactory` class:
  - `create(browser="chrome", headless=False, window_size="1920x1080", video_on_fail=False) -> WebDriver`
  - `create_chrome(headless, window_size, video_on_fail, **options) -> WebDriver`
  - `create_firefox(headless, window_size, **options) -> WebDriver`
  - `create_edge(headless, window_size, **options) -> WebDriver`
  - Use `webdriver-manager` for automatic driver downloads
- [ ] Configure browser options:
  - Headless mode support (`--headless=new` for Chrome)
  - Window size
  - Common args: `--disable-infobars`, `--no-sandbox`, `--disable-dev-shm-usage`
  - Video recording: Chrome DevTools `Page.startScreencast` when `video_on_fail=True`
- [ ] Error handling: driver not found, download failed

### 5. Pytest Plugin Skeleton (`pytest_pyshaft/plugin.py`)
- [ ] Create pytest fixture `pyshaft_session`:
  - Scope controlled by config (`session`/`module`/`function` from `execution.scope`)
  - Creates browser via `DriverFactory` with headless + video_on_fail from config
  - Stores driver in `SessionContext` (worker-ID keyed for parallel)
  - Closes browser on teardown (scope-aware)
- [ ] Register fixture via `@pytest.fixture`
- [ ] Create `@pytest.mark.pyshaft_scope("function")` marker:
  - Parse marker in fixture to override global scope
  - Apply per-test scope override
- [ ] Parallel execution support:
  - When `execution.parallel = true`, isolate sessions per worker
  - Use `pytest-xdist` worker ID to key sessions
- [ ] Retry integration:
  - When `execution.retry_attempts > 0`, wrap test execution
  - Fresh browser instance per retry (no stale state)

### 6. Pytest Hooks (`pytest_pyshaft/hooks.py`)
- [ ] Implement `pytest_configure` hook:
  - Register custom markers (`pyshaft_scope`)
  - Load config early
  - Initialize video recording if `video_on_fail=True`
- [ ] Implement `pytest_runtest_setup` hook:
  - Initialize session if needed
  - Start video recording for test (if enabled)
  - Initialize step collector
- [ ] Implement `pytest_runtest_teardown` hook:
  - Handle session cleanup based on scope
  - Stop video recording on failure, save trimmed `.webm`
  - Capture screenshot on failure (if `screenshot_on_fail=True`)
- [ ] Implement `pytest_runtest_makereport` hook:
  - Capture test result, attach to report
  - Trigger retry if `retry_attempts > 0` and test failed
- [ ] Implement `pytest_sessionfinish` hook:
  - Write all reports (HTML + JSON + JUnit XML)
  - Merge reports from parallel workers

### 7. Web Module Stub (`pyshaft/web/__init__.py`)
- [ ] Create `open_url(url: str) -> None`:
  - Resolve base_url from config (prepend if relative)
  - Get driver from session
  - Call `driver.get(full_url)`
  - If `force_navigation_check`: verify URL changed + page title loaded (with `navigation_timeout`)
  - If `respect_native_waits`: trigger `wait_for_network_idle`
- [ ] Create `get_url() -> str`
- [ ] Create `get_title() -> str`
- [ ] Create `assert_title(expected: str) -> None`:
  - Wait for title to match (simple poll, uses `default_element_timeout`)
  - Raise `AssertionError` on mismatch

### 8. First Test (`tests/examples/test_smoke.py`)
- [ ] Write smoke test:
  ```python
  from pyshaft.web import open_url, assert_title
  
  def test_google_title():
      open_url("https://google.com")
      assert_title("Google")
  ```
- [ ] Test runs via `pytest tests/examples/test_smoke.py`
- [ ] Browser opens, navigates, asserts, closes

### 9. Config Override Marker Test
- [ ] Write test demonstrating scope override:
  ```python
  import pytest
  
  @pytest.mark.pyshaft_scope("function")
  def test_isolated_browser():
      open_url("https://example.com")
      assert_title("Example Domain")
  ```

### 10. Documentation
- [ ] Write Phase 1 README section with:
  - Installation instructions (`pip install -e .`)
  - Quick start example
  - Config file explanation
  - Scope configuration examples

---

## Phase 1 Acceptance Criteria
- [ ] `pip install -e .` installs pyshaft successfully
- [ ] `pytest tests/examples/test_smoke.py` passes
- [ ] Browser opens and navigates to URL
- [ ] `assert_title()` works with wait
- [ ] Expanded `pyshaft.toml` config loading works (7 sections)
- [ ] Session scope (session/module/function) configurable via `execution.scope`
- [ ] `@pytest.mark.pyshaft_scope` marker works
- [ ] Browser closes cleanly after tests
- [ ] `headless = true` runs browser in headless mode
- [ ] `force_navigation_check` verifies page loaded after `open_url()`
- [ ] `js_click_fallback` retries click via JS when WebDriver click fails
- [ ] `respect_native_waits = false` skips auto-wait pipeline
- [ ] `video_on_fail = true` saves `.webm` for failed tests
- [ ] `screenshot_on_fail = true` captures screenshot on failure
- [ ] Parallel execution via `pytest -n auto` isolates sessions per worker
- [ ] `retry_attempts = 2` retries failed test up to 2 times with fresh browser

---

## Phase 2 — Dual Locator Engine (Weeks 3–4)

> **Start after Phase 1 complete**

- [ ] Create `pyshaft/core/locator.py`
- [ ] Implement `_detect_mode(text: str) -> str` ("raw" or "semantic")
  - Raw CSS signals: starts with `#`, `.`, `[`, `>`, `css=`
  - XPath signals: starts with `//`, `.//`, `xpath=`
  - Everything else → semantic
- [ ] Implement 10-strategy semantic resolution chain — replaces XPath for 99% of use cases:
  1. ARIA role + name (`button[aria-label="Login"]`)
  2. Exact visible text (JS text scan)
  3. Partial visible text (JS text scan with `contains()`)
  4. Placeholder / label / aria-label (`input[placeholder*="Email"]`)
  5. ID contains text (`#loginBtn`, `#login-btn`, `#login_button`)
  6. data-testid / data-qa / data-cy (`[data-testid="login"]`, `[data-qa="login-btn"]`)
  7. Title/alt/name attributes
  8. **Relative/near**: "button near Email field" → finds closest element by proximity
  9. **Parent/ancestor chain**: "button inside login form" → finds parent then descends
  10. **Index/ordinal**: "first submit button", "third row" → `:nth-of-type`, JS ordinal
- [ ] **Shadow DOM support** (strategy #11):
  - `shadow > button` traverses shadow roots recursively
  - `shadow > #container > button` with intermediate IDs/classes
  - Works with nested shadow DOMs (Lit, Stencil, Polymer)
  - JS-based: walks `element.shadowRoot` properties recursively
- [ ] Implement explicit prefix support: `css=`, `xpath=`, `text=` (full XPath supported)
- [ ] Implement `DualLocator` class with `resolve(description) -> WebElement`
- [ ] Add locator result caching (keyed by description + URL)
- [ ] Implement `MultipleMatchWarning` with best-match selection
- [ ] Implement `force_locator_unique` config: when `true`, upgrade `MultipleMatchWarning` to `MultipleMatchError`
- [ ] Create custom exceptions:
  - `ElementNotFoundError` — with auto-screenshot + all 10 tried strategies dump
  - `MultipleMatchError` — raised when `force_locator_unique=true` and >1 match
- [ ] Write 50+ unit tests for locator scenarios
- [ ] Integrate locator into `click()`, `type_text()`, and all web functions

---

## Phase 3 — Auto-Wait Engine (Weeks 5–6)

> **Start after Phase 2 complete**

- [ ] Create `pyshaft/core/wait_engine.py`
- [ ] Implement WaitEngine with checks:
  - Element visible (not `display:none`, not `opacity:0`)
  - Element enabled (no `disabled` attr)
  - Position stable (not mid-animation, 300ms stability)
  - Not covered by overlay/modal
- [ ] Implement overlay detection before clicks
- [ ] Implement NetworkIdle wait on `open_url()`
- [ ] Implement `wait_until(condition: Callable) -> None`
- [ ] Timeout errors include element state snapshot
- [ ] Integrate `force_element_visibility` config: enforce visibility check in pipeline
- [ ] Integrate `respect_native_waits` config: when `false`, skip entire wait pipeline (raw Selenium escape hatch)

---

## Phase 4 — pyshaft.web (Weeks 7–8)

> **Start after Phase 3 complete**

- [ ] Complete `pyshaft/web/navigation.py`: `open_url`, `go_back`, `go_forward`, `refresh`, `get_url`, `get_title`
  - `open_url` respects `force_navigation_check` and `navigation_timeout`
- [ ] Complete `pyshaft/web/interactions.py`: `click`, `double_click`, `right_click`, `hover`, `drag_to`
  - `click` respects `js_click_fallback` config
- [ ] Complete `pyshaft/web/inputs.py`: `type_text`, `clear_text`, `press_key`, `upload_file`
  - `type_text` respects `force_text_verification` (re-reads field value after typing)
- [ ] Complete `pyshaft/web/assertions.py`: `assert_text`, `assert_visible`, `assert_hidden`, `assert_url`, `assert_title`, `assert_attribute`, `assert_enabled`, `assert_disabled`, `assert_checked`
- [ ] Complete `pyshaft/web/windows.py`: `switch_to_frame`, `switch_to_main`, `switch_to_window`, `close_tab`
- [ ] Complete scroll functions: `scroll_to`, `scroll_to_bottom`, `scroll_by`
- [ ] Complete wait functions: `wait_for_text`, `wait_for_visible`, `wait_until`
- [ ] Complete utilities: `take_screenshot`, `execute_js`, `get_cookies`, `set_cookie`
- [ ] Integration tests on Sauce Demo
- [ ] **Alert/Dialog handling** (`pyshaft/web/alerts.py`):
  - `accept_alert()` — accepts JS alert/confirm
  - `dismiss_alert()` — dismisses JS confirm dialog
  - `get_alert_text() → str` — reads alert message
  - `type_alert(text)` — types into JS prompt
  - `handle_auth(username, password)` — handles HTTP Basic Auth popup
- [ ] **Element collections** (`pyshaft/web/collections.py`):
  - `count(locator) → int` — number of matching elements
  - `get_all(locator) → list[WebElement]` — all matching elements
  - `first(locator) → WebElement` — first match
  - `last(locator) → WebElement` — last match
  - `nth(locator, n) → WebElement` — nth match (1-indexed)
  - `filter_visible(elements) → list[WebElement]` — filter to visible only
- [ ] **Keyboard combos** (`pyshaft/web/keyboard.py`):
  - `hotkey(*keys) → None` — press multiple keys simultaneously (e.g., `hotkey("Control", "c")`)
  - `press_combo(*keys) → None` — sequential key combination
  - `hold(key) → None`, `press(key) → None`, `release(key) → None` — individual control for complex combos
- [ ] **LocalStorage/SessionStorage** (`pyshaft/web/storage.py`):
  - `get_local_storage(key) → str | None`
  - `set_local_storage(key, value) → None`
  - `clear_local_storage() → None`
  - `get_session_storage(key) → str | None`
  - `set_session_storage(key, value) → None`
  - `clear_session_storage() → None`
- [ ] **File download** (`pyshaft/web/downloads.py`):
  - `wait_for_download(timeout=30) → str` — waits for file to appear in download dir, returns path
  - `get_downloaded_file(name) → Path` — get path to specific downloaded file
  - Configurable download directory via `pyshaft.toml`
- [ ] **Table helpers** (`pyshaft/web/tables.py`):
  - `get_cell(row, col, table=None) → str` — get cell text (1-indexed)
  - `get_row_count(table=None) → int` — number of rows
  - `get_column(col, table=None) → list[str]` — all values in column
  - `assert_cell_text(row, col, expected, table=None) → None`
  - Auto-detects `<table>`, or finds by locator
- [ ] **Date picker helper** (`pyshaft/web/dates.py`):
  - `set_date(locator, value="2025-01-15") → None`
  - Handles native `<input type=date>` via JS
  - Handles flatpickr, Material Date, React Date Picker via click-then-type
  - Validates date format before setting
- [ ] **Drag by offset** (`pyshaft/web/interactions.py`):
  - `drag_by_offset(locator, dx=100, dy=50) → None` — for kanban boards, sorters, canvas
  - Uses `ActionChains.drag_and_drop_by_offset`
- [ ] **New tab/window** (`pyshaft/web/windows.py`):
  - `open_new_tab(url) → None` — opens URL in new tab, switches to it
  - `close_all_tabs() → None` — closes all tabs except first
  - `switch_to_tab(index_or_title) → None` — switch by index or title
  - `get_tab_count() → int` — number of open tabs
- [ ] **Deferred assertions** (`pyshaft/web/deferred.py`):
  - `defer_assert_text(locator, expected)` — queues check, doesn't raise immediately
  - `defer_assert_visible(locator)` — queues visibility check
  - `defer_assert_element(locator)` — queues element existence check
  - `check_deferred()` — runs all queued checks, raises `DeferredAssertionError` with combined message listing all failures
- [ ] **JS helpers** (`pyshaft/web/js_helpers.py`):
  - `activate_jquery()` — injects jQuery 3.7 into page if not present
  - `highlight_element(locator, color="red")` — adds temporary red border for demo mode
  - `set_value_via_js(locator, value)` — sets input value via JavaScript
  - `get_text_content(locator)` — returns element text via JS (bypasses Selenium text extraction)
- [ ] **Mobile emulation** (`pyshaft/web/mobile.py`):
  - `open_mobile(url, device="iPhone 14")` — launches Chrome with DevTools device override
  - Device presets: iPhone 14, iPhone SE, Pixel 7, Pixel 5, Galaxy S23, iPad Pro
  - `set_mobile_device(device)` — switch device mid-test
  - Uses Chrome DevTools `Emulation.setDeviceMetricsOverride` + `Network.setUserAgentOverride`
- [ ] **Ad/image blocking** (`pyshaft/web/blocking.py`):
  - `block_ads()` — loads Chrome extension that blocks known ad domains
  - `block_images()` — Chrome preference `profile.managed_default_content_settings.images=2`
  - Reduces bandwidth, speeds up tests on ad-heavy sites
- [ ] **Proxy support** (`pyshaft/web/proxy.py`):
  - `set_proxy(url, type="http")` — HTTP/SOCKS4/SOCKS5 proxy
  - Authenticated proxy: `set_proxy("http://user:pass@proxy:8080")`
  - Per-browser proxy config from `pyshaft.toml`
- [ ] **Session reuse** (`pyshaft/session.py`):
  - `reuse_session()` — keeps current browser/session state for next test
  - `clear_cookies()` — clears all cookies while keeping browser open
  - `preserve_state(keys=["cookies", "localStorage", "sessionStorage"])` — save state
  - `restore_state(keys=...)` — restore saved state

---

## Phase 5 — pyshaft.api (Weeks 9–10)

> **Start after Phase 4 complete**

- [ ] Create `pyshaft/api/client.py` with httpx session
- [ ] Implement `pyshaft/api/methods.py`: `send_get`, `send_post`, `send_put`, `send_patch`, `send_delete`, `send_request`
- [ ] Implement setup: `set_base_url`, `set_headers`, `set_auth`, `set_timeout`, `clear_headers`
- [ ] Implement `pyshaft/api/assertions.py`: `assert_status`, `assert_json`, `assert_json_schema`, `assert_header`, `assert_response_time`, `assert_body_contains`, `assert_body_not_contains`
- [ ] Implement `pyshaft/api/store.py`: `extract_json`, `extract_header`, `store`, `stored`
- [ ] Implement utility: `get_response`, `get_status_code`, `get_response_time`
- [ ] Integration tests on JSONPlaceholder API
- [ ] **GraphQL** (`pyshaft/api/graphql.py`):
  - `send_query(query) → Response` — send GraphQL query
  - `send_mutation(name, variables) → Response` — send GraphQL mutation
  - `assert_gql_errors(expected_errors=None) → None` — assert GraphQL error field exists/doesn't exist
  - `assert_no_gql_errors() → None` — convenience wrapper
- [ ] **Multipart form upload** (`pyshaft/api/methods.py`):
  - `send_file(url, file_path, method="POST") → Response`
  - `send_multipart(url, fields={}, files={}) → Response` — multi-part form data
  - httpx `files=` parameter support
- [ ] **OAuth 2.0 flows** (`pyshaft/api/oauth2.py`):
  - `oauth2_client_credentials(token_url, client_id, client_secret) → str` — returns access token
  - `oauth2_password_grant(token_url, username, password, client_id, client_secret) → str`
  - Auto-refresh on 401: detect expired token, re-auth, retry original request
  - Token caching: store in memory, reuse until expiry
- [ ] **Cookie jar** (`pyshaft/api/client.py`):
  - `get_api_cookies() → dict` — extract all cookies from httpx session
  - `set_api_cookies(cookies: dict) → None` — set cookies on session
  - Cookie-based auth support (session cookies, CSRF tokens)
- [ ] **Pagination helpers** (`pyshaft/api/pagination.py`):
  - `get_all_pages(url, limit=50, page_param="page", cursor_param="cursor") → list[dict]`
  - Supports: offset-based (`?page=1`), cursor-based (`?cursor=abc`), link-header pagination
  - Returns all items across all pages
- [ ] **File download via API** (`pyshaft/api/methods.py`):
  - `download_file(url, save_path) → Path` — handles binary responses, saves to disk
  - Progress callback for large downloads
- [ ] **Multi-proxy routing** (`pyshaft/api/multi_proxy.py`):
  - `--multi-proxy` flag assigns different proxies to parallel workers
  - Each httpx client gets its own proxy config
- [ ] **Request interception** (`pyshaft/api/interceptor.py`):
  - `before_request(callback)` — modify request before sending
  - `after_response(callback)` — inspect/modify response before assertion
- [ ] **@retry_on_exception decorator** (`pyshaft/api/retry.py`):
  - `@retry_on_exception(ConnectionError, timeout=5, max_attempts=3)` — retries on specific exceptions
  - Exponential backoff between retries
  - Works with both web and API functions

---

## Phase 6 — Report Engine (Weeks 11–12)

> **Start after Phase 5 complete**

### 6a. Step Collection + Media Capture
- [ ] Create `pyshaft/report/collector.py` (StepCollector singleton)
- [ ] Implement step auto-capture via decorator/hook
- [ ] Implement screenshot capture on fail + on-demand
- [ ] Implement video on fail:
  - Chrome DevTools `Page.startScreencast` records throughout test
  - On failure: stop recording, save `.webm` trimmed to test duration
  - On pass: discard recording (no storage wasted)
- [ ] **DOM snapshot capture**: serialize DOM before each step (lightweight, `< 10KB`)
  - Capture via `driver.execute_script("return document.documentElement.outerHTML")`
  - Store as compressed blob in SQLite DB
  - Viewer: render in sandboxed iframe with inline styles

### 6b. SQLite History DB (`pyshaft/report/history_db.py`)
- [ ] Auto-create `pyshaft_history.db` on first run (zero config)
- [ ] Database schema:
  - `runs` table: id, timestamp, duration_ms, passed, failed, skipped, total, git_hash, env
  - `tests` table: id, run_id, name, file, status, duration_ms, error, screenshot_path, video_path
  - `steps` table: id, test_id, action, locator, duration_ms, status, dom_snapshot, error, screenshot_path
  - `network` table: id, test_id, url, method, status_code, duration_ms
- [ ] Methods: `insert_run()`, `insert_test()`, `insert_step()`, `insert_network()`
- [ ] Query methods: `get_runs()`, `get_run(id)`, `get_test(id)`, `get_steps(test_id)`, `compare_runs(run1, run2)`
- [ ] Analytics: `get_flaky_tests()`, `get_slowest_tests()`, `get_trend(days)`, `get_pass_rate(days)`

### 6c. Static HTML Report (`pyshaft/report/html_renderer.py`)
- [ ] Self-contained HTML file — open directly, no server needed
- [ ] Dark/light mode toggle (CSS variables)
- [ ] Responsive, mobile-friendly layout (CSS Grid + Flexbox)
- [ ] **Dashboard header**:
  - Summary cards: passed, failed, skipped, total, duration
  - Pass rate donut chart (CSS-only, no JS chart lib)
  - Duration breakdown bar chart
  - Flaky test badge (if any)
- [ ] **Test list table**:
  - Columns: status icon, name, file, duration, actions
  - Sortable by any column (click header)
  - Filter by status (All / Passed / Failed / Skipped)
  - Search by test name (debounced, JS-only)
  - Click row → expand test details
- [ ] **Test detail panel** (expand on row click):
  - Error message (if failed) with syntax highlighting
  - Screenshot gallery (full-width, zoom on hover)
  - Embedded video player (`<video>` tag) for failed tests
  - **Step timeline** (vertical, color-coded):
    - Each step: action name, locator, duration, status icon
    - Click step → show DOM snapshot in iframe + element state
    - Hover step → tooltip with full details
  - **DOM snapshot viewer**:
    - Sandboxed iframe renders captured DOM
    - Inspect element mode: hover highlights, click to copy selector
    - Toggle: raw HTML vs rendered view
  - **Network request log** (collapsible table):
    - Columns: method, URL, status, duration
    - Color-coded status (green 2xx, red 5xx, etc.)
- [ ] **Run comparison** (static mode: pick two runs from dropdown):
  - Side-by-side table showing passed/failed status per test
  - Highlight changed tests (color-coded)
  - Duration delta column

### 6d. Flask Dashboard (`pyshaft/report/flask_app.py`)
- [ ] Flask app: `pyshaft report serve` CLI command
- [ ] **Dashboard home** (`/`):
  - Aggregate stats: total runs, pass rate trend (last 30 days)
  - Pass/fail donut chart (SVG, no JS chart lib)
  - Duration trend line chart (SVG)
  - Top 10 slowest tests
  - Top flaky tests (failed then passed on retry)
  - Recent runs list with status
- [ ] **Run detail page** (`/run/<id>`):
  - Same layout as static HTML report but server-rendered
  - Interactive step timeline with DOM snapshot viewer
  - Video + screenshots
  - Network log
- [ ] **Run comparison page** (`/compare/<id1>/<id2>`):
  - Side-by-side diff view
  - Changed tests highlighted
  - Duration delta chart
- [ ] **Search page** (`/search?q=...`):
  - Full-text search across all historical runs
  - Results grouped by run, with context
  - Filter by date range, status, test file
- [ ] **Live progress page** (`/live`):
  - Server-Sent Events (SSE) stream
  - Steps appear in real-time as tests run
  - Live pass/fail count, duration ticker
  - Auto-refresh test list as tests complete
- [ ] **API endpoints** (`/api/...`):
  - `/api/runs` — list all runs (JSON)
  - `/api/run/<id>` — single run detail
  - `/api/compare/<id1>/<id2>` — comparison data
  - `/api/search?q=...` — search results
  - `/api/live` — SSE stream endpoint
  - `/api/stream` — live step stream (SSE)

### 6e. Live Progress (SSE Integration)
- [ ] SSE endpoint: `/api/stream` — streams steps as they happen
- [ ] Client-side JS: `EventSource` connects to SSE, updates DOM
- [ ] Live counter: total, passed, failed, running, queued
- [ ] Progress bar: estimated time remaining (based on historical avg)
- [ ] Auto-scroll to latest step
- [ ] No WebSocket needed — SSE is simpler, works with Flask

### 6f. JSON + JUnit Export
- [ ] Create `pyshaft/report/json_exporter.py`
- [ ] Create `pyshaft/report/junit_writer.py`
- [ ] Implement `--pyshaft-report` flag in pytest plugin
- [ ] Generate GitHub Actions example workflow

---

## Phase 7 — Release (Weeks 13–14)

> **Start after Phase 6 complete**

- [ ] Write comprehensive README:
  - Quick start guide
  - API reference
  - Configuration guide
  - Examples
- [ ] Set up MkDocs Material documentation site
- [ ] Write example test suite (login flow, API CRUD, mixed)
- [ ] Set up CI pipeline (GitHub Actions)
- [ ] Self-dogfood: run PyShaft's own tests with PyShaft
- [ ] Publish to PyPI (`pyshaft` v1.0.0)
- [ ] Create GitHub release with changelog
- [ ] **CLI commands** (`pyshaft/cli.py`):
  - `pyshaft run` — run tests (wraps pytest with pyshaft config)
  - `pyshaft run --demo` — demo mode (highlight elements, slow execution, show step names)
  - `pyshaft run --headless` — headless mode override
  - `pyshaft run --browser=firefox` — browser override
  - `pyshaft run --grid-url=http://grid:4444` — run on Selenium Grid
  - `pyshaft run --with-s3` — upload reports to AWS S3 after run
  - `pyshaft run --tags=smoke,api` — filter tests by tags
  - `pyshaft run --data=users.csv` — data-driven testing from CSV/JSON
  - `pyshaft record` — test recorder
- [ ] **Test Recorder** (`pyshaft/recorder.py`):
  - Opens browser, records all user actions (clicks, typing, navigation)
  - Generates Python test code: `click("Login")`, `type_text("Email", "...")`
  - Uses PyShaft semantic locators (not raw CSS/XPath)
  - Save to file: `pyshaft record --output=test_login.py`
- [ ] **Demo Mode** (integration into action_runner.py):
  - When active: highlights element before each action (red border, 500ms)
  - Slows execution: `time.sleep(0.5)` between steps
  - Prints step names to console: `>>> click "Login button" [PASS]`
  - Useful for presentations, debugging, and teaching
- [ ] **Selenium Grid support** (`pyshaft/grid.py`):
  - `pyshaft grid start --hub` — start Selenium Grid hub
  - `pyshaft grid start --node --browser=chrome` — start Grid node
  - `--grid-url=http://hub:4444` — run tests on remote grid
  - Supports parallel execution across multiple nodes
- [ ] **AWS S3 integration** (`pyshaft/report/s3_uploader.py`):
  - `--with-s3` uploads: HTML report, screenshots, videos, JSON summary
  - Configurable bucket: `[report.s3] bucket="my-reports", prefix="pyshaft/"`
  - Generates public URLs for sharing
  - Requires `boto3` (optional dependency)
- [ ] **@retry_on_exception decorator** (`pyshaft/utils/retry.py`):
  - `@retry_on_exception(ElementNotFoundError, max_attempts=3, backoff=1.5)`
  - Works on any function — web, API, or custom
  - Logs each retry attempt in report
- [ ] **Data-driven testing** (`pyshaft/utils/data.py`):
  - `@data_from_csv("users.csv")` — runs test once per CSV row, passes row as dict
  - `@data_from_json("scenarios.json")` — runs test once per JSON array item
  - `@data_from_yaml("config.yaml")` — runs test once per YAML item
  - Report shows: `test_login [row 1/100]`, `test_login [row 2/100]`, etc.
- [ ] **Tagging** (`pyshaft/utils/tags.py`):
  - `@tag("smoke")`, `@tag("api", "regression")` — decorate tests
  - `pyshaft run --tags=smoke,api` — run only tagged tests
  - `pyshaft run --exclude-tags=slow,flaky` — skip tagged tests
  - Tags visible in report dashboard
- [ ] **Secrets management** (`pyshaft/utils/secrets.py`):
  - `get_secret("DB_PASSWORD") → str` — reads from:
    1. Environment variable `DB_PASSWORD`
    2. `.env` file in project root
    3. AWS Secrets Manager (if `secrets_provider = "aws"` in config)
    4. HashiCorp Vault (if `secrets_provider = "vault"`)
  - `get_secret_json("CREDENTIALS") → dict` — parses JSON secrets
  - Secrets never logged or shown in reports (redacted as `***`)
- [ ] **PDF testing** (`pyshaft/utils/pdf.py`):
  - `assert_pdf_text("invoice.pdf", "Invoice #123") → None` — checks text exists in PDF
  - `extract_pdf_text("report.pdf") → str` — extracts all text from PDF
  - Supports local files and URLs
  - Requires `pypdf` (optional dependency)
- [ ] **Visual diff** (`pyshaft/utils/visual_diff.py`):
  - `assert_no_visual_change(name="homepage") → None` — pixel comparison against baseline
  - Baseline stored in `pyshaft-visual-baselines/` directory
  - `--update-baselines` flag updates baselines after intentional changes
  - Report shows side-by-side diff with highlighted pixels
  - Requires `Pillow` (optional dependency)

---

## Notes & Decisions Log

| Date | Decision | Details |
|------|----------|---------|
| 2026-04-13 | Locator Syntax | Dual mode — semantic (10-chain) + CSS/XPath fallback. Goal: users never need XPath |
| 2026-04-13 | Browser Session | Shared session default, configurable scope, parallel-worker isolated |
| 2026-04-13 | Package Name | `pyshaft` for PyPI, GitHub, docs |
| 2026-04-13 | Python Version | 3.10+ (match/case, better type hints) |
| 2026-04-13 | Locator Failure | Error + auto-screenshot + dump all tried strategies |
| 2026-04-13 | Async Support | Sync v1.0, optional async via pytest-asyncio |
| 2026-04-13 | Testing Strategy | Core first, comprehensive tests in Phase 2 |
| 2026-04-13 | Config System | 7 sections: browser, execution, waits, validations, actions, report, api |
| 2026-04-13 | Parallel Execution | pytest-xdist, isolated sessions per worker |
| 2026-04-13 | Retry | pytest-rerunfailures, fresh browser per retry |
| 2026-04-13 | Video on Fail | Chrome DevTools screencast, .webm trimmed to test duration |
| 2026-04-13 | Validation Guards | force_element_visibility, force_locator_unique, force_text_verification, force_navigation_check |
| 2026-04-13 | JS Click Fallback | Auto-retry via JS when WebDriver click fails |
| 2026-04-13 | Native Waits Toggle | respect_native_waits=false skips auto-wait (raw Selenium escape hatch) |
