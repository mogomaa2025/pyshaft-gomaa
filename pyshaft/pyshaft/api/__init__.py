"""PyShaft API module — chainable REST testing engine.

Usage:
    from pyshaft import api

    (api.get("/users/1")
        .assert_status(200)
        .assert_json("name", "Alice"))
    
    (api.post("/users", json={"name": "Bob"})
        .assert_status(201)
        .extract_json("id", "uid"))
"""

from __future__ import annotations

from pyshaft.api.methods import (
    send_delete,
    send_get,
    send_patch,
    send_post,
    send_put,
)
from pyshaft.api.store import (
    clear_store,
    get_stored,
    store_data,
)
from pyshaft.api.response import ApiResponse
from pyshaft.api.builder import RequestBuilder
from typing import Any, Dict, Optional


class ApiEngine:
    """State-aware API engine for fluent, punctuation-free multi-line testing."""

    def __init__(self):
        self._current_builder: Optional[RequestBuilder] = None

    def _get_builder(self) -> RequestBuilder:
        """Internal helper to get or create the current request buffer."""
        if self._current_builder is None:
            self._current_builder = RequestBuilder()
        return self._current_builder

    def request(self, method: str = "GET", url: str = "") -> ApiEngine:
        """Start a new request session, clearing any previous state.
        
        Returns the Engine instance for a unified fluency chain on the singleton.
        """
        self._current_builder = RequestBuilder(method, url)
        return self

    # --- Builder Proxy Methods (Modify State) ---

    def url(self, url: str) -> ApiEngine:
        self._get_builder().url(url)
        return self

    def method(self, method: str) -> ApiEngine:
        self._get_builder().method(method.upper())
        return self

    def param(self, key: str, value: Any) -> ApiEngine:
        self._get_builder().param(key, value)
        return self

    def query(self, key: str, value: Any) -> ApiEngine:
        return self.param(key, value)

    def header(self, key: str, value: str) -> ApiEngine:
        self._get_builder().header(key, value)
        return self

    def headers(self, headers_dict: dict[str, str]) -> ApiEngine:
        self._get_builder().headers(headers_dict)
        return self

    def body(self, *args: Any, **kwargs: Any) -> ApiEngine:
        self._get_builder().body(*args, **kwargs)
        return self

    def with_data(self, key: str, values: list[Any]) -> ApiEngine:
        self._get_builder().with_data(key, values)
        return self

    def perform_each(self, callback: Any) -> list[ApiResponse]:
        return self._get_builder().perform_each(callback)

    # --- Execute & Assert Proxy Methods (Trigger & Assert) ---

    def assert_status(self, expected: int) -> ApiEngine:
        self._get_builder().assert_status(expected)
        return self

    def assert_json(self, path: str, expected: Any) -> ApiEngine:
        self._get_builder().assert_json(path, expected)
        return self

    def assert_json_path(self, path: str, expected: Any = None) -> Any:
        return self._get_builder().assert_json_path(path, expected)

    def assert_json_type(self, path: str, expected_type: str) -> ApiEngine:
        self._get_builder().assert_json_type(path, expected_type)
        return self

    def assert_json_contains(self, path: str, expected: Any) -> ApiEngine:
        self._get_builder().assert_json_contains(path, expected)
        return self

    def assert_json_in_array(self, path: str, criteria: dict) -> ApiEngine:
        self._get_builder().assert_json_in_array(path, criteria)
        return self

    def assert_schema(self, schema: dict, path: str = "$") -> ApiEngine:
        self._get_builder().assert_schema(schema, path=path)
        return self

    def assert_deep_equals(self, path: str, expected: Any) -> ApiEngine:
        """Assert that a JSON object at path deeply equals the expected object."""
        self._get_builder().assert_deep_equals(path, expected)
        return self

    def assert_deep_contains(self, path: str, expected: dict) -> ApiEngine:
        """Assert that a JSON object at path contains all key-value pairs from expected."""
        self._get_builder().assert_deep_contains(path, expected)
        return self

    def assert_partial_schema(self, schema: dict, ignore_keys: list[str], path: str = "$") -> ApiEngine:
        self._get_builder().assert_partial_schema(schema, ignore_keys, path=path)
        return self

    def log(self, verbose: bool = True, max_length: int = 2000) -> ApiEngine:
        """Log/print the response in pretty format.
        
        Args:
            verbose: If True, show full response. If False, show minimal output (default: True)
            max_length: Truncate output longer than this (default: 2000 chars)
        """
        self._get_builder().log(verbose=verbose, max_length=max_length)
        return self

    def prettify(self, verbose: bool = True, max_length: int = 2000) -> ApiEngine:
        """Alias for log(). Print response in pretty format.
        
        Args:
            verbose: If True, show full response. If False, show minimal output (default: True)
            max_length: Truncate output longer than this (default: 2000 chars)
        """
        self._get_builder().log(verbose=verbose, max_length=max_length)
        return self

    def extract_json(self, path: str, key: str) -> ApiEngine:
        self._get_builder().extract_json(path, key)
        return self

    def save(self, path: str, key: str) -> ApiEngine:
        return self.extract_json(path, key)

    def for_each(self, path: str, callback: Any) -> ApiEngine:
        self._get_builder().for_each(path, callback)
        return self

    def for_each_key(self, path: str, callback: Any) -> ApiEngine:
        self._get_builder().for_each_key(path, callback)
        return self

    # --- HTTP Method Shortcuts ---

    def get(self, url: str, **kwargs: Any) -> Any:
        """Send a GET request."""
        if self._current_builder is not None:
            self._current_builder.get(url)
            self._current_builder.extra(**kwargs)
            return self
        # Auto-create builder for resolution support
        self._current_builder = RequestBuilder("GET", url)
        self._current_builder.extra(**kwargs)
        return self

    def post(self, url: str, body: Any = None, **kwargs: Any) -> Any:
        """Send a POST request."""
        if self._current_builder is not None:
            self._current_builder.post(url)
            self._current_builder.body(body)
            self._current_builder.extra(**kwargs)
            return self
        # Auto-create builder for resolution support
        self._current_builder = RequestBuilder("POST", url)
        self._current_builder.body(body)
        self._current_builder.extra(**kwargs)
        return self

    def put(self, url: str, body: Any = None, **kwargs: Any) -> Any:
        if self._current_builder is not None:
            self._current_builder.put(url).body(body).extra(**kwargs)
            return self
        # Auto-create builder for resolution support
        self._current_builder = RequestBuilder("PUT", url)
        self._current_builder.body(body)
        self._current_builder.extra(**kwargs)
        return self

    def patch(self, url: str, body: Any = None, **kwargs: Any) -> Any:
        if self._current_builder is not None:
            self._current_builder.patch(url).body(body).extra(**kwargs)
            return self
        # Auto-create builder for resolution support
        self._current_builder = RequestBuilder("PATCH", url)
        self._current_builder.body(body)
        self._current_builder.extra(**kwargs)
        return self

    def delete(self, url: str, **kwargs: Any) -> Any:
        if self._current_builder is not None:
            self._current_builder.delete(url).extra(**kwargs)
            return self
        # Auto-create builder for resolution support
        self._current_builder = RequestBuilder("DELETE", url)
        self._current_builder.extra(**kwargs)
        return self

    # --- Compatibility & Aliases ---

    def expect(self, response: ApiResponse) -> ApiResponse:
        """Start a response assertion chain (provided for backward compatibility)."""
        return response

    send_get = get
    send_post = post
    send_put = put
    send_patch = patch
    send_delete = delete

    def fill(self, template: Any, **data: Any) -> Any:
        """Deeply replace {{key}} placeholders in a JSON template."""
        import re

        def _replace(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: _replace(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_replace(i) for i in obj]
            elif isinstance(obj, str):
                match = re.fullmatch(r"\{\{\s*([\w-]+)\s*\}\}", obj)
                if match:
                    key = match.group(1)
                    if key in data: return data[key]
                res = obj
                for k, v in data.items():
                    res = res.replace(f"{{{{{k}}}}}", str(v))
                return res
            return obj

        return _replace(template)

    def stored(self, key: str) -> Any:
        return get_stored(key)

    def store(self, key: str, value: Any) -> None:
        store_data(key, value)

    def clear(self) -> None:
        clear_store()
        self._current_builder = None

    def last_response(self) -> Optional[ApiResponse]:
        """Retrieve the most recent response from the current stateful session."""
        if self._current_builder:
            return self._current_builder._executed_response
        return None

    response = last_response


# Singleton
api = ApiEngine()

# Expose top-level functions for module-level access (avoids IDE reference errors)
request = api.request
get = api.get
post = api.post
put = api.put
patch = api.patch
delete = api.delete
fill = api.fill
store = api.store
stored = api.stored
clear = api.clear
expect = api.expect
prettify = api.prettify
assert_json_path = api.assert_json_path

# Aliases for backward compatibility
send_get = api.get
send_post = api.post
send_put = api.put
send_patch = api.patch
send_delete = api.delete

__all__ = [
    "api",
    "request",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "fill",
    "store",
    "stored",
    "clear",
    "expect",
    "prettify",
    "assert_json_path",
    "send_get",
    "send_post",
    "send_put",
    "send_patch",
    "send_delete",
    "store_data",
    "get_stored",
    "clear_store",
]
