# PyShaft — Module Specifications

> Detailed design for every module in the package. Each section maps to one file.

---

## 1. `pyshaft/__init__.py`

**Purpose**: Package entry point. Version string and public re-exports.

```python
__version__ = "0.1.0"

__all__ = [
    "config",
    "session",
    "web",
    "api",
    "report",
]
```

- Exposes `__version__` for `pyshaft.__version__`
- Re-exports commonly used items so users can do `from pyshaft import click` instead of `from pyshaft.web import click`

---

## 2. `pyshaft/config.py`

**Purpose**: Load, validate, and provide access to `pyshaft.toml` configuration.

### Exports
- `Config` — dataclass with all config sections
- `load_config(path: str | None = None) -> Config`
- `get_config() -> Config` — singleton accessor
- `reset_config() -> None` — for testing

### Config Dataclasses (7 sections)
```python
@dataclass
class BrowserConfig:
    browser: str = "chrome"              # chrome | firefox | edge
    headless: bool = False
    window_size: str = "1920x1080"
    base_url: str = ""
    navigation_timeout: float = 30.0

@dataclass
class ExecutionConfig:
    parallel: bool = False
    workers: str | int = "auto"
    retry_attempts: int = 0
    scope: str = "session"               # session | module | function

@dataclass
class WaitsConfig:
    default_element_timeout: float = 10.0
    polling_interval: float = 0.25
    stability_threshold: float = 0.3
    network_idle_timeout: float = 3.0
    navigation_timeout: float = 30.0
    respect_native_waits: bool = True

@dataclass
class ValidationsConfig:
    force_element_visibility: bool = True
    force_locator_unique: bool = True
    force_text_verification: bool = False
    force_navigation_check: bool = True

@dataclass
class ActionsConfig:
    js_click_fallback: bool = True

@dataclass
class ReportConfig:
    output_dir: str = "pyshaft-report"
    screenshot_on_fail: bool = True
    screenshot_on_step: bool = False
    video_on_fail: bool = False
    junit_xml: bool = True
    json_report: bool = True

@dataclass
class ApiConfig:
    base_url: str = ""
    timeout: float = 30.0
    verify_ssl: bool = True

@dataclass
class Config:
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    waits: WaitsConfig = field(default_factory=WaitsConfig)
    validations: ValidationsConfig = field(default_factory=ValidationsConfig)
    actions: ActionsConfig = field(default_factory=ActionsConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
```

### Config Resolution
1. Start with defaults (hard-coded)
2. Search for `pyshaft.toml` in cwd, then parent dirs (up to home)
3. Merge user config over defaults (deep merge)
4. Validate values (e.g., scope must be one of session/module/function, browser must be chrome/firefox/edge)
5. Apply environment variable overrides: `PYSHAFT_BROWSER=firefox` → overrides `[browser].browser`
6. Cache as singleton via `get_config()`

### Environment Variable Overrides
Format: `PYSHAFT_<SECTION>_<KEY>` (uppercase, underscore-separated)
```bash
PYSHAFT_BROWSER=firefox pytest
PYSHAFT_HEADLESS=true pytest
PYSHAFT_EXECUTION_RETRY_ATTEMPTS=3 pytest
PYSHAFT_REPORT_SCREENSHOT_ON_FAIL=false pytest
```

---

## 3. `pyshaft/session.py`

**Purpose**: Thread-local and worker-isolated browser session management.

### Exports
- `SessionContext` — thread-local + worker-ID keyed driver storage
- `get_session() -> SessionContext` — singleton accessor
- `close_all_sessions() -> None` — cleanup all workers

### SessionContext Class
```python
class SessionContext:
    _local = threading.local()

    @property
    def driver(self) -> WebDriver: ...
    @driver.setter
    def driver(self, value: WebDriver) -> None: ...

    @property
    def is_active(self) -> bool: ...
    @property
    def worker_id(self) -> str: ...  # from pytest-xdist or "main"

    def start(self, browser_name: str, **options) -> None: ...
    def close(self) -> None: ...
```

### Thread Safety & Parallel Execution
- Uses `threading.local()` — each thread has its own driver reference
- When `execution.parallel = true`: sessions keyed by `PYTEST_XDIST_WORKER` env var
- Worker IDs: `"gw0"`, `"gw1"`, etc. (pytest-xdist) or `"main"` (single-process)
- No cross-worker state sharing — each worker launches and manages its own browser
- Session state tracked per-worker: `active`, `browser_name`, `start_time`

---

## 4. `pyshaft/core/driver_factory.py`

**Purpose**: Create and configure browser driver instances with video recording support.

### Exports
- `DriverFactory` — creates Chrome/Firefox/Edge drivers

### DriverFactory Class
```python
class DriverFactory:
    @staticmethod
    def create(
        browser: str = "chrome",
        headless: bool = False,
        window_size: str = "1920x1080",
        video_on_fail: bool = False,
        **kwargs
    ) -> WebDriver: ...

    @staticmethod
    def _create_chrome(headless, window_size, video_on_fail, **kwargs) -> WebDriver: ...
    @staticmethod
    def _create_firefox(headless, window_size, **kwargs) -> WebDriver: ...
    @staticmethod
    def _create_edge(headless, window_size, **kwargs) -> WebDriver: ...
```

### Browser Options
- **Chrome**: `--disable-infobars`, `--no-sandbox`, `--disable-dev-shm-usage`, `--window-size=WxH`
- **Firefox**: `--width=W --height=H`, accept insecure certs for local testing
- **Edge**: same as Chrome (Chromium-based)
- **Headless**: `--headless=new` for Chrome, `headless=True` for Firefox
- **webdriver-manager** auto-downloads the correct driver version

### Video Recording Setup (Chrome only)
When `video_on_fail = true`:
```python
options = ChromeOptions()
options.add_experimental_option("prefs", {
    "download.default_directory": str(video_dir),
})
options.add_argument("--enable-logging")
options.add_argument("--v=1")
```
- After driver creation, start Chrome DevTools screencast via `driver.execute_cdp_cmd("Page.startScreencast", ...)`
- Saves frames to a buffer; on failure, encode to `.webm`
- On test pass, discard buffer (no disk I/O wasted on passing tests)

---

## 5. `pyshaft/core/locator.py`

**Purpose**: Dual locator engine with 11-strategy semantic chain (including shadow DOM) + CSS/XPath fallback.

### Exports
- `DualLocator` — main locator class
- `ElementNotFoundError` — raised when nothing matches
- `MultipleMatchWarning` — warned when multiple elements match
- `_detect_mode(text: str) -> str` — "raw" or "semantic"

### Detection Logic
```python
def _detect_mode(text: str) -> str:
    raw_css_signals = [
        text.startswith("#"),
        text.startswith("."),
        text.startswith("["),
        text.startswith("css="),
        ">" in text,
    ]
    xpath_signals = [
        text.startswith("//"),
        text.startswith(".//"),
        text.startswith("xpath="),
    ]
    if any(raw_css_signals): return "raw"
    if any(xpath_signals): return "raw"
    return "semantic"
```

### 10-Strategy Resolution Chain (semantic mode)
Each strategy returns `list[WebElement]`. First non-empty, single-match result wins.

