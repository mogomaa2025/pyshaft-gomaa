"""PyShaft Test Data Decorators — Easy data-driven testing.

Usage:
    # Inline data as list of dicts
    @data([
        {"email": "admin@test.com", "password": "123"},
        {"email": "user@test.com", "password": "456"},
    ])
    def test_login(data):
        ...

    # From file
    @data_from("users.csv")
    def test_users(data):
        ...

    # With pytest.mark.parametrize style
    @data.parametrize(email=["a@test.com", "b@test.com"])
    def test_email(email):
        ...
"""

from __future__ import annotations

import csv
import json
import logging
import os
from typing import Any, Callable
from functools import wraps

logger = logging.getLogger("pyshaft.utils")


def data(test_data: list[dict] | dict, param_name: str = "data") -> Callable:
    """Decorator to run test with inline data.
    
    Usage:
        @data([
            {"email": "admin@test.com", "password": "123"},
            {"email": "user@test.com", "password": "456"},
        ])
        def test_login(data):
            api.post("/login").body(data)
        
        # Or use custom param name
        @data([{"name": "Alice"}], param_name="user")
        def test_user(user):
            api.post("/users").body(user)
    
    Args:
        test_data: List of dicts (runs once per item) or single dict (runs once)
        param_name: Name of parameter to pass to test function (default: "data")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Handle single dict vs list
            items = test_data if isinstance(test_data, list) else [test_data]
            
            for i, item in enumerate(items):
                logger.info(f"Running {func.__name__} with data {i+1}/{len(items)}: {item}")
                try:
                    func(*args, **{param_name: item}, **kwargs)
                except Exception as e:
                    logger.error(f"Test {func.__name__} failed on data {i+1}: {e}")
                    raise
        
        return wrapper
    return decorator


def data_from(path: str, key: str | None = None) -> Callable:
    """Decorator to run test with data from file (CSV or JSON).
    
    Usage:
        @data_from("tests/data/users.csv")
        def test_csv(data):
            api.post("/users").body(data)
        
        @data_from("tests/data/users.json", key="users")
        def test_json(data):
            api.post("/users").body(data)
    
    Args:
        path: Path to CSV or JSON file
        key: For JSON, which key to extract (e.g., "users" for {"users": [...]})
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Resolve file path
            file_path = path
            if not os.path.isabs(file_path):
                for p in [file_path, os.path.join(os.getcwd(), file_path)]:
                    if os.path.exists(p):
                        file_path = p
                        break
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Data file not found: {file_path}")
            
            # Load based on extension
            if file_path.endswith('.csv'):
                with open(file_path, 'r', newline='', encoding='utf-8') as f:
                    items = list(csv.DictReader(f))
            elif file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if key:
                    items = data.get(key, [])
                else:
                    items = data if isinstance(data, list) else [data]
            else:
                raise ValueError(f"Unsupported file type: {file_path}")
            
            if not items:
                logger.warning(f"No data found in: {file_path}")
                return
            
            for i, item in enumerate(items):
                logger.info(f"Running {func.__name__} with data {i+1}/{len(items)}: {item}")
                try:
                    func(*args, data=item, **kwargs)
                except Exception as e:
                    logger.error(f"Test {func.__name__} failed on data {i+1}: {e}")
                    raise
        
        return wrapper
    return decorator


class parametrize:
    """Pytest-like parametrize decorator for PyShaft.
    
    Usage:
        @parametrize("email", ["a@test.com", "b@test.com"])
        def test_email(email):
            api.post("/users").body({"email": email})
        
        @parametrize({"email": "a@test.com", "role": "admin"})
        def test_user(data):
            api.post("/users").body(data)
    """
    
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*func_args, **func_kwargs):
            # Build test data from arguments
            if self.args:
                # Positional: parametrize("field", [val1, val2])
                if len(self.args) != 2:
                    raise ValueError("@parametrize requires (field_name, values_list)")
                field_name, values = self.args
                items = [{field_name: v} for v in values]
            else:
                # Keyword: parametrize({"field": "value"}) or parametrize(field="value")
                # If dict passed as first kwarg value, use that
                items = []
                for k, v in self.kwargs.items():
                    if isinstance(v, list):
                        items = [{k: val} for val in v]
                    else:
                        items = [self.kwargs]
                if not items:
                    items = [self.kwargs]
            
            for i, item in enumerate(items):
                logger.info(f"Running {func.__name__} with param {i+1}/{len(items)}: {item}")
                try:
                    func(*func_args, **func_kwargs, **item)
                except Exception as e:
                    logger.error(f"Test {func.__name__} failed on param {i+1}: {e}")
                    raise
        
        return wrapper


__all__ = [
    'data',
    'data_from',
    'parametrize',
]