# PyShaft — Handoff Context for Continuation

> **Read this first.** This document contains everything a new AI needs to continue building PyShaft.

---

## Project Summary

**PyShaft** is a Python test automation framework. It provides:

1. **Web testing** — `w.click(role, button)` with semantic locators, auto-wait, fluent chaining
2. **API testing** — `api.get("/users/1").assert_status(200).assert_json("name", "Alice")`
3. **Recorder GUI** — A PyQt6 IDE for visually recording browser interactions into PyShaft test code

- **Location**: `d:\automation\me\pyshaft\`
- **Python**: 3.10+
- **Install**: `pip install -e .` (development) or `pip install -e .[recorder]` (with GUI)
- **Run tests**: `pytest tests/ -v`
- **Launch Recorder**: `pyshaft inspect` or `pyshaft record`

---

## What's DONE — All Phases

### Phase 1 — Foundation ✅

- Package skeleton with `pyproject.toml` (hatchling build)
- Config system (`pyshaft/config.py`) — 7 TOML sections, env var overrides
- Session management (`pyshaft/session.py`) — thread-local driver storage
- Driver factory (`pyshaft/core/driver_factory.py`) — Chrome/Firefox/Edge
- Pytest plugin (`pytest_pyshaft/plugin.py`) — auto-use fixtures, scope markers
- Action runner pipeline (`pyshaft/core/action_runner.py`) — locate→wait→execute→log
- Step logger (`pyshaft/core/step_logger.py`)
- CLI (`pyshaft/cli.py`) — `pyshaft run`, `pyshaft inspect`, `pyshaft record`, `pyshaft report serve`
- Custom exceptions (`pyshaft/exceptions.py`)
- Utilities (`pyshaft/utils.py`) — data_from_csv, data_from_json, retry, test_tag

### Phase 2 — Dual Locator Engine ✅

- 10-strategy semantic chain in `pyshaft/core/locator.py`
- Strategies: ARIA, exact/partial text, placeholder/label, ID slugs, data-testid, title/alt/name, near (proximity), inside (structural), ordinal (positional), shadow DOM
- LRU cache, best-match selection

### Phase 3 — Auto-Wait Engine ✅

- 4-check pipeline in `pyshaft/core/wait_engine.py`: visible, enabled, position stable, not covered
- Network idle wait (XHR/fetch interception)
- DOM stability wait (MutationObserver)
- Public wait API in `pyshaft/web/waits.py`

### Phase 4 — pyshaft.web (Full Suite) ✅

All web modules created in `pyshaft/web/`:

- `navigation.py` — open_url, go_back, go_forward, refresh, scroll, scroll_to_bottom, get_url, get_title
- `interactions.py` — click, double_click, right_click, hover, drag_to, click_all
- `inputs.py` — type_text, clear_text, press_key, upload_file, select_option, check, uncheck, get_text, get_value
- `assertions.py` — assert_title, assert_url, assert_text, assert_visible, assert_hidden, assert_enabled, assert_disabled, assert_checked, assert_contain_title, assert_contain_url, assert_contain_text, assert_contain_attribute
- `waits.py` — wait_for_text, wait_for_visible, wait_for_hidden, wait_for_element, wait_until, wait_for_url, wait_for_title
- `alerts.py` — accept_alert, dismiss_alert, get_alert_text, type_alert
- `collections.py` — count, get_all, first, last, nth
- `keyboard.py` — hotkey, press_combo
- `storage.py` — get/set/clear local storage and session storage
- `screenshot.py` — take_screenshot with auto-naming
- `tables.py` — get_cell, get_row_count, get_column, assert_cell_text
- `js_helpers.py` — activate_jquery, highlight_element, set_value_via_js
- `locators.py` — **Fluent Locator class** with `.filter()`, `.inside()`, `.nth()`, `.execute()`, and **ActionProxy** for chaining

#### Fluent API (WebEngine — `pyshaft/web/__init__.py`)

The `WebEngine` class is the core singleton (`w = WebEngine()`). It provides:

- **Lazy execution**: Actions build a `Locator` with a pending action, executed on next call or `.flush()`
- **Chaining**: `w.click(role, button).type("hello", role, textbox).assert_visible(role, modal)`
- **Constants**: `role, text, label, placeholder, testid, id_, cls, css_, xpath, tag, attr, any_`
- **Element types**: `button, textbox, input_, checkbox, radio, link, dialog, modal, form, heading, ...`
- **Modifiers**: `exact, contain, starts, contains`
- **Smart \_build_loc**: Handles `(selector)`, `(type, value)`, and `(type, modifier, value)` patterns

### Phase 5 — pyshaft.api (REST API Testing) ✅

API modules in `pyshaft/api/`:

- `client.py` — httpx session with base_url
- `methods.py` — send_get, send_post, send_put, send_patch, send_delete
- `response.py` — ApiResponse with chainable assertions (assert_status, assert_json, assert_json_path, assert_json_type, assert_json_contains, assert_json_in_array, for_each, for_each_key, prettify)
- `builder.py` — RequestBuilder for fluent request building (method, url, param, header, body, with_data, perform_each)
- `store.py` — extract_json, store, stored (cross-request data sharing)
- `__init__.py` — ApiEngine singleton with stateful builder pattern

#### API Engine Pattern

```python
from pyshaft import api

