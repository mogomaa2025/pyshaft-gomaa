"""PyShaft web collections — interact with multiple elements simultaneously."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selenium.webdriver.remote.webelement import WebElement

from pyshaft.core.locator import DualLocator
from pyshaft.session import session_context

logger = logging.getLogger("pyshaft.web.collections")


def count(locator: str) -> int:
    """Count the number of elements matching the locator.

    Returns:
        Number of matching elements.
    """
    elements = DualLocator.resolve_all(session_context.driver, locator)
    return len(elements)


def get_all(locator: str) -> list[WebElement]:
    """Get all elements matching the locator.

    Returns:
        List of matching WebElements.
    """
    return DualLocator.resolve_all(session_context.driver, locator)


def get_all_text(locator: str) -> list[str]:
    """Get text contents of all elements matching the locator.

    Returns:
        List of strings containing text from each element.
    """
    elements = DualLocator.resolve_all(session_context.driver, locator)
    return [el.text for el in elements]


def first(locator: str) -> WebElement:
    """Get the first element matching the locator.

    Returns:
        The first matching WebElement.
    """
    elements = DualLocator.resolve_all(session_context.driver, locator)
    if not elements:
        # Trigger standard error handling via resolve()
        return DualLocator.resolve(session_context.driver, locator)
    return elements[0]


def last(locator: str) -> WebElement:
    """Get the last element matching the locator.

    Returns:
        The last matching WebElement.
    """
    elements = DualLocator.resolve_all(session_context.driver, locator)
    if not elements:
        return DualLocator.resolve(session_context.driver, locator)
    return elements[-1]


def nth(locator: str, index: int) -> WebElement:
    """Get the Nth element matching the locator.

    Args:
        locator: Locator description.
        index: 0-based index of the desired element.

    Returns:
        The Nth matching WebElement.
    """
    elements = DualLocator.resolve_all(session_context.driver, locator)
    if not elements:
        return DualLocator.resolve(session_context.driver, locator)
    try:
        return elements[index]
    except IndexError:
        logger.error("Index %d out of bounds for collection %r (size: %d)", index, locator, len(elements))
        raise
