"""PyShaft web interactions — click, double_click, right_click, hover, drag_to, and click_all.

Phase 4: full interaction suite.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement

from pyshaft.core.action_runner import run_action, run_driver_action
from pyshaft.core.locator import DualLocator
from pyshaft.session import session_context

if TYPE_CHECKING:
    from pyshaft.web.locators import Locator

logger = logging.getLogger("pyshaft.web.interactions")


def click(locator: str | Locator, amount: int = 1) -> Any:
    """Click an element."""
    target = locator._get_final_selector() if hasattr(locator, "_get_final_selector") else str(locator)
    
    def _click(element: WebElement) -> None:
        for i in range(amount):
            element.click()
            if amount > 1 and i < amount - 1:
                time.sleep(0.1)

    run_action("click", target, _click)


def click_all(locator: str | Locator) -> Any:
    """Click all elements matching the locator."""
    target = locator._get_final_selector() if hasattr(locator, "_get_final_selector") else str(locator)
    
    def _click_all(driver):
        elements = DualLocator.resolve_all(driver, target)
        for el in elements:
            el.click()

    run_driver_action("click_all", target, _click_all)


def double_click(locator: str | Locator) -> Any:
    """Double-click an element."""
    target = locator._get_final_selector() if hasattr(locator, "_get_final_selector") else str(locator)
    
    def _double_click(element: WebElement) -> None:
        actions = ActionChains(session_context.driver)
        actions.double_click(element).perform()

    run_action("double_click", target, _double_click)


def right_click(locator: str | Locator) -> Any:
    """Right-click an element."""
    target = locator._get_final_selector() if hasattr(locator, "_get_final_selector") else str(locator)
    
    def _right_click(element: WebElement) -> None:
        actions = ActionChains(session_context.driver)
        actions.context_click(element).perform()

    run_action("right_click", target, _right_click)


def hover(locator: str | Locator) -> Any:
    """Hover over an element."""
    target = locator._get_final_selector() if hasattr(locator, "_get_final_selector") else str(locator)
    
    def _hover(element: WebElement) -> None:
        actions = ActionChains(session_context.driver)
        actions.move_to_element(element).perform()

    run_action("hover", target, _hover, require_interactable=False)


def drag_to(source: str | Locator, target: str | Locator) -> Any:
    """Drag source to target."""
    src_sel = source._get_final_selector() if hasattr(source, "_get_final_selector") else str(source)
    tgt_sel = target._get_final_selector() if hasattr(target, "_get_final_selector") else str(target)
    
    def _drag(driver):
        s_el = DualLocator.resolve(driver, src_sel)
        t_el = DualLocator.resolve(driver, tgt_sel)
        actions = ActionChains(driver)
        actions.drag_and_drop(s_el, t_el).perform()

    run_driver_action("drag_to", f"{src_sel} -> {tgt_sel}", _drag)
