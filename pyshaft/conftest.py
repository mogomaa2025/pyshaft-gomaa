"""PyShaft pytest configuration and fixtures.

This file auto-imports all PyShaft fixtures for use in tests.
Place this in tests/ or the root directory.
"""

# Import all fixtures so pytest can discover them
from pyshaft.fixtures import (
    data_dir,
    test_data_manager,
    test_data,
    load_data,
    test_env,
    api_client,
    store,
    browser,
    web,
    test_name,
    test_info,
)

__all__ = [
    "data_dir",
    "test_data_manager",
    "test_data",
    "load_data",
    "test_env",
    "api_client",
    "store",
    "browser",
    "web",
    "test_name",
    "test_info",
]