"""PyShaft Data Pipeline - Easy data flow between tests.

Usage:
    @extract("$.data.id", "wharf_id")   # Extract and store
    def test_create(): ...

    @use_stored("wharf_id")             # Use stored value in body
    def test_use():
        api.post("/berths").body({"wharfId": "{{wharf_id}}"})

Or use the simpler approach:
    # In test 1
    api.post("/wharfs").extract("id", "wharf_id")
    
    # In test 2  
    use stored value directly with api.fill()
"""

from typing import Any, Callable
from functools import wraps


def extract(path: str, key: str):
    """Decorator that extracts JSON path value after request and stores it.
    
    Usage:
        @extract("$.data.id", "wharf_id")
        def test_create():
            api.post("/wharfs").body({...})
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # Try to get the last response and extract
            from pyshaft.api import api
            if hasattr(result, 'extract_json'):
                result.extract_json(path, key)
            return result
        return wrapper
    return decorator


def use_stored(key: str):
    """Decorator that ensures stored value exists before test runs.
    
    Usage:
        @use_stored("wharf_id")
        def test_use():
            api.get(f"/wharfs/{{wharf_id}}")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from pyshaft.api import api
            try:
                api.stored(key)
            except KeyError:
                raise RuntimeError(
                    f"Test requires stored key '{key}' but it's not found. "
                    f"Make sure a previous test runs first that extracts this value."
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


class DataPipeline:
    """Simple class to chain data between tests within same test file.
    
    Usage:
        dp = DataPipeline()
        
        # In first test
        dp.create("wharf", api.post("/wharfs").body({...}).extract("$.data.id"))
        
        # In second test
        dp.get("wharf")  # Returns the stored wharf ID
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {}
        return cls._instance
    
    def set(self, key: str, value: Any) -> None:
        """Store value in memory (cleared after test session)."""
        self._data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get stored value."""
        return self._data.get(key, default)
    
    def clear(self) -> None:
        """Clear all stored data."""
        self._data.clear()
    
    def __repr__(self) -> str:
        return f"DataPipeline({self._data})"


# Convenience functions
pipeline = DataPipeline()


def store_value(key: str, value: Any) -> None:
    """Store a value in both memory and file (for cross-test sharing)."""
    pipeline.set(key, value)
    # Also save to file for persistence across pytest sessions
    from pyshaft.api.store import store_data
    store_data(key, value)


def get_value(key: str, default: Any = None) -> Any:
    """Get a stored value from memory or file.
    
    Checks:
    1. In-memory pipeline (set via store_value())
    2. File store (set via api.extract_json())
    """
    # First check memory
    val = pipeline.get(key)
    if val is not None:
        return val
    
    # Fall back to file store
    from pyshaft.api.store import get_stored
    try:
        return get_stored(key)
    except KeyError:
        return default


def chain_test(key: str, json_path: str):
    """Decorator to chain test data - extract and store in one step.
    
    Usage:
        @chain_test("wharf_id", "$.data.id")
        def test_create():
            return api.post("/wharfs").body({...})
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from pyshaft.api import api
            # Get current builder if exists
            builder = api._current_builder if hasattr(api, '_current_builder') else None
            
            result = func(*args, **kwargs)
            
            # If result is ApiEngine chain, trigger extract
            if hasattr(result, 'extract_json'):
                result.extract_json(json_path, key)
            
            # Also store in pipeline
            try:
                pipeline.set(key, api.stored(key))
            except:
                pass
            
            return result
        return wrapper
    return decorator


__all__ = [
    'extract',
    'use_stored',
    'DataPipeline',
    'pipeline',
    'store_value',
    'get_value',
    'chain_test',
]