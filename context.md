# PyShaft — Project Context

> **What is PyShaft?** A Python test automation framework that reads like English. Write `click("Login button")` instead of wrestling with selectors. Auto-wait, smart locators, modern reports.

---

## 🎯 Problem Statement

Traditional Selenium tests are brittle and hard to maintain:
- XPath/CSS selectors break on every UI change
- Explicit waits (`time.sleep`, `WebDriverWait`) scattered everywhere
- No built-in reporting — failures give no context
- Session management is manual and error-prone
- Tests are slow and flaky

PyShaft solves all of this with:
- **Semantic locators** — describe what you want in English
- **Auto-wait** — every action waits silently for the right conditions
- **Modern reports** — HTML timeline with embedded screenshots
- **Configurable sessions** — shared by default, isolated when needed
- **10-strategy resolution chain** — covers every XPath use case in plain English

---

## 🏗️ High-Level Architecture

```
User writes: click("Login button")
        │
        ▼
┌─────────────────────────────────────┐
│  Auto-Detect Mode                   │
│  "Login button" → semantic          │
│  "#login-btn"   → raw CSS           │
│  "//button..."  → XPath             │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Semantic Resolution Chain (10 steps)│
│  1. ARIA role + name                │
│  2. Exact visible text              │
│  3. Partial visible text            │
│  4. Placeholder / label             │
│  5. ID contains text                │
│  6. data-testid / data-qa / data-cy │
│  7. Title / alt / name              │
│  8. Relative/near proximity         │
│  9. Parent/ancestor chain           │
│  10. Index/ordinal position         │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Auto-Wait Pipeline                 │
│  ✓ Found in DOM                    │
│  ✓ Visible                         │
│  ✓ Enabled                         │
│  ✓ Position stable (300ms)         │
│  ✓ Not covered by overlay          │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Execute: driver.click()            │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Log Step: name, duration, screenshot│
└─────────────────────────────────────┘
```

---

## 📦 Package Structure

```
pyshaft/                          ← root repo
├── pyshaft/                      ← main package
│   ├── __init__.py               # __version__, public re-exports
│   ├── config.py                 # pyshaft.toml loader + Config dataclass
│   ├── session.py                # thread-local SessionContext
│   ├── core/                     # core engine modules
│   │   ├── driver_factory.py     # Chrome/Firefox/Edge via webdriver-manager
│   │   ├── locator.py            # DualLocator: 10-chain + auto-detect + cache
│   │   ├── wait_engine.py        # WaitEngine: visible/stable/overlay checks
│   │   ├── action_runner.py      # locate → wait → execute → log pipeline
│   │   └── step_logger.py        # step name/time/screenshot capture
│   ├── web/                      # web automation (35+ functions)
│   │   ├── __init__.py           # exports all public functions
│   │   ├── navigation.py         # open_url, go_back, go_forward, refresh
│   │   ├── interactions.py       # click, double_click, hover, drag_to
│   │   ├── inputs.py             # type_text, clear_text, press_key, upload_file
│   │   ├── assertions.py         # assert_text, assert_visible, assert_url, ...
│   │   ├── windows.py            # switch_to_frame, switch_to_window
│   │   └── screenshot.py         # take_screenshot
│   ├── api/                      # REST API testing (25+ functions)
│   │   ├── __init__.py           # exports all public functions
│   │   ├── client.py             # httpx session + base_url + auth
│   │   ├── methods.py            # send_get, send_post, send_put, ...
│   │   ├── assertions.py         # assert_status, assert_json, assert_json_schema
│   │   └── store.py              # extract_json, store, stored (value chaining)
│   └── report/                   # reporting engine
│       ├── collector.py          # StepCollector singleton
│       ├── html_renderer.py      # dark/light HTML report with timeline
│       ├── json_exporter.py      # JSON summary
│       └── junit_writer.py       # JUnit XML for CI
│
├── pytest_pyshaft/               ← pytest plugin (separate installable)
│   ├── plugin.py                 # session/module/function fixtures + markers
│   └── hooks.py                  # pytest_runtest_* hooks for step capture
│
├── tests/                        ← test suite
│   ├── unit/                     # locator, wait, config unit tests
│   ├── integration/              # real browser + real API tests
│   └── examples/                 # sample tests (login, API CRUD, mixed)
│
├── docs/                         ← MkDocs Material documentation
├── pyproject.toml                # package config + dependencies
├── pyshaft.toml                  # default config for examples
└── README.md                     # project README
```

