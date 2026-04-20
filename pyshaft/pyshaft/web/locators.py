"""PyShaft fluent locators — Unified syntax for element interaction.

New format: action(type, value).filter(k1=v1).inside(t,v).nth(N:M)
Examples:
    click(role,button).nth(1)
    click(role,button).filter(class="primary").nth(1:5)
    type("hello", role,textbox).filter(placeholder="email")
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("pyshaft.web.locators")


class Locator:
    """Unified locator for fluent interactions with new syntax."""

    def __init__(
        self,
        locator_type: str | None = None,
        value: str = "",
        modifier: str | None = None,
        **filters: Any,
    ):
        if callable(locator_type):
            locator_type = getattr(locator_type, "__name__", str(locator_type))
            
        self._locator_type = locator_type  # role, text, id, class, etc.
        self._value = value                 # the value to search for
        self._modifier = modifier           # exact, contain, starts, contains
        
        # Normalize class_ to class
        if "class_" in filters:
            filters["class"] = filters.pop("class_")
            
        self._filters = filters             # additional filters: tag="div", class="btn"
        self._inside = None                  # inside locator: (type, value)
        self._index: int | tuple | None = None  # single index or range
        self._debug = False                  # debug mode flag
        self._web_instance = None            # reference to WebEngine for chaining
        self._action: str | None = None       # pending action to execute
        self._action_args: dict = {}         # action arguments
        # Retry configuration for this locator
        self._retry_config = None            # RetryConfig instance or None

    def _build_selector(self) -> str:
        """Build the selector string for DualLocator."""
        # Build base selector from type and value
        parts = []
        
        if self._locator_type and self._value:
            if self._modifier:
                parts.append(f"{self._locator_type},{self._modifier}={self._value}")
            else:
                parts.append(f"{self._locator_type}={self._value}")
        elif self._value:
            parts.append(self._value)
        
        # Add filters
        for key, val in self._filters.items():
            if val:
                parts.append(f'{key}="{val}"')
        
        selector = " ".join(parts) if parts else "*"
        
        # Add inside clause
        if self._inside:
            inside_type, inside_value = self._inside
            selector = f"{selector} inside={inside_type}={inside_value}"
        
        # Add index/range
        if self._index is not None:
            if isinstance(self._index, tuple):
                # Range: (start, end) -> "0:5" means 0,1,2,3,4
                start, end = self._index
                selector = f"({selector}) >> index={start}:{end}"
            else:
                # Single index (convert from 1-based to 0-based)
                idx = self._index - 1 if self._index > 0 else self._index
                selector = f"({selector}) >> index={idx}"
        
        return selector

    # -------------------------------------------------------------------------
    # Execute pending action
    # -------------------------------------------------------------------------

    def execute(self) -> "Locator":
        """Execute the pending action (click, type, etc.).
        
        This is called automatically when you use wait methods or assertions.
        You can also call it explicitly to execute actions:
        
        Example:
            w.click(role, button).execute()
            w.type("hello", role, textbox).filter(placeholder="email").execute()
        """
        if self._action is None:
            return self  # Nothing to execute
        
        # Clear pending state on engine if it was this locator
        if self._web_instance and getattr(self._web_instance, "_pending_locator", None) is self:
            setattr(self._web_instance, "_pending_locator", None)

        selector = self._build_selector()
        
        # Debug mode
        if self._debug:
            self._debug_highlight(selector)
        
        # Wrap execution with retry logic if configured
        def _do_execute():
            # Execute based on action type
            if self._action == "click":
                from pyshaft.web.interactions import click
                click(selector, amount=self._action_args.get("amount", 1))
            elif self._action == "type":
                from pyshaft.web.inputs import type_text
                type_text(selector, self._action_args.get("text", ""), 
                         clear_first=self._action_args.get("clear_first", True))
            elif self._action == "hover":
                from pyshaft.web.interactions import hover
                hover(selector)
            elif self._action == "scroll":
                from pyshaft.web.js_helpers import scroll_into_view
                scroll_into_view(selector)
            elif self._action == "clear":
                from pyshaft.web.inputs import clear_text
                clear_text(selector)
            elif self._action == "check":
                from pyshaft.web.inputs import check_checkbox
                check_checkbox(selector)
            elif self._action == "uncheck":
                from pyshaft.web.inputs import uncheck_checkbox
                uncheck_checkbox(selector)
            elif self._action == "select":
                from pyshaft.web.inputs import select_option
                select_option(selector, self._action_args.get("value"))
            elif self._action == "select_dynamic":
                from pyshaft.web.interactions import click
                click(selector)
                from pyshaft.config import get_config
                import time
                time.sleep(get_config().waits.polling_interval)
                option_text = self._action_args.get("option")
                click(f"text={option_text}")
            elif self._action == "pick_date":
                from pyshaft.web.inputs import type_text
                type_text(selector, self._action_args.get("date", ""), clear_first=True)
                from pyshaft.web.keyboard import press_key
                press_key("ENTER")
            elif self._action == "upload_file":
                from pyshaft.web.inputs import upload_file
                upload_file(selector, self._action_args.get("file_path", ""))
            elif self._action == "remove_element":
                from pyshaft.web.js_helpers import remove_element
                remove_element(selector)
            elif self._action == "switch_to_iframe":
                from pyshaft.core.action_runner import run_driver_action
                from pyshaft.core.locator import DualLocator
                def _switch(driver):
                    el = DualLocator.resolve(driver, selector)
                    driver.switch_to.frame(el)
                run_driver_action("switch_to_iframe", selector, _switch)
            elif self._action == "assert_text":
                from pyshaft.web.assertions import assert_text
                assert_text(selector, self._action_args.get("expected"), 
                           timeout=self._action_args.get("timeout"))
            elif self._action == "assert_visible":
                from pyshaft.web.assertions import assert_visible
                assert_visible(selector, timeout=self._action_args.get("timeout"))
            elif self._action == "assert_hidden":
                from pyshaft.web.assertions import assert_hidden
                assert_hidden(selector, timeout=self._action_args.get("timeout"))
            elif self._action == "assert_enabled":
                from pyshaft.web.assertions import assert_enabled
                assert_enabled(selector, timeout=self._action_args.get("timeout"))
            elif self._action == "assert_disabled":
                from pyshaft.web.assertions import assert_disabled
                assert_disabled(selector, timeout=self._action_args.get("timeout"))
            elif self._action == "assert_checked":
                from pyshaft.web.assertions import assert_checked
                assert_checked(selector, timeout=self._action_args.get("timeout"))
            elif self._action == "press_key":
                from pyshaft.web.keyboard import press_key
                press_key(self._action_args.get("key", ""))
            elif self._action == "assert_contain_attribute":
                from pyshaft.web.assertions import assert_contain_attribute
                assert_contain_attribute(
                    selector, 
                    self._action_args.get("attr"), 
                    self._action_args.get("expected"), 
                    timeout=self._action_args.get("timeout")
                )
        
        # Execute with retry if configured
        if self._retry_config:
            self._retry_config.apply_to_function(_do_execute)
        else:
            _do_execute()
        
        # Action completed
        self._action = None
        self._action_args = {}
        
        return self

    # -------------------------------------------------------------------------
    # Chain Methods
    # -------------------------------------------------------------------------

    def filter(self, **filters) -> "Locator":
        """Add filters to the locator.
        
        Examples:
            click(role,button).filter(class_="primary")
            click(role,button).filter(tag="div", class_="container")
        """
        # Normalize class_ to class
        if "class_" in filters:
            filters["class"] = filters.pop("class_")
            
        new_loc = Locator(
            locator_type=self._locator_type,
            value=self._value,
            modifier=self._modifier,
            **self._filters,
        )
        new_loc._filters = {**self._filters, **filters}
        new_loc._inside = self._inside
        new_loc._index = self._index
        new_loc._debug = self._debug
        new_loc._web_instance = self._web_instance
        new_loc._action = self._action
        new_loc._action_args = self._action_args.copy()
        new_loc._retry_config = self._retry_config
        
        # Update pending locator in web instance
        if new_loc._web_instance and getattr(new_loc._web_instance, "_pending_locator", None) is self:
            setattr(new_loc._web_instance, "_pending_locator", new_loc)
            
        return new_loc

    def inside(self, locator_type: str, value: str) -> "Locator":
        """Add inside clause to find element within a parent.
        
        Examples:
            click(role,button).inside(tag,"modal")
            click(role,input).inside(id,"form-container")
        """
        if callable(locator_type):
            locator_type = getattr(locator_type, "__name__", str(locator_type))
            
        new_loc = Locator(
            locator_type=self._locator_type,
            value=self._value,
            modifier=self._modifier,
            **self._filters,
        )
        new_loc._filters = self._filters.copy()
        new_loc._inside = (locator_type, value)
        new_loc._index = self._index
        new_loc._debug = self._debug
        new_loc._web_instance = self._web_instance
        new_loc._action = self._action
        new_loc._action_args = self._action_args.copy()
        new_loc._retry_config = self._retry_config

        if new_loc._web_instance and getattr(new_loc._web_instance, "_pending_locator", None) is self:
            setattr(new_loc._web_instance, "_pending_locator", new_loc)
            
        return new_loc

    def _clone_with_modifier(self, modifier: str, **kwargs) -> "Locator":
        """Helper to clone locator and set a specific modifier and target."""
        new_loc = Locator(
            locator_type=self._locator_type,
            value=self._value,
            modifier=modifier,
            **self._filters,
        )
        
        if kwargs:
            k, v = next(iter(kwargs.items()))
            new_loc._locator_type = k
            new_loc._value = v
            
        new_loc._filters = self._filters.copy()
        new_loc._inside = self._inside
        new_loc._index = self._index
        new_loc._debug = self._debug
        new_loc._web_instance = self._web_instance
        new_loc._action = self._action
        new_loc._action_args = self._action_args.copy()
        new_loc._retry_config = self._retry_config
        
        if new_loc._web_instance and getattr(new_loc._web_instance, "_pending_locator", None) is self:
            setattr(new_loc._web_instance, "_pending_locator", new_loc)
            
        return new_loc

    def contain(self, **kwargs) -> "Locator":
        """Set modifier to contain and optionally update target.
        
        Example:
            w.click().contain(text="Submit")
            w.click(role, button).contain()
        """
        return self._clone_with_modifier("contain", **kwargs)
        
    def contains(self, **kwargs) -> "Locator":
        """Alias for contain."""
        return self.contain(**kwargs)

    def exact(self, **kwargs) -> "Locator":
        """Set modifier to exact and optionally update target.
        
        Example:
            w.click().exact(text="Submit")
        """
        return self._clone_with_modifier("exact", **kwargs)

    def starts(self, **kwargs) -> "Locator":
        """Set modifier to starts and optionally update target.
        
        Example:
            w.click().starts(id="btn-")
        """
        return self._clone_with_modifier("starts", **kwargs)

    def nth(self, index: int | str, end: int | None = None) -> "Locator":
        """Target the nth element (1-indexed) or a range.
        
        Examples:
            .nth(1)        # 1st element
            .nth(-1)       # last element
            .nth(1, 5)     # elements 1,2,3,4,5 (batch)
            .nth("1:5")    # elements 1-5 as string
        """
        new_loc = Locator(
            locator_type=self._locator_type,
            value=self._value,
            modifier=self._modifier,
            **self._filters,
        )
        new_loc._filters = self._filters.copy()
        new_loc._inside = self._inside
        new_loc._debug = self._debug
        new_loc._web_instance = self._web_instance
        new_loc._action = self._action
        new_loc._action_args = self._action_args.copy()
        new_loc._retry_config = self._retry_config

        if new_loc._web_instance and getattr(new_loc._web_instance, "_pending_locator", None) is self:
            setattr(new_loc._web_instance, "_pending_locator", new_loc)
            
        # Parse the index
        if end is not None:
            # Range mode: nth(start, end) = elements from start to end
            new_loc._index = (index, end)
        elif isinstance(index, str):
            if ":" in index:
                parts = index.split(":")
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if parts[1] else 0
                new_loc._index = (start, end)  # store as tuple for range
            else:
                new_loc._index = int(index)
        elif isinstance(index, int):
            new_loc._index = index
        else:
            new_loc._index = index
            
        return new_loc

    def first(self) -> "Locator":
        """Target the first element."""
        return self.nth(1)

    def last(self) -> "Locator":
        """Target the last element."""
        return self.nth(-1)

    def debug(self) -> "Locator":
        """Enable debug mode - highlights element and logs info."""
        new_loc = Locator(
            locator_type=self._locator_type,
            value=self._value,
            modifier=self._modifier,
            **self._filters,
        )
        new_loc._filters = self._filters.copy()
        new_loc._inside = self._inside
        new_loc._index = self._index
        new_loc._debug = True
        new_loc._web_instance = self._web_instance
        new_loc._action = self._action
        new_loc._action_args = self._action_args.copy()
        new_loc._retry_config = self._retry_config
        
        if new_loc._web_instance and getattr(new_loc._web_instance, "_pending_locator", None) is self:
            setattr(new_loc._web_instance, "_pending_locator", new_loc)
            
        return new_loc

    def retry(self, count: int, mode: str | type = "all", backoff: float = 1.5) -> "Locator":
        """Configure retry behavior for this action chain.
        
        Args:
            count: Number of retry attempts
            mode: Retry mode - can be:
                - "timeout": Retry on timeout exceptions
                - "fail": Retry on assertion/element not found errors
                - "all": Retry on any exception (default)
                - Exception class: Specific exception type to catch
            backoff: Backoff multiplier between retries (default 1.5)
                
        Examples:
            w.click(role, button).retry(3)  # retry up to 3 times on any error
            w.click(role, button).retry(2, "timeout")  # retry on timeout
            w.assert_text("hello", role, div).retry(3, "fail")  # retry on assertion fail
        """
        from pyshaft.core.retry_utils import RetryConfig
        
        new_loc = Locator(
            locator_type=self._locator_type,
            value=self._value,
            modifier=self._modifier,
            **self._filters,
        )
        new_loc._filters = self._filters.copy()
        new_loc._inside = self._inside
        new_loc._index = self._index
        new_loc._debug = self._debug
        new_loc._web_instance = self._web_instance
        new_loc._action = self._action
        new_loc._action_args = self._action_args.copy()
        new_loc._retry_config = RetryConfig(max_attempts=count, mode=mode, backoff=backoff)
        
        if new_loc._web_instance and getattr(new_loc._web_instance, "_pending_locator", None) is self:
            setattr(new_loc._web_instance, "_pending_locator", new_loc)
            
        return new_loc


    def visible(self, timeout: float | None = None) -> "Locator":
        """Wait for element to become visible, then return self.
        
        Example:
            w.wait(role, spinner).visible()  # wait for spinner to appear
            w.wait(role, modal).visible()   # wait for modal to appear
        """
        from pyshaft.web.assertions import assert_visible
        selector = self._build_selector()
        from pyshaft.web.assertions import assert_visible
        self.execute()  # Execute pending action first
        assert_visible(selector, timeout=timeout)
        return self

    def hidden(self, timeout: float | None = None) -> "Locator":
        """Wait for element to become hidden (or not present).
        
        Example:
            w.wait(role, spinner).hidden()  # wait for spinner to disappear
            w.wait(role, loading).hidden()  # wait for loading to disappear
        """
        from pyshaft.web.assertions import assert_hidden
        selector = self._build_selector()
        self.execute()
        assert_hidden(selector, timeout=timeout)
        return self

    def enabled(self, timeout: float | None = None) -> "Locator":
        """Wait for element to become enabled.
        
        Example:
            w.wait(role, button).enabled()  # wait for button to become enabled
        """
        from pyshaft.web.assertions import assert_enabled
        selector = self._build_selector()
        self.execute()
        assert_enabled(selector, timeout=timeout)
        return self

    def disabled(self, timeout: float | None = None) -> "Locator":
        """Wait for element to become disabled.
        
        Example:
            w.wait(role, button).disabled()  # wait for button to become disabled
        """
        from pyshaft.web.assertions import assert_disabled
        selector = self._build_selector()
        assert_disabled(selector, timeout=timeout)
        return self

    def has_text(self, text: str, timeout: float | None = None) -> "Locator":
        """Wait for element to contain specific text.
        
        Example:
            w.wait(role, message).has_text("Success")
        """
        from pyshaft.web.assertions import assert_text
        selector = self._build_selector()
        self.execute()
        assert_text(selector, text, timeout=timeout)
        return self

    # -------------------------------------------------------------------------
    # Assertions (return self for chaining)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Assertions (return self for chaining)
    # -------------------------------------------------------------------------

    def should_be_visible(self, timeout: float | None = None) -> "Locator":
        """Assert element is visible."""
        from pyshaft.web.assertions import assert_visible
        selector = self._build_selector()
        assert_visible(selector, timeout=timeout)
        return self

    def should_be_hidden(self, timeout: float | None = None) -> "Locator":
        """Assert element is hidden."""
        from pyshaft.web.assertions import assert_hidden
        selector = self._build_selector()
        assert_hidden(selector, timeout=timeout)
        return self

    def should_have_text(self, text: str, timeout: float | None = None) -> "Locator":
        """Assert element has text."""
        from pyshaft.web.assertions import assert_text
        selector = self._build_selector()
        assert_text(selector, text, timeout=timeout)
        return self

    def should_be_enabled(self, timeout: float | None = None) -> "Locator":
        """Assert element is enabled."""
        from pyshaft.web.assertions import assert_enabled
        selector = self._build_selector()
        assert_enabled(selector, timeout=timeout)
        return self

    def should_be_disabled(self, timeout: float | None = None) -> "Locator":
        """Assert element is disabled."""
        from pyshaft.web.assertions import assert_disabled
        selector = self._build_selector()
        assert_disabled(selector, timeout=timeout)
        return self

    def should_be_checked(self, timeout: float | None = None) -> "Locator":
        """Assert checkbox/radio is checked."""
        from pyshaft.web.assertions import assert_checked
        selector = self._build_selector()
        assert_checked(selector, timeout=timeout)
        return self

    def should_have_attribute(self, attr: str, value: str, timeout: float | None = None) -> "Locator":
        """Assert element has attribute with value."""
        from pyshaft.web.assertions import assert_attribute
        selector = self._build_selector()
        assert_attribute(selector, attr, value, timeout=timeout)
        return self

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _debug_highlight(self, selector: str) -> None:
        """Debug: highlight element and log info."""
        try:
            from pyshaft.web.js_helpers import highlight_element
            highlight_element(selector)
            logger.info(f"🔍 Debug: {selector}")
        except Exception as e:
            logger.debug(f"Debug highlight failed: {e}")

    def __repr__(self) -> str:
        return f"<Locator {self._build_selector()}>"

    def _get_final_selector(self) -> str:
        """Legacy compatibility method."""
        return self._build_selector()

    # -------------------------------------------------------------------------
    # Engine Chaining (Proxy to WebEngine)
    # -------------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        # Ignore dunder methods to avoid strange inspection behaviors
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(f"'Locator' object has no attribute '{name}'")
            
        # Proxy to web engine for fluent chaining across entire API
        if self._web_instance and hasattr(self._web_instance, name):
            # Accessing an action on WebEngine will allow syntax like:
            # w.click(role, button).type("hello")
            return getattr(self._web_instance, name)
            
        raise AttributeError(f"'Locator' object has no attribute '{name}'")


# -------------------------------------------------------------------------
# Factory functions for new unified syntax
# -------------------------------------------------------------------------

def locator(selector: str) -> Locator:
    """Create locator from raw CSS/XPath selector."""
    return Locator(value=selector)


def role(value: str) -> Locator:
    """Create role-based locator."""
    return Locator(locator_type="role", value=value)


def text(value: str, contain: bool = True) -> Locator:
    """Create text-based locator."""
    modifier = "contain" if contain else "exact"
    return Locator(locator_type="text", value=value, modifier=modifier)


def label(value: str) -> Locator:
    """Create label-based locator."""
    return Locator(locator_type="label", value=value)


def placeholder(value: str, contain: bool = False) -> Locator:
    """Create placeholder-based locator."""
    modifier = "contain" if contain else None
    return Locator(locator_type="placeholder", value=value, modifier=modifier)


def testid(value: str) -> Locator:
    """Create test-id based locator."""
    return Locator(locator_type="testid", value=value)


def id_(value: str, starts: bool = False, contains: bool = False) -> Locator:
    """Create ID-based locator."""
    modifier = "starts" if starts else ("contains" if contains else None)
    return Locator(locator_type="id", value=value, modifier=modifier)


def class_(value: str) -> Locator:
    """Create class-based locator."""
    return Locator(locator_type="class", value=value)


def css(selector: str) -> Locator:
    """Create CSS selector locator."""
    return Locator(locator_type="css", value=selector)


def xpath(expr: str) -> Locator:
    """Create XPath locator."""
    return Locator(locator_type="xpath", value=expr)


def tag(name: str) -> Locator:
    """Create tag-based locator."""
    return Locator(locator_type="tag", value=name)


def attr(name: str, starts: bool = False, contains: bool = False) -> Locator:
    """Create attribute-based locator."""
    modifier = "starts" if starts else ("contains" if contains else None)
    return Locator(locator_type="attr", value=name, modifier=modifier)


def any_(value: str = "") -> Locator:
    """Create generic locator (matches any element with text)."""
    return Locator(locator_type="any", value=value)


# -------------------------------------------------------------------------
# Legacy factory functions (deprecated)
# -------------------------------------------------------------------------

def get_by_role(role: str, **kwargs: Any) -> Locator:
    """Deprecated: Use w.click(role,button) instead."""
    logger.warning("get_by_role is deprecated. Use w.click(role,button) instead.")
    return Locator(locator_type="role", value=role, **kwargs)


def get_by_text(text: str, exact: bool = False) -> Locator:
    """Deprecated: Use w.click(text,exact,value) instead."""
    logger.warning("get_by_text is deprecated. Use w.click(text,exact,value) instead.")
    modifier = None if exact else "contain"
    return Locator(locator_type="text", value=text, modifier=modifier)


def get_by_label(label: str) -> Locator:
    """Deprecated: Use w.click(label,value) instead."""
    logger.warning("get_by_label is deprecated. Use w.click(label,value) instead.")
    return Locator(locator_type="label", value=label)


def get_by_placeholder(placeholder: str) -> Locator:
    """Deprecated: Use w.click(placeholder,value) instead."""
    logger.warning("get_by_placeholder is deprecated. Use w.click(placeholder,value) instead.")
    return Locator(locator_type="placeholder", value=placeholder)


def get_by_test_id(test_id: str) -> Locator:
    """Deprecated: Use w.click(testid,value) instead."""
    logger.warning("get_by_test_id is deprecated. Use w.click(testid,value) instead.")
    return Locator(locator_type="testid", value=test_id)