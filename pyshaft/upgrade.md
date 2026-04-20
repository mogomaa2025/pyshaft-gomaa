# PyShaft Developer & Upgrade Guide

This document provides a technical guide for adding new features, modifying existing ones, or upgrading the PyShaft framework. It is intended for both humans and AI agents.

---

## 🏗 Interaction Architecture

PyShaft uses a structured pipeline to ensure consistent logging, error handling, and auto-waiting across all web interactions. **Never call `driver` methods or `element` methods directly** in public functions; always wrap them in the action runners.

### 1. Element Actions (`run_action`)
Use `run_action` for anything that interacts with a specific element. It automatically handles:
- **Locator Resolution**: Resolves CSS/XPath/Semantic strings via `DualLocator`.
- **Auto-Wait**: Passes the element through the `WaitEngine` readiness checks.
- **Logging**: Captures the action in the reporter.

**Pattern:**
```python
from pyshaft.core.action_runner import run_action

def my_new_action(locator: str, arg1: str):
    def _logic(element: WebElement):
        # element is already resolved and validated as ready
        element.send_keys(arg1)
    
    return run_action("my_new_action", locator, _logic)
```

### 2. Driver Actions (`run_driver_action`)
Use `run_driver_action` for browser-level tasks like navigation, alerts, window switching, or custom JS where a specific target element is not the primary focus.

**Pattern:**
```python
from pyshaft.core.action_runner import run_driver_action

def switch_to_context(name: str):
    def _logic(driver: WebDriver):
        driver.switch_to.context(name)
        
    run_driver_action("switch_to_context", name, _logic)
```

---

## 🛠 Adding a New Web Module

1.  **Create the file** in `pyshaft/web/`.
2.  **Import dependencies**:
    - `from __future__ import annotations`
    - `from pyshaft.core.action_runner import run_action, run_driver_action`
    - `from pyshaft.session import session_context`
3.  **Implement functions** using the runners described above.
4.  **Export in `pyshaft/web/__init__.py`**:
    - Add the import from your module.
    - Add the function names to the `__all__` list.

---

## 🕵️‍♂️ Using the Core Engines

### DualLocator (Semantic Resolution)
Always use `DualLocator.resolve(driver, description)` if you need to manually find an element (though `run_action` usually does this for you).
- Supported: `css=...`, `xpath=...`, `id=...`, `text=...`, `shadow > ...`, and plain English "labels".

### WaitEngine (Actionability)
The `WaitEngine` performs a 5-point check:
1. `DOM Presence`
2. `Visibility` (Opacity > 0, displayed, non-zero size)
3. `Enabled`
4. `Position Stable` (Detects animations)
5. `Not Covered` (No overlays)

To wait for custom conditions, use `WaitEngine.wait_for_condition(lambda: ..., "Description")`.

---

## ✅ Assertion Standards

Public assertions should be implemented in `pyshaft/web/assertions.py` using a **polling loop**.
- Catch `Exception` inside the loop.
- Only raise `AssertionError` if the condition isn't met after the timeout.
- Use `run_driver_action` for the final wrap.

---

## 🧪 Testing Requirements

Every new feature must have a corresponding test in `tests/unit/`.
- Use the `driver` fixture (if available/required) or mock the components.
- Run the full suite before committing: `pytest tests/unit/ -v`.

---

## 📜 Coding Rules
- **Formatting**: 4-space indentation.
- **Typing**: Use type hints for all parameters and return values.
- **Logging**: Use the module-specific logger (e.g., `logger = logging.getLogger(__name__)`).
- **No Side Effects**: Avoid printing to `stdout`. Use the logging system.
