"""PyShaft retryable API response — wrapper that supports chainable retry logic."""

from __future__ import annotations

from typing import Any, Union, Type

from pyshaft.api.response import ApiResponse
from pyshaft.core.retry_utils import RetryConfig


class RetryableResponse:
    """Wrapper around ApiResponse that provides chainable retry logic for assertions.
    
    Example:
        api.request().post("/users").body("name", "Bob").send() \
            .retry(3, "fail") \
            .assert_status(201) \
            .assert_json("id", 123)
    """

    def __init__(self, response: ApiResponse):
        """Initialize with an ApiResponse."""
        self._response = response
        self._retry_config: RetryConfig | None = None

    def retry(
        self,
        count: int,
        mode: Union[str, int, Type[Exception]] = "all",
        backoff: float = 1.5,
    ) -> "RetryableResponse":
        """Configure retry behavior for assertions.
        
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
            api.post("/users").send().retry(3)  # retry up to 3 times on any error
            api.post("/users").send().retry(2, "fail").assert_status(201)  # retry on assertion fail
            api.get("/data").send().retry(3, 500).assert_status(200)  # retry if status is 500
        """
        self._retry_config = RetryConfig(max_attempts=count, mode=mode, backoff=backoff)
        return self

    # --- Delegation methods for ApiResponse ---

    def assert_status(self, expected: int) -> "RetryableResponse":
        """Assert that the response status code matches expected."""
        def _do_assert():
            self._response.assert_status(expected)
        
        if self._retry_config:
            # Check if we should retry based on status code
            if self._retry_config.should_retry_status(self._response.status_code):
                # For status code retries, we need to re-execute the request
                # This is handled at RequestBuilder level
                pass

            # Execute assertion with retry
            self._retry_config.apply_to_function(_do_assert)
        else:
            _do_assert()
        
        self._retry_config = None  # Clear retry config after execution
        return self

    def assert_json(self, path: str, expected: Any) -> "RetryableResponse":
        """Assert that a JSON value at a given path matches expected."""
        def _do_assert():
            self._response.assert_json(path, expected)
        
        if self._retry_config:
            self._retry_config.apply_to_function(_do_assert)
        else:
            _do_assert()
        
        self._retry_config = None
        return self

    def assert_json_contains(self, path: str, expected: Any) -> "RetryableResponse":
        """Assert that a JSON collection at path contains the expected item."""
        def _do_assert():
            self._response.assert_json_contains(path, expected)
        
        if self._retry_config:
            self._retry_config.apply_to_function(_do_assert)
        else:
            _do_assert()
        
        self._retry_config = None
        return self

    def assert_json_type(self, path: str, expected_type: str) -> "RetryableResponse":
        """Assert that a JSON value at path is of a specific type."""
        def _do_assert():
            self._response.assert_json_type(path, expected_type)
        
        if self._retry_config:
            self._retry_config.apply_to_function(_do_assert)
        else:
            _do_assert()
        
        self._retry_config = None
        return self

    def assert_json_in_array(self, path: str, criteria: dict) -> "RetryableResponse":
        """Assert that an array at path contains an object matching the criteria."""
        def _do_assert():
            self._response.assert_json_in_array(path, criteria)
        
        if self._retry_config:
            self._retry_config.apply_to_function(_do_assert)
        else:
            _do_assert()
        
        self._retry_config = None
        return self

    def extract_json(self, path: str, key: str) -> "RetryableResponse":
        """Extract a JSON value at path and store it in global memory."""
        self._response.extract_json(path, key)
        return self

    def save(self, path: str, key: str) -> "RetryableResponse":
        """Alias for extract_json."""
        return self.extract_json(path, key)

    def for_each(self, path: str, callback: Any) -> "RetryableResponse":
        """Execute a callback function for each item in a JSON array at path."""
        self._response.for_each(path, callback)
        return self

    def for_each_key(self, path: str, callback: Any) -> "RetryableResponse":
        """Execute a callback function for each key in a JSON object at path."""
        self._response.for_each_key(path, callback)
        return self

    def prettify(self) -> "RetryableResponse":
        """Execute and print the pretty response body."""
        self._response.prettify()
        return self

    def assert_json_path(self, path: str, expected: Any = None) -> Any:
        """Assert that a JSONPath query finds the expected value."""
        return self._response.assert_json_path(path, expected)

    def map(self, path: str, field: str) -> list[Any]:
        """Extract a specific field from every object in an array at path."""
        return self._response.map(path, field)

    def to_map(self, path: str, key_field: str) -> dict[str, Any]:
        """Convert an array of objects at path into a dictionary keyed by key_field."""
        return self._response.to_map(path, key_field)

    def to_list(self, path: str) -> list[Any]:
        """Convert a JSON object at path into a list of its values."""
        return self._response.to_list(path)

    # --- Direct property access ---

    @property
    def status_code(self) -> int:
        """Get the HTTP status code."""
        return self._response.status_code

    @property
    def text(self) -> str:
        """Get the response text."""
        return self._response.text

    @property
    def json_data(self) -> Any:
        """Get the parsed JSON data."""
        return self._response.json_data

    def __repr__(self) -> str:
        return f"<RetryableResponse [{self.status_code}]>"

