# PyShaft — Project Plan

> **Status**: Decisions Locked · Phase 1 Ready  
> **Goal**: Build `pyshaft` — a Python test automation framework with semantic locators, auto-wait, and modern reporting. Installable via `pip install pyshaft`.

---

## 🔒 All Decisions Locked

| # | Decision | Value |
|---|----------|-------|
| 1 | **Locator Syntax** | Dual mode — plain English (semantic) + raw CSS/XPath fallback. Smart auto-detection at runtime. XPath supported but users should never need it. |
| 2 | **Browser Session** | Shared session by default (fast). Configurable to `function`/`module`/`session` scope via `pyshaft.toml`. |
| 3 | **Package Name** | `pyshaft` — PyPI, GitHub org, docs domain all under this name. |
| 4 | **Python Version** | **Python 3.10+** — match/case for locator detection, cleaner union types (`str | None`), covers 90%+ of active installs. |
| 5 | **Locator Failure Behavior** | **Error + auto-screenshot + dump all tried strategies** in the error message. Detailed debugging info, zero extra deps. |
| 6 | **Async Support** | **Sync API in v1.0 with optional async mode via `pytest-asyncio`**. Keeps codebase clean; full async path for v2.0. |
| 7 | **Testing Strategy** | Core skeleton first in Phase 1. Comprehensive unit/integration tests in Phase 2 with the locator engine. |

---

## 🏗️ Architecture Overview

### Package Structure
```
pyshaft/
├── pyshaft/
│   ├── __init__.py             # version, public re-exports
│   ├── config.py               # pyshaft.toml loader + defaults
│   ├── session.py              # thread-local SessionContext
│   ├── core/
│   │   ├── driver_factory.py   # Chrome/Firefox/Edge + webdriver-manager
│   │   ├── locator.py          # DualLocator: detect_mode + 7-chain + cache
│   │   ├── wait_engine.py      # WaitEngine: visible/stable/overlay checks
│   │   ├── action_runner.py    # locate → wait → execute → log pipeline
│   │   └── step_logger.py      # captures step name/time/screenshot
│   ├── web/
│   │   ├── __init__.py         # exports all public functions
│   │   ├── navigation.py
│   │   ├── interactions.py     # click, hover, drag_to, etc.
│   │   ├── inputs.py
│   │   ├── assertions.py
│   │   ├── windows.py          # frames, tabs, windows
│   │   └── screenshot.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py           # httpx session + base_url + auth
│   │   ├── methods.py          # send_get, send_post, etc.
│   │   ├── assertions.py
│   │   └── store.py            # extract_json, store, stored
│   └── report/
│       ├── collector.py        # StepCollector singleton
│       ├── html_renderer.py
│       ├── json_exporter.py
│       └── junit_writer.py
├── pytest_pyshaft/
│   ├── plugin.py               # session/module/function fixture + markers
│   └── hooks.py                # pytest_runtest_* hooks for step capture
├── tests/
│   ├── unit/                   # locator, wait, config unit tests
│   ├── integration/            # real browser + real API tests
│   └── examples/               # sample tests (login, API CRUD, mixed)
├── docs/                       # MkDocs Material
├── pyproject.toml
├── pyshaft.toml                # default config for examples
└── README.md
```

### Core Design Principles
- **Zero required config** — sensible defaults for everything
- **Auto-wait built in** — every action goes through the wait pipeline silently (toggleable via `respect_native_waits`)
- **Dual locator engine** — auto-detects semantic vs raw, supports `css=`, `xpath=`, `text=` prefixes
- **Thread-safe session storage** — shared session by default, configurable scope, parallel-ready
- **Modern reports** — HTML (dark/light), JSON, JUnit XML, optional video on failure
- **Validation guards** — enforce visibility, locator uniqueness, text verification, navigation checks
- **Resilient actions** — JS click fallback, retry attempts, per-test isolation when needed

---

## 📅 Build Phases (14 Weeks)

### Phase 1 — Weeks 1–2: Foundation
**Goal**: Skeleton, DriverFactory, Session, Config — make the first test pass: `open_url("https://google.com")`

