"""PyShaft web module — Unified syntax API.

New format: w.click(type, value).filter(k1=v1).nth(N)
Examples:
    w.click(role, button).nth(1)
    w.type("hello", role, textbox).filter(placeholder="email")
    w.assert_visible(role, modal).nth(1)
"""

from __future__ import annotations

import logging
from typing import Any

# Import sub-modules
from pyshaft.web import (
    alerts,
    assertions,
    collections,
    data_extract,
    inputs,
    interactions,
    keyboard,
    locators,
    navigation,
    screenshot,
    storage,
    tables,
    waits,
)

logger = logging.getLogger("pyshaft.web")


class WebEngine:
    """Unified chainable engine for PyShaft web automation."""

    # Retry configuration
    _retry_count = 0
    _retry_backoff = 1.5

    # Current step name for logging
    _current_step: str | None = None

    # Implicit Execution: track last builds locator with an action
    _pending_locator: locators.Locator | None = None

    @property
    def api(self):
        """Access API engine for hybrid tests (lazy import to avoid circular deps)."""
        from pyshaft.api import api
        return api

    # -------------------------------------------------------------------------
    # Configuration Methods (return self for chaining)
    # -------------------------------------------------------------------------

    def retry(self, count: int = 3, backoff: float = 1.5) -> "WebEngine":
        """Set retry configuration for the entire chain.
        
        Args:
            count: Number of retry attempts on failure
            backoff: Backoff multiplier between retries
            
        Example:
            w.retry(3).click(role, button)
        """
        self._retry_count = count
        self._retry_backoff = backoff
        return self

    def step(self, name: str) -> "WebEngine":
        """Mark a named test step for logging.
        
        Args:
            name: Step name to log
            
        Example:
            w.step("Login").click(role, button)
        """
        self._current_step = name
        logger.info(f"📍 Step: {name}")
        return self

    def debug(self) -> "WebEngine":
        """Enable debug mode - highlights elements and logs info."""
        # This is handled at Locator level
        logger.info("🔍 Debug mode enabled")
        return self

    def locator(self, locator_type: str = "any", value: str = "") -> "locators.Locator":
        """Create a locator for chaining (alias for wait)."""
        return self.wait(locator_type, value)

    def wait(self, locator_type: str = "any", value: str = "") -> "locators.Locator":
        """Create a wait locator for chainable waits.
        
        Args:
            locator_type: Type (role, text, id, etc.)
            value: Value to match
            
        Example:
            w.wait(role, spinner).visible()
            w.wait(role, modal).hidden()
        """
        loc = locators.Locator(locator_type=locator_type, value=value)
        loc._web_instance = self
        return loc

    def shadow(self, selector: str) -> "locators.Locator":
        """Find element within shadow DOM."""
        loc = locators.Locator(value=f"shadow > {selector}")
        loc._web_instance = self
        return loc

    def reset(self) -> "WebEngine":
        """Reset configuration (retry, step, etc.)."""
        self.flush()  # Ensure all pending actions are done
        self._retry_count = 0
        self._retry_backoff = 1.5
        self._current_step = None
        self._pending_locator = None
        return self

    def flush(self) -> "WebEngine":
        """Execute any pending lazy action."""
        if self._pending_locator:
            loc = self._pending_locator
            self._pending_locator = None  # Clear before execution to avoid recursion
            loc.execute()
        return self

    def _register_action(self, loc: locators.Locator) -> "locators.Locator":
        """Register a locator as pending, flushing any previous one."""
        self.flush()
        self._pending_locator = loc
        return loc

    def _build_loc(self, locator_type, value, third_arg=None, **filters) -> tuple["locators.Locator", Any]:
        """Smart locator builder that handles (selector), (type, value), or (type, modifier, value)."""
        # Known locator types and modifiers
        TYPES = {"role", "text", "label", "placeholder", "testid", "id", "class", "css", "xpath", "tag", "attr", "any"}
        MODIFIERS = {"exact", "contain", "contains", "starts"}
        
        # Sanitize common built-ins like `id` and `type` passed accidentally
        if callable(locator_type):
            locator_type = getattr(locator_type, "__name__", str(locator_type))
            
        real_type = locator_type
        real_modifier = None
        real_value = value
        new_third_arg = third_arg
        
        logger.debug(f"BuildLoc: type={locator_type!r}, value={value!r}, third={third_arg!r}")
        
        # Detected 3-arg pattern: w.method(type, modifier, value)
        if value in MODIFIERS and isinstance(third_arg, str):
            real_modifier = value
            real_value = third_arg
            new_third_arg = None  # Consumed by locator
            logger.debug(f"BuildLoc: detected 3-arg pattern -> mod={real_modifier}, val={real_value}")
        elif not value and locator_type and locator_type not in TYPES:
            # (selector) pattern
            real_type = None
            real_value = locator_type
            logger.debug(f"BuildLoc: detected raw selector pattern -> val={real_value}")
            
        loc = locators.Locator(locator_type=real_type, value=real_value, modifier=real_modifier, **filters)
        loc._web_instance = self
        return loc, new_third_arg

    # -------------------------------------------------------------------------
    # Navigation Methods
    # -------------------------------------------------------------------------

    def open_url(self, url: str) -> "WebEngine":
        """Navigate to a URL."""
        self.flush()
        self._execute_with_retry(lambda: navigation.open_url(url))
        return self

    def go_back(self) -> "WebEngine":
        """Navigate back in browser history."""
        self._execute_with_retry(lambda: navigation.go_back())
        return self

    def go_forward(self) -> "WebEngine":
        """Navigate forward in browser history."""
        self._execute_with_retry(lambda: navigation.go_forward())
        return self

    def refresh(self) -> "WebEngine":
        """Refresh the current page."""
        self.flush()
        self._execute_with_retry(lambda: navigation.refresh())
        return self

    def scroll(self, x: int = 0, y: int = 0) -> "WebEngine":
        """Scroll the window by pixel offset."""
        navigation.scroll(x, y)
        return self

    def scroll_to_bottom(self) -> "WebEngine":
        """Scroll to the bottom of the page."""
        navigation.scroll_to_bottom()
        return self

    def scroll_to_top(self) -> "WebEngine":
        """Scroll to the top of the page."""
        navigation.scroll_to_top()
        return self

    def ad_block(self) -> "WebEngine":
        """Block common ads on the current page."""
        js_helpers.ad_block()
        return self

    def switch_to_new_window(self, switch_to: bool = True) -> "WebEngine":
        """Open a new browser window/tab."""
        navigation.open_new_window(switch_to=switch_to)
        return self

    def switch_to_window(self, handle_or_index: str | int) -> "WebEngine":
        """Switch focus to a different browser window/tab."""
        navigation.switch_to_window(handle_or_index)
        return self

    def switch_to_newest_window(self) -> "WebEngine":
        """Switch focus to the most recently opened window/tab."""
        navigation.switch_to_newest_window()
        return self

    def switch_to_parent_frame(self) -> "WebEngine":
        """Switch focus back to the parent frame."""
        navigation.switch_to_parent_frame()
        return self

    def switch_to_default_content(self) -> "WebEngine":
        """Switch focus back to the main document/top-level frame."""
        navigation.switch_to_default_content()
        return self

    # -------------------------------------------------------------------------
    # Storage & Cookie Methods
    # -------------------------------------------------------------------------

    def get_cookies(self) -> list[dict]:
        """Get all browser cookies."""
        return storage.get_cookies()

    def add_cookie(self, cookie_dict: dict) -> "WebEngine":
        """Add a cookie to the current session."""
        storage.add_cookie(cookie_dict)
        return self

    def delete_cookie(self, name: str) -> "WebEngine":
        """Delete a specific cookie by name."""
        storage.delete_cookie(name)
        return self

    def clear_cookies(self) -> "WebEngine":
        """Delete all cookies from the current session."""
        storage.clear_cookies()
        return self

    def save_cookies(self, file_path: str) -> "WebEngine":
        """Save current session cookies to a JSON file."""
        storage.save_cookies(file_path)
        return self

    def load_cookies(self, file_path: str) -> "WebEngine":
        """Load cookies from a JSON file and add them to the session."""
        storage.load_cookies(file_path)
        return self

    def get_url(self) -> str:
        """Get the current page URL."""
        return navigation.get_url()

    def get_title(self) -> str:
        """Get the current page title."""
        return navigation.get_title()

    # -------------------------------------------------------------------------
    # Interaction Methods (New Unified API)
    # -------------------------------------------------------------------------

    def click(
        self,
        locator_type: str | None = None,
        value: str = "",
        amount: int = 1,
        **filters: Any,
    ) -> "locators.Locator":
        """Click an element.
        
        Example:
            w.click(role, button)
            w.click(role, button).nth(1)
            w.click(role, button).filter(class="primary")
        
        Args:
            locator_type: Type (role, text, id, class, etc.)
            value: Value to match
            amount: Number of clicks
            **filters: Additional filters
            
        Returns:
            Locator for chaining (.nth(), .filter(), etc.)
        """
        loc, amount = self._build_loc(locator_type, value, third_arg=amount, **filters)
        loc._action = "click"
        loc._action_args = {"amount": amount or 1, "force": filters.get("force", False)}
        res = self._register_action(loc)
        self.flush()
        return res

    def force_click(self, locator_type: str | None = None, value: str = "", **filters: Any) -> "locators.Locator":
        """Force-click an element via JavaScript bypass."""
        return self.click(locator_type, value, force=True, **filters)

    def click_all(self, locator_type: str | None = None, value: str = "", **filters: Any) -> "WebEngine":
        """Click all matching elements."""
        self.flush()
        loc, _ = self._build_loc(locator_type, value, **filters)
        self._execute_with_retry(lambda: interactions.click_all(loc._build_selector()))
        return self

    def double_click(self, locator_type: str | None = None, value: str = "", **filters: Any) -> "locators.Locator":
        """Double-click an element."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        self._execute_with_retry(lambda: interactions.double_click(loc._build_selector()))
        return loc

    def right_click(self, locator_type: str | None = None, value: str = "", **filters: Any) -> "locators.Locator":
        """Right-click an element."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        self._execute_with_retry(lambda: interactions.right_click(loc._build_selector()))
        return loc

    def hover(self, locator_type: str | None = None, value: str = "", **filters: Any) -> "locators.Locator":
        """Hover over an element (lazy)."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "hover"
        res = self._register_action(loc)
        self.flush()
        return res

    def drag(
        self,
        source_type: str | None = None,
        source_value: str = "",
        target_type: str | None = None,
        target_value: str = "",
        **filters: Any,
    ) -> "WebEngine":
        """Drag source element to target element."""
        self.flush()
        source_loc = locators.Locator(locator_type=source_type, value=source_value)
        target_loc = locators.Locator(locator_type=target_type, value=target_value)
        self._execute_with_retry(
            lambda: interactions.drag_to(source_loc._build_selector(), target_loc._build_selector())
        )
        return self

    def drag_by_offset(
        self,
        x: int,
        y: int,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "locators.Locator":
        """Drag an element by a specific offset."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "drag_by_offset"
        loc._action_args = {"x": x, "y": y}
        res = self._register_action(loc)
        self.flush()
        return res

    def hover_and_click(
        self,
        hover_locator_type: str | None = None,
        hover_value: str = "",
        click_locator_type: str | None = None,
        click_value: str = "",
        **filters: Any,
    ) -> "WebEngine":
        """Hover over one element and then click another (immediate)."""
        self.flush()
        # Handle hover locator
        h_loc, _ = self._build_loc(hover_locator_type, hover_value, **filters)
        # Handle click locator
        c_loc, _ = self._build_loc(click_locator_type, click_value)
        self._execute_with_retry(
            lambda: interactions.hover_and_click(h_loc._build_selector(), c_loc._build_selector())
        )
        return self

    # -------------------------------------------------------------------------
    # Input Methods (New Unified API)
    # -------------------------------------------------------------------------

    def type(
        self,
        text: str,
        locator_type: str | None = None,
        value: str = "",
        clear_first: bool = True,
        **filters: Any,
    ) -> "locators.Locator":
        """Type text into an element (lazy - returns Locator for chaining).
        
        Example:
            w.type("hello", role, textbox)
            w.type("hello", role, textbox).filter(placeholder="email")
        """
        # Pattern: type(text, locator_type, value)
        loc, value = self._build_loc(locator_type, value, third_arg=None, **filters)
        loc._action = "type"
        loc._action_args = {"text": text, "clear_first": clear_first, "force": filters.get("force", False)}
        res = self._register_action(loc)
        self.flush()
        return res

    def clear(self, locator_type: str | None = None, value: str = "", **filters: Any) -> "locators.Locator":
        """Clear text from an element (builds locator without executing)."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "clear"
        res = self._register_action(loc)
        self.flush()
        return res

    def delete(self, locator_type: str | None = None, value: str = "", **filters: Any) -> "locators.Locator":
        """Delete text from element (alias for clear)."""
        return self.clear(locator_type, value, **filters)

    def enter_mfa_code(
        self,
        totp_key: str,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "locators.Locator":
        """Generate a TOTP code and type it into the element."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "enter_mfa_code"
        loc._action_args = {"totp_key": totp_key}
        res = self._register_action(loc)
        self.flush()
        return res

    def select(
        self,
        option: str | int,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "locators.Locator":
        """Select option from dropdown (builds locator without executing)."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "select"
        loc._action_args = {"value": option}
        res = self._register_action(loc)
        self.flush()
        return res

    def select_options(
        self,
        options: list[str | int],
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "locators.Locator":
        """Select multiple options from dropdown."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "select_options"
        loc._action_args = {"values": options}
        res = self._register_action(loc)
        self.flush()
        return res

    def deselect_option(
        self,
        option: str | int,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "locators.Locator":
        """Deselect an option from dropdown."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "deselect_option"
        loc._action_args = {"value": option}
        res = self._register_action(loc)
        self.flush()
        return res

    def deselect_all(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "locators.Locator":
        """Deselect all options from dropdown."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "deselect_all_options"
        res = self._register_action(loc)
        self.flush()
        return res

    def select_dynamic(
        self,
        option: str,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "locators.Locator":
        """Select an option from a custom UI dropdown (clicks container, then clicks option)."""
        # We model this by returning a locator for the dropdown, but when executed,
        # it will perform the dual-action.
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "select_dynamic"
        loc._action_args = {"option": option}
        res = self._register_action(loc)
        self.flush()
        return res

    def upload(
        self,
        file_path: str,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "locators.Locator":
        """Upload a file to an element (equivalent to choose_file)."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "upload_file"
        loc._action_args = {"file_path": file_path}
        res = self._register_action(loc)
        self.flush()
        return res

    def upload_files(
        self,
        file_paths: list[str],
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "locators.Locator":
        """Upload multiple files to an element."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "upload_files"
        loc._action_args = {"file_paths": file_paths}
        res = self._register_action(loc)
        self.flush()
        return res

    def download(
        self,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> str:
        """Click element and wait for download to complete. Returns path to file.
        
        This executes immediately and returns the path string, not a locator.
        """
        self.flush()
        loc, _ = self._build_loc(locator_type, value, **filters)
        return self._execute_with_retry(
            lambda: interactions.download_file(loc._build_selector(), timeout=timeout)
        )

    def remove_element(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "locators.Locator":
        """Remove an element from the DOM via JavaScript."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "remove_element"
        res = self._register_action(loc)
        self.flush()
        return res

    def remove_elements(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "WebEngine":
        """Remove all matching elements from the DOM via JavaScript."""
        self.flush()
        loc, _ = self._build_loc(locator_type, value, **filters)
        self._execute_with_retry(lambda: js_helpers.remove_elements(loc._build_selector()))
        return self

    def pick_date(
        self,
        date: str,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "locators.Locator":
        """Interact with a date picker. Equivalent to a clear and type."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "pick_date"
        loc._action_args = {"date": date}
        res = self._register_action(loc)
        self.flush()
        return res

    def check(self, locator_type: str | None = None, value: str = "", **filters: Any) -> "locators.Locator":
        """Check a checkbox/radio (builds locator without executing)."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "check"
        res = self._register_action(loc)
        self.flush()
        return res

    def uncheck(self, locator_type: str | None = None, value: str = "", **filters: Any) -> "locators.Locator":
        """Uncheck a checkbox (builds locator without executing)."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "uncheck"
        res = self._register_action(loc)
        self.flush()
        return res

    def submit(self, locator_type: str | None = None, value: str = "", **filters: Any) -> "locators.Locator":
        """Submit a form by pressing Enter (builds locator without executing)."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "press_key"
        loc._action_args = {"key": "ENTER"}
        res = self._register_action(loc)
        self.flush()
        return res

    # -------------------------------------------------------------------------
    # Assertion Methods (New Unified API)
    # -------------------------------------------------------------------------

    def assert_text(
        self,
        expected: str,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Assert element text contains expected value (lazy - returns Locator for chaining)."""
        # If locator not specified, search entire page for text
        if not locator_type and not value:
            loc, _ = self._build_loc("text", expected, **filters)
        else:
            loc, _ = self._build_loc(locator_type, value, **filters)
            
        loc._action = "assert_text"
        loc._action_args = {"expected": expected, "timeout": timeout}
        res = self._register_action(loc)
        self.flush()
        return res

    def assert_contain_title(self, expected: str, timeout: float | None = None) -> "WebEngine":
        """Assert page title contains expected substring."""
        self.flush()
        self._execute_with_retry(lambda: assertions.assert_contain_title(expected, timeout=timeout))
        return self

    def assert_contain_url(self, expected: str, timeout: float | None = None) -> "WebEngine":
        """Assert current URL contains expected substring."""
        self.flush()
        self._execute_with_retry(lambda: assertions.assert_contain_url(expected, timeout=timeout))
        return self

    def assert_contain_text(
        self,
        expected: str,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Alias for assert_text (which is already a partial match)."""
        return self.assert_text(expected, locator_type, value, timeout, **filters)

    def assert_contain_attribute(
        self,
        attr: str,
        expected: str,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Assert element attribute contains expected substring."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "assert_contain_attribute"
        loc._action_args = {"attr": attr, "expected": expected, "timeout": timeout}
        res = self._register_action(loc)
        self.flush()
        return res

    def assert_visible(
        self,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Assert element is visible (lazy - returns Locator for chaining)."""
        loc, _ = self._build_loc(locator_type, value, third_arg=None, **filters)
        loc._action = "assert_visible"
        loc._action_args = {"timeout": timeout}
        res = self._register_action(loc)
        self.flush()
        return res

    def assert_hidden(
        self,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Assert element is hidden (builds locator without executing)."""
        loc, _ = self._build_loc(locator_type, value, third_arg=None, **filters)
        loc._action = "assert_hidden"
        loc._action_args = {"timeout": timeout}
        res = self._register_action(loc)
        self.flush()
        return res

    def wait_until_disappears(
        self,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Wait until an element (like an ajax-loader) disappears."""
        return self.assert_hidden(locator_type, value, timeout, **filters)

    def assert_title(self, expected: str, timeout: float | None = None) -> "WebEngine":
        """Assert page title (executes immediately - no locator)."""
        self.flush()
        self._execute_with_retry(lambda: assertions.assert_title(expected, timeout=timeout))
        return self

    def assert_url(self, expected: str, timeout: float | None = None) -> "WebEngine":
        """Assert current URL."""
        self.flush()
        self._execute_with_retry(lambda: assertions.assert_url(expected, timeout=timeout))
        return self

    def assert_enabled(
        self,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Assert element is enabled."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "assert_enabled"
        loc._action_args = {"timeout": timeout}
        res = self._register_action(loc)
        self.flush()
        return res

    def assert_disabled(
        self,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Assert element is disabled."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "assert_disabled"
        loc._action_args = {"timeout": timeout}
        res = self._register_action(loc)
        self.flush()
        return res

    def assert_checked(
        self,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Assert checkbox/radio is checked."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "assert_checked"
        loc._action_args = {"timeout": timeout}
        res = self._register_action(loc)
        self.flush()
        return res

    # -------------------------------------------------------------------------
    # Data Extraction Methods
    # -------------------------------------------------------------------------

    def get_text(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> str:
        """Get the visible text of an element.

        Example:
            result = w.get_text(role, heading)
            price = int(w.get_text(id_, "price"))
        """
        self.flush()
        loc, _ = self._build_loc(locator_type, value, **filters)
        return self._execute_with_retry(lambda: inputs.get_text(loc._build_selector()))

    def get_value(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> str:
        """Get the 'value' attribute of an element (for inputs, textareas)."""
        self.flush()
        loc, _ = self._build_loc(locator_type, value, **filters)
        return self._execute_with_retry(lambda: inputs.get_value(loc._build_selector()))

    def get_selected_option(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> str:
        """Get the visible text of the selected option in a <select>."""
        self.flush()
        loc, _ = self._build_loc(locator_type, value, **filters)
        return self._execute_with_retry(lambda: data_extract.get_selected_option(loc._build_selector()))

    def get_selected_options(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> list[str]:
        """Get the visible text of all selected options in a <select multiple>."""
        self.flush()
        loc, _ = self._build_loc(locator_type, value, **filters)
        return self._execute_with_retry(lambda: data_extract.get_selected_options(loc._build_selector()))

    def assert_selected_option(
        self,
        expected: str,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Assert that a <select>'s selected option text matches expected."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "assert_selected_option"
        loc._action_args = {"expected": expected, "timeout": timeout}
        res = self._register_action(loc)
        self.flush()
        return res

    def assert_contain_selected(
        self,
        expected: str,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Assert that a <select>'s selected option text contains expected."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "assert_contain_selected"
        loc._action_args = {"expected": expected, "timeout": timeout}
        res = self._register_action(loc)
        self.flush()
        return res

    def assert_data_type(
        self,
        expected_type: str,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Assert that an element's text matches expected data type.

        Supported types: int, float, string, bool, email, url, date, phone, uuid, empty, not_empty.
        """
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "assert_data_type"
        loc._action_args = {"expected_type": expected_type, "timeout": timeout}
        res = self._register_action(loc)
        self.flush()
        return res

    def assert_value(
        self,
        expected: str,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Assert that an element's value attribute matches expected."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "assert_value"
        loc._action_args = {"expected": expected, "timeout": timeout}
        res = self._register_action(loc)
        self.flush()
        return res

    # -------------------------------------------------------------------------
    # Unified Aliases
    # -------------------------------------------------------------------------
    type_text = type
    clear_text = clear
    select_option = select
    check_checkbox = check
    uncheck_checkbox = uncheck

    # -------------------------------------------------------------------------
    # Alert Methods
    # -------------------------------------------------------------------------

    def accept_alert(self) -> "WebEngine":
        """Accept an alert dialog."""
        alerts.accept_alert()
        return self

    def dismiss_alert(self) -> "WebEngine":
        """Dismiss an alert dialog."""
        alerts.dismiss_alert()
        return self

    def get_alert_text(self) -> str:
        """Get the text of an active alert dialog."""
        self.flush()
        return alerts.get_alert_text()

    # -------------------------------------------------------------------------
    # Frame Methods
    # -------------------------------------------------------------------------

    def switch_to_iframe(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "locators.Locator":
        """Switch context to an iframe."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "switch_to_iframe"
        res = self._register_action(loc)
        self.flush()
        return res

    def switch_to_default(self) -> "WebEngine":
        """Switch context back to the default content from an iframe."""
        self.flush()
        # Ensure we execute immediately
        self._execute_with_retry(lambda: self.api.switch_to_default_content())
        return self

    # -------------------------------------------------------------------------
    # Screenshot Method
    # -------------------------------------------------------------------------

    def take_screenshot(self, name: str | None = None) -> "WebEngine":
        """Take a screenshot."""
        screenshot.take_screenshot(name)
        return self

    def assert_snapshot(
        self,
        name: str,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Assert visual layout of an element matches a baseline snapshot."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "assert_snapshot"
        loc._action_args = {"name": name, "timeout": timeout}
        res = self._register_action(loc)
        self.flush()
        return res

    def assert_aria_snapshot(
        self,
        expected_yaml: str,
        locator_type: str | None = None,
        value: str = "",
        timeout: float | None = None,
        **filters: Any,
    ) -> "locators.Locator":
        """Assert semantic structure matches expected ARIA YAML."""
        loc, _ = self._build_loc(locator_type, value, **filters)
        loc._action = "assert_aria_snapshot"
        loc._action_args = {"expected_yaml": expected_yaml, "timeout": timeout}
        res = self._register_action(loc)
        self.flush()
        return res


    # -------------------------------------------------------------------------
    # Page Object Helper
    # -------------------------------------------------------------------------

    def page(self, mapping: dict) -> "PageObject":
        """Create a page object from a mapping.
        
        Args:
            mapping: Dict of {name: locator} pairs
            
        Example:
            login_page = w.page({
                "username": w.input(role, textbox),
                "password": w.input(role, password),
                "submit": w.click(role, button),
            })
            login_page.username.type("admin")
            login_page.submit.click()
        """
        return PageObject(mapping, self)

    # -------------------------------------------------------------------------
    # Internal: Execute with retry
    # -------------------------------------------------------------------------

    def _execute_with_retry(self, func):
        """Execute a function with retry logic."""
        import time
        import threading
        
        attempts = self._retry_count + 1
        last_error = None
        
        for attempt in range(attempts):
            try:
                return func()
            except Exception as e:
                last_error = e
                if attempt < attempts - 1:
                    wait_time = self._retry_backoff ** attempt
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise last_error


class PageObject:
    """Page object wrapper for reusable components."""

    def __init__(self, mapping: dict, engine: WebEngine):
        self._mapping = mapping
        self._engine = engine
        for name, locator in mapping.items():
            # Create property for each page element
            setattr(self, name, locator)

    def __repr__(self):
        return f"<PageObject {list(self._mapping.keys())}>"


class ActionProxy:
    """A callable proxy that adds chainable property-like methods for locator interactions.
    
    This allows syntax like w.click.contain(text="Submit") as well as w.click(role, button).
    """

    def __init__(self, func):
        self._func = func

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def contain(self, **kwargs):
        """Set modifier to contain."""
        res = self()
        if hasattr(res, 'contain'):
            return res.contain(**kwargs)
        return res

    def contains(self, **kwargs):
        """Alias for contain."""
        return self.contain(**kwargs)

    def exact(self, **kwargs):
        """Set modifier to exact."""
        res = self()
        if hasattr(res, 'exact'):
            return res.exact(**kwargs)
        return res

    def starts(self, **kwargs):
        """Set modifier to starts."""
        res = self()
        if hasattr(res, 'starts'):
            return res.starts(**kwargs)
        return res


# Create singleton instance
web = WebEngine()

# Patch web instance methods with ActionProxy to allow w.click.contain(...)
# ONLY wrap methods that return a Locator
for action_name in [
    "click", "double_click", "right_click", "hover",
    "clear", "delete", "select", "check", "uncheck", "submit",
    "enter_mfa_code", "remove_element",
    "assert_visible", "assert_hidden", "assert_enabled", "assert_disabled", "assert_checked",
    "assert_text", "assert_contain_text", "assert_contain_attribute",
    "assert_selected_option", "assert_contain_selected", "assert_data_type", "assert_value",
    "assert_snapshot", "assert_aria_snapshot"
]:
    setattr(web, action_name, ActionProxy(getattr(web, action_name)))

# Expose top-level functions
open_url = web.open_url
click = web.click
type = web.type
type_text = web.type  # Unified alias
check = web.check
check_checkbox = web.check  # Unified alias
uncheck = web.uncheck
uncheck_checkbox = web.uncheck  # Unified alias
hover = web.hover
scroll = web.scroll
drag = web.drag
select = web.select
select_option = web.select  # Unified alias
select_options = web.select_options
deselect_option = web.deselect_option
deselect_all = web.deselect_all
submit = web.submit
clear = web.clear
clear_text = web.clear  # Unified alias
assert_text = web.assert_text
assert_contain_text = web.assert_contain_text
assert_contain_title = web.assert_contain_title
assert_contain_url = web.assert_contain_url
assert_contain_attribute = web.assert_contain_attribute
assert_visible = web.assert_visible
assert_hidden = web.assert_hidden
assert_enabled = web.assert_enabled
assert_disabled = web.assert_disabled
assert_checked = web.assert_checked
assert_title = web.assert_title
assert_url = web.assert_url
assert_selected_option = web.assert_selected_option
assert_contain_selected = web.assert_contain_selected
assert_data_type = web.assert_data_type
assert_value = web.assert_value
get_text = web.get_text
get_value = web.get_value
get_selected_option = web.get_selected_option
get_selected_options = web.get_selected_options
download = web.download
upload_files = web.upload_files
enter_mfa_code = web.enter_mfa_code
hover_and_click = web.hover_and_click
drag_by_offset = web.drag_by_offset
switch_to_new_window = web.switch_to_new_window
switch_to_newest_window = web.switch_to_newest_window
switch_to_parent_frame = web.switch_to_parent_frame
switch_to_default_content = web.switch_to_default_content
scroll_to_top = web.scroll_to_top
remove_elements = web.remove_elements
ad_block = web.ad_block
get_cookies = storage.get_cookies
add_cookie = storage.add_cookie
delete_cookie = storage.delete_cookie
clear_cookies = storage.clear_cookies
save_cookies = storage.save_cookies
load_cookies = storage.load_cookies

# Legacy aliases (deprecated)
get_by_role = web.click  # Not exactly, but provides quick access
get_by_text = web.click
get_by_label = web.click
locator = web.wait  # Creates a locator for chaining

# Debug/retry/step
retry = web.retry
step = web.step
debug = web.debug
shadow = web.shadow

__all__ = [
    "web",
    # Navigation
    "open_url",
    "go_back",
    "go_forward",
    "refresh",
    "scroll",
    "scroll_to_bottom",
    "scroll_to_top",
    "switch_to_new_window",
    "switch_to_newest_window",
    "switch_to_parent_frame",
    "switch_to_default_content",
    "get_url",
    "get_title",
    # Interactions
    "click",
    "hover",
    "hover_and_click",
    "drag",
    "drag_by_offset",
    # Inputs
    "type",
    "type_text",  # alias
    "clear",
    "select",
    "select_options",
    "deselect_option",
    "deselect_all",
    "check",
    "uncheck",
    "submit",
    "upload",
    "upload_files",
    "download",
    "enter_mfa_code",
    "remove_element",
    "remove_elements",
    "ad_block",
    # Assertions
    "assert_text",
    "assert_visible",
    "assert_hidden",
    "assert_contain_title",
    "assert_contain_url",
    "assert_contain_text",
    "assert_contain_attribute",
    "assert_enabled",
    "assert_disabled",
    "assert_checked",
    "assert_title",
    "assert_url",
    "assert_contain_title",
    "assert_contain_url",
    "assert_contain_text",
    "assert_contain_attribute",
    # Configuration
    "retry",
    "step",
    "debug",
    # Page object
    "locator",
    "wait",
    "page",
    "shadow",
    # Legacy (deprecated)
    "get_by_role",
    "get_by_text",
    "get_by_label",
    # Data extraction
    "get_text",
    "get_value",
    "get_selected_option",
    "get_selected_options",
    "get_cookies",
    "add_cookie",
    "delete_cookie",
    "clear_cookies",
    "save_cookies",
    "load_cookies",
    # Locator type constants
    "role", "text", "label", "placeholder", "testid", "id_", "cls", "css_", "xpath", "tag", "attr", "any_",
    # Text modifiers
    "exact", "contain", "starts", "contains",
    # HTML element types
    "button", "textbox", "input_", "checkbox", "radio", "link", "menu", "menuitem",
    "dialog", "modal", "form", "heading", "alert", "spinner", "image", "listbox", "option", "combobox",
    # Type aliases
    "password", "email", "submit",
]


# -------------------------------------------------------------------------
# Locator Type Constants
# -------------------------------------------------------------------------
# Use these for readable syntax: w.click(role, button)
# Example: w.click(role, button).nth(1)

# Core types
role = "role"
text = "text"
label = "label"
placeholder = "placeholder"
testid = "testid"
id_ = "id"  # Use id_ to avoid Python keyword
cls = "class"  # Use cls to avoid Python keyword
css_ = "css"  # Use css_ to avoid keyword
xpath = "xpath"
tag = "tag"
attr = "attr"
any_ = "any"

# Text modifiers (use with text type)
exact = "exact"
contain = "contain"
starts = "starts"
contains = "contains"

# HTML element types (common roles)
button = "button"
textbox = "textbox"
input_ = "input"  # Use input_ to avoid keyword
checkbox = "checkbox"
radio = "radio"
link = "link"
menu = "menu"
menuitem = "menuitem"
dialog = "dialog"
modal = "modal"
form = "form"
heading = "heading"
alert = "alert"
spinner = "spinner"
image = "img"
listbox = "listbox"
option = "option"
combobox = "combobox"

# Aliases for common types
password = "password"
email = "email"
submit = "submit"