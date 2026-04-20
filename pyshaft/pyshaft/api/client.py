"""PyShaft API client — httpx session management."""

from __future__ import annotations

import httpx

from pyshaft.config import get_config

_client: httpx.Client | None = None


def get_api_client() -> httpx.Client:
    """Get the active API client, or create one from config."""
    global _client
    if _client is None:
        config = get_config().api
        _client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            verify=config.verify_ssl,
            headers={"User-Agent": "PyShaft/API-Engine"},
        )
    return _client


def close_api_client() -> None:
    """Close the API client session."""
    global _client
    if _client:
        _client.close()
        _client = None