---

## 🔧 Configuration System

One `pyshaft.toml` file, zero required fields. All defaults are sensible.

```toml
# ── Browser ────────────────────────────────────────────────────
[browser]
browser = "chrome"              # chrome | firefox | edge
headless = false                # true in CI, false locally
window_size = "1920x1080"       # WxH string
base_url = ""                   # prefix for all open_url()
navigation_timeout = 30           # seconds for page load

# ── Execution ──────────────────────────────────────────────────
[execution]
parallel = false                # enable pytest-xdist parallel mode
workers = "auto"                # number of workers (auto | int)
retry_attempts = 0              # retry failed tests N times (0 = off)
scope = "session"               # session | module | function

# ── Waits ──────────────────────────────────────────────────────
[waits]
default_element_timeout = 10    # seconds to find/wait for elements
polling_interval = 0.25         # check every N seconds
stability_threshold = 0.3       # element position must be still N sec
network_idle_timeout = 3        # wait for network quiet on navigation
navigation_timeout = 30         # max time for page load
respect_native_waits = true     # false = skip auto-wait (raw Selenium)

# ── Validations ────────────────────────────────────────────────
[validations]
force_element_visibility = true  # every interaction requires element visible
force_locator_unique = true      # error if locator matches >1 element
force_text_verification = false  # after type_text, verify text was entered
force_navigation_check = true    # after open_url, verify page loaded

# ── Actions ────────────────────────────────────────────────────
[actions]
js_click_fallback = true         # if WebDriver click fails, try JS click

# ── Report ─────────────────────────────────────────────────────
[report]
output_dir = "pyshaft-report"
screenshot_on_fail = true
screenshot_on_step = false
video_on_fail = false            # record video, trim to failed test
junit_xml = true
json_report = true

# ── API ────────────────────────────────────────────────────────
[api]
base_url = ""                   # prefix for all send_*()
timeout = 30                    # request timeout
verify_ssl = true               # SSL cert verification
```

### Config → Module Mapping

| Config Section | Modules Affected | Key Behaviors |
|---|---|---|
| `[browser]` | `driver_factory.py` | Browser choice, headless, window size, base URL, nav timeout |
| `[execution]` | `plugin.py`, `hooks.py`, `session.py` | Parallel (pytest-xdist), retry (pytest-rerunfailures), scope |
| `[waits]` | `wait_engine.py`, `action_runner.py` | Auto-wait pipeline, polling, stability, network idle, toggle |
| `[validations]` | `locator.py`, `wait_engine.py`, `inputs.py`, `navigation.py` | Visibility enforcement, uniqueness check, text verify, nav check |
| `[actions]` | `action_runner.py` | JS click fallback when WebDriver click fails |
| `[report]` | `step_logger.py`, `collector.py`, `html_renderer.py` | Screenshot/video capture, HTML/JSON/JUnit output |
| `[api]` | `client.py` | Base URL, timeout, SSL verification |

---

## 🧪 Public API (v1.0)

