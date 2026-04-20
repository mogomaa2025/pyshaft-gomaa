"""PyShaft utilities — data-driven testing and retry decorators.

These utilities help manual testers write less code:
    - @data_from() - Run tests with data from CSV/JSON
    - @retry() - Retry failed tests
    - @tag() - Tag tests for filtering
"""

from __future__ import annotations

import csv
import json
import logging
import os
from typing import Any, Callable
from functools import wraps

logger = logging.getLogger("pyshaft.utils")

# -------------------------------------------------------------------------
# Data-Driven Decorator
# -------------------------------------------------------------------------


def data_from_csv(file_path: str) -> Callable:
    """Decorator to run a test function with data from a CSV file.
    
    Each row in the CSV becomes a separate test run.
    
    Args:
        file_path: Path to CSV file (relative or absolute)
        
    Example:
        @data_from_csv("test_data/users.csv")
        def test_login(data):
            w.type(data["email"], role, textbox)
            w.type(data["password"], role, password)
            w.click(role, button)
            
        # users.csv:
        # email,password
        # admin@example.com,secret123
        # user@example.com,pass456
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Resolve file path
            if not os.path.isabs(file_path):
                # Try relative to current file or cwd
                for path in [file_path, os.path.join(os.getcwd(), file_path)]:
                    if os.path.exists(path):
                        file_path = path
                        break
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"CSV file not found: {file_path}")
            
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            if not rows:
                logger.warning(f"No data rows found in CSV: {file_path}")
                return
            
            # Run test for each row
            for i, row in enumerate(rows):
                logger.info(f"Running {func.__name__} with data row {i+1}/{len(rows)}: {row}")
                try:
                    func(*args, data=row, **kwargs)
                except Exception as e:
                    logger.error(f"Test {func.__name__} failed on row {i+1}: {e}")
                    raise
        
        return wrapper
    return decorator


def data_from_json(file_path: str, key: str | None = None) -> Callable:
    """Decorator to run a test function with data from a JSON file.
    
    If key is provided, use that array from JSON.
    Otherwise, use the entire JSON (if it's an array) or wrap it.
    
    Args:
        file_path: Path to JSON file
        key: Optional key to extract from JSON (e.g., "users" for {"users": [...]})
        
    Example:
        @data_from_json("test_data/users.json", key="users")
        def test_login(data):
            w.type(data["email"], role, textbox)
            w.type(data["password"], role, password)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Resolve file path
            if not os.path.isabs(file_path):
                for path in [file_path, os.path.join(os.getcwd(), file_path)]:
                    if os.path.exists(path):
                        file_path = path
                        break
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"JSON file not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract data based on key
            if key:
                if key not in data:
                    raise KeyError(f"Key '{key}' not found in JSON: {file_path}")
                items = data[key]
            else:
                # Use as-is if it's a list, otherwise wrap
                items = data if isinstance(data, list) else [data]
            
            if not items:
                logger.warning(f"No data found in JSON: {file_path}")
                return
            
            # Run test for each item
            for i, item in enumerate(items):
                logger.info(f"Running {func.__name__} with data item {i+1}/{len(items)}: {item}")
                try:
                    func(*args, data=item, **kwargs)
                except Exception as e:
                    logger.error(f"Test {func.__name__} failed on item {i+1}: {e}")
                    raise
        
        return wrapper
    return decorator


# -------------------------------------------------------------------------
# Retry Decorator for Test Functions
# -------------------------------------------------------------------------


def retry(
    max_attempts: int = 3,
    backoff: float = 1.5,
    exceptions: tuple = (Exception,),
) -> Callable:
    """Decorator to retry a test function on failure.
    
    Useful for flaky tests that might fail due to timing issues.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff: Multiplier for wait time between retries
        exceptions: Tuple of exceptions to catch and retry
        
    Example:
        @retry(max_attempts=3, backoff=2.0)
        def test_flaky():
            w.click(role, button)
            w.assert_text("Success", role, heading)
    """
    def decorator(func: Callable) -> Callable:
        import time
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = backoff ** attempt
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        time.sleep(wait_time)
            
            # All attempts failed
            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_exception
        
        return wrapper
    return decorator


# -------------------------------------------------------------------------
# Tag Decorator for Test Filtering
# -------------------------------------------------------------------------


def tag(*tags: str) -> Callable:
    """Decorator to add tags to a test function.
    
    Use with pytest to run specific groups:
        pytest -m "smoke"          # Run only smoke tests
        pytest -m "not slow"       # Exclude slow tests
        pytest -m "smoke and api"  # Run tests with both tags
        
    Args:
        *tags: Tag names (e.g., "smoke", "regression", "slow")
        
    Example:
        @tag("smoke", "regression")
        def test_login():
            w.open_url("/login")
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Store tags as an attribute (pytest-marks compatible)
        func.pytestmark = getattr(func, 'pytestmark', [])
        if not isinstance(func.pytestmark, list):
            func.pytestmark = [func.pytestmark] if func.pytestmark else []
        
        # Add pytest.mark with tags
        import pytest
        for tag_name in tags:
            func = pytest.mark.tag(tag_name)(func)
        
        return func
    return decorator


# -------------------------------------------------------------------------
# Convenience aliases
# -------------------------------------------------------------------------

#: Alias for @data_from_csv
data_from = data_from_csv

#: Alias for @retry  
retry_on_exception = retry

__all__ = [
    "data_from_csv",
    "data_from_json",
    "data_from",
    "retry",
    "retry_on_exception",
    "tag",
]