"""PyShaft StepLogger — captures step metadata for reporting.

Records action name, locator, duration, status, and optional screenshot
for each step in the test execution pipeline.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("pyshaft.core.step_logger")


@dataclass(frozen=True)
class Step:
    """Immutable record of a single test action step.

    Attributes:
        action: The action performed (e.g., "click", "type_text", "open_url").
        locator: The locator description used (e.g., "Login button").
        duration_ms: Time taken in milliseconds.
        status: "pass" or "fail".
        timestamp: Unix timestamp when the step started.
        screenshot: Path to screenshot captured for this step, if any.
        error: Error message if the step failed.
    """
    action: str
    locator: str
    duration_ms: float
    status: str
    timestamp: float
    screenshot: str | None = None
    error: str | None = None


class StepLogger:
    """Collects step records during test execution.

    Thread-safe singleton — each test gets its own step list via reset().

    Usage::

        step_logger.reset()
        with step_logger.track("click", "Login button"):
            # ... perform action ...
        steps = step_logger.get_steps()
    """

    def __init__(self) -> None:
        self._steps: list[Step] = []
        self._listeners: list[callable] = []

    def add_listener(self, callback) -> None:
        """Register a callback that receives each Step as it's recorded.

        Args:
            callback: A callable accepting a single Step argument.
        """
        self._listeners.append(callback)

    def remove_listener(self, callback) -> None:
        """Remove a previously registered listener."""
        try:
            self._listeners.remove(callback)
        except ValueError:
            pass

    def reset(self) -> None:
        """Clear all recorded steps — called at the start of each test."""
        self._steps.clear()

    def record(
        self,
        action: str,
        locator: str,
        duration_ms: float,
        status: str = "pass",
        screenshot: str | None = None,
        error: str | None = None,
    ) -> None:
        """Record a completed step.

        Args:
            action: The action name.
            locator: The locator description.
            duration_ms: Duration in milliseconds.
            status: "pass" or "fail".
            screenshot: Optional screenshot path.
            error: Optional error message.
        """
        step = Step(
            action=action,
            locator=locator,
            duration_ms=duration_ms,
            status=status,
            timestamp=time.time(),
            screenshot=screenshot,
            error=error,
        )
        self._steps.append(step)
        logger.debug(
            "Step recorded: %s(%s) [%s] %.1fms",
            action,
            locator,
            status,
            duration_ms,
        )

        # Notify listeners
        for listener in self._listeners:
            try:
                listener(step)
            except Exception as e:
                logger.warning("Step listener error: %s", e)

    def get_steps(self) -> list[Step]:
        """Get all recorded steps for the current test."""
        return list(self._steps)

    @property
    def step_count(self) -> int:
        """Number of steps recorded so far."""
        return len(self._steps)

    @property
    def failed_steps(self) -> list[Step]:
        """Get only the failed steps."""
        return [s for s in self._steps if s.status == "fail"]


# Module-level singleton
step_logger = StepLogger()
