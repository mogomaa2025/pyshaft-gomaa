"""PyShaft web inputs — type_text, clear_text, press_key, upload_file, and more.

Provides functions for interacting with input elements, including text fields,
dropdowns, checkboxes, and file uploads.
"""

from __future__ import annotations

import logging

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select

from pyshaft.config import get_config
from pyshaft.core.action_runner import run_action

logger = logging.getLogger("pyshaft.web.inputs")


def type_text(locator: str, text: str, clear_first: bool = True) -> None:
    """Type text into an input element.

    Args:
        locator: Element locator (CSS, XPath, or semantic description).
        text: The text to type.
        clear_first: If True, clears the field before typing (default).
    """
    config = get_config()

    def _type(element: WebElement) -> None:
        if clear_first:
            element.clear()
        element.send_keys(text)

        # Verify text was entered if force_text_verification is on
        if config.validations.force_text_verification:
            actual = element.get_attribute("value") or ""
            if text not in actual:
                logger.warning(
                    "Text verification failed: typed %r but field contains %r",
                    text,
                    actual,
                )

    run_action("type_text", locator, _type)


def clear_text(locator: str) -> None:
    """Clear the text from an input element."""
    run_action("clear_text", locator, lambda el: el.clear())


def press_key(locator: str, key: str) -> None:
    """Press a keyboard key on an element.

    Args:
        locator: Element locator.
        key: Key name (e.g., "ENTER", "TAB", "ESCAPE").
    """
    key_map = {
        "ENTER": Keys.ENTER,
        "RETURN": Keys.RETURN,
        "TAB": Keys.TAB,
        "ESCAPE": Keys.ESCAPE,
        "ESC": Keys.ESCAPE,
        "BACKSPACE": Keys.BACKSPACE,
        "DELETE": Keys.DELETE,
        "SPACE": Keys.SPACE,
        "ARROW_UP": Keys.ARROW_UP,
        "ARROW_DOWN": Keys.ARROW_DOWN,
        "ARROW_LEFT": Keys.ARROW_LEFT,
        "ARROW_RIGHT": Keys.ARROW_RIGHT,
        "HOME": Keys.HOME,
        "END": Keys.END,
        "PAGE_UP": Keys.PAGE_UP,
        "PAGE_DOWN": Keys.PAGE_DOWN,
    }

    selenium_key = key_map.get(key.upper(), key)
    run_action("press_key", locator, lambda el: el.send_keys(selenium_key))


def upload_file(locator: str, file_path: str) -> None:
    """Upload a file to a file input element."""
    run_action("upload_file", locator, lambda el: el.send_keys(file_path))


def get_text(locator: str) -> str:
    """Get the visible text of an element."""
    return run_action("get_text", locator, lambda el: el.text)


def get_value(locator: str) -> str:
    """Get the 'value' attribute of an element."""
    return run_action("get_value", locator, lambda el: el.get_attribute("value") or "")


def get_attribute(locator: str, attribute: str) -> str:
    """Get the value of a specific attribute of an element."""
    return run_action("get_attribute", locator, lambda el: el.get_attribute(attribute) or "")


def select_option(locator: str, value: str | int) -> None:
    """Select an option in a <select> element by value, text, or index."""
    def _select(element: WebElement) -> None:
        sel = Select(element)
        if isinstance(value, int):
            sel.select_by_index(value)
        else:
            try:
                sel.select_by_value(value)
            except Exception:
                sel.select_by_visible_text(value)

    run_action("select_option", locator, _select)


def check_checkbox(locator: str) -> None:
    """Ensure a checkbox or radio button is checked."""
    def _check(element: WebElement) -> None:
        if not element.is_selected():
            element.click()

    run_action("check_checkbox", locator, _check)


def uncheck_checkbox(locator: str) -> None:
    """Ensure a checkbox is unchecked."""
    def _uncheck(element: WebElement) -> None:
        if element.is_selected():
            element.click()

    run_action("uncheck_checkbox", locator, _uncheck)