| Step | Strategy | Selenium By | Example Input → Output |
|------|----------|-------------|----------------------|
| 1 | ARIA role + name | `By.CSS_SELECTOR` | `"Login button"` → `button[aria-label="Login"]` |
| 2 | Exact visible text | `By.XPATH` (text scan) | `"Submit"` → `//button[normalize-space()="Submit"]` |
| 3 | Partial visible text | `By.XPATH` (contains) | `"Login"` → `//button[contains(text(),"Login")]` |
| 4 | Placeholder / label | `By.CSS_SELECTOR` | `"Email"` → `input[placeholder*="Email"]` |
| 5 | ID contains text | `By.CSS_SELECTOR` | `"login"` → `#login, #loginBtn, #login-btn, #login_button` |
| 6 | data-testid / data-qa / data-cy | `By.CSS_SELECTOR` | `"login"` → `[data-testid*="login"], [data-qa*="login"], [data-cy*="login"]` |
| 7 | Title / alt / name | `By.CSS_SELECTOR` | `"logo"` → `[title*="logo"], [alt*="logo"], [name*="logo"]` |
| 8 | **Near/proximity** | JS execution | `"button near Email"` → find element, measure distance, pick closest |
| 9 | **Parent/ancestor** | CSS + descendant | `"button inside login form"` → `#login-form button`, `form[name="login"] button` |
| 10 | **Index/ordinal** | CSS `:nth-*` + JS | `"first submit button"` → `button[type="submit"]:nth-of-type(1)` |
| 11 | **Shadow DOM** | JS traversal | `"shadow > button"` → recursively walks `element.shadowRoot` |

### Relative/Near Strategy (step 8)
1. Resolve the reference element ("Email field") via steps 1–7
2. Get all candidate elements of the target type ("button")
3. Calculate screen distance between reference and each candidate
4. Return the closest one

### Parent/Ancestor Strategy (step 9)
1. Parse "X inside Y" or "X in Y"
2. Resolve Y via steps 1–7 (parent container)
3. Search for X as descendant within Y

### Index/Ordinal Strategy (step 10)
- Parse ordinal keywords: `first`, `second`, `third`, `last`, or numeric `1st`, `2nd`, `3`
- Map to CSS `:nth-of-type(n)` or JS array indexing

### Caching
```python
class LocatorCache:
    """LRU cache keyed by (description, current_url)."""
    def get(desc: str, url: str) -> WebElement | None: ...
    def put(desc: str, url: str, element: WebElement) -> None: ...
    def clear() -> None: ...
```
- Cache invalidates on URL change (navigation)
- Max 500 entries, evicts oldest

### force_locator_unique Integration
When `get_config().validations.force_locator_unique = true`:
- If any strategy returns >1 element → raise `MultipleMatchError` (not just warning)
- Error message includes all matched elements + strategies tried
- User can tighten description or switch to raw CSS/XPath

---

## 6. `pyshaft/core/wait_engine.py`

**Purpose**: Auto-wait before every action. Zero config. Toggleable via `respect_native_waits`.

### Exports
- `WaitEngine` — main wait orchestrator
- `wait_until(condition: Callable[[], bool], timeout: float | None = None) -> None`

### WaitEngine Class
```python
class WaitEngine:
    def wait_for_element(self, locator: By, value: str, timeout: float | None = None) -> WebElement: ...
    def wait_for_visible(self, element: WebElement, timeout: float | None = None) -> None: ...
    def wait_for_enabled(self, element: WebElement, timeout: float | None = None) -> None: ...
    def wait_for_stable(self, element: WebElement, threshold: float | None = None) -> None: ...
    def wait_for_not_covered(self, element: WebElement, timeout: float | None = None) -> None: ...
    def wait_for_network_idle(self, timeout: float | None = None) -> None: ...
```

### Wait Loop
```
poll every 250ms until timeout (default 10s):
    1. Element exists in DOM
    2. Element is visible (not display:none, not opacity:0, dimensions > 0)  ← force_element_visibility
    3. Element is enabled (no disabled attribute, not aria-disabled)
    4. Position stable for 300ms (bounding box not changing)
    5. Not covered by overlay (check elements at element center point via JS)
```

### force_element_visibility Integration
When `get_config().validations.force_element_visibility = true` (default):
- Step 2 (visibility check) is always enforced before any interaction
- If `false`, skip visibility check — interact with element even if hidden (escape hatch for edge cases)

### respect_native_waits Integration
When `get_config().waits.respect_native_waits = false`:
- Entire wait pipeline is skipped
- Actions use raw Selenium: find element → click immediately
- Useful for debugging or when you want full manual control

### Overlay Detection (step 5)
```javascript
// Execute in browser to check if element is covered
function isElementCovered(el) {
    const rect = el.getBoundingClientRect();
    const center_x = rect.left + rect.width / 2;
    const center_y = rect.top + rect.height / 2;
    const top_el = document.elementFromPoint(center_x, center_y);
    return top_el && top_el !== el && !el.contains(top_el);
}
```
- If covered, wait for overlay to disappear (modal closing, spinner fading)
- Timeout → `ElementNotInteractableError` with overlay info

### Timeout Errors
Include:
- Element description
- All 10 strategies attempted + result for each (found 0, found N)
- Current URL
- DOM snapshot of closest matching element (if any)
- Auto-screenshot saved to report dir

---

## 7. `pyshaft/core/action_runner.py`

**Purpose**: The pipeline — locate → wait → execute → log. Used by every web action.

### Exports
- `ActionRunner` — orchestrates the pipeline
- `run(action_name: str, *args, **kwargs) -> Any`

### Pipeline
```python
class ActionRunner:
    def click(self, locator: str) -> None:
        element = self._resolve(locator)    # DualLocator

        if get_config().waits.respect_native_waits:
            self._wait(element)             # WaitEngine

        if get_config().validations.force_element_visibility:
            self._wait_for_visible(element)

        try:
            element.click()
        except ElementClickInterceptedException:
            if get_config().actions.js_click_fallback:
                driver.execute_script("arguments[0].click()", element)
            else:
                raise

        self._log("click", locator)         # StepLogger

    def type_text(self, locator: str, text: str) -> None:
        element = self._resolve(locator)
        if get_config().waits.respect_native_waits:
            self._wait(element)
        element.clear()
        element.send_keys(text)

        # force_text_verification: verify text was actually entered
        if get_config().validations.force_text_verification:
            actual = element.get_attribute("value")
            if actual != text:
                raise TextVerificationError(
                    f"Typed {text!r} but field contains {actual!r}"
                )

        self._log("type_text", f"{locator} → {text!r}")
```

### Error Handling
- Every action wrapped in try/except
- On failure: capture screenshot, log state, re-raise with context
- `js_click_fallback` catches `ElementClickInterceptedException` and retries via JS
- `force_text_verification` reads back field value after typing to confirm

---

## 8. `pyshaft/core/step_logger.py`

**Purpose**: Capture every test step with metadata.

### Exports
- `StepLogger` — step capture and retrieval
- `Step` — dataclass for a single step

### Step Dataclass
```python
@dataclass
class Step:
    test_name: str
    action: str           # "click", "type_text", "open_url", etc.
    locator: str          # description or raw selector
    duration_ms: float    # how long the action took
    status: str           # "pass" | "fail" | "skip"
    timestamp: float      # time.time()
    screenshot: str | None = None  # path to screenshot file
    error: str | None = None       # error message if failed
```

