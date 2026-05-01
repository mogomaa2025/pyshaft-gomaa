# PyShaft

> **Write tests that read like English.** `click("Login button")` — not `driver.find_element(By.XPATH, "//button[@id='submit']")`.

PyShaft is a Python test automation framework with semantic locators, auto-wait, and modern reporting.

## 🚀 Quick Start

### Install

```bash
pip install -e .
```

### Write Your First Test

```python
# tests/examples/test_smoke.py
from pyshaft.web import open_url, assert_title

def test_google_title():
    open_url("https://www.google.com")
    assert_title("Google")
```

### Run

```bash
pytest tests/examples/test_smoke.py
```

## 🔧 Configuration

Create a `pyshaft.toml` in your project root (all values are optional):

```toml
[browser]
browser = "chrome"       # chrome | firefox | edge
headless = false         # true for CI
window_size = "1920x1080"
base_url = ""            # prefix for all open_url() calls

[execution]
scope = "session"        # session | module | function
retry_attempts = 0       # retry failed tests N times

[waits]
default_element_timeout = 10   # seconds
respect_native_waits = true    # false = skip auto-wait

[validations]
force_navigation_check = true  # verify page loaded after open_url()
js_click_fallback = true       # retry click via JS if WebDriver fails
```

## 🏗️ Architecture

```
pyshaft/
├── pyshaft/                 # main package
│   ├── config.py           # pyshaft.toml loader
│   ├── session.py          # thread-local driver storage
│   ├── core/               # engine modules
│   │   ├── driver_factory.py
│   │   ├── locator.py      # dual locator: semantic + CSS/XPath
│   │   ├── wait_engine.py  # auto-wait pipeline
│   │   └── action_runner.py # locate → wait → execute → log
│   └── web/                # web automation API
│       ├── navigation.py
│       ├── interactions.py
│       ├── inputs.py
│       └── assertions.py
├── pytest_pyshaft/          # pytest plugin
│   └── plugin.py
├── pyproject.toml
└── pyshaft.toml            # default config
```

## 📌 Key Features

- **Semantic locators** — `click("Login button")` auto-resolves to the right element
- **Auto-wait** — every action waits for element readiness silently
- **Zero config** — sensible defaults for everything
- **JS click fallback** — automatic retry via JavaScript when WebDriver click fails
- **Configurable sessions** — session/module/function scope
- **Screenshot on failure** — automatic capture

## 📋 Requirements

- Python ≥ 3.10
- selenium ≥ 4.0
- webdriver-manager ≥ 4.0

## 📄 License

MIT


