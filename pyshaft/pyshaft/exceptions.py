"""PyShaft custom exceptions — all errors carry rich debugging context."""


class PyShaftError(Exception):
    """Base exception for all PyShaft errors."""


class ElementNotFoundError(PyShaftError):
    """Raised when no element matches the given locator description.

    Attributes:
        description: The locator text that was searched for.
        strategies_tried: List of strategy names that were attempted.
        url: The page URL at the time of failure.
        screenshot: Path to auto-captured screenshot, if available.
    """

    def __init__(
        self,
        description: str,
        strategies_tried: list[str] | None = None,
        url: str = "",
        screenshot: str | None = None,
    ) -> None:
        self.description = description
        self.strategies_tried = strategies_tried or []
        self.url = url
        self.screenshot = screenshot
        strategies_info = ", ".join(self.strategies_tried) if self.strategies_tried else "none"
        super().__init__(
            f"Element not found: {description!r}\n"
            f"URL: {url}\n"
            f"Strategies tried: {strategies_info}\n"
            f"Screenshot: {screenshot or 'not captured'}"
        )


class MultipleMatchError(PyShaftError):
    """Raised when a locator matches more than one element and uniqueness is enforced.

    Attributes:
        description: The locator text that matched multiple elements.
        match_count: Number of elements found.
        url: The page URL at the time of failure.
    """

    def __init__(
        self,
        description: str,
        match_count: int,
        url: str = "",
    ) -> None:
        self.description = description
        self.match_count = match_count
        self.url = url
        super().__init__(
            f"Multiple elements found for {description!r}: {match_count} matches\n"
            f"URL: {url}\n"
            f"Set [validations] force_locator_unique = false to use best match instead."
        )


class ElementNotInteractableError(PyShaftError):
    """Raised when an element is found but cannot be interacted with.

    Attributes:
        description: The locator text for the element.
        reason: Why the element is not interactable (covered, disabled, etc.).
        overlay_info: Info about the covering element, if applicable.
    """

    def __init__(
        self,
        description: str,
        reason: str = "",
        overlay_info: str | None = None,
    ) -> None:
        self.description = description
        self.reason = reason
        self.overlay_info = overlay_info
        msg = f"Element not interactable: {description!r}\nReason: {reason}"
        if overlay_info:
            msg += f"\nCovered by: {overlay_info}"
        super().__init__(msg)


class WaitTimeoutError(PyShaftError):
    """Raised when an auto-wait condition is not met within the timeout.

    Attributes:
        condition: Description of the condition that timed out.
        timeout: The timeout value in seconds.
        element_state: Snapshot of the element's state at timeout.
    """

    def __init__(
        self,
        condition: str,
        timeout: float,
        element_state: dict | None = None,
    ) -> None:
        self.condition = condition
        self.timeout = timeout
        self.element_state = element_state or {}
        state_info = ", ".join(f"{k}={v}" for k, v in self.element_state.items())
        super().__init__(
            f"Wait timed out after {timeout:.1f}s\n"
            f"Condition: {condition}\n"
            f"Element state: {state_info or 'unknown'}"
        )


class NavigationError(PyShaftError):
    """Raised when page navigation fails verification.

    Attributes:
        url: The URL that was navigated to.
        reason: Why navigation was considered failed.
    """

    def __init__(self, url: str, reason: str = "") -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"Navigation failed: {url!r}\nReason: {reason}")


class ConfigError(PyShaftError):
    """Raised when pyshaft.toml contains invalid configuration values."""

    def __init__(self, field: str, value: str, allowed: str = "") -> None:
        self.field = field
        self.value = value
        self.allowed = allowed
        msg = f"Invalid config: {field} = {value!r}"
        if allowed:
            msg += f"\nAllowed values: {allowed}"
        super().__init__(msg)


class DriverCreationError(PyShaftError):
    """Raised when browser driver cannot be created."""

    def __init__(self, browser: str, reason: str = "") -> None:
        self.browser = browser
        self.reason = reason
        super().__init__(f"Failed to create {browser} driver\nReason: {reason}")


class SessionNotActiveError(PyShaftError):
    """Raised when trying to use a session that hasn't been started."""

    def __init__(self) -> None:
        super().__init__(
            "No active PyShaft session. "
            "Make sure the pyshaft pytest plugin is active or call session_context.start()."
        )


class DeferredAssertionError(PyShaftError):
    """Raised by check_deferred() when one or more deferred assertions failed.

    Attributes:
        failures: List of individual failure messages.
    """

    def __init__(self, failures: list[str]) -> None:
        self.failures = failures
        numbered = "\n".join(f"  {i + 1}. {f}" for i, f in enumerate(failures))
        super().__init__(
            f"{len(failures)} deferred assertion(s) failed:\n{numbered}"
        )