- [ ] PyShaft package + `pyproject.toml` (Python ≥ 3.10)
- [ ] DriverFactory: Chrome/Firefox/Edge via webdriver-manager + headless + video recording support
- [ ] SessionContext: thread-local driver storage, parallel-worker isolated
- [ ] `pyshaft.toml` loader with expanded 7-section config:
  - `[browser]` — browser, headless, window_size, base_url, navigation_timeout
  - `[execution]` — parallel, workers, retry_attempts, scope
  - `[waits]` — default_element_timeout, polling_interval, stability_threshold, network_idle_timeout, navigation_timeout, respect_native_waits
  - `[validations]` — force_element_visibility, force_locator_unique, force_text_verification, force_navigation_check
  - `[actions]` — js_click_fallback
  - `[report]` — output_dir, screenshot_on_fail, screenshot_on_step, video_on_fail, junit_xml, json_report
  - `[api]` — base_url, timeout, verify_ssl
- [ ] Pytest plugin skeleton (conftest.py + session fixture)
- [ ] Configurable scope: session/module/function via toml
- [ ] `@pytest.mark.pyshaft_scope` override marker
- [ ] First test: `open_url()` + `assert_title()`
- [ ] JS click fallback in action pipeline
- [ ] Navigation check after `open_url()` (force_navigation_check)

### Phase 2 — Weeks 3–4: Dual Locator Engine
**Goal**: SmartLocator with semantic + raw CSS/XPath + auto-detection. `click("Login")` and `click("#login")` and `click("//button[@data-id='submit']")` all work.

- [ ] `_detect_mode()`: auto-detect raw vs semantic
- [ ] 10-strategy semantic resolution chain — covers every XPath use case:
  1. ARIA role + name
  2. Exact visible text
  3. Partial visible text
  4. Placeholder / label / aria-label
  5. ID contains text
  6. data-testid / data-qa / data-cy attributes
  7. Title/alt/name attributes
  8. **Relative/near**: "button near Email field" (positional)
  9. **Parent/ancestor chain**: "button inside login form" (structural)
  10. **Index/ordinal**: "first submit button", "third row"
- [ ] **Shadow DOM support** — strategy #11: `shadow > button` traverses shadow roots recursively
- [ ] Explicit prefix support: `css=`, `xpath=`, `text=`
- [ ] MultipleMatchWarning + best-match selection
- [ ] Locator result caching (keyed by description + URL)
- [ ] Unit tests: 50+ locator scenarios

### Phase 3 — Weeks 5–6: Auto-Wait Engine
**Goal**: Playwright-grade waits — no `sleep()`, ever. Toggleable via `respect_native_waits`.

- [ ] WaitEngine: visible, enabled, stable, not-covered checks
- [ ] Overlay/modal detection before clicks
- [ ] NetworkIdle wait on `open_url()`
- [ ] `wait_until(lambda: ...)` for custom conditions
- [ ] Timeout errors with element state snapshot in message
- [ ] `respect_native_waits` toggle — when `false`, skip auto-wait pipeline (raw Selenium escape hatch)

### Phase 4 — Weeks 7–8: pyshaft.web
**Goal**: Full web automation module (35+ functions) + advanced utilities.