### StepLogger Class
```python
class StepLogger:
    def record(self, step: Step) -> None: ...
    def get_steps(test_name: str) -> list[Step]: ...
    def get_all_steps() -> list[Step]: ...
    def capture_screenshot(driver: WebDriver) -> str: ...  # returns file path
```

---

## 9. `pyshaft/web/__init__.py`

**Purpose**: Export all web automation functions.

```python
from .navigation import open_url, go_back, go_forward, refresh, get_url, get_title
from .interactions import click, double_click, right_click, hover, drag_to
from .inputs import type_text, clear_text, press_key, upload_file
from .assertions import assert_text, assert_visible, assert_hidden, assert_url, assert_title, ...
from .windows import switch_to_frame, switch_to_main, switch_to_window, close_tab
from .screenshot import take_screenshot

__all__ = [
    "open_url", "go_back", "go_forward", "refresh", "get_url", "get_title",
    "click", "double_click", "right_click", "hover", "drag_to",
    "type_text", "clear_text", "press_key", "upload_file",
    # ... etc
]
```

---

## 10. `pyshaft/web/navigation.py`

### Functions
- `open_url(url: str) -> None` — prepends `base_url` from config if url is relative, triggers `wait_for_network_idle` (if `respect_native_waits`)
- `go_back() -> None`
- `go_forward() -> None`
- `refresh() -> None`
- `get_url() -> str`
- `get_title() -> str`

### force_navigation_check Integration
When `get_config().validations.force_navigation_check = true` (default):
```python
def open_url(url: str) -> None:
    config = get_config()
    full_url = f"{config.browser.base_url}{url}" if not url.startswith("http") else url
    driver.get(full_url)

    # Verify navigation succeeded
    WebDriverWait(driver, config.browser.navigation_timeout).until(
        lambda d: d.current_url != "about:blank"
    )
    if not driver.title:
        raise NavigationError(f"Page title is empty after navigating to {full_url}")
```

---

## 11. `pyshaft/web/interactions.py`

### Functions
- `click(locator: str) -> None` — goes through action runner pipeline, respects `js_click_fallback`
  - On `ElementClickInterceptedException`: retries via `driver.execute_script("arguments[0].click()", element)` if `js_click_fallback = true`
- `double_click(locator: str) -> None`
- `right_click(locator: str) -> None`
- `hover(locator: str) -> None` — wait for visible, then `ActionChains.move_to_element`
- `drag_to(source: str, target: str) -> None` — `ActionChains.drag_and_drop`

---

## 12. `pyshaft/web/inputs.py`

### Functions
- `type_text(locator: str, text: str, clear: bool = True) -> None` — clear by default, then `send_keys`
  - If `force_text_verification = true`: after typing, reads back `element.get_attribute("value")` and compares
  - Raises `TextVerificationError` if actual value doesn't match expected text
- `clear_text(locator: str) -> None` — select all + delete, or `element.clear()`
- `press_key(locator: str, key: str) -> None` — `send_keys(getattr(Keys, key))`
- `upload_file(locator: str, file_path: str | list[str]) -> None` — `element.send_keys(file_path)`, handles multiple files

---

## 13. `pyshaft/web/assertions.py`

### Functions
All raise `AssertionError` on failure with descriptive message.

- `assert_text(locator: str, expected: str) -> None` — get element text, compare
- `assert_visible(locator: str) -> None` — element is displayed
- `assert_hidden(locator: str) -> None` — element is NOT displayed
- `assert_url(expected: str) -> None` — current URL matches
- `assert_title(expected: str) -> None` — page title matches (with wait)
- `assert_attribute(locator: str, attr: str, expected: str) -> None`
- `assert_enabled(locator: str) -> None` — no `disabled` attribute
- `assert_disabled(locator: str) -> None` — has `disabled` attribute
- `assert_checked(locator: str) -> None` — checkbox/radio is checked
- `assert_not_checked(locator: str) -> None`

---

## 13b. `pyshaft/web/deferred.py`

**Purpose**: Deferred assertions — batch multiple checks, report all failures at once.

### Exports
- `defer_assert_text(locator: str, expected: str) -> None`
- `defer_assert_visible(locator: str) -> None`
- `defer_assert_element(locator: str) -> None`
- `check_deferred() -> None`
- `clear_deferred() -> None`

### DeferredAssertionError
```python
class DeferredAssertionError(AssertionError):
    def __init__(self, failures: list[dict]):
        # failures = [{"locator": "X", "check": "visible", "error": "..."}, ...]
        self.failures = failures
        message = "Deferred assertions failed:\n" + "\n".join(
            f"  - {f['check']}('{f['locator']}'): {f['error']}" for f in failures
        )
        super().__init__(message)
```

### Usage Pattern
```python
defer_assert_visible("Dashboard title")   # queues check, no raise
defer_assert_text("Welcome, Admin")       # queues check, no raise
defer_assert_text("5 pending orders")     # queues check, no raise
check_deferred()  # runs ALL checks, raises combined error if any failed
```

### Thread Safety
- Deferred queue stored in `threading.local()` — each test thread has its own queue
- Auto-cleared after `check_deferred()` call

---

## 14. `pyshaft/web/windows.py`

### Functions
- `switch_to_frame(locator: str | int) -> None` — by locator, index, or name
- `switch_to_main() -> None` — switch back to default content
- `switch_to_window(title_or_index: str | int) -> None` — by title or window index
- `close_tab() -> None` — close current tab, switch to previous

---

## 15. `pyshaft/web/screenshot.py`

### Functions
- `take_screenshot(name: str | None = None) -> str` — capture and save to report dir, returns file path

---

## 15b. `pyshaft/web/js_helpers.py`

**Purpose**: JavaScript utility helpers for DOM manipulation and demo mode.

### Exports
- `activate_jquery() -> None` — injects jQuery 3.7 if not already present
- `highlight_element(locator: str, color: str = "red", duration_ms: int = 500) -> None`
- `set_value_via_js(locator: str, value: str) -> None`
- `get_text_content(locator: str) -> str`

### jQuery Activation
```python
JQUERY_SCRIPT = "https://code.jquery.com/jquery-3.7.1.min.js"

def activate_jquery() -> None:
    if not driver.execute_script("return typeof jQuery !== 'undefined'"):
        # Inject jQuery from CDN or bundled copy
        js_content = _get_bundled_jquery()
        driver.execute_script(f"var s=document.createElement('script');s.innerHTML=`{js_content}`;document.head.appendChild(s);")
```

### Highlight Element (for demo mode)
```python
def highlight_element(locator: str, color: str = "red", duration_ms: int = 500) -> None:
    element = _resolve(locator)
    driver.execute_script(f"""
        arguments[0].style.outline = '3px solid {color}';
        arguments[0].style.transition = 'outline 0.2s';
        setTimeout(() => {{ arguments[0].style.outline = ''; }}, {duration_ms});
    """, element)
```

### Set Value via JS
```python
def set_value_via_js(locator: str, value: str) -> None:
    element = _resolve(locator)
    driver.execute_script("arguments[0].value = arguments[1];", element, value)
    driver.execute_script("arguments[0].dispatchEvent(new Event('input', {{ bubbles: true }}));", element)
    driver.execute_script("arguments[0].dispatchEvent(new Event('change', {{ bubbles: true }}));", element)
```

---

## 15c. `pyshaft/web/mobile.py`

**Purpose**: Mobile device emulation via Chrome DevTools.

