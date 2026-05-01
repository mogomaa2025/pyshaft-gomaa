"""PyShaft web inputs — type_text, clear_text, press_key, upload_file, and more.

Provides functions for interacting with input elements, including text fields,
dropdowns, checkboxes, and file uploads.
"""

from __future__ import annotations

import logging
import os

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
    abs_path = os.path.abspath(file_path)
    run_action("upload_file", locator, lambda el: el.send_keys(abs_path))


def upload_files(locator: str, file_paths: list[str]) -> None:
    """Upload multiple files to a file input element (if it supports multiple)."""
    abs_paths = "\n".join(os.path.abspath(p) for p in file_paths)
    run_action("upload_files", locator, lambda el: el.send_keys(abs_paths))


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


def select_options(locator: str, values: list[str | int]) -> None:
    """Select multiple options in a <select multiple> element."""
    def _select_many(element: WebElement) -> None:
        sel = Select(element)
        if not sel.is_multiple:
            logger.warning("Attempting select_options on a single-select dropdown: %s", locator)
            
        for val in values:
            if isinstance(val, int):
                sel.select_by_index(val)
            else:
                try:
                    sel.select_by_value(val)
                except Exception:
                    sel.select_by_visible_text(val)

    run_action("select_options", locator, _select_many)


def deselect_option(locator: str, value: str | int) -> None:
    """Deselect an option in a <select multiple> element."""
    def _deselect(element: WebElement) -> None:
        sel = Select(element)
        if isinstance(value, int):
            sel.deselect_by_index(value)
        else:
            try:
                sel.deselect_by_value(value)
            except Exception:
                sel.deselect_by_visible_text(value)

    run_action("deselect_option", locator, _deselect)


def deselect_all_options(locator: str) -> None:
    """Deselect all options in a <select multiple> element."""
    run_action("deselect_all_options", locator, lambda el: Select(el).deselect_all())


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


def enter_mfa_code(locator: str, totp_key: str) -> None:
    """Generate a TOTP code and type it into the specified field.

    Args:
        locator: Element locator for the 2FA input field.
        totp_key: The secret TOTP key (base32).
    """
    import pyotp

    totp = pyotp.TOTP(totp_key)
    code = totp.now()
    logger.info("Generated MFA code for key %s", totp_key[:4] + "****")
    type_text(locator, code)
