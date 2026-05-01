"""PyShaft web navigation — open_url, go_back, go_forward, refresh, get_url, get_title, window/frame switching, and scrolling."""

from __future__ import annotations

import logging

from selenium.webdriver.remote.webdriver import WebDriver

from pyshaft.config import get_config
from pyshaft.core.action_runner import run_driver_action
from pyshaft.core.wait_engine import WaitEngine
from pyshaft.exceptions import NavigationError
from pyshaft.session import session_context

logger = logging.getLogger("pyshaft.web.navigation")


def open_url(url: str) -> None:
    """Navigate to a URL."""
    config = get_config()
    full_url = _resolve_url(url, config.browser.base_url)

    def _navigate(driver: WebDriver) -> None:
        driver.get(full_url)
        if config.waits.respect_native_waits:
            WaitEngine.wait_for_page_load(driver)
        if config.validations.force_navigation_check:
            _verify_navigation(driver, full_url)

    run_driver_action("open_url", full_url, _navigate)


def go_back() -> None:
    """Navigate back in browser history."""
    run_driver_action("go_back", "browser back", lambda d: d.back())


def go_forward() -> None:
    """Navigate forward in browser history."""
    run_driver_action("go_forward", "browser forward", lambda d: d.forward())


def refresh() -> None:
    """Refresh the current page."""
    def _refresh(driver: WebDriver) -> None:
        driver.refresh()
        config = get_config()
        if config.waits.respect_native_waits:
            WaitEngine.wait_for_page_load(driver)

    run_driver_action("refresh", "page refresh", _refresh)


def get_url() -> str:
    """Get the current page URL."""
    return session_context.driver.current_url


def get_title() -> str:
    """Get the current page title."""
    return session_context.driver.title


def close_window() -> None:
    """Close the current browser window/tab."""
    run_driver_action("close_window", "current window", lambda d: d.close())


def open_new_window(switch_to: bool = True) -> None:
    """Open a new browser window/tab."""
    def _open(driver: WebDriver) -> None:
        driver.execute_script("window.open('');")
        if switch_to:
            driver.switch_to.window(driver.window_handles[-1])

    run_driver_action("open_new_window", "new window", _open)


def switch_to_window(handle_or_index: str | int) -> None:
    """Switch focus to a different browser window/tab."""
    def _switch(driver: WebDriver) -> None:
        if isinstance(handle_or_index, int):
            handles = driver.window_handles
            driver.switch_to.window(handles[handle_or_index])
        else:
            driver.switch_to.window(handle_or_index)

    run_driver_action("switch_to_window", str(handle_or_index), _switch)


def switch_to_newest_window() -> None:
    """Switch focus to the most recently opened window/tab."""
    run_driver_action("switch_to_newest_window", "newest window", lambda d: d.switch_to.window(d.window_handles[-1]))


def switch_to_frame(locator: str | int) -> None:
    """Switch focus to a frame (iframe)."""
    def _switch(driver: WebDriver) -> None:
        if isinstance(locator, int):
            driver.switch_to.frame(locator)
        else:
            from pyshaft.core.locator import DualLocator
            element = DualLocator.resolve(driver, locator)
            driver.switch_to.frame(element)

    run_driver_action("switch_to_frame", str(locator), _switch)


def switch_to_parent_frame() -> None:
    """Switch focus back to the parent frame."""
    run_driver_action("switch_to_parent_frame", "parent frame", lambda d: d.switch_to.parent_frame())


def switch_to_default_content() -> None:
    """Switch focus back to the main document/top-level frame."""
    run_driver_action("switch_to_default_content", "top frame", lambda d: d.switch_to.default_content())


def scroll(x: int = 0, y: int = 0) -> None:
    """Scroll the window by pixel offset."""
    run_driver_action("scroll", f"window scroll ({x}, {y})", lambda d: d.execute_script(f"window.scrollBy({x}, {y})"))


def scroll_to_bottom() -> None:
    """Scroll to the bottom of the page."""
    run_driver_action("scroll_to_bottom", "window scroll to bottom", lambda d: d.execute_script("window.scrollTo(0, document.body.scrollHeight)"))


def scroll_to_top() -> None:
    """Scroll to the top of the page."""
    run_driver_action("scroll_to_top", "window scroll to top", lambda d: d.execute_script("window.scrollTo(0, 0)"))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_url(url: str, base_url: str) -> str:
    """Prepend base_url if the URL is relative."""
    if not url:
        return base_url or ""
    if url.startswith(("http://", "https://", "file://", "data:", "about:")):
        return url
    if base_url:
        base = base_url.rstrip("/")
        path = url.lstrip("/")
        return f"{base}/{path}"
    return url


def _verify_navigation(driver: WebDriver, expected_url: str) -> None:
    """Verify that navigation succeeded."""
    ready_state = driver.execute_script("return document.readyState")
    if ready_state != "complete":
        raise NavigationError(url=expected_url, reason=f"readyState is '{ready_state}'")
    
    current_url = driver.current_url
    error_indicators = ["ERR_", "about:neterror", "chrome-error://"]
    if any(indicator in current_url for indicator in error_indicators):
        raise NavigationError(url=expected_url, reason=f"Browser error page: {current_url}")
