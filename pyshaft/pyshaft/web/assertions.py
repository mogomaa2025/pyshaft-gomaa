"""PyShaft web assertions — assert_title, assert_text, assert_url, and more.

Provides auto-waiting assertions for page state and element properties.
"""

from __future__ import annotations

import logging
import time

from selenium.webdriver.remote.webdriver import WebDriver

from pyshaft.config import get_config
from pyshaft.core.action_runner import run_driver_action
from pyshaft.core.locator import DualLocator
from pyshaft.core.wait_engine import _is_visible
from pyshaft.session import session_context
from pyshaft.web import screenshot, aria

logger = logging.getLogger("pyshaft.web.assertions")

def _wait_until(condition_func, timeout, error_message):
    """Wait for a condition to be true, polling regularly."""
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout
    poll = config.waits.polling_interval
    deadline = time.time() + timeout

    while time.time() < deadline:
        res, last_val = condition_func()
        if res:
            return True, last_val
        time.sleep(poll)
    
    raise AssertionError(error_message.format(timeout=timeout, last_val=last_val))


def assert_title(expected: str, timeout: float | None = None) -> None:
    """Assert that the page title matches the expected value."""
    def _check_title(driver: WebDriver) -> None:
        _wait_until(
            lambda: (driver.title == expected, driver.title),
            timeout,
            "Page title mismatch after {timeout:.1f}s\nExpected: " + f"{expected!r}" + "\nActual:   {last_val!r}"
        )
    run_driver_action("assert_title", f"title == {expected!r}", _check_title)


def assert_title_contains(expected: str, timeout: float | None = None) -> None:
    """Assert that the page title contains the expected substring."""
    def _check_title(driver: WebDriver) -> None:
        _wait_until(
            lambda: (expected in driver.title, driver.title),
            timeout,
            "Page title does not contain " + f"{expected!r}" + " after {timeout:.1f}s\nActual title: {last_val!r}"
        )
    run_driver_action("assert_title_contains", f"title contains {expected!r}", _check_title)


def assert_contain_title(expected: str, timeout: float | None = None) -> None:
    """Alias for assert_title_contains."""
    assert_title_contains(expected, timeout=timeout)


def assert_url(expected: str, timeout: float | None = None) -> None:
    """Assert that the current URL matches the expected value."""
    def _check_url(driver: WebDriver) -> None:
        _wait_until(
            lambda: (driver.current_url == expected, driver.current_url),
            timeout,
            "URL mismatch after {timeout:.1f}s\nExpected: " + f"{expected!r}" + "\nActual:   {last_val!r}"
        )
    run_driver_action("assert_url", f"url == {expected!r}", _check_url)


def assert_url_contains(expected: str, timeout: float | None = None) -> None:
    """Assert that the current URL contains the expected substring."""
    def _check_url(driver: WebDriver) -> None:
        _wait_until(
            lambda: (expected in driver.current_url, driver.current_url),
            timeout,
            "URL does not contain " + f"{expected!r}" + " after {timeout:.1f}s\nActual URL: {last_val!r}"
        )
    run_driver_action("assert_url_contains", f"url contains {expected!r}", _check_url)


def assert_contain_url(expected: str, timeout: float | None = None) -> None:
    """Alias for assert_url_contains."""
    assert_url_contains(expected, timeout=timeout)


def assert_text(locator: str, expected: str, timeout: float | None = None) -> None:
    """Assert that the element's text contains the expected value."""
    def _check(driver: WebDriver) -> None:
        def condition():
            try:
                el = DualLocator.resolve(driver, locator)
                txt = el.text or ""
                return expected in txt, txt
            except Exception:
                return False, ""
                
        _wait_until(
            condition,
            timeout,
            f"Element {locator!r} text mismatch after {{timeout:.1f}}s\nExpected to contain: {expected!r}\nActual text:         {{last_val!r}}"
        )
    run_driver_action("assert_text", f"{locator!r} contains {expected!r}", _check)


def assert_contain_text(locator: str, expected: str, timeout: float | None = None) -> None:
    """Alias for assert_text."""
    assert_text(locator, expected, timeout=timeout)


def assert_visible(locator: str, timeout: float | None = None) -> None:
    """Assert that an element is visible on the page."""
    def _check(driver: WebDriver) -> None:
        def condition():
            try:
                el = DualLocator.resolve(driver, locator)
                return _is_visible(driver, el), ""
            except Exception:
                return False, ""
        _wait_until(condition, timeout, f"Element {locator!r} was not visible after {{timeout:.1f}}s")
    run_driver_action("assert_visible", locator, _check)


