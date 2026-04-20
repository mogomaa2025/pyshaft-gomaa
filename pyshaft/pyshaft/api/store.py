"""PyShaft API data store — simple memory for sharing data between requests."""

from __future__ import annotations

from typing import Any

_memory: dict[str, Any] = {}


def store_data(key: str, value: Any) -> None:
    """Store data in global memory."""
    _memory[key] = value


def get_stored(key: str) -> Any:
    """Retrieve data from global memory."""
    if key not in _memory:
        raise KeyError(f"No data found in PyShaft memory for key: {key!r}")
    return _memory[key]


def clear_store() -> None:
    """Clear all stored data."""
    _memory.clear()
