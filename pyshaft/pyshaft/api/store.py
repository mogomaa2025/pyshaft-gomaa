"""PyShaft API data store — persistent memory for sharing data between requests and individual runs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Path to the persistent storage file
STORE_FILE = Path(".pyshaft_store.json")

def _load_store() -> dict[str, Any]:
    """Load data from the persistent file."""
    if not STORE_FILE.exists():
        return {}
    try:
        with open(STORE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def _save_store(data: dict[str, Any]) -> None:
    """Save data to the persistent file."""
    try:
        with open(STORE_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except IOError:
        pass

def store_data(key: str, value: Any) -> None:
    """Store data in persistent memory."""
    data = _load_store()
    data[key] = value
    _save_store(data)

def get_stored(key: str) -> Any:
    """Retrieve data from persistent memory."""
    data = _load_store()
    if key not in data:
        raise KeyError(f"No data found in PyShaft memory for key: {key!r}")
    return data[key]

def clear_store() -> None:
    """Clear all stored data."""
    if STORE_FILE.exists():
        try:
            os.remove(STORE_FILE)
        except IOError:
            pass

def set(key: str, value: Any) -> None:
    """Store a value with a key (alias for store_data)."""
    store_data(key, value)

def get(key: str) -> Any:
    """Retrieve a stored value by key (alias for get_stored)."""
    return get_stored(key)


class Pipeline:
    """Fluent pipeline for storing and retrieving values."""
    
    def set(self, key: str, value: Any) -> "Pipeline":
        store_data(key, value)
        return self
        
    def get(self, key: str) -> Any:
        return get_stored(key)
        
    def clear(self) -> "Pipeline":
        clear_store()
        return self

pipeline = Pipeline()