- [ ] All navigation, interaction, input, scroll, frame/window functions
- [ ] All 10 assertion functions
- [ ] Every function goes through wait pipeline automatically
- [ ] Integration tests on real demo app (Sauce Demo)
- [ ] **Alert/Dialog handling** — `accept_alert()`, `dismiss_alert()`, `get_alert_text()`, `type_alert("text")`, `handle_auth(user, pass)`
- [ ] **Element collections** — `count("tr")`, `get_all("li") → list[WebElement]`, `first("btn")`, `last("btn")`, `nth("row", 3)`
- [ ] **Keyboard combos** — `hotkey("Control", "c")`, `press_combo("Alt", "F4")`, `hold("Shift")` + `press("Tab")` + `release("Shift")`
- [ ] **LocalStorage/SessionStorage** — `get_local_storage("key")`, `set_local_storage("key", "value")`, `clear_local_storage()`
- [ ] **File download** — `wait_for_download(timeout=30) → str`, `get_downloaded_file(name) → Path`
- [ ] **Table helpers** — `get_cell(row=2, col=3)`, `get_row_count()`, `get_column(1)`, `assert_cell_text(row=1, col=2, expected="John")`
- [ ] **Date picker helper** — `set_date("Date field", "2025-01-15")` — handles native `<input type=date>`, flatpickr, Material Date
- [ ] **Drag by offset** — `drag_by_offset(locator, dx=100, dy=50)` — for kanban, sorters, canvas
- [ ] **Deferred assertions** — batch multiple checks, report all failures at once:
  - `defer_assert_text("Welcome")`, `defer_assert_visible("Logout")` → `check_deferred()` raises combined error
- [ ] **JS helpers** — `activate_jquery()`, `highlight_element()`, `set_value_via_js()`, `get_text_content()`
- [ ] **Mobile emulation** — `open_mobile("iPhone 14")`, `open_mobile("Pixel 7")` (Chrome DevTools device override)
- [ ] **Ad/image blocking** — `block_ads()`, `block_images()` (Chrome extension or JS-based blocking)
- [ ] **Proxy support** — `set_proxy("http://proxy:8080")`, authenticated proxy support
- [ ] **Demo mode** — `pyshaft run --demo` highlights elements, slows execution, shows step names (for presentations/debugging)
- [ ] **Session reuse** — `reuse_session()`, `clear_cookies()` for multi-test state management

### Phase 5 — Weeks 9–10: pyshaft.api
**Goal**: Full REST API testing module (25+ functions) + GraphQL + advanced utilities.

- [ ] HTTP client built on httpx (async-ready, sync first)
- [ ] All request methods + auth helpers
- [ ] `assert_json_schema` with jsonschema library
- [ ] store/stored value chaining for multi-step flows
- [ ] Integration tests on JSONPlaceholder API
- [ ] **GraphQL** — `send_query("{ users { id name } }")`, `send_mutation("createUser", {...})`, `assert_gql_errors()`
- [ ] **Multipart form upload** — `send_file(url, file_path)`, `send_multipart(url, fields={...}, files={...})`
- [ ] **OAuth 2.0 flows** — `oauth2_client_credentials(url, id, secret)`, `oauth2_password_grant(url, user, pass, id, secret)`, auto-refresh on 401
- [ ] **Cookie jar** — `get_api_cookies() → dict`, `set_api_cookies(dict)` — cookie-based auth support
- [ ] **Pagination helpers** — `get_all_pages("/items", limit=50)` — auto-iterates cursor/offset-based pagination
- [ ] **File download via API** — `download_file(url, save_path) → Path` — handles binary responses
- [ ] **Multi-proxy routing** — `--multi-proxy` for parallel API tests through different proxies
- [ ] **Request interception** — intercept and modify requests before they're sent (via httpx middleware)

### Phase 6 — Weeks 11–12: Report Engine
**Goal**: Hybrid report — static HTML file + Flask dashboard with SQLite history, live progress, DOM snapshots, video, and interactive UI.

- [ ] StepCollector: auto-intercepts every action via decorator
- [ ] Screenshot capture on fail + on-demand
- [ ] Video recording: Chrome DevTools screencast, `.webm` saved on failure, trimmed to test duration
- [ ] **DOM snapshot per step**: capture serialized DOM before each action (lightweight, no full page dump)
- [ ] **SQLite history DB** (`pyshaft_history.db`):
  - Auto-created on first run, zero config
  - Stores every test run: steps, screenshots, videos, durations, status
  - Enables: run comparison, flaky test detection, trend analysis
- [ ] **Static HTML report** (self-contained, open directly):
  - Dark/light mode toggle
  - Step timeline with color-coded status
  - Embedded screenshots inline with failing steps
  - Embedded video player for failed tests
  - DOM snapshot viewer (click any step → see the page state)
  - Network request log per test
  - Search, filter, sort tests
  - Responsive, mobile-friendly
