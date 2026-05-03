"""PyShaft API Request Builder — fluent, chainable configuration."""

from __future__ import annotations
from typing import Any, Dict, Optional

from pyshaft.api.response import ApiResponse


class RequestBuilder:
    """Fluent builder for creating and sending REST requests.
    
    Usage:
        (api.request()
            .post("/users")
            .body("name", "Bob")
            .send()
            .assert_status(201))
    """

    def __init__(self, method: str = "GET", url: str = ""):
        self._method = method.upper()
        self._url = url
        self._params: Dict[str, Any] = {}
        self._headers: Dict[str, str] = {}
        self._body: Optional[Any] = None
        self._kwargs: Dict[str, Any] = {}
        # Batch options
        self._loop_key: Optional[str] = None
        self._loop_values: Optional[list[Any]] = None
        # Execution state
        self._executed_response: Optional[ApiResponse] = None
        # Retry configuration
        self._retry_config: Optional[Any] = None

    def url(self, url: str) -> RequestBuilder:
        """Set the request URL."""
        self._url = url
        return self

    def method(self, method: str) -> RequestBuilder:
        """Set the HTTP method."""
        self._method = method.upper()
        return self

    def get(self, url: str) -> RequestBuilder:
        """Set method to GET and set URL."""
        self._method = "GET"
        self._url = url
        return self

    def post(self, url: str) -> RequestBuilder:
        """Set method to POST and set URL."""
        self._method = "POST"
        self._url = url
        return self

    def put(self, url: str) -> RequestBuilder:
        """Set method to PUT and set URL."""
        self._method = "PUT"
        self._url = url
        return self

    def patch(self, url: str) -> RequestBuilder:
        """Set method to PATCH and set URL."""
        self._method = "PATCH"
        self._url = url
        return self

    def delete(self, url: str) -> RequestBuilder:
        """Set method to DELETE and set URL."""
        self._method = "DELETE"
        self._url = url
        return self

    def param(self, key: str, value: Any) -> RequestBuilder:
        """Add a single query parameter."""
        self._params[key] = value
        return self

    def params(self, params_dict: Dict[str, Any]) -> RequestBuilder:
        """Add multiple query parameters from a dictionary."""
        self._params.update(params_dict)
        return self

    def query(self, key: str, value: Any) -> RequestBuilder:
        """Alias for param()."""
        return self.param(key, value)

    def header(self, key: str, value: str) -> RequestBuilder:
        """Add a request header."""
        self._headers[key] = value
        return self

    def headers(self, headers_dict: Dict[str, str]) -> RequestBuilder:
        """Add multiple headers from a dictionary."""
        self._headers.update(headers_dict)
        return self

    def body(self, *args: Any, **kwargs: Any) -> RequestBuilder:
        """Set request body."""
        if len(args) == 1 and not kwargs:
            self._body = args[0]
            return self

        if self._body is None or not isinstance(self._body, dict):
            self._body = {}
        if len(args) == 2:
            self._body[args[0]] = args[1]
        if kwargs:
            self._body.update(kwargs)
        return self

    def with_data(self, key: str, values: list[Any]) -> RequestBuilder:
        """Register a body key to be swapped during perform_each loop."""
        self._loop_key = key
        self._loop_values = values
        return self

    def extra(self, **kwargs: Any) -> RequestBuilder:
        """Pass extra arguments directly to httpx."""
        self._kwargs.update(kwargs)
        return self

    def retry(self, count: int, mode: Any = "all", backoff: float = 1.5) -> RequestBuilder:
        """Configure retry behavior for assertions on the response.

        Args:
            count: Number of retry attempts
            mode: Retry mode - can be:
                - "timeout": Retry on timeout exceptions
                - "fail": Retry on assertion/HTTP errors
                - "all": Retry on any exception (default)
                - int: HTTP status code (e.g., 500 to retry on 500 status)
                - Exception class: Specific exception type to catch
            backoff: Backoff multiplier between retries (default 1.5)

        Examples:
            api.request().post("/users").retry(3).send().assert_status(201)
            api.post("/users").retry(2, "fail").send().assert_status(201)
            api.get("/data").retry(3, 500).send().assert_status(200)
        """
        from pyshaft.core.retry_utils import RetryConfig
        self._retry_config = RetryConfig(max_attempts=count, mode=mode, backoff=backoff)
        return self

    def send(self) -> ApiResponse:
        """Execute the request and return the response."""
        return self.perform()

    def perform_each(self, callback: Any) -> list[ApiResponse]:
        """Execute the request once for each value in with_data."""
        if not self._loop_key or self._loop_values is None:
            raise ValueError("No data provided via with_data()")
        
        import copy
        original_body = copy.deepcopy(self._body) if self._body is not None else {}
        
        def run_once(val):
            if not isinstance(self._body, dict): self._body = {}
            self._body[self._loop_key] = val
            resp = self.perform()
            callback(resp)
            self._body = copy.deepcopy(original_body)
            return resp

        return [run_once(val) for val in self._loop_values]

    def perform(self) -> ApiResponse:
        """Execute the request, resolve placeholders, and cache the response."""
        from pyshaft.api.methods import (
            send_get, send_post, send_put, send_patch, send_delete
        )
        from pyshaft.api.store import get_stored
        import re

        def _resolve(val: Any) -> Any:
            """Recursively resolve {{var}} placeholders."""
            if isinstance(val, str):
                # Match entire string if it's just {{var}} to preserve types (int/float)
                match = re.fullmatch(r"\{\{\s*([\w-]+)\s*\}\}", val)
                if match:
                    try: return get_stored(match.group(1))
                    except KeyError: return val
                
                # Otherwise do partial string replacement
                res = val
                pattern = re.compile(r"\{\{\s*([\w-]+)\s*\}\}")
                for match in pattern.finditer(val):
                    key = match.group(1)
                    try:
                        replacement = get_stored(key)
                        res = res.replace(match.group(0), str(replacement))
                    except KeyError: pass
                return res
            elif isinstance(val, dict):
                return {k: _resolve(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [_resolve(i) for i in val]
            return val

        # 1. Resolve Variables
        self._url = _resolve(self._url)
        self._headers = _resolve(self._headers)
        self._params = _resolve(self._params)
        self._body = _resolve(self._body)
        
        # 2. Build Call
        call_kwargs = {**self._kwargs}
        
        # Merge all parameters into URL to prevent httpx from stripping existing ones
        import httpx
        url_obj = httpx.URL(self._url)
        if self._params:
            url_obj = url_obj.copy_merge_params(self._params)
        if "params" in call_kwargs:
            url_obj = url_obj.copy_merge_params(call_kwargs.pop("params"))
        self._url = str(url_obj)

        # Merge headers
        if self._headers:
            if "headers" in call_kwargs:
                call_kwargs["headers"].update(self._headers)
            else:
                call_kwargs["headers"] = self._headers

        match self._method:
            case "GET":
                resp = send_get(self._url, **call_kwargs)
            case "POST":
                resp = send_post(self._url, self._body, **call_kwargs)
            case "PUT":
                resp = send_put(self._url, self._body, **call_kwargs)
            case "PATCH":
                resp = send_patch(self._url, self._body, **call_kwargs)
            case "DELETE":
                resp = send_delete(self._url, **call_kwargs)
            case _:
                raise ValueError(f"Unsupported method: {self._method}")
        
        self._executed_response = resp

        # 3. Wrap with RetryableResponse if retry was configured
        if self._retry_config:
            from pyshaft.api.retryable_response import RetryableResponse
            retryable = RetryableResponse(resp)
            retryable._retry_config = self._retry_config
            return retryable

        return resp

    # --- Implicit Execution & Assertion Redirection ---
    
    def _ensure_performed(self) -> ApiResponse:
        if self._executed_response is None:
            return self.perform()
        return self._executed_response

    def assert_status(self, expected: int) -> RequestBuilder:
        self._ensure_performed().assert_status(expected)
        return self

    def assert_json(self, path: str, expected: Any) -> RequestBuilder:
        self._ensure_performed().assert_json(path, expected)
        return self

    def assert_json_path(self, path: str, expected: Any = None) -> Any:
        return self._ensure_performed().assert_json_path(path, expected)

    def assert_json_contains(self, path: str, expected: Any) -> RequestBuilder:
        self._ensure_performed().assert_json_contains(path, expected)
        return self

    def assert_json_type(self, path: str, expected_type: str) -> RequestBuilder:
        self._ensure_performed().assert_json_type(path, expected_type)
        return self

    def assert_json_in_array(self, path: str, criteria: dict) -> RequestBuilder:
        self._ensure_performed().assert_json_in_array(path, criteria)
        return self

    def assert_schema(self, schema: dict, path: str = "$") -> RequestBuilder:
        self._ensure_performed().assert_schema(schema, path=path)
        return self

    def assert_deep_equals(self, path: str, expected: Any) -> RequestBuilder:
        """Assert that a JSON object at path deeply equals the expected object."""
        self._ensure_performed().assert_deep_equals(path, expected)
        return self

    def assert_deep_contains(self, path: str, expected: dict) -> RequestBuilder:
        """Assert that a JSON object at path contains all key-value pairs from expected."""
        self._ensure_performed().assert_deep_contains(path, expected)
        return self

    def assert_partial_schema(self, schema: dict, ignore_keys: list[str], path: str = "$") -> RequestBuilder:
        self._ensure_performed().assert_partial_schema(schema, ignore_keys, path=path)
        return self

    def log(self, verbose: bool = True, max_length: int = 2000) -> RequestBuilder:
        """Log/print the response JSON in pretty format.
        
        Args:
            verbose: If True, show full response. If False, show minimal output (default: True)
            max_length: Truncate output longer than this (default: 2000 chars)
        """
        self._ensure_performed().log(verbose=verbose, max_length=max_length)
        return self

    def prettify(self, verbose: bool = True, max_length: int = 2000) -> RequestBuilder:
        """Alias for log(). Execute and print the pretty response body.
        
        Args:
            verbose: If True, show full response. If False, show minimal output (default: True)
            max_length: Truncate output longer than this (default: 2000 chars)
        """
        self._ensure_performed().log(verbose=verbose, max_length=max_length)
        return self

    def extract_json(self, path: str, key: str) -> RequestBuilder:
        self._ensure_performed().extract_json(path, key)
        return self

    def save(self, path: str, key: str) -> RequestBuilder:
        return self.extract_json(path, key)

    def for_each(self, path: str, callback: Any) -> RequestBuilder:
        self._ensure_performed().for_each(path, callback)
        return self

    def for_each_key(self, path: str, callback: Any) -> RequestBuilder:
        self._ensure_performed().for_each_key(path, callback)
        return self

    # Data transformation methods return raw data, so they terminate the chain
    def map(self, path: str, field: str) -> list[Any]:
        return self._ensure_performed().map(path, field)

    def to_map(self, path: str, key_field: str) -> dict[str, Any]:
        return self._ensure_performed().to_map(path, key_field)

    def to_list(self, path: str) -> list[Any]:
        return self._ensure_performed().to_list(path)
