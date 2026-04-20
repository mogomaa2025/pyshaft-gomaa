"""PyShaft web waits — public wait API for tests.

Provides wait functions that tests can use directly:
    - ``wait_for_text(locator, expected)`` — wait for text in element
    - ``wait_for_visible(locator)`` — wait for element to become visible
    - ``wait_for_hidden(locator)`` — wait for element to disappear
    - ``wait_for_element(locator)`` — wait for element to exist in DOM
    - ``wait_until(condition)`` — wait for custom condition
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from selenium.webdriver.remote.webdriver import WebDriver

from pyshaft.config import get_config
from pyshaft.core.action_runner import run_driver_action
from pyshaft.core.locator import DualLocator
from pyshaft.core.wait_engine import WaitEngine, _is_visible
from pyshaft.exceptions import WaitTimeoutError
from pyshaft.session import session_context

logger = logging.getLogger("pyshaft.web.waits")


def wait_for_text(
    locator: str,
    expected: str,
    timeout: float | None = None,
) -> None:
    """Wait for an element's text to contain the expected value.

    Args:
        locator: Element locator (CSS, XPath, or semantic).
        expected: The text to wait for (substring match).
        timeout: Max wait time in seconds.

    Raises:
        WaitTimeoutError: If text doesn't appear within timeout.
    """
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _wait(driver: WebDriver) -> None:
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

        raise WaitTimeoutError(
            condition=f"text {expected!r} in element {locator!r}",
            timeout=timeout,
            element_state={"last_text": last_text},
        )

    run_driver_action("wait_for_text", f"{locator!r} contains {expected!r}", _wait)


def wait_for_visible(
    locator: str,
    timeout: float | None = None,
) -> None:
    """Wait for an element to become visible on the page.

    Args:
        locator: Element locator.
        timeout: Max wait time in seconds.

    Raises:
        WaitTimeoutError: If element doesn't become visible within timeout.
    """
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _wait(driver: WebDriver) -> None:
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

        raise WaitTimeoutError(
            condition=f"element {locator!r} visible",
            timeout=timeout,
        )

    run_driver_action("wait_for_visible", locator, _wait)


def wait_for_hidden(
    locator: str,
    timeout: float | None = None,
) -> None:
    """Wait for an element to become hidden or removed from the page.

    Useful for waiting for loading spinners, modals, or overlays to disappear.

    Args:
        locator: Element locator.
        timeout: Max wait time in seconds.

    Raises:
        WaitTimeoutError: If element doesn't become hidden within timeout.
    """
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _wait(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                element = DualLocator.resolve(driver, locator)
                if not _is_visible(driver, element):
                    return
            except Exception:
                # Element not found = hidden (success)
                return
            time.sleep(poll)

        raise WaitTimeoutError(
            condition=f"element {locator!r} hidden",
            timeout=timeout,
        )

    run_driver_action("wait_for_hidden", locator, _wait)


def wait_for_element(
    locator: str,
    timeout: float | None = None,
) -> None:
    """Wait for an element to exist in the DOM (not necessarily visible).

    Args:
        locator: Element locator.
        timeout: Max wait time in seconds.

    Raises:
        WaitTimeoutError: If element doesn't appear in DOM within timeout.
    """
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def _wait(driver: WebDriver) -> None:
        poll = config.waits.polling_interval
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                DualLocator.resolve(driver, locator)
                return  # Found in DOM
            except Exception:
                pass
            time.sleep(poll)

        raise WaitTimeoutError(
            condition=f"element {locator!r} exists in DOM",
            timeout=timeout,
        )

    run_driver_action("wait_for_element", locator, _wait)


def wait_until(
    condition: Callable[[], bool],
    description: str = "custom condition",
    timeout: float | None = None,
) -> None:
    """Wait for a custom condition to become True.

    Example::

        wait_until(lambda: get_url().endswith("/dashboard"), "on dashboard page")

    Args:
        condition: A callable returning True when the condition is met.
        description: Human-readable label for error messages.
        timeout: Max wait time in seconds.

    Raises:
        WaitTimeoutError: If condition isn't met within timeout.
    """
    WaitEngine.wait_for_condition(
        condition=condition,
        description=description,
        timeout=timeout,
    )


def wait_for_url(
    expected: str,
    timeout: float | None = None,
) -> None:
    """Wait for the current URL to contain the expected substring.

    Args:
        expected: Substring to wait for in the URL.
        timeout: Max wait time in seconds.

    Raises:
        WaitTimeoutError: If URL doesn't match within timeout.
    """
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def url_matches() -> bool:
        return expected in session_context.driver.current_url

    WaitEngine.wait_for_condition(
        condition=url_matches,
        description=f"URL contains {expected!r}",
        timeout=timeout,
    )


def wait_for_title(
    expected: str,
    timeout: float | None = None,
) -> None:
    """Wait for the page title to contain the expected substring.

    Args:
        expected: Substring to wait for in the title.
        timeout: Max wait time in seconds.

    Raises:
        WaitTimeoutError: If title doesn't match within timeout.
    """
    config = get_config()
    timeout = timeout or config.waits.default_element_timeout

    def title_matches() -> bool:
        return expected in session_context.driver.title

    WaitEngine.wait_for_condition(
        condition=title_matches,
        description=f"title contains {expected!r}",
        timeout=timeout,
    )