### Web (`from pyshaft.web import ...`)
```python
# Navigation
open_url, go_back, go_forward, refresh, get_url, get_title

# Interaction
click, double_click, right_click, hover, drag_to, drag_by_offset

# Input
type_text, clear_text, press_key, upload_file, set_date

# Keyboard
hotkey, press_combo, hold, press, release

# Alerts & Dialogs
accept_alert, dismiss_alert, get_alert_text, type_alert, handle_auth

# Selection
select_option, check_checkbox, uncheck_checkbox, get_text, get_value

# Collections
count, get_all, first, last, nth

# Tables
get_cell, get_row_count, get_column, assert_cell_text

# Scroll
scroll_to, scroll_to_bottom, scroll_by

# Frames / Windows
switch_to_frame, switch_to_main, switch_to_window, close_tab, open_new_tab, close_all_tabs

# Storage
get_local_storage, set_local_storage, clear_local_storage
get_session_storage, set_session_storage, clear_session_storage

# Downloads
wait_for_download, get_downloaded_file

# Assertions
assert_text, assert_visible, assert_hidden, assert_url, assert_title,
assert_attribute, assert_enabled, assert_disabled, assert_checked, assert_not_checked

# Deferred Assertions
defer_assert_text, defer_assert_visible, defer_assert_element, check_deferred, clear_deferred

# Wait
wait_for_text, wait_for_visible, wait_until

# Utilities
take_screenshot, execute_js, get_cookies, set_cookie
activate_jquery, highlight_element, set_value_via_js, get_text_content

# Blocking & Proxy
block_ads, block_images, unblock_images
set_proxy, clear_proxy

# Mobile
open_mobile, set_mobile_device, reset_to_desktop
```

### API (`from pyshaft.api import ...`)
```python
# Setup
set_base_url, set_headers, set_auth, set_timeout, clear_headers

# OAuth 2.0
oauth2_client_credentials, oauth2_password_grant

# Requests
send_get, send_post, send_put, send_patch, send_delete, send_request
send_file, send_multipart

# GraphQL
send_query, send_mutation, assert_gql_errors

# Pagination & Download
get_all_pages, download_file

# Assertions
assert_status, assert_json, assert_json_schema,
assert_header, assert_response_time,
assert_body_contains, assert_body_not_contains

# Cookie Jar
get_api_cookies, set_api_cookies

# Extraction + Chaining
extract_json, extract_header, store, stored,
get_response, get_status_code, get_response_time
```

### Utilities (`from pyshaft.utils import ...`)
```python
# Retry
@retry_on_exception(ExceptionType, max_attempts=3, backoff=1.5)

# Tagging
@tag("smoke", "api", "regression")

# Data-Driven
@data_from_csv("users.csv")
@data_from_json("scenarios.json")

# Secrets
get_secret("DB_PASSWORD")

# PDF
assert_pdf_text("invoice.pdf", "Invoice #123")
extract_pdf_text("report.pdf") → str

# Visual Diff
assert_no_visual_change("homepage")
```

---

## 🔄 Session Model

| Scope | Behavior | Best For |
|-------|----------|----------|
| **session** (default) | One browser for all tests. Fastest. Tests share cookies/state. | Regression suites, read-heavy tests |
| **module** | New browser per test file. Good balance. | Feature-grouped test files |
| **function** | New browser per test. Fully isolated. Slowest. | Auth tests, destructive operations |

**Parallel mode**: When `execution.parallel = true`, each pytest-xdist worker gets its own isolated browser session. Sessions are keyed by worker ID — no cross-worker state sharing.

Per-test override:
```python
import pytest

@pytest.mark.pyshaft_scope("function")
def test_delete_account():
    open_url("https://app.example.com")
    click("Delete my account")
    assert_text("Account deleted")
```

---

## ⏳ Auto-Wait Pipeline

Runs silently before every web action:

```
call: click("Login button")
  │
  ├─ 1. DETECT MODE ─────────── "Login button" → semantic
  ├─ 2. RESOLVE LOCATOR ──────── 10-chain → By.cssSelector("button[aria-label='Login']")
  ├─ 3. WAIT LOOP (250ms polls, 10s timeout)
  │      ✓ Element found in DOM
  │      ✓ Visible (not display:none, not opacity:0)
  │      ✓ Not disabled (no disabled attr)
  │      ✓ Position stable for 300ms
  │      ✓ Not covered by overlay/modal
  │       → TimeoutError with state snapshot if fails
  ├─ 4. EXECUTE ──────────────── driver.click()
  └─ 5. LOG STEP ─────────────── name, duration, screenshot (if fail)
```

