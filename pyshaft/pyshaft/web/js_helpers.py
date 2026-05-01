"""PyShaft web JavaScript helpers — interact with the page via JS execution."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement

from pyshaft.core.action_runner import run_action, run_driver_action

logger = logging.getLogger("pyshaft.web.js_helpers")


def execute_js(script: str, *args: Any) -> Any:
    """Execute custom JavaScript on the current page.

    Args:
        script: The JS code to run.
        *args: Arguments to pass to the script (accessible via arguments[0], etc.).

    Returns:
        The return value of the JS execution.
    """
    def _execute(driver: WebDriver) -> Any:
        return driver.execute_script(script, *args)

    return run_driver_action("execute_js", "custom script", _execute)


def highlight_element(locator: str, color: str = "red", duration: float = 2.0) -> None:
    """Highlight an element by changing its border color temporarily.

    Args:
        locator: Locator for the element to highlight.
        color: CSS color string for the border.
        duration: How long to keep the highlight (seconds).
    """
    def _highlight(element: WebElement) -> None:
        driver = element.parent
        original_style = element.get_attribute("style")
        
        # Apply highlight
        driver.execute_script(
            f"arguments[0].style.border = '3px solid {color}'; "
            f"arguments[0].style.boxShadow = '0 0 10px {color}';",
            element
        )
        
        # Wait and revert
        time.sleep(duration)
        driver.execute_script("arguments[0].setAttribute('style', arguments[1]);", element, original_style)

    run_action("highlight_element", locator, _highlight)

def remove_element(locator: str) -> None:
    """Remove an element from the DOM via JavaScript.

    Args:
        locator: Locator for the target element to remove.
    """
    def _remove(element: WebElement) -> None:
        element.parent.execute_script("arguments[0].remove();", element)

    run_action("remove_element", locator, _remove)


def remove_elements(locator: str) -> None:
    """Remove all elements matching the locator from the DOM via JavaScript.

    Args:
        locator: Locator for the target elements to remove.
    """
    def _remove_all(driver: WebDriver) -> None:
        from pyshaft.core.locator import DualLocator

        elements = DualLocator.resolve_all(driver, locator)
        for el in elements:
            driver.execute_script("arguments[0].remove();", el)

    run_driver_action("remove_elements", locator, _remove_all)


def set_value_js(locator: str, value: str) -> None:
    """Set an element's value property directly via JavaScript.

    Useful for elements that are difficult to type into normally.

    Args:
        locator: Locator for the target element.
        value: The value to set.
    """
    def _set(element: WebElement) -> None:
        element.parent.execute_script("arguments[0].value = arguments[1];", element, value)

    run_action("set_value_js", locator, _set)


def scroll_into_view(locator: str) -> None:
    """Scroll the page until the specified element is in view.

    Args:
        locator: Locator for the target element.
    """
    def _scroll(element: WebElement) -> None:
        element.parent.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

    run_action("scroll_into_view", locator, _scroll)


def ad_block() -> None:
    """Block common advertisement elements from loading on the page."""
    ad_selectors = [
        '[aria-label="Ads"]',
        '[src*="adservice."]',
        '[src*="doubleclick"]',
        '[class*="sponsored-content"]',
        '[class*="adsbygoogle"]',
        'iframe[src*="doubleclick"]',
        '[id*="-ad-"]',
        '[id*="_ads_"]',
        "ins.adsby",
    ]
    for selector in ad_selectors:
        remove_elements(selector)
    logger.info("Ad blocking applied to the current page.")
