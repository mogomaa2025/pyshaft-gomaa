"""PyShaft web tables — helper functions for interacting with HTML tables."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selenium.webdriver.remote.webelement import WebElement

from selenium.webdriver.common.by import By
from pyshaft.core.locator import DualLocator
from pyshaft.core.action_runner import run_driver_action
from pyshaft.session import session_context

logger = logging.getLogger("pyshaft.web.tables")


def get_table_rows(locator: str) -> int:
    """Get the number of rows in a table.

    Args:
        locator: Locator for the <table> element.

    Returns:
        Number of <tr> elements in the table.
    """
    driver = session_context.driver
    table = DualLocator.resolve(driver, locator)
    rows = table.find_elements(By.TAG_NAME, "tr")
    return len(rows)


def get_table_cell(locator: str, row: int, col: int) -> str:
    """Get the text content of a specific table cell.

    Args:
        locator: Locator for the <table> element.
        row: 1-indexed row number.
        col: 1-indexed column number.

    Returns:
        Text content of the cell.
    """
    driver = session_context.driver
    table = DualLocator.resolve(driver, locator)
    
    # 1-indexed to 0-indexed
    rows = table.find_elements(By.TAG_NAME, "tr")
    if row > len(rows):
        raise IndexError(f"Table {locator!r} only has {len(rows)} rows, but row {row} requested")
    
    target_row = rows[row - 1]
    cells = target_row.find_elements(By.XPATH, "./td | ./th")
    if col > len(cells):
        raise IndexError(f"Row {row} of table {locator!r} only has {len(cells)} columns, but column {col} requested")
        
    return cells[col - 1].text


def get_table_column(locator: str, col: int) -> list[str]:
    """Get the text contents of an entire table column.

    Args:
        locator: Locator for the <table> element.
        col: 1-indexed column number.

    Returns:
        List of strings from the requested column.
    """
    driver = session_context.driver
    table = DualLocator.resolve(driver, locator)
    
    rows = table.find_elements(By.TAG_NAME, "tr")
    column_data = []
    
    for r in rows:
        cells = r.find_elements(By.XPATH, "./td | ./th")
        if len(cells) >= col:
            column_data.append(cells[col - 1].text)
            
    return column_data


def assert_table_cell(locator: str, row: int, col: int, expected: str) -> None:
    """Assert that a table cell contains the expected text.

    Args:
        locator: Locator for the <table> element.
        row: 1-indexed row number.
        col: 1-indexed column number.
        expected: Expected text content.
    """
    def _assert(driver):
        actual = get_table_cell(locator, row, col)
        if expected not in actual:
            raise AssertionError(f"Table {locator!r} row {row} col {col}: expected {expected!r} to be in {actual!r}")

    run_driver_action("assert_table_cell", f"table {locator} row {row} col {col} contains {expected}", _assert)
