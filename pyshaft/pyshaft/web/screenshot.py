"""PyShaft web screenshot — capture browser and element screenshots."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement

from pyshaft.core.action_runner import run_action, run_driver_action

logger = logging.getLogger("pyshaft.web.screenshot")


def take_screenshot(path: str | None = None) -> str:
    """Capture a screenshot of the entire browser viewport.

    Args:
        path: Optional file path. If None, saves to pyshaft-report/screenshot_<timestamp>.png.

    Returns:
        The absolute path to the saved screenshot.
    """
    def _take(driver: WebDriver) -> str:
        nonlocal path
        if not path:
            report_dir = Path("pyshaft-report")
            report_dir.mkdir(exist_ok=True)
            timestamp = int(time.time())
            path = str(report_dir / f"screenshot_{timestamp}.png")
        
        path_obj = Path(path).absolute()
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        driver.save_screenshot(str(path_obj))
        logger.info("Screenshot saved to: %s", path_obj)
        return str(path_obj)

    return run_driver_action("take_screenshot", "browser viewport", _take)


def take_element_screenshot(locator: str, path: str | None = None, name: str | None = None) -> str:
    """Capture a screenshot of a specific element.

    Args:
        locator: Locator for the target element.
        path: Optional full file path.
        name: Optional simple name (saved to saved_snapshots/<name>.png).

    Returns:
        The absolute path to the saved screenshot.
    """
    def _take(element: WebElement) -> str:
        nonlocal path
        if name:
            base_dir = Path("saved_snapshots")
            base_dir.mkdir(exist_ok=True)
            path = str(base_dir / f"{name}.png")
            
        if not path:
            report_dir = Path("pyshaft-report")
            report_dir.mkdir(exist_ok=True)
            timestamp = int(time.time())
            path = str(report_dir / f"element_{timestamp}.png")
            
        path_obj = Path(path).absolute()
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        element.screenshot(str(path_obj))
        logger.info("Element screenshot saved to: %s", path_obj)
        return str(path_obj)

    return run_action("take_element_screenshot", locator, _take)
