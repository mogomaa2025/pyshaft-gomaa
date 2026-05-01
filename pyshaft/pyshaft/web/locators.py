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
import inspect
from functools import wraps
from typing import Any

logger = logging.getLogger("pyshaft.web.locators")

def chainable(engine_method_name: str | None = None):
    """Decorator to enable seamless chaining of Locator and WebEngine actions.
    
    If locator-specific arguments (locator_type, value, filters) are provided,
    it executes any pending action on the current Locator and forwards the call
    to the WebEngine to start a new action chain.
    Otherwise, it executes any pending action and sets the new action on the current Locator.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Always flush the previous action if we are applying a new one
            self.execute()
            
            sig = inspect.signature(func)
            bound = sig.bind(self, *args, **kwargs)
            bound.apply_defaults()
            
            loc_type = bound.arguments.get("locator_type")
            val = bound.arguments.get("value")
            # The kwargs parameter might be named 'filters' or 'kwargs'
            var_kwargs_name = None
            for param in sig.parameters.values():
                if param.kind == inspect.Parameter.VAR_KEYWORD:
                    var_kwargs_name = param.name
                    break
            
            filters = bound.arguments.get(var_kwargs_name, {}) if var_kwargs_name else {}
            
            # If targeting a new element, forward to WebEngine
            if loc_type or val or filters:
                method_name = engine_method_name or func.__name__
                engine_method = getattr(self._web_instance, method_name)
                
                kwargs_to_pass = {}
                for k, v in bound.arguments.items():
                    if k == "self": continue
                    if k == var_kwargs_name:
                        kwargs_to_pass.update(v)
                    else:
                        kwargs_to_pass[k] = v
                        
                return engine_method(**kwargs_to_pass)
            
            # Otherwise, apply action to the current Locator
            res = func(self, *args, **kwargs)
            
            # Auto-flush if this was a terminal action (it set a pending locator)
            if self._web_instance and self._web_instance._pending_locator == self:
                self._web_instance.flush()
                
            return res
        return wrapper
    return decorator


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
            elif self._action == "double_click":
                from pyshaft.web.interactions import double_click
                double_click(selector)
            elif self._action == "right_click":
                from pyshaft.web.interactions import right_click
                right_click(selector)
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
            elif self._action == "select_options":
                from pyshaft.web.inputs import select_options
                select_options(selector, self._action_args.get("values", []))
            elif self._action == "deselect_option":
                from pyshaft.web.inputs import deselect_option
                deselect_option(selector, self._action_args.get("value"))
            elif self._action == "deselect_all_options":
                from pyshaft.web.inputs import deselect_all_options
                deselect_all_options(selector)
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
            elif self._action == "upload_files":
                from pyshaft.web.inputs import upload_files
                upload_files(selector, self._action_args.get("file_paths", []))
            elif self._action == "enter_mfa_code":
                from pyshaft.web.inputs import enter_mfa_code
                enter_mfa_code(selector, self._action_args.get("totp_key", ""))
            elif self._action == "remove_element":
                from pyshaft.web.js_helpers import remove_element
                remove_element(selector)
            elif self._action == "remove_elements":
                from pyshaft.web.js_helpers import remove_elements
                remove_elements(selector)
            elif self._action == "switch_to_iframe":
                from pyshaft.web.navigation import switch_to_frame
                switch_to_frame(selector)
            elif self._action == "drag_by_offset":
                from pyshaft.web.interactions import drag_by_offset
                drag_by_offset(selector, self._action_args.get("x", 0), self._action_args.get("y", 0))
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

    def shadow(self, selector: str) -> "Locator":
        """Target an element within shadow DOM.

        Example:
            w.wait().shadow("button.primary").visible()
        """
        new_loc = Locator(value=f"shadow > {selector}")
        new_loc._web_instance = self
        return new_loc

    # -------------------------------------------------------------------------
    # Action Methods (Terminal)
    # -------------------------------------------------------------------------

    @chainable()
    def click(
        self,
        locator_type: str | None = None,
        value: str = "",
        amount: int = 1,
        **filters: Any,
    ) -> "Locator":
        """Set pending click action. If locator info provided, starts a new action."""
        self._action = "click"
        self._action_args = {"amount": amount}
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

    @chainable()
    def double_click(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "Locator":
        """Set pending double_click action."""
        self._action = "double_click"
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

    @chainable()
    def right_click(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "Locator":
        """Set pending right_click action."""
        self._action = "right_click"
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

    @chainable()
    def type(
        self,
        text: str,
        locator_type: str | None = None,
        value: str = "",
        clear_first: bool = True,
        **filters: Any,
    ) -> "Locator":
        """Set pending type action."""
        self._action = "type"
        self._action_args = {"text": text, "clear_first": clear_first}
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

    @chainable()
    def fill(self, text: str, **kwargs) -> "Locator":
        """Alias for type."""
        return self.type(text, **kwargs)

    @chainable()
    def clear(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "Locator":
        """Set pending clear action."""
        self._action = "clear"
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

    @chainable()
    def hover(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "Locator":
        """Set pending hover action."""
        self._action = "hover"
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

    @chainable()
    def check(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "Locator":
        """Set pending check action."""
        self._action = "check"
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

    @chainable()
    def uncheck(
        self,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "Locator":
        """Set pending uncheck action."""
        self._action = "uncheck"
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

    @chainable()
    def select(
        self,
        option: str | int,
        locator_type: str | None = None,
        value: str = "",
        **filters: Any,
    ) -> "Locator":
        """Set pending select action."""
        self._action = "select"
        self._action_args = {"value": option}
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

    @chainable()
    def should_match_snapshot(self, name: str) -> "Locator":
        """Assert visual layout of the element matches a baseline snapshot."""
        self._action = "assert_snapshot"
        self._action_args = {"name": name}
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

    @chainable()
    def should_match_aria_snapshot(self, expected_yaml: str) -> "Locator":
        """Assert semantic structure matches expected ARIA YAML."""
        self._action = "assert_aria_snapshot"
        self._action_args = {"expected_yaml": expected_yaml}
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

    def drag_by_offset(self, x: int, y: int) -> "Locator":
        """Set pending drag_by_offset action."""
        self._action = "drag_by_offset"
        self._action_args = {"x": x, "y": y}
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

    def enter_mfa_code(self, totp_key: str) -> "Locator":
        """Set pending enter_mfa_code action."""
        self._action = "enter_mfa_code"
        self._action_args = {"totp_key": totp_key}
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

    def remove(self) -> "Locator":
        """Set pending remove action."""
        self._action = "remove_element"
        if self._web_instance:
            self._web_instance._pending_locator = self
        return self

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
            attr = getattr(self._web_instance, name)
            if callable(attr):
                # We return a wrapper that flushes the current locator before executing the next command
                def _wrapper(*args, **kwargs):
                    self.execute()
                    return attr(*args, **kwargs)
                return _wrapper
            return attr

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