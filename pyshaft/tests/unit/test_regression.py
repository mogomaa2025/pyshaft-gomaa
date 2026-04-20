"""PyShaft regression tests — ensures all modules import, construct, and chain correctly.

These tests do NOT require a browser. They validate:
    1. All modules import without errors
    2. WebEngine is a singleton with correct method signatures
    3. Fluent Locator API constructs selectors correctly
    4. Locator chaining types (get_by_role, get_by_text, etc.) work
    5. API module: response wrapper, store, and client
    6. Structured locator parsing (role=textbox type=password)
    7. Action runner module loads correctly
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# ============================================================================
# 1. Import Smoke Tests — every module must import cleanly
# ============================================================================


class TestImports:
    """Verify every public module imports without errors."""

    def test_import_web_module(self):
        from pyshaft.web import web
        assert web is not None

    def test_import_web_engine_class(self):
        from pyshaft.web import WebEngine
        assert WebEngine is not None

    def test_import_locators(self):
        from pyshaft.web.locators import (
            Locator, locator, get_by_role, get_by_text,
            get_by_label, get_by_placeholder, get_by_test_id,
        )

    def test_import_interactions(self):
        from pyshaft.web.interactions import (
            click, click_all, double_click, right_click, hover, drag_to,
        )

    def test_import_inputs(self):
        from pyshaft.web.inputs import (
            type_text, clear_text, press_key, upload_file,
            get_text, get_value, get_attribute,
            select_option, check_checkbox, uncheck_checkbox,
        )

    def test_import_navigation(self):
        from pyshaft.web.navigation import (
            open_url, go_back, go_forward, refresh,
            get_url, get_title,
            close_window, switch_to_window, switch_to_frame,
            switch_to_parent_frame, switch_to_default_content,
            scroll, scroll_to_bottom, scroll_to_top,
        )

    def test_import_assertions(self):
        from pyshaft.web.assertions import (
            assert_title, assert_title_contains,
            assert_url, assert_url_contains,
            assert_text, assert_visible, assert_hidden,
            assert_attribute, assert_enabled, assert_disabled,
            assert_checked,
        )

    def test_import_alerts(self):
        from pyshaft.web.alerts import (
            accept_alert, dismiss_alert, get_alert_text, type_alert,
        )

    def test_import_collections(self):
        from pyshaft.web.collections import (
            count, get_all, get_all_text, first, last, nth,
        )

    def test_import_keyboard(self):
        from pyshaft.web.keyboard import hotkey, global_press

    def test_import_storage(self):
        from pyshaft.web.storage import (
            get_local_storage, set_local_storage, clear_local_storage,
            get_session_storage, set_session_storage, clear_session_storage,
        )

    def test_import_tables(self):
        from pyshaft.web.tables import (
            get_table_rows, get_table_cell, get_table_column, assert_table_cell,
        )

    def test_import_screenshot(self):
        from pyshaft.web.screenshot import take_screenshot, take_element_screenshot

    def test_import_js_helpers(self):
        from pyshaft.web.js_helpers import (
            execute_js, highlight_element, scroll_into_view, set_value_js,
        )

    def test_import_waits(self):
        from pyshaft.web.waits import (
            wait_for_element, wait_for_visible, wait_for_hidden,
            wait_for_text, wait_for_url, wait_for_title, wait_until,
        )

    def test_import_api_module(self):
        from pyshaft.api import (
            send_get, send_post, send_put, send_patch, send_delete,
            store_data, get_stored, clear_store,
        )

    def test_import_api_response(self):
        from pyshaft.api.response import ApiResponse

    def test_import_api_store(self):
        from pyshaft.api.store import store_data, get_stored, clear_store

    def test_import_api_client(self):
        from pyshaft.api.client import get_api_client, close_api_client

    def test_import_core_action_runner(self):
        from pyshaft.core.action_runner import run_action, run_driver_action

    def test_import_core_locator(self):
        from pyshaft.core.locator import DualLocator, detect_mode

    def test_import_core_wait_engine(self):
        from pyshaft.core.wait_engine import WaitEngine

    def test_import_config(self):
        from pyshaft.config import get_config, load_config, Config

    def test_import_session(self):
        from pyshaft.session import session_context


# ============================================================================
# 2. WebEngine Singleton & Method Signatures
# ============================================================================


class TestWebEngine:
    """Verify WebEngine is properly constructed and methods exist."""

    def test_web_is_singleton(self):
        from pyshaft.web import web
        from pyshaft.web import WebEngine
        assert isinstance(web, WebEngine)

    def test_web_has_navigation_methods(self):
        from pyshaft.web import web
        assert callable(web.open_url)
        assert callable(web.go_back)
        assert callable(web.go_forward)
        assert callable(web.refresh)
        assert callable(web.scroll)
        assert callable(web.scroll_to_bottom)
        assert callable(web.get_url)
        assert callable(web.get_title)

    def test_web_has_interaction_methods(self):
        from pyshaft.web import web
        assert callable(web.click)
        assert callable(web.click_all)
        assert callable(web.double_click)
        assert callable(web.right_click)
        assert callable(web.hover)
        assert callable(web.drag)

    def test_web_has_input_methods(self):
        from pyshaft.web import web
        assert callable(web.type)
        assert callable(web.clear)
        assert callable(web.delete)
        assert callable(web.select)
        assert callable(web.check)
        assert callable(web.uncheck)

    def test_web_has_assertion_methods(self):
        from pyshaft.web import web
        assert callable(web.assert_text)
        assert callable(web.assert_visible)
        assert callable(web.assert_hidden)
        assert callable(web.assert_title)
        assert callable(web.assert_url)

    def test_web_has_locator_factories(self):
        from pyshaft.web import web
        assert callable(web.locator)
        assert callable(web.wait)

    def test_web_has_alert_methods(self):
        from pyshaft.web import web
        assert callable(web.accept_alert)
        assert callable(web.dismiss_alert)

    def test_web_has_screenshot_method(self):
        from pyshaft.web import web
        assert callable(web.take_screenshot)


# ============================================================================
# 3. Fluent Locator Construction
# ============================================================================


class TestLocatorConstruction:
    """Verify Locator objects are constructed and produce correct selectors."""

    def test_locator_by_css(self):
        from pyshaft.web.locators import locator
        loc = locator("#submit")
        assert loc._get_final_selector() == "#submit"

    def test_locator_by_role_name(self):
        from pyshaft.web.locators import Locator
        loc = Locator(locator_type="role", value="textbox", name="Username")
        sel = loc._build_selector()
        assert "role=textbox" in sel
        assert "name=Username" in sel or "Username" in sel

    def test_locator_by_role_type(self):
        from pyshaft.web.locators import Locator
        loc = Locator(locator_type="role", value="textbox", type="password")
        sel = loc._build_selector()
        assert "role=textbox" in sel
        assert "type=password" in sel or "password" in sel

    def test_locator_by_role_name_and_type(self):
        from pyshaft.web.locators import Locator
        loc = Locator(locator_type="role", value="button", name="Submit", type="submit")
        sel = loc._build_selector()
        assert "role=button" in sel

    def test_locator_by_text(self):
        from pyshaft.web.locators import Locator
        loc = Locator(locator_type="text", value="Submit")
        sel = loc._build_selector()
        assert "text" in sel
        assert "Submit" in sel

    def test_locator_by_label(self):
        from pyshaft.web.locators import Locator, get_by_label
        loc = Locator(locator_type="label", value="Email")
        sel = loc._build_selector()
        assert "label" in sel
        assert "Email" in sel
        loc = get_by_label("Email")
        sel = loc._get_final_selector()
        assert "label=Email" in sel

    def test_locator_by_placeholder(self):
        from pyshaft.web.locators import Locator
        loc = Locator(locator_type="placeholder", value="Enter password")
        sel = loc._build_selector()
        assert "placeholder" in sel

    def test_locator_by_test_id(self):
        from pyshaft.web.locators import Locator
        loc = Locator(locator_type="testid", value="login-btn")
        sel = loc._build_selector()
        assert "testid" in sel

    def test_locator_nth(self):
        from pyshaft.web.locators import Locator
        loc = Locator(locator_type="role", value="button")
        loc = loc.nth(1)
        assert loc._index == 1
        assert ">> index=0" in loc._build_selector()

    def test_locator_nth_second(self):
        from pyshaft.web.locators import Locator
        loc = Locator(locator_type="role", value="button")
        loc = loc.nth(2)
        assert loc._index == 2
        assert ">> index=1" in loc._build_selector()

    def test_locator_first(self):
        from pyshaft.web.locators import Locator
        loc = Locator(locator_type="role", value="button").first()
        assert loc._index == 1

    def test_locator_last(self):
        from pyshaft.web.locators import Locator
        loc = Locator(locator_type="role", value="button").last()
        assert loc._index == -1

    def test_locator_nth_preserves_filters(self):
        from pyshaft.web.locators import Locator
        loc = Locator(locator_type="role", value="textbox", name="User")
        loc = loc.nth(1)
        assert loc._index == 1
        sel = loc._build_selector()
        assert "role=textbox" in sel

    def test_locator_has_action_methods(self):
        from pyshaft.web.locators import Locator
        loc = Locator(locator_type="role", value="button")
        assert callable(loc.click)
        assert callable(loc.type)
        assert callable(loc.hover)
        assert callable(loc.scroll)
        assert callable(loc.delete)

    def test_locator_has_assertion_methods(self):
        from pyshaft.web.locators import Locator
        loc = Locator(locator_type="role", value="button")
        assert callable(loc.should_be_visible)
        assert callable(loc.should_be_hidden)
        assert callable(loc.should_have_text)
        assert callable(loc.should_have_attribute)


# ============================================================================
# 4. WebEngine → Locator Factory (the bug that was just fixed)
# ============================================================================


class TestWebEngineLocatorFactories:
    """Verify WebEngine methods work with new unified syntax."""

    def test_click_with_role(self):
        from pyshaft.web import web
        from pyshaft.web.locators import Locator
        # Lazy: returns Locator without executing
        loc = web.click("role", "button")
        assert isinstance(loc, Locator)

    def test_type_with_role(self):
        from pyshaft.web import web
        from pyshaft.web.locators import Locator
        # Lazy: returns Locator without executing
        loc = web.type("hello", "role", "textbox")
        assert isinstance(loc, Locator)

    def test_hover_with_role(self):
        from pyshaft.web import web
        from pyshaft.web.locators import Locator
        # Lazy: returns Locator without executing
        loc = web.hover("role", "menu")
        assert isinstance(loc, Locator)

    def test_assert_visible_with_role(self):
        from pyshaft.web import web
        from pyshaft.web.locators import Locator
        # Assertions are lazy - returns Locator without executing
        loc = web.assert_visible("role", "modal")
        assert isinstance(loc, Locator)

    def test_wait_returns_locator(self):
        from pyshaft.web import web
        from pyshaft.web.locators import Locator
        loc = web.wait("role", "spinner")
        assert isinstance(loc, Locator)

    def test_locator_factory(self):
        from pyshaft.web import web
        from pyshaft.web.locators import Locator
        loc = web.locator("#my-button")
        assert isinstance(loc, Locator)

    def test_locator_returns_locator(self):
        from pyshaft.web import web
        from pyshaft.web.locators import Locator
        loc = web.locator("css", "#my-button")
        assert isinstance(loc, Locator)
        assert "#my-button" in loc._build_selector()

    def test_locator_final_selector(self):
        from pyshaft.web import web
        from pyshaft.web.locators import Locator
        loc = web.locator("css", "#my-button")
        assert isinstance(loc, Locator)
        assert "#my-button" in loc._get_final_selector()


# ============================================================================
# 5. Structured Locator Parsing (DualLocator)
# ============================================================================


class TestStructuredLocatorParsing:
    """Verify _build_structured_chain parses role=X type=Y correctly."""

    def test_structured_chain_basic_role(self):
        """role=textbox alone now returns base tag strategies."""
        from pyshaft.core.locator import _build_structured_chain
        chain = _build_structured_chain("role=textbox")
        assert len(chain) > 0
        xpaths = [s for _, m, s in chain if m == "xpath"]
        assert any("//input" in x for x in xpaths)
        assert any("//textarea" in x for x in xpaths)

    def test_structured_chain_role_with_type(self):
        from pyshaft.core.locator import _build_structured_chain
        chain = _build_structured_chain("role=textbox type=password")
        assert len(chain) > 0
        # At least one XPath should contain @type='password'
        xpaths = [s for _, m, s in chain if m == "xpath"]
        assert any("@type='password'" in x for x in xpaths)

    def test_structured_chain_role_with_name(self):
        from pyshaft.core.locator import _build_structured_chain
        chain = _build_structured_chain("role=textbox text=Username")
        xpaths = [s for _, m, s in chain if m == "xpath"]
        assert any("Username" in x for x in xpaths)

    def test_structured_chain_button_role(self):
        from pyshaft.core.locator import _build_structured_chain
        chain = _build_structured_chain("role=button text=Submit")
        assert len(chain) > 0
        xpaths = [s for _, m, s in chain if m == "xpath"]
        assert any("button" in x for x in xpaths)

    def test_structured_chain_unknown_role(self):
        from pyshaft.core.locator import _build_structured_chain
        chain = _build_structured_chain("role=combobox text=Country")
        assert len(chain) > 0  # Falls back to //*

    def test_non_structured_returns_empty(self):
        from pyshaft.core.locator import _build_structured_chain
        chain = _build_structured_chain("Login button")
        assert chain == []


class TestDetectMode:
    def test_detect_mode_structured_is_unified(self):
        from pyshaft.core.locator import detect_mode
        mode = detect_mode("role=textbox")
        assert mode == "unified"


# ============================================================================
# 6. API Module Tests
# ============================================================================


class TestApiStore:
    """Verify API data store works correctly."""

    def test_store_and_retrieve(self):
        from pyshaft.api.store import store_data, get_stored, clear_store
        clear_store()
        store_data("user_id", 42)
        assert get_stored("user_id") == 42

    def test_retrieve_missing_key_raises(self):
        from pyshaft.api.store import get_stored, clear_store
        clear_store()
        with pytest.raises(KeyError, match="no_such_key"):
            get_stored("no_such_key")

    def test_clear_store(self):
        from pyshaft.api.store import store_data, get_stored, clear_store
        store_data("a", 1)
        store_data("b", 2)
        clear_store()
        with pytest.raises(KeyError):
            get_stored("a")

    def test_overwrite_key(self):
        from pyshaft.api.store import store_data, get_stored, clear_store
        clear_store()
        store_data("x", "old")
        store_data("x", "new")
        assert get_stored("x") == "new"


class TestApiResponse:
    """Verify ApiResponse wrapper without making real HTTP calls."""

    def _make_response(self, status_code=200, json_data=None, text=""):
        mock = MagicMock()
        mock.status_code = status_code
        mock.text = text or str(json_data)
        if json_data is not None:
            mock.json.return_value = json_data
        else:
            mock.json.side_effect = ValueError("No JSON")
        return mock

    def test_assert_status_pass(self):
        from pyshaft.api.response import ApiResponse
        resp = ApiResponse(self._make_response(200, {"ok": True}))
        result = resp.assert_status(200)
        assert result is resp  # chainable

    def test_assert_status_fail(self):
        from pyshaft.api.response import ApiResponse
        resp = ApiResponse(self._make_response(404, text="Not Found"))
        with pytest.raises(AssertionError, match="404"):
            resp.assert_status(200)

    def test_assert_json_pass(self):
        from pyshaft.api.response import ApiResponse
        resp = ApiResponse(self._make_response(200, {"user": {"name": "Alice"}}))
        result = resp.assert_json("user.name", "Alice")
        assert result is resp

    def test_assert_json_fail(self):
        from pyshaft.api.response import ApiResponse
        resp = ApiResponse(self._make_response(200, {"user": {"name": "Alice"}}))
        with pytest.raises(AssertionError, match="user.name"):
            resp.assert_json("user.name", "Bob")

    def test_assert_json_nested(self):
        from pyshaft.api.response import ApiResponse
        data = {"data": {"users": [{"id": 1}, {"id": 2}]}}
        resp = ApiResponse(self._make_response(200, data))
        resp.assert_json("data.users.0.id", 1)

    def test_extract_json(self):
        from pyshaft.api.response import ApiResponse
        from pyshaft.api.store import get_stored, clear_store
        clear_store()
        resp = ApiResponse(self._make_response(200, {"id": 99}))
        result = resp.extract_json("id", "my_id")
        assert result is resp  # chainable
        assert get_stored("my_id") == 99

    def test_chaining(self):
        from pyshaft.api.response import ApiResponse
        from pyshaft.api.store import clear_store
        clear_store()
        resp = ApiResponse(self._make_response(201, {"id": 42, "status": "created"}))
        (resp
            .assert_status(201)
            .assert_json("status", "created")
            .extract_json("id", "new_id"))

    def test_repr(self):
        from pyshaft.api.response import ApiResponse
        resp = ApiResponse(self._make_response(200))
        assert "200" in repr(resp)

    def test_no_json_body(self):
        from pyshaft.api.response import ApiResponse
        resp = ApiResponse(self._make_response(204, text="No Content"))
        assert resp.json_data is None
        with pytest.raises(ValueError, match="valid JSON"):
            resp.assert_json("foo", "bar")


# ============================================================================
# 7. Config Module Tests
# ============================================================================


class TestConfig:
    """Verify config loads and has correct defaults."""

    def test_default_config(self):
        from pyshaft.config import Config
        cfg = Config()
        assert cfg.browser.browser == "chrome"
        assert cfg.browser.headless is False
        assert cfg.waits.default_element_timeout == 10.0
        assert cfg.api.timeout == 30.0

    def test_api_config_defaults(self):
        from pyshaft.config import ApiConfig
        api_cfg = ApiConfig()
        assert api_cfg.base_url == ""
        assert api_cfg.verify_ssl is True

    def test_load_config_works(self):
        from pyshaft.config import load_config, reset_config
        reset_config()
        cfg = load_config()
        assert cfg is not None
        assert cfg.browser.browser == "chrome"
        reset_config()


# ============================================================================
# 8. Action Runner Module Smoke Test
# ============================================================================


class TestActionRunner:
    """Verify action runner has retry logic imports."""

    def test_stale_element_imported(self):
        """The retry loop depends on StaleElementReferenceException."""
        from pyshaft.core.action_runner import run_action
        # Just verify the import chain doesn't break
        assert callable(run_action)

    def test_run_driver_action_importable(self):
        from pyshaft.core.action_runner import run_driver_action
        assert callable(run_driver_action)


# ============================================================================
# 9. ApiEngine — new chainable API wrapper
# ============================================================================


class TestApiEngine:
    """Verify ApiEngine has short method names and backward compat."""

    def test_api_engine_importable(self):
        from pyshaft.api import api, ApiEngine
        assert isinstance(api, ApiEngine)

    def test_api_has_short_methods(self):
        from pyshaft.api import api
        assert callable(api.get)
        assert callable(api.post)
        assert callable(api.put)
        assert callable(api.patch)
        assert callable(api.delete)

    def test_api_has_long_methods(self):
        """Backward compat: send_get, send_post still work."""
        from pyshaft.api import api
        assert callable(api.send_get)
        assert callable(api.send_post)
        assert callable(api.send_put)
        assert callable(api.send_patch)
        assert callable(api.send_delete)

    def test_api_store_shortcuts(self):
        from pyshaft.api import api
        api.clear()
        api.store("key1", "value1")
        assert api.stored("key1") == "value1"
        api.clear()

    def test_api_stored_missing_key(self):
        from pyshaft.api import api
        api.clear()
        with pytest.raises(KeyError):
            api.stored("nonexistent")


# ============================================================================
# 10. Cross-Module Bridge (web.api)
# ============================================================================


class TestCrossModuleBridge:
    """Verify web.api returns the ApiEngine without circular import."""

    def test_web_api_returns_engine(self):
        from pyshaft.web import web
        from pyshaft.api import ApiEngine
        assert isinstance(web.api, ApiEngine)

    def test_web_api_has_get(self):
        from pyshaft.web import web
        assert callable(web.api.get)

    def test_web_api_has_post(self):
        from pyshaft.web import web
        assert callable(web.api.post)

    def test_web_api_same_singleton(self):
        """web.api and direct api import should be the same object."""
        from pyshaft.web import web
        from pyshaft.api import api
        assert web.api is api

    def test_no_circular_import(self):
        """Importing both modules in any order should work."""
        # Forward
        from pyshaft.web import web
        from pyshaft.api import api
        assert web.api is api

        # Reverse
        from pyshaft.api import api as api2
        from pyshaft.web import web as web2
        assert web2.api is api2


class TestFluentAssertions:
    """Verify web.assert_text and web.assert_contain_text behavior."""

    def test_assert_text_single_arg_returns_locator(self):
        from pyshaft.web import web
        from pyshaft.web.locators import Locator
        loc = web.assert_text("Success")
        assert isinstance(loc, Locator)
        assert "text=Success" in loc._get_final_selector()

    def test_assert_contain_text_single_arg_returns_locator(self):
        from pyshaft.web import web
        from pyshaft.web.locators import Locator
        loc = web.assert_contain_text("Logged In")
        assert isinstance(loc, Locator)
        assert "text=Logged In" in loc._get_final_selector()

    def test_assert_text_double_arg_returns_locator(self):
        from pyshaft.web import web, WebEngine
        from pyshaft.web.locators import Locator
        res = web.assert_text("Expected", "#id")
        assert isinstance(res, Locator)

    def test_assert_contain_text_double_arg_returns_locator(self):
        from pyshaft.web import web, WebEngine
        from pyshaft.web.locators import Locator
        res = web.assert_contain_text("Expected", "#id")
        assert isinstance(res, Locator)

    def test_assert_text_chaining(self):
        from pyshaft.web import web
        from pyshaft.web.locators import Locator
        from unittest.mock import patch
        # web.assert_text() returns Locator
        loc = web.assert_text("Success")
        
        # Patch assert_visible to avoid real driver wait/timeout
        with patch("pyshaft.web.assertions.assert_visible") as mock_visible:
            # Locator.should_be_visible() returns Locator (self)
            res = loc.should_be_visible()
            mock_visible.assert_called_once()
            assert res is loc
            assert isinstance(res, Locator)


class TestLocatorChaining:
    """Verify deep chaining of actions on Locator objects."""

    def test_scroll_click_chain(self):
        from pyshaft.web.locators import Locator
        # Test that locator builds correct selector
        loc = Locator(value="#btn")
        assert loc._build_selector() == "#btn"
        # Test chaining - scroll and click return locator
        result = loc.scroll()
        assert isinstance(result, Locator)

    def test_hover_type_chain(self):
        from pyshaft.web.locators import Locator
        from unittest.mock import patch
        
        loc = Locator(value="#input")
        with patch("pyshaft.web.interactions.hover") as mock_hover:
            with patch("pyshaft.web.inputs.type_text") as mock_type:
                res = loc.hover().type_text("hello")
                
                mock_hover.assert_called_once_with("#input")
                mock_type.assert_called_once_with("#input", "hello", clear_first=True)
                assert res is loc


class TestApiPositionalArgs:
    """Verify api.post and friends handle positional body correctly."""

    def test_api_post_positional_json(self):
        from pyshaft.api import api
        from unittest.mock import patch
        # Patch where it's used (imported in pyshaft.api)
        with patch("pyshaft.api.send_post") as mock_send:
            api.post("https://example.com/users", {"id": 1})
            # Should have mapped {"id": 1} to the 'body' argument
            mock_send.assert_called_once_with("https://example.com/users", {"id": 1})

    def test_api_expect_bridge(self):
        from pyshaft.api import api
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        res = api.expect(mock_resp)
        assert res is mock_resp


class TestNewWebAssertions:
    """Verify should_be_enabled and should_be_disabled calls."""

    def test_should_be_enabled_exists(self):
        from pyshaft.web.locators import Locator
        loc = Locator("#id")
        assert hasattr(loc, "should_be_enabled")

    def test_should_be_disabled_exists(self):
        from pyshaft.web.locators import Locator
        loc = Locator("#id")
        assert hasattr(loc, "should_be_disabled")


