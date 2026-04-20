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

logger = logging.getLogger("pyshaft.web.assertions")


def assert_title(expected: str, timeout: float | None = None) -> None:
    """Assert that the page title matches the expected value.

    Polls the page title until it matches or the timeout is reached.

    Args:
        expected: The expected page title (exact match).
        timeout: Max wait time in seconds (defaults to config).

    Raises:
        AssertionError: If the title doesn't match within the timeout.
    """
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check_title(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout
        last_title = ""

        while time.time() < deadline:
            last_title = driver.title
            if last_title == expected:
                return
            time.sleep(poll)

        raise AssertionError(
            f"Page title mismatch after {timeout:.1f}s\n"
            f"Expected: {expected!r}\n"
            f"Actual:   {last_title!r}"
        )

    run_driver_action("assert_title", f"title == {expected!r}", _check_title)


def assert_title_contains(expected: str, timeout: float | None = None) -> None:
    """Assert that the page title contains the expected substring.

    Args:
        expected: The expected substring in the page title.
        timeout: Max wait time in seconds.

    Raises:
        AssertionError: If the title doesn't contain the substring within timeout.
    """
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check_title(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout
        last_title = ""

        while time.time() < deadline:
            last_title = driver.title
            if expected in last_title:
                return
            time.sleep(poll)

        raise AssertionError(
            f"Page title does not contain {expected!r} after {timeout:.1f}s\n"
            f"Actual title: {last_title!r}"
        )

    run_driver_action("assert_title_contains", f"title contains {expected!r}", _check_title)


def assert_contain_title(expected: str, timeout: float | None = None) -> None:
    """Alias for assert_title_contains."""
    assert_title_contains(expected, timeout=timeout)


def assert_url(expected: str, timeout: float | None = None) -> None:
    """Assert that the current URL matches the expected value.

    Args:
        expected: The expected URL (exact match).
        timeout: Max wait time in seconds.

    Raises:
        AssertionError: If the URL doesn't match within timeout.
    """
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check_url(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout
        last_url = ""

        while time.time() < deadline:
            last_url = driver.current_url
            if last_url == expected:
                return
            time.sleep(poll)

        raise AssertionError(
            f"URL mismatch after {timeout:.1f}s\n"
            f"Expected: {expected!r}\n"
            f"Actual:   {last_url!r}"
        )

    run_driver_action("assert_url", f"url == {expected!r}", _check_url)


def assert_url_contains(expected: str, timeout: float | None = None) -> None:
    """Assert that the current URL contains the expected substring.

    Args:
        expected: The expected substring in the URL.
        timeout: Max wait time in seconds.

    Raises:
        AssertionError: If the URL doesn't contain the substring within timeout.
    """
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check_url(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout
        last_url = ""

        while time.time() < deadline:
            last_url = driver.current_url
            if expected in last_url:
                return
            time.sleep(poll)

        raise AssertionError(
            f"URL does not contain {expected!r} after {timeout:.1f}s\n"
            f"Actual URL: {last_url!r}"
        )

    run_driver_action("assert_url_contains", f"url contains {expected!r}", _check_url)


def assert_contain_url(expected: str, timeout: float | None = None) -> None:
    """Alias for assert_url_contains."""
    assert_url_contains(expected, timeout=timeout)


def assert_text(locator: str, expected: str, timeout: float | None = None) -> None:
    """Assert that the element's text contains the expected value."""
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
                if expected in last_text:
                    return
            except Exception:
                pass
            time.sleep(poll)

        raise AssertionError(
            f"Element {locator!r} text mismatch after {timeout:.1f}s\n"
            f"Expected to contain: {expected!r}\n"
            f"Actual text:         {last_text!r}"
        )

    run_driver_action("assert_text", f"{locator!r} contains {expected!r}", _check)


def assert_contain_text(locator: str, expected: str, timeout: float | None = None) -> None:
    """Alias for assert_text."""
    assert_text(locator, expected, timeout=timeout)


def assert_visible(locator: str, timeout: float | None = None) -> None:
    """Assert that an element is visible on the page."""
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                element = DualLocator.resolve(driver, locator)
                if _is_visible(driver, element):
                    return
            except Exception:
                pass
            time.sleep(poll)

        raise AssertionError(f"Element {locator!r} was not visible after {timeout:.1f}s")

    run_driver_action("assert_visible", locator, _check)


def assert_hidden(locator: str, timeout: float | None = None) -> None:
    """Assert that an element is hidden or not in the DOM."""
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                element = DualLocator.resolve(driver, locator)
                if not _is_visible(driver, element):
                    return
            except Exception:
                return
            time.sleep(poll)

        raise AssertionError(f"Element {locator!r} was still visible after {timeout:.1f}s")

    run_driver_action("assert_hidden", locator, _check)


def assert_attribute(locator: str, attr: str, expected: str, timeout: float | None = None) -> None:
    """Assert that an element's attribute matches the expected value."""
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout
        last_val = ""

        while time.time() < deadline:
            try:
                element = DualLocator.resolve(driver, locator)
                last_val = element.get_attribute(attr) or ""
                if last_val == expected:
                    return
            except Exception:
                pass
            time.sleep(poll)

        raise AssertionError(
            f"Element {locator!r} attribute {attr!r} mismatch after {timeout:.1f}s\n"
            f"Expected: {expected!r}\n"
            f"Actual:   {last_val!r}"
        )

    run_driver_action("assert_attribute", f"{locator}[{attr}] == {expected}", _check)


def assert_contain_attribute(locator: str, attr: str, expected: str, timeout: float | None = None) -> None:
    """Assert that an element's attribute contains the expected value."""
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout
        last_val = ""

        while time.time() < deadline:
            try:
                element = DualLocator.resolve(driver, locator)
                last_val = element.get_attribute(attr) or ""
                if expected in last_val:
                    return
            except Exception:
                pass
            time.sleep(poll)

        raise AssertionError(
            f"Element {locator!r} attribute {attr!r} containment mismatch after {timeout:.1f}s\n"
            f"Expected to contain: {expected!r}\n"
            f"Actual value:        {last_val!r}"
        )

    run_driver_action("assert_contain_attribute", f"{locator}[{attr}] contains {expected}", _check)


def assert_enabled(locator: str, timeout: float | None = None) -> None:
    """Assert that an element is enabled."""
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                element = DualLocator.resolve(driver, locator)
                if element.is_enabled():
                    return
            except Exception:
                pass
            time.sleep(poll)

        raise AssertionError(f"Element {locator!r} was not enabled after {timeout:.1f}s")

    run_driver_action("assert_enabled", locator, _check)


def assert_disabled(locator: str, timeout: float | None = None) -> None:
    """Assert that an element is disabled."""
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                element = DualLocator.resolve(driver, locator)
                if not element.is_enabled():
                    return
            except Exception:
                pass
            time.sleep(poll)

        raise AssertionError(f"Element {locator!r} was not disabled after {timeout:.1f}s")

    run_driver_action("assert_disabled", locator, _check)


def assert_checked(locator: str, timeout: float | None = None) -> None:
    """Assert that an element (checkbox/radio) is checked."""
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _check(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                element = DualLocator.resolve(driver, locator)
                if element.is_selected():
                    return
            except Exception:
                pass
            time.sleep(poll)

        raise AssertionError(f"Element {locator!r} was not checked after {timeout:.1f}s")

    run_driver_action("assert_checked", locator, _check)
