# PyShaft — The Definitive Usage Guide

PyShaft provides a unified, readable API for web and API automation. Designed for manual testers with low code skills.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Locator Syntax](#2-locator-syntax)
3. [Actions](#3-actions)
4. [Assertions](#4-assertions)
5. [Chaining](#5-chaining)
6. [Filters & Inside](#6-filters--inside)
7. [Index Ranges](#7-index-ranges)
8. [Configuration](#8-configuration)
9. [Page Objects](#9-page-objects)
10. [API Testing](#10-api-testing)
11. [Recorder GUI](#11-recorder-gui)

---

## 1. Quick Start

```python
from pyshaft import web as w
from pyshaft import role, textbox, button, label, placeholder, heading, modal, id_

# Open a page
w.open_url("https://example.com")

# Click a button
w.click(role, button).nth(1)

# Type into input
w.type("hello world", role, textbox).filter(placeholder="email")

# Assert
w.assert_text("Welcome", role, heading)
w.assert_visible(role, modal)
```

---

## 1b. Import Constants

All locator types and element names are exported from pyshaft:

```python
from pyshaft import (
    # Core locator types
    role, text, label, placeholder, testid, id_, cls, css_, xpath, tag, attr, any_,
    # Text modifiers
    exact, contain, starts, contains,
    # HTML elements
    button, textbox, input_, checkbox, radio, link, menu, menuitem,
    dialog, modal, form, heading, alert, spinner, image, listbox, option, combobox,
    # Type aliases
    password, email, submit,
)
```

> **Note:** Use `id_` (not `id`), `cls` (not `class`), `css_` (not `css`), and `input_` (not `input`) to avoid Python keyword clashes.

---

## 2. Locator Syntax

### 2.1 Locator Types

| Type               | Syntax                          | Example                         | Description           |
| ------------------ | ------------------------------- | ------------------------------- | --------------------- |
| **Role**           | `w.click(role, value)`          | `w.click(role, button)`         | By ARIA role          |
| **Text (exact)**   | `w.click.exact(text="value")`   | `w.click.exact(text="Submit")`  | Exact text match      |
| **Text (contain)** | `w.click.contain(text="value")` | `w.click.contain(text="Log")`   | Text contains         |
| **Label**          | `w.click(label, value)`         | `w.click(label, "Email")`       | Via label element     |
| **Placeholder**    | `w.click(placeholder, value)`   | `w.click(placeholder, "email")` | Input placeholder     |
| **Test ID**        | `w.click(testid, value)`        | `w.click(testid, "login-btn")`  | data-testid           |
| **ID**             | `w.click(id_, value)`           | `w.click(id_, "username")`      | CSS #id               |
| **ID Starts**      | `w.click.starts(id="value")`    | `w.click.starts(id="btn-")`     | ID starts with        |
| **ID Contains**    | `w.click.contain(id="value")`   | `w.click.contain(id="name")`    | ID contains           |
| **Class**          | `w.click(cls, value)`           | `w.click(cls, "btn-primary")`   | CSS .class            |
| **CSS**            | `w.click(css_, value)`          | `w.click(css_, "#id .class")`   | Raw CSS selector      |
| **XPath**          | `w.click(xpath, value)`         | `w.click(xpath, "//button")`    | Raw XPath             |
| **Tag**            | `w.click(tag, value)`           | `w.click(tag, "div")`           | HTML tag name         |
| **Attr**           | `w.click(attr, name)`           | `w.click(attr, "data-id")`      | Has attribute         |
| **Any**            | `w.click(any_, value)`          | `w.click(any_, "text")`         | Any element with text |

### 2.2 Property Chains (Modifiers)

Use fluent constraint chaining directly on actions for precise matching:

```python
# Exact match
w.click.exact(role=button)
w.click.exact(text="Login")

# Partial substring match
w.click.contain(text="Submit")
w.assert_visible.contain(id="btn-submit")

# Starts with prefix match
w.click.starts(id="btn-")
```

---

## 3. Actions

### 3.1 Click

```python
# Basic
w.click(role, button)

# With index (1st button)
w.click(role, button).nth(1)

# With filters (use class_ to avoid Python keyword clash)
w.click(role, button).filter(class_="primary", tag="div")

# With inside (structural boundaries)
w.click.contain(text="Submit").inside(id_, "form-container")
```

### 3.2 Type

```python
# Basic
w.type("hello world", role, textbox)

# With filters
w.type("email@test.com", role, textbox).filter(placeholder="email")

# ID-based
w.type("admin", id_, "username")
```

### 3.3 Hover & Scroll

```python
# Hover
w.hover(role, menuitem).nth(1)

# Scroll to element
w.scroll(role, heading)

# Scroll to bottom
w.scroll_to_bottom()
```

### 3.4 Drag & Drop

```python
w.drag(role, "handle", role, "target-zone")
```

### 3.5 Select, Check, Uncheck

```python
# Select dropdown option (Native Select)
w.select("Option 1", role, listbox)

# Built-in Checkbox/Radio Handlers
w.check(role, checkbox).nth(1)
w.uncheck(role, checkbox).nth(1)
```

### 3.6 Advanced Interactions

```python
# Upload File (equivalent to Choose File)
w.upload("C:\\path\\to\\file.png", id_, "file-upload")

# Date Pickers
# pick_date acts like a type combined with an ENTER keypress
w.pick_date("10/25/2026", id_, "calendar-input")

# Dynamic Select (UI Framework Dropdowns like spans/divs)
w.select_dynamic("Option Text", id_, "dropdown-container")

# IFrame Switching
w.switch_to_iframe(id_, "payment-frame")
w.type("1234", id_, "card-number")
w.switch_to_default() # Back to main document

# Alerts / JS Popups
w.accept_alert()
w.dismiss_alert()
text = w.get_alert_text()

# Force Click (Ignore clickability/visibility checks)
w.click(role, button).filter(force=True)

# Hidden Elements (Included in searches via force flag)
w.type("secret", id_, "hidden-input").filter(force=True)

# Remove Element via JS
w.remove_element(id_, "annoying-banner")
```

### 3.7 Lazy Execution

All actions build locators without executing. The action runs implicitly when the next action is called, or explicitly with `.execute()`:

```python
# Just builds locator (no execution yet)
loc = w.click(role, button)

# Add filters/nth without executing
loc = w.click(role, button).filter(class_="primary").nth(1)

# Execute explicitly
loc.execute()

# Or chain with wait methods (they auto-execute)
w.click(role, button).wait(role, "success-message").visible()

# Assertions also auto-execute
w.assert_visible(role, modal).execute()
w.assert_text("Welcome", role, heading).execute()
```

### 3.7 Submit

```python
w.submit(role, form)
```

---

## 4. Assertions

### 4.1 Text Assertions

```python
# Element text contains
w.assert_text("Welcome", role, heading)

# Element text exact
w.assert_text.exact("Hello World", role, heading)

# Contains text (alias for assert_text)
w.assert_contain_text("Welcome", role, heading)
```

### 4.2 Visibility Assertions

```python
# Must be visible
w.assert_visible(role, modal)
w.assert_visible(role, spinner).nth(1)

# Must be hidden
w.assert_hidden(role, modal)
```

### 4.3 State Assertions

```python
# Must be enabled
w.assert_enabled(role, button)
w.assert_enabled(role, button).nth(1)

# Must be disabled
w.assert_disabled(role, button)

# Must be checked
w.assert_checked(role, checkbox)
```

### 4.4 Page Assertions

```python
# Page title (exact)
w.assert_title("Dashboard")
w.assert_title("Home", timeout=5)

# Page title contains
w.assert_contain_title("Dash")

# Current URL (exact)
w.assert_url("https://example.com/dashboard")

# URL contains
w.assert_contain_url("dashboard")
```

### 4.5 Attribute Assertions

```python
# Exact attribute match
w.assert_attribute("disabled", "true", role, button)

# Attribute contains
w.assert_contain_attribute("class", "active", role, button)
```

### 4.6 Snapshot & Advanced Assertions

```python
# Wait for UI or loading overlay to disappear
w.wait_until_disappears(id_, "ajax-loader", timeout=10)

# Visual Regression Testing (Snapshot comparison)
w.assert_snapshot("dashboard_baseline")
```

# Element attribute contains

w.assert_contain_attribute("class", "active", role, button)

````

---

## 5. Chaining

### 5.1 Basic Chain

```python
# Action returns Locator for further chaining
w.click(role, button).nth(1).should_be_visible()
w.type("email", role, textbox).filter(placeholder="email").should_be_enabled()
````

### 5.2 Infinite Action Sequence

Chain across different independent actions in a single fluent flow. Wrap in `()` for clean multi-line formatting:

```python
(w.type("student").exact(tag="input").nth(1)
  .type("Password123").exact(tag="input").nth(2)
  .click.contain(text="Submit").inside(id_, "form")
  .assert_contain_title("Successfully")
  .assert_contain_text("Successfully").should_be_visible())
```

### 5.3 Chaining on the Same Element

You can perform multiple actions on the exact same element sequentially without repeating the locator:

```python
# Hover over a menu, then click it
w.hover(id_, "dropdown-menu").click()

# Clear an input, type into it, then press ENTER
w.clear(role, textbox).type("search query").press_key("ENTER")
```

### 5.3 Assertion Chain

```python
# Assert then continue (falls through seamlessly)
(w.click(role, submit)
   .assert_visible(role, "success-message")
   .assert_text("Success", role, heading))
```

---

## 6. Filters & Inside

### 6.1 Filters

Add constraints to refine element selection. Use `class_` since `class` is a Python keyword:

```python
# Tag filter
w.click(role, button).filter(tag="div")

# Class filter
w.click(role, button).filter(class_="primary")

# Multiple filters
w.click(role, button).filter(tag="div", class_="container")
w.click(role, input_).filter(type="text", placeholder="email")
```

### 6.2 Inside (Structural)

Find an element as a descendant within a parent container:

```python
# Inside by ID
w.click(role, button).inside(id_, "modal")

# Inside by tag
w.click(role, input_).inside(tag, "form")

# Inside by role
w.click(role, option).inside(role, dialog)
```

### 6.3 Combined

```python
w.click.contain(text="Login") \
    .filter(class_="primary") \
    .inside(id_, "form-container") \
    .nth(1)
```

---

## 7. Index Ranges

### 7.1 Single Index

| Syntax     | Description  |
| ---------- | ------------ |
| `.nth(1)`  | 1st element  |
| `.nth(2)`  | 2nd element  |
| `.nth(-1)` | Last element |

### 7.2 Range (Batch Actions)

| Syntax      | Description      |
| ----------- | ---------------- |
| `.nth(1:5)` | Elements 1–5     |
| `.nth(0:3)` | First 3 elements |
| `.nth(5:)`  | From 5th to end  |

```python
# Click first 3 buttons
w.click(role, button).nth(1:3)

# Check all checkboxes in a group
w.check(role, checkbox).nth(1:10)
```

### 7.3 Shortcuts

```python
# First element
w.click(role, button).first()

# Last element
w.click(role, button).last()
```

---

## 8. Configuration

### 8.1 Retry

Automatically retry failed actions:

```python
# Retry 3 times with 1.5x backoff
w.retry(3).click(role, button)
w.retry(count=3, backoff=2.0).type("text", role, input_)
```

### 8.2 Steps

Named test steps for logging:

```python
w.step("Login").type("admin", id_, "username") \
               .type("secret", id_, "password") \
               .click(role, button)
w.step("Verify dashboard").assert_visible(role, "dashboard")
```

### 8.3 Debug Mode

Highlight elements and log info for debugging:

```python
w.click(role, button).debug()
w.type("text", role, input_).debug()
```

---

## 9. Page Objects

### 9.1 Create Page Object

```python
login_page = w.page({
    "username": w.input(role, textbox).filter(placeholder="email"),
    "password": w.input(role, password),
    "submit": w.click(role, button),
    "error": w.text(role, alert),
})
```

### 9.2 Use Page Object

```python
login_page.username.type("admin@example.com")
login_page.submit.click()
login_page.error.should_be_visible()
```

---

## 10. API Testing

### 10.1 Basic Requests

```python
from pyshaft import api as a

# GET request
a.get("https://api.example.com/users")

# POST request
a.post("https://api.example.com/users", {"name": "John"})

# PUT request
a.put("https://api.example.com/users/1", {"name": "Jane"})

# DELETE request
a.delete("https://api.example.com/users/1")
```

### 10.2 Assertions

```python
a.get("/users").assert_status(200)
a.get("/users/1").assert_json("name", "John")
a.get("/users").assert_header("content-type", "application/json")
```

### 10.3 Fluent Chain

```python
(a.get("https://api.example.com/users")
   .assert_status(200)
   .assert_json("data.0.name", "John")
   .extract_json("data.0.id", "user_id"))
```

### 10.4 State & Store

PyShaft API allows you to extract data from a response and reuse it in subsequent requests.

#### In Python Scripts:

You can use `api.stored()` to retrieve values, OR use the more readable `{{variable_name}}` syntax directly in your request chains.

```python
# 1. Extract value from response and store as 'll'
(api.get("https://postman-echo.com/get")
   .extract_json("$.headers.content-length", "ll"))

# 2. OPTION A: Retrieve it using api.stored()
length = api.stored("ll")
api.get(f"/verify?len={length}")

# 3. OPTION B: Use the built-in interpolation (Recommended)
# PyShaft automatically resolves {{ll}} from memory
(api.post("/check")
   .body({"original_length": "{{ll}}"})
   .header("X-Check", "{{ll}}")
   .assert_status(200))

# Clear all stored data
api.clear()
```

#### In the Inspector GUI (`inspectapi`):

1. **Extract**: Right-click any value in the **Response JSON Tree** and select **Extract to Variable**. Give it a name (e.g., `ll`).
2. **Reuse**: In any subsequent request, use the `{{variable_name}}` syntax in the **URL**, **Headers**, or **JSON Body**.
   - Example URL: `https://api.example.com/pets/{{ll}}`
   - Example Body: `{"id": "{{ll}}", "name": "New Name"}`
3. **Verify**: The **Workflow Map** will automatically show an arrow connecting the producing step to the consuming step.

## Retrying API Steps

You can configure automatic retries for API steps in the request builder. This is useful for flaky endpoints or transient network issues.

- **Count**: Number of retry attempts (0 = no retry)
- **Mode**: What to retry on (all, timeout, fail, status, exception)
- **Backoff**: Multiplier for exponential backoff (1.0 = no backoff)

In generated code, this appears as:

```python
api.get('/endpoint').retry(3, mode='timeout', backoff=2.0)
```

This will retry up to 3 times on timeout, doubling the wait each time.

---

## 11. Recorder GUI

PyShaft includes a built-in GUI recorder for creating tests visually — no code required.

### 11.1 Launch

```bash
# Via CLI
pyshaft-recorder

# With a start URL
pyshaft-recorder --url https://example.com

# Via Python
python -m pyshaft.recorder
```

### 11.2 Modes

The recorder operates in three modes via the toolbar **Mode** selector:

| Mode             | Default | Description                                                                             |
| ---------------- | ------- | --------------------------------------------------------------------------------------- |
| **🔍 Inspector** | ✅      | Browse & click elements → popup appears with actions/assertions → create steps manually |
| **⏺ Record**     |         | Auto-capture all browser interactions (clicks, typing, selects) as steps                |
| **🔍+⏺ Both**    |         | Inspector popup + auto-recording simultaneously                                         |

### 11.3 Inspector Workflow

1. Navigate to a page in the built-in browser
2. Click any element → a **floating popup** appears showing:
   - Element tag & best locator preview
   - Locator choices ranked by stability (green=high, yellow=medium, red=low)
   - Modifier toggles (Exact / Contain / Starts) + nth input
   - **Action buttons**: Click, Type, Hover, Scroll, Check, Select, etc.
   - **Assertion buttons**: Visible, Hidden, Text, Enabled, Disabled, etc.
3. Pick a locator strategy → click an action → step is created
4. Steps appear in the left panel, code updates live in the bottom panel

### 11.4 Code Output

Generated code uses PyShaft fluent API with chain mode by default:

```python
import pytest
from pyshaft import web as w, role, button, textbox, id_

@pytest.mark.pyshaft_web
def test_untitled_test():
    w.open_url("https://example.com")
    (w.type("admin", role, textbox).filter(placeholder="email")
     .type("secret", id_, "password")
     .click(role, button).filter(type="submit"))
```

Toggle between **Chain** (fluent chaining) and **Flat** (one action per line) via the dropdown in the Code tab.

### 11.5 Keyboard Shortcuts

| Shortcut | Action            |
| -------- | ----------------- |
| `Ctrl+R` | Toggle recording  |
| `Ctrl+I` | Toggle inspector  |
| `Ctrl+K` | Command palette   |
| `Ctrl+Z` | Undo              |
| `Ctrl+S` | Save session      |
| `Ctrl+E` | Export code (.py) |

---

## New Feature: Add Custom Actions/Assertions

PyShaft now allows you to add your own custom actions and assertions directly from the Inspector GUI (`pyshaft inspect`) and API Inspector (`pyshaft inspectapi`).

### How to Add a Custom Feature

- **Web Inspector (pyshaft inspect):**
  1. Open the Inspector GUI: `pyshaft inspect` (or `pyshaft-recorder`)
  2. Press `Ctrl+K` to open the Command Palette.
  3. Type your desired action or assertion name. If it doesn't exist, select `Add Custom Action` or `Add Custom Assertion` from the palette.
  4. Fill in the details (name, code snippet, etc.) in the dialog.
  5. The new feature will appear in the palette and can be used in your test steps.

- **API Inspector (pyshaft inspectapi):**
  1. Open the API Inspector: `pyshaft inspectapi`
  2. In the request builder or assertion/extraction panels, click `Add Custom` or use the context menu to define a new action/assertion.
  3. Enter the details and save. The new feature will be available for all API workflows.

> **Tip:** Custom features are saved in your user config and persist across sessions. You can edit or remove them anytime from the Command Palette or settings.

---

## Complete Examples

### Example 1: Login Flow

```python
from pyshaft import web as w, role, textbox, button, heading, password

def test_login():
    w.open_url("https://example.com/login")

    w.type("admin@example.com", role, textbox).filter(placeholder="email")
    w.type("secret123", role, password)
    w.click(role, button).filter(type="submit")

    w.assert_url("https://example.com/dashboard")
    w.assert_text("Welcome, Admin", role, heading)
```

### Example 2: Fluent Chain Login

```python
from pyshaft import web as w, role, textbox, button, heading, id_

def test_login_chain():
    w.open_url("https://example.com/login")

    (w.type("admin@example.com", role, textbox).filter(placeholder="email")
      .type("secret123", id_, "password")
      .click(role, button).filter(type="submit")
      .assert_contain_url("dashboard")
      .assert_text("Welcome", role, heading))
```

### Example 3: Form with Validation

```python
from pyshaft import web as w, role, button, textbox

def test_form_validation():
    w.open_url("https://example.com/form")

    # Submit empty form
    w.click(role, button).filter(type="submit")

    # Assert validation errors
    w.assert_visible(role, "error-message").nth(1)
    w.assert_visible(role, "error-message").nth(2)

    # Fill form
    w.type("John", role, textbox).filter(name="firstName")
    w.type("Doe", role, textbox).filter(name="lastName")
    w.type("john@example.com", role, textbox).filter(name="email")

    # Submit
    w.click(role, button).filter(type="submit")

    # Assert success
    w.assert_visible(role, "success-message")
```

### Example 4: Table Interaction

```python
from pyshaft import web as w, role, button, textbox, tag

def test_table():
    w.open_url("https://example.com/users")

    # Click edit on 2nd row
    w.click(role, button).inside(tag, "tr").nth(2).filter(class_="edit")

    # Update user
    w.type("Jane", role, textbox).filter(name="name")
    w.click(role, button).filter(type="submit")

    # Verify update
    w.assert_text("Jane", tag, "td").nth(2)
```

### Example 5: API + Web Hybrid

```python
from pyshaft import web as w, api as a, id_

def test_api_then_web():
    # Create user via API
    (a.post("/users", {"name": "Test User"})
       .assert_status(201)
       .extract_json("id", "new_user_id"))

    # Verify in web
    w.open_url("/users")
    w.assert_visible(id_, f"user-{a.stored('new_user_id')}")
```

---

## Configuration File (pyshaft.toml)

```toml
[browser]
browser = "chrome"
headless = false

[waits]
default_element_timeout = 10

[report]
screenshot_on_fail = true
```

---

## Tips for Manual Testers

1. **Start simple**: Use `role` to find elements by their function
2. **Use .nth()**: When multiple elements match, pick the right one
3. **Add filters**: Refine with `.filter(class_="x")` — use `class_` not `class`
4. **Use property chains**: `w.click.contain(text="Submit")` for partial matches
5. **Debug first**: Use `.debug()` to see what you're selecting
6. **Chain everything**: `(w.click(...).type(...).assert_visible(...))` in one flow
7. **Use the recorder**: `pyshaft-recorder` to generate code visually

---

## Visual Tracer

PyShaft includes a powerful **Visual Tracer** that allows you to scrub through every step of your test execution with corresponding screenshots.

### Enabling the Tracer

To capture a visual trace, enable per-step screenshots in your `pyshaft.toml`:

```toml
[report]
screenshot_on_step = true
output_dir = "pyshaft-report"
```

### Using the Tracer Dashboard

1. Run your tests: `pytest --pyshaft`
2. Launch the report dashboard: `pyshaft report serve`
3. In the dashboard, click on a test result.
4. Switch to the **🔍 Tracer** tab.
5. Click through the steps on the left to see the browser state (screenshot) at that exact moment on the right.

---

## Need Help?

- ❌ Element not found? → Try `.nth(1)` or add more filters
- ❌ Multiple elements found? → Use `.nth(N)` to pick a specific one
- ❓ What locator to use? → Start with `role` for most elements
- 🔍 Need to inspect? → Run `pyshaft-recorder` for visual element selection