### Exports
- `open_mobile(url: str, device: str = "iPhone 14") -> None`
- `set_mobile_device(device: str) -> None`
- `reset_to_desktop() -> None`

### Device Presets
```python
DEVICES = {
    "iPhone 14":       {"width": 390, "height": 844, "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)..."},
    "iPhone SE":       {"width": 375, "height": 667, "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)..."},
    "Pixel 7":         {"width": 412, "height": 915, "ua": "Mozilla/5.0 (Linux; Android 13; Pixel 7)..."},
    "Pixel 5":         {"width": 393, "height": 851, "ua": "Mozilla/5.0 (Linux; Android 11; Pixel 5)..."},
    "Galaxy S23":      {"width": 360, "height": 780, "ua": "Mozilla/5.0 (Linux; Android 13; SM-S911B)..."},
    "iPad Pro":        {"width": 1024, "height": 1366, "ua": "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X)..."},
}
```

### Implementation
```python
def set_mobile_device(device: str) -> None:
    config = DEVICES[device]
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": config["width"], "height": config["height"],
        "mobile": True, "deviceScaleFactor": 2,
    })
    driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": config["ua"]})
```

---

## 15d. `pyshaft/web/blocking.py`

**Purpose**: Ad and image blocking for faster tests on ad-heavy sites.

### Exports
- `block_ads() -> None`
- `block_images() -> None`
- `unblock_images() -> None`

### Block Ads
- Loads Chrome extension that blocks known ad domains (EasyList-based)
- Alternative: inject JS that removes ad containers on page load

### Block Images
```python
def block_images() -> None:
    options = ChromeOptions()
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,
    })
```

---

## 15e. `pyshaft/web/proxy.py`

**Purpose**: Proxy configuration for browser and API requests.

### Exports
- `set_proxy(url: str, type: str = "http") -> None`
- `clear_proxy() -> None`

### Supported Types
- HTTP: `http://proxy:8080`
- SOCKS4: `socks4://proxy:1080`
- SOCKS5: `socks5://proxy:1080`
- Authenticated: `http://user:pass@proxy:8080`

### Implementation
```python
def set_proxy(url: str, type: str = "http") -> None:
    options = ChromeOptions()
    options.add_argument(f"--proxy-server={url}")
```

---

## 15f. `pyshaft/utils/retry.py`

**Purpose**: Retry decorator for flaky operations.

### Exports
- `retry_on_exception(*exceptions, max_attempts: int = 3, backoff: float = 1.5, on_retry: Callable | None = None)`

### Implementation
```python
def retry_on_exception(*exceptions, max_attempts=3, backoff=1.5, on_retry=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = 1.0
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise
                    logger.warning(f"Attempt {attempt}/{max_attempts} failed: {e}. Retrying in {delay:.1f}s...")
                    if on_retry:
                        on_retry(attempt, e)
                    time.sleep(delay)
                    delay *= backoff
        return wrapper
    return decorator
```

### Usage
```python
@retry_on_exception(ElementNotFoundError, max_attempts=3, backoff=1.5)
def test_flaky_element():
    click("Submit button")  # retries up to 3 times

@retry_on_exception(ConnectionError, TimeoutError, max_attempts=5)
def test_api():
    send_get("https://api.example.com/data")
```

---

## 15g. `pyshaft/web/alerts.py`

**Purpose**: Alert, confirm, prompt, and HTTP Basic Auth dialog handling.

### Exports
- `accept_alert() -> None`
- `dismiss_alert() -> None`
- `get_alert_text() -> str`
- `type_alert(text: str) -> None`
- `handle_auth(username: str, password: str) -> None`

### Implementation
```python
def accept_alert() -> None:
    Alert(driver).accept()

def dismiss_alert() -> None:
    Alert(driver).dismiss()

def get_alert_text() -> str:
    return Alert(driver).text

def type_alert(text: str) -> None:
    Alert(driver).send_keys(text)
    Alert(driver).accept()

def handle_auth(username: str, password: str) -> None:
    # Option 1: Include credentials in URL
    # open_url(f"https://{username}:{password}@app.example.com")
    # Option 2: Use CDP for Chrome
    driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {
        "Authorization": f"Basic {base64.b64encode(f'{username}:{password}'.encode()).decode()}"
    })
```

---

## 15h. `pyshaft/web/collections.py`

**Purpose**: Element collection helpers.

### Exports
- `count(locator: str) -> int`
- `get_all(locator: str) -> list[WebElement]`
- `first(locator: str) -> WebElement`
- `last(locator: str) -> WebElement`
- `nth(locator: str, n: int) -> WebElement`
- `filter_visible(elements: list[WebElement]) -> list[WebElement]`

### Implementation
```python
def count(locator: str) -> int:
    return len(_resolve_all(locator))

def get_all(locator: str) -> list[WebElement]:
    return _resolve_all(locator)

def first(locator: str) -> WebElement:
    elements = _resolve_all(locator)
    if not elements:
        raise ElementNotFoundError(locator, strategies_tried=[], url=driver.current_url)
    return elements[0]

def nth(locator: str, n: int) -> WebElement:
    elements = _resolve_all(locator)
    if n < 1 or n > len(elements):
        raise ElementNotFoundError(f"{locator}[{n}]")
    return elements[n - 1]
```

---

## 15i. `pyshaft/web/keyboard.py`

**Purpose**: Keyboard shortcuts and key combinations.

### Exports
- `hotkey(*keys: str) -> None`
- `press_combo(*keys: str) -> None`
- `hold(key: str) -> None`
- `press(key: str) -> None`
- `release(key: str) -> None`

### Implementation
```python
def hotkey(*keys: str) -> None:
    """Press multiple keys simultaneously (hold all, release all)."""
    actions = ActionChains(driver)
    actions.key_down(keys[0])
    for k in keys[1:]:
        actions.key_down(k)
    for k in reversed(keys):
        actions.key_up(k)
    actions.perform()

def hold(key: str) -> None:
    ActionChains(driver).key_down(getattr(Keys, key)).perform()

def press(key: str) -> None:
    ActionChains(driver).send_keys(getattr(Keys, key)).perform()

def release(key: str) -> None:
    ActionChains(driver).key_up(getattr(Keys, key)).perform()
```

---

## 15j. `pyshaft/web/storage.py`

**Purpose**: LocalStorage and SessionStorage helpers.

### Exports
- `get_local_storage(key: str) -> str | None`
- `set_local_storage(key: str, value: str) -> None`
- `clear_local_storage() -> None`
- `get_session_storage(key: str) -> str | None`
- `set_session_storage(key: str, value: str) -> None`
- `clear_session_storage() -> None`

### Implementation
```python
def get_local_storage(key: str) -> str | None:
    return driver.execute_script(f"return localStorage.getItem('{key}')")

def set_local_storage(key: str, value: str) -> None:
    driver.execute_script(f"localStorage.setItem('{key}', {json.dumps(value)})")

def clear_local_storage() -> None:
    driver.execute_script("localStorage.clear()")
```

---

## 15k. `pyshaft/web/tables.py`

**Purpose**: HTML table helpers.

### Exports
- `get_cell(row: int, col: int, table: str | None = None) -> str`
- `get_row_count(table: str | None = None) -> int`
- `get_column(col: int, table: str | None = None) -> list[str]`
- `assert_cell_text(row: int, col: int, expected: str, table: str | None = None) -> None`

