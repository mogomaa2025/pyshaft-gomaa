"""PyShaft Test Data Manager — Easy management of test data files.

Manual testers can store test data in CSV/JSON files and use them easily.
Data is automatically injected into tests via decorators or fixtures.

Usage:
    from pyshaft.testdata import TestDataManager, load_test_data

    # Simple loading
    users = load_test_data("users.csv")

    # With manager (supports overrides, env-based loading)
    manager = TestDataManager(base_dir="tests/data")
    data = manager.get("users", env="staging")
"""

from __future__ import annotations

import csv
import json
import logging
import os
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("pyshaft.testdata")


class DataFormat(Enum):
    CSV = "csv"
    JSON = "json"
    YAML = "yaml"


@dataclass
class TestDataSet:
    """Represents a loaded test data set."""
    name: str
    format: DataFormat
    rows: list[dict[str, Any]]
    source_file: Path
    env: str | None = None


@dataclass
class TestDataManager:
    """Manager for loading and accessing test data files.

    Supports:
    - Multiple data formats (CSV, JSON, YAML)
    - Environment-based overrides (e.g., users.staging.json)
    - Data interpolation with {{variable}} syntax
    - Shared data across tests

    Example:
        manager = TestDataManager(base_dir="tests/data")

        # Load users with staging override
        users = manager.get("users", env="staging")

        # Load with default fallback
        users = manager.get("users", env="staging", fallback=True)

        # Get all loaded datasets
        all_data = manager.load_all()
    """

    base_dir: Path = field(default_factory=lambda: Path("tests/data"))
    _cache: dict[str, TestDataSet] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.base_dir, str):
            self.base_dir = Path(self.base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get(
        self,
        name: str,
        env: str | None = None,
        fallback: bool = True,
    ) -> list[dict[str, Any]]:
        """Load test data by name.

        Args:
            name: Base name of the data file (without extension)
            env: Environment override (e.g., "staging", "prod")
            fallback: If True, fall back to base file if env-specific not found

        Returns:
            List of dictionaries (rows/items)

        Example:
            # Looks for: tests/data/users.staging.json
            # Falls back to: tests/data/users.json
            users = manager.get("users", env="staging")
        """
        cache_key = f"{name}:{env or 'default'}"

        if cache_key in self._cache:
            return self._cache[cache_key].rows

        # Try environment-specific file first
        if env:
            env_file = self.base_dir / f"{name}.{env}.json"
            if env_file.exists():
                rows = self._load_json(env_file)
                self._cache[cache_key] = TestDataSet(
                    name=name,
                    format=DataFormat.JSON,
                    rows=rows,
                    source_file=env_file,
                    env=env
                )
                logger.info(f"Loaded env-specific data: {env_file}")
                return rows

            env_file = self.base_dir / f"{name}.{env}.csv"
            if env_file.exists():
                rows = self._load_csv(env_file)
                self._cache[cache_key] = TestDataSet(
                    name=name,
                    format=DataFormat.CSV,
                    rows=rows,
                    source_file=env_file,
                    env=env
                )
                logger.info(f"Loaded env-specific data: {env_file}")
                return rows

            if not fallback:
                raise FileNotFoundError(
                    f"No data file found for {name} in env {env}"
                )
                logger.warning(f"No env-specific file for {name}.{env}, trying base file")

        # Try base files
        for ext in [".json", ".csv", ".yaml"]:
            base_file = self.base_dir / f"{name}{ext}"
            if base_file.exists():
                if ext == ".json":
                    rows = self._load_json(base_file)
                    fmt = DataFormat.JSON
                elif ext == ".csv":
                    rows = self._load_csv(base_file)
                    fmt = DataFormat.CSV
                else:
                    rows = self._load_yaml(base_file)
                    fmt = DataFormat.YAML

                self._cache[cache_key] = TestDataSet(
                    name=name,
                    format=fmt,
                    rows=rows,
                    source_file=base_file,
                    env=env
                )
                logger.info(f"Loaded test data: {base_file}")
                return rows

        raise FileNotFoundError(f"No test data file found: {name}")

    def _load_json(self, path: Path) -> list[dict[str, Any]]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Check for common wrapper keys
            for key in ["data", "items", "records", "results"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data]
        return []

    def _load_csv(self, path: Path) -> list[dict[str, Any]]:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _load_yaml(self, path: Path) -> list[dict[str, Any]]:
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                for key in ["data", "items", "records"]:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]
            return []
        except ImportError:
            logger.warning("yaml not installed, skipping yaml file")
            return []

    def load_all(self) -> dict[str, list[dict[str, Any]]]:
        """Load all data files from base_dir."""
        result = {}
        for f in self.base_dir.iterdir():
            if f.suffix in [".json", ".csv", ".yaml"]:
                name = f.stem.split(".")[0]  # Remove .staging suffix
                if name not in result:
                    try:
                        result[name] = self.get(name)
                    except Exception as e:
                        logger.warning(f"Failed to load {f.name}: {e}")
        return result

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache.clear()


# Global instance for convenience
_default_manager: TestDataManager | None = None


def get_data_manager(base_dir: str | Path = "tests/data") -> TestDataManager:
    """Get the global TestDataManager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = TestDataManager(base_dir=base_dir)
    return _default_manager


def load_test_data(
    name: str,
    env: str | None = None,
    base_dir: str | Path = "tests/data",
) -> list[dict[str, Any]]:
    """Convenience function to load test data.

    Args:
        name: Name of the data file (without extension)
        env: Optional environment (e.g., "staging")
        base_dir: Directory containing test data files

    Returns:
        List of dictionaries with test data

    Example:
        # Load tests/data/users.csv or tests/data/users.json
        users = load_test_data("users")

        # Load environment-specific data
        users = load_test_data("users", env="staging")
    """
    manager = TestDataManager(base_dir=base_dir)
    return manager.get(name, env=env)


def load_csv(file_path: str | Path) -> list[dict[str, Any]]:
    """Load a single CSV file."""
    if isinstance(file_path, str):
        file_path = Path(file_path)
    with open(file_path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_json(file_path: str | Path) -> list[dict[str, Any]]:
    """Load a single JSON file."""
    if isinstance(file_path, str):
        file_path = Path(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return [data]


__all__ = [
    "TestDataManager",
    "TestDataSet",
    "DataFormat",
    "get_data_manager",
    "load_test_data",
    "load_csv",
    "load_json",
]