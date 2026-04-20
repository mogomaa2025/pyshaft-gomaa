"""PyShaft ActionRunner — the locate → wait → execute → log pipeline.

Every web action (click, type, assert) goes through this pipeline to ensure
consistent auto-wait behavior, step logging, and error handling.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from pyshaft.config import get_config
from pyshaft.core.locator import DualLocator
from pyshaft.core.step_logger import step_logger
from pyshaft.core.wait_engine import WaitEngine
from pyshaft.exceptions import ElementNotInteractableError, WaitTimeoutError
from pyshaft.session import session_context

logger = logging.getLogger("pyshaft.core.action_runner")


def run_action(
    action_name: str,
    locator: str,
    action_fn: Callable[[WebElement], Any],
    require_interactable: bool = True,
) -> Any:
    """Execute a web action with built-in retries and reliability.

    Pipeline:
        1. Resolve locator
        2. Wait for readiness
        3. Execute action
        4. Handle StaleElementReferenceException by re-resolving
        5. Handle ClickIntercepted by re-waiting or JS fallback
    """
    config = get_config()
    driver = session_context.driver
    start = time.time()
    timeout = config.waits.default_element_timeout
    deadline = start + timeout
    
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            # 1. Resolve & Wait
            element = DualLocator.resolve(driver, locator)
            if require_interactable and config.waits.respect_native_waits:
                element = WaitEngine.wait_for_element(driver, element)

            # 2. Execute
            try:
                result = action_fn(element)
                
                # Log success
                _record_step(action_name, locator, start, "pass")
                return result

            except (ElementClickInterceptedException, ElementNotInteractableException) as e:
                if config.actions.js_click_fallback and action_name == "click":
                    logger.info("WebDriver click failed, using JS fallback")
                    _js_click(driver, element)
                    _record_step(action_name, locator, start, "pass")
                    return None
                last_error = e
                time.sleep(config.waits.polling_interval)
                continue

        except (StaleElementReferenceException, WaitTimeoutError) as e:
            last_error = e
            logger.debug("Action %s failed with %s, retrying...", action_name, type(e).__name__)
            time.sleep(config.waits.polling_interval)
            continue
        
        except Exception as e:
            _record_step(action_name, locator, start, "fail", str(e))
            raise

    # If we reached here, we timed out
    _record_step(action_name, locator, start, "fail", str(last_error))
    raise last_error or TimeoutError(f"Action {action_name} on {locator!r} timed out")


def run_driver_action(
    action_name: str,
    description: str,
    action_fn: Callable[[WebDriver], Any],
) -> Any:
    """Execute a driver-level action."""
    driver = session_context.driver
    start = time.time()

    try:
        result = action_fn(driver)
        _record_step(action_name, description, start, "pass")
        return result

    except Exception as e:
        _record_step(action_name, description, start, "fail", str(e))
        raise


def _record_step(action: str, locator: str, start_time: float, status: str, error: str | None = None):
    duration_ms = (time.time() - start_time) * 1000
    config = get_config()
    
    screenshot_path = None
    if config.report.screenshot_on_step or (status == "fail" and config.report.screenshot_on_fail):
        try:
            from pyshaft.web.screenshot import take_screenshot
            # take_screenshot handles output dir and timestamp
            screenshot_path = take_screenshot()
        except Exception as e:
            logger.warning("Failed to capture automatic screenshot for step: %s", e)

    step_logger.record(
        action=action,
        locator=locator,
        duration_ms=duration_ms,
        status=status,
        screenshot=screenshot_path,
        error=error,
    )


def _js_click(driver: WebDriver, element: WebElement) -> None:
    driver.execute_script("arguments[0].click();", element)