### Implementation
```python
def get_cell(row: int, col: int, table: str | None = None) -> str:
    if table:
        selector = f"{table} tbody tr:nth-child({row}) td:nth-child({col})"
    else:
        selector = f"table tbody tr:nth-child({row}) td:nth-child({col})"
    return _resolve(selector).text
```

---

## 15l. `pyshaft/web/dates.py`

**Purpose**: Date picker helpers.

### Exports
- `set_date(locator: str, value: str) -> None`  # value = "YYYY-MM-DD"

### Implementation
```python
def set_date(locator: str, value: str) -> None:
    element = _resolve(locator)
    input_type = element.get_attribute("type")

    if input_type == "date":
        # Native date input - set value directly via JS
        driver.execute_script(f"arguments[0].value = '{value}';", element)
        element.send_keys(Keys.ENTER)
    else:
        # Custom date picker (flatpickr, Material, React)
        element.click()
        type_text("input[role='textbox']", value)
        press_key("Enter")
```

---

## 15m. `pyshaft/web/downloads.py`

**Purpose**: File download handling.

### Exports
- `wait_for_download(timeout: float = 30) -> str`
- `get_downloaded_file(name: str) -> Path`

### Implementation
```python
DOWNLOAD_DIR = os.path.abspath("downloads")

def wait_for_download(timeout: float = 30) -> str:
    """Wait for any file to appear in download directory."""
    end = time.time() + timeout
    while time.time() < end:
        files = os.listdir(DOWNLOAD_DIR)
        # Skip .crdownload / .part files (in-progress)
        complete = [f for f in files if not f.endswith(('.crdownload', '.part'))]
        if complete:
            return os.path.join(DOWNLOAD_DIR, complete[0])
        time.sleep(0.5)
    raise TimeoutError(f"No download appeared in {DOWNLOAD_DIR} within {timeout}s")
```

---

## 15n. `pyshaft/api/graphql.py`

**Purpose**: GraphQL testing helpers.

### Exports
- `send_query(query: str, variables: dict | None = None) -> Response`
- `send_mutation(mutation: str, variables: dict | None = None) -> Response`
- `assert_gql_errors(expected_errors: list[str] | None = None) -> None`
- `assert_no_gql_errors() -> None`

### Implementation
```python
def send_query(query: str, variables: dict | None = None) -> Response:
    body = {"query": query}
    if variables:
        body["variables"] = variables
    return send_post("/graphql", json=body)

def assert_gql_errors(expected_errors: list[str] | None = None) -> None:
    resp = get_response()
    errors = resp.json_body.get("errors", [])
    if not errors:
        raise AssertionError("Expected GraphQL errors but found none")
    if expected_errors:
        error_messages = [e.get("message", "") for e in errors]
        for expected in expected_errors:
            if not any(expected in msg for msg in error_messages):
                raise AssertionError(f"Expected error '{expected}' not found in: {error_messages}")
```

---

## 15o. `pyshaft/api/oauth2.py`

**Purpose**: OAuth 2.0 authentication flows.

### Exports
- `oauth2_client_credentials(token_url: str, client_id: str, client_secret: str) -> str`
- `oauth2_password_grant(token_url: str, username: str, password: str, client_id: str, client_secret: str) -> str`
- `_token_cache: dict[str, dict]` — internal token cache
- `auto_refresh_on_401(callback: Callable) -> Callable` — decorator

### Implementation
```python
_token_cache: dict[str, dict] = {}

def oauth2_client_credentials(token_url, client_id, client_secret) -> str:
    resp = httpx.post(token_url, data={
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    })
    resp.raise_for_status()
    data = resp.json()
    _token_cache["access_token"] = data
    return data["access_token"]
```

---

## 15p. `pyshaft/api/pagination.py`

**Purpose**: Automatic pagination for API responses.

### Exports
- `get_all_pages(url: str, limit: int = 50, max_pages: int = 100) -> list[dict]`

### Implementation
```python
def get_all_pages(url: str, limit: int = 50, max_pages: int = 100) -> list[dict]:
    """Auto-iterate through paginated API."""
    all_items = []
    page = 1
    for _ in range(max_pages):
        resp = send_get(url, params={"page": page, "limit": limit})
        items = resp.json_body.get("data", resp.json_body)
        if not items:
            break
        all_items.extend(items)
        if len(items) < limit:
            break
        page += 1
    return all_items
```

---

## 15q. `pyshaft/utils/data.py`

**Purpose**: Data-driven testing decorators.

### Exports
- `data_from_csv(path: str) -> Callable`
- `data_from_json(path: str) -> Callable`
- `data_from_yaml(path: str) -> Callable`

### Implementation
```python
def data_from_csv(path: str) -> Callable:
    """Run test once per CSV row. Each row passed as keyword args."""
    import csv
    def decorator(func):
        @pytest.mark.parametrize("_row", _load_csv(path), ids=[str(i) for i in range(len(_load_csv(path)))])
        @functools.wraps(func)
        def wrapper(_row, **kwargs):
            return func(**_row, **kwargs)
        return wrapper
    return decorator

def _load_csv(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))
```

---

## 15r. `pyshaft/utils/tags.py`

**Purpose**: Test tagging and filtering.

### Exports
- `tag(*tags: str) -> Callable` — decorator
- `run_with_tags(tags: list[str]) -> None` — CLI integration

### Implementation
```python
def tag(*tags: str):
    """Mark test with tags: @tag('smoke', 'api')"""
    return pytest.mark.pyshaft_tags(*tags)
```

---

## 15s. `pyshaft/utils/secrets.py`

**Purpose**: Secrets management.

### Exports
- `get_secret(name: str) -> str`
- `get_secret_json(name: str) -> dict | list`

### Implementation
```python
def get_secret(name: str) -> str:
    # 1. Environment variable
    if val := os.environ.get(name):
        return val
    # 2. .env file
    if val := _load_dotenv().get(name):
        return val
    # 3. AWS Secrets Manager
    if get_config().secrets.provider == "aws":
        return _aws_secrets(name)
    # 4. HashiCorp Vault
    if get_config().secrets.provider == "vault":
        return _vault_secrets(name)
    raise SecretNotFoundError(f"Secret '{name}' not found in any provider")
```

---

## 15t. `pyshaft/utils/pdf.py`

**Purpose**: PDF testing utilities.

### Exports
- `assert_pdf_text(path: str, expected: str) -> None`
- `extract_pdf_text(path: str) -> str`

### Implementation
```python
from pypdf import PdfReader

def extract_pdf_text(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() for page in reader.pages)

def assert_pdf_text(path: str, expected: str) -> None:
    text = extract_pdf_text(path)
    if expected not in text:
        raise AssertionError(f"'{expected}' not found in PDF")
```

---

## 15u. `pyshaft/utils/visual_diff.py`

**Purpose**: Visual regression testing.

### Exports
- `assert_no_visual_change(name: str, threshold: float = 0.01) -> None`
- `update_baseline(name: str) -> None`