# Fluent chain
api.get("/users/1").assert_status(200).assert_json("name", "Alice")

# Stateful builder
api.request("POST", "/users")
api.body(name="Bob")
api.assert_status(201)
api.extract_json("id", "new_user_id")

# Template filling
payload = api.fill({"name": "{{name}}", "age": "{{age}}"}, name="Bob", age=30)
```

### Phase 6 — Recorder GUI ✅ (Functional, needs polish)

Full PyQt6 recorder application in `pyshaft/recorder/`:

| File                          | Purpose                                                              |
| ----------------------------- | -------------------------------------------------------------------- |
| `app.py`                      | Application entry point, initializes QApplication                    |
| `main_window.py` (1122 lines) | Main window with 3-panel dock layout, ultra-compact toolbar          |
| `browser_bridge.py`           | WebSocket bridge between PyQt6 WebEngine and Chrome DevTools         |
| `code_generator.py`           | Converts recorded steps → PyShaft code (flat, chain, POM modes)      |
| `command_palette.py`          | VS Code-style Ctrl+K command palette                                 |
| `element_popup.py`            | Floating popup on element click with action/assertion buttons        |
| `inspector_panel.py`          | Right dock — shows element details, locator suggestions              |
| `step_list_panel.py`          | Left dock — displays recorded steps with drag/drop, edit, delete     |
| `step_editor_dialog.py`       | Dialog for editing individual recorded steps                         |
| `workflow_view.py`            | Visual workflow diagram of recorded test steps                       |
| `io_manager.py`               | Save/load sessions (.pyshaft JSON format)                            |
| `models.py`                   | RecordedStep, RecordingSession, LocatorSuggestion dataclasses        |
| `theme.py`                    | Dark theme colors, fonts, icons, complete QSS stylesheet             |
| `js/inspector.js`             | Injected JS for element inspection (hover highlights, click capture) |
| `js/recorder.js`              | Injected JS for recording clicks, types, selects, scrolls            |

#### Recorder UI Layout

```
┌──────────────────────────────────────────────────────────────┐
│ [S] [I] [O]  │Insp▼│ 🔍 ⏺ ⏸ ⏹ │Zen│↺│ URL bar...  │Go│Name│
├──────────┬──────────────────────────────────┬────────────────┤
│ Steps    │     Integrated WebEngine         │   Inspector    │
│ (left    │     (center - browser view)      │   (right dock) │
│  dock)   │                                  │                │
├──────────┴──────────────────────────────────┴────────────────┤
│  Code  │  POM (test.py / page.py / data.py)  │  Workflow     │
│  (bottom dock with tabs)                                     │
└──────────────────────────────────────────────────────────────┘
```

Toolbar buttons:

- **S, I, O** — Single-letter toggles for Steps/Inspector/Outputs docks
- **Mode dropdown** — "Insp", "Rec", "Both"
- **🔍** — Inspector tool (element picker), highlights purple when active
- **⏺ ⏸ ⏹** — Icon-only record/pause/stop, record glows red when active
- **Zen** — Hide all sidebars
- **↺** — Restore all panels

### Phase 6b — Report Engine ✅
Included in `pyshaft/report/`:
- **collector.py**: StepCollector singleton that captures test steps during execution.
- **json_exporter.py**, **junit_writer.py**: CI integrations for JSON and XML summaries.
- **screenshot_capture.py**, **video_recorder.py**: Record screenshots and CDP screencasts on failure/step.
- **flask_app.py**: A self-contained Flask dashboard server (accessible via `pyshaft report serve`).

### Phase 6c — API Inspector GUI ✅
Included in `pyshaft/recorder/api_inspector/`:
- Visual workflow builder for consecutive API requests.
- Assertion panel, variable extraction logic, and Pipeline operations.
- Interactively builds and generates PyShaft fluent API test code.
- Launch with `pyshaft inspectapi`.

---

## File Structure

```
d:\automation\me\pyshaft\
├── pyshaft/
│   ├── __init__.py              # Top-level exports (web, api, constants)
│   ├── cli.py                   # CLI: run, inspect, record, report
│   ├── config.py                # TOML config, env overrides
│   ├── exceptions.py            # Custom exceptions
│   ├── session.py               # Thread-local driver session
│   ├── utils.py                 # Data providers, retry, tags
│   ├── core/
│   │   ├── action_runner.py     # run_action / run_driver_action pipeline
│   │   ├── driver_factory.py    # Browser driver creation
│   │   ├── locator.py           # 10-strategy semantic locator engine
│   │   ├── step_logger.py       # Step logging
│   │   └── wait_engine.py       # Auto-wait: visible, enabled, stable, uncovered
│   ├── web/
│   │   ├── __init__.py          # WebEngine singleton + Locator constants (879 lines)
│   │   ├── locators.py          # Fluent Locator class (661 lines)
│   │   ├── navigation.py        # URL, scroll, history
│   │   ├── interactions.py      # click, hover, drag
│   │   ├── inputs.py            # type, select, check, upload
│   │   ├── assertions.py        # assert_text, assert_visible, etc.
│   │   ├── waits.py             # wait_for_text, wait_for_visible, etc.
│   │   ├── alerts.py            # Browser alert handling
│   │   ├── collections.py       # count, get_all, first, last, nth
│   │   ├── keyboard.py          # hotkey, key combos
│   │   ├── storage.py           # localStorage, sessionStorage
│   │   ├── screenshot.py        # Screenshots
│   │   ├── tables.py            # Table operations
│   │   └── js_helpers.py        # jQuery, highlight, JS value set
│   ├── api/
│   │   ├── __init__.py          # ApiEngine singleton (273 lines)
│   │   ├── builder.py           # RequestBuilder for fluent requests
│   │   ├── client.py            # httpx session
│   │   ├── methods.py           # send_get/post/put/patch/delete
│   │   ├── response.py          # ApiResponse with assertion chain
│   │   └── store.py             # Cross-request data store
│   ├── report/              # Phase 6b Flask Reporting Engine
│   │   ├── __init__.py
│   │   ├── collector.py
│   │   ├── flask_app.py
│   │   ├── json_exporter.py
│   │   ├── junit_writer.py
│   │   ├── models.py
│   │   ├── screenshot_capture.py
│   │   ├── video_recorder.py
│   │   └── templates/       # Dashboards & reports
│   └── recorder/
│       ├── __init__.py
│       ├── app.py               # QApplication entry
│       ├── main_window.py       # Main window (1122 lines)
│       ├── browser_bridge.py    # WebSocket DevTools bridge
│       ├── code_generator.py    # Steps → code (flat/chain/POM)
│       ├── command_palette.py   # Ctrl+K palette
│       ├── element_popup.py     # Floating action popup
│       ├── inspector_panel.py   # Element inspector dock
│       ├── step_list_panel.py   # Step list dock
│       ├── step_editor_dialog.py # Step editing dialog
│       ├── workflow_view.py     # Visual workflow diagram
│       ├── io_manager.py        # Session save/load
│       ├── models.py            # Data models
│       ├── theme.py             # Dark theme + QSS
│       ├── js/
│       │   ├── inspector.js     # Element inspection script
│       │   └── recorder.js      # Event capture script
│       └── api_inspector/       # API inspector GUI module
│           ├── api_main_window.py
│           ├── api_models.py
│           ├── api_assertion_panel.py
│           ├── api_code_generator.py
│           ├── api_io_manager.py
│           └── api_json_viewer.py
├── pytest_pyshaft/
│   ├── __init__.py
│   └── plugin.py                # Pytest plugin (fixtures, markers)
├── tests/
│   ├── unit/                    # Unit tests (no browser)
│   ├── integration/             # Integration tests
│   └── examples/                # Example tests
├── pyproject.toml               # Build config, deps, entry points
├── pyshaft.toml                 # Default framework config
├── how.md                       # Usage guide (738 lines)
└── README.md
```

---

## Key Patterns to Follow

### 1. Web actions use the action pipeline

```python
# Element-level action
from pyshaft.core.action_runner import run_action
def click(locator: str) -> None:
    run_action("click", locator, lambda el: el.click())

