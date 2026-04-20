"""PyShaft retry utilities — reusable retry logic for web and API operations."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional, Type, Union

logger = logging.getLogger("pyshaft.core.retry_utils")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 1,
        mode: Union[str, Type[Exception], int] = "all",
        backoff: float = 1.5,
    ):
        """Initialize retry configuration.

        Args:
            max_attempts: Number of attempts (including first try)
            mode: Retry mode - can be:
                - "all": Retry on any exception
                - "timeout": Retry on timeout-related exceptions
                - "fail": Retry on assertion/element not found errors
                - int: Status code to retry on (API only, e.g., 500)
                - Exception class: Specific exception type to catch
            backoff: Backoff multiplier between retries (exponential)
        """
        self.max_attempts = max(1, max_attempts)  # At least 1 attempt
        self.mode = mode
        self.backoff = backoff

    def should_retry(self, exception: Exception) -> bool:
        """Determine if we should retry based on the exception."""
        if isinstance(self.mode, int):
            # Status code mode - shouldn't be called with exception
            return False

        if self.mode == "all":
            return True

        if self.mode == "timeout":
            # Catch timeout-related exceptions
            from pyshaft.exceptions import WaitTimeoutError
            from selenium.common.exceptions import TimeoutException
            return isinstance(exception, (TimeoutException, WaitTimeoutError, TimeoutError))

        if self.mode == "fail":
            # Catch assertion and element not found errors
            from selenium.common.exceptions import NoSuchElementException
            return isinstance(exception, AssertionError) or isinstance(
                exception, (NoSuchElementException, AssertionError)
            )

        if isinstance(self.mode, type) and issubclass(self.mode, Exception):
            # Specific exception type
            return isinstance(exception, self.mode)

        return False

    def should_retry_status(self, status_code: int) -> bool:
        """Check if we should retry based on HTTP status code."""
        if isinstance(self.mode, int):
            return status_code == self.mode
        return False

    def apply_to_function(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a function with retry logic.

        Args:
            func: Callable to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of successful function call

        Raises:
            Last exception if all retries fail
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if we should retry
                if not self.should_retry(e):
                    raise

                # Don't sleep after the last attempt
                if attempt < self.max_attempts - 1:
                    wait_time = self.backoff ** attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {wait_time:.2f}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"All {self.max_attempts} attempts failed for {func.__name__}. "
                        f"Last error: {e}"
                    )

        # If we get here, all attempts failed
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Function {func.__name__} failed after {self.max_attempts} attempts")


def retry_on_exception(
    func: Callable[..., Any],
    max_attempts: int = 3,
    mode: Union[str, Type[Exception]] = "all",
    backoff: float = 1.5,
) -> Any:
    """Decorator to retry a function based on exception criteria.

    Args:
        func: Function to retry
        max_attempts: Number of attempts
        mode: Retry mode ("all", "timeout", "fail", or exception type)
        backoff: Backoff multiplier between retries

    Returns:
        Decorated function that retries on failure
    """
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        config = RetryConfig(max_attempts=max_attempts, mode=mode, backoff=backoff)
        return config.apply_to_function(func, *args, **kwargs)

    return wrapper