### Implementation
```python
from PIL import Image, ImageChops

BASELINES_DIR = "pyshaft-visual-baselines"

def assert_no_visual_change(name: str, threshold: float = 0.01) -> None:
    baseline_path = os.path.join(BASELINES_DIR, f"{name}.png")
    if not os.path.exists(baseline_path):
        # First run - create baseline
        os.makedirs(BASELINES_DIR, exist_ok=True)
        take_screenshot(baseline_path)
        return

    current = take_screenshot()
    diff = ImageChops.difference(Image.open(baseline_path), Image.open(current))
    diff_pixels = sum(1 for p in diff.getdata() if p != (0, 0, 0))
    total_pixels = diff.width * diff.height
    diff_ratio = diff_pixels / total_pixels

    if diff_ratio > threshold:
        diff_path = f"pyshaft-report/visual-diff-{name}.png"
        diff.save(diff_path)
        raise AssertionError(f"Visual diff exceeds {threshold*100}% threshold (actual: {diff_ratio*100:.2f}%)")
```

---

## 16. `pyshaft/api/__init__.py`

**Purpose**: Export all API testing functions.

```python
from .client import api_session, set_base_url, set_headers, set_auth, set_timeout, clear_headers
from .methods import send_get, send_post, send_put, send_patch, send_delete, send_request
from .assertions import assert_status, assert_json, assert_json_schema, assert_header, ...
from .store import extract_json, extract_header, store, stored, get_response, ...

__all__ = [...]
```

---

## 17. `pyshaft/api/client.py`

**Purpose**: HTTP session management via httpx.

### Exports
- `api_session` — module-level httpx.Client (shared across tests)
- `set_base_url(url: str) -> None`
- `set_headers(headers: dict) -> None`
- `set_auth(token: str | tuple[str, str], type: str = "bearer") -> None`
- `set_timeout(seconds: float) -> None`
- `clear_headers() -> None`

### Session Setup
- Shared `httpx.Client(base_url=..., timeout=..., verify=...)`
- Headers merged from: defaults → config → `set_headers()` → per-call override
- Auth: Bearer token, Basic auth, or custom headers

---

## 18. `pyshaft/api/methods.py`

### Functions
- `send_get(url: str, **kwargs) -> Response`
- `send_post(url: str, json: dict | None = None, data: str | None = None, **kwargs) -> Response`
- `send_put(url: str, json: dict | None = None, **kwargs) -> Response`
- `send_patch(url: str, json: dict | None = None, **kwargs) -> Response`
- `send_delete(url: str, **kwargs) -> Response`
- `send_request(method: str, url: str, **kwargs) -> Response` — generic

### Response Wrapper
```python
@dataclass
class Response:
    status_code: int
    headers: httpx.Headers
    body: str
    json_body: dict | list | None
    elapsed_ms: float
    _raw: httpx.Response  # internal, for advanced use
```

---

## 19. `pyshaft/api/assertions.py`

### Functions
- `assert_status(expected: int | list[int]) -> None` — check last response status code
- `assert_json(expected: dict) -> None` — deep equality check
- `assert_json_schema(schema: dict) -> None` — validate against JSON schema using `jsonschema`
- `assert_header(name: str, expected: str) -> None`
- `assert_response_time(max_ms: float) -> None`
- `assert_body_contains(text: str) -> None`
- `assert_body_not_contains(text: str) -> None`

---

## 20. `pyshaft/api/store.py`

**Purpose**: Value extraction and chaining for multi-step API flows.

### Exports
- `extract_json(path: str, key: str) -> None` — extract value from last response JSON (supports JSONPath-like dot notation)
- `extract_header(name: str, key: str) -> None` — extract header value
- `store(key: str, value: Any) -> None` — manually store a value
- `stored(key: str) -> Any` — retrieve a stored value
- `get_response() -> Response` — get the last full response
- `get_status_code() -> int`
- `get_response_time() -> float`

### Usage
```python
send_post("/login", json={"user": "admin", "pass": "secret"})
extract_json("token", "auth_token")  # stores response.json()["token"] as "auth_token"

send_get("/profile", headers={"Authorization": f"Bearer {stored('auth_token')}"})
assert_status(200)
```

---

## 21. `pyshaft/report/collector.py`

**Purpose**: StepCollector singleton — auto-intercepts every action. Manages screenshots and video recordings.

### Exports
- `StepCollector` — singleton collector
- `get_collector() -> StepCollector`

### StepCollector Class
```python
class StepCollector:
    _instance: ClassVar["StepCollector | None"] = None

    def start_test(self, test_name: str) -> None: ...
    def end_test(self, status: str, error: str | None = None) -> None: ...
    def record_step(self, action: str, locator: str, duration_ms: float, status: str, ...) -> None: ...
    def attach_screenshot(self, path: str) -> None: ...
    def attach_video(self, path: str) -> None: ...
    def get_report(test_name: str) -> TestReport: ...
    def get_all_reports() -> list[TestReport]: ...
    def write_reports(output_dir: str) -> None: ...  # triggers HTML + JSON + JUnit
```

### Video Integration
- On test start: if `video_on_fail = true`, signal `driver_factory` to begin screencast
- On test pass: discard screencast buffer (no disk write)
- On test fail: stop screencast, encode buffer to `.webm`, save to `{output_dir}/videos/{test_name}.webm`
- Report attaches video path; HTML renderer embeds `<video>` player

---

## 22. `pyshaft/report/html_renderer.py`

**Purpose**: Render HTML report with step timeline, embedded screenshots, and video player for failed tests.

### Exports
- `render_html(reports: list[TestReport]) -> str`

### Report Features
- Dark/light mode toggle
- Test summary: passed/failed/skipped counts, total duration
- Per-test step timeline with color-coded status icons
- Embedded screenshots inline with failing steps
- Embedded `<video>` player for failed tests (when `video_on_fail = true`)
- Duration bar per step
- Export as standalone HTML file (no external deps)

---

## 23. `pyshaft/report/json_exporter.py`

**Purpose**: Write JSON summary of all test results.

### Exports
- `export_json(reports: list[TestReport], path: str) -> None`

### JSON Structure
```json
{
  "meta": { "version": "0.1.0", "timestamp": "...", "duration_ms": 1234 },
  "summary": { "passed": 10, "failed": 2, "skipped": 1, "total": 13 },
  "tests": [
    {
      "name": "test_login",
      "status": "passed",
      "duration_ms": 4500,
      "steps": [
        { "action": "open_url", "locator": "https://app.example.com", "status": "pass", "duration_ms": 1200 },
        { "action": "click", "locator": "Login button", "status": "pass", "duration_ms": 350 },
        ...
      ]
    }
  ]
}
```

---

## 23b. `pyshaft/report/history_db.py`

**Purpose**: SQLite-based test history storage. Enables run comparison, trend analysis, flaky test detection.

### Exports
- `HistoryDB` — database wrapper
- `get_history_db() -> HistoryDB` — singleton accessor (auto-creates DB)

### Database Schema
```sql
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    passed INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    skipped INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    git_hash TEXT,
    env TEXT
);

CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    name TEXT NOT NULL,
    file TEXT NOT NULL,
    status TEXT NOT NULL,       -- 'passed' | 'failed' | 'skipped'
    duration_ms INTEGER NOT NULL,
    error TEXT,
    screenshot_path TEXT,
    video_path TEXT,
    retry_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL REFERENCES tests(id),
    action TEXT NOT NULL,
    locator TEXT,
    duration_ms INTEGER NOT NULL,
    status TEXT NOT NULL,       -- 'pass' | 'fail' | 'skip'
    dom_snapshot TEXT,           -- compressed HTML
    error TEXT,
    screenshot_path TEXT
);

CREATE TABLE IF NOT EXISTS network (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL REFERENCES tests(id),
    url TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER,
    duration_ms INTEGER
);

CREATE INDEX idx_tests_run_id ON tests(run_id);
CREATE INDEX idx_steps_test_id ON steps(test_id);
CREATE INDEX idx_network_test_id ON network(test_id);
CREATE INDEX idx_runs_timestamp ON runs(timestamp);
```