- [ ] **Flask dashboard** (`pyshaft report serve`):
  - Aggregate stats dashboard: pass/fail trends, slowest tests, flaky tests
  - Run comparison (side-by-side): pick two runs, see diffs
  - Full-text search across all historical runs
  - Live progress view via Server-Sent Events (SSE)
  - Responsive, modern UI (like Playwright report, better than Allure)
- [ ] **Live progress** (SSE-based):
  - Open report page while tests are running
  - Steps appear in real-time, live pass/fail count, duration updates
  - No WebSocket needed — SSE works with Flask out of the box
- [ ] JSON + JUnit XML writers
- [ ] pytest-pyshaft plugin: `--pyshaft-report` flag
- [ ] GitHub Actions example workflow

### Phase 7 — Weeks 13–14: Release
**Goal**: `pip install pyshaft` — v1.0 public launch.

- [ ] README + quickstart + example test suite
- [ ] MkDocs Material documentation site
- [ ] PyPI publish + GitHub release with changelog
- [ ] CI pipeline for PyShaft itself (self-dogfooding)
- [ ] **Test Recorder** — `pyshaft record` opens browser, records actions, generates Python test code
- [ ] **CLI commands**:
  - `pyshaft run` — run tests with config
  - `pyshaft run --demo` — demo mode (highlight + slow execution)
  - `pyshaft run --tags=smoke,api` — filter tests by tags
  - `pyshaft run --data=users.csv` — data-driven testing from CSV/JSON
  - `pyshaft record` — test recorder
  - `pyshaft report serve` — Flask dashboard
  - `pyshaft grid start` — start Selenium Grid hub/node
- [ ] **Cloud storage integration** — `--with-s3` uploads reports/screenshots to AWS S3
- [ ] **Selenium Grid support** — `--grid-url` runs tests on remote grid, hub/node management
- [ ] **@retry_on_exception decorator** — per-method retry with configurable exceptions
- [ ] **Data-driven testing** — `@data_from_csv("users.csv")`, `@data_from_json("scenarios.json")` — runs same test with N data rows
- [ ] **Tagging** — `@tag("smoke")`, `@tag("api", "regression")`, `pyshaft run --tags=smoke,api`
- [ ] **Secrets management** — `get_secret("DB_PASSWORD")` — reads from env vars, `.env` file, or vault (AWS Secrets Manager, HashiCorp Vault)
- [ ] **PDF testing** — `assert_pdf_text("invoice.pdf", "Invoice #123")`, `extract_pdf_text("report.pdf") → str`
- [ ] **Visual diff** — `assert_no_visual_change("homepage")` — pixel-by-page screenshot comparison against baseline

---

## 🚀 Full Roadmap

### v1.0 — Build Now
- Dual locator engine (semantic 11-chain + CSS/XPath + shadow DOM)
- Auto-wait pipeline (overlay-aware, zero config, toggleable)
- pyshaft.web (45+ web functions — alerts, collections, keyboard, tables, dates, downloads)
- pyshaft.api (30+ functions — REST + GraphQL + OAuth 2.0 + pagination + multipart)
- Configurable scope (session/module/function)
- Parallel execution via pytest-xdist
- Retry attempts on failure (configurable)
- Validation guards (visibility, locator uniqueness, text verification, navigation check)
- JS click fallback
- **Advanced utilities**:
  - Deferred assertions — batch multiple checks, report all failures at once
  - JS helpers — jQuery activation, highlight, set value, get text
  - Mobile emulation — iPhone/Pixel device override via DevTools
  - Ad/image blocking — Chrome extension or JS-based
  - Proxy support — HTTP/SOCKS5, authenticated, multi-proxy
  - Demo mode — highlight elements, slow execution, step names visible
  - Session reuse — multi-test state management
  - @retry_on_exception — per-method retry
  - Data-driven testing — @data_from_csv, @data_from_json
  - Tagging — @tag("smoke"), run --tags=smoke
  - Secrets management — env vars, .env, vault integration
  - PDF testing — assert_pdf_text, extract_pdf_text
  - Visual diff — assert_no_visual_change with baselines
