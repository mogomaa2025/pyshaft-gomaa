# PyShaft — Feature Review & Integration Prompt

Copy and paste this prompt to any AI after you add or update a feature.

---

## PROMPT (copy below)

```
I just added/updated a feature in PyShaft. Review and integrate it properly.

## Project Location
d:\automation\me\pyshaft\

## Your Tasks (do ALL of them, in order)

### 1. Understand the Architecture
Read these files first:
- pyshaft/web/__init__.py → WebEngine class (chainable web API)
- pyshaft/web/locators.py → Locator class (fluent element finder)
- pyshaft/api/__init__.py → ApiEngine class (chainable REST API)
- pyshaft/core/locator.py → DualLocator + _build_structured_chain
- pyshaft/core/action_runner.py → run_action / run_driver_action pipeline

### 2. Check for Bugs
Look for these common issues:
- **Signature mismatch**: WebEngine methods must match the underlying module functions exactly. If a module function takes `**kwargs`, the WebEngine wrapper must too. (Example bug: `get_by_role(role, name, exact)` vs `get_by_role(role, **kwargs)`)
- **Circular imports**: web/__init__.py must NOT do `from pyshaft import api` at module level. Use lazy imports inside methods/properties.
- **Missing return self**: Every WebEngine method that performs an action MUST return `self` for chaining. Methods that return data (get_url, get_title) return the data instead.
- **Locator actions must return `web`**: Every action on a Locator (click, type_text, hover, etc.) must `from pyshaft.web import web` and `return web` so the user can chain back.

### 3. Unify the Code
Apply these rules:
- If a new web function was added to a submodule (e.g., interactions.py, inputs.py), it MUST also be exposed on WebEngine in web/__init__.py
- If a new API method was added to api/methods.py, it MUST also be exposed on ApiEngine in api/__init__.py (both short and long name)
- All element-targeted actions MUST go through `run_action()` for auto-wait + retry
- All driver-targeted actions MUST go through `run_driver_action()`
- Locator._get_final_selector() generates `key=value` strings. The core DualLocator._build_structured_chain() must handle any new keys.

### 4. Update Tests
Open tests/unit/test_regression.py and add tests for the new feature:
- Import smoke test (does the new function import without error?)
- WebEngine method existence test (does web.new_method exist and is callable?)
- If it's a locator feature: does it generate the correct selector string?
- If it's an API feature: does it chain properly?

### 5. Run Tests
Run: `python -m pytest tests/unit/ -v`
ALL tests must pass. If any fail, fix them.

### 6. Update Documentation
Update how.md with a usage example of the new feature.

## Architecture Rules Summary

| Layer | File | Returns | Purpose |
|-------|------|---------|---------|
| WebEngine | web/__init__.py | `self` (WebEngine) | Top-level chainable API |
| Locator | web/locators.py | `web` (WebEngine) | Element-level fluent API |
| ApiEngine | api/__init__.py | ApiResponse | Top-level chainable API |
| ApiResponse | api/response.py | `self` (ApiResponse) | Response assertion chain |
| Actions | web/interactions.py, inputs.py | None | Raw action functions |
| Core | core/action_runner.py | varies | Auto-wait + retry pipeline |
| Core | core/locator.py | WebElement | Semantic element resolution |

## Chaining Rules
- `web.method()` → returns `web` (WebEngine) → can chain more web methods
- `web.get_by_role(...)` → returns `Locator` → can chain `.click()`, `.type_text()`, etc.
- `locator.click()` → returns `web` (WebEngine) → can chain more web methods
- `api.get(...)` → returns `ApiResponse` → can chain `.assert_status()`, `.assert_json()`
- `web.api` → returns `api` (ApiEngine) → bridges web → api

## Test Command
python -m pytest tests/unit/ -v
```

---

**Usage**: After making changes, paste the prompt above into any AI chat along with a description of what you changed.