---

## 📋 Dependencies

| Category | Package | Purpose |
|----------|---------|---------|
| **Core** | `selenium` ≥ 4.0 | WebDriver |
| **Core** | `webdriver-manager` | Automatic browser driver management |
| **Core** | `httpx` | HTTP client for API testing |
| **Testing** | `pytest` ≥ 7.0 | Test framework |
| **Testing** | `pytest-asyncio` | Optional async support |
| **Reporting** | `jinja2` | HTML report templating |
| **Reporting** | `jsonschema` | JSON schema validation |
| **Build** | `build` | pyproject build backend |
| **Build** | `mkdocs-material` | Documentation site |
| **Build** | `twine` | PyPI publishing |

---

## 🚀 Roadmap

### v1.0 — Build Now
Dual locator (10-chain + CSS/XPath), auto-wait, web API, REST API, configurable sessions, modern reports, PyPI launch.

### v2.0 — After Launch
Page Object helper, GraphQL testing, parallel execution, visual regression, mobile (Appium), AI locator fallback, async support.

### v3.0 — Future
Self-healing tests, accessibility testing, cloud grid, VS Code extension, test recorder, dashboard UI, AI test generator.

---

## 📌 Key Design Principles

1. **Zero required config** — everything has a sensible default
2. **Read like English** — `click("Login button")` not `driver.find_element(By.XPATH, "//button[@id='submit']")`
3. **Auto-wait built in** — no `time.sleep()` or `WebDriverWait` ever needed (toggleable via `respect_native_waits`)
4. **Thread-safe** — shared session uses `threading.local()`, parallel-ready with worker isolation
5. **Fail loud with context** — screenshot + video + full strategy dump on every error
6. **Extensible** — plugin system for custom fixtures and hooks
7. **Resilient actions** — JS click fallback, retry attempts, text verification, navigation checks
8. **Validation guards** — enforce visibility, locator uniqueness, text correctness, navigation success
9. **Interactive reports** — hybrid: static HTML file + Flask dashboard with SQLite history, live progress, DOM snapshots

---

## 📊 Report Engine Architecture

### Two Modes
| Mode | How to View | Features | Best For |
|------|------------|----------|----------|
| **Static HTML** | Open `pyshaft-report/index.html` in browser | Single run view, step timeline, screenshots, video, DOM snapshots, search/filter | Quick inspection, sharing, CI artifacts |
| **Flask Dashboard** | `pyshaft report serve` → `http://localhost:8080` | Historical trends, run comparison, full-text search, live progress, analytics | Deep analysis, team collaboration, flaky test tracking |

### SQLite History DB (`pyshaft_history.db`)
Auto-created, zero config. Schema:
```
runs      → id, timestamp, duration_ms, passed, failed, skipped, total, git_hash, env
tests     → id, run_id, name, file, status, duration_ms, error, screenshot_path, video_path
steps     → id, test_id, action, locator, duration_ms, status, dom_snapshot, error
network   → id, test_id, url, method, status_code, duration_ms
```

### Live Progress (SSE)
- Open report page while tests are running → see steps appear in real-time
- No WebSocket — uses Server-Sent Events (simpler, Flask-native)
- Live counters, estimated time remaining, auto-scroll to latest step

### DOM Snapshots
- Before every step: capture `document.documentElement.outerHTML` (compressed, ~5-10KB)
- Viewer: sandboxed iframe renders snapshot at that exact moment
- Inspect mode: hover highlights, click to copy CSS selector
- Network log: all HTTP requests captured during test, color-coded by status

### UI Tech Stack
- **Zero external JS dependencies** — vanilla JS, no React/Vue/jQuery
- CSS Grid + Flexbox for responsive layout
- SVG for charts (donut, bar, line) — no chart library needed
- Jinja2 templates for server-rendered Flask views
- Same CSS used by both static HTML and Flask dashboard (DRY)

---

## 🛠️ Advanced Utilities (SeleniumBase-Inspired)