- **Hybrid report engine**:
  - Self-contained HTML file (open directly, no server)
  - Flask dashboard (`pyshaft report serve`) with aggregate stats
  - SQLite history DB — run comparison, flaky tests, trends
  - DOM snapshot viewer per step
  - Embedded video + screenshots
  - Live progress via SSE
  - Search, filter, sort across all runs
  - Network request log per test
- **CLI & Tooling**:
  - `pyshaft run` — run tests with config
  - `pyshaft record` — test recorder (browser actions → Python code)
  - `pyshaft report serve` — Flask dashboard
  - Selenium Grid support (`--grid-url`, hub/node management)
  - AWS S3 integration (`--with-s3`)
- `pip install pyshaft` — PyPI v1.0.0

### v2.0 — After Launch
- Page Object helper (optional POM pattern)
- GraphQL testing (`send_query`, `assert_gql`)
- Visual regression (pixel diff screenshots)
- Mobile (Appium) — same API on Android/iOS
- AI locator fallback (LLM suggests fixes)
- Full async support (pytest-asyncio + httpx async)
- Report: historical trend charts, custom dashboards, email/Slack notifications

### v3.0 — Future
- Self-healing tests (auto-recover broken locators)
- Accessibility testing (axe-core built in)
- Cloud grid (BrowserStack / Sauce adapter)
- VS Code extension (IntelliSense for PyShaft)
- Test recorder (browser → PyShaft code)
- Dashboard UI (historical trend analysis, team sharing)
- AI test generator (spec → test code)
- Report: multi-project aggregation, SSO, RBAC

---

## 📋 Dependencies

### Core
- `selenium` ≥ 4.0 — WebDriver
- `webdriver-manager` — automatic browser driver management
- `httpx` — HTTP client for API testing
- `flask` — Flask dashboard server (optional, for `pyshaft report serve`)
- `lxml` — fast HTML parsing for DOM snapshots
- `python-dotenv` — .env file loading for secrets

### Testing
- `pytest` ≥ 7.0
- `pytest-asyncio` — optional async support
- `pytest-xdist` — parallel execution
- `pytest-rerunfailures` — retry failed tests

### Reporting
- `jinja2` — HTML report templating (already a Flask dep)
- `jsonschema` — JSON schema validation for API assertions
- `ffmpeg-python` (optional) — video trimming for `video_on_fail`

### Utilities
- `boto3` (optional) — AWS S3 upload integration
- `selenium-wire` (optional) — network request interception
- `selenium-grid` — Selenium Grid hub/node management
- `pypdf` (optional) — PDF text extraction
- `Pillow` — image comparison for visual diff
- `pyotp` (optional) — TOTP 2FA codes for auth testing

### Build / Docs
- `build` — pyproject build backend
- `mkdocs-material` — documentation site
- `twine` — PyPI publishing

---

## 🎯 Phase 1 Deliverable

A working `pyshaft/` repo with:
```python
from pyshaft.web import open_url, assert_title

open_url("https://google.com")
assert_title("Google")
```

- Package installs via `pip install -e .`
- Expanded `pyshaft.toml` config loading works (7 sections, zero required fields)
- Shared session opens browser and persists (parallel-worker isolated)
- `pytest` runs the first test successfully
- Scope configurable (session/module/function)
- `@pytest.mark.pyshaft_scope` marker works
- `force_navigation_check` verifies page loaded after `open_url()`
- JS click fallback active (`js_click_fallback = true`)
- Headless mode configurable (`headless = true/false`)
- `respect_native_waits` controls auto-wait pipeline
- **Report infrastructure ready**: SQLite DB auto-created, StepCollector captures steps, DOM snapshot capture stub, video recording stub
- **CLI ready**: `pyshaft run` and `pyshaft report serve` stubs working