### HistoryDB Class
```python
class HistoryDB:
    def __init__(self, path: str = "pyshaft_history.db"): ...

    # Write operations
    def insert_run(self, timestamp, duration_ms, passed, failed, skipped, total, git_hash=None, env=None) -> int: ...
    def insert_test(self, run_id, name, file, status, duration_ms, error=None, screenshot_path=None, video_path=None, retry_count=0) -> int: ...
    def insert_step(self, test_id, action, locator, duration_ms, status, dom_snapshot=None, error=None, screenshot_path=None) -> None: ...
    def insert_network(self, test_id, url, method, status_code, duration_ms) -> None: ...

    # Read operations
    def get_runs(self, limit=50) -> list[dict]: ...
    def get_run(self, run_id: int) -> dict | None: ...
    def get_tests(self, run_id: int) -> list[dict]: ...
    def get_test(self, test_id: int) -> dict | None: ...
    def get_steps(self, test_id: int) -> list[dict]: ...
    def get_network(self, test_id: int) -> list[dict]: ...

    # Analytics
    def compare_runs(self, run1_id: int, run2_id: int) -> dict: ...
    def get_flaky_tests(self, days=7) -> list[dict]: ...  # tests that failed then passed on retry
    def get_slowest_tests(self, days=7, limit=10) -> list[dict]: ...
    def get_trend(self, days=30) -> list[dict]: ...  # daily pass/fail counts
    def get_pass_rate(self, days=30) -> float: ...

    # Maintenance
    def vacuum(self) -> None: ...  # reclaim disk space
    def prune_old_runs(self, days=90) -> None: ...  # delete runs older than N days
```

### Auto-Create Logic
- DB created in `pyshaft_history.db` in current working directory on first test run
- No config needed — just `from pyshaft.report import get_history_db`
- Optional: set custom path via `PYSHAFT_HISTORY_DB=/path/to.db`

---

## 23c. `pyshaft/report/html_renderer.py`

**Purpose**: Render self-contained HTML report — open directly in browser, no server needed.

### Exports
- `render_html(reports: list[TestReport]) -> str`
- `render_html_with_history(db: HistoryDB, run_id: int) -> str`  # uses SQLite for context

### Report Structure
```
┌─────────────────────────────────────────────────────────────┐
│  PYSHAFT REPORT                          [🌙/☀️]              │
├─────────────────────────────────────────────────────────────┤
│  ✅ 10   ❌ 2   ⏭️ 1   📊 13    ⏱️ 2m 34s   🔴 2 flaky       │
│  [Pass Rate Donut: 77%]    [Duration Bar Chart]              │
├─────────────────────────────────────────────────────────────┤
│  Search: [________________________]  Filter: [All ▼]        │
├─────────────────────────────────────────────────────────────┤
│  ✅ test_login              login_test.py    4.5s     [▼]   │
│  ❌ test_checkout           checkout_test.py 12.3s    [▼]   │
│     ├── open_url /checkout        ✓  1.2s                    │
│     ├── click "Buy Now"           ✗  8.1s  [Screenshot]     │
│     ├── DOM snapshot              [👁️ View]                  │
│     └── Network (14 reqs)         [📋 View]                  │
│  ✅ test_profile              profile_test.py  2.1s     [▼]   │
└─────────────────────────────────────────────────────────────┘
```

### Step Detail Panel (expand on row click)
```
┌─ Step: click "Buy Now" ───────────────────────────────────┐
│  Status: ❌ Failed  |  Duration: 8.1s                     │
│  Error: ElementNotFoundError: "Buy Now" not found after   │
│         10s. Strategies tried: ARIA, text, placeholder... │
├───────────────────────────────────────────────────────────┤
│  [📸 Screenshot]  [▶️ Video]  [🌐 DOM Snapshot]            │
├───────────────────────────────────────────────────────────┤
│  Timeline:                                                │
│  ✓ open_url /checkout              1.2s                   │
│  ✓ click "Cart icon"               0.3s                   │
│  ✗ click "Buy Now"                 8.1s ←                 │
│    [DOM Snapshot Viewer - iframe below]                   │
│    ┌─────────────────────────────────────┐                │
│    │  [Sandboxed iframe renders DOM]      │                │
│    │  Hover to highlight, click selector  │                │
│    └─────────────────────────────────────┘                │
├───────────────────────────────────────────────────────────┤
│  Network (14 requests):                                   │
│  GET /checkout          200   0.8s                        │
│  POST /api/cart         201   0.3s                        │
│  GET /api/products      500   5.2s ← (red)                │
└───────────────────────────────────────────────────────────┘
```

### DOM Snapshot Viewer
- Sandboxed iframe: `<iframe sandbox="allow-same-origin" srcdoc="...">`
- Inline CSS injected to match original styles
- Inspect mode: mouseover highlights element, click copies CSS selector
- Toggle: "Rendered" vs "Raw HTML" view

### Run Comparison (static mode)
- Dropdown to pick another run from same directory (parsed from JSON sidecar)
- Side-by-side table:
  ```
  Test Name          | Run A (current) | Run B (selected) | Delta
  ───────────────────┼─────────────────┼──────────────────┼──────
  test_login         | ✅ 4.5s         | ✅ 4.2s          | -0.3s
  test_checkout      | ❌ 12.3s        | ✅ 8.1s          | FIXED
  test_profile       | ✅ 2.1s         | ❌ 5.0s          | NEW FAIL
  ```

### Technical Constraints
- Zero external JS dependencies — vanilla JS only
- CSS variables for dark/light mode (same theme as main app)
- All JS/CSS inline in HTML file (self-contained, no external requests)
- Max file size: < 5MB for single run (compressed images, trimmed DOM snapshots)

---

## 23d. `pyshaft/report/flask_app.py`

**Purpose**: Flask dashboard server — `pyshaft report serve` → `http://localhost:8080`.

### Exports
- `create_app(db_path=None) -> Flask` — factory function
- `main()` — CLI entry point for `pyshaft report serve`

### Routes
```
GET  /                  → Dashboard home (aggregate stats, charts)
GET  /run/<id>          → Single run detail (same layout as static HTML)
GET  /compare/<id1>/<id2> → Run comparison page
GET  /search?q=...      → Full-text search across all runs
GET  /live              → Live progress page (SSE)
GET  /api/runs          → JSON: list all runs
GET  /api/run/<id>      → JSON: single run detail
GET  /api/compare/<id1>/<id2> → JSON: comparison data
GET  /api/search?q=...  → JSON: search results
GET  /api/stream        → SSE: live step stream
```

