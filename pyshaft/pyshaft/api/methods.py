"""PyShaft API methods — public GET, POST, PUT, DELETE functions."""

from __future__ import annotations

from typing import Any

from pyshaft.api.client import get_api_client
from pyshaft.api.response import ApiResponse


def send_get(url: str, **kwargs: Any) -> ApiResponse:
    """Send a GET request."""
    client = get_api_client()
    return ApiResponse(client.get(url, **kwargs))


def _handle_body(body: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Internal helper to map positional 'body' to types (json vs data)."""
    if body is not None and "json" not in kwargs and "data" not in kwargs and "content" not in kwargs:
        if isinstance(body, (dict, list)):
            kwargs["json"] = body
        else:
            kwargs["data"] = body
    return kwargs


def send_post(url: str, body: Any = None, **kwargs: Any) -> ApiResponse:
    """Send a POST request."""
    client = get_api_client()
    kwargs = _handle_body(body, kwargs)
    return ApiResponse(client.post(url, **kwargs))


def send_put(url: str, body: Any = None, **kwargs: Any) -> ApiResponse:
    """Send a PUT request."""
    client = get_api_client()
    kwargs = _handle_body(body, kwargs)
    return ApiResponse(client.put(url, **kwargs))


def send_patch(url: str, body: Any = None, **kwargs: Any) -> ApiResponse:
    """Send a PATCH request."""
    client = get_api_client()
    kwargs = _handle_body(body, kwargs)
    return ApiResponse(client.patch(url, **kwargs))


def send_delete(url: str, **kwargs: Any) -> ApiResponse:
    """Send a DELETE request."""
    client = get_api_client()
    return ApiResponse(client.delete(url, **kwargs))
