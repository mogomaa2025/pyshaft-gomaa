# PyShaft — Coding Rules

> Clean code principles for the entire PyShaft codebase. Every contributor follows these.

---

## 1. General Principles

- **Readability first** — code is read 10x more than it's written
- **One responsibility per function** — if it does two things, split it
- **Fail fast, fail loud** — validate inputs early, raise with context
- **No magic** — no hidden side effects, no global state except documented singletons
- **Document why, not what** — code says what, comments say why

---

## 2. Naming

### Variables & Functions
- **snake_case** for everything (Python convention)
- Names describe intent, not type: `timeout`, not `timeout_seconds_int`
- Booleans start with verbs: `is_visible`, `has_overlay`, `can_click`
- Collections are plural: `strategies`, `elements`, `steps`

### Classes
- **PascalCase**: `DualLocator`, `WaitEngine`, `StepCollector`
- Single responsibility — if a class has 10+ methods, reconsider

### Constants
- **UPPER_SNAKE_CASE**: `DEFAULT_TIMEOUT`, `MAX_RETRIES`
- Module-level constants at top of file

### Private Members
- Prefix with underscore: `_detect_mode`, `_resolve_strategy`
- These are implementation details — not exported in `__all__`

---

## 3. Functions

### Keep them small
- Max **30 lines** per function (excluding docstrings and comments)
- If longer → extract helpers

### Prefer early returns over nesting
```python
# ❌ Bad
def resolve(locator: str) -> WebElement:
    if locator:
        mode = _detect_mode(locator)
        if mode == "semantic":
            result = _resolve_semantic(locator)
            if result:
                return result
    return None

# ✅ Good
def resolve(locator: str) -> WebElement:
    if not locator:
        return None
    mode = _detect_mode(locator)
    if mode != "semantic":
        return None
    return _resolve_semantic(locator)
```

### Default arguments for optional config
```python
# ✅ Good
def wait_for(element: WebElement, timeout: float | None = None) -> None:
    timeout = timeout or get_config().wait.default_timeout
```

### Type hints on every function
```python
# ✅ Good — always annotate
def click(locator: str) -> None: ...
def get_text(locator: str) -> str: ...
def find_all(selector: str) -> list[WebElement]: ...
```

---

## 4. Control Flow

### List/dict/set comprehensions over loops
```python
# ❌ Bad
results = []
for strategy in strategies:
    elements = strategy.find(driver, description)
    if elements:
        results.append(elements)

# ✅ Good
results = [
    elements
    for strategy in strategies
    if (elements := strategy.find(driver, description))
]
```

```python
# ❌ Bad
config = {}
for key, value in pairs:
    if value is not None:
        config[key] = value

# ✅ Good
config = {key: value for key, value in pairs if value is not None}
```

```python
# ❌ Bad
seen = set()
for item in items:
    if item not in seen:
        seen.add(item)

# ✅ Good
seen = {item for item in items}
```

### Generator expressions for large sequences
```python
# ✅ Good — lazy, memory-efficient
any_match = any(strategy.matches(desc) for strategy in strategies)
```

### Walrus operator for inline assignment (Python 3.10+)
```python
# ✅ Good
if (element := driver.find_element(By.CSS, selector)):
    return element
```

### `match/case` for multi-branch logic (Python 3.10+)
```python
# ✅ Good
def _build_selector(strategy: int, description: str) -> str:
    match strategy:
        case 1: return f'[aria-label="{description}"]'
        case 2: return f'//*[normalize-space()="{description}"]'
        case 3: return f'//*[contains(text(),"{description}")]'
        case 4: return f'input[placeholder*="{description}"]'
        case 5: return f'#{description}, #{description}Btn, #{description}-btn'
        case _: return None
```

---

## 5. Error Handling

### Custom exceptions with context
```python
# ✅ Good
class ElementNotFoundError(Exception):
    def __init__(self, description: str, strategies: list[str], url: str, screenshot: str | None):
        self.description = description
        self.strategies_tried = strategies
        self.url = url
        self.screenshot = screenshot
        super().__init__(
            f"Element not found: {description!r}\n"
            f"URL: {url}\n"
            f"Strategies tried: {', '.join(strategies)}\n"
            f"Screenshot: {screenshot or 'not captured'}"
        )
```

### Catch specific exceptions, never bare `except`
```python
# ❌ Bad
try:
    element.click()
except:
    pass

# ✅ Good
try:
    element.click()
except ElementClickInterceptedException as e:
    raise ElementNotInteractableError(locator, overlay=top_element) from e
```

### Use `contextlib` for resource management
```python
# ✅ Good
from contextlib import contextmanager

@contextmanager
def session_scope(scope: str):
    driver = DriverFactory.create()
    try:
        yield driver
    finally:
        if scope == "function":
            driver.quit()
```

---

## 6. Data Structures

### Use `dataclass` for configuration and DTOs
```python
# ✅ Good
@dataclass(frozen=True)
class Step:
    action: str
    locator: str
    duration_ms: float
    status: str
    timestamp: float
    screenshot: str | None = None
    error: str | None = None
```