### Dashboard Home Page
```
┌─────────────────────────────────────────────────────────────┐
│  PYSHAFT DASHBOARD                        [🌙/☀️] [📋 Open]   │
├─────────────────────────────────────────────────────────────┤
│  Total Runs: 147   Pass Rate: 94.2%   Last 30 days          │
│  [Pass Rate Trend Line Chart - SVG]                          │
│  [Duration Trend Line Chart - SVG]                           │
├─────────────────────────────────────────────────────────────┤
│  Top 10 Slowest Tests                    Top Flaky Tests     │
│  1. test_checkout    12.3s               1. test_login       │
│  2. test_search      8.1s                2. test_profile     │
│  3. test_login       4.5s                3. test_cart        │
├─────────────────────────────────────────────────────────────┤
│  Recent Runs:                                                │
│  ✅ Run #147  2m 34s  13 tests  2h ago    [View]             │
│  ❌ Run #146  3m 12s  13 tests  4h ago    [View]             │
│  ✅ Run #145  2m 28s  13 tests  6h ago    [View]             │
└─────────────────────────────────────────────────────────────┘
```

### Live Progress Page
- SSE connection: `const es = new EventSource('/api/stream')`
- Steps appear in real-time with animation
- Live counters: `Running: 3 | Passed: 10 | Failed: 2 | Total: 13`
- Progress bar: estimated time remaining (based on historical average)
- Auto-scrolls to latest step

### SSE Implementation
```python
@app.route('/api/stream')
def stream():
    def event_stream():
        collector = get_collector()
        for step in collector.live_stream():  # Queue-based generator
            yield f"data: {json.dumps(step)}\n\n"
    return Response(event_stream(), mimetype='text/event-stream')
```

### Server-Rendered Templates
- Uses same CSS as static HTML (shared `report/static/style.css`)
- Jinja2 templates: `templates/dashboard.html`, `templates/run_detail.html`, etc.
- Charts rendered as SVG inline (no JS chart library)
- HTMX for interactive elements (search, filter, expand/collapse)

---

## 24. `pyshaft/report/junit_writer.py`

**Purpose**: Write JUnit XML for CI/CD integration (GitHub Actions, Jenkins, etc.).

### Exports
- `export_junit(reports: list[TestReport], path: str) -> None`

### XML Structure
- Standard JUnit `<testsuite>` with `<testcase>` elements
- `<failure>` elements with error message and stack trace
- `<system-out>` with step log
- Compatible with all CI systems that parse JUnit XML

---

## 25. `pytest_pyshaft/plugin.py`

**Purpose**: Pytest plugin — session fixtures, scope management, markers, parallel + retry support.

### Exports
- `pyshaft_session` — pytest fixture (scope controlled by config)
- `pyshaft_scope` — custom marker for per-test scope override

### Fixture Logic
```python
@pytest.fixture(scope="session")
def pyshaft_session(request):
    config = get_config()
    scope = _resolve_scope(request)  # check for @pytest.mark.pyshaft_scope
    driver = DriverFactory.create(
        browser=config.browser.browser,
        headless=config.browser.headless,
        window_size=config.browser.window_size,
        video_on_fail=config.report.video_on_fail,
    )
    SessionContext().driver = driver
    yield driver
    if scope == "function":
        driver.quit()
```

### Parallel Execution
When `execution.parallel = true`:
- Each pytest-xdist worker gets its own isolated browser session
- Sessions keyed by `PYTEST_XDIST_WORKER` env var (`"gw0"`, `"gw1"`, etc.)
- Reports from each worker merged in `pytest_sessionfinish`

### Retry Integration
When `execution.retry_attempts > 0`:
- Failed tests are re-run with a fresh browser instance (no stale state)
- Report shows: `test_login [attempt 1/3] → fail`, `test_login [attempt 2/3] → pass`
- Uses `pytest-rerunfailures` under the hood

### Module-level cleanup
- Session-scoped: close at end of entire test run
- Module-scoped: close at end of each test file
- Function-scoped: close after each test

---

## 26. `pytest_pyshaft/hooks.py`

**Purpose**: Pytest hooks for test lifecycle, step capture, video recording, and retry handling.

### Hooks
- `pytest_configure(config)` — register custom markers, load config early, init video if enabled
- `pytest_runtest_setup(item)` — initialize step collector, start video recording for test
- `pytest_runtest_teardown(item)` — stop video on failure, save trimmed `.webm`, capture screenshot, scope-based cleanup
- `pytest_runtest_makereport(item, call)` — capture test result, attach to report, trigger retry if configured
- `pytest_sessionfinish(session, exitstatus)` — write all reports (HTML + JSON + JUnit XML), merge reports from parallel workers

### Video Lifecycle
```
test starts → start_screencast(driver)
    ├── test passes → discard_screencast()  # no disk I/O
    └── test fails  → stop_screencast() → encode_webm() → save to report/videos/
```

### Retry Lifecycle
```
test fails → check retry_attempts > 0
    ├── retries remaining → fresh browser → re-run test → mark as [retry N/M]
    └── no retries left  → capture screenshot + video → mark as failed
```

---

## 27. `pyproject.toml`

**Purpose**: Package metadata, dependencies, build config, CLI entry points.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyshaft"
version = "0.1.0"
description = "Test automation that reads like English"
requires-python = ">=3.10"
dependencies = [
    "selenium>=4.0",
    "webdriver-manager",
    "httpx",
    "jinja2",
    "jsonschema",
    "pytest>=7.0",
]

[project.optional-dependencies]
async = ["pytest-asyncio"]
parallel = ["pytest-xdist"]
retry = ["pytest-rerunfailures"]
video = ["ffmpeg-python"]
report = ["flask", "lxml"]
s3 = ["boto3"]
grid = ["selenium-grid"]
wire = ["selenium-wire"]
dev = ["pytest", "pytest-xdist", "pytest-rerunfailures", "ruff", "mypy"]
docs = ["mkdocs-material"]
full = ["pyshaft[async,parallel,retry,video,report,s3,grid,wire]"]

[project.scripts]
pyshaft = "pyshaft.cli:main"

[project.entry-points.pytest11]
pyshaft = "pytest_pyshaft.plugin"
```

### CLI Entry Point (`pyshaft/cli.py`)
```python
def main():
    parser = argparse.ArgumentParser(prog="pyshaft")
    sub = parser.add_subparsers(dest="command")

    # pyshaft run
    run = sub.add_parser("run", help="Run tests")
    run.add_argument("--demo", action="store_true", help="Demo mode")
    run.add_argument("--headless", action="store_true")
    run.add_argument("--browser", type=str, default=None)
    run.add_argument("--grid-url", type=str, default=None)
    run.add_argument("--with-s3", action="store_true")

    # pyshaft record
    rec = sub.add_parser("record", help="Test recorder")
    rec.add_argument("--output", type=str, default="test_recorded.py")

    # pyshaft report serve
    report = sub.add_parser("report", help="Report commands")
    report_sub = report.add_subparsers(dest="report_command")
    serve = report_sub.add_parser("serve", help="Start dashboard")
    serve.add_argument("--port", type=int, default=8080)
    serve.add_argument("--host", type=str, default="localhost")
    serve.add_argument("--db", type=str, default=None)

    args = parser.parse_args()
    # ... dispatch to handler
```

Usage:
```bash
pyshaft run                                    # Run tests with config
pyshaft run --demo                             # Demo mode (highlight + slow)
pyshaft run --headless --browser=firefox       # Override config
pyshaft run --grid-url=http://hub:4444         # Run on Selenium Grid
pyshaft run --with-s3                          # Upload reports to AWS S3
pyshaft record --output=test_login.py          # Test recorder
pyshaft report serve                           # http://localhost:8080
pyshaft report serve --port 3000               # http://localhost:3000
```