def assert_hidden(locator: str, timeout: float | None = None) -> None:
    """Assert that an element is hidden or not in the DOM."""
    def _check(driver: WebDriver) -> None:
        def condition():
            try:
                el = DualLocator.resolve(driver, locator)
                return not _is_visible(driver, el), ""
            except Exception:
                return True, ""
        _wait_until(condition, timeout, f"Element {locator!r} was still visible after {{timeout:.1f}}s")
    run_driver_action("assert_hidden", locator, _check)


def assert_attribute(locator: str, attr: str, expected: str, timeout: float | None = None) -> None:
    """Assert that an element's attribute matches the expected value."""
    def _check(driver: WebDriver) -> None:
        def condition():
            try:
                el = DualLocator.resolve(driver, locator)
                val = el.get_attribute(attr) or ""
                return val == expected, val
            except Exception:
                return False, ""
        _wait_until(
            condition,
            timeout,
            f"Element {locator!r} attribute {attr!r} mismatch after {{timeout:.1f}}s\nExpected: {expected!r}\nActual:   {{last_val!r}}"
        )
    run_driver_action("assert_attribute", f"{locator}[{attr}] == {expected}", _check)


def assert_contain_attribute(locator: str, attr: str, expected: str, timeout: float | None = None) -> None:
    """Assert that an element's attribute contains the expected value."""
    def _check(driver: WebDriver) -> None:
        def condition():
            try:
                el = DualLocator.resolve(driver, locator)
                val = el.get_attribute(attr) or ""
                return expected in val, val
            except Exception:
                return False, ""
        _wait_until(
            condition,
            timeout,
            f"Element {locator!r} attribute {attr!r} containment mismatch after {{timeout:.1f}}s\nExpected to contain: {expected!r}\nActual value:        {{last_val!r}}"
        )
    run_driver_action("assert_contain_attribute", f"{locator}[{attr}] contains {expected}", _check)


def assert_enabled(locator: str, timeout: float | None = None) -> None:
    """Assert that an element is enabled."""
    def _check(driver: WebDriver) -> None:
        def condition():
            try:
                el = DualLocator.resolve(driver, locator)
                return el.is_enabled(), ""
            except Exception:
                return False, ""
        _wait_until(condition, timeout, f"Element {locator!r} was not enabled after {{timeout:.1f}}s")
    run_driver_action("assert_enabled", locator, _check)


def assert_disabled(locator: str, timeout: float | None = None) -> None:
    """Assert that an element is disabled."""
    def _check(driver: WebDriver) -> None:
        def condition():
            try:
                el = DualLocator.resolve(driver, locator)
                return not el.is_enabled(), ""
            except Exception:
                return False, ""
        _wait_until(condition, timeout, f"Element {locator!r} was not disabled after {{timeout:.1f}}s")
    run_driver_action("assert_disabled", locator, _check)


def assert_checked(locator: str, timeout: float | None = None) -> None:
    """Assert that an element (checkbox/radio) is checked."""
    def _check(driver: WebDriver) -> None:
        def condition():
            try:
                el = DualLocator.resolve(driver, locator)
                return el.is_selected(), ""
            except Exception:
                return False, ""
        _wait_until(condition, timeout, f"Element {locator!r} was not checked after {{timeout:.1f}}s")
    run_driver_action("assert_checked", locator, _check)


def assert_snapshot(locator: str, name: str, timeout: float | None = None) -> None:
    """Assert visual layout of an element matches a baseline snapshot."""
    def _check(driver: WebDriver) -> None:
        def condition():
            try:
                el = DualLocator.resolve(driver, locator)
                return _is_visible(driver, el), ""
            except Exception:
                return False, ""
        _wait_until(condition, timeout, f"Element {locator!r} not visible for snapshot")
        screenshot.take_element_screenshot(locator, name=name)
        
    run_driver_action("assert_snapshot", f"{locator!r} matches {name!r}", _check)


def assert_aria_snapshot(locator: str, expected_yaml: str, timeout: float | None = None) -> None:
    """Assert that an element's Aria Tree matches the expected YAML structure."""
    def _check(driver: WebDriver) -> None:
        def condition():
            try:
                aria.assert_aria_snapshot(locator, expected_yaml)
                return True, ""
            except Exception as e:
                return False, str(e)
        _wait_until(condition, timeout, "Aria snapshot mismatch: {last_val}")
        
    run_driver_action("assert_aria_snapshot", locator, _check)
