"""PyShaft web alerts — accept, dismiss, and interact with browser alerts."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

from pyshaft.core.action_runner import run_driver_action

logger = logging.getLogger("pyshaft.web.alerts")


def accept_alert() -> None:
    """Accept (click OK/Yes) on the current browser alert."""
    def _accept(driver: WebDriver) -> None:
        alert = driver.switch_to.alert
        alert.accept()

    run_driver_action("accept_alert", "browser alert", _accept)


def dismiss_alert() -> None:
    """Dismiss (click Cancel/No) on the current browser alert."""
    def _dismiss(driver: WebDriver) -> None:
        alert = driver.switch_to.alert
        alert.dismiss()

    run_driver_action("dismiss_alert", "browser alert", _dismiss)


def get_alert_text() -> str:
    """Get the text message showing on the current browser alert.

    Returns:
        The alert message text.
    """
    def _get_text(driver: WebDriver) -> str:
        alert = driver.switch_to.alert
        return alert.text

    # run_driver_action returns the result of action_fn
    return run_driver_action("get_alert_text", "browser alert", _get_text)


def type_alert(text: str) -> None:
    """Type text into a browser prompt alert.

    Args:
        text: The text to type into the prompt.
    """
    def _type(driver: WebDriver) -> None:
        alert = driver.switch_to.alert
        alert.send_keys(text)

    run_driver_action("type_alert", f"browser alert: {text}", _type)