# Driver-level action
from pyshaft.core.action_runner import run_driver_action
def open_url(url: str) -> None:
    run_driver_action("open_url", url, lambda driver: driver.get(url))
```

### 2. WebEngine fluent pattern

```python
# Every WebEngine method either:
# (a) Returns self (WebEngine) for immediate actions
# (b) Returns a Locator for lazy/chainable actions via _register_action

def click(self, locator_type, value, **filters) -> Locator:
    loc, _ = self._build_loc(locator_type, value, **filters)
    loc._action = "click"
    return self._register_action(loc)

def open_url(self, url) -> WebEngine:
    self.flush()
    self._execute_with_retry(lambda: navigation.open_url(url))
    return self
```

### 3. API Engine stateful pattern

```python
# The ApiEngine holds a _current_builder (RequestBuilder)
# Builder methods modify state, assert methods trigger execution
api.request("POST", "/users")
api.body(name="Bob")           # modifies builder state
api.assert_status(201)         # triggers execute + assert
```

### 4. Config / Session access

```python
from pyshaft.config import get_config
from pyshaft.session import session_context
config = get_config()
driver = session_context.driver
```

### 5. Recorder code generation

The recorder converts `RecordedStep` objects to code via `code_generator.py`.
Three modes: `flat` (one action per line), `chain` (fluent chaining), `pom` (page object model with test.py/page.py/data.py).

### 6. All functions need type hints and docstrings

### 7. Coding rules are in `d:\automation\me\rules.md`

---

## What's LEFT to Build

### Phase 7 — Release (NOT STARTED)

- Polish README with badges, screenshots
- Add comprehensive docs (mkdocs-material)
- CLI help improvements
- PyPI publish preparation

### Recorder — Known Issues & Improvements

- **Inspect mode quirks**: The element picker (🔍) sometimes loses state when switching between modes
- **Workflow diagram**: Basic connectivity works but could use drag-to-reorder and visual polish
- **Code generation**: POM mode needs testing with complex multi-page scenarios
- **Browser bridge**: WebSocket connection to DevTools can be fragile on Edge
- **Missing features**: No undo/redo shortcut indicators in the toolbar, no recent sessions list
- **Test coverage**: The recorder module has no automated tests

### Web Module — Gaps

- `deferred.py` — defer_assert_text, defer_assert_visible, check_deferred (soft assertions — NOT BUILT)
- `downloads.py` — wait_for_download, get_downloaded_file (NOT BUILT)

---

## How to Test

```bash
cd d:\automation\me\pyshaft

# Unit tests (no browser)
pytest tests/unit/ -v

# Integration tests (opens browser)
pytest tests/examples/ -v

# All tests
pytest -v

# Launch recorder
pyshaft inspect          # Inspector mode
pyshaft record           # Recording mode
pyshaft inspect --url https://example.com
```

---

## Dependencies

**Core**: selenium, webdriver-manager, httpx, pytest, jinja2, jsonpath-ng
**Recorder (optional)**: PyQt6, PyQt6-WebEngine, websocket-client
**Dev**: ruff, mypy, mkdocs-material

Install: `pip install -e .[recorder]` for full development with GUI.
