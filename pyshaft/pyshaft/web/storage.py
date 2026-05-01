"""PyShaft web storage — interact with localStorage and sessionStorage."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

from pyshaft.core.action_runner import run_driver_action

logger = logging.getLogger("pyshaft.web.storage")


def get_local_storage(key: str) -> Any:
    """Get a value from the browser's localStorage.

    Args:
        key: The key to retrieve.

    Returns:
        The value associated with the key, or None if not found.
    """
    def _get(driver: WebDriver) -> Any:
        return driver.execute_script("return window.localStorage.getItem(arguments[0]);", key)

    return run_driver_action("get_local_storage", f"key: {key}", _get)


def set_local_storage(key: str, value: str) -> None:
    """Set a value in the browser's localStorage.

    Args:
        key: The key to set.
        value: The value to store.
    """
    def _set(driver: WebDriver) -> None:
        driver.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", key, value)

    run_driver_action("set_local_storage", f"key: {key}", _set)


def clear_local_storage() -> None:
    """Clear all entries in the browser's localStorage."""
    def _clear(driver: WebDriver) -> None:
        driver.execute_script("window.localStorage.clear();")

    run_driver_action("clear_local_storage", "localStorage", _clear)


def get_session_storage(key: str) -> Any:
    """Get a value from the browser's sessionStorage.

    Args:
        key: The key to retrieve.

    Returns:
        The value associated with the key, or None if not found.
    """
    def _get(driver: WebDriver) -> Any:
        return driver.execute_script("return window.sessionStorage.getItem(arguments[0]);", key)

    return run_driver_action("get_session_storage", f"key: {key}", _get)


def set_session_storage(key: str, value: str) -> None:
    """Set a value in the browser's sessionStorage.

    Args:
        key: The key to set.
        value: The value to store.
    """
    def _set(driver: WebDriver) -> None:
        driver.execute_script("window.sessionStorage.setItem(arguments[0], arguments[1]);", key, value)

    run_driver_action("set_session_storage", f"key: {key}", _set)


def clear_session_storage() -> None:
    """Clear all entries in the browser's sessionStorage."""
    def _clear(driver: WebDriver) -> None:
        driver.execute_script("window.sessionStorage.clear();")

    run_driver_action("clear_session_storage", "sessionStorage", _clear)


def get_cookies() -> list[dict]:
    """Get all browser cookies."""
    from pyshaft.session import session_context
    return session_context.driver.get_cookies()


def add_cookie(cookie_dict: dict) -> None:
    """Add a cookie to the current session."""
    def _add(driver: WebDriver) -> None:
        driver.add_cookie(cookie_dict)

    run_driver_action("add_cookie", str(cookie_dict), _add)


def delete_cookie(name: str) -> None:
    """Delete a specific cookie by name."""
    def _delete(driver: WebDriver) -> None:
        driver.delete_cookie(name)

    run_driver_action("delete_cookie", name, _delete)


def clear_cookies() -> None:
    """Delete all cookies from the current session."""
    def _clear(driver: WebDriver) -> None:
        driver.delete_all_cookies()

    run_driver_action("clear_cookies", "all cookies", _clear)


def save_cookies(file_path: str) -> None:
    """Save current session cookies to a JSON file."""
    import json
    cookies = get_cookies()
    with open(file_path, "w") as f:
        json.dump(cookies, f)
    logger.info("Cookies saved to %s", file_path)


def load_cookies(file_path: str) -> None:
    """Load cookies from a JSON file and add them to the current session."""
    import json
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cookie file not found: {file_path}")
    
    with open(file_path, "r") as f:
        cookies = json.load(f)
        
    for cookie in cookies:
        add_cookie(cookie)
    logger.info("Cookies loaded from %s", file_path)