### Use `TypedDict` for dict-shaped data
```python
# ✅ Good
class LocatorResult(TypedDict):
    strategy: int
    selector: str
    elements: list[WebElement]
    match_count: int
```

### Prefer `enum` over string constants for fixed sets
```python
# ✅ Good
class StrScope(StrEnum):
    SESSION = "session"
    MODULE = "module"
    FUNCTION = "function"

class Browser(StrEnum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
```

---

## 7. Imports

### Standard order
1. Standard library
2. Third-party
3. Local (relative)

```python
# ✅ Good
import threading
from dataclasses import dataclass, field
from typing import Any

import httpx
from selenium.webdriver.common.by import By

from ..config import get_config
from .driver_factory import DriverFactory
```

### Import specific names, not modules
```python
# ❌ Bad
import os
from selenium import webdriver

# ✅ Good
from pathlib import Path
from selenium.webdriver.common.by import By
```

---

## 8. Strings

### Use f-strings exclusively
```python
# ❌ Bad
msg = "Element %s not found after %.1fs" % (desc, timeout)
msg = "Element {} not found after {}s".format(desc, timeout)

# ✅ Good
msg = f"Element {desc!r} not found after {timeout:.1f}s"
```

### Multi-line strings with triple quotes
```python
# ✅ Good
HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><title>PyShaft Report</title></head>
<body>{{ content }}</body>
</html>
"""
```

---

## 9. Testing (when Phase 2 arrives)

### Test behavior, not implementation
```python
# ✅ Good — tests the observable outcome
def test_click_by_visible_text():
    click("Login button")
    assert_text("Welcome")

# ❌ Bad — tests internal strategy index
def test_click_strategy_2():
    locator = DualLocator("Login button")
    assert locator._current_strategy == 2
```

### One assertion per test (mostly)
```python
# ✅ Good — each test has one reason to fail
def test_detects_css():
    assert _detect_mode("#submit") == "raw"

def test_detects_semantic():
    assert _detect_mode("Login button") == "semantic"
```

### Parametrize for multiple inputs
```python
# ✅ Good
@pytest.mark.parametrize("input,expected", [
    ("#submit", "raw"),
    (".btn", "raw"),
    ("//button", "raw"),
    ("css=div", "raw"),
    ("Login", "semantic"),
    ("Sign In", "semantic"),
])
def test_detect_mode(input: str, expected: str):
    assert _detect_mode(input) == expected
```

---

## 10. Logging & Debugging

### Use `logging` module, not `print`
```python
# ❌ Bad
print(f"Found {len(elements)} elements")

# ✅ Good
logger.debug("Found %d elements for strategy %d: %s", len(elements), step, desc)
```

### Log at the right level
- `DEBUG` — internal decisions, strategy attempts
- `INFO` — test start/end, browser open/close
- `WARNING` — multiple matches, deprecated config
- `ERROR` — action failures, driver errors

---

## 11. Concurrency

### Thread-local for session data
```python
# ✅ Good
class SessionContext:
    _local = threading.local()

    @property
    def driver(self) -> WebDriver:
        return self._local.driver

    @driver.setter
    def driver(self, value: WebDriver) -> None:
        self._local.driver = value
```

### No shared mutable state
- Singletons are fine if they're immutable or use locks
- Use `threading.Lock()` for shared caches

---

## 12. Code Formatting

- **4-space indent** (Python standard)
- **Max line length: 100** (configured in `pyproject.toml` for ruff)
- **Trailing commas** in multi-line structures
- **Blank lines**: 2 between top-level classes, 1 between methods

```python
# ✅ Good
config = Config(
    browser=BrowserConfig(scope="session", browser="chrome"),
    wait=WaitConfig(default_timeout=10),
    api=ApiConfig(),
    report=ReportConfig(),
)
```

---

## 13. Anti-Patterns (Never Do These)

| Anti-Pattern | Why | Fix |
|-------------|-----|-----|
| `time.sleep()` | Flaky, wastes time | Use `WaitEngine` |
| `except: pass` | Swallows errors | Catch specific, log |
| Global mutable dict | Thread-unsafe race conditions | `threading.local()` or lock |
| `len(x) == 0` | Unpythonic | `not x` |
| `if x == True` | Redundant | `if x` |
| `if x == None` | Wrong comparison | `if x is None` |
| Deep nesting (3+ levels) | Unreadable | Early returns, extract helpers |
| Hard-coded selectors in tests | Brittle | Semantic descriptions |
| `import *` | Namespace pollution | Explicit imports |

---

## 14. Review Checklist

Before committing code, verify:

- [ ] Type hints on all public functions
- [ ] Docstring on every public class and function
- [ ] No `print()` statements (use `logging`)
- [ ] No `time.sleep()` (use wait engine)
- [ ] List comprehensions used instead of manual loops where possible
- [ ] Early returns instead of deep nesting
- [ ] Custom exceptions with context, not generic `Exception`
- [ ] Thread-safe (no shared mutable state)
- [ ] Tests pass (`pytest`)
- [ ] Linter clean (`ruff check .`)
