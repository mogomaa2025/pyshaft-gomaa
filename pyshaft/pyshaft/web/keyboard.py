"""PyShaft web keyboard — perform keyboard interactions and shortcuts."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from pyshaft.core.action_runner import run_driver_action

logger = logging.getLogger("pyshaft.web.keyboard")


def hotkey(*keys: str) -> None:
    """Perform a keyboard shortcut (e.g., Ctrl+C).

    Args:
        *keys: Key names as strings (e.g., "control", "c").
    """
    def _hotkey(driver: WebDriver) -> None:
        actions = ActionChains(driver)
        
        # Convert string names to Selenium Keys if possible
        mapped_keys = []
        for k in keys:
            k_upper = k.upper()
            if hasattr(Keys, k_upper):
                mapped_keys.append(getattr(Keys, k_upper))
            else:
                mapped_keys.append(k)

        # Press all keys down
        for k in mapped_keys:
            actions.key_down(k)
        
        # Release all keys up in reverse order
        for k in reversed(mapped_keys):
            actions.key_up(k)
            
        actions.perform()

    run_driver_action("hotkey", f"keys: {'+'.join(keys)}", _hotkey)


def global_press(key: str) -> None:
    """Press a single key globally (not targeted at an element).

    Args:
        key: The key name to press.
    """
    def _press(driver: WebDriver) -> None:
        actions = ActionChains(driver)
        
        k_upper = key.upper()
        mapped_key = getattr(Keys, k_upper) if hasattr(Keys, k_upper) else key
        
        actions.send_keys(mapped_key).perform()

    run_driver_action("global_press", f"key: {key}", _press)