### Deferred Assertions
Batch multiple checks, report all failures at once instead of failing on the first one:
```python
from pyshaft.web import defer_assert_text, defer_assert_visible, check_deferred

def test_dashboard():
    defer_assert_visible("Dashboard title")
    defer_assert_text("Welcome, Admin")
    defer_assert_text("5 pending orders")
    check_deferred()  # raises DeferredAssertionError listing ALL failed checks
```

### JS Helpers
```python
from pyshaft.web import activate_jquery, highlight_element, set_value_via_js

activate_jquery()              # injects jQuery 3.7 if not present
highlight_element("#submit")   # red border for visual debugging
set_value_via_js("#email", "test@example.com")  # bypasses normal typing
```

### Mobile Emulation
```python
from pyshaft.web import open_mobile, set_mobile_device

open_mobile("https://m.example.com", device="iPhone 14")
# Later: switch to tablet
set_mobile_device("iPad Pro")
```
- Device presets: iPhone 14, iPhone SE, Pixel 7, Pixel 5, Galaxy S23, iPad Pro
- Uses Chrome DevTools `Emulation.setDeviceMetricsOverride` + `Network.setUserAgentOverride`

### Ad/Image Blocking
```python
from pyshaft.web import block_ads, block_images

block_ads()      # Chrome extension blocks known ad domains
block_images()   # Disables image loading (faster tests, less bandwidth)
```

### Proxy Support
```python
from pyshaft.web import set_proxy

set_proxy("http://proxy:8080")                        # HTTP proxy
set_proxy("http://user:pass@proxy:8080")             # Authenticated
set_proxy("socks5://proxy:1080")                     # SOCKS5
```

### Session Reuse & State Management
```python
from pyshaft.web import open_url, preserve_state, restore_state, clear_cookies

open_url("https://app.example.com")
click("Login")
type_text("Username", "admin")
click("Sign In")
preserve_state(keys=["cookies", "localStorage"])  # save login state

# In next test:
restore_state(keys=["cookies", "localStorage"])  # skip login, already authenticated
clear_cookies()  # clear but keep browser open
```

### @retry_on_exception Decorator
```python
from pyshaft.utils.retry import retry_on_exception

@retry_on_exception(ElementNotFoundError, max_attempts=3, backoff=1.5)
def test_flaky_element():
    click("Submit button")  # retries up to 3 times with 1.5x backoff
```

### Demo Mode
```bash
pyshaft run --demo
```
- Highlights each element before interaction (red border, 500ms)
- Slows execution between steps
- Prints step names to console: `>>> click "Login button" [PASS]`
- Perfect for presentations, debugging, teaching

### Test Recorder
```bash
pyshaft record --output=test_login.py
```
- Opens browser, records clicks, typing, navigation
- Generates PyShaft Python code with semantic locators
- Output: `click("Login")`, `type_text("Email", "user@example.com")`

### Selenium Grid Support
```bash
pyshaft grid start --hub                        # Start Grid hub
pyshaft grid start --node --browser=chrome      # Start Grid node
pyshaft run --grid-url=http://hub:4444          # Run tests on grid
```

### AWS S3 Integration
```bash
pyshaft run --with-s3
```
- Uploads: HTML report, screenshots, videos, JSON summary
- Configurable: `[report.s3] bucket="my-reports", prefix="pyshaft/"`
- Generates public URLs for sharing

### CLI Commands
| Command | Description |
|---------|-------------|
| `pyshaft run` | Run tests with config |
| `pyshaft run --demo` | Demo mode (highlight + slow) |
| `pyshaft run --headless` | Headless override |
| `pyshaft run --browser=firefox` | Browser override |
| `pyshaft run --grid-url=...` | Run on Selenium Grid |
| `pyshaft run --with-s3` | Upload to AWS S3 |
| `pyshaft record` | Test recorder |
| `pyshaft report serve` | Flask dashboard |
| `pyshaft grid start --hub` | Start Grid hub |
| `pyshaft grid start --node` | Start Grid node |
