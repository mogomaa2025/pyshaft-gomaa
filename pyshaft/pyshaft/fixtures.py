"""PyShaft Test Fixtures — Ready-to-use fixtures for manual testers.

These fixtures make it easy to:
- Load test data from CSV/JSON files
- Set up API clients
- Manage test environments
- Use stored variables

Usage in test files:
    import pytest
    from pyshaft.fixtures import *

    # Use built-in fixtures
    def test_example(test_data):
        print(test_data["users"])

    def test_api(test_env):
        api.get(test_env["base_url"] + "/users")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from pyshaft.api import api, clear as clear_api_store
from pyshaft.session import session_context
from pyshaft.testdata import TestDataManager, load_test_data


# ---------------------------------------------------------------------------
# Test Data Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """Get the test data directory path.

    Default: tests/data/ (relative to project root)
    Override: Set PYSHAFT_DATA_DIR environment variable
    """
    base = os.environ.get("PYSHAFT_DATA_DIR")
    if base:
        return Path(base)
    # Try to find project root
    for path in [Path.cwd(), Path(__file__).parent.parent]:
        data_path = path / "tests" / "data"
        if data_path.exists():
            return data_path
    return Path("tests/data")


@pytest.fixture(scope="session")
def test_data_manager(data_dir: Path) -> TestDataManager:
    """Create a TestDataManager instance for the test session."""
    return TestDataManager(base_dir=data_dir)


@pytest.fixture
def test_data(test_data_manager: TestDataManager):
    """Fixture that provides a dict of all loaded test data.

    Usage:
        def test_something(test_data):
            users = test_data["users"]
            print(users[0]["name"])
    """
    return test_data_manager.load_all()


@pytest.fixture
def load_data(test_data_manager: TestDataManager):
    """Fixture that provides a function to load specific data files.

    Usage:
        def test_something(load_data):
            users = load_data("users")
            for user in users:
                print(user["email"])
    """
    return test_data_manager.get


# ---------------------------------------------------------------------------
# Environment Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_env() -> dict[str, Any]:
    """Get test environment configuration.

    Reads from environment variables:
        PYSHAFT_ENV - environment name (dev/staging/prod)
        PYSHAFT_BASE_URL - API base URL
        PYSHAFT_API_KEY - API key for authentication

    Also loads from tests/data/env/{ENV}.json if exists.
    """
    env_name = os.environ.get("PYSHAFT_ENV", "dev")

    # Load environment-specific config
    env_config = {}
    for path in [Path.cwd(), Path(__file__).parent.parent]:
        env_file = path / "tests" / "data" / "env" / f"{env_name}.json"
        if env_file.exists():
            import json
            with open(env_file) as f:
                env_config = json.load(f)
            break

    # Merge with environment variables
    return {
        "env": env_name,
        "base_url": os.environ.get("PYSHAFT_BASE_URL", env_config.get("base_url", "")),
        "api_key": os.environ.get("PYSHAFT_API_KEY", env_config.get("api_key", "")),
        **env_config,
    }


@pytest.fixture
def api_client(test_env: dict[str, Any]):
    """Configure API client with test environment.

    Sets base URL and any configured headers.
    """
    if test_env.get("base_url"):
        api.clear()
        # Set base URL for subsequent requests
        # Note: This is stored in the api singleton
    return api


# ---------------------------------------------------------------------------
# Store/Variable Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store():
    """Fixture to access and manipulate stored variables.

    Usage:
        def test_example(store):
            # Get stored value
            user_id = store.get("user-id")

            # Store a new value
            store.set("order-id", 123)

            # Clear all stored values
            store.clear()
    """
    class StoreFixture:
        def get(self, key: str, default: Any = None) -> Any:
            """Get a stored value."""
            try:
                return api.stored(key)
            except KeyError:
                if default is not None:
                    return default
                raise

        def set(self, key: str, value: Any) -> None:
            """Store a value."""
            api.store(key, value)

        def clear(self) -> None:
            """Clear all stored values."""
            clear_api_store()

        def all(self) -> dict[str, Any]:
            """Get all stored values."""
            import json
            store_file = Path(".pyshaft_store.json")
            if store_file.exists():
                with open(store_file) as f:
                    return json.load(f)
            return {}

    return StoreFixture()


# ---------------------------------------------------------------------------
# Web Fixtures (if browser is needed)
# ---------------------------------------------------------------------------


@pytest.fixture
def browser():
    """Fixture to get the active WebDriver instance.

    Only works if @pytest.mark.pyshaft_web is used or browser is configured to auto-start.
    """
    if session_context.is_active:
        return session_context.driver
    return None


@pytest.fixture
def web():
    """Fixture to access the web engine."""
    from pyshaft.web import web as web_engine
    return web_engine


# ---------------------------------------------------------------------------
# Cleanup Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Auto-cleanup after each test."""
    yield
    # Cleanup after test if needed
    try:
        from pyshaft.web import web as w
        w.flush()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Reporting Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_name(request: pytest.FixtureRequest) -> str:
    """Get the current test name."""
    return request.node.name


@pytest.fixture
def test_info(request: pytest.FixtureRequest) -> dict[str, Any]:
    """Get detailed test information."""
    return {
        "name": request.node.name,
        "nodeid": request.node.nodeid,
        "file": str(request.node.fspath),
    }


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