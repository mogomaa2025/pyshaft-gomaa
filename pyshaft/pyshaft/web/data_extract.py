"""PyShaft web data extraction — get_selected_option, assert_selected_option, assert_data_type, assert_value.

Provides functions for extracting values from elements and asserting
data types and dropdown selections.
"""

from __future__ import annotations

import logging
import re
import time

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select

from pyshaft.config import get_config
from pyshaft.core.action_runner import run_action, run_driver_action
from pyshaft.core.locator import DualLocator

logger = logging.getLogger("pyshaft.web.data_extract")


# ── Type validation patterns ──────────────────────────────────────────────

_TYPE_VALIDATORS: dict[str, callable] = {
    "int": lambda v: v.lstrip("-").isdigit(),
    "integer": lambda v: v.lstrip("-").isdigit(),
    "float": lambda v: bool(re.fullmatch(r"-?\d+(\.\d+)?", v.strip())),
    "double": lambda v: bool(re.fullmatch(r"-?\d+(\.\d+)?", v.strip())),
    "number": lambda v: bool(re.fullmatch(r"-?\d+(\.\d+)?", v.strip())),
    "string": lambda _: True,
    "str": lambda _: True,
    "bool": lambda v: v.strip().lower() in ("true", "false"),
    "boolean": lambda v: v.strip().lower() in ("true", "false"),
    "email": lambda v: bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v.strip())),
    "url": lambda v: bool(re.fullmatch(r"https?://\S+", v.strip())),
    "date": lambda v: bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.strip())),
    "phone": lambda v: bool(re.fullmatch(r"[\d\s\-\+\(\)]{7,20}", v.strip())),
    "uuid": lambda v: bool(
        re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", v.strip(), re.I)
    ),
    "empty": lambda v: v.strip() == "",
    "not_empty": lambda v: v.strip() != "",
}


def get_selected_option(locator: str) -> str:
    """Get the visible text of the currently selected option in a <select>.

    Args:
        locator: Element locator for the <select> element.

    Returns:
        The visible text of the selected option.
    """
    def _get(element: WebElement) -> str:
        sel = Select(element)
        return sel.first_selected_option.text

    return run_action("get_selected_option", locator, _get)


def get_selected_options(locator: str) -> list[str]:
    """Get the visible text of all currently selected options in a <select multiple>.

    Args:
        locator: Element locator for the <select> element.

    Returns:
        List of visible texts of selected options.
    """
    def _get_many(element: WebElement) -> list[str]:
        sel = Select(element)
        return [opt.text for opt in sel.all_selected_options]

    return run_action("get_selected_options", locator, _get_many)


def get_selected_value(locator: str) -> str:
    """Get the value attribute of the currently selected option in a <select>.

    Args:
        locator: Element locator for the <select> element.

    Returns:
        The value of the selected option.
    """
    def _get(element: WebElement) -> str:
        sel = Select(element)
        return sel.first_selected_option.get_attribute("value") or ""

    return run_action("get_selected_value", locator, _get)


def get_all_options(locator: str) -> list[str]:
    """Get visible text of all options in a <select>.

    Args:
        locator: Element locator for the <select> element.

    Returns:
        List of option texts.
    """
    def _get(element: WebElement) -> list[str]:
        sel = Select(element)
        return [opt.text for opt in sel.options]

    return run_action("get_all_options", locator, _get)


def assert_selected_option(
    locator: str,
    expected: str,
    timeout: float | None = None,
) -> None:
    """Assert that a <select>'s selected option text matches expected.

    Args:
        locator: Element locator for the <select> element.
        expected: Expected exact text of the selected option.
        timeout: Max wait time in seconds.

    Raises:
        AssertionError: If the selected option doesn't match.
    """
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout
        last_text = ""

        while time.time() < deadline:
            try:
                element = DualLocator.resolve(driver, locator)
                sel = Select(element)
                last_text = sel.first_selected_option.text
                if last_text == expected:
                    return
            except Exception:
                pass
            time.sleep(poll)

        raise AssertionError(
            f"Selected option mismatch after {timeout:.1f}s\n"
            f"Expected: {expected!r}\n"
            f"Actual:   {last_text!r}"
        )

    run_driver_action("assert_selected_option", f"{locator!r} selected == {expected!r}", _check)


def assert_contain_selected(
    locator: str,
    expected: str,
    timeout: float | None = None,
) -> None:
    """Assert that a <select>'s selected option text contains expected substring.

    Args:
        locator: Element locator for the <select> element.
        expected: Expected substring in the selected option text.
        timeout: Max wait time in seconds.

    Raises:
        AssertionError: If the selected option doesn't contain expected.
    """
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout
        last_text = ""

        while time.time() < deadline:
            try:
                element = DualLocator.resolve(driver, locator)
                sel = Select(element)
                last_text = sel.first_selected_option.text
                if expected in last_text:
                    return
            except Exception:
                pass
            time.sleep(poll)

        raise AssertionError(
            f"Selected option does not contain {expected!r} after {timeout:.1f}s\n"
            f"Actual selected: {last_text!r}"
        )

    run_driver_action(
        "assert_contain_selected",
        f"{locator!r} selected contains {expected!r}",
        _check,
    )


def assert_data_type(
    locator: str,
    expected_type: str,
    timeout: float | None = None,
) -> None:
    """Assert that an element's text matches the expected data type.

    Supported types: int, float, double, number, string, str, bool, boolean,
    email, url, date, phone, uuid, empty, not_empty.

    Args:
        locator: Element locator.
        expected_type: The expected data type name.
        timeout: Max wait time in seconds.

    Raises:
        AssertionError: If the text doesn't match the expected type.
        ValueError: If the expected type is not supported.
    """
    validator = _TYPE_VALIDATORS.get(expected_type.lower())
    if validator is None:
        raise ValueError(
            f"Unsupported data type: {expected_type!r}. "
            f"Supported: {sorted(_TYPE_VALIDATORS.keys())}"
        )

    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout
        last_text = ""

        while time.time() < deadline:
            try:
                element = DualLocator.resolve(driver, locator)
                last_text = element.text or ""
                if validator(last_text):
                    return
            except Exception:
                pass
            time.sleep(poll)

        raise AssertionError(
            f"Element {locator!r} text is not of type {expected_type!r} "
            f"after {timeout:.1f}s\n"
            f'Actual text: {last_text!r}'
        )

    run_driver_action("assert_data_type", f"{locator!r} is {expected_type}", _check)


def assert_value(
    locator: str,
    expected: str,
    timeout: float | None = None,
) -> None:
    """Assert that an element's value attribute matches expected.

    Args:
        locator: Element locator.
        expected: The expected value.
        timeout: Max wait time in seconds.

    Raises:
        AssertionError: If the value doesn't match.
    """
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout
        last_val = ""

        while time.time() < deadline:
            try:
                element = DualLocator.resolve(driver, locator)
                last_val = element.get_attribute("value") or ""
                if last_val == expected:
                    return
            except Exception:
                pass
            time.sleep(poll)

        raise AssertionError(
            f"Element {locator!r} value mismatch after {timeout:.1f}s\n"
            f"Expected: {expected!r}\n"
            f"Actual:   {last_val!r}"
        )

    run_driver_action("assert_value", f"{locator!r} value == {expected!r}", _check)
